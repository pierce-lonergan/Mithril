#!/usr/bin/env python3
"""a1_events.py SCRIPTS_DIR DECODE_DIR MANIFEST VARIANT_ID SEC:OFF -- Amendment X0-A1 evidence tool (x0fix track,
2026-10-23; not a census input). Read only. For the function containing the instruction SEC:OFF (hex offset) of variant
VARIANT_ID ("C:k_avx512:matmul[Q8]"), prints every FrameInfo event of the fixed x0_loops.py (kind, address, the
instruction's disassembly, the pointer register and its value as offsets from the entry RSP) and every instruction that
materialises a stack address (LEA/MOV from RSP or RBP), as JSON lines. Revision after the review of 2026-10-23: SEC:OFF
is the loop header, and each event says whether the header is reachable from it ("reaches_header"; with the revised
x0_loops.py only such events make the loop's slots escape). Standard library only."""
import json
import os
import sys


def main():
    scripts, dec, man, vid, where = sys.argv[1:6]
    sys.path.insert(0, scripts)
    import x0_loops as L
    insts = {}
    with open(os.path.join(dec, "instructions.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("role") == "reachable" and r.get("variant") == vid:
                insts[(r["section"], r["offset"])] = r
    m = json.load(open(man, encoding="utf-8"))
    L.ABI["current"] = "coff" if any(o.get("format", "").startswith("coff") for o in m.get("objects", [])) else "elf"
    sec, off = where.split(":")
    at = (int(sec), int(off, 16))
    succ = {k: [tuple(s) for s in i.get("succ", [])] for k, i in insts.items()}
    fr = L.FrameInfo(insts, succ)
    fam = L._family(insts[at])
    fi = fr.info(fam)
    print(json.dumps({"variant": vid, "function": fam, "instructions": len(fr.fams[fam]), "events": len(fi["events"]),
                      "rsp_at": list(fr.to_e(fi["state_in"].get(at, (None, {}))[0]) or [])}))
    reach = fr.reaching(fi, at) if hasattr(fr, "reaching") and "preds" in fi else None
    for e in fi["events"]:
        n = tuple(e["at"])
        print(json.dumps({"event": e["kind"], "at": "%x:%x" % n, "disasm": insts[n].get("disasm"), "via": e["via"],
                          "value_from_entry_rsp": fr.to_e(e["value"]), "width": e["width"], "why": e["why"],
                          "reaches_header": (n in reach) if reach is not None else None}))
    for n in sorted(fr.fams[fam]):
        ins = insts[n]
        d = (ins.get("disasm") or "")
        if (ins.get("iclass") == "LEA" and ("[rsp" in d or "[rbp" in d)) or \
                (ins.get("iclass") == "MOV" and (d.endswith(", rsp") or d.endswith(", rbp"))):
            st = fi["state_in"].get(n, (None, {}))
            print(json.dumps({"materialises": "%x:%x" % n, "disasm": d, "rsp_from_entry_rsp": fr.to_e(st[0])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
