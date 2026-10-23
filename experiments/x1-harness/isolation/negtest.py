"""X1 isolation negative-test suite (X1-amendment-1 2.3; X1 DESIGN 4.6, 11).

Proves each control by trying to break it and showing it fails with a SPECIFIC denial (an OS error
code, a kill reason, a refusal), never merely "not OK": the probe reports every failure as one
"ERR <op> code=<code> ..." line and never panics or aborts (review 1, finding 4). Runs on the laptop,
no installers, no system settings. Builds a probe with the pinned rustc, builds a throwaway toolchain
image, and:

  A. LPAC sandbox battery (the Stage B configuration, where agent output runs):
       positive: read a granted input; write to out/.
       negative: read the repo / an oracle-or-design file / another attempt / the user's Claude
                 config; write into the read-only input; list the repo; TCP connect out; resolve DNS;
                 connect to a loopback listener (reachable from outside the sandbox: control row);
                 spawn a child process; environment names outside the allowlist; TEMP outside out/.
  A2. Non-LPAC battery (the Stage A configuration, where the Rust compiler runs): the repo and
       another attempt, TCP out, DNS, loopback, environment names.
  B. Job and watchdog budgets: CPU-time, wall-clock, memory (chunked and one large block, with a
     positive control), child processes, and disk (writes into out/ and into the AppContainer
     profile's own storage folder), and the profile folder's removal.
  C. Per-call budget and Stage B shape (checker.run_check): one wall deadline and one CPU pool for a
     whole check call with several slow cases; a fresh sandbox per visible case.
  D. The MCP server (no shell), started with only its generated env block: only the eight tools;
     read/write confined to work/; Stage A diagnostics name no attempt; the 8-check budget; submit.
  E. The isolated configuration: agent type, settings, launch argv, env blocks, refusal of attempt
     directories under project instructions or a repository, opaque names, finish_attempt.
  F. Nothing left behind: no x1iso AppContainer profile registered, no profile folder.

Every check is tagged PASS/FAIL and written to <out>/negtest.json. Results are [M] (measured on this
machine, this run). The report records the Python version, not the interpreter's path (a path in
the user profile): negtest.py writes that field itself (review 1, finding 9).

Usage:
  python negtest.py --mithi C:\\Users\\Pierce Lonergan\\x1s\\mithi.exe [--rustc <rustc.exe>] \
      --out <results dir> [--repo <repo root>] [--attempt-root <dir>]

--attempt-root must not lie under CLAUDE.md / AGENTS.md / .claude / .git (attempt.py refuses such a
place); the default is <SystemDrive>\\x1iso-negtest-<random>, created and removed by the suite.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import winsandbox as W  # noqa: E402
import attempt as A  # noqa: E402
import checker as C  # noqa: E402

REPO = HERE.parents[2]
DEFAULT_RUSTC = Path.home() / ".rustup-mithril" / "toolchains" / "1.99.1-x86_64-pc-windows-gnu" / "bin" / "rustc.exe"
MIB = 1 << 20


def build_probe(rustc: Path, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    exe = out / "probe.exe"
    r = subprocess.run([str(rustc), "--edition", "2021", "-C", "opt-level=2", "--color", "never",
                        "-o", str(exe), str(HERE / "probe" / "probe.rs")],
                       capture_output=True, text=True, cwd=str(out), timeout=180)
    if not exe.exists():
        raise SystemExit("probe build failed:\n" + r.stderr[:2000])
    return exe


class Report:
    def __init__(self):
        self.rows = []

    def check(self, control: str, name: str, ok: bool, detail: str = ""):
        self.rows.append({"control": control, "test": name, "verdict": "PASS" if ok else "FAIL",
                          "detail": detail[:300]})
        print(f"[{'PASS' if ok else 'FAIL':4}] {control:10} {name:44} {detail[:90]}", flush=True)

    def ok(self):
        return all(r["verdict"] == "PASS" for r in self.rows)


def last_line(r: dict) -> str:
    if not r.get("started", True):
        return f"(not started: {r.get('create_error')} {r.get('create_error_text')})"
    out = (r.get("stdout", "") + r.get("stderr", "")).strip().splitlines()
    return out[-1] if out else f"(no output; killed={r.get('killed')} rc={r.get('rc')})"


def err_code(line: str, op: str):
    """The code of an 'ERR <op> code=<code> ...' line, else None."""
    pre = f"ERR {op} code="
    if not line.startswith(pre):
        return None
    return line[len(pre):].split(" ", 1)[0]


def after_flag(argv: list, flag: str):
    """The argument that follows `flag` in an argv list, else None."""
    if flag in argv and argv.index(flag) + 1 < len(argv):
        return argv[argv.index(flag) + 1]
    return None


def is_denied(line: str, op: str, codes) -> bool:
    return err_code(line, op) in set(codes)


def winsock_refused(line: str, op: str) -> bool:
    # LPAC: WSAStartup returns 10107 (WSASYSCALLFAILURE) [M]; Rust std asserts on it, the probe
    # catches the panic and reports it on its line.
    return err_code(line, op) == "panic" and "10107" in line


# ----------------------------------------------------------------------------- A / A2: sandboxes

def sandbox_battery(rep: Report, image: W.ToolchainImage, scratch: Path, repo: Path, other_file: Path,
                    lpac: bool, port: int):
    probe = str(image.probe)
    tag = "lpac" if lpac else "nonlpac"
    ctl = "sandbox" if lpac else "stageA"
    oracle = None
    for cand in (repo / "experiments" / "x1-harness" / "smoke" / "tasks" / "D-Q4-1" / "task.py",
                 repo / "experiments" / "x1-harness" / "DESIGN.md"):
        if cand.exists():
            oracle = cand
            break
    cd = scratch / f"sb_{tag}"
    n = [0]

    def P(op, args, name, want, lim=None):
        n[0] += 1
        with W.Sandbox(cd / f"{n[0]:02d}", image, lpac=lpac) as sb:
            a = list(args)
            if op == "read-granted":
                (sb.indir / "input.txt").write_text("the visible task input\n")
                op, a = "read", [str(sb.indir / "input.txt")]
            elif op == "write-out":
                op, a = "write", [str(sb.outdir / "solution.txt")]
            elif op == "write-in":
                op, a = "write", [str(sb.indir / "evil.txt")]
            r = sb.run([probe, op, *a], cwd=sb.outdir, limits=lim or {"wall_s": 30, "cpu_s": 20})
            line = last_line(r)
            ok = want(line, sb)
            rep.check(ctl, name, ok, line)

    denied5 = lambda op: (lambda line, sb: is_denied(line, op, {"5"}))
    if lpac:
        P("read-granted", [], "read granted input", lambda l, sb: l.startswith("OK read"))
        P("write-out", [], "write to out", lambda l, sb: l.startswith("OK write"))
    P("read", [str(repo / "README.md")], f"{tag}: read repo README -> os error 5", denied5("read"))
    if lpac and oracle:
        P("read", [str(oracle)], "lpac: read an oracle/design file -> os error 5", denied5("read"))
    P("read", [str(other_file)], f"{tag}: read another attempt -> os error 5", denied5("read"))
    if lpac:
        P("read", [str(Path.home() / ".claude" / "settings.json")], "lpac: read claude config -> os error 5",
          denied5("read"))
        P("write-in", [], "lpac: write to read-only input -> os error 5", denied5("write"))
        P("listdir", [str(repo)], "lpac: list the repo -> os error 5", denied5("listdir"))
        P("connect", ["1.1.1.1:443"], "lpac: TCP connect out -> winsock 10107",
          lambda l, sb: winsock_refused(l, "connect"))
        P("resolve", ["example.com"], "lpac: DNS resolve -> winsock 10107",
          lambda l, sb: winsock_refused(l, "resolve"))
        P("connect", [f"127.0.0.1:{port}"], "lpac: loopback listener -> winsock 10107",
          lambda l, sb: winsock_refused(l, "connect"))
        P("spawnmany", ["20"], "lpac: spawn child -> os error 5, 0 spawned",
          lambda l, sb: is_denied(l, "spawnmany", {"5"}) and l.endswith("after 0 spawns"))
    else:
        # WSAEACCES: the AppContainer has no network capability [M]
        P("connect", ["1.1.1.1:443"], "nonlpac: TCP connect out -> 10013", lambda l, sb: is_denied(l, "connect", {"10013"}))
        # WSAHOST_NOT_FOUND family: the name does not resolve inside the container [M: 11001]
        P("resolve", ["example.com"], "nonlpac: DNS resolve -> 1100x",
          lambda l, sb: is_denied(l, "resolve", {"11001", "11002", "11003", "11004"}))
        # the listener IS reachable from outside (control row); inside, the SYN is dropped [M: TimedOut]
        P("connect", [f"127.0.0.1:{port}"], "nonlpac: loopback listener -> dropped/refused",
          lambda l, sb: is_denied(l, "connect", {"TimedOut", "10013", "10060"}))
    P("envnames", [], f"{tag}: env names within the allowlist",
      lambda l, sb: l.startswith("OK envnames ") and set(l.split(" ", 2)[2].split(",")) <= W.SANDBOX_ENV_NAMES)
    if lpac:
        P("envget", ["TEMP"], "lpac: TEMP lies inside out/ (disk-capped)",
          lambda l, sb: l.startswith("OK envget ") and A.is_within(Path(l.split(" ", 2)[2]), sb.outdir))


# ----------------------------------------------------------------------------- B: budgets

def job_battery(rep: Report, image: W.ToolchainImage, scratch: Path):
    probe = str(image.probe)
    cd = scratch / "sb_job"
    n = [0]

    def one(args, lim, name, judge, setup=None):
        n[0] += 1
        with W.Sandbox(cd / f"{n[0]:02d}", image, lpac=True) as sb:
            a = setup(sb) if setup else list(args)
            r = sb.run([probe, *a], cwd=sb.outdir, limits=lim)
            ok, detail = judge(r, last_line(r), sb)
            rep.check("budget", name, ok, detail)
            return sb.ac.storage_root

    one(["burn", "500"], {"cpu_s": 180, "wall_s": 60}, "normal work completes",
        lambda r, l, sb: (l.startswith("OK burn"), l))
    one(["sleep", "60000"], {"cpu_s": 180, "wall_s": 3}, "wall budget kills at the cap",
        lambda r, l, sb: (r["killed"] == "wall" and r["wall_s"] <= 3 + 1.5,
                          f"killed={r['killed']} wall={r['wall_s']} cpu={r.get('cpu_user_s')}"))
    one(["burn", "60000"], {"cpu_s": 2, "wall_s": 90}, "cpu budget kills (user+kernel)",
        lambda r, l, sb: (r["killed"] == "cpu" and r["cpu_user_s"] + r["cpu_kernel_s"] <= 2 + 0.5,
                          f"killed={r['killed']} wall={r['wall_s']} cpu={r['cpu_user_s']}+{r['cpu_kernel_s']}"))
    cap = 256 * MIB

    def mem_chunks(r, l, sb):
        c = err_code(l, "alloc")
        got_mb = None
        if c == "alloc" and " after " in l:
            got_mb = int(l.split(" after ", 1)[1].split(" ", 1)[0])
        peak = r.get("peak_job_memory_bytes", 0)
        # PeakJobMemoryUsed also counts the one refused request (here 1 MiB) [M]; allow 2 MiB
        ok = got_mb is not None and got_mb * MIB <= cap and peak <= cap + 2 * MIB
        return ok, f"{l} | peak={peak} cap={cap}"
    one(["alloc", "8000"], {"memory_bytes": cap, "wall_s": 40, "cpu_s": 40},
        "memory cap: 1 MiB chunks refused at the cap", mem_chunks)
    one(["alloc1", "400"], {"memory_bytes": cap, "wall_s": 40, "cpu_s": 40},
        "memory cap: one 400 MB block refused",
        lambda r, l, sb: (err_code(l, "alloc1") == "alloc",
                          f"{l} | peak={r.get('peak_job_memory_bytes')} (counts the refused request) cap={cap}"))
    one(["alloc1", "200"], {"memory_bytes": cap, "wall_s": 40, "cpu_s": 40},
        "memory cap: a 200 MB block under the cap works",
        lambda r, l, sb: (l.startswith("OK alloc1"), f"{l} | peak={r.get('peak_job_memory_bytes')}"))
    one(["spawnmany", "40"], {"processes": 8, "wall_s": 20, "cpu_s": 30}, "child spawn denied",
        lambda r, l, sb: (is_denied(l, "spawnmany", {"5"}), l))
    disk = {"out_bytes": 8 * MIB, "wall_s": 30, "cpu_s": 20}
    root = one([], disk, "disk cap: writes into the profile's own folder",
               lambda r, l, sb: (r["killed"] == "disk", f"killed={r['killed']} | {l}"),
               setup=lambda sb: ["fill", str(sb.ac.storage_root / "AC" / "fill.bin"), "64"])
    rep.check("budget", "profile storage folder removed on close", not root.exists(),
              f"exists_after_close={root.exists()}")
    one([], disk, "disk cap: writes into TEMP (inside out/)",
        lambda r, l, sb: (r["killed"] == "disk", f"killed={r['killed']} | {l}"),
        setup=lambda sb: ["fill", str(sb.outdir / "tmp" / "Packages" / sb.name / "AC" / "Temp" / "fill.bin"), "64"])


# ----------------------------------------------------------------------------- C: per-call budget

RUST_DRIVER = ("#![allow(unused_imports, dead_code, unused_variables)]\n"
               "mod prelude;\nmod solution;\nuse solution::*;\n"
               "fn x1h_case(_k: usize) -> String { format!(\"{}\", f()) }\n"
               "fn main() {\n"
               "    let a: Vec<String> = std::env::args().collect();\n"
               "    let k: usize = a.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);\n"
               "    println!(\"{}\", x1h_case(k));\n"
               "    println!(\"N:@@NONCE@@\");\n}\n")

# Harness-side driver (not gated: the gate applies to the subject's solution) for the Stage B shape
# test: case 0 leaves a file in its working directory, case 1 looks for it.
LEAK_DRIVER = ("#![allow(unused_imports, dead_code, unused_variables)]\n"
               "mod prelude;\nmod solution;\nuse solution::*;\n"
               "fn x1h_case(k: usize) -> String {\n"
               "    if k == 0 { std::fs::write(\"marker.txt\", b\"left by case 0\").map(|_| \"wrote\".to_string())"
               ".unwrap_or_else(|e| format!(\"write failed {}\", e)) }\n"
               "    else if std::path::Path::new(\"marker.txt\").exists() { \"found\".to_string() } else { \"absent\".to_string() }\n"
               "}\n"
               "fn main() {\n"
               "    let a: Vec<String> = std::env::args().collect();\n"
               "    let k: usize = a.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);\n"
               "    println!(\"{}\", x1h_case(k));\n"
               "    println!(\"N:@@NONCE@@\");\n}\n")


def check_battery(rep: Report, image: W.ToolchainImage, scratch: Path):
    sbx = scratch / "sbx_checks"
    base = {"arm": "rust", "ext": "rs", "prelude": "// public prelude (empty)\n", "driver": RUST_DRIVER,
            "entries": [], "expected": ["0", "0", "0"], "run_tests": True}
    # wall: three cases that each sleep 6 s, one 12 s deadline for the whole call
    sol = "pub fn f() -> i32 { std::thread::sleep(std::time::Duration::from_secs(6)); 0 }\n"
    r = C.run_check(image, sbx / secrets.token_hex(8), "rust", sol, base, limits={"wall_s": 12, "cpu_s": 60})
    b, t = r["budget"], r.get("tests", {})
    rep.check("call", "one wall deadline per check call (3 x 6 s cases)",
              b["spent"] == "wall" and b["wall_s_used"] <= 12 + 3 and t.get("passed", 0) < 3,
              f"verdict={r.get('verdict')} budget={json.dumps(b)} passed={t.get('passed')} "
              f"errors={[c.get('error') for c in t.get('cases', [])]}")
    # cpu: three cases that each burn 5 CPU-s, one 8 CPU-s pool for the whole call (build included)
    sol = ("pub fn f() -> i32 { let t = std::time::Instant::now(); let mut x = 0u64;"
           " while t.elapsed().as_secs() < 5 { x = x.wrapping_mul(6364136223846793005).wrapping_add(1); }"
           " (x % 2) as i32 * 0 }\n")
    r = C.run_check(image, sbx / secrets.token_hex(8), "rust", sol, base, limits={"wall_s": 120, "cpu_s": 8})
    b, t = r["budget"], r.get("tests", {})
    rep.check("call", "one CPU pool per check call (3 x 5 CPU-s cases)",
              b["spent"] == "cpu" and b["cpu_s_used"] <= 8 + 0.5 and t.get("passed", 0) < 3,
              f"verdict={r.get('verdict')} budget={json.dumps(b)} passed={t.get('passed')}")
    # Stage B: a fresh sandbox per case
    leak = dict(base, driver=LEAK_DRIVER, expected=["wrote", "absent"])
    r = C.run_check(image, sbx / secrets.token_hex(8), "rust", "pub fn f() -> i32 { 0 }\n", leak,
                    limits={"wall_s": 120, "cpu_s": 60})
    t = r.get("tests", {})
    rep.check("call", "stage B: a fresh sandbox per case (no carry-over)",
              t.get("passed") == 2, f"verdict={r.get('verdict')} tests={json.dumps(t)[:200]}")
    # Mithril arm, Stage A: `mithi check` under LPAC with the allowlisted environment
    mb = {"arm": "mithril", "ext": "mith", "prelude": "fn helper() -> i32 { 1 }\n",
          "driver": "fn x1h_one_0() -> i32 { f() }\n", "entries": [], "expected": [], "run_tests": False}
    r = C.run_check(image, sbx / secrets.token_hex(8), "mithril", "fn f() -> i32 { 0 }\n", mb,
                    limits={"wall_s": 120, "cpu_s": 60})
    rep.check("call", "mithril stage A: mithi check runs under LPAC",
              r.get("verdict") == "accept" and r.get("checker") == "accept",
              f"verdict={r.get('verdict')} checker={r.get('checker')} budget={json.dumps(r.get('budget'))}")
    left = [p.name for p in sbx.iterdir()] if sbx.exists() else []
    rep.check("call", "call directories removed after each check", not left, f"left={left}")


# ----------------------------------------------------------------------------- D: MCP server

def mcp_battery(rep: Report, image: W.ToolchainImage, att_root: Path, repo: Path, python: str):
    """Drive the MCP server over a pipe as Claude Code would, started with ONLY the env block that
    attempt.py generated (plus the OS variables Python itself needs), and assert the no-shell
    surface, the confinement, the opacity of sandbox paths, and the budgets."""
    arm = "rust"
    bundle = {"arm": arm, "ext": "rs", "prelude": "// public prelude (empty)\n",
              "driver": RUST_DRIVER, "entries": [], "expected": ["0"]}
    runs = att_root / "runs"
    att_dir = runs / A.new_attempt_name()
    sbx = att_root / "sbx"
    A.prepare_attempt(att_dir, arm, "pub fn f() -> i32 { todo!() }\n", bundle, python,
                      HERE / "mcp_server.py", image_root=image.root, sandbox_root=sbx)
    gen = json.loads((att_dir / "config" / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["x1"]
    env = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP")
           if k in os.environ}
    env.update(gen["env"])
    errlog_p = att_root / f"server.{att_dir.name}.stderr.log"
    errlog = open(errlog_p, "w", encoding="utf-8")
    proc = subprocess.Popen([gen["command"], *gen["args"]], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=errlog, text=True, env=env, bufsize=1)
    rid = [0]

    def call(method, params=None, notify=False):
        if notify:
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}}) + "\n")
            proc.stdin.flush()
            return None
        rid[0] += 1
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": rid[0], "method": method,
                                     "params": params or {}}) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    def tool(name, args=None):
        r = call("tools/call", {"name": name, "arguments": args or {}})
        if "result" not in r:
            errlog.flush()
            raise RuntimeError(f"tool {name} -> {json.dumps(r)[:300]}\nserver stderr:\n"
                               f"{errlog_p.read_text(encoding='utf-8')[-1500:]}")
        return json.loads(r["result"]["content"][0]["text"])

    try:
        call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
        call("notifications/initialized", notify=True)
        tl = call("tools/list")
        names = {t["name"] for t in tl["result"]["tools"]}
        rep.check("mcp", "only the 8 x1 tools offered",
                  names == {"list_files", "read_file", "write_file", "str_replace", "check",
                            "run_tests", "submit", "abandon"}, ",".join(sorted(names)))
        esc = tool("read_file", {"path": "../../README.md"})
        rep.check("mcp", "read_file cannot escape workspace", "error" in esc, json.dumps(esc)[:120])
        esc2 = tool("read_file", {"path": str(repo / "README.md")})
        rep.check("mcp", "read_file rejects absolute repo path", "error" in esc2, json.dumps(esc2)[:120])
        wbad = tool("write_file", {"path": "prelude.rs", "text": "x"})
        rep.check("mcp", "write_file refuses non-solution", "error" in wbad, json.dumps(wbad)[:120])
        # a compile error: the diagnostics the subject sees must name no attempt directory
        tool("write_file", {"path": "solution.rs", "text": "pub fn f() -> i32 { \"not an int\" }\n"})
        c1 = tool("check")
        diag = c1.get("diagnostics", "")
        rep.check("mcp", "diagnostics name a neutral sandbox path, not the attempt",
                  c1.get("verdict") == "reject" and bool(diag) and att_dir.name not in diag
                  and str(att_dir) not in diag and "harness" not in diag and str(sbx) in diag,
                  f"verdict={c1.get('verdict')} attempt_named={att_dir.name in diag} "
                  f"sbx_named={str(sbx) in diag}")
        w = tool("write_file", {"path": "solution.rs", "text": "pub fn f() -> i32 { 0 }\n"})
        rep.check("mcp", "write_file writes the solution", w.get("ok") is True, json.dumps(w)[:120])
        c = tool("run_tests")
        rep.check("mcp", "sandboxed check runs + tests pass",
                  c.get("verdict") == "accept" and c.get("tests", {}).get("passed") == 1,
                  f"verdict={c.get('verdict')} tests={c.get('tests')} budget={c.get('budget')}")
        seq = []
        for _ in range(8):
            r = tool("check")
            seq.append(r.get("error") or r.get("verdict"))
            if r.get("error"):
                break
        # 2 calls used above; calls 3..8 succeed, the 9th is refused
        rep.check("mcp", "8-check budget enforced (9th refused)",
                  seq == ["accept"] * 6 + ["budget_exhausted"], ",".join(seq))
        s = tool("submit")
        rep.check("mcp", "submit ends the attempt", s.get("ended") == "submit", json.dumps(s)[:120])
        after = tool("check")
        rep.check("mcp", "no checks after submit", after.get("error") == "attempt_ended", json.dumps(after)[:120])
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.wait(timeout=30)
        errlog.close()
    inside = [str(p.relative_to(att_dir)) for p in att_dir.rglob("*") if p.is_dir() and p.name in ("sandbox", "sbx")]
    left = [p.name for p in sbx.iterdir()] if sbx.exists() else []
    rep.check("mcp", "no sandbox directory in the attempt tree; none left",
              not inside and not left, f"inside={inside} left_in_sbx={left}")


# ----------------------------------------------------------------------------- E: configuration

def config_battery(rep: Report, att_root: Path, python: str, image_root: Path):
    runs = att_root / "runs"
    sbx = att_root / "sbx"
    att = runs / A.new_attempt_name()
    bundle = {"arm": "rust", "ext": "rs", "prelude": "", "driver": "", "entries": [], "expected": []}
    launch = A.prepare_attempt(att, "rust", "fn f(){}\n", bundle, python, HERE / "mcp_server.py",
                               image_root=image_root, sandbox_root=sbx)
    cfg = att / "config"
    import re
    agent = (cfg / "agents" / "x1-subject.md").read_text(encoding="utf-8")
    m = re.search(r"^tools:\s*\[(.*?)\]", agent, re.MULTILINE)
    listed = {t.strip() for t in m.group(1).split(",")} if m else set()
    aj = json.loads((cfg / "agents.json").read_text(encoding="utf-8"))
    rep.check("config", "agent lists only mcp__x1__* tools (md + --agents JSON)",
              listed == set(A.X1_TOOLS) and set(aj["x1-subject"]["tools"]) == set(A.X1_TOOLS),
              ",".join(sorted(listed)))
    body = agent.split("---", 2)[2].strip()
    app = (cfg / "append_system_prompt.md").read_text(encoding="utf-8")
    rep.check("config", "agent prompt empty; instructions appended (2.3 item 4)",
              body == "" and aj["x1-subject"]["prompt"] == "" and app == A.COMMON_INSTRUCTIONS
              and after_flag(launch["argv_sketch"], "--append-system-prompt-file") == str(cfg / "append_system_prompt.md"),
              f"md_body_len={len(body)} json_prompt_len={len(aj['x1-subject']['prompt'])} append_len={len(app)}")
    settings = json.loads((cfg / "settings.json").read_text(encoding="utf-8"))
    deny = settings["permissions"]["deny"]
    rep.check("config", "settings deny built-ins, never an mcp__ pattern",
              {"Bash", "Write", "Read", "WebFetch", "Task"}.issubset(set(deny))
              and not any(d.startswith("mcp__") or d == "*" for d in deny)
              and settings["permissions"]["allow"] == A.X1_TOOLS, ",".join(deny))
    rep.check("config", "settings register only the x1 MCP server",
              list(settings["mcpServers"].keys()) == ["x1"] and settings.get("disableAllHooks") is True,
              json.dumps(list(settings["mcpServers"].keys())))
    argv = launch["argv_sketch"]

    def after(flag):
        return after_flag(argv, flag)
    agents_arg = after("--agents")
    try:
        agents_ok = set(json.loads(agents_arg)["x1-subject"]["tools"]) == set(A.X1_TOOLS)
    except Exception:
        agents_ok = False
    rep.check("config", "launch selects x1-subject; no built-in tools",
              after("--agent") == "x1-subject" and agents_ok and after("--tools") == ""
              and "--strict-mcp-config" in argv and after("--mcp-config") == str(cfg / ".mcp.json"),
              " ".join(a if len(a) < 40 else a[:37] + "..." for a in argv[3:13]))
    mj = json.loads((cfg / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["x1"]["env"]
    want = {"X1_ATTEMPT_DIR", "X1_IMAGE_ROOT", "X1_SANDBOX_ROOT"}
    rep.check("config", "env blocks carry attempt, image and sandbox roots",
              want <= set(mj) and want <= set(settings["mcpServers"]["x1"]["env"]) and want <= set(launch["env"])
              and mj["X1_IMAGE_ROOT"] == str(image_root) and not A.is_within(Path(mj["X1_SANDBOX_ROOT"]), att),
              json.dumps(sorted(mj)))
    rep.check("config", "launch isolates CLAUDE_CONFIG_DIR per attempt",
              launch["env"]["CLAUDE_CONFIG_DIR"] == str(cfg), "config/ of the attempt")
    # refusal under project instructions or a repository
    results = {}
    for name in A.INSTRUCTION_NAMES:
        host = att_root / f"host_{secrets.token_hex(4)}"
        host.mkdir(parents=True)
        if name in (".claude", ".git"):
            (host / name).mkdir()
        else:
            (host / name).write_text("# planted instructions\n", encoding="utf-8")
        try:
            A.prepare_attempt(host / "deep" / A.new_attempt_name(), "rust", "", bundle, python,
                              HERE / "mcp_server.py", image_root=image_root, sandbox_root=sbx)
            results[name] = "accepted"
        except RuntimeError as e:
            results[name] = "refused" if "project instructions" in str(e) else f"other: {e}"
    rep.check("config", "refuses attempts under CLAUDE.md/AGENTS.md/.claude/.git",
              all(v == "refused" for v in results.values()), json.dumps(results))
    try:
        A.prepare_attempt(runs / "item-D-Q4-1-mithril-r1", "rust", "", bundle, python, HERE / "mcp_server.py",
                          image_root=image_root, sandbox_root=sbx)
        named = "accepted"
    except RuntimeError as e:
        named = "refused" if "not opaque" in str(e) else f"other: {e}"
    rep.check("config", "refuses a labelled (non-opaque) attempt name", named == "refused", named)
    # finish: everything moves to the private store, verified, nothing stays in the run tree
    (att / "work" / "solution.rs").write_text("pub fn f() -> i32 { 0 }\n", encoding="utf-8")
    store = att_root / "store"
    before = {n: A.tree_hashes(att / n) for n in A.FINISH_ITEMS if (att / n).exists()}
    fin = A.finish_attempt(att, store)
    after_h = {n: A.tree_hashes(store / att.name / n) for n in before}
    rep.check("config", "finish_attempt moves records, verified by hash",
              fin["ok"] and before == after_h and not att.exists() and set(fin["deleted"]) == set(before),
              f"ok={fin['ok']} deleted={fin['deleted']} left={fin.get('left_in_run_tree')} run_tree_exists={att.exists()}")


# ----------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mithi", required=True)
    ap.add_argument("--rustc", default=str(DEFAULT_RUSTC))
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--attempt-root", default=None)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)
    rustc, mithi, repo, out = Path(a.rustc), Path(a.mithi), Path(a.repo), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    sysdrive = os.environ.get("SystemDrive", "C:")
    att_root = Path(a.attempt_root) if a.attempt_root else Path(sysdrive + "\\") / f"x1iso-negtest-{secrets.token_hex(4)}"
    made_att_root = not att_root.exists()
    hits = A.instruction_ancestors(att_root)
    if hits:
        raise SystemExit(f"--attempt-root {att_root} lies under {hits[:3]}; choose another")
    scratch = Path(tempfile.mkdtemp(prefix="x1iso_negtest_"))
    rep = Report()
    image = None
    probe_sha = None
    t0 = time.monotonic()
    stale_before = W.stale_profiles()
    try:
        probe = build_probe(rustc, scratch / "probe")
        probe_sha = hashlib.sha256(probe.read_bytes()).hexdigest()
        image = W.ToolchainImage.build(scratch / "image", rustc.parents[1], mithi,
                                       extra={"probe/probe.exe": probe})
        print("image_id", image.image_id[:16], flush=True)
        # Sandboxes, the other attempt and the attempts all live under the attempt root: outside the
        # user profile, the kind of place attempt.py requires for real runs.
        att_root.mkdir(parents=True, exist_ok=True)
        other = att_root / "runs" / A.new_attempt_name() / "work"
        other.mkdir(parents=True, exist_ok=True)
        (other / "secret_of_other_attempt.txt").write_text("another attempt's workspace\n")
        lst = socket.socket()
        lst.bind(("127.0.0.1", 0))
        lst.listen(16)
        port = lst.getsockname()[1]
        try:
            ctl = subprocess.run([str(image.probe), "connect", f"127.0.0.1:{port}"], capture_output=True,
                                 text=True, timeout=30).stdout.strip()
            rep.check("control", "loopback listener reachable outside the sandbox", ctl.startswith("OK connect"), ctl)
            sandbox_battery(rep, image, att_root, repo, other / "secret_of_other_attempt.txt", True, port)
            sandbox_battery(rep, image, att_root, repo, other / "secret_of_other_attempt.txt", False, port)
        finally:
            lst.close()
        job_battery(rep, image, att_root)
        check_battery(rep, image, att_root)
        mcp_battery(rep, image, att_root, repo, python)
        config_battery(rep, att_root, python, image.root)
        stale = [s for s in W.stale_profiles() if s not in stale_before]
        pk = Path(os.environ.get("LOCALAPPDATA", "")) / "Packages"
        folders = [p.name for p in pk.iterdir() if p.name.startswith("x1iso.")] if pk.exists() else []
        rep.check("cleanup", "no x1iso AppContainer profile or folder left", not stale and not folders,
                  f"profiles={stale[:5]} folders={folders[:5]}")
    finally:
        report = {"schema": "x1iso-negtest/2",
                  "when_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "machine": os.environ.get("COMPUTERNAME"),
                  # the interpreter's version only; its path (in the user profile) is not recorded
                  "python": f"{platform.python_implementation()} {platform.python_version()}",
                  "os": platform.platform(),
                  "sandbox_version": W.SANDBOX_VERSION,
                  "image_id": image.image_id if image else None,
                  "probe_sha256": probe_sha,
                  "duration_s": round(time.monotonic() - t0, 1),
                  "all_pass": rep.ok(), "n": len(rep.rows),
                  "n_pass": sum(1 for r in rep.rows if r["verdict"] == "PASS"), "rows": rep.rows}
        A.write_json(out / "negtest.json", report)
        if not a.keep:
            for d in (scratch, att_root if made_att_root else None):
                if d is None or not d.exists():
                    continue
                try:
                    W._icacls(str(d), "/reset", "/T", "/C", "/Q")
                except Exception:
                    pass
                shutil.rmtree(d, ignore_errors=True)
    print(f"\n{sum(1 for r in rep.rows if r['verdict'] == 'PASS')}/{len(rep.rows)} PASS -> {out / 'negtest.json'}")
    return 0 if rep.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
