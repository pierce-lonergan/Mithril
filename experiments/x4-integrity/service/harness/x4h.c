/* x4h.c -- the C harness of the X4 measurement service v0 (F0). MEASUREMENT-SERVICE.md section 3.
 *
 * One process = one run. The orchestrator starts this exe suspended inside a Job Object (and, for
 * untrusted workloads, an AppContainer), passing the write end of a pipe, an output SECTION it created
 * (and maps read-only for its own copy and rehash), the poison salt and the declared affinity mask.
 * The harness: snapshots the allowed thread set and runs the workload's untimed init WITHOUT the
 * output extent (step 0); poisons the output extent after init, with a guard page after it (step 2);
 * sets the default MXCSR and wraps thread creation (step 3); sends START, takes t0, runs the workload
 * (steps 4-5); joins registered threads/parks and outstanding I/O, takes t1, sends STOP, snapshots
 * every thread's cycle count, freezes the output view read-only, takes a thread census -- MXCSR,
 * affinity, priority -- hashes the output, re-reads the cycle counts (post-t1 CPU rule) (step 6-7);
 * reports typed fields (step 8) and terminates itself with exit code 0. The harness never decides
 * whether the run counts; the orchestrator does (steps 8a, 9). Everything here shares an address
 * space with the workload: it is the precise record, not the trusted one.
 * With --selftest it runs the sandbox probes (SANDBOX.md section 5) rather than a workload.
 *
 * Build: cl /O2 /W4 /std:c11 /MT (MSVC 14.44). Depends on x4sb_probes.c for --selftest.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <intrin.h>
#include <xmmintrin.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include "x4h.h"
#include "x4proto.h"
#include "x4sb_probes.h"

#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "advapi32.lib")

#define X4H_MAX_THREADS 2048
#define X4H_MAX_REG 512

static uint64_t g_qpf = 1;
volatile uint64_t x4h_t0_ns;

uint64_t x4h_now_ns(void) {   /* Hearth hx_now_ns, platform_win.c:158 at b5d3f14 */
    LARGE_INTEGER c;
    QueryPerformanceCounter(&c);
    uint64_t t = (uint64_t)c.QuadPart;
    return (t / g_qpf) * 1000000000ull + (t % g_qpf) * 1000000000ull / g_qpf;
}

/* ------------------------------------------------------------------- pipe */
static HANDLE g_pipe = INVALID_HANDLE_VALUE;
static CRITICAL_SECTION g_pipe_cs;
static uint32_t g_seq;

static int pipe_write_all(const BYTE *p, DWORD n) {
    DWORD done = 0;
    while (done < n) {
        DWORD w = 0;
        if (!WriteFile(g_pipe, p + done, n - done, &w, NULL) || w == 0) return 0;
        done += w;
    }
    return 1;
}

/* One frame per call, header and payload in a single write so a reader never sees a torn frame from
 * this writer (the orchestrator's framer handles torn reads anyway). */
static BYTE g_frame[16 + (X4H_MAX_THREADS + 64) * X4P_CENSUS_W * 8];
static void send_msg(uint32_t type, const uint64_t *payload, uint32_t count) {
    EnterCriticalSection(&g_pipe_cs);
    uint32_t hdr[4] = { X4P_MAGIC, type, count * 8u, g_seq++ };
    if (g_pipe != INVALID_HANDLE_VALUE && 16u + count * 8u <= sizeof g_frame) {
        memcpy(g_frame, hdr, 16);
        if (count) memcpy(g_frame + 16, payload, count * 8u);
        pipe_write_all(g_frame, 16u + count * 8u);
    }
    LeaveCriticalSection(&g_pipe_cs);
}

static void send_fail(uint64_t code, uint64_t a, uint64_t b, uint64_t c) {
    uint64_t p[4] = { code, a, b, c };
    send_msg(X4P_FAIL, p, 4);
}

/* --------------------------------------------------------------- threads */
/* Registered threads: created through x4h_thread_create. The harness holds each one's OS thread id so
 * the census can tell a registered thread from one the workload created another way (a3/a3b). */
struct x4h_thread { HANDLE h; x4h_thread_fn fn; void *arg; DWORD tid; };

static DWORD g_reg_tid[X4H_MAX_REG];
static volatile LONG g_reg_n;
static volatile LONG g_reg_entry_mxcsr_bad;   /* registered threads whose MXCSR was non-default on entry */
static volatile LONG g_reg_exit_mxcsr_bad;    /* ... non-default when their fn returned (set-then-joined) */
static volatile LONG g_reg_exit_prio_bad;     /* ... priority not normal when their fn returned           */
static DWORD g_harness_tid;

/* parked / outstanding-I/O bookkeeping, read at t1 */
static volatile LONG g_parked[X4H_MAX_REG];   /* index by registration slot */
static DWORD __declspec(thread) t_reg_slot = (DWORD)-1;
static volatile LONG g_io_outstanding;

static unsigned int mxcsr_ctrl(void) { return _mm_getcsr() & X4P_MXCSR_CTRL_MASK; }

static DWORD WINAPI x4h_thread_main(LPVOID p) {
    struct x4h_thread *t = (struct x4h_thread *)p;
    /* step 3a: every registered thread asserts the default MXCSR on entry. */
    if (mxcsr_ctrl() != X4P_MXCSR_DEFAULT) InterlockedIncrement(&g_reg_entry_mxcsr_bad);
    _mm_setcsr(X4P_MXCSR_DEFAULT);
    LONG slot = InterlockedIncrement(&g_reg_n) - 1;
    if (slot < X4H_MAX_REG) { g_reg_tid[slot] = GetCurrentThreadId(); t_reg_slot = (DWORD)slot; }
    t->fn(t->arg);
    /* A worker that changed MXCSR or its priority and then returned (joined before the census) is
     * caught here. A value set and restored before return stays invisible in-process (binary T0, M4). */
    if (mxcsr_ctrl() != X4P_MXCSR_DEFAULT) InterlockedIncrement(&g_reg_exit_mxcsr_bad);
    if (GetThreadPriority(GetCurrentThread()) != THREAD_PRIORITY_NORMAL) InterlockedIncrement(&g_reg_exit_prio_bad);
    return 0;
}

int x4h_thread_create(x4h_thread **out, x4h_thread_fn fn, void *arg) {
    *out = NULL;
    struct x4h_thread *t = (struct x4h_thread *)calloc(1, sizeof *t);
    if (!t) return -1;
    t->fn = fn; t->arg = arg;
    t->h = CreateThread(NULL, 0, x4h_thread_main, t, 0, &t->tid);
    if (!t->h) { free(t); return -1; }
    *out = t;
    return 0;
}

void x4h_thread_join(x4h_thread *t) {
    if (!t) return;
    WaitForSingleObject(t->h, INFINITE);
    CloseHandle(t->h);
    free(t);
}

void x4h_thread_parked(int parked) {
    DWORD s = t_reg_slot;
    if (s < X4H_MAX_REG) InterlockedExchange(&g_parked[s], parked ? 1 : 0);
}

void x4h_io_begin(void) { InterlockedIncrement(&g_io_outstanding); }
void x4h_io_end(void)   { InterlockedDecrement(&g_io_outstanding); }

static int reg_slot_of(DWORD tid) {
    LONG n = g_reg_n;
    if (n > X4H_MAX_REG) n = X4H_MAX_REG;
    for (LONG i = 0; i < n; i++) if (g_reg_tid[i] == tid) return (int)i;
    return -1;
}

/* ----------------------------------------------------------------- poison */
/* The output extent is a view of the orchestrator's section (step 2): the bytes the orchestrator
 * copies and rehashes are the bytes the workload wrote. After init we fill it with 0xA5 and plant the
 * orchestrator's 64-bit salt across the first and the last 64-byte line, then after the run count how
 * many aligned words still hold poison or salt (a workload that forgot to write its output leaves
 * poison; a4/a13). The head before the extent is poisoned too and counted; the page after it is a
 * no-access guard page, so an overflowing write faults. */
static uint64_t g_salt;

static void poison_fill(uint8_t *p, size_t n, uint64_t salt) {
    memset(p, X4P_POISON_BYTE, n);
    if (n < 64) return;
    for (size_t i = 0; i < 64; i += 8) { memcpy(p + i, &salt, 8); memcpy(p + n - 64 + i, &salt, 8); }
}

static uint64_t poison_word(uint64_t salt, size_t word_index, size_t words) {
    if (word_index < 8 || word_index + 8 >= words) return salt;
    return 0xA5A5A5A5A5A5A5A5ull;
}

static uint64_t count_residual(const uint8_t *p, size_t n, uint64_t salt) {
    size_t words = n / 8;   /* n is a multiple of 64 (checked at start-up) */
    uint64_t resid = 0;
    for (size_t i = 0; i < words; i++) {
        uint64_t v;
        memcpy(&v, p + i * 8, 8);
        if (v == poison_word(salt, i, words)) resid++;
    }
    return resid;
}

static uint64_t count_changed(const uint8_t *p, size_t n) {
    uint64_t changed = 0;
    for (size_t i = 0; i < n; i++) if (p[i] != X4P_POISON_BYTE) changed++;
    return changed;
}

/* x4h_alloc: a fresh poisoned input buffer with a no-access guard page after it. */
void *x4h_alloc(size_t bytes) {
    SYSTEM_INFO si; GetSystemInfo(&si);
    size_t pg = si.dwPageSize;
    size_t body = (bytes + pg - 1) / pg * pg;
    uint8_t *base = (uint8_t *)VirtualAlloc(NULL, body + pg, MEM_RESERVE, PAGE_NOACCESS);
    if (!base) return NULL;
    if (!VirtualAlloc(base, body, MEM_COMMIT, PAGE_READWRITE)) { VirtualFree(base, 0, MEM_RELEASE); return NULL; }
    poison_fill(base, bytes, g_salt ? g_salt : 0xA5A5A5A5A5A5A5A5ull);
    return base;
}

/* -------------------------------------------------------- thread snapshots */
static ULONG64 read_cycles(HANDLE th) {
    ULONG64 c = 0;
    if (!QueryThreadCycleTime(th, &c)) return 0;
    return c;
}

static ULONGLONG thread_create_ft(HANDLE th) {
    FILETIME cr, ex, k, u;
    if (GetThreadTimes(th, &cr, &ex, &k, &u))
        return ((ULONGLONG)cr.dwHighDateTime << 32) | cr.dwLowDateTime;
    return 0;
}

/* Visit every thread of this process in a fresh Toolhelp snapshot. Returns -1 on snapshot failure. */
typedef void (*thread_visit_fn)(DWORD tid, void *ctx);
static int for_each_thread(thread_visit_fn fn, void *ctx) {
    DWORD pid = GetCurrentProcessId();
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (snap == INVALID_HANDLE_VALUE) return -1;
    THREADENTRY32 te; te.dwSize = sizeof te;
    int n = 0;
    if (Thread32First(snap, &te)) {
        do { if (te.th32OwnerProcessID == pid) { fn(te.th32ThreadID, ctx); n++; } } while (Thread32Next(snap, &te));
    } else n = -1;
    CloseHandle(snap);
    return n;
}

/* Allowed set: the threads that exist just before the workload's init runs (the harness thread and
 * the Windows loader's workers [inference; not observed here]). Any later thread that was not created
 * through x4h_thread_create is NEW_UNREGISTERED, however early in init it was created (a3/a3b). */
static DWORD g_pre_tid[X4H_MAX_THREADS];
static int g_pre_n;
static void visit_pre(DWORD tid, void *ctx) { (void)ctx; if (g_pre_n < X4H_MAX_THREADS) g_pre_tid[g_pre_n++] = tid; }
static int was_pre_init(DWORD tid) {
    for (int i = 0; i < g_pre_n; i++) if (g_pre_tid[i] == tid) return 1;
    return 0;
}

/* t1 snapshot: every thread alive right after STOP, with a query handle kept open so its cycle count
 * can be re-read after the hash even if it has exited meanwhile (step 6, post-t1 CPU rule). */
typedef struct { DWORD tid; HANDLE h; ULONG64 cyc_t1, cyc_hash; int in_census; } t1_entry;
static t1_entry g_t1[X4H_MAX_THREADS];
static int g_t1_n;
static uint64_t g_t1_errs;
static void visit_t1(DWORD tid, void *ctx) {
    (void)ctx;
    if (g_t1_n >= X4H_MAX_THREADS) { g_t1_errs++; return; }
    t1_entry *e = &g_t1[g_t1_n++];
    memset(e, 0, sizeof *e);
    e->tid = tid;
    e->h = OpenThread(THREAD_QUERY_LIMITED_INFORMATION, FALSE, tid);
    if (e->h) e->cyc_t1 = read_cycles(e->h); else g_t1_errs++;
}
static t1_entry *t1_find(DWORD tid) {
    for (int i = 0; i < g_t1_n; i++) if (g_t1[i].tid == tid) return &g_t1[i];
    return NULL;
}

/* ----------------------------------------------------------------- census */
typedef struct {
    DWORD tid;
    ULONG64 cyc_t1, cyc_hash;
    unsigned mxcsr;
    int priority;
    DWORD_PTR affinity;
    ULONGLONG create_ft;
    uint32_t flags;
} census_row;

static census_row g_rows[X4H_MAX_THREADS + 64];
static int g_rows_n;
static uint64_t g_census_errs;
static unsigned g_harness_mxcsr_after_run;

static int read_affinity(HANDLE th, DWORD_PTR *out) {
    GROUP_AFFINITY ga;
    ZeroMemory(&ga, sizeof ga);
    if (!GetThreadGroupAffinity(th, &ga)) return 0;   /* read-only getter; never moves the thread */
    *out = (DWORD_PTR)ga.Mask;
    return 1;
}

/* Census: every thread alive now. Non-harness threads are suspended in turn to read CONTEXT.MxCsr. */
static void visit_census(DWORD tid, void *ctx) {
    (void)ctx;
    if (g_rows_n >= X4H_MAX_THREADS) { g_census_errs++; return; }
    census_row *r = &g_rows[g_rows_n++];
    memset(r, 0, sizeof *r);
    r->tid = tid;
    if (tid == GetCurrentThreadId()) {
        r->flags |= X4P_CF_HARNESS;
        r->mxcsr = g_harness_mxcsr_after_run;
        r->priority = GetThreadPriority(GetCurrentThread());
        if (!read_affinity(GetCurrentThread(), &r->affinity)) { r->flags |= X4P_CF_OPEN_FAILED; g_census_errs++; }
        r->create_ft = thread_create_ft(GetCurrentThread());
        return;
    }
    HANDLE th = OpenThread(THREAD_QUERY_INFORMATION | THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT, FALSE, tid);
    if (!th) { r->flags |= X4P_CF_OPEN_FAILED; g_census_errs++; return; }
    r->priority = GetThreadPriority(th);
    r->create_ft = thread_create_ft(th);
    if (!read_affinity(th, &r->affinity)) { r->flags |= X4P_CF_OPEN_FAILED; g_census_errs++; }
    DWORD sc = SuspendThread(th);
    if (sc != (DWORD)-1) {
        CONTEXT c; ZeroMemory(&c, sizeof c);
        c.ContextFlags = CONTEXT_FLOATING_POINT | CONTEXT_CONTROL;
        if (GetThreadContext(th, &c)) r->mxcsr = c.MxCsr;
        else { r->flags |= X4P_CF_OPEN_FAILED; g_census_errs++; }
        ResumeThread(th);
    } else { r->flags |= X4P_CF_OPEN_FAILED; g_census_errs++; }
    CloseHandle(th);
}

/* After the hash: threads that appeared since the census (created after t1, still alive) get a row. */
static uint64_t g_late_new;
static void visit_late(DWORD tid, void *ctx) {
    (void)ctx;
    for (int i = 0; i < g_rows_n; i++) if (g_rows[i].tid == tid) return;
    if (t1_find(tid)) return;
    if (g_rows_n >= X4H_MAX_THREADS + 64) { g_census_errs++; return; }
    census_row *r = &g_rows[g_rows_n++];
    memset(r, 0, sizeof *r);
    r->tid = tid;
    r->flags = X4P_CF_POST_T1_NEW;
    g_late_new++;
}

/* measured TSC rate, cycles per second, against QPC (for the post-t1 CPU allowance in cycles). */
static ULONG64 measure_tsc_hz(void) {
    uint64_t q0 = x4h_now_ns();
    unsigned long long c0 = __rdtsc();
    uint64_t target = q0 + 20000000ull;   /* 20 ms */
    uint64_t q1;
    while ((q1 = x4h_now_ns()) < target) { YieldProcessor(); }
    unsigned long long c1 = __rdtsc();
    double secs = (double)(q1 - q0) / 1e9;
    if (secs <= 0) return 0;
    return (ULONG64)((double)(c1 - c0) / secs);
}

/* SHA-256 of a buffer into four little-endian u64 (bytes in order); chunked so no length truncates. */
static int sha256_4(const uint8_t *data, size_t n, uint64_t out[4]) {
    BCRYPT_ALG_HANDLE alg = NULL;
    BCRYPT_HASH_HANDLE h = NULL;
    uint8_t digest[32];
    int ok = 0;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) != 0) return 0;
    if (BCryptCreateHash(alg, &h, NULL, 0, NULL, 0, 0) == 0) {
        ok = 1;
        for (size_t off = 0; off < n && ok;) {
            ULONG chunk = (ULONG)((n - off) > 0x40000000u ? 0x40000000u : (n - off));
            if (BCryptHashData(h, (PUCHAR)(data + off), chunk, 0) != 0) ok = 0;
            off += chunk;
        }
        if (ok && BCryptFinishHash(h, digest, sizeof digest, 0) == 0) memcpy(out, digest, 32);
        else ok = 0;
    }
    if (h) BCryptDestroyHash(h);
    BCryptCloseAlgorithmProvider(alg, 0);
    return ok;
}

/* ------------------------------------------------------------- selfcheck */
static uint64_t selfcheck_flags(void) {
    uint64_t f = 0;
    HANDLE tok = NULL;
    if (OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &tok)) {
        DWORD v = 0, len = 0;
        if (GetTokenInformation(tok, TokenIsAppContainer, &v, sizeof v, &len) && v) f |= 1u;       /* bit0 */
        TOKEN_ELEVATION e; ZeroMemory(&e, sizeof e);
        if (GetTokenInformation(tok, TokenElevation, &e, sizeof e, &len) && e.TokenIsElevated) f |= 4u; /* bit2 */
        CloseHandle(tok);
    }
    /* bit1 LPAC is left to the orchestrator's probe set; not duplicated here. */
    BOOL inj = FALSE;
    if (IsProcessInJob(GetCurrentProcess(), NULL, &inj) && inj) f |= 8u;                            /* bit3 */
    if (mxcsr_ctrl() == X4P_MXCSR_DEFAULT) f |= 32u;                                                /* bit5 */
    /* bit4 (child-process creation blocked): the job's active-process limit and the absence of
       CREATE_BREAKAWAY are asserted by the orchestrator; probing it here would be a side effect. */
    return f;
}

/* ---------------------------------------------------------------- one run */
typedef struct {
    uint8_t *base;             /* the mapped section view                         */
    uint8_t *out;              /* output extent = base + X4P_OUT_OFFSET(out_bytes) */
    size_t   out_bytes, out_offset;
    uint64_t param;
    ULONG64  spin_budget_cycles, idle_budget_cycles;   /* 0 = derive a provisional default */
    const x4h_workload *wl;
    DWORD_PTR expected_affinity;
} run_cfg;

static uint64_t g_census_payload[(X4H_MAX_THREADS + 64) * X4P_CENSUS_W];

static int run_workload(run_cfg *cfg) {
    uint64_t rep[X4P_R_COUNT];
    memset(rep, 0, sizeof rep);
    rep[X4P_R_VERSION] = X4P_VERSION;
    rep[X4P_R_SALT] = g_salt;
    rep[X4P_R_OUT_OFFSET] = cfg->out_offset;
    rep[X4P_R_EXPECTED_AFFINITY] = (uint64_t)cfg->expected_affinity;
    g_harness_tid = GetCurrentThreadId();

    /* step 3: default MXCSR on this thread */
    _mm_setcsr(X4P_MXCSR_DEFAULT);

    /* step 0 / 6: the allowed thread set is fixed BEFORE the workload's init runs. */
    g_pre_n = 0;
    if (for_each_thread(visit_pre, NULL) < 0) { send_fail(X4P_F_INTERNAL, 1, 0, 0); return 1; }

    /* workload init (untimed). It never sees the output extent (out = NULL), and the extent is
     * (re)poisoned after init returns, so nothing init writes there can survive into the run. */
    x4h_ctx ctx; memset(&ctx, 0, sizeof ctx);
    ctx.out = NULL; ctx.out_bytes = cfg->out_bytes; ctx.param = cfg->param;
    if (cfg->wl->init && cfg->wl->init(&ctx) != 0) { send_fail(X4P_F_WORKLOAD, 0, 0, 0); return 1; }
    _mm_setcsr(X4P_MXCSR_DEFAULT);

    /* step 2: poison the head and the output extent (salt across both 64-byte end lines). The guard
     * page after the extent was set at map time. */
    memset(cfg->base, X4P_POISON_BYTE, cfg->out_offset);
    poison_fill(cfg->out, cfg->out_bytes, g_salt);

    ULONG64 tsc_hz = measure_tsc_hz();
    rep[X4P_R_TSC_HZ] = tsc_hz;
    ULONG64 spin_budget = cfg->spin_budget_cycles ? cfg->spin_budget_cycles : (tsc_hz / 20000 + tsc_hz / 1000);
    ULONG64 idle_budget = cfg->idle_budget_cycles ? cfg->idle_budget_cycles : (tsc_hz / 1000);

    /* step 4: START, then t0. The output extent is handed to the workload only now. */
    ctx.out = cfg->out;
    send_msg(X4P_START, NULL, 0);
    uint64_t t0 = x4h_now_ns();
    x4h_t0_ns = t0;

    /* step 5: run */
    int rc = cfg->wl->run(&ctx);
    g_harness_mxcsr_after_run = _mm_getcsr();
    int harness_prio_after_run = GetThreadPriority(GetCurrentThread());
    rep[X4P_R_WORKLOAD_RC] = (uint64_t)(uint32_t)rc;

    /* step 6: join outstanding I/O before stopping the clock */
    uint64_t join_deadline = x4h_now_ns() + 10000000000ull;   /* 10 s */
    while (g_io_outstanding > 0 && x4h_now_ns() < join_deadline) YieldProcessor();
    if (g_io_outstanding > 0) { send_fail(X4P_F_JOIN_TIMEOUT, (uint64_t)g_io_outstanding, 0, 0); return 1; }
    rep[X4P_R_IO_OUTSTANDING] = (uint64_t)g_io_outstanding;

    uint64_t t1 = x4h_now_ns();
    send_msg(X4P_STOP, NULL, 0);
    /* The reported t0 is the exported x4h_t0_ns, which lives in the workload's address space and can in
     * principle be written by it (MEASUREMENT-SERVICE.md section 2). That is deliberate: the precise
     * clock is in-process, and the TRUSTED guard is the orchestrator's out-of-process wall bracket
     * (step 8a). A workload that shaves or pads t0 trips |delta_h - delta_o| > tau_clock (a5). */
    rep[X4P_R_T0_NS] = x4h_t0_ns;
    rep[X4P_R_T1_NS] = t1;

    /* t1 snapshot of every thread's cycle count. It follows STOP so the orchestrator's bracket closes
     * at t1 (step 6); the lag is reported, and CPU in it is charged by the orchestrator's process
     * cycle accounting at STOP (out of process). */
    g_t1_n = 0; g_t1_errs = 0;
    if (for_each_thread(visit_t1, NULL) < 0) g_t1_errs++;
    rep[X4P_R_T1_SNAP_LAG_NS] = x4h_now_ns() - t1;

    /* freeze the output view read-only: a late write by another thread faults (step 6). */
    DWORD old;
    int freeze_ok = VirtualProtect(cfg->out, cfg->out_bytes, PAGE_READONLY, &old) != 0;
    rep[X4P_R_FREEZE_OK] = (uint64_t)freeze_ok;

    /* census */
    g_rows_n = 0; g_census_errs = g_t1_errs + (freeze_ok ? 0 : 1);
    int n_census = for_each_thread(visit_census, NULL);
    if (n_census < 0) { g_census_errs++; n_census = 0; }

    /* step 7: hash the (now read-only) output extent */
    uint64_t hash[4] = {0,0,0,0};
    if (!sha256_4(cfg->out, cfg->out_bytes, hash)) g_census_errs++;

    /* post-t1 CPU rule: re-read every t1 thread's cycles after the hash; then look for late threads */
    for (int i = 0; i < g_t1_n; i++) if (g_t1[i].h) g_t1[i].cyc_hash = read_cycles(g_t1[i].h);
    g_late_new = 0;
    if (for_each_thread(visit_late, NULL) < 0) g_census_errs++;

    uint64_t new_unreg = 0, reg_created = 0, reg_unparked = 0, post_viol = 0, post_new = g_late_new;
    uint64_t mxcsr_bad = 0, aff_bad = 0, prio_bad = 0;
    ULONG64 post_max = 0;

    for (int i = 0; i < g_rows_n; i++) {
        census_row *r = &g_rows[i];
        int harness = (r->flags & X4P_CF_HARNESS) != 0;
        int slot = reg_slot_of(r->tid);
        int reg = slot >= 0, pre = was_pre_init(r->tid);
        int parked = reg && g_parked[slot];
        if (reg) { r->flags |= X4P_CF_REGISTERED; reg_created++; }
        if (parked) r->flags |= X4P_CF_PARKED;
        if (pre) r->flags |= X4P_CF_PRE_T0;
        if (!harness && !pre && !reg) { r->flags |= X4P_CF_NEW_UNREG; new_unreg++; }
        t1_entry *e = t1_find(r->tid);
        if (e) { e->in_census = 1; r->cyc_t1 = e->cyc_t1; r->cyc_hash = e->cyc_hash; }
        else if (!(r->flags & X4P_CF_POST_T1_NEW)) { r->flags |= X4P_CF_POST_T1_NEW; post_new++; }
        if (r->flags & X4P_CF_POST_T1_NEW) continue;   /* nothing else was read for a late thread */
        int readable = !(r->flags & X4P_CF_OPEN_FAILED);
        if (readable && (r->mxcsr & X4P_MXCSR_CTRL_MASK) != X4P_MXCSR_DEFAULT) { r->flags |= X4P_CF_MXCSR_BAD; mxcsr_bad++; }
        if (readable && cfg->expected_affinity && r->affinity != cfg->expected_affinity) {
            r->flags |= X4P_CF_AFFINITY_BAD; aff_bad++;
        }
        if (readable && r->priority != THREAD_PRIORITY_NORMAL) { r->flags |= X4P_CF_PRIORITY_BAD; prio_bad++; }
        if (!harness && reg && !parked) reg_unparked++;   /* a registered thread still alive = unjoined (a3) */
    }
    /* t1 threads that exited before the census still answer to the CPU rule, and a registered thread
     * that was alive and unparked at t1 was not joined before the clock stopped (a3), whether or not it
     * is still alive at the census (review round 3: the census-only count missed a worker that exited
     * between t1 and the census) */
    for (int i = 0; i < g_t1_n; i++) {
        t1_entry *e = &g_t1[i];
        if (e->in_census || g_rows_n >= X4H_MAX_THREADS + 64) continue;
        census_row *r = &g_rows[g_rows_n++];
        memset(r, 0, sizeof *r);
        r->tid = e->tid; r->cyc_t1 = e->cyc_t1; r->cyc_hash = e->cyc_hash;
        int slot = reg_slot_of(e->tid);
        r->flags = X4P_CF_EXITED | (slot >= 0 ? X4P_CF_REGISTERED : 0) | (slot >= 0 && g_parked[slot] ? X4P_CF_PARKED : 0);
        if (slot >= 0 && !g_parked[slot] && e->tid != g_harness_tid) reg_unparked++;
    }
    for (int i = 0; i < g_rows_n; i++) {
        census_row *r = &g_rows[i];
        if ((r->flags & X4P_CF_HARNESS) || (r->flags & X4P_CF_POST_T1_NEW) || r->tid == g_harness_tid) continue;
        ULONG64 post = r->cyc_hash >= r->cyc_t1 ? r->cyc_hash - r->cyc_t1 : 0;
        int slot = reg_slot_of(r->tid);
        ULONG64 budget = (slot >= 0 && g_parked[slot]) ? spin_budget : idle_budget;   /* pre-t0 threads: idle */
        if (post > post_max) post_max = post;
        if (post > budget) { r->flags |= X4P_CF_POST_T1_OVER; post_viol++; }
    }
    for (int i = 0; i < g_t1_n; i++) if (g_t1[i].h) CloseHandle(g_t1[i].h);

    int cn = 0;
    for (int i = 0; i < g_rows_n; i++) {
        census_row *r = &g_rows[i];
        g_census_payload[cn + X4P_C_TID] = r->tid;
        g_census_payload[cn + X4P_C_FLAGS] = r->flags;
        g_census_payload[cn + X4P_C_CYC_T1] = r->cyc_t1;
        g_census_payload[cn + X4P_C_CYC_HASH] = r->cyc_hash;
        g_census_payload[cn + X4P_C_MXCSR] = r->mxcsr;
        g_census_payload[cn + X4P_C_PRIORITY] = (uint64_t)(int64_t)r->priority;
        g_census_payload[cn + X4P_C_AFFINITY] = r->affinity;
        g_census_payload[cn + X4P_C_CREATE_FT] = r->create_ft;
        cn += (int)X4P_CENSUS_W;
    }
    send_msg(X4P_CENSUS, g_census_payload, (uint32_t)cn);

    rep[X4P_R_HASH0] = hash[0]; rep[X4P_R_HASH1] = hash[1];
    rep[X4P_R_HASH2] = hash[2]; rep[X4P_R_HASH3] = hash[3];
    rep[X4P_R_OUT_BYTES] = cfg->out_bytes;
    rep[X4P_R_POISON_RESIDUAL_WORDS] = count_residual(cfg->out, cfg->out_bytes, g_salt);
    rep[X4P_R_SLACK_MODIFIED_BYTES] = count_changed(cfg->base, cfg->out_offset);
    rep[X4P_R_THREADS_AT_CENSUS] = (uint64_t)n_census;
    rep[X4P_R_NEW_UNREGISTERED] = new_unreg;
    rep[X4P_R_REGISTERED_CREATED] = reg_created;
    rep[X4P_R_REGISTERED_UNPARKED] = reg_unparked;
    rep[X4P_R_POST_T1_VIOLATIONS] = post_viol;
    rep[X4P_R_POST_T1_MAX_CYCLES] = post_max;
    rep[X4P_R_POST_T1_NEW_THREADS] = post_new;
    rep[X4P_R_MXCSR_BAD_THREADS] = mxcsr_bad;
    rep[X4P_R_MXCSR_ENTRY_BAD] = (uint64_t)g_reg_entry_mxcsr_bad;
    rep[X4P_R_MXCSR_EXIT_BAD] = (uint64_t)g_reg_exit_mxcsr_bad;
    rep[X4P_R_PRIORITY_EXIT_BAD] = (uint64_t)g_reg_exit_prio_bad;
    rep[X4P_R_AFFINITY_BAD] = aff_bad;
    rep[X4P_R_PRIORITY_BAD] = prio_bad;
    rep[X4P_R_PRIORITY_HARNESS] = (uint64_t)(int64_t)harness_prio_after_run;
    rep[X4P_R_PRIORITY_CLASS] = GetPriorityClass(GetCurrentProcess());
    DWORD_PTR pm = 0, sm = 0;
    GetProcessAffinityMask(GetCurrentProcess(), &pm, &sm);
    rep[X4P_R_PROCESS_AFFINITY] = (uint64_t)pm;
    rep[X4P_R_CENSUS_ERRORS] = g_census_errs;
    rep[X4P_R_HARNESS_TID] = g_harness_tid;
    rep[X4P_R_MXCSR_HARNESS] = g_harness_mxcsr_after_run;
    rep[X4P_R_SELFCHECK_FLAGS] = selfcheck_flags();

    send_msg(X4P_REPORT, rep, X4P_R_COUNT);
    /* No workload code runs after REPORT: fini is not called in a measured run, and the process ends
     * here with exit code 0 (every run is a fresh process). */
    TerminateProcess(GetCurrentProcess(), 0);
    return 0;
}

/* ----------------------------------------------------------------- setup */
/* The output section: the orchestrator creates a file-mapping, maps it RW into the child by passing an
 * inherited, access-reduced HANDLE as --section, and maps the same section read-only in its own process
 * for the step-8a copy and rehash. Without --section (dev / x4_devcheck) the harness maps an anonymous
 * section of the same layout itself. The guard page after the extent is made PAGE_NOACCESS here. */
static int map_output(uint64_t section_handle, size_t out_bytes, run_cfg *cfg) {
    size_t total = (size_t)X4P_SECTION_BYTES(out_bytes);
    size_t off = (size_t)X4P_OUT_OFFSET(out_bytes);
    HANDLE sec;
    if (section_handle) {
        sec = (HANDLE)(uintptr_t)section_handle;
    } else {
        sec = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
                                 (DWORD)((uint64_t)total >> 32), (DWORD)(total & 0xffffffffu), NULL);
        if (!sec) return 0;
    }
    uint8_t *p = (uint8_t *)MapViewOfFile(sec, FILE_MAP_WRITE, 0, 0, total);
    if (!p) return 0;
    DWORD old;
    if (!VirtualProtect(p + off + out_bytes, X4P_PAGE, PAGE_NOACCESS, &old)) return 0;
    cfg->base = p;
    cfg->out = p + off;
    cfg->out_offset = off;
    return 1;
}

static int parse_u64(const wchar_t *s, uint64_t *out) {
    wchar_t *end = NULL;
    *out = wcstoull(s, &end, 0);
    return end && *end == 0;
}

/* --------------------------------------------------------------- selftest */
static int run_selftest(int argc, wchar_t **argv) {
    x4sb_probe_cfg c; ZeroMemory(&c, sizeof c);
    c.inside = 1;
    for (int i = 1; i < argc; i++) {
        if (wcscmp(argv[i], L"--selftest") == 0) continue;
        int j = i;
        if (x4sb_probe_arg(&c, argc, argv, &j)) { i = j; continue; }
    }
    x4sb_probe_result r[X4SB_MAX_RESULTS];
    int n = x4sb_run_probes(&c, r, X4SB_MAX_RESULTS);
    uint64_t payload[X4SB_MAX_RESULTS * X4P_PROBE_W];
    for (int i = 0; i < n; i++) {
        payload[i * X4P_PROBE_W + X4P_P_ID] = r[i].id;
        payload[i * X4P_PROBE_W + X4P_P_ATTEMPTED] = r[i].attempted;
        payload[i * X4P_PROBE_W + X4P_P_SUCCEEDED] = r[i].succeeded;
        payload[i * X4P_PROBE_W + X4P_P_ERROR] = r[i].error;
        payload[i * X4P_PROBE_W + X4P_P_ELAPSED_US] = r[i].elapsed_us;
        payload[i * X4P_PROBE_W + X4P_P_EXTRA] = r[i].extra;
    }
    send_msg(X4P_PROBES, payload, (uint32_t)(n * X4P_PROBE_W));
    return 0;
}

/* ------------------------------------------------------------------ wmain */
static run_cfg g_cfg;

static int run_guarded(run_cfg *cfg) {
    int rc = 1;
    __try {
        rc = run_workload(cfg);
    } __except (GetExceptionCode() == EXCEPTION_ACCESS_VIOLATION
                    ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH) {
        /* a write into the frozen output view or the guard page on this thread: an integrity fault */
        send_fail(X4P_F_FAULT, GetExceptionCode(), 0, 0);
        rc = 1;
    }
    return rc;
}

int wmain(int argc, wchar_t **argv) {
    LARGE_INTEGER q;
    QueryPerformanceFrequency(&q);
    g_qpf = (uint64_t)q.QuadPart ? (uint64_t)q.QuadPart : 1;
    InitializeCriticalSection(&g_pipe_cs);

    uint64_t pipe_handle = 0, section_handle = 0, out_bytes = 4096, param = 0, salt = 0;
    uint64_t spin_cycles = 0, idle_cycles = 0, job_affinity = 0;
    const wchar_t *wl_name = NULL;
    int selftest = 0, bad_arg = 0;

    for (int i = 1; i < argc; i++) {
        const wchar_t *k = argv[i];
        if (wcscmp(k, L"--selftest") == 0) { selftest = 1; continue; }
        if (i + 1 >= argc) break;
        const wchar_t *v = argv[i + 1];
        int ok = 1;
        if      (wcscmp(k, L"--pipe") == 0)      ok = parse_u64(v, &pipe_handle);
        else if (wcscmp(k, L"--section") == 0)   ok = parse_u64(v, &section_handle);
        else if (wcscmp(k, L"--out-bytes") == 0) ok = parse_u64(v, &out_bytes);
        else if (wcscmp(k, L"--param") == 0)     ok = parse_u64(v, &param);
        else if (wcscmp(k, L"--salt") == 0)      ok = parse_u64(v, &salt);
        else if (wcscmp(k, L"--spin-cycles") == 0) ok = parse_u64(v, &spin_cycles);
        else if (wcscmp(k, L"--idle-cycles") == 0) ok = parse_u64(v, &idle_cycles);
        else if (wcscmp(k, L"--affinity") == 0)  ok = parse_u64(v, &job_affinity);
        else if (wcscmp(k, L"--workload") == 0)  wl_name = v;
        else continue;
        if (!ok) bad_arg = 1;
        i++;
    }

    g_pipe = pipe_handle ? (HANDLE)(uintptr_t)pipe_handle : GetStdHandle(STD_OUTPUT_HANDLE);

    uint64_t hello[X4P_HELLO_N];
    SYSTEM_INFO si; GetSystemInfo(&si);
    hello[X4P_H_VERSION] = X4P_VERSION;
    hello[X4P_H_PID] = GetCurrentProcessId();
    hello[X4P_H_PAGE] = si.dwPageSize;
    hello[X4P_H_SECTION_BYTES] = X4P_SECTION_BYTES(out_bytes);
    hello[X4P_H_OUT_OFFSET] = X4P_OUT_OFFSET(out_bytes);
    hello[X4P_H_OUT_BYTES] = out_bytes;
    send_msg(X4P_HELLO, hello, X4P_HELLO_N);

    if (selftest) return run_selftest(argc, argv);

    if (bad_arg || out_bytes == 0 || out_bytes % X4P_OUT_ALIGN != 0 || si.dwPageSize != X4P_PAGE) {
        send_fail(X4P_F_ARGS, out_bytes, si.dwPageSize, 0);
        return 2;
    }
    const x4h_workload *wl = NULL;
    for (int i = 0; x4h_workloads[i]; i++) {
        char nm[64]; int j = 0;
        if (wl_name) { while (wl_name[j] && j < 63) { nm[j] = (char)wl_name[j]; j++; } nm[j] = 0; }
        if (wl_name && strcmp(x4h_workloads[i]->name, nm) == 0) { wl = x4h_workloads[i]; break; }
        if (!wl_name && i == 0) wl = x4h_workloads[i];
    }
    if (!wl) { send_fail(X4P_F_ARGS, 1, 0, 0); return 2; }

    /* the salt is the orchestrator's (so it can count residual poison itself); standalone, draw one */
    g_salt = salt;
    if (!g_salt) BCryptGenRandom(NULL, (PUCHAR)&g_salt, 8, BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (!g_salt) g_salt = ((uint64_t)GetTickCount64() << 1) | 1;

    ZeroMemory(&g_cfg, sizeof g_cfg);
    if (!map_output(section_handle, (size_t)out_bytes, &g_cfg)) { send_fail(X4P_F_MAP, GetLastError(), 0, 0); return 3; }
    if (!job_affinity) {   /* standalone: compare against the process mask this process started with */
        DWORD_PTR pm = 0, sm = 0;
        GetProcessAffinityMask(GetCurrentProcess(), &pm, &sm);
        job_affinity = (uint64_t)pm;
    }
    g_cfg.out_bytes = (size_t)out_bytes;
    g_cfg.param = param;
    g_cfg.spin_budget_cycles = spin_cycles;
    g_cfg.idle_budget_cycles = idle_cycles;
    g_cfg.expected_affinity = (DWORD_PTR)job_affinity;
    g_cfg.wl = wl;

    return run_guarded(&g_cfg);
}
