/* hearth_x4_shim.c -- wires hearth-c-ref's thread and condition-variable calls to the X4 harness
 * (MEASUREMENT-SERVICE.md section 3 step 3a "wraps hx_thread_create", step 6 "pool drained to the
 * quiescent state"). X4 pilot track, 2026-10-23; revision 4 the same day (wake accounting).
 *
 * Hearth creates every thread through hx_thread_create (platform_win.c:206-216 is the only
 * CreateThread in engine/src at b5d3f14 [M, grep of the clone]) and every idle thread blocks in
 * hx_cond_wait / hx_cond_timedwait (pool.c:210, store.c:346). The harness build compiles Hearth's
 * own platform_win.c, unmodified, with six renames on the command line:
 *     /Dhx_thread_create=hx__os_thread_create  /Dhx_thread_join=hx__os_thread_join
 *     /Dhx_cond_wait=hx__os_cond_wait          /Dhx_cond_timedwait=hx__os_cond_timedwait
 *     /Dhx_cond_signal=hx__os_cond_signal      /Dhx_cond_broadcast=hx__os_cond_broadcast
 * so its definitions keep their bodies under the new names, and the eight other engine objects are
 * the unmodified objects of the clean CMake build. This file supplies the original names:
 *   - threads go through x4h_thread_create, so the census sees them as REGISTERED and each asserts
 *     the default MXCSR on entry and on return;
 *   - a registered thread that blocks in a condition wait declares itself parked for the wait, so
 *     x4h_quiesce() can tell when the pool and the store readers are idle, and the post-t1 CPU rule
 *     gives them the pool-spin allowance;
 *   - (revision 4, review 2026-10-23) every condition variable's waiters and pending wakes are
 *     counted: a signal to a variable with more waiters than pending wakes adds one pending wake, a
 *     broadcast makes every waiter pending, and a waiter that returns from a wake (not a timeout)
 *     consumes one, after it has cleared its parked flag. x4h_quiesce does not return while any wake
 *     is pending, so a reader signalled just before the end of run() (a prefetch hint, the store's
 *     tick broadcast) cannot still read as parked when t1 is stamped. Hearth signals and waits with
 *     the variable's mutex held (pool.c, store.c [M, clone]), so the counts are consistent with the
 *     waits the OS holds. Residual: a spurious wake-up consumes another waiter's pending wake.
 * Nothing here changes what Hearth computes; it changes only which thread wrapper runs.
 */
#include <windows.h>
#include "hx_platform.h"
#include "x4h.h"

/* the renamed bodies from platform_win.c */
int  hx__os_thread_create(hx_thread **out, hx_thread_fn fn, void *arg);
void hx__os_thread_join(hx_thread *t);
void hx__os_cond_wait(hx_cond *c, hx_mutex *m);
int  hx__os_cond_timedwait(hx_cond *c, hx_mutex *m, uint32_t timeout_us);
void hx__os_cond_signal(hx_cond *c);
void hx__os_cond_broadcast(hx_cond *c);

int hx_thread_create(hx_thread **out, hx_thread_fn fn, void *arg) {
    /* hx_thread is opaque to the engine; the handle it holds is the harness's thread record */
    return x4h_thread_create((x4h_thread **)out, (x4h_thread_fn)fn, arg);
}

void hx_thread_join(hx_thread *t) { x4h_thread_join((x4h_thread *)t); }

/* ------------------------------------------------------------ wake accounting (revision 4) */
#define CV_MAX 256
static struct { const void *cv; long waiters; long pending; } g_cv[CV_MAX];
static int g_cv_n;
static SRWLOCK g_cv_lock = SRWLOCK_INIT;

static int cv_slot(const void *c) {   /* under g_cv_lock; -1 = table full (untracked, as before) */
    for (int i = 0; i < g_cv_n; i++)
        if (g_cv[i].cv == c) return i;
    if (g_cv_n >= CV_MAX) return -1;
    g_cv[g_cv_n].cv = c;
    g_cv[g_cv_n].waiters = 0;
    g_cv[g_cv_n].pending = 0;
    return g_cv_n++;
}

static void cv_enter(const void *c) {
    AcquireSRWLockExclusive(&g_cv_lock);
    int i = cv_slot(c);
    if (i >= 0) g_cv[i].waiters++;
    ReleaseSRWLockExclusive(&g_cv_lock);
}

static void cv_leave(const void *c, int woken) {
    AcquireSRWLockExclusive(&g_cv_lock);
    int i = cv_slot(c);
    if (i >= 0) {
        long d = 0;
        g_cv[i].waiters--;
        if (woken && g_cv[i].pending > 0) { g_cv[i].pending--; d--; }
        if (g_cv[i].pending > g_cv[i].waiters) { d -= g_cv[i].pending - g_cv[i].waiters; g_cv[i].pending = g_cv[i].waiters; }
        if (d) x4h_wake_pending(d);
    }
    ReleaseSRWLockExclusive(&g_cv_lock);
}

void hx_cond_signal(hx_cond *c) {
    AcquireSRWLockExclusive(&g_cv_lock);
    int i = cv_slot(c);
    if (i >= 0 && g_cv[i].pending < g_cv[i].waiters) { g_cv[i].pending++; x4h_wake_pending(1); }
    ReleaseSRWLockExclusive(&g_cv_lock);
    hx__os_cond_signal(c);
}

void hx_cond_broadcast(hx_cond *c) {
    AcquireSRWLockExclusive(&g_cv_lock);
    int i = cv_slot(c);
    if (i >= 0 && g_cv[i].pending < g_cv[i].waiters) { x4h_wake_pending(g_cv[i].waiters - g_cv[i].pending); g_cv[i].pending = g_cv[i].waiters; }
    ReleaseSRWLockExclusive(&g_cv_lock);
    hx__os_cond_broadcast(c);
}

void hx_cond_wait(hx_cond *c, hx_mutex *m) {
    cv_enter(c);
    x4h_thread_parked(1);   /* no-op on a thread the harness did not create (the caller thread) */
    hx__os_cond_wait(c, m);
    x4h_thread_parked(0);   /* busy first, then the pending wake is consumed: never both clear early */
    cv_leave(c, 1);
}

int hx_cond_timedwait(hx_cond *c, hx_mutex *m, uint32_t timeout_us) {
    cv_enter(c);
    x4h_thread_parked(1);
    int r = hx__os_cond_timedwait(c, m, timeout_us);
    x4h_thread_parked(0);
    cv_leave(c, r == 0);    /* 1 = timed out: no wake consumed */
    return r;
}
