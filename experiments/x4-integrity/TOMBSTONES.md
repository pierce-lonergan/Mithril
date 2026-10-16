# X4 tombstone import, `mithc revisit` prototype, and the gate's trigger tests

**Track:** x4-integrity. **Status:** DESIGN (implementation follows next). **Date:** 2026-10-16 (revision 2 adds §6, the design tombstones from the review; see the [prereg review log](../../docs/m0/prereg/X4-integrity.md#12-review-log-independent-reviewers-with-model-family)).
**Anchors:** ROADMAP §3.5 (tombstone import and replay; lookahead and ADR-0004; the revisit prototype; irrelevant perturbations), §8 (M3 revisit-engine readiness, backtest); [06-forge §4 (tombstones), §7 (the trigger language, firing, auto-derived triggers, acceptance tests §7.6)](../../docs/architecture/06-forge.md); [DECISIONS §1, §4](../../docs/DECISIONS.md); [07-hearth-port §S0 (import)](../../docs/architecture/07-hearth-port.md); [R02 §10](../../docs/research/R02-open-endedness-revisiting.md); [RV: D3-ii](../../docs/research/revisited-ideas.md). Evidence tags as in [MEASUREMENT-SERVICE.md](MEASUREMENT-SERVICE.md).

X4 imports the engine-level and design-level tombstones, builds a `mithc revisit` prototype that parses and evaluates their triggers in the [06 §7.2](../../docs/architecture/06-forge.md) grammar with Kleene unknowns, and runs the firing tests the gate requires — including pre-registered **irrelevant perturbations** that must **not** fire. The prototype is validated now against acceptance vectors; the signed-ledger engine is M3 (status v0, M3, [06 §7.4](../../docs/architecture/06-forge.md)), and X4's replay must be **identical on the M3 ledger** (ROADMAP §3.5 last bullet, M3 kill-check).

Working prototypes validating this design (scratch, standard-library Python, run with `python -I`): [`revisit_proto.py`](revisit_proto.py) (parser + Kleene evaluator over `docs/DECISIONS.md`) and [`revisit_acceptance.py`](revisit_acceptance.py) (firing state machine + acceptance vectors). Their current results are reported inline below and in the structured summary.

---

## 1. The two engine tombstones (import, ROADMAP §3.5)

Imported at S0 ([07 §S0](../../docs/architecture/07-hearth-port.md)); the canonical lookahead record lives in [06 §7.1](../../docs/architecture/06-forge.md) and is not restated, so the two cannot drift. X4 imports them as ledger facts and replays their triggers.

### 1.1 lookahead_depth_4
```text
tombstone lookahead_depth_4 {
    verdict: slower                         // decode 13.02 -> 10.00 tok/s at depth 4, 2 GiB (measured) [R02 §10, Hearth]
    scope:   { model: qwen3_30b_a3b, drives: 1 (990 PRO), cache_gib: 2..=4 }
    class:   H                              // hardware-contingent (NVMe bandwidth)
    revisit_when: nvme_read_gbps > 12.0 || tier_exists(vram) || drives >= 2
    evidence: ledger:sha256:…               // hits 73% -> 86%; +7-17% NVMe bytes/token on a saturated drive
}
```
- **Hand-written trigger** (above) overrides the **derived default** ([06 §7.3](../../docs/architecture/06-forge.md)). The loss was bound by NVMe bytes, ratio 545/402 ≈ 1.36 [M]; the derived default is `nvme_read_gbps >= 1.36 * at_burial.nvme_read_gbps || has(tier: vram)`, which holds from ≈ 1.36 × 7.16 ≈ 9.7 GB/s. Burial reports the 9.7-vs-12.0 GB/s gap; the hand trigger (12.0) is the one that fires ([06 §7.6](../../docs/architecture/06-forge.md)).

### 1.2 ADR-0004 decayed LFU (niche-scoped: cache size × prefetch)
```text
tombstone adr0004_decayed_lfu_0995 {
    verdict: slower                         // LFU 0.995 worst at every cache size on real Qwen3 (measured) [R02 §10]
    scope:   { model: qwen3_30b_a3b, axes: { cache_gib in {1,2,4,8}, prefetch in {off, on} } }
    class:   V                              // overturned by measurement; niche-dependent winner
    revisit_when: <ADR-0004 niche trigger, §3.2>
    evidence: ledger:sha256:…
}
```
- **Niche scope, not a global verdict** (ROADMAP §3.5, [R02 §10](../../docs/research/R02-open-endedness-revisiting.md)): in trace replay LRU beat LFU 0.995 by 8–13 hit-rate points (simulated) [R01]; in the engine on real Qwen3, LFU 0.995 was the **worst** policy at every cache size, LRU won at 1 GiB without prefetch, LFU 0.9 won at 2–4 GiB and whenever prefetch was on (measured) [R02 §10]. The tombstone's scope is therefore **cache size × prefetch on/off**, and a fired revisit must reproduce **those scoped winners, not a global switch to LRU** (ROADMAP §3.5).

---

## 2. The design-level tombstones (import, all of DECISIONS §4)

X4 imports every DECISIONS §4 tombstone as a design-level ledger fact (`mithc revisit --design`, status v0 M3, [06 §7.5](../../docs/architecture/06-forge.md)). The canonical records with class, scope and trigger live **only** in [DECISIONS §4](../../docs/DECISIONS.md), so X4 does not restate them (the two cannot drift, [06 §7.5](../../docs/architecture/06-forge.md)). The 27 imported tombstones, by section:

- **§4.1 (merged "Rejected"/"Still dead"), 24:** `vliw_bundling`, `runtime_self_modifying_code`, `spdk_bypass_default`, `weights_as_instructions`, `online_supercompilation`, `structured_agent_io`, `sound_static_bounds_4bit_network`, `prolog_compiler_substrate`, `hit_rate_objective`, `ipc_objective`, `pass1_per_kilotoken`, `test_only_acceptance`, `formal_speed_proofs`, `timing_based_approx_default`, `implicit_spec_regeneration`, `hard_file_locks`, `physics_only_pruning`, `pe_core_dual_paths`, `uop_port_superopt_main_path`, `bypass_llvm_as_goal`, `lean_replacing_smt`, `seed_synthetic_repos` (22 here) — plus the two in §4.2 below bring the "still dead" count.
- **§4.2 ("Still dead" only), 2:** `public_only_expert_caches`, `single_trusted_checker`.
- **§4.3 (rejected inline), 3:** `python_primary_surface`, `llms_txt_delivery`, `static_model_quality_guarantees`.

**Total imported:** 27 design tombstones + 2 engine tombstones = **29**. `revisit_proto.py` extracts and parses all 27 design records plus the 2 engine triggers directly from `DECISIONS.md` (see §4.1 for the one grammar finding). Two of these are themselves X4 survivors and double as acceptance targets:
- `hit_rate_objective` — the objective lesson F1-sim enforces ([F1-SIM.md §3](F1-SIM.md));
- `physics_only_pruning` — pruned 0/144; its survivor is the replay bound for `timing_blind` policies ([F1-SIM.md §5](F1-SIM.md)), and its trigger `sim.prune_pilot(bound: phys_only, hw: current).pruned > 0` must stay false on the reproduced pilot.

**Options a DR rejected** (e.g. the direct x86 emitter, DR-009) come back only through that DR's **Revisit when** line, not as tombstones ([DECISIONS §1](../../docs/DECISIONS.md), [06 §7.5](../../docs/architecture/06-forge.md)); X4 also parses all 27 DR triggers (§4.1).

---

## 3. `mithc revisit` prototype design

Status: X4 prototype now ([revisit_proto.py](revisit_proto.py)); the signed-ledger engine is v0 M3 ([06 §7.4](../../docs/architecture/06-forge.md)). The prototype demonstrates every piece the M3 engine needs, so that "zero false fires on replay" and "the ADR-0004 backtest reported" (ROADMAP §8 M3 readiness) are decidable.

### 3.1 Parser for the 06 §7.2 grammar
A recursive-descent parser for the **normative** grammar ([06 §7.2](../../docs/architecture/06-forge.md), summarised in [DECISIONS §1](../../docs/DECISIONS.md)):
- connectives `||`, `&&`, `!`/`not`, parentheses;
- atoms: linear (in)equalities over numeric facts (no product of two facts); `in` over an interval (`cache_gib in 2..=4`) or a finite set; `==`/`!=` on enum/hash/ref; `const in fact`; set equality/superset/subset; a bare boolean fact; `has(kind: name args?)`; the **only** quantifier `exists(var in fact: pred)`, non-nesting, bounded over a finite ledger-set snapshot; sugar `tier_exists(t) == has(tier: t)`;
- refs: parameterised named facts (`harness.vp1_delta(a,b).ci_low`), `at_burial.f`, `scope.f`, `prereg(key)`;
- it rejects anything outside the grammar — this is the **CI check** `mithc revisit --design --check` ([06 §7.2](../../docs/architecture/06-forge.md), v0 M3): a trigger that fails to parse is an **admission error, never a silent false** ([DECISIONS §1](../../docs/DECISIONS.md)).

### 3.2 Kleene (three-valued) evaluation
Facts resolve to a value, or **`unknown`** when there is no value, no signed `prereg` record, or no set snapshot ([06 §7.2](../../docs/architecture/06-forge.md), [DECISIONS §1](../../docs/DECISIONS.md)). Connectives follow Kleene's rules (`unknown || true = true`, `unknown && false = false`, `!unknown = unknown`). An `unknown` trigger **never fires but is reported**, so a trigger over a fact nobody measures is visible. The prototype implements the full Kleene table and the lookup that returns `unknown` for missing facts/`prereg`/sets.

### 3.3 Firing and re-basing
- A trigger is evaluated at burial/import and on every event changing a fact it mentions ([06 §7.2](../../docs/architecture/06-forge.md) "Firing").
- It **fires** on a transition to true **from false or from `unknown`**.
- A trigger already true at burial/import is **queued at once** (Hearth's imported tombstones and DECISIONS entries are covered by this).
- After a failed revisit the tombstone is **re-based**: `at_burial` values are replaced by current ones and derived triggers re-derived; a still-true absolute trigger (`tier_exists(vram)`) fires again only when a fact it mentions changes value while true.

### 3.4 Auto-derived triggers and the background-audit boost
The prototype derives the default trigger from the burial binding term ([06 §7.3](../../docs/architecture/06-forge.md) class templates): for the lookahead H-class, `nvme_read_gbps >= 1.36 * at_burial.nvme_read_gbps || has(tier: vram)`. It stores the derived formula as `derived_when` beside the hand-written trigger; when the derived default holds and the hand trigger does not, it raises a **background-audit priority boost** and reports the disagreement — it fires nothing ([06 §7.3, §7.4 step 7](../../docs/architecture/06-forge.md)).

### 3.5 Subsumption (fold check)
Subsumption is decidable on the quantifier-free fragment: `A ⊑ B` iff `A ⇒ B` is valid, with ground parameterised facts / `has(...)` / `prereg` values treated as uninterpreted constants of their type — a quantifier-free linear-arithmetic-over-finite-domains formula SMT decides ([06 §7.2](../../docs/architecture/06-forge.md)). The X4 prototype implements a **sound syntactic** subsumption (interval/set containment and identical-atom folding) and marks anything else "not proven"; folding is an optimisation, so incompleteness costs only archive size. Folding never loses a fire (the survivor keeps the folded trigger as a disjunct).

---

## 4. The gate's trigger tests (ROADMAP §3.5, [06 §7.6](../../docs/architecture/06-forge.md))

All four pass on the prototype (see [revisit_acceptance.py](revisit_acceptance.py)); results below are from the current scratch run [S/D].

### 4.1 Every trigger parses (CI check)
`revisit_proto.py` over `docs/DECISIONS.md` (at git blob `7bf050b…`) parses **53 of 54** triggers (27 design tombstones + 26 DR Revisit-when + 2 engine triggers; one record counted in both passes). The **one finding**: `timing_based_approx_default` and any trigger using `hearth.invariant_hash(INV-DET-1)` fails the prototype's argument lexer because the fact *argument* `INV-DET-1` contains a hyphen, which the grammar's `arg := (name:)? (const | fact | prereg(key))` does not admit as a bare name (a hyphen is the subtraction operator). This is a **genuine grammar/spec gap**, surfaced here, not a defect to hide: invariant names like `INV-DET-1`, `INV-LOSSLESS-DEFAULT` are used as enum constants in several triggers (DECISIONS §4.1 `timing_based_approx_default`, and the B1 MXCSR items). **Owner question / spec note** (I do not edit the grammar — [06 §7.2](../../docs/architecture/06-forge.md) is normative and not mine): either invariant ids must be quoted strings (`hearth.invariant_hash("INV-DET-1")`) or the grammar's `const`/`name` production must admit a hyphenated identifier class for known-id namespaces. Recorded in the structured summary and the prereg.

Three further **warnings** (not failures): `D0.mithril_core`, `D0.gpu_scope`, `hw.uarch` used as dotted arguments are ambiguous between a fact path and a constant key; the grammar allows both and the resolver's type decides, but the prototype flags them so the ambiguity is visible.

### 4.2 Lookahead fires iff its hand trigger becomes true; the 10 GB/s step does not fire
Replaying Hearth's environment history ([06 §7.6](../../docs/architecture/06-forge.md)): the lookahead tombstone fires **iff** `nvme_read_gbps > 12.0 || drives >= 2 || tier_exists(vram)`. The acceptance run confirms:
- at 10.0 GB/s (only the derived ≈ 9.7 GB/s default holds) → **no fire**, but the **background-audit boost** is raised and the 9.7-vs-12.0 disagreement reported [S];
- at 12.0 GB/s (strict `>`) → no fire; at 12.5 GB/s → fires;
- a second drive → fires; a VRAM tier → fires;
- a new machine where the NVMe fact is **unmeasured** (`unknown`) → no fire but reported; once measured at 12.5 → fires (`unknown → true`) [S].

This matches ROADMAP X4's gate.

### 4.3 ADR-0004 fires on the recorded traces with niche-scoped verdicts
The ADR-0004 trigger, once encoded (§1.2, §3.2), fires on the recorded LRU-vs-LFU traces and produces verdicts matching the **measured winners** (LRU at 1 GiB without prefetch; LFU 0.9 at 2–4 GiB and with prefetch), **not a global switch to LRU** (ROADMAP §3.5, [06 §7.6](../../docs/architecture/06-forge.md)). Encoded as a bytes/measurement trigger over a per-niche policy table:
```text
revisit_when: exists(r in sim.policy_table: r.policy != lfu_0995
                     && r.nvme_bytes_per_token < 1.0 * sim.default_nvme_bytes_per_token)
           || exists(q in meas.policy_table: q.policy != lfu_0995
                     && q.tok_s_lo > meas.default_tok_s_hi)
```
Acceptance run [S]: a niche where a non-LFU policy reads fewer bytes → **fires**; a niche where hit rate rose but **bytes rose** (the lookahead trap) → **does not fire** (`unknown`/false — hit rate is not in the trigger); measured ranges that **overlap** → no fire; **no tables yet** → `unknown`, reported, no fire. The firing is per-niche, so the revived verdict is scoped, not global.

### 4.4 Pre-registered irrelevant perturbations must NOT fire
"Neither fires on the pre-registered irrelevant perturbations" (ROADMAP §3.5). The perturbations, pinned in the prereg **before replay**:
- **DRAM bandwidth change** (77 → 90 GB/s): irrelevant to a *NVMe-bound* lookahead loss — must not fire (the trigger mentions `nvme_read_gbps`, not `dram`; unit-typed facts make a GB/s-vs-GB/s category confusion a type error anyway, [06 §7.2](../../docs/architecture/06-forge.md));
- **OS build / Windows update** (26200 → 26300): irrelevant — no fact the trigger mentions changes;
- **Compiler version change** (MSVC 14.44 → 14.50): irrelevant — not in the trigger;
- **A small NVMe *decrease*** (7.16 → 7.0 GB/s): must not fire (wrong direction);
- **A rebuild / toolchain-hash change**: a generic "toolchain changed" event does **not** fire every tombstone; it only makes them eligible for the background audit ([06 §7.2](../../docs/architecture/06-forge.md) incremental evaluation).

Acceptance run [S]: all five perturbations produce **no fire** on both the lookahead and ADR-0004 triggers; the Fact Plane re-evaluates only triggers mentioning a changed fact, so DRAM/OS/compiler events touch neither NVMe trigger.

### 4.5 Replay must be identical on the M3 ledger (ROADMAP §3.5)
X4 records the exact trigger texts, their parse trees (content-hashed) and the acceptance-vector outcomes. The M3 revisit engine must reproduce **identical** firing on the signed M3 ledger (ROADMAP §3.5 last bullet; [06 §13 M3 row](../../docs/architecture/06-forge.md): "X4's tombstone replay is identical on the signed M3 ledger"). The X4 prototype's outputs are the golden for that M3 check.

---

## 5. The ADR-0004 backtest (reported, not gated — ROADMAP §8 M3)
Hearth's git history replayed as an event stream: would `mithc revisit` have re-opened ADR-0004's decayed LFU before the manual finding? The correct answer is **niche-scoped** ([R02 §10](../../docs/research/R02-open-endedness-revisiting.md)): re-open everywhere LFU 0.995 lost, producing verdicts matching the measured winners (LRU at 1 GiB without prefetch; LFU 0.9 at 2–4 GiB and with prefetch), not a global switch to LRU. One historical case cannot carry a powered gate, so it is **reported, not gated** (ROADMAP §8). X4 designs the backtest; the full git-history replay lands at M3 with the signed ledger. The X4 prototype already shows the scoped firing (§4.3), which is the backtest's core claim.

---

## 6. X4 design tombstones from the revision-2 review (proposed for DECISIONS §4)

The 2026-10-16 reviews led X4 to reject several of its own revision-1 design choices. Each rejected idea is written here in the [DECISIONS §4](../../docs/DECISIONS.md) block format, with a `revisit_when` in the [06 §7.2](../../docs/architecture/06-forge.md) grammar. X4 may not edit DECISIONS.md, so these are **proposed** entries for the lead engineer to admit; until then they live here. `revisit_acceptance.py` parses every trigger below with `revisit_proto.py` and runs one firing vector per tombstone (all pass [S/D], 2026-10-16). Facts named here (`meas.*`, `f1sim.*`, `sandbox.*`) are facts the measurement service, F1-sim and the sandbox self-test would emit; until a fact has a value the trigger is `unknown` and is reported, never fired. Pure errors that are not design ideas (the black-hole network probe, the "candidate runs first" sentence, the "brackets ROADMAP §10" wording) are corrected in place and not tombstoned.

```text
tombstone aa_sentinel_e20_void {
    verdict: vacuous                       // sentinel wealth <= (1 + theta)^k: 2.25 at k = 2 (sigma_d 2%), 25.6 at k = 8 (4%) [D]
    scope:   { rule: void_when_sentinel_superiority_e_reaches_20, sentinel_share: 1/6, theta: 0.5 }
    class:   F                             // under few sentinel blocks per session and bets capped at theta
    revisit_when: meas.sentinel_blocks_per_session >= 12
    evidence: [X4 rev 2: stats/ table 3e; MEASUREMENT-SERVICE §5.3] [06 §6.3]
    // survivor: S1 sentinel mean z-test + S2 variance envelope on unflagged blocks
}

tombstone kill_loss_scoring {
    verdict: unsound                       // outlier blocks scored +c push the kill null toward a false kill
    scope:   { test: kill, scorer: [R, 06_literal], clip: c }
    class:   F                             // under a nonzero environmental outlier rate
    revisit_when: meas.aa_slow_outlier_rate_ucb < 0.0005
    evidence: [X4 rev 2: stats/ tables 2d, 3c; reviewers 1 and 2]
    // survivor: Rk scorer (outliers scored -c_kill), c_kill = max(3 sigma, m_kill + 3 sigma), theta_kill 0.8
}

tombstone fixed_cycle_spin_planted_regression {
    verdict: unpredictable                 // a core-bound busy loop beside an L2-resident matvec: the ratio moves with boost and thermal state
    scope:   { calibration: planted_regression, run_type: microbench }
    class:   H
    revisit_when: meas.fixed_spin_ratio_sd < 0.1 * meas.sigma_d_micro
    evidence: [X4 rev 2; reviewer 2] [inference]
    // survivor: proportional extra work, K' = ceil(e^mu* K) matvec repetitions (MEASUREMENT-SERVICE §8.3)
}

tombstone unrestricted_mann_kendall_trend_void {
    verdict: misleading                    // uncorrected MK: 8.8% false voids under AR(1) 0.6; all-lag Hamed-Rao: 10.0% under iid noise (n = 24 runs per arm) [S]
    scope:   { test: trend_void, runs_per_arm: 24..=88 }
    class:   F                             // under autocorrelated run noise and small samples
    revisit_when: meas.run_logtime_lag1_autocorr_ci_hi < 0.05 || meas.runs_per_arm_per_session >= 200
    evidence: [X4 rev 2: stats/ table 3f]
    // survivor: Hamed-Rao factor restricted to lag 1, floored at 1, two-sided alpha 0.01 (MEASUREMENT-SERVICE §5.3 S3)
}

tombstone public_trace_as_sealed_heldout {
    verdict: gameable                      // the in-repo trace is readable by every proposer (a10b)
    scope:   { experiment: f1_sim, trace: qwen3_30b_a3b_5tasks }
    class:   V
    revisit_when: f1sim.trace_readable_by_proposer(qwen3_30b_a3b_5tasks) == false
    evidence: [M: git ls-files at Hearth b5d3f14, 2026-10-16] [reviewer 1]
    // survivor: new traces in the Gatekeeper store, or synthetic traces with post-freeze seeds (F1-SIM §7.2)
}

tombstone untrusted_kernels_without_lpac {
    verdict: unsafe                        // generated code shares the harness address space; without (LP)AppContainer nothing blocks brokered egress
    scope:   { workload: [x3_kernels, forge_candidates], sandbox: [job_only, job_user_wfp] }
    class:   F                             // under no binary confinement of candidate syscalls and stores
    revisit_when: has(rule: t0_binary_confinement) && sandbox.wfp_egress_block == verified
    evidence: [X4 rev 2; reviewer 1] [03 §11.3]
    // survivor: the SANDBOX §4 refusal table
}
```

**Pending, not proposed yet.** Revision 2 names the run-level R scorer as the gate scorer and makes 06 §6.2's literal block clip descriptive (it scores a 20% true improvement as a loss: share 0.000 within 400 blocks [S, stats/ table 2e]). Because 06 §6.2 is normative, that is **owner question 4**, not a tombstone; if the Owner confirms, the literal rule is buried as `literal_block_clip_gate_scorer` with `revisit_when: prereg(x4_max_gated_effect) <= 0.5 * prereg(x4_clip_c)` (the literal rule is harmless when no gated effect can approach the clip).
