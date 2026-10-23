/* a1_escape.c -- NON-Hearth reproduction for X0 Amendment X0-A1 (tooling fix of x0_loops.py, record §4.7
 * "constant-offset, non-escaping stack slot"). Written 2026-10-23 by the x0fix track (Claude) from the SHAPE that
 * REPORT.md §10 and §20 describe, not from Hearth's text: a stack array of vector accumulators with a run-time live
 * count (at most A1_LANES_MAX entries), zeroed at the start of every chunk of outputs, accumulated over an inner
 * reduction loop, then stored; the array's address is taken (by the zeroing loop's memset/rep stos lowering, by an
 * explicit memset, or by a call). Controls: register accumulators (no array), and an amax loop.
 * The functions only exercise the census tooling (x0_extract, x0_decode, x0_twin, x0_loops); they compute a small
 * matrix product so that the compilers keep the shape, and nothing calls them.
 */
#include <immintrin.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#if defined(_MSC_VER) && !defined(__clang__)
#define A1_FORCE static __forceinline
#define A1_NOINLINE __declspec(noinline)
#else
#define A1_FORCE static inline __attribute__((always_inline))
#define A1_NOINLINE __attribute__((noinline))
#endif

#define A1_LANES_MAX 8          /* outputs per chunk */
#define A1_WIDE_MAX 4

typedef void (*a1_mm_fn)(const void *wts, int64_t ncol, const void *xs, int ntok, float *out, int64_t ostride,
                         int64_t rlo, int64_t rhi);

typedef struct a1_kernels {
    int isa;
    a1_mm_fn mm[5];
    void (*peak)(const float *v, void *res, int64_t len);
} a1_kernels;

void a1_external_sink(void *p, int64_t bytes);

/* One 4-row tile: out[(c + u) * ostride + row .. row + 3] = sum over k of wts[row .. row + 3][k] * xs[c + u][k]. */
A1_FORCE void a1_tile_rep(const float *wts, int64_t ncol, const float *xs, int ntok, float *out, int64_t ostride,
                          int64_t row)
{
    for (int c = 0; c < ntok; c += A1_LANES_MAX) {
        int live = ntok - c;
        if (live > A1_LANES_MAX)
            live = A1_LANES_MAX;
        __m128 part[A1_LANES_MAX];
        for (int u = 0; u < live; ++u)
            part[u] = _mm_setzero_ps();
        for (int64_t k = 0; k < ncol; ++k) {
            const __m128 wv = _mm_loadu_ps(wts + (row * ncol + k * 4));
            for (int u = 0; u < live; ++u) {
                const __m128 xv = _mm_set1_ps(xs[(int64_t)(c + u) * ncol + k]);
                part[u] = _mm_add_ps(part[u], _mm_mul_ps(wv, xv));
            }
        }
        for (int u = 0; u < live; ++u)
            _mm_storeu_ps(out + (int64_t)(c + u) * ostride + row, part[u]);
    }
}

static void a1_mm_rep(const void *wts, int64_t ncol, const void *xs, int ntok, float *out, int64_t ostride,
                      int64_t rlo, int64_t rhi)
{
    for (int64_t row = rlo; row + 4 <= rhi; row += 4)
        a1_tile_rep((const float *)wts, ncol, (const float *)xs, ntok, out, ostride, row);
}

/* The same shape with the zeroing written as one memset of the live entries. */
A1_FORCE void a1_tile_memset(const float *wts, int64_t ncol, const float *xs, int ntok, float *out, int64_t ostride,
                             int64_t row)
{
    for (int c = 0; c < ntok; c += A1_LANES_MAX) {
        const int live = (ntok - c) < A1_LANES_MAX ? (ntok - c) : A1_LANES_MAX;
        __m128 part[A1_LANES_MAX];
        memset(part, 0, (size_t)live * sizeof(part[0]));
        for (int64_t k = 0; k < ncol; ++k) {
            const __m128 wv = _mm_loadu_ps(wts + (row * ncol + k * 4));
            for (int u = 0; u < live; ++u)
                part[u] = _mm_add_ps(part[u], _mm_mul_ps(wv, _mm_set1_ps(xs[(int64_t)(c + u) * ncol + k])));
        }
        for (int u = 0; u < live; ++u)
            _mm_storeu_ps(out + (int64_t)(c + u) * ostride + row, part[u]);
    }
}

static void a1_mm_memset(const void *wts, int64_t ncol, const void *xs, int ntok, float *out, int64_t ostride,
                         int64_t rlo, int64_t rhi)
{
    for (int64_t row = rlo; row + 4 <= rhi; row += 4)
        a1_tile_memset((const float *)wts, ncol, (const float *)xs, ntok, out, ostride, row);
}

/* Control: four named accumulators, no array, no address taken (16 lanes per k). */
static void a1_mm_regs(const void *wts, int64_t ncol, const void *xs, int ntok, float *out, int64_t ostride,
                       int64_t rlo, int64_t rhi)
{
    const float *w = (const float *)wts;
    const float *x = (const float *)xs;
    for (int64_t row = rlo; row + 4 <= rhi; row += 4) {
        for (int c = 0; c + 4 <= ntok; c += 4) {
            __m128 s0 = _mm_setzero_ps(), s1 = _mm_setzero_ps(), s2 = _mm_setzero_ps(), s3 = _mm_setzero_ps();
            for (int64_t k = 0; k < ncol; ++k) {
                const __m128 wv = _mm_loadu_ps(w + (row * ncol + k * 4));
                s0 = _mm_add_ps(s0, _mm_mul_ps(wv, _mm_set1_ps(x[(int64_t)(c + 0) * ncol + k])));
                s1 = _mm_add_ps(s1, _mm_mul_ps(wv, _mm_set1_ps(x[(int64_t)(c + 1) * ncol + k])));
                s2 = _mm_add_ps(s2, _mm_mul_ps(wv, _mm_set1_ps(x[(int64_t)(c + 2) * ncol + k])));
                s3 = _mm_add_ps(s3, _mm_mul_ps(wv, _mm_set1_ps(x[(int64_t)(c + 3) * ncol + k])));
            }
            _mm_storeu_ps(out + (int64_t)(c + 0) * ostride + row, s0);
            _mm_storeu_ps(out + (int64_t)(c + 1) * ostride + row, s1);
            _mm_storeu_ps(out + (int64_t)(c + 2) * ostride + row, s2);
            _mm_storeu_ps(out + (int64_t)(c + 3) * ostride + row, s3);
        }
    }
}

/* 512-bit accumulators in an array with a live count (the frame needs 64-byte alignment). */
static void a1_mm_wide(const void *wts, int64_t ncol, const void *xs, int ntok, float *out, int64_t ostride,
                       int64_t rlo, int64_t rhi)
{
    const float *w = (const float *)wts;
    const float *x = (const float *)xs;
    for (int64_t row = rlo; row + 16 <= rhi; row += 16) {
        for (int c = 0; c < ntok; c += A1_WIDE_MAX) {
            int live = ntok - c;
            if (live > A1_WIDE_MAX)
                live = A1_WIDE_MAX;
            __m512 big[A1_WIDE_MAX];
            for (int u = 0; u < live; ++u)
                big[u] = _mm512_setzero_ps();
            for (int64_t k = 0; k < ncol; ++k) {
                const __m512 wv = _mm512_loadu_ps(w + (row * ncol + k * 16));
                for (int u = 0; u < live; ++u)
                    big[u] = _mm512_add_ps(big[u], _mm512_mul_ps(wv, _mm512_set1_ps(x[(int64_t)(c + u) * ncol + k])));
            }
            for (int u = 0; u < live; ++u)
                _mm512_storeu_ps(out + (int64_t)(c + u) * ostride + row, big[u]);
        }
    }
}

/* The array's address handed to an external function after every chunk. */
static void a1_mm_call(const void *wts, int64_t ncol, const void *xs, int ntok, float *out, int64_t ostride,
                       int64_t rlo, int64_t rhi)
{
    const float *w = (const float *)wts;
    const float *x = (const float *)xs;
    for (int64_t row = rlo; row + 4 <= rhi; row += 4) {
        for (int c = 0; c < ntok; c += A1_LANES_MAX) {
            const int live = (ntok - c) < A1_LANES_MAX ? (ntok - c) : A1_LANES_MAX;
            __m128 part[A1_LANES_MAX];
            for (int u = 0; u < A1_LANES_MAX; ++u)
                part[u] = _mm_setzero_ps();
            for (int64_t k = 0; k < ncol; ++k) {
                const __m128 wv = _mm_loadu_ps(w + (row * ncol + k * 4));
                for (int u = 0; u < live; ++u)
                    part[u] = _mm_add_ps(part[u], _mm_mul_ps(wv, _mm_set1_ps(x[(int64_t)(c + u) * ncol + k])));
            }
            a1_external_sink(part, (int64_t)sizeof(part));
            for (int u = 0; u < live; ++u)
                _mm_storeu_ps(out + (int64_t)(c + u) * ostride + row, part[u]);
        }
    }
}

/* Control: one scalar running maximum of |v| (1 lane). */
static void a1_peak(const float *v, void *res, int64_t len)
{
    float top = 0.0f;
    for (int64_t i = 0; i < len; ++i) {
        const float m = v[i] < 0.0f ? -v[i] : v[i];
        top = m > top ? m : top;
    }
    *(float *)res = top;
}

static const a1_kernels a1_table = {
    3,
    {a1_mm_rep, a1_mm_memset, a1_mm_regs, a1_mm_wide, a1_mm_call},
    a1_peak,
};

const a1_kernels *a1_table_get(void) { return &a1_table; }
