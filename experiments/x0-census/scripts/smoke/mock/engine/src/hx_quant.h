/* hx_quant.h -- X0 census MOCK. NOT Hearth code; never part of the census.
 *
 * Written by the x0final track (2026-10-16) so that the census driver (runbook steps 80-82, x0_driver.py
 * census mode) can be run end to end before freeze -- configure, two clean builds, the debug-info twin, extract,
 * decode, loops, attribution, assembly and judge.py -- on a project with the SHAPE of Hearth's dispatch tables
 * (one int, a 7-entry matmul array indexed F32, F16, BF16, Q8, Q4, I32, U8 with I32/U8 NULL, one activation
 * quantiser; tables hx_kernels_scalar, k_avx2, k_avx512; 18 variants) and the flag logic of Hearth's
 * CMakeLists.txt.
 *
 * Correction (x0final revision after the independent review of 2026-10-16/17, record §2 and §12): the first
 * version of this mock was NOT only "small stand-ins written for this test". Its helpers tree16 (both SIMD files),
 * canon4, red8, hsum_i32, q_rint, the bf16 load and dot16_conv's tree loop were copied verbatim from Hearth
 * b5d3f14, and they were compiled and analysed before freeze (record §2 disclosure). Every helper and kernel of
 * this version is written afresh with other intrinsics and other text; x0_driver.py now refuses a smoke source that
 * shares three consecutive non-trivial lines with any pinned Hearth file (class/hearth_shingles.json). What the
 * mock exercises: the d1 canary shape (v + M) - M that the record itself defines; a 16-lane accumulator in each
 * SIMD file; a tree16 in quant_avx512.c that computes the record's s = 8, 4, 2, 1 pairing through other
 * instructions (P3(d2) must say match) and a tree16 in quant_avx2.c that deliberately pairs adjacent lanes first
 * (s = 1, 2, 4, 8; P3(d2) must say mismatch); an interposable call under ELF -fPIC; a stack array (stack protector,
 * /GS); and _mm512_dpbusd_epi32 (clang-cl's /arch:AVX512 lacks VNNI, so B-cmake is expected to fail to compile the
 * mock's quant_avx512.c, a genuine compile_failed).
 */
#ifndef X0MOCK_HX_QUANT_H
#define X0MOCK_HX_QUANT_H

#include <stddef.h>
#include <stdint.h>

#define HEARTH_ISA_SCALAR 0
#define HEARTH_ISA_AVX2 1
#define HEARTH_ISA_AVX512 2
#define HEARTH_F32 0
#define HEARTH_F16 1
#define HEARTH_BF16 2
#define HEARTH_Q8 3
#define HEARTH_Q4 4

#if defined(_MSC_VER) && !defined(__clang__)
#define HX_INLINE static __forceinline
#else
#define HX_INLINE static inline __attribute__((always_inline))
#endif

typedef struct hx_act_q8 {
    float d;
    int32_t sum;
    int8_t q[64];
} hx_act_q8;

/* one matmul kernel of the mock: rows [first, last) of W times the T activation rows */
typedef void (*hx_matmul_fn)(const void *wmat, int64_t ncol, const void *xact, int ntok, float *yout, int64_t ystride,
                             int64_t first, int64_t last);

/* the dispatch table (Hearth's shape: isa, matmul[7], act_quantize_q8) */
typedef struct hx_kernels {
    int isa;
    hx_matmul_fn matmul[7];
    void (*act_quantize_q8)(const float *x, hx_act_q8 *out, int64_t n);
} hx_kernels;

extern const hx_kernels hx_kernels_scalar;
const hx_kernels *hx_kernels_avx2_table(void);
const hx_kernels *hx_kernels_avx512_table(void);

size_t hx_row_bytes(int dt, int64_t n);
float hx_f16_to_f32(uint16_t h);
float hx_bf16_to_f32(uint16_t h);

#endif
