"""Unit tests for the smoke-source guard and the census-run ties of x0_driver.py (x0final revision after the independent
review of 2026-10-16/17: the first census mock contained verbatim Hearth helpers; pre-freeze review of 2026-10-17:
two-line Hearth runs and trailing comments, the freeze point, per-step script checks). SYNTHETIC text only; no Hearth
text is used here except the allow-listed structural declarations of class/hearth_shingles.json. git is replaced by
stubs: no repository is touched and no git command runs.
Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0_driver as D  # noqa: E402

NL = chr(10)


class TestShingles(unittest.TestCase):
    def test_nontrivial_lines(self):
        text = "#include <x.h>\n{\n  // a comment that is long enough\n  int   alpha = b + c;   \n}\n  return  value_of(a);\n"
        self.assertEqual(D.nontrivial_lines(text), ["int alpha = b + c;", "return value_of(a);"])

    def test_comments_are_stripped_and_dereferences_kept(self):
        """pre-freeze review of 2026-10-17: a trailing comment made an equal line differ; '*' lines were skipped."""
        a = "const float magic_value = 1.0f;   /* 1.5 * 2^23 */\n*out_pointer_value = magic_value;\n"
        b = "const float magic_value = 1.0f;\n*out_pointer_value = magic_value; // store\n"
        self.assertEqual(D.nontrivial_lines(a), D.nontrivial_lines(b))
        self.assertEqual(D.nontrivial_lines(a)[1], "*out_pointer_value = magic_value;")
        self.assertEqual(D.nontrivial_lines('const char *s = "// not a comment here";\n'),
                         ['const char *s = "// not a comment here";'])
        self.assertEqual(D.nontrivial_lines("int keep_this_line = 1; /* a\n b\n */ int next_line_kept = 2;\n"),
                         ["int keep_this_line = 1;", "int next_line_kept = 2;"])

    def test_shared_pair_is_found_whatever_the_spacing(self):
        a = "float t = alpha + beta;\nfloat u = t * gamma_value;\nreturn u - delta_value;\n"
        b = "{\n    float  t = alpha + beta;\n\n float u = t * gamma_value;\n}\n"
        self.assertTrue(set(D.shingles(a)) & set(D.shingles(b)))
        c = "float t = alpha + beta;\nfloat w = t * other_value;\nreturn w + delta_value;\n"
        self.assertFalse(set(D.shingles(a)) & set(D.shingles(c)))         # one shared line alone is not a pair
        allowed = frozenset(["float t = alpha + beta;", "float u = t * gamma_value;"])
        self.assertFalse(set(D.shingles(b, allowed=allowed)) & set(D.shingles(a)))

    def test_pinned_fingerprints_cover_the_pinned_blobs(self):
        root = os.path.dirname(os.path.dirname(HERE))
        sh = json.load(open(os.path.join(root, "class", "hearth_shingles.json")))
        bi = json.load(open(os.path.join(root, "class", "B_iform.json")))
        self.assertEqual(sh["hearth_blobs"], bi["inputs"]["hearth_blobs"])
        self.assertEqual((sh["k"], sh["definition"]), (D.SHINGLE_K, D.SHINGLE_DEFINITION))
        self.assertGreater(len(sh["shingles"]), 1000)
        self.assertEqual(len(sh["allowed_structural_lines"]), 13)

    def fake_shingles(self, text, allowed=()):
        real = D.jload

        def fake(path, default=None):
            if path.endswith("hearth_shingles.json"):
                pins = real(os.path.join(D.ROOT, "class", "B_iform.json"))["inputs"]["hearth_blobs"]
                return {"hearth_blobs": pins, "shingles": D.shingles(text), "k": D.SHINGLE_K,
                        "definition": D.SHINGLE_DEFINITION, "allowed_structural_lines": list(allowed)}
            return real(path, default)
        return real, fake

    def test_guard_refuses_a_source_sharing_a_pinned_pair(self):
        class A:
            mode = "replay"
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "s.c")
            text = "int first_line_here = 1;\nint second_line_here = 2;\n"
            open(src, "w").write("int other_line_number_one = 1;\nint more_line_number_two = 2;\n")
            real, fake = self.fake_shingles(text)
            D.jload = fake
            try:
                D.guard_sources(A(), {"kind": "smoke"}, {"files": [{"source": src}]}, d)
                open(os.path.join(d, "helper.c"), "w").write("/* x */\n" + text)    # a neighbour file is scanned too
                with self.assertRaises(SystemExit):
                    D.guard_sources(A(), {"kind": "smoke"}, {"files": [{"source": src}]}, d)
                os.remove(os.path.join(d, "helper.c"))
                open(os.path.join(d, "u16.h"), "wb").write("int x;".encode("utf-16"))   # not UTF-8: refused
                with self.assertRaises(SystemExit):
                    D.guard_sources(A(), {"kind": "smoke"}, {"files": [{"source": src}]}, d)
            finally:
                D.jload = real

    def test_census_mode_scans_every_source_and_include_file(self):
        class A:
            mode = "census"
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "engine", "src"))
            os.makedirs(os.path.join(d, "engine", "include"))
            for f in ("quant.c", "other.c", "hx.h"):
                open(os.path.join(d, "engine", "src", f), "w").write("int x;\n")
            open(os.path.join(d, "engine", "include", "api.h"), "w").write("int y;\n")
            got = {os.path.basename(p) for p in D.guard_paths(A(), None, d)}
        self.assertEqual(got, {"quant.c", "other.c", "hx.h", "api.h"})

    def test_current_smoke_sources_pass_the_guard(self):
        root = os.path.dirname(os.path.dirname(HERE))
        sh = json.load(open(os.path.join(root, "class", "hearth_shingles.json")))
        known, allowed = set(sh["shingles"]), frozenset(sh["allowed_structural_lines"])
        srcs = []
        for sub in ("smoke", os.path.join("smoke", "mock", "engine", "src"), "probes", os.path.join("runbook", "probes")):
            dd = os.path.join(root, "scripts", sub)
            srcs += [os.path.join(dd, f) for f in sorted(os.listdir(dd)) if f.endswith((".c", ".h"))]
        self.assertGreater(len(srcs), 12)
        for p in srcs:
            self.assertFalse(set(D.shingles(open(p, encoding="utf-8").read(), allowed=allowed)) & known, p)


class FakeGit:
    """A stub of `git` over a linear history: commits oldest first, each with the record's bytes; HEAD is the last."""

    def __init__(self, records, status="", ignored="", diff=""):
        self.records, self.status, self.ignored, self.diff = records, status, ignored, diff
        self.order = list(records)

    def __call__(self, *args, binary=False):
        out = ""
        if args[0] == "rev-parse":
            out = self.order[-1] + NL
        elif args[0] == "status":
            out = self.ignored if "--ignored" in args else self.status
        elif args[0] == "show":
            rev, _, path = args[1].partition(":")
            rev = self.order[-1] if rev == "HEAD" else rev
            data = self.records[rev]
            return data if binary else data.decode("utf-8")
        elif args[0] == "log":
            out = NL.join(self.order) + NL
        elif args[0] == "diff":
            out = self.diff
        return out.encode() if binary else out


class TestFreezeCheckout(unittest.TestCase):
    """A census run only from a clean checkout tied to the freeze point (x0final revision; pre-freeze review of
    2026-10-17: the freeze point is the first commit at which the record reads FROZEN, not HEAD)."""
    DRAFT = b"# X0\nStatus: DRAFT (to be FROZEN)\nbody\n"
    FROZEN = b"# X0\nStatus: FROZEN\nbody\n"
    REC = os.path.join(D.REPO, "docs", "m0", "prereg", "X0-census.md")

    def run_with(self, git, scripts=None, pins=None, record=None):
        return D.freeze_checkout(record or self.REC, {"scripts": pins if pins is not None else {"s": "1"}},
                                 scripts if scripts is not None else {"s": "1"}, git=git)

    def test_freeze_point_is_the_first_frozen_commit(self):
        g = FakeGit({"a" * 40: self.DRAFT, "b" * 40: self.FROZEN})
        t = self.run_with(g)
        self.assertEqual((t["freeze_commit"], t["run_commit"], t["post_freeze_changes"]), ("b" * 40, "b" * 40, []))
        amended = self.FROZEN + b"\n## Amendment 1 (2026-11-01)\nTooling fix in scripts/x0_loops.py.\n"
        g = FakeGit({"a" * 40: self.DRAFT, "b" * 40: self.FROZEN, "c" * 40: amended},
                    diff="experiments/x0-census/scripts/x0_loops.py" + NL)
        t = self.run_with(g)
        self.assertEqual((t["freeze_commit"], t["run_commit"]), ("b" * 40, "c" * 40))
        self.assertEqual(t["post_freeze_changes"], ["experiments/x0-census/scripts/x0_loops.py"])
        self.assertGreater(t["record_appended_bytes"], 0)

    def test_refusals(self):
        edited = b"# X0\nStatus: FROZEN\nbody with a changed threshold\n"
        cases = [
            FakeGit({"a" * 40: self.FROZEN}, status=" M experiments/x0-census/scripts/judge.py" + NL),     # dirty
            FakeGit({"a" * 40: self.DRAFT}),                                                            # not FROZEN
            FakeGit({"a" * 40: self.FROZEN, "b" * 40: edited}),                                         # body edited
            FakeGit({"a" * 40: self.FROZEN, "b" * 40: self.FROZEN + b"\n## Amendment\nreason only\n"},
                    diff="experiments/x0-census/class/fp_class.csv" + NL),                              # unnamed change
            FakeGit({"a" * 40: self.FROZEN, "b" * 40: self.FROZEN},
                    diff="experiments/x0-census/scripts/judge.py" + NL),                                # no amendment
            FakeGit({"a" * 40: self.FROZEN}, ignored="!! experiments/x0-census/scripts/judge.pyc" + NL),  # importable
        ]
        for g in cases:
            with self.assertRaises(SystemExit):
                self.run_with(g)
        g = FakeGit({"a" * 40: self.FROZEN})
        with self.assertRaises(SystemExit):
            self.run_with(g, scripts={"s": "2"})
        with self.assertRaises(SystemExit):
            self.run_with(g, record=os.path.join(D.ROOT, "elsewhere.md"))

    def test_pycache_is_tolerated(self):
        g = FakeGit({"a" * 40: self.FROZEN}, ignored="!! experiments/x0-census/scripts/__pycache__/" + NL +
                    "!! experiments/x0-census/scripts/tests/__pycache__/" + NL)
        self.assertEqual(self.run_with(g)["freeze_commit"], "a" * 40)


class TestCensusSteps(unittest.TestCase):
    """pre-freeze review of 2026-10-17: config and assemble re-check the tree init verified."""

    def setUp(self):
        self.pins = D.jload(os.path.join(D.ROOT, "class", "frozen_inputs.json"))
        self.real_git = D._git_runner

    def tearDown(self):
        D._git_runner = self.real_git

    def stub_git(self, head):
        D._git_runner = lambda repo: FakeGit({head: b"Status: FROZEN\n"})

    def test_recheck_needs_the_verified_scripts_and_commit(self):
        scripts = D.pinned_script_hashes(self.pins)
        self.stub_git("c" * 40)
        if scripts != self.pins["scripts"]:
            self.skipTest("this working tree's scripts differ from the pins (re-pin pending)")
        got, checked = D.recheck_census_tree({"scripts_sha256": scripts, "run_commit": "c" * 40}, self.pins)
        self.assertEqual(got, scripts)
        bad = dict(scripts)
        bad[sorted(bad)[0]] = "0" * 64
        with self.assertRaises(SystemExit):
            D.recheck_census_tree({"scripts_sha256": bad, "run_commit": "c" * 40}, self.pins)
        if os.name == "nt":
            with self.assertRaises(SystemExit):
                D.recheck_census_tree({"scripts_sha256": scripts, "run_commit": "d" * 40}, self.pins)

    def test_census_config_refuses_replaced_captures_and_assemble_refuses_commits(self):
        class A:
            pass
        with tempfile.TemporaryDirectory() as d:
            json.dump({"kind": "census", "source": d, "scripts_sha256": {}}, open(os.path.join(d, "run.json"), "w"))
            json.dump({}, open(os.path.join(d, "tools.json"), "w"))
            a = A()
            a.run, a.tools, a.config, a.frozen_db, a.design_time = d, os.path.join(d, "tools.json"), "C", "x.json", None
            with self.assertRaises(SystemExit) as cm:
                D.cmd_config(a)
            self.assertIn("frozen captures", str(cm.exception))
            b = A()
            b.run, b.tools, b.xml, b.freeze_commit, b.scripts_commit, b.qualify_tables = d, None, None, "e" * 40, None, False
            with self.assertRaises(SystemExit) as cm:
                D.cmd_assemble(b)
            self.assertIn("come from init", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
