"""Unit tests for the smoke-source guard of x0_driver.py (x0final revision after the independent review of
2026-10-16/17: the first census mock contained verbatim Hearth helpers). SYNTHETIC text only; no Hearth text is used
here (class/hearth_shingles.json holds only hashes).
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


class TestShingles(unittest.TestCase):
    def test_nontrivial_lines(self):
        text = "#include <x.h>\n{\n  // a comment that is long enough\n  int   alpha = b + c;   \n}\n  return  value_of(a);\n"
        self.assertEqual(D.nontrivial_lines(text), ["int alpha = b + c;", "return value_of(a);"])

    def test_shared_run_of_three_lines_is_found_whatever_the_spacing(self):
        a = "float t = alpha + beta;\nfloat u = t * gamma_value;\nreturn u - delta_value;\n"
        b = "{\n    float  t = alpha + beta;\n\n float u = t * gamma_value;\n  return u - delta_value;\n}\n"
        self.assertTrue(set(D.shingles(a)) & set(D.shingles(b)))
        c = "float t = alpha + beta;\nfloat u = t * gamma_value;\nreturn u + delta_value;\n"
        self.assertFalse(set(D.shingles(a)) & set(D.shingles(c)))

    def test_pinned_fingerprints_cover_the_pinned_blobs(self):
        root = os.path.dirname(os.path.dirname(HERE))
        sh = json.load(open(os.path.join(root, "class", "hearth_shingles.json")))
        bi = json.load(open(os.path.join(root, "class", "B_iform.json")))
        self.assertEqual(sh["hearth_blobs"], bi["inputs"]["hearth_blobs"])
        self.assertGreater(len(sh["shingles"]), 1000)

    def test_guard_refuses_a_source_sharing_a_pinned_run(self):
        class A:
            mode = "replay"
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "s.c")
            text = "int first_line_here = 1;\nint second_line_here = 2;\nint third_line_here = 3;\n"
            open(src, "w").write(text)
            real = D.jload

            def fake(path, default=None):
                if path.endswith("hearth_shingles.json"):
                    pins = real(os.path.join(D.ROOT, "class", "B_iform.json"))["inputs"]["hearth_blobs"]
                    return {"hearth_blobs": pins, "shingles": D.shingles(text)}
                return real(path, default)
            D.jload = fake
            try:
                with self.assertRaises(SystemExit):
                    D.guard_sources(A(), {"kind": "smoke"}, {"files": [{"source": src}]}, d)
                open(src, "w").write("int other_line_number_one = 1;\nint second_line_here = 2;\nint third_line_here = 3;\n")
                D.guard_sources(A(), {"kind": "smoke"}, {"files": [{"source": src}]}, d)
            finally:
                D.jload = real

    def test_current_smoke_sources_pass_the_guard(self):
        root = os.path.dirname(os.path.dirname(HERE))
        known = set(json.load(open(os.path.join(root, "class", "hearth_shingles.json")))["shingles"])
        srcs = []
        for sub in ("smoke", os.path.join("smoke", "mock", "engine", "src"), "probes"):
            dd = os.path.join(root, "scripts", sub)
            srcs += [os.path.join(dd, f) for f in sorted(os.listdir(dd)) if f.endswith((".c", ".h"))]
        self.assertGreater(len(srcs), 8)
        for p in srcs:
            self.assertFalse(set(D.shingles(open(p, encoding="utf-8").read())) & known, p)


class TestFreezeCheckout(unittest.TestCase):
    """x0final revision (review of 2026-10-16/17): a census run only from a clean checkout whose record reads FROZEN
    at HEAD. git is replaced by a stub here (no repository is touched)."""

    NL = chr(10)

    def run_with(self, status, record_text, scripts=None, pins=None, record=None):
        class P:
            def __init__(self, out, rc=0):
                self.stdout, self.stderr, self.returncode = out, "", rc

        def fake(argv, capture_output=True, text=True):
            if "rev-parse" in argv:
                return P("a" * 40 + self.NL)
            if "status" in argv:
                return P(status)
            if "show" in argv:
                return P(record_text)
            return P("", 1)
        real = D.subprocess.run
        D.subprocess.run = fake
        try:
            repo = os.path.dirname(os.path.dirname(D.ROOT))
            rec = record or os.path.join(repo, "docs", "m0", "prereg", "X0-census.md")
            return D.freeze_checkout(rec, {"scripts": pins if pins is not None else {"s": "1"}},
                                     scripts if scripts is not None else {"s": "1"})
        finally:
            D.subprocess.run = real

    def test_clean_frozen_checkout_gives_head(self):
        self.assertEqual(self.run_with("", "# X0" + self.NL + "Status: FROZEN (commit x)" + self.NL), "a" * 40)

    def test_refusals(self):
        nl = self.NL
        with self.assertRaises(SystemExit):
            self.run_with(" M experiments/x0-census/scripts/judge.py" + nl, "Status: FROZEN" + nl)
        with self.assertRaises(SystemExit):
            self.run_with("", "Status: DRAFT (to be FROZEN ...)" + nl)
        with self.assertRaises(SystemExit):
            self.run_with("", "Status: FROZEN" + nl, scripts={"s": "2"})
        with self.assertRaises(SystemExit):
            self.run_with("", "Status: FROZEN" + nl, record=os.path.join(D.ROOT, "elsewhere.md"))


if __name__ == "__main__":
    unittest.main()
