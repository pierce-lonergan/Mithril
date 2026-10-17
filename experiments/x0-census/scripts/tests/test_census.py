"""Unit tests for the census.json assembler (x0_census.py) on a SYNTHETIC run directory (no object file, no Hearth
code). The end-to-end runs on NON-Hearth objects are runbook steps 83-90 (scripts/README.md).
Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import judge  # noqa: E402


def dump(obj, *parts):
    p = os.path.join(*parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f)


class TestAssembler(unittest.TestCase):
    def make_run(self, d):
        dump({"run_id": "t1", "kind": "smoke", "profile": "hearth", "scripts_sha256": {"scripts/x.py": "00"}}, d, "run.json")
        for cfg, a1 in (("A", []), ("A-ninja", []), ("B-cmake", ["a1_ffp_contract_on"])):
            dump({"role": "release", "census_files": [{"id": "quant.c", "source": "q.c"}],
                  "p3a": {"quant.c": {"a1": a1, "a2": [], "hits": []}}, "compiler": {"path": "cl.exe"},
                  "steps": [{"step": "build1", "utc_start": "2026-10-16T00:00:00+00:00", "utc_end": "2026-10-16T00:01:00+00:00"}]},
                 d, cfg, "config.json")
            for bi in (1, 2):
                dump({"config": cfg, "file": "quant.c", "build_index": bi, "rc": 0, "compiler_ran": True,
                      "compiler_sha256": {"cl.exe": "aa"}, "argv_sha256": "bb", "argv_matches_frozen": True, "errors": [],
                      "includes": [], "ice": False, "object_exists": False, "object": None}, d, cfg, "builds", "quant.c.b%d.json" % bi)
                dump({"unit": "all", "files": [{"id": "quant.c", "source": "q.c", "object": "/x/q.obj"}]},
                     d, cfg, "b%d" % bi, "all", "unit.json")
                dump([{"config": cfg, "object": "q.obj", "table": "hx_kernels_scalar", "slot": "matmul[F32]", "symbol": "f",
                       "coverage": {"slot_resolved": True, "gaps": []}, "iforms": {"RET_NEAR": 1, "VFMADD231PS_YMMqq_YMMqq_YMMqq": 1},
                       "iclasses": {"RET_NEAR": 1, "VFMADD231PS": 1, "RCPPS": 1}, "p2_fma": 1,
                       "closure": [{"symbol": "f", "section_index": 3}]}], d, cfg, "b%d" % bi, "all", "decode", "variants.json")
                dump({"disagreements": []}, d, cfg, "b%d" % bi, "all", "decode", "crossdecoder.json")
                dump([{"table": "hx_kernels_scalar", "slot": "matmul[F32]", "key_is_canary": False, "attribution": "exact",
                       "p3": {"c": ["L1"], "d2": [{"site": "tree16", "result": "unchecked"}]},
                       "loops": [{"id": "L1", "tags": ["lockstep"], "not_computed_tags": []}]}],
                     d, cfg, "b%d" % bi, "all", "loops.json")

    def test_assembles_a_schema_conforming_census(self):
        with tempfile.TemporaryDirectory() as d:
            self.make_run(d)
            out = os.path.join(d, "census.json")
            p = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "x0_census.py"), "--run", d, "-o", out],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            with open(out, encoding="utf-8") as f:
                c = json.load(f)
        self.assertEqual(judge.validate_schema(c), [])
        self.assertEqual(c["schema_check"]["violations"], [])
        self.assertEqual(len(c["builds"]), 6)
        self.assertEqual(c["record"]["scripts_sha256"], {"scripts/x.py": "00"})
        an = [v for v in c["variants"] if v["config"] == "A-ninja"]
        self.assertEqual({v["ab_compare"] for v in an}, {"differs"})          # no objects: cannot be identical
        self.assertTrue(all(v["union_member"] for v in an))
        b = [v for v in c["variants"] if v["config"] == "B-cmake"][0]
        self.assertEqual(b["p3"]["a1"], ["a1_ffp_contract_on"])
        self.assertEqual(b["p3"]["b"], ["RCPPS"])
        self.assertEqual(b["p3"]["c"], ["L1"])
        self.assertEqual(c["metrics"]["p4_u_all"], 2)
        self.assertEqual(c["metrics"]["p2"]["B-cmake"], 2)                    # both builds
        self.assertFalse(c["rederivation"]["present"])

    def test_attribution_none_is_a_gap_and_the_freeze_commit_comes_from_init(self):
        """x0final revision (review of 2026-10-16/17): a twin attribution of none is a tooling gap; the init step's
        freeze commit reaches record.freeze_commit and record.scripts_commit."""
        with tempfile.TemporaryDirectory() as d:
            self.make_run(d)
            rj = os.path.join(d, "run.json")
            r = json.load(open(rj))
            r["freeze_commit"] = "c" * 40
            dump(r, rj)
            lj = os.path.join(d, "A", "b1", "all", "loops.json")
            lr = json.load(open(lj))
            lr[0]["attribution"], lr[0]["attribution_detail"] = "none", "twin line table unusable: x"
            dump(lr, lj)
            out = os.path.join(d, "census.json")
            p = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "x0_census.py"), "--run", d, "-o", out],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            c = json.load(open(out, encoding="utf-8"))
        self.assertEqual((c["record"]["freeze_commit"], c["record"]["scripts_commit"]), ("c" * 40, "c" * 40))
        a1 = [v for v in c["variants"] if v["config"] == "A" and v["build_index"] == 1][0]
        a2 = [v for v in c["variants"] if v["config"] == "A" and v["build_index"] == 2][0]
        self.assertEqual([g["cause"] for g in a1["coverage"]["gaps"]], ["other"])
        self.assertIn("twin attribution none", a1["coverage"]["gaps"][0]["detail"])
        self.assertEqual(a2["coverage"]["gaps"], [])

    def test_census_run_takes_commits_from_init_only(self):
        """pre-freeze review of 2026-10-17: in a census run --freeze-commit is refused; the freeze point, the run
        commit, the post-freeze change list and each configuration's script hashes reach census.json."""
        with tempfile.TemporaryDirectory() as d:
            self.make_run(d)
            rj = os.path.join(d, "run.json")
            r = json.load(open(rj))
            r.update(kind="census", freeze_commit="c" * 40, run_commit="e" * 40,
                     post_freeze_changes=["experiments/x0-census/scripts/x0_loops.py"])
            dump(r, rj)
            for cfg in ("A", "A-ninja"):
                cp = os.path.join(d, cfg, "config.json")
                cj = json.load(open(cp))
                cj["scripts_sha256"] = {"scripts/x.py": "00"}
                dump(cj, cp)
            out = os.path.join(d, "census.json")
            argv = [sys.executable, "-I", os.path.join(SCRIPTS, "x0_census.py"), "--run", d, "-o", out]
            p = subprocess.run(argv + ["--freeze-commit", "c" * 40], capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("REFUSED", p.stdout + p.stderr)
            p = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            c = json.load(open(out, encoding="utf-8"))
        rec = c["record"]
        self.assertEqual((rec["id"], rec["freeze_commit"], rec["run_commit"], rec["scripts_commit"]),
                         ("X0-census", "c" * 40, "e" * 40, "e" * 40))
        self.assertEqual(rec["post_freeze_changes"], ["experiments/x0-census/scripts/x0_loops.py"])
        self.assertEqual(c["configs"]["A"]["scripts_sha256"], {"scripts/x.py": "00"})
        self.assertIsNone(c["configs"]["B-cmake"]["scripts_sha256"])
        self.assertTrue(any("B-cmake ran other scripts" in n for n in c["notes"]))


if __name__ == "__main__":
    unittest.main()
