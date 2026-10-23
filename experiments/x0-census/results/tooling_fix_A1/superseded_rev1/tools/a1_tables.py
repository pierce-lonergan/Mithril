#!/usr/bin/env python3
"""a1_tables.py RESULTS_DIR -- Amendment X0-A1 evidence tool (x0fix track, 2026-10-23; not a census input). Writes the
before/after tables of P3(c) from the JSON evidence in RESULTS_DIR (results/tooling_fix_A1):
  run1/p3c_before_after.tsv   census run 1: every loop record whose X0-A1 reading differs from census.json's, both
                              directions (flags removed, flags added, lanes changed, newly unscreened), with the cause
                              of each removed flag: (a) escape events, (b) string stores in the loop body;
  run1/p3c_summary.tsv        census run 1: per configuration and build, variants, loops, P3(c)-flagged loops and
                              variants before and after, unscreened loops after;
  repro/p3c_before_after.tsv  the NON-Hearth reproduction a1_escape.c (pinned vs fixed script on the same decodes);
  repro/p3c_summary.tsv       the same per configuration and build.
Standard library only."""
import json
import os
import sys

COLS = ["config", "build", "unit", "variant", "loop", "source_loop", "bound_rule", "bound_used", "acc_lanes_before",
        "acc_lanes_after", "p3c_flag_before", "p3c_flag_after", "unscreened_after", "escaping_partial_results",
        "cause_a_escape_events", "cause_b_string_stores_in_loop_body"]


def cell(x):
    if isinstance(x, (list, dict)):
        x = json.dumps(x, separators=(",", ":"))
    return str(x).replace("\t", " ").replace("\n", " ")


def b_text(cb):
    if not isinstance(cb, dict):
        return ""
    if "error" in cb:
        return "error: %s" % cb["error"]
    ss = cb.get("string_stores_in_loop_body") or []
    if not ss:
        return "none in the loop body"
    return "; ".join("%s %s, rdi set by '%s'%s, count set by '%s' (%s), stack-pointer value of rdi %s" % (
        s["at"], s["disasm"], s.get("rdi_set_by"),
        " (stored stack address reloaded)" if (s.get("rdi_set_by") or "").startswith("mov rdi, qword ptr [rsp") else "",
        s.get("count_set_by"), "immediate" if s.get("count_is_immediate") else "not an immediate",
        s.get("rdi_from_entry_rsp") if s.get("rdi_is_stack_pointer") else
        "not tracked by FrameInfo (the address reaches rdi through memory or a vector register)")
        for s in ss)


def events_text(evs):
    """The distinct escape events behind a loop's escaping slots (each line of a loop record reads 'KEY <- event')."""
    out = []
    for w in evs or []:
        t = w.split(" <- ", 1)[-1]
        if t not in out:
            out.append(t)
    return "; ".join(out)


def table(cmp, info_by_key=None):
    rows = []
    removed = {(e["config"], e["build"], e["unit"], e["variant"], e["loop"]): e for e in cmp["flags_removed"]}
    added = {(e["config"], e["build"], e["unit"], e["variant"], e["loop"]): e for e in cmp["flags_added"]}
    for c in cmp["loop_changes"]:
        if "loop" not in c:
            rows.append({"config": c["config"], "build": c["build"], "unit": c["unit"], "variant": c["variant"],
                         "loop": c.get("change")})
            continue
        k = (c["config"], c["build"], c["unit"], c["variant"], c["loop"])
        d = c.get("diff") or {}
        e = removed.get(k)
        inf = (info_by_key or {}).get(k, {})
        lanes = d.get("acc_lanes_emitted")
        rows.append({
            "config": c["config"], "build": c["build"], "unit": c["unit"], "variant": c["variant"], "loop": c["loop"],
            "source_loop": (e or {}).get("source_loop") or inf.get("source_loop"),
            "bound_rule": inf.get("bound_rule", ""), "bound_used": (e or {}).get("bound_used", inf.get("bound_used")),
            "acc_lanes_before": lanes[0] if lanes else c.get("acc_lanes_if_escaping_slots_were_registers"),
            "acc_lanes_after": lanes[1] if lanes else "",
            "p3c_flag_before": k in removed or (k not in added and False),
            "p3c_flag_after": k in added,
            "unscreened_after": c.get("unscreened_after"),
            "escaping_partial_results": c.get("escaping_partial_results"),
            "cause_a_escape_events": events_text((e or {}).get("cause_a_escape_events") or inf.get("escape_events")),
            "cause_b_string_stores_in_loop_body": b_text((e or {}).get("cause_b")) if e else "not computed (no flag removed)"})
    for k, e in added.items():
        rows.append({"config": k[0], "build": k[1], "unit": k[2], "variant": k[3], "loop": k[4],
                     "p3c_flag_before": False, "p3c_flag_after": True, "acc_lanes_after": e["after"].get("acc_lanes_emitted")})
    return rows


def write_tsv(path, rows, cols):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(cell(r.get(c, "")) for c in cols) + "\n")


def summary(other):
    cols = ["config", "build", "variants", "loops", "flagged_loops_before", "flagged_loops_after",
            "flagged_variants_before", "flagged_variants_after", "unscreened_loops_after"]
    rows = []
    for k, v in sorted(other["p3c"].items()):
        cfg, b = k.split("|")
        rows.append(dict(v, config=cfg, build=b))
    return rows, cols


def main():
    res = sys.argv[1]
    r1 = json.load(open(os.path.join(res, "run1", "run1_compare_new_vs_census.json"), encoding="utf-8"))
    info = {}
    p = os.path.join(res, "run1", "run1_changed_loops.json")
    if os.path.exists(p):
        for x in json.load(open(p, encoding="utf-8")):
            info[(x["config"], x["build"], "all", x["variant"], x["id"])] = x
    write_tsv(os.path.join(res, "run1", "p3c_before_after.tsv"), table(r1, info), COLS)
    rows, cols = summary(json.load(open(os.path.join(res, "run1", "run1_otherfields.json"), encoding="utf-8")))
    write_tsv(os.path.join(res, "run1", "p3c_summary.tsv"), rows, cols)
    rp = json.load(open(os.path.join(res, "repro", "A1final_compare.json"), encoding="utf-8"))
    write_tsv(os.path.join(res, "repro", "p3c_before_after.tsv"), table(rp), COLS)
    rows, cols = summary(json.load(open(os.path.join(res, "repro", "A1final_otherfields.json"), encoding="utf-8")))
    write_tsv(os.path.join(res, "repro", "p3c_summary.tsv"), rows, cols)
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
