"""x0fix scratch: summary fields of the run-1 loops whose X0-A1 reading changed (read only)."""
import json
import os

OUT = r"D:\mithril\x0fixA1\run1_reloop"
cmp = json.load(open(os.path.join(OUT, "run1_compare_new_vs_census.json"), encoding="utf-8"))
rows = []
for c in cmp["loop_changes"]:
    step = "loops_%s_%s" % (c["build"], c["unit"])
    new = json.load(open(os.path.join(OUT, "new", c["config"], step, "loops.json"), encoding="utf-8"))
    rec = next(r for r in new if "%s:%s" % (r["table"], r["slot"]) == c["variant"])
    lp = next(x for x in rec["loops"] if x["id"] == c["loop"])
    rows.append({k: lp.get(k) for k in ("id", "source_loop", "bound_rule", "bound_used", "acc_lanes_source",
                                          "acc_lanes_emitted", "acc_lanes_if_escaping_slots_were_registers", "tags",
                                          "unscreened", "escaping_partial_results")}
                | {"config": c["config"], "build": c["build"], "variant": c["variant"], "flagged_after": c["loop"] in rec["p3"]["c"],
                   "escape_events": (lp.get("escape_events") or [])[:3]})
json.dump(rows, open(os.path.join(OUT, "run1_changed_loops.json"), "w", encoding="utf-8"), indent=1)
for r in rows:
    print(r["config"], r["build"], r["variant"], r["id"], r["source_loop"], r["bound_rule"], r["bound_used"], r["acc_lanes_if_escaping_slots_were_registers"], "->", r["acc_lanes_emitted"], r["escape_events"][:1])
