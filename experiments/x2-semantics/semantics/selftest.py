"""Self-tests. Run from experiments/x2-semantics:   python -B -m semantics.selftest

Sections A-F use HAND-DERIVED expected bit patterns: each expectation was worked out from the SDM
pseudocode / IEEE 754 rules written in the comment beside it, not by running this code. Sections
G-I are DERIVED checks: compositions of table semantics against Hearth's stated lane maps and
scalar definitions, T2 bound re-derivations, mutant witnesses and registry integrity.
Run with --full to scan the commute-before-MAXPS witness rule over every (ISA, chain, NaN position)
case (1,536 cases, about 10 s); the default run checks a subset (3 chains per ISA).
Exit status = number of failures.
"""
import copy
import random
import sys

from . import bounds, fp_ops, hearth_kernels as hk, int_ops, table, vec
from .bits import s32
from .fpenv import DE, IE, OE, PE, RC_RD, RC_RNE, RC_RU, RC_RZ, UE, ZE, Env, UnmodeledEnvironment, flags_str
from .vec import lanes, pack

FAIL = []
COUNT = {"n": 0}
SECTION = {"name": ""}


def section(name):
    SECTION["name"] = name
    print("[%s]" % name)


def check(label, got, want):
    COUNT["n"] += 1
    if got != want:
        FAIL.append("%s / %s: got %r want %r" % (SECTION["name"], label, got, want))


def r(fn, *args):
    """Format (bits, flags) results for comparison."""
    b, f = fn(*args)
    return ("0x%08X" % b, flags_str(f))


D = Env.make()
RNE, RD, RU, RZ = (Env.make(rc=m) for m in (RC_RNE, RC_RD, RC_RU, RC_RZ))
FTZ = Env.make(ftz=True)
DAZ = Env.make(daz=True)
P, NONE = "PE", "-"

ONE, TWO, HALF = 0x3F800000, 0x40000000, 0x3F000000
PINF, NINF, FMAX = 0x7F800000, 0xFF800000, 0x7F7FFFFF
MINN, DEN1 = 0x00800000, 0x00000001


def sec_a_arith():
    section("A arithmetic, rounding, signed zero, NaN, FTZ/DAZ")
    # A1-A4: ties and directed rounding. 2^-24 = 0x33800000. 1 + 2^-24 is a tie between 1.0
    # (mantissa 0, even) and 1 + 2^-23 (mantissa 1, odd).
    check("A1 1+2^-24 RNE", r(fp_ops.add, ONE, 0x33800000, RNE), ("0x3F800000", P))
    check("A2 (1+2^-23)+2^-24 RNE -> even 1+2^-22", r(fp_ops.add, 0x3F800001, 0x33800000, RNE), ("0x3F800002", P))
    check("A3 1+2^-24 RU", r(fp_ops.add, ONE, 0x33800000, RU), ("0x3F800001", P))
    check("A3 1+2^-24 RD", r(fp_ops.add, ONE, 0x33800000, RD), ("0x3F800000", P))
    check("A3 1+2^-24 RZ", r(fp_ops.add, ONE, 0x33800000, RZ), ("0x3F800000", P))
    check("A4 -1-2^-24 RD", r(fp_ops.add, 0xBF800000, 0xB3800000, RD), ("0xBF800001", P))
    check("A4 -1-2^-24 RU", r(fp_ops.add, 0xBF800000, 0xB3800000, RU), ("0xBF800000", P))
    # A5: IEEE 754 §6.3 exact-zero sums.
    check("A5 +0 + -0 RNE", r(fp_ops.add, 0, 0x80000000, RNE), ("0x00000000", NONE))
    check("A5 +0 + -0 RD", r(fp_ops.add, 0, 0x80000000, RD), ("0x80000000", NONE))
    check("A5 -0 + -0", r(fp_ops.add, 0x80000000, 0x80000000, RNE), ("0x80000000", NONE))
    check("A5 1 + -1 RNE", r(fp_ops.add, ONE, 0xBF800000, RNE), ("0x00000000", NONE))
    check("A5 1 + -1 RD", r(fp_ops.add, ONE, 0xBF800000, RD), ("0x80000000", NONE))
    check("A5 x + (-0) keeps -0 (rule R-SZ)", r(fp_ops.add, 0x80000000, 0x80000000, RNE), ("0x80000000", NONE))
    check("A5 -0 + (+0) is NOT -0 (why x+0.0 is never a rule)", r(fp_ops.add, 0x80000000, 0, RNE), ("0x00000000", NONE))
    # A6: NaN selection, SDM Vol 1 Table 4-7 (SSE column): first source wins, quieted.
    check("A6 QNaN,QNaN -> src1", r(fp_ops.add, 0x7FC01234, 0xFFC05678, D), ("0x7FC01234", NONE))
    check("A6 1.0,SNaN -> quiet(src2)", r(fp_ops.add, ONE, 0x7F800001, D), ("0x7FC00001", "IE"))
    check("A6 SNaN,QNaN -> quiet(src1)", r(fp_ops.add, 0xFF812345, 0x7FC00099, D), ("0xFFC12345", "IE"))
    check("A6 SNaN,SNaN -> quiet(src1)", r(fp_ops.add, 0x7F800002, 0x7F800003, D), ("0x7FC00002", "IE"))
    check("A6 QNaN,SNaN -> quiet... src1 (QNaN), IE", r(fp_ops.mul, 0x7FC00010, 0x7F800020, D), ("0x7FC00010", "IE"))
    check("A6 commuted add changes the NaN bits", fp_ops.add(0x7FC00001, 0x7FC00002, D)[0] != fp_ops.add(0x7FC00002, 0x7FC00001, D)[0], True)
    # A7: invalid operations -> QNaN indefinite 0xFFC00000.
    check("A7 +inf + -inf", r(fp_ops.add, PINF, NINF, D), ("0xFFC00000", "IE"))
    check("A7 0 * inf", r(fp_ops.mul, 0, PINF, D), ("0xFFC00000", "IE"))
    check("A7 -0 * +inf (indefinite sign is 1)", r(fp_ops.mul, 0x80000000, PINF, D), ("0xFFC00000", "IE"))
    check("A7 inf - inf", r(fp_ops.sub, PINF, PINF, D), ("0xFFC00000", "IE"))
    check("A7 sub keeps src2 NaN sign", r(fp_ops.sub, ONE, 0x7F800005, D), ("0x7FC00005", "IE"))
    # A8: overflow by rounding mode; MAX * 2.
    check("A8 MAX*2 RNE", r(fp_ops.mul, FMAX, TWO, RNE), ("0x7F800000", "OE|PE"))
    check("A8 MAX*2 RZ", r(fp_ops.mul, FMAX, TWO, RZ), ("0x7F7FFFFF", "OE|PE"))
    check("A8 MAX*2 RD", r(fp_ops.mul, FMAX, TWO, RD), ("0x7F7FFFFF", "OE|PE"))
    check("A8 MAX*2 RU", r(fp_ops.mul, FMAX, TWO, RU), ("0x7F800000", "OE|PE"))
    check("A8 MAX*-2 RD", r(fp_ops.mul, FMAX, 0xC0000000, RD), ("0xFF800000", "OE|PE"))
    check("A8 MAX*-2 RU", r(fp_ops.mul, FMAX, 0xC0000000, RU), ("0xFF7FFFFF", "OE|PE"))
    # A9-A11: gradual underflow. 2^-126 * 0.5 = 2^-127 exactly representable -> no flags.
    check("A9 2^-126*0.5 exact subnormal", r(fp_ops.mul, MINN, HALF, D), ("0x00400000", NONE))
    check("A10 2^-126*2^-23 = 2^-149", r(fp_ops.mul, MINN, 0x34000000, D), ("0x00000001", NONE))
    # 2^-149 is itself a denormal SOURCE, so DE is raised too (first hand derivation omitted DE;
    # corrected 2026-10-16 after the first run -- the expectation, not the code, was wrong).
    check("A11 2^-149*0.5 tie -> +0 (even)", r(fp_ops.mul, DEN1, HALF, RNE), ("0x00000000", "DE|UE|PE"))
    check("A11 2^-149*0.5 RU", r(fp_ops.mul, DEN1, HALF, RU), ("0x00000001", "DE|UE|PE"))
    check("A14 2^-149*0.5 RD", r(fp_ops.mul, DEN1, HALF, RD), ("0x00000000", "DE|UE|PE"))
    check("A14 -2^-149*0.5 RD", r(fp_ops.mul, 0x80000001, HALF, RD), ("0x80000001", "DE|UE|PE"))
    check("A14 2^-149*0.5 RD with DAZ: source flushed, exact +0", r(fp_ops.mul, DEN1, HALF, Env.make(rc=RC_RD, daz=True)),
          ("0x00000000", NONE))
    # A12: FTZ flushes tiny results to a signed zero with UE|PE (exact or not: UNCERTAIN F-FTZ-EXACT).
    check("A12 FTZ 2^-126*0.5", r(fp_ops.mul, MINN, HALF, FTZ), ("0x00000000", "UE|PE"))
    check("A12 FTZ -2^-126*0.5", r(fp_ops.mul, 0x80800000, HALF, FTZ), ("0x80000000", "UE|PE"))
    # A13: tininess AFTER rounding (class F-TINY). (2^-126 (1+2^-23)) * (1-2^-23) = 2^-126 (1-2^-46):
    # below 2^-126, but rounds (24 bits, unbounded exponent) to 2^-126 -> NOT tiny -> no UE, no flush.
    # A before-rounding implementation would give UE|PE (FTZ=0) and +0 with UE|PE (FTZ=1).
    check("A13 band, FTZ=0", r(fp_ops.mul, 0x00800001, 0x3F7FFFFE, D), ("0x00800000", P))
    check("A13 band, FTZ=1", r(fp_ops.mul, 0x00800001, 0x3F7FFFFE, FTZ), ("0x00800000", P))
    # (2^-126) * (1-2^-24) = (2^24-1) 2^-150: exact with 24 bits, tiny; subnormal grid tie -> 2^-126.
    check("A13b tiny, rounds up to MIN_NORMAL", r(fp_ops.mul, MINN, 0x3F7FFFFF, D), ("0x00800000", "UE|PE"))
    check("A13b same with FTZ", r(fp_ops.mul, MINN, 0x3F7FFFFF, FTZ), ("0x00000000", "UE|PE"))
    # A15: DAZ. Denormal operand: DE without DAZ; with DAZ treated as signed zero and no DE.
    check("A15 den+0 DAZ=0", r(fp_ops.add, DEN1, 0, D), ("0x00000001", "DE"))
    check("A15 den+0 DAZ=1", r(fp_ops.add, DEN1, 0, DAZ), ("0x00000000", NONE))
    check("A15 -den + +0 DAZ=1 -> +0", r(fp_ops.add, 0x80000001, 0, DAZ), ("0x00000000", NONE))
    check("A15 1.0 + den DAZ=0 (inexact)", r(fp_ops.add, ONE, DEN1, D), ("0x3F800000", "DE|PE"))
    check("A15 QNaN + den: NaN suppresses DE", r(fp_ops.add, 0x7FC00000, DEN1, D), ("0x7FC00000", NONE))
    # A16: division.
    check("A16 1/0", r(fp_ops.div, ONE, 0, D), ("0x7F800000", "ZE"))
    check("A16 -1/+0", r(fp_ops.div, 0xBF800000, 0, D), ("0xFF800000", "ZE"))
    check("A16 0/0", r(fp_ops.div, 0, 0, D), ("0xFFC00000", "IE"))
    check("A16 inf/inf", r(fp_ops.div, PINF, NINF, D), ("0xFFC00000", "IE"))
    check("A16 1/3", r(fp_ops.div, ONE, 0x40400000, D), ("0x3EAAAAAB", P))
    check("A16 127/127", r(fp_ops.div, 0x42FE0000, 0x42FE0000, D), ("0x3F800000", NONE))
    check("A16 1/den DAZ -> ZE", r(fp_ops.div, ONE, DEN1, DAZ), ("0x7F800000", "ZE"))
    # 1/(2^-149) = 2^149 overflows -> +inf (act_q8 scale for a tiny block, MUTANTS.md M-CLAMP).
    check("A16 1/2^-149 overflow", r(fp_ops.div, ONE, DEN1, D), ("0x7F800000", "DE|OE|PE"))


def sec_b_minmax():
    section("B MAX/MIN operand order")
    check("B1 max(+0,-0) -> src2", r(fp_ops.max_, 0, 0x80000000, D), ("0x80000000", NONE))
    check("B1 max(-0,+0) -> src2", r(fp_ops.max_, 0x80000000, 0, D), ("0x00000000", NONE))
    check("B1 min(+0,-0) -> src2", r(fp_ops.min_, 0, 0x80000000, D), ("0x80000000", NONE))
    check("B2 max(QNaN,1) -> 1", r(fp_ops.max_, 0x7FC00001, ONE, D), ("0x3F800000", "IE"))
    check("B2 max(1,QNaN) -> QNaN", r(fp_ops.max_, ONE, 0x7FC00001, D), ("0x7FC00001", "IE"))
    check("B2 max(1,SNaN) -> SNaN NOT quieted", r(fp_ops.max_, ONE, 0x7F800001, D), ("0x7F800001", "IE"))
    check("B2 min(SNaN,SNaN2) -> SNaN2", r(fp_ops.min_, 0x7F800001, 0xFF800002, D), ("0xFF800002", "IE"))
    check("B3 max(2,1)", r(fp_ops.max_, TWO, ONE, D), ("0x40000000", NONE))
    check("B3 max(1,2)", r(fp_ops.max_, ONE, TWO, D), ("0x40000000", NONE))
    check("B3 max(-inf,1)", r(fp_ops.max_, NINF, ONE, D), ("0x3F800000", NONE))
    check("B3 min(+inf,1)", r(fp_ops.min_, PINF, ONE, D), ("0x3F800000", NONE))
    check("B3 equal nonzero -> src2 bits (same value)", r(fp_ops.max_, ONE, ONE, D), ("0x3F800000", NONE))
    check("B4 max(den,0) DAZ=0", r(fp_ops.max_, DEN1, 0, D), ("0x00000001", "DE"))
    check("B4 max(den,0) DAZ=1 -> flushed src2", r(fp_ops.max_, DEN1, 0, DAZ), ("0x00000000", NONE))
    check("B4 max(0,-den) DAZ=1 -> -0 (UNCERTAIN F-DAZ-SEL)", r(fp_ops.max_, 0, 0x80000001, DAZ), ("0x80000000", NONE))
    # Hearth act_q8: m = max(abs(v), m) skips a NaN in v; the commuted form propagates it.
    check("B5 max(abs NaN, m) -> m", r(fp_ops.max_, 0x7FC00000, TWO, D), ("0x40000000", "IE"))
    check("B5 max(m, abs NaN) -> NaN", r(fp_ops.max_, TWO, 0x7FC00000, D), ("0x7FC00000", "IE"))
    # B6: coexisting-flag READINGS (class F-FLAGPRI; added 2026-10-16, review R1-11). Derived from the
    # model's rules (TABLE-SCHEMA §4 rules 6-7): DAZ flushes before any check; only a NaN source
    # suppresses DE; every other detected condition is recorded. Silicon decides each of these.
    check("B6 den / +0: DE and ZE both recorded", r(fp_ops.div, DEN1, 0, D), ("0x7F800000", "DE|ZE"))
    check("B6 +inf * den under DAZ: 0*inf invalid after flushing", r(fp_ops.mul, PINF, DEN1, DAZ), ("0xFFC00000", "IE"))
    check("B6 den / den under DAZ: 0/0 invalid after flushing", r(fp_ops.div, DEN1, DEN1, DAZ), ("0xFFC00000", "IE"))
    check("B6 den + inf: DE recorded although the result is inf", r(fp_ops.add, DEN1, PINF, D), ("0x7F800000", "DE"))
    # SEL-MAX (RULES.md R01): C `a > b ? a : b` equals MAXPS(a, b) bit for bit, NaN and +-0 included.
    for a_, b_ in ((0, 0x80000000), (0x80000000, 0), (0x7FC00001, ONE), (ONE, 0x7F800001), (TWO, ONE), (ONE, TWO),
                   (0x7FC00001, 0xFF800002)):
        sel = a_ if fp_ops.relation(a_, b_, D, True)[0] == fp_ops.GT else b_
        check("B7 SEL-MAX (%08X,%08X)" % (a_, b_), sel, fp_ops.max_(a_, b_, D)[0])


def sec_c_cmp():
    section("C comparisons")
    P_ = fp_ops.CMP_BY_NAME
    cp = lambda a, b, n, e=D: (fp_ops.cmp_pred(a, b, P_[n], e)[0], flags_str(fp_ops.cmp_pred(a, b, P_[n], e)[1]))
    check("C1 1<2 LT_OS", cp(ONE, TWO, "LT_OS"), (True, NONE))
    check("C1 QNaN<1 LT_OS signals", cp(0x7FC00000, ONE, "LT_OS"), (False, "IE"))
    check("C1 QNaN<1 LT_OQ quiet", cp(0x7FC00000, ONE, "LT_OQ"), (False, NONE))
    check("C1 SNaN==1 EQ_OQ", cp(0x7F800001, ONE, "EQ_OQ"), (False, "IE"))
    check("C1 QNaN UNORD_Q", cp(0x7FC00000, 0x7FC00000, "UNORD_Q"), (True, NONE))
    check("C1 SNaN UNORD_Q signals", cp(0x7F800001, 0x7F800001, "UNORD_Q"), (True, "IE"))
    check("C1 1 ORD_Q", cp(ONE, ONE, "ORD_Q"), (True, NONE))
    check("C1 +0 == -0", cp(0, 0x80000000, "EQ_OQ"), (True, NONE))
    check("C1 QNaN NEQ_UQ", cp(0x7FC00000, ONE, "NEQ_UQ"), (True, NONE))
    check("C1 den==0 DAZ", cp(DEN1, 0, "EQ_OQ", DAZ), (True, NONE))
    check("C1 den==0 no DAZ", cp(DEN1, 0, "EQ_OQ"), (False, "DE"))
    check("C1 predicate count", len(fp_ops.CMP_PREDICATES), 32)
    check("C1 imm 3 and 7", (fp_ops.CMP_PREDICATES[3][0], fp_ops.CMP_PREDICATES[7][0]), ("UNORD_Q", "ORD_Q"))
    # C5: all 32 predicates, hand-derived from SDM Vol 2 CMPPS Table 3-1 (imm order and names) and the
    # naming rules: O = false when unordered, U = true when unordered; Q = IE only for an SNaN,
    # S = IE for any NaN. Columns: 1<2, 1==1, 2>1, (QNaN,1) result+IE, (SNaN,1) result+IE.
    # Written by hand on 2026-10-16 (review R1-10), not generated from fp_ops.CMP_PREDICATES.
    hand = """\
00 EQ_OQ    F T F  F -   F IE
01 LT_OS    T F F  F IE  F IE
02 LE_OS    T T F  F IE  F IE
03 UNORD_Q  F F F  T -   T IE
04 NEQ_UQ   T F T  T -   T IE
05 NLT_US   F T T  T IE  T IE
06 NLE_US   F F T  T IE  T IE
07 ORD_Q    T T T  F -   F IE
08 EQ_UQ    F T F  T -   T IE
09 NGE_US   T F F  T IE  T IE
0A NGT_US   T T F  T IE  T IE
0B FALSE_OQ F F F  F -   F IE
0C NEQ_OQ   T F T  F -   F IE
0D GE_OS    F T T  F IE  F IE
0E GT_OS    F F T  F IE  F IE
0F TRUE_UQ  T T T  T -   T IE
10 EQ_OS    F T F  F IE  F IE
11 LT_OQ    T F F  F -   F IE
12 LE_OQ    T T F  F -   F IE
13 UNORD_S  F F F  T IE  T IE
14 NEQ_US   T F T  T IE  T IE
15 NLT_UQ   F T T  T -   T IE
16 NLE_UQ   F F T  T -   T IE
17 ORD_S    T T T  F IE  F IE
18 EQ_US    F T F  T IE  T IE
19 NGE_UQ   T F F  T -   T IE
1A NGT_UQ   T T F  T -   T IE
1B FALSE_OS F F F  F IE  F IE
1C NEQ_OS   T F T  F IE  F IE
1D GE_OQ    F T T  F -   F IE
1E GT_OQ    F F T  F -   F IE
1F TRUE_US  T T T  T IE  T IE"""
    cases = [(ONE, TWO), (ONE, ONE), (TWO, ONE), (0x7FC00000, ONE), (0x7F800001, ONE)]
    for line in hand.splitlines():
        f = line.split()
        imm, name = int(f[0], 16), f[1]
        want = [(f[2] == "T", "-"), (f[3] == "T", "-"), (f[4] == "T", "-"), (f[5] == "T", f[6]), (f[7] == "T", f[8])]
        check("C5 imm %02X name" % imm, fp_ops.CMP_PREDICATES[imm][0], name)
        for (a_, b_), w in zip(cases, want):
            t, fl = fp_ops.cmp_pred(a_, b_, imm, D)
            check("C5 %s(%08X,%08X)" % (name, a_, b_), (t, flags_str(fl)), w)
    # C2: EVEX compare into k with a source mask: masked lanes are not compared and raise nothing.
    v = pack([ONE, 0x7FC00000, TWO, 0x7F800001], 32)
    u3 = P_["UNORD_Q"]
    check("C2 k=1011", tuple(map(str, vec.packed_cmp_k(fp_ops.cmp_pred, v, v, u3, D, 128, k=0b1011))), ("10", "1"))
    check("C2 k=0011 hides SNaN lane", vec.packed_cmp_k(fp_ops.cmp_pred, v, v, u3, D, 128, k=0b0011), (0b0010, 0))
    # C3: VEX compare -> all-ones lanes.
    check("C3 vex unord lanes", lanes(vec.packed_cmp_vec(fp_ops.cmp_pred, v, v, u3, D, 128)[0], 32, 4),
          [0, 0xFFFFFFFF, 0, 0xFFFFFFFF])
    # C4: (U)COMISS -> (ZF, PF, CF).
    check("C4 ucomiss QNaN", fp_ops.comis(0x7FC00000, ONE, D, False), ((1, 1, 1), 0))
    check("C4 comiss QNaN", fp_ops.comis(0x7FC00000, ONE, D, True), ((1, 1, 1), IE))
    check("C4 ucomiss SNaN", fp_ops.comis(0x7F800001, ONE, D, False), ((1, 1, 1), IE))
    check("C4 ucomiss 1<2", fp_ops.comis(ONE, TWO, D, False), ((0, 0, 1), 0))
    check("C4 ucomiss 2>1", fp_ops.comis(TWO, ONE, D, False), ((0, 0, 0), 0))
    check("C4 ucomiss +0,-0", fp_ops.comis(0, 0x80000000, D, False), ((1, 0, 0), 0))


def sec_d_cvt():
    section("D conversions")
    i2f = lambda i, e=D: r(fp_ops.cvt_i32_to_f32, i & 0xFFFFFFFF, e)
    check("D1 2^24+1 RNE -> 2^24", i2f(16777217), ("0x4B800000", P))
    check("D1 2^24+1 RU", i2f(16777217, RU), ("0x4B800001", P))
    check("D1 2^24+3 RNE -> 2^24+4", i2f(16777219), ("0x4B800002", P))
    check("D1 -2^31 exact", i2f(-2147483648), ("0xCF000000", NONE))
    check("D1 2^31-1 RNE", i2f(2147483647), ("0x4F000000", P))
    check("D1 2^31-1 RZ", i2f(2147483647, RZ), ("0x4EFFFFFF", P))
    check("D1 0 -> +0", i2f(0), ("0x00000000", NONE))
    check("D1 65024 exact (Q4 isum bound)", i2f(65024), ("0x477E0000", NONE))
    check("D1 -1032256 exact (Q8 bound)", i2f(-1032256), ("0xC97C0400", NONE))
    f2i = lambda b, e=D, t=False: r(lambda x, ee: fp_ops.cvt_f32_to_i32(x, ee, t), b, e)
    check("D2 2.5 RNE -> 2", f2i(0x40200000), ("0x00000002", P))
    check("D2 3.5 RNE -> 4", f2i(0x40600000), ("0x00000004", P))
    check("D2 -2.5 RNE -> -2", f2i(0xC0200000), ("0xFFFFFFFE", P))
    check("D2 2.5 RD -> 2", f2i(0x40200000, RD), ("0x00000002", P))
    check("D2 2.5 RU -> 3", f2i(0x40200000, RU), ("0x00000003", P))
    check("D2 -2.5 RZ -> -2", f2i(0xC0200000, RZ), ("0xFFFFFFFE", P))
    check("D2 0.5 -> 0", f2i(0x3F000000), ("0x00000000", P))
    check("D2 1.5 -> 2", f2i(0x3FC00000), ("0x00000002", P))
    check("D2 -0.5 -> 0", f2i(0xBF000000), ("0x00000000", P))
    check("D2 2^31-128 exact", f2i(0x4EFFFFFF), ("0x7FFFFF80", NONE))
    check("D2 2^31 -> indefinite", f2i(0x4F000000), ("0x80000000", "IE"))
    check("D2 -2^31 exact (not indefinite)", f2i(0xCF000000), ("0x80000000", NONE))
    check("D2 -(2^31+256) -> indefinite", f2i(0xCF000001), ("0x80000000", "IE"))
    check("D2 QNaN -> indefinite", f2i(0x7FC00000), ("0x80000000", "IE"))
    check("D2 +inf -> indefinite", f2i(PINF), ("0x80000000", "IE"))
    check("D2 -0 -> 0", f2i(0x80000000), ("0x00000000", NONE))
    check("D2 den RU DAZ=0 -> 1 (no DE)", f2i(DEN1, RU), ("0x00000001", P))
    check("D2 den RU DAZ=1 -> 0", f2i(DEN1, Env.make(rc=RC_RU, daz=True)), ("0x00000000", NONE))
    check("D2 127.0 -> 127", f2i(0x42FE0000), ("0x0000007F", NONE))
    check("D3 trunc 2.75", f2i(0x40300000, D, True), ("0x00000002", P))
    check("D3 trunc -2.75", f2i(0xC0300000, D, True), ("0xFFFFFFFE", P))
    check("D3 trunc ignores RC (RU)", f2i(0x40300000, RU, True), ("0x00000002", P))
    check("D3 trunc 2^31 -> indefinite", f2i(0x4F000000, D, True), ("0x80000000", "IE"))
    check("D3 trunc 1.0", f2i(ONE, D, True), ("0x00000001", NONE))
    h2f = lambda h, e=D: r(fp_ops.cvt_f16_to_f32, h, e)
    check("D4 f16 1.0", h2f(0x3C00), ("0x3F800000", NONE))
    check("D4 f16 min subnormal 2^-24", h2f(0x0001), ("0x33800000", NONE))
    check("D4 f16 -min subnormal", h2f(0x8001), ("0xB3800000", NONE))
    check("D4 f16 max subnormal", h2f(0x03FF), ("0x387FC000", NONE))
    check("D4 f16 max normal 65504", h2f(0x7BFF), ("0x477FE000", NONE))
    check("D4 f16 0x3555", h2f(0x3555), ("0x3EAAA000", NONE))
    check("D4 f16 +inf", h2f(0x7C00), ("0x7F800000", NONE))
    check("D4 f16 -inf", h2f(0xFC00), ("0xFF800000", NONE))
    check("D4 f16 -0", h2f(0x8000), ("0x80000000", NONE))
    check("D4 f16 SNaN quieted", h2f(0x7C01), ("0x7FC02000", "IE"))
    check("D4 f16 QNaN payload", h2f(0xFE55), ("0xFFCAA000", NONE))
    check("D4 f16 subnormal ignores DAZ", h2f(0x0001, DAZ), ("0x33800000", NONE))


def sec_e_masks():
    section("E masking, broadcast, scalar forms, {er}/{sae}")
    a, b = pack([ONE] * 16, 32), pack([TWO] * 16, 32)
    old = pack([0xDEADBEEF] * 16, 32)
    res, f = vec.packed_fp2(fp_ops.add, a, b, D, 512, k=0x00F0, z=True)
    check("E1 zero-mask", lanes(res, 32, 16), [0] * 4 + [0x40400000] * 4 + [0] * 8)
    res, f = vec.packed_fp2(fp_ops.add, a, b, D, 512, k=0x00F0, z=False, dst=old)
    check("E1 merge-mask", lanes(res, 32, 16), [0xDEADBEEF] * 4 + [0x40400000] * 4 + [0xDEADBEEF] * 8)
    sn = pack([0x7F800001] + [ONE] * 15, 32)
    check("E1 masked-off SNaN raises nothing", vec.packed_fp2(fp_ops.add, sn, b, D, 512, k=0xFFFE)[1], 0)
    check("E1 active SNaN raises IE", vec.packed_fp2(fp_ops.add, sn, b, D, 512, k=0x0001)[1], IE)
    res, _ = vec.packed_fp2(fp_ops.mul, a, None, D, 512, bcast_b=TWO)
    check("E2 {1to16} broadcast", lanes(res, 32, 16), [TWO] * 16)
    s1 = pack([ONE, 0x40A00000, 0x40C00000, 0x40E00000], 32)
    s2 = pack([TWO, 0x41100000, 0x41100000, 0x41100000], 32)
    check("E3 addss upper lanes from src1", lanes(vec.scalar_fp2(fp_ops.add, s1, s2, D)[0], 32, 4),
          [0x40400000, 0x40A00000, 0x40C00000, 0x40E00000])
    d0 = pack([0x12345678, 0, 0, 0], 32)
    check("E4 masked scalar merge", lanes(vec.scalar_fp2(fp_ops.add, s1, s2, D, k=0, dst=d0)[0], 32, 4)[0], 0x12345678)
    check("E4 masked scalar zero", lanes(vec.scalar_fp2(fp_ops.add, s1, s2, D, k=0, z=True)[0], 32, 4)[0], 0)
    er = Env.make(er=RC_RU)
    check("E5 {er} RU overrides MXCSR.RC", fp_ops.add(ONE, 0x33800000, er)[0], 0x3F800001)
    check("E5 {er} implies {sae}: no flags", vec.packed_fp2(fp_ops.add, pack([ONE] * 16, 32),
                                                           pack([0x33800000] * 16, 32), er, 512)[1], 0)
    check("E5 mxcsr_after with sae unchanged", er.mxcsr_after(PE), er.mxcsr)
    try:
        Env(0x1F00)
        check("E6 unmasked env rejected", False, True)
    except UnmodeledEnvironment:
        check("E6 unmasked env rejected", True, True)
    check("E7 VEX write zeroes upper bits", vec.write_dest((1 << 512) - 1, 0xABC, 128, "vex"), 0xABC)
    check("E7 legacy write preserves upper bits", vec.write_dest(1 << 300, 0xABC, 128, "legacy"), (1 << 300) | 0xABC)
    # E8: full-width destinations of the scalar converts (review R1-6; SDM Vol 2 CVTSI2SS, CVTTSS2SI).
    old = pack([0x11110000 + i for i in range(16)], 32)             # recognisable 512-bit old destination
    e = table.find("CVTSI2SS")                                      # legacy: lanes 1-3 AND bits 511:128 kept
    r128, fl = e["_sem"](old, 5, D)
    check("E8 CVTSI2SS legacy full width", lanes(table.write_full(e, r128, old), 32, 16),
          [0x40A00000] + [0x11110000 + i for i in range(1, 16)])
    e = table.find("VCVTSI2SS")                                     # VEX: lanes 1-3 from src1, bits 511:128 zeroed
    src1 = pack([0x22220000 + i for i in range(4)], 32)
    r128, fl = e["_sem"](src1, (-3) & 0xFFFFFFFF, D)
    check("E8 VCVTSI2SS VEX full width", lanes(table.write_full(e, r128, old), 32, 16),
          [0xC0400000, 0x22220001, 0x22220002, 0x22220003] + [0] * 12)
    check("E8 VCVTSI2SS 2^24+1 inexact flag", table.find("VCVTSI2SS")["_sem"](0, 16777217, D)[1], PE)
    e = table.find("CVTTSS2SI")                                     # r32 destination zero-extends to 64 bits
    check("E8 CVTTSS2SI -2.75 -> r64", e["_sem"](0xC0300000, D), (0x00000000FFFFFFFE, PE))
    check("E8 VCVTTSS2SI NaN -> indefinite, zero-extended", table.find("VCVTTSS2SI")["_sem"](0x7FC00000, D),
          (0x0000000080000000, IE))
    check("E8 CVTSS2SI 2.5 RU -> 3", table.find("CVTSS2SI")["_sem"](0x40200000, RU), (3, PE))
    e = table.find("ADDSS")                                         # legacy ADDSS: src1 is the destination
    r128, _ = e["_sem"](old, pack([TWO], 32), D)
    full = table.write_full(e, r128, old)
    check("E8 ADDSS legacy keeps lanes 1-15", lanes(full, 32, 16)[1:], [0x11110000 + i for i in range(1, 16)])
    e = table.find("VADDSS", encoding="evex")
    r128, _ = e["_sem"](pack([ONE, 7, 8, 9], 32), pack([TWO], 32), D)
    check("E8 EVEX VADDSS zeroes 511:128", lanes(table.write_full(e, r128, old), 32, 16), [0x40400000, 7, 8, 9] + [0] * 12)
    rf, fl = table.find("VUCOMISS")["_sem"](ONE, 0x7FC00000, D)
    check("E8 VUCOMISS RFLAGS full", (rf, fl), ({"ZF": 1, "PF": 1, "CF": 1, "OF": 0, "SF": 0, "AF": 0}, 0))


def sec_f_int():
    section("F integer: maddubs, maddwd, dpbusd, phaddd, abs/sign, packs")
    w16 = lambda v, n: [x - 0x10000 if x & 0x8000 else x for x in lanes(v, 16, n)]
    a = pack([255, 255, 1, 2] + [0] * 12, 8)
    b = pack([127, 127, (-3) & 0xFF, 4] + [0] * 12, 8)
    check("F1 maddubs saturate +, and 1*-3+2*4", w16(int_ops.pmaddubsw(a, b, 128), 8)[:2], [32767, 5])
    a = pack([255, 255] + [0] * 14, 8)
    b = pack([0x80, 0x80] + [0] * 14, 8)
    check("F1 maddubs saturate -", w16(int_ops.pmaddubsw(a, b, 128), 8)[0], -32768)
    check("F2 maddwd all 0x8000 wraps", lanes(int_ops.pmaddwd(pack([0x8000] * 2, 16), pack([0x8000] * 2, 16), 32), 32, 1)[0], 0x80000000)
    check("F2 maddwd 2*4+3*5", lanes(int_ops.pmaddwd(pack([2, 3], 16), pack([4, 5], 16), 32), 32, 1)[0], 23)
    check("F3 dpbusd wraps", lanes(int_ops.pdpbusd(0x7FFFFFFF, 1, 1, 32), 32, 1)[0], 0x80000000)
    check("F3 dpbusds saturates", lanes(int_ops.pdpbusd(0x7FFFFFFF, 1, 1, 32, saturate=True), 32, 1)[0], 0x7FFFFFFF)
    check("F3 dpbusd 10 + 4*255*-128", int_ops.pdpbusd(10, pack([255] * 4, 8), pack([0x80] * 4, 8), 32), 0xFFFE020A)
    A, B = pack(list(range(1, 9)), 32), pack([10 * i for i in range(1, 9)], 32)
    check("F4 phaddd 256", lanes(int_ops.phaddd(A, B, 256), 32, 8), [3, 7, 30, 70, 11, 15, 110, 150])
    check("F5 pabsb(-128) = 0x80", int_ops.pabsb(0x80, 8), 0x80)
    check("F5 psignb(-128,-1) wraps", int_ops.psignb(0x80, 0xFF, 8), 0x80)
    check("F5 psignb(5,0)", int_ops.psignb(5, 0, 8), 0)
    check("F5 psignb(5,-3)", int_ops.psignb(5, 0xFD, 8), 0xFB)
    v = int_ops.packssdw(pack([40000, (-40000) & 0xFFFFFFFF, 7, 0], 32), 0, 128)
    check("F6 packssdw saturates", lanes(v, 16, 4)[:3], [0x7FFF, 0x8000, 7])
    v = int_ops.packsswb(pack([200, (-200) & 0xFFFF, 5], 16), 0, 128)
    check("F6 packsswb saturates", lanes(v, 8, 3), [0x7F, 0x80, 5])
    check("F7 pmovdb truncates", int_ops.pmovdb(0x180, 32), 0x80)
    check("F8 permd 512 idx-first arg order", lanes(int_ops.permd(pack(list(range(100, 116)), 32),
                                                                  pack([15 - i for i in range(16)], 32), 512), 32, 2),
          [115, 114])
    check("F9 movhlps", lanes(int_ops.movhlps(pack([1, 2, 3, 4], 32), pack([5, 6, 7, 8], 32)), 32, 4), [7, 8, 3, 4])
    check("F9 shufps imm 1", lanes(int_ops.shufps(pack([1, 2, 3, 4], 32), pack([1, 2, 3, 4], 32), 1, 128), 32, 4)[0], 2)


def _rand_f32(rng, lo_e=120, hi_e=134):
    return (rng.getrandbits(1) << 31) | (rng.randint(lo_e, hi_e) << 23) | rng.getrandbits(23)


def sec_g_hearth():
    section("G Hearth compositions (derived)")
    rng = random.Random(20261016)
    # red8: lane i = sum of row i's 8 partials (wrapping int32).
    for t in range(20):
        s = [[rng.getrandbits(32) for _ in range(8)] for _ in range(8)]
        got = lanes(hk.red8([pack(x, 32) for x in s]), 32, 8)
        check("G1 red8 %d" % t, got, [sum(x) & 0xFFFFFFFF for x in s])
    # red_quads: lane 4k+j = total of quad j's 128-bit lane k.
    for t in range(10):
        q = [[rng.getrandbits(32) for _ in range(16)] for _ in range(4)]
        got = lanes(hk.red_quads(*[pack(x, 32) for x in q]), 32, 16)
        want = [sum(q[j][4 * k:4 * k + 4]) & 0xFFFFFFFF for k in range(4) for j in range(4)]
        check("G2 red_quads %d" % t, got, want)
        got1 = lanes(hk.red_quad1(pack(q[0], 32)), 32, 4)
        check("G2 red_quad1 %d" % t, got1, [sum(q[0][4 * k:4 * k + 4]) & 0xFFFFFFFF for k in range(4)])
    # tree16 (AVX2 lo/hi and AVX-512) == NUMERICS sum16 tree, bit for bit, incl. signed zeros.
    for t in range(40):
        L = [_rand_f32(rng) for _ in range(16)]
        if t % 4 == 0:
            L = [0x80000000] * 16                         # all -0: tree must give -0
        if t % 4 == 1:
            L[rng.randrange(16)] = 0x7FC00000 | rng.getrandbits(10)
        ref = hk.canon_scalar(hk.sum16_ref(L))
        check("G3 tree16 avx2 %d" % t, hk.tree16_avx2(pack(L[:8], 32), pack(L[8:], 32)), ref)
        check("G3 tree16 avx512 %d" % t, hk.tree16_avx512(pack(L, 32)), ref)
    # act_q8: scalar == AVX2 == AVX-512 on hand-built blocks (NUMERICS §2 + degenerate cases).
    blocks = _act_blocks(rng)
    for name, x in blocks.items():
        s = hk.act_q8_scalar(x)
        check("G4 act_q8 avx2 == scalar [%s]" % name, hk.act_q8_avx2(x), s)
        check("G4 act_q8 avx512 == scalar [%s]" % name, hk.act_q8_avx512(x), s)
        check("G4 |q| <= 127 [%s]" % name, max(abs(v) for v in s[2]) <= 127, True)
    # Q4 / Q8 block integer sums: AVX2 maddubs paths and AVX-512 VNNI path == scalar.
    for t in range(30):
        xq = [rng.randint(-127, 127) for _ in range(64)]
        if t == 0:
            xq = [-127] * 64
        qs = [rng.getrandbits(8) for _ in range(32)]
        wq = [rng.randint(-128, 127) for _ in range(64)]
        if t == 1:
            wq, xq = [-128] * 64, [127] * 64
        asum = sum(xq)
        sc4, sc8 = hk.isum_q4_scalar(qs, xq), hk.isum_q8_scalar(wq, xq)
        check("G5 q4 avx2 %d" % t, hk.isum_q4_avx2(qs, xq, asum), sc4)
        nib = [b & 0x0F for b in qs] + [b >> 4 for b in qs]
        check("G5 q4 vnni %d" % t, hk.isum_vnni(nib, xq, asum, 8), sc4)
        check("G5 q8 avx2 sign trick %d" % t, hk.isum_q8_avx2(wq, xq), sc8)
        check("G5 q8 vnni %d" % t, hk.isum_vnni([(w + 128) & 0xFF for w in wq], xq, asum, 128), sc8)
    # The AVX2 Q8 sign trick needs x != -128 (activation domain): a witness that it is load-bearing.
    xq, wq = [-128] + [0] * 63, [-1] + [0] * 63
    check("G6 sign trick breaks at x=-128 (T2 precondition)", (hk.isum_q8_avx2(wq, xq), hk.isum_q8_scalar(wq, xq)), (-128, 128))
    # G7: DOM-ACT-SUM is load-bearing: the SIMD Q4/Q8 paths read a.sum, the scalar meaning never does.
    xq = [rng.randint(-127, 127) for _ in range(64)]
    wq = [rng.randint(-128, 127) for _ in range(64)]
    off = hk.isum_vnni([(w + 128) & 0xFF for w in wq], xq, sum(xq) + 1, 128) - hk.isum_q8_scalar(wq, xq)
    check("G7 a.sum off by one shifts the VNNI Q8 isum by -128 (DOM-ACT-SUM)", off, -128)
    check("H3' AVX2 Q4 red8 before the bias", bounds.isum_bounds()["q4_avx2_red8_before_bias"], 121920)


def _act_blocks(rng):
    f = hk.f32
    B = {}
    B["gauss-like"] = [_rand_f32(rng, 124, 128) for _ in range(64)]
    x = [_rand_f32(rng, 124, 128) for _ in range(64)]
    x[1], x[9], x[17], x[40] = 0x7FC00000, 0x7F800001 | 0x1234, 0x7F800000, 0xFF800000
    B["nan-inf"] = x                       # NaNs AND infinities: amax = +inf, every q = 0
    x = [_rand_f32(rng, 124, 128) for _ in range(64)]
    x[63] = 0xFFC00ABC                      # one QNaN, last element of its lane chain, no inf
    B["nan-only"] = x
    # amax ~ 1e-39 < 127 * 2^-128: d = amax/127 is so small that id = 1/d overflows to +inf
    B["subnormal-scale"] = [f("1e-39") if i & 1 else f("-3e-40") for i in range(64)]
    B["flt-max"] = [(0x7F7FFFFF | (0x80000000 if i & 8 else 0)) if i % 7 == 0 else _rand_f32(rng, 124, 128) for i in range(64)]
    B["ties"] = [f(127)] + [f(k + Fraction_half(k)) for k in range(-60, 3)]
    B["zeros"] = [0x80000000 if i & 1 else 0 for i in range(64)]
    # amax = 1e-36 > 127 * 2^-128: d is subnormal but id = 1/d stays finite
    B["small-normal-scale"] = [f("1e-36") if i & 1 else f("-4e-37") for i in range(64)]
    # Regression witness from review R1-1 (2026-10-16): the block maximum heads AVX2 chain 0 and a
    # QNaN sits later in the same chain (x[8]); the commuted max discards x[0], amax collapses to 1.0.
    x = [f(1)] * 64
    x[0], x[8] = f(100), 0x7FC00000
    B["nan-erases-chain-max"] = x
    return B


def Fraction_half(k):
    from fractions import Fraction
    return Fraction(1, 2) if k % 2 else Fraction(-1, 2)


MUTANTS = ["commute_max", "trunc", "clamp128", "no_ord_zero", "tie_away"]


def mutant_witness_table():
    """For each act_q8 mutant (applied to the AVX2 and AVX-512 variants only, so the ISA-identity
    tests could see it) list the blocks on which its output differs from the scalar meaning."""
    rng = random.Random(20261016)
    blocks = _act_blocks(rng)
    out = {}
    for m in MUTANTS:
        diff = []
        for name, x in blocks.items():
            ref = hk.act_q8_scalar(x)
            if hk.act_q8_avx2(x, frozenset([m])) != ref or hk.act_q8_avx512(x, frozenset([m])) != ref:
                diff.append(name)
        out[m] = diff
    return out


def sec_h_bounds_mutants():
    section("H T2 bounds (exhaustive per product) and mutant witnesses")
    b = bounds.all_bounds()
    check("H1 Q4 maddubs pair bound", b["q4_maddubs"]["pair_bound"], 3810)
    check("H1 Q4 no saturation", b["q4_maddubs"]["pair_saturates"], False)
    check("H1 Q4 VPADDW bound", b["q4_maddubs"]["vpaddw_bound"], 7620)
    check("H1 Q4 if x were int8", b["q4_maddubs_if_x_were_int8"]["pair_bound"], 3840)
    check("H2 Q8 sign-trick pair bound", b["q8_sign_trick"]["pair_bound"], 32512)
    check("H2 Q8 identity holds on x in [-127,127]", b["q8_sign_trick"]["identity_failures"], [])
    check("H2 Q8 no saturation", b["q8_sign_trick"]["pair_saturates"], False)
    bad = b["q8_sign_trick_if_x_could_be_-128"]["identity_failures"]
    check("H2 x=-128 breaks identity for every w<0", sorted(bad) == [(w, -128) for w in range(-128, 0)], True)
    i = b["isum"]
    check("H3 Q4 isum bound", i["q4_isum"], 65024)
    check("H3 Q8 isum (any byte)", i["q8_isum_any_byte"], 1040384)
    check("H3 Q8 isum (quantiser)", i["q8_isum_quantiser"], 1032256)
    check("H3 exact int->f32", (i["q4_exact_f32"], i["q8_exact_f32"]), (True, True))
    check("H3 VNNI no int32 wrap", i["vnni_no_int32_wrap"], True)
    w = mutant_witness_table()
    # The commuted max m = max(m, |v|) lets a NaN into m: a NaN at position p of lane chain c
    # (AVX2 c = p mod 8, AVX-512 c = p mod 16) sets m_c = NaN, and the NEXT element q of chain c sets
    # m_c = |x_q| (MAXPS returns src2 when src1 is NaN), discarding every chain-c element before p.
    # So the mutant is visible iff (i) the block maximum is in chain c before p and nothing after p in
    # chain c, nor any other chain, reaches it; or (ii) p ends its chain, so the NaN enters hmax8 /
    # hmax16: it reaches the root (x[63]: d becomes NaN) or erases the lanes merged with it so far
    # (hearth_kernels.nan_tree_fate). Corrected 2026-10-16 (review R1-1); the earlier comment said
    # only chain ends matter, which was wrong. The 'nan-inf' block does not witness it: its NaNs head
    # their chains or follow an infinity that sets amax = +inf in both versions.
    check("H4 commute-before-MAXPS witnessed by exactly these blocks", w["commute_max"],
          ["nan-only", "nan-erases-chain-max"])
    check("H4 RNE->trunc seen on ordinary data", "gauss-like" in w["trunc"] and "ties" in w["trunc"], True)
    check("H4 127->128 clamp seen only with id = +inf (tiny amax)", w["clamp128"], ["subnormal-scale"])
    check("H4 removed NaN zeroing seen only with NaN input", w["no_ord_zero"],
          ["nan-inf", "nan-only", "nan-erases-chain-max"])
    check("H4 tie flip seen on the tie block", "ties" in w["tie_away"], True)
    # H5: the derived rule, first against a hand derivation (maximum at x[0], one NaN at p = 1..63;
    # review R1-1 evidence: AVX2 x[8,16,...,56,60,62,63], AVX-512 x[16,32,48,56,60,62,63]) ...
    check("H5 rule, AVX2, max at x[0]", [p for p in range(1, 64) if hk.commute_max_visible(8, 0, p)],
          [8, 16, 24, 32, 40, 48, 56, 60, 62, 63])
    check("H5 rule, AVX-512, max at x[0]", [p for p in range(1, 64) if hk.commute_max_visible(16, 0, p)],
          [16, 32, 48, 56, 60, 62, 63])
    check("H5 tree fate lane 6 of 8 erases the even lanes", hk.nan_tree_fate(8, 6), ("erased", frozenset({0, 2, 4, 6})))
    check("H5 tree fate lane 15 of 16 reaches the root", hk.nan_tree_fate(16, 15)[0], "root")
    # ... then against table-semantics simulation: maximum (100.0) at the head of chain c, every other
    # element 1.0, one QNaN at p. Default: 3 chains per ISA x 64 positions; --full: every chain.
    full = "--full" in sys.argv
    ONE_, BIG = hk.f32(1), hk.f32(100)
    n_cases = n_bad = 0
    for L, fn in ((8, hk.act_q8_avx2), (16, hk.act_q8_avx512)):
        chains = range(L) if full else (0, L // 2 - 1, L - 1)
        for c in chains:
            for p in range(64):
                x = [ONE_] * 64
                x[c], x[p] = BIG, 0x7FC00000
                ref = hk.act_q8_scalar(x)
                sim = fn(x, frozenset(["commute_max"])) != ref
                n_cases += 1
                n_bad += sim != hk.commute_max_visible(L, c, p)
    check("H5 derived rule == simulation on %d cases" % n_cases, n_bad, 0)
    return b, w


def sec_i_registry():
    section("I registry")
    keys = [(e["key"]["iclass"], e["key"]["iform"]) for e in table.ENTRIES]
    check("I1 unique (iclass, iform) keys", len(keys), len(set(keys)))
    idx = table.index()
    check("I2 hash deterministic", table.index()["entries"][0]["content_hash"], idx["entries"][0]["content_hash"])
    e = table.find("VADDPS", encoding="evex", vl=512)
    res, fl = e["_sem"](pack([ONE] * 16, 32), pack([TWO] * 16, 32), D, k=0x1, z=True)
    check("I3 registry VADDPS zmm{k}{z}", lanes(res, 32, 2), [0x40400000, 0])
    e = table.find("VADDPS", encoding="evex", vl=512, mem=True)
    res, fl = e["_sem"](pack([ONE] * 16, 32), None, D, bcast_src2=TWO)
    check("I3 registry VADDPS zmm, m32{1to16}", lanes(res, 32, 16), [0x40400000] * 16)
    e = table.find("VCMPPS", encoding="evex", vl=512)
    check("I3 registry VCMPPS k", e["_sem"](pack([0x7FC00000] + [ONE] * 15, 32), pack([ONE] * 16, 32), 3, D)[0], 1)
    e = table.find("VPDPBUSD", encoding="evex", vl=512)
    check("I3 registry VPDPBUSD", lanes(e["_sem"](0, pack([2] * 64, 8), pack([3] * 64, 8)), 32, 1)[0], 24)
    check("I3 registry VPDPBUSD {k}{z}", lanes(e["_sem"](pack([5] * 16, 32), pack([1] * 64, 8), pack([1] * 64, 8),
                                                         k=0b10, z=True), 32, 2), [0, 9])
    check("I4 FP families", table.FAMILIES_FP, sorted(set(table.FAMILIES_FP)))
    # I5: schema fields present and hashed (review R1-4, R1-8, R2-9, R2-13).
    need = ("elem", "operands", "operands_status", "upper", "scalar", "nan_role", "sem", "table_source")
    check("I5 every entry carries the schema fields", [e["key"]["iform"] for e in table.ENTRIES
                                                       if any(k not in e for k in need)], [])
    check("I5 table_source vocabulary", sorted({e["table_source"] for e in table.ENTRIES}), ["sdm", "sdm+bochs"])
    # I6: operand roles agree with the NaN rule and with the encoding's first-source convention
    # (EVEX: REG2 = src1 after REG1 = mask; VEX: REG1 = src1; legacy: REG0 is dst AND src1, read-write).
    bad = []
    for e in table.ENTRIES:
        roles = {o["role"]: o for o in e["operands"]}
        rule = table.NAN_RULES.get(e["nan_rule"])
        if rule:
            for need_role in rule["roles"]:
                if need_role not in roles and not (need_role == "src1" and "dst_src1" in roles):
                    bad.append((e["key"]["iform"], "missing " + need_role))
        s1 = roles.get("src1") or roles.get("dst_src1")
        if s1 and e["family"] != "FP.COMI.f32":
            want = {"evex": "REG2", "vex": "REG1", "legacy": "REG0"}[e["encoding"]]
            if s1["xed"] != want or (e["encoding"] == "legacy" and s1["access"] != "rw"):
                bad.append((e["key"]["iform"], "src1 at %s" % s1["xed"]))
        if e["encoding"] == "evex" and "mask" not in roles:
            bad.append((e["key"]["iform"], "EVEX without mask operand"))
    check("I6 operand roles consistent with nan_rule and encoding", bad, [])
    # I7: transparency is a whitelist (RULES.md §2): no operand is transparent or erasing unless its
    # family's justification says so; unknown roles default to observer.
    bad = []
    for e in table.ENTRIES:
        for role, v in e["nan_role"].items():
            just = table.NAN_ROLE_JUSTIFICATION.get(e["family"], "")
            if v != table.OB and not just.startswith(v):
                bad.append((e["key"]["iform"], role, v))
    check("I7 nan_role whitelist", bad, [])
    check("I7 unlisted operand defaults to observer", table.nan_role_of(table.find("VPDPBUSD", vl=512), "src1"), "observer")
    # I8: `_sem` is built from the hashed spec, and changing the wiring changes the hash (R1-5, R2-10).
    check("I8 every _sem carries its spec", [e["key"]["iform"] for e in table.ENTRIES if e["_sem"].spec != e["sem"]], [])
    b0 = table.bundle_hash()
    for iform, edit in (("VPDPBUSD_ZMMi32_MASKmskw_ZMMu8_ZMMu32_AVX512", lambda d: d["sem"].update(saturate=True)),
                        ("VCVTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512", lambda d: d["sem"].update(trunc=True)),
                        ("VCVTPH2PS_ZMMf32_MASKmskw_YMMf16_AVX512", lambda d: d["sem"].update(src_eb=32)),
                        ("VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512",
                         lambda d: (d["operands"][2].update(role="src2"), d["operands"][3].update(role="src1"))),
                        ("VCOMISS_XMMd_XMMd", lambda d: d["sem"].update(signalling=False))):
        e = table.find(iform.split("_")[0], iform=iform)
        d = copy.deepcopy(table._decl(e))
        edit(d)
        check("I8 wiring edit re-keys %s" % iform, table.content_hash(d, b0) != table.content_hash(e, b0), True)
    probe = pack([ONE, 0x7FC00001, 0x00000001, 0xC0300000] * 4, 32)
    e = table.find("VCVTPS2DQ", encoding="evex", vl=512)
    check("I8 rebuilt closure == registered closure", table.build_sem(e["sem"], 512)(probe, D), e["_sem"](probe, D))
    # I9: intrinsic_map v0 covers every intrinsic in quant_avx2.c / quant_avx512.c at b5d3f14 (130,
    # TABLE-SCHEMA §9) and the compositions above ran on hashed entries.
    check("I9 intrinsic map size", len(hk.INTRINSIC_MAP_V0), 130)
    fp_unresolved = [n for n, m in hk.INTRINSIC_MAP_V0.items() if not isinstance(m, str)
                     and m[0] in {"VADDPS", "VMULPS", "VMAXPS", "VMINPS", "VCMPPS", "VCVTDQ2PS", "VCVTPS2DQ",
                                  "VCVTPH2PS", "VADDSS", "VMULSS", "VMAXSS"} and hk.resolve_intrinsic(n) is None]
    check("I9 every FP intrinsic resolves to a table entry", fp_unresolved, [])
    used = hk.entries_used()
    check("I9 compositions recorded their entries", len(used) >= 10 and all(len(h) == 64 for h in used.values()), True)
    return idx


def sec_j_tools():
    section("J census absorber and host cross-check")
    from . import census_absorb, crosscheck
    ok, _ = census_absorb._selftest()
    check("J1 census_absorb synthetic census", ok, True)
    rep = crosscheck.main(2000, seed=7)
    for op, v in rep.items():
        check("J2 host binary64 cross-check %s (agree %d, skipped %d)" % (op, v["agree"], v["skipped"]),
              v["disagree"], 0)
    return rep


def main():
    sec_a_arith()
    sec_b_minmax()
    sec_c_cmp()
    sec_d_cvt()
    sec_e_masks()
    sec_f_int()
    sec_g_hearth()
    b, w = sec_h_bounds_mutants()
    idx = sec_i_registry()
    xc = sec_j_tools()
    print()
    print("host cross-check:", {k: (v["agree"], v["disagree"], v["skipped"]) for k, v in xc.items()},
          "(agree, disagree, skipped)")
    print("checks: %d   failures: %d" % (COUNT["n"], len(FAIL)))
    for f in FAIL:
        print("FAIL", f)
    print("table: %d entries, %d FP-sensitive families: %s" % (len(idx["entries"]), len(table.FAMILIES_FP),
                                                              ", ".join(table.FAMILIES_FP)))
    print("semantics bundle sha256:", idx["semantics_bundle"])
    print("intrinsic_map v0 sha256:", hk.intrinsic_map_hash(), "| entries used by the compositions:",
          len(hk.entries_used()), "| int_ops functions without entries:", len(hk.unregistered_used()))
    print("T2: Q4 pair %d, Q4 vpaddw %d, Q8 pair %d, Q4 isum %d, Q8 isum %d/%d" % (
        b["q4_maddubs"]["pair_bound"], b["q4_maddubs"]["vpaddw_bound"], b["q8_sign_trick"]["pair_bound"],
        b["isum"]["q4_isum"], b["isum"]["q8_isum_quantiser"], b["isum"]["q8_isum_any_byte"]))
    print("mutant witnesses (blocks that distinguish):", w)
    return len(FAIL)


if __name__ == "__main__":
    sys.exit(main())
