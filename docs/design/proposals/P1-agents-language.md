# P1: Mithril as the agent's language

**Proposal id:** P1 · **Lens:** the agent's language (what measurably helps agents most) · **Date:** 2026-10-11
**Inputs:** `brief.md`, `design-inputs.md` (treated as binding unless marked **[DEVIATION]**), `draft-thesis.md`, `digest-raw.md`, dossiers R01-R13, G01-G05 and `revisited-ideas.md` (cited as R03, G01, D2-D, D3-i and so on). The Hearth source was read but not modified.
**Labels:** every number comes from a dossier with its measured or simulated label. My own estimates and targets are marked **[inference]** or **[target]**. A target is a gate value I am proposing, not a result.

---

## 0. Decisions in one page

1. **Surface.** A standalone `.mith` language that accepts a *subset of Rust's meaning*. Anything that parses like Rust means what Rust means. Mithril never reinterprets it: where Mithril differs, the familiar form is either rejected with a named `FalseFriend` diagnostic or replaced by a new keyword or type. Which of the two applies is decided per construct by measurement (D3-i, G01).
2. **The signature is the summary.** Public signatures carry types, effects, capabilities, contracts, fidelity grade and determinism scope. Context packs ship signatures, not bodies.
3. **Typed holes use Rust's own stub, `todo!("name")`.** A program with holes still type-checks and runs. `mithc hole` returns the expected type, the bindings in scope, the obligations and the candidate functions.
4. **The edit protocol is text plus hash anchors.** Edits address a definition path plus its content hash, never a line number. Stale anchors are refused, never applied fuzzily. Every edit set is parsed, formatted and type-checked atomically, and the edit response *is* the check result.
5. **Diagnostics are a typed API.** One root cause per group, cascades folded, at most one auto-applicable fix. Each fix is labelled with the evidence it invalidates.
6. **Reference card in tiers.** Tier 0 is at most 8,192 bytes, always in context, delivered through AGENTS.md rather than a skill. Tier 1 is 5-15k tokens in three modules. Tier 2 is retrieved. One normative Lark grammar. Byte and token budgets are CI-enforced.
7. **Nothing is decided without the harness.** No language or toolchain decision ships without the **comprehension harness**: sealed Hearth-shaped tasks, C11 and Rust control arms, verified pass@1, the checker-accepted-but-wrong rate, tokens and turns per verified pass, and pre-registered kill criteria.
8. **Hearth closes the loop.** Hearth hosts the local models, applies Mithril grammar and type masks to their logits as an opt-in sampler feature, and is itself ported to Mithril.
9. **Everything else** follows `design-inputs.md`: exact numerics by default, the evidence lattice and ledger, effects as capabilities, mutable value semantics, the Exo-style meaning/schedule split, the C11 backend first, the timing_only "prove the space" policy class, and the Forge with a hardened evaluator.

---

## 1. Thesis and design principles

**Thesis.** Mithril is a small, Rust-shaped systems language and toolchain whose primary users are AI agents. Its goal is that a cold agent (a frontier model through an API, or a small model hosted by Hearth) can write, change, verify, benchmark and hand over *correct* low-level code at the lowest cost in tokens, turns and dollars. Porting Hearth is the first proof. The surface is deliberately unoriginal, because the evidence says novel syntax is pure cost (G01, R03).

The value is in what surrounds the text:
- signatures that are sufficient summaries;
- a checker that is the only judge;
- one executable *meaning* per performance-critical function, with many *realisations* that are checked against it, so agents can search "how" freely while "what" stays fixed;
- a closed measurement loop that keeps every language feature only if fresh agents measurably do better with it.

If the loop says they do not, Mithril shrinks to an evidence and verification layer over a Rust subset. The design is built so that this outcome is cheap.

**Principles**

1. **Familiar where meaning matches; rejected or loud where it differs.** False friends are the worst case: a single in-prompt 1-based-index rule took GPT-4 from 82.5% to 40.5% on affected problems (G01). A construct is classified as *coincident* (C), *checker-visible divergent* (Dc) or *checker-invisible divergent* (D):
   - C keeps Rust syntax.
   - Dc keeps Rust syntax but gets a targeted rejection.
   - D gets a new keyword, a new type or a mandatory disambiguator, and the bare familiar form is trapped.

   The class is grade-indexed. In code that cannot affect outputs (timing_only), some D constructs become C (D3-i, child 1).
2. **The signature is the summary.** A caller never needs a callee's body. The compiler enforces this: public functions must declare their effects, and context packs omit bodies by default. Context rot is real: on NoLiMa, 11 of 13 models fell below half their baseline at 32k tokens (G01 F5.3).
3. **The checker judges; the agent proposes.** Agents overrate their own work; in the chess study, agents rated their own play 200-1,100 Elo too high (G01). The harness, not the agent, owns oracles, clocks and goldens. No claim is printed without a matching evidence entry.
4. **One meaning, many checked realisations. Prove the space, not the candidate.** Schedules, timing_only policies and exact rewrites are certified once as *classes that cannot change outputs*. Inside such a class, search needs only performance evidence (revisit synthesis, design-inputs).
5. **Exact by default.** Strict IEEE arithmetic and named reduction orders. Nondeterminism, platform behaviour and lossy approximation are explicit effects. INV-LOSSLESS-DEFAULT becomes a link error.
6. **One root cause, one fix, one turn.** Grouped, localised diagnostics took GPT-3.5 from 4.97% to 44.76% on RustAssistant's benchmark (R03 §7). After one failed edit, SWE-agent's chance of eventual success fell from 90.5% to 57.2% (R03 §9). Edit and check are therefore one atomic call.
7. **Text is the interface; hashes are the identity.** LLMs are text-native: wrapping code in JSON lowers quality (aider, S3). Identity, caching, evidence and anchoring all key on content hashes of definitions.
8. **Small enough to fit.** Every construct must be explainable in Tier 1 with one snippet and one false-friend line (G01). The normative core is at most about 30k words (R09). Budgets fail CI.
9. **No ambient authority.** Effects are capabilities rooted at `main`. Running agent-generated code is a bounded-risk action by construction.
10. **Measure before deciding; keep what failed.** Every language decision carries a pre-registered gate and kill criterion. Rejected variants become scoped tombstones with resurrection triggers (R02).

---

## 2. Layered architecture

```
 L0 AGENTS & HUMANS   frontier API agent | Hearth-hosted local model (owns logits) | maintainers
                      (roles: Author, Builder, Prover, Adversary, Gatekeeper)
        |  Tier 0 card (always) + project card + context packs + handover manifest
 =======v===================================================================================
 L1 AGENT INTERFACE   mithc CLI (--json) | LSP + hole/context extensions | MCP tools | SARIF
                      edit protocol (hash anchors) . hole query . type search . explain/guide
                      prove/evidence . bench (runtime-owned clock) . handover/resume . lift
 =======v===================================================================================
 L2 CODEBASE STORE    canonical .mith text on disk (truth) + mith.lock (name -> def hash)
                      content-addressed definitions . spec escrow & roles . Surface Map
                      evidence ledger (+ tombstones) . toolchain journal . Comprehension Ledger
 =======v===================================================================================
 L3 FRONT END         lossless Syntax (Lark-conformant) -> HIR (holes as nodes) ->
   (query database)   types . effects/caps . ownership . fidelity grade . det scope ->
                      Fact Plane (Datalog relations) -> grouped diagnostics + fixes
 =======v===================================================================================
 L4 MIDDLE            MCore  (small typed core calculus; normative; Lean reference semantics)
                      KIR    (kernel IR: index loops + layouts + explicit FP op-DAG + schedule)
 =======v===================================================================================
 L5 VERIFICATION      T0 types/effects/grades | contracts -> SMT (auto-active) | T1 FP-DAG
    & EVIDENCE        matcher | T2 bit-vector SMT | T3 tolerance certs (opt-in, lossy label)
                      property + mutation tests | golden + cross-binary hash corpus | bench
 =======v===================================================================================
 L6 BACKENDS          C11 strict (first) | x86-64 kernel emitter over owned semantics table
                      | copy-and-patch JIT (load-time residuals) | PTX expert tier (gated) | LLVM opt.
 =======v===================================================================================
 L7 RUNTIME           no hidden runtime: audited std layer (Mutex/Condvar, Arena->SlabBuf,
                      Frozen, File.read_at, scoped pool/services) . tiered residency .
                      determinism scopes . quiescent hot-swap . capabilities rooted at main
 =======v===================================================================================
 L8 TARGETS           x86-64 {scalar, AVX2(+VNNI), AVX-512(VNNI,BF16)} | arm64 NEON | sm_120
                      DRAM . NVMe . VRAM | machine profiles (fingerprinted)
 -------------------------------------------------------------------------------------------
 SIDE SYSTEMS  Forge (archive, QD search, hardened evaluator) . Comprehension harness
               (pack, sealed suites, Surface Lab) . Hearth (host of local agents + acid test)
```

| Layer | Responsibility | Agent-facing guarantee |
|---|---|---|
| L0 | Proposes changes, specs, schedules and policies; maintainers promote | Roles have disjoint write capabilities |
| L1 | One JSON contract over CLI, LSP and MCP; every response carries the next actions | No line numbers; budgeted responses; edit equals check |
| L2 | Text on disk; identity, caching and evidence by hash | Formatting changes alter no identity; stale anchors are refused |
| L3 | Incremental checking, holes, the fact queries agents ask | Millisecond feedback on single-definition edits [target] |
| L4 | Small normative core; kernel meaning with an explicit FP op-DAG | The meaning is the oracle for every realisation |
| L5 | Small trusted checkers; graded evidence | Evidence requirements are policy, not convention |
| L6 | Emits code without changing meaning | Each backend implements every op exactly or refuses |
| L7 | Determinism and safety without a garbage collector or hidden threads | Nondeterminism is visible in types |
| L8 | Hardware as data | Every performance number carries a hardware fingerprint |

---

## 3. Language core

### 3.1 Surface syntax policy

**The subset rule.** Mithril source either (a) parses as Rust and means what Rust means, (b) is a Rust form Mithril rejects with a specific diagnostic, or (c) uses a construct Rust does not have, introduced by a keyword Rust does not use. There is no fourth category. This is a stronger version of the settled "Rust-shaped, no false friends" constraint, and it is what makes the false-friend table finite and testable.

**Keywords versus attributes.** Constructs that change typing rules get keywords: `uses`, `seals`, `requires`, `ensures`, `invariant`, `decreases`, `spec`, `kernel`, `schedule`, `layout`, `policy`, `timing_only`, `linear`. Metadata that does not change typing goes in Rust-style attributes: `#[evidence(...)]`, `#[decision("ADR-0004")]`, `#[bind(load)]`, `#[implements(...)]`. This keeps the grammar small and puts new meaning in greppable, line-leading tokens (G01).

**Tie-breaks taken under my lens** (each to be confirmed by the Surface Lab, §7.11):
- Disambiguators are Rust enums (`Ties::LowerIndex`), not named arguments, so no new call syntax is needed.
- Typed holes reuse `todo!()`, not R03's suggested `?name`, because Rust's postfix `?` is the try operator. **[DEVIATION from an R03 recommendation; not from a settled constraint.]**
- v1 has no `async`, `macro_rules!` or `dyn`. These are Dc rejections with fixes, which saves card budget.
- Staging quotes (`Code<T>`) exist but live in Tier 2. Agents use schedules (§3.7).

**Initial false-friend table.** This seeds Tier 0. Rows marked D are Surface Lab pilots, D1-D5 in D3-i.

| ID | Construct | Prior meaning | Mithril rule | Class | Surface |
|---|---|---|---|---|---|
| FF-FMA | `a * b + c` (float) | Rust: two roundings. C: GCC contracts by default outside ISO mode | Two roundings, never fused. `a.mul_add(b, c)` (Rust meaning) is the only fused form | C vs Rust; D vs C priors | familiar; `mithc lift --from c` flags it |
| FF-SUM | float `Iterator::sum`, `fold` | Rust: sequential left fold | Rejected in exact-graded code. Fixes: `canon::sum16(xs)` or `canon::sum_seq(xs)` | D | trap plus mandatory choice |
| FF-ROUND | `x.round()` | Rust: ties away from zero. C `nearbyintf`: ties to even | Rust meaning. Hearth quantisers use `round_ties_even()` | C (Rust prior); D (C prior) | familiar; lifter maps |
| FF-TIES | `max_by`, `min_by`, top-k | Rust `max_by` returns the last maximum; numpy `argmax` the first; `torch.topk` is unstable | Rust meaning kept. Routing must call `sel.topk(k, Ties::LowerIndex, Nan::Last)` | D | mandatory enum arguments |
| FF-NAN | float ordering | `total_cmp` puts NaN above +inf | `topk` and `sort` on floats require a `Nan::` argument | D | mandatory enum argument |
| FF-CAST | `x as i32` from f32 | Rust: saturating, NaN to 0. C: undefined | Rust meaning. The x86 lowering adds saturation unless the range is proven | C | familiar |
| FF-OVF | integer `+` | Rust: panics in debug, wraps in release | Always checked (`Fail`) unless `wrapping_*`. Kernels must prove absence (T2) | Dc | familiar plus diagnostic |
| FF-REF | `&T` stored in a struct or returned | Rust: allowed with lifetimes | Rejected: references are second-class. Store an index or handle, or use `Frozen<T>` | Dc | diagnostic |
| FF-UNSAFE | `unsafe {}` | Rust: local opt-in | Needs a package grant in `mith.toml` | Dc | diagnostic |
| FF-ASYNC | `async`/`await` | Rust futures | Not in v1. Use scoped services and the pool | Dc | diagnostic |
| FF-Q4 | "Q4 block" | llama.cpp Q4_0: 32 elements, high nibble at j+16 | Hearth Q4: 64 elements, high nibble at j+32, reachable only through a `layout` type | D | new keyword |
| FF-HOLE | `todo!()` | Rust: panics when reached | Same runtime meaning, plus a typed hole the compiler reports | C | familiar |
| FF-CLOCK | `std::time::Instant::now()` | ambient clock | Needs `uses { Time }`. Forbidden in timing_only code and in Forge candidates | Dc | diagnostic |

### 3.2 Illustrative snippets

**(a) A quantisation layout type** (Hearth FORMAT.md §6, `hx_quant.h`):

```rust
layout Q4 = block_scaled {
    block: 64,
    code: i4 biased(8),                       // stored q + 8, q in [-8, 7]
    scale: f16 per block,
    order: nibble_pairs(lo: j, hi: j + 32),   // NOT llama.cpp Q4_0 (32-block, hi = j + 16)
    bytes_per_block: 34,                      // checked against the derived size
}
layout MXFP4 = block_scaled { block: 32, code: e2m1, scale: e8m0 per block, order: packed_lo_first }
```

From each layout the compiler derives:
- `pack`, `unpack` and `codes()`;
- an exhaustive round-trip test over all codes and the scale classes;
- the exact-integer dot lowerings that are legal for it (VNNI `vpdpbusd` for u8×i8 after the bias identity; MXFP4 doubled to int8; R06).

The comment on `order` is the false-friend row FF-Q4, printed by the formatter.

**(b) A Q4 matrix-vector meaning plus a schedule, under exact numerics** (NUMERICS.md §3, `quant.c` `mm_q4_scalar`):

```rust
kernel fn matvec_q4(w: &Rows<Q4>, x: &[ActQ8], y: &mut [f32])
    requires w.cols() == 64 * x.len() && y.len() == w.rows()
{
    for r in 0..w.rows() {
        let mut acc = 0.0f32;
        for g in 0..x.len() {
            let b = w.block(r, g);
            let isum: i32 = dot_exact(b.codes(), x[g].q);      // exact int; |isum| <= 65_024
            acc = acc + (isum as f32) * (b.scale.to_f32() * x[g].d);
        }
        y[r] = canon_nan(acc);                                 // 0x7fc00000 for any NaN
    }
}

schedule matvec_q4 for x86_64.avx512_vnni {
    tile r by 16;                        // 16 rows per zmm pass
    parallel r over pool(chunk = 64);    // disjoint writes to y[r]: provable
    lower dot_exact with vpdpbusd;       // licensed: sum(n*x) - 8*sum(x), |.| < 2^31
    prefetch w.block(r + 4, 0) to L2;    // timing-only: cannot change bits
}   // reordering acc over g is rejected: E-SCHED-FPDAG (the meaning fixes the op order)
```

The meaning is ordinary Rust-shaped code, and every float operation in it means what it means in Rust: no contraction, with parentheses deciding the order. The schedule can only tile, parallelise disjoint writes, lower exact-integer subterms and add timing hints. T1 then checks that the emitted float DAG matches the meaning (§5). One meaning plus three schedules (scalar, AVX2, AVX-512) replaces Hearth's three hand-kept files (R05, R09).

**(c) A cache policy under the timing_only class** (D2-A; `store.c` `cheaper`/`pick_victim`):

```rust
policy RouterAwareLru: timing_only {
    state { last_use: [u64; MAX_SLOTS] }            // fixed size: no heap, no clock, no FP env
    fn on_use(&mut self, s: SlotIx, t: Tick) { self.last_use[s.0] = t.0; }
    fn victim(&self, cands: &[Cand], pred: &RoutePred) -> Choice {
        // Rust min_by_key tie semantics are fine here: output bits cannot depend on them
        cands.min_by_key(|c| (pred.likely_next(c.key), self.last_use[c.slot.0]))
    }
    // fn f(&self, c: &Cand) -> u64 { c.bytes()[0] }  -> E-TIMING-OPAQUE: payload is opaque
    // fn g(&mut self) { std::time::Instant::now(); }  -> E-TIMING-AUTH: Time not allowed
}
```

The store core validates the choice at commit, falls back to LRU on overrun, and is certified once against arbitrary ("demonic") hints. Every policy that type-checks is therefore bit-identical in output, and the Forge searches this space on bytes and stall time alone (§8).

**(d) A spec and contract with evidence** (NUMERICS.md §5.3 routing; D2-E):

```rust
// routing.spec.mith: owned by role Author, hash-locked on admission
spec fn route_topk(sel: &[f32], k: usize) -> Vec<u32>
    requires k <= sel.len()
    ensures result.len() == k
    ensures forall |i: usize, j: usize| i < j && j < k ==>
                ranks_before(sel, result[i], result[j], Order::Desc, Ties::LowerIndex, Nan::Last)
    fault_model numerics_v1
    rejects [first_k(sel, k), stable_sort_asc(sel, k)];     // vacuity witnesses must FAIL

#[implements(route_topk)]
#[evidence(require = proof, min_spec_strength = 0.95)]
fn grouped_topk(sel: &[f32], k: usize, g: GroupCfg) -> Vec<u32> uses { Alloc } { todo!("grouped") }
```

`mithc prove` discharges the `ensures` through SMT (auto-active, Dafny-style; on vericoding, Dafny's union success was 82.2% against 44.2% for Verus and 26.8% for Lean, R03). A Builder cannot edit `routing.spec.mith`. `min_spec_strength` refers to the mutant-kill record of the spec itself (§5.4).

**(e) An effectful direct-I/O function with capabilities, and a sealed nondeterminism boundary** (G05; `platform_win.c`, `store.c`):

```rust
fn read_slab(f: &File<Direct>, at: Offset<4096>, buf: &mut SlabBuf<4096>) -> Result<(), IoError>
    uses { Io }
{
    f.read_at(at, buf)      // std (audited): overlapped + wait on Windows, pread + O_DIRECT on POSIX
}

pub fn acquire(s: &Store, key: ExpertKey) -> Result<Lease, IoError>
    uses { Blob, Fail }                                         // what callers see
    seals { Io, Spawn, Nondet } by test(golden::scheduling_independence)
{
    s.state.with_lock(|st| st.lookup_or_enqueue(key))?.wait()  // reader threads, demand queue
}
```

`seals` is the audited boundary that G05 found necessary. The body may observe scheduling, but the declared result is value-deterministic because it is a pure function of content-hashed bytes (`Blob`). The justification must name evidence, here Hearth's INV-DET-1 golden test, and the ledger records it. `Lease` is a `linear` type, so a missing release is a compile error.

### 3.3 Types

- **Scalars:** `i8`-`i64`, `u8`-`u64`, `f16`, `bf16`, `f32`, `f64`, `bool`, `usize`. `i4`/`u4`/`e2m1`/`e8m0` exist only as element codes inside `layout`s, not as general arithmetic types (R10 C6: real systems lower sub-byte types through int8 dots or lookup tables).
- **Aggregates:** structs, enums, tuples, arrays `[T; N]`, slices, `Vec<T>` (needs `Alloc`), traits with static dispatch and Rust meaning. No `dyn` in v1.
- **Const generics as the size and index layer:** `SlabBuf<4096>`, `Offset<4096>`, `[f32; N]`. Size and range side conditions go in `requires` clauses (Verus/Dafny keyword, familiar to models trained on verification code). There are no refinement-type annotations on every binding.
- **SIMD:** explicit `Simd<T, N>` and `Mask<N>` with intrinsic-level methods, available only in `schedule` lowerings and `#[target]` functions (R11 P0).
- **Units and origin** (revisit ADOPT): `Quantity<U, Measured | Simulated | Predicted>`, for example `Quantity<GBps, Measured>`. The formatter refuses to print an unlabelled performance number, so INV-HONEST becomes a type rule.
- **Inference:** inside bodies only. Signatures of public items are mandatory and there is no implicit `Any` (R03-3).

### 3.4 Effects and capabilities

- **Effect rows are written with `uses { ... }`.** Built-ins:
  - `Io`, `Spawn`, `Alloc` / `Alloc<A>`, `Time`, `Fail`;
  - `Nondet`: observing scheduling, completion order or relaxed atomics;
  - `Blob`: value-deterministic reads of content-hashed immutable bytes;
  - `Unsafe` and `Foreign`, both requiring package grants;
  - `Lossy(profile)`: output-changing approximation;
  - `Compile`: load-time code generation.
- **Effects are capabilities passed implicitly** (Effekt style) and rooted at `main(root: Root)`. Attenuation is ordinary code, for example `root.fs().read_only(model_dir)`.
- **Handlers** are tail-resumptive or one-shot only (R09).
- **Inference and declaration.** Effects are inferred for private functions. Public functions must declare them, and an inferred-but-undeclared row is an error whose fix inserts the row. This answers R09's open question in favour of agents: the boundary is explicit, while leaf code stays terse.
- **ABI exports must be `Fail`-free.** Errors cross the C ABI as codes, never as aborts (INV-SAFE, R11 P0).
- **timing_only** is a module kind whose permitted row is empty apart from hint outputs: no `Io`, `Time`, `Alloc` or FP-environment writes, static fuel, and opaque payloads (D2-A).
- **Fidelity grade and determinism scope** are computed per function and shown in its signature summary:
  - grade: `exact`, `real(bound)` or `approx(profile)`;
  - scope: `det(cross_device)`, `det(device(t))` or `schedule_dependent`.

  A Hearth export such as `hearth_eval` carries `#[require(grade = exact, det = cross_device)]`.

### 3.5 Memory model

The memory model is mutable value semantics with second-class references, written with Rust syntax that keeps Rust's meaning where the forms overlap (R09, G05):
- By-value parameters move, exactly as in Rust.
- `&T` is a shared borrow and `&mut T` an exclusive borrow for the duration of a call.
- References cannot be stored in structs or returned. That is the rejected-Dc row FF-REF, and it removes lifetime annotations from the language and the card.

Further rules:
- `linear struct` marks values that must be consumed, such as leases and in-flight I/O.
- `Send` and `Sync` keep their Rust names and meaning; they are G05's transfer and share kinds.
- Arenas carry `Alloc<A>`.
- Raw pointers need `Unsafe`.

The audited std layer is a few hundred lines per OS [inference, G05]: `Mutex<T>::with_lock` (scoped exclusive access), `Condvar`, `Arena::split` into owned 4096-aligned `SlabBuf`, `Frozen<T>` with `into_unique`, `File::read_at`, scoped pool and services, and an optional MPSC ring. G05 judged that `store.c` fits with no user-level `Unsafe` [inference, medium-high].

Liveness bugs live in safe code, so test builds swap in a loom-style schedule-permuting scheduler under the std primitives (G05).

### 3.6 Numerics

- **Strict IEEE everywhere:** round-to-nearest-even, no contraction, no reassociation, no FTZ/DAZ. `mul_add` is the only fused operation; it is the settled "explicit fma" under Rust's own name, so FF-FMA stays coincident with Rust. A backend implements each op exactly or refuses to compile (G03).
- **Named reduction orders** in `canon`:
  - `sum16` and `dot16` (16 lanes, then an 8-4-2-1 tree);
  - `sum_seq`;
  - `Order::Blocks(64, ExactI32)` followed by a sequential pass;
  - `Order::Chunks(c, Seq)`, a device-neutral fixed-chunk form for future GPU attention (G03).
- **Exact integer accumulators with proven bounds** license reordering. For Q4, |isum| ≤ 64·8·127 = 65,024; for Q8, 64·127·127 = 1,032,256 < 2^24, so `(float)isum` is exact (R07). This is the route to VNNI and dp4a, and possibly to INT8 tensor cores, without breaking bit identity.
- **Transcendentals are specified functions:** `cr::expf` (correctly rounded) or `canon_v1::expf` (a fixed op-DAG). Platform libm is reachable only through `extern "C"` with `Foreign + Nondet(platform)`, and exact code rejects it. A `parity::` shim exists only for migration comparisons against the C binary (G04).
- **The FP environment is a checked precondition.** Default MXCSR is asserted at pool-worker start and is part of what T1 certificates assume (G02).
- **INV-LOSSLESS-DEFAULT is a link rule.** A configuration field whose variants reach `Lossy(p)` code may not take such a variant from `Default`.

### 3.7 Staging and specialisation

Three stages, ordered by how often an agent needs them:
1. **Build time:** `const fn` and const generics with Rust meaning. Mithril's `const` evaluation may accept more than Rust's; a superset is not a reinterpretation.
2. **Load time:** `#[bind(load)]` parameters (binding-time types). Keys must be finite; specialising on an unbounded value is a compile error. Specialisation produces a residual kernel through the AOT C residual or copy-and-patch, plus a lockstep check against the unspecialised meaning (revisit S10).
3. **Generators:** typed `Code<T>` quotes for library authors, documented in Tier 2. Agents write `schedule` blocks, which are data over a small vocabulary, instead of quotes. This keeps Tier 0/1 small; the tie-break is that one surface for kernels beats two.

A Python-embedded schedule-search API (allowed by the settled constraints, G01) is deferred until the harness shows that agents benefit from it. The Forge drives schedules through `mithc` JSON instead.

### 3.8 Modules, packages, editions

- **Modules:** `mod`, `use` and `pub` with Rust meaning; one package manifest, `mith.toml`.
- **The manifest pins:**
  - dependencies by content hash;
  - the toolchain hash;
  - the edition;
  - capability grants per package (`Unsafe`, `Foreign`; the ponyc `--safe` precedent, G05);
  - **ownership** by definition path and role (specs: Author; goldens and harnesses: Gatekeeper);
  - **evidence policies**, for example `kernels = "validated"`, `perf_claims = "measured"`.
- **Editions:** syntax freezes early and changes additively through editions. Every breaking change ships a `mithc fix` migration that is MachineApplicable and preserves the corpus bit-exactly, because every break becomes stale-prior debt (G01; Zig 0.15, Mojo pre-1.0).

---

## 4. Compiler pipeline and IRs

```
 .mith text --(Lark-conformant, error-tolerant parser)--> Syntax (lossless CST, holes kept)
   --> HIR      names resolved, desugared, holes as typed nodes, def hashes (alpha-normalised)
   --> THIR     types, effect rows, capabilities, ownership, fidelity grade, det scope
                 \--> Fact Plane relations (Datalog)  \--> diagnostics (grouped) + fixes
   --> MCore    small typed core calculus; monomorphised; MVS explicit (move/borrow/consume)
                 \--> reference interpreter (oracle) ; Lean 4 executable semantics (diff-tested)
   --> KIR      kernel fns only: index loop nests + layouts + explicit FP op-DAG + int subterms
                 + schedule application (tile/parallel/lower/prefetch) -> T1/T2 obligations
   --> backends C11 text (strict flags) | MIR-x86 (instruction SSA keyed by XED iclass) -> bytes
                 | copy-and-patch stencils | PTX text (.rn explicit; gated)
```

- **Named IRs:**
  - *Syntax* is lossless, so the formatter and the edit protocol round-trip.
  - *HIR* carries holes.
  - *THIR* is typed HIR.
  - *MCore* is normative.
  - *KIR* is the kernel IR.
  - *MIR-x86* is the machine IR.

  Store, policy and I/O code stays in MCore with effect annotations. Byte and time "views" of the same code (D2-C, one flow and many handlers) arrive later as additional interpretations of MCore, not as a separate IR.
- **Query architecture.** The compiler is a salsa-style query database whose keys are content hashes (R09). Early cutoff mirrors principle 2: if a body changes but its signature hash does not, dependents are not re-checked. Verification, test and benchmark results are queries whose persisted cache *is* the evidence ledger (§5.3). Latency targets for a single-definition edit on a Hearth-sized corpus (about 9k engine lines): `mithc check` p50 ≤ 200 ms and p95 ≤ 1 s; `mithc hole` ≤ 100 ms **[target]**.
- **Completion-engine API.** Mündler et al. ask language designers to build "compilers as incremental completion engines" (R03 §5). mithc exposes `prefix_check(text_prefix) -> {extendable, admissible_token_classes, expected_type?}`. Hearth's constrained decoding (§7.9) and LSP completion both use it.
- **Backends, in order:**
  1. **C11** with strict FP flags (MSVC `/fp:precise`, `-ffp-contract=off`), no runtime library. This is the Hearth port path and keeps INV-DEP satisfiable (§9).
  2. **A direct x86-64 emitter** for KIR kernels only, over the owned semantics table (G02: about 25-40 instruction families, 1.5-3k lines, fuzz-validated on Zen 5). T1 then checks *machine code*, not just IR.
  3. **Copy-and-patch JIT** for load-time residuals: W^X, `FlushInstructionCache` (R08).
  4. **A narrow PTX expert-tier backend** loaded through `nvcuda.dll`. It is owner-gated (G03).
  5. **LLVM**, optional and never in the trusted path.

  The rustc Cranelift backend lists SIMD as unsupported and QBE has no vector types (R09), so neither is on the path.

---

## 5. Verification and evidence

### 5.1 Trusted core

Each component is small, adversarially tested and versioned by hash. These components are trusted; everything else is untrusted search:
1. the MCore type, effect and grade checker, mirrored by the Lean reference semantics;
2. the T1 FP-DAG matcher and its audited list of IEEE-exact rewrites;
3. the x86 semantics table (fuzz record per iclass, with Bochs as a second oracle; G02);
4. SMT and bit-vector solvers, with certificates where available (`bv_decide`-style);
5. `mithcheck`, which re-checks the witnesses shipped with an artifact;
6. Gatekeeper code: the harness, the clock, golden runners and spec-strength runners.

Precedent warns against complacency: testers found 15 eBPF verifier logic bugs in a month, and the Lean kernel had a soundness bug in July 2026 (R07, revisit). Trusted cores are therefore attacked on purpose with chaos suites and mutant pools.

### 5.2 Checker tiers

| Tier | Checks | Cost | Decides |
|---|---|---|---|
| T0 | types, effects/capabilities, ownership, grade, det scope, timing_only confinement | ms | acceptance of every edit |
| Contracts | `requires`/`ensures`/`invariant` via SMT (auto-active) | s | `proof` evidence |
| T1 | emitted float DAG ≡ meaning DAG, modulo the audited exact rewrites (KLEE-FP precedent) | s | `validated` for kernels |
| T2 | integer side conditions (ranges, saturation freedom, exact int-to-float, alignment) by bit-vector SMT | sub-s | licences for integer reordering |
| T3 | tolerance certificates (FPTaylor/Satire-class) plus runtime margin checks at top-k and argmax; opt-in | s-min | `real(bound)` grade, labelled lossy |
| Tests | property tests; AST- and type-aware mutation on the diff; schedule-permutation for concurrency | s-min | `tested`, with the mutation score recorded |
| Oracles | Hearth goldens plus the cross-binary hash corpus (logits, routes, quantiser bytes) | min | port acceptance |
| Bench | runtime-owned clock, joins all async work, poisoned allocations, anytime-valid e-values | min | `measured(hw)` |

A checker returning "unknown" or timing out counts as rejection for promotion. For iteration it counts as "not yet": the agent sees the smallest failing obligation (§5.5).

### 5.3 Evidence lattice and ledger

- **Lattice:** `proof > validated > tested(mutation ≥ τ) > measured(hw) > assumed`. An artifact's grade is the *meet* of its evidence and its spec's strength (D2-E).
- **Ledger key:** `hash(code closure, spec, toolchain, target, hardware fingerprint)`. Any change to a component re-keys the entry, so entries invalidate automatically.
- **Entries store** the claim, evidence kind, witness or artifact hash, principal (agent id, model family, role), cost and time.
- **Negative results are tombstones.** Each records its scope, a failure class (H/T/S/E/V/C/X/F, R02) and machine-checkable resurrection triggers. Hearth's "lookahead REJECTED for this model, drive and cache size" is the template.
- **Policies in `mith.toml`** turn conventions into errors. Examples: an `exact` kernel realisation without `validated` evidence cannot link into a release build, and an untyped performance number in docs fails `mithc doc-check`.

### 5.4 Spec ownership

Specs live in `*.spec.mith` files owned by role Author (SESL, D2-E):
- A change set in which a Builder or Prover writes a spec, witness, mutant pool or gate is refused.
- Change sets are judged as content-addressed objects, which defeats the symlink, case-twin and 8.3-name bypasses Hearth's golden gate suffered (D2-E).
- `mithc spec-strength` reports:
  - soundness (the reference and all legal variants pass);
  - the kill interval [K_lo, K_hi] with the unknown fraction;
  - vacuity (rejection witnesses must fail);
  - latitude;
  - independence, which counts as measured only when principals come from distinct model families.
- The first numerics fault model, `numerics_v1`, contains the D2-E list: FMA contraction, lane-count or tree change, round-half-even to truncate, the 127/128 clamp, a dropped scale, softmax without max-subtraction, a NEOX/GPT-J RoPE swap, GQA head mapping, a tie-break flip, and NaN canonicalisation.

This matters because LLM-written specs are sound and complete only about half the time (Verina 51-52%), and about 9% of vericoding successes rested on specs that were too weak (R03).

### 5.5 What an agent sees

`mithc evidence <def>` returns four things:
- what is established;
- what the policy requires;
- the gap;
- the cheapest next action, with an estimated cost.

`mithc prove` turns failed SMT obligations into *concrete Mithril values* (a counterexample rendered as a test case) and offers to add it as an Adversary-owned regression test. Counterexamples are the most actionable verifier output **[inference]**; DafnyBench and AlgoVeri show that verifier-feedback rounds raise success (R03 §7).

---

## 6. Runtime and targets

- **ISA tiers are data:**
  - x86-64 scalar;
  - AVX2 with or without AVX-VNNI (Intel client chips through Panther Lake have no AVX-512);
  - AVX-512 F/BW/VL/VNNI/BF16 (Zen 4/5; Zen 5 desktop runs a full 512-bit datapath, has no AMX, and executes gathers as microcode, R08);
  - AVX10.2 pending;
  - arm64 NEON (macOS CI).

  Dispatch happens once at load time through cpuid plus XCR0 and an atomically cached function table. There are no P-core/E-core paths (R08). Vector width is a cost-model choice, except that a bit-exact reduction's lane count is part of its meaning: `sum16` maps to one zmm, two ymm or a half-warp (G03).
- **Memory tiers are data:** VRAM, DRAM and NVMe, plus the slow HDD, with capacity, bandwidth and transfer cost in a machine profile. `resident<T, tier>` and `streamed<T, tier>`; demand versus prefetch priority; completion-order compute with a canonical-order combine (rank-order expert sums, NUMERICS §5.3). VRAM is in the placement model from v1 even before any GPU code exists (G03).
- **Threads:** one persistent pool (spin then sleep, per-worker condition variables), and a disjoint-write `par for` whose disjointness T0 proves. Small regions stay on the caller, as in `model.c`. Pool dispatch measured about 0.75 µs per 16-thread round trip (R11); the port must match it.
- **Determinism scopes:**
  - the logits path must be `det(cross_device)` for a named canonical core (`canon.v1`);
  - device-specific orders such as tensor-core MMA or vendor libraries live only behind `det(device(t))` or `Lossy`, with their own goldens;
  - goldens are keyed by contract version, not by device (G03).
- **Hot-swap:** versioned dispatch tables and overlay epochs published at quiescent points (token boundaries, `hx_store_tick`), with reclamation through `Frozen` refcounts. No self-modifying code, no INVD, no CAS tricks (R08, R12).
- **Weights** are immutable and content-addressed, changed only through typed overlays with provenance (R12). These are runtime library types, not language features.

---

## 7. The agent protocol and toolchain

### 7.1 The loop, with budgets

| Step | Call | Response budget [target] | Evidence lever |
|---|---|---|---|
| Orient | `mithc resume <manifest>` or `mithc context <def> --budget 6000` | Tier 0 (≈2k) + project card (≈1k) + pack (≤6k) | compact always-on index: 53% → 100% (Vercel, G01) |
| Skeleton | write signatures plus `todo!("...")` bodies; `mithc check --json` | ≤1.5k tokens per check (top 5 groups) | holes: ~10× for StarCoder2-15B with type context (Hazel, R03) |
| Fill | `mithc hole <name>` then an edit | ≤1.5k per hole query | expected type and bindings are the most valuable context (R03 §4, §6) |
| Repair | `mithc edit` (edit plus check in one call) | ≤1.5k | grouping 4.97% → 44.76% (RustAssistant) |
| Verify | `mithc prove`, `mithc test --mutation`, `mithc evidence` | ≤1k plus counterexamples | auto-active SMT beats Lean for LLM authors (R03 §10) |
| Benchmark | `mithc bench <def> --vs <baseline>` | ≤0.5k | runtime-owned clock against documented reward hacks (R01, R05) |
| Hand over | `mithc handover` | manifest generated from the ledger | Hearth's handover practice, made unforgeable |

Every response ends with `next: [...]`, the one to three highest-value next commands, so the agent rarely spends a turn exploring **[inference]**.

### 7.2 The reference card

**Tier 0: at most 8,192 bytes of ASCII, always in context, embedded in AGENTS.md.** It does not go in a skill: on-demand skills were never invoked in 56% of Vercel's runs (G01). CI also checks the token count on two pinned tokenizers (≤ 2.3k each **[target]**).

| Block | Byte budget [target] | Content |
|---|---|---|
| Identity and the subset rule | 700 | "If it looks like Rust it means Rust; otherwise it is rejected or uses a new keyword." |
| 12 rules | 900 | exact numerics, effects in public signatures, no stored references, holes, no line numbers |
| New keywords and effects | 700 | `uses seals requires ensures invariant decreases spec kernel schedule layout policy timing_only linear`; effect list |
| False-friend table | 2,300 | the §3.1 rows, one line each, with the fix |
| Snippets | 2,500 | eight tiny ones: fn with `uses`; `todo!` hole; `requires`/`ensures`; `layout`; `kernel` + `schedule`; `policy`; `seals`; `Quantity` |
| The loop and commands | 1,000 | §7.1 in eight lines; JSON field glossary |

**Tier 1: 5-15k tokens in three modules**, served by `mithc guide core|std|kernels` and also over MCP:
- *core*: the printed Lark grammar (≤3k tokens) and the ownership rules;
- *std*: signatures and numerics;
- *kernels*: schedules, specs and evidence.

Together the modules carry 40-80 snippets and the error-code index. This sits between SkillsBench's compact and standard optimum and the Mojo and MoonBit guides (3.5-4k and ~9k words; G01 F5.5).

**Tier 2: retrieved.** The normative manual (≤30k words), `mithc explain CODE`, `mithc doc <path>` and LSP hover.

**Project card: at most 4 KB, always on.** For Hearth it holds invariant IDs with one line each (text hash-referenced, carried verbatim), ownership and commands. **[DEVIATION, mild]**: the settled Tier 0 budget covers the language card. I count the project card separately, so the always-on total is at most 12 KB, and the harness measures the split.

**Governance.** Maintainers curate the cards; self-generated skills scored 8-12 points *below* having no skill (SkillsBench, G01). Card atoms are content-addressed. Every edit runs a screening subset of the harness (about 100 IRT-selected items, tinyBenchmarks-style); editions run the full harness. A construct that needs more than one snippet plus one false-friend line is a design smell and must justify itself in the harness.

### 7.3 The Lark grammar

There is one normative `mithril.lark`. It is keyword-first with LL-friendly productions, uses explicit whitespace terminals and does not depend on `%ignore`, so it fits OpenAI's CFG-tool restrictions (R03). Budget: at most about 150 rules, printed in at most 3k tokens **[target]**. The production parser is hand-written for error recovery and is differentially fuzzed against the Lark grammar, so the two must accept the same language. Illustrative excerpt:

```
item: attr* vis? (fn_item | struct_item | enum_item | layout_item | spec_item
                 | schedule_item | policy_item | impl_item | use_item | mod_item)
fn_item: (KERNEL _ws)? "fn" _ws NAME generics? "(" _ws? params? ")" ret? effects? seals? contract* block
effects: _ws "uses" _ws? "{" _ws? EFFECT (_ws? "," _ws? EFFECT)* _ws? "}"
contract: _ws ("requires" | "ensures" | "invariant" | "decreases") _ws expr
hole: "todo!" "(" _ws? STRING? _ws? ")"
_ws: (WS | COMMENT)+
```

The same file drives five things: the Tier 1 printout, OpenAI CFG tools, Hearth's grammar mask (§7.9), the Surface Lab parsers and formatter tests (parse∘print = id, D3-i).

### 7.4 Typed holes, hole queries, type search

`todo!()` and `todo!("name")` are holes. They type-check against the expected type, the program still runs, and reaching a hole is `Fail` (Rust's panic). `mithc hole q_lat --json` returns, for example:

```json
{"hole":"q_lat","at":"model::mla_attend@h:7c21","expected":"f32","grade":"exact","effects_allowed":[],
 "in_scope":[{"name":"q_nope","type":"&[f32; NOPE]"},{"name":"w_uk","type":"&MatF32<NOPE, C>"},{"name":"c","type":"usize"}],
 "obligations":["ensures result == canon::dot_seq(q_nope, w_uk.col(c))   // NUMERICS 5.2: n ascending from 0.0"],
 "candidates":[{"fn":"canon::dot_seq","type":"fn(&[f32], &[f32]) -> f32"},{"fn":"canon::sum_seq","type":"fn(impl Iterator<Item = f32>) -> f32"}],
 "false_friends":["FF-SUM: float Iterator::sum is rejected in exact code"],"tokens":388}
```

- **Holes as stubs.** Holes are how agents generate top-down. A cold agent that writes Rust-style stubs produces typed holes without having to learn anything new **[inference; Surface Lab arm]**.
- **Type search against hallucinated APIs.** `mithc search --type "(&[f32], &[f32]) -> f32" --uses "{}"` queries a content-addressed API index. Unknown identifiers in diagnostics come with nearest-name suggestions drawn from the same index (R03-6).
- **Propagation.** When a signature changes, `mithc propagate` turns every dependent that no longer type-checks into a hole with a context entry (S3), so a cross-module change becomes a list of local work items. Cross-file changes are where agents degrade (Multi-SWE-bench, R03).

### 7.5 Diagnostics and fix applicability

```json
{"code":"E0412","kind":"FalseFriend","construct":"FF-SUM","group":1,"root":true,
 "at":{"def":"model::rmsnorm@h:91aa","anchor":"x.iter().map(|v| v * v).sum::<f32>()"},
 "prior":"Rust: Iterator::sum is a sequential left fold","rule":"exact code names its reduction order (NUMERICS 1, INV-DET-3)",
 "fixes":[{"applicability":"MeaningChanging","replace":"canon::sum16(x.iter().map(|v| v * v))","invalidates":["tested:model::rmsnorm"],"obligations":["test"]},
          {"applicability":"Safe","replace":"canon::sum_seq(x.iter().map(|v| v * v))"}],
 "cascade_suppressed":3,"explain":"mithc explain E0412"}
```

Rules:
1. JSON is primary and text is derived from it. Codes are stable, and `mithc explain` holds one worked example per code.
2. Diagnostics are grouped by root cause. Each group reports one root and the count of suppressed cascades. By default a response holds at most 5 groups, ordered by cause.
3. Spans are anchors (definition path, hash and an anchor text), never line numbers. SARIF 2.1.0 export carries line and column for human tools.
4. Applicability extends rustc's four levels:
   - `Safe`: meaning-preserving; batch-applicable with `mithc fix --safe`.
   - `InterfaceChanging`: shows the number of dependents that will become holes.
   - `MeaningChanging`: lists the evidence it invalidates and the obligations it creates.
   - `SpecTouching`: needs role Author and is never auto-applied.
   - `HasPlaceholders`: inserts holes.
   At most one `Safe` fix per diagnostic.
5. `FalseFriend` diagnostics name the prior and the Mithril rule, because the false-friend gap is the cold-start failure the evidence measures (G01 F2).

Open evidence gap: no controlled study varies only the wording of diagnostics (R03 §7). Wording is therefore a Forge target scored by the harness (§8), not a matter of taste.

### 7.6 The edit protocol

Operations:
- `view(path, projection = familiar | signature | typed | slice)`, in windows of about 100 lines (SWE-agent's best setting);
- `replace_def(path@hash, text)`;
- `replace_in(path@hash, search, replace)`, where `search` must match exactly once inside that definition after canonical formatting, with whitespace matched leniently;
- `insert_after(path@hash, text)`;
- `fill_hole(path@hash, name, text)`;
- `rename(path, new)`, which changes no hash because names are metadata;
- `delete_def(path@hash)`.

Behaviour:
- **Atomicity.** A batch of operations is parsed, formatted and type-checked as one unit. On success the response returns new hashes, the check result, invalidated evidence and `next`. On failure nothing is applied and the response returns grouped diagnostics.
- **Staleness.** A stale hash returns `StaleAnchor` with the current hash and text slice. Nothing is applied fuzzily. In a single-author preprint (medium confidence, S3), line-number edits corrupted 99.1% of files after a one-line shift, function-name anchors hit the wrong function 12.7% of the time, and an anchor-and-verify applier misapplied silently once in 8,320 trials.
- **Envelope for Claude.** Claude's structured outputs accept only non-recursive JSON Schema (R03). The envelope is therefore flat (`op, target, anchor, search?, replace?, text?`), with code carried as a string payload validated by mithc, never as a JSON-encoded AST (aider's JSON penalty).

```json
{"op":"replace_in","target":"model::rmsnorm","anchor":"h:91aa",
 "search":"x.iter().map(|v| v * v).sum::<f32>()","replace":"canon::sum16(x.iter().map(|v| v * v))"}
```

The protocol is an accelerator, not a gate. Agents limited to `str_replace` or raw file writes still work: files are canonicalised on check and identity is recomputed. CodeStruct's gains (+1.2-5.0% Pass@1, 12-38% fewer tokens) came from structured actions over plain files (S3). That is the design point, and §10 M2 holds the kill criterion if the protocol adds nothing.

### 7.7 Context packs

`mithc context <target> --budget N --for edit|review|port` assembles, in priority order:
1. the target definition;
2. signatures, effects and contracts of callees and callers, without bodies;
3. type definitions in the closure;
4. the governing specs with their strength;
5. evidence status;
6. false-friend rows for the constructs present;
7. relevant invariants, verbatim;
8. one corpus example using the same API.

The pack is truncated to budget and ends with an index of omitted items the agent can expand. `#[closure_budget(N)]` makes context locality a compile-time property of a module (S15). For scale: `store.c` alone is 1,030 lines, plausibly 12-15k tokens **[inference]**, while a pack for editing `pick_victim` should fit in 6k **[target]**. M2 measures this as an ablation, packs against agent-driven file reading.

### 7.8 Handover manifests

`mithc handover` emits a manifest that extends Hearth's `handover.schema.json`. Its *facts* come from the toolchain journal and the ledger, not from the agent's narration:
- base and head store root hashes;
- the commands actually run, with exit codes;
- evidence added and invalidated;
- policy gaps;
- open holes with their contexts;
- outstanding diagnostic groups;
- typed measurements (`kind` mandatory, with hardware fingerprint and baseline);
- invariants touched (ID plus text hash);
- tombstones created.

The agent adds only `rationale` and `next_actions`, each length-capped. DGM faked its test logs (R01), so a manifest whose facts the agent cannot write is the fix.

`mithc resume` rebuilds the orientation pack from the manifest (§7.1). The successor never reads a transcript, which matches Hearth's practice.

### 7.9 Constrained decoding where Hearth owns the logits

Hearth gains an opt-in sampler mask hook in `hearth.h`. The default is off, so INV-LOSSLESS-DEFAULT holds.
- **Grammar mask.** Computed from `mithril.lark`, implemented in C11 inside Hearth because INV-DEP forbids linking llguidance (Rust) or XGrammar (C++) (R03). A llguidance-class mask costs about 50 µs per token, roughly 0.1% of a 45-53 ms decode token (R03).
- **Type mask.** Supplied out of process by mithc's `prefix_check`, applied only at identifier and hole boundaries. Mündler et al. found 99.4% of tokens needed only one check.
- **Expected effect.** Type constraints cut compile errors by 52-75% where syntax-only constraints cut at most 9%. Gemma 2 2B's repair success rose from 33.5% to 56.4% (HumanEval) (R03).
- **Mask placement.** The mask applies only to the code channel (tool-call payloads), leaving reasoning unconstrained (the "Let Me Speak Freely" caveat), with grammar-aligned sampling as an option.
- **Budget.** Total mask overhead at most 5% of decode time **[target]**.

Small models are where this matters most. The ability to override semantic priors emerges with scale, which predicts larger false-friend effects for local models (D3-i) **[inference]**.

### 7.10 CLI, LSP and MCP surface

One JSON contract is exposed three ways:
- **CLI:** `check`, `edit`, `view`, `hole`, `search`, `context`, `fmt`, `fix --safe`, `explain`, `guide`, `test [--mutation]`, `prove`, `spec-strength`, `evidence`, `bench`, `caps` (the capability graph), `query` (the Fact Plane), `ledger`, `handover`, `resume`, `lift --from c|rust`, `pack`, `harness`, `forge`, `revisit`.
- **LSP:** standard requests plus ChatLSP-style extensions (hole context, context pack, evidence hover). Claude Code ships an LSP tool (R04).
- **MCP:** the same operations with non-recursive JSON Schemas.
- **Agent onboarding:** an AGENTS.md snippet carrying Tier 0.
- **Lifter.** `mithc lift` translates C11 and Rust subsets into `.mith`, with differential tests (the SPEAC/LLMLift pattern, G01). It maps `nearbyintf` to `round_ties_even` and flags C-prior contraction. It is the cold-start escape hatch and the port's first tool.

### 7.11 The comprehension harness: evals that gate language decisions

The comprehension harness has two parts: `mithc pack` and the Comprehension Ledger (D2-D). Its components:
- **Sealed task families** (Gatekeeper-owned, hash-locked, rotated each epoch):
  - T-Q4: bit-exact Q4 dot and matvec;
  - T-ACTQ: activation quantisation;
  - T-ROUTE: grouped top-k with ties;
  - T-NORM: RMSNorm and softmax;
  - T-EVICT: a timing_only policy (oracle: bit-identical logits plus bytes and stall);
  - T-STORE: a slab arena with pins and 4096 alignment;
  - T-CTRL: non-numeric control tasks.

  Every oracle must kill at least 95% of mutants, including `numerics_v1`.
- **Arms:** Mithril (Tier 0; Tier 0+1; Tier 0+1+2), C11 and Rust controls, and an obfuscated-Mithril control. Participants are at least two frontier model families plus one Hearth-hosted local model.
- **Metrics:**
  - verified pass@1 (VP@1);
  - the **checker-accepted-but-wrong rate** (CABW), judged by the hidden oracle;
  - tokens, turns and dollars per verified pass (TPV, turns/VP, $/VP);
  - first-compile rate.

  Fitness is the slope on a Pareto front, never a raw ratio (revisit REJECT).
- **Statistics:** paired seeds, IRT item selection, anytime-valid sequential tests. Detecting a 5-point difference needs about 1.5k attempts per arm, and a 10-point threshold roughly a quarter of that **[inference]**. Screening runs use about 100 items; constitutional decisions use the full suite.
- **Surface Lab** (D3-i), run per construct:
  - arms: familiar, familiar plus mandatory disambiguator, alien, obfuscated;
  - decision rule: minimise TPV subject to false-friend incidence ≤ τ;
  - falsifiers: F1 (the divergence-marking rule itself), F3 (alien syntax only where the divergence is checker-invisible) and F4 (decay: re-run every model generation).
- **Language change protocol.** Every change to the grammar, keywords, std signatures in Tier 0/1 or diagnostic templates goes through the same steps:
  1. a Surface Map diff;
  2. a pre-registered expectation and kill criterion;
  3. a screening run;
  4. a full run for editions;
  5. an ADR;
  6. human promotion.

  The Forge may propose such changes but never promote them.

### 7.12 Coordination and safety of agent actions

- **Concurrency between agents** is optimistic at definition granularity. Hash anchors give `StaleAnchor` instead of silent overwrites, and merges are structural per definition. Hard file locks are rejected: Cursor measured 20 agents collapsing to the throughput of 2-3 (revisit REJECT). Typed conflict holes (CALM ledger) come later.
- **Ownership** is per definition path and role, held in the manifest, not per file.
- **`mithc run`** grants only the declared capabilities. Forge evaluation runs in a separate process under Windows Job Objects (or WSL2 or a container), with no network and read-only goldens (R01).

---

## 8. The Forge: self-improvement and its trust model

**Levels, in order of trust required:**

| Level | What is searched | Correctness comes from | Fitness | Promotion |
|---|---|---|---|---|
| Realisations | schedules, timing_only policies, layouts, exact rewrites | the space is certified once (T1/T2 by construction, D2-A core theorem) | measured bytes/token and stall time; tok/s with e-values | automatic into the archive; defaults need a human |
| Agent interface | card atoms, diagnostic templates, hole-context ranking, pack ranking, edit-tool behaviour | not applicable (no output semantics) | comprehension harness: held-out VP@1, CABW, TPV, turns | maintainer review plus a harness gate |
| Compiler heuristics | tiling, inlining and lowering choices among proven-legal rewrites; e-graph extraction | translation validation in evaluation builds; the trusted core is never searched | measured performance across niches | ADR |
| Language | constructs, std surface, editions | spec diff plus a corpus-preserving migration | harness on refreshed held-out suites | ADR plus human decision (R01) |

**Why the agent-interface level is first-class.** DGM's discovered gains were "better code editing tools" and context management (R03 §9). SWE-agent's interface ablations moved results by several points (R03). These are the cheapest, safest things to evolve because they cannot change program outputs. The Forge applies GEPA-style reflective delta edits to card atoms and diagnostic templates (R04: GEPA was an ICLR 2026 oral) and keeps a DGM-style archive of variants. Two Goodhart guards apply: held-out rotation each epoch, and ablation of one atom at a time.

**Trust model.** These rules are settled in design-inputs; this proposal adds no relaxations.
- The evaluator is hidden, frozen, hash-pinned and process-isolated. Candidates cannot read the clock, the reference outputs or the scoring rules.
- The runtime owns the clock and joins all asynchronous work before stopping it. Fresh allocations are poisoned and outputs must be materialised.
- Physics plausibility gates quarantine any score that beats a bound as a suspected hack. Bounds are replay-conditioned and only phys-tier bounds may prune (D3-ii); Belady is the bound for policies without prefetch, storage bytes divided by bandwidth when prefetching.
- Only checker-accepted candidates count. An "unknown" verdict is a rejection.
- Semantically identical candidates are deduplicated before spending (normalisation or e-graphs).
- Search runs over a QD archive of hardware × shape niches, with HGM clade selection and tombstones.
- Candidate code carries no ambient authority, so the documented exploits are type errors: overwriting timers, monkey-patching evaluators, `torch.empty` reuse, reading the reference output (R01, R05).

**Objectives are physics-aware.** Hit rate is not one: Hearth's depth-4 lookahead raised hits from 73% to 86% but cut decode from 13.0 to 10.0 tok/s (measured, revisit).

**Who proposes, and at what cost.** Frontier agents handle hard proposals. Hearth-hosted local models (for example Qwen3-30B-A3B, measured at 19-22 tok/s decode on the 9950X) generate the high-volume, low-stakes proposals: policies and schedules inside certified spaces, at zero marginal API cost and with identical gating **[inference]**. Every archived entry records its proposer's model family, so correlated failures across roles can be measured (D2-E; Goel et al.).

**What the Forge never does:** promote defaults, edit specs or goldens, build its own evaluator or verifier (the trusting-trust problem, R01), or run lossy candidates in the default lane.

---

## 9. The Hearth port

**Principles.**
- The port is a strangler fig behind the `hx_*.h` seams. Mithril-emitted C replaces C objects one module at a time, and every step is gated by the C tests, the golden suite and a new **cross-binary hash corpus**: SHA-256 of logits, routes, quantiser bytes and `hearth_matmul` outputs across ISA, T, row splits and NaN/inf cases (R11). The golden tests are relational and tolerance-based, so on their own they cannot detect a silent change of float order.
- The frozen `hearth-c-ref` binary stays as a permanent differential oracle.
- Agents port by `mithc lift` (transliteration) plus annotation: adding `uses`, specs, layouts and schedules.

**Comprehension precondition (lens addition).** Before stage *k* starts, the harness task family closest to that stage must reach its pre-registered VP@1 threshold with Tier 0+1 and the project card. Examples: T-Q4 for kernels, T-STORE for the store. The port is therefore also the harness's largest external validation set.

| Stage | Scope | Acceptance gates (all measured on the 9950X unless noted) |
|---|---|---|
| 0 Freeze and instrument | tag the base; build `hearth-c-ref`; generate the hash corpus; record CRT/libm identity; settle C3, C8, C10 below | corpus reproducible across 3 runs; maintainers sign the ADRs |
| 1 Leaf numerics | half conversions, Q4/Q8/BF16/F16 formats as `layout`s, quantisers, act_q8, matvec/matmul meaning plus scalar/AVX2/AVX-512 schedules | `test_quant` (117,681 checks); golden ISA and batch identity; quantiser output byte-identical to C (closes the oracle hole R11 found); hash corpus identical; single-thread AVX-512 Q4 ≥ 69.6 GB/s |
| 2 Container parser | `format` descriptions to a verified reader (EverParse-style, revisit ADOPT) | `test_modelfile` fuzz cases; golden malformed-file test; identical accept/reject and parsed configs against C on a generated fuzz corpus |
| 3 Pool | persistent pool over the std layer | `test_pool`; dispatch within noise of ~0.75 µs at 16 threads in interleaved A/B, including WSL2 crowded-pool scenarios |
| 4 Store logic and policies | `store.mith` over the audited layer; `seals`; timing_only eviction and prefetch ports; per-slab content hashes | `test_store`; golden scheduling independence; ≥ 7 GB/s peak direct-I/O demand reads on the 990 PRO; chaos suite kills 100% of seeded core mutants |
| 5 Forward pass | `model.c`: GQA, MLA, routing, MoE combine, `#[bind(load)]` specialisation | full golden suite (`check_golden.py --run`); 512-step real-Qwen3 decode hashes; tok/s ≥ 0.97× C at 2, 4 and 8 GiB caches and 512/2048-token prefill (interleaved, load-gated) **[target ratio]** |
| 6 API and platform | export `hearth.h` exactly (19 functions, same struct layouts plus `struct_size`); the platform layer as audited `Unsafe` (the riskiest stage, G05) | Python toolkit and ctypes mirror tests pass unchanged; `test_platform`; the C core is retired, `hearth-c-ref` kept |

**Honest performance expectations.** Fully cached Qwen3-30B-A3B decode is near the DRAM roofline. The physics ceiling is about 34 tok/s at 77 GB/s measured bandwidth, against Hearth's measured 19-22, which leaves about 1.5× of honest CPU headroom. Further gains must come from prefill and attention compute (a bit-identical AVX-512 value-pass prototype went from 18 to 94 GMAC/s), from I/O-compute overlap and from moving fewer bytes, or from the GPU tier (simulated 3.6-4.8× for in-RAM MoE) (R08, R11, G03). Mithril's port is judged on parity plus agent maintainability, not on speed-ups.

**Constitutional decisions Hearth's maintainers must make.** None of these may be made by an agent.

1. **C1 (INV-DEP / ADR-0001).** Option A: the Mithril-emitted C11 is committed to the repository, so the build still needs only a C11 compiler and OS APIs. INV-DEP then holds literally, and ADR-0001 is amended to make `.mith` the source of truth. Option B: the Mithril toolchain becomes a build dependency, which needs an INV-DEP change. I recommend A for the port period. Either option trips Hearth's decision circuit breaker.
2. **C2.** Is the RTX 5070 in scope for compute, and does `nvcuda.dll` count as an "OS API"? Optionally, move the display to the iGPU to free about 1.5 GB of VRAM (G03).
3. **C3 (ADR-0010, specified transcendentals),** decided *before* the hash corpus is built. UCRT switches between FMA3 and non-FMA3 paths at startup; the two were measured to differ on 44,232 sinf inputs (G04).
4. **C4.** Re-scope INV-DET-1 to "fixed binary, ISA, device plan and version root". Fix or qualify the mirror check, which samples only the first page.
5. **C5.** Make the cross-binary hash corpus a maintainer-owned sealed test. Extend INV-VERIFY to specs (spec escrow) and to the comprehension harness suites.
6. **C6.** Make `kind` (measured or simulated) mandatory in the handover schema, and accept toolchain-generated manifests as canonical.
7. **C7.** Add `struct_size` and version fields to the ABI structs before Stage 6.
8. **C8.** Decide the normative LFU heat decay: 0.9 in `hx_model.h`'s default path against 0.995 in ADR-0004 and `hx_store.h`.
9. **C9.** Add an MXCSR invariant: pool workers assert the default FP environment.
10. **C10.** Add the opt-in sampler mask hook (§7.9) to `hearth.h`.
11. **C11.** Move ownership in the task DAG from file paths to definition paths once `.mith` is the source.

**Live Hearth defects the research surfaced** (to report, not fix):
- the mirror check covers only the first page of up to 16 slabs;
- `hx_store_heat` returns an unguarded pointer, a data race;
- the `read_errors` ABI change wrote past the ctypes buffer;
- MXCSR is never asserted;
- the heat-decay drift above;
- storage channels in the server.

---

## 10. Roadmap

Durations are deliberately omitted. Each milestone ends at its gate. Kill criteria are pre-registered: they are written into the Comprehension Ledger before data collection and judged by a Gatekeeper.

| # | Milestone | Deliverable | Measurable gate | Pre-registered kill criterion |
|---|---|---|---|---|
| M0 | Measure first | Harness v0 (sealed T-* families, C11/Rust/obfuscated arms, 2 frontier families plus 1 local model); Tier 0 draft (≤ 8,192 B) and Lark v0; `mithc check` prototype (Syntax→THIR, holes, JSON diagnostics) with the MCore interpreter; Surface Lab pilot on D1-D5 | Oracles kill ≥ 95% of mutants including `numerics_v1`; paired test-retest VP@1 within ±3 points; Tier 0 within budget in CI | **K1:** Mithril (Tier 0+1, holes plus diagnostics) VP@1 more than 10 points below the Rust arm **and** CABW not at most 0.5× Rust's → stop the standalone language; Mithril becomes an evidence layer over a Rust subset |
| M1 | Kernels | C11 backend; KIR and schedules; `layout` types; T1 (KIR level); hash corpus; Stage 1 | Stage 1 gates (§9); T1 accepts all Hearth kernel variants with zero false accepts on `numerics_v1` mutants | T1 needs unaudited rewrites for > 20% of kernel variants, **or** generated kernels stay > 5% slower than C with no attributable cause → C kernels stay behind the seam and Mithril kernels serve as oracles only |
| M2 | Agent toolchain | Edit protocol, hole query, type search, context packs, handover and resume, LSP plus MCP, SARIF, Tier 1 modules | Replay shows the edit protocol's silent misapplication ≤ 1 per 5,000; hole context plus packs cut TPV ≥ 20% at equal or better VP@1; `check` p50 ≤ 200 ms **[targets]** | Edit protocol shows no gain over `str_replace` plus format-on-save (CI excludes benefit) → the store becomes a derived index and the protocol leaves Tier 0. Hole query shows no TPV gain → removed from the default loop |
| M3 | Parser, pool, machine code | `format`-derived parser; pool port; x86 emitter plus semantics table (fuzz record per iclass; Bochs cross-check); T1 on emitted x86 | Stage 2 and 3 gates; 100% of emitted iclasses have fuzz records; T1 passes on x86 for Stage 1 kernels | FP-sensitive entries (MAXPS NaN order, VCVTPS2DQ indefinite, etc.) cannot be matched to silicon → the x86 emitter is limited to integer kernels and FP stays on the C backend |
| M4 | Store, policies, Forge v0 | Safe `store.mith`; `seals`; timing_only ports; Forge v0 (eviction and prefetch; simulator first, then engine); loom-style tests of std sync | Stage 4 gates; 100+ generated policies all bit-identical in one golden run (prediction P1, D2-A); Forge winners labelled SIMULATED until measured | **Hard stop:** any type-checked timing_only policy changes logits → the policy feature and the Forge halt until the soundness hole is closed and a regression test is admitted |
| M5 | Forward plus API | Stages 5-6; load-time specialisation; `hearth.h` export | Stage 5 and 6 gates; Python toolkit unchanged | A module misses parity after its time box → it stays C behind its seam. More than 2 modules stay C → re-plan the port and publish a tombstone |
| M6 | Local agents; GPU tier (owner-gated) | Hearth mask hook, C11 grammar mask, type-mask provider; validated Mithril corpus from the port (MultiPL-T style) and an optional fine-tune; PTX expert GEMV (if C2 is yes) | Type masks cut local-model compile errors ≥ 30% with no VP@1 loss; GPU expert GEMV hash-identical to the CPU corpus (`canon.v1`); speed against llama.cpp MMVQ measured on the same card | Masks cut errors < 15% or reduce VP@1 → grammar-only masks. Canonical GPU GEMV < 0.5× MMVQ → GPU tier only as an opt-in `det(device)` contract |
| M7 | Edition 1 and the cold-agent proof | Syntax freeze; ≤ 30k-word manual; Lean MCore semantics differentially tested; Mithril MultiPL-E published; self-hosting decision | A fresh agent with Tier 0+1 plus the project card implements an open Hearth item (for example a prediction-aware eviction policy) to the evidence policy at TPV ≤ 1.2× the Rust arm on that item class; K1 holds on the *rotated* suite | K1 fails on the rotated suite (Goodhart on earlier suites) → freeze features and rerun the Surface Lab. No Edition 1 until it passes |

---

## 11. Non-goals and top risks

**Non-goals for v1:**
- novel syntax, glyphs or a Python near-clone;
- a Python-embedded primary surface;
- projectional editors, or JSON-wrapped code as agent input or output;
- visual-generation primitives (R13);
- `async`, macros, trait objects, garbage collection, exceptions or full dependent types;
- Lean as the authoring layer;
- a verified compiler (translation validation instead);
- formal proofs of speed on out-of-order cores;
- µop-level byte superoptimisation as the main path;
- VLIW bundling;
- self-modifying code, INVD or CAS hot-patching;
- SPDK bypass by default;
- compiling weights into instructions;
- implicit spec-to-code regeneration;
- hit rate, IPC or raw pass@1 per kilotoken as objectives;
- the Forge promoting defaults or language changes;
- seeding synthetic repositories or relying on llms.txt as the cold-start strategy.

**Top risks:**

| Risk | Why it is real | Mitigation |
|---|---|---|
| Cold-start cost stays above Rust | Training-data gravity; the chess study showed large cost multiples for unfamiliar languages (G01) | Subset rule; Tier 0 always on; lifter; K1 kill with a designed fallback (evidence layer over a Rust subset) |
| Card bloat and context rot | Comprehensive docs gave +0.7 points; NoLiMa knee near 32k | Byte and token budgets in CI; leave-one-atom-out ablations; packs instead of files |
| Goodhart on the harness | Sealed suites leak through repeated tuning | Rotation each epoch; a permanent holdout; obfuscated control; independent task authors; F4 decay re-runs |
| Weak or gamed specs | Verina spec soundness ~52%; ImpossibleBench: GPT-5 cheated on 54% of conflicting tasks | Spec escrow, two-sided strength, vacuity witnesses, an abort option (cut GPT-5 to 9%, D2-E) |
| T1 incompleteness frustrates agents | Sound but incomplete; horizontal reductions are the hard case (R07) | Clear "unknown" diagnostics; fallback to `tested` grade, labelled; grow the audited rewrite list only through review |
| Trusted-core bugs | eBPF verifier bugs; Lean kernel bug, July 2026 | Small cores, chaos and mutation testing of checkers, Lean mirror, two independent oracles for semantics |
| Correlated agent failures across roles | Knight and Leveson; Goel et al. 2025 | Distinct model families per role; measured independence recorded in evidence |
| Windows performance parity | MSVC intrinsics reach ~70 GB/s single-thread Q4; the pool heuristics were tuned by measurement | Port one seam at a time with interleaved A/B; keep C where parity fails |
| Constitutional rejection by Hearth | INV-DEP and ADR-0001 | Option A (committed C11); the port stays useful as an oracle and harness even if rejected |
| Harness cost | ~1.5k attempts per arm for 5-point resolution [inference] | Screening with ~100 IRT items; full runs only for editions and K-criteria; local-model arms are free at the margin |
| Model drift makes the Surface Map stale | Priors change as Mithril code enters training corpora | Falsifier F4 re-runs per model generation; revert to the familiar form when safe |

---

## 12. What is new and what is borrowed

**Plausibly novel as a combination.** "Novel" here means that no dossier found prior art. Several dossiers ran with exhausted search budgets, so each claim is **unverified** against 2025-26 work.

1. **A subset-of-Rust surface governed by grade-indexed, per-construct false-friend measurement against bit-exact oracles.** This includes a content-addressed Surface Map with parse/print laws and decay falsifiers (D3-i). Familiar-syntax advice is prior art (G01); measuring it construct by construct against checker-invisible divergence is not, to our knowledge.
2. **A comprehension harness as the gating fitness function for language and toolchain decisions,** with pre-registered kill criteria, C11/Rust control arms and the checker-accepted-but-wrong rate as a first-class metric (D2-D). Evidence-based language design with humans is prior art and stayed marginal (D2-D).
3. **"Prove the space" applied to agent search.** A timing_only policy class is certified once against demonic hints, and schedules cannot change the op-DAG. Self-improvement then needs only performance evidence inside those spaces (D2-A; the revisit synthesis).
4. **Diagnostics whose fixes carry evidence obligations,** tied to one content-addressed evidence ledger whose policies are compiler-enforced (§5.3, §7.5; the PCC and Alive2 lineages are prior art for the parts).
5. **Unforgeable handover manifests** derived from the toolchain journal and ledger rather than narrated, fixing DGM's log-faking class (R01).
6. **The acid-test engine as host.** Hearth runs the local models that write Hearth, applying the language's own grammar and type masks to its logits as an opt-in sampler feature (R03, G01).
7. **Cross-device canonical numerics with exact-integer reordering licences** as a type-level contract (G03). This comes from the numerics lens and is included for completeness.

**Deliberately taken from prior art:**
- Rust syntax and semantics, including no contraction and RFC 2686 left unmerged (D3-i);
- Dafny/Verus `requires`/`ensures` with auto-active SMT (R03);
- Hazel/ChatLSP typed holes and context (R03);
- rustc JSON diagnostics with applicability levels, and SARIF (R04);
- the SWE-agent agent-computer interface: lint-gated edits and 100-line views (R03);
- Anthropic `str_replace` and Aider search/replace practice (R03);
- Unison content addressing and salsa queries (R09, S3);
- Exo schedules and Halide's meaning/schedule split, adding an IEEE-exact mode (R05);
- Koka/Effekt effect rows and Austral capabilities (R09);
- Hylo mutable value semantics and Swift's `Mutex` shape (G05);
- KLEE-FP structural FP matching, Alive2 and CryptOpt translation validation (R07);
- s2n-bignum's practice of growing the semantics table one instruction at a time (G02);
- CORE-MATH and LLVM libc correctly rounded functions (G04);
- llguidance/XGrammar masks and Mündler et al.'s type-constrained decoding (R03);
- Vercel's AGENTS.md index and SkillsBench sizing (G01);
- GEPA reflective evolution (R04);
- DGM/HGM archives, MAP-Elites and POET (R01, R02);
- the Lean Comparator gate (R07);
- EverParse-style format descriptions (revisit);
- Hearth's own governance: the invariants lane, hash-locked goldens, mutation testing and handover manifests (R11).

**What this proposal adds to design-inputs**, all from the agent lens:
- the subset rule as the operational form of "no false friends";
- `todo!` holes;
- `seals` as the spelling of G05's boundary;
- the keyword-versus-attribute rule;
- fix applicability with evidence obligations;
- the flat, non-recursive edit envelope for Claude;
- a project card counted separately from Tier 0;
- `next` actions in every response;
- a comprehension precondition for each port stage;
- the agent-interface level of the Forge.

Deviations are marked inline: the hole syntax (§3.1) and the 12 KB always-on total (§7.2).
