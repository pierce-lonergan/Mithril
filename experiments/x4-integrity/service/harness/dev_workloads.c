/* dev_workloads.c -- DEVELOPMENT probes for the X4 harness (non-gate). NOT the HACK-SUITE catalogue:
 * these are the X4 track's own dev_* workloads, used to exercise the harness's clock/join/census/MXCSR/
 * poison machinery and the orchestrator's out-of-process bracket on synthetic inputs
 * (MEASUREMENT-SERVICE.md section 3). The catalogue (a) hacks stay sealed; running them is gate data
 * and is NOT done here. Every probe here is cooperative test code written by the service's own authors.
 *
 * Clean probes (dev_busy, dev_sleep, dev_write, dev_io, dev_parked, dev_sleep_long) must produce a clean
 * report. Fault probes each must trip the check named in their comment. The v2 probes (marked [v2]) are
 * the regression probes asked for by the 2026-10-16 same-family, independent-context review. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <xmmintrin.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <wchar.h>
#include "x4h.h"
#include "x4proto.h"

static volatile uint64_t g_sink;

static void busy_cycles(uint64_t iters) {
    volatile uint64_t x = 1;
    for (uint64_t i = 0; i < iters; i++) x = x * 6364136223846793005ull + 1442695040888963407ull;
    g_sink += x;
}

static void busy_ms(uint64_t ms) {
    uint64_t end = x4h_now_ns() + ms * 1000000ull;
    while (x4h_now_ns() < end) busy_cycles(1000);
}

static void fill_output(x4h_ctx *ctx) {
    for (size_t i = 0; i < ctx->out_bytes; i++) ctx->out[i] = (uint8_t)(i * 31u + 7u);
}

/* ---- clean probes ---- */
static int dev_busy_run(x4h_ctx *c) { busy_cycles(c->param ? c->param : 2000000); fill_output(c); return 0; }
static int dev_sleep_run(x4h_ctx *c) { Sleep((DWORD)(c->param ? c->param : 20)); fill_output(c); return 0; }
/* long enough (>= 1 s) for the orchestrator's tau_clock cap (0.1% of delta_o) to admit the 1 ms floor */
static int dev_sleep_long_run(x4h_ctx *c) { Sleep((DWORD)(c->param ? c->param : 1100)); fill_output(c); return 0; }
static int dev_write_run(x4h_ctx *c) { fill_output(c); return 0; }

static int dev_io_run(x4h_ctx *c) {
    /* overlapped write to a temp file, bracketed so the harness waits for it before t1. Under the
     * orchestrator TEMP is the run's fresh scratch directory. */
    wchar_t path[MAX_PATH], dir[MAX_PATH];
    GetTempPathW(MAX_PATH, dir);
    swprintf(path, MAX_PATH, L"%sx4dev_io_%lu.tmp", dir, GetCurrentProcessId());
    HANDLE h = CreateFileW(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                           FILE_FLAG_OVERLAPPED | FILE_FLAG_DELETE_ON_CLOSE, NULL);
    if (h == INVALID_HANDLE_VALUE) { fill_output(c); return 1; }
    OVERLAPPED ov; ZeroMemory(&ov, sizeof ov);
    ov.hEvent = CreateEventW(NULL, TRUE, FALSE, NULL);
    static char buf[65536];
    memset(buf, 0xC3, sizeof buf);
    x4h_io_begin();
    DWORD wr = 0;
    BOOL ok = WriteFile(h, buf, sizeof buf, &wr, &ov);
    if (!ok && GetLastError() == ERROR_IO_PENDING) {
        GetOverlappedResult(h, &ov, &wr, TRUE);   /* reap the completion (join I/O) */
    }
    x4h_io_end();
    CloseHandle(ov.hEvent);
    CloseHandle(h);
    fill_output(c);
    return 0;
}

static void *parked_worker(void *arg) {
    x4h_ctx *c = (x4h_ctx *)arg;
    busy_cycles(c->param ? c->param : 1000000);
    fill_output(c);
    x4h_thread_parked(1);   /* declares itself parked before the clock stops */
    for (;;) Sleep(1000);   /* lives on, parked; the harness allows it the spin budget */
}
static int dev_parked_run(x4h_ctx *c) {
    x4h_thread *t;
    if (x4h_thread_create(&t, parked_worker, c) != 0) return 1;
    Sleep(30);              /* let the worker do its work and park; we do not join it */
    return 0;
}

/* ---- fault probes (each trips one check) ---- */

/* registered worker that keeps running and never parks -> REGISTERED_UNPARKED (a3: unjoined work) */
static void *leak_worker(void *arg) {
    (void)arg;
    for (uint64_t i = 0; i < 200000000ull; i++) busy_cycles(1);
    return NULL;
}
static int dev_leak_registered_run(x4h_ctx *c) {
    x4h_thread *t;
    x4h_thread_create(&t, leak_worker, c);
    Sleep(5);
    fill_output(c);
    return 0;   /* does not join t; t is still spinning at t1 */
}

/* raw CreateThread after t0, left running past t1 -> NEW_UNREGISTERED (a3b) */
static DWORD WINAPI raw_worker(LPVOID p) {
    (void)p;
    for (uint64_t i = 0; i < 300000000ull; i++) busy_cycles(1);
    return 0;
}
static int dev_raw_thread_run(x4h_ctx *c) {
    HANDLE h = CreateThread(NULL, 0, raw_worker, NULL, 0, NULL);
    if (h) CloseHandle(h);   /* handle closed, thread runs on; we never join it */
    Sleep(5);
    fill_output(c);
    return 0;
}

/* worker sets FTZ/DAZ (non-default MXCSR) and stays alive -> MXCSR_BAD_THREADS (a9) */
static volatile LONG g_mxcsr_ready;
static void *mxcsr_worker(void *arg) {
    (void)arg;
    _mm_setcsr(_mm_getcsr() | 0x8040u);   /* FTZ (bit15) + DAZ (bit6) */
    InterlockedExchange(&g_mxcsr_ready, 1);
    x4h_thread_parked(1);
    for (;;) Sleep(1000);                  /* stays alive so the census reads its context */
}
static int dev_mxcsr_worker_run(x4h_ctx *c) {
    x4h_thread *t;
    x4h_thread_create(&t, mxcsr_worker, NULL);
    while (!g_mxcsr_ready) Sleep(1);
    fill_output(c);
    return 0;
}

/* leaves part of the output as poison -> POISON_RESIDUAL_WORDS > 0 (a4) */
static int dev_partial_output_run(x4h_ctx *c) {
    size_t half = c->out_bytes / 2;
    for (size_t i = 0; i < half; i++) c->out[i] = (uint8_t)(i * 31u + 7u);
    return 0;
}

/* writes past the output extent -> the guard page faults on the harness thread -> FAIL(FAULT) */
static int dev_overflow_run(x4h_ctx *c) {
    fill_output(c);
    uint8_t *slack = c->out + c->out_bytes;
    for (int i = 0; i < 128; i++) slack[i] = (uint8_t)(i + 1);
    return 0;
}

/* [v2] writes just BEFORE the output extent -> head bytes changed (in-process SLACK_MODIFIED_BYTES and
 * the orchestrator's own check of the bytes outside the extent) */
static int dev_underflow_run(x4h_ctx *c) {
    fill_output(c);
    for (int i = 1; i <= 64; i++) c->out[-i] = (uint8_t)i;
    return 0;
}

/* overwrites the harness's exported t0 -> the orchestrator's wall bracket disagrees (a5 stand-in) */
static int dev_t0_poke_run(x4h_ctx *c) {
    Sleep((DWORD)(c->param ? c->param : 1100));
    x4h_t0_ns -= 500000000ull;   /* claim the run took 0.5 s longer than the orchestrator saw */
    fill_output(c);
    return 0;
}

/* a worker narrows its affinity to a core outside the job mask, if it can -> AFFINITY_BAD (a31) */
static void *affinity_worker(void *arg) {
    (void)arg;
    SetThreadAffinityMask(GetCurrentThread(), (DWORD_PTR)1 << 2);
    x4h_thread_parked(1);
    for (;;) Sleep(1000);
}
static int dev_affinity_run(x4h_ctx *c) {
    x4h_thread *t;
    x4h_thread_create(&t, affinity_worker, NULL);
    Sleep(5);
    fill_output(c);
    return 0;
}

/* [v2] a worker narrows itself to the lowest core of the process mask (INSIDE the job mask, but a
 * different core set than declared) -> AFFINITY_BAD (a31, MEASUREMENT section 7.6) */
static volatile LONG g_narrow_ready;
static void *narrow_worker(void *arg) {
    (void)arg;
    DWORD_PTR pm = 0, sm = 0;
    GetProcessAffinityMask(GetCurrentProcess(), &pm, &sm);
    SetThreadAffinityMask(GetCurrentThread(), pm & (~pm + 1));
    InterlockedExchange(&g_narrow_ready, 1);
    x4h_thread_parked(1);
    for (;;) Sleep(1000);
}
static int dev_aff_narrow_run(x4h_ctx *c) {
    x4h_thread *t;
    x4h_thread_create(&t, narrow_worker, NULL);
    while (!g_narrow_ready) Sleep(1);
    fill_output(c);
    return 0;
}

/* a worker raises its own priority and stays alive -> PRIORITY_BAD (a31) */
static void *priority_worker(void *arg) {
    (void)arg;
    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_HIGHEST);
    x4h_thread_parked(1);
    for (;;) Sleep(1000);
}
static int dev_priority_run(x4h_ctx *c) {
    x4h_thread *t;
    x4h_thread_create(&t, priority_worker, NULL);
    Sleep(5);
    fill_output(c);
    return 0;
}

/* [v2] a worker sets FTZ/DAZ, returns, and is joined before t1 -> MXCSR_EXIT_BAD (a9) */
static void *mxcsr_then_exit(void *arg) { (void)arg; _mm_setcsr(_mm_getcsr() | 0x8040u); return NULL; }
static int dev_mxcsr_joined_run(x4h_ctx *c) {
    x4h_thread *t;
    if (x4h_thread_create(&t, mxcsr_then_exit, NULL) != 0) return 1;
    x4h_thread_join(t);
    fill_output(c);
    return 0;
}

/* [v2] a worker raises its priority, returns, and is joined before t1 -> PRIORITY_EXIT_BAD (a31) */
static void *prio_then_exit(void *arg) { (void)arg; SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_HIGHEST); return NULL; }
static int dev_priority_joined_run(x4h_ctx *c) {
    x4h_thread *t;
    if (x4h_thread_create(&t, prio_then_exit, NULL) != 0) return 1;
    x4h_thread_join(t);
    fill_output(c);
    return 0;
}

/* [v2] FTZ/DAZ left set on the HARNESS thread, where a single-thread workload runs -> MXCSR_HARNESS (a9) */
static int dev_main_ftz_run(x4h_ctx *c) { _mm_setcsr(_mm_getcsr() | 0x8040u); fill_output(c); return 0; }

/* [v2] the harness thread's priority raised and left -> PRIORITY_HARNESS / PRIORITY_BAD (a31) */
static int dev_main_prio_run(x4h_ctx *c) { SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_HIGHEST); fill_output(c); return 0; }

/* [v2] a raw thread created in the UNTIMED init and left alive -> NEW_UNREGISTERED (the allowed set is
 * fixed before init) */
static DWORD WINAPI sleeper(LPVOID p) { (void)p; for (;;) Sleep(1000); }
static int dev_init_thread_init(x4h_ctx *c) {
    (void)c;
    HANDLE h = CreateThread(NULL, 0, sleeper, NULL, 0, NULL);
    if (!h) return 1;
    CloseHandle(h);
    return 0;
}

/* [v2] init finds the output section by scanning its address space and writes the final output there;
 * run() then writes nothing. The extent is re-poisoned after init -> poison residual + hash mismatch. */
static int dev_init_output_init(x4h_ctx *c) {
    uint64_t want = X4P_SECTION_BYTES(c->out_bytes);
    uint8_t *p = NULL;
    MEMORY_BASIC_INFORMATION mbi;
    for (uint8_t *a = NULL; VirtualQuery(a, &mbi, sizeof mbi) == sizeof mbi; a = (uint8_t *)mbi.BaseAddress + mbi.RegionSize) {
        if (mbi.State == MEM_COMMIT && mbi.Type == MEM_MAPPED && mbi.Protect == PAGE_READWRITE &&
            (uint64_t)mbi.RegionSize >= want - X4P_PAGE && mbi.BaseAddress == mbi.AllocationBase) {
            p = (uint8_t *)mbi.BaseAddress;
            break;
        }
        if ((uint8_t *)mbi.BaseAddress + mbi.RegionSize < (uint8_t *)mbi.BaseAddress) break;
    }
    if (!p) return 0;   /* not found: run() still writes nothing, so the run must fail either way */
    uint8_t *out = p + X4P_OUT_OFFSET(c->out_bytes);
    for (size_t i = 0; i < c->out_bytes; i++) out[i] = (uint8_t)(i * 31u + 7u);
    return 0;
}
static int dev_nothing_run(x4h_ctx *c) { (void)c; return 0; }

/* [v2] a registered parked worker that burns CPU from the moment run() returns (across t1, the census
 * and the hash) -> POST_T1_VIOLATIONS when the budgets are tighter than the census window (the dev
 * check passes --spin-cycles/--idle-cycles; the orchestrator's process-cycle accounting is the
 * out-of-process counterpart) */
static volatile LONG g_after_go;
static void *after_t1_worker(void *arg) {
    (void)arg;
    x4h_thread_parked(1);
    while (!g_after_go) YieldProcessor();
    busy_ms(30);
    for (;;) Sleep(1000);
}
static int dev_after_t1_run(x4h_ctx *c) {
    x4h_thread *t;
    if (x4h_thread_create(&t, after_t1_worker, NULL) != 0) return 1;
    Sleep(5);
    fill_output(c);
    InterlockedExchange(&g_after_go, 1);
    return 0;
}

/* [v2] forged early STOP (the reviewer's rev_early_stop): 200 ms of work, a STOP frame written straight
 * to stdout (the pipe), 200 ms more work, then t0 shifted so delta_h matches the forged bracket.
 * -> protocol violation (duplicate STOP) and CPU charged after the first STOP (out of process). */
static int dev_early_stop_run(x4h_ctx *c) {
    busy_ms(200);
    uint32_t hdr[4] = { X4P_MAGIC, X4P_STOP, 0, 999 };
    DWORD w = 0;
    uint64_t t_forged = x4h_now_ns();
    WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), hdr, sizeof hdr, &w, NULL);
    busy_ms(200);
    fill_output(c);
    x4h_t0_ns += x4h_now_ns() - t_forged;
    return 0;
}

/* [v2] a complete, correct output but a non-zero workload status -> WORKLOAD_RC */
static int dev_rc_run(x4h_ctx *c) { fill_output(c); return 7; }

/* ---- [r3] review round 3 (2026-10-16/17): gaps the in-process record cannot see by construction. Each
 * reads CLEAN to the harness; the orchestrator's out-of-process check named in its comment catches it. */

/* [r3] precompute laundered into the untimed init: init burns param ms (default 1500), run() only waits
 * 1.1 s and writes the output -> OOP pre_start_wall + pre_start_cycles (R1-1) */
static int dev_init_precompute_init(x4h_ctx *c) { busy_ms(c->param ? c->param : 1500); return 0; }
static int dev_sleep_fill_run(x4h_ctx *c) { Sleep(1100); fill_output(c); return 0; }

/* [r3] parallel work by raw threads that exit before t1: two threads each run a fixed amount of work and
 * are joined inside run(), so none survives to the census -> OOP window_cores when the job allows >= 2
 * CPUs; pinned to one CPU it is Accepted at about twice the wall time, i.e. no gain (R1-2) */
static DWORD WINAPI par_worker(LPVOID p) { busy_cycles((uint64_t)(uintptr_t)p); return 0; }
static int dev_par_exited_run(x4h_ctx *c) {
    uint64_t iters = c->param ? c->param : 1500000000ull;
    HANDLE h[2];
    for (int i = 0; i < 2; i++) {
        h[i] = CreateThread(NULL, 0, par_worker, (LPVOID)(uintptr_t)iters, 0, NULL);
        if (!h[i]) return 1;
    }
    WaitForMultipleObjects(2, h, TRUE, INFINITE);
    CloseHandle(h[0]);
    CloseHandle(h[1]);
    fill_output(c);
    return 0;
}

/* [r3] lifts the child's own guard page and writes past the extent: no fault, and the harness cannot
 * read its no-access guard -> OOP outside_extent_oop on the trailing page (R1-5) */
static int dev_guard_lift_run(x4h_ctx *c) {
    Sleep((DWORD)(c->param ? c->param : 1100));
    fill_output(c);
    DWORD old;
    uint8_t *past = c->out + c->out_bytes;
    if (!VirtualProtect(past, X4P_PAGE, PAGE_READWRITE, &old)) return 5;   /* could not lift: say so */
    for (int i = 0; i < 128; i++) past[i] = (uint8_t)(i + 1);
    return 0;
}

/* [r3] handle canary (R1-3). With --param H (`x4svc run --dev-canary` holds an inheritable, signalled
 * event it does NOT list for the child and passes its value): status 9 if the child received it.
 * Without --param: counts the handles in this process that carry HANDLE_FLAG_INHERIT; exactly 2 are
 * expected (the pipe's write end and the section), so the status is 0 for 2 and 100 + count otherwise
 * (a launcher without a handle list leaks whatever the orchestrator holds inheritable). */
static int dev_handle_canary_run(x4h_ctx *c) {
    Sleep(1100);
    fill_output(c);
    DWORD fl = 0;
    if (c->param) {
        /* the value must name an INHERITED handle (the flag survives inheritance: the round-2 launcher's
         * child counted 29 flagged handles [M]); a same-valued handle the child created itself is not
         * the canary (an unflagged signalled object gave one false positive before this check [M]) */
        HANDLE h = (HANDLE)(uintptr_t)c->param;
        if (GetHandleInformation(h, &fl) && (fl & HANDLE_FLAG_INHERIT) && WaitForSingleObject(h, 0) == WAIT_OBJECT_0) return 9;
        return 0;
    }
    int n = 0;
    for (uintptr_t v = 4; v < 65536; v += 4)
        if (GetHandleInformation((HANDLE)v, &fl) && (fl & HANDLE_FLAG_INHERIT)) n++;
    return n == 2 ? 0 : 100 + n;
}

/* [r3] FORGED FRAME STREAM (R1-1, the reviewer's variant). From init the workload finds the section,
 * writes the output and a poisoned head, writes START, waits ~1.1 s, writes STOP, an empty CENSUS and a
 * clean REPORT (its own t0/t1, the orchestrator's salt read from the command line, the SHA-256 of the
 * output) straight to the pipe, and terminates the process before the harness sends anything after
 * HELLO. param = ms of busy work BEFORE the forged START (the precompute variant).
 * Expected: param 0 -> Accept: the in-process record is forgeable (documented), but every cycle is still
 * charged to a bounded out-of-process window and the output was complete before the orchestrator's
 * START stamp; param 1500 -> pre_start_wall + pre_start_cycles. */
static uint64_t cmdline_u64(const wchar_t *key) {
    const wchar_t *s = wcsstr(GetCommandLineW(), key);
    if (!s) return 0;
    s += wcslen(key);
    while (*s == L' ') s++;
    return wcstoull(s, NULL, 0);
}
/* The harness's view of the section: a mapped RW region of exactly head + extent bytes, immediately
 * followed by the one-page no-access guard of the same allocation (set before init runs). */
static uint8_t *find_section(size_t out_bytes) {
    uint64_t want = X4P_SECTION_BYTES(out_bytes);
    MEMORY_BASIC_INFORMATION mbi, next;
    for (uint8_t *a = NULL; VirtualQuery(a, &mbi, sizeof mbi) == sizeof mbi; a = (uint8_t *)mbi.BaseAddress + mbi.RegionSize) {
        if (mbi.State == MEM_COMMIT && mbi.Type == MEM_MAPPED && mbi.Protect == PAGE_READWRITE &&
            (uint64_t)mbi.RegionSize == want - X4P_PAGE && mbi.BaseAddress == mbi.AllocationBase) {
            uint8_t *g = (uint8_t *)mbi.BaseAddress + mbi.RegionSize;
            if (VirtualQuery(g, &next, sizeof next) == sizeof next && next.AllocationBase == mbi.AllocationBase &&
                next.Protect == PAGE_NOACCESS && next.RegionSize == X4P_PAGE)
                return (uint8_t *)mbi.BaseAddress;
        }
        if ((uint8_t *)mbi.BaseAddress + mbi.RegionSize < (uint8_t *)mbi.BaseAddress) break;
    }
    return NULL;
}
static void forge_frame(uint32_t type, uint32_t seq, const uint64_t *p, uint32_t n) {
    static uint8_t buf[16 + 64 * 8];
    uint32_t hdr[4] = { X4P_MAGIC, type, n * 8u, seq };
    memcpy(buf, hdr, 16);
    if (n) memcpy(buf + 16, p, n * 8u);
    DWORD w = 0;
    WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), buf, 16u + n * 8u, &w, NULL);
}
static int sha256_buf(const uint8_t *d, size_t n, uint8_t out[32]) {
    BCRYPT_ALG_HANDLE alg = NULL;
    BCRYPT_HASH_HANDLE h = NULL;
    int ok = 0;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) != 0) return 0;
    if (BCryptCreateHash(alg, &h, NULL, 0, NULL, 0, 0) == 0 && BCryptHashData(h, (PUCHAR)d, (ULONG)n, 0) == 0 &&
        BCryptFinishHash(h, out, 32, 0) == 0) ok = 1;
    if (h) BCryptDestroyHash(h);
    BCryptCloseAlgorithmProvider(alg, 0);
    return ok;
}
static int dev_forge_frames_init(x4h_ctx *c) {
    size_t n = c->out_bytes, off = (size_t)X4P_OUT_OFFSET(n);
    uint8_t *base = find_section(n);
    if (!base) return 1;
    memset(base, X4P_POISON_BYTE, off);                                   /* the head the orchestrator expects */
    for (size_t i = 0; i < n; i++) base[off + i] = (uint8_t)(i * 31u + 7u);   /* the output, before START */
    if (c->param) busy_ms(c->param);                                      /* precompute variant */
    forge_frame(X4P_START, 1, NULL, 0);
    uint64_t t0 = x4h_now_ns();
    Sleep(1100);
    uint64_t t1 = x4h_now_ns();
    forge_frame(X4P_STOP, 2, NULL, 0);
    forge_frame(X4P_CENSUS, 3, NULL, 0);
    uint64_t r[X4P_R_COUNT];
    memset(r, 0, sizeof r);
    uint8_t dg[32];
    if (!sha256_buf(base + off, n, dg)) return 1;
    DWORD_PTR pm = 0, sm = 0;
    GetProcessAffinityMask(GetCurrentProcess(), &pm, &sm);
    uint64_t aff = cmdline_u64(L"--affinity");
    r[X4P_R_VERSION] = X4P_VERSION;
    r[X4P_R_T0_NS] = t0;
    r[X4P_R_T1_NS] = t1;
    memcpy(&r[X4P_R_HASH0], dg, 32);
    r[X4P_R_OUT_BYTES] = n;
    r[X4P_R_SALT] = cmdline_u64(L"--salt");
    r[X4P_R_THREADS_AT_CENSUS] = 1;
    r[X4P_R_PRIORITY_CLASS] = GetPriorityClass(GetCurrentProcess());
    r[X4P_R_PROCESS_AFFINITY] = (uint64_t)pm;
    r[X4P_R_HARNESS_TID] = GetCurrentThreadId();
    r[X4P_R_MXCSR_HARNESS] = X4P_MXCSR_DEFAULT;
    r[X4P_R_EXPECTED_AFFINITY] = aff ? aff : (uint64_t)pm;
    r[X4P_R_OUT_OFFSET] = off;
    r[X4P_R_FREEZE_OK] = 1;
    forge_frame(X4P_REPORT, 4, r, X4P_R_COUNT);
    TerminateProcess(GetCurrentProcess(), 0);
    return 0;
}

#define WL(id, run_fn) static const x4h_workload id = { #id, NULL, run_fn, NULL }
#define WLI(id, init_fn, run_fn) static const x4h_workload id = { #id, init_fn, run_fn, NULL }
WL(dev_busy, dev_busy_run);
WL(dev_sleep, dev_sleep_run);
WL(dev_sleep_long, dev_sleep_long_run);
WL(dev_write, dev_write_run);
WL(dev_io, dev_io_run);
WL(dev_parked, dev_parked_run);
WL(dev_leak_registered, dev_leak_registered_run);
WL(dev_raw_thread, dev_raw_thread_run);
WL(dev_mxcsr_worker, dev_mxcsr_worker_run);
WL(dev_partial_output, dev_partial_output_run);
WL(dev_overflow, dev_overflow_run);
WL(dev_underflow, dev_underflow_run);
WL(dev_t0_poke, dev_t0_poke_run);
WL(dev_affinity, dev_affinity_run);
WL(dev_aff_narrow, dev_aff_narrow_run);
WL(dev_priority, dev_priority_run);
WL(dev_mxcsr_joined, dev_mxcsr_joined_run);
WL(dev_priority_joined, dev_priority_joined_run);
WL(dev_main_ftz, dev_main_ftz_run);
WL(dev_main_prio, dev_main_prio_run);
WLI(dev_init_thread, dev_init_thread_init, dev_write_run);
WLI(dev_init_output, dev_init_output_init, dev_nothing_run);
WL(dev_after_t1, dev_after_t1_run);
WL(dev_early_stop, dev_early_stop_run);
WL(dev_rc, dev_rc_run);
WLI(dev_init_precompute, dev_init_precompute_init, dev_sleep_fill_run);
WL(dev_par_exited, dev_par_exited_run);
WL(dev_guard_lift, dev_guard_lift_run);
WL(dev_handle_canary, dev_handle_canary_run);
WLI(dev_forge_frames, dev_forge_frames_init, dev_nothing_run);

const x4h_workload *const x4h_workloads[] = {
    &dev_busy, &dev_sleep, &dev_sleep_long, &dev_write, &dev_io, &dev_parked,
    &dev_leak_registered, &dev_raw_thread, &dev_mxcsr_worker,
    &dev_partial_output, &dev_overflow, &dev_underflow, &dev_t0_poke, &dev_affinity, &dev_aff_narrow,
    &dev_priority, &dev_mxcsr_joined, &dev_priority_joined, &dev_main_ftz, &dev_main_prio,
    &dev_init_thread, &dev_init_output, &dev_after_t1, &dev_early_stop, &dev_rc,
    &dev_init_precompute, &dev_par_exited, &dev_guard_lift, &dev_handle_canary, &dev_forge_frames,
    NULL
};
const char *const x4h_workload_set_name = "dev";
