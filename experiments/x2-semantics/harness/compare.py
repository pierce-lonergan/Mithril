"""Comparator of the X2 fuzz harness (FUZZ-DESIGN.md §1, §2, §6.3). Deterministic; a Gatekeeper
script: agents run it, they never judge its output (ROADMAP §1 rule 3).

  python -I compare.py --manifest stubs_manifest.json --vectors VEC --silicon RES [--silicon2 RES2]
         --pred PRED_C [--pyref PRED_PY] [--bochs BOCHS] [--classes VEC.classes.json] --out REPORT.json
  python -I compare.py --selftest

Units (prereg X2 §4 item 8): a lane mismatch is any bit of a lane observable (full-width destination,
destination opmask, RFLAGS & 0x8D5, the 64-bit GPR) that differs between silicon and the table
prediction, attributed to the lane whose bits differ; a flag mismatch is any bit of MXCSR[5:0] that
differs, counted per execution. Cells are (iform, set, class, environment). Differences between the C
interpreter and the Python oracle are interpreter divergences (they block a run); differences between
two silicon runs are nondeterminism; a silicon exception, a changed MXCSR control field or a vector
whose MXCSR has a sticky flag preset (outside VALID sets; FUZZ-DESIGN §2) is a harness anomaly.

With --bochs (revised 2026-10-16 after review) the Bochs output is compared with the table on EVERY
record, not only where silicon disagrees: table = silicon != Bochs gives the "Bochs differs" verdict of
FUZZ-DESIGN §6.3 (it blocks validated(partition)), every table/silicon disagreement gets the three-way
verdict, and a Bochs record whose status is not OK is a Bochs anomaly. Per-cell counters
bochs_mismatch (Bochs != table) and bochs_anomaly.

Provenance (revised 2026-10-16): every results input must name the vectors file's sha256 and the
manifest's sha256 in its header, have as many records as the vectors file, and carry each vector
record's index in order; otherwise the comparison stops with ProvenanceError.
"""
import argparse
import collections
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vecfmt  # noqa: E402

RFL = 0x8D5


def lane_geometry(sem):
    """(element bits, number of lane-case lanes, compared bits) for the destination."""
    b = sem["builder"]
    if sem["dst_kind"] == 1:
        return 1, sem["vl"] // 32, 64
    if sem["dst_kind"] in (2, 3):
        return 64, 1, 64
    width = 128 if sem["scalar"] else sem["vl"]
    eb = sem["dst_eb"] if b in (3, 9, 10) else 32
    return eb, width // eb, 512


def diff_lanes(sem, s, p):
    """Lanes whose observable bits differ: ints (lane indices) and 'upper' for bits above the operation width
    (or above lane 0 of a scalar form: lanes copied from src1 / preserved)."""
    out = []
    if sem["dst_kind"] == 1:
        x = s.kdst ^ p.kdst
        n = sem["vl"] // 32
        out = [i for i in range(n) if (x >> i) & 1]
        if x >> n:
            out.append("upper")
        return out
    if sem["dst_kind"] == 2:
        return [0] if (s.rflags ^ p.rflags) & RFL else []
    if sem["dst_kind"] == 3:
        return [0] if s.gpr != p.gpr else []
    eb, n, _ = lane_geometry(sem)
    x = s.dst ^ p.dst
    m = (1 << eb) - 1
    lane_cases = 1 if sem["scalar"] else n
    out = [i for i in range(lane_cases) if (x >> (eb * i)) & m]
    if x >> (eb * lane_cases):
        out.append("upper")
    return out


def lane_value(sem, o, lane):
    if lane == "upper":
        return None
    if sem["dst_kind"] == 1:
        return (o.kdst >> lane) & 1
    if sem["dst_kind"] == 2:
        return o.rflags & RFL
    if sem["dst_kind"] == 3:
        return o.gpr
    eb, _, _ = lane_geometry(sem)
    return (o.dst >> (eb * lane)) & ((1 << eb) - 1)


def same_obs(sem, a, b):
    return not diff_lanes(sem, a, b) and ((a.mxcsr ^ b.mxcsr) & 0x3F) == 0


def verdict(sem, t, s, bo):
    """FUZZ-DESIGN §6.3 for one disagreeing execution (t = table, s = silicon, bo = Bochs or None)."""
    ts = same_obs(sem, t, s)
    if bo is None:
        return "table/silicon mismatch (no second oracle)" if not ts else "agree"
    tb, sb = same_obs(sem, t, bo), same_obs(sem, s, bo)
    if not ts and sb:
        return "table bug"
    if not ts and tb:
        return "Zen 5 differs from the shared reading"
    if ts and not tb:
        return "Bochs differs"
    if not ts:
        return "three-way disagreement"
    return "agree"


class ProvenanceError(Exception):
    """A results file does not belong to the vectors file / manifest it is compared against."""


def check_provenance(name, res, vrecs, vectors_sha=None, manifest_sha=None):
    info, recs = res
    if vectors_sha is not None and info.get("vectors_sha256") != vectors_sha:
        raise ProvenanceError("%s: header vectors_sha256 %s != vectors file %s" % (name, info.get("vectors_sha256"),
                                                                                  vectors_sha))
    if manifest_sha is not None and info.get("manifest") != manifest_sha:
        raise ProvenanceError("%s: header manifest %s != manifest file %s" % (name, info.get("manifest"), manifest_sha))
    if len(recs) != len(vrecs):
        raise ProvenanceError("%s: %d records, vectors file has %d" % (name, len(recs), len(vrecs)))
    for i, (r, (meta, _)) in enumerate(zip(recs, vrecs)):
        if r[0] != meta["index"]:
            raise ProvenanceError("%s: record %d carries index %d, vector record has index %d" % (name, i, r[0],
                                                                                                 meta["index"]))


def compare(manifest, vec, sil, pred, pyref=None, sil2=None, bochs=None, classes=None, vectors_sha=None,
            manifest_sha=None):
    """vec = (info, records) from vecfmt.read_vectors; every other input = (info, records) from
    vecfmt.read_results. vectors_sha / manifest_sha: sha256 of the vectors file and of the manifest file;
    when given, every results header must name them (ProvenanceError otherwise)."""
    stubs = manifest["stubs"]
    vinfo, vrecs = vec
    if manifest_sha is not None and vinfo.get("manifest") != manifest_sha:
        raise ProvenanceError("vectors: header manifest %s != manifest file %s" % (vinfo.get("manifest"), manifest_sha))
    inputs = [("silicon", sil), ("pred", pred), ("pyref", pyref), ("silicon2", sil2), ("bochs", bochs)]
    for name, res in inputs:
        if res is not None:
            check_provenance(name, res, vrecs, vectors_sha, manifest_sha)
    srecs, precs = sil[1], pred[1]
    pyr = pyref[1] if pyref else None
    s2 = sil2[1] if sil2 else None
    bor = bochs[1] if bochs else None
    dev_label_valid = str(vinfo.get("label", "")).startswith("VALID")
    cname = (lambda i: classes["classes"][i]) if classes else (lambda i: str(i))
    ename = (lambda i: classes["envs"][i]) if classes else (lambda i: str(i))
    setname = {v: k for k, v in vecfmt.SETS.items()}
    cells = collections.OrderedDict()
    dis, anomalies, divergences, nondet, bochs_anom = [], [], [], [], []
    for i, ((meta, case), (_, sst, sexc, so), (_, pst, _, po)) in enumerate(zip(vrecs, srecs, precs)):
        stub = stubs[meta["stub"]]
        sem = stub["sem"]
        key = (stub["iform"], setname.get(meta["set"], str(meta["set"])), cname(meta["class"]), ename(meta["env"]))
        c = cells.setdefault(key, {"executions": 0, "lane_cases": 0, "lane_mismatch": 0, "flag_mismatch": 0,
                                   "upper_mismatch": 0, "filler_mismatch": 0, "single_lane_mismatch": 0,
                                   "single_lane_flag_mismatch": 0, "anomalies": 0, "bochs_mismatch": 0,
                                   "bochs_anomaly": 0})
        c["executions"] += 1
        c["lane_cases"] += meta["n_lane_cases"]
        if pst != vecfmt.ST_OK:
            anomalies.append({"record": i, "kind": "unmodeled case (prediction status %d)" % pst, "stub": stub["name"]})
            c["anomalies"] += 1
            continue
        if (case.mxcsr & 0x3F) and not dev_label_valid:
            anomalies.append({"record": i, "kind": "sticky MXCSR flag preset in the vector (0x%04X)" % case.mxcsr,
                              "stub": stub["name"]})
            c["anomalies"] += 1
            continue
        tb, bo = None, None
        if bor is not None:
            _, bst, bexc, bo = bor[i]
            if bst != vecfmt.ST_OK:
                bochs_anom.append({"record": i, "stub": stub["name"], "kind": "exception 0x%08X" % bexc
                                   if bst == vecfmt.ST_EXCEPTION else "status %d" % bst})
                c["bochs_anomaly"] += 1
                bo = None
            else:
                tb = same_obs(sem, po, bo)
                if not tb:
                    c["bochs_mismatch"] += 1
        if pyr is not None:
            _, yst, _, yo = pyr[i]
            if yst != pst or diff_lanes(sem, po, yo) or ((po.mxcsr ^ yo.mxcsr) & 0xFFFF) or \
                    (sem["dst_kind"] == 0 and po.dst != yo.dst):
                divergences.append({"record": i, "stub": stub["name"], "variant": stub["variant"],
                                    "c": [hex(po.dst), hex(po.mxcsr), hex(po.kdst), hex(po.rflags), hex(po.gpr)],
                                    "py": [hex(yo.dst), hex(yo.mxcsr), hex(yo.kdst), hex(yo.rflags), hex(yo.gpr)]})
        if sst != vecfmt.ST_OK:
            kind = "exception 0x%08X" % sexc if sst == vecfmt.ST_EXCEPTION else "status %d" % sst
            if meta["flags"] & vecfmt.FLAG_MEMFAULT:
                c["lane_mismatch"] += max(1, meta["n_lane_cases"])     # the table says: no fault in masked-off lanes
                dis.append({"record": i, "stub": stub["name"], "iform": stub["iform"], "variant": stub["variant"],
                            "cell": key, "lane": "fault", "silicon": kind, "table": "no fault",
                            "verdict": "table/silicon mismatch (fault)"})
            else:
                anomalies.append({"record": i, "kind": kind, "stub": stub["name"]})
                c["anomalies"] += 1
            continue
        if (so.mxcsr ^ case.mxcsr) & 0xFFC0:
            anomalies.append({"record": i, "kind": "MXCSR control field changed", "stub": stub["name"]})
            c["anomalies"] += 1
        if s2 is not None:
            _, s2st, _, s2o = s2[i]
            if s2st != sst or diff_lanes(sem, so, s2o) or so.mxcsr != s2o.mxcsr or so.dst != s2o.dst:
                nondet.append({"record": i, "stub": stub["name"]})
        lanes = diff_lanes(sem, so, po)
        flag_x = (so.mxcsr ^ po.mxcsr) & 0x3F
        if not lanes and not flag_x and tb is False:
            # table = silicon != Bochs: FUZZ-DESIGN §6.3 "Bochs differs" (blocks validated(partition))
            blanes = diff_lanes(sem, bo, po)
            dis.append({"record": i, "stub": stub["name"], "iform": stub["iform"], "variant": stub["variant"],
                        "cell": key, "lanes": blanes,
                        "bochs": {str(ln): (None if lane_value(sem, bo, ln) is None else hex(lane_value(sem, bo, ln)))
                                  for ln in blanes},
                        "table": {str(ln): (None if lane_value(sem, po, ln) is None else hex(lane_value(sem, po, ln)))
                                  for ln in blanes},
                        "mxcsr_bochs": hex(bo.mxcsr), "mxcsr_table": hex(po.mxcsr), "verdict": verdict(sem, po, so, bo),
                        "inputs": {"src1": hex(case.src1), "src2": hex(case.src2), "dst_old": hex(case.dst_old),
                                   "k": hex(case.k), "mxcsr": hex(case.mxcsr), "gpr_in": hex(case.gpr_in)}})
        if lanes or flag_x:
            v = verdict(sem, po, so, bo)
            single = bool(meta["flags"] & vecfmt.FLAG_SINGLE_LANE)   # interpreted only after F-MASKEXC (sec. 2)
            for ln in lanes:
                if single:
                    c["single_lane_mismatch"] += 1
                elif ln == "upper":
                    c["upper_mismatch"] += 1
                elif (meta["flags"] & vecfmt.FLAG_FILLERS) and ln != meta["lane"]:
                    c["filler_mismatch"] += 1
                else:
                    c["lane_mismatch"] += 1
            if flag_x:
                c["single_lane_flag_mismatch" if single else "flag_mismatch"] += 1
            dis.append({"record": i, "stub": stub["name"], "iform": stub["iform"], "variant": stub["variant"],
                        "cell": key, "lanes": lanes,
                        "silicon": {str(ln): (None if lane_value(sem, so, ln) is None else hex(lane_value(sem, so, ln)))
                                    for ln in lanes},
                        "table": {str(ln): (None if lane_value(sem, po, ln) is None else hex(lane_value(sem, po, ln)))
                                  for ln in lanes},
                        "mxcsr_silicon": hex(so.mxcsr), "mxcsr_table": hex(po.mxcsr), "verdict": v,
                        "inputs": {"src1": hex(case.src1), "src2": hex(case.src2), "dst_old": hex(case.dst_old),
                                   "k": hex(case.k), "mxcsr": hex(case.mxcsr), "gpr_in": hex(case.gpr_in)}})
    rows = [dict(zip(("iform", "set", "class", "env"), k), **v) for k, v in cells.items()]
    bad_cells = [r for r in rows if r["lane_mismatch"] or r["flag_mismatch"] or r["upper_mismatch"] or r["filler_mismatch"]
                 or r["single_lane_mismatch"] or r["single_lane_flag_mismatch"]]
    rep = {"records": len(vrecs), "vectors_label": vinfo["label"],
           "lane_cases": sum(r["lane_cases"] for r in rows),
           "cells": len(rows), "cells_with_mismatch": len(bad_cells),
           "lane_mismatches": sum(r["lane_mismatch"] for r in rows),
           "flag_mismatch_executions": sum(r["flag_mismatch"] for r in rows),
           "single_lane_mismatch_executions": sum(r["single_lane_mismatch"] + r["single_lane_flag_mismatch"] for r in rows),
           "interpreter_divergences": len(divergences), "nondeterminism": len(nondet),
           "harness_anomalies": len(anomalies), "rows": rows, "disagreements": dis,
           "divergence_list": divergences[:200], "anomaly_list": anomalies[:200], "nondeterminism_list": nondet[:200],
           "provenance": {"vectors_sha256": vectors_sha, "manifest_sha256": manifest_sha,
                          "producers": {n: {"producer": r[0].get("producer"), "producer_sha256": r[0].get("producer_sha256")}
                                        for n, r in inputs if r is not None}}}
    if bor is not None:
        rep.update({"bochs_mismatch_executions": sum(r["bochs_mismatch"] for r in rows),
                    "bochs_differs": sum(1 for d in dis if d["verdict"] == "Bochs differs"),
                    "bochs_anomalies": len(bochs_anom), "bochs_anomaly_list": bochs_anom[:200],
                    "cells_with_bochs_difference": sum(1 for r in rows if r["bochs_mismatch"] or r["bochs_anomaly"])})
    return rep


def selftest():
    """Synthetic inputs only: fabricated silicon outputs with injected differences."""
    fails = []
    man = {"stubs": [
        {"name": "s0", "iform": "VADDPS_ZMM", "variant": "plain",
         "sem": {"builder": 1, "dst_kind": 0, "vl": 512, "scalar": 0, "dst_eb": 32}},
        {"name": "s1", "iform": "VCMPPS_K", "variant": "plain_imm03",
         "sem": {"builder": 4, "dst_kind": 1, "vl": 512, "scalar": 0, "dst_eb": 32}},
        {"name": "s2", "iform": "UCOMISS", "variant": "plain",
         "sem": {"builder": 6, "dst_kind": 2, "vl": 128, "scalar": 0, "dst_eb": 32}},
        {"name": "s3", "iform": "ADDSS", "variant": "plain",
         "sem": {"builder": 2, "dst_kind": 0, "vl": 128, "scalar": 1, "dst_eb": 32}}]}
    vrecs, sil, pred = [], [], []
    for i in range(8):
        st = i % 4
        meta = {"stub": st, "flags": 0, "set": 1, "class": 0, "env": 0, "lane": 0xFFFFFFFF, "n_lane_cases": 1, "index": i}
        vrecs.append((meta, vecfmt.Case()))
        o = vecfmt.Out(dst=0x1234 << 64, mxcsr=0x1F80, kdst=0b1010, rflags=0x44)
        pred.append((i, 0, 0, o))
        s = vecfmt.Out(o.dst, o.mxcsr, o.rflags, o.kdst, o.gpr)
        if i == 4:
            s.dst ^= 1 << (32 * 3)          # lane 3 of the zmm stub
        if i == 5:
            s.kdst ^= 1 << 20               # k bit above 16 lanes -> upper
        if i == 6:
            s.rflags ^= 0x800               # OF set: lane 0 of COMIS
        if i == 7:
            s.dst ^= 1 << 40                # scalar form: lane 1 (copied from src1) -> upper
            s.mxcsr |= 0x20                 # PE
        sil.append((i, 0, 0, s))
    # a single-active-lane duplicate (flag isolation) with a difference: tallied apart, never as a lane case
    meta = {"stub": 0, "flags": vecfmt.FLAG_SINGLE_LANE, "set": 2, "class": 0, "env": 0, "lane": 5, "n_lane_cases": 0,
            "index": 8}
    vrecs.append((meta, vecfmt.Case()))
    o = vecfmt.Out(dst=0, mxcsr=0x1F80)
    pred.append((8, 0, 0, o))
    sil.append((8, 0, 0, vecfmt.Out(dst=1 << (32 * 5), mxcsr=0x1F81)))
    rep = compare(man, ({"label": "SELFTEST"}, vrecs), ({}, sil), ({}, pred))
    if rep["single_lane_mismatch_executions"] != 2:
        fails.append("single-lane tallies %s, want 2 (one lane, one flag)" % rep["single_lane_mismatch_executions"])
    want = {"lane_mismatches": 2, "flag_mismatch_executions": 1, "cells_with_mismatch": 5, "harness_anomalies": 0}
    for k, v in want.items():
        if rep[k] != v:
            fails.append("%s = %s, want %s" % (k, rep[k], v))
    lanes = sorted(str(d["lanes"]) for d in rep["disagreements"])
    if lanes != sorted(["[3]", "['upper']", "[0]", "['upper']", "[5]"]):
        fails.append("lane attribution %s" % lanes)
    # three-way verdicts
    sem = man["stubs"][0]["sem"]
    t, s_, b_ = vecfmt.Out(dst=1), vecfmt.Out(dst=2), vecfmt.Out(dst=2)
    if verdict(sem, t, s_, b_) != "table bug":
        fails.append("verdict table bug")
    if verdict(sem, t, s_, vecfmt.Out(dst=1)) != "Zen 5 differs from the shared reading":
        fails.append("verdict vendor deviation")
    if verdict(sem, t, vecfmt.Out(dst=1), vecfmt.Out(dst=3)) != "Bochs differs":
        fails.append("verdict Bochs differs")
    # the Bochs path through compare() (review 2026-10-16: it was consulted only where silicon disagreed)
    man1 = {"stubs": [man["stubs"][0]]}
    vb, sb, pb, bb = [], [], [], []
    plan = [  # (table, silicon, bochs, bochs status)
        (vecfmt.Out(dst=5, mxcsr=0x1F80), vecfmt.Out(dst=5, mxcsr=0x1F80), vecfmt.Out(dst=7, mxcsr=0x1FA0), 0),  # Bochs differs
        (vecfmt.Out(dst=5, mxcsr=0x1F80), vecfmt.Out(dst=5, mxcsr=0x1F80), vecfmt.Out(dst=5, mxcsr=0x1F80), 0),  # agree
        (vecfmt.Out(dst=5, mxcsr=0x1F80), vecfmt.Out(dst=5, mxcsr=0x1F80), vecfmt.Out(dst=7, mxcsr=0x1FA0), 1),  # Bochs fault
        (vecfmt.Out(dst=5, mxcsr=0x1F80), vecfmt.Out(dst=6, mxcsr=0x1F80), vecfmt.Out(dst=6, mxcsr=0x1F80), 0),  # table bug
    ]
    for i, (t_, s_, b_, bst) in enumerate(plan):
        vb.append(({"stub": 0, "flags": 0, "set": 7, "class": 0, "env": 0, "lane": 0xFFFFFFFF, "n_lane_cases": 16,
                    "index": i}, vecfmt.Case()))
        pb.append((i, 0, 0, t_))
        sb.append((i, 0, 0, s_))
        bb.append((i, bst, 0xC0000005 if bst else 0, b_))
    rb = compare(man1, ({"label": "SELFTEST"}, vb), ({}, sb), ({}, pb), bochs=({}, bb))
    verdicts = sorted(d["verdict"] for d in rb["disagreements"])
    if verdicts != ["Bochs differs", "table bug"]:
        fails.append("Bochs path verdicts %s" % verdicts)
    if (rb["bochs_differs"], rb["bochs_anomalies"], rb["bochs_mismatch_executions"]) != (1, 1, 2):
        fails.append("Bochs counters %s" % [rb["bochs_differs"], rb["bochs_anomalies"], rb["bochs_mismatch_executions"]])
    if rb["lane_mismatches"] != 1 or rb["harness_anomalies"] != 0:
        fails.append("Bochs path table/silicon counts %s %s" % (rb["lane_mismatches"], rb["harness_anomalies"]))
    # provenance: a results file of another vectors file (swapped hash) or with shuffled indices must be refused
    hdr_ok = {"vectors_sha256": "a" * 64, "manifest": "b" * 64}
    for label, sinfo, srecs in (("swapped vectors hash", {"vectors_sha256": "c" * 64, "manifest": "b" * 64}, sb),
                                ("swapped manifest hash", {"vectors_sha256": "a" * 64, "manifest": "d" * 64}, sb),
                                ("shuffled indices", hdr_ok, [sb[1], sb[0]] + sb[2:]),
                                ("short file", hdr_ok, sb[:-1])):
        try:
            compare(man1, ({"label": "SELFTEST", "manifest": "b" * 64}, vb), (sinfo, srecs), (hdr_ok, pb),
                    vectors_sha="a" * 64, manifest_sha="b" * 64)
            fails.append("provenance check missed: %s" % label)
        except ProvenanceError:
            pass
    try:
        compare(man1, ({"label": "SELFTEST", "manifest": "b" * 64}, vb), (hdr_ok, sb), (hdr_ok, pb),
                vectors_sha="a" * 64, manifest_sha="b" * 64)
    except ProvenanceError as e:
        fails.append("provenance check refused matching files: %s" % e)
    # a preset sticky flag in a vector is an anomaly outside VALID sets
    vs = [({"stub": 0, "flags": 0, "set": 7, "class": 0, "env": 0, "lane": 0xFFFFFFFF, "n_lane_cases": 16, "index": 0},
           vecfmt.Case(mxcsr=0x1F81))]
    o1 = [(0, 0, 0, vecfmt.Out(dst=5, mxcsr=0x1F81))]
    if compare(man1, ({"label": "DEV-X"}, vs), ({}, o1), ({}, o1))["harness_anomalies"] != 1:
        fails.append("preset sticky flag not reported as an anomaly")
    if compare(man1, ({"label": "VALID-X"}, vs), ({}, o1), ({}, o1))["harness_anomalies"] != 0:
        fails.append("preset sticky flag reported for a VALID set")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--manifest")
    ap.add_argument("--vectors")
    ap.add_argument("--silicon")
    ap.add_argument("--silicon2")
    ap.add_argument("--pred")
    ap.add_argument("--pyref")
    ap.add_argument("--bochs")
    ap.add_argument("--classes")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.selftest:
        f = selftest()
        for x in f:
            print("FAIL", x)
        print("compare selftest: %s (%d failures)" % ("FAIL" if f else "PASS", len(f)))
        return 1 if f else 0
    with open(a.manifest, "rb") as f:
        mraw = f.read()
    man = json.loads(mraw)
    manifest_sha = hashlib.sha256(mraw).hexdigest()
    vectors_sha = vecfmt.file_sha256(a.vectors)
    rep = compare(man, vecfmt.read_vectors(a.vectors), vecfmt.read_results(a.silicon), vecfmt.read_results(a.pred),
                  vecfmt.read_results(a.pyref) if a.pyref else None,
                  vecfmt.read_results(a.silicon2) if a.silicon2 else None,
                  vecfmt.read_results(a.bochs) if a.bochs else None,
                  json.load(open(a.classes)) if a.classes else None,
                  vectors_sha=vectors_sha, manifest_sha=manifest_sha)
    rep["inputs"] = {k: (vecfmt.file_sha256(getattr(a, k)) if getattr(a, k) else None)
                     for k in ("vectors", "silicon", "silicon2", "pred", "pyref", "bochs")}
    rep["inputs"]["manifest"] = manifest_sha
    with open(a.out, "w") as f:
        json.dump(rep, f, indent=1)
    keys = ["records", "lane_cases", "cells", "cells_with_mismatch", "lane_mismatches", "flag_mismatch_executions",
            "interpreter_divergences", "nondeterminism", "harness_anomalies"]
    if a.bochs:
        keys += ["bochs_mismatch_executions", "bochs_differs", "bochs_anomalies"]
    print(json.dumps({k: rep[k] for k in keys}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
