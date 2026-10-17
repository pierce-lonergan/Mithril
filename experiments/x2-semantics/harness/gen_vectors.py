"""Vector generator of the X2 fuzz harness (FUZZ-DESIGN.md §2-§5). Python, seeded, counter-based.

Every lane case is drawn from a SplitMix64 stream keyed by sha256(entry content hash | set | class |
environment | index), so any single case can be regenerated from its coordinates (FUZZ-DESIGN §3.1).
It writes vectors.bin (vecfmt.py) plus a sidecar JSON naming every class and environment id.

  python -I gen_vectors.py --sem-root DIR --manifest stubs_manifest.json --out VEC
         [--iform IFORM] [--set V1|V2|V3|V4|BCAST|F-MEMFAULT] [--class NAME] [--limit N]
         [--label BUDGET-...] [--dev --limit N --label DEV-...]
  python -I gen_vectors.py --sem-root DIR --manifest stubs_manifest.json --selftest

Rows come from semantics.census_absorb.budget_rows over the table (the frozen budget.v1.json replaces
this at freeze). Nothing here runs anything on silicon. Labels (revised 2026-10-16 after review): the
default is BUDGET-v1-<set>; a DEV label needs --dev, which also caps --limit. Every record keeps its
budget set id (V1..F-MEMFAULT), and x2fuzz refuses any budget-set record without --collection-authorised
whatever the label says, so a development slice of budget rows can be generated and timed but never
executed on silicon by accident.

Counting unit: a lane case (FUZZ-DESIGN §2). Each record (one execution) states how many lane cases it
carries; flag-isolation duplicates (single-active-lane executions) carry 0, so the totals equal the
budget rows. `plan()` gives every row's lane-case count from the same loop bounds the generator uses;
the self-test compares it with the row and reports every row whose formula the design does not let the
generator meet (see README.md "Open items found while building").
"""
import argparse
import hashlib
import json
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vecfmt  # noqa: E402

M64 = (1 << 64) - 1
E8 = [("default", 0x1F80), ("RD", 0x3F80), ("RU", 0x5F80), ("RZ", 0x7F80), ("DAZ", 0x1FC0), ("FTZ", 0x9F80),
      ("DAZ+FTZ", 0x9FC0), ("RD+FTZ", 0xBF80)]
V4ENVS = [("DAZ=FTZ=0", 0x1F80), ("DAZ=FTZ=1", 0x9FC0)]
ENV_NAMES = [n for n, _ in E8] + [n for n, _ in V4ENVS]
FLAG_BEARING = {"F-FLAGPRI", "F-TINY", "F-FTZ-EXACT", "F-DAZ-SEL", "F-DAZ-CVT", "F-H2F", "F-MASKEXC", "UFL", "OVF",
                "TIE", "CVT-BND", "CANCEL"}
F32_CLASSES = ["Z+", "Z-", "DEN+", "DEN-", "NORM+", "NORM-", "ONE", "BIG", "INF+", "INF-", "QNAN", "SNAN"]
# FUZZ-DESIGN §3.1 says "12 integer classes" but lists 10; the generator implements the 10 listed (open item).
INT_CLASSES = ["I:0", "I:+-1", "I:+-(2^24-1)", "I:+-2^24", "I:+-(2^24+1)", "I:2^31-1", "I:-2^31", "I:small",
               "I:large", "I:tie24"]
PAT = 0xA5A50000
# --dev slices (development measurements such as generator throughput) are capped at this many executions per
# row. Whatever the label, x2fuzz refuses records of the budget sets V1-V4, BCAST, F-MEMFAULT without
# --collection-authorised (review 2026-10-16), so a DEV label never lets budget rows run on silicon.
DEV_LIMIT_CAP = 100000


# ------------------------------------------------------------------ counter-based RNG
class Rng:
    __slots__ = ("s",)

    def __init__(self, key):
        self.s = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little")

    def next(self):
        self.s = (self.s + 0x9E3779B97F4A7C15) & M64
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return z ^ (z >> 31)

    def bits(self, n):
        return self.next() & ((1 << n) - 1)

    def range(self, lo, hi):            # inclusive
        return lo + self.next() % (hi - lo + 1)

    def choice(self, seq):
        return seq[self.next() % len(seq)]


def keyed(*parts):
    return Rng("|".join(str(p) for p in parts))


# ------------------------------------------------------------------ binary32 / binary16 helpers
def f32(sign, exp, frac):
    return ((sign & 1) << 31) | ((exp & 0xFF) << 23) | (frac & 0x7FFFFF)


def f32_from_mE(sign, M, E):
    """bits of +-M * 2^E when exactly representable (M > 0)."""
    while M >= (1 << 24):
        assert M & 1 == 0
        M >>= 1
        E += 1
    while M < (1 << 23) and E > -149:
        M <<= 1
        E -= 1
    if M < (1 << 23):                       # subnormal
        assert E == -149
        return (sign << 31) | M
    assert -149 <= E <= 104, E
    return (sign << 31) | ((E + 150) << 23) | (M - (1 << 23))


def val(b):
    s, e, f = b >> 31, (b >> 23) & 0xFF, b & 0x7FFFFF
    m = Fraction(f, 1 << 149) if e == 0 else Fraction((1 << 23) | f) * Fraction(2) ** (e - 150)
    return -m if s else m


def is_nan(b):
    return (b & 0x7F800000) == 0x7F800000 and (b & 0x7FFFFF) != 0


def is_den(b):
    return (b & 0x7F800000) == 0 and (b & 0x7FFFFF) != 0


def draw_f32(cls, rng, idx):
    s = rng.bits(1)
    if cls == "Z+":
        return 0
    if cls == "Z-":
        return 0x80000000
    if cls in ("DEN+", "DEN-"):
        sg = 0 if cls == "DEN+" else 1
        fr = {0: 1, 1: 0x7FFFFF}.get(idx) or rng.range(1, 0x7FFFFF)
        return f32(sg, 0, fr)
    if cls in ("NORM+", "NORM-"):
        return f32(0 if cls == "NORM+" else 1, rng.range(1, 254), rng.bits(23))
    if cls == "ONE":
        return f32(s, rng.range(120, 134), rng.bits(23))
    if cls == "BIG":
        return 0x7F7FFFFF if idx == 0 else f32(s, 254, rng.bits(23))
    if cls == "INF+":
        return 0x7F800000
    if cls == "INF-":
        return 0xFF800000
    if cls == "QNAN":
        pl = {0: 0, 1: 1, 2: 0x3FFFFF}.get(idx, rng.bits(22))
        return (s << 31) | 0x7FC00000 | pl
    if cls == "SNAN":
        pl = {0: 1, 1: 0x3FFFFF}.get(idx) or rng.range(1, 0x3FFFFF)
        return (s << 31) | 0x7F800000 | pl
    raise KeyError(cls)


def draw_f16(cls, rng, idx):
    s = rng.bits(1)
    if cls == "Z+":
        return 0
    if cls == "Z-":
        return 0x8000
    if cls in ("DEN+", "DEN-"):
        fr = {0: 1, 1: 0x3FF}.get(idx) or rng.range(1, 0x3FF)
        return ((0 if cls == "DEN+" else 1) << 15) | fr
    if cls in ("NORM+", "NORM-"):
        return ((0 if cls == "NORM+" else 1) << 15) | (rng.range(1, 30) << 10) | rng.bits(10)
    if cls == "ONE":
        return (s << 15) | (rng.range(12, 18) << 10) | rng.bits(10)
    if cls == "BIG":
        return 0x7BFF if idx == 0 else (s << 15) | (30 << 10) | rng.bits(10)
    if cls == "INF+":
        return 0x7C00
    if cls == "INF-":
        return 0xFC00
    if cls == "QNAN":
        pl = {0: 0, 1: 1, 2: 0x1FF}.get(idx, rng.bits(9))
        return (s << 15) | 0x7E00 | pl
    if cls == "SNAN":
        pl = {0: 1, 1: 0x1FF}.get(idx) or rng.range(1, 0x1FF)
        return (s << 15) | 0x7C00 | pl
    raise KeyError(cls)


def draw_int(cls, rng, idx):
    sg = -1 if rng.bits(1) else 1
    v = {"I:0": 0, "I:+-1": sg, "I:+-(2^24-1)": sg * ((1 << 24) - 1), "I:+-2^24": sg * (1 << 24),
         "I:+-(2^24+1)": sg * ((1 << 24) + 1), "I:2^31-1": (1 << 31) - 1, "I:-2^31": -(1 << 31)}.get(cls)
    if v is None:
        if cls == "I:small":
            v = sg * rng.range(0, (1 << 24) - 1)
        elif cls == "I:large":
            v = sg * rng.range(1 << 24, (1 << 31) - 1)
        elif cls == "I:tie24":            # odd 25-bit significand times 2^s: halfway between two floats
            sh = rng.range(0, 6)
            v = sg * (((1 << 24) | (rng.bits(23) << 1) | 1) << sh)
        else:
            raise KeyError(cls)
    return v & 0xFFFFFFFF


# ------------------------------------------------------------------ exact class predicates (self-test)
def exact(op, a, b):
    if op in ("add", "sub"):
        return val(a) + (val(b) if op == "add" else -val(b))
    if op == "mul":
        return val(a) * val(b)
    return val(a) / val(b)


def is_tie_rne(q):
    """Exact nonzero value q: is it exactly halfway between two binary32 neighbours (normal or subnormal grid)?"""
    m = abs(q)
    e = m.numerator.bit_length() - m.denominator.bit_length()
    if Fraction(2) ** e > m:
        e -= 1
    unit = Fraction(2) ** max(e - 23, -149)
    r = m / unit
    return r - (r.numerator // r.denominator) == Fraction(1, 2)


TWO128, T126 = Fraction(2) ** 128, Fraction(2) ** -126


# ------------------------------------------------------------------ targeted constructions (one lane case)
def finite_pair(rng):
    return draw_f32("ONE", rng, 9), draw_f32("ONE", rng, 9)


def c_tie(op, rng):
    for _ in range(64):
        if op in ("add", "sub"):
            ea = rng.range(2, 254)
            a = f32(rng.bits(1), ea, rng.bits(23))
            sgn = (a >> 31) ^ rng.bits(1)
            hb = f32_from_mE(sgn, 1, ea - 151)          # half an ulp of a
            b = hb if op == "add" else hb ^ 0x80000000
        elif op == "mul":
            # a tie needs the product's lowest set bit exactly at the first discarded position:
            # v2(Ma) + v2(Mb) = bitlen(Ma*Mb) - 25 (22 for a 47-bit product, 23 for a 48-bit one)
            sum_v = rng.range(22, 23)
            i = rng.range(max(0, sum_v - 23), min(23, sum_v))
            j = sum_v - i
            oa = (rng.bits(23 - i) | (1 << (23 - i))) | 1
            ob = (rng.bits(23 - j) | (1 << (23 - j))) | 1
            a = f32_from_mE(rng.bits(1), oa << i, rng.range(-60, 40))
            b = f32_from_mE(rng.bits(1), ob << j, rng.range(-60, 40))
        elif op == "div":                                   # ties exist only on the subnormal grid
            M = (1 << 23) | rng.bits(23) | 1
            E = rng.range(-140, -40)
            a = f32_from_mE(rng.bits(1), M, E)
            b = f32_from_mE(rng.bits(1), 1, E + 150)
        else:
            raise KeyError(op)
        if is_tie_rne(exact(op, a, b)):
            return a, b
    raise RuntimeError("tie construction failed")


def c_tie_f2i(rng):
    j = rng.range(0, (1 << 22) - 1)
    return f32_from_mE(rng.bits(1), 2 * j + 1, -1)                # (2j+1)/2


def c_ovf(op, rng):
    for _ in range(256):
        sg = rng.bits(1)
        if op in ("add", "sub"):
            a = f32_from_mE(sg, (1 << 24) - 1 - rng.range(0, 1), 104)
            b = f32_from_mE(sg, rng.range(1, 12), 102) if rng.range(0, 3) else 0
            if op == "sub":
                b ^= 0x80000000
        elif op == "mul":
            Ma = (1 << 23) | rng.bits(23)
            Mb = (((1 << 47) + Ma // 2) // Ma) + rng.range(-1, 1)
            if not ((1 << 23) <= Mb < (1 << 24)):
                continue
            ea = rng.range(1, 100)
            a = f32_from_mE(sg, Ma, ea)
            b = f32_from_mE(rng.bits(1), Mb, 128 - 47 - ea)
        else:
            Mb = (1 << 23) | rng.bits(23)
            Ma = Mb + rng.range(-1, 1)
            if not ((1 << 23) <= Ma < (1 << 24)):
                continue
            eb = rng.range(-100, -24)
            a = f32_from_mE(sg, Ma, eb + 128)                           # a / b ~ 2^128
            b = f32_from_mE(rng.bits(1), Mb, eb)
        x = exact(op, a, b)
        if abs(abs(x) - TWO128) <= Fraction(2) ** 105:
            return a, b
    raise RuntimeError("ovf construction failed")


def c_tiny(op, rng, idx):
    if op == "mul":
        if idx == 0:
            return 0x00800001, 0x3F7FFFFE
        for _ in range(64):
            Ma = (1 << 23) | rng.bits(23)
            Mb = ((1 << 47) - 1) // Ma
            if Ma * Mb >= (1 << 47) - (1 << 23) and (1 << 23) <= Mb < (1 << 24):
                ea = rng.range(-149, -24)
                return f32_from_mE(rng.bits(1), Ma, ea), f32_from_mE(rng.bits(1), Mb, -173 - ea)
        raise RuntimeError("tiny construction failed")
    # DIV: exact quotients cannot reach [2^-126 - 2^-150, 2^-126); the reachable band is
    # (1 - 1/q) * 2^-126, which rounds to 2^-126 under RU (positive) / RD (negative) only.
    q = rng.range((1 << 23) + 1, (1 << 24) - 1)
    eb = rng.range(-23, 104)
    sg = rng.bits(1)
    return f32_from_mE(sg, q - 1, eb - 126), f32_from_mE(0, q, eb)


def c_ufl(op, rng):
    for _ in range(64):
        if op in ("add", "sub"):
            a = f32(rng.bits(1), rng.range(0, 2), rng.bits(23))
            b = f32(rng.bits(1), rng.range(0, 2), rng.bits(23))
        elif op == "mul":
            F = rng.range(-196, -172)
            ea = rng.range(max(-149, F - 104), min(104, F + 149))
            Mb = 1 << 23 if rng.range(0, 3) == 0 else (1 << 23) | rng.bits(23)
            a = f32_from_mE(rng.bits(1), (1 << 23) | rng.bits(23), ea)
            b = f32_from_mE(rng.bits(1), Mb, F - ea)
        else:
            G = rng.range(-150, -126)
            eb = rng.range(-149 - G, 104)
            a = f32_from_mE(rng.bits(1), (1 << 23) | rng.bits(23), eb + G)
            b = f32_from_mE(rng.bits(1), (1 << 23) | rng.bits(23), eb)
        x = exact(op, a, b)
        if x != 0 and abs(x) < T126 * (1 + Fraction(1, 1 << 23)):
            return a, b
    raise RuntimeError("ufl construction failed")


def c_cancel(op, rng):
    """a + (-a) / a - a (exact zero), or a sum whose exact value is a nonzero subnormal: a is a normal in
    [2^-126, 2^-125), r a random subnormal of a's sign, b = r - a (|b| < 2^-125, so exactly representable)."""
    if rng.range(0, 1) == 0:
        a = f32(rng.bits(1), rng.range(1, 254), rng.bits(23))
        return a, (a ^ 0x80000000 if op == "add" else a)
    a = f32(rng.bits(1), 1, rng.bits(23))
    r = Fraction(rng.range(1, (1 << 23) - 1) * (-1 if a >> 31 else 1), 1 << 149)   # same sign as a: |b| < 2^-125
    bv = r - val(a) if op == "add" else val(a) - r
    m = abs(bv) * (1 << 149)
    assert m.denominator == 1
    return a, f32_from_mE(1 if bv < 0 else 0, m.numerator, -149)


def c_zeros(rng):
    z = [0, 0x80000000]
    k = rng.range(0, 3)
    if k < 2:
        return rng.choice(z), rng.choice(z)
    d = f32(rng.bits(1), 0, rng.range(1, 0x7FFFFF))
    return (rng.choice(z), d) if k == 2 else (d, rng.choice(z))


def c_ftz_exact(op, rng, idx):
    if idx == 0 and op == "mul":
        return 0x00800000, 0x3F000000                                # 2^-126 * 0.5
    s = rng.range(1, (1 << 23) - 1)
    r = f32_from_mE(rng.bits(1), s, -149)                            # exact subnormal result
    if op in ("add", "sub"):
        s2 = rng.range(0, s)
        a = f32_from_mE(r >> 31, s - s2, -149) if s - s2 else (r & 0x80000000)
        b = f32_from_mE(r >> 31, s2, -149) if s2 else (r & 0x80000000)
        return a, (b if op == "add" else b ^ 0x80000000)
    m = rng.range(30, 120)
    a = f32_from_mE(r >> 31, s, -149 + m)
    b = f32_from_mE(0, 1, -m) if op == "mul" else f32_from_mE(0, 1, m)
    return a, b


def c_flagpri(op, rng):
    den = f32(rng.bits(1), 0, rng.range(1, 0x7FFFFF))
    nan = draw_f32(rng.choice(["QNAN", "SNAN"]), rng, 9)
    snan = draw_f32("SNAN", rng, 9)
    big = draw_f32("BIG", rng, 9)
    inf = rng.choice([0x7F800000, 0xFF800000])
    zero = rng.choice([0, 0x80000000])
    opts = [(nan, den), (den, nan), (snan, big), (big, snan)]
    if op == "div":
        opts += [(den, zero), (den, den)]
    if op == "mul":
        opts += [(den, inf), (inf, den)]
    if op in ("add", "sub", "max", "min", "cmp"):
        opts += [(den, inf), (inf, den)]
    return rng.choice(opts)


def c_cvt_bnd_f2i(rng):
    k = rng.range(0, 9)
    if k == 0:
        return rng.choice([0x4F000000, 0xCF000000])                  # +-2^31
    if k == 1:
        return rng.choice([0x4EFFFFFF, 0xCEFFFFFF])                  # +-(2^31 - 128)
    if k == 2:
        return 0xCF000001                                            # -(2^31 + 256)
    if k == 3:
        j = rng.range(-8, 8)
        v = (1 << 24) + (2 * j if j > 0 else j)
        return f32_from_mE(rng.bits(1), v, 0)                        # +-2^24 +- k
    if k == 4:
        return f32_from_mE(rng.bits(1), rng.choice([1, 3, 5]), -1)   # +-0.5, +-1.5, +-2.5
    if k == 5:
        return f32(1, rng.range(1, 126), rng.bits(23))               # in (-1, 0)
    if k == 6:
        return f32(rng.bits(1), 0, rng.range(1, 0x7FFFFF))           # DEN (DAZ on DEN)
    if k == 7:
        return f32(rng.bits(1), rng.range(157, 160), rng.bits(23))   # around +-2^31
    if k == 8:
        return c_tie_f2i(rng)
    return f32(rng.bits(1), 126, rng.bits(23))                       # [0.5, 1)


def c_cvt_bnd_i2f(rng):
    k = rng.range(0, 5)
    sg = -1 if rng.bits(1) else 1
    if k == 0:
        v = sg * ((1 << 24) + rng.range(-8, 8))
    elif k == 1:
        v = rng.choice([(1 << 31) - 1, -(1 << 31), (1 << 31) - 64, -(1 << 31) + 64, (1 << 31) - 128, -(1 << 31) + 128])
    elif k == 2:
        sh = rng.range(1, 7)
        v = sg * ((((1 << 24) | rng.bits(24)) << sh) & 0x7FFFFFFF)
    elif k == 3:
        v = sg * (((1 << 24) | (rng.bits(23) << 1) | 1) << rng.range(0, 6))   # ties
    elif k == 4:
        v = sg * rng.range(0, 3)
    else:
        v = sg * ((1 << 25) + rng.range(-4, 4))
    return v & 0xFFFFFFFF


def c_h2f(rng, idx):
    """F-H2F: every f16 subnormal (both signs), then every f16 SNaN, then random from both."""
    if idx < 2046:
        return ((idx // 1023) << 15) | (idx % 1023 + 1)
    j = idx - 2046
    if j < 1022:
        return ((j // 511) << 15) | 0x7C00 | (j % 511 + 1)
    return rng.choice([lambda: (rng.bits(1) << 15) | rng.range(1, 0x3FF),
                       lambda: (rng.bits(1) << 15) | 0x7C00 | rng.range(1, 0x1FF)])()


# ------------------------------------------------------------------ fillers (flag-neutral in every E8 env)
ONE_, TWO_ = 0x3F800000, 0x40000000
FILL = {"FP.ADD.f32": (ONE_, ONE_), "FP.SUB.f32": (ONE_, ONE_), "FP.MUL.f32": (ONE_, ONE_), "FP.DIV.f32": (ONE_, ONE_),
        "FP.MAX.f32": (ONE_, TWO_), "FP.MIN.f32": (ONE_, TWO_), "FP.CMP.f32": (ONE_, TWO_), "FP.COMI.f32": (ONE_, TWO_),
        "FP.CVT.f32_i32.rc": (ONE_, 0), "FP.CVT.f32_i32.trunc": (ONE_, 0), "FP.CVT.i32_f32": (1, 0),
        "FP.CVT.f16_f32": (0x3C00, 0)}
OPNAME = {"FP.ADD.f32": "add", "FP.SUB.f32": "sub", "FP.MUL.f32": "mul", "FP.DIV.f32": "div", "FP.MAX.f32": "max",
          "FP.MIN.f32": "min", "FP.CMP.f32": "cmp", "FP.COMI.f32": "cmp"}


def b_any(lanes):
    return any(b is not None for _, b in lanes)


# ------------------------------------------------------------------ the generator
class Gen:
    def __init__(self, sem_root, manifest_path):
        sys.path.insert(0, sem_root)
        from semantics import census_absorb, table  # noqa: E402
        self.table, self.census_absorb = table, census_absorb
        with open(manifest_path, "rb") as f:
            raw = f.read()
        self.manifest_sha = hashlib.sha256(raw).hexdigest()
        self.man = json.loads(raw)
        self.by_entry = {}
        for s in self.man["stubs"]:
            self.by_entry.setdefault(s["entry_index"], {})[s["variant"]] = s
        self.idx_of = {e["key"]["iform"]: i for i, e in enumerate(table.ENTRIES)}
        self.classes = []
        self.class_id = {}
        with open(os.path.abspath(__file__), "rb") as f:
            self.gen_sha = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()

    def cid(self, name):
        if name not in self.class_id:
            self.class_id[name] = len(self.classes)
            self.classes.append(name)
        return self.class_id[name]

    # -- case assembly
    def assemble(self, e, stub, lanes, mxcsr, k=0, extra=None):
        """lanes: list of (a, b) per lane (b may be None for unary). Returns a Case with every operand in
        the register its ROLE names (legacy dst_src1 -> dst_old; GPR sources -> gpr_in)."""
        roles = {o["role"]: o for o in e["operands"]}
        fam = e["family"]
        n = len(lanes)
        eb = e["sem"].get("src_eb", 32) if e["sem"]["builder"] == "packed_fp1" else 32
        dst_old = vecfmt.b2i(b"".join((PAT + i).to_bytes(4, "little") for i in range(16)))
        c = vecfmt.Case(mxcsr=mxcsr, k=k, rflags_in=0x202 | 0x8D5, gpr_in=0xDEADBEEFDEADBEEF, kdst_in=M64,
                        dst_old=dst_old)
        src1 = src2 = 0
        for i, (a, b) in enumerate(lanes):
            src1 |= (a & ((1 << eb) - 1)) << (eb * i)
            if b is not None:
                src2 |= (b & 0xFFFFFFFF) << (32 * i)
        if fam == "FP.CVT.i32_f32" and e["sem"]["builder"] == "cvt_i2f_scalar":
            c.gpr_in = 0xDEADBEEF00000000 | (lanes[0][0] & 0xFFFFFFFF)
            src1 = vecfmt.b2i(b"".join((0x3C3C0000 + i).to_bytes(4, "little") for i in range(16)))
        if "dst_src1" in roles and e["sem"]["builder"] == "scalar_fp2":
            c.dst_old = (dst_old & ~0xFFFFFFFF) | (src1 & 0xFFFFFFFF)
            src1 = dst_old
        else:
            if n < 16 and e["sem"]["builder"] != "cvt_i2f_scalar":     # upper source lanes: a recognisable pattern
                for i in range(n, 16 if eb == 32 else 32):
                    src1 |= ((0x3C3C0000 + i) & ((1 << eb) - 1)) << (eb * i)
        if b_any(lanes):                                         # upper src2 lanes: a second recognisable pattern
            for i in range(n, 16):
                src2 |= (0x3D3D0000 + i) << (32 * i)
        c.src1, c.src2 = src1, src2
        if extra:
            extra(c)
        return c

    def lanes_of(self, e):
        return 1 if e["scalar"] is not None or e["sem"]["builder"] in ("comis", "cvt_f2i_gpr") else e["lanes"]

    # -- row handlers: each returns (planned lane cases, iterator of (meta, Case))
    def row(self, r, limit=None):
        ei = self.idx_of[r["iform"]]
        e = self.table.ENTRIES[ei]
        fam, st = e["family"], self.by_entry[ei]
        if r["set"] == "V5":
            return 0, iter(())
        if fam.startswith("INT."):
            return self.int_rows(r, e, ei, st, limit)
        if r["set"] == "V1":
            return self.v1(r, e, st, limit)
        if r["set"] == "V2":
            return self.v2(r, e, st, limit)
        if r["set"] == "V3":
            return self.v3(r, e, st, limit)
        if r["set"] == "V4":
            return self.v4(r, e, st, limit)
        if r["set"] == "BCAST":
            if str(r.get("class", "")).startswith("masked"):
                return self.bcast_masked(r, e, st, limit)
            return self.bcast(r, e, st, limit)
        if r["set"] == "F-MEMFAULT":
            return self.memfault(r, e, st, limit)
        raise KeyError(r["set"])

    def stubs_for(self, e, st, kind):
        """plain stubs (one per predicate for compares) of an entry."""
        if any(o["role"] == "imm" for o in e["operands"]):
            n = 32 if e["encoding"] != "legacy" else 8
            return [st["plain_imm%02X" % i] for i in range(n)]
        return [st[kind]]

    def source_kind(self, e):
        fam = e["family"]
        if fam == "FP.CVT.f16_f32":
            return "f16"
        if fam == "FP.CVT.i32_f32":
            return "int"
        return "f32"

    def draw_src(self, kind, cls, rng, idx):
        return {"f32": draw_f32, "f16": draw_f16, "int": draw_int}[kind](cls, rng, idx)

    def pack_exec(self, e, stub, set_name, cname, env_i, lane_cases, idx0, mxcsr, k=0, flags=0, lane=0xFFFFFFFF,
                  counted=None, extra=None):
        meta = {"stub": stub["id"], "flags": flags, "set": vecfmt.SETS[set_name], "class": self.cid(cname),
                "env": env_i, "lane": lane, "n_lane_cases": len(lane_cases) if counted is None else counted,
                "index": idx0}
        return meta, self.assemble(e, stub, lane_cases, mxcsr, k=k, extra=extra)

    def v1(self, r, e, st, limit):
        fam, n = e["family"], self.lanes_of(e)
        kind = self.source_kind(e)
        ch = self.table.content_hash(e)
        stubs = self.stubs_for(e, st, "plain")
        unary = e["sem"]["builder"] in ("packed_fp1", "cvt_f2i_gpr", "cvt_i2f_scalar")
        cells = [(c,) for c in (INT_CLASSES if kind == "int" else F32_CLASSES)] if unary else \
            [(c1, c2) for c1 in F32_CLASSES for c2 in F32_CLASSES]
        per = 1000
        plan = len(stubs) * len(E8) * len(cells) * per

        def it():
            emitted = 0
            for stub in stubs:
                for env_i, (env_n, mx) in enumerate(E8):
                    for cell in cells:
                        cname = "x".join(cell)
                        buf, start = [], 0
                        for idx in range(per):
                            rng = keyed(ch, "V1", stub["variant"], cname, env_n, idx)
                            a = self.draw_src(kind, cell[0], rng, idx)
                            b = None if unary else draw_f32(cell[1], rng, idx)
                            buf.append((a, b))
                            if len(buf) == n or idx == per - 1:
                                yield self.pack_exec(e, stub, "V1", cname, env_i, buf, start, mx)
                                emitted += 1
                                if limit and emitted >= limit:
                                    return
                                buf, start = [], idx + 1
        return plan, it()

    def v2_case(self, fam, cname, rng, idx):
        op = OPNAME.get(fam)
        if fam == "FP.CVT.i32_f32":
            return (c_cvt_bnd_i2f(rng), None)
        if fam.startswith("FP.CVT.f32_i32"):
            if cname == "CVT-BND":
                return (c_cvt_bnd_f2i(rng), None)
            return (f32(rng.bits(1), 0, rng.range(1, 0x7FFFFF)), None)              # F-DAZ-CVT: DEN+-
        if fam == "FP.CVT.f16_f32":
            return (c_h2f(rng, idx), None)
        if cname == "TIE":
            return c_tie(op, rng)
        if cname == "OVF":
            return c_ovf(op, rng)
        if cname == "F-TINY":
            return c_tiny(op, rng, idx)
        if cname == "UFL":
            return c_ufl(op, rng)
        if cname == "CANCEL":
            return c_cancel(op, rng)
        if cname == "ZEROS":
            return c_zeros(rng)
        if cname == "F-FTZ-EXACT":
            return c_ftz_exact(op, rng, idx)
        if cname == "F-FLAGPRI":
            return c_flagpri(op, rng)
        if cname == "F-DAZ-SEL":
            d = f32(rng.bits(1), 0, rng.range(1, 0x7FFFFF))
            o = draw_f32(rng.choice(F32_CLASSES), rng, 9)
            return (d, o) if rng.bits(1) else (o, d)
        raise KeyError((fam, cname))

    def isolated(self, e, st, stub, set_name, cname, env_i, mx, case, idx, n):
        """FUZZ-DESIGN §2 flag isolation: the case in lane idx mod n with flag-neutral fillers; for EVEX forms
        also a single-active-lane execution through the write mask (merge), counted 0 lane cases."""
        fam = e["family"]
        fa, fb = FILL[fam]
        unary = case[1] is None
        lane = idx % n
        lanes = [case if i == lane else (fa, None if unary else fb) for i in range(n)]
        out = [self.pack_exec(e, stub, set_name, cname, env_i, lanes, idx, mx, flags=vecfmt.FLAG_FILLERS, lane=lane,
                              counted=1)]
        if e["encoding"] == "evex" and n > 1:
            mvar = stub["variant"].replace("plain", "merge")
            if mvar in st:
                out.append(self.pack_exec(e, st[mvar], set_name, cname, env_i, lanes, idx, mx, k=1 << lane,
                                          flags=vecfmt.FLAG_SINGLE_LANE, lane=lane, counted=0))
        return out

    def v2(self, r, e, st, limit):
        fam, n = e["family"], self.lanes_of(e)
        ch = self.table.content_hash(e)
        cname = r["class"]
        stubs = self.stubs_for(e, st, "plain")
        per = 10000
        plan = len(stubs) * len(E8) * per

        def it():
            emitted = 0
            for stub in stubs:
                for env_i, (env_n, mx) in enumerate(E8):
                    buf, start = [], 0
                    for idx in range(per):
                        rng = keyed(ch, "V2", stub["variant"], cname, env_n, idx)
                        case = self.v2_case(fam, cname, rng, idx)
                        if cname in FLAG_BEARING:
                            for rec in self.isolated(e, st, stub, "V2", cname, env_i, mx, case, idx, n):
                                yield rec
                                emitted += 1
                        else:
                            buf.append(case)
                            if len(buf) == n or idx == per - 1:
                                yield self.pack_exec(e, stub, "V2", cname, env_i, buf, start, mx)
                                emitted += 1
                                buf, start = [], idx + 1
                        if limit and emitted >= limit:
                            return
        return plan, it()

    def hetero(self, e, rng):
        """The fixed heterogeneous lane vector of V3: one SNaN, one QNaN, one DEN, one overflow-producing
        value, one tie, ordinary values (FUZZ-DESIGN §3.4)."""
        fam = e["family"]
        op = OPNAME.get(fam)
        n = max(self.lanes_of(e), 4)
        if fam.startswith("FP.CVT.f32_i32"):
            sp = [(0x7F800001, None), (0xFFC00000, None), (0x00000001, None), (0x4F000000, None), (0x40200000, None)]
        elif fam == "FP.CVT.i32_f32":
            sp = [((1 << 31) - 1, None), ((-(1 << 31)) & 0xFFFFFFFF, None), (16777217, None), (16777219, None), (3, None)]
        elif fam == "FP.CVT.f16_f32":
            sp = [(0x7C01, None), (0xFE55, None), (0x0001, None), (0x7BFF, None), (0x3555, None)]
        else:
            ovf = {"add": (0x7F7FFFFF, 0x7F7FFFFF), "sub": (0x7F7FFFFF, 0xFF7FFFFF), "mul": (0x7F7FFFFF, 0x40000000),
                   "div": (0x7F7FFFFF, 0x3F000000)}.get(op, (0x7F7FFFFF, 0x7F7FFFFF))
            tie = {"add": (ONE_, 0x33800000), "sub": (ONE_, 0xB3800000)}.get(op) or (c_tie(op, rng) if op in ("mul", "div") else (ONE_, ONE_))
            sp = [(0x7F800001, ONE_), (ONE_, 0x7FC00001), (0x00000001, ONE_), ovf, tie]
        kind = self.source_kind(e)
        ordinary = [((draw_f32("ONE", rng, 9) if kind == "f32" else (draw_f16("ONE", rng, 9) if kind == "f16" else rng.bits(20))),
                     None if sp[0][1] is None else draw_f32("ONE", rng, 9)) for _ in range(max(0, n - len(sp)))]
        return (sp + ordinary)[:n] if n >= len(sp) else sp

    def v3(self, r, e, st, limit):
        n = self.lanes_of(e)
        ch = self.table.content_hash(e)
        zero_only = e["masking"] == ["zero(k-dest)"]
        modes = ["merge"] if zero_only else ["merge", "zero"]   # compare into k: the merge stub is zeroing by definition
        base = self.hetero(e, keyed(ch, "V3", "vector"))
        if n == 1:
            masks = [0, 1]
            rot_lanes = [[base[r_]] for r_ in range(4)]
            plan = len(masks) * len(modes) * 4
        else:
            masks = list(range(1 << n))
            rot_lanes = [base[r_:] + base[:r_] for r_ in range(4)]
            plan = len(masks) * len(modes) * 4 * n
        imm_stubs = any(o["role"] == "imm" for o in e["operands"])

        def it():
            emitted = 0
            for mode in modes:
                stub = st["%s_imm03" % mode] if imm_stubs else st[mode]
                for rot in range(4):
                    lanes = rot_lanes[rot][:n]
                    for m in masks:
                        yield self.pack_exec(e, stub, "V3", "masks/%s/rot%d" % (mode, rot), 0, lanes, m, 0x1F80, k=m)
                        emitted += 1
                        if limit and emitted >= limit:
                            return
        return plan, it()

    def v4(self, r, e, st, limit):
        n = self.lanes_of(e)
        kind = self.source_kind(e)
        ch = self.table.content_hash(e)
        unary = e["sem"]["builder"] in ("packed_fp1", "cvt_f2i_gpr", "cvt_i2f_scalar")
        cells = [(c,) for c in (INT_CLASSES if kind == "int" else F32_CLASSES)] if unary else \
            [(c1, c2) for c1 in F32_CLASSES for c2 in F32_CLASSES]
        per = 100
        plan = 4 * len(V4ENVS) * len(cells) * per

        def it():
            emitted = 0
            for mode in range(4):
                stub = st["plain_er%d" % mode]
                for env_j, (env_n, mx) in enumerate(V4ENVS):
                    for cell in cells:
                        cname = "er%d/%s" % (mode, "x".join(cell))
                        buf, start = [], 0
                        for idx in range(per):
                            rng = keyed(ch, "V4", mode, cname, env_n, idx)
                            buf.append((self.draw_src(kind, cell[0], rng, idx), None if unary else draw_f32(cell[1], rng, idx)))
                            if len(buf) == n or idx == per - 1:
                                yield self.pack_exec(e, stub, "V4", cname, len(E8) + env_j, buf, start, mx)
                                emitted += 1
                                if limit and emitted >= limit:
                                    return
                                buf, start = [], idx + 1
        return plan, it()

    def bcast(self, r, e, st, limit):
        n = self.lanes_of(e)
        ch = self.table.content_hash(e)
        stub = st["plain_bcast"]
        per = 100
        plan = 144 * per * n

        def it():
            emitted = 0
            for c1 in F32_CLASSES:
                for c2 in F32_CLASSES:
                    cname = "%sx%s{1to%d}" % (c1, c2, n)
                    for idx in range(per):
                        rng = keyed(ch, "BCAST", cname, idx)
                        bval = draw_f32(c2, rng, idx)
                        lanes = [(draw_f32(c1, rng, idx if i == 0 else 9), bval) for i in range(n)]
                        meta, c = self.pack_exec(e, stub, "BCAST", cname, 0, lanes, idx, 0x1F80)
                        c.src2 = bval                                       # only the broadcast element is in memory
                        yield meta, c
                        emitted += 1
                        if limit and emitted >= limit:
                            return
        return plan, it()

    def memfault(self, r, e, st, limit):
        """F-MEMFAULT, LOAD SIDE ONLY (review 2026-10-16): the in-scope table entries with a memory operand are
        loads folded into arithmetic (VADDPS/VMULPS zmm m512); no stub writes memory, so the store half of
        FUZZ-DESIGN §3.2 F-MEMFAULT needs the memory-window ABI extension (README §4) before the census adds
        masked moves or stores. EVEX forms run every prefix mask with merge masking (the budget row's
        (n + 1) x n lane cases) and again with zero masking; the zero-masking executions are uncounted
        duplicates (n_lane_cases = 0), as the flag-isolation duplicates are, so the row total is unchanged."""
        n = self.lanes_of(e)
        ch = self.table.content_hash(e)
        if e["encoding"] == "evex":
            modes, bounds = ["merge"] + (["zero"] if "zero" in st else []), list(range(n + 1))
        else:
            modes, bounds = ["plain"], [n]
        plan = len(bounds) * n

        def it():
            for b in bounds:
                rng = keyed(ch, "F-MEMFAULT", b)
                lanes = [(draw_f32("ONE", rng, 9), draw_f32("ONE", rng, 9)) for _ in range(n)]
                for mi, mode in enumerate(modes):
                    meta, c = self.pack_exec(e, st[mode], "F-MEMFAULT", "prefix%d" % b if mi == 0 else "prefix%d/zero" % b,
                                             0, lanes, b, 0x1F80, k=(1 << b) - 1 if e["encoding"] == "evex" else 0,
                                             flags=vecfmt.FLAG_MEMFAULT, counted=None if mi == 0 else 0)
                    meta["mf_boundary"] = b
                    yield meta, c
        return plan, it()

    def bcast_masked(self, r, e, st, limit):
        """Masked broadcast (merge_bcast and zero_bcast stubs; review 2026-10-16 found them generated but run by no
        budget row). Reached only through a BCAST row whose class starts with "masked"; budget_rows emits no such
        row today (proposed for the record, README §6 open item 8): per masking mode, the class-pair grid x 10
        draws, each execution with its own random write mask, so 144 x 10 x n lane cases per mode."""
        n = self.lanes_of(e)
        ch = self.table.content_hash(e)
        modes = [m for m in ("merge_bcast", "zero_bcast") if m in st]
        per = 10
        plan = len(modes) * 144 * per * n

        def it():
            emitted = 0
            for mode in modes:
                for c1 in F32_CLASSES:
                    for c2 in F32_CLASSES:
                        cname = "%s/%sx%s{1to%d}" % (mode, c1, c2, n)
                        for idx in range(per):
                            rng = keyed(ch, "BCAST-masked", mode, cname, idx)
                            bval = draw_f32(c2, rng, idx)
                            lanes = [(draw_f32(c1, rng, idx if i == 0 else 9), bval) for i in range(n)]
                            k = rng.bits(n)
                            meta, c = self.pack_exec(e, st[mode], "BCAST", cname, 0, lanes, idx, 0x1F80, k=k)
                            c.src2 = bval
                            yield meta, c
                            emitted += 1
                            if limit and emitted >= limit:
                                return
        return plan, it()

    # -- integer entries (FUZZ-DESIGN §3.5; default environment)
    def int_rows(self, r, e, ei, st, limit):
        fam, vl = e["family"], e["vl"]
        ch = self.table.content_hash(e)
        n = e["lanes"]
        if r["set"] in ("V3",):
            return self.v3_int(r, e, st, limit)
        per_total = 100000 if r["set"] == "V1" else 10000
        classes = INT_FAMILY_CLASSES[fam][r["set"]]
        plan = per_total

        def it():
            emitted = 0
            stub = st["plain"]
            per = [per_total // len(classes) + (1 if i < per_total % len(classes) else 0) for i in range(len(classes))]
            for ci, cname in enumerate(classes):
                for start in range(0, per[ci], n):
                    m = min(n, per[ci] - start)
                    rng = keyed(ch, r["set"], cname, start)
                    a, b, acc = int_case(fam, cname, rng, vl, m)
                    meta = {"stub": stub["id"], "flags": 0, "set": vecfmt.SETS[r["set"]], "class": self.cid(cname),
                            "env": 0, "lane": 0xFFFFFFFF, "n_lane_cases": m, "index": start}
                    c = vecfmt.Case(mxcsr=0x1F80, k=0, rflags_in=0x202, gpr_in=0, kdst_in=M64,
                                    src1=a, src2=b, dst_old=acc)
                    yield meta, c
                    emitted += 1
                    if limit and emitted >= limit:
                        return
        return plan, it()

    def v3_int(self, r, e, st, limit):
        fam, vl, n = e["family"], e["vl"], e["lanes"]
        ch = self.table.content_hash(e)
        rng = keyed(ch, "V3", "vector")
        a, b, acc = int_case(fam, "random", rng, vl, n)
        if n <= 16:
            masks = list(range(1 << n))
        else:
            full = (1 << n) - 1
            alt = [int(("01" * 32)[:n][::-1], 2), int(("10" * 32)[:n][::-1], 2), int(("0011" * 16)[:n][::-1], 2),
                   int(("1100" * 16)[:n][::-1], 2)]
            mrng = keyed(ch, "V3", "masks")
            masks = ([0, full] + [1 << i for i in range(n)] + [full ^ (1 << i) for i in range(n)] + alt
                     + [(1 << i) - 1 for i in range(1, n + 1)] + [mrng.bits(n) for _ in range(4096)])
        plan = len(masks) * 2 * 4 * n
        eb = e["sem"]["dst_eb"]

        def rot(v, r_):
            return ((v >> (eb * r_)) | (v << (vl - eb * r_))) & ((1 << vl) - 1) if r_ else v

        def it():
            emitted = 0
            for mode in ("merge", "zero"):
                stub = st[mode]
                for r_ in range(4):
                    for m in masks:
                        meta = {"stub": stub["id"], "flags": 0, "set": vecfmt.SETS["V3"],
                                "class": self.cid("masks/%s/rot%d" % (mode, r_)), "env": 0, "lane": 0xFFFFFFFF,
                                "n_lane_cases": n, "index": m}
                        yield meta, vecfmt.Case(mxcsr=0x1F80, k=m, rflags_in=0x202, kdst_in=M64,
                                                src1=rot(a, r_), src2=rot(b, r_), dst_old=acc)
                        emitted += 1
                        if limit and emitted >= limit:
                            return
        return plan, it()


INT_FAMILY_CLASSES = {
    "INT.MADDUBS.u8s8": {"V1": ["random", "u255", "s-extremes", "zeros", "act-range"],
                         "V2": ["saturate+", "saturate-", "near-saturation"]},
    "INT.MADDWD.s16": {"V1": ["wordgrid", "random"], "V2": ["all-0x8000", "near-wrap"]},
    "INT.DPBUSD.u8s8": {"V1": ["bytegrid", "random"], "V2": ["wrap+", "wrap-"]},
    "INT.HADDD": {"V1": ["dwordgrid", "random"], "V2": ["wrap-in-lane", "wrap-across"]},
}


def int_case(fam, cname, rng, vl, m):
    """(src1, src2, dst_old/acc) for m output lanes of an integer entry; other lanes random."""
    nb = vl // 8
    A, B = [rng.bits(8) for _ in range(nb)], [rng.bits(8) for _ in range(nb)]
    acc = [rng.bits(32) for _ in range(vl // 32)]
    if fam == "INT.MADDUBS.u8s8":
        for i in range(2 * m):
            if cname == "u255":
                A[i] = 255
            elif cname == "s-extremes":
                B[i] = rng.choice([0x7F, 0x80, 0x81, 0xFF])
            elif cname == "zeros":
                A[i] = 0 if rng.bits(1) else A[i]
                B[i] = 0 if rng.bits(1) else B[i]
            elif cname == "act-range":
                A[i] = rng.range(0, 15)
                B[i] = rng.range(-127, 127) & 0xFF
            elif cname == "saturate+":
                A[i], B[i] = rng.range(200, 255), rng.range(100, 127)
            elif cname == "saturate-":
                A[i], B[i] = rng.range(200, 255), rng.range(128, 160)
            elif cname == "near-saturation":
                A[i], B[i] = 255, rng.choice([64, 65, 0xC0, 0xBF])
    elif fam == "INT.MADDWD.s16":
        W = [0, 1, 0xFFFF, 0x7FFF, 0x8000]
        for i in range(2 * m):
            for arr in (A, B):
                if cname == "wordgrid":
                    w = rng.choice(W) if rng.range(0, 3) else rng.bits(16)
                elif cname == "all-0x8000":
                    w = 0x8000
                elif cname == "near-wrap":
                    w = rng.choice([0x8000, 0x8001, 0x7FFF])
                else:
                    continue
                arr[2 * i], arr[2 * i + 1] = w & 0xFF, w >> 8
    elif fam == "INT.DPBUSD.u8s8":
        for i in range(4 * m):
            if cname == "bytegrid":
                A[i] = rng.choice([0, 1, 0x7F, 0x80, 0xFF, rng.bits(8)])
                B[i] = rng.choice([0, 1, 0x7F, 0x80, 0xFF, rng.bits(8)])
            elif cname == "wrap+":
                A[i], B[i] = 255, 127
            elif cname == "wrap-":
                A[i], B[i] = 255, 0x80
        for i in range(m):
            if cname == "bytegrid":
                acc[i] = rng.choice([0, 1, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, rng.bits(32)])
            elif cname == "wrap+":
                acc[i] = 0x7FFFFFFF - rng.range(0, 200000)
            elif cname == "wrap-":
                acc[i] = 0x80000000 + rng.range(0, 200000)
    elif fam == "INT.HADDD":
        D = [0, 1, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000]
        for arr in (A, B):
            for i in range(vl // 32):
                if cname == "dwordgrid":
                    v = rng.choice(D) if rng.range(0, 2) else rng.bits(32)
                elif cname == "wrap-in-lane":
                    v = rng.choice([0x7FFFFFFF, 0x7FFFFFFE, 0x80000000, 0x80000001])
                elif cname == "wrap-across":
                    v = 0x7FFFFFFF if (i % 4) < 2 else 0x80000000
                else:
                    continue
                for j in range(4):
                    arr[4 * i + j] = (v >> (8 * j)) & 0xFF
    return (vecfmt.b2i(bytes(A)), vecfmt.b2i(bytes(B)), vecfmt.b2i(b"".join(x.to_bytes(4, "little") for x in acc)))


# ------------------------------------------------------------------ CLI
def all_rows(g):
    return g.census_absorb.budget_rows(g.table.ENTRIES)


def selftest(g):
    """Generator self-test (no silicon, no harness run). Returns (failures, report)."""
    from semantics import fp_ops, fpenv
    fails, rep = [], {}
    pred = {"Z+": lambda b: b == 0, "Z-": lambda b: b == 0x80000000, "DEN+": lambda b: is_den(b) and b >> 31 == 0,
            "DEN-": lambda b: is_den(b) and b >> 31 == 1,
            "NORM+": lambda b: 0 < (b >> 23) & 0xFF < 255 and b >> 31 == 0,
            "NORM-": lambda b: 0 < (b >> 23) & 0xFF < 255 and b >> 31 == 1,
            "ONE": lambda b: 120 <= (b >> 23) & 0xFF <= 134, "BIG": lambda b: (b >> 23) & 0xFF == 254,
            "INF+": lambda b: b == 0x7F800000, "INF-": lambda b: b == 0xFF800000,
            "QNAN": lambda b: is_nan(b) and b & 0x400000, "SNAN": lambda b: is_nan(b) and not b & 0x400000}
    for cls in F32_CLASSES:
        draws = [draw_f32(cls, keyed("selftest", cls, i), i) for i in range(1000)]
        bad = [hex(d) for d in draws if not pred[cls](d)]
        if bad:
            fails.append("class %s: %d draws outside the class, e.g. %s" % (cls, len(bad), bad[:3]))
    forced = {"DEN+": [1, 0x7FFFFF], "BIG": [0x7F7FFFFF]}
    for cls, vals in forced.items():
        for v in vals:
            if v not in [draw_f32(cls, keyed("selftest", cls, i), i) for i in range(3)]:
                fails.append("class %s misses forced value %x" % (cls, v))
    qp = {draw_f32("QNAN", keyed("s", i), i) & 0x3FFFFF for i in range(3)}
    if qp != {0, 1, 0x3FFFFF}:
        fails.append("QNAN forced payloads %s" % qp)
    sp = {draw_f32("SNAN", keyed("s", i), i) & 0x3FFFFF for i in range(2)}
    if sp != {1, 0x3FFFFF}:
        fails.append("SNAN forced payloads %s" % sp)
    # targeted constructions, checked by exact arithmetic
    n_t = 0
    for op in ("add", "sub", "mul", "div"):
        for i in range(300):
            rng = keyed("t", op, i)
            a, b = c_tie(op, rng)
            if not is_tie_rne(exact(op, a, b)):
                fails.append("TIE %s %x %x" % (op, a, b))
            a, b = c_ovf(op, rng)
            if abs(abs(exact(op, a, b)) - TWO128) > Fraction(2) ** 105:
                fails.append("OVF %s %x %x" % (op, a, b))
            x = exact(op, *c_ufl(op, rng))
            if not (x != 0 and abs(x) < T126 * (1 + Fraction(1, 1 << 23))):
                fails.append("UFL %s" % op)
            a, b = c_ftz_exact(op, rng, i)
            x = exact(op, a, b)
            if not (x != 0 and abs(x) < T126 and (x * (1 << 149)).denominator == 1):
                fails.append("F-FTZ-EXACT %s %x %x -> %s" % (op, a, b, x))
            n_t += 4
        for i in range(300):
            if op in ("mul", "div"):
                rng = keyed("tiny", op, i)
                a, b = c_tiny(op, rng, i)
                x = abs(exact(op, a, b))
                if op == "mul" and not (T126 - Fraction(2) ** -150 <= x < T126):
                    fails.append("F-TINY mul %x %x" % (a, b))
                if op == "div" and not (T126 * (1 - Fraction(1, 1 << 23)) <= x < T126):
                    fails.append("F-TINY div %x %x" % (a, b))
                n_t += 1
    for i in range(300):
        v = c_tie_f2i(keyed("tf", i))
        if (val(v) * 2).denominator != 1 or (val(v) * 2).numerator % 2 == 0:
            fails.append("TIE f2i %x" % v)
    rep["targeted_checked"] = n_t
    # fillers raise no flag in any environment
    for fam, (fa, fb) in FILL.items():
        for env_n, mx in E8:
            env = fpenv.Env(mx)
            if fam in ("FP.CVT.f32_i32.rc", "FP.CVT.f32_i32.trunc"):
                fl = fp_ops.cvt_f32_to_i32(fa, env, fam.endswith("trunc"))[1]
            elif fam == "FP.CVT.i32_f32":
                fl = fp_ops.cvt_i32_to_f32(fa, env)[1]
            elif fam == "FP.CVT.f16_f32":
                fl = fp_ops.cvt_f16_to_f32(fa, env)[1]
            elif fam in ("FP.CMP.f32", "FP.COMI.f32"):
                fl = max(fp_ops.cmp_pred(fa, fb, p, env)[1] for p in range(32))
            else:
                fl = {"add": fp_ops.add, "sub": fp_ops.sub, "mul": fp_ops.mul, "div": fp_ops.div, "max": fp_ops.max_,
                      "min": fp_ops.min_}[OPNAME[fam]](fa, fb, env)[1]
            if fl:
                fails.append("filler %s raises %x under %s" % (fam, fl, env_n))
    # plans against the budget rows
    mism = []
    tot_plan = tot_row = 0
    for r in all_rows(g):
        if r["set"] == "V5":
            continue
        p, _ = g.row(r, limit=1)
        tot_plan += p
        tot_row += r["lane_cases"]
        if p != r["lane_cases"]:
            mism.append({"iform": r["iform"], "set": r["set"], "class": r["class"], "row": r["lane_cases"], "plan": p})
    rep["plan_vs_budget"] = {"rows_checked": sum(1 for r in all_rows(g) if r["set"] != "V5"), "plan_total": tot_plan,
                             "budget_total": tot_row, "mismatching_rows": mism}
    # determinism and regeneration from coordinates; full iteration of small rows equals the plan
    rows = all_rows(g)
    pick = [r for r in rows if r["set"] in ("V3", "F-MEMFAULT") and r["lane_cases"] <= 4096][:6] + \
           [r for r in rows if r["set"] == "V2" and r["class"] == "TIE"][:1]
    for r in pick:
        lim = None if r["set"] != "V2" else 200
        p, it1 = g.row(r, limit=lim)
        recs1 = list(it1)
        _, it2 = g.row(r, limit=lim)
        recs2 = list(it2)
        if [m["stub"] for m, _ in recs1] != [m["stub"] for m, _ in recs2] or \
                [c.pack() for _, c in recs1] != [c.pack() for _, c in recs2]:
            fails.append("non-deterministic row %s %s" % (r["iform"], r["set"]))
        if lim is None and sum(m["n_lane_cases"] for m, _ in recs1) != p:
            fails.append("row %s %s yields %d lane cases, plan %d" % (r["iform"], r["set"],
                                                                     sum(m["n_lane_cases"] for m, _ in recs1), p))
    rep["determinism_rows"] = len(pick)
    # F-MEMFAULT (review 2026-10-16): every EVEX row runs each prefix mask with merge (counted) and zero
    # (uncounted duplicate) masking; the counted total stays the row's
    mf_rows = [r for r in rows if r["set"] == "F-MEMFAULT"]
    n_zero = 0
    for r in mf_rows:
        p, it = g.row(r)
        recs = list(it)
        e = g.table.ENTRIES[g.idx_of[r["iform"]]]
        variants = [g.man["stubs"][m["stub"]]["variant"] for m, _ in recs]
        if sum(m["n_lane_cases"] for m, _ in recs) != p:
            fails.append("F-MEMFAULT %s counted %d, plan %d" % (r["iform"], sum(m["n_lane_cases"] for m, _ in recs), p))
        if e["encoding"] == "evex":
            zr = [m for m, _ in recs if g.man["stubs"][m["stub"]]["variant"] == "zero"]
            n_zero += len(zr)
            if len(zr) != e["lanes"] + 1 or any(m["n_lane_cases"] for m in zr) or variants.count("merge") != e["lanes"] + 1:
                fails.append("F-MEMFAULT %s zero-masking duplicates: %d" % (r["iform"], len(zr)))
        if any(not (m["flags"] & vecfmt.FLAG_MEMFAULT) for m, _ in recs):
            fails.append("F-MEMFAULT %s record without the memfault flag" % r["iform"])
    rep["memfault_rows"] = len(mf_rows)
    rep["memfault_zero_mask_duplicates"] = n_zero
    # masked broadcast (review 2026-10-16): reachable through a BCAST row whose class starts with "masked"
    # (no such row in budget_rows today; proposed for the record); checked on a synthetic row
    bc = [r for r in rows if r["set"] == "BCAST"]
    if bc:
        syn = dict(bc[0], **{"class": "masked {1to%d} x 144 x 10 x {merge,zero}" % g.table.ENTRIES[g.idx_of[bc[0]["iform"]]]["lanes"]})
        p, it1 = g.row(syn)
        recs1 = list(it1)
        _, it2 = g.row(syn, limit=50)
        recs2 = list(it2)
        st_names = {g.man["stubs"][m["stub"]]["variant"] for m, _ in recs1}
        if sum(m["n_lane_cases"] for m, _ in recs1) != p or st_names != {"merge_bcast", "zero_bcast"}:
            fails.append("masked BCAST row: %d lane cases, plan %d, variants %s" %
                         (sum(m["n_lane_cases"] for m, _ in recs1), p, sorted(st_names)))
        if [c.pack() for _, c in recs1[:50]] != [c.pack() for _, c in recs2]:
            fails.append("masked BCAST row not deterministic")
        if len({c.k for _, c in recs1}) < 100:
            fails.append("masked BCAST row: masks not varied")
        rep["masked_bcast_synthetic_row"] = {"iform": syn["iform"], "lane_cases": p, "executions": len(recs1)}
    return fails, rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out")
    ap.add_argument("--iform")
    ap.add_argument("--set")
    ap.add_argument("--class", dest="cls")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--label", help="default BUDGET-v1-<set>; a DEV/SELFTEST/VALID label needs --dev")
    ap.add_argument("--dev", action="store_true",
                    help="development slice: allows a DEV label, requires --limit <= %d executions per row" % DEV_LIMIT_CAP)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if not a.selftest:
        dev_label = a.label is not None and a.label.startswith(("DEV", "SELFTEST", "VALID"))
        if a.dev:
            if a.limit is None or not 0 < a.limit <= DEV_LIMIT_CAP:
                ap.error("--dev needs --limit between 1 and %d" % DEV_LIMIT_CAP)
            if a.label is None:
                a.label = "DEV-GEN"
        elif dev_label:
            ap.error("a development label (DEV, SELFTEST, VALID) needs --dev; budget-row vectors carry BUDGET labels")
        if a.label is None:
            a.label = "BUDGET-v1-%s" % (a.set or "ALL")
    g = Gen(a.sem_root, a.manifest)
    if a.selftest:
        fails, rep = selftest(g)
        print(json.dumps(rep, indent=1))
        for f in fails[:50]:
            print("FAIL", f)
        print("gen_vectors selftest: %s (%d failures)" % ("FAIL" if fails else "PASS", len(fails)))
        return 1 if fails else 0
    rows = [r for r in all_rows(g) if r["set"] != "V5" and (not a.iform or r["iform"] == a.iform)
            and (not a.set or r["set"] == a.set) and (not a.cls or r["class"] == a.cls)]

    def recs():
        for r in rows:
            _, it = g.row(r, limit=a.limit)
            yield from it
    n, sha = vecfmt.write_vectors(a.out, recs(), g.manifest_sha, g.gen_sha, g.man["semantics_bundle"], a.label)
    with open(a.out + ".classes.json", "w") as f:
        json.dump({"classes": g.classes, "envs": ENV_NAMES, "rows": rows, "generator_sha256": g.gen_sha,
                   "vectors_sha256": sha}, f, indent=1)
    print(json.dumps({"records": n, "rows": len(rows), "vectors_sha256": sha}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
