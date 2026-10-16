"""Vector register model (TABLE-SCHEMA.md §3): lanes, write masks, broadcast, scalar forms.

A register value is a Python int holding `vl` bits (128, 256 or 512); lane 0 is the least
significant. Opmask registers are ints with one bit per lane.

Write-mask semantics (EVEX {k}{z}, SDM Vol 1 §15.6 / Vol 2 §2.7.x):
  * active lane (k[i] = 1, or no mask): the lane result is written; its exceptions are recorded.
  * inactive lane, merge-masking: the destination lane keeps its old value; NO exception from it.
  * inactive lane, zero-masking {z}: the destination lane becomes 0; NO exception from it.
  * k0 as a write mask means "no masking" (encoding-level fact; callers pass k=None for it).
Upper-bit semantics (SDM Vol 1 §14.1.x / §15.5): VEX- and EVEX-encoded instructions zero the
destination bits above the operation's vector length up to the maximum (VLMAX = 512 here);
legacy SSE encodings leave those bits unchanged. Modeled in `write_dest`.
Memory fault suppression for masked-off lanes is a footprint fact for T1, not a value fact; it is
not modeled here (TABLE-SCHEMA.md §3); fuzz class F-MEMFAULT tests it on silicon (FUZZ-DESIGN.md §3.2).
"""
from .bits import MASK32


def lanes(v, eb, n):
    m = (1 << eb) - 1
    return [(v >> (eb * i)) & m for i in range(n)]


def pack(ls, eb):
    m = (1 << eb) - 1
    v = 0
    for i, x in enumerate(ls):
        v |= (x & m) << (eb * i)
    return v


def lanes32(v, vl):
    return lanes(v, 32, vl // 32)


def write_dest(old512, result, vl, encoding):
    """Combine an operation result of width vl into the full 512-bit register."""
    low_mask = (1 << vl) - 1
    if encoding == "legacy":
        return (old512 & ~low_mask & ((1 << 512) - 1)) | (result & low_mask)
    assert encoding in ("vex", "evex")
    return result & low_mask


def _apply(i, k, z, dlanes, compute):
    if k is not None and not (k >> i) & 1:
        return (0 if z else dlanes[i]), 0
    return compute()


def packed_fp1(lane_fn, a, env, vl, k=None, z=False, dst=0, src_eb=32, dst_eb=32):
    """Unary packed op (conversions). src_eb may differ from dst_eb (e.g. VCVTPH2PS: 16 -> 32)."""
    n = vl // dst_eb
    A = lanes(a, src_eb, n)
    D = lanes(dst, dst_eb, n)
    out, fl = [], 0
    for i in range(n):
        r, f = _apply(i, k, z, D, lambda: lane_fn(A[i], env))
        out.append(r)
        fl |= f
    return pack(out, dst_eb), (0 if env.sae else fl)


def packed_fp2(lane_fn, a, b, env, vl, k=None, z=False, dst=0, bcast_b=None):
    """Binary packed op on 32-bit lanes. bcast_b: a 32-bit scalar broadcast from memory ({1to16})."""
    n = vl // 32
    A = lanes32(a, vl)
    B = [bcast_b] * n if bcast_b is not None else lanes32(b, vl)
    D = lanes32(dst, vl)
    out, fl = [], 0
    for i in range(n):
        r, f = _apply(i, k, z, D, lambda: lane_fn(A[i], B[i], env))
        out.append(r)
        fl |= f
    return pack(out, 32), (0 if env.sae else fl)


def packed_cmp_vec(pred_fn, a, b, imm, env, vl):
    """VEX (V)CMPPS: each lane all-ones if the predicate holds, else zero."""
    out, fl = [], 0
    for x, y in zip(lanes32(a, vl), lanes32(b, vl)):
        t, f = pred_fn(x, y, imm, env)
        out.append(MASK32 if t else 0)
        fl |= f
    return pack(out, 32), (0 if env.sae else fl)


def packed_cmp_k(pred_fn, a, b, imm, env, vl, k=None, bcast_b=None):
    """EVEX VCMPPS k1 {k2}, ...: result bit i = k2[i] AND pred(a[i], b[i]); bits >= lanes are 0.
    Lanes with k2[i] = 0 are not compared and raise nothing (comparison into a mask is always
    zeroing)."""
    n = vl // 32
    A = lanes32(a, vl)
    B = [bcast_b] * n if bcast_b is not None else lanes32(b, vl)
    res, fl = 0, 0
    for i in range(n):
        if k is not None and not (k >> i) & 1:
            continue
        t, f = pred_fn(A[i], B[i], imm, env)
        res |= (1 if t else 0) << i
        fl |= f
    return res, (0 if env.sae else fl)


def scalar_fp2(lane_fn, src1, src2_low, env, k=None, z=False, dst=0):
    """(V)xxxSS forms on the low 128 bits: lane 0 = op(src1[0], src2[0]); lanes 1-3 from src1.
    EVEX masking applies to lane 0 only. Legacy SSE has src1 == dst (pass the same value)."""
    S1 = lanes32(src1, 128)
    s2 = src2_low & MASK32
    D = lanes32(dst, 128)
    if k is not None and not (k & 1):
        r, f = (0 if z else D[0]), 0
    else:
        r, f = lane_fn(S1[0], s2, env)
    return pack([r] + S1[1:], 32), (0 if env.sae else f)
