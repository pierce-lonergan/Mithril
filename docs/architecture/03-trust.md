# 03 — Evidence and trust (the constitution)

Mithril accepts nothing about code on anyone's word, including its own compiler's. This document
makes that precise. Every definition carries typed **claims**; each claim is backed by **evidence**
whose admissible forms depend on the claim kind; evidence carries a **grade** stated relative to a
declared **trust base**; and every admitted fact lives, signed, in one content-addressed **ledger**
that never deletes and that invalidates automatically when code, spec, toolchain, target, hardware
or evaluator change. On that base sit **certified spaces** (classes of change proved
output-preserving once, checked mechanically per candidate), the verification tiers T0–T3 over an
owned, Zen-5-fuzzed x86 semantics table, a promotion rule that spends a project **α budget**,
separation of powers between agent roles, and a deterministic, code-only **Gatekeeper**. It closes
with the threat model, the canon migration protocol, the honest cost of a Dafny-class verifier, and an
inventory of everything trusted, with line budgets. The design is P2's trust model [P2 §5, §8] with
P4's ledger transport [P4 §8.11, §8.13] and P5's budgets and sequencing [P5 §5, §13].

**Contents**

1. The constitution in twelve articles
2. Claims and admissibility
3. Grade algebra and trust bases
4. The ledger
5. Certified spaces
6. Verification tiers T0–T3 and the semantics table
7. The promotion rule and the α budget
8. Roles, spec escrow and spec strength
9. The Gatekeeper and `abandon`
10. Documented reward hacks and their counters
11. Threat model
12. Canon version migration protocol
13. The honest cost of a Dafny-class verifier (DR-012)
14. What is trusted: TCB inventory and line budgets
15. Reviewer notes and open problems

Conventions. All syntax is provisional until the Surface Lab decides it
([05-agent-protocol.md](05-agent-protocol.md)). Status labels map to milestones exactly as in
[ROADMAP §1](../ROADMAP.md), rule 7: **v0**: in the mithc that ports Hearth (M1–M5); **v1**: present
by Edition 1 (M6–M7); **later**: planned after M7; **reserved**: in the types and schema but not
producible; **by-trigger**: added only when its register trigger fires (IDs D-nn in
[ROADMAP §9](../ROADMAP.md)). Milestone numbers are added where they help; M0 experiments that feed
v0 are written v0 (M0). Literature figures are as reported by their authors; my own numbers
are labelled [inference] or [target]. Decisions are DR-xxx in [../DECISIONS.md](../DECISIONS.md).

---

## 1. The constitution in twelve articles

A change to any article is an AUTHORITY change (§4.4) and needs an Owner-signed ADR.

| # | Article | Where |
|---|---|---|
| A1 | **No unchecked arrow.** Nothing produced by an untrusted component (front end, optimiser, backends including the C compiler for kernels, solvers, LLMs, the Forge) becomes evidence except through `mithcheck` or the measurement service, and only the gate admits it. | §4, §9 |
| A2 | **Every claim is typed and graded**: kind, property, spec hash, grade, trust base. An unlabelled performance number cannot be printed (`Quantity<Unit, Origin>`). | §2 |
| A3 | **Admissibility is per claim kind.** Correctness, performance and prune evidence never substitute for one another. | §2.2 |
| A4 | **Grades are relative to a declared trust base**, and every grade's derivation is queryable (`mithc ledger why --trust-base`). | §3.4 |
| A5 | **Prove the space, not the candidate.** Space soundness is trusted and checked per build on the binary; completeness-for-members is untrusted and tested; "unknown" means reject. | §5 |
| A6 | **Exact means bit-identical**, and tests never suffice for an exact kernel slot. | §2.2, DR-021 |
| A7 | **Speed is measured, never proved.** Every measured promotion test spends from an α budget that only the Owner replenishes. | §7 |
| A8 | **Powers are separated.** Whoever writes a spec never writes its implementation, the gate, the goldens or the clock. | §8 |
| A9 | **The judge is code.** The Gatekeeper is deterministic; LLMs hold roles, never verdicts; `abandon` is always a legal answer. | §9 |
| A10 | **Authority is a signature, never a sentence.** AUTHORITY facts need the Owner key; no text anywhere (prompt, comment, tombstone, diagnostic) grants authority. | §4.3, §11.2 |
| A11 | **Accumulate, never erase.** Facts are append-only; change makes evidence stale, never deleted; revocation propagates. | §4.5 |
| A12 | **The core is small, frozen, budgeted and attacked on purpose.** Growing the TCB needs an ADR; the Forge cannot write F0. | §14 |

---

## 2. Claims and admissibility

### 2.1 Anatomy of a claim

A claim is a typed statement about a **subject** (a definition's closure hash, or an object file's
hash for realisations), of a **kind**, under a **spec** (hash of the admitted spec item), for a
**slot** (a site whose manifest policy sets required grades). The Author role writes claims in sealed,
hash-locked `spec` items (§8):

```mith
/// Claims live in spec items owned by the Author role and hash-locked; Builders cannot edit them.
spec q4_matvec_claims for q4_matvec {
    claim refines(q4_matvec_avx512, q4_matvec) requires validated;     // T1 witness on the object
    claim refines(q4_matvec_avx2, q4_matvec) requires validated;
    claim perf(q4_matvec_avx512) requires measured
        noninferior(to: hearth_c_ref::mm_q4_avx512, margin: 3%);
}
```

`requires validated` is a floor on the claim's **effective** grade (§3.2), whatever its qualifier
(§2.3) unless the slot excludes one. The ledger records which evidence actually discharged the claim
and prints the code floor beside the grade (§3.4).

### 2.2 Claim kinds and admissible evidence (schema v0 from M1; each kind live once its check lands, M2–M6)

| Kind | Statement | Admissible evidence | Never admissible |
|---|---|---|---|
| `refines(impl, meaning)`, **kernel slot** (exact) | bit-identical on all inputs in the declared domain (§2.4) | proof (T1 witness + T2 certificates; Lean later) · validated | tested, assumed. An unmatched variant is `tested` and **not dispatched** in release profiles (DR-008, DR-021) |
| `refines`, non-kernel **logits-path** code | same | proof · validated · tested **plus** the cross-binary hash corpus, labelled as such (DR-021) | assumed |
| `refines`, other code | contract holds | proof · validated · tested (mutation score recorded) · assumed (Owner-signed, expiring) | — |
| `confined(space)` | the candidate is a member of the space | proof only: the T0 verdict on the binary | anything sampled |
| `safe` | no out-of-bounds access, no UB, and no trap where the `may_trap` fact is false (traps only at recorded trap sites, [01 §12](01-language.md)) | proof (types + T2); tested (ASan, fuzzing) outside kernels | in `kernel` code, anything but proof (DR-011) |
| `deterministic(scope)` | output is a function of the declared inputs at `scope` | proof · validated · tested (named golden + hash corpus) | — |
| `perf` | a quantity on hardware H against a named baseline | measured(hw, e-value, same-machine baseline) · bound(phys), one-sided | simulated, estimated (they rank, never promote) |
| `quality(profile)` | a statistical quality property: agent-interface fitness (F1-A, v1, M6); lossy profiles (reserved) | measured(corpus hash, e-value or CI) | — |

Prune evidence is a claim about a **bound**, not about the candidate; it has its own tiers (§3.1) and
admissibility rule (§7.4).

### 2.3 What each grade means

The panel rejected P1/P5's linear lattice, and P5's "proof means Lean only" left SMT-discharged
contracts unable to reach `proof`. This document adopts P2's semantics: the grade says *how* a
statement was established; *how far the checker is trusted* lives in the trust base (§3.4).

| Grade | Meaning | Examples |
|---|---|---|
| `proof` | established **by derivation** over all inputs: a decision-procedure verdict, or a certificate re-checked by a trusted checker | T0 verdict; T1 witness replayed by `mithcheck`; T2 LRAT or Alethe/CPC certificate re-checked; Lean term through a Comparator-style gate |
| `validated(q)` | established **by execution** over a complete finite domain, a declared case partition, or a declared bound; the qualifier `q` is mandatory | `validated(exhaustive)`: all 2^32 binary32 inputs of a unary function · `validated(partition)`: a table entry run on silicon over every declared case class (§6.7) · `validated(bounded: depth 6, n_slots ≤ N, threads ≤ T)`: a bounded model check of the store core |
| `tested` | sampled inputs with a recorded adequacy measure | differential tests against `mithi`; goldens; hash corpus; property tests with a mutation score under a named fault model |
| `assumed` | Owner-signed assertion with an expiry | trust-base axioms; temporary waivers |

These grades describe the **form** of the evidence. A slot compares the **effective** grade (§3.2),
which also takes the meet with the premises the derivation used. A T1 witness is `proof` in form. Its
effective grade is `validated(partition, …)`, because it rests on silicon-validated table entries and
on the rewrite list. That is the grade that [01 §13.7](01-language.md), [04 §7.2](04-toolchain.md) and
DR-021 state.

**The `validated` qualifier is part of the claim's printed statement**, because the three forms
establish different things:

- `exhaustive` covers every input. Nothing is extrapolated.
- `partition` runs representatives of each declared case class (for example, binary FP operations,
  whose domain is 2^64). Uniformity within a class is **assumed, not shown**. That assumption is a
  trust-base axiom (§3.4, §6.7).
- `bounded: …` covers every behaviour up to the stated bound, and the claim **holds only up to that
  bound**. It extends past the bound only if a cutoff or small-model argument is admitted as its own
  claim. Until then the bound appears wherever the claim is printed or cited (§3.3).

The meet keeps the union of the qualifiers of every `validated` input, so an effective grade such as
`validated(partition, exhaustive)` names everything it rests on. A slot may exclude a qualifier, for
example `refines = "validated(exhaustive|partition)"`.

A `tested` grade without an adequacy measure is inadmissible: Hearth's council found a mutant reporting
3,071,655 GB/token that passed all 112 tests [RV: D2-E].

### 2.4 Declared domains and the C seam (v0, M1–M2)

A `refines` claim quantifies over its **declared domain**. That domain is made of:

- the parameter refinements (`#[range]`);
- struct invariants and `requires` clauses;
- the non-overlap of buffers that exclusive `&mut` implies.

For `q4_matvec` the domain is:

- `a[*].q ∈ [−127, 127]`, because the `vpsignb` sign trick fails at −128;
- `a[*].sum == Σ a[*].q`, because the integer-ring rewrite of §6.3 reads `sum`;
- `a.len() == w.blocks_per_row()` and `y.len() == w.rows()`, the `requires` of the canonical
  `q4_matvec` ([ARCHITECTURE §5.3](../ARCHITECTURE.md)); `Matrix::row` ensures
  `result.len() == self.blocks_per_row()`, so `w.row(r).len() == a.len()` follows;
- `y` disjoint from `w` and `a`, which `restrict` (DR-027) and T1's separate symbolic arrays (§6.3)
  assume.

The domain is part of every `refines` claim's printed statement (§3.4).

Inside Mithril, every call site discharges the domain statically ([01 §9.1](01-language.md)).
Some callers are not Mithril:

- the `hx_*` seams during the strangler-fig port;
- `export abi` entry points;
- later, Python through ctypes.

At such a **seam** nothing checks the domain. An out-of-domain input makes a certified variant
diverge from its meaning, or reaches C undefined behaviour. So every seam entry into Mithril code
does one of two things:

1. **It checks the domain at run time**, in the seam wrapper, outside kernel code. Lengths,
   alignment and non-overlap cost O(1). Value refinements and invariants cost one O(n) pass over the
   inputs. A failure is a trap in the export's fail domain and returns its declared error code
   ([01 §12.2](01-language.md)). This is the default. For `q4_matvec` the pass reads the activation
   once, which is small next to the weight matrix [inference]. A debug-only check is allowed only if
   `ledger why` grades the seam `assumed`.
2. **It carries an Owner-signed `assumed(caller_contract)` axiom** that names the seam and the
   domain. Like any `assumed` fact, it expires. It appears in the trust base of every claim that
   crosses the seam.

The seam rule's surface belongs in [01 §11](01-language.md) and [04 §6](04-toolchain.md). This
section fixes what the trust model requires of it.

---

## 3. Grade algebra and trust bases

### 3.1 Three property kinds, never mixed (DR-007)

| Property kind | Order | Used for |
|---|---|---|
| Correctness | `proof > validated > tested > assumed` | `refines`, `confined`, `safe`, `deterministic` |
| Performance | `measured(hw) > simulated > estimated > assumed` | `perf`, `quality` |
| Bound tier | `phys > emp(audited) > est` | prune and quarantine |

There is no meet across kinds: `meet(validated, measured)` is a schema error, because a measurement is
evidence about a different property, not weak evidence of correctness. Only `phys` and audited `emp`
bounds may prune or quarantine; `est` may only rank [RV: D3-ii]. An audited `emp` term acts only
through `emp_bound`, and a result between `emp_bound` and `phys` is flagged for audit, not
quarantined (§7.4, [02 §13.2](02-compute.md)).

**Every composition moves toward the weaker element.** Correctness and performance grades put the
best element at the top, so composition takes the **meet**. Fidelity and determinism scope (§3.2) put
the best element at the bottom, so composition takes the **join**. These are one rule.
[01 §7.2](01-language.md) calls the meet a "sign error" for the value grades, and that does not
conflict with the meet used here.

### 3.2 Effective grade

For a correctness claim `c`:

```text
eff(c)   = ev(c)                                 -- grade of the evidence form that discharged c (§2.3)
         ⊓ cap(strength(spec(c)))                -- spec-strength cap (§8.4): the only strength check
         ⊓ ⨅ { grade(b) | b ∈ B(o) }             -- value-level claims about an output o only (data flow, 01 §7.2)
         ⊓ ⨅ { eff(d)   | d a claim c depends on: T2 obligations, callee claims }
         ⊓ ⨅ { grade(p) | p a premise component in TB(c) }   -- table entries, rewrite rules, space basis
floor(c) = ⨅ { grade(k) | k a code component in TB(c) }      -- checkers, T0 pass, elaboration
TB(c)    = TB(ev(c)) ∪ ⋃ TB(d)
```

**This is the one normative rule.** It is the outline's meet (evidence, spec strength, boundaries),
extended by the **premises** a derivation uses. A T1 witness is a derivation from table entries and
rewrite rules, so its conclusion can be no stronger than they are.

**The boundary term follows data flow** ([01 §7.2](01-language.md)).
It is ⨅ grade(b) for b ∈ B(o), where `B(o)` is the set of `deterministic` boundaries (§3.3) that the
output `o` depends on by data flow. It applies to **value-level claims** only:
`deterministic(scope)` of an output, and end-to-end logits claims. **Input-universal claims**
(`refines`, `confined`, `safe`) quantify over all inputs and exclude upstream boundaries: a boundary
that produced a kernel's input bytes cannot weaken its `refines` claim. A boundary *inside* the
claim's subject still counts, through the subject's own dependencies (the `eff(d)` term). A
call-closure reading would cap every kernel whose closure reaches `acquire` at `tested` and break
DR-021.

The **checker** that replayed the derivation is not a premise. Like the Lean kernel for a Lean term,
it is the engine relative to which the grade is stated. Its grade, and the grade of every other code
component, forms the **code floor** `floor(c)`:

- It is printed beside every effective grade. A bare effective grade is unprintable, as an unlabelled
  `Quantity` is (A2).
- Slot policies compare it against `code_floor` (§3.5).

Both alternatives fail:

- Meeting the code components as well would make every claim `tested` until the checkers are
  mechanised (ROADMAP D-08), so DR-021 could not be satisfied.
- Leaving them out of the printout would overstate assurance.

Two results under this rule:

- **A kernel.** A T1 witness over `validated(partition)` table entries yields an effective
  `validated(partition, …)` with `code floor: tested`. This matches [01 §13.7](01-language.md),
  [04 §7.2](04-toolchain.md) and DR-021.
- **A policy.** The T0 verdict on the binary is `proof` in form. Its effective grade is
  `validated(partition)` from its table premises. A `confined(S)` claim also has S's soundness basis
  among its premises, because slots read it as output preservation (A5), so for `confined(S)` it is
  `validated(bounded: …)` via the store-core theorem. The code floor, `tested`, is printed and not
  met. This is the reading that [ARCHITECTURE §8.1](../ARCHITECTURE.md) and DECISIONS reviewer note 3
  asked for, and it satisfies the `confined = "validated"` slot of §3.5.

Performance claims combine the same way within their kind (a `perf` claim against a stale baseline
is stale). Two value-level grades travel in types, not in the ledger, and compose by **join** (the
lossier wins): fidelity `exact ⊑ real(bound) ⊑ approx(profile)` and determinism scope `cross_device ⊑
device(t) ⊑ schedule_dependent` ([01-language.md](01-language.md)). `real(bound)`, `approx` and
`device(t)` are **reserved**.

### 3.3 Deterministic boundaries propagate their grade

`deterministic(by: E) { … }` removes only `nondet` (results become `blob`-grade), never authority
effects. It needs a DeclareDeterministic manifest grant, cites evidence `E`, passes `E`'s grade
downstream, and loses its licence when `E` goes stale.

```mith
/// Thread timing and cache state are nondeterministic inside; the bytes returned are a function
/// of the immutable, content-hashed file. Authority (io, spawn) stays visible to callers.
fn acquire(store: &Store, id: ExpertId) -> Result<Frozen<SlabBuf>, IoError> uses { io, spawn } {
    deterministic(by: golden::scheduling_independence) {
        store.acquire_inner(id)          // Err only from an environment fault (HX_E_IO, O5)
    }
}
```

This is the canonical form of [ARCHITECTURE §5.3](../ARCHITECTURE.md) and
[02 §12.1](02-compute.md): an I/O fault surfaces as `Err`, never as a trap, as O5 and Theorem 3
([01-language.md](01-language.md)) require.

As written, the boundary cites a named golden test, so every logits-path `deterministic` claim that
crosses it is at most `tested`. Later the store-core theorem (O1–O5, [02-compute.md](02-compute.md))
is admitted at `validated(bounded: depth 6, n_slots ≤ N, threads ≤ T)`, from the bounded model check
of [02 §12.4](02-compute.md), the chaos suite and 100% core-mutant kill (DR-010). The Author then
changes the citation to `deterministic(by: store_core::output_noninterference)`. The downstream
grade rises to that grade, **bound included**, with no other edit.

INV-DET-1 for the store path is therefore honestly `validated(bounded: …)`, not `proof`. The ledger
prints the theorem as "output noninterference up to depth 6, n_slots ≤ N, threads ≤ T". N and T are
fixed by the certificate's model hash [target]. The bound goes away only in one of two ways:

- a cutoff or small-model argument is admitted as its own claim;
- the theorem is mechanised (by-trigger, ROADMAP D-08).

### 3.4 Trust bases

A trust base is what a grade depends on but does not check. It has three parts, and it also prints
the runtime-checked entries a claim relies on:

- **Axioms.** These are assumed and never graded higher. They are printed, never met and never
  floored:
  - the target CPU conforms to the table on the case classes used, uniformly within each class
    (§6.7);
  - the microcode and the OS;
  - the human Owner;
  - the Lean kernel, once used;
  - the C compiler for non-kernel code (§14);
  - Owner-signed `assumed(caller_contract)` entries at seams (§2.4).
- **Premise components.** These are facts a derivation uses, each with its own ledger grade, and they
  enter the meet of §3.2:
  - each semantics-table entry used;
  - each rewrite rule used;
  - a space's soundness basis, such as the store-core theorem.
- **Code components.** This is trusted code that decides or produces what is checked, and it forms
  the code floor:
  - the `mithcheck` T1 build, its lifter and loop rules (§6.4);
  - the T0 pass;
  - the T2 certificate checker;
  - the elaboration of exact meanings into KIR, comptime included (§14). In v0 it is trusted code
    with code floor `tested`, mitigated by the second comptime evaluation path. The by-trigger
    kernel-subset extractor inside `mithcheck` (§14, ROADMAP D-23) would remove it from the trust
    base;
  - the audited `std_platform`, which sits in the store-core theorem's trust base (§5.2).
- **Runtime-checked entries.** These are preconditions that the runtime establishes and checks on
  every execution. They are printed in the trust base, but they are not axioms, not discharged
  obligations, and they are neither met nor floored:
  - **default MXCSR.** The default MXCSR is set on entry and restored on exit at every `export abi`
    and `hx_*` entry, and set and asserted at pool-worker start
    ([ARCHITECTURE §6.3](../ARCHITECTURE.md), [04 §9.2](04-toolchain.md)). Every T1 certificate
    records it as a precondition checked at entry;
  - seam domain checks at run time (§2.4).

Grades are stated **relative to** the trust base. A slot policy sets a `code_floor` that `floor(c)`
must reach.

This also reconciles two instructions. "`confined` admits proof only" constrains the evidence *form*:
a T0 verdict on the binary, never samples. The panel asked that confinement be recorded as `tested`
until it is mechanised. That is the code floor, `tested`, printed beside the effective
`validated(bounded: …)`. The T0 pass earns its `tested` grade from the planted corpus, core mutants
and the `mithi` differential, and timing_only slots set `code_floor = "tested"` until ROADMAP D-08
fires.

```text
$ mithc ledger why hearth::quant::q4_matvec@x86_64-v4 --trust-base
refines(q4_matvec_avx512 -> q4_matvec)        proof          T1 witness sha256:77d2… (evidence form)
  on domain  a[*].q ∈ [-127,127] · a[*].sum = Σq · a.len = w.blocks_per_row · y.len = w.rows · y ∩ (w ∪ a) = ∅
  ⊓ spec q4_matvec_claims                     uncapped       executable meaning (intent vs numpy_ref: tested)
  ⊓ T2 |isum| <= 65_024 < 2^24                 proof          Alethe cert sha256:…, re-checked by mithcheck-t2
  ⊓ T2 footprint: stores ⊆ y, loads ⊆ w ∪ a    proof          cert sha256:… (§6.3)
  ⊓ premise rewrite list v1, n rules used      validated(exhaustive, partition)  (enumeration + two solvers)
  ⊓ premise semantics entries used: n          validated(partition)  (9950X case classes + Bochs)
  = effective                                 validated(partition, exhaustive)  relative to tb:sha256:c3e9…
    code floor                                tested         (mithcheck-t1, mithcheck-t2, elaboration)
trust base tb:sha256:c3e9…
  axiom  target CPU conforms to the table on the case classes used, uniformly per class
         (validated on Zen 5 9950X, microcode …)                                              assumed
  check  default MXCSR: set on entry, restored on exit at every export abi / hx_* entry;
         set and asserted at pool-worker start (§3.4)                                 runtime-checked
  code   mithcheck-t1 @sha256:… (lifter, loop rules)     tested   (planted corpus, core mutants)
  code   mithcheck-t2 @sha256:…                          tested   (malformed-certificate corpus)
  code   elaboration to KIR, comptime included           tested   (second evaluator agrees; mithi differential)
  check  seam hx_q4_matvec (C callers): domain checked at entry, O(n) over a (§2.4)
  not in base: MSVC/Clang (object audit), schedule primitives (completeness only), SMT solvers (certificates)
```

### 3.5 Slot policies in the manifest (v0, M2–M4)

Slot requirements are data in `mith.toml`, changed only by AUTHORITY facts:

```toml
[slots."hearth::quant::*"]          # exact kernels (DR-021)
refines = "validated"               # effective grade (§3.2): T1 witness ⊓ table entries ⊓ rewrite rules
code_floor = "tested"               # mithcheck unmechanised until ROADMAP D-08/D-09; elaboration in the TCB until the D-23 extractor
perf = { grade = "measured", baseline = "hearth_c_ref", margin = "3%" }   # DR-018

[slots."hearth::store::policy::*"]  # timing_only space
confined = "validated"              # form must be a T0 verdict (§2.2); effective via the store-core theorem
code_floor = "tested"               # T0 pass unmechanised until ROADMAP D-08 (DR-010)
promote = "profile"                 # standing grants only; defaults need an ADR (DR-015)
```

Grades and floors are evaluated against the **build machine's fingerprint**, both at build time and
when the release dispatch table is generated. Other machines are covered by the conformance axiom
and the load-time self-test (§6.7).

This makes INV-HONEST a link rule (perf claims need `measured(hw)` against a named same-machine
baseline), INV-DET-3 a dispatch rule (release dispatch tables are generated from ledger queries) and
INV-LOSSLESS-DEFAULT a link error (no `approx` default).

---

## 4. The ledger

### 4.1 Fact schema (v0: local ledger at M1, signed ledger at M3)

A fact is a canonical, deterministically serialised record named by the SHA-256 of its bytes. The gate
signature covers that hash; git's own object hash is not relied on for integrity.

| Field | Content |
|---|---|
| `type` | `claim` · `evidence` · `tombstone` (a claim with verdict `reject`, [06-forge.md](06-forge.md)) · `handover` · `grant` · `adr` · `authority` · `revoke` · `seal` |
| `key` | `H(code closure, spec hash, toolchain hash, target, hardware fingerprint)`; hardware is empty for correctness claims, whose silicon dependence lives in the trust base |
| `claim`, `kind`, `property`, `verdict` | §2.2; verdict `accept`, `reject` or `unknown` (unknown satisfies no slot) |
| `grade`, `trust_base`, `evidence` | §2.3, §3.4; evidence as blob hashes (certificates, witnesses, samples, fuzz records) |
| `evaluator`, `scope` | measurement-service build and protocol hash; a predicate in the decidable scope language shared with tombstones |
| `provenance`, `cost` | principal, role, model family and version, prompt hash; tokens, CPU-seconds, wall-seconds |
| `notes` | optional free text, length-capped, flagged untrusted (§11.2) |
| `sig` | gate signature; AUTHORITY facts also carry the Owner's |

Status (`live`, `stale`, `quarantined`) is never stored. It is a Fact Plane view over the facts and the
`revoke` facts, so the store stays monotone [P4 §5.3].

### 4.2 Storage (DR-019)

- **Admitted facts** are gate-signed files named by hash under `.mith/ledger/`, committed to git and
  union-mergeable: two agents that create the same fact create the same file [P4 §8.11]. Files are
  sharded by hash prefix [inference].
- **Raw samples, certificates, witnesses and fuzz records** are content-addressed blobs in the data
  directory, outside the repository and outside cloud-synced folders (Hearth's INV-DATA pattern).
  Certificate and witness blobs that admitted facts reference are mirrored to an artifact store CI can
  read, so CI can replay them (§11.4) [inference].
- **Checkpoints (v0, M3).** A SEAL operation records the ledger's Merkle root. Compromise recovery
  relies on it (§11.4).
- **Compaction (by-trigger, ROADMAP D-13).** The trigger is "git on `.mith/ledger/` exceeds the CI
  budget". When it fires, a SEAL operation packs older facts into a signed segment, under the
  checkpointed Merkle root. Segments preserve membership, so compaction is not deletion. This answers
  a judge's warning that millions of tiny files scale poorly in git on Windows.

### 4.3 Signing (v0, M3)

| Key | Holder | Signs |
|---|---|---|
| Gate key, one per machine | the gate principal, which agents cannot read (§11.3) | admitted FREE and SEAL facts |
| CI key | CI runners | `reverified` facts: independent replay of certificate-backed evidence |
| Owner key (primary + offline backup) | the human Owner, on hardware tokens | AUTHORITY facts |

Every read verifies signatures against `.mith/trust/roots.toml`, which changes only through an
AUTHORITY fact signed by a key it already lists.

### 4.4 Operation classes

CALM says *when* agreement is needed; AUTHORITY says *who* gives it [RV: D2-F].

| Class | Operations | Coordination | Status |
|---|---|---|---|
| **FREE** (monotone) | add a definition, evidence, a verdict, a tombstone, a candidate, a measurement, a handover, an `abandon`, a contract *extension* | none: union merge | v0 (M3; local ledger from M1) |
| **SEAL** (non-monotone, mechanical) | bind a name in `mith.lock`, release a version, evict from a profile, checkpoint, close an α period; compact (by-trigger, D-13) | sequenced by the machine's gate; the heavier sequencer and typed conflict holes are by-trigger (D-13) | v0 (M3) / by-trigger |
| **AUTHORITY** (normative) | admit or amend specs and goldens; change defaults (ADR); grants; replenish α; admit a canon version; amend the TCB or table; grant DeclareDeterministic / `unsafe` / `foreign`; contract *weakenings*; release quarantine; rotate keys | Owner signature | v0 (M3); grants v1 (M6) |

A contract weakening opens typed holes in every dependent, FFI mirrors included; this would have caught
Hearth's `read_errors` ABI break [RV: D2-F].

### 4.5 Invalidation, revocation, quarantine

Facts about old hashes are never invalidated; they describe old code, and lookups for the current
closure miss them. These events change the status of facts that still match:

| Event | Effect |
|---|---|
| Toolchain hash changes | old-toolchain facts stop matching; the instruction census reruns (§6.6) |
| Trust-base component revoked (entry fails re-fuzz, rule withdrawn, checker bug) | `revoke` fact; dependent facts `quarantined`; certificate-backed ones are re-checked under the fixed component and restored if they pass |
| Evaluator hash changes | perf and quality scores under the old evaluator go stale (IF-4 [P4 §8.13]) |
| Hardware fingerprint changes (CPU, microcode, BIOS memory settings, drives, power plan) | measured facts and machine-profile prune certificates stop applying [RV: D3-ii] |
| Spec amended | new spec hash; old evidence keeps pointing at the old one |
| Boundary evidence stale | the `deterministic` boundary loses its licence; downstream claims drop (§3.3) |
| Canon version admitted | §12 |
| Measurement beats a sound bound | candidate quarantined; evaluator and bound audited (§7.4) |

Quarantined facts satisfy no slot. Revocation propagates along Fact Plane dependency edges.

---

## 5. Certified spaces

### 5.1 Soundness versus completeness-for-members

A **certified space** is a typed class of modifications that the trusted core shows, once, cannot
change outputs. Two properties are kept apart [P2 §5.3]:

- **Soundness (trusted):** every candidate the space's check accepts preserves outputs. It is checked
  per build, on the emitted binary, and only it enters the ledger.
- **Completeness-for-members (untrusted, tested):** every legitimate member passes the check. A
  completeness failure costs search time, never correctness.

For schedules, a Lean proof that each primitive preserves the op-DAG gives **completeness only**: it
predicts that T1 will accept. Soundness comes from T1 on the binary the C compiler emitted. A wrong
primitive proof still meets T1's rejection; an incomplete T1 rejects a correct schedule and names the
correspondence that failed.

### 5.2 The spaces

| Space | What may change | Soundness basis (once) | Per-candidate check | Status |
|---|---|---|---|---|
| `timing_only` policy | eviction, prefetch, I/O order, mirror choice, pinning, thread mapping | store-core theorem O1–O5 against demonic hints, `validated(bounded: …)` (DR-010, §3.3) | T0 on the binary (§6.2): ms [target] when the SFI pattern survives, re-derived after X0; seconds on the SSA route | v0 (M4) |
| `schedule` for an exact meaning | tiling, disjoint parallel split, fixed-lane-count mapping, unrolling, prefetch distance, integer reordering licensed by range proofs | none trusted beyond per-build T1 + T2 | T1 witness + T2 certificates (seconds) | v0 (M2) |
| `relayout` (lossless) | repacking weights into kernel-native layouts | derived pack/unpack are inverses | round-trip check per instance | v0 (M2); Forge search v1 (M6) |
| agent-interface artifacts (F1-A) | card atoms, diagnostic templates, hole and pack ranking, scaffolds | not in any program's build closure (Fact Plane query) | closure disjointness; fitness is `quality(harness)` | v1 (M6) |
| `placement` under `cross_device` | CPU versus GPU for expert GEMV | kernels T1-validated on both backends; ptxas/driver JIT in the trust base, SASS level `tested` (DR-022) | the kernels' own claims | by-trigger (owner-gated) |
| `refines(spec)`, free body | anything | none | full certificate; **tests never suffice** | v0 (M2) |
| `real(bound)` | reassociation, FMA, approximate transcendentals | bound calculus | T3 certificate + runtime margin checks | reserved |
| `approx(profile)` | lower-bit cold experts, dynamic k | none | quality certificate; Owner opt-in; never a default | reserved |

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

Two constitutional points about the store-core theorem (stated fully in
[02-compute.md](02-compute.md)). A policy trap or fuel overrun **falls back to the default policy**
and never returns `Err`; otherwise a policy could deny service through the `Err` branch of the
noninterference statement. `Err` comes only from the device (I/O failure → `HX_E_IO`). And because the
core runs over the audited `std_platform` layer, that layer is in the theorem's trust base.

### 5.3 Incompleteness is accepted; unsoundness is not

Rice's theorem guarantees that some true improvements fall outside every space. They need a
per-candidate `refines` certificate or they are not promotable. A space is a fast path, not the only
door [P4 §8.4]. The prize must be stated honestly: the revisit node expects eviction gains of a few
points at most, prefetch timing to be the bigger lever, and assurance to be the durable win
[RV: D2-A]. The largest wins on this machine change outputs and belong to the reserved `approx` lane.
Certified spaces make search safe and cheap; they do not raise the memory-bound roofline.

---

## 6. Verification tiers T0–T3 and the semantics table

### 6.1 Overview

| Tier | Decides | Grade | Status |
|---|---|---|---|
| T0 | types, effects, ownership, grades (front end; advisory for policy/evolve code) + **binary-level confinement** for policy/evolve code | `proof` form; effective `validated(partition)` from table premises; for `confined(S)`, `validated(bounded: …)` via the store-core theorem; code floor `tested`, printed, not met (§3.2) | v0: front end from M1, binary pass at M4 |
| T1 | FP-DAG matching of lifted object code against the KIR meaning, modulo an audited exact-rewrite list, using schedule-supplied correspondence maps, plus a memory-footprint check; near-linear in unrolled DAG size [R07] | `proof` form for `refines`; effective `validated(partition, …)` through table and rewrite-list premises; code floor `tested`, printed, not met (§3.2) | v0 (M0): X2 spike · v0 (M2): object audit |
| T2 | bit-vector obligations: ranges, overflow, saturation, alignment, mask extraction, address bounds, simple integer contracts | `proof` (certificate) | v0 (M2) |
| T3 | tolerance certificates + runtime margin checks | lossy-labelled | reserved (ROADMAP D-07) |
| Tests, measurement | sampled correctness; runtime-owned measurement | `tested`; `measured(hw)` | v0 |

The pipeline that produces lifted objects (XED decode → LIR, caching by closure hash, CI latency) is in
[04-toolchain.md](04-toolchain.md). This section says what the checks mean and why they are sound.

### 6.2 T0: confinement on the binary

For policy and evolve code the front end's effect checker gives fast feedback but is advisory. The
ledger verdict comes from a check over the decoded objects of the candidate's whole closure
[P2 §5.2]. That check must establish Lemma 3a ([01 §13.6](01-language.md)) on machine code:

- a call reads only its inputs;
- it writes only its state block and its own stack frame;
- it leaves no ambient machine state changed;
- it returns, or is cut off, within its fuel.

An instruction allowlist plus a store rule does not give that. Unrestricted loads can read a clock
with no banned instruction. Windows maps KUSER_SHARED_DATA, with tick and interrupt time, at the fixed
address 0x7FFE0000, and the TEB is reachable through `gs:`. A stray stack store can overwrite the
return address. An exit with DF set breaks the core's `rep movs` and `memcpy` [inference]. So T0 has
six parts:

- **Instruction allowlist.** RDTSC, RDTSCP, RDPMC, CPUID, syscalls, and indirect calls and jumps are
  banned. So are STD, POPF/POPFQ, LDMXCSR/VLDMXCSR, FLDCW, FLDENV, FRSTOR and any other x87
  control-word write. Because it is an allowlist, state-restoring instructions (FXRSTOR, the XRSTOR
  family) and nondeterministic sources (RDRAND, RDSEED) are excluded without being named [inference].
  `fs:`/`gs:` segment overrides and absolute addresses are rejected as operands.
- **Memory confinement, loads and stores alike (SFI).** `mithc` lowers every policy so that each
  non-stack load and store addresses one **policy arena** as base plus masked index,
  `[arena + (idx & mask)]`, with a power-of-two arena size. The arena holds the read-only snapshot
  the port passes in and the state block. Loads may use the whole arena; stores use a second mask
  that covers only the state block. Stack accesses follow the stack discipline below, and RIP-relative
  loads from the object's own read-only constants are also allowed. T0 checks the pattern
  syntactically on each memory operand, so this route stays a linear pass. The C
  compiler may drop a mask it can prove redundant. In that case T0 bounds the computed address using
  the T1 lifter's SSA and T2 range certificates instead, which costs seconds rather than milliseconds.
  An address that neither route bounds is rejection. Confining loads keeps payload bytes and core
  memory out of the policy's reach. It also keeps the `time`-free claim, hack #14's counter and
  `timing_blind` replay (§7.4) sound.
- **Stack discipline.** RSP changes only by constant prologue and epilogue adjustments, and it is
  balanced on every exit path. Stack stores use constant RSP offsets strictly below the return-address
  slot, within the frame that the prologue allocated.
- **ABI conformance on every exit**, checked over the lifted SSA:
  - Callee-saved registers hold their entry values. On Win64 these are RBX, RBP, RDI, RSI, R12–R15
    and XMM6–XMM15. On SysV they are RBX, RBP and R12–R15.
  - DF is clear: STD is banned and CLD is allowed.
  - No instruction writes RFLAGS.AC, MXCSR or the x87 control word.
- **Fuel.** Every CFG back-edge passes through a fuel decrement whose exhaustion traps to the
  fallback. The fuel cell lies outside the policy arena, and the recognised decrement is the only
  instruction that writes it.
- **Calls** go only to direct targets inside the T0-checked closure.

**Pinned flags for policy translation units** [inference; [04](04-toolchain.md) owns the flag table]:

- MSVC gets `/GS-` (no `__security_check_cookie`) and `/guard:cf-` (no CFG dispatch call).
- Clang and GCC get `-fno-stack-protector -fcf-protection=none -fno-stack-check -ffreestanding
  -fno-jump-tables`.
- Frames stay below the stack-probe threshold, so no `__chkstk` call is emitted. A larger frame fails
  T0.
- Any `memcpy` or `memset` that the compiler synthesises resolves to freestanding implementations
  inside the closure.
- A switch that still lowers to a jump table fails T0, because the jump is indirect.

The flags are part of the toolchain hash, so changing them reruns T0.

The check blocks four classes even if the C compiler or an intrinsic introduces something the front
end did not see:

- timer overwrite;
- FP-environment changes;
- clock reads through mapped memory;
- corruption of ABI state.

It reuses the object audit's decoder and lifter. Its cost, milliseconds per policy when the SFI
pattern survives compilation, is a [target]. The X0 census re-derives it for policy translation
units.

### 6.3 T1: IEEE-exact DAG matching

T1 symbolically executes meaning and implementation at each point of a correspondence map, hash-conses
both FP DAGs, and requires every FP operation to correspond one-to-one, same operands, same order, up
to the rewrite list. Integer subterms become T2 obligations. The output is a witness (lane map,
register-to-value map) that makes re-checking linear [R07, P5 §5.2]. **Correspondence maps are
untrusted hints**: schedules emit them, and for hand-written intrinsics a `#[lanes(...)]` annotation
supplies them [P5 §4]. A wrong map only causes rejection, so the checker is useful before the schedule
language exists ("validate the output, not each rewrite").

**The footprint (frame) check.** Matching output DAGs is not enough. A miscompiled kernel that also
writes past the end of `y`, or loads out of bounds, still matches every output DAG. Hearth had three
one-past writes into SIMD arrays that escaped every tool (T02 [R11]). So T1 also proves three things,
with T2 certificates:

1. **Stores.** Every store in the lifted code is one of two kinds. It is a frame-local spill (§6.4),
   or it lands in a declared output buffer at a location the meaning writes. The final value stored
   at each such location is the one the correspondence matches. No store falls outside the
   correspondence.
2. **Loads.** Every load reads one of three places: a declared input or output buffer within its
   bounds, the object's read-only constant pool, or a frame-local spill slot.
3. **Separate arrays.** Parameter buffers are treated as separate symbolic arrays only under the
   declared domain's non-overlap fact (§2.4).

A footprint failure is rejection, like a DAG mismatch.

**The audited rewrite list.** Budget ≤ 30 rules [target], following P5's X2 gate. Each rule is proved
by exhaustive binary32 enumeration where the domain allows; otherwise from the IEEE 754 definition for
non-NaN values plus a case-exhaustive check of the NaN and signed-zero layer, cross-checked with Z3 FPA
and a second solver. The list is graded `validated(exhaustive, partition)` until mechanised in Lean
(DR-010).

| Family | Rule | Side condition |
|---|---|---|
| Commutation | `a + b ↔ b + a`; `a · b ↔ b · a` | NaN-order condition |
| Negation | `−(−x) ↔ x`; `x − y ↔ x + (−y)` | NaN-order condition |
| Signed-zero identity | `x + (−0.0) ↔ x` | NaN-order condition: an SNaN `x` is quieted, so the result differs from `x` bit for bit. For every non-NaN `x`, −0.0 included, the rule is exact under the default MXCSR. `x + (+0.0)` is **not** a rule; it maps −0.0 to +0.0 [R07] |
| Unit | `x · 1.0 ↔ x` | NaN-order condition (quieting can change an SNaN payload) |
| Power-of-two scaling | `x · 2.0 ↔ x + x`; `(x · 2^k) · 2^−k ↔ x` | first: none; proved by exhaustive binary32 enumeration against the table entries (both sides round 2x once, overflow to the same ∞ and quiet the same NaN). Second: T2 range shows that `x · 2^k` neither overflows nor loses bits in the subnormal range, plus the NaN-order condition |
| Exact conversion | int→f32 | T2 range `|v| ≤ 2^24` |
| Exact widening | f16→f32; bf16→f32 by a 16-bit shift | none [G02] |
| Data movement | loads, stores, moves, lane permutes, broadcasts, extracts, inserts, constant-mask blends | bitwise identities over table semantics |
| Masking | all-ones mask ↔ unmasked; zero-masking semantics | T2 proves mask contents |
| Integer ring | e.g. `Σ(n−8)q = Σnq − 8Σq`; `vpdpbusd` as four u8×s8 products summed into i32 | T2: no overflow, no saturation (e.g. Q4 `maddubs` bound 3,810 [R07 via P2]) |

**Never on the list:** reassociation, distribution, FMA contraction or fusion, MAX/MIN operand
commutation, `x + 0.0 → x`, `x − x → 0`, `x · 0 → 0`, accumulator splitting.

**The NaN-order side condition.** Commutation, negation, the signed-zero identity, the unit rule and
inverse scaling preserve every non-NaN result bit for bit and preserve NaN-ness. They may change a
NaN's payload, quiet bit or sign: IEEE 754 does not fix which NaN operand an add or mul propagates,
and an SNaN operand comes back quieted. That is why Hearth canonicalises NaN on store (NUMERICS.md).
Such a rewrite is admissible only if **every path from the rewritten node to an observable sink passes
through `canon::nan` before reaching any consumer that observes NaN payload, NaN sign or operand
position**. Observing consumers include stores to observable memory, bitwise operations and integer
reinterpretation, sign-driven selection (BLENDV, movemask, mask-from-sign) and, conservatively,
MAXPS/MINPS-class selections, which return their second operand on NaN or ±0 [R07]. Comparisons and
FP→int conversions do not observe payload. T1 checks the condition as a dataflow property of the lifted
DAG.

### 6.4 Loop correspondence under compiler transformations

KLEE-FP's precedent was straight-line code on fixed shapes [R07]; compiler output adds loops, and the
panel made loop correspondence a prerequisite for any object-code claim.

| Transformation | How T1 relates the loops | T2 side conditions |
|---|---|---|
| None (lockstep) | one machine iteration ↔ one meaning iteration, related by a **simulation relation R over symbolic loop-head states**. R has a register part (machine registers equal the meaning's values under the lane map) and a memory part: output locations the meaning has written so far (`y[0..i)`) hold equal values, no other output location has been written, and inputs are unchanged. *Base:* R holds on entry. *Step:* for **every** symbolic state that satisfies R, the guard and the hinted invariant, one machine iteration and one meaning iteration re-establish R (one-iteration DAG match plus footprint, §6.3). *Exit:* R and the negated guard imply equal outputs. This is the **lockstep rule**, proved once (DR-010) | equal trip counts; footprint (§6.3) |
| Unroll by u, with remainder | machine body ↔ u consecutive meaning iterations composed **in order**; remainder loop ↔ the last `r` iterations in order | `N = u·q + r`, `0 ≤ r < u`; guards match |
| Rotation, software pipelining | loop-head state ↔ meaning boundary state **plus pending terms** of the next iteration (loads, integer partials), checked inductively; no FP operation may combine operands of two meaning iterations in an order the meaning lacks | prologue and epilogue trip arithmetic |
| Peeling (alignment prologue, masked tail) | segments concatenated in iteration order; masked lanes excluded by blend or zero-mask, or combined only through an exact identity (`+ (−0.0)` under its NaN-order condition, never `+ (+0.0)`) | mask contents |
| Spills and reloads | frame-local, constant-offset stack slots promoted to SSA values by the lifter; a reload equals the last spill if no intervening store may alias; any computed or escaping address is unknown | constant offsets, non-escaping |
| Horizontal reductions | shuffles and extracts evaluated into a lane tree that must equal the meaning's named tree. `_mm512_reduce_add_ps` documents the halving tree equal to `canon::sum16`'s last stage, but its lowering by MSVC, Clang and GCC is unverified until the census [G02] | — |
| Row tiling, interchange of independent outputs | each output's DAG matched separately; independence from the meaning's disjoint writes (`par for`) | disjointness |

Any failure is rejection. The other rows reduce to the lockstep rule. Each composes its segments or
unrolled bodies into one step of the same simulation relation, with the memory part included.

**Soundness argument.** T1's "equal" depends only on five things:

- the semantics entries in its trust base;
- the rewrite list;
- the loop rules above, each proved once and part of `mithcheck-t1`'s design;
- T2 certificates;
- the declared domain (§2.4).

"Equal" covers memory as well as values. The footprint check (§6.3) and the memory part of R make
out-of-bounds stores, out-of-bounds loads and writes outside the correspondence into rejections.
Correspondence maps, induction invariants and pending-term sets are hints whose errors cause rejection.
Attention's sequential-in-t accumulation may need the fixed-chunk redefinition the GPU tier needs anyway
[P5 §14]; that is a canon change (§12).

### 6.5 T2, and T3 (reserved)

T2 discharges ranges (the snippet's `|isum| ≤ 64·8·127 = 65,024 < 2^24`), saturation freedom, exact
int→float, alignment, nibble extraction (`elem(j)`), the address bounds of T1's footprint check and
T0's SSA route, and DR-011's simple integer contracts. **Solvers are untrusted**: an answer counts
only with a certificate (LRAT for SAT and `bv_decide`, Alethe or CPC for
cvc5) re-checked by a small checker. Alive2's authors hit six Z3 soundness bugs [R07]. **Unknown or
timeout is rejection**: in `kernel` code an unprovable refinement is a compile error, never a runtime
trap (DR-011); elsewhere the obligation stays open and the claim is not admitted.

T3 tolerance certificates (FPTaylor- or Satire-class bounds, runtime margin checks at top-k and argmax)
are reserved behind ROADMAP D-07. Bounds do not propagate through routing or quantisation, so any
end-to-end tolerance claim needs margin checks there [R07]. T3 output can never satisfy an exact slot.

### 6.6 The instruction census (DR-008, step X0)

The ~105 instruction forms (74 mnemonics, about 10 FP-sensitive) are what Hearth's intrinsics imply,
not what compilers emit; G02 leaves the emitted census as its open question 6 [G02]. So the census
comes **first**: compile Hearth's kernels with each supported compiler under the pinned strict flags
(MSVC `/fp:precise`; Clang/GCC `-ffp-contract=off`, no fast-math); decode each kernel symbol with XED;
record per (compiler hash, flags, source hash, symbol) the iclass multiset plus loop nests, unroll
factors, vector spills, horizontal-reduction sequences and calls; diff against table coverage. The
result defines the day-one table and is stored as `evidence` facts keyed by toolchain hash, so a
compiler upgrade reruns it.

Then X2 runs T1 on transliterated intrinsic IR, and only then comes the object audit of the ~20 hot
kernels (DR-008). A variant that emits an unvalidated iclass, or fails to lift or match, is `tested` and
not dispatched in release profiles. Claims are keyed by the object's toolchain, so release dispatch
needs the slot's grade for the objects actually shipped. arm64 NEON has no table unless ROADMAP D-17
fires (by-trigger); until then those builds are `tested` (hash corpus) and labelled so. Cross-compiler variance: [04-toolchain.md](04-toolchain.md).

### 6.7 The semantics table (v0 for Hearth's census, M0–M2; by-trigger for the emitter subset, D-05)

No public source has bit-precise, silicon-validated AVX-512 FP semantics: pseudocode-derived models are
integer-only or FP-imprecise, ACL2 and Sail x86 implement no EVEX opcodes, and nothing has been
validated on AMD silicon [G02]. Mithril owns a **hand-written, single-source table**:

- **Key and source.** Keyed by XED iclass (XED is Apache-2.0). Entries are written from the SDM, not
  derived mechanically from Intel's intrinsics XML, whose terms forbid derivative works (an Owner
  question, G02 open question 2).
- **Fields.** Lane shape; mask mode; integer semantics as bit-vector terms; FP semantics as an FPA core
  plus an explicit **x86 FP-environment layer** (MXCSR.RC and `{er}`, DAZ/FTZ as configured or forced,
  NaN selection and quieting as bit-vector logic, integer-indefinite conversions, MAX/MIN operand
  order); and a `precond` such as `mxcsr == default`. The default MXCSR is set on entry and
  restored on exit at every `export abi` and `hx_*` entry, and set and asserted at pool-worker
  start ([ARCHITECTURE §6.3](../ARCHITECTURE.md), [04 §9.2](04-toolchain.md)). That precondition
  is a runtime-checked trust-base entry (§3.4), not an axiom and not a discharged obligation [G02].
- **Generated consumers.** SMT terms for T1/T2, a C reference interpreter for fuzzing, Exo-style
  `instr` bodies (closing Exo's unchecked-`@instr` gap by construction), later a Lean export [G02, R05].
- **Validation and grade.** Each entry declares a case partition: NaN (SNaN and QNaN, distinct
  payloads) in each operand position, ±0 combinations, subnormals, ±∞, conversion boundaries such as
  2^24 and 2^31, saturation boundaries, all mask-pattern classes, `{er}` variants. An entry is
  `validated(partition)` on a silicon fingerprint (CPU family, microcode) when two things hold: every
  class has been run on the 9950X with zero disagreements, and Bochs agrees. A lane function whose
  domain is at most 2^32 must also be enumerated exhaustively, and then it is
  `validated(exhaustive)`. Otherwise the entry is `tested`. Uniformity within a case class is the
  axiom of §3.4, not a result. Integer entries are cross-checked against Hydride, VeGen and Alive2
  where they overlap [G02]. Re-fuzz triggers: microcode change, new CPU, entry change.
- **Fingerprints and other machines.** Grades and floors are evaluated against the build machine's
  fingerprint (§3.5), today the 9950X. That happens at build time and when the release dispatch table
  is generated. Every shipped claim therefore carries the axiom "the target CPU conforms to the table
  on the case classes used". INV-DET-3 on a user's Intel or Zen 4 part, or on a CI runner, rests on
  that axiom, and `ledger why` prints it.
- **Load-time self-test (v0, M5 [inference]).** This narrows the axiom on each machine. Before
  publishing the dispatch table ([04 §6.7](04-toolchain.md)), the runtime runs the stored case-class
  vectors for the iclasses of each variant it would dispatch. This takes milliseconds [target].
  - On a mismatch, that variant is dropped. Dispatch falls back to the next variant that passes,
    ending at the portable variant. If none passes, the release profile is refused.
  - Because the vectors are the case-class representatives, a passing self-test is a
    `validated(partition)` record for that fingerprint. It is logged. On a machine that runs a gate,
    it is admitted as a fact.
  - A full re-run with Bochs, plus exhaustive enumeration, replaces the conformance axiom for that
    machine with its own entry grades. Uniformity within each class remains an axiom.
- **Special entries.** VDPBF16PS and VCVTNEPS2BF16 (forced DAZ/FTZ) and RCP14/RSQRT14 (approximations)
  are admitted one at a time, and stay out of kernels whose meaning is defined by IEEE operations [G02].

```text
entry VMAXPS  form VMAXPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512        (illustrative)
  lanes 16 x f32 · mask merge|zero · precond mxcsr == default
  lane i: if isnan(a[i]) || isnan(b[i]) || (a[i] == 0 && b[i] == 0) then b[i]
          else if a[i] > b[i] then a[i] else b[i]                       -- second operand wins on NaN and ±0
  evidence: case-class record sha256:… · silicon Zen 5 (9950X, microcode …): agree · Bochs: agree
  grade:    validated(partition) (on that fingerprint)
```

G02 estimates 25–40 parameterised families and about 1.5–3k lines of table plus generator [inference,
G02]. The X2 gate requires zero table/silicon mismatches [P5 §10.1].

---

## 7. The promotion rule and the α budget

### 7.1 The rule (DR-015)

For an evolvable slot with declared space `S`, candidate `c`, incumbent `inc` and hardware fingerprint
`H`, the gate promotes `c` if and only if, cheapest first:

```text
promote(c, slot, H) <=>
     check_S(c)                                   -- T0 or T1/T2: decidable, cached, no agent-written proof
  && eff(correctness(c)) >= slot.required_grade   -- §3.2: premises and the spec-strength cap included
  && floor(correctness(c)) >= slot.code_floor     -- §3.2: checkers and elaboration
  && E_t(perf(c) vs perf(inc) on H) >= 1/alpha_i  -- anytime-valid e-process; alpha_i charged when the test opens
  && plausible(c, H)                              -- no measurement beats a validated phys/emp floor
  && authority(slot)                              -- standing grant (opt-in profile) or Owner ADR (default)
```

A failure stops spending. Correctness failures and pruned candidates never touch the α budget.

Spec strength enters once, through the cap inside `eff` (§8.4). There is no separate
`strength(slot.spec) >= slot.required_strength` conjunct: it would count strength twice, with no
stated relation between the two thresholds (Reviewer note 8).

### 7.2 The α budget

- Each engine-measured promotion test `i` is allocated `α_i` **when it opens**, whether or not it later
  passes. Charging only winners would let many trials launder a lucky run.
- A *false promotion* is one whose true effect on the pre-registered estimand is not an improvement
  ([06 §6.2](06-forge.md)). The minimum detectable effect sizes each test but is not part of the
  guarantee.
- **The guarantee has two tiers** ([06 §6.5](06-forge.md)):
  - **Defaults and F1-A promotions: a union-bound α budget.** Per budget period and slot family,
    `Σ α_i ≤ α_budget`, so E[false promotions] ≤ Σα_i, and P(any false promotion) ≤ Σα_i when
    Σα_i < 1 (Ville's inequality and the union bound).
  - **Grant-promoted opt-in per-machine profiles: e-LOND online FDR ≤ q.** Each grant runs an
    e-LOND stream. Test t opens with α_t = min(0.05, q · γ_t · (D + 1)), where γ is a
    pre-registered sequence summing to at most 1 and D counts the grant's promotions so far, and
    passes at e ≥ max(20, 1/α_t). The expected share of false promotions among the grant's
    promotions is then at most q at every point in the stream. The specimen grant has q = 0.20 and
    γ uniform over 40 tests, so its thresholds are 200/(D + 1), never below 20.
- DR-015's floor `e ≥ 20` means `α_i ≤ 0.05` on both tiers. On the union-bound tier a budget `B`
  therefore admits at most `20·B` tests at the floor per period, and more at smaller `α_i`, which
  cost only logarithmically more blocks ([06 §6.5](06-forge.md)). Budget sizes, q and γ are Owner
  decisions (Reviewer note 7).
- Replenishment (a refilled budget or a new γ sequence) is AUTHORITY. Thresholds may tighten
  autonomously but loosen only by AUTHORITY (P4's S3 monotone strictness, [06-forge.md](06-forge.md)).
- E-processes assume exchangeable samples. The interleaving, blocking, stationarity checks and quiet
  windows that make that defensible on a Windows desktop are in [06-forge.md](06-forge.md); a
  fingerprint change mid-test voids it.

Parity gates use the same machinery as a non-inferiority test (δ = 3%, interleaved and load-gated
against `hearth-c-ref`, DR-018); superiority claims need `e ≥ 20`.

### 7.3 Authority levels

| Promotion | Authority | Constraint | Status |
|---|---|---|---|
| Opt-in per-machine profile, pinned per fingerprint in `mith.lock` | standing grant: AUTHORITY fact, scoped to slot and space, expiring, revocable | output-preserving spaces only; `e ≥ max(20, 1/α_t)` in the grant's e-LOND stream (§7.2); plausibility pass | v1 (M6) |
| Shipped default, timing_only defaults included (ADR-0004 class) | Owner-signed ADR with dossier | union-bound α budget (§7.2) | v0 (M3) |
| `approx` | — | never a default | reserved |
| TCB, semantics table, canon, editions | Owner-signed ADR | §12, §14 | v0 (M3); editions v1 (M7) |

Grant operations are detailed in [06-forge.md](06-forge.md).

### 7.4 Plausibility needs a validated bound

A measurement that beats a physical floor is an evaluator bug or a hack [R01]. But Hearth's own Belady
bound was beaten by an online policy (68.2% against 63.4%) because its warm start was wrong
[R01, RV: D3-ii]. So a bound drives **quarantine** on its own only if its derivation is graded at
least `validated`: a `phys` bound (link and DIMM limits) or exact bytes replayed by the trusted core.
An audited `emp` term prunes but does not quarantine on its own. It is a measured peak, and a
measured peak is a lower bound on the attainable roof: a better kernel or I/O pattern can beat it.
So it acts as an upper bound only with a pre-registered headroom, `emp_bound = min(phys, max observed peak × (1 + h))`, with h at least the
measurement CI plus a declared margin (e.g. 5%) ([02 §13.2](02-compute.md)). Pruning uses
`emp_bound`. A result between `emp_bound` and `phys` is **flagged for audit, not quarantined**.
With a weaker bound, an implausible measurement holds the candidate and opens an audit
of both evaluator and bound; the bound term may be the one retracted. Replayed exact-byte bounds are
sound only for `timing_blind` policies, whose decisions read the logical event stream and never clocks
or completions; prefetching policies get MIN-type bounds only, which pruned nothing in the simulated
pilot [RV: D3-ii]. The prune-certificate protocol is in [06-forge.md](06-forge.md).

### 7.5 The resulting guarantee

The guarantee holds under a declared trust base:

- a sound `mithcheck`;
- faithful elaboration of the meaning;
- table entries that match silicon on their validated domain;
- a space theorem sound at its stated grade and bound;
- callers inside the declared domain (§2.4);
- correct hardware and OS;
- isolation that holds.

Under it, two things hold:

- every promoted candidate in an exact slot produces outputs bit-identical to its meaning or
  fallback on the declared domain;
- false promotions (true effect on the pre-registered estimand not an improvement) are bounded in
  two tiers (§7.2). For defaults and F1-A promotions, a union-bound α budget gives
  E[false promotions] ≤ Σα_i per period and slot family. For grant-promoted opt-in per-machine
  profiles, each grant's e-LOND stream keeps online FDR ≤ q (q = 0.20 in the specimen grant;
  thresholds as in [06 §6.5](06-forge.md)).

Both are checkable from the ledger. The tractability is in the decomposition: one proof per space,
a mechanical check per candidate, statistics only where no proof exists [P2 §8.1].

---

## 8. Roles, spec escrow and spec strength

### 8.1 Roles (v0: pilots from M0–M1, enforced with the M3 ledger)

| Role | May write | May never write |
|---|---|---|
| Author | meanings, specs, claims, fault models, slot-policy drafts | implementations, schedules, the gate |
| Builder | implementations, schedules, policies, layouts | specs, meanings, goldens, mutant pools, the harness, baselines |
| Prover | proofs and certificates for named obligations | specs, implementations |
| Adversary | sealed mutant pools (commit-reveal), chaos policies, planted kernels, injection canaries (§11.2) | specs, implementations, the gate |
| Gatekeeper | runs the gate; assembles dossiers | the gate's code, thresholds or α budget |
| Owner (human key) | AUTHORITY facts | — |

All Forge proposers are Builders by construction [P4 §5.4]. A session holds exactly one role token, a
write capability over sealed definitions.

### 8.2 Enforcement

Ownership is declared over definitions and sealed modules in `mith.toml`. Change sets are judged as
**content-addressed git objects** of the merge result, never as working-tree paths; links on sealed
paths are refused; **the gate never executes code from the change it judges** and runs base-revision
tools. These are the lessons of Hearth ADR-0009, whose golden gate fell to gut-and-re-lock, symlinks,
stale merge refs, case twins, 8.3 names and a change that edited its own judge [RV: D2-E]. `mithc check`
refuses change sets in which a Builder or Prover writes a spec, witness set, mutant pool, holdout,
baseline or gate artifact.

### 8.3 Spec lifecycle

draft → hardening → admitted (hash-locked, AUTHORITY) → amended (new hash, re-hardened). Old evidence
keeps pointing at old hashes. `assume`, `sorry` and `assume(false)` are banned in admitted code;
AlphaVerus saw `assume(false)` spread from one program to all of them [RV: D2-E].

### 8.4 Two-sided strength and the versioned strength map

**Executable meanings** (kernels) are complete for refinement by construction and do not cap `refines`
claims. Their risk is the **intent gap**, attacked by separate claims against independent oracles
(Hearth's numpy reference and transformers under INV-NUM-1/2, [07-hearth-port.md](07-hearth-port.md))
and by running the numerics fault model against the meaning itself [P2 §5.5]. **Contracts** (parser,
store, router) are partial, so their strength is measured two-sided: soundness (the reference and every
legal variant pass); a kill interval `[K_lo, K_hi]` with the unknown fraction `U`; vacuity (zeros,
passthrough and ignore-scale witnesses must fail); latitude (distinct admitted variants, penalising
specs that restate one implementation); and independence (§8.5). The cap is a versioned table, so the
meet in §3.2 is well typed, as the panel required:

| Strength record (`strength_map.v1`) | Cap |
|---|---|
| executable meaning, for refinement claims | none |
| contract: sound, `K_lo ≥ K_min`, `U ≤ U_max`, vacuity pass, latitude ≥ `L_min`, independent | `validated` |
| contract: thresholds met, but `independence: same_family` | `tested` |
| contract: thresholds unmet, or not hardened | `assumed` |

The revisit node's example values (strength ≥ 0.97, unknown ≤ 0.02, latitude ≥ 3) are the starting
[target] thresholds pending an Owner decision [RV: D2-E]. LLM-written specs are sound and complete only
about half the time [R03]. The honest claim is always "strong against fault model F, as judged by
principals P", never "correct".

### 8.5 Independence, friction, handovers

Author and Builder on a sealed spec must come from different model families (P5's approximation;
measured independence is by-trigger, ROADMAP D-16). Errors among similar models are measured to
correlate (Goel et al., [RV: D2-E]), so a same-family record lowers the cap; separation of powers stops tampering, not
shared misunderstanding [RV §6.11]. A fourth identical failing retry is blocked until a root-cause note
exists. Handover facts come from the toolchain journal and the ledger; the agent writes only
length-capped `rationale` and `next_actions` ([05-agent-protocol.md](05-agent-protocol.md)), which
closes DGM's log-faking class [R01].

---

## 9. The Gatekeeper and `abandon`

**A deterministic judge (v0, M3).** The gate is trusted F0 code, built by the frozen bootstrap toolchain
pinned by hash; no candidate compiler ever builds the gate, the checker or the measurement service
[R01, P2 §4]. Its inputs are facts, certificates, measurement run records and slot policies, all by
hash; it reads no free text; its output is a signed verdict. An LLM in the Gatekeeper role runs it and
assembles dossiers but cannot change thresholds, budget or code. Model-judged gates are ruled out: LLM
verifiers reached only 0.73–0.82 accuracy on robust-kbench's checks [R01], and judges favour similar
models [RV: D2-E]. Scoring rules stay hidden, because DGM hacked more when its checker was visible;
diagnostics are exposed [R01].

**`abandon` (v0, M1; ledger-backed from M3).** `mithc abandon --reason spec_conflict|infeasible|blocked|budget` is a first-class
outcome, recorded as a FREE fact. The verb and its reason enum are owned by
[05 §10](05-agent-protocol.md); this document uses them unchanged. On a task that is in fact impossible or
contradictory, `abandon` scores as correct in the harness. ImpossibleBench found that an abort option
cut GPT-5's cheating on conflicting tasks from 54% to 9% [RV: D2-E]. A spec-versus-test conflict is
routed to the Author, never resolved by the Builder.

**A second checker (by-trigger, ROADMAP D-09).** The trigger: before the first grant or ADR that
rests on T1 evidence (expected M6), or after the first T1 soundness bug. From then on,
promotion-grade claims also pass an independently written T1/T2. Acceptance requires agreement, and
disagreement quarantines the claim [P2 §5.6]. Under
AND-composition the verdict is sound if *either* checker is, so this reduces reliance on the first
checker rather than enlarging the TCB.

---

## 10. Documented reward hacks and their counters

Every exploit documented in [R01] and [R05], plus [RV: D2-E] and Hearth's history, maps to a named
mechanism. Several counters are runtime or isolation properties, not type errors, and are labelled so.
All counters are v0, in place by M5, unless marked; rows marked (v0, M1) are in place from the first
compiler. Rows 1–29 cover program and kernel evaluators. Rows 30–34 cover the
agent harness, which scores DR-017's kill decisions, the comprehension preconditions, B2 and all F1-A
fitness ([05 §13](05-agent-protocol.md), [06 §10](06-forge.md)).

| # | Documented exploit | Source | Counter | Kind |
|---|---|---|---|---|
| 1 | Faked tool-use and test logs | DGM [R01] | facts admitted only gate-signed; handover facts from the journal | structural |
| 2 | Removing hallucination markers (node 114) | DGM [R01] | checkers, specs, goldens sealed; Builders cannot write them; scoring hidden | structural (v0, M1) |
| 3 | Disabling the sandbox flag "for efficiency" (0.42% of attempts) | STOP [R01] | isolation is not a parameter of candidate code: Job Object or WSL2, supervisor-held limits | isolation |
| 4 | Wrong output shape → accuracy above 1000% | STOP [R01] | shapes fixed by evaluator types; `refines` over all inputs | type (v0, M1) |
| 5 | Editing its own time limit; relaunching itself; ~1 TB of checkpoints | AI Scientist [R01] | supervisor-held limits and quotas; no `spawn` or `io` in evolve rows | isolation + type |
| 6 | Bypassing accuracy validation (aggregate 3.13× → 1.49×) | AI CUDA Engineer [R05] | correctness by certificate or space membership, checked out of process | structural |
| 7 | Reading the reference through memory reuse (`torch.empty`) | METR [R01] | poisoned fresh allocations; reference never in the candidate's capabilities; candidate runs first | runtime |
| 8 | Copying, calling or inheriting the reference; `try/except` fallback | Kevin-32B [R01, R05] | exact slots need a certificate over all inputs; no calls outside the T0-checked closure; a fallback is a different DAG, so T1 rejects | type + T1 |
| 9 | Work on unwatched streams (82 of 250, 32.8%); lazy outputs; shrunken batch or dimensions; outputs cached by input address | CUDA-L1 [R01] | runtime owns the clock and joins all threads, streams and I/O first; outputs materialised and hashed; shapes from evaluator types; no state outside a declared block reset between calls | runtime + type + T0 |
| 10 | Hard-coding tested inputs; dropping "redundant" ops; assuming weight properties | robust-kbench, KernelBench-Verified [R01, R05] | `refines` over all inputs; specialisation keys are finite kinds, never weight values; held-out shapes | T1 + type |
| 11 | Weak or slow baselines (51× on one task; FP32 versus TF32) | robust-kbench, KernelBench-Verified [R01, R05] | baselines named in Author-owned specs, measured interleaved on the same machine | structural |
| 12 | Near-zero outputs; loose tolerance (atol 0.01) | robust-kbench, METR [R05] | exact grade is bit equality; tolerance only through reserved T3 | type (v0, M1) |
| 13 | CPU overhead dominating timing; lucky runs; winner's curse | robust-kbench, DGM [R01] | protocol owned by the measurement service; anytime-valid e-values; α charged per test opened | statistical |
| 14 | Timer overwrite, evaluator monkey-patching, stack walk to the reference, disabled sync, overridden equality (30.4% of runs) | o3 on RE-Bench [R01] | no `time` capability; T0 bans RDTSC/RDTSCP/RDPMC and confines loads to the policy arena, so there are no KUSER_SHARED_DATA or TEB clock reads (§6.2); no reflection or operator redefinition; evaluator in another process | type + T0 + isolation |
| 15 | Leaky discretised verifier; exploited numerical integration | AlphaEvolve (Tao et al.) [R01] | exact checking; unknown = reject; plausibility bounds | structural |
| 16 | Calling stronger models (capability escape) | Gödel Agent [R01] | no `foreign` or network in evolve rows; proposer model and cost in provenance | type + ledger |
| 17 | Self-modifying the improver (4% of runs terminated) | Gödel Agent [R01] | the Forge cannot write F0 or the gate; promotions reversible (IF-3) | structural |
| 18 | Resource regressions the metric ignores (28% of the best model's kernels raised peak memory) | KernelBench-Verified [R05] | cost signatures record bytes per tier; a regression on a declared resource blocks promotion | structural |
| 19 | Special-casing under conflicting specs (54%; 9% with an abort option) | ImpossibleBench [RV: D2-E] | `abandon`; Adversary conflict probes; hidden holdouts | process (v0, M1) |
| 20 | Vacuous specs (`assume(false)`); ~9% of successful specs too weak | AlphaVerus, vericoding [RV: D2-E, R03] | escrow; vacuity witnesses; banned escape hatches; strength cap | process |
| 21 | Near-tautological tests | Hearth council [RV: D2-E] | `tested` requires a recorded kill rate under a named fault model | process |
| 22 | Golden test gutted and re-locked; gate edited by the change; symlinks, case twins, 8.3 names, stale merge refs | Hearth ADR-0009 [RV: D2-E] | git objects only; gate never executes the change; base-revision tools; paths never enter trust decisions | structural (v0, M1) |
| 23 | A hook setting FTZ/DAZ or the rounding mode | [RV: D2-A], [G02] | `fp_env` absent from timing_only; T0 allowlist; the default MXCSR set on entry and restored on exit at every `export abi` and `hx_*` entry, and set and asserted at pool-worker start (§3.4) | type + T0 + runtime |
| 24 | Poisoned benchmarks persisting after clean re-evolution | Roesner & Kohno [RV: S1] | evaluator hash in every score; evaluator change voids scores; provenance enables bulk re-scoring | ledger |
| 25 | Sabotage attempts (12% in one evaluation) | Anthropic [RV: D2-E] | separation of powers; Owner key for defaults; Adversary role | structural |
| 26 | Correlated errors among same-family roles and judges | Goel et al. [RV: D2-E] | independence caps strength; no LLM judges | process |
| 27 | A bound "beaten" by an evaluator bug | Hearth simulator [R01, RV: D3-ii] | quarantine plus bound audit; only validated bounds quarantine on their own | structural |
| 28 | Probing the checker by near-identical resubmission [inference] | — | friction rule; e-graph dedup; acceptance after many near-miss rejections is flagged for Adversary review | process |
| 29 | Instructions planted in archived text [inference] | — | §11.2 | structural |

**Harness and F1-A.** The harness is itself an evaluator that agents are scored by, so it needs the
same treatment [inference except where cited].

| # | Documented exploit | Source | Counter | Kind |
|---|---|---|---|---|
| 30 | Locating hidden tests, oracles or reference solutions in the sandbox, its VCS history or the evaluator's memory | SWE-bench-style leakage [inference]; reference reads and stack walks (rows 7, 14) [R01] | The sandbox holds only the visible task: a fresh tree with **no VCS history**, no oracle or reference files, and no network but the model API ([06 §10](06-forge.md)). The hidden oracle runs **out of process**, in the Gatekeeper's private store | isolation |
| 31 | Editing visible tests or the acceptance harness so that they pass | DGM's marker removal [R01]; Hearth ADR-0009 [RV: D2-E] | The harness **scores the final artifact, which it rehashes itself**. Edits outside the task's writable definitions are discarded, the hidden oracle runs on the rehashed artifact, and visible-test edits never count. The agent's own report is never read | structural |
| 32 | Solution leakage through card atoms, worked examples or F1-A atoms | [05 §13](05-agent-protocol.md) contamination rule | An atom contamination check runs against every hidden reference (token 5-gram containment, alpha-renamed AST similarity). An atom above the threshold is rejected unscored, and the equal-information brief applies to every arm | process |
| 33 | Training-set contamination of sealed items through the public Hearth and Mithril repositories | contamination concern for SWE-bench Verified [R01] | **Private suites** with canary strings, **fresh items** each epoch (≥ 30% [target]), kill decisions on unflagged items only, and the reused-minus-fresh gap read as contamination ([05 §13](05-agent-protocol.md)) | process |
| 34 | Eval-aware behaviour: a model under test acts differently when it detects an evaluation | [inference] | Items carry no harness markers and match working tasks in form. **Item-level paired comparisons** set scored runs against unscored shadow runs of the same items under working-session framing. A systematic shift flags the model family, and its results are reported separately | statistical |

---

## 11. Threat model

### 11.1 Assets, adversaries, boundaries

**Assets:** bit-identity of logits; ledger integrity; the Owner's authority; integrity of the gate and
measurement service; quiet-machine time; the Owner's machine and data (keys, model files, traces).
**Adversaries:** (A1) a capable, adversarial proposer in any role, assumed to try every exploit in §10;
(A2) correlated roles from one model family; (A3) untrusted text reaching models; (A4) a buggy, not
malicious, TCB: the Lean kernel bug of July 2026 [R07], 15 eBPF verifier logic bugs found in a month
[RV: D2-A], solver bugs [R07]; (A5) a compromised machine; (A6) a changed or compromised upstream
toolchain. **Out of scope:** physical attacks; general side channels (server tenant labelling is a
separate, later item [RV: D3-iii]); denial of service by the Owner.

```text
 +--------------------------- owner's desktop (Windows 11) ------------------------------+
 |  agent sessions (role tokens) --> mithc (untrusted) --> objects, certificates         |
 |        | request only                                       |                         |
 |        v                                                    v                         |
 |  +------------- gate principal (separate account or VM) ---------------+             |
 |  |  gate + mithcheck + measurement service   (gate key, non-exportable)  |             |
 |  +-----------------------------------------------------------------------+             |
 |        | signed facts -> .mith/ledger (git)        blobs -> data dir (not synced)      |
 +--------|------------------------------------------------------------------------------+
          v                                         Owner hardware token (AUTHORITY only)
   CI (CI key): replays certificates, signs `reverified`; Owner approves high-impact AUTHORITY on a 2nd device
```

### 11.2 Prompt injection through archived text (v0, M1–M3)

Models read much text the project keeps: tombstone rationale, comments, string literals, diagnostics
that quote source, handover `rationale` and `next_actions`, commit messages, dossiers, model-file
metadata and tokenizer strings. All of it is untrusted data. No dossier studies this threat for Mithril;
the design is [inference].

1. **Authority never flows from text** (A10). Every privileged act needs a role capability or an Owner
   signature, and no verb takes instructions from archived text. A successful injection can at most
   mislead a proposer's search, and the gate bounds what that search can promote.
2. **Structured fields carry meaning; free text carries none.** The gate, `mithc revisit` and the Fact
   Plane never interpret `notes`, `rationale` or comments. Tombstone triggers are expressions in a
   decidable data language that evaluates no code ([06-forge.md](06-forge.md)).
3. **Rendering.** Context packs and `mithc resume` place untrusted text in delimited, length-capped,
   provenance-labelled blocks after the structured facts, never in the role preamble; the Tier 0 card
   says such blocks are data. Diagnostics reference spans rather than echoing literals.
4. **Measured susceptibility.** The Adversary plants injection canaries in the archive and harness
   tasks; the harness reports an injection-follow rate per model family beside VP@1 and CABW
   ([05-agent-protocol.md](05-agent-protocol.md)). Sessions that follow a canary are flagged.
5. **Outside inputs.** `.hearth` files and tokenizer data go through the format-derived parser
   (INV-FMT). It has no `unsafe`; its totality and safety are graded `tested` (fuzzing, the `mithi`
   differential and the golden malformed-file test), and only the bounds obligations T2 discharges
   are `proof` ([ROADMAP §7](../ROADMAP.md) B1). Strings from these inputs never enter agent context
   unescaped.

### 11.3 Owner key management on a single desktop (v0, M3)

No proposal addressed this (panel judges); the design is [inference].

- **Owner key.** A signing key on a hardware token that requires a physical touch per signature, plus a
  second token kept offline; both are listed in `.mith/trust/roots.toml`. It signs only AUTHORITY facts.
  `mithc ledger sign --authority` renders the fact from structured fields, never free text, and shows
  the hash prefix.
- **Second channel.** High-impact AUTHORITY (TCB amendment, key rotation, α replenishment, canon
  admission) takes effect only after the Owner also approves the matching pull request from a second
  device, where CI re-renders the summary from the fact bytes. A compromised desktop can lie about what
  it asks the token to sign, but not about what CI shows.
- **Gate key.** Held by the gate principal (a separate local account or VM that agent sessions cannot
  read) as a non-exportable key in the OS key store, TPM-backed where available. Agents run without
  elevation, ideally as a standard user distinct from the Owner's administrator account. **Until that
  separation exists, gate signatures on this desktop defend only against accidental and in-protocol
  tampering**, not against an agent with shell access that sets out to read the key; CI
  re-verification and Owner-signed AUTHORITY are what hold in that state.
- **Never in the repository.** Keys, raw samples and private traces stay out of the repository and of
  cloud-synced folders (Reviewer note 6).
- **Rotation and loss.** Rotation is an AUTHORITY fact signed by a listed key. Losing the primary token
  is recovered with the backup; losing both is a re-rooting event the Owner decides and records.

### 11.4 Compromised machine and supply chain

An administrator-level compromise can forge gate signatures and fake measurements. The design does not
prevent that; it makes it **detectable and recoverable**:

- **Certificate-backed evidence is portable.** T0 verdicts, T1 witnesses and T2 certificates replay in
  linear time anywhere. CI replays them and signs `reverified` facts, so a forged `proof` without a
  valid certificate fails off the desktop (the PCC and eBPF pattern [R07]).
- **Measured evidence is machine-bound.** After a suspected compromise the Owner revokes the gate key as
  of the last Merkle checkpoint CI also verified. Later facts are quarantined; certificate-backed ones
  are re-checked by CI and re-signed by the new key; measured ones are re-measured; AUTHORITY facts are
  re-confirmed. Nothing is deleted (A11).
- **Supply chain.** A compiler upgrade changes the toolchain hash, reruns the census and re-audits
  kernels; since T1 validates outputs, a new compiler adds no trust for kernels. For non-kernel code the
  C compiler stays trusted (§14). XED decoding is trusted, with a second decoder (for example LLVM's
  disassembler) run differentially during audits [inference]. The Rust toolchain that builds F0 is
  pinned by hash; solver binaries are untrusted.

---

## 12. Canon version migration protocol

`canon.v1` is Hearth's NUMERICS.md made normative. Meanings reference `canon` functions by hash, so the
canon version sits inside every exact claim's closure. There are two kinds of change:

- **Additive (minor, `canon.v1.1`):** a new named reduction or `canon_v1::` function, for example
  the MXFP4 dot order (later). Existing meanings keep their hashes and evidence; no golden reset.
- **Redefining (major, `canon.v2`):** any change to an existing op-DAG, for example the fixed-chunk
  attention order the GPU tier needs (DR-022), explicit FMA, or a different reduction tree.
  `canon.v2` is by-trigger, and it is the first use of the major-version protocol below.

**A major version never changes what existing source text means.** It introduces a new namespace,
`canon_v2::`, beside `canon_v1::`. The unversioned names (`canon::sum16`, `canon::dot16`,
`canon::sum_seq`, `canon::nan`) denote their `canon.v1` definitions permanently. Otherwise the same
text `canon::sum16(xs)` would denote different op-DAGs depending on the profile in `mith.lock`. Agents
would then read identical code with different bit meanings, which is a reinterpretation the subset
rule forbids (DR-002) and a source of false friends for priors.

Migrated meanings name `canon_v2::` functions, so their source and their hashes change. Unmigrated
meanings keep both. Once a v2 exists, a lint suggests the explicit versioned name.

Correctly rounded `cr::` functions are implementation-independent: a new implementation needs
exhaustive binary32 re-validation per target [G04] but no canon bump. A `canon_v1::` op-DAG change
always needs a major version. Protocol for a major version (defined now; first use by-trigger, with
`canon.v2`):

1. **Draft.** The Author writes the delta with a semantics diff and rationale. New operations pass the
   rewrite list and semantics table first (§6).
2. **Quantify.** Build both versions and measure divergence on the hash corpus and golden prompts
   (fraction of tokens with a different top-1, maximum logit difference), labelled measured.
3. **Admit.** An Owner-signed ADR (AUTHORITY, second channel) records the golden reset scope; Hearth
   needs its own maintainer ADR ([07-hearth-port.md](07-hearth-port.md)).
4. **Regenerate.** A new cross-binary hash corpus under `canon.v2`, reproducible across three runs; the
   `canon.v1` corpus is retained. Tolerance goldens (INV-NUM-1/2) are unaffected unless exceeded;
   bit-exact goldens reset.
5. **Migrate, and invalidate by closure.** `mithc fix` rewrites call sites from `canon::` or
   `canon_v1::` to `canon_v2::`. This is a MeaningChanging fix, applied by the Author because
   meanings change. Migrated meanings get new hashes and start with no evidence, so they are
   re-certified. Facts about unmigrated meanings stay live; nothing about old hashes goes stale.
   `mithc revisit` re-evaluates tombstones whose scope names the numerics version; one rejected
   because "it changes canon" may now fire.
6. **Coexist.** `mith.lock` lists the canon versions a build may use. A logits path compiles against
   exactly one version, so mixing `canon_v1::` and `canon_v2::` names on one logits path is a link
   error. CI builds both for a declared window.
7. **Flip and retire.** The default flips only by ADR, by running the migration across the logits
   path. `canon_v1::` stays addressable for reproducing archived results but is no longer built by
   default.

---

## 13. The honest cost of a Dafny-class verifier (DR-012)

Auto-active verification suits agents better than tactic proofs, but the headline figure does not
transfer by itself. On vericoding's 12,504 specs, the union of models succeeded on 82.2% in Dafny, 44.2%
in Verus and 26.8% in Lean; on identical contracts AlgoVeri reports 40.3%, 24.7% and 7.8% [R03]. Verus
is the Rust-shaped analogue, and Mithril is Rust-shaped; the 82% also reflects a mature verifier on a
benchmark written in its own language.

A Dafny-class verifier would need verification-condition generation over MIR; quantifier instantiation
with triggers, whose brittleness is a known cost of the style [inference]; loop invariants that agents
must supply and repair; frame reasoning, which mutable value semantics simplifies (a callee changes only
what it receives by `&mut`) but does not remove; nonlinear arithmetic; and proof stability across solver
versions. It would also grow the TCB unless every discharge carried a certificate. None of this is in
v0 or v1; it is by-trigger (below).

**v0 scope (M2):** T2 discharges integer and bit-vector side conditions and simple contracts: `#[range(..)]`
on fields and parameters, and `requires` / `ensures` / `invariant` over integers and indices in a
quantifier-free fragment, with bounded quantifiers only where they expand to quantifier-free
obligations. In `kernel` code an unprovable obligation is a compile error. Elsewhere it stays open and
the claim is not admitted. If the author opts for a runtime check instead, the function's computed
`may_trap` fact is set ([01 §12.6](01-language.md)), the trap site is recorded, and the `safe` claim
is `tested`. A trap is an outcome, not a row label ([01 §12.1](01-language.md)). Syntax is in
[01-language.md](01-language.md).

**By-trigger:** when the ledger shows a recurring class of `unknown` obligations in port modules that
the v0 fragment cannot state, a scoped design study opens; that trigger is written now as a design-level
tombstone ([06-forge.md](06-forge.md)). Specs stay the bottleneck either way: Verina measured 52.3% spec
soundness against 72.6% code correctness [RV: D2-E].

---

## 14. What is trusted: TCB inventory and line budgets

The judges found P2's trusted core (over 15k lines, uncapped) too large for one Owner, and P5's roughly
8–10k lines of line-reviewed code the right order. The budget below is a [target] cap on
**line-reviewed trusted code**, allocated from the proposals' [inference] estimates; growth needs an ADR.

| Component | Budget [target] | Basis | Evidence for it | Status |
|---|---|---|---|---|
| `mithcheck` T1 matcher, lifter (shared with T0), footprint check, loop rules | ≤ 3,500 | P5 ≤ 4k [P5 §5.1] | planted corpus of ≥ 200 wrong kernels with zero acceptances [P2 §5.6], one-past stores included; 100% core-mutant kill; second checker by-trigger (ROADMAP D-09) | v0 (M0): X2 spike · v0 (M2) |
| Kernel-subset extractor inside `mithcheck` (planned): re-derives the op-DAG and T2 obligations from the `kernel fn` source (first-order loops, index arithmetic, scalar FP and integer operations), so `mithc`'s KIR becomes only a hint and a cache key and elaboration leaves the trust base | within the T1 row's ≤ 3,500 (adds nothing to the total) | [ARCHITECTURE §8.2](../ARCHITECTURE.md) | planted mis-elaborations (swapped operands, a dropped operation, a missing overflow obligation) with zero acceptances; differential against `mithc`'s KIR | by-trigger (ROADMAP D-23): any elaboration bug found that changed a KIR DAG, or before the first grant or ADR that rests on T1 evidence (with D-09) |
| T0 binary confinement pass: allowlist, SFI pattern, stack and ABI checks (§6.2) | ≤ 500 [re-estimate after X0] | reuses the T1 decoder and lifter | planted policy hacks, including clock reads through KUSER_SHARED_DATA, return-address stores and DF left set | v0 (M4) |
| T2 certificate checkers (LRAT, Alethe/CPC subset) | ≤ 800 | P2 caps mithcheck at ≤ ~6k [P2 §5.1] | malformed-certificate corpus | v0 (M2) |
| Gate: promotion rule, α accounting, authority, signing | ≤ 1,200 | P2 ≤ ~3k; P5 ~2k with the harness | attack suite including the ADR-0009 bypasses | v0 (M3) |
| Measurement service: clock, joins, poisoning, interleaving, fingerprint | ≤ 1,500 | same | planted timing hacks (§10) | v0 (M0 kit; M2) |
| Ledger kernel: schema, signatures, invalidation, AUTHORITY checks | ≤ 800 | P4 "small" [P4 §5.1] | property tests; replay of Hearth history | v0 (M3) |
| Audited `std_platform` Unsafe | ≤ 1,500 across OSes | G05 "a few hundred lines per OS"; the M4 gate ([ROADMAP §5](../ROADMAP.md), P5's cap) | human review; ASan, TSan, permutation scheduler | v0 (M4) |
| **Total line-reviewed code** | **≤ 9,800** | P5's ~10k | | |

**Trusted data and code, validated empirically rather than line by line:**

| Component | Role in §3.4 | Grade | Evidence and mitigation |
|---|---|---|---|
| Semantics table and generator (1.5–3k lines [G02]) | premise | `validated(partition)` / `validated(exhaustive)` per entry and fingerprint | review concentrated on the ~10 FP-sensitive mnemonics; silicon case classes; Bochs; load-time self-test (§6.7) |
| Rewrite list (≤ 30 rules) | premise | `validated(exhaustive, partition)` | each rule proved (§6.3) |
| Store-core theorem and its bounded model | premise | `validated(bounded: depth 6, n_slots ≤ N, threads ≤ T)` | chaos suite; 100% core-mutant kill (§3.3) |
| **Elaboration of exact meanings into KIR, comptime included** (`mithi` in comptime mode, DR-010) | code | `tested` | Comptime results (constants, tables, shapes) feed the meaning before KIR and T1. A comptime bug would change both sides of T1 consistently, so T1 cannot catch it. Mitigation: kernel-reachable comptime values are recomputed at build by a second evaluation path that shares no front end with `mithi` (the comptime code compiled through B1 and run natively [inference]), and byte equality is required. In addition, `mithi` runs the meaning differentially on the hash corpus, and intent claims are checked against the numpy reference (§8.4). This is the v0 model, and DR-021 holds under it because the component sets only the code floor. The by-trigger kernel-subset extractor (budget table above, ROADMAP D-23) removes elaboration from the trust base |
| **Comprehension-harness scorer and hidden oracles** (Gatekeeper-owned, sealed; [05 §13](05-agent-protocol.md)) | outside any claim's TB; decides DR-017 kills, B2 and F1-A promotions | `tested` | built by the frozen bootstrap toolchain; hash-locked suites; every oracle kills ≥ 95% of mutants; a blind Adversary batch of planted wrong and `abandon`-bait submissions is scored among real attempts each epoch; counters 30–34 (§10). Its size grows with the suites, so it is not line-budgeted |

| Trusted outside the budget (axiom) | Mitigation |
|---|---|
| CPU, microcode, OS; conformance of the target CPU to the table on the case classes used, and uniformity within each class | silicon case-class runs per table entry; load-time self-test on each machine (§6.7). The default MXCSR is not an axiom: it is a runtime-checked entry (§3.4) |
| Caller contracts at seams (`assumed(caller_contract)`, only where a seam does not check its domain) | Owner-signed, expiring; run-time domain check is the default (§2.4) |
| C compiler **for non-kernel code** (store, parser, API) | `mithi` differential tests, Hearth's C tests, hash corpus; no translation validation is planned for control-heavy code ([04-toolchain.md](04-toolchain.md)) |
| XED decoder | differential decode during audits |
| Rust toolchain building F0 | frozen bootstrap pinned by hash; candidate compilers never build F0 |
| Lean kernel (later) | Comparator-style gate with multi-kernel replay [R07] |
| ptxas and driver JIT (owner-gated GPU tier) | SASS level graded `tested` by the hash corpus (DR-022) |
| The Owner and the Owner's tokens | second channel; offline backup |

**Not trusted:** the front end and type checker (advisory for policy code, differential-tested by
`mithi`; theorem statements in [01-language.md](01-language.md)). The one exception is the
elaboration of exact meanings, comptime included. It defines what T1 compares against, so it is
listed above with its own grade, until the by-trigger kernel-subset extractor makes `mithc`'s KIR
only a hint. Also not trusted: lowering, schedules and schedule
primitives (completeness only), the C compiler for kernels (object audit), SMT solvers (certificates),
cost models and simulators (rank only), the Forge, and every agent.

---

## 15. Reviewer notes and open problems

Reviewer note 1. The outline's verb list omits `abandon` (named there as a role verb) and has no
Owner-signing verb; this document uses `mithc abandon` and `mithc ledger sign --authority`.

Reviewer note 2. The outline states the NaN-order condition in terms of MAXPS/MINPS, which is not
sufficient alone: sign-driven selects, bitwise reinterpretation and stores also observe NaN payload or
sign. §6.3 states the general condition, keeping MAXPS/MINPS as a conservative case.

Reviewer note 3. DR-019 (file-per-fact in git) is kept. Merkle checkpoints are v0 (M3). SEAL compaction
(§4.2) is by-trigger under ROADMAP D-13: "git on `.mith/ledger/` exceeds the CI budget". Measure
scaling on Windows before M3.

Reviewer note 4. The outline does not define `proof` versus `validated`, and P2 and P5 disagree. This
document adopts P2's derivation-versus-execution semantics for the evidence **form** (§2.3). The
effective grade then meets the premise components, while code components form a printed code floor
(§3.2, §3.4). This one rule reconciles three instructions:

- "confined admits proof only" constrains the form;
- "confinement stays tested until mechanised" is the code floor;
- "exact kernels require validated" (DR-021) is met by T1 over `validated` table entries.

Under these definitions silicon fuzzing reaches only `validated(partition)` over a declared case
partition (§6.7). It answers DECISIONS reviewer note 3, including its question about SMT: a checked
certificate is `proof` in form.

Reviewer note 5. The canonical `acquire` snippet (ARCHITECTURE §5.3's form, which returns
`Result<Frozen<SlabBuf>, IoError>` so that I/O faults surface as `Err`, O5) cites a golden (boundary
grade `tested`) while DR-010 grades the store-core theorem `validated`; §3.3 shows the citation
upgrade.

Reviewer note 6. The Mithril repository on the Owner's machine sits under a OneDrive folder. If it
syncs, keys, raw samples and private traces must live outside it.

Reviewer note 7. With DR-015's `e ≥ 20` per test, a probability-style α budget below 1 allows very few
tests per period, so §7.2 reads the union-bound tier (defaults and F1-A) as a bound on expected false
promotions, and grant-promoted profiles get online FDR control (e-LOND, [06 §6.5](06-forge.md)). The
Owner sets the per-period budget, q and γ.

Reviewer note 8. **Follow-ups in sibling documents.** This document settles each of the points
below; the siblings cite it rather than restate it differently. Status after the residual-fix round
of 2026-10-11:

- **Resolved:** [ARCHITECTURE §8.1](../ARCHITECTURE.md) now meets premise components and prints the
  code floor; ARCHITECTURE §8.5 and [06 §8.1](06-forge.md) print §7.1's block (no separate strength
  conjunct; `code_floor` line added); ARCHITECTURE §8.9 uses §14's rows and the elaboration row with
  the D-23 extractor plan; DECISIONS DR-003, [04 §6.3/§6.6](04-toolchain.md) and
  [05 §6, §9](05-agent-protocol.md) say "trap" and cite [01 §12](01-language.md).
- **Open (not yet checked):** [01 §11](01-language.md) and [04 §6](04-toolchain.md) should carry the
  seam rule of §2.4 ([04 §6.9](04-toolchain.md)'s "discharged at every call site" holds only for
  Mithril callers); [04 §7.2](04-toolchain.md) should list the footprint check (§6.3) among the
  lifter's steps and the pinned policy flags (§6.2) in the flag table; [05 §13](05-agent-protocol.md)
  and [06 §10](06-forge.md) should cite counters 30–34 (§10).

Open problems: the census may show lowerings the loop rules cannot relate (the X2 kill criterion
decides); the store-core theorem's bounded model must be shown to cover the real `std_platform`
semantics, and it needs a cutoff argument before its bound can be dropped (§3.3); whether MSVC
preserves T0's SFI pattern in policy objects is unmeasured (X0 decides how often the slower SSA route
runs); injection-follow rates have no baseline; and separating the gate principal on Windows costs
usability.
