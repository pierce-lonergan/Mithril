"""Sandboxed checker for one X1 `check` call (X1 DESIGN 11.2-11.4, X1-amendment-1 2.3 item 5).

Content-agnostic: it takes the subject's current workspace and a *check bundle* supplied by the
caller (the per-attempt harness, which the Gatekeeper fills from the sealed item) and runs the
arm's toolchain inside a fresh per-call `winsandbox.Sandbox`:

  - Mithril arm: `mithi check --json --subset agent --prelude prelude.mith solution.mith driver.mith`
    for the build, and `mithi run --entry <e>` per visible case for `--tests`.
  - Rust arm: `rustc` on prelude.rs + solution.rs + driver (main.rs), then the built binary per case,
    plus the lexical static gate of harness/x1check.py (DESIGN 11.4).

What makes this the real control, not the smoke kit's wrapper:
  - the toolchain runs in an LPAC AppContainer with no network and read-only inputs; the agent's
    solution text is copied into the sandbox's `in/`, the build writes only to `out/`;
  - no hidden data (expected outputs, references, oracle model) is ever placed in a sandbox that
    runs agent-produced code: the visible driver and the public prelude are the only inputs, and the
    expected outputs are compared **in this parent process**, outside the sandbox (DESIGN 11.3 compare
    stage). The two-stage held-out oracle (Stage B on sealed vectors) is the same shape and is out of
    this module's scope (it runs after collection, DESIGN 4.2).

This module performs no agent I/O and reads no instructions from the workspace (03 row 31); the brief
and diagnostics are data, never commands.
"""

from __future__ import annotations

import json
import re
import secrets
import time
from pathlib import Path

import winsandbox as W

NONCE_RE = re.compile(r"^N:[0-9a-f]{16}$")
EXT = {"mithril": "mith", "rust": "rs"}

# The lexical static gate lives in the smoke harness; import it if present, else a minimal inline copy.
try:  # pragma: no cover - import shape depends on run root
    import importlib.util
    _sg = (Path(__file__).resolve().parents[1] / "smoke" / "harness" / "x1check.py")
    if _sg.exists():
        _spec = importlib.util.spec_from_file_location("x1check_gate", _sg)
        _x1check = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_x1check)
        rust_static_gate = _x1check.rust_static_gate
        count_holes = _x1check.count_holes
    else:
        raise ImportError
except Exception:  # minimal fallback so this module stands alone
    _HOLE = re.compile(r"\b(todo|unimplemented)\s*!")
    _BANNED = [re.compile(r"\binclude(_bytes|_str)?\s*!"), re.compile(r"\benv\s*!"),
               re.compile(r"\bstd\s*::\s*(fs|env|process|net|os)\b"), re.compile(r"\bunsafe\b"),
               re.compile(r"\bextern\s+crate\b"), re.compile(r"\b(global_)?asm\s*!")]

    def rust_static_gate(src: str):
        return [{"code": "E-X1-GATE", "what": rx.pattern} for rx in _BANNED if rx.search(src)]

    def count_holes(src: str):
        return len(_HOLE.findall(src))


def _mithi_json(stdout: str):
    line = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    try:
        return json.loads(line)
    except ValueError:
        return None


class CallBudget:
    """One `check` call's CPU pool and wall deadline (DESIGN 11.2: "180 CPU-seconds per call", wall
    backstop 540 s; review 1, finding 2). Every sandbox run inside the call (Stage A and each Stage B
    case) gets only what is left; once either is spent, nothing more starts."""

    MIN_SLICE_S = 0.05

    def __init__(self, limits: dict | None):
        self.lim = dict(W.DEFAULT_LIMITS)
        self.lim.update(limits or {})
        self.t0 = time.monotonic()
        self.cpu_cap = float(self.lim["cpu_s"])
        self.wall_cap = float(self.lim["wall_s"])
        self.deadline = self.t0 + self.wall_cap
        self.cpu_used = 0.0
        self.spent = None      # None | "cpu" | "wall"
        self.runs = 0

    def left(self):
        return self.cpu_cap - self.cpu_used, self.deadline - time.monotonic()

    def can_start(self) -> bool:
        cpu_left, wall_left = self.left()
        if self.spent is None and cpu_left <= self.MIN_SLICE_S:
            self.spent = "cpu"
        if self.spent is None and wall_left <= self.MIN_SLICE_S:
            self.spent = "wall"
        return self.spent is None

    def run(self, sb, argv, cwd):
        """One sandbox run with the remainder of the pool; None if the call's budget is spent."""
        if not self.can_start():
            return None
        cpu_left, wall_left = self.left()
        r = sb.run(argv, cwd=cwd, limits=dict(self.lim, cpu_s=cpu_left, wall_s=wall_left))
        self.runs += 1
        self.cpu_used += float(r.get("cpu_user_s") or 0.0) + float(r.get("cpu_kernel_s") or 0.0)
        if r.get("killed") in ("cpu", "wall") and self.spent is None:
            # the run hit the remainder it was given: the call's budget is spent
            self.spent = r["killed"]
        return r

    def report(self) -> dict:
        return {"cpu_s_cap": round(self.cpu_cap, 3), "cpu_s_used": round(self.cpu_used, 3),
                "wall_s_cap": round(self.wall_cap, 3), "wall_s_used": round(time.monotonic() - self.t0, 3),
                "sandbox_runs": self.runs, "spent": self.spent}


def run_check(image: W.ToolchainImage, call_dir: Path, arm: str, solution_text: str,
              bundle: dict, limits: dict | None = None) -> dict:
    """One check call, two stages (DESIGN 11.3).

    `bundle` holds: prelude (str), driver (str), entries (list[str] for mithril visible cases),
    expected (list[str]), and optionally run_tests (bool). `call_dir` is a fresh per-call directory
    under a neutral root with a random name, outside the attempt tree (mcp_server.py); this function
    creates the sub-sandboxes under it and tears them down. `limits` are the call's caps: one CPU
    pool (`cpu_s`) and one wall deadline (`wall_s`) for the whole call, shared by every sandbox run.

    Stage A (build): the arm's toolchain. Mithril runs `mithi check` in an LPAC sandbox (an
    interpreter, no child process). Rust/C run the compiler in a NON-LPAC sandbox, because the GNU
    toolchain must exec its own linker (a child process), which LPAC forbids; non-LPAC still denies
    the repo/oracle (no ALL-APPLICATION-PACKAGES ACE on them) and the network (no internetClient
    capability), so the build is confined, and only toolchain binaries from the image run.

    Stage B (run): each visible case runs the built artifact in its OWN fresh LPAC sandbox (its own
    AppContainer SID and its own empty out/, so no case sees a file an earlier case wrote; DESIGN
    11.2 "no prior call's artifacts"), with NO child process allowed and no network - this is where
    agent-controlled behaviour executes. Expected outputs are compared HERE, outside every sandbox;
    no hidden data is ever placed in a sandbox that runs agent code.
    """
    call_dir = Path(call_dir)
    budget = CallBudget(limits)
    try:
        res = _run_check(image, call_dir, arm, solution_text, bundle, budget)
    finally:
        try:
            call_dir.rmdir()   # the sandboxes removed their own sub-directories
        except OSError:
            pass
    res["budget"] = budget.report()
    return res


def _run_check(image, call_dir, arm, solution_text, bundle, budget: CallBudget) -> dict:
    ext = EXT[arm]
    nonce = secrets.token_hex(8)
    driver = bundle["driver"].replace("@@NONCE@@", nonce)
    res = {"arm": arm, "holes": count_holes(solution_text)}
    gate = rust_static_gate(solution_text) if arm == "rust" else []
    res["static_gate"] = {"verdict": "fail" if gate else "pass", "hits": gate}
    built_ok = False
    build_lpac = arm != "rust"   # mithril interpreter: LPAC; rust compiler: non-LPAC (linker child)
    exe_bytes = None

    with W.Sandbox(call_dir / "A", image, lpac=build_lpac, name="A") as a:
        (a.indir / f"prelude.{ext}").write_text(bundle["prelude"], encoding="utf-8")
        (a.indir / f"solution.{ext}").write_text(solution_text, encoding="utf-8")
        (a.indir / f"driver.{ext}").write_text(driver, encoding="utf-8")
        if arm == "mithril":
            argv = [str(image.mithi), "check", "--json", "--subset", "agent",
                    "--prelude", str(a.indir / "prelude.mith"),
                    str(a.indir / "solution.mith"), str(a.indir / "driver.mith")]
        else:
            exe = a.outdir / "x1drv.exe"
            argv = [str(image.rustc), "--edition", "2021", "--crate-name", "x1drv",
                    "--crate-type", "bin", "-C", "opt-level=0", "-C", "overflow-checks=on",
                    "-C", "debug-assertions=on", "-C", "codegen-units=1", "-F", "unsafe_code",
                    "--color", "never", "-o", str(exe), str(a.indir / "driver.rs")]
        r = budget.run(a, argv, cwd=a.outdir)
        if r is None:
            return {**res, "verdict": "timeout", "killed": budget.spent}
        if not r["started"]:
            return {**res, "verdict": "internal-error", "sandbox_error": r.get("create_error_text")}
        if r["killed"]:
            return {**res, "verdict": "timeout", "killed": r["killed"]}
        if arm == "mithril":
            j = _mithi_json(r["stdout"])
            if j is None:
                return {**res, "verdict": "internal-error", "detail": (r["stdout"] + r["stderr"])[:400]}
            res["checker"] = j.get("verdict")
            res["primary"] = j.get("primary")
            built_ok = j.get("verdict") == "accept"
        else:
            res["checker"] = "accept" if (r["rc"] == 0 and exe.exists()) else "reject"
            built_ok = r["rc"] == 0 and exe.exists() and not gate
            if not built_ok and r["stderr"]:
                res["diagnostics"] = r["stderr"][:4000]
            if exe.exists():
                exe_bytes = exe.read_bytes()

    res["verdict"] = "accept" if (built_ok and not gate) else "reject"
    if not bundle.get("run_tests"):
        return res
    if res["verdict"] != "accept":
        res["tests"] = {"run": False, "why": "checker or static gate rejected the file"}
        return res

    # Stage B: one fresh LPAC sandbox per visible case, all inside the call's budget.
    cases = []
    for k, exp in enumerate(bundle["expected"]):
        if not budget.can_start():
            cases.append({"case": k, "ok": False, "expected": exp[:200],
                          "error": f"not run: the call's {budget.spent} budget is spent"})
            continue
        with W.Sandbox(call_dir / f"B{k}", image, lpac=True, name=f"B{k}") as b:
            if arm == "mithril":
                (b.indir / "prelude.mith").write_text(bundle["prelude"], encoding="utf-8")
                (b.indir / "solution.mith").write_text(solution_text, encoding="utf-8")
                (b.indir / "driver.mith").write_text(driver, encoding="utf-8")
                argv = [str(image.mithi), "run", "--subset", "agent",
                        "--prelude", str(b.indir / "prelude.mith"), "--entry", bundle["entries"][k],
                        str(b.indir / "solution.mith"), str(b.indir / "driver.mith")]
            else:
                exe = b.indir / "x1drv.exe"
                exe.write_bytes(exe_bytes)
                argv = [str(exe), str(k)]
            rr = budget.run(b, argv, cwd=b.outdir)
        if rr is None:
            cases.append({"case": k, "ok": False, "expected": exp[:200],
                          "error": f"not run: the call's {budget.spent} budget is spent"})
            continue
        parse = _parse_mith_run if arm == "mithril" else _parse_rust_run
        got = parse(rr["stdout"], nonce) if rr["started"] and not rr["killed"] else None
        cases.append(_case(k, exp, got, rr))
    npass = sum(1 for c in cases if c["ok"])
    res["tests"] = {"run": True, "passed": npass, "failed": len(cases) - npass, "cases": cases}
    return res


def _case(k, exp, got, rr):
    ok = got is not None and got == exp
    c = {"case": k, "ok": ok}
    if not ok:
        c["expected"] = exp[:200]
        if got is not None:
            c["got"] = got[:200]
        elif rr.get("killed"):
            c["error"] = f"killed:{rr['killed']}"
        else:
            c["error"] = (rr.get("stderr") or "")[:200] or "no result record"
    return c


def _parse_mith_run(stdout: str, nonce: str):
    s = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    parts = s.split("|")
    if len(parts) == 2 and parts[1] == "N:" + nonce:
        return parts[0]
    return None


def _parse_rust_run(stdout: str, nonce: str):
    lines = stdout.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) == 2 and lines[1] == "N:" + nonce:
        return lines[0]
    return None
