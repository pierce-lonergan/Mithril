"""Unit tests for x0_build.py (census build records: record §5 P1 compile rule inputs) on SYNTHETIC text (no compiler
is run, no Hearth code). Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0_build as B  # noqa: E402

BS = chr(92)


def win(p):
    return p.replace("/", BS)


class TestDiagnostics(unittest.TestCase):
    def test_error_formats(self):
        text = "\n".join([
            win("D:/h/engine/src/quant_avx512.c") + "(237,22): error: always_inline function '_mm512_dpbusd_epi32' "
            "requires target feature 'avx512vnni'",                                       # clang-cl
            win("D:/h/engine/src/quant.c") + "(12,5): error C2065: 'x': undeclared identifier [" + win("D:/b/h.vcxproj") + "]",
            "/mnt/d/h/engine/src/quant.c:40:3: error: 'y' undeclared",                     # GCC / clang
            "/usr/lib/gcc/x86_64-linux-gnu/13/include/avx512vnniintrin.h:43:1: error: inlining failed in call to "
            "'always_inline' '_mm512_dpbusd_epi32': target specific option mismatch",
            "cl : Command line error D8021 : invalid numeric argument '/arch:X'",
            win("D:/h/a.c") + "(3): warning C4244: conversion"])
        e = B.parse_errors(text)
        self.assertEqual([(os.path.basename(x["file"].replace(BS, "/")) if x["file"] else None, x["line"]) for x in e],
                         [("quant_avx512.c", 237), ("quant.c", 12), ("quant.c", 40), ("avx512vnniintrin.h", 43), (None, None)])
        self.assertNotIn("vcxproj", e[1]["text"])

    def test_ice(self):
        self.assertTrue(B.ICE_RE.search("x.c(3) : fatal error C1001: Internal compiler error."))
        self.assertTrue(B.ICE_RE.search("PLEASE submit a bug report to https://github.com/llvm/llvm-project/issues/"))
        self.assertTrue(B.ICE_RE.search("during GIMPLE pass: vect\nx.c:3:1: internal compiler error: Segmentation fault"))
        self.assertFalse(B.ICE_RE.search("x.c:3:1: error: expected ';'"))

    def test_includes(self):
        msvc = "Note: including file: " + win("C:/VC/include/immintrin.h") + "\nNote: including file:  " + win("C:/VC/include/x.h") + "\nquant.c\n"
        self.assertEqual(B.parse_includes(msvc, True), [win("C:/VC/include/immintrin.h"), win("C:/VC/include/x.h")])
        gnu = ". /usr/include/stdint.h\n.. /usr/include/x86_64-linux-gnu/bits/types.h\nMultiple include guards may be useful for:\n/usr/include/y.h\n"
        self.assertEqual(B.parse_includes(gnu, False), ["/usr/include/stdint.h", "/usr/include/x86_64-linux-gnu/bits/types.h"])


class TestFrozen(unittest.TestCase):
    CL = ["C:/VC/cl.exe", "/nologo", "-DX", "/O2", "/fp:precise", "/arch:AVX512", "/FoCMakeFiles/q.c.obj", "/FdCMakeFiles/", "/FS",
          "-c", "D:/h/engine/src/quant_avx512.c"]

    def test_same_flags_match(self):
        other = list(self.CL)
        other[6] = "/FoD:/elsewhere/q.c.obj"                    # plumbing only
        fc = B.frozen_compare(other, other[-1], self.CL, self.CL[-1])
        self.assertTrue(fc["argv_matches_frozen"])

    def test_extra_flag_is_a_difference(self):
        other = self.CL[:-1] + ["/fp:fast", self.CL[-1]]
        fc = B.frozen_compare(other, other[-1], self.CL, self.CL[-1])
        self.assertFalse(fc["argv_matches_frozen"])
        self.assertEqual(fc["frozen_diff"]["only_run"], ["/fp:fast"])

    def test_twin_flag_removed_before_comparing(self):
        twin = self.CL[:-2] + ["/Z7", "/c", "/FoT.obj", self.CL[-1]]
        self.assertTrue(B.frozen_compare(twin, twin[-1], self.CL, self.CL[-1], ["/Z7"])["argv_matches_frozen"])
        self.assertFalse(B.frozen_compare(self.CL, self.CL[-1], self.CL, self.CL[-1], ["/Z7"])["argv_matches_frozen"])

    def test_source_swap_for_replay(self):
        rep = self.CL[:-1] + ["D:/x0/smoke/smoke_dispatch.c"]
        self.assertTrue(B.frozen_compare(rep, rep[-1], self.CL, self.CL[-1])["argv_matches_frozen"])


LOG = """Task "CL" skipped, due to false condition; (...)
Task "CL"
  Task Parameter:Sources=...
  C:\\VC\\bin\\HostX64\\x64\\CL.exe /c /ID:\\h\\src /nologo /W3 /O2 /fp:precise /Fo"core.dir\\Release\\\\" /TC D:\\h\\src\\pool.c D:\\h\\src\\quant.c
  Tracking command:
  C:\\VS\\Tracker.exe /d "C:\\VS\\FileTracker64.dll" /i D:\\b\\core.dir\\Release\\core.tlog /r D:\\H\\SRC\\POOL.C|D:\\H\\SRC\\QUANT.C /c CL.exe /c ...
  pool.c
D:\\h\\src\\pool.c(5,1): error C2143: syntax error: missing ';' before '}' [D:\\b\\core.vcxproj]
  quant.c
C:\\VS\\MSBuild\\Microsoft.CppCommon.targets(800,5): error MSB6006: "CL.exe" exited with code 2. [D:\\b\\core.vcxproj]
Done executing task "CL" -- FAILED.
Task "CL"
  C:\\VC\\bin\\HostX64\\x64\\CL.exe /c /ID:\\h\\src /nologo /W3 /O2 /arch:AVX512 /fp:precise /Fo"core.dir\\Release\\\\" /TC D:\\h\\src\\quant_avx512.c
  Tracking command:
  C:\\VS\\Tracker.exe /d x /c CL.exe
  quant_avx512.c
Done executing task "CL".
"""


class TestMsbuild(unittest.TestCase):
    def test_blocks_sections_and_batch_rc(self):
        blocks = B.msbuild_cl_blocks(LOG)
        self.assertEqual(len(blocks), 2)
        b0, b1 = blocks
        self.assertEqual([os.path.basename(s.replace(BS, "/")) for s in b0["sources"]], ["pool.c", "quant.c"])
        self.assertEqual(b0["rc"], 2)
        self.assertTrue(b0["failed"])
        self.assertEqual(len(B.parse_errors("\n".join(b0["sections"]["pool.c"]))), 1)
        # the MSB6006 line names no source file: quant.c's own section holds no located error
        self.assertEqual([e for e in B.parse_errors("\n".join(b0["sections"]["quant.c"])) if e["file"]
                          and e["file"].lower().endswith(".c")], [])
        self.assertEqual(b1["rc"], 0)
        self.assertFalse(b1["failed"])
        self.assertIn("/arch:AVX512", b1["cmd"])

    def test_design_time_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "dt.txt")
            with open(p, "w") as f:
                f.write("# comment\ncmd:   /c /W3 /Ob2 /fp:precise /Fo\"x\\\\\"\nfiles: " + win("D:/h/src/pool.c") + ";" + win("D:/h/src/quant.c") + "\n")
            dt = B.parse_design_time(p)
        self.assertEqual(sorted(dt), ["pool.c", "quant.c"])
        self.assertIn("/fp:precise", dt["quant.c"])


# x0final revision (independent review of 2026-10-16/17): A's line must be the design-time line plus exactly /O2, in
# order. The lines below have the shape measured on a NON-Hearth Visual Studio project (runbook/logs/
# x0final_rev_probes.log): the design-time line omits /nologo, /diagnostics:column, /O2 and the /Fd plumbing.
DT = ['/c', '/W1', '/WX-', '/Ob2', '/D', '_MBCS', '/D', 'NDEBUG', '/MD', '/arch:AVX2', '/fp:precise',
      '/Fo"msbp.dir\\Release\\\\"', '/external:W1', '/TC', '/errorReport:queue']
SRC = "D:\\p\\src\\c_avx2.c"
BUILD = ['C:\\VC\\CL.exe', '/c', '/nologo', '/W1', '/WX-', '/diagnostics:column', '/O2', '/Ob2', '/D', '_MBCS', '/D',
         'NDEBUG', '/MD', '/arch:AVX2', '/fp:precise', '/Fo"msbp.dir\\Release\\\\"', '/Fd"msbp.dir\\Release\\msbp.pdb"',
         '/external:W1', '/TC', '/errorReport:queue', SRC]


class TestDesignTimeDelta(unittest.TestCase):
    def test_measured_shape_matches(self):
        fc = B.design_time_compare(BUILD, SRC, DT)
        self.assertTrue(fc["argv_matches_frozen"])
        self.assertEqual(fc["frozen_diff"]["only_build"], ["/O2"])

    def test_debug_optimisation_is_a_difference(self):
        """review: /Od, /Ob0 instead of /Ob2 were tolerated by the optimisation-switch rule."""
        b = [t if t != "/Ob2" else "/Ob0" for t in BUILD]
        b.insert(b.index("/O2") + 1, "/Od")
        fc = B.design_time_compare(b, SRC, DT)
        self.assertFalse(fc["argv_matches_frozen"])
        self.assertEqual(fc["frozen_diff"]["only_design_time"], ["/Ob2"])
        self.assertFalse(B.design_time_compare([t for t in BUILD if t != "/O2"], SRC, DT)["argv_matches_frozen"])
        self.assertFalse(B.design_time_compare(BUILD[:6] + ["/O1"] + BUILD[7:], SRC, DT)["argv_matches_frozen"])
        self.assertFalse(B.design_time_compare(BUILD[:-1] + ["/GL", SRC], SRC, DT)["argv_matches_frozen"])

    def test_reordered_last_wins_switches_are_a_difference(self):
        dt = DT[:10] + ["/fp:strict", "/fp:precise"] + DT[11:]
        b = BUILD[:14] + ["/fp:precise", "/fp:strict"] + BUILD[15:]
        fc = B.design_time_compare(b, SRC, dt)
        self.assertFalse(fc["argv_matches_frozen"])
        self.assertFalse(fc["frozen_diff"]["same_order_without_delta"])


SINGLE = """Task "CL"
  C:\\VC\\bin\\HostX64\\x64\\CL.exe /c /ID:\\h\\src /nologo /W3 /O2 /arch:AVX2 /fp:precise /Fo"core.dir\\Release\\\\" /TC D:\\h\\src\\quant_avx2.c
  Tracking command:
  C:\\VS\\Tracker.exe /d x /c CL.exe
  quant_avx2.c
Done executing task "CL".
"""


class TestBatchErrorOwnership(unittest.TestCase):
    def test_error_of_another_batch_source_is_not_this_files(self):
        """x0final revision, measured on the mock with a broken other.c: its error was printed after quant.c's echo."""
        log = LOG.replace("  pool.c\nD:\\h\\src\\pool.c(5,1)", "  pool.c\n  quant.c\nD:\\h\\src\\pool.c(5,1)").replace(
            "  quant.c\nC:\\VS", "C:\\VS")
        b0 = B.msbuild_cl_blocks(log)[0]
        sec = "\n".join(b0["sections"]["quant.c"])
        self.assertEqual(len(B.parse_errors(sec)), 2)                 # pool.c's error and MSBuild's MSB6006 line
        with tempfile.TemporaryDirectory() as d:
            blog = os.path.join(d, "b.log")
            open(blog, "w").write(log)
            os.makedirs(os.path.join(d, "core.dir", "Release"))
            open(os.path.join(d, "core.dir", "Release", "quant.obj"), "w").write("x")

            class A:
                pass
            a = A()
            a.log, a.project_dir, a.files, a.config, a.build_index = blog, d, "quant.c", "A", 1
            a.outdir, a.design_time, a.msbuild_rc, a.since, a.reference_record = os.path.join(d, "rec"), None, 1, 0, None
            a.single_log = []
            B.cmd_msbuild(a)
            import json
            r = json.load(open(os.path.join(d, "rec", "quant.c.b1.json")))
        self.assertEqual((r["rc"], r["errors"]), (0, []))


class TestSingleFileFallback(unittest.TestCase):
    def test_file_missing_from_the_build_log_comes_from_its_single_log(self):
        """MSBuild stopped after the failed pool.c/quant.c batch [M, probe]; quant_avx2.c was compiled alone."""
        with tempfile.TemporaryDirectory() as d:
            blog, slog, out = os.path.join(d, "b.log"), os.path.join(d, "s.log"), os.path.join(d, "rec")
            open(blog, "w").write(LOG.replace(LOG[LOG.index('Task "CL"\n  C:\\VC\\bin\\HostX64\\x64\\CL.exe /c /ID:\\h\\src /nologo /W3 /O2 /arch'):], ""))
            open(slog, "w").write(SINGLE)

            class A:
                pass
            a = A()
            a.log, a.project_dir, a.files, a.config, a.build_index = blog, d, "quant.c,quant_avx2.c,quant_avx512.c", "A", 1
            a.outdir, a.design_time, a.msbuild_rc, a.since, a.reference_record = out, None, 1, 0, None
            a.single_log = ["quant_avx2.c=" + slog]
            B.cmd_msbuild(a)
            import json
            r2 = json.load(open(os.path.join(out, "quant_avx2.c.b1.json")))
            r5 = json.load(open(os.path.join(out, "quant_avx512.c.b1.json")))
        self.assertTrue(r2["compiler_ran"])
        self.assertIn("/arch:AVX2", r2["argv"])
        self.assertTrue(r2["fallback"].startswith("single-file ClCompile"))
        self.assertFalse(r5["compiler_ran"])                   # no CL block anywhere: tooling, never success
        self.assertFalse(r5["object_exists"])


if __name__ == "__main__":
    unittest.main()
