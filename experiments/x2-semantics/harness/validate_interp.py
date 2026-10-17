"""Validate the C reference interpreter against the Python reference before it is used (FUZZ-DESIGN §4,
prereg X2 §9 "Reference interpreter divergence": >= 10^6 random lane cases, disagreements block a run).

  1. python -I validate_interp.py gen  --sem-root S --manifest M --out VAL.vec [--lane-cases 1000000] [--seed X]
  2. x2fuzz predict VAL.vec VAL.c
  3. python -I pyref.py --sem-root S --manifest M VAL.vec VAL.py
  4. python -I validate_interp.py check --manifest M --vectors VAL.vec --c VAL.c --py VAL.py --out REPORT.json

Cases: every stub in turn (round robin), random MXCSR (any RC, DAZ, FTZ, sticky flag bits; 1 in 64 with an
exception unmasked, which both must report as outside the model), random write masks, operand lanes drawn
from the 12 value classes (f32 and f16 sources), the 10 integer classes (i32 sources) or random bytes
(integer entries), random old destination and GPR. No silicon is involved. Byte-exact comparison of every
output field (full 512-bit destination, MXCSR, RFLAGS, opmask, GPR) and of the status.
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_vectors as G  # noqa: E402
import vecfmt  # noqa: E402


def gen(a):
    with open(a.manifest, "rb") as f:
        raw = f.read()
    import hashlib
    man = json.loads(raw)
    msha = hashlib.sha256(raw).hexdigest()
    stubs = man["stubs"]

    def lanes_of(s):
        sem = s["sem"]
        if sem["builder"] in (2, 6, 7, 8):
            return 1
        if sem["builder"] == 3:
            return sem["vl"] // sem["dst_eb"]
        if sem["builder"] == 9:
            return sem["vl"] // sem["dst_eb"]
        return sem["vl"] // 32

    def recs():
        total, i = 0, 0
        while total < a.lane_cases:
            s = stubs[i % len(stubs)]
            sem = s["sem"]
            rng = G.keyed(a.seed, i)
            mx = 0x1F80 | (rng.bits(2) << 13) | (rng.bits(1) << 6) | (rng.bits(1) << 15) | rng.bits(6)
            if rng.range(0, 63) == 0:
                mx &= ~(1 << rng.range(7, 12))                      # one exception unmasked: outside the model
            src = "f16" if sem["fn"] == 10 else ("int" if sem["fn"] == 8 else "f32")
            eb = 16 if src == "f16" else 32
            s1 = s2 = 0
            for j in range(512 // eb):
                if sem["builder"] >= 9:
                    v1, v2 = rng.bits(eb), rng.bits(eb)
                else:
                    c1, c2 = rng.choice(G.F32_CLASSES), rng.choice(G.F32_CLASSES)
                    if src == "int":
                        v1 = G.draw_int(rng.choice(G.INT_CLASSES), rng, rng.range(0, 3))
                    elif src == "f16":
                        v1 = G.draw_f16(c1, rng, rng.range(0, 3))
                    else:
                        v1 = G.draw_f32(c1, rng, rng.range(0, 3))
                    v2 = G.draw_f32(c2, rng, rng.range(0, 3)) if eb == 32 else rng.bits(16)
                s1 |= v1 << (eb * j)
                s2 |= v2 << (eb * j)
            c = vecfmt.Case(mxcsr=mx, k=rng.bits(64), rflags_in=0x202 | (rng.bits(12) & 0x8D5),
                            gpr_in=(rng.bits(32) << 32) | G.draw_int(rng.choice(G.INT_CLASSES), rng, 0),
                            kdst_in=rng.bits(64), src1=s1, src2=s2,
                            dst_old=sum(rng.bits(32) << (32 * j) for j in range(16)))
            n = lanes_of(s)
            yield ({"stub": s["id"], "flags": 0, "set": vecfmt.SETS["VALID"], "class": 0, "env": 0, "lane": 0xFFFFFFFF,
                    "n_lane_cases": n, "index": i}, c)
            total += n
            i += 1
    n, sha = vecfmt.write_vectors(a.out, recs(), msha, "validate_interp", man["semantics_bundle"], "VALID-INTERP")
    print(json.dumps({"records": n, "vectors_sha256": sha}))


def check(a):
    with open(a.manifest) as f:
        man = json.load(f)
    stubs = man["stubs"]
    _, vrecs = vecfmt.read_vectors(a.vectors)
    ci, cres = vecfmt.read_results(a.c)
    pi, pres = vecfmt.read_results(a.py)
    assert len(vrecs) == len(cres) == len(pres)
    per = collections.Counter()
    lanes = collections.Counter()
    bad, unmod = [], 0
    for (meta, case), (_, cst, _, co), (_, pst, _, po) in zip(vrecs, cres, pres):
        s = stubs[meta["stub"]]
        fam = s["family"]
        per[fam] += 1
        lanes[fam] += meta["n_lane_cases"]
        if cst != pst:
            bad.append({"index": meta["index"], "stub": s["name"], "why": "status c=%d py=%d" % (cst, pst)})
            continue
        if cst == vecfmt.ST_UNMODELED:
            unmod += 1
            continue
        if (co.dst, co.mxcsr, co.rflags & 0x8D5, co.kdst, co.gpr) != (po.dst, po.mxcsr, po.rflags & 0x8D5, po.kdst, po.gpr):
            bad.append({"index": meta["index"], "stub": s["name"], "variant": s["variant"], "mxcsr": hex(case.mxcsr),
                        "src1": hex(case.src1), "src2": hex(case.src2), "k": hex(case.k),
                        "c": [hex(co.dst), hex(co.mxcsr), hex(co.kdst), hex(co.rflags), hex(co.gpr)],
                        "py": [hex(po.dst), hex(po.mxcsr), hex(po.kdst), hex(po.rflags), hex(po.gpr)]})
    rep = {"records": len(vrecs), "lane_cases": sum(lanes.values()), "divergences": len(bad), "unmodeled_both": unmod,
           "records_by_family": dict(per), "lane_cases_by_family": dict(lanes), "c_producer_sha256": ci["producer_sha256"],
           "py_bundle": pi["producer_sha256"], "vectors_sha256": vecfmt.file_sha256(a.vectors),
           "examples": bad[:50]}
    with open(a.out, "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps({k: rep[k] for k in ("records", "lane_cases", "divergences", "unmodeled_both")}))
    for b in bad[:10]:
        print("DIVERGENCE", json.dumps(b)[:600])
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "check"])
    ap.add_argument("--sem-root")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lane-cases", type=int, default=1000000)
    ap.add_argument("--seed", default="x2-validate-interp-v1")
    ap.add_argument("--vectors")
    ap.add_argument("--c")
    ap.add_argument("--py")
    a = ap.parse_args(argv)
    return gen(a) if a.cmd == "gen" else check(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
