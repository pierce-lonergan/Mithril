"""Unit tests for the x0final additions to x0_loops.py, on SYNTHETIC instruction records (no object file, no Hearth
code): back-edge accumulators and partial results, call clobbers, peeled, interchanged, the d2 site checker (trimming,
live-in widths, the VSHUFPD / VPERMILPD forms Clang emits) and source-loop attribution through the inline stack.
Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0_loops as L  # noqa: E402


def ins(ic, ops, fields, length=4, succ=None):
    r = {"iclass": ic, "operands": [o + "/X/EXPLICIT" for o in ops], "fields": fields, "len": length, "hex": "00" * length}
    if succ is not None:
        r["succ"] = succ
    return r


def vop(ic, dst, a, b, imm=None):
    f = {"REG0": dst, "REG1": a, "REG2": b}
    ops = ["REG0/W", "REG1/R", "REG2/R"]
    if imm is not None:
        f["IMM0"] = hex(imm)
        ops.append("IMM0/R")
    return ins(ic, ops, f)


def build(seq, edges):
    insts = {(1, 4 * k): i for k, i in enumerate(seq)}
    succ = {(1, 4 * k): [(1, 4 * t) for t in edges.get(k, [k + 1] if k + 1 < len(seq) else [])] for k in range(len(seq))}
    return insts, succ


class TestBackEdgeAccumulators(unittest.TestCase):
    def setUp(self):
        L.ABI["current"] = "elf"

    def test_register_overwritten_before_the_back_edge_is_not_an_accumulator(self):
        """MSVC reuses the mask register xmm1: MAXSS writes it, a constant load overwrites it before the latch."""
        seq = [ins("NOP", [], {}),
               ins("MOVSS", ["REG0/W", "MEM0/R"], {"REG0": "XMM0", "MEM0": "ptr [RAX]"}),                  # 1 header
               ins("ANDPS", ["REG0/RW", "REG1/R"], {"REG0": "XMM0", "REG1": "XMM1"}),                       # uses mask
               ins("MAXSS", ["REG0/RW", "MEM0/R"], {"REG0": "XMM0", "MEM0": "ptr [RSP+0xc0]"}),             # acc slot
               ins("MAXSS", ["REG0/RW", "REG1/R"], {"REG0": "XMM1", "REG1": "XMM0"}),                       # writes xmm1
               ins("MOVSS", ["MEM0/W", "REG0/R"], {"REG0": "XMM1", "MEM0": "ptr [RSP+0xc0]"}),              # store acc
               ins("MOVDQA", ["REG0/W", "MEM0/R"], {"REG0": "XMM1", "MEM0": "ptr [RIP+0x0]"}),              # mask back
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = build(seq, {7: [1, 8]})
        loops, preds = L.natural_loops((1, 0), succ)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        self.assertEqual(info["accumulators"], {"STK:RSP:192": 1})
        self.assertEqual(info["acc_lanes_emitted"], 1)
        self.assertEqual(info["carried_overwritten_before_back_edge"], ["V1"])

    def test_register_and_its_spill_copy_are_one_partial_result(self):
        seq = [ins("NOP", [], {}),
               vop("VADDPS", "YMM0", "YMM0", "YMM1"),                                                         # 1 header
               ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "YMM0", "MEM0": "ptr [RSP+0x20]"}),
               ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "YMM2", "MEM0": "ptr [RSP+0x20]"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = build(seq, {4: [1, 5]})
        loops, preds = L.natural_loops((1, 0), succ)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        self.assertEqual(info["acc_lanes_emitted"], 8)
        self.assertEqual(len(info["partial_results"]), 1)

    def test_call_return_value_is_not_loop_carried(self):
        """GCC -fPIC: xmm0 holds the return value of an interposable call before MULSS reads it."""
        seq = [ins("NOP", [], {}),
               ins("CALL_NEAR", ["RELBR/R"], {}),                                                             # 1 header
               ins("MULSS", ["REG0/RW", "REG1/R"], {"REG0": "XMM0", "REG1": "XMM2"}),
               ins("ADDSS", ["REG0/RW", "REG1/R"], {"REG0": "XMM1", "REG1": "XMM0"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = build(seq, {4: [1, 5]})
        loops, preds = L.natural_loops((1, 0), succ)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        # xmm1 is caller-saved under SysV: the call kills it, so even the ADDSS chain is not carried in registers
        self.assertEqual(info["acc_lanes_emitted"], 0)
        L.ABI["current"] = "coff"                    # Win64: xmm6-xmm15 survive calls
        seq[3] = ins("ADDSS", ["REG0/RW", "REG1/R"], {"REG0": "XMM6", "REG1": "XMM0"})
        insts, succ = build(seq, {4: [1, 5]})
        loops, preds = L.natural_loops((1, 0), succ)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        self.assertEqual(info["accumulators"], {"V6": 1})
        L.ABI["current"] = "elf"


class TestMovingFramePointer(unittest.TestCase):
    def test_rbp_used_as_a_data_pointer_is_not_a_stack_slot(self):
        """GCC -O3: Y[r] = Y[r] * c through [rbp], rbp += 4 each iteration (regression set, rv_coldsw under C)."""
        seq = [ins("NOP", [], {}),
               ins("VMULSS", ["REG0/W", "REG1/R", "MEM0/R"], {"REG0": "XMM0", "REG1": "XMM1", "MEM0": "ptr [RBP]"}),
               ins("VMOVSS", ["MEM0/W", "REG0/R"], {"REG0": "XMM0", "MEM0": "ptr [RBP]"}),
               ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RBP", "IMM0": "0x4"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = build(seq, {4: [1, 5]})
        loops, preds = L.natural_loops((1, 0), succ)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        self.assertEqual(info["accumulators"], {})
        seq[3] = ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RAX", "IMM0": "0x4"})     # rbp invariant: a real slot
        insts, succ = build(seq, {4: [1, 5]})
        loops, preds = L.natural_loops((1, 0), succ)
        self.assertEqual(L.analyse_loop(loops[0], insts, succ, preds)["accumulators"], {"STK:RBP:0": 1})


class TestPeeledInterchanged(unittest.TestCase):
    def test_peeled_copy_before_the_header(self):
        seq = [vop("VMULPS", "YMM2", "YMM3", "YMM4"), vop("VADDPS", "YMM0", "YMM0", "YMM2"),                 # peeled
               vop("VMULPS", "YMM2", "YMM3", "YMM5"), vop("VADDPS", "YMM0", "YMM0", "YMM2"),                 # 2 header
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = build(seq, {4: [2, 5]})
        gpreds = {}
        for n, ss in succ.items():
            for s in ss:
                gpreds.setdefault(s, []).append(n)
        loops, preds = L.natural_loops((1, 0), succ)
        pe, regs = L.peeled_check(loops[0], insts, succ, gpreds)
        self.assertTrue(pe)
        self.assertEqual(regs[0]["where"], "before")

    def test_no_copy_no_peel(self):
        seq = [ins("NOP", [], {}), vop("VMULPS", "YMM2", "YMM3", "YMM5"), vop("VADDPS", "YMM0", "YMM0", "YMM2"),
               ins("JNZ", ["RELBR/R"], {}), vop("VADDPS", "YMM0", "YMM0", "YMM1"), ins("RET_NEAR", [], {})]
        insts, succ = build(seq, {3: [1, 4]})
        gpreds = {}
        for n, ss in succ.items():
            for s in ss:
                gpreds.setdefault(s, []).append(n)
        loops, preds = L.natural_loops((1, 0), succ)
        self.assertFalse(L.peeled_check(loops[0], insts, succ, gpreds)[0])   # an ADD alone is not MUL+ADD

    def test_interchanged(self):
        outer = {"_body": {1, 2, 3, 4}, "attribution": "exact", "source_loop_lines": [20, 22], "tags": []}
        inner = {"_body": {2, 3}, "attribution": "exact", "source_loop_lines": [10, 30], "tags": []}
        L.interchange_tags([outer, inner])
        self.assertIn("interchanged", outer["tags"])
        self.assertEqual(outer["not_computed_tags"], [])
        ok_o = {"_body": {1, 2, 3, 4}, "attribution": "exact", "source_loop_lines": [10, 30], "tags": []}
        ok_i = {"_body": {2, 3}, "attribution": "exact", "source_loop_lines": [20, 22], "tags": []}
        L.interchange_tags([ok_o, ok_i])
        self.assertNotIn("interchanged", ok_o["tags"])
        nx_o = {"_body": {1, 2, 3, 4}, "attribution": "exact", "source_loop_lines": [10, 30], "tags": []}
        nx_i = {"_body": {2, 3}, "attribution": "none", "source_loop_lines": None, "tags": []}
        L.interchange_tags([nx_o, nx_i])
        self.assertEqual(nx_o["not_computed_tags"], ["interchanged"])
        lone = {"_body": {1, 2}, "attribution": "none", "source_loop_lines": None, "tags": []}
        L.interchange_tags([lone])
        self.assertEqual(lone["not_computed_tags"], [])


class TestD2Sites(unittest.TestCase):
    def site(self, seq):
        insts = {(1, 4 * k): i for k, i in enumerate(seq)}
        return sorted(insts), insts

    def test_clang_avx2_tree_with_shufpd_and_trailing_canonicalisation(self):
        seq = [vop("VADDPS", "YMM1", "YMM2", "YMM1"), vop("VEXTRACTF128", "XMM2", "YMM1", "YMM1", 1),
               vop("VADDPS", "XMM1", "XMM1", "XMM2"), vop("VSHUFPD", "XMM2", "XMM1", "XMM1", 1),
               vop("VADDPS", "XMM1", "XMM1", "XMM2"), ins("VMOVSHDUP", ["REG0/W", "REG1/R"], {"REG0": "XMM2", "REG1": "XMM1"}),
               vop("VADDSS", "XMM1", "XMM1", "XMM2"), vop("VCMPSS", "XMM2", "XMM1", "XMM1", 3),
               ins("VBLENDVPS", ["REG0/W", "REG1/R", "REG2/R", "REG3/R"], {"REG0": "XMM1", "REG1": "XMM1", "REG2": "XMM0", "REG3": "XMM2"})]
        seq[1] = ins("VEXTRACTF128", ["REG0/W", "REG1/R", "IMM0/R"], {"REG0": "XMM2", "REG1": "YMM1", "IMM0": "0x1"})
        order, insts = self.site(seq)
        res, reason, s = L.check_d2_site(order, [], insts)
        self.assertEqual(res, "match", reason)
        self.assertEqual(s[-1][0], "VADDSS")            # trimmed after the tree's last ADD

    def test_gcc_avx512_copy_of_low_half(self):
        seq = [ins("VMOVAPD", ["REG0/W", "REG1/R"], {"REG0": "YMM1", "REG1": "YMM0"}),
               ins("VEXTRACTF64X4", ["REG0/W", "REG1/R", "IMM0/R"], {"REG0": "YMM0", "REG1": "ZMM0", "IMM0": "0x1"}),
               vop("VADDPS", "YMM1", "YMM1", "YMM0"),
               ins("VEXTRACTF128", ["REG0/W", "REG1/R", "IMM0/R"], {"REG0": "XMM0", "REG1": "YMM1", "IMM0": "0x1"}),
               vop("VADDPS", "XMM0", "XMM0", "XMM1"), vop("VMOVHLPS", "XMM1", "XMM0", "XMM0"),
               vop("VADDPS", "XMM0", "XMM0", "XMM1"),
               ins("VPERMILPS", ["REG0/W", "REG1/R", "IMM0/R"], {"REG0": "XMM1", "REG1": "XMM0", "IMM0": "0x1"}),
               vop("VADDSS", "XMM0", "XMM0", "XMM1")]
        order, insts = self.site(seq)
        res, reason, _ = L.check_d2_site(order, [], insts)
        self.assertEqual(res, "match", reason)

    def test_wrong_pairing_still_mismatches_after_trimming(self):
        seq = [ins("VEXTRACTF64X4", ["REG0/W", "REG1/R", "IMM0/R"], {"REG0": "YMM1", "REG1": "ZMM0", "IMM0": "0x1"}),
               vop("VADDPS", "YMM0", "YMM0", "YMM1"),
               ins("VEXTRACTF128", ["REG0/W", "REG1/R", "IMM0/R"], {"REG0": "XMM1", "REG1": "YMM0", "IMM0": "0x1"}),
               vop("VADDPS", "XMM0", "XMM0", "XMM1"), vop("VSHUFPS", "XMM1", "XMM0", "XMM0", 0xB1),
               vop("VADDPS", "XMM0", "XMM0", "XMM1"), vop("VMOVHLPS", "XMM1", "XMM0", "XMM0"),
               vop("VADDSS", "XMM0", "XMM0", "XMM1")]
        order, insts = self.site(seq)
        self.assertEqual(L.check_d2_site(order, [], insts)[0], "mismatch")

    def test_vpermilpd_swap(self):
        st = L.track_tree16([("VEXTRACTF64X4", "V1", ["V0"], 1), ("VADDPS", "V0", ["V0", "V1"], None),
                             ("VEXTRACTF128", "V1", ["V0"], 1), ("VADDPS", "V0", ["V0", "V1"], None),
                             ("VPERMILPD", "V1", ["V0"], 1), ("VADDPS", "V0", ["V0", "V1"], None),
                             ("VMOVSHDUP", "V1", ["V0"], None), ("VADDSS", "V0", ["V0", "V1"], None)], ["V0"])
        self.assertEqual(st, "match")


class TestStackAttribution(unittest.TestCase):
    A = {"sources": {"k.c": {"loops": [["for", 50, 50, 60], ["for", 52, 52, 55]], "functions": {}},
                     "h.h": {"loops": [], "functions": {}}}}

    def test_inlined_helper_without_loop_falls_back_to_the_call_site(self):
        sl = L.Attribution.source_loop_of_stack(self.A, [("avx512fintrin.h", 12821), ("h.h", 7), ("k.c", 53)])
        self.assertEqual(sl[0], "k.c:52")
        self.assertEqual(sl[4], 2)

    ROWS = {"k.c:75": {"loop_id": "k.c:75", "source_lanes": "8", "trip_count": "4 (s = 8 4 2 1)"},
            "k.c:76": {"loop_id": "k.c:76", "source_lanes": "0", "trip_count": "s"},
            "k.c:90": {"loop_id": "k.c:90", "source_lanes": "128", "trip_count": "nb"},
            "k.c:92": {"loop_id": "k.c:92", "source_lanes": "0", "trip_count": "tn"}}
    AD = {"sources": {"k.c": {"loop_vars": {"75": "s", "76": "j", "90": "g", "92": "t"}}}}

    def test_header_in_flattened_inner_loop_latch_in_outer(self):
        outer = ("k.c:75", "for", 75, 76, 0)
        inner = ("k.c:76", "for", 76, 76, 0)
        # x0final: the outer loop when the two nest; x0final revision: only with the signs of flattening
        sl, how, rule = L.choose_source_loop(inner, outer, set(), self.ROWS, self.AD)
        self.assertEqual((sl[0], rule), ("k.c:75", "outer"))
        self.assertEqual(L.choose_source_loop(inner, inner)[1], "header=latch")
        self.assertEqual(L.choose_source_loop(None, outer)[0][0], "k.c:75")
        self.assertEqual(L.choose_source_loop(inner, None)[0][0], "k.c:76")
        other = ("h.h:10", "for", 10, 12, 1)
        self.assertEqual(L.choose_source_loop(inner, other)[0][0], "h.h:10")      # unrelated: the back edge's loop

    def test_inner_loop_not_shown_flattened_takes_the_smaller_bound(self):
        """review 2026-10-16/17 (reviewer 2): a real inner loop whose back-edge line lands on the outer loop."""
        outer = ("k.c:90", "for", 90, 99, 0)
        inner = ("k.c:92", "for", 92, 95, 0)
        sl, how, rule = L.choose_source_loop(inner, outer, set(), self.ROWS, self.AD)   # trip count tn: runtime
        self.assertEqual((sl[0], rule), ("k.c:92", "min"))
        o2, i2 = ("k.c:75", "for", 75, 76, 0), ("k.c:76", "for", 76, 76, 0)
        sl, how, rule = L.choose_source_loop(i2, o2, {"k.c:76"}, self.ROWS, self.AD)    # the inner loop is emitted
        self.assertEqual((sl[0], rule), ("k.c:76", "min"))
        sl, how, rule = L.choose_source_loop(i2, o2, set(), {}, self.AD)                 # no loop-table row
        self.assertEqual(rule, "min")
        sl, how, rule = L.choose_source_loop(o2, i2, set(), self.ROWS, self.AD)          # header outer, latch inner
        self.assertEqual((sl[0], rule), ("k.c:75", "outer"))

    def test_loop_enclosing_an_emitted_inner_loop_is_the_outer_loop(self):
        """x0final revision, measured on the regression set under C: GCC keeps j-loops (header = latch = j line) inside
        the emitted s-loop, whose header line is a j line; condition (i) alone would check its 8 lanes against 0."""
        o2, i2 = ("k.c:75", "for", 75, 76, 0), ("k.c:76", "for", 76, 76, 0)
        sl, how, rule = L.choose_source_loop(i2, o2, {"k.c:76"}, self.ROWS, self.AD, lambda x: x == "k.c:76")
        self.assertEqual((sl[0], rule), ("k.c:75", "outer"))
        sl, how, rule = L.choose_source_loop(i2, o2, {"k.c:76"}, self.ROWS, self.AD, lambda x: False)
        self.assertEqual(rule, "min")

    def test_innermost_containing_loop(self):
        self.assertEqual(L.Attribution.source_loop_of_stack(self.A, [("k.c", 57)])[0], "k.c:50")
        self.assertIsNone(L.Attribution.source_loop_of_stack(self.A, [("k.c", 70)]))



def _mov(dst, src):
    return ins("VMOVAPS", ["REG0/W", "REG1/R"], {"REG0": dst, "REG1": src})


class TestPartialResultsReview(unittest.TestCase):
    """x0final revision: the adversarial streams of the independent review of 2026-10-16/17 (reviewer 2, scratch
    adv_loops.py), each with the number of independent partial results the source would show."""

    def setUp(self):
        L.ABI["current"] = "elf"

    def run_loop(self, seq, edges):
        insts, succ = build(seq, edges)
        loops, preds = L.natural_loops((1, 0), succ)
        return L.analyse_loop(loops[0], insts, succ, preds)

    def test_t1_register_rotation_counts_both_partial_results(self):
        seq = [ins("NOP", [], {}),
               ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "YMM3", "MEM0": "ptr [RDI]"}),
               vop("VADDPS", "YMM2", "YMM0", "YMM3"), _mov("YMM0", "YMM1"), _mov("YMM1", "YMM2"),
               ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RDI", "IMM0": "0x20"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        i = self.run_loop(seq, {6: [1, 7]})
        self.assertEqual(i["acc_lanes_emitted"], 16)
        self.assertEqual(i["partial_results"], [["V0"], ["V1"]])

    def test_t2_compare_select_max_is_an_accumulation(self):
        blend = lambda d, a, b, m: ins("VBLENDVPS", ["REG0/W", "REG1/R", "REG2/R", "REG3/R"],  # noqa: E731
                                       {"REG0": d, "REG1": a, "REG2": b, "REG3": m})
        seq = [ins("NOP", [], {}),
               ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "YMM1", "MEM0": "ptr [RDI]"}),
               ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "YMM5", "MEM0": "ptr [RDI+0x20]"}),
               vop("VCMPPS", "YMM3", "YMM1", "YMM0", imm=0x1e), blend("YMM0", "YMM0", "YMM1", "YMM3"),
               vop("VCMPPS", "YMM6", "YMM5", "YMM4", imm=0x1e), blend("YMM4", "YMM4", "YMM5", "YMM6"),
               ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RDI", "IMM0": "0x40"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        i = self.run_loop(seq, {8: [1, 9]})
        self.assertEqual(i["acc_lanes_emitted"], 16)
        self.assertEqual(i["fp_accumulator_ops"], ["VBLENDVPS"])

    def test_t2b_masked_move_select_avx512(self):
        seq = [ins("NOP", [], {}),
               ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "ZMM1", "MEM0": "ptr [RDI]"}),
               ins("VCMPPS", ["REG0/W", "REG1/R", "REG2/R", "IMM0/R"], {"REG0": "K1", "REG1": "ZMM1", "REG2": "ZMM0", "IMM0": "0x1e"}),
               ins("VMOVAPS", ["REG0/RCW", "REG1/R", "REG2/R"], {"REG0": "ZMM0", "REG1": "K1", "REG2": "ZMM1"}),
               ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RDI", "IMM0": "0x40"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        i = self.run_loop(seq, {5: [1, 6]})
        self.assertEqual(i["acc_lanes_emitted"], 16)

    def test_t3_two_fma_chains(self):
        seq = [ins("NOP", [], {}),
               ins("VFMADD231PS", ["REG0/RW", "REG1/R", "REG2/R"], {"REG0": "YMM0", "REG1": "YMM2", "REG2": "YMM3"}),
               ins("VFMADD231PS", ["REG0/RW", "REG1/R", "REG2/R"], {"REG0": "YMM1", "REG1": "YMM4", "REG2": "YMM5"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        self.assertEqual(self.run_loop(seq, {3: [1, 4]})["acc_lanes_emitted"], 16)

    def test_t4_add_then_merge_blend_into_the_accumulator(self):
        bm = lambda d, b: ins("VBLENDMPS", ["REG0/W", "REG1/R", "REG2/R", "REG3/R"],  # noqa: E731
                              {"REG0": d, "REG1": "K1", "REG2": d, "REG3": b})
        seq = [ins("NOP", [], {}), vop("VADDPS", "ZMM2", "ZMM0", "ZMM3"), bm("ZMM0", "ZMM2"),
               vop("VADDPS", "ZMM5", "ZMM4", "ZMM6"), bm("ZMM4", "ZMM5"),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        self.assertEqual(self.run_loop(seq, {5: [1, 6]})["acc_lanes_emitted"], 32)

    def test_t5_accumulator_through_a_permute(self):
        perm = lambda r: ins("VPERMILPS", ["REG0/W", "REG1/R", "IMM0/R"], {"REG0": r, "REG1": r, "IMM0": "0x4e"})  # noqa: E731
        seq = [ins("NOP", [], {}), vop("VADDPS", "XMM0", "XMM0", "XMM3"), perm("XMM0"),
               vop("VADDPS", "XMM1", "XMM1", "XMM4"), perm("XMM1"),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        self.assertEqual(self.run_loop(seq, {5: [1, 6]})["acc_lanes_emitted"], 8)

    def test_t6_copy_on_one_path_does_not_merge_two_accumulators(self):
        seq = [ins("NOP", [], {}), vop("VADDPS", "YMM0", "YMM0", "YMM3"), vop("VADDPS", "YMM1", "YMM1", "YMM4"),
               ins("JZ", ["RELBR/R"], {}), _mov("YMM1", "YMM0"),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        i = self.run_loop(seq, {3: [4, 5], 5: [1, 6]})
        self.assertEqual(i["acc_lanes_emitted"], 16)
        self.assertEqual(len(i["partial_results"]), 2)

    def test_serial_unroll_is_one_partial_result(self):
        seq = [ins("NOP", [], {}), vop("VADDPS", "YMM0", "YMM0", "YMM3"), vop("VADDPS", "YMM0", "YMM0", "YMM4"),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        i = self.run_loop(seq, {3: [1, 4]})
        self.assertEqual((i["acc_lanes_emitted"], i["acc_updates_per_iter"]), (8, 16))

    def test_integer_induction_is_not_an_accumulator(self):
        seq = [ins("NOP", [], {}),
               ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "YMM1", "MEM0": "ptr [RDI]"}),
               ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "YMM1", "MEM0": "ptr [RSI]"}),
               ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RDI", "IMM0": "0x20"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        self.assertEqual(self.run_loop(seq, {4: [1, 5]})["acc_lanes_emitted"], 0)

    def test_load_through_a_carried_pointer_is_not_a_carried_value(self):
        """x0final revision, measured on the regression set under C: x[i] * id compared into k0 each iteration."""
        seq = [ins("NOP", [], {}),
               ins("VMULPS", ["REG0/W", "REG1/R", "MEM0/R"], {"REG0": "ZMM1", "REG1": "ZMM7", "MEM0": "ptr [RDI]"}),
               ins("VCMPPS", ["REG0/W", "REG1/R", "REG2/R", "IMM0/R"], {"REG0": "K0", "REG1": "ZMM1", "REG2": "ZMM6", "IMM0": "0x1e"}),
               ins("VMOVAPS", ["REG0/RCW", "REG1/R", "REG2/R"], {"REG0": "ZMM1", "REG1": "K0", "REG2": "ZMM6"}),
               ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "ZMM1", "MEM0": "ptr [RSI]"}),
               ins("KMOVW", ["REG0/W", "REG1/R"], {"REG0": "K0", "REG1": "K0"}),
               ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RDI", "IMM0": "0x40"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        i = self.run_loop(seq, {7: [1, 8]})
        self.assertEqual(i["acc_lanes_emitted"], 0)

    def test_sccs(self):
        self.assertEqual(L.sccs(["a", "b", "c"], {"a": {"b"}, "b": {"a"}, "c": {"c"}}), [["a", "b"], ["c"]])


if __name__ == "__main__":
    unittest.main()
