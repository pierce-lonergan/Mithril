#!/usr/bin/env python3
"""x0_extract.py -- find every function's bytes in x86-64 object files (ELF64 or COFF).

Usage:
  python3 x0_extract.py -o OUT.json OBJ [OBJ ...] [--readobj PATH/TO/llvm-readobj] [--label NAME]

For each object it writes one manifest (JSON) listing:
  * code sections (SHF_EXECINSTR / IMAGE_SCN_CNT_CODE), with COMDAT info (.text$mn, .text.<fn>);
  * functions: name, aliases, binding, section, [start,end) section offsets, how the size was
    obtained, the code ranges to decode, data ranges (jump tables found by relocation runs),
    trailing int3 fill trimmed, relocations inside the function;
  * gaps: bytes of code sections covered by no function (alignment padding, orphan code).

Boundary rules:
  ELF : STT_FUNC / STT_GNU_IFUNC symbols, [st_value, st_value+st_size). st_size 0 -> next symbol.
  COFF: symbols with Type 0x20 (function) defined in a code section. COFF has no symbol size, so
        end = next function symbol in the same section, else section end. Trailing 0xCC (int3)
        fill is trimmed. /Gy puts each function in its own COMDAT .text$mn section, so end is
        normally the section end.
  Data in code: a run of >= 2 relocations spaced exactly by their width (4 or 8 bytes) is a
        table (MSVC x64 places switch jump tables after the function in .text). Such ranges are
        excluded from decoding and reported.

With --readobj, the symbol table is cross-checked against llvm-readobj --symbols (names,
sections, values, and sizes for ELF); mismatches are listed under "crosscheck".

The manifest records the object's SHA-256 and file offsets so x0_decode.py reads bytes directly
from the object. Standard library only; Python >= 3.8.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x0obj  # noqa: E402

RUN_TYPES_OK = {"ADDR32NB", "ADDR32", "REL32", "ADDR64", "64", "32", "32S", "PC32", "PC64"}


def find_tables(relocs, lo, hi):
    """Return data ranges [(a,b)] for runs of >=2 relocations spaced by their width in [lo,hi)."""
    rs = sorted((r for r in relocs if lo <= r["offset"] < hi and r["type"] in RUN_TYPES_OK),
                key=lambda r: r["offset"])
    out, i = [], 0
    while i < len(rs):
        j = i
        while (j + 1 < len(rs) and rs[j + 1]["width"] == rs[i]["width"]
               and rs[j + 1]["offset"] - rs[j]["offset"] == rs[i]["width"]):
            j += 1
        if j > i:
            out.append((rs[i]["offset"], min(hi, rs[j]["offset"] + rs[j]["width"])))
        i = j + 1
    return out


def subtract(lo, hi, holes):
    """[lo,hi) minus sorted holes -> list of ranges."""
    out, cur = [], lo
    for a, b in sorted(holes):
        if a > cur:
            out.append((cur, min(a, hi)))
        cur = max(cur, b)
    if cur < hi:
        out.append((cur, hi))
    return [(a, b) for a, b in out if b > a]


def classify_fill(blob):
    if not blob:
        return "empty"
    if all(b == 0xCC for b in blob):
        return "int3"
    if all(b == 0x00 for b in blob):
        return "zero"
    if all(b == 0x90 for b in blob):
        return "nop90"
    return "other"


def readobj_symbols(readobj, path):
    """Parse `llvm-readobj --symbols` text output (ELF and COFF) into a list of dicts."""
    out = subprocess.run([readobj, "--symbols", path], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError("llvm-readobj failed: " + out.stderr.strip())
    syms, cur, depth = [], None, 0
    for line in out.stdout.splitlines():
        s = line.strip()
        if s == "Symbol {" and depth == 0:
            cur, depth = {}, 1
            continue
        if cur is None:
            continue
        if s.endswith("{"):
            depth += 1
            continue
        if s == "}":
            depth -= 1
            if depth == 0:
                syms.append(cur)
                cur = None
            continue
        if depth == 1 and ":" in s:
            k, v = s.split(":", 1)
            cur[k.strip()] = v.strip()
    return syms


def crosscheck(obj, funcs, readobj, path):
    issues = []
    rsyms = readobj_symbols(readobj, path)
    if obj["format"].startswith("coff"):
        rf = {}
        for s in rsyms:
            m = re.search(r"\((\d+)\)\s*$", s.get("Section", ""))
            if s.get("ComplexType", "").startswith("Function") and m and int(m.group(1)) > 0:
                rf.setdefault(s["Name"], set()).add((int(m.group(1)), int(s.get("Value", "0"), 0)))
        mine = {}
        for f in funcs:
            for n in [f["name"]] + f["aliases"]:
                mine.setdefault(n, set()).add((f["section"], f["start"]))
    else:
        rf = {}
        for s in rsyms:
            m = re.search(r"\((0x[0-9a-fA-F]+|\d+)\)\s*$", s.get("Section", ""))
            if s.get("Type", "").startswith(("Function", "GNU_IFunc")) and m and 0 < int(m.group(1), 0) < 0xFF00:
                name = re.sub(r"\s*\(\d+\)$", "", s["Name"])
                rf.setdefault(name, set()).add((int(m.group(1), 0), int(s.get("Value", "0"), 0),
                                                int(s.get("Size", "0"), 0)))
        mine = {}
        for f in funcs:
            sec = obj["sections"][f["section"]]
            base = sec["addr"] if obj["kind"] != "rel" else 0
            for n in [f["name"]] + f["aliases"]:
                mine.setdefault(n, set()).add((f["section"], f["start"] + base, f["symbol_size"]))
    for n in sorted(set(rf) | set(mine)):
        if rf.get(n) != mine.get(n):
            issues.append({"symbol": n, "llvm_readobj": sorted(rf.get(n, [])), "x0obj": sorted(mine.get(n, []))})
    return {"tool": readobj, "functions_readobj": sum(len(v) for v in rf.values()),
            "functions_x0obj": sum(len(v) for v in mine.values()), "mismatches": issues}


def extract(path, readobj=None, label=None):
    obj = x0obj.parse_object(path)
    data = obj["data"]
    secs = obj["sections"]
    is_coff = obj["format"].startswith("coff")
    code = {s["index"]: s for s in secs if s and s["is_code"] and s["size"] > 0}

    # ---- function symbols grouped by (section, start)
    by_start = {}
    for sym in obj["symbols"]:
        if not sym["defined"] or sym["section"] not in code:
            continue
        if is_coff:
            if not sym["is_function"]:
                continue
            start, ssize = sym["value"], None
        else:
            if sym["type"] not in ("func", "gnu_ifunc"):
                continue
            base = code[sym["section"]]["addr"] if obj["kind"] != "rel" else 0
            start, ssize = sym["value"] - base, sym["size"]
        key = (sym["section"], start)
        ent = by_start.setdefault(key, {"names": [], "binds": [], "sizes": []})
        ent["names"].append(sym["name"])
        ent["binds"].append(sym.get("bind") or sym.get("storage_class"))
        ent["sizes"].append(ssize)

    funcs, warnings = [], []
    for sidx, sec in sorted(code.items()):
        starts = sorted(st for (si, st) in by_start if si == sidx)
        relocs = obj["relocs"].get(sidx, [])
        for k, st in enumerate(starts):
            ent = by_start[(sidx, st)]
            nxt = starts[k + 1] if k + 1 < len(starts) else sec["size"]
            sizes = [s for s in ent["sizes"] if s]
            if sizes:
                end, how = st + max(sizes), "symbol_size"
                if len(set(sizes)) > 1:
                    warnings.append("aliases at %s+%#x have different sizes %s" % (sec["name"], st, sorted(set(sizes))))
            else:
                end, how = nxt, ("next_function_symbol" if k + 1 < len(starts) else "section_end")
            if end > sec["size"]:
                warnings.append("%s runs past end of section %s" % (ent["names"][0], sec["name"]))
                end = sec["size"]
            if end > nxt:
                warnings.append("%s overlaps next function at %#x" % (ent["names"][0], nxt))
            blob = data[sec["offset"] + st: sec["offset"] + end]
            trail = 0
            if how != "symbol_size":
                while trail < len(blob) and blob[len(blob) - 1 - trail] == 0xCC:
                    trail += 1
            tables = find_tables(relocs, st, end - trail)
            # int3 fill directly before a table is alignment, not code
            holes = []
            for a, b in tables:
                p = a
                while p > st and data[sec["offset"] + p - 1] == 0xCC:
                    p -= 1
                holes.append((p, b))
            ranges = subtract(st, end - trail, holes)
            names = sorted(ent["names"], key=lambda n: (n.startswith("."), len(n), n))
            funcs.append({
                "id": len(funcs), "name": names[0], "aliases": names[1:],
                "bind": sorted(set(str(b) for b in ent["binds"])),
                "section": sidx, "section_name": sec["name"], "comdat": sec.get("comdat") is not None
                or bool(sec.get("in_group")),
                "start": st, "end": end, "size": end - st, "size_source": how,
                "symbol_size": max(sizes) if sizes else None,
                "trailing_int3": trail,
                "code_ranges": [{"start": a, "end": b, "file_offset": sec["offset"] + a} for a, b in ranges],
                "data_ranges": [{"start": a, "end": b, "kind": "reloc_table"} for a, b in tables],
                "relocs": [{"offset": r["offset"], "type": r["type"], "width": r["width"]}
                           for r in relocs if st <= r["offset"] < end],
            })

    # ---- gaps: code bytes covered by no function
    gaps = []
    for sidx, sec in sorted(code.items()):
        cov = sorted((f["start"], f["end"]) for f in funcs if f["section"] == sidx)
        for a, b in subtract(0, sec["size"], cov):
            blob = data[sec["offset"] + a: sec["offset"] + b]
            gaps.append({"section": sidx, "section_name": sec["name"], "start": a, "end": b,
                         "file_offset": sec["offset"] + a, "fill": classify_fill(blob)})

    man = {
        "object": os.path.abspath(path), "label": label, "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data), "format": obj["format"], "kind": obj["kind"],
        "code_sections": [{"index": s["index"], "name": s["name"], "size": s["size"], "file_offset": s["offset"],
                           "align": s.get("align"), "comdat": s.get("comdat"),
                           "n_relocs": len(obj["relocs"].get(s["index"], []))} for s in code.values()],
        "functions": funcs, "gaps": gaps, "warnings": warnings,
    }
    if readobj:
        man["crosscheck"] = crosscheck(obj, funcs, readobj, path)
    return man


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("objects", nargs="+")
    ap.add_argument("-o", "--out", required=True, help="output JSON (list of manifests)")
    ap.add_argument("--readobj", help="path to llvm-readobj for symbol cross-check")
    ap.add_argument("--label", help="configuration label stored in each manifest (e.g. A-msvc)")
    a = ap.parse_args()
    mans, bad = [], 0
    for p in a.objects:
        m = extract(p, a.readobj, a.label)
        mans.append(m)
        cc = m.get("crosscheck", {}).get("mismatches", [])
        bad += len(cc) + len(m["warnings"])
        print("%s: %s, %d code sections, %d functions, %d gaps, %d warnings%s" % (
            p, m["format"], len(m["code_sections"]), len(m["functions"]), len(m["gaps"]), len(m["warnings"]),
            (", crosscheck mismatches %d" % len(cc)) if "crosscheck" in m else ""), file=sys.stderr)
    with open(a.out, "w") as f:
        json.dump(mans, f, indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
