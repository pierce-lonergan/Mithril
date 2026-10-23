"""Per-primitive precondition checks (DESIGN 4.2): each primitive refuses an application that would
change the FP DAG or the footprint, before any lowering. Run: python -I -m unittest discover -s tests
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from x3gen.core.sched import PrimError, Schedule  # noqa: E402
from x3gen.hearth import meaning  # noqa: E402
from x3gen.hearth.schedules import avx2, avx512, scalar  # noqa: E402

Q8, Q4 = meaning.MEANINGS["q8"], meaning.MEANINGS["q4"]


def fresh(k=Q4, isa="avx2"):
    return Schedule(k, isa)


class Positive(unittest.TestCase):
    def test_all_six_schedules_apply(self):
        for fn in (scalar.schedule, avx2.schedule, avx512.schedule):
            for k in (Q8, Q4):
                s = fn(k)
                prims = {a["prim"].split(".")[0] for a in s.log.apps}
                self.assertIn("P12", prims)
                self.assertTrue(all(a["facts"] for a in s.log.apps))

    def test_meaning_is_not_mutated(self):
        before = repr(Q4.body)
        avx512.schedule(Q4)
        self.assertEqual(before, repr(Q4.body))


class P1Split(unittest.TestCase):
    def test_nonpositive_factor(self):
        with self.assertRaises(PrimError):
            fresh().split("r", 0)

    def test_dup_last_on_fp_carried_loop(self):
        with self.assertRaises(PrimError):
            fresh().split("g", 2, tail="dup_last")

    def test_unknown_tail(self):
        with self.assertRaises(PrimError):
            fresh().split("r", 8, tail="wrap")


class P2Reorder(unittest.TestCase):
    def test_two_fp_carried_pieces(self):
        # planted 16 at primitive level: g split, then its pieces interchanged
        s = fresh()
        s.split("g", 2)
        with self.assertRaises(PrimError):
            s.reorder("g_o", "g_i")

    def test_not_a_perfect_nest(self):
        s = fresh()
        with self.assertRaises(PrimError):
            s.reorder("r", "g")  # r's body is [init, g loop, store]

    def test_token_inside_block_without_expansion(self):
        s = fresh()
        s.reorder("t", "r")
        s.split("t", 8)
        s.split("r", 8, tail="dup_last")
        s.reorder("r_i", "t_o")
        with self.assertRaises(PrimError):
            s._distribute_node(s.loop("t_i"))  # accumulator not expanded over t_i


class P3Expand(unittest.TestCase):
    def test_over_fp_carried_loop(self):
        with self.assertRaises(PrimError):
            fresh().expand("acc", "g")

    def test_not_reinitialised_inside(self):
        s = fresh()
        s.split("g", 2)
        with self.assertRaises(PrimError):
            s.expand("acc", "g_i")


class P4Vectorize(unittest.TestCase):
    def test_vectorize_reduction_loop(self):
        s = fresh()
        s.split("g", 8)
        with self.assertRaises(PrimError):
            s.vectorize("g_i", 8, 256)

    def test_lanes_differ_from_split(self):
        s = fresh()
        s.reorder("t", "r")
        s.split("r", 8, tail="dup_last")
        s.reorder("r_i", "t")
        with self.assertRaises(PrimError):
            s.vectorize("r_i", 4, 128, store="mask")

    def test_dup_last_needs_masked_store(self):
        s = fresh()
        s.reorder("t", "r")
        s.split("r", 8, tail="dup_last")
        s.reorder("r_i", "t")
        with self.assertRaises(PrimError):
            s.vectorize("r_i", 8, 256, store="full")

    def test_guarded_vector_tile(self):
        s = fresh()
        s.reorder("t", "r")
        s.split("r", 8, tail="guard")
        s.reorder("r_i", "t")
        with self.assertRaises(PrimError):
            s.vectorize("r_i", 8, 256, store="mask")


class P5LowerIsum(unittest.TestCase):
    def test_q8_biased_maddubs_saturates(self):
        # planted 8 at primitive level
        with self.assertRaises(PrimError):
            fresh(Q8).lower_isum("maddubs", signed="bias")

    def test_sign_transfer_needs_PRE1(self):
        # planted 22 at primitive level
        import planted

        with self.assertRaises(PrimError):
            fresh(planted.kernel_x_minus128(Q8)).lower_isum("maddubs", signed="sign_transfer")

    def test_bias_form_needs_P2(self):
        k = Q4.clone()
        k.requires = tuple(r for r in k.requires if "sum" not in r)
        with self.assertRaises(PrimError):
            fresh(k).lower_isum("dpbusd", signed="bias")

    def test_unknown_recipe(self):
        with self.assertRaises(PrimError):
            fresh().lower_isum("vpdpwssd")


class OtherPrimitives(unittest.TestCase):
    def test_P7_unroll_needs_constant_trip_count(self):
        with self.assertRaises(PrimError):
            fresh().unroll("g")

    def test_P8_no_shape_specialisation(self):
        for pred in (("n", "==", 4096), ("r1", "==", 240), ("T", "==", 8)):
            with self.assertRaises(PrimError):
                fresh().specialize("t", pred)

    def test_P9_hoist_needs_blocked_token_loop(self):
        s = fresh()
        with self.assertRaises(PrimError):
            s.hoist(("W",), out_of="t")

    def test_P9_hoist_needs_no_alias(self):
        k = Q4.clone()
        k.requires = tuple(r for r in k.requires if "disjoint" not in r)
        sch = Schedule(k, "avx2")
        sch.reorder("t", "r")
        sch.split("r", 8, tail="dup_last")
        sch.reorder("r_i", "t")
        sch.vectorize("r_i", 8, 256, store="mask")
        sch.block("t", 8, "r_i")
        with self.assertRaises(PrimError):
            sch.hoist(("W",), out_of="t_i")

    def test_P9_hoist_only_weights(self):
        sch = Schedule(Q4, "avx2")
        sch.reorder("t", "r")
        sch.split("r", 8, tail="dup_last")
        sch.reorder("r_i", "t")
        sch.vectorize("r_i", 8, 256, store="mask")
        sch.block("t", 8, "r_i")
        with self.assertRaises(PrimError):
            sch.hoist(("A",), out_of="t_i")

    def test_P11_prefetch_distance(self):
        with self.assertRaises(PrimError):
            fresh().prefetch("W", 0)
        with self.assertRaises(PrimError):
            fresh().prefetch("Y", 2)

    def test_P13_canon_lowering(self):
        with self.assertRaises(PrimError):
            fresh().canon_store("max_with_zero")

    def test_P14_scale_packing(self):
        with self.assertRaises(PrimError):
            fresh().load_scales("gather", "cvtph")

    def test_P15_commute(self):
        with self.assertRaises(PrimError):
            fresh().commute("canon")

    def test_P7_unroll_is_not_lowered(self):
        # review 2026-10-23: a logged unroll had no effect on the program (lower.py ignores it)
        s = fresh()
        s.split("r", 8, tail="dup_last")
        with self.assertRaises(PrimError) as cm:
            s.unroll("r_i")  # constant trip count: passes the precondition, then refuses
        self.assertIn("not lowered", str(cm.exception))

    def test_P15_needs_canon_at_every_store(self):
        # review 2026-10-23: commutation is exact only up to the NaN payload, erased by canon
        with self.assertRaises(PrimError):
            fresh().commute("fadd")
        s = fresh()
        s.canon_store("blendv")
        self.assertTrue(s.commute("fadd").startswith("P15.commute#"))


if __name__ == "__main__":
    unittest.main()
