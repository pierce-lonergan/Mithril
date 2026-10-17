#!/usr/bin/env python3
"""x0_extract.py -- X0 record §4.1 (dispatched variants, slot -> function by relocation) and the object model
that x0_decode.py's §4.2 closure works on. Standard library only; Python >= 3.8. Run with python -I.

Usage (one configuration; each object is paired with the source file it was compiled from):
  python -I x0_extract.py -o MANIFEST.json --struct hx_kernels --struct-src engine/src/hx_quant.h \
      --index-names F32,F16,BF16,Q8,Q4,I32,U8 --expect-variants 18 --label A \
      --pair engine/src/quant.c=OBJ_quant --pair engine/src/quant_avx2.c=OBJ_avx2 \
      --pair engine/src/quant_avx512.c=OBJ_avx512 [--readobj llvm-readobj]
  Arm P (record §3, the reduce probe; x0final): --functions NAME[,NAME...] instead of --struct/--struct-src makes each
  named external-linkage function a variant (table "probe", slot = its name), found by its symbol; the probe is
  not a dispatch table. --expect-variants defaults to the number of names times the number of pairs.

Dispatched variants (§4.1). The dispatch tables are found in the SOURCE: every initialised object of type
`[static] const <struct> NAME = { ... };`. The struct layout comes from the struct definition (supported field
kinds: int/int32_t/uint32_t, function pointers and arrays of function-pointer typedefs). Every non-NULL
function-pointer field or array element is a slot. The script fails unless the number of slots equals
--expect-variants. In the OBJECT, each slot is mapped to its function only through the relocation on that
slot's 8 bytes of the table's data (ELF R_X86_64_64; COFF IMAGE_REL_AMD64_ADDR64, implicit addend), never by
name. The table is located by its symbol; if the object has no symbol for it, through the single data
relocation of the accessor function the source defines (`const S *f(void) { return &NAME; }`).

Function ranges (§4.2 "Function bytes"):
  ELF : [st_value, st_value + st_size) of STT_FUNC / STT_GNU_IFUNC symbols (st_size 0: to the next symbol,
        flagged).
  COFF: no symbol size. A function alone in a COMDAT code section spans the section ("comdat"). Otherwise the
        union of its .pdata RUNTIME_FUNCTION ranges ("pdata"). Otherwise up to the next function symbol or the
        section end ("next_symbol", flagged; a closure function with this range source is a P1 tooling gap).
        The .pdata entries of a function are cross-checked: the first begins at the function symbol; further
        entries (MSVC chained-unwind fragments) begin inside the function's range; the entries are sorted,
        non-overlapping and contiguous, and the last ends at or before the range end. A failure is recorded
        under range_check and becomes a `range_mismatch` gap if the function is in a closure. Leaf functions
        without .pdata entries are allowed ("no_pdata").
Slot names: after the relocation mapping, the initialiser's function name is compared with the resolved
function's names (GCC .constprop/.isra/.part/.cold suffixes stripped). A mismatch is a warning
(`slot_name_warnings`, variant `name_check`), not a gap: ICF and clones must stay visible, not fail.
Relocations are resolved to (target section, target offset) or to an undefined symbol, with ELF explicit and
COFF implicit (in-place) addends, so that x0_decode.py never needs the symbol table again.
"""
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x0obj  # noqa: E402

IMAGE_SCN_LNK_COMDAT = 0x1000


# ------------------------------------------------------------------------------------------- source side
def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def parse_struct(text, name):
    """Layout of `struct name { ... }` -> (fields, size). Field: dict(name, kind, offset, count, elem_size)."""
    t = strip_comments(text)
    m = re.search(r"struct\s+%s\s*\{(.*?)\}\s*(?:%s)?\s*;" % (re.escape(name), re.escape(name)), t, re.S)
    if not m:
        raise SystemExit("struct %s not found" % name)
    fields, off, maxal = [], 0, 1
    for decl in [d.strip() for d in m.group(1).split(";") if d.strip()]:
        d = " ".join(decl.split())
        fp = re.match(r"^.*\(\s*\*\s*(\w+)\s*\)\s*\(.*\)$", d)
        arr = re.match(r"^(\w+)\s+(\w+)\s*\[\s*(\d+)\s*\]$", d)
        sc = re.match(r"^(?:const\s+)?(int|int32_t|uint32_t|unsigned|unsigned int)\s+(\w+)$", d)
        ptr_td = re.match(r"^(\w+)\s+(\w+)$", d)
        if fp:
            fname, kind, size, count = fp.group(1), "fnptr", 8, 1
        elif arr and (arr.group(1).endswith("_fn") or "fn" in arr.group(1)):
            fname, kind, size, count = arr.group(2), "fnptr", 8, int(arr.group(3))
        elif sc:
            fname, kind, size, count = sc.group(2), "int", 4, 1
        elif ptr_td and ptr_td.group(1).endswith("_fn"):
            fname, kind, size, count = ptr_td.group(2), "fnptr", 8, 1
        else:
            raise SystemExit("struct %s: unsupported field declaration %r" % (name, d))
        off = (off + size - 1) // size * size
        fields.append({"name": fname, "kind": kind, "offset": off, "count": count, "elem_size": size})
        off += size * count
        maxal = max(maxal, size)
    return fields, (off + maxal - 1) // maxal * maxal


def _split_top(s):
    out, depth, cur = [], 0, []
    for ch in s:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


def parse_tables(text, struct_name):
    """`[static] const S NAME = { ... };` -> {NAME: {"linkage", "elements", "line"}}; accessor functions too."""
    t = strip_comments(text)
    tables = {}
    for m in re.finditer(r"(^|\n)\s*(static\s+)?const\s+%s\s+(\w+)\s*=\s*\{" % re.escape(struct_name), t):
        i, depth = m.end() - 1, 0
        for j in range(i, len(t)):
            if t[j] == "{":
                depth += 1
            elif t[j] == "}":
                depth -= 1
                if depth == 0:
                    break
        body = t[i + 1:j]
        elems = []
        for e in _split_top(body):
            elems.append([x.strip() for x in _split_top(e.strip()[1:-1])] if e.strip().startswith("{") else e.strip())
        tables[m.group(3)] = {"linkage": "static" if m.group(2) else "external", "elements": elems,
                              "line": t.count("\n", 0, m.start(3)) + 1}
    acc = {}
    for m in re.finditer(r"const\s+%s\s*\*\s*(\w+)\s*\(\s*void\s*\)\s*\{\s*return\s*&\s*(\w+)\s*;\s*\}" %
                         re.escape(struct_name), t):
        acc[m.group(2)] = m.group(1)
    return tables, acc


def table_slots(fields, table, index_names):
    """Slots of one table: list of dict(slot, offset, source_function or None)."""
    slots = []
    if len(table["elements"]) != len(fields):
        raise SystemExit("table initialiser has %d elements, struct has %d fields" % (len(table["elements"]), len(fields)))
    for f, e in zip(fields, table["elements"]):
        if f["kind"] != "fnptr":
            continue
        vals = e if isinstance(e, list) else [e]
        if f["count"] > 1 and len(vals) != f["count"]:
            raise SystemExit("array %s has %d initialisers, expected %d" % (f["name"], len(vals), f["count"]))
        for k, v in enumerate(vals):
            label = f["name"] if f["count"] == 1 else "%s[%s]" % (f["name"], index_names[k] if index_names else k)
            fn = None if v in ("NULL", "0", "((void*)0)") else v
            slots.append({"slot": label, "offset": f["offset"] + k * f["elem_size"], "source_function": fn})
    return slots


def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


# ------------------------------------------------------------------------------------------- object side
def resolve_relocs(obj):
    """Per section: list of resolved relocations sorted by offset."""
    data, secs, syms, is_coff = obj["data"], obj["sections"], obj["symbols"], obj["format"].startswith("coff")
    by_index = {s["index"]: s for s in syms}
    out = {}
    for sidx, lst in obj["relocs"].items():
        sec = secs[sidx]
        res = []
        for r in lst:
            s = by_index.get(r["sym"])
            if s is None:
                res.append({"offset": r["offset"], "type": r["type"], "width": r["width"], "sym_name": None,
                            "defined": False, "error": "symbol index %d" % r["sym"]})
                continue
            if is_coff:
                w = r["width"]
                fo = sec["offset"] + r["offset"]
                raw = data[fo:fo + w]
                if w == 8:
                    addend = struct.unpack("<Q", raw)[0]
                elif w == 4:
                    addend = struct.unpack("<i" if r["type"].startswith("REL32") else "<I", raw)[0]
                else:
                    addend = struct.unpack("<H", raw)[0] if w == 2 else 0
            else:
                addend = r["addend"]
            defined = bool(s["defined"])
            is_section = (s.get("type") == "section") or bool(s.get("is_section_symbol"))
            rec = {"offset": r["offset"], "type": r["type"], "width": r["width"], "sym_name": s["name"],
                   "defined": defined, "is_section_symbol": is_section, "addend": addend}
            if defined:
                rec["target_section"] = s["section"]
                rec["sym_value"] = s["value"] if not is_coff or not is_section else 0
            res.append(rec)
        out[sidx] = sorted(res, key=lambda r: r["offset"])
    return out


def functions_of(obj):
    secs, is_coff = obj["sections"], obj["format"].startswith("coff")
    code = {s["index"]: s for s in secs if s and s["is_code"] and s["size"] > 0}
    by_start = {}
    for sym in obj["symbols"]:
        if not sym["defined"] or sym["section"] not in code:
            continue
        if is_coff:
            if not sym["is_function"]:
                continue
            bind = "local" if sym["storage_class"] == "static" else "global"
            vis, size = 0, None
        else:
            if sym["type"] not in ("func", "gnu_ifunc"):
                continue
            bind, vis, size = sym["bind"], sym["visibility"], sym["size"]
        ent = by_start.setdefault((sym["section"], sym["value"]), {"names": [], "binds": [], "vis": [], "sizes": []})
        ent["names"].append(sym["name"])
        ent["binds"].append(bind)
        ent["vis"].append(vis)
        ent["sizes"].append(size)
    return code, by_start


def pdata_entries(obj, relocs):
    """COFF .pdata -> list of dict(begin_section, begin, end_section, end, pdata_section, entry)."""
    out = []
    for s in obj["sections"]:
        if not s or not s["name"].startswith(".pdata"):
            continue
        rl = {r["offset"]: r for r in relocs.get(s["index"], [])}
        for k in range(s["size"] // 12):
            b, e = rl.get(12 * k), rl.get(12 * k + 4)
            if not b or not e or not b["defined"] or not e["defined"]:
                out.append({"pdata_section": s["index"], "entry": k, "error": "unresolved begin/end"})
                continue
            out.append({"pdata_section": s["index"], "entry": k,
                        "begin_section": b["target_section"], "begin": b["sym_value"] + b["addend"],
                        "end_section": e["target_section"], "end": e["sym_value"] + e["addend"]})
    return out


def build_functions(obj, relocs):
    code, by_start = functions_of(obj)
    is_coff = obj["format"].startswith("coff")
    pd = pdata_entries(obj, relocs) if is_coff else []
    funcs, warnings = [], []
    for sidx, sec in sorted(code.items()):
        starts = sorted(st for (si, st) in by_start if si == sidx)
        comdat = bool(sec["flags"] & IMAGE_SCN_LNK_COMDAT) if is_coff else bool(sec.get("in_group"))
        for k, st in enumerate(starts):
            ent = by_start[(sidx, st)]
            nxt = starts[k + 1] if k + 1 < len(starts) else sec["size"]
            names = sorted(ent["names"], key=lambda n: (n.startswith("."), len(n), n))
            f = {"name": names[0], "aliases": names[1:], "section": sidx, "section_name": sec["name"], "start": st,
                 "bind": sorted(set(ent["binds"]))[0] if len(set(ent["binds"])) == 1 else "mixed",
                 "visibility": max(ent["vis"]), "comdat": comdat}
            if not is_coff:
                sizes = [x for x in ent["sizes"] if x]
                if sizes:
                    f.update(end=st + max(sizes), range_source="symbol_size")
                else:
                    f.update(end=nxt, range_source="next_symbol")
            else:
                mine = [p for p in pd if "error" not in p and p["begin_section"] == sidx and st <= p["begin"] < nxt]
                if comdat and len(starts) == 1:
                    f.update(end=sec["size"], range_source="comdat")
                elif mine:
                    f.update(end=max(p["end"] for p in mine), range_source="pdata")
                else:
                    f.update(end=nxt, range_source="next_symbol")
                mine = sorted(mine, key=lambda p: (p["begin"], p["end"]))
                f["pdata"] = [[p["begin"], p["end"]] for p in mine]
                checks = []
                if mine and mine[0]["begin"] != st:
                    checks.append("first .pdata entry begins at %#x, symbol at %#x" % (mine[0]["begin"], st))
                for p in mine:
                    if p["end_section"] != sidx or p["end"] > f["end"] or p["end"] <= p["begin"]:
                        checks.append(".pdata entry %d [%#x,%#x) not inside [%#x,%#x)" % (p["entry"], p["begin"], p["end"], st, f["end"]))
                for p, q in zip(mine, mine[1:]):     # chained-unwind fragments: sorted, contiguous, no overlap
                    if q["begin"] != p["end"]:
                        checks.append(".pdata entries %d [%#x,%#x) and %d [%#x,%#x) are not contiguous" % (
                            p["entry"], p["begin"], p["end"], q["entry"], q["begin"], q["end"]))
                f["range_check"] = "ok" if (mine and not checks) else ("no_pdata" if not mine else "mismatch")
                f["range_check_detail"] = checks
            if f["end"] > sec["size"]:
                warnings.append("%s runs past the end of %s" % (f["name"], sec["name"]))
            funcs.append(f)
    for p in pd:
        if "error" in p:
            warnings.append(".pdata entry %d: %s" % (p["entry"], p["error"]))
        elif not any(f["section"] == p["begin_section"] and f["start"] <= p["begin"] < f["end"] for f in funcs):
            warnings.append(".pdata entry %d [%#x,%#x) in section %d covers no function symbol" % (
                p["entry"], p["begin"], p["end"], p["begin_section"]))
    for i, f in enumerate(funcs):
        f["id"] = i
    return funcs, pd, warnings


GCC_SUFFIX_RE = re.compile(r"(\.(constprop|isra|part|lto_priv|clone|cold)(\.\d+)?)+$")


def name_check(source_function, resolved, funcs):
    """Warning-level cross-check of the relocation mapping (record §4.1 maps by relocation, never by name): is the
    initialiser's function among the resolved function's names after stripping GCC clone suffixes?"""
    if not source_function or not resolved or resolved.get("function_id") is None:
        return None
    m = re.search(r"(\w+)\s*$", source_function)
    want = m.group(1) if m else source_function
    f = funcs[resolved["function_id"]]
    names = {GCC_SUFFIX_RE.sub("", n) for n in [f["name"]] + f["aliases"]}
    return "match" if want in names else "mismatch"


def find_symbol(obj, name):
    hits = [s for s in obj["symbols"] if s["name"] == name and s["defined"]]
    return hits[0] if len(hits) == 1 else (None if not hits else "ambiguous")


def locate_table(obj, relocs, funcs, tname, accessor):
    s = find_symbol(obj, tname)
    if s == "ambiguous":
        return None, "ambiguous_symbol"
    if s is not None:
        return {"section": s["section"], "offset": s["value"], "size": s.get("size")}, "symbol"
    if accessor:
        fa = [f for f in funcs if accessor in [f["name"]] + f["aliases"]]
        if len(fa) == 1:
            f = fa[0]
            refs = [r for r in relocs.get(f["section"], []) if f["start"] <= r["offset"] < f["end"] and r["defined"]
                    and not obj["sections"][r["target_section"]]["is_code"]]
            if len(refs) == 1:
                r = refs[0]
                pcrel = r["type"] in ("PC32", "REL32", "GOTPCREL", "GOTPCRELX", "REX_GOTPCRELX")
                adj = 4 if (pcrel and not obj["format"].startswith("coff")) else 0
                return {"section": r["target_section"], "offset": r["sym_value"] + r["addend"] + adj, "size": None}, \
                    "accessor:%s" % accessor
        return None, "accessor_unresolved"
    return None, "absent"


def resolve_slot(obj, relocs, funcs, loc, slot):
    off = loc["offset"] + slot["offset"]
    rl = [r for r in relocs.get(loc["section"], []) if r["offset"] == off]
    if not rl:
        return None, "no relocation at table+%#x" % slot["offset"]
    r = rl[0]
    if r["type"] not in ("64", "ADDR64"):
        return None, "relocation type %s at slot" % r["type"]
    if not r["defined"]:
        return {"external": r["sym_name"]}, "slot relocation targets undefined symbol %s" % r["sym_name"]
    tsec, toff = r["target_section"], r["sym_value"] + r["addend"]
    f = [x for x in funcs if x["section"] == tsec and x["start"] == toff]
    if not f:
        inside = [x for x in funcs if x["section"] == tsec and x["start"] <= toff < x["end"]]
        return {"section": tsec, "offset": toff, "function": None,
                "inside": inside[0]["name"] if inside else None}, "slot target is not a function start"
    return {"section": tsec, "offset": toff, "function": f[0]["name"], "function_id": f[0]["id"]}, None


def readobj_crosscheck(readobj, path, funcs, is_coff):
    out = subprocess.run([readobj, "--symbols", path], capture_output=True, text=True)
    if out.returncode != 0:
        return {"error": out.stderr.strip()[:300]}
    names, blocks, cur = set(), [], None
    for line in out.stdout.splitlines():
        s = line.strip()
        if s == "Symbol {":
            cur = {}
            blocks.append(cur)
        elif cur is not None and ":" in s and not s.endswith("{"):
            k, v = s.split(":", 1)
            cur.setdefault(k.strip(), v.strip())
    for b in blocks:
        typ = b.get("Type", "") + " " + b.get("ComplexType", "")
        sec = b.get("Section", "")
        if ("Function" in typ or "GNU_IFunc" in typ) and sec and not re.search(r"Undefined|IMAGE_SYM_UNDEFINED|\(0\)$|Absolute", sec):
            names.add(re.sub(r"\s*\(\d+\)$", "", b.get("Name", "")))
    mine = {n for f in funcs for n in [f["name"]] + f["aliases"]}
    return {"tool": readobj, "only_readobj": sorted(names - mine), "only_x0obj": sorted(mine - names)}


def extract(pairs, struct_name, struct_src, index_names, label, readobj, functions=None):
    if functions:
        fields, ssize = [], 0
        out = {"label": label, "struct": None, "functions_mode": list(functions), "objects": [], "variants": [],
               "slot_name_warnings": []}
    else:
        fields, ssize = parse_struct(open(struct_src, encoding="utf-8").read(), struct_name)
        out = {"label": label, "struct": {"name": struct_name, "source": os.path.abspath(struct_src), "fields": fields,
                                          "size": ssize}, "objects": [], "variants": [], "slot_name_warnings": []}
    for src, objp in pairs:
        sbytes = open(src, "rb").read()
        tables, accessors = parse_tables(sbytes.decode("utf-8"), struct_name) if not functions else ({}, {})
        obj = x0obj.parse_object(objp)
        relocs = resolve_relocs(obj)
        funcs, pd, warnings = build_functions(obj, relocs)
        is_coff = obj["format"].startswith("coff")
        rec = {"object": os.path.abspath(objp), "sha256": hashlib.sha256(obj["data"]).hexdigest(),
               "source": os.path.abspath(src), "source_blob_sha1": git_blob_sha1(sbytes),
               "format": obj["format"], "kind": obj["kind"],
               "sections": [{"index": s["index"], "name": s["name"], "size": s["size"], "file_offset": s["offset"],
                             "is_code": s["is_code"], "flags": s["flags"],
                             "comdat": (bool(s["flags"] & IMAGE_SCN_LNK_COMDAT) if is_coff else bool(s.get("in_group")))}
                            for s in obj["sections"] if s],
               "functions": funcs, "pdata": pd,
               "relocs": {str(k): v for k, v in sorted(relocs.items())},
               "undefined_symbols": sorted({s["name"] for s in obj["symbols"] if not s["defined"] and s["name"]}),
               "tables": [], "warnings": warnings}
        if readobj:
            rec["readobj_crosscheck"] = readobj_crosscheck(readobj, objp, funcs, is_coff)
        for tname, t in sorted(tables.items()):
            slots = table_slots(fields, t, index_names)
            loc, how = locate_table(obj, relocs, funcs, tname, accessors.get(tname))
            trec = {"table": tname, "linkage": t["linkage"], "source_line": t["line"], "located_by": how,
                    "location": loc, "slots": []}
            if loc and loc.get("size") not in (None, 0) and loc["size"] != ssize:
                rec["warnings"].append("table %s symbol size %s != struct size %d" % (tname, loc["size"], ssize))
            for sl in slots:
                srec = dict(sl)
                if loc is None:
                    srec.update(resolved=None, gap="table_or_slot_absent", detail="table %s: %s" % (tname, how))
                else:
                    res, err = resolve_slot(obj, relocs, funcs, loc, sl)
                    if sl["source_function"] is None:
                        srec.update(resolved=res, gap="other" if res else None,
                                    detail="relocation present on a NULL slot" if res else None)
                    elif err and res is None:
                        srec.update(resolved=None, gap="table_or_slot_absent", detail=err)
                    elif err:
                        srec.update(resolved=res, gap="other", detail=err)
                    else:
                        srec.update(resolved=res, gap=None, detail=None)
                trec["slots"].append(srec)
                if sl["source_function"] is not None:
                    nc = name_check(sl["source_function"], srec["resolved"], funcs)
                    out["variants"].append({"object_index": len(out["objects"]), "table": tname, "slot": sl["slot"],
                                            "source_function": sl["source_function"], "resolved": srec["resolved"],
                                            "gap": srec["gap"], "detail": srec["detail"], "name_check": nc})
                    if nc == "mismatch":
                        out["slot_name_warnings"].append("%s %s: initialiser %s, relocation resolves to %s" % (
                            tname, sl["slot"], sl["source_function"], srec["resolved"].get("function")))
            rec["tables"].append(trec)
        for name in functions or []:
            # arm P (record §3): each probe wrapper is an external-linkage function found by its symbol name
            hits = [f for f in funcs if name in [f["name"]] + f["aliases"]]
            if len(hits) == 1:
                f = hits[0]
                res = {"section": f["section"], "offset": f["start"], "function": f["name"], "function_id": f["id"]}
                gap, det = None, None
            else:
                res, gap, det = None, "table_or_slot_absent", "symbol %s found %d times" % (name, len(hits))
            out["variants"].append({"object_index": len(out["objects"]), "table": "probe", "slot": name,
                                    "source_function": name, "resolved": res, "gap": gap, "detail": det,
                                    "name_check": "match" if res else None})
        out["objects"].append(rec)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--pair", action="append", required=True, help="SOURCE.c=OBJECT")
    ap.add_argument("--struct")
    ap.add_argument("--struct-src")
    ap.add_argument("--functions", help="arm P: comma-separated function names found by symbol (no dispatch table)")
    ap.add_argument("--index-names", default="", help="comma-separated names for array indices (e.g. F32,F16,...)")
    ap.add_argument("--expect-variants", type=int)
    ap.add_argument("--label")
    ap.add_argument("--readobj")
    a = ap.parse_args()
    pairs = [tuple(p.split("=", 1)) for p in a.pair]
    names = [x for x in a.index_names.split(",") if x] or None
    funcs = [x for x in (a.functions or "").split(",") if x]
    if not funcs and not (a.struct and a.struct_src):
        ap.error("--struct and --struct-src are required unless --functions is given")
    man = extract(pairs, a.struct, a.struct_src, names, a.label, a.readobj, funcs)
    nvar = len(man["variants"])
    man["n_variants"] = nvar
    problems = []
    if a.expect_variants is None and funcs:
        a.expect_variants = len(funcs) * len(pairs)
    if a.expect_variants is not None and nvar != a.expect_variants:
        problems.append("found %d dispatched variants in the sources, expected %d" % (nvar, a.expect_variants))
    for o in man["objects"]:
        problems += ["%s: %s" % (os.path.basename(o["object"]), w) for w in o["warnings"]]
        rc = o.get("readobj_crosscheck", {})
        if rc.get("only_readobj") or rc.get("only_x0obj") or rc.get("error"):
            problems.append("%s: llvm-readobj symbol cross-check differs: %s" % (os.path.basename(o["object"]), rc))
    man["problems"] = problems
    with open(a.out, "w") as f:
        json.dump(man, f, indent=1)
    for v in man["variants"]:
        r = v["resolved"] or {}
        print("%-26s %-22s -> %-28s %s" % (v["table"], v["slot"], r.get("function") or r.get("external") or "-",
                                           v["gap"] or "ok"), file=sys.stderr)
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    for w in man["slot_name_warnings"]:
        print("WARNING (slot name, not a gap):", w, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
