"""Integer differential (added 2026-10-16 after review finding R2-5): ties the QF_BV lane formulas of the
integer rule queries (int_lanes.py, used by z3_rules.py and z3_int.py) and the C transliterations of x2prove.c
to the table's Python reference, semantics/int_ops.py.

  1. Z3 formula vs int_ops, by evaluating the formula terms on concrete inputs:
       pabs   all 256 bytes                         psign  all 2^16 (x, w)
       word   every single-product pair (2 x 2^16), the saturation corners, 20,000 random 4-tuples
       dpbusd_lane  every (u, x) at byte position 0 with 8 accumulators (2^19), 20,000 random (acc, 4 x (u, x))
       packs  every q in [-2^16, 2^16), the int32 extremes, 20,000 random int32
  2. C transliterations vs int_ops, by hash: x2prove's HASH-PABS-PSIGN and HASH-PACKS entries (exhaustive.json)
     must equal the same sha256 computed here from int_ops over the same inputs in the same order.
  The C transliterations of the word and dpbusd formulas are compared with the table's C lane functions
  exhaustively by x2prove's DIFF-MADDUBS and DIFF-DPBUSD entries.

  python -B int_differential.py --sem-root DIR --exhaustive exhaustive.json --out int_differential.json
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time

import z3

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--exhaustive", help="x2prove output with the HASH-* entries")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sys.path.insert(0, a.sem_root)
    sys.path.insert(0, HERE)
    import int_lanes
    from semantics import int_ops
    from semantics.bits import s8, s16, s32
    F = int_lanes.make(z3)
    rng = random.Random(20261016)
    t0 = time.perf_counter()
    res, mism = {"z3_version": z3.get_version_string(), "checks": {}}, []
    B8 = lambda v: z3.BitVecVal(v & 0xFF, 8)
    B32 = lambda v: z3.BitVecVal(v & 0xFFFFFFFF, 32)

    def ev(term, subs):
        return z3.simplify(z3.substitute(term, *subs)).as_long()

    # pabs / psign (8-bit lanes)
    xb, wb = z3.BitVecs("xb wb", 8)
    tp, ts = F.pabs(xb), F.psign(xb, wb)
    n = 0
    for x in range(256):
        want = int_ops.pabsb(x, 128) & 0xFF
        got = ev(tp, [(xb, B8(x))])
        n += 1
        if got != want:
            mism.append(("pabs", x, got, want))
    res["checks"]["pabs"] = n
    n = 0
    for x in range(256):
        for w in range(256):
            want = int_ops.psignb(x, w, 128) & 0xFF
            got = ev(ts, [(xb, B8(x)), (wb, B8(w))])
            n += 1
            if got != want:
                mism.append(("psign", x, w, got, want))
    res["checks"]["psign"] = n
    # word (one VPMADDUBSW word, int32 view)
    u0, u1, v0, v1 = z3.BitVecs("u0 u1 v0 v1", 8)
    tw = F.word(u0, u1, v0, v1)

    def word_ref(a0, a1, b0, b1):
        return s16(int_ops.pmaddubsw(a0 | (a1 << 8), b0 | (b1 << 8), 128) & 0xFFFF)
    cases = []
    for p in range(1 << 16):
        cases.append((p >> 8, 0, p & 0xFF, 0))
        cases.append((0, p >> 8, 0, p & 0xFF))
    for a0 in (0, 1, 127, 128, 255):
        for b0 in (0, 1, 0x7F, 0x80, 0x81, 0xFF):
            for a1 in (0, 255):
                for b1 in (0x7F, 0x80):
                    cases.append((a0, a1, b0, b1))
    cases += [tuple(rng.getrandbits(8) for _ in range(4)) for _ in range(20000)]
    for c in cases:
        got = s32(ev(tw, [(u0, B8(c[0])), (u1, B8(c[1])), (v0, B8(c[2])), (v1, B8(c[3]))]))
        want = word_ref(*c)
        if got != want:
            mism.append(("word", c, got, want))
    res["checks"]["word"] = len(cases)
    # dpbusd lane
    acc = z3.BitVec("acc", 32)
    us = z3.BitVecs("du0 du1 du2 du3", 8)
    xs = z3.BitVecs("dx0 dx1 dx2 dx3", 8)
    td = F.dpbusd_lane(acc, us, xs)
    accs = [0, 1, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, 0x12345678, 0x7FFF8000, 0x80007FFF]
    n = 0

    def dp_ref(ac, U, X):
        return int_ops.pdpbusd(ac, sum(b << (8 * i) for i, b in enumerate(U)), sum(b << (8 * i) for i, b in enumerate(X)),
                               128) & 0xFFFFFFFF
    dcases = [(ac, (p >> 8, 0, 0, 0), (p & 0xFF, 0, 0, 0)) for ac in accs for p in range(1 << 16)]
    dcases += [(rng.getrandbits(32), tuple(rng.getrandbits(8) for _ in range(4)), tuple(rng.getrandbits(8) for _ in range(4)))
               for _ in range(20000)]
    for ac, U, X in dcases:
        subs = [(acc, B32(ac))] + [(us[i], B8(U[i])) for i in range(4)] + [(xs[i], B8(X[i])) for i in range(4)]
        got = ev(td, subs)
        want = dp_ref(ac, U, X)
        n += 1
        if got != want:
            mism.append(("dpbusd_lane", hex(ac), U, X, hex(got), hex(want)))
    res["checks"]["dpbusd_lane"] = n
    # packs: VPACKSSDW then VPACKSSWB, lane 0
    q = z3.BitVec("q", 32)
    tk = F.packs(q)

    def packs_ref(v):
        w = int_ops.packssdw(v & 0xFFFFFFFF, 0, 128)
        return s8(int_ops.packsswb(w, 0, 128) & 0xFF)
    qs = list(range(-(1 << 16), 1 << 16)) + list(range(-(1 << 31), -(1 << 31) + 64)) + list(range((1 << 31) - 64, 1 << 31))
    qs += [s32(rng.getrandbits(32)) for _ in range(20000)]
    for v in qs:
        got = s8(ev(tk, [(q, B32(v))]) & 0xFF)
        if got != packs_ref(v):
            mism.append(("packs", v, got, packs_ref(v)))
    res["checks"]["packs"] = len(qs)
    # hashes of the C transliterations (x2prove) vs int_ops over the same inputs in the same order
    h1 = hashlib.sha256()
    h1.update(bytes(int_ops.pabsb(x, 128) & 0xFF for x in range(256)))
    h1.update(bytes(int_ops.psignb(x, w, 128) & 0xFF for x in range(256) for w in range(256)))
    h2 = hashlib.sha256()
    for lo, hi in ((-(1 << 17), 1 << 17), (-(1 << 31), -(1 << 31) + 64), ((1 << 31) - 64, 1 << 31)):
        h2.update(bytes(packs_ref(v) & 0xFF for v in range(lo, hi)))
    res["int_ops_hashes"] = {"HASH-PABS-PSIGN": h1.hexdigest(), "HASH-PACKS": h2.hexdigest()}
    if a.exhaustive:
        with open(a.exhaustive) as f:
            ex = json.load(f)
        got = {r["rule"]: r.get("hash") for r in ex["rules"] if r["rule"].startswith("HASH-")}
        res["x2prove_hashes"] = got
        for k, v in res["int_ops_hashes"].items():
            if got.get(k) != v:
                mism.append(("hash", k, got.get(k), v))
    res["total_checks"] = sum(res["checks"].values())
    res["mismatches"] = len(mism)
    res["mismatch_list"] = mism[:50]
    res["seconds"] = round(time.perf_counter() - t0, 1)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("checks", "total_checks", "mismatches", "seconds")}))
    print(json.dumps({"int_ops_hashes": res["int_ops_hashes"], "x2prove_hashes": res.get("x2prove_hashes")}))
    return 0 if not mism else 1


if __name__ == "__main__":
    sys.exit(main())
