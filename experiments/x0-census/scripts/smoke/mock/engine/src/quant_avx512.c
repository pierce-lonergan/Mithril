/* quant_avx512.c -- X0 census MOCK, AVX-512 table. NOT Hearth code (see hx_quant.h); rewritten by the x0final
 * revision (2026-10-17) without any line of Hearth's helpers.
 * Uses _mm512_dpbusd_epi32 (AVX512-VNNI): clang-cl's /arch:AVX512 (skylake-avx512) lacks VNNI, so B-cmake is
 * expected to fail to compile this file (a genuine compile_failed of the mock, record §3 E2's shape). */
#include "hx_quant.h"

#include <immintrin.h>
#include <string.h>

#define MK_Q8_BLOCK 66
#define MK_Q4_BLOCK 34

/* NaN lanes replaced by the quiet NaN 0x7fc00000 through a k-mask blend */
HX_INLINE __m128 canon4(__m128 v)
{
    const __mmask8 isnan = _mm_cmp_ps_mask(v, v, _CMP_UNORD_Q);
    return _mm_mask_blend_ps(isnan, v, _mm_castsi128_ps(_mm_set1_epi32(0x7fc00000)));
}

/* The record's pairing (lane j + lane j+8, then + j+4, + j+2, + j+1), computed on whole zmm registers through
 * 128-bit-lane shuffles and in-lane permutes: P3(d2) must report a match. */
HX_INLINE float tree16(__m512 v)
{
    const __m512 a = _mm512_add_ps(v, _mm512_shuffle_f32x4(v, v, 0x4e));   /* lanes 0-7: j + j+8 */
    const __m512 b = _mm512_add_ps(a, _mm512_shuffle_f32x4(a, a, 0xb1));   /* lanes 0-3: + j+4 */
    const __m512 c = _mm512_add_ps(b, _mm512_permute_ps(b, 0x4e));         /* lanes 0-1: + j+2 */
    const __m512 d = _mm512_add_ps(c, _mm512_permute_ps(c, 0xb1));         /* lane 0: + j+1 */
    return _mm_cvtss_f32(canon4(_mm512_castps512_ps128(d)));
}

HX_INLINE int32_t hsum_i32(__m512i v)
{
    return _mm512_reduce_add_epi32(v);
}

HX_INLINE __m512 mk_load16(int dt, const void *w, int64_t i)
{
    if (dt == HEARTH_F32)
        return _mm512_loadu_ps((const float *)w + i);
    const __m256i raw = _mm256_loadu_si256((const __m256i *)((const uint16_t *)w + i));
    if (dt == HEARTH_F16)
        return _mm512_cvtph_ps(raw);
    const __m512i wide = _mm512_cvtepu16_epi32(raw);
    return _mm512_castsi512_ps(_mm512_sllv_epi32(wide, _mm512_set1_epi32(16)));
}

static void mk_float_rows(int dt, const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0,
                          int64_t r1)
{
    const size_t stride = hx_row_bytes(dt, n);
    for (int64_t row = r0; row < r1; ++row) {
        const uint8_t *wrow = (const uint8_t *)W + (size_t)row * stride;
        for (int tok = 0; tok < T; ++tok) {
            const float *xr = (const float *)act + (size_t)tok * (size_t)n;
            __m512 acc = _mm512_setzero_ps();
            for (int64_t k = 0; k + 16 <= n; k += 16)
                acc = _mm512_add_ps(_mm512_mul_ps(_mm512_loadu_ps(xr + k), mk_load16(dt, wrow, k)), acc);
            Y[tok * ldy + row] = tree16(acc);
        }
    }
}

static void mk_f32_avx512(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_float_rows(HEARTH_F32, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_f16_avx512(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_float_rows(HEARTH_F16, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_bf16_avx512(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_float_rows(HEARTH_BF16, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_quant_rows(int nibbles, const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy,
                          int64_t r0, int64_t r1)
{
    const int64_t blocks = n / 64;
    const size_t bsize = nibbles ? MK_Q4_BLOCK : MK_Q8_BLOCK;
    for (int64_t row = r0; row < r1; ++row) {
        const uint8_t *wrow = (const uint8_t *)W + (size_t)row * (size_t)blocks * bsize;
        for (int tok = 0; tok < T; ++tok) {
            const hx_act_q8 *xa = (const hx_act_q8 *)act + (size_t)tok * (size_t)blocks;
            float total = 0.0f;
            for (int64_t blk = 0; blk < blocks; ++blk) {
                const __m512i wq = _mm512_loadu_si512((const void *)(wrow + (size_t)blk * bsize + 2));
                const __m512i xq = _mm512_loadu_si512((const void *)xa[blk].q);
                const int32_t dot = hsum_i32(_mm512_dpbusd_epi32(_mm512_setzero_si512(), wq, xq));
                uint16_t scale_bits;
                memcpy(&scale_bits, wrow + (size_t)blk * bsize, 2);
                total = total + hx_f16_to_f32(scale_bits) * xa[blk].d * (float)dot;
            }
            Y[tok * ldy + row] = total;
        }
    }
}

static void mk_q8_avx512(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_quant_rows(0, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_q4_avx512(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_quant_rows(1, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_act_avx512(const float *x, hx_act_q8 *out, int64_t n)
{
    const __m512i absbits = _mm512_set1_epi32(0x7fffffff);
    for (int64_t blk = 0; blk < n / 64; ++blk) {
        __m512 peak = _mm512_setzero_ps();
        for (int e = 0; e < 64; e += 16) {
            const __m512i bits = _mm512_castps_si512(_mm512_loadu_ps(x + blk * 64 + e));
            peak = _mm512_max_ps(_mm512_castsi512_ps(_mm512_and_si512(absbits, bits)), peak);
        }
        const float top = _mm512_reduce_max_ps(peak);
        const float scale = top / 127.0f, inv = scale != 0.0f ? 1.0f / scale : 0.0f;
        const __m512 vinv = _mm512_set1_ps(inv), magic = _mm512_set1_ps(12582912.0f);
        int32_t total = 0;
        for (int e = 0; e < 64; e += 16) {
            const __m512 shifted = _mm512_add_ps(magic, _mm512_mul_ps(vinv, _mm512_loadu_ps(x + blk * 64 + e)));
            const __m512i qv = _mm512_cvttps_epi32(_mm512_sub_ps(shifted, magic));
            _mm_storeu_si128((__m128i *)(out[blk].q + e), _mm512_cvtepi32_epi8(qv));
            total += _mm512_reduce_add_epi32(qv);
        }
        out[blk].d = scale;
        out[blk].sum = total;
    }
}

static const hx_kernels k_avx512 = {
    HEARTH_ISA_AVX512,
    {mk_f32_avx512, mk_f16_avx512, mk_bf16_avx512, mk_q8_avx512, mk_q4_avx512, NULL, NULL},
    mk_act_avx512,
};

const hx_kernels *hx_kernels_avx512_table(void) { return &k_avx512; }
