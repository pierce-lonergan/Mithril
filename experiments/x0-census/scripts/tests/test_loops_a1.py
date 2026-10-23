"""Unit tests for Amendment X0-A1 (post-data tooling fix of x0_loops.py, 2026-10-23): record §4.7 admits only a
"constant-offset, non-escaping stack slot treated as a register"; a slot whose address escapes is plain memory, and a
loop whose P3(c) count or partial results differ between the frozen and the X0-A1 reading is reported `unscreened`;
every other loop field keeps the frozen reading. SYNTHETIC instruction records only (no object file, no Hearth code).
The shapes: an accumulator array zeroed per chunk through REP STOSQ (the shape of census run 1's four C flags, written
from the shape described in REPORT.md §10, not from any decode; the offset 0x140 is the one REPORT.md §10 quotes from
run 1's re-derivation, "lea rax/rsi,[rsp+0x140]"), the same array zeroed by constant-offset stores (no address taken:
unchanged), MSVC's r11 prologue, GCC's DRAP realignment, a memset call, the /GS cookie, exact accesses through a
derived pointer, and the unchanged descriptive spilled tag. Added after the review of 2026-10-23 (Claude, same family,
independent context): a register accumulator spilled and reloaded through an escaping slot inside one iteration, a
split with one half so spilled, events that only follow the loop (an epilogue call, a return), an event in an
enclosing loop, the descriptive fields kept on the frozen reading, and the per-variant frozen-reading P3(c) list.
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

NOP = ins("NOP", [], {})
JNZ = ins("JNZ", ["RELBR/R"], {})
RET = ins("RET_NEAR", ["REG0/RW", "MEM0/R"], {"REG0": "STACKPOP", "MEM0": "ptr [RSP]"})


def imm_op(ic, reg, value, width=8):
    """ic reg, imm with XED's encoding of the immediate (raw bits, IMM_WIDTH, IMM0SIGNED)."""
    return ins(ic, ["REG0/RW", "IMM0/R", "REG1/W"],
               {"REG0": reg, "IMM0": hex(value & ((1 << width) - 1)), "IMM_WIDTH": str(width), "IMM0SIGNED": True,
                "REG1": "RFLAGS"})


def lea(dst, mem):
    return ins("LEA", ["REG0/W", "AGEN/R"], {"REG0": dst, "AGEN": "ptr [%s]" % mem})


def mov(dst, src):
    return ins("MOV", ["REG0/W", "REG1/R"], {"REG0": dst, "REG1": src})


def vload(x, mem):
    return ins("VMOVAPS", ["REG0/W", "MEM0/R"], {"REG0": x, "MEM0": "ptr [%s]" % mem})


def vstore(mem, x):
    return ins("VMOVAPS", ["MEM0/W", "REG0/R"], {"REG0": x, "MEM0": "ptr [%s]" % mem})


def push(r):
    return ins("PUSH", ["REG0/R", "REG1/RW", "MEM0/W"], {"REG0": r, "REG1": "STACKPUSH", "MEM0": "ptr [RSP]"})


REP_STOSQ = ins("REP_STOSQ", ["MEM0/W", "REG0/R", "REG1/RW", "REG2/RW"],
                {"MEM0": "ptr [RDI]", "REG0": "RAX", "REG1": "RDI", "REG2": "RCX"})


def call(target=None):
    r = ins("CALL_NEAR", ["RELBR/R", "REG0/RW", "REG1/RW", "MEM0/W"],
            {"REG0": "STACKPUSH", "REG1": "RIP", "MEM0": "ptr [RSP]"})
    if target:
        r["call"] = list(target)
    return r


class Base(unittest.TestCase):
    def setUp(self):
        L.ABI["current"] = "elf"

    def tearDown(self):
        L.ABI["current"] = "elf"

    def loops(self, seq, edges):
        insts, succ = build(seq, edges)
        loops, preds = L.natural_loops((1, 0), succ)
        frames = L.FrameInfo(insts, succ)
        return {lp["header"][1] // 4: L.analyse_loop(lp, insts, succ, preds, frames) for lp in loops}


def chunk_stream(zeroing):
    """0 prologue | 1 header of the chunk loop: zero acc[0..1] (zeroing) | inner loop: acc[k] += x_k in the slots
    RSP+0x140 and RSP+0x150 | after the inner loop: store acc[0] | latch of the chunk loop | epilogue."""
    head = [imm_op("SUB", "RSP", 0x1c0, 32)]
    inner = [vload("XMM1", "RSP+0x140"), vop("VADDPS", "XMM1", "XMM1", "XMM5"), vstore("RSP+0x140", "XMM1"),
             vload("XMM2", "RSP+0x150"), vop("VADDPS", "XMM2", "XMM2", "XMM6"), vstore("RSP+0x150", "XMM2"),
             imm_op("ADD", "RSI", 0x40), JNZ]
    tail = [vload("XMM3", "RSP+0x140"), ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "XMM3", "MEM0": "ptr [RDX]"}),
            imm_op("ADD", "RDX", 0x10), JNZ, imm_op("ADD", "RSP", 0x1c0, 32), RET]
    seq = head + zeroing + inner + tail
    h_outer = len(head)
    h_inner = len(head) + len(zeroing)
    latch_inner = h_inner + len(inner) - 1
    latch_outer = latch_inner + 4
    return seq, {latch_inner: [h_inner, latch_inner + 1], latch_outer: [h_outer, latch_outer + 1]}, h_outer, h_inner


class TestEscapingArray(Base):
    """The shape of census run 1's four configuration-C flags, written from the shape only."""

    REP = [lea("RDI", "RSP+0x140"), mov("RCX", "R8"), ins("XOR", ["REG0/RW", "REG1/R"], {"REG0": "EAX", "REG1": "EAX"}),
           REP_STOSQ]

    def test_rep_stosq_zeroed_array_is_not_register_like(self):
        seq, edges, ho, hi = chunk_stream(self.REP)
        res = self.loops(seq, edges)
        outer, inner = res[ho], res[hi]
        self.assertEqual(outer["acc_lanes_emitted"], 0)
        self.assertEqual(outer["escaping_slots"], ["STK:RSP:320", "STK:RSP:336"])
        self.assertTrue(outer["unscreened"])
        self.assertEqual(outer["escaping_partial_results"], [["STK:RSP:320"], ["STK:RSP:336"]])
        self.assertEqual(outer["acc_lanes_if_escaping_slots_were_registers"], 8)
        self.assertTrue(any("REP_STOSQ" in w for w in outer["escape_events"]))
        # the inner loop's array accumulators are unscreened too (memory-held), not cleared
        self.assertEqual((inner["acc_lanes_emitted"], inner["unscreened"]), (0, True))
        self.assertEqual(inner["acc_lanes_if_escaping_slots_were_registers"], 8)

    def test_the_frozen_reading_is_what_the_census_counted(self):
        """Without the escape rule the chunk loop carries both slots: the false 8 lanes against a bound of 0."""
        seq, edges, ho, hi = chunk_stream(self.REP)
        insts, succ = build(seq, edges)
        loops, preds = L.natural_loops((1, 0), succ)
        lp = next(x for x in loops if x["header"] == (1, 4 * ho))
        L.MOVING_BASES["now"] = L.moving_bases(lp["body"], insts)
        try:
            old = L._analyse_loop(lp, insts, succ, preds)
        finally:
            L.MOVING_BASES["now"] = set()
        self.assertEqual((old["acc_lanes_emitted"], old["partial_results"]), (8, [["STK:RSP:320"], ["STK:RSP:336"]]))

    def test_constant_offset_zeroing_takes_no_address(self):
        """The same array zeroed by constant-offset stores: no address escapes, the frozen data flow stands (the stores
        kill both slots, so the chunk loop carries nothing; the inner loop keeps its two 4-lane partial results)."""
        zero = [vop("VXORPS", "XMM0", "XMM0", "XMM0"), vstore("RSP+0x140", "XMM0"), vstore("RSP+0x150", "XMM0")]
        seq, edges, ho, hi = chunk_stream(zero)
        res = self.loops(seq, edges)
        self.assertEqual((res[ho]["acc_lanes_emitted"], res[ho]["escaping_slots"], res[ho]["unscreened"]), (0, [], False))
        self.assertEqual((res[hi]["acc_lanes_emitted"], res[hi]["escaping_slots"], res[hi]["unscreened"]), (8, [], False))

    def test_spilled_tag_is_unchanged(self):
        seq, edges, ho, hi = chunk_stream(self.REP)
        res = self.loops(seq, edges)
        self.assertIn("spilled", res[hi]["tags"])
        self.assertGreater(res[hi]["spills"], 0)


def spill_loop(slot):
    """A ymm accumulator spilled to a stack slot every iteration (8 lanes): vmovups ymm1,[slot]; vaddps ymm1,ymm1,ymm2;
    vmovups [slot],ymm1."""
    return [ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "YMM1", "MEM0": "ptr [%s]" % slot}),
            vop("VADDPS", "YMM1", "YMM1", "YMM2"),
            ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "YMM1", "MEM0": "ptr [%s]" % slot}),
            imm_op("ADD", "RDI", 0x20), JNZ]


class TestPrologues(Base):
    def run_spill(self, prologue, slot, epilogue=None, abi="elf"):
        L.ABI["current"] = abi
        body = spill_loop(slot)
        seq = prologue + body + (epilogue or []) + [RET]
        h = len(prologue)
        res = self.loops(seq, {h + len(body) - 1: [h, h + len(body)]})
        return res[h]

    def test_msvc_r11_frame_accesses_leave_other_slots_register_like(self):
        pro = [mov("R11", "RSP"), push("RBP"), imm_op("SUB", "RSP", 0x98, 32),
               ins("MOVAPS", ["MEM0/W", "REG0/R"], {"REG0": "XMM6", "MEM0": "ptr [R11-0x18]"})]
        epi = [lea("R11", "RSP+0xa0"), ins("MOVAPS", ["REG0/W", "MEM0/R"], {"REG0": "XMM6", "MEM0": "ptr [R11-0x18]"}),
               mov("RSP", "R11")]
        lp = self.run_spill(pro, "RSP+0x20", epi, abi="coff")
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"], lp["unscreened"]), (8, [], False))

    def test_an_exact_access_through_a_pointer_to_the_slot_makes_it_escape(self):
        # entry RSP 0; push -> -8; sub 0x98 -> -0xa0; [RSP+0x20] is entry-relative -0x80, also reached as [R11-0x80]
        pro = [mov("R11", "RSP"), push("RBP"), imm_op("SUB", "RSP", 0x98, 32),
               ins("MOV", ["MEM0/W", "IMM0/R"], {"MEM0": "ptr [R11-0x80]", "IMM0": "0x0", "IMM_WIDTH": "32"})]
        lp = self.run_spill(pro, "RSP+0x20", abi="coff")
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"], lp["unscreened"]), (0, ["STK:RSP:32"], True))
        self.assertEqual(lp["acc_lanes_if_escaping_slots_were_registers"], 8)

    def test_exact_access_elsewhere_in_the_frame_does_not_reach_the_slot(self):
        # (the pointer is kept in R10: a stack pointer left in RAX at the return would be a returned pointer, an
        # unbounded use)
        pro = [imm_op("SUB", "RSP", 0x300, 32), lea("R10", "RSP+0x200"),
               ins("MOV", ["MEM0/W", "REG0/R"], {"MEM0": "ptr [R10+0x8]", "REG0": "RCX"})]
        self.assertEqual(self.run_spill(pro, "RSP+0x100")["escaping_slots"], [])
        self.assertEqual(self.run_spill(pro, "RSP+0x208")["escaping_slots"], ["STK:RSP:520"])

    def test_gcc_drap_realignment_pointer_is_the_callers_frame(self):
        pro = [lea("R10", "RSP+0x8"), imm_op("AND", "RSP", -64),
               ins("PUSH", ["MEM0/R", "REG0/RW", "MEM1/W"], {"MEM0": "ptr [R10-0x8]", "REG0": "STACKPUSH", "MEM1": "ptr [RSP]"}),
               push("RBP"), mov("RBP", "RSP"), push("R10"), imm_op("SUB", "RSP", 0x100, 32),
               ins("MOV", ["REG0/W", "MEM0/R"], {"REG0": "RAX", "MEM0": "ptr [R10]"})]                # a stack argument
        epi = [ins("MOV", ["REG0/W", "MEM0/R"], {"REG0": "R10", "MEM0": "ptr [RBP-0x8]"}), lea("RSP", "R10-0x8")]
        lp = self.run_spill(pro, "RSP+0x40", epi)
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"], lp["unscreened"]), (8, [], False))

    def test_stack_address_passed_to_a_call_escapes_the_frame(self):
        pro = [imm_op("SUB", "RSP", 0x200, 32), lea("RDI", "RSP+0x40"),
               ins("XOR", ["REG0/RW", "REG1/R"], {"REG0": "ESI", "REG1": "ESI"}), call()]
        lp = self.run_spill(pro, "RSP+0x100")
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"], lp["unscreened"]), (0, ["STK:RSP:256"], True))
        self.assertTrue(any("argument register" in w for w in lp["escape_events"]))

    def test_register_accumulators_are_unaffected_by_an_escaping_frame(self):
        pro = [imm_op("SUB", "RSP", 0x200, 32), lea("RDI", "RSP+0x40"), call()]
        body = [vop("VADDPS", "YMM0", "YMM0", "YMM1")] + spill_loop("RSP+0x100")
        seq = pro + body + [RET]
        h = len(pro)
        lp = self.loops(seq, {h + len(body) - 1: [h, h + len(body)]})[h]
        self.assertEqual(lp["acc_lanes_emitted"], 8)                      # ymm0 still counted
        self.assertEqual(lp["acc_lanes_if_escaping_slots_were_registers"], 16)
        self.assertTrue(lp["unscreened"])

    def test_gs_cookie_xor_is_not_an_escape(self):
        pro = [imm_op("SUB", "RSP", 0x98, 32),
               ins("MOV", ["REG0/W", "MEM0/R"], {"REG0": "RAX", "MEM0": "ptr [RIP+0x0]"}),
               ins("XOR", ["REG0/RW", "REG1/R"], {"REG0": "RAX", "REG1": "RSP"}),
               ins("MOV", ["MEM0/W", "REG0/R"], {"MEM0": "ptr [RSP+0x80]", "REG0": "RAX"})]
        lp = self.run_spill(pro, "RSP+0x20", abi="coff")
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"]), (8, []))

    def test_stored_stack_pointer_escapes_the_frame(self):
        pro = [imm_op("SUB", "RSP", 0x98, 32), lea("RAX", "RSP+0x40"),
               ins("MOV", ["MEM0/W", "REG0/R"], {"MEM0": "ptr [RBX]", "REG0": "RAX"})]
        self.assertTrue(self.run_spill(pro, "RSP+0x20")["unscreened"])

    def test_indexed_access_through_a_stack_pointer_escapes_the_frame(self):
        pro = [imm_op("SUB", "RSP", 0x98, 32), lea("RAX", "RSP+0x40"),
               ins("MOV", ["MEM0/W", "REG0/R"], {"MEM0": "ptr [RAX+RCX*4]", "REG0": "EDX"})]
        self.assertTrue(self.run_spill(pro, "RSP+0x20")["unscreened"])

    def test_stack_pointer_returned_in_rax_is_an_event_that_cannot_reach_the_loop(self):
        """A return ends the activation, so a returned stack pointer is an unbounded use (FrameInfo records it) that no
        loop of the function can follow (review of 2026-10-23: events count only when the header is reachable)."""
        pro = [imm_op("SUB", "RSP", 0x300, 32), lea("RAX", "RSP+0x200")]
        body = spill_loop("RSP+0x100")
        seq = pro + body + [RET]
        insts, succ = build(seq, {len(pro) + len(body) - 1: [len(pro), len(pro) + len(body)]})
        fi = L.FrameInfo(insts, succ).info("")
        self.assertTrue(any("returned" in e["why"] for e in fi["events"]))
        lp = self.run_spill(pro, "RSP+0x100")
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"], lp["unscreened"]), (8, [], False))

    def test_multibyte_nop_through_a_stack_pointer_is_not_a_use(self):
        """MSVC pads with nop word ptr [rax+rax*1]; when RAX happens to hold a stack address that is no access (seen on
        the NON-Hearth repro a1_escape.c under A, 2026-10-23)."""
        pro = [imm_op("SUB", "RSP", 0x98, 32), lea("RAX", "RSP+0x40"),
               ins("NOP", ["MEM0/R", "REG0/R"], {"MEM0": "ptr [RAX+RAX*1]", "REG0": "AX"}),
               ins("PREFETCHT0", ["MEM0/R"], {"MEM0": "ptr [RAX+RCX*4]"}), mov("RAX", "RCX")]
        self.assertEqual(self.run_spill(pro, "RSP+0x20")["escaping_slots"], [])

    def test_no_stack_address_no_change(self):
        lp = self.run_spill([imm_op("SUB", "RSP", 0x98, 32), mov("RAX", "RCX")], "RSP+0x20")
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"], lp["unscreened"]), (8, [], False))
        self.assertNotIn("escape_events", lp)


class TestReview20261023(Base):
    """Cases of the independent review of X0-A1 (2026-10-23; reviewer 1's adv_a1.py streams)."""

    PRO = [imm_op("SUB", "RSP", 0x200, 32), lea("RDI", "RSP+0x100"), call()]       # the frame escapes before the loop
    TAIL = [imm_op("ADD", "RSP", 0x200, 32), RET]

    def one_loop(self, pro, body, tail=None):
        seq = pro + body + (tail if tail is not None else self.TAIL)
        h = len(pro)
        return self.loops(seq, {h + len(body) - 1: [h, h + len(body)]})[h]

    def test_in_iteration_spill_through_an_escaping_slot_is_unscreened(self):
        """vmovaps [rsp+0x40],xmm0; vmulps xmm0,xmm7,xmm7; vmovaps xmm0,[rsp+0x40]; vaddps xmm0,xmm0,xmm5: the slot is
        written before it is read, so it is no partial result itself, but the accumulator's cycle passes through it."""
        body = [vstore("RSP+0x40", "XMM0"), vop("VMULPS", "XMM0", "XMM7", "XMM7"), vload("XMM0", "RSP+0x40"),
                vop("VADDPS", "XMM0", "XMM0", "XMM5"), imm_op("ADD", "RSI", 0x10), JNZ]
        lp = self.one_loop(self.PRO, body)
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"]), (0, ["STK:RSP:64"]))
        self.assertTrue(lp["unscreened"])
        self.assertEqual(lp["acc_lanes_if_escaping_slots_were_registers"], 4)
        self.assertEqual(lp["escaping_partial_results"], [["V0"]])
        # control: no escaping call, the frozen reading stands and nothing is unscreened
        pro2 = [imm_op("SUB", "RSP", 0x200, 32), NOP, NOP]
        lp2 = self.one_loop(pro2, body)
        self.assertEqual((lp2["acc_lanes_emitted"], lp2["escaping_slots"], lp2["unscreened"]), (4, [], False))

    def test_split_with_one_half_spilled_is_unscreened_at_the_frozen_count(self):
        body = [vstore("RSP+0x40", "XMM0"), vop("VMULPS", "XMM0", "XMM7", "XMM7"), vload("XMM0", "RSP+0x40"),
                vop("VADDPS", "XMM0", "XMM0", "XMM5"), vop("VADDPS", "XMM1", "XMM1", "XMM6"), imm_op("ADD", "RSI", 0x10),
                JNZ]
        lp = self.one_loop(self.PRO, body)
        self.assertEqual((lp["acc_lanes_emitted"], lp["partial_results"]), (4, [["V1"]]))
        self.assertTrue(lp["unscreened"])
        self.assertEqual(lp["acc_lanes_if_escaping_slots_were_registers"], 8)
        self.assertEqual(lp["escaping_partial_results"], [["V0"]])

    def test_epilogue_call_after_the_loop_does_not_reach_it(self):
        """The shape of run 1's A/A-ninja k_avx2 Q8 loop: a stack address in an argument register at a call after the
        loop (there the /GS check, RDX under Win64; here RDI under SysV)."""
        pro = [imm_op("SUB", "RSP", 0x200, 32), NOP]
        epi = [lea("RDI", "RSP+0x100"), call(), imm_op("ADD", "RSP", 0x200, 32), RET]
        lp = self.one_loop(pro, spill_loop("RSP+0x100"), epi)
        self.assertEqual((lp["acc_lanes_emitted"], lp["escaping_slots"], lp["unscreened"]), (8, [], False))
        # the same call before the loop reaches it
        lp2 = self.one_loop([imm_op("SUB", "RSP", 0x200, 32), lea("RDI", "RSP+0x100"), call()], spill_loop("RSP+0x100"))
        self.assertEqual((lp2["acc_lanes_emitted"], lp2["escaping_slots"], lp2["unscreened"]), (0, ["STK:RSP:256"], True))

    def test_event_in_an_enclosing_loop_after_the_inner_loop_reaches_it(self):
        """0 prologue | outer header: nop | inner loop (spilled accumulator) | after it, still in the outer loop: a call
        with a stack address in RDI | outer latch | epilogue. The call reaches the inner header through the outer back
        edge, so the slot escapes."""
        head = [imm_op("SUB", "RSP", 0x200, 32), NOP]
        inner = spill_loop("RSP+0x100")
        after = [lea("RDI", "RSP+0x100"), call(), imm_op("ADD", "RDX", 0x10), JNZ]
        tail = [imm_op("ADD", "RSP", 0x200, 32), RET]
        seq = head + inner + after + tail
        h_out, h_in = 1, 2
        latch_in = h_in + len(inner) - 1
        latch_out = latch_in + len(after)
        res = self.loops(seq, {latch_in: [h_in, latch_in + 1], latch_out: [h_out, latch_out + 1]})
        self.assertEqual(res[h_in]["escaping_slots"], ["STK:RSP:256"])
        self.assertTrue(res[h_in]["unscreened"])

    def test_descriptive_fields_keep_the_frozen_reading(self):
        """Only acc_lanes_emitted, partial_results and partial_result_cycles take the X0-A1 reading; accumulators,
        acc_updates_per_iter (so u_acc and unrolled-u), fp_accumulator_ops, carried_registers and the tags do not."""
        seq, edges, ho, hi = chunk_stream(TestEscapingArray.REP)
        insts, succ = build(seq, edges)
        loops, preds = L.natural_loops((1, 0), succ)
        frames = L.FrameInfo(insts, succ)
        for lp in loops:
            new = L.analyse_loop(lp, insts, succ, preds, frames)
            L.MOVING_BASES["now"] = L.moving_bases(lp["body"], insts)
            try:
                old = L._analyse_loop(lp, insts, succ, preds)
            finally:
                L.MOVING_BASES["now"] = set()
            self.assertTrue(new["unscreened"])
            for k in old:
                if k not in L.A1_FIELDS:
                    self.assertEqual(new[k], old[k], k)
            self.assertNotEqual(new["acc_lanes_emitted"], old["acc_lanes_emitted"])
            self.assertTrue(old["accumulators"])


class TestHelpers(unittest.TestCase):
    def test_signed_immediates(self):
        self.assertEqual(L._imm_value({"IMM0": "0xc0", "IMM_WIDTH": "8", "IMM0SIGNED": True}, "IMM0"), -64)
        self.assertEqual(L._imm_value({"IMM0": "0x98", "IMM_WIDTH": "32", "IMM0SIGNED": True}, "IMM0"), 0x98)
        self.assertEqual(L._imm_value({"IMM0": "0xc0", "IMM_WIDTH": "8"}, "IMM0"), 0xc0)

    def test_cold_part_shares_the_frame(self):
        self.assertEqual(L._family({"function": "mm_q8.cold"}), "mm_q8")
        self.assertEqual(L._family({"function": "mm_q8.cold.3"}), "mm_q8")

    def test_access_width(self):
        self.assertEqual(L._access_width(vstore("RSP+0x40", "ZMM1")), 64)
        self.assertEqual(L._access_width(vstore("RSP+0x40", "XMM1")), 16)
        self.assertEqual(L._access_width(ins("MOV", ["MEM0/W", "REG0/R"], {"MEM0": "ptr [RAX]", "REG0": "RCX"})), 8)


class TestMainEndToEnd(unittest.TestCase):
    """x0_loops.main on a synthetic decode directory with two loops of one function (no attribution): the escaping
    array is reported in loops.json (p3c_unscreened, unscreened, escaping_slots). The first desktop run of the repro
    (2026-10-23) failed because main() reused the name `frames` (inline stacks) for the per-variant FrameInfo; that
    needs exact attribution to show and is covered by the desktop runs, not by this test."""

    def test_main_writes_unscreened_loops(self):
        import io
        import json
        import tempfile
        from contextlib import redirect_stdout
        seq, edges, ho, hi = chunk_stream(TestEscapingArray.REP)
        insts, succ = build(seq, edges)
        with tempfile.TemporaryDirectory() as d:
            dec = os.path.join(d, "decode")
            os.makedirs(dec)
            vid = "S:t_table:mm[0]"
            with open(os.path.join(dec, "variants.json"), "w") as fh:
                json.dump([{"config": "S", "table": "t_table", "slot": "mm[0]", "object": "t.o"}], fh)
            with open(os.path.join(dec, "instructions.jsonl"), "w") as fh:
                for (sec, off), r in sorted(insts.items()):
                    rec = dict(r, section=sec, offset=off, role="reachable", variant=vid, function="t_fn",
                               succ=[list(x) for x in succ[(sec, off)]], call=None, entry=(off == 0))
                    fh.write(json.dumps(rec) + chr(10))
            man = os.path.join(d, "manifest.json")
            with open(man, "w") as fh:
                json.dump({"objects": [{"object": "t.o", "source": "t.c", "format": "elf", "sha256": "0" * 64}], "variants": []}, fh)
            lt = os.path.join(d, "lt.csv")
            with open(lt, "w") as fh:
                fh.write("loop_id,function,variants,fp_accumulators,source_lanes,op,induction_pointer,bytes_per_iter,"
                         "trip_count,notes" + chr(10) + "t.c:1,t_fn,t.mm0,none,0,none,x,4,n,synthetic" + chr(10))
            out = os.path.join(d, "loops.json")
            argv = ["x0_loops.py", dec, "--manifest", man, "-o", out, "--loop-table", lt, "--canary-variant", "none",
                    "--d2-variants", "none", "--variant-map", "t_table:mm[0]=t.mm0"]
            old_argv = sys.argv
            try:
                sys.argv = argv
                with redirect_stdout(io.StringIO()):
                    rc = L.main()
            finally:
                sys.argv = old_argv
            self.assertEqual(rc, 0)
            with open(out) as fh:
                rec = json.load(fh)[0]
            self.assertEqual(sorted(rec["p3c_unscreened"]), sorted(lp["id"] for lp in rec["loops"]))
            self.assertEqual(rec["p3"]["c"], [])                 # bound 0, no register-like partial result left
            # review of 2026-10-23: the frozen reading's P3(c) (both loops, 8 lanes against 0) is kept for judge.py's
            # both-ways report, and the descriptive fields keep the frozen reading (FP accumulators, so not fp_free)
            self.assertEqual(sorted(rec["p3c_frozen_reading"]), sorted(lp["id"] for lp in rec["loops"]))
            self.assertTrue(all(not lp["fp_free"] and lp["accumulators"] for lp in rec["loops"]))
            self.assertTrue(all(lp["unscreened"] and lp["escaping_slots"] for lp in rec["loops"]))
            self.assertEqual(len(rec["loops"]), 2)


if __name__ == "__main__":
    unittest.main()
