/* x4h.h -- the C harness's interface to in-process workloads (X4 measurement service v0, F0).
 *
 * A workload is linked into the harness process. It is NOT trusted unless it is hearth-c-ref at its
 * pinned tag (SANDBOX.md section 1): it shares this address space, so everything the harness
 * computes here is the precise record, and the orchestrator's out-of-process bracket is the trusted one
 * (MEASUREMENT-SERVICE.md section 2).
 *
 * Threads: a workload may create threads only through x4h_thread_create (same shape as Hearth's
 * hx_thread_create, hx_platform.h:75, so Hearth can be wired to it at link time). Any other thread
 * created after the pre-init snapshot (i.e. in init or later) and alive at the census rejects the run.
 * A registered thread that stays alive past the end of the timed region must declare itself parked
 * (x4h_thread_parked(1)) before it blocks; parked registered threads get the pool spin allowance after
 * t1, every other thread (pre-init threads included) the idle allowance. A registered thread whose
 * MXCSR or priority is non-default when its function returns is counted even if it was joined.
 *
 * I/O: a workload that issues overlapped I/O brackets each request with x4h_io_begin / x4h_io_end;
 * the harness waits for the count to reach zero before it stops the clock.
 */
#ifndef X4H_H
#define X4H_H

#include <stddef.h>
#include <stdint.h>

typedef struct x4h_thread x4h_thread;
typedef void *(*x4h_thread_fn)(void *arg);

int  x4h_thread_create(x4h_thread **out, x4h_thread_fn fn, void *arg); /* 0 on success */
void x4h_thread_join(x4h_thread *t);                                   /* also frees t */
void x4h_thread_parked(int parked);   /* called by a registered thread about itself    */
void x4h_io_begin(void);
void x4h_io_end(void);
uint64_t x4h_now_ns(void);            /* Hearth's hx_now_ns formula (QPC), monotonic   */

/* Wait, inside the timed region, until every registered thread has either returned from its
 * function or declared itself parked: the pool "drained to the quiescent state" of
 * MEASUREMENT-SERVICE.md section 3 step 6. A workload whose registered threads outlive run()
 * (Hearth's pool workers and store readers, parked in hx_cond_wait through the shim) calls it last
 * in run(), so the time they need to go idle is charged to the clock. Returns 0, or -1 when the
 * deadline passed (the workload then returns a non-zero status, an integrity failure).
 * (X4 pilot track, 2026-10-23.) */
int x4h_quiesce(uint64_t timeout_ns);

/* Pending condition-variable wakes (revision 4, review 2026-10-23): a thread that was signalled in a
 * condition wait still reads as parked until it runs, so a wrapper that tracks wakes (the Hearth shim,
 * hearth_x4_shim.c) adds +1 per wake issued to a waiting thread and -1 when a waiter returns;
 * x4h_quiesce does not return while the count is above zero. Without a shim the count stays 0. */
void x4h_wake_pending(long delta);

typedef struct {
    uint8_t *out;          /* the output extent (a view of the orchestrator's section, poisoned);
                              NULL during init -- the extent is handed over only at START       */
    size_t   out_bytes;    /* fixed by the orchestrator; a non-zero multiple of 64              */
    uint64_t param;        /* workload parameter (iterations, milliseconds, ...)                */
    void    *state;        /* workload-private state from init                                  */
} x4h_ctx;

typedef struct {
    const char *name;
    int  (*init)(x4h_ctx *ctx);   /* untimed; allocate and fill inputs here; 0 = ok              */
    int  (*run)(x4h_ctx *ctx);    /* the timed region; returns a workload status code           */
    void (*fini)(x4h_ctx *ctx);   /* NOT called in a measured run (the harness terminates itself
                                     right after REPORT); kept for API shape; may be NULL         */
} x4h_workload;

/* Fresh input allocation: page-aligned, filled with the poison byte, followed by a no-access guard
 * page. Freed when the process exits (every run is a fresh process). NULL on failure. */
void *x4h_alloc(size_t bytes);

/* Provided by the linked workload set (dev_workloads.c for development; a Hearth set later). */
extern const x4h_workload *const x4h_workloads[];
extern const char *const x4h_workload_set_name;

/* The harness keeps t0 in this exported variable. It is in the workload's address space, like every
 * harness variable; the trusted check is the orchestrator's bracket (|dh - do| <= tau_clock). The
 * development probe dev_t0_poke writes it to show that the bracket catches the change. */
extern volatile uint64_t x4h_t0_ns;

#endif
