/* smoke_dispatch.c -- X0 smoke test for slot mapping, recursive descent and call kinds (record §4.1, §4.2).
 * NOT Hearth code; never part of the census. It mirrors the SHAPE of Hearth's dispatch tables (an int field,
 * a 7-entry array of matmul function pointers with two NULL entries, one activation-quantiser pointer) so
 * that x0_extract.py / x0_decode.py can be validated on every configuration before freeze.
 *
 * Compile it with each configuration's exact quant_avx512.c command AND its exact quant.c command
 * (x0_flags.py replay --as ... --src smoke/smoke_dispatch.c). Without AVX-512 flags the scalar branches are
 * used, so the same file exercises legacy-SSE and AVX-512 code.
 *
 * What it exercises:
 *   two tables (one static, one with external linkage), 6 non-NULL slots each, 2 NULL slots each;
 *   slot functions with internal linkage (static), resolved only through the table's relocations;
 *   a shared internal callee reached from two slots (sd_float_common);
 *   an external-linkage callee defined here (sd_row_bytes): interposable under ELF -fPIC, internal on COFF;
 *   undefined callees: expf (libm, an FP trust dependency), sd_external_log (unknown, conservative: FP trust),
 *     memcpy with a variable size (allow-listed, not FP);
 *   switch statements dense enough for jump tables (MSVC: in .text after the function; GCC/Clang: .rodata);
 *   a cold path (GCC: foo.cold in .text.unlikely);
 *   q_rint's magic constant pair (v + 12582912.0f) - 12582912.0f (canary d1 shape);
 *   a 16-lane accumulator loop and the s = 8, 4, 2, 1 tree (canary d2 shape);
 *   a local byte array whose address escapes (GCC stack protector; MSVC /GS cookie).
 */
#include <immintrin.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#if defined(_MSC_VER) && !defined(__clang__)
#define SD_NOINLINE __declspec(noinline)
#define SD_UNLIKELY(x) (x)
#define SD_COLD __declspec(noinline)
#else
#define SD_NOINLINE __attribute__((noinline))
#define SD_UNLIKELY(x) __builtin_expect(!!(x), 0)
#define SD_COLD __attribute__((cold, noinline))
#endif

typedef void (*sd_matmul_fn)(const void *W, int64_t n, const void *act, int T,
                             float *Y, int64_t ldy, int64_t r0, int64_t r1);

typedef struct sd_kernels {
    int isa;
    sd_matmul_fn matmul[7];
    void (*act_quantize)(const float *x, void *out, int64_t n);
} sd_kernels;

volatile int sd_sink;
void sd_external_log(const char *msg);   /* undefined in this object */
size_t sd_row_bytes(int dt, int64_t n);  /* defined below with external linkage */

SD_COLD static void sd_fail(int code)
{
    sd_external_log("smoke_dispatch: bad argument");
    sd_sink = code;
}

size_t sd_row_bytes(int dt, int64_t n)
{
    switch (dt) {
    case 0: sd_sink = 1; return (size_t)n * 4;
    case 1: sd_sink = 2; return (size_t)n * 2;
    case 2: sd_sink = 3; return (size_t)n * 2 + 1;
    case 3: sd_sink = 4; return (size_t)(n / 64) * 66;
    case 4: sd_sink = 5; return (size_t)(n / 64) * 34;
    case 5: sd_sink = 6; return (size_t)n * 4 + 3;
    case 6: sd_sink = 7; return (size_t)n;
    case 7: sd_sink = 8; return (size_t)n * 8;
    default: return 0;
    }
}

static float sd_tree16(float *L)
{
    for (int s = 8; s >= 1; s >>= 1)
        for (int j = 0; j < s; j++) L[j] = L[j] + L[j + s];
    return L[0];
}

static float sd_rint(float v)
{
    const float magic = 12582912.0f;
    return (v + magic) - magic;
}

static SD_NOINLINE void sd_float_common(int dt, const void *W, int64_t n, const void *act, int T,
                                        float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    const float *X = (const float *)act;
    const size_t rb = sd_row_bytes(dt, n);
    for (int64_t r = r0; r < r1; r++) {
        const float *w = (const float *)((const uint8_t *)W + (size_t)r * rb);
        for (int t = 0; t < T; t++) {
            float L[16] = {0};
            const float *x = X + (size_t)t * (size_t)n;
#if defined(__AVX512F__)
            __m512 a = _mm512_setzero_ps();
            int64_t i = 0;
            for (; i + 16 <= n; i += 16)
                a = _mm512_add_ps(a, _mm512_mul_ps(_mm512_loadu_ps(w + i), _mm512_loadu_ps(x + i)));
            _mm512_storeu_ps(L, a);
            for (; i < n; i++) L[i & 15] = L[i & 15] + w[i] * x[i];
#else
            for (int64_t i = 0; i < n; i++) L[i & 15] = L[i & 15] + w[i] * x[i];
#endif
            Y[t * ldy + r] = sd_tree16(L);
        }
    }
}

static void sd_f32(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    if (SD_UNLIKELY(n < 0 || T < 0))
        sd_fail(1);
    sd_float_common(0, W, n, act, T, Y, ldy, r0, r1);
}

static void sd_f16(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    sd_float_common(1, W, n, act, T, Y, ldy, r0, r1);
}

static void sd_bf16(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    sd_float_common(2, W, n, act, T, Y, ldy, r0, r1);
}

static void sd_q8(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    const int8_t *w = (const int8_t *)W;
    const int8_t *a = (const int8_t *)act;
    for (int64_t r = r0; r < r1; r++) {
        int32_t isum = 0;
        float acc = 0.0f;
        for (int64_t i = 0; i < n; i++) isum += (int32_t)w[r * n + i] * (int32_t)a[i];
        switch ((int)(r % 10)) {
        case 0: acc = (float)isum; break;
        case 1: acc = (float)isum * 0.5f; break;
        case 2: acc = (float)isum + 1.0f; break;
        case 3: acc = (float)(isum ^ 0x55); break;
        case 4: acc = (float)(isum << 2); break;
        case 5: acc = (float)(isum >> 1); break;
        case 6: acc = (float)(~isum); break;
        case 7: acc = (float)isum * (float)isum; break;
        case 8: acc = (float)(isum / 5); break;
        default: acc = (float)(isum % 13); break;
        }
        for (int t = 0; t < T; t++) Y[t * ldy + r] = acc;
    }
}

static void sd_q4(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    float tmp[64];
    size_t k = (size_t)(n < 64 ? n : 64);
    memcpy(tmp, W, k * sizeof(float));
    (void)act;
    for (int64_t r = r0; r < r1; r++)
        for (int t = 0; t < T; t++)
            Y[t * ldy + r] = expf(tmp[(size_t)r % (k ? k : 1)]);
}

static void sd_act(const float *x, void *out, int64_t n)
{
    char buf[64];
    int8_t *q = (int8_t *)out;
    float amax = 0.0f, id;
    for (int64_t i = 0; i < n; i++) {
        float a = fabsf(x[i]);
        if (a > amax) amax = a;
    }
    id = amax != 0.0f ? 127.0f / amax : 0.0f;
    for (int64_t i = 0; i < n; i++) {
        float v = x[i] * id;
        v = v > 127.0f ? 127.0f : (v < -127.0f ? -127.0f : v);
        q[i] = (int8_t)sd_rint(v);
    }
    memcpy(buf, out, (size_t)(n < 64 ? n : 64));
    sd_external_log(buf);
}

static const sd_kernels sd_table = {
    1,
    {sd_f32, sd_f16, sd_bf16, sd_q8, sd_q4, NULL, NULL},
    sd_act,
};

const sd_kernels sd_table_global = {
    2,
    {sd_f16, sd_f32, sd_q8, sd_bf16, sd_q4, NULL, NULL},
    sd_act,
};

const sd_kernels *sd_table_get(void) { return &sd_table; }
