"""Unit tests for the P3(a) matcher (x0_flags.match_p3a) and class/fp_flag_patterns.txt.

Inputs are synthetic token lists plus the pre-freeze effective-flag captures in flags/prefreeze/ (configure-only
runs and `-###` / `gcc -Q` on a dummy source; no Hearth object). Run:
  python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0_flags as F  # noqa: E402

PAT = os.path.join(HERE, "..", "..", "class", "fp_flag_patterns.txt")
PRE = os.path.join(HERE, "..", "..", "flags", "prefreeze")
FLAGS = os.path.join(HERE, "..", "..", "flags")


def read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


class TestPatterns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = F.load_patterns(PAT)

    def m(self, **kw):
        return F.match_p3a(self.p, **kw)

    def test_msvc(self):
        self.assertEqual(self.m(argv=["cl", "/O2", "/fp:precise"])["a1"], [])
        self.assertEqual(self.m(argv=["cl", "/fp:contract"])["a1"], ["a1_msvc_fp_contract"])
        self.assertEqual(self.m(argv=["cl", "-fp:fast"])["a2"], ["a2_msvc_fp_fast"])
        self.assertEqual(self.m(argv=["cl", "/Qfast_transcendentals"])["a2"], ["a2_msvc_fast_transcendentals"])

    def test_clang_tokens(self):
        for t, cls, pid in (("-ffp-contract=on", "a1", "a1_ffp_contract_on"), ("-ffp-contract=fast", "a1", "a1_ffp_contract_on"),
                            ("-ffp-contract=fast-honor-pragmas", "a1", "a1_ffp_contract_on"),
                            ("-ffast-math", "a2", "a2_ffast_math"), ("-mreassociate", "a2", "a2_mreassociate"),
                            ("-fdenormal-fp-math=preserve-sign,preserve-sign", "a2", "a2_fdenormal_fp_math"),
                            ("-fdenormal-fp-math-f32=positive-zero", "a2", "a2_fdenormal_fp_math_f32"),
                            ("-fno-signed-zeros", "a2", "a2_fno_signed_zeros"), ("-menable-no-nans", "a2", "a2_menable_no_nans")):
            self.assertIn(pid, self.m(cc1=["-cc1", t])[cls], t)
        self.assertEqual(self.m(cc1=["-cc1", "-ffp-contract=off", "-fdenormal-fp-math=ieee"]), {"a1": [], "a2": [], "hits": []})

    def test_clang_cl_passthrough(self):
        self.assertIn("a2_ffast_math", self.m(argv=["clang-cl", "/clang:-ffast-math"])["a2"])
        self.assertIn("a1_ffp_contract_on", self.m(argv=["clang", "-Xclang", "-ffp-contract=fast"])["a1"])
        self.assertEqual(self.m(argv=["clang-cl", "/clang:-ffp-contract=off"])["a1"], [])

    def test_gcc_effective_values(self):
        g = F.parse_gccq("  -ffp-contract=[off|on|fast]        fast\n  -fsigned-zeros      [disabled]\n"
                         "  -fassociative-math   [enabled]\n  -freciprocal-math [disabled]\n")
        r = self.m(gccq=g)
        self.assertEqual(r["a1"], ["a1_gcc_effective"])
        self.assertEqual(r["a2"], ["a2_gcc_assoc", "a2_gcc_signed_zeros"])
        g = F.parse_gccq("  -ffp-contract=[off|on|fast]        off\n  -fsigned-zeros      [enabled]\n")
        self.assertEqual(self.m(gccq=g)["a1"], [])

    def test_parse_cc1_windows_escapes(self):
        line = ' "D:\\\\llvm\\\\clang.exe" "-cc1" "-ffp-contract=on" "-I" "C:\\\\a b"'
        self.assertEqual(F.parse_cc1(line), ["D:\\llvm\\clang.exe", "-cc1", "-ffp-contract=on", "-I", "C:\\a b"])

    def test_prefreeze_captures(self):
        """The captured effective flags: B-cmake contracts (E1), B-proxy, C and D do not; no a2 anywhere."""
        for q in ("quant.c", "quant_avx2.c", "quant_avx512.c"):
            b = F.parse_cc1(read(os.path.join(PRE, "B-cmake.%s.cc1.txt" % q)))
            self.assertEqual(self.m(cc1=b)["a1"], ["a1_ffp_contract_on"], q)
            bp = F.parse_cc1(read(os.path.join(PRE, "B-proxy.%s.cc1.txt" % q)))
            self.assertEqual(self.m(cc1=bp), {"a1": [], "a2": [], "hits": []}, q)
            d = F.parse_cc1(read(os.path.join(PRE, "D-clang.%s.cc1.txt" % q)))
            self.assertEqual(self.m(cc1=d), {"a1": [], "a2": [], "hits": []}, q)
            g = F.parse_gccq(read(os.path.join(PRE, "C-gcc.%s.gccq.txt" % q)))
            self.assertTrue(any(x.startswith("-ffp-contract=") for x in g))
            self.assertEqual(self.m(gccq=g), {"a1": [], "a2": [], "hits": []}, q)
            for db in (os.path.join(PRE, "A-ninja.compile_commands.json"), os.path.join(FLAGS, "C-gcc.compile_commands.json")):
                with open(db) as f:
                    e = [x for x in json.load(f) if os.path.basename(x["file"]) == q][0]
                self.assertEqual(self.m(argv=F.entry_argv(e))["a1"] + self.m(argv=F.entry_argv(e))["a2"], [], db)

    def test_proxy_argv_order(self):
        b = ["clang-cl", "/O2", "/fp:precise", "/arch:AVX512", "/W3", "/FoX.obj", "-c", "--", "q.c"]
        d = ["clang", "-O3", "-mavx512f", "-mfma", "-c", "-o", "q.o", "q.c"]
        out = F.proxy_argv(b, d)
        self.assertNotIn("/fp:precise", out)
        self.assertNotIn("/arch:AVX512", out)
        self.assertLess(out.index("/clang:-mfma"), out.index("--"))
        self.assertLess(out.index("/clang:-ffp-contract=off"), out.index("/FoX.obj"))


if __name__ == "__main__":
    unittest.main()
