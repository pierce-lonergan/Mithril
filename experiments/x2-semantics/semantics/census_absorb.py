"""Absorb X0's census into a table-coverage report and the fuzz budget (TABLE-SCHEMA.md §9).

Primary input (the census of record, X0-census.md Appendix C):
  census.json         variants[]: {config, table, slot, symbol, closure: [{symbol, ...}], iforms: {iform: n}}
  instructions.jsonl  one record per decoded instruction: {label, object, function, iclass, iform,
                      fields: {MASK, ZEROING, ROUNDC, SAE, BCAST, ...}, attributes, padding}
The union is taken over the variants[] of the selected configurations only (the dispatched closures,
not whole objects), and every (iclass, iform) is split by OPERAND VARIANT read from the XED fields:
  plain | merge | zeroing | bcast | sae | er:ROUNDC=<v>   (joined with '+', e.g. 'bcast+merge')
A join cross-check refuses the input if the iforms found in instructions.jsonl for a configuration's
closure symbols differ from the iforms census.json lists for that configuration's variants.

Legacy input (X0 smoke runs, which have no census.json): functions.json, whole objects, no operand
variants. It is reported as such and never used for the verdict.

Output buckets for the union:
  covered_exact          an entry with exactly this (iclass, iform) exists
  needs_form_instance    the iclass's family is in the table but not this iform: add an entry
                         instance (same lane function, new operand shape) and fuzz it
  needs_family           no entry for the iclass at all: write one (SDM), classify FP sensitivity,
                         and give it a nan_role (default observer)
  operand_variants_seen  (iclass, iform, operand variant, count): feeds the fuzz budget (V3/V4/BCAST)
  provisional_unseen     provisional iform strings in the table that the census never produced
  xed_mxcsr_disagree     FP-sensitivity of our family vs XED's MXCSR attribute, listed both ways
  entries_without_nan_role  table entries lacking a nan_role (RULES.md §2: they count as observers)
The script refuses input whose shape it does not recognise and labels that match nothing (it never
guesses).

Run:  python -B -m semantics.census_absorb --census census.json --insts instructions.jsonl [--configs A,D]
                                           [--label-map A=A-msvc,D=D-clang] [-o out.json] [--budget]
      python -B -m semantics.census_absorb --functions f1.json [f2.json ...] [--labels A-msvc,D-clang]
      python -B -m semantics.census_absorb --selftest
"""
import argparse
import collections
import json
import os
import sys
import tempfile

from . import table

# Data-movement / bitwise / integer iclasses whose semantics are FP-insensitive by construction.
# Membership here is a CLASSIFICATION, not an entry: each still needs a table entry before T1 may
# accept code that uses it. Extend only with an SDM reason.
NON_FP_KNOWN = {
    # moves, loads, stores, broadcasts, inserts, extracts
    "VMOVUPS", "VMOVAPS", "VMOVDQU", "VMOVDQU8", "VMOVDQU16", "VMOVDQU32", "VMOVDQU64", "VMOVDQA",
    "VMOVDQA32", "VMOVDQA64", "VMOVSS", "VMOVD", "VMOVQ", "MOVSS", "MOVD", "MOVQ", "MOVAPS", "MOVUPS",
    "VMASKMOVPS", "VBROADCASTSS", "VPBROADCASTD", "VPBROADCASTW", "VPBROADCASTB", "VPBROADCASTQ",
    "VBROADCASTI32X4", "VBROADCASTI128", "VEXTRACTF128", "VEXTRACTI128", "VEXTRACTF64X4",
    "VEXTRACTI64X4", "VEXTRACTF32X8", "VEXTRACTI32X8", "VINSERTI128", "VINSERTF128", "VINSERTI64X4",
    "VINSERTF64X4", "VPINSRQ", "VPINSRD", "VMOVHLPS", "MOVHLPS", "VMOVLHPS",
    # shuffles, permutes, unpacks, blends
    "VPSHUFD", "VSHUFPS", "SHUFPS", "VPERMD", "VPERMPS", "VPERM2I128", "VPERM2F128", "VPERMQ",
    "VPUNPCKLDQ", "VPUNPCKHDQ", "VPUNPCKLQDQ", "VPUNPCKHQDQ", "VSHUFI64X2", "VSHUFI32X4",
    "VSHUFF64X2", "VBLENDVPS", "BLENDVPS", "VBLENDMPS", "VPBLENDMD", "VPBLENDD", "VPERMILPS",
    # bitwise
    "VPAND", "VPANDD", "VPANDQ", "VPANDN", "VPANDND", "VPOR", "VPORD", "VPXOR", "VPXORD", "VPXORQ",
    "VANDPS", "VANDNPS", "VORPS", "VXORPS", "ANDPS", "ANDNPS", "ORPS", "XORPS", "VPTERNLOGD",
    # integer arithmetic, shifts, compares, narrowing, widening
    "VPADDD", "VPADDW", "VPADDB", "VPADDQ", "VPSUBD", "VPSUBW", "VPMADDUBSW", "VPMADDWD",
    "VPDPBUSD", "VPDPBUSDS", "VPHADDD", "VPABSB", "VPSIGNB", "VPCMPGTD", "VPCMPD", "VPSLLD",
    "VPSRLW", "VPSRLD", "VPSRAD", "VPACKSSDW", "VPACKSSWB", "VPMOVDB", "VPMOVSDB", "VPMOVZXWD",
    "VPMOVZXBW", "VPMOVSXBW",
    # opmask
    "KMOVW", "KMOVB", "KMOVD", "KMOVQ", "KORTESTW", "KANDW", "KORW", "KNOTW", "KXORW", "KSHIFTRW",
}
# Instructions that read or write the FP environment itself (X0 §5 descriptive list).
FP_ENV_ICLASSES = {"LDMXCSR", "STMXCSR", "VLDMXCSR", "VSTMXCSR", "FLDCW", "FNSTCW", "FLDENV",
                   "FNSTENV", "FXRSTOR", "FXRSTOR64", "XRSTOR", "XRSTOR64", "XRSTORS", "FNINIT", "FNCLEX"}


def _nz(fields, k):
    v = fields.get(k)
    return v not in (None, "", "0", 0, False)


def operand_variant(fields):
    """Operand variant of one decoded instruction from XED's operand fields (x0_decode.py
    EVEX_FIELDS). ROUNDC values are kept raw: their mapping to RNE/RD/RU/RZ is read from XED at
    freeze [inference: 1..4 in that order, unverified]."""
    f = fields or {}
    tags = []
    if _nz(f, "BCAST"):
        tags.append("bcast")
    if _nz(f, "ROUNDC"):
        tags.append("er:ROUNDC=%s" % f["ROUNDC"])
    elif _nz(f, "SAE"):
        tags.append("sae")
    if _nz(f, "MASK"):
        tags.append("zeroing" if _nz(f, "ZEROING") else "merge")
    return "+".join(tags) or "plain"


def _rec(union, icl, ifm, attrs, isa_set, ext, n, where, variant=None):
    rec = union.setdefault((icl, ifm), {"count": 0, "functions": set(), "attributes": set(attrs or []),
                                        "isa_set": isa_set, "extension": ext, "variants": collections.Counter()})
    rec["count"] += n
    rec["functions"].add(where)
    if variant is not None:
        rec["variants"][variant] += n


def load_functions(paths, labels):
    """Legacy mode: X0 functions.json (whole objects). Labels must match exactly."""
    union, seen_labels = collections.OrderedDict(), set()
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list) or (data and "tuples" not in data[0]):
            raise SystemExit("%s: not an X0 functions.json (expected a list of functions with 'tuples')" % p)
        for fn in data:
            seen_labels.add(str(fn.get("label")))
            if labels and str(fn.get("label")) not in labels:
                continue
            for t in fn["tuples"]:
                if t.get("iclass"):
                    _rec(union, t["iclass"], t["iform"], t.get("attributes"), t.get("isa_set"), t.get("extension"),
                         t.get("count", 1), "%s:%s" % (fn.get("label"), fn.get("function")))
    if labels and not labels <= seen_labels:
        raise SystemExit("labels %s match no function (labels present: %s)" % (sorted(labels - seen_labels),
                                                                              sorted(seen_labels)))
    return union


def load_census(census_path, insts_paths, configs, label_map=None):
    """Census mode: closures of census.json variants[] joined with instructions.jsonl operand fields."""
    with open(census_path, encoding="utf-8") as fh:
        cen = json.load(fh)
    if not isinstance(cen, dict) or not isinstance(cen.get("variants"), list):
        raise SystemExit("%s: not an X0 census.json (expected an object with variants[])" % census_path)
    label_map = label_map or {}
    closure, iforms_cen = collections.defaultdict(set), collections.defaultdict(set)
    for v in cen["variants"]:
        if v.get("config") not in configs:
            continue
        for c in v.get("closure", []):
            closure[v["config"]].add(c["symbol"])
        iforms_cen[v["config"]].update(v.get("iforms", {}).keys())
    missing = [c for c in configs if c not in closure]
    if missing:
        raise SystemExit("configs %s have no variants in %s" % (missing, census_path))
    union = collections.OrderedDict()
    iforms_join = collections.defaultdict(set)
    label_to_cfg = {label_map.get(c, c): c for c in configs}
    for p in insts_paths:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                cfg = label_to_cfg.get(str(r.get("label")))
                if cfg is None or r.get("undecodable") or r.get("padding") or not r.get("iclass"):
                    continue
                if r.get("function") not in closure[cfg]:
                    continue
                iforms_join[cfg].add(r["iform"])
                _rec(union, r["iclass"], r["iform"], r.get("attributes"), r.get("isa_set"), r.get("extension"), 1,
                     "%s:%s" % (cfg, r.get("function")), operand_variant(r.get("fields")))
    for cfg in configs:
        if not iforms_join[cfg]:
            raise SystemExit("config %s: no instruction record matched its closure (label %r); "
                             "pass --label-map" % (cfg, label_map.get(cfg, cfg)))
        if iforms_join[cfg] != iforms_cen[cfg]:
            raise SystemExit("config %s: join mismatch; only in instructions.jsonl: %s; only in census.json: %s"
                             % (cfg, sorted(iforms_join[cfg] - iforms_cen[cfg])[:10],
                                sorted(iforms_cen[cfg] - iforms_join[cfg])[:10]))
    return union


def absorb(union, mode="census"):
    by_key = {(e["key"]["iclass"], e["key"]["iform"]): e for e in table.ENTRIES}
    fam_of_iclass = {}
    for e in table.ENTRIES:
        fam_of_iclass.setdefault(e["key"]["iclass"], set()).add(e["family"])
    rep = {"mode": mode, "covered_exact": [], "needs_form_instance": [], "needs_family": [],
           "operand_variants_seen": [], "fp_env_instructions": [], "xed_mxcsr_disagree": [],
           "provisional_unseen": [], "entries_without_nan_role": []}
    seen_iforms = set()
    for (icl, ifm), rec in union.items():
        seen_iforms.add(ifm)
        row = {"iclass": icl, "iform": ifm, "count": rec["count"], "n_functions": len(rec["functions"]),
               "xed_mxcsr": "MXCSR" in rec["attributes"], "isa_set": rec["isa_set"]}
        for var, n in sorted(rec["variants"].items()):
            rep["operand_variants_seen"].append({"iclass": icl, "iform": ifm, "variant": var, "count": n})
        if icl in FP_ENV_ICLASSES:
            rep["fp_env_instructions"].append(row)
        if (icl, ifm) in by_key:
            e = by_key[(icl, ifm)]
            row["family"] = e["family"]
            rep["covered_exact"].append(row)
            ours = e["fp_sensitive"]
        elif icl in fam_of_iclass:
            row["families"] = sorted(fam_of_iclass[icl])
            rep["needs_form_instance"].append(row)
            ours = any(x.startswith("FP.") for x in fam_of_iclass[icl])
        else:
            row["classification"] = "non-FP (known)" if icl in NON_FP_KNOWN else "UNCLASSIFIED: read the SDM"
            row["nan_role"] = "required when the entry is written (default: observer)"
            rep["needs_family"].append(row)
            ours = None if icl not in NON_FP_KNOWN else False
        if ours is not None and ours != row["xed_mxcsr"]:
            rep["xed_mxcsr_disagree"].append({"iclass": icl, "iform": ifm, "table_fp_sensitive": ours,
                                              "xed_MXCSR_attribute": row["xed_mxcsr"]})
    for e in table.ENTRIES:
        if e["key"]["iform_status"] == "provisional" and e["key"]["iform"] not in seen_iforms:
            rep["provisional_unseen"].append(e["key"]["iform"])
        if "nan_role" not in e:
            rep["entries_without_nan_role"].append(e["key"]["iform"])
    rep["summary"] = {k: len(v) for k, v in rep.items() if isinstance(v, list)}
    rep["summary"]["union_size"] = len(union)
    fp_fams = set()
    for row in rep["covered_exact"]:
        if row["family"].startswith("FP."):
            fp_fams.add(row["family"])
    for row in rep["needs_form_instance"]:
        fp_fams.update(f for f in row["families"] if f.startswith("FP."))
    rep["summary"]["fp_operation_classes_seen"] = sorted(fp_fams)
    return rep


# ---------------------------------------------------------------- the fuzz budget (FUZZ-DESIGN.md §5)
E8 = ["default", "RD", "RU", "RZ", "DAZ", "FTZ", "DAZ+FTZ", "RD+FTZ"]
_V2 = {"FP.ADD.f32": ["TIE", "OVF", "UFL", "CANCEL", "ZEROS", "F-FTZ-EXACT", "F-FLAGPRI"],
       "FP.SUB.f32": ["TIE", "OVF", "UFL", "CANCEL", "ZEROS", "F-FTZ-EXACT", "F-FLAGPRI"],
       "FP.MUL.f32": ["TIE", "OVF", "F-TINY", "UFL", "ZEROS", "F-FTZ-EXACT", "F-FLAGPRI"],
       "FP.DIV.f32": ["TIE", "OVF", "F-TINY", "UFL", "ZEROS", "F-FTZ-EXACT", "F-FLAGPRI"],
       "FP.MAX.f32": ["ZEROS", "F-DAZ-SEL", "F-FLAGPRI"], "FP.MIN.f32": ["ZEROS", "F-DAZ-SEL", "F-FLAGPRI"],
       "FP.CMP.f32": ["ZEROS", "F-FLAGPRI"], "FP.COMI.f32": ["ZEROS", "F-FLAGPRI"],
       "FP.CVT.i32_f32": ["CVT-BND"], "FP.CVT.f32_i32.rc": ["CVT-BND", "F-DAZ-CVT"],
       "FP.CVT.f32_i32.trunc": ["CVT-BND", "F-DAZ-CVT"], "FP.CVT.f16_f32": ["F-H2F"]}


def budget_rows(entries=None, variants_seen=None):
    """budget.v1 rows: (iform, operand variant, set, class, envs, lane cases). Formulas are those of
    FUZZ-DESIGN.md §5; every count is in LANE CASES. variants_seen: {(iclass, iform): {variant}} from
    a census absorption; without it, every EVEX memory form with a broadcast-capable operand gets a
    BCAST row and register forms get 'plain' only."""
    rows = []
    for e in entries or table.ENTRIES:
        ifm, fam, n = e["key"]["iform"], e["family"], e["lanes"]
        evex, mem = e["encoding"] == "evex", any(o["kind"] == "mem" for o in e["operands"])
        bcast = any(o.get("broadcast") for o in e["operands"])
        add = lambda s, c, envs, cases: rows.append(
            {"iform": ifm, "family": fam, "set": s, "class": c, "envs": envs, "lane_cases": cases})
        if fam.startswith("FP.") and fam not in ("FP.CMP.f32", "FP.COMI.f32") and "CVT" not in fam:
            add("V1", "class-pair grid 144 x 1000", "E8", 144 * 1000 * 8)
            for c in _V2[fam]:
                add("V2", c, "E8", 10000 * 8)
        elif fam in ("FP.CMP.f32", "FP.COMI.f32"):
            npred = 32 if (fam == "FP.CMP.f32" and e["encoding"] != "legacy") else (8 if fam == "FP.CMP.f32" else 1)
            add("V1", "class-pair grid 144 x 1000 x %d predicates" % npred, "E8", 144 * 1000 * 8 * npred)
            for c in _V2[fam]:
                add("V2", c, "E8", 10000 * 8 * npred)
        elif "CVT" in fam:
            add("V1", "12 classes x 1000", "E8", 12 * 1000 * 8)
            for c in _V2[fam]:
                add("V2", c, "E8", 10000 * 8)
            if fam == "FP.CVT.f16_f32":
                add("V5", "all 2^16 inputs", "E8", (1 << 16) * 8)
            elif fam == "FP.CVT.i32_f32":
                add("V5", "all 2^32 inputs", "4 RC", (1 << 32) * 4)
            else:
                add("V5", "all 2^32 inputs", "4 RC x DAZ{0,1}", (1 << 32) * 8)
        else:                                                        # integer entries
            add("V1", "SS3.5 classes x 100000", "default", 100000)
            add("V2", "wrap/saturation boundaries x 10000", "default", 10000)
            if fam == "INT.MADDUBS.u8s8":
                add("V5", "pair domain u8^2 x s8^2", "default", 1 << 32)
        if evex and n > 1:
            if n <= 16:
                per = (1 << n) * (1 if e["masking"] == ["zero(k-dest)"] else 2) * 4 * n
                add("V3", "all %d masks x %s x 4 rotations" % (1 << n, "zero" if e["masking"] == ["zero(k-dest)"]
                                                                else "{merge,zero}"), "default", per)
            else:
                nm = 2 + 2 * n + 4 + n + 4096                           # all-0, all-1, single bit/zero, alt., prefixes, random
                add("V3", "structured %d masks x {merge,zero} x 4 rotations" % nm, "default", nm * 2 * 4 * n)
        if evex and n == 1 and fam.startswith("FP."):
            add("V3", "mask bit 0 x {merge,zero} x 4 rotations", "default", 2 * 2 * 4)
        er = evex and not mem and ((e["vl"] == 512 and n > 1) or n == 1) and fam in (
            "FP.ADD.f32", "FP.SUB.f32", "FP.MUL.f32", "FP.DIV.f32", "FP.CVT.i32_f32", "FP.CVT.f32_i32.rc")
        if er:
            add("V4", "{er} 4 modes x 144 x 100" if "CVT" not in fam else "{er} 4 modes x 12 x 100",
                "{DAZ=FTZ=0, DAZ=FTZ=1}", 4 * (144 if "CVT" not in fam else 12) * 100 * 2)
        if mem:
            add("F-MEMFAULT", "prefix masks 0..n on a PAGE_NOACCESS boundary" if evex else "page-boundary load",
                "default", (n + 1) * n if evex else n)
            vs = (variants_seen or {}).get((e["key"]["iclass"], ifm))
            if bcast and (vs is None or any("bcast" in v for v in vs)):
                add("BCAST", "{1to%d} x 144 x 100" % n, "default", 144 * 100 * n)
    return rows


def budget_summary(rows):
    tot = collections.Counter()
    for r in rows:
        tot[r["set"]] += r["lane_cases"]
    return {"by_set": dict(tot), "total": sum(tot.values()), "rows": len(rows)}


# ---------------------------------------------------------------- self-test
def _selftest(smoke_dir=None):
    """(1) synthetic census.json + instructions.jsonl: closure join, operand variants, refusal of a
    join mismatch and of an unmatched label; (2) legacy functions.json; (3) if X0's smoke outputs are
    present, the keys verified by them are covered_exact."""
    checks = {}
    cen = {"variants": [
        {"config": "A", "symbol": "act_q8_avx512", "closure": [{"symbol": "act_q8_avx512"}],
         "iforms": {"VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512": 2, "VADDPS_ZMMf32_MASKmskw_ZMMf32_MEMf32_AVX512": 1,
                    "VPTERNLOGD_ZMMu32_MASKmskw_ZMMu32_ZMMu32_IMM8_AVX512": 1, "VSQRTSS_XMMdq_XMMdq_XMMd": 1,
                    "LDMXCSR_MEMd": 1}},
        {"config": "B-cmake", "symbol": "x", "closure": [{"symbol": "x"}], "iforms": {"NOP": 1}}]}
    insts = [
        {"label": "A", "function": "act_q8_avx512", "iclass": "VADDPS", "iform": "VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512",
         "fields": {"MASK": "1", "ZEROING": "1"}, "attributes": ["MXCSR"], "isa_set": "AVX512F_512"},
        {"label": "A", "function": "act_q8_avx512", "iclass": "VADDPS", "iform": "VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512",
         "fields": {"ROUNDC": "2"}, "attributes": ["MXCSR"], "isa_set": "AVX512F_512"},
        {"label": "A", "function": "act_q8_avx512", "iclass": "VADDPS", "iform": "VADDPS_ZMMf32_MASKmskw_ZMMf32_MEMf32_AVX512",
         "fields": {"BCAST": "1"}, "attributes": ["MXCSR"], "isa_set": "AVX512F_512"},
        {"label": "A", "function": "act_q8_avx512", "iclass": "VPTERNLOGD",
         "iform": "VPTERNLOGD_ZMMu32_MASKmskw_ZMMu32_ZMMu32_IMM8_AVX512", "fields": {}, "attributes": []},
        {"label": "A", "function": "act_q8_avx512", "iclass": "VSQRTSS", "iform": "VSQRTSS_XMMdq_XMMdq_XMMd",
         "fields": {}, "attributes": ["MXCSR"]},
        {"label": "A", "function": "act_q8_avx512", "iclass": "LDMXCSR", "iform": "LDMXCSR_MEMd", "fields": {}},
        {"label": "A", "function": "not_in_closure", "iclass": "VMULPS", "iform": "VMULPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512"},
        {"label": "A", "function": "act_q8_avx512", "iclass": "NOP", "iform": "NOP", "padding": True}]
    d = tempfile.mkdtemp(prefix="x2_absorb_")
    cp, ip = os.path.join(d, "census.json"), os.path.join(d, "instructions.jsonl")
    try:
        with open(cp, "w") as fh:
            json.dump(cen, fh)
        with open(ip, "w") as fh:
            fh.write("\n".join(json.dumps(r) for r in insts) + "\n")
        rep = absorb(load_census(cp, [ip], ["A"]))
        s = rep["summary"]
        vs = {(r["iform"].split("_")[4] if r["iclass"] == "VADDPS" else r["iclass"], r["variant"])
              for r in rep["operand_variants_seen"]}
        checks["census: buckets"] = (s["covered_exact"] == 2 and s["needs_family"] == 3 and s["fp_env_instructions"] == 1
                                     and s["union_size"] == 5)
        checks["census: closure excludes other functions"] = all(r["iclass"] != "VMULPS" for r in rep["covered_exact"])
        checks["census: operand variants"] = {("ZMMf32", "merge"), ("ZMMf32", "er:ROUNDC=2"), ("ZMMf32", "zeroing")} & vs \
            == {("ZMMf32", "zeroing"), ("ZMMf32", "er:ROUNDC=2")} and ("MEMf32", "bcast") in vs
        checks["census: VSQRTSS unclassified"] = any(r["iclass"] == "VSQRTSS" and r["classification"].startswith("UNCLASSIFIED")
                                                     for r in rep["needs_family"])
        try:
            load_census(cp, [ip], ["A"], {"A": "A-msvc"})
            checks["census: unmatched label refused"] = False
        except SystemExit:
            checks["census: unmatched label refused"] = True
        cen["variants"][0]["iforms"]["VEXTRA_IFORM"] = 1
        with open(cp, "w") as fh:
            json.dump(cen, fh)
        try:
            load_census(cp, [ip], ["A"])
            checks["census: join mismatch refused"] = False
        except SystemExit:
            checks["census: join mismatch refused"] = True
        fake = [{"label": "A-msvc", "function": "f", "tuples": [
            {"iclass": "VADDPS", "iform": "VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512", "attributes": ["MXCSR"], "count": 3},
            {"iclass": "VADDPS", "iform": "VADDPS_ZMMf32_MASKmskw_ZMMf32_MEMf32_AVX512", "attributes": ["MXCSR"], "count": 1},
            {"iclass": "VADDPS", "iform": "VADDPS_YMMf32_MASKmskw_YMMf32_MEMf32_AVX512", "attributes": ["MXCSR"], "count": 1}]}]
        fp = os.path.join(d, "functions.json")
        with open(fp, "w") as fh:
            json.dump(fake, fh)
        rep2 = absorb(load_functions([fp], {"A-msvc"}), mode="legacy-functions")
        checks["legacy: buckets"] = rep2["summary"]["covered_exact"] == 2 and rep2["summary"]["needs_form_instance"] == 1
        try:
            load_functions([fp], {"A"})
            checks["legacy: label 'A' does not match 'A-msvc'"] = False
        except SystemExit:
            checks["legacy: label 'A' does not match 'A-msvc'"] = True
    finally:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
        os.rmdir(d)
    smoke = smoke_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                      "x0-census", "scripts", "smoke", "results")
    paths = [os.path.join(smoke, c, "functions.json") for c in ("A-msvc", "B-clangcl", "C-gcc", "D-clang")]
    if all(os.path.exists(p) for p in paths):
        rep3 = absorb(load_functions(paths, None), mode="legacy-functions")
        cov = {r["iform"] for r in rep3["covered_exact"]}
        checks["smoke: xed-decode keys covered"] = {e["key"]["iform"] for e in table.ENTRIES
                                                    if e["key"]["iform_status"] == "xed-decode"} <= cov
    else:
        checks["smoke: outputs absent (skipped)"] = True
    return all(checks.values()), checks


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--census")
    ap.add_argument("--insts", nargs="*", default=[])
    ap.add_argument("--configs", default="A,D")
    ap.add_argument("--label-map", default="")
    ap.add_argument("--functions", nargs="*", default=[])
    ap.add_argument("--labels", default="")
    ap.add_argument("--budget", action="store_true")
    ap.add_argument("-o", "--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest or not (a.census or a.functions or a.budget):
        ok, checks = _selftest()
        print("census_absorb selftest:", "ok" if ok else "FAILED", json.dumps(checks))
        return 0 if ok else 1
    if a.census:
        lm = dict(x.split("=", 1) for x in a.label_map.split(",") if x)
        union = load_census(a.census, a.insts, [c for c in a.configs.split(",") if c], lm)
        rep = absorb(union)
    elif a.functions:
        rep = absorb(load_functions(a.functions, set(a.labels.split(",")) if a.labels else None), mode="legacy-functions")
    else:
        rep = {"summary": {}}
    if a.budget:
        vs = collections.defaultdict(set)
        for r in rep.get("operand_variants_seen", []):
            vs[(r["iclass"], r["iform"])].add(r["variant"])
        rows = budget_rows(variants_seen=vs or None)
        rep["budget_v1"] = {"rows": rows, "summary": budget_summary(rows)}
        rep["summary"]["budget_v1"] = rep["budget_v1"]["summary"]
    txt = json.dumps(rep, indent=1, default=sorted)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(txt)
    print(json.dumps(rep["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
