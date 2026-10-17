"""Runner of the seeded table mutants (FUZZ-DESIGN.md §6.4; mutants.py). Comparator time only: the silicon
results are reused, never re-run. One Python process at a time (1 thread).

  python -I -B run_mutants.py --sem-root DIR --manifest stubs_manifest.json --vectors VEC --silicon SIL
         --work DIR --out SUMMARY.json [--silicon2 SIL2] [--only M01_...,M04_...]

For the unmutated table and then for each mutant: pyref.py predicts VEC with that table, and compare.py
compares the predictions with SIL. A mutant is DETECTED when the set of disagreements differs from the
baseline's: a new disagreeing record, or a baseline record whose disagreement (lanes, table values, table
MXCSR, verdict) changed. The summary names the vectors, silicon, manifest and spec hashes (provenance), the
baseline counts, and per mutant: detected, the new or changed records, their kinds (lane, upper bits,
flag only, fault) and the stubs hit.

What a run shows depends on the vector set: on development data it calibrates the runner; the X2 record's
calibration arm runs it on the frozen budget's silicon results (target: every §6.4 mutant detected).
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, HARNESS)
import mutants  # noqa: E402
import vecfmt  # noqa: E402


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise SystemExit("FAILED %s\n%s\n%s" % (cmd, p.stdout[-2000:], p.stderr[-2000:]))
    return p.stdout


def sig(d):
    return json.dumps({k: d.get(k) for k in ("lanes", "lane", "table", "mxcsr_table", "verdict")}, sort_keys=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True, help="directory containing the UNMUTATED semantics/")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--silicon", required=True)
    ap.add_argument("--silicon2")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only")
    a = ap.parse_args(argv)
    py = [sys.executable, "-I", "-B"]
    os.makedirs(a.work, exist_ok=True)

    def report(sem_root, tag):
        pred = os.path.join(a.work, tag + ".pred")
        out = os.path.join(a.work, tag + ".report.json")
        run(py + [os.path.join(HARNESS, "pyref.py"), "--sem-root", sem_root, "--manifest", a.manifest, a.vectors, pred])
        cmd = py + [os.path.join(HARNESS, "compare.py"), "--manifest", a.manifest, "--vectors", a.vectors, "--silicon",
                    a.silicon, "--pred", pred, "--out", out]
        if a.silicon2:
            cmd += ["--silicon2", a.silicon2]
        run(cmd)
        with open(out) as f:
            return json.load(f)

    seal = mutants.seal()
    with open(a.manifest, "rb") as f:
        manifest_sha = hashlib.sha256(f.read()).hexdigest()
    base = report(a.sem_root, "baseline")
    base_sig = {d["record"]: sig(d) for d in base["disagreements"]}
    keys = ("records", "lane_cases", "lane_mismatches", "flag_mismatch_executions", "cells_with_mismatch",
            "interpreter_divergences", "nondeterminism", "harness_anomalies")
    res = {"tool": "run_mutants.py", "spec": seal, "provenance": {
        "vectors_sha256": vecfmt.file_sha256(a.vectors), "silicon_sha256": vecfmt.file_sha256(a.silicon),
        "silicon2_sha256": vecfmt.file_sha256(a.silicon2) if a.silicon2 else None, "manifest_sha256": manifest_sha,
        "vectors_label": base["vectors_label"]},
        "baseline": {k: base[k] for k in keys}, "baseline_disagreement_records": sorted(base_sig), "mutants": {}}
    names = [n for n in mutants.MUTANTS if not a.only or n in a.only.split(",")]
    for nm in names:
        root = os.path.join(a.work, "mut", nm)
        os.makedirs(root, exist_ok=True)
        mutants.apply(os.path.join(a.sem_root, "semantics"), root, nm)
        rep = report(root, os.path.join("mut", nm, "m"))
        new = [d for d in rep["disagreements"] if d["record"] not in base_sig]
        changed = [d for d in rep["disagreements"] if d["record"] in base_sig and sig(d) != base_sig[d["record"]]]
        gone = sorted(set(base_sig) - {d["record"] for d in rep["disagreements"]})
        kinds = {"lane": 0, "upper": 0, "flag_only": 0, "fault": 0}
        for d in new + changed:
            ls = d.get("lanes")
            if ls is None:
                kinds["fault"] += 1
            elif not ls:
                kinds["flag_only"] += 1
            elif all(x == "upper" for x in ls):
                kinds["upper"] += 1
            else:
                kinds["lane"] += 1
        stubs = sorted({d["iform"] + ":" + d["variant"] for d in new + changed})
        res["mutants"][nm] = {"design_list": nm in seal["design_list"], "detected": bool(new or changed or gone),
                              "new_disagreeing_executions": len(new), "changed_baseline_records": len(changed),
                              "baseline_records_no_longer_disagreeing": len(gone), "kinds": kinds,
                              "lane_mismatches": rep["lane_mismatches"],
                              "flag_mismatch_executions": rep["flag_mismatch_executions"],
                              "anomalies": rep["harness_anomalies"],
                              "n_stubs_hit": len(stubs), "stubs_hit": stubs[:12]}
        print("%-32s detected=%-5s new=%-5d changed=%-3d %s" % (nm, res["mutants"][nm]["detected"], len(new),
                                                               len(changed), json.dumps(kinds)), flush=True)
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    det = [n for n, v in res["mutants"].items() if v["detected"]]
    dl = [n for n in names if n in seal["design_list"]]
    res["summary"] = {"mutants_run": len(names), "detected": len(det),
                      "design_list_detected": sum(1 for n in dl if n in det), "design_list_run": len(dl),
                      "not_detected": [n for n in names if n not in det]}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
