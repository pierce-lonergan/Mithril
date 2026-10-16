"""FP lane functions. Each takes raw bit patterns and an Env and returns (result_bits, flags).

The NaN layer is explicit bit-vector logic around an exact-arithmetic core, which is what the SMT
encoding must do too (SMT-LIB FPA has one NaN per sort; TABLE-SCHEMA.md §5).

NaN rules, SSE/AVX column of SDM Vol 1 Table 4-7 ("Rules for handling NaNs"), two-source arithmetic:
  * if source 1 is a NaN: result = source 1, quieted (fraction bit 22 set; sign and payload kept)
  * else if source 2 is a NaN: result = source 2, quieted
  * else if the operation is invalid (inf - inf, 0 * inf, 0/0, inf/inf): QNaN indefinite 0xFFC00000
  * IE is raised iff a source is an SNaN or the operation is invalid.
"Source 1" is the first source operand of the instruction encoding: for VADDPS xmm1, xmm2, xmm3 it is
xmm2; for legacy ADDPS xmm1, xmm2 it is xmm1 (also the destination). For the C intrinsic
_mm_add_ps(a, b) it is `a` -- but only if the compiler kept the operand order, which it need not.
This is why NaN payloads are canonicalised in Hearth (NUMERICS §3) and why T1's commutation rules
carry the NaN-order side condition (RULES.md).

Flag priority (masked): a NaN source suppresses DE (SDM Vol 1 §4.9.2 priority: SNaN invalid, then
QNaN operand, then other invalid, then denormal, then overflow/underflow, then inexact). UNCERTAIN
for silicon: fuzz class F-FLAGPRI.
"""
from fractions import Fraction

from .bits import (F32_QNAN_INDEFINITE, F32_QUIET, F32_SIGN, I32_INDEFINITE, f16_is_nan,
                   f16_is_snan, f16_value, f32_is_denormal, f32_is_inf, f32_is_nan, f32_is_snan,
                   f32_is_zero, f32_quiet, f32_sign, f32_signed_inf, f32_signed_zero, f32_value,
                   s32, u32)
from .fpenv import DE, IE, PE, RC_RD, RC_RZ, ZE
from .rounding import round_f32, round_to_integer


# ---------------------------------------------------------------- shared pieces

def _nan_select(a, b):
    """Two-source arithmetic NaN propagation (Table 4-7, SSE column). Caller checks a NaN exists."""
    flags = IE if (f32_is_snan(a) or f32_is_snan(b)) else 0
    return (f32_quiet(a) if f32_is_nan(a) else f32_quiet(b)), flags


def _daz(b, env, reports_de=True):
    """Apply DAZ to one non-NaN source. Returns (bits, flags). Under DAZ a denormal becomes a zero
    of the same sign and DE is NOT raised (SDM Vol 1 §10.2.3.4)."""
    if f32_is_denormal(b):
        if env.daz:
            return b & F32_SIGN, 0
        return b, (DE if reports_de else 0)
    return b, 0


def _finish(negative, value, env):
    """Round an exact nonzero value; exact zeros are handled by the callers."""
    return round_f32(negative, abs(value), env.rc, env.ftz)


def _exact_zero_sum_sign(sa, sb, both_zero_inputs, env):
    """IEEE 754-2019 §6.3: an exact zero sum of opposite-signed operands is +0, except under
    roundTowardNegative where it is -0; x + x keeps the sign of x (so -0 + -0 = -0)."""
    if both_zero_inputs and sa == sb:
        return sa
    return 1 if env.rc == RC_RD else 0


# ---------------------------------------------------------------- arithmetic

def add(a, b, env):
    if f32_is_nan(a) or f32_is_nan(b):
        return _nan_select(a, b)
    a, fa = _daz(a, env)
    b, fb = _daz(b, env)
    fl = fa | fb
    ia, ib = f32_is_inf(a), f32_is_inf(b)
    if ia and ib:
        if f32_sign(a) != f32_sign(b):
            return F32_QNAN_INDEFINITE, IE
        return a, fl
    if ia:
        return a, fl
    if ib:
        return b, fl
    s = f32_value(a) + f32_value(b)
    if s == 0:
        sign = _exact_zero_sum_sign(f32_sign(a), f32_sign(b), f32_is_zero(a) and f32_is_zero(b), env)
        return f32_signed_zero(sign), fl
    r, f = _finish(s < 0, s, env)
    return r, fl | f


def sub(a, b, env):
    """a - b. NaN selection uses the operands as given (b's sign is NOT flipped on the NaN path)."""
    if f32_is_nan(a) or f32_is_nan(b):
        return _nan_select(a, b)
    return add(a, b ^ F32_SIGN, env)


def mul(a, b, env):
    if f32_is_nan(a) or f32_is_nan(b):
        return _nan_select(a, b)
    a, fa = _daz(a, env)
    b, fb = _daz(b, env)
    fl = fa | fb
    sign = f32_sign(a) ^ f32_sign(b)
    ia, ib, za, zb = f32_is_inf(a), f32_is_inf(b), f32_is_zero(a), f32_is_zero(b)
    if (ia and zb) or (ib and za):
        return F32_QNAN_INDEFINITE, IE
    if ia or ib:
        return f32_signed_inf(sign), fl
    if za or zb:
        return f32_signed_zero(sign), fl
    p = f32_value(a) * f32_value(b)
    r, f = _finish(sign == 1, p, env)
    return r, fl | f


def div(a, b, env):
    if f32_is_nan(a) or f32_is_nan(b):
        return _nan_select(a, b)
    a, fa = _daz(a, env)
    b, fb = _daz(b, env)
    fl = fa | fb
    sign = f32_sign(a) ^ f32_sign(b)
    ia, ib, za, zb = f32_is_inf(a), f32_is_inf(b), f32_is_zero(a), f32_is_zero(b)
    if (ia and ib) or (za and zb):
        return F32_QNAN_INDEFINITE, IE
    if ia:
        return f32_signed_inf(sign), fl
    if ib:
        return f32_signed_zero(sign), fl
    if zb:
        return f32_signed_inf(sign), fl | ZE
    if za:
        return f32_signed_zero(sign), fl
    q = f32_value(a) / f32_value(b)
    r, f = _finish(sign == 1, q, env)
    return r, fl | f


# ---------------------------------------------------------------- selection: MAX / MIN

def _minmax(a, b, env, want_greater):
    """SDM MAXPS/MINPS pseudocode:
         MAX(SRC1, SRC2): if SRC1 = 0.0 and SRC2 = 0.0 (either sign) -> SRC2
                          else if SRC1 = NaN -> SRC2; else if SRC2 = NaN -> SRC2
                          else if SRC1 > SRC2 -> SRC1 else SRC2
       The second source is returned UNCHANGED: an SNaN is not quieted.
       IE for any NaN source (QNaN included: MAX/MIN are signalling comparisons).
       DAZ: denormal sources are replaced by signed zeros BEFORE selection, so the selected value
       is the flushed zero (as Bochs f32_max/f32_min do). UNCERTAIN on silicon: class F-DAZ-SEL.
       FTZ does not apply (no rounding happens)."""
    if f32_is_nan(a) or f32_is_nan(b):
        a = a & F32_SIGN if (env.daz and f32_is_denormal(a)) else a
        b = b & F32_SIGN if (env.daz and f32_is_denormal(b)) else b
        return b, IE
    a, fa = _daz(a, env)
    b, fb = _daz(b, env)
    fl = fa | fb
    if f32_is_zero(a) and f32_is_zero(b):
        return b, fl
    ka, kb = _order_key(a), _order_key(b)
    take_a = (ka > kb) if want_greater else (ka < kb)
    return (a if take_a else b), fl


def _order_key(x):
    """Total order on non-NaN binary32 values; +0 and -0 compare equal."""
    if f32_is_inf(x):
        return (-1 if f32_sign(x) else 1, Fraction(0))
    return (0, f32_value(x))


def max_(a, b, env):
    return _minmax(a, b, env, True)


def min_(a, b, env):
    return _minmax(a, b, env, False)


# ---------------------------------------------------------------- comparisons

LT, EQ, GT, UN = 1, 2, 4, 8

# (name, relation set that yields TRUE, signals IE on a QNaN?) for imm8 = 0..31, the VCMPPS
# predicate table (SDM Vol 2 CMPPS, Table 3-1). Names match the C _CMP_* constants.
# Hearth uses UNORD_Q (3) for NaN canonicalisation and ORD_Q (7) for NaN zeroing.
CMP_PREDICATES = [
    ("EQ_OQ", EQ, False),               # 0x00
    ("LT_OS", LT, True),                # 0x01
    ("LE_OS", LT | EQ, True),           # 0x02
    ("UNORD_Q", UN, False),             # 0x03
    ("NEQ_UQ", LT | GT | UN, False),    # 0x04
    ("NLT_US", EQ | GT | UN, True),     # 0x05
    ("NLE_US", GT | UN, True),          # 0x06
    ("ORD_Q", LT | EQ | GT, False),     # 0x07
    ("EQ_UQ", EQ | UN, False),          # 0x08
    ("NGE_US", LT | UN, True),          # 0x09
    ("NGT_US", LT | EQ | UN, True),     # 0x0A
    ("FALSE_OQ", 0, False),             # 0x0B
    ("NEQ_OQ", LT | GT, False),         # 0x0C
    ("GE_OS", GT | EQ, True),           # 0x0D
    ("GT_OS", GT, True),                # 0x0E
    ("TRUE_UQ", LT | EQ | GT | UN, False),  # 0x0F
    ("EQ_OS", EQ, True),                # 0x10
    ("LT_OQ", LT, False),               # 0x11
    ("LE_OQ", LT | EQ, False),          # 0x12
    ("UNORD_S", UN, True),              # 0x13
    ("NEQ_US", LT | GT | UN, True),     # 0x14
    ("NLT_UQ", EQ | GT | UN, False),    # 0x15
    ("NLE_UQ", GT | UN, False),         # 0x16
    ("ORD_S", LT | EQ | GT, True),      # 0x17
    ("EQ_US", EQ | UN, True),           # 0x18
    ("NGE_UQ", LT | UN, False),         # 0x19
    ("NGT_UQ", LT | EQ | UN, False),    # 0x1A
    ("FALSE_OS", 0, True),              # 0x1B
    ("NEQ_OS", LT | GT, True),          # 0x1C
    ("GE_OQ", GT | EQ, False),          # 0x1D
    ("GT_OQ", GT, False),               # 0x1E
    ("TRUE_US", LT | EQ | GT | UN, True),   # 0x1F
]
CMP_BY_NAME = {n: i for i, (n, _, _) in enumerate(CMP_PREDICATES)}


def relation(a, b, env, signalling):
    """Returns (relation, flags). DAZ zeroes denormals first; +0 == -0."""
    if f32_is_nan(a) or f32_is_nan(b):
        f = IE if (signalling or f32_is_snan(a) or f32_is_snan(b)) else 0
        return UN, f
    a, fa = _daz(a, env)
    b, fb = _daz(b, env)
    fl = fa | fb
    ka, kb = _order_key(a), _order_key(b)
    if ka == kb:
        return EQ, fl
    return (LT if ka < kb else GT), fl


def cmp_pred(a, b, imm, env):
    """One lane of (V)CMPPS/(V)CMPSS. Returns (True/False, flags). imm in 0..31 (VEX/EVEX);
    legacy SSE CMPPS accepts only 0..7."""
    _, rel_true, sig = CMP_PREDICATES[imm & 31]
    rel, fl = relation(a, b, env, sig)
    return bool(rel & rel_true), fl


def comis(a, b, env, signalling):
    """(U)COMISS: returns ((ZF, PF, CF), flags). OF = SF = AF = 0.
    UCOMISS (signalling=False): IE only for SNaN. COMISS (signalling=True): IE for any NaN."""
    rel, fl = relation(a, b, env, signalling)
    zpc = {UN: (1, 1, 1), GT: (0, 0, 0), LT: (0, 0, 1), EQ: (1, 0, 0)}[rel]
    return zpc, fl


# ---------------------------------------------------------------- conversions

def cvt_i32_to_f32(i_bits, env):
    """CVTDQ2PS / CVTSI2SS (32-bit source). Rounds by RC; PE if inexact. Integer 0 -> +0.0.
    DAZ/FTZ are irrelevant (integer source; result never tiny)."""
    v = s32(i_bits)
    if v == 0:
        return 0, 0
    return round_f32(v < 0, Fraction(abs(v)), env.rc, False)


def cvt_f32_to_i32(b, env, truncate):
    """CVTPS2DQ (truncate=False: RC or {er}) / CVTTPS2DQ (truncate=True: toward zero).
    NaN, +-inf and results outside [-2^31, 2^31-1] give the integer indefinite 0x80000000 with IE
    (no PE). Exceptions listed by the SDM: Invalid, Precision -- DE is never raised.
    DAZ: a denormal source is treated as a zero (so RU of a positive denormal gives 0, not 1).
    UNCERTAIN on silicon: class F-DAZ-CVT."""
    if f32_is_nan(b) or f32_is_inf(b):
        return I32_INDEFINITE, IE
    if f32_is_denormal(b) and env.daz:
        b = b & F32_SIGN
    v = f32_value(b)
    rc = RC_RZ if truncate else env.rc
    n, inexact = round_to_integer(abs(v), rc, v < 0)
    val = -n if v < 0 else n
    if val < -(1 << 31) or val > (1 << 31) - 1:
        return I32_INDEFINITE, IE
    return u32(val), (PE if inexact else 0)


def cvt_f16_to_f32(h, env):
    """VCVTPH2PS lane. Exact. SNaN -> quieted with IE; payload shifted left by 13.
    SDM VCVTPH2PS: MXCSR.DAZ is ignored and no denormal exception is reported; Bochs
    (avx_cvt.cc, read 2026-10-16) forces DAZ off and suppresses DE accordingly."""
    sign = (h >> 15) & 1
    if f16_is_nan(h):
        frac = h & 0x3FF
        bits = (sign << 31) | 0x7F800000 | (frac << 13) | F32_QUIET
        return bits, (IE if f16_is_snan(h) else 0)
    if (h & 0x7FFF) == 0x7C00:
        return f32_signed_inf(sign), 0
    v = f16_value(h)
    if v == 0:
        return f32_signed_zero(sign), 0
    r, f = round_f32(v < 0, abs(v), RC_RZ, False)     # exact: any RC gives the same bits
    assert f == 0
    return r, 0
