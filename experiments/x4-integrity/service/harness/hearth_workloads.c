/* hearth_workloads.c -- the Hearth workload set of x4harness_hearth.exe (X4-noise-pilot section 3).
 * X4 pilot track, 2026-10-23. Linked with the hearth-c-ref objects of Hearth b5d3f14 (clean CMake
 * Release build) and hearth_x4_shim.c; see service/tools/build_hearth_harness.bat.
 *
 *   mb_q4_avx512  the microbenchmark run type `mb-q4-avx512`: the shape of x3_bench (X3 DESIGN
 *                 section 8.2): n = 4096 columns, 240 rows x 2,176 B of Q4 weights (522,240 B,
 *                 L2-resident), activations 64 x 72 B, T = 1, one thread. Weights filled as
 *                 test_quant.c:1436-1456 (fill_weights, Q4 branch); activations from the AVX-512
 *                 table's act_quantize_q8 on seeded Gaussian input (test_quant.c:66-78, seed
 *                 0x9e3779b97f4a7c15). Init warms the kernel for 0.5 s into a private Y (X3 step 5,
 *                 untimed, inside the pre-START bound). The timed region is exactly K calls of
 *                 k->matmul[HEARTH_Q4](W, 4096, act, 1, Y, 240, 0, 240) with Y = the output extent
 *                 (960 B); K = param (default 65536). Output hashed: Y.
 *   e2e_decode    the end-to-end run type `e2e-decode`: hearth_open on the model named by the pinned
 *                 environment variable X4_MODEL_PATH (read-only, direct I/O, cold: warm_start 0) in
 *                 init; the timed region evaluates hearth_bench's 32 LCG-seeded prompt ids (seed 1,
 *                 hearth_bench.c) and then N greedy decode tokens (N = param, default 2048), copies the
 *                 last token's logits (vocab x 4 B) into the output extent and waits for the pool and
 *                 the store readers to go idle (x4h_quiesce). HEARTH_THREADS, HEARTH_IO_THREADS,
 *                 HEARTH_CACHE_GB, HEARTH_ISA and HEARTH_LOG come from the pinned environment block.
 *   dry_mb_tiny   DRY-RUN ONLY: mb_q4_avx512 without the 0.5 s warm-up and with a small default K, so
 *                 a dry night runs in minutes. Its runs are shorter than 1 s, so the out-of-process
 *                 bracket is ineligible on them by design (`bracket_too_short`); never a pilot run type.
 *   dry_quiesce_wake DRY/DEV ONLY (revision 4, review 2026-10-23): the quiescence race probe. Two
 *                 workers created through hx_thread_create (so through the shim) wait on one Hearth
 *                 condition variable; run() signals it `param` times (default 1000), each signal
 *                 followed at once by x4h_quiesce, and checks that the woken worker finished its job
 *                 (20 us of spin) before quiesce returned. Status 230 if quiesce returned while a
 *                 signalled worker had not yet run (the race the wake accounting closes), 231 if
 *                 quiesce timed out. Output: a fixed pattern.
 *
 * Status codes (the init status reaches the orchestrator in FAIL WORKLOAD's first field; a run status
 * is the report's WORKLOAD_RC, an integrity failure): 1xx microbenchmark, 2xx end-to-end.
 */
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "x4h.h"
#include "hx_quant.h"   /* hx_platform.h, hearth.h, the kernel table */

const char *const x4h_workload_set_name = "hearth-b5d3f14";

/* ------------------------------------------------------------ microbenchmark */
#define MB_COLS 4096
#define MB_ROWS 240                       /* floor(floor(524288 / 2176) / 16) * 16 (X3 section 8.2) */
#define MB_WARM_NS 500000000ull           /* X3 section 8.2 step 5 */
#define MB_DEFAULT_K 65536ull
#define DRY_DEFAULT_K 256ull

typedef struct {
    const hx_kernels *k;
    uint8_t *W;
    void *act;
    float *ywarm;
} mb_state;
static mb_state g_mb;

/* test_quant.c:66-78 (seeded SplitMix64, Box-Muller) */
static uint64_t g_rng;
static uint64_t rnd64(void) {
    uint64_t z = (g_rng += 0x9e3779b97f4a7c15ull);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
    return z ^ (z >> 31);
}
static double rnd_u(void) { return (double)(rnd64() >> 11) * (1.0 / 9007199254740992.0); }
static float rnd_gauss(void) {
    double u1 = rnd_u(), u2 = rnd_u();
    if (u1 < 1e-300) u1 = 1e-300;
    return (float)(sqrt(-2.0 * log(u1)) * cos(6.283185307179586 * u2));
}

/* test_quant.c:1436-1456, the Q4 branch: xorshift bytes, then every 34-byte block's scale = 0x2c00 */
static void mb_fill_weights(uint8_t *w, size_t bytes, size_t rb) {
    uint64_t s = 0x1234567ull;
    for (size_t i = 0; i + 8 <= bytes; i += 8) {
        s ^= s << 13; s ^= s >> 7; s ^= s << 17;
        memcpy(w + i, &s, 8);
    }
    const size_t bs = 34;
    for (size_t r = 0; r + rb <= bytes; r += rb)
        for (size_t g = 0; g < rb; g += bs) { w[r + g] = 0x00; w[r + g + 1] = 0x2c; }
}

static int mb_setup(x4h_ctx *ctx, int warm) {
    if (ctx->out_bytes != (size_t)MB_ROWS * 4u) return 101;
    const hx_kernels *k = hx_kernels_for(HEARTH_ISA_AVX512);
    if (!k || k->isa != HEARTH_ISA_AVX512 || !k->matmul[HEARTH_Q4] || !k->act_quantize_q8) return 102;
    const size_t rb = hx_row_bytes(HEARTH_Q4, MB_COLS);
    if (rb != 2176u || hx_act_bytes(HEARTH_Q4, MB_COLS) != 64u * 72u) return 103;
    g_mb.k = k;
    g_mb.W = (uint8_t *)hx_aligned_alloc(64, rb * MB_ROWS);
    g_mb.act = hx_aligned_alloc(64, hx_act_bytes(HEARTH_Q4, MB_COLS));
    g_mb.ywarm = (float *)hx_aligned_alloc(64, (size_t)MB_ROWS * 4u);
    float *x = (float *)hx_aligned_alloc(64, (size_t)MB_COLS * 4u);
    if (!g_mb.W || !g_mb.act || !g_mb.ywarm || !x) return 104;
    mb_fill_weights(g_mb.W, rb * MB_ROWS, rb);
    g_rng = 0x9e3779b97f4a7c15ull;
    for (int i = 0; i < MB_COLS; i++) x[i] = rnd_gauss();
    k->act_quantize_q8(x, (hx_act_q8 *)g_mb.act, MB_COLS);
    hx_aligned_free(x);
    if (warm) {
        const uint64_t end = x4h_now_ns() + MB_WARM_NS;
        do {
            k->matmul[HEARTH_Q4](g_mb.W, MB_COLS, g_mb.act, 1, g_mb.ywarm, MB_ROWS, 0, MB_ROWS);
        } while (x4h_now_ns() < end);
    }
    ctx->state = &g_mb;
    return 0;
}

static int mb_init(x4h_ctx *ctx) { return mb_setup(ctx, 1); }
static int dry_init(x4h_ctx *ctx) { return mb_setup(ctx, 0); }

static int mb_loop(x4h_ctx *ctx, uint64_t k_default) {
    mb_state *s = (mb_state *)ctx->state;
    float *Y = (float *)ctx->out;
    const uint64_t K = ctx->param ? ctx->param : k_default;
    for (uint64_t i = 0; i < K; i++)
        s->k->matmul[HEARTH_Q4](s->W, MB_COLS, s->act, 1, Y, MB_ROWS, 0, MB_ROWS);
    return 0;
}
static int mb_run(x4h_ctx *ctx) { return mb_loop(ctx, MB_DEFAULT_K); }
static int dry_run(x4h_ctx *ctx) { return mb_loop(ctx, DRY_DEFAULT_K); }

/* ------------------------------------------------------------- end to end */
#define E2E_PROMPT 32
#define E2E_DEFAULT_N 2048ull
#define E2E_QUIESCE_NS 10000000000ull     /* 10 s, as the harness's own I/O join */

typedef struct {
    hearth_engine *e;
    hearth_model_info info;
    float *logits;
    int32_t prompt[E2E_PROMPT];
    uint64_t n_decode;
} e2e_state;
static e2e_state g_e2e;

static int argmax(const float *x, int n) {   /* hearth_bench.c bench_argmax */
    int b = 0;
    for (int i = 1; i < n; i++)
        if (x[i] > x[b]) b = i;
    return b;
}

static int e2e_init(x4h_ctx *ctx) {
    const char *path = getenv("X4_MODEL_PATH");
    if (!path || !*path) return 201;
    g_e2e.n_decode = ctx->param ? ctx->param : E2E_DEFAULT_N;
    hearth_options o;
    hearth_default_options(&o);
    o.model_path = path;
    o.direct_io = 1;      /* cold: the standby list never holds model bytes (MEASUREMENT section 3) */
    o.warm_start = 0;
    o.isa = HEARTH_ISA_AVX512;
    o.max_seq = (int)(E2E_PROMPT + g_e2e.n_decode + 1);   /* hearth_bench's default */
    char err[512];
    err[0] = 0;
    g_e2e.e = hearth_open(&o, err, sizeof err);
    if (!g_e2e.e) return 202;
    if (hearth_info(g_e2e.e, &g_e2e.info) != 0) return 203;
    if (g_e2e.info.isa != HEARTH_ISA_AVX512) return 204;
    if (g_e2e.info.vocab_size <= 0 || (size_t)g_e2e.info.vocab_size * 4u != ctx->out_bytes) return 205;
    g_e2e.logits = (float *)malloc((size_t)g_e2e.info.vocab_size * 4u);
    if (!g_e2e.logits) return 206;
    uint64_t seed = 1;    /* hearth_bench.c: --seed default 1, LCG */
    for (int i = 0; i < E2E_PROMPT; i++) {
        seed = seed * 6364136223846793005ull + 1442695040888963407ull;
        g_e2e.prompt[i] = (int32_t)((seed >> 33) % (unsigned long long)g_e2e.info.vocab_size);
    }
    ctx->state = &g_e2e;
    return 0;
}

static int e2e_run(x4h_ctx *ctx) {
    e2e_state *s = (e2e_state *)ctx->state;
    const int V = s->info.vocab_size;
    if (hearth_eval(s->e, s->prompt, E2E_PROMPT, s->logits, 0) != 0) return 210;
    int next = argmax(s->logits, V);
    for (uint64_t i = 0; i < s->n_decode; i++) {
        if (hearth_eval(s->e, &next, 1, s->logits, 0) != 0) return 211;
        next = argmax(s->logits, V);
    }
    memcpy(ctx->out, s->logits, (size_t)V * 4u);
    if (x4h_quiesce(E2E_QUIESCE_NS) != 0) return 212;
    return 0;
}

static const x4h_workload wl_mb = { "mb_q4_avx512", mb_init, mb_run, NULL };
static const x4h_workload wl_e2e = { "e2e_decode", e2e_init, e2e_run, NULL };
static const x4h_workload wl_dry = { "dry_mb_tiny", dry_init, dry_run, NULL };

/* ------------------------------------------------------- the quiescence race probe (dry/dev) */
#define QW_DEFAULT_N 1000ull
typedef struct {
    hx_mutex mu;
    hx_cond cv;
    int go, stop;
    uint64_t done;
    hx_thread *t[2];
} qw_state;
static qw_state g_qw;

static void *qw_worker(void *a) {
    qw_state *s = (qw_state *)a;
    hx_mutex_lock(&s->mu);
    for (;;) {
        while (!s->go && !s->stop) hx_cond_wait(&s->cv, &s->mu);
        if (s->stop) break;
        s->go = 0;
        hx_mutex_unlock(&s->mu);
        const uint64_t end = x4h_now_ns() + 20000u;   /* the job: 20 us of spin */
        while (x4h_now_ns() < end) {
        }
        hx_mutex_lock(&s->mu);
        s->done++;
    }
    hx_mutex_unlock(&s->mu);
    return NULL;
}

static int qw_init(x4h_ctx *ctx) {
    hx_mutex_init(&g_qw.mu);
    hx_cond_init(&g_qw.cv);
    for (int i = 0; i < 2; i++)
        if (hx_thread_create(&g_qw.t[i], qw_worker, &g_qw) != 0) return 220;
    ctx->state = &g_qw;
    return 0;
}

static int qw_run(x4h_ctx *ctx) {
    qw_state *s = (qw_state *)ctx->state;
    const uint64_t n = ctx->param ? ctx->param : QW_DEFAULT_N;
    for (uint64_t i = 0; i < n; i++) {
        hx_mutex_lock(&s->mu);
        s->go = 1;
        hx_cond_signal(&s->cv);
        hx_mutex_unlock(&s->mu);
        if (x4h_quiesce(1000000000ull) != 0) return 231;
        hx_mutex_lock(&s->mu);
        const uint64_t d = s->done;
        hx_mutex_unlock(&s->mu);
        if (d != i + 1) return 230;
    }
    for (size_t k = 0; k < ctx->out_bytes; k++) ctx->out[k] = (uint8_t)(0x3c ^ k);
    return 0;
}

static const x4h_workload wl_qw = { "dry_quiesce_wake", qw_init, qw_run, NULL };

const x4h_workload *const x4h_workloads[] = { &wl_mb, &wl_e2e, &wl_dry, &wl_qw, NULL };
