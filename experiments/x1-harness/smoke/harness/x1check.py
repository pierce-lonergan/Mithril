#!/usr/bin/env python3
"""X1 smoke-run check wrapper (development items only; not the held-out harness).

Usage (the subject runs exactly these, through its Bash tool):
    python x1check.py <attempt_dir> check [--tests]   one checker call (counts against the budget)
    python x1check.py <attempt_dir> submit            ends the attempt; the submitted file is final
    python x1check.py <attempt_dir> abandon [reason]  ends the attempt as abandoned

What it enforces and records (X1 DESIGN 7, 12.2; X1-amendment-1 2.3):
- at most `budget` (8) checker calls per attempt; the 9th and later return budget_exhausted
  (logged, and they do not run the checker). The call count is taken from the hash-chained log
  (one `start` entry per call, minus refunded calls), never from state.json, which is only a cache;
- a wall budget (RUN.json `wall_budget_s`, 45 min) from the attempt's first harness command: after
  it, check and submit return wall_budget_exhausted and the attempt ends as `budget_wall`;
- every call, including refused ones, is appended to <attempt>/harness/log.jsonl, hash-chained
  (each line carries the SHA-256 of the previous line), with the workspace hash and a snapshot of
  the solution file at that call; a broken chain refuses further checks (log_integrity_failure);
- the build and the visible cases run in a fresh directory outside the attempt tree
  (<run root>/b/<random>), deleted afterwards; the prelude is the harness copy
  (<attempt>/harness/prelude.<ext>), never the subject-writable work/ copy;
- a wrapper failure before the subject's code ran is refunded (the call does not count);
- `submit` copies the solution file to <attempt>/harness/submitted/ and ends the attempt; after
  `submit` or `abandon` every command returns attempt_ended. An abandon reason is reduced to
  letters, digits, spaces and , . : _ ( ) < > = + - and 200 characters.

The checker per arm (same flags as the scorer's acceptance check and oracle):
- mithril: `mithi check --json --subset agent --prelude prelude.mith solution.mith <driver>`;
- rust: `rustc --edition 2021 -C opt-level=0 -C overflow-checks=on -C debug-assertions=on
  -F unsafe_code` on a crate made of prelude.rs, solution.rs and the harness driver, plus a lexical
  static gate on solution.rs (DESIGN 11.4 list, regex-based: a heuristic, not a syn pass).
Visible tests (`check --tests`) run each visible case in its own process and compare the printed
result with the expected value outside the process; a result without the run's nonce line fails.

Isolation limits: this wrapper runs with the user's rights on the laptop. It is not the DESIGN 11
sandbox (no container, no network cut, no CPU-time limit; a wall-clock timeout only). Development
items only.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WRAPPER_VERSION = "x1check/2"
MAX_DIAG_CHARS = 6000
MAX_DIAGS = 12
DEFAULT_WALL_BUDGET_S = 45 * 60
REASON_RE = re.compile(r"[^A-Za-z0-9 ,.:_()<>=+\-]")


# ----------------------------------------------------------------------------- small utilities

def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def sha256_text(t: str) -> str:
    return sha256_bytes(t.encode("utf-8"))


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)


def truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n] + f"\n... [truncated {len(s) - n} chars]"


def first_difference(exp: str, got: str) -> str:
    """Where two printed results first differ, by comma-separated field (results are field lists)."""
    e, g = exp.replace(";", ",").replace(":", ",").split(","), got.replace(";", ",").replace(":", ",").split(",")
    for i in range(max(len(e), len(g))):
        a = e[i] if i < len(e) else "<missing>"
        b = g[i] if i < len(g) else "<missing>"
        if a != b:
            return f"field {i}: expected {a}, got {b}"
    return "none"


# ----------------------------------------------------------------------------- lexical helpers

RAW_STR_RE = re.compile(r'b?r(#*)"')


def strip_comments_and_strings(src: str) -> str:
    """Remove // and /* */ comments (nesting-aware) and the contents of string, raw string and char
    literals.

    Good enough for the lexical gate and the hole count on small solution files; it is a heuristic.
    Raw strings (r"..", r#".."#, br"..") are consumed to their own terminator, so a backslash or a
    quote inside one cannot hide the code that follows it.
    """
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in "rb" and (i == 0 or not (src[i - 1].isalnum() or src[i - 1] == "_")):
            m = RAW_STR_RE.match(src, i)
            if m:
                term = '"' + m.group(1)
                j = src.find(term, m.end())
                i = n if j < 0 else j + len(term)
                out.append('""')
                continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            depth, i = 1, i + 2
            while i < n and depth:
                if src.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif src.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            out.append(" ")
            continue
        if c == '"':
            i += 1
            while i < n and src[i] != '"':
                i += 2 if src[i] == "\\" else 1
            i += 1
            out.append('""')
            continue
        if c == "'" and i + 2 < n and (src[i + 2] == "'" or (src[i + 1] == "\\" and "'" in src[i + 2:i + 12])):
            # a char literal ('a' or an escape); lifetimes ('a without a closing quote) fall through
            j = src.find("'", i + 2 if src[i + 1] != "\\" else i + 3)
            i = j + 1 if j > 0 else i + 1
            out.append("' '")
            continue
        out.append(c)
        i += 1
    return "".join(out)


HOLE_RE = re.compile(r"\b(todo|unimplemented)\s*!")

RUST_GATE = [
    (re.compile(r"\binclude(_bytes|_str)?\s*!"), "include!/include_bytes!/include_str!"),
    (re.compile(r"#\s*\[\s*path\b"), "#[path]"),
    (re.compile(r"\b(option_)?env\s*!"), "env!/option_env!"),
    (re.compile(r"\bextern\s+crate\b"), "extern crate"),
    (re.compile(r"\b(global_)?asm\s*!"), "asm!/global_asm!"),
    (re.compile(r"\bstd\s*::\s*(fs|env|process|net|os)\b"), "std::fs/env/process/net/os path"),
    (re.compile(r"\bcore\s*::\s*arch\b"), "core::arch"),
    (re.compile(r"\bunsafe\b"), "unsafe (also refused by -F unsafe_code)"),
    # renames and globs that would hide a std path from the patterns above (review 1, finding 3)
    (re.compile(r"\b(std|core|alloc)\s+as\b"), "renamed std/core/alloc (`std as x`)"),
    (re.compile(r"\buse\b[^;]*\bself\s+as\b"), "`self as` rename in a use"),
    (re.compile(r"\b(std|core)\s*::\s*\*"), "glob import of std/core (`std::*`)"),
    (re.compile(r"\bmacro_rules\s*!"), "macro_rules! (path construction in macros)"),
    (re.compile(r"\balloc\s*::"), "alloc:: path"),
    (re.compile(r"\buse\s+(::\s*)?alloc\b"), "use alloc"),
    (re.compile(r"\br#[A-Za-z_]"), "raw identifier (r#name)"),
]

STD_GROUP_RE = re.compile(r"\b(std|core)\s*::\s*\{")
STD_GROUP_BANNED = re.compile(r"\b(fs|env|process|net|os|arch)\b")


def _std_group_hits(s: str) -> list:
    """`std::{...}` groups, nested braces included: a banned module anywhere inside, or a
    top-level `*` or `self as` item."""
    hits = []
    for m in STD_GROUP_RE.finditer(s):
        i, depth, start = m.end(), 1, m.end()
        while i < len(s) and depth:
            depth += {"{": 1, "}": -1}.get(s[i], 0)
            i += 1
        body = s[start:i - 1]
        line = s.count("\n", 0, m.start()) + 1
        if STD_GROUP_BANNED.search(body):
            hits.append({"code": "E-X1-GATE", "what": "grouped use of std::fs/env/process/net/os", "line": line})
        # top-level items of the group
        items, d, cur = [], 0, ""
        for ch in body:
            if ch == "{":
                d += 1
            elif ch == "}":
                d -= 1
            if ch == "," and d == 0:
                items.append(cur.strip())
                cur = ""
            else:
                cur += ch
        items.append(cur.strip())
        if any(it == "*" or re.match(r"self\s+as\b", it) for it in items):
            hits.append({"code": "E-X1-GATE", "what": "glob or `self as` item in a std group", "line": line})
    return hits


def count_holes(src: str) -> int:
    return len(HOLE_RE.findall(strip_comments_and_strings(src)))


def rust_static_gate(src: str) -> list:
    s = strip_comments_and_strings(src)
    hits = []
    for rx, what in RUST_GATE:
        for m in rx.finditer(s):
            line = s.count("\n", 0, m.start()) + 1
            hits.append({"code": "E-X1-GATE", "what": what, "line": line})
    hits += _std_group_hits(s)
    return hits


# ----------------------------------------------------------------------------- toolchain runs

def run_proc(argv, cwd, timeout, env=None):
    t0 = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=str(cwd), capture_output=True, timeout=timeout, env=env)
        return {
            "rc": p.returncode,
            "stdout": p.stdout.decode("utf-8", "replace"),
            "stderr": p.stderr.decode("utf-8", "replace"),
            "timeout": False,
            "wall_s": round(time.monotonic() - t0, 3),
        }
    except subprocess.TimeoutExpired as e:
        return {
            "rc": None,
            "stdout": (e.stdout or b"").decode("utf-8", "replace"),
            "stderr": (e.stderr or b"").decode("utf-8", "replace"),
            "timeout": True,
            "wall_s": round(time.monotonic() - t0, 3),
        }


def rust_env(cfg) -> dict:
    env = dict(os.environ)
    for k, v in (cfg.get("rust_env") or {}).items():
        env[k] = v
    return env


def build(arm: str, cfg: dict, bdir: Path, solution: str, prelude: str, driver: str, timeout: int) -> dict:
    """Run the arm's checker on solution + prelude + driver in a fresh build directory.

    Returns {"verdict": "accept"|"reject"|"internal-error"|"timeout", "diagnostics": ..., "exe": path?}.
    """
    if bdir.exists():
        shutil.rmtree(bdir, ignore_errors=True)
    bdir.mkdir(parents=True)
    if arm == "mithril":
        (bdir / "prelude.mith").write_text(prelude, encoding="utf-8")
        (bdir / "solution.mith").write_text(solution, encoding="utf-8")
        (bdir / "x1_driver.mith").write_text(driver, encoding="utf-8")
        r = run_proc([cfg["mithi"], "check", "--json", "--subset", "agent", "--prelude", "prelude.mith",
                      "solution.mith", "x1_driver.mith"], bdir, timeout)
        if r["timeout"]:
            return {"verdict": "timeout", "diagnostics": [], "wall_s": r["wall_s"]}
        line = r["stdout"].strip().splitlines()[-1] if r["stdout"].strip() else ""
        try:
            j = json.loads(line)
        except ValueError:
            return {"verdict": "internal-error", "diagnostics": [truncate(r["stdout"] + r["stderr"], 2000)],
                    "wall_s": r["wall_s"]}
        if j.get("verdict") == "internal-error" or r["rc"] == 3:
            return {"verdict": "internal-error", "diagnostics": [], "wall_s": r["wall_s"]}
        diags = []
        for d in j.get("diagnostics", [])[:MAX_DIAGS]:
            at = d.get("at") or {}
            diags.append({k: v for k, v in {
                "code": d.get("code"), "severity": d.get("severity"), "message": d.get("message"),
                "loc": at.get("loc"), "anchor": at.get("anchor"), "notes": d.get("notes") or None,
            }.items() if v})
        more = len(j.get("diagnostics", [])) - len(diags)
        if more > 0:
            diags.append({"note": f"{more} more diagnostics not shown"})
        return {"verdict": j.get("verdict"), "primary": j.get("primary"), "diagnostics": diags,
                "mithi_std_sha256": j.get("std_sha256"), "wall_s": r["wall_s"]}
    if arm == "rust":
        (bdir / "prelude.rs").write_text(prelude, encoding="utf-8")
        (bdir / "solution.rs").write_text(solution, encoding="utf-8")
        (bdir / "main.rs").write_text(driver, encoding="utf-8")
        exe = bdir / ("x1drv.exe" if os.name == "nt" else "x1drv")
        argv = [cfg["rustc"], "--edition", "2021", "--crate-name", "x1drv", "--crate-type", "bin",
                "-C", "opt-level=0", "-C", "debuginfo=0", "-C", "overflow-checks=on",
                "-C", "debug-assertions=on", "-C", "codegen-units=1", "-F", "unsafe_code",
                "--color", "never", "-o", str(exe), "main.rs"]
        r = run_proc(argv, bdir, timeout, env=rust_env(cfg))
        if r["timeout"]:
            return {"verdict": "timeout", "diagnostics": [], "wall_s": r["wall_s"]}
        text = r["stderr"].strip()
        verdict = "accept" if r["rc"] == 0 and exe.exists() else "reject"
        out = {"verdict": verdict, "diagnostics": [truncate(text, MAX_DIAG_CHARS)] if text else [],
               "wall_s": r["wall_s"]}
        if verdict == "accept":
            out["exe"] = str(exe)
        return out
    raise ValueError(arm)


def parse_mithi_run(stdout: str):
    """`mithi run` prints the entry's String Debug-quoted; our outputs contain no escapes."""
    s = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return None


def run_visible_case(arm: str, cfg: dict, bdir: Path, k: int, nonce: str, timeout: int) -> dict:
    """Run visible case k in its own process; returns {"got": str|None, "error": str|None}."""
    if arm == "mithril":
        r = run_proc([cfg["mithi"], "run", "--subset", "agent", "--prelude", "prelude.mith", "--entry",
                      f"x1h_one_{k}", "solution.mith", "x1_driver.mith"], bdir, timeout)
        if r["timeout"]:
            return {"got": None, "error": f"timeout after {timeout} s"}
        body = parse_mithi_run(r["stdout"]) if r["rc"] == 0 else None
        if body is None:
            return {"got": None, "error": truncate((r["stdout"] + r["stderr"]).strip(), 1500) or f"exit {r['rc']}"}
        parts = body.split("|")
        if len(parts) != 2 or parts[-1] != "N:" + nonce:
            return {"got": None, "error": "result record incomplete (no nonce line)"}
        return {"got": parts[0], "error": None}
    exe = bdir / ("x1drv.exe" if os.name == "nt" else "x1drv")
    r = run_proc([str(exe), str(k)], bdir, timeout)
    if r["timeout"]:
        return {"got": None, "error": f"timeout after {timeout} s"}
    lines = r["stdout"].replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if r["rc"] != 0 or len(lines) != 2 or lines[-1] != "N:" + nonce:
        err = (r["stderr"] or "").strip()
        return {"got": None, "error": truncate(err, 1500) or f"exit {r['rc']}; result record incomplete"}
    return {"got": lines[0], "error": None}


# ----------------------------------------------------------------------------- the attempt log

GENESIS = "sha256:" + "0" * 64


def read_log(log_p: Path):
    """The attempt log's entries and whether its hash chain verifies.

    Returns (entries, {"ok": bool, "entries": n, "broken_at": i?}). A line that is not JSON breaks
    the chain at that line.
    """
    entries = []
    if not log_p.exists():
        return entries, {"ok": True, "entries": 0}
    prev = GENESIS
    for i, raw in enumerate(l for l in log_p.read_bytes().splitlines() if l.strip()):
        try:
            e = json.loads(raw)
        except ValueError:
            return entries, {"ok": False, "entries": i, "broken_at": i}
        if e.get("prev") != prev:
            return entries, {"ok": False, "entries": i, "broken_at": i}
        prev = sha256_bytes(raw)
        entries.append(e)
    return entries, {"ok": True, "entries": len(entries)}


def call_accounting(entries: list) -> dict:
    """Checker calls as the log records them: one `start` entry per call; a `refund` entry (a
    wrapper failure before the subject's code ran) cancels its call. `seq` numbers every started
    call, refunded or not; `call` is the budget count."""
    starts = [e for e in entries if e.get("cmd") == "check" and e.get("phase") == "start"]
    refunded = {e.get("seq") for e in entries if e.get("cmd") == "check" and e.get("phase") == "refund"}
    counted = [e for e in starts if e.get("seq") not in refunded]
    ended = [e for e in entries if e.get("ended")]
    return {"used": len(counted), "next_seq": len(starts) + 1, "refunded": len(refunded),
            "counted_calls": [e.get("call") for e in counted],
            "first_utc": entries[0].get("t_utc") if entries else None,
            "ended": ended[0].get("ended") if ended else None}


def _parse_utc(s: str):
    return _dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=_dt.timezone.utc)


# ----------------------------------------------------------------------------- the attempt state

class Attempt:
    def __init__(self, adir: Path):
        self.dir = adir.resolve()
        self.meta = read_json(self.dir / "attempt.json")
        self.root = self.dir.parent.parent
        self.cfg = read_json(self.root / "RUN.json")
        self.h = self.dir / "harness"
        self.work = self.dir / "work"
        self.arm = self.meta["arm"]
        self.ext = self.meta["ext"]
        self.state_p = self.h / "state.json"
        self.log_p = self.h / "log.jsonl"
        self.lock_p = self.h / "lock"

    # one command at a time per attempt. A lock older than STALE_LOCK_S is left by a wrapper that
    # was killed (for example by the caller's own command timeout) and is broken; no command of
    # this wrapper legitimately runs that long. (No PID probe: os.kill on Windows terminates.)
    STALE_LOCK_S = 300

    def lock(self):
        deadline = time.monotonic() + 60
        while True:
            try:
                fd = os.open(str(self.lock_p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.lock_p) > self.STALE_LOCK_S:
                        os.remove(self.lock_p)
                        continue
                except OSError:
                    continue
                if time.monotonic() > deadline:
                    raise RuntimeError("attempt lock held by another command for more than 60 s")
                time.sleep(0.2)

    def unlock(self):
        try:
            os.remove(self.lock_p)
        except OSError:
            pass

    def state(self):
        """state.json is a cache for `status`; the log decides calls and endings."""
        if self.state_p.exists():
            try:
                return read_json(self.state_p)
            except ValueError:
                pass
        return {"calls": 0, "refused_calls": 0, "ended": False, "end_reason": None, "first_call_utc": None}

    def save_state(self, st):
        write_json(self.state_p, st)

    def solution_text(self):
        p = self.work / f"solution.{self.ext}"
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace"), True
        return (self.work / f"stub.{self.ext}").read_text(encoding="utf-8"), False

    def prelude_text(self):
        """The harness copy of the prelude (the work/ copy is subject-writable). Returns the text
        and whether the work/ copy differs from it."""
        hp = self.h / f"prelude.{self.ext}"
        text = hp.read_text(encoding="utf-8")
        wp = self.work / f"prelude.{self.ext}"
        try:
            modified = wp.read_text(encoding="utf-8", errors="replace") != text
        except OSError:
            modified = True
        return text, modified

    def build_dir(self, seq: int) -> Path:
        """A fresh directory outside the attempt tree for one call's build and runs."""
        base = Path(self.cfg.get("build_base") or (self.root / "b"))
        base.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=f"{seq:02d}", dir=str(base)))

    def wall_exceeded(self, acct: dict) -> bool:
        budget = int(self.cfg.get("wall_budget_s") or DEFAULT_WALL_BUDGET_S)
        if not acct["first_utc"]:
            return False
        elapsed = (_dt.datetime.now(_dt.timezone.utc) - _parse_utc(acct["first_utc"])).total_seconds()
        return elapsed > budget

    def log(self, entry: dict):
        prev = GENESIS
        if self.log_p.exists():
            data = [l for l in self.log_p.read_bytes().splitlines() if l.strip()]
            if data:
                prev = sha256_bytes(data[-1])
        entry = dict(entry)
        entry["prev"] = prev
        entry["t_utc"] = utcnow()
        entry["wrapper"] = WRAPPER_VERSION
        line = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        with open(self.log_p, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")

    def end(self, how: str, reason: str = "") -> dict:
        """End the attempt: submit (the file is final), abandon, or budget_wall."""
        src, written = self.solution_text()
        sub = self.h / "submitted" if how == "submit" else self.h / "final"
        sub.mkdir(parents=True, exist_ok=True)
        (sub / f"solution.{self.ext}").write_text(src, encoding="utf-8")
        acct = call_accounting(read_log(self.log_p)[0])
        st = self.state()
        st.update({"ended": True, "end_reason": how, "ended_utc": utcnow(), "calls": acct["used"]})
        self.save_state(st)
        self.log({"cmd": how, "ended": how, "written": written,
                  "final_artifact_hash": sha256_text(src), "reason": reason or None, "calls": acct["used"]})
        return {"final_artifact_hash": sha256_text(src)}


def _wall_reply(a: Attempt) -> dict:
    a.end("budget_wall")
    return {"error": "wall_budget_exhausted",
            "note": "the attempt's time budget is used up; the attempt has ended. Reply with your final line and stop."}


def cmd_check(a: Attempt, run_tests: bool) -> dict:
    entries, chain = read_log(a.log_p)
    acct = call_accounting(entries)
    st = a.state()
    budget = int(a.meta.get("budget", 8))
    if not chain["ok"]:
        a.log({"cmd": "check", "refused": "log_integrity_failure", "chain": chain})
        return {"error": "log_integrity_failure",
                "note": "the attempt log failed its integrity check; no further checks. You may still submit."}
    if st.get("ended") or acct["ended"]:
        a.log({"cmd": "check", "refused": "attempt_ended"})
        return {"error": "attempt_ended", "end_reason": st.get("end_reason") or acct["ended"]}
    if a.wall_exceeded(acct):
        return _wall_reply(a)
    used = acct["used"]
    if used >= budget:
        st["refused_calls"] = st.get("refused_calls", 0) + 1
        st["calls"] = used
        a.save_state(st)
        a.log({"cmd": "check", "refused": "budget_exhausted", "calls": used,
               "state_calls_cache": st.get("calls")})
        return {"error": "budget_exhausted", "budget": budget,
                "hint": "no checker calls left; submit or abandon"}
    k, s = used + 1, acct["next_seq"]
    a.log({"cmd": "check", "phase": "start", "seq": s, "call": k, "tests": run_tests})
    st.update({"calls": k})
    if not st.get("first_call_utc"):
        st["first_call_utc"] = acct["first_utc"] or utcnow()
    a.save_state(st)

    code_ran = False
    bdir = None
    try:
        src, written = a.solution_text()
        snap = a.h / "snapshots" / f"s{s:02d}_call{k}.{a.ext}"
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text(src, encoding="utf-8")
        vis = read_json(a.h / "visible.json")
        prelude, prelude_modified = a.prelude_text()
        nonce = secrets.token_hex(8)
        driver = vis["driver"].replace("@@NONCE@@", nonce)
        bdir = a.build_dir(s)
        t0 = time.monotonic()
        res = {"call": k, "budget": budget, "remaining": budget - k, "arm": a.arm,
               "file": f"solution.{a.ext}" + ("" if written else " (not written yet: the stub was checked)")}
        gate = rust_static_gate(src) if a.arm == "rust" else []
        chk = build(a.arm, a.cfg, bdir, src, prelude, driver, timeout=int(a.cfg.get("check_timeout_s", 60)))
        res["checker"] = {k2: v for k2, v in chk.items() if k2 not in ("exe", "wall_s")}
        res["static_gate"] = {"verdict": "fail" if gate else "pass", "hits": gate}
        res["holes"] = count_holes(src)
        tests = None
        if run_tests:
            if chk["verdict"] != "accept" or gate:
                tests = {"run": False, "why": "the checker or the static gate rejected the file"}
            else:
                cases = []
                timed_out = False
                code_ran = True
                for i, exp in enumerate(vis["expected"]):
                    if timed_out:
                        # keep one call well inside a caller's 2-minute command timeout
                        cases.append({"case": i, "ok": False, "error": "not run: an earlier case timed out"})
                        continue
                    r = run_visible_case(a.arm, a.cfg, bdir, i, nonce, timeout=int(a.cfg.get("case_timeout_s", 10)))
                    timed_out = bool(r["error"] and r["error"].startswith("timeout"))
                    ok = r["error"] is None and r["got"] == exp
                    c = {"case": i, "ok": ok}
                    if not ok:
                        c["expected"] = truncate(exp, 400)
                        if r["got"] is not None:
                            c["got"] = truncate(r["got"], 400)
                            c["first_difference"] = first_difference(exp, r["got"])
                        if r["error"]:
                            c["error"] = r["error"]
                    cases.append(c)
                npass = sum(1 for c in cases if c["ok"])
                tests = {"run": True, "passed": npass, "failed": len(cases) - npass, "cases": cases}
            res["tests"] = tests
        wall = round(time.monotonic() - t0, 3)
    except Exception as e:  # an infrastructure failure of the wrapper, never a verdict
        if not code_ran:
            a.log({"cmd": "check", "phase": "refund", "seq": s, "call": k, "infra_error": repr(e)[:500]})
            st = a.state()
            st["calls"] = k - 1
            a.save_state(st)
            return {"error": "harness_failure", "detail": repr(e)[:500], "refunded": True,
                    "note": "infrastructure failure before your code ran; this call was not counted"}
        a.log({"cmd": "check", "phase": "infra", "seq": s, "call": k, "infra_error": repr(e)[:500]})
        return {"error": "harness_failure", "detail": repr(e)[:500], "refunded": False,
                "note": "infrastructure failure after your code started; this call counted"}
    finally:
        if bdir is not None:
            shutil.rmtree(bdir, ignore_errors=True)
    out_text = json.dumps(res, sort_keys=True)
    a.log({
        "cmd": "check", "phase": "done", "seq": s, "call": k, "tests": run_tests, "written": written,
        "workspace_hash": sha256_text(src), "out_hash": sha256_text(out_text),
        "verdict": chk["verdict"], "primary": chk.get("primary"), "static_gate": "fail" if gate else "pass",
        "holes": res["holes"], "prelude_work_copy_modified": prelude_modified,
        "tests_passed": None if not tests or not tests.get("run") else tests["passed"],
        "tests_failed": None if not tests or not tests.get("run") else tests["failed"],
        "wall_s": wall,
    })
    return res


def cmd_end(a: Attempt, how: str, reason: str) -> dict:
    entries, _chain = read_log(a.log_p)
    acct = call_accounting(entries)
    st = a.state()
    if st.get("ended") or acct["ended"]:
        a.log({"cmd": how, "refused": "attempt_ended"})
        return {"error": "attempt_ended", "end_reason": st.get("end_reason") or acct["ended"]}
    if a.wall_exceeded(acct):
        return _wall_reply(a)
    r = a.end(how, REASON_RE.sub("", reason or "")[:200])
    return {"ok": True, "ended": how, "final_artifact_hash": r["final_artifact_hash"],
            "note": "the attempt has ended; reply with your final line and stop"}


def main(argv) -> int:
    if len(argv) < 3 or argv[2] not in ("check", "submit", "abandon"):
        print(json.dumps({"error": "usage: x1check.py <attempt_dir> check [--tests] | submit | abandon ['reason']"}))
        return 2
    a = Attempt(Path(argv[1]))
    a.lock()
    try:
        if argv[2] == "check":
            out = cmd_check(a, "--tests" in argv[3:])
        elif argv[2] == "submit":
            out = cmd_end(a, "submit", "")
        else:
            out = cmd_end(a, "abandon", " ".join(argv[3:]))
    except Exception as e:  # an infrastructure failure of the wrapper, never a verdict
        try:
            a.log({"cmd": argv[2], "infra_error": repr(e)[:500]})
        except Exception:
            pass
        out = {"error": "harness_failure", "detail": repr(e)[:500],
               "note": "infrastructure failure; this call is recorded as such"}
    finally:
        a.unlock()
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
