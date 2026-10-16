/* smoke.c -- X0 toolchain smoke test. NOT Hearth code; never part of the census.
 *
 * Exercises the extract/decode pipeline on all four configurations (MSVC, clang-cl,
 * GCC, Clang). Compile it with the flags Hearth gives quant_avx512.c, e.g.
 *   cl       /c /O2 /fp:precise /arch:AVX512 smoke.c
 *   clang-cl /c /O2 /fp:precise /arch:AVX512 smoke.c
 *   gcc   -c -O3 -ffp-contract=off -mavx512f -mavx512bw -mavx512vl -mavx512vnni -mavx2 -mfma -mf16c smoke.c
 *   clang -c -O3 -ffp-contract=off -mavx512f -mavx512bw -mavx512vl -mavx512vnni -mavx2 -mfma -mf16c smoke.c
 *
 * What each function is for:
 *   smoke_avx512_addmul   AVX-512 FP add + mul, unmasked (vaddps/vmulps zmm)
 *   smoke_avx512_masked   AVX-512 masked loads, masked FP mul, masked store (k-registers)
 *   smoke_avx2_dot        AVX2 + FMA intrinsics, horizontal add, scalar tail
 *   smoke_contract_probe  scalar a*b+c: shows whether the compiler contracts to FMA
 *   smoke_switch          dense switch: jump table (in .text for MSVC, .rodata/.rdata otherwise)
 *   smoke_sqrt_helper     static (local-symbol) function calling sqrtf
 */
#include <immintrin.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>

#if defined(_MSC_VER)
#define SMOKE_NOINLINE __declspec(noinline)
#else
#define SMOKE_NOINLINE __attribute__((noinline))
#endif

volatile int32_t smoke_sink;

void smoke_avx512_addmul(float *dst, const float *a, const float *b, size_t n)
{
    for (size_t i = 0; i + 16 <= n; i += 16) {
        __m512 x = _mm512_loadu_ps(a + i);
        __m512 y = _mm512_loadu_ps(b + i);
        __m512 s = _mm512_add_ps(x, y);
        __m512 p = _mm512_mul_ps(s, y);
        _mm512_storeu_ps(dst + i, p);
    }
}

void smoke_avx512_masked(float *dst, const float *a, const float *b, size_t n)
{
    size_t i = 0;
    for (; i + 16 <= n; i += 16) {
        __m512 x = _mm512_loadu_ps(a + i);
        __m512 y = _mm512_loadu_ps(b + i);
        _mm512_storeu_ps(dst + i, _mm512_mul_ps(x, y));
    }
    if (i < n) {
        __mmask16 m = (__mmask16)((1u << (unsigned)(n - i)) - 1u);
        __m512 x = _mm512_maskz_loadu_ps(m, a + i);
        __m512 y = _mm512_maskz_loadu_ps(m, b + i);
        __m512 p = _mm512_mask_mul_ps(x, m, x, y);
        _mm512_mask_storeu_ps(dst + i, m, p);
    }
}

float smoke_avx2_dot(const float *a, const float *b, size_t n)
{
    size_t i = 0;
    __m256 acc = _mm256_setzero_ps();
    for (; i + 8 <= n; i += 8)
        acc = _mm256_fmadd_ps(_mm256_loadu_ps(a + i), _mm256_loadu_ps(b + i), acc);
    __m128 lo = _mm256_castps256_ps128(acc);
    __m128 hi = _mm256_extractf128_ps(acc, 1);
    lo = _mm_add_ps(lo, hi);
    lo = _mm_hadd_ps(lo, lo);
    lo = _mm_hadd_ps(lo, lo);
    float r = _mm_cvtss_f32(lo);
    for (; i < n; ++i)
        r += a[i] * b[i]; /* contraction candidate */
    return r;
}

float smoke_contract_probe(float a, float b, float c)
{
    return a * b + c; /* FMA only if the compiler contracts */
}

int32_t smoke_switch(int32_t k, int32_t x)
{
    switch (k) {
    case 0: smoke_sink = x + 11; break;
    case 1: smoke_sink = x * 3; break;
    case 2: smoke_sink = x - 7; break;
    case 3: smoke_sink = x ^ 0x55; break;
    case 4: smoke_sink = x << 2; break;
    case 5: smoke_sink = x >> 1; break;
    case 6: smoke_sink = ~x; break;
    case 7: smoke_sink = x * x; break;
    case 8: smoke_sink = x / 5; break;
    case 9: smoke_sink = x % 13; break;
    default: return -1;
    }
    return smoke_sink;
}

static SMOKE_NOINLINE float smoke_sqrt_helper(float x)
{
    return sqrtf(x) * 0.5f;
}

float smoke_call_helper(float x)
{
    return smoke_sqrt_helper(x) + smoke_sqrt_helper(x + 1.0f);
}
