"""T2 range re-derivations from Hearth's kernel code (RULES.md §4), using the table semantics.

Method: each saturation/overflow obligation is decomposed to per-product facts over the declared
domains, which are enumerated EXHAUSTIVELY through the table's own lane functions; pair and block
bounds then follow by additivity over independent operands (a sum of independent terms attains the
sum of the termwise extremes). Every number returned is [D] with the formula recorded.

Domains (from Hearth b5d3f14):
  X  activation quants: act_quantize_q8 clamps to [-127, 127] in every ISA (quant.c act_q8_scalar,
     quant_avx2.c act_q8_avx2, quant_avx512.c act_q8_avx512) -> x in [-127, 127].
  W8 Q8 weight quants: the quantiser clamps to [-127, 127], but the kernels must also be safe for
     any int8 byte (test_quant.c test_nonfinite fills Q8 blocks with random bytes) -> w in [-128, 127].
  N4 Q4 nibbles: (byte & 0x0F) or ((byte >> 4) & 0x0F) -> n in [0, 15]; stored value q = n - 8.
The activation facts are the domain predicates DOM-ACT-Q (x in [-127, 127]) and DOM-ACT-SUM
(a.sum == sum of a.q as int32, so |a.sum| <= 8,128) of RULES.md §4.
"""
from .bits import s8
from .int_ops import pabsb, pmaddubsw, pmaddubsw_unsat, psignb
from .vec import pack

X = range(-127, 128)
X_FULL = range(-128, 128)
W8 = range(-128, 128)
N4 = range(0, 16)


def _maddubs_products(pairs):
    """Run (u, s) pairs through VPMADDUBSW (128-bit), one product per 16-bit lane (other byte 0).
    Returns the list of 16-bit results (signed) and the unsaturated sums, to show they agree."""
    out_sat, out_raw = [], []
    for i in range(0, len(pairs), 8):
        chunk = pairs[i:i + 8] + [(0, 0)] * (8 - len(pairs[i:i + 8]))
        a = pack([b for (u, _) in chunk for b in (u & 0xFF, 0)], 8)
        b = pack([b for (_, s) in chunk for b in (s & 0xFF, 0)], 8)
        r = pmaddubsw(a, b, 128)
        raw = pmaddubsw_unsat(a, b, 128)
        for j in range(len(pairs[i:i + 8])):
            v = (r >> (16 * j)) & 0xFFFF
            out_sat.append(v - 0x10000 if v & 0x8000 else v)
            out_raw.append(raw[j])
    return out_sat, out_raw


def q4_maddubs():
    """AVX2 qtile8, Q4: maddubs(nibble, x) -> pair sums; then VPADDW(lo-pair, hi-pair)."""
    prods, raw = _maddubs_products([(n, x) for n in N4 for x in X])
    assert prods == raw
    lo, hi = min(prods), max(prods)
    pair = (2 * lo, 2 * hi)
    padd = (2 * pair[0], 2 * pair[1])          # VPADDW of the low- and high-nibble pair sums
    return {
        "product_range": (lo, hi),             # [-1905, 1905] = +-15*127
        "pair_bound": max(-pair[0], pair[1]),  # 3,810 = 2*15*127
        "pair_saturates": pair[0] < -32768 or pair[1] > 32767,
        "vpaddw_bound": max(-padd[0], padd[1]),  # 7,620
        "vpaddw_wraps": padd[0] < -32768 or padd[1] > 32767,
        "formula": "pair <= 2*15*127; VPADDW <= 2*3810",
    }


def q4_maddubs_full_int8_activation():
    """Same as q4_maddubs but if x could be -128 (it cannot, by X): shows the margin."""
    prods, _ = _maddubs_products([(n, x) for n in N4 for x in X_FULL])
    return {"pair_bound": 2 * max(-min(prods), max(prods))}   # 3,840 -- still far from 32,767


def q8_sign_trick(x_domain=X):
    """AVX2 qtile8, Q8: maddubs(abs_epi8(w), sign_epi8(x, w)). Checks the identity
    |w| * sign(x, w) == w * x for every (w, x) and the pair bound, exhaustively per product."""
    pairs, bad = [], []
    for w in W8:
        u_vec = pabsb(pack([w & 0xFF] * 16, 8), 128)
        u = u_vec & 0xFF                               # PABSB(-128) = 0x80 = 128 as unsigned
        for x in x_domain:
            s = s8(psignb(pack([x & 0xFF] * 16, 8), pack([w & 0xFF] * 16, 8), 128) & 0xFF)
            pairs.append((u, s))
            if u * s != w * x:
                bad.append((w, x))
    prods, raw = _maddubs_products(pairs)
    assert prods == raw
    lo, hi = min(prods), max(prods)
    return {
        "identity_failures": bad,             # [] for x in [-127,127]; x = -128 with w < 0 fails
        "product_range": (lo, hi),
        "pair_bound": max(-2 * lo, 2 * hi),   # 32,512 = 2*128*127
        "pair_saturates": 2 * lo < -32768 or 2 * hi > 32767,
        "formula": "u = |w| <= 128 (PABSB), |s| = |x| <= 127 -> pair <= 2*128*127",
    }


def isum_bounds():
    """Block (64-element) integer sums; each must stay < 2^24 for exact VCVTDQ2PS / (float)isum."""
    q4 = 64 * max(abs(n - 8) for n in N4) * max(abs(x) for x in X)        # 64*8*127
    q8 = 64 * max(abs(w) for w in W8) * max(abs(x) for x in X)            # 64*128*127 (any byte)
    q8_quantiser = 64 * 127 * 127                                          # quantiser range only
    # AVX-512 VNNI path: u = q + 128 (Q8, q xor 0x80) or u = nibble (Q4); correction - bias*sum(x)
    vnni_q8_raw = 64 * 255 * 127
    vnni_q4_raw = 64 * 15 * 127
    act_sum = 64 * 127
    return {
        "q4_isum": q4, "q8_isum_any_byte": q8, "q8_isum_quantiser": q8_quantiser,
        "q4_exact_f32": q4 <= (1 << 24), "q8_exact_f32": q8 <= (1 << 24),
        "vnni_q8_unsigned_sum": vnni_q8_raw, "vnni_q4_unsigned_sum": vnni_q4_raw,
        "vnni_q8_bias_term": 128 * act_sum, "vnni_no_int32_wrap": vnni_q8_raw + 128 * act_sum < (1 << 31),
        "act_sum_bound": act_sum,
        # AVX2 Q4 (quant_avx2.c qtile8): red8 holds sum(n*x) BEFORE `is - a->sum * 8`; |.| <= 64*15*127
        "q4_avx2_red8_before_bias": 64 * max(N4) * max(abs(x) for x in X),
    }


def all_bounds():
    return {"q4_maddubs": q4_maddubs(), "q4_maddubs_if_x_were_int8": q4_maddubs_full_int8_activation(),
            "q8_sign_trick": q8_sign_trick(), "q8_sign_trick_if_x_could_be_-128": q8_sign_trick(X_FULL),
            "isum": isum_bounds()}
