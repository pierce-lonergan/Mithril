#!/usr/bin/env python3
"""X0 independent re-derivation, v2 (POST-COMPARISON: carried locations restricted to those live into the
header, record 4.7; written after census.json was read; v1 = rederive_x0.py is the frozen independent script) (record docs/m0/prereg/X0-census.md section 7, V3; rederive/PROCEDURE.md).

Written by an independent-context agent (same family, Claude) that has NOT read x0_extract.py, x0_decode.py,
x0_loops.py, x0_twin.py, judge.py, the census decode dumps, loops.json, attr/ files or census.json before producing
its own figures.  Standard library only.  Run with `python -I`.

Inputs (only): the frozen record's rules; the census objects of every main-union configuration and build and the
debug-info twins (copied into an empty directory with a SHA-256 manifest); class/fp_class.csv, class/loop_table.csv,
class/xed_tables.tsv, class/objdump_norm.csv; Hearth b5d3f14 sources; the stdarch XML; pinned XED and LLVM tools.

Subcommands
  stage    copy objects + twins from a census run directory into an empty input directory, write manifest
  run      compute everything, write figures.json and rederive_detail.json
  dumpxed  (debug) decode one section of one object with XED and print the raw output
"""
import argparse, bisect, collections, csv, hashlib, json, os, re, shutil, struct, subprocess, sys, tempfile

CONFIGS = ["A", "A-ninja", "B-cmake", "C", "D"]
FILES = ["quant.c", "quant_avx2.c", "quant_avx512.c"]
TABLE_FILE = {"hx_kernels_scalar": "quant.c", "k_avx2": "quant_avx2.c", "k_avx512": "quant_avx512.c"}
TABLE_CODE = {"hx_kernels_scalar": "scalar", "k_avx2": "avx2", "k_avx512": "avx512"}

# ----------------------------------------------------------------------------------------------------------------
# Object model
# ----------------------------------------------------------------------------------------------------------------

class Sec:
    def __init__(s, idx, name, data, execu, size=None):
        s.idx, s.name, s.data, s.execu = idx, name, data, execu
        s.size = len(data) if size is None else size
        s.relocs = []          # list of Rel, sorted by offset
        s.comdat_sym = None
        s.assoc = None         # COFF associative section number

class Sym:
    def __init__(s, idx, name, value, sec, kind, bind, size=0, vis="default", storage=None):
        s.idx, s.name, s.value, s.sec, s.kind, s.bind, s.size, s.vis, s.storage = \
            idx, name, value, sec, kind, bind, size, vis, storage
    def __repr__(s):
        return "Sym(%s,%s,%s,%s)" % (s.name, s.value, s.sec, s.kind)

class Rel:
    __slots__ = ("off", "type", "sym", "addend", "size")
    def __init__(s, off, typ, sym, addend, size):
        s.off, s.type, s.sym, s.addend, s.size = off, typ, sym, addend, size

COFF_REL = {1: "ADDR64", 2: "ADDR32", 3: "ADDR32NB", 4: "REL32", 5: "REL32_1", 6: "REL32_2", 7: "REL32_3",
            8: "REL32_4", 9: "REL32_5", 10: "SECTION", 11: "SECREL", 0: "ABSOLUTE"}
COFF_REL_SIZE = {"ADDR64": 8, "ADDR32": 4, "ADDR32NB": 4, "REL32": 4, "REL32_1": 4, "REL32_2": 4, "REL32_3": 4,
                 "REL32_4": 4, "REL32_5": 4, "SECTION": 2, "SECREL": 4, "ABSOLUTE": 0}
ELF_REL = {1: "64", 2: "PC32", 3: "GOT32", 4: "PLT32", 9: "GOTPCREL", 10: "32", 11: "32S", 24: "PC64",
           26: "GOTPC32", 41: "GOTPCRELX", 42: "REX_GOTPCRELX", 0: "NONE"}
ELF_REL_SIZE = {"64": 8, "PC32": 4, "GOT32": 4, "PLT32": 4, "GOTPCREL": 4, "32": 4, "32S": 4, "PC64": 8,
                "GOTPC32": 4, "GOTPCRELX": 4, "REX_GOTPCRELX": 4, "NONE": 0}


class Obj:
    def __init__(o, path):
        o.path = path
        with open(path, "rb") as f:
            o.raw = f.read()
        o.sha256 = hashlib.sha256(o.raw).hexdigest()
        o.secs = {}
        o.syms = []
        if o.raw[:4] == b"\x7fELF":
            o.fmt = "elf"
            o._elf()
        else:
            o.fmt = "coff"
            o._coff()
        o._index()

    # ---- ELF64 little endian ----
    def _elf(o):
        r = o.raw
        (e_shoff,) = struct.unpack_from("<Q", r, 0x28)
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", r, 0x3A)
        shdrs = []
        for i in range(e_shnum):
            shdrs.append(struct.unpack_from("<IIQQQQIIQQ", r, e_shoff + i * e_shentsize))
        shstr = shdrs[e_shstrndx]
        def sname(off, tab):
            end = r.index(b"\0", tab[4] + off)
            return r[tab[4] + off:end].decode("latin-1")
        o.elf_shdrs = shdrs
        for i, h in enumerate(shdrs):
            name = sname(h[0], shstr)
            typ, flags, off, size = h[1], h[2], h[4], h[5]
            data = r[off:off + size] if typ != 8 else b""
            o.secs[i] = Sec(i, name, data, bool(flags & 4), size)
            o.secs[i].elf_type = typ
            o.secs[i].elf_flags = flags
        # symbols
        symtab = [i for i, h in enumerate(shdrs) if h[1] == 2]
        if symtab:
            st = shdrs[symtab[0]]
            strtab = shdrs[st[6]]
            n = st[5] // 24
            for k in range(n):
                st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from("<IBBHQQ", r, st[4] + k * 24)
                name = sname(st_name, strtab)
                kind = {0: "notype", 1: "object", 2: "func", 3: "section", 4: "file"}.get(st_info & 15, "other")
                bind = {0: "local", 1: "global", 2: "weak"}.get(st_info >> 4, "other")
                vis = {0: "default", 1: "internal", 2: "hidden", 3: "protected"}[st_other & 3]
                sec = st_shndx if 0 < st_shndx < 0xff00 else None
                if kind == "section" and sec is not None:
                    name = o.secs[sec].name
                o.syms.append(Sym(k, name, st_value, sec, kind, bind, st_size, vis))
        # relocations
        for i, h in enumerate(shdrs):
            if h[1] == 4:  # SHT_RELA
                tgt = h[7]
                n = h[5] // 24
                rl = []
                for k in range(n):
                    off, info, add = struct.unpack_from("<QQq", r, h[4] + k * 24)
                    t = ELF_REL.get(info & 0xffffffff, "T%d" % (info & 0xffffffff))
                    rl.append(Rel(off, t, o.syms[info >> 32], add, ELF_REL_SIZE.get(t, 4)))
                o.secs[tgt].relocs.extend(rl)
        for s in o.secs.values():
            s.relocs.sort(key=lambda x: x.off)

    # ---- COFF (and bigobj) ----
    def _coff(o):
        r = o.raw
        big = struct.unpack_from("<HH", r, 0) == (0, 0xFFFF)
        if big:
            nsec = struct.unpack_from("<I", r, 44)[0]
            symptr, nsym = struct.unpack_from("<II", r, 48)
            hdr = 56
            symsize = 20
        else:
            machine, nsec, _, symptr, nsym, optsz, _ = struct.unpack_from("<HHIIIHH", r, 0)
            hdr = 20 + optsz
            symsize = 18
        strtab_off = symptr + nsym * symsize
        def longname(off):
            end = r.index(b"\0", strtab_off + off)
            return r[strtab_off + off:end].decode("latin-1")
        raw_secs = []
        for i in range(nsec):
            b = hdr + i * 40
            nm = r[b:b + 8].rstrip(b"\0").decode("latin-1")
            if nm.startswith("/"):
                nm = longname(int(nm[1:]))
            vsize, vaddr, rsize, rptr, relptr, lnptr, nrel, nln, ch = struct.unpack_from("<IIIIIIHHI", r, b + 8)
            if ch & 0x01000000 and nrel == 0xFFFF:   # IMAGE_SCN_LNK_NRELOC_OVFL
                nrel = struct.unpack_from("<I", r, relptr)[0]
                relptr += 10
                nrel -= 1
            data = r[rptr:rptr + rsize] if rptr else b"\0" * rsize
            s = Sec(i + 1, nm, data, bool(ch & 0x20000020), rsize)
            s.coff_ch = ch
            o.secs[i + 1] = s
            raw_secs.append((s, relptr, nrel))
        # symbols
        k = 0
        symbyidx = {}
        while k < nsym:
            b = symptr + k * symsize
            if r[b:b + 4] == b"\0\0\0\0":
                nm = longname(struct.unpack_from("<I", r, b + 4)[0])
            else:
                nm = r[b:b + 8].rstrip(b"\0").decode("latin-1")
            if big:
                value, secno, typ, sc, naux = struct.unpack_from("<IiHBB", r, b + 8)
            else:
                value, secno, typ, sc, naux = struct.unpack_from("<IhHBB", r, b + 8)
            sec = secno if secno > 0 else None
            kind = "func" if (typ >> 4) == 2 else ("section" if (sc == 3 and value == 0 and sec is not None
                                                                 and nm == o.secs[sec].name and naux >= 1) else "other")
            bind = "global" if sc == 2 else ("local" if sc in (3, 6) else "other")
            sy = Sym(k, nm, value, sec, kind, bind, 0, "default", sc)
            if kind == "section" and naux >= 1:
                ab = b + symsize
                ln, nr, nl, cs, num_lo, sel = struct.unpack_from("<IHHIHB", r, ab)
                num = num_lo
                if big:
                    num |= struct.unpack_from("<H", r, ab + 15)[0] << 16 if False else 0
                o.secs[sec].comdat_sel = sel
                if sel == 5:
                    o.secs[sec].assoc = num
            if secno == 0 and sc == 2:
                sy.sec = None  # undefined external (or common)
            symbyidx[k] = sy
            o.syms.append(sy)
            k += 1 + naux
        o.coff_symbyidx = symbyidx
        for s, relptr, nrel in raw_secs:
            for j in range(nrel):
                va, si, t = struct.unpack_from("<IIH", r, relptr + j * 10)
                tn = COFF_REL.get(t, "T%d" % t)
                sz = COFF_REL_SIZE.get(tn, 4)
                if sz == 8:
                    add = struct.unpack_from("<q", s.data, va)[0]
                elif sz == 4:
                    add = struct.unpack_from("<i", s.data, va)[0]
                elif sz == 2:
                    add = struct.unpack_from("<h", s.data, va)[0]
                else:
                    add = 0
                s.relocs.append(Rel(va, tn, symbyidx[si], add, sz))
            s.relocs.sort(key=lambda x: x.off)
        # COMDAT leader symbols (first symbol after the section symbol with the same section)
        for sy in o.syms:
            if sy.sec and sy.kind != "section" and o.secs[sy.sec].comdat_sym is None and \
                    getattr(o.secs[sy.sec], "comdat_sel", 0) not in (0, 5):
                o.secs[sy.sec].comdat_sym = sy

    def _index(o):
        o.relidx = {}
        for s in o.secs.values():
            o.relidx[s.idx] = ([x.off for x in s.relocs], s.relocs)
        o.by_name = collections.defaultdict(list)
        for sy in o.syms:
            o.by_name[sy.name].append(sy)

    def rel_at(o, secidx, off, end=None):
        """Relocations whose field starts in [off, end)."""
        offs, rl = o.relidx[secidx]
        if end is None:
            end = off + 1
        i = bisect.bisect_left(offs, off)
        out = []
        while i < len(offs) and offs[i] < end:
            out.append(rl[i])
            i += 1
        return out

    def exec_secs(o):
        return [s for s in o.secs.values() if s.execu and s.size > 0]

    def defined_funcs(o):
        return [sy for sy in o.syms if sy.kind == "func" and sy.sec is not None]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()

# ----------------------------------------------------------------------------------------------------------------
# XED
# ----------------------------------------------------------------------------------------------------------------

class Insn:
    __slots__ = ("sec", "off", "len", "iclass", "iform", "cat", "ext", "f", "ops", "text", "bytes")
    def end(i):
        return i.off + i.len
    def __repr__(i):
        return "%s+%x:%s" % (i.sec, i.off, i.text)


def parse_xed(text, secidx, base):
    """Parse `xed -64 -cet -ir file -b base -v 4` output into Insn objects keyed by offset."""
    out = {}
    cur_hdr, cur_ops = None, []
    for line in text.splitlines():
        if not line:
            continue
        if line.startswith("XDIS "):
            m = re.match(r"XDIS ([0-9a-fA-F]+): (\S+)\s+(\S+)\s+([0-9A-F]+)\s+(.*)$", line)
            if not m or cur_hdr is None:
                cur_hdr, cur_ops = None, []
                continue
            off = int(m.group(1), 16)
            ins = Insn()
            ins.sec, ins.off = secidx, off
            ins.bytes = bytes.fromhex(m.group(4))
            ins.len = len(ins.bytes)
            ins.cat, ins.ext, ins.text = m.group(2), m.group(3), m.group(5).strip()
            ins.iclass, ins.iform, ins.f = cur_hdr
            ins.ops = cur_ops
            out[off] = ins
            cur_hdr, cur_ops = None, []
        elif line.startswith("YDIS:"):
            continue
        elif line[0].isdigit() and "\t\t" in line:
            parts = line.split("\t\t", 1)[1].split("/")
            cur_ops.append(tuple(parts))
        elif line[0].isupper() and not line.startswith("XED") and " " in line:
            sp = line.split(" ", 2)
            if len(sp) >= 2 and re.match(r"^[A-Z0-9_]+$", sp[0]) and re.match(r"^[A-Za-z0-9_]+$", sp[1]):
                fields = {}
                if len(sp) == 3:
                    for kv in sp[2].split(", "):
                        if ":" in kv:
                            k, v = kv.split(":", 1)
                            fields[k] = v
                        else:
                            fields[kv] = True
                cur_hdr, cur_ops = (sp[0], sp[1], fields), []
    return out


class Xed:
    def __init__(x, exe, tmpdir):
        x.exe, x.tmp = exe, tmpdir
        x.calls = 0

    def sweep(x, data, secidx, base):
        fn = os.path.join(x.tmp, "sweep.bin")
        with open(fn, "wb") as f:
            f.write(data)
        x.calls += 1
        p = subprocess.run([x.exe, "-64", "-cet", "-v", "4", "-b", hex(base), "-ir", fn],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        txt = p.stdout.decode("latin-1")
        return parse_xed(txt, secidx, base), txt

# ----------------------------------------------------------------------------------------------------------------
# C source: tokenizer, struct layout, dispatch tables, loops, functions
# ----------------------------------------------------------------------------------------------------------------

TOK_RE = re.compile(r"[A-Za-z_]\w*|0[xX][0-9a-fA-F]+[uUlL]*|\d+\.?\d*(?:[eE][+-]?\d+)?[fFuUlL]*|\.\d+[fF]?|"
                    r"->|\+\+|--|<<=|>>=|<<|>>|<=|>=|==|!=|&&|\|\||[+\-*/%&|^]=|\S")


def c_tokens(text):
    """Tokens with line numbers; comments, strings, char literals and preprocessor lines removed."""
    out = []
    i, n, line = 0, len(text), 1
    at_bol = True
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1; i += 1; at_bol = True; continue
        if c in " \t\r\f\v":
            i += 1; continue
        if at_bol and c == "#":
            while i < n and text[i] != "\n":
                if text[i] == "\\" and i + 1 < n and text[i + 1] == "\n":
                    line += 1; i += 2; continue
                if text.startswith("/*", i):
                    j = text.index("*/", i + 2); line += text.count("\n", i, j); i = j + 2; continue
                i += 1
            continue
        at_bol = False
        if text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        if text.startswith("/*", i):
            j = text.index("*/", i + 2); line += text.count("\n", i, j); i = j + 2; continue
        if c == '"' or c == "'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(("STR", line)); i = j + 1; continue
        m = TOK_RE.match(text, i)
        out.append((m.group(0), line))
        i = m.end()
    return out


def match_brackets(toks):
    pairs, stack = {}, []
    for k, (t, _) in enumerate(toks):
        if t in ("(", "{", "["):
            stack.append(k)
        elif t in (")", "}", "]"):
            j = stack.pop(); pairs[j] = k; pairs[k] = j
    return pairs


class Source:
    def __init__(s, name, text):
        s.name, s.text = name, text
        s.toks = c_tokens(text)
        s.pairs = match_brackets(s.toks)
        s.funcs = []      # (name, start_line, end_line)
        s.loops = []      # dict(id, kw, start, end, func, var)
        s._functions()
        s._loops()

    def _functions(s):
        T, P = s.toks, s.pairs
        k = 0
        while k < len(T):
            if T[k][0] == "{":
                j = k - 1
                if j >= 0 and T[j][0] == ")":
                    o = P[j]
                    nm = T[o - 1][0] if o > 0 else "?"
                    s.funcs.append((nm, T[o - 1][1], T[P[k]][1]))
                k = P[k] + 1
                continue
            k += 1

    def func_at(s, line):
        for nm, a, b in s.funcs:
            if a <= line <= b:
                return nm
        return None

    def stmt_end(s, i):
        T, P = s.toks, s.pairs
        t = T[i][0]
        if t == "{":
            return P[i]
        if t in ("for", "while", "switch"):
            return s.stmt_end(P[i + 1] + 1)
        if t == "do":
            k = s.stmt_end(i + 1)
            w = k + 1
            p = P[w + 1]
            return p + 1
        if t == "if":
            k = s.stmt_end(P[i + 1] + 1)
            if k + 1 < len(T) and T[k + 1][0] == "else":
                return s.stmt_end(k + 2)
            return k
        if t == "else":
            return s.stmt_end(i + 1)
        j = i
        while T[j][0] != ";":
            if T[j][0] in ("(", "{", "["):
                j = P[j]
            j += 1
        return j

    def _loops(s):
        T, P = s.toks, s.pairs
        dotails = set()
        for k, (t, ln) in enumerate(T):
            if t == "do":
                e = s.stmt_end(k + 1)
                dotails.add(e + 1)
        for k, (t, ln) in enumerate(T):
            if t in ("for", "while", "do") and k not in dotails:
                var = None
                if t != "do" and (k + 1 >= len(T) or T[k + 1][0] != "("):
                    continue
                e = s.stmt_end(k)
                if t == "for":
                    c = P[k + 1]
                    j = k + 2
                    first = []
                    while j < c and T[j][0] != ";":
                        first.append(T[j][0]); j += 1
                    if "=" in first:
                        q = first.index("=")
                        if q >= 1:
                            var = first[q - 1]
                s.loops.append({"id": "%s:%d" % (s.name, ln), "kw": t, "start": ln, "end": T[e][1],
                                "func": s.func_at(ln), "var": var})

    def innermost_loop(s, line):
        best = None
        for L in s.loops:
            if L["start"] <= line <= L["end"]:
                if best is None or (L["start"], -L["end"]) > (best["start"], -best["end"]):
                    best = L
        return best

    def loop_by_id(s, lid):
        for L in s.loops:
            if L["id"] == lid:
                return L
        return None


def struct_layout(hdr_text):
    """Field offsets of struct hx_kernels from hx_quant.h (int, pointer, pointer arrays only)."""
    m = re.search(r"typedef\s+struct\s+hx_kernels\s*\{(.*?)\}\s*hx_kernels\s*;", hdr_text, re.S)
    body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    off, fields = 0, {}
    for decl in [d.strip() for d in body.split(";") if d.strip()]:
        fm = re.match(r"[\w\s]+\(\s*\*\s*(\w+)\s*\)", decl)
        am = re.match(r"(\w+)\s+(\w+)\s*\[\s*(\d+)\s*\]$", decl)
        im = re.match(r"int\s+(\w+)$", decl)
        if fm:
            size, align, name, n = 8, 8, fm.group(1), 1
        elif am:
            size, align, name, n = 8, 8, am.group(2), int(am.group(3))   # array of function-pointer typedef
        elif im:
            size, align, name, n = 4, 4, im.group(1), 1
        else:
            raise SystemExit("unhandled struct field: %r" % decl)
        off = (off + align - 1) // align * align
        fields[name] = (off, size, n)
        off += size * n
    return fields


def dtype_names(hearth_h):
    m = re.search(r"HEARTH_F32\s*=\s*0.*?HEARTH_U8\s*=\s*6", hearth_h, re.S)
    names = {}
    for nm, v in re.findall(r"HEARTH_(\w+)\s*=\s*(\d+)", m.group(0)):
        names[int(v)] = nm
    return names


def source_tables(srcs, layout, dtn):
    """The three table initialisers -> list of (table, slot, function name, field offset, file)."""
    out = []
    for fname, src in srcs.items():
        text = re.sub(r"/\*.*?\*/", "", src.text, flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
        for m in re.finditer(r"(?:static\s+)?const\s+hx_kernels\s+(\w+)\s*=\s*\{", text):
            tname = m.group(1)
            i = m.end()
            depth, j = 1, i
            while depth:
                if text[j] == "{": depth += 1
                elif text[j] == "}": depth -= 1
                j += 1
            inner = text[i:j - 1]
            arr = re.search(r"\{([^{}]*)\}", inner)
            mm = [x.strip() for x in arr.group(1).split(",")]
            rest = [x.strip() for x in inner[arr.end():].split(",") if x.strip()]
            off_mm = layout["matmul"][0]
            for k, fn in enumerate(mm):
                if fn and fn != "NULL":
                    out.append((tname, "matmul[%s]" % dtn[k], fn, off_mm + 8 * k, fname))
            if rest and rest[0] != "NULL":
                out.append((tname, "act_quantize_q8", rest[0], layout["act_quantize_q8"][0], fname))
    return out

# ----------------------------------------------------------------------------------------------------------------
# Class files and the intrinsic baseline
# ----------------------------------------------------------------------------------------------------------------

def load_fp_class(path):
    d = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d[row["iclass"]] = (row["fp_sensitive"] == "yes", row["op_class"])
    return d


def load_loop_table(path):
    rows = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["loop_id"]] = {"lanes": int(row["source_lanes"]), "variants": row["variants"].split("|"),
                                    "trip": row["trip_count"], "func": row["function"]}
    return rows


def load_xed_tables(path):
    iform_iclass, iclasses = {}, set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if p[0] == "IFORM":
                iform_iclass[p[1]] = p[2]
            elif p[0] == "ICLASS":
                iclasses.add(p[1])
    return iform_iclass, iclasses


def baseline(srcs_text, xml_path, iform_iclass):
    import xml.etree.ElementTree as ET
    names = set()
    for fn in ("quant_avx2.c", "quant_avx512.c"):
        names |= set(re.findall(r"_mm[0-9]*_[a-z0-9_]+", srcs_text[fn]))
    entries = {}
    for ev, el in ET.iterparse(xml_path, events=("end",)):
        if el.tag == "intrinsic":
            nm = el.get("name")
            if nm in names:
                entries[nm] = [(i.get("name"), i.get("form"), i.get("xed")) for i in el.findall("instruction")]
            el.clear()

    def kinds_of_form(form):
        out = []
        for t in [x.strip() for x in (form or "").split(",") if x.strip()]:
            t = t.split()[0].lower()
            if t.startswith("xmm"): out.append("xmm")
            elif t.startswith("ymm"): out.append("ymm")
            elif t.startswith("zmm"): out.append("zmm")
            elif t.startswith("imm"): out.append("imm")
            elif t.startswith("k"): out.append("k")
            elif t.startswith("m"): out.append("mem")
            elif t.startswith("r"): out.append("r")
            else: out.append(t)
        return out

    def kinds_of_iform(ifm):
        out = []
        for t in ifm.split("_")[1:]:
            u = t.upper()
            for pfx, k in (("XMM", "xmm"), ("YMM", "ymm"), ("ZMM", "zmm"), ("MEM", "mem"), ("IMM", "imm"),
                           ("MASK", "k"), ("GPR", "r")):
                if u.startswith(pfx):
                    out.append(k); break
        return out

    iforms, problems, hand, nosingle, per = set(), [], [], [], {}
    for nm in sorted(names):
        if nm not in entries:
            problems.append("no XML entry: " + nm); per[nm] = None; continue
        ins = entries[nm]
        if not ins:
            nosingle.append(nm); per[nm] = []; continue
        got = []
        for (iname, form, x) in ins:
            if x and x in iform_iclass:
                got.append(x)
            else:
                cands = [f for f, c in iform_iclass.items() if c == iname and kinds_of_iform(f) == kinds_of_form(form)]
                if len(cands) == 1:
                    got.append(cands[0]); hand.append((nm, iname, form, x, cands[0]))
                else:
                    problems.append("unmapped %s %s %s %s cands=%s" % (nm, iname, form, x, cands[:6]))
        per[nm] = sorted(set(got))
        iforms |= set(got)
    b_mnem = sorted({iform_iclass[f] for f in iforms})
    return {"n_names": len(names), "n_512": sum(1 for x in names if x.startswith("_mm512_")),
            "n_256": sum(1 for x in names if x.startswith("_mm256_")),
            "n_128": sum(1 for x in names if x.startswith("_mm_")),
            "no_single_instruction": sorted(nosingle), "b_iform": sorted(iforms), "b_mnem": b_mnem,
            "hand_map": hand, "problems": problems, "per_intrinsic": per}

# ----------------------------------------------------------------------------------------------------------------
# Instruction helpers
# ----------------------------------------------------------------------------------------------------------------

GPR_FAM = {}
for _b in ("AX", "BX", "CX", "DX"):
    for _n in ("R" + _b, "E" + _b, _b, _b[0] + "L", _b[0] + "H"):
        GPR_FAM[_n] = "r" + _b.lower()
for _b in ("SI", "DI", "SP", "BP"):
    for _n in ("R" + _b, "E" + _b, _b, _b + "L"):
        GPR_FAM[_n] = "r" + _b.lower()
for _i in range(8, 32):
    for _n in ("R%d" % _i, "R%dD" % _i, "R%dW" % _i, "R%dB" % _i):
        GPR_FAM[_n] = "r%d" % _i
PARTIAL_GPR = {n for n in GPR_FAM if re.match(r"^(?:[A-D][LHX]|SI|DI|SP|BP|SIL|DIL|SPL|BPL|R\d+[WB])$", n)}


def loc_of_reg(name):
    if name in GPR_FAM:
        return GPR_FAM[name]
    m = re.match(r"^[XYZ]MM(\d+)$", name)
    if m:
        return "v" + m.group(1)
    m = re.match(r"^K([0-7])$", name)
    if m:
        return "k" + m.group(1)
    return None


def parse_mem(s):
    """'ptr [RAX+RCX*4+0x10]' / 'ptr FS:[0x28]' -> dict(base, index, scale, disp, seg)."""
    if not isinstance(s, str) or "[" not in s:
        return None
    seg = None
    m = re.search(r"([A-Z]S):\[", s)
    if m:
        seg = m.group(1)
    inner = s[s.index("[") + 1:s.rindex("]")]
    base = index = None
    scale, disp = 1, 0
    for sign, tok in re.findall(r"([+-]?)([A-Za-z0-9_*]+)", inner):
        if tok.lower().startswith("0x") or tok.isdigit():
            v = int(tok, 16) if tok.lower().startswith("0x") else int(tok)
            disp += -v if sign == "-" else v
        elif "*" in tok:
            r, sc = tok.split("*")
            index, scale = r, int(sc)
        else:
            if base is None:
                base = tok
            else:
                index = tok
    return {"base": base, "index": index, "scale": scale, "disp": disp, "seg": seg}


def sval(v, bits=64):
    v = int(v, 16) if isinstance(v, str) else int(v)
    if v >= 1 << (bits - 1):
        v -= 1 << bits
    return v


def is_nop_class(ins):
    return ins.iclass.startswith("NOP") or ins.cat == "WIDENOP" or ins.iclass in ("FNOP",)


FMA_PREFIXES = ("VFMADD", "VFMSUB", "VFNMADD", "VFNMSUB", "VFMADDSUB", "VFMSUBADD")
APPROX = {"RCPPS", "RCPSS", "RSQRTPS", "RSQRTSS", "VRCPPS", "VRCPSS", "VRSQRTPS", "VRSQRTSS", "VRCPPH", "VRCPSH",
          "VRSQRTPH", "VRSQRTSH", "VRCPBF16", "VRSQRTBF16", "VEXP2PS", "VEXP2PD"}
NORETURN = {"__stack_chk_fail", "__stack_chk_fail_local", "abort", "exit", "_exit", "__assert_fail", "__chk_fail",
            "__fortify_fail", "longjmp", "__longjmp_chk", "_invalid_parameter_noinfo_noreturn", "__report_gsfailure",
            "__report_rangecheckfailure", "__fastfail", "ExitProcess"}
NONFP_ALLOW = {"memcpy", "memmove", "memset", "memcmp", "__memcpy_chk", "__memset_chk", "__memmove_chk",
               "__stack_chk_fail", "__stack_chk_fail_local", "__security_check_cookie", "__GSHandlerCheck", "__chkstk",
               "___chkstk_ms", "__report_rangecheckfailure", "__guard_check_icall_fptr"}


def is_fma(iclass):
    return iclass.startswith(FMA_PREFIXES)


def is_approx(iclass):
    return iclass in APPROX or iclass.startswith(("VRCP14", "VRSQRT14", "VRCP28", "VRSQRT28", "PFRCP", "PFRSQ"))


def ctl_kind(ins):
    ic = ins.iclass
    if ic in ("CALL_NEAR",):
        return "call"
    if ic == "JMP":
        return "jmp"
    if ic.startswith("RET"):
        return "ret"
    if ins.cat == "COND_BR":
        return "jcc"
    if ic in ("UD2", "UD0", "UD1", "INT3", "HLT"):
        return "trap"
    return "seq"


def branch_target_field(ins):
    if "RELBR" in ins.f:
        w = int(ins.f.get("BRDISP_WIDTH", "32"))
        return ins.end() + sval(ins.f["RELBR"], 64 if ins.f["RELBR"].startswith("0xffffffff") else w)
    return None


def reg_ops(ins):
    """[(loc, action, opname, width, lookup, regname)] for register operands with a tracked location."""
    out = []
    for op in ins.ops:
        nm = op[0]
        if nm.startswith("REG"):
            rn = ins.f.get(nm)
            if not isinstance(rn, str):
                continue
            loc = loc_of_reg(rn)
            if loc is None:
                continue
            lookup = op[-1] if len(op) >= 5 else ""
            out.append((loc, op[1], nm, op[2], lookup, rn))
    return out


def mem_ops(ins):
    out = []
    for op in ins.ops:
        nm = op[0]
        if nm.startswith("MEM") or nm == "AGEN":
            vis = op[3] if len(op) > 3 else ""
            m = parse_mem(ins.f.get(nm))
            if m is None:
                continue
            m["name"], m["action"], m["vis"], m["width"] = nm, op[1], vis, op[2]
            out.append(m)
    return out


def writemask(ins):
    """The EVEX write mask register name (None or K0 -> no masking)."""
    for loc, act, nm, w, lookup, rn in reg_ops(ins):
        if lookup == "MASK1" and rn != "K0":
            return loc
    return None


# ----------------------------------------------------------------------------------------------------------------
# Per-object analyzer: function ranges, decoding, closure
# ----------------------------------------------------------------------------------------------------------------

class Func:
    def __init__(f, name, sec, start, end, sym, names):
        f.name, f.sec, f.start, f.end, f.sym, f.names = name, sec, start, end, sym, names
        f.range_gap = None
        f.parent = None     # cold part -> parent name
    def __repr__(f):
        return "Func(%s,%s,%x-%x)" % (f.name, f.sec, f.start, f.end)


class Analyzer:
    def __init__(a, obj, xed, objdump_exe):
        a.o, a.xed, a.objdump = obj, xed, objdump_exe
        a.funcs = []
        a.by_start = {}
        a.sec_starts = collections.defaultdict(list)
        a.dec = {}
        a.decode_fail = {}
        a._ranges()
        for s in obj.exec_secs():
            ins, txt = xed.sweep(s.data, s.idx, 0)
            a.dec[s.idx] = ins
        a.swept_from = collections.defaultdict(set)

    # ---- function ranges (record 4.2 "Function bytes", "COFF function ranges") ----
    def _ranges(a):
        o = a.o
        groups = collections.defaultdict(list)
        for sy in o.defined_funcs():
            if o.secs[sy.sec].execu:
                groups[(sy.sec, sy.value)].append(sy)
        for (sec, val) in sorted(groups):
            syms = groups[(sec, val)]
            syms.sort(key=lambda s: (s.bind != "global", s.name))
            main = syms[0]
            f = Func(main.name, sec, val, None, main, [s.name for s in syms])
            f.sizes = [s.size for s in syms]
            a.funcs.append(f)
            a.sec_starts[sec].append(val)
        for sec in a.sec_starts:
            a.sec_starts[sec].sort()
        pdata = a._pdata() if o.fmt == "coff" else {}
        for f in a.funcs:
            sec = o.secs[f.sec]
            starts = a.sec_starts[f.sec]
            k = starts.index(f.start)
            nxt = starts[k + 1] if k + 1 < len(starts) else sec.size
            if o.fmt == "elf":
                sz = max(f.sizes)
                if sz > 0:
                    f.end = f.start + sz
                else:
                    f.end = nxt
                    f.range_gap = "ELF symbol size 0; range up to the next symbol"
                m = re.match(r"^(.*)\.cold(?:\.\d+)?$", f.name)
                if m:
                    f.parent = m.group(1)
            else:
                ents = sorted(pdata.get(f.sec, []))
                mine = [e for e in ents if f.start <= e[0] < nxt]
                comdat = getattr(sec, "comdat_sel", 0) not in (0, 5) or sec.comdat_sym is not None
                if len(starts) == 1 and f.start == 0 and comdat:
                    f.end = sec.size
                elif mine:
                    f.end = max(e[1] for e in mine)
                else:
                    f.end = nxt
                    f.range_gap = "COFF range up to the next function symbol"
                # .pdata cross-check
                if mine:
                    if mine[0][0] != f.start:
                        f.range_gap = "first .pdata entry does not begin at the symbol"
                    for e1, e2 in zip(mine, mine[1:]):
                        if e1[1] != e2[0]:
                            f.range_gap = ".pdata entries not contiguous"
                    if mine[-1][1] > f.end:
                        f.range_gap = ".pdata entry ends past the range"
            a.by_start[(f.sec, f.start)] = f
        a.fam = collections.defaultdict(list)
        for f in a.funcs:
            a.fam[f.parent or f.name].append(f)

    def _pdata(a):
        o = a.o
        out = collections.defaultdict(list)
        for s in o.secs.values():
            if s.name != ".pdata":
                continue
            rl = {r.off: r for r in s.relocs}
            for e in range(0, s.size - 11, 12):
                rb, re_ = rl.get(e), rl.get(e + 4)
                if not rb or not re_ or rb.sym.sec is None:
                    continue
                b = rb.sym.value + rb.addend
                en = re_.sym.value + re_.addend
                out[rb.sym.sec].append((b, en))
        return out

    def func_containing(a, sec, off):
        st = a.sec_starts.get(sec)
        if not st:
            return None
        k = bisect.bisect_right(st, off) - 1
        if k < 0:
            return None
        f = a.by_start[(sec, st[k])]
        if f.start <= off < f.end:
            return f
        return None

    def family(a, f):
        return a.fam[f.parent or f.name]

    # ---- decoding at arbitrary offsets ----
    def insn_at(a, sec, off):
        d = a.dec[sec]
        if off in d:
            return d[off]
        if off in a.swept_from[sec]:
            return None
        a.swept_from[sec].add(off)
        s = a.o.secs[sec]
        f = a.func_containing(sec, off)
        end = f.end if f else s.size
        ins, txt = a.xed.sweep(s.data[off:end], sec, off)
        for k, v in ins.items():
            if k not in d:
                d[k] = v
        return d.get(off)

    def objdump_len(a, sec, off):
        """llvm-objdump's instruction length at sec:off (None if it cannot decode)."""
        s = a.o.secs[sec]
        with tempfile.TemporaryDirectory() as td:
            fn = os.path.join(td, "b.bin")
            with open(fn, "wb") as fh:
                fh.write(s.data[off:off + 15])
            p = subprocess.run([a.objdump, "-D", "-b", "binary", "-m", "i386:x86-64", fn],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        txt = p.stdout.decode("latin-1")
        m = re.search(r"^\s*0:\s+((?:[0-9a-f]{2} )+)\s*(\S+)", txt, re.M)
        if not m or "unknown" in m.group(2) or "(bad)" in txt:
            return None
        return len(m.group(1).split())

    # ---- relocation-based target resolution ----
    def rel_target(a, ins, rel):
        """Target (sec, off) or ('ext', name) of a relocated displacement in an instruction."""
        o = a.o
        S = rel.sym
        P = rel.off
        end = ins.end()
        if o.fmt == "elf":
            if rel.type in ("PC32", "PLT32", "GOTPCREL", "GOTPCRELX", "REX_GOTPCRELX"):
                tgt = rel.addend + (end - P)
            else:
                tgt = rel.addend
        else:
            k = {"REL32": 0, "REL32_1": 1, "REL32_2": 2, "REL32_3": 3, "REL32_4": 4, "REL32_5": 5}.get(rel.type)
            if k is not None:
                tgt = rel.addend + (end - P - 4 - k)
            else:
                tgt = rel.addend
        if S.sec is None:
            return ("ext", S.name, tgt)
        return (S.sec, S.value + tgt, S)

    def disp_rel(a, ins):
        p = ins.f.get("POS_DISP")
        if p is None:
            return None
        r = a.o.rel_at(ins.sec, ins.off + int(p))
        return r[0] if r else None

    def imm_rel(a, ins):
        p = ins.f.get("POS_IMM")
        if p is None:
            return None
        r = a.o.rel_at(ins.sec, ins.off + int(p))
        return r[0] if r else None

    def call_kind(a, rel, tgt_func):
        """internal | interposable for a defined callee."""
        if a.o.fmt == "coff":
            return "internal"
        if rel is not None and rel.sym.kind == "func" and rel.sym.sec is not None:
            sy = rel.sym
            if sy.bind in ("global", "weak") and sy.vis in ("default", "protected"):
                return "interposable"
            return "internal"
        return "internal"

    # ---- recursive descent (record 4.2) ----
    def closure(a, entry, noret_internal=frozenset()):
        o = a.o
        R = {"funcs": collections.OrderedDict(), "reach": {}, "owner": {}, "gaps": [], "internal": set(),
             "external": set(), "interposable": set(), "tail": set(), "fp_deps": set(), "noret_inferred": [],
             "indirect": [], "jump_tables": [], "edges": collections.defaultdict(set), "rets": set(),
             "calls_at": {}}
        work = []

        def add_func(f, kind):
            fam = a.family(f)
            head = [g for g in fam if g.parent is None] or fam
            for g in fam:
                if g.name not in R["funcs"]:
                    R["funcs"][g.name] = (g, kind if g is f else ("cold_part_of:" + (g.parent or f.name)
                                                                if g.parent else kind))
                    if g.range_gap:
                        R["gaps"].append(("range_mismatch", g.sec, g.start, g.range_gap))
            work.append((f.sec, f.start, f))

        def in_family(F, sec, off):
            for g in a.family(F):
                if g.sec == sec and g.start <= off < g.end:
                    return g
            return None

        def handle_callee(ins, F, tgt, rel, is_tail):
            """tgt: (sec, off, sym?) or ('ext', name, add). Returns 'noreturn' or None."""
            if tgt[0] == "ext":
                nm = tgt[1]
                if nm.startswith("__imp_"):
                    nm = nm[6:]
                R["external"].add(nm)
                if nm not in NONFP_ALLOW:
                    R["fp_deps"].add(nm)
                    R["gaps"].append(("fp_trust_dep", ins.sec, ins.off, "external callee " + nm))
                if is_tail:
                    R["tail"].add(nm)
                return "noreturn" if nm in NORETURN else None
            sec, off = tgt[0], tgt[1]
            g = in_family(F, sec, off)
            if g is not None and is_tail:
                return "intra"
            f = a.by_start.get((sec, off))
            if f is None:
                fc = a.func_containing(sec, off)
                R["gaps"].append(("other", ins.sec, ins.off, "branch into the middle of %s" % (fc.name if fc else
                                                                                            "no function")))
                return None
            kind = a.call_kind(rel, f)
            R["internal" if kind == "internal" else "interposable"].add(f.name)
            if is_tail:
                R["tail"].add(f.name)
            add_func(f, kind)
            if f.name in noret_internal:
                return "noreturn"
            return None

        def padding_to_end(sec, off, F):
            g = in_family(F, sec, off - 1)
            end = g.end if g else off
            if off >= end:
                return True
            data = o.secs[sec].data[off:end]
            if all(b in (0xCC, 0x00) for b in data):
                return True
            p = off
            while p < end:
                i2 = a.insn_at(sec, p)
                if i2 is None or not (is_nop_class(i2) or i2.iclass == "INT3"):
                    return False
                p = i2.end()
            return True

        add_func(entry, "entry")
        while work:
            sec, off, F = work.pop()
            if (sec, off) in R["reach"]:
                continue
            ins = a.insn_at(sec, off)
            if ins is None:
                n = a.objdump_len(sec, off)
                R["gaps"].append(("xed_gap" if n else "both_decoders_fail", sec, off, "XED cannot decode"))
                continue
            R["reach"][(sec, off)] = ins
            R["owner"][(sec, off)] = F
            k = ctl_kind(ins)
            succ = []
            ft = True
            if k == "ret":
                ft = False
                R["rets"].add((sec, off))
            elif k == "trap":
                ft = False
            elif k in ("call", "jmp", "jcc"):
                is_tail = (k == "jmp")
                if ins.iform.endswith("RELBRb") or ins.iform.endswith("RELBRd") or ins.iform.endswith("RELBRz") or \
                        "RELBR" in ins.f:
                    rel = a.disp_rel(ins)
                    if rel is not None:
                        tgt = a.rel_target(ins, rel)
                    else:
                        t = branch_target_field(ins)
                        tgt = (sec, t, None)
                    if k == "call":
                        res = handle_callee(ins, F, tgt, rel, False)
                        R["calls_at"][(sec, off)] = tgt
                        if res == "noreturn":
                            ft = False
                        elif padding_to_end(sec, ins.end(), F):
                            ft = False
                            R["noret_inferred"].append((sec, off))
                    else:
                        if k == "jmp":
                            ft = False
                        if tgt[0] != "ext" and in_family(F, tgt[0], tgt[1]):
                            succ.append((tgt[0], tgt[1]))
                        else:
                            res = handle_callee(ins, F, tgt, rel, True)
                            R["calls_at"][(sec, off)] = tgt
                else:
                    # indirect
                    if k == "jmp":
                        ft = False
                    res = a.indirect(ins, F, R, k)
                    if res is None:
                        R["indirect"].append((sec, off, ins.text))
                        R["gaps"].append(("unresolved_indirect", sec, off, ins.text))
                    elif res[0] == "table":
                        R["jump_tables"].append(res[1])
                        for t in res[1]["targets"]:
                            succ.append((sec, t))
                    elif res[0] == "ext":
                        r2 = handle_callee(ins, F, ("ext", res[1], 0), None, k == "jmp")
                        R["calls_at"][(sec, off)] = ("ext", res[1], 0)
                        if k == "call" and r2 == "noreturn":
                            ft = False
                        elif k == "call" and padding_to_end(sec, ins.end(), F):
                            ft = False
                            R["noret_inferred"].append((sec, off))
            if ft:
                nxt = ins.end()
                gcur = in_family(F, sec, off)
                if gcur is None or nxt >= gcur.end:
                    R["gaps"].append(("other", sec, off, "execution falls off the end of the function range"))
                else:
                    succ.append((sec, nxt))
            for s2 in succ:
                R["edges"][(sec, off)].add(s2)
                g = in_family(F, s2[0], s2[1])
                if g is None:
                    R["gaps"].append(("other", sec, off, "successor outside the function family"))
                    continue
                work.append((s2[0], s2[1], F))
        # overlapping decodes
        keys = sorted(R["reach"])
        for k1, k2 in zip(keys, keys[1:]):
            if k1[0] == k2[0] and R["reach"][k1].end() > k2[1]:
                R["gaps"].append(("other", k1[0], k1[1], "overlapping decodes"))
        return R

    def indirect(a, ins, F, R, k):
        """Calls/jumps through memory or registers; jump tables in the recognised shapes."""
        o = a.o
        mops = [m for m in mem_ops(ins) if m["vis"] == "EXPLICIT"]
        if mops:
            m = mops[0]
            rel = a.disp_rel(ins)
            if m["base"] == "RIP" and m["index"] is None and rel is not None:
                nm = rel.sym.name
                if o.fmt == "coff" and nm.startswith("__imp_"):
                    return ("ext", nm[6:])
                if o.fmt == "elf" and rel.type in ("GOTPCREL", "GOTPCRELX", "REX_GOTPCRELX") and rel.sym.sec is None:
                    return ("ext", nm)
                if nm == "__guard_check_icall_fptr":
                    return ("ext", nm)
                return None
            if k == "jmp" and m["base"] is None and m["index"] and m["scale"] == 8 and rel is not None:
                return a.jump_table_mem(ins, F, rel, m)
            return None
        # register forms
        regs = [r for r in reg_ops(ins) if r[2] == "REG0"]
        if not regs:
            return None
        if k == "jmp":
            return a.jump_table_reg(ins, F, regs[0][5])
        return None

    def block_back(a, ins, F, limit=24):
        """Instructions of ins's basic block before ins, in straight-line address order (most recent first);
        stops at a control transfer."""
        out = []
        p = ins.off
        d = a.dec[ins.sec]
        cand = sorted(x for x in d if F.start <= x < p)
        cur = p
        for x in reversed(cand):
            if d[x].end() == cur:
                if ctl_kind(d[x]) != "seq":
                    break
                out.append(d[x]); cur = x
                if len(out) >= limit:
                    break
        return out

    def jump_table_reg(a, ins, F, reg):
        o = a.o
        back = a.block_back(ins, F)
        fam = GPR_FAM.get(reg)
        add = load = lea = None
        for b in back:
            rr = reg_ops(b)
            if add is None and b.iclass == "ADD" and rr and rr[0][0] == fam:
                add = b; continue
            if add is not None and load is None and b.iclass in ("MOVSXD", "MOV") and rr and rr[0][0] == fam:
                load = b; continue
        if add is None or load is None:
            return None
        lm = [m for m in mem_ops(load) if m["vis"] == "EXPLICIT"]
        if not lm or lm[0]["index"] is None or lm[0]["scale"] != 4:
            return None
        lm = lm[0]
        baseloc = GPR_FAM.get(lm["base"])
        idx = GPR_FAM.get(lm["index"])
        addsrc = [r for r in reg_ops(add) if r[2] == "REG1"]
        if not addsrc or addsrc[0][0] != baseloc:
            return None
        lrel = a.disp_rel(load)
        for b in back:
            rr = reg_ops(b)
            if b.iclass == "LEA" and rr and rr[0][0] == baseloc:
                lea = b; break
        if lea is None:
            return None
        rel = a.disp_rel(lea)
        if rel is None:
            return None
        tb = a.rel_target(lea, rel)
        if tb[0] == "ext":
            if o.fmt == "coff" and tb[1] == "__ImageBase" and lrel is not None:
                tsec, toff = lrel.sym.sec, lrel.sym.value + lrel.addend
                kind = "coff_addr32nb"
            else:
                return None
        else:
            tsec, toff = tb[0], tb[1]
            kind = "pc32"
        n = a.table_bound(ins, F, idx, back)
        if n is None:
            return None
        targets = []
        for e in range(n):
            P = toff + 4 * e
            rl = o.rel_at(tsec, P)
            if not rl:
                return None
            r = rl[0]
            if r.sym.sec is None:
                return None
            if kind == "pc32":
                t = r.sym.value + r.addend - (P - toff) if r.type == "PC32" else None
            else:
                t = r.sym.value + r.addend if r.type == "ADDR32NB" else None
            if t is None or r.sym.sec != ins.sec or a.func_containing(ins.sec, t) is None:
                return None
            targets.append(t)
        return ("table", {"site": (ins.sec, ins.off), "table": (tsec, toff), "n": n, "targets": targets})

    def jump_table_mem(a, ins, F, rel, m):
        o = a.o
        back = a.block_back(ins, F)
        idx = GPR_FAM.get(m["index"])
        n = a.table_bound(ins, F, idx, back)
        if n is None or rel.sym.sec is None:
            return None
        tsec, toff = rel.sym.sec, rel.sym.value + rel.addend
        targets = []
        for e in range(n):
            rl = o.rel_at(tsec, toff + 8 * e)
            if not rl or rl[0].sym.sec != ins.sec:
                return None
            targets.append(rl[0].sym.value + rl[0].addend)
        return ("table", {"site": (ins.sec, ins.off), "table": (tsec, toff), "n": n, "targets": targets})

    def table_bound(a, ins, F, idx, back):
        """Entry count from the bound guarding the index register (record 4.2, jump tables)."""
        fams = {idx}
        for b in back:          # most recent first, inside the jump's block
            rr = reg_ops(b)
            w = [r for r in rr if "W" in r[1] and r[0] in fams]
            if b.iclass == "AND" and rr and rr[0][0] in fams and "IMM0" in b.f:
                v = sval(b.f["IMM0"])
                if v > 0 and (v + 1) & v == 0:
                    return v + 1
            if w:
                src = [r for r in rr if r[1] == "R" and r[2] != w[0][2]]
                if b.iclass in ("MOVSXD", "MOVZX", "MOVSX", "MOV") and src and not mem_ops(b):
                    fams.add(src[0][0])
                    continue
                if b.iclass in ("MOVSXD", "MOVZX", "MOV") and not src:
                    return None
                return None
        start = back[-1].off if back else ins.off
        preds = []
        d = a.dec[ins.sec]
        for x, i2 in d.items():
            if not (F.start <= x < F.end):
                continue
            if i2.end() == start and x + i2.len == start:
                k = ctl_kind(i2)
                if k == "jcc":
                    preds.append((i2, "ft"))
                elif k == "seq" or k == "call":
                    preds.append((i2, "seq"))
            if i2.cat in ("COND_BR", "UNCOND_BR") and branch_target_field(i2) == start and a.disp_rel(i2) is None:
                preds.append((i2, "taken"))
        if len(preds) != 1 or preds[0][1] == "seq":
            return None
        br, how = preds[0]
        cb = a.block_back(br, F, 6)
        for b in cb:
            rr = reg_ops(b)
            if b.iclass == "CMP" and "IMM0" in b.f:
                if rr and rr[0][0] in fams and rr[0][5] not in PARTIAL_GPR:
                    imm = sval(b.f["IMM0"])
                    if br.iclass == "JNBE" and how == "ft":
                        return imm + 1
                    if br.iclass == "JNB" and how == "ft":
                        return imm
                    if br.iclass == "JBE" and how == "taken":
                        return imm + 1
                    if br.iclass == "JB" and how == "taken":
                        return imm
                return None
            if any("W" in r[1] and r[0] in fams for r in rr):
                return None
        return None


# ----------------------------------------------------------------------------------------------------------------
# Loops (record 4.7) and P3(c)
# ----------------------------------------------------------------------------------------------------------------

MOVES = {"MOV", "MOVAPS", "MOVUPS", "MOVAPD", "MOVUPD", "MOVDQA", "MOVDQU", "MOVSS", "MOVSD_XMM", "MOVD", "MOVQ",
         "VMOVAPS", "VMOVUPS", "VMOVAPD", "VMOVUPD", "VMOVDQA", "VMOVDQU", "VMOVDQA32", "VMOVDQA64", "VMOVDQU8",
         "VMOVDQU16", "VMOVDQU32", "VMOVDQU64", "VMOVSS", "VMOVSD", "VMOVD", "VMOVQ", "KMOVW", "KMOVB", "KMOVD",
         "KMOVQ", "LDDQU", "VLDDQU"}
PASSTHRU = {"SQRTSS", "SQRTSD", "RCPSS", "RSQRTSS", "ROUNDSS", "ROUNDSD", "CVTSI2SS", "CVTSI2SD", "CVTSS2SD",
            "CVTSD2SS", "MOVSS", "MOVSD_XMM", "VSQRTSS", "VSQRTSD", "VRCPSS", "VRSQRTSS", "VROUNDSS", "VROUNDSD",
            "VCVTSI2SS", "VCVTSI2SD", "VCVTUSI2SS", "VCVTUSI2SD", "VCVTSS2SD", "VCVTSD2SS", "VMOVSS", "VMOVSD",
            "VRCP14SS", "VRCP14SD", "VRSQRT14SS", "VRSQRT14SD", "VRNDSCALESS", "VRNDSCALESD", "VGETEXPSS",
            "VGETEXPSD"}
IDIOM_ZERO = {"XOR", "SUB", "XORPS", "XORPD", "PXOR", "VXORPS", "VXORPD", "VPXOR", "VPXORD", "VPXORQ", "PSUBB",
              "PSUBW", "PSUBD", "PSUBQ", "VPSUBB", "VPSUBW", "VPSUBD", "VPSUBQ", "PCMPGTB", "PCMPGTW", "PCMPGTD",
              "PCMPGTQ", "VPCMPGTB", "VPCMPGTW", "VPCMPGTD", "VPCMPGTQ"}
IDIOM_ONES = {"PCMPEQB", "PCMPEQW", "PCMPEQD", "PCMPEQQ", "VPCMPEQB", "VPCMPEQW", "VPCMPEQD", "VPCMPEQQ"}
SELECTS = {"BLENDVPS", "BLENDVPD", "VBLENDVPS", "VBLENDVPD", "VBLENDMPS", "VBLENDMPD", "VPBLENDMD", "VPBLENDMQ",
           "PBLENDVB", "VPBLENDVB"}
ANDS = {"ANDPS", "ANDPD", "PAND", "VANDPS", "VANDPD", "VPAND", "VPANDD", "VPANDQ"}
ANDNS = {"ANDNPS", "ANDNPD", "PANDN", "VANDNPS", "VANDNPD", "VPANDN", "VPANDND", "VPANDNQ"}
ORS = {"ORPS", "ORPD", "POR", "VORPS", "VORPD", "VPOR", "VPORD", "VPORQ", "XORPS", "XORPD", "VXORPS", "VXORPD"}
SYSV_CLOBBER = ["rax", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11"] + ["v%d" % i for i in range(32)]
WIN64_CLOBBER = ["rax", "rcx", "rdx", "r8", "r9", "r10", "r11"] + ["v%d" % i for i in range(6)] + \
    ["v%d" % i for i in range(16, 32)]


def lanes_of(ins, iclass=None):
    ic = iclass or ins.iclass
    if re.search(r"(SS|SD|SH)$", ic) and not ic.startswith(("VPMOV", "PMOV")):
        return 1
    vl = ins.f.get("VL")
    bits = {"0": 128, "1": 256, "2": 512}.get(str(vl), 128) if "VEXVALID" in ins.f else 128
    if ic.endswith("PD") or ic.endswith("MQ"):
        return bits // 64
    return bits // 32


def sem(ins, ctx):
    """Data semantics of one instruction for the carried-value analysis.
    Returns (reads, writes, merge_locs, fresh_load, kind) where reads are data locations, writes are written
    locations, merge_locs are written locations whose old value survives, fresh_load is True when a non-stack
    memory value is read, kind in {'idiom', 'move', 'call', 'op'}."""
    ic = ins.iclass
    rops = reg_ops(ins)
    mops = mem_ops(ins)
    wm = writemask(ins)
    reads, writes, merge = [], [], set()
    fresh = False
    kind = "op"
    if ic == "CALL_NEAR":
        return [], list(ctx["clobber"]), set(), False, "call"
    # explicit / implicit memory operands
    for m in mops:
        if m["name"] == "AGEN":
            for r in (m["base"], m["index"]):
                if r and loc_of_reg(r):
                    reads.append(loc_of_reg(r))
            continue
        if m["vis"] == "SUPPRESSED":
            continue
        slot = stack_slot(m, ctx)
        if "R" in m["action"]:
            if slot:
                reads.append(slot)
            else:
                fresh = True
        if "W" in m["action"]:
            if slot:
                writes.append(slot)
                if "C" in m["action"]:
                    merge.add(slot)
    # register operands
    data_srcs = []
    for loc, act, nm, w, lookup, rn in rops:
        if lookup == "MASK1":
            continue                      # write mask: predicate, not data
        if "R" in act:
            data_srcs.append((loc, nm, rn))
        if "W" in act:
            writes.append(loc)
            if "C" in act or rn in PARTIAL_GPR:
                merge.add(loc)
    srcs_regs = [x[0] for x in data_srcs]
    # dependency-breaking idioms
    explicit = [(loc, act, nm, rn) for loc, act, nm, w, lookup, rn in rops if lookup != "MASK1" and
                not lookup.startswith(("RFLAGS",))]
    exp_regs = [rn for loc, act, nm, w, lookup, rn in rops if lookup not in ("MASK1",) and nm.startswith("REG")
                and loc is not None and not rn.startswith("K")] if False else None
    if (ic in IDIOM_ZERO or ic in IDIOM_ONES) and not mops and "IMM0" not in ins.f and wm is None:
        names = [rn for loc, act, nm, w, lookup, rn in rops if lookup != "MASK1" and loc_of_reg(rn)
                 and not rn.startswith("K")]
        if names and len(set(names)) == 1:
            return [], [loc_of_reg(names[0])], set(), False, "idiom"
    # scalar unary / insert-style: only the last source reaches lane 0
    if ic in PASSTHRU:
        regsrc = [x for x in data_srcs]
        if mops and any(m["vis"] != "SUPPRESSED" and "R" in m["action"] for m in mops):
            reads = [r for r in reads if r.startswith(("stk", "rbp"))]
            srcs_regs = []
        else:
            last = regsrc[-1][0] if regsrc else None
            srcs_regs = [last] if last else []
        for wl in list(merge):
            if wl.startswith("v"):
                merge.discard(wl)
        if ic in ("MOVSS", "MOVSD_XMM", "VMOVSS", "VMOVSD") and wm is None:
            kind = "move"
    elif ic in MOVES and wm is None:
        kind = "move"
    reads = reads + srcs_regs
    return reads, writes, merge, fresh, kind


def stack_slot(m, ctx):
    """A constant-offset, non-escaping stack slot (record 4.7).  A slot at or above the lowest displacement of an
    indexed access or an address computation (LEA) on the same base anywhere in the function escapes."""
    if m["index"] is not None or m["seg"] is not None:
        return None
    if m["base"] == "RSP" and ctx["rsp_ok"] and m["disp"] < ctx.get("esc_rsp", 1 << 40):
        return "stk%+d" % m["disp"]
    if m["base"] == "RBP" and ctx["rbp_ok"] and m["disp"] < ctx.get("esc_rbp", 1 << 40):
        return "rbp%+d" % m["disp"]
    return None


def stack_escapes(reach):
    esc = {"RSP": 1 << 40, "RBP": 1 << 40}
    for ins in reach.values():
        for m in mem_ops(ins):
            if m["vis"] == "SUPPRESSED" or m["base"] not in esc:
                continue
            if m["name"] == "AGEN" or m["index"] is not None:
                esc[m["base"]] = min(esc[m["base"]], m["disp"])
    return esc["RSP"], esc["RBP"]


def build_cfg(R, fam_funcs):
    """Basic blocks of the reachable instructions of one function family."""
    reach = {k: v for k, v in R["reach"].items() if R["owner"][k].name in fam_funcs}
    if not reach:
        return None
    succ = collections.defaultdict(set)
    pred = collections.defaultdict(set)
    for k in reach:
        for s2 in R["edges"].get(k, ()):
            if s2 in reach:
                succ[k].add(s2); pred[s2].add(k)
    leaders = set()
    for k in reach:
        if len(pred[k]) != 1:
            leaders.add(k)
        else:
            p = next(iter(pred[k]))
            if len(succ[p]) != 1 or reach[p].end() != k[1]:
                leaders.add(k)
    for k in reach:
        if len(succ[k]) > 1:
            for s2 in succ[k]:
                leaders.add(s2)
    blocks = {}
    bof = {}
    for l in sorted(leaders):
        cur = l
        insns = []
        while True:
            insns.append(cur)
            bof[cur] = l
            ss = succ[cur]
            if len(ss) != 1:
                break
            n = next(iter(ss))
            if n in leaders or n[1] != reach[cur].end() or n[0] != cur[0]:
                break
            cur = n
        blocks[l] = insns
    bsucc = {l: {bof[s2] for s2 in succ[b[-1]]} for l, b in blocks.items()}
    bpred = collections.defaultdict(set)
    for l, ss in bsucc.items():
        for s2 in ss:
            bpred[s2].add(l)
    return {"reach": reach, "blocks": blocks, "bsucc": bsucc, "bpred": bpred, "bof": bof}


def dominators(cfg, entry):
    blocks = cfg["blocks"]
    order, seen = [], set()
    stack = [(entry, iter(sorted(cfg["bsucc"][entry])))]
    seen.add(entry)
    while stack:
        n, it = stack[-1]
        nxt = next(it, None)
        if nxt is None:
            order.append(n); stack.pop()
        elif nxt not in seen:
            seen.add(nxt); stack.append((nxt, iter(sorted(cfg["bsucc"][nxt]))))
    rpo = list(reversed(order))
    idx = {n: i for i, n in enumerate(rpo)}
    idom = {entry: entry}
    changed = True
    while changed:
        changed = False
        for n in rpo[1:]:
            ps = [p for p in cfg["bpred"][n] if p in idom]
            if not ps:
                continue
            new = ps[0]
            for p in ps[1:]:
                a, b = p, new
                while a != b:
                    while idx[a] > idx[b]:
                        a = idom[a]
                    while idx[b] > idx[a]:
                        b = idom[b]
                new = a
            if idom.get(n) != new:
                idom[n] = new; changed = True
    def dom(a, b):     # a dominates b
        while True:
            if a == b:
                return True
            if b == entry or b not in idom:
                return False
            b = idom[b]
    return dom, set(rpo)


def natural_loops(cfg, entry):
    dom, reachable = dominators(cfg, entry)
    loops = {}
    for t in reachable:
        for h in cfg["bsucc"][t]:
            if h in reachable and dom(h, t):
                loops.setdefault(h, set()).add(t)
    out = []
    for h, latches in loops.items():
        body = {h}
        stack = [t for t in latches]
        while stack:
            n = stack.pop()
            if n in body:
                continue
            body.add(n)
            for p in cfg["bpred"][n]:
                if p in reachable:
                    stack.append(p)
        out.append({"header": h, "latches": sorted(latches), "body": body})
    return out


def analyse_loop(L, cfg, fpc, abi):
    """Emitted accumulator lanes of one natural loop (record 4.7, as read by the re-deriver)."""
    blocks = cfg["blocks"]
    reach = cfg["reach"]
    body = L["body"]
    h = L["header"]
    # stack-slot admissibility
    rsp_ok, rbp_ok = True, True
    for b in body:
        for k in blocks[b]:
            ins = reach[k]
            for loc, act, nm, w, lookup, rn in reg_ops(ins):
                if "W" in act and loc == "rsp" and ins.iclass not in ("PUSH", "POP", "CALL_NEAR", "RET_NEAR"):
                    rsp_ok = False
                if "W" in act and loc == "rbp":
                    rbp_ok = False
    ctx = {"rsp_ok": rsp_ok, "rbp_ok": rbp_ok, "clobber": SYSV_CLOBBER if abi == "sysv" else WIN64_CLOBBER}
    if "esc" not in cfg:
        cfg["esc"] = stack_escapes(reach)
    ctx["esc_rsp"], ctx["esc_rbp"] = cfg["esc"]
    S = {}
    W = set()
    for b in body:
        for k in blocks[b]:
            S[k] = sem(reach[k], ctx)
            W |= set(S[k][1])
    W = {w for w in W if not w.startswith("k")}

    def is_accum_op(ins):
        ic = ins.iclass
        if is_fma(ic):
            return True
        fs, oc = fpc.get(ic, (True, ic))
        return fs and oc.split(".")[0] in ("ADD", "SUB", "MUL", "MAX", "MIN")

    # forward data flow over one iteration (edges into the header cut), to a fixpoint
    # state: loc -> (origin frozenset, prov frozenset, cls, cmp, part)
    intern_tab = {}
    def interned(x):
        return intern_tab.setdefault(x, len(intern_tab))
    def run_df(Wc):
        readorig = set()
        init = {l: (frozenset([l]), frozenset(), ("H", l), None, None) for l in Wc}
        order = sorted(body)
        instate = {h: init}
        outstate = {}
        accums = {}
        changed = True
        rounds = 0
        while changed and rounds < 50:
            changed = False
            rounds += 1
            for b in order:
                if b == h:
                    st = dict(init)
                else:
                    preds = [p for p in cfg["bpred"][b] if p in body and p in outstate]
                    if not preds:
                        continue
                    st = {}
                    keys = set()
                    for p in preds:
                        keys |= set(outstate[p])
                    for l in keys:
                        vals = [outstate[p].get(l) for p in preds]
                        vals = [v for v in vals if v is not None]
                        if len(vals) == 1:
                            st[l] = vals[0]
                        else:
                            o = frozenset().union(*[v[0] for v in vals])
                            pv = frozenset().union(*[v[1] for v in vals])
                            clss = {v[2] for v in vals}
                            if len(clss) == 1:
                                cl = vals[0][2]
                            else:
                                pairs = []
                                for p_ in preds:
                                    c_ = outstate[p_].get(l, (None, None, None))[2]
                                    if isinstance(c_, tuple) and c_[0] == "phi" and c_[1] == b:
                                        continue
                                    pairs.append((p_, interned(c_)))
                                cl = ("phi", b, interned(tuple(sorted(pairs))))
                            cm = vals[0][3] if all(v[3] == vals[0][3] for v in vals) else None
                            pt = vals[0][4] if all(v[4] == vals[0][4] for v in vals) else None
                            st[l] = (o, pv, cl, cm, pt)
                for k in blocks[b]:
                    ins = reach[k]
                    reads, writes, merge, fresh, kind = S[k]
                    ins_o = frozenset().union(*[st.get(r, (frozenset(),))[0] for r in reads]) if reads else frozenset()
                    ins_p = frozenset().union(*[st.get(r, (None, frozenset()))[1] for r in reads]) if reads else frozenset()
                    if kind not in ("idiom", "call"):
                        readorig.update(ins_o)
                    ic = ins.iclass
                    acc = False
                    lanes = 0
                    newcmp = newpart = None
                    if kind not in ("idiom", "call", "move") and is_accum_op(ins) and (ins_o & Wc):
                        acc, lanes = True, lanes_of(ins)
                    # compare producing a mask
                    fs, oc = fpc.get(ic, (True, ic))
                    if oc.split(".")[0] == "CMP" and fs and not ic.endswith(("COMISS", "COMISD")):
                        newcmp = (k, ins_o, ins_p, lanes_of(ins))
                    # selects
                    wm = writemask(ins)
                    if not acc and kind != "idiom":
                        maskloc = None
                        if ic in SELECTS:
                            if ic in ("BLENDVPS", "BLENDVPD", "PBLENDVB"):
                                maskloc = "v0"
                            elif ic.startswith("VBLENDM") or ic.startswith("VPBLENDM"):
                                maskloc = wm
                            else:
                                rr = [r for r in reg_ops(ins) if r[1] == "R" and r[0].startswith("v")]
                                maskloc = rr[-1][0] if rr else None
                        elif wm is not None and ic in MOVES and any(r[1] == "RCW" for r in reg_ops(ins)):
                            maskloc = wm
                        if maskloc is not None:
                            cm = st.get(maskloc, (None,) * 5)[3]
                            if cm is not None:
                                data = [r for r in reads if r != maskloc]
                                d_o = frozenset().union(*[st.get(r, (frozenset(),))[0] for r in data]) if data else frozenset()
                                d_p = frozenset().union(*[st.get(r, (None, frozenset()))[1] for r in data]) if data else frozenset()
                                if (d_o & cm[1] & Wc) or (d_p & cm[2]):
                                    acc, lanes = True, lanes_of(ins)
                        # SSE2 and/andn/or select
                        if ic in ANDS or ic in ANDNS:
                            for r in reads:
                                cm = st.get(r, (None,) * 5)[3]
                                if cm is not None:
                                    newpart = (cm, "and" if ic in ANDS else "andn")
                                    break
                        if ic in ORS and len(set(reads)) == 2:
                            parts = [st.get(r, (None,) * 5)[4] for r in reads]
                            if all(parts) and parts[0][0] == parts[1][0] and {parts[0][1], parts[1][1]} == {"and", "andn"}:
                                cm = parts[0][0]
                                if (ins_o & cm[1] & Wc) or (ins_p & cm[2]):
                                    acc, lanes = True, cm[3]
                    if acc:
                        accums[k] = lanes
                        ins_p = ins_p | {k}
                    # copy class
                    for wl in writes:
                        if kind == "call":
                            val = (frozenset(), frozenset(), ("def", k, wl), None, None)
                        elif kind == "idiom":
                            val = (frozenset(), frozenset(), ("def", k, wl), None, None)
                        else:
                            o = ins_o
                            p = ins_p
                            if kind == "move" and len(reads) == 1:
                                cl = st.get(reads[0], (None, None, ("def", k, wl)))[2]
                                cmv = st.get(reads[0], (None,) * 5)[3]
                                ptv = st.get(reads[0], (None,) * 5)[4]
                            elif acc:
                                cl, cmv, ptv = ("def", k), None, None
                            else:
                                tainted_cls = {st[r][2] for r in reads if r in st and st[r][1]}
                                cl = next(iter(tainted_cls)) if len(tainted_cls) == 1 and p else ("def", k, wl)
                                cmv, ptv = newcmp, newpart
                            if fresh and not reads:
                                o, p = frozenset(), frozenset()
                            if wl in merge and wl in st:
                                old = st[wl]
                                o, p = o | old[0], p | old[1]
                                cl = ("merge", k, wl)
                            val = (o, p, cl, cmv, ptv)
                        st[wl] = val
                if outstate.get(b) != st:
                    outstate[b] = st
                    changed = True
        return outstate, accums, readorig

    # pass 1: which written locations have their header value read at all (live into the header along the
    # back edge); pass 2: the analysis over those carried locations only (v2, added after the comparison)
    _o1, _a1, live = run_df(W)
    W = {l for l in W if l in live}
    outstate, accums, _r2 = run_df(W)
    # carried-location graph at the latches
    latch_states = []
    for t in L["latches"]:
        if t in outstate:
            latch_states.append(outstate[t])
    nodes = sorted(W)
    edges = {n: set() for n in nodes}
    tainted = set()
    for st in latch_states:
        for r in nodes:
            v = st.get(r)
            if v is None:
                continue
            for s2 in v[0]:
                if s2 in edges:
                    edges[s2].add(r)
            if v[1]:
                tainted.add(r)
    # Tarjan SCC
    index, low, onst, stack, sccs = {}, {}, set(), [], []
    counter = [0]
    def strong(v):
        index[v] = low[v] = counter[0]; counter[0] += 1
        stack.append(v); onst.add(v)
        for w in edges[v]:
            if w not in index:
                strong(w); low[v] = min(low[v], low[w])
            elif w in onst:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop(); onst.discard(w); comp.append(w)
                if w == v:
                    break
            sccs.append(comp)
    sys.setrecursionlimit(10000)
    for v in nodes:
        if v not in index:
            strong(v)
    total = 0
    parts = []
    for comp in sccs:
        cyc = len(comp) > 1 or comp[0] in edges[comp[0]]
        tc = [r for r in comp if r in tainted]
        if not cyc or not tc:
            continue
        groups = {}
        provs = set()
        for r in tc:
            key = tuple((st.get(r, (None, frozenset(), None))[1], st.get(r, (None, None, None))[2])
                        for st in latch_states)
            groups.setdefault(key, []).append(r)
            for st in latch_states:
                provs |= set(st.get(r, (None, frozenset()))[1])
        unt = [r for r in comp if r not in tainted]
        widest = max([accums.get(p, 0) for p in provs] or [0])
        n_parts = len(groups) + len(unt)
        total += n_parts * widest
        parts.append({"locations": sorted(comp), "tainted": sorted(tc), "partial_results": n_parts,
                      "lanes": widest, "accumulations": sorted("%x" % p[1] for p in provs)})
    return {"acc_lanes_emitted": total, "cycles": parts, "rsp_ok": rsp_ok, "rbp_ok": rbp_ok,
            "stack_escape_from": {"rsp": ctx["esc_rsp"] if ctx["esc_rsp"] < (1 << 40) else None,
                                  "rbp": ctx["esc_rbp"] if ctx["esc_rbp"] < (1 << 40) else None}}

# ----------------------------------------------------------------------------------------------------------------
# P3(d1) canary: (v + M) - M in act_q8_scalar's closure
# ----------------------------------------------------------------------------------------------------------------

M_POS, M_NEG = 0x4B400000, 0xCB400000


def const_at(an, ins, m):
    """Constant 32-bit lanes read by memory operand m of ins (None if not a relocated constant)."""
    rel = an.disp_rel(ins)
    if rel is None:
        return None
    t = an.rel_target(ins, rel)
    if t[0] == "ext":
        return None
    sec = an.o.secs[t[0]]
    width = {"D": 4, "SS": 4, "DQ": 16, "PS": 16, "XUD": 16, "QQ": 32, "ZD": 64, "VV": 64, "Q": 8, "SD": 8,
             "ZF32": 64}.get(m["width"], 4)
    if "{1to" in ins.text:
        width = 4
    data = sec.data[t[1]:t[1] + width]
    if len(data) < 4:
        return None
    vals = {struct.unpack_from("<I", data, i)[0] for i in range(0, len(data) - 3, 4)}
    return vals.pop() if len(vals) == 1 else ("mixed",)


def canary_d1(an, R):
    """Address-order scan over the closure; pass if ADD of M is followed by SUB M (or ADD -M) reading its result
    through moves only, with the sum as the minuend."""
    regs = {}
    sums = {}
    found = []
    n_add = 0
    for key in sorted(R["reach"]):
        ins = R["reach"][key]
        ic = ins.iclass
        rops = [r for r in reg_ops(ins) if r[4] != "MASK1"]
        mops = [m for m in mem_ops(ins) if m["vis"] == "EXPLICIT" and m["name"] != "AGEN"]
        dst = [r for r in rops if "W" in r[1]]
        srcs = [r for r in rops if "R" in r[1]]
        def val_of_src(i):
            """Value of the i-th explicit source operand (register tag or memory constant)."""
            return None
        base = ic[1:] if ic.startswith("V") else ic
        if base in ("ADDSS", "ADDPS", "SUBSS", "SUBPS") and dst:
            d = dst[0][0]
            # operands in order: dest, src1, src2 (VEX) or dest(src1), src2 (legacy)
            if ic.startswith("V"):
                order = [r[0] for r in srcs if r[2] != dst[0][2]]
                s1 = ("reg", order[0]) if order else None
                s2 = ("reg", order[1]) if len(order) > 1 else (("mem", mops[0]) if mops else None)
            else:
                s1 = ("reg", d)
                o2 = [r[0] for r in srcs if r[2] != dst[0][2]]
                s2 = ("reg", o2[0]) if o2 else (("mem", mops[0]) if mops else None)
            def tag(s):
                if s is None:
                    return None
                if s[0] == "reg":
                    return regs.get(s[1])
                c = const_at(an, ins, s[1])
                return ("const", c) if isinstance(c, int) else None
            t1, t2 = tag(s1), tag(s2)
            res = None
            if base.startswith("ADD"):
                if t2 == ("const", M_POS) or t1 == ("const", M_POS):
                    n_add += 1
                    res = ("sum", key)
                if (t1 and t1[0] == "sum" and t2 == ("const", M_NEG)) or (t2 and t2[0] == "sum" and t1 == ("const", M_NEG)):
                    found.append({"add": "%d:%x" % t1[1] if t1[0] == "sum" else "%d:%x" % t2[1],
                                  "sub": "%d:%x" % key, "form": "add -M"})
            else:
                if t1 and t1[0] == "sum" and t2 == ("const", M_POS):
                    found.append({"add": "%d:%x" % t1[1], "sub": "%d:%x" % key, "form": "sub M"})
            regs[d] = res
            continue
        if ic == "MOV" and dst and "IMM0" in ins.f and not mops:
            regs[dst[0][0]] = ("const", sval(ins.f["IMM0"]) & 0xffffffff)
            continue
        if ic in MOVES or ic.startswith(("VBROADCASTSS", "VPBROADCASTD")) or ic in ("MOVD", "VMOVD"):
            if dst and mops and "R" in mops[0]["action"]:
                c = const_at(an, ins, mops[0])
                regs[dst[0][0]] = ("const", c) if isinstance(c, int) else None
                continue
            if dst and srcs and not mops:
                src = [r for r in srcs if r[2] != dst[0][2]]
                if src:
                    regs[dst[0][0]] = regs.get(src[-1][0])
                    continue
        for r in dst:
            regs[r[0]] = None
        if ic == "CALL_NEAR":
            for r in list(regs):
                regs[r] = None
    return ("pass" if found else "fail"), {"pairs": found, "adds_of_M": n_add}

# ----------------------------------------------------------------------------------------------------------------
# Debug-info twin: identity (record 4.6) and source lines
# ----------------------------------------------------------------------------------------------------------------

def sec_key(o, s):
    fn = sorted(sy.name for sy in o.syms if sy.sec == s.idx and sy.kind == "func")
    return (s.name, tuple(fn))


def rel_sig(o, s, lo=0, hi=None):
    hi = s.size if hi is None else hi
    out = []
    for r in s.relocs:
        if lo <= r.off < hi:
            nm = r.sym.name
            out.append((r.off - lo, r.type, nm, r.addend if o.fmt == "elf" else 0))
    return out


def twin_identity(co, tw):
    """Per census executable section: (twin section idx, identical, {func name: identical})."""
    tmap = {}
    for s in tw.exec_secs():
        tmap.setdefault(sec_key(tw, s), []).append(s)
    out = {}
    for s in co.exec_secs():
        k = sec_key(co, s)
        cands = tmap.get(k, [])
        if len(cands) != 1:
            out[s.idx] = (None, False, {})
            continue
        t = cands[0]
        same = s.data == t.data and rel_sig(co, s) == rel_sig(tw, t)
        per = {}
        if not same and s.size == t.size and [(r.off, r.type) for r in s.relocs] == [(r.off, r.type) for r in t.relocs]:
            for sy in co.syms:
                if sy.sec == s.idx and sy.kind == "func" and sy.size:
                    lo, hi = sy.value, sy.value + sy.size
                    per[sy.name] = (s.data[lo:hi] == t.data[lo:hi] and rel_sig(co, s, lo, hi) == rel_sig(tw, t, lo, hi))
        out[s.idx] = (t.idx, same, per)
    return out


def cv_uint(b, i):
    x = b[i]
    if x & 0x80 == 0:
        return x, i + 1
    if x & 0xC0 == 0x80:
        return ((x & 0x3F) << 8) | b[i + 1], i + 2
    if x & 0xE0 == 0xC0:
        return ((x & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4
    raise ValueError("bad compressed int")


def cv_sint(u):
    return -(u >> 1) if u & 1 else (u >> 1)


class CoffLines:
    """CodeView (.debug$S) line tables and inline sites of a /Z7 object."""
    def __init__(c, o, mode="msvc"):
        c.o, c.mode = o, mode
        c.procs = []        # dict(sec, start, len, rows=[(off, line, file)], sites=[...])
        c.files = {}        # checksum offset -> file name
        c.inlinee = {}      # item id -> (file name, line)
        strtab, chks, raw_lines, syms = None, None, [], []
        for s in o.secs.values():
            if not s.name.startswith(".debug$S") or s.size < 4:
                continue
            d = s.data
            if struct.unpack_from("<I", d, 0)[0] != 4:
                continue
            i = 4
            while i + 8 <= len(d):
                kind, ln = struct.unpack_from("<II", d, i)
                body = i + 8
                if kind == 0xF3:
                    strtab = d[body:body + ln]
                elif kind == 0xF4:
                    chks = d[body:body + ln]
                elif kind == 0xF2:
                    raw_lines.append((s, body, ln))
                elif kind == 0xF1:
                    syms.append((s, body, ln))
                elif kind == 0xF6:
                    c._inlinee_lines(d[body:body + ln])
                i = body + ln
                i = (i + 3) & ~3
        c._strtab, c._chks = strtab, chks
        c.inlinee = {k: (c.fname(v[0]), v[1]) for k, v in c._inl_raw.items()} if hasattr(c, "_inl_raw") else {}
        for s, body, ln in raw_lines:
            c._lines(s, body, ln)
        for s, body, ln in syms:
            c._symbols(s, body, ln)

    def fname(c, chkoff):
        if c._chks is None or c._strtab is None:
            return "?"
        nameoff = struct.unpack_from("<I", c._chks, chkoff)[0]
        e = c._strtab.index(b"\0", nameoff)
        return c._strtab[nameoff:e].decode("latin-1").replace("\\", "/").split("/")[-1]

    def _inlinee_lines(c, b):
        if not hasattr(c, "_inl_raw"):
            c._inl_raw = {}
        sig = struct.unpack_from("<I", b, 0)[0]
        i = 4
        while i + 12 <= len(b):
            iid, fid, line = struct.unpack_from("<III", b, i)
            i += 12
            if sig == 1:
                nx = struct.unpack_from("<I", b, i)[0]
                i += 4 + 4 * nx
            c._inl_raw[iid] = (fid, line)

    def _reloc_target(c, s, off):
        rl = c.o.rel_at(s.idx, off)
        if not rl:
            return None
        r = rl[0]
        if r.sym.sec is None:
            return None
        return r.sym.sec, r.sym.value + r.addend

    def _lines(c, s, body, ln):
        d = s.data
        t = c._reloc_target(s, body)
        if t is None:
            return
        sec, base = t
        flags, cb = struct.unpack_from("<HI", d, body + 6)
        i = body + 12
        end = body + ln
        rows = []
        while i + 12 <= end:
            fid, nl, cbb = struct.unpack_from("<III", d, i)
            fn = c.fname(fid)
            for k in range(nl):
                off, lf = struct.unpack_from("<II", d, i + 12 + 8 * k)
                rows.append((base + off, lf & 0xFFFFFF, fn))
            i += cbb
        c.procs.append({"sec": sec, "start": base, "len": cb, "rows": sorted(rows), "sites": []})

    def _symbols(c, s, body, ln):
        d = s.data
        i = body
        end = body + ln
        proc = None
        stack = []
        while i + 4 <= end:
            rl, rt = struct.unpack_from("<HH", d, i)
            rec = i + 4
            if rt in (0x1146, 0x1147, 0x110F, 0x1110):
                t = c._reloc_target(s, rec + 28)
                plen = struct.unpack_from("<I", d, rec + 12)[0]
                if t is not None:
                    proc = {"sec": t[0], "start": t[1], "len": plen}
                    c.procs_sym = getattr(c, "procs_sym", [])
                    c.procs_sym.append(proc)
                    proc["sites"] = []
                stack = []
            elif rt in (0x114D, 0x115D) and proc is not None:
                inl = struct.unpack_from("<I", d, rec + 8)[0]
                ann = rec + (16 if rt == 0x115D else 12)
                anns = d[ann:i + 2 + rl]
                fn, line = c.inlinee.get(inl, ("?", 0))
                ranges = c._annotations(anns, line, fn)
                site = {"inlinee": inl, "depth": len(stack), "parent": stack[-1] if stack else None,
                        "ranges": [(proc["start"] + a, proc["start"] + b, l, f) for a, b, l, f in ranges],
                        "sec": proc["sec"]}
                proc["sites"].append(site)
                stack.append(site)
            elif rt == 0x114E:
                if stack:
                    stack.pop()
            elif rt in (0x114F, 0x0006):
                stack = []
            i += 2 + rl

    def _annotations(c, b, line, fn):
        code = 0
        cur = None
        out = []
        i = 0
        while i < len(b):
            op = b[i]; i += 1
            if op == 0:
                break
            if op in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13):
                v, i = cv_uint(b, i)
            if op == 3:          # ChangeCodeOffset
                code += v
                if cur is not None and cur[1] is None:
                    cur[1] = code
                cur = [code, None, line, fn]; out.append(cur)
            elif op == 4:        # ChangeCodeLength
                if cur is not None:
                    cur[1] = cur[0] + v
                    code = cur[0] + v
            elif op == 6:        # ChangeLineOffset
                line += cv_sint(v)
                # LLVM's encoder emits a lone ChangeLineOffset only for a location at the current code offset, which
                # replaces the open entry's line; MSVC emits it before the code-offset annotation of the next range.
                # LLVM pairs "ChangeLineOffset; ChangeCodeOffset" for a new location; a ChangeLineOffset not followed
                # by ChangeCodeOffset is a location at the same code offset and replaces the open entry's line.
                nxt = b[i] if i < len(b) else 0
                if c.mode == "llvm" and nxt not in (3, 12) and cur is not None and cur[1] is None:
                    cur[2] = line
            elif op == 5:        # ChangeFile
                fn = c.fname(v)
            elif op == 11:       # ChangeCodeOffsetAndLineOffset
                v, i = cv_uint(b, i)
                line += cv_sint(v >> 4)
                code += v & 0xF
                if cur is not None and cur[1] is None:
                    cur[1] = code
                cur = [code, None, line, fn]; out.append(cur)
            elif op == 12:       # ChangeCodeLengthAndCodeOffset (length, offset delta)
                ln_, i = cv_uint(b, i)
                d_, i = cv_uint(b, i)
                code += d_
                if cur is not None and cur[1] is None:
                    cur[1] = code
                cur = [code, code + ln_, line, fn]; out.append(cur)
                # the code offset stays at the start of this range: the next code-offset delta is measured from it
                # (checked by hand on MSVC's mm_f32_avx512: 0x2b movsxd T at line 138, 0x104 zeroing at 141,
                # 0x11c at 142, 0x142 x load at 143)
        if cur is not None and cur[1] is None:
            cur[1] = cur[0] + 1
        return [tuple(x) for x in out]

    def frames(c, sec, off):
        """[(file, line)] innermost first, for twin section sec at offset off."""
        procs = [p for p in getattr(c, "procs_sym", []) if p["sec"] == sec and p["start"] <= off < p["start"] + p["len"]]
        lines = [p for p in c.procs if p["sec"] == sec and p["start"] <= off < p["start"] + max(p["len"], 1)]
        top = None
        for p in lines:
            for (a, l, f) in p["rows"]:
                if a <= off:
                    top = (f, l)
                else:
                    break
        fr = []
        if procs:
            sites = [s for s in procs[0]["sites"] if any(a <= off < b for a, b, l, f in s["ranges"])]
            if sites:
                site = max(sites, key=lambda s: s["depth"])
                while site is not None:
                    # the site's line at off: the entry containing off, else the nearest entry before it (the call
                    # site of a nested inlinee whose code the parent's ranges exclude)
                    rng = sorted(site["ranges"])
                    hit = [r for r in rng if r[0] <= off < r[1]] or [r for r in rng if r[0] <= off][-1:] or rng[:1]
                    fr.append((hit[0][3], hit[0][2]))
                    site = site["parent"]
        if top:
            fr.append(top)
        return fr


class ElfLines:
    """Source frames through llvm-symbolizer --inlining (relocatable ELF; the .text section)."""
    def __init__(c, path, symbolizer):
        c.path, c.exe = path, symbolizer
        c.cache = {}

    def prefetch(c, offs):
        need = sorted(set(o for o in offs if o not in c.cache))
        if not need:
            return
        inp = "".join("0x%x\n" % o for o in need).encode()
        p = subprocess.run([c.exe, "--obj=" + c.path, "--inlining", "--functions=linkage"], input=inp,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        blocks = p.stdout.decode("latin-1").replace("\r", "").split("\n\n")
        blocks = [b for b in blocks if b.strip()]
        for o, b in zip(need, blocks):
            ls = b.strip().split("\n")
            fr = []
            for k in range(0, len(ls) - 1, 2):
                m = re.match(r"^(.*):(\d+):(\d+)$", ls[k + 1])
                if m:
                    fr.append((m.group(1).replace("\\", "/").split("/")[-1], int(m.group(2))))
            c.cache[o] = fr

    def frames(c, sec, off):
        return c.cache.get(off, [])

# ----------------------------------------------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------------------------------------------

def census_obj_path(run, cfg, b, fname):
    stem = fname[:-2]
    if cfg == "A":
        return os.path.join(run, cfg, "cfg%d" % b, "hearth_core.dir", "Release", stem + ".obj")
    ext = ".obj" if cfg in ("A-ninja", "B-cmake") else ".o"
    return os.path.join(run, cfg, "cfg%d" % b, "CMakeFiles", "hearth_core.dir", "engine", "src", fname + ext)


def twin_path(run, cfg, fname):
    ext = ".obj" if cfg in ("A", "A-ninja", "B-cmake") else ".o"
    return os.path.join(run, cfg, "twin", fname + "_twin" + ext)


def cmd_stage(a):
    if os.path.exists(a.dest) and os.listdir(a.dest):
        raise SystemExit("destination not empty: " + a.dest)
    man = []
    for cfg in CONFIGS:
        for fname in FILES:
            ext = ".obj" if cfg in ("A", "A-ninja", "B-cmake") else ".o"
            for b in (1, 2):
                src = census_obj_path(a.run, cfg, b, fname)
                dst = os.path.join(a.dest, cfg, "b%d" % b, fname + ext)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)
                    man.append((sha256_file(dst), os.path.getsize(dst), os.path.relpath(dst, a.dest), src))
                else:
                    man.append(("ABSENT", 0, os.path.relpath(dst, a.dest), src))
            src = twin_path(a.run, cfg, fname)
            dst = os.path.join(a.dest, cfg, "twin", fname + "_twin" + ext)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
                man.append((sha256_file(dst), os.path.getsize(dst), os.path.relpath(dst, a.dest), src))
            else:
                man.append(("ABSENT", 0, os.path.relpath(dst, a.dest), src))
    with open(os.path.join(a.dest, "MANIFEST.sha256"), "w", newline="\n") as f:
        for h, n, rel, src in man:
            f.write("%s  %d  %s  <- %s\n" % (h, n, rel.replace("\\", "/"), src))
    print("staged", sum(1 for m in man if m[0] != "ABSENT"), "files;", sum(1 for m in man if m[0] == "ABSENT"), "absent")


def staged(inp, cfg, b, fname):
    ext = ".obj" if cfg in ("A", "A-ninja", "B-cmake") else ".o"
    p = os.path.join(inp, cfg, "b%d" % b if b else "twin", fname + ("_twin" if not b else "") + ext)
    return p if os.path.exists(p) else None


def strip_suffix(n):
    return re.sub(r"\.(constprop|isra|part|cold)(\.\d+)?", "", n)


def find_table(o, tname, accessor):
    for sy in o.by_name.get(tname, []):
        if sy.sec is not None and sy.kind != "func":
            return sy.sec, sy.value, "symbol"
    for fs in o.by_name.get(accessor, []):
        if fs.sec is None:
            continue
        for r in o.secs[fs.sec].relocs:
            if fs.value <= r.off < fs.value + (fs.size or o.secs[fs.sec].size) and r.sym.sec is not None and \
                    not o.secs[r.sym.sec].execu:
                add = r.addend + (4 if r.type in ("PC32", "REL32") else 0)
                return r.sym.sec, r.sym.value + add, "accessor relocation"
    return None


def analyse_object(an, objpath, file_variants, srcs, lt, fpc, twin, twin_lines, cfg, notes):
    o = an.o
    abi = "sysv" if o.fmt == "elf" else "win64"
    ident = twin_identity(o, twin) if twin is not None else None
    res = {}
    for (tname, slot, fn, foff, fname) in file_variants:
        key = "%s:%s" % (tname, slot)
        V = {"table": tname, "slot": slot, "source_function": fn, "gaps": [], "slot_resolved": False}
        res[key] = V
        acc = {"hx_kernels_scalar": None, "k_avx2": "hx_kernels_avx2_table", "k_avx512": "hx_kernels_avx512_table"}[tname]
        t = find_table(o, tname, acc)
        if t is None:
            V["gaps"].append(("table_or_slot_absent", None, None, "table %s not found" % tname)); continue
        tsec, toff, how = t
        V["table_found_by"] = how
        rl = o.rel_at(tsec, toff + foff)
        if not rl or rl[0].off != toff + foff or rl[0].type not in ("64", "ADDR64"):
            V["gaps"].append(("table_or_slot_absent", None, None, "no pointer relocation on the slot")); continue
        r = rl[0]
        if r.sym.sec is None:
            V["gaps"].append(("other", None, None, "slot relocation to undefined symbol " + r.sym.name)); continue
        ent = an.by_start.get((r.sym.sec, r.sym.value + r.addend))
        if ent is None:
            V["gaps"].append(("other", None, None, "slot target is not a function start")); continue
        V["slot_resolved"] = True
        V["entry"] = ent.name
        V["slot_name_check"] = "match" if any(strip_suffix(n) == fn for n in ent.names) else "mismatch"
        # closure, repeated until the internal no-return set is stable
        noret = frozenset()
        for _ in range(5):
            R = an.closure(ent, noret)
            new = set()
            for nm, (f, kind) in R["funcs"].items():
                if kind in ("internal", "interposable") and f.parent is None:
                    fam = {g.name for g in an.family(f)}
                    rets = [k for k in R["rets"] if R["owner"][k].name in fam]
                    tails_ok = any(R["owner"][k].name in fam and (v[0] == "ext" and v[1] not in NORETURN)
                                   for k, v in R["calls_at"].items()
                                   if ctl_kind(R["reach"][k]) == "jmp")
                    if not rets and not tails_ok and not any(
                            R["owner"][k].name in fam and ctl_kind(R["reach"][k]) == "jmp" and v[0] != "ext"
                            for k, v in R["calls_at"].items()):
                        new.add(nm)
            if frozenset(new) == noret:
                break
            noret = frozenset(new)
        V["noreturn_internal"] = sorted(noret)
        V["gaps"].extend(R["gaps"])
        V["closure"] = [(nm, kind, o.secs[f.sec].name, f.start, f.end) for nm, (f, kind) in R["funcs"].items()]
        V["external_calls"] = sorted(R["external"])
        V["internal_calls"] = sorted(R["internal"])
        V["interposable_calls"] = sorted(R["interposable"])
        V["fp_trust_deps"] = sorted(R["fp_deps"])
        V["tail_calls"] = sorted(R["tail"])
        V["noreturn_inferred"] = ["%d:%x" % k for k in R["noret_inferred"]]
        V["indirect_unresolved"] = [("%d:%x" % (s, off), t) for s, off, t in R["indirect"]]
        V["jump_tables"] = [{"site": "%d:%x" % j["site"], "n": j["n"]} for j in R["jump_tables"]]
        iforms, iclasses = collections.Counter(), collections.Counter()
        for k, ins in R["reach"].items():
            iforms[ins.iform] += 1
            iclasses[ins.iclass] += 1
        V["n_instructions"] = len(R["reach"])
        V["iforms"] = dict(iforms)
        V["iclasses"] = dict(iclasses)
        V["fma_addrs"] = sorted("%d:%x" % k for k, ins in R["reach"].items() if is_fma(ins.iclass))
        V["p2"] = len(V["fma_addrs"])
        V["p3b"] = sorted({ins.iclass for ins in R["reach"].values() if is_approx(ins.iclass)})
        # attribution
        exact = None
        if ident is None:
            V["attribution"] = "none"
            V["gaps"].append(("other", None, None, "twin attribution none: no twin object"))
        else:
            ok = True
            for nm, (f, kind) in R["funcs"].items():
                tsec_, same, per = ident.get(f.sec, (None, False, {}))
                if tsec_ is None or not (same or per.get(f.name)):
                    ok = False
            V["attribution"] = "exact" if ok else "approximate"
            exact = ok
        # loops
        vcode = TABLE_CODE[tname] + "." + ("act" if slot == "act_quantize_q8" else slot[7:-1])
        vbound = max([row["lanes"] for row in lt.values() if vcode in row["variants"]] or [0])
        V["variant_bound"] = vbound
        V["loops"] = []
        loops_all = []
        fams = collections.OrderedDict()
        for nm, (f, kind) in R["funcs"].items():
            head = f.parent or f.name
            fams.setdefault(head, set()).add(nm)
        for head, names in fams.items():
            cfg_ = build_cfg(R, names)
            if cfg_ is None:
                continue
            hf = [an.by_start[(R["funcs"][n][0].sec, R["funcs"][n][0].start)] for n in names if
                  R["funcs"][n][0].parent is None]
            if not hf:
                continue
            entry_key = (hf[0].sec, hf[0].start)
            if entry_key not in cfg_["blocks"]:
                continue
            for L in natural_loops(cfg_, entry_key):
                A = analyse_loop(L, cfg_, fpc, abi)
                L["cfg"] = cfg_
                L["res"] = A
                L["func"] = head
                loops_all.append(L)
        # source attribution of every loop
        def src_loop_of(frames):
            for i, (fl, ln) in enumerate(frames):
                if fl in srcs and ln > 0:
                    sl = srcs[fl].innermost_loop(ln)
                    if sl is not None:
                        return sl, frames[i + 1:]
            return None, []
        def tw_frames(sec, off):
            if ident is None:
                return []
            tsec_ = ident.get(sec, (None,))[0]
            if tsec_ is None:
                return []
            return twin_lines.frames(tsec_, off)
        if twin_lines is not None and isinstance(twin_lines, ElfLines):
            offs = []
            for L in loops_all:
                for b in [L["header"]] + L["latches"]:
                    offs += [k[1] for k in L["cfg"]["blocks"][b]]
            twin_lines.prefetch(offs)
        for L in loops_all:
            blocks = L["cfg"]["blocks"]
            hfr = []
            for k in blocks[L["header"]]:
                fr = tw_frames(*k)
                if fr and fr[0][1] > 0:
                    hfr = fr; break
            tfr = []
            lt_latch = max(L["latches"], key=lambda b: blocks[b][-1])
            for k in reversed(blocks[lt_latch]):
                fr = tw_frames(*k)
                if fr and fr[0][1] > 0:
                    tfr = fr; break
            L["H"], L["Hout"] = src_loop_of(hfr)
            L["T"], L["Tout"] = src_loop_of(tfr)
            L["hframes"], L["tframes"] = hfr, tfr
        def lanes_src(sl):
            return lt[sl["id"]]["lanes"] if sl and sl["id"] in lt else vbound
        def same_file(x, y):
            return x["id"].split(":")[0] == y["id"].split(":")[0]
        def contains(o_, i_, iout):
            if same_file(o_, i_) and o_["start"] <= i_["start"] and i_["end"] <= o_["end"] and o_ is not i_:
                return True
            for fl, ln in iout:
                if fl == o_["id"].split(":")[0] and o_["start"] <= ln <= o_["end"]:
                    return True
            return False
        def att(L2, sl):
            return L2["H"] is not None and L2["T"] is not None and L2["H"]["id"] == sl["id"] and L2["T"]["id"] == sl["id"]
        for L in loops_all:
            Hs, Ts = L["H"], L["T"]
            if not exact:
                bound, rule = vbound, "unattributed"
            elif Hs is None and Ts is None:
                bound, rule = vbound, "unattributed"
            elif Hs is None:
                bound, rule = lanes_src(Ts), "latch"
            elif Ts is None:
                bound, rule = lanes_src(Hs), "header"
            elif Hs["id"] == Ts["id"]:
                bound, rule = lanes_src(Hs), "same"
            else:
                if contains(Ts, Hs, L["Hout"]):
                    inner, outer = Hs, Ts
                elif contains(Hs, Ts, L["Tout"]):
                    inner, outer = Ts, Hs
                else:
                    inner = outer = None
                if inner is None:
                    bound, rule = min(lanes_src(Hs), lanes_src(Ts)), "min"
                else:
                    enc = [L2 for L2 in loops_all if L2 is not L and L2["func"] == L["func"] and
                           L["body"] < L2["body"] and att(L2, outer)]
                    ins_ = [L2 for L2 in loops_all if L2 is not L and L2["func"] == L["func"] and
                            L2["body"] < L["body"] and att(L2, inner)]
                    if enc:
                        bound, rule = (min(lanes_src(inner), lanes_src(outer)), "min") if ins_ else \
                            (lanes_src(inner), "inner")
                    elif ins_:
                        bound, rule = lanes_src(outer), "outer"
                    else:
                        own = any(att(L2, inner) for L2 in loops_all)
                        trip = lt.get(inner["id"], {}).get("trip", "")
                        flat = (not own) and (re.match(r"^\d+", trip or "") is not None or
                                              (outer.get("var") and trip.strip() == outer.get("var")))
                        bound, rule = (lanes_src(outer), "outer") if flat else \
                            (min(lanes_src(inner), lanes_src(outer)), "min")
            lanes = L["res"]["acc_lanes_emitted"]
            hk = L["header"]
            f = an.func_containing(*hk)
            lid = "%s+0x%x" % (f.name if f else "?", hk[1] - (f.start if f else 0))
            entry = {"id": lid, "header": "%s#%d:0x%x" % (o.secs[hk[0]].name, hk[0], hk[1]),
                     "latches": ["0x%x" % L["cfg"]["blocks"][b][-1][1] for b in L["latches"]],
                     "n_blocks": len(L["body"]), "acc_lanes_emitted": lanes, "bound": bound, "bound_rule": rule,
                     "source_header": Hs["id"] if Hs else None, "source_latch": Ts["id"] if Ts else None,
                     "header_frames": L["hframes"][:4], "latch_frames": L["tframes"][:4],
                     "flagged": lanes > bound, "cycles": L["res"]["cycles"]}
            V["loops"].append(entry)
        V["p3c"] = [x["id"] for x in V["loops"] if x["flagged"]]
        if tname == "hx_kernels_scalar" and slot == "act_quantize_q8":
            d1, det = canary_d1(an, R)
            V["d1"], V["d1_detail"] = d1, det
        V["_R"] = R
    return res


def closure_signature(an, V):
    """Bytes + relocation list of every closure function, for the A versus A-ninja comparison."""
    o = an.o
    sig = []
    for nm, kind, secname, start, end in V.get("closure", []):
        f = None
        for g in an.funcs:
            if g.name == nm:
                f = g; break
        s = o.secs[f.sec]
        rels = [(r.off - f.start, r.type, r.sym.name if r.sym.kind != "section" else "sec:" + r.sym.name,
                 r.addend if o.fmt == "elf" else 0) for r in s.relocs if f.start <= r.off < f.end]
        sig.append((nm, kind, hashlib.sha256(s.data[f.start:f.end]).hexdigest(), tuple(rels)))
    return sig


def code_sig(o):
    """SHA-256 over every non-debug section's bytes and relocation list (COFF headers and debug records excluded)."""
    h = hashlib.sha256()
    for s in sorted(o.secs.values(), key=lambda x: x.idx):
        if s.name.startswith((".debug", ".chks64")) or not s.name:
            continue
        h.update(s.name.encode() + b"\0" + s.data)
        for r in s.relocs:
            h.update(repr((r.off, r.type, r.sym.name, r.addend)).encode())
    return h.hexdigest()


def cmd_run(a):
    t0 = __import__("time").time()
    out = a.out
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="x0r_")
    xed = Xed(a.xed, tmp)
    srcs_text = {}
    for fn in FILES + ["hx_quant.h"]:
        with open(os.path.join(a.src, fn), encoding="utf-8") as f:
            srcs_text[fn] = f.read()
    with open(os.path.join(a.include, "hearth.h"), encoding="utf-8") as f:
        hearth_h = f.read()
    srcs = {fn: Source(fn, srcs_text[fn]) for fn in FILES}
    layout = struct_layout(srcs_text["hx_quant.h"])
    dtn = dtype_names(hearth_h)
    tables = source_tables(srcs, layout, dtn)
    if len(tables) != 18:
        raise SystemExit("expected 18 variants from the source, found %d" % len(tables))
    fpc = load_fp_class(a.fp_class)
    lt = load_loop_table(a.loop_table)
    iform_iclass, all_iclasses = load_xed_tables(a.xed_tables)
    base = baseline(srcs_text, a.xml, iform_iclass)
    detail = {"inputs": {}, "baseline": {k: v for k, v in base.items() if k != "per_intrinsic"},
              "layout": layout, "tables": tables, "variants": {}, "configs": {}, "notes": []}
    detail["baseline"]["per_intrinsic"] = base["per_intrinsic"]
    detail["source_loops"] = {fn: srcs[fn].loops for fn in FILES}
    allres = {}
    analyzers = {}
    for cfg in (a.configs.split(",") if a.configs else CONFIGS):
        detail["configs"][cfg] = {"objects": {}}
        for fname in FILES:
            fv = [t for t in tables if t[4] == fname]
            twp = staged(a.input, cfg, 0, fname)
            twin = Obj(twp) if twp else None
            tl = None
            if twin is not None:
                tl = CoffLines(twin, "llvm" if cfg == "B-cmake" else "msvc") if twin.fmt == "coff" else                     ElfLines(twp, a.symbolizer)
            prev = None
            for b in (1, 2):
                p = staged(a.input, cfg, b, fname)
                rec = {"path": p, "sha256": sha256_file(p) if p else None}
                if p:
                    rec["code_sig"] = code_sig(Obj(p))
                detail["configs"][cfg]["objects"]["%s|b%d" % (fname, b)] = rec
                if p is None:
                    for (tname, slot, fn, foff, _) in fv:
                        allres[(cfg, b, "%s:%s" % (tname, slot))] = {
                            "table": tname, "slot": slot, "slot_resolved": False,
                            "gaps": [("compile_failed", None, None, "no object for %s in build %d" % (fname, b))],
                            "loops": [], "p3c": [], "iforms": {}, "iclasses": {}, "p2": 0, "p3b": []}
                    continue
                if prev is not None and prev[0] == rec["code_sig"]:
                    rec["identical_to_b1"] = True
                    for k, v in prev[1].items():
                        allres[(cfg, b, k)] = v
                    analyzers[(cfg, b, fname)] = analyzers[(cfg, 1, fname)]
                    continue
                o = Obj(p)
                an = Analyzer(o, xed, a.objdump)
                analyzers[(cfg, b, fname)] = an
                r = analyse_object(an, p, fv, srcs, lt, fpc, twin, tl, cfg, detail["notes"])
                for k, v in r.items():
                    allres[(cfg, b, k)] = v
                prev = (rec["code_sig"], r)
                print("%s %s b%d: %d variants, %.0fs, xed calls %d" % (cfg, fname, b, len(r),
                      __import__("time").time() - t0, xed.calls), flush=True)
    # A versus A-ninja, per variant
    ab = {}
    for (tname, slot, fn, foff, fname) in tables:
        k = "%s:%s" % (tname, slot)
        va, vn = allres.get(("A", 1, k)), allres.get(("A-ninja", 1, k))
        if va and vn and va.get("slot_resolved") and vn.get("slot_resolved"):
            sa = closure_signature(analyzers[("A", 1, fname)], va)
            sn = closure_signature(analyzers[("A-ninja", 1, fname)], vn)
            ab[k] = "identical" if sa == sn else "differs"
        else:
            ab[k] = "differs"
    detail["ab_compare"] = ab
    # figures
    def vkey(cfg, k):
        return "%s|%s" % (cfg, k)
    union_cfgs = ["A", "B-cmake", "C", "D"]
    members = [(cfg, k) for cfg in union_cfgs for k in ["%s:%s" % (t[0], t[1]) for t in tables]]
    members += [("A-ninja", k) for k, v in ab.items() if v == "differs"]
    fig = {"p1": {}, "p2": {}, "p3b": [], "p3c": {}, "p3d1": {}}
    U, FPS = set(), set()
    for cfg, k in members:
        gaps, resolved, flagged_loops, p3b = set(), True, set(), set()
        for b in (1, 2):
            V = allres.get((cfg, b, k))
            if V is None:
                gaps.add("other"); resolved = False; continue
            resolved = resolved and V["slot_resolved"]
            gaps |= {g[0] for g in V["gaps"]}
            flagged_loops |= set(V.get("p3c", []))
            U |= set(V.get("iforms", {}))
            FPS |= {ic for ic in V.get("iclasses", {}) if fpc.get(ic, (True, ic))[0]}
            for ic in V.get("p3b", []):
                p3b.add(ic)
        fig["p1"][vkey(cfg, k)] = {"slot_resolved": resolved, "gap_causes": sorted(gaps)}
        fig["p3c"][vkey(cfg, k)] = sorted(flagged_loops)
        for ic in sorted(p3b):
            fig["p3b"].append("%s|%s" % (vkey(cfg, k), ic))
    for cfg in CONFIGS:
        n = 0
        for b in (1, 2):
            addrs = set()
            for (c2, b2, k), V in allres.items():
                if c2 == cfg and b2 == b and (cfg != "A-ninja" or ab.get(k) == "differs" or True):
                    addrs |= {(TABLE_FILE[V["table"]], x) for x in V.get("fma_addrs", [])}
            n = max(n, len(addrs))
        fig["p2"][cfg] = n
        d1s = [allres.get((cfg, b, "hx_kernels_scalar:act_quantize_q8"), {}).get("d1") for b in (1, 2)]
        fig["p3d1"][cfg] = "pass" if all(x == "pass" for x in d1s) else ("fail" if any(x == "fail" for x in d1s)
                                                                          else "not_evaluated")
    fig["u_all"] = len(U)
    fig["p5_iclass"] = len(FPS)
    fig["p5_opclass"] = len({fpc.get(ic, (True, ic))[1] for ic in FPS})
    fig["b_iform"] = len(base["b_iform"])
    fig["b_mnem"] = len(base["b_mnem"])
    fig["t_forms"] = min(len(base["b_iform"]), 105)
    fig["iforms"] = sorted(U)
    fig["fp_sensitive_iclasses"] = sorted(FPS)
    # detail per variant
    for (cfg, b, k), V in sorted(allres.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        D = {kk: vv for kk, vv in V.items() if not kk.startswith("_") and kk not in ("iforms",)}
        D["gaps"] = [{"cause": g[0], "where": None if g[1] is None else "%d:%x" % (g[1], g[2]), "detail": g[3]}
                     for g in V["gaps"]]
        D["n_iforms"] = len(V.get("iforms", {}))
        D["iform_list"] = sorted(V.get("iforms", {}))
        detail["variants"]["%s|b%d|%s" % (cfg, b, k)] = D
    detail["xed_calls"] = xed.calls
    detail["elapsed_s"] = round(__import__("time").time() - t0, 1)
    with open(os.path.join(out, "figures.json"), "w", newline="\n") as f:
        json.dump(fig, f, indent=1, sort_keys=False)
    with open(os.path.join(out, "rederive_detail.json"), "w", newline="\n") as f:
        json.dump(detail, f, indent=1, default=str)
    print("figures:", {k: v for k, v in fig.items() if k not in ("iforms", "fp_sensitive_iclasses", "p1", "p3c")})
    print("p1 gaps:", {k: v["gap_causes"] for k, v in fig["p1"].items() if v["gap_causes"]})
    print("p3c:", {k: v for k, v in fig["p3c"].items() if v})
    print("ab:", ab)
    shutil.rmtree(tmp, ignore_errors=True)


def cmd_dumpxed(a):
    o = Obj(a.obj)
    for s in o.exec_secs():
        if s.name == a.section or str(s.idx) == a.section:
            x = Xed(a.xed, tempfile.mkdtemp())
            ins, txt = x.sweep(s.data, s.idx, 0)
            sys.stdout.write(txt[: a.limit])
            print("\n# parsed", len(ins))
            return
    print("sections:", [(s.idx, s.name, s.size) for s in o.exec_secs()])


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd")
    s = sp.add_parser("stage"); s.add_argument("--run", required=True); s.add_argument("--dest", required=True)
    r = sp.add_parser("run")
    for k in ("input", "out", "src", "include", "fp_class", "loop_table", "xed_tables", "xml", "xed", "objdump",
              "symbolizer"):
        r.add_argument("--" + k.replace("_", "-"), dest=k, required=True)
    r.add_argument("--configs", default="")
    d = sp.add_parser("dumpxed"); d.add_argument("obj"); d.add_argument("section"); d.add_argument("--xed", required=True)
    d.add_argument("--limit", type=int, default=20000)
    a = ap.parse_args()
    {"stage": cmd_stage, "run": cmd_run, "dumpxed": cmd_dumpxed}[a.cmd](a)


if __name__ == "__main__":
    main()
