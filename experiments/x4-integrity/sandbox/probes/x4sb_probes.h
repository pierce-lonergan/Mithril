/* x4sb_probes.h -- sandbox self-test probes (SANDBOX.md section 5).
 *
 * The same probe code runs twice per session: inside the sandbox (linked into the harness, run with
 * --selftest before any workload) and outside it (x4sb_probe.exe, started by the orchestrator without
 * job or AppContainer) as the positive control. A probe only records what happened: attempted,
 * succeeded, the Win32/WSA/HRESULT error and the elapsed time. The orchestrator (x4sandbox crate,
 * selftest.rs) decides pass/fail from the inside/outside pair; a probe never judges itself.
 */
#ifndef X4SB_PROBES_H
#define X4SB_PROBES_H

#include <stdint.h>

enum x4sb_probe_id {
    X4SB_TOKEN_APPCONTAINER = 1, X4SB_TOKEN_LPAC = 2, X4SB_TOKEN_ELEVATED = 3,
    X4SB_TOKEN_ADMIN_ENABLED = 4, X4SB_TOKEN_USER_IS_MEASURE = 5,
    X4SB_JOB_IN_JOB = 10, X4SB_JOB_CREATE_CHILD = 11, X4SB_JOB_BREAKAWAY = 12, X4SB_JOB_CLEAR_LIMITS = 13,
    X4SB_JOB_RAISE_PRIORITY = 14, X4SB_JOB_WIDEN_AFFINITY = 15, X4SB_JOB_QUERY_OWN_LIMITS = 16,
    X4SB_NET_LOOPBACK_TCP = 20, X4SB_NET_LAN_TCP = 21, X4SB_NET_DNS = 22,
    X4SB_BROKER_PIPE = 30, X4SB_BROKER_WMI = 31, X4SB_BROKER_TASKSCHED = 32, X4SB_BROKER_COM_LOCAL = 33,
    X4SB_SEALED_READ = 40, X4SB_SEALED_WRITE = 41, X4SB_SEALED_ALT_READ = 42, X4SB_SEALED_ALT_WRITE = 43,
    X4SB_SEALED_HARDLINK = 47, X4SB_SEALED_JUNCTION_READ = 48,
    X4SB_SCRATCH_EMPTY = 50, X4SB_SCRATCH_WRITE = 51, X4SB_DIRECT_IO = 52, X4SB_LARGE_PAGES = 53,
    X4SB_MXCSR_DEFAULT = 60, X4SB_EXE_DIR_WRITE = 70
};

typedef struct {
    uint64_t id, attempted, succeeded, error, elapsed_us, extra;
} x4sb_probe_result;

#define X4SB_MAX_ALT 8
#define X4SB_MAX_RESULTS 64

typedef struct {
    int inside;                       /* 1 when running inside the sandbox                        */
    uint16_t loopback_port;           /* orchestrator's loopback listener (0: skip)                */
    const wchar_t *lan_host;          /* LAN positive-control target "a.b.c.d" (NULL: skip)        */
    uint16_t lan_port;
    const wchar_t *dns_name;          /* a name not in the hosts file (NULL: skip)                 */
    const wchar_t *pipe_name;         /* orchestrator-created named pipe (NULL: skip)              */
    int com_local;                    /* 1: run the out-of-process COM activation probe            */
    const wchar_t *com_clsid;         /* "{...}" CLSID for that probe                               */
    const wchar_t *sealed_path;       /* a sealed file (NULL: skip the sealed probes)              */
    const wchar_t *sealed_dir;        /* its directory (junction target)                           */
    const wchar_t *alt[X4SB_MAX_ALT]; /* alternate names of sealed_path computed outside            */
    int n_alt;
    const wchar_t *scratch;           /* the run's scratch directory (NULL: skip)                  */
    const wchar_t *measure_sid;       /* SID string of MithrilMeasure, or NULL if it does not exist */
} x4sb_probe_cfg;

/* Runs every configured probe; returns the number of results written (<= cap). */
int x4sb_run_probes(const x4sb_probe_cfg *cfg, x4sb_probe_result *out, int cap);
/* Consumes one "--flag value" probe argument at argv[*i] (advancing *i); returns 0 if not a probe flag. */
int x4sb_probe_arg(x4sb_probe_cfg *c, int argc, wchar_t **argv, int *i);

#endif
