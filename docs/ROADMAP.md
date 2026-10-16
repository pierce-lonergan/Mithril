# Mithril roadmap

This is Mithril's delivery plan: what gets built in what order, what must be true before the next
step starts, and which results stop the project or re-scope it. It follows the P5 backbone
[P5 §10] with the design panel's grafts (DR-001). The plan opens with M0, a falsification sprint of
five to six weeks. M0 runs five experiments (X0 instruction census, X1 agent writability, X2 checker
spike, X3 one meaning plus schedules, X4 evaluator integrity), writes the core-calculus note and
collects the owner decisions D0. Its results can stop the standalone language, or re-scope it to
tools over Rust/C, before the expensive parts exist. Milestones M1–M7 then port Hearth and measure
what the port bought. Each milestone has a deliverable, a measurable gate, a pre-registered kill
criterion and a cost labelled [inference]. Agent gates compare against Rust (DR-017). Performance
gates compare against an interleaved `hearth-c-ref` (DR-018). The document also fixes the benefit
claims B1–B3, a minimum Forge benefit per milestone (with a revisit benefit claim), measurement and
quiet-machine budgets, a deferral register with a measurable trigger for every deferred feature,
and the owner decisions D0. Every kill that fires becomes a tombstone,
so `mithc revisit --design` can reopen the stopped line when its trigger fires.

**Contents**
1. [Rules for every gate](#1-rules-for-every-gate)
2. [Timeline](#2-timeline)
3. [M0: the falsification sprint](#3-m0-the-falsification-sprint)
4. [Kill outcomes](#4-kill-outcomes)
5. [Milestones M1–M7](#5-milestones-m1m7)
6. [Beyond M7](#6-beyond-m7)
7. [Pre-registered benefit claims B1–B3](#7-pre-registered-benefit-claims-b1b3)
8. [Minimum Forge benefit per milestone](#8-minimum-forge-benefit-per-milestone)
9. [Deferral register](#9-deferral-register)
10. [Cost and owner hours](#10-cost-and-owner-hours)
11. [Owner decisions D0](#11-owner-decisions-d0)
12. [Reviewer notes](#12-reviewer-notes)

Section 13 of [ARCHITECTURE.md](ARCHITECTURE.md) summarises this file. The full stage gates are in
[07-hearth-port](architecture/07-hearth-port.md), measurement statistics and the tombstone engine are
in [06-forge](architecture/06-forge.md), the harness design is in
[05-agent-protocol](architecture/05-agent-protocol.md), and decision records are in
[DECISIONS.md](DECISIONS.md). All Mithril syntax shown here is provisional until the Surface Lab
decides it.

---

## 1. Rules for every gate

1. **Pre-registration.** Every experiment and gate has a written record, made before any data is
   collected. It states the hypothesis, arms, metrics, sample size, analysis, power and thresholds,
   and what happens on each outcome. The Owner signs it, and it enters the ledger as an AUTHORITY
   fact ([03-trust](architecture/03-trust.md)). Thresholds never move once data has been seen. If a
   margin turns out to be unaffordable, a new signed record must replace it before collection.
2. **Three outcomes.** Every gate is *pass*, *amber* or *kill*. Amber always has a written action: a
   bounded extension or a narrowed claim. No band between gate and kill is left undefined (the flaw
   the judges found in P3's M4).
3. **Deterministic judge.** The Gatekeeper, which is deterministic code plus the Owner key, evaluates
   every gate (N5). LLMs may run it and assemble dossiers, but never judge.
4. **Relative performance (DR-018).** Performance gates are non-inferiority tests:
   - margin δ = 3%;
   - an anytime-valid e-value;
   - interleaved and load-gated against `hearth-c-ref`, in the same session;
   - on a declared quiet-machine profile.

   Non-inferiority holds when the e-process against "ratio < 0.97" reaches 20 [target]. Superiority
   also needs e ≥ 20. Absolute figures are context only. One example is the 69.6 GB/s single-thread
   figure, which was measured L2-resident on a busy machine [R11]. In source, such a gate is a sealed
   claim:

   ```mith
   /// Claims live in spec items owned by the Author role and hash-locked; Builders cannot edit them.
   spec q4_matvec_claims for q4_matvec {
       claim refines(q4_matvec_avx512, q4_matvec) requires validated;     // T1 witness on the object
       claim refines(q4_matvec_avx2, q4_matvec) requires validated;
       claim perf(q4_matvec_avx512) requires measured
           noninferior(to: hearth_c_ref::mm_q4_avx512, margin: 3%);
   }
   ```

   Two calibrations back these gates (X4, §3.5). A/A sessions validate the superiority null.
   Planted-regression sessions validate the non-inferiority null, which A/A cannot test: at a true
   ratio of 1.0 the non-inferiority e-process *should* reach 20. Quiet-machine time bounds every
   parity gate (§10):
   - Each stage names its **confirmatory** configurations. The rest are **screening-only**: one fixed
     6-block session each, escalated to confirmatory only if the point estimate is worse than −1%
     [target].
   - **Inconclusive is amber, not kill.** If the e-process has not reached 20 after N hours, where N
     is twice the hours §10 plans from M0's measured σ_d [target], the configuration gets gap
     attribution (counters, `mithc explain`), one bounded tuning window and one more N-hour session.
     If it is still inconclusive, a signed record ships the module behind its seam with C as the
     default, and a scoped tombstone keeps the question open. A kill needs a confirmed regression:
     the anytime-valid upper confidence bound on the ratio falls below 0.97.
   - **Rebase windows re-measure only what changed.** Correctness gates re-run in full at every
     window ([07](architecture/07-hearth-port.md) §6). A performance gate re-runs only if the
     build-closure hash of its measured binary changed.
5. **Agent gates against Rust (DR-017).** Every agent gate uses:
   - at least 60 held-out items;
   - a task-clustered mixed-effects analysis;
   - at least two model families;
   - a power analysis published with the threshold.

   VP@1 (verified pass@1) and CABW (checker-accepted-but-wrong rate) are co-primary, and each can
   trigger a kill on its own.
6. **No unregistered features.** Each milestone gate checks that nothing landed outside the
   milestone's deliverables or a fired trigger in the deferral register (§9) [P5 §11.2].
7. **Labels.** Thresholds in gate and kill columns are **[target]**. Costs and dates are
   **[inference]**. Facts are marked *measured* or *simulated*, with a citation. Status labels map
   to milestones:
   - **v0**: in the mithc that ports Hearth (M1–M5);
   - **v1**: present by Edition 1 (M6–M7);
   - **later**: planned after M7;
   - **reserved**: in the types and schema but not producible;
   - **by-trigger**: added only when its register trigger fires.

   Product version numbers are not status labels. "Ledger v1" and "`std_platform` v0" name
   releases of a component; ledger v1 lands at M3, so its status is v0 (M3).
8. **Kills become tombstones.** A fired kill is written as a design-level tombstone with a scope, a
   failure class and a decidable trigger ([06](architecture/06-forge.md), §4).

---

## 2. Timeline

All dates are [inference]. Gates depend on deliverables, not dates, except for the schedule kill in
M1.

```text
weeks  0    1    2    3    4    5    6
D0     [owner decisions.............]
X0     [census]
X1     [grammar, cards, mithi, tooling kit, suite][mithi check][runs, all arms][report]
X2     [semantics table + Zen 5 fuzz ... T1/T2 spike][report]
X3          [generator ...........][A/B per compiler][report]
X4     [measurement svc + sandbox][hack suite][calibration; sim Forge + tombstone replay][report]
CC     [core-calculus note ...............]
quiet  nights: X3 A/B, X4 calibration | days: X2 fuzz, builds, X1 local pilot
                                             [M0 verdict + sign-off]
months
 1.5 - 3.5   M1 front end + agent protocol; scalar S1
 3.5 - 5     M2 kernels: KIR, schedules, T1/T2, object audit; S1 complete
 4.5 - 6     M3 formats, ABI, ledger v1, revisit engine; S2
 5.5 - 7.5   M4 concurrency, store logic, certified policy space; S3 + S4
 7.5 - 9.5   M5 forward pass, API, platform layer; S5 + S6a + S6b
 8.5 - 10.5  M6 measured benefit: B1-B3, Forge campaigns (F1 + F1-A)
10.5 - 16    M7 Edition 1 + triggered growth
```

---

## 3. M0: the falsification sprint

| Exp | Assumption under test | If it is false |
|---|---|---|
| X0 | We know which instructions real compilers emit for Hearth's kernels [G02, open question 6] | X2's table scope is wrong and the object audit may be unsound |
| X1 | Cold agents write Mithril nearly as well as Rust | The standalone surface stops (DR-017) |
| X2 | A small T1/T2 checker accepts Hearth's real kernels and rejects wrong ones | The validated-bit-identity claim (N2) dies |
| X3 | One meaning plus schedules regenerates the scalar/AVX2/AVX-512 triplets at parity | "One generator replaces the triplets" leaves the plan |
| X4 | The judge (measurement, sandbox, gate) cannot be gamed | The Forge halts until it is redesigned |

### 3.1 X0: instruction census (weeks 0–1.5)

- **Build.** Compile `quant.c`, `quant_avx2.c` and `quant_avx512.c` with MSVC, Clang and GCC under
  Hearth's strict FP flags, then XED-decode the objects. For each kernel × ISA × compiler, record:
  - the iclass set;
  - how sequence intrinsics (`_mm512_reduce_add_ps`, horizontal shuffles) are lowered;
  - unrolling, rotation, peeling, spills and register reuse;
  - any FP-environment instructions.
- **Deliverable.** A census ledger record that gives the delta against the ~105 forms and 74
  mnemonics implied by the intrinsics [G02], plus the loop-correspondence patterns T1 must handle.
  The union of the census sets the scope of X2's table (DR-008).
- **Gate.** Every dispatched variant is covered under every release compiler. No FP contraction or
  reassociation appears under the strict flags. If one does, it is reported to Hearth as a flag
  defect.
- **Amber.** The union is more than twice the intrinsic-implied forms, or more than 20 mnemonics are
  FP-sensitive [target]. The table then covers only the release compilers (MSVC on Windows, Clang
  elsewhere). Variants from other compilers drop to `tested` and are not dispatched in release
  (DR-008).
- **Narrowing.** If hot-kernel loops fall outside the lockstep rule plus correspondence maps, the
  object audit (B1.5) is deferred and T1 runs at intrinsic or KIR level only. The C compiler then
  stays trusted for kernels, and B1's first item narrows.
- **Cost.** $0.5–1.5k, ~10 h [inference].

### 3.2 X1: cold-agent writability with all arms (weeks 0–5)

- **Build.**
  - The Lark grammar v0.
  - A Tier 0 card (≤ 8 KB) and a Tier 1 card.
  - `mithi`: an independent Rust tree-walking interpreter with a type checker (~4–6k lines,
    [inference, P5 §10.1]). It becomes M1's differential oracle.
  - The **M0 tooling kit** for the Rust + Mithril tooling arm: a rust-analyzer-based shim that
    answers `todo!()` holes with the expected type, in-scope bindings and relevant trait impls; and
    the false-friend table ([01 §2.5](architecture/01-language.md)) as a clippy-style lint pass over
    Rust. About 10 owner hours and $1–2k [inference]. If the kit is not ready when the held-out runs
    start, the arm is dropped from X1 and starts at M1, and amber (a) waits for M1.
- **Checker precondition (before any held-out run).** `mithi` is judged before it judges agents,
  because its false rejections lower VP@1 and its false accepts distort CABW:
  - it accepts 100% of the hidden reference solutions for the Mithril arms;
  - it rejects 100% of a planted corpus of Dc constructs and type errors (≥ 100 items [target]),
    written by a model family other than `mithi`'s author;
  - it agrees with the core-calculus note's hand derivations on every canonical and derived snippet.
    The note's rules for the X1 subset are frozen at this point; a later change that would flip a
    verdict on an X1 item is recorded as an amendment and applies from M1.

  `mithi`'s hash is frozen in the pre-registration. **Re-scoring rule (pre-declared):** if a `mithi`
  bug is found after collection, the fixed `mithi` re-scores every final verdict. Attempts in which a
  reversed verdict occurred mid-loop are reported, and the analysis is run with and without them. If
  they exceed 5% of a Mithril arm's attempts [target], the held-out result is void and the run
  repeats on a fresh sealed batch, built as M1's is (§5). "Infrastructure failures are re-run" does
  not cover a wrong checker verdict.
- **Suite.** At least 80 sealed Hearth-shaped tasks: about 20 for card iteration and at least 60
  held out. The task families:
  - T-Q4, T-ACTQ, T-NORM;
  - T-ROUTE (top-k with ties going to the lower index);
  - T-EVICT (a `timing_only` policy);
  - T-STORE (a pinned, 4096-aligned slab arena);
  - T-FMT (a bounded container parser);
  - T-CTRL (a mutex-guarded queue and a rank-order combine) [P1 §7.11, P5 §10.1].

  Every oracle must kill at least 95% of mutants, including `numerics_v1`.
- **Arms.** All six run from day one (the tooling arm if its kit is ready, see Build).

  | Arm | What the agent gets |
  |---|---|
  | Mithril | Paper Mithril, Tier 0+1, `mithi` as checker, static-dispatch traits (DR-005) |
  | Mithril without traits | Traits rejected by a Dc diagnostic, so the cost of their absence is measured (DR-005) |
  | Rust | rustc/cargo, same oracles and checker-call budget |
  | C11 | Clang, same oracles |
  | Rust + Mithril tooling | Rust plus the M0 tooling kit (above): the false-friend lint pass over Rust, `todo!()` hole context through rust-analyzer, the same check loop. `mithc lift` and full diagnostics join at M1, so at X1 this arm is a floor for the cheapest competitor |
  | Obfuscated Mithril | Same semantics with renamed keywords. Separates comprehension from guessability [P1 §7.11] |

- **Participants.** At least two frontier families, with 8 checker calls per task [P5]. They carry
  the kill. One Hearth-hosted local model runs as a **pilot**: the Mithril and Rust arms on one task
  family named in the pre-registration, about 10 held-out items × 3 attempts × 2 arms = 60
  attempts. At about 20 tok/s, with 5–10 minutes per agentic attempt, that is 5–10 hours of loaded
  9950X time [inference]; the full design (about 80 items × 6 arms × several attempts) would need
  100+ hours, in the same weeks that X3 and X4 need quiet windows. Local runs, like X2 fuzzing and
  builds, use daytime only and never overlap quiet-machine windows (DR-023). The local pilot is
  reported, not part of the kill. The local model joins every arm from M1, with its machine hours
  sized in M1's pre-registration.
- **Metrics.** VP@1 and CABW (co-primary); tokens, turns and dollars per verified pass;
  first-compile rate; and the **subset rejection rate**, the share of passing Rust solutions the
  subset rejects, by Dc rule ([05](architecture/05-agent-protocol.md)).
- **Analysis.** Mixed-effects, with task as a random effect. The card iterates for up to 3 epochs on
  training items only; the held-out set runs once, after the card freezes.
- **Power.** The dossier estimates about 1.5k attempts per arm for a 5-point difference [RV: D2-D,
  inference]; 1/δ² scaling gives roughly 170 independent attempts for 15 points [inference]. Attempts
  within a task are correlated, so the task is the unit. The pre-registration publishes the kill's
  operating characteristics: it fires with probability ≤ 10% at a true 5-point gap and ≥ 90% at 25
  points [target]. If 60 items cannot meet that, the item count grows; the threshold does not move.
- **Gate.** Rust − Mithril VP@1 ≤ 15 points, and CABW is no more than 5 points worse than Rust's.
- **Kill (DR-017).** VP@1 gap > 15 points **or** CABW worse than Rust's by > 5 points. The
  standalone surface then stops, and Mithril ships as checker, ledger and tooling over Rust/C.
- **Review triggers (amber).**
  - (a) Rust + tooling beats Mithril by > 10 points [target]: the Owner reviews, before M1, whether
    the surface earns its cost.
  - (b) The traits ablation costs > 5 points: DR-005 is confirmed.
  - (c) The subset rejects > 30% of passing Rust solutions [target]: the Dc list is revised before
    M1.
- **Caveat.** Mithril has no full diagnostics yet, so this gap is pessimistic.
- **Cost.** $7–15k, ~55 h [inference], including the tooling kit and the checker precondition.
  Writing the suite and its oracles dominates; the attempt budget is in §10.

### 3.3 X2: T1 spike on transliterated Hearth intrinsics (weeks 0–5, verdict in week 6)

- **Build.**
  - A `mithcheck` spike. T1 matches FP DAGs modulo an audited exact-rewrite list, including the
    NaN-order side condition: a commuted add or mul is exact only if no MAXPS/MINPS-class consumer
    precedes NaN canonicalisation. T2 discharges ranges, for example the Q4 `maddubs` bound 3,810
    and the Q8 sign-trick bound 32,512 [R07].
  - Semantics entries for every census iclass, keyed by XED iclass, with an explicit FP-environment
    layer.
  - Hearth's Q4, Q8, F32 and act-q8 AVX2/AVX-512 kernels, transliterated into intrinsic-level IR with
    lane correspondence maps. The check validates the output, not each rewrite [P5 §10.1].
- **Fuzz.** Run the FP-sensitive iclasses on the 9950X with SNaN/QNaN payloads in each operand, ±0,
  subnormals, every mask pattern, VCVTPS2DQ indefinite results and MAXPS/MINPS NaN order. Bochs is
  the second oracle. The vector budget per iclass is pre-registered.
- **Mutants.** A `numerics_v1` pool of at least 200 mutants [target, P2 §10]: FMA contraction, lane
  count and tree shape, RNE→trunc, 127→128 clamp, dropped scale, tie flip, removed NaN
  canonicalisation, NEOX/GPT-J RoPE swap, and a commute before MAXPS. Kill rates are measured under
  goldens alone (G), goldens plus contributor tests (G+C), and T1+T2.
- **Proofs.** Each rewrite rule is checked by Z3 FPA or exhaustive binary32. The lockstep loop rule,
  extended to the unroll, rotation and peel shapes X0 finds, gets a written proof reviewed by a
  Prover from a different family. Lean comes later (DR-010).
- **Gate.** T1 accepts 100% of real variants with ≤ 30 proved rules and rejects 100% of FP-changing
  mutants. After fixes, no table/silicon mismatches remain, and there are zero false accepts.
- **Amber.** If 31–40 rules are needed, X2 gets one more week and is judged again.
- **Kill.** At the end of week 6, T1 still needs per-kernel `assumed` axioms, or more than 40 rules
  [P2 §10], or has made a false accept that is not traceable to a fixable table bug. N2 then dies,
  kernels carry `tested` evidence plus the hash corpus, and the project continues only if X1 and X3
  pass.
- **Honest reporting.** If G+C already kill every mutant T1 kills, the result reads "stronger
  evidence per build at lower cost", not "catches more bugs". Either way, X2 certifies C Hearth's
  existing kernels.
- **Cost.** $3–6k, ~40 h [inference], mostly reviewing table entries.

### 3.4 X3: one meaning regenerates the triplets (weeks 1–4)

- **Build.** A throwaway Python prototype of DAG-preserving schedule primitives, or Exo (MIT,
  emits C). Exo has no IEEE-exact mode [R05], so X3 uses only its DAG-preserving primitives. Either
  tool generates scalar, AVX2 and AVX-512 Q4 and Q8 matvec C from one meaning.
- **Run.**
  - Link the output into a scratch Hearth through `hx_kernels`.
  - Run `test_quant` (117,681 checks [R11]) and `test_isa_identity`.
  - Measure, interleaved and load-gated (through the X4 service once it is live, otherwise with
    ≥ 10 runs per arm [P5]), with **each release compiler**: MSVC for win-x64, and Clang for the
    Linux release. On this Windows desktop the Clang arm is a clang-cl build with the release flags,
    labelled as a proxy for the SysV build. MSVC's zmm register allocation and scheduling differ from
    Clang's, so parity under Clang (Exo's usual path) says little about the shipping Windows build.
  - **Primary metric:** single-thread, L2-resident Q4 and Q8 matvec throughput per ISA, pinned as in
    [06](architecture/06-forge.md) §6.7.
  - **Secondary guard:** Qwen3-30B-A3B Q4 decode tok/s. Decode is bandwidth-bound, with cores about
    97% idle [R08], so it cannot detect a codegen regression. Passing decode alone does not establish
    generator parity.
- **Gate.** Bit-identical output; the primary metric non-inferior at δ = 3% under every release
  compiler; decode non-inferior as a guard. Schedule text is at most 30% of the hand-written lines.
  If X2 is ready, T1 also accepts the generated variants.
- **Amber.** 90–97% of hand-kernel speed on the primary metric under any release compiler: the gap
  goes to M2 as a named item with gap attribution.
- **Kill.** Still < 90% after two weeks of tuning, or bit-identity needs primitives that do not
  preserve the DAG. "One generator" then leaves the plan, and kernels become explicit-SIMD `.mith`
  checked by T1.
- **Cost.** $1–3k, ~20 h [inference].

### 3.5 X4: evaluator-integrity kit (weeks 0–6)

X4 tests the judge before there is anything to hack [P4 §10]. Every part of it is useful to C
Hearth whatever happens to Mithril.

- **Measurement service v0.** The runtime owns the clock and joins all threads and I/O before
  stopping it. Fresh allocations are poisoned, and every run carries a hardware fingerprint. Runs use
  ABAB interleaving behind a load gate, with a stationarity check, on a quiet-machine profile (power
  plan, core parking, CCD pinning, Defender and indexing exclusions, NVMe thermal and SLC state).
  Results are anytime-valid e-values with α-budget accounting, output as `Quantity<Unit, Origin>`.
  `mithc profile measure` (STREAM per CCD and all-core, NVMe request-size × QD grid) supplies the
  phys and emp bounds ([06](architecture/06-forge.md)).
- **Sandbox.** A Windows Job Object with no network, read-only goldens and traces, and
  supervisor-held limits.
- **Planted-hack suite.**
  - (a) A catalogue batch taken from documented hacks [R01, RV: D2-E]: faked logs, removed markers,
    unwatched async timing, uninitialised-buffer reuse, timer overwrite, sandbox-flag flips,
    wrong-shape scoring, symlink/case-twin/8.3 golden-gate bypass, FTZ/MXCSR writes, hard-coded
    outputs, lucky-run selection, and physics-violating wins.
  - (b) A blind batch, written after the kit is hash-frozen by an Adversary from a different model
    family. This answers the judges' point that P4's version of this gate was circular.
  - Every hack declares the stage that must catch it. Static-type and binary-T0 hacks re-run at M4.
- **Policy Forge on a scratch `hearth.sim` (F1-sim).**
  - Eviction and prefetch candidates run behind an `hx_policy` shim that the simulator mirrors
    [P4 §9.2].
  - The objective is NVMe bytes/token and stall time, never hit rate.
  - The MIN-bytes oracle is validated first, against brute-force OPT on small traces. Hearth's own
    Belady bounds were beaten twice by bugs.
  - Replay pruning applies only to `timing_blind` policies; prefetch gets MIN bounds only
    [RV: D3-ii].
  - All results are labelled SIMULATED.
- **Tombstone import and replay.**
  - Lookahead depth 4: hits rose 73% → 86%, but decode fell 13.0 → 10.0 tok/s (measured).
  - ADR-0004's decayed LFU (decay 0.995): LRU beat it by 8–13 hit-rate points in trace replay
    (simulated) [R01]. In the engine the winner depended on the niche: LFU 0.995 was the worst
    policy at every cache size, LRU won at 1 GiB without prefetch, and LFU 0.9 won at 2–4 GiB and
    whenever prefetch was on (measured [R02 §10]). The tombstone's scope is therefore cache size ×
    prefetch on/off, not a global verdict.
  - Every rejected idea in the design inputs, entered as a design-level tombstone (these feed
    DECISIONS.md).
  - A `mithc revisit` prototype that evaluates their triggers.
- **Optional.** A clean quiet-machine head-to-head of C-Hearth against llama.cpp (an open Hearth
  item). It is context only, not a gate.
- **Gate.**
  - 100% of both hack batches are caught at or before their declared stage (IF-5).
  - **A/A calibration (superiority null).** Across at least 100 identical-binary sessions on the
    microbenchmark run type, the superiority e-process reaches 20 in **≤ 2** of them [target].
    Ville's bound is 1/20 when samples are exchangeable, so this tests exchangeability on this
    desktop. The exact binomial rule passes a true 5% false-alarm rate with probability ≈ 0.12 and a
    true 8% rate with ≈ 0.01; a sound evaluator at a true 1% passes with ≈ 0.92 [inference]. (A
    "≤ 5 of 100" rule would pass a true 8% rate with probability ≈ 0.18.)
  - **Planted-regression calibration (non-inferiority null).** `hearth-c-ref` runs against itself
    with an injected slowdown of 3% and, separately, 4%: a calibrated spin whose realised ratio a
    separate long run confirms. The non-inferiority e-process must reach 20 in **≤ 2 of ≥ 100**
    sessions per level [target]. Sessions run to the amber limit N of §1 rule 4, so the calibration
    covers the longest a real parity gate can run.
  - **Time-to-pass at true parity.** The A/A sessions also run the non-inferiority e-process. Its
    median and 90th-percentile time to reach 20 are published per run type; they size the parity
    budget in §10.
  - End-to-end run types get ≥ 20 A/A sessions [target]: enough for σ_d and time-to-pass, not
    enough to test a 5% rate. Their gates rest on the microbenchmark calibration plus the
    per-session A/A sentinels ([06](architecture/06-forge.md) §6.3).
  - Throughput is published as candidates per quiet hour at MDE 5% and 2%; it sizes the M4 and M6
    campaigns.
  - The lookahead tombstone fires only when the simulated environment gains a VRAM tier, a second
    drive or NVMe bandwidth above 12 GB/s. ADR-0004's revisit condition, once encoded, fires on the
    recorded traces and the measured policy table per niche (cache size × prefetch), and the scoped
    verdicts it produces match the measured winners above, not a global switch to LRU. Neither
    fires on the pre-registered irrelevant perturbations.
  - The prune pilot is reproduced with zero audit violations. The original pilot pruned
    41/32/26/16% per cache size and 66% jointly (simulated) [RV: D3-ii].
- **Kill.** Any accepted planted hack stops all Forge work: no Forge result counts until the
  evaluator is redesigned and the suite passes again. This does not kill the language. A failed A/A
  calibration bars every superiority gate, and a failed planted-regression calibration bars every
  parity gate, until the cause is fixed and the calibration passes again on fresh sessions (see D0-8
  and D-22).
- **Cost.** $3–8k, ~40 h [inference]. Quiet-machine hours are in §10.

### 3.6 Core-calculus note (weeks 0–5)

- **Deliverable.** The core calculus in [01-language](architecture/01-language.md):
  - judgement forms;
  - effects typed as authority and grades as fidelity and determinism;
  - the non-escaping kind for closures and iterator adapters;
  - projections and `deterministic(by: E) { }`;
  - deterministic trap semantics (01 §12): a trap ends its fail domain, never unwinds and never
    aborts the host; the lowest index wins in a `par for`, and a policy trap falls back to the
    default policy;
  - theorem statements for progress/preservation, capability confinement, `timing_only`
    noninterference and determinism.
- **Gate.** Every canonical snippet derives by hand and is accepted by `mithi`. Every Tier 0 rule
  traces back to the note. A Prover and an Adversary from another model family review it, and the
  Owner signs it.
- **Amber.** An idiom that X1's reference solutions need cannot be typed. It becomes a Dc rule, and
  X1 measures what that costs.
- **Narrowing.** If noninterference cannot be stated together with the trap fallback, the policy
  feature is redesigned before M4.
- **Cost.** $1–2k, ~20 h [inference].

### 3.7 The M0 verdict

D0 (§11) runs from week 0 and takes about 10 owner hours [inference]. In week 6 the Gatekeeper
applies the pre-registered rules, picks a row of §4, and the Owner signs. M0 in total costs
$16–36k and ~195 owner hours [inference], plus about 60–215 quiet-machine hours (§10). If σ_d is at
the high end and X4's calibration runs past week 6, the X4 verdict waits (amber); the other
verdicts do not.

---

## 4. Kill outcomes

The outcome classes:
- **STOP-L**: the language stops and the tools are kept.
- **NARROW**: work continues with one named claim removed.
- **HALT-F**: the Forge is frozen until it is repaired.
- **STOP-ALL**: the repository is archived with its tombstones, and its tools go to C Hearth.

Kills in later milestones are listed in §5.

| Outcome | Class | Consequence | What survives |
|---|---|---|---|
| X1 kill, or M1 kill (DR-017) | STOP-L | Mithril becomes checker, ledger and tooling over Rust/C through `mithc lift` | T1/T2 over C objects, ledger, revisit engine, measurement service |
| X1 kill **and** X2 kill | STOP-ALL | Neither the surface nor the checker carries weight | Census, partial table, measurement service, hash corpus, tombstones |
| X2 kill **and** X3 kill | STOP-L | No kernel benefit; format, store and ledger alone do not justify a language [P5 §10.1] | As in the first row, without validated kernels |
| X2 kill alone | NARROW | Continue only if X1 and X3 pass. N2 dropped; kernels `tested` plus the hash corpus | Everything else |
| X3 kill alone | NARROW | Kernels written as explicit-SIMD `.mith`, checked by T1 | Everything else |
| X0 narrowing | NARROW | Object audit deferred; the C compiler stays trusted for kernels | Everything else |
| X4 kill | HALT-F | No F1 claim until the evaluator is redesigned; the language continues | All except Forge results |
| Owner rejects a Mithril-sourced core (D0-1) | STOP-L | Re-scoped to tools over C | As in the first row |

Here is the tombstone an X1 or M1 kill would write:

```text
tombstone standalone_surface {                      // written only if the X1 or M1 kill fires
    verdict: vp1_gap | cabw_gap                     // whichever fired (or both), copied from the signed report
    scope:   { arms: {mithril_t01, rust}, suite: x1_heldout@sha256:…, models: {family_a@v, family_b@v} }
    class:   F                                      // fundamental under the assumption "today's model priors"
    revisit_when: harness.model_generation > scope.model_generation
               || harness.context_window_tokens >= 4 * at_burial.harness.context_window_tokens
    evidence: ledger:sha256:…
}
```

The second trigger reopens the line when agents can hold far more of the language in context. It
does not touch the Tier 0 card, whose ≤ 8 KB budget stays CI-enforced; the factor 4 is [target].

---

## 5. Milestones M1–M7

The full stage gates and their order (S0 → S6b, DR-020) are in
[07-hearth-port](architecture/07-hearth-port.md). Costs are API dollars and owner hours
[inference].

| # (months) | Deliverable | Gate (all required) | Pre-registered kill | Cost |
|---|---|---|---|---|
| **M1** Front end + agent protocol (1.5–3.5) | mithc v0: parser/formatter, Syntax → HIR → THIR → MIR, checker (types, effects, second-class references, projections, non-escaping kind, static traits, layouts, ranges), MIR → strict C11, `export abi`. Verbs `--json` with `next`; MCP server, SARIF. Tier 0 card in AGENTS.md, project card, Tier 1. Mithril MultiPL-E (≥ 150 tasks). `mithi` differential tests, `mithc lift` v0, local ledger v0. A **fresh sealed M1 held-out batch** (≥ 60 items, more if X1's σ_ta requires), authored by a model family different from the card editors', plus ≥ 15 anchor items from X1's held-out set for IRT linking. Surface Lab pilot on D1–D5 ([05 §14](architecture/05-agent-protocol.md)). v0 lever ablations as a fractional-factorial design on shared runs (§10). Scalar S1 | Scalar quant port passes `test_quant` via the seam. VP@1 with full diagnostics ≥ the X1 result + 5 points, on a common IRT scale: the anchors and the Rust arm (pinned model versions) link the two batches, and anchors are never scored for the gate. One-definition re-check < 300 ms at 30k lines. Edit-protocol ablation against `str_replace` + format-on-save reported. S1 comprehension precondition | DR-017: VP@1 gap to Rust > 10 points **or** CABW > Rust's (one-sided test, [05 §13](architecture/05-agent-protocol.md)) → STOP-L. Gate missed by > 6 weeks → STOP-L [P5]. Edit protocol shows no gain → it leaves Tier 0 [P1 §10] | $15–39k, 180 h |
| **M2** Kernels (3.5–5) | KIR, DAG-preserving schedules, `mithcheck` T1/T2, Zen-5-fuzzed table. Object audit (B1.5) of the ~20 hot kernels. `canon` library (`sum16`, `dot16`, `sum_seq`, `canon_v1::expf`, `cr::sinf/cosf`). `format` types with integer view. `restrict` and out-parameter lowering (DR-027). Cost signatures and `mithc explain` v0. S1 complete | S1 gates (`test_quant`, ISA/batch identity, quantiser byte diff, hash corpus). `validated` + audited evidence for every dispatched variant (DR-021). Non-inferior at δ = 3% on S1's confirmatory set under every release compiler (§10). All `numerics_v1` FP mutants rejected with ≤ 30 rules. Audit coverage recorded as a scoped verdict: ≥ 95% puts the GPU tier before any emitter (DR-008/009) | T1 certifies < 90% of dispatched variants without `assumed` → drop validated identity and re-justify [P5]. Not non-inferior after 4 weeks of schedule search → C kernels stay behind the seam; Mithril's become oracles [P1 §10] | $10–24k, 110 h |
| **M3** Formats, ABI, ledger v1 (4.5–6) | `format` → total parser and writer; S2. ABI variance lattice. Ledger v1 (gate-signed fact files under `.mith/ledger/`, FREE/SEAL/AUTHORITY, blobs outside the repo; DR-019). Trigger language, `mithc revisit [--design]`, `ledger why --trust-base`. ADR-0004 revisit backtest over Hearth's git history (report, §8) | S2 gates (zero accept/reject diff on ≥ 10^6 generated files, zero `unsafe`; totality and safety `tested` by fuzzing, `mithi` differential and the golden malformed-file test, with `proof` only for the bounds obligations T2 discharges; §7 B1). Replayed `read_errors`-class ABI break rejected at compile time. X4 tombstone replay identical on ledger v1 | Parser > 1.3x C parse time **or** accept/reject diff ≠ 0 after 3 weeks → keep the C parser and write a tombstone [P5] | $7–15k, 65 h |
| **M4** Concurrency, store logic, policy space (5.5–7.5) | `std_platform` v0 (`Mutex<T>`/`with_lock`, `Condvar`, Arena → `SlabBuf`, `Frozen<T>`, scoped pool) over the existing C platform functions. `deterministic(by:)` with grants. `timing_only` + hint ports. Binary-level T0 confinement. Store-core certificate O1–O5, graded `validated` by BMC + chaos suite (DR-010). Engine and `hearth.sim` share the same policy code. Permutation scheduler. S3, S4 logic. F1-live Forge | S3/S4 gates: dispatch latency non-inferior (~0.75 µs at 16 threads, measured [R11]); demand reads non-inferior to `hearth-c-ref` at δ = 3% (7.16 GB/s measured [R11], context only); 2 GiB-cache decode non-inferior (13.02 tok/s measured [R11], context only); golden scheduling independence; TSan clean. Chaos kill 1.0. ≥ 100 type-checked policies bit-identical. Static and binary-T0 planted hacks 100% rejected. Zero user `unsafe` outside `std_platform`; audited `unsafe` ≤ 1,500 lines across OSes. 144-candidate prune grid with 0 false prunes | **Hard stop:** any type-checked `timing_only` policy changes logits → HALT-F until the theorem is repaired and a regression test admitted. User `unsafe` in > 2 places, **or** dispatch > C + 10% that cannot be closed → reopen the memory model (amber at 1–2: audited primitive by ADR) [P5]. Any false prune in ≥ 60 audits → replay bounds demoted to `est` [P2 §10] | $12–28k, 140 h |
| **M5** Full port (7.5–9.5) | S5 forward pass. S6a: `hearth.h` exported exactly (19 functions, 3 structs, + `struct_size`). S6b: platform layer as audited `unsafe`, including large pages ([04](architecture/04-toolchain.md)). C core retired; `hearth-c-ref` kept permanently | Full golden suite, hash corpus, 512-step real-Qwen3 decode hashes. tok/s non-inferior at δ = 3% on the confirmatory set (cached, 2 GiB, 2,048-token prefill); 4/8 GiB and 512-token prefill screened and escalated per §1 rule 4. Python toolkit unchanged. Non-kernel logits-path code `tested` + corpus, labelled (DR-021). Bounds-check tax within budget; no hidden memcpy > N on hot paths. B1 complete | A confirmed regression > 3% (upper confidence bound below 0.97) unclosed in 4 weeks, **or** a hash mismatch traced to language semantics → ship the hybrid (Mithril kernels, parser, store logic; C forward pass) [P2 §10]. More than 2 modules miss parity → re-plan with a tombstone [P1 §10] | $12–28k, 110 h |
| **M6** Measured benefit (8.5–10.5) | Forge v1 campaigns. F1: policies, exact schedules searched in the certified schedule space (prefill VNNI tiles; the attention value pass, a portable loop at 18.0 GMAC/s against a bit-identical register-blocked AVX-512 prototype at 94 GMAC/s, both measured [R11]), lossless relayouts. Landing that prototype, or Hearth's planned expert-major VNNI prefill (Hearth task R05 [R11]), is a C-Hearth gain and does not count for B3 (§7). F1-A: card atoms, diagnostic templates, pack ranking, scored by the held-out harness. Grants (DR-015). B2 A/B. Benefit report | B3 certified gain and B2 non-inferior (§7). F1-A minimum met, or its amber epoch running (§8) | No candidate beyond noise after 2 campaigns (≤ $10k) → Forge deprioritised to revisit-only, with tombstones (§8). B2 inferior → port stays an artifact and Hearth keeps C [P5] | $20–55k, 110 h (§10) |
| **M7** Edition 1 + growth (10.5–16) | Syntax freeze, normative manual ≤ 30k words plus machine-readable core, Mithril MultiPL-E published. Triggered items (§9): GPU tier if D0-6 says yes, Lean for the T1 rules, `@bind(load)`, NEON. Self-hosting decision (DR-026) | DR-017 M1 thresholds hold on a **rotated** held-out suite. A fresh agent with Tier 0+1 and the project card implements an open Hearth item to the evidence policy at TPV ≤ 1.2x Rust [P1 §10]. GPU (DR-022): canonical expert GEMV ≥ 0.6x llama.cpp MMVQ on the same card, **and** end-to-end ≥ 2x CPU-only (measured), **and** logits hash-identical across placements. ptxas/driver JIT in the trust base, SASS graded `tested` | Rotated K1 fails → features freeze, the Surface Lab re-runs, no Edition 1. GPU amber at GEMV 0.5–0.6x MMVQ: one relayout campaign (scales split from the 34-byte blocks), then re-judge. GPU kill, split because rule C2 ([02 §14](architecture/02-compute.md)) forbids `device(t)` values in placements decided at run time and a Qwen3 expert tier is cache-driven: *speed miss with identity intact* (GEMV < 0.5x, or end-to-end < 2x) → the tier stays an opt-in `cross_device` profile, never a default, with a class-H tombstone and a hardware trigger; *identity failure* that cannot be repaired → only a statically placed, load-time-fixed GPU plan may run, as an opt-in `device(t)` lane with per-plan goldens, and no cache-driven expert placement | Per item |

**Comprehension preconditions** [P1 §9]. Before a stage starts, its nearest task families must stay
within 10 points of Rust on VP@1, with CABW no higher than Rust's [target]. A miss delays the stage
(amber) and triggers work on the card or diagnostics. It is not a kill. Stage boundaries double as
upstream rebase windows ([07](architecture/07-hearth-port.md)); at each window, performance gates
re-run only where the measured binary's closure hash changed (§1 rule 4).

| Stage | S1 | S2 | S3 | S4 | S5 | S6a |
|---|---|---|---|---|---|---|
| Families | T-Q4, T-ACTQ | T-FMT | T-CTRL | T-STORE, T-EVICT | T-NORM, T-ROUTE | T-CTRL |

---

## 6. Beyond M7

Everything here is later or by-trigger.

- **F2 compiler heuristics** (DR-016). Work starts after M5, with translation validation in CI.
  - Gate: an evolved heuristic beats the hand-written one on held-out shapes on two
    microarchitectures, with zero translation-validation failures.
  - Kill: if the gain is lost in two consecutive rounds, heuristics freeze and rules continue
    [P4 §10].
- **F3 editions.** Changes are human ADRs backed by harness evidence. Migration must preserve the
  corpus, including tombstone recipes [P4 §8.9].
  - Kill: if no delta improves VP@1 within 2 epochs, F3 is limited to stdlib, docs and diagnostics.
- **Fm.** Meta-level changes go through counterfactual replay (§9).
- **Cross-device beyond expert GEMV.** This needs validated canon/cr PTX transcendentals (each
  target re-validated exhaustively over binary32, no canon bump) and a fixed-chunk attention order.
  The attention order redefines an existing op-DAG, so it is the major version `canon.v2`
  (by-trigger), the first use of the major-version migration protocol
  ([03](architecture/03-trust.md) §12, [02](architecture/02-compute.md) §15.4, DR-022). The
  additive `canon.v1.1` (MXFP4 order, later) needs no golden reset.
- **Kimi-K3.** KDA chunkwise scans under canon ([02](architecture/02-compute.md)). The snapshot API
  and the overlay API are designed together (DR-025).
- **Living models** are later (post-v1, DR-025). **Visual generation** is later (v2+, DR-024).

---

## 7. Pre-registered benefit claims B1–B3

The port succeeds only if every B1 and B3 item holds and B2 is non-inferior [P5 §9.1, extended].

**B1 Assurance.**
- Every kernel variant dispatched in release holds `validated` bit-identity evidence on the audited
  object. Today these kernels are only tested.
- The generated parser has no `unsafe`. Its totality and safety (INV-FMT/SAFE) are `tested`: fuzzing,
  the `mithi` differential and the golden malformed-file test. Only the bounds obligations that T2
  discharges are graded `proof`, at source level. The parser is generated by an untrusted `mithc`,
  checked by a front end graded `tested` (DR-010) and compiled by a C compiler that stays trusted
  for control-heavy code ([04](architecture/04-toolchain.md) §12), so no stronger claim is
  delivered. An F0 re-check of the derived parser (EverParse-style obligations that `mithcheck`
  re-checks) would lift it to `proof`; it is neither planned nor budgeted.
- At least 5 live Hearth defects are closed by a compile-time rule or a certified check:
  - mirror full-content hashing (O4);
  - the `hx_store_heat` pointer race, which second-class references cannot express;
  - ABI `struct_size`;
  - the MXCSR invariant: the default MXCSR is set on entry and restored on exit at every
    `export abi` and `hx_*` entry, and set and asserted at pool-worker start. It is a
    runtime-checked trust-base entry, not an axiom and not a discharged obligation
    ([ARCHITECTURE](ARCHITECTURE.md) §6.3, [04](architecture/04-toolchain.md) §9.2);
  - heat-decay drift (0.9 vs 0.995), caught by a decision-constant lint.
- On `numerics_v1`, T1+T2 kill at least as many mutants as G+C, plus at least one class G misses.
  *Fallback wording:* if G+C already match T1, the report reads "stronger evidence per build at
  lower cost".
- `timing_only` confinement is checked on the binary. Every tool-printed number carries its origin.

**B2 Agent non-inferiority.**
- Suite: sealed Hearth tasks (bug fixes, a new kernel variant, a policy change, a format extension).
- Arms: C-Hearth, Mithril-Hearth, and C-Hearth with Mithril tooling (the fallback).
- Claim: VP@1 ≥ C-Hearth − 3 points, cost per solved task ≤ 1.2x, and CABW no worse, using DR-017's
  statistics.
- The 3-point margin is the most expensive measurement in the plan: about 4k attempts per arm by 1/δ²
  scaling [inference], about 12k attempts and $6–24k in all (§10). If that proves unaffordable, the
  margin widens before collection, never after. The Owner chooses before B2's pre-registration:
  3 points with M6 at $20–55k, or 5 points (about 1.5k attempts per arm) with M6 at $16–40k
  [inference].

**B3 Performance.** Parity (non-inferior at δ = 3%) at every confirmatory configuration (§1 rule 4,
§10), **plus** at least one certified gain promoted through a certified space: ≥ 5% tok/s **or**
≥ 10% fewer NVMe bytes/token on a named configuration, with e ≥ 20 and zero output changes. Two
conditions keep the gain a claim about the language rather than about engine tuning:
- **Found, not ported.** The Forge found it by search inside a certified space (the schedule space,
  the `timing_only` policy space or a lossless relayout space). A hand port of an existing C
  prototype does not count.
- **Against today's C.** It is measured against C Hearth `main` at the time of the claim (a fresh
  `hearth-c-ref@<tag>`, [07](architecture/07-hearth-port.md) §6), including any C version of the
  same algorithm that exists by then, not only against the frozen S0 tag. Where the candidate can be
  written in C, the report also runs a "C + same algorithm" arm and splits the gain between search
  and code generation.

Known C prototypes are C-Hearth gains, whatever language lands them: the attention value pass
(portable loop 18.0 GMAC/s against a bit-identical register-blocked AVX-512 prototype at 94 GMAC/s,
both measured [R11]) and Hearth's planned expert-major VNNI prefill (Hearth task R05 [R11]).

These targets are modest on purpose. Cached Qwen3-30B-A3B has about 1.5x of honest CPU headroom: a
ceiling of ≈ 34 tok/s at 77 GB/s measured, against Hearth's 19–22 tok/s (noisy). Speed comes from
bytes, placement and scheduling, not syntax. No absolute tok/s gate exists, because plain-C tuning
could meet one without proving anything about the language.

The revisit engine's benefit is pre-registered in §8 rather than as a port claim. It is not called
B4, because B4 already names the copy-and-patch JIT backend (D-04).

---

## 8. Minimum Forge benefit per milestone

The prior: eviction is worth a few points at most, and prefetch timing is the bigger lever
[RV: D2-A]. Compute-bound schedules are where kernel search pays off. The GPU tier is the largest
lossless lever (simulated 3.6–4.8x for in-RAM MoE [G03]). If the durable win turns out to be
assurance rather than speed, the report says so.

**A tombstone is the record of a miss, never a pass.** Every minimum below can fail. When one does,
the miss is written as a scoped tombstone and the "If missed" action applies. This is the single
authoritative table; [06 §13](architecture/06-forge.md) links here and adds only rationale. Levels
are named F1-sim (simulator), F1-live (engine) and F1-place (CPU/GPU placement), so that none can be
misread as F1-A, the agent-interface level.

| Milestone | Line and level | Minimum [target] | If missed |
|---|---|---|---|
| M0 | Policy, F1-sim (SIMULATED) | *Readiness:* σ_d published per run type and niche; the [06](architecture/06-forge.md) §7.6 acceptance tests pass; the prune pilot is reproduced with zero bound violations. *Benefit:* a policy beats LRU on simulated NVMe bytes/token or stall time by ≥ the pre-registered MDE on sealed held-out traces. (An accepted planted hack is X4's HALT-F, §3.5, not a Forge miss) | Readiness miss: no M4 campaign until fixed. Benefit miss: the policy line enters M4 as a hypothesis with its campaign budget halved |
| M2 | Schedule, F1 exact schedules | A T1-validated schedule, found by search inside the certified schedule space (not a hand port of a C prototype, §7 B3), with a measured gain at e ≥ 20 against C Hearth `main` on a compute-bound configuration (the T > 1 prefill matmul in S1's scope), recorded as a ledger fact (no promotion before grants exist, M6; DR-015, D-09). Assurance, every dispatched variant `validated`, is M2's gate, not a Forge benefit | Schedule search moves to M6 with its budget unchanged |
| M3 | Revisit engine | *Readiness:* design graveyard imported; zero false fires on replay; the ADR-0004 backtest reported (below) | Re-gated at M5; revisit spending limited to the audit slice until it passes |
| M4 | Policy, F1-live | *Safety:* ≥ 100 type-checked policies bit-identical in one golden run; the chaos suite kills 100% of seeded core mutants; counters = replay for every `timing_blind` configuration; zero false prunes in ≥ 60 audits on the eligible part of the 144-candidate grid. *Benefit:* the best measured policy beaten at ≥ 1 cache size, with e ≥ 20 on tok/s or stall time, or by ≥ the MDE in NVMe bytes/token (deterministic count, `timing_blind` configurations only) | Safety: per M4's kills in §5 (a logits change → HALT-F; a false prune → replay bounds demoted to `est`, the Forge continues). Benefit: policy budget halved for M6 |
| M4–M7 | Revisit | The revisit benefit claim below | Revisit spending drops to the audit slice; the null result and its cost are published |
| M6 | Policy and schedule, F1 | B3's gain (§7): found by the Forge in a certified space; ≥ 5% tok/s (e ≥ 20) **or** ≥ 10% fewer NVMe bytes/token (deterministic count) on a named configuration, against C Hearth `main`; zero output changes [P5 §10.2] | None after 2 campaigns (≤ $10k [inference, P5]) → policy and schedule lines tombstoned; the Forge goes revisit-only; B3 fails (§7) |
| M6 | Agent interface, F1-A | ≥ 1 atom or scaffold delta, kept after leave-one-atom-out, that raises held-out VP@1 or cuts tokens per verified pass (TPV) by ≥ 10% at non-inferior VP@1, with the CI excluding zero on ≥ 2 model families, and CABW not worse | Amber: one more epoch, judged at M7. No gain in 2 epochs → F1-A frozen; atoms tombstoned with model-generation triggers |
| M7 | F1-A, F1-place | F1-A gains hold on the rotated suite. If the GPU tier exists, a placement plan is ≥ 2x CPU-only end-to-end (measured) | F1-A frozen; GPU per DR-022 |

**Rule.** Two consecutive misses on the same line cap that line's spending at the background audit
slice. The lines are policy (M0 → M4 → M6), schedule (M2 → M6), revisit (M3 → M4–M7) and agent
interface (M6 → M7). The capped line becomes a tombstone with triggers: a new hardware fingerprint,
a second drive, a VRAM tier, or a new proposer model generation. When every line is capped, the
Forge as a whole runs revisit-only.

**Revisit benefit claim.** Revisiting unfruitful spaces is the owner's central idea, so it gets a
positive claim, not only acceptance tests. Over M4–M7 the benefit report gives:
- tombstones re-tested through fired triggers and through the audit slice, counted separately;
- the revival rate per failure class (H, T, S, E, V, C, X, F);
- the Forge budget revisit consumed: 20% of the split plus the 10% audit slice [inference,
  [06](architecture/06-forge.md) §4.5].

Minimum [target]: at least one revived idea, from a trigger or the audit slice, reaches a niche
elite or a promotion by M7. On a single desktop, H-class triggers will rarely fire, so most of the
yield is expected from the audit slice and from E- and V-class triggers (new proposer models,
evaluator changes) [inference]. If no revived idea qualifies, the pre-registered null is published
with its cost.

**Backtest (M3, report only).** Hearth's git history is replayed as an event stream: would
`mithc revisit` have re-opened ADR-0004's decayed LFU before the manual finding? The correct answer
is niche-scoped [R02 §10]: re-open everywhere LFU 0.995 lost, and produce verdicts that match the
measured winners (LRU at 1 GiB without prefetch, LFU 0.9 at 2–4 GiB and with prefetch), not a
global switch to LRU. One historical case cannot carry a powered gate, so it is reported, not
gated.

---

## 9. Deferral register

Each trigger is checked by the Gatekeeper and recorded in the ledger. Reserved grades exist in the
types and the schema from v0 ("reserve the lattice").

| ID | Deferred item | Status | Trigger |
|---|---|---|---|
| D-01 | `dyn` traits, specialisation, async, user macros | by-trigger | ≥ 10% of held-out failures cite the missing construct, **or** ≥ 3 port modules duplicate code that generics + `comptime` cannot share [P5] |
| D-02 | User effects, one-shot handlers | by-trigger | A Hearth requirement that stdlib configuration cannot meet |
| D-03 | `Code<T>` quotes | by-trigger | A required generator that meaning + schedule + `comptime` cannot express |
| D-04 | `@bind(load)`; then copy-and-patch JIT (B4) | by-trigger | A C experiment shows ≥ 10% decode or prefill gain [inference threshold, P5]. The JIT follows only if the AOT variant count cannot be shipped |
| D-05 | Direct x86-64 emitter (B3) | by-trigger | The audit finds an unpinnable compiler rewrite, **or** a ≥ 5% kernel gap attributable to codegen. Never for decode GEMV. Ordering rule: if M2 records audit coverage ≥ 95% and D0-6 is yes, D-06 comes before this item (DR-009) |
| D-06 | PTX expert tier; VRAM tier live; `device(t)` producible | by-trigger | D0-6 yes, INV-DEP ruling (`nvcuda.dll` as an OS API), and the canonical GEMV prototype measured [G03]. Audit coverage is not a precondition: it only orders D-06 before D-05 (DR-009) |
| D-07 | T3 certificates; `real(bound)` and `approx` producible | reserved | The first owner-approved non-exact path (MLA bound, tensor-core mode, lossy experts) |
| D-08 | Lean: Core mechanisation; T1 rules and store-core theorem | by-trigger / later | T1 rules and certificate format stable for 2 months, **or** any T0/T1 soundness bug. Until then: Z3/exhaustive checks and BMC (DR-010) |
| D-09 | Second independent T1/T2 checker | by-trigger | Before the first grant or ADR that rests on T1 evidence (expected M6), or after the first T1 soundness bug |
| D-10 | Full LSP | by-trigger | Humans edit `.mith` regularly, **or** an A/B shows agent benefit [P5] |
| D-11 | Hearth-hosted proposers, constrained decoding, `hearth.h` sampler hook | by-trigger | Out-of-tree type-mask benefit shown, **and** never co-scheduled with measurement (DR-023) |
| D-12 | Incremental Datalog Fact Plane engine | by-trigger | > 20 custom lints, **or** trigger scans exceed the edit-loop budget |
| D-13 | SEAL sequencer, conflict holes, I-confluence; ledger fact packing | by-trigger | Semantic conflicts that stale-evidence detection misses; git on `.mith/ledger/` exceeds the CI budget |
| D-14 | Full QD archive (CVT-MAP-Elites, PATA-EC, POET); Fm replay | later | A second hardware class enters the archive; ≥ 2 archived campaigns plus a proposed selection change |
| D-15 | F2 compiler heuristics and rules | later | M5 passed, translation validation in CI, a second microarchitecture (DR-016) |
| D-16 | Commit-reveal mutant markets, measured role independence | by-trigger | Specs authored at scale by agents |
| D-17 | NEON/SVE/AVX10.2 schedules | by-trigger | Owner priority or hardware. Until then arm64 runs portable code, `tested` + corpus |
| D-18 | Weight overlays, living models | later | Owner asks for adapters (DR-025) |
| D-19 | Cross-device attention and transcendentals | later | DR-022 passed and the `canon.v2` migration (fixed-chunk attention, §6) approved |
| D-20 | Visual-generation primitives | later (v2+) | GPU backend exists (DR-024) |
| D-21 | Self-hosting | later | Decision record after M7 (DR-026) |
| D-22 | Second measurement machine | by-trigger | A/A or planted-regression calibration fails, **or** throughput falls below campaign demand, **or** the parity-gate quiet hours of §10 exceed the available windows, **or** the void rate exceeds its declared bound, **or** quiet windows conflict with the owner's use (D0-8), **or** F2 starts (DR-016) ([06](architecture/06-forge.md) §6.9) |
| D-23 | Independent kernel-subset extractor in `mithcheck`: re-derives the op-DAG and T2 obligations from `kernel fn` source, removing front-end elaboration from the trust base; within T1's ≤ 3,500-line cap ([03](architecture/03-trust.md) §14) | by-trigger | Any elaboration bug found that changed a KIR DAG, **or** before the first grant or ADR that rests on T1 evidence (with D-09). Until then the elaboration of exact meanings into KIR, comptime included, is a trusted code component with code floor `tested`, mitigated by a second comptime evaluation path ([03](architecture/03-trust.md) §3.4, §14), so DR-021 holds |

---

## 10. Cost and owner hours

All figures here are [inference], at low to medium confidence. They take P5's estimates
[P5 §10.2] and add deltas for the grafted scope:
- M0: X0, X4 (with the planted-regression calibration), the core note, and X1's larger suite, extra
  arms, tooling kit and checker precondition;
- M1: the fresh sealed held-out batch, the Surface Lab pilot and the lever ablations;
- M3: the revisit engine and the ADR-0004 backtest;
- M4: binary confinement and shared policy code;
- M5: S6b;
- M6: F1-A, the tooling arm, and B2 at its full 3-point margin.

| Milestone | API | Owner h | Where owner time goes |
|---|---|---|---|
| M0 | $16–36k | ~195 | Table entries, X1 suite, pre-registrations, D0 |
| M1 | $15–39k | ~180 | Card, diagnostics, checker review, M1 held-out batch |
| M2 | $10–24k | ~110 | T1 rules, table, audit pipeline (TCB) |
| M3 | $7–15k | ~65 | Ledger signing, trigger language |
| M4 | $12–28k | ~140 | Audited `unsafe`, store-core certificate |
| M5 | $12–28k | ~110 | Platform layer, ABI, ADRs |
| M6 | $20–55k | ~110 | Promotions, B2 suite, report. $16–40k if B2's margin widens to 5 points (§7) |
| **M0–M6** | **$92–225k** | **~910** | ~10.5 months |
| M7 | per item | per item | Budgeted when each trigger fires |

**Measurement budget** [inference]. Agent measurement is priced explicitly, at $0.5–2 per agentic
attempt with a frontier model and $0.1–0.5 per short Surface Lab episode. The local family costs no
API dollars but costs machine hours, always outside quiet windows. Attempt counts follow
[05](architecture/05-agent-protocol.md) §13, where items buy more power than attempts. The API
figures sit inside the milestone lines above.

| When | Measurement | Items × attempts × arms × API families | Attempts | API |
|---|---|---|---|---|
| M0 | X1 held-out | 60 × 5 × 3 primary arms (Mithril, Rust, Rust + tooling) + 60 × 3 × 3 secondary arms, × 2 | ≈ 2.9k | $1.4–5.8k |
| M0 | X1 card iteration | 20 × 5 × 3 epochs × 2 Mithril arms × 2 | ≈ 1.2k | $0.6–2.4k |
| M0 | X1 local pilot | 10 × 3 × 2 arms × 1 local | 60 | $0; 5–10 machine h |
| M1 | DR-017 M1 kill: fresh batch plus anchors | 80 × 5 × 3 arms × 2, + 15 anchors × 5 × 2 arms × 2 | ≈ 2.7k | $1.4–5.4k |
| M1 | v0 lever ablations ([05](architecture/05-agent-protocol.md) §18) | fractional factorial on shared runs (resolution IV, 16 cells, up to 8 levers per design) × 100 screening items × 2; one confirmatory A/B per lever that shows an effect | ≈ 3.2k + 1.2k per confirmation | $1.6–6.4k + $0.6–2.4k each |
| M1 | Surface Lab pilot, D1–D5 | 390 episodes × 4 arms × 5 constructs [RV: D3-i] | ≈ 7.8k episodes | $0.8–3.9k |
| M1–M5 | Comprehension preconditions, 6 stages | per stage about 10 items × 5 × 2 arms × 2 | ≈ 1.2k | $0.6–2.4k |
| M6 | B2 at 3 points | about 4k per arm × 3 arms, families pooled | ≈ 12k | $6–24k |
| M6 | F1-A | leave-one-atom-out screening (fractional factorial, about 3k) + 2 confirmations at 120 × 5 × 2 arms × 2 | ≈ 7.8k | $3.9–15.6k |
| M7 | DR-017 thresholds on the rotated suite | as at M1 | ≈ 2.7k | $1.4–5.4k |

**Quiet-machine hours for parity gates** [inference]. Hours per attempt ≈ Σ over confirmatory
configurations of n × 4·t_run × c, with n = max(6, 12·σ_d²/δ²) blocks at δ = 3%
([06](architecture/06-forge.md) §6.6) and c ≈ 1.5 for NVMe cool-downs. The figures below use
illustrative σ_d; each stage's line is recomputed from M0's measured σ_d before its
pre-registration. A true 1% regression raises a configuration's hours by about 2.25x, because the
effective margin shrinks from 3% to 2%. Rebase windows re-run only gates whose closure hash changed
(§1 rule 4).

| Stage (milestone) | Confirmatory | Screening only | Quiet h per attempt, σ_d = 2% / 4% |
|---|---|---|---|
| M0 | X3 per release compiler; X4 calibration (300 microbenchmark sessions, ≥ 20 end-to-end A/A) | — | ≈ 60–215 in total, 8–27 nights of 8 h |
| S1 (M1–M2) | Q4 and Q8 single-thread matvec × AVX2, AVX-512 × 2 release compilers; cached decode | scalar variants, batch matmul | ≈ 1.5 / 5 |
| S2 (M3) | open time | — | < 0.5 / < 0.5 |
| S3 (M4) | dispatch round trip at 16 and 32 threads | WSL2 and crowded-pool cases | ≈ 0.2 / 0.5 |
| S4 (M4) | demand reads; 2 GiB decode | 4 GiB decode | ≈ 2 / 7 |
| S5 (M5) | cached decode; 2 GiB decode; 2,048-token prefill | 4 and 8 GiB decode; 512-token prefill (≈ 3 h more) | ≈ 2.5 / 9 |
| S6b (M5) | direct I/O | large-page arena variants | ≈ 0.5 / 2 |

With all six S5 configurations confirmatory, S5 alone would need about 18 h per attempt at
σ_d = 4%, before rebase re-runs; the confirmatory/screening split is what keeps the port inside the
quiet windows. If a stage's planned hours exceed its available windows, D-22 fires.

For scale, one DGM SWE-bench run cost about $22k (reported by the DGM authors [R01]). Owner review
is the binding constraint, concentrated in the trusted core (line budgets in
[03](architecture/03-trust.md)) and in ADRs. M0 is the peak at about 33 h/week; at 15 h/week it
stretches to about 13 weeks, and because kills are tied to deliverables no threshold changes.
Quiet-machine time is the second scarce resource: X4 measures it, the table above turns it into a
per-stage budget, and campaign sizes are derived from it. Hardware, such as a second measurement
box, is not costed.

---

## 11. Owner decisions D0

No agent may take these decisions. "Needed by" is the latest point before work blocks.

| ID | Decision | Recommendation | Needed by | If declined |
|---|---|---|---|---|
| D0-1 | INV-DEP / ADR-0001: may Mithril be the core's source? | Option A: checked-in C11, regenerated byte for byte by a pinned mithc in CI (DR-026). It needs a superseding ADR | End of M0 | STOP-L. Tombstone, trigger "owner ADR changes" |
| D0-2 | ADR-0010 specified transcendentals (`cr` or `canon_v1` per function) | Adopt before the S0 corpus (DR-014); goldens need no re-lock [G04] | S0 | libm drift risk; `parity::` shim fallback |
| D0-3 | S0 freeze, `hearth-c-ref`, hash corpus as maintainer golden tier | Yes, reproduced twice on the 9950X | M1's S1 | No bit-exact oracle, so no port |
| D0-4 | Normativity | NUMERICS.md and C stay normative through S6, then meanings are normative | S6 | Dual normativity with a drift check |
| D0-5 | Heat-decay value, `struct_size`, MXCSR invariant, mirror hashing or qualified INV-DET-1 | Decide now; land each before the stage that needs it | S4 / S6a | B1 defect items shrink |
| D0-6 | RTX 5070 in scope? `nvcuda.dll` as an OS API? Display on the iGPU (~1.5 GB of VRAM freed [G03])? | Decide by M5; the VRAM tier is reserved either way | M5 | CPU-only; the GPU becomes a tombstone |
| D0-7 | Forge authority: grant signer; `timing_only` defaults by ADR only (DR-015); unattended runs | Owner signs grants; defaults by ADR; unattended only inside quiet windows | X4 | Attended runs only |
| D0-8 | Measurement host | The desktop first; a second box by D-22 | M4 | Campaigns bounded by measured throughput |
| D0-9 | Owner key management ([03](architecture/03-trust.md)) | Offline or hardware-backed key with a written recovery path | X4 | No AUTHORITY facts, so no promotion |
| D0-10 | Budget, cadence, harness model families, quiet windows | Approve the M0 budget, including the measurement budget and quiet hours of §10; ≥ 2 frontier families + 1 local (a one-family pilot at X1, full from M1); B2's margin (3 or 5 points) before B2's pre-registration | Week 0 (B2 margin: before M6) | No M0 |
| D0-11 | Spec authority: sealing; different model families for Author and Builder; `validated` as an INV-VERIFY evidence class | Yes to all three | M1 | Maintainers write all specs |
| D0-12 | Pre-registration sign-off for every gate | The Owner signs each record before collection | Per gate | The gate cannot be evaluated |

---

## 12. Reviewer notes

- *Reviewer note:* the outline names B2 without a control arm. DR-017 uses Rust for cold-start
  writability. B2 compares against C-Hearth, Hearth's real alternative, and adds the
  C-Hearth-plus-tooling arm so the comparison against the fallback is kept.
- *Reviewer note:* B2's 3-point margin implies about 4k attempts per arm [inference], a cost that
  neither P5 nor the outline accounts for. §10 now budgets it, and the Owner picks the margin before
  pre-registration (D0-10).
- *Reviewer note:* §8 is the single minimum-benefit table. It merges 06 §13's stricter F1-A criteria
  (CI excluding zero, ≥ 2 families, CABW not worse) and its M4 safety items; 06 §13 should become a
  link plus rationale. P4's level names F1-a/b/d are renamed F1-sim/live/place to avoid confusion
  with F1-A.
- *Reviewer note (resolved):* B1 grades the derived parser `tested`, with `proof` only for
  T2-discharged bounds. ARCHITECTURE §13, 04 §12, 07 §2.6 and S2, and 01 §12.6 now use §7 B1's
  wording.
- *Reviewer note:* sibling documents should mirror two more changes here. Performance gates re-run
  at a rebase window only where the closure hash changed (refines 07 §6, step 5). The value pass and
  R05 prefill belong in ARCHITECTURE §12.6 as C-Hearth gains. *Resolved:* ARCHITECTURE §12.2's S4
  and S6b gates are relative, ARCHITECTURE §11.5 labels the ADR-0004 hit-rate result as trace replay
  (simulated) with a niche-dependent engine result, and ARCHITECTURE §13 carries B3's two conditions
  ("found, not ported"; "against today's C").
- *Reviewer note (resolved):* at X1 the Rust + Mithril tooling arm has only the M0 kit (§3.2);
  `lift` and full diagnostics join at M1. ARCHITECTURE §10.6 now says so.
- *Reviewer note (resolved):* the outline never maps v0/v1 to milestones. §1 rule 7 fixes a mapping,
  and every sibling document now uses it.
- *Reviewer note:* DR-018 sets e ≥ 20 for superiority only. This document applies the same threshold
  to non-inferiority, and calibrates the two nulls separately (A/A and planted regressions, §3.5).
- *Reviewer note:* DR-019 (one file per fact in git) inherits the PL judge's worry about many small
  files on Windows. D-13 adds a measurable packing trigger.
- *Reviewer note:* the outline's planted-hack suite has no independence requirement, and the judges
  called P4's version circular. X4 adds a blind batch.
- *Reviewer note:* the audited-`unsafe` cap is "per OS" in P2/P3 and "across OSes" in P5. The outline
  is silent, and this document keeps P5's stricter form. M4's kill (§5) is the one memory-model kill
  for every document: user `unsafe` in > 2 places (amber at 1–2) or dispatch > C + 10% unclosed
  reopens the memory model; audited `unsafe` ≤ 1,500 lines across OSes is a gate, not the kill.
