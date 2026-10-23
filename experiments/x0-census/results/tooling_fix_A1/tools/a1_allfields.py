#!/usr/bin/env python3
"""a1_allfields.py -- Amendment X0-A1 evidence tool (x0fix track, revision after the review of 2026-10-23; not a census
input). Compares EVERY field of two sets of loops.json files on the same decodes: BEFORE (the frozen x0_loops.py, or the
census run's own loops.json, which it reproduces byte for byte) against AFTER (the X0-A1 script).

  a1_allfields.py reloop OUTDIR CFG... [--before-dir DIR] -o RESULT.json
      AFTER from an a1_reloop.py output tree (OUTDIR/<CFG>/reloop.json); BEFORE the run's own loops.json named there,
      or the same step under --before-dir (another a1_reloop.py output tree).
  a1_allfields.py runs OLD_RUN NEW_RUN -o RESULT.json
      two x0_driver.py runs of the same inputs, unit by unit (RUN/<CFG>/b<k>/<unit>/loops.json).

Per variant record: every key except "loops" and the X0-A1 lists (p3c_unscreened, p3c_frozen_reading); p3 is compared
key by key (p3.c, p3.d1, p3.d1_sites, p3.d2). Per loop record: every key except the X0-A1 loop keys, counted by field and
by whether AFTER lists the loop as unscreened. Checks (each a count that must be 0):
  * frozen_reading_differs_from_before_p3c: AFTER's p3c_frozen_reading is not BEFORE's p3.c;
  * unscreened_frozen_count_differs: an unscreened loop's acc_lanes_if_escaping_slots_were_registers is not BEFORE's
    acc_lanes_emitted;
  * screened_count_differs: a loop not listed as unscreened whose acc_lanes_emitted changed;
  * screened_partial_results_differ: on a loop not listed as unscreened, AFTER's partial_results differ from BEFORE's
    with the escaping slot keys removed (x0_loops.py's own test for "unscreened").
A change of partial_results or partial_result_cycles on a screened loop that only drops escaping slot keys is counted
under loop_field_changes, not as a check failure.
Paths recorded by WSL steps (/mnt/d/...) are read as D:/... on Windows. Standard library only.
"""
import argparse
import collections
import json
import os
import sys

A1_VARIANT_KEYS = {"loops", "p3c_unscreened", "p3c_frozen_reading"}
A1_LOOP_KEYS = {"escaping_slots", "unscreened", "unscreened_reason", "escaping_partial_results",
                "acc_lanes_if_escaping_slots_were_registers", "escape_events"}


def native(p):
    if os.name == "nt" and p.startswith("/mnt/") and len(p) > 6:
        return p[5].upper() + ":" + p[6:]
    return p


def load(p):
    with open(native(p), encoding="utf-8") as f:
        return json.load(f)


def pairs_reloop(outdir, cfgs, before_dir):
    for cfg in cfgs:
        rl = load(os.path.join(outdir, cfg, "reloop.json"))
        for st in rl["steps"]:
            dd = native(st["argv"][3]).rstrip("/\\")
            unit = os.path.basename(os.path.dirname(dd))
            b = os.path.basename(os.path.dirname(os.path.dirname(dd)))
            bp = os.path.join(before_dir, cfg, st["step"], "loops.json") if before_dir else st["run_loops_json"]
            yield (cfg, b, unit), bp, os.path.join(outdir, cfg, st["step"], "loops.json")


def pairs_runs(old, new):
    for cfg in sorted(os.listdir(new)):
        for b in ("b1", "b2"):
            bdir = os.path.join(new, cfg, b)
            if not os.path.isdir(bdir):
                continue
            for u in sorted(os.listdir(bdir)):
                pn = os.path.join(bdir, u, "loops.json")
                po = os.path.join(old, cfg, b, u, "loops.json")
                if os.path.exists(pn) and os.path.exists(po):
                    yield (cfg, b, u), po, pn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("reloop", "runs"))
    ap.add_argument("a")
    ap.add_argument("rest", nargs="+")
    ap.add_argument("--before-dir")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    it = pairs_reloop(a.a, a.rest, a.before_dir) if a.mode == "reloop" else pairs_runs(a.a, a.rest[0])
    vfields, lfields, checks = collections.Counter(), collections.Counter(), collections.Counter()
    examples = collections.defaultdict(list)
    per = collections.defaultdict(collections.Counter)
    files = 0
    for (cfg, b, unit), pb, pa in it:
        files += 1
        before = {"%s:%s" % (r["table"], r["slot"]): r for r in load(pb)}
        after = {"%s:%s" % (r["table"], r["slot"]): r for r in load(pa)}
        pc = per["%s|%s" % (cfg, b)]
        for k in sorted(set(before) | set(after)):
            rb, ra = before.get(k), after.get(k)
            if rb is None or ra is None:
                vfields["variant present on one side only"] += 1
                continue
            pc["variants"] += 1
            for f in sorted((set(rb) | set(ra)) - A1_VARIANT_KEYS - {"p3"}):
                if rb.get(f) != ra.get(f):
                    vfields[f] += 1
                    examples["variant:" + f].append([cfg, b, unit, k]) if len(examples["variant:" + f]) < 5 else None
            qb, qa = rb.get("p3") or {}, ra.get("p3") or {}
            for f in sorted(set(qb) | set(qa)):
                if qb.get(f) != qa.get(f):
                    vfields["p3." + f] += 1
            if "p3c_frozen_reading" in ra and sorted(ra["p3c_frozen_reading"]) != sorted(qb.get("c") or []):
                checks["frozen_reading_differs_from_before_p3c"] += 1
                examples["check:frozen_reading"].append([cfg, b, unit, k])
            pc["p3c_flagged_loops_before"] += len(qb.get("c") or [])
            pc["p3c_flagged_loops_after"] += len(qa.get("c") or [])
            pc["p3c_flagged_variants_before"] += bool(qb.get("c"))
            pc["p3c_flagged_variants_after"] += bool(qa.get("c"))
            pc["p3c_flagged_loops_after_frozen_reading"] += len(ra.get("p3c_frozen_reading") or [])
            lb = {x["id"]: x for x in rb.get("loops", [])}
            la = {x["id"]: x for x in ra.get("loops", [])}
            if set(lb) != set(la):
                lfields["loop ids differ"] += 1
            for lid in sorted(set(lb) & set(la)):
                xb, xa = lb[lid], la[lid]
                uns = bool(xa.get("unscreened"))
                side = "unscreened" if uns else "screened"
                pc["loops"] += 1
                pc["unscreened_loops_after"] += uns
                pc["loops_with_escaping_slots_after"] += bool(xa.get("escaping_slots"))
                for f in sorted((set(xb) | set(xa)) - A1_LOOP_KEYS):
                    if xb.get(f) != xa.get(f):
                        lfields["%s|%s" % (f, side)] += 1
                        ex = examples["loop:%s|%s" % (f, side)]
                        if len(ex) < 5:
                            ex.append([cfg, b, unit, k, lid, xb.get(f), xa.get(f)])
                if uns and xa.get("acc_lanes_if_escaping_slots_were_registers") != xb.get("acc_lanes_emitted"):
                    checks["unscreened_frozen_count_differs"] += 1
                if not uns and xa.get("acc_lanes_emitted") != xb.get("acc_lanes_emitted"):
                    checks["screened_count_differs"] += 1
                if not uns:
                    esc = set(xa.get("escaping_slots") or [])
                    rest = sorted(g for g in ([x for x in g0 if x not in esc] for g0 in xb.get("partial_results") or []) if g)
                    if rest != sorted(xa.get("partial_results") or []):
                        checks["screened_partial_results_differ"] += 1
    for c in ("frozen_reading_differs_from_before_p3c", "unscreened_frozen_count_differs", "screened_count_differs",
              "screened_partial_results_differ"):
        checks.setdefault(c, 0)
    res = {"mode": a.mode, "files": files, "variant_field_changes": dict(sorted(vfields.items())),
           "loop_field_changes": dict(sorted(lfields.items())), "checks": dict(sorted(checks.items())),
           "per_config_build": {k: dict(v) for k, v in sorted(per.items())}, "examples": dict(sorted(examples.items()))}
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print(json.dumps({k: res[k] for k in ("files", "variant_field_changes", "loop_field_changes", "checks")}, indent=1))
    return 0 if not any(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
