/* x2ref.c -- C reference interpreter of the X2 semantics table. See x2ref.h for the exactness
 * argument. Every function names the Python function it ports; behaviour must match bit for bit
 * (validate_interp.py checks it on >= 10^6 random lane cases before the interpreter is used). */
#include "x2ref.h"

#include <string.h>

#define SIGN 0x80000000u
#define EXPM 0x7F800000u
#define FRAC 0x007FFFFFu
#define QUIET 0x00400000u
#define PINF 0x7F800000u
#define NINF 0xFF800000u
#define FMAX 0x7F7FFFFFu
#define QNAN_INDEF 0xFFC00000u
#define I32_INDEF 0x80000000u
#define MXCSR_MASKS 0x1F80u

/* ------------------------------------------------------------------ fpenv.py Env */
int x2_env_make(x2env *e, uint32_t mxcsr, int er, int sae) {
    if ((mxcsr & MXCSR_MASKS) != MXCSR_MASKS) return -1;   /* #XM: outside the model */
    if (mxcsr & ~0xFFFFu) return -1;                        /* reserved bits: #GP on LDMXCSR */
    e->mxcsr = mxcsr;
    e->daz = (mxcsr >> 6) & 1;
    e->ftz = (mxcsr >> 15) & 1;
    if (er >= 0) { e->rc = er; e->er = 1; e->sae = 1; }   /* {er} implies {sae} */
    else { e->rc = (mxcsr >> 13) & 3; e->er = 0; e->sae = sae ? 1 : 0; }
    return 0;
}

/* ------------------------------------------------------------------ bits.py */
int x2_is_nan(uint32_t b) { return (b & EXPM) == EXPM && (b & FRAC) != 0; }
int x2_is_snan(uint32_t b) { return x2_is_nan(b) && !(b & QUIET); }
static int is_inf(uint32_t b) { return (b & 0x7FFFFFFFu) == PINF; }
static int is_zero(uint32_t b) { return (b & 0x7FFFFFFFu) == 0; }
int x2_is_denormal(uint32_t b) { return (b & EXPM) == 0 && (b & FRAC) != 0; }
static uint32_t sgn(uint32_t b) { return b >> 31; }

/* finite, nonzero or zero: value = M * 2^E */
static void decode(uint32_t b, uint64_t *M, int *E) {
    uint32_t e8 = (b >> 23) & 0xFF, f = b & FRAC;
    if (e8 == 0) { *M = f; *E = -149; }
    else { *M = (uint64_t)(f | 0x800000u); *E = (int)e8 - 150; }
}

static int bitlen64(uint64_t x) { int n = 0; while (x) { n++; x >>= 1; } return n; }

/* ------------------------------------------------------------------ rounding.py */
/* round_to_integer applied to M / 2^sh: returns q, sets *inexact. */
static uint64_t round_shift(uint64_t M, int sh, int rc, int neg, int *inexact) {
    uint64_t q, rem;
    int cmp_half;   /* rem vs 2^(sh-1): -1 below, 0 equal, 1 above */
    if (sh <= 0) { *inexact = 0; return M << (-sh); }
    if (sh < 64) {
        uint64_t half = 1ull << (sh - 1);
        q = M >> sh;
        rem = M & ((1ull << sh) - 1);
        cmp_half = rem > half ? 1 : (rem == half ? 0 : -1);
    } else {
        q = 0;
        rem = M;
        if (sh == 64) cmp_half = rem > 0x8000000000000000ull ? 1 : (rem == 0x8000000000000000ull ? 0 : -1);
        else cmp_half = -1;
    }
    if (rem == 0) { *inexact = 0; return q; }
    *inexact = 1;
    switch (rc) {
    case X2_RNE: if (cmp_half > 0) q += 1; else if (cmp_half == 0) q += (q & 1); break;
    case X2_RZ: break;
    case X2_RD: if (neg) q += 1; break;
    case X2_RU: if (!neg) q += 1; break;
    }
    return q;
}

static uint32_t overflow_result(int neg, int rc) {
    int mag_inf;
    if (rc == X2_RNE) mag_inf = 1;
    else if (rc == X2_RZ) mag_inf = 0;
    else if (rc == X2_RD) mag_inf = neg;
    else mag_inf = !neg;
    if (mag_inf) return neg ? NINF : PINF;
    return neg ? (SIGN | FMAX) : FMAX;
}

/* round_f32: nonzero magnitude M * 2^E (M may carry a sticky stand-in, see x2ref.h). */
static uint32_t round_pack(int neg, uint64_t M, int E, int rc, int ftz, uint32_t *fl) {
    uint32_t sb = neg ? SIGN : 0;
    int L = bitlen64(M), e = L - 1 + E, inexact;
    uint64_t m = round_shift(M, L - 24, rc, neg, &inexact);
    if (m == (1ull << 24)) { m = 1ull << 23; e += 1; }
    if (e > 127) { *fl |= X2_OE | X2_PE; return overflow_result(neg, rc); }
    if (e < -126) {                                   /* tiny, detected after rounding */
        int inex2;
        uint64_t ms;
        if (ftz) { *fl |= X2_UE | X2_PE; return sb; }
        ms = round_shift(M, -149 - E, rc, neg, &inex2);
        if (inex2) *fl |= X2_UE | X2_PE;
        return sb | (uint32_t)ms;                     /* ms == 2^23 encodes the smallest normal */
    }
    if (inexact) *fl |= X2_PE;
    return sb | ((uint32_t)(e + 127) << 23) | (uint32_t)(m - (1ull << 23));
}

/* ------------------------------------------------------------------ fp_ops.py */
static uint32_t quiet(uint32_t b) { return b | QUIET; }

static uint32_t nan_select(uint32_t a, uint32_t b, uint32_t *fl) {
    if (x2_is_snan(a) || x2_is_snan(b)) *fl |= X2_IE;
    return x2_is_nan(a) ? quiet(a) : quiet(b);
}

static uint32_t daz(uint32_t b, const x2env *e, uint32_t *f) {
    if (x2_is_denormal(b)) {
        if (e->daz) return b & SIGN;
        *f |= X2_DE;
    }
    return b;
}

uint32_t x2_add(uint32_t a, uint32_t b, const x2env *e, uint32_t *fl) {
    uint32_t f = 0;
    uint64_t Ma, Mb, Mx, My, S;
    int Ea, Eb, Ex, Ey, sx, sy, d, neg;
    if (x2_is_nan(a) || x2_is_nan(b)) return nan_select(a, b, fl);
    a = daz(a, e, &f);
    b = daz(b, e, &f);
    if (is_inf(a) && is_inf(b)) {
        if (sgn(a) != sgn(b)) { *fl |= X2_IE; return QNAN_INDEF; }
        *fl |= f;
        return a;
    }
    if (is_inf(a)) { *fl |= f; return a; }
    if (is_inf(b)) { *fl |= f; return b; }
    decode(a, &Ma, &Ea);
    decode(b, &Mb, &Eb);
    if (Ma == 0 && Mb == 0) {                         /* exact zero sum: IEEE 754 sec. 6.3 */
        uint32_t s;
        if (sgn(a) == sgn(b)) s = sgn(a);
        else s = (e->rc == X2_RD) ? 1u : 0u;
        *fl |= f;
        return s ? SIGN : 0;
    }
    if (Ma == 0) { *fl |= f; return round_pack((int)sgn(b), Mb, Eb, e->rc, e->ftz, fl) ; }
    if (Mb == 0) { *fl |= f; return round_pack((int)sgn(a), Ma, Ea, e->rc, e->ftz, fl) ; }
    if (Ea >= Eb) { Mx = Ma; Ex = Ea; sx = (int)sgn(a); My = Mb; Ey = Eb; sy = (int)sgn(b); }
    else { Mx = Mb; Ex = Eb; sx = (int)sgn(b); My = Ma; Ey = Ea; sy = (int)sgn(a); }
    d = Ex - Ey;
    if (d > 40) { Mx <<= 40; My = 1; Ey = Ex - 40; }   /* sticky stand-in, see x2ref.h */
    else { Mx <<= d; }
    /* both now at exponent Ey */
    if (sx == sy) { S = Mx + My; neg = sx; }
    else if (Mx > My) { S = Mx - My; neg = sx; }
    else if (My > Mx) { S = My - Mx; neg = sy; }
    else {                                             /* exact cancellation of nonzero values */
        *fl |= f;
        return (e->rc == X2_RD) ? SIGN : 0;
    }
    *fl |= f;
    return round_pack(neg, S, Ey, e->rc, e->ftz, fl);
}

uint32_t x2_sub(uint32_t a, uint32_t b, const x2env *e, uint32_t *fl) {
    if (x2_is_nan(a) || x2_is_nan(b)) return nan_select(a, b, fl);
    return x2_add(a, b ^ SIGN, e, fl);
}

uint32_t x2_mul(uint32_t a, uint32_t b, const x2env *e, uint32_t *fl) {
    uint32_t f = 0, s;
    uint64_t Ma, Mb;
    int Ea, Eb, ia, ib, za, zb;
    if (x2_is_nan(a) || x2_is_nan(b)) return nan_select(a, b, fl);
    a = daz(a, e, &f);
    b = daz(b, e, &f);
    s = sgn(a) ^ sgn(b);
    ia = is_inf(a); ib = is_inf(b); za = is_zero(a); zb = is_zero(b);
    if ((ia && zb) || (ib && za)) { *fl |= X2_IE; return QNAN_INDEF; }
    *fl |= f;
    if (ia || ib) return s ? NINF : PINF;
    if (za || zb) return s ? SIGN : 0;
    decode(a, &Ma, &Ea);
    decode(b, &Mb, &Eb);
    return round_pack((int)s, Ma * Mb, Ea + Eb, e->rc, e->ftz, fl);
}

uint32_t x2_div(uint32_t a, uint32_t b, const x2env *e, uint32_t *fl) {
    uint32_t f = 0, s;
    uint64_t Ma, Mb, num, Q, R;
    int Ea, Eb, ia, ib, za, zb;
    if (x2_is_nan(a) || x2_is_nan(b)) return nan_select(a, b, fl);
    a = daz(a, e, &f);
    b = daz(b, e, &f);
    s = sgn(a) ^ sgn(b);
    ia = is_inf(a); ib = is_inf(b); za = is_zero(a); zb = is_zero(b);
    if ((ia && ib) || (za && zb)) { *fl |= X2_IE; return QNAN_INDEF; }
    if (ia) { *fl |= f; return s ? NINF : PINF; }
    if (ib) { *fl |= f; return s ? SIGN : 0; }
    if (zb) { *fl |= X2_ZE; return s ? NINF : PINF; }   /* B6 correction 2026-10-23: ZE alone (fp_ops.div) */
    if (za) { *fl |= f; return s ? SIGN : 0; }
    decode(a, &Ma, &Ea);
    decode(b, &Mb, &Eb);
    while (Ma < (1ull << 23)) { Ma <<= 1; Ea -= 1; }
    while (Mb < (1ull << 23)) { Mb <<= 1; Eb -= 1; }
    num = Ma << 40;
    Q = num / Mb;
    R = num % Mb;
    *fl |= f;
    return round_pack((int)s, (Q << 1) | (R != 0 ? 1u : 0u), Ea - Eb - 41, e->rc, e->ftz, fl);
}

/* total order key on non-NaN values; +0 and -0 equal */
static int64_t okey(uint32_t x) {
    int64_t m = (int64_t)(x & 0x7FFFFFFFu);
    return (x & SIGN) ? -m : m;
}

static uint32_t minmax(uint32_t a, uint32_t b, const x2env *e, int want_greater, uint32_t *fl) {
    uint32_t f = 0;
    int take_a;
    if (x2_is_nan(a) || x2_is_nan(b)) {
        if (e->daz && x2_is_denormal(b)) b &= SIGN;
        *fl |= X2_IE;
        return b;
    }
    a = daz(a, e, &f);
    b = daz(b, e, &f);
    *fl |= f;
    if (is_zero(a) && is_zero(b)) return b;
    take_a = want_greater ? (okey(a) > okey(b)) : (okey(a) < okey(b));
    return take_a ? a : b;
}
uint32_t x2_max(uint32_t a, uint32_t b, const x2env *e, uint32_t *fl) { return minmax(a, b, e, 1, fl); }
uint32_t x2_min(uint32_t a, uint32_t b, const x2env *e, uint32_t *fl) { return minmax(a, b, e, 0, fl); }

static const struct { int rel_true, sig; } CMP_PRED[32] = {
    {2, 0}, {1, 1}, {3, 1}, {8, 0}, {13, 0}, {14, 1}, {12, 1}, {7, 0},
    {10, 0}, {9, 1}, {11, 1}, {0, 0}, {5, 0}, {6, 1}, {4, 1}, {15, 0},
    {2, 1}, {1, 0}, {3, 0}, {8, 1}, {13, 1}, {14, 0}, {12, 0}, {7, 1},
    {10, 1}, {9, 0}, {11, 0}, {0, 1}, {5, 1}, {6, 0}, {4, 0}, {15, 1},
};

int x2_relation(uint32_t a, uint32_t b, const x2env *e, int signalling, uint32_t *fl) {
    uint32_t f = 0;
    int64_t ka, kb;
    if (x2_is_nan(a) || x2_is_nan(b)) {
        if (signalling || x2_is_snan(a) || x2_is_snan(b)) *fl |= X2_IE;
        return X2_REL_UN;
    }
    a = daz(a, e, &f);
    b = daz(b, e, &f);
    *fl |= f;
    ka = okey(a); kb = okey(b);
    if (ka == kb) return X2_REL_EQ;
    return ka < kb ? X2_REL_LT : X2_REL_GT;
}

int x2_cmp_pred(uint32_t a, uint32_t b, int imm, const x2env *e, uint32_t *fl) {
    int p = imm & 31;
    int rel = x2_relation(a, b, e, CMP_PRED[p].sig, fl);
    return (rel & CMP_PRED[p].rel_true) != 0;
}

void x2_comis(uint32_t a, uint32_t b, const x2env *e, int signalling, int *zf, int *pf, int *cf,
              uint32_t *fl) {
    int rel = x2_relation(a, b, e, signalling, fl);
    switch (rel) {
    case X2_REL_UN: *zf = 1; *pf = 1; *cf = 1; break;
    case X2_REL_GT: *zf = 0; *pf = 0; *cf = 0; break;
    case X2_REL_LT: *zf = 0; *pf = 0; *cf = 1; break;
    default: *zf = 1; *pf = 0; *cf = 0; break;
    }
}

uint32_t x2_cvt_i2f(uint32_t i, const x2env *e, uint32_t *fl) {
    int32_t v = (int32_t)i;
    uint64_t mag;
    if (v == 0) return 0;
    mag = v < 0 ? (uint64_t)(-(int64_t)v) : (uint64_t)v;
    return round_pack(v < 0, mag, 0, e->rc, 0, fl);
}

uint32_t x2_cvt_i64_2f(uint64_t i, const x2env *e, uint32_t *fl) {
    int neg = (i >> 63) != 0;
    uint64_t mag;
    if (i == 0) return 0;
    mag = neg ? (0ull - i) : i;            /* 2^63 for INT64_MIN: round_pack takes a full 64-bit magnitude */
    return round_pack(neg, mag, 0, e->rc, 0, fl);
}

uint32_t x2_cvt_f2i(uint32_t b, const x2env *e, int trunc, uint32_t *fl) {
    uint64_t M, n;
    int E, neg, rc, inexact = 0;
    if (x2_is_nan(b) || is_inf(b)) { *fl |= X2_IE; return I32_INDEF; }
    if (x2_is_denormal(b) && e->daz) b &= SIGN;
    decode(b, &M, &E);
    neg = (int)sgn(b) && M != 0;          /* -0 is not negative (Python: v < 0) */
    rc = trunc ? X2_RZ : e->rc;
    if (M == 0) return 0;
    if (E >= 0) {
        if (E > 31) { *fl |= X2_IE; return I32_INDEF; }
        n = M << E;
    } else {
        n = round_shift(M, -E, rc, neg, &inexact);
    }
    if (neg ? (n > 0x80000000ull) : (n > 0x7FFFFFFFull)) { *fl |= X2_IE; return I32_INDEF; }
    if (inexact) *fl |= X2_PE;
    return neg ? (uint32_t)(0u - (uint32_t)n) : (uint32_t)n;
}

uint32_t x2_cvt_h2f(uint32_t h, const x2env *e, uint32_t *fl) {
    uint32_t sign = (h >> 15) & 1, e5 = (h >> 10) & 0x1F, m = h & 0x3FF, dummy = 0;
    (void)e;
    if (e5 == 0x1F && m) {
        if (!(h & 0x200)) *fl |= X2_IE;
        return (sign << 31) | 0x7F800000u | (m << 13) | QUIET;
    }
    if (e5 == 0x1F) return sign ? NINF : PINF;
    if (e5 == 0 && m == 0) return sign ? SIGN : 0;
    if (e5 == 0) return round_pack((int)sign, m, -24, X2_RZ, 0, &dummy);   /* exact */
    return (sign << 31) | ((e5 + 112) << 23) | (m << 13);
}

/* ------------------------------------------------------------------ int_ops.py */
static int32_t sat16(int32_t v) { return v > 32767 ? 32767 : (v < -32768 ? -32768 : v); }

uint16_t x2_maddubs_word(uint8_t a0, uint8_t a1, uint8_t b0, uint8_t b1) {
    return (uint16_t)sat16((int32_t)a1 * (int8_t)b1 + (int32_t)a0 * (int8_t)b0);
}

void x2_pmaddubsw(const x2reg *a, const x2reg *b, int vl, x2reg *r) {
    x2reg t;
    int i;
    memset(&t, 0, sizeof t);
    for (i = 0; i < vl / 16; i++) t.w[i] = x2_maddubs_word(a->b[2 * i], a->b[2 * i + 1], b->b[2 * i], b->b[2 * i + 1]);
    *r = t;
}

void x2_pmaddwd(const x2reg *a, const x2reg *b, int vl, x2reg *r) {
    x2reg t;
    int i;
    memset(&t, 0, sizeof t);
    for (i = 0; i < vl / 32; i++) {
        int64_t s = (int64_t)(int16_t)a->w[2 * i + 1] * (int16_t)b->w[2 * i + 1] +
                    (int64_t)(int16_t)a->w[2 * i] * (int16_t)b->w[2 * i];
        t.d[i] = (uint32_t)(s & 0xFFFFFFFFll);
    }
    *r = t;
}

uint32_t x2_dpbusd_lane(uint32_t acc, const uint8_t *a4, const uint8_t *b4, int saturate) {
    int64_t s = (int32_t)acc;
    int j;
    for (j = 0; j < 4; j++) s += (int64_t)a4[j] * (int8_t)b4[j];
    if (saturate) s = s > 2147483647ll ? 2147483647ll : (s < -2147483648ll ? -2147483648ll : s);
    return (uint32_t)(s & 0xFFFFFFFFll);
}

void x2_pdpbusd(const x2reg *acc, const x2reg *a, const x2reg *b, int vl, int saturate, x2reg *r) {
    x2reg t;
    int i;
    memset(&t, 0, sizeof t);
    for (i = 0; i < vl / 32; i++) t.d[i] = x2_dpbusd_lane(acc->d[i], &a->b[4 * i], &b->b[4 * i], saturate);
    *r = t;
}

void x2_phaddd(const x2reg *a, const x2reg *b, int vl, x2reg *r) {
    x2reg t;
    int L;
    memset(&t, 0, sizeof t);
    for (L = 0; L < vl / 128; L++) {
        const uint32_t *x = &a->d[4 * L], *y = &b->d[4 * L];
        t.d[4 * L + 0] = x[0] + x[1];
        t.d[4 * L + 1] = x[2] + x[3];
        t.d[4 * L + 2] = y[0] + y[1];
        t.d[4 * L + 3] = y[2] + y[3];
    }
    *r = t;
}

static uint64_t get_elem(const x2reg *v, int eb, int i) {
    switch (eb) {
    case 8: return v->b[i];
    case 16: return v->w[i];
    case 32: return v->d[i];
    default: return v->q[i];
    }
}
static void set_elem(x2reg *v, int eb, int i, uint64_t x) {
    switch (eb) {
    case 8: v->b[i] = (uint8_t)x; break;
    case 16: v->w[i] = (uint16_t)x; break;
    case 32: v->d[i] = (uint32_t)x; break;
    default: v->q[i] = x; break;
    }
}

void x2_masked(const x2reg *res, const x2reg *dst, uint64_t k, int z, int vl, int eb, x2reg *r) {
    x2reg t;
    int i;
    memset(&t, 0, sizeof t);
    for (i = 0; i < vl / eb; i++)
        set_elem(&t, eb, i, ((k >> i) & 1) ? get_elem(res, eb, i) : (z ? 0 : get_elem(dst, eb, i)));
    *r = t;
}

/* ------------------------------------------------------------------ vec.py / table.py builders */
static void write_full(int encoding, int vl, const x2reg *result, const x2reg *old, x2reg *out) {
    int nbytes = vl / 8, i;
    x2reg t;
    if (encoding == X2E_LEGACY) t = *old;
    else memset(&t, 0, sizeof t);
    for (i = 0; i < nbytes; i++) t.b[i] = result->b[i];
    *out = t;
}

static uint32_t lane_fp2(int fn, uint32_t a, uint32_t b, const x2env *e, uint32_t *fl) {
    switch (fn) {
    case X2F_ADD: return x2_add(a, b, e, fl);
    case X2F_SUB: return x2_sub(a, b, e, fl);
    case X2F_MUL: return x2_mul(a, b, e, fl);
    case X2F_DIV: return x2_div(a, b, e, fl);
    case X2F_MAX: return x2_max(a, b, e, fl);
    case X2F_MIN: return x2_min(a, b, e, fl);
    }
    return 0;
}

static uint32_t lane_fp1(const x2sem *s, uint32_t a, const x2env *e, uint32_t *fl) {
    switch (s->fn) {
    case X2F_CVT_I2F: return x2_cvt_i2f(a, e, fl);
    case X2F_CVT_F2I: return x2_cvt_f2i(a, e, s->trunc, fl);
    case X2F_CVT_H2F: return x2_cvt_h2f(a, e, fl);
    }
    return 0;
}

int x2_lanes(const x2sem *s) {
    switch (s->builder) {
    case X2B_CMP_K: return s->scalar ? 1 : s->vl / 32;
    case X2B_PACKED_FP2: case X2B_CMP_VEC: return s->vl / 32;
    case X2B_PACKED_FP1: return s->vl / s->dst_eb;
    case X2B_INT2: return s->vl / s->dst_eb;
    case X2B_INT_ACC: return s->vl / 32;
    default: return 1;
    }
}

static int active(const x2sem *s, uint64_t k, int i) {
    return s->maskmode == X2M_NONE || ((k >> i) & 1);
}

int x2_predict(const x2sem *s, const x2case *c, x2out *o) {
    x2env env;
    uint32_t fl = 0;
    int i, n;
    x2reg res;
    memset(o, 0, sizeof *o);
    memset(&res, 0, sizeof res);
    if (s->builder == X2B_INT2 || s->builder == X2B_INT_ACC) {   /* integer entries: no MXCSR input */
        x2reg r1;
        if (s->builder == X2B_INT2) {
            if (s->fn == X2F_PMADDUBSW) x2_pmaddubsw(&c->src1, &c->src2, s->vl, &r1);
            else if (s->fn == X2F_PMADDWD) x2_pmaddwd(&c->src1, &c->src2, s->vl, &r1);
            else x2_phaddd(&c->src1, &c->src2, s->vl, &r1);
            if (s->maskmode != X2M_NONE) x2_masked(&r1, &c->dst_old, c->k, s->maskmode == X2M_ZERO, s->vl, s->dst_eb, &res);
            else res = r1;
        } else {
            x2_pdpbusd(&c->dst_old, &c->src1, &c->src2, s->vl, s->saturate, &r1);
            if (s->maskmode != X2M_NONE) x2_masked(&r1, &c->dst_old, c->k, s->maskmode == X2M_ZERO, s->vl, s->dst_eb, &res);
            else res = r1;
        }
        write_full(s->encoding, s->vl, &res, &c->dst_old, &o->dst);
        o->mxcsr = c->mxcsr;
        return 0;
    }
    if (x2_env_make(&env, c->mxcsr, s->er, s->sae) != 0) return -1;
    /* Compare immediates outside the entry's declared domain: no prediction. VEX/EVEX use imm8[4:0]; the legacy
       CMPPS/CMPSS entries declare imm8 in [0, 7] (SDM: bits 7:3 reserved; table.py "imm_max": 7; review 2026-10-23). */
    if ((s->builder == X2B_CMP_K || s->builder == X2B_CMP_VEC || s->builder == X2B_CMP_SCALAR) &&
        (s->imm < 0 || s->imm > (s->encoding == X2E_LEGACY ? 7 : 31))) return -1;
    switch (s->builder) {
    case X2B_PACKED_FP2: {
        const x2reg *s1 = (s->encoding == X2E_LEGACY) ? &c->dst_old : &c->src1;   /* legacy ADDPS: src1 IS dst */
        n = s->vl / 32;
        for (i = 0; i < n; i++) {
            uint32_t b = s->bcast ? c->src2.d[0] : c->src2.d[i];
            if (!active(s, c->k, i)) res.d[i] = (s->maskmode == X2M_ZERO) ? 0 : c->dst_old.d[i];
            else res.d[i] = lane_fp2(s->fn, s1->d[i], b, &env, &fl);
        }
        write_full(s->encoding, s->vl, &res, &c->dst_old, &o->dst);
        break;
    }
    case X2B_SCALAR_FP2: {
        const x2reg *s1 = (s->encoding == X2E_LEGACY) ? &c->dst_old : &c->src1;   /* legacy: src1 IS dst */
        if (s->maskmode != X2M_NONE && !(c->k & 1)) res.d[0] = (s->maskmode == X2M_ZERO) ? 0 : c->dst_old.d[0];
        else res.d[0] = lane_fp2(s->fn, s1->d[0], c->src2.d[0], &env, &fl);
        for (i = 1; i < 4; i++) res.d[i] = s1->d[i];
        write_full(s->encoding, 128, &res, &c->dst_old, &o->dst);
        break;
    }
    case X2B_PACKED_FP1: {
        const x2reg *sp = s->mem ? &c->src2 : &c->src1;   /* a memory source is read through RAX = &src2 */
        n = s->vl / s->dst_eb;
        for (i = 0; i < n; i++) {
            uint32_t a = (s->src_eb == 16) ? sp->w[i] : sp->d[i];
            if (!active(s, c->k, i)) res.d[i] = (s->maskmode == X2M_ZERO) ? 0 : c->dst_old.d[i];
            else res.d[i] = lane_fp1(s, a, &env, &fl);
        }
        write_full(s->encoding, s->vl, &res, &c->dst_old, &o->dst);
        break;
    }
    case X2B_CMP_K: {
        uint64_t k = 0;
        n = s->scalar ? 1 : s->vl / 32;                   /* EVEX VCMPSS: lane 0 only, bits >= 1 zero */
        for (i = 0; i < n; i++) {
            uint32_t b = s->bcast ? c->src2.d[0] : c->src2.d[i];
            if (!active(s, c->k, i)) continue;
            if (x2_cmp_pred(c->src1.d[i], b, s->imm, &env, &fl)) k |= 1ull << i;
        }
        o->kdst = k;
        break;
    }
    case X2B_CMP_VEC: {
        const x2reg *s1 = (s->encoding == X2E_LEGACY) ? &c->dst_old : &c->src1;   /* legacy CMPPS: src1 IS dst */
        n = s->vl / 32;
        for (i = 0; i < n; i++) res.d[i] = x2_cmp_pred(s1->d[i], c->src2.d[i], s->imm, &env, &fl) ? 0xFFFFFFFFu : 0;
        write_full(s->encoding, s->vl, &res, &c->dst_old, &o->dst);
        break;
    }
    case X2B_CMP_SCALAR: {
        const x2reg *s1 = (s->encoding == X2E_LEGACY) ? &c->dst_old : &c->src1;   /* legacy CMPSS: src1 IS dst */
        res.d[0] = x2_cmp_pred(s1->d[0], c->src2.d[0], s->imm, &env, &fl) ? 0xFFFFFFFFu : 0;
        for (i = 1; i < 4; i++) res.d[i] = s1->d[i];
        write_full(s->encoding, 128, &res, &c->dst_old, &o->dst);
        break;
    }
    case X2B_COMIS: {
        int zf, pf, cf;
        x2_comis(c->src1.d[0], c->src2.d[0], &env, s->signalling, &zf, &pf, &cf, &fl);
        o->rflags = ((uint64_t)zf << 6) | ((uint64_t)pf << 2) | (uint64_t)cf;   /* OF = SF = AF = 0 */
        break;
    }
    case X2B_CVT_F2I_GPR: {
        o->gpr = (uint64_t)x2_cvt_f2i(c->src1.d[0], &env, s->trunc, &fl);       /* zero-extended */
        break;
    }
    case X2B_CVT_I2F_SCALAR: {
        const x2reg *up = (s->encoding == X2E_LEGACY) ? &c->dst_old : &c->src1;
        res.d[0] = (s->src_eb == 64) ? x2_cvt_i64_2f(c->gpr_in, &env, &fl) : x2_cvt_i2f((uint32_t)c->gpr_in, &env, &fl);
        for (i = 1; i < 4; i++) res.d[i] = up->d[i];
        write_full(s->encoding, 128, &res, &c->dst_old, &o->dst);
        break;
    }
    default:
        return -1;
    }
    if (env.sae) fl = 0;
    o->mxcsr = env.sae ? c->mxcsr : (c->mxcsr | (fl & 0x3F));
    return 0;
}
