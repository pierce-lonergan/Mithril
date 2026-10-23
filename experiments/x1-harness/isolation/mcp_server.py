"""The X1 harness MCP server (X1-amendment-1 2.3 item 3; X1 DESIGN 7).

A stdio JSON-RPC (newline-delimited) MCP server that is the subject agent's ONLY capability. It has
no shell: it exposes exactly eight tools over `work/` and the sandboxed checker, and nothing else.
The subject agent type (attempt.py) lists only `mcp__x1__*` tools, so the subject cannot read a file,
run a command, reach the network, or call any other tool except through this server.

Tools (DESIGN 7; the task's named set maps onto these):
  list_files()                      "read-own-workspace": list the writable + read-only task files
  read_file(path)                   read one file under work/
  write_file(path, text)            write the solution file under work/
  str_replace(path, old, new)       edit the solution file under work/
  check(run_tests=false)            run the arm checker in the per-call sandbox; 1 of 8 calls
  run_tests()                       check(run_tests=true)
  submit()                          end the attempt; only ending that can be a verified pass
  abandon(reason)                   end the attempt as abandoned

Every call is appended to the hash-chained attempt log. Budgets enforced here: the 8-check budget,
the wall-clock budget (from the first tool call), and a hard tool-call backstop. The turn and token
budgets are the runner's to enforce from the headless session's usage report (SMOKE 2: `agent()` has
no turn option and a headless session's token report is unavailable on this laptop); this server
records each `tools/call` so the runner can bound them, and refuses further work past the wall and
check budgets regardless.

Run as:  CLAUDE/MCP spawns `python mcp_server.py` with env X1_ATTEMPT_DIR, X1_IMAGE_ROOT (the
toolchain image) and X1_SANDBOX_ROOT (the neutral root for per-call sandbox directories, outside the
attempt tree; default `<attempt parent>/sbx`). attempt.py writes all three into the server's `env`
block. It reads JSON-RPC from stdin, writes to stdout; all logging goes to stderr.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import attempt as A  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
REASON_RE = re.compile(r"[^A-Za-z0-9 ,.:_()<>=+\-]")

TOOLS = [
    {"name": "list_files", "description": "List the files in your workspace (writable and read-only).",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "read_file", "description": "Read one file from your workspace.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}},
                     "required": ["path"], "additionalProperties": False}},
    {"name": "write_file", "description": "Write (create or overwrite) a file in your workspace.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "text": {"type": "string"}},
                     "required": ["path", "text"], "additionalProperties": False}},
    {"name": "str_replace", "description": "Replace one exact occurrence of a string in a workspace file.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"},
                                                      "new": {"type": "string"}},
                     "required": ["path", "old", "new"], "additionalProperties": False}},
    {"name": "check", "description": "Run the checker on your solution. Counts as one of 8 calls.",
     "inputSchema": {"type": "object", "properties": {"run_tests": {"type": "boolean"}},
                     "additionalProperties": False}},
    {"name": "run_tests", "description": "Run the checker with the visible tests. Counts as one of 8 calls.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "submit", "description": "Declare the work done and end the attempt.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "abandon", "description": "End the attempt as abandoned, with a short reason.",
     "inputSchema": {"type": "object", "properties": {"reason": {"type": "string"}},
                     "additionalProperties": False}},
]


def log(*a):
    print("[x1-mcp]", *a, file=sys.stderr, flush=True)


class Server:
    def __init__(self, attempt_dir: Path, image_root: Path | None, sandbox_root: Path | None = None):
        self.att = A.Attempt(attempt_dir)
        self.image_root = image_root
        self.sandbox_root = Path(sandbox_root) if sandbox_root else A.default_sandbox_root(self.att.dir)
        if A.is_within(self.sandbox_root, self.att.dir):
            raise RuntimeError("the sandbox root must lie outside the attempt tree")
        self._image_cache = None
        self.ext = self.att.bundle.get("ext") or {"mithril": "mith", "rust": "rs"}[self.att.bundle["arm"]]
        self.sol = self.att.work / f"solution.{self.ext}"

    # ----------------------------------------------------- workspace (confined to work/)
    def _resolve(self, path: str):
        """Resolve `path` under work/. Returns (Path, None) or (None, error-dict) if it escapes."""
        root = str(self.att.work.resolve())
        p = (self.att.work / path).resolve()
        if p != self.att.work.resolve() and not str(p).startswith(root + os.sep):
            return None, {"error": "path escapes the workspace; only files under your workspace are readable"}
        return p, None

    def t_list_files(self, _args):
        files = []
        for p in sorted(self.att.work.rglob("*")):
            if p.is_file():
                rel = p.relative_to(self.att.work).as_posix()
                writable = p.name.startswith("solution.")
                files.append({"path": rel, "bytes": p.stat().st_size, "writable": writable})
        files.append({"path": f"solution.{self.ext}", "writable": True, "exists": self.sol.exists()})
        return {"files": files,
                "note": f"Write your answer to solution.{self.ext}. prelude.{self.ext} and the stub are read-only."}

    def t_read_file(self, args):
        p, err = self._resolve(args["path"])
        if err:
            return err
        if not p.is_file():
            return {"error": "no such file"}
        return {"path": args["path"], "text": p.read_text(encoding="utf-8", errors="replace")}

    def t_write_file(self, args):
        if not args["path"].endswith(f"solution.{self.ext}") and Path(args["path"]).name != f"solution.{self.ext}":
            return {"error": f"you may only write solution.{self.ext}"}
        self.sol.write_text(args["text"], encoding="utf-8")
        return {"ok": True, "bytes": len(args["text"].encode("utf-8"))}

    def t_str_replace(self, args):
        if not self.sol.exists():
            return {"error": f"solution.{self.ext} does not exist yet; write_file it first"}
        src = self.sol.read_text(encoding="utf-8")
        n = src.count(args["old"])
        if n != 1:
            return {"error": f"old string occurs {n} times; it must occur exactly once"}
        self.sol.write_text(src.replace(args["old"], args["new"]), encoding="utf-8")
        return {"ok": True}

    # ----------------------------------------------------- check (sandboxed)
    def _image(self):
        if self._image_cache is None:
            import winsandbox as W
            if not self.image_root:
                raise RuntimeError("X1_IMAGE_ROOT not set")
            self._image_cache = W.ToolchainImage(Path(self.image_root))
        return self._image_cache

    def _run_check(self, run_tests: bool):
        import winsandbox as W
        import checker
        acct = self.att.accounting()
        st = self.att.state()
        if st.get("ended") or acct["ended"]:
            return {"error": "attempt_ended", "end_reason": st.get("end_reason") or acct["ended"]}
        if not acct["chain_ok"]:
            self.att.log({"cmd": "check", "refused": "log_integrity_failure"})
            return {"error": "log_integrity_failure"}
        if self.att.wall_left(acct) <= 0:
            self._end("budget_wall", "")
            return {"error": "wall_budget_exhausted", "note": "time is up; the attempt has ended"}
        used = acct["checks_used"]
        budget = self.att.budgets["checks"]
        if used >= budget:
            self.att.log({"cmd": "check", "refused": "budget_exhausted", "checks_used": used})
            return {"error": "budget_exhausted", "budget": budget}
        if not self.sol.exists():
            return {"error": f"write solution.{self.ext} before checking"}
        k = used + 1
        bundle = dict(self.att.bundle, run_tests=run_tests)
        # A neutral, random call directory OUTSIDE the attempt tree (review 1, finding 6): sandboxed
        # code and the toolchain's diagnostics see this path, so it must name no attempt, item or arm.
        token = secrets.token_hex(8)
        call_dir = self.sandbox_root / token
        # One CPU pool and one wall deadline for the whole call (checker.CallBudget): the wall cap
        # is also bounded by what is left of the attempt's wall budget, so no call outlives it.
        limits = {"cpu_s": self.att.bundle.get("cpu_s", 180.0),
                  "wall_s": min(self.att.bundle.get("sandbox_wall_s", 540.0), max(1.0, self.att.wall_left(acct)))}
        res = checker.run_check(self._image(), call_dir, self.att.bundle["arm"],
                                self.sol.read_text(encoding="utf-8"), bundle, limits=limits)
        res["call"] = k
        res["remaining"] = budget - k
        self.att.log({"cmd": "check", "phase": "done", "call": k, "run_tests": run_tests,
                      "verdict": res.get("verdict"), "static_gate": res["static_gate"]["verdict"],
                      "holes": res.get("holes"), "sandbox_call": token, "budget": res.get("budget"),
                      "workspace_hash": A.sha256_text(self.sol.read_text(encoding="utf-8"))})
        st["checks_used"] = k
        self.att.save_state(st)
        return res

    def t_check(self, args):
        return self._run_check(bool(args.get("run_tests", False)))

    def t_run_tests(self, _args):
        return self._run_check(True)

    def _end(self, how: str, reason: str):
        src = self.sol.read_text(encoding="utf-8") if self.sol.exists() else ""
        sub = self.att.harn / ("submitted" if how == "submit" else "final")
        sub.mkdir(parents=True, exist_ok=True)
        (sub / f"solution.{self.ext}").write_text(src, encoding="utf-8")
        st = self.att.state()
        st.update({"ended": True, "end_reason": how})
        self.att.save_state(st)
        self.att.log({"cmd": how, "ended": how, "reason": reason or None,
                      "final_artifact_hash": A.sha256_text(src)})
        return {"ok": True, "ended": how, "final_artifact_hash": A.sha256_text(src)}

    def t_submit(self, _args):
        acct = self.att.accounting()
        if self.att.state().get("ended") or acct["ended"]:
            return {"error": "attempt_ended"}
        return self._end("submit", "")

    def t_abandon(self, args):
        acct = self.att.accounting()
        if self.att.state().get("ended") or acct["ended"]:
            return {"error": "attempt_ended"}
        return self._end("abandon", REASON_RE.sub("", args.get("reason", ""))[:200])

    # ----------------------------------------------------- dispatch
    def call_tool(self, name: str, args: dict):
        # record every tool call (turns proxy) and enforce the tool-call backstop + wall
        acct = self.att.accounting()
        if acct["tool_calls"] >= self.att.budgets["tool_calls"]:
            return {"error": "tool_call_budget_exhausted"}
        if not self.att.state().get("ended") and self.att.wall_left(acct) <= 0 and name in ("check", "run_tests"):
            pass  # handled inside _run_check
        self.att.log({"cmd": "tool", "tool": name})
        fn = getattr(self, "t_" + name, None)
        if fn is None:
            raise ValueError(f"unknown tool {name}")
        return fn(args or {})


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> int:
    adir = os.environ.get("X1_ATTEMPT_DIR")
    if not adir:
        log("X1_ATTEMPT_DIR not set")
        return 2
    image_root = os.environ.get("X1_IMAGE_ROOT")
    sandbox_root = os.environ.get("X1_SANDBOX_ROOT")
    srv = Server(Path(adir), Path(image_root) if image_root else None,
                 Path(sandbox_root) if sandbox_root else None)
    log("ready, attempt", adir)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        mid = msg.get("id")
        method = msg.get("method")
        try:
            if method == "initialize":
                send({"jsonrpc": "2.0", "id": mid, "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "x1", "version": "x1iso/1"}}})
            elif method in ("notifications/initialized", "initialized"):
                pass
            elif method == "tools/list":
                send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
            elif method == "tools/call":
                params = msg.get("params") or {}
                out = srv.call_tool(params.get("name"), params.get("arguments") or {})
                send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": json.dumps(out, sort_keys=True)}],
                    "isError": bool(isinstance(out, dict) and out.get("error"))}})
            elif method == "ping":
                send({"jsonrpc": "2.0", "id": mid, "result": {}})
            elif mid is not None:
                send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method {method}"}})
        except Exception as e:  # never crash the server on a bad call
            log("error in", method, repr(e))
            if mid is not None:
                send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32000, "message": repr(e)[:300]}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
