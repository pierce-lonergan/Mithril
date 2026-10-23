#!/usr/bin/env python3
"""a1_otherfields.py OLD_OUTDIR NEW_OUTDIR -o RESULT.json -- Amendment X0-A1 evidence tool (x0fix track, 2026-10-23; not a
census input). For two a1_reloop.py output trees (the pinned and the fixed x0_loops.py on the same decodes), checks that
every per-variant field of loops.json OTHER than the loop records and the P3(c) lists is byte-for-byte equal after JSON
parsing: attribution, P3(d1) and its sites, P3(d2) sites and results, the helper sequences and the arm-P probe records.
Also counts, per configuration and build, the P3(c)-flagged loops and variants on each side (revision after the review
of 2026-10-23: also the NEW side's frozen-reading P3(c) list, which must equal the OLD side's p3.c). Standard library
only."""
import argparse
import collections
import glob
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    res = {"differences": [], "p3c": {}, "files": 0}
    for p_new in sorted(glob.glob(os.path.join(a.new, "*", "loops_*", "loops.json"))):
        rel = os.path.relpath(p_new, a.new)
        cfg, step = rel.split(os.sep)[0], rel.split(os.sep)[1]
        p_old = os.path.join(a.old, rel)
        old = {"%s:%s" % (r["table"], r["slot"]): r for r in json.load(open(p_old, encoding="utf-8"))}
        new = {"%s:%s" % (r["table"], r["slot"]): r for r in json.load(open(p_new, encoding="utf-8"))}
        res["files"] += 1
        if set(old) != set(new):
            res["differences"].append({"file": rel, "what": "variant keys differ"})
        b = step.split("_")[1]
        cnt = res["p3c"].setdefault("%s|%s" % (cfg, b), collections.Counter())
        for k in sorted(set(old) & set(new)):
            ro, rn = dict(old[k]), dict(new[k])
            cnt["variants"] += 1
            cnt["loops"] += len(rn.get("loops", []))
            cnt["flagged_loops_before"] += len(ro["p3"].get("c") or [])
            cnt["flagged_loops_after"] += len(rn["p3"].get("c") or [])
            cnt["flagged_variants_before"] += 1 if ro["p3"].get("c") else 0
            cnt["flagged_variants_after"] += 1 if rn["p3"].get("c") else 0
            cnt["unscreened_loops_after"] += len(rn.get("p3c_unscreened") or [])
            if "p3c_frozen_reading" in rn:     # revision after the review of 2026-10-23
                cnt["flagged_loops_after_frozen_reading"] += len(rn["p3c_frozen_reading"])
                cnt["frozen_reading_differs_from_before"] += sorted(rn["p3c_frozen_reading"]) != sorted(ro["p3"].get("c") or [])
            for r in (ro, rn):
                r.pop("loops", None)
                r.pop("p3c_unscreened", None)
                r.pop("p3c_frozen_reading", None)
                r["p3"] = {x: y for x, y in r["p3"].items() if x != "c"}
            if ro != rn:
                diff = sorted(x for x in set(ro) | set(rn) if ro.get(x) != rn.get(x))
                res["differences"].append({"file": rel, "variant": k, "fields": diff})
    res["p3c"] = {k: dict(v) for k, v in res["p3c"].items()}
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps({"files": res["files"], "differences": len(res["differences"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
