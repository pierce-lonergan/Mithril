#!/usr/bin/env python3
"""x4_devcheck.py -- DEVELOPMENT self-test of the X4 C harness (non-gate).

Spawns x4harness.exe for each dev_* workload, reads the framed messages it writes to stdout, decodes
the typed REPORT (and the thread census), and checks that each harness integrity signal is what that
dev probe is designed to produce. This exercises the clock/join/census/MXCSR/poison machinery on
synthetic workloads only (a busy loop, a sleep, a leaking thread, ...). It does NOT run the sealed
HACK-SUITE catalogue, and it spends no alpha and collects no calibration data.

The wire format mirrors service/proto/x4proto.h. This script is the C-side counterpart of the Rust
orchestrator's proto decoder; it is a convenience, not the trusted bracket.

Usage:  python x4_devcheck.py <path-to-x4harness.exe>
Exit 0 iff every dev probe produced its expected signal.
"""
import struct
import subprocess
import sys

MAGIC = 0x34503458
T_HELLO, T_START, T_STOP, T_CENSUS, T_REPORT, T_FAIL, T_PROBES = 1, 2, 3, 4, 5, 6, 7

# REPORT field order (x4proto.h enum x4p_report_field, protocol v2: 38 fields). This is the C-side
# harness view only; the orchestrator-side detectors (clock bracket, post-STOP cycles, protocol order,
# early STOP) are checked by the Rust run_e2e path, not here.
R = ["VERSION", "T0_NS", "T1_NS", "HASH0", "HASH1", "HASH2", "HASH3", "OUT_BYTES",
     "POISON_RESIDUAL_WORDS", "SLACK_MODIFIED_BYTES", "SALT", "THREADS_AT_CENSUS",
     "NEW_UNREGISTERED", "REGISTERED_CREATED", "REGISTERED_UNPARKED", "POST_T1_VIOLATIONS",
     "MXCSR_BAD_THREADS", "MXCSR_ENTRY_BAD", "AFFINITY_BAD", "PRIORITY_BAD", "PRIORITY_CLASS",
     "PROCESS_AFFINITY", "TSC_HZ", "WORKLOAD_RC", "IO_OUTSTANDING", "CENSUS_ERRORS",
     "HARNESS_TID", "MXCSR_HARNESS", "POST_T1_MAX_CYCLES", "SELFCHECK_FLAGS",
     "MXCSR_EXIT_BAD", "PRIORITY_EXIT_BAD", "PRIORITY_HARNESS", "POST_T1_NEW_THREADS",
     "T1_SNAP_LAG_NS", "EXPECTED_AFFINITY", "OUT_OFFSET", "FREEZE_OK"]
MXCSR_DEFAULT, MXCSR_CTRL_MASK = 0x1F80, 0xFFC0


def parse_frames(buf):
    msgs, off = [], 0
    while off + 16 <= len(buf):
        magic, mtype, plen, seq = struct.unpack_from("<IIII", buf, off)
        off += 16
        if magic != MAGIC:
            raise ValueError("bad magic at %d: %08x" % (off - 16, magic))
        payload = buf[off:off + plen]
        off += plen
        vals = list(struct.unpack_from("<%dQ" % (plen // 8), payload)) if plen else []
        msgs.append((mtype, seq, vals))
    return msgs


def run(exe, workload, param=None, out_bytes=4096, extra=None):
    cmd = [exe, "--workload", workload, "--out-bytes", str(out_bytes)]
    if param is not None:
        cmd += ["--param", str(param)]
    if extra:
        cmd += extra
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    msgs = parse_frames(p.stdout)
    rep, census, order = None, [], []
    for mtype, seq, vals in msgs:
        order.append(mtype)
        if mtype == T_REPORT:
            rep = dict(zip(R, vals))
        elif mtype == T_CENSUS:
            w = 8
            census = [vals[i:i + w] for i in range(0, len(vals), w)]
        elif mtype == T_FAIL:
            rep = {"FAIL": vals}
    return order, rep, census, p.returncode


# (workload, expectation predicate on report, human description)
def harness_harness_mxcsr_ok(r):
    return (r.get("MXCSR_HARNESS", MXCSR_DEFAULT) & MXCSR_CTRL_MASK) == MXCSR_DEFAULT


CLEAN = lambda r: (r.get("NEW_UNREGISTERED") == 0 and r.get("REGISTERED_UNPARKED") == 0 and
                   r.get("POISON_RESIDUAL_WORDS") == 0 and r.get("SLACK_MODIFIED_BYTES") == 0 and
                   r.get("MXCSR_BAD_THREADS") == 0 and r.get("MXCSR_ENTRY_BAD") == 0 and
                   r.get("MXCSR_EXIT_BAD") == 0 and r.get("PRIORITY_EXIT_BAD") == 0 and
                   r.get("POST_T1_NEW_THREADS") == 0 and r.get("POST_T1_VIOLATIONS") == 0 and
                   r.get("AFFINITY_BAD") == 0 and r.get("PRIORITY_BAD") == 0 and r.get("FREEZE_OK") == 1 and
                   harness_harness_mxcsr_ok(r) and r.get("WORKLOAD_RC") == 0 and
                   r.get("CENSUS_ERRORS") == 0 and r.get("IO_OUTSTANDING") == 0)

# A tiny spin/idle budget (in TSC cycles) so dev_after_t1's post-t1 burst trips the in-process rule.
TIGHT = ["--spin-cycles", "100000", "--idle-cycles", "100000"]

CASES = [
    ("dev_write",   {}, lambda r: r and "FAIL" not in r and CLEAN(r), "clean full output"),
    ("dev_busy",    {"param": 3000000}, lambda r: r and "FAIL" not in r and CLEAN(r) and r["T1_NS"] > r["T0_NS"], "clean busy loop, t1>t0"),
    ("dev_sleep",   {"param": 20}, lambda r: r and "FAIL" not in r and CLEAN(r) and (r["T1_NS"]-r["T0_NS"]) >= 15_000_000, "sleep >=15ms inside clock"),
    ("dev_io",      {}, lambda r: r and "FAIL" not in r and r["IO_OUTSTANDING"] == 0 and CLEAN(r), "overlapped I/O joined"),
    ("dev_parked",  {"param": 500000}, lambda r: r and "FAIL" not in r and r["REGISTERED_UNPARKED"] == 0, "parked worker allowed"),
    ("dev_leak_registered", {}, lambda r: r and r.get("REGISTERED_UNPARKED", 0) >= 1, "unjoined registered worker flagged (a3)"),
    ("dev_raw_thread", {}, lambda r: r and r.get("NEW_UNREGISTERED", 0) >= 1, "raw CreateThread after t0 flagged (a3b)"),
    ("dev_mxcsr_worker", {}, lambda r: r and r.get("MXCSR_BAD_THREADS", 0) >= 1, "worker FTZ/DAZ flagged (a9)"),
    ("dev_partial_output", {}, lambda r: r and r.get("POISON_RESIDUAL_WORDS", 0) > 0, "unwritten output leaves poison (a4)"),
    ("dev_overflow", {}, lambda r: r and ("FAIL" in r and r["FAIL"][0] == T_FAULT) or r.get("SLACK_MODIFIED_BYTES", 0) > 0, "write past extent faults the guard page"),
    ("dev_underflow", {}, lambda r: r and r.get("SLACK_MODIFIED_BYTES", 0) > 0, "write before extent flagged (slack)"),
    ("dev_priority", {}, lambda r: r and r.get("PRIORITY_BAD", 0) >= 1, "worker priority raise flagged (a31)"),
    # v2 regression probes (the reviewers' rev_* equivalents), harness-visible signals:
    ("dev_main_ftz", {}, lambda r: r and not harness_harness_mxcsr_ok(r), "FTZ/DAZ left on the harness thread (a9, rev_main_ftz)"),
    ("dev_main_prio", {}, lambda r: r and (r.get("PRIORITY_HARNESS", 0) != 0 or r.get("PRIORITY_BAD", 0) >= 1), "harness-thread priority raised (a31, rev_main_prio)"),
    ("dev_rc", {}, lambda r: r and r.get("WORKLOAD_RC", 0) != 0, "nonzero workload status (rev_rc)"),
    ("dev_mxcsr_joined", {}, lambda r: r and r.get("MXCSR_EXIT_BAD", 0) >= 1, "worker set FTZ/DAZ then joined (a9)"),
    ("dev_priority_joined", {}, lambda r: r and r.get("PRIORITY_EXIT_BAD", 0) >= 1, "worker raised priority then joined (a31)"),
    ("dev_aff_narrow", {"extra": ["--affinity", "3"]}, lambda r: r and r.get("AFFINITY_BAD", 0) >= 1, "worker narrowed to a core off the declared mask (a31, rev_aff_narrow)"),
    ("dev_init_thread", {}, lambda r: r and r.get("NEW_UNREGISTERED", 0) >= 1, "raw thread created in init flagged (a3b)"),
    ("dev_init_output", {}, lambda r: r and r.get("POISON_RESIDUAL_WORDS", 0) > 0, "output written in init is re-poisoned (a4)"),
    # The post-t1 CPU rule (a3b) is demonstrated by dev_leak_registered above, whose registered worker
    # spins continuously across the census window (POST_T1_VIOLATIONS fires reliably). dev_after_t1's
    # one-shot 30 ms burst is timing-sensitive on whether it lands in the short in-process [t1, hash]
    # window, so it is not asserted here; the orchestrator's post-STOP cycle window is coarse (dominated
    # by ~0.58 Gcycles of harness census cost on this box), so it is not the fine a3b detector either.
    #
    # Review round 3 (2026-10-16/17): gaps the in-process record is BLIND to by construction. Each must
    # read CLEAN here; the out-of-process check that catches it runs in the orchestrator (`x4svc run`):
    # pre_start_wall/pre_start_cycles, window_cores, outside_extent_oop. Asserting CLEAN keeps the blind
    # spot explicit: if one of these ever read dirty in-process, the trust-class table would be wrong.
    ("dev_init_precompute", {"param": 300}, lambda r: r and "FAIL" not in r and CLEAN(r), "init precompute reads clean in-process (OOP: pre_start_*)"),
    ("dev_par_exited", {"param": 200000000}, lambda r: r and "FAIL" not in r and CLEAN(r), "parallel raw threads joined before t1 read clean (OOP: window_cores)"),
    ("dev_guard_lift", {"param": 10}, lambda r: r and "FAIL" not in r and CLEAN(r), "guard lifted, write past extent reads clean (OOP: trailing page)"),
    ("dev_forge_frames", {}, lambda r: r and "FAIL" not in r and CLEAN(r), "forged START..REPORT stream reads clean (OOP windows bound it)"),
]
T_FAULT = 4  # X4P_F_FAULT


def main(argv):
    if len(argv) < 2:
        print("usage: x4_devcheck.py <x4harness.exe>", file=sys.stderr)
        return 2
    exe = argv[1]
    passed = failed = 0
    for wl, kw, pred, desc in CASES:
        try:
            order, rep, census, rc = run(exe, wl, kw.get("param"), kw.get("out_bytes", 4096), kw.get("extra"))
        except Exception as e:
            print("FAIL  %-22s spawn/parse error: %s" % (wl, e))
            failed += 1
            continue
        ok = False
        try:
            ok = bool(pred(rep))
        except Exception as e:
            ok = False
            desc += " (pred error %s)" % e
        tag = "ok  " if ok else "FAIL"
        detail = ""
        if rep and "FAIL" not in rep:
            detail = ("newunreg=%d regunpark=%d poisonresid=%d slack=%d mxcsrbad=%d mxcsrentry=%d "
                      "affbad=%d priobad=%d censusN=%d err=%d dt_ms=%.2f post_max_cyc=%d" % (
                          rep["NEW_UNREGISTERED"], rep["REGISTERED_UNPARKED"], rep["POISON_RESIDUAL_WORDS"],
                          rep["SLACK_MODIFIED_BYTES"], rep["MXCSR_BAD_THREADS"], rep["MXCSR_ENTRY_BAD"],
                          rep["AFFINITY_BAD"], rep["PRIORITY_BAD"], rep["THREADS_AT_CENSUS"],
                          rep["CENSUS_ERRORS"], (rep["T1_NS"] - rep["T0_NS"]) / 1e6, rep["POST_T1_MAX_CYCLES"]))
        elif rep and "FAIL" in rep:
            detail = "FAIL frame %s" % rep["FAIL"]
        print("%s  %-22s %-42s %s" % (tag, wl, desc, detail))
        passed += ok
        failed += (not ok)
    print("\n%d passed, %d failed" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
