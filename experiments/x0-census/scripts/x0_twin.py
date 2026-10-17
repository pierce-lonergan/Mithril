#!/usr/bin/env python3
"""x0_twin.py -- X0 record §4.6 (debug-info twin, source attribution only) for ONE census object.

Usage:
  python -I x0_twin.py --census OBJ --twin TWIN_OBJ --source SRC.c -o ATTR.json
         [--readobj llvm-readobj] [--dwarfdump llvm-dwarfdump] [--objdump llvm-objdump]
         [--codeview-text F] [--dwarfdump-text F] [--source-dir DIR ...]

The twin is the census file compiled again from its captured command line with exactly one flag added (/Z7 for
A, A-ninja and B-cmake; -g for C and D; the driver builds it). This script:
 1. Identity (§4.6). The executable sections of the census object and of the twin are paired by key (section name
    plus the sorted names of the function symbols defined in the section; an ordinal among equal keys), and for
    each pair compares the bytes and the relocation list (offset, type, target symbol name, addend; COFF addends
    are the in-place field, so they are compared twice, once in the bytes). A census code section without a twin
    partner, or a pair that differs, is not identical. A variant's attribution is EXACT only if every executable
    section in its closure is identical (x0_loops.py decides that per variant from this file) or, x0final revision,
    if a differing section kept its size and relocation offsets and the closure function's own range is identical
    (`functions` of the section record, function_identity); otherwise it is APPROXIMATE, and loops fall back to the
    variant-wide bound of P3(c), d2 sites are `unchecked`. (A line table that fails the self-checks below makes the
    attribution NONE, which x0_census.py and judge.py treat as a tooling gap.)
 2. Line tables of the twin.
    * ELF / DWARF: `.debug_line` is decoded here (DWARF 4 and 5) with the object's relocations, which gives every
      row its section (a relocatable object has every section at address 0, so `llvm-dwarfdump` alone cannot say
      which section a row belongs to). Every row (address, line, file index, end_sequence) is then compared, in
      order, with `llvm-dwarfdump --debug-line` (the record's tool); any difference fails the line table.
    * COFF / CodeView (/Z7): `llvm-readobj --codeview` (the record's tool) is parsed: per procedure its
      FunctionLineTable, its S_INLINESITE records (nested through S_INLINESITE / S_INLINESITE_END) with their
      binary annotations, and the InlineeLines subsection (each inlinee's file and first line). Annotation
      semantics, measured on MSVC 19.44 and clang-cl 23.1.3 objects (NON-Hearth smoke file, x0final 2026-10-16):
      ChangeCodeOffset d and ChangeCodeOffsetAndLineOffset (d, l) open a row at offset += d that runs to the next
      row start or to the end given by ChangeCodeLength L (which also advances the offset to that end);
      ChangeCodeLengthAndCodeOffset (L, d) is a closed row [offset += d, offset + L) and leaves the offset at its
      start; ChangeLineOffset and ChangeFile change the line and file of later rows. Offsets are relative to the
      procedure start.
    The INNERMOST frame wins: an address covered by an inline site gets the inlinee's line (deepest site), else
    the procedure's line-table line (MSVC and LLVM give the call-site line there for inlined code). DWARF line
    tables already give the innermost line. Line 0 (compiler-generated code) gives no line.
 3. Self-checks (any failure makes the line table unusable: attribution none for the whole object):
    every row start must be an instruction start of `llvm-objdump -d` on the twin (when --objdump is given), and
    every CodeView row must lie inside its procedure.
 4. Source side (read from the census SOURCE files, never from an object): the line ranges of every `for`,
    `while` and `do` loop and of every function definition in the census source and in any source the line table
    names that exists in a --source-dir. A loop's range runs from its keyword to the end of its body.

Output ATTR.json: identity per section, `lines` (per CENSUS section index: sorted [start, end, file_basename, line,
depth]), source `loops` and `functions` per file basename, the tools used and the self-check results. Line ranges
are expressed in census-object coordinates, and only for section pairs whose bytes and relocations are identical
or, marked approximate, for pairs whose sizes match.
Standard library only; Python >= 3.8. Run with python -I (the objects are untrusted input).
"""
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x0obj  # noqa: E402
import x0_extract  # noqa: E402


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------------------------------- identity (§4.6)
def _sec_bytes(obj, s):
    if obj["format"].startswith("coff") and not s["offset"]:
        return b"\0" * s["size"]
    return obj["data"][s["offset"]: s["offset"] + s["size"]]


def code_sections(obj):
    """Executable sections with their pairing keys."""
    is_coff = obj["format"].startswith("coff")
    out = []
    for s in obj["sections"]:
        if not s or not s["is_code"] or s["size"] <= 0:
            continue
        names = []
        for sym in obj["symbols"]:
            if not sym["defined"] or sym["section"] != s["index"]:
                continue
            if is_coff:
                if sym["is_function"] or sym["storage_class"] in ("external", "static") and not sym.get("is_section_symbol"):
                    if sym["is_function"]:
                        names.append(sym["name"])
            elif sym["type"] in ("func", "gnu_ifunc"):
                names.append(sym["name"])
        out.append({"index": s["index"], "name": s["name"], "size": s["size"],
                    "key": "%s|%s" % (s["name"], ",".join(sorted(set(names))))})
    seen = {}
    for c in out:
        k = c["key"]
        seen[k] = seen.get(k, 0) + 1
        c["key"] = "%s#%d" % (k, seen[k])
    return out


def reloc_list(relocs, sidx):
    return [[r["offset"], r["type"], r.get("sym_name"), r.get("addend")] for r in relocs.get(sidx, [])]


def function_identity(cobj, sidx, cb, tb, cr, tr):
    """x0final revision (review of 2026-10-16/17; record §4.6): per-function identity inside a section pair that
    differs. Only when the two sections have the same size and their relocation lists the same offsets and types
    (so no address moved); then every function symbol of the census section with a size (ELF st_size) is identical
    if its bytes [st_value, st_value + st_size) and its relocations in that range (offset, type, target symbol,
    addend) are equal. Returns None when the precondition fails (the whole section stays not identical) or the
    format gives no function sizes (COFF: MSVC and clang-cl put each function in its own COMDAT section under /Gy)."""
    if len(cb) != len(tb) or [r[:2] for r in cr] != [r[:2] for r in tr]:
        return None
    out = []
    for sym in cobj["symbols"]:
        if not sym.get("defined") or sym.get("section") != sidx or sym.get("type") not in ("func", "gnu_ifunc"):
            continue
        lo, hi = sym.get("value"), (sym.get("value") or 0) + (sym.get("size") or 0)
        if not isinstance(lo, int) or not sym.get("size"):
            continue
        same = cb[lo:hi] == tb[lo:hi] and [r for r in cr if lo <= r[0] < hi] == [r for r in tr if lo <= r[0] < hi]
        out.append({"name": sym["name"], "start": lo, "end": hi, "identical": same})
    return sorted(out, key=lambda f: (f["start"], f["name"])) if out else None


def identity(cobj, tobj):
    crel, trel = x0_extract.resolve_relocs(cobj), x0_extract.resolve_relocs(tobj)
    cs, ts = code_sections(cobj), code_sections(tobj)
    tby = {t["key"]: t for t in ts}
    secs, pair = [], {}
    for c in cs:
        t = tby.get(c["key"])
        cb = _sec_bytes(cobj, cobj["sections"][c["index"]])
        cr = reloc_list(crel, c["index"])
        rec = {"census_index": c["index"], "name": c["name"], "key": c["key"], "size": c["size"],
               "census_bytes_sha256": sha256_bytes(cb),
               "census_relocs_sha256": sha256_bytes(json.dumps(cr).encode())}
        if t is None:
            rec.update(twin_index=None, bytes_equal=False, relocs_equal=False, identical=False,
                       detail="no twin section with this key")
        else:
            tb = _sec_bytes(tobj, tobj["sections"][t["index"]])
            tr = reloc_list(trel, t["index"])
            be, re_ = cb == tb, cr == tr
            rec.update(twin_index=t["index"], twin_bytes_sha256=sha256_bytes(tb),
                       twin_relocs_sha256=sha256_bytes(json.dumps(tr).encode()), bytes_equal=be, relocs_equal=re_,
                       identical=be and re_, size_equal=len(cb) == len(tb))
            if not re_:
                diff = [(a, b) for a, b in zip(cr, tr) if a != b][:5]
                rec["detail"] = "relocations differ (%d vs %d; first differences %s)" % (len(cr), len(tr), diff)
            elif not be:
                k = next((i for i in range(min(len(cb), len(tb))) if cb[i] != tb[i]), min(len(cb), len(tb)))
                rec["detail"] = "bytes differ (first at %#x; sizes %d vs %d)" % (k, len(cb), len(tb))
            if not (be and re_):
                rec["functions"] = function_identity(cobj, c["index"], cb, tb, cr, tr)
            pair[t["index"]] = c["index"]
        secs.append(rec)
    used = {s["twin_index"] for s in secs if s.get("twin_index") is not None}
    extra = [t["key"] for t in ts if t["index"] not in used]
    return {"identical": all(s["identical"] for s in secs) and not extra, "sections": secs,
            "twin_only_code_sections": extra}, pair


# ------------------------------------------------------------------------------------------- DWARF .debug_line
def _uleb(b, p):
    r, s = 0, 0
    while True:
        x = b[p]
        p += 1
        r |= (x & 0x7F) << s
        s += 7
        if not x & 0x80:
            return r, p


def _sleb(b, p):
    r, s = 0, 0
    while True:
        x = b[p]
        p += 1
        r |= (x & 0x7F) << s
        s += 7
        if not x & 0x80:
            if x & 0x40:
                r -= 1 << s
            return r, p


def _cstr(b, p):
    e = b.index(b"\0", p)
    return b[p:e].decode("utf-8", "replace"), e + 1


def _sec_by_name(obj, name):
    hits = [s for s in obj["sections"] if s and s["name"] == name]
    return hits[0] if hits else None


def parse_debug_line(obj):
    """Decode every line table of .debug_line. Returns (tables, error). A table: {"files": [name...],
    "rows": [[section_index|None, address, line, file_index, end_sequence]]}. Relocations give each
    DW_LNE_set_address its section, and each DW_FORM_line_strp / DW_FORM_strp its string offset."""
    dl = _sec_by_name(obj, ".debug_line")
    if dl is None:
        return None, "no .debug_line section"
    data = obj["data"][dl["offset"]: dl["offset"] + dl["size"]]
    rels = {r["offset"]: r for r in obj["relocs"].get(dl["index"], [])}
    syms = {s["index"]: s for s in obj["symbols"]}

    def rel_value(off, raw):
        r = rels.get(off)
        if r is None:
            return None, raw
        s = syms.get(r["sym"])
        if s is None:
            return None, raw
        return (s["section"] if s["defined"] else None), (s["value"] if s.get("type") != "section" else 0) + r["addend"]

    strs = {}
    for nm in (".debug_line_str", ".debug_str"):
        s = _sec_by_name(obj, nm)
        if s:
            strs[nm] = obj["data"][s["offset"]: s["offset"] + s["size"]]
    tables, pos = [], 0
    while pos < len(data):
        unit_len = struct.unpack_from("<I", data, pos)[0]
        p = pos + 4
        off64 = unit_len == 0xFFFFFFFF
        if off64:
            unit_len = struct.unpack_from("<Q", data, p)[0]
            p += 8
        end = p + unit_len
        version = struct.unpack_from("<H", data, p)[0]
        p += 2
        if version < 2 or version > 5:
            return None, "unsupported .debug_line version %d" % version
        addr_size = 8
        if version >= 5:
            addr_size = data[p]
            p += 2
        osz = 8 if off64 else 4
        hdr_len = struct.unpack_from("<Q" if off64 else "<I", data, p)[0]
        p += osz
        prog = p + hdr_len
        min_inst = data[p]
        p += 1
        max_ops = 1
        if version >= 4:
            max_ops = data[p]
            p += 1
        default_is_stmt = data[p]
        line_base = struct.unpack_from("<b", data, p + 1)[0]
        line_range = data[p + 2]
        opcode_base = data[p + 3]
        p += 4
        std_len = list(data[p: p + opcode_base - 1])
        p += opcode_base - 1
        files, dirs = [], []
        if version >= 5:
            def entries(p):
                nfmt = data[p]
                p += 1
                fmts = []
                for _ in range(nfmt):
                    ct, p = _uleb(data, p)
                    fm, p = _uleb(data, p)
                    fmts.append((ct, fm))
                n, p = _uleb(data, p)
                out = []
                for _ in range(n):
                    ent = {}
                    for ct, fm in fmts:
                        val = None
                        if fm == 0x08:                                  # string
                            val, p = _cstr(data, p)
                        elif fm in (0x1F, 0x0E):                        # line_strp, strp
                            raw = struct.unpack_from("<Q" if off64 else "<I", data, p)[0]
                            _, v = rel_value(p, raw)
                            blob = strs.get(".debug_line_str" if fm == 0x1F else ".debug_str", b"")
                            val = _cstr(blob, v)[0] if 0 <= v < len(blob) else "?"
                            p += osz
                        elif fm == 0x0F:                                # udata
                            val, p = _uleb(data, p)
                        elif fm in (0x0B, 0x05, 0x06, 0x07, 0x1E):      # data1/2/4/8/16
                            w = {0x0B: 1, 0x05: 2, 0x06: 4, 0x07: 8, 0x1E: 16}[fm]
                            val = data[p: p + w]
                            p += w
                        elif fm == 0x09:                                # block
                            n2, p = _uleb(data, p)
                            val = data[p: p + n2]
                            p += n2
                        else:
                            raise ValueError("unsupported DW_FORM %#x in a line-table header" % fm)
                        ent[ct] = val
                    out.append(ent)
                return out, p
            dents, p = entries(p)
            dirs = [d.get(1, "") for d in dents]
            fents, p = entries(p)
            for f in fents:
                nm = f.get(1, "")
                di = f.get(2, 0)
                d = dirs[di] if isinstance(di, int) and di < len(dirs) else ""
                files.append(nm if nm.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", nm) else (d + "/" + nm if d else nm))
            first_file = 0
        else:
            dirs = [""]
            while data[p] != 0:
                d, p = _cstr(data, p)
                dirs.append(d)
            p += 1
            files = [None]
            while data[p] != 0:
                nm, p = _cstr(data, p)
                di, p = _uleb(data, p)
                _, p = _uleb(data, p)
                _, p = _uleb(data, p)
                d = dirs[di] if di < len(dirs) else ""
                files.append(nm if nm.startswith("/") else (d + "/" + nm if d else nm))
            p += 1
            first_file = 1
        # the line program
        rows = []
        p = prog

        def reset():
            return {"sec": None, "addr": 0, "op": 0, "file": 1, "line": 1, "stmt": default_is_stmt}
        st = reset()
        while p < end:
            op = data[p]
            p += 1
            if op >= opcode_base:
                adj = op - opcode_base
                st["addr"] += min_inst * ((st["op"] + adj // line_range) // max_ops)
                st["line"] += line_base + adj % line_range
                rows.append([st["sec"], st["addr"], st["line"], st["file"], False])
            elif op == 0:
                ln, p = _uleb(data, p)
                sub = data[p]
                q = p + 1
                if sub == 1:
                    rows.append([st["sec"], st["addr"], st["line"], st["file"], True])
                    st = reset()
                elif sub == 2:
                    raw = struct.unpack_from("<Q" if addr_size == 8 else "<I", data, q)[0]
                    sec, val = rel_value(q, raw)
                    st["sec"], st["addr"], st["op"] = sec, val, 0
                elif sub == 3:
                    pass                                  # DW_LNE_define_file (v <= 4): ignored, rare
                p += ln
            elif op == 1:
                rows.append([st["sec"], st["addr"], st["line"], st["file"], False])
            elif op == 2:
                v, p = _uleb(data, p)
                st["addr"] += min_inst * v
            elif op == 3:
                v, p = _sleb(data, p)
                st["line"] += v
            elif op == 4:
                st["file"], p = _uleb(data, p)
            elif op == 5:
                _, p = _uleb(data, p)
            elif op == 6:
                st["stmt"] = not st["stmt"]
            elif op in (7, 10, 11):
                pass
            elif op == 8:
                st["addr"] += min_inst * ((255 - opcode_base) // line_range)
            elif op == 9:
                st["addr"] += struct.unpack_from("<H", data, p)[0]
                p += 2
            elif op == 12:
                _, p = _uleb(data, p)
            else:
                for _ in range(std_len[op - 1]):
                    _, p = _uleb(data, p)
        tables.append({"version": version, "files": files, "first_file_index": first_file, "rows": rows})
        pos = end
    return tables, None


DD_ROW = re.compile(r"^0x([0-9a-f]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+\s*(.*)$")


def parse_dwarfdump_rows(text):
    """Rows of `llvm-dwarfdump --debug-line` per table: [[address, line, file, end_sequence]]."""
    tables, cur = [], None
    for line in text.splitlines():
        if line.startswith("debug_line["):
            cur = []
            tables.append(cur)
            continue
        m = DD_ROW.match(line.strip())
        if m and cur is not None:
            cur.append([int(m.group(1), 16), int(m.group(2)), int(m.group(4)), "end_sequence" in m.group(5)])
    return tables


def dwarf_ranges(tables):
    """{section: [[start, end, file, line, depth]]} from decoded rows (the last row at an address wins; a row
    covers up to the next row of the same sequence and section)."""
    out = {}
    unextended = 0
    for t in tables:
        files = t["files"]
        rows = t["rows"]
        for i, (sec, addr, line, fidx, endseq) in enumerate(rows):
            if endseq or sec is None:
                continue
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            if nxt is None or nxt[0] != sec or nxt[1] < addr:
                unextended += 1
                continue
            if nxt[1] == addr:
                continue
            fname = files[fidx] if 0 <= fidx < len(files) and files[fidx] else "?"
            out.setdefault(sec, []).append([addr, nxt[1], os.path.basename(fname.replace("\\", "/")), line or None, 0])
    return out, unextended


# ------------------------------------------------------------------------------------------- DWARF inline frames
FORM_FIXED = {0x0B: 1, 0x05: 2, 0x06: 4, 0x07: 8, 0x1E: 16, 0x0C: 1, 0x11: 1, 0x12: 2, 0x13: 4, 0x14: 8, 0x20: 8,
              0x25: 1, 0x26: 2, 0x27: 3, 0x28: 4, 0x29: 1, 0x2A: 2, 0x2B: 3, 0x2C: 4, 0x1C: 4, 0x24: 8}
TAG_SUBPROGRAM, TAG_INLINED = 0x2E, 0x1D
AT = {"low_pc": 0x11, "high_pc": 0x12, "ranges": 0x55, "call_file": 0x58, "call_line": 0x59, "addr_base": 0x73,
      "rnglists_base": 0x74, "name": 0x03, "abstract_origin": 0x31}


class _Reloc:
    def __init__(self, obj, sec):
        self.syms = {s["index"]: s for s in obj["symbols"]}
        self.rels = {r["offset"]: r for r in obj["relocs"].get(sec["index"], [])} if sec else {}

    def value(self, off, raw):
        """(section, value) of a relocated field at `off`, or (None, raw)."""
        r = self.rels.get(off)
        if r is None:
            return None, raw
        s = self.syms.get(r["sym"])
        if s is None or not s["defined"]:
            return None, raw
        return s["section"], (s["value"] if s.get("type") != "section" else 0) + r["addend"]


def parse_inlined(obj, files):
    """Every DW_TAG_inlined_subroutine of .debug_info: {"depth", "ranges": [[section, start, end]], "call_file",
    "call_line"} in DIE order, with relocations applied (section-aware, unlike llvm-dwarfdump's text for a .o).
    DWARF 5 (GCC 13, Clang 23) and DWARF 4 compile units; `files` is the CU's line-table file list."""
    di, ab = _sec_by_name(obj, ".debug_info"), _sec_by_name(obj, ".debug_abbrev")
    if di is None or ab is None:
        return None, "no .debug_info or .debug_abbrev"
    data = obj["data"][di["offset"]: di["offset"] + di["size"]]
    abd = obj["data"][ab["offset"]: ab["offset"] + ab["size"]]
    sec = {n: _sec_by_name(obj, n) for n in (".debug_addr", ".debug_rnglists", ".debug_ranges")}
    blob = {n: (obj["data"][s["offset"]: s["offset"] + s["size"]] if s else b"") for n, s in sec.items()}
    rel_info = _Reloc(obj, di)
    rel_addr, rel_rng = _Reloc(obj, sec[".debug_addr"]), _Reloc(obj, sec[".debug_rnglists"])
    out, pos = [], 0
    while pos < len(data):
        unit_len = struct.unpack_from("<I", data, pos)[0]
        p = pos + 4
        off64 = unit_len == 0xFFFFFFFF
        if off64:
            unit_len = struct.unpack_from("<Q", data, p)[0]
            p += 8
        end = p + unit_len
        osz = 8 if off64 else 4
        version = struct.unpack_from("<H", data, p)[0]
        p += 2
        if version >= 5:
            utype, asz = data[p], data[p + 1]
            p += 2
            raw = struct.unpack_from("<Q" if off64 else "<I", data, p)[0]
            aoff = rel_info.value(p, raw)[1]
            p += osz
            if utype in (4, 5):                    # skeleton / split: dwo id
                p += 8
            elif utype in (2, 6):                  # type units: signature + offset
                p += 8 + osz
        else:
            raw = struct.unpack_from("<Q" if off64 else "<I", data, p)[0]
            aoff = rel_info.value(p, raw)[1]
            p += osz
            asz = data[p]
            p += 1
        abbrevs = _parse_abbrev(abd, aoff)
        cu = {"addr_base": None, "rnglists_base": None, "low_pc": (None, 0)}
        stack = []                                 # nesting of DIEs with children: tags
        pending = []
        while p < end:
            code, p = _uleb(data, p)
            if code == 0:
                if stack:
                    stack.pop()
                continue
            tag, children, specs = abbrevs[code]
            attrs = {}
            for at, form, ic in specs:
                val, p = _read_form(data, p, form, ic, asz, osz, rel_info, version)
                attrs[at] = (form, val)
            if tag == 0x11:                        # compile unit
                for k in ("addr_base", "rnglists_base"):
                    if AT[k] in attrs:
                        cu[k] = attrs[AT[k]][1][1] if isinstance(attrs[AT[k]][1], tuple) else attrs[AT[k]][1]
                if AT["low_pc"] in attrs:
                    form, val = attrs[AT["low_pc"]]
                    if form in (0x1B, 0x29, 0x2A, 0x2B, 0x2C):          # addrx: needs addr_base (read above)
                        cu["low_pc"] = _addrx(val, cu, asz, blob, rel_addr)
                    else:
                        cu["low_pc"] = val
            if tag == TAG_INLINED:
                depth = sum(1 for t in stack if t == TAG_INLINED) + 1
                pending.append((depth, attrs))
            if children:
                stack.append(tag)
        for depth, attrs in pending:
            ranges, err = _die_ranges(attrs, cu, asz, osz, blob, rel_addr, rel_rng, version)
            cf = attrs.get(AT["call_file"], (None, None))[1]
            cl = attrs.get(AT["call_line"], (None, None))[1]
            fname = files[cf] if isinstance(cf, int) and 0 <= cf < len(files) and files[cf] else None
            out.append({"depth": depth, "ranges": ranges, "call_file": fname, "call_line": cl, "error": err})
        pos = end
    return out, None


def _parse_abbrev(b, off):
    out, p = {}, off
    while True:
        code, p = _uleb(b, p)
        if code == 0:
            return out
        tag, p = _uleb(b, p)
        children = b[p]
        p += 1
        specs = []
        while True:
            at, p = _uleb(b, p)
            form, p = _uleb(b, p)
            ic = None
            if form == 0x21:
                ic, p = _sleb(b, p)
            if at == 0 and form == 0:
                break
            specs.append((at, form, ic))
        out[code] = (tag, children, specs)


def _read_form(d, p, form, ic, asz, osz, rel, version):
    if form == 0x01:                               # addr: relocated -> (section, value)
        raw = struct.unpack_from("<Q" if asz == 8 else "<I", d, p)[0]
        return rel.value(p, raw), p + asz
    if form in (0x0E, 0x17, 0x1F, 0x10, 0x1D):      # strp, sec_offset, line_strp, ref_addr, strp_sup
        raw = struct.unpack_from("<Q" if osz == 8 else "<I", d, p)[0]
        return rel.value(p, raw), p + osz
    if form in FORM_FIXED:
        n = FORM_FIXED[form]
        if form in (0x0B, 0x05, 0x06, 0x07, 0x11, 0x12, 0x13, 0x14, 0x25, 0x26, 0x28, 0x29, 0x2A, 0x2C, 0x1C, 0x24):
            v = int.from_bytes(d[p: p + n], "little")
        elif form in (0x27, 0x2B):
            v = int.from_bytes(d[p: p + 3], "little")
        else:
            v = d[p: p + n]
        return v, p + n
    if form == 0x08:
        e = d.index(b"\0", p)
        return d[p:e].decode("utf-8", "replace"), e + 1
    if form in (0x0F, 0x15, 0x1A, 0x1B, 0x22, 0x23, 0x1F01, 0x1F02):
        return _uleb(d, p)
    if form == 0x0D:
        return _sleb(d, p)
    if form == 0x19:
        return True, p
    if form == 0x21:
        return ic, p
    if form in (0x09, 0x18):
        n, p = _uleb(d, p)
        return d[p: p + n], p + n
    if form == 0x0A:
        return d[p + 1: p + 1 + d[p]], p + 1 + d[p]
    if form == 0x03:
        n = struct.unpack_from("<H", d, p)[0]
        return d[p + 2: p + 2 + n], p + 2 + n
    if form == 0x04:
        n = struct.unpack_from("<I", d, p)[0]
        return d[p + 4: p + 4 + n], p + 4 + n
    if form == 0x16:
        f2, p = _uleb(d, p)
        return _read_form(d, p, f2, ic, asz, osz, rel, version)
    raise ValueError("unsupported DW_FORM %#x" % form)


def _addrx(idx, cu, asz, blob, rel_addr):
    off = (cu["addr_base"] or 8) + idx * asz
    raw = int.from_bytes(blob[".debug_addr"][off: off + asz], "little")
    return rel_addr.value(off, raw)


def _die_ranges(attrs, cu, asz, osz, blob, rel_addr, rel_rng, version):
    lo = attrs.get(AT["low_pc"])
    if lo is not None:
        form, v = lo
        start = v if form == 0x01 else (_addrx(v, cu, asz, blob, rel_addr) if form in (0x1B, 0x29, 0x2A, 0x2B, 0x2C) else (None, v))
        hi = attrs.get(AT["high_pc"])
        if hi is None:
            return [], "low_pc without high_pc"
        hform, hv = hi
        if hform == 0x01:
            end = hv[1]
        elif hform in (0x1B, 0x29, 0x2A, 0x2B, 0x2C):
            end = _addrx(hv, cu, asz, blob, rel_addr)[1]
        else:
            end = start[1] + hv
        return [[start[0], start[1], end]], None
    rg = attrs.get(AT["ranges"])
    if rg is None:
        return [], None
    form, v = rg
    if version < 5:
        return [], "DWARF 4 .debug_ranges not supported"
    b = blob[".debug_rnglists"]
    if form == 0x23:                               # rnglistx
        base = cu["rnglists_base"] or 12
        off = base + int.from_bytes(b[base + v * osz: base + v * osz + osz], "little")
    else:
        off = v[1] if isinstance(v, tuple) else v
    base_sec, base_val = cu["low_pc"] if isinstance(cu["low_pc"], tuple) else (None, 0)
    out, p = [], off
    while p < len(b):
        k = b[p]
        p += 1
        if k == 0:
            break
        if k == 1:
            i, p = _uleb(b, p)
            base_sec, base_val = _addrx(i, cu, asz, blob, rel_addr)
        elif k == 2:
            i, p = _uleb(b, p)
            j, p = _uleb(b, p)
            s, e = _addrx(i, cu, asz, blob, rel_addr), _addrx(j, cu, asz, blob, rel_addr)
            out.append([s[0], s[1], e[1]])
        elif k == 3:
            i, p = _uleb(b, p)
            n, p = _uleb(b, p)
            s = _addrx(i, cu, asz, blob, rel_addr)
            out.append([s[0], s[1], s[1] + n])
        elif k == 4:
            a, p = _uleb(b, p)
            e, p = _uleb(b, p)
            out.append([base_sec, base_val + a, base_val + e])
        elif k == 5:
            raw = int.from_bytes(b[p: p + asz], "little")
            base_sec, base_val = rel_rng.value(p, raw)
            p += asz
        elif k == 6:
            s = rel_rng.value(p, int.from_bytes(b[p: p + asz], "little"))
            e = rel_rng.value(p + asz, int.from_bytes(b[p + asz: p + 2 * asz], "little"))
            p += 2 * asz
            out.append([s[0], s[1], e[1]])
        elif k == 7:
            s = rel_rng.value(p, int.from_bytes(b[p: p + asz], "little"))
            p += asz
            n, p = _uleb(b, p)
            out.append([s[0], s[1], s[1] + n])
        else:
            return out, "unknown DW_RLE %d" % k
    return out, None


DD_DIE = re.compile(r"^(0x[0-9a-f]+):(\s+)(DW_TAG_\w+)")
DD_RANGE = re.compile(r"\[0x([0-9a-f]+), 0x([0-9a-f]+)\)")


def parse_dwarfdump_inlined(text):
    """llvm-dwarfdump --debug-info: every DW_TAG_inlined_subroutine in order: [[start, end], ...], call_line."""
    out, cur, in_ranges = [], None, False
    for line in text.splitlines():
        m = DD_DIE.match(line)
        if m:
            cur = None
            in_ranges = False
            if m.group(3) == "DW_TAG_inlined_subroutine":
                cur = {"ranges": [], "call_line": None, "lo": None, "hi": None}
                out.append(cur)
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("DW_AT_ranges"):
            in_ranges = True
            cur["ranges"] += [[int(a, 16), int(b, 16)] for a, b in DD_RANGE.findall(s)]
            continue
        if in_ranges and s.startswith("["):
            cur["ranges"] += [[int(a, 16), int(b, 16)] for a, b in DD_RANGE.findall(s)]
            continue
        in_ranges = False
        if s.startswith("DW_AT_low_pc"):
            cur["lo"] = int(re.search(r"\((0x[0-9a-f]+)", s).group(1), 16)
        elif s.startswith("DW_AT_high_pc"):
            cur["hi"] = int(re.search(r"\((0x[0-9a-f]+)", s).group(1), 16)
        elif s.startswith("DW_AT_call_line"):
            cur["call_line"] = int(re.search(r"\((\d+)\)", s).group(1))
    for c in out:
        if c["lo"] is not None and c["hi"] is not None:
            c["ranges"].append([c["lo"], c["hi"]])
    return [{"ranges": c["ranges"], "call_line": c["call_line"]} for c in out]


def stacks_from(base_ranges, frames):
    """Flatten into [start, end, [[file, line], ...]] per section, innermost frame first. base_ranges: the innermost
    line ranges {sec: [[start, end, file, line, depth]]}; frames: {sec: [[start, end, file, line, depth]]} outer frames
    (call sites of inlined code, depth = nesting depth of the inlined code they call)."""
    out = {}
    for sec in set(base_ranges) | set(frames):
        rs = base_ranges.get(sec, [])
        fs = frames.get(sec, [])
        pts = sorted({x for r in rs + fs for x in (r[0], r[1])})
        segs = []
        for a, b in zip(pts, pts[1:]):
            inner = [r for r in rs if r[0] <= a and b <= r[1]]
            outer = sorted([r for r in fs if r[0] <= a and b <= r[1]], key=lambda r: -r[4])
            if not inner and not outer:
                continue
            st = ([[inner[-1][2], inner[-1][3]]] if inner else []) + [[r[2], r[3]] for r in outer]
            if segs and segs[-1][1] == a and segs[-1][2] == st:
                segs[-1][1] = b
            else:
                segs.append([a, b, st])
        out[sec] = segs
    return out


# ------------------------------------------------------------------------------------------- CodeView
def _hex(s):
    return int(s, 16)


def parse_codeview(text):
    """Parse `llvm-readobj --codeview`. Returns (procs, inlinee_lines, errors).
    procs: {linkage: {"sym": name, "off": int, "size": int, "lines": [[off, line, file]], "sites": [...]}}
    site: {"inlinee_id": hex, "inlinee": name, "depth": d, "annots": [[op, args...]]}"""
    procs, inl, errors = {}, {}, []
    scope = []                       # stack of ("proc", rec) / ("block", None) / ("site", rec)
    cur_sym = None                   # the symbol record being read: dict
    in_annot = None
    flt = None                       # FunctionLineTable being read
    fl_file = None
    fl_entry = None
    inl_rec = None
    for raw in text.splitlines():
        line = raw.strip()
        if in_annot is not None:
            if line == "]":
                in_annot = None
                continue
            m = re.match(r"^(\w+): (.*)$", line)
            if m:
                op, arg = m.group(1), m.group(2)
                m2 = re.match(r"^\{CodeOffset: (0x[0-9A-Fa-f]+), (LineOffset|Length): (-?(?:0x)?[0-9A-Fa-f]+)\}$", arg)
                if m2:
                    a = _hex(m2.group(1))
                    b = int(m2.group(3), 16) if m2.group(3).lower().startswith(("0x", "-0x")) else int(m2.group(3))
                    in_annot["annots"].append([op, a, b])
                elif op == "ChangeFile":
                    in_annot["annots"].append([op, re.sub(r"\s*\(0x[0-9A-Fa-f]+\)$", "", arg)])
                else:
                    try:
                        v = int(arg, 16) if arg.lower().startswith(("0x", "-0x")) else int(arg)
                    except ValueError:
                        v = arg
                    in_annot["annots"].append([op, v])
            elif line != "(Annotation Padding)":
                errors.append("unparsed annotation line %r" % line)
            continue
        if line.startswith("FunctionLineTable ["):
            flt = {"lines": []}
            continue
        if flt is not None:
            if line.startswith("LinkageName:") and "linkage" not in flt:
                flt["linkage"] = line.split(":", 1)[1].strip()
            elif line.startswith("CodeSize:"):
                flt["size"] = _hex(line.split(":", 1)[1].strip())
            elif line.startswith("Filename:"):
                fl_file = re.sub(r"\s*\(0x[0-9A-Fa-f]+\)$", "", line.split(":", 1)[1].strip())
            elif re.match(r"^\+0x[0-9A-Fa-f]+ \[$", line):
                fl_entry = [_hex(line[1:].split()[0]), None, fl_file]
            elif line.startswith("LineNumberStart:") and fl_entry is not None:
                fl_entry[1] = int(line.split(":", 1)[1])
                flt["lines"].append(fl_entry)
                fl_entry = None
            elif raw.startswith("  ]") and not raw.startswith("   "):
                p = procs.setdefault(flt.get("linkage"), {})
                p.setdefault("lines", []).extend(flt["lines"])
                p["line_table_size"] = flt.get("size")
                flt = None
            continue
        if line.startswith("InlineeSourceLine {"):
            inl_rec = {}
            continue
        if inl_rec is not None:
            m = re.match(r"^Inlinee: (.*) \((0x[0-9A-Fa-f]+)\)$", line)
            if m:
                inl_rec["name"], inl_rec["id"] = m.group(1), m.group(2).lower()
            elif line.startswith("FileID:"):
                inl_rec["file"] = re.sub(r"\s*\(0x[0-9A-Fa-f]+\)$", "", line.split(":", 1)[1].strip())
            elif line.startswith("SourceLineNum:"):
                inl_rec["line"] = int(line.split(":", 1)[1])
            elif line == "}":
                if "id" in inl_rec:
                    inl[inl_rec["id"]] = inl_rec
                inl_rec = None
            continue
        m = re.match(r"^Kind: (S_[A-Z0-9_]+) \(0x([0-9A-Fa-f]+)\)$", line)
        if m:
            kind = m.group(1)
            if kind in ("S_GPROC32_ID", "S_LPROC32_ID", "S_GPROC32", "S_LPROC32", "S_LPROC32_DPC", "S_LPROC32_DPC_ID"):
                cur_sym = {"kind": "proc", "sites": []}
                scope.append(("proc", cur_sym))
            elif kind in ("S_BLOCK32", "S_THUNK32", "S_SEPCODE"):
                cur_sym = {"kind": "block"}
                scope.append(("block", cur_sym))
            elif kind in ("S_INLINESITE", "S_INLINESITE2"):
                proc = next((r for k, r in reversed(scope) if k == "proc"), None)
                depth = sum(1 for k, _ in scope if k == "site") + 1
                cur_sym = {"kind": "site", "depth": depth, "annots": []}
                if proc is None:
                    errors.append("inline site outside a procedure")
                else:
                    proc["sites"].append(cur_sym)
                scope.append(("site", cur_sym))
            elif kind in ("S_INLINESITE_END",):
                if not scope or scope[-1][0] != "site":
                    errors.append("unbalanced S_INLINESITE_END")
                else:
                    scope.pop()
                cur_sym = None
            elif kind in ("S_END", "S_PROC_ID_END"):
                if not scope or scope[-1][0] not in ("proc", "block"):
                    errors.append("unbalanced %s" % kind)
                else:
                    k, r = scope.pop()
                    if k == "proc":
                        nm = r.get("linkage") or r.get("display")
                        p = procs.setdefault(nm, {})
                        p.update({"sym": r.get("sym"), "off": r.get("off"), "size": r.get("size"), "sites": r["sites"]})
                cur_sym = None
            else:
                cur_sym = None
            continue
        if cur_sym is None:
            continue
        if cur_sym["kind"] == "proc":
            if line.startswith("CodeSize:"):
                cur_sym["size"] = _hex(line.split(":", 1)[1].strip())
            elif line.startswith("CodeOffset:"):
                v = line.split(":", 1)[1].strip()
                m2 = re.match(r"^(.*)\+(0x[0-9A-Fa-f]+)$", v)
                if m2:
                    cur_sym["sym"], cur_sym["off"] = m2.group(1), _hex(m2.group(2))
                else:
                    errors.append("unparsed procedure CodeOffset %r" % v)
            elif line.startswith("LinkageName:"):
                cur_sym["linkage"] = line.split(":", 1)[1].strip()
            elif line.startswith("DisplayName:"):
                cur_sym["display"] = line.split(":", 1)[1].strip()
        elif cur_sym["kind"] == "site":
            m2 = re.match(r"^Inlinee: (.*) \((0x[0-9A-Fa-f]+)\)$", line)
            if m2:
                cur_sym["inlinee"], cur_sym["inlinee_id"] = m2.group(1), m2.group(2).lower()
            elif line.startswith("BinaryAnnotations ["):
                in_annot = cur_sym
    if scope:
        errors.append("%d CodeView scopes left open" % len(scope))
    return procs, inl, errors


def site_rows(site, inl):
    """Rows [[start, end, file, line]] of one inline site (offsets relative to the procedure start)."""
    base = inl.get(site.get("inlinee_id") or "")
    if base is None:
        return None, "no InlineeLines entry for %s" % site.get("inlinee")
    line, fname = base["line"], base.get("file")
    off = 0
    rows, open_row, errs = [], None, []

    def close(at):
        if open_row is not None:
            if at > open_row[0]:
                rows.append([open_row[0], at, open_row[1], open_row[2]])
    for a in site["annots"]:
        op = a[0]
        if op == "ChangeLineOffset":
            line += a[1]
        elif op == "ChangeFile":
            fname = a[1]
        elif op in ("ChangeCodeOffset", "CodeOffset"):
            off = off + a[1] if op == "ChangeCodeOffset" else a[1]
            close(off)
            open_row = [off, fname, line]
        elif op == "ChangeCodeOffsetAndLineOffset":
            off += a[1]
            line += a[2]
            close(off)
            open_row = [off, fname, line]
        elif op == "ChangeCodeLength":
            if open_row is None:
                errs.append("ChangeCodeLength without an open row")
                continue
            end = open_row[0] + a[1]
            rows.append([open_row[0], end, open_row[1], open_row[2]])
            open_row = None
            off = end
        elif op == "ChangeCodeLengthAndCodeOffset":
            off += a[1]
            close(off)
            open_row = None
            rows.append([off, off + a[2], fname, line])
        elif op in ("ChangeLineEndDelta", "ChangeRangeKind", "ChangeColumnStart", "ChangeColumnEndDelta",
                    "ChangeColumnEnd"):
            continue
        else:
            errs.append("unsupported annotation %s" % op)
    if open_row is not None:
        errs.append("inline-site row at %#x has no end" % open_row[0])
    return rows, ("; ".join(errs) if errs else None)


def codeview_ranges(tobj, procs, inl):
    """{twin_section: [[start, end, file, line, depth]]}; errors."""
    symidx = {}
    for s in tobj["symbols"]:
        if s["defined"] and not s.get("is_section_symbol"):
            symidx.setdefault(s["name"], []).append(s)
    out, errors = {}, []
    for name, p in sorted(procs.items(), key=lambda kv: str(kv[0])):
        if p.get("sym") is None:
            continue
        hits = symidx.get(p["sym"], [])
        if len(hits) != 1:
            errors.append("procedure %s: symbol %s found %d times" % (name, p["sym"], len(hits)))
            continue
        sec, base = hits[0]["section"], hits[0]["value"] + p["off"]
        size = p.get("size") or p.get("line_table_size") or 0
        lines = sorted(p.get("lines", []), key=lambda x: x[0])
        for i, (o, ln, fn) in enumerate(lines):
            nxt = next((x[0] for x in lines[i + 1:] if x[0] > o), size)
            if nxt > o and ln:
                out.setdefault(sec, []).append([base + o, base + nxt, os.path.basename(fn.replace("\\", "/")), ln, 0])
        for site in p.get("sites", []):
            rows, err = site_rows(site, inl)
            if err:
                errors.append("procedure %s, inline site %s: %s" % (name, site.get("inlinee"), err))
            for (a, b, fn, ln) in rows or []:
                if a < 0 or b > size or b <= a:
                    errors.append("procedure %s, inline site %s: row [%#x,%#x) outside the procedure (size %#x)" % (
                        name, site.get("inlinee"), a, b, size))
                    continue
                out.setdefault(sec, []).append([base + a, base + b, os.path.basename((fn or "?").replace("\\", "/")),
                                                ln, site["depth"]])
    return out, errors


def stacks_all(ranges):
    """CodeView: per segment, one frame per depth (the later-listed range at equal depth), innermost first."""
    pts = sorted({x for r in ranges for x in (r[0], r[1])})
    segs = []
    for a, b in zip(pts, pts[1:]):
        by_depth = {}
        for r in ranges:
            if r[0] <= a and b <= r[1]:
                by_depth[r[4]] = r
        if not by_depth:
            continue
        st = [[by_depth[d][2], by_depth[d][3]] for d in sorted(by_depth, reverse=True)]
        if segs and segs[-1][1] == a and segs[-1][2] == st:
            segs[-1][1] = b
        else:
            segs.append([a, b, st])
    return segs


def innermost(ranges):
    """Flatten overlapping [start, end, file, line, depth] ranges: the deepest range wins; at equal depth the
    later-listed range wins. Returns sorted non-overlapping ranges."""
    pts = sorted({x for r in ranges for x in (r[0], r[1])})
    out = []
    for a, b in zip(pts, pts[1:]):
        best = None
        for k, r in enumerate(ranges):
            if r[0] <= a and b <= r[1]:
                if best is None or (r[4], k) >= (best[0], best[1]):
                    best = (r[4], k, r)
        if best is not None:
            r = best[2]
            if out and out[-1][1] == a and out[-1][2:] == [r[2], r[3], r[4]]:
                out[-1][1] = b
            else:
                out.append([a, b, r[2], r[3], r[4]])
    return out


# ------------------------------------------------------------------------------------------- source side
def _blank_comments_strings(t):
    def keep_nl(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    t = re.sub(r"/\*.*?\*/", keep_nl, t, flags=re.S)
    t = re.sub(r"//[^\n]*", keep_nl, t)
    t = re.sub(r'"(?:\\.|[^"\\\n])*"', keep_nl, t)
    t = re.sub(r"'(?:\\.|[^'\\\n])*'", keep_nl, t)
    return t


def _line_of(t, i):
    return t.count("\n", 0, i) + 1


def _match(t, i, o, c):
    d = 0
    for j in range(i, len(t)):
        if t[j] == o:
            d += 1
        elif t[j] == c:
            d -= 1
            if d == 0:
                return j
    return len(t) - 1


def _skip_ws(t, i):
    while i < len(t) and t[i].isspace():
        i += 1
    return i


def _statement_end(t, i):
    """Index of the last character of the statement starting at i."""
    i = _skip_ws(t, i)
    if t.startswith("{", i):
        return _match(t, i, "{", "}")
    m = re.match(r"(for|while|if|switch)\b", t[i:])
    if m:
        j = _skip_ws(t, i + len(m.group(1)))
        j = _match(t, j, "(", ")")
        e = _statement_end(t, j + 1)
        if m.group(1) == "if":
            k = _skip_ws(t, e + 1)
            if re.match(r"else\b", t[k:]):
                return _statement_end(t, k + 4)
        return e
    m = re.match(r"do\b", t[i:])
    if m:
        e = _statement_end(t, i + 2)
        k = _skip_ws(t, e + 1)
        if t.startswith("while", k):
            j = _match(t, _skip_ws(t, k + 5), "(", ")")
            k2 = _skip_ws(t, j + 1)
            return k2 if t.startswith(";", k2) else j
        return e
    d = 0
    for j in range(i, len(t)):
        if t[j] in "([{":
            d += 1
        elif t[j] in ")]}":
            d -= 1
        elif t[j] == ";" and d <= 0:
            return j
    return len(t) - 1


def source_regions(path):
    """Loops ([kind, header_line, start_line, end_line]) and function definitions ({name: [start, end]})."""
    with open(path, encoding="utf-8", errors="replace") as f:
        t = _blank_comments_strings(f.read())
    loops, loop_vars = [], {}
    for m in re.finditer(r"\b(for|while|do)\b", t):
        kind, i = m.group(1), m.start()
        if kind == "while":                       # the tail of a do-while is not a loop of its own
            k = i - 1
            while k >= 0 and t[k].isspace():
                k -= 1
            if k >= 0 and t[k] == "}":
                o = _match(t[::-1], len(t) - 1 - k, "}", "{")
                ob = len(t) - 1 - o
                b = ob - 1
                while b >= 0 and t[b].isspace():
                    b -= 1
                if t[max(0, b - 1): b + 1] == "do":
                    continue
        e = _statement_end(t, i)
        loops.append([kind, _line_of(t, i), _line_of(t, i), _line_of(t, e)])
        if kind == "for":                         # x0final revision: the induction variable of the init clause
            mv = re.match(r"for\s*\(\s*(?:[A-Za-z_]\w*\s+|\*\s*)*([A-Za-z_]\w*)\s*=", t[i:i + 200])
            if mv:
                loop_vars["%d" % _line_of(t, i)] = mv.group(1)
    funcs = {}
    for m in re.finditer(r"(?m)^[A-Za-z_][\w \t\*]*?\b([A-Za-z_]\w*)\s*\(([^;{}()]|\([^()]*\))*\)\s*\{", t):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        ob = m.end() - 1
        funcs.setdefault(name, [_line_of(t, m.start(1)), _line_of(t, _match(t, ob, "{", "}"))])
    return {"loops": loops, "functions": funcs, "loop_vars": loop_vars}


# ------------------------------------------------------------------------------------------- main
def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return p.returncode, p.stdout, p.stderr


OBJDUMP_LINE = re.compile(r"^\s*([0-9a-f]+):\s")


def objdump_starts(objdump, path, tobj):
    rc, out, err = run([objdump, "-d", "--no-show-raw-insn", path])
    if rc != 0:
        return None, "llvm-objdump failed: %s" % err.strip()[:200]
    order = [s for s in tobj["sections"] if s and s["is_code"] and s["size"] > 0]
    res, k, cur = {}, -1, None
    for line in out.splitlines():
        if line.startswith("Disassembly of section "):
            k += 1
            nm = line[len("Disassembly of section "):].rstrip(":")
            if k >= len(order) or order[k]["name"] != nm:
                return None, "section order mismatch at %r" % nm
            cur = res.setdefault(order[k]["index"], set())
            continue
        m = OBJDUMP_LINE.match(line)
        if m and cur is not None and not line.rstrip().endswith(":"):
            cur.add(int(m.group(1), 16))
    return res, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--census", required=True)
    ap.add_argument("--twin", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--source-dir", action="append", default=[])
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--readobj")
    ap.add_argument("--dwarfdump")
    ap.add_argument("--objdump")
    ap.add_argument("--codeview-text", help="saved `llvm-readobj --codeview` output of the twin (instead of --readobj)")
    ap.add_argument("--dwarfdump-text", help="saved `llvm-dwarfdump --debug-line` output of the twin")
    ap.add_argument("--dwarfdump-info-text", help="saved `llvm-dwarfdump --debug-info` output of the twin")
    a = ap.parse_args()
    cobj, tobj = x0obj.parse_object(a.census), x0obj.parse_object(a.twin)
    ident, pair = identity(cobj, tobj)
    out = {"census_object": os.path.abspath(a.census), "census_sha256": sha256_bytes(cobj["data"]),
           "twin_object": os.path.abspath(a.twin), "twin_sha256": sha256_bytes(tobj["data"]),
           "source": os.path.abspath(a.source), "format": cobj["format"], "identity": ident,
           "lines": {}, "line_table": {"ok": False, "errors": []}, "tools": {}}
    if cobj["format"] != tobj["format"]:
        out["line_table"]["errors"].append("census and twin formats differ")
    errors = out["line_table"]["errors"]
    ranges, stacks = {}, {}
    if tobj["format"].startswith("coff"):
        out["debug_format"] = "codeview"
        if a.codeview_text:
            text = open(a.codeview_text, encoding="utf-8", errors="replace").read()
            out["tools"]["codeview_text"] = os.path.abspath(a.codeview_text)
        elif a.readobj:
            rc, text, err = run([a.readobj, "--codeview", a.twin])
            out["tools"]["readobj"] = a.readobj
            if rc != 0:
                errors.append("llvm-readobj --codeview failed: %s" % err.strip()[:200])
                text = ""
        else:
            text = ""
            errors.append("no --readobj or --codeview-text")
        procs, inl, perr = parse_codeview(text)
        errors += perr
        ranges, rerr = codeview_ranges(tobj, procs, inl)
        errors += rerr
        stacks = {s: stacks_all(lst) for s, lst in ranges.items()}
        out["line_table"]["procedures"] = sum(1 for p in procs.values() if p.get("sym"))
        out["line_table"]["inline_sites"] = sum(len(p.get("sites", [])) for p in procs.values())
    else:
        out["debug_format"] = "dwarf"
        tables, err = parse_debug_line(tobj)
        if err:
            errors.append(err)
            tables = []
        if a.dwarfdump_text:
            dd = open(a.dwarfdump_text, encoding="utf-8", errors="replace").read()
            out["tools"]["dwarfdump_text"] = os.path.abspath(a.dwarfdump_text)
        elif a.dwarfdump:
            rc, dd, e2 = run([a.dwarfdump, "--debug-line", a.twin])
            out["tools"]["dwarfdump"] = a.dwarfdump
            if rc != 0:
                errors.append("llvm-dwarfdump failed: %s" % e2.strip()[:200])
        else:
            dd = None
            errors.append("no --dwarfdump or --dwarfdump-text (the record's tool is required for the row check)")
        if dd is not None:
            ddt = parse_dwarfdump_rows(dd)
            mine = [[[r[1], r[2], r[3], r[4]] for r in t["rows"]] for t in tables]
            if ddt != mine:
                n = sum(len(x) for x in ddt)
                errors.append("decoded rows differ from llvm-dwarfdump --debug-line (%d tables / %d rows vs %d / %d)" % (
                    len(mine), sum(len(x) for x in mine), len(ddt), n))
            out["line_table"]["rows_compared_with_dwarfdump"] = sum(len(x) for x in ddt)
        ranges, unext = dwarf_ranges(tables)
        out["line_table"]["rows_without_extent"] = unext
        # inline frames (call sites) from .debug_info, cross-checked with llvm-dwarfdump --debug-info
        frames = {}
        infos, ierr = parse_inlined(tobj, tables[0]["files"] if tables else [])
        if ierr:
            errors.append(ierr)
            infos = []
        if a.dwarfdump_info_text:
            ddi = open(a.dwarfdump_info_text, encoding="utf-8", errors="replace").read()
        elif a.dwarfdump:
            rc, ddi, e3 = run([a.dwarfdump, "--debug-info", a.twin])
            if rc != 0:
                errors.append("llvm-dwarfdump --debug-info failed: %s" % e3.strip()[:200])
                ddi = None
        else:
            ddi = None
        if ddi is not None:
            ddl = parse_dwarfdump_inlined(ddi)
            mine = [{"ranges": sorted([r[1], r[2]] for r in x["ranges"]), "call_line": x["call_line"]} for x in infos]
            theirs = [{"ranges": sorted(x["ranges"]), "call_line": x["call_line"]} for x in ddl]
            if mine != theirs:
                k = next((i for i, (m1, m2) in enumerate(zip(mine, theirs)) if m1 != m2), min(len(mine), len(theirs)))
                errors.append("inlined subroutines differ from llvm-dwarfdump --debug-info (%d vs %d; first at %d)" % (
                    len(mine), len(theirs), k))
            out["line_table"]["inlined_subroutines_compared_with_dwarfdump"] = len(theirs)
        for x in infos:
            if x.get("error"):
                errors.append("inlined subroutine: %s" % x["error"])
            for sec_i, s0, e0 in x["ranges"]:
                if sec_i is None:
                    errors.append("inlined subroutine range without a section")
                    continue
                if e0 > s0 and x["call_line"]:
                    frames.setdefault(sec_i, []).append([s0, e0, os.path.basename((x["call_file"] or "?").replace("\\", "/")),
                                                         x["call_line"], x["depth"]])
        stacks = stacks_from(ranges, frames)
        out["line_table"]["rows_without_section"] = sum(1 for t in tables for r in t["rows"] if r[0] is None and not r[4])
    # boundary self-check against llvm-objdump instruction starts of the twin
    if a.objdump:
        starts, err = objdump_starts(a.objdump, a.twin, tobj)
        out["tools"]["objdump"] = a.objdump
        if err:
            errors.append(err)
        else:
            bad = [[s, r[0]] for s, lst in ranges.items() for r in lst if r[0] not in starts.get(s, set())]
            out["line_table"]["row_starts_checked"] = sum(len(v) for v in ranges.values())
            out["line_table"]["row_starts_not_instruction_starts"] = bad[:50]
            if bad:
                errors.append("%d line-table row starts are not instruction starts of the twin" % len(bad))
    # map twin sections to census sections
    exact_secs = {s["twin_index"]: s for s in ident["sections"] if s.get("twin_index") is not None}
    for tsec, lst in sorted(ranges.items()):
        s = exact_secs.get(tsec)
        if s is None:
            continue
        if not s["identical"] and not s.get("size_equal"):
            continue
        out["lines"][str(s["census_index"])] = innermost(lst)
        out.setdefault("stacks", {})[str(s["census_index"])] = stacks.get(tsec, [])
    out["line_table"]["ok"] = not errors
    # source side
    srcs = {os.path.basename(a.source): a.source}
    named = {r[2] for lst in out["lines"].values() for r in lst}
    for d in a.source_dir:
        for nm in named:
            p = os.path.join(d, nm)
            if nm not in srcs and os.path.isfile(p):
                srcs[nm] = p
    out["sources"] = {}
    for nm, p in sorted(srcs.items()):
        b = open(p, "rb").read()
        reg = source_regions(p)
        out["sources"][nm] = {"path": os.path.abspath(p), "git_blob_sha1": x0_extract.git_blob_sha1(b),
                              "loops": reg["loops"], "functions": reg["functions"], "loop_vars": reg["loop_vars"]}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({"identical": ident["identical"],
                      "sections": len(ident["sections"]),
                      "identical_sections": sum(1 for s in ident["sections"] if s["identical"]),
                      "line_table_ok": out["line_table"]["ok"], "errors": errors[:10],
                      "ranges": sum(len(v) for v in out["lines"].values())}))
    return 0 if out["line_table"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
