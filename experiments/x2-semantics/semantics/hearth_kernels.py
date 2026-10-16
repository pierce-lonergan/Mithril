"""Transliterations of Hearth b5d3f14 kernel pieces built ONLY from table semantics.

Purpose (X2 spike): (1) check that composing the table's instruction semantics reproduces the lane
maps Hearth's comments claim (red8, red_quads, red_quad1, tree16) -- these are the correspondence
maps T1 needs; (2) check scalar == AVX2 == AVX-512 for act_q8 and the Q4/Q8 block sums on
hand-built blocks, including NaN, inf, subnormal and tie blocks; (3) produce numerics_v1 mutant
WITNESSES: inputs on which a mutant's output differs, or evidence that it does not on a given
input class (equivalent-mutant analysis, MUTANTS.md §5).

Every FP instruction, and every integer instruction that has a table entry, is resolved through
`table.find` (review finding R2-8, 2026-10-16): `entries_used()` returns the (iclass, iform) keys and
content hashes the compositions ran on. Data-movement and bitwise operations without entries yet are
called directly from int_ops and listed by `unregistered_used()`; they become entries when the census
gives their iforms (TABLE-SCHEMA.md §10). Which instruction an intrinsic denotes is fixed by
INTRINSIC_MAP_V0 below, the draft of the frozen `intrinsic_map.v1` (TABLE-SCHEMA.md §8.1).

The transliteration follows the C source line by line; it is evidence about the table and the
design, NOT about what a compiler emits (that is X0's census and the object audit). The scalar
act_q8 function is the MEANING's reference evaluation (KIR operations evaluated with the exact IEEE
core of fp_ops); it is deliberately not routed through x86 table entries.
"""
import hashlib
import json
from fractions import Fraction

from . import fp_ops, int_ops, table
from .bits import F32_SIGN, MASK32, f32_is_nan, s8, s32
from .fpenv import DEFAULT
from .rounding import round_f32
from .vec import lanes, pack

E = DEFAULT

# ---------------------------------------------------------------- intrinsic_map v0 (draft of v1)
# intrinsic -> (iclass, encoding, vl) of the register form, or a non-instruction kind:
#   "cast..."  bit reinterpretation or lane-0 view, no instruction at intrinsic level
#   "seq:..."  a sequence intrinsic, with its expansion
# Encoding rule: every _mm512_* intrinsic and every masked or k-producing 128/256 intrinsic -> EVEX;
# every other 128/256 intrinsic -> VEX, in both files (unmasked VEX and EVEX forms share a family and a
# lane function; the census records which one a compiler emitted). Intrinsic -> instruction follows
# the Intel intrinsics documentation as read by the X2 agents [inference until X0's census iclass
# multisets confirm it; that comparison is a freeze check].
_V, _X = "vex", "evex"
INTRINSIC_MAP_V0 = {
    "_mm256_abs_epi8": ("VPABSB", _V, 256), "_mm256_add_epi16": ("VPADDW", _V, 256),
    "_mm256_add_epi32": ("VPADDD", _V, 256), "_mm256_add_ps": ("VADDPS", _V, 256),
    "_mm256_and_ps": ("VANDPS", _V, 256), "_mm256_and_si256": ("VPAND", _V, 256),
    "_mm256_andnot_ps": ("VANDNPS", _V, 256), "_mm256_blendv_ps": ("VBLENDVPS", _V, 256),
    "_mm256_castpd_ps": "cast", "_mm256_castps256_ps128": "cast",
    "_mm256_castsi128_si256": "cast (upper 128 bits undefined: T1 must show they are overwritten before use)",
    "_mm256_castsi256_ps": "cast", "_mm256_castsi256_si128": "cast",
    "_mm256_cmp_ps": ("VCMPPS", _V, 256), "_mm256_cmpgt_epi32": ("VPCMPGTD", _V, 256),
    "_mm256_cvtepi32_ps": ("VCVTDQ2PS", _V, 256), "_mm256_cvtepu16_epi32": ("VPMOVZXWD", _V, 256),
    "_mm256_cvtph_ps": ("VCVTPH2PS", _V, 256), "_mm256_cvtps_epi32": ("VCVTPS2DQ", _V, 256),
    "_mm256_extractf128_ps": ("VEXTRACTF128", _V, 256), "_mm256_extracti128_si256": ("VEXTRACTI128", _V, 256),
    "_mm256_hadd_epi32": ("VPHADDD", _V, 256), "_mm256_inserti128_si256": ("VINSERTI128", _V, 256),
    "_mm256_load_ps": ("VMOVAPS", _V, 256), "_mm256_loadu_ps": ("VMOVUPS", _V, 256),
    "_mm256_loadu_si256": ("VMOVDQU", _V, 256), "_mm256_madd_epi16": ("VPMADDWD", _V, 256),
    "_mm256_maddubs_epi16": ("VPMADDUBSW", _V, 256), "_mm256_maskstore_ps": ("VMASKMOVPS", _V, 256),
    "_mm256_maskz_loadu_epi16": ("VMOVDQU16", _X, 256), "_mm256_max_ps": ("VMAXPS", _V, 256),
    "_mm256_min_ps": ("VMINPS", _V, 256), "_mm256_mul_ps": ("VMULPS", _V, 256),
    "_mm256_packs_epi16": ("VPACKSSWB", _V, 256), "_mm256_packs_epi32": ("VPACKSSDW", _V, 256),
    "_mm256_permute2x128_si256": ("VPERM2I128", _V, 256), "_mm256_permutevar8x32_epi32": ("VPERMD", _V, 256),
    "_mm256_set1_epi16": "seq:constant or VPBROADCASTW", "_mm256_set1_epi32": "seq:constant or VPBROADCASTD",
    "_mm256_set1_epi8": "seq:constant or VPBROADCASTB", "_mm256_set1_ps": "seq:constant or VBROADCASTSS",
    "_mm256_setr_epi32": "seq:constant", "_mm256_setzero_ps": "seq:zero idiom (+0.0 lanes)",
    "_mm256_setzero_si256": "seq:zero idiom", "_mm256_sign_epi8": ("VPSIGNB", _V, 256),
    "_mm256_slli_epi32": ("VPSLLD", _V, 256), "_mm256_srli_epi16": ("VPSRLW", _V, 256),
    "_mm256_store_ps": ("VMOVAPS", _V, 256), "_mm256_storeu_ps": ("VMOVUPS", _V, 256),
    "_mm256_storeu_si256": ("VMOVDQU", _V, 256), "_mm256_sub_epi32": ("VPSUBD", _V, 256),
    "_mm512_abs_ps": "seq:VPANDD with a broadcast 0x7FFFFFFF (sign-bit clear)",
    "_mm512_add_epi32": ("VPADDD", _X, 512), "_mm512_add_ps": ("VADDPS", _X, 512),
    "_mm512_and_si512": ("VPANDD", _X, 512), "_mm512_broadcast_i32x4": ("VBROADCASTI32X4", _X, 512),
    "_mm512_castps512_ps256": "cast", "_mm512_castps_pd": "cast",
    "_mm512_castsi256_si512": "cast (upper 256 bits undefined)", "_mm512_castsi512_ps": "cast",
    "_mm512_castsi512_si128": "cast", "_mm512_castsi512_si256": "cast",
    "_mm512_cmp_ps_mask": ("VCMPPS", _X, 512), "_mm512_cvtepi32_epi8": ("VPMOVDB", _X, 512),
    "_mm512_cvtepi32_ps": ("VCVTDQ2PS", _X, 512), "_mm512_cvtepu16_epi32": ("VPMOVZXWD", _X, 512),
    "_mm512_cvtph_ps": ("VCVTPH2PS", _X, 512), "_mm512_cvtps_epi32": ("VCVTPS2DQ", _X, 512),
    "_mm512_dpbusd_epi32": ("VPDPBUSD", _X, 512), "_mm512_extractf64x4_pd": ("VEXTRACTF64X4", _X, 512),
    "_mm512_extracti64x4_epi64": ("VEXTRACTI64X4", _X, 512), "_mm512_inserti64x4": ("VINSERTI64X4", _X, 512),
    "_mm512_loadu_ps": ("VMOVUPS", _X, 512), "_mm512_mask_add_ps": ("VADDPS", _X, 512),
    "_mm512_mask_mov_ps": ("VMOVAPS", _X, 512), "_mm512_maskz_loadu_ps": ("VMOVUPS", _X, 512),
    "_mm512_maskz_mov_ps": ("VMOVAPS", _X, 512), "_mm512_max_ps": ("VMAXPS", _X, 512),
    "_mm512_min_ps": ("VMINPS", _X, 512), "_mm512_mul_ps": ("VMULPS", _X, 512),
    "_mm512_permutexvar_epi32": ("VPERMD", _X, 512), "_mm512_set1_epi32": "seq:constant or VPBROADCASTD",
    "_mm512_set1_epi8": "seq:constant or VPBROADCASTB", "_mm512_set1_ps": "seq:constant or VBROADCASTSS",
    "_mm512_setr_epi32": "seq:constant", "_mm512_setzero_ps": "seq:zero idiom (+0.0 lanes)",
    "_mm512_setzero_si512": "seq:zero idiom", "_mm512_shuffle_epi32": ("VPSHUFD", _X, 512),
    "_mm512_shuffle_i64x2": ("VSHUFI64X2", _X, 512), "_mm512_slli_epi32": ("VPSLLD", _X, 512),
    "_mm512_srli_epi16": ("VPSRLW", _X, 512), "_mm512_storeu_ps": ("VMOVUPS", _X, 512),
    "_mm512_sub_epi32": ("VPSUBD", _X, 512), "_mm512_unpackhi_epi32": ("VPUNPCKHDQ", _X, 512),
    "_mm512_unpackhi_epi64": ("VPUNPCKHQDQ", _X, 512), "_mm512_unpacklo_epi32": ("VPUNPCKLDQ", _X, 512),
    "_mm512_unpacklo_epi64": ("VPUNPCKLQDQ", _X, 512), "_mm512_xor_si512": ("VPXORD", _X, 512),
    "_mm_add_epi32": ("VPADDD", _V, 128), "_mm_add_ps": ("VADDPS", _V, 128), "_mm_add_ss": ("VADDSS", _V, 128),
    "_mm_blendv_ps": ("VBLENDVPS", _V, 128), "_mm_castsi128_ps": "cast",
    "_mm_cmp_ps_mask": ("VCMPPS", _X, 128), "_mm_cmpunord_ps": ("VCMPPS", _V, 128),
    "_mm_cvtepi32_ps": ("VCVTDQ2PS", _V, 128), "_mm_cvtph_ps": ("VCVTPH2PS", _V, 128),
    "_mm_cvtsi128_si32": ("VMOVD", _V, 128), "_mm_cvtsi32_si128": ("VMOVD", _V, 128),
    "_mm_cvtsi64_si128": ("VMOVQ", _V, 128), "_mm_cvtss_f32": "cast (lane 0)",
    "_mm_load_ss": ("VMOVSS", _V, 128), "_mm_loadu_si128": ("VMOVDQU", _V, 128),
    "_mm_mask_mov_ps": ("VMOVAPS", _X, 128), "_mm_mask_storeu_ps": ("VMOVUPS", _X, 128),
    "_mm_max_ps": ("VMAXPS", _V, 128), "_mm_max_ss": ("VMAXSS", _V, 128), "_mm_movehl_ps": ("VMOVHLPS", _V, 128),
    "_mm_mul_ps": ("VMULPS", _V, 128), "_mm_mul_ss": ("VMULSS", _V, 128),
    "_mm_set1_epi32": "seq:constant or VPBROADCASTD", "_mm_set1_ps": "seq:constant or VBROADCASTSS",
    "_mm_set_epi64x": "seq:constant or VMOVQ + VPINSRQ", "_mm_set_ss": "seq:VMOVSS (upper lanes +0.0)",
    "_mm_setzero_ps": "seq:zero idiom (+0.0 lanes)", "_mm_shuffle_epi32": ("VPSHUFD", _V, 128),
    "_mm_shuffle_ps": ("VSHUFPS", _V, 128), "_mm_store_ss": ("VMOVSS", _V, 128),
    "_mm_storeu_si128": ("VMOVDQU", _V, 128), "_mm_sub_epi32": ("VPSUBD", _V, 128),
}
# Scalar C operators inside the SIMD files (no intrinsic): one named VEX scalar form each. Integer C
# operators (`a->sum * bias`, `(int8_t)q`, index arithmetic) keep C integer semantics and are evaluated
# as QF_BV terms by T2 (signed overflow is UB, so T2 proves its absence); they use no table entry.
SCALAR_C_MAP_V0 = {
    "float / float": ("VDIVSS", _V, 128), "float * float": ("VMULSS", _V, 128),
    "float + float": ("VADDSS", _V, 128), "float - float": ("VSUBSS", _V, 128),
    "float == float, float != float": ("VUCOMISS", _V, 128),   # quiet predicates; truth from ZF and PF
    "float < float, >, <=, >=": ("VCOMISS", _V, 128),           # IEEE relational operators signal on QNaN
    "(float)int32": ("VCVTSI2SS", _V, 128), "(int32)float": ("VCVTTSS2SI", _V, 128),
}


def intrinsic_map_hash():
    blob = json.dumps({"intrinsics": INTRINSIC_MAP_V0, "scalar_c": SCALAR_C_MAP_V0},
                      sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def resolve_intrinsic(name):
    """The table entry an intrinsic denotes, or None (cast, sequence, or no entry yet)."""
    m = INTRINSIC_MAP_V0[name]
    if isinstance(m, str):
        return None
    try:
        return table.find(m[0], encoding=m[1], vl=m[2])
    except KeyError:
        return None


# ---------------------------------------------------------------- entry resolution with a record
_USED = {}
_UNREG = set()


def _use(iclass, encoding, vl):
    e = table.find(iclass, encoding=encoding, vl=vl)
    _USED[(e["key"]["iclass"], e["key"]["iform"])] = e
    return e["_sem"]


def _raw(name):
    """Record a data-movement / bitwise operation evaluated without a table entry."""
    _UNREG.add(name)
    return getattr(int_ops, name)


def entries_used():
    b = table.bundle_hash()
    return {"%s %s" % k: table.content_hash(e, b) for k, e in sorted(_USED.items())}


def unregistered_used():
    return sorted(_UNREG)


def f32(dec):
    """binary32 bits of a decimal/rational literal (RNE), e.g. f32('1e-39')."""
    v = Fraction(dec)
    if v == 0:
        return F32_SIGN if str(dec).startswith("-") else 0
    return round_f32(v < 0, abs(v), 0, False)[0]


C127, CM127, ONE, ZERO = f32(127), f32(-127), f32(1), 0


# ---------------------------------------------------------------- instruction helpers (table entries)

def _enc(vl):
    return "evex" if vl == 512 else "vex"


def vaddps(a, b, vl):
    return _use("VADDPS", _enc(vl), vl)(a, b, E)[0]


def vmulps(a, b, vl):
    return _use("VMULPS", _enc(vl), vl)(a, b, E)[0]


def vmaxps(a, b, vl):
    return _use("VMAXPS", _enc(vl), vl)(a, b, E)[0]


def vminps(a, b, vl):
    return _use("VMINPS", _enc(vl), vl)(a, b, E)[0]


def vaddss(a, b):
    return _use("VADDSS", "vex", 128)(a, b, E)[0]


def vmaxss(a, b):
    return _use("VMAXSS", "vex", 128)(a, b, E)[0]


def vdivss(a, b):
    return _use("VDIVSS", "vex", 128)(a, b, E)[0] & MASK32


def c_ne(a, b):
    """C `a != b` on floats -> VUCOMISS; true iff ZF == 0 or PF == 1 (unordered counts as !=)."""
    fl = _use("VUCOMISS", "vex", 128)(a, b, E)[0]
    return fl["ZF"] == 0 or fl["PF"] == 1


def vcvtps2dq(a, vl, trunc=False):
    return _use("VCVTTPS2DQ" if trunc else "VCVTPS2DQ", _enc(vl), vl)(a, E)[0]


def vcmpps_vec(a, b, pred, vl):
    return _use("VCMPPS", "vex", vl)(a, b, fp_ops.CMP_BY_NAME[pred], E)[0]


def vcmpps_k(a, b, pred, vl):
    return _use("VCMPPS", "evex", vl)(a, b, fp_ops.CMP_BY_NAME[pred], E)[0]


def bcast(x, vl):
    return _raw("broadcast32")(x, vl)


# ---------------------------------------------------------------- reductions (lane maps)

def sum16_ref(L):
    """NUMERICS §1 tree (meaning side): for s in 8,4,2,1: L[j] = L[j] + L[j+s]."""
    L = list(L)
    for s in (8, 4, 2, 1):
        for j in range(s):
            L[j] = fp_ops.add(L[j], L[j + s], E)[0]
    return L[0]


def canon_scalar(v):
    return 0x7FC00000 if f32_is_nan(v) else v


def canon4_avx2(v128):
    m = vcmpps_vec(v128, v128, "UNORD_Q", 128)
    return _raw("blendvps")(v128, bcast(0x7FC00000, 128), m, 128)


def canon4_avx512(v128):
    k = vcmpps_k(v128, v128, "UNORD_Q", 128)
    return _raw("blend_k")(v128, bcast(0x7FC00000, 128), k, 128)


def tree16_avx2(lo, hi):
    """quant_avx2.c tree16: s8 = lo+hi; s4 = s8.lo128 + s8.hi128; s2 = s4 + movehl(s4,s4);
    s1 = add_ss(s2, shuffle(s2,s2,1)); canon4."""
    s8_ = vaddps(lo, hi, 256)
    s4 = vaddps(_raw("extract128")(s8_, 0), _raw("extract128")(s8_, 1), 128)
    s2 = vaddps(s4, _raw("movhlps")(s4, s4), 128)
    s1 = vaddss(s2, _raw("shufps")(s2, s2, 1, 128))
    return canon4_avx2(s1) & 0xFFFFFFFF


def tree16_avx512(v):
    lo, hi = _raw("extract256")(v, 0), _raw("extract256")(v, 1)
    s8_ = vaddps(lo, hi, 256)
    s4 = vaddps(_raw("extract128")(s8_, 0), _raw("extract128")(s8_, 1), 128)
    s2 = vaddps(s4, _raw("movhlps")(s4, s4), 128)
    s1 = vaddss(s2, _raw("shufps")(s2, s2, 1, 128))
    return canon4_avx512(s1) & 0xFFFFFFFF


def red8(s):
    """quant_avx2.c red8: s[i] = 8 int32 partials of row i -> lane i = total of row i."""
    hadd = _use("VPHADDD", "vex", 256)
    h01, h23 = hadd(s[0], s[1]), hadd(s[2], s[3])
    h45, h67 = hadd(s[4], s[5]), hadd(s[6], s[7])
    a, b = hadd(h01, h23), hadd(h45, h67)
    p2 = _raw("perm2i128")
    return _raw("padd")(p2(a, b, 0x20), p2(a, b, 0x31), 256, 32)


def red_quads(v0, v1, v2, v3):
    lo, hi, add = _raw("unpcklo"), _raw("unpckhi"), _raw("padd")
    s01 = add(lo(v0, v1, 512, 32), hi(v0, v1, 512, 32), 512, 32)
    s23 = add(lo(v2, v3, 512, 32), hi(v2, v3, 512, 32), 512, 32)
    return add(lo(s01, s23, 512, 64), hi(s01, s23, 512, 64), 512, 32)


def red_quad1(v):
    idx = pack([0, 4, 8, 12] * 4, 32)
    add, shuf = _raw("padd"), _raw("pshufd")
    v = add(v, shuf(v, 0x4E, 512), 512, 32)
    v = add(v, shuf(v, 0xB1, 512), 512, 32)
    return _raw("extract128")(_raw("permd")(v, idx, 512), 0)


# ---------------------------------------------------------------- act_q8: scalar meaning (quant.c)

def _c_gt(a, b):
    return fp_ops.relation(a, b, E, False)[0] == fp_ops.GT


def _c_lt(a, b):
    return fp_ops.relation(a, b, E, False)[0] == fp_ops.LT


def act_q8_scalar(x, mut=frozenset()):
    """quant.c act_q8_scalar for one 64-block. Returns (d_bits, sum, q list)."""
    amax = ZERO
    for xi in x:
        a = xi & 0x7FFFFFFF                                   # fabsf
        if _c_gt(a, amax):
            amax = a
    d = fp_ops.div(amax, C127, E)[0]
    idv = fp_ops.div(ONE, d, E)[0] if not fp_ops.relation(d, ZERO, E, False)[0] == fp_ops.EQ else ZERO
    q, s = [], 0
    hi_c = f32(128) if "clamp128" in mut else C127
    lo_c = f32(-128) if "clamp128" in mut else CM127
    for xi in x:
        v = fp_ops.mul(xi, idv, E)[0]
        if f32_is_nan(v):
            v = ZERO
        v = hi_c if _c_gt(v, hi_c) else v
        v = lo_c if _c_lt(v, lo_c) else v
        magic = f32(12582912)                                 # q_rint: (v + 1.5*2^23) - 1.5*2^23
        r = fp_ops.sub(fp_ops.add(v, magic, E)[0], magic, E)[0]
        qi = s32(fp_ops.cvt_f32_to_i32(r, E, True)[0])        # (int) cast = CVTTSS2SI
        q.append(s8(qi))                                      # (int8_t)
        s += qi
    return d, s, q


# ---------------------------------------------------------------- act_q8: AVX2 / AVX-512 (table ops)

def _amax_and_scale(vs, vl, mut):
    m = 0
    for v in vs:
        absv = _raw("pandn")(bcast(F32_SIGN, vl), v)                            # andnot(sign, v)
        m = vmaxps(m, absv, vl) if "commute_max" in mut else vmaxps(absv, m, vl)
    if vl == 512:
        m = vmaxps(_raw("extract256")(m, 0), _raw("extract256")(m, 1), 256)
    b = vmaxps(_raw("extract128")(m, 0), _raw("extract128")(m, 1), 128)
    b = vmaxps(b, _raw("movhlps")(b, b), 128)
    b = vmaxss(b, _raw("shufps")(b, b, 1, 128))
    amax = b & 0xFFFFFFFF
    d = vdivss(amax, C127)                                                      # amax / 127.0f
    idv = vdivss(ONE, d) if c_ne(d, ZERO) else ZERO                             # d != 0.0f ? 1.0f / d : 0.0f
    return d, idv


def _quantize_vec(v, vid, vl, mut):
    p = vmulps(v, vid, vl)
    if "no_ord_zero" not in mut:
        if vl == 256:
            p = _raw("pand")(p, vcmpps_vec(p, p, "ORD_Q", vl))
        else:
            k = vcmpps_k(p, p, "ORD_Q", vl)
            p = _raw("masked")(p, 0, k, True, vl, 32)                          # maskz_mov
    hi_c = f32(128) if "clamp128" in mut else C127
    lo_c = f32(-128) if "clamp128" in mut else CM127
    p = vmaxps(vminps(p, bcast(hi_c, vl), vl), bcast(lo_c, vl), vl)
    if "tie_away" in mut:                       # round half away: trunc(p + copysign(0.5, p))
        half = pack([(f32("0.5") | (x & F32_SIGN)) for x in lanes(p, 32, vl // 32)], 32)
        return vcvtps2dq(vaddps(p, half, vl), vl, trunc=True)
    return vcvtps2dq(p, vl, trunc=("trunc" in mut))


def act_q8_avx2(x, mut=frozenset()):
    vs = [pack(x[8 * k:8 * k + 8], 32) for k in range(8)]
    d, idv = _amax_and_scale(vs, 256, mut)
    vid = bcast(idv, 256)
    q, s = [], 0
    for v in vs:
        qk = _quantize_vec(v, vid, 256, mut)
        q.append(qk)
        s = _raw("padd")(s, qk, 256, 32)
    perm = pack([0, 4, 1, 5, 2, 6, 3, 7], 32)
    out = []
    for h in range(2):
        w = _raw("packsswb")(_raw("packssdw")(q[4 * h], q[4 * h + 1], 256),
                             _raw("packssdw")(q[4 * h + 2], q[4 * h + 3], 256), 256)
        out += [s8(b) for b in lanes(_raw("permd")(w, perm, 256), 8, 32)]
    total = sum(s32(t) for t in lanes(s, 32, 8))          # hsum8_i32 (exact: no wrap possible)
    return d, s32(total), out


def act_q8_avx512(x, mut=frozenset()):
    vs = [pack(x[16 * k:16 * k + 16], 32) for k in range(4)]
    d, idv = _amax_and_scale(vs, 512, mut)
    vid = bcast(idv, 512)
    out, s = [], 0
    for v in vs:
        qk = _quantize_vec(v, vid, 512, mut)
        s = _raw("padd")(s, qk, 512, 32)
        out += [s8(b) for b in lanes(_raw("pmovdb")(qk, 512), 8, 16)]
    total = sum(s32(t) for t in lanes(s, 32, 16))
    return d, s32(total), out


# ---------------------------------------------------------------- the commute-before-MAXPS witness rule

def nan_tree_fate(n_lanes, lane):
    """A NaN in lane `lane` of the running-max vector entering Hearth's horizontal max tree (hmax8:
    pairs (j, j+4), (j, j+2), (j, j+1); hmax16 adds (j, j+8) first; src1 = low half, src2 = high half).
    MAXPS returns src2 when either source is NaN, so the NaN propagates while it is on the src2 side
    and, at the first node where it is on the src1 side, the node returns the src2 sibling and every
    lane merged into the NaN so far is ERASED. Returns ("root", lanes) if the NaN reaches the result
    (d becomes NaN), else ("erased", lanes)."""
    merged, pos, half = {lane}, lane, n_lanes // 2
    while half >= 1:
        if pos >= half:                      # NaN is src2: max(sibling, NaN) = NaN; sibling is lost too
            merged |= {x - half for x in merged}
            pos -= half
        else:                                # NaN is src1: the node returns the src2 sibling
            return "erased", frozenset(merged)
        half //= 2
    return "root", frozenset(merged)


def commute_max_visible(n_lanes, max_pos, nan_pos, n=64):
    """Derived rule (MUTANTS.md §5) for a block whose maximum magnitude sits ONLY at max_pos, with one
    NaN at nan_pos and every other element of smaller magnitude: is the mutant m = max(m, |v|)
    visible in act_q8's output? Lane chain of position p is p mod n_lanes.
      (i)  the NaN sets its chain's running max to NaN and the next element of that chain replaces
           it, discarding every earlier element of the chain: visible iff the maximum is in the
           NaN's chain before it;
      (ii) a NaN that ends its chain enters the horizontal tree: visible iff it reaches the root
           (d = NaN) or the lane holding the maximum is in the erased set."""
    if nan_pos == max_pos:
        return False
    c_nan, c_max = nan_pos % n_lanes, max_pos % n_lanes
    if c_nan == c_max and max_pos < nan_pos:
        return True
    if nan_pos >= n - n_lanes:               # last element of its chain
        fate, lanes_ = nan_tree_fate(n_lanes, c_nan)
        return fate == "root" or c_max in lanes_
    return False


# ---------------------------------------------------------------- Q4 / Q8 block integer sums

def isum_q4_scalar(qs, xq):
    t = 0
    for j in range(32):
        t += ((qs[j] & 0x0F) - 8) * xq[j]
        t += ((qs[j] >> 4) - 8) * xq[j + 32]
    return t


def isum_q8_scalar(wq, xq):
    return sum(w * x for w, x in zip(wq, xq))


def isum_q4_avx2(qs, xq, asum):
    v = pack(qs, 8)
    m4 = pack([0x0F] * 32, 8)
    lo = _raw("pand")(v, m4)
    hi = _raw("pand")(_raw("psrl")(v, 4, 256, 16), m4)
    x0, x1 = pack([b & 0xFF for b in xq[:32]], 8), pack([b & 0xFF for b in xq[32:]], 8)
    maddubs, madd = _use("VPMADDUBSW", "vex", 256), _use("VPMADDWD", "vex", 256)
    p = _raw("padd")(maddubs(lo, x0), maddubs(hi, x1), 256, 16)
    s = madd(p, pack([1] * 16, 16))
    tot = sum(s32(t) for t in lanes(s, 32, 8))
    return s32((tot - asum * 8) & 0xFFFFFFFF)


def isum_q8_avx2(wq, xq):
    w0, w1 = pack([b & 0xFF for b in wq[:32]], 8), pack([b & 0xFF for b in wq[32:]], 8)
    x0, x1 = pack([b & 0xFF for b in xq[:32]], 8), pack([b & 0xFF for b in xq[32:]], 8)
    ones = pack([1] * 16, 16)
    maddubs, madd = _use("VPMADDUBSW", "vex", 256), _use("VPMADDWD", "vex", 256)
    absb, signb = _raw("pabsb"), _raw("psignb")
    p0 = maddubs(absb(w0, 256), signb(x0, w0, 256))
    p1 = maddubs(absb(w1, 256), signb(x1, w1, 256))
    s = _raw("padd")(madd(p0, ones), madd(p1, ones), 256, 32)
    return s32(sum(s32(t) for t in lanes(s, 32, 8)) & 0xFFFFFFFF)


def isum_vnni(u_bytes, xq, asum, bias):
    """AVX-512 dot_quad arithmetic for one row: 4 VPDPBUSD over 16-byte chunks, then the lane total,
    then - bias * sum(x). u = nibble (Q4, bias 8) or q xor 0x80 (Q8, bias 128). Correct only on the
    domain DOM-ACT-SUM (asum == sum(xq)), RULES.md §4."""
    dpbusd = _use("VPDPBUSD", "evex", 128)
    acc = 0
    for c in range(4):
        u = pack(u_bytes[16 * c:16 * c + 16], 8)
        x = pack([b & 0xFF for b in xq[16 * c:16 * c + 16]], 8)
        acc = dpbusd(acc, u, x)
    acc_total = sum(s32(t) for t in lanes(acc, 32, 4))
    return s32((acc_total - asum * bias) & 0xFFFFFFFF)
