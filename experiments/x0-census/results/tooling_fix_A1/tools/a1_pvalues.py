#!/usr/bin/env python3
"""a1_pvalues.py SCRIPTS_DIR CENSUS_JSON LOOPS_DIR -o TABLE.tsv [--json OUT.json] [--after-census AFTER.json]
-- Amendment X0-A1 evidence tool (x0fix track, revision after the review of 2026-10-23; not a census input).

Record §10: "The fix is logged with a before/after table of every P1 to P5 value". BEFORE is census run 1's census.json
as written on 2026-10-17. AFTER is the same census with only the fields x0_census.py copies from loops.json replaced by
the X0-A1 script's loops.json for the same unit (LOOPS_DIR/<CFG>/reloop.json from a1_reloop.py; read only): p3.c,
p3.d1, p3.d1_sites, p3.d2, loops, sequences, probe, attribution, attribution_detail, and the X0-A1 lists p3c_unscreened
and p3c_frozen_reading (as the revised x0_census.py copies them). Every other field is census run 1's own: no compile,
no decode, no new census. The values are computed with judge.py's own definitions (SCRIPTS_DIR/judge.py: the main union,
FMA_RE and APPROX_RE, the gap cause sets, fp_class.csv), per configuration and build:
  P1  variant records, slots resolved, build records with a non-zero exit status (builds[]: B-cmake's quant_avx512.c,
      whose six variants then have no record), genuine and tooling gaps in the variants' coverage;
  P2  FMA-class count (the larger of p2_fma and the FMA-class iclasses, per variant, summed);
  P3(a) flagged census files; P3(b) variants with an approximation; P3(c) flagged loops and variants (and, AFTER only,
      those of the frozen reading and the unscreened loops); P3(d1) the canary's result; P3(d2) match/mismatch/unchecked;
and over the main union (judge.py), P4 = |U_all|, P5_iclass and P5_opclass. Writes one row per configuration and build
and one row "union". Standard library only."""
import argparse
import collections
import copy
import csv
import json
import os
import sys

COPIED = ("loops", "sequences", "probe", "attribution", "attribution_detail")
P3_COPIED = ("c", "d1", "d1_sites", "d2")


def native(p):
    if os.name == "nt" and p.startswith("/mnt/") and len(p) > 6:
        return p[5].upper() + ":" + p[6:]
    return p


def load(p):
    with open(native(p), encoding="utf-8") as f:
        return json.load(f)


def after_census(census, loops_dir):
    """Census run 1 with the loops.json-derived fields of each variant taken from the X0-A1 re-run."""
    lj = {}
    for cfg in sorted(os.listdir(loops_dir)):
        rp = os.path.join(loops_dir, cfg, "reloop.json")
        if not os.path.exists(rp):
            continue
        for st in load(rp)["steps"]:
            dd = native(st["argv"][3]).rstrip("/\\")
            unit = os.path.basename(os.path.dirname(dd))
            b = int(os.path.basename(os.path.dirname(os.path.dirname(dd)))[1:])
            for r in load(os.path.join(loops_dir, cfg, st["step"], "loops.json")):
                lj[(cfg, b, unit, r["table"], r["slot"])] = r
    out = copy.deepcopy(census)
    missing = 0
    for v in out["variants"]:
        r = lj.get((v["config"], v["build_index"], v.get("unit"), v["table"].split("@")[0], v["slot"]))
        if r is None:
            missing += 1
            continue
        for k in COPIED:
            if k in r:
                v[k] = r[k]
        for k in P3_COPIED:
            if k in (r.get("p3") or {}) and (k != "d1" or r.get("key_is_canary")):
                v["p3"][k] = r["p3"][k]
        v["p3c_unscreened"] = list(r.get("p3c_unscreened", []))
        v["p3c_frozen_reading"] = list(r.get("p3c_frozen_reading", v["p3"].get("c") or []))
    return out, missing


def values(census, J, fpc, opc):
    rows = collections.OrderedDict()
    configs = census.get("configs") or {}
    for v in census["variants"]:
        key = (v["config"], v["build_index"])
        r = rows.setdefault(key, collections.Counter())
        q = v.get("p3") or {}
        r["P1_variants"] += 1
        r["P1_slots_resolved"] += bool((v.get("coverage") or {}).get("slot_resolved"))
        for g in (v.get("coverage") or {}).get("gaps") or []:
            r["P1_genuine_gaps"] += g.get("cause") in J.GENUINE
            r["P1_tooling_gaps"] += g.get("cause") in J.TOOLING
        r["P2_fma"] += max(int(v.get("p2_fma") or 0),
                           sum(int(n) for i, n in (v.get("iclasses") or {}).items() if J.FMA_RE.match(i or "")))
        r["P3b_variants"] += bool(q.get("b") or any(J.APPROX_RE.match(i or "") for i in (v.get("iclasses") or {})))
        r["P3c_flagged_loops"] += len(q.get("c") or [])
        r["P3c_flagged_variants"] += bool(q.get("c"))
        if "p3c_frozen_reading" in v:
            r["P3c_flagged_loops_frozen_reading"] += len(v["p3c_frozen_reading"])
            r["P3c_flagged_variants_frozen_reading"] += bool(v["p3c_frozen_reading"])
            r["P3c_unscreened_loops"] += len(v.get("p3c_unscreened") or [])
        if (v["table"].split("@")[0], v["slot"]) == J.CANARY:
            r["P3d1"] = q.get("d1")
        for s in q.get("d2") or []:
            r["P3d2_" + str(s.get("result"))] += 1
    for b in census.get("builds") or []:
        if (b.get("config"), b.get("build_index")) in rows and b.get("rc") != 0:
            rows[(b["config"], b["build_index"])]["P1_builds_rc_nonzero"] += 1
    out = []
    for (cfg, bi), r in rows.items():
        p3a = sorted(f for f, x in ((configs.get(cfg) or {}).get("p3a") or {}).items()
                     if isinstance(x, dict) and (x.get("a1") or x.get("a2")))
        out.append(dict(r, config=cfg, build="b%d" % bi, P3a_flagged_files=",".join(p3a) or "none"))
    union = [v for v in census["variants"] if v.get("config") in J.MAIN or
             (v.get("config") == "A-ninja" and v.get("union_member"))]
    u_all, ic = set(), set()
    for v in union:
        u_all |= set(v.get("iforms") or {})
        ic |= set(v.get("iclasses") or {})
    fp_ic = {i for i in ic if fpc.get(i, True)}
    out.append({"config": "union", "build": "b1+b2", "P4_u_all": len(u_all), "P5_iclass": len(fp_ic),
                "P5_opclass": len({opc.get(i, i) for i in fp_ic})})
    return out


COLS = ["P1_variants", "P1_slots_resolved", "P1_builds_rc_nonzero", "P1_genuine_gaps", "P1_tooling_gaps", "P2_fma", "P3a_flagged_files",
        "P3b_variants", "P3c_flagged_loops", "P3c_flagged_variants", "P3d1", "P3d2_match", "P3d2_mismatch",
        "P3d2_unchecked", "P4_u_all", "P5_iclass", "P5_opclass"]
AFTER_ONLY = ["P3c_flagged_loops_frozen_reading", "P3c_flagged_variants_frozen_reading", "P3c_unscreened_loops"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts")
    ap.add_argument("census")
    ap.add_argument("loops_dir")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--json")
    ap.add_argument("--after-census")
    a = ap.parse_args()
    sys.path.insert(0, a.scripts)
    import judge as J
    cls = os.path.join(a.scripts, "..", "class", "fp_class.csv")
    fpc, opc = {}, {}
    with open(cls, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            fpc[r["iclass"]] = r["fp_sensitive"] == "yes"
            opc[r["iclass"]] = r["op_class"]
    before = load(a.census)
    after, missing = after_census(before, a.loops_dir)
    vb, va = values(before, J, fpc, opc), values(after, J, fpc, opc)
    hdr = ["config", "build"]
    for c in COLS:
        hdr += [c + "_before", c + "_after"]
    hdr += [c + "_after" for c in AFTER_ONLY] + ["changed"]
    ab = {(r["config"], r["build"]): r for r in va}
    rows = []
    for rb in vb:
        ra = ab[(rb["config"], rb["build"])]
        row = {"config": rb["config"], "build": rb["build"]}
        changed = []
        for c in COLS:
            x, y = rb.get(c, "" if rb["config"] == "union" or c.startswith("P4") or c.startswith("P5") else 0), \
                ra.get(c, "" if ra["config"] == "union" or c.startswith("P4") or c.startswith("P5") else 0)
            row[c + "_before"], row[c + "_after"] = x, y
            if x != y:
                changed.append(c)
        for c in AFTER_ONLY:
            row[c + "_after"] = ra.get(c, "" if ra["config"] == "union" else 0)
        row["changed"] = ",".join(changed) or "none"
        rows.append(row)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(hdr) + "\n")
        for r in rows:
            fh.write("\t".join(str(r.get(h, "")) for h in hdr) + "\n")
    res = {"census": a.census, "loops_dir": a.loops_dir, "variants_without_a_rerun_record": missing,
           "rows_changed": [(r["config"], r["build"], r["changed"]) for r in rows if r["changed"] != "none"]}
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(dict(res, before=vb, after=va), fh, indent=1)
    if a.after_census:
        with open(a.after_census, "w", encoding="utf-8") as fh:
            json.dump(after, fh, indent=1, sort_keys=True)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
