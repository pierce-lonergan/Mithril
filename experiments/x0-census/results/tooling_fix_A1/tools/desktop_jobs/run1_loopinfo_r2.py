"""x0fix track, revision after the review of 2026-10-23 (r2): summary fields of the run-1 loop records whose X0-A1 reading
differs from census run 1's loops.json, or that are listed unscreened (read only). Usage: run1_loopinfo_r2.py R2_DIR"""
import json
import os
import sys

B = sys.argv[1]
with open(os.path.join(B, "cmp", "run1_compare_new_vs_census.json"), encoding="utf-8") as fh:
    cmp = json.load(fh)
rows = []
for c in cmp["loop_changes"]:
    if "loop" not in c:
        continue
    step = "loops_%s_%s" % (c["build"], c["unit"])
    with open(os.path.join(B, "run1_reloop", "new", c["config"], step, "loops.json"), encoding="utf-8") as fh:
        new = json.load(fh)
    rec = next(r for r in new if "%s:%s" % (r["table"], r["slot"]) == c["variant"])
    lp = next(x for x in rec["loops"] if x["id"] == c["loop"])
    row = {k: lp.get(k) for k in ("id", "header", "source_loop", "bound_rule", "bound_used", "acc_lanes_source",
                                  "acc_lanes_emitted", "acc_lanes_if_escaping_slots_were_registers", "tags", "fp_free",
                                  "u_acc", "unscreened", "escaping_slots", "escaping_partial_results")}
    row.update({"config": c["config"], "build": c["build"], "variant": c["variant"],
                "flagged_after": c["loop"] in rec["p3"]["c"],
                "flagged_frozen_reading": c["loop"] in (rec.get("p3c_frozen_reading") or []),
                "escape_events": (lp.get("escape_events") or [])[:3]})
    rows.append(row)
with open(os.path.join(B, "cmp", "run1_changed_loops.json"), "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)
for r in rows:
    print(r["config"], r["build"], r["variant"], r["id"], r["source_loop"], r["bound_used"],
          r["acc_lanes_if_escaping_slots_were_registers"], "->", r["acc_lanes_emitted"], r["escape_events"][:1])
