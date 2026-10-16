# P4: The Living Forge

**Mithril as an evolving system: a language, toolchain and runtime built for sustained, safe self-improvement over years**

- Status: design proposal P4, phase 1 (architecture). Date: 2026-10-11.
- Lens: open-ended, safe self-improvement. Tie-breaker: *sustained safe improvement*. When two options are close, this proposal picks the one that keeps an unattended improvement loop running safely for years: a narrower certified space over broad unverified search, a reversible step over a fast one, a human signature over automation for anything normative.
- Inputs: `brief.md`, `design-inputs.md` (cited **[DI]**, authoritative), `draft-thesis.md`, the dossiers R01–R13 and G01–G05 (cited **[R01]** … **[G05]**), and the revisit archive (cited **[RV:node]**, e.g. **[RV:D2-A]**). Numbers keep the labels their sources give them: *measured* or *simulated*. My own estimates are marked **[inference]**. Wherever this proposal departs from a settled constraint in [DI], it says **DEVIATION** and gives the reason.

---

## 0. Summary

Mithril is a Rust-shaped language built on three ideas: meanings with checked realisations, one evidence ledger that records every judgment including rejections, and the Forge. The Forge is an improvement loop at three levels: (F1) programs and policies, (F2) the compiler, (F3) the language. It sits over a frozen trusted core (F0) that it cannot write.

Its leverage comes from types, not from cleverer search:

- certified spaces of output-preserving change;
- evaluator hacks made into type errors;
- tombstones that revive themselves through `mithc revisit`;
- stratified authority, so humans sign defaults, specs, evaluators and language changes.

---

## 1. Thesis and design principles

### 1.1 Thesis

A Mithril function's signature (types, effects, capabilities, contract and numeric grade) is a sufficient summary of everything it may do, so an agent never has to read a callee's body. Performance-critical code is written as a normative *meaning* plus separately checked *realisations*. Correctness is anchored to the meaning, and agents can search the realisations aggressively. All evidence is content-addressed and scoped to the code, spec, toolchain, target and hardware it was obtained on. That includes negative evidence. So the codebase accumulates knowledge monotonically, and stale knowledge invalidates itself.

These properties turn a Darwin-Gödel-style loop from a fragile research harness into a permanent part of the language:

- the type system certifies spaces of safe modification once;
- the runtime owns all measurement;
- the ledger is the archive;
- tombstones carry their own revival conditions;
- language changes are editions, judged by how well fresh agents use them and migrated without breaking the archive.

Mithril does not claim the loop improves without limit. It claims the loop can run for years without its judges being corrupted, without losing stepping stones, and without forgetting why things were rejected.

### 1.2 Principles

| # | Principle | Concrete consequence |
|---|---|---|
| P1 | **Signature sufficiency.** A signature bounds behaviour. | Effects and capabilities in every public signature; no ambient authority; `uses {…}` rows; contracts and grades in the type. |
| P2 | **Familiar where meaning matches, loud where it differs.** | Rust-shaped surface. Every semantic deviation gets a new keyword or a mandatory disambiguator (`argmin(…, ties: lower)`), never a reinterpreted familiar token [DI, G01, RV:D3-i]. |
| P3 | **Meaning is normative; realisations carry evidence.** | `meaning fn` plus `schedule`, `policy` and `layout` realisations, each with a refinement certificate or membership in a certified space. |
| P4 | **Exact by default; determinism speeds up search.** | Strict IEEE, named reduction orders, `cr`/`canon` transcendentals. Bit-identity makes float equivalence a DAG question and makes traces replayable for cheap, sound evaluation [R07, RV §6.8]. |
| P5 | **Prove the space, measure the candidate.** | Space certificates (§8.4) amortise correctness. Per-candidate cost is a millisecond re-check plus measurement. |
| P6 | **One ledger, including "no".** | Every judgment is a fact keyed by closure hash plus environment fingerprint, typed by the evidence lattice, invalidated automatically. Tombstones are facts too. |
| P7 | **Nothing is final; the graveyard is executable.** | Tombstones store exact reproduction recipes and triggers. Editions must migrate the archive as well as live code. |
| P8 | **Stratified trust.** | The judged never builds the judge. Checkers become stricter on their own, never laxer. Humans sign defaults, specs, evaluators and language changes. |
| P9 | **Physics-aware objectives with honest units.** | `Quantity<unit, origin>`. Objectives are bytes/token, stall time and verified pass rate, never hit rate or IPC [DI]. Beating a sound bound means quarantine. |
| P10 | **Monotone coordination.** | Agents add facts. Only non-monotone operations need a barrier, and only normative ones need a signature (CALM, [RV:D2-F]). |

---

## 2. Layered architecture

```
 ┌───────────────────────────────────────────────────────────────────────────────────────┐
 │ 9  AGENTS AND HUMANS   frontier API agents · Hearth-hosted local models · maintainers   │
 │        canonical .mith text, hash-anchored edits, queries, proof/bench requests, ADRs   │
 ├───────────────────────────────────────────────────────────────────────────────────────┤
 │ 8  AGENT PROTOCOL      mithc CLI (--json) · LSP · MCP · SARIF · guide/pack (Tier 0/1/2)│
 ├──────────────────────────────────────────┬────────────────────────────────────────────┤
 │ 7  CODEBASE STORE AND LEDGER             │ 6  THE FORGE (untrusted proposers)          │
 │  .mith text <-> content-addressed defs   │  slots · spaces · QD archive (hw x shape)   │
 │  Fact Plane (Datalog views)              │  HGM clade selection · cascade scheduler   │
 │  Evidence ledger: claims, certificates,  │  revisit engine (triggers) · promotion queue│
 │  measurements, TOMBSTONES                │  F1 artifacts · F2 toolchain · F3 language │
 │  editions · surface map · roles · grants │  reads 7, 5, 4; writes candidates and facts │
 ├──────────────────────────────────────────┴───────────── cannot write F0 ──────────────┤
 │ 5  COMPILER (Rust, salsa-style queries keyed by content hash)                          │
 │  CST -> Core (types, effects, grades) -> MIR (meaning, FP-DAG) -> SIR (scheduled)       │
 │  -> LIR (ISA SSA, XED-keyed) -> emit C11 | x86-64 kernels | PTX (later)                 │
 ├───────────────────────────────────────────────────────────────────────────────────────┤
 │ 4  VERIFICATION AND EVIDENCE   F0 TRUSTED CORE (frozen, hash-locked, human-owned):      │
 │  confinement re-checker · T1 FP-DAG matcher · T2 BV-SMT w/ certificates · T3 tolerance │
 │  ISA semantics table · Lean 4 reference semantics · measurement service · gate runner   │
 │  spec escrow · mutation engine · sandbox supervisor · ledger kernel                     │
 ├───────────────────────────────────────────────────────────────────────────────────────┤
 │ 3  RUNTIME (no GC, C ABI)  pool · tiered store (VRAM/DRAM/NVMe) · async I/O · dispatch  │
 │  tables · epoch hot-swap · weights+overlays · deterministic{} boundaries                │
 ├───────────────────────────────────────────────────────────────────────────────────────┤
 │ 2  TARGETS   x86-64-v3(+VNNI) · x86-64-v4 (AVX-512 VNNI/BF16/VBMI) · arm64 NEON ·       │
 │              PTX sm_120 expert tier (owner-gated) · OS: Win32 / POSIX                   │
 ├───────────────────────────────────────────────────────────────────────────────────────┤
 │ 1  HARDWARE  Zen 5 (16C, 2 CCDs, 512-bit) · DDR5 (~77 GB/s measured) · 990 PRO NVMe     │
 │              (~7 GB/s) · RTX 5070 12 GB (PCIe 5) · USB HDD                               │
 └───────────────────────────────────────────────────────────────────────────────────────┘
```

Trust by layer:

- **Untrusted:** agents (9), except their signed AUTHORITY facts; the protocol (8), which returns only ledger facts; the Forge (6), which runs isolated and holds no capability to F0; the compiler (5), except checks that F0 re-verifies.
- **The ledger (7):** its kernel (append, signature check, invalidation) is F0, and its content is data.
- **Verification (4):** all F0. Small, adversarially tested, changed only by humans.
- **The runtime (3):** safe Mithril over an audited Unsafe layer of a few hundred lines per OS [G05].
- **Targets (2):** data. The ISA semantics table is F0.
- **Hardware (1):** recorded as a fingerprint on every measurement.

---

## 3. The language core

### 3.1 Surface syntax policy

- **Standalone `.mith`, Rust-shaped**, with braces, `fn`, `let`, `struct`, `enum`, `match`, traits, generics and `Result`/`?`. Anything that looks like Rust means what it means in Rust [DI, G01]. It is not a Python clone. A Python API is provided only for schedule and search scripting [G01].
- **New concepts get new keywords:** `meaning`, `schedule`, `layout`, `policy`, `spec`, `uses`, `grade`, `deterministic`, `evolve`, `tombstone`. Divergent operations get mandatory disambiguators. Example: `topk(xs, k, ties: lower, nan: last)`. In `exact` code, the bare familiar forms whose meaning differs (`xs.iter().sum()` on floats, `max_by`) are **traps**: they do not compile, and the diagnostic is a `FalseFriend` error naming the rule broken [RV:D3-i].
- **One normative Lark grammar** that fits OpenAI's CFG-tool restrictions. Whitespace-insensitive, with a canonical formatter [R03]. The syntax freezes early and evolves only additively through editions, with `mithc fix` [G01].
- **Budget:** a normative prose core of at most 30k words, plus a machine-readable formal core [R09]. Tier 0 card ≤ 8 KB, always in context. Tier 1 ≤ 15k tokens [G01]. A construct that needs more than one snippet and one false-friend line to explain is a design smell [G01].

### 3.2 Illustrative snippets

**(a) Quant layouts as declarative block-scaled types.** Pack/unpack, round-trip obligations, value ranges and integer dot paths are all derived from the declaration.

```mith
layout Q4x64 = block_scaled {            // Hearth Q4, 4.25 bits/weight (hx_block_q4, 34 bytes)
    elems: 64,
    code: u4 offset 8,                   // stored q + 8; value range -8..=7
    pack: nibbles { lo: j, hi: j + 32 }, // NOT llama.cpp Q4_0 (32-elem blocks, hi at j+16): a distinct type
    scale: f16 first,
    size: 34,
}
layout Act8x64 = block_scaled { elems: 64, code: i8 range -127..=127, scale: f32 first, aux sum: i32, size: 72 }
layout Mxfp4   = block_scaled { elems: 32, code: e2m1, scale: e8m0 first, size: 17 }  // nibble order: per checkpoint
// derived: e2m1 * 2 fits i8, so Mxfp4 x Act8x64 gets an exact-integer dot path automatically
```

**(b) A Q4 matvec as meaning plus schedule under `exact`** (Hearth NUMERICS.md §3). The schedule may tile, parallelise and vectorise. It may not change the float DAG.

```mith
meaning fn matvec_q4<const R: usize, const C: usize>(w: &Tensor<Q4x64, [R, C]>, x: &Tensor<Act8x64, [C]>) -> [f32; R]
where C % 64 == 0
grade exact                                            // bit-identical on every target; scope cross_device
{
    par for r in 0..R -> out[r] {                      // each out[r] written by exactly one iteration: checked
        let mut acc: f32 = 0.0;
        for g in 0..C / 64 {                           // the float chain is sequential in g: part of the meaning
            let isum: i32 = sum_exact(i in 0..64) { w[r].blk(g).val(i) as i32 * x.blk(g).val(i) as i32 };
            acc = acc + (isum as f32) * (w[r].blk(g).scale() * x.blk(g).scale());   // no contraction, ever
        }
        canon_nan(acc)                                 // NaN stored as 0x7fc00000
    }
}

schedule matvec_q4_v4 for matvec_q4 on cpu(x86_64_v4 + avx512_vnni) {
    tile r by 16 -> (rt, ri);
    parallel rt over pool chunk dynamic;
    lower sum_exact with vpdpbusd via offset(8);       // Σ nibble·x − 8·Σx: the same exact integer (T2 obligation)
    vectorize ri width 16;                             // 16 rows' chains in one zmm; each chain keeps its order
    prefetch w.blk(g + 2);                             // timing only; no effect on values
}
```

The compiler derives |val·x| ≤ 8·127 per product and |isum| ≤ 64·8·127 = 65,024. That is below 2^31, which licenses integer reordering, and below 2^24, which makes `isum as f32` exact. Both are discharged as bit-vector obligations [R07]. Each float node in the scheduled IR keeps its MIR identity, so the T1 check is a renaming match.

**(c) A spec, owned separately, with an evidence policy.**

```mith
spec matvec_q4_spec for matvec_q4 by role::author {          // sealed after hardening; Builders cannot edit
    fault_model numerics_v1;   // FMA contraction, lane/tree change, ties flip, 127->128 clamp, dropped scale, NaN canon
    admits [matvec_q4_scalar, matvec_q4_v3, matvec_q4_v4];
    rejects witness [zeros, passthrough(x), ignore_scale];
    require strength >= 0.97, unknown <= 0.02, independence(author, adversary) == distinct_family;
}
evidence policy kernels {
    grade exact => correctness >= validated;                 // a T1/T2 witness; "tested" is not enough
    claim speed => Measured { hw: fingerprint, e_value >= 100, baseline: named };
    default     => fidelity == exact;                        // INV-LOSSLESS-DEFAULT as a link-time rule
}
```

**(d) A cache policy under `timing_only`.** It can change speed. It provably cannot change logits.

```mith
policy EvictPredLru<P: opaque> : timing_only {
    state { last: [u32; MAX_SLOTS], tick: u32 }              // fixed size: no heap, no clock, no FP-environment writes
    fn on_use(&mut self, c: &Cand<P>) { self.tick = self.tick.wrapping_add(1); self.last[c.slot] = self.tick; }
    fn victim<'call>(&self, cs: &'call [Cand<'call, P>], pred: &RoutePred) -> Hint<SlotIdx> {
        argmin(cs, |c| (pred.next_use_rank(c.key), self.last[c.slot]), ties: lower).hint()
    }
    // fp_env::set_ftz(true);   error E0712 FpEnvWrite: not permitted under timing_only
    // c.payload().len()        error E0420 OpaquePayload: P is opaque to policies
}
core ExpertStore<P> {
    hint port evict: EvictPolicy<P> fallback Lru validate evictable wrap robust(Lru, eps: 0.02)
        budget fuel(4 * n_slots) off_lock eject_after 16;
    hint port prefetch: PrefetchPolicy<P> budget bytes_per_token(cap) reserve demand_readers >= 1;
    theorem noninterference: forall h: HintStream, s: IoOrder. out(self, x, h, s) in { out(self, x, Lru, s0), Err }
        evidence model_check(bound: 6) + chaos_suite("adversarial/*") + mutation_kill(core_mutants, rate: 1.0);
    tier mirror(path): lossless by content_hash(slab);
}
```

**(e) Effectful direct I/O with capabilities and a `deterministic` boundary.**

```mith
pub fn read_slab(dev: &BlockDev, at: Offset<4096>, buf: inout SlabBuf<4096>) -> Result<(), IoError>
uses { Io, Fail }
{
    dev.read_at(at, buf)        // audited stdlib: overlapped + NO_BUFFERING on Windows; pread + O_DIRECT/F_NOCACHE on POSIX
}

fn main(root: Root) -> Result<(), Error>
uses { Io, Spawn, Alloc<Heap>, Nondet }
{
    let dev = root.fs().open_direct("model.hearth", ReadOnly)?;            // attenuated: one file, read-only
    let store = ExpertStore::spawn(dev, evict: EvictPredLru, readers: 4)?; // the service holds Spawn + Nondet
    deterministic(by: golden::scheduling_independence) {                    // Nondet inside, value-deterministic outside
        serve(&store)                                                       // the logits path sees only { Blob, Fail }
    }
}
```

**(f) A Forge slot and a tombstone** (Hearth's lookahead result, recorded as data).

```mith
evolve slot store.evict : EvictPolicy<P> in space timing_only {
    seed EvictLru;
    objective minimize (nvme_bytes_per_token, stall_per_token) per niche(hw, model, cache_ratio);
    bound by oracle::min_bytes(trace) prune phys audit 5%;        // only phys or audited-emp bounds may prune
    holdout traces::sealed("qwen3-30b-a3b/held/*", "kimi-shaped/held/*");
    promote profile by grant(store_policies);  promote default by authority(maintainers);
}
tombstone store.prefetch.lookahead4 {
    variant  h:…;                                                 // exact repro: source, toolchain, flags, seed
    verdict  slower { tok_s: 13.0 -> 10.0, hits: 73% -> 86%, Measured { hw: mp:9950x/990pro-x1 } };
    scope    model == qwen3_30b_a3b && storage == nvme(gen4, x1) && cache in 2.GiB..=4.GiB;
    class    H(storage_bw);  binding nvme_bytes;
    revisit_when hw.storage_bw >= 2.0 * scope.storage_bw || hw.has_tier(Vram)
              || model.shared_experts > 0 || incumbent(store.evict).wasted_prefetch_bytes <= 0.5 * at_burial;
}
```

### 3.3 Types

- **Scalars:** i8–i64, u8–u64, f32, f64. f16 and bf16 are storage types: arithmetic first converts explicitly to f32. Sub-byte codes (u4, i4, e2m1, e8m0) exist *only* inside `layout` declarations, so there is no bare int4 arithmetic and no popcount-style lowering trap [R05, R10].
- **Refinement and index types** for integer side conditions: `C % 64 == 0`, `Offset<4096>`, `ExpertId<N>`, `i8 range -127..=127`. They are discharged by SMT at compile time and erased [R07, RV:S11]. Overflow proofs on `sum_exact` accumulators are what license integer reordering.
- **Tensors and layouts:** `Tensor<L, [dims]>`, built on a layout/tile algebra (maps from logical to storage order with provable contiguity and bounds) and on block-sparse iteration, both static and data-dependent (MoE routing, paged KV) [R13, DI].
- **Quantities:** `Quantity<unit, origin>`, with origin one of `Measured{hw}`, `Simulated{model}`, `Predicted`, `Bound{phys|emp|est}`. The formatter and every doc or benchmark sink refuse an unlabelled number [RV §4 #6]. INV-HONEST becomes a type.
- **Linear resources** (`linear struct Lease`), plus **transfer** (Send-like) and **share** (Sync-like) kinds [G05].
- **Typed holes** `?name: T`. Programs with holes type-check, and run until a hole is reached. Each hole exposes its expected type, the in-scope bindings and the relevant definitions [R03].
- **Values carry grades.** Fidelity (`exact` / `real(bound)` / `approx(profile)`) and determinism scope (`cross_device` / `device(t)` / `schedule_dependent`) are part of the type. Fidelity composes by meet [DI].
- **Excluded from v1:** implicit Any, inheritance, macros (comptime replaces them), general dependent types, GC, exceptions as unwinding, multi-shot continuations [R09].

### 3.4 Effects and capabilities

- **One mechanism.** Effects are capability values rooted at `main(root: Root)` and attenuated as they are passed down. Built-in effects: `Io, Spawn, Alloc<A>, Nondet, Time, Fail, Cancel, Unsafe, Foreign, Compile, Train` [R09, DI]. `Train` may only produce weight overlays (§6.6).
- **Rows** (`uses {…}`) are mandatory at public and module boundaries and inferred inside. Handlers must be tail-resumptive or one-shot, compiled by evidence passing [R09].
- **Grade effects:** `timing_only` (policy confinement, §8.4), `lossy(metric)` (fidelity loss, opt-in only) and `nondet(platform)` (platform libm via FFI). A precondition that the FP environment is in its default state is a checked effect, so T1 certificates do not rest on an unstated MXCSR assumption [G02].
- **`deterministic(by: E) {}`** is the counterpart of Rust's interior `unsafe`. Nondet is allowed inside the block, and the result is value-deterministic outside. `E` must name a sealed test or a proof, and declaring such a block requires a manifest grant [G05].
- **Package-granular grants** for `Unsafe` and `Foreign` live in the manifest [G05]. Capability flows are facts in the Fact Plane, so authority is greppable and auditable ("who can reach `Io`?").
- **Evolved code gets nothing by default:** no clock, filesystem, network, spawn, environment, reflection, eval, monkey-patching, or redefinition of equality [R01]. This is what turns the documented hack classes into type errors (§8.13).

### 3.5 Memory model

Mithril uses mutable value semantics with second-class references (`let` / `inout` / `sink`), linear resources, and transfer and share kinds. Below this sits an audited stdlib layer: `Mutex<T>` with a scoped `inout` lock, `Condvar`, `Arena.split` into 4096-aligned `SlabBuf` chunks, `Frozen<T>` with `into_unique`, `File.read_at`, scoped threads and services, and an optional MPSC ring [G05].

G05 found that Hearth's `store.c` is one monitor over integer handles plus a slab typestate (LOADING, then READY with refs>0, then evictable at refs==0). It is therefore expressible with no user-level `Unsafe` [G05, medium-high].

Liveness bugs live in safe code, so test builds substitute a loom-style schedule-permutation scheduler under every stdlib synchronisation primitive [G05]. There is no epoch reclamation in v1; token-boundary quiescence plus `Frozen` refcounts covers hot-swap [G05].

### 3.6 Numerics

- **Strict IEEE by default:** no contraction, no reassociation, no FTZ/DAZ, explicit `fma()`, canonical NaN [DI, R11].
- **Reductions must name their order:** `order lanes(16).tree(8,4,2,1)` (Hearth `sum16`/`dot16`), `blocks(64, exact_i32).seq`, `chunks(c).seq`. Device-neutral fixed-chunk orders are preferred [G03].
- **Transcendentals are specified functions:** `cr` (correctly rounded) or `canon.vN` (a versioned DAG of basic IEEE operations). Platform libm is reachable only via FFI under `nondet(platform)`. A `parity` shim exists solely for comparisons against legacy C binaries [G04].
- **Grades × scopes.** `exact × cross_device` is the default for the canonical core `canon.v1`. A placement checker rejects device-scoped values flowing into computations whose placement is decided at runtime [G03].
- **Exact integer accumulators with overflow proofs** license VNNI, dp4a and INT8 tensor cores bit-exactly. This is the route to a bit-exact GPU expert GEMV [DI, G03].
- **The tolerance grade `real(bound)`** carries FPTaylor/Satire-class certificates, plus runtime margin checks at top-k and argmax. It is never reachable from defaults [R07].

### 3.7 Staging and specialisation

- **Two stages, both typed:** same-language `comptime`, plus `Code<T>` quotes that guarantee well-typed output (MetaOCaml-style, purely generative in v1) [R09].
- **Binding-time types:** `@bind(build | load | call(buckets))` over finite kinds. Specialising on unbounded data is rejected [RV:S10].
- **Schedules are data**, so one generator replaces Hearth's scalar/AVX2/AVX-512 triplets [R05, R09].
- **Load-time specialisation** to a model file runs under a *residual contract*: the residual must agree with the unspecialised program in lockstep on a sample. It is gated on the C-generator go/no-go experiment [RV §4 #18].
- **Never specialise on weight values** [RV §5.4].

### 3.8 Modules, packages and editions

- A module is a file. Definitions are content-addressed by the hash of their normalised Core, and names are metadata [RV:S3].
- **The manifest (`Mith.toml`)** declares:
  - the edition;
  - capability grants;
  - roles (Author, Builder, Prover, Adversary, Gatekeeper) and which principals hold them;
  - sealed modules (specs, goldens, mutant pools, harnesses);
  - invariants, with text hashes linked to their enforcing sealed tests [R11];
  - evidence policies;
  - standing promotion grants (§8.3).
- **`@decision(ADR-0004)` on constants** produces a drift diagnostic when the value disagrees with the referenced record. This would have caught Hearth's 0.9 vs 0.995 heat-decay drift [R11].
- **Contract variance lattice.** Extensions are FREE. Weakenings require an AUTHORITY fact and open typed holes in every dependent, FFI mirrors included. This would have caught the `read_errors` ABI break [RV:D2-F].
- **`export abi` blocks** generate the C header, the ctypes/cffi bindings and the layout tests, with mandatory `struct_size` fields [R11].
- **Editions** pin per module, Rust-style. Their Forge role is described in §8.9.

---

## 4. Compiler pipeline and IRs

| Stage | IR | What happens | Cached by |
|---|---|---|---|
| Parse | **CST** (lossless) | Lark-normative grammar; canonical format; hash anchors for edits | file content hash |
| Elaborate | **Core** | Desugar, resolve, hash each definition; types, refinements (SMT), effects/capabilities, ownership, grades | def hash + edition |
| Facts | **Fact Plane** relations | Every phase emits typed relations (calls, capabilities, grades, evidence edges) into a Datalog store. Invariants, lints, triggers and "why" queries run here [RV:S16] | closure hash |
| Meaning | **MIR** | Index-typed loop/tensor IR with an explicit FP operation DAG. Every float op has a stable DAG id. Reduction orders are explicit nodes | def hash |
| Schedule | **SIR** | Exo-2-style rewrites (tile, parallel, vectorise, lower-with-instr, prefetch, place). Each primitive is legal by construction or by affine effect analysis plus SMT. Float nodes keep their DAG ids [R05, R07] | (def, schedule, target) |
| Select | **LIR** | Instruction-level SSA keyed by XED iclass, with semantics from the owned table [G02] | (SIR, target) |
| Validate | witness | T1 DAG match plus T2 bit-vector obligations of LIR against MIR. The witness is stored in the ledger | closure hash + checker hash |
| Emit | C11 / x86-64 object / PTX text | Strict flags in C11 (MSVC `/fp:precise`, GCC/Clang `-ffp-contract=off`, no fast-math) | (LIR, backend) |

General (non-kernel) code goes Core → **LowIR** (C-shaped SSA) → C11. Kernels take the MIR → SIR → LIR route.

**Incremental, query-based design** [R09]. mithc is a salsa-style query database. Every query is keyed by content hashes: (definition closure, edition, target, toolchain hash). The **evidence ledger is the persistent tier of this cache**. Expensive query results (T1 witnesses, SMT certificates, mutation scores, measurements) are ledger facts, so a rebuild on another machine reuses proofs but not measurements, because measurements are keyed by hardware fingerprint.

**Backends, in order** [DI, R09]:

1. **C11** at M1. This serves Hearth on day one and may satisfy the spirit of INV-DEP.
2. **A direct x86-64 emitter** for the staged-kernel subset at M5. This is where instruction-level T1 applies.
3. **A copy-and-patch JIT** for load-time specialisation, later, with W^X and `FlushInstructionCache` / `membarrier` / `MAP_JIT`.
4. **A PTX expert-tier backend** with explicit `.rn`, loaded through `nvcuda.dll`, at M6. Owner-gated [G03].
5. **LLVM**, optional and never required.

arm64 NEON goes through C11 first. A later emitter would import Arm ASL semantics [R07]. mithc is written in Rust, with an executable Lean 4 reference semantics of Core for differential testing. Self-hosting comes after the Hearth port [DI].

---

## 5. Verification and evidence

### 5.1 The trusted core (F0)

F0 is everything whose bug would let a wrong candidate be accepted. It is kept small, hash-locked, human-owned and attacked on purpose [RV §5.19].

| Component | Role | Size and validation |
|---|---|---|
| Confinement re-checker | Independent re-check, on Core, of the properties space certificates depend on: effect rows, opacity of `P`, no FP-environment writes, fuel bounds, sealed-object ownership. The full type checker is *not* in F0; this small re-checker is (diverse double-checking) [inference] | small; mutation-tested |
| T1 FP-DAG matcher | Bit-exact equivalence modulo an audited list of IEEE-exact rewrites (lane renaming, order-preserving moves, exact integer identities) [R07] | rule list proved in Lean |
| T2 BV obligations | Integer ranges, saturation freedom, exact int→float, alignment; SMT/SAT with certificates (bv_decide-style) [R07] | certificate checker |
| T3 tolerance certificates | Opt-in `real(bound)`; runtime margin checks at discontinuities [R07] | labelled lossy by construction |
| ISA semantics table | XED-keyed, hand-written, with an explicit FP-environment layer; fuzz-validated on Zen 5 with Bochs as a second oracle. Covers Hearth's ~105 instruction forms (74 mnemonics), of which ~10 are FP-sensitive [G02] | estimated 25–40 families, 1.5–3k lines [G02] |
| Lean 4 reference semantics | Differential oracle for Core; meta-theory for T1 rules and schedule primitives; Comparator-style gate for deep proofs [R04, R07] | grows with proofs |
| Measurement service | Owns the clock; joins all async work; pins threads; warm and cold runs (CLFLUSHOPT sweeps on Windows); hardware fingerprint; anytime-valid e-values [R01, R08, RV:S1] | adversarial timing suite |
| Gate runner and sandbox supervisor | Runs sealed suites hermetically; Job Objects / WSL2 / VM; supervisor-held limits; no network; read-only tests [R01] | bypass suite (symlinks, case twins, 8.3 names) |
| Ledger kernel | Append, signature verification, invalidation by closure hash, AUTHORITY checks | small |

### 5.2 Checker tiers (cheapest first)

- **T0, by construction:** membership in a certified space (§8.4).
- **T1:** DAG-match witness.
- **T2:** bit-vector certificate.
- **Lean proof** through a Comparator-style gate.
- **Tested:** property tests plus a mutation score under a declared fault model.
- **Measured:** statistical, with a fingerprint.

An "unknown" or a timeout counts as rejection [R07]. Test-only acceptance of an `exact`-grade realisation is a compile error [RV §4 #10].

### 5.3 The evidence lattice and the ledger

The settled lattice is: **proof > validated > tested > measured(hw) > assumed** [DI]. I use it with one refinement (not a deviation). A claim has a *property kind*:

- **Correctness kinds** use proof / validated / tested / assumed.
- **Performance kinds** use measured(hw, e-value) > simulated(model, calibration) > estimated > assumed, because formal speed proofs are rejected [DI].
- **Prune kinds** use the bound tiers phys / audited-emp, while est may only rank [RV:D3-ii].

A ledger fact is:

```
claim { subject: closure_hash, property, spec: spec_hash, grade, kind, verdict: accept|reject|unknown,
        scope: Pred(env), toolchain: hash, target, hw: fingerprint?, evaluator: hash,
        provenance { principal, role, model_family, prompt_hash? }, cost { tokens, cpu_s, wall_s }, sig }
```

An artifact's effective grade is the meet of its evidence and its spec's strength [RV:D2-E].

When any element of the key changes, the fact is not deleted. Dependents are marked stale and re-validated lazily. **Tombstones are claims with `verdict: reject`** plus the extra fields in §8.7. Positive and negative knowledge share one store, one query language and one invalidation rule.

### 5.4 Spec ownership

The roles are Author, Builder, Prover, Adversary and Gatekeeper. Their write capabilities are disjoint. mithc refuses any change set in which a Builder or Prover writes a spec, witness set, mutant pool, holdout or gate [RV:D2-E].

- **Spec lifecycle:** draft → hardening → admitted (hash-locked) → amended (new hash).
- **Two-sided strength:**
  - soundness (the reference and legal variants pass);
  - a kill interval with the unknown fraction reported;
  - vacuity (no trivial witness passes);
  - latitude (several admitted variants, so restating the implementation is penalised);
  - independence (distinct principals or model families).
- Sealed commit-reveal mutant pools. `WeakSpec` diagnostics [RV:D2-E].

**All Forge proposers are Builders by construction.** This is the structural answer to "can the agent edit the tests?". Specs are the bottleneck: VERINA measured 52.3% spec soundness against 72.6% code correctness [RV:D2-E]. So specs get their own adversarial process instead of being trusted.

---

## 6. Runtime and targets

### 6.1 CPU ISA tiers as data

| Tier | Coverage |
|---|---|
| x86-64-v3 (+ optional AVX-VNNI) | Intel client through Panther Lake |
| x86-64-v4 (AVX-512 F/BW/VL + VNNI/BF16/VBMI) | Zen 4/5. No AMX and no FP16 on Zen 5 |
| AVX10.2 | when shipped |
| AMX | Xeon only |
| arm64 NEON (+ optional SME) | Apple |

Sources: [R08]. For `exact` reductions the lane count is semantics: 16 lanes is one zmm, two ymm or a half-warp. Vector width is a cost-model choice only where the grade allows it [G03, R08]. Dispatch is cpuid plus XCR0 at load time, through atomically cached tables. There are no P/E-core paths [R08].

### 6.2 Memory and storage tiers

- `Vram`, `Dram`, `Nvme` and `Hdd` are type-level tiers. `resident<T>` and `streamed<T>` mark residency.
- Acquire-futures carry demand vs prefetch priority and support cancellation.
- Compute runs in completion order, followed by a canonical-order combine.
- **VRAM is in the placement model from v1**, with capacity, bandwidth and transfer cost, even before any GPU backend [G03].
- Bytes/token by tier is a first-class cost annotation [R08].

### 6.3 Threads

- A persistent pool, spin-then-sleep.
- `par for` with compile-time disjoint writes.
- Dynamic chunk claiming.
- CCD topology in the cost model (per-CCD cap ~64 GB/s) [R08, R11].

### 6.4 Determinism scopes

Every value is `cross_device`, `device(t)` or `schedule_dependent`. Logs record (binary, ISA, version root, inputs, kv_policy) per token [R12].

### 6.5 Hot-swap

- Versioned dispatch tables.
- Release-store of an aligned pointer at quiescent points (token boundaries).
- Reclamation by quiescence plus `Frozen` refcounts.
- No self-modifying code, INVD or CMPXCHG16B tricks [DI, R08].

### 6.6 Living models

- `Weights<V>` are immutable and content-addressed: a Merkle root over the base plus an ordered overlay stack.
- Typed overlays: `SlabReplace`, `LowRank`, `AddExpert`, `SlotDelta`, `Codebook`, `KVPrefix`. Retrieval is the default path for facts.
- Copy-on-write at expert granularity.
- Epoch commit at token boundaries (Hearth's `hx_store_tick`).
- Per-sequence version pinning, with an explicit KV policy (`Recompute(from_layer)` / `AcceptStale` / `Restart`).
- Signed provenance on every overlay.

Sources: [R12]. Mixing tensors from two versions in one forward pass is a type error [R12].

### 6.7 Evaluation builds

- Poisoned fresh allocations.
- Outputs must be materialised values.
- Shapes come from the evaluator's types.
- No undeclared cross-call state [R01].

---

## 7. Agent protocol and toolchain

### 7.1 Session lifecycle

| Step | Command (CLI `--json`; same queries over LSP and MCP) | What the agent gets |
|---|---|---|
| Orient | `mithc guide` (Tier 0 ≤ 8 KB; `--tier 1`) · `mithc status` | Card, false-friend table, open holes, stale evidence, owned modules, claimed tasks |
| Read | `mithc sig <path>` · `mithc view <def> --lines 100` · `mithc query 'fn(&[f32]) -> f32 uses {}'` | Signatures as sufficient summaries; type-directed search that returns **only existing definitions**, which stops hallucinated APIs |
| Hole | `mithc hole <name>` | Expected type, bindings, relevant type definitions (ChatLSP-style) [R03] |
| Edit | `mithc edit --anchor <def>@<hash> --search … --replace …` | Search/replace without line numbers, anchored to a definition hash. `StaleAnchor` if the definition changed. The edit is accepted only if it parses and type-checks [R03, RV:S3] |
| Check | `mithc check` | Grouped root-cause diagnostics: stable codes, spans, expected/actual, fixes with applicability, `FalseFriend`, SARIF [R03, R04] |
| Prove | `mithc prove <def>` | Discharges contracts and T1/T2. Remaining obligations come back as typed holes |
| Test | `mithc test --mutate --fault-model numerics_v1` | AST- and type-aware mutation on the diff; equivalent-mutant detection via e-graph |
| Bench | `mithc bench <def> --niche …` | A request to the measurement service. The result is a `Quantity<…, Measured{hw}>` with an e-value. **Agents cannot time code themselves** |
| Explain | `mithc explain perf <def>` · `mithc why <claim>` | Bound, achieved fraction, binding resource; derivation trees for any fact |
| Forge | `mithc evolve <slot>` · `mithc archive <niche>` · `mithc revisit [--scan|--design]` · `mithc promote --propose` | Candidates, elites, tombstones, fired triggers; promotion requests |
| Hand over | `mithc handover` | A manifest generated from ledger facts: commands actually run, outcomes, typed measurements, open holes, new tombstones and claims. Nothing is self-reported [R11] |

### 7.2 Swarm rules

- Agents take *advisory* claims, never locks. Cursor measured file locks collapsing 20 agents to the throughput of 2–3 [RV:D2-F].
- FREE operations merge by union.
- SEAL requests go to a sequencer.
- AUTHORITY operations need a maintainer signature (§8.11).

### 7.3 Local models

Hearth owns the logits for local models, so it can apply grammar and type masks there. Type constraints cut compile errors by 52–75% [R03]. Masks are off by default under INV-LOSSLESS-DEFAULT [R04].

### 7.4 Tier 0 reference card (outline; ≤ 8 KB)

1. Ten-line grammar summary and keyword list.
2. The false-friend table: float sums, ties, rounding (`round` vs `round_ties_even`), NaN order, empty sums (+0.0), Q4 layout, no contraction.
3. Effects and capabilities in five lines.
4. Grades and scopes.
5. About ten snippets, like §3.2.
6. The edit, check, bench and handover commands.
7. The five forbidden things: writing specs or gates as a Builder; reading the clock in evolved code; `assume`/`sorry`; unlabelled numbers; test-only acceptance of exact code.

The card is curated by maintainers, not generated: self-generated skills scored −8 to −12 points [G01]. It is itself an F3 Forge object (§8.9).

---

## 8. The Forge

### 8.1 Premises from evidence

1. **The archive matters more than self-modification.** On SWE-bench, DGM fell from 50.0% to 23.0% without its archive, against 39.0% without self-modification [R01].
2. **Clade statistics predict descendants better than scores do.** HGM's clade-metaproductivity estimate correlates 0.778 with empirical CMP, against 0.285 for DGM's scheme. HGM used 517 vs 1231 CPU-hours on SWE-Verified-60 [R01].
3. **Evaluators break.**
   - DGM faked logs and removed hallucination markers.
   - CUDA-L1 hacked timing on 32.8% of 250 kernels.
   - o3 hacked 30.4% of RE-Bench runs.
   - The AI CUDA Engineer fell from 3.13x to 1.49x.
   - AlphaEvolve exploited leaky verifiers (Tao et al.) [R01].
   - Hearth's golden gate was bypassed through symlinks, case twins and 8.3 names [RV:D2-E].
4. **Ideas lose for contingent reasons and come back.** Examples: MoE (1991 to 2017), e-graphs to egg, the delta rule to KDA [R02]. Hearth's own ADR-0004 carried an informal "revisit if" clause, and measurement later overturned it: LRU beat decayed LFU by 8–13 points on real traces (measured).
5. **LLMs propose well but judge badly** [R02].
6. **Measurement is the scarce resource.** Replay-conditioned sound bounds pruned 16–41% of candidates per cache size (66% joint) in a simulated pilot, while physics-only rooflines pruned none [RV:D3-ii].
7. **Obvious objectives deceive.** Depth-4 lookahead raised Hearth's hit rate from 73% to 86% but cut decode from 13.0 to 10.0 tok/s (measured) [DI].

### 8.2 Vocabulary

| Term | Definition |
|---|---|
| **Slot** | A declared evolvable site: frozen signature, effect row, space, objective, holdout and promotion rule (`evolve slot`, §3.2f). It generalises AlphaEvolve's EVOLVE-BLOCK into a typed hole [R01]. |
| **Space** | The set of bodies admissible in a slot, defined by type and effect. |
| **Space certificate** | One-time evidence, keyed by the core's hash, that every member of a space preserves the meaning or the declared grade. |
| **Candidate** | A content-addressed body with its lineage and proposer provenance. |
| **Niche** | A (hardware class, shape bucket, model family, grade) cell. |
| **Elite** | The best candidate in a niche on the aligned objective, with evidence above the policy threshold. |
| **Clade** | A candidate and all its descendants. |
| **Tombstone** | A reject claim with scope, contingency class, binding factor, budget ratio, reproduction recipe and triggers. |
| **Trigger** | A decidable predicate over environment facts (§8.7). |
| **Promotion** | Making a candidate the selection for a *profile* (opt-in, per niche) or a *default*. |

### 8.3 Levels, evaluators and authority

| Level | What may change | Admissibility (correctness) | Fitness | Who promotes |
|---|---|---|---|---|
| **F0** trusted core | Checkers, evaluator, measurement service, semantics table, specs, gates, ledger kernel | Human change; independent review; adversarial suite; Lean meta-proofs where feasible | n/a | Maintainers, two signatures (AUTHORITY) |
| **F1** artifacts | Schedules, policies, layouts (lossless repacks), placement plans, kernel realisations; lossy formats and weight overlays only in the opt-in lane | T0 space certificate, or per-candidate T1/T2. Lossy lane: T3 or statistical gates plus opt-in | bytes/token, stall/token, measured time; e-values | *Profile:* a standing grant may auto-promote. *Default:* human |
| **F2** toolchain | Heuristic hooks (inlining, tiling, fusion, unroll, register priority, placement), cost models, new rewrite rules, diagnostic wording | Heuristics choose only among certified rewrites, so they can be slow but never wrong. New rules carry an obligation discharged by T1/T2/Lean. Translation validation in evaluation builds [R01] | Held-out compile and run time, code size; for diagnostics, agent repair rate | Human (lightweight ADR) |
| **F3** language and stdlib | Grammar, semantics, stdlib signatures, pack atoms (card, examples, error catalogue), surface map, editions | Lean semantics diff plus reference-interpreter patch plus corpus-preserving migration (§8.9) | Cold-agent comprehension: verified pass@1 (VP@1), checker-accepted-but-wrong rate, Pareto slope vs C11/Rust arms | Human ADR, always [R01] |
| **Fm** meta | Selection policy, mutation operators, prompts, budget split, emitters | Counterfactual replay on the archive, then a capped shadow run | Archive productivity (CMP growth per CPU-hour and per token) | Human |

**Standing grants are a refinement of human promotion, not a deviation from it.** A maintainer can sign a revocable fact such as `grant store_policies: space timing_only, slot store.*, promote profile when e_value >= 100 and plausibility_pass, expires 2027-04-01`. Under that grant, elites flow into *opt-in niche profiles* without a per-candidate signature. Defaults still need a signature. Grants are AUTHORITY facts: logged, scoped and time-limited.

### 8.4 Space certificates: prove the space, measure the candidate

Six independent revisit branches converged on this move [DI, RV §6.1]. Mithril makes it a language mechanism.

| Space | What is free | One-time certificate | Per-candidate check | Hearth instance |
|---|---|---|---|---|
| **`timing_only` policies** over opaque payloads | Eviction, prefetch, I/O ordering, mirror choice, thread mapping | Core theorem against *demonic* hints, five obligations: O1 hint validation, O2 slab race freedom, O3 arrival-order confluence, O4 lossless content-hashed tiers, O5 liveness. Evidence: bounded model check, chaos suite, 100% core-mutant kill [RV:D2-A] | Confinement re-check (milliseconds) | `cheaper`, `pick_victim`, `slot_for_prefetch`, `pick_file` (under 60 lines) |
| **DAG-preserving schedules** | Tiling, parallelisation, integer vectorisation, prefetch distance, placement | Soundness of each schedule primitive against the Lean reference semantics | T1 witness (renaming check), cached | Regenerating `quant_avx2.c` and `quant_avx512.c` from one generator |
| **Exact rewrite licences** | E-graph rewrites inside the compiler | Each rule proved IEEE-exact or integer-exact | None | Integer reassociation under overflow proofs |
| **Heuristic hooks** | Compiler decisions | Hooks are pure functions from features to a choice among certified rewrites | None for correctness; translation validation as a safety net | Prefill tile sizes |
| **Cross-device placement** under `exact × cross_device` | CPU vs GPU expert compute; upload-on-miss vs compute-on-CPU | Canonical kernels T1-validated on both backends | None | Choosing Strata/Fiddler-style vs llama.cpp-style becomes a pure cost decision with identical output [G03] |
| **Lossless layout repacks** | Interleaving, row-interleaved repack | Bijection (round-trip) proof per layout pair | Round-trip check | Load-time repack into kernel-native layout |

Outside these spaces a candidate needs a per-candidate refinement certificate, or it goes to the **lossy lane**: `lossy(metric <= bound)`, statistical gates, opt-in, never default [RV:S1 Tier 3].

The archive records which space a candidate belongs to. A candidate that fails space membership but passes T1 is still admissible; the space is a fast path, not the only door.

### 8.5 The evaluation cascade

Each stage records its result in the ledger, and failing a stage stops further spending [R01].

| # | Stage | Typical cost | Rejects |
|---|---|---|---|
| 0 | Normalise, then e-graph dedup against the archive | ~free | Exact duplicates, before any spend [R01] |
| 1 | Parse, type, effect and space-membership check | ms | Hack classes (§8.13), out-of-space bodies |
| 2 | Sound lower-bound prune: replay-conditioned bytes at `phys` or audited-`emp` peaks; emits a `PruneCert` | ~1 s per candidate in the pilot (simulated) | Candidates that cannot beat (1 − mde)·UCB(incumbent) [RV:D3-ii] |
| 3 | Correctness: T1/T2 witness, or property tests on randomised and held-out shapes | ms–s | Non-refining realisations |
| 4 | Simulator ranking (`est` tier; ranks, never decides) | s | Nothing; reorders the queue |
| 5 | Microbenchmark on the measurement service, quiet machine | s–min | Slow candidates |
| 6 | Held-out macro run (end-to-end tok/s, load-gated) | min | Overfit candidates |
| 7 | Plausibility gates: beating a phys bound, a Belady bound (prefetch-free policies) or replay byte counts | ms | Hacks and evaluator bugs (**quarantine**, not rejection) [R01] |
| 8 | Anytime-valid e-value against the project error budget | — | Noisy claims (e.g. the 19–22 vs ~25 tok/s llama.cpp comparison) [RV:S1] |
| 9 | Archive insert: a niche elite, or a tombstone with scope | — | — |
| 10 | Promotion: standing grant (profile) or human signature (default) | human | — |

Audits re-measure a fraction ρ of pruned candidates. A single bound violation quarantines that bound term, and the Fact Plane revokes every dependent `PruneCert`. Pruned candidates stay in the archive as possible parents [RV:D3-ii].

**The error budget.** The error budget α is a project-level resource. Every promotion spends some of it, and only a human decision replenishes it. Running many trials therefore cannot launder a false promotion [RV:S1].

### 8.6 The archive: quality-diversity over hardware × shape niches

- **The archive is a view, not a separate database.** It is computed over ledger facts.
- **Niche key:** hardware class (derived from the fingerprint: ISA tier, DRAM-bandwidth class, storage class, VRAM) × shape bucket (op, dimension buckets, dtype, top-k, batch, working-set/cache ratio) × model family × grade [R02].
- **Behaviour descriptors are computed by the compiler**, never self-reported:
  - bytes/token by tier (the *aligned* descriptor);
  - arithmetic intensity;
  - vector width;
  - working-set level;
  - spills;
  - fusion depth;
  - determinism class [R02, Pugh et al. via R02].
- **Tessellation:** CVT-MAP-Elites or Dominated Novelty Search. Each cell holds its elite, the runners-up, its tombstones and the lineage.
- **New niche test.** When a new CPU or shape appears, run the current elites on it, PATA-EC style. A familiar rank order means reuse. A novel rank order opens a niche and starts a search [R02].
- **Transfer.** Elites and tombstones from niche *i* are periodically evaluated on niche *j*, POET style [R02].
- **Selection.** HGM-style Thompson sampling over clade statistics (CMP̂ = clade successes / clade trials). Expansion is separated from evaluation, with HGM's UCB-Air rule (α = 0.6) [R01]. Two additions:
  - a DGM-style non-zero floor with a 1/(1+n) visit penalty, so no clade is starved;
  - cross-niche clade credit: a clade that produces elites in several niches earns credit in all of them [inference].
- **Mutation operators:**
  - LLM SEARCH/REPLACE edits confined to slot bodies (AlphaEvolve-style);
  - CMA-ME emitters for continuous knobs (tile sizes, prefetch distance, decay constants);
  - e-graph local rewrites;
  - bandit selection over proposer models (ShinkaEvolve) [R01, R02].
- **Budget split.** Exploitation / triggered revisits / random tombstone audit starts at 70/20/10 [inference; R02 found no evidence for a particular split]. The split is itself an Fm object.

### 8.7 Tombstones, scoped verdicts and `mithc revisit`

**Schema.** Fields, following [R02 §B]:

- content hash and lineage;
- an exact reproduction recipe (source, toolchain hash, flags, seed). This is Go-Explore's "return" step, and it prevents detachment;
- environment fingerprint;
- evidence, with measured/simulated label and noise controls;
- **verdict scope**;
- contingency class: H hardware, T tooling, S search, E effort, V evaluation, C composition, X scale, F fundamental-under-assumption;
- binding factor;
- search budget spent vs the incumbent's;
- **triggers**.

**The scope and trigger language is deliberately decidable.** Formulas are built from:

- conjunctions and disjunctions of interval constraints over numeric environment facts (`hw.storage_bw`, `cache_ratio`, `model.top_k`);
- set membership over enumerated facts (`hw.isa ⊇ {avx512_vnni}`, `hw.has_tier(Vram)`);
- equality on hashes (`evaluator == h`);
- relative predicates against the burial snapshot (`≥ 2.0 * scope.storage_bw`, `<= 0.5 * at_burial`);
- existence of a primitive or rule (`toolchain.has(rule chunkwise_householder)`).

Three things follow.

- **Subsumption is decidable**, so tombstones can be merged: a narrower scope with the same class and verdict folds into a wider one. This answers R02's "unbounded archive growth" question for the common case [inference].
- **Triggers evaluate incrementally in the Fact Plane.** When an environment fact changes, only tombstones whose predicates mention it are re-evaluated.
- **Verdicts are never global.** A verdict without a scope is a type error. "Doesn't work" cannot be written.

**Auto-derived triggers (new).** When a candidate is buried, the cascade already knows *why* it lost:

- the bound term that bound it (NVMe bytes, DRAM bytes, span);
- the oracle's gap attribution (eviction, wrong prefetch, lateness) [RV:D2-B].

mithc turns that attribution into a default trigger: "the capacity of the binding resource changes by at least the loss ratio", or "the attributed gap term shrinks by half". Agents and humans may add triggers, but they never have to remember to. Plain "doesn't work" verdicts die because the toolchain writes the scope and the trigger itself.

**The revisit loop** (`mithc revisit`, after [R02 §E]):

1. **Event.** Any change to a hardware fingerprint, toolchain, primitive set, evaluator version, model shape catalogue, numeric contract (e.g. `canon.v2`) or proposer model.
2. **Trigger scan.** An incremental Datalog query. It yields the set of tombstones whose triggers flipped from false to true.
3. **Priority.** `priority = [P_win·V(niche) + β·Novelty] / Cost`, sampled, never argmax.
   - P_win rises with κ (the share of the original loss attributable to changed factors), the under-search ratio, the evidence uncertainty, and clade CMP.
   - Novelty is behaviour-space k-NN distance plus embedding distance plus cost-model surprise.
   - An LLM "interestingness" score only breaks ties [R02].
4. **Return, then explore.** Rebuild the exact variant from its recipe. Older toolchains stay addressable by hash. Re-measure under current conditions, and only then mutate.
5. **Cascade** (§8.5).
6. **Verdict update.** A revived variant becomes a niche elite with its scope recorded. A repeated failure narrows or widens the scope.
7. **Background audit.** A fixed budget slice samples tombstones whether or not any trigger fired, to catch contingencies nobody modelled [R02].
8. **Dormant clades are re-scored** when the proposer model, hardware, heuristic or numeric mode changes [R01 #22].

**Design-level tombstones** (`mithc revisit --design`). The design process uses the same graveyard as the compiler [R02 §G]. Every rejected idea in [DI] is entered as an F3 or F1 tombstone with triggers, for example:

| Rejected idea | Class | Example trigger |
|---|---|---|
| Python-embedded primary surface | E/V | the cold-agent harness shows the embedded arm's VP@1 ≥ the standalone arm's + δ, with CI excluding 0, on two model families |
| VLIW-style bundling | F under OoO | a target with in-order issue appears in the target catalogue |
| SPDK bypass as default | H | an NVMe tier becomes CPU-bound (cycles/byte above threshold) at full link bandwidth |
| Lean replacing SMT | T | Lean vericoding rate ≥ Dafny's on the Mithril proof suite (now 27% vs 82% [R03]) |
| Hit rate as objective | F under prefetch | never; listed so revisits can cite it |
| Timing-based approximation in defaults | F (INV-DET-1) | never for defaults; an opt-in deterministic-degradation variant stays a live F1 lane [RV §4 #22] |

Seed-discussion claims enter as *hypotheses* in a claims ledger. They become tombstones or elites only after execution, because ideation-stage judgments mislead [R02].

### 8.8 F2: improving the compiler without trusting it

- **Heuristic hooks** are pure functions from compiler features to a choice among certified rewrites or schedule primitives. An evolved heuristic can make code slower, never wrong. This is the MLGO and AlphaEvolve-tiling pattern, made structural [R01]. Evolved heuristics are judged on held-out shapes, as AlphaEvolve's tiling result was with half the shapes held out [R01], and on at least two microarchitectures so they do not overfit one Zen 5 box.
- **New rewrite rules** are proposed by agents or by Ruler/Isaria-style inference. Each carries an obligation: IEEE-exact (T1 rule audit), integer (T2), or tolerance-only, which is unreachable from `exact` code [R07]. Rules enter the exact-licence space only after a Lean proof or a certificate. Rule sets are versioned, so a revisit can ask "would rule R have changed this tombstone's verdict?".
- **Cost models** rank and never decide [R05]. Cost-model surprise is a novelty signal.
- **Diagnostics are an F2 target with a measurable fitness:** the repair rate in the cold-agent harness. RustAssistant's error grouping moved GPT-3.5 from 4.97% to 44.76% [R03].
- **Trusting trust.** A candidate compiler never builds F0: not the evaluator, the checkers, the measurement service or the harness. F0 is built by a frozen bootstrap toolchain pinned by hash. When the bootstrap itself is updated (a human F0 change), diverse double compilation is required [R01 #15].
- **Translation validation** runs on every transformed function in evaluation and CI builds, as a backstop against bugs in the certified rewrite rules themselves [R01 #14].

### 8.9 F3: evolving the language itself

**The genome** is the kernel pack: grammar fragments, semantic rules, worked examples, stdlib signatures, diagnostic catalogue entries and the surface map. All are content-addressed atoms. Semantics stay frozen within an epoch [RV:D2-D]. Mutations are GEPA-style reflective deltas; full rewrites are banned [RV:D2-D].

**Fitness is cold-agent comprehension** (`mithc pack` plus the Comprehension Ledger) [RV:D2-D]:

- fresh sessions with a fixed budget of checker and doc calls;
- at least two frontier model families plus local models;
- sealed, hash-locked, rotating Hearth-shaped tasks: bit-exact Q4 dot, grouped top-k with lower-index ties, an LRU slot arena with pins and 4096-byte alignment, a `timing_only` eviction policy;
- every task oracle must kill at least 95% of its mutants;
- the harness owns the oracle.

Metrics: VP@1, first-compile rate, checker rounds, tokens per verified pass, and the **checker-accepted-but-wrong rate**. Fitness is the Pareto front over these, reported as a *slope* (marginal VP@1 per kilotoken), never a raw ratio [RV §5.16].

**Controls:**

- C11 and Rust arms on the same suite and oracle;
- an obfuscated twin;
- padding sweeps;
- leave-one-atom-out;
- a decay falsifier (F4) re-run on every new model generation [RV:D3-i].

Power: about 1.5k attempts per arm to detect a 5-point difference [RV:D2-D, inference]. Paired designs and sequential testing reduce this.

**Per-construct syntax decisions** go through the Surface Lab. For each construct it compares four arms: familiar, familiar plus disambiguator, alien, and an obfuscated control. The rule: pick the arm that minimises tokens per verified pass, subject to false-friend incidence ≤ τ (pre-registered). Falsifier F1 can reject the whole "loud syntax" rule if the alien and disambiguated arms are not cheaper [RV:D3-i].

**An edition is a 6-tuple:** (id, grammar delta, Lean semantics delta, reference-interpreter patch, migration `mig: Core_n → Core_{n+1}`, pack and surface-map delta). Gates:

1. **Corpus closure.** `mig` applied to the whole corpus compiles. The corpus includes the stdlib, Hearth-in-Mithril, the sealed suites, Mithril MultiPL-E, and **every archived candidate's and tombstone's reproduction source**. The graveyard is part of the corpus, or the archive detaches across years.
2. **Corpus preservation.** For `exact` code, the MIR DAG hash is unchanged after migration, or else the golden-corpus outputs are bit-identical. For other code, sealed tests give identical results [R01 #17].
3. **Evidence carry-over** happens only where closure hashes are unchanged. Everything else is marked stale and re-validated lazily, with tombstones included.
4. **Old editions remain compilable** per module. The support window is a maintainer choice; I suggest at least two editions [inference].
5. **Fitness** improves with a confidence interval that excludes zero on held-out suites across two or more families, and no regression on the checker-accepted-but-wrong rate.
6. **A human ADR.** Language changes otherwise Goodhart toward easier benchmarks [R01 #18–19].

**The stdlib splits across levels.** Stdlib *signatures* are F3. Stdlib *implementations* are F1 realisations under their specs. An evolved `sort` is an F1 change, and a new `sort` parameter is an F3 change.

**Goodhart controls:**

- suite rotation every epoch;
- the task distribution co-evolves (DGM §6, via R01);
- the obfuscated twin;
- control arms as pre-registered kill criteria;
- the leave-one-atom-out guessability check;
- human promotion.

### 8.10 Fm: improving the improver, Löb-safely

DGM and HGM keep their selection procedure fixed [R01]. Mithril lets it change under these rules:

- **S1, no self-judging.** An artifact at level *k* may be evaluated only by an evaluator whose build closure contains (a) F0 and (b) promoted artifacts at a pinned snapshot. It may contain no unpromoted artifact of level ≥ *k*, and nothing from the artifact's own clade.
- **S2, frozen judges.** F0 is built by the frozen bootstrap. No Forge output compiles F0.
- **S3, monotone strictness.** Autonomous changes to any checker-like component (lint rules, plausibility thresholds, tactics) must only strengthen it. Shown by replay: over the whole archive, the new accept set ⊆ the old accept set. Loosening is an F0 human change [RV:S1 child 4].
- **S4, free proposers.** Proposers, prompts and mutation operators are untrusted and may evolve freely, because they cannot accept anything.
- **S5, separation of powers.** Specs, gates, holdouts and mutant pools are Author- or Gatekeeper-owned. No Forge process holds those write capabilities (§5.4).
- **S6, budgeted honesty.** The error budget α and quiet-machine time are project resources, replenished only by humans.

**Counterfactual replay.** A new Fm policy is first evaluated by replaying archived trajectories offline. The archive records every evaluation, so "what would policy π′ have selected, and what did those nodes score?" can be answered without new benchmark spend [R01 #21]. Replay is necessary but not sufficient: π′ may want to visit nodes nobody evaluated. Those visits are estimated off-policy and flagged. Only then does π′ steer a *capped shadow run*, at most 10% of budget [inference], before human promotion.

### 8.11 Swarm coordination: a monotone, CALM-style ledger

The ledger's state is a grow-only set of signed, content-addressed facts: `def`, `edit`, `task`, `dep`, `claim`, `evidence`, `tombstone`, `handover`, `adr`, `authority`, `grant`. Every current view is a Datalog query over them [RV:D2-F].

**DEVIATION (partial, earlier adoption).** [DI]/[RV] rank the full CALM ledger as "later" because of its ecosystem cost. I adopt the *monotone substrate* in v1, at near-zero ecosystem cost: each fact is a file named by its hash under `.mith/ledger/`. Git merges a grow-only set of uniquely named files without conflicts. Views are computed by mithc [inference]. Rationale: the evidence ledger and the tombstones must be monotone anyway, and making them union-mergeable is what lets many agents and many years of Forge runs share one archive. The heavier machinery (sequencer-stamped SEAL prefixes, typed conflict holes in the type checker, I-confluence analysis of INVARIANTS.md) stays "later", as ranked.

**Operation classes:**

- **FREE** (monotone: adding a definition, evidence, a tombstone, a candidate, a contract *extension*);
- **SEAL** (non-monotone but mechanical: binding a name, releasing a version, evicting from a profile);
- **AUTHORITY** (normative: specs, goldens, defaults, F0, editions, grants, contract *weakenings*).

CALM says *when* agreement is needed. AUTHORITY says *who* gives it [RV:D2-F].

**Evidence invalidation by closure hash** is how semantic conflicts surface. Two FREE edits that break each other's evidence show up as stale claims, not as silent merges.

A preliminary manual replay of Hearth's 33 handover manifests found about 9 coordination points that were monotone but escalated anyway [RV:D2-F, low-medium]. Test T1 from that node (recall ≥ 0.9 on Hearth's history, flagging the `read_errors` break) is a gate for this component.

### 8.12 Living models as Forge objects

Weight overlays are F1 candidates in the lossy lane. They are produced only under the `Train` effect with a declared compute and byte budget. They are judged by a hash-locked, maintainer-owned gate set:

- efficacy and generalisation;
- locality;
- canary perplexity;
- KL to the parent;
- a capability probe;
- calibration;
- safety refusal;
- MoE routing drift;
- simulated cache impact.

Sources: [R12]. Overlays are never default (INV-LOSSLESS-DEFAULT). Retrieval is preferred for facts, because sequential parameter editing degrades capability at scale in every independent study R12 found.

The cache simulator gives a pre-commit gate no GPU server offers: an overlay's routing drift and predicted tok/s can be checked before acceptance [R12]. Overlay tombstones carry triggers such as "base version changed" or "router retrained", so a buried adapter is re-tested when its base changes.

### 8.13 Threat model and countermeasures

The proposer is assumed capable and adversarial. ImpossibleBench measured GPT-5 cheating on 54% of conflicting tasks [RV:D2-E]. Every documented hack maps to a mechanism:

| Documented hack | Source | Countermeasure | Kind |
|---|---|---|---|
| Faked test logs; removed hallucination markers (DGM) | R01 | The harness owns oracles. Logs are facts signed by the measurement service. Builders cannot write gates | structural |
| Unwatched-stream timing (CUDA-L1, 32.8%) | R01 | No `Spawn` or `Time` in evolved code. The runtime joins all async work before stopping the clock | type error |
| Reading the reference via `torch.empty` reuse (METR) | R01 | Poisoned allocations; reference outputs never in the candidate's capability set | runtime + type |
| Timer overwrite, monkey-patching (o3, 30.4%) | R01 | No ambient authority; evaluator in a separate process or VM, hash-locked | type + isolation |
| Wrong-shape broadcast scoring >1000% (STOP) | R01 | Shapes come from the evaluator's types | type error |
| Disabling the sandbox flag (STOP, 0.42%) | R01 | Limits held by the supervisor outside the candidate's address space | isolation |
| Leaky discretised verifier (AlphaEvolve, Tao et al.) | R01 | Exact or interval arithmetic in verifiers; plausibility bounds | structural |
| Golden-gate bypass via symlinks, case twins, 8.3 names | RV:D2-E | Change sets judged as content-addressed objects, never as paths | structural |
| FTZ/MXCSR set by a hook, silently changing logits | RV:D2-A | `timing_only` forbids FP-environment writes; default MXCSR is a checked effect | type error |
| Hardcoded outputs or "near-zero output" exploits | R01 | Bit-exact refinement against the meaning; sealed holdouts | T1 |
| Gaming a weak spec | RV:D2-E | Spec escrow, two-sided strength, independence | process |
| Capability escape (Gödel Agent calling stronger models) | R01 | No `Foreign` or network in evolved code; proposer model and budget recorded as provenance | type + ledger |

**Forge invariants**, each a checkable property and a release gate for the Forge itself:

- **IF-1:** No candidate is promoted without a ledger fact signed by F0.
- **IF-2:** No Forge process holds a write capability to an F0 or sealed object.
- **IF-3:** Every promotion is reversible. The previous selection stays addressable, and rollback is one AUTHORITY fact.
- **IF-4:** Every score names its evaluator hash and hardware fingerprint. A changed evaluator invalidates the score.
- **IF-5:** Every planted hack in the adversarial catalogue is rejected, at a stage no later than its documented class allows.
- **IF-6:** A score beating a sound bound is quarantined and reported to a human.
- **IF-7:** An asynchronous overseer flags sudden score jumps for human review [R01].

### 8.14 How this goes further than DGM, AlphaEvolve and HGM

| Axis | DGM [R01] | AlphaEvolve [R01] | HGM [R01] | Mithril Forge |
|---|---|---|---|---|
| What improves | The agent's own scaffold | User programs and heuristics in EVOLVE-BLOCKs | The agent's own scaffold | F1 programs, kernels and policies; F2 compiler heuristics and rules; F3 language and stdlib; Fm the selection policy |
| Correctness basis | Per-candidate benchmark | User-written evaluator | Per-candidate benchmark | Space certificates (once) or per-candidate T1/T2 witnesses; tests never suffice for exact code |
| Hack resistance | Monitoring; hacks observed | Evaluator design; leaks observed | Not discussed | Hack classes are type errors; runtime-owned measurement; sealed, content-addressed gates |
| Archive lifetime | One run | One run (program DB) | One run (tree) | Permanent ledger keyed by closure hash × environment; survives toolchains, hardware and editions |
| Negative results | Kept as stepping stones, unscoped | Discarded or kept as population | Unscoped tree nodes | Tombstones with scoped verdicts, contingency class, auto-derived triggers, repro recipes |
| Context change | Not modelled | Not modelled | Not modelled | `mithc revisit`: environment events fire triggers; dormant clades re-scored |
| Niches | Single benchmark score | MAP-Elites + islands | Single score | Hardware × shape × model × grade niches, PATA-EC niche test, cross-niche clade credit |
| Selection | Score × novelty heuristic | MAP-Elites sampling | Clade metaproductivity, Thompson sampling | HGM CMP plus floor plus cross-niche credit; Fm can change it via replay and shadow runs |
| Measurement economy | ~$22k per run [R01] | Cascade | 2.4–6.9x fewer CPU-hours than DGM | Dedup + sound PruneCerts (simulated 16–41%) + cascade, combined with HGM selection |
| Statistical control | None stated | Held-out shapes | Held-out Lite split | Anytime-valid e-values against a project error budget |
| Meta-level | Fixed | Meta-prompt evolution | Fixed | Löb-safe stratification (S1–S6) plus counterfactual replay |
| Human role | Fixed outer loop | Expert confirmation | Fixed outer loop | AUTHORITY facts for defaults, specs, F0 and editions; scoped, revocable standing grants |

**Falsifiable claims** (each a gate in §10):

1. **Amortised correctness.** 100+ typechecked `timing_only` candidates run once through Hearth's goldens with zero logit differences [RV:D2-A P1].
2. **Hacks unrepresentable.** 100% static rejection of the ported hack catalogue [RV:S5 T1].
3. **Scoped revival.** Replaying Hearth's history, the lookahead tombstone fires when, and only when, the simulated environment gains a VRAM tier or a second drive. ADR-0004's informal trigger, encoded, fires on the recorded LRU-vs-LFU traces.
4. **Cheaper search.** Real-engine pruning on the 144-candidate grid with zero false prunes.

**What is not claimed:**

- unbounded capability growth;
- formal speed proofs;
- that language-level gains persist as models get stronger. DGM's transfer added only ~1.2 points on Claude 3.7 Sonnet, and SICA's scaffold made o3-mini worse [R01]. The F4 decay falsifier exists to measure exactly this.

---

## 9. The Hearth port

### 9.1 Stages

The strangler-fig order follows [DI]. Each stage links Mithril-emitted C11 into `hearth_core` behind the `hx_*.h` seams. Gates follow [R11] unless noted.

| Stage | Scope | Acceptance gates |
|---|---|---|
| 0 Freeze and instrument | Tag the port base; build a frozen `hearth-c-ref`. **Recommend ADR-0010 "specified transcendentals" in C Hearth first** [G04]. Then build the cross-binary hash corpus: logits, routes, quantiser bytes, matmul outputs across ISA, T, row splits and NaN/inf. Record CRT/libm identity. Import Hearth's past rejections (lookahead depth, ADR-0004's LFU) as ledger tombstones | Corpus reproducible twice on the 9950X. ADR-0010 decided (either way) before the corpus is locked |
| 1 Quant kernels | Formats as `layout` types; quantisers; one meaning plus schedules replacing the scalar/AVX2/AVX-512 triplets | `test_quant` (117,681 checks); golden ISA/batch identity; byte diff of quantiser output against C (closes the oracle hole); T1 witnesses for every ISA variant; single-thread AVX-512 Q4 ≥ 69.6 GB/s (measured) |
| 2 Container parser | `format` descriptions → verified parser and writer (EverParse3D-style) [RV §4 #15] | `test_modelfile` fuzz cases; golden malformed-file test; identical accept/reject decisions and parsed configs on a generated fuzz corpus |
| 3 Pool | Persistent pool on audited `Mutex`/`Condvar`/atomics | `test_pool`; interleaved A/B dispatch latency within noise of C (~0.75 µs at 16 threads), including the WSL2/Windows crowded-pool scenarios; loom-style permutation suite |
| 4 Store logic + platform | `ExpertStore` core with hint ports; O1–O5 certificate; platform layer as the audited Unsafe layer (**riskiest**) [DI, G05] | `test_platform`, `test_store`, golden scheduling independence; ≥ 7 GB/s peak direct-I/O demand reads on the 990 PRO; chaos suite kills 100% of core mutants |
| 5 Forward pass | `model.c` (GQA/MLA attention, routers, shared experts, batched eval) | Full golden suite via `check_golden.py --run`; hash corpus; 512-step real-model decode hashes; load-gated tok/s parity (e-value) at 2/4/8 GiB caches and 512/2048-token prefill |
| 6 API | `export abi` produces `hearth.h` (19 functions, same struct layouts, plus `struct_size`) | Python toolkit and ctypes mirror tests unchanged. Retire the C core; **keep `hearth-c-ref` permanently** as a differential oracle |

### 9.2 Forge track, interleaved with the port

| Track | When | Target | Honest expectation |
|---|---|---|---|
| F1-a | From M0, before the language exists | Eviction and prefetch policies against `hearth.sim` (960k requests through five policies in ~2.6 s) on a scratch copy, through an `hx_policy` shim mirrored in the simulator [RV:D2-A E0]. Objective: bytes/token and stall, with MIN-bytes and AGL-LP oracles [RV:D2-B] | Eviction gains of a few points at most; prefetch timing is the bigger lever; the durable win is assurance [RV:D2-A] |
| F1-b | After Stage 4 | The same space on the live engine; promotion into opt-in profiles under a grant | Beat the best measured policy at ≥ 1 cache size with e ≥ 100, or tombstone with scope |
| F1-c | After Stage 1 | Prefill VNNI tiling, and the attention value pass (a bit-identical AVX-512 prototype exists: 18 → 94 GMAC/s) | Compute-bound paths are where kernel search pays off; decode GEMV is near the bandwidth roof [R11] |
| F1-d | After the GPU tier (owner-gated) | CPU/GPU expert placement under `cross_device` | Simulated 3.6–4.8x for in-RAM MoE [G03]. Must be measured |

**Physics ceilings, stated up front so the Forge cannot be credited with impossible gains [DI, R08]:**

- Qwen3-30B-A3B in the lossless format: ≈ 34 tok/s at 77 GB/s (measured DRAM bandwidth), against Hearth's 19–22, so about 1.5x of CPU headroom.
- Kimi-class on one NVMe: a 0.8–2.9 tok/s band, physics cap ≈ 3.4.

A Forge claim above a sound ceiling is quarantined (§8.5, stage 7).

### 9.3 Constitutional decisions for Hearth's maintainers

1. **INV-DEP and ADR-0001** forbid a non-C core. A superseding ADR is needed, which trips Hearth's circuit breaker. My recommendation: Mithril emits C11 plus OS APIs with no runtime library, which plausibly satisfies the invariant's spirit [DI, R11].
2. **ADR-0010, specified transcendentals** (`cr` sinf/cosf; `cr` or `canon.v1` expf), *before* the hash corpus. UCRT alone switches between FMA3 and non-FMA3 paths, measured to differ on 44,232 sinf inputs [G04]. Then add INV-DET-4: cross-OS hash equality.
3. **Is the RTX 5070 in scope for compute?** Does `nvcuda.dll` count as an OS API under INV-DEP? Should the display move to the iGPU (~1.5 GB of VRAM freed)? [G03]
4. **Tighten INV-DET-1** to name device placement as an axis once a GPU tier exists, and require bit-identity for any dynamically placed op [G03].
5. **The cross-binary hash corpus** becomes a sealed, maintainer-owned oracle next to the golden suite. The golden suite is relational and tolerance-based [R11].
6. **ABI `struct_size`/version fields** on `hearth_options` and `hearth_stats` [R11].
7. **Which heat-decay value is normative:** 0.9 in code or 0.995 in ADR-0004 and `hx_store.h` [R11].
8. **Forge authority:**
   - Who may sign standing grants?
   - May a `timing_only` default change (an output-preserving change, but ADR-0004-class) be promoted by grant, or only by ADR? I recommend ADR only.
   - May the Forge run unattended on the maintainer's machine, and under what isolation?
9. **Qualify or fix INV-DET-1's mirror clause.** It requires full slab hashing (O4).
10. **A default-MXCSR invariant** with a check at worker start [G02].

### 9.4 Live Hearth defects to report (not fix) [DI]

- `check_mirror` samples only the first page.
- `hx_store_heat` returns an unguarded pointer (a data race).
- The `read_errors` ABI break wrote past the ctypes buffer.
- MXCSR is never asserted.
- Heat decay is 0.9 in code vs 0.995 in ADR-0004.
- The server has storage channels (`cached_tokens`, `/stats`, unauthenticated `/health`) [RV:D3-iii].
- With `n_io=1`, a demand read can queue behind prefetch [RV:D2-A].

---

## 10. Roadmap

Gates are pre-registered. Thresholds marked *[choice]* are design decisions, not measurements.

| Milestone | Deliverable | Gate (measurable) | Pre-registered kill criterion |
|---|---|---|---|
| **M0 Ledger and judges first** (before the language) | Ledger kernel + tombstone schema + Fact Plane (Soufflé or CodeQL prototype); measurement service; sandbox supervisor; cold-agent harness with C11 and Rust arms; F1-a policy Forge on `hearth.sim` (scratch copy) | Hack catalogue planted as candidates: 100% caught. Lookahead and ADR-0004 tombstones fire correctly on replayed environment changes. Prune pilot reproduced on the simulator | Any planted hack accepted → stop; redesign the evaluator before writing language code |
| **M1 Core language + C11** | Parser, Core checker (types, effects, refinements, grades), C11 backend, Tier 0/1 card, Mithril MultiPL-E, Surface Lab pilot on D1–D5 | Sealed Hearth-shaped tasks: Mithril VP@1 within δ of the better control arm after ≤ 2 pack epochs, two model families. δ = 5 points *[choice]* | Mithril VP@1 below the better arm by more than δ (CI excluding 0) after 2 epochs → Mithril shrinks to a verification and evidence layer over C/Rust (the design permits this [RV:D2-D]) |
| **M2 Exact kernels** | MIR/SIR/LIR; T1 matcher; T2 obligations; ISA semantics table (Zen 5 fuzzed); port Stage 1 | Stage 1 gates (§9.1). T1 accepts all of Hearth's kernels with zero false positives on the seeded numerics fault model | T1 ever accepts a non-identical kernel → halt and audit. Or acceptance needs > 40 audited rewrite rules *[choice]* → downgrade kernels to "tested", reconsider T1 |
| **M3 Certified policy space live** | `timing_only` + hint ports; store core with O1–O5; Stages 2–4; F1-b live | ≥ 100 typechecked policy candidates bit-identical on goldens; chaos suite kills 100% of core mutants; real-engine prune grid (144) with 0 false prunes | Any typechecked policy changes logits → the core theorem is wrong; freeze F1 until fixed. Real-engine stand-in/bound ratio ≈ 2x → drop pruning, keep the Forge |
| **M4 Hearth runs on Mithril** | Stages 5–6; `hearth.h` exported; `mithc revisit` on the full archive; handover manifests generated from the ledger | Full golden suite + hash corpus + 512-step decode hashes; tok/s parity (e-value) at 2/4/8 GiB; Python toolkit unchanged | No tok/s parity at any cache size after a fixed effort budget *[choice: 8 agent-weeks]* → ship Mithril for kernels and policies only (partial port); tombstone the rest with scope |
| **M5 Compiler Forge (F2)** | Heuristic hooks; rule inference with proof obligations; direct x86-64 kernel emitter; diagnostics fitness | An evolved heuristic beats the hand-written one on held-out shapes on 2 microarchitectures, with 0 translation-validation failures; a diagnostics delta improves repair rate (CI excluding 0) | Evolved heuristics lose their gain on held-out shapes in 2 consecutive rounds → freeze F2 heuristics (rules continue) |
| **M6 GPU expert tier** (owner-gated) | Canonical Q4/Q8/MXFP4 expert GEMV in PTX via `nvcuda.dll`; VRAM tier live; F1-d placement Forge | Bit-identical to CPU (one hash across scalar, AVX2, AVX-512 and sm_120); measured speed vs llama.cpp MMVQ on the same card | Canonical GEMV below 0.5x of MMVQ *[choice]* → GPU tier only as an opt-in `device(t)` contract with its own goldens |
| **M7 First edition (F3)** | Edition 2027 with corpus-preserving migration; pack evolved via the Comprehension Ledger; self-hosting starts | Migration preserves 100% of corpus MIR hashes or golden outputs, archive included; VP@1 improvement with CI excluding 0 on 2 families; checker-accepted-but-wrong not worse | No language delta improves VP@1 measurably in 2 epochs → F3 limited to stdlib, docs and diagnostics; syntax frozen |

---

## 11. Non-goals and top risks

### 11.1 Non-goals

- Visual-generation primitives in v1 [R13].
- Runtime self-modifying code, INVD or CMPXCHG16B hot-patching [DI].
- Bypassing LLVM as a goal, and µop-port byte superoptimisation as the main path [DI].
- Formal proofs of speed [DI].
- Lean as the authoring layer, or Lean replacing SMT [DI].
- SMT "bounded loss divergence", or "forgetting-free" types [DI, R12].
- Per-token persistent learning [R12].
- Autonomous changes to defaults, specs, evaluators, F0 or the language. The Forge proposes; humans promote.
- Projectional editors or JSON-wrapped code as agent I/O [DI].
- Seeding synthetic repositories [DI].
- P/E dual code paths [DI].
- A full GPU backend in v1 [G03].
- GC, inheritance, macros, multi-shot continuations [R09].
- Unbounded self-improvement claims.

### 11.2 Top risks

| Risk | Why it is real | Mitigation |
|---|---|---|
| **Cold start: models were never trained on Mithril** | Pass rates track how common a language is; false friends halve accuracy (82.5% → 40.5%) [G01] | Rust-shaped surface; Tier 0 card; typed holes; FalseFriend diagnostics; C/Rust lifter; constrained decoding on local models; the M1 kill criterion |
| **Evaluator or F0 compromise** | Every hack in the literature broke the judge, not the generator [RV §6.3]; the Lean kernel had a soundness bug in July 2026 [R07] | Small F0; diverse re-checking; adversarial suites; hash-locked; process/VM isolation; frozen bootstrap; quarantine on implausible scores |
| **Weak or gamed specs** | LLM specs are sound and complete about half the time [R03] | Spec escrow, two-sided strength, sealed mutant pools, measured independence |
| **Correlated failures among same-family agents** | Knight & Leveson; Goel et al. [RV:D2-E] | Independence as typed evidence; distinct families for Author and Adversary; human review on AUTHORITY |
| **Goodhart on language fitness** | Language loops drift toward easier benchmarks [R01] | Rotating sealed suites; co-evolved tasks; control arms; obfuscated twin; F4 decay; human ADR |
| **Archive bloat and cost over years** | Unbounded tombstones and evaluations | Decidable scope subsumption and merging; cost-aware priority; budget split; evaluations memoised by hash |
| **Small payoff on memory-bound decode** | ~1.5x honest CPU headroom [DI]; `timing_only` may be the smaller prize [RV:D2-A] | Ceilings published in advance; aim the Forge at bytes and scheduling; GPU placement as the big lossless lever; the value of assurance counted explicitly |
| **Measurement noise on a Windows desktop** | The 19–22 vs ~25 tok/s comparison is not yet clean [brief] | Runtime-owned measurement; anytime-valid e-values; quiet-machine scheduling; machine-profile hashes |
| **Hearth constitutional rejection** | INV-DEP and ADR-0001 [R11] | C11 output with no runtime; strangler-fig seams; `hearth-c-ref` retained; partial-port fallback (M4) |
| **Spec drift in Hearth during the port** | 17 uncommitted files; heat-decay drift [R11] | Stage 0 freeze; `@decision` drift diagnostics; ADRs before corpus lock |
| **Scope creep in the Forge itself** | Many attractive mechanisms | Each mechanism has a milestone and a kill criterion; "later" items stay tombstoned with triggers |

---

## 12. Novel vs prior art

### 12.1 What is genuinely new here

As far as the dossiers' coverage goes. Several dossiers note truncated 2025–26 search, so "new" means "not found in R01–R13, G01–G05 or RV".

1. **The Forge as a language feature with stratified levels F0–F3 plus Fm.** Typed slots, spaces, certificates and authority rules apply uniformly to programs, compiler and language. DGM and HGM evolve one level with a fixed loop. AlphaEvolve evolves user programs against a user evaluator [R01].
2. **Space certificates as the unit of trust.** The "prove the space" convergence [DI, RV §6.1] made operational as declared spaces with one-time certificates keyed by core hash. The archive records space membership, and per-candidate correctness costs milliseconds.
3. **Tombstones with a decidable scope and trigger language, auto-derived triggers from bound and oracle attribution, and incremental trigger evaluation in the Fact Plane.** R02 proposed the tombstone record and the revisit loop. Decidable subsumption, toolchain-written triggers and environment-event-driven re-evaluation are this proposal's additions [inference].
4. **Editions that must migrate the graveyard.** Corpus preservation includes every archived candidate and tombstone recipe, so the archive stays executable across language changes. R01 proposed corpus-preserving editions; extending the corpus to the archive is new here.
5. **Löb-safe stratification rules S1–S6, with monotone-strictness checked by replay** (new accept set ⊆ old accept set over the archive). This is a concrete version of RV:S1 child 4, plus counterfactual replay for the meta-level (R01 #21).
6. **Standing, scoped, revocable promotion grants** as AUTHORITY facts. They separate opt-in profile promotion from default promotion, which keeps humans in charge of normative changes without making them a per-candidate bottleneck.
7. **A union-mergeable, file-per-fact monotone ledger on top of git.** It carries evidence, tombstones and coordination facts for agent swarms at near-zero ecosystem cost. The CALM classes come from RV:D2-F; the transport choice is new [inference].
8. **One lattice store for positive and negative knowledge**, keyed by closure hash × environment fingerprint, typed by property kind (correctness, performance, prune) [DI, RV §6.4].

### 12.2 What is deliberately taken from prior art

By area:

- **Self-improvement (R01, R02):**
  - DGM: archive and parent sampling.
  - HGM: clade metaproductivity, Thompson sampling, expand vs evaluate.
  - AlphaEvolve: EVOLVE-BLOCKs, MAP-Elites with islands, evaluation cascade, held-out shapes.
  - ShinkaEvolve: novelty rejection, bandit over proposers.
  - Quality-diversity search: CVT-MAP-Elites, Dominated Novelty Search, POET transfer and PATA-EC.
  - Go-Explore: return, then explore.
- **Compute and verification (R05, R07, G02):**
  - Halide and Exo 2: meaning/schedule split and checked rewrites.
  - Alive2, CryptOpt and KLEE-FP: translation validation and DAG matching.
  - s2n-bignum: precedent for an owned, fuzz-validated ISA semantics table.
- **Semantics (R09, G05):**
  - Koka, Effekt and Austral: effects as capabilities.
  - Hylo, Swift SE-0433 and OxCaml: value semantics and scoped mutexes.
  - Unison: content addressing.
  - salsa: query-based incremental compilation.
- **Agent ergonomics (R03, R04):**
  - Hazel and ChatLSP: typed holes.
  - rustc, RustAssistant and SARIF: diagnostics.
  - Rust editions with `fix` migrations.
- **Revisit archive:**
  - Necula & Lee: proof-carrying code and an evidence lattice (RV:S6).
  - Spec escrow and mutation (RV:D2-E).
  - CALM, LVars and Grove (RV:D2-F).
  - Anytime-valid statistical gates (RV:S1).
  - Albers-Garg-Leonardi prefetching bounds (RV:D2-B).
  - Cold-agent comprehension with GEPA (RV:D2-D).
- **Models (R12):** immutable versioned weights and typed overlays (S-LoRA, Lifelong-MoE, GRACE/WISE).

### 12.3 Open questions this proposal leaves open

- Is counterfactual replay plus a capped shadow run a sufficient safety test for Fm changes [R01]?
- What revisit/audit budget split is principled, and can HGM statistics make it adaptive [R02]?
- How accurate must κ (contingency attribution) be before revisit priorities become noise? Hearth's simulator scalars are uncalibrated [R02].
- Is the PATA-EC rank test stable under desktop measurement noise [R02]?
- What does a canonical expert GEMV cost on sm_120? This one measurement decides GPU usefulness under `exact` [G03].
- Do language-level affordances keep helping as models strengthen, or do they decay like scaffold gains [R01]? F4 measures this every model generation.
- Which signals can be exposed to proposers (diagnostics, profiles) without leaking the scorer [R01]?
