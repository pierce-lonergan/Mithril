#!/usr/bin/env python3
"""check_smoke.py EXPECT.json ROOT -- compare the decode outputs of runbook step 72 with tricky_expect.json.

ROOT/<config>/<decode>/{lifo,fifo}/variants.json and summary.json, for every configuration and decode named in
EXPECT.json (decodes: smoke_dispatch, rv_tricky, rv_tricky2; NON-Hearth sources only). Also checked:
  * order independence: lifo/variants.json and fifo/variants.json (x0_decode.py --worklist-order) are
    byte-identical;
  * every slot resolved (summary n_resolved == expected variant count);
  * for smoke_dispatch, ROOT/<config>/smoke_dispatch/loops.json has d1 == "pass" for both canary variants.
Prints one line per deviation and exits 1 if there is any. Standard library only.
"""
import json
import os
import sys


def merged_rules(rules, cfg, defaults):
    out = dict(defaults)
    for r in rules:
        cs = r.get("configs", "*")
        if cs == "*" or cfg in cs:
            out.update({k: v for k, v in r.items() if k != "configs"})
    return out


def check_variant(v, e):
    bad = []
    gaps = (v.get("coverage") or {}).get("gaps") or []
    causes = {g.get("cause") for g in gaps}
    details = " | ".join(str(g.get("detail")) for g in gaps)
    lb = v.get("lift_blockers") or {}
    clos = {c.get("symbol") for c in v.get("closure") or []}
    tables = v.get("jump_tables") or []
    if e.get("no_gaps") and gaps:
        bad.append("expected no gaps, got %s" % sorted((g["cause"], g.get("detail")) for g in gaps))
    for c in e.get("require_causes", []):
        if c not in causes:
            bad.append("missing gap cause %s (have %s)" % (c, sorted(causes)))
    for c in e.get("forbid_causes", []):
        if c in causes and not e.get("no_gaps"):
            bad.append("forbidden gap cause %s: %s" % (c, [g.get("detail") for g in gaps if g.get("cause") == c]))
    for s in e.get("require_detail", []):
        if s not in details:
            bad.append("no gap detail contains %r" % s)
    for n in e.get("fp_trust_deps_include", []):
        if n not in (lb.get("fp_trust_deps") or []):
            bad.append("fp_trust_deps lacks %s (have %s)" % (n, lb.get("fp_trust_deps")))
    if "fp_trust_deps_subset" in e and not set(lb.get("fp_trust_deps") or []) <= set(e["fp_trust_deps_subset"]):
        bad.append("fp_trust_deps %s not within %s" % (lb.get("fp_trust_deps"), e["fp_trust_deps_subset"]))
    for n in e.get("external_calls_exclude", []):
        if n in (lb.get("external_calls") or []) or n in (lb.get("fp_trust_deps") or []):
            bad.append("%s listed as an external call" % n)
    for n in e.get("noreturn_inferred_include", []):
        if n not in (lb.get("noreturn_inferred") or []):
            bad.append("noreturn_inferred lacks %s (have %s)" % (n, lb.get("noreturn_inferred")))
    for n in e.get("closure_include", []):
        if n not in clos:
            bad.append("closure lacks %s (have %s)" % (n, sorted(clos)))
    if "jump_tables" in e and len(tables) != e["jump_tables"]:
        bad.append("jump tables %d, expected %d" % (len(tables), e["jump_tables"]))
    if "table_entries" in e and sorted(t.get("n_entries") for t in tables) != sorted(e["table_entries"]):
        bad.append("table entries %s, expected %s" % (sorted(t.get("n_entries") for t in tables), e["table_entries"]))
    if e.get("byte_table") and not any(t.get("byte_table") for t in tables):
        bad.append("no byte index table recognised")
    if "orphan_bytes" in e and (v.get("unreachable") or {}).get("orphan_bytes") != e["orphan_bytes"]:
        bad.append("orphan bytes %s, expected %s (%s)" % ((v.get("unreachable") or {}).get("orphan_bytes"),
                                                         e["orphan_bytes"], (v.get("unreachable") or {}).get("orphan_ranges")))
    if (v.get("crossdecoder_disagreements") or 0) > e.get("xdis_max", 0):
        bad.append("%s cross-decoder disagreements (max %s)" % (v.get("crossdecoder_disagreements"), e.get("xdis_max", 0)))
    return bad


def main():
    exp = json.load(open(sys.argv[1]))
    root = sys.argv[2]
    devs, nvar = [], 0
    for cfg in exp["configs"]:
        for name, spec in exp["decodes"].items():
            base = os.path.join(root, cfg, name)
            try:
                lifo_b = open(os.path.join(base, "lifo", "variants.json"), "rb").read()
                fifo_b = open(os.path.join(base, "fifo", "variants.json"), "rb").read()
                summ = json.load(open(os.path.join(base, "lifo", "summary.json")))
            except OSError as e:
                devs.append("%s %s: missing output (%s)" % (cfg, name, e))
                continue
            if lifo_b != fifo_b:
                devs.append("%s %s: variants.json differs between --worklist-order lifo and fifo" % (cfg, name))
            vs = json.loads(lifo_b)
            if len(vs) != spec["variants"] or summ.get("n_resolved") != spec["variants"]:
                devs.append("%s %s: %d variants, %s resolved, expected %d" % (cfg, name, len(vs), summ.get("n_resolved"),
                                                                            spec["variants"]))
            for v in vs:
                nvar += 1
                key = v.get("source_function") if name != "smoke_dispatch" else "smoke_dispatch:*"
                rules = exp["expect"].get(key)
                if rules is None:
                    devs.append("%s %s %s: no expectation" % (cfg, name, key))
                    continue
                for b in check_variant(v, merged_rules(rules, cfg, exp["defaults"])):
                    devs.append("%s %s %s:%s (%s): %s" % (cfg, name, v.get("table"), v.get("slot"),
                                                          v.get("source_function"), b))
            if name == "smoke_dispatch":
                try:
                    loops = json.load(open(os.path.join(base, "loops.json")))
                except OSError as e:
                    devs.append("%s %s: loops.json missing (%s)" % (cfg, name, e))
                    continue
                d1 = {"%s:%s" % (r["table"], r["slot"]): r["p3"].get("d1") for r in loops}
                for k in ("sd_table:act_quantize", "sd_table_global:act_quantize"):
                    if d1.get(k) != "pass":
                        devs.append("%s %s: d1 canary %s = %r" % (cfg, name, k, d1.get(k)))
    for d in devs:
        print("DEVIATION:", d)
    print("check_smoke: %d variants checked, %d deviations" % (nvar, len(devs)))
    return 1 if devs else 0


if __name__ == "__main__":
    sys.exit(main())
