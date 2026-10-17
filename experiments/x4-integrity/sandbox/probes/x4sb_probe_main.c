/* x4sb_probe_main.c -- the OUTSIDE positive control (SANDBOX.md section 5): the orchestrator starts this
 * exe without job or AppContainer and requires the probes that must fail inside to succeed here.
 * Output: one line per probe, "probe <id> <attempted> <succeeded> <error> <elapsed_us> <extra>". */
#include <stdio.h>
#include <wchar.h>
#include "x4sb_probes.h"

int wmain(int argc, wchar_t **argv) {
    x4sb_probe_cfg c = {0};
    c.inside = 0;
    for (int i = 1; i < argc; i++) {
        if (!x4sb_probe_arg(&c, argc, argv, &i)) { fwprintf(stderr, L"unknown argument %s\n", argv[i]); return 2; }
    }
    x4sb_probe_result r[X4SB_MAX_RESULTS];
    int n = x4sb_run_probes(&c, r, X4SB_MAX_RESULTS);
    for (int i = 0; i < n; i++)
        printf("probe %llu %llu %llu %llu %llu %llu\n", (unsigned long long)r[i].id,
               (unsigned long long)r[i].attempted, (unsigned long long)r[i].succeeded,
               (unsigned long long)r[i].error, (unsigned long long)r[i].elapsed_us, (unsigned long long)r[i].extra);
    return 0;
}
