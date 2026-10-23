"""Acceptance check and hidden oracle for the X1 smoke kit (development items only).

The acceptance check is the arm's own check as the subject saw it (the same `build` and visible-case
runner as harness/x1check.py, with a fresh nonce), plus zero remaining holes. The oracle builds the
final artifact with the hidden driver (visible cases first, then literal edge cases, then the
task's seeded random cases), runs every case in one process, and compares the printed results with
the Python model's outputs outside that process. A run whose result record lacks the nonce line, has
fewer lines than cases, or ends in a trap, panic or timeout fails.

Isolation limit: development items only. The hidden expectations are computed here from the task's
Python model, which lives in the public repository; nothing here is sealed.
"""

from __future__ import annotations

import importlib.util
import os
import secrets
import shutil
from pathlib import Path

import smokelib as L

_spec = importlib.util.spec_from_file_location("x1check", L.HARNESS_DIR / "x1check.py")
x1check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1check)


def prelude_text(task_id: str, arm: str) -> str:
    return L.read_text(L.task_file(task_id, f"{arm}/prelude.{L.EXT[arm]}"))


def stub_text(task_id: str, arm: str) -> str:
    return L.read_text(L.task_file(task_id, f"{arm}/stub.{L.EXT[arm]}"))


def visible_bundle(task_id: str, arm: str) -> dict:
    """What an attempt's harness needs for visible tests: driver source and expected outputs."""
    task = L.load_task(task_id)
    cases = task.visible_cases()
    drv = L.rust_driver(task, cases, "visible") if arm == "rust" else L.mith_driver(task, cases, "visible")
    return {
        "task_id": task_id,
        "arm": arm,
        "driver": drv,
        "expected": [task.model(c) for c in cases],
        "describe": [task.describe(c) for c in cases],
    }


def acceptance(task_id: str, arm: str, src: str, cfg: dict, work: Path) -> dict:
    vis = visible_bundle(task_id, arm)
    nonce = secrets.token_hex(8)
    drv = vis["driver"].replace(L.NONCE_PLACEHOLDER, nonce)
    bdir = work / "acc"
    chk = x1check.build(arm, cfg, bdir, src, prelude_text(task_id, arm), drv,
                        timeout=int(cfg.get("check_timeout_s", 60)))
    gate = x1check.rust_static_gate(src) if arm == "rust" else []
    holes = x1check.count_holes(src)
    res = {"checker": chk["verdict"], "primary": chk.get("primary"), "static_gate": "fail" if gate else "pass",
           "holes": holes, "visible_passed": 0, "visible_total": len(vis["expected"])}
    ok = chk["verdict"] == "accept" and not gate and holes == 0
    if chk["verdict"] == "accept" and not gate:
        npass = 0
        for k, exp in enumerate(vis["expected"]):
            r = x1check.run_visible_case(arm, cfg, bdir, k, nonce, timeout=int(cfg.get("case_timeout_s", 10)))
            if r["error"] is None and r["got"] == exp:
                npass += 1
        res["visible_passed"] = npass
        ok = ok and npass == len(vis["expected"])
    else:
        ok = False
    res["verdict"] = "pass" if ok else "fail"
    shutil.rmtree(bdir, ignore_errors=True)
    return res


def oracle(task_id: str, arm: str, src: str, cfg: dict, work: Path) -> dict:
    task = L.load_task(task_id)
    cases = L.hidden_cases(task)
    expected = L.expected_hidden(task)
    nonce = secrets.token_hex(8)
    if arm == "rust":
        drv = L.rust_driver(task, cases, "hidden")
    else:
        drv = L.mith_driver(task, cases, "hidden")
    drv = drv.replace(L.NONCE_PLACEHOLDER, nonce)
    bdir = work / "orc"
    chk = x1check.build(arm, cfg, bdir, src, prelude_text(task_id, arm), drv,
                        timeout=int(cfg.get("check_timeout_s", 60)))
    res = {"n_cases": len(expected), "build": chk["verdict"]}
    if chk["verdict"] != "accept":
        res.update({"verdict": "fail", "failed": ["build"], "detail": str(chk.get("primary") or "")[:200]})
        shutil.rmtree(bdir, ignore_errors=True)
        return res
    gate = x1check.rust_static_gate(src) if arm == "rust" else []
    if gate:
        res.update({"verdict": "fail", "failed": ["static_gate"]})
        shutil.rmtree(bdir, ignore_errors=True)
        return res
    tmo = int(cfg.get("oracle_timeout_s", 900))
    if arm == "rust":
        exe = bdir / ("x1drv.exe" if os.name == "nt" else "x1drv")
        r = x1check.run_proc([str(exe), "all"], bdir, tmo)
        lines = r["stdout"].replace("\r\n", "\n").split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        ok_run = (not r["timeout"]) and r["rc"] == 0
        err = None if ok_run else ("timeout" if r["timeout"] else x1check.truncate(r["stderr"].strip(), 300))
    else:
        r = x1check.run_proc([cfg["mithi"], "run", "--subset", "agent", "--prelude", "prelude.mith", "--entry",
                              "x1h_all", "solution.mith", "x1_driver.mith"], bdir, tmo)
        body = x1check.parse_mithi_run(r["stdout"]) if (not r["timeout"] and r["rc"] == 0) else None
        lines = body.split("|") if body is not None else []
        ok_run = body is not None
        err = None if ok_run else ("timeout" if r["timeout"] else x1check.truncate((r["stdout"] + r["stderr"]).strip(), 300))
    res["run_wall_s"] = r["wall_s"]
    failed = []
    if not ok_run:
        failed.append("run")
    if not lines or lines[-1] != "N:" + nonce:
        failed.append("completeness")
    got = lines[:-1] if lines and lines[-1] == "N:" + nonce else lines
    mism = []
    for k, exp in enumerate(expected):
        g = got[k] if k < len(got) else None
        if g != exp:
            mism.append({"case": k, "expected": exp, "got": g})
    if len(got) != len(expected):
        failed.append("case_count")
    if mism:
        failed.append("vectors")
    res.update({
        "verdict": "fail" if failed else "pass",
        "failed": sorted(set(failed)),
        "n_mismatch": len(mism),
        "first_mismatches": mism[:3],
    })
    if err:
        res["error"] = err
    shutil.rmtree(bdir, ignore_errors=True)
    return res
