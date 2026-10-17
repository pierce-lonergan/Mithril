"""Unit tests for the pre-freeze review of 2026-10-17 (Claude, same family, independent context; scratch file
adv_pfr.py, streams A1 to A9) of x0_loops.py, on SYNTHETIC instruction records (no object file, no Hearth code):
"reads a loop-carried value" from DEP, compare-select on a copy and in its SSE2 form, merging only copies or parts
of one value (EQ), and the source-loop rule's mirror test, nesting through the inline stack and unrelated loops.
Each stream carries the number of independent partial results the source would show.
Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import x0_loops as L  # noqa: E402
from test_loops_x0final import build, ins, vop  # noqa: E402


def mov(ic, d, s):
    return ins(ic, ["REG0/W", "REG1/R"], {"REG0": d, "REG1": s})


def load(r, mem):
    return ins("VMOVUPS" if r.startswith(("YMM", "ZMM")) else "MOVUPS", ["REG0/W", "MEM0/R"], {"REG0": r, "MEM0": mem})


JNZ = ins("JNZ", ["RELBR/R"], {})
RET = ins("RET_NEAR", [], {})
NOP = ins("NOP", [], {})


def rdi_step(k):
    return ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RDI", "IMM0": hex(k)})


class Base(unittest.TestCase):
    def setUp(self):
        L.ABI["current"] = "elf"

    def run_loop(self, seq, latch=None, edges=None):
        n = len(seq)
        insts, succ = build(seq, edges or {n - 2 if latch is None else latch: [1, n - 1]})
        loops, preds = L.natural_loops((1, 0), succ)
        return L.analyse_loop(loops[0], insts, succ, preds)


class TestCarriedThroughAnyInstruction(Base):
    """Finding 1: the carried value reaches the accumulation through an instruction outside the move whitelist."""

    def test_a1_scalar_accumulators_carried_in_gprs_through_vmovd(self):
        seq = [NOP, mov("VMOVD", "XMM0", "EAX"), vop("VADDSS", "XMM0", "XMM0", "XMM4"), mov("VMOVD", "EAX", "XMM0"),
               mov("VMOVD", "XMM1", "EDX"), vop("VADDSS", "XMM1", "XMM1", "XMM5"), mov("VMOVD", "EDX", "XMM1"), JNZ, RET]
        self.assertEqual(self.run_loop(seq)["acc_lanes_emitted"], 2)
        self.assertTrue(L.is_move(mov("VMOVD", "EAX", "XMM0")) and L.is_move(mov("MOVD", "XMM0", "EAX")))

    def test_a2_permute_before_the_add(self):
        perm = lambda d, s: ins("VPERMILPS", ["REG0/W", "REG1/R", "IMM0/R"], {"REG0": d, "REG1": s, "IMM0": "0x4e"})  # noqa: E731
        seq = [NOP, perm("XMM2", "XMM0"), vop("VADDPS", "XMM0", "XMM2", "XMM3"),
               perm("XMM6", "XMM1"), vop("VADDPS", "XMM1", "XMM6", "XMM4"), JNZ, RET]
        self.assertEqual(self.run_loop(seq)["acc_lanes_emitted"], 8)

    def test_a3_ymm_accumulators_spilled_as_two_halves(self):
        def halves(r, slot):
            return [ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "XMM" + r[3:], "MEM0": "ptr [RSP+%#x]" % slot}),
                    ins("VEXTRACTF128", ["MEM0/W", "REG0/R", "IMM0/R"],
                        {"REG0": r, "MEM0": "ptr [RSP+%#x]" % (slot + 16), "IMM0": "0x1"})]

        def reload(r, slot):
            return [ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "XMM" + r[3:], "MEM0": "ptr [RSP+%#x]" % slot}),
                    ins("VINSERTF128", ["REG0/W", "REG1/R", "MEM0/R", "IMM0/R"],
                        {"REG0": r, "REG1": r, "MEM0": "ptr [RSP+%#x]" % (slot + 16), "IMM0": "0x1"})]
        seq = [NOP] + reload("YMM0", 0x40) + [vop("VADDPS", "YMM0", "YMM0", "YMM3")] + halves("YMM0", 0x40) + \
            reload("YMM1", 0x80) + [vop("VADDPS", "YMM1", "YMM1", "YMM4")] + halves("YMM1", 0x80) + [JNZ, RET]
        i = self.run_loop(seq)
        self.assertEqual(i["acc_lanes_emitted"], 16)          # the two halves of one value are one partial result
        self.assertEqual(len(i["partial_results"]), 2)

    def test_a6_compare_on_a_copy_then_blend_the_original(self):
        bl = lambda d, a, b, m: ins("VBLENDVPS", ["REG0/W", "REG1/R", "REG2/R", "REG3/R"],  # noqa: E731
                                    {"REG0": d, "REG1": a, "REG2": b, "REG3": m})
        seq = [NOP, load("YMM2", "ptr [RDI]"), mov("VMOVAPS", "YMM8", "YMM0"), vop("VCMPPS", "YMM3", "YMM2", "YMM8", imm=0x1e),
               bl("YMM0", "YMM0", "YMM2", "YMM3"), load("YMM5", "ptr [RDI+0x20]"), mov("VMOVAPS", "YMM9", "YMM1"),
               vop("VCMPPS", "YMM6", "YMM5", "YMM9", imm=0x1e), bl("YMM1", "YMM1", "YMM5", "YMM6"), rdi_step(0x40), JNZ, RET]
        self.assertEqual(self.run_loop(seq)["acc_lanes_emitted"], 16)

    def test_a9_legacy_sse41_select_max_mask_in_xmm0(self):
        def lsel(acc, x):
            return [mov("MOVAPS", "XMM0", acc),
                    ins("CMPPS", ["REG0/RW", "REG1/R", "IMM0/R"], {"REG0": "XMM0", "REG1": x, "IMM0": "0x1"}),
                    ins("BLENDVPS", ["REG0/RW", "REG1/R", "REG2/R"], {"REG0": acc, "REG1": x, "REG2": "XMM0"})]
        seq = [NOP, load("XMM2", "ptr [RDI]"), load("XMM3", "ptr [RDI+0x10]")] + lsel("XMM4", "XMM2") + \
            lsel("XMM5", "XMM3") + [rdi_step(0x20), JNZ, RET]
        self.assertEqual(self.run_loop(seq)["acc_lanes_emitted"], 8)


class TestSelectAndMerge(Base):
    """Finding 9: the SSE2 select idiom, and no merge of two accumulators swapped on one path."""

    @staticmethod
    def sse2_select(acc, x, t, u):
        return [mov("MOVAPS", t, x), ins("CMPPS", ["REG0/RW", "REG1/R", "IMM0/R"], {"REG0": t, "REG1": acc, "IMM0": "0x1"}),
                mov("MOVAPS", u, t), ins("ANDPS", ["REG0/RW", "REG1/R"], {"REG0": t, "REG1": x}),
                ins("ANDNPS", ["REG0/RW", "REG1/R"], {"REG0": u, "REG1": acc}),
                ins("ORPS", ["REG0/RW", "REG1/R"], {"REG0": u, "REG1": t}), mov("MOVAPS", acc, u)]

    def test_a5_sse2_and_andn_or_select_max(self):
        seq = [NOP, load("XMM2", "ptr [RDI]"), load("XMM3", "ptr [RDI+0x10]")] + \
            self.sse2_select("XMM0", "XMM2", "XMM4", "XMM5") + self.sse2_select("XMM1", "XMM3", "XMM6", "XMM7") + \
            [rdi_step(0x20), JNZ, RET]
        i = self.run_loop(seq)
        self.assertEqual(i["acc_lanes_emitted"], 8)
        self.assertEqual(i["fp_accumulator_ops"], ["ORPS"])

    def test_scalar_sse2_select_counts_one_lane(self):
        seq = [NOP, ins("MOVSS", ["REG0/W", "MEM0/R"], {"REG0": "XMM2", "MEM0": "ptr [RDI]"}),
               mov("MOVAPS", "XMM4", "XMM2"),
               ins("CMPSS", ["REG0/RW", "REG1/R", "IMM0/R"], {"REG0": "XMM4", "REG1": "XMM0", "IMM0": "0x1"}),
               mov("MOVAPS", "XMM5", "XMM4"), ins("ANDPS", ["REG0/RW", "REG1/R"], {"REG0": "XMM4", "REG1": "XMM2"}),
               ins("ANDNPS", ["REG0/RW", "REG1/R"], {"REG0": "XMM5", "REG1": "XMM0"}),
               ins("ORPS", ["REG0/RW", "REG1/R"], {"REG0": "XMM5", "REG1": "XMM4"}), mov("MOVAPS", "XMM0", "XMM5"),
               rdi_step(4), JNZ, RET]
        self.assertEqual(self.run_loop(seq)["acc_lanes_emitted"], 1)

    def test_argmax_index_select_is_not_an_accumulator(self):
        """max = maxps(max, x) is one 4-lane accumulator; the index vector selected by the same mask is not."""
        seq = [NOP, load("XMM3", "ptr [RDI]"), mov("MOVAPS", "XMM4", "XMM0"),
               ins("CMPPS", ["REG0/RW", "REG1/R", "IMM0/R"], {"REG0": "XMM4", "REG1": "XMM3", "IMM0": "0x1"}),
               ins("MAXPS", ["REG0/RW", "REG1/R"], {"REG0": "XMM0", "REG1": "XMM3"}),
               mov("MOVAPS", "XMM5", "XMM4"), ins("ANDPS", ["REG0/RW", "REG1/R"], {"REG0": "XMM5", "REG1": "XMM2"}),
               ins("ANDNPS", ["REG0/RW", "REG1/R"], {"REG0": "XMM4", "REG1": "XMM1"}),
               ins("ORPS", ["REG0/RW", "REG1/R"], {"REG0": "XMM4", "REG1": "XMM5"}), mov("MOVAPS", "XMM1", "XMM4"),
               ins("PADDD", ["REG0/RW", "REG1/R"], {"REG0": "XMM2", "REG1": "XMM6"}), rdi_step(0x10), JNZ, RET]
        i = self.run_loop(seq)
        self.assertEqual(i["acc_lanes_emitted"], 4)
        self.assertEqual(i["partial_results"], [["V0"]])

    def test_a4_swap_on_one_path_is_not_merged(self):
        seq = [NOP, vop("VADDPS", "YMM0", "YMM0", "YMM3"), vop("VADDPS", "YMM1", "YMM1", "YMM4"),
               ins("JZ", ["RELBR/R"], {}), mov("VMOVAPS", "YMM2", "YMM0"), mov("VMOVAPS", "YMM0", "YMM1"),
               mov("VMOVAPS", "YMM1", "YMM2"), JNZ, RET]
        i = self.run_loop(seq, edges={3: [4, 7], 7: [1, 8]})
        self.assertEqual(i["acc_lanes_emitted"], 16)
        self.assertEqual(i["partial_results"], [["V0"], ["V1"]])

    def test_halves_spilled_on_each_of_two_paths_are_one_partial_result(self):
        """An accumulator kept as two stack halves and updated on one of two paths: the halves are parts of one value
        on every path (EQ holds at the latch), so one partial result, as in A3."""
        def spill(ymm):
            return [ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "XMM0", "MEM0": "ptr [RSP+0x40]"}),
                    ins("VEXTRACTF128", ["MEM0/W", "REG0/R", "IMM0/R"], {"REG0": "YMM0", "MEM0": "ptr [RSP+0x50]", "IMM0": "0x1"})]
        seq = [NOP, ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "XMM0", "MEM0": "ptr [RSP+0x40]"}),
               ins("VINSERTF128", ["REG0/W", "REG1/R", "MEM0/R", "IMM0/R"],
                   {"REG0": "YMM0", "REG1": "YMM0", "MEM0": "ptr [RSP+0x50]", "IMM0": "0x1"}),
               ins("JZ", ["RELBR/R"], {}), vop("VADDPS", "YMM0", "YMM0", "YMM3")] + spill("YMM0") + \
            [ins("JMP", ["RELBR/R"], {}), vop("VADDPS", "YMM0", "YMM0", "YMM4")] + spill("YMM0") + [JNZ, RET]
        i = self.run_loop(seq, edges={3: [4, 8], 7: [11], 11: [1, 12]})
        self.assertEqual(i["acc_lanes_emitted"], 8)
        self.assertEqual(i["partial_results"], [["STK:RSP:64", "STK:RSP:80"]])


class TestNoNewFalseCounts(Base):
    """Shapes the DEP-based reading must not turn into extra partial results."""

    def test_converted_counter_feeding_the_accumulator(self):
        seq = [NOP, ins("CVTSI2SS", ["REG0/W", "REG1/R"], {"REG0": "XMM1", "REG1": "EAX"}),
               ins("MULSS", ["REG0/RW", "REG1/R"], {"REG0": "XMM1", "REG1": "XMM2"}),
               ins("ADDSS", ["REG0/RW", "REG1/R"], {"REG0": "XMM0", "REG1": "XMM1"}),
               ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RAX", "IMM0": "0x1"}), JNZ, RET]
        i = self.run_loop(seq)
        self.assertEqual((i["acc_lanes_emitted"], i["partial_results"]), (1, [["V0"]]))

    def test_software_pipelined_load(self):
        seq = [NOP, vop("VMULPS", "YMM2", "YMM1", "YMM5"), vop("VADDPS", "YMM0", "YMM0", "YMM2"),
               load("YMM1", "ptr [RDI+0x20]"), rdi_step(0x20), JNZ, RET]
        i = self.run_loop(seq)
        self.assertEqual((i["acc_lanes_emitted"], i["partial_results"]), (8, [["V0"]]))

    def test_vector_index_update_is_not_an_accumulator(self):
        seq = [NOP, ins("VPADDD", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "YMM1", "REG1": "YMM1", "REG2": "YMM7"}),
               ins("VCVTDQ2PS", ["REG0/W", "REG1/R"], {"REG0": "YMM2", "REG1": "YMM1"}),
               vop("VMULPS", "YMM2", "YMM2", "YMM6"), ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "YMM2", "MEM0": "ptr [RSI]"}),
               rdi_step(0x20), JNZ, RET]
        self.assertEqual(self.run_loop(seq)["acc_lanes_emitted"], 0)


class TestSourceLoopRule(unittest.TestCase):
    """Finding 8: the mirror test, nesting through the inline stack, unrelated loops."""
    ROWS = {"k.c:86": {"loop_id": "k.c:86", "source_lanes": "16", "trip_count": "4"},
            "k.c:82": {"loop_id": "k.c:82", "source_lanes": "128", "trip_count": "nb"},
            "k.c:20": {"loop_id": "k.c:20", "source_lanes": "0", "trip_count": "4"},
            "k.c:60": {"loop_id": "k.c:60", "source_lanes": "128", "trip_count": "nb"},
            "k.c:30": {"loop_id": "k.c:30", "source_lanes": "0", "trip_count": "n"}}
    AD = {"sources": {"k.c": {"loop_vars": {"82": "b", "86": "i", "60": "g", "20": "j", "30": "q"}}}}

    def test_a7_real_inner_loop_enclosed_by_an_emitted_outer_loop(self):
        outer, inner = ("k.c:82", "for", 82, 99, 0), ("k.c:86", "for", 86, 90, 0)
        sl, how, rule = L.choose_source_loop(inner, outer, {"k.c:82"}, self.ROWS, self.AD, lambda x: False,
                                             lambda x: x == "k.c:82")
        self.assertEqual((sl[0], rule), ("k.c:86", "inner"))
        # without the mirror evidence the earlier rule still applies (flattened inner loop: the outer one)
        sl, how, rule = L.choose_source_loop(inner, outer, {"k.c:82"}, self.ROWS, self.AD, lambda x: False, lambda x: False)
        self.assertEqual((sl[0], rule), ("k.c:82", "outer"))
        # enclosing an emitted inner loop and enclosed by an emitted outer loop: the smaller bound
        sl, how, rule = L.choose_source_loop(inner, outer, {"k.c:82"}, self.ROWS, self.AD, lambda x: x == "k.c:86",
                                             lambda x: x == "k.c:82")
        self.assertEqual(rule, "min")

    def test_a8_helper_loop_inlined_into_the_caller_loop_is_nested(self):
        helper, caller = ("k.c:20", "for", 20, 24, 0), ("k.c:60", "for", 60, 70, 1)
        fh = [("k.c", 21), ("k.c", 63)]                       # the helper is inlined at k.c:63, inside the caller loop
        fl = [("k.c", 70)]
        # a real helper loop inside an emitted caller loop: its own bound (0)
        sl, how, rule = L.choose_source_loop(helper, caller, set(), self.ROWS, self.AD, lambda x: False,
                                             lambda x: x == "k.c:60", fh, fl)
        self.assertEqual((sl[0], rule), ("k.c:20", "inner"))
        # no emitted caller loop around it and a constant helper trip count: flattened, the caller's loop
        sl, how, rule = L.choose_source_loop(helper, caller, set(), self.ROWS, self.AD, lambda x: False, lambda x: False, fh, fl)
        self.assertEqual((sl[0], rule), ("k.c:60", "outer"))
        # a helper loop with a runtime trip count: the smaller bound
        h2 = ("k.c:30", "for", 30, 34, 0)
        sl, how, rule = L.choose_source_loop(h2, caller, set(), self.ROWS, self.AD, lambda x: False, lambda x: False,
                                             [("k.c", 31), ("k.c", 65)], fl)
        self.assertEqual(rule, "min")

    def test_unrelated_loops_take_the_smaller_bound(self):
        helper, caller = ("k.c:20", "for", 20, 24, 0), ("k.c:60", "for", 60, 70, 1)
        sl, how, rule = L.choose_source_loop(helper, caller, set(), self.ROWS, self.AD, lambda x: False, lambda x: False,
                                             [("k.c", 21), ("k.c", 80)], [("k.c", 70)])
        self.assertEqual(rule, "min")
        self.assertEqual(L.choose_source_loop(helper, caller)[2], "min")


if __name__ == "__main__":
    unittest.main()
