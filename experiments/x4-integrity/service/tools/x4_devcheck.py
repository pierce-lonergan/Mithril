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

# REPORT field order (x4proto.h enum x4p_report_field)
R = ["VERSION", "T0_NS", "T1_NS", "HASH0", "HASH1", "HASH2", "HASH3", "OUT_BYTES",
     "POISON_RESIDUAL_WORDS", "SLACK_MODIFIED_BYTES", "SALT", "THREADS_AT_CENSUS",
     "NEW_UNREGISTERED", "REGISTERED_CREATED", "REGISTERED_UNPARKED", "POST_T1_VIOLATIONS",
     "MXCSR_BAD_THREADS", "MXCSR_ENTRY_BAD", "AFFINITY_BAD", "PRIORITY_BAD", "PRIORITY_CLASS",
     "PROCESS_AFFINITY", "TSC_HZ", "WORKLOAD_RC", "IO_OUTSTANDING", "CENSUS_ERRORS",
     "HARNESS_TID", "MXCSR_HARNESS", "POST_T1_MAX_CYCLES", "SELFCHECK_FLAGS"]


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
CLEAN = lambda r: (r.get("NEW_UNREGISTERED") == 0 and r.get("REGISTERED_UNPARKED") == 0 and
                   r.get("POISON_RESIDUAL_WORDS") == 0 and r.get("SLACK_MODIFIED_BYTES") == 0 and
                   r.get("MXCSR_BAD_THREADS") == 0 and r.get("MXCSR_ENTRY_BAD") == 0 and
                   r.get("AFFINITY_BAD") == 0 and r.get("PRIORITY_BAD") == 0 and
                   r.get("CENSUS_ERRORS") == 0 and r.get("IO_OUTSTANDING") == 0)

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
    ("dev_overflow", {}, lambda r: r and r.get("SLACK_MODIFIED_BYTES", 0) > 0, "write past extent flagged (overflow)"),
    ("dev_priority", {}, lambda r: r and r.get("PRIORITY_BAD", 0) >= 1, "worker priority raise flagged (a31)"),
]


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
