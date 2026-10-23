#!/usr/bin/env python3
"""a1_r3_bothways.py X0_DIR AFTER_CENSUS OUT_DIR WORK_DIR -- Amendment X0-A1 evidence tool, revision after the review of
X0-A1 r2 ("r3", x0r2 reviser, 2026-10-23; not a census input). Read only, on the laptop; no compile, no decode, no
new census, no desktop.

AFTER_CENSUS is census run 1's census.json with the loops.json-derived fields taken from the r2 re-run of x0_loops.py
(tools/a1_pvalues.py --after-census; SHA-256 dd9c4acd...; x0_loops.py is unchanged in r3, so the r2 re-run stands).
X0_DIR is experiments/x0-census at r3. Steps:
  1. judge.validate_schema (r3: with the X0-A1 consistency checks) on AFTER_CENSUS;
  2. rederive/compare_x0.py (r3) with census run 1's frozen re-derivation v1 (results/rederive/figures.json and
     rederive_detail.json) against AFTER_CENSUS: the amended comparison and the frozen-reading comparison;
  3. judge.py (r3) on AFTER_CENSUS as it is (no re-derivation, as in r2's preview) and on step 2's census (both
     rederivation blocks). Both are previews, NOT verdicts: V4 fails (the scripts are not census run 1's), and the
     re-derivation is v1 of 2026-10-17, which REPORT section 20 replaces by a fresh one.
Writes OUT_DIR/schema_after_x0a1_r3.json, OUT_DIR/comparison_after_x0a1_both_ways_r3.json,
OUT_DIR/judge_preview_r3_no_rederivation_NOT_A_VERDICT.json, OUT_DIR/judge_preview_r3_rederivation_v1_NOT_A_VERDICT.json
and OUT_DIR/bothways_r3_summary.json (inputs and outputs with SHA-256, outcomes both ways, V3 per reading). The census
with both rederivation blocks (7 MB, census run 1 data) goes to WORK_DIR only; its SHA-256 is in the summary.
Standard library only."""
import hashlib
import json
import os
import subprocess
import sys


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(argv):
    r = subprocess.run([sys.executable, "-I"] + argv, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("failed (%d): %s\n%s%s" % (r.returncode, " ".join(argv), r.stdout, r.stderr))
    return r.stdout


def main():
    x0, after, out, work = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    os.makedirs(work, exist_ok=True)
    scripts = os.path.join(x0, "scripts")
    sys.path.insert(0, scripts)
    import judge  # noqa: E402
    with open(after, encoding="utf-8") as f:
        census = json.load(f)
    schema = judge.validate_schema(census)
    p_schema = os.path.join(out, "schema_after_x0a1_r3.json")
    with open(p_schema, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"violations": schema}, f, indent=1)
    figs = os.path.join(x0, "results", "rederive", "figures.json")
    detail = os.path.join(x0, "results", "rederive", "rederive_detail.json")
    p_cmp = os.path.join(out, "comparison_after_x0a1_both_ways_r3.json")
    p_crd = os.path.join(work, "census_after_x0a1_with_rederivation_v1_r3.json")
    cmp_stdout = run([os.path.join(x0, "rederive", "compare_x0.py"), "--figures", figs, "--detail", detail,
                      "--census", after, "--out-comparison", p_cmp, "--out-census", p_crd])
    p_j0 = os.path.join(out, "judge_preview_r3_no_rederivation_NOT_A_VERDICT.json")
    p_j1 = os.path.join(out, "judge_preview_r3_rederivation_v1_NOT_A_VERDICT.json")
    j0 = run([os.path.join(scripts, "judge.py"), after, "-o", p_j0])
    j1 = run([os.path.join(scripts, "judge.py"), p_crd, "-o", p_j1])
    res = {"tool": "a1_r3_bothways.py (x0r2 reviser, 2026-10-23)", "not_a_verdict": True,
           "inputs": {"after_census": sha(after), "figures.json": sha(figs), "rederive_detail.json": sha(detail),
                      "judge.py": sha(os.path.join(scripts, "judge.py")),
                      "compare_x0.py": sha(os.path.join(x0, "rederive", "compare_x0.py")),
                      "frozen_inputs.json": sha(os.path.join(x0, "class", "frozen_inputs.json"))},
           "schema_violations": len(schema), "compare_stdout_tail": cmp_stdout.strip().splitlines()[-3:],
           "census_with_both_rederivation_blocks_sha256": sha(p_crd), "previews": {}}
    with open(p_cmp, encoding="utf-8") as f:
        comp = json.load(f)
    res["comparison"] = {"amended": {"matches": comp["matches"], "n_mismatches": comp["n_mismatches"]},
                         "frozen_reading": {k: comp["frozen_reading"][k] for k in ("matches", "n_mismatches")},
                         "frozen_only": sorted("%s %s" % (m["kind"], m["key"]) for m in comp["frozen_reading"]["mismatches"]
                                               if m not in comp["mismatches"]),
                         "amended_only": sorted("%s %s" % (m["kind"], m["key"]) for m in comp["mismatches"]
                                                if m not in comp["frozen_reading"]["mismatches"])}
    for name, p, so in (("no_rederivation", p_j0, j0), ("rederivation_v1", p_j1, j1)):
        with open(p, encoding="utf-8") as f:
            v = json.load(f)
        bw = v["both_ways"]["frozen_reading"]
        res["previews"][name] = {
            "file": os.path.basename(p), "sha256": sha(p), "stdout": so.strip(),
            "amended": {"outcomes": v["outcomes"], "validity": v["validity"],
                        "v3_mismatches": len(v["validity_detail"]["v3"]) if isinstance(v["validity_detail"].get("v3"), list) else v["validity_detail"].get("v3"),
                        "amber_b_configs": v["both_ways"]["amber_b_configs"]},
            "frozen_reading": {"outcomes": bw["outcomes"], "validity": bw["validity"], "v3_basis": bw["v3_basis"],
                               "v3_mismatches": len(bw["validity_detail"]["v3"]) if isinstance(bw["validity_detail"].get("v3"), list) else bw["validity_detail"].get("v3"),
                               "amber_b_configs": v["both_ways"]["amber_b_configs_frozen_reading"]},
            "p3c_differs": v["both_ways"]["p3c_differs"], "variants_listed": len(v["both_ways"]["variants"]),
            "outcomes_differ": v["both_ways"]["outcomes_differ"]}
    with open(os.path.join(out, "bothways_r3_summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
