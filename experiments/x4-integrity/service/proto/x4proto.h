/* x4proto.h -- wire protocol between the C harness (child) and the Rust orchestrator (supervisor).
 *
 * X4 measurement service v0 (F0). Design: experiments/x4-integrity/MEASUREMENT-SERVICE.md section 3.
 * The Rust side mirrors these constants in orchestrator/src/proto.rs; unit tests there pin every value.
 *
 * Framing: every message is a 16-byte header of four little-endian u32
 *   { magic, type, payload_len_bytes, seq }
 * followed by payload_len_bytes of payload. Every payload is an array of little-endian u64
 * (f64 values travel as their IEEE-754 bit pattern), so payload_len_bytes is a multiple of 8.
 *
 * Order (enforced by the orchestrator, proto::validate_run_sequence): a measured run is exactly
 *   HELLO(seq 0), START(1), STOP(2), CENSUS(3), REPORT(4)
 * or a prefix of that sequence followed by exactly one FAIL whose seq is its position. A self-test is
 * exactly HELLO(0), PROBES(1). Any other sequence -- a duplicate, a reordering, a bad seq, an extra
 * frame or trailing bytes -- is an integrity failure. The orchestrator never parses workload text.
 *
 * Version 2 (2026-10-16 revision after the same-family, independent-context review of the v0 build):
 * new report fields at the end, the shared output layout below, orchestrator-chosen poison salt.
 */
#ifndef X4PROTO_H
#define X4PROTO_H

#include <stdint.h>

#define X4P_MAGIC   0x34503458u   /* bytes 'X','4','P','4' */
#define X4P_VERSION 2u

enum x4p_type {
    X4P_HELLO  = 1,  /* payload: X4P_HELLO_N u64 (below)                                     */
    X4P_START  = 2,  /* no payload; sent immediately before t0                                */
    X4P_STOP   = 3,  /* no payload; sent immediately after t1                                 */
    X4P_CENSUS = 4,  /* payload: n entries of X4P_CENSUS_W u64 (thread census after t1)       */
    X4P_REPORT = 5,  /* payload: X4P_R_COUNT u64 (typed run report)                           */
    X4P_FAIL   = 6,  /* payload: 4 u64 {code, a, b, c}                                        */
    X4P_PROBES = 7   /* payload: n entries of X4P_PROBE_W u64 (sandbox self-test results)     */
};

/* HELLO payload */
enum { X4P_H_VERSION, X4P_H_PID, X4P_H_PAGE, X4P_H_SECTION_BYTES, X4P_H_OUT_OFFSET, X4P_H_OUT_BYTES, X4P_HELLO_N };

/* Output section layout, shared by both sides (MEASUREMENT-SERVICE.md section 3 step 2):
 *   [0, off)                 head: poison byte; any change = a write before the extent
 *   [off, off + out_bytes)   the output extent: poison + salt in the first and last 64-byte line
 *   [off + out_bytes, +page) guard page, PAGE_NOACCESS in the child's view (an overflow faults); the
 *                            child can lift that, so the orchestrator also requires it to stay zero
 * off is at least one page and makes the extent END on a page boundary. out_bytes must be a
 * non-zero multiple of 64; both sides reject anything else. */
#define X4P_PAGE 4096u
#define X4P_OUT_ALIGN 64u
#define X4P_OUT_OFFSET(n)    ((uint64_t)X4P_PAGE + (((uint64_t)X4P_PAGE - ((uint64_t)(n) % X4P_PAGE)) % X4P_PAGE))
#define X4P_SECTION_BYTES(n) (X4P_OUT_OFFSET(n) + (uint64_t)(n) + (uint64_t)X4P_PAGE)

/* REPORT payload field indices. Times are ns from the harness clock (QPC, Hearth's hx_now_ns formula).
 * Every field is computed INSIDE the child, which shares its address space with the workload: these
 * are the precise record, not the trusted one (orchestrator/src/proto.rs labels each check's class). */
enum x4p_report_field {
    X4P_R_VERSION = 0,
    X4P_R_T0_NS,
    X4P_R_T1_NS,
    X4P_R_HASH0, X4P_R_HASH1, X4P_R_HASH2, X4P_R_HASH3,   /* SHA-256 of the output extent, bytes in order */
    X4P_R_OUT_BYTES,
    X4P_R_POISON_RESIDUAL_WORDS,   /* aligned 8-byte words still equal to the poison word or the salt     */
    X4P_R_SLACK_MODIFIED_BYTES,    /* bytes changed in the poisoned head before the output extent         */
    X4P_R_SALT,
    X4P_R_THREADS_AT_CENSUS,
    X4P_R_NEW_UNREGISTERED,        /* threads created after the pre-init snapshot not through the wrapper  */
    X4P_R_REGISTERED_CREATED,
    X4P_R_REGISTERED_UNPARKED,     /* registered threads alive at t1 that were neither joined nor parked   */
    X4P_R_POST_T1_VIOLATIONS,      /* threads over their CPU allowance in [t1 snapshot, hash]              */
    X4P_R_MXCSR_BAD_THREADS,       /* threads whose MXCSR control bits are not the default after t1        */
    X4P_R_MXCSR_ENTRY_BAD,         /* registered threads whose MXCSR was not default at entry              */
    X4P_R_AFFINITY_BAD,            /* threads (harness included) whose affinity != the declared mask       */
    X4P_R_PRIORITY_BAD,            /* threads (harness included) not at THREAD_PRIORITY_NORMAL             */
    X4P_R_PRIORITY_CLASS,
    X4P_R_PROCESS_AFFINITY,
    X4P_R_TSC_HZ,                  /* TSC rate measured against QPC before t0 (for cycle allowances)       */
    X4P_R_WORKLOAD_RC,
    X4P_R_IO_OUTSTANDING,          /* registered overlapped I/O still pending at t1 (must be 0)            */
    X4P_R_CENSUS_ERRORS,           /* API failures during the census or the freeze; any > 0 fails closed   */
    X4P_R_HARNESS_TID,
    X4P_R_MXCSR_HARNESS,           /* v2: the harness thread's MXCSR read immediately after run() returns  */
    X4P_R_POST_T1_MAX_CYCLES,      /* largest post-t1 cycle count among non-harness threads                */
    X4P_R_SELFCHECK_FLAGS,         /* bit0 token AppContainer, bit1 LPAC, bit2 elevated, bit3 in job,
                                      bit4 child-process creation blocked, bit5 MXCSR default at start     */
    /* ---- v2 fields ---- */
    X4P_R_MXCSR_EXIT_BAD,          /* registered threads whose MXCSR was not default when their fn returned */
    X4P_R_PRIORITY_EXIT_BAD,       /* registered threads whose priority was not normal when their fn returned */
    X4P_R_PRIORITY_HARNESS,        /* the harness thread's priority immediately after run() returns        */
    X4P_R_POST_T1_NEW_THREADS,     /* threads present before the hash that were absent at the t1 snapshot  */
    X4P_R_T1_SNAP_LAG_NS,          /* t1 -> the per-thread cycle snapshot (covered out of process)         */
    X4P_R_EXPECTED_AFFINITY,       /* the affinity mask every thread was compared against                 */
    X4P_R_OUT_OFFSET,
    X4P_R_FREEZE_OK,               /* 1 iff VirtualProtect(PAGE_READONLY) of the output view succeeded     */
    X4P_R_COUNT
};

/* CENSUS entry: X4P_CENSUS_W u64 */
enum { X4P_C_TID, X4P_C_FLAGS, X4P_C_CYC_T1, X4P_C_CYC_HASH, X4P_C_MXCSR, X4P_C_PRIORITY,
       X4P_C_AFFINITY, X4P_C_CREATE_FT, X4P_CENSUS_W };
/* CENSUS flags */
#define X4P_CF_PRE_T0        0x001u   /* existed at the pre-init snapshot                                */
#define X4P_CF_REGISTERED    0x002u
#define X4P_CF_NEW_UNREG     0x004u
#define X4P_CF_HARNESS       0x008u
#define X4P_CF_POST_T1_OVER  0x010u
#define X4P_CF_MXCSR_BAD     0x020u
#define X4P_CF_AFFINITY_BAD  0x040u
#define X4P_CF_PRIORITY_BAD  0x080u
#define X4P_CF_OPEN_FAILED   0x100u
#define X4P_CF_PARKED        0x200u
#define X4P_CF_EXITED        0x400u   /* in the t1 snapshot, gone by the census (CPU rule still applied) */
#define X4P_CF_POST_T1_NEW   0x800u   /* absent at the t1 snapshot                                       */

/* PROBES entry: X4P_PROBE_W u64 {id, attempted, succeeded, error, elapsed_us, extra} */
enum { X4P_P_ID, X4P_P_ATTEMPTED, X4P_P_SUCCEEDED, X4P_P_ERROR, X4P_P_ELAPSED_US, X4P_P_EXTRA, X4P_PROBE_W };

/* FAIL codes */
enum x4p_fail_code {
    X4P_F_ARGS = 1,          /* bad command line (incl. out_bytes not a non-zero multiple of 64) */
    X4P_F_MAP = 2,           /* could not map the output section or set its guard page          */
    X4P_F_WORKLOAD = 3,      /* unknown workload or workload init failed                        */
    X4P_F_FAULT = 4,         /* access violation in the output view or its guards               */
    X4P_F_JOIN_TIMEOUT = 5,  /* registered threads / I/O not joined in time                     */
    X4P_F_INTERNAL = 6
};

/* MXCSR: default control word (round to nearest, all exceptions masked, no FTZ/DAZ). The six status
 * flags (bits 0-5) are sticky and set by ordinary arithmetic, so only the control bits are compared. */
#define X4P_MXCSR_DEFAULT   0x1F80u
#define X4P_MXCSR_CTRL_MASK 0xFFC0u

/* Poison byte for fresh allocations (MEASUREMENT-SERVICE.md section 3 step 2). */
#define X4P_POISON_BYTE 0xA5u

#endif
