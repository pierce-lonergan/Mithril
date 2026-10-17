#!/usr/bin/env python3
"""x0_census.py -- the census.json assembler (record Appendix C, with the x0prep fields judge.py reads).

Usage:
  python -I x0_census.py --run RUN_DIR -o census.json [--class-dir ../class] [--xml x86-intel.xml]
         [--freeze-commit SHA] [--scripts-commit SHA] [--qualify-tables]

RUN_DIR is written by x0_driver.py (one directory per configuration):
  RUN_DIR/run.json                         run id, kind (census | smoke), times, host, Hearth commit and blobs,
                                           the SHA-256 of every script listed in class/frozen_inputs.json "scripts"
                                           as the run used them
  RUN_DIR/<CFG>/config.json                role, generator, host, ABI, compiler, headers, census files, effective
                                           flags and the P3(a) result per file, the steps run and their status
  RUN_DIR/<CFG>/builds/<file>.b<k>.json    build records (x0_build.py), build_index 1 and 2
  RUN_DIR/<CFG>/twin/<file>.twin.json      the debug-info twin's build record
  RUN_DIR/<CFG>/b<k>/<unit>/unit.json      the census files of one extraction unit and their objects
  RUN_DIR/<CFG>/b<k>/<unit>/manifest.json  x0_extract.py
  RUN_DIR/<CFG>/b<k>/<unit>/decode/        x0_decode.py (variants.json, crossdecoder.json, summary.json)
  RUN_DIR/<CFG>/b<k>/<unit>/loops.json     x0_loops.py (with the x0_twin.py attribution)

What it computes itself (everything else is copied from the stage outputs, which keep their own hashes):
  * configs.<cfg>.objects (build 1) and objects_build2: object SHA-256, source git blob SHA-1, and per executable
    section the SHA-256 of its bytes and of its relocation list;
  * configs.<cfg>.repro (record §6): build 1 against build 2, per file and section (bytes and relocations);
  * A versus A-ninja (record §2): per file the same comparison (configs["A-ninja"].ab_compare_files), and per
    A-ninja variant `ab_compare` = identical iff A has the same variant in the same build with the same entry
    symbol and every closure section of the A-ninja variant has an identical partner in A's object (paired by
    section name plus function symbols, as for the twin); `union_member` = (ab_compare == differs);
  * variants[].p3: a1/a2 from the configuration's P3(a) result for the variant's file; b = approximation
    iclasses of the counted set (judge.py's list); c, d1, d2 from x0_loops.py;
  * metrics: P1 (gap counts per configuration and cause), P2, P3 flags, P4 |U_all| and P5_iclass over the main
    union (A, B-cmake, C, D, and A-ninja variants with union_member) with judge.py's rules, and the secondary
    metrics that need no new tooling (|U_all^S| through xed_tables.tsv's iform extension, |U_all^SIMD|,
    |U_all^SIMD,S|, |U_release|, iform sets per configuration, P5_opclass from fp_class.csv, the raw delta against
    B_iform, EVEX static-rounding counts, FP-environment iclasses in the counted sets, external calls).
Not computed here and listed in `notes`: the operand-normalised delta against B_iform, |U_object| (arm S-object)
and |U_helpers| (arm S-helpers), operand order (§5 descriptive), the proxy-fidelity metric (needs the B-proxy arm)
and the reduce-probe lane pairing beyond the iclass sequences. judge.py recomputes every gate figure itself.
The result is checked against the Appendix C shape (judge.validate_schema plus the stricter checks below) and the
script exits 1 if it does not conform. rederivation is written as {present: false} until the independent
re-derivation (rederive/PROCEDURE.md) fills it, so judge.py's V3 fails until then, as the record requires.
Standard library only; Python >= 3.8. Run with python -I.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import judge  # noqa: E402
import x0obj  # noqa: E402
import x0_twin  # noqa: E402

MAIN = ("A", "B-cmake", "C", "D")
ROLE = {"A": "release", "D": "release", "B-cmake": "union", "C": "union", "A-ninja": "union"}
S_EXT = {"SSE", "SSE2", "SSE3", "SSSE3", "SSE4", "AVX", "AVX2", "AVX2GATHER", "FMA", "F16C", "AVX512EVEX", "AVX512VEX"}
FP_ENV = {"LDMXCSR", "STMXCSR", "VLDMXCSR", "VSTMXCSR", "FLDCW", "FNSTCW", "FLDENV", "FNSTENV", "FRSTOR", "FNSAVE",
          "FXRSTOR", "FXRSTOR64", "XRSTOR", "XRSTOR64", "XRSTORS", "XRSTORS64", "FNINIT", "FNCLEX"}
VARIANT_KEEP = ("symbol", "source_function", "slot_name_check", "closure", "coverage", "n_instructions", "iforms",
                "iclasses", "categories", "fp_sensitive", "fp_sensitive_missing_from_fp_class", "p2_fma",
                "evex_static_rounding", "lift_blockers", "jump_tables", "unreachable", "sweep_crosscheck",
                "crossdecoder_disagreements")


def localpath(p):
    """A path recorded on the other side of the desktop's Windows/WSL boundary, as this side sees it
    (drive path <-> /mnt/<drive>/...). Other paths are returned unchanged."""
    if not isinstance(p, str):
        return p
    if os.name == "nt":
        m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", p)
        return (m.group(1).upper() + ":" + os.sep + m.group(2).replace("/", os.sep)) if m else p
    m = re.match(r"^([a-zA-Z]):[\\/](.*)$", p)
    return ("/mnt/%s/%s" % (m.group(1).lower(), m.group(2).replace(chr(92), "/"))) if m else p


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def object_record(path, source=None):
    o = x0obj.parse_object(path)
    rel = x0_twin.x0_extract.resolve_relocs(o)
    secs = []
    for c in x0_twin.code_sections(o):
        s = o["sections"][c["index"]]
        b = x0_twin._sec_bytes(o, s)
        secs.append({"name": c["name"], "key": c["key"], "index": c["index"], "size": c["size"],
                     "bytes_sha256": hashlib.sha256(b).hexdigest(),
                     "relocs_sha256": hashlib.sha256(json.dumps(x0_twin.reloc_list(rel, c["index"])).encode()).hexdigest()})
    rec = {"object": os.path.abspath(path), "object_sha256": hashlib.sha256(o["data"]).hexdigest(), "format": o["format"],
           "code_sections": secs}
    if source and os.path.exists(source):
        rec["source"] = os.path.abspath(source)
        rec["source_blob_sha1"] = x0_twin.x0_extract.git_blob_sha1(open(source, "rb").read())
    return rec


def compare_objects(pa, pb):
    """Section-by-section comparison (bytes and relocation list) of two objects; x0_twin's pairing."""
    ident, _ = x0_twin.identity(x0obj.parse_object(pa), x0obj.parse_object(pb))
    return ident


def iform_extension(class_dir):
    ext = {}
    with open(os.path.join(class_dir, "xed_tables.tsv"), encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if p[0] == "IFORM" and len(p) >= 5:
                ext[p[1]] = p[4]
    return ext


def load_fp_class(class_dir):
    with open(os.path.join(class_dir, "fp_class.csv"), encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["iclass"]: r["fp_sensitive"] == "yes" for r in rows}, {r["iclass"]: r["op_class"] for r in rows}


def proxy_fidelity(variants):
    """Record §5 secondary 'proxy fidelity': per variant and build, the Jaccard index of the iform sets of B-proxy
    and D, and the agreement of their loop tag multisets (fraction of D's tags that B-proxy also has)."""
    d = {(v["table"], v["slot"], v["build_index"]): v for v in variants if v["config"] == "D"}
    out = {}
    for v in variants:
        if v["config"] != "B-proxy":
            continue
        w = d.get((v["table"], v["slot"], v["build_index"]))
        if w is None:
            continue
        a, b = set(v.get("iforms") or {}), set(w.get("iforms") or {})
        ta = collections.Counter(t for lp in v.get("loops") or [] for t in lp.get("tags") or [])
        tb = collections.Counter(t for lp in w.get("loops") or [] for t in lp.get("tags") or [])
        out["%s:%s|b%d" % (v["table"], v["slot"], v["build_index"])] = {
            "jaccard_iforms": round(len(a & b) / len(a | b), 4) if a | b else None,
            "tag_agreement": round(sum((ta & tb).values()) / sum(tb.values()), 4) if tb else None}
    return out


def schema_check(c):
    """judge.validate_schema plus the Appendix C fields judge.py does not read but the record requires."""
    bad = judge.validate_schema(c)
    for k in ("baseline", "metrics"):
        if not isinstance(c.get(k), dict):
            bad.append("%s missing or not an object" % k)
    for name, cfg in (c.get("configs") or {}).items():
        for k in ("role", "compiler", "effective_flags", "objects", "p3a"):
            if k not in cfg:
                bad.append("configs.%s.%s missing" % (name, k))
    for i, v in enumerate(c.get("variants") or []):
        for k in ("file", "coverage", "p3"):
            if k not in v:
                bad.append("variants[%d].%s missing" % (i, k))
        if v.get("config") == "A-ninja" and v.get("ab_compare") not in ("identical", "differs"):
            bad.append("variants[%d] (A-ninja) has no ab_compare" % i)
    for i, b in enumerate(c.get("builds") or []):
        for k in ("compiler_ran", "compiler_sha256", "argv_sha256", "argv_matches_frozen", "errors", "includes", "ice"):
            if k not in b:
                bad.append("builds[%d].%s missing" % (i, k))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--class-dir", default=os.path.join(HERE, "..", "class"))
    ap.add_argument("--xml", help="the stdarch x86-intel.xml the run used (its SHA-256 goes into record.sha256.xml)")
    ap.add_argument("--freeze-commit")
    ap.add_argument("--scripts-commit")
    ap.add_argument("--qualify-tables", action="store_true",
                    help="regression profile: table names become TABLE@FILE (several census files share table names)")
    a = ap.parse_args()
    run = load(os.path.join(a.run, "run.json"), {})
    cdir = a.class_dir
    pins = load(os.path.join(cdir, "frozen_inputs.json"), {})
    rec_sha = {key: sha256(os.path.join(cdir, name)) for name, key in judge.FROZEN.items()}
    rec_sha["xml"] = sha256(a.xml) if a.xml else None
    # x0final revision: the freeze commit comes from the init step (x0_driver.py init checks the clean checkout of
    # the FROZEN record and writes HEAD to run.json); an explicit --freeze-commit must agree with it
    fc_run = run.get("freeze_commit")
    freeze_commit = a.freeze_commit or fc_run
    commit_notes = []
    if a.freeze_commit and fc_run and a.freeze_commit != fc_run:
        commit_notes.append("--freeze-commit %s differs from the init step's %s" % (a.freeze_commit, fc_run))
    census = {"record": {"id": "X0-census" if run.get("kind") == "census" else "X0-census-%s" % run.get("kind", "smoke"),
                         "freeze_commit": freeze_commit, "scripts_commit": a.scripts_commit or freeze_commit,
                         "sha256": rec_sha,
                         "scripts_sha256": run.get("scripts_sha256") or {}, "profile": run.get("profile"),
                         "mock": bool(run.get("mock")), "hearth_commit": run.get("hearth_commit"),
                         "source_blobs": run.get("source_blobs"), "assembled_utc": datetime.datetime.now(
                             datetime.timezone.utc).isoformat(timespec="seconds")},
              "runs": [], "configs": {}, "variants": [], "builds": [], "twin_builds": [],
              "crossdecoder": {"disagreements": []},
              "rederivation": {"present": False, "matches": False, "mismatches": [],
                               "note": "no independent re-derivation yet (record §7, rederive/PROCEDURE.md)"},
              "notes": []}
    fpc, opc = load_fp_class(cdir)
    iext = iform_extension(cdir)
    cfgs = sorted(d for d in os.listdir(a.run) if os.path.isfile(os.path.join(a.run, d, "config.json")))
    objects_by = {}                            # (cfg, build_index, file) -> object path
    for cfg in cfgs:
        root = os.path.join(a.run, cfg)
        cj = load(os.path.join(root, "config.json"))
        files = [f["id"] for f in cj.get("census_files", [])]
        ce = {"role": cj.get("role") or ROLE.get(cfg, "secondary"), "generator": cj.get("generator"),
              "host": cj.get("host"), "abi": cj.get("abi"), "mode": cj.get("mode"), "compiler": cj.get("compiler"),
              "headers": cj.get("headers"), "effective_flags": cj.get("effective_flags", {}),
              "p3a": {f: {"a1": list(x.get("a1", [])), "a2": list(x.get("a2", []))}
                      for f, x in (cj.get("p3a") or {}).items() if isinstance(x, dict) and "a1" in x},
              "p3a_hits": {f: x.get("hits") for f, x in (cj.get("p3a") or {}).items() if isinstance(x, dict)},
              "census_files": cj.get("census_files", []), "steps": cj.get("steps", []),
              "objects": {}, "objects_build2": {}, "repro": {}}
        census["configs"][cfg] = ce
        for st in cj.get("steps", []):
            if st.get("step") in ("build1", "build2") or str(st.get("step")).startswith("twin_"):
                twin = str(st["step"]).startswith("twin_")
                census["runs"].append({"run_id": run.get("run_id"), "utc": st.get("utc_end") or st.get("utc_start"),
                                       "kind": "twin" if twin else run.get("kind", "smoke"), "config": cfg,
                                       "build_index": 1 if (twin or st["step"] == "build1") else 2,
                                       "census_sha256": None, "rc": st.get("rc")})
        for bi in (1, 2):
            for f in files:
                p = os.path.join(root, "builds", "%s.b%d.json" % (f, bi))
                b = load(p)
                if b is None:
                    continue
                b = dict(b)
                b["file"] = f
                b["build_index"] = bi
                b["record_path"] = os.path.abspath(p)
                census["builds"].append(b)
                bobj = localpath(b.get("object"))
                if b.get("object_exists") and bobj and os.path.exists(bobj):
                    objects_by[(cfg, bi, f)] = bobj
                    try:
                        orec = object_record(bobj, localpath(b.get("source")))
                    except (ValueError, OSError, struct.error) as e:
                        orec = {"object": bobj, "error": str(e)}
                    ce["objects" if bi == 1 else "objects_build2"][f] = orec
        for f in files:
            tp = os.path.join(root, "twin", "%s.twin.json" % f)
            tw = load(tp)
            if tw is not None:
                census["twin_builds"].append(dict(tw, file=f, record_path=os.path.abspath(tp)))
        for f in files:                          # §6: build 1 against build 2
            p1, p2 = objects_by.get((cfg, 1, f)), objects_by.get((cfg, 2, f))
            if p1 and p2:
                ident = compare_objects(p1, p2)
                ce["repro"][f] = {"identical": ident["identical"],
                                  "differing_sections": [s["key"] for s in ident["sections"] if not s["identical"]],
                                  "only_in_build2": ident["twin_only_code_sections"]}
            else:
                ce["repro"][f] = {"identical": None, "detail": "an object is missing (build 1 %s, build 2 %s)" % (
                    bool(p1), bool(p2))}
    # variants
    approx_re = judge.APPROX_RE
    for cfg in cfgs:
        root = os.path.join(a.run, cfg)
        ce = census["configs"][cfg]
        for bi in (1, 2):
            bdir = os.path.join(root, "b%d" % bi)
            if not os.path.isdir(bdir):
                continue
            for unit in sorted(os.listdir(bdir)):
                udir = os.path.join(bdir, unit)
                uj = load(os.path.join(udir, "unit.json"))
                vj = load(os.path.join(udir, "decode", "variants.json"))
                if uj is None or vj is None:
                    continue
                file_of_obj = {os.path.basename(x["object"]): x["id"] for x in uj["files"]}
                lj = {("%s:%s" % (r["table"], r["slot"])): r for r in (load(os.path.join(udir, "loops.json")) or [])}
                xd = load(os.path.join(udir, "decode", "crossdecoder.json"), {"disagreements": []})
                for d in xd.get("disagreements", []):
                    d = dict(d)
                    d["build_index"] = bi
                    census["crossdecoder"]["disagreements"].append(d)
                for v in vj:
                    f = file_of_obj.get(v.get("object"))
                    table = v["table"] + ("@%s" % f if a.qualify_tables else "")
                    out = {"config": cfg, "table": table, "slot": v["slot"], "build_index": bi, "file": f,
                           "unit": unit, "object": v.get("object")}
                    for k in VARIANT_KEEP:
                        if k in v:
                            out[k] = v[k]
                    lr = lj.get("%s:%s" % (v["table"], v["slot"]))
                    p3a = ce["p3a"].get(f) or {}
                    out["p3"] = {"a1": list(p3a.get("a1", [])), "a2": list(p3a.get("a2", [])),
                                 "b": sorted(i for i in (v.get("iclasses") or {}) if approx_re.match(i or "")),
                                 "c": (lr or {}).get("p3", {}).get("c", []), "d2": (lr or {}).get("p3", {}).get("d2", [])}
                    if lr is not None and lr.get("key_is_canary"):
                        out["p3"]["d1"] = lr["p3"].get("d1")
                        out["p3"]["d1_sites"] = lr["p3"].get("d1_sites")
                    if lr is not None:
                        out["loops"] = lr.get("loops", [])
                        out["sequences"] = lr.get("sequences", [])
                        if "probe" in lr:                  # arm P: iclass sequence and lane pairing
                            out["probe"] = lr["probe"]
                        out["attribution"] = lr.get("attribution")
                        out["attribution_detail"] = lr.get("attribution_detail")
                    # x0final revision (record §4.6): attribution none (twin build failed, line table failed its
                    # self-checks, no loop analysis) disables P3(c)'s own bounds and every d2 site: a tooling gap
                    if cfg in judge.CHECKED and out.get("iforms") and out.get("attribution") not in ("exact", "approximate"):
                        out.setdefault("coverage", {}).setdefault("gaps", []).append(
                            {"cause": "other", "offset": None,
                             "detail": "twin attribution %s: %s" % (out.get("attribution"),
                                                                     out.get("attribution_detail") or "no loop analysis")})
                    out["operand_order"] = []
                    census["variants"].append(out)
    # A versus A-ninja (record §2)
    if "A-ninja" in census["configs"]:
        an = census["configs"]["A-ninja"]
        an["ab_compare_files"] = {}
        idents = {}
        for bi in (1, 2):
            for f in [x["id"] for x in an.get("census_files", [])]:
                pa, pn = objects_by.get(("A", bi, f)), objects_by.get(("A-ninja", bi, f))
                if pa and pn:
                    idents[(bi, f)] = (x0_twin.identity(x0obj.parse_object(pa), x0obj.parse_object(pn))[0])
                    if bi == 1:
                        an["ab_compare_files"][f] = {"identical": idents[(bi, f)]["identical"],
                                                     "differing_sections": [s["key"] for s in idents[(bi, f)]["sections"]
                                                                            if not s["identical"]]}
                else:
                    if bi == 1:
                        an["ab_compare_files"][f] = {"identical": None, "detail": "object missing (A %s, A-ninja %s)" % (
                            bool(pa), bool(pn))}
        av = {(v["table"], v["slot"], v["build_index"]): v for v in census["variants"] if v["config"] == "A"}
        for v in census["variants"]:
            if v["config"] != "A-ninja":
                continue
            twin = av.get((v["table"], v["slot"], v["build_index"]))
            why = None
            ident = idents.get((v["build_index"], v.get("file")))
            if twin is None:
                why = "A has no such variant in build %d" % v["build_index"]
            elif ident is None:
                why = "an object is missing"
            elif twin.get("symbol") != v.get("symbol"):
                why = "entry symbol %s in A, %s in A-ninja" % (twin.get("symbol"), v.get("symbol"))
            else:
                by_tidx = {s.get("twin_index"): s for s in ident["sections"]}
                secs = sorted({c["section_index"] for c in v.get("closure") or []})
                bad = [s for s in secs if not by_tidx.get(s, {}).get("identical")]
                if not secs:
                    why = "no closure"
                elif bad:
                    why = "closure sections %s of A-ninja differ from A" % bad
            v["ab_compare"] = "identical" if why is None else "differs"
            v["ab_compare_detail"] = why
            v["union_member"] = v["ab_compare"] == "differs"
    for v in census["variants"]:
        if v["config"] in MAIN:
            v["union_member"] = True
        elif v["config"] != "A-ninja":
            v["union_member"] = False
    # baseline
    bj = load(os.path.join(cdir, "B_iform.json"), {})
    bset = set(bj.get("b_iform", []))
    census["baseline"] = {"stdarch_commit": (bj.get("inputs") or {}).get("stdarch_commit"),
                          "xml_sha256": (bj.get("inputs") or {}).get("xml_sha256"),
                          "intrinsics": (bj.get("counts") or {}).get("intrinsics"),
                          "no_single_instruction": (bj.get("counts") or {}).get("no_single_instruction"),
                          "b_iform": len(bset), "b_mnem": len(bj.get("b_mnem", [])),
                          "t_forms": (bj.get("t_forms") or {}).get("value")}
    # metrics
    union = [v for v in census["variants"] if v.get("union_member")]
    u_all = set().union(*[set(v.get("iforms") or {}) for v in union]) if union else set()
    ic_all = set().union(*[set(v.get("iclasses") or {}) for v in union]) if union else set()
    fp_ic = {i for i in ic_all if fpc.get(i, True)}
    simd_tables = tuple(t for t in ("k_avx2", "k_avx512"))
    simd = [v for v in union if v["table"].split("@")[0] in simd_tables]
    u_simd = set().union(*[set(v.get("iforms") or {}) for v in simd]) if simd else set()
    u_simd_s = {i for i in u_simd if iext.get(i) in S_EXT}
    rel = [v for v in union if v["config"] in ("A", "D")]
    gaps = collections.defaultdict(collections.Counter)
    p2 = collections.Counter()
    p3 = collections.defaultdict(lambda: collections.Counter())
    for v in census["variants"]:
        for g in (v.get("coverage") or {}).get("gaps") or []:
            gaps[v["config"]][g.get("cause")] += 1
        if v.get("union_member"):
            p2[v["config"]] += max(int(v.get("p2_fma") or 0),
                                   sum(int(n) for i, n in (v.get("iclasses") or {}).items() if judge.FMA_RE.match(i or "")))
            q = v.get("p3") or {}
            p3[v["config"]]["b"] += bool(q.get("b"))
            p3[v["config"]]["c"] += bool(q.get("c"))
            p3[v["config"]]["d1_not_pass"] += ("d1" in q and q.get("d1") != "pass")
            p3[v["config"]]["d2_mismatch"] += any(s.get("result") == "mismatch" for s in q.get("d2") or [])
            p3[v["config"]]["d2_unchecked"] += sum(1 for s in q.get("d2") or [] if s.get("result") == "unchecked")
            p3[v["config"]]["d2_match"] += sum(1 for s in q.get("d2") or [] if s.get("result") == "match")
    census["metrics"] = {
        "p1": {c: dict(x) for c, x in sorted(gaps.items())},
        "p2": dict(p2),
        "p3": {c: dict(x, a_flagged_files=sorted(f for f, r in (census["configs"].get(c, {}).get("p3a") or {}).items()
                                                  if r.get("a1") or r.get("a2"))) for c, x in sorted(p3.items())},
        "p4_u_all": len(u_all), "p5_iclass": len(fp_ic),
        "secondary": {
            "u_all_S": len({i for i in u_all if iext.get(i) in S_EXT}),
            "u_all_simd": len(u_simd), "u_all_simd_S": len(u_simd_s),
            "u_release": len(set().union(*[set(v.get("iforms") or {}) for v in rel]) if rel else set()),
            "iforms_per_config": {c: sorted(set().union(*[set(v.get("iforms") or {}) for v in union if v["config"] == c]))
                                  for c in sorted({v["config"] for v in union})},
            "fp_sensitive_iclasses": sorted(fp_ic),
            "p5_opclass": len({opc.get(i, i) for i in fp_ic}),
            "delta_vs_b_iform_raw": {"added": sorted(u_simd_s - bset), "missing": sorted(bset - u_simd_s),
                                     "shared": len(u_simd_s & bset)},
            "evex_static_rounding": {"%s|%s:%s|b%d" % (v["config"], v["table"], v["slot"], v["build_index"]):
                                     v.get("evex_static_rounding") for v in union if v.get("evex_static_rounding")},
            "fp_environment_iclasses_in_counted_sets": sorted(i for i in ic_all if i in FP_ENV),
            "external_calls": {"%s|%s:%s|b%d" % (v["config"], v["table"], v["slot"], v["build_index"]):
                               (v.get("lift_blockers") or {}).get("external_calls") for v in census["variants"]
                               if (v.get("lift_blockers") or {}).get("external_calls")},
            "ab_compare": collections.Counter(v.get("ab_compare") for v in census["variants"] if v["config"] == "A-ninja"),
            "repro_identical": {c: {f: r.get("identical") for f, r in x.get("repro", {}).items()}
                                for c, x in census["configs"].items()},
            "attribution": collections.Counter("%s:%s" % (v["config"], v.get("attribution")) for v in census["variants"]),
            "loop_tags": collections.Counter(t for v in union for lp in v.get("loops") or [] for t in lp.get("tags") or []),
            "loops_not_computed": collections.Counter(t for v in union for lp in v.get("loops") or []
                                                      for t in lp.get("not_computed_tags") or []),
            "proxy_fidelity": proxy_fidelity(census["variants"])}}
    census["notes"] += [
        "not computed by the assembler (REPORT step or another arm): the operand-normalised delta against B_iform, "
        "|U_object| (arm S-object), |U_helpers| (arm S-helpers), operand order (variants[].operand_order is empty), "
        "proxy fidelity (arm B-proxy), the reduce-probe lane pairing beyond its iclass sequences",
        "runs[].census_sha256 is null: a census.json cannot carry its own hash; the build records carry their logs' hashes"]
    if pins.get("x86-intel.xml") and not a.xml:
        census["notes"].append("no --xml given: record.sha256.xml is null, so judge.py V4 fails")
    census["notes"] += commit_notes
    if not freeze_commit:
        census["notes"].append("no freeze commit (not a census run from a clean checkout of the FROZEN record): "
                               "judge.py V4 fails for a census record")
    # x0final revision (record §4.7): every loop whose header and back edge lie in different source loops, with the
    # rule that set its P3(c) bound
    for v in census["variants"]:
        for lp in v.get("loops") or []:
            if lp.get("bound_rule") in ("outer", "min"):
                census["notes"].append("loop %s|%s:%s|b%d|%s: header %s (bound %s), back edge %s (bound %s), rule %s, "
                                       "bound used %s" % (v["config"], v["table"], v["slot"], v["build_index"],
                                                          lp.get("id"), (lp.get("header_inline_stack") or ["?"])[0],
                                                          lp.get("bound_header"), (lp.get("latch_inline_stack") or ["?"])[0],
                                                          lp.get("bound_latch"), lp.get("bound_rule"), lp.get("bound_used")))
    bad = schema_check(census)
    census["schema_check"] = {"violations": bad}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(census, f, indent=1, sort_keys=True, default=lambda o: dict(o) if isinstance(o, collections.Counter) else str(o))
    print(json.dumps({"configs": cfgs, "variants": len(census["variants"]), "builds": len(census["builds"]),
                      "disagreements": len(census["crossdecoder"]["disagreements"]), "p4_u_all": len(u_all),
                      "p5_iclass": len(fp_ic), "schema_violations": bad[:10]}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
