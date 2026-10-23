/*
 * x3_bitid.c: standalone bit-identity harness for the X3 prototype (development data only).
 *
 * Built CRT-free into a DLL together with
 *   - Hearth's scalar reference kernels, extracted verbatim from engine/src/quant.c at b5d3f14 into a
 *     scratch file (never into the repository) by scripts/bitid.py,
 *   - Hearth's quant_avx2.c and quant_avx512.c, copied unmodified into scratch,
 *   - the six generated kernels.
 * The Python driver allocates every buffer between no-access guard pages, fills inputs through the
 * exports below, and calls x3t_case() per shape.
 *
 * Input rule (DESIGN 7, step 6): activation codes and sums always come from Hearth's scalar
 * act_quantize_q8, so P1 and P2 hold; special values (NaN, +-inf, +-0, subnormals, extremes) are
 * injected only into W's code bytes, W's f16 scales and A's f32 scales after quantisation.
 */
#include "hx_quant.h"
#include "x3_gen.h"

#include <immintrin.h>
#include <string.h>

#define EXPORT __declspec(dllexport)

/* P3 (DESIGN 3.3): the tests must run with the default MXCSR (RNE, FTZ = DAZ = 0). */
EXPORT unsigned x3t_mxcsr(void) { return _mm_getcsr(); }

void x3ref_mm_q8_scalar(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1);
void x3ref_mm_q4_scalar(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1);
void x3ref_act_q8_scalar(const float *x, hx_act_q8 *out, int64_t n);

enum { NK = 6 };
static const char *const KNAME[NK] = {"hearth_scalar", "hearth_avx2", "hearth_avx512",
                                      "x3_scalar", "x3_avx2", "x3_avx512"};

static hx_matmul_fn kern(int which, int dtype) {
    const int q8 = dtype == HEARTH_Q8;
    switch (which) {
    case 0: return q8 ? x3ref_mm_q8_scalar : x3ref_mm_q4_scalar;
    case 1: return hx_kernels_avx2_table()->matmul[dtype];
    case 2: return hx_kernels_avx512_table()->matmul[dtype];
    case 3: return q8 ? hx_x3_mm_q8_scalar : hx_x3_mm_q4_scalar;
    case 4: return q8 ? hx_x3_mm_q8_avx2 : hx_x3_mm_q4_avx2;
    case 5: return q8 ? hx_x3_mm_q8_avx512 : hx_x3_mm_q4_avx512;
    default: return 0;
    }
}

EXPORT const char *x3t_kernel_name(int which) { return (which >= 0 && which < NK) ? KNAME[which] : ""; }

/* ------------------------------------------------------------------ deterministic random */

static uint64_t rs;
static uint64_t rnd(void) {
    uint64_t z = (rs += 0x9e3779b97f4a7c15ull);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
    return z ^ (z >> 31);
}
static uint32_t rnd_below(uint32_t m) { return (uint32_t)(rnd() % m); }

static float f32_from(uint32_t b) {
    float f;
    memcpy(&f, &b, 4);
    return f;
}

/* f16 scale patterns. smode 1: realistic (around 0x2c00, as test_quant's fill_weights), no
 * specials. smode 0: every IEEE half class; NaN and inf each with probability nanpm per mille,
 * so that long rows are not all NaN. */
static uint16_t rnd_f16(int smode, int nanpm, int32_t *cls) {
    uint32_t c = rnd_below(1000);
    uint16_t s = (uint16_t)(rnd_below(2) << 15);
    if (smode == 1) {
        cls[0]++;
        return (uint16_t)(0x2800u + rnd_below(0x0800u));
    }
    if (c < (uint32_t)nanpm) { cls[3]++; return (uint16_t)(s | 0x7c00u); }                       /* +-inf */
    if (c < 2u * (uint32_t)nanpm) { cls[4]++; return (uint16_t)(s | 0x7c00u | (1u + rnd_below(1023u))); } /* NaN */
    c = rnd_below(100);
    if (c < 70) { cls[0]++; return (uint16_t)(s | ((1u + rnd_below(30u)) << 10) | rnd_below(1024u)); }
    if (c < 84) { cls[1]++; return (uint16_t)(s | (1u + rnd_below(1023u))); }               /* subnormal */
    if (c < 92) { cls[2]++; return s; }                                                   /* +-0 */
    cls[5]++;
    {
        static const uint16_t edge[] = {0x7bff, 0x0400, 0x0001, 0x03ff, 0x3c00, 0x0200, 0x7800};
        return (uint16_t)(s | edge[rnd_below(7)]);
    }
}

/* W: nblocks blocks of dtype. smode 0: all f16 classes (NaN/inf at nanpm per mille each);
 * 1: realistic scales. cmode 0: uniform random code bytes; 1: extremes only
 * (0x00, 0x7f, 0x80, 0xff, 0x0f, 0xf0, 0x88). cls[0..5]: normal, subnormal, zero, inf, NaN, edge. */
EXPORT void x3t_fill_weights(uint8_t *W, int64_t nblocks, int dtype, uint64_t seed, int smode, int cmode,
                             int nanpm, int32_t *cls) {
    const size_t bs = dtype == HEARTH_Q8 ? sizeof(hx_block_q8) : sizeof(hx_block_q4);
    static const uint8_t ext[] = {0x00, 0x7f, 0x80, 0xff, 0x0f, 0xf0, 0x88};
    rs = seed;
    for (int64_t b = 0; b < nblocks; b++) {
        uint8_t *p = W + (size_t)b * bs;
        uint16_t d = rnd_f16(smode, nanpm, cls);
        memcpy(p, &d, 2);
        for (size_t j = 2; j < bs; j++) p[j] = cmode ? ext[rnd_below(7)] : (uint8_t)rnd();
    }
}

/* A: nblocks activation blocks quantised by Hearth's scalar act_q8 from random floats
 * (xmode 0: wide-range values with zero, NaN and inf inputs mixed in; 1: N(0,1)-like),
 * then dmode 1 overwrites block scales d with special binary32 values: NaN, inf and huge
 * (overflowing) ones with probability nanpm per mille, zeros and subnormals with 1/3.
 * inf inputs (which make d = inf) also occur at nanpm per mille.
 * cls[0..5]: d normal, subnormal, zero, inf, NaN, huge/edge. */
EXPORT void x3t_fill_act(uint8_t *A, int64_t nblocks, uint64_t seed, int xmode, int dmode, int nanpm,
                         int32_t *cls) {
    float x[HX_QK];
    rs = seed ^ 0x5bd1e995u;
    for (int64_t b = 0; b < nblocks; b++) {
        hx_act_q8 *a = (hx_act_q8 *)(A + (size_t)b * sizeof(hx_act_q8));
        const uint32_t kind = rnd_below(16);
        for (int i = 0; i < HX_QK; i++) {
            if (xmode == 1) {
                int32_t s = 0;
                for (int k = 0; k < 4; k++) s += (int32_t)rnd_below(2001) - 1000;
                x[i] = (float)s * 0.001f;
            } else if (kind == 0) {
                x[i] = 0.0f;
            } else if (kind == 1 && rnd_below(8) == 0) {
                x[i] = f32_from(0x7fc00000u | (uint32_t)rnd_below(1u << 22)); /* NaN input */
            } else if (kind == 2 && rnd_below(1000) < (uint32_t)nanpm) {
                x[i] = f32_from(rnd_below(2) ? 0x7f800000u : 0xff800000u);     /* inf input */
            } else {
                /* random sign, exponent spread over most of the range */
                uint32_t e = 64u + rnd_below(128u);
                x[i] = f32_from((uint32_t)(rnd_below(2) << 31) | (e << 23) | rnd_below(1u << 23));
            }
        }
        x3ref_act_q8_scalar(x, a, HX_QK);
        if (dmode == 1 && rnd_below(1000) < (uint32_t)nanpm) {
            static const uint32_t nf[] = {0x7fc00000u, 0xffc00000u, 0x7f800001u, 0x7fa00001u,
                                          0x7f800000u, 0xff800000u, 0x7f7fffffu, 0xff7fffffu,
                                          0x7e967699u};
            a->d = f32_from(nf[rnd_below(9)]);
        } else if (dmode == 1 && rnd_below(3) == 0) {
            static const uint32_t sp[] = {0x00000000u, 0x80000000u, 0x00000001u, 0x807fffffu,
                                          0x007fffffu, 0x00400000u, 0x00800000u, 0x80800000u};
            a->d = f32_from(sp[rnd_below(8)]);
        }
        {
            uint32_t db;
            memcpy(&db, &a->d, 4);
            if ((db & 0x7f800000u) == 0x7f800000u) cls[(db & 0x007fffffu) ? 4 : 3]++;
            else if ((db & 0x7fffffffu) == 0) cls[2]++;
            else if ((db & 0x7f800000u) == 0) cls[1]++;
            else if ((db & 0x7fffffffu) >= 0x7e000000u) cls[5]++;
            else cls[0]++;
        }
    }
}

EXPORT void x3t_matmul(int which, int dtype, const void *W, int64_t n, const void *act, int T, float *Y,
                       int64_t ldy, int64_t r0, int64_t r1) {
    kern(which, dtype)(W, n, act, T, Y, ldy, r0, r1);
}

EXPORT void x3t_act_quant(const float *x, void *out, int64_t n) { x3ref_act_q8_scalar(x, (hx_act_q8 *)out, n); }

/* ------------------------------------------------------------------ one shape */

static const uint32_t SENT = 0x7fc0deadu; /* as test_quant.c:1044 */

static void fill_sent(float *Y, int64_t m) {
    for (int64_t i = 0; i < m; i++) memcpy(&Y[i], &SENT, 4);
}

static int32_t diff(const float *a, const float *b, int64_t m) {
    int32_t bad = 0;
    for (int64_t i = 0; i < m; i++) bad += memcmp(&a[i], &b[i], 4) != 0;
    return bad;
}

static uint64_t fnv(uint64_t h, const void *p, size_t m) {
    const uint8_t *q = (const uint8_t *)p;
    for (size_t i = 0; i < m; i++) h = (h ^ q[i]) * 0x100000001b3ull;
    return h;
}

/*
 * Non-default MXCSR modes (review 2026-10-23). Two kernels with the same FP DAG give the same bits
 * under every rounding mode and under FTZ/DAZ, so agreement here is a stronger DAG-identity test
 * than agreement under the default mode alone. The meaning itself is defined under the default
 * mode (P3); these runs test identity, not the meaning. The mode is set only around the two calls
 * and restored at once (documented SSE intrinsics _mm_getcsr / _mm_setcsr; the kernels themselves
 * never write MXCSR, as the object scan checks).
 *
 * For each mode i: Ys = Hearth scalar; then for k = 0..2, Yr = Hearth kernel k, Yk = x3 kernel k+3.
 * pair[3i + k]   words where x3 kernel k+3 != Hearth kernel k (same ISA), padding included
 * cross[6i + j]  words where kernel j != Hearth scalar under the same mode
 * live[i]        words where Hearth scalar under mode i != Hearth scalar under the default mode
 *                (shows the mode changes results on this case)
 */
EXPORT void x3t_case_modes(int dtype, int64_t n, int64_t rows, int T, int64_t ldy, const uint8_t *W,
                           const uint8_t *A, float *Yd, float *Ys, float *Yr, float *Yk, const unsigned *csr,
                           int nm, int32_t *pair, int32_t *cross, int32_t *live) {
    const int64_t m = (int64_t)T * ldy;
    const unsigned old = _mm_getcsr();
    fill_sent(Yd, m);
    kern(0, dtype)(W, n, A, T, Yd, ldy, 0, rows);
    for (int i = 0; i < nm; i++) {
        fill_sent(Ys, m);
        _mm_setcsr(csr[i]);
        kern(0, dtype)(W, n, A, T, Ys, ldy, 0, rows);
        _mm_setcsr(old);
        live[i] += diff(Ys, Yd, m);
        for (int k = 0; k < 3; k++) {
            fill_sent(Yr, m);
            fill_sent(Yk, m);
            _mm_setcsr(csr[i]);
            kern(k, dtype)(W, n, A, T, Yr, ldy, 0, rows);
            kern(k + 3, dtype)(W, n, A, T, Yk, ldy, 0, rows);
            _mm_setcsr(old);
            pair[3 * i + k] += diff(Yk, Yr, m);
            cross[6 * i + k] += diff(Yr, Ys, m);
            cross[6 * i + k + 3] += diff(Yk, Ys, m);
        }
    }
}

/*
 * bad[k]        whole call of kernel k != Hearth scalar (all T*ldy words, padding included)
 * bad[6 + k]    T single-token calls != the batched reference
 * bad[12 + k]   random row splits (1..23 rows, as test_quant.c:1082-1087) != whole
 * bad[18 + k]   a write happened for T == 0 or r0 == r1
 * bad[24 + k]   a sub-range call [r0, r1) wrote outside it or disagreed inside it
 * oc[0..4]      reference outputs that are NaN, +-inf, +-0, subnormal, normal
 */
EXPORT void x3t_case(int dtype, int64_t n, int64_t rows, int T, int64_t ldy, const uint8_t *W, const uint8_t *A,
                     float *Yref, float *Yk, uint64_t seed, int32_t *bad, uint64_t *hash, int32_t *oc) {
    const int64_t m = (int64_t)T * ldy;
    const size_t ab = (size_t)(n / HX_QK) * sizeof(hx_act_q8);
    rs = seed;
    fill_sent(Yref, m);
    kern(0, dtype)(W, n, A, T, Yref, ldy, 0, rows);
    *hash = fnv(*hash, Yref, (size_t)m * 4);
    for (int64_t i = 0; i < m; i++) {
        uint32_t u;
        memcpy(&u, &Yref[i], 4);
        if ((i % ldy) >= rows) continue;
        if ((u & 0x7f800000u) == 0x7f800000u) oc[(u & 0x007fffffu) ? 0 : 1]++;
        else if ((u & 0x7fffffffu) == 0) oc[2]++;
        else if ((u & 0x7f800000u) == 0) oc[3]++;
        else oc[4]++;
    }
    for (int k = 0; k < NK; k++) {
        hx_matmul_fn f = kern(k, dtype);
        if (k) {
            fill_sent(Yk, m);
            f(W, n, A, T, Yk, ldy, 0, rows);
            bad[k] += diff(Yk, Yref, m);
        } else {
            int32_t pad = 0;
            for (int t = 0; t < T; t++)
                for (int64_t r = rows; r < ldy; r++) pad += memcmp(&Yref[t * ldy + r], &SENT, 4) != 0;
            bad[0] += pad;
        }
        fill_sent(Yk, m);
        for (int t = 0; t < T; t++) f(W, n, A + (size_t)t * ab, 1, Yk + (size_t)t * ldy, ldy, 0, rows);
        bad[6 + k] += diff(Yk, Yref, m);
        fill_sent(Yk, m);
        for (int64_t r0 = 0; r0 < rows;) {
            int64_t r1 = r0 + 1 + (int64_t)rnd_below(23);
            if (r1 > rows) r1 = rows;
            f(W, n, A, T, Yk, ldy, r0, r1);
            r0 = r1;
        }
        bad[12 + k] += diff(Yk, Yref, m);
        fill_sent(Yk, m);
        f(W, n, A, 0, Yk, ldy, 0, rows);
        f(W, n, A, T, Yk, ldy, 0, 0);
        f(W, n, A, T, Yk, ldy, rows, rows);
        f(W, n, A, T, Yk, ldy, rows / 2, rows / 2);
        for (int64_t i = 0; i < m; i++) bad[18 + k] += memcmp(&Yk[i], &SENT, 4) != 0;
        {
            const int64_t a0 = (int64_t)rnd_below((uint32_t)rows), a1 = a0 + 1 + (int64_t)rnd_below((uint32_t)(rows - a0));
            fill_sent(Yk, m);
            f(W, n, A, T, Yk, ldy, a0, a1);
            for (int t = 0; t < T; t++)
                for (int64_t r = 0; r < ldy; r++) {
                    const float *want = (r >= a0 && r < a1) ? &Yref[t * ldy + r] : (const float *)&SENT;
                    bad[24 + k] += memcmp(&Yk[t * ldy + r], want, 4) != 0;
                }
        }
    }
}
