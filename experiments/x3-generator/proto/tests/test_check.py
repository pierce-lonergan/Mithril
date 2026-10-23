"""Checker rules added after the 2026-10-23 review: a chain that equals the meaning only up to
commutation is accepted only when a P15 application is logged, and shapes must satisfy the
meaning's preconditions (an injective output map). The planted suite (tests/planted.py) covers
the other new rules. Run: python -I -m unittest discover -s tests
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from x3gen.core import check, lower  # noqa: E402
from x3gen.core.lp import Call, Let, Set, walk  # noqa: E402
from x3gen.hearth import meaning  # noqa: E402
from x3gen.hearth.schedules import scalar  # noqa: E402


def scalar_variant(fmt="q8"):
    k = meaning.MEANINGS[fmt]
    s = scalar.schedule(k)
    return k, s, lower.lower(s, "x3_test_%s_scalar" % fmt)


def commute_first(f, entry, target=None):
    """Swap the operands of the first statement computing `entry` (optionally assigning target)."""
    for st in walk(f.body):
        if not (isinstance(st, (Let, Set)) and isinstance(st.rhs, Call)):
            continue
        name = st.name if isinstance(st, Let) else getattr(st.target, "name", None)
        if st.rhs.entry == entry and (target is None or name == target):
            a, b = st.rhs.args
            st.rhs = Call(st.rhs.entry, (b, a))
            return
    raise AssertionError("no %s statement" % entry)


class P15Licence(unittest.TestCase):
    def _both_ways(self, entry, target=None):
        k, s, f = scalar_variant()
        commute_first(f, entry, target)
        shapes = check.default_shapes(1, 1)
        with self.assertRaises(check.Reject) as cm:
            check.check_func(k, f, s.log.ids(), shapes)
        self.assertIn("no P15 application is logged", str(cm.exception))
        r = check.check_func(k, f, s.log.ids() | {check.P15_ID + "99"}, shapes)
        self.assertEqual(r["commuted"], r["stores"])
        self.assertGreater(r["stores"], 0)

    def test_commuted_accumulation(self):
        self._both_ways("f32.add", target="acc")

    def test_commuted_scale_product(self):
        self._both_ways("f32.mul", target="f")

    def test_uncommuted_variant_needs_no_licence(self):
        k, s, f = scalar_variant("q4")
        r = check.check_func(k, f, s.log.ids(), check.default_shapes(1, 1))
        self.assertEqual(r["commuted"], 0)


class BlockCountForms(unittest.TestCase):
    def test_block_count_value_in_a_narrow_type(self):
        k, s, f = scalar_variant()
        rb = [st for st in f.body if isinstance(st, Let) and st.name == "rb"][0]
        rb.ctype = "const int"  # C would wrap rb = G * size for large G; the forms are over Z
        with self.assertRaises(check.Reject) as cm:
            check.structure(f, k)
        self.assertIn("narrow", str(cm.exception))

    def test_loads_carry_affine_forms(self):
        k, s, f = scalar_variant("q4")
        seen = []
        m = check.Machine(k, f, (192, 2, 1, 3, 4), s.log.ids())
        orig = m._uniform

        def spy(p, nb):
            seen.append((p.buf, p.aff, nb))
            return orig(p, nb)

        m._uniform = spy
        m.execute()
        blk = {"W": k.params["W"][1].size, "A": k.params["A"][1].size}
        self.assertTrue(seen)
        for buf, (c0, cG, cg), nb in seen:
            self.assertEqual(cg, blk[buf])  # block g of the row (token), for every G
            self.assertEqual(cG % blk[buf], 0)
            self.assertLessEqual(c0 + nb, blk[buf])


class ShapePreconditions(unittest.TestCase):
    def test_output_map_must_be_injective(self):
        k, s, f = scalar_variant()
        with self.assertRaises(ValueError):
            check.check_shape(k, f, (128, 2, 0, 10, 5), s.log.ids())  # T > 1, ldy < r1 - r0
        r = check.check_shape(k, f, (128, 2, 4, 10, 6), s.log.ids())  # ldy = r1 - r0 < r1
        self.assertEqual(r["stores"], 12)
        r = check.check_shape(k, f, (64, 1, 3, 9, 2), s.log.ids())  # T == 1: any ldy
        self.assertEqual(r["stores"], 6)

    def test_meaning_states_the_precondition(self):
        for k in meaning.MEANINGS.values():
            self.assertIn("T <= 1 or ldy >= r1 - r0", k.requires)


if __name__ == "__main__":
    unittest.main()
