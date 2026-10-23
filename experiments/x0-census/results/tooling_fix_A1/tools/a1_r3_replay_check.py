#!/usr/bin/env python3
"""a1_r3_replay_check.py X0_DIR R1_CENSUS R2_CENSUS OUT.json WORK_DIR -- Amendment X0-A1 evidence tool, revision after
the review of X0-A1 r2 ("r3", x0r2 reviser, 2026-10-23; not a census input). Read only, on the laptop.

R1_CENSUS and R2_CENSUS are the census.json files of the r2 regression replay (runbook step 88 with the r2 tree:
R1 smoke-20261023T174221Z, R2 smoke-20261023T172426Z; NON-Hearth), copied read-only from the desktop
(D:\\mithril\\x0fixA1\\r2\\runs88\\<run>\\census.json). Nothing is compiled, decoded or assembled again: r3 does not
change x0_loops.py, and x0_census.py changes only the names of two metrics.x0_a1 counters and its schema check.
  1. judge.validate_schema (r3: with the X0-A1 consistency checks) on each census;
  2. judge.py and judge_regression.py (r3) on each census exactly as step 88 ran them (R1: judge.py, and
     judge_regression.py --set smoke/regression_set.json --synthetic-rederivation; R2: judge.py, and
     judge_regression.py --synthetic-rederivation), on a copy whose record.scripts_sha256 is replaced by r3's pins
     (class/frozen_inputs.json "scripts"). Without that, V4 fails only because r3 re-pinned the scripts, and judge.py
     stops before the rows. The replacement is the only change to the census; it is stated in OUT.json;
  3. every JSON path where r3's verdict differs from r2's (regression_replay/*verdict*.json), apart from the
     evaluation date basis.
Standard library only."""
import copy
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from a1_jsondiff import walk  # noqa: E402


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    x0, r1, r2, out_path, work = sys.argv[1:6]
    scripts = os.path.join(x0, "scripts")
    sys.path.insert(0, scripts)
    import judge  # noqa: E402
    with open(os.path.join(x0, "class", "frozen_inputs.json"), encoding="utf-8") as f:
        pins = json.load(f)["scripts"]
    os.makedirs(work, exist_ok=True)
    rr = os.path.join(x0, "results", "tooling_fix_A1", "regression_replay")
    jobs = [("R1reg", r1, [("verdict.json", [os.path.join(scripts, "judge.py")]),
                           ("verdict_regression_profile.json",
                            [os.path.join(scripts, "smoke", "judge_regression.py"), "--set",
                             os.path.join(scripts, "smoke", "regression_set.json"), "--synthetic-rederivation"])]),
            ("R2mock", r2, [("verdict.json", [os.path.join(scripts, "judge.py")]),
                            ("verdict_synthetic_rederivation.json",
                             [os.path.join(scripts, "smoke", "judge_regression.py"), "--synthetic-rederivation"])])]
    res = {"tool": "a1_r3_replay_check.py (x0r2 reviser, 2026-10-23)",
           "census_change": "record.scripts_sha256 replaced by r3's class/frozen_inputs.json scripts map (V4 only)",
           "judge.py": sha(os.path.join(scripts, "judge.py")), "runs": {}}
    for run, cpath, verdicts in jobs:
        with open(cpath, encoding="utf-8") as f:
            census = json.load(f)
        viol = judge.validate_schema(census)
        c2 = copy.deepcopy(census)
        c2["record"]["scripts_sha256"] = dict(pins)
        cp2 = os.path.join(work, "%s_census_repinned.json" % run)
        with open(cp2, "w", encoding="utf-8") as f:
            json.dump(c2, f)
        uns = sum(1 for v in census["variants"] for lp in v.get("loops") or [] if lp.get("unscreened"))
        entry = {"census_sha256": sha(cpath), "variants": len(census["variants"]), "unscreened_loop_records": uns,
                 "schema_violations": viol, "verdicts": {}}
        for name, argv in verdicts:
            newp = os.path.join(work, "%s_%s" % (run, name))
            p = subprocess.run([sys.executable, "-I"] + argv[:1] + [cp2, "-o", newp] + argv[1:],
                               capture_output=True, text=True)
            if p.returncode != 0:
                raise SystemExit(p.stdout + p.stderr)
            with open(os.path.join(rr, "%s_%s" % (run, name)), encoding="utf-8") as f:
                old = json.load(f)
            with open(newp, encoding="utf-8") as f:
                new = json.load(f)
            diffs = []
            walk(old, new, "", diffs)
            diffs = [d for d in diffs if not d["path"].startswith("eval_date_basis")]
            entry["verdicts"][name] = {
                "r2_outcomes": old["outcomes"], "r3_outcomes": new["outcomes"],
                "r3_validity": new["validity"],
                "r3_both_ways_frozen": {k: new["both_ways"]["frozen_reading"][k] for k in ("outcomes", "validity", "v3_basis")},
                "r3_p3c_differs": new["both_ways"]["p3c_differs"],
                "r3_variants_listed": len(new["both_ways"]["variants"]),
                "n_differences": len(diffs), "differences": diffs}
        res["runs"][run] = entry
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    for run, e in res["runs"].items():
        print(run, "schema violations", len(e["schema_violations"]), "unscreened", e["unscreened_loop_records"])
        for name, x in e["verdicts"].items():
            print(" ", name, x["r2_outcomes"], "->", x["r3_outcomes"], "frozen", x["r3_both_ways_frozen"]["outcomes"],
                  "diffs", x["n_differences"], sorted({d["path"].split("[")[0] for d in x["differences"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
