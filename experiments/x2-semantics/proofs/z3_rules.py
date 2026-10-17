"""Z3 routes for the rules of RULES.md sec. 3.1 marked "not yet run" (rules.v1 draft 2), plus re-runs of
the proved FP rows for timing on the measuring machine. Every query asserts the NEGATION of the rule and
asks for unsat (PROVED); sat gives a counterexample; unknown/timeout is "not proved" (RULES.md sec. 1).

Encodings: ADD/SUB/MUL/MAX/MIN/CVT f32->i32 reuse semantics/smt_encoding.py (the bit-vector NaN layer around
the FPA core, checked against the Python reference by its differential). Revised 2026-10-16 after review
(findings R2-1, R2-2): the compare, (U)COMISS and VCVTPH2PS entries now come from proofs/smt_table.py, a
pure-BV transliteration of semantics/fp_ops.py checked by its own differential, instead of SMT-LIB's
fp.isNaN / fp.lt / fp.eq / fp.to_fp; R10 and R11 have no "generic" query any more (they were the
tautology t == t); the R08 and R09 generic queries remain as DEFINITIONAL lemmas about the transliterated
AND / BLENDVPS (no table entry) and do not count as table evidence; the R08-R11 instances use the table's
compare lane and, for R10/R11, the EVEX masking function of int_ops.masked; R06-R11 and R21 run under
DAZ = 0 and DAZ = 1 (RC and FTZ are not inputs of these entries); R20 compares Hearth's q_f16 with the
table's VCVTPH2PS without Z3's non-standard fp.to_ieee_bv, so cvc5 can replay it.

Integer rows are QF_BV over hand transliterations of the table's lane semantics (int_ops.py: PMADDUBSW
saturation, PMADDWD, VPDPBUSD wrapping, PABSB/PSIGNB, packs), tied to the table by
proofs/int_differential.py and the DIFF-* entries of x2prove.c, with the domain predicates of RULES.md
sec. 4.0 asserted where the rule's side condition names them. The monolithic R12-R14 queries model ONE row
with its per-row lane total; the lane maps of the reduction trees (red8, red_quads, red_quad1) are proved
separately by the T lemmas of z3_int.py.

  python -B z3_rules.py --sem-root DIR --out z3.json [--smt2-dir DIR] [--timeout 1200] [--only R02,R12]

--smt2-dir writes each query as SMT-LIB 2 (Z3's printer) for the second-solver route (second_solver.py).
"""
import argparse
import hashlib
import json
import os
import sys
import time


def build(sem_root):
    sys.path.insert(0, sem_root)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import z3
    from semantics import smt_encoding as se
    import smt_table as st
    BV = lambda v, n=32: z3.BitVecVal(v, n)
    fp, is_nan, maxmin, arith2, cvt_f2i = se.fp, se.is_nan, se.maxmin, se.arith2, se.cvt_f2i
    Q = {}

    # ---------------------------------------------------------------- FP rows
    def fold_chain(n_lanes, n_steps, hmax):
        xs = [z3.BitVec("x%d" % i, 32) for i in range(64)]
        vs = [x & BV(0x7FFFFFFF) for x in xs]                      # andnot(signmask, v) / _mm512_abs_ps
        m = BV(0)                                                  # amax = 0.0f
        for v in vs:                                               # meaning: if (a > amax) amax = a
            m = z3.If(z3.fpGT(fp(v), fp(m)), v, m)
        lanes = [BV(0)] * n_lanes                                  # m = setzero
        for k in range(n_steps):                                   # m = max(abs(v[k]), m): element = src1
            lanes = [maxmin(True, vs[n_lanes * k + c], lanes[c]) for c in range(n_lanes)]
        return hmax(lanes) == m, xs

    def hmax8(L):                       # quant_avx2.c hmax8: src1 = low half, src2 = high half
        b = [maxmin(True, L[j], L[j + 4]) for j in range(4)]
        b2 = [maxmin(True, b[0], b[2]), maxmin(True, b[1], b[3])]  # max_ps(b, movehl(b, b)) lanes 0, 1
        return maxmin(True, b2[0], b2[1])                          # max_ss(b, shuffle(b, b, 1))

    def hmax16(L):                      # quant_avx512.c hmax16
        return hmax8([maxmin(True, L[j], L[j + 8]) for j in range(8)])

    claim, _ = fold_chain(8, 8, hmax8)
    Q["R02"] = ("MAX-FOLD-8x8: sequential 64-step `if (|x_i| > m) m = |x_i|` from +0 == 8 lane chains of "
                "MAXPS(|v|, m) then hmax8, all 2^2048 inputs, DAZ = 0", claim)
    claim, _ = fold_chain(16, 4, hmax16)
    Q["R03"] = ("MAX-FOLD-16x4: as R02 with 16 lane chains of 4 and hmax16", claim)

    a, b, v = z3.BitVecs("a b v", 32)
    c = z3.Bool("c")
    ones, zero, canon = BV(0xFFFFFFFF), BV(0), BV(0x7FC00000)
    cmpmask = lambda cond: z3.If(cond, ones, zero)                 # VEX compare lane: all-ones or zero
    blendv = lambda x, y, m: z3.If(z3.Extract(31, 31, m) == 1, y, x)  # int_ops.blendvps lane (no table entry)
    ctab = st._cmp_table()
    for daz in (False, True):
        tag = "DAZ=1" if daz else "DAZ=0"
        D = z3.BoolVal(daz)
        unord = st.cmp_pred(3, v, v, D, ctab)                      # table: VCMPPS lane, predicate 3 (UNORD_Q)
        ordq = st.cmp_pred(7, v, v, D, ctab)                       # table: predicate 7 (ORD_Q)
        Q["R06/" + tag] = ("ISNAN-UNORD: table CMP(v, v, UNORD_Q) lane (smt_table.cmp_pred) == isnan(v), " + tag,
                           unord == is_nan(v))
        Q["R07/" + tag] = ("NOTNAN-ORD: table CMP(v, v, ORD_Q) lane == not isnan(v), " + tag, ordq == z3.Not(is_nan(v)))
        Q["R08/inst/" + tag] = ("ANDMASK-SELECT act_q8 instance: and(p, table CMP(p,p,ORD_Q) lane) == isnan(p) ? +0 : p, "
                                "AND transliterated, " + tag, (v & cmpmask(ordq)) == z3.If(is_nan(v), zero, v))
        Q["R09/inst/" + tag] = ("BLENDV-SELECT canon8 instance: blendv(v, 0x7FC00000, table CMP(v,v,UNORD_Q)) == "
                                "isnan(v) ? canon : v, BLENDVPS transliterated, " + tag,
                                blendv(v, canon, cmpmask(unord)) == z3.If(is_nan(v), canon, v))
        Q["R10/inst/" + tag] = ("MASKMOV-SELECT canon16 instance: k = table VCMPPS-into-k bit (UNORD_Q), merge-masked move "
                                "int_ops.masked(canon, v, k, z=0) == isnan(v) ? canon : v, " + tag,
                                st.masked_lane(unord, canon, v, False) == z3.If(is_nan(v), canon, v))
        Q["R11/inst/" + tag] = ("MASKZMOV-SELECT act_q8 instance: k = table VCMPPS-into-k bit (ORD_Q), zero-masked move "
                                "int_ops.masked(p, ., k, z=1) == isnan(p) ? +0 : p, " + tag,
                                st.masked_lane(ordq, v, a, True) == z3.If(is_nan(v), zero, v))
    Q["R08"] = ("DEFINITIONAL lemma (VANDPS/VPAND has no table entry; not table evidence): and(x, cmpmask(c)) == "
                "select(c, x, +0.0)", (a & cmpmask(c)) == z3.If(c, a, zero))
    Q["R09"] = ("DEFINITIONAL lemma (BLENDVPS has no table entry; not table evidence): blendv(a, b, cmpmask(c)) == "
                "select(c, b, a)", blendv(a, b, cmpmask(c)) == z3.If(c, b, a))

    # R01, R04, R05, R19 (proved in RULES.md on the laptop): re-run here for the record's timing
    c127, cm127 = BV(0x42FE0000), BV(0xC2FE0000)
    Q["R01"] = ("SEL-MAX: (a > b ? a : b) == MAXPS(a, b), all bits", z3.If(z3.fpGT(fp(a), fp(b)), a, b) == maxmin(True, a, b))
    Q["R04"] = ("MIN-SEL-127 for non-NaN v", z3.Implies(z3.Not(is_nan(v)),
                                                       z3.If(z3.fpGT(fp(v), fp(c127)), c127, v) == maxmin(False, v, c127)))
    Q["R05"] = ("MAX-SEL-M127 for non-NaN v", z3.Implies(z3.Not(is_nan(v)),
                                                         z3.If(z3.fpLT(fp(v), fp(cm127)), cm127, v) == maxmin(True, v, cm127)))
    # the same three rows with the C comparison as the TABLE's relation (smt_table.relation = fp_ops.relation, as
    # hearth_kernels._c_gt / _c_lt evaluate it) instead of SMT-LIB fp.gt / fp.lt (added 2026-10-16, cf. R2-2)
    GT4, LT4 = BV(4, 4), BV(1, 4)
    F0 = z3.BoolVal(False)
    Q["R01/table"] = ("SEL-MAX with the table relation: (rel(a, b) == GT ? a : b) == MAXPS(a, b), all bits, DAZ = 0",
                      z3.If(st.relation(a, b, F0) == GT4, a, b) == maxmin(True, a, b))
    Q["R04/table"] = ("MIN-SEL-127 with the table relation, non-NaN v, DAZ = 0",
                      z3.Implies(z3.Not(is_nan(v)), z3.If(st.relation(v, c127, F0) == GT4, c127, v) == maxmin(False, v, c127)))
    Q["R05/table"] = ("MAX-SEL-M127 with the table relation, non-NaN v, DAZ = 0",
                      z3.Implies(z3.Not(is_nan(v)), z3.If(st.relation(v, cm127, F0) == LT4, cm127, v) == maxmin(True, v, cm127)))
    M = BV(0x4B400000)
    in_range = z3.And(z3.Not(is_nan(v)), z3.fpLEQ(z3.fpAbs(fp(v)), z3.FPVal(127.0, z3.Float32())))
    Q["R19"] = ("RINT-MAGIC: cvtt((v+M)-M) == cvt_rne(v), |v| <= 127",
                z3.Implies(in_range, cvt_f2i(arith2("sub", arith2("add", v, M), M), z3.RTZ()) == cvt_f2i(v, z3.RNE())))
    nonneg = lambda t: z3.And(z3.Extract(31, 31, t) == 0, z3.Not(is_nan(t)))
    Q["R02-lemma-commute"] = ("fold lemma: MAXPS commutes on sign-0 non-NaN operands",
                              z3.Implies(z3.And(nonneg(a), nonneg(b)), maxmin(True, a, b) == maxmin(True, b, a)))
    Q["R02-lemma-nan"] = ("fold lemma: MAXPS(NaN, m) == m", z3.Implies(is_nan(a), maxmin(True, a, b) == b))
    Q["R02-lemma-order"] = ("fold lemma: sign-0 non-NaN FP order == unsigned BV order",
                            z3.Implies(z3.And(nonneg(a), nonneg(b)), z3.fpGT(fp(a), fp(b)) == z3.UGT(a, b)))

    # R20: Hearth q_f16 (quant.c) vs the table's VCVTPH2PS lane
    h = z3.BitVec("h", 16)
    sign = z3.Concat(z3.Extract(15, 15, h), BV(0, 31))
    e5 = z3.ZeroExt(27, z3.Extract(14, 10, h))
    m10 = z3.ZeroExt(22, z3.Extract(9, 0, h))
    f32 = z3.Float32()
    # (float)m * 2^-24 as the bits r of the FPA product: fp(r) = product (SMT-LIB structural '='; the product is
    # never NaN, so r is unique), which avoids Z3's non-standard fp.to_ieee_bv and lets cvc5 replay the query
    r16 = z3.BitVec("r", 32)
    prod = z3.fpMul(z3.RNE(), z3.fpToFP(z3.RNE(), m10, f32), z3.FPVal(2.0 ** -24, f32))
    qf16 = z3.If(e5 == 0x1F, sign | BV(0x7F800000) | (m10 << 13) | z3.If(m10 != 0, BV(0x00400000), BV(0)),
                 z3.If(e5 != 0, sign | ((e5 + 112) << 23) | (m10 << 13),
                       z3.If(m10 == 0, sign, sign | r16)))
    Q["R20"] = ("F16-WIDEN: Hearth q_f16(h) (integer code; (float)m * 2^-24 for subnormals, through FPA) == table "
                "VCVTPH2PS lane (smt_table.cvt_h2f, pure BV), all 2^16 h",
                z3.Implies(z3.fpBVToFP(r16, f32) == prod, qf16 == st.cvt_h2f(h)))
    # R21: C `v != v` through UCOMISS(v, v) (table: smt_table.comis): true iff ZF == 0 or PF == 1
    for daz in (False, True):
        zf, pf, _cf = st.comis(v, v, z3.BoolVal(daz))
        Q["R21/" + ("DAZ=1" if daz else "DAZ=0")] = (
            "ISNAN-UCOMI: (ZF == 0 or PF == 1) of the table's UCOMISS(v, v) == isnan(v), DAZ=%d" % daz,
            z3.Or(z3.Not(zf), pf) == is_nan(v))

    # ---------------------------------------------------------------- integer rows (QF_BV)
    import int_lanes
    F = int_lanes.make(z3)                     # the lane formulas int_differential.py checks against int_ops.py
    sext, zext, sat16, maddubs_word = F.sext, F.zext, F.sat16, F.word

    def act_domain(xs):                                           # DOM-ACT-Q: -127 <= x <= 127
        return z3.And(*[z3.And(x >= -127, x <= 127) for x in xs])

    def wide_sum(terms, n=48):
        s = z3.BitVecVal(0, n)
        for t in terms:
            s = s + t
        return s
    us = [z3.BitVec("u%d" % i, 8) for i in range(64)]
    xs = [z3.BitVec("xq%d" % i, 8) for i in range(64)]
    # R12: AVX-512 VNNI per row (hearth_kernels.isum_vnni): 4 x VPDPBUSD over 16-byte chunks, lane total
    accl = [BV(0)] * 4
    for ch in range(4):
        accl = [F.dpbusd_lane(accl[j], [us[16 * ch + 4 * j + t] for t in range(4)], [xs[16 * ch + 4 * j + t] for t in range(4)])
                for j in range(4)]
    total = accl[0] + accl[1] + accl[2] + accl[3]
    meaning = BV(0)
    for i in range(64):
        meaning = meaning + zext(us[i]) * sext(xs[i])
    wide = wide_sum([zext(us[i], 48) * sext(xs[i], 48) for i in range(64)])
    Q["R12"] = ("INT-DOT-VNNI, ONE ROW: 4 x VPDPBUSD + that row's lane total == sum_i u_i*x_i in index order (int32), "
                "and no int32 wrap (== the 48-bit sum) under DOM-ACT-Q; the red_quads / red_quad1 lane maps are the "
                "separate T lemmas of z3_int.py", z3.Implies(act_domain(xs), z3.And(total == meaning, sext(total, 48) == wide)))
    # R13: AVX2 Q4 (isum_q4_avx2 before the bias): maddubs(lo nibbles, x0) + maddubs(hi nibbles, x1) (VPADDW,
    # wrapping 16-bit), madd(., 1), red8 lane total == sum n_i x_i; n_i are the nibbles
    ns = [z3.BitVec("n%d" % i, 8) for i in range(64)]
    nib_dom = z3.And(*[z3.ULE(n, 15) for n in ns])
    words = []
    for w in range(16):
        lo = maddubs_word(ns[2 * w], ns[2 * w + 1], xs[2 * w], xs[2 * w + 1])
        hi = maddubs_word(ns[32 + 2 * w], ns[32 + 2 * w + 1], xs[32 + 2 * w], xs[32 + 2 * w + 1])
        words.append(z3.Extract(15, 0, lo) + z3.Extract(15, 0, hi))   # VPADDW wraps
    dws = [sext(words[2 * j]) + sext(words[2 * j + 1]) for j in range(8)]   # VPMADDWD with ones
    tot13 = dws[0]
    for j in range(1, 8):
        tot13 = tot13 + dws[j]
    mean13 = wide_sum([zext(ns[i], 48) * sext(xs[i], 48) for i in range(64)])
    Q["R13"] = ("INT-DOT-MADDUBS-Q4, ONE ROW: maddubs pairs, VPADDW low+high, madd(.,1), the row's lane total (red8's lane map: z3_int T lemma) == sum n_i x_i (no saturation, "
                "no VPADDW wrap, no int32 wrap) for n in [0,15], DOM-ACT-Q", z3.Implies(z3.And(nib_dom, act_domain(xs)),
                                                                                     sext(tot13, 48) == mean13))
    # R14: AVX2 Q8 sign trick (isum_q8_avx2)
    ws = [z3.BitVec("w%d" % i, 8) for i in range(64)]
    pabs, psign = F.pabs, F.psign
    dw14 = []
    for half in range(2):
        wd = [maddubs_word(pabs(ws[32 * half + 2 * i]), pabs(ws[32 * half + 2 * i + 1]),
                           psign(xs[32 * half + 2 * i], ws[32 * half + 2 * i]),
                           psign(xs[32 * half + 2 * i + 1], ws[32 * half + 2 * i + 1])) for i in range(16)]
        dw14.append([sext(z3.Extract(15, 0, wd[2 * j])) + sext(z3.Extract(15, 0, wd[2 * j + 1])) for j in range(8)])
    tot14 = BV(0)
    for j in range(8):
        tot14 = tot14 + (dw14[0][j] + dw14[1][j])
    mean14 = wide_sum([sext(ws[i], 48) * sext(xs[i], 48) for i in range(64)])
    Q["R14"] = ("INT-DOT-SIGNTRICK-Q8, ONE ROW: maddubs(PABSB(w), PSIGNB(x, w)), madd(.,1), the row's lane total (red8: z3_int T lemma) == sum w_i x_i for any w, "
                "under DOM-ACT-Q (x != -128); no saturation (32,512)", z3.Implies(act_domain(xs), sext(tot14, 48) == mean14))
    Q["R14/x=-128"] = ("R14 without DOM-ACT-Q (expect a counterexample: x = -128, w < 0)", sext(tot14, 48) == mean14)
    # R15, R16: bias identities under DOM-ACT-SUM (asum = sum x)
    asum = BV(0)
    for x in xs:
        asum = asum + sext(x)
    lhs15 = BV(0)
    rhs15 = BV(0)
    for i in range(64):
        lhs15 = lhs15 + (zext(ns[i]) - 8) * sext(xs[i])
        rhs15 = rhs15 + zext(ns[i]) * sext(xs[i])
    Q["R15"] = ("INT-BIAS-NIB: sum (n_i - 8) x_i == sum n_i x_i - 8*a.sum with a.sum = sum x_i (DOM-ACT-SUM), int32, "
                "and no int32 wrap", z3.Implies(z3.And(nib_dom, act_domain(xs)),
                                                 z3.And(lhs15 == rhs15 - 8 * asum,
                                                        sext(lhs15, 48) == wide_sum([(zext(ns[i], 48) - 8) * sext(xs[i], 48)
                                                                                     for i in range(64)]))))
    qs = ws
    lhs16, rhs16 = BV(0), BV(0)
    for i in range(64):
        lhs16 = lhs16 + sext(qs[i]) * sext(xs[i])
        rhs16 = rhs16 + zext(qs[i] ^ z3.BitVecVal(0x80, 8)) * sext(xs[i])
    Q["R16"] = ("INT-BIAS-XOR80: sum q_i x_i == sum u8(q_i xor 0x80) x_i - 128*a.sum (DOM-ACT-SUM), int32, no wrap",
                z3.Implies(act_domain(xs), z3.And(lhs16 == rhs16 - 128 * asum,
                                                  sext(lhs16, 48) == wide_sum([sext(qs[i], 48) * sext(xs[i], 48) for i in range(64)]))))
    q = z3.BitVec("q", 32)
    s8 = F.packs(q)
    Q["R17"] = ("INT-NARROW-PACKS: packsswb(packssdw(q)) == (int8_t)q for |q| <= 127",
                z3.Implies(z3.And(q >= -127, q <= 127), z3.Extract(7, 0, s8) == z3.Extract(7, 0, q)))
    # R18: act sum: AVX2 lane-parallel VPADDD over 8 vectors + hsum8_i32; AVX-512 over 4 vectors + hsum_i32
    qa = [z3.BitVec("qa%d" % i, 32) for i in range(64)]
    qdom = z3.And(*[z3.And(t >= -127, t <= 127) for t in qa])
    seq = BV(0)
    for t in qa:
        seq = seq + t
    wseq = wide_sum([sext(t, 48) for t in qa])
    s8l = [BV(0)] * 8
    for kk in range(8):
        s8l = [s8l[l] + qa[8 * kk + l] for l in range(8)]
    b4 = [s8l[j] + s8l[j + 4] for j in range(4)]                   # lo128 + hi128
    b4 = [b4[j] + b4[[2, 3, 0, 1][j]] for j in range(4)]           # + shuffle 0x4E
    b4 = [b4[j] + b4[[1, 0, 3, 2][j]] for j in range(4)]           # + shuffle 0xB1
    s16l = [BV(0)] * 16
    for kk in range(4):
        s16l = [s16l[l] + qa[16 * kk + l] for l in range(16)]
    a8 = [s16l[j] + s16l[j + 8] for j in range(8)]                 # lo256 + hi256
    c4 = [a8[j] + a8[j + 4] for j in range(4)]
    c4 = [c4[j] + c4[[2, 3, 0, 1][j]] for j in range(4)]
    c4 = [c4[j] + c4[[1, 0, 3, 2][j]] for j in range(4)]
    Q["R18"] = ("INT-SUM-ACT: AVX2 (8 x VPADDD + hsum8_i32) and AVX-512 (4 x VPADDD + hsum_i32) == sequential sum, "
                "no int32 wrap, |q| <= 127", z3.Implies(qdom, z3.And(b4[0] == seq, c4[0] == seq, sext(seq, 48) == wseq)))
    return z3, Q


def run(z3, name, what, claim, timeout_s, smt2_dir, export_only=False):
    s = z3.Solver()
    s.set("timeout", int(timeout_s * 1000))
    s.add(z3.Not(claim))
    blob = s.to_smt2()
    sha = hashlib.sha256(blob.encode()).hexdigest()
    if smt2_dir:
        with open(os.path.join(smt2_dir, name.replace("/", "_") + ".smt2"), "w", newline="\n") as f:
            f.write(blob)
    if export_only:
        return {"rule": name, "what": what, "z3": "NOT SOLVED (export only)", "seconds": 0.0, "query_sha256": sha,
                "counterexample": None, "reason_unknown": None}
    t = time.perf_counter()
    r = s.check()
    dt = time.perf_counter() - t
    cex = None
    if r == z3.sat:
        m = s.model()
        cex = {str(d): hex(m[d].as_long()) if z3.is_bv_value(m[d]) else str(m[d]) for d in m.decls()}
        cex = dict(list(sorted(cex.items()))[:12])
    verdict = {"unsat": "PROVED", "sat": "COUNTEREXAMPLE", "unknown": "UNKNOWN(timeout)"}[str(r)]
    return {"rule": name, "what": what, "z3": verdict, "seconds": round(dt, 3), "query_sha256": sha,
            "counterexample": cex, "reason_unknown": s.reason_unknown() if str(r) == "unknown" else None}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--smt2-dir")
    ap.add_argument("--timeout", type=float, default=1200)
    ap.add_argument("--only")
    ap.add_argument("--export-only", action="store_true", help="write the SMT-LIB 2 files and hashes, do not solve")
    a = ap.parse_args(argv)
    z3, Q = build(a.sem_root)
    if a.smt2_dir:
        os.makedirs(a.smt2_dir, exist_ok=True)
    res = {"z3_version": z3.get_version_string(), "timeout_s": a.timeout, "rules": []}
    for name, (what, claim) in Q.items():
        if a.only and name.split("/")[0] not in a.only.split(","):
            continue
        r = run(z3, name, what, claim, a.timeout, a.smt2_dir, a.export_only)
        res["rules"].append(r)
        print("%-20s %-18s %9.3f s  %s" % (name, r["z3"], r["seconds"], r["counterexample"] or ""), flush=True)
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
