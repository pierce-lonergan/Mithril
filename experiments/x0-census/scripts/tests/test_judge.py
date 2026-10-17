"""Unit tests for judge.py on SYNTHETIC census.json inputs (no Hearth object is involved).

Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v

The tests marked "review 2026-10-16" are the adversarial cases of the x0prep review (reviewer 1, same family,
independent context; scratch files adv_judge.py and adv2.py), kept as regression tests.
"""
import copy
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import judge  # noqa: E402

CLASS = os.path.join(HERE, "..", "..", "class")
BEFORE = datetime.date(2026, 11, 1)
AFTER = datetime.date(2026, 11, 20)
XML_SHA = "6762a50652a35ef663fd532ed83b789d19bbc2ac7e94b1771f19d666d96c2c30"
COMPILERS = {"A": {"cl.exe": "a1" * 32, "c1.dll": "a2" * 32, "c2.dll": "a3" * 32},
             "A-ninja": {"cl.exe": "a1" * 32, "c1.dll": "a2" * 32, "c2.dll": "a3" * 32},
             "B-cmake": {"clang-cl.exe": "b1" * 32}, "C": {"cc1": "c1" * 32, "gcc": "c2" * 32},
             "D": {"clang-23": "d1" * 32}}


def read_text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def fp_yes():
    return [r.split(",")[0] for r in read_text(os.path.join(CLASS, "fp_class.csv")).split("\n")[1:] if ",yes," in r]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.root = os.path.join(cls.tmp, "x0")
        cls.cdir = os.path.join(cls.root, "class")
        os.makedirs(cls.cdir)
        os.makedirs(os.path.join(cls.root, "scripts"))
        for n in judge.FROZEN:
            shutil.copy(os.path.join(CLASS, n), cls.cdir)
        with open(os.path.join(cls.root, "scripts", "census_script.py"), "w") as f:
            f.write("print('synthetic census script')\n")
        pins = {n: sha(os.path.join(cls.cdir, n)) for n in judge.FROZEN}
        pins["x86-intel.xml"] = XML_SHA
        pins["scripts"] = {"scripts/census_script.py": sha(os.path.join(cls.root, "scripts", "census_script.py"))}
        pins["compilers"] = COMPILERS
        with open(os.path.join(cls.cdir, "frozen_inputs.json"), "w") as f:
            json.dump(pins, f)
        cls.pins = pins

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def clean(self, iforms_per_variant=("MOV_GPRv_GPRv_89", "RET_NEAR"), iclasses=("MOV", "RET_NEAR")):
        variants, builds = [], []
        for cfg in judge.CHECKED:
            for bi in (1, 2):
                for t, s in judge.EXPECTED_VARIANTS:
                    v = {"config": cfg, "table": t, "slot": s, "build_index": bi, "union_member": cfg != "A-ninja",
                         "file": judge.FILE_OF_TABLE[t],
                         "coverage": {"slot_resolved": True, "gaps": []},
                         "iforms": {f: 1 for f in iforms_per_variant}, "iclasses": {c: 1 for c in iclasses},
                         "p2_fma": 0, "p3": {"a1": [], "a2": [], "b": [], "c": [], "d2": []},
                         "loops": [{"id": "L1", "tags": ["lockstep"]}]}
                    if (t, s) == judge.CANARY:
                        v["p3"]["d1"] = "pass"
                    if cfg == "A-ninja":
                        v["ab_compare"] = "identical"
                    variants.append(v)
                for fl in judge.CENSUS_FILES:
                    builds.append({"config": cfg, "file": fl, "build_index": bi, "rc": 0, "compiler_ran": True,
                                   "compiler_sha256": dict(COMPILERS[cfg]), "argv_matches_frozen": True,
                                   "errors": [], "includes": [], "ice": False})
        rec = {k: self.pins[n] for n, k in judge.FROZEN.items()}
        rec["xml"] = XML_SHA
        return {"record": {"id": "X0-census", "sha256": rec, "scripts_sha256": dict(self.pins["scripts"])},
                "runs": [{"run_id": "r1", "kind": "census", "utc": "2026-10-30T12:00:00Z"}],
                "configs": {c: {"p3a": {f: {"a1": [], "a2": []} for f in judge.CENSUS_FILES}} for c in judge.CHECKED},
                "variants": variants, "builds": builds, "crossdecoder": {"disagreements": []},
                "rederivation": {"present": True, "matches": True, "mismatches": []}, "metrics": {}}

    def run_judge(self, census, date=BEFORE, x2=None):
        return judge.judge(copy.deepcopy(census), self.cdir, date, x2=x2, judged_utc="2026-11-26T00:00:00Z",
                           root=self.root)

    def fail_build(self, c, cfg, fl, **kw):
        for b in c["builds"]:
            if b["config"] == cfg and b["file"] == fl:
                b.update(rc=1, **kw)
        c["variants"] = [v for v in c["variants"] if not (v["config"] == cfg and v["file"] == fl)]

    @staticmethod
    def variant(c, cfg, t, s, bi=1):
        return [v for v in c["variants"] if v["config"] == cfg and v["table"] == t and v["slot"] == s
                and v["build_index"] == bi][0]

    def full_figures(self, c, **extra):
        figs = {"u_all": 2, "p5_iclass": 0}
        for v in c["variants"]:
            if v["config"] in judge.MAIN or v.get("union_member"):
                figs["%s|%s:%s" % (v["config"], v["table"], v["slot"])] = {"flagged": False, "gap_causes": []}
        figs.update(extra)
        return figs


ERR237 = [{"file": "D:/mithril/src/hearth/engine/src/quant_avx512.c", "line": 237,
           "text": "always_inline function '_mm512_dpbusd_epi32' requires target feature 'avx512vnni'"}]


class TestJudge(Base):
    def test_clean_is_pass(self):
        v = self.run_judge(self.clean())
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertEqual(v["validity"], {"v1": True, "v2": True, "v3": True, "v4": True})
        self.assertEqual(v["amber_a"]["t_forms"], 102)

    def test_p5_over_20_is_amber_a(self):
        v = self.run_judge(self.clean(iclasses=fp_yes()[:21]))
        self.assertIn("amber_a", v["outcomes"])
        self.assertEqual(v["amber_a"]["p5_iclass"], 21)

    def test_p5_exactly_20_is_not_amber(self):
        ics = [i for i in fp_yes() if not judge.FMA_RE.match(i) and not judge.APPROX_RE.match(i)][:20]
        self.assertEqual(self.run_judge(self.clean(iclasses=ics))["outcomes"], ["pass"])

    def test_missing_iclass_counts_fp_sensitive(self):
        v = self.run_judge(self.clean(iclasses=["MOV", "NOT_AN_XED_ICLASS"]))
        self.assertIn("NOT_AN_XED_ICLASS", v["amber_a"]["fp_sensitive_iclasses"])

    def test_union_over_2t_is_amber_a(self):
        c = self.clean(iforms_per_variant=["F%d" % i for i in range(205)])
        self.assertIn("amber_a", self.run_judge(c)["outcomes"])
        c = self.clean(iforms_per_variant=["F%d" % i for i in range(204)])
        self.assertEqual(self.run_judge(c)["outcomes"], ["pass"])

    def test_bcmake_flag_defect_even_if_file_fails(self):
        c = self.clean()
        c["configs"]["B-cmake"]["p3a"]["quant_avx512.c"] = {"a1": ["a1_ffp_contract_on"], "a2": []}
        self.fail_build(c, "B-cmake", "quant_avx512.c", errors=ERR237)
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["amber_b"])
        self.assertTrue(v["validity"]["v1"])
        rows = {(n["row"], n["config"]) for n in v["non_gate"]}
        self.assertIn(("N2", "B-cmake"), rows)
        self.assertIn(("N1", "B-cmake"), rows)

    def test_bcmake_compile_failure_alone_is_pass_with_n2(self):
        c = self.clean()
        self.fail_build(c, "B-cmake", "quant_avx512.c", errors=ERR237)
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertTrue(any(n["row"] == "N2" for n in v["non_gate"]))

    def test_error_in_included_header_is_genuine(self):
        c = self.clean()
        self.fail_build(c, "C", "quant_avx2.c", errors=[{"file": "/usr/lib/gcc/x86_64-linux-gnu/13/include/avx2intrin.h",
                                                          "line": 9}],
                        includes=["/usr/lib/gcc/x86_64-linux-gnu/13/include/avx2intrin.h"])
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertTrue(any(n["row"] == "N2" and n["config"] == "C" for n in v["non_gate"]))

    def test_release_compile_failure_is_amber_c(self):
        c = self.clean()
        self.fail_build(c, "D", "quant.c", errors=[{"file": "engine/src/quant.c", "line": 1}])
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["amber_c"])
        self.assertEqual(len(v["amber_c"]), 12)   # 6 variants x 2 builds

    def test_compile_failure_without_located_error_is_tooling(self):
        c = self.clean()
        self.fail_build(c, "A", "quant_avx2.c", errors=[])
        v = self.run_judge(c)
        self.assertFalse(v["validity"]["v1"])
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        v = self.run_judge(c, AFTER)
        self.assertTrue(v["conservative_resolution"])
        self.assertEqual(v["outcomes"], ["amber_c"])

    def test_argv_mismatch_is_tooling(self):
        c = self.clean()
        self.fail_build(c, "C", "quant.c", errors=[{"file": "quant.c", "line": 1}], argv_matches_frozen=False)
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])
        v = self.run_judge(c, AFTER)
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertTrue(any(n["row"] == "N1" and n["config"] == "C" for n in v["non_gate"]))

    def test_unpinned_compiler_is_tooling(self):
        c = self.clean()
        for b in c["builds"]:
            if b["config"] == "D" and b["file"] == "quant.c":
                b["compiler_sha256"] = {"clang-23": "ee" * 32}
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        self.assertTrue(any("pin" in (g["detail"] or "") for g in v["validity_detail"]["v1_tooling_gaps"]))

    def test_ice(self):
        c = self.clean()
        for b in c["builds"]:
            if b["config"] == "D" and b["file"] == "quant_avx512.c":
                b.update(rc=1, ice=True)
        c["variants"] = [v for v in c["variants"] if not (v["config"] == "D" and v["file"] == "quant_avx512.c")]
        self.assertEqual(self.run_judge(c)["outcomes"], ["amber_c"])          # reproducible ICE: genuine
        for b in c["builds"]:
            if b["config"] == "D" and b["file"] == "quant_avx512.c" and b["build_index"] == 2:
                b.update(rc=0, ice=False)
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])   # one build only: tooling

    def test_missing_build_record_is_tooling(self):
        c = self.clean()
        c["builds"] = [b for b in c["builds"] if not (b["config"] == "A" and b["build_index"] == 2 and b["file"] == "quant.c")]
        self.assertFalse(self.run_judge(c)["validity"]["v1"])

    def test_missing_variant_is_tooling(self):
        c = self.clean()
        c["variants"] = [v for v in c["variants"] if not (v["config"] == "D" and v["slot"] == "matmul[Q4]"
                                                          and v["table"] == "k_avx512")]
        v = self.run_judge(c)
        self.assertFalse(v["validity"]["v1"])
        self.assertEqual(v["outcomes"], ["tooling_failure"])

    def test_tooling_gap_under_c(self):
        c = self.clean()
        for v in c["variants"]:
            if v["config"] == "C" and v["slot"] == "matmul[F32]" and v["table"] == "k_avx2":
                v["coverage"]["gaps"].append({"cause": "unresolved_indirect", "detail": "x"})
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])
        v = self.run_judge(c, AFTER)
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertTrue(v["conservative_resolution"])
        self.assertTrue(any(n["row"] == "N1" for n in v["non_gate"]))

    def test_unknown_cause_is_tooling(self):
        c = self.clean()
        c["variants"][0]["coverage"]["gaps"].append({"cause": "mystery"})
        self.assertFalse(self.run_judge(c)["validity"]["v1"])

    def test_genuine_gaps(self):
        for cause, cfg, expect in (("fp_trust_dep", "D", "amber_c"), ("xed_gap", "A", "amber_c"),
                                   ("table_or_slot_absent", "A", "amber_c")):
            c = self.clean()
            for v in c["variants"]:
                if v["config"] == cfg and v["slot"] == "matmul[Q8]":
                    v["coverage"]["gaps"].append({"cause": cause})
            self.assertEqual(self.run_judge(c)["outcomes"], [expect], cause)
        c = self.clean()
        for v in c["variants"]:
            if v["config"] == "C" and v["slot"] == "matmul[Q8]":
                v["coverage"]["gaps"].append({"cause": "fp_trust_dep"})
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertTrue(any(n["row"] == "N1" and n["config"] == "C" for n in v["non_gate"]))

    def test_slot_absent_with_genuine_gap_is_not_tooling(self):
        c = self.clean()
        x = self.variant(c, "A", "k_avx2", "matmul[Q4]")
        x["coverage"] = {"slot_resolved": False, "gaps": [{"cause": "table_or_slot_absent"}]}
        x["iforms"], x["iclasses"] = {}, {}
        v = self.run_judge(c)
        self.assertTrue(v["validity"]["v1"])
        self.assertEqual(v["outcomes"], ["amber_c"])

    def test_v2_unresolved_fp_disagreement(self):
        c = self.clean()
        c["crossdecoder"]["disagreements"].append({"config": "A", "variant": "A:k_avx2:matmul[F32]", "offset": 4,
                                                   "xed_iclass": "VADDPS", "normalised": ["VFMADD231PS"],
                                                   "fp_sensitive": True, "resolution": None})
        v = self.run_judge(c)
        self.assertFalse(v["validity"]["v2"])
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        v = self.run_judge(c, AFTER)
        self.assertTrue(v["conservative_resolution"])
        self.assertIn("amber_b", v["outcomes"])          # one reading is FMA-class
        self.assertIn("VFMADD231PS", v["amber_a"]["fp_sensitive_iclasses"])

    def test_v2_resolved_or_non_fp_disagreement_is_valid(self):
        c = self.clean()
        c["crossdecoder"]["disagreements"] += [
            {"config": "A", "variant": "x", "xed_iclass": "VADDPS", "fp_sensitive": True, "resolution": "decoder bug, see note"},
            {"config": "A", "variant": "x", "xed_iclass": "MOV", "normalised": ["MOV"], "fp_sensitive": False,
             "resolution": None}]
        self.assertTrue(self.run_judge(c)["validity"]["v2"])

    def test_v2_recomputes_fp_sensitivity(self):
        # review 2026-10-16 (reviewer 1 scratch test, not among the relayed findings): the objdump reading is FP
        c = self.clean()
        c["crossdecoder"]["disagreements"].append({"config": "D", "variant": "k_avx2:matmul[F32]",
                                                   "xed_iclass": "VPADDD", "normalised": ["VADDPS"],
                                                   "fp_sensitive": False})
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_v3_absent_after_bound_is_final_tooling_failure(self):
        c = self.clean()
        c["rederivation"] = {"present": False}
        self.assertEqual(self.run_judge(c, AFTER)["outcomes"], ["tooling_failure"])

    def test_v3_mismatch_after_bound_uses_less_favourable_figure(self):
        c = self.clean()
        c["rederivation"] = {"present": True, "matches": False, "mismatches": ["P5"],
                             "figures": self.full_figures(c, u_all=10, p5_iclass=25)}
        v = self.run_judge(c, AFTER)
        self.assertEqual(v["amber_a"]["p5_iclass"], 25)
        self.assertEqual(v["outcomes"], ["amber_a"])

    def test_v4_mismatch(self):
        c = self.clean()
        c["record"]["sha256"]["fp_class"] = "0" * 64
        v = self.run_judge(c)
        self.assertFalse(v["validity"]["v4"])
        self.assertEqual(self.run_judge(c, AFTER)["outcomes"], ["tooling_failure"])

    def test_p2_and_canaries(self):
        c = self.clean()
        for v in c["variants"]:
            if v["config"] == "D" and v["slot"] == "matmul[F32]":
                v["p2_fma"] = 3
        self.assertEqual(self.run_judge(c)["outcomes"], ["amber_b"])
        c = self.clean()
        self.variant(c, "A", "hx_kernels_scalar", "act_quantize_q8")["p3"]["d1"] = "fail"
        self.assertEqual(self.run_judge(c)["outcomes"], ["amber_b"])
        c = self.clean()
        for v in c["variants"]:
            if v["config"] == "C" and v["table"] == "k_avx512" and v["slot"] == "matmul[F32]":
                v["p3"]["d2"] = [{"site": "tree16", "result": "unchecked"}]
        self.assertEqual(self.run_judge(c)["outcomes"], ["pass"])      # unchecked is reported, not flagged
        for v in c["variants"]:
            if v["config"] == "C" and v["table"] == "k_avx512" and v["slot"] == "matmul[F32]":
                v["p3"]["d2"] = [{"site": "tree16", "result": "mismatch"}]
        self.assertEqual(self.run_judge(c)["outcomes"], ["amber_b"])

    def test_approximation_iclass_flags_p3b(self):
        v = self.run_judge(self.clean(iclasses=["MOV", "VRCP14PS"]))
        self.assertIn("amber_b", v["outcomes"])

    def test_ninja_only_counts_when_union_member(self):
        c = self.clean()
        for v in c["variants"]:
            if v["config"] == "A-ninja":
                v["iclasses"] = {"VRCP14PS": 1}
                v["p2_fma"] = 2
        self.assertEqual(self.run_judge(c)["outcomes"], ["pass"])
        for v in c["variants"]:
            if v["config"] == "A-ninja":
                v["union_member"], v["ab_compare"] = True, "differs"
        self.assertIn("amber_b", self.run_judge(c)["outcomes"])

    def test_multiple_rows(self):
        c = self.clean(iclasses=fp_yes()[:30])
        c["configs"]["C"]["p3a"]["quant.c"] = {"a1": [], "a2": ["a2_gcc_assoc"]}
        for v in c["variants"]:
            if v["config"] == "A" and v["slot"] == "matmul[Q4]":
                v["coverage"]["gaps"].append({"cause": "fp_trust_dep"})
        self.assertEqual(self.run_judge(c)["outcomes"], ["amber_a", "amber_b", "amber_c"])

    def test_narrowing(self):
        c = self.clean()
        self.assertIsNone(self.run_judge(c)["narrowing"])
        v = self.run_judge(c, x2={"proved_loop_shapes": ["lockstep"]})
        self.assertFalse(v["narrowing"]["holds"])
        for x in c["variants"]:
            x["loops"] = [{"id": "L1", "tags": ["lockstep"], "not_computed_tags": ["peeled", "interchanged"]}]
        v = self.run_judge(c, x2={"proved_loop_shapes": ["lockstep"]})
        self.assertTrue(v["narrowing"]["holds"])        # unchecked peeled/interchanged: covered only by id
        ids = ["%s|%s:%s|L1" % (x["config"], x["table"], x["slot"]) for x in c["variants"]]
        v = self.run_judge(c, x2={"proved_loop_shapes": ["lockstep"], "proved_loop_ids": ids})
        self.assertFalse(v["narrowing"]["holds"])
        v = self.run_judge(c, x2={"verdict": "pass"})
        self.assertTrue(v["narrowing"]["holds"])
        for x in c["variants"]:
            x["loops"] = [{"id": "L1", "tags": ["other"]}]
        v = self.run_judge(c, x2={"proved_loop_shapes": ["lockstep", "other"]})
        self.assertTrue(v["narrowing"]["holds"])
        v = self.run_judge(c, x2={"proved_loop_shapes": ["other"], "proved_loop_ids": ids})
        self.assertFalse(v["narrowing"]["holds"])

    def test_classify_build(self):
        pin = COMPILERS["D"]
        ok = {"rc": 0, "compiler_sha256": pin}
        self.assertEqual(judge.classify_build([ok, ok], pin)[0], "ok")
        self.assertEqual(judge.classify_build([], pin)[0], "other")
        self.assertEqual(judge.classify_build([ok, ok], None)[0], "other")
        bad = {"rc": 1, "compiler_ran": True, "argv_matches_frozen": True, "compiler_sha256": pin,
               "errors": [{"file": "quant_avx512.c", "line": 237}]}
        self.assertEqual(judge.classify_build([bad, bad], pin)[0], "compile_failed")
        self.assertEqual(judge.classify_build([bad, ok], pin)[0], "other")
        self.assertEqual(judge.classify_build([dict(bad, compiler_ran=False), bad], pin)[0], "other")

    def test_evaluation_date(self):
        c = self.clean()
        d, basis = judge.evaluation_date(c, today=datetime.date(2026, 10, 20))
        self.assertEqual(d, datetime.date(2026, 10, 30))      # the latest census run is later than the clock
        d, _ = judge.evaluation_date(c, today=datetime.date(2026, 11, 20))
        self.assertEqual(d, datetime.date(2026, 11, 20))
        self.assertEqual(basis["latest_census_run_date"], "2026-10-30")


class TestReview20261016(Base):
    """Adversarial cases of the x0prep review (reviewer 1), each asserting what the record requires."""

    def test_fma_iclass_with_p2_counter_zero(self):
        c = self.clean()
        self.variant(c, "D", "k_avx2", "matmul[F32]")["iclasses"]["VFMADD231PS"] = 3
        v = self.run_judge(c)
        self.assertIn("amber_b", v["outcomes"])
        self.assertEqual([x["p2"] for x in v["amber_b"] if x["config"] == "D"], [3])

    def test_missing_p3a_for_config(self):
        c = self.clean()
        del c["configs"]["B-cmake"]["p3a"]
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])
        v = self.run_judge(c, AFTER)
        self.assertTrue(v["conservative_resolution"])
        self.assertIn("amber_b", v["outcomes"])          # conservative: P3(a) not evaluated counts as flagged

    def test_missing_p3a_for_one_file(self):
        c = self.clean()
        del c["configs"]["D"]["p3a"]["quant_avx512.c"]
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        self.assertTrue(v["validity_detail"]["v1_config_gaps"])

    def test_d1_missing(self):
        c = self.clean()
        for x in c["variants"]:
            x["p3"].pop("d1", None)
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["amber_b"])
        self.assertEqual({x["config"] for x in v["amber_b"]}, set(judge.MAIN))

    def test_d1_not_found_string(self):
        c = self.clean()
        self.variant(c, "A", "hx_kernels_scalar", "act_quantize_q8")["p3"]["d1"] = "not_found"
        self.assertIn("amber_b", self.run_judge(c)["outcomes"])

    def test_unknown_cause_after_bound_release(self):
        c = self.clean()
        self.variant(c, "A", "k_avx2", "matmul[Q8]")["coverage"]["gaps"].append({"cause": "weird", "detail": "x"})
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])
        v = self.run_judge(c, AFTER)
        self.assertTrue(v["conservative_resolution"])
        self.assertIn("amber_c", v["outcomes"])
        self.assertTrue(any(i["cause_original"] == "weird" for i in v["amber_c"]))

    def test_a_ninja_absent(self):
        c = self.clean()
        del c["configs"]["A-ninja"]
        c["variants"] = [v for v in c["variants"] if v["config"] != "A-ninja"]
        c["builds"] = [b for b in c["builds"] if b["config"] != "A-ninja"]
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["tooling_failure"])

    def test_a_ninja_tooling_compile_failure(self):
        c = self.clean()
        for b in c["builds"]:
            if b["config"] == "A-ninja":
                b.update(rc=1, compiler_ran=False, argv_matches_frozen=False)
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_a_ninja_missing_comparison(self):
        c = self.clean()
        self.variant(c, "A-ninja", "k_avx2", "matmul[F32]").pop("ab_compare")
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])
        c = self.clean()
        self.variant(c, "A-ninja", "k_avx2", "matmul[F32]")["ab_compare"] = "differs"   # but union_member false
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_v3_after_bound_without_figures(self):
        c = self.clean()
        c["rederivation"]["matches"] = False
        v = self.run_judge(c, AFTER)
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        self.assertFalse(v["conservative_resolution"])

    def test_rederivation_flag_and_gap_after_bound(self):
        c = self.clean()
        figs = self.full_figures(c)
        figs["D|k_avx2:matmul[F32]"] = {"flagged": True, "gap_causes": []}
        figs["A|k_avx512:matmul[Q8]"] = {"flagged": False, "gap_causes": ["unresolved_indirect"]}
        c["rederivation"] = {"present": True, "matches": False, "mismatches": ["p2 D"], "figures": figs}
        v = self.run_judge(c, AFTER)
        self.assertIn("amber_b", v["outcomes"])
        self.assertIn("amber_c", v["outcomes"])

    def test_v3_mismatch_before_bound(self):
        c = self.clean()
        c["rederivation"]["matches"] = False
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_error_location_not_in_census_file(self):
        c = self.clean()
        self.fail_build(c, "B-cmake", "quant_avx2.c",
                        errors=[{"file": "LINK", "line": None, "text": "fatal error LNK1104: cannot open file"}])
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_build_index_none_does_not_crash(self):
        c = self.clean()
        c["builds"].append({"config": "C", "file": "quant.c", "rc": 0, "compiler_ran": True,
                            "argv_matches_frozen": True, "errors": []})
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        self.assertTrue(v["validity_detail"]["schema"])

    def test_extra_variant(self):
        c = self.clean()
        x = copy.deepcopy(self.variant(c, "A", "k_avx2", "matmul[F32]"))
        x["slot"] = "matmul[F8]"
        c["variants"].append(x)
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_duplicate_variant(self):
        c = self.clean()
        c["variants"].append(copy.deepcopy(self.variant(c, "C", "k_avx2", "matmul[F32]")))
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_narrowing_empty_tags(self):
        c = self.clean()
        for x in c["variants"]:
            x["loops"] = [{"id": "L1", "tags": []}]
        v = self.run_judge(c, x2={"proved_loop_shapes": ["lockstep"], "proved_loop_ids": []})
        self.assertTrue(v["narrowing"]["holds"])

    def test_narrowing_missing_loops_field(self):
        c = self.clean()
        for x in c["variants"]:
            x.pop("loops")
        v = self.run_judge(c, x2={"proved_loop_shapes": ["lockstep"], "proved_loop_ids": []})
        self.assertTrue(v["narrowing"]["holds"])

    def test_fp16_bf16_3dnow_approximations(self):
        for ic in ("VRCPPH", "VRSQRTSH", "VRCPBF16", "PFRCP", "PFRSQIT1", "VEXP2PS"):
            c = self.clean()
            self.variant(c, "D", "k_avx512", "matmul[F16]")["iclasses"][ic] = 1
            self.assertIn("amber_b", self.run_judge(c)["outcomes"], ic)

    def test_slot_unresolved_no_gap(self):
        c = self.clean()
        self.variant(c, "A", "k_avx2", "matmul[Q4]")["coverage"] = {"slot_resolved": False, "gaps": []}
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_coverage_missing(self):
        c = self.clean()
        self.variant(c, "D", "k_avx2", "matmul[Q4]").pop("coverage")
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_empty_counted_set(self):
        c = self.clean()
        x = self.variant(c, "D", "k_avx512", "matmul[Q4]")
        x["iforms"], x["iclasses"] = {}, {}
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_only_build1_variants(self):
        c = self.clean()
        c["variants"] = [v for v in c["variants"] if not (v["config"] == "C" and v["build_index"] == 2)]
        self.assertEqual(self.run_judge(c)["outcomes"], ["tooling_failure"])

    def test_v4_scripts_and_xed_tables(self):
        c = self.clean()
        c["record"]["scripts_sha256"]["scripts/census_script.py"] = "0" * 64
        self.assertFalse(self.run_judge(c)["validity"]["v4"])
        c = self.clean()
        c["record"]["sha256"]["xed_tables"] = "0" * 64
        v = self.run_judge(c)
        self.assertFalse(v["validity"]["v4"])
        self.assertEqual(self.run_judge(c, AFTER)["outcomes"], ["tooling_failure"])


if __name__ == "__main__":
    unittest.main()
