# Mithril architecture

*Master document, 2026-10-11. Audience: AI agents and the project owner. It stands alone; every
section summarises and links to a detailed document. Decisions are cited as DR-xxx
([DECISIONS.md](DECISIONS.md)), research dossiers as [R08], [G03] or [RV: node]
([research/](research/)), and design proposals as [P2 §n] ([design/proposals/](design/proposals/)).
Every number carries a label: measured, simulated, [inference] or [target]. Every capability
carries a status. Status labels map to milestones exactly as in [ROADMAP §1](ROADMAP.md), rule 7:
**v0**: in the mithc that ports Hearth (M1–M5); **v1**: present by Edition 1 (M6–M7); **later**:
planned after M7; **reserved**: in the types and schema but not producible; **by-trigger**: added
only when its register trigger fires. Milestone numbers are added where they help.*

**Summary.** Mithril is a small, Rust-shaped systems language whose primary users are AI agents.
Its novelty is deliberately not in its notation, because novel syntax measurably costs language
models; it is in what surrounds the text. Every definition carries typed claims backed by graded
evidence in one content-addressed ledger. Performance-critical code is one exact meaning plus
separately checked realisations (schedules, layouts, policies, placements). Whole classes of change
are certified output-preserving once (or checked mechanically per candidate), so agents and the
Forge (Mithril's built-in improvement loop) can search them with performance evidence alone:
Gödel-style proof obligations for invariance, Darwinian evidence for utility. Every rejected
idea is kept as a scoped tombstone whose machine-checkable trigger re-opens it when the hardware,
toolchain, model or evaluator changes. The language itself is governed by measured agent
comprehension rather than taste. Hearth, a zero-dependency C11 MoE inference engine, is the acid
test: its invariants become types, its golden suite the frozen evaluator, and its kernels and cache
policies the first certified spaces. Delivery is falsify-first: a five-to-six-week falsification
sprint of five cheap experiments (X0–X4) can stop or re-scope the project before the expensive parts
are built, and if the standalone language fails, its checker, ledger and format tools survive as
tools over C and Rust.

**Contents**

1. [Thesis and what is genuinely new](#1-thesis-and-what-is-genuinely-new)
2. [Field notes from the intended user](#2-field-notes-from-the-intended-user)
3. [Principles](#3-principles)
4. [The stack](#4-the-stack)
5. [The language at a glance](#5-the-language-at-a-glance)
6. [Exact numerics](#6-exact-numerics)
7. [The compute layer](#7-the-compute-layer)
8. [Evidence and trust](#8-evidence-and-trust)
9. [Compiler, backends and runtime](#9-compiler-backends-and-runtime)
10. [The agent protocol](#10-the-agent-protocol)
11. [The Forge and revisit](#11-the-forge-and-revisit)
12. [The Hearth port](#12-the-hearth-port)
13. [Roadmap summary and kill criteria](#13-roadmap-summary-and-kill-criteria)
14. [Refined seed ideas](#14-refined-seed-ideas)
15. [Non-goals](#15-non-goals)
16. [Top risks](#16-top-risks)
17. [Owner decisions](#17-owner-decisions)
18. [Glossary](#18-glossary)
19. [Sources](#19-sources)

Detailed documents: [01-language](architecture/01-language.md) ·
[02-compute](architecture/02-compute.md) · [03-trust](architecture/03-trust.md) ·
[04-toolchain](architecture/04-toolchain.md) · [05-agent-protocol](architecture/05-agent-protocol.md) ·
[06-forge](architecture/06-forge.md) · [07-hearth-port](architecture/07-hearth-port.md) ·
[ROADMAP](ROADMAP.md) · [SEED-REFINEMENT](SEED-REFINEMENT.md) · [DECISIONS](DECISIONS.md).

**Reading path for a cold agent:** this document (what happens next is §13.1) →
[ROADMAP](ROADMAP.md) → [01-language](architecture/01-language.md) →
[03-trust](architecture/03-trust.md) → the rest by task.

---

## 1. Thesis and what is genuinely new

### 1.1 Thesis

Mithril is a small, Rust-shaped systems language whose primary users are AI agents. Its novelty is
not notation (novel syntax measurably costs LLMs [G01, R03]) but what surrounds the text:

1. Every definition carries typed **claims** backed by graded **evidence** in one content-addressed
   **ledger**, so nothing about code is asserted without a checkable record.
2. Performance-critical code is one **exact meaning** plus separately checked **realisations**:
   schedules, layouts, policies and placements.
3. Whole classes of change are **certified output-preserving once**, or checked mechanically per
   candidate ("prove the space, not the candidate"), so agents and the **Forge** can search them
   with performance evidence alone. P2 calls this a "tractable Gödel machine". Stated precisely, it
   pairs Gödel-style proof obligations for invariance with Darwinian evidence for utility, and
   self-reference is limited to the agents' own scaffolds (F1-A) in v1 and to the compiler and meta
   levels later (§1.4).
4. Every rejected idea is kept as a scoped **tombstone** whose machine-checkable **resurrection
   trigger** re-opens it when hardware, toolchain, model or evaluator change (`mithc revisit`).
   This turns the owner's "revisit unfruitful problem spaces" into a mechanism.
5. The language itself is governed by **measured agent comprehension** (the Surface Lab and the
   cold-agent harness), not by taste.

Hearth is the acid test. Its invariants become types, its golden suite becomes the frozen
evaluator, and its kernels and cache/prefetch policies become the first certified spaces.
Delivery is falsify-first: a five-to-six-week falsification sprint runs five cheap experiments
(X0–X4). Three of them, X1–X3, can stop or re-scope the language, and X4 can freeze the Forge,
before the expensive parts are built (§13).

### 1.2 How the architecture was composed

Five design proposals were written in parallel and judged by three independent experts (a PL and
formal-verification researcher, a systems/performance engineer and an AI-agent researcher). All
three chose the same backbone (DR-001):

| Part | Taken from | What it contributes |
|---|---|---|
| Delivery backbone | [P5](design/proposals/P5-minimum-viable.md) Minimum Viable Mithril | Falsification sprint, deferral register with triggers, relative performance gates, C11 backend plus object audit, checked-in generated C |
| Trust constitution | [P2](design/proposals/P2-tractable-godel.md) Tractable Gödel Machine | Soundness vs completeness-for-members of certified spaces, claim-kind evidence, the promotion rule with an alpha budget, a code-only Gatekeeper, `abandon` |
| Agent protocol | [P1](design/proposals/P1-agents-language.md) The agent's language | Subset rule with C/Dc/D classes, `todo!` holes, hash-anchored edit-plus-check, fix applicability tied to evidence, journal-derived handovers, the comprehension harness |
| Physics and cost layer | [P3](design/proposals/P3-physics-first.md) Physics-first | Projections, bytes-per-tier cost signatures with phys/emp/est tiers, `format` types with integer views, conditional backend order, platform ported last |
| Tombstones and ledger transport | [P4](design/proposals/P4-living-forge.md) The Living Forge | Decidable trigger language, auto-derived triggers, design-level tombstones, file-per-fact ledger with FREE/SEAL/AUTHORITY classes, Löb-safe stratification, standing grants |

The rest of P4's Forge (compiler- and language-level evolution, meta-selection, living models) is
staged behind triggers. Panel scores and grafts are recorded in [DECISIONS.md](DECISIONS.md).

### 1.3 What is genuinely new

The pieces have precedents: the Gödel machine (Schmidhuber's design for a system that rewrites
itself only with a proof that the rewrite raises its utility), the Darwin Gödel Machine (DGM, a
coding agent that edits its own scaffold, keeps an archive of variants and validates each change
empirically on benchmarks) and its successor the Huxley–Gödel Machine (HGM, which selects variants
by how well their descendants do) [R01], Exo, KLEE-FP, Unison, Hazel, sched_ext, noninterference,
proof-carrying code and CryptOpt. The contribution is the combination,
made checkable. "New" below means the dossiers found no prior instance; several dossiers ran with
an exhausted search budget, so each claim is unverified against all 2025–2026 work.

| # | Mechanism | Borrowed from prior art | What is new |
|---|---|---|---|
| **N1** | **Certified modification spaces as typed items, plus the Gödel–Darwin promotion rule.** A candidate is promoted only if: the space check passes → the effective correctness grade ≥ the slot's requirement → spec strength (as a cap inside the effective grade, 03 §3.2) → the code floor (checkers, elaboration) ≥ the slot's `code_floor` → an anytime-valid e-value (a betting statistic that stays valid however long the test runs, §8.5) clears its threshold, charged to an alpha budget per period and slot family (defaults, F1-A) or to the grant's online-FDR stream (opt-in profiles) → physics plausibility passes → authority is present. | The Gödel machine's "no change without a proof", here narrowed to proofs of invariance while utility is measured; DGM/HGM's archive and clade selection [R01]; sched_ext-style fallback and noninterference [RV: D2-A]; Exo's checked schedules [R05]; anytime-valid statistics [RV: S1] | Spaces are language items. *Soundness* is a one-time space certificate (where one exists) plus a per-build membership check on the emitted binary; for schedules the per-build T1 check alone carries soundness. *Completeness-for-members* is untrusted and only tested. False promotions are bounded in two tiers: in expectation by a union-bound α budget for defaults and F1-A, and by FDR ≤ q per grant for opt-in profiles [P2 §5.3, §8.1; 06 §6.5] |
| **N2** | **IEEE-exact translation validation of SIMD (later GPU) kernels** by FP-DAG matching against a canonical-order meaning, over an owned, Zen-5-fuzzed x86 semantics table | KLEE-FP's structural FP matching on SSE kernels; Alive2, CryptOpt and VeriISLE translation validation [R07]; XED iclass keys; s2n-bignum's table-growing practice [G02] | No public AVX-512 FP semantics exists [G02]; Mithril writes and fuzzes its own and applies it to real compiler object code. Canonical numerics are reframed as a *verification asset* (they make float equivalence a graph question), not a tax |
| **N3** | **One evidence ledger** with claim-kind admissibility, trust-base-relative grades, negative results, auto-invalidation, and INV-HONEST as a type (`Quantity<Unit, Origin>`) | Proof-carrying code [RV: S6]; Unison content hashes; the DGM archive; Hearth's INV-HONEST [R11] | About ten revisit nodes reinvented parts of this substrate [RV: §6]; Mithril makes it one store whose policies the compiler enforces as link errors |
| **N4** | **A decidable tombstone scope/trigger language** with auto-derived triggers and decidable subsumption; `mithc revisit` (and `--design` for design-level tombstones) | R02's failure classes and revisit loop; Go-Explore's "return then explore"; Hearth's informal "revisit if" ADR clauses [R02] | Verdicts without scope are type errors; triggers come from the bound term and gap attribution the evaluator already computed; the design process and the compiler share one graveyard [P4 §8.7] |
| **N5** | **Separation of powers for agents:** role capabilities, spec escrow, a deterministic code-only Gatekeeper, the `abandon` verb, handovers derived from the toolchain journal | Hearth's agent governance (invariant lane, sealed goldens, handover manifests) [R11]; ImpossibleBench's abort option; Comparator-style gates [R07] | Authority is a capability held by a role and enforced by the store; no LLM judges; DGM's log-faking class is closed because the agent cannot write the facts in its own handover [P2 §5.5, P1 §7.8] |
| **N6** | **Language governance by measured comprehension:** the subset rule with per-construct false-friend classes (C / Dc / D) decided in a Surface Lab; agent-interface artifacts as a Forge level scored by a held-out harness | Familiar-syntax evidence [G01]; Hazel typed holes, SWE-agent's interface, RustAssistant grouping [R03]; GEPA reflective evolution [R04]; DGM, whose own gains came from tools and context [R01] | The harness gates every language decision with pre-registered kill criteria and control arms. Evolving the agents' card, diagnostics and scaffolds is the DGM-proper loop, run under the same integrity rules [P1 §7.11, §8] |
| **N7** | **Physics-typed compilation:** bytes-per-tier cost signatures (symbolic at build, numeric at load, measured at run) with phys/emp/est bound tiers; `mithc explain` reports floor and fraction of roof; gap attribution; plausibility quarantine | The roofline model and Hearth's bytes/token equation [R08]; Belady/MIN and AGL bounds [RV: D2-B]; one flow, many handlers [RV: D2-C] | Rooflines become part of each definition's checked interface and the Forge's fitness; only phys and audited-emp bounds may prune or quarantine [P3 §4] |
| **N8** | **Cross-device bit-exactness for a named canonical core:** exact integer accumulators with overflow proofs license reordering, so VNNI and dp4a can be used bit-exactly, and INT8 tensor cores too if their exact int32 accumulation on sm_120 is confirmed (unverified [G03 open question 3]); output is independent of what is in VRAM. **Owner-gated.** | Batch-invariance work gives same-device determinism only [G03]; dp4a/VNNI exact integer dots | No engine the research found offers output independent of VRAM contents [G03]. Placement becomes a pure cost decision [P3 §1] |

### 1.4 Answer to the brief: further than DGM, and revisiting unfruitful spaces

The owner asked for a system that goes further than DGM and recursively re-explores problem spaces
that once proved unfruitful. The answer, in one place:

- **DGM's own loop is F1-A.** DGM's measured gains came from improving its own scaffold: editing
  tools and context handling, validated empirically [R01]. F1-A evolves the agents' card,
  diagnostics, ranking and scaffolds for writing Mithril, scored by a sealed held-out harness under
  the same integrity rules as every other Forge level (§11.1) **[v1, M6]**.
- **Four mechanisms go further than DGM, AlphaEvolve and HGM:**
  1. a **persistent ledger** keyed by code closure × environment and shared across models and
     campaigns, instead of one run's archive (§8.3, §11.3);
  2. **self-reviving tombstones**: scoped negative results whose decidable triggers re-open them
     when the hardware, toolchain, model or evaluator changes, so "revisit unfruitful spaces" is a
     scheduled computation, not a memory (§11.5);
  3. **certified spaces**, so a whole class of change is searched with performance evidence alone,
     and known hack classes become type errors or isolation properties (§8.4, §8.7);
  4. **measured surface governance**: the language itself changes only on harness evidence against
     control arms (§10.6).
- **The recursion ladder.** Each rung widens what can be searched, and each opens only when its
  trigger fires:

| Rung | What becomes searchable | Trigger | Status |
|---|---|---|---|
| F1 | `timing_only` policies, exact schedules, lossless layouts | simulator pilot in M0; live engine once the store certificate holds (M4) | v0 (M4); campaigns v1 (M6) |
| F1-A | the agents' own interface: card atoms, diagnostic templates, ranking, scaffolds | harness stable for two epochs ([06 §10](architecture/06-forge.md)) | v1 (M6) |
| F2 | compiler heuristics among certified rewrites, then new rewrite rules with proof obligations | M5 passed, translation validation in CI, a second microarchitecture (D-15, DR-016) | later |
| F3 | the language and stdlib, as human-ADR editions | Edition 1 at M7; later editions on harness evidence | later |
| Fm | the selection policy and budget split | ≥ 2 archived campaigns plus a proposed selection change (D-14) | later |
| Placements, lossy lanes | CPU vs GPU; `approx` variants | DR-022 gate; the first owner-approved non-exact path (D-07) | by-trigger; reserved |

- **What is refused, and why.** The Forge never rewrites F0: the checkers, the gate, the measurement
  service and the harness. A judge that can rewrite itself certifies nothing, and DGM's own record
  includes faked logs (§8.7). The Löb-safe rules S1–S3 (§11.6) make this structural. Proposers, by
  contrast, evolve freely, because they cannot accept anything (S4).
- **Why v1 is staged narrow.** Every wider rung needs a judge that has already survived adversarial
  tests (X4) and a ledger of earlier verdicts to replay against. The staging is deliberate; the
  ladder above is the plan for the rest.

> **Reviewer note (F2 pilot).** A by-trigger F2 rewrite-rule discovery pilot after M2 is a natural
> candidate, because the Z3-FPA rule audit exists from M2. It is not in ROADMAP's deferral register,
> so under ROADMAP §1 rule 6 it needs an Owner decision before it can land.

---

## 2. Field notes from the intended user

> **Clearly labelled:** this section is written by Claude, in the first person, about its own
> failure modes as an agent writing software, adapted from the pre-research draft thesis. It records
> *self-reported* experience, not measurements. Each note maps to a feature, and the cold-agent harness (§10.6) exists precisely
> to test whether the features help agents in practice. Where a note is not borne out, the feature
> loses.

What actually costs me correctness and turns when I write software today:

1. **Context economy.** I cannot hold a large codebase. Hidden global state, ambient authority,
   implicit invariants and action at a distance force me to read far more than I can afford. I want
   a function's signature (types, effects, capabilities, contract) to be a sufficient summary of
   what it may do, so callees' bodies never have to enter my context.
2. **Priors.** I write familiar syntax (Rust-, TypeScript- or Python-shaped) far more accurately
   than novel syntax. Novel *semantics* behind a new keyword is cheap for me; novel *syntax* is not;
   familiar syntax with a changed meaning is the worst of all.
3. **Edits.** Whitespace-exact search/replace and line-number diffs fail often. Stable identities
   and edits that are checked atomically would remove a whole class of my failures.
4. **Feedback latency and precision.** Slow builds waste turns, cascades of errors hide root
   causes, and vague messages make me guess. I want one root-cause diagnostic, structured, with a
   machine-applicable fix, quickly and incrementally.
5. **Hallucinated APIs.** I invent functions that do not exist. A queryable API index ("what has
   type T → U with no effects?") prevents this.
6. **Tests that prove nothing.** I can write tests that pass trivially. Mutation scores and
   independent checkers should grade my tests and my specs for me.
7. **Invisible performance.** I cannot see caches, ports or bandwidth. The compiler should explain
   performance against physics (floor, achieved fraction, binding resource), per kernel, per target.
8. **Nondeterminism.** Flaky concurrency and float-order drift turn debugging into guesswork. I want
   determinism by default, with nondeterminism as an explicit, audited effect.
9. **Lost intent across sessions.** My successors lose why code is the way it is. Specs, rationale,
   provenance, evidence and handover state should live in the codebase as typed data, not in prose
   that rots.
10. **Safety of my own actions.** I may run code that does damage. Capability-safe effects make
    "run this generated code" a bounded-risk action by construction.
11. **Coordination.** Many agents editing one repository conflict. Content-addressed definitions,
    role ownership and mergeable evidence make parallel work safe.
12. **Search.** I am good at proposing many candidates and bad at being sure. A language that
    separates *what* (one meaning) from *how* (realisations) lets me search "how" aggressively
    while correctness stays anchored to "what". And when I judge my own work, I overrate it; a
    separate, deterministic judge should decide.

| Note | Feature that answers it | Where |
|---|---|---|
| 1 Context | Mandatory `uses { }` rows and contracts on public items; context packs ship signatures, not bodies; `#[closure_budget(N)]` | §5, §10; [01](architecture/01-language.md), [05](architecture/05-agent-protocol.md) |
| 2 Priors | Subset rule: Rust syntax means Rust; divergence is rejected by name or gets a new keyword; C/Dc/D classes measured per construct | §5.1; DR-002 |
| 3 Edits | Hash-anchored, atomic edit-plus-check; `StaleAnchor`, never fuzzy application | §10.3 |
| 4 Feedback | Grouped root-cause JSON diagnostics with applicability levels; query database keyed by content hash | §9.1, §10.4 |
| 5 APIs | `mithc search` by type and effect over existing hashes; nearest-name suggestions | §10.2 |
| 6 Tests | Spec escrow, mutation-scored spec strength, T1/T2 checkers; "tested" never suffices for exact slots | §8 |
| 7 Performance | Cost signatures, `mithc explain`, `Quantity<Unit, Origin>` | §7.5, N7 |
| 8 Nondeterminism | `canon.v1` exact numerics; `nondet` as an effect; `deterministic(by: …)` boundaries citing evidence; permutation scheduler in tests | §5.4, §6, §9.4 |
| 9 Intent | Ledger facts, tombstones, journal-derived handovers, `#[decision(ADR-…)]` drift lints | §8.3, §10.5 |
| 10 Safety | Effects are capabilities rooted at `main(root)`; Forge candidates have no clock, I/O or FP environment | §5.4, §11 |
| 11 Coordination | File-per-fact ledger, union-mergeable; FREE/SEAL/AUTHORITY classes; per-definition ownership | §8.3 |
| 12 Search | Meaning/realisation split; certified spaces; a code-only Gatekeeper | §7, §8.6 |

---

## 3. Principles

1. **Familiar where meaning matches; rejected or loud where it differs.** Code that parses as Rust
   means what Rust means. A Rust form Mithril does not support is rejected with a named diagnostic.
   Every new concept arrives with a new keyword or type. Nothing is reinterpreted (DR-002). One
   in-prompt rule change took GPT-4 from 82.5% to 40.5% on affected problems, measured [G01]:
   false friends are the costliest case.
2. **The signature is the summary.** Types, effects, capabilities, contract, fidelity grade and
   determinism scope together say everything a caller needs. There is no ambient authority.
3. **Checkers decide correctness; measurements decide utility.** No test-only acceptance on the
   logits path for exact kernels (DR-021). A checker that answers "unknown" or times out has
   rejected.
4. **Prove the space, not the candidate.** Make whole classes of change unable to alter outputs,
   certify each class once (or check each candidate mechanically per build where no one-time
   certificate exists), then search it with performance evidence only. Six independent revisit
   branches converged on this [RV: §6].
5. **Exact by default.** Canonical IEEE order is part of the semantics. Losing bits is an explicit,
   opt-in grade, and INV-LOSSLESS-DEFAULT is a link error.
6. **Reserve the lattice, defer the checker.** Grades and tiers not yet implemented (`real(bound)`,
   `approx`, `device(t)`, the VRAM tier) exist in the types and schema from v0 but cannot be
   produced yet, so growth needs no language change [P5 §1].
7. **Small trusted core, attacked on purpose.** Search, optimisations, agents and (for audited
   kernels) the C compiler are untrusted. The trusted base is budgeted in lines and adversarially
   tested (§8.9).
8. **Objectives follow physics; numbers are honest.** Objectives are bytes per token and stall time,
   never hit rate or IPC. A result that beats a validated physical bound is quarantined. Speed gains
   come from bytes, placement and scheduling, not from syntax.
9. **Accumulate; never erase.** Evidence, archive entries and tombstones are content-addressed and
   append-only. A change makes old evidence stale; it never deletes it.
10. **Measure the central claim, including against Mithril.** Every surface decision passes through
    a harness with Rust, C11 and "Rust + Mithril tooling" control arms and pre-registered kill
    criteria. If the standalone surface loses, Mithril ships as a checker, ledger and tool layer
    over Rust and C, and the design keeps that fallback cheap.

**What the standalone surface buys, and what survives without it** [inference]. The decision-relevant
contrast is Mithril against "Rust + Mithril tooling", so the Owner needs to know what only the
surface provides:

| Mechanism | Needs the standalone surface | Survives in the fallback (tools over Rust/C) as |
|---|---|---|
| N1 certified spaces, promotion rule | front-end `policy fn` / `timing_only` typing, `evolve slot` items | binary T0 confinement, the gate and the α budget, the `hx_policy` shim on C Hearth |
| N2 T1/T2 translation validation | `kernel fn` meanings and `schedule` items as the checked pair | T1/T2 over C objects against a C scalar reference (X2 certifies today's C kernels) |
| N3 ledger, `Quantity<Unit, Origin>` | compiler-enforced evidence policies as link errors | the ledger and `lift`-derived facts; quantities as a library type with weaker enforcement |
| N4 tombstones, `revisit` | nothing | unchanged |
| N5 roles, escrow, Gatekeeper, `abandon` | `spec` items in the language | specs as sidecar files; everything else unchanged |
| N6 surface governance, F1-A | the Surface Lab (moot without a surface) | F1-A over the tooling's cards and diagnostics |
| N7 cost signatures, `explain` | derivation from `kernel`, `flow` and `format` items | hand-written annotations or sidecars |
| N8 cross-device core | `device(t)` / `cross_device` scope types and the placement rule | per-kernel T1 on PTX; no placement checker |
| Effects and memory model | `uses { }` capability rows, `deterministic(by:)`, second-class references and projections | lost; Rust's own types and borrow checker remain |
| Formats and ABI | `format` and `export abi` items | generators over C (§12.6) |

ROADMAP §3.2 makes "Rust + tooling beats Mithril by > 10 points" an Owner review (amber), not a
kill. The X1 pre-registration (D0-12) should state the decision rule explicitly: proceed with the
standalone port only if Mithril − (Rust + tooling) ≥ −k points, with k fixed before X1, **or** a
named surface-only capability from the table above is required; otherwise take the STOP-L path.

---

## 4. The stack

```
 ==========================================================================================
 L0 AGENTS & ROLES     frontier API agents | Hearth-hosted local models (by-trigger) | humans
                       roles: Author | Builder | Prover | Adversary | Gatekeeper (code + Owner key)
        | Tier-0 card (<= 8 KB, in AGENTS.md) + project card (<= 4 KB) + context packs + handovers
 =======v==================================================================================
 L1 AGENT INTERFACE    mithc CLI (--json, every reply ends with next: [...]) | MCP | LSP | SARIF
                       check hole edit outline search pack propagate prove audit bench explain
                       profile-measure ledger revisit resume handover guide fix fmt lift
                       + abandon (the role verb of §8.6)
 =======v==================================================================================
 L2 CODEBASE STORE     canonical .mith text in git (truth) + mith.toml (grants, owners, sealed
    & LEDGER           items, evidence policies) + mith.lock (name -> definition hash)
                       ledger: gate-signed fact files under .mith/ledger/ (FREE/SEAL/AUTHORITY);
                       raw samples + certificates = content-addressed blobs in the data dir
 =======v==================================================================================
 L3 FRONT END          lossless Syntax (Lark-conformant CST) -> HIR (holes as typed nodes)
    (query DB)         -> THIR (types, effects, ownership, grades)   ... salsa-style, keyed by hash
                       every phase emits Fact Plane (Datalog) relations; grouped diagnostics
 =======v==================================================================================
 L4 MIDDLE IRs         MIR = MCore (small normative core; oracle = mithi's independent mode)
                       KIR (kernel meaning op-DAG + layouts + schedule application)
 =======v==================================================================================
 L5 VERIFICATION       TRUSTED CORE = F0: T0 types/effects/grades + binary confinement |
    & EVIDENCE         T1 FP-DAG matcher + audited exact-rewrite list | T2 bit-vector SMT with
                       certificates | T3 tolerance (reserved) | x86 semantics table (XED-keyed,
                       Zen-5 fuzzed) | gate (promotion rule, alpha budget) | measurement service
 =======v==================================================================================
 L6 BACKENDS           B1 strict C11 (checked in, regenerated byte-for-byte in CI)
                       B1.5 object audit (XED decode -> LIR -> T1) for ~20 hot kernels
                       B2 PTX expert tier (owner-gated) | B3 direct x86 emitter (by-trigger)
                       B4 copy-and-patch JIT (deferred) | LLVM optional, never trusted
 =======v==================================================================================
 L7 RUNTIME            no hidden runtime; audited std_platform: Mutex<T>/with_lock, Condvar,
    (std_platform)     Arena -> SlabBuf, Frozen<T>, File.read_at, scoped pool & services;
                       permutation scheduler in test builds; hot-swap only at token epochs
 =======v==================================================================================
 L8 TARGETS &          x86-64 scalar | AVX2 (+VNNI) | AVX-512 F/BW/VL/VNNI/BF16 | arm64 (CI)
    HARDWARE           | sm_120 (owner-gated); tiers NVMe -> DRAM (-> VRAM reserved)
                       Ryzen 9 9950X . 64 GB DDR5 . 990 PRO NVMe . RTX 5070 12 GB . Windows 11
 ------------------------------------------------------------------------------------------
 SIDE SYSTEMS   THE FORGE   untrusted proposers -> cascade -> F0 gate -> ledger (archive)
                            levels F1 artifacts (v0, M4) + F1-A agent interface (v1, M6);
                            F2/F3/Fm later
                THE HARNESS sealed task families, Surface Lab, Mithril MultiPL-E; arms Mithril |
                            Mithril without traits | Rust | C11 | Rust + Mithril tooling |
                            obfuscated-Mithril; VP@1, CABW
                HEARTH      the acid test; hearth-c-ref kept as a permanent differential oracle
 ==========================================================================================
```

**Rule of the diagram:** no arrow from an untrusted layer reaches the ledger except through the F0
checkers or the gate. The front end can say "this looks like a valid schedule" in milliseconds; only
the F0 verdict on emitted code becomes evidence [P2 §2]. The layers above are drawn as a build
stack; the evidence path below is the only route into the ledger (L2), and the Forge and the Harness
enter it only through L5:

```
 L0 agent session | Forge proposer | harness attempt                       UNTRUSTED
      |  request: mithc verb over CLI / MCP (L1)
      v
 L3 front end -> L4 MIR / KIR -> L6 backend -> emitted C, compiled object   UNTRUSTED
      |                                                 |
      |  claimed obligations (advisory)                 |  the bytes that will run
      v                                                 v
 L5 F0: T0 / T1 / T2 check the emitted object against the meanings'       TRUSTED
        KIR (in v0, elaboration is trusted code graded tested, §8.2); the
        measurement service owns the clock and times the object against
        hearth-c-ref
      |  verdicts + measurements
      v
 L5 gate: promotion rule, alpha budget, authority (grant or Owner ADR)     TRUSTED
      |  signs
      v
 L2 ledger: gate-signed fact file under .mith/ledger/ (FREE / SEAL / AUTHORITY)
```

| Layer | Responsibility | Trust | Detailed in |
|---|---|---|---|
| L0 Agents & roles | Propose specs, code, proofs, attacks; each session holds one role | Untrusted; bounded by role capabilities | [03](architecture/03-trust.md), [05](architecture/05-agent-protocol.md) |
| L1 Agent interface | One JSON contract over CLI, MCP and LSP; anchors, not line numbers | Untrusted input/output; returns only ledger facts as evidence | [05](architecture/05-agent-protocol.md) |
| L2 Store & ledger | Text as truth; identity, caching and evidence by hash; sealed role-owned items | Integrity by hashes and gate signatures | [03](architecture/03-trust.md), [04](architecture/04-toolchain.md) |
| L3 Front end | Incremental checking, holes, Fact Plane queries, diagnostics | Untrusted; advisory until F0 agrees. The one exception is the elaboration of exact meanings into KIR, a trusted code component graded `tested` (§8.2, §8.9) | [01](architecture/01-language.md), [04](architecture/04-toolchain.md) |
| L4 Middle IRs | MCore normative core; KIR kernel meanings | `mithi` has two modes: an independent mode with its own parser and checker (the DR-010 differential oracle) and a MIR mode that only localises faults ([04 §2](architecture/04-toolchain.md)) | [01](architecture/01-language.md), [02](architecture/02-compute.md) |
| L5 Verification | Check evidence, define ISA semantics, decide promotion, own measurement | **Trusted (F0)**, budgeted, attacked | [03](architecture/03-trust.md) |
| L6 Backends | Emit code without changing meaning | Untrusted; T1 validates the output for audited kernels | [04](architecture/04-toolchain.md) |
| L7 Runtime | Deterministic execution without GC or hidden threads | Audited `std_platform`; store core covered by a space certificate | [02](architecture/02-compute.md), [04](architecture/04-toolchain.md) |
| L8 Targets | ISA tiers and devices as data; machine profiles fingerprinted | Assumed, with semantics fuzz-validated on silicon | [02](architecture/02-compute.md) |
| Forge | Search inside certified spaces | Untrusted; cannot write F0 | [06](architecture/06-forge.md) |
| Harness | Measure agent comprehension; gate language decisions | Gatekeeper-owned, sealed | [05](architecture/05-agent-protocol.md) |

---

## 5. The language at a glance

All syntax below is **provisional pending the Surface Lab** (§10.6): the semantics are decided,
the spelling is measured. Full language reference: [01-language](architecture/01-language.md).

### 5.1 Surface policy

- **Standalone `.mith`, Rust-shaped** (DR-002). Braces, `fn`, `let`/`let mut`, `struct`, `enum`,
  `match`, inherent `impl`, `mod`/`use`, `Result` with `?`, `as` casts with Rust semantics, and a
  static-dispatch trait subset with Rust meaning (no `dyn`, no specialisation, no `async`, no user
  macros; DR-005) **[v0]**.
- **The subset rule.** Every construct is classified **C** (coincident with Rust: kept),
  **Dc** (Rust form Mithril rejects, with a named diagnostic and fix) or **D** (new concept,
  keyword-led). The classification is indexed by grade: some Dc constructs (such as `max_by` over
  floats) become C inside `timing_only` code, where output bits cannot depend on them [P1 §3.1].
- **New keywords** (each loud, line-leading, and contextual: reserved only where an item or clause
  begins): `kernel`, `schedule`, `format`, `policy`, `spec`, `claim`, `uses`,
  `requires`/`ensures`/`invariant`, `deterministic`, `linear`, `par for`, `comptime` and
  `export abi` **[v0]**; the store items `store`, `hint port` and `certificate` **[v0, M4]** and `flow` **[v0, M4–M5]**
  ([02 §12](architecture/02-compute.md)); and `evolve slot`
  ([06 §2.1](architecture/06-forge.md)) **[v0, M4]**. The clause words inside a `store` item
  (`fallback`, `validate`, `budget`, `fuel`, `reserve`, `off_lock`, `evidence`) are reserved only
  inside it, as schedule primitives are. Metadata that does not change typing uses attributes
  (`#[range(..)]`, `#[decision("ADR-0004")]`, `#[closure_budget(N)]`).
- **Typed holes are `todo!("name")`** (DR-003): Rust-coincident, type-checked, and reaching one at
  run time is a trap ([01 §12](architecture/01-language.md)), as a panic is in Rust. `?name` was
  rejected because it collides with Rust's `?`.
- **One normative Lark grammar** within OpenAI's CFG-tool limits; a hand-written error-recovering
  parser is differentially fuzzed against it; `mithc fmt` is canonical **[v0]**.
- **Integer overflow traps** unless proved absent (Rust's debug meaning, kept in every build);
  `wrapping_*` is explicit. In `kernel` code an unprovable refinement is a compile error, never a
  silent runtime trap (DR-011).

Initial false-friend rows (seeded from Hearth's real bit-exact traps [RV: D3-i]): float `.sum()` /
`max_by` / `min_by_key` are rejected in exact-graded code and on the logits path (DR-013; Safe fix
`canon::sum_seq`, MeaningChanging fix `canon::sum16`); `round()` keeps Rust's ties-away meaning
while Hearth's quantiser needs `round_ties_even()`; `f32::max` keeps Rust's NaN rule while x86
MAXPS operand order needs its own name; references stored in structs or returned are rejected;
`unsafe {}` needs a package grant; `async` is rejected; "Q4 block" exists only as a Hearth `format`
(64 elements, high nibble at j+32), never llama.cpp's 32-element Q4_0.

### 5.2 Types and memory

- **Scalars:** `i8..i64`, `u8..u64`, `usize`, `bool`, `f16`, `bf16`, `f32`, `f64`. Sub-byte and
  microscaling codes (`nibbles`, `e2m1`, `e8m0`) exist only as element codes inside `format`s,
  never as arithmetic types [R10] **[v0]**.
- **Minimal refinements** (DR-011): `#[range(lo..=hi)]` on fields and parameters, `requires`,
  `ensures`, `invariant`. Mithril discharges integer side conditions (T2) and simple contracts
  **[v0, M2]**; a full Dafny-class auto-active verifier is **not v1** (DR-012). Dafny's 82% vericoding figure does
  not transfer automatically; Verus, the Rust-shaped analogue, scored 44% [R03].
- **Memory model** (DR-004): mutable value semantics; Rust move semantics; borrows spelled only
  `&T` / `&mut T`; references are **second-class** (parameters and locals; never stored in structs
  or returned) **except** through **projections** (Hylo-style subscripts such as `w.row(r)`, which
  yield a borrow scoped to the caller's expression), plus a **non-escaping kind** for closures and
  iterator adapters that capture references. No lifetime annotations. `linear struct` values must
  be consumed. `Send`/`Sync` keep Rust's names and meaning **[v0]**.
- **`Quantity<Unit, Origin>`** with `Origin ∈ {Measured{hw, …}, Simulated{model}, Estimated, Assumed}`
  (mirroring the performance grades of DR-007):
  an unlabelled performance number does not format, and unit errors are type errors (INV-HONEST as
  a type) **[v0]**.

### 5.3 Canonical snippets

A Hearth quantisation format. The format *is* the specification; accessors, pack/unpack, size
checks and range facts are derived **[v0]**:

```mith
/// Hearth Q4 weight block (FORMAT.md, hx_quant.h): 64 elements in 34 bytes.
format BlockQ4 {
    d: f16,                          // block scale
    q: nibbles<64, offset = 8>,      // byte j: low nibble = elem j, high nibble = elem j+32
}
// Derived by the compiler: size == 34 (checked), elem(i) -> i32 with #[range(-8..=7)],
// pack/unpack, and the integer view used by exact dot products.
```

A kernel *meaning* (NUMERICS §3 transcribed). Exact grade is the default; the body runs as-is in
the reference interpreter and is the oracle for every realisation **[v0]**:

```mith
/// NUMERICS §3, one Q4 row times one Q8 activation. Exact grade is the default.
kernel fn q4_row_dot(w: &[BlockQ4], a: &[ActQ8]) -> f32
    requires w.len() == a.len()
{
    let mut acc: f32 = 0.0;
    for g in 0..w.len() {
        let mut isum: i32 = 0;      // exact integer sum: may be reordered (T2 range proof)
        for j in 0..32 {
            isum += w[g].q.elem(j) * (a[g].q[j] as i32);
            isum += w[g].q.elem(j + 32) * (a[g].q[j + 32] as i32);
        }
        // |isum| <= 64 * 8 * 127 = 65_024 < 2^24, so the cast is exact (T2 obligation)
        acc = acc + (isum as f32) * (w[g].d.to_f32() * a[g].d);   // fixed order, no contraction
    }
    canon::nan(acc)                 // canonical quiet NaN 0x7fc00000
}

kernel fn q4_matvec(w: &Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32])
    requires y.len() == w.rows() && a.len() == w.blocks_per_row()
{
    par for r in 0..w.rows() {      // disjoint writes: each y[r] written by exactly one iteration
        y[r] = q4_row_dot(w.row(r), a);   // w.row(r) is a projection, not a stored borrow
    }
}
```

A *realisation*: a schedule may apply only DAG-preserving primitives, and T1 validates the emitted
object code against the meaning **[v0, M2]**:

```mith
/// A schedule may only apply DAG-preserving primitives. T1 validates the emitted object code.
schedule q4_matvec_avx512 for q4_matvec on x86_64(avx512f, avx512bw, avx512vnni) {
    tile r by 16;                   // 16 rows per pass
    vectorize j using vpdpbusd;     // integer block sums via VNNI: licensed by the exact-i32 range proof
    keep_order acc;                 // the float epilogue order comes from the meaning
    prefetch w ahead 2 blocks;      // timing-only; the distance is illustrative, kept only if measured
}
```

A `timing_only` policy: it can only emit hints, and the store core validates every hint, so no
policy can change logits **[v0, M4]**:

```mith
/// A policy can only emit hints. The store core validates every hint, so no policy can change
/// logits (certified space, store-core certificate O1–O5). Integer scores avoid the f32-Ord trap.
policy fn pick_victim(slots: &[SlotView], now: Tick) -> Hint<SlotId> {
    let mut best = Hint::none();
    let mut best_age: u64 = 0;
    for s in slots {
        if s.pinned || s.refs > 0 { continue; }
        let age = now.0 - s.last_use.0;
        if age > best_age { best_age = age; best = Hint::some(s.id); }   // ties: lowest index wins
    }
    best
}
```

Authority in signatures, and a determinism boundary that removes only `nondet` **[v0, M4]**:

```mith
/// Unbuffered positional read of one expert slab. Authority is explicit in the signature.
fn read_slab(file: &BlobFile, off: Aligned<u64, 4096>, buf: &mut SlabBuf) -> Result<(), IoError>
    uses { io }
{
    file.read_at(off, buf.bytes_mut())   // std_platform: OVERLAPPED+NO_BUFFERING / pread+O_DIRECT
}

/// Thread timing and cache state are nondeterministic inside; the bytes returned are a function
/// of the immutable, content-hashed file. Authority (io, spawn) stays visible to callers.
fn acquire(store: &Store, id: ExpertId) -> Result<Frozen<SlabBuf>, IoError> uses { io, spawn } {
    deterministic(by: golden::scheduling_independence) {
        store.acquire_inner(id)          // Err only from an environment fault (HX_E_IO, O5)
    }
}
```

Claims live in sealed, Author-owned spec items **[v0: syntax at M1, sealing enforced by the M3
ledger]**:

```mith
/// Claims live in spec items owned by the Author role and hash-locked; Builders cannot edit them.
spec q4_matvec_claims for q4_matvec {
    claim refines(q4_matvec_avx512, q4_matvec) requires validated;     // T1 witness on the object
    claim refines(q4_matvec_avx2, q4_matvec) requires validated;
    claim perf(q4_matvec_avx512) requires measured
        noninferior(to: hearth_c_ref::mm_q4_avx512, margin: 3%);
}
```

Honest numbers as a type, and a typed hole:

```mith
let bw: Quantity<GBps, Measured> = profile.dram_read_all_core;
// Formatting prints value + origin ("77 GB/s, measured, <hw fingerprint>"); an unlabelled
// number does not format. Simulated and measured quantities do not mix without conversion.

let score = todo!("eviction_score");   // typed hole: `mithc hole eviction_score` returns context
```

A boundary resets the determinism grade ("blob-grade" is a grade, not a row entry), so `acquire`'s
row stays `{ io, spawn }` ([01 §6.4](architecture/01-language.md), rule 2).

> **Reviewer note (snippets derived from the outline).** Two canonical snippets are corrected here,
> and their decisions are unchanged. (1) The outline's `q4_matvec` required only
> `y.len() == w.rows()`, so `q4_row_dot`'s `requires w.len() == a.len()` could not be proved at the
> call, and under DR-011 an unprovable refinement in kernel code is a compile error. The added
> `a.len() == w.blocks_per_row()`, with `Matrix::row` ensuring
> `result.len() == self.blocks_per_row()`, discharges it statically. (2) The outline's `acquire`
> returned `Frozen<SlabBuf>`, so an I/O fault could surface only as a trap, contradicting O5 and
> Theorem 3 ("`Err` arises only from environment faults"). It now returns `Result`, as
> [02 §12.1](architecture/02-compute.md) does. Both corrected snippets are canonical:
> [01 §5.3, §6.4](architecture/01-language.md), [02 §2, §9](architecture/02-compute.md) (whose
> `q4_matmul` requires `a.cols() == w.blocks_per_row()`) and [03 §3.3](architecture/03-trust.md)
> print the same forms. (3) The schedule's prefetch line is kept with a comment: two 34-byte blocks (68 bytes)
> is too short a distance to hide DRAM latency (Little's law needs ~6 KB in flight chip-wide), and
> hardware prefetch usually beats software prefetch on Zen 5 [R08]. Prefetch is a timing-only
> primitive, kept only if measured.

### 5.4 Effects, capabilities and grades

- **Effects are capabilities** (authority) **[v0]**: `io`, `spawn`, `alloc(A)`, `time`, `foreign`,
  `unsafe`, `fp_env`, `compile`, `lossy`, plus `nondet` and `nondet(platform)` (which also taint
  the determinism scope), and `blob` for value-deterministic reads of immutable content-hashed
  bytes. The set is fixed in v0; user effects and one-shot handlers are **by-trigger**.
- Capabilities are values rooted at `main(root)` or exported entry points; `unsafe` and `foreign`
  need per-package grants in `mith.toml`. Rows are inferred for private functions and mandatory on
  `pub` items, written `uses { … }` after the return type (DR-006).
- **Effects record authority; grades record fidelity and determinism.** Fidelity is
  `exact | real(bound) | approx(profile)` with exact ⊑ real ⊑ approx, and composition takes the
  **join** (the lossier grade). Determinism scope is `cross_device | device(t) | schedule_dependent`.
  `real(bound)`, `approx`, `device(t)` and the VRAM tier are **reserved**.
- **`deterministic(by: E) { … }`** removes *only* `nondet`, never authority effects. It needs a
  DeclareDeterministic manifest grant, cites evidence E, propagates E's grade downstream, and loses
  its licence when E goes stale **[v0, M4]**.
- **Failure semantics [v0]:** errors use `Result` and `?`. A trap (what Rust calls a panic) never
  unwinds and never aborts the host process (INV-SAFE). It ends evaluation up to the nearest
  **fail domain**: an `export abi` entry returns its declared trap error code, a hint-port policy
  call takes the fallback policy's decision (plus a strike), and a test case records a failure
  ([01 §12](architecture/01-language.md)). Every function carries a computed `may_trap` fact, and
  `kernel fn`s must be trap-free. In a `par for`, the outcome of the lowest index that exits early
  wins, so failure is deterministic. A policy trap falls back to the default policy rather than
  returning an error; otherwise a policy could deny service through the error branch of the
  noninterference theorem ([01](architecture/01-language.md), [02](architecture/02-compute.md)).

### 5.5 Staging, modules and the core calculus

- **Staging [v0]:** `comptime` (run by `mithi`), monomorphisation and schedules as data. `Code<T>`
  quotes and `@bind(load)` load-time specialisation are **by-trigger** (a C go/no-go experiment
  must first show a gain from folding a model config) [P5 §3.7].
- **Modules [v0]:** one file is one module; packages have `mith.toml` (grants, owners, sealed
  items, evidence policies, edition) and `mith.lock` (hashes of sealed items). `export abi` blocks
  generate the C header, a ctypes mirror and layout tests from one source, with mandatory
  `struct_size` fields; appending fields is free, removing or reordering needs an ADR (contract
  variance lattice) [RV: D2-F].
- **Core calculus.** All judges flagged that no proposal wrote one. [01-language](architecture/01-language.md)
  gives the judgement forms, the typing of effects (authority) versus grades (fidelity,
  determinism), and the soundness theorems to prove: progress and preservation, capability
  confinement, `timing_only` noninterference, and determinism. Until mechanised (Lean is
  by-trigger, DR-010), the ledger records their real grades ([01 §13.7](architecture/01-language.md)):
  Theorems 1, 2(a, b) and 4 are `tested`; Theorem 2(c), binary confinement, is `validated` relative
  to the semantics table; Theorem 3 (`timing_only` noninterference) is `validated` when the binary
  check ran and `tested` otherwise.

---

## 6. Exact numerics

Detailed in [01-language](architecture/01-language.md) (numerics semantics) and
[02-compute](architecture/02-compute.md) (reductions, transcendentals, GPU); the canon migration
protocol is in [03-trust](architecture/03-trust.md).

### 6.1 `canon.v1`

`canon.v1` is Hearth's `docs/NUMERICS.md` made normative and machine-readable **[v0]**:

- strict IEEE binary32 (and binary64), round-to-nearest-even, no FTZ/DAZ;
- **no contraction and no reassociation**; `fma` only when written explicitly (`mul_add`, Rust's
  own name; Rust never contracts, so this rule coincides with Rust);
- canonical quiet NaN `0x7fc00000` at kernel outputs (`canon::nan`);
- named reductions `canon::sum16`, `canon::dot16` (16 lanes, then an 8-4-2-1 tree) and
  `canon::sum_seq`; blocked exact-int32 sums; the rank-order MoE combine; sequential-in-t attention.

**Exact integer accumulators with overflow proofs license reordering.** If T2 proves an integer sum
cannot overflow its accumulator, every summation order yields the same bits. That is the route to
VNNI `vpdpbusd`, `dp4a` and possibly INT8 tensor cores without breaking bit identity [G03]. For Q4 the
bound is 64·8·127 = 65,024; for Q8 it is 64·127·127 = 1,032,256 < 2^24, so `isum as f32` is exact
[R07]. Under exactness the *lane count* of a float reduction is part of the meaning: 16 lanes map to
one zmm, two ymm or (later) a half-warp. Vector width is otherwise a schedule choice [G03, R08].

**Why canonical numerics are an asset, not a tax.** Under a fixed op order, bit-exact equivalence of a
vectorised kernel reduces to matching floating-point DAGs modulo a short audited list of IEEE-exact
rewrites, plus bit-vector SMT for the integer parts. That check is cheap, sound and incomplete [R07].
Without a canonical order, equivalence would need tolerance reasoning, which is weaker and far more
expensive. Hearth already pays the performance cost of canonical order; Mithril collects the
verification dividend (N2).

### 6.2 Transcendentals

There is **no implicit default in exact code** (DR-014). Call sites name `cr::expf` (correctly
rounded) or `canon_v1::expf` (a fixed op-DAG, vectorisable, bit-identical across ISAs). Outside exact
code, std defaults to `cr`. Platform libm is reachable only through FFI with `nondet(platform)`, which
exact profiles reject. Measured motivation [G04]: Windows UCRT switches between FMA3 and non-FMA3
paths at startup, and the two differ on 44,232 sinf inputs; a no-FMA canonical expf prototype was
bit-identical across scalar, AVX2 and AVX-512 over all 2^32 inputs and ran at 0.204 ns/element on
AVX-512, against 1.12 ns for scalar UCRT expf (both measured). Hearth must land **ADR-0010**
(specified transcendentals) in C Hearth *before* the cross-binary hash corpus is built (§12, §17).

### 6.3 Grades, profiles and the FP environment

- A default profile that reaches `lossy` is a **link error**, which makes INV-LOSSLESS-DEFAULT
  mechanical. `approx` is never a default (DR-015) **[v0]**.
- The FP environment is an effect (`fp_env`) that no exact code holds. Asserting MXCSR on pool
  workers is not enough: Hearth is called from Python through ctypes, kernel code can run on the
  caller's thread, and a host library built with fast-math (or a C module during the port) can set
  FTZ/DAZ per thread or process-wide. So every `export abi` and `hx_*` entry, and every thread that
  executes exact code, **sets** the default MXCSR on entry and restores the caller's value on exit,
  and pool workers **set and assert** the default at start. Every T1 certificate records "default
  MXCSR" as a precondition **checked at entry**: a runtime-checked trust-base entry, not an axiom
  and not a discharged obligation ([03 §3.4](architecture/03-trust.md),
  [04 §9.2](architecture/04-toolchain.md)). This closes a live Hearth gap: MXCSR is never asserted
  today [G02] **[v0]**.
- On the logits path, exact kernels require `validated` evidence; non-kernel logits-path code may be
  `tested` plus the cross-binary hash corpus, labelled as such (DR-021).
- `real(bound)` (T3 tolerance certificates plus runtime margin checks at top-k and argmax) and
  `approx(profile)` (statistical quality certificates) are **reserved**: present in the types,
  producible only once an owner-approved non-exact path exists.

### 6.4 Meanings, the numpy reference and canon migration

Meanings become normative, so their *intent gap* (the meaning itself might be wrong) needs an
independent oracle. Hearth's numpy reference and the transformers comparison (INV-NUM-1/2) remain that
oracle, and the numerics fault model is also run *against the meanings*, to check that the differential
suite would catch a mutated meaning [P2 §5.5]. Through port stage S6, NUMERICS.md and the C scalar code
stay normative; afterwards the Mithril meanings become normative and NUMERICS.md is generated from them
and checked [P5 §9.2]. See [02](architecture/02-compute.md) and [07](architecture/07-hearth-port.md).

Canon changes come in two kinds ([03 §12](architecture/03-trust.md)). An **additive**
`canon.v1.1` adds a named reduction or `canon_v1::` function, such as the MXFP4 block order;
existing meanings keep their hashes and evidence, and no golden resets **[later]**. A **major**
`canon.v2` redefines an existing op-DAG, such as fixed-chunk attention for GPU parallelism or
explicit FMA, under a new `canon_v2::` namespace **[by-trigger]**. A major version follows the
**canon migration protocol** in [03-trust](architecture/03-trust.md): which goldens reset, which
ledger evidence is invalidated (the canon version is part of every key, so invalidation follows
closure hashes), and how old and new meanings coexist during the transition. The protocol is
specified now; its first use is `canon.v2`, which is by-trigger.

---

## 7. The compute layer

Detailed in [02-compute](architecture/02-compute.md).

### 7.1 Kernels, schedules and projections

- A **`kernel fn`** body is the canonical meaning. It executes in `mithi` and defines the per-output
  FP-DAG that T1 compares against **[v0]**.
- **`par for`** requires compile-time-disjoint writes. Dynamic chunk claiming stays
  value-deterministic, and the lowest-index error wins **[v0]**.
- A **`schedule`** may apply only DAG-preserving primitives: tiling, lane mapping with a fixed lane
  count, disjoint parallel splits, exact-integer lowering under a T2 licence, prefetch distance and
  unrolling. A schedule that reassociates a float chain is rejected with a named error. Schedules
  supply **correspondence maps** to T1 ("validate the output, not each rewrite"), so hand-written
  intrinsic code can be checked too, before the schedule language is complete [P5 §4] **[v0, M2]**.
  The rewrite model is borrowed from Exo (MIT) with an IEEE-exact mode added [R05].
- **Projections** (`w.row(r)`, slices, block views) are the one way a borrow leaves a call. They keep
  hot loops zero-copy without lifetimes [P3 §3.1] **[v0]**.
- One meaning plus N schedules replaces Hearth's scalar/AVX2/AVX-512 kernel triplets (the two SIMD
  files total 726 lines [P5 §3.2]). Whether this reaches parity is experiment X3 (§13).

### 7.2 Formats and layouts

`format` types declare block-scaled quantisation layouts once. The compiler derives pack/unpack,
dequantisation and a round-trip obligation, and, through an **integer view**, the exact-integer dot
meaning with its T2 range obligations. MXFP4 is native: doubled E2M1 values are exact i8 values in
{0, ±1, ±2, ±3, ±4, ±6, ±8, ±12}, so its integer path is derived automatically [P3 §3.2, R06].
Formats and integer views are **[v0, M2]**; MXFP4's canonical dot order needs `canon.v1.1`
(**later**, §12.5). Container formats use the same mechanism: Hearth's `.hearth` header becomes a
`format` description that generates a parser and writer with no `unsafe` (EverParse-style)
**[v0, M3]**. Their totality and safety (INV-FMT/SAFE) are graded `tested` (fuzzing, the `mithi`
differential and the golden malformed-file test); only the bounds obligations that T2 discharges
are graded `proof` ([ROADMAP §7](ROADMAP.md), B1). A small layout/tile algebra and block-sparse iteration (static masks and
data-dependent block lists such as MoE routing) are general features **[v0 where the port needs
them; v1 otherwise]**.

### 7.3 Flows, policies and the store core

- **`timing_only` policies** (eviction, prefetch issue and depth, mirror choice, I/O order) receive
  opaque handles. They cannot reach payload bytes, clocks, the FP environment, the heap or I/O; state
  is a fixed block; loops carry static fuel; outputs exist only as `Hint<T>` values **[v0, M4]**.
- **Hint ports** connect policies to the **store core**, which validates every hint and falls back to
  the default policy on overrun or trap. The store core is certified once against *demonic* hints,
  with obligations **O1** hint validation, **O2** slab race freedom, **O3** arrival-order confluence,
  **O4** lossless tiers by per-slab content hash, and **O5** liveness (`n_slots ≥ 2·top_k + n_io + 2`)
  [RV: D2-A]. The certificate is graded `validated` (bounded model checking, a chaos suite and 100%
  core-mutant kill) until mechanised (DR-010).
- **One policy code for engine and simulator.** The simulator replays traces with *the same* policy
  code as the engine ("one flow, many handlers" [RV: D2-C]). A miscalibrated simulator produced
  Hearth's lookahead reversal; sharing code is the cheapest calibration guarantee **[v0, M4]**.
- **Completion-order compute, canonical-order combine.** Experts may finish in any order; the
  rank-order combine fixes the sum. Demand and prefetch queues are separate, with at least one reader
  reserved for demand [RV: D2-B] **[v0, M4–M5]**.

### 7.4 Tiers and placement

`Tier::{Nvme, Dram, Vram}` exists in the types from v0, with the residency types
`resident<T, Tier>`, `streamed<T, Tier>` and `cached<T, Tier, budget>`
([02 §14](architecture/02-compute.md)). v0 and v1 implement NVMe → DRAM only. **The VRAM tier is reserved**, so
adding the GPU tier needs no language change ("retrofitting placement is the expensive mistake" [G03]).
A `device(t)` value may never flow into a computation whose placement is decided at run time.

**GPU expert tier (owner-gated, DR-022) [by-trigger, D-06].** Canonical Q4/Q8 expert GEMV on sm_120
with exact int32 block sums and an ordered `add.rn` epilogue; gate in §13. ptxas and the driver JIT
stay in the trust base (SASS graded `tested`). Cross-device scope covers expert GEMV and the ops
placed with it. The first tier needs a validated `canon_v1::expf` in PTX (a fixed op-DAG, checked
structurally by T1) for SwiGLU. Only the attention core (sequential-in-t order) and `cr::` device
transcendentals wait: they need exhaustively validated PTX implementations and a fixed-chunk
attention order, which is the major canon version `canon.v2` (by-trigger, §6.4); RoPE sin/cos stay
host-computed ([02 §15.2–15.4](architecture/02-compute.md)). Because a cache-driven expert placement
is decided at run time, the tier's kernels must be `cross_device`. A lossless relayout separating
scales from the 34-byte Q4 blocks is in the space, because unaligned blocks hurt coalescing.

### 7.5 Cost signatures and the roofline

For each kernel and flow the compiler derives `bytes{nvme, dram_rd, dram_wr, pcie_h2d, pcie_d2h,
vram}`, ops per class and syncs. These are **symbolic** in load-bound parameters at build time,
**numeric** at load (against a measured machine profile) and **measured** at run time [P3 §4]
**[v0, M2: cost signatures and `mithc explain` v0]**. Each yields a floor `T_floor = max_ρ bytes_ρ / BW_ρ`, and `mithc explain` reports the
binding resource, the floor and the achieved fraction of roof. P3's worked example (one Qwen3 expert
projection, 768 × 32 blocks × 34 B = 835,584 B) gives a 10.9 µs floor at 77 GB/s, DRAM-bound
[inference, P3 §7]. Bounds carry soundness tiers: **phys** (datasheet peak), **emp** (audited
measurement) and **est** (model). Only phys and audited emp bounds may prune a search or quarantine a
result; est may only rank. A measured peak is a lower bound on the attainable roof, so an audited
emp term acts as an upper bound only with pre-registered headroom:
`emp_bound = min(phys, max observed peak × (1 + h))`, with h at least the measurement CI plus a
declared margin (e.g. 5%). Results between `emp_bound` and phys are **flagged for audit, not
quarantined**; pruning uses `emp_bound` with the same margin; a measurement beating a phys floor is
quarantined as an evaluator bug or a hack ([02 §13.2](architecture/02-compute.md)). In the simulated
pilot, physics-only rooflines pruned 0 of 144 candidates [RV: D3-ii]. Machine
profiles come from `mithc profile measure`, run inside the sealed evaluator (STREAM per CCD and
all-core, an NVMe request-size × queue-depth grid, PCIe transfers), so floors rest on this machine,
not on datasheets.

### 7.6 Inference-specific requirements

- **Batched prefill under canon.** Sequential-in-block float accumulation forbids K-splitting a float
  accumulation across threads. Quantised paths use exact int32 cross-thread partials instead, which
  canon licenses **[v0, M5]**. The parallelism cost for small per-expert batches is quantified in
  [02](architecture/02-compute.md).
- **Chunkwise recurrent scans (Kimi-K3 KDA) under canon.** This is an open Hearth item. Their grade
  (exact or `real(bound)`) and whether DAG-preserving schedules can parallelise them are analysed in
  02 **[later]**; the recurrent-state snapshot API is designed together with weight overlays (DR-025).
- **Reserved `approx` / cache effect.** Step caching and other output-changing reuse live only in the
  opt-in lossy lane **[reserved]**.
- **Visual generation.** No primitives in v1 (DR-024), only the general features above. Generative
  video is gated on a GPU backend (**later**, D-20).

### 7.7 Honest Hearth performance ceilings

Speed gains come from bytes, placement and scheduling, not from syntax.

| Workload (Ryzen 9 9950X, 64 GB DDR5, 990 PRO) | Today | Ceiling or prototype | Source |
|---|---|---|---|
| Qwen3-30B-A3B, Q4 experts + Q8 dense, in RAM, decode | 19–22 tok/s, measured, noisy | ≈ 34 tok/s lossless at short context and 77 GB/s measured DRAM; 28.8 tok/s at 4K context [inference, R08]; R11's 2.38 GB/token container count gives ~32 tok/s [inference]. Honest CPU headroom is ~1.3–1.5x, the upper figure at short context | [R08], [R11], brief |
| Same, llama.cpp | ~25 tok/s, noisy; not a clean head-to-head | — | brief |
| Attention value pass (prefill/long context) | 18 GMAC/s portable (already `restrict`), measured | 94 GMAC/s bit-identical register-blocked AVX-512 prototype, measured: a schedule gap (§9.3) | [R11] |
| GPU, backbone + experts in VRAM (G03's `dense+experts` mode, attention included: needs fixed-chunk attention, a canon change) | no GPU path | **SIMULATED** 23.2 → 112.4 tok/s for Qwen3-30B-A3B (4.8x) and 15.2 → 54.7 for gpt-oss-120b (3.6x). The GPU paths are uncalibrated and use the 672 GB/s VRAM peak while DRAM is discounted; the CPU baseline is simulated, not the measured 19–22 | [G03 F9] |
| GPU, DR-022 first tier (experts + Q8 dense GEMVs on the GPU, attention core on the CPU) | no GPU path | no simulated or measured figure yet. Per-layer CPU–GPU syncs over PCIe and WDDM can eat a 12–15 ms token budget, so the gate is measured end-to-end ≥ 2x CPU-only | [02 §13.4, §15](architecture/02-compute.md), [G03] |
| Kimi-K2-class (32B active, 1T total; 40 GB cache, Q8 backbone) on one NVMe | 1T-parameter synthetic container: 1.2–1.8 s/token worst case, measured | 0.8–2.9 tok/s band at plausible hit rates; all-in-DRAM cap ≈ 3.4 tok/s (4.5 with a Q4 backbone) [inference] | [R08] |
| Kimi-K3 (2.8T total, 104B active, ~109 GB BF16 trunk) on one NVMe | no real-model path yet | with a lossless BF16 trunk of which about 50 GB stays resident in 64 GB, (109 − ~50) ≈ 59 GB/token of trunk streams from NVMe at 7.16 GB/s → ≈ 8.2 s/token, **≤ ~0.12 tok/s** from the trunk alone; routed experts (≈ 25.8 GB/token, with almost no cache left) add ≈ 3.6 s, about 12 s/token [inference, 07 §11]. Hearth's simulator figures (0.36 tok/s NVMe-bound, 1.04 tok/s with every expert in DRAM; simulated, uncalibrated) model every layer as MLA with a resident Q8 backbone about a third the size of the BF16 trunk, so they are **not comparable** and are not lossless figures for K3 [07 §11]. kimi-k3-in-c measured 19.8 s/token at 64 GB on 2× EPYC 7763 with 3.2 GB/s reads [R06] | [R06], [07](architecture/07-hearth-port.md) |

Batch-1 Q4 decode runs about 56x below the Zen 5 ridge point (≈ 213 ops/byte) [inference, R08 §7.2;
at 4.0 GHz and 77 GB/s]. That is why a direct emitter buys almost nothing for decode GEMV (DR-009).
The GPU tier is the largest lossless lever for a different reason: it takes DRAM bytes off the CPU's
critical path and serves them from much faster VRAM.

---

## 8. Evidence and trust

Detailed in [03-trust](architecture/03-trust.md), the constitution.

### 8.1 Claims and admissible evidence

Evidence is organised by **claim kind**, not on one linear lattice (DR-007) **[v0]**. A linear order
would let a measurement stand in for a correctness proof, which is ill-typed.

| Claim kind | Meaning | Admissible evidence |
|---|---|---|
| `refines(impl, meaning)` | the realisation is bit-identical to its meaning, or meets its contract | for an exact slot: proof or validated, **never tested** |
| `confined(space)` | the candidate is a member of a certified space | proof only (the per-candidate membership check, relative to the space certificate) |
| `safe` | no out-of-bounds access, no UB, no unwanted panic | proof (types + T2) or tested (sanitisers, fuzzing) |
| `deterministic(scope)` | output is independent of scheduling, cache and I/O order | proof, validated, or tested against a named golden |
| `perf` | speed on named hardware | measured(hw, e-value, named same-machine baseline), or a one-sided phys bound |
| `quality(profile)` | a statistical quality property | measured on a hashed corpus; live for F1-A harness fitness and reference-agreement claims (such as numpy agreement), reserved for lossy profiles |

- **Correctness grades:** proof > validated > tested > assumed.
- **Performance grades:** measured(hw) > simulated > estimated > assumed.
- **Prune and bound tiers:** phys / emp(audited) / est. Only phys and audited emp may prune or
  quarantine; audited emp acts through `emp_bound`, and results between `emp_bound` and phys are
  flagged, not quarantined (§7.5).
- **Effective grade** = meet(evidence grade, spec-strength cap, grades of the trust base's premise
  components such as table entries, rewrite rules and space bases, and, for value-level claims only,
  the grades of the `deterministic` boundaries the output depends on by data flow). Input-universal
  claims (`refines`, `confined`, `safe`) are never capped by boundaries upstream of their inputs
  ([03 §3.2](architecture/03-trust.md), [01 §7.2](architecture/01-language.md)). The **code floor**,
  the grades of trusted code components (checkers, the T0 pass, elaboration), is printed beside it
  and compared with the slot's `code_floor`; it is not met into the effective grade.
- **Every grade is relative to a declared trust base**: a sound checker, a semantics table that
  matches silicon on its validated domain, sound space theorems, correct hardware and OS, and isolation
  that holds. `mithc ledger why --trust-base` prints the derivation, including the trust base's own
  entries and their grades [P2 §5.1].
- **`confined` admits only a checker verdict** (the T0 decision on the binary), `proof` in form. In
  03's format, the T0 verdict's grade is: effective `validated(partition)` from its table premises;
  for `confined(S)`, effective `validated(bounded)` via the store-core theorem that is S's soundness
  basis; code floor `tested` (the T0 pass, until Lean mechanisation, D-08, fires), printed, not met
  ([03 §3.2, §3.4](architecture/03-trust.md)). A `timing_only` slot requiring `confined =
  "validated"` with `code_floor = "tested"` is therefore satisfiable (03 §3.5).

### 8.2 Verification tiers and the semantics table

- **T0** checks types, effects, grades, ownership and layouts. For policy and evolve code it adds
  **binary-level confinement**: an instruction allowlist that bans RDTSC/RDTSCP/RDPMC/CPUID/LDMXCSR/
  FLDCW, syscalls and indirect calls; stores only to the state block or stack; fuel. The front-end
  effect checker thereby becomes advisory rather than trusted **[v0: types from M1, binary
  confinement at M4]**.
- **T1** is an FP-DAG matcher modulo an audited IEEE-exact rewrite list, using schedule-supplied
  correspondence maps and a lockstep loop rule. Every rule has side conditions, including the
  **NaN-order condition**: commuting an add or a mul is exact only if no order-sensitive consumer
  (MAXPS and MINPS return their second operand on NaN) sits before NaN canonicalisation. T1 is sound
  and incomplete; "unknown" means reject **[X2 spike in M0; object audit v0, M2]**.
- **What T1 compares against.** T1 checks the object code against the meaning's KIR op-DAG and the
  T2 obligations elaborated from the `kernel fn` source. A mis-elaborated meaning (swapped operands,
  a dropped operation, a missing overflow obligation) would be certified faithfully against the
  wrong DAG, and a comptime bug would change both sides of T1 consistently. So in v0 the
  **elaboration of exact meanings into KIR, comptime included, is a trusted code component** of
  every exact claim's trust base, graded `tested` ([03 §3.4, §14](architecture/03-trust.md)). It
  sets only the code floor, not the effective grade, so exact kernels keep `validated` effective
  grades and DR-021 holds. It is mitigated by a **second comptime evaluation path** (kernel-reachable
  comptime values recomputed by the comptime code compiled through B1 and run natively, with byte
  equality required), by `mithi` running the meaning differentially on the hash corpus, and by
  intent checks against the numpy reference. **By-trigger upgrade:** a small independent
  kernel-subset extractor inside `mithcheck` (first-order loops, index arithmetic, scalar FP and
  integer operations) re-derives the op-DAG and the T2 obligations from the source, so `mithc`'s
  KIR becomes only a hint and a cache key and elaboration leaves the TCB. It is budgeted within
  the ≤ 3,500-line T1 cap (03 §14) and registered as [ROADMAP D-23](ROADMAP.md) with its trigger:
  any elaboration bug found that changed a KIR DAG, or before the first grant or ADR that rests on T1
  evidence (with D-09).
- **T2** discharges bit-vector SMT obligations (ranges, overflow, saturation, alignment) with
  certificates that a small checker re-verifies, for example the Q4 `maddubs` bound 3,810 and the Q8
  sign-trick bound 32,512 < 32,767 [R07] **[v0, M2]**.
- **T3** tolerance certificates are **reserved**, opt-in and lossy-labelled.
- **The semantics table** is hand-written and keyed by Intel XED iclass (Apache-2.0), with an explicit
  x86 FP-environment layer. It is fuzz-validated on Zen 5 (NaN payloads in each operand position, ±0,
  subnormals, every mask pattern), with Bochs as a second oracle. It generates SMT terms, the C
  reference interpreter, Exo-style instruction bodies and later Lean definitions. G02 estimates 25–40
  parameterised families in 1.5–3k lines [inference, G02]. Intel's XML has no open licence and falls
  under Intel's site terms (medium confidence, not legal advice), so the table is hand-written from
  the SDM [G02].

**Where T1 runs (DR-008).** First comes an **X0 instruction census** of what MSVC, Clang and GCC
actually emit for Hearth's kernels, including `_mm512_reduce_add_ps`, horizontal shuffles, unrolling,
rotation and spills. G02's ~105 instruction forms are implied by the intrinsics, not observed in
compiler output. Then an **X2 spike** on transliterated intrinsic IR with correspondence maps. Only
then the **object audit** of the ~20 hot kernels. A variant that fails to lift or match drops to
`tested` and is **not dispatched in release profiles**.

### 8.3 The ledger

- **Key:** H(code closure, spec hash, toolchain hash, target, hardware fingerprint). Any change to a
  component re-keys the entry, so evidence invalidates itself.
- **Storage (DR-019):** admitted facts are **gate-signed files named by hash under `.mith/ledger/`**
  in git and are union-mergeable. Operations fall into three classes: **FREE** (monotone: add a
  definition, evidence or a tombstone), **SEAL** (non-monotone but mechanical: bind a name, release a
  version) and **AUTHORITY** (normative: specs, goldens, defaults, F0, editions, grants). Raw samples
  and certificates are content-addressed blobs in the data directory, outside the repository and
  outside cloud-synced folders **[v0: local ledger at M1; signed ledger, tombstones and revisit at
  M3]**.
- **Contents of a fact:** claim kind and property; evidence blob hash and grade; trust-base hashes;
  the producing principal (role, model family, version, prompt hash); cost; status (live, stale,
  tombstone, quarantined); scope; triggers.
- The same ledger is the Forge archive, the specialisation cache and the handover evidence.

- **Scaling.** File-per-fact stands (DR-019). A SEAL compaction packs older facts into a signed
  segment and records the ledger's Merkle root, preserving membership
  ([03 §4.2](architecture/03-trust.md)); its trigger is D-13 (git on `.mith/ledger/` exceeds the CI
  budget, [ROADMAP §9](ROADMAP.md)).

### 8.4 Certified spaces

| Space | What may change | One-time certificate | Per-candidate check | Status |
|---|---|---|---|---|
| `timing_only` policy | eviction, prefetch, I/O order, mirror choice | store-core theorem O1–O5 | T0 confinement on the binary (ms) | v0 (M4) |
| `schedule` for a meaning | tiling, lane mapping, disjoint parallel split, prefetch, unrolling | primitives preserve the op-DAG (gives completeness only) | T1 on the emitted binary (gives soundness) | v0 (M2) |
| `rewrite(licence)` | integer re-association under overflow-free ranges | each rule proved against the semantics | T2 side conditions | v0 (M2) |
| `relayout` | lossless repacks into kernel-native layouts | derived pack/unpack are inverses | round-trip check per instance | v0 (M2); Forge search v1 (M6) |
| placement | CPU vs GPU, DRAM vs VRAM | `cross_device` canonical kernels validated on both backends | plan check | owner-gated, by-trigger |
| `refines(spec)` (free body) | anything | none | full T1/T2 certificate; tests never suffice | v0 (M2) |
| `real(bound)`, `approx` | reassociation, lossy variants | bound calculus / quality gates | T3 / statistical | reserved |

Each space has two separate properties: **soundness**, which is trusted (anything the check accepts
preserves outputs), and **completeness-for-members**, which is untrusted and only tested (legitimate
members are not spuriously rejected). Soundness rests on a one-time space certificate where one
exists plus a per-build membership check on the emitted binary; for schedules there is no one-time
basis, and the per-build T1 check alone carries soundness. Spaces are deliberately incomplete: incompleteness is accepted,
unsoundness is not [P2 §5.3].

### 8.5 The promotion rule

The rule is normative in [03 §7.1](architecture/03-trust.md) and is copied here verbatim:

```text
promote(c, slot, H) <=>
     check_S(c)                                   -- T0 or T1/T2: decidable, cached, no agent-written proof
  && eff(correctness(c)) >= slot.required_grade   -- §3.2: premises and the spec-strength cap included
  && floor(correctness(c)) >= slot.code_floor     -- §3.2: checkers and elaboration
  && E_t(perf(c) vs perf(inc) on H) >= 1/alpha_i  -- anytime-valid e-process; alpha_i charged when the test opens
  && plausible(c, H)                              -- no measurement beats a validated phys/emp floor
  && authority(slot)                              -- standing grant (opt-in profile) or Owner ADR (default)
```

The `§` references inside the block are to 03. Spec strength enters once, through the cap inside
`eff` (03 §3.2, §8.4); there is no separate `strength(slot.spec) >= slot.required_strength`
conjunct, which would count strength twice. A failure stops spending: correctness failures and
pruned candidates never touch the α budget.

An **e-value** is a non-negative statistic whose expectation under the null is at most 1; an
**e-process** keeps that property at every stopping time, so a test may stop as soon as
e ≥ 1/α_i ("anytime-valid"). The guarantee, under the declared trust base, has two parts
[P2 §8.1, 03 §7.2, 06 §6.5]:

- **Outputs.** Every promoted candidate in an exact slot produces outputs identical to its
  meaning's. For `timing_only` slots, outputs are identical to the fallback configuration's,
  assuming the store-core theorem holds beyond its bounded-model-checked bound (it is graded
  `validated`, not `proof`).
- **False promotions.** A false promotion is one whose true effect is no improvement: the
  superiority null is E[d] ≥ 0 ([06 §6.2](architecture/06-forge.md)), so the minimum detectable
  effect sizes each test but is not part of the guarantee. α_i is charged when a confirmatory test
  opens, whatever its outcome, and the test's threshold is max(20, 1/α_i), keeping DR-015's floor.
  The guarantee has **two tiers**
  ([06 §6.5](architecture/06-forge.md), [03 §7.2, §7.5](architecture/03-trust.md)):
  - *Defaults and F1-A promotions: a union-bound α budget.* Per period and slot family,
    E[number of false promotions] ≤ Σα_i, and P(any false promotion) ≤ Σα_i when Σα_i < 1. With
    e ≥ 20 each test costs 0.05, so the Owner sizes the per-period budget.
  - *Grant-promoted opt-in per-machine profiles: online FDR.* Each grant runs an e-LOND stream at
    FDR level q = 0.20 [target]: test t opens with α_t = min(0.05, q · γ_t · (D + 1)), where γ is a
    pre-registered sequence summing to at most 1 and D counts the grant's promotions so far, so
    under γ = uniform(40) the first threshold is e ≥ 200. The expected share of false promotions
    among the grant's promotions is at most q at every point in the stream [inference]. Profiles
    are opt-in, revocable and output-preserving, so a false one costs speed, never correctness.

**Promotion authority (DR-015):** standing, scoped, expiring, revocable **grants** auto-promote
output-preserving winners into opt-in per-machine profiles (e ≥ max(20, 1/α_t) on the grant's
e-LOND stream, plus a plausibility pass). Every shipped default, including `timing_only` defaults
of the ADR-0004 class, needs an ADR signed by the Owner. `approx` is never a default.

### 8.6 Roles, spec escrow and the Gatekeeper

| Role | May write | May never write |
|---|---|---|
| Author | meanings, specs, fault models | implementations, schedules, gate policy |
| Builder | implementations, schedules, policies, layouts | specs, meanings, goldens, mutant pools, the harness |
| Prover | proofs and certificates for named obligations | specs, implementations |
| Adversary | sealed mutant pools, chaos policies, planted kernels | specs, implementations, the gate |
| Gatekeeper | runs the gate; assembles promotion dossiers | the gate's code, thresholds or alpha budget |
| Owner (human key) | admits specs; ratifies defaults; amends the TCB; editions; grants | — |

The **Gatekeeper is deterministic code** in F0 plus the Owner's key; an LLM holding the role can only
run it. Change sets are judged as content-addressed objects, never as paths: Hearth's golden gate was
bypassed through symlinks, case twins and 8.3 names [RV: D2-E]. **Spec strength** is two-sided: the
kill rate on a sealed fault model (`numerics_v1`: FMA contraction, lane or tree change, RNE→truncate,
the 127/128 clamp, a dropped scale, tie flips, NaN canonicalisation, a RoPE variant swap and more),
vacuity witnesses that must fail, latitude, and measured independence (distinct model families for
Author and Builder). LLM-written specs are sound and complete only about half the time [R03], which is
why specs are escrowed. Agents have a first-class **`abandon`** verb: an abort option cut GPT-5's
cheating on conflicting tasks from 54% to 9% [RV: D2-E]. A **friction rule** blocks a fourth identical
failing retry until a root-cause note exists.

### 8.7 Every documented hack has a named counter

The full table is in [03-trust](architecture/03-trust.md); the pattern [R01, RV: D2-E]: faked logs
and removed hallucination markers (DGM) meet sealed, harness-owned oracles and gate-signed results;
unwatched-stream timing (32.8% of 250 CUDA-L1 kernels) meets a runtime that joins all threads, streams
and I/O before stopping the clock; timer overwrites, evaluator monkey-patching and similar exploits
(reward hacking of all kinds in 30.4% of RE-Bench runs by o3 and other frontier models [R01]) meet
the absence of a `time` capability, T0's RDTSC/RDPMC ban and an evaluator in a separate process
built by a frozen toolchain; memory-reuse reads meet poisoned allocations; hard-coded outputs meet hidden held-out
shapes and `refines` claims that quantify over all inputs; lucky runs meet e-values and the alpha
budget; physics-violating wins meet quarantine against a *validated* bound; vacuous specs meet escrow
and vacuity witnesses; special-casing meets `abandon`.

### 8.8 Threat model

- **Prompt injection through archived text.** Tombstone rationale, comments, diagnostics and handover
  rationale that models read are **untrusted data**, never instructions. Proposer contexts mark them
  as such, and no archived text can carry authority ([03](architecture/03-trust.md),
  [06](architecture/06-forge.md)).
- **The one sanctioned instruction channel.** F1-A card atoms and diagnostic templates are, by
  design, instructions to models. Only promoted ones reach production: they enter after maintainer
  promotion, are content-addressed and hash-pinned in AGENTS.md, and unpromoted atoms exist only
  inside harness sandboxes.
- **Key management on one desktop.** Gate-signing and Owner keys are separate, and AUTHORITY facts
  require the Owner key. [03](architecture/03-trust.md) specifies storage, rotation and revocation.
- **A compromised machine.** Ledger integrity is relative to the machine. On compromise, the trust
  base is declared broken, keys rotate, and every claim signed since the last known-good root is
  re-validated.
- **Trusting trust.** A candidate compiler never builds the gate, the checkers or the harness. They
  are built by a frozen bootstrap toolchain pinned by hash.

### 8.9 What is trusted

The caps are those of [03 §14](architecture/03-trust.md), which is authoritative: a [target] cap on
**line-reviewed trusted code**, allocated from the proposals' [inference] estimates; growth needs an
ADR.

| Component | Budget [target] | Defence |
|---|---|---|
| `mithcheck` T1 matcher, lifter (shared with T0), footprint check, loop rules; the by-trigger kernel-subset extractor (§8.2) fits within this cap | ≤ 3,500 lines | planted corpus of ≥ 200 wrong kernels with zero acceptances; 100% core-mutant kill; second checker by-trigger (D-09) |
| T0 binary confinement pass | ≤ 500 | planted policy hacks |
| T2 certificate checkers (LRAT, Alethe/CPC subset) | ≤ 800 | malformed-certificate corpus; certificates from a second solver |
| Gate: promotion rule, α accounting, authority, signing | ≤ 1,200 | attack suite, including Hearth's golden-gate bypasses |
| Measurement service: clock, joins, poisoning, interleaving, fingerprint | ≤ 1,500 | planted timing hacks |
| Ledger kernel: schema, signatures, invalidation, AUTHORITY checks | ≤ 800 | property tests; replay of Hearth history |
| Audited `std_platform` `unsafe` | ≤ 1,500 across OSes (the M4 gate; the memory-model kill is in §13) | human line review; ASan/TSan; permutation scheduler |
| **Total line-reviewed code** | **≤ 9,800** | |

**Trusted data, validated empirically rather than line by line:** the x86 semantics table and its
generator (1.5–3k lines [G02]; Zen 5 fuzzing, Bochs as second oracle), the exact-rewrite list (≤ 30
rules, each proved by Z3 FPA or exhaustive binary32, Lean once stable, DR-010) and the store-core
theorem with its bounded model (`validated`). **Trusted code validated empirically:** the
elaboration of exact meanings into KIR, comptime included (`tested`; second comptime evaluation
path, `mithi` differential, numpy reference; §8.2), until the by-trigger extractor removes it from
the TCB, and the comprehension-harness scorer and hidden oracles (`tested`; Gatekeeper-owned and
sealed) ([03 §14](architecture/03-trust.md)).

Not trusted: the parser, the front end and type checker (until mechanised; their verdicts are
re-checked where it matters) except the elaboration of exact meanings above, schedules, lowering,
the C compiler *for audited kernels*, the Forge and every agent. The C compiler **is** trusted for
non-kernel code; that trust is mitigated by the C tests, the hash corpus, `mithi` differential
testing and format-derived parsers.

---

## 9. Compiler, backends and runtime

Detailed in [04-toolchain](architecture/04-toolchain.md).

### 9.1 Pipeline and IRs

```
.mith --parse--> Syntax (lossless CST, Lark-conformant; anchors for edits and formatting)
      --> HIR   (names resolved; holes as typed nodes; definition hashes, alpha-normalised)
      --> THIR  (types, effect rows, capabilities, ownership, fidelity, determinism scope)
      --> MIR = MCore (small normative core; MVS moves explicit; mithi's MIR mode localises faults)
      --> KIR   (kernel fns: index loops + layouts + explicit FP op-DAG + integer subterms;
                 applying a schedule emits correspondence maps and T1/T2 obligations)
backends: C11 (strict FP) | LIR (lifted x86 for audit; later a direct emitter) | PIR (PTX, later)
audit:    kernel object --XED decode--> LIR --T1/T2 against KIR--> witness --> ledger
every phase emits Fact Plane (Datalog) relations
oracle:   mithi independent mode (own parser and checker, from the Lark grammar and normative core)
```

- **`mithi` has two modes** ([04 §2](architecture/04-toolchain.md)). The independent mode has its
  own parser and checker and shares no lowering code with `mithc`; it is the DR-010 differential
  oracle. The MIR mode interprets `mithc`'s serialised MIR and only localises a disagreement to the
  front end or the back end, because it shares the front end's bugs.

- **Query database** (salsa-style), keyed by content hashes plus a toolchain hash. A definition hash
  is the normalised AST with references replaced by their targets' interface hashes, so editing a body
  does not re-check callers. Expensive results (T1 witnesses, certificates, measurements) persist in
  the ledger under the same keys. `mithc serve` keeps the database warm **[v0]**.
- **Latency targets:** one-definition re-check < 300 ms at 30k lines [target, P5 §4]; `mithc check`
  p50 ≤ 200 ms on a Hearth-sized corpus [target, P1 §4]. These exclude C compilation and the object
  audit, so 04 sets separate edit-loop and CI budgets and caches audited objects by closure hash.
- **Fact Plane:** a decidable Datalog layer over compiler facts, used for capability audits, API
  search, evidence policies and tombstone triggers **[v0: relations and fixed rules from M1, trigger
  evaluation at M3; user-written rules by-trigger, D-12]**.

### 9.2 Backends

| Backend | Scope | Status |
|---|---|---|
| **B1 strict C11** | all code; MSVC `/fp:precise`, GCC/Clang `-ffp-contract=off`, no fast-math; emits Hearth's internal `hx_*` symbols. The generated C is **checked in and regenerated byte-for-byte in CI** by a pinned `mithc`, which satisfies INV-DEP literally during the port (DR-026) | v0 |
| **B1.5 object audit** | XED-decode MSVC/Clang kernel objects → LIR → T1, for the ~20 hot kernels; unmatched variants drop to `tested` and are not dispatched in release | v0 (M2) |
| **B2 PTX expert tier** | canonical expert GEMV on sm_120 via `nvcuda.dll`, explicit `.rn`; comes **before** any direct emitter if audit coverage is ≥ 95% | owner-gated, by-trigger (D-06) |
| **B3 direct x86 emitter** | staged-kernel subset; only if the audit finds compiler rewrites that cannot be pinned, or a ≥ 5% kernel gap attributable to codegen; never for bandwidth-bound decode GEMV (DR-009) | by-trigger |
| **B4 copy-and-patch JIT** | load-time residuals; W^X; `FlushInstructionCache` | by-trigger |
| LLVM | optional; never trusted | later |

### 9.3 C11 lowering rules

- **`restrict` from alias facts** (mutable value semantics plus exclusive `&mut`; DR-027) is needed
  for parity with Hearth's hand-annotated C, whose `value_sum` already declares every pointer
  `HX_RESTRICT`, and it covers code nobody annotated. Its gain is measured per port stage, not
  assumed. The attention value pass's 18 → 94 GMAC/s gap (measured [R11]) is a register-blocking
  schedule gap, closed by a T1-validated exact F1 schedule (§7.1, ROADMAP M6), not by `restrict`
  ([04 §6.4](architecture/04-toolchain.md)) **[v0, M2]**.
- **Values lower to out-parameters**, with no hidden memcpy above N bytes on hot paths (checked)
  **[v0, M2]**.
- **Bounds-check elision with a tax budget:** proved checks vanish, each port stage has a measured
  overhead gate, and kernels admit no unprovable checks (DR-011).
- **Strict FP flags** are pinned per compiler; `#line` directives map generated C back to `.mith`.
- **Assurance for non-kernel C** (store, parser, API) comes from the C tests, the cross-binary hash
  corpus, `mithi` differential testing and format-derived parsers. Translation validation is **not**
  planned for control-heavy code.
- **Cross-compiler and cross-OS audit variance**, and validation of arm64 NEON (4-lane registers
  composing `sum16`), are covered in 04 **[NEON schedules by-trigger, D-17]**.

> **Reviewer note (DR-027).** The outline's DR-027 credits `restrict` with the 18 → 94 GMAC/s
> value-pass gap. Hearth's loop already uses `restrict`, so this document keeps the decision and
> corrects the attribution, as [DECISIONS](DECISIONS.md) reviewer note 1 and 04 §6.4 do.

### 9.4 Runtime and `std_platform`

There is no hidden runtime, no GC and no unwinding. The audited `std_platform` layer **[v0: over
Hearth's C platform functions at M4; native layer at S6b, M5]**
provides `Mutex<T>` with a scoped `with_lock`, `Condvar`, `Arena` → 4096-aligned `SlabBuf`,
`Frozen<T>` with `into_unique`, `File.read_at` (Windows OVERLAPPED + NO_BUFFERING; POSIX `pread` +
`O_DIRECT` or `F_NOCACHE`), a persistent spin-then-sleep pool (it must match Hearth's measured
~0.75 µs per 16-thread round trip [R11]) and scoped services that hold capabilities. G05 judged that
Hearth's `store.c` is expressible on this layer with **no user-level `unsafe`** [inference,
medium-high, G05]. Large pages and TLB behaviour for a 30 GB slab arena on Windows
(SeLockMemoryPrivilege, with a fallback when it is denied) are budgeted in 04. Test builds swap in a
**loom-style permutation scheduler**, because Hearth's real concurrency risk is liveness bugs in safe
code [G05]. **Hot-swap** happens only at quiescent token-boundary epochs (a release-store of a version
root, with `Frozen` refcounts for reclamation). There is no self-modifying code **[later]**.

### 9.5 Debugging, profiling and dogfooding

- PDB/DWARF symbol names map to definition hashes, and ETW and AMD uProf attribution (Windows has no
  `perf_event_open`) reports per definition **[v0 symbol and `#line` maps; ETW/uProf attribution
  v1]**.
- **How `mithc` is built.** In Rust, by agents working under Mithril's own protocol (roles, ledger,
  handovers), with `mithi`, an independent tree-walking interpreter, as the differential oracle and the
  `comptime` evaluator. A front-end bug is caught by disagreement with `mithi`, by the C tests, by the
  hash corpus or, for kernel lowering, by T1 on the object code. T1 cannot see an elaboration bug in
  a meaning itself; the second comptime evaluation path, `mithi` and the numpy reference cover that
  (§8.2).
- **Self-hosting** is decided only after M7 (DR-026).

---

## 10. The agent protocol

Detailed in [05-agent-protocol](architecture/05-agent-protocol.md).

### 10.1 The loop

```text
mithc resume <manifest>   |   mithc pack <target> --budget 6000   # orient: Tier 0 + project card + pack
mithc outline store::evict                                        # signatures only; bodies stay out
mithc hole eviction_score                                         # expected type, bindings, obligations
mithc edit --anchor store::evict::pick_victim@h:3fa0 ...          # edit + parse + type-check, atomic
mithc check --json                                                # grouped root-cause diagnostics
mithc prove q4_matvec --target x86_64.avx512                      # T1/T2; counterexamples as values
mithc bench q4_matvec_avx512 --vs hearth_c_ref                    # a request: the gate owns the clock
mithc explain q4_matvec --profile this-pc                         # floor, binding resource, % of roof
mithc handover                                                    # manifest generated from the journal
mithc abandon --reason spec_conflict                              # first-class "cannot satisfy"
```

Every verb takes `--json`, is exposed over MCP (`mithc mcp`), emits SARIF 2.1.0 where relevant, and
ends every response with `next: [...]`, the one to three highest-value next commands. The canonical
verbs are `check, hole, edit, outline, search, pack, propagate, prove, audit, bench, explain, profile
measure, ledger, revisit, resume, handover, guide, fix, fmt, lift`, plus `abandon`. Testing and
mutation analysis are `mithc check --tests` and `mithc check --mutate`, so the list stays closed.
Every verb is **v0**, by milestone ([05 §11](architecture/05-agent-protocol.md)):

| Milestone | Verbs |
|---|---|
| M1 | `check`, `hole`, `search`, `edit`, `outline`, `fix`, `fmt`, `guide`, `pack`, `propagate`, `handover`, `resume`, `abandon` (ledger-backed from M3), `lift`; MCP and SARIF |
| M2 | `prove`, `audit`, `explain`, `bench`, `profile measure` |
| M3 | `ledger`, `revisit` |
| by-trigger (D-10) | full LSP |

### 10.2 Holes, search and propagation

`mithc hole` returns the expected type, the bindings in scope, the obligations, candidate functions and
the relevant false-friend rows. Typed-hole context is the best-measured agent lever in the literature
(Hazel/ChatLSP: 3x tests passed for GPT-4, 10x for StarCoder2 [R04]); type definitions were the
single most useful context in Hazel's study [R03]. `mithc search --type "fn(&[f32], &[f32]) -> f32" --uses "{}"` returns only
existing hashes, which prevents hallucinated APIs. `mithc propagate` turns every dependent broken by a
signature change into a typed hole, so a cross-module change becomes a list of local work items;
cross-file changes are where agents degrade [R03].

### 10.3 The edit protocol

Edits address a definition path plus its content hash, never a line number: `replace_def`,
`replace_in` (the search text must match exactly once inside that definition), `insert_after`,
`fill_hole`, `rename` (no hash change, because names are metadata) and `delete_def`. A batch is parsed,
formatted and type-checked atomically, and the response *is* the check result, with the new hashes,
the invalidated evidence and `next`. A stale hash returns `StaleAnchor` with the current text; nothing
is applied fuzzily. The envelope is flat, non-recursive JSON with code as a string payload: Claude's
structured outputs accept only non-recursive schemas, and wrapping code in JSON lowers quality [R03].
Plain file edits remain legal, because text is the truth. The protocol has its own kill criterion: if
it beats `str_replace` plus format-on-save by nothing, it leaves Tier 0 [P1 §10].

### 10.4 Diagnostics

Diagnostics are JSON first, with one root cause per group and cascades folded (grouping took GPT-3.5
from 4.97% to 44.76% fixed on RustAssistant's benchmark, measured [R03]), stable codes, and anchors
instead of line numbers (SARIF carries lines for human tools). Fix applicability extends rustc's
levels: **Safe** (batch-applicable), **InterfaceChanging** (shows how many dependents become holes),
**MeaningChanging** (lists the ledger evidence it invalidates and the obligations it creates),
**SpecTouching** (Author role only; never auto-applied) and **HasPlaceholders**. `FalseFriend`
diagnostics name the Rust prior and the Mithril rule.

### 10.5 Cards, context packs and handovers

- **Cards [v0].** Tier 0 is ≤ 8 KB, embedded in AGENTS.md rather than a skill (on-demand skills were
  never invoked in 56% of Vercel's runs [G01]). The project card is ≤ 4 KB. Tier 1 is three modules of
  5–15k tokens served by `mithc guide`; Tier 2 is the retrieved manual; the normative core is ≤ 30k
  words plus a machine-readable core. An 8 KB always-on index lifted one pass rate from 53% to 100%,
  measured, while self-generated skills scored 8–12 points *below* no skill [G01]. Maintainers curate
  the cards, and their budgets fail CI.
- **Context packs [v0, M1].** In priority order: the target definition; callee and caller signatures
  without bodies; types in the closure; governing specs with their strength; evidence status; the
  false-friend rows for constructs present; relevant invariants verbatim; one example. The pack is
  truncated to budget and ends with an index of omitted items. `#[closure_budget(N)]` makes context
  locality a compile-time property of a module.
- **Handovers [v0, M1; ledger-backed from M3].** Facts come only from the toolchain journal and the
  ledger: commands actually run with exit codes, evidence added and invalidated, open holes, typed
  measurements (`kind` mandatory), invariants touched and tombstones created. The agent writes only length-capped `rationale` and
  `next_actions`, which closes DGM's log-faking class. `mithc resume` rebuilds the orientation pack.

### 10.6 The comprehension harness and the Surface Lab

- **Sealed task families** (Gatekeeper-owned, rotated each epoch): T-Q4 bit-exact Q4 dot and matvec;
  T-ACTQ activation quantisation; T-ROUTE grouped top-k with lower-index ties; T-NORM RMSNorm and
  softmax; T-EVICT a `timing_only` policy; T-STORE a slab arena with pins and 4096 alignment; T-FMT a
  bounded container parser; T-CTRL a mutex-guarded queue and a rank-order combine; and, from M1,
  T-XMOD (a cross-module signature change) and T-CONFLICT (spec and tests contradict; the correct
  outcome is `abandon`). Every oracle kills ≥ 95% of mutants, `numerics_v1` included.
- **Arms (six):** Mithril; **Mithril without traits** (traits rejected by a Dc diagnostic, so the
  cost of their absence is measured, DR-005); Rust; C11; **Rust + Mithril tooling**, from day one,
  so the surface is judged against its cheapest competitor; and obfuscated-Mithril, which separates
  comprehension from guessability. At X1 the tooling arm gets only the **M0 tooling kit** (a
  rust-analyzer shim answering `todo!()` holes, and the false-friend table as a lint pass over
  Rust), so it is a floor for that competitor; `mithc lift` (and the ledger facts it derives) and
  full diagnostics join at M1. If the kit is not ready when the held-out runs start, the arm is
  dropped from X1 and starts at M1 ([ROADMAP §3.2](ROADMAP.md)).
- **Metrics:** **VP@1** (verified pass@1) and **CABW** (the checker-accepted-but-wrong rate, judged by
  a hidden oracle) are co-primary; tokens, turns and dollars per verified pass and the first-compile
  rate are secondary.
- **Statistics:** ≥ 60 held-out items, task-clustered mixed-effects analysis, ≥ 2 model families, and
  a power analysis published with each threshold. The often-quoted ~1.5k attempts per arm for a
  5-point difference [inference, P1 §7.11] assumes independent attempts; with task-clustered
  variance, more items beat more attempts ([05 §13](architecture/05-agent-protocol.md)). Each kill
  is pre-registered with its operating characteristics (the X1 VP@1 kill fires with probability
  ≤ 10% at a true 5-point gap and ≥ 90% at 25 [target]), and the item count grows if 60 items
  cannot meet them. Screening uses ~100 IRT-selected (item response theory) items; full runs are
  reserved for kill criteria and editions.
- **Surface Lab:** for each construct, arms familiar / familiar with a mandatory disambiguator /
  alien / obfuscated. The rule picks the arm that minimises tokens per verified pass subject to
  false-friend incidence ≤ τ. A decay falsifier re-runs every model generation, because priors shift
  as Mithril code enters training corpora.
- **Subset rejection rate:** how much idiomatic agent-written Rust (iterator chains, closures, traits,
  returned references) the subset rejects is measured explicitly. It is the real cold-start tax of
  the subset rule.
- **The lifter**, `mithc lift --from c|rust`, is the cold-start escape hatch and the port's first tool
  (it maps `nearbyintf` to `round_ties_even` and flags C-prior contraction).
- **Constrained decoding** with grammar and type masks on Hearth-hosted local models is **deferred by
  trigger** and never co-scheduled with quiet-machine measurement (DR-023).

---

## 11. The Forge and revisit

Detailed in [06-forge](architecture/06-forge.md).

### 11.1 Levels

| Level | What may change | Correctness from | Fitness | Promotion | Status |
|---|---|---|---|---|---|
| **F0** trusted core | checkers, semantics table, gate, harness, ledger kernel | human change, review, attack suites | — | Owner (AUTHORITY) | frozen; the Forge cannot write it |
| **F1** artifacts | `timing_only` policies, exact schedules, lossless layouts; placements by-trigger (F1-place, after the DR-022 gate) | space certificate or per-candidate T1/T2 | bytes/token, stall time, measured time with e-values | grant → opt-in profile; ADR → default | **v0**: simulator pilot in M0, live engine at M4; campaigns **v1** (M6) |
| **F1-A** agent interface | card atoms, diagnostic templates, hole and pack ranking, agent scaffolds | none needed for semantics: it cannot change program semantics directly, and its effect on outputs (through what agents write) is measured by CABW. Fix applicability classes, fix replacement content, the Safe-fix set and evidence-invalidation lists stay outside its genome (only wording and order evolve), and a CI check rejects F1-A deltas that touch them | held-out VP@1, CABW, tokens per verified pass | maintainer review + harness gate | **v1** (M6) |
| **F2** compiler | heuristics among certified rewrites; new rewrite rules with proof obligations | translation validation in CI; rules proved | held-out shapes on two microarchitectures | ADR | later: after M5 (D-15, DR-016) |
| **F3** language and stdlib | editions | human ADR with harness evidence; corpus-preserving migration | harness on refreshed held-out suites | Owner ADR, always | later (Edition 1 at M7 is a human ADR) |
| **Fm** meta | selection policy, budget split | counterfactual replay on the archive, then a capped shadow run | archive productivity | human | later |

**F1-A is the DGM-proper loop.** DGM's own measured gains came from better editing tools and context
management [R01, R03]. Evolving the agents' card, diagnostics and scaffolds for writing Mithril,
scored by a held-out harness with leave-one-atom-out ablations and suite rotation, under the same
integrity rules, is the most DGM-faithful loop available. It cannot change program semantics
directly; it steers what agents write, so CABW is a co-primary fitness term.

### 11.2 The evaluation cascade

Cheapest first; each stage records its result, and failing a stage stops further spending: normalise
and deduplicate (e-graph, hash) → type, effect and space check → replay-conditioned sound pruning with
a `PruneCert` → correctness (T1/T2) → simulator ranking (est tier: it ranks, never decides) →
quiet-machine measurement → held-out macro run → plausibility gate (quarantine, not rejection) →
e-value against the alpha budget → archive (a niche elite or a scoped tombstone) → promotion [P4 §8.5].

- **Replay-conditioned exact-byte pruning is sound only for `timing_blind` configurations** (every
  byte-moving decision reads only the logical event stream). Completion-driven prefetch is
  timing-dependent and gets only MIN bounds, which pruned nothing. In the simulated pilot
  (144 candidates: 6 eviction policies × 6 prefetch settings × 4 cache sizes), replay bounds pruned
  16–41% per cache size and 66% jointly; some pruned candidates are timing-dependent in the real
  engine, so the real-engine fraction is expected to be lower and is gated at M4 [RV: D3-ii;
  06 §5.4].
- **Plausibility quarantine needs a validated bound first.** Hearth's own "Belady bounds" were beaten
  twice, both times through bugs, so a bound earns quarantine power only after audit. An audited
  measured peak only flags: results between `emp_bound` and phys go to audit, not quarantine (§7.5).
- **Objectives** are wall time and NVMe bytes per token, with demand-stall time as the diagnostic.
  **Never hit rate:** Hearth's depth-4 lookahead raised hits from 73% to 86% and cut decode from 13.0
  to 10.0 tok/s, measured.

### 11.3 Archive and selection

The archive is a view over ledger facts: quality-diversity niches over hardware × shape × model ×
grade; HGM-style Thompson sampling over clades with a DGM-style non-zero floor for dormant lineages;
semantic duplicates rejected before any spend. DGM's ablation is why the archive exists: SWE-bench
went from 20.0% to 50.0% with the archive and only to 23.0% without it, measured [R01].

### 11.4 Measuring on one Windows desktop

The Forge shares one 9950X with agent builds and the owner's own work, so
[06-forge](architecture/06-forge.md) specifies an interleaved, blocked A/B design; stationarity checks
(e-processes assume exchangeable samples); composite nulls and a declared minimum detectable effect; a
measurement-throughput budget (how many candidates per day can reach e ≥ 20 at 2–5% effects);
**quiet windows**, CCD pinning, the power plan, Defender and indexing exclusions, and NVMe SLC-cache
and thermal state for storage runs; and the option of a second measurement machine. Performance gates
are **non-inferiority with margin δ = 3%**, anytime-valid, interleaved and load-gated against
`hearth-c-ref` in the same session on a declared quiet-machine profile (DR-018). Absolute figures such
as 69.6 GB/s single-thread L2-resident (one measurement, on a busy machine [R11]) are context only.
Superiority claims need e ≥ 20.

### 11.5 Tombstones and `mithc revisit`

```text
tombstone lookahead_depth_4 {                       // a ledger fact, shown as text
    verdict: slower                                 // decode 13.0 -> 10.0 tok/s (measured)
    scope:   { model: qwen3_30b_a3b, drives: 1 (990 PRO), cache_gib: 2..=4 }
    class:   H                                      // hardware-contingent
    revisit_when: nvme_read_gbps > 12.0 || tier_exists(vram) || drives >= 2
    evidence: ledger:sha256:…
}
```

- **Fields:** a scoped verdict; a failure class (**H** hardware, **T** tooling, **S** search, **E**
  effort, **V** evaluation, **C** composition, **X** scale, **F** fundamental-under-assumption); a
  decidable trigger; an evidence link; an exact reproduction recipe; and the search budget spent
  compared with the incumbent's [R02].
- **The trigger language is decidable:** interval constraints, set membership, hash equality,
  primitive existence and relative-to-burial predicates. Its normative grammar is
  [06 §7.2](architecture/06-forge.md): primitive existence is spelled `has(kind: name)` (with sugar
  such as `tier_exists(vram)`), and `exists` is reserved for bounded `exists(var in fact: pred)`. Subsumption is decidable, so narrower
  tombstones merge into wider ones, and triggers re-evaluate incrementally in the Fact Plane when an
  environment fact changes. **A verdict without a scope is a type error** **[v0, M3]**.
- **Auto-derived triggers:** when a candidate is buried, the cascade already knows the binding bound
  term and the gap attribution (eviction, wrong prefetch, lateness). `mithc` turns these into a default
  trigger, so nobody has to remember to write "revisit if".
- **The revisit loop:** an event (hardware, toolchain, primitive set, evaluator, model catalogue,
  canon version, proposer model) → an incremental trigger scan → priority `[P_win·V + β·novelty] /
  cost`, sampled rather than argmaxed → rebuild from the recipe and re-measure *before* mutating → the
  cascade → a verdict update. A background audit slice samples tombstones whether or not a trigger
  fired [P4 §8.7].
- **Design-level tombstones** (`mithc revisit --design`): every rejected idea in this architecture is
  entered in [DECISIONS.md](DECISIONS.md) with a class and a trigger, so the design process and the
  compiler share one graveyard **[v0, M3; imported in M0]**.
- **An acceptance test from real history.** Hearth's past rejections are imported as tombstones at
  Stage 0: lookahead depth 4, and the ADR-0004 decayed-LFU default (decay 0.995). LRU beat that
  default by 8–13 hit-rate points in trace replay (simulated [R01]); in-engine measurement found LFU
  0.995 worst at every cache size, with a niche-dependent winner: LRU at 1 GiB without prefetch,
  LFU 0.9 at 2–4 GiB or with prefetch (measured [R02]). The imported tombstone is scoped to those
  niches, and its verdict rests on the in-engine measurement, not on hit rate (§11.2). A replay test checks that the lookahead tombstone fires only when the
  simulated environment gains VRAM or a second drive.

### 11.6 Löb-safe stratification and minimum benefit

**S1** no self-judging: an artifact is evaluated only by an evaluator whose build closure excludes
unpromoted artifacts of its own level and its own clade. **S2** frozen judges: no Forge output compiles
F0. **S3** monotone strictness: autonomous changes to checker-like components may only tighten, which
is *tested* by archive replay (new accept set ⊆ old); over a finite archive this is a test, not a
proof. **S4** proposers evolve freely, because they cannot accept anything. **S5** separation of
powers. **S6** the alpha budget and quiet-machine time are resources that only humans replenish
[P4 §8.10]. Each milestone carries a **pre-registered minimum Forge benefit**
([ROADMAP §8](ROADMAP.md), the single authoritative table; summary in §13); if it is not met within
its budget, the Forge line is tombstoned rather than funded further. Before grants exist (M6), a
measured gain such as M2's schedule gain at e ≥ 20 is recorded as a ledger fact, not promoted.

### 11.7 Beyond DGM, AlphaEvolve and HGM

| Axis | DGM / AlphaEvolve / HGM [R01] | Mithril Forge |
|---|---|---|
| Correctness basis | per-candidate benchmark or user-written evaluator | space certificates once, or per-candidate T1/T2; tests never suffice for exact code |
| Hack resistance | monitoring; hacks observed | hack classes are type errors or isolation properties; runtime-owned clock; sealed gates |
| Archive lifetime | one run | a permanent ledger keyed by closure × environment |
| Negative results | unscoped stepping stones, or discarded | scoped tombstones with classes, decidable triggers and recipes |
| Context change | not modelled | `mithc revisit` fires on environment events |
| Statistical control | none stated, or held-out shapes | anytime-valid e-values: a union-bound alpha budget per period and slot family for defaults and F1-A; online FDR (e-LOND, q = 0.20) per grant for opt-in profiles |
| What improves | the agent's scaffold (DGM, HGM); user programs (AlphaEvolve) | by v1: artifacts (live from M4) and the agents' own interface (M6); later the compiler, the language and the meta level (§1.4) |

**Living models** (immutable versioned weights plus typed overlays) are post-v1. The overlay API and
the KDA recurrent-state snapshot API are designed together when Hearth adds Kimi-K3 (DR-025)
**[later]**.

---

## 12. The Hearth port

Detailed in [07-hearth-port](architecture/07-hearth-port.md).

### 12.1 Approach

Hearth is about 9k lines of C11 (9,068 lines, measured line count [R11]) plus a numpy-only Python
toolkit, governed by invariants written for AI agents: bit-identical logits regardless of threads,
cache, prefetch and I/O mode (INV-DET-1); batch equals sequential (INV-DET-2); scalar = AVX2 = AVX-512
through canonical float order (INV-DET-3); agreement with the numpy reference and transformers within
tolerance (INV-NUM-1/2); malformed files never crash (INV-FMT/SAFE); C11 plus OS APIs only (INV-DEP);
every performance claim labelled (INV-HONEST); sealed goldens and mutation testing (INV-VERIFY);
defaults never change output (INV-LOSSLESS-DEFAULT).

The port is a **strangler fig** behind Hearth's internal `hx_*.h` seams: Mithril emits C11 with the
same `hx_*` symbols, so Mithril modules replace C objects one at a time inside `hearth_core`. A frozen
`hearth-c-ref` binary stays as a **permanent differential oracle**. Hearth's golden tests are
relational and tolerance-based, so they cannot detect a silent change of float order; the port
therefore adds a **cross-binary hash corpus** (SHA-256 of logits, routes, quantiser bytes and matmul
outputs across ISA, thread count, row splits and NaN/inf cases, plus 512 real Qwen3 decode steps)
[R11]. Agents port by `mithc lift` (transliteration) plus annotation (`uses`, specs, formats,
schedules).

### 12.2 Stages and gates (DR-020)

| Stage | Scope (C lines, measured count [R11]) | Acceptance gates (all required) |
|---|---|---|
| **S0** Freeze & instrument | tag the base; build `hearth-c-ref`; land ADR-0010 first; land `struct_size` fields in C Hearth (with the R3 commit); generate the hash corpus; record CRT identity; import Hearth's historical rejections as tombstones | corpus reproducible across repeated runs; Owner signs it as golden-tier |
| **S1** Quant kernels | `quant.c`, `quant_avx2.c`, `quant_avx512.c` (1,408) → formats + one meaning + schedules | `test_quant` (117,681 checks); golden ISA/batch identity; quantiser output byte-identical to C; hash corpus equal; **validated** T1/T2 plus object audit for every dispatched variant; throughput non-inferior to `hearth-c-ref` at δ = 3% |
| **S2** Modelfile | `modelfile.c` (922) → `format` descriptions → total parser and writer | `test_modelfile` fuzz cases; golden malformed-file test; identical accept/reject and parsed configs against C on a generated corpus; zero `unsafe`; totality and safety graded `tested`, with `proof` only for T2-discharged bounds (§7.2) |
| **S3** Pool | `pool.c` (732) | `test_pool`; dispatch latency within noise of C (~0.75 µs at 16 threads, measured), including WSL2 and crowded-pool cases |
| **S4** Store logic | `store.c` (1,030) as values + `timing_only` hint ports, calling the **existing C platform functions** | `test_store`; golden scheduling independence; demand-read throughput non-inferior to `hearth-c-ref` at δ = 3%, interleaved, with SMART-temperature and SLC-settle controls ([06 §6.7](architecture/06-forge.md)); 7.16 GB/s (measured) is context only; chaos suite kills 100% of seeded core mutants; no user `unsafe`; ≥ 100 generated policies bit-identical |
| **S5** Forward pass | `model.c` (2,040) | full golden suite; hash corpus; 512-step real-model decode hashes; tok/s non-inferior at δ = 3% on the confirmatory set (cached, 2 GiB, 2,048-token prefill); 4/8 GiB and 512-token prefill screened and escalated per ROADMAP §1 rule 4 |
| **S6a** API | `api.c` + `hearth.h`: export `hearth.h` exactly (19 functions, 3 structs), including the `struct_size` fields landed at S0 | Python toolkit and ctypes mirror tests pass unchanged |
| **S6b** Platform | `platform_win.c` / `platform_posix.c` (1,574) → audited `std_platform`, **last** | `test_platform`; direct-I/O throughput non-inferior to `hearth-c-ref` at δ = 3% (same controls); large-page arenas; timed waits never return early; TSan clean; audited `unsafe` ≤ 1,500 lines across OSes |

The platform is ported last because G05 ranks it the riskiest `unsafe` surface, and the store's logic
gates do not need it ported [P3 §9]. Before each stage starts, a **comprehension precondition**
applies: the harness task family closest to that stage (T-Q4 for S1, T-STORE for S4, …) must clear its
pre-registered VP@1 bar, so the port never outruns agents' ability to maintain what it produces
[P1 §9].

### 12.3 Working alongside a live C codebase

- **Rebase windows.** Upstream C changes after the S0 freeze are absorbed at stage boundaries:
  rebase, regenerate the hash corpus where the change is intended, and re-run the gates.
- **Generated-C review.** Checked-in generated C carries provenance headers and `#line` maps. A
  C-only contributor who patches a generated file trips CI (byte-for-byte regeneration fails); the fix
  path is to change the `.mith` source or to land the C change upstream first.
- **Normativity flips after S6** (§6.4): until then NUMERICS.md and the C scalar code are normative.

### 12.4 What the research found in Hearth (report, do not fix)

These are reported to the maintainers, not fixed by Mithril agents: the mirror check compares only
the first page of up to 16 slabs [G05, RV: D2-A]; `hx_store_heat` returns an unguarded pointer, a C11
data race when several threads call it (on diagnostics data) [G05]; the `read_errors` ABI change wrote
past the ctypes buffer [R11]; MXCSR is never asserted [G02]; the LFU heat decay is 0.9 in code but
0.995 in ADR-0004 and `hx_store.h` [R11]; the server has storage channels (`cached_tokens`, `/stats`,
unauthenticated `/health`) [RV: D3-iii]; and with `n_io=1` a demand read can wait behind a prefetch
[RV: D2-A]. The full table is in [07 §10](architecture/07-hearth-port.md).
Several become impossible by construction in Mithril: second-class references cannot express the
`hx_store_heat` race, `struct_size` plus the contract variance lattice reject the `read_errors` class,
`#[decision(ADR-0004)]` flags the decay drift, and O4 requires full-content slab hashes.

### 12.5 Kimi-K3 and MXFP4

Hearth's open items include real Kimi-K3 (latent MoE plus KDA linear attention) and MXFP4. MXFP4 uses
32-element scale blocks while activation blocks are 64, so canon needs a decision (for example two
sub-block terms added in order) before the first MXFP4 golden; that is an additive `canon.v1.1`
change with no golden reset (§6.4) [P3 §9]. KDA needs chunkwise recurrent scans under a canonical order (§7.6) and a recurrent-state
snapshot API designed with overlays (DR-025).

### 12.6 What Hearth gains even if Mithril stops

- M0's checker spike can certify (or fail to certify) **today's** hand-written C kernels, giving
  INV-DET-3 a per-build certificate instead of tests alone [P2 §9].
- ADR-0010, the MXCSR invariant, `struct_size` fields and the cross-binary hash corpus land in C Hearth
  regardless.
- The defect reports above.
- The historical rejections become scoped tombstones with triggers; the policy Forge on `hearth.sim`
  and the measurement service work on C Hearth's own policies.
- If the standalone surface fails X1 or M1, the checker, ledger and format generator continue as tools
  over C (§13).

---

## 13. Roadmap summary and kill criteria

[ROADMAP.md](ROADMAP.md) is authoritative for milestones, gates, costs and the deferral register; this
is a summary. Milestones end at their gates, not on dates.

| # | Milestone | Main deliverables | Gate (summary) |
|---|---|---|---|
| **M0** | Falsify (five to six weeks, verdict in week 6 [inference]) | **X0** instruction census; **X1** cold-agent writability (paper Mithril + Tier 0/1 vs Mithril without traits, Rust, C11, Rust + Mithril tooling, obfuscated); **X2** checker spike on Hearth's real AVX2/AVX-512 kernels with Zen 5 fuzzing and the `numerics_v1` mutant pool; **X3** one meaning plus schedules vs the hand kernels; **X4** evaluator-integrity kit (measurement service, sandbox, catalogue and blind planted-hack batches, simulator policy Forge, tombstone import and replay); the **core-calculus note**; D0 owner decisions; S0 corpus | each experiment against its pre-registered pass line; the Owner signs the verdict in week 6 |
| **M1** | Front end | `mithc` v0 (parser, formatter, HIR/THIR checker, MIR → C11, `export abi`), `check/hole/edit/outline/search --json`, MCP, Tier 0/1 cards, Mithril MultiPL-E, `mithi` differential tests; scalar S1 | scalar quant port passes `test_quant`; cold-agent kill criterion M1 |
| **M2** | Kernels | KIR, schedules, T1/T2, Zen-5-fuzzed semantics table, object audit, `canon` library, formats; S1 complete | S1 gates; all `numerics_v1` FP mutants rejected |
| **M3** | Formats, ABI, ledger | format-generated parser and writer (S2); contract variance lattice; ledger with tombstones and `revisit` | S2 gates; a replay of the `read_errors` ABI break is rejected at compile time |
| **M4** | Concurrency and store | `std_platform`, `deterministic`, `timing_only` + hint ports, permutation scheduler; binary T0 confinement; S3 + S4; store certificate O1–O5; live F1 policy Forge on the engine (F1-live) | S3/S4 gates; ≥ 100 policies bit-identical; 0 planted hacks accepted |
| **M5** | Full port | S5, S6a, S6b: Mithril-Hearth exports `hearth.h`; Python toolkit unchanged | S5/S6 gates; benefit claim B1 (assurance) complete |
| **M6** | Measured benefit | Forge campaigns (policies and kernel schedules); F1-A agent-interface level; benefit claim B2 maintainability A/B; benefit report under INV-HONEST | benefit claims B2 and B3 (below) |
| **M7** | Edition 1 + growth | Syntax freeze; normative manual ≤ 30k words plus a machine-readable core; Mithril MultiPL-E published. Triggered items (ROADMAP §9): GPU tier if D0-6 says yes, Lean for the T1 rules, `@bind(load)`, NEON. Self-hosting decision (DR-026) | DR-017's M1 thresholds hold on a **rotated** held-out suite; a fresh agent with Tier 0+1 and the project card implements an open Hearth item to the evidence policy at TPV (tokens per verified pass) ≤ 1.2x Rust; GPU per DR-022 (below). Kill: the rotated suite fails → features freeze, the Surface Lab re-runs, no Edition 1 |

Beyond M7, in the deferral register rather than in any milestone: F2 compiler heuristics and rules
(D-15), the direct x86 emitter B3 (D-05), full LSP (D-10), further F3 editions and Fm (D-14).

**Pre-registered kill criteria** (each written before data collection). Every gate is pass, amber or
kill, and a fired kill selects one of ROADMAP §4's outcome classes: **STOP-L** (the language stops,
the tools are kept), **NARROW** (work continues with one named claim removed), **HALT-F** (the Forge
is frozen until repaired) or **STOP-ALL** (the repository is archived with its tombstones, and its
tools go to C Hearth).

- **Cold start (DR-017),** against Rust, the strongest prior and the real fallback, disjunctive. At
  X1 (paper Mithril with Tier 0/1): a VP@1 gap > 15 points **or** CABW worse than Rust's by > 5
  points → STOP-L: stop the standalone surface and ship Mithril as a checker, ledger and tooling
  layer over Rust and C. At M1 (full diagnostics): a gap > 10 points **or** CABW > Rust's. ≥ 60
  held-out items, task-clustered mixed-effects analysis, ≥ 2 model families, power published. The
  surface contrast against "Rust + Mithril tooling" is decided by the rule proposed in §3.
- **Evaluator integrity (X4):** any accepted planted hack, from either the catalogue or the blind
  batch → HALT-F: no Forge result counts until the evaluator is redesigned and the suite passes
  again; the language continues. A failed A/A calibration bars every superiority gate, and a failed planted-regression calibration bars
  every parity gate, until the cause is fixed and the calibration passes again on fresh sessions.
- **Census (X0):** hot-kernel loops outside the lockstep rule plus correspondence maps → NARROW: the
  object audit is deferred and the C compiler stays trusted for kernels.
- **Checker (X2):** if T1 cannot accept the real kernels without per-kernel `assumed` axioms, the
  "validated bit-identity" benefit dies; the project continues only if X1 and X3 pass [P5 §10.1].
- **Generator (X3):** below parity after the tuning budget, or bit-identity needs non-DAG-preserving
  primitives → kernels become explicit-SIMD `.mith` checked by T1.
- **Project level:** X2 and X3 both fail → stop (no kernel benefit). The Owner rejects a
  Mithril-sourced core → re-scope to tools over C, recorded as a tombstone.
- **Soundness hard stops:** any type-checked `timing_only` policy that changes logits halts the
  policy feature and the Forge until the core theorem is repaired; any T1 false accept halts T1 for an
  audit.
- **Memory model (ROADMAP M4):** user `unsafe` in > 2 places (amber at 1–2: an audited primitive by
  ADR), or dispatch > C + 10% that cannot be closed → reopen the memory model. Audited `unsafe`
  ≤ 1,500 lines across OSes is the M4 gate, not the kill.
- **Performance (DR-018):** non-inferiority at δ = 3% against interleaved `hearth-c-ref`; a regression
  that cannot be closed in the stage's time box keeps that module in C behind its seam.
- **Forge:** no candidate beats the incumbent beyond noise within the pre-registered campaign budget
  → the Forge line is deprioritised and tombstoned.
- **GPU (DR-022, ROADMAP M7):** ship gate: canonical expert GEMV ≥ 0.6x llama.cpp's MMVQ kernel on
  the same card [target], **and** end-to-end ≥ 2x CPU-only (measured), **and** logits hash-identical
  across placements. Amber at 0.5–0.6x: one relayout campaign (scales split from the 34-byte
  blocks), then re-judge. Kill: GEMV < 0.5x, or identity cannot be repaired. The outcomes are split,
  because rule C2 ([02 §14](architecture/02-compute.md)) forbids `device(t)` values in placements
  decided at run time, and a Qwen3 expert tier is necessarily cache-driven (about 15.4 GB of Q4
  experts exceed about 10.5 GiB of usable VRAM):
  - *speed miss with identity intact* (GEMV < 0.5x, or end-to-end < 2x): the tier stays an opt-in
    `cross_device` profile, never a default, with a class H tombstone and a hardware trigger;
  - *identity failure*: only a statically placed, load-time-fixed GPU plan may run, as a `device(t)`
    opt-in lane with per-plan goldens; no cache-driven expert placement.

**Pre-registered benefit claims** [P5 §9.1] (not to be confused with backends B1–B4 of §9.2):
**benefit claim B1, assurance** — every dispatched kernel variant holds `validated` bit-identity
evidence; the generated parser has no `unsafe`, and its totality and safety (INV-FMT/SAFE) are
graded `tested` (fuzzing, the `mithi` differential and the golden malformed-file test), with
`proof` only for the bounds obligations T2 discharges, because an untrusted `mithc`, a front end
graded `tested` and a C compiler trusted for control-heavy code allow no stronger claim
([ROADMAP §7](ROADMAP.md)); at least five live defects are closed by a compile-time rule or
certified check; on `numerics_v1`, T1+T2 kill at least as many mutants as
goldens plus contributor tests, and at least one class the goldens miss (if not, the honest report
is "stronger evidence per build", not "more bugs caught"). **Benefit claim B2, agent
productivity** — Mithril-Hearth VP@1 ≥ C-Hearth's − 3 points at ≤ 1.2x cost per solved task.
**Benefit claim B3, performance** — parity everywhere plus at least one measured, promoted,
output-preserving gain (≥ 5% tok/s or ≥ 10% fewer NVMe bytes/token on a named configuration,
e ≥ 20), under two conditions that keep it a claim about the language rather than about engine
tuning: **found, not ported** (the Forge found it by search inside a certified space; a hand port
of an existing C prototype, such as the 94 GMAC/s value pass, does not count) and **against
today's C** (measured against C Hearth `main` at the time of the claim, including any C version of
the same algorithm, not only against the frozen S0 tag) ([ROADMAP §7](ROADMAP.md)).

**Cost** [inference, low-medium confidence; ROADMAP §10, which takes P5's base estimate [P5 §10.2]
and adds deltas for the grafted scope]: about $92–225k of API spend and ~910 owner hours over
~10.5 months for M0–M6. M0 alone costs $16–36k and ~195 owner hours, peaking at about 33 h/week.
M6 costs $16–40k instead of $20–55k if B2's margin widens to 5 points (D0-10). Owner review time
is the binding constraint, concentrated in the trusted core and the ADRs.

### 13.1 What happens next (week 0)

1. The Owner approves the M0 budget, cadence, harness model families and quiet windows (D0-10),
   and the rule that every gate's pre-registration is signed before collection (D0-12).
2. The Owner takes D0-1 (INV-DEP / ADR-0001) and D0-2 (ADR-0010) early, because S0 and the M0
   verdict depend on them, and settles key management (D0-9) and Forge authority (D0-7) before X4
   needs them (§17).
3. In parallel ([ROADMAP §2](ROADMAP.md)): the X0 census, X1 suite and card authoring, X2 semantics
   table and fuzzing, X4 measurement service and sandbox, and the core-calculus note start in
   week 0; X3's generator starts in week 1.
4. In week 6 the Gatekeeper applies the pre-registered rules, picks an outcome row of ROADMAP §4,
   and the Owner signs the M0 verdict.

---

## 14. Refined seed ideas

The owner supplied an earlier AI discussion as the seed. R10 checked its 59 concrete claims: 24 true
or mostly true, 17 misleading, 6 false, 5 likely fabricated and 7 unverifiable [R10]. **The instincts
were good; the numbers were not.** [SEED-REFINEMENT.md](SEED-REFINEMENT.md) refines each section; the
summary:

| Seed section | Verdict | What survives, and where it lives |
|---|---|---|
| A Layers below C | context, kept | Mithril targets strict C11 plus audited object code, and owns an x86 semantics table (§8.2); microcode and HDL are out of scope |
| B An x86-native language that beats C | **transformed** | Hardware as data, schedules, translation validation of real compiler output (N2), `restrict` from alias facts (DR-027). Rejected: µop-port byte superoptimisation as the main path, IPC as reward, P/E-core dual paths (the 9950X has 16 identical cores [R10]), "guaranteed" vectorisation; direct ELF emission only by trigger (DR-009) |
| C Objective reality check | **kept, strengthened** | The roofline becomes a typed cost layer (N7). Low-bit types become `format` element codes with derived integer dots, not popcount primitives (fast low-bit kernels use lookup tables or int8 dots [R10]); VGATHER rejected as the sparsity primitive (a zmm gather is 64 µops on Zen 5 [R10]); async pipelines become tiers and hint ports |
| D Claimed gains | **rejected** | The speed-up table has no sources and several rows break the memory roofline; e.g. 12–22 tok/s out-of-core for Kimi-class is impossible on this machine (all-in-DRAM cap ≈ 3.4 tok/s for Kimi-K2-class [R08]; Kimi-K3 is far lower, §7.7). Replaced by honest ceilings (§7.7) |
| E Visual generation | **rejected for v1** | No primitives (DR-024); general features only (layout/tile algebra, block sparsity, reserved approx/cache effect). The cited video speed-ups are real but reuse work across denoising steps, not frames [R10] |
| F openai/math | **partly true** | The repository exists with a Lean 4 library and the Comparator checker; the family-level claims are false [R10]. Lean enters only for TCB pieces through a Comparator-style gate (DR-010); "Lean replacing SMT" is a design-level tombstone |
| G Projects to study | kept as prior art | Alive2, STOKE, Souper, Triton, TileLang inform §8 and [R05, R07]; SPDK bypass is rejected as a default |
| H Go-to-market | **mixed** | Kept: machine-actionable JSON diagnostics (§10.4), drop-in C ABI (`export abi`, `hearth.h`), open proofs. Rejected: seeding synthetic repositories and relying on llms.txt as the cold-start strategy |
| I "Living tissue" AI | **guarantees rejected; idea transformed** | SMT "bounded loss divergence", null-space "forgetting-free" types, INVD-based self-modifying code and "single-cycle" CMPXCHG16B are false or impractical [R10]. What survives: immutable content-addressed weights with typed overlays and token-boundary epochs, post-v1 (DR-025) |

---

## 15. Non-goals

For v1, explicitly:

- Novel syntax, glyphs, a Python near-clone, or a Python-embedded primary surface (a Python schedule
  and search API is acceptable).
- Projectional editors or JSON-wrapped code as agent input or output.
- `async`, user macros, trait objects (`dyn`), specialisation, garbage collection, exceptions,
  multi-shot continuations, inheritance, general dependent types.
- A full Dafny-class auto-active verifier (DR-012); Lean as the authoring layer.
- A verified compiler (translation validation instead); formal speed proofs on out-of-order cores.
- µop-port byte-level superoptimisation as the main optimisation path; VLIW-style bundling; bypassing
  LLVM as a goal; P/E-core dual paths.
- Runtime self-modifying code, INVD tricks or CAS hot-patching; compiling weights into instructions;
  online supercompilation.
- SPDK or kernel bypass as a default.
- Visual-generation primitives (DR-024); a general GPU backend; training beyond (post-v1) overlays.
- Lossy defaults of any kind; timing-based approximation in default builds; sound static error bounds
  for 4-bit networks.
- Hit rate, IPC or raw pass@1-per-token as objectives; test-only acceptance of exact code.
- Implicit spec-to-code regeneration; hard file locks for agent swarms.
- Seeding synthetic repositories.
- Self-hosting before the port is complete (DR-026).
- Claiming to beat llama.cpp as a *language* result: speed is credited to placement and bytes.
- The Forge promoting defaults, editing specs or goldens, or building its own evaluator.

Each rejected idea is a design-level tombstone with a trigger in [DECISIONS.md](DECISIONS.md).

---

## 16. Top risks

| # | Risk | Why it is real | Mitigation |
|---|---|---|---|
| 1 | Cold start: agents write `.mith` badly | training-data gravity; new languages cost a steep multiple [G01] | subset rule; Tier 0 always on; lifter; "Rust + Mithril tooling" arm from day one (M0 kit at X1, full tooling from M1; §10.6); DR-017 kill with a designed fallback |
| 2 | Scope creep (second-system effect) with one maintainer | five proposals' worth of ideas | P5 backbone; deferral register with triggers; each milestone checks that no unregistered feature landed |
| 3 | T1 incompleteness on compiler output (horizontal reductions, shuffles, spills, loop rotation) | KLEE-FP's precedent was straight-line code [R07]; the instruction census is not done [G02] | X0 census first; correspondence maps; "unknown = reject"; unmatched variants not dispatched |
| 4 | An unsound trusted-core rule or table entry | 15 eBPF verifier logic bugs found in a month [RV: D2-A]; a Lean kernel soundness bug in July 2026 [R07] | proved rules; Zen 5 fuzzing + Bochs; planted corpus; core mutants; second checker for promotion-grade claims; quarantine and revocation |
| 5 | Measurement noise on a Windows desktop | thermal, background load, shared machine | interleaving, stationarity checks, quiet windows, e-values that refuse to certify, alpha budget; optional second box |
| 6 | Owner bandwidth | owner review is the binding constraint [P5 §10.2] | TCB kept small and budgeted; review queue ordered by evidence grade |
| 7 | Windows performance parity (MSVC codegen, pool heuristics) | Hearth is hand-tuned intrinsics C | emit intrinsics that mirror Hearth's; port heuristics verbatim; `restrict`; non-inferiority gates |
| 8 | Weak or gamed specs; correlated failures across roles | LLM specs sound and complete about half the time [R03] | escrow; two-sided strength; distinct model families; independent oracles |
| 9 | Evaluator hacking | documented in DGM, CUDA-L1, RE-Bench [R01] | certified spaces only; runtime-owned clock; isolation; validated plausibility bounds; named counters |
| 10 | Goodhart on the harness; model drift | sealed suites leak under tuning | rotation; permanent holdout; obfuscated arm; decay re-runs per model generation |
| 11 | libm identity breaks the parity oracle | platform libm is not a fixed function across machines (UCRT's FMA3 dispatch [G04]), and a transcendental spec change after the hash corpus exists forces a re-baseline | ADR-0010 before the corpus |
| 12 | Constitutional rejection by Hearth | INV-DEP, ADR-0001 | checked-in generated C; value delivered to C Hearth regardless (§12.6) |
| 13 | Forge payoff smaller than hoped | eviction gains are a few points at most [RV: D2-A]; ~1.3–1.5x is the whole honest CPU headroom | pre-registered minimum benefit; Forge staged; the GPU tier is the larger lever (simulated, uncalibrated; §7.7) |
| 14 | Liveness bugs in safe concurrent code | blocking bugs live in safe code [G05] | permutation scheduler; TSan; chaos suite |

---

## 17. Owner decisions

None of these can be made by an agent. IDs, wording and the "Needed by" column follow
[ROADMAP §11](ROADMAP.md), which is authoritative; "Needed by" is the latest point before work
blocks. Rows are sorted by deadline. Unnumbered rows are Hearth-maintainer decisions with no D0 entry
([07 §9.3](architecture/07-hearth-port.md)).

| ID | Decision | Recommendation | Needed by | If declined |
|---|---|---|---|---|
| D0-10 | Budget, cadence, harness model families, quiet windows | Approve the M0 budget, including the measurement budget and quiet hours of ROADMAP §10; ≥ 2 frontier families + 1 local (a one-family pilot at X1, full from M1); B2's margin (3 or 5 points) before B2's pre-registration | Week 0 (B2 margin: before M6) | No M0 |
| D0-12 | Pre-registration sign-off for every gate | The Owner signs each record before collection | Per gate (the first M0 records in week 0) | The gate cannot be evaluated |
| D0-9 | Owner key management ([03](architecture/03-trust.md)) | Offline or hardware-backed key with a written recovery path | X4 | No AUTHORITY facts, so no promotion |
| D0-7 | Forge authority: grant signer; `timing_only` defaults by ADR only (DR-015); unattended runs | Owner signs grants; defaults by ADR; unattended only inside quiet windows | X4 | Attended runs only |
| D0-2 | ADR-0010 specified transcendentals (`cr` or `canon_v1` per function) | Adopt before the S0 corpus (DR-014): `cr` sinf/cosf, `cr` or `canon_v1` expf per function; goldens are relational, so they need no re-lock [G04] | S0 | libm drift risk; `parity::` shim fallback |
| D0-1 | INV-DEP / ADR-0001: may Mithril be the core's source? | Option A: checked-in C11, regenerated byte for byte by a pinned mithc in CI (DR-026); CMake builds without `mithc`. It needs a superseding ADR for ADR-0001. Landed alone (1 of 8 Accepted ADRs, 12.5%) it stays under Hearth's 15% churn breaker, so the Owner must enforce its constitutional status; bundling it with the ADR-0004 heat-decay supersession would trip the breaker, so land them separately (07 §9.1) | End of M0 | STOP-L. Tombstone, trigger "owner ADR changes" |
| D0-3 | S0 freeze, `hearth-c-ref`, hash corpus as maintainer golden tier (INV-VERIFY extension) | Yes, reproduced twice on the 9950X | M1's S1 | No bit-exact oracle, so no port |
| D0-11 | Spec authority: sealing; different model families for Author and Builder; `validated` as an INV-VERIFY evidence class | Yes to all three | M1 | Maintainers write all specs |
| — | Task-DAG ownership by definition path once `.mith` is the source | Adopt for ported modules | S1 | — |
| D0-8 | Measurement host | The desktop first; a second box by D-22 | M4 | Campaigns bounded by measured throughput |
| D0-5 | Heat-decay value (0.9 vs 0.995), `struct_size` fields, MXCSR invariant, mirror hashing or qualified INV-DET-1 | Decide now; land each before the stage that needs it: `struct_size` with the R3 commit, so S6a can export `hearth.h` exactly (07 §9.3); MXCSR set and restored at every `export abi` and `hx_*` entry, and set and asserted at pool-worker start (§6.3); the decay as a superseding ADR for ADR-0004, separately from D0-1 | S4 / S6a | B1 defect items shrink |
| D0-6 | RTX 5070 in scope? `nvcuda.dll` as an OS API? Display on the iGPU (~1.5 GB of VRAM freed [G03])? | Decide by M5; the VRAM tier is reserved either way. INV-DET-1 gains a device-placement axis only once a GPU tier exists | M5 | CPU-only; the GPU becomes a tombstone |
| D0-4 | Normativity | NUMERICS.md and C stay normative through S6, then meanings are normative and NUMERICS.md is generated and checked | S6 | Dual normativity with a drift check |
| — | `canon.v1.1` MXFP4 block order (additive; no golden reset) | Decide before the first MXFP4 golden | later | — |
| — | `canon.v2` fixed-chunk attention order (major; the first use of the migration protocol, 03 §12) | Decide before any GPU attention; an Owner ADR plus a Hearth maintainer ADR record the golden reset | by-trigger | Attention stays on the CPU |
| — | Self-hosting | Decide after M7 (DR-026) | after M7 | — |

---

## 18. Glossary

Terms already defined where they first appear are listed with a pointer.

| Term | Meaning |
|---|---|
| **`abandon`** | Agent verb: "this task cannot be satisfied as specified" (§8.6) |
| **ADR** | Architecture decision record in Hearth's governance, such as ADR-0001 (INV-DEP), ADR-0004 (LFU default) or ADR-0010 (specified transcendentals) (§12, §17) |
| **alpha budget (α budget)** | Allowance for false promotions; the guarantee has two tiers. *Defaults and F1-A promotions:* a union-bound budget per period and slot family; each confirmatory test is charged α_i = 1/e_threshold when it opens, whatever its outcome (0.05 at e ≥ 20); E[false promotions] ≤ Σα_i, and P(any) ≤ Σα_i when Σα_i < 1. *Grant-promoted opt-in profiles:* online FDR ≤ q (q = 0.20) per grant through an e-LOND stream, α_t = min(0.05, q · γ_t · (D + 1)). The Owner sizes budgets, q and γ, and only humans replenish them (§8.5) |
| **anchor** | Definition path plus content hash that addresses an edit; never a line number (§10.3) |
| **AUTHORITY / FREE / SEAL** | Ledger operation classes: normative (needs a signature) / monotone / non-monotone but mechanical (§8.3) |
| **B1 / B1.5 / B2 / B3 / B4 (backends)** | Strict C11 / object audit / PTX expert tier / direct x86 emitter / copy-and-patch JIT (§9.2) |
| **benefit claims B1 / B2 / B3** | Pre-registered port benefits: assurance / agent productivity / performance; distinct from the backends (§13) |
| **C / Dc / D** | Surface classes: coincident with Rust / Rust form rejected by name / new keyword-led concept (§5.1) |
| **CABW** | Checker-accepted-but-wrong rate: accepted by the checker, wrong by the hidden oracle (§10.6) |
| **CALM** | Consistency As Logical Monotonicity: add-only (monotone) operations need no coordination, which is why FREE ledger operations merge freely [RV: D2-F] (§8.3) |
| **`canon.v1`** | Hearth's NUMERICS.md made normative (§6.1); `canon_v1::` names its specified functions |
| **certified space** | A class of modifications proved once to preserve outputs (or checked per candidate where no one-time certificate exists); membership is checked per build. **Soundness** (trusted) vs **completeness-for-members** (untrusted, tested) (§8.4) |
| **code floor** | The meet of the grades of the trusted code components in a claim's trust base (checkers, the T0 pass, elaboration into KIR); printed beside the effective grade and compared with a slot's `code_floor`, never met into the effective grade (§8.1, §8.5) |
| **cost signature** | Bytes per tier, ops per class, syncs; symbolic at build, numeric at load, measured at run (§7.5) |
| **cross-binary hash corpus** | SHA-256 hashes of C Hearth's logits, routes and quantiser bytes; the bit-exact oracle for the port (§12.1) |
| **D0-n** | Owner decisions D0-1 … D0-12, IDs as in ROADMAP §11 (§17) |
| **D-nn** | Deferral-register entries with triggers, in ROADMAP §9 (§13) |
| **`deterministic(by: E)`** | Block that removes `nondet`, never authority, on the strength of cited evidence E (§5.4) |
| **DGM / HGM / Gödel machine** | Darwin Gödel Machine (a self-improving coding agent with an archive, validated empirically) / Huxley–Gödel Machine (its successor, selecting by descendants' performance) / Schmidhuber's proof-gated self-rewriter (§1.3) |
| **DR-xxx** | A decision record in [DECISIONS.md](DECISIONS.md) |
| **e-value / e-process** | A non-negative statistic with expectation ≤ 1 under the null / a sequence of them valid at every stopping time, so a test may stop once e ≥ 1/α ("anytime-valid") (§8.5, §11.4) |
| **F0 / F1 / F1-A / F2 / F3 / Fm** | Forge levels: trusted core / artifacts / agent interface / compiler / language / meta (§11.1) |
| **Fact Plane** | Decidable Datalog relations every compiler phase emits; used for capability audits, API search, evidence policies and tombstone triggers (§9.1) |
| **fail domain** | Where a trap stops: an `export abi` entry (error code), a hint-port call (fallback decision), a test case (recorded failure) (§5.4) |
| **false friend** | Familiar syntax with a changed meaning; the costliest surface error for LLMs (§3) |
| **`format`** | Declarative block-scaled layout from which pack/unpack, dequantisation and integer dots are derived (§7.2) |
| **golden / golden suite** | Hearth's sealed, maintainer-owned regression tests; relational and tolerance-based, so blind to a silent float-order change (§12.1) |
| **grant** | Standing, scoped, expiring, revocable AUTHORITY fact allowing auto-promotion into opt-in profiles (§8.5) |
| **hearth-c-ref** | Frozen C build of Hearth kept as a permanent differential oracle (§12.1) |
| **hint port / `Hint<T>`** | The only output channel of a `timing_only` policy / the hint value the store core validates before use (§7.3) |
| **INV-\*** | Hearth's invariants, such as INV-DET-1/2/3, INV-NUM-1/2, INV-DEP, INV-HONEST, INV-LOSSLESS-DEFAULT (§12.1) |
| **IR names** | Syntax (lossless CST) → HIR (names, holes) → THIR (types, effects, grades) → MIR = MCore (normative core) → KIR (kernel op-DAG); backends C11, LIR (lifted x86), PIR (PTX) (§9.1) |
| **IRT** | Item response theory, used to select informative harness items for screening (§10.6) |
| **KDA** | Kimi Delta Attention, Kimi-K3's linear-attention layers with a recurrent state (§7.6, §12.5) |
| **ledger** | Content-addressed store of all claims and evidence, tombstones included (§8.3) |
| **Löb-safe** | Stratification rules S1–S6 that stop any level from judging itself or its own judges (§11.6) |
| **M0–M7** | Milestones: falsification sprint, then front end, kernels, formats/ABI/ledger, concurrency and store, full port, measured benefit, Edition 1 (§13) |
| **MDE** | Minimum detectable effect, pre-registered per slot; it sizes tests and prune rules (§11.4) |
| **meaning / realisation** | The exact executable definition of a computation / a schedule, layout, policy or placement that implements it (§1.1) |
| **mithc / mithi / mithcheck** | The compiler (untrusted) / the independent reference interpreter and differential oracle / the trusted T1/T2 checker (§8.9, §9) |
| **MMVQ** | llama.cpp's quantised matrix-vector CUDA kernel, the GPU speed baseline (§13) |
| **MVS** | Mutable value semantics: values first, `&mut` exclusive for a call, references second-class (§5.2) |
| **MXFP4** | OCP microscaling FP4: 32 E2M1 elements sharing one E8M0 power-of-two scale (§7.2, §12.5) |
| **numerics_v1** | The sealed numerics fault model (mutant pool) that measures spec strength and checker power (§8.6) |
| **O1–O5** | Store-core obligations: hint validation, slab race freedom, arrival-order confluence, lossless tiers, liveness (§7.3) |
| **object audit** | XED decode of compiled kernel objects, lifted to LIR and checked by T1 (§9.2) |
| **Owner / Author / Builder / Prover / Adversary / Gatekeeper** | Roles: human key holder / specs and meanings / implementations / proofs / attacks / runs the deterministic gate (§8.6) |
| **phys / emp / est** | Bound tiers: datasheet peak / audited measurement / model estimate (§7.5) |
| **projection** | Hylo-style subscript (`w.row(r)`) yielding a borrow scoped to the caller's expression (§5.2) |
| **PruneCert** | Content-addressed certificate for a replay-bound prune of a `timing_blind` candidate (§11.2) |
| **QD** | Quality-diversity: an archive that keeps elites per niche rather than one best (§11.3) |
| **S0–S6b** | Hearth port stages, from freeze and instrument to the platform layer (§12.2) |
| **semantics table** | Hand-written, XED-keyed, Zen-5-fuzzed x86 instruction semantics in F0 (§8.2) |
| **spec escrow / spec strength** | Specs owned by the Author role and hash-locked / their two-sided quality measure (§8.6) |
| **STOP-L / NARROW / HALT-F / STOP-ALL** | Kill outcome classes: language stops, tools kept / one claim removed / Forge frozen / project archived (§13) |
| **subset rule** | Rust syntax means Rust; unsupported Rust is rejected by name; new concepts get new keywords (§5.1) |
| **Surface Lab / harness** | Per-construct spelling experiments / the cold-agent comprehension measurement system (§10.6) |
| **T0 / T1 / T2 / T3** | Verification tiers: types and confinement / FP-DAG matching / bit-vector SMT / tolerance (reserved) (§8.2) |
| **Tier 0 / 1 / 2** | Reference cards: always in context / on demand / retrieved (§10.5) |
| **`timing_blind`** | A store configuration whose byte-moving decisions read only the logical event stream, never completion order or queue state; only these admit replay pruning (§11.2) |
| **`timing_only`** | Policy discipline whose only outputs are hints; cannot affect values (§7.3) |
| **tombstone / trigger** | Scoped negative result / the decidable predicate that re-opens it (§11.5) |
| **TPV** | Tokens per verified pass (§10.6, §13) |
| **trust base** | The declared assumptions relative to which every grade holds (§8.1) |
| **typed hole** | `todo!("name")`; type-checked and queryable with `mithc hole` (§5.1) |
| **VNNI** | x86 vector neural-network instructions; `vpdpbusd` accumulates u8 × i8 dot products into int32 (§6.1) |
| **VP@1** | Verified pass@1: the first attempt passes the hidden oracle (§10.6) |
| **X0–X4** | M0 experiments: instruction census / agent writability / checker spike / one meaning plus schedules / evaluator integrity (§13) |

---

## 19. Sources

### 19.1 Research dossiers ([research/](research/))

| ID | Title | Informs |
|---|---|---|
| [R01](research/R01-self-improving-systems.md) | Darwin Gödel Machine and self-improving systems | Forge, archive, evaluator hacks, promotion |
| [R02](research/R02-open-endedness-revisiting.md) | Open-endedness and revisiting dismissed ideas | tombstones, failure classes, revisit loop, QD niches |
| [R03](research/R03-llm-language-ergonomics.md) | What makes a language easy or hard for LLMs | surface, holes, diagnostics, edit protocol, vericoding rates |
| [R04](research/R04-ai-first-languages-landscape.md) | AI-first languages and agent-native tooling landscape | protocol surfaces, GEPA, prior AI-first languages |
| [R05](research/R05-kernel-dsls-and-schedules.md) | Kernel DSLs, schedule languages and tensor compilers | Exo/Halide schedules, IEEE-exact mode |
| [R06](research/R06-local-inference-moe-landscape.md) | Local inference and MoE offloading landscape | formats (MXFP4), placement, honest perf |
| [R07](research/R07-verification-superoptimization.md) | Verification, superoptimisation and rewriting | T1/T2, KLEE-FP, translation validation, range bounds |
| [R08](research/R08-hardware-reality.md) | Hardware reality check and roofline ceilings | machine profile, ceilings, ridge point |
| [R09](research/R09-language-building-blocks.md) | Language semantics building blocks and compiler construction | effects as capabilities, MVS, staging, salsa |
| [R10](research/R10-seed-fact-check.md) | Fact-check of the seed discussion | §14, SEED-REFINEMENT |
| [R11](research/R11-hearth-port-requirements.md) | Hearth deep read and Mithril port requirements | port stages, hash corpus, defects, line counts |
| [R12](research/R12-living-models.md) | Continual learning, model editing and living models | overlays (post-v1) |
| [R13](research/R13-visual-generation-local.md) | Local visual generation: reality and scope | DR-024 scope boundary |
| [G01](research/G01-new-language-cold-start-evidence.md) | Can frontier agents write a brand-new language from in-context docs? | standalone Rust-shaped surface, cards, false friends |
| [G02](research/G02-x86-avx512-formal-semantics-sources.md) | Machine-readable AVX-512 semantics for the bit-exact checker | owned semantics table, XED keys, census gap |
| [G03](research/G03-gpu-tier-and-cross-device-determinism.md) | Is there a GPU in scope, and can canonical-order bit-exactness survive on it? | GPU tier, cross-device determinism, N8 |
| [G04](research/G04-transcendental-libm-numeric-spec.md) | Transcendentals in the numeric spec | `cr` / `canon_v1`, ADR-0010 |
| [G05](research/G05-shared-mutable-state-memory-model.md) | Can a Hylo-style memory model express Hearth's concurrent store? | memory model, `std_platform`, deterministic boundaries |
| [RV](research/revisited-ideas.md) | Revisited ideas: a Darwin-Gödel archive of dismissed computing ideas | S1–S16 seeds; D2-A timing-only effect; D2-B stall-and-bytes prefetching; D2-C one flow, many handlers; D2-D comprehension fitness; D2-E spec hardening; D2-F CALM swarm ledger; D3-i divergence-marking surface; D3-ii sound pruning; D3-iii tenant labels |

### 19.2 Design proposals ([design/proposals/](design/proposals/))

| ID | Proposal | Role in the final architecture |
|---|---|---|
| [P1](design/proposals/P1-agents-language.md) | Mithril as the agent's language | agent protocol and harness |
| [P2](design/proposals/P2-tractable-godel.md) | Mithril as a Tractable Gödel Machine | trust constitution |
| [P3](design/proposals/P3-physics-first.md) | Physics-first: exact meanings, measured bytes | physics and cost layer, projections, formats |
| [P4](design/proposals/P4-living-forge.md) | The Living Forge | tombstones, revisit, ledger transport, staged Forge |
| [P5](design/proposals/P5-minimum-viable.md) | Minimum Viable Mithril | delivery backbone |

The panel's scores, grafts and conflict resolutions are recorded as decision records in
[DECISIONS.md](DECISIONS.md).
