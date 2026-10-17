/* quant.c -- X0 census MOCK, scalar table. NOT Hearth code (see hx_quant.h); rewritten by the x0final revision
 * (2026-10-17) without any line of Hearth's helpers. */
#include "hx_quant.h"

#include <math.h>
#include <string.h>

#define MK_Q8_BLOCK 66
#define MK_Q4_BLOCK 34

size_t hx_row_bytes(int dt, int64_t n)
{
    switch (dt) {
    case HEARTH_F32: return (size_t)n * 4;
    case HEARTH_F16: return (size_t)n * 2;
    case HEARTH_BF16: return (size_t)n * 2;
    case HEARTH_Q8: return (size_t)(n / 64) * MK_Q8_BLOCK;
    case HEARTH_Q4: return (size_t)(n / 64) * MK_Q4_BLOCK;
    default: return 0;
    }
}

float hx_f16_to_f32(uint16_t h)
{
    uint32_t s = (uint32_t)(h & 0x8000) << 16, e = (h >> 10) & 31, m = h & 1023, bits;
    float f;
    if (e == 0)
        bits = s;
    else if (e == 31)
        bits = s | 0x7f800000u | (m << 13);
    else
        bits = s | ((e + 112) << 23) | (m << 13);
    memcpy(&f, &bits, 4);
    return f;
}

float hx_bf16_to_f32(uint16_t h)
{
    union { uint32_t u; float f; } cvt;
    cvt.u = ((uint32_t)h) * 65536u;
    return cvt.f;
}

/* the record's d1 canary shape: add M = 12582912.0f, then subtract it again */
static float mk_round_near(float x)
{
    float shifted = x + 12582912.0f;
    return shifted - 12582912.0f;
}

static float mk_weight(int dt, const void *w, int64_t i)
{
    if (dt == HEARTH_F32) return ((const float *)w)[i];
    if (dt == HEARTH_F16) return hx_f16_to_f32(((const uint16_t *)w)[i]);
    return hx_bf16_to_f32(((const uint16_t *)w)[i]);
}

/* 16 partial sums (index modulo 16), then folded by halving: 16 -> 8 -> 4 -> 2 -> 1 */
static float mk_dot16(int dt, const void *w, const float *x, int64_t n)
{
    float part[16];
    memset(part, 0, sizeof part);
    for (int64_t k = 0; k < n; ++k)
        part[k % 16] += mk_weight(dt, w, k) * x[k];
    for (int half = 8; half > 0; half /= 2) {
        for (int q = 0; q < half; ++q)
            part[q] += part[q + half];
    }
    return part[0];
}

static void mk_float_rows(int dt, const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy,
                          int64_t r0, int64_t r1)
{
    const size_t stride = hx_row_bytes(dt, n);
    for (int64_t row = r0; row < r1; ++row) {
        const uint8_t *wrow = (const uint8_t *)W + (size_t)row * stride;
        for (int tok = 0; tok < T; ++tok)
            Y[tok * ldy + row] = mk_dot16(dt, wrow, (const float *)act + (size_t)tok * n, n);
    }
}

static void mk_f32_scalar(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_float_rows(HEARTH_F32, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_f16_scalar(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_float_rows(HEARTH_F16, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_bf16_scalar(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
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
                const uint8_t *bp = wrow + (size_t)blk * bsize;
                uint16_t scale_bits;
                int32_t dot = 0;
                memcpy(&scale_bits, bp, 2);
                for (int e = 0; e < 64; ++e) {
                    int wv = nibbles ? (int)((bp[2 + e / 2] >> (4 * (e & 1))) & 15) - 8 : (int)(int8_t)bp[2 + e];
                    dot += wv * xa[blk].q[e];
                }
                total = total + hx_f16_to_f32(scale_bits) * xa[blk].d * (float)dot;
            }
            Y[tok * ldy + row] = total;
        }
    }
}

static void mk_q8_scalar(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_quant_rows(0, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_q4_scalar(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    mk_quant_rows(1, W, n, act, T, Y, ldy, r0, r1);
}

static void mk_act_scalar(const float *x, hx_act_q8 *out, int64_t n)
{
    for (int64_t blk = 0; blk < n / 64; ++blk) {
        const float *xb = x + blk * 64;
        float peak = 0.0f;
        int32_t total = 0;
        for (int e = 0; e < 64; ++e) {
            float mag = fabsf(xb[e]);
            if (mag > peak)
                peak = mag;
        }
        const float scale = peak / 127.0f, inv = scale != 0.0f ? 1.0f / scale : 0.0f;
        for (int e = 0; e < 64; ++e) {
            int qv = (int)mk_round_near(xb[e] * inv);
            qv = qv > 127 ? 127 : qv;
            qv = qv < -127 ? -127 : qv;
            out[blk].q[e] = (int8_t)qv;
            total += qv;
        }
        out[blk].d = scale;
        out[blk].sum = total;
    }
}

/* a helper outside every table (not a variant): an external libm call */
float hx_softmax_max(const float *x, int64_t n)
{
    float m = -INFINITY, s = 0.0f;
    for (int64_t i = 0; i < n; i++) m = x[i] > m ? x[i] : m;
    for (int64_t i = 0; i < n; i++) s += expf(x[i] - m);
    return s;
}

const hx_kernels hx_kernels_scalar = {
    HEARTH_ISA_SCALAR,
    {mk_f32_scalar, mk_f16_scalar, mk_bf16_scalar, mk_q8_scalar, mk_q4_scalar, NULL, NULL},
    mk_act_scalar,
};
