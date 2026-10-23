#!/usr/bin/env python3
"""a1_runcompare.py OLD_RUN NEW_RUN -o RESULT.json -- Amendment X0-A1 evidence tool (x0fix track, 2026-10-23; not a census
input). Compares two x0_driver.py runs of the same NON-Hearth inputs (the 2026-10-17 step-88 run with the scripts pinned
at the freeze, and the step-88 re-run with the X0-A1 scripts), unit by unit (RUN/<CFG>/b<k>/<unit>/):
  * the decode outputs (decode/variants.json and decode/instructions.jsonl byte for byte), so that any loop difference is
    known to come from x0_loops.py and not from the code analysed;
  * P3(c) flags per (config, build, unit, table, slot): removed and added loop ids;
  * every loop whose acc_lanes_emitted, partial_results, bound_used, tags or source_loop differ, and every loop the new
    run lists as unscreened, with its escaping slots and the partial results the frozen reading counted in them;
  * d1 and d2 results per variant.
Standard library only.
"""
import argparse
import hashlib
import json
import os
import sys


def sha(p):
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def units(run):
    out = {}
    for cfg in sorted(os.listdir(run)):
        cdir = os.path.join(run, cfg)
        if not os.path.isdir(cdir):
            continue
        for b in ("b1", "b2"):
            bdir = os.path.join(cdir, b)
            if not os.path.isdir(bdir):
                continue
            for u in sorted(os.listdir(bdir)):
                if os.path.exists(os.path.join(bdir, u, "loops.json")) or os.path.isdir(os.path.join(bdir, u, "decode")):
                    out[(cfg, b, u)] = os.path.join(bdir, u)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    uo, un = units(a.old), units(a.new)
    res = {"old": a.old, "new": a.new, "units_only_old": [list(k) for k in sorted(set(uo) - set(un))],
           "units_only_new": [list(k) for k in sorted(set(un) - set(uo))], "decode_differs": [],
           "flags_removed": [], "flags_added": [], "loop_changes": [], "unscreened": [], "canary_changes": [],
           "summary": {}}
    n_loops = n_var = 0
    for k in sorted(set(uo) & set(un)):
        for f in ("decode/variants.json", "decode/instructions.jsonl"):
            if sha(os.path.join(uo[k], f)) != sha(os.path.join(un[k], f)):
                res["decode_differs"].append(list(k) + [f])
        po, pn = os.path.join(uo[k], "loops.json"), os.path.join(un[k], "loops.json")
        if not (os.path.exists(po) and os.path.exists(pn)):
            continue
        lo = {"%s:%s" % (r["table"], r["slot"]): r for r in json.load(open(po, encoding="utf-8"))}
        ln = {"%s:%s" % (r["table"], r["slot"]): r for r in json.load(open(pn, encoding="utf-8"))}
        for v in sorted(set(lo) | set(ln)):
            ro, rn = lo.get(v), ln.get(v)
            if ro is None or rn is None:
                res["loop_changes"].append({"unit": list(k), "variant": v, "change": "variant on one side only"})
                continue
            n_var += 1
            co, cn = set(ro["p3"].get("c") or []), set(rn["p3"].get("c") or [])
            bo = {x["id"]: x for x in ro.get("loops", [])}
            bn = {x["id"]: x for x in rn.get("loops", [])}
            n_loops += len(bn)
            for lid in sorted(co - cn):
                res["flags_removed"].append({"unit": list(k), "variant": v, "loop": lid,
                                             "old_lanes": bo.get(lid, {}).get("acc_lanes_emitted"),
                                             "new_lanes": bn.get(lid, {}).get("acc_lanes_emitted"),
                                             "bound": bo.get(lid, {}).get("bound_used"),
                                             "new_unscreened": bn.get(lid, {}).get("unscreened"),
                                             "escape_events": bn.get(lid, {}).get("escape_events")})
            for lid in sorted(cn - co):
                res["flags_added"].append({"unit": list(k), "variant": v, "loop": lid,
                                           "new_lanes": bn.get(lid, {}).get("acc_lanes_emitted"),
                                           "bound": bn.get(lid, {}).get("bound_used")})
            if set(bo) != set(bn):
                res["loop_changes"].append({"unit": list(k), "variant": v, "change": "loop ids differ",
                                            "old": sorted(bo), "new": sorted(bn)})
            for lid in sorted(set(bo) & set(bn)):
                d = {x: [bo[lid].get(x), bn[lid].get(x)] for x in ("acc_lanes_emitted", "partial_results", "bound_used",
                                                                   "tags", "source_loop", "acc_updates_per_iter")
                     if bo[lid].get(x) != bn[lid].get(x)}
                if d:
                    res["loop_changes"].append({"unit": list(k), "variant": v, "loop": lid, "diff": d,
                                                "unscreened": bn[lid].get("unscreened"),
                                                "escaping_slots": bn[lid].get("escaping_slots")})
                if bn[lid].get("unscreened"):
                    res["unscreened"].append({"unit": list(k), "variant": v, "loop": lid,
                                              "source_loop": bn[lid].get("source_loop"),
                                              "escaping_partial_results": bn[lid].get("escaping_partial_results"),
                                              "acc_lanes_if_escaping_slots_were_registers":
                                                  bn[lid].get("acc_lanes_if_escaping_slots_were_registers"),
                                              "acc_lanes_emitted": bn[lid].get("acc_lanes_emitted"),
                                              "first_escape_event": (bn[lid].get("escape_events") or [None])[0]})
            for x in ("d1", "d2"):
                if ro["p3"].get(x) != rn["p3"].get(x):
                    res["canary_changes"].append({"unit": list(k), "variant": v, "field": x})
    res["summary"] = {"units_compared": len(set(uo) & set(un)), "variants": n_var, "loops_new": n_loops,
                      "decode_files_differ": len(res["decode_differs"]), "flags_removed": len(res["flags_removed"]),
                      "flags_added": len(res["flags_added"]),
                      "loops_changed": sum(1 for c in res["loop_changes"] if "diff" in c),
                      "unscreened_new": len(res["unscreened"]), "canary_changes": len(res["canary_changes"])}
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
