/* Provenance: written by reviewer 2 of the x0prep review (Claude, same family, independent context), 2026-10-16;
 * adopted unchanged below this comment by the x0prep reviser as a regression input of runbook step 72
 * (expected outcomes: tricky_expect.json). NOT Hearth code. */
/* rv_tricky2.c -- adversarial extraction tests, part 2 (review of track x0prep). NOT Hearth code.
 *   rv_coldsw2 : dense switch whose LAST cases call a cold function (GCC moves them to .cold): silent truncation?
 *   rv_pf      : indirect tail call; the only jump table in the closure belongs to rv_pf_b (name-prefix match)
 */
#include <stdint.h>
#include <stddef.h>

#if defined(_MSC_VER) && !defined(__clang__)
#define RV_NOINLINE __declspec(noinline)
#define RV_COLD __declspec(noinline)
#else
#define RV_NOINLINE __attribute__((noinline))
#define RV_COLD __attribute__((cold, noinline))
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

RV_COLD static void rv_cold(int c)
{
    rv_ext_log("cold");
    rv_sink = c;
}

static void rv_coldsw2(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    (void)W; (void)n; (void)act; (void)T; (void)ldy;
    for (int64_t r = r0; r < r1; r++) {
        switch ((int)(r % 8)) {
        case 0: rv_sink = 200; Y[r] = Y[r] * 1.5f; break;
        case 1: rv_sink = 201; Y[r] = Y[r] + 2.5f; break;
        case 2: rv_sink = 202; Y[r] = Y[r] * 3.0f; break;
        case 3: rv_sink = 203; Y[r] = Y[r] - 1.0f; break;
        case 4: rv_sink = 204; Y[r] = Y[r] + 4.0f; break;
        case 5: rv_cold(5); rv_sink = 205; Y[r] = Y[r] - 6.0f; break;
        case 6: rv_cold(6); rv_sink = 206; Y[r] = Y[r] * Y[r]; break;
        default: rv_sink = 207; Y[r] = Y[r] * 0.125f; break;
        }
    }
}

static RV_NOINLINE void rv_pf_b(float *Y, int k)
{
    switch (k & 7) {
    case 0: rv_sink = 300; Y[0] = Y[0] * 2.0f; break;
    case 1: rv_sink = 301; Y[1] = Y[1] + 3.0f; break;
    case 2: rv_sink = 302; Y[2] = Y[2] - 5.0f; break;
    case 3: rv_sink = 303; Y[3] = Y[3] * Y[4]; break;
    case 4: rv_sink = 304; Y[5] = Y[5] / 7.0f; break;
    case 5: rv_sink = 305; Y[6] = Y[6] + Y[7]; break;
    case 6: rv_sink = 306; Y[8] = Y[8] * 11.0f; break;
    default: rv_sink = 307; Y[9] = Y[9] - Y[10]; break;
    }
}

static void rv_pf(const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1)
{
    (void)W; (void)ldy; (void)r1;
    if (T > 3) {
        rv_pf_b(Y, (int)r0);
        rv_sink = 1;
        return;
    }
    ((rv_cb)act)(Y, n);
}

static void rv_act2(const float *x, void *out, int64_t n)
{
    float *o = (float *)out;
    for (int64_t i = 0; i < n; i++) o[i] = x[i] * 0.5f;
}

static const rv_kernels rv_table2 = {
    1,
    {rv_coldsw2, rv_pf, NULL, NULL, NULL, NULL, NULL},
    rv_act2,
};

const rv_kernels *rv_table2_get(void) { return &rv_table2; }
