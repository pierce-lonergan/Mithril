"""The integer reduction trees of Hearth b5d3f14 that rows R12-R14 name, as lane-list transliterations, the T
lemmas built from them, and two checks that tie them to the table (added 2026-10-16 after review finding R2-3).

  red8(s[0..7])          quant_avx2.c:71-76    6 x VPHADDD, 2 x VPERM2I128 (0x20, 0x31), VPADDD -> lane i = total of row i
  red_quads(v0..v3)      quant_avx512.c:64-69  VPUNPCKLDQ/HDQ, VPADDD, VPUNPCKLQDQ/HQDQ, VPADDD -> lane 4k+j = total of
                                               quad j's 128-bit lane k
  red_quad1(v)           quant_avx512.c:71-76  VPSHUFD 0x4E, VPADDD, VPSHUFD 0xB1, VPADDD, VPERMD (0,4,8,12 x4), low 128
                                               -> lane k = total of v's 128-bit lane k

The functions below work on lists of 32-bit lanes whose elements are either Python ints (wrapping adds mod
2^32) or z3 bit-vector terms (bvadd), so the SAME code builds the T lemmas (z3_int.py) and is executed
concretely by the checks here:

  differential(sem_root)  random inputs: these transliterations == semantics/hearth_kernels.py red8 / red_quads /
                          red_quad1, which compose the table's VPHADDD entry and int_ops data movement;
  unit_basis(sem_root)    the table compositions on every unit vector: the lane map they compute is exactly the
                          row-indicator map. Every operation in the trees is a lane move or a wrapping add, so each
                          output lane is a Z/2^32-linear function of the input lanes, and its values on the unit
                          vectors determine it: this is a second, solver-free route to the T lemmas.

  python -B trees.py --sem-root DIR --out trees.json
"""
import argparse
import json
import random
import sys
import time

M32 = 0xFFFFFFFF


def _add(x, y):
    if isinstance(x, int) and isinstance(y, int):
        return (x + y) & M32
    return x + y


def padd(a, b):
    return [_add(x, y) for x, y in zip(a, b)]


def phaddd(a, b):
    """VPHADDD per 128-bit lane L (int_ops.phaddd): [a0+a1, a2+a3, b0+b1, b2+b3]."""
    out = []
    for L in range(len(a) // 4):
        x, y = a[4 * L:4 * L + 4], b[4 * L:4 * L + 4]
        out += [_add(x[0], x[1]), _add(x[2], x[3]), _add(y[0], y[1]), _add(y[2], y[3])]
    return out


def perm2i128(a, b, imm):
    """VPERM2I128 on 8-lane lists (int_ops.perm2i128); the zeroing bits 3 and 7 are not used by red8."""
    assert not imm & 0x88
    src = [a[0:4], a[4:8], b[0:4], b[4:8]]
    return list(src[imm & 3]) + list(src[(imm >> 4) & 3])


def red8(s):
    h01, h23, h45, h67 = phaddd(s[0], s[1]), phaddd(s[2], s[3]), phaddd(s[4], s[5]), phaddd(s[6], s[7])
    a, b = phaddd(h01, h23), phaddd(h45, h67)
    return padd(perm2i128(a, b, 0x20), perm2i128(a, b, 0x31))


def unpck(a, b, eb, hi):
    """VPUNPCK{L,H}{DQ,QDQ} per 128-bit lane (int_ops.unpcklo / unpckhi) on 32-bit lane lists."""
    w = eb // 32                         # 32-bit lanes per element
    n = 128 // eb                        # elements per 128-bit lane
    out = []
    for L in range(len(a) // 4):
        base = 4 * L + (n // 2) * w * (1 if hi else 0)
        for i in range(n // 2):
            out += a[base + w * i: base + w * i + w]
            out += b[base + w * i: base + w * i + w]
    return out


def red_quads(v0, v1, v2, v3):
    s01 = padd(unpck(v0, v1, 32, False), unpck(v0, v1, 32, True))
    s23 = padd(unpck(v2, v3, 32, False), unpck(v2, v3, 32, True))
    return padd(unpck(s01, s23, 64, False), unpck(s01, s23, 64, True))


def pshufd(a, imm):
    out = []
    for L in range(len(a) // 4):
        out += [a[4 * L + ((imm >> (2 * j)) & 3)] for j in range(4)]
    return out


def permd(table, idx):
    return [table[i % len(table)] for i in idx]


def red_quad1(v):
    idx = [0, 4, 8, 12] * 4
    v = padd(v, pshufd(v, 0x4E))
    v = padd(v, pshufd(v, 0xB1))
    return permd(v, idx)[0:4]


# ------------------------------------------------------------------ the T lemmas (z3)

def lemmas(z3):
    """{name: (description, claim)} over free 32-bit leaves."""
    leaves = lambda nm, k: [z3.BitVec("%s%d" % (nm, i), 32) for i in range(k)]

    def ssum(ts):
        s = z3.BitVecVal(0, 32)
        for t in ts:
            s = s + t
        return s
    S = [leaves("s%d_" % i, 8) for i in range(8)]
    out8 = red8(S)
    V = [leaves("v%d_" % j, 16) for j in range(4)]
    outq = red_quads(*V)
    W = leaves("w", 16)
    out1 = red_quad1(W)
    return {
        "T/red8": ("red8 (6 x VPHADDD per-128-bit-lane, VPERM2I128 0x20/0x31, VPADDD) over 8 rows x 8 free int32 partials: "
                   "lane i == the sum of row i's 8 partials, mod 2^32 (R13, R14)",
                   z3.And(*[out8[i] == ssum(S[i]) for i in range(8)])),
        "T/red_quads": ("red_quads (VPUNPCKLDQ/HDQ, VPADDD, VPUNPCKLQDQ/HQDQ, VPADDD) over 4 quads x 16 free int32 lanes: "
                        "lane 4k+j == the sum of quad j's 128-bit lane k, mod 2^32 (R12)",
                        z3.And(*[outq[4 * k + j] == ssum(V[j][4 * k:4 * k + 4]) for k in range(4) for j in range(4)])),
        "T/red_quad1": ("red_quad1 (VPSHUFD 0x4E, VPADDD, VPSHUFD 0xB1, VPADDD, VPERMD 0,4,8,12) over 16 free int32 lanes: "
                        "lane k == the sum of 128-bit lane k, mod 2^32 (R12 tail)",
                        z3.And(*[out1[k] == ssum(W[4 * k:4 * k + 4]) for k in range(4)])),
    }


# ------------------------------------------------------------------ checks against the table compositions

def _hk(sem_root):
    sys.path.insert(0, sem_root)
    from semantics import hearth_kernels as hk
    from semantics.vec import lanes, pack
    return hk, lanes, pack


def differential(sem_root, n=2000, seed=5):
    hk, lanes, pack = _hk(sem_root)
    rng = random.Random(seed)
    mism, count = [], 0
    for _ in range(n):
        s = [rng.getrandbits(256) for _ in range(8)]
        if hk.red8(s) != pack(red8([lanes(x, 32, 8) for x in s]), 32):
            mism.append(("red8", [hex(x) for x in s]))
        v = [rng.getrandbits(512) for _ in range(4)]
        if hk.red_quads(*v) != pack(red_quads(*[lanes(x, 32, 16) for x in v]), 32):
            mism.append(("red_quads", [hex(x) for x in v]))
        w = rng.getrandbits(512)
        if hk.red_quad1(w) != pack(red_quad1(lanes(w, 32, 16)), 32):
            mism.append(("red_quad1", hex(w)))
        count += 3
    return {"random_inputs_per_tree": n, "comparisons": count, "mismatches": len(mism), "mismatch_list": mism[:10]}


def unit_basis(sem_root):
    """Evaluate the table compositions on every unit vector (one input lane = 1) and compare the resulting
    0/1 matrix with the row-indicator map."""
    hk, lanes, pack = _hk(sem_root)
    bad = []
    # red8: input (row i, partial j) -> output lane i only
    for i in range(8):
        for j in range(8):
            s = [0] * 8
            s[i] = 1 << (32 * j)
            out = lanes(hk.red8(s), 32, 8)
            if out != [1 if l == i else 0 for l in range(8)]:
                bad.append(("red8", i, j, out))
    # red_quads: input (quad j, lane 4k+t) -> output lane 4k+j only
    for j in range(4):
        for ln in range(16):
            v = [0] * 4
            v[j] = 1 << (32 * ln)
            out = lanes(hk.red_quads(*v), 32, 16)
            k = ln // 4
            if out != [1 if l == 4 * k + j else 0 for l in range(16)]:
                bad.append(("red_quads", j, ln, out))
    # red_quad1: input lane 4k+t -> output lane k only
    for ln in range(16):
        out = lanes(hk.red_quad1(1 << (32 * ln)), 32, 4)
        if out != [1 if l == ln // 4 else 0 for l in range(4)]:
            bad.append(("red_quad1", ln, out))
    return {"unit_vectors": 64 + 64 + 16, "mismatches": len(bad), "mismatch_list": bad[:10],
            "linearity": "every operation of the three trees is a lane move (VPHADDD pairing, VPERM2I128, "
                         "VPUNPCK*, VPSHUFD, VPERMD) or a wrapping 32-bit add, so each output lane is a "
                         "Z/2^32-linear form in the input lanes and the unit vectors determine it"}


def negative_controls():
    """Each T lemma with its lane map perturbed (lanes 0 and 1 of the claimed map swapped) must be refuted by
    Z3 (sat), which shows the T lemmas are not vacuous."""
    import z3
    leaves = lambda nm, k: [z3.BitVec("%s%d" % (nm, i), 32) for i in range(k)]

    def ssum(ts):
        s = z3.BitVecVal(0, 32)
        for t in ts:
            s = s + t
        return s
    S = [leaves("s%d_" % i, 8) for i in range(8)]
    out8 = red8(S)
    V = [leaves("v%d_" % j, 16) for j in range(4)]
    outq = red_quads(*V)
    W = leaves("w", 16)
    out1 = red_quad1(W)
    sw = lambda i: {0: 1, 1: 0}.get(i, i)
    wrong = {"T/red8": z3.And(*[out8[i] == ssum(S[sw(i)]) for i in range(8)]),
             "T/red_quads": z3.And(*[outq[4 * k + j] == ssum(V[sw(j)][4 * k:4 * k + 4]) for k in range(4) for j in range(4)]),
             "T/red_quad1": z3.And(*[out1[k] == ssum(W[4 * sw(k):4 * sw(k) + 4]) for k in range(4)])}
    res = {}
    for name, claim in wrong.items():
        s = z3.Solver()
        s.set("timeout", 60000)
        s.add(z3.Not(claim))
        res[name + " (lanes 0/1 swapped)"] = {"sat": "REFUTED (as required)", "unsat": "PROVED (control FAILED)",
                                              "unknown": "UNKNOWN"}[str(s.check())]
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    t = time.perf_counter()
    res = {"differential": differential(a.sem_root), "unit_basis": unit_basis(a.sem_root),
           "z3_negative_controls": negative_controls()}
    res["seconds"] = round(time.perf_counter() - t, 2)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({"differential_mismatches": res["differential"]["mismatches"],
                      "differential_comparisons": res["differential"]["comparisons"],
                      "unit_basis_mismatches": res["unit_basis"]["mismatches"],
                      "z3_negative_controls": res["z3_negative_controls"], "seconds": res["seconds"]}))
    ok = all(v.startswith("REFUTED") for v in res["z3_negative_controls"].values())
    return 0 if res["differential"]["mismatches"] == 0 and res["unit_basis"]["mismatches"] == 0 and ok else 1


if __name__ == "__main__":
    sys.exit(main())
