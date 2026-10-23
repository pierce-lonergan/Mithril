"""Lowering recipes for exact integer sums, scale loads, canon and stores (library L).

A recipe turns one meaning leaf into single-instruction calls. Recipes are generic over the block
format: element positions, code widths, value offsets and field offsets are read from the format
declaration, never written here. check_isum() is P5's precondition check: it proves with interval
arithmetic that no instruction saturates or wraps and that i2f stays exact (E1), or rejects.
"""

from .lp import Call, If, IX, Var, add, ix, mul
from .sched import PrimError

I16 = (-(1 << 15), (1 << 15) - 1)
I32 = (-(1 << 31), (1 << 31) - 1)
EXACT_F32 = 1 << 24


def _runs(F, group):
    """Element groups of `group` consecutive elements -> (byte offset, shift) of each group, or
    None if some group is not a contiguous byte run with one shift."""
    out = []
    for g0 in range(0, F.q.count, group):
        b0, s0 = F.q.locate(g0)
        for i in range(g0, g0 + group):
            b, s = F.q.locate(i)
            if s != s0 or b != b0 + (i - g0):
                return None
        out.append((b0, s0))
    return out


def _code_range(F, signed_mode):
    """Range of the unsigned multiplicand fed to an u8 x s8 instruction, and the bias that makes
    sum(u * x) - bias * sum(x) equal sum(w * x)."""
    q = F.q
    if q.bits < 8:
        return (0, q.mask), q.value_offset
    if q.signed and signed_mode == "bias":
        return (0, 255), 1 << (q.bits - 1)  # xor with the sign bit: u = w + 128
    if q.signed and signed_mode == "sign_transfer":
        return (0, 1 << (q.bits - 1)), 0  # |w|, multiplied by x * sgn(w)
    if not q.signed:
        return (0, 255), q.value_offset
    raise PrimError("P5: no unsigned form for this format")


def check_isum(kernel, using, opts):
    """P5 precondition: returns the list of proven facts, or raises PrimError."""
    F = kernel.params["W"][1]
    AF = kernel.params["A"][1]
    blk = kernel.params["block"]
    xlo, xhi = AF.q.value_bounds()
    xm = max(abs(xlo), abs(xhi))
    wlo, whi = F.q.value_bounds()
    wm = max(abs(wlo), abs(whi))
    facts = []
    ibound = blk * wm * xm
    if ibound >= EXACT_F32:
        raise PrimError("P5/E1: |I| <= %d is not below 2^24" % ibound)
    facts.append("E1: |I| <= %d*%d*%d = %d < 2^24, so i2f is exact" % (blk, wm, xm, ibound))
    if using == "scalar_loop":
        if ibound > I32[1]:
            raise PrimError("P5: int32 accumulation could wrap")
        facts.append("P5: scalar int32 sum of exact products; |partial| <= %d" % ibound)
        return facts
    signed_mode = opts.get("signed", "bias")
    (ulo, uhi), bias = _code_range(F, signed_mode)
    if bias and "A.sum == sum(A.q)" not in kernel.requires:
        raise PrimError("P5: the bias form needs PRE2 (A.sum == sum(A.q))")
    if signed_mode == "sign_transfer":
        if xlo < -127:
            raise PrimError("P5: sign transfer needs x in [-127, 127] (PRE1): sign(-128) overflows")
        facts.append(
            "P5: |w| * (x * sgn w) = w * x for w in [-128,127], x in [-127,127] (PRE1); "
            "re-proved by exhaustive enumeration in C3"
        )
    if using == "maddubs":
        if _runs(F, 32) is None:
            raise PrimError("P5: maddubs needs 32-element halves in contiguous byte runs")
        pair = 2 * uhi * xm
        if pair > I16[1]:
            raise PrimError("P5: maddubs pair bound %d > 32767: saturates" % pair)
        facts.append(
            "P5: maddubs pair |.| <= 2*%d*%d = %d <= 32767 (no saturation)" % (uhi, xm, pair)
        )
        if 2 * pair <= I16[1]:
            facts.append("P5: two halves summed in int16: |.| <= %d <= 32767" % (2 * pair))
        else:
            facts.append("P5: halves widened to int32 before adding (2*%d > 32767)" % pair)
    elif using == "dpbusd":
        if _runs(F, 16) is None:
            raise PrimError("P5: dpbusd needs 16-element blocks in contiguous byte runs")
        step = 4 * uhi * xm
        tot = blk * uhi * xm
        if tot > I32[1]:
            raise PrimError("P5: dpbusd partials could wrap int32")
        facts.append(
            "P5: dpbusd lane partials |.| <= %d per step, total <= %d < 2^31 (no wrap)"
            % (step, tot)
        )
    else:
        raise PrimError("P5: unknown integer recipe %r" % using)
    if bias:
        facts.append(
            "P5: bias identity sum(u*x) - %d*sum(x) = sum(w*x), with sum(x) = A.sum by PRE2" % bias
        )
    return facts


# ======================================================================= emission helpers


def _ptr(base, *offs):
    p = base
    for o in offs:
        p = add(p, o)
    return p


class IsumScalar:
    """Exact integer sum as a scalar loop over the code bytes (the scalar variant)."""

    def __init__(self, cx, opts, prov):
        self.cx, self.prov = cx, prov

    def decode(self, rows, go):
        return {"rows": rows, "go": go}

    def dot(self, dec, aptr):
        cx, F, AF, p = self.cx, self.cx.F, self.cx.AF, self.prov
        em = cx.em
        cp = _ptr(dec["rows"][0], dec["go"], F.q.offset)
        xp = _ptr(aptr, AF.q.offset)
        isum = em.call("i32.zero", base="isum", mut=True, prov=p)
        per_byte = 8 // F.q.bits
        stride = F.q.hi_at if F.q.bits < 8 else 0
        j = em.fresh("j")
        with em.loop(j, 0, F.q.nbytes, prov=p) as jv:
            b = em.call("ld.s8" if F.q.signed else "ld.u8", add(cp, jv), base="b", prov=p)
            for k in range(per_byte):
                i_off = k * stride
                shift = k * F.q.bits
                assert all(F.q.locate(j_ + i_off) == (j_, shift) for j_ in range(F.q.nbytes))
                c = b
                if shift:
                    c = em.call("i32.shr", c, shift, base="c", prov=p)
                if shift + F.q.bits < 8:
                    c = em.call("i32.and", c, F.q.mask, base="c", prov=p)
                if F.q.value_offset:
                    c = em.call("i32.sub", c, F.q.value_offset, base="c", prov=p)
                x = em.call("ld.s8", add(xp, add(jv, i_off)), base="x", prov=p)
                m = em.call("i32.mul", c, x, base="m", prov=p)
                em.set(isum, Call("i32.add", (isum, m)), prov=p)
        return isum


class IsumMaddubs:
    """u8 x s8 pair products (maddubs), widened with madd, rows transposed by an hadd tree.
    Lanes = rows; 256-bit vectors; 32 elements per vector."""

    def __init__(self, cx, opts, prov):
        self.cx, self.prov = cx, prov
        self.mode = opts.get("signed", "bias")
        self.reduce = opts.get("reduce", "hadd")
        F = cx.F
        (_, uhi), self.bias = _code_range(F, self.mode)
        xm = max(abs(v) for v in cx.AF.q.value_bounds())
        self.i16_combine = 2 * (2 * uhi * xm) <= I16[1]
        self.halves = _runs(F, 32)
        if cx.width != 256 or cx.tile.lanes != 8 or self.reduce != "hadd":
            raise PrimError("maddubs recipe: implemented for 256-bit vectors of 8 rows (hadd)")

    def _consts(self):
        em, F, p = self.cx.em, self.cx.F, self.prov
        c = {"ones": em.const("_mm256_set1_epi16", 1, base="ones", prov=p)}
        if F.q.bits < 8:
            c["mask"] = em.const("_mm256_set1_epi8", F.q.mask, base="cmask", prov=p)
        return c

    def decode_row(self, rowptr, go):
        em, F, p = self.cx.em, self.cx.F, self.prov
        c = self._consts()
        loads = {}
        out = []
        for b0, sh in self.halves:
            if b0 not in loads:
                loads[b0] = em.call(
                    "_mm256_loadu_si256", _ptr(rowptr, go, F.q.offset + b0), base="wv", prov=p
                )
            v = loads[b0]
            if F.q.bits < 8:
                if sh:
                    v = em.call("_mm256_srli_epi16", v, sh, base="ws", prov=p)
                u = em.call("_mm256_and_si256", v, c["mask"], base="wu", prov=p)
                out.append((u, None))
            elif self.mode == "sign_transfer":
                u = em.call("_mm256_abs_epi8", v, base="wa", prov=p)
                out.append((u, v))
            else:
                raise PrimError("maddubs recipe: signed 8-bit codes need sign_transfer")
        return out

    def decode(self, rows, go):
        return [self.decode_row(r, go) for r in rows]

    def dot(self, dec, aptr, rows=None, go=None):
        em, AF, p = self.cx.em, self.cx.AF, self.prov
        c = self._consts()
        xs = [
            em.call("_mm256_loadu_si256", _ptr(aptr, AF.q.offset + 32 * h), base="x", prov=p)
            for h in range(len(self.halves))
        ]
        sums = []
        for k in range(8):
            d = dec[k] if dec is not None else self.decode_row(rows[k], go)
            prods = []
            for h, (u, w) in enumerate(d):
                xx = xs[h]
                if w is not None:
                    xx = em.call("_mm256_sign_epi8", xs[h], w, base="xs", prov=p)
                prods.append(em.call("_mm256_maddubs_epi16", u, xx, base="pp", prov=p))
            if self.i16_combine:
                acc16 = prods[0]
                for q in prods[1:]:
                    acc16 = em.call("_mm256_add_epi16", acc16, q, base="ps", prov=p)
                s = em.call("_mm256_madd_epi16", acc16, c["ones"], base="s", prov=p)
            else:
                s = None
                for q in prods:
                    w32 = em.call("_mm256_madd_epi16", q, c["ones"], base="pw", prov=p)
                    s = w32 if s is None else em.call("_mm256_add_epi32", s, w32, base="s", prov=p)
            sums.append(s)
        h = [
            em.call("_mm256_hadd_epi32", sums[2 * i], sums[2 * i + 1], base="h", prov=p)
            for i in range(4)
        ]
        a = em.call("_mm256_hadd_epi32", h[0], h[1], base="ha", prov=p)
        b = em.call("_mm256_hadd_epi32", h[2], h[3], base="hb", prov=p)
        lo = em.call("_mm256_permute2x128_si256", a, b, 0x20, base="hl", prov=p)
        hi = em.call("_mm256_permute2x128_si256", a, b, 0x31, base="hh", prov=p)
        isum = em.call("_mm256_add_epi32", lo, hi, base="is", prov=p)
        return _bias(self.cx, isum, aptr, self.bias, 256, p)


def _bias(cx, isum, aptr, bias, width, p):
    if not bias:
        return isum
    em, AF = cx.em, cx.AF
    s = em.call("ld.i32", _ptr(aptr, AF.sum.offset), base="xsum", prov=p)
    sb = em.call("i32.mul", s, bias, base="xb", prov=p)
    pre = {128: "_mm_", 256: "_mm256_", 512: "_mm512_"}[width]
    bv = em.call(pre + "set1_epi32", sb, base="bv", prov=p)
    return em.call(pre + "sub_epi32", isum, bv, base="is", prov=p)


class IsumDpbusd:
    """u8 x s8 quadruple dot products (vpdpbusd). Rows sit one per 128-bit lane in quads; element
    block e (16 elements) of 4 rows forms one 512-bit operand. reduce 'unpack' restores lane = row
    over 4 quads (16 rows); reduce 'permute' folds one quad into a 128-bit vector (4 rows)."""

    def __init__(self, cx, opts, prov):
        self.cx, self.prov = cx, prov
        self.mode = opts.get("signed", "bias")
        self.reduce = opts.get("reduce")
        (_, _), self.bias = _code_range(cx.F, self.mode)
        if self.mode != "bias":
            raise PrimError("dpbusd recipe: needs unsigned codes (bias form)")
        self.blocks = _runs(cx.F, 16)
        lanes = cx.tile.lanes
        if self.reduce == "unpack" and (cx.width, lanes) == (512, 16):
            self.quads = [[j, j + 4, j + 8, j + 12] for j in range(4)]
        elif self.reduce == "permute" and (cx.width, lanes) == (128, 4):
            self.quads = [[0, 1, 2, 3]]
        else:
            raise PrimError("dpbusd recipe: (width, lanes, reduce) not implemented")

    def decode(self, rows, go):
        em, F, p = self.cx.em, self.cx.F, self.prov
        if F.q.bits < 8:
            mask = em.const("_mm512_set1_epi8", F.q.mask, base="cmask", prov=p)
        else:
            sbit = em.const("_mm512_set1_epi8", 1 << (F.q.bits - 1), base="csign", prov=p)
        out = []
        for quad in self.quads:
            a, b, c, d = (rows[i] for i in quad)
            pairs, zs, us = {}, {}, []
            for b0, sh in self.blocks:
                base32, half = 32 * (b0 // 32), (b0 % 32) // 16
                if base32 not in pairs:
                    off = F.q.offset + base32
                    la = em.call("_mm256_loadu_si256", _ptr(a, go, off), base="wl", prov=p)
                    lb = em.call("_mm256_loadu_si256", _ptr(b, go, off), base="wl", prov=p)
                    lc = em.call("_mm256_loadu_si256", _ptr(c, go, off), base="wl", prov=p)
                    ld = em.call("_mm256_loadu_si256", _ptr(d, go, off), base="wl", prov=p)
                    za = em.call("_mm512_castsi256_si512", la, base="wz", prov=p)
                    ab = em.call("_mm512_inserti64x4", za, lb, 1, base="wab", prov=p)
                    zc = em.call("_mm512_castsi256_si512", lc, base="wz", prov=p)
                    cd = em.call("_mm512_inserti64x4", zc, ld, 1, base="wcd", prov=p)
                    pairs[base32] = (ab, cd)
                if (base32, half) not in zs:
                    ab, cd = pairs[base32]
                    zs[(base32, half)] = em.call(
                        "_mm512_shuffle_i64x2",
                        ab,
                        cd,
                        0x88 if half == 0 else 0xDD,
                        base="wq",
                        prov=p,
                    )
                z = zs[(base32, half)]
                if F.q.bits < 8:
                    if sh:
                        z = em.call("_mm512_srli_epi16", z, sh, base="ws", prov=p)
                    u = em.call("_mm512_and_si512", z, mask, base="wu", prov=p)
                else:
                    u = em.call("_mm512_xor_si512", z, sbit, base="wu", prov=p)
                us.append(u)
            out.append(us)
        return out

    def dot(self, dec, aptr, rows=None, go=None):
        em, AF, p = self.cx.em, self.cx.AF, self.prov
        if dec is None:
            dec = self.decode(rows, go)
        xs = []
        for e in range(len(self.blocks)):
            xl = em.call("_mm_loadu_si128", _ptr(aptr, AF.q.offset + 16 * e), base="xl", prov=p)
            xs.append(em.call("_mm512_broadcast_i32x4", xl, base="x", prov=p))
        dots = []
        for us in dec:
            acc = em.const("_mm512_setzero_si512", base="izero", prov=p)
            for e, u in enumerate(us):
                acc = em.call("_mm512_dpbusd_epi32", acc, u, xs[e], base="dq", prov=p)
            dots.append(acc)
        if self.reduce == "unpack":
            v0, v1, v2, v3 = dots
            l01 = em.call("_mm512_unpacklo_epi32", v0, v1, base="ru", prov=p)
            h01 = em.call("_mm512_unpackhi_epi32", v0, v1, base="ru", prov=p)
            s01 = em.call("_mm512_add_epi32", l01, h01, base="rs", prov=p)
            l23 = em.call("_mm512_unpacklo_epi32", v2, v3, base="ru", prov=p)
            h23 = em.call("_mm512_unpackhi_epi32", v2, v3, base="ru", prov=p)
            s23 = em.call("_mm512_add_epi32", l23, h23, base="rs", prov=p)
            lo = em.call("_mm512_unpacklo_epi64", s01, s23, base="ru", prov=p)
            hi = em.call("_mm512_unpackhi_epi64", s01, s23, base="ru", prov=p)
            isum = em.call("_mm512_add_epi32", lo, hi, base="is", prov=p)
            return _bias(self.cx, isum, aptr, self.bias, 512, p)
        v = dots[0]
        idx = em.const("_mm512_setr_epi32", *([0, 4, 8, 12] * 4), base="ridx", prov=p)
        t1 = em.call("_mm512_shuffle_epi32", v, 0x4E, base="rp", prov=p)
        v = em.call("_mm512_add_epi32", v, t1, base="rs", prov=p)
        t2 = em.call("_mm512_shuffle_epi32", v, 0xB1, base="rp", prov=p)
        v = em.call("_mm512_add_epi32", v, t2, base="rs", prov=p)
        pv = em.call("_mm512_permutexvar_epi32", idx, v, base="rv", prov=p)
        isum = em.call("_mm512_castsi512_si128", pv, base="is", prov=p)
        return _bias(self.cx, isum, aptr, self.bias, 128, p)


ISUM = {"scalar_loop": IsumScalar, "maddubs": IsumMaddubs, "dpbusd": IsumDpbusd}


# ======================================================================= scales (P14)


def _pack4(cx, rows, go, p):
    """Four f16 scales in one u64, lane 0 lowest."""
    em, F = cx.em, cx.F
    acc = None
    for k, r in enumerate(rows):
        s = em.call("ld.u16", _ptr(r, go, F.d.offset), base="sc", prov=p)
        if k:
            s = em.call("u64.shl", s, 16 * k, base="sc", prov=p)
            acc = em.call("u64.or", acc, s, base="sp", prov=p)
        else:
            acc = s
    return acc


def scales(cx, rows, go, pack, p):
    """h2f of the tile rows' block scales, lane k = row k."""
    em, F = cx.em, cx.F
    if F.d.kind != "f16":
        raise PrimError("P14: scale field is not f16")
    w = cx.width
    if w is None:
        s = em.call("ld.u16", _ptr(rows[0], go, F.d.offset), base="sc", prov=p)
        return em.call("scalar.h2f_bits", s, base="dw", prov=p)
    lanes = cx.tile.lanes
    if (w, lanes) == (256, 8):
        lo = _pack4(cx, rows[0:4], go, p)
        hi = _pack4(cx, rows[4:8], go, p)
        h = em.call("_mm_set_epi64x", hi, lo, base="hs", prov=p)
        return em.call("_mm256_cvtph_ps", h, base="dw", prov=p)
    if (w, lanes) == (512, 16):
        q = [_pack4(cx, rows[4 * i : 4 * i + 4], go, p) for i in range(4)]
        h0 = em.call("_mm_set_epi64x", q[1], q[0], base="hs", prov=p)
        h1 = em.call("_mm_set_epi64x", q[3], q[2], base="hs", prov=p)
        c0 = em.call("_mm256_castsi128_si256", h0, base="hc", prov=p)
        h = em.call("_mm256_inserti128_si256", c0, h1, 1, base="hs", prov=p)
        return em.call("_mm512_cvtph_ps", h, base="dw", prov=p)
    if (w, lanes) == (128, 4):
        q = _pack4(cx, rows[0:4], go, p)
        h = em.call("_mm_cvtsi64_si128", q, base="hs", prov=p)
        return em.call("_mm_cvtph_ps", h, base="dw", prov=p)
    raise PrimError("P14: scale packing for (%r, %r) not implemented" % (w, lanes))


# ======================================================================= canon (P13), stores


def canon(cx, lowering, v, p):
    em, w = cx.em, cx.width
    nan = 0x7FC00000  # the canonical quiet NaN of the meaning (canon)
    if w is None:
        if lowering != "branch":
            raise PrimError("P13: scalar canon must be 'branch'")
        isn = em.call("f32.isnan", v, base="isn", prov=p)
        nv = em.call("f32.bits", nan, base="qnan", prov=p)
        return em.call("f32.select", isn, nv, v, base="cv", prov=p)
    pre = {128: "_mm_", 256: "_mm256_", 512: "_mm512_"}[w]
    if lowering == "blendv" and w == 256:
        m = em.call("_mm256_cmp_ps_unord", v, v, base="isn", prov=p)
        ni = em.const("_mm256_set1_epi32", nan, base="qnani", prov=p)
        nf = em.const("_mm256_castsi256_ps", ni, base="qnan", prov=p)
        return em.call("_mm256_blendv_ps", v, nf, m, base="cv", prov=p)
    if lowering == "mask_mov" and w in (128, 512):
        k = em.call(pre + "cmp_ps_mask_unord", v, v, base="isn", prov=p)
        ni = em.const(pre + "set1_epi32", nan, base="qnani", prov=p)
        nf = em.const(
            "_mm512_castsi512_ps" if w == 512 else "_mm_castsi128_ps", ni, base="qnan", prov=p
        )
        return em.call(pre + "mask_mov_ps", v, k, nf, base="cv", prov=p)
    raise PrimError("P13: canon lowering %r unavailable at width %r" % (lowering, w))


def store(cx, yptr, v, p):
    em, w = cx.em, cx.width
    if w is None:
        em.do("f32.store", yptr, v, prov=p)
        return
    kind = cx.tile.store
    pre = {128: "_mm_", 256: "_mm256_", 512: "_mm512_"}[w]
    if kind == "full":
        em.do(pre + "storeu_ps", yptr, v, prov=p)
    elif kind == "mask" and w == 256:
        full, part = [], []
        with em.into(full):
            em.do("_mm256_storeu_ps", yptr, v, prov=p)
        with em.into(part):
            em.do("_mm256_maskstore_ps", yptr, cx.tile.smask, v, prov=p)
        em.emit(If(ix("==", cx.tile.nr, cx.tile.lanes), full, part, prov=p))
    elif kind == "kmask" and w == 128:
        em.do("_mm_mask_storeu_ps", yptr, cx.tile.kmask, v, prov=p)
    else:
        raise PrimError("store kind %r unavailable at width %r" % (kind, w))


__all__ = ["check_isum", "ISUM", "scales", "canon", "store", "Var", "mul"]
