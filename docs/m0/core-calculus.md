# Core-calculus note: MCore v0.1

Status: DRAFT (becomes FROZEN at the commit that first adds it with this line changed to FROZEN;
the X1-subset rules of §12 freeze no later than the `mithi` checker precondition, ROADMAP §3.2)
ROADMAP anchor: [§3.6](../ROADMAP.md#36-core-calculus-note-weeks-05) (deliverable, gate, amber,
narrowing), [§3.2](../ROADMAP.md#32-x1-cold-agent-writability-with-all-arms-weeks-05) (checker
precondition), §4 (no kill row for this note)
Track: CC. Owner authorisation: drafting needs none (PLAN §3.6, "Now: all drafting"). Freezing the
X1 subset and signing need D0-12; the different-family Prover and Adversary need D0-10.

**Appendices.** [core-calculus/derivations.md](core-calculus/derivations.md) holds the hand
derivation of every canonical and derived snippet. [core-calculus/verdicts.json](core-calculus/verdicts.json)
holds the expected verdict for each snippet in machine-readable form, keyed by the SHA-256 of the
snippet text, so that `mithi`'s agreement (ROADMAP §3.2) can be checked by a script.

## Summary

MCore is the small, explicitly typed calculus that every Mithril surface form elaborates into, and
that `mithi` interprets. [01-language §13](../architecture/01-language.md#13-core-calculus-sketch-mcore)
sketched it. This note makes it complete enough to derive every canonical snippet by hand, states
the four theorems with proof plans, and checks the ROADMAP §3.6 narrowing question. It does not edit
01; changes it would make there are proposals (§14).

What the note contains:

- the syntax of MCore, its runtime syntax, and the elaboration of every surface form that a canonical
  snippet uses (§2, §3);
- 18 judgement forms and the typing rules: capability rows `uses { … }`, grades for fidelity and
  determinism scope, the NaN-canonicality bit, second-class references and loans, Hylo-style
  projections, the non-escaping kind `Local`, linear resources, static-dispatch traits, kernels,
  `timing_only` policies, `par`, `det[E]`, formats, schedules and specs (§4, §5);
- a small-step semantics with deterministic traps: a trap ends its fail domain, runs no user code on
  the way, never aborts the host (modulo stack exhaustion, finding F-8), the lowest index wins in
  `par`, a policy trap falls back to the port's declared fallback, and `det[E]` is an administrative
  frame with no dynamic effect (§6);
- theorem statements for type safety, capability confinement, `timing_only` noninterference and
  determinism with scopes, each with a proof plan and its hardest case (§7);
- the narrowing check (§8). **Noninterference can be stated together with the trap fallback**, as an
  instance of a theorem over arbitrary port oracles, provided premises that the O1–O6 list does not
  name today are added: the fallback is total and trap-free (F-tot), whether and where the core traps
  does not depend on the oracle (P-ind, which replaced the stronger P-tot after review), every port
  call runs within a reserved stack budget (S-tot), and whether the core exhausts an arena does not
  depend on the oracle (A-ind). On that reading the narrowing does not fire [G, pending the
  different-family review];
- a hand derivation of every canonical snippet: 8 canonical blocks, 45 `mith` blocks in all, 35
  distinct by hash [M, CC track script, 2026-10-16, Mithril commit `ec46300`] (§9 and the
  appendices);
- a trace of 57 Tier 0 rule atoms to the note's rules [M: counted in §10];
- 11 idioms that X1 reference solutions may need and that do not type, as Dc candidates for the
  §3.6 amber (§11), and the X1 freeze list (§12).

Twenty-nine findings came out of the derivations (§0.4). Four of them change whether a canonical
snippet derives:

- **F-1.** Without a covering-write rule the canonical `q4_matvec` fails the NaN sink check: the
  caller's `y` is raw, and a summary analysis joins it with the canonical writes. (If the check looks
  only at the values written, the failure moves to the next exact sink downstream.) This note adds
  `T-Cover`.
- **F-2.** The canonical schedule names `j` and `acc`, which are bound in the callee `q4_row_dot`, not
  in `q4_matvec`. Names must resolve over the inlined KIR.
- **F-3.** `Matrix::row` is kernel-callable only with a `Matrix` invariant that no snippet shows.
- **F-18.** `moe_ffn`'s `deterministic` block needs a `DeclareDeterministic` grant for its module,
  which the manifest example does not give.

None of these changes a decision. Each has a proposed rule or wording.

The first independent review (two same-family reviewers, 2026-10-16, §17) reported 53 findings, 7
of them blockers. Each was checked against the sources and accepted; in 4 of them a sub-claim or a
proposed placement was declined (§17). Several made theorems false as first stated: implicit flows
through `break`, `continue` and `return` were not tracked; `T-Det`'s mask erased schedule taint that
the block's inputs carried in; closure calls had no result grade; loans were not propagated through
assignments and calls; `T-Cover` allowed an exit after the covering write; and a `par` that returned
early left schedule-dependent contents in places graded `cross_device`. §0.5 lists the 30 resulting
findings (F-30 to F-59) and the rules that now close them; the remaining review items corrected the
gate record, the prelude and the tombstones. No canonical verdict changed. One derived verdict (D-D11) now rests on a new provisional rule, and the agreement
rule now covers the out-of-X1 derived snippets (§0.3, Q10).

One cross-track conflict needs the Owner (§12, Q9). The X1 track's design draft rejects `par for`,
`deterministic`, `schedule`, `spec` and `linear` in `mithi` as "not yet", but ROADMAP §3.6 requires
`mithi` to accept every canonical snippet, and the canonical snippets use them. This note recommends
typing-only acceptance in `mithi`; it does not loosen the gate.

**Contents**

0. [Gate record and findings](#0-gate-record-and-findings)
1. [Scope, settled inputs and conventions](#1-scope-settled-inputs-and-conventions)
2. [Syntax](#2-syntax)
3. [Elaboration from the surface](#3-elaboration-from-the-surface)
4. [Judgement forms](#4-judgement-forms)
5. [Static semantics](#5-static-semantics)
6. [Dynamic semantics](#6-dynamic-semantics)
7. [Theorems](#7-theorems)
8. [Noninterference with the trap fallback: the §3.6 narrowing check](#8-noninterference-with-the-trap-fallback-the-36-narrowing-check)
9. [Hand derivations: summary](#9-hand-derivations-summary)
10. [Tier 0 trace](#10-tier-0-trace)
11. [Idioms that do not type: amber candidates](#11-idioms-that-do-not-type-amber-candidates)
12. [What is frozen for X1's subset](#12-what-is-frozen-for-x1s-subset)
13. [Open problems](#13-open-problems)
14. [Proposed changes to sibling documents](#14-proposed-changes-to-sibling-documents)
15. [Tombstones](#15-tombstones)
16. [Owner questions](#16-owner-questions)
17. [Review log and signature block](#17-review-log-and-signature-block)

---

## 0. Gate record and findings

This note is a deliverable, not an experiment, but its gate is evaluated like one. This section maps
it onto the record template of [docs/m0/README.md](README.md#record-template), so the Gatekeeper
has fixed units before `mithi` produces a single verdict.

### 0.1 Assumption under test, and what follows if it is false

One small calculus types every canonical idiom of Mithril and supports the four theorems of
ARCHITECTURE §5.5. If an idiom that X1's reference solutions need cannot be typed, it becomes a Dc
rule and X1 measures its cost (ROADMAP §3.6 amber). If `timing_only` noninterference cannot be stated
together with the trap fallback, the policy feature is redesigned before M4 (ROADMAP §3.6
narrowing). There is no kill row for this note in ROADMAP §4.

### 0.2 Inputs pinned

- Mithril documents at commit `ec46300926d4efa4e36fb022a19ea0285fde1c96`. On 2026-10-16 the working
  tree of every file the snippets come from was identical to that commit (`git diff --stat HEAD`
  empty for README.md, docs/ARCHITECTURE.md, docs/ROADMAP.md and docs/architecture/) [M, CC track].
- Hearth `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220` (GitHub `main`, 2026-10-16), read for
  `hx_quant.h`, `docs/NUMERICS.md`, `governance/INVARIANTS.md` and `store.c` [M, CC track: `git log -1`].
- Snippet identities: SHA-256 of each fenced `mith` block body, by the rule in verdicts.json [M, CC
  track script, 2026-10-16]. A snippet whose hash changes needs a new derivation before `mithi` is
  judged on it.

### 0.3 Units, counting rules and outcomes (made more precise; no ROADMAP threshold moves)

| Term | Definition (fixed before `mithi` exists) |
|---|---|
| Canonical snippet | Each fenced `mith` block in ARCHITECTURE §5.3 (7 blocks) and in README "A taste" (1 block): 8 blocks [M] |
| Derived snippet | Each other fenced `mith` block in ROADMAP.md and docs/architecture/01–07 at the pinned commit: 37 occurrences, so 45 in all, 35 distinct by hash [M]. Negative examples written as comments inside a block (`// fn first_dyn …`) are separate items with an `n` suffix |
| Agreement | For **every** canonical and derived item in verdicts.json and each negative item marked `gate_item`: `mithi`'s verdict (accept or reject) equals the expected one, and for a reject its primary diagnostic code equals the expected code. For an item in X1 scope (`scope` of `x1` or `x1-front-end`) the expected verdict is the calculus verdict. For an item outside X1 scope the expected verdict at the checker precondition is the out-of-scope rejection in its `x1_expected` field, `E-OUT-OF-SCOPE-<KW>` [prov], where KW names the first out-of-X1 keyword, format code or `std_platform` name in source order (§12); the calculus verdict is recorded beside it and becomes the expected verdict when the construct enters scope (Q10). The primary code is the first emitted code in the precedence order of §5.16. Facts (row, `may_trap`, output grade) are secondary and reported |
| Conditional item | An item whose verdict depends on a declaration outside the snippet. Its conditions are listed, and the prelude of [derivations §P](core-calculus/derivations.md#p-the-canonical-prelude) supplies them |
| Tier 0 rule atom | Each rule-bearing line the Tier 0 card must carry under [05 §2](../architecture/05-agent-protocol.md#2-reference-cards-and-budgets): the three clauses of the subset rule, the seven rules of the "Rules" block, each keyword and the effect and grade lists, each false-friend row of [01 §2.5](../architecture/01-language.md#25-seed-false-friend-table-v0), each of the eight snippet constructs, and the loop and verbs block. 57 atoms (§10) |

Outcomes, operational:

| Outcome | Condition | Action |
|---|---|---|
| Pass | 100% agreement on every item of the agreement rule; 100% of Tier 0 atoms traced (semantic atoms to rules; protocol atoms per Q4, and until Q4 is answered each protocol atom must also cite a section of this note, §10); Prover and Adversary reviews from a model family other than the author's logged (ROADMAP §3.6, D0-10); Owner signature | X1 subset frozen as §12 |
| Amber | An idiom in an X1 reference solution does not type under §5 | It becomes a Dc rule with a code and a fix; X1 measures its cost through the subset rejection rate (ROADMAP §3.2 amber c) |
| Narrowing | Noninterference cannot be stated with the trap fallback (§8) | The policy feature is redesigned before M4 |
| Not a gate outcome | A disagreement caused by a `mithi` bug | Fixed under ROADMAP §3.2's re-scoring rule |
| Not a gate outcome | A disagreement caused by an error in this note | An amendment, dated, before the freeze; after the freeze it applies from M1 if it flips an X1 verdict (ROADMAP §3.2) |

### 0.4 Findings

Each finding was found while deriving a snippet or stating a theorem. "Fix" names where this note
resolves it; §14 lists the changes that sibling documents would need.

| ID | Finding | Fix in this note |
|---|---|---|
| F-1 | A weak (summary) update of a written array joins the caller's raw NaN state with canonical writes. If the sink check reads the final contents, the canonical `q4_matvec` and 07's `softmax` fail `E-NAN-RAW-SINK` at once; if it checks only the values written, the kernel passes but its transfer still depends on the old `y`, and the error appears at the next exact sink downstream | `T-Cover`: a loop that writes every element exactly once is a strong update (§5.9) |
| F-2 | The canonical schedule names `j` and `acc`, bound in `q4_row_dot`, not in `q4_matvec` | Schedule names resolve over the inlined KIR and must be unique there (§5.14) |
| F-3 | `Matrix::row` is kernel-callable only if its slice bounds are discharged, which needs `invariant Matrix { blocks.len() == rows * blocks_per_row }`; no snippet shows it | The prelude declares it; `kcall` predicate (§5.10) |
| F-4 | 01's T-CloE has no capability-capture premise, so a function without `io` could create an `io` closure and hand it to `spawn` | `T-CloE` requires and charges ε_e ⊆ Σ; service threads are attributed to their closure's row (§5.7, Thm 2) |
| F-5 | Theorem 4's "non-failing environment" covers only the store's demand set; a direct `read_slab` of a faulty copy returns `Err` in a non-failing environment | Non-failing is generalised to direct I/O outside `det` blocks (§7.4) |
| F-6 | In `par`, the join waits for started iterations above the winner, so the parallel run can diverge where the serial projection terminates | Stated: `par` refines its serial projection for partial correctness; cooperative cancellation is a by-trigger option (§6.4, tombstone) |
| F-7 | After an early exit, "unspecified" written places must still satisfy types, ranges, invariants and enum validity; a fixed-byte test poison can violate them | Unspecified means "pre-loop value or a value some iteration wrote"; test poison must be a valid value of the type (§6.4) |
| F-8 | Stack exhaustion in the C11 lowering aborts the host; it is not a trap | "Never aborts the host" holds modulo stack; a static stack bound or a recursion guard is proposed (§6.3, OP-6) |
| F-9 | 01 §12.2's fail-domain table omits `main`, scoped threads and services | Added (§6.3) |
| F-10 | O1–O6 do not name fallback totality or core trap-freedom, which noninterference needs; "default policy" in ROADMAP §3.6 must mean the port's declared fallback | Premises F-tot and P-tot (§8); P-tot was replaced by the weaker P-ind after review (F-47) |
| F-11 | A deadline overrun is a scheduler choice: it does not affect output noninterference, but `timing_blind` exact replay holds only for runs with zero deadline strikes | Corollary 3c (§7.3) |
| F-12 | Grades of trait-method calls in generic bodies have no modular rule | In v0 a grade transfer is bounded by the row, so trait-declared rows bound impl transfers (§5.12) |
| F-13 | `f32::total_cmp` observes NaN payload and sign but is missing from 01's observer list | Added to the observers (§5.3) |
| F-14 | The arithmetic semantics of contract expressions (`requires o.len() == heads * dn`) is unspecified | Checked evaluation: an overflow in a contract is a contract violation (§5.10) |
| F-15 | Global heap allocation (`Vec`, `String`, `Box`) has no row rule; the derived `moe_ffn` returns an owned `Act` without an `alloc` label | Provisional `alloc(Global)` rule for X1, flagged for review (§12, OP-1) |
| F-16 | `HashMap` with Rust's `RandomState` exposes a nondeterministic iteration order | Provisional: iteration carries `nondet`; lookup does not (OP-2) |
| F-17 | User `impl Drop` is unspecified; with traps that skip it and a host that survives, it is a false friend | Provisional Dc `E-DROP-IMPL` (§11, tombstone) |
| F-18 | `moe_ffn`'s `det` block needs `DeclareDeterministic` for its module; 01 §11's manifest grants only `store` | Derivation conditional; §14 P-9 |
| F-19 | Whether `det[E]` masks writes to outer places is unstated | Only the result value is masked (§5.11) |
| F-20 | "abandon" names both the agent role verb (03 §9, 05 §10) and the trap-path release of linear values (01 §12.4) | Owner question Q7 |
| F-21 | 05 §3 says the built-in `name!(…)` forms are a closed list "in 01", but 01 has no list | X1 list proposed (§12) |
| F-22 | Whether an absent `uses` clause on a `pub fn` means `uses {}` is unstated | It does (§5.2) |
| F-23 | The type of an unconstrained hole binding (`let score = todo!(…);` with no later use) is unstated | Defaulted per the pinned edition; accepted (§5.10) |
| F-24 | Whether `Frozen<SlabBuf>` is linear (its last release would drop a linear `SlabBuf`) is unstated | Provisional: `Frozen<T>` is linear iff `T` is (§5.1, OP-4) |
| F-25 | `T-Par`'s disjointness check must see through user projections (`y[t][r]` on `Matrix` in 02's `q4_matmul`) | Projections may declare a footprint; otherwise the item is conditional (§5.9) |
| F-26 | An escaping closure created inside `det[E]` keeps `nondet` in its type; the mask applies to exercised rows, not to types | Stated (§5.11) |
| F-27 | Kernels call non-kernel helpers (`Matrix::row`, `rows()`); the rule for which helpers are allowed is unstated | `kcall` predicate (§5.10) |
| F-28 | `heat_view`'s rejection comes from `with_lock`'s implicit non-`Local` bound on its result type, not from T-Ret: `heat_view`'s own signature is a valid projection | Code `E-REF-ESCAPE` kept as the reported code for that case (§5.7) |
| F-29 | 01's `d°` ("scope with the nondet taint masked") needs provenance; a two-component scope makes it a plain function | `d = ⟨d_s, d_p⟩` (§2.3); the first draft's mask also erased input taint, corrected by F-32 |

### 0.5 Findings from the first review (2026-10-16)

Two independent same-family reviewers (§17) reported 53 items. Each was checked against the sources;
those that change a rule are recorded here. "R1-n" and "R2-n" are the reviewers' item numbers in the
§17 log. Every new rule is [prov].

| ID | Finding (review items) | Fix in this note |
|---|---|---|
| F-30 | `break`, `continue` and `return` decisions were not tracked, so a `for` body was never typed under its guard's grade and writes after `if h { break }` or `if h { return }` escaped `h`'s grade (R1-1) | Jump grades `J(L)` per jump target, raised at each jump, part of the effective pc until L is left (§5.5 `T-Jump`, `T-Loop`) |
| F-31 | `T-Return` did not record its context, so a `&mut` referent written just before an early `return` was missing from `θ_mut` (found while verifying R1-5) | Returns record the `&mut` referents in the exit context `X`; `T-Fn` reads `θ_mut` from the body's end joined with `X` (§5.5, §5.15) |
| F-32 | `T-Det` masked every schedule component, including taint the block's inputs carried in, so `det[E] { v }` laundered a value read from a `Mutex` before the block; 01's `d°` keeps input taint (R1-2) | The result's schedule component is recomputed from the block's free inputs; Lemma F assumes E's claim for every scheduler and every non-failing environment (§5.11, §7.5) |
| F-33 | `T-Det` accepted evidence about any definition whose closure contains the block, and the prelude's fixture named a glob subject, so evidence that never exercised a block could mask it (R1-16, R2-9) | E's subject is the block itself (by anchor), or the enclosing definition when the block is its whole body, resolved to content hashes at admission (§5.11) |
| F-34 | A `det` block could return a closure that runs `nondet` code later, outside the block's extent (R2-8) | `E-DET-RESULT`: a `det` block's result type contains no closure type and is not `Local` (§5.11) |
| F-35 | Closure types carried no grade summary: a closure call had no result grade, a generic body that invokes a closure parameter under a high pc did not raise the closure's by-mut captures, and lazy adapters applied capture writes at the wrong call (R1-3, R2-6, R2-7) | Each creation site κ has a summary `Θ_κ`; closure calls apply it; callees declare an invocation transfer `θ_inv`; a call whose argument type mentions `clo⟨κ⟩` applies κ's capture writes at its own pc; std higher-order signatures state their transfers (§5.7) |
| F-36 | Restricted contexts checked only the charged row, so a `Local` closure or a `det` block inside a `par` body ran `nondet` code that `E-PAR-EFFECT` never saw, and Lemma B was false (R1-7, R2-10) | An exercised row `ε^x` (charged labels, plus the rows of `Local` closures called, plus `nondet` removed by `det`) is what `E-PAR-EFFECT`, (k1) and (t1) check (§5.5, §5.9) |
| F-37 | `T-Cover` forbade exits only before the covering write, so a `break`, `return` or `?` after it left later elements unwritten under a strong update (R1-4, R2-3) | Premise 0: no `break`, `continue`, `return` or `?` anywhere in the body; conditions are stated on the surface loop (§5.9) |
| F-38 | After a `par` returned early, its written places held schedule-dependent contents, but code after the return in the caller read them at `cross_device` (R1-5) | A `par` whose body may return joins `γ_unspec` into W in the exit context of those returns; Theorem 4's condition (iii) becomes a consequence of typing (§5.9, §7.4) |
| F-39 | Loan carriers were never propagated: a reference stored through `&mut`, pushed into a `Vec` or swapped out lived past its target, and a write through a local reference updated the reference's grade instead of the borrowed place's (R2-1, R1-6, R2-2) | Values carry loan sets `L`; writes go to `target*(p)` through loans; `E-BORROW-OUTLIVE` at scope end; `E-LOCAL-MUT-STORE` for storing foreign loans into a parameter's referent (§5.4, §5.5) |
| F-40 | A closure could return a loan on one of its captures through a signature that elision ties to a parameter, and a direct closure call's result carried no loan (R1-8, R2-1) | Closure result discipline: `T-Ret` (a) applied to the closure signature at a bound; direct calls give the result the capture loans (§5.7) |
| F-41 | A closure that moves a Linear value, and `Vec<Lease>`, `Option<Lease>` or a generic `drop(lease)`, dropped linear values silently (R1-9, R2-5) | K-Lin covers closures and std generics; every type parameter has an implicit `¬Linear` bound that only std may relax (`E-LINEAR-INSTANTIATE`) (§5.1, §5.8) |
| F-42 | A trap lost Linear values held by the callee's by-value parameters and by already-evaluated temporaries in the discarded context (R1-10) | `E-Call` puts Linear by-value parameters in `Φ.lin`; elaboration invariant E6 names every Linear temporary (§3.1, §6.2) |
| F-43 | An invariant could be broken between a field write and the end of a `&mut` loan, or through a loan on a field, while a kernel assumed it and erased its bounds checks (R1-11, R2-4) | Invariants and field ranges are asserted at publication points and at the end of any `&mut` loan on a sub-place, and assumed only for unwritten, unloaned values (§5.10) |
| F-44 | Path facts were never killed on reassignment, so a stale fact could discharge a kernel bounds check (R1-12) | Φ ranges over SSA versions; every write creates new versions and kills facts on the old ones (§5.10) |
| F-45 | Footprints were `ensures` clauses, checked at run time outside kernels, which a ghost predicate cannot be; and D-D11's inner `par` takes `&mut` on the same row in every iteration (R1-13, R1-14, R2-27) | Footprints are discharged statically (`E-FOOTPRINT`); rule `Proj-Split` lets a footprinted projection borrow only its footprint and split it per iteration (§5.6, §5.9) |
| F-46 | Preservation's "grade and row do not grow" was false at `E-Det`, `T-Cover` was not preserved after one iteration, and the runtime terms had no typing (R1-15) | `det` is an administrative runtime frame; runtime typing rules for frames, joins, traps, ports and `⊠`; element-wise heap grades (§6.2, §7.1) |
| F-47 | P-tot demanded that the core never trap, which input-dependent traps violate although Theorem 3 needs only oracle-independence of traps (R1-17, R2-17) | P-ind replaces P-tot (§7.3, §8) |
| F-48 | A policy could exhaust the core thread's stack inside a port call and abort the host; N4 was marked closed (R1-18, R2-16) | (t9) a static stack bound; premise S-tot; `E-TO-STACK` at ports; row N10 (§5.13, §7.3, §8.3) |
| F-49 | `E-Par-Join` let a fault above the winning index override the serial outcome and named "the first fault recorded"; "non-failing" was a property of one run; `oom(A)` was a trap whose occurrence depends on the environment (R1-19, R2-11, R2-12) | Faults join the lowest-index rule; non-failing quantifies over every scheduler; arena exhaustion is an environment fault except in program-sized sub-arenas; premise A-ind (§3.4, §6.4, §7.4) |
| F-50 | The transfer form could not express NaN-observer taint, which depends on whether an argument is raw, and the claim that every scope taint comes from a row label was false (R1-20, R2-14) | θ gains an observer set O; `Θ_impl ⊑ Θ̂_m` is checked with `E-IMPL-GRADE` (§2.5, §5.12) |
| F-51 | `nanrule` had no default case, marked `clamp` canonical though FF-NANMAX pins only `max` and `min`, and the conformance axiom exempted NaN payloads even for `canon::nan` (R1-21, R2-13) | `nanrule` is total with default raw; `clamp` and `f64::max`/`min` are raw; conformance is bit-exact except NaN results of raw-rule primitives (§5.3, §6.1) |
| F-52 | `⊢_sch` recorded licence classes but never decided them, so a schedule that vectorises a float accumulator passed the front end (R2-18) | (s3') decides `exact` and `int_assoc` from the loop-carried dependences (§5.14) |
| F-53 | `⊢_to`, `⊢_k`, `kcall` and `E-DET-POLICY` are facts about callee bodies, which a generic body checked once cannot know (R2-15) | Side judgements are evaluated on the monomorphised call graph (§5.12) |
| F-54 | `x op= e` was elaborated as `x = x op e`, which reads x before evaluating e; Rust evaluates the right operand first for primitive operands and the assigned value before the assignee (R2-22) | Right operand first, then the place and its index asserts (§3.2, §6.2) |
| F-55 | Theorem 2(b) attributed a step to "the nearest enclosing call", which a `par` iteration or scoped child's stack does not contain (R2-24) | A logical parent link; (b) over the logical call stack; (b'') for scoped children (§7.2) |
| F-56 | Unlabelled nondeterminism: user-visible atomics (01 §6.1 labels them `nondet`), `{:p}` formatting, and `HashMap` APIs other than iteration whose output or callback order follows buckets (R2-25) | Atomics carry `nondet`; `{:p}` is Dc (`E-FF-ADDR`); C-HASH covers every bucket-order API (§5.3, §12) |
| F-57 | The grade of a hint value received by the core was unstated, so a hint flowing into an exact sink was not a type error (R2-26) | Hint values are graded `γ_sh` (§5.13) |
| F-58 | Lemma 3a ran `C[𝒪_r]` under a scheduler for a different configuration space; Lemma 3b did not quantify over interleavings; policies set MXCSR's sticky status flags (R1-22, R2-23) | `proj(s)`; Lemma 3b over every scheduler; the port wrapper restores MXCSR (§7.3) |
| F-59 | The std functions admissible in exact context were never listed, and FF-SUM's `product` and `fold` were missing from `cls` (R2-30) | Closed X1 list C-EXACT-STD (§12); `cls` covers `sum`, `product` and `fold` (§5.0) |

---

## 1. Scope, settled inputs and conventions

### 1.1 What MCore is for

MCore is MIR in [04 §2](../architecture/04-toolchain.md#2-the-pipeline-and-its-irs): monomorphised,
with moves, borrows, consumes, capabilities and trap sites explicit. It is the object of three
checks:

- **`mithi`'s independent mode** re-derives the typing of this note from source, with its own parser
  and checker (DR-010). At X1 it is the checker the agents use (ROADMAP §3.2).
- **`mithc`'s THIR** must agree with it. That agreement is graded `tested` (DR-010).
- **KIR** is derived from MCore kernel bodies. That elaboration is a trusted code component graded
  `tested` (DR-021, 03 §3.4).

Schedules, specs, stores and evolve slots are not MCore terms. Each has a side judgement (§5.13,
§5.14) that the front end checks; their soundness comes from T0, T1 or T2 on emitted code, not from
this note.

### 1.2 Settled inputs (not re-opened here)

- Rust-shaped surface, no false friends, the subset rule C / Dc / D (DR-002).
- Strict IEEE binary32/64 with canonical reduction order, so bit-exact verification reduces to
  FP-DAG matching (`canon.v1`, ARCHITECTURE §6.1).
- Specified transcendentals, `cr::` and `canon_v1::`, not platform libm (DR-014). Which one each
  Hearth call site uses is D0-2; examples here that name one are provisional, pending D0-2.
- Translation validation against Mithril's own x86 semantics table (DR-008); SMT contracts, not Lean
  (DR-010, DR-012); prove the space, not the candidate (03 §5).
- MVS, second-class references, projections, the non-escaping kind, linear resources, `Send`/`Sync`,
  audited `std_platform` (DR-004, G05).
- Effects as capabilities, fixed label set, no user effects in v0 (DR-006, D-02).
- Static-dispatch traits only (DR-005).
- Compiler in Rust, C11 backend first, traps by status return (DR-026, 04 §9.1).

### 1.3 Conventions

- **Evidence tags** follow [docs/m0/README.md](README.md#evidence-tags). Bounds such as 65,024 are
  [D] with their formula. Hashes and counts produced by this track's scratch scripts are [M] with the
  date. Design choices made here are [G] when they are judgments and carry **[prov]** when they are
  provisional rules that this note proposes and that the review and the Owner's signature can reverse.
- **Status labels** follow ROADMAP §1 rule 7 (v0, v1, later, reserved, by-trigger).
- **Diagnostic codes** follow 01 and 05 where they exist (`E-REF-ESCAPE`, `E-LINEAR-DROP`, …). New
  codes proposed here are marked [prov]; 05 stabilises codes.
- **Owner decisions.** Nothing here decides a D0 item. Where a rule depends on one, it says
  "provisional, pending D0-x".
- **Notation.** `⊔` is join (the lossier grade, set union on B), `⊑` its order, `∪` set union of rows.
  `Γ ⊢ … ⊣ Γ'` threads the flow-sensitive context. `ā` is a sequence. `[x ↦ v]` updates a map.
  Rules are written premises over a line, conclusion under it, name on the right.

---

## 2. Syntax

### 2.1 Names

| Metavariable | Ranges over |
|---|---|
| `x, y, z` | variables (locals, parameters) |
| `g, h` | function names: user, std, `std_platform`, primitives (`prim`) |
| `S` | nominal type names: structs, enums, linear structs, format-derived structs, std types |
| `Tr` | trait names |
| `A` | arena names (type-level) |
| `E` | evidence names (ledger facts; at X1, fixture names, §12) |
| `σ` | trap sites (§3.4) |
| `λ` | loans |
| `κ` | closure-creation sites |
| `n` | integer constants; `t` device classes (reserved) |

### 2.2 Types, modes and kinds

```text
ι   ::= i8 | i16 | i32 | i64 | isize | u8 | u16 | u32 | u64 | usize | bool | f32 | f64
s   ::= f16 | bf16                                   storage-only scalars: no arithmetic primitive
τ   ::= ι | s | () | ! | (τ̄) | [τ; n] | S⟨τ̄; n̄⟩ | α
      | &τ | &mut τ                                  second-class references; τ may be a slice [τ']
      | [τ]                                          unsized slice, only under & or &mut
      | fn(m̄ τ̄) -> τ ! ε ▷ Θ [lin]?                 escaping function value: row, transfer summary and
                                                     linearity in the type (F-35, F-41)
      | clo_E⟨κ⟩(m̄ τ̄) -> τ ! ε_κ                    escaping closure created at site κ; coerces to fn(…) ▷ Θ
                                                     when Θ_κ ⊑ Θ
      | clo_L⟨κ⟩(m̄ τ̄) -> τ                          Local closure created at site κ; row ε_κ charged at κ
m   ::= own | ref | mut                              parameter mode: by value, &, &mut
K   ::= Copy | Linear | Local | Send | Sync          derived kinds (§5.1); Δ ⊢ τ : K
Δ   ::= type and const variables with bounds  α : Tr, α : ¬Local and α : ¬Linear (implicit),
        α : ?Local and α : ?Linear (std signatures only)
```

Every closure-creation site κ has a summary `Θ_κ = (θ_ret, θ_mut,q for each by-mut capture q,
θ_exit, mt_κ, ε_κ)`, computed from its body by `T-CloL` or `T-CloE` over symbols for its parameters
(§5.7). A type that mentions `clo⟨κ⟩`, directly, behind a reference or as a type argument of a std
adapter (`Map<I, clo_L⟨κ⟩>`), carries κ, so every rule can look the summary up.

There is no `dyn`, no lifetime parameter and no raw pointer type outside packages granted `unsafe`
(DR-004, DR-005). Std and `std_platform` types used by the canonical snippets: `Option`, `Result`,
`Hint<T>`, `Mutex<T>`, `Frozen<T>`, `SlabBuf`, `Arena<A>`, `Aligned<T, n>`, `Quantity<U, O>`,
`BlobFile`, and the capability types `Root`, `Fs`, `File<M>`, `Spawner`, `Clock`, `MemCap`.

### 2.3 Rows and grades

```text
ℓ   ::= io | spawn | alloc(A) | time | foreign | unsafe | fp_env | compile | lossy
      | nondet | nondet(platform) | blob                         the fixed v0 label set (01 §6.1)
ε   ::= {ℓ̄}                                                      finite set; no row variables in v0

f   ::= exact | real(b) | approx(p)        fidelity     exact ⊑ real ⊑ approx (real, approx reserved)
d   ::= ⟨d_s, d_p⟩                         scope, two components (F-29):
         d_s ∈ {cd ⊑ sd}                     the schedule component (nondet)
         d_p ∈ {cd ⊑ dev(t)}                 the platform component (nondet(platform), NaN observers)
         |d| = cross_device        if d = ⟨cd, cd⟩
             = device(t)           if d = ⟨cd, dev(t)⟩       (reserved; in v0 dev(platform) reads as
             = schedule_dependent  if d_s = sd                schedule_dependent, 01 §13.4)
B   ⊆ Evid                                 the data-flow set of deterministic boundaries (01 §7.2)
ν   ::= canon ⊑ raw                        NaN-canonicality of float content (canon for non-floats)
γ   ::= (f, d, B, ν)                       a grade; ⊥ = (exact, ⟨cd, cd⟩, ∅, canon)
pc  ::= (f, d, B)                          the control grade
ω                                          the exit grade: join of pc over reachable returns, traps
                                           and early exits (01 §13.6, Theorem 4)
```

`γ ⊔ γ'` is componentwise: fidelity and scope components by their orders, `B ∪ B'`, and `raw` if
either is `raw`. Joining a `pc` into a grade leaves `ν` unchanged.

Splitting the scope into two components is a presentation of 01's lattice, not a new one: `|·|`
maps it onto `cross_device ⊑ device(t) ⊑ schedule_dependent`. It lets `T-Det` drop the `nondet`
contribution without 01 §13.4's "taint provenance": the result keeps `d_p`, and its schedule
component is recomputed from the schedule components of the block's free inputs (F-32). The first
draft defined the mask as `⟨d_s, d_p⟩ ↦ ⟨cd, d_p⟩`, which also erased taint the inputs carried into
the block; that is not 01's `d°` ("the scope the body would receive if `taint(nondet)` were ⊥").

### 2.4 Places and expressions

```text
p   ::= x | p.f | p[e] | p[e..e] | *p | g(p, ē)       places; g a projection (§5.6)

e   ::= v | copy p | move p | &p | &mut p | p = e
      | let x: τ = e; e | let mut x: τ = e; e | e; e
      | g::⟨τ̄⟩(ē)                                     call, after method resolution and monomorphisation
      | prim_ℓ̄(ē)                                     primitive with its row labels
      | S { f̄: ē } | (ē) | [ē]
      | if e { e } else { e } | match e { (pat => e)̄ }
      | loop_L { e } | break_L | continue_L | return e  L: the loop a jump targets (a Rust label, or the
                                                       innermost loop); return targets the function F
      | clo_L⟨κ⟩[c̄] |x̄: τ̄| e | clo_E⟨κ⟩[c̄] |x̄: τ̄| e | e(ē)
      | assert⟨σ⟩(e)                                   an explicit trap site guarded by e
      | trap(σ)
      | par i in e..e { e }
      | scope { e }                                     structured spawning (std)
      | det[E] { e }
      | comptime { e }                                  staging (§5.14)
c   ::= x by ref | x by mut | x by move                closure captures
```

### 2.5 Items and signatures

```text
D   ::= fn g⟨Δ⟩(x̄: m̄ τ̄) -> τ  uses ε?  requires φ̄  ensures ψ̄  { e }
      | kernel fn …  |  policy fn …                  same shape, kind kernel or policy
      | struct S⟨Δ⟩ { f̄: τ̄ }  |  linear struct S⟨Δ⟩ { f̄: τ̄ }  |  enum S⟨Δ⟩ { C̄(τ̄) }
      | invariant S { φ }  |  #[range(lo..=hi)] on fields and parameters
      | trait Tr⟨Δ⟩ { (fn sig)̄ }  |  impl⟨Δ⟩ Tr for τ { D̄ }  |  impl⟨Δ⟩ τ { D̄ }
      | format S { (field: code)̄ }                    elaborated by ⊢_fmt (§5.14)
      | schedule …  |  spec …  |  store …  |  evolve slot …   side judgements, not MCore terms

sig(g) = ∀Δ. (m̄ τ̄) -> τ_r
         row       ε_g
         transfers Θ_g = (θ_ret, θ_mut,1 … θ_mut,k, θ_exit, θ_inv,1 … θ_inv,c)
                   one per result, per &mut, per exit, and per closure-typed parameter (F-35)
         may_trap  mt_g ∈ {true, false}
         contract  (φ_req, ψ_ens)
         kind      ∈ {fn, kernel, policy, std, prim, proj(x★, m★)}
θ      = (γ⁰, D, n, O)  with O ⊆ D                                                            (F-50)
         γ_out = γ⁰ ⊔ ⨆_{j∈D} γ_j ⊔ pc_call ⊔ (obs⁰ if some j ∈ O has ν_j = raw)
         obs⁰ = (exact, ⟨cd, dev(platform)⟩, ∅, canon);  n ∈ {canon, raw, pass(D_ν)} gives ν_out
```

O is the set of parameters whose raw float content reaches a NaN observer (§5.3) on some path. A
transfer without it would have to add `obs⁰` always, which falsely rejects hashing canonical values
through a helper, or never, which is unsound. `θ_inv,j` is the join of the pc at every point where
g, or a function g passes the closure to, invokes closure parameter j.

### 2.6 Runtime syntax

```text
loc                                       heap locations;  π ::= · | π.f | π[n] | π[n..n]  paths
v   ::= n | b32(bits) | b64(bits) | true | false | () | (v̄) | [v̄] | S{f̄: v̄} | C(v̄)
      | ref_m(loc·π, λ)                   reference: target, mode, ghost loan tag (erased, Lemma C)
      | ⟨clo, κ | ε, env, body⟩           closure value
      | cap(k, ℓ̄)                         capability token; no constructor outside std_platform
      | hint(v) | nohint
      | ⊠                                 moved-out or uninitialised marker
e   ::= … | det_E⟨e⟩ | join(j)            runtime-only terms: the administrative det frame (F-46) and a
                                          par join point
H   : loc ⇀ v                             plus std objects: mutex state, Frozen refcounts, arena chunks
Ψ   : loc·π ↦ (τ, γ)                      heap typing; arrays and slices carry one grade, NaN bit included,
                                          per element (F-46)
Φ   ::= ⟨g, ρ: x ↦ loc, lin: [x̄], dom: k?⟩   frame: locals, live linear locals in creation order,
                                               fail-domain kind if the frame is a domain (§6.3)
T   ::= ⟨Φ̄ ; e⟩ | ⟨Φ̄ ; ⇑(σ, ī)⟩            thread: frame stack and redex, or a trap propagating
J   ::= ⟨par-id, lo, hi, r: i ↦ {pending, running, Normal, Exit(o), skipped}⟩     par join record
Π   ::= port ↦ ⟨committed state block, strikes, ejected⟩
C   ::= ⟨H, T̄, J̄, Π⟩                     configuration
c   ::= sched(tid) | claim(par-id, i) | io(req) | lock(tid) | hint(port, h) | overrun(port, b)
o   ::= Val(v) | Trap(σ, ī) | Fault(φ) | Ret(v)          outcomes; Ret only inside par (early return)
e_nv : (slab, copy) → {ok, fault},  cap_nv : A → ℕ        the environment, fixed before a run (01 §13.5)
```

---

## 3. Elaboration from the surface

### 3.1 Invariants of elaboration

Elaboration `⟦·⟧` maps checked HIR to MCore. It has six invariants. `mithi` and `mithc` must both
satisfy them, and the differential test (DR-010) compares them.

1. **E1, coincidence.** For a construct of class C, the serial semantics of `⟦e⟧` equals the pinned
   Rust edition's meaning on every run that does not panic. Where Rust panics, `⟦e⟧` traps at a site
   of the same kind. Where Rust leaves a choice open, the Surface Map's pinned choice applies (01
   §2.1).
2. **E2, explicit traps.** Every place Rust can panic becomes an explicit `assert⟨σ⟩(φ)` or
   `trap(σ)` (§3.4). No primitive traps implicitly.
3. **E3, explicit authority.** Each label in a function's row becomes an implicit capability
   parameter `κ_ℓ`, passed at every call (erased in C, Lemma C).
4. **E4, keyword-led novelty.** A D construct elaborates only from a keyword, a new type or a new std
   name (DR-002). Nothing reinterprets a Rust form.
5. **E5, erasure.** Rows, grades, kinds, loans and the NaN bit have no runtime representation. The
   only code elaboration adds is undischarged `assert`s outside kernels, `canon::nan` where the
   source wrote it, and `abandon` on trap paths (Lemma C).
6. **E6, named Linear temporaries [prov, F-42].** Every Linear-typed subexpression that is a call
   argument, a struct-literal field, a tuple or array component, or a match scrutinee is let-bound
   to a fresh local before the next operand is evaluated (A-normal form for Linear values). It then
   sits in `Φ.lin`, so a trap in a later operand abandons it (§6.3). This names a temporary the C
   lowering creates anyway; it adds no code.

### 3.2 Every surface form in the canonical snippets

| Surface form | Snippet | MCore | Rule |
|---|---|---|---|
| `kernel fn g(…) -> τ requires φ { … }` | `q4_row_dot` | `fn g` of kind kernel, contract `(φ, true)`, context `exact` | `⊢_k` |
| `policy fn g(…) -> Hint<T> { … }` | `pick_victim` | `fn g` of kind policy, row ∅ | `⊢_to` |
| `fn g(…) -> τ uses { ℓ̄ } { … }` | `read_slab`, `acquire` | declared row `{ℓ̄}` | `T-Fn` |
| `/// …` doc comment | all | erased (metadata, not semantics) | — |
| `let mut x: τ = e;` | `acc`, `isum`, `best` | `let mut x: τ = ⟦e⟧;` | `T-Let` |
| `for i in a..b { body }` | loops | `let mut i = ⟦a⟧; let n = ⟦b⟧; loop_L { if i >= n { break_L } ⟦body⟧ⁱ; i = i + 1 }`, where `⟦body⟧ⁱ` rewrites `continue` to `{ i = i + 1; continue_L }`. `b` is evaluated once, as Rust's `Range` is. The increment cannot overflow because `i < n`, so its assert is discharged. The guard's `break_L` raises `J(L)` by the grades of `i` and `n`, so the whole body is typed under them (F-30). Rules that speak of "the loop body" (`T-Cover`) mean the surface `body`, not the elaborated header | `T-Loop`, `T-Jump` |
| `for s in xs` with `xs: &[T]` | `pick_victim` | the index loop over `0..xs.len()` with `let s: &T = &xs[i];`, a built-in projection whose bound is discharged | `T-Loop`, `T-Proj` |
| `xs[e]`, `&xs[a..b]` | indexing, slicing | the place `xs[e]` with `assert⟨idx⟩(e < xs.len())`; a slice adds `assert⟨slice⟩(a <= b && b <= xs.len())` | `T-Proj` |
| `x.m(ā)` | `w.row(r)`, `elem(j)`, `to_f32()` | method resolution by Rust's probe order (inherent impls, then traits in scope, with autoref and autoderef), then the UFCS call `T::m(adj(x), ā)` and monomorphisation | `T-Call`, J12 (§5.12) |
| `e1 op e2` on integers | `isum += …`, `now.0 - …` | `assert⟨ovf(op)⟩(no_overflow_op(e1, e2)); prim_op(e1, e2)`. Division and remainder also assert `e2 != 0` and, for signed types, `!(e1 == MIN && e2 == -1)`; shifts assert `e2 < bits` | `T-Assert`, `T-Prim` |
| `p op= e` on primitive operands | `isum += …` | `let t = ⟦e⟧; p = p op t`, with p's index expressions and their asserts evaluated after t, once. Rust evaluates the right operand first when both operands are primitive [inference: Rust Reference, compound assignment; not re-read here], so `a += { a = 5; 1 }` gives 6, not 2 (F-54) | `T-Assign` |
| `e1 op e2` on floats | `acc + …` | `prim_fop(e1, e2)`: IEEE binary32, round to nearest even, never contracted (FF-FMA) | `T-Prim` |
| `e as τ` | `a[g].q[j] as i32`, `isum as f32` | `prim_cast⟨τ_e, τ⟩(e)` with Rust's meaning: sign extension, truncation, saturating float-to-int with NaN to 0, round-to-nearest-even int-to-float | `T-Prim` |
| `x.to_f32()` on `f16` | `w[g].d.to_f32()` | `prim_cvt_f16_f32(x)`, exact | `T-Prim` |
| `canon::nan(e)` | `q4_row_dot` | `prim_canon_nan(e)` | `T-Prim` (sets `ν = canon`) |
| `requires φ` | `q4_row_dot`, `q4_matvec` | callers insert `assert⟨req(g)⟩(φ[ā/x̄])`; the callee assumes `φ` as a path fact | `T-Call`, §5.10 |
| `par for i in a..b { body }` | `q4_matvec` | `par i in ⟦a⟧..⟦b⟧ { ⟦body⟧ }` | `T-Par` |
| `p = e` | `y[r] = …` | the place assignment: the assigned value e first, then p's index expressions and their asserts, left to right (Rust evaluates the assigned value before the assignee [inference: Rust Reference, assignment expressions; not re-read here]), so `y[bad] = f()` with a trapping f reports f's trap (F-54) | `T-Assign` |
| `a \|\| b`, `a && b` | `s.pinned \|\| s.refs > 0` | `if a { true } else { b }`, `if a { b } else { false }` | `T-If` |
| `if c { e }`, `continue` | `pick_victim` | `if c { e } else { () }`; `continue` as in the loop row above | `T-If`, `T-Loop` |
| `s.f` with `s: &T` | `s.pinned`, `s.id` | the place `(*s).f`; reading a `Copy` field is `copy (*s).f` | `T-Copy` |
| `t.0` on a tuple struct | `now.0` | the place `t.0` | `T-Copy` |
| `T::f(ā)` (std constructor) | `Hint::none()`, `Hint::some(…)` | a std call | `T-Call` |
| tail expression `e` | `best`, `canon::nan(acc)` | `return e` | `T-Return` |
| `deterministic(by: E) { e }` | `acquire` | `det[E] { ⟦e⟧ }` | `T-Det` |
| `format S { … }` | `BlockQ4` | a struct and derived functions (§5.14) | `⊢_fmt` |
| `schedule … { … }` | `q4_matvec_avx512` | a schedule record, not an MCore term | `⊢_sch` |
| `spec … { claim … }` | `q4_matvec_claims` | claim records, not MCore terms | `⊢_spec` |
| `let x: Quantity<U, O> = e;` | `bw` | an ordinary `let` with ascription; `Quantity` is a std generic type | `T-Let` |
| `todo!("n")` | `score` | `trap(hole("n"))`, typed at the expected type | `T-Hole` |
| `e?` | derived (`expert_step`, `moe_ffn`) | `match ⟦e⟧ { Ok(v) => v, Err(r) => return Err(From::from(r)) }` | `T-Match` |
| closures `\|x\| e` | derived (`hottest`, `note_use`) | `clo_L` if a capture is by reference or `Local`, else `clo_E` (§5.7); captures follow Rust's inference of capture modes | `T-CloL`, `T-CloE` |

### 3.3 What elaboration may not do

Elaboration may not insert a copy that the source did not write above the hot-path budget (DR-027,
04 §6.5). It may not reorder floating-point operations, contract them, or change a reduction's order
(`canon.v1`). It may not introduce a `det` block, a capability, or a trap site that is not one of
§3.4's kinds. These are checked by the differential test and, for kernels, by T1 against KIR.

### 3.4 Trap sites

Every trap carries a site `σ = (kind, definition hash, anchor)`. The kinds are fixed, so `may_trap`
and the outcome of a trap are fully determined by the program and its input:

```text
kind ::= ovf(op) | idx | slice | div0 | divovf | shift | unwrap | expect | panic | assert
       | req(g) | ens(g) | inv(S) | range | hole(name) | unreachable | oom(A) | contract_ovf
       | fuel(port)                                                     (policy calls only)
```

`fuel(port)` is not a source trap. The port inserts it at every back edge of a policy body (03 §6.2),
and it can only end a policy call's fail domain.

**Arena exhaustion [prov, F-49].** `oom(A)` is a trap only for an arena whose capacity is a program
value: a bounded sub-arena split off by the program, such as the per-iteration sub-arenas of 01 §12.3.
Exhausting any other arena (`Global` under C-ALLOC, a reservation sized by `cap_nv`) depends on the
environment's capacity and, for `Sync` arenas, on interleaving, so it is the environment fault
`⇑F(oom(A))`, inside or outside a `par` body. Only then does "fully determined by the program and its
input" hold for every trap kind.

### 3.5 Elaboration of the policy and kernel kinds

`kernel` and `policy` change no evaluation rule. They select a well-formedness judgement (`⊢_k`,
`⊢_to`) and a grade context (§5.3). A `kernel fn` is graded `exact × cross_device` at its sinks. A
`policy fn` is normally called through a hint port, whose frame is its fail domain (§6.5). A direct
call from a test or from other code is an ordinary call, and a trap in it propagates like any other.

---

## 4. Judgement forms

| # | Form | Reading |
|---|---|---|
| J1 | `Δ ⊢ τ : K` | type τ has derived kind K (Copy, Linear, Local, Send, Sync) |
| J2 | `Δ ⊢ τ wf` | τ is well formed: no `Local` field, no `Local` instantiation of a user generic, no `dyn`, no lifetime |
| J3 | `⊢_pkg ε ok` | row ε is admissible under the package's grants |
| J4 | `ctx(g) ∈ {exact, timing_only, default}` | the grade context of definition g, computed from its sinks (01 §2.2) |
| J5 | `Δ;Γ ⊢ p : τ @ γ ⇐ m` | place p has type τ and grade γ and may be accessed in mode m under the live loans of Γ |
| J6 | `Δ;Γ;Σ;pc ⊢ e : τ @ γ ! ε ⊣ Γ'` | under authority Σ and control grade pc, e has type τ, yields a value of grade γ, exercises the labels ε ⊆ Σ, and leaves context Γ' |
| J7 | `Φ ⊢_T2 φ` | T2 proves obligation φ from path facts Φ |
| J8 | `⊢ D : sig` | item D is well formed with signature sig (§2.5) |
| J9 | `⊢_k g` | g is a well-formed kernel |
| J10 | `kcall(h)` | non-kernel h may be called from exact context |
| J11 | `⊢_to P` | P satisfies `timing_only` confinement |
| J12 | `Δ ⊢ τ : Tr ⇝ i` and `⊢_impl i` | trait resolution to impl i, and impl conformance |
| J13 | `⊢_fmt F ⇝ D̄` | format F elaborates to the items D̄ |
| J14 | `⊢_sch N for g on t` | schedule N is well formed for meaning g and target t (completeness side only) |
| J15 | `⊢_spec P for g` | spec item P is well formed |
| J16 | `⊢_store C` | store item C and its ports are well formed (M4; sketch) |
| J17 | `Ψ ⊢ C` | runtime configuration C is well typed under heap typing Ψ |
| J18 | `C ─[c]→_{e,T} C'` | one step under scheduler choice c, environment e, target T |

The context of J6 is `Γ = (V, Λ, Φ, ω, ρ, J, X)`:

- `V : x ↦ (τ, γ, st, μ, L)` with ownership state `st ∈ {own, moved, uninit}`, mutability `μ`, and
  the set `L` of loans the value of x carries (F-39). For a variable of reference type, γ is the
  grade of what is read through it, including the grade of whatever chose the target (an index or a
  row number). A reference parameter j's referent contents carry the symbolic loan `ℓ_j*`: "whatever
  the caller lent".
- `Λ` is the set of live loans `λ = (q, m)` with target place q and mode m. A loan is live iff some
  live value carries it in its `L` (§5.4).
- `Φ` is the set of path facts over SSA versions (§5.10).
- `ω` is the exit grade so far, and `ρ` the grade of values returned so far.
- `J : L ↦ γ` holds, for each open jump target L (each enclosing loop, and the function F), the
  join of the pc at every jump to L taken so far (F-30).
- `X` holds, for each `&mut` parameter, the join of its referent grade at every `return` so far (F-31).

The **effective pc** of an expression is `pc ⊔ ⨆_L Γ.J(L)`; every rule below that joins "pc" uses the
effective pc. J6 is flow-sensitive and threads Γ to Γ'. Rows and grades are separate outputs composed
by different operators, union and join (01 §7.4). J6 has two row outputs: the **charged row** ε,
which must be within the authority Σ, and the **exercised row** `ε^x ⊇ ε`, which adds the rows
`ε_κ` of `Local` closures the expression calls and the `nondet` that `T-Det` removes inside it
(F-36). Contexts that restrict what code may do at run time (`E-PAR-EFFECT`, (k1), (t1)) check
`ε^x`; the capability check checks ε. Where a rule below shows one row, `ε^x` is the union of the
premises' exercised rows plus the extra labels the rule names.

---

## 5. Static semantics

### 5.0 The class function

Every construct has a class that depends on the grade context of the definition it appears in:
`cls(construct, ctx) ∈ {C, Dc(code), D}`. The rules below consult it wherever a false-friend row
applies (`T-Prim`, `T-Call`, `⊢_k`). For example, `cls(float Iterator::sum, default) = C`,
`cls(float Iterator::sum, exact) = Dc(E-FF-SUM)` and `cls(float max_by, timing_only) = C`
(01 §2.2, §2.5). FF-SUM's row names float `.sum()`, `.product()` and `fold`, so
`cls(float product, exact) = cls(fold with a float accumulator, exact) = Dc(E-FF-SUM)` as well (F-59).
§5.16 lists the codes.

### 5.1 Kinds and well-formedness

```text
 ───────────────────────────────── K-Scalar      ───────────────────────────────────── K-Ref
 Δ ⊢ ι : Copy, Send, Sync                         Δ ⊢ &τ : Local, Copy;  &τ : Send ⟺ τ : Sync
                                                  Δ ⊢ &mut τ : Local;    &mut τ : Send ⟺ τ : Send

 S is a linear struct, or a field or variant-field type of S⟨τ̄⟩ is Linear,
   or S is a std generic (Option, Result, tuples, arrays, Vec, Frozen) and some τ_k is Linear
 ───────────────────────────────────────────── K-Lin           some component of τ is Local, or τ = clo_L⟨κ⟩(…)
 Δ ⊢ S⟨τ̄⟩ : Linear                                              ───────────────────────────────────────── K-Local
                                                                 Δ ⊢ τ : Local
 the closure at κ captures a Linear value by move
 ───────────────────────────────────────────── K-LinClo  (F-41)
 Δ ⊢ clo_L⟨κ⟩(…), clo_E⟨κ⟩(…) : Linear;  fn(…) ▷ Θ coerced from it carries [lin]
```

A Linear closure implements only `FnOnce`: calling it consumes it, and it must be called or moved on
every normal path (`T-Lin`). Abandoning it abandons its captured Linear values in reverse capture
order; abandoning a std container abandons its Linear elements in ascending index order [prov].

- **Copy** comes only from the std derive on types whose components are all Copy. Linear and Copy
  together is `E-LINEAR-COPY`.
- **Send and Sync** are structural with Rust's rules. Only `std_platform` asserts them by hand (01 §5.7).
- **Capability types** (`Root`, `Fs`, `File<M>`, `BlobFile`, `Spawner`, `Clock`, `MemCap`) are neither
  Copy nor Linear: they are affine (move-only, droppable), implement no `Clone`, `Default`, `From` or
  other constructor trait, and are shared by `&Cap` or weakened by attenuation methods [prov]. This
  keeps Theorem 2(a)'s provenance a tree.
- **`Frozen<T>`** is Linear iff T is Linear [prov, F-24]. Releasing the last reference to a
  `Frozen<SlabBuf>` must hand the buffer back to its arena through audited code, never drop it.
- **`Mutex<T>`** requires `T : ¬Local` and is `Sync` iff `T : Send`.
- **Std containers** `Option`, `Result`, tuples and arrays are `?Local` (01 §5.4). Whether `Vec` and
  the iterator adapters over owned collections are `?Local` is OP-3; this note assumes they are [prov].
- **`¬Linear` by default [prov, F-41].** Every type parameter of a user struct, enum, impl or
  function carries an implicit `¬Linear` bound, as it carries `¬Local`, because a generic body is
  checked once with its parameters non-Linear and may drop them. Only std signatures may write
  `?Linear`: `Option`, `Result`, tuples, arrays, `Vec::push`/`pop`, `mem::swap`, `mem::replace`.
  `drop`, `mem::forget`, iterator adapters, and every container method that discards elements
  (`clear`, `truncate`, `retain`, `dedup`, `drain`) keep `¬Linear`.
  Instantiating a `¬Linear` parameter at a Linear type is `E-LINEAR-INSTANTIATE`, so
  `drop(lease)` and a user `fn sink<T>(_x: T) {}` called with a lease are rejected. How an emptied
  Linear container is finally consumed (for instance a std method that asserts emptiness) is OP-20.

Well-formedness (J2), each with its code:

```text
 struct or enum S { f̄: τ̄ } ok only if ∀i. Δ ⊬ τ_i : Local                    E-REF-FIELD     (FF-REF)
 S⟨σ̄⟩ or g::⟨σ̄⟩, S and g user-declared, ok only if ∀k. Δ ⊬ σ_k : Local      E-LOCAL-INSTANTIATE
   except the closure-parameter exception (§5.7)
 a type argument σ_k : Linear at a parameter bounded ¬Linear                  E-LINEAR-INSTANTIATE [prov]
 a lifetime 'a anywhere                                                       E-LIFETIME [prov]  (FF-REF)
 dyn Tr, Box<dyn …>                                                           E-DYN           (FF-DYN)
 Cell, RefCell, Rc, static mut, unscoped thread::spawn                        E-FF-CELL       (FF-CELL)
 a static with interior mutability (static Mutex, OnceLock, lazy_static!)     E-GLOBAL-STATE [prov]  (01 §6.2)
 a user impl Drop                                                             E-DROP-IMPL [prov, F-17]
```

### 5.2 Rows

```text
 ⊢_pkg ε ok  iff   unsafe  ∈ ε ⇒ the package is in grants.unsafe                  else E-GRANT-UNSAFE
                   foreign ∈ ε ⇒ the package is in grants.foreign                 else E-GRANT-FOREIGN
                   fp_env  ∈ ε ⇒ the module is std_platform's audited runtime      else E-FP-ENV
                   lossy   ∈ ε ⇒ a lossy producer exists (reserved: always rejected in v0)
```

- **Declared rows.** A `pub fn`, a trait method, and any function with a `uses` clause has a declared
  row. An absent clause on a `pub fn` or trait method declares `∅` (F-22).
- **Inferred rows.** Other functions get the least solution of `ε(g) = ∪ {labels of g's primitives
  and callees}` over the call graph, strongly connected components solved together. The lattice is
  finite, so this terminates.
- **Check.** The body's labels must be a subset of the declared row (`E-ROW-UNDECLARED`). Declared
  rows may over-approximate. For a `pub fn` the fix that inserts a label changes the public signature,
  so 05 §5 classes it `InterfaceChanging`; 01 §6.3 calls it MachineApplicable (§14 P-12).
- **Capabilities.** Each label in `ε(g)` is an implicit parameter `κ_ℓ`. A call passes the caller's
  `κ_ℓ`, so a call is well typed only if `ε_g ⊆ Σ` (`T-Call`).

### 5.3 Grades

**Context.** `ctx(g) = exact` if g is a `kernel fn`, carries `#[grade(exact, _)]`, or is called
transitively by a definition whose context is exact. `ctx(g) = timing_only` if g is a `policy fn` or
every caller of g has context `timing_only`. Otherwise `ctx(g) = default`. Exact wins over
`timing_only` when a helper has callers of both kinds. Logits-path identification for non-kernel code
(DR-013) needs `export abi` and is M1; it is outside the X1 subset.

**Taint, fidelity, NaN rule and observers.**

```text
 taint(ℓ̄) = (exact, ⟨sd, cd⟩, ∅, canon)           if nondet ∈ ℓ̄
          ⊔ (exact, ⟨cd, dev(platform)⟩, ∅, canon) if nondet(platform) ∈ ℓ̄
          = ⊥                                      otherwise
            (time primitives, reads of mutable files, and load, store and read-modify-write
             operations on user-visible std atomics carry nondet: 01 §6.1, 01 §14 R6, F-56)

 fid(prim) = exact for every primitive producible in v0: IEEE basic operations, casts, cr::*,
             canon_v1::*, canon::*;  approx(p) only for primitives that require lossy (reserved)

 nanrule(prim, ν̄) = canon   for canon::nan; integer-to-float casts; float literals; f32::NAN once pinned (below);
                             f32::max and f32::min under the pinned FF-NANMAX choice (the result is a
                             non-NaN operand or the canonical NaN); any result T2 proves is not NaN
                  = ⨆ν̄     for copy, move, and selection by if or match
                  = raw     for every other float-producing primitive, including + - * / % sqrt
                             mul_add neg abs; cr::*; canon_v1::*; canon::sum16, dot16, sum_seq;
                             f16 and bf16 widening; `as` between f32 and f64 in either direction;
                             from_bits; copysign; floor, ceil, round, round_ties_even, trunc, fract,
                             recip; f64::max and f64::min; clamp                              (F-51)

 obs(prim, ν̄) = (exact, ⟨cd, dev(platform)⟩, ∅, canon)  if prim ∈ Observers and some argument is raw
              = ⊥                                        otherwise
 Observers    = { to_bits, to_le_bytes, to_be_bytes, to_ne_bytes, is_sign_positive,
                  is_sign_negative, copysign with a raw sign source, total_cmp }        (F-13 adds total_cmp)
 Payload-blind (no taint): == != < <= > >= partial_cmp is_nan is_finite classify, and `as` to integers
```

`total_cmp` implements IEEE totalOrder, which orders NaNs by sign and payload [inference: from the
documented totalOrder semantics, not re-read here], so it observes exactly what 01 §13.6 says is not
portable. An `abs` of a canonical NaN stays canonical, but `nanrule` marks every arithmetic result
raw because x86's default NaN differs from arm64's [inference: x86 SSE's "QNaN floating-point
indefinite" has the sign bit set; not re-verified here].

`nanrule` is total: a float-producing primitive not listed as canon is raw (F-51). Two entries of the
first draft were wrong. `clamp` returns `self` when `self` is NaN [inference: Rust's documented
`f32::clamp`, not re-read here], so its NaN result keeps the input's payload; FF-NANMAX pins only
`f32::max` and `f32::min` (01 §2.5). The f64 forms and `clamp` would become canon only by an amendment
to FF-NANMAX (§14 P-20). Restating conformance (§6.1) also exposes one entry that needs a pin:
`f32::NAN` is canon only if the edition's Surface Map fixes its bits to `0x7fc00000`, because Rust
does not promise a bit pattern for it [inference: from Rust's documentation of `f32::NAN`, not
re-read here]; E1 allows pinning such an open choice (01 §2.1). Until the Surface Map does, a checker
should treat `f32::NAN` as raw.

**Formatting addresses [prov, F-56].** The `{:p}` format specifier prints an address, which 01 §6.1
says safe code cannot observe. It is Dc everywhere (`E-FF-ADDR`).

**Fixed shared-state grade.** Every read of the contents of a `std_platform` shared-mutable type
(`Mutex<T>`, state guarded by a `Condvar`) has the grade `γ_sh = (exact, ⟨sd, cd⟩, ∅, raw)` (01 §7.2).
Inside a `det` block the read still has `γ_sh`; only the block's result is recomputed (§5.11).
`with_lock` declares its closure parameter at `γ_sh`, and its result is the closure's result
transfer applied to `γ_sh` (§5.7), so a value read out of a `Mutex` is never `cross_device`.

**Transfers.** Each function has the transfers `Θ_g` of §2.5, read off its body checked with symbolic
parameter grades (§5.15). Because the lattice is finite and the checker joins only, this is a
dependency analysis: `D` is the set of parameters the output depends on by data or control flow, and
`O ⊆ D` the parameters whose raw float content reaches an observer.

**Sinks.**

| Sink | Requirement |
|---|---|
| `kernel fn` outputs: the result and every `&mut` parameter's referent | `(exact, cross_device)`, and `ν = canon` for float content |
| `#[grade(f, d)]` outputs | `(f, d)`, and `ν = canon` if `d = cross_device` |
| `export abi` outputs declared exact (M1) | as for kernels |
| Claim slots and Forge slots | the grade the slot states (03 §3.5) |

A sink is checked on its final contents at every normal exit: the returned value, and each `&mut`
parameter's referent as the body leaves it, at its end and at every `return` (the exit context `X`,
F-31). It fails with `E-GRADE` (fidelity or scope) or
`E-NAN-RAW-SINK` (01 §13.6). The exit grade
`ω_g` must also meet the scope requirement when the output's required scope is `cross_device`,
because Theorem 4's outcome grade includes the pc of every reachable return, trap and early exit.

### 5.4 Places, loans and the second-class discipline

```text
 V(x) = (τ, γ, own, _)                  Γ ⊢ p : S⟨…⟩ @ γ    f : τ_f in S
 ───────────────────── P-Var            ───────────────────────────── P-Field
 Γ ⊢ x : τ @ γ                          Γ ⊢ p.f : τ_f @ γ

 Γ ⊢ p : &τ @ γ  or  &mut τ @ γ          Γ ⊢ p : [τ; n] or [τ] @ γ    Γ;Σ;pc ⊢ e : usize @ γ_i ! ε ⊣ Γ'
 ───────────────────── P-Deref          ─────────────────────────────────────────────── P-Index
 Γ ⊢ *p : τ @ γ                          Γ' ⊢ p[e] : τ @ γ ⊔ γ_i     with assert⟨idx⟩(e < len(p))
```

Access modes:

- **Read** (`copy p`, `&p`): no live mutable loan on a place overlapping p, other than the loan p is
  read through.
- **Write** (`p = e`, `&mut p`): no live loan of any mode on a place overlapping p; p is rooted in a
  `mut` local or reached through `&mut`.
- **Move** (`move p`): as for a write, and p is a local or a field path of an owned local, not behind
  a reference (`E-MOVE-BORROWED`).

Two places overlap unless they differ at a field or at indices that T2 proves distinct under Φ. A
conflict is `E-BORROW-CONFLICT` [prov; rustc's numeric codes are not reused, 05 §5].

**Loan sets [prov, F-39].** The first draft gave every loan a carrier and never said how carriers
move, so a reference stored through `&mut`, pushed into a `Vec` or swapped out of scope lived past
its target. Loans now travel with values:

```text
 T-Ref        &p, &mut p carry {λ}, λ = (p, m) fresh
 T-Copy/Move  the result carries L(root(p))            (conservative for fields of Local aggregates)
 T-Let        L(x) := L(value)
 T-Assign     L(p) := L(value) for a whole local, else L(t) ∪= L(value) for each t ∈ target*(p);
              for a place reached through a reference parameter j, see E-LOCAL-MUT-STORE below
 T-Call       result: λ_r for a projection (T-Proj); the union of the Local arguments' L for a std
              adapter (T-Ret (b)); ∅ for a non-Local result. A std function that stores an argument
              (Vec::push, Option::insert, Option::replace, mem::swap, mem::replace) adds the stored
              values' L to the receiving referent's L (both ways for swap)
 T-CallClo    see §5.7 (F-40)
```

A loan is live at a point iff some value live there carries it. This is Rust's non-lexical liveness,
restricted to one function body, because no signature mentions a lifetime. Three premises close the
body:

```text
 when the scope of local x ends, no live loan targets x or a sub-place of x       (E-BORROW-OUTLIVE [prov])
 a value stored into a Local-typed place reached through reference parameter j (by assignment, or
   through a storing std call) carries no loan other than ℓ_j*                   (E-LOCAL-MUT-STORE [prov])
 at the end of a body every live loan is the result's projection loan (T-Ret (a))
```

`E-LOCAL-MUT-STORE` rejects `fn set(o: &mut Option<&u32>, d: &u32) { *o = Some(d); }`, which rustc
also rejects, because elision gives the two references distinct lifetimes. It accepts reshuffling a
parameter's own contents (`*it = it.clone()`) and calling std's `next` on `&mut Iter<T>`. The
alternative, rejecting every user signature that takes `&mut τ` with `τ : Local`, is simpler but
rejects Rust that compiles (C-STORE in §12).

**Write targets [F-39].** For a write through a reference, `target*(p)` is the place whose grade
changes. If p is rooted in a reference parameter, it is that parameter's referent, as before. If p is
rooted in a local reference r (`let r = &mut y; *r = e`, or a projection result bound to a local), it
is `target*` of the place each loan `(q, mut) ∈ L(r)` targets, with p's path suffix appended: the
borrowed place, not r, whose own grade means "what is read through it". Every reference traversed
contributes its grade (the address grade, for example `γ_i` in `let r = &mut v[i]`).

**The consequence (01 §5.2).** Every loan created in a body ends before the body returns, except a
projection result, which is a loan on the caller's own place. Borrow checking is intraprocedural.

### 5.5 Expression rules

The rules of 01 §13.4 are kept, extended with the NaN bit, the exit grade and obligations. `Γ;Σ;pc ⊢`
abbreviates `Δ;Γ;Σ;pc ⊢` when Δ does not change.

```text
 ───────────────────────────────────────────── T-Lit
 Γ;Σ;pc ⊢ n : ι @ ⊥ ⊔ pc ! ∅ ⊣ Γ

 Γ ⊢ p : τ @ γ ⇐ read    Δ ⊢ τ : Copy               Γ ⊢ p : τ @ γ ⇐ move
 ───────────────────────────────────── T-Copy     ───────────────────────────────────────── T-Move
 Γ;Σ;pc ⊢ copy p : τ @ γ ⊔ pc ! ∅ ⊣ Γ               Γ;Σ;pc ⊢ move p : τ @ γ ⊔ pc ! ∅ ⊣ Γ[p ↦ moved]

 Γ ⊢ p : τ @ γ ⇐ read  (write for &mut)    λ = (p, ref) fresh  ((p, mut) for &mut)
 ───────────────────────────────────────────── T-Ref / T-RefMut
 Γ;Σ;pc ⊢ &p : &τ @ γ ⊔ pc ! ∅ ⊣ Γ + λ,  the result carrying L = {λ}       (&mut p : &mut τ)

 Γ;Σ;pc ⊢ e : τ @ γ ! ε ⊣ Γ1    Γ1 ⊢ p : τ @ γ_p ⇐ write    the value of e carries loans L_e
 γ_sel = ⨆ grades of the index expressions in p;  γ_addr = ⨆ grades of the references p traverses
 the old content of p is not an initialised Linear value                         (else E-LINEAR-DROP)
 p reached through reference parameter j and τ : Local ⇒ L_e ⊆ {ℓ_j*}           (else E-LOCAL-MUT-STORE)
 Γ2 = Γ1[t ⊔= γ ⊔ γ_sel ⊔ γ_addr ⊔ pc for each t ∈ target*(p)][L(t) ∪= L_e]   weak update
    = Γ1[p := γ ⊔ pc][L(p) := L_e]                                            strong, p a whole local
 ───────────────────────────────────────────── T-Assign
 Γ;Σ;pc ⊢ p = e : () @ pc ! ε ⊣ Γ2
   -- target*(p) (§5.4): the local p is rooted in; a reference parameter's referent; or, through a
   --   local reference or projection result, the place its loans target (F-39). Writes into a &mut
   --   parameter's referent are what θ_mut records

 Γ;Σ;pc ⊢ e1 : τ1 @ γ1 ! ε1 ⊣ Γ1    Γ1, x : (τ1, γ1, own, μ, L_e1);Σ;pc ⊢ e2 : τ @ γ ! ε2 ⊣ Γ2
 τ1 Linear ⇒ x is moved in Γ2 (else E-LINEAR-DROP)    x carries no loan that is live in Γ2
 no loan live in Γ2 targets x or a sub-place of x                               (else E-BORROW-OUTLIVE)
 ───────────────────────────────────────────── T-Let
 Γ;Σ;pc ⊢ let x: τ1 = e1; e2 : τ @ γ ! ε1 ∪ ε2 ⊣ Γ2 \ x

 Γ;Σ;pc ⊢ ē : τ̄ @ γ̄ ! ε̄ ⊣ Γ'    prim : τ̄ → τ with labels ℓ̄ ⊆ Σ    cls(prim, ctx) ≠ Dc
 ───────────────────────────────────────────── T-Prim
 Γ;Σ;pc ⊢ prim_ℓ̄(ē) : τ @ (⨆γ̄ ⊔ pc ⊔ taint(ℓ̄) ⊔ fid(prim) ⊔ obs(prim, ν̄))[ν := nanrule(prim, ν̄)]
                      ! ⋃ε̄ ∪ ℓ̄ ⊣ Γ'

 Γ;Σ;pc ⊢ e : bool @ γ ! ε ⊣ Γ'
 ───────────────────────────────────────────── T-Assert
 Γ;Σ;pc ⊢ assert⟨σ⟩(e) : () @ pc ! ε ⊣ Γ'[Φ += e]                if Γ'.Φ ⊢_T2 e  (σ discharged, erased)
 Γ;Σ;pc ⊢ assert⟨σ⟩(e) : () @ pc ! ε ⊣ Γ'[Φ += e][ω ⊔= pc ⊔ γ]   otherwise       (σ stays: may_trap)

 ───────────────────────────────────────────── T-Trap
 Γ;Σ;pc ⊢ trap(σ) : τ @ pc ! ∅ ⊣ Γ[ω ⊔= pc]          any τ, including !; sets may_trap

 ⟦todo!("n")⟧ = trap(hole("n")), typed by T-Trap at the expected type      T-Hole (01 §3.3)

 Γ;Σ;pc ⊢ c : bool @ γc ! εc ⊣ Γ1    Γ1;Σ;pc ⊔ γc ⊢ e_k : τ @ γ_k ! ε_k ⊣ Γ2,k   (k = 1, 2)
 Γ2 = Γ2,1 ⊔ Γ2,2: grades joined; a value moved on one path is moved after the join; a Linear value
      is consumed on both normal paths or on neither                              (else E-LINEAR-DROP)
 ───────────────────────────────────────────── T-If
 Γ;Σ;pc ⊢ if c {e1} else {e2} : τ @ γ1 ⊔ γ2 ⊔ γc ! εc ∪ ε1 ∪ ε2 ⊣ Γ2
   -- a branch of type ! (trap, return, break, continue) contributes nothing to the join of V and Λ,
   --   but its J, X, ω and ρ are joined: a jump in it raised J(L) at pc ⊔ γc (T-Jump), so the code
   --   after the if, up to the end of L, runs under γc (F-30)
   -- T-Match is T-If over arms: the scrutinee's grade joins pc in every arm; patterns bind by Rust's
   --   default binding modes; non-exhaustive matches are rejected as in Rust

 ───────────────────────────────────────────── T-Jump  (F-30)
 Γ;Σ;pc ⊢ break_L : ! ⊣ Γ[J(L) ⊔= pc]          and records Γ into Γ_brk(L)
 Γ;Σ;pc ⊢ continue_L : ! ⊣ Γ[J(L) ⊔= pc]       and records Γ into Γ_cont(L)
   -- pc is the effective pc, so a jump decided under h raises J(L) by h; return raises J(F) (T-Return)
   -- a trap raises nothing: it ends the fail domain, so no code of the domain runs after it, and
   --   T-Trap, T-Assert and θ_exit already put its pc into ω, which joins every outcome grade (§7.4)

 Γ_I ⊒ Γ[J(L) := ⊥]    Γ_I;Σ;pc ⊢ e : () @ _ ! ε ⊣ Γ_B    Γ_I ⊒ Γ_B ⊔ Γ_cont(L)
 (least such Γ_I; ownership states loop-invariant, else E-MOVE-LOOP)
 ───────────────────────────────────────────── T-Loop
 Γ;Σ;pc ⊢ loop_L {e} : () @ pc ! ε ⊣ Γ_brk(L) \ J(L)       Γ_brk(L) = ⨆ of the contexts at L's breaks
   -- J(L) is part of the fixpoint, so an iteration runs under the jump decisions of the iterations
   --   before it; for `for` loops the guard's break puts the bound's grade into every iteration
   -- termination-insensitive: code after the loop runs under pc, because every break of L reaches it;
   --   the places the loop writes carry J(L) through T-Assign's effective pc. J entries for targets
   --   outside the loop (an outer label, F) persist after it

 Γ;Σ;pc ⊢ e : τ_r @ γ ! ε ⊣ Γ'    the value of e carries at most the projection loan of T-Ret (a)
 every live Linear local is consumed                                              (else E-LINEAR-DROP)
 ───────────────────────────────────────────── T-Return
 Γ;Σ;pc ⊢ return e : ! @ pc ! ε ⊣ Γ'[ρ ⊔= γ ⊔ pc][ω ⊔= pc][J(F) ⊔= pc][X ⊔= Γ'|_out]
   -- Γ'|_out: the referent grades of the &mut parameters at this return; T-Fn reads θ_mut from the
   --   end of the body joined with X (F-31). Without X, `if h { *y = v; return }` left θ_mut,y = ⊥

 sig(g) = ∀Δ_g. (m̄ τ̄) → τ_r ! ε_g; Θ_g; mt_g; (φ_req, ψ_ens); kind_g
 Δ ⊢ θ : Δ_g  (bounds, including the implicit ¬Local and ¬Linear, hold)    ε_g ⊆ Σ    cls(g, ctx) ≠ Dc
 the caller is a kernel or a kcall helper ⇒ g is a kernel fn, kcall(g), a format accessor, or a
   primitive or std function on the closed list C-EXACT-STD (§12)                  (else E-KERNEL-CALL)
 Γ;Σ;pc ⊢ ā : θτ̄ @ γ̄ ! ε̄ ⊣ Γ'   (own: move or copy;  ref: &p or a shared reborrow;  mut: &mut p or a reborrow)
 Γ'.Φ ⊢_T2 φ_req[ā/x̄], or the caller is neither a kernel nor a kcall helper and assert⟨req(g)⟩
   stays (may_trap)                                                                (else E-KERNEL-OBLIGATION)
 Γ'' = Γ'[t ⊔= θ_mut,j(γ̄) ⊔ pc                  for each a_j a mutable borrow or reborrow, t ∈ target*(*a_j)]
         [q ⊔= wr_q ⊔ pc ⊔ θ_inv,j(γ̄)          for each a_j whose type mentions clo⟨κ⟩, and each q that κ
                                                captures by mut]
         [ω ⊔= pc ⊔ θ_exit(γ̄)                   if mt_g]
         [Φ := Φ with the facts on every place g may write killed (§5.10); Φ += ψ_ens[ā/x̄, result]]
         [L as in §5.4]
 ───────────────────────────────────────────── T-Call
 Γ;Σ;pc ⊢ g::⟨θ⟩(ā) : θτ_r @ θ_ret(γ̄) ⊔ pc ! ⋃ε̄ ∪ ε_g ⊣ Γ''
   -- ε_g ⊆ Σ is the capability check: κ_ℓ for each ℓ ∈ ε_g is passed implicitly
   -- target*(*a_j): for a reborrow &mut *r of a local reference r, the place r's loan targets (F-39)
   -- wr_q = Θ_κ.θ_mut,q at the parameter grades with which g runs the closure: those its signature
   --   declares (with_lock: γ_sh), or for a user generic g the grades at its invocation sites, read
   --   off g's per-κ check (§5.7, F-35)
   -- "mentions clo⟨κ⟩" includes &F, &mut F and std adapters that store the closure (Map<I, clo⟨κ⟩>),
   --   so the call that finally runs a lazily stored closure (next, a consuming method, for) applies
   --   κ's writes at its own pc. Applying them also at calls that do not run it is conservative
   -- θ_exit joins ω only if g may trap: a callee's early returns end in the caller's continuation,
   --   and their decisions are already in θ_ret and θ_mut through the callee's J(F), ρ and X
```

The jump grades make the first draft's claim true by rule rather than by assertion. For the
counterexample `let mut c = 0u32; for _i in 0..n_sd { c = c + 1; } return c;` with `n_sd` read under
`with_lock`, the guard's `break_L` puts `γ_sh` into `J(L)`, so `c = c + 1` is typed under it and c is
`schedule_dependent`, as it must be. Without `T-Jump` it stayed ⊥ (item N-11).

`T-Seq` is standard. A grade-weakening rule `T-Sub` applies only where a declared row or a declared
transfer over-approximates the derived one; derivations never weaken silently.

### 5.6 Projections

A function of kind `proj(x★, m★)` returns a `Local` type whose `Local` parts are references that
Rust's lifetime elision ties to the parameter `x★`: the receiver if there is one, otherwise the single
reference parameter (01 §5.3). The result may wrap them in std containers (`Option<&T>`,
`(&T, usize)`).

```text
 kind_g = proj(x★, m★)    a★ is &p★ or &mut p★, or a reborrow &*r or &mut *r of a reference r
 that carries loan λ0     (all premises of T-Call)
 ───────────────────────────────────────────── T-Proj
 Γ;Σ;pc ⊢ g(ā) : θτ_r @ θ_ret(γ̄) ⊔ pc ! … ⊣ Γ'' + λ_r
   λ_r = (p★, m★, result)  or, for a reborrow, a loan on the target of λ0, nested in λ0
   λ_r is live while the result, or any value it flows into, is live
   the result's referent grade is θ_ret(γ̄) ⊔ pc, which includes the grades of address arguments
     such as r in w.row(r)

 fn g(x̄: m̄ τ̄) -> τ with Δ ⊢ τ : Local is accepted only if                                     T-Ret
   (a) kind_g = proj(x★, m★), and the body's result carries only loans on the place x★ refers to,
       or on its sub-places, in a mode ⊑ m★; or
   (b) g is a std adapter whose declared result loan is the union of its Local arguments' loans.
   Otherwise E-REF-ESCAPE if the result is a reference, E-LOCAL-RETURN if it is another Local type.
```

Built-in projections are indexing `p[e]`, slicing `&p[a..b]` and `&mut p[a..b]`, and field access
through a reference. **Footprints [prov, F-25, F-45].** A user projection may declare its footprint as
an `ensures` over the underlying buffer, for example
`ensures footprint(result) == self.blocks[r * bpr .. (r + 1) * bpr]`. `T-Par` uses declared footprints
to check disjointness through user projections. Without one, a `par` that writes through a user
projection is checked as if it wrote the whole receiver.

A footprint is a ghost predicate, so it cannot be checked at run time, and a wrong one would turn a
`par` into a data race in safe code. Every footprint clause is therefore discharged **statically**
by T2 at the projection's definition, whatever kind of function the projection is: the body's result
loan must target exactly the declared sub-place (`E-FOOTPRINT` [prov]). Built-in slicing makes this a
range equality. A footprinted projection's body may not write through its receiver, and may read
only the receiver's fields outside every footprint (for `Matrix`, `rows` and `blocks_per_row`); both
are checked at its definition. A call to it then borrows only the footprint, not the whole receiver:
`λ_r` targets `footprint(result)`, and the call's `&mut` access to the receiver is a write access to
that sub-place plus a read of those fields (F-45). This is what lets loans on different rows of one
`Matrix` coexist.

### 5.7 Closures and the non-escaping kind

```text
 some capture is by ref or by mut, or a captured value is Local      κ fresh
 Γ_c, x̄ : (τ̄, ᾱ);Σ;⊥ ⊢ e : τ @ γ ! ε_e ⊣ Γ_e   over parameter symbols ᾱ, captures at their grades in Γ
 ε_e ⊆ Σ    the result discipline below holds                                      (else E-REF-ESCAPE)
 Θ_κ = (θ_ret from γ ⊔ Γ_e.ρ, θ_mut,q from Γ_e's final grade of each by-mut capture q, θ_exit from Γ_e.ω,
        mt_κ, ε_κ = ε_e^x), each read off over ᾱ as in T-Fn
 ───────────────────────────────────────────── T-CloL
 Γ;Σ;pc ⊢ clo_L⟨κ⟩[c̄] |x̄| e : clo_L⟨κ⟩(τ̄) → τ @ pc ! ε_e ⊣ Γ + loans of the by-ref and by-mut captures
   -- the row is charged here, once (Effekt-style); calls add ε_κ to the exercised row only (F-36)
   -- by-ref captures cannot change while the closure holds its loan on them, so their grades are
   --   constants of Θ_κ; by-mut captures change only through the closure, which θ_mut,q records

 every capture is by move and no captured value is Local
 Γ_c, x̄ : (τ̄, ᾱ);ε_e;⊥ ⊢ e : τ @ γ ! ε_e ⊣ Γ_e     ε_e ⊆ Σ      (capability capture, F-4)
 the result discipline below holds; Θ_κ as for T-CloL                             (else E-REF-ESCAPE)
 ───────────────────────────────────────────── T-CloE
 Γ;Σ;pc ⊢ clo_E⟨κ⟩[c̄] |x̄| e : clo_E⟨κ⟩(τ̄) → τ ! ε_e @ pc ⊔ ⨆γ(c̄) ! ε_e ⊣ Γ[c̄ moved]
   -- the creator is charged ε_e, so a function that hands an io closure to spawn shows io in its row;
   --   the type keeps ε_e for whoever runs the closure; it is Linear if a moved capture is (K-LinClo)

 f : clo⟨κ⟩ (or fn(τ̄) → τ ! ε_f ▷ Θ)    Γ;Σ;pc ⊢ ā : τ̄ @ γ̄ ! ε̄ ⊣ Γ'    clo_E or fn: ε_f ⊆ Σ
 ───────────────────────────────────────────── T-CallClo  (F-35, F-40)
 Γ;Σ;pc ⊢ f(ā) : τ @ Θ.θ_ret(γ̄) ⊔ γ(f) ⊔ pc ! ⋃ε̄ (∪ ε_f for clo_E and fn)
           ⊣ Γ'[q ⊔= Θ.θ_mut,q(γ̄) ⊔ γ(f) ⊔ pc for each by-mut capture q][ω ⊔= pc ⊔ Θ.θ_exit(γ̄) if mt]
   ε^x ∪= ε_κ;  a Linear f is consumed;  if τ is Local, the result carries the loans of κ's by-ref
   captures and of the Local arguments
   -- inside a generic body, f : F with F bounded by Fn*: the call is typed per κ at monomorphisation
   --   (below); the captures q are not in scope there, so the call instead raises θ_inv,j by pc and
   --   the caller applies κ's writes through T-Call's wr_q ⊔ θ_inv,j
```

**Result discipline for closures [F-40].** `T-Ret` (a) applies to closures too. When a closure is
instantiated at a type parameter whose `Fn*` bound declares a `Local` result (`F: Fn(&[f32]) ->
&[f32]`), its body's result may carry only loans on the parameter that elision selects in that
signature (or on its sub-places); a loan on a capture is `E-REF-ESCAPE`, as rustc rejects the
higher-ranked signature. When the creating frame calls a `Local` closure directly, `T-CallClo` gives
the result the loans of the closure's by-ref captures, so `let r = { let c = || &x[0]; c() };` keeps
x borrowed while r is live, and a later `x.push(2)` is `E-BORROW-CONFLICT`.

**Closure summaries and monomorphisation [prov, F-35].** A closure's grade behaviour is its summary
`Θ_κ`, not its value grade. Without it, `fn apply<F: Fn() -> u64>(f: F) -> u64 { f() }` returned ⊥
for a closure that reads a clock, and `fn maybe<F: FnMut()>(h: bool, f: &mut F) { if h { f() } }`
left the closure's by-mut captures untouched by h. Three rules close this:

1. A generic body with a type parameter bounded by `Fn`, `FnMut` or `FnOnce` is re-typed per closure
   site κ at monomorphisation, for grades, loans, the exercised row and the side judgements, as B
   already is (§5.12). Its signature then has, per instantiation, a result transfer that includes
   `Θ_κ.θ_ret` and an invocation transfer `θ_inv,j` per closure parameter.
2. Std higher-order functions declare their transfers with the closure's summary as a symbol:
   `with_lock`: `θ_ret = Θ_f.θ_ret(γ_sh) ⊔ γ(f)`, `θ_inv,f = ⊥` (it runs f once, unconditionally);
   `Option::map`: `θ_ret = α_self ⊔ Θ_f.θ_ret(α_self)`; `max_by_key`, `min_by_key`, `max_by`,
   `min_by`: `θ_ret = α_self ⊔ Θ_f.θ_ret(α_item)`; `sort_by`, `sort_by_key`: `θ_mut,self = α_self ⊔
   Θ_f.θ_ret(α_item, α_item)`; lazy adapters (`map`, `filter`, `inspect`) store κ in their type, and
   `next` on them has `θ_ret = α_self ⊔ Θ_f.θ_ret(α_item)` and `θ_inv = α_self`.
3. The exercised row of a call to a closure parameter is `ε_κ`, so a restriction (`E-PAR-EFFECT`,
   (k1), (t1)) sees what the closure does wherever it runs.

The cost is a re-check per closure site for generic helpers, which OP-19 asks X1 to measure.

**Closure-parameter exception (01 §5.4).** A function's type parameter F bounded by `Fn`, `FnMut` or
`FnOnce` (or `impl Fn…` in argument position) that occurs in exactly one parameter type, as `F`, `&F`
or `&mut F`, and not in the return type (directly or through an associated type), may be instantiated
at `clo_L`. The body is then checked with `Δ ⊢ F : Local`.

**Rejections.**

| Code | When |
|---|---|
| `E-LOCAL-RETURN` | a function returns a `Local` adapter or closure outside T-Ret (FF-LOCAL) |
| `E-REF-FIELD` | a struct or enum field has a `Local` type (FF-REF, FF-LOCAL) |
| `E-LOCAL-INSTANTIATE` | a user generic is instantiated at a `Local` type outside the exception |
| `E-REF-ESCAPE` | a reference is returned outside T-Ret, or a std generic parameter with the implicit `¬Local` bound (such as `with_lock`'s result type R) is instantiated at a reference type (F-28), or a closure's result carries a loan that its bound's elision does not allow (F-40) |

`heat_view` (01 §5.8) is the F-28 case. Its own signature, `fn heat_view(st: &Mutex<StoreState>) ->
&[u32]`, is a valid projection by elision. The rejection comes from instantiating `with_lock`'s `R` at
`&[u32]`.

### 5.8 Linear resources

```text
 Δ ⊢ τ : Linear and x : τ is owned in Γ
 ⟹ on every non-trapping path from x's creation to the end of its scope, x is consumed exactly once:
    moved into a call, returned, destructured, or moved into a place that is itself consumed.        T-Lin
```

- An implicit drop is `E-LINEAR-DROP`, including assignment over an initialised Linear place.
- "Moved into a call" counts as consumption only because the callee's own `T-Lin` then applies to
  the parameter. A generic callee is checked with its type parameters `¬Linear` and may drop them, so
  instantiating one at a Linear type is `E-LINEAR-INSTANTIATE` (§5.1, F-41). Moving a Linear value
  into a closure capture makes the closure Linear (K-LinClo), so the closure must be called or moved.
- A partial move out of a Linear struct is allowed only by destructuring the whole value
  (`E-LINEAR-PARTIAL` [prov]).
- Trap paths are exempt. §6.3 abandons live Linear values in reverse order of creation (01 §12.4),
  including Linear by-value parameters and, by E6, every Linear temporary (F-42).

### 5.9 `par`, and covering writes

```text
 Γ;Σ;pc ⊢ a : usize @ γa ! εa ⊣ Γa    Γa;Σ;pc ⊢ b : usize @ γb ! εb ⊣ Γ0    pc' = pc ⊔ γa ⊔ γb
 the body e is checked with i : (usize, pc', own, imm), under pc'
 W = the places e writes, including the &mut accesses of §5.4 and of calls. Each w ∈ W is
     p[π(i)] with π injective on [a, b) (an affine check, or T2);
     or a projection &mut p[lo(i)..hi(i)] with lo(i) ≤ hi(i) ≤ lo(i+1) on [a, b), by T2;
     or reached through a user projection whose declared footprint has one of these forms (§5.6);
     or, by Proj-Split below, footprint(proj)[π(i)]                                  (E-PAR-DISJOINT)
 every read in e of a place in W is at the iteration's own index π(i) or within [lo(i), hi(i));
     captured &mut places are split per iteration                                     (E-PAR-RACE)
 shared captures are Sync; written or moved element types are Send                   (E-PAR-SEND)
 no break targets the par                                                             (E-PAR-BREAK)
 ε_e^x ⊆ {blob} ∪ {alloc(A) | A : Sync}: the exercised row, so the rows of Local closures the body
     calls and nondet removed by a det block in the body count (F-36)               (E-PAR-EFFECT)
 γ_unspec = (exact, ⟨sd, cd⟩, ∅, raw)
 X' = X_e ⊔ X_e[w ⊔= γ_unspec for w ∈ W]   if e may return (contains return or ?), else X_e   (F-38)
 ───────────────────────────────────────────── T-Par
 Γ;Σ;pc ⊢ par i in a..b {e} : () @ pc' ! εa ∪ εb ∪ ε_e
        ⊣ Γ0[w ⊔= γ_w ⊔ pc' for w ∈ W][ω ⊔= pc' ⊔ ω_e][ρ ⊔= ρ_e][J(F) ⊔= J_e(F)][X := X']
   -- no schedule taint is added on the normal continuation: under the write premise and the read
   --   premise together, the iteration order is unobservable (01 §13.4), and after a normal join
   --   every iteration completed, so W equals the serial run's (Lemma B)
   -- after an early Ret the join returns from the enclosing function with W holding contents that
   --   depend on which iterations above the winner ran; X' records that at the function's exit, so a
   --   caller that ignores the Err and reads W sees schedule_dependent (item N-15)
   -- early exits (return, ?, trap) in the body join the exit grade under pc'
   -- a cross-iteration float accumulator is a write of a place not indexed by i, so E-PAR-DISJOINT
   --   rejects it (02 §3 rule 3)
```

**`Proj-Split` [prov, F-45].** Rust elaborates `y[t][r] = v` to
`*IndexMut::index_mut(IndexMut::index_mut(&mut *y, t), r) = v`, so an inner `par r` takes a `&mut`
on row t in every iteration, which is not a place of the forms above. The rule: inside a `par` over
i, a call to a projection with a declared footprint whose result is used, within one iteration, only
as the base of a write or read at index `π(i)` contributes only `footprint(proj)[π(i)]` to W and to the
reads, and its loan is split per iteration like a captured `&mut` place. Without the rule, D-D11's
inner `par` is `E-PAR-DISJOINT`; the alternative is to ask 02's owner to hoist `let yt = &mut y[t];`
above the inner `par` (§14 P-19).

**`T-Cover` (F-1, F-37).** A loop L, either `for i in 0..n {…}` or `par i in 0..n {…}`, *covers* the
place p with the expression `e_w` if its surface body (not the elaborated header of §3.2) satisfies:

0. the body contains no `break`, `continue`, `return` or `?`, targeting L or any enclosing construct,
   anywhere, before or after the write. Traps are allowed: a trap ends the enclosing fail domain, so
   no normal exit follows it, and sinks and transfers concern normal exits only (§5.3);
1. on every path through one iteration that does not trap, the body writes `p[i] = e_w` exactly
   once, and no `if` or `match` arm precedes the write on any path;
2. `Γ.Φ ⊢_T2 n == p.len()`; and
3. the body makes no other write to p: no other element, no whole-p or length-changing write, and no
   `&mut` of p or of a sub-place passed to a call. Writes are identified by place after reborrows and
   local references are resolved (`target*`, §5.4).

After a covering loop, the element grade of p is a strong update, `p[*] := γ(e_w) ⊔ pc'`, with the
NaN bit included, instead of `T-Assign`'s weak join; `pc'` includes `J(L)`, so the bound's grade.
Nested covers compose for two-dimensional projections such as `y[t][r]` when the row projection
declares its footprint. The first draft's condition 1 forbade exits only before the write, so
`for i in 0..n { y[i] = canon::nan(x[i]); if x[i] > 0.0 { break; } }` passed and marked y canonical
while its tail kept the caller's raw NaNs (item N-14).

Without `T-Cover`, the canonical `q4_matvec` fails its sink check. The caller's `y` is `raw`, and the
weak join `raw ⊔ canon` is `raw` (derivation D-C2 in the appendix). A sink check that looks only at
the values written would let the kernel pass, but its transfer would still depend on the old `y`, so
the failure would reappear at the next exact sink. The rule is deliberately narrow: an index analysis
that proves arbitrary loops exhaustive is a tombstone (§15), not a v0 rule. Sinks are checked on final
contents in this note.

### 5.10 Traps, obligations, kernels and contracts

**Path facts.** `Φ` at a program point holds: the function's `requires`; the `#[range]` facts of
parameters and of fields read; the invariants of struct values read; the `ensures` of every call
already made; `a ≤ i < b` for every enclosing loop over `a..b`; the conditions of enclosing branches;
and the conditions of asserts already passed.

**Facts are over SSA versions [F-44].** Every place name in Φ is a version. An assignment, a write
through `&mut` or a local reference, a `&mut` argument, and a call to a closure that captures by mut
create a fresh version of every place they may write (`target*`, `θ_mut`, `Θ_κ`), and the facts that
mention an old version are kept only about that old version. So in
`let mut j = j0; if j < y.len() { j = j + 1; y[j] = 0; }`, the fact is `j₀ < len(y)`, the index is
`j₁ = j₀ + 1`, and the bounds check stays (in a kernel, `E-KERNEL-OBLIGATION`, item N-22). The
derivations name versions where a fact crosses a write (`isum_k` in D-C2).

**Discharge.** `Φ ⊢_T2 φ` holds when T2 proves φ from Φ in quantifier-free bit-vector and
linear-integer arithmetic over the machine types (03 §6.5). Bounded quantifiers over constant ranges
are discharged by unrolling (01 §9.2). Loop invariants are not inferred (DR-012), so a loop body's
obligations that depend on earlier iterations are provable only for constant trip counts, by
unrolling. `q4_row_dot`'s overflow obligation is of this kind (derivation D-C2).

**Contract expressions [prov, F-14].** `requires`, `ensures`, `invariant` and `#[range]` are evaluated
with checked arithmetic. At run time an overflow inside a contract makes the check fail, so the
guarded trap fires at a `contract_ovf` site. In T2 a contract is read over the integers with an
explicit no-overflow conjunct.

**Where contracts are checked.**

| Contract | Asserted | Assumed |
|---|---|---|
| `requires` | at each call site | at callee entry |
| `ensures` | at each return (outside kernels: runtime; in kernels: proved) | at the call site after the call |
| `#[range]` on a parameter | at each call site | at callee entry |
| `#[range]` on a field | at construction, on every direct write, and when a `&mut` loan on the field or on a sub-place of it ends | on a read, unless the field has been written through a loan whose end has not yet been checked or a `&mut` loan on it is live |
| `invariant S` [prov] | at construction; at every **publication point** of an S value that has had a field write or a `&mut` loan on a sub-place since its last check in this frame: before it, or a reference to it or to a sub-place, is passed to a call, shared-reborrowed, moved or returned; when any `&mut` loan on it or on a sub-place of it ends; and at exit, for each `&mut` parameter whose referent contains an S | on a read of a value reached from a parameter, a call result, or a place with no write and no live `&mut` loan since its last check |
| footprint `ensures` of a projection | statically, by T2, at the projection's definition, in every kind of function (`E-FOOTPRINT`) | at every call |

Outside kernels these checks run at run time and are trap sites `inv(S)` and `range`; in kernels and
`kcall` helpers they are T2 obligations. The first draft re-checked an invariant only after by-value
field assignments and at the end of a loan on a whole S value, so `m.rows = m.rows + 1;
q4_matvec(&*m, a, y)` inside `impl Matrix`, or `m.blocks.truncate(0)` through a loan on the field,
handed a kernel a `Matrix` whose invariant was false while the kernel's slice bounds had been
discharged from it (items N-21, N-28; F-43). While a `par` is live, the per-iteration `&mut` loans
that `Proj-Split` or a footprint creates do not trigger the re-check; it runs once, at the join, so it
never reads places other iterations are writing.

**`may_trap`.** `may_trap(g)` is true iff, after T2 discharge, g's body still contains a reachable
assert or trap, or g calls some h with `may_trap(h)`. It is a least fixpoint over the call graph.

**Holes (F-23).** `todo!("n")` has the expected type of its context. If the binding it initialises
is never used, its type is the pinned edition's never-type fallback [inference: which type that is
for the pinned edition is not verified here]. Either way the item is accepted, and reaching the hole
traps at `hole("n")`.

**Kernels.**

```text
 ⊢_k g  iff
  (k1) row(g) = ∅ and the exercised row of g's body is ∅ (F-36)                         (E-KERNEL-ROW)
  (k2) may_trap(g) = false: every assert in g is discharged statically (DR-011)        (E-KERNEL-OBLIGATION)
  (k3) every callee is a kernel fn, a primitive or std function on the closed list C-EXACT-STD (§12),
       a format accessor, or a helper h with kcall(h)                                  (E-KERNEL-CALL)
  (k4) every output sink meets (exact, cross_device), ν = canon for floats, and ω_g is cross_device
                                                                                (E-GRADE, E-NAN-RAW-SINK)
  (k5) no construct whose class is Dc in exact context: FF-SUM (float sum, product and fold), FF-TIES,
       FF-EXP, FF-POWI, FF-F16, FF-CLOCK
  (k6) no det block, no Mutex access, no capability parameter (02 §2: no ambient authority)

 kcall(h)  iff  h is not a kernel, row(h) = ∅, may_trap(h) = false given its requires, and h's body
                satisfies (k3), (k5) and (k6)                                                  (F-27)
```

Std accessors such as `<[T]>::len` are `kcall`. So are `Matrix::rows`, `Matrix::blocks_per_row` and
`Matrix::row`, but `Matrix::row` only with the invariant `blocks.len() == rows * blocks_per_row`
(F-3): without it the slice bound `(r + 1) * bpr <= blocks.len()` is unprovable. The prelude declares
it ([derivations §P](core-calculus/derivations.md#p-the-canonical-prelude)).

### 5.11 The deterministic boundary

```text
 module(g) ∈ grants.declare_deterministic (exact module names, 01 §6.4 rule 3)           (E-DET-GRANT)
 g is not a policy fn and no policy fn reaches g, in the monomorphised call graph        (E-DET-POLICY)
 E is admitted and current, its kind is deterministic, and its claim is about this block (01 §13.4):
   E's subject is the block itself, named by its anchor, or the enclosing definition when the block
   is that definition's entire body; subjects are resolved to definition content hashes when E is
   admitted, and the enclosing definition's current hash must be among them      (E-DET-EVIDENCE, E-DET-STALE)
 τ contains no closure type and Δ ⊢ τ : ¬Local                                       (E-DET-RESULT [prov])
 Γ;Σ ∪ {nondet};pc ⊢ e : τ @ (f, ⟨d_s, d_p⟩, B, ν) ! ε ⊣ Γ'          the body, typed without any mask
 d_s^in = ⨆ { Γ(y).d_s | y free in e }   (for a reference y, its referent grade; for a closure, its
                                          captures)                                        (F-32)
 ───────────────────────────────────────────── T-Det
 Γ;Σ;pc ⊢ det[E] {e} : τ @ (f, ⟨d_s^in, d_p⟩ ⊔ pc.d, B ∪ {E} ∪ pc.B, ν) ! ε \ {nondet} ⊣ Γ'
   -- exercised row: ε^x keeps nondet (F-36)
```

- It removes only `nondet` from the charged row. Authority stays visible (DR-006). The exercised row
  keeps `nondet`, so a `det` block inside a `par` body is `E-PAR-EFFECT` (item N-34).
- It drops only the `nondet` contribution to the schedule component, by recomputing it from the
  block's free inputs: taint that the inputs carried in survives. The first draft's mask, `⟨cd, d_p⟩`
  whatever the inputs, laundered `let v = st.with_lock(|s| *s); deterministic(by: E) { v }` into
  `cross_device` (item N-12). `nondet(platform)` is neither removed nor masked.
- Fidelity is unchanged. E joins B, so every value-level claim downstream meets E's grade (03 §3.2):
  this is the sense in which the boundary "lowers grades by E". Input-universal claims are not capped
  by boundaries upstream of their inputs (01 §7.2).
- Only the result value is recomputed (F-19). The body is typed without a mask, so places written
  inside the block, and jumps out of it, keep their taint.
- **Evidence must be about the block (F-33).** 01 §13.4's premise is "its claim is deterministic(e)".
  The first draft also accepted "a definition whose closure contains it", and its prelude fixture had
  the glob subject `store::*`. Evidence that the enclosing subject's output is deterministic does not
  show that an inner block's result is (the subject may sort the block's output), and a glob lets any
  new function in the module borrow evidence that never exercised it (item N-33). At X1, fixtures and
  `declare_deterministic` grants are hash-pinned task inputs that the agent cannot edit (§12).
- **First-order results (F-34).** A closure created inside the block and returned from it would run
  its `nondet` code after the block, outside the extent E's evidence covers, and with no label
  (item N-32). The result type therefore contains no closure and is not `Local`. An escaping closure
  that stays inside the block keeps `nondet` in its type (F-26).

### 5.12 Static-dispatch traits

```text
 trait Tr⟨Δ⟩ { fn m(…) -> τ uses ε_m; … }           rows on trait methods are declared (absent = ∅)
 Θ̂_m(γ̄) = (γ⁰ = taint(ε_m), D = all parameters, n = raw for float results, O = all parameters)
                                                                     the row-derived bound (F-12, F-50)

 impl⟨Δ'⟩ Tr for τ { fn m … } is accepted if
   the method signatures match the trait's after substitution (Rust's rules);
   ε_impl(m) ⊆ ε_m                                                                   (E-IMPL-ROW [prov])
   Θ_impl(m) ⊑ Θ̂_m, ignoring B                                                     (E-IMPL-GRADE [prov])
   Rust's coherence and orphan rules hold                                           (E-COHERENCE)
 Δ ⊢ τ : Tr ⇝ i: the unique impl, by Rust's rules.
```

- **What the bound checks.** The first draft argued that `Θ_impl ⊑ Θ̂_m` holds automatically because
  every producible scope taint comes from a row label. That is false: the NaN observers add
  `⟨cd, dev(platform)⟩` with no label (§5.3, F-50). `Θ̂_m` therefore has every parameter in O, so an
  impl that observes a raw *argument* conforms, and a generic caller sees the observer taint whenever
  it passes a raw float. An impl that observes a raw value it computed itself, such as
  `impl Key for f32 { fn key(&self) -> u32 { (*self + 0.0).to_bits() } }`, has `dev(platform)` in its
  constant part γ⁰, exceeds the bound, and is `E-IMPL-GRADE` (item N-39); the fix canonicalises
  before observing. An impl that masks `nondet` with a `det` block has a smaller row and, by F-32, a
  result no higher than its inputs, which the bound allows.
- **B** is the exception: an impl with a `det[E]` block adds E to its result's B, which `Θ̂_m` cannot
  know. B matters only for value-level claims in the ledger, which are made about concrete,
  monomorphic definitions (03 §3.2), and typing never rejects on B. So B is computed after
  monomorphisation, and a generic body carries a placeholder for it that instantiation resolves.
- **Generic bodies** are checked once for grades and rows. A call `Tr::m` on a type parameter uses
  `ε_m` and `Θ̂_m`. Monomorphisation substitutes and needs no grade re-check, except that it resolves
  B, and that bodies generic over a closure type are re-typed per closure site (§5.7).
- **Side judgements on the monomorphised call graph [F-53].** `⊢_to` (t5)–(t9), `⊢_k` (k3)–(k6),
  `kcall` and `E-DET-POLICY` are facts about callee bodies. A policy generic over `T: Score` that calls
  `Score::score` cannot know whether the impl it will get contains a `det` block, a `Mutex` or a loop
  over a non-view slice. These judgements are therefore evaluated on the monomorphised call graph,
  after instantiation. The grade check stays modular (tombstone
  `generic_grades_after_monomorphisation`).
- **Kernels** and `kcall` helpers may call trait methods only on concrete types in v0, because
  `may_trap` and canonical results are not part of trait signatures [prov].
- **Operators.** On primitive types an operator elaborates to a primitive (§3.2); on user types to
  `Tr::m` (`Add::add` and so on). `Quantity`'s `Add` exists only for equal units and equal origins, so
  mixing them is "no impl", a type error: INV-HONEST as a type (01 §4).
- **Rejected** (DR-005): `dyn` (`E-DYN`), specialisation (`E-SPECIALIZE`), `async` (`E-ASYNC`), user
  macros (`E-MACRO`).

### 5.13 Policies and hint ports

```text
 ⊢_to P  iff
  (t1) row(P) = ∅ and P's exercised row is ∅: no io, time, alloc, fp_env, nondet (T0 re-checks on
       the binary)                                                                      (E-TO-ROW)
  (t2) the result type is Hint⟨T⟩                                                       (E-TO-RESULT)
  (t3) parameters are core-provided views: types the core marks #[view], Copy and payload-free,
       and slices of them                                                          (E-TO-PARAM [prov])
  (t4) state, if any, is one fixed-size block owned by the port and double-buffered (§6.5)
                                                                                   (E-TO-STATE [prov])
  (t5) loops only over core-provided slices or constant ranges; no recursion             (E-TO-LOOP, E-TO-RECURSION)
  (t6) no det block, no Mutex, no capability, no escaping closure                  (E-TO-AUTHORITY [prov])
  (t7) every callee satisfies ⊢_to apart from (t2) (a helper need not return a Hint), or is a
       stateless std function with row ∅ (Hint::none, Hint::some, <[T]>::len, integer and float
       primitives), in the monomorphised call graph (F-53)                           (E-TO-CALL [prov])
  (t8) may_trap(P) may be true: a trap ends the port call's fail domain (§6.3, §6.5)
  (t9) P's static maximum stack use S(P), over P and its callees, is computed from frame sizes;
       (t5) makes the call graph acyclic, so S(P) is finite. A port whose stack budget is below
       S(P) is E-TO-STACK [prov] (⊢_store; F-48)
```

- **Grade context `timing_only`.** FF-SUM and FF-TIES are C (01 §2.2). Every view value has the fixed
  shared grade `γ_sh`, because views are snapshots of shared mutable core state. Nothing is required
  of the result's grade: Theorem 3 is what makes the result harmless.
- **Static fuel.** (t5) gives a bound `fuel(P)`: the sum over back edges of the product of enclosing
  trip bounds, a polynomial in view lengths. If `fuel(P)` exceeds the port's declared fuel, every call
  would exhaust and fall back; `W-FUEL` warns [prov].
- **`⊢_store`** (M4, a sketch, outside X1). Each `hint port q: P fallback F validate V …` requires
  `⊢_to P`, a fallback F that is core code with row ∅ and `may_trap(F) = false` (premise F-tot of §8),
  a validator V with `may_trap(V) = false` (part of premise P-ind), a stack budget at least S(P)
  (premise S-tot, (t9)), and a certificate clause naming its evidence. `evolve slot` items (06 §2.1)
  are checked like ports: the slot's maximum row bounds every candidate's row, and the space names the
  side judgement (`⊢_to` for `timing_only`).
- **Hint values are graded `γ_sh` [prov, F-57].** A hint value the core receives from a port has the
  fixed shared grade, because the policy computed it from snapshots of shared state. A hint that flows
  into an exact sink is then `E-GRADE` unless it passes through a `det` boundary whose evidence is
  the store-core certificate. Theorem 3 does not need this, but it gives the certificate a type-level
  backstop that the checker enforces on every core edit.

### 5.14 Formats, schedules, specs and staging

**Formats.**

```text
 ⊢_fmt  format BlockQ4 { d: f16, q: nibbles<64, offset = 8> }  ⇝
   struct BlockQ4 { d: f16, q: Nib64o8 }       size_of::<BlockQ4>() == 34 checked   [D: 2 + 64/2]
   impl Nib64o8 {
     fn elem(&self, i: usize) -> i32  requires i < 64  ensures -8 <= result && result <= 7   (kcall)
       body: (if i < 32 { self.b[i] & 0xF } else { self.b[i - 32] >> 4 }) as i32 - 8
   }
   plus pack, unpack and the integer view (02 §7.2)
```

The body transcribes Hearth's layout: byte j holds element j in its low nibble and element j+32 in
its high nibble, stored as q+8 (`hx_quant.h`, `hx_block_q4`) [M, CC track: read at b5d3f14]. Storage
codes exist only inside formats (01 §4).

**Schedules.**

```text
 ⊢_sch N for g on t  iff
  (s1) g is a kernel fn, and t names a catalogue target with known feature names
  (s2) every name in N resolves over the inlined KIR of g: kernel callees are inlined, and a name
       bound in an inlined callee is accepted if it is unique in the inlined loop nest (F-2)
                                                                                  (E-SCHED-AMBIGUOUS)
  (s3) every primitive is in 02 §8.1's licence table; its class is recorded: exact; int_assoc, which
       emits T2 obligations for the reordered integer sum (a bound on the sum of absolute values of
       the terms, and for VNNI the bias identity over ActQ8.sum); keep_order; or timing-only (prefetch)
  (s3') the class is decided from the inlined KIR's loop-carried dependences, not read off the
       primitive's name (F-52):
       - `vectorize v` (and `parallel v`) is exact only if no loop-carried dependence through a
         float place crosses v's iterations (lanes are independent outputs), or v is the 16-lane
         loop of `canon::dot16` or `canon::sum16`;
       - `vectorize v using vpdpbusd | vpmaddubsw` (or another integer-sum lowering) is int_assoc
         only if the only dependence v carries is one integer accumulator whose partial sums T2
         bounds in every order;
       - `commute` of one IEEE add or mul is exact only if no order-sensitive consumer (MAXPS,
         MINPS) reads the result before `canon::nan`;
       - `keep_order x` holds only if x names a float chain the schedule leaves untouched
  (s4) a primitive outside the licence set, or one whose (s3') condition fails (split accumulators,
       FMA, a lane-count change, vectorising a float accumulator) is rejected (02 §8.2) (E-SCHED-REASSOC)
```

Without (s3'), `schedule bad for q4_row_dot on x86_64(avx512f) { vectorize g; }`, which splits the
float `acc` chain across lanes (02 §8.2's split accumulator), passed the front end and was caught only
by T1 at M2 (item N-35).

`⊢_sch` is the completeness side only. A schedule's soundness is T1 on the emitted object (03 §5.1),
which `mithi` cannot run.

**Specs.**

```text
 ⊢_spec P for g  iff
  (p1) g and every name in the claims resolve: definitions, schedules (realisations), or external
       reference symbols in a declared seam namespace (hearth_c_ref::…)
  (p2) each claim kind is one of refines, confined, safe, deterministic, perf, quality (03 §2.2)
  (p3) each grade is on its kind's property scale: correctness for refines, confined, safe and
       deterministic; performance for perf and quality                              (E-CLAIM-KIND, DR-007)
  (p4) each grade is admissible for its kind and slot: refines on a kernel slot needs proof or
       validated; non-kernel logits-path refines may say tested (03 §2.2)          (E-CLAIM-INADMISSIBLE)
  (p5) quantities in qualifiers are typed: margin: 3% is a Ratio, a [target]
```

Sealing and Author ownership are ledger rules (M3) that `⊢_spec` does not check. Whether `validated`
is an INV-VERIFY evidence class is provisional, pending D0-11.

**Staging.** `comptime { e }` is typed under `Σ ∪ {compile}` and no other label. Its result type must
contain no capability, no `Local` type and no `Mutex`. `mithi` evaluates it at build. Outside the X1
subset except `const` items (§12).

### 5.15 Function and program well-formedness

```text
 sig(g) wf: parameter and result types wf; a Local result only under T-Ret; ⊢_pkg ε_g ok
 Γ0: parameters as owned locals with symbolic grades α_j (reference parameters: referent grades,
     carrying ℓ_j*), J0 = {F ↦ ⊥}, X0 = ⊥,
     Φ0 = requires ∪ parameter ranges ∪ invariants of parameter types;  Σ = ε_g (declared or inferred)
 Γ0;Σ;⊥ ⊢ body : τ_r @ γ ! ε ⊣ Γ1
 ε ⊆ Σ;  every Linear by-value parameter is consumed;  no loan is live at exit except T-Ret (a)'s
 Θ_g: θ_ret from γ ⊔ Γ1.ρ;  θ_mut,j from the referent grade of &mut parameter j in Γ1 ⊔ Γ1.X (the
      end of the body and every return, F-31);  θ_exit from Γ1.ω;  θ_inv,j from the pc at the
      invocations of closure parameter j; each read off as (γ⁰, D, n, O) over the symbols α_j
 may_trap(g) as in §5.10;  ctx(g) as in §5.3;  g's sinks meet req(ctx(g))
 kernel fns satisfy ⊢_k; policy fns satisfy ⊢_to
 ───────────────────────────────────────────── T-Fn
 ⊢ fn g … : sig(g)
```

A program checks when every item checks and the call graph's rows, transfers and `may_trap` facts
reach their least fixpoint. The link rule INV-LOSSLESS-DEFAULT applies at link time: a default profile
that reaches `lossy` is a link error (01 §7.3).

### 5.16 Rejection codes the rules emit

This list is the vocabulary for the planted Dc corpus of ROADMAP §3.2 (≥ 100 items [target]), which
another family writes.

| Code | Rule | Source |
|---|---|---|
| `E-REF-FIELD` | J2 | 01 §5.3 (FF-REF) |
| `E-REF-ESCAPE` | T-Ret, std `¬Local` bound | 01 §5.3, §5.8 |
| `E-LOCAL-RETURN` | T-Ret | 01 §5.4 (FF-LOCAL) |
| `E-LOCAL-INSTANTIATE` | J2 | 01 §5.4 |
| `E-LIFETIME` [prov] | J2 | 01 §5.2 ("'a is Dc") |
| `E-DYN`, `E-ASYNC`, `E-MACRO`, `E-SPECIALIZE` | J2, J12 | DR-005 |
| `E-FF-CELL` | J2 | FF-CELL |
| `E-FF-SUM`, `E-FF-TIES`, `E-FF-EXP`, `E-FF-POWI`, `E-FF-F16`, `E-FF-CLOCK` | T-Prim, T-Call via cls | 01 §2.5 |
| `E-GRANT-UNSAFE`, `E-GRANT-FOREIGN`, `E-FP-ENV` | J3 | 01 §6.1 |
| `E-ROW-UNDECLARED` | §5.2 | 01 §6.3 |
| `E-LINEAR-DROP`, `E-LINEAR-COPY`, `E-LINEAR-PARTIAL` [prov] | T-Lin, J1 | 01 §5.6 |
| `E-LINEAR-INSTANTIATE` [prov] | J2, T-Call | F-41 |
| `E-BORROW-CONFLICT` [prov], `E-MOVE-BORROWED`, `E-MOVE-LOOP` | §5.4, T-Loop | Rust's rules |
| `E-BORROW-OUTLIVE`, `E-LOCAL-MUT-STORE` [prov] | §5.4, T-Let, T-Assign | F-39 (rustc rejects the same programs) |
| `E-FOOTPRINT` [prov] | §5.6 | F-45 |
| `E-PAR-DISJOINT`, `E-PAR-RACE`, `E-PAR-SEND`, `E-PAR-BREAK`, `E-PAR-EFFECT` | T-Par | 01 §12.3 |
| `E-DET-GRANT`, `E-DET-POLICY`, `E-DET-EVIDENCE`, `E-DET-STALE` | T-Det | 01 §6.4 |
| `E-DET-RESULT` [prov] | T-Det | F-34 |
| `E-GRADE`, `E-NAN-RAW-SINK` | §5.3 sinks | 01 §13.6 |
| `E-KERNEL-ROW`, `E-KERNEL-OBLIGATION`, `E-KERNEL-CALL` [prov codes] | ⊢_k | DR-011, 02 §2 |
| `E-TO-ROW`, `E-TO-RESULT`, `E-TO-LOOP`, `E-TO-RECURSION` [prov codes]; `E-TO-PARAM`, `E-TO-STATE`, `E-TO-AUTHORITY`, `E-TO-CALL`, `E-TO-STACK` [prov] | ⊢_to, ⊢_store | 01 §13.4; F-48 |
| `E-IMPL-ROW`, `E-IMPL-GRADE` [prov], `E-COHERENCE` | J12 | §5.12, F-50 |
| `E-SCHED-AMBIGUOUS` [prov], `E-SCHED-REASSOC` | ⊢_sch | 02 §8.2 |
| `E-CLAIM-KIND`, `E-CLAIM-INADMISSIBLE` [prov codes] | ⊢_spec | DR-007, 03 §2.2 |
| `E-DROP-IMPL`, `E-AMBIENT-IO`, `E-GLOBAL-STATE`, `E-FF-ADDR` [prov] | J2, §11, §5.3 | F-17, §11, F-56 |
| `E-TRAIT-OFF` [prov] | J12, in X1's "Mithril without traits" arm only | DR-005, ROADMAP §3.2 |
| `E-OUT-OF-SCOPE-<KW>` [prov] | §12: a construct outside the checker's X1 scope; KW is the keyword, format code or `std_platform` name | §0.3 agreement, Q10 |
| `E-TYPE` | all | ordinary type errors |

**Which code is primary [prov].** Agreement compares one code per rejected item, so the order is
fixed. `mithi` reports every failure it finds; the primary code is the first in this order, and
within one class the first by source position:

1. `E-OUT-OF-SCOPE-<KW>`, then J2 well-formedness (`E-DYN`, `E-REF-FIELD`, `E-LIFETIME`,
   `E-LOCAL-INSTANTIATE`, `E-LINEAR-INSTANTIATE`, `E-FF-CELL`, `E-DROP-IMPL`, …) and `E-TYPE`;
2. class codes from `cls` and the Dc list (`E-FF-*`, `E-AMBIENT-IO`, `E-MACRO`, `E-TRAIT-OFF`);
3. rows and grants (`E-ROW-UNDECLARED`, `E-GRANT-*`, `E-FP-ENV`, `E-DET-GRANT`);
4. loans and linearity (`E-BORROW-*`, `E-MOVE-*`, `E-LOCAL-*`, `E-REF-ESCAPE`, `E-LINEAR-*`,
   `E-FOOTPRINT`);
5. `par` (`E-PAR-*`) and the deterministic boundary (`E-DET-POLICY`, `E-DET-EVIDENCE`,
   `E-DET-STALE`, `E-DET-RESULT`);
6. grades and sinks (`E-GRADE`, `E-NAN-RAW-SINK`, `E-IMPL-GRADE`);
7. side judgements (`E-KERNEL-*`, `E-TO-*`, `E-SCHED-*`, `E-CLAIM-*`).

A verdicts.json item may list secondary codes in `also`; they are reported, not compared. So a clock
read in a policy (N-09) is primarily `E-FF-CLOCK` (class 2), with `E-TO-ROW` (class 7) in `also`.

---

## 6. Dynamic semantics

### 6.1 Configurations, choices, environments and targets

A run starts from a configuration `⟨H, T̄, J̄, Π⟩` (§2.6) with one thread at an entry point. Each step
is labelled by a choice `c` from an oracle: which thread steps, which `par` index a worker claims,
which I/O request completes, which thread acquires a lock, and, at certified ports in the demonic
mode used by Lemma 3b, which hint value arrives and whether a policy call overran its deadline. A
**scheduler** `s` is a strategy for these choices.

The **environment** `e` is not a choice per event. It is fixed before the run (01 §13.5): a function
`(slab, copy) → {ok, fault}`, where a copy that fails its content hash counts as `fault` and a
transient error that bounded retries absorb counts as `ok`, plus a capacity for every arena. A
**target** `T` is the C11 backend with its C compiler (trusted for non-kernel code) and T1-validated
kernels (03 §3.4). `⟦prim⟧_T` is the target's implementation of a primitive.

**Conformance (trust base).** For every primitive of `canon.v1`, `⟦prim⟧_T` equals the specified
result bit for bit, with one exception: the payload and sign of a NaN result of a primitive whose
`nanrule` is raw. A primitive whose `nanrule` is canon returns the canonical quiet NaN `0x7fc00000`
whenever it returns a NaN (`canon::nan`, 02 §5; Hearth NUMERICS §3 [M, CC track: read at b5d3f14]),
and the pinned FF-NANMAX forms return it for two NaN operands (01 §2.5). Integer primitives are exact.
Casts follow Rust. `cr::f` is correctly rounded and `canon_v1::f` is its fixed op-DAG. This is the
semantics-table axiom and the T1 witnesses of 03 §3.4, stated as one premise. The first draft
exempted NaN payloads for every primitive, `canon::nan` included, so Lemma E could not be proved from
it (F-51).

### 6.2 Thread-local steps

Evaluation contexts are left to right, as Rust's, except that an assignment evaluates its value
first (F-54):

```text
E ::= □ | E; e | let x = E; e | p = E | P[E] = v | g(v̄, E, ē) | prim(v̄, E, ē) | if E {e} else {e}
    | match E {…} | assert⟨σ⟩(E) | return E | S{…, f: E, …} | (v̄, E, ē) | det_E⟨E⟩
      P[E] = v: once the assigned value is a value v, the place's index expressions are evaluated,
      left to right, with their asserts; in every other position P[E] reads a place whose index is E
```

`addr(p)` resolves a place to `loc·π` in the current frame: a local through `ρ`, a field by extending
the path, an index by its value, a dereference through the reference value stored at `addr(p)`, and a
projection call by running its body to a reference.

```text
 [E-Copy]    E[copy p]                → E[H(addr(p))]
 [E-Move]    E[move p]                → E[v]   with H[addr(p) ↦ ⊠]; a moved Linear local leaves Φ.lin
 [E-Ref]     E[&p] / E[&mut p]        → E[ref_m(addr(p), λ)]          λ a fresh ghost tag (Lemma C)
 [E-Assign]  E[p = v]                 → E[()]  with H[addr(p) ↦ v]; an old std-owned resource is
                                                 released by audited drop glue (never user code)
 [E-Let]     E[let x = v; e]          → E[e]   with a fresh loc for x; a Linear v appends x to Φ.lin
 [E-Prim]    E[prim(v̄)]               → E[⟦prim⟧_T(v̄)]
 [E-Assert]  E[assert⟨σ⟩(true)]       → E[()]          E[assert⟨σ⟩(false)] → E[trap(σ)]
 [E-Call]    E[g(v̄)]                  → push ⟨g, ρ_g, lin_g, dom_g⟩ with parameters bound to v̄, where
                                         lin_g lists g's Linear by-value parameters in order (F-42);
                                         the capability parameters κ_ℓ are implicit and erased
 [E-Return]  ⟨Φ̄·Φ_c·Φ ; E[return v]⟩  → ⟨Φ̄·Φ_c ; E_c[v]⟩   (Φ's Linear locals are consumed by typing;
                                         its std-owned locals are released by drop glue)
 [E-Det]     E[det[E] {e}]            → E[det_E⟨e⟩]       an administrative frame (F-46)
 [E-DetEnd]  E[det_E⟨v⟩]              → E[v]              the frame has no other dynamic content
 [E-If], [E-Match], [E-Loop], [E-Break], [E-Continue], [E-Clo]: standard
```

`with_lock`, `Condvar` waits, `File.read_at` and the other `std_platform` operations step according to
their interface specification. A lock acquisition is a `lock(tid)` choice, an I/O completion an
`io(req)` choice, and the bytes an I/O returns are the file's content when `e` says `ok` and an
`Err` value when it says `fault`.

### 6.3 Traps, abandonment and fail domains

```text
 [E-Trap]   ⟨Φ̄·Φ ; E[trap(σ)]⟩ → ⟨Φ̄·Φ ; ⇑(σ, ε)⟩
              the context E is discarded: nothing in it is evaluated

 [E-Pop]    Φ.dom = none:
            ⟨Φ̄·Φ_c·Φ ; ⇑(σ, ī)⟩ → ⟨Φ̄·Φ_c ; ⇑(σ, ī)⟩
              after abandon(v_x) for each x in Φ.lin, newest first, and drop glue for Φ's other
              std-owned locals; the caller's context at the call site is discarded too

 [E-Domain] Φ.dom = k:
            ⟨Φ̄·Φ ; ⇑(σ, ī)⟩ → the domain result D_k(σ, ī)       (table below)
```

Discarding a context is safe for linear resources only because of E6 and `E-Call`'s `lin_g`: every
Linear temporary already evaluated in a discarded context is a named local in `Φ.lin`, and a callee's
Linear by-value parameters are in its own `Φ.lin`. Without them, a trap in
`consume2(store.lease(id)?, xs[i])` after the lease was produced, or in a callee before it consumed
its lease parameter, leaked the lease (F-42).

`abandon` for a `std_platform` linear type is its audited routine: an abandoned `Lease` decrements
the store's reference count and records the abandonment (01 §12.4). A user linear struct abandons its
fields in reverse declaration order [prov]. Abandon routines and drop glue are audited and may not
trap. An environment fault `Fault(φ)` propagates the same way, as `⇑F(φ)`.

| Fail domain | `D_k(σ, ī)` | Source |
|---|---|---|
| `export abi` entry | the declared trap error code; output buffers unspecified, as for any C API error | 01 §12.2 |
| hint-port policy call | `⊥`: the port takes its fallback's decision, plus a strike (§6.5) | 01 §12.2 |
| test or harness case | a recorded failure naming σ | 01 §12.2 |
| `main(root)` | process exit with a trap status. The host is the process itself | added (F-9) |
| service root (a long-lived `std_platform` service) | the service enters `Trapped(σ)`; its owner observes this at its next interaction or at the join | added (F-9) [prov] |
| scoped child (`scope.spawn`) | not a domain: it propagates to the scope's join, where the lowest spawn index wins, as in `par` | added (F-9) [prov] |
| `par` iteration | not a domain: it propagates to the join (§6.4) | 01 §12.3 |

**Never unwinds.** Between a trap and its domain, no user-written code runs: no `Drop` impl (user
`Drop` is Dc, F-17), no `catch_unwind` (Dc, 01 §12.1), and no code from the discarded contexts. Only
audited abandon routines and drop glue run. In the C11 lowering a trap is a status return, never
`setjmp` or unwinding tables (04 §9.1).

**Never aborts the host, modulo the stack (F-8).** No rule above aborts a process. Two things outside
these rules can. **Stack exhaustion** in the C11 lowering faults the process. The note proposes a
static stack bound from every thread root, with recursion either rejected on paths reachable from
`export abi` entries or guarded by a checked depth counter that traps (OP-6). **The C lowering of a
trap** must use a status return, never `__builtin_trap`, `abort` or `ud2`. For policy code, T0's
positive allowlist excludes any instruction not listed. The note assumes UD2 and INT3 are not listed;
03 §6.2 is normative for the list [inference].

### 6.4 `par`: serial projection and parallel realisation

The meaning of `par i in a..b { e }` is its serial projection: `for i in a..b { e }`. The realisation:

```text
 [E-Par-Start] E[par i in a..b {e}] → E[join(j)], with a fresh record
               J_j = ⟨lo = a, hi = b, r(k) = pending for a ≤ k < b⟩ and one task e[i := k] per k
 m(J) = min {k | r(k) = Exit(_)}, or hi if there is none           (Exit includes Fault, F-49)

 [E-Par-Claim] choice claim(j, k) with r(k) = pending:
               if k < m(J_j): r(k) := running, and a child thread ⟨Φ_iter(j, k) ; e[i := k]⟩ starts,
                              its root frame of domain kind iter(j, k), logical parent the frame
                              that executed the par (§7.2)
               else:          r(k) := skipped

 [E-Par-Done]  a child for k ends with a value:              r(k) := Normal
               it reaches ⇑(σ, ī) at its root:                r(k) := Exit(Trap(σ, ī))
               it executes return v at its root:              r(k) := Exit(Ret(v))
               it reaches ⇑F(φ) at its root:                  r(k) := Exit(Fault(φ))

 [E-Par-Join]  when no child of j is running and r(k) = Normal for every k < m(J_j):
               (1) m = hi:                      E[join(j)] → E[()]
               (2) r(m) = Exit(Fault(φ)):       E[join(j)] → E[⇑F(φ)]
               (3) r(m) = Exit(Trap(σ, ī)):     E[join(j)] → E[⇑(σ, m·ī)]
               (4) r(m) = Exit(Ret(v)):         E[join(j)] → E[return v]
               exits recorded above m, faults included, are ignored, as the serial projection never
               reaches them; before reducing, in cases (2) to (4): abandon, in ascending index order,
               every Linear value any iteration wrote into W, leaving those places holding no live
               Linear value (None for Option elements); in test builds, overwrite W's other places
               with a valid value of their type (F-7)
```

The first draft tried a "some iteration faulted" case first. A fault at an index above the winner
then overrode the serial outcome, and φ was "the first fault recorded", which depends on timing
(F-49). Faults now take part in the lowest-index rule like every other exit.

Three properties follow, and two deviations from the serial projection are stated rather than hidden:

1. **Lowest index wins.** The join waits for every index below the lowest recorded exit, so the
   reported outcome is the serial one and never depends on which iterations above it ran (Lemma B).
   Nested `par` loops produce index vectors `m·ī`, compared lexicographically.
2. **Faults are ordered but excluded.** An I/O fault in iteration k is a function of the environment
   and k's inputs, so it is ordered like a trap. Arena exhaustion inside a `par` body also depends on
   what other iterations allocated, so whether iteration k faults can differ between schedules; it is
   reported without an index (01 §12.3), and Theorem 4 excludes every environment under which some
   schedule exhausts an arena (§7.4). Per-iteration sub-arenas turn it into a trap at that
   iteration's index (§3.4).
3. **Unspecified means well typed (F-7).** After an early exit, each place in W holds its pre-loop
   value or a value some iteration wrote. Both are well typed and satisfy the type's `#[range]`,
   invariants and enum validity, because each iteration's writes are type-checked. A test-build poison
   must be such a value too. A fixed byte pattern could put an invalid discriminant or an out-of-range
   value in a place the checker reasons about.
4. **Deviation 1: written places.** After an early exit, W's contents differ from the serial run's.
   `T-Par` grades them `schedule_dependent` and raw on the exits that follow an early `Ret` (F-38),
   so Theorem 4's condition (iii) is now a consequence of typing.
5. **Deviation 2: termination (F-6).** The join waits for started iterations above the winner. If one
   of them diverges, the parallel run diverges where the serial projection would have stopped at the
   winner. So `par` refines its serial projection for partial correctness only. Theorem 4 is already
   termination-insensitive (condition iv). `mithi` runs the serial projection, so a differential test
   sees a timeout, not a wrong value. Cooperative cancellation (iterations poll `m(J)` at back edges)
   would close the gap at a cost on hot paths; it is a tombstone with a trigger (§15).

### 6.5 Policy calls at hint ports

```text
 a core thread reaches port q with snapshot s = snap_q(H):
 [E-Port-Ejected] Π(q).ejected                      → the core uses F_q(s)

 [E-Port-Call]    otherwise: st' := copy of Π(q).committed; save MXCSR; push a frame of domain kind
                  port(q) running P_q(s, &mut st') on a stack region of at least the port's budget
                  B_q ≥ S(P_q) (S-tot, (t9)) with a fuel counter φ_q, decremented at every back edge;
                  at 0 the decrement executes trap(fuel(q)); when the frame is popped, by return or
                  by trap, MXCSR is restored, status flags included [prov, F-58]

 [E-Port-Commit]  P_q returns h, the choice is overrun(q, false), and V_q(H, h) = ok:
                  one atomic step sets Π(q).committed := st' and the core uses h

 [E-Port-Fail]    P_q reaches ⇑(σ, ·) (any trap, fuel included), or the choice is overrun(q, true),
                  or V_q(H, h) = reject:
                  st' is discarded, the core uses F_q(s), Π(q).strikes += 1, and
                  Π(q).ejected := (Π(q).strikes ≥ k_q)
```

- **Fuel is logical, the deadline is not.** Fuel exhaustion is a function of P's inputs, so it is
  reproducible. The deadline is checked at commit against wall-clock time, so `overrun` is a scheduler
  choice (01 §12.5). Corollary 3c (§7.3) depends on this distinction.
- **The commit is one step.** The deadline check and the publication of `st'` happen in the same step,
  so a call's state is committed if and only if its hint is used.
- **Stack and FP state are the port's, not the policy's (F-48, F-58).** The port runs the policy on
  a reserved stack region of at least S(P), either a dedicated guarded stack or a check of the
  remaining core stack before the call that takes the fallback when it is short; either way stack
  exhaustion never happens inside a policy frame. Float arithmetic in a policy (allowed: FF-SUM and
  FF-TIES are C in `timing_only`) can set MXCSR's sticky status flags, so "the policy leaves MXCSR as it found it" holds
  only because the port restores it. No core code without `fp_env` can read the status flags, so
  restoring the control bits alone would suffice for outputs; restoring both makes Lemma 3a's
  "as it found them" literally true.
- **The fallback is the port's declared `fallback`.** ROADMAP §3.6 says "the default policy". This note
  reads that as the port's declared fallback, not a profile's default policy: a profile default that
  is itself a Mithril policy can trap, and its own fallback is the port's (F-10).

### 6.6 `det` and erasure

`det[E] { e }` steps to the administrative frame `det_E⟨e⟩`, which steps inside and disappears when
its body is a value (`E-Det`, `E-DetEnd`). The frame exists so that the runtime typing can keep
typing the block by `T-Det` while it runs (F-46); the first draft reduced `det[E] { e }` to `e` at
once, which changed its type's grade and row in one step. The frame has no other dynamic content
and the C lowering erases it: the boundary's whole effect is `T-Det`'s recomputed result grade and
the evidence it adds to B. Rows, grades, kinds, loans, the NaN bit and the ghost loan tags in
reference values influence no step (Lemma C).

### 6.7 Outcomes and observations

`eval_{s,e,T}(P, x)` is the outcome of the entry point on input x:

- at an `export abi` entry: the return value and output buffers for `Val`, an error code for `Trap`
  or `Fault` (output buffers unspecified);
- at `main`: the exit status;
- at a test case: pass, or fail naming σ.

`eval|o` restricts the observation to one output o: the result, the final content of one `&mut`
parameter's referent, or one export output buffer.

---

## 7. Theorems

Each theorem keeps 01 §13.6's statement where it was right and adds the fixes of §0.4. Each has a
proof plan, not a proof, and names its hardest case. Grades today are in §7.6.

### 7.1 Theorem 1: type safety (progress and preservation)

**Scope.** Well-typed MCore programs with `unsafe` and `foreign` only in granted packages, with
`std_platform` meeting its interface specification, including trap-free abandon routines and drop
glue.

- **Preservation.** If `Ψ ⊢ C` and `C ─[c]→ C'`, there is `Ψ' ⊇ Ψ` with `Ψ' ⊢ C'`. For each thread's
  redex, the type is preserved, and its grade and charged row do not grow: `γ' ⊑ γ`, `ε' ⊆ ε`. This
  holds at `E-Det` only because `det_E⟨e⟩` stays a frame typed by `T-Det` until its body is a value
  (F-46); the first draft's step from `det[E] {e}` to `e` raised the grade and added `nondet`.
- **Runtime typing (J17) [F-46].** `Ψ ⊢ C` types every runtime term, not only source terms:

  ```text
   RT-Det    the body typed as T-Det's premise, under the free-input grades recorded at entry
             ⟹ det_E⟨e⟩ : τ @ ⟨d_s^in, d_p⟩ … ! ε \ {nondet}
   RT-Join   join(j) : () when J_j is well formed: each Normal or running iteration k is typed under
             its own footprint of W, Exit records hold well-typed outcomes, and W's places satisfy
             Ψ with the per-element grades the completed iterations wrote
   RT-Trap   ⇑(σ, ī) and ⇑F(φ) : τ for any τ, at a site whose pc is already in ω
   RT-Port   a port(q) frame : Hint_q, its state copy typed as the state block with no loan outside it
   RT-Moved  ⊠ inhabits a location only where V marks it moved or uninit
   RT-Cover  a loop that covers p and has finished iterations [0, k) is typed by the generalised
             T-Cover, "covers p[k..n] given Ψ(p[i]) ⊑ γ(e_w) with ν canon for every i < k"
  ```

  With `RT-Cover` and element-wise grades in Ψ, `T-Cover`'s strong update is preserved after each
  iteration, although the residual loop runs from k, not from 0 (the first draft's premise 2 failed
  there). Lemma E and Theorem 4 are proved over this runtime typing; if grade monotonicity at some
  step proves awkward, the fallback is a binary logical relation for Theorem 4, and preservation then
  claims types, loans and rows only.
- **Progress.** If `Ψ ⊢ C`, then one of these holds: every thread has reached its root with a domain
  result; some thread can step under some choice; or every unfinished thread is blocked on a
  `std_platform` synchronisation or I/O operation. A thread in a propagating state `⇑` can always step
  (Lemma A).
- **Corollaries.** No use after move. No access through an ended loan. No data race: no two unordered
  accesses to one location of which at least one is a write. No Linear value dropped on a normal path.
  Every trap occurs at a site the checker recorded for the frame it occurs in, and never in a kernel
  frame (Lemma D).
- **Not claimed.** Termination, deadlock freedom, and freedom from stack exhaustion (F-8). The
  permutation scheduler and liveness monitors cover the first two (01 §5.8).

**Proof plan.** The standard syntactic method of progress and preservation (attributed to Wright and
Felleisen; named from background knowledge, not re-read for this note), over an *instrumented*
semantics, then erasure:

1. Instrument the heap with a ghost permission map `𝒫 : loc·π ↦ {own, excl(λ), shr(λ̄)}`. Every access
   checks `𝒫`, and a step that violates it is stuck.
2. Prove progress and preservation for the instrumented semantics. The semantics is environment- and
   heap-based (`E-Let` allocates a location, `E-Call` binds parameters in ρ), so the lemmas are not
   the syntactic method's usual substitution and weakening. They are: **Env-Heap correspondence**
   (ρ and H agree with Γ under Ψ: every variable's location holds a value of its type and grade,
   loans included); substitution only of integer values for a `par` index (`e[i := k]`); weakening
   only for non-Linear, unloaned bindings (review item R1-23); place inversion; **Loan-Transfer** (a projection's
   result loan is nested in its argument's loan, and a loan set moves with its value, §5.4),
   **Frame-Pop** (every loan carried by a popped frame ends, except a projection loan, which is
   re-rooted on the caller's place), **Par-Split** (W splits into per-iteration exclusive footprints by
   injectivity or T2, and shared captures are read-only, so shared permissions can be duplicated),
   **Par-Join** (footprints merge back; an invariant re-check deferred to the join runs only after
   they have), **Scope-End** (`E-BORROW-OUTLIVE` makes every loan on a dying local dead), and
   **Abandon** (abandon routines restore `𝒫` for the leases they release; by E6 and `lin_g`, every
   live Linear value is reachable from some frame's `Φ.lin` when a trap discards contexts).
3. Lemma C transfers the result to the uninstrumented semantics.

**Hardest case.** Preservation at `E-Par-Join` after an early exit. Heap typing for W must be
re-established when iterations above the winner ran partly or fully. Each wrote only well-typed values
(per-iteration preservation, F-7), and the join abandons the Linear values among them, which needs the
`lin` bookkeeping to be per iteration rather than per frame. The second hardest is `E-Return` of a
projection, where Loan-Transfer must re-root the result loan without overlapping a live loan of the
caller. The third is a value stored through `&mut` by a std function (`Vec::push`, `mem::swap`),
where the loan set must follow the value into the receiving referent; the review's examples of
dangling references (items N-24 to N-27) all fail exactly there when loan sets are not propagated.

### 7.2 Theorem 2: capability confinement

**Scope.** Well-typed programs whose `unsafe` and `foreign` code lies only in granted packages, with
`std_platform` meeting its specification: capability types have no constructors other than minting at
`main(root)` or an `export abi` entry and attenuation methods, and attenuation never adds authority.

- **(a) No forging.** In every reachable configuration, every capability value `cap(k, ℓ̄)` was minted
  at `main(root)` or an `export abi` entry, or produced by `std_platform` attenuation from a capability
  its producer held, with no more authority. It reached its holder by parameter passing, by return, by
  a move into a data structure and back out, or by a recorded service capture (01 §6.2).
- **Logical call stack [F-55].** A `par` iteration's root frame and a scoped child's root frame
  have a logical parent: the frame that executed the `par` or the `scope.spawn`. The logical call
  stack of a frame is its own thread's stack followed by its root's logical parent's logical stack.
  A call to g is "in progress" for a step if g's frame is on the step's logical call stack.
- **(b) Row soundness.** During a call to g, every executed primitive with labels ℓ̄, on any thread
  whose logical call stack contains g's frame, satisfies `ℓ̄ ⊆ row(g) ∪ ε_C ∪ N_g`. Here `ε_C` is the
  union of the rows charged when the `Local` closures passed into the call were created, which
  belong to g's callers. `N_g = {nondet}` if the primitive executes inside a `det_E` frame created by
  g or one of its callees, and `∅` otherwise (01 §13.6). Because `T-Det`'s result is first-order
  (F-34), no closure created inside the frame runs after it.
- **(b') Service threads (F-4).** Every primitive executed by a thread whose root is an escaping
  closure of type `fn(…) ! ε_f` satisfies `ℓ̄ ⊆ ε_f ∪ N`, and `ε_f` is contained in the authority of
  the frame that created the closure, which was charged `ε_f` (`T-CloE`).
- **(b'') Scoped children and `par` iterations [F-55].** Every primitive executed by such a thread
  is covered by (b) for every call on its logical call stack. For a child rooted at a `Local`
  closure, the closure's row is in its creator's `ε_C`, as for any `Local` closure call.
- **(c) Slot corollary.** A candidate for a Forge slot or hint port with maximum row `ε_s`, called
  with no closure arguments, executes no primitive outside `ε_s`. For `timing_only` slots, `ε_s = ∅`
  and `N = ∅`, because `⊢_to` forbids `det` blocks in the policy and its callees. T0 checks this on the
  object code with a positive allowlist (03 §6.2).

**Proof plan.** Attach to each frame its authority `A(Φ)`: `row(g)` for a function frame, and for a
`Local` closure body the authority Σ of its creator at the creation site. Show three invariants by
induction on steps:

1. every primitive step in Φ has `ℓ̄ ⊆ A(Φ)`, or `A(Φ) ∪ {nondet}` inside a `det` block (`T-Prim`'s
   premise `ℓ̄ ⊆ Σ`);
2. a callee frame's authority is contained in its caller's (`T-Call`'s premise `ε_g ⊆ Σ`);
3. a `Local` closure value exists only while its creator's frame is live.

(b) follows by attributing each step to the nearest enclosing call of g on the step's logical call
stack, which a child thread's own stack would not contain. (a) is a case analysis
showing that only minting and attenuation steps produce capability values: no primitive produces one,
generics cannot conjure one (capability types implement no constructor trait, §5.1), and `format`
parsers cannot produce one, because formats contain only storage codes and scalars.

**Hardest case.** A `Local` closure created by f, passed down through g, whose row lacks the closure's
labels, and invoked deep inside h. The labels are attributed to f through `ε_C`, which needs invariant
3. That invariant rests on `T-Ret`, `E-REF-FIELD`, `E-LOCAL-INSTANTIATE` and Theorem 1's loan
discipline together. It is also the place where the closure-parameter exception of §5.7 must be shown
not to smuggle a `Local` closure into another parameter's place.

### 7.3 Theorem 3: `timing_only` noninterference

**Setting.** A core C with hint ports q ∈ Q. Each port has a snapshot function `snap_q`, a validator
`V_q`, a fallback `F_q` (core code) and a fuel budget `φ_q`. A **port oracle** `𝒪 : (q, k) ↦ Hint_q ∪
{⊥}` assigns a value to the k-th call of each port. `C[𝒪]` is the core in which the k-th call of q
yields `𝒪(q, k)` if that is not ⊥ and `V_q` accepts it, and `F_q(snap_q)` otherwise. `C[P̄]` is the
core with policy `P_q` at each port, run by the rules of §6.5. `F` also names the all-⊥ oracle: every
call takes its fallback.

**Premises.** O1–O5 (02 §12.4) and O6 (01 §13.6), plus four that this note adds (§8):

- **F-tot.** Each `F_q` is core code with row ∅ and `may_trap(F_q) = false`, and it terminates on
  every snapshot.
- **P-ind [F-47].** Whether and where the core traps does not depend on the oracle: for every oracle
  𝒪, input x, scheduler s and environment e with ¬fail_e(x), the trap outcome of `C[𝒪]` (none, or a
  site with its index vector) equals that of `C[F]` under `(σ0, ok)`. Sufficient discharges, in
  increasing cost: no trap site is reachable in the port-reachable core (`may_trap = false`, which is
  what the first draft's P-tot demanded); every trap site reachable under a pc or guard that depends
  on a hint value is discharged (a hint-taint variant of `may_trap`, using the grade `γ_sh` of hint
  values, §5.13); or the store-core bounded model check proves it, up to its bound. The first draft's
  P-tot ("C[𝒪] reaches no trap site for any input") was stronger than Theorem 3 needs and fails for
  any core with an input-dependent trap, which 01 §12.6 allows at exports.
- **S-tot [F-48].** Every port call runs within a reserved stack region of at least `S(P_q)` (§5.13
  (t9), §6.5).
- **A-ind [F-49].** Whether the core exhausts an arena under e does not depend on the oracle; arena
  exhaustion is then part of `fail_e(x)` (below), never a channel through which a policy causes `Err`.

Every `P_q` satisfies `⊢_to` and passes T0 on its object code.

**Lemma 3a (containment; this note plus T0).** For every run r of `C[P̄]` under scheduler s and
environment e, there is an oracle `𝒪_r` such that r and the run of `C[𝒪_r]` under `(proj(s), e)` agree
on every core location other than the ports' policy state blocks, and on every output. `proj(s)` is
the scheduler s with every choice about a policy thread's steps erased: `C[𝒪_r]` has no policy steps,
so s itself is a strategy over the wrong configurations, and r and the run of `C[𝒪_r]` are related by
a simulation that erases policy steps (F-58). `𝒪_r(q, k)` is the hint `P_q`'s k-th call returned if
it returned normally, within fuel and before the deadline; otherwise it is ⊥. Each call of `P_q`
writes only its private state copy and its own stack region, and returns or is cut off within its
fuel; the port leaves the FP environment (MXCSR control and status bits, the x87 control word), DF,
the callee-saved registers and every core location as it found them (§6.5).

**Lemma 3b (the core certificate; 03).** For every oracle 𝒪, every scheduler s (thread
interleavings and completion orders; the first draft quantified over completion orders only, F-58)
and every environment e:

```text
 out(C[𝒪], x, s, e) = Err(φ_e(x))          if fail_e(x): some slab in demand(x) is fault on every copy
                                              and tier under e, or (A-ind) the core exhausts an
                                              arena under e's capacities; φ_e(x) is the first such
                                              slab in demand(x) order, or the arena fault
                    = out(C[F], x, σ0, ok)  otherwise   (σ0 a reference order; ok the all-ok environment
                                                          with every capacity sufficient)
```

`demand(x)` is the set of slabs the demand reads of the serial projection of `C[F]` on x read under
the all-ok environment: hint-initiated reads are not demand reads (O6), and iterations above a `par`
winner never contribute (§6.4), so the set is a function of x alone.

**Theorem 3.** For every policy assignment P̄ as above (each satisfying `⊢_to` with its side
judgements evaluated on the monomorphised call graph, F-53), every scheduler s (thread interleavings,
completion orders, deadline overruns) and every environment e:

```text
 out(C[P̄], x, s, e) = Err(φ_e(x))          if fail_e(x)
                    = out(C[F], x, σ0, ok)  otherwise
```

The proof composes the two lemmas: Lemma 3a turns the run into a run of `C[𝒪_r]` under `proj(s)`, and
Lemma 3b applies to every oracle and every scheduler. Stack exhaustion inside a policy frame, which
would abort the host and break the equation, is excluded by S-tot, not assumed away (F-48).

- **Corollary 3a (relational).** For any two policy assignments P̄ and P̄′:
  `out(C[P̄], x, s, e) = out(C[P̄′], x, s′, e)`. Logits are independent of every policy choice, and the
  condition for `Err` mentions only x and e, so no policy behaviour is ever a cause of `Err`.
- **Corollary 3b (fallback).** A run in which some or all policy calls trap, exhaust their fuel,
  overrun the deadline, return an invalid hint or are ejected has the same output. These are runs of
  `C[𝒪]` for oracles with ⊥ entries.
- **Corollary 3c (`timing_blind` replay, F-11).** Suppose P̄ is `timing_blind` and every validation
  outcome is a function of the logical event stream (the premise of 02 §12.5). If the run has no
  deadline strike, its port decisions equal those of a trace replay, so replay byte counts are exact.
  A run with a deadline strike has the same output (Corollary 3b), but its replay exactness is void.
  The evaluator must therefore record deadline strikes and void the replay comparison of any run that
  has one.

**Hardest case.** Lemma 3b, the store core's own theorem. It lies outside this calculus and is graded
by its bounded model check, chaos suite and core-mutant kill (DR-010). Inside the calculus, the hardest
case of Lemma 3a is a trap in the middle of a policy call that has partly written its state copy,
racing the deadline check: the commit must be the single atomic step of `E-Port-Commit`.

### 7.4 Theorem 4: determinism, with scopes

**Setting.** P is well typed, g its entry point, x an input. o is an output of g: its result, the
referent of a `&mut` parameter, or an export output buffer. Its **outcome grade** is
`γ̂_o = γ_o ⊔ ω_g`: the grade of the value joined with the exit grade (§2.3).

**Non-failing environments (generalised, F-5, F-49).** An environment e is non-failing for x if:

- (a) no slab in `demand(x)` is fault on every copy and tier under e (`demand(x)` as defined with
  Lemma 3b: a function of x alone);
- (b) for every scheduler, no run of P on x under e exhausts an arena (other than the program-sized
  sub-arenas whose exhaustion is a trap, §3.4); and
- (c) for every scheduler, every I/O primitive executed outside a `det` block returns its ok result
  under e.

Each clause quantifies over schedulers, so non-failing is a property of (P, x, e), not of one run.
The first draft's (b), "no arena is exhausted inside a `par` body", depended on which iterations
above a winner happened to run. Quantifying over every scheduler is strictly stronger than a per-run
premise; whether Theorem 4 also holds for every pair of runs that both end without `Fault` is OP-17.

If e fails (a) or (b), the run's outcome is `Fault(φ)`, which the API maps to `Err`. If e fails (c),
the outcome is whatever the program computes from the `Err` value. Theorem 4 says nothing about such
runs, and nothing in general guarantees that they fail closed: a program can turn an `Err` from a
direct read into a default value. Only code whose I/O passes through a `det` boundary whose evidence
covers faults, as the store's does through O6, fails closed.

**Theorem 4.** Suppose:

- (i) every boundary `E ∈ B(o)` holds: its claim is true;
- (ii) the trust base of 03 §3.4 holds: the semantics table, the T1 rewrite list, `std_platform`, the
  elaboration of exact meanings into KIR, and the C compiler for non-kernel code;
- (iii) the Linear values among the places written by a `par` that exited early have been abandoned
  in index order (`E-Par-Join`). The contents of those places need no exclusion any more: `T-Par`
  grades them `schedule_dependent` on the exits that follow an early `Ret`, so any output computed
  from them has that scope and no claim is made about it (F-38). The first draft excluded the places
  but not outputs computed from them, so `let _ = fill(&mut y, x); y[7]` was graded `cross_device`
  while its value depended on the schedule (item N-15); and
- (iv) both runs terminate. A run that diverges, deadlocks or exhausts its stack voids the comparison,
  including a run in which an iteration above a `par` winner diverges (F-6).

Then, by the scope of o's outcome grade γ̂_o:

| Scope of γ̂_o | Claim |
|---|---|
| `cross_device` | For all schedulers s, s′ (interleavings, `par` claims, I/O completion orders, hint streams at certified ports, deadline overruns), all conforming targets T, T′, and all environments e, e′ non-failing for x: `eval_{s,e,T}(P, x)\|o = eval_{s′,e′,T′}(P, x)\|o` |
| `device(t)` (reserved) | The same, with T and T′ of class t |
| `schedule_dependent` | No claim beyond Theorem 3 and the boundaries' own evidence |

Equal means one of three things: the same bits, with every float at a `cross_device` sink
NaN-canonical; the same trap site with the same lowest `par` index vectors; or the same `Err` value.

**`deterministic(by: E)`.** Removing `nondet` with `det[E]` is sound for Theorem 4 exactly when E's
claim holds, which is condition (i). The statement is a value-level claim, so its effective grade
meets `grade(E)` for every `E ∈ B(o)` (03 §3.2). That is the precise sense in which the boundary
removes only `nondet` and lowers grades by E.

**Proof plan.**

1. **Low equivalence.** Two configurations are low-equivalent if they agree on every location whose
   grade has scope `cross_device` and on every control decision taken under a `cross_device` pc.
2. **Unwinding.** Every step preserves low equivalence for any pair of choices, in the style of
   pc-based information-flow type systems (01 §13.1 names information-flow typing as the precedent).
   Primitives with `nondet` or `nondet(platform)` produce high values. Writes under a high effective
   pc go to high places (`T-Assign` joins the effective pc, which includes every jump decision still
   open, F-30). Writes through a local reference go to the borrowed place (F-39). Closure calls apply
   their summaries (F-35). Reads of shared state have the fixed high grade `γ_sh`. `T-Det`'s
   recomputed result is justified by (i) and Lemma F.
3. **`par`.** Lemma B reduces every parallel schedule to the serial projection.
4. **Targets.** Conformance (§6.1) gives bit equality of primitives except NaN payloads, and Lemma E
   shows payloads never reach a low observer or a `cross_device` float sink.
5. **Exits.** `ω_g` of scope `cross_device` means the choice among return, trap and early exit is low;
   the lowest-index rule makes the index vector low.

**Hardest case.** A `par` early exit whose trap condition reads shared inputs, together with the
join's waiting rule. The outcome is the minimum over low-determined iteration outcomes, but only after
grading W high on the early-return exits (F-38) and excluding the runs in which a higher iteration
diverges (iv). The NaN observers are the second hardest: every payload-exposing operation must carry
the `device(platform)` taint, F-13 showed the list in 01 was incomplete, and F-50 showed the transfer
form needs the observer set O to carry the taint through calls.

Hearth's INV-DET-1, -2 and -3 are instances. Kernels discharge them by per-build T1 witnesses,
policies by Theorem 3, and the store path by its boundary evidence (01 §13.6).

### 7.5 Lemmas

- **Lemma A (traps never unwind and never abort).**
  1. After `E-Trap`, no user-written code executes until a domain frame is reached; only audited
     abandon routines and drop glue run.
  2. Every thread's root frame is a domain frame (export, port, test, `main`, service), or a `par`
     iteration or scoped child whose join is in an ancestor thread, so every `⇑` reaches a domain.
  3. No rule aborts the process, except stack exhaustion (F-8) and `main`'s own exit. Inside a
     policy frame, S-tot rules out stack exhaustion too (F-48).

  *Proof plan:* inspection of `E-Trap`, `E-Pop`, `E-Domain` and `E-Par-*`. Part 3 relies on the
  status-return lowering (04 §9.1) and, for policies, on T0's allowlist.
- **Lemma B (`par` refines its serial projection).** Under `T-Par`'s premises, for every scheduler and
  every terminating parallel run, the outcome of `par i in a..b { e }` and every location outside W,
  plus W itself when no iteration exits early, equal those of `for i in a..b { e }`. The premise
  that does the work is `E-PAR-EFFECT` on the exercised row: the first draft checked the row after
  `T-Det` had removed `nondet`, so `par i in 0..n { let k = deterministic(by: E) { m.with_lock(…) }; … }`
  passed while its iterations did not commute (F-36, item N-34). *Proof plan:*
  disjoint footprints and the read rule make steps of different iterations commute (a diamond
  property), so every interleaving is equivalent to the serial order on the locations outside W. On an
  early exit the join waits for every index below m, so the indices below m are Normal in both runs,
  and the serial run stops at m with the same outcome. *Hardest case:* reborrowed sub-slice
  projections `&mut p[lo(i)..hi(i)]`, whose disjointness is a T2 fact, not a syntactic one.
- **Lemma C (erasure).** Rows, grades, kinds, loans and the NaN bit are compile-time only. The ghost
  loan tags and the permission map influence no step of a well-typed program. Elaboration adds only
  undischarged asserts outside kernels, the `canon::nan` calls the source wrote, and abandonment on
  trap paths and after an early-exited `par`. Effects and grades therefore cost nothing at run time
  [target], which `mithc audit` checks on generated C (01 §13.6).
- **Lemma D (kernels never trap).** If `⊢_k g` holds and T2 is sound, no trap occurs in a frame of g
  or of any `kcall` helper it calls.
- **Lemma E (NaN canonicality).** Under conformance, every float value with `ν = canon` is either not
  a NaN on any conforming target or the canonical NaN on every one. Every value whose bits can differ
  between conforming targets has `ν = raw`, and every observer of such a value carries the
  `device(platform)` taint. It rests on the restated conformance (canon-rule primitives return
  `0x7fc00000`, F-51) and on `nanrule` being total. *Hardest case:* `T-Cover`'s strong update, which
  must be justified by the loop writing every element exactly once on every path through an
  iteration and by the body having no exit that could leave a later element unwritten (premise 0,
  F-37); a trap is the only way out, and it ends the domain before any sink is read. At run time the
  strong update is carried by `RT-Cover` (§7.1).
- **Lemma F (boundary soundness).** Suppose `det[E] { e }` is well typed and E's claim holds: for
  every scheduler and every environment non-failing for the run (condition (c) of the non-failing
  definition exempts I/O inside `det`, so the claim must cover environment variation itself), the
  block's result is a function of the values of its free inputs at entry. Then if those inputs are
  low, the result is low, and `T-Det`'s recomputed result scope `⟨d_s^in, d_p⟩` preserves the
  unwinding invariant of Theorem 4's proof. If an input is high, `d_s^in` is high and nothing is
  claimed (F-32). E's claim is about first-order values only (F-34).

### 7.6 What each statement is worth today

Grades follow 03 §3.2 and §3.4 and agree with 01 §13.7. Nothing here is mechanised. Lean is
by-trigger (DR-010, D-08).

| Statement | Proof route | Grade today | Upgrade path |
|---|---|---|---|
| Theorem 1 | paper proof plan above; `mithi` against `mithc` differential testing; checker property tests and mutation | `tested` | Lean MCore when D-08 fires |
| Theorem 2 (a, b, b', b'') | Theorem 1 plus the no-forging case analysis; capability audit graph in the Fact Plane | `tested` | Lean MCore (D-08) |
| Theorem 2 (c), binary level | T0 allowlist decision procedure on lifted object code | effective `validated(partition)`; for `confined(S)`, `validated(bounded: …)` through the store-core theorem; code floor `tested`, printed, not met | mechanised T0 (D-08); second checker (D-09) |
| Theorem 3 | Lemma 3a (T0 plus this note) and Lemma 3b (store core with O6, F-tot, P-ind, S-tot and A-ind: bounded model check, chaos suite, core-mutant kill) | effective `validated(bounded: …)` with code floor `tested` when the binary check ran; `tested` otherwise | Lean or Verus proof of the store core (DR-010) |
| Theorem 4 | Theorem 1, the unwinding argument and boundary evidence | `tested` (golden scheduling, ISA and batch identity, hash corpus); kernel instances `validated` by T1, code floor `tested` | Lean MCore (D-08) |
| Lemmas A, B, D, E, F | as above | `tested` | with their theorems |
| Lemma C (erasure) | inspection of generated C; object audit | `tested` | — |

---

## 8. Noninterference with the trap fallback: the §3.6 narrowing check

ROADMAP §3.6: "If noninterference cannot be stated together with the trap fallback, the policy feature
is redesigned before M4." This section checks the question explicitly.

### 8.1 Why the fallback is the problem

A policy that could make the store return `Err` by trapping would satisfy any noninterference theorem
of the form "the golden output *or an error*" while denying service at will (01 §12.5, [RV: D2-A]).
Mithril therefore turns every policy failure into the fallback's decision plus a strike. The question
is whether a single theorem can then say both "outputs do not depend on policies" and "a trapping
policy is harmless", or whether the trap path needs a separate argument that might not go through.

### 8.2 The statement that works

Theorem 3 (§7.3) quantifies over **port oracles**, not over policies, and puts the fallback *inside*
the oracle's semantics: an oracle value ⊥ means "take `F_q`'s decision". Lemma 3a maps every behaviour
of a policy, normal or not, onto an oracle: a normal, in-time, valid hint becomes its value, and
everything else (a trap anywhere in the call, fuel exhaustion, a deadline overrun, an invalid hint,
ejection) becomes ⊥. Lemma 3b holds for **every** oracle, so it does not need to know why ⊥ occurred.
The trap fallback is therefore an instance of the theorem, not an exception to it.

An oracle fixes one value per call, while a policy chooses adaptively from its snapshot. That
difference does not matter: Lemma 3a builds the oracle `𝒪_r` from the run itself, and the core's
behaviour given the values it receives does not depend on how they were chosen.

01's formulation quantifies over every hint *stream*. The first draft said it already covers the
fallback because "the fallback's decision is itself a valid hint value". That reason is wrong (review
item R1-22): `F_q` is computed on the snapshot taken when the core reached the port, and `V_q` runs on
the heap at commit, so the fallback's decision need not validate. The conclusion still holds, for a
different reason: a stream that carries `F_q(s)` at that call yields the decision `F_q(s)` either way,
because a validated hint is used and a rejected one is replaced by the fallback computed on the same
snapshot. 01's formulation therefore covers the fallback only through that same-snapshot property of
the port, which §6.5 states. The ⊥ notation does not depend on it, which is a reason to adopt it in 01
(§14 P-2).

### 8.3 Where it could fail, and what closes each case

| # | Way the combined statement could fail | Status |
|---|---|---|
| N1 | The fallback itself traps or diverges, so `C[F]` is not total and the right-hand side is undefined or an `Err` that comes from the core | Closed by **F-tot** (new premise): `F_q` is core code, row ∅, `may_trap = false`, terminating |
| N2 | Core code traps for some oracle values (for example after accepting a valid but unusual victim), so a hint causes a core trap that the export maps to its trap error code, an `Err` not caused by the environment | Closed by **P-ind** (new premise, F-47): the core's trap outcome is the same under every oracle. Input-dependent traps are allowed; they appear identically on both sides of Lemma 3b. "No trap site reachable" is one sufficient discharge |
| N3 | A policy traps after writing part of its state, and the half-written state is committed | Closed by the double buffer: `E-Port-Commit` publishes `st'` only on a normal, in-time, validated return |
| N4 | A policy trap escapes the port: it unwinds into the core or aborts the host | Closed by the port frame being a fail domain (`E-Domain`) and by status-return lowering; at the binary level by T0 (no instruction outside the allowlist, no call outside the closure). The first draft marked this closed while a policy could still exhaust the core thread's stack (N10) |
| N5 | `Err` used as a denial-of-service channel | Closed by Lemma 3b's form: the `Err` condition is a function of (x, e) only (O6) |
| N6 | The deadline makes ⊥ timing-dependent | Harmless for outputs, because Lemma 3b holds for every oracle. It breaks `timing_blind` replay exactness for runs with a deadline strike: Corollary 3c (F-11) |
| N7 | "The default policy" is a Mithril policy that can itself trap | Read as the port's declared fallback, where the chain ends (§6.5) |
| N8 | Strike counts or ejection are visible to the policy through its views | Harmless: a policy can only emit hints, whatever it observes |
| N9 | A demonic hint stream livelocks the store (it keeps evicting what demand needs next) | Outside Theorem 3, which is termination-insensitive; liveness under demonic hints is O5's job, monitored and model-checked to its bound |
| N10 | A policy with large stack frames, `let scratch = [0u64; 1 << 21];` (16 MiB [D: 2^21 · 8 bytes]), overflows the core thread's stack inside the port call, and the host dies: neither an `Err` nor the fallback | Closed by **S-tot** (new premise, F-48): (t9) computes S(P), finite because (t5) forbids recursion; the port runs the policy in a reserved region of at least S(P) or takes the fallback; T0 can check frame sizes on the object code |
| N11 | A policy steers the core into exhausting an arena (by prefetch hints that fill a cache, say), so an arena fault, now an environment fault (§3.4), becomes a policy-caused `Err` | Open: closed by **A-ind** (new premise, F-49), a store-core obligation that whether the core exhausts an arena does not depend on the oracle. It has no discharge route in this note; P-2 proposes it for the certificate |

### 8.4 Verdict

Noninterference **can** be stated together with the trap fallback, in the form of §7.3. The ROADMAP
§3.6 narrowing does not fire, on three conditions:

1. F-tot, P-ind, S-tot and A-ind are added as named obligations of the store-core certificate and
   its ports. 02 §12.4's O1–O5 and 01's O6 do not name them today. F-tot is checkable with the
   `may_trap` fact; P-ind with `may_trap`, its hint-taint variant, or the bounded model check; S-tot
   with (t9) and T0's frame-size check. §14 P-2 proposes the change.
2. A-ind is discharged by the store-core certificate. This note gives no route for it; the review
   added it (N11), and it is the premise most likely to need design work at M4 [G].
3. The different-family Prover and Adversary required by ROADMAP §3.6 agree.

This is a judgment [G], not a proof. The narrowing would fire if Lemma 3b could be shown only for
oracles restricted to the values a policy can produce. The demonic quantification would then fail,
and the trap path would need its own theorem. It would also fire if F-tot, P-ind or A-ind could not
be discharged: for example, if the LRU fallback or a validator needs a trapping path, or if the
store's capacity management lets hints decide whether a demand allocation fails. P-ind is weaker than
the first draft's P-tot, which would have fired the narrowing for any core with an input-dependent
trap (F-47).

---

## 9. Hand derivations: summary

The full derivations are in [core-calculus/derivations.md](core-calculus/derivations.md). Each one
gives the elaborated MCore, the context, the judgement steps, every obligation with how it is
discharged, the computed facts (row, `may_trap`, transfers, NaN bit, context) and the verdict.
[verdicts.json](core-calculus/verdicts.json) repeats the verdicts in machine-readable form.

**Copies.** All 45 `mith` blocks were hashed. After stripping `//` comments and normalising
whitespace, every copy of a canonical snippet in 01, 02, 03 and ROADMAP is identical to its
ARCHITECTURE §5.3 original, and README's two functions are identical to ARCHITECTURE's `q4_row_dot`
and `pick_victim` [M, CC track script, 2026-10-16]. Copies therefore share a derivation.

**The prelude.** Canonical snippets mention declarations they do not contain: `Matrix`, `ActQ8`,
`SlotView`, `Store::acquire_inner`, the evidence `golden::scheduling_independence`, the schedule
`q4_matvec_avx2` and others. [derivations §P](core-calculus/derivations.md#p-the-canonical-prelude)
lists them as signatures. `mithi` is judged on prelude plus snippet.

| Item | Snippet (source) | Verdict | Rules that carry the derivation | Conditions |
|---|---|---|---|---|
| D-C1 | `format BlockQ4` (ARCH §5.3; 01 §4; 02 §7.1) | accept | ⊢_fmt, kcall | — |
| D-C2 | `q4_row_dot`, `q4_matvec` (ARCH §5.3; 01 §5.3, §8; 02 §2) | accept | T-Fn, ⊢_k, T-Jump (loop guards), T-Call, T-Proj, T-Par, **T-Cover**, T2 by unrolling | Matrix invariant (F-3) |
| D-C3 | `schedule q4_matvec_avx512` (ARCH §5.3; 02 §8.1) | accept (front end) | ⊢_sch with inlined-KIR resolution (F-2) | soundness is T1 at M2 |
| D-C4 | `policy fn pick_victim` (ARCH §5.3; README; 01, 02, 03) | accept; `may_trap` true | ⊢_to, T-Assert, T-Loop, T-Jump | prelude: `SlotView` and `Tick` are `#[view]` |
| D-C5 | `read_slab`, `acquire` (ARCH §5.3; 01 §6.4; 02 §14; 03 §3.3) | accept | T-Fn, T-Proj, T-Det | `acquire` in module `store`; E present with subject `store::acquire`, hash-pinned (F-33); `acquire_inner`'s row |
| D-C6 | `spec q4_matvec_claims` (ARCH; ROADMAP §1; 01; 03) | accept (front end) | ⊢_spec | `q4_matvec_avx2` exists; seam namespace |
| D-C7 | `Quantity` and `todo!` (ARCH; 01; 02) | accept; `may_trap` true | T-Let, J12 (no mixed-origin `Add`), T-Hole | checked as the body of a prelude function |
| D-C8 | README taste | accept | as D-C2 and D-C4 | as D-C4 |
| D-D01 | `trait Dequant`, `first_value` (01 §4) | accept | J12, T-Call through Θ̂ | — |
| D-D02 | `Matrix::row` (01 §5.3) | accept | T-Ret (a), T-Proj, T2 (nonlinear) | Matrix fields and invariant |
| D-D04 | `hottest` (01 §5.4) | accept | T-CloL, T-CallClo, closure exception, std adapter rule T-Ret (b) | prelude adapter signatures and their transfers (§5.7) |
| D-D05 | `Lease`, `expert_step` (01 §5.6) | accept | T-Lin, T-Match (`?`), T-Proj | store and kernel signatures |
| D-D06 | `note_use` (01 §5.8) | accept | T-CloL, with_lock's signature | prelude: `with_lock`, `StoreState::touch` |
| D-D08 | `ActQ8`, `block_index` (01 §9.1) | accept | §5.10 contracts, T2 | — |
| D-D09 | `check_entries` (01 §12.3) | accept | T-Par (W = ∅), early exit, Lemma B | — |
| D-D11 | `q4_matmul` and its schedule (02 §9) | accept | nested T-Par, **Proj-Split**, T-Cover | Matrix `IndexMut` footprint (F-25), discharged statically at its definition (F-45); rule `Proj-Split` [prov] (F-45); `cols() == blocks_per_row()` |
| D-D12 | `flow moe_ffn` (02 §12.1) | out of X1 (M4–M5); at X1 `E-OUT-OF-SCOPE-FLOW` | T-Det, T-CloL | grant for its module (F-18); allocation rule (F-15); `map_on_arrival` scoped; evidence whose subject is this block (F-33) |
| D-D13 | `store ExpertStore` (02 §12.3) | out of X1 (M4); at X1 `E-OUT-OF-SCOPE-STORE` | ⊢_store sketch | F-tot, P-ind, S-tot, A-ind; `next_layer` |
| D-D16 | `value_sum` with a hole (04 §6.4) | accept | T-Hole, contracts (F-14) | — |
| D-D17 | `KvRow`, `tick` (04 §6.5) | accept by the calculus | T-Assign, T-Proj | the hot-path copy rule is a lowering rule and may reject it |
| D-D18 | `open_slots` (04 §9.3) | out of X1 (M5); at X1 `E-OUT-OF-SCOPE-MEMCAP` | T-Lin, T-Match | arena signatures |
| D-D19 | `evolve slot store_evict` (06 §2.1) | out of X1 (M4); at X1 `E-OUT-OF-SCOPE-EVOLVE` | ⊢_store (slot) sketch | — |
| D-D20 | `spec s5_forward_claims` (07) | accept (front end) | ⊢_spec | subjects in the target's closure (OP-16) |
| D-D21 | `kernel fn softmax` (07) | accept | ⊢_k, **T-Cover** | transcendental choice provisional, pending D0-2 |
| D-D22 | `heat_into` (07) | accept; `may_trap` true | T-CloL by-mut capture, γ_sh transfer | `Store::state` visible in module `store` |
| D-D10, D-D23 | MXFP4 `format` (02 §7.3; 07) | out of scope (later); at X1 `E-OUT-OF-SCOPE-E8M0` | ⊢_fmt structure only | needs `canon.v1.1` |

The remaining items are copies with their own hashes: D-D03 and D-D07 (the two halves of D-C2 in 01),
D-D14 and D-D15 (the two halves of D-C5 in 02 and 03), D-D24 (ROADMAP's indented copy of D-C6), D-D25
and D-D26 (01's and 02's copies of D-C7's lines) and D-D27 (02's copy of D-C3). Each shares its
original's derivation and verdict.

Negative items that are part of the gate, because they appear as comments inside derived snippets:
`first_dyn` (`E-DYN`), `RowCache` (`E-REF-FIELD`), `pick` (`E-REF-ESCAPE`), `live`
(`E-LOCAL-RETURN`), `expert_step` without `release` (`E-LINEAR-DROP`), and `heat_view`
(`E-REF-ESCAPE`, F-28). Supplementary negative items, reported but not gate inputs: the outline's
`q4_matvec` without `a.len() == w.blocks_per_row()` (`E-KERNEL-OBLIGATION`), a mixed-origin
`Quantity` (`E-TYPE`), a clock read in a policy (`E-FF-CLOCK`) and a bare float sum in a kernel
(`E-FF-SUM`).

The review's counterexamples became supplementary items N-11 to N-39 (derivations §N): each is a
program the first draft accepted wrongly, or handled wrongly, with the verdict and code the revised
rules give. They are not gate inputs, because ROADMAP §3.2's agreement covers the documents'
snippets, and they are offered to the planted Dc corpus of ROADMAP §3.2, which another model family
writes.

---

## 10. Tier 0 trace

The Tier 0 card does not exist yet; the X1 track drafts it. This table traces each rule atom that 05
§2 says the card must carry. **Rule for the card [prov]:** every rule-bearing sentence of the card
cites a T0 ID below, and every card snippet gets a verdicts.json entry and a hand derivation before
the card freezes.

Atoms that are protocol, not semantics, trace to their owning document. They are marked "protocol"
(Owner question Q4).

| T0 | Atom (05 §2 block) | Traces to |
|---|---|---|
| T0-01 | If it parses as Rust it means Rust (subset rule) | §3.1 E1; §5.0 cls |
| T0-02 | Otherwise it is rejected with a named diagnostic | §5.16 codes; §5.0 cls = Dc |
| T0-03 | Or it uses a new keyword | §3.1 E4; §2.5 items |
| T0-04 | Exact numerics in exact-graded code (Rules) | §5.3 ctx and sinks; ⊢_k (k4, k5); §6.1 conformance |
| T0-05 | `uses { }` on public functions | §5.2 (declared and inferred rows, F-22) |
| T0-06 | Second-class references except projections | §5.4; T-Proj, T-Ret (§5.6); J2 `E-REF-FIELD` |
| T0-07 | `todo!` holes | T-Hole (§5.5); F-23 |
| T0-08 | Anchors, not lines | protocol: 05 §5, §7. Note section until Q4 is answered: §3.4 (trap sites are named by anchor) and §5.11 (evidence subjects name blocks by anchor) |
| T0-09 | Evidence policy | protocol (03 §2–§3), except T-Det's evidence premise (§5.11) and ⊢_spec (§5.14) |
| T0-10 | `abandon` and the friction rule | protocol: 05 §10, 03 §9. Note section until Q4 is answered: §6.3, which defines the other `abandon` and so fixes what the card must not confuse it with (F-20) |
| T0-11 | `kernel` | ⊢_k, kcall (§5.10) |
| T0-12 | `format` | ⊢_fmt (§5.14) |
| T0-13 | `schedule` | ⊢_sch (§5.14) |
| T0-14 | `policy` | ⊢_to (§5.13); E-Port (§6.5) |
| T0-15 | `spec`, `claim` | ⊢_spec (§5.14) |
| T0-16 | `uses` | §5.2; T-Call capability check (§5.5) |
| T0-17 | `deterministic` | T-Det (§5.11); E-Det (§6.6); Theorem 4 |
| T0-18 | `par` | T-Par, T-Cover (§5.9); E-Par (§6.4); Lemma B |
| T0-19 | `linear` | K-Lin (§5.1); T-Lin (§5.8); E-Pop abandon (§6.3) |
| T0-20 | `requires`, `ensures`, `invariant` | §5.10 contracts and obligations; T-Assert; T-Call |
| T0-21 | `comptime` | §5.14 staging (outside X1 except `const`) |
| T0-22 | `export abi` | §6.3 fail domain; Theorem 2(a) minting (M1, outside X1) |
| T0-23 | `store`, `hint port`, `certificate` | ⊢_store sketch (§5.13); E-Port (§6.5); Theorem 3 (M4, outside X1) |
| T0-24 | `evolve slot` | §5.13 (slot sketch; M4, outside X1) |
| T0-25 | `flow` | typed as `fn` (D-D12); no flow-specific rule yet (M4–M5, OP-12) |
| T0-26 | Every keyword is contextual | grammar (05 §3); no calculus rule. Note section until Q4 is answered: §3.1 E4 (a D construct elaborates only from a keyword, a new type or a std name) |
| T0-27 | Effect list | §2.3 ℓ; §5.2; taint (§5.3) |
| T0-28 | Fidelity and determinism scope | §2.3 grades; §5.3; Theorem 4 scopes |
| T0-29 | FF-FMA | §3.2 float operators; §6.1 conformance (two roundings) |
| T0-30 | FF-MULADD | T-Prim: `mul_add` is the only fused primitive |
| T0-31 | FF-SUM | §5.0 cls; ⊢_k (k5) `E-FF-SUM`; C in default and `timing_only` |
| T0-32 | FF-TIES | §5.0 cls `E-FF-TIES` in exact context; C in `timing_only` |
| T0-33 | FF-NANMAX | nanrule (canon under the pinned choice, §5.3) |
| T0-34 | FF-ROUND | §3.2 casts and calls: Rust meaning (ties away); no calculus rule beyond E1 |
| T0-35 | FF-CAST | §3.2 `as`: saturating, NaN to 0 |
| T0-36 | FF-OVF | §3.2 integer operators: `assert⟨ovf⟩`; ⊢_k (k2) |
| T0-37 | FF-EXP | §5.0 cls `E-FF-EXP` in exact context; `cr::` and `canon_v1::` primitives |
| T0-38 | FF-POWI | §5.0 cls `E-FF-POWI` in exact context |
| T0-39 | FF-F16 | §2.2 storage-only scalars `s`; no arithmetic primitive (`E-FF-F16`) |
| T0-40 | FF-REF | J2 `E-REF-FIELD`, `E-LIFETIME`; T-Ret `E-REF-ESCAPE` |
| T0-41 | FF-LOCAL | K-Local; T-Ret `E-LOCAL-RETURN`; J2 `E-LOCAL-INSTANTIATE`; §5.7 |
| T0-42 | FF-DYN | §2.2 (no `dyn`); `E-DYN` |
| T0-43 | FF-ASYNC | §5.12 `E-ASYNC`, `E-MACRO` |
| T0-44 | FF-CELL | J2 `E-FF-CELL` |
| T0-45 | FF-UNSAFE | J3 `E-GRANT-UNSAFE` |
| T0-46 | FF-CLOCK | §2.3 `time` carries `nondet`; ⊢_k (k5); ⊢_to (t1) |
| T0-47 | FF-HOLE | T-Hole; trap site `hole(n)` (§3.4) |
| T0-48 | FF-Q4 | ⊢_fmt `BlockQ4` (§5.14) |
| T0-49 | Snippet: fn with `uses` | D-C5 `read_slab` pattern; §5.2 |
| T0-50 | Snippet: a hole | D-C7; T-Hole |
| T0-51 | Snippet: `requires`/`ensures` | D-D08 pattern; §5.10 |
| T0-52 | Snippet: `format` | D-C1 pattern; ⊢_fmt |
| T0-53 | Snippet: `kernel` + `schedule` | D-C2, D-C3 patterns; ⊢_k, ⊢_sch |
| T0-54 | Snippet: `policy fn` | D-C4 pattern; ⊢_to |
| T0-55 | Snippet: `deterministic(by: …)` | D-C5 `acquire` pattern; T-Det |
| T0-56 | Snippet: `Quantity` | D-C7 pattern; J12 |
| T0-57 | Loop, verbs, JSON glossary | protocol: 05 §1, §11. Note section until Q4 is answered: §5.16 (the diagnostic codes and their precedence, which the glossary's error vocabulary names) |

57 atoms [M: counted in this table]. 53 trace to calculus rules (T0-09 only in part). 4 are protocol
atoms: T0-08, T0-10, T0-26 and T0-57. Until the Owner answers Q4, each of the 4 also cites a section
of this note, so the trace gate does not presume Q4's answer (review item R2-20). None is untraced.
T0-34 traces only to E1, because "quantisers
call `round_ties_even()`" is advice about which Rust function to call, not a rule Mithril adds. The
card's eight snippets must come from outside every sealed family's solution space (05 §13), so they
are patterns of the derivations above, not copies of them.

---

## 11. Idioms that do not type: amber candidates

ROADMAP §3.6's amber fires when an idiom that X1's reference solutions *need* cannot be typed. No
reference solution exists yet, so this is a prediction [G], not a measurement. Each row would become
a Dc rule with a code and a fix, and the subset rejection rate (ROADMAP §3.2 amber c, 05 §16) would
measure its cost.

| ID | Idiom (Rust) | Why it does not type | Code | Fix offered | Families at risk [G] |
|---|---|---|---|---|---|
| A-1 | A struct holding a borrowed slice: `struct Cursor<'a> { buf: &'a [u8], pos: usize }` | a reference in a field | `E-REF-FIELD` | keep `pos` in the struct and pass `buf` to every method | T-FMT, T-STORE |
| A-2 | A lookup returning a reference with two reference parameters: `fn find<'a>(t: &'a Table, k: &Key) -> Option<&'a Entry>` | Rust needs `'a`; Mithril has no lifetimes, and extending elision would accept non-Rust programs without a D construct (tombstone `multi_reference_elision`) | `E-LIFETIME` | take the key by value, or return an index | T-STORE, T-CTRL |
| A-3 | Returning an iterator: `fn live(&self) -> impl Iterator<Item = &Slot> + '_` | a `Local` adapter escapes | `E-LOCAL-RETURN` | take a closure parameter, or return indices | all |
| A-4 | An RAII guard with `impl Drop` | user `Drop` is Dc [prov, F-17] | `E-DROP-IMPL` | a `linear struct` consumed explicitly | T-STORE, T-CTRL |
| A-5 | `println!`, `eprintln!`, `dbg!` for debugging | ambient I/O authority [prov] | `E-AMBIENT-IO` | a log capability passed in, or remove | all |
| A-6 | Global mutable state: `static M: Mutex<…>`, `OnceLock`, `lazy_static!` | no globals (01 §6.2) [prov code] | `E-GLOBAL-STATE` | pass the state as a parameter | T-CTRL |
| A-7 | An LRU list as `Rc<RefCell<Node>>` | interior mutability and shared ownership | `E-FF-CELL` | index-based nodes in a `Vec` with generation stamps (G05 §1) | T-EVICT, T-STORE |
| A-8 | `impl<'a> IntoIterator for &'a MyColl` | needs a named lifetime in the associated type | `E-LIFETIME` | a method returning a slice (a projection) | T-FMT, T-STORE |
| A-9 | A strategy object `Box<dyn Policy>` | no `dyn` (DR-005) | `E-DYN` | a generic parameter | T-EVICT |
| A-10 | `sort_by(\|a, b\| b.partial_cmp(a).unwrap())` inside a kernel | the `unwrap` cannot be discharged (NaN) | `E-KERNEL-OBLIGATION` | `canon::topk` with an explicit NaN rule, or `total_cmp` on canonical values | T-ROUTE, T-NORM |
| A-11 | Debug output of an address: `format!("{:p}", &x)` | addresses are not observable in safe code (01 §6.1) [prov, F-56] | `E-FF-ADDR` | print an index or an id | all (debugging) |

Three further idioms type but cost a row label or a grade, and X1 should count them separately from
Dc rejections: global heap allocation under the provisional `alloc(Global)` rule (OP-1), `HashMap`
APIs whose order follows the buckets under the provisional `nondet` rule (OP-2, C-HASH), and user-
visible atomics, which carry `nondet` (C-ATOMIC). The review's other new rejections
(`E-LOCAL-MUT-STORE`, `E-BORROW-OUTLIVE`, the closure result discipline) reject only programs that
rustc also rejects, so they should add nothing to the subset rejection rate [G]. `E-LINEAR-INSTANTIATE`
applies only to Linear values, which Rust does not have.

---

## 12. What is frozen for X1's subset

ROADMAP §3.2: "The note's rules for the X1 subset are frozen at this point; a later change that would
flip a verdict on an X1 item is recorded as an amendment and applies from M1." The freeze point is the
commit that marks this note FROZEN, and no later than the `mithi` precondition run.

**In the checker's X1 scope; rules frozen.** These are the constructs whose rules `mithi` must
implement for the checker precondition. The agent-facing subset may be smaller (next paragraph).

| Construct | Rules frozen |
|---|---|
| Rust-coincident core: `fn`, `let`, `struct`, `enum`, `match`, `if`, loops, `?`, `Result`, `Option`, integer and float primitives, `as` | §3, §5.0–§5.5, §5.10, §6.1–§6.3 |
| Second-class references, projections, loans | §5.4, §5.6 |
| Closures and the non-escaping kind, std iterator adapters | §5.7 |
| `linear struct`, abandonment on trap paths | §5.8, §6.3 |
| Static-dispatch traits (the "Mithril" arm; the "without traits" arm rejects `trait` and `impl Tr for` with `E-TRAIT-OFF` [prov code]) | §5.12 |
| `kernel fn`, `kcall`, contracts, `#[range]`, `invariant` | §5.10 |
| `par for`, `T-Cover` | §5.9, §6.4 |
| `policy fn` (no ports at X1: `mithi` runs a policy directly, and a trap is reported as the test's failure) | §5.13 (t1–t9; (t9) only computes S(P), since budgets belong to ports) |
| `deterministic(by: E)`, with E checked against fixtures declared in the task's `mith.toml` (`[evidence] fixtures = [...]`, each with a kind, a grade and a subject naming one definition or one block anchor) instead of a ledger [prov]. Fixtures and `declare_deterministic` grants are hash-pinned task inputs that the agent cannot edit (F-33) | §5.11 |
| `format` for Hearth's Q4, Q8, F16, BF16 and F32 blocks | ⊢_fmt |
| `schedule` and `spec`: front-end checks only | ⊢_sch, ⊢_spec |
| `Mutex<T>::with_lock`, `Condvar`, `Frozen<T>`, `SlabBuf`, `Arena`, `Hint<T>`, `Quantity` | prelude signatures (derivations §P) |
| Grades: `exact`, `cross_device`, `schedule_dependent`, the NaN bit | §2.3, §5.3 |

**Two subsets, not one.** The X1 track's draft design
([experiments/x1-harness/DESIGN.md §9.1](../../experiments/x1-harness/DESIGN.md), read 2026-10-16)
defines the *agent* subset: what the X1 tasks and the Tier 0 card need. It rejects `par for`,
`deterministic`, `schedule`, `spec`, `linear` and others with `E-X1-NOTYET-<KW>`, and leaves out
`Frozen<T>`, I/O capabilities and T2. That is a reasonable cut for the agents, but ROADMAP §3.6 also
requires every canonical snippet to be *accepted by `mithi`*, and §3.2 requires agreement on every
canonical and derived snippet. The canonical `q4_matvec` uses `par for`, `acquire` uses
`deterministic`, and the schedule and spec snippets are themselves canonical. Under the draft's cut,
`mithi` would reject them and the §3.6 gate could not pass. Treating `E-X1-NOTYET` as agreement would
loosen ROADMAP §3.6, which neither track may do.

| Construct | X1 design draft §9.1 | This note | What the §3.6 gate needs from `mithi` |
|---|---|---|---|
| `par for` | out (`E-X1-NOTYET`) | in | type it; running it as its serial projection is enough |
| `deterministic(by: E)` | out | in, with fixture evidence | type it; dynamically it is an administrative frame with no effect (`E-Det`) |
| `schedule`, `spec`, `claim` | out | front end only | `⊢_sch` and `⊢_spec`, no execution |
| `linear struct` | out | in | `T-Lin` (static); abandonment only on trap paths |
| `Frozen<T>`, `BlobFile`, `read_at` | out | prelude signatures | type the canonical `read_slab` and `acquire`; no I/O needs to run |
| static discharge of kernel obligations (T2) | out: `requires` checked at run time | required in kernels (DR-011) | the canonical kernels are accepted either way; only the supplementary item N-07 tells the two apart |
| `Vec`, `String` | in (minimal) | C-ALLOC [prov] | none for canonical snippets |

**Recommendation [G].** Keep the X1 design's agent subset for the card and the tasks, and give `mithi`
a *typing-only* acceptance of the constructs in the first five rows, so that the canonical and derived
snippets are accepted as ROADMAP requires. The cost is some hundreds of lines of checker [G, not
estimated in detail]. If that is not affordable, the Owner decides (Q9); this note does not loosen the
gate.

**Outside the X1 subset.** `export abi` (M1), logits-path grade context (M1), `store`, `hint port`,
`certificate` and `evolve slot` (M4), `flow` (M4–M5), `comptime` blocks other than `const` items,
MXFP4 formats (later), `device(t)`, `real`, `approx` and `lossy` (reserved), and user effects
(by-trigger). An X1 *task* item that uses one of them is out of scope, not a Dc rejection: it is not
counted in the subset rejection rate. At the checker precondition, `mithi` must recognise them and
answer `E-OUT-OF-SCOPE-<KW>` [prov], with KW the first such keyword, format code or `std_platform`
name in source order: `FLOW`, `STORE`, `EVOLVE`, `EXPORT`, `COMPTIME`, a format code outside the X1
list (`E8M0`, `E2M1X2`), or a `std_platform` name outside the X1 prelude (`MEMCAP`). The derived
snippets D-D10, D-D12, D-D13, D-D18, D-D19 and D-D23 have these as their expected X1 verdicts
(§0.3, Q10).

**Provisional rules that must be pinned before the card freezes.** Each is reversible and needs the
review and the Owner's signature on this note.

| ID | Rule [prov] | Alternative | Finding |
|---|---|---|---|
| C-ALLOC | `Vec`, `String`, `Box`, `vec!` and `format!` allocate from a std arena `Global`, so they carry `alloc(Global)`, inferred for private functions and declared on `pub` ones. `Global` is Sync, so `par` bodies may allocate | no label for the global heap (but then policies could allocate unless T0 alone forbids it), or arena-only tasks at X1 | F-15, OP-1 |
| C-HASH | `HashMap`/`HashSet` with the default hasher: every API whose output order or callback order follows the bucket order carries `nondet`: `iter`, `iter_mut`, `keys`, `values`, `values_mut`, `drain`, `into_iter`, `retain`, `Debug` formatting, and the set operations `intersection`, `union`, `difference`, `symmetric_difference` (F-56). Lookup, insertion, removal by key, `len` and `contains_key` do not | a pinned deterministic hasher, if the pinned Rust documentation permits one for an open choice [inference: unverified] | F-16, F-56, OP-2 |
| C-DROP | user `impl Drop` is Dc (`E-DROP-IMPL`) | allow it on normal paths only, which is a false friend | F-17 |
| C-IO | `println!`, `print!`, `eprintln!`, `eprint!` and `dbg!` are Dc (`E-AMBIENT-IO`) | allow them in test builds only | §11 A-5 |
| C-MACROS | built-in forms (F-21): `todo!`, `unimplemented!`, `unreachable!`, `panic!`, `assert!`, `assert_eq!`, `assert_ne!`, `debug_assert!` and its `_eq`/`_ne` forms (always checked: a pinned choice, as for overflow), `matches!`, `vec!`, `format!`, `write!`, `writeln!`. All others are Dc (`E-MACRO`) | a longer list | F-21 |
| C-VEC | `Vec` and iterator adapters over owned collections are `?Local` | `Vec<&T>` is `E-LOCAL-INSTANTIATE` | OP-3 |
| C-FROZEN | `Frozen<T>` is Linear iff T is | `Frozen` always affine, with audited release | F-24 |
| C-CAP | capability types are affine, with no constructor traits | linear capabilities (Austral) | §5.1 |
| C-ATOMIC | load, store and read-modify-write operations on user-visible std atomics carry `nondet` (01 §6.1); atomics inside `Frozen` refcounts and `par` work distribution are not user-visible | atomics are Dc in the X1 subset | F-56 |
| C-FMT-ADDR | the `{:p}` format specifier is Dc everywhere (`E-FF-ADDR`) | allow it in test builds only | F-56 |
| C-LIN-GENERIC | every type parameter has an implicit `¬Linear` bound; only std may write `?Linear`; `drop`, `mem::forget` and discarding container methods keep `¬Linear` (`E-LINEAR-INSTANTIATE`) | linearity checked after monomorphisation, with errors far from their cause | F-41 |
| C-STORE | storing a value with foreign loans into a parameter's `Local` referent is `E-LOCAL-MUT-STORE` | reject every user signature with `&mut τ`, `τ : Local` (simpler; rejects Rust that compiles) | F-39 |
| C-PROJSPLIT | rule `Proj-Split` (§5.9) for footprinted projections inside `par` | none: without it D-D11 is `E-PAR-DISJOINT` and 02 §9 hoists the row (P-19) | F-45 |
| C-CLOMONO | bodies generic over a closure type are re-typed per closure site at monomorphisation | a closure-summary bound declared on `Fn*` bounds (more annotation) | F-35, OP-19 |
| C-OOM | exhausting an arena whose capacity is not a program value is the environment fault `⇑F(oom(A))`; only program-sized sub-arenas trap | `oom(A)` a trap everywhere, with Theorem 4 restricted to environments of equal capacity | F-49 |
| C-EXACT-STD | the std functions admissible in exact context (`⊢_k` (k3), `kcall`, `T-Call`): `<[T]>::len` and `<[T; n]>::len`; built-in indexing and slicing; `f16::to_f32`, `bf16::to_f32`; `canon::*`, `canon_v1::*`, `cr::*`; on integer types `wrapping_*`, `checked_*`, `saturating_*`, `min`, `max`, `abs`, `count_ones`, `leading_zeros`, `trailing_zeros`; `f32::max` and `f32::min` under FF-NANMAX; the constructors of `Option` and `Result`; format accessors. Every other std function is `E-KERNEL-CALL` in exact context | a longer list, each entry with a reason | F-59 |

---

## 13. Open problems

| ID | Problem | Why it matters | Next step |
|---|---|---|---|
| OP-1 | Global heap allocation (C-ALLOC) | the derived `moe_ffn` returns an owned `Act` and declares only `{ io, spawn }`; X1 tasks will allocate | X1 pre-registration pins C-ALLOC or an alternative; the cost shows in the subset rejection rate |
| OP-2 | Collections whose iteration order is nondeterministic (C-HASH) | silent `schedule_dependent` outputs in T-ROUTE-like code | read the pinned edition's `RandomState` contract [inference: unverified here] |
| OP-3 | Which std containers are `?Local`; user-defined `Local` types (by-trigger, 01 §5.4) | A-1 and A-8 are the main source of predicted Dc cost | X1's subset rejection rate by construct |
| OP-4 | Linearity of `Frozen<T>` and `Arena<A>` | the last release of a `Frozen<SlabBuf>` must not drop a linear buffer | settle with the S4 store prototype (G05 open question 1) |
| OP-5 | Cooperative cancellation in `par` (F-6) | divergence above the winner hangs the join | tombstone with a trigger (§15) |
| OP-6 | Stack exhaustion (F-8) | "never aborts the host" fails on deep recursion | a static stack bound per thread root, or a checked depth counter that traps; owned by 04 |
| OP-7 | Cost of runtime invariant checks outside kernels (§5.10) | re-checking at publication points and at the end of every `&mut` loan on a sub-place (F-43) may be expensive | measure at M1; a weaker re-establishment point is an amendment, and must not weaken what kernels assume |
| OP-8 | Logits-path grade context for non-kernel code (DR-013) | needs `export abi` and hot roots | M1 |
| OP-9 | Unconstrained hole types (F-23) | the pinned edition's never-type fallback is unverified here | check the edition's reference when it is pinned |
| OP-10 | T2 cost of nonlinear obligations and unrolling | `Matrix::row` needs `(r+1)·bpr ≤ rows·bpr`; `q4_row_dot` unrolls 64 additions; the `ActQ8` invariant 64 terms | measure T2 times on the prelude at M1 |
| OP-11 | Grades of policy views | all views are `γ_sh` here; a logical view such as a token counter could be `cross_device`, which matters for `timing_blind` | decide with the store port (S4) |
| OP-12 | `flow` has no rule of its own | 02 §12.2's handlers need flows to be interpretable several ways | specify at M4 |
| OP-13 | Rows charged at closure creation (F-4) may inflate creators' rows | agents may find over-approximated rows confusing (01 §14 question 1) | Surface Lab |
| OP-14 | Diagnostic code for a reference at a std `¬Local` bound (F-28) | `heat_view` is `E-REF-ESCAPE` in 01, but the rule is the instantiation rule | 05 stabilises codes |
| OP-15 | What to mechanise first when D-08 fires | Theorem 1's par and projection cases carry the most risk | Lean MCore plan at the D-08 trigger |
| OP-16 | Spec claims about subjects other than the spec's target (07's S5 spec claims `q4_matvec_avx512`) | ⊢_spec (p1) needs a scope rule | proposed: subjects must lie in the target's closure [prov] |
| OP-17 | Theorem 4 in a per-run form: do any two runs that both end without `Fault` agree, without quantifying non-failing over every scheduler (F-49)? | the universal premise excludes environments in which only some schedules exhaust an arena | a proof attempt with the runtime typing of §7.1 |
| OP-18 | A-ind: whether the store core can exhaust an arena depending on hints (N11) | a new store-core obligation with no discharge route here | design with the S4 store prototype; P-2 |
| OP-19 | Cost of re-typing generic closure bodies per closure site (C-CLOMONO, F-35) | checker time and diagnostics far from their cause | count per-κ re-checks on X1's reference solutions |
| OP-20 | How an emptied Linear container (`Vec<Lease>`) is finally consumed (F-41) | without a consuming operation a Linear `Vec` can never leave scope | a std method that asserts emptiness and consumes, specified with the S4 store prototype |
| OP-21 | Analysis cost of the jump grades and loan sets (F-30, F-39) in `mithi` | both add a fixpoint component to every loop | measure on the prelude and X1's reference solutions |

01 §14's four open questions remain open: lexical charging of rows, richer `Local` types, whether
`abandon` suffices for Hearth's error paths, and whether T1's lockstep rule composes with the serial
projection for batched prefill.

---

## 14. Proposed changes to sibling documents

This note edits none of them (track rule). Each change below is a proposal for the owner of that
document.

| ID | Document | Change |
|---|---|---|
| P-1 | 01 §13 | After this note is signed, replace the sketch with a link to it, or import its rules (PLAN §3.6 says 01 is not edited in M0) |
| P-2 | 02 §12.4, 03 §5.2, 02's `store` snippet, 01 §13.6 | Add F-tot, P-ind, S-tot and A-ind to the store-core and port obligations, and name O6 in the `certificate` clause (§8); state Theorem 3 over port oracles with ⊥ for the fallback (§8.2) |
| P-3 | 01 §12.2 | Add `main`, services and scoped children to the fail-domain table (F-9) |
| P-4 | 01 §13.6 | Add `total_cmp` to the NaN observers (F-13) |
| P-5 | 01 §13.6 Theorem 4 | Generalise non-failing environments (F-5); state that `par` refines its serial projection for partial correctness only (F-6) |
| P-6 | 01 §13.4 | Add the capability-capture premise to T-CloE and Theorem 2(b') (F-4) |
| P-7 | 01 §12.3, 02 §3 | Unspecified written places hold well-typed values; test poison must be a valid value of the type (F-7) |
| P-8 | ARCHITECTURE §5.3, 01 §5.3 | Show `Matrix`'s invariant, or state that kernels rely on it (F-3) |
| P-9 | 01 §11 or 02 §12.1 | Grant `DeclareDeterministic` to `moe_ffn`'s module, or move its `deterministic` block into module `store` (F-18) |
| P-10 | 02 §8.1 | Schedule names resolve in the meaning's own scope first, then uniquely in inlined kernel callees (F-2) |
| P-11 | 02 §12.5, 06 §5.4 | The evaluator records deadline strikes and voids replay exactness for runs that have one (F-11) |
| P-12 | 01 §6.3, 05 §5 | Make the fix level for inserting a row label on a `pub fn` agree (`InterfaceChanging`) |
| P-13 | 01 §3 or 05 §3 | Publish the closed list of built-in `name!(…)` forms (F-21, C-MACROS) |
| P-14 | 01 §12.4 | Say in which order a user linear struct abandons its fields (reverse declaration order, proposed) |
| P-15 | 04 §9.1 | A trap's C lowering never uses `__builtin_trap`, `abort` or `ud2`; add a static stack bound per thread root (F-8) |
| P-16 | 03 §6.2 | State explicitly that UD2 and INT3 are not on T0's allowlist |
| P-17 | docs/m0/PLAN.md §3.6 | Resolved: PLAN now names `docs/m0/core-calculus.md` and withdraws `CORE-CALCULUS.md` |
| P-18 | experiments/x1-harness/DESIGN.md §9.1, docs/m0/prereg/X1-writability.md | Let `mithi` accept, typing-only, the D constructs the canonical and derived snippets use (§12, Q9); have `mithi` answer `E-OUT-OF-SCOPE-<KW>` for the out-of-X1 constructs (§12, Q10); add the tombstone constructs of §15 to the harness's `dc_rate` enumeration, and define the facts the tombstones name that no recorder produces yet (§15) |
| P-19 | 02 §9 | If the Owner or the review rejects `Proj-Split` (F-45), hoist `let yt = &mut y[t];` above the inner `par for` in `q4_matmul`, so that D-D11 types without it |
| P-20 | 01 §2.5 FF-NANMAX | Decide whether `f64::max`, `f64::min` and `clamp` get the pinned choice; until then `nanrule` treats them as raw (F-51) |
| P-21 | 01 §13.4 T-Det, 01 §6.4 | Keep `d°` as "the scope with the block's own `nondet` removed", stated as the join of the free inputs' schedule components (F-32); add the first-order result premise (F-34) and block-level evidence subjects (F-33) |
| P-22 | 03 §6.2, 02 §12.3 | The port wrapper saves and restores MXCSR, status flags included, and runs each policy call in a reserved stack region of at least S(P) (F-48, F-58) |
| P-23 | 01 §6.1, 01 §13.6 | List the observers and the unlabelled nondeterminism sources this note adds: `{:p}` (Dc), bucket-order `HashMap` APIs (F-56); give Theorem 4's non-failing clauses their every-scheduler form (F-49) |
| P-24 | 01 §5.4, §5.6, §13.4 | Add loan sets and `E-BORROW-OUTLIVE`/`E-LOCAL-MUT-STORE` (F-39), closure summaries (F-35), jump grades (F-30), `¬Linear` by default and Linear closures (F-41) to the calculus sketch, or replace the sketch by this note (P-1) |

---

## 15. Tombstones

Ideas this note considered and rejected, in the format of DECISIONS §4. They are proposals: admitting
them to the ledger is an AUTHORITY operation that needs the Owner key (DECISIONS §1). Proposed burial
date 2026-10-16. Every trigger is written in the grammar of 06 §7.2.

```text
tombstone general_index_coverage_analysis {
    verdict: costlier                      // proving arbitrary loops write every element needs index reasoning v1 lacks (DR-012)
    scope:   { checker: mcore_v0, analysis: nan_strong_update }
    class:   E
    revisit_when: harness.dc_rate(construct: nan_raw_sink) > prereg(agent.dc_rate_bound)
    evidence: [core-calculus §5.9, F-1]
    // survivor: T-Cover, for loops that write each element exactly once, unconditionally, with no exit (F-37)
}

tombstone par_cooperative_cancellation {
    verdict: costlier                      // a poll at every back edge of every par body and its callees
    scope:   { construct: par_for, status: v0 }
    class:   E
    revisit_when: ledger.count(incident: par_join_divergence) > 0
               || harness.dc_rate(construct: par_early_exit) > prereg(agent.dc_rate_bound)
    evidence: [core-calculus §6.4, F-6]
    // survivor: termination-insensitive Theorem 4; mithi runs the serial projection
}

tombstone user_drop_impls {
    verdict: misleading                    // Rust runs Drop on unwind, or the process dies; Mithril does neither on a trap
    scope:   { construct: impl_drop, surface: mith_v0 }
    class:   F                             // under "a trap never unwinds and the host survives" (01 §12.1)
    revisit_when: owner.decision(trap_semantics) != no_unwind
               || harness.dc_rate(construct: drop_impl) > prereg(agent.dc_rate_bound)
    evidence: [core-calculus F-17] [01 §12.4]
    // survivor: linear struct, explicit consumption, audited abandon
}

tombstone multi_reference_elision {
    verdict: misleading                    // accepting a program Rust rejects, without a D construct, breaks DR-002
    scope:   { construct: return_ref_two_ref_params, surface: mith_v0 }
    class:   F                             // under the subset rule (DR-002)
    revisit_when: owner.decision(subset_rule) != in_force
               || harness.dc_rate(construct: multi_borrow_return) > prereg(agent.dc_rate_bound)
    evidence: [core-calculus §11 A-2] [DR-002]
    // survivor: return an index or a copy; a keyword-led projection form if the Surface Lab finds one
}

tombstone det_masks_outer_writes {
    verdict: unsound                       // masking every write inside a det block would launder taint the evidence never covered
    scope:   { construct: deterministic_block, version: mcore_v0 }
    class:   F                             // under "evidence covers only the block's result" (01 §6.4)
    revisit_when: has(rule: det_claim_covers_writes)
               || port.obligations_unexpressible(form: det_result_only) > 0
    evidence: [core-calculus §5.11, F-19]
    // survivor: result-only masking; writes keep their taint unless a future claim form lists them
}

tombstone generic_grades_after_monomorphisation {
    verdict: costlier                      // grade errors would surface at instantiation sites, far from their cause
    scope:   { checker: mcore_v0, feature: trait_generic_grades }
    class:   E
    revisit_when: harness.dc_rate(construct: trait_row_bound) > prereg(agent.dc_rate_bound)
    evidence: [core-calculus §5.12, F-12, F-50]
    // survivor: row- and observer-bounded trait transfers (Θ̂_m with O), checked once per generic body;
    // bodies generic over a closure type are re-typed per closure site (C-CLOMONO), which this does not cover
}

tombstone det_full_schedule_mask {
    verdict: unsound                       // erasing the whole schedule component launders taint the block's inputs carried in
    scope:   { construct: deterministic_block, version: mcore_v0 }
    class:   F                             // under "E shows the result is a function of the block's inputs" (01 §13.4)
    revisit_when: has(rule: det_claim_input_independent)
    evidence: [core-calculus §5.11, F-32] [review 2026-10-16, R1-2]
    // survivor: the result's schedule component is recomputed from the block's free inputs
}

tombstone core_trap_freedom_premise {
    verdict: costlier                      // P-tot forbade input-dependent traps that Theorem 3 does not need to exclude
    scope:   { theorem: timing_only_noninterference, premise: p_tot }
    class:   E
    revisit_when: port.obligations_unexpressible(form: p_ind) > 0
    evidence: [core-calculus §7.3, §8.3 N2, F-47] [review 2026-10-16, R1-17, R2-17]
    // survivor: P-ind, oracle-independence of the core's trap outcome; trap-freedom is one discharge of it
}

tombstone mut_local_param_ban {
    verdict: costlier                      // rejects &mut Iter<T> and similar parameters that rustc accepts
    scope:   { construct: mut_ref_to_local_param, surface: mith_v0 }
    class:   E
    revisit_when: ledger.count(incident: local_mut_store_escape) > 0
    evidence: [core-calculus §5.4, F-39] [review 2026-10-16, R2-1]
    // survivor: E-LOCAL-MUT-STORE, which rejects only stores of foreign loans, as rustc's elision does
}
```

Every class-F entry's trigger includes a disjunct that negates its assumption (DECISIONS §4): a
recorded Owner decision that traps may unwind or that the subset rule no longer holds, or a rule
(`has(rule: …)`) for a claim form that covers what the assumption says evidence cannot cover
(review item R2-28). `det_masks_outer_writes` was first classed T; its verdict is a soundness
verdict under an assumption, so it is F.

**Facts no recorder produces yet.** The following facts are in the grammar and in namespaces
DECISIONS §1 lists, and several fact families already appear in DECISIONS (`ledger.count(…)`,
`port.obligations_unexpressible(…)`, `owner.decision(…)`), but no recorder produces these parameter
values today. Each evaluates to `unknown`, which is reported and never fires (DECISIONS §1):

- `harness.dc_rate(construct: c)` for `nan_raw_sink`, `par_early_exit`, `drop_impl`,
  `multi_borrow_return` and `trait_row_bound`, outside the twelve constructs that the X1
  pre-registration enumerates (`docs/m0/prereg/X1-writability.md`);
- `ledger.count(incident: par_join_divergence)` and `ledger.count(incident: local_mut_store_escape)`;
- `port.obligations_unexpressible(form: det_result_only)` and `(form: p_ind)`;
- `owner.decision(trap_semantics)` and `owner.decision(subset_rule)`;
- `has(rule: det_claim_covers_writes)` and `has(rule: det_claim_input_independent)`, which are false
  until such a rule enters the catalogue, and so can fire only when it does.

§14 P-18 proposes defining each of them for the harness, the ledger and the Owner record.

---

## 16. Owner questions

No ROADMAP threshold is judged wrong. One ROADMAP wording is made more precise (Q1).

| ID | Question | Why it matters |
|---|---|---|
| Q1 | ROADMAP §3.6 says a policy trap "falls back to the default policy". This note reads that as the port's declared `fallback`, not a profile's default policy (§6.5, F-10). Is that the intended reading? | A profile default that is itself a policy can trap; the chain must end at a total fallback |
| Q2 | Should F-tot, P-ind, S-tot and A-ind become named obligations of the store-core certificate and its ports (P-2)? | The narrowing verdict of §8 depends on them; they add to M4's verification work, and A-ind has no discharge route yet (N11) |
| Q3 | Which allocation rule should X1 use: C-ALLOC (`alloc(Global)`), a label-free global heap, or arena-only tasks? | Every X1 family that allocates pays for it; the choice must be fixed before the card freezes. It is a language rule signed with this note, not a D0 item |
| Q4 | Do protocol atoms of the Tier 0 card (anchors, verbs, evidence policy, the `abandon` verb) satisfy "every Tier 0 rule traces back to the note" by tracing to 05 and 03 (§10)? | Otherwise the trace gate cannot pass, because these atoms have no calculus content |
| Q5 | Is a frozen prelude of declarations (derivations §P) an acceptable input to the gate "accepted by `mithi`"? | Canonical snippets reference declarations they do not contain |
| Q6 | The gate needs a Prover and an Adversary from another family. Until D0-10 names families, reviews are same-family only (docs/m0/README). Should the note freeze for X1 on same-family review, with the different-family review applied as an amendment from M1? | The X1 freeze (W3 in PLAN) comes before the different-family review (W5) |
| Q7 | "abandon" names both the agent verb and the trap-path release of linear values (F-20). Rename one before the Tier 0 card freezes? | Both may appear on the card |
| Q8 | `debug_assert!` is pinned to "always checked", like overflow (C-MACROS). Confirm? | It is a choice Rust permits, but it costs run time outside kernels |
| Q9 | The X1 design draft's agent subset rejects `par for`, `deterministic`, `schedule`, `spec` and `linear` with `E-X1-NOTYET`, but ROADMAP §3.6 needs `mithi` to accept every canonical snippet, which uses them (§12). Should `mithi` accept them typing-only (recommended), or does the Owner want to change the gate? | As drafted, the two documents cannot both hold; the note does not loosen the gate |
| Q10 | ROADMAP §3.2 requires agreement "on every canonical and derived snippet". Six derived snippets use constructs outside the checker's X1 scope (`flow`, `store`, `evolve slot`, MXFP4 format codes, `MemCap`). This note now includes them in agreement, with the expected X1 verdict `E-OUT-OF-SCOPE-<KW>` (§0.3, §12). Is that what "every derived snippet" means at X1, or should `mithi` type them (more checker work), or may they be excluded (which would loosen §3.2 and needs the Owner)? | The first draft excluded them silently, which the review found loosened §3.2 (R2-19). Until answered, they stay in agreement with these codes |
| Q11 | The review's counterexamples are supplementary items N-11 to N-39, reported and offered to the planted corpus, not gate items. Should any become gate items? | Making them gate items would add requirements ROADMAP §3.2 does not state; leaving them out means `mithi` could get them wrong without failing the gate |

---

## 17. Review log and signature block

| Date | Reviewer (lens) | Family | Scope | Findings by severity | Outcome |
|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 (adversarial soundness: counterexamples against the typing rules and the four theorems) | Claude (same family as author; independent context) | the note, derivations.md, verdicts.json | 23: 6 blocker, 13 major, 4 minor | 23 accepted (2 with a sub-claim rejected, below); 0 rejected |
| 2026-10-16 | Reviewer 2 (soundness plus conformance: gate record, ROADMAP thresholds, DECISIONS format, cross-document facts) | Claude (same family as author; independent context) | the note, derivations.md, verdicts.json | 30: 1 blocker, 18 major, 11 minor | 30 accepted (1 with a sub-claim rejected, 1 with its proposed placement declined, below); 0 rejected |

Totals: 53 findings, 7 blocker, 31 major, 15 minor [M: counted from the two reviewers' lists,
2026-10-16]. Every finding was checked against the sources named in it (01 §5–§7, §12, §13; 02 §8,
§9, §12; 03 §6.2; 06 §7.2; DECISIONS §1, §4; ROADMAP §3.2, §3.6; Hearth `b5d3f14` NUMERICS §3 and
INVARIANTS) before a fix was written. Findings that are true as stated were accepted; none was false
as a whole. By this reviser's reading [G], 15 of reviewer 1's items overlap an item of reviewer 2's in
whole or in part (for example writes through local references, `T-Cover` with a late exit, P-tot, the
policy stack); 8 of reviewer 1's items (R1-1, -2, -5, -10, -12, -13, -15, -23) and 14 of reviewer 2's
were found by one reviewer only.

**Disposition of each finding.** "R1-n" is reviewer 1's n-th item in the order of the review, "R2-n"
reviewer 2's. The F numbers are §0.5's; the N numbers are the supplementary items of derivations §N.

| Item | Severity | Disposition |
|---|---|---|
| R1-1 | blocker | accepted: F-30, `T-Jump`, N-11; D-C2 step 2 now cites the rule |
| R1-2 | blocker | accepted: F-32, `T-Det`, Lemma F, N-12; D-C5's conclusion now follows from the rule |
| R1-3 | blocker | accepted: F-35, closure summaries, `θ_inv`, N-13 |
| R1-4 | blocker | accepted: F-37, `T-Cover` premise 0, N-14 |
| R1-5 | blocker | accepted: F-38, `T-Par`'s exit context, condition (iii) restated, N-15; verifying it found F-31 |
| R1-6 | blocker | accepted: F-39, `target*`, N-16 |
| R1-7 | major | accepted: F-36, exercised row, N-17 |
| R1-8 | major | accepted: F-40, closure result discipline, N-18 |
| R1-9 | major | accepted: F-41, K-LinClo, std generics, N-19 |
| R1-10 | major | accepted: F-42, E6 and `lin_g` |
| R1-11 | major | accepted: F-43, publication points, N-21 |
| R1-12 | major | accepted: F-44, SSA facts, N-22 |
| R1-13 | major | accepted: F-45, `E-FOOTPRINT`, deferred re-check in `par`, N-23 |
| R1-14 | major | accepted: F-45, rule `Proj-Split`; D-D11 stays accept, now conditional on it; P-19 is the alternative |
| R1-15 | major | accepted: F-46, `det_E⟨e⟩` frame, runtime typing rules, `RT-Cover` |
| R1-16 | major | accepted: F-33, block-level subjects; prelude fixture names one definition |
| R1-17 | major | accepted: F-47, P-ind; sub-claim rejected (below) |
| R1-18 | major | accepted: F-48, (t9), S-tot, N10, N-38 |
| R1-19 | major | accepted: F-49, `E-Par-Join` rewritten, non-failing over every scheduler |
| R1-20 | minor | accepted: F-50, observer set O, `E-IMPL-GRADE`, N-39 |
| R1-21 | minor | accepted: F-51, total `nanrule` |
| R1-22 | minor | accepted: F-58, `proj(s)`, §8.2 reworded; sub-claim rejected (below) |
| R1-23 | minor | accepted: §7.1 proof plan names Env-Heap correspondence and restricted substitution and weakening |
| R2-1 | blocker | accepted: F-39, F-40, loan sets, `E-BORROW-OUTLIVE`, `E-LOCAL-MUT-STORE`, N-24 to N-27; proposed placement as gate items declined (below), Q11 |
| R2-2 | major | accepted (same defect as R1-6): F-39, address grade in `T-Assign`, N-16 |
| R2-3 | major | accepted (same defect as R1-4): F-37; conditions stated on the surface loop; no whole-p write |
| R2-4 | major | accepted: F-43, field loans re-check, N-28 |
| R2-5 | major | accepted: F-41, `¬Linear` by default, `E-LINEAR-INSTANTIATE`, N-20 |
| R2-6 | major | accepted: F-35, std higher-order transfers, N-29, N-30 |
| R2-7 | major | accepted: F-35, "mentions clo⟨κ⟩" in `T-Call`, N-31 |
| R2-8 | major | accepted: F-34, `E-DET-RESULT`, N-32 |
| R2-9 | major | accepted: F-33, hash-pinned subjects and fixtures, N-33 |
| R2-10 | major | accepted: F-36, `E-PAR-EFFECT` on the exercised row, Lemma B, N-34 |
| R2-11 | major | accepted: F-49, faults in the lowest-index rule, `demand(x)` defined on the serial projection |
| R2-12 | major | accepted: F-49, C-OOM, A-ind, N11 |
| R2-13 | major | accepted: F-51, conformance restated, `clamp` raw, P-20 |
| R2-14 | major | accepted: F-50 |
| R2-15 | major | accepted: F-53, side judgements on the monomorphised call graph |
| R2-16 | major | accepted (overlaps R1-18): F-48, `E-TO-STACK` |
| R2-17 | major | accepted (overlaps R1-17): F-47 |
| R2-18 | major | accepted: F-52, (s3'), N-35 |
| R2-19 | major | accepted: §0.3 agreement covers every item; `E-OUT-OF-SCOPE-<KW>`; Q10 |
| R2-20 | minor | accepted: §0.3 Pass row names the different family; protocol atoms cite note sections until Q4 (§10) |
| R2-21 | minor | accepted: `Tick` is `#[view]` in the prelude; `E-TO-PARAM`; D-C4, D-C8, D-D04, D-D06 marked conditional, and D-D07, D-D09, D-D14 and D-D21, which rely on the prelude in the same way |
| R2-22 | minor | accepted: F-54 |
| R2-23 | minor | accepted: F-58, Lemma 3b over every scheduler, MXCSR restored by the port, P-22 |
| R2-24 | minor | accepted: F-55 |
| R2-25 | minor | accepted: F-56, C-ATOMIC, C-FMT-ADDR, C-HASH widened, N-37 |
| R2-26 | minor | accepted: F-57 |
| R2-27 | minor | accepted (same defect as R1-14): F-45 |
| R2-28 | minor | accepted: F-negating disjuncts, `det_masks_outer_writes` reclassed F, unrecorded facts listed (§15); sub-claim rejected (below) |
| R2-29 | minor | accepted: §5.16 precedence order and `also` lists |
| R2-30 | minor | accepted: F-59, C-EXACT-STD, N-36 |

**Rejected parts.** No finding was rejected as a whole. These parts were not accepted:

- R1-17, sub-claim that P-tot is "inconsistent with its stated discharge": `may_trap = false` for the
  port-reachable core does imply P-tot, so the discharge was consistent; the defect is only that P-tot
  is stronger than needed, which is accepted.
- R1-22, sub-claim that the ⊥ formulation is "genuinely stronger, not merely notation": given §6.5's
  port, a hint stream that carries `F_q(s)` yields the decision `F_q(s)` whether `V_q` accepts it or
  not, because a rejected hint falls back to the fallback on the same snapshot. The first draft's
  reason ("a valid hint value") was wrong and is withdrawn; the conclusion holds for the
  same-snapshot reason, which §8.2 now states.
- R2-1, proposed placement of the four counterexamples as gate negative items: gate items are the
  negative examples inside the documents' snippets (§0.3), and adding constructed items would add
  requirements ROADMAP §3.2 does not state. They are supplementary items N-24 to N-27, and Q11 asks
  the Owner.
- R2-28, sub-claim that `port.obligations_unexpressible(…)` and `ledger.count(…)` are "not defined
  anywhere": both fact families appear in DECISIONS (DR-011's and DR-012's triggers). What is
  missing is a recorder for these parameter values, which §15 now lists.

Reviews still required by ROADMAP §3.6: a Prover and an Adversary from a model family other than
this note's author's (D0-10). Until then reviews are logged as same-family, independent-context
(docs/m0/README). This revision is DRAFT; the lead engineer freezes it.

```text
Owner: ______________________   Date: __________
Signs the note frozen at commit: ________
```

## Sources

- Mithril: [ROADMAP](../ROADMAP.md) §1, §3.2, §3.6, §4, §9, §11; [ARCHITECTURE](../ARCHITECTURE.md)
  §3, §5; [DECISIONS](../DECISIONS.md) DR-002 to DR-006, DR-010 to DR-013, DR-021, §1 and §4;
  [01-language](../architecture/01-language.md) (all); [02-compute](../architecture/02-compute.md)
  §1–§8, §12; [03-trust](../architecture/03-trust.md) §2, §3, §5, §6.2; [04-toolchain](../architecture/04-toolchain.md)
  §2, §6.4–§6.5, §9; [05-agent-protocol](../architecture/05-agent-protocol.md) §2, §3, §5, §13, §16;
  [06-forge](../architecture/06-forge.md) §2.1, §7.2; [07-hearth-port](../architecture/07-hearth-port.md)
  (snippets); research [G05](../research/G05-shared-mutable-state-memory-model.md),
  [R09](../research/R09-language-building-blocks.md), [revisited-ideas](../research/revisited-ideas.md)
  D2-A; proposals P2 §3.4–§3.5, P3 §3.4–§3.5, P5 §3.4–§3.5.
- Hearth `b5d3f14`: `engine/src/hx_quant.h` (block layouts), `docs/NUMERICS.md` §1–§5,
  `governance/INVARIANTS.md` (INV-DET-1/2/3, INV-SAFE), `engine/src/store.c` (`pick_victim`).
- Precedents named in 01 §13.1: Rust, Hylo, Swift SE-0446, Effekt and Austral, Cilk,
  information-flow typing and the Zdancewic–Myers timing factoring, sched_ext. This note did not
  re-read them. It adds one name from background knowledge, the syntactic progress-and-preservation
  method attributed to Wright and Felleisen (§7.1), and marks it as such.

## Amendments

None.

