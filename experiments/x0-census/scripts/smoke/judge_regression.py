#!/usr/bin/env python3
"""judge_regression.py -- run judge.py's decision list on a NON-Hearth driver run (x0final; smoke only).

  python -I judge_regression.py CENSUS.json -o VERDICT.json [--set regression_set.json] [--synthetic-rederivation]

judge.py's constants describe Hearth: tables hx_kernels_scalar, k_avx2, k_avx512, census files quant.c,
quant_avx2.c, quant_avx512.c, 18 variants per configuration. A census.json of the regression set (assembled with
--qualify-tables) has other tables, so the unmodified judge.py reports every Hearth variant missing (V1) and says
tooling_failure, which is correct for it. To exercise the decision list on real regression data, --set replaces
those constants IN THIS PROCESS ONLY with the regression set's own: the census files are the set's ids, and the
expected (table, slot) pairs are read from the set's SOURCES with x0_extract's parser (never from an object);
the d1 canary is sd_table@smoke_dispatch.c#scalar:act_quantize. Without --set (the mock, which has Hearth's
shape) the constants stay judge.py's own.
--synthetic-rederivation replaces census.json's rederivation block, in memory, by {present: true, matches: true}
so that the rows after V3 are evaluated; the verdict then carries "SYNTHETIC REDERIVATION" in its notes. No real
re-derivation exists; nothing produced with this flag is a census result.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import judge  # noqa: E402
import x0_extract  # noqa: E402


def regression_profile(sset_path):
    sset = json.load(open(sset_path))
    root = os.path.dirname(SCRIPTS)
    expected, file_of_table, ids = [], {}, []
    for f in sset["files"]:
        src = os.path.join(root, *f["source"].split("/"))
        text = open(src, encoding="utf-8").read()
        fields, _ = x0_extract.parse_struct(text, f["struct"])
        tables, _ = x0_extract.parse_tables(text, f["struct"])
        ids.append(f["id"])
        for tname, t in sorted(tables.items()):
            q = "%s@%s" % (tname, f["id"])
            file_of_table[q] = f["id"]
            for s in x0_extract.table_slots(fields, t, None):
                if s["source_function"]:
                    expected.append((q, s["slot"]))
    judge.EXPECTED_VARIANTS = expected
    judge.TABLES = tuple(sorted(file_of_table))
    judge.SLOTS = tuple(sorted({s for _, s in expected}))
    judge.FILE_OF_TABLE = file_of_table
    judge.CENSUS_FILES = tuple(ids)
    judge.CANARY = ("sd_table@smoke_dispatch.c#scalar", "act_quantize")
    return {"expected_variants": len(expected), "census_files": ids}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("census")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--set")
    ap.add_argument("--synthetic-rederivation", action="store_true")
    ap.add_argument("--class-dir", default=os.path.join(SCRIPTS, "..", "class"))
    a = ap.parse_args()
    census = json.load(open(a.census))
    prof = regression_profile(a.set) if a.set else {"profile": "judge.py constants (Hearth shape)"}
    notes = ["NON-Hearth smoke run judged by judge_regression.py: %s" % json.dumps(prof)]
    if a.synthetic_rederivation:
        census["rederivation"] = {"present": True, "matches": True, "mismatches": [],
                                  "note": "SYNTHETIC REDERIVATION (judge_regression.py, smoke only)"}
        notes.append("SYNTHETIC REDERIVATION: V3 forced true to exercise the rows; not a census result")
    d, basis = judge.evaluation_date(census)
    v = judge.judge(census, a.class_dir, d, date_basis=basis)
    v["notes"] = notes + v.get("notes", [])
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(v, f, indent=1, sort_keys=True)
    print(json.dumps({"outcomes": v["outcomes"], "validity": v["validity"], "amber_b": [x["config"] for x in v["amber_b"]],
                      "amber_c": len(v["amber_c"]), "non_gate": sorted({(x["row"], x["config"]) for x in v["non_gate"]}),
                      "amber_a": {k: v["amber_a"][k] for k in ("u_all", "p5_iclass", "holds")} if v.get("amber_a") else None,
                      "v1_gaps": len((v.get("validity_detail") or {}).get("v1_tooling_gaps", []) or []),
                      "v1_config_gaps": len((v.get("validity_detail") or {}).get("v1_config_gaps", []) or []),
                      "v4": (v.get("validity_detail") or {}).get("v4")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
