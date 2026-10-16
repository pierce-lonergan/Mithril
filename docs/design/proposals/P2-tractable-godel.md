# P2: Mithril as a Tractable Gödel Machine

Status: design proposal P2, phase 1 (architecture). Written 2026-10-11.
Lens: **trust**. Tie-breaker: **soundness and evaluator integrity**.
Inputs: `brief.md`, `design-inputs.md` (authoritative), `draft-thesis.md`, the digest, and the dossiers in
`Mithril/docs/research/`. Dossiers are cited as (R01)…(R13), (G01)…(G05). Nodes of `revisited-ideas.md` are cited as
(RV S1), (RV D2-A) and so on. Numbers carry their measured or simulated label from the source (INV-HONEST).
**[inference]** marks my own reasoning or estimates. **[DEVIATION]** marks a departure from `design-inputs.md`.
**[EXTENSION]** marks something those inputs do not cover.

---

## 1. Thesis and design principles

### 1.1 Thesis

Mithril is a conservative, Rust-shaped systems language. Every definition is stored with its **claims**:

- **What it computes:** a sealed executable meaning, or a contract.
- **What it may touch:** effects and capabilities.
- **How exact it is:** a fidelity grade crossed with a determinism scope.
- **How fast it is, and on which machine:** quantities that carry a unit and an origin.

Every claim carries evidence of a declared grade, recorded in one content-addressed evidence ledger.

The central construction is the **certified modification space**. Examples are timing-only resource policies,
schedules that preserve the op-DAG, exact-rewrite licences and exact re-layouts. Each is a class of edits that the
trusted core shows **once** to be unable to change outputs. After that, membership in the space replaces a
per-candidate correctness proof. Membership is checked by a confinement pass or by a mechanical, decidable certificate.

This is what makes the Gödel machine tractable. Schmidhuber's switch rule needs a proof that a rewrite raises
utility. That proof is intractable, and no formal timing model of an out-of-order core exists (RV §5.12). Mithril
splits it into two parts:

- *"Every member of this space preserves outputs."* This is proved once, over a small core.
- *"This member is faster on this machine."* This is an anytime-valid statistical test that spends a declared error
  budget.

The Darwin Gödel Machine supplies **what to try**: an open-ended archive with clade selection. Mithril supplies the
**judge** the DGM lacked:

- a small, frozen, adversarially tested trusted core;
- role-separated authority over specs and evaluators;
- a runtime that owns the clock.

Hearth is the right acid test for two reasons. It already has the normative numerics (`docs/NUMERICS.md`), an
invariant lane and a golden oracle. And its memory-bound physics places most of its profitable changes (eviction,
prefetch, placement, schedules, layouts) inside spaces that preserve outputs.

### 1.2 Principles

1. **Every claim is graded.** Nothing is called "verified" without saying three things: by which checker, against
   which spec hash, and on which trust base. Evidence is ordered: proof > validated > tested > measured(hw) >
   assumed(owner, expiry). An unlabelled number cannot be printed.
2. **Prove the space, not the candidate.** Wherever possible, a modification is safe because of its *type*, so the
   Forge needs only performance evidence.
3. **The trusted core is small, frozen and attacked on purpose.** The core is the checker, the semantics tables, the
   space theorems, the gate and the measurement harness. Everything else is untrusted and checked: the front end, the
   optimiser, the backends (including the C compiler), the LLMs, the solvers and the search.
4. **Powers are separated.** Whoever writes a spec never writes its implementation or the gate. Whoever is judged
   never holds the clock or the reference outputs. Authority is a capability held by a role, never an instruction in
   a prompt.
5. **Exact by default.** Canonical IEEE numerics are the default semantics. Losing bits is an explicit, opt-in grade.
   INV-LOSSLESS-DEFAULT becomes a link error.
6. **Familiar where meaning matches, loud where it differs** (G01, RV D3-i). Anything that looks like Rust means what
   it means in Rust. Every new meaning gets a new keyword, type or name.
7. **A signature is a sufficient summary.** Types, effects and capabilities, grade, and contract together say
   everything a caller needs. There is no ambient authority, so a callee's body never has to enter an agent's
   context.
8. **Objectives follow physics, and numbers are honest.** Objectives are bytes per token and stall time, never hit
   rate or IPC. Every result is checked against a physical lower bound; a result that beats one is quarantined.
9. **Accumulate; never erase.** Archive entries, evidence and tombstones are content-addressed and append-only. A
   change makes old evidence stale; it never deletes it.
10. **Measure the central claim, including against Mithril.** Every surface and stdlib decision passes through a
    cold-agent harness with C and Rust control arms and pre-registered kill criteria.

---

## 2. Layered architecture

```
+-----------------------------------------------------------------------------------------------+
| L0 AGENTS IN ROLES: Author | Builder | Prover | Adversary | Gatekeeper  (+ human Owner key)    |
|    each session holds exactly one role token -> write capabilities in L2                       |
+---------------+-------------------------------------------------------------------------------+
                | text views, hash-anchored edits, JSON diagnostics, obligations (CLI / LSP / MCP)
+---------------v-------------------------------+
| L1 CANONICAL TEXT (.mith)                     |  Rust-shaped; one Lark grammar; mithc fmt is an
|    Tier-0 card <= 8 KB; typed holes ?h: T     |  AST<->text bijection; no layout-sensitive meaning
+---------------+-------------------------------+
+---------------v-------------------------------+     +============ TRUSTED CORE (frozen, hash-pinned) ======+
| L2 CODEBASE STORE                             |     | semantics: Core semantics (Lean 4, executable)       |
|  defs keyed by BLAKE3(alpha-normal AST+deps)  |     |            x86 table keyed by XED iclass; PTX later  |
|  mith.lock names->hashes; sealed modules       |     | mithcheck: T0 confinement pass (policies, evolve)    |
|  (meanings, specs, goldens, gate) role-owned   |     |            T1 IEEE-exact DAG matcher on object code  |
|  Fact Plane (Datalog): types, caps, evidence   |     |            T2 certificate checker (LRAT/Alethe/CPC)  |
+---------------+-------------------------------+     |            T3 tolerance-bound checker (opt-in)       |
+---------------v-------------------------------+     |            T4 Lean kernel via Comparator-style gate  |
| L3 FRONT END (untrusted): parse -> hir        |     | space theorems: timing_only store core (O1-O5),      |
|    names, types, effects/caps, grades,        |     |            exact-rewrite list soundness               |
|    spaces (fast, advisory), refinements, holes|     | gate:      promotion rule, alpha budget, authority   |
| L4 MIDDLE: core IR -> loop IR (meaning+sched) |     | harness:   clock, async joins, poison, A/B, hw print |
|    -> tir; salsa queries keyed by hash        |     +=====+===================+=======================+=====+
| L5 BACKENDS (untrusted): C11 | direct x86 |   |           ^ object code       | signed verdicts       |
|    copy-and-patch | PTX (owner-gated) | LLVM  |-----------+ (lifted, matched) v                       |
+---------------+-------------------------------+     +-------------------------------------------------+
+---------------v-------------------------------+     | L6 EVIDENCE LEDGER (append-only, gate-signed)   |
| L7 FORGE (untrusted search)                   |<--->|  key = H(closure, spec, toolchain, target, hw)  |
|    proposes only inside declared spaces;      |     |  claims, grades, tombstones, PruneCerts,        |
|    QD niches, clades, cascade, replay bounds  |     |  quarantine, staleness, alpha spent             |
+---------------+-------------------------------+     +-------------------------------------------------+
+---------------v-------------------------------------------------------------------------------+
| L8 RUNTIME: persistent pool, disjoint par-for, expert store with hint ports, residency tiers,  |
|    direct I/O, ISA dispatch, epoch commit / hot swap, immutable weights + overlays,            |
|    measurement mode (the harness from the trusted core)                                        |
+---------------+-------------------------------------------------------------------------------+
+---------------v-------------------------------------------------------------------------------+
| L9 TARGETS: x86-64 scalar | v3 AVX2(+AVX-VNNI) | v4 AVX-512 F/BW/VL/VNNI/BF16 | arm64 NEON |   |
|    sm_120 PTX expert tier (owner-gated)                                                        |
| L10 HARDWARE: Zen 5 cores (2 CCDs) | DDR5 | RTX 5070 12 GB VRAM | 990 PRO NVMe | USB HDD        |
+-----------------------------------------------------------------------------------------------+
```

| Layer | Responsibility | Trust status |
|---|---|---|
| L0 Agents | Propose specs, implementations, proofs, attacks and promotions, each within one role | Untrusted. Bounded by role capabilities |
| L1 Text | The only agent-facing code form. Canonical, formatter-enforced | Untrusted input |
| L2 Store | Content identity; role-owned sealed modules; the Fact Plane for queries and capability audits | Integrity via hashes. Policy enforced by the gate |
| L3–L4 Front/middle | Fast typing, effect, grade and space checks; lowering meanings and schedules to `tir` | Untrusted. Its verdicts are advisory until mithcheck agrees |
| L5 Backends | Emit C11, x86, PTX, stencils | Untrusted. T1 validates their *output* |
| Trusted core | Check evidence, define semantics, decide promotions, own measurement | Trusted. Small, budgeted, adversarially tested |
| L6 Ledger | Durable memory for every judgment, positive or negative | Integrity via gate signatures and Merkle root |
| L7 Forge | Open-ended search inside certified spaces | Untrusted |
| L8 Runtime | Execute deterministically; enforce hint validation, fuel and placement rules | The store core is covered by a space theorem; the audited stdlib layer is tested |
| L9–L10 | ISA tiers and devices as data | Assumed, with semantics fuzz-validated on silicon (G02) |

The key property of the diagram: **no arrow from an untrusted layer reaches the ledger except through mithcheck or
the gate.** The front end can tell an agent "this looks like a valid schedule" in milliseconds. Only mithcheck's
verdict on the emitted object code becomes evidence.

---

## 3. The language core

### 3.1 Surface policy

The surface is a standalone `.mith` language with Rust-shaped syntax (G01, R03). There is one normative Lark grammar
that fits OpenAI's CFG-tool limits, and a canonical formatter. Rust tokens keep their Rust meaning, including:

- `f32` `+` and `*`, which are IEEE operations with no contraction;
- `mul_add`, which is a fused multiply-add;
- `iter().sum()`, a sequential left fold;
- `f32::max`, with Rust's NaN rule;
- `Result` and `?`;
- `match` and traits.

Each deviation gets a new name, and the false-friends table in the Tier-0 card lists them all:

| Looks like | Mithril meaning | Why it is loud |
|---|---|---|
| `&T`, `&mut T` | Second-class references: cannot be stored in fields or returned | Misuse is a compile error (E-REF-2ND) with a fix-it. It is never silent |
| Integer `+` | Overflow always traps (`Fail`) unless proven absent; `wrapping_add` is explicit | Same as Rust debug builds. The release-mode wrap is not a Mithril behaviour |
| canonical tree sum | `reduce::<Tree16>()` / `sum16()` | A new name. `sum()` stays sequential |
| x86 `MAXPS` operand rule | `max_x86(a, b)` | A new name. `f32::max` keeps the Rust rule |
| effects | `uses [Io, Spawn]` in signatures | A new keyword |
| meaning, schedule, policy, spec, claim, layout, evolve | New keyword-led items | No Rust lookalike |

There is also an untrusted Python schedule and search API (settled constraint). It emits schedule data only, and that
data is checked like any other schedule.

### 3.2 Illustrative snippets

**(a) A quant layout type.** This is Hearth's `hx_block_q4`: 34 bytes, with byte *j* holding element *j* in its low
nibble and element *j*+32 in its high nibble, stored as q+8.

```mith
layout Q4H = block_scaled {
    block: 64,
    elem:  u4 { value = (raw as i8) - 8 },           // stored q+8, value range [-8, 7]
    scale: f16 per_block { decode = f16_to_f32 },
    order: [scale, elems],                            // 2 + 32 = 34 bytes
    pack:  nibbles { lo: 0..32, hi: 32..64 },
}
layout MXFP4 = block_scaled { block: 32, elem: e2m1, scale: e8m0 per_block };   // OCP MX v1.0
static_assert!(size_of::<Block<Q4H>>() == 34);
```

From one declaration the compiler derives `pack`, `unpack`, `dot_i32` (exact) and layout tests. Each derived pair
carries a round-trip obligation that T2 discharges per layout instance.

**(b) The Q4 matvec: one meaning and one schedule, under exact numerics.**

```mith
#[grade(exact, det = cross_device)]
meaning fn matvec_q4<const R: usize, const C: usize>(w: &Mat<Q4H, R, C>, x: &[ActQ8; C / 64]) -> [f32; R]
where C % 64 == 0
{
    from_fn(|r| {
        let mut acc = 0.0f32;
        for g in 0..C / 64 {                                      // sequential in g: part of the meaning
            let isum: i32 = Q4H::dot_i32(&w[r][g], &x[g].q);      // exact integer: order is free
            acc = acc + (isum as f32) * (w[r][g].scale() * x[g].d);   // Rust meaning: no contraction
        }
        canon_nan(acc)                                            // 0x7fc00000
    })
}

schedule matvec_q4_v4 for matvec_q4 on x86_64::v4 + [avx512bw, avx512vnni] {
    tile r by 16; vectorize r.inner as lanes(16);     // lane = row, so each row's g-order is untouched
    parallel r.outer over pool chunks(dynamic);       // disjoint writes: each row has one writer
    lower Q4H::dot_i32 via vpdpbusd licence int.ring with bias(8 * x[g].sum);   // Σnib·q − 8Σq
    prefetch w[r][g + 4] to L2;                       // timing-only: no value effect
}
```

The `isum as f32` cast must be exact, which needs |isum| < 2^24. That follows from the ranges: |isum| ≤ 64·8·127 =
65,024. T2 discharges the obligation from the refinement types (`ActQ8.q: i8 in -127..=127`). A second schedule,
`matvec_q4_v3` for AVX2, and the scalar lowering are siblings. All three are certified against the same meaning. This
is how INV-DET-3 stops being a test and becomes a per-build certificate.

**(c) A cache policy under `timing_only`.**

```mith
policy EvictPredictive<P: opaque>: timing_only {
    state { score: [f32; MAX_SLOTS], ghost: Ring<ExpertKey, 4096> }        // fixed size, no heap
    fn victim(&mut self, cands: &[Cand<P>], pred: &RoutePred) -> Hint<SlotIdx> {
        cands.min_by_key(|c| self.score[c.slot] + 3.0 * pred.p_next(c.key)).hint()
    }
    // c.bytes()          -> E-TIMING-01: P is opaque (payload parametricity)
    // fp::set_rounding() -> E-TIMING-03: FP-environment write is not in timing_only
}
core ExpertStore {
    hint port evict: EvictPolicy fallback Lru validate evictable wrap robust(Lru, eps = 0.02)
        budget fuel(4 * n_slots) off_lock(snapshot) eject_after 16;
    theorem output_noninterference cert "store-core@b3:9f1c…";   // proved once, in the trusted core
}
```

**(d) A spec with escrow and evidence requirements.** This example uses routing, where Hearth has a real false friend:
ties go to the lower index.

```mith
spec topk_route by role(author) sealed h:3fa0… {
    fn route<const E: usize, const K: usize>(logits: &[f32; E]) -> [u32; K]
    requires K <= E
    ensures result.is_sorted_by_key(|i| (Desc(logits[i]), i))    // ties -> lower index
    ensures forall j !in result: rank(logits, j) > rank(logits, result[K - 1])
    fault_model numerics_v1 + routing_v1;      // tie flip, NaN order, k off-by-one, ...
    rejects witness [first_k, sort_unstable];  // vacuity check: these must fail
    require strength >= 0.97, unknown <= 0.02, independence(author, adversary) = distinct_family;
}
claim route_avx512 refines topk_route   require proof | validated;   // tested is not enough
claim route_avx512 perf: Quantity<ns_per_call, Measured>
    require e_value >= 20 vs route_scalar on hw("9950x/ddr5-6000-2ch/990pro");
```

**(e) An effectful direct-I/O function with capabilities.**

```mith
fn read_slab(file: &File<Direct>, at: Offset<4096>, buf: &mut SlabBuf<4096>) -> Result<(), IoError>
    uses [io::Read]
{
    file.read_at(at, buf.bytes_mut())        // Win: OVERLAPPED + NO_BUFFERING, wait; POSIX: pread + O_DIRECT
}
fn admit(buf: SlabBuf<4096>, want: SlabHash) -> Result<Frozen<SlabBuf<4096>>, IoError> {
    if blake3(buf.bytes()) != want { return Err(IoError::Corrupt) }   // obligation O4: lossless tier
    Ok(buf.freeze())                                                   // linear -> shared, refcounted
}
```

`read_slab` cannot be called without an `io::Read` capability. Capabilities descend from `main(root: Root)`.
`Offset<4096>` and `SlabBuf<4096>` make direct-I/O alignment a type error rather than a runtime `EINVAL`.

### 3.3 Types

- **Scalars and data:** fixed-width integers; `f16`, `bf16`, `f32`, `f64`; structs, enums, tuples and arrays with
  exact layout control (`#[repr(C)]`, `static_assert!`). Little-endian decoding helpers and bit-casts have no UB.
- **Refinements and indices** (Flux-style, R07). Examples: `i32 in -127..=127`, `[T; N] where N % 64 == 0`,
  `Offset<4096>`, `ExpertId<E>`. Obligations go to T2. Inside kernels they cost nothing at runtime, because a check
  that cannot be proven becomes a compile error, never a silent runtime check (R11's bounds-check-cost risk).
- **Layouts** (§3.2a) and **tensors** `Mat<L, R, C>` with a layout/tile algebra (logical-to-storage maps with provable
  contiguity). Block-sparse iteration comes in two forms: static masks and data-dependent block lists. MoE routing is
  the second kind (R13).
- **SIMD types** are `Vec<T, N>` with opmasks, used only inside schedules and `instr` libraries. Every `instr` is
  generated from the owned semantics table (G02), which closes Exo's unchecked-`@instr` gap by construction.
- **Quantities:** `Quantity<Unit, Origin>`, where `Origin ∈ {Measured{hw, load, baseline}, Simulated{model},
  Predicted, Bound{tier}}`. The formatter refuses to print an untyped performance number (RV D2-C). Dimension errors
  are type errors; the `/tok` vs `*tok` class becomes impossible.
- **Linear resources:** `linear struct`. Files, leases and slab buffers must be consumed exactly once.
- **Weights:** `Weights<V>`, where V is a version root over base + overlays (R12). Mixing tensors from two versions in
  one forward pass is a type error.

### 3.4 Effects, capabilities and the lattices

**Effects are capabilities** (R09). The built-in capabilities are:

`Io` (subdivided: `io::Read`, `io::Write`, `io::Dir`), `Spawn`, `Alloc<A>`, `Nondet`, `Time`, `Fail`, `Cancel`,
`FpEnv`, `Unsafe`, `Foreign`, `Device<D>` and `Compile`.

- Within a body, effects are inferred. At module boundaries they must be written out.
- Handlers are tail-resumptive or one-shot only, compiled by evidence passing.
- A long-lived service captures capabilities through `scope.service(..)`, and every capture appears in the capability
  audit graph in the Fact Plane.
- Unsafe and Foreign grants are made per package in the manifest.

Mithril tracks five orthogonal lattices. Each is checked separately, and four cross rules tie them together.

| Lattice | Elements | Attached to |
|---|---|---|
| Integrity | `timing_only` ⊂ `value` | functions and modules |
| Fidelity | `exact` ⊑ `real(bound)` ⊑ `approx(profile)` | values and functions |
| Determinism scope | `cross_device` ⊑ `device(t)` ⊑ `schedule_dependent` | values and functions |
| Evidence | proof > validated > tested > measured(hw) > assumed | claims (not values) |
| Confidentiality | `Pub` ⊑ `Tenant<t>` ⊑ `Top` | server cells. v1 ships the lint and flush only (RV D3-iii) |

The cross rules:

- **C1.** `Nondet` inside an `exact`/`cross_device` result is legal only through a `deterministic { }` boundary.
- **C2.** A `device(t)` value must not flow into a computation whose placement is decided at runtime (G03).
- **C3.** `approx` data reaching top-k or argmax requires a route-agreement metric in its quality certificate (RV S7
  R2).
- **C4.** `timing_only` code can affect value code only through validated hint ports.

The integrity certificate is what makes confidentiality tractable, because hints cannot change values (RV §6.9).

### 3.5 Memory model

The memory model is mutable value semantics with second-class references, linear resources, and two derived kinds:
`transfer` (Send-like) and `share` (Sync-like) (R09, G05). There are no lifetimes, no GC, no regions or cowns, and no
epoch reclamation in v1.

Below the language sits an **audited stdlib layer**, the only place `Unsafe` appears. G05 estimates it at a few
hundred lines per OS [inference]. It provides:

- `Mutex<T>` with a scoped `with_lock(|inout s| ..)`, and `Condvar`;
- `Arena::split` into owned, 4096-aligned `SlabBuf`s;
- `Frozen<T>` with `into_unique`;
- `File::read_at`;
- scoped threads and services;
- an optional MPSC ring.

G05 found that Hearth's `store.c` is expressible on top of this layer with **no user-level Unsafe**. The store is one
monitor over integer-handle metadata; slab bytes follow LOADING → READY(refs>0) → evictable.

Every synchronisation primitive goes through the stdlib. A test build can therefore swap in a loom-style
permutation scheduler. That scheduler is the liveness oracle, because blocking bugs occur in safe code (G05: Qin et
al.).

**The `deterministic { }` boundary** is a trust hole if declared casually, so it is restricted (my resolution of G05's
open question):

- Only a module whose manifest grants it the `DeclareDeterministic` authority may contain one.
- Each boundary must cite evidence: a space theorem or a named golden test.
- **The boundary's evidence grade flows to everything downstream.**

For the store, the citation is the `output_noninterference` theorem itself (§5.3). If that theorem is backed by a
bounded model check plus a chaos suite, INV-DET-1 for the store path is honestly graded `validated`, not `proof`.

### 3.6 Numerics

The default numeric semantics are:

- **Strict IEEE:** no contraction, no reassociation, no FTZ/DAZ.
- **Explicit `fma`.**
- **Canonical NaN:** `canon_nan` stores 0x7fc00000.
- **Named reduction orders:** `lanes(16).tree(8,4,2,1)`, `blocks(64, exact_i32).seq`, `chunks(c, seq).seq`.

**Exact integer accumulators with overflow proofs license reordering.** This is the route to bit-exact VNNI, dp4a
and INT8 tensor cores (G03). The whole design depends on three further rules:

1. **The FP environment is an effect.** Changing MXCSR requires `FpEnv`, which no `exact` code holds. The runtime
   asserts the default MXCSR at worker start and after every policy call. Every T1 certificate records "default
   MXCSR" as a discharged precondition (G02).
2. **Transcendentals are specified functions.** The language default is `cr`: correctly rounded, round-to-nearest. For
   binary32 it is validated exhaustively over all 2^32 inputs per target, in seconds to minutes per function (G04). The
   alternative, `canon.vN`, is a versioned DAG of basic operations that T1 certifies structurally. G04 measured a
   no-FMA canon expf prototype at 0.204 ns/element on AVX-512, against 1.12 ns for scalar UCRT expf, and found it
   bit-identical across scalar, AVX2 and AVX-512. Platform libm is reachable only via `Foreign` with
   `nondet(platform)`, which the exact grade rejects. The reason: UCRT switches FMA3 paths at startup, and the two
   paths differ on 44,232 sinf inputs (measured, G04). G04 leaves the `cr`-versus-`canon` default open; I choose `cr`
   for the language because its meaning does not depend on any implementation. Hearth chooses per function in
   ADR-0010 (§9).
3. **Grades are checked.** `real(bound)` requires a T3 certificate plus runtime margin checks at discontinuities.
   `approx(profile)` requires a statistical quality certificate (KL divergence, flip rate, route agreement).
   `#[default]` on a non-`exact` configuration is a link error (INV-LOSSLESS-DEFAULT).

### 3.7 Staging and specialisation

Staging is typed and two-stage, following R09:

- Same-language `comptime`.
- `Code<T>` quotes, generative only in v1, which keeps the MetaOCaml guarantee that well-typed generators emit
  well-typed code.
- Binding-time types `#[bind(build | load | call(buckets))]`.

Specialisation keys must have a finite kind: enums, bounded integers, shapes and dtypes. Specialising on weight
*values* is rejected (RV §5.4).

Every specialised residual carries a **residual contract**: it must refine the generic definition. Kernels are checked
by T1 lockstep. Other code is checked differentially, graded `tested` (RV S10). Load-time specialisation to a
`.hearth` file (shapes, dtypes, layer kinds) produces shape-specialised kernels. These are cached in the ledger by
hash(model header, target, toolchain), so a second load costs a lookup.

One meaning plus N schedules replaces Hearth's scalar, AVX2 and AVX-512 triplets.

### 3.8 Modules, packages and editions

Definitions are content-addressed: names are metadata, so a rename changes no hash. On disk, a repository is canonical
text plus `mith.lock`. The manifest `mith.toml` declares:

- capability grants (Unsafe, Foreign, DeclareDeterministic) per package;
- **sealed modules** (meanings, specs, goldens, gate policy) and the role that owns each;
- invariant texts, hash-locked;
- per-slot evidence requirements;
- the edition.

**Contract variance lattice** (RV D2-F): extensions are free. A weakening needs authority and opens typed holes in
every dependent, FFI mirrors included. This would have caught Hearth's `read_errors` ABI break.

`export abi` blocks generate the C header, ctypes bindings and layout tests from one source, with mandatory
`struct_size` fields (R11).

Editions change the language. Each comes with a formal-spec diff and a `mithc fix` migration that preserves the whole
corpus bit-exactly (R01).

---

## 4. Compiler pipeline, IRs and backends

```
.mith --parse--> ast --resolve, type, effect, grade, space(advisory)--> hir   [content hash computed here]
hir --elaborate--> core IR (capabilities as evidence params, MVS moves explicit, grades explicit)
      +--> Lean reference interpreter (differential testing of mithc; never on the build path)
meaning fns: core --> loop IR (index-typed op-DAG; reduction orders named; layouts explicit)
      --apply schedule (Exo-style rewrites; dependence/effect legality)--> scheduled loop IR
      --select instrs from semantics-table instr libraries--> tir (SSA over table instructions)
other code:  core --> C11, or core --> tir
backends:    C11 (strict FP flags) | x86 encoder from tir | copy-and-patch stencils | PTX text | LLVM (optional)
validation:  object code --decode (XED iclass)--> lifted tir --T1 match vs loop-IR DAG, T2 side conditions--> witness
facts:       every phase emits Datalog relations into the Fact Plane
```

- **IRs.** `ast` (syntax), `hir` (resolved and typed; the unit of identity), `core` (the small calculus that the Lean
  reference semantics interprets), `loop` (meanings and schedules), `tir` (target SSA). Five IRs, each with one job.
- **Incremental, query-based** (salsa style). Queries are keyed by content hashes plus a toolchain hash: `type_of`,
  `effects_of`, `lower(def, target)`, `certify(def, spec, target)`. The ledger is the persistent tier for the
  expensive queries (`certify`, `prove`, `measure`). Upgrading the compiler invalidates nothing silently, because the
  toolchain hash is part of every key.
- **Diagnostics.** JSON first, rustc applicability levels, SARIF 2.1.0. Root causes are grouped and cascades folded
  (RustAssistant: 4.97% → 44.76%, R03). Nearest-name suggestions catch hallucinated APIs. Semantic fix-its carry
  obligations ("re-certify on v4", "re-measure").
- **Backend sequencing.**
  1. **C11 first** (M2–M5). It uses strict FP flags (`/fp:precise`, `-ffp-contract=off`) and emits Hearth's internal
     `hx_*` symbols behind the existing seams. It has no runtime, so INV-DEP holds in spirit.
  2. **Direct x86 emitter** for the staged-kernel subset (M6).
  3. **Copy-and-patch** for load-time specialisation, under W^X with `FlushInstructionCache` (later).
  4. **PTX expert tier** (M7, owner-gated): explicit `.rn`, loaded through `nvcuda.dll`.
  5. **LLVM** stays optional at any time. Because T1 validates outputs, adding a backend adds no trust.
- **[DEVIATION] T1 validates object code from every backend, including the C compiler,** from M0 onwards.
  `design-inputs.md` scopes T1 checking to the direct x86 emitter's subset. Validating MSVC and clang output
  puts the C compiler *outside* the TCB on day one. It also lets M0 certify INV-DET-3 for today's hand-written C
  kernels before any Mithril syntax exists. The evidence for feasibility: Hearth's AVX2/AVX-512 kernels use about 105
  instruction forms (74 mnemonics), of which about 10 are FP-sensitive (G02), at a fixed 64-element block size, and
  KLEE-FP's symbolic matching of SSE kernels is the precedent (R07). The risk is compiler output with spills and
  horizontal shuffles. The fallback is per-block exhaustive or T2 checking, or validation restricted to our own
  emitter. M0's kill criterion decides this (§10).
- **Self-hosting** comes only after the Hearth port. A candidate compiler, whether Forge-produced or an untrusted
  rebuild, never builds the gate, the checker or the harness. Those are built by a frozen bootstrap toolchain pinned
  by hash, to avoid the trusting-trust problem (R01).

---

## 5. Verification and evidence

### 5.1 The trusted core

| Component | Content | Size budget [inference] | Evidence for it |
|---|---|---|---|
| Core semantics | Executable Lean 4 definition of `core`, plus the interpreter | ≤ 30k-word prose spec (R09) | Differential testing against mithc. Lean meta-theory |
| x86 semantics table | XED-iclass-keyed bit-vector + FPA entries with an explicit FP-environment layer | 1.5–3k lines incl. generator (G02) | Silicon fuzzing on Zen 5 (SNaN/QNaN in each operand, ±0, subnormals, masks), with Bochs as a second oracle |
| mithcheck T0–T4 | Confinement pass, DAG matcher, certificate checkers, Comparator gate | ≤ ~6k lines Rust | Planted corpus, 100% core-mutant kill, second implementation (§5.6) |
| Space theorems | timing_only store core (O1–O5); exact-rewrite list soundness | Lean proofs / bounded model checks | Chaos suite. Grade recorded honestly |
| Gate | Promotion rule, α budget, authority checks, signing | ≤ ~3k lines | Attack suite (Hearth's golden-gate bypasses) |
| Measurement harness | Clock, async joins, poisoning, interleaved A/B, fingerprint, plausibility bounds | ≤ ~3k lines | Planted timing hacks (§8.2) |

The TCB size is a tracked metric with a hard cap. Growing it needs an ADR. Every guarantee is stated *relative to a
declared trust base*, and the trust base's own entries live in the ledger with their grades. Examples: "semantics
entry VPMAXSD: validated on 9950X, 10^9 vectors"; "Lean kernel v4.x: assumed + multi-kernel replay". A claim that is
`proof` relative to a `validated` semantics table says exactly that; `mithc ledger why --trust-base` prints it.

### 5.2 Checker tiers

- **T0, confinement.** A linear pass over the `tir` of policy and evolve code. All stores must target the policy's
  state block or the stack. No instruction may come from outside the space's allowlist (RDTSC/RDTSCP, RDPMC, CPUID,
  LDMXCSR/FLDCW, syscalls and indirect calls are all banned). Loops must be fuel-instrumented. Payloads may be read
  only through opaque handles. This makes the front end's effect checker advisory rather than trusted.
- **T1, IEEE-exact DAG matching.** The checker lifts object code to `tir` through the semantics table. It then checks
  that every FP operation corresponds one-to-one to a meaning operation, with the same operands in the same order, up
  to an audited list of exact rewrites:
  - add/mul commutation, which is exact under output NaN canonicalisation;
  - sign-bit negation;
  - lane moves, shuffles, blends and broadcasts;
  - loads and stores;
  - int→float conversion with a T2 range side condition;
  - power-of-two scaling with range conditions.

  It emits a witness (lane map, register-to-value map) that makes re-checking linear. Reassociation is never on the
  list.
- **T2, integer and bit-vector obligations.** Ranges, saturation freedom (for example the Q4 `maddubs` bound 3,810 and
  the Q8 sign-trick bound 32,512, R07), alignment and bounds. These are discharged by cvc5 or `bv_decide` with
  certificates (Alethe/CPC/LRAT) re-checked by a small checker. **"Unknown" or a timeout counts as rejection** (R07).
- **T3, tolerance.** FPTaylor/Satire-style bound certificates are re-evaluated with interval arithmetic, plus runtime
  margin checks at top-k and argmax. Opt-in, and labelled lossy by construction.
- **T4, deep proofs.** Lean terms accepted through a Comparator-style gate: a trusted statement hash, an axiom
  whitelist, a sandbox and multi-kernel replay, because the Lean kernel had a soundness bug in July 2026 (R07). T4 is
  used for space theorems, rewrite-list soundness and the occasional inductive kernel proof. It is never the agent's
  everyday path: for agents, SMT-backed auto-active contracts are the default (vericoding: Dafny 82% / Verus 44% /
  Lean 27%, R03).
- **S, statistical.** Anytime-valid e-values for performance and quality claims, spending from a project α budget
  (RV S1 Tier 2). Never used for correctness.

### 5.3 Certified spaces

For each space, two properties are kept distinct:

- **Soundness** (trusted): any candidate the space's check accepts preserves outputs.
- **Completeness-for-members** (untrusted, tested): every legitimate member passes the check, so agents do not see
  spurious rejections.

"Prove the space" means the per-candidate check is cheap and mechanical, and nobody writes a proof per candidate.

| Space | What may change | One-time certificate | Per-candidate check (automatic) | Remaining evidence to promote |
|---|---|---|---|---|
| `timing_only` policy | Eviction, prefetch, I/O order, mirror choice, pinning, thread-mapping heuristics | Store-core theorem: ∀ hint streams h, completion orders σ: out ∈ {out(fallback, σ₀), Err} (O1 hint validation, O2 slab race freedom, O3 arrival-order confluence, O4 lossless tiers by content hash, O5 liveness) (RV D2-A) | T0 confinement (ms) | Performance (S). Liveness timing contracts are monitored |
| `schedule` for a meaning | Tiling, fusion, lane mapping with fixed lane count, disjoint parallel split, placement, prefetch distance, unrolling | Schedule primitives preserve the op-DAG (Lean, against `core`). This gives *completeness* only | T1 on the emitted binary (seconds). This gives *soundness* | Performance |
| `rewrite(licence)` | E-graph rewrites, e.g. `int.ring` with overflow-free ranges | Each rule proved against the semantics; the FP list contains exact rules only | T2 side conditions | Performance |
| `relayout` | Repacking or interleaving weights into kernel-native layouts with identical values | Layout algebra: derived pack/unpack are inverses | Round-trip check per instance (T2 or exhaustive per block) | Performance; the converter emits the new layout |
| `refines(spec)` (free body) | Anything | None | Full T1/T2 certificate or T4. **Tests never suffice** | Performance |
| `real(bound)` | Reassociation, FMA, approximate transcendentals | Soundness of the bound calculus | T3 certificate plus margin checks | Performance + opt-in |
| `approx(profile)` | Lower-bit cold experts, dynamic k, deterministic degradation | None | Quality certificate (S, held-out corpus) | Human opt-in. Never the default |

Spaces are deliberately **incomplete**: Rice's theorem guarantees that some true improvements fall outside every
certified space. They go to `refines` with a per-candidate certificate, or they are not promotable. Incompleteness is
accepted; unsoundness is not.

### 5.4 The evidence ledger

A ledger entry contains:

- `key = H(code closure, spec hash, toolchain hash, target, hardware fingerprint)`;
- the claim kind and property;
- the evidence blob hash and grade;
- the trust-base hashes;
- the producing principal: role, model family and version, prompt hash;
- cost;
- status: live, stale, tombstone or quarantined;
- scope;
- resurrection triggers.

The ledger is append-only, Merkle-rooted and signed by the gate. Different claim kinds admit different evidence:

| Claim kind | Admissible evidence |
|---|---|
| `refines` / `bit_eq` | proof (T1/T2/T4) · validated (exhaustive, bounded) · tested (differential + mutation score) · assumed |
| `confined(space)` | proof (T0 + space theorem) only |
| `safe` (no OOB, no UB, no panic where `Fail` is absent) | proof (types + T2) · tested (ASan, fuzzing) |
| `deterministic(scope)` | proof · validated · tested (named golden) |
| `perf` | measured(hw, e-value, named baseline) · bound(phys) one-sided · assumed |
| `quality(profile)` | measured(corpus hash, CI) |

**Effective grade = meet(evidence grade, spec-strength grade, grades of `deterministic` boundaries crossed).**

**Tombstones** record negative results. Each carries a scope (hardware, model, shape), a failure class (H, T, S, E, V,
C, X, F from R02), the search budget spent compared with the incumbent's, and machine-checkable resurrection triggers.
Hearth's lookahead rejection, for example, gets `hw.nvme_links >= 2 || tier(vram).present ||
policy.evict.class == predictive`. `mithc revisit` scans triggers whenever hardware, toolchain, primitives or evaluator
change.

Manifest policies state per-slot requirements. For example, Hearth's exact kernels require `refines: proof |
validated`, and every perf claim requires `measured(hw)` against a named same-machine baseline. That is INV-HONEST as
a link rule.

### 5.5 Spec escrow and separation of powers

| Role | May write | May never write |
|---|---|---|
| Author | Meanings, specs, fault models, invariant drafts | Implementations, schedules, gate policy |
| Builder | Implementations, schedules, policies, layouts | Specs, meanings, goldens, mutant pools, the harness |
| Prover | Proofs and certificates for named obligations | Specs, implementations |
| Adversary | Sealed mutant pools (commit-reveal), chaos policies, planted kernels, trace adversaries | Specs, implementations, the gate |
| Gatekeeper | Runs the gate and assembles promotion dossiers | The gate's code, thresholds or α budget |
| Owner (human key) | Admitting specs, ratifying defaults, amending the TCB, editions | — |

The store judges change sets as content-addressed objects, never as paths. That defeats the symlink, case-twin, 8.3
name and stale-merge-ref bypasses found against Hearth's golden gate (RV D2-E).

**[DEVIATION] The Gatekeeper is not an LLM judge.** The gate is deterministic code in the trusted core. An LLM holding
the Gatekeeper role can run it and prepare dossiers, but it cannot change its policies. Promotions that need authority
need the Owner's signature. The task framing lists "gatekeeper agents"; the tie-breaker (evaluator integrity) argues
against a model-judged gate, given measured judge self-preference (Goel et al., RV D2-E).

**Spec lifecycle:** draft → hardening → admitted (hash-locked) → amended (new hash, hardened again). Old evidence keeps
pointing at old hashes. The strength record is two-sided (RV D2-E):

- **soundness:** the reference and every legal variant pass;
- **kill interval:** [K_lo, K_hi], with the unknown fraction reported;
- **vacuity:** rejected witnesses must fail; `assume`, `sorry` and `assume(false)` are banned in admitted code;
- **latitude:** the number of distinct admitted variants, which penalises specs that merely restate an implementation;
- **independence:** distinct model families, or measured low agreement. If both roles come from the same family, the
  record says `independence: same_family` and the grade drops.

Two kinds of spec carry different risks:

- **Executable meanings** (kernels). For exact refinement they are complete by construction. Their risk is the
  *intent gap*: the meaning itself may be wrong. Mithril attacks this with independent oracles (the numpy reference,
  transformers) and by running the numerics fault model *against the meaning*: does the differential suite catch a
  mutated meaning?
- **Contracts** (parser, store, router). These are partial, so their strength must be measured.

The honest claim is always "strong against fault model F, as judged by principals P", never "correct".

### 5.6 Attacking the trusted core

- **Planted corpus.** At least 200 wrong kernels per release: FMA contraction, wrong lane count or tree, the NaN
  operand order of MAXPS, a 127→128 clamp, a dropped scale, round-half-even → truncate, tie flips. The requirement is
  zero acceptances.
- **Core mutants.** Mutations of mithcheck, the gate and the harness must be killed 100% of the time by the core's
  own test suite.
- **Two checkers [EXTENSION].** A second T1/T2 implementation (Lean-extracted or independently written) runs in
  differential mode for promotion-grade claims. Any disagreement quarantines the claim. Independence between the two
  is itself measured, per the N-version lesson.
- **Standing Adversary bounties.** Ledger credit for accepted exploits. Every exploit becomes a regression test, plus
  a tombstone on the bypassed rule.
- **Semantics fuzzing** on silicon whenever the microcode, CPU or table changes. The emitter may use only opcodes
  whose table entries are covered (G02).

---

## 6. Runtime and targets

- **CPU tiers as data.** x86-64 scalar baseline; v3 (AVX2, optionally AVX-VNNI: Intel client through Panther Lake);
  v4 (AVX-512 F/BW/VL/VNNI/BF16/VBMI on Zen 4 and Zen 5; no AMX, no FP16); AVX10.2 pending; arm64 NEON, with SME
  later. Dispatch happens per ISA at load time (cpuid plus XCR0) through an atomic-cached table. There are no P/E-core
  paths (R08). Lane counts in an exact reduction are part of the meaning, so vector width is a schedule choice only
  where lanes are fixed (G03: 16 lanes map to one zmm, two ymm or a half-warp).
- **Memory and storage tiers.** VRAM, DRAM, NVMe and HDD appear in the placement model from v1, each with capacity,
  bandwidth and transfer cost (G03).
  - Tensors are `resident<T>` or `streamed<T>`.
  - Placement is an explicit, checkable schedule decision.
  - Tiers are lossless by content hash (O4). This closes Hearth's first-page-only mirror check.
  - Demand and prefetch requests have separate priorities, with reserved demand readers, chunked cancellable reads,
    and completion-order compute followed by a canonical-order combine (R06, RV D2-B).
- **Threads.** A persistent spin-then-sleep pool (no OpenMP). `par for` with compile-time-disjoint writes. Dynamic
  chunk claiming. Heterogeneity-tolerant stealing. Topology in the cost model, since each CCD's link caps reads at
  64 GB/s (R08).
- **Determinism scopes.**
  - `cross_device` is the canonical core `canon.v1`: one hash covers scalar, AVX2, AVX-512 and (later) PTX.
  - `device(t)` holds vendor-ordered paths (tensor-core float MMA, cuBLAS) that have their own goldens.
  - `schedule_dependent` is reserved for explicitly nondeterministic diagnostics.

  The runtime rejects any plan in which a `device(t)` value feeds a dynamically placed operation (C2). Determinism is
  defined as logits = f(binary, ISA set, version root, inputs, KV policy), and the version root is logged per token
  (R12).
- **Hot swap.** Versioned dispatch tables. Epoch commit at token boundaries (Hearth's `hx_store_tick`). A release-store
  of an aligned pointer, then quiescence-based reclamation through `Frozen` refcounts. JIT pages are W^X. There is no
  self-modifying code, no INVD and no CMPXCHG16B trickery (R08, R10).
- **Weights.** Immutable and content-addressed. Typed overlays (SlabReplace, LowRank, AddExpert, …) carry signed
  provenance and statistical gates. Sequences are pinned to a version, and migrating one requires a declared KV policy
  (R12).
- **Measurement mode.** This is the harness from the trusted core, linked into the runtime (§8.2).

---

## 7. Agent protocol and toolchain

**The loop.** One session holds one role token.

```
mithc guide --tier 0                          # <= 8 KB card, always in context
mithc view store::evict --slice --json        # canonical text + def hashes + signature summaries
mithc hole store::evict::victim               # expected type, bindings, effect budget, space rules
mithc edit --anchor h:7c2e… --text <file>     # hash-anchored; StaleAnchor on drift; atomic parse+typecheck gate
mithc check --json                            # grouped root-cause diagnostics + open obligations
mithc prove --json                            # discharges T1/T2 mechanically; lists residue for the Prover role
mithc bench request store::evict --niche cache=2GiB   # the gate measures; you never hold the clock
mithc ledger why store::evict@h:… [--trust-base]      # derivation of every grade
mithc abandon --reason spec_conflict          # first-class "cannot satisfy" outcome
mithc handover                                # emits the session manifest
```

- **Reading.** The unit of reading is a definition with its signature summary (types, `uses`, grade, contract,
  evidence status). Slices are about 100 lines. The Fact Plane answers API questions ("what has type `T -> U` with
  `uses [Io]`?") and returns only existing hashes, which prevents hallucinated APIs.
- **Editing.** Text stays the interface (aider's measured JSON penalty, RV S3). Edits are anchored by hash and never
  applied fuzzily. `propagate` turns dependents that stop typechecking into typed holes. Typed-hole context is the
  best-measured lever in the literature (Hazel/ChatLSP, R03).
- **Checking.** Incremental, with millisecond responses on unchanged closures. Each root cause gets one primary
  diagnostic with a stable code and a fix-it that has an applicability level and attached obligations. False-friend
  diagnostics name the rule that was violated (G01).
- **Proving.** Obligations are listed in JSON and discharged mechanically wherever a space or T1/T2 applies. The
  residue goes to the Prover role as Dafny-style auto-active goals.
- **Benchmarking.** Agents *request* measurements. The gate returns `Quantity<_, Measured>`, an e-value, the
  fingerprint and the plausibility verdict, or "insufficient evidence, budget α_i would be exceeded". The raw clock
  and the reference outputs are never exposed.
- **Abandoning.** `abandon` is first-class. ImpossibleBench found that an abort option cut GPT-5's cheating on
  conflicting tasks from 54% to 9% (RV D2-E).
- **Handover.** The session manifest is generated automatically: role, commands actually run, ledger deltas, open
  obligations, stale claims, new tombstones, α and compute spent, and the hash of the invariant lane. Handover
  `kind: measured | simulated` is mandatory; in Hearth's schema it is currently optional (R11). A friction rule blocks
  a fourth identical failing retry until a root-cause note exists.
- **Surfaces.** CLI with `--json`; an LSP whose hover shows grade and evidence and whose code actions are the fix-its;
  an MCP server exposing the same verbs; SARIF output; an AGENTS.md snippet; `mithc guide`. Constrained decoding with
  grammar plus type masks is available only where Mithril owns the logits (Hearth-hosted local models), and is off by
  default.

**Tier-0 reference card (draft skeleton, about 2k tokens when complete).**

```
MITHRIL T0 (edition 2027.0)   Rust syntax = Rust meaning, except the rows marked "!".
ITEMS   fn struct enum trait impl mod use | meaning fn | schedule X for f on target {...}
        policy P: timing_only {...} | spec S {...} | claim c refines S require ... | layout L = block_scaled{...}
        evolve slot s: Trait in space <timing_only|schedule|refines(S)|...> {...}
REFS !  &T / &mut T are params/locals only: no fields, no returns (E-REF-2ND). Moves as in Rust.
INTS !  overflow traps unless proven or wrapping_*; refinements: i32 in a..=b, [T; N] where N % 64 == 0
FLOAT   + * no contraction; mul_add = fma; sum() sequential; ! canonical: sum16(), reduce::<Tree16>()
      ! f32::max = Rust rule; MAXPS rule = max_x86(); NaN stored canonical via canon_nan()
      ! exp/sin/cos are cr (correctly rounded) unless canon::v1::exp; libm only via Foreign + nondet
EFFECTS fn f(..) -> T uses [Io, Spawn, Alloc<A>, Nondet, Time, Fail, FpEnv, Unsafe, Foreign, Device<D>]
GRADES  #[grade(exact|real(b)|approx(p), det = cross_device|device(t)|schedule_dependent)]
QUANT   Quantity<GB_per_s, Measured> ; untyped perf numbers do not print
NEVER   assume/sorry; Time or FpEnv in policies; rdtsc in evolve code; tests as proof for exact slots
LOOP    guide -> view -> hole -> edit(anchor) -> check -> prove -> bench request -> handover | abandon
```

---

## 8. The Forge and its trust model

### 8.1 How Gödel-machine proof and DGM empiricism combine

Let `slot` be an evolvable site (§8.3), `S` its declared space, `c` a candidate, `inc` the incumbent and `H` a
hardware fingerprint. The gate promotes `c` iff all of the following hold:

```
promote(c, slot, H) <=>
     check_S(c)                                        -- T0 or T1/T2: decidable, cached, no agent-written proof
  && grade(correctness(c)) >= slot.required_grade      -- meet of evidence, spec strength, boundaries
  && strength(slot.spec) >= slot.required_strength     -- escrowed, two-sided
  && E_t(perf(c) vs perf(inc) on H) >= 1 / alpha_i     -- anytime-valid e-process; sum of alpha_i <= alpha_budget
  && plausible(c, H)                                   -- no measured time beats LB_phys / replayed MIN floor
  && authority(slot)                                   -- Owner key for defaults, TCB changes, editions
```

**What the Gödel machine contributes.** First, the rule that nothing changes semantics without a machine-checked
certificate. Second, the stratification that answers the Löbian obstacle: proposers, tactics and heuristics may
evolve, but the checker and gate are frozen. Proof tactics may evolve freely, because the frozen checker re-checks
everything they produce. Gate thresholds and α budgets may only tighten without Owner authority. A new trusted core
v(n+1) is admitted by humans, with its rule-soundness proofs checked by v(n)'s Lean gate and differential runs on the
planted corpus. It is never produced by the Forge (RV S1 child 4).

**What the DGM contributes.** An open-ended archive, which is the ledger. Its ablation is the reason to keep it:
SWE-bench went 20.0% → 50.0% with the archive and only to 23.0% without (R01). It also contributes stepping stones,
clade selection (HGM), and the empirical treatment of performance, which cannot be proved on out-of-order hardware.

**The resulting guarantee.** Under trust base A (sound mithcheck, a semantics table that matches silicon on its
validated domain, a sound space theorem, correct hardware and OS, isolation that holds):

- every promoted `c` in an `exact` slot produces outputs bit-identical to its meaning or fallback, and
- the probability that *any* promotion in a budget period is not a real improvement of at least the minimum
  detectable effect on H is at most `alpha_budget`.

Both statements can be checked. **The tractability is in the decomposition:** a proof per space instead of a proof
per candidate, and statistics for the part that has no proofs.

### 8.2 Evaluator integrity: every documented hack has a named counter

| Documented exploit | Mithril counter |
|---|---|
| Faked test logs (DGM) | The harness owns the oracle. Results reach the ledger only signed by the gate process. Candidates have no ledger write capability |
| Removed hallucination markers / weakened checker (DGM node 114) | Checkers, specs and goldens are sealed and role-owned. Builders cannot write them. Hacking was more frequent with visible checkers, so scoring rules stay hidden |
| Timing on unwatched async streams, 32.8% of 250 kernels (CUDA-L1) | The runtime joins all threads, streams and I/O before stopping the clock. `Spawn` and `Device` are absent from evolve rows unless declared |
| Timer overwrite and evaluator monkey-patching, 30.4% of RE-Bench runs (o3) | No `Time` capability. T0 bans RDTSC/RDPMC in candidate binaries. The evaluator is a separate process built by the frozen toolchain |
| Reading the reference via memory reuse (METR, `torch.empty`) | Poisoned fresh allocations, guard pages, a materialisation check on outputs, no address observation |
| Copying the reference (Kevin-32B) | Reference outputs are never exposed. Exact slots need a certificate covering all inputs, not test passes |
| Hard-coded outputs, shrunken task, changed hyperparameters | Shapes are fixed by evaluator types. Hidden held-out shapes and seeds. `refines` certificates quantify over all inputs |
| Lazy evaluation; address-keyed caching across calls | Outputs must be materialised. No cross-call state outside the declared `state` block, which is reset between measured calls |
| Sandbox escape; agents editing their own limits (STOP, AI Scientist) | Supervisor-held limits: Windows Job Objects or a WSL2 container, no network, read-only mounts. An mprotect sandbox alone is not enough (R01) |
| Leaky verifier (AlphaEvolve, Tao et al.) | Small, adversarially tested TCB. Two checkers. Unknown counts as reject |
| Vacuous or weak specs: `assume(false)` spread (AlphaVerus); about 9% of successes too weak (vericoding) | Spec escrow, vacuity witnesses, strength thresholds, ban on `assume`/`sorry` |
| Special-casing under conflict, 54% (ImpossibleBench) | `abandon` outcome. Hidden holdouts. Adversary-generated conflict probes |
| Lucky-run selection under noise | Anytime-valid e-values. Interleaved A/B. Noise floor. Fingerprint mismatch voids the evidence |
| Physics-violating "wins" | Plausibility gate: beating a phys-tier bound or a replayed MIN floor means quarantine plus an audit of the evaluator |
| Golden-gate bypass via symlinks, case twins, 8.3 names (Hearth) | Content-addressed change sets. Paths never enter trust decisions |
| Poisoned benchmarks persisting after re-evolution (Roesner & Kohno) | An evaluator change invalidates scores; archive provenance allows bulk re-scoring |
| Sabotage attempts, 12% (Anthropic, RV D2-E) | Separation of powers. Adversary role. Owner key for anything that changes defaults |

On Windows, a cold-cache run needs CLFLUSHOPT sweeps or eviction buffers, because there is no user-mode WBINVD and no
`perf_event_open` (R08). Each measured candidate also serves as a free soundness test of the lower-bound model: every
measurement must satisfy LB ≤ T (RV D3-ii).

### 8.3 Search

```mith
evolve slot store.evict: EvictPolicy in space timing_only {
    objective minimize (stall_ms_per_token, nvme_bytes_per_token)          // never hit rate
    niches    cache in [1, 2, 4, 8].GiB, model in [qwen3_30b_a3b, k2_shaped], storage in [990pro_x1]
    bound     oracle::min_bytes_floor(trace), oracle::agl_stall_lp(trace)  // gap attribution + stopping rule
    holdout   traces sealed h:51ab…;  promote machine_profile;  default requires owner
}
```

The **cascade** runs cheapest first:

1. type and space check;
2. e-graph and hash deduplication (free rejection of semantic duplicates);
3. replay-conditioned sound pruning with a `PruneCert`. In the simulated pilot this pruned 16–41% of candidates per
   cache size and 66% jointly; physics-only rooflines pruned 0 of 144 (RV D3-ii);
4. simulator ranking (`est` tier, which may rank but never prune);
5. engine measurement on the quiet machine;
6. e-gate;
7. plausibility check;
8. promotion.

**Archive structure.**

- **Niches** are hardware × shape × model × storage profile (MAP-Elites style). A PATA-EC-style rank-order test
  decides when a new CPU or shape needs its own niche (R02).
- **Selection** is HGM-style Thompson sampling over clades, with a DGM-style non-zero floor for dormant lineages.
- **Revisit priority** is [P_win · V + β · novelty] / cost, sampled rather than argmaxed.
- **New meta-level selection policies** are tested by counterfactual replay on archived trajectories before they steer
  live runs (R01).

**Objectives.** Bytes per token and stall time, for a measured reason: depth-4 lookahead raised hits from 73% to 86%
but cut decode from 13.0 to 10.0 tok/s (measured, R02/RV D2-B). The oracle library gives every search a correct
fitness function and a stopping rule.

**Promotion levels [DEVIATION, a refinement of "human promotion for defaults"].**

- A winner in an output-preserving space is applied automatically as a **per-machine profile** pinned in
  `mith.lock`, keyed by fingerprint. It cannot change outputs, and its performance claim carries an e-value.
- Changing a **shipped default** still needs the Owner's key, with the dossier attached.
- `approx` changes are never defaults.

### 8.4 Levels of self-improvement

1. **Program level.** Policies, schedules, layouts and `refines` bodies, as above. Initial targets in order: store
   policies (cheapest evaluator: hearth.sim replays 960k requests through five policies in about 2.6 s, R01), then
   kernel schedules, then layouts.
2. **Compiler level.**
   - Heuristics (inlining, tiling choice, schedule search strategy, cost models) choose only among certified rewrites,
     so they evolve freely.
   - A new rewrite rule must be proved against the semantics: VeriISLE-style SMT, or Lean for FP-exact rules. It
     enters the audited list only through the Author→Adversary→Owner path.
   - Cost models rank; they never decide correctness.
   - Lifted wins are generalised into license-parametric rules (RV S2).
3. **Language level.** Editions, stdlib and the card. Fitness is held-out VP@1 and the checker-accepted-but-wrong
   rate on refreshed sealed suites, against C and Rust arms. Every edition migrates the corpus bit-exactly. Promotion
   needs an Owner ADR, because language fitness Goodharts toward easier benchmarks (R01, RV D2-D).
4. **Meta level.** Selection policies and budget splits, changed only through counterfactual replay plus Owner
   sign-off.

**Beyond DGM and AlphaEvolve:**

- Correctness is free per candidate for the largest optimisation classes.
- Hack classes are type errors rather than sandbox events.
- Negative results are durable, scoped and automatically resurrected.
- Sound pruning saves quiet-machine time.
- The statistical error is a budgeted resource.
- Spec strength is itself evidence.
- Determinism doubles as a search accelerator: replay gives cheap OPT labels and exact bytes (RV §6.8).

---

## 9. The Hearth port

The port is a strangler fig behind Hearth's internal `hx_*.h` seams. Mithril emits C11 objects that replace C objects
one at a time, with the stages ordered as in `design-inputs.md`. `hearth-c-ref` stays frozen permanently as a
differential oracle (R11).

| Stage | Content | Acceptance gates (all must pass) |
|---|---|---|
| −1 Constitution and C fixes (maintainers) | ADR-0010 specified transcendentals; MXCSR assertion at worker start; full-content slab hashes for mirrors; `struct_size` in ABI structs; settle heat decay (0.9 in `hx_model.h` vs 0.995 in `hx_store.h` and ADR-0004) | ADRs merged; C tests updated with the measured output-change rate (INV-LOSSLESS-DEFAULT) |
| 0 Freeze and instrument | Tag the base; build `hearth-c-ref`; **cross-binary hash corpus** (SHA-256 of logits, routes and quantiser bytes for every `make_tiny` arch × {F32, Q4} × ISA, `big_q4`, 512 real Qwen3 decode steps); record CRT identity; **M0: T1 certifies the existing C kernels** | Corpus reproducible across 3 runs; T1 accepts the existing AVX2/AVX-512 Q4/Q8 kernels; zero planted acceptances |
| 1 Leaf numerics | Layouts, quantisers, scalar and canonical helpers; one meaning plus v3/v4 schedules replace `quant*.c` | `test_quant` (117,681 checks); golden ISA/batch identity; byte-identical hash corpus; quantiser byte diff against C (closes the oracle hole); single-thread AVX-512 Q4 ≥ 69.6 GB/s (measured, interleaved A/B) |
| 2 Container parser | `format` descriptions → generated parser and writer (EverParse3D-style); signature has no `Fail` | `test_modelfile` fuzz cases; golden malformed-file test; identical accept/reject decisions and parsed configs against C on a generated corpus |
| 3 Pool | Persistent pool, disjoint par-for | `test_pool`; dispatch latency within noise of C (about 0.75 µs at 16 threads, measured); WSL2 and crowded-pool scenarios |
| 4 Store logic + platform | `ExpertStore` core with hint ports; audited stdlib layer (platform is riskiest); **Forge pilot E0–E4** (RV D2-A) | `test_platform`, `test_store`; golden scheduling independence; ≥ 7 GB/s peak direct-I/O demand reads on the 990 PRO; chaos suite kills 100% of core mutants; ≥ 100 generated policies → bit-identical logits (one falsification run) |
| 5 Forward pass | `model.c` as meanings and schedules (GQA, MLA, routers, shared experts) | Full golden suite (`check_golden.py --run`); hash corpus; 512-step real-model decode hashes; load-gated tok/s parity at 2/4/8 GiB caches and 512/2048-token prefill |
| 6 API | `export abi` reproduces `hearth.h` (19 functions, 3 structs) | Python toolkit and ctypes mirror tests pass unchanged; C core retired; `hearth-c-ref` kept |

**Constitutional decisions Hearth's maintainers must make:**

1. **INV-DEP and ADR-0001.** May Mithril be the source of the core if what ships is C11 with no runtime? My
   recommendation: during Stages 1–5, check in the generated C11 with provenance headers and keep `mithc` a build-time
   tool only. The source-of-truth shift is a separate ADR, taken at Stage 6, and it trips the decision circuit
   breaker.
2. **ADR-0010, transcendentals:** `cr` versus `canon.v1` per function, adopted **before** the hash corpus exists. The
   golden tests are relational, so no re-lock is needed (G04). After that, add INV-DET-4 (cross-OS hash equality).
3. **Golden strength.** Make the cross-binary bit-exact corpus a maintainer-owned golden. Hypothesis to test first:
   the current tolerance-based golden layer is *weaker* than the bit-exact contributor tests for numerics (RV D2-E).
4. **INV-DET-1 scope:** extend it to "fixed binary, ISA set, device plan and version root" once a GPU tier or overlays
   exist.
5. **GPU:** is the RTX 5070 in scope for compute? Does `nvcuda.dll` count as an OS API, or must the GPU path use
   Vulkan? Should the display move to the iGPU, freeing about 1.5 GB (G03)?
6. **Forge authority:** may per-machine profiles in output-preserving spaces auto-apply? Which roles do maintainers
   hold, given that Author and Owner for meanings must be humans or maintainer-designated agents?
7. **Defects to report, not fix, through maintainers:**
   - `check_mirror` samples only the first page;
   - `hx_store_heat` returns an unguarded pointer (a C11 data race);
   - the `read_errors` ABI break wrote past the ctypes buffer;
   - MXCSR is never asserted;
   - the heat-decay mismatch above;
   - storage channels in the server (`cached_tokens`, `/stats`, unauthenticated `/health`);
   - `n_io=1` leaves no reserved demand reader.

---

## 10. Roadmap

Durations are [inference]. Thresholds are pre-registered *gates*, not results.

| # | Milestone | Deliverable | Measurable gate | Pre-registered kill criterion |
|---|---|---|---|---|
| M0 | Trusted-core seed on C Hearth | Semantics table for Hearth's ~105 instruction forms, fuzzed on the 9950X; T1/T2 over MSVC and clang object code against NUMERICS meanings; hash corpus; numerics fault model N1 and spec-escrow pilot; cold-agent harness skeleton | T1 certifies Hearth's existing Q4/Q8 AVX2 and AVX-512 kernels; 0 acceptances in a planted corpus of ≥ 200; ≤ 40 audited exact rules | If T1 cannot accept the existing AVX-512 Q4 kernel within 10 weeks without exceeding 40 rules or tolerating any false accept: drop object-code validation and restrict T1 to Mithril's own emitter (the [DEVIATION] in §4 is withdrawn) |
| M1 | Surface and cold start | Lark grammar; Tier-0/1 card; `mithc check` for core plus meanings and schedules; Mithril MultiPL-E; sealed Hearth-shaped tasks; C and Rust arms | VP@1 within 10 points of the Rust arm, with a checker-accepted-but-wrong rate no higher than Rust's, on frontier models from two families | If VP@1 trails Rust by > 15 points after two card iterations and the gap is not shrinking: Mithril becomes a spec/evidence/checker layer over C and Rust, and the standalone surface is dropped |
| M2 | Kernels (Stage 1) | Layouts plus matvec meanings; v3/v4 schedules; C11 backend; per-build T1 certificates | Stage 1 gates (§9) | If generated kernels stay > 5% slower than the hand C (e-value-confirmed) after schedule search, or bit-identity cannot be certified: halt the port at Stage 1 and keep only the M0 certification |
| M3 | Forge pilot on timing_only | Hint ports (C vtable first, then Mithril); O1–O5 evidence; MIN/AGL oracles; replay pruning; e-gate; archive | Every type-checked policy bit-identical (≥ 100 policies); 100% core-mutant kill; 0 planted hacks accepted; either a measured improvement in bytes/token or tok/s at e ≥ 20, or scoped tombstones | **Soundness kill:** any type-checked policy that changes logits halts all Forge promotion until the core theorem is repaired. Any false prune in ≥ 60 real-engine audits demotes replay bounds to the `est` tier |
| M4 | Parser, pool, store (Stages 2–4) | `format` parser; pool; store over the audited layer; loom-style tests | Stage 2–4 gates | User-level Unsafe in store logic > 0 lines, or the audited layer > 1,500 lines per OS: reopen the memory model (regions/capsules) before Stage 5 |
| M5 | Forward and API (Stages 5–6) | Full engine as Mithril-emitted C11; `hearth.h` exported | Stage 5–6 gates | tok/s parity missed by > 5% at any gated configuration for 6 weeks: ship the hybrid (Mithril kernels and parser, C forward pass) and stop |
| M6 | Direct emitter, superopt ledger, compiler-level Forge | x86 emitter for staged kernels; AVX-512 attention value pass (prototype 18 → 94 GMAC/s, measured, R11) admitted via the ledger; proved rewrite rules | Prefill or long-context gains at e ≥ 20 on a named baseline; zero test-only acceptances | No measured gain over the C11 backend on any niche after two search rounds: freeze the emitter; C11 and LLVM remain |
| M7 | GPU expert tier (owner-gated) | PTX Q4/Q8 expert GEMV with exact int32 blocks and an `add.rn` epilogue; VRAM tier in the store | Cross-device hash equality (CPU = sm_120) on the corpus; GEMV throughput measured against llama.cpp MMVQ on the same card | Canonical GEMV < 50% of MMVQ throughput [inference threshold]: the GPU stays `device(t)` opt-in with its own goldens, and the canonical core stays CPU-only |

---

## 11. Non-goals and top risks

**Non-goals.**

- A verified compiler: translation validation instead.
- Formal proofs of speed.
- Runtime self-modifying code, INVD or CMPXCHG16B hot patches.
- SMT "bounded loss divergence" or "forgetting-free" types.
- Per-token persistent learning.
- A Python-embedded primary surface, projectional editors, or JSON-wrapped code as agent I/O.
- Lean tactics as the authoring layer.
- Visual-generation primitives.
- A full GPU backend in v1.
- P/E-core paths; SPDK as default.
- µop superoptimisation as the main path; bypassing LLVM as a goal.
- Implicit spec→code regeneration.
- Multi-shot continuations, GC, exceptions-as-unwinding, macros, inheritance or general dependent types in v1.
- Hard file locks for swarms.
- Replacing Hearth's C core before maintainers decide.

**Top risks.**

| Risk | Mitigation |
|---|---|
| A trusted-core soundness bug certifies wrong code | TCB cap; two checkers; planted corpus; core mutants; bounties; Lean proofs of rule soundness; ledger quarantine and revocation of every dependent claim |
| Semantics table diverges from Zen 5 silicon (NaN selection, ±0 max, conversions) | Fuzz campaign plus Bochs; emit only covered opcodes; MXCSR effect; re-fuzz on microcode change |
| Specs are weak, or Author and Adversary fail in correlated ways | Escrow; two-sided strength; independent oracles; measured independence; honest "against F, by P" claims |
| Cold start: agents write Mithril badly | M1 kill criterion; fallback to the verification-layer product |
| The C11 backend misses MSVC hand-intrinsic throughput | Schedule search; direct emitter; M0 certification keeps value even if the port stops |
| T1 is incomplete on compiler output | T2 or per-block exhaustive fallback; own emitter; M0 kill criterion |
| Measurement noise on a Windows desktop | Interleaved A/B; e-values that refuse to certify; quiet-machine protocol; fingerprint voiding |
| Scope versus a one-person-plus-agents team | Milestones with kill criteria; M0 and M3 deliver value to C Hearth on their own |
| Maintainers reject the constitutional change | No-runtime C11 output; Stage −1 improvements land in C regardless |
| Goodhart at the language level | Owner ADR; refreshed sealed suites; control arms |
| `deterministic { }` boundaries become an escape hatch | Authority-gated; evidence-cited; grade flows downstream |
| Liveness bugs in safe concurrent code | Loom-style permutation scheduler; timing contracts T1–T5 with a watchdog |

---

## 12. Novelty versus prior art

**What I claim is new.** These are combinations or mechanisms for which the dossiers found no prior instance;
coverage of 2025–2026 work is incomplete (RV provenance warning).

1. **Certified modification spaces as typed language items, used as the self-improvement contract.** This separates
   space soundness (trusted) from completeness-for-members (untrusted). The precedents are pieces: the Gödel machine,
   DGM/HGM (R01), sched_ext fallback and noninterference (RV D2-A), and Exo's checked schedules (R05). The node found
   no 2025–2026 paper on noninterference-typed resource policies (unverified, RV D2-A).
2. **IEEE-exact translation validation of untrusted compilers' SIMD object code,** by DAG matching against a
   canonical-order meaning, over an owned, silicon-fuzzed AVX-512 FP semantics table. KLEE-FP, Alive2, CryptOpt and
   VeriISLE are precedents (R07). No public AVX-512 FP semantics exist (G02).
3. **One evidence ledger:** grade lattice, spec-strength meet, boundary-grade propagation, tombstones with
   machine-checkable resurrection triggers, a statistical α budget as a project resource, and signed by the gate.
   About ten revisit nodes reinvented parts of it (RV §6.4). PCC (RV S6), Unison caching and the Statistical Gödel
   Machine (RV S1) are the precedents.
4. **Evaluator integrity by construction:** effect-typed evolve slots, a binary-level instruction allowlist,
   runtime-owned clocks and joins, and physics plausibility quarantine. robust-kbench, KernelBench-Verified and
   METR's protocols harden the harness; Mithril makes the hack classes unrepresentable (RV S5).
5. **Spec escrow enforced by store capabilities,** with two-sided strength and measured independence (RV D2-E). The
   precedents are Comparator, mutation testing and nl2postcond.
6. **Replay-conditioned sound pruning with audited PruneCerts,** enabled by determinism (RV D3-ii).
7. **Fidelity × determinism-scope types, including a cross-device canonical core and a placement checker** (G03, RV
   S7).

**What I took deliberately from prior art:**

- the Rust surface (G01);
- Hylo mutable value semantics, Swift `Mutex`, OxCaml-style capsules collapsed to a mutex (G05);
- Koka/Effekt effects and Austral capabilities (R09);
- Halide/Exo meaning/schedule split, with Exo's MIT code as a candidate base plus an IEEE-exact mode (R05);
- Terra/MetaOCaml staging and Zig comptime (R09);
- Unison content addressing, salsa queries and rustc/SARIF diagnostics (R03, R04, R09);
- Hazel typed holes (R03);
- Dafny-style auto-active contracts and the Lean Comparator gate (R03, R07);
- cvc5 proofs and `bv_decide` (R07);
- EverParse-style formats (RV S11);
- the OCP MX formats (R06);
- CORE-MATH / LLVM libc correct rounding (G04);
- DGM archives, HGM clades, MAP-Elites, the AlphaEvolve cascade and GEPA-style reflective mutation (R01, R02);
- loom; copy-and-patch; Erlang's two-version hot-swap rule; XED iclass keys (G02, R09).

Mithril's claim is not that these pieces are new. Its claim is that one trust model binds them: correctness is proved
per space, mechanically checked per candidate, and graded on a ledger, while speed is measured by a judge the
candidate cannot touch.
