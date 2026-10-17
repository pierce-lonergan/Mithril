#!/usr/bin/env python3
"""norm_check.py -- validate class/objdump_norm.csv on NON-Hearth objects (zoo, smoke) before freeze.

  python -I norm_check.py --xed XED --objdump LLVM_OBJDUMP [--norm ../../class/objdump_norm.csv]
                          [--fp-class ../../class/fp_class.csv] -o OUT.json OBJ [OBJ ...]

Linear-sweeps every code section with XED (`-64 -cet -ir`) and with llvm-objdump, and for every offset where
both start an instruction compares XED's iclass with the normalised objdump mnemonic. Reports instruction-
boundary disagreements, iclass disagreements (with whether either side is FP-sensitive per fp_class.csv) and
the distinct (objdump mnemonic, XED iclass) pairs seen. Exit 1 if any iclass disagreement remains.
"""
import argparse
import collections
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0obj  # noqa: E402
import x0_norm  # noqa: E402
from x0_decode import xed_sweep  # noqa: E402

LINE_RE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}[ \t])+)\s*(.*)$")


def objdump_sections(objdump, path):
    p2 = subprocess.run([objdump, "-d", "--no-print-imm-hex", "--x86-asm-syntax=intel", path],
                        capture_output=True, text=True)
    secs, cur = [], None
    for line in p2.stdout.splitlines():
        if line.startswith("Disassembly of section "):
            cur = {"name": line[len("Disassembly of section "):].rstrip(":"), "insts": {}}
            secs.append(cur)
            continue
        m = LINE_RE.match(line)
        if m and cur is not None:
            cur["insts"][int(m.group(1), 16)] = (len(m.group(2).split()), m.group(3).strip())
    return secs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xed", required=True)
    ap.add_argument("--objdump", required=True)
    ap.add_argument("--norm", default=os.path.join(HERE, "..", "..", "class", "objdump_norm.csv"))
    ap.add_argument("--fp-class", default=os.path.join(HERE, "..", "..", "class", "fp_class.csv"))
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("objects", nargs="+")
    a = ap.parse_args()
    norm = x0_norm.Normalizer(a.norm)
    with open(a.fp_class, encoding="utf-8", newline="") as f:
        fps = {r["iclass"]: r["fp_sensitive"] == "yes" for r in csv.DictReader(f)}
    pairs = collections.Counter()
    bad, bounds, total, xerr = [], [], 0, 0
    tmp = tempfile.mkdtemp()
    for path in a.objects:
        obj = x0obj.parse_object(path)
        code = [s for s in obj["sections"] if s and s["is_code"] and s["size"] > 0]
        ods = objdump_sections(a.objdump, path)
        if len(ods) != len(code):
            raise SystemExit("%s: objdump shows %d code sections, x0obj %d" % (path, len(ods), len(code)))
        for sec, od in zip(code, ods):
            od["insts"] = norm.merge_lines(od["insts"])
            fn = os.path.join(tmp, "sec.bin")
            with open(fn, "wb") as f:
                f.write(obj["data"][sec["offset"]:sec["offset"] + sec["size"]])
            insts, errors, _ = xed_sweep(a.xed, ["-64", "-cet"], fn, 0)
            xerr += sum(1 for e in errors if e["kind"] == "undecodable")
            for i in insts:
                o = od["insts"].get(i["offset"])
                total += 1
                if o is None or o[0] != i["len"]:
                    bounds.append({"object": os.path.basename(path), "section": sec["name"], "offset": i["offset"],
                                   "xed": [i.get("iclass"), i["len"]], "objdump": o})
                    continue
                acc, mnem = norm.iclasses(o[1])
                pairs[(mnem, i.get("iclass"))] += 1
                if acc is None or i.get("iclass") not in acc:
                    bad.append({"object": os.path.basename(path), "section": sec["name"], "offset": i["offset"],
                                "xed_iclass": i.get("iclass"), "objdump": o[1], "normalised": sorted(acc or []),
                                "fp_sensitive": bool(fps.get(i.get("iclass"), True) or
                                                     any(fps.get(x, False) for x in (acc or [])))})
    out = {"objects": [os.path.abspath(p) for p in a.objects], "instructions_compared": total,
           "xed_undecodable": xerr, "boundary_disagreements": len(bounds), "iclass_disagreements": len(bad),
           "fp_sensitive_disagreements": sum(1 for b in bad if b["fp_sensitive"]),
           "distinct_pairs": len(pairs), "distinct_xed_iclasses": len({p[1] for p in pairs}),
           "distinct_fp_sensitive_xed_iclasses": len({p[1] for p in pairs if fps.get(p[1])}),
           "disagreements": bad[:500], "boundaries": bounds[:200],
           "pairs": sorted([[m, x, n] for (m, x), n in pairs.items()], key=lambda r: (r[1] or "", r[0] or ""))}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("disagreements", "boundaries", "pairs")}))
    for b in bad[:40]:
        print("DISAGREE", b["xed_iclass"], "|", b["objdump"], "|", b["normalised"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
