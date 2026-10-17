"""Unit tests for x0_loops.py on SYNTHETIC instruction records (no object file, no Hearth code).

Run: python -I -m unittest discover -s experiments/x0-census/scripts/tests -v
"""
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0_loops as L  # noqa: E402


def ins(ic, ops, fields, length=4):
    """ops: list of 'NAME/ACTION'; fields: XED operand-storage values (REG0: ZMM0, MEM0: 'ptr [RSP+0x10]', ...)."""
    return {"iclass": ic, "operands": [o + "/X/EXPLICIT" for o in ops], "fields": fields, "len": length, "hex": "00" * length}


def vaddps(dst, a, b):
    return ins("VADDPS", ["REG0/W", "REG1/R", "REG2/R", "REG3/R"], {"REG0": dst, "REG1": "K0", "REG2": a, "REG3": b})


class TestLoops(unittest.TestCase):
    def build(self, seq, edges):
        insts = {(1, 4 * k): i for k, i in enumerate(seq)}
        succ = {(1, 4 * k): [(1, 4 * t) for t in edges.get(k, [k + 1] if k + 1 < len(seq) else [])] for k in range(len(seq))}
        return insts, succ

    def test_zmm_accumulator_16_lanes(self):
        seq = [ins("VXORPS", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "XMM0", "REG1": "XMM0", "REG2": "XMM0"}),  # 0
               ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "ZMM1", "MEM0": "ptr [RDI+RAX*1]"}),            # 1 header
               vaddps("ZMM0", "ZMM0", "ZMM1"),                                                                 # 2
               ins("ADD", ["REG0/RW", "IMM0/R"], {"REG0": "RAX", "IMM0": "0x40"}),                              # 3
               ins("JNZ", ["RELBR/R"], {}),                                                                    # 4 latch
               ins("RET_NEAR", [], {})]                                                                        # 5
        insts, succ = self.build(seq, {4: [1, 5]})
        loops, preds = L.natural_loops((1, 0), succ)
        self.assertEqual(len(loops), 1)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        self.assertEqual(info["accumulators"], {"V0": 16})
        self.assertEqual(info["acc_lanes_emitted"], 16)
        self.assertEqual(info["inductions"], {"RAX": 0x40})

    def test_serial_unroll_is_not_splitting(self):
        seq = [ins("NOP", [], {}),
               vaddps("ZMM0", "ZMM0", "ZMM1"), vaddps("ZMM0", "ZMM0", "ZMM2"),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = self.build(seq, {3: [1, 4]})
        loops, preds = L.natural_loops((1, 0), succ)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        self.assertEqual(info["acc_lanes_emitted"], 16)       # one register: 16 independent partial results
        self.assertEqual(info["acc_updates_per_iter"], 32)    # two updates per iteration: u_acc = 2 for 16 lanes

    def test_split_accumulators_are_counted(self):
        seq = [ins("NOP", [], {}),
               vaddps("ZMM0", "ZMM0", "ZMM2"), vaddps("ZMM1", "ZMM1", "ZMM3"),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = self.build(seq, {3: [1, 4]})
        loops, preds = L.natural_loops((1, 0), succ)
        self.assertEqual(L.analyse_loop(loops[0], insts, succ, preds)["acc_lanes_emitted"], 32)

    def test_spilled_accumulator_in_stack_slot(self):
        seq = [ins("NOP", [], {}),
               ins("VMOVUPS", ["REG0/W", "MEM0/R"], {"REG0": "YMM0", "MEM0": "ptr [RSP+0x20]"}),
               vaddps("YMM0", "YMM0", "YMM1"),
               ins("VMOVUPS", ["MEM0/W", "REG0/R"], {"REG0": "YMM0", "MEM0": "ptr [RSP+0x20]"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = self.build(seq, {4: [1, 5]})
        loops, preds = L.natural_loops((1, 0), succ)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        self.assertIn("spilled", info["tags"])
        self.assertEqual(info["accumulators"], {"STK:RSP:32": 8})   # constant stack slot treated as a register
        self.assertNotIn("software-pipelined", info["tags"])        # the slot is redefined by a store, not a load

    def test_scalar_pass_through_is_not_a_carried_read(self):
        """xmm2 carries an integer sum; VCVTSI2SS rewrites its lane 0 before the FP ops (the sd_q8 pattern)."""
        seq = [ins("NOP", [], {}),
               ins("VPADDD", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "XMM2", "REG1": "XMM2", "REG2": "XMM3"}),
               ins("VCVTSI2SS", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "XMM2", "REG1": "XMM15", "REG2": "EDI"}),
               ins("VMULSS", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "XMM2", "REG1": "XMM2", "REG2": "XMM0"}),
               ins("VMOVSS", ["MEM0/W", "REG0/R"], {"REG0": "XMM2", "MEM0": "ptr [R8+RAX*1]"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = self.build(seq, {5: [1, 6]})
        loops, preds = L.natural_loops((1, 0), succ)
        info = L.analyse_loop(loops[0], insts, succ, preds)
        self.assertEqual(info["accumulators"], {})
        self.assertEqual(info["acc_lanes_emitted"], 0)

    def test_scalar_accumulator_detected(self):
        seq = [ins("NOP", [], {}),
               ins("VCVTSI2SS", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "XMM2", "REG1": "XMM15", "REG2": "EDI"}),
               ins("VADDSS", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "XMM0", "REG1": "XMM0", "REG2": "XMM2"}),
               ins("JNZ", ["RELBR/R"], {}), ins("RET_NEAR", [], {})]
        insts, succ = self.build(seq, {3: [1, 4]})
        loops, preds = L.natural_loops((1, 0), succ)
        self.assertEqual(L.analyse_loop(loops[0], insts, succ, preds)["accumulators"], {"V0": 1})

    def test_no_loop(self):
        seq = [ins("NOP", [], {}), ins("RET_NEAR", [], {})]
        insts, succ = self.build(seq, {})
        self.assertEqual(L.natural_loops((1, 0), succ)[0], [])

    def test_parse_mem(self):
        self.assertEqual(L.parse_mem("ptr [RSP+0xc8]"), ("RSP", None, 0xc8))
        self.assertEqual(L.parse_mem("ptr [RCX+RAX*4-0x10]"), ("RCX", "RAX", -0x10))
        self.assertEqual(L.parse_mem("ptr [RIP-0x4]"), ("RIP", None, -4))


class TestTree16(unittest.TestCase):
    AVX512 = [("VEXTRACTF64X4", "V1", ["V0"], 1), ("VADDPS", "V0", ["V0", "V1"], 0),
              ("VEXTRACTF128", "V1", ["V0"], 1), ("VADDPS", "V0", ["V0", "V1"], 0),
              ("VMOVHLPS", "V1", ["V0", "V0"], 0), ("VADDPS", "V0", ["V0", "V1"], 0),
              ("VSHUFPS", "V1", ["V0", "V0"], 1), ("VADDSS", "V0", ["V0", "V1"], 0)]

    def test_hearth_tree_matches(self):
        self.assertEqual(L.track_tree16(self.AVX512, ["V0"]), "match")

    def test_avx2_two_registers(self):
        seq = [("VADDPS", "V2", ["V0", "V1"], 0)] + self.AVX512[2:]
        seq = [(ic, d if d != "V0" or k == 0 else d, s, imm) for k, (ic, d, s, imm) in enumerate(seq)]
        seq[1] = ("VEXTRACTF128", "V1", ["V2"], 1)
        seq[2] = ("VADDPS", "V0", ["V2", "V1"], 0)
        self.assertEqual(L.track_tree16(seq, ["V0", "V1"]), "match")

    def test_commutation_allowed(self):
        seq = list(self.AVX512)
        seq[1] = ("VADDPS", "V0", ["V1", "V0"], 0)
        self.assertEqual(L.track_tree16(seq, ["V0"]), "match")

    def test_wrong_pairing_is_mismatch(self):
        seq = list(self.AVX512)
        seq[6] = ("VMOVSHDUP", "V1", ["V0"], 0)      # pairs lanes 0 and 1 (same as shuffle 1) ...
        self.assertEqual(L.track_tree16(seq, ["V0"]), "match")
        seq[4] = ("VSHUFPS", "V1", ["V0", "V0"], 0xB1)  # pairs (0,1),(2,3) before (0,2): a different tree
        self.assertEqual(L.track_tree16(seq, ["V0"]), "mismatch")

    def test_unknown_instruction_is_unchecked(self):
        seq = list(self.AVX512)
        seq[4] = ("VHADDPS", "V1", ["V0", "V0"], 0)
        self.assertEqual(L.track_tree16(seq, ["V0"]), "unchecked")


class FakeConst:
    def __init__(self, words):
        self.words = words

    def mem_words(self, sec, off, ins, nb):
        return self.words.get(off)


class TestCanaryD1(unittest.TestCase):
    def test_pair_through_memory_constants(self):
        seq = [((1, 0), ins("VADDSS", ["REG0/W", "REG1/R", "MEM0/R"], {"REG0": "XMM1", "REG1": "XMM0", "MEM0": "ptr [RIP+0x0]"})),
               ((1, 8), ins("VMOVAPS", ["REG0/W", "REG1/R"], {"REG0": "XMM2", "REG1": "XMM1"})),
               ((1, 12), ins("VSUBSS", ["REG0/W", "REG1/R", "MEM0/R"], {"REG0": "XMM3", "REG1": "XMM2", "MEM0": "ptr [RIP+0x0]"}))]
        cr = FakeConst({0: [L.M_BITS], 12: [L.M_BITS]})
        self.assertEqual(L.canary_d1(seq, cr)[0], "pass")

    def test_legacy_sse_and_gpr_constant(self):
        seq = [((1, 0), ins("MOV", ["REG0/W", "IMM0/R"], {"REG0": "EAX", "IMM0": "0x4b400000"})),
               ((1, 5), ins("MOVD", ["REG0/W", "REG1/R"], {"REG0": "XMM5", "REG1": "EAX"})),
               ((1, 9), ins("ADDSS", ["REG0/RW", "REG1/R"], {"REG0": "XMM0", "REG1": "XMM5"})),
               ((1, 13), ins("SUBSS", ["REG0/RW", "REG1/R"], {"REG0": "XMM0", "REG1": "XMM5"}))]
        self.assertEqual(L.canary_d1(seq, FakeConst({}))[0], "pass")

    def test_folded_pair_fails(self):
        seq = [((1, 0), ins("VMULSS", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "XMM0", "REG1": "XMM1", "REG2": "XMM2"})),
               ((1, 4), ins("VCVTTSS2SI", ["REG0/W", "REG1/R"], {"REG0": "EAX", "REG1": "XMM0"}))]
        self.assertEqual(L.canary_d1(seq, FakeConst({}))[0], "fail")

    def test_reversed_subtraction_fails(self):
        seq = [((1, 0), ins("VADDSS", ["REG0/W", "REG1/R", "MEM0/R"], {"REG0": "XMM1", "REG1": "XMM0", "MEM0": "ptr [RIP+0x0]"})),
               ((1, 8), ins("VMOVSS", ["REG0/W", "MEM0/R"], {"REG0": "XMM4", "MEM0": "ptr [RIP+0x0]"})),
               ((1, 16), ins("VSUBSS", ["REG0/W", "REG1/R", "REG2/R"], {"REG0": "XMM3", "REG1": "XMM4", "REG2": "XMM1"}))]
        cr = FakeConst({0: [L.M_BITS], 8: [L.M_BITS]})
        self.assertEqual(L.canary_d1(seq, cr)[0], "fail")      # M - (v + M) is not the canary


if __name__ == "__main__":
    unittest.main()
