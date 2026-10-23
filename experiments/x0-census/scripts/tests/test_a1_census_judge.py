"""Unit tests for Amendment X0-A1's census-level and verdict-level reporting (review of 2026-10-23; Claude, same family,
independent context): x0_census.py carries variants[].p3c_unscreened and variants[].p3c_frozen_reading, writes
metrics.x0_a1 and one note per unscreened loop; judge.py reports the verdict both ways ("both_ways": the decision list
evaluated a second time with P3(c) under the reading frozen at 152fa33). SYNTHETIC inputs only (no object file, no
Hearth code).
Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, HERE)
import judge  # noqa: E402
import test_census as TC  # noqa: E402  (module imports, so that discovery does not run their tests twice)
import test_judge as TJ  # noqa: E402

BEFORE = TJ.BEFORE


class TestJudgeBothWays(TJ.Base):
    def a1_census(self):
        """The clean census with X0-A1 fields: every variant's frozen reading equals its p3.c, except C's k_avx512 Q8
        in both builds, whose loop L1 is unscreened (0 lanes under X0-A1, 32 under the frozen reading, bound 0)."""
        c = self.clean()
        for v in c["variants"]:
            v["p3c_frozen_reading"] = list(v["p3"]["c"])
            v["p3c_unscreened"] = []
        for bi in (1, 2):
            v = self.variant(c, "C", "k_avx512", "matmul[Q8]", bi)
            v["p3c_frozen_reading"] = ["L1"]
            v["p3c_unscreened"] = ["L1"]
            v["loops"] = [{"id": "L1", "tags": ["lockstep"], "unscreened": True, "acc_lanes_emitted": 0,
                           "acc_lanes_if_escaping_slots_were_registers": 32, "bound_used": 0}]
        return c

    def test_census_without_x0_a1_fields_has_no_both_ways(self):
        v = self.run_judge(self.clean())
        self.assertEqual(v["outcomes"], ["pass"])
        self.assertNotIn("both_ways", v)

    def test_both_ways_when_the_frozen_reading_flags_more(self):
        v = self.run_judge(self.a1_census(), date=BEFORE)
        self.assertEqual(v["outcomes"], ["pass"])                              # the amended P3(c): no flag
        bw = v["both_ways"]
        self.assertTrue(bw["p3c_differs"])
        self.assertTrue(bw["outcomes_differ"])
        self.assertEqual(bw["frozen_reading"]["outcomes"], ["amber_b"])
        self.assertEqual((bw["amber_b_configs"], bw["amber_b_configs_frozen_reading"]), ([], ["C"]))
        self.assertEqual(len(bw["variants"]), 2)
        row = bw["variants"][0]
        self.assertEqual((row["config"], row["p3c"], row["p3c_frozen_reading"]), ("C", [], ["L1"]))
        self.assertEqual(row["unscreened_loops"][0]["acc_lanes_if_escaping_slots_were_registers"], 32)
        self.assertTrue(any("X0-A1" in n for n in v["notes"]))

    def test_both_ways_identical_when_the_readings_agree(self):
        c = self.clean()
        for v in c["variants"]:
            v["p3c_frozen_reading"] = list(v["p3"]["c"])
        v = self.run_judge(c)
        self.assertEqual(v["both_ways"]["frozen_reading"]["outcomes"], v["outcomes"])
        self.assertFalse(v["both_ways"]["p3c_differs"])
        self.assertFalse(v["both_ways"]["outcomes_differ"])
        self.assertEqual(v["both_ways"]["variants"], [])

    def test_the_input_census_is_not_changed_by_the_second_evaluation(self):
        c = self.a1_census()
        before = copy.deepcopy(c)
        judge.judge(c, self.cdir, BEFORE, judged_utc="2026-11-26T00:00:00Z", root=self.root)
        self.assertEqual([v["p3"]["c"] for v in c["variants"]], [v["p3"]["c"] for v in before["variants"]])

    def test_schema_types_the_x0_a1_lists(self):
        c = self.a1_census()
        self.variant(c, "C", "k_avx512", "matmul[Q8]", 1)["p3c_frozen_reading"] = "L1"
        v = self.run_judge(c)
        self.assertEqual(v["outcomes"], ["tooling_failure"])
        self.assertTrue(any("p3c_frozen_reading" in x for x in v["validity_detail"]["schema"]))


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
        self.assertEqual((m["unscreened_loops"], m["unscreened_loops_flagged_only_by_the_frozen_reading"],
                          m["p3c_flagged_loops"], m["p3c_flagged_variants_frozen_reading"]), (2, 2, 0, 2))
        notes = [n for n in c["notes"] if "unscreened (Amendment X0-A1)" in n]
        self.assertEqual(len(notes), 2)
        self.assertIn("0 lanes under X0-A1, 32 under the frozen reading, bound used 0", notes[0])
        self.assertIn("a P3(c) flag under the frozen reading only", notes[0])
        self.assertEqual(judge.validate_schema(c), [])


if __name__ == "__main__":
    unittest.main()
