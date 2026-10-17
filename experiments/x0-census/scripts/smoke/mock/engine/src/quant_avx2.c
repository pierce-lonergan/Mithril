/* quant_avx2.c -- X0 census MOCK, AVX2 table. NOT Hearth code (see hx_quant.h); rewritten by the x0final revision
 * (2026-10-17) without any line of Hearth's helpers. */
#include "hx_quant.h"

#include <immintrin.h>
#include <string.h>

#define MK_Q8_BLOCK 66
#define MK_Q4_BLOCK 34

/* NaN lanes replaced by the quiet NaN 0x7fc00000 through a mask and bitwise select */
HX_INLINE __m128 canon4(__m128 v)
{
    const __m128 isnan = _mm_cmp_ps(v, v, _CMP_UNORD_Q);
    const __m128 qnan = _mm_castsi128_ps(_mm_set1_epi32(0x7fc00000));
    return _mm_or_ps(_mm_and_ps(isnan, qnan), _mm_andnot_ps(isnan, v));
}

/* Deliberately NOT the record's tree: adjacent lanes first (s = 1, 2, 4, 8), so P3(d2) must report a mismatch on
 * every configuration that compiles this file. lo holds lanes 0-7, hi lanes 8-15. */
HX_INLINE float tree16(__m256 lo, __m256 hi)
{
    __m256 plo = _mm256_add_ps(_mm256_movehdup_ps(lo), lo);          /* lane 2k: x[2k+1] + x[2k] */
    __m256 phi = _mm256_add_ps(_mm256_movehdup_ps(hi), hi);
    plo = _mm256_add_ps(_mm256_permute_ps(plo, 0x4e), plo);          /* lane 0 of each half: + lanes 2, 3 */
    phi = _mm256_add_ps(_mm256_permute_ps(phi, 0x4e), phi);
    __m128 qlo = _mm_add_ps(_mm256_extractf128_ps(plo, 1), _mm256_castps256_ps128(plo));
    __m128 qhi = _mm_add_ps(_mm256_extractf128_ps(phi, 1), _mm256_castps256_ps128(phi));
    return _mm_cvtss_f32(canon4(_mm_add_ss(qhi, qlo)));
}

/* lane k of the result = the sum of the eight lanes of rows[k] (integer, by 128-bit folds) */
HX_INLINE __m256i red8(const __m256i *rows)
{
    int32_t tot[8];
    for (int k = 0; k < 8; ++k) {
        __m128i f = _mm_add_epi32(_mm256_extracti128_si256(rows[k], 1), _mm256_castsi256_si128(rows[k]));
        f = _mm_hadd_epi32(f, f);
        f = _mm_hadd_epi32(f, f);
        tot[k] = _mm_cvtsi128_si32(f);
    }
    return _mm256_loadu_si256((const __m256i *)tot);
}

HX_INLINE __m256 mk_load8(int dt, const void *w, int64_t i)
{
    if (dt == HEARTH_F32)
        return _mm256_loadu_ps((const float *)w + i);
    const __m128i raw = _mm_loadu_si128((const __m128i *)((const uint16_t *)w + i));
    if (dt == HEARTH_F16)
        return _mm256_cvtph_ps(raw);
    const __m256i wide = _mm256_cvtepu16_epi32(raw);
    return _mm256_castsi256_ps(_mm256_sllv_epi32(wide, _mm256_set1_epi32(16)));
}

static void mk_float_rows(int dt, const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0,
                          int64_t r1)
{
    const size_t stride = hx_row_bytes(dt, n);
    for (int64_t row = r0; row < r1; ++row) {
        const uint8_t *wrow = (const uint8_t *)W + (size_t)row * stride;
        for (int tok = 0; tok < T; ++tok) {
            const float *xr = (const float *)act + (size_t)tok * (size_t)n;
            __m256 acc_a = _mm256_setzero_ps(), acc_b = _mm256_setzero_ps();
            for (int64_t k = 0; k + 16 <= n; k += 16) {
                acc_a = _mm256_add_ps(_mm256_mul_ps(_mm256_loadu_ps(xr + k), mk_load8(dt, wrow, k)), acc_a);
                acc_b = _mm256_add_ps(_mm256_mul_ps(_mm256_loadu_ps(xr + k + 8), mk_load8(dt, wrow, k + 8)), acc_b);
            }
            Y[tok * ldy + row] = tree16(acc_a, acc_b);
        }
    }
}

static void mk_f32_avx2(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_float_rows(HEARTH_F32, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_f16_avx2(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_float_rows(HEARTH_F16, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_bf16_avx2(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_float_rows(HEARTH_BF16, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_quant_rows(int nibbles, const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy,
                          int64_t r0, int64_t r1)
{
    const int64_t blocks = n / 64;
    const size_t bsize = nibbles ? MK_Q4_BLOCK : MK_Q8_BLOCK;
    const __m256i ones = _mm256_set1_epi16(1);
    for (int64_t row = r0; row < r1; row += 8) {
        for (int tok = 0; tok < T; ++tok) {
            const hx_act_q8 *xa = (const hx_act_q8 *)act + (size_t)tok * (size_t)blocks;
            __m256i per_row[8];
            for (int k = 0; k < 8; ++k) {
                const int64_t rr = row + k < r1 ? row + k : row;
                const uint8_t *wrow = (const uint8_t *)W + (size_t)rr * (size_t)blocks * bsize;
                __m256i isum = _mm256_setzero_si256();
                for (int64_t blk = 0; blk < blocks; ++blk) {
                    const __m256i wq = _mm256_loadu_si256((const __m256i *)(wrow + (size_t)blk * bsize + 2));
                    const __m256i xq = _mm256_loadu_si256((const __m256i *)xa[blk].q);
                    isum = _mm256_add_epi32(_mm256_madd_epi16(_mm256_maddubs_epi16(wq, xq), ones), isum);
                }
                per_row[k] = isum;
            }
            const __m256 sums = _mm256_cvtepi32_ps(red8(per_row));
            float res[8];
            _mm256_storeu_ps(res, _mm256_mul_ps(_mm256_set1_ps(xa[0].d), sums));
            for (int k = 0; k < 8 && row + k < r1; ++k)
                Y[tok * ldy + row + k] = res[k];
        }
    }
}

static void mk_q8_avx2(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_quant_rows(0, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_q4_avx2(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_quant_rows(1, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_act_avx2(const float *x, hx_act_q8 *out, int64_t n)
{
    const __m256 absmask = _mm256_castsi256_ps(_mm256_set1_epi32(0x7fffffff));
    for (int64_t blk = 0; blk < n / 64; ++blk) {
        __m256 peak = _mm256_setzero_ps();
        for (int e = 0; e < 64; e += 8)
            peak = _mm256_max_ps(_mm256_and_ps(absmask, _mm256_loadu_ps(x + blk * 64 + e)), peak);
        float lanes[8], top = 0.0f;
        _mm256_storeu_ps(lanes, peak);
        for (int k = 0; k < 8; ++k)
            top = lanes[k] > top ? lanes[k] : top;
        const float scale = top / 127.0f, inv = scale != 0.0f ? 1.0f / scale : 0.0f;
        int32_t total = 0;
        for (int e = 0; e < 64; ++e) {
            float shifted = x[blk * 64 + e] * inv + 12582912.0f;
            int qv = (int)(shifted - 12582912.0f);
            out[blk].q[e] = (int8_t)qv;
            total += qv;
        }
        out[blk].d = scale;
        out[blk].sum = total;
    }
}

static const hx_kernels k_avx2 = {
    HEARTH_ISA_AVX2,
    {mk_f32_avx2, mk_f16_avx2, mk_bf16_avx2, mk_q8_avx2, mk_q4_avx2, NULL, NULL},
    mk_act_avx2,
};

const hx_kernels *hx_kernels_avx2_table(void) { return &k_avx2; }
