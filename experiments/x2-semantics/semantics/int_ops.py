"""Integer and data-movement semantics (no FP environment dependence).

Every function takes register values as Python ints of `vl` bits and returns an int of the
destination width. Operand order follows the instruction's SOURCE order (src1, src2), which for
VEX/EVEX three-operand forms is the order of the C intrinsic's arguments unless noted.
Masking for EVEX forms is applied by `masked(...)` around these functions.
SDM pseudocode is cited by instruction page name (Vol 2).
"""
from .bits import MASK32, s8, s16, s32, sat_s8, sat_s16, sat_s32
from .vec import lanes, pack


def masked(result, dst, k, z, vl, eb):
    """Apply an EVEX write mask with element width eb to an already computed result."""
    if k is None:
        return result
    R, D = lanes(result, eb, vl // eb), lanes(dst, eb, vl // eb)
    return pack([R[i] if (k >> i) & 1 else (0 if z else D[i]) for i in range(vl // eb)], eb)


# ------------------------------------------------------------ multiply-add family (T2-relevant)

def pmaddubsw(a, b, vl):
    """(V)PMADDUBSW: a = UNSIGNED bytes, b = SIGNED bytes (intrinsic _mm*_maddubs_epi16(a, b)).
    dst.word[i] = SaturateToSignedWord(a[2i+1]*b[2i+1] + a[2i]*b[2i])."""
    A, B = lanes(a, 8, vl // 8), [s8(x) for x in lanes(b, 8, vl // 8)]
    return pack([sat_s16(A[2 * i + 1] * B[2 * i + 1] + A[2 * i] * B[2 * i]) for i in range(vl // 16)], 16)


def pmaddubsw_unsat(a, b, vl):
    """Helper for T2: the exact pair sums before saturation (list of Python ints)."""
    A, B = lanes(a, 8, vl // 8), [s8(x) for x in lanes(b, 8, vl // 8)]
    return [A[2 * i + 1] * B[2 * i + 1] + A[2 * i] * B[2 * i] for i in range(vl // 16)]


def pmaddwd(a, b, vl):
    """(V)PMADDWD: signed words; dst.dword[i] = a[2i+1]*b[2i+1] + a[2i]*b[2i], wrapping to 32 bits.
    The only wrap: all four words 0x8000 -> 0x80000000 (SDM PMADDWD)."""
    A, B = [s16(x) for x in lanes(a, 16, vl // 16)], [s16(x) for x in lanes(b, 16, vl // 16)]
    return pack([(A[2 * i + 1] * B[2 * i + 1] + A[2 * i] * B[2 * i]) & MASK32 for i in range(vl // 32)], 32)


def pdpbusd(src, a, b, vl, saturate=False):
    """VPDPBUSD(S): src = accumulator (dwords), a = UNSIGNED bytes, b = SIGNED bytes
    (intrinsic _mm512_dpbusd_epi32(src, a, b)). dst.dword[i] = src[i] + sum_{j<4} a[4i+j]*b[4i+j],
    wrapping (VPDPBUSD) or signed-saturating (VPDPBUSDS)."""
    S = [s32(x) for x in lanes(src, 32, vl // 32)]
    A, B = lanes(a, 8, vl // 8), [s8(x) for x in lanes(b, 8, vl // 8)]
    out = []
    for i in range(vl // 32):
        t = S[i] + sum(A[4 * i + j] * B[4 * i + j] for j in range(4))
        out.append((sat_s32(t) if saturate else t) & MASK32)
    return pack(out, 32)


def phaddd(a, b, vl):
    """(V)PHADDD, per 128-bit lane L: [a0+a1, a2+a3, b0+b1, b2+b3] of that lane (wrapping)."""
    A, B = lanes(a, 32, vl // 32), lanes(b, 32, vl // 32)
    out = []
    for L in range(vl // 128):
        x, y = A[4 * L:4 * L + 4], B[4 * L:4 * L + 4]
        out += [(x[0] + x[1]) & MASK32, (x[2] + x[3]) & MASK32, (y[0] + y[1]) & MASK32, (y[2] + y[3]) & MASK32]
    return pack(out, 32)


# ------------------------------------------------------------ element-wise integer

def padd(a, b, vl, eb):
    m = (1 << eb) - 1
    return pack([(x + y) & m for x, y in zip(lanes(a, eb, vl // eb), lanes(b, eb, vl // eb))], eb)


def psub(a, b, vl, eb):
    m = (1 << eb) - 1
    return pack([(x - y) & m for x, y in zip(lanes(a, eb, vl // eb), lanes(b, eb, vl // eb))], eb)


def pabsb(a, vl):
    """(V)PABSB: |a| per byte; |-128| = 0x80 (128 when read as unsigned, as PMADDUBSW does)."""
    return pack([abs(s8(x)) & 0xFF for x in lanes(a, 8, vl // 8)], 8)


def psignb(a, b, vl):
    """(V)PSIGNB(a, b): b<0 -> -a (wrapping: -(-128) = -128), b==0 -> 0, b>0 -> a."""
    out = []
    for x, y in zip(lanes(a, 8, vl // 8), lanes(b, 8, vl // 8)):
        y = s8(y)
        out.append(((-s8(x)) & 0xFF) if y < 0 else (0 if y == 0 else x))
    return pack(out, 8)


def pcmpgtd(a, b, vl):
    return pack([MASK32 if s32(x) > s32(y) else 0 for x, y in zip(lanes(a, 32, vl // 32), lanes(b, 32, vl // 32))], 32)


def psll(a, count, vl, eb):
    m = (1 << eb) - 1
    return pack([((x << count) & m) if count < eb else 0 for x in lanes(a, eb, vl // eb)], eb)


def psrl(a, count, vl, eb):
    return pack([(x >> count) if count < eb else 0 for x in lanes(a, eb, vl // eb)], eb)


def pand(a, b):
    return a & b


def pandn(a, b):
    """(V)PANDN / (V)ANDNPS(a, b) = (NOT a) AND b (intrinsic _mm*_andnot_*(a, b))."""
    return (~a) & b


def pxor(a, b):
    return a ^ b


def pmovzxwd(a, vl):
    """(V)PMOVZXWD: zero-extend vl/32 words of the source to dwords."""
    return pack(lanes(a, 16, vl // 32), 32)


# ------------------------------------------------------------ narrowing

def packssdw(a, b, vl):
    """(V)PACKSSDW per 128-bit lane: [sat16(a0..a3), sat16(b0..b3)]."""
    A, B = lanes(a, 32, vl // 32), lanes(b, 32, vl // 32)
    out = []
    for L in range(vl // 128):
        out += [sat_s16(s32(x)) & 0xFFFF for x in A[4 * L:4 * L + 4]]
        out += [sat_s16(s32(x)) & 0xFFFF for x in B[4 * L:4 * L + 4]]
    return pack(out, 16)


def packsswb(a, b, vl):
    """(V)PACKSSWB per 128-bit lane: [sat8(a0..a7), sat8(b0..b7)]."""
    A, B = lanes(a, 16, vl // 16), lanes(b, 16, vl // 16)
    out = []
    for L in range(vl // 128):
        out += [sat_s8(s16(x)) & 0xFF for x in A[8 * L:8 * L + 8]]
        out += [sat_s8(s16(x)) & 0xFF for x in B[8 * L:8 * L + 8]]
    return pack(out, 8)


def pmovdb(a, vl_src):
    """VPMOVDB: truncate each dword to its low byte (no saturation); result has vl_src/32 bytes."""
    return pack([x & 0xFF for x in lanes(a, 32, vl_src // 32)], 8)


# ------------------------------------------------------------ data movement

def pshufd(a, imm, vl):
    """(V)PSHUFD per 128-bit lane: dst[j] = src[(imm >> 2j) & 3]."""
    A = lanes(a, 32, vl // 32)
    out = []
    for L in range(vl // 128):
        out += [A[4 * L + ((imm >> (2 * j)) & 3)] for j in range(4)]
    return pack(out, 32)


def shufps(a, b, imm, vl):
    """(V)SHUFPS per 128-bit lane: [a[i0], a[i1], b[i2], b[i3]], i_j = (imm >> 2j) & 3."""
    A, B = lanes(a, 32, vl // 32), lanes(b, 32, vl // 32)
    out = []
    for L in range(vl // 128):
        x, y = A[4 * L:4 * L + 4], B[4 * L:4 * L + 4]
        out += [x[imm & 3], x[(imm >> 2) & 3], y[(imm >> 4) & 3], y[(imm >> 6) & 3]]
    return pack(out, 32)


def movhlps(a, b):
    """VMOVHLPS xmm1, xmm2(a), xmm3(b) = intrinsic _mm_movehl_ps(a, b): [b2, b3, a2, a3]."""
    A, B = lanes(a, 32, 4), lanes(b, 32, 4)
    return pack([B[2], B[3], A[2], A[3]], 32)


def permd(table, idx, vl):
    """VPERMD: dst[i] = table[idx[i] mod n]. Intrinsics: _mm256_permutevar8x32_epi32(table, idx)
    and _mm512_permutexvar_epi32(idx, table) -- note the swapped C argument order. In the encoding
    VPERMD ymm1, ymm2, ymm3/m256 the INDEX is ymm2 and the table is ymm3/m256."""
    n = vl // 32
    T, I = lanes(table, 32, n), lanes(idx, 32, n)
    return pack([T[I[i] % n] for i in range(n)], 32)


def perm2i128(a, b, imm):
    """VPERM2I128 / VPERM2F128: each 128-bit half selects a.lo, a.hi, b.lo, b.hi by imm[1:0] / imm[5:4];
    imm[3] / imm[7] zero that half."""
    src = [a & ((1 << 128) - 1), a >> 128, b & ((1 << 128) - 1), b >> 128]
    lo = 0 if imm & 0x08 else src[imm & 3]
    hi = 0 if imm & 0x80 else src[(imm >> 4) & 3]
    return lo | (hi << 128)


def unpcklo(a, b, vl, eb):
    """(V)PUNPCKL{DQ,QDQ}: per 128-bit lane interleave the low halves of a and b."""
    n = 128 // eb
    A, B = lanes(a, eb, vl // eb), lanes(b, eb, vl // eb)
    out = []
    for L in range(vl // 128):
        x, y = A[n * L:n * L + n // 2], B[n * L:n * L + n // 2]
        for i in range(n // 2):
            out += [x[i], y[i]]
    return pack(out, eb)


def unpckhi(a, b, vl, eb):
    n = 128 // eb
    A, B = lanes(a, eb, vl // eb), lanes(b, eb, vl // eb)
    out = []
    for L in range(vl // 128):
        x, y = A[n * L + n // 2:n * L + n], B[n * L + n // 2:n * L + n]
        for i in range(n // 2):
            out += [x[i], y[i]]
    return pack(out, eb)


def shuf_i64x2(a, b, imm):
    """VSHUFI64X2 / VSHUFI32X4 (512): 128-bit blocks [a[i0], a[i1], b[i2], b[i3]]."""
    A, B = lanes(a, 128, 4), lanes(b, 128, 4)
    return pack([A[imm & 3], A[(imm >> 2) & 3], B[(imm >> 4) & 3], B[(imm >> 6) & 3]], 128)


def extract128(a, i):
    return (a >> (128 * i)) & ((1 << 128) - 1)


def extract256(a, i):
    return (a >> (256 * i)) & ((1 << 256) - 1)


def insert128(a, x, i, vl):
    m = ((1 << 128) - 1) << (128 * i)
    return ((a & ~m) | ((x & ((1 << 128) - 1)) << (128 * i))) & ((1 << vl) - 1)


def insert256(a, x, i):
    m = ((1 << 256) - 1) << (256 * i)
    return ((a & ~m) | ((x & ((1 << 256) - 1)) << (256 * i))) & ((1 << 512) - 1)


def broadcast128(x, vl):
    """VBROADCASTI32X4 / VBROADCASTI128: repeat a 128-bit value."""
    return pack([x & ((1 << 128) - 1)] * (vl // 128), 128)


def broadcast32(x, vl):
    return pack([x & MASK32] * (vl // 32), 32)


def blendvps(a, b, mask, vl):
    """(V)BLENDVPS(a, b, mask): lane = b if the mask lane's SIGN BIT is set, else a.
    A sign-driven select: it observes the sign bit of whatever is in `mask` (RULES.md NaN-order)."""
    A, B, M = lanes(a, 32, vl // 32), lanes(b, 32, vl // 32), lanes(mask, 32, vl // 32)
    return pack([B[i] if (M[i] >> 31) & 1 else A[i] for i in range(vl // 32)], 32)


def blend_k(a, b, k, vl, eb=32):
    """VBLENDMPS / masked VMOVAPS merge: lane = b if k[i] else a."""
    A, B = lanes(a, eb, vl // eb), lanes(b, eb, vl // eb)
    return pack([B[i] if (k >> i) & 1 else A[i] for i in range(vl // eb)], eb)


def maskmov_store(old_mem_lanes, v, mask, vl):
    """VMASKMOVPS store: lane i written iff the mask lane's sign bit is set; others untouched."""
    V, M = lanes(v, 32, vl // 32), lanes(mask, 32, vl // 32)
    return [V[i] if (M[i] >> 31) & 1 else old_mem_lanes[i] for i in range(vl // 32)]
