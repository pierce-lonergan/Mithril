"""Checker rules added after the first 2026-10-23 review: a chain that equals the meaning only up to
commutation is accepted only when a P15 application is logged, and shapes must satisfy the
meaning's preconditions (an injective output map). Rules added after the second 2026-10-23 review
(meaning and checker lenses): the shape domain is evaluated from meaning.REQUIRES; index arithmetic
is evaluated in C's integer types; every string the printer copies is checked; coverage sites are
positions. The planted suite (tests/planted.py) covers the rules on whole programs.
Run: python -I -m unittest discover -s tests
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from x3gen.core import check, lower, printer  # noqa: E402
from x3gen.core.lp import IX, Call, Comment, Do, For, Let, Program, Set, Var, ix, walk  # noqa: E402
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


class RequiresDriveTheDomain(unittest.TestCase):
    """Review 2026-10-23 (meaning lens) findings 1 and 3: the checked shape domain is evaluated from
    meaning.REQUIRES, and PRE3 is the MXCSR predicate with the status flags unconstrained."""

    def test_each_shape_condition_is_enforced(self):
        k, s, f = scalar_variant()
        for bad in [(-64, 1, 0, 1, 1), (96, 1, 0, 1, 1), (64, -1, 0, 1, 1), (64, 1, 3, 2, 3)]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                check.shape_ok(k, bad)
        check.shape_ok(k, (0, 0, 0, 0, 0))

    def test_unknown_or_inconsistent_requirements_are_refused(self):
        k, s, f = scalar_variant()
        k2 = k.clone()
        k2.requires = k.requires + ("W rows are 64-byte aligned",)
        with self.assertRaises(ValueError):
            check.shape_ok(k2, (64, 1, 0, 1, 1))
        k3 = k.clone()
        k3.requires = tuple(
            "A.q in [-128, 127]" if r.startswith("A.q in") else r for r in k.requires
        )
        with self.assertRaises(ValueError):  # PRE1 disagrees with ActQ8's value_range
            check.shape_ok(k3, (64, 1, 0, 1, 1))

    def test_pre3_is_the_mxcsr_control_predicate(self):
        pre3 = [r for r in meaning.REQUIRES if "mxcsr" in r]
        self.assertEqual(pre3, ["(mxcsr & 0xFFC0) == 0x1F80"])

        def holds(v):
            return eval(pre3[0], {"__builtins__": {}}, {"mxcsr": v})  # noqa: S307 (fixed text)

        self.assertTrue(holds(0x1F80))
        self.assertTrue(holds(0x1FA0))  # precision flag set, as measured during the runs
        for v in (0x9F80, 0x1FC0, 0x3F80, 0x5F80, 0x1F00, 0x1E80, 0x1D80, 0x1B80, 0x1780, 0x0F80):
            self.assertFalse(holds(v), hex(v))  # FTZ, DAZ, RC != nearest, a mask cleared


SHAPE = (128, 2, 0, 3, 3)


class CIntegerSemantics(unittest.TestCase):
    """Review 2026-10-23 (checker lens) findings 1 and 4: index arithmetic is evaluated in the C
    types the printer emits; a value outside its type is rejected, never wrapped."""

    def machine(self, G=None):
        k, s, f = scalar_variant()
        n, T, r0, r1, ldy = SHAPE
        m = check.Machine(k, f, (64 * G if G else n, T, r0, r1, ldy), s.log.ids())
        if G is not None:
            m.env["G"], m.tenv["G"] = check.TInt(G, (0, 1, 0)), (64, True)
        return m

    def reject(self, e, G=None, what="outside the C type"):
        with self.assertRaises(check.Reject) as cm:
            self.machine(G).ev(e)
        self.assertIn(what, str(cm.exception))

    def test_unsigned_wrap(self):
        self.reject(ix("-", ix("cast", "size_t", 0), 72))

    def test_narrowing_cast(self):
        self.reject(ix("cast", "int", ix("<<", ix("cast", "int64_t", 1), 32)))

    def test_suffixed_literal(self):
        self.reject(ix("-", IX("lit", ("0u",)), 16), what="plain decimal")

    def test_mixed_signedness(self):
        self.reject(ix("<", ix("cast", "size_t", 1), 2), what="signed and unsigned")
        self.reject(ix("/", ix("cast", "size_t", 8), 2), what="signed and unsigned")

    def test_signed_overflow(self):
        self.reject(ix("*", 65536, 65536))

    def test_block_count_value_checked_for_every_G(self):
        self.reject(ix("-", ix("cast", "size_t", Var("G")), 6), G=7)  # G = 7 here, wraps at G <= 5
        self.reject(ix("cast", "int", Var("G")), G=2)  # fine at G = 2, not for every G

    def test_generated_forms_are_accepted(self):
        m = self.machine(G=3)
        v = m.ev(ix("*", ix("cast", "size_t", Var("G")), 66))
        self.assertEqual((int(v), v.aff), (198, (0, 66, 0)))
        self.assertEqual(m.ev(ix("cast", "__mmask8", ix("-", ix("<<", 1, 4), 1))), 15)


def first(f, pred):
    for st in walk(f.body):
        if pred(st):
            return st
    raise AssertionError("no such statement")


class VerbatimChannels(unittest.TestCase):
    """Review 2026-10-23 (checker lens) finding 2, and the reviser's three further channels: every
    string the printer copies is checked by audit_static, and refused again by the printer."""

    def both(self, mutate, what):
        k, s, f = scalar_variant("q4")
        mutate(f)
        with self.assertRaises(check.Reject) as cm:
            check.audit_static(f, s.log.ids())
        self.assertIn(what, str(cm.exception))
        prog = Program("scalar", None, (), [], [f], [])
        with self.assertRaises(printer.PrintError):
            printer.print_program(prog)

    def test_comment(self):
        self.both(lambda f: f.body.insert(0, Comment("*/ int x; /*")), "comment")

    def test_identifier(self):
        def mut(f):
            first(f, lambda st: isinstance(st, Let) and st.name == "c1").name = "c1 = 0; int c9"

        self.both(mut, "identifier")

    def test_declared_type(self):
        def mut(f):
            first(f, lambda st: isinstance(st, Let) and st.name == "c1").ctype = "int x = 1; int"

        self.both(mut, "type")

    def test_cast_type(self):
        def mut(f):
            st = first(f, lambda st: isinstance(st, Let) and st.name == "rb")
            st.rhs = ix("*", ix("cast", "size_t)(1) + (size_t", Var("G")), 34)

        self.both(mut, "cast type")

    def test_nested_operator_call(self):
        def mut(f):
            c1 = first(f, lambda st: isinstance(st, Let) and st.name == "c1")
            m = first(f, lambda st: isinstance(st, Let) and st.name == "m")
            m.rhs = Call(m.rhs.entry, (c1.rhs, m.rhs.args[1]))

        self.both(mut, "nested")

    def test_glued_placeholder(self):
        def mut(f):
            st = first(
                f, lambda st: isinstance(st, Let) and getattr(st.rhs, "entry", 0) == "f32.bits"
            )
            st.rhs = Call("f32.bits", (Var("G"),))

        self.both(mut, "non-negative literal")

    def test_call_result_retyped(self):
        def mut(f):
            first(f, lambda st: isinstance(st, Let) and st.name == "ad").ctype = "int32_t"

        self.both(mut, "holds a float result")

    def test_provenance_binds_stores_to_P13(self):
        k, s, f = scalar_variant("q4")
        store = first(f, lambda st: isinstance(st, Do) and st.call.entry == "f32.store")
        p12 = [i for i in s.log.ids() if i.startswith("P12.")][0]
        store.prov = p12
        with self.assertRaises(check.Reject) as cm:
            check.audit_static(f, s.log.ids())
        self.assertIn("licence does not cover", str(cm.exception))


class CallArgumentKinds(unittest.TestCase):
    """The call-side twin of finding 1 (reviser): an argument C would convert numerically at the
    call (an integer to a float parameter, a float to an integer one) is rejected."""

    def run_variant(self, mutate):
        k, s, f = scalar_variant("q4")
        mutate(f)
        with self.assertRaises(check.Reject) as cm:
            check.check_func(k, f, s.log.ids(), check.default_shapes(1, 1))
        self.assertIn("C would convert it", str(cm.exception))

    def test_integer_to_a_float_parameter(self):
        def mut(f):
            st = first(f, lambda st: isinstance(st, Let) and st.name == "f")
            st.rhs = Call(st.rhs.entry, (st.rhs.args[0], 2))

        self.run_variant(mut)

    def test_float_to_an_integer_parameter(self):
        def mut(f):  # dw = x3_h2f(fi): C would convert the float fi to a uint64_t
            st = first(f, lambda st: isinstance(st, Let) and st.name == "dw")
            st.rhs = Call(st.rhs.entry, (Var("fi"),))

        self.run_variant(mut)

    def test_every_entry_has_kinds_for_its_placeholders(self):
        import re

        from x3gen.isa import TABLE

        for e in TABLE.values():
            n = len(set(re.findall(r"\{(\d+)\}", e.c)))
            self.assertEqual(len(check.arg_kinds(e)), n, e.key)


class CoverageByPosition(unittest.TestCase):
    """Review 2026-10-23 (checker lens) finding 3: a statement object placed at a second position
    that never runs is unchecked code, even though the same object runs elsewhere."""

    def test_aliased_statement_is_a_second_site(self):
        k, s, f = scalar_variant("q8")
        loop = first(f, lambda st: isinstance(st, For) and st.var == "g")
        acc_update = [st for st in loop.body if isinstance(st, Set)][-1]
        loop.body.append(
            For("tt", "int", 18, ix("<", Var("tt"), Var("T")), 1, [acc_update], prov=loop.prov)
        )
        with self.assertRaises(check.Reject) as cm:
            check.check_func(k, f, s.log.ids(), check.default_shapes(1, 1))
        self.assertEqual(cm.exception.stage, "C1 coverage")


if __name__ == "__main__":
    unittest.main()
