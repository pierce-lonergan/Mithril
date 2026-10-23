#!/usr/bin/env python3
"""X1 smoke-run kit (X1-amendment-1 2.3 and 6.2). DEVELOPMENT items only; never sealed content.

Subcommands (all deterministic; none of them starts a Claude session):
  prepare   create a run root: harness copy, mithi copy, cards, 65 planned attempts (plus one
            replacement directory each and a probe attempt), RUN.json, the agent files under
            <run root>/.claude/agents/, and the workflow instances smoke_workflow.js (batches, in
            waves of 5) and probe_workflow.js (the pre-flight probe)
  probe     read the probe workflow's transcripts: agent type, tools offered, model, effort,
            working directory, prefix size -> results/probe.json (the gate needs ok = true)
  tokens    per-attempt token usage, model, effort, tools offered, Claude Code version, budgets
            and a tool-use audit, read from the workflow transcripts -> results/tokens.json
  score     acceptance check + hidden oracle per attempt, VP@1 and CABW per arm, log integrity
            -> results/score.json
  gate      the 6.2 decision rule on the recorded plan readings (readings.json), with the pins,
            the audit and the batch records checked first -> results/gate.json (+ gate_history/)
  p2        record 2.4 P2 on the latest reading: may the next wave start?
  status    calls used and end reasons of a run's attempts (no tokens, no toolchains)
  selftest  everything above on reference solutions, stubs, mutants and synthetic transcripts,
            without any agent

Evidence tags in outputs follow docs/m0/README.md: everything these scripts compute from files is
[M] (measured here) or [D] (derived by a stated formula); the decision constants are [target].
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import smokelib as L  # noqa: E402
import scoring  # noqa: E402

C = scoring.x1check          # the wrapper module (log reading, static gate)
REPO = HERE.parents[2]
KIT_VERSION = "x1smoke/2"
DEFAULT_PYTHON = sys.executable
DEFAULT_RUSTC = Path.home() / ".rustup-mithril" / "toolchains" / "1.99.1-x86_64-pc-windows-gnu" / "bin" / "rustc.exe"
AGENT_FILE = REPO / ".claude" / "agents" / "x1-subject.md"

# X1-amendment-1 6.2 [target], as signed in the interim chat signature of 2026-10-23
GATE_S = Fraction(1, 2)          # share s = 50%
GATE_K = 6                       # weeks
GATE_A = 3456                    # planned Claude attempts at n = 136 (record 4.4)
BATCHES = [(1, 0, 5), (2, 5, 25), (3, 25, 45), (4, 45, 65)]   # 5, then batches of 20 up to 65
CONCURRENCY = 5
WAVE_SIZE = 5                    # P2 is checked before every wave (record 2.4)
FULL_MODEL_ID = "claude-opus-5-5"
PINNED_EFFORT = "max"
SUBJECT_TOOLS = {"Write", "Bash"}
# record 2.3 item 6 / DESIGN 12.1 budgets [G]; only checks and wall time are enforced by the kit
CHECK_BUDGET = 8
TURN_BUDGET = 60
NONPREFIX_INPUT_BUDGET = 600_000
OUTPUT_BUDGET = 60_000
WALL_BUDGET_S = 45 * 60
PATH_MAX = 240                   # Windows CreateDirectory limit is about 248 characters [M, review 1]
BUILD_NAME_ALLOWANCE = 60        # longest file name rustc/mithi write inside a build directory [G]
TEN_MIN = dt.timedelta(minutes=10)
TOL = dt.timedelta(seconds=30)
WEEK = dt.timedelta(days=7)


# ----------------------------------------------------------------------------- helpers

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def sha256_text(t: str) -> str:
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, sort_keys=True), encoding="utf-8")


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def fwd(p) -> str:
    """A path with forward slashes, for the subject's Bash commands."""
    return str(p).replace("\\", "/")


def parse_t(s):
    """ISO-8601 UTC (with Z or an offset) -> aware datetime; None if missing or unparseable."""
    if not isinstance(s, str) or not s:
        return None
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else None


def norm_path(p) -> str:
    try:
        p = Path(p).resolve()
    except OSError:
        pass
    return os.path.normcase(os.path.normpath(str(p)))


def git_head() -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception:
        return "unknown"


def git_dirty_paths() -> list:
    try:
        out = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", "experiments/x1-harness/smoke",
                              ".claude/agents/x1-subject.md", "crates/mithi", "grammar"],
                             capture_output=True, text=True, timeout=30).stdout
        return [l for l in out.splitlines() if l.strip()]
    except Exception:
        return ["unknown"]


def toolchain(args) -> dict:
    mithi = Path(args.mithi) if getattr(args, "mithi", None) else None
    if mithi is None or not mithi.exists():
        raise SystemExit("--mithi PATH to a built mithi binary is required (see SMOKE.md, 'Build mithi')")
    rustc = Path(args.rustc) if getattr(args, "rustc", None) else DEFAULT_RUSTC
    if not rustc.exists():
        raise SystemExit(f"rustc not found at {rustc}; pass --rustc")
    rv = subprocess.run([str(rustc), "-vV"], capture_output=True, text=True, timeout=60).stdout
    return {
        "mithi": str(mithi), "mithi_sha256": sha256_file(mithi),
        "rustc": str(rustc), "rustc_sha256": sha256_file(rustc), "rustc_vV": rv.strip().splitlines(),
        "python": DEFAULT_PYTHON, "python_version": sys.version.split()[0],
        **mithi_std_check(mithi),
    }


def mithi_std_check(mithi: Path) -> dict:
    """Does the mithi binary embed the std that Tier 1 is generated from? mithi reports
    std_sha256 = SHA-256(std.mith bytes + prelude/canonical.mith bytes) as compiled in
    (crates/mithi/src/main.rs); the repository's working-tree files give the same hash when the
    binary was built from them [M, 2026-10-23]. A mismatch means the card would describe a different
    std from the one the checker enforces."""
    d = Path(tempfile.mkdtemp(prefix="x1std_"))
    try:
        (d / "t.mith").write_text("fn f() -> u32 { 1 }\n", encoding="utf-8")
        r = subprocess.run([str(mithi), "check", "--json", "--subset", "agent", "t.mith"], cwd=str(d),
                           capture_output=True, text=True, timeout=120)
        try:
            got = json.loads(r.stdout.strip().splitlines()[-1]).get("std_sha256")
        except (ValueError, IndexError):
            got = None
    finally:
        shutil.rmtree(d, ignore_errors=True)
    std_b = (REPO / "crates" / "mithi" / "std" / "std.mith").read_bytes()
    pre_b = (REPO / "crates" / "mithi" / "prelude" / "canonical.mith").read_bytes()
    repo = hashlib.sha256(std_b + pre_b).hexdigest()
    return {"mithi_std_sha256": got, "repo_std_sha256": repo, "std_matches_repo": got == repo}


# ----------------------------------------------------------------------------- cards

def tier1_text() -> str:
    """Development Tier 1: the X1 grammar verbatim (core) and the X1 std signatures (std).

    Generated from the repository at prepare time; its hash is recorded in RUN.json.
    """
    grammar = (REPO / "grammar" / "mithril_v0.lark").read_text(encoding="utf-8")
    std = (REPO / "crates" / "mithi" / "std" / "std.mith").read_text(encoding="utf-8")
    std = re.sub(r"#\[builtin\([^)]*\)\]\s*", "", std)
    std = re.sub(r"#\[lang = \"[^\"]*\"\]\s*", "", std)
    std = re.sub(r"#\[builtin_type\]\s*", "", std)
    return ("MITHRIL TIER 1 - X1 smoke run, DEVELOPMENT reference (v0-dev). Generated from the repository.\n"
            "core: the X1 grammar (grammar/mithril_v0.lark, verbatim). std: the X1 std and std_platform\n"
            "signatures (crates/mithi/std/std.mith; bodies are native). #[exact_std] marks std items a kernel\n"
            "may call; `uses { alloc(Global) }` marks allocating items; `requires`/`ensures` are checked.\n\n"
            "== core: grammar ==\n" + grammar + "\n== std: signatures ==\n" + std)


def card_texts() -> dict:
    t0 = L.read_text(L.CARDS_DIR / "mithril_tier0_dev.md")
    t1 = tier1_text()
    return {
        "mithril": t0 + "\n" + t1,
        "rust": L.read_text(L.CARDS_DIR / "rust_helper_dev.md"),
        "preamble": L.read_text(L.CARDS_DIR / "domain_preamble_dev.md"),
        "tier0": t0,
        "tier1": t1,
    }


# ----------------------------------------------------------------------------- plan

def make_plan(seed: int, n_max: int = 65) -> list:
    """Seeded attempt order: blocks of the 16 (task, arm) cells; inside a block the arms alternate
    (Mithril first in odd blocks, Rust first in even ones) and the tasks are shuffled per arm. Any
    prefix is balanced between the arms within one attempt."""
    rng = random.Random(seed)
    order = []
    block = 0
    while len(order) < n_max:
        m = list(L.TASK_IDS)
        r = list(L.TASK_IDS)
        rng.shuffle(m)
        rng.shuffle(r)
        first, second = (m, r) if block % 2 == 0 else (r, m)
        a1, a2 = ("mithril", "rust") if block % 2 == 0 else ("rust", "mithril")
        for i in range(len(L.TASK_IDS)):
            order.append((first[i], a1))
            order.append((second[i], a2))
        block += 1
    return order[:n_max]


def batches_for(n_max: int) -> list:
    """The record's batches (5, then 20s up to 65), clipped to n_max (selftest runs use fewer)."""
    return [(b, lo, min(hi, n_max)) for b, lo, hi in BATCHES if lo < n_max]


def batch_of(index: int, n_max: int = 65) -> int:
    for b, lo, hi in batches_for(n_max):
        if lo <= index < hi:
            return b
    raise ValueError(index)


def visible_listing(task, arm_bundle) -> str:
    lines = []
    for k, (desc, exp) in enumerate(zip(arm_bundle["describe"], arm_bundle["expected"])):
        lines.append(f"case {k}: {desc}\n  expected: {exp}")
    return "\n".join(lines)


def attempt_ids(run_id: str, n_max: int) -> list:
    return [f"{run_id}-a{i + 1:02d}" for i in range(n_max)]


def longest_paths(root: Path, run_id: str, n_max: int) -> dict:
    """The longest paths the wrapper and the toolchains create under a run root (review 1, finding 8)."""
    aid = attempt_ids(run_id, n_max)[-1] + "-r1"
    h = root / "attempts" / aid / "harness"
    return {
        "snapshot": str(h / "snapshots" / "s99_call8.mith"),
        "state_tmp": str(h / "state.json.tmp"),
        "submitted": str(h / "submitted" / "solution.mith"),
        "prelude": str(h / "prelude.mith"),
        "build_file": str(root / "b" / ("99" + "x" * 8) / ("x" * BUILD_NAME_ALLOWANCE)),
    }


def check_path_lengths(root: Path, run_id: str, n_max: int) -> dict:
    lp = longest_paths(root, run_id, n_max)
    worst = max(len(v) for v in lp.values())
    return {"longest": worst, "limit": PATH_MAX, "ok": worst <= PATH_MAX, "paths": lp}


SUBJECT_PROMPT_NOTE = ("The reason may use letters, digits, spaces and , . : _ ( ) < > = + - only "
                       "(no quotes, $ or backticks inside it).")

TURNCAP_AGENT = """---
name: x1-turncap-probe
description: X1 smoke-run pre-flight probe only. Tests whether a maxTurns frontmatter field is honoured. Not for any other use.
tools: Bash
model: {model}
maxTurns: 2
---
You are a probe. Follow the task message exactly: run each command it gives as its own Bash call,
one command per turn, in the order given.
"""


def make_attempt_dir(root: Path, aid: str, tid: str, arm: str, entry: dict, meta_extra: dict, python: str) -> dict:
    adir = root / "attempts" / aid
    (adir / "work").mkdir(parents=True)
    (adir / "harness").mkdir()
    ext = L.EXT[arm]
    (adir / "work" / f"stub.{ext}").write_text(entry[arm]["stub"], encoding="utf-8", newline="\n")
    (adir / "work" / f"prelude.{ext}").write_text(entry[arm]["prelude"], encoding="utf-8", newline="\n")
    (adir / "harness" / f"prelude.{ext}").write_text(entry[arm]["prelude"], encoding="utf-8", newline="\n")
    write_json(adir / "harness" / "visible.json", entry[arm]["visible_bundle"])
    meta = {"schema": "x1-smoke-attempt-meta/2", "attempt_id": aid, "task_id": tid, "arm": arm, "ext": ext,
            "budget": CHECK_BUDGET, "split": "development",
            "prelude_sha256": sha256_file(adir / "harness" / f"prelude.{ext}"), **meta_extra}
    write_json(adir / "attempt.json", meta)
    return {"id": aid, "task": tid, "arm": arm,
            "solution_path": fwd(adir / "work" / f"solution.{ext}"),
            "cmd": f"\"{fwd(python)}\" \"{fwd(root / 'harness' / 'x1check.py')}\" \"{fwd(adir)}\""}


def cmd_prepare(args) -> None:
    root = Path(args.root).resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"{root} exists and is not empty; choose a new run root")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", args.run_id):
        raise SystemExit("--run-id: 1-32 characters of [A-Za-z0-9_-]")
    pl = check_path_lengths(root, args.run_id, args.n_max)
    if not pl["ok"]:
        raise SystemExit(f"run root too long: the wrapper would create a {pl['longest']}-character path "
                         f"(limit {PATH_MAX}). Use a short root such as %LOCALAPPDATA%\\x1s\\<id> and a short run id.")
    tc = toolchain(args)
    if not tc["std_matches_repo"] and not getattr(args, "allow_std_mismatch", False):
        raise SystemExit(f"the mithi binary's std ({tc['mithi_std_sha256']}) is not the repository's std.mith + "
                         f"canonical.mith ({tc['repo_std_sha256']}): Tier 1 would describe another std. Rebuild mithi "
                         f"from this tree (SMOKE.md 4.2 step 1), or pass --allow-std-mismatch (a deviation to log).")
    python = args.python or DEFAULT_PYTHON
    root.mkdir(parents=True, exist_ok=True)
    for d in ("harness", "bin", "cards", "attempts", "results", "b", ".claude/agents"):
        (root / d).mkdir(parents=True, exist_ok=True)
    shutil.copy2(L.HARNESS_DIR / "x1check.py", root / "harness" / "x1check.py")
    mithi_copy = root / "bin" / ("mithi.exe" if os.name == "nt" else "mithi")
    shutil.copy2(tc["mithi"], mithi_copy)
    # the controller session runs with the run root as its working directory (SMOKE.md 4.2), so the
    # agent type is resolved from here, away from the repository and its memory and transcripts
    shutil.copy2(AGENT_FILE, root / ".claude" / "agents" / "x1-subject.md")
    (root / ".claude" / "agents" / "x1-turncap-probe.md").write_text(
        TURNCAP_AGENT.format(model=args.model), encoding="utf-8", newline="\n")
    cards = card_texts()
    for name, text in cards.items():
        (root / "cards" / f"{name}.txt").write_text(text, encoding="utf-8", newline="\n")

    # per-task packets (both arms), shared by the attempts of that cell
    tasks = {}
    for tid in L.TASK_IDS:
        task = L.load_task(tid)
        entry = {"brief": L.read_text(L.task_file(tid, "brief.md")), "meta": task.TASK}
        for arm in L.ARMS:
            vb = scoring.visible_bundle(tid, arm)
            entry[arm] = {
                "prelude": scoring.prelude_text(tid, arm),
                "stub": scoring.stub_text(tid, arm),
                "visible": visible_listing(task, vb),
                "visible_bundle": vb,
            }
        tasks[tid] = entry

    order = make_plan(args.seed, args.n_max)
    batches = batches_for(args.n_max)
    attempts, replacements = [], {}
    for i, (tid, arm) in enumerate(order):
        aid = f"{args.run_id}-a{i + 1:02d}"
        b = batch_of(i, args.n_max)
        a = make_attempt_dir(root, aid, tid, arm, tasks[tid],
                             {"run_id": args.run_id, "index": i, "batch": b, "kind": "planned"}, python)
        a["batch"] = b
        attempts.append(a)
        # one replacement directory per attempt: record 2.3 item 7 re-runs an infrastructure failure
        # as a fresh attempt; it runs in a replacement wave of the same batch (SMOKE.md 4.4)
        r = make_attempt_dir(root, aid + "-r1", tid, arm, tasks[tid],
                             {"run_id": args.run_id, "index": i, "batch": b, "kind": "replacement",
                              "replaces": aid}, python)
        r.update({"batch": b, "replaces": aid})
        replacements[aid] = r
    probe_tid, probe_arm = "D-Q4-1", "rust"
    probe = make_attempt_dir(root, f"{args.run_id}-probe", probe_tid, probe_arm, tasks[probe_tid],
                             {"run_id": args.run_id, "index": -1, "batch": 0, "kind": "probe"}, python)

    cfg = {
        "schema": "x1-smoke-run/2", "kit": KIT_VERSION, "run_id": args.run_id, "created_utc": now_utc(),
        "split": "development", "root": str(root), "mithi": str(mithi_copy), "mithi_sha256": sha256_file(mithi_copy),
        "mithi_std_sha256": tc["mithi_std_sha256"], "repo_std_sha256": tc["repo_std_sha256"],
        "std_matches_repo": tc["std_matches_repo"],
        "allow_std_mismatch": bool(getattr(args, "allow_std_mismatch", False)),
        "rustc": tc["rustc"], "rustc_sha256": tc["rustc_sha256"], "rustc_vV": tc["rustc_vV"],
        "rust_env": {}, "python": python, "python_version": tc["python_version"],
        "check_timeout_s": 60, "case_timeout_s": 10, "oracle_timeout_s": 900,
        "wall_budget_s": WALL_BUDGET_S, "build_base": str(root / "b"), "path_check": pl,
        "repo_head": git_head(), "repo_dirty_paths": git_dirty_paths(),
        "seed": args.seed, "n_max": args.n_max, "batches": batches, "concurrency": CONCURRENCY,
        "wave_size": WAVE_SIZE, "agent_type": "x1-subject", "model": args.model, "effort": args.effort,
        "agent_file_sha256": sha256_file(AGENT_FILE),
        "agent_file_copy_sha256": sha256_file(root / ".claude" / "agents" / "x1-subject.md"),
        "harness_sha256": sha256_file(root / "harness" / "x1check.py"),
        "cards_sha256": {k: sha256_text(v) for k, v in cards.items()},
        "card_bytes": {k: len(v.encode("utf-8")) for k, v in cards.items()},
        "task_sha256": {tid: {rel: sha256_file(L.task_file(tid, rel)) for rel in
                              ["task.py", "brief.md", "mithril/stub.mith", "mithril/prelude.mith",
                               "rust/stub.rs", "rust/prelude.rs"]} for tid in L.TASK_IDS},
        "gate": {"s": str(GATE_S), "K": GATE_K, "A": GATE_A, "w_star": str(GATE_S * 100 * GATE_K / GATE_A)},
        "attempts": [{k: a[k] for k in ("id", "task", "arm", "batch")} for a in attempts],
        "replacements": [{k: r[k] for k in ("id", "task", "arm", "batch", "replaces")} for r in replacements.values()],
        "probe": {"attempt_id": probe["id"], "task": probe_tid, "arm": probe_arm,
                  "labels": {"main": f"{args.run_id}-probe", "fullid": f"{args.run_id}-probe-fullid",
                             "turncap": f"{args.run_id}-probe-turncap"}},
    }

    plan = {
        "run_id": args.run_id, "root": fwd(root), "agent_type": "x1-subject", "model": args.model,
        "effort": args.effort, "concurrency": CONCURRENCY, "wave_size": WAVE_SIZE,
        "batches": [{"batch": b, "from": lo, "to": hi} for b, lo, hi in batches],
        "cards": {"mithril": cards["mithril"], "rust": cards["rust"]}, "preamble": cards["preamble"],
        "tasks": {tid: {"brief": t["brief"], **{arm: {k: t[arm][k] for k in ("prelude", "stub", "visible")}
                                                for arm in L.ARMS}} for tid, t in tasks.items()},
        "attempts": attempts,
        "replacements": replacements,
        "abandon_note": SUBJECT_PROMPT_NOTE,
    }
    plan_json = json.dumps(plan, sort_keys=True, ensure_ascii=True)
    plan["plan_sha256"] = sha256_text(plan_json)
    write_json(root / "plan.json", plan)
    template = (HERE / "smoke_workflow.js").read_text(encoding="utf-8")
    marker = "const PLAN = null; // @@PLAN@@"
    if marker not in template:
        raise SystemExit("smoke_workflow.js template marker missing")
    inst = template.replace(marker, "const PLAN = " + json.dumps(plan, sort_keys=True, ensure_ascii=True) + ";")
    (root / "smoke_workflow.js").write_text(inst, encoding="utf-8", newline="\n")

    labels = cfg["probe"]["labels"]
    probe_spec = {
        "run_id": args.run_id, "plan_sha256": plan["plan_sha256"], "agent_type": "x1-subject",
        "model": args.model, "full_model_id": FULL_MODEL_ID, "effort": args.effort, "labels": labels,
        "main_prompt": (
            f"X1 SMOKE PROBE (pre-flight check; not an attempt; nothing is scored). Probe id: {labels['main']}.\n"
            "Do exactly these three steps, then stop.\n"
            "1. Write a line TOOLS-BEGIN, then the exact name of every tool available to you, one per line, "
            "then a line TOOLS-END.\n"
            "2. Run this harness command with Bash, copied exactly:\n"
            f"   {probe['cmd']} check\n"
            "3. Reply with the values of the \"call\" and \"remaining\" fields the command printed, as one line "
            f"`CALL <call> REMAINING <remaining>`, and then a final line `END {labels['main']}`."),
        "fullid_prompt": (f"X1 SMOKE PROBE (model-ID test; not an attempt). Reply with the single word OK, "
                          f"then a final line `END {labels['fullid']}`. Use no tool."),
        "turncap_prompt": ("X1 SMOKE PROBE (turn-cap test; not an attempt). Run these five commands with Bash, "
                           "one Bash call per command, in this order: `echo turn-1`, `echo turn-2`, `echo turn-3`, "
                           "`echo turn-4`, `echo turn-5`. After the fifth, reply DONE."),
    }
    ptemplate = (HERE / "probe_workflow.js").read_text(encoding="utf-8")
    pmarker = "const PROBE = null; // @@PROBE@@"
    if pmarker not in ptemplate:
        raise SystemExit("probe_workflow.js template marker missing")
    (root / "probe_workflow.js").write_text(
        ptemplate.replace(pmarker, "const PROBE = " + json.dumps(probe_spec, sort_keys=True, ensure_ascii=True) + ";"),
        encoding="utf-8", newline="\n")

    cfg["plan_sha256"] = plan["plan_sha256"]
    cfg["workflow_instance_sha256"] = sha256_file(root / "smoke_workflow.js")
    cfg["probe_instance_sha256"] = sha256_file(root / "probe_workflow.js")
    write_json(root / "RUN.json", cfg)
    write_json(root / "readings.json", readings_skeleton(args.run_id))
    write_json(root / "dispositions.json", dispositions_skeleton(args.run_id))
    print(json.dumps({"root": str(root), "run_id": args.run_id, "attempts": len(attempts),
                      "workflow": str(root / "smoke_workflow.js"), "probe_workflow": str(root / "probe_workflow.js"),
                      "plan_sha256": plan["plan_sha256"], "card_bytes": cfg["card_bytes"],
                      "longest_path": pl["longest"],
                      "controller_cwd": str(root),
                      "next": "start a fresh controller session with the run root as its working directory; "
                              "run the probe (SMOKE.md 4.2)"}, indent=1))


def readings_skeleton(run_id: str) -> dict:
    return {
        "schema": "x1-smoke-readings/2",
        "run_id": run_id,
        "note": ("Fill in by hand (SMOKE.md 4.3), in time order. Every reading: kind ('gate' or 'p2'), t_utc, "
                 "weekly_all_models_pct and five_hour_pct (whole points from get_usage, [M]), "
                 "controller_context_tokens. Gate readings also carry after_batch (0 for r0, k after batch k, "
                 "-k before batch k in the step-5 variant). P2 readings carry 'before' (e.g. 'batch 2 wave 1'). "
                 "weekly_reset_utc: any reset instant of the weekly all-models window (it recurs every 7 days)."),
        "quiet_throughout": True,
        "weekly_reset_utc": None,
        "readings": [],
        "batches": [],
    }


def dispositions_skeleton(run_id: str) -> dict:
    return {
        "schema": "x1-smoke-dispositions/1",
        "run_id": run_id,
        "note": ("Lead engineer: one entry per attempt the audit or the integrity check flags, recorded BEFORE "
                 "the gate reports a decision (the gate withholds it until then). Fields: attempt_id, "
                 "disposition ('benign' or 'misuse'), exclude_from_N (true when the flagged use could have made "
                 "the attempt cheaper, e.g. reading a reference), reviewer, note."),
        "dispositions": [],
    }


def load_plan(root: Path) -> dict:
    p = root / "plan.json"
    if p.exists():
        return read_json(p)
    inst = (root / "smoke_workflow.js").read_text(encoding="utf-8")
    m = re.search(r"^const PLAN = (\{.*\});$", inst, re.M)
    return json.loads(m.group(1))


def all_attempt_entries(plan: dict) -> dict:
    """Every attempt id the subject agents may carry as a label: planned and replacement."""
    out = {a["id"]: a for a in plan["attempts"]}
    for r in (plan.get("replacements") or {}).values():
        out[r["id"]] = r
    return out


# ----------------------------------------------------------------------------- log integrity

def log_integrity(adir: Path) -> dict:
    """The attempt log against itself and against state.json (review 1, finding 3)."""
    h = adir / "harness"
    entries, chain = C.read_log(h / "log.jsonl")
    acct = C.call_accounting(entries)
    meta = read_json(adir / "attempt.json")
    budget = int(meta.get("budget", CHECK_BUDGET))
    st = None
    if (h / "state.json").exists():
        try:
            st = read_json(h / "state.json")
        except ValueError:
            st = {"calls": None}
    done = [e for e in entries if e.get("cmd") == "check" and e.get("phase") in ("done", "infra")]
    calls = [e.get("call") for e in done]
    res = {
        "log_chain_ok": chain["ok"],
        "counted_calls": acct["used"],
        "calls_within_budget": acct["used"] <= budget,
        "call_numbers_in_order": calls == list(range(1, len(calls) + 1)),
        "every_counted_call_finished": len(done) == acct["used"],
        "state_matches_log": st is None or st.get("calls") == acct["used"],
        "refunded_calls": acct["refunded"],
        "log_integrity_refusals": sum(1 for e in entries if e.get("refused") == "log_integrity_failure"),
    }
    res["ok"] = all(res[k] for k in ("log_chain_ok", "calls_within_budget", "call_numbers_in_order",
                                     "state_matches_log")) and not res["log_integrity_refusals"]
    res["unrefunded_infra_errors"] = [e.get("infra_error") for e in entries
                                      if e.get("infra_error") and e.get("phase") != "refund"]
    res["end_reason"] = acct["ended"]
    res["first_utc"] = acct["first_utc"]
    return res


def launched_attempts(root: Path) -> dict:
    """Attempts the workflow launched, from the saved results (results/batch_*.workflow.json) and
    from the transcripts (results/tokens.json), when those files exist."""
    out = {}
    for p in sorted((root / "results").glob("batch_*.workflow.json")):
        try:
            data = read_json(p)
        except ValueError:
            continue
        for a in data.get("attempts") or []:
            if a:
                prev = out.get(a["attempt_id"])
                ret = bool(a.get("returned"))
                out[a["attempt_id"]] = {"returned": ret if prev is None else (prev["returned"] or ret),
                                        "batch": data.get("batch")}
    tp = root / "results" / "tokens.json"
    if tp.exists():
        for r in read_json(tp).get("attempts") or []:
            out.setdefault(r["attempt_id"], {"returned": None})["transcript"] = True
    return out


def infra_status(root: Path, aid: str, launched: dict) -> dict:
    """One definition of an infrastructure-failure candidate, used by score and gate (review 1,
    finding 9): agent() returned null, or the wrapper failed in a call it did not refund."""
    info = launched.get(aid) or {}
    li = log_integrity(root / "attempts" / aid)
    not_returned = info.get("returned") is False
    return {"not_returned": not_returned, "wrapper_infra": bool(li["unrefunded_infra_errors"]),
            "infra": not_returned or bool(li["unrefunded_infra_errors"]), "integrity": li}


# ----------------------------------------------------------------------------- score

def score_attempt(root: Path, cfg: dict, aid: str, work: Path) -> dict:
    adir = root / "attempts" / aid
    meta = read_json(adir / "attempt.json")
    tid, arm, ext = meta["task_id"], meta["arm"], meta["ext"]
    h = adir / "harness"
    st = read_json(h / "state.json") if (h / "state.json").exists() else None
    sol = adir / "work" / f"solution.{ext}"
    entries, _chain = C.read_log(h / "log.jsonl")
    rec = {"schema": "x1-smoke-attempt/2", "attempt_id": aid, "task_id": tid, "arm": arm, "batch": meta["batch"],
           "kind": meta.get("kind", "planned"), "replaces": meta.get("replaces"), "split": "development"}
    integ = log_integrity(adir)
    rec["integrity"] = {k: v for k, v in integ.items() if k not in ("end_reason", "first_utc")}
    rec["integrity_flag"] = not integ["ok"]
    rec["infra_errors"] = integ["unrefunded_infra_errors"]
    checks = [e for e in entries if e.get("cmd") == "check" and e.get("phase") == "done"]
    rec["checker_calls"] = integ["counted_calls"]
    rec["refused_calls"] = sum(1 for e in entries if e.get("refused"))
    rec["first_check_accept"] = (checks[0]["verdict"] == "accept" and checks[0].get("static_gate") == "pass") if checks else None
    rec["first_call_utc"] = integ["first_utc"]
    rec["ended_utc"] = st.get("ended_utc") if st else None
    end = integ["end_reason"] or (st.get("end_reason") if st and st.get("ended") else None)
    if end:
        rec["end_reason"] = end
    elif not entries and not sol.exists():
        rec["end_reason"] = "not_started"     # no harness call and no file: see tokens.json for the transcript
    else:
        rec["end_reason"] = "no_submit"       # the agent stopped without submit or abandon
    if rec["end_reason"] == "submit":
        art = (h / "submitted" / f"solution.{ext}").read_text(encoding="utf-8")
    elif rec["end_reason"] in ("abandon", "budget_wall"):
        art = (h / "final" / f"solution.{ext}").read_text(encoding="utf-8")
    elif sol.exists():
        art = sol.read_text(encoding="utf-8", errors="replace")
    else:
        art = (adir / "work" / f"stub.{ext}").read_text(encoding="utf-8")
    rec["final_artifact_hash"] = sha256_text(art)
    tcfg = {"mithi": cfg["mithi"], "rustc": cfg["rustc"], "rust_env": cfg.get("rust_env") or {},
            "check_timeout_s": cfg["check_timeout_s"], "case_timeout_s": cfg["case_timeout_s"],
            "oracle_timeout_s": cfg["oracle_timeout_s"]}
    w = work / aid
    w.mkdir(parents=True, exist_ok=True)
    acc = scoring.acceptance(tid, arm, art, tcfg, w)
    orc = scoring.oracle(tid, arm, art, tcfg, w)
    rec["acceptance"] = acc
    rec["oracle"] = orc
    submitted = rec["end_reason"] == "submit"
    rec["vp"] = submitted and orc["verdict"] == "pass"
    rec["accepted"] = submitted and acc["verdict"] == "pass"
    rec["accepted_and_wrong"] = rec["accepted"] and orc["verdict"] != "pass"
    rec["unsubmitted_oracle_pass"] = (not submitted) and orc["verdict"] == "pass"
    rec["submitted_not_accepted_oracle_pass"] = submitted and acc["verdict"] != "pass" and orc["verdict"] == "pass"
    return rec


def aggregate(recs: list) -> dict:
    def agg(rs):
        scored = [r for r in rs if r["end_reason"] != "not_started"]
        n = len(scored)
        vp = sum(r["vp"] for r in scored)
        acc = sum(r["accepted"] for r in scored)
        aw = sum(r["accepted_and_wrong"] for r in scored)
        fc = [r["first_check_accept"] for r in scored if r["first_check_accept"] is not None]
        ends = {}
        for r in scored:
            ends[r["end_reason"]] = ends.get(r["end_reason"], 0) + 1
        return {"attempts_scored": n, "not_started": len(rs) - n, "vp": vp,
                "vp_at_1": (vp / n) if n else None, "accepted": acc, "accepted_and_wrong": aw,
                "cabw": (aw / acc) if acc else None,
                "cabw_unconditional": (aw / n) if n else None,
                "first_compile_rate": (sum(fc) / len(fc)) if fc else None,
                "end_reasons": ends,
                "unsubmitted_oracle_pass": sum(r["unsubmitted_oracle_pass"] for r in scored),
                "mean_checker_calls": (sum(r["checker_calls"] for r in scored) / n) if n else None}
    out = {"by_arm": {}, "by_task_arm": {}, "all": agg(recs)}
    for arm in L.ARMS:
        out["by_arm"][arm] = agg([r for r in recs if r["arm"] == arm])
    for tid in L.TASK_IDS:
        for arm in L.ARMS:
            rs = [r for r in recs if r["task_id"] == tid and r["arm"] == arm]
            if rs:
                out["by_task_arm"][f"{tid}/{arm}"] = agg(rs)
    return out


SCORE_LABEL = ("DEVELOPMENT DATA: public development items, not an X1 estimate, enters no decision. Subject "
               "outputs and scores of this run are never used for card iteration or mithi diagnostics tuning.")


def cmd_score(args) -> None:
    root = Path(args.root).resolve()
    cfg = read_json(root / "RUN.json")
    launched = launched_attempts(root)
    ids = [a["id"] for a in cfg["attempts"]] + [r["id"] for r in cfg.get("replacements") or []]
    if args.attempts:
        want = set(args.attempts.split(","))
        ids = [i for i in ids if i in want]
    else:
        def touched(i):
            ad = root / "attempts" / i
            ext = read_json(ad / "attempt.json")["ext"]
            return (ad / "harness" / "log.jsonl").exists() or (ad / "work" / f"solution.{ext}").exists()
        planned = {a["id"] for a in cfg["attempts"]}
        ids = [i for i in ids if touched(i) or i in launched or (args.include_not_started and i in planned)]
    work = Path(tempfile.mkdtemp(prefix="x1score_"))
    try:
        recs = [score_attempt(root, cfg, aid, work) for aid in ids]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for r in recs:
        info = launched.get(r["attempt_id"])
        # an attempt the workflow launched is scored even if it never touched the harness
        if info and r["end_reason"] == "not_started":
            r["end_reason"] = "no_submit"
        inf = infra_status(root, r["attempt_id"], launched)
        r["infra_candidate"] = inf["infra"]
        r["infra_detail"] = {"not_returned": inf["not_returned"], "wrapper_infra": inf["wrapper_infra"]}
    scored = [r for r in recs if not r["infra_candidate"] and not r["integrity_flag"]]
    out = {"schema": "x1-smoke-score/2", "run_id": cfg["run_id"], "scored_utc": now_utc(),
           "label": SCORE_LABEL, "mithi_sha256": cfg["mithi_sha256"], "attempts": recs,
           "infra_candidates": [r["attempt_id"] for r in recs if r["infra_candidate"]],
           "integrity_flags": [r["attempt_id"] for r in recs if r["integrity_flag"]],
           "aggregate_note": "infrastructure candidates and integrity-flagged attempts are left out of the aggregates",
           "aggregate": aggregate(scored)}
    write_json(root / "results" / "score.json", out)
    a = out["aggregate"]
    print(json.dumps({"scored": len(recs), "infra_candidates": out["infra_candidates"],
                      "integrity_flags": out["integrity_flags"], "by_arm": a["by_arm"]}, indent=1))


# ----------------------------------------------------------------------------- transcripts

def _usage_fields(u: dict) -> dict:
    return {"input": u.get("input_tokens", 0) or 0, "cache_creation": u.get("cache_creation_input_tokens", 0) or 0,
            "cache_read": u.get("cache_read_input_tokens", 0) or 0, "output": u.get("output_tokens", 0) or 0}


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def _harness_reply(text: str) -> dict:
    """The wrapper's JSON reply inside a Bash tool result (call number, error), if any."""
    t = text.strip()
    i = t.find("{")
    if i >= 0:
        try:
            j = json.loads(t[i:t.rfind("}") + 1])
            if isinstance(j, dict):
                return {"call": j.get("call"), "error": j.get("error"), "refunded": j.get("refunded")}
        except ValueError:
            pass
    m = re.search(r'"call":\s*(\d+)', t)
    return {"call": int(m.group(1)) if m else None, "error": None, "refunded": None}


def transcript_summary(path: Path) -> dict:
    """Per-agent facts from a Claude Code agent transcript (agent-<id>.jsonl) [M].

    Usage: records of one API message (same message.id) repeat its usage; the input-side fields are
    equal across them and output_tokens grows, so each field's maximum over the message's records is
    used. What was sent to the API: `api-request` records (params.model, params.output_config.effort)
    and `api-request-shape` records (the tool list), plus the sibling .prefix.json's toolNames.
    """
    msgs, order, msg_ts = {}, [], {}
    models, efforts, turn_efforts, versions, req_models = set(), set(), set(), set(), set()
    api_models, api_efforts, tools_offered, cwds = set(), set(), set(), set()
    system_chars = 0
    instruction_files, attachment_types = [], {}
    first = last = None
    tools, results = [], {}
    final_text = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        ts = r.get("timestamp")
        if ts:
            first = ts if first is None or ts < first else first
            last = ts if last is None or ts > last else last
        if r.get("cwd"):
            cwds.add(r["cwd"])
        typ = r.get("type")
        if typ == "api-request":
            p = r.get("params") or {}
            if p.get("model"):
                api_models.add(p["model"])
            eff = (p.get("output_config") or {}).get("effort")
            if eff:
                api_efforts.add(str(eff))
            continue
        if typ == "api-request-shape":
            sh = r.get("shape") or {}
            for t in sh.get("tools") or []:
                if isinstance(t, dict) and t.get("name"):
                    tools_offered.add(t["name"])
            system_chars = max(system_chars, sum(len(b.get("text", "")) for b in sh.get("system") or []
                                                 if isinstance(b, dict)))
            continue
        if typ == "attachment":
            a = r.get("attachment") or {}
            attachment_types[a.get("type")] = attachment_types.get(a.get("type"), 0) + 1
            if a.get("type") == "instructions":
                for f in a.get("files") or []:
                    instruction_files.append({"path": f.get("path"), "type": f.get("type"),
                                              "chars": len(f.get("content") or "")})
            continue
        if typ == "user":
            for b in (r.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = _result_text(b.get("content"))
            continue
        if typ != "assistant":
            continue
        m = r.get("message") or {}
        mid = m.get("id") or r.get("uuid")
        u = _usage_fields(m.get("usage") or {})
        if mid not in msgs:
            msgs[mid] = u
            order.append(mid)
            msg_ts[mid] = ts
        else:
            msgs[mid] = {k: max(msgs[mid][k], u[k]) for k in u}
        if m.get("model"):
            models.add(m["model"])
        for k, s in (("effort", efforts), ("perTurnEffort", turn_efforts), ("version", versions),
                     ("requestedModel", req_models)):
            if r.get(k) is not None:
                s.add(str(r[k]))
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                inp = b.get("input") or {}
                tools.append({"id": b.get("id"), "name": b.get("name"), "command": inp.get("command"),
                              "file_path": inp.get("file_path"),
                              "content": inp.get("content") if b.get("name") == "Write" else None})
            elif isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                final_text = b["text"]
    pj = path.with_name(path.stem + ".prefix.json")
    if pj.exists():
        try:
            for n in ((read_json(pj).get("state") or {}).get("toolNames") or []):
                tools_offered.add(n)
        except ValueError:
            pass
    seen_tool = {}
    for t in tools:
        seen_tool[t["id"] or len(seen_tool)] = t
    tools = list(seen_tool.values())
    for t in tools:
        t["result"] = results.get(t["id"])
    tot = {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
    for u in msgs.values():
        for k in tot:
            tot[k] += u[k]
    first_msg = msgs[order[0]] if order else {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
    final = msgs[order[-1]] if order else first_msg
    return {
        "api_messages": len(order),
        "usage_sum": tot,
        "processed_incl_cache_reads": tot["input"] + tot["cache_creation"] + tot["cache_read"] + tot["output"],
        "processed_excl_cache_reads": tot["input"] + tot["cache_creation"] + tot["output"],
        "first_call_input_side": first_msg["input"] + first_msg["cache_creation"] + first_msg["cache_read"],
        "final_context": final["input"] + final["cache_creation"] + final["cache_read"],
        "models": sorted(models), "requested_models": sorted(req_models), "effort": sorted(efforts),
        "per_turn_effort": sorted(turn_efforts), "claude_code_versions": sorted(versions),
        "api_models": sorted(api_models), "api_efforts": sorted(api_efforts),
        "tools_offered": sorted(tools_offered), "system_prompt_chars": system_chars,
        "cwds": sorted(cwds), "instruction_files": instruction_files, "attachment_types": attachment_types,
        "first_utc": first, "last_utc": last, "tool_uses": tools,
        "final_text": (final_text or "")[-2000:],
        "_messages": [(msg_ts[mid], msgs[mid]) for mid in order],
    }


def over_budget(s: dict) -> dict:
    """Usage past each record 2.3 item 6 budget the kit does not enforce [D from M] (review 1,
    finding 6): what a budget-enforcing runner would not have spent."""
    msgs = s["_messages"]
    prefix = s["first_call_input_side"]
    t0 = parse_t(s["first_utc"])
    proc = [u["input"] + u["cache_creation"] + u["cache_read"] + u["output"] for _, u in msgs]
    after_turn = sum(proc[TURN_BUDGET:])
    after_wall, nonprefix, after_np, out_cum, after_out = 0, 0, 0, 0, 0
    for (ts, u), p in zip(msgs, proc):
        t = parse_t(ts)
        if t0 and t and (t - t0).total_seconds() > WALL_BUDGET_S:
            after_wall += p
        if nonprefix > NONPREFIX_INPUT_BUDGET:
            after_np += p
        if out_cum > OUTPUT_BUDGET:
            after_out += p
        nonprefix += max(0, u["input"] + u["cache_creation"] + u["cache_read"] - prefix)
        out_cum += u["output"]
    t1 = parse_t(s["last_utc"])
    wall = (t1 - t0).total_seconds() if t0 and t1 else None
    res = {"turns": len(msgs), "wall_s": wall, "nonprefix_input_cum": nonprefix, "output_cum": out_cum,
           "prefix_proxy_first_call": prefix,
           "processed_after_turn_60": after_turn, "processed_after_45_min": after_wall,
           "processed_after_600k_nonprefix": after_np, "processed_after_60k_output": after_out}
    res["any_over"] = bool(len(msgs) > TURN_BUDGET or (wall or 0) > WALL_BUDGET_S
                           or nonprefix > NONPREFIX_INPUT_BUDGET or out_cum > OUTPUT_BUDGET)
    res["processed_past_any_budget_max"] = max(after_turn, after_wall, after_np, after_out)
    return res


SAFE_REASON = r"[A-Za-z0-9 ,.:_()<>=+\-]{0,200}"
SAFE_BARE = r"[A-Za-z0-9 ,.:_=+\-]{0,200}"


def harness_cmd_re(cmd: str):
    """The only Bash commands a subject may run: the attempt's harness commands, an abandon reason
    quoted or bare from a restricted alphabet; no shell metacharacters, no second line (review 1,
    finding 4)."""
    return re.compile("^" + re.escape(cmd) + r" (check( --tests)?|submit|abandon( '" + SAFE_REASON + "'| \""
                      + SAFE_REASON + "\"| " + SAFE_BARE + ")?)[ ]*\\Z")


def audit_tools(att: dict, tools: list, check_sequence: bool = True) -> dict:
    """Every tool use must be Write to the attempt's solution file or Bash running one of the
    attempt's harness commands. Anything else is flagged (it is not blocked: see SMOKE.md). A Rust
    Write whose content hits the static gate is flagged too; and the harness replies in the
    transcript must show call numbers 1, 2, ... within the budget."""
    sol = att["solution_path"].lower().replace("\\", "/")
    allowed_cmd = harness_cmd_re(att["cmd"])
    flags = []
    counts = {}
    calls_seen = []
    for t in tools:
        counts[t["name"]] = counts.get(t["name"], 0) + 1
        if t["name"] == "Write":
            fp = (t.get("file_path") or "").lower().replace("\\", "/")
            if fp != sol:
                flags.append({"tool": "Write", "file_path": t.get("file_path")})
            elif att.get("arm") == "rust" and t.get("content"):
                hits = C.rust_static_gate(t["content"])
                if hits:
                    flags.append({"tool": "Write", "static_gate": sorted({h["what"] for h in hits})})
        elif t["name"] == "Bash":
            c = (t.get("command") or "").strip()
            if not allowed_cmd.match(c):
                flags.append({"tool": "Bash", "command": c[:300]})
            elif t.get("result") is not None and re.search(r" check( --tests)?$", c):
                rep = _harness_reply(t["result"])
                if rep["call"] is not None:
                    calls_seen.append(rep["call"])
        else:
            flags.append({"tool": t["name"]})
    if check_sequence and (calls_seen != list(range(1, len(calls_seen) + 1)) or len(calls_seen) > CHECK_BUDGET):
        flags.append({"integrity": "harness call numbers in the transcript are not 1, 2, ... within the budget",
                      "calls_seen": calls_seen})
    return {"tool_counts": counts, "flags": flags, "clean": not flags, "harness_calls_seen": calls_seen}


def collect_agents(workflow_dirs: list) -> list:
    """(label, agent_id, meta, transcript path, journal result) for every agent of the given runs."""
    out = []
    for wdir in workflow_dirs:
        wd = Path(wdir)
        labels, results = {}, {}
        jp = wd / "journal.jsonl"
        if jp.exists():
            for line in jp.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                e = json.loads(line)
                if e.get("type") == "started" and e.get("agentId"):
                    labels[e["agentId"]] = e.get("label")
                if e.get("type") == "result" and e.get("agentId"):
                    results[e["agentId"]] = e.get("result")
        for f in sorted(wd.glob("agent-*.jsonl")):
            agent_id = f.stem[len("agent-"):]
            meta_p = f.with_name(f.stem + ".meta.json")
            meta = read_json(meta_p) if meta_p.exists() else {}
            label = labels.get(agent_id) or meta.get("description")
            out.append({"label": label, "agent_id": agent_id, "meta": meta, "path": f, "workflow_dir": str(wd),
                        "journal_result": results.get(agent_id)})
    return out


def cmd_tokens(args) -> None:
    root = Path(args.root).resolve()
    cfg = read_json(root / "RUN.json")
    plan = load_plan(root)
    plan_attempts = all_attempt_entries(plan)
    probe_labels = set((cfg.get("probe") or {}).get("labels", {}).values())
    per_attempt, unmatched, probe_agents = {}, [], []
    for ag in collect_agents(args.workflow_dir):
        s = transcript_summary(ag["path"])
        s.update({"agent_id": ag["agent_id"], "agent_type": ag["meta"].get("agentType"),
                  "workflow_dir": ag["workflow_dir"]})
        label = ag["label"]
        if label in plan_attempts:
            att = dict(plan_attempts[label])
            s["audit"] = audit_tools(att, s.pop("tool_uses"))
            s["over_budget"] = over_budget(s)
            s.pop("_messages")
            per_attempt.setdefault(label, []).append(s)
        else:
            s.pop("tool_uses", None)
            s.pop("_messages", None)
            (probe_agents if label in probe_labels else unmatched).append({"label": label, **s})
    rows = []
    for aid, lst in sorted(per_attempt.items()):
        pa = plan_attempts[aid]
        for s in lst:
            rows.append({"attempt_id": aid, "batch": pa["batch"], "task": pa["task"], "arm": pa["arm"],
                         "kind": "replacement" if pa.get("replaces") else "planned", **s})

    def total(rs):
        t = {"agents": len(rs), "processed_incl_cache_reads": 0, "processed_excl_cache_reads": 0,
             "output": 0, "cache_read": 0, "cache_creation": 0, "input": 0, "final_context_sum": 0}
        for r in rs:
            t["processed_incl_cache_reads"] += r["processed_incl_cache_reads"]
            t["processed_excl_cache_reads"] += r["processed_excl_cache_reads"]
            t["final_context_sum"] += r["final_context"]
            for k in ("output", "cache_read", "cache_creation", "input"):
                t[k] += r["usage_sum"][k]
        return t

    def means(rs):
        n = len(rs)
        if not n:
            return None
        return {"agents": n,
                "processed_incl_cache_reads": sum(r["processed_incl_cache_reads"] for r in rs) / n,
                "processed_excl_cache_reads": sum(r["processed_excl_cache_reads"] for r in rs) / n,
                "turns": sum(r["api_messages"] for r in rs) / n,
                "first_call_input_side": sum(r["first_call_input_side"] for r in rs) / n,
                "processed_past_any_budget": sum(r["over_budget"]["processed_past_any_budget_max"] for r in rs) / n}

    by_batch = {str(b): total([r for r in rows if r["batch"] == b]) for b, _, _ in cfg["batches"]}
    by_task_arm = {f"{tid}/{arm}": means([r for r in rows if r["task"] == tid and r["arm"] == arm])
                   for tid in L.TASK_IDS for arm in L.ARMS}
    subject_unmatched = [u for u in unmatched if u.get("agent_type") == "x1-subject"]
    root_n = norm_path(root)
    checks = {
        "models": sorted({m for r in rows for m in r["models"]}),
        "api_models": sorted({m for r in rows for m in r["api_models"]}),
        "effort": sorted({e for r in rows for e in r["effort"]}),
        "api_efforts": sorted({e for r in rows for e in r["api_efforts"]}),
        "per_turn_effort": sorted({e for r in rows for e in r["per_turn_effort"]}),
        "claude_code_versions": sorted({v for r in rows for v in r["claude_code_versions"]}),
        "agent_types": sorted({str(r["agent_type"]) for r in rows}),
        "tools_offered": sorted({t for r in rows for t in r["tools_offered"]}),
        "cwds": sorted({c for r in rows for c in r["cwds"]}),
        "instruction_files": sorted({f"{f['type']}:{f['path']}" for r in rows for f in r["instruction_files"]}),
        "attempts_with_tool_flags": sorted({r["attempt_id"] for r in rows if not r["audit"]["clean"]}),
        "attempts_with_several_transcripts": sorted(a for a, l in per_attempt.items() if len(l) > 1),
        "attempts_over_a_budget": sorted({r["attempt_id"] for r in rows if r["over_budget"]["any_over"]}),
        "unmatched_subject_agents": [u.get("label") for u in subject_unmatched],
        "attempts_without_tool_list": sorted({r["attempt_id"] for r in rows if not r["tools_offered"]}),
    }
    checks["model_is_pinned"] = bool(rows) and checks["models"] == [FULL_MODEL_ID] and \
        checks["api_models"] in ([FULL_MODEL_ID], [])
    checks["effort_is_max"] = bool(rows) and (checks["api_efforts"] or checks["effort"]) == [PINNED_EFFORT] and \
        set(checks["effort"]) <= {PINNED_EFFORT} and set(checks["per_turn_effort"]) <= {PINNED_EFFORT}
    checks["agent_type_is_subject"] = checks["agent_types"] == ["x1-subject"]
    # an extra tool the lead engineer accepted at the probe (--allow-extra-tool, a logged deviation)
    pp = root / "results" / "probe.json"
    allowed = set(SUBJECT_TOOLS)
    if pp.exists():
        allowed |= set(((read_json(pp).get("main") or {}).get("allowed_extra_tools")) or [])
    checks["allowed_tools"] = sorted(allowed)
    checks["tools_only_write_bash"] = bool(rows) and not checks["attempts_without_tool_list"] and \
        set(checks["tools_offered"]) <= allowed
    checks["claude_code_version_single"] = len(checks["claude_code_versions"]) == 1
    checks["cwd_is_run_root"] = bool(checks["cwds"]) and all(norm_path(c) == root_n for c in checks["cwds"])
    checks["no_instruction_files"] = not checks["instruction_files"]
    out = {"schema": "x1-smoke-tokens/2", "run_id": cfg["run_id"], "extracted_utc": now_utc(),
           "workflow_dirs": [str(Path(w)) for w in args.workflow_dir],
           "basis_note": ("usage_sum fields are Claude Code's per-API-message usage, summed over each "
                          "agent's messages [M]; processed_incl_cache_reads = input + cache_creation + "
                          "cache_read + output; final_context = the last message's input side, which is what a "
                          "workflow report's 'subagent tokens' total sums over agents [D, SMOKE.md]; "
                          "first_call_input_side = the per-attempt prefix proxy (system prompt, tools and the "
                          "task message) [M]; over_budget = usage after each unenforced record 2.3 budget [D]"),
           "checks": checks, "by_batch": by_batch, "by_task_arm_means": by_task_arm, "all": total(rows),
           "attempts": rows, "unmatched_agents": unmatched, "unmatched_total": total(unmatched),
           "probe_agents": probe_agents}
    write_json(root / "results" / "tokens.json", out)
    print(json.dumps({"checks": checks, "by_batch": by_batch, "all": out["all"], "unmatched": len(unmatched),
                      "unmatched_total": out["unmatched_total"]}, indent=1))


# ----------------------------------------------------------------------------- probe

def cmd_probe(args) -> None:
    root = Path(args.root).resolve()
    cfg = read_json(root / "RUN.json")
    labels = cfg["probe"]["labels"]
    agents = {a["label"]: a for a in collect_agents(args.workflow_dir)}
    out = {"schema": "x1-smoke-probe/1", "run_id": cfg["run_id"], "evaluated_utc": now_utc(),
           "workflow_dirs": [str(Path(w)) for w in args.workflow_dir], "problems": []}
    allow_extra = set(args.allow_extra_tool or [])
    main = agents.get(labels["main"])
    if not main:
        out["problems"].append(f"no transcript labelled {labels['main']} in the given workflow directories")
    else:
        s = transcript_summary(main["path"])
        att = {"solution_path": fwd(root / "attempts" / cfg["probe"]["attempt_id"] / "work" / "solution.rs"),
               "cmd": all_probe_cmd(root, cfg), "arm": "rust"}
        audit = audit_tools(att, s.pop("tool_uses"), check_sequence=False)
        s.pop("_messages")
        li = log_integrity(root / "attempts" / cfg["probe"]["attempt_id"])
        extra = sorted(set(s["tools_offered"]) - SUBJECT_TOOLS - allow_extra)
        root_n = norm_path(root)
        allowed_cwds = {root_n} | {norm_path(c) for c in (args.allow_cwd or [])}
        m = {
            "agent_type": main["meta"].get("agentType"),
            "tools_offered": s["tools_offered"], "extra_tools": extra, "allowed_extra_tools": sorted(allow_extra),
            "models": s["models"], "api_models": s["api_models"], "effort": s["effort"],
            "api_efforts": s["api_efforts"], "per_turn_effort": s["per_turn_effort"],
            "claude_code_versions": s["claude_code_versions"], "cwds": s["cwds"],
            "instruction_files": s["instruction_files"], "attachment_types": s["attachment_types"],
            "first_call_input_side": s["first_call_input_side"], "system_prompt_chars": s["system_prompt_chars"],
            "api_messages": s["api_messages"], "audit": audit, "probe_attempt_log": li,
            "final_text": s["final_text"], "first_utc": s["first_utc"], "last_utc": s["last_utc"],
        }
        m["checks"] = {
            "agent_type_is_subject": m["agent_type"] == "x1-subject",
            "tools_are_write_and_bash": bool(s["tools_offered"]) and not extra,
            "model_is_pinned": s["models"] == [FULL_MODEL_ID] and s["api_models"] in ([FULL_MODEL_ID], []),
            "effort_is_max": (s["api_efforts"] or s["effort"]) == [PINNED_EFFORT] and
                             set(s["effort"]) <= {PINNED_EFFORT},
            "cwd_is_run_root": bool(s["cwds"]) and all(norm_path(c) in allowed_cwds for c in s["cwds"]),
            "harness_reached": audit["clean"] and len(audit["harness_calls_seen"]) == 1 and li["counted_calls"] >= 1,
        }
        m["isolation"] = {"no_instruction_files": not s["instruction_files"],
                          "note": "instruction files (CLAUDE.md, auto-memory) reaching the subject are a record "
                                  "2.3 item 2 deviation; reported, not a pin"}
        out["main"] = m
        for k, v in m["checks"].items():
            if not v:
                out["problems"].append(f"probe check failed: {k}")
    fid = agents.get(labels["fullid"])
    if fid:
        s = transcript_summary(fid["path"])
        out["full_model_id"] = {"tested": True, "transcript": True, "models": s["models"],
                                "api_models": s["api_models"],
                                "accepted": s["models"] == [FULL_MODEL_ID] and s["api_messages"] > 0}
    else:
        out["full_model_id"] = {"tested": cfg["model"] != FULL_MODEL_ID, "transcript": False,
                                "accepted": None if cfg["model"] == FULL_MODEL_ID else False}
    tc = agents.get(labels["turncap"])
    if tc:
        s = transcript_summary(tc["path"])
        bash = [t for t in s["tool_uses"] if t["name"] == "Bash"]
        out["turncap"] = {"api_messages": s["api_messages"], "bash_calls": len(bash), "asked_for": 5,
                          "maxTurns_frontmatter": 2,
                          "honoured": len(bash) < 5,
                          "note": "honoured = fewer Bash calls than asked for under maxTurns: 2 [M]"}
    else:
        out["turncap"] = {"api_messages": None, "honoured": None, "note": "no turn-cap transcript"}
    ends = [a for a in (agents.get(labels[k]) for k in ("main", "fullid", "turncap")) if a]
    out["end_utc"] = max((transcript_summary(a["path"])["last_utc"] or "") for a in ends) if ends else None
    out["ok"] = not out["problems"]
    write_json(root / "results" / "probe.json", out)
    print(json.dumps({k: out[k] for k in ("ok", "problems", "full_model_id", "turncap", "end_utc")}, indent=1))


def all_probe_cmd(root: Path, cfg: dict) -> str:
    adir = root / "attempts" / cfg["probe"]["attempt_id"]
    return f"\"{fwd(cfg['python'])}\" \"{fwd(root / 'harness' / 'x1check.py')}\" \"{fwd(adir)}\""


# ----------------------------------------------------------------------------- the 6.2 gate

def w_star(s=GATE_S, K=GATE_K, A=GATE_A) -> Fraction:
    return Fraction(100) * Fraction(s) * K / A


def gate_decide(delta: int, n: int, ws: Fraction, slack: int = 1) -> str:
    """X1-amendment-1 6.2 step 3 (slack = 1), or step 5's variant (slack = k after k batches)."""
    if n <= 0:
        return "NO_DATA"
    if Fraction(delta - slack, n) > ws:
        return "NOT_RUNNABLE"
    if Fraction(delta + slack, n) <= ws:
        return "RUNNABLE"
    return "CONTINUE"


def p2_status(reading: dict, reset_utc) -> dict:
    """Record 2.4 P2 on one reading: no new attempt while weekly > days/7*100 + 15 or 5-hour > 80."""
    p2 = {"t_utc": reading.get("t_utc"), "weekly": reading.get("weekly_all_models_pct"),
          "five_hour": reading.get("five_hour_pct")}
    t, r = parse_t(reading.get("t_utc")), parse_t(reset_utc)
    if t and r and type(p2["weekly"]) is int:
        days = ((t - r).total_seconds() / 86400.0) % 7.0
        p2["days_since_reset"] = round(days, 3)
        p2["weekly_stop_line"] = round(days / 7.0 * 100 + 15, 2)
        p2["weekly_ok"] = p2["weekly"] <= p2["weekly_stop_line"]
    if type(p2["five_hour"]) is int:
        p2["five_hour_ok"] = p2["five_hour"] <= 80
    p2["start_allowed"] = bool(p2.get("weekly_ok") and p2.get("five_hour_ok"))
    return p2


def validate_readings(rd: dict) -> dict:
    """Mandatory fields, time order, weekly windows and monotonicity (review 1, finding 1).

    Returns {"problems", "readings": [normalised readings in time order], "reset"}.
    """
    problems = []
    reset = parse_t(rd.get("weekly_reset_utc"))
    if reset is None:
        problems.append("weekly_reset_utc is missing or not an ISO-8601 UTC time")
    out = []
    for i, r in enumerate(rd.get("readings") or []):
        kind = r.get("kind") or ("gate" if "after_batch" in r else None)
        t = parse_t(r.get("t_utc"))
        w, f = r.get("weekly_all_models_pct"), r.get("five_hour_pct")
        if kind not in ("gate", "p2"):
            problems.append(f"reading {i}: kind must be 'gate' or 'p2'")
        if t is None:
            problems.append(f"reading {i}: t_utc missing or not an ISO-8601 UTC time")
        if type(w) is not int or not 0 <= w <= 100:
            problems.append(f"reading {i}: weekly_all_models_pct must be a whole number 0-100, got {w!r}")
        if type(f) is not int or not 0 <= f <= 100:
            problems.append(f"reading {i}: five_hour_pct must be a whole number 0-100, got {f!r}")
        if kind == "gate" and type(r.get("after_batch")) is not int:
            problems.append(f"reading {i}: a gate reading needs an integer after_batch")
        out.append({**r, "kind": kind, "_t": t, "_i": i,
                    "_window": ((t - reset) // WEEK) if (t and reset) else None})
    ts = [r["_t"] for r in out]
    if all(ts) and any(b < a for a, b in zip(ts, ts[1:])):
        problems.append("readings are not in time order")
    if not problems:
        for a, b in zip(out, out[1:]):
            if a["_window"] == b["_window"] and b["weekly_all_models_pct"] < a["weekly_all_models_pct"]:
                problems.append(f"readings {a['_i']} -> {b['_i']}: the weekly reading decreased inside one window")
    return {"problems": problems, "readings": out, "reset": reset}


def gate_history_lookup(root: Path, sha: str):
    hd = root / "results" / "gate_history"
    if not sha or not hd.exists():
        return None
    for p in sorted(hd.glob("gate_*.json")):
        b = p.read_bytes()
        if hashlib.sha256(b).hexdigest() == sha:
            return json.loads(b)
    return None


def batch_records(root: Path, cfg: dict, tokens: dict, dispositions: dict) -> dict:
    """Per batch: the attempts that ran (from the saved workflow results), which count in N, their
    transcript times; and every inconsistency between results, transcripts, logs and gate history
    (review 1, findings 9 and 12)."""
    problems, caveats = [], []
    planned = {a["id"]: a for a in cfg["attempts"]}
    repl = {r["id"]: r for r in cfg.get("replacements") or []}
    files = sorted((root / "results").glob("batch_*.workflow.json"))
    runs, seen_keys, where = {}, {}, {}
    for p in files:
        try:
            d = read_json(p)
        except ValueError:
            problems.append(f"{p.name}: not JSON")
            continue
        if d.get("schema") != "x1-smoke-batch-result/2":
            problems.append(f"{p.name}: schema is not x1-smoke-batch-result/2")
            continue
        if d.get("run_id") != cfg["run_id"] or d.get("plan_sha256") != cfg.get("plan_sha256"):
            problems.append(f"{p.name}: run_id or plan_sha256 does not match RUN.json")
            continue
        key = (d.get("batch"), d.get("wave"), tuple(d.get("replace") or []))
        body = json.dumps(d.get("attempts"), sort_keys=True)
        if key in seen_keys:
            if seen_keys[key] != body:
                problems.append(f"{p.name}: batch {key[0]} wave/replace {key[1:]} saved twice with different results")
            continue
        seen_keys[key] = body
        runs.setdefault(d.get("batch"), []).append({"file": p.name, **d})
        for a in d.get("attempts") or []:
            aid = a.get("attempt_id")
            if aid in where and where[aid] != p.name:
                problems.append(f"attempt {aid} appears in {where[aid]} and {p.name} (relaunched without resume?)")
            where[aid] = p.name
    launched = {}
    for b, lst in runs.items():
        for d in lst:
            for a in d.get("attempts") or []:
                launched[a["attempt_id"]] = {"returned": bool(a.get("returned")), "batch": b}
    tok_rows = {}
    for r in (tokens or {}).get("attempts") or []:
        tok_rows.setdefault(r["attempt_id"], []).append(r)
    excluded = {d["attempt_id"] for d in (dispositions or {}).get("dispositions") or [] if d.get("exclude_from_N")}
    out = {}
    for b, lo, hi in cfg["batches"]:
        if b not in runs:
            break
        want = [a["id"] for a in cfg["attempts"] if a["batch"] == b]
        ran = [aid for aid, v in launched.items() if v["batch"] == b]
        missing = [aid for aid in want if aid not in launched]
        if missing:
            problems.append(f"batch {b} incomplete: planned attempts not run: {missing}")
        for aid in ran:
            if aid not in planned and aid not in repl:
                problems.append(f"batch {b}: unknown attempt {aid}")
            if aid in planned and planned[aid]["batch"] != b:
                problems.append(f"attempt {aid} of batch {planned[aid]['batch']} ran in batch {b}")
        ran = [a for a in ran if a in planned or a in repl]
        info = {aid: infra_status(root, aid, launched) for aid in ran}
        for aid in ran:
            if aid in repl:
                orig = repl[aid]["replaces"]
                if repl[aid]["batch"] != b:
                    problems.append(f"replacement {aid} ran in batch {b}, its original is in batch {repl[aid]['batch']}")
                elif orig not in info or not info[orig]["infra"]:
                    problems.append(f"replacement {aid} ran, but {orig} is not an infrastructure failure of batch {b}")
        infra = sorted(a for a in ran if info[a]["infra"])
        integ = sorted(a for a in ran if not info[a]["integrity"]["ok"])
        counted = sorted(a for a in ran if a not in infra and a not in integ and a not in excluded)
        unreplaced = [a for a in infra if a in planned and (a + "-r1") not in ran]
        if unreplaced:
            caveats.append(f"batch {b}: infrastructure failures not replaced: {unreplaced} (N below plan; "
                           f"their usage stays in the reading)")
        # transcript times; the gate needs them for every attempt that returned
        firsts, lasts = [], []
        for aid in ran:
            rows = tok_rows.get(aid) or []
            for r in rows:
                if r.get("first_utc"):
                    firsts.append(r["first_utc"])
                if r.get("last_utc"):
                    lasts.append(r["last_utc"])
        no_transcript = [a for a in ran if launched[a]["returned"] and not tok_rows.get(a)]
        if b > 1:
            for d in runs[b]:
                gh = gate_history_lookup(root, d.get("gate_sha256"))
                last = (gh or {}).get("steps") or [{}]
                if not gh or gh.get("decision") != "CONTINUE" or last[-1].get("batch") != b - 1:
                    problems.append(f"{d['file']}: gate_sha256 does not name a stored gate result that said "
                                    f"CONTINUE after batch {b - 1}")
        waves = [{"file": d["file"], "wave": d.get("wave"), "replace": d.get("replace"),
                  "first_utc": min((r["first_utc"] for a in (x["attempt_id"] for x in d.get("attempts") or [])
                                    for r in tok_rows.get(a) or [] if r.get("first_utc")), default=None)}
                 for d in runs[b]]
        out[b] = {"ran": sorted(ran), "infra": infra, "integrity_flagged": integ,
                  "excluded_by_disposition": sorted(a for a in ran if a in excluded),
                  "counted": counted, "n": len(counted),
                  "n_if_infra_counted": len(counted) + len(infra),
                  "start_utc": min(firsts) if firsts else None, "end_utc": max(lasts) if lasts else None,
                  "no_transcript": no_transcript, "waves": waves}
    return {"batches": out, "problems": problems, "caveats": caveats}


def pins_status(root: Path, cfg: dict, tokens, probe, recs: dict) -> dict:
    """The model, effort, agent type and tools the record pins (2.1, 2.3), shown for the probe and
    for every attempt (review 1, finding 2)."""
    why = []
    if not probe:
        why.append("results/probe.json missing: run the probe before r0 (SMOKE.md 4.2)")
    elif not probe.get("ok"):
        why.append(f"probe not ok: {probe.get('problems')}")
    if not tokens:
        why.append("results/tokens.json missing: run x1smoke.py tokens on every batch's workflow directory")
    else:
        ch = tokens.get("checks") or {}
        for k in ("model_is_pinned", "effort_is_max", "agent_type_is_subject", "tools_only_write_bash"):
            if not ch.get(k):
                why.append(f"tokens check {k} is false")
        if ch.get("unmatched_subject_agents"):
            why.append(f"x1-subject transcripts with no plan label: {ch['unmatched_subject_agents']}")
    for b, info in recs.items():
        if info["no_transcript"]:
            why.append(f"batch {b}: no transcript in tokens.json for {info['no_transcript']}")
    return {"ok": not why, "why": why}


def audit_status(tokens, recs: dict, dispositions: dict) -> dict:
    flagged = set((tokens or {}).get("checks", {}).get("attempts_with_tool_flags") or [])
    for info in recs.values():
        flagged |= set(info["integrity_flagged"])
    disp = {d["attempt_id"]: d for d in (dispositions or {}).get("dispositions") or []
            if d.get("disposition") in ("benign", "misuse") and d.get("reviewer")}
    open_ = sorted(a for a in flagged if a not in disp)
    return {"flagged": sorted(flagged), "undisposed": open_, "dispositions": [disp[a] for a in sorted(disp)],
            "hold": bool(open_)}


def settle(readings: list, after: int, not_before, not_after):
    """r_k: the value of the last two gate readings after batch `after` when they agree. Only
    readings at least 10 min after the batch's last attempt ended count; the last two must be at
    least 10 min apart; none may be later than the next batch's first attempt. Returns
    (value, used_readings, incomplete_reason, problem)."""
    seq = [r for r in readings if r["kind"] == "gate" and r.get("after_batch") == after]
    if not_before is None:
        return None, seq, None, f"batch {after}: no end time (no transcripts in tokens.json and no last_attempt_end_utc)"
    if not_after is not None and any(r["_t"] > not_after for r in seq):
        return None, seq, None, f"batch {after}: a reading labelled after it was taken after the next batch started"
    ok = [r for r in seq if r["_t"] + TOL >= not_before + TEN_MIN]
    if len(ok) < 2:
        return None, ok, f"batch {after}: fewer than two readings at least 10 min after its last attempt ended", None
    a, b = ok[-2], ok[-1]
    if b["_t"] + TOL < a["_t"] + TEN_MIN:
        return None, ok, f"batch {after}: the last two readings are less than 10 min apart; read again", None
    if a["weekly_all_models_pct"] != b["weekly_all_models_pct"]:
        return None, ok, f"batch {after}: the last two readings disagree; keep reading every 10 min", None
    return b["weekly_all_models_pct"], ok, None, None


def evaluate_gate(rd: dict, ws: Fraction, recs: dict, batches_cfg: list, probe_end=None, pins=None,
                  audit=None, record_problems=None, record_caveats=None) -> dict:
    """The 6.2 decision on validated readings and batch records. Decision precedence: problems in
    the readings (INVALID_READINGS), in the batch records (INCONSISTENT_RECORDS), a weekly reset
    inside the measured interval (RESET_CROSSED), unverified pins (PINS_UNVERIFIED), undisposed
    audit flags (AUDIT_HOLD); only then READING_INCOMPLETE or the rule. Under any of the first five,
    no rule outcome is emitted."""
    v = validate_readings(rd)
    out = {"w_star": str(ws), "w_star_float": float(ws), "problems": list(v["problems"]),
           "record_problems": list(record_problems or []), "caveats": list(record_caveats or []), "steps": []}
    rs = v["readings"]
    quiet = rd.get("quiet_throughout", True)
    hand_end = {b.get("batch"): parse_t(b.get("last_attempt_end_utc")) for b in rd.get("batches") or []}
    steps, incomplete, reset_crossed = [], None, []
    if not out["problems"]:
        n_cum, n_alt, delta_cum = 0, 0, 0
        r0 = None
        if quiet:
            r0s = [r for r in rs if r["kind"] == "gate" and r.get("after_batch") == 0]
            if not r0s:
                out["problems"].append("no r0 reading (kind gate, after_batch 0)")
            else:
                r0 = r0s[-1]
                start1 = parse_t((recs.get(1) or {}).get("start_utc"))
                if start1 and r0["_t"] > start1:
                    out["problems"].append("r0 was read after the first attempt started")
                if probe_end and r0["_t"] < probe_end:
                    out["problems"].append("r0 was read before the probe ended")
        bs = [b for b, _, _ in batches_cfg]
        for i, b in enumerate(bs):
            if out["problems"] or b not in recs:
                break
            info = recs[b]
            end = max([t for t in (parse_t(info["end_utc"]), hand_end.get(b)) if t], default=None)
            nxt = parse_t((recs.get(bs[i + 1]) or {}).get("start_utc")) if i + 1 < len(bs) else None
            val, used, why_inc, why_bad = settle(rs, b, end, nxt)
            if why_bad:
                out["problems"].append(why_bad)
                break
            n_cum += info["n"]
            n_alt += info.get("n_if_infra_counted", info["n"])
            if val is None:
                incomplete = why_inc
                steps.append({"batch": b, "N": n_cum, "decision": "READING_INCOMPLETE"})
                break
            if quiet:
                if any(r["_window"] != r0["_window"] for r in rs if r0["_t"] <= r["_t"] <= used[-1]["_t"]):
                    reset_crossed.append(f"a weekly reset falls between r0 and the readings after batch {b}")
                    break
                delta = val - r0["weekly_all_models_pct"]
                slack = 1
            else:
                before = [r for r in rs if r["kind"] == "gate" and r.get("after_batch") == -b]
                if not before:
                    out["problems"].append(f"step-5 variant: no reading before batch {b} (after_batch = -{b})")
                    break
                bef = before[-1]
                if b == bs[0] and probe_end and bef["_t"] < probe_end:
                    out["problems"].append("step-5 variant: the reading before batch 1 was taken before the probe ended")
                    break
                st = parse_t(info["start_utc"])
                if st and bef["_t"] > st:
                    out["problems"].append(f"step-5 variant: the reading before batch {b} was taken after it started")
                    break
                if any(r["_window"] != bef["_window"] for r in rs if bef["_t"] <= r["_t"] <= used[-1]["_t"]):
                    reset_crossed.append(f"a weekly reset falls inside batch {b}'s before/after readings")
                    break
                if val < bef["weekly_all_models_pct"]:
                    out["problems"].append(f"batch {b}: negative change")
                    break
                delta_cum += val - bef["weekly_all_models_pct"]
                delta = delta_cum
                slack = b
            if delta < 0:
                out["problems"].append(f"batch {b}: negative change {delta}")
                break
            d = gate_decide(delta, n_cum, ws, slack)
            if d == "CONTINUE" and b == bs[-1]:
                d = "UNDETERMINED"
            steps.append({"batch": b, "N": n_cum, "N_if_infra_counted_info": n_alt, "delta": delta, "slack": slack,
                          "interval_points_per_attempt": [str(Fraction(delta - slack, n_cum)) if n_cum else None,
                                                          str(Fraction(delta + slack, n_cum)) if n_cum else None],
                          "interval_float": [float(Fraction(delta - slack, n_cum)) if n_cum else None,
                                             float(Fraction(delta + slack, n_cum)) if n_cum else None],
                          "decision": d})
            if d != "CONTINUE":
                break
    # P2 before every wave [caveat only: P2 is pacing, not measurement]
    for b, info in recs.items():
        for wv in info["waves"]:
            t = parse_t(wv["first_utc"])
            if not t:
                continue
            prior = [r for r in rs if r["_t"] and r["_t"] <= t]
            if not prior or not p2_status(prior[-1], rd.get("weekly_reset_utc"))["start_allowed"]:
                out["caveats"].append(f"batch {b} {wv['file']}: no reading allowing P2 before its first attempt")
    if out["problems"]:
        out["decision"] = "INVALID_READINGS"
    elif out["record_problems"]:
        out["decision"] = "INCONSISTENT_RECORDS"
    elif reset_crossed:
        out["decision"] = "RESET_CROSSED"
        out["reset"] = reset_crossed
    elif pins is not None and not pins["ok"]:
        out["decision"] = "PINS_UNVERIFIED"
    elif audit is not None and audit["hold"]:
        out["decision"] = "AUDIT_HOLD"
    elif incomplete:
        out["decision"] = "READING_INCOMPLETE"
        out["steps"] = steps
        out["incomplete"] = incomplete
    else:
        out["steps"] = steps
        out["decision"] = steps[-1]["decision"] if steps else "NO_DATA"
    if out["decision"] in ("INVALID_READINGS", "INCONSISTENT_RECORDS", "RESET_CROSSED", "PINS_UNVERIFIED",
                           "AUDIT_HOLD"):
        out["steps"] = []
        out["withheld"] = "no rule outcome is emitted until the cause above is resolved"
    if rs:
        out["p2_latest"] = p2_status(rs[-1], rd.get("weekly_reset_utc"))
    return out


def cmd_gate(args) -> None:
    if args.selftest:
        print(json.dumps(gate_selftest(), indent=1))
        return
    root = Path(args.root).resolve()
    cfg = read_json(root / "RUN.json")
    rd = read_json(root / "readings.json")
    tp, pp, dp = root / "results" / "tokens.json", root / "results" / "probe.json", root / "dispositions.json"
    tokens = read_json(tp) if tp.exists() else None
    probe = read_json(pp) if pp.exists() else None
    disp = read_json(dp) if dp.exists() else {"dispositions": []}
    br = batch_records(root, cfg, tokens, disp)
    pins = pins_status(root, cfg, tokens, probe, br["batches"])
    audit = audit_status(tokens, br["batches"], disp)
    if tokens:
        ch = tokens.get("checks") or {}
        if not ch.get("claude_code_version_single"):
            br["caveats"].append(f"several Claude Code versions: {ch.get('claude_code_versions')}")
        if not ch.get("cwd_is_run_root"):
            br["caveats"].append(f"subject working directory is not the run root: {ch.get('cwds')}")
        if not ch.get("no_instruction_files"):
            br["caveats"].append(f"instruction files reached the subjects: {ch.get('instruction_files')}")
        if ch.get("attempts_over_a_budget"):
            br["caveats"].append(f"attempts past an unenforced record 2.3 budget (w biased up): "
                                 f"{ch['attempts_over_a_budget']}")
        if ch.get("attempts_with_several_transcripts"):
            br["caveats"].append(f"attempts with several transcripts (usage in the reading, counted once): "
                                 f"{ch['attempts_with_several_transcripts']}")
    probe_end = parse_t((probe or {}).get("end_utc"))
    res = evaluate_gate(rd, w_star(), br["batches"], cfg["batches"], probe_end, pins, audit,
                        br["problems"], br["caveats"])
    res.update({"schema": "x1-smoke-gate/2", "run_id": cfg["run_id"], "evaluated_utc": now_utc(),
                "rule": "X1-amendment-1 6.2 step 3 (quiet) or step 5 (not quiet); s=1/2, K=6, A=3456 [target]",
                "pins": pins, "audit": audit,
                "batches": {str(b): info for b, info in br["batches"].items()},
                "standing_caveats": [
                    "development items D-*, not DESIGN 5.2's S-*-0 set; no T-STORE or T-CTRL item (w may be low)",
                    "x1-subject subagent prefix, not a headless Claude Code session's (w may be low or high)",
                    "turn and token budgets measured, not enforced (w biased up); see tokens over_budget"]})
    text = json.dumps(res, indent=1, sort_keys=True)
    hd = root / "results" / "gate_history"
    hd.mkdir(parents=True, exist_ok=True)
    n = len(list(hd.glob("gate_*.json"))) + 1
    (hd / f"gate_{n:03d}.json").write_bytes(text.encode("utf-8"))
    (root / "results" / "gate.json").write_bytes(text.encode("utf-8"))
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(text)
    print(json.dumps({"decision": res["decision"], "gate_sha256": sha,
                      "note": "pass gate_sha256 to the next batch's workflow args only when the decision is CONTINUE"}))


def cmd_p2(args) -> None:
    root = Path(args.root).resolve()
    rd = read_json(root / "readings.json")
    v = validate_readings(rd)
    if not v["readings"]:
        raise SystemExit("no readings yet")
    res = p2_status(v["readings"][-1], rd.get("weekly_reset_utc"))
    res["reading_problems"] = v["problems"]
    print(json.dumps({k: (str(x) if isinstance(x, dt.datetime) else x) for k, x in res.items()}, indent=1))


def gate_fixture_tests() -> dict:
    """evaluate_gate on fixed readings with known answers (no files): the rule, the settling
    checks, and the review-1 cases (a weekly reset inside the interval, missing timestamps, a
    non-integer reading, a decrease)."""
    base = {"quiet_throughout": True, "weekly_reset_utc": "2026-10-23T12:00:00Z"}

    def R(ab, t, w, day="2026-10-24", kind="gate"):
        r = {"kind": kind, "t_utc": f"{day}T{t}:00Z", "weekly_all_models_pct": w, "five_hour_pct": 30}
        if kind == "gate":
            r["after_batch"] = ab
        return r

    def B(n, start, end, day="2026-10-24"):
        return {"n": n, "start_utc": f"{day}T{start}:00Z", "end_utc": f"{day}T{end}:00Z", "waves": []}
    cfgb = BATCHES
    cases = {
        "runnable_at_45": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 10), R(1, "14:21", 10),
                                                R(2, "17:11", 11), R(2, "17:21", 11), R(3, "20:11", 11),
                                                R(3, "20:21", 11)]),
                           {1: B(5, "13:05", "14:00"), 2: B(20, "14:30", "17:00"), 3: B(20, "17:30", "20:00")},
                           "RUNNABLE"),
        "not_runnable_at_5": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 12), R(1, "14:21", 12)]),
                              {1: B(5, "13:05", "14:00")}, "NOT_RUNNABLE"),
        "readings_disagree": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 10), R(1, "14:21", 11)]),
                              {1: B(5, "13:05", "14:00")}, "READING_INCOMPLETE"),
        "first_reading_too_early": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:05", 10), R(1, "14:15", 10)]),
                                    {1: B(5, "13:05", "14:00")}, "READING_INCOMPLETE"),
        "last_two_too_close": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 10), R(1, "14:15", 10)]),
                               {1: B(5, "13:05", "14:00")}, "READING_INCOMPLETE"),
        "undetermined_at_65": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 9), R(1, "14:21", 9),
                                                    R(2, "17:11", 11), R(2, "17:21", 11), R(3, "20:11", 13),
                                                    R(3, "20:21", 13), R(4, "23:11", 14), R(4, "23:21", 14)]),
                               {1: B(5, "13:05", "14:00"), 2: B(20, "14:30", "17:00"), 3: B(20, "17:30", "20:00"),
                                4: B(20, "20:30", "23:00")}, "UNDETERMINED"),
        "step5_continue": (dict(base, quiet_throughout=False,
                                readings=[R(-1, "13:00", 9), R(1, "14:11", 10), R(1, "14:21", 10), R(-2, "15:00", 13),
                                          R(2, "18:11", 14), R(2, "18:21", 14)]),
                           {1: B(4, "13:05", "14:00"), 2: B(20, "15:05", "18:00")}, "CONTINUE"),
        # review 1, finding 1: a weekly reset (Fri 2026-10-30T12:00Z) between r0 and r1
        "reset_crossed_stage1": (dict(base, readings=[R(0, "10:30", 62, "2026-10-30"), R(1, "12:10", 0, "2026-10-30"),
                                                      R(1, "12:20", 0, "2026-10-30")]),
                                 {1: B(5, "10:35", "11:55", "2026-10-30")}, "RESET_CROSSED"),
        "reset_crossed_batch2": (dict(base, readings=[R(0, "06:00", 60, "2026-10-30"), R(1, "07:11", 61, "2026-10-30"),
                                                      R(1, "07:21", 61, "2026-10-30"), R(2, "12:11", 2, "2026-10-30"),
                                                      R(2, "12:21", 2, "2026-10-30")]),
                                 {1: B(5, "06:05", "07:00", "2026-10-30"), 2: B(20, "07:30", "12:00", "2026-10-30")},
                                 "RESET_CROSSED"),
        "missing_timestamps": ({"quiet_throughout": True, "weekly_reset_utc": "2026-10-23T12:00:00Z",
                                "readings": [{"kind": "gate", "after_batch": 0, "weekly_all_models_pct": 9, "five_hour_pct": 1},
                                             {"kind": "gate", "after_batch": 1, "weekly_all_models_pct": 9, "five_hour_pct": 1},
                                             {"kind": "gate", "after_batch": 1, "weekly_all_models_pct": 9, "five_hour_pct": 1}]},
                               {1: B(5, "13:05", "14:00")}, "INVALID_READINGS"),
        "missing_reset_time": ({"quiet_throughout": True,
                                "readings": [R(0, "13:00", 9), R(1, "14:11", 9), R(1, "14:21", 9)]},
                               {1: B(5, "13:05", "14:00")}, "INVALID_READINGS"),
        "missing_batch_end": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 9), R(1, "14:21", 9)]),
                              {1: {"n": 5, "start_utc": None, "end_utc": None, "waves": []}}, "INVALID_READINGS"),
        "non_int_reading": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 9.6), R(1, "14:21", 9.6)]),
                            {1: B(5, "13:05", "14:00")}, "INVALID_READINGS"),
        "bool_reading": (dict(base, readings=[R(0, "13:00", True), R(1, "14:11", 1), R(1, "14:21", 1)]),
                         {1: B(5, "13:05", "14:00")}, "INVALID_READINGS"),
        "decrease_in_window": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 8), R(1, "14:21", 8)]),
                               {1: B(5, "13:05", "14:00")}, "INVALID_READINGS"),
        "r0_after_start": (dict(base, readings=[R(0, "13:10", 9), R(1, "14:11", 9), R(1, "14:21", 9)]),
                           {1: B(5, "13:05", "14:00")}, "INVALID_READINGS"),
        "reading_after_next_batch": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 9), R(1, "14:40", 9)]),
                                     {1: B(5, "13:05", "14:00"), 2: B(20, "14:30", "17:00")}, "INVALID_READINGS"),
        "pins_unverified": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 12), R(1, "14:21", 12)]),
                            {1: B(5, "13:05", "14:00")}, "PINS_UNVERIFIED"),
        "audit_hold": (dict(base, readings=[R(0, "13:00", 9), R(1, "14:11", 12), R(1, "14:21", 12)]),
                       {1: B(5, "13:05", "14:00")}, "AUDIT_HOLD"),
    }
    out = {}
    for name, (rd, recs, want) in cases.items():
        pins = {"ok": name != "pins_unverified", "why": []}
        audit = {"hold": name == "audit_hold"}
        res = evaluate_gate(rd, w_star(), recs, cfgb, None, pins, audit)
        got = res["decision"]
        ok = got == want and (got not in ("RESET_CROSSED", "PINS_UNVERIFIED", "AUDIT_HOLD", "INVALID_READINGS")
                              or not res["steps"])
        out[name] = {"want": want, "got": got, "ok": ok}
    return out


def gate_selftest() -> dict:
    """Simulate the rule on whole-point readings (round and floor) for true w on a grid, as the
    record's 6.2 'Properties' paragraph states: no wrong decision; RUNNABLE needs N >= 12; cost."""
    import math
    ws = w_star()
    sizes = [hi for _, lo, hi in BATCHES]
    wrong = []
    max_cost = 0.0
    undetermined = []
    first_runnable_n = None
    for i in range(0, 1601):
        w = i / 1000.0
        wf = Fraction(i, 1000)
        for rnd in ("round", "floor"):
            for frac0 in (0.0, 0.25, 0.5, 0.75, 0.999):
                true0 = 37.0 + frac0
                f = (lambda x: math.floor(x + 0.5)) if rnd == "round" else math.floor
                r0 = f(true0)
                decision = None
                for n in sizes:
                    rk = f(true0 + w * n)
                    d = gate_decide(rk - r0, n, ws)
                    if d == "CONTINUE" and n == sizes[-1]:
                        d = "UNDETERMINED"
                    if d != "CONTINUE":
                        decision = (d, n)
                        break
                d, n = decision
                if (d == "RUNNABLE" and wf > ws) or (d == "NOT_RUNNABLE" and wf <= ws):
                    wrong.append((w, rnd, frac0, d, n))
                if d == "RUNNABLE":
                    first_runnable_n = n if first_runnable_n is None else min(first_runnable_n, n)
                if d == "UNDETERMINED":
                    undetermined.append(w)
                max_cost = max(max_cost, w * n)
    return {"w_star": str(ws), "w_star_float": float(ws), "wrong_decisions": len(wrong), "wrong_examples": wrong[:5],
            "smallest_N_with_RUNNABLE": first_runnable_n,
            "undetermined_w_range": [min(undetermined), max(undetermined)] if undetermined else None,
            "max_points_spent": round(max_cost, 3)}


# ----------------------------------------------------------------------------- status

def cmd_status(args) -> None:
    root = Path(args.root).resolve()
    cfg = read_json(root / "RUN.json")
    rows = []
    for a in cfg["attempts"] + (cfg.get("replacements") or []):
        li = log_integrity(root / "attempts" / a["id"])
        rows.append({"id": a["id"], "batch": a["batch"], "task": a["task"], "arm": a["arm"],
                     "calls": li["counted_calls"], "ended": bool(li["end_reason"]), "end_reason": li["end_reason"],
                     "integrity_ok": li["ok"]})
    want = int(args.batch) if args.batch else None
    rows = [r for r in rows if want is None or r["batch"] == want]
    rows = [r for r in rows if not r["id"].endswith("-r1") or r["calls"] or r["ended"]]
    print(json.dumps(rows, indent=1))


# ----------------------------------------------------------------------------- selftest helpers

def run_x1check(python: str, root: Path, aid: str, *argv) -> dict:
    p = subprocess.run([python, str(root / "harness" / "x1check.py"), str(root / "attempts" / aid), *argv],
                       capture_output=True, text=True, timeout=900)
    return json.loads(p.stdout)


def extract_card_snippets(card: str) -> str:
    a = card.index("SNIPPETS")
    b = card.index("READING", a)
    body = card[a:b].split("\n", 1)[1]
    return body


def quiet(fn, *a, **k):
    """Run a cmd_* function with its stdout discarded (the selftest reads the files it writes)."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def static_gate_unit_tests() -> dict:
    """Review 1, finding 3: renames, globs, nested groups, macros, raw identifiers and raw strings."""
    cases = {
        "use std as s; fn f(){ s::fs::write(\"a\",\"b\").unwrap(); }": True,
        "use std::{io::{self}, fs}; fn f(){ fs::write(\"a\",\"b\").unwrap(); }": True,
        "use std::*; fn f(){ fs::write(\"a\",\"b\").unwrap(); }": True,
        "use std::{*}; fn f(){}": True,
        "macro_rules! p { ($a:ident) => { std::$a::write(\"a\",\"b\").unwrap() } } fn f(){ p!(fs); }": True,
        "fn f(){ std::r#fs::write(\"a\",\"b\").unwrap(); }": True,
        "use std::{self as t}; fn f(){ t::fs::write(\"a\",\"b\").unwrap(); }": True,
        "use ::std as s;": True,
        "extern crate alloc; use alloc::vec::Vec;": True,
        "fn f(){ let s = r\"C:\\\"; std::fs::remove_file(\"x\"); }": True,
        "fn f(){ std /* c */ :: fs::remove_file(\"x\"); }": True,
        "fn f(){ let s = r#\"a\"b\"#; let t = 1; }": False,
        "fn f(){ let s = \"r\"; let t = 2; }": False,
        "use std::cmp::Ordering; use std::{cmp::{max, min}, collections::*};": False,
        "fn f(x: u8) -> u32 { x as u32 }": False,
        "impl X { fn g(self) -> u32 { self.0 as u32 } }": False,
    }
    rows = []
    for src, want in cases.items():
        got = bool(C.rust_static_gate(src))
        rows.append({"src": src[:70], "want_hit": want, "hit": got, "ok": got == want})
    return {"cases": rows, "ok": all(r["ok"] for r in rows)}


def audit_unit_tests() -> dict:
    """Review 1, finding 4: shell text after `abandon`, second lines, redirections."""
    att = {"solution_path": "C:/r/attempts/x-a01/work/solution.rs", "arm": "rust",
           "cmd": '"C:/py/python.exe" "C:/r/harness/x1check.py" "C:/r/attempts/x-a01"'}
    c = att["cmd"]
    cases = {
        c + " check": True, c + " check --tests": True, c + " submit": True, c + " abandon": True,
        c + " abandon 'cannot fix the tie rule (case 3)'": True, c + ' abandon "out of ideas, case 2 < 3"': True,
        c + " abandon cannot solve": True,
        c + ' abandon "$(cat C:/repo/tasks/D-Q4-1/ref/solution.rs)"': False,
        c + " abandon x; cat C:/repo/ref/solution.rs": False,
        c + " abandon x\ncat y": False,
        c + " check --tests\ncat y": False,
        c + " abandon `cat y`": False,
        c + " abandon x > out.txt": False,
        c + " abandon 'x' && cat y": False,
        "cat C:/repo/tasks/D-Q4-1/ref/solution.rs": False,
        "cd C:/r && " + c + " check": False,
    }
    rows = []
    for cmd, clean in cases.items():
        a = audit_tools(att, [{"id": "1", "name": "Bash", "command": cmd, "result": None}])
        rows.append({"command": cmd[-60:], "want_clean": clean, "clean": a["clean"], "ok": a["clean"] == clean})
    w = audit_tools(att, [{"id": "2", "name": "Write", "file_path": att["solution_path"],
                           "content": "use std as s; pub fn f() {}", "result": None}])
    rows.append({"command": "Write with a static-gate hit", "want_clean": False, "clean": w["clean"],
                 "ok": not w["clean"]})
    seq = audit_tools(att, [{"id": str(i), "name": "Bash", "command": c + " check",
                             "result": json.dumps({"call": k})} for i, k in enumerate([1, 2, 1, 2])])
    rows.append({"command": "transcript call numbers 1,2,1,2", "want_clean": False, "clean": seq["clean"],
                 "ok": not seq["clean"]})
    return {"cases": rows, "ok": all(r["ok"] for r in rows)}


class SynthClock:
    def __init__(self, start: str):
        self.t = parse_t(start)

    def tick(self, minutes=1.0) -> str:
        self.t += dt.timedelta(minutes=minutes)
        return self.t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def write_synth_agent(wf: Path, agent_id: str, label: str, agent_type: str, start: str, steps: list,
                      final_text: str, cwd: str, model=FULL_MODEL_ID, effort=PINNED_EFFORT,
                      tools=("Bash", "Write"), version="2.1.308", returned=True) -> str:
    """A transcript in the format Claude Code 2.1.308 writes for a workflow agent [M, this session's
    workflow transcripts, 2026-10-23]: attachment, api-request-shape (tools), api-request (model,
    effort), assistant records with usage and tool_use, user records with tool_result."""
    wf.mkdir(parents=True, exist_ok=True)
    clk = SynthClock(start)
    recs = [{"type": "attachment", "timestamp": clk.tick(0), "cwd": cwd,
             "attachment": {"type": "instructions", "files": []}},
            {"type": "api-request-shape", "timestamp": clk.tick(0),
             "shape": {"system": [{"type": "text", "text": "x1 subject"}], "tools": [{"name": n} for n in tools]}}]
    ctx = 20000
    for i, (name, inp, result) in enumerate(steps + [(None, None, None)]):
        ts = clk.tick(1)
        recs.append({"type": "api-request", "timestamp": ts,
                     "params": {"model": model, "output_config": {"effort": effort}}})
        usage = {"input_tokens": 3, "cache_creation_input_tokens": 20000 if i == 0 else 800,
                 "cache_read_input_tokens": 0 if i == 0 else ctx, "output_tokens": 400}
        ctx += 1200
        content = ([{"type": "tool_use", "id": f"tu{i}", "name": name, "input": inp}] if name else
                   [{"type": "text", "text": final_text}])
        recs.append({"type": "assistant", "timestamp": ts, "cwd": cwd, "effort": effort, "perTurnEffort": effort,
                     "version": version, "requestedModel": model,
                     "message": {"id": f"msg_{agent_id}_{i}", "model": model, "usage": usage, "content": content}})
        if name:
            recs.append({"type": "user", "timestamp": clk.tick(0.2), "cwd": cwd,
                         "message": {"content": [{"type": "tool_result", "tool_use_id": f"tu{i}",
                                                  "content": result}]}})
    (wf / f"agent-{agent_id}.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    write_json(wf / f"agent-{agent_id}.meta.json", {"agentType": agent_type, "description": label})
    with open(wf / "journal.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "started", "agentId": agent_id, "label": label}) + "\n")
        f.write(json.dumps({"type": "result", "agentId": agent_id, "result": final_text if returned else None}) + "\n")
    return clk.t.strftime("%Y-%m-%dT%H:%M:%SZ")


def steps_from_log(root: Path, att: dict) -> list:
    """Tool uses a subject would have made to produce this attempt's log."""
    adir = root / "attempts" / att["id"]
    entries, _ = C.read_log(adir / "harness" / "log.jsonl")
    ext = L.EXT[att["arm"]]
    steps = []
    sol = adir / "work" / f"solution.{ext}"
    if sol.exists():
        steps.append(("Write", {"file_path": att["solution_path"], "content": sol.read_text(encoding="utf-8")},
                      "File created"))
    for e in entries:
        if e.get("cmd") == "check" and e.get("phase") == "done":
            steps.append(("Bash", {"command": att["cmd"] + (" check --tests" if e.get("tests") else " check")},
                          json.dumps({"call": e["call"], "remaining": CHECK_BUDGET - e["call"]}, indent=1)))
        elif e.get("cmd") == "check" and e.get("refused"):
            steps.append(("Bash", {"command": att["cmd"] + " check"}, json.dumps({"error": e["refused"]})))
        elif e.get("ended") in ("submit", "abandon"):
            steps.append(("Bash", {"command": att["cmd"] + (" submit" if e["ended"] == "submit" else " abandon 'cannot solve'")},
                          json.dumps({"ok": True})))
    return steps


def gate_e2e(root: Path, work: Path, python: str) -> dict:
    """The gate end to end on a prepared run root whose attempts ran through the wrapper: synthetic
    transcripts, workflow results, readings, probe, tokens, two gate evaluations, and variants that
    must not give a rule outcome (review 1, findings 1, 2, 9 and 12)."""
    cfg = read_json(root / "RUN.json")
    plan = load_plan(root)
    rootstr = str(root)
    batch_start = {1: ["2026-10-24T13:00:00Z"], 2: ["2026-10-24T14:00:00Z", "2026-10-24T14:30:00Z",
                                                    "2026-10-24T15:00:00Z"]}
    # the probe attempt's one check (the probe agent would run it)
    run_x1check(python, root, cfg["probe"]["attempt_id"], "check")
    pcmd = all_probe_cmd(root, cfg)

    def reset_results():
        for p in (root / "results").glob("*"):
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        write_json(root / "dispositions.json", dispositions_skeleton(cfg["run_id"]))

    def build(variant: str):
        reset_results()
        wf_probe = work / f"wf_probe_{variant}"
        shutil.rmtree(wf_probe, ignore_errors=True)
        labels = cfg["probe"]["labels"]
        write_synth_agent(wf_probe, "p0", labels["main"], "x1-subject", "2026-10-24T12:30:00Z",
                          [("Bash", {"command": pcmd + " check"}, json.dumps({"call": 1, "remaining": 7}))],
                          "TOOLS-BEGIN\nBash\nWrite\nTOOLS-END\nCALL 1 REMAINING 7\nEND", rootstr)
        write_synth_agent(wf_probe, "p2", labels["turncap"], "x1-turncap-probe", "2026-10-24T12:40:00Z",
                          [("Bash", {"command": "echo turn-1"}, "turn-1"), ("Bash", {"command": "echo turn-2"}, "turn-2")],
                          "", rootstr, effort="low", tools=("Bash",))
        quiet(cmd_probe, argparse.Namespace(root=str(root), workflow_dir=[str(wf_probe)], allow_extra_tool=None,
                                            allow_cwd=None))
        wf = {b: work / f"wf_b{b}_{variant}" for b in (1, 2)}
        for d in wf.values():
            shutil.rmtree(d, ignore_errors=True)
        res = {}
        for b in (1, 2):
            atts = [a for a in plan["attempts"] if a["batch"] == b]
            waves = [atts[i:i + WAVE_SIZE] for i in range(0, len(atts), WAVE_SIZE)]
            for w, wave in enumerate(waves):
                for j, a in enumerate(wave):
                    steps = steps_from_log(root, a)
                    model = FULL_MODEL_ID
                    if variant == "wrong_model" and b == 2 and w == 0 and j == 0:
                        model = "claude-other-model"
                    if variant in ("flagged_read", "flagged_read_disposed") and b == 1 and j == 0:
                        steps.insert(0, ("Bash", {"command": "cat C:/repo/tasks/D-Q4-1/ref/solution.rs"}, "..."))
                    write_synth_agent(wf[b], f"{a['id']}x", a["id"], "x1-subject", batch_start[b][w], steps,
                                      f"END {a['id']}", rootstr, model=model)
                res[(b, w)] = {"schema": "x1-smoke-batch-result/2", "run_id": cfg["run_id"],
                               "plan_sha256": cfg["plan_sha256"], "batch": b, "wave": w, "replace": None,
                               "attempts": [{"attempt_id": a["id"], "task": a["task"], "arm": a["arm"],
                                             "returned": True} for a in wave]}
        return wf, res

    reset_r = "2026-10-23T12:00:00Z"

    def readings(variant, upto):
        rr = [{"kind": "gate", "after_batch": 0, "t_utc": "2026-10-24T12:55:00Z", "weekly_all_models_pct": 9,
               "five_hour_pct": 5}]
        rr += [{"kind": "gate", "after_batch": 1, "t_utc": f"2026-10-24T13:{m}:00Z", "weekly_all_models_pct": 9,
                "five_hour_pct": 6} for m in ("35", "45")]
        if upto >= 2:
            later = 0 if variant == "reset_crossed" else 9
            rr += [{"kind": "p2", "before": "batch 2 wave 1", "t_utc": "2026-10-24T14:25:00Z",
                    "weekly_all_models_pct": later, "five_hour_pct": 7},
                   {"kind": "p2", "before": "batch 2 wave 2", "t_utc": "2026-10-24T14:55:00Z",
                    "weekly_all_models_pct": later, "five_hour_pct": 8}]
            rr += [{"kind": "gate", "after_batch": 2, "t_utc": f"2026-10-24T15:{m}:00Z",
                    "weekly_all_models_pct": later, "five_hour_pct": 9} for m in ("40", "50")]
        reset = "2026-10-24T14:00:00Z" if variant == "reset_crossed" else reset_r
        return {"schema": "x1-smoke-readings/2", "run_id": cfg["run_id"], "quiet_throughout": True,
                "weekly_reset_utc": reset, "readings": rr, "batches": []}

    def gate_now():
        quiet(cmd_gate, argparse.Namespace(root=str(root), selftest=False))
        b = (root / "results" / "gate.json").read_bytes()
        return json.loads(b), hashlib.sha256(b).hexdigest()

    def scenario(variant):
        wf, res = build(variant)
        write_json(root / "readings.json", readings(variant, 1))
        write_json(root / "results" / "batch_1_wave_0.workflow.json", {**res[(1, 0)], "gate_sha256": None})
        quiet(cmd_tokens, argparse.Namespace(root=str(root), workflow_dir=[str(wf[1])]))
        g1, sha1 = gate_now()
        if variant in ("flagged_read", "flagged_read_disposed") and g1["decision"] == "AUDIT_HOLD":
            if variant == "flagged_read":
                return {"after_batch_1": g1["decision"], "final": g1["decision"]}
            first = plan["attempts"][0]["id"]
            write_json(root / "dispositions.json", {**dispositions_skeleton(cfg["run_id"]), "dispositions": [
                {"attempt_id": first, "disposition": "misuse", "exclude_from_N": True, "reviewer": "selftest",
                 "note": "synthetic read of a reference"}]})
            g1, sha1 = gate_now()
        auth = sha1 if variant != "unauthorised_batch" else "0" * 64
        for (b, w), d in res.items():
            if b == 2:
                write_json(root / "results" / f"batch_2_wave_{w}.workflow.json", {**d, "gate_sha256": auth})
        write_json(root / "readings.json", readings(variant, 2))
        quiet(cmd_tokens, argparse.Namespace(root=str(root), workflow_dir=[str(wf[1]), str(wf[2])]))
        g2, _ = gate_now()
        return {"after_batch_1": g1["decision"], "final": g2["decision"], "steps": g2.get("steps"),
                "problems": g2.get("problems") + g2.get("record_problems"), "pins": g2.get("pins", {}).get("why"),
                "caveats": g2.get("caveats")}

    want = {"clean": ("CONTINUE", "RUNNABLE"), "unauthorised_batch": ("CONTINUE", "INCONSISTENT_RECORDS"),
            "wrong_model": ("CONTINUE", "PINS_UNVERIFIED"), "flagged_read": ("AUDIT_HOLD", "AUDIT_HOLD"),
            "flagged_read_disposed": ("CONTINUE", "RUNNABLE"), "reset_crossed": ("CONTINUE", "RESET_CROSSED")}
    out = {}
    for v, (w1, w2) in want.items():
        r = scenario(v)
        r["ok"] = r["after_batch_1"] == w1 and r["final"] == w2
        if v == "flagged_read_disposed" and r["ok"]:
            r["ok"] = bool(r["steps"]) and r["steps"][-1]["N"] == len(plan["attempts"]) - 1
        out[v] = r
    probe = read_json(root / "results" / "probe.json")
    out["probe_ok"] = probe["ok"]
    out["probe_turncap_honoured"] = probe["turncap"]["honoured"]
    reset_results()
    return out


def mini_root_tests(work: Path, tc: dict) -> dict:
    """Wrapper behaviours on a 2-attempt run root: a refunded wrapper failure, a state.json reset,
    a broken log chain, the wall budget, prelude tampering and abandon-reason sanitising."""
    root = work / "mini"
    quiet(cmd_prepare, argparse.Namespace(root=str(root), run_id="m", seed=11, n_max=2, mithi=tc["mithi"],
                                          rustc=tc["rustc"], python=DEFAULT_PYTHON, model="opus", effort="max",
                                allow_std_mismatch=True))
    cfg = read_json(root / "RUN.json")
    a1, a2 = cfg["attempts"][0], cfg["attempts"][1]
    res = {}
    # a2: refund, state reset, prelude tamper, then a broken chain
    ad = root / "attempts" / a2["id"]
    ext = L.EXT[a2["arm"]]
    shutil.copy2(L.TASKS_DIR / a2["task"] / "ref" / f"solution.{ext}", ad / "work" / f"solution.{ext}")
    vis = ad / "harness" / "visible.json"
    vis.rename(ad / "harness" / "visible.json.off")
    o1 = run_x1check(DEFAULT_PYTHON, root, a2["id"], "check")
    (ad / "harness" / "visible.json.off").rename(vis)
    (ad / "work" / f"prelude.{ext}").write_text("this is not a prelude\n", encoding="utf-8")
    o2 = run_x1check(DEFAULT_PYTHON, root, a2["id"], "check", "--tests")
    st = read_json(ad / "harness" / "state.json")
    st["calls"] = 0
    write_json(ad / "harness" / "state.json", st)
    o3 = run_x1check(DEFAULT_PYTHON, root, a2["id"], "check")
    entries, _ = C.read_log(ad / "harness" / "log.jsonl")
    done2 = [e for e in entries if e.get("phase") == "done" and e.get("call") == 1]
    res["refund"] = {"first_reply_refunded": o1.get("refunded") is True, "next_call": o2.get("call"),
                     "ok": o1.get("refunded") is True and o2.get("call") == 1}
    res["prelude_tamper"] = {"tests_passed": (o2.get("tests") or {}).get("passed"),
                             "logged": bool(done2 and done2[0].get("prelude_work_copy_modified")),
                             "ok": (o2.get("tests") or {}).get("failed") == 0 and bool(done2 and
                                                                                       done2[0].get("prelude_work_copy_modified"))}
    res["state_reset"] = {"call_after_reset": o3.get("call"), "ok": o3.get("call") == 2}
    lp = ad / "harness" / "log.jsonl"
    lines = lp.read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace('"seq":', '"seq": ', 1)
    lp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    o4 = run_x1check(DEFAULT_PYTHON, root, a2["id"], "check")
    li = log_integrity(ad)
    res["log_tamper"] = {"reply": o4.get("error"), "integrity_ok": li["ok"],
                         "ok": o4.get("error") == "log_integrity_failure" and not li["ok"]}
    # a1: abandon reason sanitising on a fresh attempt is checked on a copy; then the wall budget
    cfg["wall_budget_s"] = 2
    write_json(root / "RUN.json", cfg)
    ad1 = root / "attempts" / a1["id"]
    ext1 = L.EXT[a1["arm"]]
    shutil.copy2(L.TASKS_DIR / a1["task"] / "ref" / f"solution.{ext1}", ad1 / "work" / f"solution.{ext1}")
    w1 = run_x1check(DEFAULT_PYTHON, root, a1["id"], "check")
    import time as _time
    _time.sleep(3)
    w2 = run_x1check(DEFAULT_PYTHON, root, a1["id"], "submit")
    w3 = run_x1check(DEFAULT_PYTHON, root, a1["id"], "check")
    li1 = log_integrity(ad1)
    res["wall_budget"] = {"first": "call" in w1, "submit_reply": w2.get("error"), "after": w3.get("error"),
                          "end_reason": li1["end_reason"],
                          "ok": "call" in w1 and w2.get("error") == "wall_budget_exhausted"
                          and w3.get("error") == "attempt_ended" and li1["end_reason"] == "budget_wall"}
    # abandon sanitising: a third attempt directory is not needed; use the replacement of a1
    cfg["wall_budget_s"] = WALL_BUDGET_S
    write_json(root / "RUN.json", cfg)
    rid = a1["id"] + "-r1"
    run_x1check(DEFAULT_PYTHON, root, rid, "abandon", "$(cat", "x)", "`id`;", "rm", "-rf", "y")
    ent, _ = C.read_log(root / "attempts" / rid / "harness" / "log.jsonl")
    reason = [e.get("reason") for e in ent if e.get("ended") == "abandon"]
    res["abandon_reason"] = {"stored": reason, "ok": bool(reason) and not re.search(r"[$`;'\"]", reason[0] or "")}
    quiet(cmd_score, argparse.Namespace(root=str(root), attempts=None, include_not_started=False))
    sc = read_json(root / "results" / "score.json")
    by = {r["attempt_id"]: r for r in sc["attempts"]}
    res["score"] = {"a1_end_reason": by[a1["id"]]["end_reason"], "a1_vp": by[a1["id"]]["vp"],
                    "a2_integrity_flag": by[a2["id"]]["integrity_flag"], "integrity_flags": sc["integrity_flags"],
                    "ok": by[a1["id"]]["end_reason"] == "budget_wall" and not by[a1["id"]]["vp"]
                    and by[a2["id"]]["integrity_flag"] and a2["id"] in sc["integrity_flags"]}
    res["ok"] = all(v["ok"] for v in res.values() if isinstance(v, dict))
    return res


def cmd_selftest(args) -> None:
    tc = toolchain(args)
    report = {"schema": "x1-smoke-selftest/2", "kit": KIT_VERSION, "run_utc": now_utc(), "repo_head": git_head(),
              "repo_dirty_paths": git_dirty_paths(), "toolchain": tc, "label": "development items only"}
    tcfg = {"mithi": tc["mithi"], "rustc": tc["rustc"], "rust_env": {}, "check_timeout_s": 60,
            "case_timeout_s": 10, "oracle_timeout_s": 900}
    work = Path(tempfile.mkdtemp(prefix="x1selftest_")).resolve()
    failures = []
    if not tc["std_matches_repo"]:
        failures.append("mithi binary's std differs from the repository's std.mith + canonical.mith (rebuild mithi)")
    try:
        # 1. cards
        cards = card_texts()
        t0 = cards["tier0"].encode("utf-8")
        report["cards"] = {"tier0_bytes": len(t0), "tier0_ascii": all(c < 128 for c in t0),
                           "tier0_within_8192": len(t0) <= 8192,
                           "bytes": {k: len(v.encode("utf-8")) for k, v in cards.items()},
                           "sha256": {k: sha256_text(v) for k, v in cards.items()}}
        if not (report["cards"]["tier0_ascii"] and report["cards"]["tier0_within_8192"]):
            failures.append("tier0 card size/ASCII")
        snip = extract_card_snippets(cards["tier0"])
        sp = work / "card_snippets.mith"
        sp.write_text(snip, encoding="utf-8")
        r = subprocess.run([tc["mithi"], "check", "--subset", "agent", str(sp)], capture_output=True, text=True, timeout=120)
        report["cards"]["mithril_snippets_mithi_check"] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[:300]
        if r.returncode != 0:
            failures.append("Mithril card snippets rejected by mithi")
        rs = extract_card_snippets(cards["rust"])
        rdir = work / "rust_snip"
        rdir.mkdir()
        (rdir / "main.rs").write_text("#![allow(dead_code)]\nfn canon_nan(x: f32) -> f32 { if x.is_nan() { f32::from_bits(0x7fc0_0000) } else { x } }\n"
                                       + rs + "\nfn main() {}\n", encoding="utf-8")
        r = subprocess.run([tc["rustc"], "--edition", "2021", "-F", "unsafe_code", "-C", "overflow-checks=on",
                            "-o", str(rdir / "s.exe"), "main.rs"], cwd=str(rdir), capture_output=True, text=True, timeout=300)
        report["cards"]["rust_snippets_compile"] = "ok" if r.returncode == 0 else r.stderr[:600]
        if r.returncode != 0:
            failures.append("Rust card snippets do not compile")
        agent_md = AGENT_FILE.read_text(encoding="utf-8")
        body = agent_md.split("---", 2)[2]
        report["agent_file"] = {"sha256": sha256_file(AGENT_FILE),
                                "frontmatter_tools": re.search(r"^tools:\s*(.*)$", agent_md, re.M).group(1).strip(),
                                "arm_neutral": not re.search(r"\b(mithril|rust|mithi|rustc|cargo|kernel)\b", body, re.I),
                                "abandon_quoting": "abandon '" in body}
        if not report["agent_file"]["arm_neutral"]:
            failures.append("agent system prompt names an arm")
        if report["agent_file"]["frontmatter_tools"] != "Write, Bash":
            failures.append("agent frontmatter tools are not exactly Write, Bash")

        # 2. helper parity (Rust helper pack against the Python model; the Mithril side is mithi's
        #    std, exercised by every reference solution below)
        hdir = work / "helpers"
        hdir.mkdir()
        prel = L.read_text(L.task_file("D-NORM-1", "rust/prelude.rs")).replace("#![allow(dead_code)]", "")
        f16src = L.read_text(L.task_file("D-Q4-1", "rust/prelude.rs"))
        f16fn = f16src[f16src.index("/// Exact binary16"):f16src.index("/// The canonical quiet NaN")]
        (hdir / "main.rs").write_text(
            "#![allow(dead_code)]\n" + prel + "\n" + f16fn + r"""
fn main() {
    let mut out = String::new();
    for h in 0..=0xffffu32 {
        let v = f16_to_f32(h as u16);
        if v.is_nan() { out.push_str("n\n"); } else { out.push_str(&format!("{:08x}\n", v.to_bits())); }
    }
    let mut s: u32 = 12345;
    for n in 0..200usize {
        let mut a: Vec<f32> = Vec::new();
        let mut b: Vec<f32> = Vec::new();
        for _i in 0..n {
            s = s.wrapping_mul(1664525).wrapping_add(1013904223);
            a.push(((s >> 8) as i32 - 8388608) as f32 * 0.001);
            s = s.wrapping_mul(1664525).wrapping_add(1013904223);
            b.push(((s >> 8) as i32 - 8388608) as f32 * 0.0003);
        }
        out.push_str(&format!("{:08x} {:08x}\n", sum16(&a).to_bits(), dot16(&a, &b).to_bits()));
    }
    print!("{}", out);
}
""", encoding="utf-8")
        r = subprocess.run([tc["rustc"], "--edition", "2021", "-O", "-o", str(hdir / "h.exe"), "main.rs"], cwd=str(hdir),
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            failures.append("helper parity program does not compile")
            report["helpers"] = {"error": r.stderr[:600]}
        else:
            got = subprocess.run([str(hdir / "h.exe")], capture_output=True, text=True, timeout=300).stdout.split("\n")
            bad16 = 0
            for h in range(0x10000):
                v = L.f16_to_f32(h)
                exp = "n" if v != v else "%08x" % L.bits(v)
                if got[h] != exp:
                    bad16 += 1
            norm = L.load_task("D-NORM-1")
            badsum = 0
            s = 12345
            for n in range(200):
                a, b = [], []
                for _ in range(n):
                    s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
                    a.append(L.mul(L.f32(float((s >> 8) - 8388608)), L.f32(0.001)))
                    s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
                    b.append(L.mul(L.f32(float((s >> 8) - 8388608)), L.f32(0.0003)))
                exp = "%08x %08x" % (L.bits(norm.sum16(a)), L.bits(norm.sum16([L.mul(x, y) for x, y in zip(a, b)])))
                if got[0x10000 + n] != exp:
                    badsum += 1
            report["helpers"] = {"f16_to_f32_all_65536_mismatches": bad16, "sum16_dot16_200_vectors_mismatches": badsum}
            if bad16 or badsum:
                failures.append("helper parity")

        # 3. tasks: stubs fail, references and correct alternatives pass, mutants fail the oracle
        rows = []
        for tid in L.TASK_IDS:
            for arm in L.ARMS:
                ext = L.EXT[arm]
                td = L.TASKS_DIR / tid
                items = [("stub", td / arm / f"stub.{ext}", "fail")]
                items += [(p.stem, p, "pass") for p in sorted((td / "ref").glob(f"*.{ext}"))]
                items += [("mutant:" + p.stem, p, "oracle_fail") for p in sorted((td / "mutants").glob(f"*.{ext}"))]
                for name, p, want in items:
                    src = p.read_text(encoding="utf-8")
                    w = work / tid / arm / name.replace(":", "_")
                    w.mkdir(parents=True, exist_ok=True)
                    acc = scoring.acceptance(tid, arm, src, tcfg, w)
                    orc = scoring.oracle(tid, arm, src, tcfg, w)
                    if want == "pass":
                        ok = acc["verdict"] == "pass" and orc["verdict"] == "pass"
                    elif want == "fail":
                        ok = acc["verdict"] == "fail" and orc["verdict"] == "fail"
                    else:
                        ok = orc["verdict"] == "fail"
                    row = {"task": tid, "arm": arm, "item": name, "expect": want, "ok": ok,
                           "acceptance": acc["verdict"], "checker": acc["checker"], "primary": acc.get("primary"),
                           "holes": acc["holes"], "visible": f"{acc['visible_passed']}/{acc['visible_total']}",
                           "oracle": orc["verdict"], "oracle_cases": orc["n_cases"],
                           "oracle_mismatches": orc.get("n_mismatch"), "oracle_failed": orc.get("failed"),
                           "oracle_run_wall_s": orc.get("run_wall_s")}
                    rows.append(row)
                    print(f"{tid:10s} {arm:8s} {name:24s} expect={want:11s} acc={acc['verdict']:4s} oracle={orc['verdict']:4s} {'OK' if ok else 'FAIL'}", flush=True)
                    if not ok:
                        failures.append(f"{tid}/{arm}/{name}")
        report["tasks"] = rows

        # 4. unit tests of the static gate and the tool audit (review 1, findings 3 and 4)
        report["static_gate_units"] = static_gate_unit_tests()
        if not report["static_gate_units"]["ok"]:
            failures.append("static gate unit cases")
        report["audit_units"] = audit_unit_tests()
        if not report["audit_units"]["ok"]:
            failures.append("audit unit cases")

        # 5. path length (review 1, finding 8): prepare refuses one character over the limit, and the
        #    end-to-end run below uses a root exactly at the limit
        base_len = check_path_lengths(work / "e2e_", "selftest", 16)["longest"]
        pad = PATH_MAX - base_len
        e2e_root = work / ("e2e_" + "p" * pad)
        too_long = work / ("e2f_" + "p" * (pad + 1))
        try:
            quiet(cmd_prepare, argparse.Namespace(root=str(too_long), run_id="selftest", seed=7, n_max=16,
                                                  mithi=tc["mithi"], rustc=tc["rustc"], python=DEFAULT_PYTHON,
                                                  model="opus", effort="max", allow_std_mismatch=True))
            refused = False
        except SystemExit:
            refused = True
        report["path_length"] = {"limit": PATH_MAX, "e2e_root_longest_path": check_path_lengths(e2e_root, "selftest", 16)["longest"],
                                 "refused_one_over": refused}
        if not refused or report["path_length"]["e2e_root_longest_path"] != PATH_MAX:
            failures.append("path-length check")

        # 6. end to end through the wrapper on a prepared run (no agent: files are copied in)
        ns = argparse.Namespace(root=str(e2e_root), run_id="selftest", seed=7, n_max=16, mithi=tc["mithi"],
                                rustc=tc["rustc"], python=DEFAULT_PYTHON, model="opus", effort="max",
                                allow_std_mismatch=True)
        quiet(cmd_prepare, ns)
        cfg = read_json(e2e_root / "RUN.json")
        report["prepared"] = {"agent_copy_matches": cfg["agent_file_sha256"] == cfg["agent_file_copy_sha256"],
                              "replacement_dirs": len(cfg["replacements"]), "probe_attempt": cfg["probe"]["attempt_id"],
                              "batches": cfg["batches"]}
        if not report["prepared"]["agent_copy_matches"] or len(cfg["replacements"]) != 16:
            failures.append("prepare: agent copy or replacement directories")
        expect = {}
        mutant_done = set()
        for i, a in enumerate(cfg["attempts"]):
            aid, tid, arm = a["id"], a["task"], a["arm"]
            ext = L.EXT[arm]
            sol = e2e_root / "attempts" / aid / "work" / f"solution.{ext}"
            td = L.TASKS_DIR / tid
            muts = sorted((td / "mutants").glob(f"*.{ext}"))
            if i == 0:
                # budget test: 8 checks, the 9th refused, then submit the reference; state.json is
                # reset to 0 calls after the 3rd call and the count still comes from the log
                shutil.copy2(td / "ref" / f"solution.{ext}", sol)
                outs = []
                for k in range(9):
                    outs.append(run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check"))
                    if k == 2:
                        stp = e2e_root / "attempts" / aid / "harness" / "state.json"
                        st = read_json(stp)
                        st["calls"] = 0
                        write_json(stp, st)
                report["e2e_budget"] = {"calls_ok": sum(1 for o in outs if "call" in o),
                                        "call_numbers": [o.get("call") for o in outs if "call" in o],
                                        "ninth": outs[-1].get("error")}
                if report["e2e_budget"]["calls_ok"] != 8 or report["e2e_budget"]["ninth"] != "budget_exhausted" \
                        or report["e2e_budget"]["call_numbers"] != list(range(1, 9)):
                    failures.append("e2e budget enforcement")
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "submit")
                expect[aid] = {"end_reason": "submit", "vp": True, "accepted": True}
            elif i == 1:
                # stub first (holes), then the reference with tests, then submit
                o1 = run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check")
                shutil.copy2(td / "ref" / f"solution.{ext}", sol)
                o2 = run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check", "--tests")
                report["e2e_first_two_calls"] = {"stub_call": {k: o1.get(k) for k in ("holes", "file")},
                                                 "ref_call_tests": o2.get("tests", {}).get("passed")}
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "submit")
                o3 = run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check")
                report["e2e_after_submit"] = o3.get("error")
                if o3.get("error") != "attempt_ended":
                    failures.append("e2e: check after submit not refused")
                expect[aid] = {"end_reason": "submit", "vp": True, "accepted": True}
            elif i == 2:
                shutil.copy2(td / "ref" / f"solution.{ext}", sol)
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check", "--tests")
                expect[aid] = {"end_reason": "no_submit", "vp": False, "accepted": False, "unsubmitted_oracle_pass": True}
            elif i == 3:
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "abandon", "cannot", "solve")
                expect[aid] = {"end_reason": "abandon", "vp": False, "accepted": False}
            elif i == 4:
                expect[aid] = {"end_reason": "not_started"}
            elif i == 5 and arm == "rust":
                # a solution that never returns: the visible run stops at the first case timeout, so
                # one call stays well inside a 2-minute Bash command timeout; then the reference
                ref = (td / "ref" / "solution.rs").read_text(encoding="utf-8")
                k = ref.index("{", ref.index("pub fn"))
                sol.write_text(ref[:k + 1] + "\n    loop {}\n" + ref[k + 1:], encoding="utf-8")
                t_start = dt.datetime.now()
                o = run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check", "--tests")
                secs = (dt.datetime.now() - t_start).total_seconds()
                cases = (o.get("tests") or {}).get("cases") or []
                report["e2e_hang"] = {"wall_s": round(secs, 1),
                                      "first_case_error": (cases[0].get("error") or "")[:40] if cases else None,
                                      "later_cases": sorted({(c.get("error") or "")[:40] for c in cases[1:]})}
                if not (cases and str(cases[0].get("error", "")).startswith("timeout") and secs < 100):
                    failures.append("e2e: hanging solution not bounded")
                shutil.copy2(td / "ref" / "solution.rs", sol)
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check", "--tests")
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "submit")
                expect[aid] = {"end_reason": "submit", "vp": True, "accepted": True}
            elif muts and (tid, arm) not in mutant_done and i % 2 == 1:
                # a wrong-but-plausible submission: accepted or not by visible tests, never a VP
                mutant_done.add((tid, arm))
                shutil.copy2(muts[0], sol)
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check", "--tests")
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "submit")
                expect[aid] = {"end_reason": "submit", "vp": False}
            else:
                shutil.copy2(td / "ref" / f"solution.{ext}", sol)
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "check", "--tests")
                run_x1check(DEFAULT_PYTHON, e2e_root, aid, "submit")
                expect[aid] = {"end_reason": "submit", "vp": True, "accepted": True}
        quiet(cmd_score, argparse.Namespace(root=str(e2e_root), attempts=None, include_not_started=True))
        sc = read_json(e2e_root / "results" / "score.json")
        e2e = []
        for rec in sc["attempts"]:
            want = expect.get(rec["attempt_id"], {})
            ok = all(rec.get(k) == v for k, v in want.items()) and rec["integrity"]["log_chain_ok"] \
                and not rec["integrity_flag"]
            e2e.append({"attempt": rec["attempt_id"], "task": rec["task_id"], "arm": rec["arm"],
                        "end_reason": rec["end_reason"], "vp": rec["vp"], "accepted": rec["accepted"],
                        "accepted_and_wrong": rec["accepted_and_wrong"], "log_chain_ok": rec["integrity"]["log_chain_ok"],
                        "integrity_flag": rec["integrity_flag"], "expected": want, "ok": ok})
            if not ok:
                failures.append(f"e2e {rec['attempt_id']}")
        report["e2e"] = {"root_path_chars": len(str(e2e_root)), "attempts": e2e,
                         "aggregate_by_arm": sc["aggregate"]["by_arm"]}
        status_rows = json.loads(_capture(cmd_status, argparse.Namespace(root=str(e2e_root), batch=None)))
        report["e2e_status_rows"] = len(status_rows)

        # 7. the gate end to end, with synthetic transcripts in Claude Code's transcript format
        report["gate_e2e"] = gate_e2e(e2e_root, work, DEFAULT_PYTHON)
        for name, r in report["gate_e2e"].items():
            if isinstance(r, dict) and not r.get("ok"):
                failures.append(f"gate e2e {name}")
        if not report["gate_e2e"].get("probe_ok"):
            failures.append("gate e2e: synthetic probe not ok")

        # tamper check: editing a log line breaks the chain
        lp = e2e_root / "attempts" / cfg["attempts"][0]["id"] / "harness" / "log.jsonl"
        lines = lp.read_text(encoding="utf-8").splitlines()
        lines[2] = lines[2].replace('"call":2', '"call":1')
        lp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report["e2e_tamper_detected"] = not C.read_log(lp)[1]["ok"]
        if not report["e2e_tamper_detected"]:
            failures.append("log tamper not detected")
        wf = (e2e_root / "smoke_workflow.js").read_text(encoding="utf-8")
        pw = (e2e_root / "probe_workflow.js").read_text(encoding="utf-8")
        report["workflow_instance"] = {"bytes": len(wf.encode("utf-8")), "sha256": sha256_text(wf),
                                       "plan_parses": bool(re.search(r"^const PLAN = \{.*\};$", wf, re.M)),
                                       "probe_parses": bool(re.search(r"^const PROBE = \{.*\};$", pw, re.M))}
        if not (report["workflow_instance"]["plan_parses"] and report["workflow_instance"]["probe_parses"]):
            failures.append("workflow instances")

        # 8. wrapper behaviours on a small root (refund, state reset, log tamper, wall budget, prelude,
        #    abandon reason)
        report["wrapper_units"] = mini_root_tests(work, tc)
        if not report["wrapper_units"]["ok"]:
            failures.append("wrapper unit behaviours")

        # 9. the gate rule
        report["gate"] = gate_selftest()
        if report["gate"]["wrong_decisions"]:
            failures.append("gate rule made a wrong decision in simulation")
        report["gate_fixtures"] = gate_fixture_tests()
        for name, r in report["gate_fixtures"].items():
            if not r["ok"]:
                failures.append(f"gate fixture {name}")
    finally:
        if args.keep:
            report["work_dir"] = str(work)
        else:
            shutil.rmtree(work, ignore_errors=True)
    report["failures"] = failures
    report["ok"] = not failures
    out = Path(args.out) if args.out else None
    if out:
        # no user names or temp paths in a report that may be committed
        text = json.dumps(report, indent=1, sort_keys=True)
        text = re.sub(r"C:(\\\\|/)+Users(\\\\|/)+(Pierce Lonergan|PIERCE~1)", "~", text)
        text = re.sub(r"~(\\\\|/)+AppData(\\\\|/)+Local(\\\\|/)+Temp[^\"]*?(\\\\|/)+scratchpad", "<scratchpad>", text)
        text = re.sub(r"~(\\\\|/)+AppData(\\\\|/)+Local(\\\\|/)+Temp(\\\\|/)+x1selftest_[A-Za-z0-9_]+", "<work>", text)
        text = text.replace("Pierce-Lonergan", "<user>")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "failures": failures, "cards": report.get("cards"),
                      "helpers": report.get("helpers"), "e2e_budget": report.get("e2e_budget"),
                      "e2e_hang": report.get("e2e_hang"), "e2e_tamper_detected": report.get("e2e_tamper_detected"),
                      "path_length": report.get("path_length"), "wrapper_units": report.get("wrapper_units"),
                      "gate_e2e": {k: (v if not isinstance(v, dict) else {kk: v.get(kk) for kk in ("after_batch_1", "final", "ok")})
                                   for k, v in (report.get("gate_e2e") or {}).items()},
                      "static_gate_units_ok": (report.get("static_gate_units") or {}).get("ok"),
                      "audit_units_ok": (report.get("audit_units") or {}).get("ok"),
                      "workflow_instance": report.get("workflow_instance"), "gate": report.get("gate")}, indent=1))
    if failures:
        sys.exit(1)


def _capture(fn, *a) -> str:
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*a)
    return buf.getvalue()


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--root", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--seed", type=int, default=20261023)
    p.add_argument("--n-max", type=int, default=65)
    p.add_argument("--mithi", required=True)
    p.add_argument("--rustc")
    p.add_argument("--python")
    p.add_argument("--model", default="opus")
    p.add_argument("--effort", default="max")
    p.add_argument("--allow-std-mismatch", action="store_true",
                   help="prepare even if mithi's embedded std is not the repository's (a deviation to log)")
    p.set_defaults(fn=cmd_prepare)
    p = sub.add_parser("probe")
    p.add_argument("--root", required=True)
    p.add_argument("--workflow-dir", action="append", required=True)
    p.add_argument("--allow-extra-tool", action="append",
                   help="a tool name besides Write and Bash to accept (a deviation the lead engineer logs)")
    p.add_argument("--allow-cwd", action="append",
                   help="a working directory besides the run root to accept (a deviation the lead engineer logs)")
    p.set_defaults(fn=cmd_probe)
    p = sub.add_parser("score")
    p.add_argument("--root", required=True)
    p.add_argument("--attempts")
    p.add_argument("--include-not-started", action="store_true")
    p.set_defaults(fn=cmd_score)
    p = sub.add_parser("tokens")
    p.add_argument("--root", required=True)
    p.add_argument("--workflow-dir", action="append", required=True)
    p.set_defaults(fn=cmd_tokens)
    p = sub.add_parser("gate")
    p.add_argument("--root")
    p.add_argument("--selftest", action="store_true")
    p.set_defaults(fn=cmd_gate)
    p = sub.add_parser("p2")
    p.add_argument("--root", required=True)
    p.set_defaults(fn=cmd_p2)
    p = sub.add_parser("status")
    p.add_argument("--root", required=True)
    p.add_argument("--batch")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("selftest")
    p.add_argument("--mithi", required=True)
    p.add_argument("--rustc")
    p.add_argument("--out")
    p.add_argument("--keep", action="store_true")
    p.set_defaults(fn=cmd_selftest)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
