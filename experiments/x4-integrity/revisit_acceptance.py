#!/usr/bin/env python3
"""Scratch: firing state machine + acceptance-test vectors for the X4 tombstone replay design.
Checks that the expected outcomes written in TOMBSTONES.md are what a Kleene evaluator produces."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from revisit_proto import parse, ev, U, T, F

HAND = "hw.nvme_aggregate_read_gbps > 12.0 || has(tier: vram) || hw.nvme_drives >= 2"
DERIVED = "hw.nvme_aggregate_read_gbps >= 1.36 * at_burial.hw.nvme_aggregate_read_gbps || has(tier: vram)"
hand, _ = parse(HAND)
derived, _ = parse(DERIVED)


class Tomb:
    def __init__(self, trig, derived, burial):
        self.trig, self.derived, self.burial = trig, derived, dict(burial)
        self.last = None; self.queue = []

    def step(self, label, store):
        v = ev(self.trig, store, burial=self.burial)
        d = ev(self.derived, store, burial=self.burial) if self.derived else None
        fired = (v is T) and (self.last is not T)
        boost = (d is T) and (v is not T)
        self.last = v
        return label, v, d, fired, boost

    def rebase(self, store):
        for k in list(self.burial):
            if k in store: self.burial[k] = store[k]


def show(rows):
    for label, v, d, fired, boost in rows:
        f = lambda x: "U" if x is None else ("T" if x else "F")
        print(f"  {label:58} hand={f(v)} derived={f(d)} fire={fired!s:5} audit_boost={boost}")


base = {"hw.nvme_aggregate_read_gbps": 7.16, "hw.nvme_drives": 1, "catalogue:tier": ["dram", "nvme"],
        "hw.dram_read_gbps": 77.0, "hw.os_build": "26200", "toolchain.cc": "msvc-14.44"}
t = Tomb(hand, derived, {"hw.nvme_aggregate_read_gbps": 7.16})
rows = [t.step("L0 burial state (7.16 GB/s, 1 drive, no vram)", base)]
hist = [
    ("L1 irrelevant: DRAM 77 -> 90 GB/s", {"hw.dram_read_gbps": 90.0}),
    ("L2 irrelevant: OS build change", {"hw.os_build": "26300"}),
    ("L3 irrelevant: compiler change", {"toolchain.cc": "msvc-14.50"}),
    ("L4 irrelevant: NVMe 7.16 -> 7.0 GB/s", {"hw.nvme_aggregate_read_gbps": 7.0}),
    ("L5 NVMe 9.0 GB/s (both false)", {"hw.nvme_aggregate_read_gbps": 9.0}),
    ("L6 NVMe 10.0 GB/s (derived only: no fire, boost)", {"hw.nvme_aggregate_read_gbps": 10.0}),
    ("L7 NVMe 12.0 GB/s (strict >: no fire)", {"hw.nvme_aggregate_read_gbps": 12.0}),
    ("L8 NVMe 12.5 GB/s (fire)", {"hw.nvme_aggregate_read_gbps": 12.5}),
]
store = dict(base)
for label, upd in hist:
    store.update(upd); rows.append(t.step(label, store))
print("lookahead_depth_4, NVMe path:"); show(rows)

for label, upd in [("L9 second drive", {"hw.nvme_drives": 2}), ("L10 VRAM tier", {"catalogue:tier": ["dram", "nvme", "vram"]})]:
    t2 = Tomb(hand, derived, {"hw.nvme_aggregate_read_gbps": 7.16}); s2 = dict(base)
    r = [t2.step("burial", s2)]; s2.update(upd); r.append(t2.step(label, s2)); print(label); show(r)

# unknown -> true fires
t3 = Tomb(hand, derived, {"hw.nvme_aggregate_read_gbps": 7.16})
s3 = {"hw.nvme_drives": 1, "catalogue:tier": ["dram", "nvme"]}
r = [t3.step("L11 new machine, NVMe fact not yet measured (U)", s3)]
s3["hw.nvme_aggregate_read_gbps"] = 12.5; r.append(t3.step("L12 measured 12.5 (U -> T fires)", s3))
print("unknown path:"); show(r)

# re-base after failed revisit
t4 = Tomb(hand, derived, {"hw.nvme_aggregate_read_gbps": 7.16}); s4 = dict(base); s4["hw.nvme_aggregate_read_gbps"] = 12.5
r = [t4.step("L13 fired at 12.5", s4)]
t4.rebase(s4)
r.append(t4.step("L14 after failed revisit, re-based (still T: no refire)", s4))
s4["hw.nvme_aggregate_read_gbps"] = 13.0; r.append(t4.step("L15 12.5 -> 13.0 while T (value change; 06: fires again)", s4))
print("re-base path:"); show(r)

# ADR-0004 niche trigger: exists over a policy table; bytes, not hit rate
ADR = ("exists(r in sim.policy_table: r.policy != lfu_0995 && "
       "r.nvme_mb_per_token < 1.0 * sim.default_nvme_mb_per_token) || "
       "exists(q in meas.policy_table: q.policy != lfu_0995 && q.tok_s_lo > meas.default_tok_s_hi)")
adr, p = parse(ADR)
print("ADR-0004 trigger parses; warnings:", p.warn)
niche_sim = {"sim.policy_table": [{"policy": "lru", "nvme_mb_per_token": 380.0}, {"policy": "lfu_0995", "nvme_mb_per_token": 500.0}],
             "sim.default_nvme_mb_per_token": 500.0}
print("  sim bytes lower -> ", ev(adr, niche_sim))
hit_only = {"sim.policy_table": [{"policy": "lookahead4", "nvme_mb_per_token": 545.0, "hit_rate": 0.86}],
            "sim.default_nvme_mb_per_token": 402.0}
print("  hit rate up but bytes up (must not fire) -> ", ev(adr, hit_only))
meas_overlap = {"meas.policy_table": [{"policy": "lru", "tok_s_lo": 12.9}], "meas.default_tok_s_hi": 13.04,
                "sim.policy_table": [], "sim.default_nvme_mb_per_token": 500.0}
print("  measured ranges overlap (no fire) -> ", ev(adr, meas_overlap))
print("  no tables yet (unknown) -> ", ev(adr, {}))

# ---------------------------------------------------------------------------------------------
# Revision 2 (2026-10-16): the X4 design tombstones of TOMBSTONES.md section 6 must parse under the
# 06-forge 7.2 grammar, and each must fire on the event its trigger names and not before.
# ---------------------------------------------------------------------------------------------
from revisit_proto import extract

X4_TOMBS = ("aa_sentinel_e20_void", "kill_loss_scoring", "fixed_cycle_spin_planted_regression",
            "unrestricted_mann_kendall_trend_void", "public_trace_as_sealed_heldout",
            "untrusted_kernels_without_lpac")
_md = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "TOMBSTONES.md"), encoding="utf-8").read()
_found = {name: trig for kind, name, trig, _h in extract(_md) if name in X4_TOMBS}
_missing = [n for n in X4_TOMBS if n not in _found]
print("\nX4 revision-2 tombstones (TOMBSTONES.md section 6): found", len(_found), "of", len(X4_TOMBS),
      ("; MISSING " + ", ".join(_missing)) if _missing else "")
VECTORS = {  # (before-event store, after-event store): expected (before, after) values; fire = F/U -> T
    "aa_sentinel_e20_void": ({"meas.sentinel_blocks_per_session": 2}, {"meas.sentinel_blocks_per_session": 12}),
    "kill_loss_scoring": ({"meas.aa_slow_outlier_rate_ucb": 0.0016}, {"meas.aa_slow_outlier_rate_ucb": 0.0004}),
    "fixed_cycle_spin_planted_regression": ({}, {"meas.fixed_spin_ratio_sd": 0.001, "meas.sigma_d_micro": 0.02}),
    "unrestricted_mann_kendall_trend_void": ({"meas.run_logtime_lag1_autocorr_ci_hi": 0.3, "meas.runs_per_arm_per_session": 24},
                                             {"meas.run_logtime_lag1_autocorr_ci_hi": 0.3, "meas.runs_per_arm_per_session": 240}),
    "public_trace_as_sealed_heldout": ({"f1sim.trace_readable_by_proposer(qwen3_30b_a3b_5tasks)": "true"},
                                       {"f1sim.trace_readable_by_proposer(qwen3_30b_a3b_5tasks)": "false"}),
    "untrusted_kernels_without_lpac": ({"catalogue:rule": [], "sandbox.wfp_egress_block": "verified"},
                                       {"catalogue:rule": ["t0_binary_confinement"], "sandbox.wfp_egress_block": "verified"}),
}
_ok = True
for name in X4_TOMBS:
    trig = _found.get(name)
    if trig is None:
        _ok = False; continue
    try:
        tree, p = parse(trig)
    except Exception as e:  # ParseError
        print(f"  FAIL parse {name}: {e} :: {trig}"); _ok = False; continue
    before, after = VECTORS[name]
    vb, va = ev(tree, before), ev(tree, after)
    fired = (va is T) and (vb is not T)
    f = lambda x: "U" if x is None else ("T" if x else "F")
    print(f"  {name:38} parses; before={f(vb)} after={f(va)} fire={fired}" + (f"; WARN {p.warn}" if p.warn else ""))
    _ok &= fired
print("X4 revision-2 tombstones:", "all parse and fire as specified" if _ok else "FAILURES above")
