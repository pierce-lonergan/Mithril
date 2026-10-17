/* Provenance: written by reviewer 2 of the x0prep review (Claude, same family, independent context), 2026-10-16;
 * adopted unchanged below this comment by the x0prep reviser as a regression input of runbook step 72
 * (expected outcomes: tricky_expect.json). NOT Hearth code. */
/* rv_tricky.c -- adversarial extraction tests for x0_extract.py / x0_decode.py (review of track x0prep).
 * NOT Hearth code. Same table shape as smoke_dispatch.c (int, 7 matmul pointers, one act pointer).
 *   rv_tailsw   : dense switch + indirect tail call through a function pointer (expect unresolved_indirect)
 *   rv_coldsw   : dense switch whose cases 1 and 3 call a cold function (GCC may move them to .cold)
 *   rv_dieuser  : calls an internal noreturn function and an external user noreturn function
 *   rv_hookcall : calls through an EXTERN function-pointer variable, direct and hoisted into a register
 *   rv_overlap  : (GCC/Clang only) two reachable decodes that overlap
 *   rv_sparse   : sparse switch (MSVC two-level byte index table)
 */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>

#if defined(_MSC_VER) && !defined(__clang__)
#define RV_NOINLINE __declspec(noinline)
#define RV_COLD __declspec(noinline)
#define RV_NORET __declspec(noreturn)
#else
#define RV_NOINLINE __attribute__((noinline))
#define RV_COLD __attribute__((cold, noinline))
#define RV_NORET __attribute__((noreturn))
#endif

typedef void (*rv_matmul_fn)(const void *W, int64_t n, const void *act, int T,
                             float *Y, int64_t ldy, int64_t r0, int64_t r1);
typedef void (*rv_cb)(float *Y, int64_t n);

typedef struct rv_kernels {
    int isa;
    rv_matmul_fn matmul[7];
    void (*act_quantize)(const float *x, void *out, int64_t n);
} rv_kernels;

volatile int rv_sink;
void rv_ext_log(const char *msg);
RV_NORET void rv_ext_fatal(const char *msg);
extern void (*rv_hook)(float *Y, int64_t n);

static void rv_tailsw(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    (void)W; (void)T; (void)r1;
    switch ((int)(r0 & 7)) {
    case 0: rv_sink = 101; Y[0] = Y[0] * 2.0f; break;
    case 1: rv_sink = 102; Y[1] = Y[1] + 3.0f; break;
    case 2: rv_sink = 103; Y[2] = Y[2] - 5.0f; break;
    case 3: rv_sink = 104; Y[3] = Y[3] * Y[4]; break;
    case 4: rv_sink = 105; Y[5] = Y[5] / 7.0f; break;
    case 5: rv_sink = 106; Y[6] = Y[6] + Y[7]; break;
    case 6: rv_sink = 107; Y[8] = Y[8] * 11.0f; break;
    default: rv_sink = 108; Y[9] = Y[9] - Y[10]; break;
    }
    Y[ldy] = 1.0f;
    ((rv_cb)act)(Y, n);
}

RV_COLD static void rv_cold(int c)
{
    rv_ext_log("cold");
    rv_sink = c;
}

static void rv_coldsw(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    (void)W; (void)n; (void)act; (void)T; (void)ldy;
    for (int64_t r = r0; r < r1; r++) {
        switch ((int)(r % 8)) {
        case 0: rv_sink = 200; Y[r] = Y[r] * 1.5f; break;
        case 1: rv_cold(1); rv_sink = 201; Y[r] = Y[r] + 2.5f; break;
        case 2: rv_sink = 202; Y[r] = Y[r] * 3.0f; break;
        case 3: rv_cold(3); rv_sink = 203; Y[r] = Y[r] - 1.0f; break;
        case 4: rv_sink = 204; Y[r] = Y[r] + 4.0f; break;
        case 5: rv_sink = 205; Y[r] = Y[r] - 6.0f; break;
        case 6: rv_sink = 206; Y[r] = Y[r] * Y[r]; break;
        default: rv_sink = 207; Y[r] = Y[r] * 0.125f; break;
        }
    }
}

RV_NOINLINE RV_NORET static void rv_die(int c)
{
    rv_ext_log("die");
    rv_sink = c;
    abort();
}

static void rv_dieuser(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    (void)W; (void)act; (void)ldy;
    if (n < 0)
        rv_die(7);
    for (int64_t r = r0; r < r1; r++) Y[r] = (float)r * 0.5f;
    if (T > 1000)
        rv_ext_fatal("T");
}

static void rv_hookcall(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    (void)W; (void)act; (void)T; (void)ldy;
    rv_hook(Y, n);
    void (*h)(float *, int64_t) = rv_hook;
    for (int64_t r = r0; r < r1; r++) h(Y + r, n);
}

static void rv_overlap(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    (void)W; (void)act; (void)T; (void)ldy; (void)r1;
#if !defined(_MSC_VER)
    int out;
    __asm__ volatile(
        "xor %%eax, %%eax\n\t"
        "test %1, %1\n\t"
        "jz 1f\n\t"
        ".byte 0xb8\n\t"
        "1: nop\n\t"
        "nop\n\t"
        "nop\n\t"
        "nop\n\t"
        "mov %%eax, %0\n\t"
        : "=r"(out) : "r"((int)n) : "eax", "cc");
    rv_sink = out;
#else
    (void)n;
#endif
    Y[0] = (float)r0;
}

static void rv_sparse(const float *x, void *out, int64_t n)
{
    float *o = (float *)out;
    for (int64_t i = 0; i < n; i++) {
        int k = (int)x[i];
        switch (k) {
        case 0: rv_sink = 10; o[i] = 1.0f; break;
        case 1: rv_sink = 11; o[i] = 2.0f; break;
        case 2: rv_sink = 12; o[i] = x[i] * 3.0f; break;
        case 3: rv_sink = 13; break;
        case 30: rv_sink = 14; o[i] = -x[i]; break;
        case 31: rv_sink = 15; break;
        case 60: rv_sink = 16; o[i] = x[i] + 0.5f; break;
        case 61: rv_sink = 17; break;
        case 62: rv_sink = 18; o[i] = 0.0f; break;
        default: rv_sink = 19; break;
        }
    }
}

static const rv_kernels rv_table = {
    1,
    {rv_tailsw, rv_coldsw, rv_dieuser, rv_hookcall, rv_overlap, NULL, NULL},
    rv_sparse,
};

const rv_kernels *rv_table_get(void) { return &rv_table; }
