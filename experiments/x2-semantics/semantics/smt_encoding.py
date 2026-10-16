"""Prototype SMT encoding of table entries (TABLE-SCHEMA.md §5-6) and rule-proof probes (RULES.md §3).
Counterexample bit patterns differ between runs; quote them as examples.

The x86 NaN layer is bit-vector logic wrapped around an SMT-LIB FPA core:
  * lanes are (_ BitVec 32); FPA values are obtained with fpBVToFP (bit reinterpretation);
  * the FPA result is converted back with fpToIEEEBV ONLY on the non-NaN path (where the map is
    injective, so the choice of NaN encoding inside the solver never matters);
  * NaN selection, quieting and the QNaN indefinite are explicit ite-terms on the input bits;
  * DAZ is an input rewrite; FTZ flushes using tininess AFTER rounding, computed by rounding the
    same operation in a wide-exponent format FP(10, 24) where nothing is subnormal.
Optional dependency: z3-solver (pip). Not part of the self-test.

Run:  python -B -m semantics.smt_encoding [timeout_s]    (prints one line per probe with timing)
"""
import random
import sys
import time

import z3

from . import fp_ops
from .fpenv import Env

F32 = z3.Float32()
WIDE = z3.FPSort(10, 24)          # same precision, unbounded-enough exponent: no subnormals here
RNE = z3.RNE()
BV = lambda v: z3.BitVecVal(v, 32)


def is_nan(x):
    return z3.And(z3.Extract(30, 23, x) == 0xFF, z3.Extract(22, 0, x) != 0)


def is_denormal(x):
    return z3.And(z3.Extract(30, 23, x) == 0, z3.Extract(22, 0, x) != 0)


def is_zero(x):
    return z3.Extract(30, 0, x) == 0


def quiet(x):
    return x | BV(0x00400000)


def fp(x):
    return z3.fpBVToFP(x, F32)


def daz_in(x, daz):
    return z3.If(z3.And(daz, is_denormal(x)), x & BV(0x80000000), x) if daz is not False else x


def _ftz_out(r_bits, wide_r, ftz):
    if ftz is False:
        return r_bits
    tiny = z3.And(z3.Not(z3.fpIsZero(wide_r)),
                  z3.fpLT(z3.fpAbs(wide_r), z3.FPVal(2.0 ** -126, WIDE)))
    sign = z3.If(z3.fpIsNegative(wide_r), BV(0x80000000), BV(0))
    return z3.If(z3.And(ftz, tiny), sign, r_bits)


def arith2(op, a, b, rm=RNE, daz=False, ftz=False):
    """x86 two-source arithmetic lane (ADD/SUB/MUL/DIV PS/SS) as a BV term."""
    fpop = {"add": z3.fpAdd, "sub": z3.fpSub, "mul": z3.fpMul, "div": z3.fpDiv}[op]
    a2, b2 = daz_in(a, daz), daz_in(b, daz)
    r = fpop(rm, fp(a2), fp(b2))
    wide = fpop(rm, z3.fpFPToFP(rm, fp(a2), WIDE), z3.fpFPToFP(rm, fp(b2), WIDE))
    core = z3.If(z3.fpIsNaN(r), BV(0xFFC00000), _ftz_out(z3.fpToIEEEBV(r), wide, ftz))
    return z3.If(is_nan(a), quiet(a), z3.If(is_nan(b), quiet(b), core))


def maxmin(want_max, a, b, daz=False):
    a2, b2 = daz_in(a, daz), daz_in(b, daz)
    gt = z3.fpGT(fp(a2), fp(b2)) if want_max else z3.fpLT(fp(a2), fp(b2))
    sel_b = z3.Or(is_nan(a2), is_nan(b2), z3.And(is_zero(a2), is_zero(b2)))
    return z3.If(sel_b, b2, z3.If(gt, a2, b2))


def cvt_f2i(a, rm, daz=False):
    """CVT(T)PS2DQ lane: integer indefinite on NaN/inf/out of range. DAZ flushes a denormal source."""
    f = fp(daz_in(a, daz))
    lo, hi = z3.FPVal(-2.0 ** 31, F32), z3.FPVal(2.0 ** 31, F32)
    rounded = z3.fpRoundToIntegral(rm, f)
    ok = z3.And(z3.Not(z3.fpIsNaN(f)), z3.Not(z3.fpIsInf(f)), z3.fpGEQ(rounded, lo), z3.fpLT(rounded, hi))
    return z3.If(ok, z3.fpToSBV(rm, f, z3.BitVecSort(32)), BV(0x80000000))


# ---------------------------------------------------------------- differential: SMT term vs Python

def _eval(term):
    return z3.simplify(term).as_long()


def differential(n=1000, seed=3):
    """Evaluate the SMT terms on concrete vectors (incl. NaN payloads, denormals, zeros, inf and the
    conversion boundaries) and compare with fp_ops under the same environment. Returns the mismatch
    list. Coverage (extended 2026-10-16, review R1-10): add, sub, mul, div, max, min under default,
    DAZ only, FTZ only and DAZ+FTZ (RNE); cvt f32->i32 under RNE and RZ (truncating) with and without
    DAZ. The R19 proof uses `sub` and `cvt_f2i`, so both are now checked against the reference."""
    rng = random.Random(seed)
    specials = [0, 0x80000000, 0x7F800000, 0xFF800000, 0x7FC00001, 0xFFC12345, 0x7F800001, 0xFF812345,
                0x00000001, 0x80000003, 0x00800000, 0x007FFFFF, 0x3F800000, 0x7F7FFFFF, 0x00800001, 0x3F7FFFFE,
                0x4F000000, 0xCF000000, 0xCF000001, 0x4EFFFFFF, 0x3F000000, 0xBFC00000, 0x40200000, 0xC0200000]
    pool = specials + [rng.getrandbits(32) for _ in range(40)]
    mism = []
    a, b = z3.BitVecs("a b", 32)
    envs = [(Env.make(), False, False), (Env.make(daz=True), True, False), (Env.make(ftz=True), False, True),
            (Env.make(daz=True, ftz=True), True, True)]
    terms = {}
    for env, daz, ftz in envs:
        for op in ("add", "sub", "mul", "div"):
            terms[(op, daz, ftz)] = arith2(op, a, b, RNE, z3.BoolVal(daz), z3.BoolVal(ftz))
        terms[("max", daz, ftz)] = maxmin(True, a, b, z3.BoolVal(daz))
        terms[("min", daz, ftz)] = maxmin(False, a, b, z3.BoolVal(daz))
        terms[("cvt_rne", daz, ftz)] = cvt_f2i(a, RNE, z3.BoolVal(daz))
        terms[("cvtt", daz, ftz)] = cvt_f2i(a, z3.RTZ(), z3.BoolVal(daz))
    py = {"add": fp_ops.add, "sub": fp_ops.sub, "mul": fp_ops.mul, "div": fp_ops.div, "max": fp_ops.max_,
          "min": fp_ops.min_, "cvt_rne": lambda x, y, e: fp_ops.cvt_f32_to_i32(x, e, False),
          "cvtt": lambda x, y, e: fp_ops.cvt_f32_to_i32(x, e, True)}
    count = 0
    for _ in range(n):
        x, y = rng.choice(pool), rng.choice(pool)
        for env, daz, ftz in envs:
            for op in py:
                want = py[op](x, y, env)[0]
                got = _eval(z3.substitute(terms[(op, daz, ftz)], (a, BV(x)), (b, BV(y))))
                count += 1
                if got != want:
                    mism.append((op, daz, ftz, hex(x), hex(y), hex(got), hex(want)))
    for x in specials:                                  # every conversion boundary, deterministically
        for env, daz, ftz in envs:
            for op in ("cvt_rne", "cvtt"):
                want = py[op](x, 0, env)[0]
                got = _eval(z3.substitute(terms[(op, daz, ftz)], (a, BV(x)), (b, BV(0))))
                count += 1
                if got != want:
                    mism.append((op, daz, ftz, hex(x), "-", hex(got), hex(want)))
    differential.count = count
    return mism


# ---------------------------------------------------------------- rule probes

def prove(claim, timeout_s):
    s = z3.Solver()
    s.set("timeout", int(timeout_s * 1000))
    s.add(z3.Not(claim))
    t = time.perf_counter()
    r = s.check()
    dt = time.perf_counter() - t
    cex = None
    if r == z3.sat:
        m = s.model()
        cex = {str(d): hex(m[d].as_long()) for d in m.decls() if z3.is_bv_value(m[d])}
    return {"unsat": "PROVED", "sat": "COUNTEREXAMPLE", "unknown": "UNKNOWN(timeout)"}[str(r)], dt, cex


def probes(timeout_s=30):
    a, b, x, v = z3.BitVecs("a b x v", 32)
    add, mul = (lambda p, q: arith2("add", p, q)), (lambda p, q: arith2("mul", p, q))
    out = []
    # Labels use the RULES.md draft-2 names (v0 ids in brackets). COMM-ADD/COMM-MUL/SZ-ADD/POW2-DOUBLE
    # are object-level candidates (RULES.md §3.2). Unconditional commutation is FALSE (NaN payload order) ...
    out.append(("COMM-ADD [v0 R01] a+b == b+a (all bits, incl. NaN)", prove(add(a, b) == add(b, a), timeout_s)))
    # ... but holds for every non-NaN result, and NaN-ness is preserved (the NaN-order side condition).
    out.append(("COMM-ADD [v0 R01] same NaN-ness; equal non-NaN bits",
                prove(z3.And(is_nan(add(a, b)) == is_nan(add(b, a)),
                             z3.Implies(z3.Not(is_nan(add(a, b))), add(a, b) == add(b, a))), timeout_s)))
    out.append(("COMM-MUL [v0 R02] same NaN-ness; equal non-NaN bits",
                prove(z3.And(is_nan(mul(a, b)) == is_nan(mul(b, a)),
                             z3.Implies(z3.Not(is_nan(mul(a, b))), mul(a, b) == mul(b, a))), timeout_s)))
    out.append(("POW2-DOUBLE [v0 R07] x*2.0 == x+x (all bits)", prove(mul(x, BV(0x40000000)) == add(x, x), timeout_s)))
    out.append(("SZ-ADD [v0 R03] x+(-0.0) == x for non-NaN x", prove(z3.Implies(z3.Not(is_nan(x)), add(x, BV(0x80000000)) == x), timeout_s)))
    out.append(("SZ-ADD [v0 R03] for ALL x (expect SNaN cex)", prove(add(x, BV(0x80000000)) == x, timeout_s)))
    out.append(("never: x+(+0.0) == x for non-NaN x (expect -0 cex)",
                prove(z3.Implies(z3.Not(is_nan(x)), add(x, BV(0)) == x), timeout_s)))
    c127 = BV(0x42FE0000)
    meaning_hi = z3.If(z3.fpGT(fp(v), fp(c127)), c127, v)
    out.append(("R04 MIN-SEL-127 [v0 R17] for non-NaN v",
                prove(z3.Implies(z3.Not(is_nan(v)), meaning_hi == maxmin(False, v, c127)), timeout_s)))
    out.append(("never: MAXPS(a,b) == MAXPS(b,a) unconditionally (expect cex)",
                prove(maxmin(True, a, b) == maxmin(True, b, a), timeout_s)))
    nonneg = lambda t: z3.And(z3.Extract(31, 31, t) == 0, z3.Not(is_nan(t)))
    out.append(("R02/R03 fold lemma: MAXPS commutes, sign-0 non-NaN",
                prove(z3.Implies(z3.And(nonneg(a), nonneg(b)), maxmin(True, a, b) == maxmin(True, b, a)), timeout_s)))
    out.append(("R02/R03 fold lemma: MAXPS(NaN, m) == m", prove(z3.Implies(is_nan(a), maxmin(True, a, b) == b), timeout_s)))
    out.append(("R02/R03 fold lemma: sign-0 order == unsigned BV order",
                prove(z3.Implies(z3.And(nonneg(a), nonneg(b)), z3.fpGT(fp(a), fp(b)) == z3.UGT(a, b)), timeout_s)))
    M = BV(0x4B400000)                                    # 1.5 * 2^23
    in_range = z3.And(z3.Not(is_nan(v)), z3.fpLEQ(z3.fpAbs(fp(v)), z3.FPVal(127.0, F32)))
    rint = arith2("sub", arith2("add", v, M), M)
    out.append(("R19 RINT-MAGIC cvtt((v+M)-M) == cvt_rne(v), |v| <= 127",
                prove(z3.Implies(in_range, cvt_f2i(rint, z3.RTZ()) == cvt_f2i(v, RNE)), timeout_s)))
    # Added 2026-10-16 (review R1-7, R1-9, R1-13). Same RC on both sides of R19 RINT-MAGIC:
    for name, rm in (("RD", z3.RTN()), ("RU", z3.RTP()), ("RZ (expect cex: negative non-integers)", z3.RTZ())):
        rint_rm = arith2("sub", arith2("add", v, M, rm), M, rm)
        out.append(("R19 RINT-MAGIC under %s on both sides" % name,
                    prove(z3.Implies(in_range, cvt_f2i(rint_rm, z3.RTZ()) == cvt_f2i(v, rm)), timeout_s)))
    nonnan2 = z3.And(z3.Not(is_nan(a)), z3.Not(is_nan(b)))
    out.append(("never: MAXPS(a,b) == MAXPS(b,a) for non-NaN a, b (expect +-0 cex)",
                prove(z3.Implies(nonnan2, maxmin(True, a, b) == maxmin(True, b, a)), timeout_s)))
    sel_max = z3.If(z3.fpGT(fp(a), fp(b)), a, b)
    sel_min = z3.If(z3.fpLT(fp(a), fp(b)), a, b)
    out.append(("R01 SEL-MAX (a>b?a:b) == MAXPS(a,b), all bits", prove(sel_max == maxmin(True, a, b), timeout_s)))
    out.append(("SEL-MIN (not a row) (a<b?a:b) == MINPS(a,b)", prove(sel_min == maxmin(False, a, b), timeout_s)))
    cm127 = BV(0xC2FE0000)
    meaning_lo = z3.If(z3.fpLT(fp(v), fp(cm127)), cm127, v)
    out.append(("R05 MAX-SEL-M127 [v0 R18] for non-NaN v",
                prove(z3.Implies(z3.Not(is_nan(v)), meaning_lo == maxmin(True, v, cm127)), timeout_s)))
    out.append(("R04 with NaN v (expect cex: side condition needed)",
                prove(meaning_hi == maxmin(False, v, c127), timeout_s)))
    return out


if __name__ == "__main__":
    tmo = float(sys.argv[1]) if len(sys.argv) > 1 else 30
    print("z3", z3.get_version_string())
    t = time.perf_counter()
    mm = differential()
    print("differential SMT-term vs fp_ops: %d comparisons, %d mismatches (%.1f s)"
          % (differential.count, len(mm), time.perf_counter() - t))
    for m in mm[:10]:
        print("  MISMATCH", m)
    for name, (verdict, dt, cex) in probes(tmo):
        print("%-64s %-16s %6.2f s %s" % (name, verdict, dt, cex if cex else ""))
