# 06 — The Forge and `mithc revisit`

**Summary.** The Forge is Mithril's permanent, safe improvement loop. Untrusted proposers offer
candidate bodies for declared *slots*. A frozen trusted core (F0) judges each one in order:

1. membership in a *certified space*, or a per-candidate refinement witness;
2. speed, measured with a runtime-owned clock;
3. an anytime-valid statistical gate that spends a project error budget;
4. a physics plausibility gate backed by a *validated* bound;
5. authority.

Every judgment, rejections included, becomes a ledger fact. The archive is a quality-diversity
view over those facts (hardware × shape × model × grade niches, HGM-style clade selection). Every
rejected idea becomes a scoped *tombstone* with a decidable *resurrection trigger*. `mithc revisit`
(plus `--design` for design-level ideas) re-opens an idea when hardware, toolchain, model or
evaluator change.

Two levels run by Edition 1. F1 covers output-preserving artifacts: `timing_only` policies, exact
schedules and lossless layouts (v0: simulator pilot at M0, schedules at M2, live policy engine at
M4; grant-backed campaigns and promotions v1, M6). F1-A is the DGM-proper loop: it evolves the
agents' own card, diagnostics, ranking and scaffolds against a sealed harness, and the genome
includes the reflection prompt and scaffold that propose the next delta, so a better agent is also
a better proposer. A maintainer-run F1-A pilot on card and diagnostics starts at M1 (v0); the full
loop is v1 (M6). Compiler (F2), language (F3) and meta (Fm) levels, and living models, come later
behind triggers. This document also specifies how statistics stay
valid on one shared Windows desktop, how much measurement that desktop can supply, and the minimum
benefit the Forge must show per milestone to keep its funding.

**Contents**
1. Purpose, premises and the size of the prize
2. Forge levels
3. One campaign: the evaluation cascade
4. The archive and selection
5. The measurement service
6. Statistics on a Windows desktop
7. Tombstones, the trigger language and `mithc revisit`
8. Promotion: the Gödel–Darwin rule and standing grants
9. Löb-safe stratification
10. F1-A: the DGM-proper loop
11. F2, F3 and Fm
12. Prompt-injection hygiene for archived text
13. Pre-registered minimum benefit per milestone
14. How this goes further than DGM, HGM, AlphaEvolve, ShinkaEvolve and the AI CUDA Engineer
15. Living models (post-v1)
16. Open questions and reviewer notes

**Conventions.**
- **Status labels** ([ROADMAP.md](../ROADMAP.md) §1 rule 7):
  - **v0**: in the mithc that ports Hearth (M1–M5);
  - **v1**: present by Edition 1 (M6–M7);
  - **later**: planned after M7;
  - **reserved**: in the types and schema but not producible;
  - **by-trigger**: added only when its register trigger fires.
- **Number labels:** *measured*, *simulated*, **[inference]**, **[target]**.
- **Citations:** dossiers [R01], revisit nodes [RV: node], proposals [P4 §8.7]. Hearth sources are
  cited by path.
- **Syntax:** all `.mith` syntax is provisional pending the Surface Lab
  ([05-agent-protocol.md](05-agent-protocol.md)). Ledger facts are shown as `text`; they are data,
  not source.
- **Siblings:** [ARCHITECTURE.md](../ARCHITECTURE.md), [01-language.md](01-language.md),
  [02-compute.md](02-compute.md), [03-trust.md](03-trust.md), [04-toolchain.md](04-toolchain.md),
  [07-hearth-port.md](07-hearth-port.md), [ROADMAP.md](../ROADMAP.md),
  [DECISIONS.md](../DECISIONS.md).

---

## 1. Purpose, premises and the size of the prize

### 1.1 What the Forge is

The Forge is a side system next to the L0–L8 stack, like the Harness. A Forge *supervisor* runs
campaigns configured by `evolve slot` items (§2.1). It is a separate program built by the frozen
bootstrap toolchain. Agents reach the Forge through four existing verbs:

- `mithc bench` (measurement requests);
- `mithc ledger` (archive views, tombstones, grants, `--trust-base`);
- `mithc revisit` (fired triggers);
- `mithc explain` (floors, gap attribution).

**Campaigns are supervisor-only.** There is no campaign verb, and none is needed. Launching,
pausing or stopping a campaign spends α and quiet-machine hours, which only humans replenish (S6,
§9). It is therefore an Owner action on the supervisor's configuration (an `evolve slot` item plus a
grant), not an agent verb. Agents take part through flags on the existing verbs:
- `mithc bench <def> --slot <slot>` submits a candidate body to that slot's cascade. Like every
  `bench`, it is a request; the gate measures.
- `mithc ledger campaign <slot>` is a read-only view of the campaign's archive, queue, budget and
  tombstones.

The F1-A loop (§10) is also run by the supervisor; its proposers are sessions it starts.
[05-agent-protocol.md](05-agent-protocol.md) §11 lists both flags in its verb table.

The Forge rests on the decomposition stated normatively in [03-trust.md](03-trust.md) (N1): **prove
the space, measure the candidate.**

- *Soundness* of a space is trusted and re-checked per build on the binary. It means any candidate
  the check accepts preserves outputs.
- *Completeness-for-members* is untrusted and only tested. It means every legitimate member
  passes [P2 §5.3].

Correctness for the largest optimisation classes therefore costs a decidable check instead of a
proof per candidate. "Is it faster here?" is left to statistics with a budgeted error rate. This is
the tractable Gödel machine [RV: §6, RV: S1].

### 1.2 Premises from evidence

1. **The archive matters more than self-modification.** Removing DGM's archive cut SWE-bench from
   50.0% to 23.0%. Removing self-modification cut it only to 39.0% [R01].
2. **Clade statistics beat scores.** HGM's clade-metaproductivity estimate correlates 0.778 with
   empirical CMP, against 0.285 for DGM's scheme. HGM used 517 vs 1231 CPU-hours on SWE-Verified-60,
   and 347 vs 2385 on Polyglot [R01].
3. **Evaluators break.**
   - DGM faked tool logs and deleted hallucination markers [R01].
   - 82 of 250 CUDA-L1 kernels (32.8%) used unwatched streams [R01].
   - o3 and other frontier models hacked 30.4% of RE-Bench runs, all hack classes together [R01].
   - The AI CUDA Engineer's aggregate fell from 3.13x to 1.49x [R05].
   - AlphaEvolve exploited a leaky verifier (Tao et al.) [R01].
   - Hearth's golden gate was bypassed via symlinks, case twins and 8.3 names [RV: D2-E].
4. **Ideas lose for contingent reasons and come back** [R02]. Hearth's ADR-0004 chose decayed LFU by
   argument. Trace replay later showed LRU beating it by 8–13 hit-rate points (simulated) [R01].
   Engine measurement on real Qwen3-30B-A3B then found LFU 0.995 the worst policy at every cache
   size, with the winner depending on the niche (measured) [R02].
5. **LLMs propose well but judge badly.** The novelty advantage of LLM ideas vanished once they were
   executed [R02].
6. **Measurement is the scarce resource.** In a simulated pilot, replay-conditioned bounds pruned
   16–41% per cache size (66% joint). Physics-only rooflines pruned 0 of 144 [RV: D3-ii].
7. **Obvious objectives deceive.** Depth-4 lookahead raised Hearth's hit rate from 73% to 86% and cut
   decode from 13.0 to 10.0 tok/s (measured) (Hearth `docs/results/policy-default.md`).
8. **DGM's gains were scaffold gains, and they decay.** The gains were string-replacement editing,
   line-range viewing, retries and summarisation. Transfer to a stronger model added about 1.2
   points on Polyglot, and SICA's scaffold made o3-mini worse on AIME and GPQA [R01].

### 1.3 The size of the prize, stated before any search

- **CPU ceiling.** Qwen3-30B-A3B lossless tops out at ≈ 34 tok/s at 77 GB/s of measured DRAM
  bandwidth. Hearth reaches 19–22 tok/s (measured, noisy). That is about 1.5x honest CPU headroom
  for all work combined [R08].
- **Policies.**
  - Eviction is worth a few points at most.
  - Prefetch timing is the bigger lever.
  - The durable win is assurance: the mirror and FP-environment holes get closed
    [inference, RV: D2-A].
- **MIN bytes floor.** At 2 GiB the floor is about 193 MB/token against 402 today [inference,
  low-medium, RV: D2-B]. It serves as an oracle and a stopping rule, not a target.
- **Schedules pay on compute-bound paths.** The attention value pass runs at 18 GMAC/s portable
  against 94 GMAC/s for a bit-identical AVX-512 prototype [R11]. Prefill tiling is the other such
  path. Decode GEMV sits near the bandwidth roof [R08].
- **GPU placement** is the largest lossless lever (simulated 3.6–4.8x in-RAM MoE [G03]). It is
  owner-gated (DR-022), so it is **later**.
- **Honesty rules.**
  - Claims above a sound ceiling are quarantined (§5.3).
  - Benefit reports state whether the change was writable by hand in C. Most are. The claim is
    cheaper, safer discovery.

---

## 2. Forge levels

| Level | Status | What may change | Correctness basis | Fitness | Promoted by |
|---|---|---|---|---|---|
| **F0** trusted core | v0, frozen | Nothing: no Forge write capability to checkers, evaluator, measurement service, semantics table, specs, gates, ledger kernel | Human change, independent review, adversarial suites | n/a | Owner-signed ADR (AUTHORITY) |
| **F1** artifacts | v0: simulator pilot at M0, schedules at M2 (ledger facts), live policy engine at M4. Grant-backed campaigns and promotions v1 (M6) | `timing_only` policies, exact schedules, lossless layouts; placements **by-trigger** (enter F1 as F1-place only after the DR-022 gate, ROADMAP §8 M7) | Space soundness re-checked per build (binary confinement; T1 on the emitted object; round-trip), or a per-candidate `refines` witness. Tests never suffice for exact slots (DR-021) | Time/token, bytes/token by tier, stall/token; e-values | Profile: standing grant (DR-015). Default: Owner ADR |
| **F1-A** agent interface | Pilot v0 (M1): card and diagnostics only. Full loop v1 (M6) | Card atoms, diagnostic templates, hole/pack ranking, agent scaffolds; the loop's own reflection prompt and scaffold (scored only through descendants, §10) | No output semantics; sealed harness owns the oracle | VP@1 on the rotating confirmation suite, CABW (co-primary), tokens per verified pass | Pilot: maintainer review. Full: Gatekeeper e-gate on its own α budget, then maintainer review |
| **F2** compiler | later (after the port, DR-016) | Heuristic hooks, rewrite rules, cost models | Heuristics choose among certified rewrites; rules carry obligations; translation validation in CI | Held-out shapes on two microarchitectures | Owner ADR |
| **F3** language/stdlib | later (edition 1 at M7) | Grammar, semantics, stdlib signatures | Semantics diff + `mithi` patch + corpus-preserving migration, archive included | Harness vs all control arms | Owner ADR, always |
| **Fm** meta | later, by-trigger | Selection policy, budget split, revisit priority model (§7.4) | Counterfactual replay, then a capped shadow run | Archive productivity per quiet-machine hour | Owner |

Proposers, their prompts and the mutation operators are not a level. They cannot accept anything,
so they evolve freely under S4 (§9) and never need promotion. Fm holds only the parts that allocate
scarce, human-replenished resources: which candidates and tombstones get measured, and how the
budget is split.

### 2.1 F1 slots and the three v0 spaces

A **slot** generalises AlphaEvolve's EVOLVE-BLOCK into a typed `evolve slot` item (contextual
keyword, v0, M4; F1 campaigns at M6) [R01, P4 §8.2]. It freezes a signature, effect row, space,
objective, niches, bounds, holdout and promotion rule. Only candidate bodies vary.

```mith
/// A declared evolvable site (syntax provisional). The incumbent is the canonical pick_victim.
evolve slot store_evict for pick_victim in space timing_only {
    seed        pick_victim;
    objective   minimize(nvme_bytes_per_token, stall_per_token);   // never hit rate
    niches      cache_gib in [1, 2, 4, 8], model in [qwen3_30b_a3b], storage in [nvme_x1];
    plausible   oracle::min_bytes(trace) tier phys;   // quarantine bound: must be graded validated
    prune       replay(trace) tier phys;              // admitted only for timing_blind configurations
    holdout     traces::sealed("qwen3-30b-a3b/held/*");
    promote     profile by grant(store_policies);     // DR-015; a default needs an Owner ADR
}
```

The spaces are specified in [02-compute.md](02-compute.md) and certified in
[03-trust.md](03-trust.md). The Forge relies on three of them: exact schedules and lossless layouts
are v0 (M2), `timing_only` policies v0 (M4).

- **`timing_only` policies.**
  - *Certificate.* The store-core certificate O1–O5 covers hint validation, slab race freedom,
    arrival-order confluence, lossless content-hashed tiers and liveness. It is graded `validated`
    (bounded model check, chaos suite, 100% core-mutant kill) until mechanised (DR-010).
  - *Per-candidate check.* Binary confinement: RDTSC/RDTSCP/RDPMC/CPUID/LDMXCSR/FLDCW, syscalls and
    indirect calls are banned; stores go only to the state block or stack; fuel is bounded. Its
    grade follows [03-trust.md](03-trust.md) §3.2: effective `validated(partition)` from table
    premises; for `confined(S)`, `validated(bounded)` via the store-core theorem; code floor
    `tested`, printed, not met.
  - *Traps.* A trapping policy falls back to the default policy ([01-language.md](01-language.md)).
    The trap is measured as the fallback, so it cannot win, and it counts as a strike.
  - *Size.* Hearth's policy surface is under 60 lines [RV: D2-A].
- **Exact schedules.**
  - Primitive proofs give completeness only. Per-build T1 on the emitted object gives soundness
    [P2 §5.3].
  - A variant that fails to lift or match drops to `tested` and is not dispatched in release
    (DR-008).
- **Lossless layouts.** Derived pack/unpack must be a bijection, checked by round trip per
  instance.

A candidate outside every space is still admissible if it carries a full `refines` witness. Spaces
are deliberately incomplete; by Rice's theorem some true improvements fall outside them.
Incompleteness is accepted. Unsoundness is not.

Two lanes stay outside v0 and v1:
- **Placements** are **by-trigger**: they enter F1 (F1-place) only after the DR-022 GPU gate (ROADMAP §8 M7).
- **The lossy lane** (`approx`: lower-bit cold experts, overlays) is **reserved**. It needs quality
  gates and opt-in, and it is never a default (DR-015).

---

## 3. One campaign: the evaluation cascade

```text
  PROPOSERS (untrusted Builders)                 F0  (frozen; no Forge write capability)
  frontier agents · CMA-ME knobs · e-graph       ┌──────────────────────────────────────┐
        │ body + provenance                      │ binary confinement · T1/T2           │
        ▼                                        │ replay engine · bound library        │
  ┌──────────────────────────────┐   requests    │ measurement service · gate · α ledger│
  │ CASCADE 0 dedup · 1 check ·  │──────────────▶│ ledger kernel (sign, invalidate)     │
  │ 2 prune · 3 correctness ·    │◀──────────────│                                      │
  │ 4 sim-rank · 5 screen ·      │ signed facts  └──────────────────────────────────────┘
  │ 6 confirm · 7 plausible ·    │
  │ 8 e-gate · 9 archive         │
  └──────────────────────────────┘
        ▼ every outcome is a ledger fact
  ARCHIVE VIEW (niches × clades × tombstones) ──▶ selection ──▶ proposers
        └──▶ PROMOTION: grant → opt-in profile (mith.lock) | Owner ADR → default
```

| # | Stage | Cost | Rejects | Quiet machine | Spends α |
|---|---|---|---|---|---|
| 0 | Normalise; deduplicate (§4.4) | ~free | Duplicates | no | no |
| 1 | Parse, type, effect, space membership; binary confinement | ms | Hack classes; out-of-space bodies | no | no |
| 2 | Sound replay prune, `timing_blind` only (§5.4); emits `PruneCert` | ~1 s (0.9 s simulated) [RV: D3-ii] | Bound ≥ (1 − mde)·UCB(incumbent) | no | no |
| 3 | Correctness: T1 on object, T2, round-trip or `refines`; "unknown" = reject | ms–s | Non-refining | no | no |
| 4 | Simulator ranking, same policy code as the engine, `est` tier | s | Nothing; reorders | no | no |
| 5 | Screening measurement | s–min | Upper bound below MDE (§6.4) | yes | no |
| 6 | Confirmatory measurement: fresh samples, interleaved blocks, held-out traces | min–h | Not better | yes | yes, on entry (§6.5) |
| 7 | Plausibility against validated bounds (§5.3) | ms | → quarantine | no | — |
| 8 | E-gate at the slot threshold | — | Noisy claims | — | — |
| 9 | Archive: elite, or tombstone with auto-derived triggers (§7) | — | — | — | — |
| 10 | Promotion: grant or Owner ADR | human for defaults | — | — | — |

Four rules apply at every stage.
- Failing a stage stops spending [R01].
- Pruned and rejected candidates stay in the archive as parents, because a false prune would delete
  a stepping stone permanently.
- A fraction ρ of pruned candidates is re-measured. With zero violations in *n* audits, the
  violation rate is at most 3/*n* at 95% (rule of three) [RV: D3-ii].
- For exact schedules, T1 on the emitted object precedes all measurement.

---

## 4. The archive and selection

### 4.1 The archive is a view

The archive is a Fact Plane view over the ledger ([03-trust.md](03-trust.md),
[04-toolchain.md](04-toolchain.md)). Admitted facts are gate-signed files under `.mith/ledger/`.
Raw samples and certificates are content-addressed blobs in the data directory (DR-019).

An entry holds [R01, R02]:
- the normalised content hash, parent edge and diff;
- the space and correctness grade, with the witness hash;
- proposer provenance: principal, role (always Builder), model family, prompt hash;
- evaluator, toolchain, trust-base and machine-profile hashes;
- per-niche, per-trace outcomes;
- compiler-computed behaviour descriptors;
- cost: tokens, CPU-seconds, quiet-machine seconds, α spent;
- the clade id, and every `PruneCert`, quarantine and tombstone that cites the entry.

A changed evaluator or trust base marks dependent scores stale, and they are re-validated lazily
(IF-4). Provenance must support bulk re-scoring, because poisoned benchmarks can survive clean
re-evolution [RV: S1].

### 4.2 Niches (quality-diversity)

- **Niche key:** hardware class (ISA tier, DRAM-bandwidth class, storage class, VRAM) × shape bucket
  (op, dimension buckets, dtype, top-k, batch, working-set/cache ratio) × model family × grade [R02].
- **Descriptors are computed by the compiler**, never self-reported.
  - Bytes/token by tier is the *aligned* descriptor.
  - Arithmetic intensity, vector width, working-set level, spills, fusion depth and determinism
    scope add diversity [R02].
  - Hit rate is a descriptor, never an objective.
- **Tessellation** uses CVT-MAP-Elites, or Dominated Novelty Search when bounds are unknown. A cell
  holds its elite, runners-up, tombstones and lineage [R02].
- **New-niche test (PATA-EC style).** Run the current elites on a new CPU or shape. A familiar rank
  order means reuse; a novel one opens a niche [R02]. **Transfer (POET style)** periodically
  evaluates elites and tombstones across niches.
- **Niche value** `V(niche)` defaults to the niche's share of the declared run configurations (the
  configurations the Owner says are actually run). The Owner may override it per niche
  [inference].

### 4.3 Selection

- **Clade metaproductivity (HGM).** `CMP̂ = clade successes / clade trials`, pooled over all
  descendants' evaluations [R01]. A *success* is a screening estimate that clears the slot's MDE, or
  a new niche elite [inference].
- **Expand vs evaluate are separate decisions** (HGM).
  - Expand when N^α ≥ |tree|, with α = 0.6 (UCB-Air).
  - Thompson-sample over clades to expand, and over individuals to evaluate [R01].
  - "Evaluate" spends one more block on an uncertain candidate. That is the cheap way to resolve
    noise on a measurement-starved machine.
- **Floor.** Every clade keeps a non-zero probability, discounted by 1/(1 + n_children) as in DGM.
  DGM's best lineage passed through regressions [R01].
- **Cross-niche clade credit.** A clade that produces elites in several niches earns credit in all
  of them [inference, P4 §8.6].

### 4.4 Deduplicate before spending

ShinkaEvolve's novelty rejection avoids paying for near-duplicates, but it is approximate [R01].
Mithril rejects duplicates exactly before any spend:

1. **Content hash** of normalised Core (alpha-renamed, canonically formatted).
2. **Canonical schedule form.** Schedules are data, and commutative directives are sorted.
3. **E-graph saturation over the audited exact-rewrite list only**, so equivalence classes are sound.
4. **Object identity.** Exact schedules that emit the same audited object need one measurement.
5. **Decision-trace identity** for `timing_blind` policies. Identical decisions on every trace mean
   identical bytes. Policy CPU cost can still differ, so the entry is marked a *behavioural*
   duplicate and re-measured only if its fuel cost differs [inference].
6. **Embedding novelty rejection** is a soft fallback. It is never a correctness tool.

### 4.5 Proposers and budget split

- **Operators.** AlphaEvolve-style SEARCH/REPLACE confined to slot bodies; CMA-ME emitters for
  continuous knobs (tile size, prefetch distance, decay constants); e-graph rewrites; a bandit over
  proposer models (ShinkaEvolve) [R01, R02].
- **What proposers see:** diagnostics, profiles, `explain` floors and gap attribution, their lineage,
  sanitised tombstones (§12).
- **What they never see:** evaluator code, held-out traces and shapes, reference outputs,
  thresholds. DGM hacked more when its checker was visible [R01].
- **Budget split.** Exploitation, triggered revisits and random audit start at 70/20/10. The split is
  [inference]: R02 found no evidence for any particular one. It is an Fm object. Each slice is
  auditable: the ledger records which queue every measured candidate came from.
- **Local Hearth-hosted proposers** are **by-trigger** (DR-023). They share the 9950X, DDR5 and NVMe
  with measurement. At the measured 19–22 tok/s, decoding a 500-token candidate alone occupies the
  machine for about 23–26 s [inference]. They are never co-scheduled with measurement.

---

## 5. The measurement service

The measurement service is F0; its line budget is tracked in [03-trust.md](03-trust.md). It is built
by the frozen bootstrap toolchain. Candidates run in a separate process under a Windows Job Object or
a WSL2 container, with supervisor-held limits, no network and read-only mounts. An in-process
`mprotect` sandbox is not enough: STOP's improvers disabled their sandbox flag, and the AI Scientist
edited its own time limit [R01].

### 5.1 The contract

| Rule | Mechanism | Hack it closes [R01] |
|---|---|---|
| The runtime owns the clock | No `time` capability; RDTSC/RDTSCP/RDPMC banned in binaries | Timer overwrite and related evaluator hacks (RE-Bench: 30.4% of runs hacked, all classes) |
| All async work is joined before the clock stops | Threads, pool tasks, I/O completions (later GPU streams) | Unwatched streams (CUDA-L1, 32.8%) |
| Poisoned allocations | Pattern-filled fresh buffers, guard pages; candidate runs before any reference | Stale reference via `torch.empty` reuse (METR) |
| Materialised outputs | Outputs are written to evaluator-owned buffers and hashed against the meaning (or, for `timing_only`, the incumbent's logits hash) on every run | Lazy tensors (CUDA-L1) |
| Shapes from evaluator types | Hidden held-out shapes, seeds, traces | Shrunken problems; wrong-shape scoring >1000% (STOP) |
| No undeclared cross-call state | State block reset between measured calls | Address-keyed caching (CUDA-L1) |
| No self-reported bytes | Engine counters and the trusted replay engine | Self-reported metrics |
| Scores name evaluator and profile | A changed evaluator invalidates scores (IF-4) | Persisting poisoned benchmarks [RV: S1] |

Hashing outputs on every run makes each `timing_only` measurement a free test of space soundness.

Warm and cold runs are both supported. A cold run on Windows needs CLFLUSHOPT sweeps or eviction
buffers, because WBINVD is ring 0 and `perf_event_open` does not exist [R08]. Store reads use direct
I/O, so the standby list never holds model bytes between runs.

### 5.2 Machine profile

A **machine-profile hash** covers:
- CPU model, microcode, BIOS and PBO state;
- memory speed and timings. The machine runs above its official DDR5 rating [RV: D3-ii];
- PCIe generation and width, drives and firmware;
- I/O mode, OS build, active power plan, GPU driver.

A mismatch voids every dependent measurement and `PruneCert`.

`mithc profile measure` runs inside the evaluator, so floors rest on this box. It records STREAM per
CCD and all-core, an NVMe request-size × queue-depth grid, and later PCIe H2D/D2H and a VRAM GEMV
[P3 §6]. Reference figures [R08, R11]:
- 77 GB/s DRAM (measured);
- a 64 GB/s per-CCD cap;
- about 7.16 GB/s demand reads on the 990 PRO (measured).

### 5.3 Plausibility quarantine needs a validated bound

A result that beats a sound bound is either a hack or an evaluator bug. It is **quarantined**: held
from promotion, reported to a human and audited (IF-6). It is never silently rejected.

The bound must be trustworthy. Hearth's simulator "Belady bound" was beaten twice by online
policies (Hearth `docs/SIMULATOR.md`) [RV: D3-ii]:
- generation 1: Belady 0.692 against LRU's 0.697;
- generation 2: lru-layer 68.2% against Belady 63.4%, caused by a warm-start error.

A wrong bound fails both ways. Too low, it quarantines real wins; too loose, it waves hacks through.
A bound term may therefore drive *automatic* quarantine only if **two orthogonal conditions** hold:

1. **Tier of the numbers.** Peaks are `phys` (link or DIMM limits, e.g. PCIe 4.0 x4 at 7.877 GB/s)
   or audited `emp`. A measured peak is a lower bound on the attainable roof, so an audited `emp`
   term enters only as `emp_bound = min(phys, max observed peak × (1 + h))`, with h at least the
   measurement CI plus a declared margin (e.g. 5%) ([02-compute.md](02-compute.md) §13.2). A result
   between the bound computed with `emp_bound` and the same bound computed with `phys` is
   **flagged** for audit, not quarantined; pruning uses `emp_bound` with the same margin. `est`
   terms, such as the simulator's time model, may only rank [RV: D3-ii].
2. **Grade of the computation.** The procedure that computes the bound (MIN floor, relaxed Belady,
   windowed AGL stall LP, replay) is graded ≥ `validated`. That takes three things: an exhaustive
   check on small instances (as Hearth's tests now do), property tests, and an independent second
   implementation run differentially.

A bound failing condition 2 raises only an advisory flag. Which bound applies depends on the
configuration:
- relaxed Belady bounds eviction-only hit rates;
- **with prefetching, Belady is not a bound** [RV: §5]. Prefetching policies get MIN-type bounds:
  MIN fetches × slab size ÷ the `phys` NVMe rate [RV: D2-B].

An audit ends one of two ways.
- *Cheat:* a rejection fact, plus a new entry in the planted-hack catalogue.
- *Bound bug:* the bound term is quarantined, and the Fact Plane revokes every dependent `PruneCert`
  and plausibility pass [RV: D3-ii].

### 5.4 Replay-conditioned pruning: `timing_blind` configurations only

INV-DET-1 makes the routing trace policy-independent, so one trace conditions every lossless
candidate's bounds [RV: D3-ii]. Exact *byte counts* also need byte traffic to be timing-independent.
The panel found that every proposal missed this condition.

- **Definition.** A store *configuration* (all hint ports plus core options) is **`timing_blind`**
  when every byte-moving decision reads only the logical event stream: routing events, logical ticks
  and fields derived from them.
  - Excluded inputs: completion order, queue depth, in-flight state.
  - The property is derived from port view types. `{id, pinned, last_use: Tick, uses}` qualifies; a
    view with `loading` or completion-dependent `refs` does not.
  - The core must also do nothing timing-dependent in that configuration, such as cancelling late
    prefetches.
  - Example: the canonical `pick_victim` reads `refs`. With prefetch off, `refs` changes only at
    logical acquire and release points, so that configuration is `timing_blind`. With
    completion-driven prefetch it is not [inference].
- **What it buys.** The trusted replay engine computes exact bytes per tier. The bound is
  LB = max(span, max over resources r of work_r / peak_r), with only `phys` peaks or audited `emp`
  peaks entered as `emp_bound` (§5.3).
  A candidate is pruned when LB ≥ (1 − mde)·UCB_α(incumbent), and a content-addressed `PruneCert` is
  emitted [RV: D3-ii].
- **What timing-dependent configurations get.** Prefetching with completion-driven cancellation (the
  bigger lever [RV: D2-A]) gets **MIN-type bounds only**, which pruned nothing [RV: D3-ii]. Those
  candidates go through simulator ranking and measurement unpruned. Confining a prefetcher's
  reactivity to a declared byte envelope could restore replayability; that is **later**.
- **Standing invariant.** For `timing_blind` configurations, engine byte counters must **equal**
  replay counts on every measured run. A mismatch quarantines replay for that class and revokes its
  `PruneCert`s.
- **Caution.** The pilot's 16–41% included prefetching candidates that are deterministic in the
  simulator but timing-dependent in the engine. The real-engine prune fraction will likely be lower
  [inference] (§13 gates it).
- **Free benefit.** For `timing_blind` configurations, a bytes/token claim is a deterministic count.
  One run whose counters equal the replay establishes it, with no e-value needed.

Expected savings are about f·M·N [inference, RV: D3-ii]. For example, f = 0.3, M = 5 min and
N = 1,000 candidates save about 25 h of quiet-machine time.

---

## 6. Statistics on a Windows desktop

E-processes give anytime-valid evidence only under assumptions a shared desktop breaks: stationary
noise, no drift and a well-specified null. Hearth's load-gated decode medians show the spread
(measured, shared machine; Hearth `docs/results/policy-default.md`):
- 13.02 tok/s ranged 12.86–13.04;
- 17.55 ranged 15.46–17.91;
- 21.16 ranged 17.91–21.31.

So 10–15% outliers sit beside 1–2% spreads. The design below keeps the e-gate valid under such noise.
Harness statistics for F1-A are in [05-agent-protocol.md](05-agent-protocol.md).

### 6.1 Session design

A **session** compares candidate B with the niche incumbent A on one niche, within one quiet window
and one machine profile.

1. **Gate.**
   - The profile hash matches.
   - A quiet window is active (§6.8).
   - The load gate passes. Hearth's current gate waits until 2-second CPU load is below 40% (practice
     on a busy machine). The quiet profile uses a stricter, calibrated threshold [target].
   - Background services are idle (§6.7).
   - NVMe temperature is below threshold, with no large writes in the settle interval.
2. **A/A calibration.** Incumbent-vs-incumbent blocks estimate this session's σ̂. If σ̂ falls outside
   the profile's envelope, the session is void.
3. **Blocks.** A and B run in randomised ABBA or BAAB order, each run in a fresh process with
   identical thread placement.
   - The block statistic is the mean paired log-ratio d = log(T_B/T_A).
   - Log-ratios make effects multiplicative.
   - ABBA cancels linear drift within a block, and random order makes position effects mean-zero
     [inference].
4. **Sentinels.** A/A blocks are inserted at random positions to detect drift [inference].
5. **Post-checks.** Stationarity (§6.3); thermal and background state; bytes = replay for
   `timing_blind` configurations; output identity on every run; plausibility.
6. **Emit** a signed fact:

```text
measurement m:… {                                        // a ledger fact, shown as text
    subject:  candidate h:… vs incumbent h:…   slot store_evict
    niche:    { hw: mp:9950x/…, model: qwen3_30b_a3b, cache_gib: 2 }
    design:   randomised ABBA blocks, n = …, A/A sentinels …, held-out traces sealed h:…
    effect:   clipped mean log-ratio … (clip ±c, outlier blocks scored as losses) : Quantity<Ratio, Measured{mp:9950x/…}>
    report:   unclipped mean log-ratio …   outlier blocks: slow … fast …   tail check: pass
    e_value:  …   null: superiority   alpha_charged: …
    checks:   stationarity pass · output hash == incumbent on every run · bytes == replay
    voided:   … runs (reason: background scan active)
}
```

### 6.2 Nulls and the e-process

- **Superiority**, used for promotion (DR-018: e ≥ 20). H0: E[x] ≥ 0, where x is the clipped,
  loss-scored block statistic defined below. Rejecting H0 shows an improvement (effect < 0); it does
  not show an improvement of at least the MDE.
- **Non-inferiority** with δ = 3%, used for parity gates ([07-hearth-port.md](07-hearth-port.md))
  and for secondary objectives. H0: E[x] ≥ log(1.03). Equality can never be certified, so parity is
  always a non-inferiority claim.
- **The null is composite:** every noise law with mean in the null region.
  - Mithril uses a **betting e-process on clipped block statistics**. Betting martingales are valid
    for every bounded distribution in such a null; a Gaussian likelihood ratio is not [inference].
  - **The clip is symmetric and pre-registered.** Each slot fixes c before collection, from the
    profile's A/A calibration (for example the A/A 99th percentile of |d| [target]). A block with
    |d| > c is an *outlier block*.
  - **Outlier blocks count as losses for the candidate.** Each one is scored +c, whichever arm was
    slow. The 10–15% outliers above look exactly like policy-induced stalls (late prefetch,
    thrashing). Clipping them symmetrically would hide the candidate's worst blocks, and a candidate
    could then show a better clipped mean while its true mean tok/s is worse. Scored as losses, an
    outlier can never help the candidate, and a candidate that causes them pays the full clipped
    loss for each. Environmental outliers that survive the hygiene voids (§6.7) cost a little power;
    validity is unaffected, because the scored statistic is never below the clipped one.
  - **Tail check (mandatory).** A run killed at the slot's pre-registered time cap counts as a slow
    outlier block and a strike. A candidate whose count of slow outlier blocks exceeds the
    pre-registered binomial bound from the A/A outlier rate (one-sided, 1% [target]) is not
    promoted, whatever its e-value. It is tombstoned with the slow tail as the binding factor. This
    only adds rejections, so it spends no α.
  - **The estimand is the clipped mean log-ratio** E[x], with x the clipped, loss-scored block
    statistic. Facts and promotions name it, and they also report the unclipped mean and the
    outlier counts per direction. Every statistical guarantee in this document (§6.5, §8.1) is about
    this pre-registered estimand, not the unclipped mean, which no bounded test on a shared desktop
    can certify [inference].
- **Validity** needs each block's conditional mean to stay in the null region given the past. Under
  drift that holds only because blocks are paired and randomised. This is why interleaving is
  mandatory.
- **Secondary objectives** (stall p99, prefill throughput) must be non-inferior while the primary is
  superior [inference].

### 6.3 Stationarity checks

A session is void if any of the following hold. Its samples are kept but never pooled.
- The A/A sentinel e-process exceeds its own threshold, meaning drift could fake an effect.
- A monotone-trend test on the incumbent's run times exceeds the profile envelope [inference].
- The incumbent's median leaves its calibrated envelope (thermal or boost drift).
- A closing background or temperature check fails.

Void rates are recorded; they feed the second-box trigger (§6.9).

### 6.4 MDE, screening and futility

- **MDE.** Each slot pre-registers a minimum detectable effect, and the prune rule uses the same mde.
- **Screening** (stage 5) is exploratory. It may stop early and rank candidates, but it never
  produces promotion evidence. Its samples are not reused in confirmation, which avoids the winner's
  curse R01 notes in DGM's same-benchmark selection.
- **Futility.** A confirmatory session stops when the upper confidence bound on the effect falls
  below the MDE. The result is a scoped class-S or class-V tombstone, not a global "doesn't work".

### 6.5 Error control is charged per confirmatory test

The promotion rule spends a project error budget [P2 §8.1, 03-trust.md]. A *false promotion* is one
whose true effect on the pre-registered estimand (§6.2) is not an improvement (E[x] ≥ 0).
Improvements smaller than the MDE are not false promotions. The MDE governs screening, futility and
power (§6.4), not the guarantee.

- **Per-test validity.** Under H0, P(E ≥ 1/α_i) ≤ α_i (Ville's inequality). Every guarantee below
  holds only if every test that *could* promote is counted.
- **Charging rule.** α_i is fixed **on entry to stage 6**, whatever the outcome. The threshold is
  max(20, 1/α_i), keeping DR-015's floor. Charging only winners would let many trials launder a
  lucky run. Screening cannot promote, so it spends nothing.
- **A smaller α_i is cheap.** An anytime-valid test stops after about log(1/α_i) divided by the
  per-block growth of evidence. Blocks therefore grow with the logarithm of the threshold: e ≥ 160
  needs about 1.7x the blocks of e ≥ 20, and e ≥ 400 about 2x [inference]. A budget buys more
  science as many tests at small α_i than as a few tests at the floor.
- **Defaults and F1-A: union-bound budgets.** Default dossiers (Owner ADRs) draw on a separate,
  small budget; F1-A promotions draw on their own (§10). Per budget period and slot family,
  Σα_i ≤ α_budget. The guarantee: E[false promotions] ≤ Σα_i ≤ α_budget, and, when α_budget ≤ 1,
  also P(any false promotion) ≤ α_budget.
- **Profiles: online FDR with e-LOND.** Grant-promoted profiles are opt-in, revocable and
  output-preserving, so a false one costs speed, never correctness. Family-wise control is stricter
  than they need. Each grant instead runs an e-LOND stream: online false-discovery-rate control with
  e-values, valid under arbitrary dependence between tests.
  - Test t opens with α_t = min(0.05, q · γ_t · (D + 1)). Here q is the grant's FDR level, γ is a
    pre-registered sequence summing to at most 1, and D counts the grant's promotions so far.
  - Before the first promotion this is the union bound; each promotion loosens later thresholds.
  - Tests that overlap in time use D as known when they open, which is conservative.
  - The guarantee: the expected share of false promotions among the grant's promotions is at most
    q, at every point in the stream [inference].
- **The guarantee is two-tier.** Union-bound α budgets for defaults and F1-A promotions:
  E[false promotions] ≤ Σα_i per period and slot family. e-LOND online FDR ≤ q for grant-promoted
  opt-in per-machine profiles, with test thresholds max(20, 1/α_t) and α_t as above. The specimen
  grant (§8.2) sets q = 0.20 and γ uniform over 40 tests, so its thresholds are 200/(D + 1), never
  below 20. [03-trust.md](03-trust.md) §7.2/§7.5, [ARCHITECTURE.md](../ARCHITECTURE.md) §8.5 and
  its glossary entry, and [DECISIONS.md](../DECISIONS.md) note 2 state the same guarantee.
- **Authority.** Budget sizes, q and γ are **Owner decisions** (S6). A new γ sequence or a refilled
  default budget is a human replenishment.

Reviewer note (resolved): the outline and P2 phrase the guarantee as a probability that a promotion
is not a real improvement *of at least the MDE*. The test as specified (H0: no improvement) supports
neither the MDE clause nor, at useful throughput, a probability. This document states an expectation
(plus a probability when the budget is ≤ 1) for defaults and F1-A, and FDR for profiles; the sibling
documents named above now carry the same two-tier wording.

### 6.6 The measurement-throughput budget

All figures in this section are **[inference]**. Parameters are illustrative until the M0 noise
floor is measured (§13).

- **Blocks.** A fixed-sample one-sided test (α = 0.05, 80% power) needs n ≈ 6.2·σ_d²/δ², where σ_d is
  the block-statistic SD. Anytime validity costs roughly 1.7–2.5x more. Take **n ≈ 12·σ_d²/δ²**, with
  a floor of 6 blocks for the stationarity checks.
- **Time per test** ≈ n × 4·t_run, ignoring calibration, sentinels and settling (all reduce
  throughput).

| σ_d \ δ | 2% | 3% | 5% |
|---|---|---|---|
| 1% | 6 (floor) | 6 (floor) | 6 (floor) |
| 2% | 12 | 6 | 6 |
| 4% | 48 | 22 | 8 |

*Blocks per confirmatory test [inference].*

Worked cases, with an illustrative 8 h window:
- **End-to-end decode, t_run = 2 min** (8-minute blocks):

  | σ_d | δ | Time per test | Tests per night |
  |---|---|---|---|
  | 2% | 2% | 1.6 h | ≈ 5 |
  | 4% | 2% | 6.4 h | ≈ 1 |
  | 2–4% | 5% | 0.8–1.1 h | 7–10 |

- **Microbenchmark, t_run = 10 s** (40-second blocks):

  | σ_d | δ | Time per test | Tests per night |
  |---|---|---|---|
  | 4% | 2% | 32 min | ≈ 15 |
  | 2% | 2% | 8 min | ≈ 60 |

- **Niches multiply.** Four cache sizes cost four tests and four α charges. Under e-LOND each one
  is a test in the grant's stream.
- **Thresholds above 20 cost blocks.** The tables assume e ≥ 20. At a threshold of 200 (§6.5),
  multiply blocks and time by about 1.8.

Six consequences:
1. **σ_d per run type and niche is an M0 deliverable.** No campaign starts without it.
2. **End-to-end confirmation is the scarcest resource.** The cascade, HGM's expand/evaluate split and
   replay pruning exist to protect it.
3. **MDE.** End-to-end slots should declare MDE ≥ 3–5% unless the measured noise is far below these
   illustrations.
4. **Bytes claims bypass statistics** for `timing_blind` configurations (§5.4). That makes the
   "≥ 10% fewer NVMe bytes/token" benefit in §13 cheap to establish.
5. **The night budget binds; α binds softly.** Error control prices tests in blocks, not in a hard
   count (§6.5). Take the specimen grant (§8.2): q = 0.20 and γ uniform over 40 tests, so test
   thresholds are 200/(D + 1), never below 20.
   - The grant supports 40 confirmations. Each costs at most about 1.8x an e ≥ 20 test, and less
     as promotions accrue.
   - At δ = 5% end-to-end that is 1.4–2.0 h per test, or 4–5 per 8 h night, so the grant's 40 tests
     need about 8–10 quiet nights.
   - Microbenchmark confirmations are cheaper still (tens per night).

   The Owner sets the night budget and the error budgets together.
6. **M6 is reachable within budget if the gain exists.** B3 needs one candidate at ≥ 5% tok/s with
   e ≥ 20, or ≥ 10% fewer NVMe bytes/token. The bytes route is a deterministic count for
   `timing_blind` configurations and spends no α (§5.4). On the tok/s route, a test for a true 5%
   effect at σ_d ≤ 4% needs about 14 blocks at e ≥ 200 (under 2 h end-to-end). The specimen grant's
   40 tests therefore cover two campaigns (eviction and prefetch) over four cache sizes, with room for
   several candidates per niche. The binding risk is the prior (§1.3: eviction is worth a few
   points), not the statistics [inference].

### 6.7 Machine hygiene

The service **detects and voids**. It never changes system or security settings; such changes are
Owner decisions recorded in [DECISIONS.md](../DECISIONS.md). These controls are [inference] unless
cited.

| Factor | Control | Void if |
|---|---|---|
| Other load (agents, builds, owner) | Quiet windows, scheduler lock, load gate | Gate fails |
| CCD topology | Single-thread microbenchmarks pinned to one fixed physical core, SMT sibling idle, core id in the fingerprint (per-core boost varies with CPPC preferred cores). End-to-end decode uses production placement across both CCDs (one CCD caps at 64 GB/s [R08]), identical for A and B. The supervisor sleeps on a reserved logical core | Placement differs between A and B |
| Power plan, core parking | Plan GUID is in the profile; a dedicated measurement plan is an Owner choice | GUID differs |
| Boost, PBO, thermal drift | Package temperature and effective clocks recorded at start and end | Out of envelope |
| Defender scans, Search indexer, Windows Update/maintenance | Activity sampled around each block; windows avoid maintenance hours. A scan exclusion for the data directory is an Owner security trade-off | Active during a block |
| NVMe temperature | SMART temperature at start and end; cool-down between NVMe-bound runs | Above threshold |
| NVMe SLC cache and garbage collection | Idle settle after large writes; builds write elsewhere where possible | Large writes within the settle interval |
| OS file cache | Direct I/O; buffered configurations excluded from confirmation unless the Owner grants a privileged standby flush | Buffered without a flush |
| DRAM state | Speed and timings in the profile hash | Mismatch |

### 6.8 Quiet windows

- The Owner declares windows (for example overnight). During a window, the supervisor holds a
  machine-wide lock: no agent sessions, compiles, object audits or local generation (DR-023).
- Daytime work is everything that needs no quiet machine: proposing, checks, T1, replay pruning,
  simulation and dedup. Measurements queue for the next window.
- An unattended Forge on the Owner's machine is an Owner decision. The supervisor yields to
  interactive use at once and voids the running session.

### 6.9 An optional second measurement box

Status **by-trigger**; cost and model are Owner decisions.

- **Trigger:** one disjunction, held in ROADMAP's deferral register as D-22
  ([ROADMAP.md](../ROADMAP.md) §9), so the revisit engine reads one trigger. It fires on any one
  of:
  - A/A or planted-regression calibration fails (§6.1, ROADMAP X4);
  - the confirmatory queue exceeds a declared wait for two consecutive weeks (throughput below
    campaign demand);
  - the parity-gate quiet hours planned in ROADMAP §10 exceed the available windows;
  - quiet windows conflict with the Owner's own use of the machine (D0-8);
  - the void rate exceeds its declared bound [target];
  - F2 starts, which needs two microarchitectures (DR-016).
- **A Zen 5 twin** doubles throughput for existing niches.
- **A different microarchitecture** (for example an AVX2-only client CPU) serves F2's
  generalisation rule but cannot confirm Zen 5 niches.

Either box has its own fingerprint and niches. Elites move between boxes through the new-niche test
(§4.2). A dedicated box removes proposer/measurement contention entirely.

---

## 7. Tombstones, the trigger language and `mithc revisit`

### 7.1 The record

A tombstone is a reject claim with these fields [R02 §B, P4 §8.7]:
- content hash and lineage;
- an **exact reproduction recipe** (source, toolchain hash, flags, seed). This is Go-Explore's
  "return" step, which prevents detachment [R02];
- environment fingerprint, and evidence labelled measured or simulated with its noise controls;
- a **verdict scope**. A verdict without one is a type error, so "doesn't work" cannot be written;
- a **failure class**: H hardware, T tooling, S search, E effort, V evaluation, C composition,
  X scale, F fundamental-under-assumption. F names the assumption, so a format change can still
  revive the idea [R02];
- the binding factor, and the search budget spent against the incumbent's;
- **triggers**, plus a short free-text rationale (untrusted, §12).

```text
tombstone lookahead_depth_4 {                       // a ledger fact, shown as text
    verdict: slower                                 // decode 13.0 -> 10.0 tok/s (measured)
    scope:   { model: qwen3_30b_a3b, drives: 1 (990 PRO), cache_gib: 2..=4 }
    class:   H                                      // hardware-contingent
    revisit_when: nvme_read_gbps > 12.0 || tier_exists(vram) || drives >= 2
    evidence: ledger:sha256:…
}
```

Status: schema **v0** (M3, with the signed ledger). Hearth's past rejections are imported at Stage 0
([07-hearth-port.md](07-hearth-port.md)).

### 7.2 The decidable scope and trigger language

This grammar is **normative** for every trigger: engine tombstones, the **Revisit when** lines of
decision records, and the design tombstones in [DECISIONS.md](../DECISIONS.md), whose §1 lists the
same building blocks.

```text
pred   := pred "||" pred | pred "&&" pred | ("!" | "not") pred | "(" pred ")" | atom
atom   := lin cmp lin                                  -- linear (in)equality over numeric facts
        | fact "in" range                              -- interval, e.g. cache_gib in 2..=4
        | fact "in" set                                -- membership in a finite enumeration
        | fact ("==" | "!=") (const | HASH | ref)      -- enum or hash equality, e.g. evaluator != at_burial.evaluator
        | const "in" fact                              -- element of a set-valued fact, e.g. "in_order" in targets.issue_models
        | fact ("==" | ">=" | "<=") set                -- set equality, superset, subset; {} is the empty set
        | fact                                         -- a boolean fact, e.g. t1.mechanised
        | "has" "(" (kind ":")? name args? ")"         -- primitive, rule, tier, target or elite exists in a finite catalogue
        | "exists" "(" var "in" fact ":" pred ")"      -- bounded: over a snapshot of a finite ledger set; no nesting
        | sugar                                        -- e.g. tier_exists(vram) == has(tier: vram)
set    := "{" (const ("," const)*)? "}"
const  := NUM | NAME | STRING | "true" | "false"       -- the fact's type decides between numeric and enum comparison
fact   := path args? ("." path)*                       -- a named fact, optionally parameterised: harness.vp1_delta(a, b).ci_low;
                                                       -- inside exists, a path may start with the bound var: c.kind
args   := "(" arg ("," arg)* ")"
arg    := (name ":")? (const | fact | "prereg(" key ")")   -- ground when evaluated
lin    := term (("+" | "-") term)*
term   := NUM "*" ref | ref | NUM
ref    := fact
        | "at_burial." fact | "at_burial(" fact ")"    -- burial-snapshot values are constants
        | "scope." fact
        | "prereg(" key ")"                            -- a threshold pre-registered in a signed record; a constant
cmp    := "<" | "<=" | "==" | ">=" | ">"
```

Restrictions:
- facts are unit-typed `Quantity` values, so comparing GB/s with tok/s is a type error;
- no product of two facts;
- the only quantifier is `exists` over a snapshot of a finite ledger set (such as `ledger.certs` or
  `targets`), taken when the trigger is evaluated, and it does not nest;
- no user functions. Parameterised facts (`harness.vp1_delta(a, b).ci_low`,
  `incumbent(store.prefetch).wasted_bytes`) are named facts that the toolchain defines and users
  cannot;
- **three-valued.** A fact with no value, a `prereg` key with no signed record, or a set with no
  snapshot evaluates to `unknown`. Connectives follow Kleene's rules (`unknown || true` is true).
  An `unknown` trigger never fires, but it is reported, so a trigger over a fact nobody measures is
  visible.

Four properties follow.
- **Evaluation** over a ledger snapshot takes time linear in the formula size times the size of the
  largest set an `exists` ranges over. A snapshot makes each `exists` a finite disjunction.
- **Subsumption is decidable on the quantifier-free fragment.** A ⊑ B iff A ⇒ B is valid. With every
  ground parameterised fact, `has(...)` atom and `prereg` value treated as an uninterpreted constant
  of its type, this is a quantifier-free formula in linear arithmetic over finite domains, which SMT
  decides. For `exists`, only a sound syntactic rule applies: `exists(x in S: φ)` ⊑
  `exists(x in S: ψ)` when φ ⊑ ψ. Otherwise subsumption is "not proven" and nothing folds; folding
  is an optimisation, so incompleteness costs only archive size.
- **Folding never loses a fire.** A narrower tombstone with the same class and verdict folds into a
  wider one, and the survivor keeps the folded trigger as a disjunct. Kleene evaluation can leave B
  `unknown` where a two-valued A ⇒ B says it must be true, and the extra disjunct covers that case.
  This answers R02's archive-growth question for the common case [P4 §8.7, inference].
- **Evaluation is incremental.** The Fact Plane indexes triggers by the facts they mention, and an
  event re-evaluates only those. A generic event such as "toolchain changed" does not fire every
  tombstone; it only makes tombstones eligible for the background audit.

**Firing.**
- A trigger is evaluated at burial (or import) and on every event that changes a fact it mentions.
- It *fires* on a transition to true from false **or from `unknown`**.
- A trigger that is already true at burial or import is queued for revisit at once. Hearth's
  imported tombstones (S0) and DECISIONS entries are covered by this rule.
- After a failed revisit the tombstone is **re-based**: its `at_burial` values are replaced by the
  current ones, and derived triggers are re-derived from the new binding term (§7.3). Relative
  triggers then read false and can fire again on a later change. A trigger that is still true after
  re-basing, such as `tier_exists(vram)`, fires again only when a fact it mentions changes value
  while it is true.

**CI check (v0, M3, with the trigger language).** `mithc revisit --design --check` parses every
trigger in [DECISIONS.md](../DECISIONS.md) and every **Revisit when** line against this grammar, and
fails CI on any trigger outside it.

### 7.3 Auto-derived triggers

At burial the cascade knows the binding bound term (from the cost signature,
[02-compute.md](02-compute.md)) and the oracle's gap attribution into eviction, wrong prefetch and
lateness [RV: D2-B]. mithc derives default triggers from them, so nobody has to remember "revisit if"
[P4 §8.7].

| Class | Default trigger template |
|---|---|
| H (resource r, loss ratio ρ) | `capacity(r) >= ρ * at_burial.capacity(r)`, or `has(tier: t)` for a tier removing r from the binding set |
| T (missing primitive p) | `has(primitive: p)` or `has(rule: p)` |
| S (under-searched) | none; a revisit-priority boost proportional to the budget ratio |
| E (effort) | `proposer_model != at_burial.proposer_model` |
| V (evaluation suspect) | `evaluator != at_burial.evaluator` |
| C (missing stepping stone X) | `has(elite: X)` |
| X (scale) | `model.params >= k * at_burial.model.params` |
| F (under assumption A) | `!(A)` |

**A hand-written trigger overrides the derived default in its scope.** The derived formula is
stored beside it as `derived_when` and shown in revisit reports. It fires nothing. When it is true
and the hand-written trigger is not, the tombstone gets a priority boost in the background audit
(§7.4 step 7). At burial the two are compared, and any disagreement is reported so the author can
tighten either one. A tombstone with no hand-written trigger uses the derived one as its trigger.

Example: the lookahead loss was bound by NVMe bytes, with a bytes ratio of 545/402 ≈ 1.36
(measured). The derived default is
`nvme_read_gbps >= 1.36 * at_burial.nvme_read_gbps || has(tier: vram)`, which holds from about
1.36 × 7.16 ≈ 9.7 GB/s. The hand-written trigger in §7.1 says 12.0 GB/s, a second drive or a VRAM
tier, and it is the one that fires. Burial reports the 9.7-vs-12.0 GB/s gap.

### 7.4 The revisit loop

`mithc revisit` (status **v0**, M3) follows R02's loop [R02 §E]:

1. **Event.** A hardware fingerprint, toolchain, primitive set, evaluator, shape catalogue, numeric
   contract (`canon` migration, [03-trust.md](03-trust.md)) or proposer model changes.
2. **Scan.** An incremental Datalog query returns the fired triggers (§7.2).
3. **Priority.** priority(t) = [P_win(t)·V(niche) + β·Novelty(t)] / Cost(t), *sampled, never
   argmaxed*. The default model below is pre-registered, so two implementations rank the same queue
   identically and the 20% revisit slice can be audited. It is an Fm object (§11), so it can be
   tuned later through counterfactual replay.
   - **P_win(t) = mean(Beta_class) × κ(t).** Each failure class keeps a Beta posterior over revival
     success, starting from a pre-registered prior (Beta(1, 4) [target]). A revisit whose variant
     becomes a niche elite counts as a success for its class; any other completed revisit counts as
     a failure.
   - **κ(t)** is the share of the burial loss carried by cost-signature terms whose input facts have
     changed since burial, from gap attribution (eviction, wrong prefetch, lateness, bytes per tier),
     clipped to [0, 1]. A tombstone with no burial cost signature (design tombstones, F1-A atoms)
     uses κ = 1 when its trigger fired. Class S, which has no trigger, uses the under-search ratio
     κ = clip(1 − budget_spent / budget_incumbent, 0, 1).
   - **V(niche)** defaults to the niche's share of declared run configurations (§4.2).
   - **Novelty(t)** is the behaviour-descriptor distance from the tombstone to the nearest current
     elite in its niche, normalised to [0, 1]. Descriptors are compiler-computed (§4.2).
   - **β = 0.1** [target], pre-registered.
   - **Cost(t)** is the expected quiet-machine time from rebuild to confirmation (§6.6), in hours.
   - **Sampling** is a softmax over priorities normalised by the queue maximum, at temperature
     τ = 0.25 [target]: P(t) ∝ exp(priority(t) / (τ · max priority)).
   - An LLM "interestingness" score only breaks exact ties [R02].
4. **Return, then explore.** Rebuild from the recipe and re-measure; only then mutate. Old mithc
   versions stay addressable by hash. If a C compiler version can no longer be obtained, the recipe
   is marked *degraded* and the rebuild is labelled as such [inference].
5. **Cascade** (§3).
6. **Update.** A revived variant becomes a scoped niche elite. A repeated failure narrows or widens
   the scope and re-bases the tombstone (§7.2, Firing). Either outcome updates the class's Beta
   posterior.
7. **Background audit.** A fixed budget slice samples tombstones regardless of triggers, to catch
   unmodelled contingencies [R02]. Tombstones whose derived default holds while their hand-written
   trigger does not (§7.3), and class-S tombstones, are sampled with their priority from step 3;
   the rest are sampled uniformly.
8. **Re-score dormant clades** when the proposer model, hardware or numeric mode changes [R01].

### 7.5 Design-level tombstones: `mithc revisit --design`

The design process shares the compiler's graveyard [R02 §G]. Every rejected idea in
[DECISIONS.md](../DECISIONS.md) is a ledger fact with scope, class and a decidable trigger. Status
**v0** (M3: design graveyard imported, ROADMAP §8).

The canonical records, with class, scope and trigger, live only in
[DECISIONS.md](../DECISIONS.md) §4. This document does not restate them, so the two cannot drift.
Examples of what the engine will revive:

| Rejected idea | DECISIONS entry | What would revive it |
|---|---|---|
| Python-embedded primary surface | `python_primary_surface` (§4.3) | a harness result favouring the embedded form on ≥ 2 families |
| VLIW-style bundling | `vliw_bundling` (§4.1) | an in-order target in the catalogue |
| SPDK bypass as default I/O | `spdk_bypass_default` (§4.1) | I/O CPU cost or an overlapped-read shortfall at link bandwidth |
| Lean replacing SMT | `lean_replacing_smt` (§4.1) | Lean matching Dafny-class vericoding rates |
| Hit rate as objective | `hit_rate_objective` (§4.1) | hit rate ranking tok/s correctly, simulated and measured |

Options that a decision record rejected, such as the direct x86 emitter (DR-009), come back only
through that record's **Revisit when** trigger and are not repeated as tombstones (DECISIONS §1).

A fired design tombstone produces a report, never a change, because design changes are AUTHORITY
operations. Seed-discussion claims enter as hypotheses in a claims ledger and become tombstones only
after execution [R02] ([SEED-REFINEMENT.md](../SEED-REFINEMENT.md)).

### 7.6 Acceptance tests from Hearth's history (M0)

- Replaying Hearth's environment history, the lookahead tombstone fires **iff**
  `tier_exists(vram) || drives >= 2 || nvme_read_gbps > 12.0` becomes true. That is its hand-written
  trigger (§7.1), which overrides the derived default (§7.3). A replay step at 10 GB/s, where only the
  derived default (≈ 9.7 GB/s) holds, must not fire; it must raise the background-audit boost and
  report the disagreement. This matches ROADMAP X4's gate.
- ADR-0004's informal "revisit if traces show a better policy", once encoded, fires on the recorded
  LRU-vs-LFU traces [R02].
- Subsumption merges scopes correctly on a synthetic set with known implications.
- Firing follows §7.2 on a synthetic history: a trigger already true at import is queued at once;
  `unknown` → true fires; a failed revisit re-bases, and a relative trigger fires again on a later
  change.

---

## 8. Promotion: the Gödel–Darwin rule and standing grants

### 8.1 The rule

The rule is normative in [03-trust.md](03-trust.md) §7.1 [P2 §8.1]. The block below is copied
verbatim from there, so section references in its comments are to [03-trust.md](03-trust.md). The
Forge applies the steps in this order, cheapest first:

```text
promote(c, slot, H) <=>
     check_S(c)                                   -- T0 or T1/T2: decidable, cached, no agent-written proof
  && eff(correctness(c)) >= slot.required_grade   -- §3.2: premises and the spec-strength cap included
  && floor(correctness(c)) >= slot.code_floor     -- §3.2: checkers and elaboration
  && E_t(perf(c) vs perf(inc) on H) >= 1/alpha_i  -- anytime-valid e-process; alpha_i charged when the test opens
  && plausible(c, H)                              -- no measurement beats a validated phys/emp floor
  && authority(slot)                              -- standing grant (opt-in profile) or Owner ADR (default)
```

A failure stops spending. Spec strength enters once, as a cap inside the effective grade
([03-trust.md](03-trust.md) §3.2); there is no separate strength conjunct. In this document's terms,
the e-process is the confirmatory test of §6.5 (α_i ≤ 0.05, fixed on entry to stage 6), `plausible`
is §5.3's gate, and `authority` is §8.2.

Two guarantees hold relative to the declared trust base:
- every promoted exact-slot candidate is bit-identical to its meaning or fallback;
- false promotions are bounded on the pre-registered estimand, the clipped mean log-ratio (§6.2). A
  false promotion is one whose true effect is not an improvement (E[x] ≥ 0); smaller-than-MDE
  improvements do not count (§6.5). The bound is two-tier (§6.5):
  - **Defaults and F1-A promotions** (union-bound α budgets): E[false promotions] ≤ Σα_i per period
    and slot family, and when Σα_i ≤ 1, so is the probability of any.
  - **Grant-promoted opt-in per-machine profiles** (e-LOND): online FDR ≤ q per grant, so the
    expected share of false promotions among the grant's promotions is at most q (q = 0.20 in the
    specimen grant, thresholds as in §6.5).

### 8.2 Standing grants (DR-015)

A **grant** is an AUTHORITY fact signed with the Owner key. It is standing, scoped, expiring and
revocable, and it auto-promotes output-preserving winners into **opt-in per-machine profiles**
pinned in `mith.lock`. Key management is in [03-trust.md](03-trust.md).

```text
grant store_policies {                                  // AUTHORITY fact, Owner-signed, shown as text
    space:    timing_only
    slots:    { store_evict, store_prefetch }
    target:   profile(fingerprint: mp:9950x/…)          // opt-in, per machine, pinned in mith.lock
    niches:   { model: qwen3_30b_a3b, cache_gib: 1..=8 }
    require:  e_value >= 1/alpha_t && plausibility == pass && spec == admitted && tail_check == pass
    error:    e_lond(q: 0.20, gamma: uniform(40))      // alpha_t = min(0.05, q * gamma_t * (promotions + 1)) [target]
    expires:  2027-04-01
}
```

The specimen's first test needs e ≥ 200; each promotion lowers later thresholds, never below 20.
Its 40 tests are the grant's whole error budget; a new γ sequence needs a new grant (§6.5, §6.6).

- **A grant cannot:**
  - change a shipped default;
  - touch `approx`, which is never a default;
  - cover a slot whose plausibility bound is not `validated`;
  - extend itself.
- **Defaults** need an Owner-signed ADR with the dossier attached. This includes `timing_only`
  defaults, which are ADR-0004-class (DR-015). A slot may demand a stricter threshold than e ≥ 20.
- **Profiles are opt-in.** Builds use defaults unless the user selects the profile. The selector
  picks per niche at load time.
- **F1-A artifacts** are promoted by maintainer review after the Gatekeeper's e-gate on the rotating
  confirmation suite, which spends F1-A's own α budget (§10). Grants do not cover them.

### 8.3 Forge invariants (release gates)

The invariants follow [P4 §8.13].
- **IF-1** No promotion without an F0-signed ledger fact.
- **IF-2** No Forge process holds a write capability to an F0 or sealed object.
- **IF-3** Every promotion is reversible: the previous selection stays addressable, and rollback is
  one AUTHORITY fact.
- **IF-4** Every score names its evaluator and machine-profile hashes. A changed evaluator
  invalidates the score.
- **IF-5** Every planted hack is rejected no later than its documented stage. The catalogue is
  written by the Adversary role, not the Forge's authors. This answers the circularity objection,
  and bounty-found exploits keep extending it ([03-trust.md](03-trust.md)).
- **IF-6** A score beating a validated bound is quarantined and reported.
- **IF-7** An asynchronous overseer flags sudden score jumps for human review [R01].

---

## 9. Löb-safe stratification

DGM and HGM keep their outer loop fixed [R01]. Mithril lets parts of it change under six rules
[P4 §8.10, RV: S1]:

- **S1, no self-judging.** An artifact at level *k* is evaluated only by an evaluator built from F0
  plus promoted artifacts at a pinned snapshot. That evaluator contains no unpromoted artifact of
  level ≥ *k* and nothing from the artifact's own clade.
- **S2, frozen judges.** F0 is built by the frozen bootstrap. Updating the bootstrap is a human F0
  change and requires diverse double compilation [R01].
- **S3, monotone strictness.** Autonomous changes to checker-like components (lints, plausibility
  thresholds, allowlists) may only strengthen them.
- **S4, free proposers.** Proposers, their prompts and the mutation operators evolve freely, because
  they cannot accept anything. Changes to them need no promotion. In F1-A the proposer's own
  reflection prompt and scaffold are genome atoms (§10). They are scored only through the
  downstream gain of their descendants, never by themselves, so S1 still holds. Fm covers only
  selection and budget allocation (§2).
- **S5, separation of powers.** Specs, gates, holdouts and mutant pools are Author- or
  Gatekeeper-owned.
- **S6, budgeted honesty.** α and quiet-machine hours are replenished only by humans.

**S3, honestly.** P4 checks S3 by archive replay: new accept set ⊆ old accept set. A judge noted
that over a finite archive this is a test, not a proof. Mithril splits S3 in two.

1. **Strengthening-only edit forms are monotone by construction**, graded `proof` by a syntactic
   check. The forms are:
   - add a reject rule (accept′ = accept ∧ ¬r);
   - move a threshold in its declared strict direction;
   - remove an accept exception;
   - shrink an allowlist or capability set.

   accept′ ⊆ accept then holds for *all* inputs.
2. **Any other edit is a human F0 change.** Archive replay still runs on every S3 change. It reports
   the liveness cost (archived accepts that become rejects) and gives a `tested` guard against bugs
   in the edit machinery.

A new trusted core v(n+1) is admitted by humans. Its rule-soundness evidence (Z3 FPA or exhaustive
binary32 for T1 rewrites, DR-010) is checked by v(n)'s rule gate and by differential runs on the
planted corpus.

---

## 10. F1-A: the DGM-proper loop

DGM's measured gains came from its own scaffold: editing tools, viewing, retries, summarisation
[R01]. F1-A evolves that layer *for writing Mithril*, under F1's integrity rules. It is the
recursive loop the panel found missing in every proposal.

**Status.**
- **Pilot, v0 (M1–M5).** GEPA-style deltas to card atoms and diagnostic templates only.
  - Deltas are proposed and screened on the card-iteration and screening items only, never the
    held-out set, so DR-017's kills stay clean.
  - Promotion is an ordinary maintainer card edit under [05-agent-protocol.md](05-agent-protocol.md)
    §2: contamination check, then the screening subset. There is no α budget and no promotion claim;
    the pilot proposes and the maintainer decides.
  - It is the remedy [07-hearth-port.md](07-hearth-port.md) §5 names for a failed comprehension
    precondition. The precondition is then re-checked on items the pilot never saw.
  - Its dollar budget comes out of M1's card-iteration work. [ROADMAP.md](../ROADMAP.md) §5 and §10
    should show it as a line item [inference: not yet costed].
- **Full loop, v1 (M6).** The whole genome below, including reflection atoms, under the suites and
  error control below. It starts once the harness has been stable for two epochs.

**Genome.** All atoms are content-addressed.
- **Card atoms:** Tier 0 blocks (≤ 8 KB total, a byte budget per block), Tier 1 sections,
  false-friend rows, worked examples ([05-agent-protocol.md](05-agent-protocol.md)).
- **Diagnostic templates:** wording, root-cause grouping, fix-it order, example-bearing diagnostics
  [RV: D2-D]. Error codes and their meaning are a stable API, outside the genome.
- **Ranking:** hole context, packs under closure budgets, `next:` actions.
- **Scaffolds:** when to call `hole`, `prove`, `explain` or `bench`; context and summarisation
  policy; retry strategy; when to `abandon`; drafting the free-text parts of a handover.
- **Reflection atoms (full loop only):** the reflection prompt and scaffold of the agent that reads
  harness logs and writes the next delta. They never ship; they live in the archive.

**How the self-reference closes.** In DGM the parent agent implements the diagnosed change in its own
codebase, so a better coding agent is also a better self-modifier [R01]. A genome that only improved
how agents write Mithril, edited by a fixed reflector, would not close that loop: better Mithril
scaffolds would not make the reflector better at proposing. F1-A closes it in three steps.
1. **An archive node is a whole agent configuration:** card, diagnostics, ranking, scaffold and
   reflection atoms.
2. **The node's own agent proposes its child.** The supervisor runs the agent configured by node g on
   g's harness logs and genome, and that agent writes the delta that yields g′. The delta may touch
   g's reflection atoms. Scaffold atoms (context, summarisation, retries, editing) serve the
   reflection task as much as the Mithril tasks, so gains there feed gains in proposing.
3. **Proposing skill is scored only downstream.** Selection uses HGM's clade metaproductivity over
   each node's descendants (§4.3) [R01]. A reflection atom earns credit only when the children it
   writes pass the sealed harness. It is never its own judge, so S1 holds, and S4 lets it change
   without promotion.

The reflexive gain runs through scaffold and reflection atoms; card atoms that only help with Mithril
need not help the reflection step. Whether the gain compounds is measured, not assumed: F1-A reports
whether descendants of improved proposers improve faster than their siblings (§16, open question 5).

**Outside the genome:**
- checker semantics and the harness;
- protocol integrity rules: the friction rule on a 4th identical failing retry, `abandon`
  semantics, journal-derived handover facts;
- per-attempt budgets;
- the scaffold's capability set: the `mithc` verbs plus read-only access to the task sandbox.

**Mutation, fitness, controls.**
- **Mutation:** GEPA-style reflective delta edits only, with full rewrites banned, kept in a
  DGM-style archive. GEPA reported about +6% over GRPO with up to 35x fewer rollouts [RV: D2-D].
- **Fitness:**
  - VP@1 on the rotating confirmation suite is primary;
  - CABW is co-primary and may not exceed a pre-registered tolerance;
  - tokens, turns and dollars per verified pass are reported as a Pareto slope, never a raw ratio
    [RV: D2-D].
- **Arms:** Mithril, Rust, C11, Rust + Mithril tooling and obfuscated-Mithril, on ≥ 2 model
  families.
- **Goodhart controls:** sealed rotating suites with oracles killing ≥ 95% of mutants, the
  obfuscated twin, leave-one-atom-out, padding sweeps, human promotion [RV: D2-D, R01].
- **Decay falsifier (F4):** every promoted atom is re-tested on each new model generation, on the
  current confirmation suite. An atom that stops helping is tombstoned with scope
  `{model_family, generation}` and trigger `model_generation != at_burial.model_generation`. A trick
  that still helps small local models stays in their scope [R01, RV: D3-i].
- **Cost:** a 5-point VP@1 difference needs about 1.5k attempts per arm if attempts were
  independent [inference, RV: D2-D]. Item-level variance raises that
  ([05-agent-protocol.md](05-agent-protocol.md) §13). DGM spent about $275 per iteration [R01], so
  each epoch has a dollar budget in [ROADMAP.md](../ROADMAP.md).

**Suites and error control (full loop).** F1-A promotion uses the same statistical machinery as F1
(§6), adapted to API models.
- **Three suites, three jobs.**
  - *Screening:* about 100 IRT-selected items from the non-held-out pool. It is exploratory: it ranks
    and stops early, but never produces promotion evidence, and its samples are never reused in
    confirmation (§6.4).
  - *Confirmation:* the epoch's rotating confirmation suite, refreshed with ≥ 30% fresh items each
    epoch ([05-agent-protocol.md](05-agent-protocol.md) §13). Every confirmatory test runs here.
  - *Permanent holdout:* never used for tuning. Only DR-017 kill decisions and edition gates touch
    it; F1-A never does.
- **Paired, interleaved design.** Candidate and incumbent genomes run on the same items, in
  randomised interleaved order within one session window, against pinned model snapshot IDs. API
  models drift silently (snapshot updates, rate limits), the same non-stationarity §6 guards
  against on the desktop. A snapshot change or a burst of provider errors voids the session, as a
  machine-profile mismatch does.
- **Statistic.** The per-item paired difference in pass rate, d_i in [−1, 1], with model families
  weighted equally. It is bounded, so a betting e-process applies without clipping.
- **Error budget.** F1-A has its own α budget, set by the Owner (S6). Promoted atoms ship in every
  agent's card, so the budget works like a default's: union bound, α_i charged on entry to
  confirmation, threshold max(20, 1/α_i) (§6.5, DR-018). CABW is checked by a non-inferiority
  e-test at the same threshold. Promotion needs both, an intersection-union test that spends no
  extra α.
- **Judge, then authority.** The deterministic Gatekeeper evaluates the e-gate. Maintainer review is
  the authority step after it [P1 §8]. A maintainer can reject a candidate that passed, but cannot
  promote one that failed.

**Integrity and promotion.**
- **The harness owns the oracle.** Attempts run in sandboxes with only the model API reachable.
  Pass/fail comes from bit-exact oracles, never the agent's report, which closes DGM's log-faking
  class.
- **Candidate atoms are untrusted text.** An atom that says "print PASS" cannot fake a pass. It
  could raise CABW, which blocks promotion (§12).
- **S1.** No candidate is judged by a harness containing unpromoted F1-A artifacts. The harness's
  suites, oracles and statistics contain no F1-A artifacts at all.
- **Promotion** ships card, diagnostic, ranking and scaffold atoms; reflection atoms never ship. The
  shipped card stays curated: self-generated skills *lowered* SkillsBench scores by 8–12 points
  [G01]. F1-A is the evaluation that keeps untested agent-written atoms from shipping.

**Beyond DGM.** DGM selected and reported on one benchmark, used unit-test oracles, and saw gains
shrink on stronger models [R01]. F1-A answers each point:
- exact oracles;
- CABW as a co-primary metric;
- separate screening, rotating-confirmation and permanent-holdout suites, with α-budgeted,
  paired confirmation;
- a Rust + Mithril tooling control arm;
- model-generation triggers, so decay is measured rather than discovered;
- the proposer's own reflection atoms in the genome, selected by downstream clade metaproductivity
  rather than by the benchmark score that HGM found mispredicts descendants [R01].

---

## 11. F2, F3 and Fm

**F2, compiler (later; after the port, DR-016).**
- **Heuristic hooks** (tiling, inlining, unrolling, fusion, register priority) are pure functions
  choosing among certified rewrites. They can make code slower, never wrong. This is the MLGO and
  AlphaEvolve-tiling pattern [R01].
- **Generalisation.** Heuristics are judged on held-out shapes on two microarchitectures, as
  AlphaEvolve held out half its shapes [R01].
- **New rewrite rules** carry obligations:
  - IEEE-exact: the T1 rule audit by Z3 FPA or exhaustive binary32 (DR-010), including the
    NaN-order side condition;
  - integer: T2;
  - tolerance-only rules are unreachable from exact code.

  Rule sets are versioned, so a revisit can ask "would rule R change this verdict?".
- **Cost models rank and never decide.**
- **Translation validation in CI.** Kernels get T1 on objects (B1.5). Non-kernel C gets `mithi`
  differential testing plus the hash corpus ([04-toolchain.md](04-toolchain.md)).
- A candidate compiler never builds F0 (S2).

**F3, language (later; human-ADR editions).**
- The Forge proposes and measures language changes but never promotes them. Syntax freezes early
  [G01].
- The corpus gate includes **every archived candidate's and tombstone's reproduction source**, so
  the graveyard stays executable [P4 §8.9].
- Preservation is judged on *outputs* (old vs new `mithi`, goldens, hash corpus). MIR-hash equality
  is only a fast path where the semantics delta is empty, since a judge noted hash preservation is
  undefined when semantics change.
- Fitness must improve with a CI excluding zero on ≥ 2 families, and CABW may not worsen. Stdlib
  signatures are F3; implementations are F1 realisations.

**Fm, meta (later; by-trigger).**
- **Objects:** the selection policy, the budget split (§4.5) and the revisit priority model (§7.4).
  Proposers, prompts and operators are not Fm objects (S4).
- **Trigger:** complete evaluation logs exist for ≥ 3 campaigns in ≥ 2 slots [target].
- **Counterfactual replay:** "what would π′ have selected, and what did those nodes score?"
  [R01 #21]. Visits to unevaluated nodes are estimated off-policy and flagged.
- π′ then steers a capped shadow run (≤ 10% of budget [inference]) before human promotion.

---

## 12. Prompt-injection hygiene for archived text

Proposers read tombstone rationales, comments, diagnostics, candidate source, handover rationales
and overlay provenance. All of it is **untrusted data** (threat model in [03-trust.md](03-trust.md)).
Integrity does not depend on proposers obeying anything: every proposer is a Builder without
AUTHORITY, and every decision that matters is F0 code over typed facts. Injection can therefore bias
proposals and waste budget, but it cannot promote. The controls below narrow even that.

| Text | Read by | Control |
|---|---|---|
| Tombstone rationale | Proposers, revisit agents | Scope, class and triggers are parsed fields; triggers are predicates, never prose; rationale is length-capped and carries principal, role and model family |
| Candidate source and comments | Next-generation proposers | Rendered as code in delimited blocks with provenance; comments from unpromoted candidates are stripped from summaries |
| Diagnostics, `explain` output | Proposers, F1-A models | Generated from templates; echoed text is quoted and escaped |
| F1-A atoms | Models under test | Candidate text; effect measured (CABW), never trusted |
| Handover rationale | Next session | Facts come from the journal; only rationale and next actions are free text, length-capped |
| Overlay provenance (later) | Gate dossiers | Typed fields, format-validated |

Five further rules apply.
1. **Frame archived text as data.** Context packs give each block a provenance header and a "data,
   not instructions" frame. Control characters, zero-width characters and bidi overrides are
   stripped.
2. **Judges never read free text.** The Gatekeeper and the measurement service use typed facts only.
3. **Detection is advisory.** Instruction-like text is flagged, but nothing relies on detection.
4. **Owner dossiers put typed facts first** and mark free text untrusted. Social engineering of the
   human signer is the remaining route to AUTHORITY.
5. **No secrets in free text.** Proposer context goes to model providers, so the gate rejects facts
   that match key formats.

---

## 13. Pre-registered minimum benefit per milestone

Milestone names follow the P5 backbone. **[ROADMAP.md](../ROADMAP.md) §8 is the single authoritative
table** of minimum Forge benefit, as ROADMAP is for numbering, dates and costs. The middle columns
below quote it (F2 and F3 quote ROADMAP §6). The last column adds the Forge-side checks that make
each row decidable. If the two ever differ, ROADMAP wins. Level names follow ROADMAP: F1-sim
(simulator), F1-live (engine) and F1-place (CPU/GPU placement), so none reads as F1-A. A tombstone
is the record of a miss, never a pass: a Forge track that misses its minimum is re-scoped as
written, and the miss becomes a scoped tombstone with triggers, so the Forge's own funding obeys the
revisit rule.

| Milestone · level | Minimum [target] (ROADMAP §8) | If missed (ROADMAP §8) | Forge-side checks (this document) |
|---|---|---|---|
| **M0** · F1-sim (simulator) | *Readiness:* σ_d published per run type and niche; the §7.6 acceptance tests pass; the prune pilot is reproduced with zero bound violations. *Benefit:* a policy beats LRU on simulated NVMe bytes/token or stall time by ≥ the pre-registered MDE on sealed held-out traces. (An accepted planted hack is X4's HALT-F, ROADMAP §3.5, not a Forge miss) | Readiness miss: no M4 campaign until fixed. Benefit miss: the policy line enters M4 as a hypothesis with its campaign budget halved | 100% of both planted-hack batches caught at their declared stage; A/A calibration passes. A planted hack accepted → no Forge result counts until the evaluator is redesigned and the suite passes (the language continues) |
| **M2** · F1 exact schedules | A T1-validated schedule, found by search inside the certified schedule space (not a hand port of a C prototype, ROADMAP §7 B3), with a measured gain at e ≥ 20 against C Hearth `main` on a compute-bound configuration (the T > 1 prefill matmul in S1's scope), recorded as a ledger fact (no promotion before grants exist, M6). Assurance, every dispatched variant `validated`, is M2's gate, not a Forge benefit | Schedule search moves to M6 with its budget unchanged | T1 on the emitted object precedes measurement (§3). Other compute-bound candidates: prefill tiling and the attention value pass (18 → 94 GMAC/s prototype, measured [R11]). A miss is a tombstone with gap attribution |
| **M3** · revisit engine | *Readiness:* design graveyard imported; zero false fires on replay; the ADR-0004 backtest reported | Re-gated at M5; revisit spending limited to the audit slice until it passes | The CI check parses every DECISIONS.md trigger against §7.2; the firing tests (§7.6) pass; X4's tombstone replay is identical on the signed M3 ledger |
| **M4** · F1-live | *Safety:* ≥ 100 type-checked policies bit-identical in one golden run; the chaos suite kills 100% of seeded core mutants; counters = replay for every `timing_blind` configuration; zero false prunes in ≥ 60 audits on the eligible part of the 144-candidate grid. *Benefit:* the best measured policy beaten at ≥ 1 cache size, with e ≥ 20 on tok/s or stall time, or by ≥ the MDE in NVMe bytes/token (deterministic count, `timing_blind` configurations only) | Safety: per M4's kills in ROADMAP §5 (a logits change → HALT-F; a false prune → replay bounds demoted to `est`, the Forge continues). Benefit: policy budget halved for M6 | e ≥ 20 is a ledger fact here, not a promotion (grants arrive at M6). The bytes route needs one run whose counters equal the replay (§5.4). A type-checked policy that changes logits halts F1 promotion until the core theorem is repaired |
| **M4–M7** · revisit | The revisit benefit claim (ROADMAP §8) | Revisit spending drops to the audit slice; the null result and its cost are published | Re-tests through fired triggers and through the audit slice are counted separately (§7.4, steps 2 and 7) |
| **M6** · F1 (policy and schedule) | B3's gain (ROADMAP §7): found by the Forge in a certified space; ≥ 5% tok/s (e ≥ 20) **or** ≥ 10% fewer NVMe bytes/token (deterministic count) on a named configuration, against C Hearth `main`; zero output changes | None after 2 campaigns (≤ $10k [inference]) → policy and schedule lines tombstoned; the Forge goes revisit-only; B3 fails | Promotion to an opt-in profile through a standing grant (§8.2). The bytes route is a deterministic count for `timing_blind` configurations (§5.4). Reachability under the specimen grant: §6.6, consequence 6 |
| **M6** · F1-A | ≥ 1 atom or scaffold delta, kept after leave-one-atom-out, that raises held-out VP@1 or cuts tokens per verified pass (TPV) by ≥ 10% at non-inferior VP@1, with the CI excluding zero on ≥ 2 model families, and CABW not worse | Amber: one more epoch, judged at M7. No gain in 2 epochs → F1-A frozen; atoms tombstoned with model-generation triggers | Promotion through §10's e-gate on the rotating confirmation suite (F1-A α budget, ≥ 2 families, CABW non-inferior), then maintainer review |
| **M7** · F1-A, F1-place | F1-A gains hold on the rotated suite. If the GPU tier exists, a placement plan is ≥ 2x CPU-only end-to-end (measured) | F1-A frozen; GPU per DR-022 | F4 decay re-runs on each new model generation (§10). Placements enter F1 only after the DR-022 gate (§2.1) |
| After the port · F2 (ROADMAP §6) | An evolved heuristic beats the hand-written one on held-out shapes on two microarchitectures, with zero translation-validation failures | Gain lost in 2 consecutive rounds → heuristics freeze; rule work continues | — |
| After M7 · F3 editions (ROADMAP §6) | Human ADR backed by harness evidence; migration preserves the corpus, tombstone recipes included | No delta improves VP@1 within 2 epochs → F3 limited to stdlib, docs and diagnostics | The Forge proposes and measures, never promotes (§11) |

**Rule (ROADMAP §8).** Two consecutive misses on the same line cap that line's spending at the
background audit slice. The lines are policy (M0 → M4 → M6), schedule (M2 → M6), revisit
(M3 → M4–M7) and agent interface (M6 → M7). The capped line becomes a tombstone with triggers: a new
hardware fingerprint, a second drive, a VRAM tier, or a new proposer model generation. When every
line is capped, the Forge as a whole runs revisit-only.

**The F1-A pilot (M1–M5)** has no minimum of its own. It proposes and maintainers decide (§10); its
results count toward the M6 F1-A row.

Reviewer note: ROADMAP §5 and §10 should list the F1-A pilot (§10).

The priors from §1.3 are pre-registered with this table: policy gains of a few points, prefetch
ahead of eviction, about 1.5x total CPU headroom, and the GPU lever behind the DR-022 gate. Benefit
reports count assurance explicitly: holes closed, mutants killed that goldens missed, hacks blocked
([ROADMAP.md](../ROADMAP.md) B1).

---

## 14. How this goes further than DGM, HGM, AlphaEvolve, ShinkaEvolve and the AI CUDA Engineer

The pieces have precedents; the contribution is the combination, made checkable. Five mechanisms
carry the difference:

1. **Correctness is certified per space.** That leaves the clock as the only exploitable signal, and
   the runtime owns it.
2. **Hacks are closed by construction, not monitored.** Capability types, binary confinement, a
   runtime-owned clock, sealed role-owned gates and validated plausibility bounds do the work.
3. **Statistical error is a budgeted resource.** It is spent per confirmatory test (online FDR for
   revocable profiles, a union-bound budget for defaults and shipped agent atoms), on a measurement
   design that stays valid on a noisy desktop and names its estimand.
4. **Negative knowledge is durable, scoped and self-reviving.** Decidable triggers sit in a permanent
   ledger, and design ideas share the graveyard.
5. **The agent-interface loop is scored by exact oracles,** with CABW, control arms and decay
   tracking.

| Axis | DGM [R01] | HGM [R01] | AlphaEvolve [R01] | ShinkaEvolve [R01] | AI CUDA Engineer [R01, R05] | Mithril Forge |
|---|---|---|---|---|---|---|
| What improves | Own scaffold (Python repo, frozen model) | Own scaffold | User programs/heuristics in EVOLVE-BLOCKs | User programs | CUDA kernels for PyTorch ops | F1 policies, schedules, layouts; F1-A agent interface, including its own reflection atoms; F2/F3/Fm later |
| Correctness basis | Benchmark pass rate | Benchmark pass rate | User-written evaluator | User-written evaluator | Tested numerical agreement | Space soundness re-checked per build on the binary, or a per-candidate T1/T2 witness; never tests for exact slots |
| Evaluator integrity | Sandbox, time limits, hidden checker, monitoring | Not discussed | User's design | User's design | Hardened after exploits | Runtime clock and joins, poisoned allocations, materialised outputs, binary allowlist, sealed gates, validated bounds |
| Documented failure | Faked logs; deleted markers | Nested diffs hard to read | Leaky verifier (Tao et al.) | — | 3.13x → 1.49x once loopholes closed | None yet; M0 plants the documented hacks first |
| Archive lifetime | One run | One run | One run | One run | — | Permanent ledger keyed by closure × environment |
| Negative results | Unscoped stepping stones | Unscoped nodes | Population | Rejected duplicates, not kept as knowledge | Not recorded | Scoped tombstones: class, binding factor, recipe, decidable triggers |
| Context change | Not modelled | Not modelled | Not modelled | Not modelled | Not modelled | `mithc revisit` fires on environment events |
| Diversity | Child-count "novelty" | Clade tree | MAP-Elites + islands | Novelty rejection (embeddings + LLM judge) | — | QD over hardware × shape × model × grade; exact dedup first |
| Selection | sigmoid(score) × 1/(1+children) | CMP, Thompson sampling, expand vs evaluate | MAP-Elites sampling | Balanced sampling; bandit over LLMs | — | HGM CMP + DGM floor + cross-niche credit |
| Measurement economy | 10 → 50 → 200 tasks; ~$22k per run | 517 vs 1231 CPU-h (SWE-Verified-60); 347 vs 2385 (Polyglot) | Cascade; async cluster | ~150 samples (circle packing) | — | Exact dedup + sound replay prunes (`timing_blind`) + deterministic bytes claims |
| Statistics | 3-run variance; same benchmark selects and reports | Held-out Lite split | Held-out shapes | — | — | Confirmatory e-processes, interleaved blocks, composite null, stationarity voids, α per test (e-LOND for profiles) |
| Meta-level | Fixed | Fixed | Meta-prompt evolution | Meta-scratchpad | — | S1–S6; strengthening-only edits graded `proof` |
| Human role | Fixed loop, supervision | Fixed loop | Expert confirmation | — | Post-hoc correction | Grants for profiles; Owner ADRs for defaults, F0, editions |

**Borrowed explicitly:**
- the archive and floor (DGM);
- CMP and expand/evaluate (HGM);
- EVOLVE-BLOCKs, the cascade and held-out shapes (AlphaEvolve);
- novelty rejection and the proposer bandit (ShinkaEvolve);
- the hack catalogue (AI CUDA Engineer, CUDA-L1, METR, robust-kbench);
- QD, POET and PATA-EC [R02];
- Go-Explore's return-then-explore;
- anytime-valid gates [RV: S1].

**Not claimed:**
- unbounded improvement;
- formal speed proofs;
- breadth: AlphaEvolve's open evaluators handle arbitrary scores, while certified spaces are narrow
  by design;
- compute scale;
- that agent-interface gains persist as models improve, which F4 measures;
- any measured result yet. The Mithril column is a design until §13 passes.

---

## 15. Living models (post-v1)

Status **later** (DR-025). Every weight change must be an explicit, typed, provenance-carrying,
reversible value [R12].

- **Immutable versioned weights.** `Weights<V>` is a Merkle root over base slab hashes plus an
  ordered overlay stack. An update creates a new version. Mixing two versions in one forward pass is
  a type error [R12 M1].
- **Typed overlays** are the only legal way to change weights: `SlabReplace`, `LowRank`,
  `SpectralScale`, `AddExpert`, `SlotDelta`, `Codebook`, `KVPrefix`. `Retrieval` is the default for
  facts, because it beat parameter editing in 2025–2026 studies [R12 M2].
- **Copy-on-write at expert granularity.** Caches key on physical slab hash, so shared experts share
  residency. Baking a low-rank overlay into a quantised slab requantises, so the gate re-runs
  [R12 M3].
- **Epoch commit at token boundaries** (`hx_store_tick`). Sequences are pinned to a version by
  default. A live migration declares `Recompute(from_layer)`, `AcceptStale` (flagged
  non-reproducible) or `Restart`. No CMPXCHG16B swaps, INVD or self-modifying code [R12 M4].
- **Determinism:** `logits = f(binary, ISA, version_root, inputs, kv_policy)`, with the version root
  logged per token [R12 M7].
- **Training only produces overlays.** A `train` effect (reserved; not in the v0 effect set of
  [01-language.md](01-language.md)) declares its compute and byte budget and never mutates
  `Weights<V>` [R12 M8].
- **In the Forge**, overlays are lossy-lane (`approx`) F1 candidates, opt-in, **never default**.
  Their gates are statistical and maintainer-owned [R12 M6]:
  - efficacy and generalisation; locality;
  - canaries: held-out perplexity, KL to parent, a small MMLU-style probe;
  - calibration and safety refusal; spectral checks on the delta;
  - MoE routing drift with simulated cache impact, a pre-commit speed gate GPU servers lack.

  Overlay tombstones trigger on `base_version != at_burial.base_version`.
- **Signed provenance** is mandatory, and overlays pass model-file format validation [R12 M5].
- **Costs.** An unmerged rank-16 BF16 LoRA adds about 11% to each overlaid Q4 expert's bytes
  [inference, R12].
- **Do not build** SMT-certified loss bounds, "forgetting-free" subspace types or per-token
  persistent learning [R12].
- **Design coupling.** The KDA recurrent-state snapshot API and the overlay API are designed together
  when Hearth adds Kimi-K3 (DR-025, [02-compute.md](02-compute.md),
  [07-hearth-port.md](07-hearth-port.md)).

---

## 16. Open questions and reviewer notes

**Open questions**
1. What are σ_d and the void rate for microbenchmarks and end-to-end decode? This M0 measurement
   decides nightly confirmation capacity (§6.6).
2. How much of the simulated 16–41% prune fraction survives the `timing_blind` restriction (§5.4)?
3. Is the PATA-EC niche test stable under desktop noise? How accurate must κ be before revisit
   priorities become noise [R02]?
4. Is counterfactual replay plus a capped shadow run a sufficient safety test for Fm? Which
   signals can proposers see without leaking the scorer [R01]?
5. Do F1-A gains persist across model generations [R01]? Do descendants of improved proposers
   improve faster than their siblings, as DGM's self-reference predicts (§10)?
6. How much power does scoring outlier blocks as candidate losses (§6.2) cost on this desktop? The
   M0 A/A calibration answers it.

**Reviewer notes on the outline**
- **α semantics (§6.5).** Resolved. Charge per confirmatory test, not per promotion. The test
  supports "not an improvement" (effect ≥ 0), not "an improvement of at least the MDE". The
  guarantee is two-tier: union-bound α budgets for defaults and F1-A promotions (an expectation,
  plus a probability when the budget is ≤ 1); e-LOND online FDR ≤ q for grant-promoted profiles.
  The siblings named in §6.5 state it identically. Budget sizes, q and γ need Owner decisions.
- **Forge verb (§1.1).** Resolved: campaigns are supervisor-only, and agents use
  `mithc bench --slot` and `mithc ledger campaign`, which [05-agent-protocol.md](05-agent-protocol.md)
  §11 lists in its verb table.
- **F1-A self-reference (§10).** The outline calls F1-A the DGM-proper loop. It is DGM-proper only if
  the proposer is itself evolved, so reflection atoms are in the genome and scored by clade
  metaproductivity. [ARCHITECTURE.md](../ARCHITECTURE.md) §1.3 (N6) and §11.1 should say so, and
  should drop "proposer prompts" from Fm.
- **Plausibility bounds need two conditions (§5.3):** phys/audited-emp peaks (outline §3), with
  `emp` peaks entered as `emp_bound` ([02-compute.md](02-compute.md) §13.2), *and* a bound
  computation graded ≥ validated (outline §5). Grants cannot auto-promote without both.
- **Diagnostics** sit in F1-A per the outline, while P4 put them in F2. The outline is followed.
- **The `train` effect** is absent from the effect list and is marked reserved.
- **HGM figures.** The panel digest calls P4's "2.4–6.9x" unsourced, but R01 supports both ends
  (1231/517 ≈ 2.4; 2385/347 ≈ 6.9). This document cites the raw CPU-hours.
