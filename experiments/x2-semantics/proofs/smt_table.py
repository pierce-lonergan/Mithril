"""Table-level QF_BV encodings of the compare, (U)COMISS and VCVTPH2PS entries, for the rule queries of
z3_rules.py (added 2026-10-16 after the same-family, independent-context review, finding R2-2).

The first run's R06, R07, R08-R11 instance, R20 and R21 queries used SMT-LIB's own predicates (fp.isNaN,
fp.lt/fp.eq/fp.gt, fp.to_fp) in place of the table entries, so they proved properties of the IEEE definition,
not of the table's VCMPPS / UCOMISS / VCVTPH2PS. The terms here are transliterated from the table's Python
reference, `semantics/fp_ops.py` (relation(), cmp_pred() with its CMP_PREDICATES table, comis(),
cvt_f16_to_f32()) and `semantics/int_ops.py` (masked()), in pure bit-vector logic (no FPA, so cvc5 can replay
every query), and are checked against those functions by `differential()` before any query uses them:

  relation(a, b, daz)        fp_ops.relation: UN if either source is NaN, else DAZ flushes denormal sources
                             to signed zeros and the total order of _order_key decides LT / EQ / GT (+0 = -0)
  cmp_pred(imm, a, b, daz)   fp_ops.cmp_pred: (relation & CMP_PREDICATES[imm & 31].true_set) != 0
  comis(a, b, daz)           fp_ops.comis: (ZF, PF, CF) from the relation (UN 111, GT 000, LT 001, EQ 100)
  cvt_h2f(h)                 fp_ops.cvt_f16_to_f32 value bits (exact; DAZ and RC ignored by the entry)
  masked_lane(k, r, d, z)    int_ops.masked for one element: k ? r : (z ? 0 : d)

Flags are not encoded (no rule of RULES.md §3.1 observes them).

  python -B smt_table.py --sem-root DIR --out differential.json     (runs the differential and writes counts)
"""
import argparse
import json
import random
import sys
import time

import z3

BV = lambda v, n=32: z3.BitVecVal(v, n)
UN_, EQ_, LT_, GT_ = 8, 2, 1, 4


def is_nan(x):
    return z3.And(z3.Extract(30, 23, x) == 0xFF, z3.Extract(22, 0, x) != 0)


def is_denormal(x):
    return z3.And(z3.Extract(30, 23, x) == 0, z3.Extract(22, 0, x) != 0)


def daz_in(x, daz):
    """fp_ops._daz value: under DAZ a denormal becomes the zero of its sign."""
    return z3.If(z3.And(daz, is_denormal(x)), x & BV(0x80000000), x)


def order_key(x):
    """fp_ops._order_key for a non-NaN source as a signed 32-bit integer: the magnitude bits of a non-NaN binary32
    value (infinity included) are ordered like its magnitude, so key = sign ? -mag : mag orders every non-NaN
    value, with +0 and -0 both 0 (the tuple order of _order_key; checked by differential())."""
    mag = x & BV(0x7FFFFFFF)
    return z3.If(z3.Extract(31, 31, x) == 1, -mag, mag)


def relation(a, b, daz):
    """4-bit relation code of fp_ops.relation (LT 1, EQ 2, GT 4, UN 8)."""
    a2, b2 = daz_in(a, daz), daz_in(b, daz)
    ka, kb = order_key(a2), order_key(b2)
    return z3.If(z3.Or(is_nan(a), is_nan(b)), BV(UN_, 4),
                 z3.If(ka == kb, BV(EQ_, 4), z3.If(ka < kb, BV(LT_, 4), BV(GT_, 4))))


def _cmp_table():
    from semantics import fp_ops
    return [t for _, t, _ in fp_ops.CMP_PREDICATES]


def cmp_pred(imm, a, b, daz, table=None):
    """One lane of (V)CMPPS / (V)CMPSS / VCMPPS into k: a Bool."""
    true_set = (table or _cmp_table())[imm & 31]
    return (relation(a, b, daz) & BV(true_set, 4)) != BV(0, 4)


def comis(a, b, daz):
    """(U)COMISS: (ZF, PF, CF) as Bools (OF = SF = AF = 0 in the table)."""
    r = relation(a, b, daz)
    un, lt, eq = r == BV(UN_, 4), r == BV(LT_, 4), r == BV(EQ_, 4)
    return z3.Or(un, eq), un, z3.Or(un, lt)


def cvt_h2f(h):
    """VCVTPH2PS lane (fp_ops.cvt_f16_to_f32): binary16 h (BitVec 16) -> binary32 bits (BitVec 32)."""
    sign = z3.Concat(z3.Extract(15, 15, h), BV(0, 31))
    e = z3.Extract(14, 10, h)
    m = z3.ZeroExt(22, z3.Extract(9, 0, h))
    e32 = z3.ZeroExt(27, e)
    nan = z3.And(e == 0x1F, m != 0)
    inf = z3.And(e == 0x1F, m == 0)
    normal = sign | ((e32 + 112) << 23) | (m << 13)
    # subnormal h: value m * 2^-24; with the highest set bit of m at position p (0..9) the binary32 result has
    # exponent p - 24 (biased p + 103) and fraction (m << (23 - p)) without the leading one. Bits 9..p of m
    # equal 1 exactly when p is that position, so at most one case matches.
    subn = sign
    for p in range(0, 10):
        top = z3.Extract(9, p, z3.Extract(9, 0, h))
        subn = z3.If(top == 1, sign | (BV(p + 103) << 23) | ((m << (23 - p)) & BV(0x7FFFFF)), subn)
    return z3.If(nan, sign | BV(0x7F800000) | (m << 13) | BV(0x00400000),
                 z3.If(inf, sign | BV(0x7F800000),
                       z3.If(e == 0, z3.If(m == 0, sign, subn), normal)))


def masked_lane(k, r, d, z):
    """int_ops.masked, one element: k ? r : (z ? 0 : d) (z a Python bool: the variant is fixed per query)."""
    return z3.If(k, r, BV(0) if z else d)


# ------------------------------------------------------------------ differential against the reference

def _ev(term):
    return z3.simplify(term).as_long()


def differential(sem_root, n_random=40, seed=11):
    sys.path.insert(0, sem_root)
    from semantics import fp_ops, int_ops
    from semantics.fpenv import Env
    rng = random.Random(seed)
    specials = [0, 0x80000000, 0x7F800000, 0xFF800000, 0x7FC00000, 0xFFC00000, 0x7FC00001, 0xFFC12345, 0x7F800001,
                0xFF812345, 0x7FBFFFFF, 0x00000001, 0x80000001, 0x80000003, 0x007FFFFF, 0x807FFFFF, 0x00800000,
                0x80800000, 0x00800001, 0x3F800000, 0xBF800000, 0x3F800001, 0x7F7FFFFF, 0xFF7FFFFF, 0x42FE0000,
                0xC2FE0000, 0x4B400000, 0x3F7FFFFF]
    pool = specials + [rng.getrandbits(32) for _ in range(n_random)]
    envs = [("default", Env.make()), ("DAZ", Env.make(daz=True)), ("FTZ", Env.make(ftz=True)),
            ("DAZ+FTZ", Env.make(daz=True, ftz=True)), ("RD", Env.make(rc=1)), ("RZ+DAZ", Env.make(rc=3, daz=True))]
    table = [t for _, t, _ in fp_ops.CMP_PREDICATES]
    a, b = z3.BitVecs("a b", 32)
    h = z3.BitVec("h", 16)
    t0 = time.perf_counter()
    mism, count = [], {"cmp_pred": 0, "comis": 0, "cvt_h2f": 0, "masked_lane": 0}
    for daz in (False, True):
        D = z3.BoolVal(daz)
        cmp_vec = z3.Concat(*[z3.If(cmp_pred(i, a, b, D, table), BV(1, 1), BV(0, 1)) for i in range(31, -1, -1)])
        zf, pf, cf = comis(a, b, D)
        com_vec = z3.Concat(z3.If(zf, BV(1, 1), BV(0, 1)), z3.If(pf, BV(1, 1), BV(0, 1)), z3.If(cf, BV(1, 1), BV(0, 1)))
        for x in pool:
            for y in pool:
                sub = [(a, BV(x)), (b, BV(y))]
                got_c = _ev(z3.substitute(cmp_vec, *sub))
                got_m = _ev(z3.substitute(com_vec, *sub))
                for en, env in envs:
                    if env.daz != daz:
                        continue
                    for imm in range(32):
                        want = 1 if fp_ops.cmp_pred(x, y, imm, env)[0] else 0
                        count["cmp_pred"] += 1
                        if ((got_c >> imm) & 1) != want:
                            mism.append(("cmp_pred", imm, en, hex(x), hex(y), (got_c >> imm) & 1, want))
                    for sig in (False, True):
                        z_, p_, c_ = fp_ops.comis(x, y, env, sig)[0]
                        count["comis"] += 1
                        if got_m != (z_ << 2 | p_ << 1 | c_):
                            mism.append(("comis", sig, en, hex(x), hex(y), got_m, (z_, p_, c_)))
    h2f = cvt_h2f(h)
    for hv in range(1 << 16):
        got = _ev(z3.substitute(h2f, (h, BV(hv, 16))))
        for en, env in envs:
            count["cvt_h2f"] += 1
            want = fp_ops.cvt_f16_to_f32(hv, env)[0]
            if got != want:
                mism.append(("cvt_h2f", en, hex(hv), hex(got), hex(want)))
    k = z3.Bool("k")
    r_, d_ = z3.BitVecs("r d", 32)
    for _ in range(200):
        kk, rr, dd = rng.getrandbits(16), rng.getrandbits(512), rng.getrandbits(512)
        for zz in (False, True):
            want = int_ops.masked(rr, dd, kk, zz, 512, 32)
            for i in range(16):
                lane = _ev(z3.substitute(masked_lane(k, r_, d_, zz), (k, z3.BoolVal(bool((kk >> i) & 1))),
                                         (r_, BV((rr >> (32 * i)) & 0xFFFFFFFF)), (d_, BV((dd >> (32 * i)) & 0xFFFFFFFF))))
                count["masked_lane"] += 1
                if lane != (want >> (32 * i)) & 0xFFFFFFFF:
                    mism.append(("masked_lane", zz, i, hex(kk), hex(lane)))
    return {"pool_values": len(pool), "pairs": len(pool) ** 2, "envs": [e for e, _ in envs], "comparisons": count,
            "total_comparisons": sum(count.values()), "mismatches": len(mism), "mismatch_list": mism[:50],
            "seconds": round(time.perf_counter() - t0, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = differential(a.sem_root)
    res["z3_version"] = z3.get_version_string()
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "mismatch_list"}))
    return 0 if res["mismatches"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
