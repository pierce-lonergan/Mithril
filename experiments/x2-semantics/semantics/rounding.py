"""Rounding an exact rational to binary32 (or to an integer) the way x86 SSE/AVX does.

Model (SDM Vol 1 §4.8.4, §4.9.1.4-5, §10.2.3.3), all exceptions masked:
  * Overflow: the result rounded with unbounded exponent exceeds the largest finite value.
    Result by RC: RNE -> +-inf; RZ -> +-MAX; RD -> +MAX / -inf; RU -> +inf / -MAX. Flags OE|PE.
  * Tininess is detected AFTER rounding: the value rounded to 24 significant bits with an
    unbounded exponent is nonzero and below 2^-126 (SDM Vol 1 §4.9.1.5 "result of rounding with
    unbounded exponent ... is non-zero and tiny"). Bochs' SoftFloat 3e (s_roundPackToF32.cc,
    read 2026-10-16) implements exactly this test. UNCERTAIN on Zen 5 silicon: fuzz class F-TINY.
  * FTZ=1 and tiny: result is a zero with the sign of the true result; flags UE|PE, whether or not
    the result was exact (Bochs does the same). UNCERTAIN for exact tiny results: class F-FTZ-EXACT.
  * FTZ=0 and tiny: the value is rounded to the subnormal grid (multiples of 2^-149) by RC; UE is
    raised only if that rounding is inexact (masked underflow), with PE.
  * Otherwise PE iff inexact.
Exact zero results are handled by the caller (their sign rule is operation specific).
"""
from fractions import Fraction

from .bits import F32_MAX, F32_NINF, F32_PINF, F32_SIGN
from .fpenv import OE, PE, RC_RD, RC_RNE, RC_RU, RC_RZ, UE

_HALF = Fraction(1, 2)


def round_to_integer(q, rc, negative):
    """Round a non-negative Fraction magnitude q to an integer magnitude.

    `negative` is the sign of the true value, needed for the directed modes.
    Returns (n, inexact).
    """
    assert q >= 0
    n = q.numerator // q.denominator
    r = q - n
    if r == 0:
        return n, False
    if rc == RC_RNE:
        if r > _HALF:
            n += 1
        elif r == _HALF:
            n += n & 1          # ties to even
    elif rc == RC_RZ:
        pass
    elif rc == RC_RD:           # toward -inf: magnitude grows for negatives
        if negative:
            n += 1
    elif rc == RC_RU:           # toward +inf: magnitude grows for positives
        if not negative:
            n += 1
    else:
        raise ValueError(rc)
    return n, True


def _floor_log2(mag):
    """Largest e with 2^e <= mag, for a positive Fraction."""
    e = mag.numerator.bit_length() - mag.denominator.bit_length()
    # 2^e <= mag < 2^(e+2) holds; adjust down/up by at most one.
    if _pow2(e) > mag:
        e -= 1
    elif _pow2(e + 1) <= mag:
        e += 1
    return e


def _pow2(e):
    return Fraction(1 << e) if e >= 0 else Fraction(1, 1 << (-e))


def overflow_result(negative, rc):
    if rc == RC_RNE:
        mag_inf = True
    elif rc == RC_RZ:
        mag_inf = False
    elif rc == RC_RD:
        mag_inf = negative
    else:  # RC_RU
        mag_inf = not negative
    if mag_inf:
        return F32_NINF if negative else F32_PINF
    return (F32_SIGN | F32_MAX) if negative else F32_MAX


def round_f32(negative, mag, rc, ftz):
    """Round a nonzero exact magnitude to binary32 under x86 rules. Returns (bits, flags)."""
    assert mag > 0
    sign_bit = F32_SIGN if negative else 0
    e = _floor_log2(mag)
    # Round to 24 significant bits with unbounded exponent.
    m, inexact = round_to_integer(mag / _pow2(e - 23), rc, negative)
    if m == (1 << 24):
        m, e = 1 << 23, e + 1
    if e > 127:
        return overflow_result(negative, rc), OE | PE
    if e < -126:                                   # tiny, detected after rounding
        if ftz:
            return sign_bit, UE | PE               # UNCERTAIN for exact tiny values (F-FTZ-EXACT)
        ms, inexact_sub = round_to_integer(mag * (1 << 149), rc, negative)
        # ms <= 2^23; ms == 2^23 encodes the smallest normal (exponent field 1), which is correct.
        return sign_bit | ms, (UE | PE) if inexact_sub else 0
    bits = sign_bit | ((e + 127) << 23) | (m - (1 << 23))
    return bits, PE if inexact else 0


def is_tiny_after_rounding(mag, rc, negative=False):
    """Exposed for fuzz-vector generation (class F-TINY)."""
    if mag == 0:
        return False
    e = _floor_log2(mag)
    m, _ = round_to_integer(mag / _pow2(e - 23), rc, negative)
    if m == (1 << 24):
        e += 1
    return e < -126


def is_tiny_before_rounding(mag):
    return 0 < mag < _pow2(-126)
