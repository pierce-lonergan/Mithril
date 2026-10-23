"""Unit tests for Amendment X0-A1's census-level and verdict-level reporting (review of 2026-10-23; Claude, same family,
independent context): x0_census.py carries variants[].p3c_unscreened and variants[].p3c_frozen_reading, writes
metrics.x0_a1 and one note per unscreened loop; judge.py reports the verdict both ways ("both_ways": the decision list
evaluated a second time with P3(c) under the reading frozen at 152fa33). Added after the review of X0-A1 r2 (Claude,
same family, independent context): V3 of the frozen reading comes from its own comparison
(census "rederivation_frozen_reading", written by rederive/compare_x0.py), never from the amended one; the schema
check makes the two P3(c) lists, the unscreened list and the loop records agree; both_ways keeps the frozen reading's
validity_detail and notes; metrics.x0_a1 counts the flags of each reading alone. SYNTHETIC inputs only (no object
file, no Hearth code).
Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
COMPARE = os.path.join(os.path.dirname(SCRIPTS), "rederive", "compare_x0.py")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, HERE)
import judge  # noqa: E402
import test_census as TC  # noqa: E402  (module imports, so that discovery does not run their tests twice)
import test_judge as TJ  # noqa: E402

BEFORE = TJ.BEFORE
Q8 = ("C", "k_avx512", "matmul[Q8]")
P3C_MISMATCH = {"kind": "p3c", "key": "C|k_avx512:matmul[Q8]@1:0xd98", "census": True, "rederivation": False,
                "note": "synthetic"}


class TestJudgeBothWays(TJ.Base):
    def a1_census(self):
        """The clean census with X0-A1 fields: every variant's frozen reading equals its p3.c, except C's k_avx512 Q8
        in both builds, whose loop L1 is unscreened (0 lanes under X0-A1, 32 under the frozen reading, bound 0). The
        census's rederivation block (matches) is the comparison with p3.c, the amended lists; there is no
        rederivation_frozen_reading block."""
        c = self.clean()
        for v in c["variants"]:
            v["p3c_frozen_reading"] = list(v["p3"]["c"])
            v["p3c_unscreened"] = []
        for bi in (1, 2):
            v = self.variant(c, *Q8, bi)
            v["p3c_frozen_reading"] = ["L1"]
            v["p3c_unscreened"] = ["L1"]
            v["loops"] = [{"id": "L1", "tags": ["lockstep"], "unscreened": True, "acc_lanes_emitted": 0,
                           "acc_lanes_if_escaping_slots_were_registers": 32, "bound_used": 0}]
        return c

    def test_census_without_x0_a1_fields_has_no_both_ways(self):
        v = self.run_judge(self.clean())
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertNotIn("both_ways", v)

    def test_frozen_reading_v3_is_not_inherited_from_the_amended_comparison(self):
        """Review of X0-A1 r2, finding 1: without rederivation_frozen_reading, the amended block is not reused for a
        frozen reading whose P3(c) lists differ; its V3 is not_computed and its outcome tooling_failure."""
        v = self.run_judge(self.a1_census(), date=BEFORE)
        self.assertEqual(v["outcomes"], ["pass"])                              # the amended P3(c): no flag
        bw = v["both_ways"]
        self.assertTrue(bw["p3c_differs"])
        fr = bw["frozen_reading"]
        self.assertEqual(fr["outcomes"], ["tooling_failure"])
        self.assertEqual((fr["validity"]["v3"], fr["v3_basis"]), ("not_computed", "not_computed"))
        self.assertTrue(any("not computed" in n for n in fr["notes"]))
        self.assertTrue(bw["outcomes_differ"])
        self.assertEqual(len(bw["variants"]), 2)
        row = bw["variants"][0]
        self.assertEqual((row["config"], row["p3c"], row["p3c_frozen_reading"]), ("C", [], ["L1"]))
        self.assertEqual(row["unscreened_loops"][0]["acc_lanes_if_escaping_slots_were_registers"], 32)
        self.assertTrue(any("X0-A1" in n for n in v["notes"]))

    def test_both_ways_when_the_frozen_reading_flags_more(self):
        """The re-derivation follows X0-A1 (no flag on L1): the amended comparison matches, the frozen one has the
        P3(c) mismatch, so V3 fails under the frozen reading only, and its validity_detail shows why."""
        c = self.a1_census()
        c["rederivation_frozen_reading"] = {"present": True, "matches": False, "mismatches": [P3C_MISMATCH]}
        v = self.run_judge(c, date=BEFORE)
        self.assertEqual(v["outcomes"], ["pass"])
        fr = v["both_ways"]["frozen_reading"]
        self.assertEqual(fr["outcomes"], ["tooling_failure"])
        self.assertEqual((fr["validity"]["v3"], fr["v3_basis"]), (False, "rederivation_frozen_reading"))
        self.assertEqual(fr["validity_detail"]["v3"], [P3C_MISMATCH])
        self.assertEqual(v["validity_detail"]["v3"], [])

    def test_rederivation_matching_only_the_frozen_list(self):
        """Review of X0-A1 r2, finding 1: a re-deriver without X0-A1.1 flags L1 like the frozen reading. V3 fails for
        the amended reading and holds for the frozen one, whose P3(c) flag then gives Amber (b) under C."""
        c = self.a1_census()
        c["rederivation"] = {"present": True, "matches": False,
                             "mismatches": [dict(P3C_MISMATCH, census=False, rederivation=True)]}
        c["rederivation_frozen_reading"] = {"present": True, "matches": True, "mismatches": []}
        v = self.run_judge(c, date=BEFORE)
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        self.assertFalse(v["validity"]["v3"])
        bw = v["both_ways"]
        self.assertEqual(bw["frozen_reading"]["outcomes"], ["amber_b"])
        self.assertTrue(bw["frozen_reading"]["validity"]["v3"])
        self.assertEqual((bw["amber_b_configs"], bw["amber_b_configs_frozen_reading"]), ([], ["C"]))

    def test_frozen_block_matching_gives_amber_b_under_the_frozen_reading(self):
        c = self.a1_census()
        c["rederivation_frozen_reading"] = {"present": True, "matches": True, "mismatches": []}
        v = self.run_judge(c, date=BEFORE)
        bw = v["both_ways"]
        self.assertEqual((v["outcomes"], bw["frozen_reading"]["outcomes"]), (["pass"], ["amber_b"]))
        self.assertTrue(bw["outcomes_differ"])

    def test_both_ways_identical_when_the_readings_agree(self):
        c = self.clean()
        for v in c["variants"]:
            v["p3c_frozen_reading"] = list(v["p3"]["c"])
            v["p3c_unscreened"] = []
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertEqual(v["both_ways"]["frozen_reading"]["outcomes"], ["pass"])
        self.assertTrue(v["both_ways"]["frozen_reading"]["validity"]["v3"])
        self.assertTrue(v["both_ways"]["frozen_reading"]["v3_basis"].startswith("rederivation: the two readings"))
        self.assertFalse(v["both_ways"]["p3c_differs"])
        self.assertFalse(v["both_ways"]["outcomes_differ"])
        self.assertEqual(v["both_ways"]["variants"], [])

    def test_without_a_rederivation_both_readings_fail_v3_alike(self):
        c = self.a1_census()
        c["rederivation"] = {"present": False}
        v = self.run_judge(c, date=BEFORE)
        fr = v["both_ways"]["frozen_reading"]
        self.assertEqual((v["outcomes"], fr["outcomes"]), (["tooling_failure"], ["tooling_failure"]))
        self.assertIs(fr["validity"]["v3"], False)
        self.assertTrue(fr["v3_basis"].startswith("no re-derivation"))

    def test_the_input_census_is_not_changed_by_the_second_evaluation(self):
        c = self.a1_census()
        before = copy.deepcopy(c)
        judge.judge(c, self.cdir, BEFORE, judged_utc="2026-11-26T00:00:00Z", root=self.root)
        self.assertEqual(c, before)

    # ---- schema (review of X0-A1 r2, finding 2)
    def schema_of(self, c):
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        return v["validity_detail"]["schema"]

    def test_schema_types_the_x0_a1_lists(self):
        c = self.a1_census()
        self.variant(c, *Q8, 1)["p3c_frozen_reading"] = "L1"
        self.assertTrue(any("p3c_frozen_reading" in x for x in self.schema_of(c)))

    def test_schema_needs_both_lists(self):
        c = self.a1_census()
        del self.variant(c, *Q8, 1)["p3c_unscreened"]
        self.assertTrue(any("without p3c_unscreened" in x for x in self.schema_of(c)))

    def test_schema_refuses_a_frozen_flag_dropped_without_an_unscreened_loop(self):
        """The reviewer's case 4: p3.c flags L9 (32 lanes, bound 0), the frozen list is empty, nothing unscreened."""
        c = self.a1_census()
        x = self.variant(c, *Q8, 1)
        x["p3"]["c"], x["p3c_frozen_reading"], x["p3c_unscreened"] = ["L9"], [], []
        x["loops"] = [{"id": "L9", "tags": ["lockstep"], "unscreened": False, "acc_lanes_emitted": 32, "bound_used": 0}]
        bad = self.schema_of(c)
        self.assertTrue(any("which p3c_unscreened does not list" in b for b in bad))
        self.assertTrue(any("p3c_frozen_reading does not list" in b for b in bad))

    def test_schema_refuses_a_frozen_list_that_disagrees_with_the_loop_record(self):
        """The reviewer's case 5: L1 is unscreened with frozen count 32 > bound 0, but the frozen list is empty."""
        c = self.a1_census()
        for bi in (1, 2):
            self.variant(c, *Q8, bi)["p3c_frozen_reading"] = []
        bad = self.schema_of(c)
        self.assertTrue(any("frozen count 32 against bound 0, but p3c_frozen_reading does not list" in b for b in bad))

    def test_schema_refuses_an_unscreened_list_that_differs_from_the_loop_records(self):
        c = self.a1_census()
        self.variant(c, *Q8, 1)["p3c_unscreened"] = []
        self.assertTrue(any("differs from the loops marked unscreened" in b for b in self.schema_of(c)))

    def test_schema_refuses_an_unscreened_loop_without_its_frozen_count(self):
        c = self.a1_census()
        del self.variant(c, *Q8, 1)["loops"][0]["acc_lanes_if_escaping_slots_were_registers"]
        self.assertTrue(any("without a numeric acc_lanes_if_escaping_slots_were_registers" in b
                            for b in self.schema_of(c)))

    def test_schema_refuses_an_amended_flag_that_disagrees_with_the_loop_record(self):
        c = self.a1_census()
        x = self.variant(c, *Q8, 2)
        x["p3"]["c"] = ["L1"]                       # 0 lanes against bound 0: not a flag
        self.assertTrue(any("0 lanes against bound 0, but p3.c lists it" in b for b in self.schema_of(c)))

    def test_schema_types_the_frozen_rederivation_block(self):
        c = self.a1_census()
        c["rederivation_frozen_reading"] = []
        self.assertTrue(any("rederivation_frozen_reading is not an object" in b for b in self.schema_of(c)))

    def test_consistent_lists_pass_the_schema(self):
        self.assertEqual(judge.validate_schema(self.a1_census()), [])


class TestAssemblerX0A1(unittest.TestCase):
    def assemble(self, d):
        out = os.path.join(d, "census.json")
        p = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "x0_census.py"), "--run", d, "-o", out],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with open(out, encoding="utf-8") as f:
            return json.load(f)

    def test_loops_json_before_x0_a1_gives_the_frozen_reading_as_p3c(self):
        with tempfile.TemporaryDirectory() as d:
            TC.TestAssembler.make_run(None, d)
            c = self.assemble(d)
        for v in c["variants"]:
            self.assertEqual((v["p3c_frozen_reading"], v["p3c_unscreened"]), (v["p3"]["c"], []))
        self.assertEqual(c["metrics"]["x0_a1"]["A"]["unscreened_loops"], 0)
        self.assertEqual(c["metrics"]["x0_a1"]["A"]["p3c_flagged_loops_frozen_reading"], 2)    # L1, both builds
        self.assertEqual(c["schema_check"]["violations"], [])

    def test_unscreened_loop_reaches_census_json(self):
        with tempfile.TemporaryDirectory() as d:
            TC.TestAssembler.make_run(None, d)
            for bi in (1, 2):
                p = os.path.join(d, "A", "b%d" % bi, "all", "loops.json")
                with open(p) as fh:
                    lj = json.load(fh)
                lj[0]["p3"]["c"] = []
                lj[0]["p3c_unscreened"] = ["L1"]
                lj[0]["p3c_frozen_reading"] = ["L1"]
                lj[0]["loops"][0].update(unscreened=True, acc_lanes_emitted=0, bound_used=0,
                                         acc_lanes_if_escaping_slots_were_registers=32)
                with open(p, "w") as fh:
                    json.dump(lj, fh)
            c = self.assemble(d)
        a = [v for v in c["variants"] if v["config"] == "A"]
        self.assertTrue(all(v["p3"]["c"] == [] and v["p3c_frozen_reading"] == ["L1"] and v["p3c_unscreened"] == ["L1"]
                            for v in a))
        m = c["metrics"]["x0_a1"]["A"]
        self.assertEqual((m["unscreened_loops"], m["p3c_flagged_loops_frozen_reading_only"],
                          m["p3c_flagged_loops_x0a1_only"], m["p3c_flagged_loops"],
                          m["p3c_flagged_variants_frozen_reading"]), (2, 2, 0, 0, 2))
        self.assertNotIn("unscreened_loops_flagged_only_by_the_frozen_reading", m)
        notes = [n for n in c["notes"] if "unscreened (Amendment X0-A1)" in n]
        self.assertEqual(len(notes), 2)
        self.assertIn("0 lanes under X0-A1, 32 under the frozen reading, bound used 0", notes[0])
        self.assertIn("a P3(c) flag under the frozen reading only", notes[0])
        self.assertEqual(judge.validate_schema(c), [])
        self.assertEqual(c["schema_check"]["violations"], [])

    def test_assembler_reports_an_inconsistent_loops_json(self):
        """Review of X0-A1 r2, finding 2: x0_census.py's schema check (judge.validate_schema) catches a loops.json
        whose frozen-reading list drops a flag its loop record carries; the script exits 1."""
        with tempfile.TemporaryDirectory() as d:
            TC.TestAssembler.make_run(None, d)
            p = os.path.join(d, "A", "b1", "all", "loops.json")
            with open(p) as fh:
                lj = json.load(fh)
            lj[0]["p3"]["c"], lj[0]["p3c_unscreened"], lj[0]["p3c_frozen_reading"] = [], ["L1"], []
            lj[0]["loops"][0].update(unscreened=True, acc_lanes_emitted=0, bound_used=0,
                                     acc_lanes_if_escaping_slots_were_registers=32)
            with open(p, "w") as fh:
                json.dump(lj, fh)
            out = os.path.join(d, "census.json")
            r = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "x0_census.py"), "--run", d, "-o", out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            with open(out, encoding="utf-8") as f:
                c = json.load(f)
        self.assertTrue(any("p3c_frozen_reading does not list" in b for b in c["schema_check"]["violations"]))


def _load_compare():
    spec = importlib.util.spec_from_file_location("compare_x0_under_test", COMPARE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestCompareX0BothWays(unittest.TestCase):
    """rederive/compare_x0.py after the review of X0-A1 r2 (finding 1): the comparison is run once per reading."""

    KEY = "C|k_avx512:matmul[Q8]"

    def inputs(self, rederive_flags):
        """One union variant (C k_avx512 Q8, two builds) with loop L1 at 1:0xd98 flagged only under the frozen
        reading; the re-derivation flags it iff rederive_flags."""
        variants = []
        for bi in (1, 2):
            variants.append({"config": "C", "table": "k_avx512", "slot": "matmul[Q8]", "build_index": bi,
                             "coverage": {"slot_resolved": True, "gaps": []}, "iforms": {"RET_NEAR": 1},
                             "fp_sensitive": [], "p2_fma": 0, "p3": {"b": [], "c": []}, "n_instructions": 1,
                             "closure": [], "attribution": "exact",
                             "p3c_frozen_reading": ["L1_d98"], "p3c_unscreened": ["L1_d98"],
                             "loops": [{"id": "L1_d98", "header": [1, 0xd98], "acc_lanes_emitted": 0,
                                        "acc_lanes_if_escaping_slots_were_registers": 32, "bound_used": 0,
                                        "unscreened": True}]})
        C = {"variants": variants, "builds": [],
             "metrics": {"p2": {}, "p4_u_all": 1, "p5_iclass": 0,
                         "secondary": {"ab_compare": {}, "p5_opclass": 0, "fp_sensitive_iclasses": []}},
             "baseline": {"b_iform": 1, "b_mnem": 1, "t_forms": 1}, "rederivation": {"present": False}}
        F = {"p1": {self.KEY: {"slot_resolved": True, "gap_causes": []}}, "p2": {}, "p3b": [],
             "p3c": {self.KEY: ["r1"] if rederive_flags else []}, "p3d1": {}, "u_all": 1, "p5_iclass": 0,
             "p5_opclass": 0, "b_iform": 1, "b_mnem": 1, "t_forms": 1, "iforms": ["RET_NEAR"],
             "fp_sensitive_iclasses": []}
        D = {"variants": {"C|b%d|k_avx512:matmul[Q8]" % bi: {
            "loops": [{"id": "r1", "header": "f#1:0xd98", "flagged": rederive_flags}], "n_instructions": 1,
            "iform_list": ["RET_NEAR"], "closure": [], "attribution": "exact"} for bi in (1, 2)}}
        return F, D, C

    def run_main(self, F, D, C):
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for n, x in (("figures", F), ("detail", D), ("census", C)):
                paths[n] = os.path.join(d, n + ".json")
                with open(paths[n], "w") as fh:
                    json.dump(x, fh)
            oc, oz = os.path.join(d, "census_rd.json"), os.path.join(d, "comparison.json")
            r = subprocess.run([sys.executable, "-I", COMPARE, "--figures", paths["figures"], "--detail",
                                paths["detail"], "--census", paths["census"], "--out-comparison", oz,
                                "--out-census", oc], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(oc) as fh, open(oz) as fz:
                return json.load(fh), json.load(fz)

    def test_rederiver_following_x0a1_matches_only_the_amended_reading(self):
        c2, comp = self.run_main(*self.inputs(rederive_flags=False))
        self.assertTrue(c2["rederivation"]["matches"])
        f = c2["rederivation_frozen_reading"]
        self.assertFalse(f["matches"])
        self.assertEqual([(m["kind"], m["census"], m["rederivation"]) for m in f["mismatches"]], [("p3c", True, False)])
        self.assertEqual(f["figures"], c2["rederivation"]["figures"])
        self.assertFalse(comp["frozen_reading"]["matches"])

    def test_rederiver_without_x0a1_matches_only_the_frozen_reading(self):
        c2, _ = self.run_main(*self.inputs(rederive_flags=True))
        self.assertFalse(c2["rederivation"]["matches"])
        self.assertTrue(c2["rederivation_frozen_reading"]["matches"])

    def test_census_without_x0_a1_lists_gets_no_frozen_block(self):
        F, D, C = self.inputs(rederive_flags=False)
        for v in C["variants"]:
            del v["p3c_frozen_reading"], v["p3c_unscreened"]
        c2, comp = self.run_main(F, D, C)
        self.assertNotIn("rederivation_frozen_reading", c2)
        self.assertNotIn("reading", c2["rederivation"])
        self.assertNotIn("frozen_reading", comp)

    def test_compare_function_reads_the_requested_list(self):
        m = _load_compare()
        F, D, C = self.inputs(rederive_flags=False)
        self.assertEqual(m.compare(F, D, C)[0], [])
        self.assertEqual(len(m.compare(F, D, C, frozen_reading=True)[0]), 1)


if __name__ == "__main__":
    unittest.main()
