"""loops_debug.py SCRIPTS_DIR DECODE_DIR VARIANT_ID LOOP_ID [--all] -- print a loop of x0_loops.py's analysis with the
accumulation instructions (acc_info), the carried locations, the cycle members and their back-edge provenance.
NON-Hearth smoke decodes only."""
import collections
import inspect
import json
import os
import sys

scripts, dec, vid, lid = sys.argv[1:5]
sys.path.insert(0, scripts)
import x0_loops as X  # noqa: E402

src = inspect.getsource(X._analyse_loop)
src = src.replace('return {"header": list(hdr),',
                  'return {"_acc_info": acc_info, "_dep_out": dep_out, "_av_out": av_out, "_carried": carried, "_eq_out": eq_out, "header": list(hdr),')
ns = dict(vars(X))
exec(src, ns)
X._analyse_loop = ns["_analyse_loop"]

insts = {}
with open(os.path.join(dec, "instructions.jsonl")) as fh:
    for line in fh:
        r = json.loads(line)
        if r.get("role") == "reachable" and r["variant"] == vid:
            insts[(r["section"], r["offset"])] = r
man_fmt = "coff" if vid.split(":")[0] in ("A", "A-ninja", "B-cmake", "B-proxy", "P.A", "P.A-ninja", "P.B-cmake") else "elf"
X.ABI["current"] = man_fmt
succ = {k: [tuple(s) for s in i.get("succ", [])] for k, i in insts.items()}
roots = [k for k, i in insts.items() if i.get("entry")] + sorted({tuple(i["call"]) for i in insts.values() if i.get("call") and tuple(i["call"]) in insts})
seen = set()
for root in roots:
    loops, preds = X.natural_loops(root, succ)
    for lp in loops:
        if lp["header"] in seen:
            continue
        seen.add(lp["header"])
        hid = "L%d_%x" % lp["header"]
        if hid != lid and "--all" not in sys.argv:
            continue
        info = X.analyse_loop(lp, insts, succ, preds)
        acc = info["_acc_info"]
        print("== %s %s carried=%s acc_lanes_emitted=%s cycles=%s" % (vid, hid, sorted(info["_carried"]), info["acc_lanes_emitted"],
                                                                     json.dumps(info["partial_result_cycles"])))
        if "--all" in sys.argv:
            continue
        latches = sorted(tuple(t) for t in lp["latches"])
        for tl in latches:
            dep = info["_dep_out"].get(tl) or {}
            av = info["_av_out"].get(tl) or {}
            for r in sorted(info["_carried"]):
                print("  latch %s: %s  dep=%s  prov=%s" % (tl, r, sorted(dep.get(r, [])), sorted("%x" % p[1] for p in av.get(r, []))))
        for n in sorted(lp["body"]):
            i = insts[n]
            mark = "ACC%-2d" % acc[n] if n in acc else "     "
            print("  %s %5x  %-14s %s" % (mark, n[1], i.get("iclass"), i.get("disasm")))
