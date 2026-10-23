"""fp32 emulation edge cases, the meaning interpreter's ops, and printer rule 5.
Run: python -I -m unittest discover -s tests"""

import math
import pathlib
import struct
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from x3gen.core import fp32, interp, printer  # noqa: E402
from x3gen.core.emit import build  # noqa: E402
from x3gen.core.ir import Store, iter_nodes  # noqa: E402
from x3gen.hearth import meaning  # noqa: E402
from x3gen.hearth.schedules import avx2, avx512, scalar  # noqa: E402


def f2b(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


class Fp32(unittest.TestCase):
    def test_overflow_midpoint_and_neighbours(self):
        mid = fp32.OVF_MID
        self.assertEqual(fp32.rne_f32(mid), 0x7F800000)
        self.assertEqual(fp32.rne_f32(-mid), 0xFF800000)
        below = math.nextafter(mid, 0.0)
        self.assertEqual(fp32.rne_f32(below), 0x7F7FFFFF)
        self.assertEqual(fp32.rne_f32(1e39), 0x7F800000)

    def test_subnormals_and_ties(self):
        tiny = 2.0**-149
        self.assertEqual(fp32.rne_f32(tiny), 1)
        self.assertEqual(fp32.rne_f32(tiny / 2), 0)  # tie to even: 0
        self.assertEqual(fp32.rne_f32(tiny * 1.5), 2)  # tie between 1 and 2 -> even 2
        self.assertEqual(fp32.rne_f32(-0.0), 0x80000000)

    def test_nan_is_nan(self):
        self.assertTrue(fp32.is_nan(fp32.rne_f32(math.nan)))
        self.assertTrue(fp32.is_nan(fp32.fadd(0x7F800000, 0xFF800000)))
        self.assertTrue(fp32.is_nan(fp32.fmul(0x7F800000, 0)))
        self.assertEqual(fp32.canon(0xFFC00001), fp32.QNAN)

    def test_x86_nan_rules(self):
        """Review 2026-10-23 (meaning lens), finding 4: x86 NaN results, not one canonical NaN."""
        one = f2b(1.0)
        self.assertEqual(fp32.fadd(0x7F800000, 0xFF800000), fp32.DEFAULT_NAN)  # inf - inf
        self.assertEqual(fp32.fmul(0x7F800000, 0), fp32.DEFAULT_NAN)  # inf * 0
        self.assertEqual(fp32.fadd(0x7FC00123, one), 0x7FC00123)  # payload propagates
        self.assertEqual(fp32.fmul(one, 0xFF800001), 0xFFC00001)  # signalling NaN is quieted
        self.assertEqual(fp32.fadd(0x7FC00001, 0x7FC00002), 0x7FC00001)  # first operand wins
        for b in (fp32.DEFAULT_NAN, 0xFFC00001, 0x7F800001):
            self.assertEqual(fp32.canon(b), fp32.QNAN)

    def test_signed_zero_sums(self):
        self.assertEqual(fp32.fadd(0, 0x80000000), 0)  # +0 + -0 = +0 (why acc_0 = +0.0 matters)
        self.assertEqual(fp32.fadd(0x80000000, 0x80000000), 0x80000000)

    def test_h2f_all_inputs_match_ieee(self):
        for h in range(65536):
            b = fp32.h2f(h)
            ref = struct.unpack("<e", struct.pack("<H", h))[0]
            if ref != ref:
                self.assertTrue(fp32.is_nan(b))
                self.assertTrue(b & 0x00400000)  # quieted, as F16C does
            else:
                self.assertEqual(b, f2b(ref), hex(h))

    def test_i2f_exact_range(self):
        self.assertEqual(fp32.i2f(-(2**24) + 1), f2b(-(2.0**24) + 1))
        with self.assertRaises(ValueError):
            fp32.i2f(2**24)


def without_canon(k):
    k2 = k.clone()
    for nd in iter_nodes(k2.body):
        if isinstance(nd, Store) and nd.value.op == "canon":
            nd.value = nd.value.args[0]
    return k2


class CanonVisible(unittest.TestCase):
    """The meaning differential can see canon (review 2026-10-23, meaning lens, finding 4): with
    x86 NaN results in the interpreter, a canon-less meaning gives a non-canonical NaN where
    Hearth's q_canon stores 0x7fc00000."""

    def run_one(self, k, wd, ad, q=0):
        F = k.params["W"][1]
        w = bytearray(F.size)
        struct.pack_into("<H", w, 0, wd)
        for i in range(F.q.nbytes):
            w[F.q.offset + i] = q
        a = bytearray(72)
        struct.pack_into("<If", a, 0, ad, 0.0)
        y = [0x7FC0DEAD]
        interp.run(k, bytes(w), bytes(a), 64, 1, y, 1, 0, 1)
        return y[0]

    def test_canonless_meaning_fails_where_hearth_canonicalises(self):
        for fmt in ("q8", "q4"):
            k = meaning.MEANINGS[fmt]
            q = 0x88 if fmt == "q4" else 0  # codes 0: I = 0
            # I = 0 and an inf weight scale: 0 * inf is invalid; NaN scales propagate their payload
            for wd, ad in ((0x7C00, f2b(1.0)), (0x3C00, 0xFFC00001), (0x7E01, f2b(2.0))):
                self.assertEqual(self.run_one(k, wd, ad, q), fp32.QNAN)
                self.assertNotEqual(self.run_one(without_canon(k), wd, ad, q), fp32.QNAN)


class Printer(unittest.TestCase):
    def test_rule5_rejects_two_fp_ops(self):
        bad = "void f(void) {\n    const __m256 a = _mm256_add_ps(_mm256_mul_ps(x, y), z);\n}\n"
        with self.assertRaises(printer.PrintError):
            printer.rule5(bad)
        bad2 = "void f(void) {\n    const float a = b * c + d;\n}\n"
        with self.assertRaises(printer.PrintError):
            printer.rule5(bad2)

    def test_rule5_accepts_integer_and_pointer_arithmetic(self):
        ok = (
            "void f(void) {\n    float *yp = Y + ((((size_t)t) * ldy) + r);\n"
            "    const int32_t m = c * x + 3;\n    const float q = p * d;\n}\n"
        )
        self.assertGreater(printer.rule5(ok), 0)

    def test_generated_files_are_deterministic_and_rule5_clean(self):
        sched = {"scalar": scalar.schedule, "avx2": avx2.schedule, "avx512": avx512.schedule}
        files = {k: ROOT / "x3gen" / "hearth" / "schedules" / (k + ".py") for k in sched}
        mf = ROOT / "x3gen" / "hearth" / "meaning.py"
        a, _ = build(meaning.MEANINGS, sched, mf, files)
        b, _ = build(meaning.MEANINGS, sched, mf, files)
        self.assertEqual(a, b)
        for name, text in a.items():
            self.assertNotIn("\r", text)
            if name.endswith(".c"):
                self.assertGreater(printer.rule5(text), 100)
        committed = ROOT / "generated"
        for name, text in a.items():
            self.assertEqual((committed / name).read_bytes(), text.encode(), name)


if __name__ == "__main__":
    unittest.main()
