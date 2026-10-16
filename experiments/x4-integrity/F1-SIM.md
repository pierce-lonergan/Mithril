# F1-sim — the policy Forge on a scratch `hearth.sim`

**Track:** x4-integrity. **Status:** DESIGN (implementation follows next). **Date:** 2026-10-16 (revision 2, after two same-family, independent-context reviews: sealed traces redefined, a differential byte counter added, the benefit criterion pinned; see the [prereg review log](../../docs/m0/prereg/X4-integrity.md#12-review-log-independent-reviewers-with-model-family)).
**Anchors:** ROADMAP §3.5 (F1-sim), §8 (M0 Forge-benefit row: readiness + benefit); [06-forge §2.1 (slots), §3 (cascade), §5.3 (plausibility), §5.4 (replay prune), §7 (tombstones)](../../docs/architecture/06-forge.md); [RV: D2-A, D2-B, D3-ii](../../docs/research/revisited-ideas.md); [R02 §10](../../docs/research/R02-open-endedness-revisiting.md); Hearth `docs/SIMULATOR.md`, `python/hearth/sim/`. Evidence tags as in [MEASUREMENT-SERVICE.md](MEASUREMENT-SERVICE.md); every number F1-sim emits is **SIMULATED [S]** (INV-HONEST).

F1-sim is the M0 pilot of the Forge's policy line: eviction and prefetch candidates evaluated against a **scratch copy** of Hearth's simulator behind an `hx_policy` shim, scored on **NVMe bytes/token and stall time, never hit rate**, with the MIN-bytes oracle validated against brute-force OPT first, replay pruning only for `timing_blind` policies, and every result labelled SIMULATED. It proves the Forge cascade and the tombstone/replay machinery work before any engine (M4) or grant (M6) exists.

---

## 1. Why the simulator, why now

The prior (pre-registered with [06 §13](../../docs/architecture/06-forge.md)): eviction is worth a few points at most; prefetch timing is the bigger lever; the durable win is assurance [RV: D2-A]. The simulator is the right M0 substrate because:

- it is the AlphaEvolve-Borg pattern — a small heuristic with a **fast, exact-replay** evaluator ([R01 (a)](../../docs/research/R01-self-improving-systems.md)): all five online policies over a 960k-request trace run in ≈ 2.6 s [M, Hearth SIMULATOR.md §9];
- it needs **no quiet machine** — replay is deterministic CPU work that runs in daytime, off the measurement windows (DR-023, [06 §6.8](../../docs/architecture/06-forge.md));
- it exposes exactly the deception X4 must handle: Hearth's own simulator "Belady bound" was beaten twice by online policies (0.692 vs 0.697; lru-layer 68.2% vs 63.4%) through warm-start bugs [RV: D3-ii], and depth-4 lookahead raised hit rate 73→86% while decode fell 13.02→10.00 tok/s [M, Hearth policy-default]. F1-sim is where the objective (bytes, not hits) and the plausibility bound (MIN, not Belady-with-prefetch) are proven safe.

**Scratch copy, never the shared tool.** F1-sim imports a **vendored, hash-pinned snapshot** of `hearth/python/hearth/sim/` into X4's scratch space; it never writes to the Hearth clone (read-only at b5d3f14) and never changes the shared simulator. The snapshot hash is pinned in the prereg.

---

## 2. The `hx_policy` shim: one policy, two hosts

The engine and `hearth.sim` must run **the same policy code** so a simulated winner is a real candidate, not a simulator artifact ([06 §13 M4 row](../../docs/architecture/06-forge.md): "engine and `hearth.sim` share the same policy code"; [P4 §9.2]). The shim defines that interface. In Hearth today the policy is C (`hx_store`, `HEARTH_POLICY_LRU/LFU`) and the simulator re-implements it in Python (`cache.py` `_LRU`/`_LFU`/`_Belady`) [M, clone]. F1-sim introduces one policy contract that both call.

**`hx_policy` contract (provisional; the real type is M4's `evolve slot store_evict`, [06 §2.1](../../docs/architecture/06-forge.md)).** A policy is a pure function over a **port view** and a **logical event**, emitting a **hint** the store validates — so no policy can change logits ([06 §2.1](../../docs/architecture/06-forge.md), DR-021). Mirroring the canonical `pick_victim` ([README](../../README.md), [06 §2.1](../../docs/architecture/06-forge.md)):

```
policy view  SlotView { id, pinned: bool, refs: u32, last_use: Tick, uses: u32 }   // no `loading`, no completion state
policy event LogicalEvent { routing_events, logical_tick }                         // the logical stream only
fn pick_victim(slots: &[SlotView], now: Tick) -> Hint<SlotId>                       // eviction
fn prefetch(layer: Layer, view: &StoreView, now: Tick) -> Hint<[ExpertId]>          // prefetch
```

In X4 the shim is realised twice and **differentially checked to be identical**:

- **Simulator side:** a Python adapter that drives the vendored `cache.py` policy interface (`admit`, `admit_last_resort`, `hold`, `release`, `touch`, `tick`) from `pick_victim`/`prefetch`. The existing `run_cache` loop ([clone `cache.py`](../../docs/research/R11-hearth-port-requirements.md)) is the host.
- **Engine side (reserved for M4):** the same `pick_victim`/`prefetch` compiled through the store's C seam. X4 does **not** run the engine; it records that the shim is engine-shaped and defers the engine parity check to M4 ([06 §13](../../docs/architecture/06-forge.md): "counters = replay for every `timing_blind` configuration" is an M4 gate).

**Why a view type, not the raw store:** the view omits `loading` and completion-dependent `refs`, which is exactly what makes a configuration `timing_blind` (§4). A policy that only reads `{id, pinned, last_use, uses}` and `refs` that change only at logical acquire/release points is `timing_blind`; one that reads completion order is not ([06 §5.4](../../docs/architecture/06-forge.md)).

---

## 3. The objective: NVMe bytes/token and stall time, never hit rate

The objective is `minimize(nvme_bytes_per_token, stall_per_token)` ([06 §2.1](../../docs/architecture/06-forge.md)). Hit rate is a **descriptor**, never an objective ([06 §4.2](../../docs/architecture/06-forge.md)), because:

- depth-4 lookahead: hits 73→86%, decode 13.02→10.00 tok/s, because each extra depth added 7–17% NVMe bytes/token on a saturated drive [M, Hearth policy-default]. This is the `hit_rate_objective` tombstone (DECISIONS §4.1, imported in [TOMBSTONES.md](TOMBSTONES.md));
- the simulator exposes both: `Result.bytes_per_token["nvme"]`, `stall`/`nvme` time attribution, and `hit_rate` [M, clone `core.py`/`timing.py`].

F1-sim reads `nvme_bytes_per_token` and the `nvme` (stall) time attribution as the objective; `hit_rate` is logged as a diversity descriptor only, so a candidate that wins on hits but loses on bytes (the lookahead trap) is correctly ranked a loss.

**Bytes vs stall split.** For `timing_blind` configurations, NVMe bytes/token is a **deterministic count** (one replay establishes it, no e-value needed, [06 §5.4, §6.6](../../docs/architecture/06-forge.md)); stall time is the simulator's `est` time model and may only **rank**, never gate ([06 §5.3](../../docs/architecture/06-forge.md), [02 §13.2](../../docs/architecture/02-compute.md)). So F1-sim's benefit claim is on **bytes/token** (sound, deterministic); stall time steers the search.

---

## 4. Plausibility: the MIN-bytes oracle, validated against brute-force OPT

A result that beats a sound bound is a bug or a hack and is **quarantined** (IF-6, [06 §5.3](../../docs/architecture/06-forge.md)). The bound must itself be `validated`, because Hearth's Belady bound was beaten twice by warm-start bugs [RV: D3-ii]. F1-sim uses the right bound for each configuration:

- **Eviction-only (no prefetch):** relaxed Belady bounds the **hit rate** ([clone `cache.py` `_Belady`](../../docs/research/R11-hearth-port-requirements.md)). But the F1-sim objective is bytes, so the aligned bound is the **MIN-bytes oracle**: MIN fetches × slab size, the minimum bytes any policy must read ([06 §5.3](../../docs/architecture/06-forge.md), [RV: D2-B]). At 2 GiB the MIN floor is ≈ 193 MB/token against 402 today [inference, RV: D2-B].
- **With prefetch:** **Belady is not a bound** ([RV: §5](../../docs/research/revisited-ideas.md), [06 §5.3](../../docs/architecture/06-forge.md), [clone SIMULATOR.md §3.2](../../docs/research/R11-hearth-port-requirements.md): "`belady` is not a bound with prefetch"). Prefetching policies get **MIN-type bounds only**: MIN fetches × slab size ÷ the `phys` NVMe rate (7.877 GB/s PCIe 4.0 x4) [RV: D2-B, R08]. These pruned nothing in the pilot [RV: D3-ii], which is accepted.

**Validation before use (both conditions of [06 §5.3](../../docs/architecture/06-forge.md)):**

1. **Tier.** The bound uses `phys` peaks (7.877 GB/s NVMe, 96 GB/s DRAM) or audited `emp` peaks entered as `emp_bound = min(phys, max observed × (1+h))`, h ≥ CI + 5% ([02 §13.2](../../docs/architecture/02-compute.md), [MEASUREMENT-SERVICE.md §6](MEASUREMENT-SERVICE.md)). `est` terms (the simulator's time model) may only rank.
2. **Grade ≥ validated.** The MIN-bytes oracle's computation is graded `validated` only after: an **exhaustive check on small instances** against brute-force OPT (the relaxed-problem optimum computed by exhaustive search, as Hearth's own tests do for Belady on ≤ 80 random small schedules [M, clone `test_sim.py`]); **property tests**; and an **independent second implementation run differentially** ([06 §5.3](../../docs/architecture/06-forge.md) condition 2). F1-sim writes that second implementation (a brute-force MIN over small traces) and requires byte-exact agreement before the oracle may quarantine anything.

**"Hearth's own Belady bounds were beaten twice by bugs"** (ROADMAP §3.5) is the acceptance test the validation must survive: F1-sim re-derives the two historical counterexamples (gen-1 Belady 0.692 vs LRU 0.697; gen-2 lru-layer 68.2% vs warm-started Belady 63.4%) and confirms the **corrected** Belady (which excludes VRAM slabs from its warm start, `cache.py` lines 524–545 [M, clone b5d3f14]) is never beaten on them. A bound that can be beaten on a known counterexample is not `validated` and may not quarantine ([06 §5.3](../../docs/architecture/06-forge.md): a wrong bound fails both ways).

### 4.1 The simulator's own byte counter is checked too (new in revision 2)

The MIN floor only catches results that are *too good to be possible*. A policy that exploits a modelling error in the vendored simulator — a byte path the simulator forgets to charge — while staying above MIN would pass every other F1-sim stage and be reported as a SIMULATED benefit. The two historical Belady bugs were simulator flaws of exactly this kind. So, for every `timing_blind` configuration, **before any benefit is recorded** a candidate's NVMe bytes/token must equal an **independent second byte counter**: a minimal cache replay, written separately from the vendored simulator (it is the brute-force replay that validates MIN in §4), that takes the access sequence and the policy's recorded decisions (admissions, victims, prefetch issues and cancellations) and counts every slab read × slab bytes. Any mismatch quarantines the candidate *and* flags the simulator path for audit ([06 §5.3](../../docs/architecture/06-forge.md) audit outcomes). The planted a32 ([HACK-SUITE.md](HACK-SUITE.md)) leaves one byte path uncounted in a scratch copy of the simulator and must be caught here. Timing-dependent configurations have no deterministic byte count and get no such check; their results stay `est`-tier rankings.

---

## 5. Replay pruning only for `timing_blind` policies

INV-DET-1 makes the routing trace policy-independent, so one trace conditions every lossless candidate's bounds ([06 §5.4](../../docs/architecture/06-forge.md), [RV: D3-ii]). Exact **byte counts** also need byte traffic to be timing-independent:

- a configuration is **`timing_blind`** when every byte-moving decision reads only the logical event stream (routing events, logical ticks, fields derived from them); completion order, queue depth and in-flight state are excluded ([06 §5.4](../../docs/architecture/06-forge.md)). The property is derived from the port **view types** (§2): `{id, pinned, last_use, uses}` qualifies; a view with `loading` or completion-dependent `refs` does not;
- **prune rule:** `LB ≥ (1 − mde)·UCB_α(incumbent)`, emitting a content-addressed `PruneCert` ([06 §5.4](../../docs/architecture/06-forge.md)); pruned candidates stay in the archive as parents (a false prune would delete a stepping stone permanently);
- **audit:** in the Forge a fraction ρ of pruned candidates is re-measured; 0 violations in n audits bounds the violation rate at 3/n (rule of three) [RV: D3-ii]. **In the X4 pilot reproduction the audit is exhaustive [target]:** every candidate the 144-grid prune removes is re-simulated in full (simulation is cheap daytime CPU), so "zero audit violations" is an exact count on the grid; at the original pilot's 66% joint prune that is ≈ 95 candidates [D: 0.66 × 144], and 0 violations bound the rate beyond the grid at 3/95 ≈ 3.2% [D]. X4 reproduces the prune pilot with **zero audit violations** (ROADMAP §3.5, §8 M0 readiness);
- **timing-dependent configurations** (completion-driven prefetch cancellation, the bigger lever [RV: D2-A]) get **MIN-type bounds only**, which pruned nothing; those candidates go through simulator ranking and measurement unpruned ([06 §5.4](../../docs/architecture/06-forge.md)).

**Pilot reproduction (ROADMAP §3.5, §8 readiness).** The original pilot on the 144-candidate grid (6 eviction × 6 prefetch × {1,2,4,8} GiB) pruned, with replayed bytes at phys peaks, **41/32/26/16%** per cache size and **66% jointly**; physics-only (policy-agnostic) rooflines pruned **0 of 144** [RV: D3-ii]. F1-sim reproduces these fractions on the vendored simulator with **zero bound violations** — that is the `physics_only_pruning` tombstone's survivor and the `D3-ii` evidence ([TOMBSTONES.md](TOMBSTONES.md)). The pilot ran on Hearth's real 5-task Qwen3 trace stand-in; the real-engine prune fraction will likely be lower ([06 §5.4](../../docs/architecture/06-forge.md)) and is an M4 measurement.

---

## 6. The cascade on `hearth.sim`

F1-sim runs the full evaluation cascade ([06 §3](../../docs/architecture/06-forge.md)) with the measurement stages replaced by simulation (every output SIMULATED):

| Stage | In F1-sim |
|---|---|
| 0 dedup | content hash of the normalised policy; decision-trace identity for `timing_blind` policies (identical decisions on every trace ⇒ identical bytes, [06 §4.4](../../docs/architecture/06-forge.md)) |
| 1 check | policy reads only the view type; `timing_blind` derived from the view; a policy that reads completion state is flagged timing-dependent, not rejected |
| 2 prune | §5 replay prune, `timing_blind` only; `PruneCert` emitted |
| 3 correctness | hint validated by the store model: no policy changes logits (bit-identical decode output on the trace) |
| 4 sim-rank | `hearth.sim` time model, `est` tier — ranks, never gates |
| 5/6 "measurement" | **simulated** bytes/token (deterministic for `timing_blind`) and stall; no quiet machine, no α; for `timing_blind`, bytes/token must equal the independent second counter (§4.1) before a benefit is recorded |
| 7 plausibility | §4 MIN-bytes oracle (validated); beating it ⇒ quarantine |
| 8 e-gate | not needed for the bytes route (deterministic count); stall-time superiority would use the e-process, but F1-sim's benefit claim is on bytes |
| 9 archive | niche elite (cache × prefetch × model) or tombstone with auto-derived triggers ([TOMBSTONES.md](TOMBSTONES.md)) |

No promotion: grants arrive at M6 ([06 §2](../../docs/architecture/06-forge.md)); F1-sim records ledger facts only.

---

## 7. The M0 readiness and benefit criteria, made precise

ROADMAP §8's M0 Forge row has a **readiness** part and a **benefit** part. Here each is made decidable; the MDE and the held-out traces are pre-registered.

### 7.1 Readiness (all required)
- **σ_d published per run type and niche** — produced by [MEASUREMENT-SERVICE.md §10](MEASUREMENT-SERVICE.md) from the A/A sessions. (This is a measurement-service deliverable; F1-sim consumes it to size any stall-time e-test.)
- **The [06 §7.6](../../docs/architecture/06-forge.md) acceptance tests pass** — the tombstone firing tests ([TOMBSTONES.md §4](TOMBSTONES.md)): the lookahead tombstone fires iff `nvme_read_gbps > 12.0 || drives ≥ 2 || tier_exists(vram)`; ADR-0004 fires on the recorded LRU-vs-LFU traces with niche-scoped verdicts; subsumption and Kleene firing behave as specified.
- **The prune pilot is reproduced with zero bound violations** — §5: the 41/32/26/16% / 66% fractions reproduced on the vendored simulator with 0 audit violations and the MIN oracle validated against brute-force OPT (§4).

### 7.2 Benefit — the MDE and the sealed held-out traces (rewritten in revision 2)
- **Claim (the gate):** a searched policy needs **≥ 10% fewer simulated NVMe bytes/token than LRU** [target] in the **primary niche** on **sealed held-out traces** (ROADMAP §8). Bytes/token is the only gated quantity; stall time is **descriptive** (it is `est`-tier and may only rank). Revision 1's "bytes/token **or** stall time" disjunction is withdrawn.
- **Baseline = LRU** (the engine's named baseline, ADR-0004) — *not* the LFU default, because the claim is "a searched policy beats LRU", and LRU is the policy with a clean cyclic-pathology failure mode the search can exploit.
- **Primary niche [target]: 1 GiB cache, prefetch off.** Grounding: on the real Qwen3 trace (simulated), LFU 0.9 already beats LRU at 2–4 GiB (62.6% vs 60.5%, 82.8% vs 82.4% hit rate) [M, Hearth policy-default], and LRU-per-layer beats global LRU at 1 GiB (46.6% vs 45.0%) — small effects, consistent with the prior that eviction is worth a few points [RV: D2-A]. A 10%-bytes win over **global LRU** is most plausible at 1 GiB without prefetch, where LRU's cyclic pathology bites, and marginal at 8 GiB where LRU already hits 95.9%. The other seven niches (cache {1, 2, 4, 8} GiB × prefetch {off, on}, minus the primary) are **reported descriptively**, never gated; a win there is a hypothesis for M4, not an M0 benefit. Naming one primary niche avoids an "any of eight niches" multiplicity.
- **MDE for stall time:** 5% [target], descriptive and `est`-tier.
- **Which traces are sealed [target].** Revision 1 called two families of `qwen3-30b-a3b-5tasks.hrtr` "sealed held-out". That file is **tracked in the Hearth repository** (`git ls-files` at b5d3f14 lists `docs/results/traces/qwen3-30b-a3b-5tasks.hrtr`; the clone's `origin` is a GitHub URL) [M, 2026-10-16] and readable in the scratch clone, so any proposer can read it and fit a policy to its routing sequence (a10b). Whether the GitHub repository is public was not checked; readability by the proposer is enough. So:
  - **Visible traces:** all five families of the in-repo trace — three for proposing and screening, two as **visible validation**. Results on them are reported, never gated, and labelled "visible".
  - **Sealed held-out traces**, either or both of:
    - (a) **New real traces** recorded with the frozen Hearth build on fresh prompt families, written directly into the Gatekeeper's private store, **never committed** and never on a path a proposer can read ([SANDBOX.md §2.1](SANDBOX.md)); only their hashes are pinned. Recording needs the model on the desktop and machine time (D0-8 host), so its availability is not guaranteed for M0 [known weakness];
    - (b) **Synthetic traces** from the simulator's deterministic Zipf/reuse generator ([clone SIMULATOR.md §2.3](../../docs/research/R11-hearth-port-requirements.md)) over a pre-registered skew grid (Zipf 0–1.4, the range SIMULATOR.md §8.3 sweeps), whose **seeds are drawn after the candidate set is frozen** and committed as a hash only until the benefit run. Synthetic results are labelled SIMULATED(synthetic) and never mixed with real-trace results.
  - **Decision rule [target]:** the benefit gate is evaluated on (a) if (a) exists when the candidate set freezes, else on (b), and the verdict names which. A (b)-only benefit is reported as "SIMULATED(synthetic) benefit".
- **Replay protocol [target].** Each held-out trace (or family) is replayed from a **cold cache**, separately; bytes/token are pooled across held-out traces **token-weighted** (total held-out bytes ÷ total held-out tokens) for the policy and for LRU, and the gate compares the two pooled values. Bytes are deterministic for `timing_blind` configurations, so there is no sampling error within a trace; the uncertainty is which traces were drawn, which the sealed seeds address.
- **If missed (ROADMAP §8):** readiness miss → no M4 campaign until fixed; benefit miss → the policy line enters M4 as a hypothesis with its campaign budget halved. A miss is written as a scoped tombstone with gap attribution ([TOMBSTONES.md](TOMBSTONES.md)).
- **An accepted planted hack is X4's HALT-F** (ROADMAP §3.5), **not** a Forge benefit miss ([06 §13 M0 row](../../docs/architecture/06-forge.md)).

### 7.3 What F1-sim does **not** claim
- **Any F1-sim win is conditional on simulator fidelity until the M4 engine run.** The differential byte counter (§4.1) checks the simulator's arithmetic against a second implementation of the *same model*; it cannot show the model matches the engine. That is the M4 gate "counters = replay for every `timing_blind` configuration" ([06 §13](../../docs/architecture/06-forge.md)).
- No engine measurement, no tok/s, no promotion (all M4/M6).
- No stall-time *certification* (that is `est`-tier and ranks only).
- Bytes/token is the only **sound, deterministic** benefit, and only for `timing_blind` configurations; timing-dependent prefetch is reported SIMULATED with MIN-type bounds that prune nothing, as the prior predicts [RV: D2-A, D3-ii].
