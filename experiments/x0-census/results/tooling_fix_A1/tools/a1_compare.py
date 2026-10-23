#!/usr/bin/env python3
"""a1_compare.py SCRIPTS_DIR OUTDIR CFG... -o RESULT.json -- Amendment X0-A1 evidence tool (x0fix track, 2026-10-23; not a
census input).

For every configuration CFG re-run by a1_reloop.py into OUTDIR, compares the run's own loops.json (BEFORE: the frozen
x0_loops.py of the census run) with the re-run (AFTER: the fixed x0_loops.py from SCRIPTS_DIR), variant by variant and
loop by loop, and lists EVERY change in both directions:
  * P3(c) flags (p3.c) per (config, build, unit, table, slot, loop id): removed or added;
  * per loop: acc_lanes_emitted, partial_results, bound_used, tags, unscreened, escaping_slots;
  * for each removed flag, the cause, from the AFTER record and the decodes (read only):
      (a) the escape events (FrameInfo) that make the counted slots escaping, i.e. the frozen record's "constant-
          offset, non-escaping" condition the frozen script did not test;
      (b) whether a string store (REP STOS*/MOVS*) inside the loop body writes through a stack pointer, where it
          points, and whether its count register is set from an immediate (a known extent) or not.
Paths recorded by WSL steps (/mnt/d/...) are read as D:/... when this runs on Windows. Standard library only.
"""
import argparse
import collections
import json
import os
import re
import sys


def native(p):
    if os.name == "nt" and p.startswith("/mnt/") and len(p) > 6:
        return p[5].upper() + ":" + p[6:]
    return p


def load(p):
    with open(native(p), encoding="utf-8") as f:
        return json.load(f)


def key(r):
    return "%s:%s" % (r["table"], r["slot"])


def loop_view(lp):
    return {k: lp.get(k) for k in ("acc_lanes_emitted", "partial_results", "bound_used", "bound_rule", "tags",
                                    "source_loop", "unscreened", "escaping_slots")}


def cause_b(L, decode_dir, manifest, variant_id, header, slots):
    """String stores in the loop body: where they write and whether their count is an immediate."""
    insts = {}
    with open(os.path.join(native(decode_dir), "instructions.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("role") == "reachable" and r.get("variant") == variant_id:
                insts[(r["section"], r["offset"])] = r
    man = load(manifest)
    L.ABI["current"] = "coff" if any(o.get("format", "").startswith("coff") for o in man.get("objects", [])) else "elf"
    succ = {k: [tuple(s) for s in i.get("succ", [])] for k, i in insts.items()}
    preds = collections.defaultdict(list)
    for n, ss in succ.items():
        for s in ss:
            preds[s].append(n)
    roots = [k for k, i in insts.items() if i.get("entry")] + \
        sorted({tuple(i["call"]) for i in insts.values() if i.get("call") and tuple(i["call"]) in insts})
    body = None
    for rt in roots:
        for lp in L.natural_loops(rt, succ)[0]:
            if list(lp["header"]) == list(header):
                body = lp["body"]
                break
        if body:
            break
    if body is None:
        return {"error": "loop header %s not found" % (header,)}
    fr = L.FrameInfo(insts, succ)
    fi = fr.info(L._family(insts[tuple(header)]))
    rsp = fi["state_in"].get(tuple(header), (None, {}))[0]
    slot_e = {}
    for s in slots:
        _, base, d = s.split(":")
        if base == "RSP":
            slot_e[s] = fr.to_e(fr.add(rsp, int(d)))
    out = []
    for n in sorted(body):
        ins = insts[n]
        if not L.STRING_RE.match(ins.get("iclass", "")):
            continue
        st = fi["state_in"].get(n, (None, {}))
        rdi = st[1].get("RDI", "not a stack pointer") if "RDI" in st[1] else "not a stack pointer"
        rdi_e = fr.to_e(rdi) if rdi != "not a stack pointer" else None
        # the count and destination registers: the nearest earlier instruction along single predecessors (and, at a
        # join, along the lowest-addressed predecessor; reported as such) that writes RCX/ECX, or RDI
        def definer(reg):
            cur, seen, path_joins = n, 0, 0
            while seen < 256:
                ps = sorted(preds.get(cur, []))
                if not ps:
                    return None, path_joins
                if len(ps) > 1:
                    path_joins += 1
                cur = ps[0]
                seen += 1
                if reg in L.explicit_defs(insts[cur]):
                    return insts[cur].get("disasm"), path_joins
            return None, path_joins
        cnt, cnt_joins = definer("RCX")
        rdi_def, rdi_joins = definer("RDI")
        imm = bool(cnt and re.match(r"^mov\s+(e|r)cx,\s*(0x[0-9a-f]+|\d+)$", cnt))
        covered = sorted(s for s, e in slot_e.items() if rdi_e and e and e[0] >= rdi_e[0])
        out.append({"at": "%x:%x" % n, "disasm": ins.get("disasm"), "rdi_from_entry_rsp": list(rdi_e) if rdi_e else None,
                    "rdi_is_stack_pointer": rdi != "not a stack pointer", "rdi_set_by": rdi_def,
                    "rdi_set_by_joins_crossed": rdi_joins, "count_set_by": cnt, "count_set_by_joins_crossed": cnt_joins,
                    "count_is_immediate": imm,
                    "counted_slots_at_or_above_rdi": covered,
                    "counted_slots_from_entry_rsp": {s: list(e) if e else None for s, e in slot_e.items()}})
    return {"string_stores_in_loop_body": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scripts")
    ap.add_argument("outdir")
    ap.add_argument("configs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--before-dir", help="BEFORE from another a1_reloop.py OUTDIR (e.g. the pinned script re-run) instead "
                                         "of the run's own loops.json")
    a = ap.parse_args()
    sys.path.insert(0, a.scripts)
    import x0_loops as L  # the fixed script, for FrameInfo in the cause (b) diagnostic
    res = {"flags_removed": [], "flags_added": [], "loop_changes": [], "units": [], "summary": {}}
    cnt = collections.Counter()
    for cfg in a.configs:
        rl = load(os.path.join(a.outdir, cfg, "reloop.json"))
        for st in rl["steps"]:
            argv = st["argv"]
            decode_dir, manifest = argv[3], argv[argv.index("--manifest") + 1]
            unit = os.path.basename(os.path.dirname(native(decode_dir).rstrip("/\\")))
            bdir = os.path.basename(os.path.dirname(os.path.dirname(native(decode_dir).rstrip("/\\"))))
            bpath = os.path.join(a.before_dir, cfg, st["step"], "loops.json") if a.before_dir else st["run_loops_json"]
            before = {key(r): r for r in load(bpath)}
            after = {key(r): r for r in load(os.path.join(a.outdir, cfg, st["step"], "loops.json"))}
            res["units"].append({"config": cfg, "build": bdir, "unit": unit, "step": st["step"], "rc": st["rc"],
                                 "recorded_rc": st["recorded_rc"], "variants": len(after),
                                 "run_loops_sha256": st["run_loops_sha256"], "new_loops_sha256": st["new_loops_sha256"]})
            for k in sorted(set(before) | set(after)):
                b, f = before.get(k), after.get(k)
                if b is None or f is None:
                    res["loop_changes"].append({"config": cfg, "build": bdir, "unit": unit, "variant": k,
                                                "change": "variant present on one side only"})
                    continue
                bl = {lp["id"]: lp for lp in b.get("loops", [])}
                fl = {lp["id"]: lp for lp in f.get("loops", [])}
                cnt["variants"] += 1
                cnt["loops"] += len(fl)
                cnt["unscreened_after"] += sum(1 for lp in fl.values() if lp.get("unscreened"))
                cnt["loops_with_escaping_slots_after"] += sum(1 for lp in fl.values() if lp.get("escaping_slots"))
                if set(bl) != set(fl):
                    res["loop_changes"].append({"config": cfg, "build": bdir, "unit": unit, "variant": k,
                                                "change": "loop ids differ", "before": sorted(bl), "after": sorted(fl)})
                for lid in sorted(set(bl) & set(fl)):
                    vb, vf = loop_view(bl[lid]), loop_view(fl[lid])
                    vb["unscreened"], vb["escaping_slots"] = None, None     # fields new in X0-A1
                    diff = {x: [vb[x], vf[x]] for x in vb if x not in ("unscreened", "escaping_slots") and vb[x] != vf[x]}
                    if diff or vf["unscreened"]:
                        res["loop_changes"].append({"config": cfg, "build": bdir, "unit": unit, "variant": k, "loop": lid,
                                                    "diff": diff, "unscreened_after": vf["unscreened"],
                                                    "escaping_slots_after": vf["escaping_slots"],
                                                    "escaping_partial_results": fl[lid].get("escaping_partial_results"),
                                                    "acc_lanes_if_escaping_slots_were_registers":
                                                        fl[lid].get("acc_lanes_if_escaping_slots_were_registers")})
                        cnt["loops_changed"] += 1 if diff else 0
                cb, cf = set(b["p3"].get("c") or []), set(f["p3"].get("c") or [])
                for lid in sorted(cb - cf):
                    lb, lf = bl.get(lid, {}), fl.get(lid, {})
                    counted = sorted({x for g in (lb.get("partial_results") or []) for x in g})
                    entry = {"config": cfg, "build": bdir, "unit": unit, "variant": k, "loop": lid,
                             "source_loop": lb.get("source_loop"), "bound_used": lb.get("bound_used"),
                             "before": {"acc_lanes_emitted": lb.get("acc_lanes_emitted"),
                                        "partial_results": lb.get("partial_results")},
                             "after": {"acc_lanes_emitted": lf.get("acc_lanes_emitted"),
                                       "partial_results": lf.get("partial_results"),
                                       "unscreened": lf.get("unscreened"), "escaping_slots": lf.get("escaping_slots"),
                                       "escaping_partial_results": lf.get("escaping_partial_results")},
                             "cause_a_escape_events": lf.get("escape_events"),
                             "cause_a": bool(set(counted) & set(lf.get("escaping_slots") or [])),
                             "cause_b": cause_b(L, decode_dir, manifest, "%s:%s" % (f["config"], k), lb.get("header"),
                                                counted)}
                    res["flags_removed"].append(entry)
                for lid in sorted(cf - cb):
                    res["flags_added"].append({"config": cfg, "build": bdir, "unit": unit, "variant": k, "loop": lid,
                                               "after": loop_view(fl.get(lid, {}))})
    cnt["flags_removed"] = len(res["flags_removed"])
    cnt["flags_added"] = len(res["flags_added"])
    cnt["units"] = len(res["units"])
    cnt["units_rc_differs"] = sum(1 for u in res["units"] if u["rc"] != u["recorded_rc"])
    res["summary"] = dict(cnt)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print(json.dumps(res["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
