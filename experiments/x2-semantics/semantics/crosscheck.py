"""Optional cross-check of the exact-arithmetic core against the HOST's binary64 arithmetic.

Not evidence about x86 silicon: CPython float ops run as SSE2 double-precision instructions under the
process's MXCSR (round-to-nearest-even by default), and struct.pack('<f') converts double -> single
with one more RNE rounding. Rounding twice (binary64, then binary32) is innocuous for +, -, *, /
when the wide format has p' >= 2p + 2 significand bits (Figueroa 1995): 53 >= 2*24 + 2, so the
host path gives the correctly rounded binary32 result for every finite, non-overflowing case,
subnormal results included. NaN results are skipped (the host's NaN propagation is not x86 SSE's
single-precision rule in general, and NaN bits are the table's job). This checks the Fraction-based
rounding code, nothing else.

Run:  python -B -m semantics.crosscheck [n_per_op]
"""
import random
import struct
import sys

from . import fp_ops
from .bits import f32_is_nan
from .fpenv import DEFAULT


def f(b):
    return struct.unpack("<f", struct.pack("<I", b))[0]


def bits(x):
    try:
        return struct.unpack("<I", struct.pack("<f", x))[0]
    except OverflowError:
        return 0xFF800000 if x < 0 else 0x7F800000


def rand_bits(rng):
    k = rng.random()
    if k < 0.05:                     # subnormals
        return (rng.getrandbits(1) << 31) | rng.getrandbits(23)
    if k < 0.10:                     # near overflow
        return (rng.getrandbits(1) << 31) | (rng.randint(250, 254) << 23) | rng.getrandbits(23)
    if k < 0.15:                     # near underflow
        return (rng.getrandbits(1) << 31) | (rng.randint(1, 8) << 23) | rng.getrandbits(23)
    return (rng.getrandbits(1) << 31) | (rng.randint(100, 154) << 23) | rng.getrandbits(23)


def main(n=4000, seed=1):
    rng = random.Random(seed)
    ops = {"add": (fp_ops.add, lambda x, y: x + y), "sub": (fp_ops.sub, lambda x, y: x - y),
           "mul": (fp_ops.mul, lambda x, y: x * y), "div": (fp_ops.div, lambda x, y: x / y if y else None)}
    report = {}
    for name, (mine, host) in ops.items():
        agree = skipped = 0
        bad = []
        for _ in range(n):
            a, b = rand_bits(rng), rand_bits(rng)
            r, _ = mine(a, b, DEFAULT)
            h = host(f(a), f(b))
            if h is None or f32_is_nan(r) or h != h:
                skipped += 1
                continue
            hb = bits(h)
            if hb == r:
                agree += 1
            else:
                bad.append(("0x%08X" % a, "0x%08X" % b, "0x%08X" % r, "0x%08X" % hb))
        report[name] = {"agree": agree, "disagree": len(bad), "skipped": skipped, "examples": bad[:5]}
    return report


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    rep = main(n)
    for k, v in rep.items():
        print(k, v)
    sys.exit(sum(v["disagree"] for v in rep.values()))
