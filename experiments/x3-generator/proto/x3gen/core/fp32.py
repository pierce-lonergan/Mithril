"""IEEE binary32 emulation on the Python standard library (library L, test oracle).

DESIGN.md section 5.1 specifies rne_f32: struct.pack('<f', x) raises OverflowError at or above the
overflow midpoint and may alter NaN payloads, so both cases are handled explicitly. A product of two
binary32 values is exact in binary64; a sum is rounded twice (binary64, then binary32), which is
innocuous because 53 >= 2*24 + 2 [inference, DESIGN 5.1].
"""

import math
import struct

OVF_MID = 3.4028235677973366e38  # midpoint between FLT_MAX and 2**128; ties to even give inf
QNAN = 0x7FC00000


def bits_to_float(b: int) -> float:
    b &= 0xFFFFFFFF
    if (b & 0x7F800000) == 0x7F800000 and (b & 0x007FFFFF):
        return math.nan
    return struct.unpack("<f", struct.pack("<I", b))[0]


def rne_f32(x: float) -> int:
    """Round a binary64 value to binary32 (round to nearest, ties to even); return the bits."""
    if x != x:
        return QNAN
    if abs(x) >= OVF_MID:
        return 0xFF800000 if x < 0 else 0x7F800000
    return struct.unpack("<I", struct.pack("<f", x))[0]


def is_nan(b: int) -> bool:
    return (b & 0x7F800000) == 0x7F800000 and (b & 0x007FFFFF) != 0


def fadd(a: int, b: int) -> int:
    if is_nan(a) or is_nan(b):
        return QNAN
    return rne_f32(bits_to_float(a) + bits_to_float(b))


def fmul(a: int, b: int) -> int:
    if is_nan(a) or is_nan(b):
        return QNAN
    return rne_f32(bits_to_float(a) * bits_to_float(b))


def i2f(i: int) -> int:
    if abs(i) >= 1 << 24:
        raise ValueError("i2f outside the exact range")
    return rne_f32(float(i))


def h2f(h: int) -> int:
    """Exact IEEE binary16 -> binary32 (NaN-ness kept; payload quieted as F16C does)."""
    sign = (h & 0x8000) << 16
    e = (h >> 10) & 0x1F
    m = h & 0x3FF
    if e == 0x1F:
        return sign | 0x7F800000 | (m << 13) | (0x00400000 if m else 0)
    if e:
        return sign | ((e + 112) << 23) | (m << 13)
    if m == 0:
        return sign
    return sign | rne_f32(m * 2.0**-24)


def canon(b: int) -> int:
    return QNAN if is_nan(b) else b
