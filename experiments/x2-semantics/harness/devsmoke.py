"""Development smoke run of the harness on the hand vectors of semantics/selftest.py (NOT data under the
X2 record: label DEV-SMOKE, no budget row, no class cell; FUZZ-DESIGN status section says what it may
and may not be used for).

  build:  python -I devsmoke.py build  --sem-root S --manifest M --out DEV.vec
  report: python -I devsmoke.py report --sem-root S --manifest M --vectors DEV.vec --silicon SIL [--silicon2 SIL2]
                                       --pred PRED --pyref PYREF --out REPORT.json

Hand vectors are EXTRACTED, not retyped: the lane-level sections A-D of selftest.py run with `check` and
the fp_ops lane functions instrumented; a check whose got-value came from exactly one top-level lane-
function call, and which passes, yields (label, function, operands, environment, hand expectation).
Each one is placed in lane 0 of several entries of its family (flag-neutral fillers in the other lanes).
Vector-level checks (C2, C3, E1-E8) are rebuilt as explicit cases under their selftest labels; every
label used here is asserted to occur verbatim in selftest.py.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vecfmt  # noqa: E402

ONE, TWO = 0x3F800000, 0x40000000
FLAGBITS = {"IE": 1, "DE": 2, "ZE": 4, "OE": 8, "UE": 16, "PE": 32}
FAMILY_STUBS = {      # function -> [(iform, variant)] ; lane 0 carries the hand vector
    "add": [("VADDSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "plain"), ("VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512", "plain"),
            ("VADDSS_XMMdq_XMMdq_XMMd", "plain"), ("ADDSS_XMMss_XMMss", "plain")],
    "sub": [("SUBSS_XMMss_XMMss", "plain")],
    "mul": [("VMULSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "plain"), ("VMULPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512", "plain"),
            ("VMULSS_XMMdq_XMMdq_XMMd", "plain"), ("MULSS_XMMss_XMMss", "plain")],
    "div": [("VDIVSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "plain"), ("VDIVSS_XMMdq_XMMdq_XMMd", "plain"),
            ("DIVSS_XMMss_XMMss", "plain")],
    "max_": [("VMAXSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "plain"), ("VMAXPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512", "plain"),
             ("VMAXSS_XMMdq_XMMdq_XMMd", "plain"), ("MAXSS_XMMss_XMMss", "plain")],
    "min_": [("VMINSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "plain"), ("VMINPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512", "plain"),
             ("MINSS_XMMss_XMMss", "plain")],
    "cmp_pred": [("VCMPPS_XMMdq_XMMdq_XMMdq_IMMb", "plain_imm%02X"), ("VCMPPS_MASKmskw_MASKmskw_XMMf32_XMMf32_IMM8_AVX512", "plain_imm%02X")],
    "comis0": [("UCOMISS_XMMss_XMMss", "plain"), ("VUCOMISS_XMMdq_XMMd", "plain")],
    "comis1": [("COMISS_XMMss_XMMss", "plain"), ("VCOMISS_XMMd_XMMd", "plain")],
    "cvt_i32_to_f32": [("VCVTDQ2PS_XMMdq_XMMdq", "plain"), ("VCVTDQ2PS_ZMMf32_MASKmskw_ZMMi32_AVX512", "plain"),
                       ("CVTSI2SS_XMMss_GPR32d", "plain"), ("VCVTSI2SS_XMMdq_XMMdq_GPR32d", "plain")],
    "cvt0": [("VCVTPS2DQ_XMMdq_XMMdq", "plain"), ("VCVTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512", "plain"),
             ("CVTSS2SI_GPR32d_XMMss", "plain")],
    "cvt1": [("VCVTTPS2DQ_XMMdq_XMMdq", "plain"), ("VCVTTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512", "plain"),
             ("CVTTSS2SI_GPR32d_XMMss", "plain"), ("VCVTTSS2SI_GPR32d_XMMd", "plain")],
    "cvt_f16_to_f32": [("VCVTPH2PS_XMMdq_XMMq", "plain"), ("VCVTPH2PS_ZMMf32_MASKmskw_YMMf16_AVX512", "plain")],
}
ER_STUBS = {"add": [("VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512", "plain_er%d"),
                    ("VADDSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "plain_er%d")],
            "mul": [("VMULPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512", "plain_er%d"),
                    ("VMULSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "plain_er%d")]}
FILL = {"add": (ONE, ONE), "sub": (ONE, ONE), "mul": (ONE, ONE), "div": (ONE, ONE), "max_": (ONE, TWO),
        "min_": (ONE, TWO), "cmp_pred": (ONE, TWO), "cvt_i32_to_f32": (1, None), "cvt0": (ONE, None),
        "cvt1": (ONE, None), "cvt_f16_to_f32": (0x3C00, None)}
PAT = 0xA5A50000


def extract(sem_root):
    """Run selftest sections A-D instrumented; return the hand vectors."""
    sys.path.insert(0, sem_root)
    from semantics import fp_ops, fpenv
    import semantics.selftest as st
    names = ["add", "sub", "mul", "div", "max_", "min_", "cmp_pred", "comis", "relation", "cvt_i32_to_f32",
             "cvt_f32_to_i32", "cvt_f16_to_f32"]
    orig = {n: getattr(fp_ops, n) for n in names}
    log, depth = [], [0]

    def wrap(n):
        f = orig[n]

        def w(*a, **k):
            top = depth[0] == 0
            depth[0] += 1
            try:
                res = f(*a, **k)
            finally:
                depth[0] -= 1
            if top:
                log.append((n, a, res))
            return res
        return w
    for n in names:
        setattr(fp_ops, n, wrap(n))
    vectors = []
    real_check = st.check

    def check(label, got, want):
        calls = list(log)
        log.clear()
        real_check(label, got, want)
        distinct = {(n, repr(a)) for n, a, _ in calls}
        if len(distinct) != 1 or got != want:
            return
        n, a, res = calls[0]
        env = [x for x in a if isinstance(x, fpenv.Env)]
        if not env:
            return
        env = env[0]
        v = {"label": "%s / %s" % (st.SECTION["name"], label), "fn": n, "mxcsr": env.mxcsr,
             "er": env.rc if env.er else None, "sae": bool(env.sae and not env.er)}
        if n in ("add", "sub", "mul", "div", "max_", "min_"):
            v["a"], v["b"] = a[0], a[1]
        elif n == "cmp_pred":
            v["a"], v["b"], v["imm"] = a[0], a[1], a[2]
        elif n == "comis":
            v["a"], v["b"], v["fn"] = a[0], a[1], "comis%d" % int(bool(a[3]))
        elif n == "cvt_f32_to_i32":
            v["a"], v["fn"] = a[0], "cvt%d" % int(bool(a[2]))
        elif n in ("cvt_i32_to_f32", "cvt_f16_to_f32"):
            v["a"] = a[0]
        else:
            return
        # hand expectation in a uniform form: result bits (or truth / ZPC) and flags (None = not stated)
        if isinstance(want, tuple) and len(want) == 2 and isinstance(want[0], str):
            v["want_bits"] = int(want[0], 16)
            v["want_flags"] = 0 if want[1] == "-" else sum(FLAGBITS[x] for x in want[1].split("|"))
        elif isinstance(want, tuple) and len(want) == 2 and isinstance(want[0], bool):
            v["want_bits"] = int(want[0])
            v["want_flags"] = 0 if want[1] == "-" else sum(FLAGBITS[x] for x in want[1].split("|"))
        elif isinstance(want, tuple) and len(want) == 2 and isinstance(want[0], tuple):
            v["want_bits"] = (want[0][0] << 6) | (want[0][1] << 2) | want[0][2]
            v["want_flags"] = want[1]
        elif isinstance(want, int):
            v["want_bits"], v["want_flags"] = want, None
        else:
            return
        vectors.append(v)
    st.check = check
    try:
        for sec in (st.sec_a_arith, st.sec_b_minmax, st.sec_c_cmp, st.sec_d_cvt):
            sec()
    finally:
        st.check = real_check
        for n in names:
            setattr(fp_ops, n, orig[n])
    with open(os.path.join(sem_root, "semantics", "selftest.py"), encoding="utf-8") as f:
        src = f.read()
    return vectors, src, st.FAIL


def lanes_case(stub_sem, roles, lanes, mxcsr, k=0):
    """Case with the given (a, b) lanes; legacy dst_src1 forms take src1 from the destination register."""
    dst_old = sum((PAT + i) << (32 * i) for i in range(16))
    c = vecfmt.Case(mxcsr=mxcsr, k=k, rflags_in=0x202 | 0x8D5, gpr_in=0xDEADBEEFDEADBEEF, kdst_in=(1 << 64) - 1,
                    dst_old=dst_old)
    eb = stub_sem["src_eb"] if stub_sem["builder"] == 3 else 32
    s1 = sum((a & ((1 << eb) - 1)) << (eb * i) for i, (a, _) in enumerate(lanes))
    for i in range(len(lanes), 512 // eb):
        s1 |= ((0x3C3C0000 + i) & ((1 << eb) - 1)) << (eb * i)
    s2 = sum(((b or 0) & 0xFFFFFFFF) << (32 * i) for i, (_, b) in enumerate(lanes))
    if stub_sem["builder"] == 8:                       # CVTSI2SS: the integer comes from EAX
        c.gpr_in = 0xDEADBEEF00000000 | (lanes[0][0] & 0xFFFFFFFF)
    if "dst_src1" in roles and stub_sem["builder"] == 2:
        c.dst_old = (dst_old & ~0xFFFFFFFF) | (s1 & 0xFFFFFFFF)
    c.src1, c.src2 = s1, s2
    return c


def build(a):
    sys.path.insert(0, a.sem_root)
    vectors, src, fails = extract(a.sem_root)
    if fails:
        raise SystemExit("selftest.py itself fails on this machine: %s" % fails[:3])
    from semantics import table
    with open(a.manifest, "rb") as f:
        raw = f.read()
    import hashlib
    msha = hashlib.sha256(raw).hexdigest()
    man = json.loads(raw)
    by = {(s["iform"], s["variant"]): s for s in man["stubs"]}
    recs, meta_out = [], []

    def add(stub, case, label, lane0_want=None, flags_want=None, kind="lane"):
        e = table.ENTRIES[stub["entry_index"]]
        lane_kind = kind == "lane"
        recs.append(({"stub": stub["id"], "flags": vecfmt.FLAG_FILLERS if lane_kind else 0, "set": vecfmt.SETS["DEV"],
                      "class": 0, "env": 0, "lane": 0 if lane_kind else 0xFFFFFFFF, "n_lane_cases": 1,
                      "index": len(recs)}, case))
        meta_out.append({"record": len(recs) - 1, "label": label, "stub": stub["name"], "iform": stub["iform"],
                         "variant": stub["variant"], "kind": kind, "want_bits": lane0_want, "want_flags": flags_want,
                         "family": e["family"]})

    for v in vectors:
        fn = v["fn"]
        if v["er"] is not None:
            targets = [(i, var % v["er"]) for i, var in ER_STUBS.get(fn, [])]
        else:
            targets = [(i, var % v["imm"] if "%" in var else var) for i, var in FAMILY_STUBS[fn]]
        for iform, var in targets:
            stub = by.get((iform, var))
            if stub is None:
                continue
            e = table.ENTRIES[stub["entry_index"]]
            roles = {o["role"] for o in e["operands"]}
            n = 1 if (e["scalar"] is not None or stub["sem"]["builder"] in (6, 7)) else e["lanes"]
            fa, fb = FILL.get(fn, (ONE, TWO))
            lane0 = (v["a"], v.get("b"))
            fill = (fa, fb if "b" in v else None)
            add(stub, lanes_case(stub["sem"], roles, [lane0] + [fill] * (n - 1), v["mxcsr"]), v["label"],
                v["want_bits"], v["want_flags"])
    # vector-level checks rebuilt under their selftest labels (expectations: the reference prediction,
    # which selftest.py asserts equal to the hand values)
    ones, twos = [ONE] * 16, [TWO] * 16

    def C(**kw):
        c = vecfmt.Case(mxcsr=kw.get("mxcsr", 0x1F80), k=kw.get("k", 0), rflags_in=0x202 | 0x8D5,
                        gpr_in=kw.get("gpr", 0xDEADBEEFDEADBEEF), kdst_in=(1 << 64) - 1,
                        src1=kw.get("src1", 0), src2=kw.get("src2", 0),
                        dst_old=kw.get("dst_old", sum((PAT + i) << (32 * i) for i in range(16))))
        return c
    P = lambda L: sum((x & 0xFFFFFFFF) << (32 * i) for i, x in enumerate(L))
    V = "VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512"
    vec_cases = [
        ("E1 zero-mask", (V, "zero"), C(k=0x00F0, src1=P(ones), src2=P(twos))),
        ("E1 merge-mask", (V, "merge"), C(k=0x00F0, src1=P(ones), src2=P(twos), dst_old=P([0xDEADBEEF] * 16))),
        ("E1 masked-off SNaN raises nothing", (V, "merge"), C(k=0xFFFE, src1=P([0x7F800001] + [ONE] * 15), src2=P(twos))),
        ("E1 active SNaN raises IE", (V, "merge"), C(k=0x0001, src1=P([0x7F800001] + [ONE] * 15), src2=P(twos))),
        ("E2 {1to16} broadcast", ("VMULPS_ZMMf32_MASKmskw_ZMMf32_MEMf32_AVX512", "plain_bcast"), C(src1=P(ones), src2=TWO)),
        ("E3 addss upper lanes from src1", ("VADDSS_XMMdq_XMMdq_XMMd", "plain"),
         C(src1=P([ONE, 0x40A00000, 0x40C00000, 0x40E00000]), src2=P([TWO, 0x41100000, 0x41100000, 0x41100000]))),
        ("E4 masked scalar merge", ("VADDSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "merge"),
         C(k=0, src1=P([ONE, 0x40A00000, 0x40C00000, 0x40E00000]), src2=P([TWO, 0x41100000, 0x41100000, 0x41100000]),
           dst_old=P([0x12345678, 0, 0, 0]))),
        ("E4 masked scalar zero", ("VADDSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "zero"),
         C(k=0, src1=P([ONE, 0x40A00000, 0x40C00000, 0x40E00000]), src2=P([TWO, 0x41100000, 0x41100000, 0x41100000]))),
        ("E5 {er} RU overrides MXCSR.RC", (V, "plain_er2"), C(src1=P(ones), src2=P([0x33800000] * 16))),
        ("E8 CVTSI2SS legacy full width", ("CVTSI2SS_XMMss_GPR32d", "plain"),
         C(gpr=5, dst_old=P([0x11110000 + i for i in range(16)]))),
        ("E8 VCVTSI2SS VEX full width", ("VCVTSI2SS_XMMdq_XMMdq_GPR32d", "plain"),
         C(gpr=(-3) & 0xFFFFFFFF, src1=P([0x22220000 + i for i in range(4)]), dst_old=P([0x11110000 + i for i in range(16)]))),
        ("E8 CVTTSS2SI -2.75 -> r64", ("CVTTSS2SI_GPR32d_XMMss", "plain"), C(src1=0xC0300000)),
        ("E8 VCVTTSS2SI NaN -> indefinite, zero-extended", ("VCVTTSS2SI_GPR32d_XMMd", "plain"), C(src1=0x7FC00000)),
        ("E8 CVTSS2SI 2.5 RU -> 3", ("CVTSS2SI_GPR32d_XMMss", "plain"), C(src1=0x40200000, mxcsr=0x5F80)),
        ("E8 ADDSS legacy keeps lanes 1-15", ("ADDSS_XMMss_XMMss", "plain"),
         C(src2=P([TWO]), dst_old=P([0x11110000 + i for i in range(16)]))),
        ("E8 EVEX VADDSS zeroes 511:128", ("VADDSS_XMMf32_MASKmskw_XMMf32_XMMf32_AVX512", "plain"),
         C(src1=P([ONE, 7, 8, 9]), src2=P([TWO]), dst_old=P([0x11110000 + i for i in range(16)]))),
        ("E8 VUCOMISS RFLAGS full", ("VUCOMISS_XMMdq_XMMd", "plain"), C(src1=ONE, src2=0x7FC00000)),
        ("C2 k=1011", ("VCMPPS_MASKmskw_MASKmskw_XMMf32_XMMf32_IMM8_AVX512", "merge_imm03"),
         C(k=0b1011, src1=P([ONE, 0x7FC00000, TWO, 0x7F800001]), src2=P([ONE, 0x7FC00000, TWO, 0x7F800001]))),
        ("C2 k=0011 hides SNaN lane", ("VCMPPS_MASKmskw_MASKmskw_XMMf32_XMMf32_IMM8_AVX512", "merge_imm03"),
         C(k=0b0011, src1=P([ONE, 0x7FC00000, TWO, 0x7F800001]), src2=P([ONE, 0x7FC00000, TWO, 0x7F800001]))),
        ("C3 vex unord lanes", ("VCMPPS_XMMdq_XMMdq_XMMdq_IMMb", "plain_imm03"),
         C(src1=P([ONE, 0x7FC00000, TWO, 0x7F800001]), src2=P([ONE, 0x7FC00000, TWO, 0x7F800001]))),
    ]
    for label, key, case in vec_cases:
        if label not in src:
            raise SystemExit("label not in selftest.py: %s" % label)
        add(by[key], case, label, kind="vector")
    n, sha = vecfmt.write_vectors(a.out, recs, msha, "devsmoke", man["semantics_bundle"], "DEV-SMOKE")
    with open(a.out + ".meta.json", "w") as f:
        json.dump({"hand_vectors_extracted": len(vectors), "records": n, "vectors_sha256": sha, "meta": meta_out},
                  f, indent=1)
    print(json.dumps({"hand_vectors_extracted": len(vectors), "vector_level_cases": len(vec_cases), "records": n,
                      "vectors_sha256": sha}))


def report(a):
    import compare
    import hashlib
    with open(a.manifest, "rb") as f:
        mraw = f.read()
    man = json.loads(mraw)
    with open(a.vectors + ".meta.json") as f:
        meta = json.load(f)["meta"]
    vec = vecfmt.read_vectors(a.vectors)
    sil, pred, py = vecfmt.read_results(a.silicon), vecfmt.read_results(a.pred), vecfmt.read_results(a.pyref)
    sil2 = vecfmt.read_results(a.silicon2) if a.silicon2 else None
    rep = compare.compare(man, vec, sil, pred, py, sil2, vectors_sha=vecfmt.file_sha256(a.vectors),
                          manifest_sha=hashlib.sha256(mraw).hexdigest())
    stubs = man["stubs"]
    hand = {"checked": 0, "silicon_eq_hand": 0, "c_eq_hand": 0, "py_eq_hand": 0, "disagree": []}
    for m in meta:
        if m["kind"] != "lane":
            continue
        i = m["record"]
        stub = stubs[vec[1][i][0]["stub"]]
        sem = stub["sem"]

        def lane0(o):
            if sem["dst_kind"] == 1:
                return o.kdst & 1
            if sem["dst_kind"] == 2:
                return o.rflags & 0x45
            if sem["dst_kind"] == 3:
                return o.gpr & 0xFFFFFFFF
            v = o.dst & 0xFFFFFFFF
            return int(v == 0xFFFFFFFF) if sem["builder"] == 5 else v
        hand["checked"] += 1
        wb, wf = m["want_bits"], m["want_flags"]
        res = {}
        for name, src in (("silicon", sil), ("c", pred), ("py", py)):
            o = src[1][i][3]
            ok = lane0(o) == wb and (wf is None or (o.mxcsr & 0x3F) == wf)
            res[name] = ok
            hand["%s_eq_hand" % name] += ok
        if not all(res.values()):
            o = sil[1][i][3]
            hand["disagree"].append({"record": i, "label": m["label"], "stub": m["stub"], "variant": m["variant"],
                                     "want": [hex(wb), wf], "silicon": [hex(lane0(o)), o.mxcsr & 0x3F],
                                     "c": [hex(lane0(pred[1][i][3])), pred[1][i][3].mxcsr & 0x3F], "agree": res})
    rep["hand_vectors"] = hand
    rep["fingerprint_note"] = "see the .fingerprint.json files next to the silicon results"
    with open(a.out, "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps({k: rep[k] for k in ("records", "lane_mismatches", "flag_mismatch_executions",
                                          "interpreter_divergences", "nondeterminism", "harness_anomalies")}))
    print(json.dumps({k: v for k, v in hand.items() if k != "disagree"}), "disagreements:", len(hand["disagree"]))
    for d in hand["disagree"][:40]:
        print("HAND", json.dumps(d))
    for d in rep["disagreements"][:40]:
        print("TABLE/SILICON", json.dumps({k: d[k] for k in ("stub", "variant", "lanes", "silicon", "table",
                                                             "mxcsr_silicon", "mxcsr_table")}))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "report"])
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vectors")
    ap.add_argument("--silicon")
    ap.add_argument("--silicon2")
    ap.add_argument("--pred")
    ap.add_argument("--pyref")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.sem_root)
    return build(a) if a.cmd == "build" else report(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
