#!/usr/bin/env python3
"""judge.py -- X0 Gatekeeper (record §8): census.json + frozen inputs -> verdict.json. Deterministic; agents may
run it, never override it (ROADMAP §1 rule 3). Standard library only; Python >= 3.8.

Usage:
  python -I judge.py CENSUS.json -o VERDICT.json [--class-dir ../class]
                     [--x2-verdict X2_VERDICT.json --judged-utc ISO8601] [--t-forms-owner-accepted]

The evaluation date is not a caller's choice: it is max(today's UTC date on the system clock, the date of the
latest census run in census.json "runs"), and both dates are written into verdict.json. (judge() takes the date
as a parameter only so that the unit tests can exercise both sides of the week-3 bound.)

Decision list, in this order (every state of census.json maps to exactly one verdict):

 S. Schema. census.json must have the Appendix C shape that this judge reads (record, runs, configs, variants,
    builds, crossdecoder, rederivation; every variant and build record with config, build_index 1|2, ...; x0final
    revision: p3.c a list, p3.d2 a list of objects with result match|mismatch|unchecked; the latest census run not
    dated after the system's UTC date). A violation gives outcome tooling_failure with the violations listed; it
    cannot be resolved conservatively.
 0. Completeness. Each main-union configuration (A, B-cmake, C, D) and the cross-check A-ninja must list every
    dispatched variant of EXPECTED_VARIANTS for build_index 1 and 2 (§6), and every census file must have a build
    record for both builds; a variant record of an unexpected (table, slot) or a duplicate is a gap. Each present
    variant of a compiled file must carry a coverage block, a resolved slot (or a genuine gap explaining why
    not: x0final revision, only table_or_slot_absent or compile_failed), a non-empty counted set (iforms) and a twin
    attribution of exact or approximate (x0final revision: none is a tooling gap). Each A-ninja variant must carry
    ab_compare (identical|differs)
    with union_member == (ab_compare == differs). Each of these configurations must carry a P3(a) result
    {a1: [...], a2: [...]} without an error for every census file. Anything missing is a tooling-class gap `other`
    (V1); an A-ninja
    variant with such a gap joins the union.
 1. Compile outcomes (from census.json "builds", decided here, not by the census script):
      every build      : compiler_sha256 must equal the Table 2.1 pin of its configuration
                         (class/frozen_inputs.json "compilers"), and (x0final revision) the pinned compiler ran
                         (compiler_ran) with exactly the frozen argv (argv_matches_frozen), and an exit status 0
                         has an object (object_exists), and (pre-freeze review of 2026-10-17) the configuration's
                         header environment (configs.<cfg>.headers) equals frozen_inputs.json "headers";
                         otherwise tooling `other`;
      genuine `compile_failed`  : rc != 0 in both builds, the pinned compiler ran with the frozen argv, and at
                                  least one error diagnostic is located (errors[].file) in a census file or in
                                  a header the build recorded as included (includes[]: /showIncludes or -H; the
                                  compiler's own intrinsic headers included); or an internal compiler error in
                                  both builds with the pinned compiler and the frozen argv.
      tooling `other`            : anything else with rc != 0 (compiler did not start, argv differs from the
                                  frozen one, no located error, an ICE in only one build, builds disagree).
    A genuine compile failure gives every variant of that file the gap `compile_failed`.
 2. V, validity:
      V1 no tooling-class gap (both_decoders_fail, range_mismatch, unresolved_indirect, other; an unknown cause
         code is rewritten in place to `other`) in any variant of a main-union configuration (A-ninja: only
         variants with union_member true), and no configuration-level gap of step 0;
      V2 no unresolved cross-decoder disagreement in a main-union configuration (or A-ninja) that is FP-sensitive:
         census flag fp_sensitive, or either reading (xed_iclass, normalised objdump iclasses) FP-sensitive or
         missing in fp_class.csv, recomputed here; only a resolution "amendment:<id>" resolves one (x0final
         revision), and the resolved ones are listed;
      V3 the independent re-derivation is present and matches exactly;
      V4 the SHA-256 of every frozen input on disk (class files, xed_tables.tsv, the census scripts listed in
         frozen_inputs.json "scripts") equals both class/frozen_inputs.json and census.json's record, and the
         compiler and (pre-freeze review of 2026-10-17) header pins exist; (x0final revision) a census record
         (record.id X0-census) carries the 40-hex freeze commit that x0_driver.py init took from the clean checkout
         of the FROZEN record, and a record.id other than X0-census or X0-census-smoke fails. Pre-freeze review of
         2026-10-17: the freeze commit is the freeze point (the first commit with the record FROZEN); a census record
         also carries the 40-hex run_commit and the post_freeze_changes list (a run after the freeze point is listed
         in validity_detail.v4_commits and the notes), hearth_commit b5d3f14 with every source blob ok, and for every
         configuration the scripts' hashes that its step ran, equal to record.scripts_sha256.
    If V fails and eval-date <= TOOLING_BOUND (2026-11-12, end of M0 week 3): outcome tooling_failure only.
    If V fails after the bound: V4 failure, a schema violation, a V3 failure because no re-derivation exists, or a
    V3 mismatch whose re-derivation figures are incomplete (u_all, p5_iclass and, for every union variant,
    "<config>|<table>:<slot>": {flagged, gap_causes}) keeps the outcome tooling_failure (final; no scientific
    verdict). Otherwise the failures are resolved conservatively and evaluation continues with
    conservative_resolution = true:
      (i)  every tooling gap counts as genuine (Amber (c) under A or D; row N1 under B-cmake, C or A-ninja); a
           missing P3(a) result counts as a P3(a) flag of that configuration;
      (ii) an unresolved disagreement counts both iclasses in U and P5 (the objdump reading through
           objdump_norm.csv), counts the instruction FP-sensitive, and flags P2/P3(b) if either reading is
           FMA-class or an approximation;
      (iii) where census and re-derivation differ, the figure less favourable to Pass is used: larger U and P5;
           a variant is flagged if either side flags it (re-derivation "flagged": P2 > 0, P3(b), P3(c) or
           d1 != pass); every gap cause the re-derivation reports is added to the variant as a genuine gap.
 3. Rows, evaluated independently (all that hold are listed):
      amber_c : a genuine P1 gap under A or D;
      amber_b : P2 > 0 (the larger of the census counter p2_fma and the FMA-class iclasses of the variant) or any P3
                flag (a1, a2 per configuration and file from the effective flags, even if the file did not compile;
                b recomputed from the iclasses; c; d1 not exactly "pass" for a present canary variant
                hx_kernels_scalar:act_quantize_q8; d2 mismatch) under A, A-ninja (union members), B-cmake, C or D;
      amber_a : |U_all| > 2*T_forms or P5_iclass > 20 [ROADMAP §3.1], recomputed here from the variants' iform and
                iclass sets and fp_class.csv (an iclass missing from fp_class.csv is FP-sensitive).
      pass    : V holds (or was resolved conservatively after the bound) and none of the three rows holds.
    Rows outside the gate (non_gate): N1 = a genuine gap under B-cmake, C or A-ninja; N2 = a genuine compile
    failure under B-cmake, C or A-ninja (a build-defect draft is required).
    Canary report (pre-freeze review of 2026-10-17; record §2 ruling, §8 E6): verdict.json "canaries" lists the d1
    result of every canary variant, the expected d2 sites (F32/F16/BF16 of k_avx2 and k_avx512) of each
    configuration by result, and the P3(c) results of the scalar F32/F16/BF16 and act variants, under the label
    "outcome indicated before freeze by a verbatim copy (E6)"; an amber_b entry with d1 or d2 flags carries the same
    label; "caveats" says when every expected d2 site under A or D is unchecked (a caveat on Pass). verdict.json
    "record" is census.json's record.id.
 4. Narrowing (only with --x2-verdict, judged at week 6): every natural loop in the closure of a dispatched
    variant under A or D whose tags are not all in X2's proved_loop_shapes ('other' is covered only if its loop
    id is in proved_loop_ids; a loop with not_computed_tags, i.e. peeled/interchanged unchecked, is covered only
    if its id is in proved_loop_ids; a loop with no tags is uncovered) is uncovered; a compiled variant under A or
    D without a loop analysis contributes an uncovered entry; if X2's verdict has no proved_loop_shapes field the
    narrowing holds with every loop listed. Narrowing holds iff at least one loop is uncovered.
 5. Both ways (Amendment X0-A1, post-data, 2026-10-23; record §10: "Verdicts are then reported under both the original
    and the amended rule"). When the census carries variants[].p3c_frozen_reading (x0_loops.py after X0-A1: P3(c)
    under the reading frozen at 152fa33, every constant-offset stack slot a register-like location), verdict.json
    "both_ways" lists every variant whose frozen-reading P3(c) differs from p3.c, every unscreened loop with both
    counts and its bound, and the whole decision list above evaluated a second time with p3.c replaced by
    p3c_frozen_reading (outcomes, validity, amber_b). The top-level outcomes are those of the amended rule; which
    rule governs is the Owner's decision (the amendment is post-data and in the direction favourable to Pass), and
    neither is acted on before it.
"""
import argparse
import copy
import csv
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = ("A", "B-cmake", "C", "D")
CHECKED = MAIN + ("A-ninja",)                  # configurations whose completeness judge.py enforces
RELEASE = ("A", "D")
NON_RELEASE = ("B-cmake", "C")
TABLES = ("hx_kernels_scalar", "k_avx2", "k_avx512")
SLOTS = ("matmul[F32]", "matmul[F16]", "matmul[BF16]", "matmul[Q8]", "matmul[Q4]", "act_quantize_q8")
EXPECTED_VARIANTS = [(t, s) for t in TABLES for s in SLOTS]
CANARY = ("hx_kernels_scalar", "act_quantize_q8")
FILE_OF_TABLE = {"hx_kernels_scalar": "quant.c", "k_avx2": "quant_avx2.c", "k_avx512": "quant_avx512.c"}
CENSUS_FILES = ("quant.c", "quant_avx2.c", "quant_avx512.c")
TOOLING = {"both_decoders_fail", "range_mismatch", "unresolved_indirect", "other"}
GENUINE = {"compile_failed", "table_or_slot_absent", "xed_gap", "fp_trust_dep"}
SLOT_GAPS = {"compile_failed", "table_or_slot_absent"}       # the only causes that explain an unresolved slot
RESOLUTION_RE = re.compile(r"^amendment:[A-Za-z0-9][A-Za-z0-9._-]*$")   # a cross-decoder resolution names an amendment
D2_RESULTS = ("match", "mismatch", "unchecked")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
TOOLING_BOUND = datetime.date(2026, 11, 12)    # record §8 [target]
P5_LIMIT = 20                                 # ROADMAP §3.1 [target]
T_FORMS_CAP = 105                             # record §4.5 [target]
FROZEN = {"fp_class.csv": "fp_class", "loop_table.csv": "loop_table", "B_iform.json": "b_iform",
          "hand_map.csv": "hand_map", "fp_flag_patterns.txt": "fp_flag_patterns", "objdump_norm.csv": "objdump_norm",
          "xed_tables.tsv": "xed_tables"}
FMA_RE = re.compile(r"^(VF(N)?M(ADD|SUB)(SUB|ADD)?(132|213|231)?(PS|PD|SS|SD|PH|SH|BF16|NEPBF16)|V4FN?MADD(PS|SS)|"
                    r"VFC?(MADD|MUL)C(PH|SH)|VFN?M(ADD|SUB)(SUB|ADD)?(PS|PD|SS|SD))$")
APPROX_RE = re.compile(r"^V?(RCP|RSQRT)(PS|SS)$|^V(RCP|RSQRT)(14|28)(PS|PD|SS|SD)$|^V(RCP|RSQRT)(PH|SH|BF16)$|"
                       r"^VEXP2P[SD]$|^PF(RCP|RSQ)")
TAGS = ("lockstep", "unrolled-u", "rotated", "peeled", "software-pipelined", "auto-vectorised", "spilled",
        "interchanged", "other")
HEARTH_COMMIT = "b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220"      # record §2
# record §2, §8 E6 (lead engineer's ruling of 2026-10-17; pre-freeze review of 2026-10-17): every report of these
# results carries this label
E6_LABEL = "outcome indicated before freeze by a verbatim copy (E6)"
D2_EXPECTED = [(t, s) for t in ("k_avx2", "k_avx512") for s in ("matmul[F32]", "matmul[F16]", "matmul[BF16]")]
E6_P3C_VARIANTS = [("hx_kernels_scalar", s) for s in ("matmul[F32]", "matmul[F16]", "matmul[BF16]", "act_quantize_q8")]


def _norm_header_value(x):
    return x.strip().rstrip("\\/").strip() if isinstance(x, str) else x


def headers_mismatch(have, pin):
    """Pre-freeze review of 2026-10-17 (record §5 P1, Table 2.1): the keys of the configuration's header pin
    (class/frozen_inputs.json "headers": Windows SDK, UCRT, MSVC toolset, libc6-dev, clang's resource-dir include tree)
    whose recorded value (census.json configs.<cfg>.headers, written by x0_driver.py) differs. A trailing path
    separator of a version string (vcvars' WindowsSDKVersion ends in a backslash) is ignored. No pin: ['no pin']."""
    if not isinstance(pin, dict) or not pin:
        return ["no header pin for this configuration"]
    have = have if isinstance(have, dict) else {}
    bad = []
    for k, want in sorted(pin.items()):
        got = have.get(k)
        if isinstance(want, dict):
            if not (isinstance(got, dict) and all(got.get(kk) == vv for kk, vv in want.items())):
                bad.append(k)
        elif _norm_header_value(got) != _norm_header_value(want):
            bad.append(k)
    return bad


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_fp_class(path):
    with open(path, encoding="utf-8", newline="") as f:
        return {r["iclass"]: r["fp_sensitive"] == "yes" for r in csv.DictReader(f)}


def _is_list_of_dicts(x):
    return isinstance(x, list) and all(isinstance(i, dict) for i in x)


def validate_schema(census):
    """The parts of the Appendix C shape that judge.py reads. Returns a list of violations."""
    bad = []
    if not isinstance(census, dict):
        return ["census.json is not an object"]
    for k, typ in (("record", dict), ("runs", list), ("configs", dict), ("variants", list), ("builds", list),
                   ("crossdecoder", dict), ("rederivation", dict)):
        if not isinstance(census.get(k), typ):
            bad.append("%s missing or not a %s" % (k, typ.__name__))
    if bad:
        return bad
    if not isinstance(census["record"].get("sha256"), dict):
        bad.append("record.sha256 missing or not an object")
    if not _is_list_of_dicts(census["runs"]):
        bad.append("runs[] entries must be objects")
    for c, x in census["configs"].items():
        if not isinstance(x, dict):
            bad.append("configs.%s is not an object" % c)
    for i, v in enumerate(census["variants"]):
        if not isinstance(v, dict):
            bad.append("variants[%d] is not an object" % i)
            continue
        for k in ("config", "table", "slot"):
            if not isinstance(v.get(k), str):
                bad.append("variants[%d].%s missing or not a string" % (i, k))
        if v.get("build_index") not in (1, 2):
            bad.append("variants[%d].build_index is %r, expected 1 or 2" % (i, v.get("build_index")))
        for k, typ in (("coverage", dict), ("iforms", dict), ("iclasses", dict), ("p3", dict), ("loops", list)):
            if k in v and not isinstance(v[k], typ):
                bad.append("variants[%d].%s is not a %s" % (i, k, typ.__name__))
        if isinstance(v.get("coverage"), dict) and not _is_list_of_dicts(v["coverage"].get("gaps", [])):
            bad.append("variants[%d].coverage.gaps is not a list of objects" % i)
        if isinstance(v.get("loops"), list) and not _is_list_of_dicts(v["loops"]):
            bad.append("variants[%d].loops[] entries must be objects" % i)
        for k in ("p3c_frozen_reading", "p3c_unscreened"):     # Amendment X0-A1
            if k in v and not (isinstance(v[k], list) and all(isinstance(x, str) for x in v[k])):
                bad.append("variants[%d].%s is not a list of loop ids" % (i, k))
        q = v.get("p3")
        if isinstance(q, dict):                   # x0final revision: the P3 lists judge.py reads are typed
            if "c" in q and not isinstance(q["c"], list):
                bad.append("variants[%d].p3.c is not a list" % i)
            if "d2" in q and not (_is_list_of_dicts(q["d2"]) and all(s.get("result") in D2_RESULTS for s in q["d2"])):
                bad.append("variants[%d].p3.d2 must be a list of objects with result in %s" % (i, "|".join(D2_RESULTS)))
    for i, b in enumerate(census["builds"]):
        if not isinstance(b, dict):
            bad.append("builds[%d] is not an object" % i)
            continue
        if not isinstance(b.get("config"), str) or not isinstance(b.get("file"), str):
            bad.append("builds[%d] lacks config or file" % i)
        if b.get("build_index") not in (1, 2):
            bad.append("builds[%d].build_index is %r, expected 1 or 2" % (i, b.get("build_index")))
        if not isinstance(b.get("rc"), int) or isinstance(b.get("rc"), bool):
            bad.append("builds[%d].rc is not an integer" % i)
    if not _is_list_of_dicts(census["crossdecoder"].get("disagreements", [])):
        bad.append("crossdecoder.disagreements is not a list of objects")
    return bad


def _norm_path(p):
    return (p or "").replace("\\", "/").lower()


def _located(b):
    """At least one error diagnostic located in a census file or in a header this build recorded as included."""
    incl = {_norm_path(p) for p in (b.get("includes") or []) if isinstance(p, str)}
    for e in b.get("errors") or []:
        f = _norm_path(e.get("file") if isinstance(e, dict) else None)
        if not f:
            continue
        if f.rsplit("/", 1)[-1] in CENSUS_FILES or f in incl:
            return True
    return False


def classify_build(builds, compiler_pin=None):
    """builds: the build records of one (config, file), any build_index; compiler_pin: {file: sha256} of the
    configuration (Table 2.1). Returns (verdict, detail): 'ok', 'compile_failed' (genuine) or 'other' (tooling)."""
    if not builds:
        return "other", "no build record"
    if not compiler_pin:
        return "other", "no compiler pin for this configuration in frozen_inputs.json"
    for b in builds:
        if b.get("compiler_sha256") != compiler_pin:
            return "other", "compiler_sha256 differs from the Table 2.1 pin (or is not recorded)"
    # x0final revision (review 2026-10-16/17): every build, successful or not, must have run the pinned compiler
    # with exactly the frozen argv, and success needs an object (record §5 P1 "success")
    for b in builds:
        if b.get("compiler_ran") is not True or b.get("argv_matches_frozen") is not True:
            return "other", "compiler did not run, or argv differs from the frozen one (build %s)" % b.get("build_index")
        if b.get("rc") == 0 and b.get("object_exists") is not True:
            return "other", "exit 0 without an object (build %s)" % b.get("build_index")
    failed = [b for b in builds if b.get("rc") != 0]
    if not failed:
        return "ok", None
    ices = [b for b in failed if b.get("ice")]
    if ices:
        if len(ices) == len(builds) and len(builds) >= 2:
            return "compile_failed", "internal compiler error in every build (reproducible)"
        return "other", "internal compiler error in only some builds"
    for b in failed:
        if not _located(b):
            return "other", "non-zero exit without an error diagnostic located in a census file or an included header"
    if len(failed) != len(builds):
        return "other", "build 1 and build 2 disagree on success"
    locs = sorted({"%s:%s" % (e.get("file"), e.get("line")) for b in failed for e in b.get("errors") or []
                   if isinstance(e, dict)})
    return "compile_failed", "; ".join(locs)[:400]


def _vid(v):
    return "%s:%s" % (v.get("table"), v.get("slot"))


A1_KEY = "p3c_frozen_reading"
A1_RULE = ("Amendment X0-A1 (post-data, 2026-10-23): P3(c) with stack slots whose address escapes as plain memory "
           "(top-level outcomes) against the reading frozen at 152fa33, every constant-offset stack slot a "
           "register-like location (frozen_reading); which governs is the Owner's decision")


def _frozen_reading_census(census):
    """A copy of census.json whose P3(c) lists are the frozen reading's (variants[].p3c_frozen_reading), or None when
    the census carries no such list (written before X0-A1)."""
    vs = census.get("variants") if isinstance(census, dict) else None
    if not isinstance(vs, list) or not any(isinstance(v, dict) and A1_KEY in v for v in vs):
        return None
    alt = copy.deepcopy(census)
    for v in alt["variants"]:
        if isinstance(v, dict) and isinstance(v.get(A1_KEY), list) and isinstance(v.get("p3"), dict):
            v["p3"]["c"] = list(v[A1_KEY])
    return alt


def judge(census, class_dir, eval_date, x2=None, judged_utc=None, t_forms_owner_accepted=False, root=None,
          date_basis=None):
    """The decision list (module docstring, items S to 4) under the census's own P3(c) lists, and (item 5, Amendment
    X0-A1) the same decision list under the frozen reading when the census carries it."""
    alt = _frozen_reading_census(census)
    rows = []
    if alt is not None:
        for v in census["variants"]:
            if not isinstance(v, dict):
                continue
            c = sorted((v.get("p3") or {}).get("c") or []) if isinstance(v.get("p3"), dict) else []
            f = sorted(v[A1_KEY]) if isinstance(v.get(A1_KEY), list) else c
            uns = [{"loop": lp.get("id"), "acc_lanes_emitted": lp.get("acc_lanes_emitted"),
                    "acc_lanes_if_escaping_slots_were_registers": lp.get("acc_lanes_if_escaping_slots_were_registers"),
                    "bound_used": lp.get("bound_used")}
                   for lp in v.get("loops") or [] if isinstance(lp, dict) and lp.get("unscreened")]
            if c != f or uns:
                rows.append({"config": v.get("config"), "variant": _vid(v), "build_index": v.get("build_index"),
                             "p3c": c, "p3c_frozen_reading": f, "unscreened_loops": uns})
    verdict = _judge_one(census, class_dir, eval_date, x2, judged_utc, t_forms_owner_accepted, root, date_basis)
    if alt is not None:
        fr = _judge_one(alt, class_dir, eval_date, x2, judged_utc, t_forms_owner_accepted, root, date_basis)
        verdict["both_ways"] = {
            "rule": A1_RULE,
            "p3c_differs": any(r["p3c"] != r["p3c_frozen_reading"] for r in rows),
            "variants": rows,
            "frozen_reading": {"outcomes": fr["outcomes"], "validity": fr["validity"], "amber_b": fr["amber_b"]},
            "outcomes_differ": fr["outcomes"] != verdict["outcomes"],
            "amber_b_configs": sorted({x["config"] for x in verdict["amber_b"]}),
            "amber_b_configs_frozen_reading": sorted({x["config"] for x in fr["amber_b"]})}
        verdict["notes"].append("Amendment X0-A1 (post-data): reported both ways in both_ways; the outcomes above use "
                                "the amended P3(c); under the frozen reading: %s" % ", ".join(fr["outcomes"]))
    return verdict


def _judge_one(census, class_dir, eval_date, x2=None, judged_utc=None, t_forms_owner_accepted=False, root=None,
               date_basis=None):
    root = root or os.path.dirname(os.path.abspath(class_dir))
    fpc = load_fp_class(os.path.join(class_dir, "fp_class.csv"))
    b_iform = _load_json(os.path.join(class_dir, "B_iform.json"))
    n_b = len(b_iform["b_iform"])
    t_forms = n_b if t_forms_owner_accepted else min(n_b, T_FORMS_CAP)
    notes = []
    after_bound = eval_date > TOOLING_BOUND
    rid = (census.get("record") or {}).get("id") if isinstance(census, dict) and isinstance(census.get("record"), dict) else None
    verdict = {"record": rid, "eval_date": eval_date.isoformat(), "eval_date_basis": date_basis,
               "tooling_bound": TOOLING_BOUND.isoformat(),
               "validity": {"v1": False, "v2": False, "v3": False, "v4": False},
               "validity_detail": {}, "tooling_runs": 0, "conservative_resolution": False, "outcomes": [],
               "amber_a": None, "amber_b": [], "amber_c": [], "non_gate": [], "narrowing": None, "notes": notes}

    # ---- S: schema
    schema = validate_schema(census)
    db = date_basis or {}
    if db.get("latest_census_run_date") and db.get("system_utc_date") and             db["latest_census_run_date"] > db["system_utc_date"]:
        schema.append("the latest census run (%s) is dated after the system's UTC date (%s)"
                      % (db["latest_census_run_date"], db["system_utc_date"]))
    if schema:
        verdict["validity_detail"] = {"schema": schema}
        verdict["outcomes"] = ["tooling_failure"]
        notes.append("census.json violates the Appendix C schema; no verdict (not resolvable conservatively)")
        return verdict

    # ---- V4: frozen inputs
    pins_path = os.path.join(class_dir, "frozen_inputs.json")
    pins = _load_json(pins_path) if os.path.exists(pins_path) else {}
    rec = census.get("record") or {}
    rec_sha = rec.get("sha256") or {}
    v4_detail = []
    for name, key in sorted(FROZEN.items()):
        p = os.path.join(class_dir, name)
        disk = sha256(p) if os.path.exists(p) else None
        if not (disk and pins.get(name) == disk and rec_sha.get(key) == disk):
            v4_detail.append({"input": name, "disk": disk, "pinned": pins.get(name), "census": rec_sha.get(key)})
    if pins.get("x86-intel.xml") is None or rec_sha.get("xml") != pins.get("x86-intel.xml"):
        v4_detail.append({"input": "x86-intel.xml", "pinned": pins.get("x86-intel.xml"), "census": rec_sha.get("xml")})
    spins = pins.get("scripts")
    if not isinstance(spins, dict) or not spins:
        v4_detail.append({"input": "scripts", "detail": "frozen_inputs.json has no scripts map"})
    else:
        rs = rec.get("scripts_sha256") if isinstance(rec.get("scripts_sha256"), dict) else {}
        if rs != spins:
            v4_detail.append({"input": "scripts", "detail": "census.json record.scripts_sha256 differs from the pins",
                              "differing": sorted(k for k in set(rs) | set(spins) if rs.get(k) != spins.get(k))})
        for rel, h in sorted(spins.items()):
            p = os.path.join(root, *rel.split("/"))
            disk = sha256(p) if os.path.exists(p) else None
            if disk != h:
                v4_detail.append({"input": rel, "disk": disk, "pinned": h})
    # x0final revision: a census run is tied to the freeze commit (x0_driver.py init checks the clean checkout and
    # the FROZEN status line at HEAD; x0_census.py copies the commit into record.freeze_commit)
    v4_commits = None
    if rec.get("id") == "X0-census":
        if not (isinstance(rec.get("freeze_commit"), str) and COMMIT_RE.match(rec["freeze_commit"])):
            v4_detail.append({"input": "record.freeze_commit", "census": rec.get("freeze_commit"),
                              "detail": "no freeze commit: the census was not run from a clean checkout of the FROZEN record"})
        # pre-freeze review of 2026-10-17: the freeze point (first commit with the record FROZEN) and the commit the
        # run used are distinct facts; a run after the freeze point lists the class/, scripts/ and flags/ paths
        # changed since (each named by an appended amendment, which x0_driver.py init checked)
        rc_ = rec.get("run_commit")
        pfc = rec.get("post_freeze_changes")
        if not (isinstance(rc_, str) and COMMIT_RE.match(rc_)) or not isinstance(pfc, list):
            v4_detail.append({"input": "record.run_commit", "census": rc_, "post_freeze_changes": pfc,
                              "detail": "no run commit or no post-freeze change list from x0_driver.py init"})
        else:
            v4_commits = {"freeze_commit": rec.get("freeze_commit"), "run_commit": rc_,
                                                  "post_freeze": rc_ != rec.get("freeze_commit"),
                                                  "post_freeze_changes": pfc}
            if rc_ != rec.get("freeze_commit"):
                notes.append("the census ran at %s, after the freeze point %s; class/scripts/flags paths changed since "
                             "(each named by an amendment, record §10): %s" % (rc_, rec.get("freeze_commit"), pfc or "none"))
        # pre-freeze review of 2026-10-17 (record §2): the census source is Hearth b5d3f14 with the pinned blobs
        sb = rec.get("source_blobs")
        if rec.get("hearth_commit") != HEARTH_COMMIT or not isinstance(sb, dict) or not sb or \
                not all(isinstance(x, dict) and x.get("ok") is True for x in sb.values()):
            v4_detail.append({"input": "record.hearth_commit/source_blobs", "census": rec.get("hearth_commit"),
                              "pinned": HEARTH_COMMIT, "detail": "the census source is not Hearth b5d3f14 with the "
                                                                 "pinned blobs of record §2"})
        # pre-freeze review of 2026-10-17: every configuration step ran the scripts init verified
        for cfg, x in sorted(census["configs"].items()):
            if not isinstance(x, dict) or x.get("scripts_sha256") != rec.get("scripts_sha256"):
                v4_detail.append({"input": "configs.%s.scripts_sha256" % cfg,
                                  "detail": "this configuration ran scripts other than the ones init verified"})
    elif rec.get("id") == "X0-census-smoke":
        notes.append("smoke record (record.id X0-census-smoke, NON-Hearth): no freeze commit is required")
    else:
        v4_detail.append({"input": "record.id", "census": rec.get("id"),
                          "detail": "record.id is neither X0-census nor X0-census-smoke"})
    cpins = pins.get("compilers") if isinstance(pins.get("compilers"), dict) else {}
    hpins = pins.get("headers") if isinstance(pins.get("headers"), dict) else {}
    for cfg in CHECKED:
        if not isinstance(cpins.get(cfg), dict) or not cpins.get(cfg):
            v4_detail.append({"input": "compilers.%s" % cfg, "detail": "no Table 2.1 compiler pin"})
        if not isinstance(hpins.get(cfg), dict) or not hpins.get(cfg):
            v4_detail.append({"input": "headers.%s" % cfg, "detail": "no Table 2.1 header pin"})
    v4 = not v4_detail

    variants = census["variants"]
    builds = census["builds"]
    configs = census["configs"]
    config_gaps = []                  # (config, kind, detail): configuration-level tooling gaps (V1)

    def add_gap(v, cause, detail):
        v.setdefault("coverage", {}).setdefault("gaps", [])
        if not any(g.get("cause") == cause and g.get("detail") == detail for g in v["coverage"]["gaps"]):
            v["coverage"]["gaps"].append({"cause": cause, "detail": detail})
        if v.get("config") == "A-ninja" and cause not in GENUINE:
            v["union_member"] = True          # a tooling gap of the cross-check must reach V1

    # ---- 0/1. completeness and compile outcomes
    synthetic = []
    compile_state = {}
    for cfg in CHECKED:
        if cfg == "A-ninja" and cfg not in configs:
            config_gaps.append((cfg, "absent", "A-ninja (A versus A-ninja comparison, record §2) absent from census.json"))
        for fl in CENSUS_FILES:
            bs = [b for b in builds if b.get("config") == cfg and b.get("file") == fl]
            idx = sorted({b.get("build_index") for b in bs}, key=repr)
            st, det = classify_build(bs, cpins.get(cfg))
            if idx != [1, 2]:
                st, det = "other", "build records for build_index %s, expected [1, 2]" % idx
            # pre-freeze review of 2026-10-17: the header environment of Table 2.1 (SDK, UCRT, toolset, libc6-dev,
            # resource-dir include tree) is part of what makes a compile failure genuine and a success Hearth's build
            hbad = headers_mismatch((configs.get(cfg) or {}).get("headers"), hpins.get(cfg))
            if hbad and st != "other":
                st, det = "other", "header environment differs from the Table 2.1 pin (frozen_inputs.json headers): %s" % hbad
            compile_state[(cfg, fl)] = (st, det)
            x = ((configs.get(cfg) or {}).get("p3a") or {}).get(fl)
            # x0final revision: a P3(a) result that carries an error was not evaluated, whatever its lists say
            if not (isinstance(x, dict) and isinstance(x.get("a1"), list) and isinstance(x.get("a2"), list)
                    and not x.get("error")):
                config_gaps.append((cfg, "p3a:%s" % fl, "P3(a) not evaluated for %s/%s" % (cfg, fl)))
    seen = {}
    for v in variants:
        cfg = v.get("config")
        if cfg not in CHECKED:
            continue
        key = (cfg, v.get("table"), v.get("slot"), v.get("build_index"))
        if (v.get("table"), v.get("slot")) not in EXPECTED_VARIANTS:
            add_gap(v, "other", "unexpected variant %s (record §4.1 lists 18 per configuration)" % _vid(v))
            v["union_member"] = True
        if key in seen:
            add_gap(v, "other", "duplicate variant record")
        seen[key] = v
    for cfg in CHECKED:
        for bi in (1, 2):
            for (t, s) in EXPECTED_VARIANTS:
                have = [v for v in variants if v.get("config") == cfg and v.get("table") == t and v.get("slot") == s
                        and v.get("build_index") == bi]
                st, det = compile_state[(cfg, FILE_OF_TABLE[t])]
                if not have:
                    cause = "compile_failed" if st == "compile_failed" else "other"
                    synthetic.append({"config": cfg, "table": t, "slot": s, "build_index": bi, "union_member": True,
                                      "file": FILE_OF_TABLE[t], "synthetic": True,
                                      "coverage": {"slot_resolved": False,
                                                   "gaps": [{"cause": cause, "detail": det or "variant missing from census.json"}]}})
                    continue
                for v in have:
                    if st != "ok":
                        add_gap(v, st, det)
                        continue
                    cov = v.get("coverage")
                    if not isinstance(cov, dict):
                        add_gap(v, "other", "coverage incomplete: no coverage block")
                    elif cov.get("slot_resolved") is not True:
                        # x0final revision: only table_or_slot_absent or compile_failed explains an unresolved slot
                        if not any(g.get("cause") in SLOT_GAPS for g in cov.get("gaps") or []):
                            add_gap(v, "other", "coverage incomplete: slot unresolved without a table_or_slot_absent "
                                                "or compile_failed gap")
                    elif not v.get("iforms") or not v.get("iclasses"):
                        add_gap(v, "other", "coverage incomplete: empty counted set")
                    # x0final revision (record §4.6): a twin whose attribution is none (twin build failed, line
                    # table failed its self-checks) silently disables P3(c)'s own bounds and every d2 site, so it is
                    # a tooling gap; 'approximate' stays as the record defines it
                    if v.get("attribution") not in ("exact", "approximate"):
                        add_gap(v, "other", "twin attribution %s: %s" % (v.get("attribution"),
                                                                          v.get("attribution_detail") or "not recorded"))
                    if cfg == "A-ninja":
                        ab = v.get("ab_compare")
                        if ab not in ("identical", "differs") or bool(v.get("union_member")) != (ab == "differs"):
                            add_gap(v, "other", "A versus A-ninja comparison missing or inconsistent "
                                                "(ab_compare %r, union_member %r)" % (ab, v.get("union_member")))
    allv = variants + synthetic

    def in_union(v):
        return v.get("config") in MAIN or (v.get("config") == "A-ninja" and v.get("union_member"))

    union = [v for v in allv if in_union(v)]

    # ---- V1, V2, V3
    for v in union:                       # an unknown cause code is a tooling defect (rewritten in place)
        for g in (v.get("coverage") or {}).get("gaps") or []:
            if g.get("cause") not in TOOLING | GENUINE:
                g["cause_original"] = g.get("cause")
                g["cause"] = "other"
                g["detail"] = "unknown cause code %r" % (g["cause_original"],)
    tooling_gaps = [(v, g) for v in union for g in (v.get("coverage") or {}).get("gaps") or []
                    if g.get("cause") in TOOLING]
    v1 = not tooling_gaps and not config_gaps
    xd = [d for d in census["crossdecoder"].get("disagreements", []) if d.get("config") in CHECKED]
    # FP-sensitivity is recomputed here from fp_class.csv for both readings (missing iclass = FP-sensitive); the
    # census flag can only add to it
    # x0final revision: only a resolution that names a post-data amendment ("amendment:<id>") resolves a
    # disagreement; any other value counts as unresolved
    resolved = [d for d in xd if isinstance(d.get("resolution"), str) and RESOLUTION_RE.match(d["resolution"])]
    unresolved = [d for d in xd if d not in resolved and
                  (d.get("fp_sensitive") or fpc.get(d.get("xed_iclass"), True) or
                   any(fpc.get(x, True) for x in d.get("normalised") or []))]
    v2 = not unresolved
    rd = census.get("rederivation") or {}
    v3 = bool(rd.get("present")) and bool(rd.get("matches"))
    valid = v1 and v2 and v3 and v4
    verdict["validity"] = {"v1": v1, "v2": v2, "v3": v3, "v4": v4}
    verdict["validity_detail"] = {
        "v1_tooling_gaps": [{"config": v.get("config"), "table": v.get("table"), "slot": v.get("slot"),
                             "build_index": v.get("build_index"), "cause": g.get("cause"), "detail": g.get("detail")}
                            for v, g in tooling_gaps],
        "v1_config_gaps": [{"config": c, "item": k, "detail": d} for c, k, d in config_gaps],
        "v2_unresolved": unresolved, "v2_resolved_by_amendment": resolved,
        "v3": rd.get("mismatches", []) if rd else "absent", "v4": v4_detail, "v4_commits": v4_commits}
    verdict["tooling_runs"] = len({r.get("run_id") for r in census["runs"] if r.get("kind") == "census"})
    rcd = {}
    if not valid:
        if not after_bound:
            verdict["outcomes"] = ["tooling_failure"]
            return verdict
        if not v4 or not rd.get("present"):
            verdict["outcomes"] = ["tooling_failure"]
            notes.append("validity failed after the week-3 bound and cannot be resolved conservatively "
                         "(V4 failed or no re-derivation exists): no scientific verdict; escalate to the Owner")
            return verdict
        if not v3:
            rcd = rd.get("figures") if isinstance(rd.get("figures"), dict) else {}
            missing = [k for k in ("u_all", "p5_iclass") if not isinstance(rcd.get(k), int)]
            for v in union:
                k = "%s|%s" % (v.get("config"), _vid(v))
                x = rcd.get(k)
                if not (isinstance(x, dict) and isinstance(x.get("flagged"), bool) and isinstance(x.get("gap_causes"), list)):
                    missing.append(k)
            if missing:
                verdict["outcomes"] = ["tooling_failure"]
                notes.append("V3 failed after the week-3 bound and the re-derivation figures are incomplete (%s); "
                             "the less favourable figure cannot be taken: no scientific verdict; escalate to the Owner"
                             % ", ".join(sorted(set(missing))[:20]))
                return verdict
        verdict["conservative_resolution"] = True

    # ---- conservative adjustments (only after the bound)
    extra_iclasses = {}
    p3a_conservative = {}
    if verdict["conservative_resolution"]:
        for v, g in tooling_gaps:
            g.setdefault("cause_original", g.get("cause"))
            g["cause"] = "conservative_genuine"
        for c, k, d in config_gaps:
            if k.startswith("p3a:"):
                p3a_conservative.setdefault(c, {})[k[4:]] = {"a1": ["conservative: P3(a) not evaluated"], "a2": []}
            else:
                notes.append("conservative resolution of a configuration-level gap: %s" % d)
        for d in unresolved:
            key = (d.get("config"), d.get("variant"))
            extra_iclasses.setdefault(key, set()).update(set(d.get("normalised") or []) | {d.get("xed_iclass")})
        for v in union:
            x = rcd.get("%s|%s" % (v.get("config"), _vid(v))) or {}
            for c in x.get("gap_causes") or []:
                v.setdefault("coverage", {}).setdefault("gaps", []).append(
                    {"cause": "conservative_genuine", "cause_original": "rederivation:%s" % c,
                     "detail": "the re-derivation reports gap %s" % c})

    def gaps_genuine(v):
        return [g for g in (v.get("coverage") or {}).get("gaps") or []
                if g.get("cause") in GENUINE | {"conservative_genuine"}]

    # ---- amber_c and N1/N2
    for v in union:
        for g in gaps_genuine(v):
            item = {"config": v.get("config"), "variant": _vid(v), "build_index": v.get("build_index"),
                    "cause": g.get("cause"), "cause_original": g.get("cause_original"), "detail": g.get("detail")}
            if v.get("config") in RELEASE:
                verdict["amber_c"].append(item)
            else:
                verdict["non_gate"].append(dict(item, row="N1"))
    for (cfg, fl), (st, det) in sorted(compile_state.items()):
        if st == "compile_failed" and cfg not in RELEASE:
            verdict["non_gate"].append({"row": "N2", "config": cfg, "file": fl, "detail": det})

    # ---- amber_b: P2 and P3
    for cfg in CHECKED:
        p3a = dict(((configs.get(cfg) or {}).get("p3a") or {}))
        p3a.update(p3a_conservative.get(cfg, {}))
        flagged_files = {fl: x for fl, x in sorted(p3a.items())
                         if isinstance(x, dict) and (x.get("a1") or x.get("a2"))}
        vs = [v for v in union if v.get("config") == cfg]
        p2 = 0
        for v in vs:
            by_iclass = sum(int(n) for ic, n in (v.get("iclasses") or {}).items() if FMA_RE.match(ic or ""))
            p2 += max(int(v.get("p2_fma") or 0), by_iclass)
        p3 = {"a": flagged_files, "b": [], "c": [], "d1": [], "d2": [], "rederivation": []}
        extra_cfg = set().union(*[s2 for (c2, _), s2 in extra_iclasses.items() if c2 == cfg]) if extra_iclasses else set()
        p2 += sum(1 for i in extra_cfg if FMA_RE.match(i or ""))
        if any(APPROX_RE.match(i or "") for i in extra_cfg):
            p3["b"].append("conservative: unresolved cross-decoder reading")
        for v in vs:
            vid = _vid(v)
            q = v.get("p3") or {}
            ics = set((v.get("iclasses") or {}).keys())
            if q.get("b") or any(APPROX_RE.match(i or "") for i in ics):
                p3["b"].append(vid)
            if q.get("c"):
                p3["c"].append({"variant": vid, "loops": q["c"]})
            if (v.get("table"), v.get("slot")) == CANARY and not v.get("synthetic") and q.get("d1") != "pass":
                p3["d1"].append({"variant": vid, "build_index": v.get("build_index"), "d1": q.get("d1")})
            if any(isinstance(s, dict) and s.get("result") == "mismatch" for s in q.get("d2") or []):
                p3["d2"].append(vid)
            rv = rcd.get("%s|%s" % (cfg, vid)) or {}
            if rv.get("flagged"):
                p3["rederivation"].append(vid)
        if p2 > 0 or any(p3.values()):
            item = {"config": cfg, "p2": p2, "p3": p3}
            if p3["d1"] or p3["d2"]:
                item["label"] = E6_LABEL           # record §2 ruling: every report of d1 or d2 carries it
            verdict["amber_b"].append(item)

    # ---- amber_a: U_all and P5_iclass recomputed here
    u_all, ic_all = set(), set()
    for v in union:
        u_all |= set((v.get("iforms") or {}).keys())
        ic_all |= set((v.get("iclasses") or {}).keys())
    for s in extra_iclasses.values():
        ic_all |= s
        u_all |= {"%s:objdump-reading" % i for i in s}     # counted as extra forms (conservative (ii))
    fp_ic = {i for i in ic_all if fpc.get(i, True)}
    u_n, p5 = len(u_all), len(fp_ic)
    if verdict["conservative_resolution"]:
        u_n = max(u_n, int(rcd.get("u_all") or 0))
        p5 = max(p5, int(rcd.get("p5_iclass") or 0))
    cm = census.get("metrics") or {}
    if not verdict["conservative_resolution"] and (cm.get("p4_u_all") not in (None, len(u_all)) or
                                                   cm.get("p5_iclass") not in (None, len(fp_ic))):
        notes.append("census.json metrics (U %s, P5 %s) differ from the judge's recomputation (U %d, P5 %d); "
                     "the recomputation is used" % (cm.get("p4_u_all"), cm.get("p5_iclass"), len(u_all), len(fp_ic)))
    verdict["amber_a"] = {"u_all": u_n, "t_forms": t_forms, "two_t_forms": 2 * t_forms, "p5_iclass": p5,
                          "p5_limit": P5_LIMIT, "fp_sensitive_iclasses": sorted(fp_ic),
                          "holds": u_n > 2 * t_forms or p5 > P5_LIMIT}

    outs = []
    if verdict["amber_a"]["holds"]:
        outs.append("amber_a")
    if verdict["amber_b"]:
        outs.append("amber_b")
    if verdict["amber_c"]:
        outs.append("amber_c")
    verdict["outcomes"] = outs or ["pass"]

    # ---- canary report (record §2 ruling, §8 E6; pre-freeze review of 2026-10-17): every d1 and d2 result, and the
    # P3(c) results of the scalar F32/F16/BF16 and act variants (dot16_conv's loops and the amax loop, whose shapes a
    # regression file carried in Hearth's own text), are reported with the E6 label; the expected d2 sites of each
    # configuration are counted by result, and "every expected d2 site unchecked" under A or D is a caveat on Pass
    canaries = {"label": E6_LABEL, "d1": {}, "d2": {}, "p3c_labelled": {}}
    for cfg in CHECKED:
        vs = [v for v in union if v.get("config") == cfg and not v.get("synthetic")]
        canaries["d1"][cfg] = sorted(["b%s:%s" % (v.get("build_index"), (v.get("p3") or {}).get("d1"))
                                      for v in vs if (v.get("table"), v.get("slot")) == CANARY])
        cnt = {"match": 0, "mismatch": 0, "unchecked": 0, "variants_without_d2": []}
        for v in vs:
            if (v.get("table"), v.get("slot")) not in D2_EXPECTED:
                continue
            sites = [s for s in (v.get("p3") or {}).get("d2") or [] if isinstance(s, dict)]
            if not sites:
                cnt["variants_without_d2"].append("%s|b%s" % (_vid(v), v.get("build_index")))
            for s in sites:
                if s.get("result") in D2_RESULTS:
                    cnt[s["result"]] += 1
        canaries["d2"][cfg] = cnt
        canaries["p3c_labelled"][cfg] = sorted("%s|b%s:%s" % (_vid(v), v.get("build_index"),
                                                              ",".join((v.get("p3") or {}).get("c") or []) or "no flag")
                                               for v in vs if (v.get("table"), v.get("slot")) in E6_P3C_VARIANTS)
    verdict["canaries"] = canaries
    verdict["caveats"] = []
    for cfg in RELEASE:
        c2 = canaries["d2"].get(cfg) or {}
        if not (c2.get("match") or c2.get("mismatch")):
            verdict["caveats"].append("every expected P3(d2) site under %s is unchecked (%d unchecked, %d variants without "
                                      "a d2 result): the d2 canary was vacuous there%s" % (
                                          cfg, c2.get("unchecked", 0), len(c2.get("variants_without_d2") or []),
                                          "; this is a caveat on Pass" if verdict["outcomes"] == ["pass"] else ""))

    # ---- narrowing (week 6)
    if x2 is not None:
        shapes = x2.get("proved_loop_shapes")
        ids = set(x2.get("proved_loop_ids") or [])
        unc = []
        for v in union:
            if v.get("config") not in RELEASE or v.get("synthetic"):
                continue
            if "loops" not in v:
                if v.get("iforms"):
                    unc.append({"config": v.get("config"), "variant": _vid(v), "loop_id": None, "tags": [],
                                "reason": "loop analysis missing"})
                continue
            for lp in v.get("loops") or []:
                tags = lp.get("tags") or []
                lid = "%s|%s|%s" % (v.get("config"), _vid(v), lp.get("id"))
                if shapes is None:
                    ok = False
                elif lp.get("not_computed_tags") and lid not in ids:
                    ok = False      # a shape the script could not check is not a proved shape (record §4.7)
                else:
                    ok = bool(tags) and all((t in shapes and t != "other") or (t == "other" and lid in ids)
                                            for t in tags)
                if not ok:
                    unc.append({"config": v.get("config"), "variant": _vid(v), "loop_id": lp.get("id"), "tags": tags})
        verdict["narrowing"] = {"judged_utc": judged_utc,
                                "x2_verdict_sha256": hashlib.sha256(json.dumps(x2, sort_keys=True).encode()).hexdigest(),
                                "x2_field_present": shapes is not None, "holds": bool(unc), "uncovered": unc}
    return verdict


def evaluation_date(census, today=None):
    """max(system UTC date, date of the latest census run). Returns (date, basis)."""
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    runs = []
    for r in (census.get("runs") or []) if isinstance(census, dict) else []:
        u = r.get("utc") if isinstance(r, dict) else None
        try:
            runs.append(datetime.date.fromisoformat(str(u)[:10]))
        except ValueError:
            continue
    latest = max(runs) if runs else None
    d = max([today] + ([latest] if latest else []))
    return d, {"system_utc_date": today.isoformat(), "latest_census_run_date": latest.isoformat() if latest else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("census")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--class-dir", default=os.path.join(HERE, "..", "class"))
    ap.add_argument("--x2-verdict")
    ap.add_argument("--judged-utc")
    ap.add_argument("--t-forms-owner-accepted", action="store_true",
                    help="only if the Owner's signature line accepts a recomputed |B_iform| above 105 (OQ-5)")
    a = ap.parse_args()
    census = _load_json(a.census)
    x2 = _load_json(a.x2_verdict) if a.x2_verdict else None
    d, basis = evaluation_date(census)
    v = judge(census, a.class_dir, d, x2, a.judged_utc, a.t_forms_owner_accepted, date_basis=basis)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(v, f, indent=1, sort_keys=True)
    print(json.dumps({"outcomes": v["outcomes"], "validity": v["validity"], "eval_date": v["eval_date"],
                      "conservative_resolution": v["conservative_resolution"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
