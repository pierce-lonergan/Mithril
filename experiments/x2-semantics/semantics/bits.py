"""binary32 / binary16 bit-level helpers. Pure integer arithmetic; no host floats.

Encodings (IEEE 754-2008 binary32): sign bit 31, biased exponent bits 30..23, fraction 22..0.
x86 uses the IEEE 754-2008 recommended NaN encoding: fraction bit 22 set = quiet NaN.
"""
from fractions import Fraction

F32_SIGN = 0x80000000
F32_EXP = 0x7F800000
F32_FRAC = 0x007FFFFF
F32_QUIET = 0x00400000
F32_PINF = 0x7F800000
F32_NINF = 0xFF800000
F32_MAX = 0x7F7FFFFF          # largest finite, (2 - 2^-23) * 2^127
F32_MIN_NORMAL = 0x00800000   # 2^-126

# x86 "QNaN floating-point indefinite" for single precision (SDM Vol 1 §4.8.3.7):
# sign 1, quiet, zero payload.
F32_QNAN_INDEFINITE = 0xFFC00000
# x86 "integer indefinite" for 32-bit integer results (SDM Vol 1 §4.8.3.7 / CVTPS2DQ).
I32_INDEFINITE = 0x80000000
# Hearth's canonical NaN (NUMERICS §3; quant.c HX_CANON_NAN). Not an x86 constant.
HEARTH_CANON_NAN = 0x7FC00000

F16_SIGN = 0x8000
F16_EXP = 0x7C00
F16_FRAC = 0x03FF
F16_QUIET = 0x0200

MASK32 = 0xFFFFFFFF


def u32(x):
    return x & MASK32


# ---------------------------------------------------------------- binary32 classification

def f32_sign(b):
    return (b >> 31) & 1


def f32_exp(b):
    return (b >> 23) & 0xFF


def f32_frac(b):
    return b & F32_FRAC


def f32_is_nan(b):
    return f32_exp(b) == 0xFF and f32_frac(b) != 0


def f32_is_snan(b):
    return f32_is_nan(b) and not (b & F32_QUIET)


def f32_is_qnan(b):
    return f32_is_nan(b) and bool(b & F32_QUIET)


def f32_is_inf(b):
    return (b & 0x7FFFFFFF) == F32_PINF


def f32_is_zero(b):
    return (b & 0x7FFFFFFF) == 0


def f32_is_denormal(b):
    """Nonzero with biased exponent 0 (x86 'denormal')."""
    return f32_exp(b) == 0 and f32_frac(b) != 0


def f32_class(b):
    if f32_is_zero(b):
        return "zero"
    if f32_is_denormal(b):
        return "denormal"
    if f32_is_inf(b):
        return "inf"
    if f32_is_snan(b):
        return "snan"
    if f32_is_qnan(b):
        return "qnan"
    return "normal"


def f32_quiet(b):
    """Quiet a NaN: set fraction bit 22, keep sign and the rest of the payload (SDM Vol 1 Table 4-7)."""
    assert f32_is_nan(b)
    return b | F32_QUIET


def f32_neg(b):
    return b ^ F32_SIGN


def f32_signed_zero(sign):
    return F32_SIGN if sign else 0


def f32_signed_inf(sign):
    return F32_NINF if sign else F32_PINF


def f32_value(b):
    """Exact value of a finite binary32 as a Fraction (-0.0 and +0.0 both give 0)."""
    assert not f32_is_nan(b) and not f32_is_inf(b)
    s, e, f = f32_sign(b), f32_exp(b), f32_frac(b)
    if e == 0:
        mag = Fraction(f, 1 << 149)
    else:
        m = (1 << 23) | f
        sh = e - 150
        mag = Fraction(m << sh, 1) if sh >= 0 else Fraction(m, 1 << (-sh))
    return -mag if s else mag


def f32_from_fields(sign, exp, frac):
    assert 0 <= exp <= 0xFF and 0 <= frac <= F32_FRAC
    return (sign << 31) | (exp << 23) | frac


# ---------------------------------------------------------------- binary16

def f16_is_nan(h):
    return (h & F16_EXP) == F16_EXP and (h & F16_FRAC) != 0


def f16_is_snan(h):
    return f16_is_nan(h) and not (h & F16_QUIET)


def f16_is_inf(h):
    return (h & 0x7FFF) == F16_EXP


def f16_is_denormal(h):
    return (h & F16_EXP) == 0 and (h & F16_FRAC) != 0


def f16_value(h):
    assert not f16_is_nan(h) and not f16_is_inf(h)
    s, e, f = (h >> 15) & 1, (h >> 10) & 0x1F, h & F16_FRAC
    if e == 0:
        mag = Fraction(f, 1 << 24)
    else:
        m = (1 << 10) | f
        sh = e - 25
        mag = Fraction(m << sh, 1) if sh >= 0 else Fraction(m, 1 << (-sh))
    return -mag if s else mag


# ---------------------------------------------------------------- integer helpers

def s8(x):
    x &= 0xFF
    return x - 0x100 if x & 0x80 else x


def s16(x):
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def s32(x):
    x &= MASK32
    return x - 0x100000000 if x & 0x80000000 else x


def sat_s16(v):
    return max(-32768, min(32767, v))


def sat_s8(v):
    return max(-128, min(127, v))


def sat_s32(v):
    return max(-(1 << 31), min((1 << 31) - 1, v))


def fmt32(b):
    return "0x%08X" % (b & MASK32)
