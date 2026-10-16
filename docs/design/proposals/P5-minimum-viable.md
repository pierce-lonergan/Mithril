# P5 — Minimum Viable Mithril (MVM)

*Design proposal, 2026-10-11. Lens: ship real value. The smallest coherent language and toolchain
that ports Hearth with measurable benefit in about 6–9 months of agent-heavy development, then
grows without rewrites. Tie-breaker: feasibility and time-to-evidence.*

**Conventions.** `[M]` = measured, `[S]` = simulated, both as reported in the cited dossier.
`[inference]` = my estimate, not a measurement. Dossier citations: R01–R13, G01–G05, and `RI §x` for
`docs/research/revisited-ideas.md`. **DEVIATION** marks a departure from `design-inputs.md`, with the
reason given. The `.mith` code is illustrative and has not been compiled.

---

## 0. Summary

- **What MVM is.** A Rust-shaped systems language (`.mith`) plus a checker-first compiler (`mithc`,
  written in Rust) that emits strict C11. It has five features beyond a "safe C with Rust syntax", and
  each one exists because Hearth needs it: (1) `kernel fn` meanings with per-ISA `schedule`s whose
  bit-identity to the scalar meaning is *validated*, not just tested, by a small trusted checker;
  (2) block-scaled `layout` types for quant formats; (3) `format` descriptions that generate Hearth's
  container parser with no `unsafe`; (4) a fixed set of effects and capabilities, including a
  `timing_only` policy kind and `deterministic` boundaries, so the expert store can be written without
  user-level `unsafe` and its policies can be searched safely; (5) one content-addressed evidence ledger
  that makes INV-HONEST and INV-LOSSLESS-DEFAULT mechanical.
- **What MVM is not.** No traits, user effect handlers, macros, GC, JIT, direct x86 emitter, GPU
  backend, Lean proofs, weight overlays or visual-generation features in v0. Each one is in the
  deferral register (§13) with the trigger that would bring it in.
- **Delivery.** Roughly 10 months to a complete Mithril-Hearth that exports `hearth.h` unchanged and
  passes the C tests, the golden suite and a new cross-binary hash corpus. Assurance and performance
  evidence starts arriving at month 4–5 from the kernel stage.
- **Kill early.** A 5-week falsification sprint (M0) runs three experiments: cold-agent writability
  against C11 and Rust control arms; a checker spike on Hearth's real AVX2/AVX-512 kernels with a
  numerics mutant pool; and a test of whether one meaning plus schedules can generate the kernel
  triplets at parity. The outcomes that kill the project are written down before the sprint starts (§10.1).
- **Fallback.** If agents cannot write `.mith` well enough, the checker, ledger and format generator
  survive as tools over C Hearth. The design is layered so that this outcome loses as little as possible.

---

## 1. Thesis and design principles

**Thesis.** Mithril is a small, Rust-shaped systems language for AI agents. A function's signature
(types, effects, capabilities, contract) is a sufficient summary of what it may do. Performance-critical
code is written once as an exact, executable *meaning*, and its optimised *realisations* are accepted
only when a small trusted checker validates them. Every claim about code (proof, test, measurement,
rejection) is a typed, content-addressed ledger record that is invalidated automatically when anything
it depends on changes. The minimum viable version is exactly the subset that ports Hearth with
evidence: its kernels become one meaning plus schedules with validated scalar = AVX2 = AVX-512 identity;
its parser becomes a format description; its store needs no user `unsafe`, and agents can search its
policies without being able to change logits. It emits C11 with no runtime, so Hearth can keep shipping
C. Mithril's claim to being "AI-first" rests on measured levers (familiar syntax, typed holes, grouped
structured diagnostics, anchored edits, compact in-context docs, checkers in the loop), not on novel
notation (R03, R04, G01).

**Principles.**

1. **Justify or defer.** A feature ships in v0 only if a Hearth requirement or a measured agent benefit
   justifies it. Everything else goes in the deferral register with a concrete trigger.
2. **Familiar where meaning matches, loud where it differs.** Any `.mith` construct that looks like Rust
   means what it means in Rust. New meaning gets a new keyword or a loudly named function. Mithril is a
   restriction of Rust semantics plus new keywords, never a reinterpretation. False friends are the
   costliest case: one rule change took GPT-4 from 82.5% to 40.5% (G01).
3. **Prove the space, not the candidate.** Make whole classes of change unable to alter outputs
   (`timing_only` policies, DAG-preserving schedules), certify the class once, then search it with
   performance evidence only (RI §6; six independent branches converged on this).
4. **Checkers decide correctness, measurements decide utility.** No test-only acceptance on the logits
   path. A checker that times out or returns "unknown" counts as a rejection (R07, RI §5).
5. **Exact by default.** Canonical IEEE order is part of the semantics: no contraction, named reduction
   trees, RNE, canonical NaN at kernel outputs. Integer arithmetic may be reordered only under a proved
   range bound.
6. **Reserve the lattice, defer the checker.** Grades and tiers that are not implemented yet
   (`real(bound)`, `device(target)`, `proof`, the VRAM tier) exist in the type syntax and the ledger
   schema from day one but cannot be produced yet. Adding the checker later then needs no language change.
7. **Text is the interface; hashes are the identity.** Source of truth is canonical-formatted text in
   git. Definition hashes are computed, never stored as the codebase, and they key caches, ledger
   records, edit anchors and Forge deduplication.
8. **Small trusted core.** Search, compiler optimisations, agents and the C compiler (for kernels) are
   untrusted. The trusted base is the checker, the semantics table, the audited stdlib layer and the
   evaluator, and each is budgeted in lines and attacked on purpose (RI §5: eBPF verifier bugs; Hearth
   golden-gate bypasses).
9. **Ship through seams.** Port strangler-fig style behind Hearth's `hx_*.h` seams, with Hearth's own
   tests as the oracle at every step, and keep a frozen `hearth-c-ref` binary as a permanent
   differential oracle (R11).

---

## 2. Layered architecture

```
+------------------------------------------------------------------------------------------+
| L7 AGENTS & HUMANS     frontier API models + Hearth-hosted local models. Roles: Author,  |
|                        Builder, Prover, Adversary, Gatekeeper (manifest-enforced write    |
|                        scopes). Owner = ADR / promotion gate.                             |
+---------------- canonical text (.mith) + JSON envelopes over CLI / MCP (LSP later) ------+
| L6 AGENT PROTOCOL      outline show hole search edit check prove test mutate bench        |
|                        explain why handover guide.  Tier-0 card (<= 8 KB) in AGENTS.md    |
+------------------------------------------------------------------------------------------+
| L5 CODEBASE            plain .mith files in git; mith.toml (grants, owners, sealed specs, |
|                        profiles); mith.lock = hashes of sealed items; definition hash =   |
|                        normalised AST + interface hashes of dependencies                  |
+------------------------------------------------------------------------------------------+
| L4 COMPILER            Rust; salsa query DB keyed by definition hash; daemon `mithc serve`|
|   (untrusted)          parse -> CST -> HIR (types, effects, ownership, layouts, obligations)|
|                        -> KIR (kernel meaning + schedules + correspondence maps)          |
|                        -> MIR (SSA, explicit moves, capabilities as params) -> LIR (ISA ops)|
+------------------------------------------------------------------------------------------+
| L3 EVIDENCE            mithcheck: T1 FP-DAG matcher + exact-rewrite list; T2 range/SMT     |
|   (trusted core)       replay; x86 semantics table (XED-keyed, Zen 5 fuzzed). Ledger:      |
|                        evidence lattice, tombstones, auto-invalidation. Profile gate:      |
|                        lossless default, evidence minimums -> link errors                 |
+------------------------------------------------------------------------------------------+
| L2 BACKENDS            C11 emitter (strict FP, intrinsics) + object audit (disassemble ->  |
|                        LIR -> T1). Later, by trigger: PTX expert tier, direct x86, JIT     |
+------------------------------------------------------------------------------------------+
| L1 RUNTIME & STDLIB    no GC, no unwinding; audited unsafe layer (Mutex, Condvar, Arena/  |
|                        SlabBuf, Frozen, File.read_at, persistent pool, ISA dispatch);     |
|                        deterministic boundaries; tiers NVMe->DRAM (VRAM modelled only)    |
+------------------------------------------------------------------------------------------+
| L0 OS & HARDWARE       Win32 OVERLAPPED+NO_BUFFERING / POSIX O_DIRECT, threads, large      |
|                        pages; Zen 5 AVX-512, DDR5 ~77 GB/s [M], 990 PRO ~7 GB/s [M],        |
|                        RTX 5070 12 GB (present, unused in v0; G03)                          |
+------------------------------------------------------------------------------------------+
  Cross-cutting: THE FORGE = proposer agents (L7) + mithc (L4) + mithcheck & ledger (L3)
                 + sandboxed evaluator with a runtime-owned clock (L1). Consumer: Hearth.
```

| Layer | Responsibility | v0 size target [inference] |
|---|---|---|
| L7 Agents | Propose code, specs, schedules and policies. Never trusted for correctness. | — |
| L6 Protocol | Gives agents typed, low-latency, anchor-based access. Same verbs on CLI, MCP and (later) LSP. | 2–4k lines of Rust |
| L5 Codebase | Holds the source, ownership and sealed items. Git stays the transport and the history. | — |
| L4 Compiler | Checks and lowers code. Generates proof obligations. Incremental. | 35–50k lines of Rust |
| L3 Evidence | Accepts or rejects realisations, records every claim, gates release profiles. | checker ≤ 4k lines + table 1.5–3k (G02) + ledger 2–3k |
| L2 Backends | C11 for everything. Object audit for kernels. | in L4 |
| L1 Runtime | The few hundred lines per OS of audited `unsafe` (G05), the pool, dispatch. | 5–8k lines of `.mith` |
| L0 | Given. | — |

---

## 3. The language core

### 3.1 Surface policy

- **Rust-shaped, Rust-meaning subset.** Braces, `fn`, `let` / `let mut`, `struct`, `enum`, `match`,
  inherent `impl` blocks, `mod` / `use`, `for i in 0..n`, `Result` with `?`, `#[attributes]`, `as`
  casts with Rust semantics (float→int saturates, NaN→0). A program that would compile as Rust means the
  same thing as Rust. A Rust program Mithril cannot express is a compile error that names the rule, never
  a silent change of meaning.
- **New keywords, each one loud:** `uses` (effect clause), `kernel` (fn modifier: body is the canonical
  meaning), `schedule`, `spec`, `requires` / `ensures` / `invariant`, `layout`, `format`, `policy`,
  `core`, `deterministic`, `linear`, `comptime`, `export abi`. Typed holes are written `?name`.
- **One normative Lark grammar** within OpenAI's CFG-tool limits (explicit whitespace terminals,
  keyword-first productions). The hand-written parser is conformance-tested against it on the corpus.
  `mithc fmt` is canonical and enforced (R03, G01).
- **Integer overflow traps** unless it is proved absent. That is Rust's debug meaning, so stricter than
  release Rust but never different on correct programs. `wrapping_*` is explicit. The prover removes the
  checks it can discharge, which matters in memory-bound kernels (R11 risk: bounds-check cost).
- **The false-friends table ships in the Tier-0 card.** Each entry has a stable lint id, for example:
  `f32::max` keeps Rust's NaN-ignoring meaning, and x86 MAXPS operand order is `fmax_sse(a, b)`;
  `round()` is half-away-from-zero, while Hearth's quantiser needs `round_ties_even()`;
  `Iterator::max_by` returns the *last* maximum, while Hearth's top-k ties go to the *lower* index
  (`topk_ties_lower`); float `.sum()` is a sequential left fold, not `canon::sum16`. These are the
  concrete Hearth false friends that RI §D3-i identified.

### 3.2 Snippets

**(a) A quant layout type.** The layout is the specification. Accessors, pack and unpack, size checks
and the round-trip property are derived from it.

```mith
// Hearth Q4: 64 elements in 34 bytes = 4.25 bpw (FORMAT.md §6).
layout BlockQ4: block_scaled<64> {
    scale d: f16 at 0,                              // little-endian
    elems q: i4 at 2 as offset_binary(8),           // stored nibble = q + 8, q in -8..=7
    pack nibbles { lo(byte j) = elem j, hi(byte j) = elem j + 32 },
    value(i) = d.to_f32() * (q(i) as f32),
}
const _: () = assert!(size_of::<BlockQ4>() == 34);

layout BlockMXFP4: block_scaled<32> {               // OCP MX: shared E8M0 scale, E2M1 elements
    scale e: e8m0 at 0,
    elems q: e2m1 at 1,                             // nibble order: per source checkpoint
}   // derived: 2*q is an exact i8 in {0,±1,±2,±3,±4,±6,±8,±12} -> integer dot path (proved by enumeration)
```

**(b) A Hearth Q4 matvec as meaning plus schedules under exact numerics.** The body is NUMERICS §3
transcribed. Schedules may only change where and when operations run. The float DAG of each output row
must stay identical, and the integer part may be rewritten only under T2 obligations.

```mith
struct ActQ8 { d: f32, sum: i32, #[range(-127..=127)] q: [i8; 64] }       // 72 bytes
invariant ActQ8 { sum == q.iter().map(|v| *v as i32).sum::<i32>() }

#[numerics(exact)]                       // canon.v1: no contraction, RNE, canonical NaN on store
kernel fn matvec_q4(w: &[BlockQ4], x: &[ActQ8], y: &mut [f32])
    requires w.len() == y.len() * x.len()
{
    let nb = x.len();
    for r in 0..y.len() {
        let mut acc = 0.0f32;
        for g in 0..nb {
            let (b, a) = (&w[r * nb + g], &x[g]);
            // order-free: T2 proves |isum| <= 64*8*127 < 2^31, so any summation order is equal
            let isum: i32 = (0..64).map(|i| b.q(i) as i32 * a.q[i] as i32).sum();
            acc = acc + (isum as f32) * (b.d.to_f32() * a.d);     // fixed float order per row
        }
        y[r] = canon_nan(acc);
    }
}

schedule matvec_q4 for x86.avx512_vnni {
    split r by 16 into (rt, lane); vectorize lane;    // lane i = row 16*rt+i; per-row DAG unchanged
    rewrite isum = vpdpbusd_sum(b.stored_nibbles, a.q) - 8 * a.sum;  // T2: integer identity + ranges
    parallel rt dynamic;                              // disjoint rows of y: value-deterministic
    prefetch w ahead(2 tiles);                        // timing only, no semantic effect
}
schedule matvec_q4 for x86.avx2 {
    split r by 8 into (rt, lane); vectorize lane;
    rewrite isum = maddubs_madd_sum(b.stored_nibbles, a.q) - 8 * a.sum;  // int16 bound 3,810 (R07)
    parallel rt dynamic;
}
schedule matvec_q4 for portable { parallel r dynamic; }    // scalar; also the arm64 CI path
```

These three schedules stand in for the role of today's `mm_q4_scalar`, `quant_avx2.c` and
`quant_avx512.c` Q4 paths (the two SIMD files total 726 lines, which also cover Q8, F16/BF16 and
activation quantisation). `mithc prove matvec_q4 --target x86.avx512_vnni` writes a ledger record of
grade `validated` holding the T1 witness and the T2 obligations. The object audit then re-runs T1 on the
disassembled MSVC and Clang output (§4).

**(c) A spec with owner, contract, fault model and evidence requirement.**

```mith
spec act_quantize_q8 owner role::author sealed {      // NUMERICS §2; hash-locked in mith.lock
    fn act_quantize_q8(x: &[f32], out: &mut [ActQ8])
        requires x.len() % 64 == 0 && out.len() == x.len() / 64
        ensures  forall g in 0..out.len(): out[g] satisfies ActQ8   // ranges + sum invariant
        refines  canon::act_q8;                    // bit-exact to the scalar meaning (T1)
    fault_model numerics_v1;   // FMA contraction, lane/tree change, RNE->trunc, 127->128, dropped scale, NaN
    require evidence(logits_path) >= validated, mutant_kill >= 1.0;
}
```
```
$ mithc why act_quantize_q8
spec  act_quantize_q8@9c1e..  sealed role::author (ADR ref)   strength: kill 1.00, unknown 0.00 (pool numerics_v1)
impl  .avx512@51f0..  validated  T1+T2 cert lg:7e2a..  object-audit: clang ok, msvc ok   numerics: canon.v1
impl  .avx2@0b93..    validated  ...
perf  measured(hw=fp:9950x/ddr5/..): median, 95% CI, baseline=hearth-c-ref@<tag>   (no unlabelled numbers)
```

**(d) Direct I/O with capabilities, a linear lease, and a determinism boundary.**

```mith
linear struct Lease { slot: SlotId, gen: u32 }      // must be released; dropping it is a compile error

pub fn read_slab(f: &File<Direct>, at: Offset<4096>, buf: &mut SlabBuf<4096>) -> Result<(), IoError>
    uses io
{
    f.read_at(at, buf)    // audited stdlib: OVERLAPPED + wait on Win32, pread/EINTR loop on POSIX
}

// Reads shared mutable state, but the returned bytes are a pure function of the immutable,
// content-hashed file. The boundary must name the evidence that licenses it (G05).
deterministic(by = golden::scheduling_independence, value = content_hash(slab))
pub fn acquire(s: &Store, k: ExpertKey) -> Result<Lease, IoError>
    uses io, nondet        // visible inside; callers see `uses blob`
{ ... }

pub fn hearth_open(path: &str, opts: &Options, root: Root) -> Result<Engine, Error>
    uses io, spawn, alloc
{
    let fs = root.fs(); let sp = root.spawner();    // capabilities originate at the export boundary
    ...
}
```

**(e) A cache policy under `timing_only`, plus the core it plugs into.**

```mith
#[decision(ADR-0004)] const HEAT_DECAY: f32 = 0.995;   // drift lint if code and ADR disagree

policy HeatEvict: timing_only {
    state { heat: [f32; MAX_EXPERTS] }      // fixed size; no heap, clock, I/O or FP-environment access
    fn on_use(&mut self, k: ExpertKey) { self.heat[k] = self.heat[k] + 1.0; }
    fn on_token(&mut self) { for h in self.heat.iter_mut() { *h = *h * HEAT_DECAY; } }
    fn victim(&self, c: &[Cand], p: &RoutePred) -> Hint<Victim> {
        Hint::of(c.min_by_key_ties_lower(|x| self.heat[x.key] + 4.0 * p.prob(x.key)))
        // c[0].bytes()         -> E0731 slab payload is opaque in timing_only
        // fp_env::set_ftz(true) -> E0732 effect fp_env not permitted in timing_only
    }
}

core ExpertStore {
    hint port evict: HeatEvict fallback Lru validate evictable(slot) budget fuel(4 * n_slots) off_lock;
    hint port prefetch: NextLayer budget bytes_per_token(cap) reserve demand_readers >= 1;
    theorem noninterference: forall hints, io_order: logits(..) in { logits_with(Lru, io0), Err }
        evidence model_check(bound = 6) + chaos_suite(golden = maintainer) + mutation_kill(1.0);
}
```

**(f) A format description.** It generates a total parser and writer for the `.hearth` container.

```mith
format HearthFile: le {                              // FORMAT.md v1 §2
    preamble at 0: {
        magic: u32 == 0x48545248, version: u32 == 1,
        meta_off: u64, meta_bytes: u64, tdir_off: u64, n_tensors: u64,
        edir_off: u64, n_expert_entries: u64, align: u32 == 4096, reserved: u32 == 0,
    },
    experts at preamble.edir_off: [ExpertEntry; preamble.n_expert_entries],
    constraint disjoint(preamble, meta, tdir, experts, dense_region, slabs),
}
format ExpertEntry: le { offset: u64 where % 4096 == 0, nbytes: u64 where % 4096 == 0,
                         dtype: DType, flags: u32, reserved: u64 == 0 }
// generated: parse(&[u8]) -> Result<HearthFile, FormatError> uses nothing; no unsafe; totality proved
```

### 3.3 Types

- **Scalars:** `i8..i64`, `u8..u64`, `isize` / `usize`, `bool`, `f16`, `bf16`, `f32`, `f64`. Sub-byte
  and microscaling codes (`i4`, `e2m1`, `e8m0`, ...) are **layout element codes only**, not arithmetic
  types. Real kernels lower them through int8 dot products or lookup tables, not bare primitives (R09,
  R10 C6).
- **Aggregates:** structs with `#[repr(C)]` / `#[packed]` layout control and static size asserts; enums
  (tagged unions); tuples; fixed arrays `[T; N]`; slices `&[T]` / `&mut [T]`.
- **Refinements, the minimal form:** `#[range(lo..=hi)]` on integer fields and parameters,
  `invariant` blocks on structs, and `requires` / `ensures` on functions. All of them are discharged
  by T2 (SMT) or become checked traps. This is the Flux-style "integer side conditions at source level"
  R07 recommends, cut down to what Hearth's kernels and parser use.
- **SIMD:** portable `Vec<T, N>` and `Mask<N>` with lane-wise Rust-like operations, plus an
  `x86::` intrinsic namespace generated from the semantics table. Only table-covered instructions exist,
  so an intrinsic with no validated semantics cannot be written (G02).
- **Generics:** type and `comptime` value parameters, monomorphised. Bounds come only from built-in
  kinds: `Copy`, `Send`, `Sync`, `Linear`. **No user traits in v0** (deferral D-1).
- **Provenance-typed quantities:** `Quantity<Unit, Origin>` where `Origin ∈ {Measured{hw}, Simulated{model},
  Predicted}`. `mithc bench` and the doc tooling refuse to format an unlabelled number. This is INV-HONEST
  as a type, and it makes Hearth's "/tok vs *tok" unit-bug class a compile error (RI §4).

### 3.4 Effects and capabilities

- **A fixed built-in effect set** in v0: `io`, `spawn`, `alloc`, `time`, `nondet`,
  `nondet(platform)`, `blob` (value-deterministic read of immutable, content-hashed bytes), `fp_env`
  (reads or writes MXCSR / rounding / FTZ-DAZ), `foreign`, `unsafe`, `lossy`. Rows are inferred for
  private functions and **mandatory on `pub`**, which keeps the signature a summary. Errors use
  `Result` and `?`, as in Rust. `panic` aborts and never unwinds across the ABI (R11 P0).
- **Capabilities are values.** `io`, `spawn` and `time` require a capability value in scope (`Fs`,
  `File<Mode>`, `Spawner`, `Clock`). They originate at `export` entry points from a `Root` and flow
  explicitly. This is a fixed-set version of effects-as-capabilities (Effekt, Austral; R09). Grants of
  `unsafe` and `foreign` are per package, in `mith.toml` (ponyc `--safe` precedent; G05).
- **Policy kinds.** `timing_only` is a confinement discipline checked per policy in milliseconds:
  payloads are opaque, there is no ambient authority (including no FP-environment access), state is a
  fixed block, loops have static fuel, and outputs exist only as `Hint<T>` values that the core
  validates (RI §D2-A).
- **`deterministic` boundaries** turn an internal `nondet` into an external `blob` (or into nothing). A
  boundary must name its evidence: a golden test, a proof or a model check. That evidence goes into the
  ledger, and the boundary loses its licence if the evidence is invalidated (G05).
- **No user-defined effects or handlers in v0** (DEVIATION, minor: design-inputs allow
  tail-resumptive / one-shot handlers. I defer them, because no Hearth requirement needs them. Trigger
  D-2.)

### 3.5 Memory model

The memory model is the G05 decision, taken whole. Mutable value semantics with Rust move semantics
(no implicit deep copies; `.clone()` is explicit). **Second-class references:** `&T` and `&mut T` may
be parameters and locals but may not be stored in structs or returned, which removes lifetime
annotations. This is a strict restriction of Rust meaning, so it is not a false friend. **Linear types**
(`linear struct`) must be consumed. `Send` and `Sync` are derived kinds with Rust's meaning, and only
the audited stdlib may assert them (DEVIATION, naming only: G05 calls them transfer and share. Rust's
names are reused because the meaning is the same, following principle 2.) The audited `unsafe` stdlib
layer provides `Mutex<T>` with a scoped `with_lock(|s: &mut T| ...)`, `Condvar`, `Arena` →
`SlabBuf<4096>` chunks, `Frozen<T>` with `into_unique`, `File::read_at`, scoped threads and services,
the persistent pool and ISA dispatch. Raw pointers exist only inside granted packages. Regions, cowns,
BoC and epoch reclamation are excluded (G05). A test build swaps the stdlib scheduler for a loom-style
permutation scheduler, because Hearth's real concurrency risk is liveness in safe code (G05: Qin et
al.).

### 3.6 Numerics

- **Default `#[numerics(exact)]` = `canon.v1`.** IEEE binary32/64; no contraction (Rust never contracts
  either, so this is not a false friend); `mul_add` is the explicit FMA; RNE only; `fp_env` effect for
  anything touching MXCSR. Kernel stores canonicalise NaN to `0x7fc00000` (NUMERICS §3). Named orders are
  `canon::sum16` and `canon::dot16` (16 lanes, then an 8-4-2-1 tree), blocked exact-int32 sums, and
  rank-order combines. The pool asserts default MXCSR at worker start, which closes a live Hearth gap (G02).
- **Fidelity × determinism grade** on every value-producing function:
  `exact | real(bound) | approx(profile)` × `cross_device | device(target) | schedule_dependent`.
  In v0 only `exact×cross_device` and `approx×*` can be produced. `real(bound)` needs T3 certificates
  and `device(target)` needs a GPU backend. Both are reserved (principle 6). `approx` requires the
  `lossy` effect. A default profile that reaches `lossy` is a **link error**, which makes
  INV-LOSSLESS-DEFAULT mechanical.
- **Transcendentals are specified functions:** `cr::sin`, `cr::cos` (correctly rounded, scalar),
  `canon.v1::exp` (a versioned op-DAG, vectorisable, T1-checkable like `dot16`), and `sqrt`, which IEEE
  already rounds correctly. Platform libm is available only via `foreign` with `nondet(platform)`, which
  the exact profile rejects. A `parity::` shim exists for migration comparisons only (G04). Grounds:
  UCRT switches FMA3 and non-FMA3 paths at startup and the two differ on 44,232 sinf inputs [M]; a
  no-FMA canonical expf prototype was bit-identical across scalar, AVX2 and AVX-512 over all 2^32 inputs
  at 0.204 ns/element on AVX-512, against 1.12 ns for scalar UCRT [M] (G04).

### 3.7 Staging and specialisation

v0 has **`comptime`** (Zig-style same-language evaluation at build time, run by the reference
interpreter `mithi`), monomorphisation, and **schedules as data** attached to `kernel fn`s. ISA variants
are selected at load through an atomic-cached function table, as Hearth does today. `Code<T>` quotes and
binding-time types `@bind(load|call)` for load-time specialisation to a model file are **deferred**
(DEVIATION, deferral with triggers D-3 and D-4). Schedules plus `comptime` cover every generator Hearth
needs for the port. Load-time specialisation has to show its value first in a cheap C experiment that
folds a model's config into generated code (RI §S10 proposes exactly this go/no-go).

### 3.8 Modules and packages

One file is one module. A package is a directory with `mith.toml`:

```toml
[package]  name = "hearth-core"   edition = "2026"
[grants]   unsafe = ["std_platform"]   foreign = ["std_platform"]
[owners]   "kernels/meaning/**" = "role:author"   "kernels/schedule/**" = "role:builder"
           "spec/**" = "role:author"   "bench/harness/**" = "role:gatekeeper"
[sealed]   specs = ["spec/**"]   golden = ["tests/golden/**"]       # hashes recorded in mith.lock
[profiles.default]  fidelity = "exact"  allow_lossy = false
                    evidence_min = { kernels = "validated", logits_path = "tested", other = "tested" }
```

`export abi "hearth.h" { ... }` blocks generate the C header, a ctypes mirror and layout tests from one
source. ABI structs must carry a `struct_size` field. Appending fields is FREE; removing or reordering
them needs an ADR reference (contract variance lattice, RI §4). This would have caught Hearth's
`read_errors` break, where the C side wrote past the ctypes buffer. There is no registry in v0: path and
git dependencies only.

---

## 4. Compiler pipeline and IRs

```
.mith ─► CST (lossless; formatter + anchors) ─► HIR (resolved, typed, effects, ownership, layouts,
         obligations) ─┬─► KIR  kernel meaning: index loops + per-iteration FP/int op DAG, canonical
                       │        order explicit; schedules = KIR→KIR rewrites emitting correspondence maps
                       └─► MIR  SSA, explicit moves/drops, capabilities as params, effects erased
         KIR(scheduled) ─► LIR  instruction-level SSA over semantics-table ops (x86 iclass, portable)
         MIR + LIR ─► C11 (intrinsics; pinned flags: MSVC /fp:precise, GCC/Clang -ffp-contract=off,
                     no fast-math) ─► object (MSVC / Clang / GCC) ─► OBJECT AUDIT: XED decode of each
                     kernel symbol ─► LIR ─► T1 against the meaning
```

- **Query architecture.** A salsa-style database in Rust. Inputs are file texts. Derived queries are
  `items(file)`, `def_hash(item)`, `sig(item)`, `effects(item)`, `obligations(item)`,
  `kir(kernel, target)`, `cert(kernel, target)` (looked up in the ledger before computing) and
  `c_unit(module, target)`. A definition hash is the normalised AST (locals alpha-renamed, references
  replaced by their targets' interface hashes), so editing a body does not invalidate callers' type
  checks. `mithc serve` keeps the database warm for CLI, MCP and LSP. Target [inference]: < 300 ms
  re-check after a one-definition edit in a 30k-line package.
- **Why validate the output instead of each rewrite.** Exo checks every scheduling rewrite with effect
  analysis and models floats as reals (R05). MVM instead translation-validates the *result* (LIR against
  the meaning). The schedule supplies the correspondence map, so hand-written intrinsic code can be
  checked too, given a `#[lanes(...)]` correspondence annotation. That means the checker delivers value
  before the schedule language exists, and agents can transliterate `quant_avx512.c` into `.mith` and
  have it validated in M2.
- **Backend sequencing.** (1) C11 for all code (M1). (2) Object audit for kernels (M2). (3) Narrow PTX
  expert-tier backend, gated on the owner's GPU decision (M7). (4) Direct x86-64 emitter **only if
  triggered** (D-5). (5) Copy-and-patch JIT only if load-time specialisation proves out (D-4). LLVM is
  not planned.
- **DEVIATION (sequencing):** design-inputs put a direct x86 emitter second. MVM replaces it with the
  **object audit**, which runs T1 on the C compiler's actual machine code for the roughly 20 hot
  kernels. That gives the same assurance where it matters (no trust in MSVC or Clang for kernels) at a
  fraction of the cost, and C compilers already reach Hearth's measured throughput, because Hearth *is*
  hand-written C with intrinsics. If lifting fails (an unknown instruction), that variant's evidence
  drops to `tested`, and the release profile refuses to dispatch it.

---

## 5. Verification and evidence

### 5.1 Trusted core

| Component | Why trusted | Budget [inference] | Defence |
|---|---|---|---|
| `mithcheck` T1 matcher + exact-rewrite list (~20 rules) | Accepts kernels | ≤ 4k lines of Rust, separate crate, takes serialised certificates | Each rule proved by Z3 FPA (single-op identities) or exhaustive binary32 check; adversarial mutant suite; later Lean (D-7) |
| x86 semantics table | T1/T2 meaning of ISA ops | 25–40 families, 1.5–3k lines (G02) | Fuzzed on Zen 5 silicon (NaN payloads per operand, ±0, subnormals, every mask pattern); Bochs as second oracle; integer entries cross-checked against Hydride/VeGen/Alive2 |
| SMT solver(s) for T2 | Integer/BV obligations | external binaries | Admitted certificates re-checked by a second solver (Z3 + cvc5 or Bitwuzla) |
| Audited stdlib `unsafe` | Memory safety of the store and pool | a few hundred lines per OS (G05) | Human line review; ASan, TSan and loom-style permutation tests |
| Evaluator / bench harness (Gatekeeper code) | Utility claims | ~2k lines | Frozen, hashed, built by the bootstrap toolchain, process-isolated |

Not trusted: the parser, type checker, schedules, MIR lowering, the C compiler *for kernels* (object
audit), the Forge, and all agents. The C compiler *is* trusted for non-kernel code. That trust is
mitigated by differential testing against `mithi`, Hearth's C tests and the cross-binary hash corpus.

### 5.2 Checker tiers

- **T0 — types, effects, ownership, layout, `timing_only` confinement.** Compiler-checked. Soundness
  rests on tests and on the independent `mithi` interpreter, with a Lean model deferred.
- **T1 — FP-DAG matching.** For each point of the correspondence map, symbolically execute meaning
  and implementation, hash-cons the float DAGs and compare them modulo the audited exact rewrites
  (commutativity of a single IEEE add or mul under canonical-NaN output, exact `f16→f32`,
  lane permutation and broadcast identities, mask and select identities, `x + (-0.0)`). Loops use a
  lockstep rule: identical initial values plus a matching one-iteration DAG imply equality by induction.
  The output is a certificate that `mithcheck` replays in linear time. T1 is sound and incomplete, and a
  rejection is final for the profile. Precedent: KLEE-FP on 51 OpenCV SSE kernels (R07).
- **T2 — integer and bit-vector obligations.** Interval ranges (for example Q4 `maddubs` 3,810; the Q8
  sign trick 32,512 < 32,767; `|isum| ≤ 1,032,256 < 2^24`, R07), multilinear polynomial identity for
  reordered integer sums, QF_BV for mask and shift extraction (nibble = `elem(j)`), and Dafny-style
  `requires` / `ensures` over integers and indices. Agents do well with this style: vericoding success
  is Dafny 82% vs Lean 27% (R03).
- **T3 — tolerance certificates** (FPTaylor- or Satire-class, plus runtime margin checks at top-k).
  **Deferred** (D-6). In v0 an `approx` value can only carry `measured` quality evidence.
- **T4 — tests:** property tests, Hearth's C tests, goldens, differential tests against `mithi` and
  `hearth-c-ref`, AST-aware mutation on the diff (replacing `mutate.py`'s text-level operators), plus the
  `numerics_v1` fault model.
- **T5 — measurement:** runtime-owned clock, hardware fingerprint, interleaved A/B, anytime-valid
  e-values, roofline ceiling printed alongside the result (RI §4: statistical Gödel gate).

### 5.3 Evidence lattice and ledger

Lattice: `proof` (machine-checked in Lean; none in v0) > `validated` (T1/T2 certificates replayed by
`mithcheck`, or exhaustive checks such as all 2^32 inputs of a unary f32 function) > `tested` (with a
recorded mutation score) > `measured(hw)` > `assumed`. A claim's effective grade is the *meet* of its
evidence and its spec's strength (RI §D2-E).

Each **ledger record** holds `{key = H(code closure, spec hash, toolchain hash, target, hw fingerprint),
claim, grade, artifact (certificate / test log / samples), principal + role, time, verdict}`. Negative
results are **tombstones** with a scope, a contingency class (hardware, tooling, search, effort,
evaluation, ...) and machine-checkable resurrection triggers (R02). Any change to a key component
invalidates the record. Storage is append-only, content-addressed JSONL segments in the data directory
(the INV-DATA pattern), plus a committed index of admitted evidence for sealed specs, so CI and
successors can verify it without the raw samples. `mithc ledger query` and `mithc why` read it. The same
ledger is the Forge archive, the superoptimisation ledger, the specialisation cache and the handover
evidence. About ten revisit nodes reinvented this one substrate (RI §6).

### 5.4 Spec ownership

Roles (Author, Builder, Prover, Adversary, Gatekeeper) map to path scopes in `mith.toml`.
`mithc check --changeset <git range>` refuses a change set in which a Builder or Prover modifies a spec,
mutant pool, golden test or harness. Change sets are judged as content-addressed objects, which defeats
the symlink, case-twin and 8.3-name bypasses found against Hearth's golden gate (RI §D2-E). Sealed specs
are hash-locked in `mith.lock`. Amending one needs an ADR reference and re-hardening, and old evidence
keeps pointing at old hashes. Spec strength is two-sided: the kill rate on the sealed `numerics_v1`
pool, plus vacuity witnesses that must fail (zeros, passthrough, ignore-scale). Commit-reveal mutant
markets and measured role independence are deferred (D-12). In MVM, independence is approximated by
requiring different model families for Author and Builder on sealed specs.

---

## 6. Runtime and targets

- **CPU ISA tiers as data:** `x86.portable`, `x86.avx2` (+F16C; AVX-VNNI optional),
  `x86.avx512_vnni` (F/BW/VL/VNNI; BF16 optional), `arm64.portable` (macOS CI; NEON schedules deferred,
  D-13). Detection uses cpuid plus XCR0, with Darwin's lazy zmm handled. Vector width is a schedule
  choice, not "always zmm", because mobile Zen 5 has a 256-bit datapath and Intel client chips have no
  AVX-512 (R08). Under exactness the *reduction lane count* is part of the meaning (16 lanes map to one
  zmm, two ymm, or later a half-warp; G03).
- **Memory tiers:** `Tier::{Nvme, Dram, Vram}` in the store and placement model, with
  `resident<T, tier>` and `streamed<T, tier>` handles and demand versus prefetch priority. v0 implements
  NVMe→DRAM only. VRAM exists in the types and in the simulator profile (RTX 5070, 12 GiB) so that
  adding the GPU tier needs no language change (G03: "retrofitting placement is the expensive mistake").
- **Threads:** a persistent spin-then-sleep pool ported from `pool.c` (OpenMP's 5–10 µs per region was
  ruled out; ~0.75 µs per 16-thread round trip [M], R11). `pool.for_chunks(y, 16, |rows, ys| ...)` gives
  disjoint `&mut` chunks, so dynamic chunk claiming stays value-deterministic. Scoped services hold
  capabilities. No P/E-core paths (R08).
- **Determinism scopes.** Logits = f(`canon` version, model content root, inputs). The ISA, thread
  count, cache budget, policy, I/O mode and mirrors are all excluded by construction or by certified
  boundaries. Once specified transcendentals replace platform libm, cross-OS identity becomes checkable
  (proposed INV-DET-4, G04). `device(target)` is reserved for GPU-only orders. `schedule_dependent`
  values must sit behind a `deterministic` boundary or carry `nondet`.
- **Hot-swap:** v0 needs only the load-time ISA dispatch table. The store's token-boundary tick is
  where a future epoch commit (an atomic release-store of a version root, with `Frozen` refcounts for
  reclamation) will go. There is no self-modifying code, no INVD and no CMPXCHG16B (R08, R10).
  Typed weight overlays (R12) are deferred (D-10).

---

## 7. Agent protocol and toolchain

**Verbs.** Every verb is available as `mithc <verb> --json`, as an MCP tool from `mithc mcp`, and later
over LSP.

| Verb | Purpose | Evidence for the lever |
|---|---|---|
| `outline <module>` | Signatures only: types, effects, contracts, evidence grade. The signature is the summary, so callee bodies stay out of context. | Type definitions were the most valuable context in Hazel (R03) |
| `show <path::item>` | Canonical text plus definition hash (the anchor) | — |
| `hole ?name` | Expected type, bindings in scope, relevant definitions; a program with holes still checks and runs | Hazel/ChatLSP, the best-measured lever (R03, R04) |
| `search --type "fn(&[f32]) -> f32" --effects none` | Type-directed API search against the real stdlib, to stop hallucinated APIs | Field note 5 (draft thesis) |
| `edit` | Anchored, atomic edits gated by parse and type check | Lint-gated edit worth up to 7.7 points in SWE-agent (R03) |
| `check` | Grouped root-cause diagnostics: stable codes, spans, expected/actual, fix-its with applicability, false-friend rule ids; SARIF for CI | RustAssistant 4.97% → 44.76% with grouping (R03) |
| `prove <item> [--target]` | T1/T2; on failure, a minimal mismatch (lane, block, the two DAG fragments) | — |
| `test` / `mutate --diff` / `fuzz` | Property tests, AST-aware mutation of changed code, `numerics_v1` | Tests that prove nothing (field note 6) |
| `bench <item> --profile <machine>` | Runtime-owned clock, interleaved A/B, e-values, `Measured<>` output | INV-HONEST |
| `explain <kernel>` | Bytes per call by tier, roofline ceiling, achieved fraction, bottleneck class | R08 |
| `why <item>` | Ledger: evidence, tombstones, ADR references, owners | — |
| `handover` | Schema-valid session manifest: commands actually run, outcomes, evidence produced, open holes, new tombstones | Replaces Hearth's hand-written handovers (R11 GOV) |
| `guide <topic>` | Tier-1 docs on demand | — |

**The edit envelope** is non-recursive JSON, which Claude's structured outputs accept (R03):
`{"anchor":"store::evict::victim@3fa09c1e", "op":"replace_item"|"search_replace"|"insert_after",
"search":"...", "text":"..."}`. A stale hash returns `StaleAnchor` with the current text and hash. There
are no line numbers. `--gate=parse|types|prove` sets the acceptance bar, with `types` as the default.
Plain file edits remain legal, because text is the truth, and `mithc fmt` canonicalises.

**An example diagnostic:**

```json
{"code":"E0412","rule":"FF-07: f32 .sum() is a sequential left fold (Rust meaning), not canon::sum16",
 "item":"model::rmsnorm@3fa09c1e","span":{"file":"model/norm.mith","line":12,"col":14},
 "expected":"canon::sum16 (spec rmsnorm.meaning)","actual":"Iterator<f32>::sum",
 "root_cause":true,"folded":3,
 "fix":{"applicability":"machine","anchor":"model::rmsnorm@3fa09c1e",
        "search":"sq.iter().sum()","replace":"canon::sum16(&sq)"},
 "after_fix":["prove model::rmsnorm --target x86.avx512_vnni"]}
```

**Reference card.** Tier 0 (≤ 8 KB, always in `AGENTS.md`) carries a grammar summary (~1.5 KB), the
keyword list (~0.5 KB), the false-friends table (~1.5 KB), 10 snippets (~3 KB), the determinism rules
(~0.5 KB), the verb list (~0.5 KB) and a pointer to the error index. Tier 1 is `mithc guide`, 5–15k
tokens in 2–3 modules: the Lark grammar, stdlib signatures, 40–80 snippets and the error catalogue.
Tier 2 is the retrieved manual. Maintainers curate the card, because self-generated skills scored −8 to
−12 points while the 8 KB index lifted a pass rate from 53% to 100% (G01). The normative prose spec is
capped at about 30k words (R09).

**A standard loop** for an agent task: `outline` → `hole` / `show` → `edit` (type-gated) → `check` →
`test` / `mutate --diff` → `prove` → `bench` if performance is claimed → `handover`. The harness, not
the agent, runs anything that produces ledger evidence at `validated` or `measured` grade (DGM faked its
test logs; R01).

**Local models.** Hearth controls its own logits, so it can later host grammar- and type-constrained
decoding for local models. Type constraints cut compile errors by 52–75% (R03). This stays off by
default and is deferred to D-11.

---

## 8. The Forge (MVM scope) and its trust model

**Scope.** In v0 the Forge searches only spaces that are already proved:

1. **`timing_only` policies** (eviction, prefetch issue and depth, mirror choice) against a store core
   certified once against demonic hints. The obligations are O1 hint validation, O2 slab race freedom,
   O3 arrival-order confluence, O4 lossless tiers by per-slab content hash, and O5 liveness
   (`n_slots ≥ 2·top_k + n_io + 2`, I/O failure → `HX_E_IO`) (RI §D2-A). A candidate needs only to
   typecheck, plus performance evidence.
2. **Schedules for `exact` kernels:** prefill VNNI tiles, the attention value pass (an 18 GMAC/s
   portable pass against a 94 GMAC/s bit-identical AVX-512 prototype [M], R11) and repacked layouts. A
   candidate needs T1/T2 acceptance, plus performance evidence.

Out of v0: compiler-heuristic evolution, language and edition evolution, and any lossy search (which
needs T3 and quality gates).

**The loop.** Proposer agents are untrusted. They see diagnostics, profiles and their own lineage,
never the evaluator code, the held-out traces or reference outputs. Each candidate goes through:
`mithc check` (confinement) → deduplication by definition hash / canonical schedule form → `hearth.sim`
stage (labelled SIMULATED; 960k requests through five policies took about 2.6 s, R01) →
replay-conditioned lower-bound pruning with a PruneCert (simulated pilot: 16–41% pruned per cache size
[S]; physics-only bounds pruned 0 of 144, RI §D3-ii) → engine measurement → physics plausibility gate →
archive → human promotion. The archive is the ledger, organised as quality-diversity niches over cache
to working-set ratio × prefetch mode × model × storage profile. Selection is HGM-style clade sampling,
with a non-zero floor for revisits (R01, R02).

**Objectives.** Wall time per token and NVMe bytes per token, with demand-stall time as the
diagnostic. Hit rate is never the objective: depth-4 lookahead raised hits from 73% to 86% and cut
decode from 13.0 to 10.0 tok/s [M] (brief).

**Trust model.** The evaluator is frozen, hashed, built by the bootstrap toolchain (a candidate
compiler never builds its own evaluator), and runs in a separate process under a Windows Job Object
(no network, read-only goldens and traces, supervisor-held limits). The runtime owns the clock and
joins all threads and I/O before stopping it. Candidates have no clock or I/O by type. Evaluation mode
poisons fresh allocations. Physics gates quarantine any eviction-only policy that beats Belady, and any
prefetching policy that beats the NVMe-bytes / bandwidth floor. Changes to defaults need an ADR. This
is aimed at the documented hacks: DGM log faking and marker removal; CUDA-L1 timing exploits on 32.8%
of 250 kernels; o3 hacking 30.4% of RE-Bench runs (R01).

**Going further than DGM.** The difference is structural. DGM validates arbitrary agent code
empirically. The Forge searches only spaces where output equivalence holds by construction or by an
automatic checker. That leaves the *clock* as the only exploitable signal, and the runtime owns it.
Tombstones carry resurrection triggers and are re-scored when hardware, toolchain, model or numeric
mode change (R02). Counterfactual replay of selection policies is deferred.

---

## 9. The Hearth port

### 9.1 Stages and acceptance gates

These stages follow R11's plan with G05's risk ordering. Mithril emits the internal `hx_*` symbols, so
each stage replaces C objects inside `hearth_core` one module at a time.

| Stage | Scope (C lines) | Acceptance gate (all required) |
|---|---|---|
| S0 Freeze | Tag the base; build `hearth-c-ref`; generate the cross-binary hash corpus (SHA-256 of logits and routes for every `make_tiny` architecture × {F32, Q4} × ISA, `big_q4`, 512 real Qwen3 decode steps, quantiser bytes, matmul outputs across ISA / T / row splits / NaN-inf); record CRT identity | Corpus reproducible twice on the 9950X; owner signs it as golden-tier |
| S1 Leaf numerics | `quant.c`, `quant_avx2.c`, `quant_avx512.c` (1,408) | `test_quant` (117,681 checks) and golden ISA/batch identity; byte diff of quantiser output against C (closes the oracle hole); hash corpus equal; **`validated` T1/T2 + object audit for every dispatched variant**; single-thread AVX-512 Q4 ≥ 97% of C (C baseline 69.6 GB/s [M]) |
| S2 Container | `modelfile.c` (922) → `format` description | `test_modelfile` fuzz cases + golden malformed-file test; identical accept/reject and parsed configs against C on a generated corpus (≥ 10^6 files [inference]); zero `unsafe`; totality proved |
| S3 Pool | `pool.c` (732) | `test_pool`; interleaved A/B dispatch latency within noise of C (~0.75 µs at 16 threads [M]), including the WSL2 / crowded-pool scenarios |
| S4 Store + platform | `store.c` (1,030), platform (1,574) | `test_store`, `test_platform`, golden scheduling independence; ≥ 7 GB/s peak direct-I/O demand reads [M baseline 7.16]; chaos suite kills 100% of seeded core mutants; no user `unsafe` outside `std_platform`; TSan clean |
| S5 Forward | `model.c` (2,040) | Full golden suite through `check_golden.py --run`; hash corpus; 512-step real-model decode hashes; load-gated tok/s ≥ 97% of C at 2/4/8 GiB caches and for 512/2048-token prefill |
| S6 API | `api.c` + `hearth.h` (19 functions, 3 structs) | Generated `hearth.h` ABI-identical (plus `struct_size`, per the decision below); Python toolkit and ctypes mirror tests pass unchanged; C core retired, `hearth-c-ref` kept permanently |

**The pre-registered benefit claim for the port.** All B1 and B3 items must hold, and B2 must be
non-inferior.

- **B1 Assurance.**
  - Every dispatched kernel variant holds `validated` bit-identity evidence (today it is tested only).
  - INV-FMT/SAFE hold by construction for the parser.
  - At least 5 live defects are closed by a compile-time rule or a certified check: mirror full-content
    hash (O4), the `hx_store_heat` pointer race (it cannot be expressed with second-class references),
    ABI `struct_size`, the MXCSR assert, and the heat-decay drift via `#[decision]`.
  - On the `numerics_v1` mutant pool, T1+T2 kill at least as many mutants as golden plus contributor
    tests (G+C), and at least one class that the goldens (G) miss.
- **B2 Agent productivity.** On a sealed suite of Hearth tasks (bug fixes, a new kernel variant, a policy
  change, a format extension), Mithril-Hearth's verified pass@1 is ≥ C-Hearth's − 3 points and its cost
  per solved task is ≤ 1.2×, under the same harness.
- **B3 Performance.** Parity (≥ 97%) everywhere, plus at least one measured gain landed through
  certified search, for example the AVX-512 attention value pass or an NVMe-bound policy.

### 9.2 Constitutional decisions for Hearth's maintainers

1. **INV-DEP / ADR-0001.** Recommended option A: the engine *build artifact* stays C11 + OS APIs. The
   Mithril sources and the **checked-in generated C** both live in the repo, CMake builds without
   `mithc`, and CI verifies that pinned `mithc` regenerates the C byte for byte. Option B, `mithc` as a
   build dependency, is not recommended during the port. Either option trips Hearth's circuit breaker
   and needs a superseding ADR.
2. **ADR-0010, specified transcendentals, adopted in C Hearth before S0.** `cr` sinf/cosf (scalar), and
   expf as `canon.v1` or `cr`. Goldens are relational and need no re-lock; only the bit-exact C
   references change (G04). This removes the libm-identity risk from the port.
3. **The cross-binary hash corpus becomes maintainer-owned golden-tier** (INV-VERIFY extension).
4. **Normativity.** Through S6, NUMERICS.md and the C scalar code remain normative. After S6, the
   Mithril meaning modules become normative and NUMERICS.md is generated from them and checked.
5. **Resolve the heat-decay drift** (0.9 in `hx_model.h`, 0.995 in ADR-0004 and `hx_store.h`) before S4.
6. **ABI:** add `struct_size` to `hearth_options` and `hearth_stats`.
7. **Add an invariant that pool workers run with default MXCSR**, asserted at worker start.
8. **INV-DET-1 wording:** require mirror full-content hashing, or qualify the invariant. Add the device
   placement axis only when a GPU tier exists.
9. **GPU in scope?** Is `nvcuda.dll` an "OS API" under INV-DEP? Should the display move to the iGPU,
   freeing about 1.5 GB of VRAM? (G03.) Not needed until M7.
10. **INV-VERIFY extension:** `validated` evidence and spec roles are admissible evidence classes.
    Decide who may seal specs.

**Live Hearth defects to report, not fix:** the mirror check samples only the first page; the
`hx_store_heat` unguarded pointer (a data race); the `read_errors` ABI break; MXCSR never asserted;
heat decay 0.9 vs 0.995; storage channels in the server; with `n_io=1`, a demand read can wait behind
prefetch.

---

## 10. Roadmap

### 10.1 The first three experiments (M0, weeks 0–5, run in parallel)

**X1 — Cold-agent writability (weeks 0–3).**

- *Build:* the Lark grammar, a Tier-0 and Tier-1 card, and `mithi`, a tree-walking reference interpreter
  with a type checker for a Rust-shaped subset (~4–6k lines, which becomes M1's differential oracle).
- *Suite:* 30 sealed Hearth-shaped tasks with oracles that kill ≥ 95% of mutants: a bit-exact Q4 dot,
  activation quantisation, grouped top-k with lower-index ties, an LRU slot arena with pins and 4096-byte
  alignment, a `timing_only` eviction policy, a bounded container parser, a mutex-guarded queue, a
  rank-order combine, a canonical RMSNorm, f16 conversion. 10 tasks are for card iteration and 20 are
  held out.
- *Arms:* Mithril (card + `mithi`), C11 (Clang + the same oracles) and Rust. At least two frontier model
  families plus one local model; 8 checker calls per task; about 200 attempts per arm per epoch, which
  resolves a 15-point gap at p ≈ 0.5 (SE ≈ 3.5 points) [inference]; up to 3 card epochs.
- *Metrics:* verified pass@1, first-compile rate, tokens per solve, and the checker-accepted-but-wrong
  rate (RI §D2-D).
- *Pre-registered kill:* held-out VP@1 for Mithril < C11 − 15 points after 3 epochs, **or** a
  checker-accepted-but-wrong rate > C11's + 5 points. *On kill:* the language is dropped, and the
  checker, ledger and format generator continue as tools over C.
- *Note:* Mithril is handicapped here (no full diagnostics yet), so the measured gap is pessimistic.
- *Cost:* $2–5k API and ~25 owner hours [inference].

**X2 — Does the checker beat the tests? (weeks 0–5).**

- *Build:* a `mithcheck` spike covering T1 and T2, and semantics entries for every mnemonic in Hearth's
  Q4/Q8/F32/act-q8 kernels on AVX2 and AVX-512 (about 105 forms, 74 mnemonics, about 10 FP-sensitive;
  G02).
- *Input:* transliterate those kernels into an intrinsic-level IR with lane correspondence annotations.
- *Fuzz:* the FP-sensitive mnemonics on the 9950X, with NaN in each operand position, ±0, subnormals and
  conversion boundaries.
- *Mutants:* build the `numerics_v1` pool (FMA contraction, lane count and tree shape, RNE→trunc,
  127→128 clamp, dropped scale, tie flip, NaN canonicalisation, NEOX/GPT-J RoPE swap) on scratch C.
  Measure the kill rate under golden only (G), golden plus contributor tests (G+C), and T1.
- *Pass:* T1 accepts 100% of the real variants with ≤ 30 audited rewrite rules, each proved; it rejects
  100% of the FP-changing mutants; zero table/silicon mismatches.
- *Pre-registered kill:* by week 5, T1 still cannot accept the real kernels without per-kernel
  `assumed` axioms. The "validated bit-identity" benefit then dies, and the project continues only if
  X1 passed **and** X3 passed; otherwise it stops at tools over C.
- *Honest reporting:* if G+C already kills every mutant that T1 kills, the kernel benefit is recorded as
  "stronger evidence per build at lower cost", not "catches more bugs". RI §D2-E predicts the goldens
  miss some.
- *Cost:* $3–6k and ~40 owner hours, most of it reviewing the semantics entries [inference].

**X3 — Can one meaning plus schedules generate the triplets at parity? (weeks 1–4).**

- *Build:* a throwaway Python prototype of the schedule primitives, or Exo itself (MIT, emits C), that
  generates scalar, AVX2 and AVX-512 Q4 and Q8 matvec C from one meaning.
- *Run:* link it into a scratch Hearth through the `hx_kernels` table; run `test_quant` and
  `test_isa_identity`; measure single-thread L2-resident Q4 throughput and Qwen3-30B-A3B Q4 decode tok/s
  (interleaved A/B, load-gated, ≥ 10 runs per arm).
- *Pass:* bit-identical; ≥ 97% of the hand kernels on both measures (95% CI); schedule text ≤ 30% of
  the hand-written lines.
- *Pre-registered kill:* < 90% after two weeks of tuning, or bit-identity needs schedule primitives that
  do not preserve the DAG. Then "one generator replaces the triplets" leaves MVM, and kernels become
  explicit-SIMD `.mith` checked by T1.
- **Project-level kill:** X2 and X3 both fail. Mithril then adds nothing to kernels, and the remaining
  benefits (format, store, ledger) do not justify a new language.
- *Cost:* $1–3k and ~20 owner hours [inference].

**Owner decisions in parallel (D0):** the INV-DEP option, ADR-0010, and the S0 corpus. If the owner
rejects any Mithril-sourced core, the project is re-scoped to tools over C, recorded as a tombstone with
a resurrection trigger.

### 10.2 Milestones

All costs are [inference] at low-medium confidence: API spend for agent-heavy development, plus
owner-review hours. Agents run work streams in parallel. For example, the semantics table and fuzz
harness start in M0, and the format generator starts in M1.

| # | When | Deliverable | Gate (measurable) | Pre-registered kill criterion | Cost |
|---|---|---|---|---|---|
| **M0** Falsify | wk 0–5 | X1–X3 reports as ledger records; D0 decisions; S0 corpus | X1, X2, X3 pass thresholds (§10.1) | §10.1 outcomes | $6–14k, 85 h |
| **M1** Front end | mo 1–3 | `mithc` v0: parser + formatter, HIR checker (types, effects, ownership, layouts, ranges), MIR → C11, `export abi`, `check/hole/edit/outline/search --json`, MCP server, Tier-0/1 card, Mithril MultiPL-E (≥ 150 tasks), `mithi` differential tests; scalar S1 port | Scalar quant port passes `test_quant` via the seam; cold-agent VP@1 with full diagnostics ≥ X1's Mithril result + 5 points; re-check after a one-definition edit < 300 ms at 30k lines | Held-out VP@1 < C11 − 10 points with full diagnostics, **or** the compiler misses the month-3 gate by more than 6 weeks → stop the language, keep the tools | $10–25k, 140 h |
| **M2** Kernels | mo 3–4.5 | KIR, schedules, `mithcheck` T1/T2, Zen 5-fuzzed semantics table, object audit, `canon` library (`sum16`, `dot16`, `canon.v1::exp`, `cr::sin/cos`), `layout` types; S1 complete | S1 gates (§9.1); all `numerics_v1` FP mutants rejected; ≤ 30 rewrite rules | T1 certifies < 90% of dispatched kernel variants without `assumed` evidence → drop the validated-identity claim and re-justify the project | $8–20k, 100 h |
| **M3** Formats + ABI | mo 4–5.5 | `format` → total parser and writer; S2; contract variance lattice for ABI; ledger v1 with tombstones; `why`, `ledger query` | S2 gates; the `read_errors`-class ABI break (replayed from Hearth's history) rejected at compile time | Generated parser > 1.3× C parse time at open, or the accept/reject diff ≠ 0 after 3 weeks → keep the C parser and record a tombstone | $5–12k, 50 h |
| **M4** Concurrency | mo 5–7 | Audited stdlib per OS, `deterministic`, `timing_only` + hint ports, permutation-test scheduler; S3 + S4; store core certificate (O1–O5) | S3/S4 gates; `unsafe` ≤ 1,500 lines across OSes; chaos suite kill 1.0 | The store needs user-level `unsafe` outside `std_platform` in > 2 places, or dispatch latency > C + 10% that cannot be closed → re-examine the memory model (G05 assumption failed) | $10–25k, 130 h |
| **M5** Full port | mo 7–9 | S5 + S6: Mithril-Hearth exports `hearth.h`; Python toolkit unchanged | S5/S6 gates; B1 complete | tok/s regression > 3% that cannot be closed in 4 weeks, or any hash-corpus mismatch traced to the language semantics | $10–25k, 100 h |
| **M6** Benefit | mo 8–10 | Forge v0 campaigns (policies + kernel schedules); B2 maintainability A/B; benefit report under INV-HONEST | B3: ≥ 1 promoted checker-accepted candidate with ≥ 5% tok/s or ≥ 10% fewer NVMe bytes/token on a named configuration, e-value ≥ 20, zero output changes; B2 non-inferior | No candidate beats the incumbent beyond noise after 2 campaigns (≤ $10k) → Forge deprioritised; B2 shows Mithril-Hearth inferior → port stays an artifact and Hearth keeps C as primary | $10–30k, 90 h |
| **M7** Grow | mo 10–15 | Triggered items: PTX expert tier (if owner approves; canonical Q4/Q8 GEMV on sm_120), Lean mechanisation of the T1 rules and checker, `@bind(load)` specialisation, direct emitter, NEON schedules, LSP, editions | Per item. GPU: bit-identical to the CPU and ≥ 60% of llama.cpp MMVQ throughput on the same card [inference threshold; G03 says this single number decides it] | Per item, in the deferral register | open |

Total for M0–M6 [inference]: about $60–150k API and 650–750 owner hours over about 10 months
(15–18 h/week). For scale, one DGM SWE-bench run cost about $22k [M] (R01). The owner's review time is
the binding constraint, and it is concentrated in the trusted core (about 8–10k lines that need line
review) and the ADRs.

### 10.3 How MVM grows without rewrites

- The effect-row syntax is final, so user effects later only add names.
- LIR and the semantics table are the substrate for a future direct emitter. T1 certificates are
  replayable by a later Lean-verified checker. `real(bound)` and `device(target)` already type-check as
  unreachable grades. VRAM is already a tier.
- The ledger schema already has `proof`.
- `kernel fn` bodies serve as both meaning and spec, so a GPU schedule is just another
  `schedule ... for ptx.sm_120`.
- Editions and `mithc fix` handle surface changes additively. The syntax freezes after M1 (G01: every
  breaking change becomes stale-prior debt).

---

## 11. Non-goals and risks

### 11.1 Non-goals (v0)

- Visual generation primitives (R13).
- Training, weight overlays and "living models" (R12).
- A general application language (GC, async runtime, web).
- Traits, macros, inheritance, exceptions, multi-shot continuations.
- Lean as an authoring layer.
- µop-port superoptimisation or x86 byte-level search (R07, R10).
- A direct ELF emitter.
- SPDK or kernel bypass.
- Projectional editors or JSON-wrapped code as the agent's interface.
- Seeding synthetic repositories.
- Hit rate or IPC as an objective.
- Sound static error bounds for 4-bit networks.
- Lossy defaults of any kind.
- Self-hosting before the port is done (R09).
- Beating llama.cpp as a language claim. Speed gains are credited to placement and bytes, not to
  syntax (R06, R08).

### 11.2 Top risks

| # | Risk | Likelihood / impact | Mitigation |
|---|---|---|---|
| 1 | Cold start: agents write `.mith` badly | M / H | X1 kill gate; Rust-meaning subset; false-friend lints; Tier-0 card; `mithi` diagnostics; fallback to tools over C |
| 2 | Scope creep (second-system effect) | H / H | Deferral register with triggers; each milestone gate checks that no unregistered feature landed |
| 3 | T1 incompleteness (horizontal reductions, shuffles) | M / H | X2 spike on real kernels first; schedules supply correspondence maps; "unknown = reject" with an explicit fallback variant |
| 4 | An unsound trusted-core rule or table entry | L-M / H | Single-op rules proved by Z3 FPA or exhaustive check; Zen 5 fuzz plus Bochs; dual-solver T2; adversarial mutants; later Lean (D-7) |
| 5 | Windows performance parity (MSVC codegen, pool heuristics) | M / M | Emit intrinsics that mirror Hearth's; port `pool.c` heuristics verbatim; interleaved load-gated A/B at every stage |
| 6 | Hearth is a moving target (17 uncommitted files, open CI issues) | H / M | S0 freeze tag; port against `hearth-c-ref`; rebase window at each stage boundary |
| 7 | Owner bandwidth (one human) | H / H | Trusted core kept ≤ 10k lines; agents do the rest; review queue prioritised by evidence grade |
| 8 | Evaluator hacking in the Forge | M / M | Only checker-certified spaces are searched; runtime-owned clock; isolated process; physics gates; human promotion |
| 9 | Weak specs (LLM specs sound and complete about half the time, R03) | H / M | Specs sealed by the Author role; `numerics_v1` kill ≥ 1.0; vacuity witnesses; different model families for Author and Builder |
| 10 | libm identity breaks the parity oracle | M / H | ADR-0010 in C first (G04); `parity::` shim only as a fallback |
| 11 | Concurrency liveness bugs in safe code | M / M | Permutation scheduler, TSan, chaos suite (G05) |
| 12 | Goodhart on the cold-agent harness, or model drift | M / M | Sealed held-out set with rotation; ≥ 2 model families; C/Rust control arms in every epoch |

---

## 12. Novel versus prior art

**Plausibly novel in combination, to the dossiers' knowledge.** All claims are scoped; none is "first ever".

1. **IEEE-exact translation validation as a language's default acceptance rule for SIMD kernels,** with
   an owned, silicon-fuzzed AVX-512 FP semantics table and an object-code audit. The technique is
   KLEE-FP's (R07). Exo models floats as reals and trusts `@instr` templates (R05). No public source has
   bit-precise AVX-512 FP semantics (G02). What is new is making it the default numeric grade and the
   gate for agent search.
2. **`timing_only` policies plus a store core certified once against demonic hints,** so agent policy
   search needs only performance evidence: "prove the space, not the candidate" (RI §D2-A). Prior art:
   sched_ext / cache_ext fallback, Zdancewic & Myers.
3. **One content-addressed evidence ledger typed by a lattice and keyed by
   (closure, spec, toolchain, target, hardware),** carrying proofs, tests, measurements and scoped
   tombstones with resurrection triggers (RI §6; precedents in PCC, Unison, the DGM archive).
4. **Grades that become link errors:** fidelity × determinism scope with reserved-but-unreachable
   grades; INV-LOSSLESS-DEFAULT as a link error; INV-HONEST as `Quantity<Unit, Origin>` (RI §4, G03).
5. **A pre-registered cold-agent comprehension harness** with C11 and Rust control arms as the kill gate
   for a language (RI §D2-D).
6. **A Rust-meaning-subset surface with a machine-checked false-friend table** taken from a real
   engine's bit-exact traps (RI §D3-i, G01).

**Deliberately taken from prior art.**

- Rust syntax and move semantics.
- Hylo-style second-class references (R09, G05).
- Swift `Mutex` (SE-0433) and OxCaml capsule ideas (G05).
- Koka, Effekt and Austral effects-as-capabilities, in fixed-set form (R09).
- Halide's meaning/schedule split and Exo's schedule model, adding an IEEE-exact mode (R05).
- Dafny- and Verus-style `requires` / `ensures` with SMT (R03).
- Alive2 and CryptOpt translation validation (R07).
- EverParse-style format descriptions (RI §4).
- salsa queries and Unison-style content hashes used as keys (R09).
- rustc JSON diagnostics with applicability, and SARIF (R04).
- Hazel / ChatLSP typed holes (R03).
- loom-style schedule permutation (G05).
- DGM / HGM archives, MAP-Elites niches, anytime-valid e-values (R01, R02).
- CORE-MATH / LLVM libc correctly rounded functions, and StrictMath-style specified functions (G04).
- XED iclass keys (G02).
- Hearth's own governance: golden tests, mutation testing, INV-HONEST (R11).

---

## 13. Deferral register

Each item names the trigger that would bring it into scope.

| ID | Deferred item | Trigger to add |
|---|---|---|
| D-1 | User traits / interfaces | ≥ 3 port modules duplicate code that generics + `comptime` cannot share, **or** ≥ 10% of held-out cold-agent failures cite the missing abstraction |
| D-2 | User effects and one-shot handlers | A Hearth requirement that stdlib configuration cannot meet (e.g. a test-time I/O substitution beyond the permutation scheduler) |
| D-3 | `Code<T>` quotes | A required generator that cannot be expressed as meaning + schedule + `comptime` |
| D-4 | `@bind(load)` specialisation; copy-and-patch JIT | A C go/no-go experiment shows ≥ 10% decode or prefill gain from folding the model config [inference threshold]; JIT only if the AOT variant count exceeds what can be shipped |
| D-5 | Direct x86-64 emitter | The object audit finds C-compiler rewrites that cannot be pinned, **or** a ≥ 5% kernel gap attributable to C codegen |
| D-6 | T3 tolerance certificates / `real(bound)` | The first owner-approved non-exact path (MLA absorbed-form bound, a GPU tensor-core mode, opt-in lossy experts) |
| D-7 | Lean reference semantics and checker mechanisation (**DEVIATION:** design-inputs put the Lean executable semantics in v1; MVM uses the independent Rust `mithi` interpreter for differential testing) | T1 rule list and certificate format stable for 2 months, **or** any soundness bug found in T1 |
| D-8 | PTX expert tier (GPU) | Owner puts the GPU in scope, plus the INV-DEP ruling, plus the G03 GEMV experiment passing |
| D-9 | LSP | Humans start editing `.mith` regularly, **or** an A/B shows an LSP benefit for agents (open question in R04) |
| D-10 | Typed weight overlays / FORMAT v2 | Owner asks for adapters or expert edits (R12) |
| D-11 | Constrained decoding for local models | Local-model proposers join the Forge |
| D-12 | Commit-reveal mutant markets; measured role independence; Datalog fact plane | Specs authored at scale by agents, **or** > 20 custom lints |
| D-13 | NEON / SVE / AVX10.2 schedules | Owner priority for macOS performance, or hardware availability |
| D-14 | Card evolution (GEPA over the pack) | Cold-agent harness stable for 2 epochs after M5 |

**Deviations from design-inputs, consolidated.** These are D-7 (Lean deferred), §4 (object audit
replaces the early direct emitter), §3.4 (no user handlers in v0), §3.7 / D-3 / D-4 (quotes and binding
times deferred) and §3.5 (Rust names `Send` / `Sync`). Each one is a deferral or a renaming chosen for
time-to-evidence. None contradicts a settled finding, and each has a trigger that restores the original
plan.

---

## 14. Open questions

1. Does Zen 5 match the semantics table bit for bit on MAXPS / MINPS with NaN and ±0, on VCVTPS2DQ
   indefinite results, and on the denormal behaviour of the BF16 instructions? (G02. X2 answers it.)
2. With the full diagnostics in place, how much does the X1 gap shrink? And where is the optimal card
   size for a whole language, as opposed to an API delta?
3. Does the T1 lockstep rule cover attention's sequential-in-t accumulation, or does that path need the
   fixed-chunk redefinition that G03 proposes for GPU parity anyway?
4. Is checked-in generated C (INV-DEP option A) acceptable to the owner as satisfying the spirit of
   ADR-0001?
5. What gain do evolved prefetch policies actually deliver on NVMe-bound configurations, measured on the
   engine rather than the simulator? (RI §D2-A predicts a few points for eviction, more for prefetch
   timing.)
