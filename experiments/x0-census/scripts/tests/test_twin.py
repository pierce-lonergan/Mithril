"""Unit tests for x0_twin.py (debug-info twin attribution, record §4.6) on SYNTHETIC inputs (no object file, no Hearth
code). The CodeView annotation semantics tested here were measured on MSVC 19.44 and clang-cl 23.1.3 objects of the
NON-Hearth smoke file (x0final, 2026-10-16).

Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0_twin as T  # noqa: E402

CV_TEXT = """CodeViewDebugInfo [
  Section: .debug$S (2)
  Magic: 0x4
  Subsection [
    SubSectionType: InlineeLines (0xF6)
    SubSectionSize: 0x34
    InlineeSourceLine {
      Inlinee: helper (0x1002)
      FileID: D:\\src\\k.c (0x0)
      SourceLineNum: 80
    }
    InlineeSourceLine {
      Inlinee: inner (0x1003)
      FileID: D:\\src\\k.c (0x0)
      SourceLineNum: 10
    }
  ]
]
CodeViewDebugInfo [
  Section: .debug$S (12)
  Magic: 0x4
  Subsection [
    SubSectionType: Symbols (0xF1)
    SubSectionSize: 0x2FA
    ProcIdSym {
      Kind: S_LPROC32_ID (0x1146)
      PtrParent: 0x0
      CodeSize: 0x40
      CodeOffset: kern+0x0
      Segment: 0x0
      DisplayName: kern
      LinkageName: kern
    }
    InlineSiteSym {
      Kind: S_INLINESITE (0x114D)
      PtrParent: 0x0
      PtrEnd: 0x0
      Inlinee: helper (0x1002)
      BinaryAnnotations [
        ChangeLineOffset: 3
        ChangeCodeOffset: 0x10
        ChangeCodeLength: 0x8
        ChangeCodeOffset: 0x4
        ChangeCodeLength: 0x4
      ]
    }
    InlineSiteSym {
      Kind: S_INLINESITE (0x114D)
      PtrParent: 0x0
      PtrEnd: 0x0
      Inlinee: inner (0x1003)
      BinaryAnnotations [
        ChangeCodeLengthAndCodeOffset: {CodeOffset: 0x12, Length: 0x2}
      ]
    }
    InlineSiteEnd {
      Kind: S_INLINESITE_END (0x114E)
    }
    InlineSiteEnd {
      Kind: S_INLINESITE_END (0x114E)
    }
    ProcEnd {
      Kind: S_PROC_ID_END (0x114F)
    }
  ]
  Subsection [
    SubSectionType: Lines (0xF2)
    LinkageName: kern
  ]
  FunctionLineTable [
    LinkageName: kern
    Flags: 0x0
    CodeSize: 0x40
    FilenameSegment [
      Filename: D:\\src\\k.c (0x0)
      +0x0 [
        LineNumberStart: 100
        LineNumberEndDelta: 0
        IsStatement: Yes
      ]
      +0x10 [
        LineNumberStart: 105
        LineNumberEndDelta: 0
        IsStatement: Yes
      ]
      +0x20 [
        LineNumberStart: 106
        LineNumberEndDelta: 0
        IsStatement: Yes
      ]
    ]
  ]
]
"""


class FakeObj(dict):
    pass


class TestCodeView(unittest.TestCase):
    def test_msvc_closed_rows_leave_the_offset_at_their_start(self):
        """MSVC: ChangeCodeLengthAndCodeOffset deltas are measured from the previous row's start (measured: sd_rint
        in sd_act at 0x117, 0x13d, 0x162, 0x187, 0x1c4 for deltas 0x117, 0x26, 0x25, 0x25, 0x3d)."""
        site = {"inlinee_id": "0x1", "annots": [["ChangeLineOffset", 2]] + [["ChangeCodeLengthAndCodeOffset", d, 8]
                                                                               for d in (0x117, 0x26, 0x25, 0x25, 0x3D)]}
        rows, err = T.site_rows(site, {"0x1": {"line": 81, "file": "a.c"}})
        self.assertIsNone(err)
        self.assertEqual([r[0] for r in rows], [0x117, 0x13D, 0x162, 0x187, 0x1C4])
        self.assertTrue(all(r[1] - r[0] == 8 and r[3] == 83 for r in rows))

    def test_llvm_length_advances_the_offset(self):
        """clang-cl: after ChangeCodeLength the next ChangeCodeOffset counts from the end of the row (measured:
        0x12f+0x18, then +0x54 = 0x19b, then +0xc+0x23 = 0x1ca)."""
        site = {"inlinee_id": "0x1", "annots": [["ChangeLineOffset", 3], ["ChangeCodeOffset", 0x12F], ["ChangeCodeLength", 0x18],
                                                ["ChangeCodeOffset", 0x54], ["ChangeCodeLength", 0xC],
                                                ["ChangeCodeOffset", 0x23], ["ChangeCodeLength", 0xC]]}
        rows, err = T.site_rows(site, {"0x1": {"line": 80, "file": "a.c"}})
        self.assertIsNone(err)
        self.assertEqual([(r[0], r[1]) for r in rows], [(0x12F, 0x147), (0x19B, 0x1A7), (0x1CA, 0x1D6)])
        self.assertTrue(all(r[3] == 83 for r in rows))

    def test_open_row_closed_by_the_next_row(self):
        site = {"inlinee_id": "0x1", "annots": [["ChangeCodeOffset", 0x3A],
                                                ["ChangeCodeOffsetAndLineOffset", 0xA, 2], ["ChangeCodeLength", 0xE]]}
        rows, err = T.site_rows(site, {"0x1": {"line": 58, "file": "a.c"}})
        self.assertEqual([(r[0], r[1], r[3]) for r in rows], [(0x3A, 0x44, 58), (0x44, 0x52, 60)])

    def test_unterminated_row_is_an_error(self):
        rows, err = T.site_rows({"inlinee_id": "0x1", "annots": [["ChangeCodeOffset", 4]]}, {"0x1": {"line": 1}})
        self.assertIn("no end", err)

    def test_parse_codeview_nesting_and_innermost(self):
        procs, inl, errs = T.parse_codeview(CV_TEXT)
        self.assertEqual(errs, [])
        p = procs["kern"]
        self.assertEqual((p["sym"], p["off"], p["size"]), ("kern", 0, 0x40))
        self.assertEqual([s["depth"] for s in p["sites"]], [1, 2])
        self.assertEqual(inl["0x1002"]["line"], 80)
        obj = {"symbols": [{"name": "kern", "defined": True, "section": 5, "value": 0x100}]}
        ranges, rerr = T.codeview_ranges(obj, procs, inl)
        self.assertEqual(rerr, [])
        flat = T.innermost(ranges[5])
        at = {r[0]: (r[3], r[4]) for r in flat}
        self.assertEqual(at[0x100], (100, 0))          # procedure line table
        self.assertEqual(at[0x110], (83, 1))           # helper inlined (80 + 3)
        self.assertEqual(at[0x112], (10, 2))           # inner inlined into helper
        stacks = {r[0]: r[2] for r in T.stacks_all(ranges[5])}
        self.assertEqual(stacks[0x112], [["k.c", 10], ["k.c", 83], ["k.c", 105]])


class TestDwarfText(unittest.TestCase):
    def test_dwarfdump_rows_and_inlined(self):
        rows = T.parse_dwarfdump_rows(
            "debug_line[0x00000000]\nAddress Line\n0x0000000000000000     43      1      1   0             0       0  is_stmt\n"
            "0x0000000000000010     44      5      1   0             0       0 \n"
            "0x0000000000000020     44      5      1   0             0       0  end_sequence\n")
        self.assertEqual(rows, [[[0, 43, 1, False], [0x10, 44, 1, False], [0x20, 44, 1, True]]])
        inl = T.parse_dwarfdump_inlined(
            "0x00000214:     DW_TAG_inlined_subroutine\n"
            "                  DW_AT_abstract_origin\t(0x000005f0 \"f\")\n"
            "                  DW_AT_ranges\t(indexed (0x8) rangelist = 0x000000d4\n"
            "                     [0x0000000000000d53, 0x0000000000000d6e)\n"
            "                     [0x0000000000000d7d, 0x0000000000000d8b))\n"
            "                  DW_AT_call_line\t(90)\n\n"
            "0x0000026c:             DW_TAG_inlined_subroutine\n"
            "                          DW_AT_low_pc\t(0x0000000000000e95)\n"
            "                          DW_AT_high_pc\t(0x0000000000000f08)\n"
            "                          DW_AT_call_line\t(106)\n")
        self.assertEqual(inl, [{"ranges": [[0xD53, 0xD6E], [0xD7D, 0xD8B]], "call_line": 90},
                               {"ranges": [[0xE95, 0xF08]], "call_line": 106}])

    def test_dwarf_ranges_last_row_at_an_address_wins(self):
        tables = [{"files": ["a.c", "a.c"], "rows": [[1, 0, 10, 1, False], [1, 0, 11, 1, False], [1, 8, 12, 1, False],
                                                     [1, 16, 12, 1, True]]}]
        rng, unext = T.dwarf_ranges(tables)
        self.assertEqual(rng[1], [[0, 8, "a.c", 11, 0], [8, 16, "a.c", 12, 0]])
        self.assertEqual(unext, 0)

    def test_stacks_from_call_sites(self):
        base = {1: [[0, 8, "h.c", 5, 0], [8, 16, "k.c", 30, 0]]}
        frames = {1: [[0, 8, "k.c", 22, 1]]}
        st = {r[0]: r[2] for r in T.stacks_from(base, frames)[1]}
        self.assertEqual(st[0], [["h.c", 5], ["k.c", 22]])
        self.assertEqual(st[8], [["k.c", 30]])


class TestSourceRegions(unittest.TestCase):
    SRC = """/* a for in a comment */
static float tree(float *L)
{
    for (int s = 8; s >= 1; s >>= 1)
        for (int j = 0; j < s; j++) L[j] = L[j] + L[j + s];
    return L[0];
}

HX_INLINE void k(const float *x, int n) {
    int i = 0;
    while (i < n) {
        i++;
    }
    do {
        i--;
    } while (i > 0);
    const char *s = "for (;;)";
}
"""

    def test_loops_and_functions(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "k.c")
            with open(p, "w") as f:
                f.write(self.SRC)
            r = T.source_regions(p)
        self.assertEqual(r["loops"], [["for", 4, 4, 5], ["for", 5, 5, 5], ["while", 11, 11, 13], ["do", 14, 14, 16]])
        self.assertEqual(r["functions"]["tree"], [2, 7])
        self.assertEqual(r["functions"]["k"], [9, 18])


class TestFunctionIdentity(unittest.TestCase):
    """x0final revision (review of 2026-10-16/17): a section that differs only inside one function keeps the other
    functions exact (same size, same relocation offsets and types)."""

    def obj(self):
        return {"symbols": [{"name": "f", "defined": True, "section": 2, "type": "func", "value": 0, "size": 8},
                            {"name": "g", "defined": True, "section": 2, "type": "func", "value": 8, "size": 8},
                            {"name": "h", "defined": True, "section": 3, "type": "func", "value": 0, "size": 4}]}

    def test_byte_difference_in_one_function(self):
        cb, tb = bytes(range(16)), bytes(range(8)) + bytes([99]) + bytes(range(9, 16))
        cr = [[2, "PC32", "x", -4], [10, "PC32", "y", -4]]
        fns = T.function_identity(self.obj(), 2, cb, tb, cr, cr)
        self.assertEqual([(f["name"], f["identical"]) for f in fns], [("f", True), ("g", False)])

    def test_relocation_target_difference_in_one_function(self):
        cb = bytes(16)
        cr = [[2, "PC32", "x", -4], [10, "PC32", "y", -4]]
        tr = [[2, "PC32", "x", -4], [10, "PC32", "z", -4]]
        fns = T.function_identity(self.obj(), 2, cb, cb, cr, tr)
        self.assertEqual([(f["name"], f["identical"]) for f in fns], [("f", True), ("g", False)])

    def test_size_or_offset_change_keeps_the_section_rule(self):
        cr = [[2, "PC32", "x", -4]]
        self.assertIsNone(T.function_identity(self.obj(), 2, bytes(16), bytes(17), cr, cr))
        self.assertIsNone(T.function_identity(self.obj(), 2, bytes(16), bytes(16), cr, [[3, "PC32", "x", -4]]))


if __name__ == "__main__":
    unittest.main()
