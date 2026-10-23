"""laptop_check_r2.py NEWDIR OLDFILE ROOT... -- X0-A1 revision after the review of 2026-10-23 (x0fix track; not a
census input). The pinned (8c7ecc9e) against the revised x0_loops.analyse_loop on existing NON-Hearth decodes kept on
the laptop (no compile, no decode, no attribution, no canary): EVERY loop-record key analyse_loop returns is compared,
not a subset, and the X0-A1 keys are reported separately. Prints one line per loop whose record differs or that has
escaping slots, then the counts per changed field (split by unscreened/screened). Standard library only."""
import collections
import glob
import importlib.util
import json
import os
import sys

A1_KEYS = {"escaping_slots", "unscreened", "unscreened_reason", "escaping_partial_results",
           "acc_lanes_if_escaping_slots_were_registers", "escape_events"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


NEW = load("x0_loops_new", os.path.join(sys.argv[1], "x0_loops.py"))
OLD = load("x0_loops_old", sys.argv[2])
tot = collections.Counter()
fields = collections.Counter()
for root in sys.argv[3:]:
    for vj in sorted(glob.glob(os.path.join(root, "**", "decode", "variants.json"), recursive=True)):
        d = os.path.dirname(vj)
        with open(vj) as fh:
            variants = json.load(fh)
        fmt = "coff" if any(v.get("object", "").lower().endswith(".obj") for v in variants) else "elf"
        by = collections.defaultdict(dict)
        if not os.path.exists(os.path.join(d, "instructions.jsonl")):
            tot["no_instructions"] += 1
            continue
        with open(os.path.join(d, "instructions.jsonl")) as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("role") == "reachable":
                    by[r["variant"]][(r["section"], r["offset"])] = r
        for v in variants:
            vid = "%s:%s:%s" % (v["config"], v["table"], v["slot"])
            insts = by.get(vid, {})
            if not insts:
                continue
            for M in (NEW, OLD):
                M.ABI["current"] = fmt
            succ = {k: [tuple(s) for s in i.get("succ", [])] for k, i in insts.items()}
            roots = [k for k, i in insts.items() if i.get("entry")] + \
                sorted({tuple(i["call"]) for i in insts.values() if i.get("call") and tuple(i["call"]) in insts})
            frames = NEW.FrameInfo(insts, succ)
            seen = set()
            for rt in roots:
                loops, preds = NEW.natural_loops(rt, succ)
                for lp in loops:
                    if lp["header"] in seen:
                        continue
                    seen.add(lp["header"])
                    a = OLD.analyse_loop(lp, insts, succ, preds)
                    b = NEW.analyse_loop(lp, insts, succ, preds, frames)
                    tot["loops"] += 1
                    diff = sorted(k for k in set(a) | set(b) if k not in A1_KEYS and a.get(k) != b.get(k))
                    side = "unscreened" if b["unscreened"] else "screened"
                    for k in diff:
                        fields[(k, side)] += 1
                    if b["escaping_slots"]:
                        tot["loops_with_escaping_slots"] += 1
                    if b["unscreened"]:
                        tot["unscreened"] += 1
                        if b["acc_lanes_if_escaping_slots_were_registers"] != a["acc_lanes_emitted"]:
                            tot["ERROR_frozen_count_differs_from_pinned"] += 1
                    elif a["acc_lanes_emitted"] != b["acc_lanes_emitted"]:
                        tot["ERROR_count_changed_but_screened"] += 1
                    if diff or b["escaping_slots"]:
                        tot["changed" if diff else "escaping_no_change"] += 1
                        print("%s | %s | L%d_%x | diff %s | lanes %s -> %s | esc %s | unscreened %s | %s" % (
                            os.path.relpath(d, root), vid, lp["header"][0], lp["header"][1], diff,
                            a["acc_lanes_emitted"], b["acc_lanes_emitted"], b["escaping_slots"][:4], b["unscreened"],
                            (b.get("escape_events") or [""])[0][:150]))
print(dict(tot))
print({"%s|%s" % k: n for k, n in sorted(fields.items())})
