"""summarize_regression.py ROOT OUT.json -- compact record of runbook step 72's outputs (NON-Hearth regression inputs):
per configuration and decode the summary counts, and per variant the gap causes and details, jump tables, closure,
no-return inferences, external calls, FP trust dependencies, orphan bytes, instruction count and whether the lifo
and fifo decodes are byte-identical; for smoke_dispatch also the d1 canary results. Standard library only."""
import json
import os
import sys

root, out = sys.argv[1], sys.argv[2]
res = {"note": "runbook step 72, x0prep reviser 2026-10-16; inputs smoke_dispatch.c, rv_tricky.c, rv_tricky2.c "
               "(NOT Hearth) under the A (A-ninja lines), B-cmake, C and D command lines of quant_avx512.c and quant.c",
       "configs": {}}
for cfg in sorted(os.listdir(root)):
    p = os.path.join(root, cfg)
    if not os.path.isdir(p):
        continue
    for name in sorted(os.listdir(p)):
        d = os.path.join(p, name)
        try:
            s = json.load(open(os.path.join(d, "lifo", "summary.json")))
            vb = open(os.path.join(d, "lifo", "variants.json"), "rb").read()
            fb = open(os.path.join(d, "fifo", "variants.json"), "rb").read()
        except OSError:
            continue
        rec = {k: s.get(k) for k in ("n_variants", "n_resolved", "gap_counts", "tooling_gaps",
                                     "crossdecoder_disagreements", "u_iforms", "u_iclasses", "anomalies", "xed_version")}
        rec["lifo_fifo_identical"] = vb == fb
        rec["variants"] = []
        for v in json.loads(vb):
            lb = v.get("lift_blockers") or {}
            rec["variants"].append({
                "slot": "%s:%s" % (v.get("table"), v.get("slot")), "function": v.get("source_function"),
                "symbol": v.get("symbol"), "slot_name_check": v.get("slot_name_check"),
                "n_instructions": v.get("n_instructions"),
                "gaps": [[g.get("cause"), (g.get("detail") or "")[:160]] for g in (v.get("coverage") or {}).get("gaps", [])],
                "closure": [[c.get("symbol"), c.get("kind")] for c in v.get("closure") or []],
                "jump_tables": [[t.get("section_name"), t.get("start"), t.get("n_entries"), t.get("entry_type"),
                                 t.get("bound"), t.get("byte_table")] for t in v.get("jump_tables") or []],
                "external_calls": lb.get("external_calls"), "fp_trust_deps": lb.get("fp_trust_deps"),
                "tail_calls": lb.get("tail_calls"), "noreturn_inferred": lb.get("noreturn_inferred"),
                "indirect_branches": lb.get("indirect_branches"),
                "orphan_bytes": (v.get("unreachable") or {}).get("orphan_bytes"),
                "referenced_non_instruction": (v.get("unreachable") or {}).get("referenced_non_instruction"),
                "crossdecoder_disagreements": v.get("crossdecoder_disagreements")})
        if os.path.exists(os.path.join(d, "loops.json")):
            rec["d1"] = {"%s:%s" % (r["table"], r["slot"]): r["p3"].get("d1") for r in json.load(open(os.path.join(d, "loops.json")))
                         if r.get("key_is_canary")}
        res["configs"].setdefault(cfg, {})[name] = rec
json.dump(res, open(out, "w"), indent=1, sort_keys=True)
print("written", out)
