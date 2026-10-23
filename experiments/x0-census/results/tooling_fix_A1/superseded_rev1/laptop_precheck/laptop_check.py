"""Laptop check (x0fix track, scratch): old (pinned 8c7ecc9e) vs new x0_loops.analyse_loop on existing NON-Hearth
decodes; loops only (no canary, no attribution). Usage: python -I laptop_check.py NEWDIR OLDFILE ROOT..."""
import collections, glob, importlib.util, json, os, sys

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

NEW = load("x0_loops_new", os.path.join(sys.argv[1], "x0_loops.py"))
OLD = load("x0_loops_old", sys.argv[2])
tot = collections.Counter()
for root in sys.argv[3:]:
    for vj in sorted(glob.glob(os.path.join(root, "**", "decode", "variants.json"), recursive=True)):
        d = os.path.dirname(vj)
        variants = json.load(open(vj))
        fmt = "coff" if any(v.get("object", "").lower().endswith(".obj") for v in variants) else "elf"
        by = collections.defaultdict(dict)
        if not os.path.exists(os.path.join(d, "instructions.jsonl")):
            tot["no_instructions"] += 1
            continue
        for line in open(os.path.join(d, "instructions.jsonl")):
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
            roots = [k for k, i in insts.items() if i.get("entry")] + sorted({tuple(i["call"]) for i in insts.values() if i.get("call") and tuple(i["call"]) in insts})
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
                    keys = ("acc_lanes_emitted", "partial_results", "tags", "acc_updates_per_iter", "spills", "reloads", "carried_registers")
                    diff = [k for k in keys if a[k] != b[k]]
                    if b["escaping_slots"]:
                        tot["loops_with_escaping_slots"] += 1
                    if b["unscreened"]:
                        tot["unscreened"] += 1
                    if diff or b["escaping_slots"]:
                        tot["changed" if diff else "escaping_no_change"] += 1
                        print("%s | %s | L%d_%x | diff %s | lanes %s -> %s | esc %s | unscreened %s | %s" % (
                            os.path.relpath(d, root), vid, lp["header"][0], lp["header"][1], diff, a["acc_lanes_emitted"],
                            b["acc_lanes_emitted"], b["escaping_slots"][:4], b["unscreened"], (b.get("escape_events") or [""])[0][:150]))
print(dict(tot))
