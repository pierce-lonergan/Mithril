/* reduce_probe.c -- X0 arm P (record §3, "reduce probe"). NOT Hearth code; never part of the main union.
 *
 * Hearth at b5d3f14 calls no _mm512_reduce_* intrinsic (record §4.5), but ROADMAP §3.1 and 04-toolchain
 * §7.1(c) ask how sequence intrinsics such as _mm512_reduce_add_ps are lowered. Each main-union
 * configuration (A, A-ninja, B-cmake, C, D) compiles this file with the exact command line it uses for
 * quant_avx512.c (x0_flags.py replay --as quant_avx512.c --src probes/reduce_probe.c). The census then
 * records each wrapper's emitted iclass sequence and its lane pairing, and compares the pairing with the
 * XML's halving tree for _mm512_reduce_add_ps (lanes j and j+8, then +4, +2, +1) [G02 §6].
 *
 * Intel defines the _reduce_ sequence intrinsics for 512-bit vectors only (for these element types), so the
 * probe has one translation unit, for the AVX-512 flag set. The AVX2 and scalar files have no counterpart.
 *
 * Every wrapper is noinline and has external linkage, so each lowering is a separate function in the object
 * and is found through the symbol table (the probe is not a dispatch table).
 */
#include <immintrin.h>

#if defined(_MSC_VER) && !defined(__clang__)
#define PROBE_NOINLINE __declspec(noinline)
#else
#define PROBE_NOINLINE __attribute__((noinline))
#endif

PROBE_NOINLINE float x0_probe_reduce_add_ps(__m512 v) { return _mm512_reduce_add_ps(v); }

PROBE_NOINLINE float x0_probe_reduce_max_ps(__m512 v) { return _mm512_reduce_max_ps(v); }

PROBE_NOINLINE int x0_probe_reduce_add_epi32(__m512i v) { return _mm512_reduce_add_epi32(v); }

/* The same three through memory, so that the census also sees the lowering when the source vector is
 * loaded rather than passed in a register (ABI-independent: Win64 passes __m512 by reference). */
PROBE_NOINLINE float x0_probe_reduce_add_ps_mem(const float *p) { return _mm512_reduce_add_ps(_mm512_loadu_ps(p)); }

PROBE_NOINLINE float x0_probe_reduce_max_ps_mem(const float *p) { return _mm512_reduce_max_ps(_mm512_loadu_ps(p)); }

PROBE_NOINLINE int x0_probe_reduce_add_epi32_mem(const int *p)
{
    return _mm512_reduce_add_epi32(_mm512_loadu_si512((const void *)p));
}
