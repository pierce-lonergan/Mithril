#!/usr/bin/env python3
"""x0_decode.py -- X0 record §4.2 (each dispatched variant's counted set, by recursive descent), the XED
decode, and the cross-decoder check of §7. Standard library only; Python >= 3.8. Run with python -I.

Usage:
  python -I x0_decode.py MANIFEST.json -o OUTDIR --xed XED --objdump LLVM_OBJDUMP
         [--norm ../class/objdump_norm.csv] [--fp-class ../class/fp_class.csv] [-j 2] [--attr-cache F]
         [--worklist-order lifo|fifo]

MANIFEST.json is written by x0_extract.py (one configuration). Steps:
 1. XED linear sweep (`xed -64 -cet -ir <bytes> -b <start> -v 4 -isa-set`) of every function range, plus the
    attribute pass (`xed -64 -cet -d <hex>`, once per distinct encoding). -cet is required so that ENDBR64
    decodes as ENDBR64 (without it XED reports a reserved NOP).
 2. For every dispatched variant (slot resolved by x0_extract.py), recursive descent from the slot's entry, in
    rounds (so that the result does not depend on the order of the work list; --worklist-order fifo must give
    byte-identical variants.json):
      a. closure over fall-through, direct conditional and unconditional jumps and direct calls. Branch targets
         come from the relocation on the displacement (ELF PC32/PLT32: S+A+(end-P); COFF REL32[_k]:
         S+inplace+(end-P-4-k)) or, without one, from the in-section displacement. A target that is not an
         instruction start of the sweep is re-decoded from that byte ("anchored" decode).
         Function families: a GCC cold part (a function symbol named exactly `<parent>.cold` or
         `<parent>.cold.N` in the same object) belongs to its parent; a jump inside a family is intra-procedural
         (no call or tail-call entry; closure kind `cold_part_of:<parent>`). A jump (JMP or Jcc) to another
         function's start is a tail call; a jump into the middle of another function is a gap `other`.
         Call kinds: internal (defined, local or hidden/protected visibility; any defined callee on COFF),
         interposable (ELF default-visibility global definition; body joins the closure), external (undefined:
         listed, not followed). Calls through memory `call/jmp [rip+X]` are calls to X only when the operand
         holds X's address: COFF X = `__imp_<name>`; ELF a GOTPCREL/GOTPCRELX/REX_GOTPCRELX relocation to an
         undefined X. Anything else (a PC32/REL32 relocation to a variable, `__guard_dispatch_icall_fptr`, any
         other memory form) is `unresolved_indirect`. `__guard_check_icall_fptr` is an allow-listed check call.
      b. every indirect jump and register call is held as pending and resolved against the COMPLETE reach set
         of the round:
           * jump table: the table is the one loaded by the jump's own address computation, recognised in the
             jump's basic block: `movsxd/mov rX,[rB+rI*4(+T@ADDR32NB)]` ; `add rX,rB` ; `jmp rX` (rB's reaching
             definitions are all `lea rB,[rip+T]`, or `lea rB,[__ImageBase]` with the ADDR32NB form), or
             `jmp [T+rI*8]` with a displacement relocation. Its extent comes from the guarding bound on rI that
             dominates the jump in its block: `cmp rI,imm` + `ja` (n = imm+1) / `jae` (n = imm), the taken
             `jbe`/`jb` forms, `and rI,2^k-1` (n = 2^k), or an MSVC byte index table
             `movzx eI,byte [rB+rJ+T2@ADDR32NB]` (byte table T2 bounded the same way on rJ; n = max byte + 1;
             the byte table is data). Exactly n entries of the expected relocation type must exist and each
             must land on an instruction start inside the jump's function family; otherwise the jump is
             `unresolved_indirect` ("jump table truncated at entry k of n", "jump-table extent", ...). Partial
             tables are never accepted.
           * `call/jmp reg` is a call (tail call) to an imported X only if every reaching definition of reg (its
             64-bit register family) is a MOV of the same import or GOT slot; a call on the path clobbers the
             caller-saved registers of the object's ABI. Otherwise `unresolved_indirect`.
         Rounds repeat until no instruction is added. A pending branch whose resolution changes between rounds
         is a gap `other`.
      c. no return: a call to a NORETURN_EXTERNALS function does not fall through, nor does a call whose next
         byte is the end of its function or padding up to the end (lift_blockers.noreturn_inferred, not a gap),
         nor a call to an internal callee whose family has no RET and no tail call to a returning function (the
         descent is repeated until this set is stable). Execution falling off the end of a function after a
         non-call instruction is a gap `other`.
    An external callee not on the NON_FP_EXTERNALS allow-list is an FP trust dependency (genuine P1 gap
    `fp_trust_dep`); this is stricter than "libm or CRT FP function" because an unknown callee is presumed
    FP-relevant. Two reachable instructions whose bytes overlap are a gap `other`.
    Data in code: jump-table and byte-index-table bytes in a code section, and bytes covered by a relocation that
    is not inside a reachable instruction, are data and are never decoded as part of the counted set.
 3. Unreachable bytes in the ranges of closure functions: padding (all 0xCC, all zero, or NOP-class only in
    the sweep) or orphan (offsets listed; their sweep decode is a secondary output, never in U). Code addresses
    referenced by a reachable instruction that are neither an instruction start nor data are listed.
 4. Cross-checks: the linear sweep against the descent (sweep-only and descent-only instruction starts);
    llvm-objdump against XED for every reachable instruction: equal length, and XED's iclass in the set that
    class/objdump_norm.csv gives for the objdump text. Disagreements are listed with an FP-sensitive flag
    (fp_class.csv; an iclass missing from it counts as FP-sensitive). XED failing where llvm-objdump decodes
    is `xed_gap` (genuine); both failing is `both_decoders_fail` (tooling).
 5. COFF range checks from the manifest: a closure function whose .pdata disagrees with its range, or whose
    range had to come from the next symbol, is a `range_mismatch` gap (tooling).

Outputs in OUTDIR: variants.json (per-variant fields of census.json, Appendix C; every list sorted),
instructions.jsonl (reachable, orphan and sweep records), crossdecoder.json, anomalies.json, summary.json.
Exit status 1 if any tooling-class gap, any cross-decoder disagreement or any internal error occurred.
"""
import argparse
import bisect
import collections
import concurrent.futures as cf
import csv
import hashlib
import json
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x0_norm  # noqa: E402

XDIS_RE = re.compile(r"^XDIS ([0-9a-fA-F]+): (\S+)\s+(\S+)\s+(\S+)\s+([0-9A-F]+)\s*(.*)$")
ERR_RE = re.compile(r"^ERROR: (\S+) Could not decode at offset: (0x[0-9a-fA-F]+) len: (\d+) PC: (0x[0-9a-fA-F]+): \[([0-9A-Fa-f]*)\]")
HDR_RE = re.compile(r"^([A-Z][A-Z0-9_]*) ([A-Z][A-Za-z0-9_]*)(?: (.*))?$")
OPND_RE = re.compile(r"^(\d+)\s+(\S+)$")
TERMINATORS = {"RET_NEAR", "RET_FAR", "IRET", "IRETD", "IRETQ", "UD0", "UD1", "UD2", "HLT", "INT3"}
RETURNS = {"RET_NEAR", "RET_FAR", "IRET", "IRETD", "IRETQ"}
COND_JUMPS = {"JB", "JBE", "JL", "JLE", "JNB", "JNBE", "JNL", "JNLE", "JNO", "JNP", "JNS", "JNZ", "JO", "JP", "JS",
              "JZ", "JRCXZ", "JECXZ", "JCXZ", "LOOP", "LOOPE", "LOOPNE"}
NOP_CLASS = {"NOP", "NOP2", "NOP3", "NOP4", "NOP5", "NOP6", "NOP7", "NOP8", "NOP9", "INT3", "FNOP"}
FMA_RE = re.compile(r"^(VF(N)?M(ADD|SUB)(SUB|ADD)?(132|213|231)?(PS|PD|SS|SD|PH|SH|BF16|NEPBF16)|V4FN?MADD(PS|SS)|"
                    r"VFC?(MADD|MUL)C(PH|SH))$")
FMA4_EXT = "FMA4"
S_EXTENSIONS = {"SSE", "SSE2", "SSE3", "SSSE3", "SSE4", "AVX", "AVX2", "AVX2GATHER", "FMA", "F16C", "AVX512EVEX",
                "AVX512VEX"}
# External callees that are not FP trust dependencies (memory, string, stack-probe, hardening, CFG check).
NON_FP_EXTERNALS = {"memcpy", "memmove", "memset", "memcmp", "__memcpy_chk", "__memset_chk", "__memmove_chk",
                    "__stack_chk_fail", "__stack_chk_fail_local", "__security_check_cookie", "__GSHandlerCheck",
                    "__chkstk", "___chkstk_ms", "__report_rangecheckfailure", "__guard_check_icall_fptr"}
NORETURN_EXTERNALS = {"__stack_chk_fail", "__stack_chk_fail_local", "abort", "exit", "_exit", "__assert_fail",
                      "__chk_fail", "__fortify_fail", "longjmp", "__longjmp_chk", "_invalid_parameter_noinfo_noreturn",
                      "__report_gsfailure", "__report_rangecheckfailure", "__fastfail", "ExitProcess"}
CFG_DISPATCH = {"__guard_dispatch_icall_fptr", "_guard_dispatch_icall_fptr"}
CFG_CHECK = {"__guard_check_icall_fptr", "_guard_check_icall_fptr"}
GOT_RELOCS = ("GOTPCREL", "GOTPCRELX", "REX_GOTPCRELX")
TOOLING = {"both_decoders_fail", "range_mismatch", "unresolved_indirect", "other"}
GENUINE = {"compile_failed", "table_or_slot_absent", "xed_gap", "fp_trust_dep"}
COLD_RE = re.compile(r"^(.+)\.cold(\.\d+)?$")

# ---------------------------------------------------------------------------------------------- registers
GPR_FAMILY, GPR_WIDTH = {}, {}
for _b, _n in {"RAX": "EAX AX AL AH", "RBX": "EBX BX BL BH", "RCX": "ECX CX CL CH", "RDX": "EDX DX DL DH",
               "RSI": "ESI SI SIL", "RDI": "EDI DI DIL", "RBP": "EBP BP BPL", "RSP": "ESP SP SPL"}.items():
    _ns = _n.split()
    GPR_FAMILY[_b], GPR_WIDTH[_b] = _b, 64
    for _x, _w in zip(_ns, (32, 16, 8, 8)):
        GPR_FAMILY[_x], GPR_WIDTH[_x] = _b, _w
for _i in range(8, 16):
    for _suf, _w in (("", 64), ("D", 32), ("W", 16), ("B", 8)):
        GPR_FAMILY["R%d%s" % (_i, _suf)], GPR_WIDTH["R%d%s" % (_i, _suf)] = "R%d" % _i, _w
FLAGS_REGS = {"RFLAGS", "EFLAGS", "FLAGS"}
VEC_FAMILY = {"%s%d" % (k, i): "V%d" % i for k in ("XMM", "YMM", "ZMM") for i in range(32)}
CALLER_SAVED = {"elf": {"RAX", "RCX", "RDX", "RSI", "RDI", "R8", "R9", "R10", "R11"} | {"V%d" % i for i in range(32)},
                "coff": {"RAX", "RCX", "RDX", "R8", "R9", "R10", "R11"} | {"V%d" % i for i in list(range(6)) + list(range(16, 32))}}
COPY_IFORMS = ("MOV_GPRv_GPRv", "MOVQ_GPR64_XMMq", "MOVQ_XMMdq_GPR64", "VMOVQ_GPR64q_XMMq", "VMOVQ_XMMdq_GPR64q",
               "VMOVQ_GPR64u64_XMMu64_AVX512", "VMOVQ_XMMu64_GPR64u64_AVX512")


def fam(r):
    return GPR_FAMILY.get(r or "")


def written(ins):
    """Register families written by an instruction (from XED's operand list; implicit operands included).
    GPRs map to their 64-bit register, XMMn/YMMn/ZMMn to Vn."""
    out, f = set(), ins.get("fields", {})
    for op in ins.get("operands", []):
        p = op.split("/")
        if p[0].startswith("REG") and len(p) > 1 and "W" in p[1]:
            r = f.get(p[0])
            out.add(fam(r) or VEC_FAMILY.get(r or "") or r)
    return out


def copy_source(ins, regf):
    """If `ins` copies a whole 64-bit value into register family regf from another register (mov r64,r64;
    (v)movq r64,xmm; (v)movq xmm,r64), return the source family; else None."""
    if not ins.get("iform", "").startswith(COPY_IFORMS):
        return None
    f = ins.get("fields", {})
    r0, r1 = f.get("REG0"), f.get("REG1")
    d0, s1 = fam(r0) or VEC_FAMILY.get(r0 or ""), fam(r1) or VEC_FAMILY.get(r1 or "")
    if d0 != regf or not s1:
        return None
    if fam(r0) and GPR_WIDTH.get(r0) != 64 or fam(r1) and GPR_WIDTH.get(r1) != 64:
        return None
    return s1


def writes_flags(ins):
    return bool(written(ins) & FLAGS_REGS)


def mem_parts(txt):
    """XED's MEM0/AGEN text, e.g. 'ptr [R9+RAX*4]', 'qword ptr [RAX*8+0x10]' -> (base, index, scale, disp)."""
    m = re.search(r"\[(.*?)\]", txt or "")
    base = index = None
    scale, disp = 1, 0
    if not m:
        return None
    for sign, term in re.findall(r"([+-]?)([^+-]+)", m.group(1)):
        t = term.strip()
        if re.match(r"^(0x[0-9a-fA-F]+|\d+)$", t):
            disp += (-1 if sign == "-" else 1) * int(t, 0)
        elif "*" in t:
            index, sc = t.split("*")
            scale = int(sc)
        elif base is None:
            base = t
        else:
            index = t
    return base, index, scale, disp


def imm_value(ins):
    v = ins.get("fields", {}).get("IMM0")
    if v is None:
        return None
    try:
        x = int(str(v), 16) if str(v).lower().startswith(("0x", "-0x")) else int(str(v), 0)
    except ValueError:
        return None
    if ins.get("fields", {}).get("IMM0SIGNED") and x >= (1 << 63):
        x -= 1 << 64
    return x


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def parse_fields(s):
    out = {}
    for tok in (s or "").split(", "):
        tok = tok.strip()
        if tok:
            k, _, v = tok.partition(":")
            out[k] = v if v else True
    return out


def xed_sweep(xed, mode, path, base):
    """Run `xed MODE -ir PATH -b BASE -v 4 -isa-set`; return (instructions, errors, declared_error_count).
    Each instruction: offset, len, hex, category, extension, isa_set, disasm, iclass, iform, fields (all XED
    operand-storage fields of the header line) and operands (list of 'NAME/ACTION/...' strings)."""
    rc, out, err = run([xed] + mode + ["-ir", path, "-b", hex(base), "-v", "4", "-isa-set"])
    insts, errors, pending, opnds, nerr = [], [], None, [], None
    for line in out.splitlines():
        if line.startswith("XDIS "):
            m = XDIS_RE.match(line)
            if not m:
                errors.append({"kind": "unparsed_xdis", "line": line})
                continue
            addr, cat, ext, isa, hx, dis = m.groups()
            rec = {"offset": int(addr, 16), "len": len(hx) // 2, "hex": hx.lower(), "category": cat,
                   "extension": ext, "isa_set": isa, "disasm": dis.strip()}
            if pending:
                rec["iclass"], rec["iform"], rec["fields"] = pending
                rec["operands"] = opnds
            else:
                errors.append({"kind": "xdis_without_iclass_line", "offset": rec["offset"]})
            pending, opnds = None, []
            insts.append(rec)
        elif line.startswith("ERROR:"):
            m = ERR_RE.match(line)
            if m:
                kind, off, ln, pc, hx = m.groups()
                errors.append({"kind": "undecodable", "xed_error": kind, "offset": int(pc, 16), "len": int(ln),
                               "hex": hx.lower()})
            else:
                errors.append({"kind": "xed_error_line", "line": line})
            pending, opnds = None, []
        elif line.startswith("# Errors:"):
            nerr = int(line.split(":")[1])
        elif pending is not None and OPND_RE.match(line.strip()):
            opnds.append(OPND_RE.match(line.strip()).group(2))
        elif line.startswith(("YDIS:", "#", "Mapped", "ASSUMED BASE")) or not line.strip():
            continue
        else:
            m = HDR_RE.match(line)
            if m and (m.group(2) == m.group(1) or m.group(2).startswith(m.group(1) + "_")):
                pending, opnds = (m.group(1), m.group(2), parse_fields(m.group(3))), []
    if rc != 0:
        errors.append({"kind": "xed_exit", "rc": rc, "stderr": err.strip()[:500]})
    return insts, errors, nerr


def xed_single(xed, mode, hx):
    rc, out, err = run([xed] + mode + ["-d", hx])
    rec = {}
    for line in out.splitlines():
        k, _, v = line.partition(":")
        k = k.strip()
        if k in ("ICLASS", "CATEGORY", "EXTENSION", "IFORM", "ISA_SET"):
            rec[k.lower()] = v.strip()
        elif k == "ATTRIBUTES":
            rec["attributes"] = sorted(v.split())
    if "iclass" not in rec:
        rec["error"] = (out + err).strip()[:300]
    return hx, rec


LINE_RE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}[ \t])+)\s*(.*)$")


def objdump_sections(objdump, path, code_sections):
    rc, out, err = run([objdump, "-d", "--no-print-imm-hex", "--x86-asm-syntax=intel", path])
    if rc != 0:
        return None, "llvm-objdump failed: " + err.strip()[:300]
    order = [s for s in sorted(code_sections, key=lambda s: s["index"]) if s["size"] > 0]
    res, cur, k = {}, None, -1
    for line in out.splitlines():
        if line.startswith("Disassembly of section "):
            name = line[len("Disassembly of section "):].rstrip(":")
            k += 1
            if k >= len(order) or order[k]["name"] != name:
                return None, "section order mismatch at %r" % name
            cur = res.setdefault(order[k]["index"], {})
            continue
        m = LINE_RE.match(line)
        if m and cur is not None:
            cur[int(m.group(1), 16)] = (len(m.group(2).split()), m.group(3).strip())
    return res, None


# --------------------------------------------------------------------------------------------- per object
class Obj:
    def __init__(self, rec, data):
        self.rec, self.data = rec, data
        self.is_coff = rec["format"].startswith("coff")
        self.abi = "coff" if self.is_coff else "elf"
        self.secs = {s["index"]: s for s in rec["sections"]}
        self.funcs = rec["functions"]
        self.fstarts = collections.defaultdict(list)
        for f in self.funcs:
            self.fstarts[f["section"]].append((f["start"], f["end"], f["id"]))
        for v in self.fstarts.values():
            v.sort()
        self.relocs = {int(k): v for k, v in rec["relocs"].items()}
        self.roff = {k: [r["offset"] for r in v] for k, v in self.relocs.items()}
        self.sweep = collections.defaultdict(dict)       # section -> offset -> inst
        self.anchored = collections.defaultdict(dict)    # section -> offset -> inst (re-decoded starts)
        self.undecodable = collections.defaultdict(dict)
        # GCC cold parts: `<parent>.cold` / `<parent>.cold.N` defined in the same object (explicit map, not a
        # name prefix test)
        by_name = {}
        for f in self.funcs:
            for n in [f["name"]] + f.get("aliases", []):
                by_name.setdefault(n, f["id"])
        self.parent = {}
        for f in self.funcs:
            p = None
            for n in [f["name"]] + f.get("aliases", []):
                m = COLD_RE.match(n)
                if m and m.group(1) in by_name and by_name[m.group(1)] != f["id"]:
                    p = by_name[m.group(1)]
                    break
            self.parent[f["id"]] = p if p is not None else f["id"]
        self.family = collections.defaultdict(set)
        for fid, p in self.parent.items():
            self.family[p].add(fid)

    def func_at(self, sec, off):
        lst = self.fstarts.get(sec, [])
        i = bisect.bisect_right(lst, (off, float("inf"), 0)) - 1
        if i >= 0 and lst[i][0] <= off < lst[i][1]:
            return self.funcs[lst[i][2]]
        return None

    def family_of(self, fid):
        return self.family[self.parent[fid]]

    def relocs_in(self, sec, a, b):
        offs = self.roff.get(sec, [])
        i, j = bisect.bisect_left(offs, a), bisect.bisect_left(offs, b)
        return self.relocs[sec][i:j]

    def reloc_at(self, sec, off):
        offs = self.roff.get(sec, [])
        i = bisect.bisect_left(offs, off)
        return self.relocs[sec][i] if i < len(offs) and offs[i] == off else None

    def section_bytes(self, sec, a, b):
        s = self.secs[sec]
        return self.data[s["file_offset"] + a: s["file_offset"] + b]

    def is_padding(self, sec, a, b):
        if b <= a:
            return True
        blob = self.section_bytes(sec, a, b)
        if all(x == 0xCC for x in blob) or all(x == 0 for x in blob):
            return True
        sw = [i for o2, i in self.sweep[sec].items() if a <= o2 < b]
        return bool(sw) and sum(i["len"] for i in sw) == b - a and all(i.get("iclass") in NOP_CLASS for i in sw)


def reloc_target(o, r, ins_end=None, table_base=None):
    """Resolve one relocation to ('ext', name) or (section, offset) per its use (branch/lea or table entry)."""
    if not r["defined"]:
        return ("ext", r["sym_name"])
    S = r["sym_value"] + r["addend"]
    t, P = r["type"], r["offset"]
    if table_base is not None:
        if t == "PC32":
            return (r["target_section"], S - (P - table_base))
        if t.startswith("REL32"):
            k = int(t[6:]) if t != "REL32" else 0
            return (r["target_section"], S - (P + 4 + k - table_base))
        return (r["target_section"], S)
    if t in ("PC32", "PLT32") + GOT_RELOCS:
        return (r["target_section"], S + (ins_end - P))
    if t.startswith("REL32"):
        k = int(t[6:]) if t != "REL32" else 0
        return (r["target_section"], S + (ins_end - P - 4 - k))
    return (r["target_section"], S)


def disp_reloc(o, sec, off, ins):
    """The relocation on an instruction's displacement (XED POS_DISP), or None."""
    pos = ins.get("fields", {}).get("POS_DISP")
    if pos is None:
        return None
    return o.reloc_at(sec, off + int(pos))


# --------------------------------------------------------------------------------------------- the descent
class Descent:
    """One variant's counted set (record §4.2). Deterministic: every round computes a set closure and resolves
    every pending indirect branch against the complete reach set."""

    def __init__(self, o, entry, decode_at, od_obj, noreturn_fids, order="lifo"):
        self.o, self.entry, self.decode_at, self.od = o, entry, decode_at, od_obj
        self.noreturn_fids = set(noreturn_fids)
        self.order = order
        self.reach = {}
        self.succs = collections.defaultdict(list)
        self.preds = None
        self.callsite = {}
        self.calls = collections.Counter()          # (kind, name) -> count
        self.tailcalls = {}                         # site -> ('ext', name) | ('fid', id)
        self.site_gaps = collections.defaultdict(list)
        self.hardening = collections.Counter()
        self.noreturn_inferred = set()
        self.pending = {}                           # site -> 'jmp' | 'call'
        self.resolution = {}                        # site -> result dict (last round)
        self.res_edges = {}                         # site -> successors justified by the last resolution
        self.added_by = collections.defaultdict(set)
        self.unresolved_jumps = set()               # indirect jumps decided unresolved without a resolution
        self.fids = set()
        self.entry_fid = o.func_at(*entry)["id"]

    # ---- helpers
    def gap(self, site, cause, detail):
        self.site_gaps[site].append({"cause": cause, "offset": list(site) if site else None, "detail": detail})

    def kind_of(self, fid):
        f = self.o.funcs[fid]
        if fid == self.entry_fid:
            return "entry"
        if self.o.parent[fid] != fid:
            return "cold_part_of:%s" % self.o.funcs[self.o.parent[fid]]["name"]
        if not self.o.is_coff and f["bind"] in ("global", "weak") and f["visibility"] == 0:
            return "interposable"
        return "internal"

    def call_kind(self, fid):
        f = self.o.funcs[fid]
        if not self.o.is_coff and f["bind"] in ("global", "weak") and f["visibility"] == 0:
            return "interposable"                   # also for a recursive call to the entry function
        return "internal"

    def run(self):
        work = [(self.entry, "entry")]
        rounds = 0
        while True:
            rounds += 1
            self._closure(work)
            self._build_preds()
            new = []
            for site in sorted(self.pending):
                res = self._resolve(site)
                self.resolution[site] = res
                self.res_edges[site] = sorted(set(res.get("targets", [])))
                for t in res.get("targets", []):
                    self.added_by[site].add(t)
                    if t not in self.reach:
                        new.append((t, res.get("why", "internal")))
            self._build_preds()
            if not new or rounds > 100:
                break
            work = sorted(set(new))
        # a resolution that changed between rounds left targets the final resolution does not justify
        for site, res in sorted(self.resolution.items()):
            if self.added_by[site] - set(res.get("targets", [])):
                self.gap(site, "other", "indirect-branch resolution changed between descent rounds")
        for site, tl in self.res_edges.items():
            self.succs[site].extend(list(t) for t in tl)
        self.res_edges = {}
        self._build_preds()

    # ---- phase a: closure
    def _closure(self, work):
        o = self.o
        work = list(work)
        while work:
            (sec, off), why = work.pop() if self.order == "lifo" else work.pop(0)
            if (sec, off) in self.reach:
                continue
            site = (sec, off)
            f = o.func_at(sec, off)
            if f is None:
                if not any(g["detail"].startswith("control reaches") for g in self.site_gaps[site]):
                    self.gap(site, "other", "control reaches an address outside every function range")
                continue
            ins, how = self.decode_at(o, sec, off)
            if ins is None:
                if self.site_gaps.get(site):
                    continue
                odi = self.od.get(sec, {}).get(off)
                if odi and not odi[1].startswith("<unknown"):
                    self.gap(site, "xed_gap", "XED cannot decode; llvm-objdump: %s" % odi[1])
                else:
                    self.gap(site, "both_decoders_fail", "neither decoder decodes this address")
                continue
            self.fids.add(f["id"])
            self.reach[site] = dict(ins, section=sec, how=how, function=f["name"], fid=f["id"])
            self._step(site, f, ins, work)

    def _push(self, work, site, tgt, why, edge=True):
        work.append((tuple(tgt), why))
        if edge:
            self.succs[site].append(list(tgt))

    def _call_falls(self, site, f, ins, callee_label):
        """Fall-through after a call unless its next byte is the function end or padding up to the end."""
        end = site[1] + ins["len"]
        if end >= f["end"] or self.o.is_padding(site[0], end, f["end"]):
            self.noreturn_inferred.add(callee_label)
            return False
        return True

    def _step(self, site, f, ins, work):
        o = self.o
        sec, off = site
        end = off + ins["len"]
        ic = ins.get("iclass", "")
        iform = ins.get("iform", "")
        rin = o.relocs_in(sec, off, end)
        for r in rin:
            if r["offset"] + r["width"] > end:
                self.gap(site, "other", "relocation at %#x straddles the instruction end" % r["offset"])
            nm = r.get("sym_name") or ""
            if nm == "__security_cookie":
                self.hardening["gs_cookie_ref"] += 1
            if nm == "__stack_chk_guard":
                self.hardening["stack_protector_canary"] += 1
        if ic in ("ENDBR64", "ENDBR32"):
            self.hardening["endbr"] += 1
        if "fs:[0x28]" in ins.get("disasm", "").replace(" ", ""):
            self.hardening["stack_protector_canary"] += 1
        if ic == "OR" and re.search(r"ptr \[rsp(\+0x0)?\], 0x0$", ins.get("disasm", "")):
            self.hardening["stack_clash_probe"] += 1
        fall = True
        is_call = ic.startswith("CALL")
        if ic in TERMINATORS:
            fall = False
        elif "RELBR" in iform:
            w = 1 if "RELBRb" in iform else 4
            rr = [r for r in rin if r["offset"] == end - 4] if w == 4 else []
            if rr:
                tgt = reloc_target(o, rr[0], ins_end=end)
            else:
                disp = struct.unpack("<b" if w == 1 else "<i", bytes.fromhex(ins["hex"])[-w:])[0]
                tgt = (sec, end + disp)
            if is_call:
                if tgt[0] == "ext":
                    self.calls[("external", tgt[1])] += 1
                    if tgt[1] in ("__stack_chk_fail", "__stack_chk_fail_local"):
                        self.hardening["stack_chk_fail_call"] += 1
                    if tgt[1] == "__security_check_cookie":
                        self.hardening["gs_cookie_check_call"] += 1
                    fall = tgt[1] not in NORETURN_EXTERNALS and self._call_falls(site, f, ins, tgt[1])
                else:
                    cf_ = o.func_at(*tgt)
                    if cf_ is None or cf_["start"] != tgt[1]:
                        self.gap(site, "other", "call target %s is not a function start" % (tgt,))
                    else:
                        self.calls[(self.call_kind(cf_["id"]), cf_["name"])] += 1
                        self._push(work, site, tgt, "call", edge=False)
                        self.callsite[site] = list(tgt)
                        if cf_["id"] in self.noreturn_fids:
                            self.noreturn_inferred.add(cf_["name"])
                            fall = False
                        else:
                            fall = self._call_falls(site, f, ins, cf_["name"])
            elif ic == "JMP" or ic in COND_JUMPS:
                if tgt[0] == "ext":
                    self.calls[("external", tgt[1])] += 1
                    self.calls[("tail_call", tgt[1])] += 1
                    self.tailcalls[site] = ("ext", tgt[1])
                else:
                    tf = o.func_at(*tgt)
                    if tf is not None and tf["id"] not in o.family_of(f["id"]):
                        if tf["start"] == tgt[1]:
                            self.calls[(self.call_kind(tf["id"]), tf["name"])] += 1
                            self.calls[("tail_call", tf["name"])] += 1
                            self.tailcalls[site] = ("fid", tf["id"])
                        else:
                            self.gap(site, "other", "jump into the middle of %s" % tf["name"])
                    self._push(work, site, tgt, "jump")
                if ic == "JMP":
                    fall = False
        elif ic in ("JMP", "CALL_NEAR", "JMP_FAR", "CALL_FAR"):
            fall = self._indirect_now(site, f, ins, rin)
        if fall:
            if end >= f["end"]:
                self.gap(site, "other", "execution falls off the end of %s" % f["name"])
            else:
                self._push(work, site, (sec, end), "fallthrough")

    def _indirect_now(self, site, f, ins, rin):
        """Indirect branches decided by the instruction alone (memory operands through a relocated RIP slot);
        everything else is pending until the round's closure is complete. Returns the fall-through flag."""
        ic, iform = ins.get("iclass", ""), ins.get("iform", "")
        is_call = ic.startswith("CALL")
        if "MEM" in iform:
            mp = mem_parts(ins.get("fields", {}).get("MEM0"))
            r = disp_reloc(self.o, site[0], site[1], ins)
            if mp and mp[0] == "RIP" and mp[1] is None and r is not None:
                nm = r.get("sym_name") or "?"
                ok_imp = self.o.is_coff and nm.startswith("__imp_")
                ok_got = (not self.o.is_coff) and r["type"] in GOT_RELOCS and not r["defined"]
                if ok_imp or ok_got or nm in CFG_CHECK:
                    name = nm[len("__imp_"):] if nm.startswith("__imp_") else nm
                    self.calls[("external", name)] += 1
                    if not is_call:
                        self.calls[("tail_call", name)] += 1
                        self.tailcalls[site] = ("ext", name)
                        return False
                    return name not in NORETURN_EXTERNALS and self._call_falls(site, f, ins, name)
                detail = ("CFG dispatch through %s" % nm) if nm in CFG_DISPATCH else \
                    ("indirect %s through variable %s" % (ic, nm))
                self.gap(site, "unresolved_indirect", detail)
                if not is_call:
                    self.unresolved_jumps.add(site)
                return is_call and self._call_falls(site, f, ins, "indirect")
            if not is_call and mp and mp[0] is None and mp[1] and mp[2] == 8 and r is not None:
                self.pending[site] = "jmp"            # jmp [T + rI*8]
                return False
            self.gap(site, "unresolved_indirect", "indirect %s through memory %s" % (ic, ins.get("disasm", "")))
            if not is_call:
                self.unresolved_jumps.add(site)
            return is_call and self._call_falls(site, f, ins, "indirect")
        if "GPR" in iform:
            self.pending[site] = "call" if is_call else "jmp"
            return False                              # a pending call's fall-through is decided on resolution
        self.gap(site, "unresolved_indirect", "indirect %s" % ic)
        if not is_call:
            self.unresolved_jumps.add(site)
        return is_call and self._call_falls(site, f, ins, "indirect")

    # ---- phase b: resolution of pending indirect branches against the complete reach set
    def _build_preds(self):
        self.preds = collections.defaultdict(list)
        for s, lst in list(self.succs.items()) + list(self.res_edges.items()):
            if s not in self.reach:
                continue
            for t in lst:
                t = tuple(t)
                if t in self.reach:
                    self.preds[t].append(s)
        for t in self.preds:
            self.preds[t] = sorted(set(self.preds[t]))

    def _fam_ids(self, site):
        return self.o.family_of(self.reach[site]["fid"])

    def _is_family_entry(self, site):
        ins = self.reach[site]
        p = self.o.funcs[self.o.parent[ins["fid"]]]
        return site == (p["section"], p["start"])

    def back_chain(self, site):
        """Straight-line predecessors of `site` inside its basic block, nearest first. Stops at a block start
        (several or no predecessors, or a predecessor with several successors), at a call, and at the family
        boundary."""
        out, cur, fams = [], site, self._fam_ids(site)
        while len(out) < 64 and not self._is_family_entry(cur):
            ps = self.preds.get(cur, [])
            if len(ps) != 1:
                break
            p = ps[0]
            pi = self.reach[p]
            if pi["fid"] not in fams or pi.get("iclass", "").startswith("CALL"):
                break
            succ_p = {tuple(x) for x in self.succs.get(p, [])} | {tuple(x) for x in self.res_edges.get(p, [])}
            if succ_p != {cur}:
                break
            out.append(p)
            cur = p
        return out

    def reaching_defs(self, site, regf):
        """Sites of every instruction that defines register family regf and reaches `site` over intra-procedural
        predecessors. (None, reason) if some path reaches the family entry without a definition, leaves the
        family, or crosses a call that clobbers a caller-saved regf."""
        fams = self._fam_ids(site)
        if self._is_family_entry(site):
            return None, "no definition between the function entry and the use"
        stack, seen, defs = list(self.preds.get(site, [])), set(), set()
        if not stack:
            return None, "no predecessor"
        while stack:
            p = stack.pop()
            if p in seen:
                continue
            seen.add(p)
            pi = self.reach[p]
            if pi["fid"] not in fams:
                return None, "a path leaves the function"
            if regf in written(pi):
                defs.add(p)
                continue
            if pi.get("iclass", "").startswith("CALL") and regf in CALLER_SAVED[self.o.abi]:
                return None, "clobbered by the call at %#x" % p[1]
            if self._is_family_entry(p) or not self.preds.get(p):
                return None, "no definition on a path from the function entry"
            stack.extend(self.preds[p])
        return defs, None

    def _lea_target(self, d):
        """For `lea reg,[rip+X]` with a relocation: the resolved target, else None."""
        di = self.reach[d]
        if di.get("iclass") != "LEA":
            return None
        mp = mem_parts(di.get("fields", {}).get("AGEN"))
        if not mp or mp[0] != "RIP" or mp[1] is not None:
            return None
        r = disp_reloc(self.o, d[0], d[1], di)
        if r is None:
            return None
        return reloc_target(self.o, r, ins_end=d[1] + di["len"])

    def value_sources(self, site, regf, depth=0):
        """Reaching definitions of regf at `site`, looking through whole-register copies (copy_source: a spill of
        a table base to an XMM register and back, a mov between GPRs). Returns (set of (site, family), reason)."""
        defs, why = self.reaching_defs(site, regf)
        if defs is None:
            return None, why
        out = set()
        for d in sorted(defs):
            src = copy_source(self.reach[d], regf)
            if src is not None:
                if depth >= 4:
                    return None, "register copy chain longer than 4"
                sub, why = self.value_sources(d, src, depth + 1)
                if sub is None:
                    return None, why
                out |= sub
            else:
                out.add((d, regf))
        return out, None

    def _defs_all_lea(self, site, regf):
        """All reaching definitions of regf at `site` (through register copies) are `lea reg,[rip+X]` with one
        and the same X."""
        srcs, why = self.value_sources(site, regf)
        if srcs is None:
            return None, why
        tg = set()
        for d, rf in sorted(srcs):
            t = self._lea_target(d)
            di = self.reach[d]
            if t is None or GPR_WIDTH.get(di.get("fields", {}).get("REG0")) != 64:
                return None, "definition at %#x is not lea %s,[rip+X]" % (d[1], rf)
            tg.add(t)
        if len(tg) != 1:
            return None, "%s has %d different lea targets" % (regf, len(tg))
        return next(iter(tg)), None

    def _resolve(self, site):
        kind = self.pending[site]
        ins = self.reach[site]
        f = self.o.funcs[ins["fid"]]
        if kind == "call":
            name, why = self._import_register(site)
            if name is None:
                res = {"kind": "unresolved", "detail": "indirect CALL_NEAR through a register (%s)" % why}
            else:
                res = {"kind": "import_call", "name": name}
            falls = (res["kind"] == "unresolved" or res["name"] not in NORETURN_EXTERNALS) and \
                self._call_falls(site, f, ins, res.get("name", "indirect"))
            end = site[1] + ins["len"]
            if falls:
                res["targets"] = [(site[0], end)]
                res["why"] = "fallthrough"
            return res
        # jmp
        if "GPR" in ins.get("iform", ""):
            regf = fam(ins.get("fields", {}).get("REG0"))
            chain = self.back_chain(site)
            first = next((p for p in chain if regf in written(self.reach[p])), None)
            if first is not None and self.reach[first].get("iclass") == "ADD":
                t, why = self._table(site, chain)
                if t is not None:
                    return {"kind": "table", "table": t, "targets": [tuple(x) for x in t["targets"]],
                            "why": "jump"}
                return {"kind": "unresolved", "detail": why}
            name, why = self._import_register(site)
            if name is not None:
                return {"kind": "import_tail_call", "name": name}
            return {"kind": "unresolved", "detail": "indirect jump through a register (%s)" % why}
        t, why = self._table(site, self.back_chain(site))
        if t is not None:
            return {"kind": "table", "table": t, "targets": [tuple(x) for x in t["targets"]], "why": "jump"}
        return {"kind": "unresolved", "detail": why}

    def _import_register(self, site):
        ins = self.reach[site]
        regf = fam(ins.get("fields", {}).get("REG0"))
        if not regf:
            return None, "no register operand"
        defs, why = self.reaching_defs(site, regf)
        if defs is None:
            return None, why
        names = set()
        for d in defs:
            di = self.reach[d]
            mp = mem_parts(di.get("fields", {}).get("MEM0"))
            r = disp_reloc(self.o, d[0], d[1], di)
            reg0 = di.get("fields", {}).get("REG0")
            if di.get("iclass") != "MOV" or fam(reg0) != regf or GPR_WIDTH.get(reg0) != 64 or not mp \
                    or mp[0] != "RIP" or r is None:
                return None, "definition at %#x is not a load of an import or GOT slot" % d[1]
            nm = r.get("sym_name") or ""
            ok = (self.o.is_coff and nm.startswith("__imp_")) or \
                 ((not self.o.is_coff) and r["type"] in GOT_RELOCS and not r["defined"])
            if not ok:
                return None, "definition at %#x loads %s, not an import or GOT slot" % (d[1], nm)
            names.add(nm[len("__imp_"):] if nm.startswith("__imp_") else nm)
        if len(names) != 1:
            return None, "%d different import slots" % len(names)
        return next(iter(names)), None

    def _table(self, site, chain):
        """Jump table loaded by the indirect jump's own address computation (see the module docstring).
        Returns (table, None) or (None, reason)."""
        o, ins = self.o, self.reach[site]
        fams = self._fam_ids(site)
        if "GPR" in ins.get("iform", ""):
            rx = fam(ins["fields"].get("REG0"))
            idx = next((k for k, p in enumerate(chain) if rx in written(self.reach[p])), None)
            if idx is None:
                return None, "jump-table shape: no definition of %s in the jump's block" % rx
            add_s = chain[idx]
            add = self.reach[add_s]
            a0, a1 = add["fields"].get("REG0"), add["fields"].get("REG1")
            if add.get("iclass") != "ADD" or fam(a0) != rx or GPR_WIDTH.get(a0) != 64 or fam(a1) is None \
                    or GPR_WIDTH.get(a1) != 64 or "IMM0" in add["fields"]:
                return None, "jump-table shape: %s is not defined by add %s,reg64" % (rx, rx)
            rb = fam(a1)
            rest = chain[idx + 1:]
            k2 = next((k for k, p in enumerate(rest) if rx in written(self.reach[p])), None)
            if k2 is None:
                return None, "jump-table shape: no table load into %s" % rx
            if any(rb in written(self.reach[p]) for p in rest[:k2]):
                return None, "jump-table shape: %s redefined between the load and the add" % rb
            load_s = rest[k2]
            ld = self.reach[load_s]
            mp = mem_parts(ld.get("fields", {}).get("MEM0"))
            r0 = ld["fields"].get("REG0")
            okdst = (ld.get("iclass") == "MOVSXD" and fam(r0) == rx and GPR_WIDTH.get(r0) == 64) or \
                    (ld.get("iclass") == "MOV" and fam(r0) == rx and GPR_WIDTH.get(r0) == 32)
            if not okdst or not mp or fam(mp[0]) != rb or not mp[1] or mp[2] != 4:
                return None, "jump-table shape: load %r is not [%s+index*4]" % (ld.get("disasm"), rb)
            ri = fam(mp[1])
            dr = disp_reloc(o, load_s[0], load_s[1], ld)
            if o.is_coff and dr is not None and dr["type"] == "ADDR32NB" and dr["defined"]:
                base_t, why = self._defs_all_lea(load_s, rb)
                if base_t is None or base_t != ("ext", "__ImageBase"):
                    return None, "jump-table shape: base %s is not __ImageBase (%s)" % (rb, why or base_t)
                T = (dr["target_section"], dr["sym_value"] + dr["addend"])
                etype, stride = "ADDR32NB", 4
            elif dr is None and mp[3] == 0:
                T, why = self._defs_all_lea(load_s, rb)
                if T is None or T[0] == "ext":
                    return None, "jump-table shape: base %s (%s)" % (rb, why or "external")
                etype, stride = ("REL32" if o.is_coff else "PC32"), 4
            else:
                return None, "jump-table shape: unrecognised displacement on the table load"
            bound_from = load_s
        else:
            mp = mem_parts(ins.get("fields", {}).get("MEM0"))
            dr = disp_reloc(o, site[0], site[1], ins)
            if not mp or mp[0] is not None or not mp[1] or mp[2] != 8 or dr is None or not dr["defined"]:
                return None, "jump-table shape: unrecognised memory jump"
            ri = fam(mp[1])
            T = (dr["target_section"], dr["sym_value"] + dr["addend"])
            etype, stride = ("ADDR64" if o.is_coff else "64"), 8
            bound_from = site
        n, extra, why = self._bound(bound_from, ri, 0)
        if n is None:
            return None, "jump-table extent: %s" % why
        tsec, tbase = T
        for (s2, o2), i2 in sorted(self.reach.items()):
            for r in o.relocs_in(s2, o2, o2 + i2["len"]):
                if r["defined"] and r["target_section"] == tsec:
                    t2 = reloc_target(o, r, ins_end=o2 + i2["len"])
                    if t2[0] == tsec and tbase < t2[1] < tbase + n * stride:
                        return None, "jump-table extent: entries [%#x,%#x) overlap the address %#x referenced at %#x" \
                            % (tbase, tbase + n * stride, t2[1], o2)
        targets = []
        for k in range(n):
            r = o.reloc_at(tsec, tbase + k * stride)
            bad = None
            if r is None or r["type"] != etype or r["width"] != stride or not r["defined"]:
                bad = "no %s relocation" % etype
            else:
                tgt = reloc_target(o, r, table_base=tbase)
                tf = o.func_at(*tgt)
                if tf is None or tf["id"] not in fams:
                    bad = "target %s outside the jump's function" % (tgt,)
                elif tgt[1] not in o.sweep[tgt[0]]:
                    bad = "target %s is not an instruction start" % (tgt,)
            if bad:
                return None, "jump table truncated at entry %d of %d (%s)" % (k, n, bad)
            targets.append(tuple(tgt))
        table = {"section": tsec, "section_name": o.secs[tsec]["name"], "start": tbase, "end": tbase + n * stride,
                 "entry_type": etype, "n_entries": n, "bound": extra.get("bound"), "site": list(site),
                 "targets": sorted(set(targets)), "byte_table": extra.get("byte_table")}
        return table, None

    def _bound(self, start, ri, depth):
        """Number of table entries from the guarding bound on index family ri. Returns (n, extra, reason)."""
        chain = self.back_chain(start)
        for p in chain:
            pi = self.reach[p]
            if ri not in written(pi):
                continue
            ic, fl = pi.get("iclass"), pi.get("fields", {})
            r0, r1 = fl.get("REG0"), fl.get("REG1")
            if ic == "MOV" and pi.get("iform", "").startswith("MOV_GPRv_GPRv") and fam(r0) == ri and fam(r1) \
                    and GPR_WIDTH.get(r0) == GPR_WIDTH.get(r1) and GPR_WIDTH.get(r0, 0) >= 32:
                ri = fam(r1)                               # mov eI,eJ / mov rI,rJ (zero extension or copy)
                continue
            if ic == "CDQE" and ri == "RAX":
                continue
            if ic == "MOVSXD" and fam(r0) == ri and fam(r1) and GPR_WIDTH.get(r1) == 32 and "MEM0" not in fl:
                ri = fam(r1)
                continue
            if ic == "AND" and fam(r0) == ri and GPR_WIDTH.get(r0, 0) >= 32:
                m = imm_value(pi)
                if m is not None and m >= 0 and (m + 1) & m == 0:
                    return m + 1, {"bound": "and %#x" % m}, None
                return None, {}, "index masked by a non power-of-two"
            if ic == "MOVZX" and depth == 0 and self.o.is_coff and fam(r0) == ri:
                mp = mem_parts(fl.get("MEM0"))
                dr = disp_reloc(self.o, p[0], p[1], pi)
                if mp and mp[0] and mp[1] and mp[2] == 1 and dr is not None and dr["type"] == "ADDR32NB" \
                        and dr["defined"] and "byte" in pi.get("disasm", ""):
                    base_t, why = self._defs_all_lea(p, fam(mp[0]))
                    if base_t != ("ext", "__ImageBase"):
                        return None, {}, "byte index table base is not __ImageBase (%s)" % why
                    n2, ex2, why2 = self._bound(p, fam(mp[1]), 1)
                    if n2 is None:
                        return None, {}, "byte index table: %s" % why2
                    t2 = (dr["target_section"], dr["sym_value"] + dr["addend"])
                    blob = self.o.section_bytes(t2[0], t2[1], t2[1] + n2)
                    if len(blob) != n2:
                        return None, {}, "byte index table runs past its section"
                    return max(blob) + 1, {"bound": "byte table (%s)" % ex2.get("bound"),
                                           "byte_table": [self.o.secs[t2[0]]["name"], t2[0], t2[1], t2[1] + n2]}, None
            return None, {}, "index %s redefined by %s at %#x" % (ri, ic, p[1])
        head = chain[-1] if chain else start
        ps = self.preds.get(head, [])
        if len(ps) != 1:
            return None, {}, "no guarding compare (block has %d predecessors)" % len(ps)
        j = ps[0]
        ji = self.reach[j]
        jic = ji.get("iclass")
        fall = head == (j[0], j[1] + ji["len"])
        if jic in ("JNBE", "JNB") and fall:
            inclusive = jic == "JNBE"
        elif jic in ("JBE", "JB") and not fall:
            inclusive = jic == "JBE"
        else:
            return None, {}, "no guarding compare (block entered from %s)" % jic
        for p in self.back_chain(j):
            pi = self.reach[p]
            fl = pi.get("fields", {})
            if writes_flags(pi):
                r0 = fl.get("REG0")
                m = imm_value(pi)
                if pi.get("iclass") == "CMP" and fam(r0) == ri and GPR_WIDTH.get(r0, 0) >= 32 and m is not None \
                        and m >= 0 and "MEM0" not in fl:
                    return (m + 1 if inclusive else m), {"bound": "cmp %#x; %s" % (m, jic.lower())}, None
                return None, {}, "flags for %s set by %s, not cmp %s,imm" % (jic, pi.get("iclass"), ri)
            if ri in written(pi):
                return None, {}, "index %s redefined between the compare and %s" % (ri, jic)
        return None, {}, "no compare before %s in its block" % jic


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--xed", required=True)
    ap.add_argument("--objdump", required=True)
    ap.add_argument("--norm", default=os.path.join(HERE, "..", "class", "objdump_norm.csv"))
    ap.add_argument("--fp-class", default=os.path.join(HERE, "..", "class", "fp_class.csv"))
    ap.add_argument("-j", "--jobs", type=int, default=2)
    ap.add_argument("--attr-cache")
    ap.add_argument("--worklist-order", choices=("lifo", "fifo"), default="lifo",
                    help="order of the descent's work list; the outputs must not depend on it (regression check)")
    a = ap.parse_args()
    mode = ["-64", "-cet"]
    os.makedirs(a.outdir, exist_ok=True)
    tmp = os.path.join(a.outdir, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    if os.path.exists(os.path.join(a.outdir, "instructions.jsonl")):
        os.remove(os.path.join(a.outdir, "instructions.jsonl"))
    rc, ver, _ = run([a.xed, "-version"])
    xed_version = (re.search(r"XED version: \[(.*?)\]", ver) or [None, "?"])[1]
    man = json.load(open(a.manifest))
    norm = x0_norm.Normalizer(a.norm)
    with open(a.fp_class, encoding="utf-8", newline="") as f:
        fpc = {r["iclass"]: r["fp_sensitive"] == "yes" for r in csv.DictReader(f)}
    hashes = {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in (a.norm, a.fp_class)}
    anomalies = []

    def anomaly(sev, kind, **kw):
        anomalies.append(dict(severity=sev, kind=kind, **kw))

    objs = []
    for orec in man["objects"]:
        data = open(orec["object"], "rb").read()
        if hashlib.sha256(data).hexdigest() != orec["sha256"]:
            raise SystemExit("object changed since extraction: %s" % orec["object"])
        objs.append(Obj(orec, data))

    # ---- 1. sweep every function range
    jobs = []
    for oi, o in enumerate(objs):
        for f in o.funcs:
            fn = os.path.join(tmp, "o%d_f%d.bin" % (oi, f["id"]))
            with open(fn, "wb") as fh:
                fh.write(o.section_bytes(f["section"], f["start"], f["end"]))
            jobs.append((oi, f, fn))
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        results = list(ex.map(lambda j: (j, xed_sweep(a.xed, mode, j[2], j[1]["start"])), jobs))
    for (oi, f, fn), (insts, errors, nerr) in results:
        o = objs[oi]
        for i in insts:
            o.sweep[f["section"]][i["offset"]] = i
        for e in errors:
            if e["kind"] == "undecodable":
                o.undecodable[f["section"]][e["offset"]] = e
            else:
                anomaly("error", "xed_" + e["kind"], object=o.rec["object"], function=f["name"], detail=e)

    def decode_at(o, sec, off):
        """Instruction starting at (sec, off): sweep record, or an anchored decode from that byte."""
        if off in o.sweep[sec]:
            return o.sweep[sec][off], "sweep"
        if off in o.anchored[sec]:
            return o.anchored[sec][off], "anchored"
        f = o.func_at(sec, off)
        end = f["end"] if f else o.secs[sec]["size"]
        fn = os.path.join(tmp, "anch_%d_%d_%x.bin" % (objs.index(o), sec, off))
        with open(fn, "wb") as fh:
            fh.write(o.section_bytes(sec, off, end))
        insts, errors, _ = xed_sweep(a.xed, mode, fn, off)
        for i in insts:
            o.anchored[sec].setdefault(i["offset"], i)
        if off in o.anchored[sec]:
            return o.anchored[sec][off], "anchored"
        return None, "undecodable"

    # ---- attribute pass
    cache = {}
    if a.attr_cache and os.path.exists(a.attr_cache):
        cache = json.load(open(a.attr_cache))
        if cache.get("_xed_version") != xed_version or cache.get("_xed_mode") != mode:
            cache = {}
    cache["_xed_version"], cache["_xed_mode"] = xed_version, mode

    # ---- objdump per object
    od = {}
    for oi, o in enumerate(objs):
        code = [s for s in o.rec["sections"] if s["is_code"] and s["size"] > 0]
        res, err = objdump_sections(a.objdump, o.rec["object"], code)
        if err:
            anomaly("error", "objdump_unavailable", object=o.rec["object"], detail=err)
            od[oi] = {}
        else:
            od[oi] = {k: norm.merge_lines(v) for k, v in res.items()}

    # ---- 2. recursive descent per variant
    variants_out, xdis_all = [], []
    for v in man["variants"]:
        oi = v["object_index"]
        o = objs[oi]
        vid = "%s:%s:%s" % (man.get("label"), v["table"], v["slot"])
        gaps = []
        if v["gap"]:
            gaps.append({"cause": v["gap"], "offset": None, "detail": v["detail"]})
        rec = {"config": man.get("label"), "object": os.path.basename(o.rec["object"]), "table": v["table"],
               "slot": v["slot"], "source_function": v["source_function"],
               "symbol": (v["resolved"] or {}).get("function"),
               "slot_name_check": v.get("name_check"),
               "coverage": {"slot_resolved": bool(v["resolved"] and v["resolved"].get("function")), "gaps": gaps}}
        if not rec["coverage"]["slot_resolved"]:
            variants_out.append(rec)
            continue
        entry = (v["resolved"]["section"], v["resolved"]["offset"])
        # no-return fixpoint over internal callees (the set only grows)
        noret = set()
        for _ in range(50):
            d = Descent(o, entry, decode_at, od[oi], noret, a.worklist_order)
            d.run()
            ret = family_returns(o, d)
            new_noret = {fid for fid in d.fids if d.kind_of(fid) == "internal" and not ret.get(o.parent[fid], True)}
            if new_noret <= noret:
                break
            noret |= new_noret
        reach = d.reach
        for site in sorted(d.site_gaps):
            for g in d.site_gaps[site]:
                gaps.append(g)
        tables, indirect, data_regions = [], 0, []
        for site in sorted(d.resolution):
            res = d.resolution[site]
            ins = reach[site]
            if res["kind"] == "table":
                indirect += 1
                t = res["table"]
                tables.append(t)
                if o.secs[t["section"]]["is_code"]:
                    data_regions.append((t["section"], t["start"], t["end"]))
                if t.get("byte_table"):
                    bt = t["byte_table"]
                    data_regions.append((bt[1], bt[2], bt[3]))
            elif res["kind"] in ("import_call", "import_tail_call"):
                d.calls[("external", res["name"])] += 1
                if res["kind"] == "import_tail_call":
                    d.calls[("tail_call", res["name"])] += 1
            else:
                indirect += 1
                gaps.append({"cause": "unresolved_indirect", "offset": list(site), "detail": res["detail"]})
        indirect += sum(1 for g in gaps if g["cause"] == "unresolved_indirect" and tuple(g["offset"] or ())
                        not in d.resolution)
        # overlapping reachable decodes
        by_sec = collections.defaultdict(list)
        for (sec, off), ins in reach.items():
            by_sec[sec].append((off, off + ins["len"]))
        for sec, spans in sorted(by_sec.items()):
            spans.sort()
            for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
                if b0 < a1:
                    gaps.append({"cause": "other", "offset": [sec, b0],
                                 "detail": "overlapping reachable decodes at %#x and %#x" % (a0, b0)})
        # closure functions and their ranges
        closure = []
        for fid in sorted(d.fids, key=lambda i: (o.funcs[i]["section"], o.funcs[i]["start"])):
            fx = o.funcs[fid]
            closure.append({"symbol": fx["name"], "kind": d.kind_of(fid), "section": o.secs[fx["section"]]["name"],
                            "section_index": fx["section"], "start": fx["start"], "end": fx["end"],
                            "range_source": fx["range_source"], "range_check": fx.get("range_check")})
            if o.is_coff and fx.get("range_check") == "mismatch":
                gaps.append({"cause": "range_mismatch", "offset": [fx["section"], fx["start"]],
                             "detail": "; ".join(fx.get("range_check_detail", []))})
            if fx["range_source"] == "next_symbol":
                gaps.append({"cause": "range_mismatch", "offset": [fx["section"], fx["start"]],
                             "detail": "%s: range taken up to the next symbol (no size, COMDAT or .pdata)" % fx["name"]})
        # relocations inside closure ranges that are not inside reachable instructions -> data
        reach_spans = collections.defaultdict(list)
        for (sec, off), ins in reach.items():
            reach_spans[sec].append((off, off + ins["len"]))
        for s in reach_spans.values():
            s.sort()
        for c in closure:
            sec = c["section_index"]
            spans = reach_spans.get(sec, [])
            starts = [x[0] for x in spans]
            for r in o.relocs_in(sec, c["start"], c["end"]):
                k = bisect.bisect_right(starts, r["offset"]) - 1
                inside = k >= 0 and spans[k][0] <= r["offset"] < spans[k][1]
                if not inside and not any(dd[0] == sec and dd[1] <= r["offset"] < dd[2] for dd in data_regions):
                    data_regions.append((sec, r["offset"], r["offset"] + r["width"]))
        # 3. unreachable bytes
        unreach = {"padding_bytes": 0, "orphan_bytes": 0, "orphan_ranges": [], "data_bytes": 0,
                   "referenced_non_instruction": []}
        orphan_insts = []
        for c in closure:
            sec = c["section_index"]
            marks = sorted(reach_spans.get(sec, []) + [(dd[1], dd[2]) for dd in data_regions if dd[0] == sec])
            cur = c["start"]
            holes = []
            for s0, e0 in marks:
                if e0 <= c["start"] or s0 >= c["end"]:
                    continue
                if s0 > cur:
                    holes.append((cur, min(s0, c["end"])))
                cur = max(cur, e0)
            if cur < c["end"]:
                holes.append((cur, c["end"]))
            for h0, h1 in holes:
                if o.is_padding(sec, h0, h1):
                    unreach["padding_bytes"] += h1 - h0
                else:
                    sw = [i for off2, i in sorted(o.sweep[sec].items()) if h0 <= off2 < h1]
                    unreach["orphan_bytes"] += h1 - h0
                    unreach["orphan_ranges"].append([c["section"], h0, h1])
                    orphan_insts += [dict(i, section=sec, function=c["symbol"], role="orphan") for i in sw]
        unreach["data_bytes"] = sum(dd[2] - dd[1] for dd in data_regions if o.secs[dd[0]]["is_code"])
        closure_ids = {(c["section_index"], c["start"], c["end"]) for c in closure}
        refs = set()
        for (sec, off2), ins in reach.items():
            for r in o.relocs_in(sec, off2, off2 + ins["len"]):
                if not r["defined"] or not o.secs.get(r["target_section"], {}).get("is_code"):
                    continue
                tgt = reloc_target(o, r, ins_end=off2 + ins["len"])
                if tgt[0] == "ext" or tgt in reach:
                    continue
                if any(dd[0] == tgt[0] and dd[1] <= tgt[1] < dd[2] for dd in data_regions):
                    continue
                if any(cs == tgt[0] and c0 <= tgt[1] < c1 for cs, c0, c1 in closure_ids):
                    refs.add((o.secs[tgt[0]]["name"], tgt[1], off2))
        unreach["referenced_non_instruction"] = sorted([list(x) for x in refs])
        # 4a. sweep cross-check
        sweep_only, descent_only = [], []
        for c in closure:
            sec = c["section_index"]
            for off2, i in sorted(o.sweep[sec].items()):
                if c["start"] <= off2 < c["end"] and (sec, off2) not in reach:
                    in_data = any(dd[0] == sec and dd[1] <= off2 < dd[2] for dd in data_regions)
                    in_orphan = any(r[1] <= off2 < r[2] for r in unreach["orphan_ranges"] if r[0] == c["section"])
                    is_pad = i.get("iclass") in NOP_CLASS
                    if not (in_data or in_orphan or is_pad):
                        sweep_only.append([c["section"], off2, i.get("iclass")])
        for (sec, off2), ins in sorted(reach.items()):
            if ins["how"] == "anchored":
                descent_only.append([o.secs[sec]["name"], off2, ins.get("iclass")])
        # 4b. cross-decoder
        disagreements = []
        for (sec, off2), ins in sorted(reach.items()):
            odi = od[oi].get(sec, {}).get(off2)
            acc = None
            if odi and odi[0] == ins["len"]:
                acc, _ = norm.iclasses(odi[1])
            if odi is None or odi[0] != ins["len"] or acc is None or ins.get("iclass") not in acc:
                fs = fpc.get(ins.get("iclass"), True) or any(fpc.get(x, True) for x in (acc or []))
                disagreements.append({"config": man.get("label"), "variant": vid, "section": o.secs[sec]["name"],
                                      "offset": off2, "xed_iclass": ins.get("iclass"), "xed_len": ins["len"],
                                      "objdump": odi, "normalised": sorted(acc or []), "fp_sensitive": bool(fs),
                                      "resolution": None})
        # attributes for reachable encodings
        need = sorted({i["hex"] for i in reach.values()} - set(cache))
        with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for hx, r in ex.map(lambda h: xed_single(a.xed, mode, h), need):
                cache[hx] = r
        # metrics
        iforms, iclasses, cats = collections.Counter(), collections.Counter(), collections.Counter()
        evex_rc = 0
        for (sec, off2), ins in sorted(reach.items()):
            c = cache.get(ins["hex"], {})
            if c.get("iclass") and c["iclass"] != ins.get("iclass"):
                anomaly("error", "xed_pass_disagreement", variant=vid, offset=off2, sweep=ins.get("iclass"),
                        single=c["iclass"])
            ins["attributes"] = c.get("attributes", [])
            iforms[ins.get("iform")] += 1
            iclasses[ins.get("iclass")] += 1
            cats["S" if ins.get("extension") in S_EXTENSIONS else "G"] += 1
            flds = ins.get("fields", {})
            if ("ROUNDC" in flds or "SAE" in flds) and not any(op.startswith(("MEM", "AGEN")) for op in ins.get("operands", [])):
                evex_rc += 1
        calls = d.calls
        ext_calls = sorted({n for (k, n) in calls if k == "external"})
        fp_deps = sorted(n for n in ext_calls if n not in NON_FP_EXTERNALS)
        for n in fp_deps:
            gaps.append({"cause": "fp_trust_dep", "offset": None, "detail": "external call to %s" % n})
        p2 = sum(n for ic, n in iclasses.items() if FMA_RE.match(ic or ""))
        p2 += sum(1 for ins in reach.values() if ins.get("extension") == FMA4_EXT)
        gaps.sort(key=lambda g: (g["cause"], json.dumps(g.get("offset")), g.get("detail") or ""))
        rec["coverage"]["gaps"] = gaps
        rec.update({
            "closure": closure,
            "n_instructions": len(reach),
            "iforms": dict(sorted(iforms.items())), "iclasses": dict(sorted(iclasses.items())),
            "categories": dict(sorted(cats.items())),
            "fp_sensitive": sorted(ic for ic in iclasses if fpc.get(ic, True)),
            "fp_sensitive_missing_from_fp_class": sorted(ic for ic in iclasses if ic not in fpc),
            "p2_fma": p2,
            "evex_static_rounding": evex_rc,
            "lift_blockers": {
                "internal_calls": sorted({n for (k, n) in calls if k == "internal"}),
                "interposable_calls": sorted({n for (k, n) in calls if k == "interposable"}),
                "external_calls": ext_calls, "fp_trust_deps": fp_deps,
                "tail_calls": sorted({n for (k, n) in calls if k == "tail_call"}),
                "noreturn_inferred": sorted(d.noreturn_inferred),
                "indirect_branches": indirect, "jump_tables": len(tables),
                "hardening": dict(sorted(d.hardening.items()))},
            "jump_tables": [{k2: t[k2] for k2 in ("section_name", "start", "end", "entry_type", "n_entries", "bound",
                                                  "site", "byte_table")} for t in tables],
            "unreachable": unreach,
            "sweep_crosscheck": {"sweep_only": sweep_only, "descent_only_anchored": descent_only},
            "crossdecoder_disagreements": len(disagreements),
        })
        variants_out.append(rec)
        xdis_all += disagreements
        for (sec, off2), ins in sorted(reach.items()):
            succ = sorted({tuple(x) for x in d.succs.get((sec, off2), [])})
            orphan_insts.append(dict(ins, role="reachable", variant=vid, succ=[list(x) for x in succ],
                                     call=d.callsite.get((sec, off2)), entry=[sec, off2] == list(entry)))
        with open(os.path.join(a.outdir, "instructions.jsonl"), "a") as fh:
            for i in orphan_insts:
                i2 = {k: v2 for k, v2 in i.items()}
                i2["variant"] = vid
                fh.write(json.dumps(i2, sort_keys=True) + "\n")

    if a.attr_cache:
        with open(a.attr_cache, "w") as f:
            json.dump(cache, f)
    # summary
    gap_counts = collections.Counter(g["cause"] for v in variants_out for g in v["coverage"]["gaps"])
    tooling = sum(n for c, n in gap_counts.items() if c in TOOLING)
    out = {"xed": a.xed, "xed_version": xed_version, "xed_mode": mode, "objdump": a.objdump, "label": man.get("label"),
           "manifest": os.path.abspath(a.manifest), "frozen_inputs_sha256": hashes,
           "worklist_order": a.worklist_order,
           "n_variants": len(variants_out), "n_resolved": sum(1 for v in variants_out if v["coverage"]["slot_resolved"]),
           "gap_counts": dict(sorted(gap_counts.items())), "tooling_gaps": tooling,
           "crossdecoder_disagreements": len(xdis_all),
           "crossdecoder_fp_sensitive": sum(1 for d in xdis_all if d["fp_sensitive"]),
           "u_iforms": len({f for v in variants_out for f in v.get("iforms", {})}),
           "u_iclasses": len({c for v in variants_out for c in v.get("iclasses", {})}),
           "anomalies": dict(collections.Counter(x["severity"] for x in anomalies))}
    json.dump(variants_out, open(os.path.join(a.outdir, "variants.json"), "w"), indent=1, sort_keys=True)
    json.dump({"disagreements": xdis_all}, open(os.path.join(a.outdir, "crossdecoder.json"), "w"), indent=1)
    json.dump(anomalies, open(os.path.join(a.outdir, "anomalies.json"), "w"), indent=1)
    json.dump(out, open(os.path.join(a.outdir, "summary.json"), "w"), indent=1)
    for fn in os.listdir(tmp):
        os.remove(os.path.join(tmp, fn))
    os.rmdir(tmp)
    print(json.dumps(out, indent=1))
    return 1 if (tooling or xdis_all or any(x["severity"] == "error" for x in anomalies)) else 0


def family_returns(o, d):
    """For every function family in the descent: can it return? Least fixpoint: a family returns if it has a
    reachable RET, an unresolved indirect jump, or a tail call to an external (not NORETURN_EXTERNALS), an
    interposable function, an import, or an internal family that returns."""
    fams = {o.parent[fid] for fid in d.fids}
    ret = {p: False for p in fams}
    by_fam = collections.defaultdict(list)
    for site, ins in d.reach.items():
        by_fam[o.parent[ins["fid"]]].append((site, ins))
    changed = True
    while changed:
        changed = False
        for p in sorted(fams):
            if ret[p]:
                continue
            r = False
            for site, ins in by_fam[p]:
                if ins.get("iclass") in RETURNS:
                    r = True
                elif site in d.tailcalls:
                    k, x = d.tailcalls[site]
                    if k == "ext":
                        r = x not in NORETURN_EXTERNALS
                    else:
                        r = d.call_kind(x) == "interposable" or ret.get(o.parent[x], True)
                elif site in d.unresolved_jumps:
                    r = True
                elif site in d.resolution:
                    res = d.resolution[site]
                    if res["kind"] == "unresolved" and d.pending.get(site) == "jmp":
                        r = True
                    elif res["kind"] == "import_tail_call":
                        r = res["name"] not in NORETURN_EXTERNALS
                if r:
                    break
            if r:
                ret[p] = True
                changed = True
    return ret


if __name__ == "__main__":
    sys.exit(main())
