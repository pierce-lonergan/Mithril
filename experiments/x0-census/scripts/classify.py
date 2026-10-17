#!/usr/bin/env python3
"""classify.py -- X0 §4.3/§4.4: FP-sensitivity class of every XED iclass, fixed before any Hearth
object exists. Writes experiments/x0-census/class/fp_class.csv.

Usage:
  python -I classify.py [--xed-tables ../class/xed_tables.tsv] [--out ../class/fp_class.csv]
                        [--summary ../class/fp_class_summary.json] [--check]

Input: xed_tables.tsv, dumped from the pinned XED (v2026.08.23) by scripts/xed_tables.c. It is
XED's own iform -> (iclass, category, extension, isa_set) map plus, for every decoder-table entry,
the iform, the exception class, the attribute set and the operand list (name/visibility/action/
element xtype/width). The script refuses to run on any other file (SHA-256 pinned below).

Scope (record §4.4, widened before freeze): EVERY iclass XED defines, not only the extensions the
record lists, so that a census iclass is never "missing" merely because it is a GPR or control
instruction. The listed extensions are checked to exist; the per-row verdict rule is the same for
all rows.

Verdict for each iclass (record §4.4, "Definition" and "Disagreement and gaps"):
  fp_sensitive = SDM reading  OR  XED cross-check
  * SDM reading: the family rules below. Each rule carries the SDM (or ISA-extension spec)
    clause that makes the result depend on MXCSR.RC/DAZ/FTZ, embedded RC/SAE or IEEE special-value
    handling, or the clause that shows it cannot. A row with an FP-typed operand that no family
    rule covers is FP-sensitive by default (rule "fp_operand_default") and is listed in the
    summary for review.
  * XED cross-check: some iform of the iclass carries XED attribute MXCSR or MXCSR_RD, or one of
    USES_DAZ, USES_FTZ, FLUSH_INPUT_DENORM, FLUSH_OUTPUT_DENORM, FIXED_ROUNDING_RNE (added: they
    mark denormal/rounding behaviour), or an FP-arithmetic exception class: SSE_TYPE_2, SSE_TYPE_2D,
    SSE_TYPE_3, AVX_TYPE_2, AVX_TYPE_2D, AVX_TYPE_3 (XED splits the SDM's types 2/3 into legacy
    and VEX spellings), AVX512_E2, AVX512_E3, AVX512_E3NF (the scalar variants).
  Names are confirmed against the pinned XED at run time (summary "xed_names_confirmed").

op_class: the frozen function of record §4.4 (secondary metric only).

Standard library only; Python >= 3.8. Deterministic: same input -> byte-identical output.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
XED_TABLES_SHA256 = "1db25e7f5f02b5796d06cbb94f4cb5ab7d8230ed1091bacae485fa5c517d1d13"  # LF bytes
XED_VERSION = "v2026.08.23"

# --------------------------------------------------------------------------- XED cross-check
XED_FP_ATTRS = ("MXCSR", "MXCSR_RD", "USES_DAZ", "USES_FTZ", "FLUSH_INPUT_DENORM",
                "FLUSH_OUTPUT_DENORM", "FIXED_ROUNDING_RNE")
XED_FP_EXC = ("SSE_TYPE_2", "SSE_TYPE_2D", "SSE_TYPE_3", "AVX_TYPE_2", "AVX_TYPE_2D", "AVX_TYPE_3",
              "AVX512_E2", "AVX512_E3", "AVX512_E3NF")
# Extensions named by the record (§4.3 category S and §4.4 enumeration); checked to exist.
RECORD_EXTENSIONS = ("X87", "SSE", "SSE2", "SSE3", "SSSE3", "SSE4", "AVX", "AVX2", "AVX2GATHER",
                     "FMA", "F16C", "AVX512EVEX", "AVX512VEX", "BMI1", "BMI2")
# Extensions whose P-prefixed iclasses are vector integer operations (rule int_vector).
SIMD_EXTS = {"MMX", "SSE", "SSE2", "SSE3", "SSSE3", "SSE4", "SSE4A", "AVX", "AVX2", "AVX2GATHER", "AVX512EVEX",
             "AVX512VEX", "XOP", "AVX_VNNI", "AVX_VNNI_INT8", "AVX_VNNI_INT16", "AVX_IFMA", "PCLMULQDQ",
             "VPCLMULQDQ", "GFNI", "SHA", "SHA512", "SM3", "SM4", "AES", "AVXAES", "VAES", "3DNOW"}
FP_XTYPES = {"F16", "F32", "F64", "F80", "BF16", "2F16", "2BF16", "BF8", "HF8", "4BF8", "4HF8",
             "BF4", "BF6", "HF6", "B80"}

SDM_MXCSR = "SDM Vol. 1 §10.2.3 (MXCSR: RC, DAZ, FTZ)"


def doc(isa_sets, mnem):
    """Which document defines the instruction: the SDM Vol. 2 page, or for ISA sets newer than the
    SDM text the Intel ISA-extension specification named by XED's ISA set."""
    newer = sorted(s for s in isa_sets if s.startswith(("AVX10", "AVX512_FP8", "AVX512_SAT", "AVX512_MINMAX",
                                                          "AVX512_COM_EF", "AVX512_VNNI_FP16", "AMX_", "ACE",
                                                          "AVX512_MOVZXC")))
    if newer:
        return "Intel ISA-extension spec for %s, instruction %s" % (newer[0].rsplit("_", 1)[0], mnem)
    return "SDM Vol. 2 instruction page %s" % mnem


# --------------------------------------------------------------------------- family rules
# Each rule: (name, regex on iclass, verdict, reason template). First match wins. {doc} and
# {mxcsr} are filled in per row. Order matters: specific families before generic ones.
R = re.compile
YES, NO = "yes", "no"
RULES = [
    # ---- FP arithmetic, element-wise (record: FP-sensitive by name)
    ("fp_arith", R(r"^V?(ADD|SUB|MUL|DIV|SQRT)(PS|PD|SS|SD|PH|SH|BF16|NEPBF16)$"), YES,
     "{doc}, Operation: each result is rounded per MXCSR.RC (EVEX.b with register operands: embedded RC); "
     "SIMD FP exceptions O,U,I,P,D; DAZ/FTZ apply ({mxcsr})"),
    ("fp_minmax", R(r"^V?(MIN|MAX)(PS|PD|SS|SD|PH|SH|BF16|NEPBF16)$"), YES,
     "{doc}, Operation: if either source is NaN, or both are zeros of either sign, the second source is "
     "returned (NaN selection, signed-zero handling); DAZ applies; exceptions I,D ({mxcsr})"),
    ("fp_minmax_new", R(r"^VMINMAX(PS|PD|SS|SD|PH|SH|BF16)$"), YES,
     "{doc}: IEEE 754-2019 minimum/maximum selection with NaN and signed-zero rules chosen by imm8"),
    ("fp_horiz", R(r"^V?(ADDSUB|HADD|HSUB)(PS|PD)$"), YES,
     "{doc}, Operation: FP add/sub of element pairs, rounded per MXCSR.RC; exceptions O,U,I,P,D ({mxcsr})"),
    ("fp_dot", R(r"^V?DPP(S|D)$"), YES,
     "{doc}, Operation: products and sums rounded per MXCSR.RC (DP_Primitive); exceptions O,U,I,P,D ({mxcsr})"),
    ("fp_dot_lowp", R(r"^(VDPBF16PS|VDPPHPS|VDPBF8PS|VDPBHF8PS|VDPHBF8PS|VDPHF8PS)$"), YES,
     "{doc}: low-precision products accumulated into f32 with fixed RNE and denormal flushing "
     "(SDM VDPBF16PS: 'MXCSR is not consulted', input denormals treated as zero) -- result depends on "
     "rounding and denormal handling"),
    # ---- compares (record: FP-sensitive by name)
    ("fp_cmp", R(r"^(V?CMP(PS|PD|SS|PH|SH|BF16)|CMPSD_XMM|VCMPSD)$"), YES,
     "{doc}, Operation: predicate result is 'unordered' for NaN operands and DAZ applies, so the mask "
     "written (xmm or k) depends on NaN and denormal handling; exceptions I,D ({mxcsr})"),
    ("fp_comi", R(r"^V?U?COMIS[SDH]$|^VU?COMXS[SDH]$|^VCOMISBF16$"), YES,
     "{doc}, Operation: the EFLAGS result distinguishes an unordered comparison (a NaN operand; COMISS/UCOMISS "
     "set ZF,PF,CF = 111) and DAZ applies; exceptions I,D ({mxcsr})"),
    # ---- FMA class (record: every FMA-class iclass)
    ("fma", R(r"^VF(N)?M(ADD|SUB)(SUB|ADD)?(132|213|231)?(PS|PD|SS|SD|PH|SH|BF16|NEPBF16)$"), YES,
     "{doc}, Operation: a*b+c with a single rounding per MXCSR.RC (or embedded RC); exceptions O,U,I,P,D; "
     "DAZ/FTZ apply ({mxcsr})"),
    ("fma_4", R(r"^V4FN?MADD(PS|SS)$"), YES,
     "{doc}: four chained fused multiply-adds, each rounded; exceptions O,U,I,P,D ({mxcsr})"),
    ("fma_complex", R(r"^VFC?(MADD|MUL)C(PH|SH)$"), YES,
     "{doc}: complex FP16 multiply(-add); results rounded per MXCSR.RC or embedded RC ({mxcsr})"),
    # ---- approximations (record: RCP*, RSQRT*, VRCP14*, VRSQRT14*; ER forms; 3DNow!)
    ("approx", R(r"^V?(RCP|RSQRT)(PS|SS|PH|SH|BF16)$|^V(RCP|RSQRT)(14|28)(PS|PD|SS|SD)$|^VEXP2P[SD]$"), YES,
     "{doc}, Operation: approximate reciprocal / reciprocal square root; result for NaN, zero, infinity "
     "and denormal inputs follows special-case tables (denormal inputs treated as zero by the 14/28 forms "
     "or DAZ); implementation-specific bits"),
    # ---- special FP (record: VFPCLASS, VGETEXP, VGETMANT, VRNDSCALE, ROUND, VREDUCE, VRANGE,
    #      VFIXUPIMM, VSCALEF)
    ("fp_special", R(r"^V(FPCLASS|GETEXP|GETMANT|RNDSCALE|REDUCE|RANGE|FIXUPIMM|SCALEF)(PS|PD|SS|SD|PH|SH|BF16)$"
                     r"|^V?ROUND(PS|PD|SS|SD)$"), YES,
     "{doc}, Operation: result depends on special-value classification (QNaN/SNaN/zero/infinity/denormal) "
     "and/or rounding per imm8 or MXCSR.RC; DAZ applies (VFPCLASS/VGETEXP/VGETMANT: MXCSR.DAZ consulted)"),
    ("fp_frcz", R(r"^VFRCZ(PS|PD|SS|SD)$"), YES,
     "AMD XOP spec (APM Vol. 4) VFRCZ: fraction extraction x - trunc(x), rounded, with NaN and denormal "
     "handling per MXCSR"),
    # ---- conversions (record: every FP<->integer and FP<->FP conversion)
    ("cvt", R(r"^V?CVT|^VBCSTNE(BF16|SH)2PS$|^TCVTROW"), YES,
     "{doc}, Operation: conversion to or from a floating-point format: rounding per MXCSR.RC, imm8, "
     "embedded RC or truncation, integer-indefinite or saturated result for NaN/out-of-range inputs, "
     "NaN quieting, denormal handling ({mxcsr})"),
    # ---- AMX FP tile arithmetic
    ("amx_fp", R(r"^T(DPBF16PS|DPFP16PS|CMMIMFP16PS|CMMRLFP16PS|DPBF8PS|DPBHF8PS|DPHBF8PS|DPHF8PS|MMULTF32PS|TMMULTF32PS)$"
                 r"|^TOP[0-9A-Z]+PS$"), YES,
     "{doc}: tile dot or outer products of low-precision FP inputs accumulated in f32 with fixed rounding and "
     "denormal flushing"),
    # ---- 3DNow!
    ("amd_3dnow_fp", R(r"^(PF[A-Z0-9]+|PI2F[DW])$"), YES,
     "AMD 3DNow! Technology Manual, instruction %s: single-precision FP arithmetic/compare/conversion with "
     "AMD-specific rounding and special-value rules"),
    # ---- x87 (decided per iclass below; this rule only routes)
    ("x87", R(r"^F"), None, None),
    # ---- NOT FP-sensitive by name (record §4.4)
    ("fp_logic", R(r"^V?(AND|ANDN|OR|XOR)(PS|PD|PH)$|^VPTERNLOG[DQ]$"), NO,
     "{doc}: bitwise operation on the bit patterns; no SIMD FP exception; result independent of MXCSR "
     "and of FP special values"),
    ("move", R(r"^V?MOV|^V?MASKMOV|^VPMASKMOV|^V?LDDQU$|^KMOV"), NO,
     "{doc}: copies bits (load/store/register move, optionally masked or zero-extended); no FP exception; "
     "result independent of MXCSR and FP special values"),
    ("blend", R(r"^V?BLENDV?P[SD]$|^VBLENDM|^VPBLEND"), NO,
     "{doc}: selects source elements by mask bits or by the sign bit of a mask element (record: blends "
     "including BLENDVPS are not FP-sensitive); no FP exception"),
    ("shuffle", R(r"^V?SHUF(PS|PD)$|^VSHUF[FI](32X4|64X2)$|^V?UNPCK[HL]P[SD]$|^VPERM|^V?INSERT(PS|F|I)|"
                  r"^V?EXTRACT(PS|F|I)|^VBROADCAST|^VPBROADCAST|^VEXPAND|^VCOMPRESS|^VPEXPAND|^VPCOMPRESS|"
                  r"^VGATHER|^VSCATTER|^VPGATHER|^VPSCATTER|^VPERMIL2P[SD]$"), NO,
     "{doc}: moves, permutes, broadcasts, gathers or scatters whole elements without FP arithmetic; "
     "no FP exception"),
    ("test_sign", R(r"^V?TESTP[SD]$"), NO,
     "{doc}: sets ZF/CF from the AND of sign bits only; no FP exception"),
    ("kmask", R(r"^K(AND|ANDN|OR|XOR|XNOR|NOT|SHIFTL|SHIFTR|TEST|ORTEST|ADD|UNPCK)[BWDQ]{1,2}$"), NO,
     "{doc}: reads and writes only opmask (k) registers or EFLAGS"),
    ("mxcsr_env", R(r"^V?(LDMXCSR|STMXCSR)$"), NO,
     "{doc}: loads or stores MXCSR itself; the value moved does not depend on the rounding mode or on FP "
     "special values (FP-environment instruction, listed descriptively in record §5)"),
    ("state", R(r"^(FX|X)(SAVE|RSTOR)"), NO,
     "{doc}: saves or restores processor state as bits"),
    ("zero", R(r"^VZERO(UPPER|ALL)$|^EMMS$|^FEMMS$"), NO,
     "{doc}: clears register state; no FP arithmetic"),
    ("int_vector", R(r"^V?P[A-Z0-9_]+$"), NO,
     "{doc}: integer (or bitwise) vector operation, including saturating forms; operands are integer-typed "
     "in XED; no FP exception; result independent of MXCSR"),
]

# x87: per-iclass verdicts (record: x87 arithmetic is FP-sensitive by name).
X87_YES = {
    "F2XM1", "FADD", "FADDP", "FIADD", "FSUB", "FSUBP", "FSUBR", "FSUBRP", "FISUB", "FISUBR", "FMUL",
    "FMULP", "FIMUL", "FDIV", "FDIVP", "FDIVR", "FDIVRP", "FIDIV", "FIDIVR", "FSQRT", "FSCALE", "FPREM",
    "FPREM1", "FRNDINT", "FXTRACT", "FCOS", "FSIN", "FSINCOS", "FPTAN", "FPATAN", "FYL2X", "FYL2XP1",
    "FCOM", "FCOMP", "FCOMPP", "FCOMI", "FCOMIP", "FUCOM", "FUCOMP", "FUCOMPP", "FUCOMI", "FUCOMIP",
    "FICOM", "FICOMP", "FTST", "FXAM", "FLD", "FST", "FSTP", "FSTPNCE", "FIST", "FISTP", "FISTTP",
    "FBSTP", "FILD", "FBLD", "FLDPI", "FLDL2E", "FLDL2T", "FLDLG2", "FLDLN2",
}
X87_REASON_YES = {
    "FLD": "{doc}: FLD m32fp/m64fp converts to double extended; SNaN sources are quieted and denormal "
           "sources raise #D (special-value handling)",
    "FST": "{doc}: FST m32fp/m64fp rounds the double-extended value per FPU control word RC; overflow/"
           "underflow/NaN handling",
    "FSTP": "{doc}: FSTP m32fp/m64fp rounds per FPU control word RC; overflow/underflow/NaN handling",
    "FSTPNCE": "{doc}: as FSTP (rounding per FPU control word RC)",
    "FILD": "{doc}: integer-to-FP conversion (record: every integer-to-FP conversion is FP-sensitive)",
    "FBLD": "{doc}: BCD-to-FP conversion (record: every integer-to-FP conversion is FP-sensitive)",
    "FIST": "{doc}: FP-to-integer conversion rounded per FPU control word RC; integer indefinite on NaN/"
            "overflow",
    "FISTP": "{doc}: FP-to-integer conversion rounded per FPU control word RC; integer indefinite on NaN/"
             "overflow",
    "FISTTP": "{doc}: FP-to-integer conversion with truncation; integer indefinite on NaN/overflow",
    "FBSTP": "{doc}: FP-to-BCD conversion rounded per FPU control word RC; BCD indefinite on NaN",
    "FXAM": "{doc}: classifies ST(0) as NaN/normal/infinity/zero/empty/denormal into C3,C2,C0 "
            "(special-value classification, as VFPCLASS)",
    "FTST": "{doc}: compares ST(0) with 0.0; unordered for NaN",
}
X87_NO_REASON = {
    "FABS": "{doc}: clears the sign bit; no rounding and no NaN processing ('Operation: ST(0) := |ST(0)|', "
            "C1 only)",
    "FCHS": "{doc}: complements the sign bit; no rounding and no NaN processing",
    "FLD1": "{doc}: pushes the exact constant +1.0",
    "FLDZ": "{doc}: pushes the exact constant +0.0",
    "FXCH": "{doc}: exchanges register contents",
    "FFREE": "{doc}: tags a register empty", "FFREEP": "{doc}: tags a register empty and pops",
    "FDECSTP": "{doc}: decrements TOP", "FINCSTP": "{doc}: increments TOP", "FNOP": "{doc}: no operation",
    "FWAIT": "{doc}: waits for pending x87 exceptions",
}
X87_ENV = {"FLDCW", "FNSTCW", "FLDENV", "FNSTENV", "FNSAVE", "FRSTOR", "FNINIT", "FNCLEX", "FNSTSW",
           "FDISI8087_NOP", "FENI8087_NOP", "FSETPM287_NOP"}
X87_CMOV = re.compile(r"^FCMOV")

# Record §4.4 lists, used as self-checks.
BY_NAME_YES = [r"^V?(ADD|SUB|MUL|DIV|SQRT|MIN|MAX)(PS|PD|SS|SD)$", r"^V?U?COMIS[SD]$", r"^V?CMP(PS|SS|PD)$",
               r"^CMPSD_XMM$", r"^VCMPSD$", r"^VFPCLASS(PS|SS)$", r"^VGETEXP", r"^VGETMANT", r"^VRNDSCALE",
               r"^V?ROUND", r"^VREDUCE", r"^VRANGE", r"^VFIXUPIMM", r"^VSCALEF", r"^VF(N)?M(ADD|SUB)",
               r"^V?RCP(PS|SS)$", r"^V?RSQRT(PS|SS)$", r"^VRCP14", r"^VRSQRT14", r"^V?CVT",
               r"^VCVTNEPS2BF16$", r"^VDPBF16PS$", r"^(FADD|FSUB|FMUL|FDIV|FSQRT)"]
BY_NAME_NO = [r"^V?(AND|ANDN|OR|XOR)(PS|PD)$", r"^VPTERNLOG", r"^V?MOV(APS|UPS|SS|HLPS|LHPS)$",
              r"^V?BLENDV?PS$", r"^V?SHUFPS$", r"^VPERM(PS|D|Q|PD|ILPS)$", r"^VBROADCASTSS$",
              r"^V?INSERTPS$", r"^V?EXTRACTPS$", r"^K(MOV|AND|OR|ORTEST)[BWDQ]$", r"^VPMADDUBSW$",
              r"^VPMADDWD$", r"^VPDPBUSD$", r"^VPACKSS(DW|WB)$", r"^VPMOVS(DB|DW|QB|QD|QW|WB)$"]


def op_class(ic):
    """Record §4.4 frozen function."""
    b = ic[1:] if ic.startswith("V") else ic
    if ic == "CMPSD_XMM":
        b = "CMPSD"
    m = re.match(r"^(ADD|SUB|MUL|DIV|SQRT|MIN|MAX|CMP)(PS|SS|PD|SD)$", b)
    if m and not (ic == "CMPSD"):          # CMPSD (no _XMM) is the string compare
        return "%s.%s" % (m.group(1), "f32" if m.group(2) in ("PS", "SS") else "f64")
    m = re.match(r"^(U?)COMIS(S|D)$", b)
    if m:
        return "%sCOMI.%s" % (m.group(1), "f32" if m.group(2) == "S" else "f64")
    m = re.match(r"^F(N?)M(ADD|SUB)(SUB|ADD)?(?:132|213|231)?(PS|SS|PD|SD)$", b)
    if m:
        return "F%sM%s%s.%s" % (m.group(1), m.group(2), m.group(3) or "", "f32" if m.group(4) in ("PS", "SS") else "f64")
    return b


def load_tables(path):
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != XED_TABLES_SHA256:
        raise SystemExit("xed_tables.tsv SHA-256 %s != pinned %s" % (sha, XED_TABLES_SHA256))
    ic = collections.OrderedDict()
    f2c, exts_all, excs_all, attrs_all, version = {}, set(), set(), set(), None

    def get(k):
        if k not in ic:
            ic[k] = {"ext": set(), "isa": set(), "cat": set(), "attr": set(), "exc": set(), "xt": set(),
                     "iforms": set(), "fp_attr": set(), "fp_exc": set()}
        return ic[k]
    for line in raw.decode("ascii").split("\n"):
        if not line:
            continue
        p = line.split("\t")
        if p[0] == "VERSION":
            version = p[1]
        elif p[0] == "IFORM":
            f2c[p[1]] = p[2]
            d = get(p[2])
            d["iforms"].add(p[1]); d["cat"].add(p[3]); d["ext"].add(p[4]); d["isa"].add(p[5])
            exts_all.add(p[4])
        elif p[0] == "ICLASS":
            get(p[1])
        elif p[0] == "INST":
            d = get(f2c[p[2]])
            d["exc"].add(p[3])
            at = set(p[4][len("ATTR:"):].split())
            d["attr"] |= at
            d["fp_attr"] |= at & set(XED_FP_ATTRS)
            if p[3] in XED_FP_EXC:
                d["fp_exc"].add(p[3])
            for o in p[5][len("OPS:"):].split():
                d["xt"].add(o.split("/")[3])
        elif p[0] == "EXCEPTION":
            excs_all.add(p[1])
        elif p[0] == "ATTRIBUTE":
            attrs_all.add(p[1])
    if version != XED_VERSION:
        raise SystemExit("XED version %r != %r" % (version, XED_VERSION))
    return sha, ic, exts_all, excs_all, attrs_all


def mnemonic_for_doc(ic):
    if ic == "CMPSD_XMM":
        return "CMPSD"
    if ic == "MOVSD_XMM":
        return "MOVSD"
    return ic


def classify(ic, d):
    """Return (sdm_verdict, rule, reason)."""
    dc = doc(d["isa"], mnemonic_for_doc(ic))
    fill = {"doc": dc, "mxcsr": SDM_MXCSR}
    if "X87" in d["ext"] or ic in ("FISTTP",):
        if ic in X87_YES:
            r = X87_REASON_YES.get(ic, "{doc}: x87 arithmetic, comparison or transcendental; result rounded per "
                                       "FPU control word RC/PC with NaN, infinity and denormal handling")
            return YES, "x87", r.format(**fill)
        if ic in X87_ENV:
            return NO, "x87_env", ("{doc}: reads or writes the x87 control/status/environment as bits "
                                   "(FP-environment instruction, listed descriptively in record §5)").format(**fill)
        if X87_CMOV.match(ic):
            return NO, "x87", "{doc}: conditional register copy on EFLAGS; no FP arithmetic".format(**fill)
        if ic in X87_NO_REASON:
            return NO, "x87", X87_NO_REASON[ic].format(**fill)
    for name, rx, verdict, reason in RULES:
        if name == "x87":
            continue
        if rx.search(ic):
            if name == "int_vector" and not (d["ext"] & SIMD_EXTS):
                continue
            if name == "amd_3dnow_fp":
                return YES, name, reason % ic
            return verdict, name, reason.format(**fill)
    if d["xt"] & FP_XTYPES:
        return YES, "fp_operand_default", (
            "{doc}: has floating-point-typed operands (XED xtypes %s) and no family rule shows the result "
            "is independent of FP state; FP-sensitive by default (record §4.4 gaps rule)" %
            ",".join(sorted(d["xt"] & FP_XTYPES))).format(**fill)
    return NO, "non_fp", ("{doc}: no floating-point-typed operand (XED xtypes %s), no MXCSR/x87 dependency" %
                          (",".join(sorted(d["xt"] - {"INVALID"})) or "none")).format(**fill)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xed-tables", default=os.path.join(HERE, "..", "class", "xed_tables.tsv"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "class", "fp_class.csv"))
    ap.add_argument("--summary", default=os.path.join(HERE, "..", "class", "fp_class_summary.json"))
    ap.add_argument("--check", action="store_true", help="do not write; exit 1 if the outputs would differ")
    a = ap.parse_args()
    sha, ic, exts_all, excs_all, attrs_all = load_tables(a.xed_tables)

    rows, stats, disagree, default_rows = [], collections.Counter(), [], []
    for name in sorted(ic):
        d = ic[name]
        sdm, rule, reason = classify(name, d)
        xed = bool(d["fp_attr"] or d["fp_exc"])
        final = YES if (sdm == YES or xed) else NO
        ev = []
        if d["fp_attr"]:
            ev.append("attr " + "+".join(sorted(d["fp_attr"])))
        if d["fp_exc"]:
            ev.append("exc " + "+".join(sorted(d["fp_exc"])))
        if xed and sdm == NO:
            reason += " || XED cross-check FP (%s): the disagreement resolves to FP-sensitive (record §4.4)" % "; ".join(ev)
            disagree.append({"iclass": name, "rule": rule, "xed": ev})
        elif xed:
            reason += " [XED: %s]" % "; ".join(ev)
        if rule == "fp_operand_default":
            default_rows.append(name)
        stats[(rule, final)] += 1
        rows.append([name, "|".join(sorted(d["ext"])), final, reason, op_class(name)])

    # self-checks against the record's by-name lists
    problems = []
    for rx in BY_NAME_YES:
        hit = [r for r in rows if re.search(rx, r[0])]
        if not hit:
            problems.append("by-name YES pattern %s matches no iclass" % rx)
        for r in hit:
            if r[2] != YES:
                problems.append("by-name YES %s classified %s" % (r[0], r[2]))
    for rx in BY_NAME_NO:
        hit = [r for r in rows if re.search(rx, r[0])]
        if not hit:
            problems.append("by-name NO pattern %s matches no iclass" % rx)
        for r in hit:
            if r[2] != NO:
                problems.append("by-name NO %s classified %s (XED cross-check?)" % (r[0], r[2]))
    missing_ext = [e for e in RECORD_EXTENSIONS if e not in exts_all]
    names_confirmed = {
        "attributes": {x: (x in attrs_all) for x in XED_FP_ATTRS},
        "exceptions": {x: (x in excs_all) for x in XED_FP_EXC},
        "record_extensions_missing": missing_ext,
        "mxcsr_rd_iclasses": sorted(k for k, d in ic.items() if "MXCSR_RD" in d["attr"]),
    }
    if missing_ext or not all(names_confirmed["attributes"].values()) or not all(names_confirmed["exceptions"].values()):
        problems.append("XED names not confirmed: %s" % json.dumps(names_confirmed))

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["iclass", "extension", "fp_sensitive", "reason", "op_class"])
    w.writerows(rows)
    out = buf.getvalue().encode("utf-8")
    summary = {
        "xed_tables_sha256": sha, "xed_version": XED_VERSION, "n_iclasses": len(rows),
        "n_fp_sensitive": sum(1 for r in rows if r[2] == YES),
        "by_rule": {"%s:%s" % k: v for k, v in sorted(stats.items())},
        "sdm_no_but_xed_fp": disagree, "fp_operand_default": default_rows,
        "xed_names_confirmed": names_confirmed, "self_check_problems": problems,
        "fp_class_csv_sha256": hashlib.sha256(out).hexdigest(),
    }
    sj = (json.dumps(summary, indent=1, sort_keys=True) + "\n").encode("utf-8")
    if a.check:
        same = os.path.exists(a.out) and open(a.out, "rb").read() == out
        print("fp_class.csv %s (sha256 %s); problems: %d" % ("unchanged" if same else "WOULD CHANGE",
                                                             summary["fp_class_csv_sha256"], len(problems)))
        return 0 if same and not problems else 1
    with open(a.out, "wb") as f:
        f.write(out)
    with open(a.summary, "wb") as f:
        f.write(sj)
    print("%d iclasses, %d FP-sensitive, %d SDM-no/XED-yes, %d by default rule, %d self-check problems; sha256 %s" % (
        len(rows), summary["n_fp_sensitive"], len(disagree), len(default_rows), len(problems),
        summary["fp_class_csv_sha256"]))
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
