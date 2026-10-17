"""Decomposed Z3 QF_BV routes for the integer rows R12-R16 and R18. The monolithic 64-element queries of
z3_rules.py ask Z3 to rediscover interval facts through bit-blasted adders and multipliers, and R13 timed
out there. Here each row is split into parts that bit-blast cheaply; their composition is the T2-style
argument of RULES.md sec. 4:

  P  lane lemma     : one output lane of the (hand-transliterated) table semantics (a VPMADDUBSW word with its
                      saturation, with PABSB/PSIGNB inputs for R14, or one bias element) equals the exact integer
                      value of its products and lies within the bound, for all inputs in the declared domains.
                      R12/P is a BOUND lemma only (|u*x| <= 32,385): the VPDPBUSD lane IS acc + the products by
                      the table's definition, and the formula's agreement with the table lane is the DIFF-DPBUSD
                      entry of x2prove.c (revised 2026-10-16: the first R12/P also asserted a reassociation of
                      itself, which says nothing about the table);
  W  narrow-add lemma (R13): VPADDW of two words within +-3,810 does not wrap, so the sign extension of the
                      16-bit sum is the sum of the sign extensions;
  M  order lemma    : over FREE 32-bit leaves, ONE ROW's reduction (lane-parallel adds, VPMADDWD with ones, the
                      4 chunked VPDPBUSD accumulations) equals the meaning's sequential sum modulo 2^32; the row's
                      partials are then summed by the tree;
  T  tree lemma     : over free 32-bit leaves, the real reduction trees of Hearth (trees.py: red8 with VPHADDD per
                      128-bit lane, VPERM2I128 0x20/0x31 and VPADDD; red_quads with VPUNPCKL/HDQ and L/HQDQ;
                      red_quad1 with VPSHUFD 0x4E/0xB1 and VPERMD) put exactly the sum of row i's partials into
                      lane i, modulo 2^32 (added 2026-10-16, finding R2-3: the first run's M lemmas replaced the
                      trees by a flat sum, and its docstring claimed they covered them);
  bound [D]         : the exact meaning lies in int32 (64 x the product bound is far below 2^31; RULES.md
                      sec. 4.1-4.3).

Composition: by P (and W) every leaf of the realization equals the exact value of its products; by M each
row's partials sum to the row's meaning modulo 2^32; by T the tree delivers that sum to the row's lane; the
exact meaning lies in [-2^31, 2^31), so the realization's int32 value is the exact meaning. P, W, M and T are
machine-checked here; the bound is arithmetic. The lane-function formulas are tied to the table by
proofs/int_differential.py and the DIFF-* entries of x2prove.c; the tree transliterations by trees.py.

  python -B z3_int.py --sem-root DIR --out int.json [--timeout 1200] [--smt2-dir DIR] [--only R14/P,T/red8]
"""
import argparse
import hashlib
import json
import os
import sys
import time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=1200)
    ap.add_argument("--smt2-dir", help="also write each query as SMT-LIB 2 (for second_solver.py)")
    ap.add_argument("--only", help="comma list of query names")
    ap.add_argument("--export-only", action="store_true", help="write the SMT-LIB 2 files and hashes, do not solve")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.sem_root)
    import z3
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import int_lanes
    F = int_lanes.make(z3)                     # the lane formulas int_differential.py checks against int_ops.py
    BV = lambda v, n=32: z3.BitVecVal(v, n)
    sext, zext, sat16, word, pabs, psign = F.sext, F.zext, F.sat16, F.word, F.pabs, F.psign
    in8 = lambda x, lo, hi: z3.And(x >= lo, x <= hi)
    leaves = lambda name, k: [z3.BitVec("%s%d" % (name, i), 32) for i in range(k)]

    def ssum(ts):
        s = BV(0)
        for t in ts:
            s = s + t
        return s
    Q = {}
    n0, n1, x0, x1, w0, w1 = z3.BitVecs("n0 n1 x0 x1 w0 w1", 8)
    # ---------------- R13: Q4 maddubs (quant_avx2.c qtile8, isum_q4_avx2 before the bias)
    w = word(n0, n1, x0, x1)
    Q["R13/P"] = ("one VPMADDUBSW word on nibbles n in [0,15], x in [-127,127]: == n0*x0 + n1*x1, |.| <= 3,810 (no saturation)",
                  z3.Implies(z3.And(z3.ULE(n0, 15), z3.ULE(n1, 15), in8(x0, -127, 127), in8(x1, -127, 127)),
                             z3.And(w == zext(n0) * sext(x0) + zext(n1) * sext(x1), w <= 3810, w >= -3810)))
    lo16, hi16 = z3.BitVecs("lo16 hi16", 16)
    Q["R13/W"] = ("VPADDW of two words in [-3810, 3810] does not wrap: sext(lo + hi) == sext(lo) + sext(hi)",
                  z3.Implies(z3.And(lo16 >= -3810, lo16 <= 3810, hi16 >= -3810, hi16 <= 3810),
                             sext(lo16 + hi16) == sext(lo16) + sext(hi16)))
    L, H = leaves("l", 16), leaves("h", 16)            # sext'd lo-nibble and hi-nibble pair words
    dws = [(L[2 * j] + H[2 * j]) + (L[2 * j + 1] + H[2 * j + 1]) for j in range(8)]  # VPADDW then VPMADDWD(., 1)
    Q["R13/M"] = ("red8 lane total of VPMADDWD(VPADDW(lo, hi), 1) == the index-order sum of the pair values, mod 2^32",
                  ssum(dws) == ssum(L) + ssum(H))
    # ---------------- R14: Q8 sign trick (isum_q8_avx2)
    ws = word(pabs(w0), pabs(w1), psign(x0, w0), psign(x1, w1))
    ex14 = sext(w0) * sext(x0) + sext(w1) * sext(x1)
    Q["R14/P"] = ("one VPMADDUBSW(PABSB(w), PSIGNB(x, w)) word == w0*x0 + w1*x1, |.| <= 32,512, any w, x in [-127,127]",
                  z3.Implies(z3.And(in8(x0, -127, 127), in8(x1, -127, 127)),
                             z3.And(ws == ex14, ws <= 32512, ws >= -32512)))
    Q["R14/P x=-128"] = ("R14/P without DOM-ACT-Q (expect a counterexample: x = -128, w < 0)", ws == ex14)
    P0, P1 = leaves("a", 16), leaves("b", 16)          # words of the two 32-byte halves
    d14 = [(P0[2 * j] + P0[2 * j + 1]) + (P1[2 * j] + P1[2 * j + 1]) for j in range(8)]  # madd(., 1) per half, VPADDD
    Q["R14/M"] = ("red8 of VPADDD(VPMADDWD(p0, 1), VPMADDWD(p1, 1)) == index-order sum of the 32 words, mod 2^32",
                  ssum(d14) == ssum(P0) + ssum(P1))
    # ---------------- R12: AVX-512 VNNI (isum_vnni: 4 x VPDPBUSD over 16-byte chunks, lane total)
    u = z3.BitVecs("u0 u1 u2 u3", 8)
    y = z3.BitVecs("y0 y1 y2 y3", 8)
    acc = z3.BitVec("acc", 32)
    prods = [zext(u[t]) * sext(y[t]) for t in range(4)]
    Q["R12/P"] = ("BOUND lemma: each VPDPBUSD product zext(u)*sext(x) has |u*x| <= 32,385 under DOM-ACT-Q (the lane is "
                  "acc + the products by the table's definition; formula vs table lane: x2prove DIFF-DPBUSD)",
                  z3.Implies(z3.And(*[in8(t, -127, 127) for t in y]),
                             z3.And(*[z3.And(p <= 32385, p >= -32385) for p in prods])))
    del acc
    T = [[leaves("t%d_" % c, 4)[j] for j in range(4)] for c in range(4)]   # T[c][j]: 4-product sum, chunk c, lane j
    accl = [BV(0)] * 4
    for c in range(4):
        accl = [accl[j] + T[c][j] for j in range(4)]
    seq12 = ssum([T[c][j] for c in range(4) for j in range(4)])
    Q["R12/M"] = ("4 chunked VPDPBUSD accumulations + lane total == index-order sum of the 16 four-product sums, mod 2^32",
                  ssum(accl) == seq12)
    # ---------------- R15 / R16: bias identities (DOM-ACT-SUM: a.sum = sum x_i)
    n, x, q = z3.BitVecs("n x q", 8)
    Q["R15/P"] = ("(n - 8)*x == n*x - 8*x and |n*x| <= 1,905 for n in [0,15], x in [-127,127]",
                  z3.Implies(z3.And(z3.ULE(n, 15), in8(x, -127, 127)),
                             z3.And((zext(n) - 8) * sext(x) == zext(n) * sext(x) - 8 * sext(x),
                                    zext(n) * sext(x) <= 1905, zext(n) * sext(x) >= -1905)))
    NX, X = leaves("nx", 64), leaves("x", 64)
    Q["R15/M"] = ("sum (nx_i - 8 x_i) == sum nx_i - 8 * sum x_i, mod 2^32 (the bias rewriting with a.sum = sum x_i)",
                  ssum([NX[i] - 8 * X[i] for i in range(64)]) == ssum(NX) - 8 * ssum(X))
    Q["R16/P"] = ("u8(q xor 0x80) == q + 128 and q*x == u8(q xor 0x80)*x - 128*x, |u8*x| <= 32,385, x in [-127,127]",
                  z3.Implies(in8(x, -127, 127),
                             z3.And(zext(q ^ BV(0x80, 8)) == sext(q) + 128,
                                    sext(q) * sext(x) == zext(q ^ BV(0x80, 8)) * sext(x) - 128 * sext(x),
                                    zext(q ^ BV(0x80, 8)) * sext(x) <= 32385, zext(q ^ BV(0x80, 8)) * sext(x) >= -32385)))
    UX = leaves("ux", 64)
    Q["R16/M"] = ("sum (ux_i - 128 x_i) == sum ux_i - 128 * sum x_i, mod 2^32",
                  ssum([UX[i] - 128 * X[i] for i in range(64)]) == ssum(UX) - 128 * ssum(X))
    # ---------------- R18: act sum (AVX2 8 x VPADDD + hsum8_i32; AVX-512 4 x VPADDD + hsum_i32)
    QA = leaves("qa", 64)
    s8l = [ssum([QA[8 * k + l] for k in range(8)]) for l in range(8)]
    b4 = [s8l[j] + s8l[j + 4] for j in range(4)]
    b4 = [b4[j] + b4[[2, 3, 0, 1][j]] for j in range(4)]
    b4 = [b4[j] + b4[[1, 0, 3, 2][j]] for j in range(4)]
    s16l = [ssum([QA[16 * k + l] for k in range(4)]) for l in range(16)]
    a8 = [s16l[j] + s16l[j + 8] for j in range(8)]
    c4 = [a8[j] + a8[j + 4] for j in range(4)]
    c4 = [c4[j] + c4[[2, 3, 0, 1][j]] for j in range(4)]
    c4 = [c4[j] + c4[[1, 0, 3, 2][j]] for j in range(4)]
    Q["R18/M"] = ("AVX2 and AVX-512 act sums (lane-parallel VPADDD, then the shuffle trees) == sequential sum, mod 2^32",
                  z3.And(b4[0] == ssum(QA), c4[0] == ssum(QA)))
    # ---------------- T: the reduction trees of R12-R14 (trees.py; finding R2-3)
    import trees
    Q.update(trees.lemmas(z3))
    res = {"z3_version": z3.get_version_string(), "timeout_s": a.timeout, "results": []}
    for name, (what, claim) in Q.items():
        if a.only and name not in a.only.split(","):
            continue
        s = z3.Solver()
        s.set("timeout", int(a.timeout * 1000))
        s.add(z3.Not(claim))
        blob = s.to_smt2()
        if a.smt2_dir:
            os.makedirs(a.smt2_dir, exist_ok=True)
            with open(os.path.join(a.smt2_dir, "int_" + name.replace("/", "_").replace(" ", "_").replace("=", "") + ".smt2"),
                      "w", newline="\n") as f:
                f.write(blob)
        if a.export_only:
            res["results"].append({"name": name, "what": what, "verdict": "NOT SOLVED (export only)",
                                   "query_sha256": hashlib.sha256(blob.encode()).hexdigest()})
            print("%-16s exported %s" % (name, res["results"][-1]["query_sha256"]), flush=True)
            with open(a.out, "w") as f:
                json.dump(res, f, indent=1)
            continue
        t = time.perf_counter()
        r = s.check()
        dt = time.perf_counter() - t
        cex = None
        if r == z3.sat:
            m = s.model()
            cex = {str(d): hex(m[d].as_long()) for d in m.decls() if z3.is_bv_value(m[d])}
        v = {"unsat": "PROVED", "sat": "COUNTEREXAMPLE", "unknown": "UNKNOWN(timeout)"}[str(r)]
        res["results"].append({"name": name, "what": what, "verdict": v, "seconds": round(dt, 3), "counterexample": cex,
                               "query_sha256": hashlib.sha256(blob.encode()).hexdigest()})
        print("%-16s %-18s %9.3f s %s" % (name, v, dt, cex or ""), flush=True)
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
