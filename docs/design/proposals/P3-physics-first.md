# P3 — Mithril, physics-first: exact meanings, measured bytes

Status: design proposal (lens: physics-first systems language; tie-breaker: measured speed under
bit-exactness). Date: 2026-10-11. Inputs: `brief.md`, `design-inputs.md` (authoritative),
`draft-thesis.md`, the 18 dossiers R01–R13 and G01–G05 and `revisited-ideas.md` in
`Mithril/docs/research/`, and a read-only pass over Hearth (`docs/NUMERICS.md`, `docs/FORMAT.md`,
`engine/src/quant_avx512.c`, `governance/INVARIANTS.md`).

Conventions. Numbers carry their origin: **measured** (with source), **SIMULATED** (Hearth's
simulator), or **[inference]** (my own arithmetic or judgement). Dossier references look like
(R08 §7). Places where this proposal departs from `design-inputs.md` are marked
**DEVIATION** and argued for.

---

## 1. Thesis and design principles

**Thesis.** Mithril is a Rust-shaped systems language. Every performance-critical computation is
written once, as an *exact, executable meaning*. Checked *schedules*, *layouts* and *placements*
then realise that meaning, and their outputs are provably bit-identical to it. The compiler
derives the cost of each realisation (bytes moved per memory tier, operations per class,
synchronisations) as unit- and origin-typed quantities. It evaluates them against a
machine profile to get a roofline floor, and every measured result is reported as a fraction of
that floor. Correctness is certified once for a whole *space* of realisations: schedules that
preserve the canonical op-DAG, integer reorderings licensed by overflow proofs, `timing_only`
policies that cannot touch outputs, and placements across CPU and GPU that do not change bits.
Agents, and the Forge, then search that space using performance evidence only, measured by a
runtime the candidates cannot see or touch. Hearth is the acceptance test. The port must reproduce
Hearth's logits bit for bit across thread counts, cache states, ISAs and, if the owner admits the
GPU, devices, and it must then beat Hearth's tokens per second under that constraint.

**Principles.**

1. **The meaning is the spec, and schedules cannot change bits.** Strict IEEE is the default, with
   no contraction or reassociation. Reduction order is part of the meaning (`canon.v1` =
   Hearth's NUMERICS.md). A schedule may change where and when an operation runs, never which
   operation runs on which operands (R05, R07).
2. **Bytes are the first-class cost.** Decode is memory-bound: a batch-1 Q4 GEMV sits about 56x
   below the Zen 5 ridge point (R08 §7.2). The compiler therefore tracks bytes per tier
   (VRAM/DRAM/NVMe/PCIe) before instructions, and it rejects IPC or hit rate as objectives
   (R06, revisit REJECT list).
3. **Prove the space, measure the candidate.** Correctness comes from types, effects and checked
   rewrites; speed comes from measurement. No candidate is accepted on tests alone (R01, R07,
   revisit INSIGHTS).
4. **Exact integers buy freedom.** An accumulator with a proved overflow bound is associative, so
   any order (VNNI, dp4a, INT8 tensor cores) gives identical bits. This is the route to fast
   bit-exact kernels on both CPU and GPU (G03).
5. **Placement does not change outputs.** Any computation whose device or tier is chosen at
   runtime must have cross-device determinism scope. Choosing CPU or GPU, or DRAM or VRAM, then
   becomes a pure cost decision (G03).
6. **Formats are types, not code.** Block-scaled quantisation formats are declared once as layout
   types. Pack, unpack, dequantisation and integer-exact dot meanings are derived from the
   declaration, and MXFP4 is native (R06).
7. **Familiar where the meaning is the same, loud where it differs.** The syntax is Rust-shaped
   with no false friends. Every new meaning gets a new keyword or type (G01, R03).
8. **Small trusted core, everything else untrusted.** Translation validation (search proposes, a
   small checker accepts) is preferred over a verified compiler. Mithril owns its x86 semantics
   table (R07, G02).
9. **Authority is explicit.** Effects are capabilities rooted at `main`. Policy code is
   `timing_only` and cannot write outputs, read clocks or touch the FP environment (R09,
   revisit D2-A).
10. **No hidden runtime.** Mithril emits C11 plus OS APIs that Hearth can build without Mithril
    installed. Any GPU path loads PTX through the driver DLL (R09, G03).

---

## 2. Layered architecture

```
 +------------------------------------------------------------------------------+
 | L0  PRINCIPALS   frontier agents (Claude...), Hearth-hosted local models,     |
 |                  maintainers. Roles: Author | Builder | Prover | Adversary |  |
 |                  Gatekeeper -- disjoint write capabilities over the store     |
 +------------------------------------------------------------------------------+
 | L1  TOOL SURFACE mithc CLI (--json) . LSP . MCP . SARIF . pack/guide cards    |
 |                  Agent Edit Protocol (hash anchors, typed holes, StaleAnchor) |
 +------------------------------------------------------------------------------+
 | L2  CODEBASE     canonical .mith text <-> content-addressed definitions       |
 |     STORE        sealed modules: spec . golden . oracle . machine profile      |
 |                  Evidence Ledger (+ tombstones) . Fact Plane (Datalog queries)|
 +------------------------------------------------------------------------------+
 | L3  FRONT END    query DB keyed by content hash (salsa-style):                |
 |                  parse -> resolve -> types/effects/caps -> refinements ->     |
 |                  binding times -> Core                                        |
 +------------------------------------------------------------------------------+
 | L4  MEANING      KIR  kernel meanings: exact op-DAG + Order objects           |
 |     & COST       FIR  flows: tiers, residency, async I/O, placement           |
 |                  cost signatures: Bytes<tier>, Ops<class>, Syncs (symbolic)   |
 |                  machine profiles: origin-typed hardware data                 |
 +------------------------------------------------------------------------------+
 | L5  REALISATION  schedules (checked rewrites as data) -> LIR                  |    +-----------+
 |                  formats -> derived pack/unpack/dot . specialiser @bind(load) |<-->|  FORGE    |
 |                  instruction selection -> C11 | XIR (x86) | PIR (PTX)         |    | proposers |
 +------------------------------------------------------------------------------+    | (untrust.)|
 | L6  VERIFICATION mithcheck (trusted): T0 types/effects . T1 FP-DAG match .    |    | archive = |
 |                  T2 bit-vector SMT with certificates . T3 tolerance (opt-in)  |<-->| ledger    |
 |                  contracts -> SMT . x86/PTX semantics table . Lean ref sem.   |    | QD niches |
 +------------------------------------------------------------------------------+    | tombstones|
 | L7  EVALUATION   sealed evaluator process . runtime-owned clock .             |<-->|           |
 |                  simulator handler . roofline floors and plausibility gates . |    +-----------+
 |                  anytime-valid statistics (e-values)                          |
 +------------------------------------------------------------------------------+
 | L8  BACKENDS     C11 (strict FP) -> lift-and-match T1 over compiler output -> |
 |                  PTX expert tier (nvcuda.dll) / x86-64 direct kernel emitter  |
 +------------------------------------------------------------------------------+
 | L9  RUNTIME      mithrt in C11: pool . store services . I/O (overlapped+      |
 |                  NO_BUFFERING / pread+O_DIRECT) . dispatch tables . epochs . |
 |                  MXCSR guard . audited Unsafe layer . CUDA driver loader      |
 +------------------------------------------------------------------------------+
 | L10 HARDWARE     Zen 5 9950X (2 CCD, AVX-512+VNNI, no AMX) . DDR5 ~77 GB/s    |
 |                  measured . 990 PRO NVMe ~7 GB/s . PCIe5 x16 .                |
 |                  RTX 5070 12 GB 672 GB/s (datasheet) . USB HDD (cold only)    |
 +------------------------------------------------------------------------------+
```

| Layer | Responsibility | Key output |
|---|---|---|
| L0 Principals | Who may write what. Roles get disjoint write capabilities: specs and goldens belong to the Author and Gatekeeper roles, implementations to the Builder (revisit "Spec escrow"). | signed provenance on every store object |
| L1 Tool surface | Every compiler fact is reachable as structured data: JSON diagnostics, hole contexts, API queries, cost and roofline reports, ledger queries. | stable-coded JSON, SARIF, MCP tools |
| L2 Codebase store | Canonical text is the interface. Definitions are keyed by the hash of the normalised AST; names are metadata. The store holds evidence, tombstones and sealed modules. | definition hashes, ledger rows |
| L3 Front end | Type, effect, capability, refinement and binding-time checking. Incremental, keyed by content hash. | `Core` (typed core calculus) |
| L4 Meaning and cost | The canonical semantics object (KIR's per-output FP-DAG) and the cost object (symbolic bytes, ops and syncs). Machine profiles are data. | KIR, FIR, cost signatures |
| L5 Realisation | Applies checked schedules, derives format kernels, specialises to the model at load time, selects instructions. | LIR, C11 text, XIR, PIR |
| L6 Verification | A small trusted checker accepts or rejects realisations and emits certificates. Contracts are discharged by SMT. | witnesses, certificates, evidence rows |
| L7 Evaluation | Measures speed in a process candidates cannot touch, compares results with floors and quarantines impossible ones. | `Measured<T>` with confidence intervals |
| L8 Backends | Emit code without a required runtime. C11 first; kernels then get T1 over the compiler's own output. | objects, PTX text |
| L9 Runtime | The minimal C11 runtime: threads, I/O, store services, dispatch, hot-swap, GPU loader. | `mithrt` (audited, no GC) |
| L10 Hardware | Described by a measured machine profile, never by assumptions. | — |

---

## 3. The language core

### 3.1 Surface syntax policy

- **Standalone `.mith`, Rust-shaped.** Items, expressions, `let`/`mut`, `match`, `Result`/`?`,
  `struct`/`enum`/`impl`/`trait`, `&T`/`&mut T`, by-value move, `as` casts (saturating, NaN→0)
  and `f32::round_ties_even` all mean what they mean in Rust (G01, R03). Integer overflow is an
  error, as in Rust debug builds; Mithril keeps that in every build (proved absent or trapped),
  which is a loud restriction rather than a changed meaning. Rust already forbids FP contraction, so `a * b + c` is two roundings in both languages.
  That makes Rust a safer parent than C, where GCC contracts by default outside ISO modes (R09).
- **Restrictions are loud errors, never silent changes.** References are *second-class*: they
  cannot be stored in fields or returned. That removes lifetime annotations (R09, G05). The one
  way a borrow leaves a call is a *projection* (`w.row(r)`, slicing), which yields a borrow scoped
  to the caller's expression, as Hylo subscripts do. Code that violates this fails with
  `E-REF-ESCAPE` and a suggested handle or `Lease`. Nothing compiles with a different meaning.
- **New meanings get new keywords:** `kernel`, `schedule`, `format`, `flow`, `policy`,
  `placement`, `spec`/`law`/`evidence`, `numerics(...)`, `effects {...}`, `exact_sum`, `reduce`,
  `par for`, `deterministic(...)`, `@bind(...)`. A construct that needs more than one snippet and
  one false-friend line to explain is treated as a design smell (G01).
- **One normative Lark grammar** that fits OpenAI's CFG-tool limits, a canonical formatter, and
  whitespace-insensitive syntax (R03). A Python API exists only for writing schedule and search
  scripts, whose output is checked (G01).
- **Known false friends are listed in the Tier-0 card**, each with a diagnostic. Examples:
  `.sum()` on floats is a sequential fold, so kernels must use a named `Order`; `f32::max`
  follows Rust's NaN rule, while x86 `MAXPS` returns its second operand, available only as
  `simd::maxps`; `round()` rounds ties away from zero, but Hearth quantises with ties-to-even;
  `llama.cpp` Q4_0 and Hearth Q4 use different nibble layouts (revisit INSIGHTS).

### 3.2 Snippets

Snippets are short and illustrative. Comments starting `//!` show what the checker does.

**(a) A quantisation layout type: Hearth Q4 and MXFP4.**

```rust
/// Hearth Q4, FORMAT.md §6: 64 elements in 34 bytes, f16 scale, byte j = (elem j | elem j+32 << 4), stored q+8.
format Q4 {
    block 64; bytes 34; endian little;
    field d:  f16      @ 0;
    field qs: [u8; 32] @ 2;
    element(i: 0..64) -> i8 range(-8..=7) {
        let b = qs[i % 32];
        (if i < 32 { b & 0x0F } else { b >> 4 }) as i8 - 8
    }
    scale() -> f32 = f32::from(d);                 //! widening f16->f32 is exact (table fact)
}

/// OCP MX: E2M1 elements, one E8M0 power-of-two scale per 32 values (17 B/block; layout illustrative).
format Mxfp4 {
    block 32; bytes 17;
    field e:  e8m0          @ 0;
    field qs: [e2m1x2; 16]  @ 1;
    element(i: 0..32) -> e2m1 = qs.nibble(i);
    integer_view(i) -> i8 range(-12..=12) = e2m1::times2(element(i));  //! {0,±1,±2,±3,±4,±6,±8,±12}
    scale() -> f32 requires e in 1..=254 = e8m0::pow2(e) * 0.5;       //! exact power of two
}
```

From each `format` the compiler derives: `pack`/`unpack` (with a proved round trip against the
declared fields); `dequant(i) = scale() * element(i)`; and, when an `integer_view` exists, an
integer-exact dot meaning against `ActQ8` blocks. The `range(...)` annotations feed the overflow
proofs in (b). Sub-byte codes (`e2m1`, `e8m0`, nibbles) are storage codes valid only inside
`format`. They are not arithmetic types, which keeps clear of the seed's "int4 primitives lowered
via popcount" mistake (R05, R06).

**(b) A Hearth Q4 matvec kernel: meaning plus schedule, exact numerics.**

```rust
/// NUMERICS.md §3 (canon.v1). This body *is* the spec; it runs as-is in the interpreter.
kernel fn q4_dot(w: &[Q4; nb], x: &[ActQ8; nb]) -> f32
    numerics(exact, canon.v1)
{
    let mut acc = 0.0f32;
    for g in 0..nb {                                         // order: sequential over blocks
        let isum: i32 = exact_sum(i in 0..64) {              // integer: any order is licensed
            w[g].element(i) as i32 * x[g].q[i] as i32
        };                                                   //! bound: 64*8*127 = 65_024 < 2^24
        acc = acc + (isum as f32) * (w[g].scale() * x[g].d); //! int->f32 exact under the bound
    }
    canon_nan(acc)                                           // NaN -> 0x7fc00000
}

kernel fn q4_matvec(w: &Rows<Q4, nb>, x: &[ActQ8; nb], y: &mut [f32]) numerics(exact, canon.v1) {
    par for r in 0..w.rows() { y[r] = q4_dot(w.row(r), x); }  //! disjoint writes: y[r] written once
}

schedule q4_matvec.zen5 for q4_matvec on isa(avx512f + avx512bw + avx512vnni) {
    tile r by 16 as lanes(f32x16);          //! licence lane_map: rows are independent DAGs
    unpack w.element via nibble_split(u8x64) offset(+8);   // unsigned u = q + 8 in 0..=15
    lower exact_sum to vpdpbusd correct(-8 * x.sum);        //! licence int_assoc: T2 proves no wrap
    hoist w.scale via vcvtph2ps per(block);                 //! licence exact_conv
    keep acc in zmm;                                        //! block order unchanged
    par r.tiles chunk(dynamic);                              //! disjointness inherited
}
// schedule q4_dot.bad { split g by 4 as accumulators(4); }
//! E-NUM-031: rewrite 'split-accumulator' reassociates a float chain; not in licence set exact(canon.v1)
```

The same meaning gets three schedules: `scalar`, `avx2` (two ymm per 16 lanes, `vpmaddubsw`
whose int16 pair bound of 3,810 is a T2 obligation) and `zen5` (above). One generator replaces
Hearth's three hand-written files (R09). The obligations are the ones R07 extracted from Hearth's
comments: the Q4 maddubs bound 3,810 (7,620 low plus high), the Q8 sign-trick bound
32,512 < 32,767, activations in [-127,127], the VNNI bias correction, and
|isum| ≤ 1,032,256 < 2^24 for Q8. Each is a sub-second QF_BV query (R07).

**(c) Cache and prefetch policy under `timing_only`.**

```rust
policy ExpertEvict: timing_only {
    state { last: [u32; MAX_SLOTS], tick: u32 }               // fixed size, no heap
    fn on_use(&mut self, k: SlotKey) { self.tick += 1; self.last[k] = self.tick; }
    fn rank(&self, c: &[Cand<Slab>], pred: &RoutePred) -> Ranking {
        c.rank_by(|s| self.last[s.key] as f32 + 4096.0 * pred.p_use(s.key))  // payload Slab is opaque
    }
    // fn bad(&mut self) { fp_env::set_rounding(Toward0) }   //! E-TIMING-02: FpEnv not in timing_only
    // fn bad2(&self) -> u64 { clock::now() }                 //! E-TIMING-01: Time not in timing_only
}

policy ExpertPrefetch: timing_only {
    fn issue(&self, c: &PrefetchCand, nvme: &Price<Nvme>) -> Hint {
        // shadow-priced rule (revisit D2-B): prefetch only if expected stall saved beats priced bytes
        if c.p * c.stall_saved_ns > nvme.lambda * (1.0 - c.p) * c.bytes_ns + c.evict_damage_ns
            { Hint::Issue } else { Hint::Skip }
    }
}

store ExpertStore<S: Slab> {
    hint evict    = ExpertEvict    fallback Lru wrap robust(Lru, eps = 0.02) fuel(4 * n_slots) off_lock;
    hint prefetch = ExpertPrefetch reserve demand_readers >= 1 budget bytes_per_token(1.15 * oracle.min_bytes);
}
```

A `timing_only` policy receives opaque handles. It cannot reach slab bytes, clocks, the FP
environment, the heap or I/O, and its outputs live only in a hint lattice that the store core
validates at commit. Per-policy checking is a millisecond-scale effect check. Noninterference
(output is either the fallback output or an error, for *any* hint stream and I/O completion
order) is a one-time certificate on the store core with obligations O1–O5: hint validation, slab
race freedom, arrival-order confluence, lossless tiers by content hash, and liveness with
`n_slots ≥ 2·top_k + n_io + 2` (revisit D2-A). This is the clearest instance of "prove the space":
every policy that typechecks is bit-identical by construction.

**(d) A spec with contracts and evidence.**

```rust
spec numerics_q4 owned_by(gatekeeper) sealed {
    law dequant_exact: forall b: Q4, i in 0..64 =>
        dequant(b, i) == f32::from(b.d) * (b.element(i) as f32)
        evidence prove(smt);
    law isa_identity: forall t in targets(q4_matvec) => q4_matvec@t == q4_matvec@meaning
        evidence validate(t1) or test(corpus("golden/kernels/q4"), mutation_score >= 0.90);
    law c_parity: q4_matvec@c11 == extern hearth_c_ref::hx_mm_q4    // cross-binary oracle
        evidence test(corpus("golden/xbin/q4"), hash_equal);
    law decode_speed: tok_per_s(model("qwen3-30b-a3b.cfgB"), cache = full) >= 1.05 * baseline(hearth_c_ref)
        evidence measured(profile("this-pc"), interleaved_ab, e_value(alpha = 0.05));
}

fn act_q8(x: &[f32], out: &mut [ActQ8])
    requires x.len() % 64 == 0 && out.len() == x.len() / 64
    ensures  forall b, i => out[b].q[i].abs() <= 127 && out[b].sum == exact_sum(j in 0..64) { out[b].q[j] as i32 }
    effects  {}
```

A `law` names what it claims, the spec it is checked against, and which evidence kinds are
admissible. Laws about correctness accept `prove`, `validate` or `test`. Laws about speed accept
only `measured`, with a hardware profile, a baseline and a statistical test, so INV-HONEST becomes
a type rule (revisit "Unit-and-origin quantities"). The spec module is sealed: a Builder-role
agent cannot edit it, and weakening a law opens typed holes in every dependent (revisit "Contract
variance lattice").

**(e) An effectful direct-I/O function with capabilities.**

```rust
/// 4096-aligned positional read. Windows: OVERLAPPED + FILE_FLAG_NO_BUFFERING; POSIX: pread + O_DIRECT/F_NOCACHE.
fn read_slab(f: &File<Direct>, at: Offset<4096>, buf: &mut SlabBuf<4096>) -> Result<(), IoError>
    effects { io }
{
    let n = f.read_at(at, buf.bytes_mut())?;          // audited stdlib; blocking, one request
    if n != buf.len() { return Err(IoError::Short { want: buf.len(), got: n }); }
    Ok(())
}

/// Value-deterministic from the caller's view: bytes are a function of the file's content hash.
fn load_expert(m: &Blob<ModelFile>, id: ExpertId, buf: SlabBuf<4096>) -> Result<Frozen<SlabBuf<4096>>, IoError>
    effects { blob }
{
    let mut b = buf;                                    // linear: moved in, moved out
    read_slab(m.file(), m.slab_offset(id), &mut b)?;
    m.verify(id, &b)?;                                  // per-slab content hash (FORMAT v2, proposed)
    Ok(b.freeze())
}

fn main(root: Root) -> Result<(), Error> effects { io, spawn, alloc, blob } {
    let m = root.fs().open_blob::<ModelFile>(root.args().path(0)?)?;   // authority flows from Root only
    ...
}
```

`File<Direct>` and `Blob<T>` are capability values: they can only be obtained by attenuating
`main`'s `Root`. `Offset<4096>` and `SlabBuf<4096>` carry alignment in their types, so the
direct-I/O preconditions (buffer, offset and size all sector-aligned) are type facts, not runtime
surprises (R11 P0). A `Blob` read is value-deterministic, so the logits path sees `{blob}`, not
`{io, nondet}` (G05).

**(f) A flow with completion-order compute, canonical combine and placement.**

```rust
flow moe_ffn(l: @bind(load) LayerCfg, x: &Act, st: &ExpertStore<ExpertSlab>) -> Act effects { blob } {
    let ids = route(l, x);                                       // exact; ties -> lower expert index
    let outs = deterministic("INV-DET-1: golden::test_scheduling_independence") {
        st.acquire_all(&ids).map_on_arrival(|e, w| expert_ffn(l, w, x))   // arrival order varies
    };
    combine_rank_order(&ids, outs, l.routed_scale)               // the sum does not
}

placement this_pc for Hearth<Qwen3_30B_A3B> on profile("this-pc") {
    dense   -> resident<Vram(0)>;
    experts -> cached<Vram(0), 9 GiB> over cached<Dram, 30 GiB> over streamed<Nvme>;
    misses  -> compute where_resident;              // never upload an expert per token over PCIe
    require det(cross_device) for expert_ffn;       //! placement is dynamic, so device-scoped kernels are rejected
}
```

`deterministic(...)` is the counterpart of Rust's `unsafe {}` for nondeterminism. Inside it,
`Nondet` (lock order, I/O completion order) is allowed. Outside it, the value is declared
deterministic, and the declaration must name a sealed test or proof that discharges it (G05).
The checker records it in the ledger as `assumed`, upgraded by that evidence.

### 3.3 Types

- **Scalars:** `i8..i64`, `u8..u64`, `f32`, `f64`, `bool`. `f16` and `bf16` are storage types;
  arithmetic on them requires an explicit, exact widening. Storage codes (`e2m1`, `e8m0`, nibbles)
  exist only in `format`.
- **Refinements on integers:** `n: usize where n % 64 == 0`, `range(...)`, `Offset<4096>`,
  `ExpertId<N>`. These are Flux-style refinements discharged by SMT. Agents get them as
  diagnostics with counterexamples, not as proof terms (R07).
- **Exact accumulators:** `exact_sum` yields an integer whose static bound comes from interval
  analysis over element `range`s and trip counts. The bound licenses reassociation (§3.6).
- **Order objects:** `order::seq`, `order::lanes(16).tree([8,4,2,1])` (= `sum16`/`dot16`),
  `order::blocks(64, exact_i32).then(seq)`, `order::chunks(c, seq).then(seq)`. They are values
  versioned under a numerics contract (G03).
- **Views and layouts:** `Rows<F, nb>`, `View<T, Layout>` with a small layout/tile algebra
  (logical-index to storage maps with provable contiguity and bounds), plus block-sparse iteration
  over static masks and data-dependent block lists such as MoE routing (R13). No visual-generation
  types.
- **Linear resources:** `SlabBuf`, `Lease`, `File`, device buffers. These have **transfer**
  (Send-like) and **share** (Sync-like) kinds (G05).
- **Quantities:** `Quantity<Unit, Origin>` where `Origin ∈ {Measured{profile, load, settings,
  baseline}, Simulated{model}, Predicted{model}, Derived, Assumed}`. Examples: `Bytes<Dram>`,
  `Rate<GB/s>`, `Time`. The formatter refuses to print an unlabelled performance number, and unit
  errors such as Hearth's `/tok` vs `*tok` bug are type errors (revisit "Unit-and-origin
  quantities").
- **Grades on values:** fidelity `exact ⊑ real(bound) ⊑ approx(profile)` and determinism scope
  `cross_device ⊑ device(t) ⊑ schedule_dependent`. Information-flow typing propagates grades to
  outputs. A `pub output` (logits, routes) defaults to `exact, cross_device` (revisit
  "Canonical numerics plus exactness grades").

### 3.4 Effects and capabilities

Effect rows are mandatory on `pub` signatures and inferred inside modules. Effects and
capabilities are one mechanism (R09). Built-in kinds:

| Effect | Meaning | Capability source |
|---|---|---|
| `io` | file/network operations | `File<…>` from `Root.fs()` |
| `blob` | reads from a content-hash-verified immutable source, value-deterministic | `Blob<T>` |
| `spawn` | create threads/services (scope-bounded) | `Root.threads()` |
| `alloc<A>` | allocate in arena `A` | arena value |
| `nondet` | observable nondeterminism | only inside `deterministic(...)` or non-output code |
| `time` | read clocks | evaluator-owned; absent in kernels, policies and evolve slots |
| `fail` | abort the enclosing transaction with an error code (lowered to error returns, no unwinding) | — |
| `gpu<d>` | launch work on device `d` | `Root.gpu(d)` |
| `fpenv` | write MXCSR/rounding/FTZ/DAZ | audited runtime only; banned elsewhere (G02) |
| `foreign` | call C | package grant |
| `unsafe` | raw pointers, layout punning | package grant (`mith.toml`) |
| `compile` | staging/comptime | build tool |

`timing_only` is a *restriction* effect: an empty row plus hint outputs. `lossy` is a label on
configuration fields; a `lossy` field whose default is not the exact variant is a link error
(INV-LOSSLESS-DEFAULT). Handlers are restricted to tail-resumptive and one-shot forms, compiled by
evidence passing. There are no multi-shot continuations (R09).

### 3.5 Memory model

The memory model is mutable value semantics with second-class references, linear resources and
explicit arenas (R09, G05):

- `Arena.split` hands out 4096-aligned `SlabBuf` chunks. `Frozen<T>` is refcounted and immutable,
  and `into_unique()` reclaims it when unique. `Mutex<T>` exposes state only inside a scoped
  `with_lock(|s: &mut State| …)`. `Condvar` waits are expressed as "inout state may change".
- Hearth's `store.c` maps onto these with **no user-level Unsafe** (G05). Store metadata is a pure
  value of integer handles under one monitor. A reader moves a `SlabBuf` out of the lock, reads
  into it, moves it back and freezes it. Leases are linear.
- **Tier address spaces.** `Dram` and `Vram<d>` buffers are addressable within their device;
  `Nvme` is never dereferenceable and is reached only through `read_at` into a buffer.
  `resident<T, Tier>`, `cached<Tier, budget>` and `streamed<Tier>` are residency types on flow
  values (§3.2f).
- Layout control: `#[repr(C)]`, `#[repr(packed)]`, static size asserts, cache-line padding
  (`#[align(64)]`, grouping fields by writer).
- An audited Unsafe/stdlib layer holds Mutex/Condvar, the arena split, `Frozen`, `File.read_at`,
  scoped services, atomics with explicit orderings and the CUDA driver loader. Estimated at a few
  hundred lines per OS (G05). A test build swaps in a loom-style permutation scheduler, because
  liveness bugs live in safe code (G05).

### 3.6 Numerics

- **`canon.v1` is Hearth's NUMERICS.md, normative and machine-readable.** It includes `sum16`,
  `dot16`, the activation-quantisation rule, the block-ordered Q8/Q4 epilogue, canonical quiet NaN
  `0x7fc00000` at kernel sinks, the rank-order MoE combine and sequential-in-t attention
  accumulation.
- **Operations:** `+ - * /` and `sqrt` round to nearest. `fma(a,b,c)` is explicit and never
  implied. `canon.v1` contains no FMA; a `canon.v2` with explicit FMA is a possible later contract
  that would need a golden reset (G03).
- **Rewrite licences by grade.** In `exact`, the admissible rewrites are those that keep each
  output's FP-DAG: lane permutation of independent rows, loop splitting and tiling that keep
  per-element order, hoisting exact conversions (f16/bf16→f32, small int→f32), commuting one IEEE
  add/mul *only when NaNs are canonicalised before any sink*, `x*1`, `-(-x)`, select/mask
  canonicalisation (R07). The licence `int_assoc` allows any association of an `exact_sum` whose
  bound fits the accumulator. Reassociating floats is admissible only under `real(bound)`, with a
  FPTaylor/Satire-class certificate and runtime margin checks at top-k and argmax, and it is
  labelled lossy (R07).
- **Transcendentals are specified functions:** `cr::{exp,sin,cos,…}` (correctly rounded) or
  `canon.v1::expf` (a versioned DAG of basic operations without FMA). Platform libm is reachable
  only through `foreign` with `nondet(platform)`, which the canonical profile rejects. A `parity`
  shim calling the same CRT symbols exists only for migration comparison against legacy C (G04).
  Measured motivation: UCRT itself switches between FMA3 and non-FMA3 transcendental paths at
  startup, and the two differ on 44,232 sinf inputs (G04).
- **FP environment.** The runtime asserts the default MXCSR on every worker at start. `fpenv` is
  banned outside the audited runtime, which closes the "C hook enables FTZ" hole (G02, revisit
  D2-A).

### 3.7 Staging and load-time specialisation

- **Two stages.** `comptime` evaluation plus `Code<T>` quotes, which are generative only in v1
  (MetaOCaml guarantee: well-typed generators emit well-typed code). Schedules are comptime values,
  so a Python script or an agent can produce them as data (R09).
- **Binding-time types:** `@bind(build | load | call(buckets))`. Specialisation keys must be
  finite (enums, bounded integers, fixed records). Specialising on unbounded data or on *weight
  values* is rejected, because compiling weights into instructions is a rejected idea (revisit
  REJECT).
- **AOT by default.** `mithc specialize model.hearth --profile this-pc` produces residual C or
  objects keyed by `(model header hash, target)` into a variant store. At load, the runtime picks
  the variant whose key matches, and otherwise falls back to the generic build. A lockstep check
  proves or tests the residual bit-identical to the generic path. Copy-and-patch JIT (W^X,
  `FlushInstructionCache`) is an optional later tier. Hearth therefore needs no compiler at
  runtime.
- **Honest expectation [inference]:** specialisation helps fixed-trip-count prefill and attention
  loops, and helps decode little, since decode is bandwidth-bound. It is gated on a cheap go/no-go
  experiment that folds the Qwen3 config into C and measures (revisit "Binding-time types").

### 3.8 Modules and packages

- Each file is a module. `pub` controls visibility. `mith.toml` is Cargo-shaped and declares
  per-package grants (`unsafe = ["mithrt.platform"]`, `foreign = [...]`), module ownership and the
  edition.
- **Sealed modules** (`spec`, `golden`, `oracle`, `profile`) are hash-locked in `mith.lock`. A
  change needs a signed Gatekeeper attestation checked against the base lock, as Hearth's ADR-0009
  does for goldens. Oracle-provenance rule: a change set may not touch both an oracle and the code
  it judges (R11 GOV).
- **`abi` blocks** generate the C header, ctypes/cffi bindings and layout tests from one source,
  with mandatory `struct_size`/version fields. That makes the class of bug where a ctypes mirror
  drifted into an 8-byte overflow impossible (R11).
- **`@decision("ADR-0004")` on constants** produces a drift diagnostic when the value disagrees
  with the referenced decision record. Hearth's heat decay is 0.9 in code but 0.995 in ADR-0004
  (R11).
- Editions are additive. `mithc fix` migrates code, and a migration must preserve the corpus
  bit-exactly (R01).

---

## 4. Compiler pipeline and IRs

```
 .mith text --parse--> CST (lossless; anchors for edits/format)
            --lower--> AST --resolve/type/effect/cap/refine/bind--> Core   [hash per definition]
 Core(kernel) ---------> KIR  exact op-DAG per output + Order + integer subterms (+ ranges)
 Core(flow/store) -----> FIR  actors, tiers, residency, I/O, hint ports, placement
 KIR x Schedule -------> LIR  loops, buffers in memories, instr calls (Exo-style), each step checked
 FIR x Profile --------> cost signature (symbolic) --@bind(load)--> numeric floor
 LIR --isel--> C11 (intrinsics, strict FP) | XIR (x86 SSA keyed by XED iclass) | PIR (PTX subset)
 object code --decode(XED)--> XIR' --T1/T2--> witness            ("lift-and-match")
```

**IRs.**
- **Core.** The typed core calculus: MVS, second-class references, linear kinds, effect rows as
  capability parameters, refinement obligations and binding times. The executable Lean 4
  reference semantics is defined over Core, and the Rust implementation is differential-tested
  against it (design-inputs).
- **KIR (Kernel IR).** An index-typed tensor meaning whose per-output FP expression DAG is
  explicit. `Order` nodes fix float association, and `exact_sum` nodes carry integer ranges. KIR
  is *the* semantics object that T1 compares against.
- **FIR (Flow IR).** Kahn-style actors with FIFOs, tier-typed loads, `deterministic` regions, hint
  ports and placements. Several handlers interpret one FIR (revisit D2-C, "one flow, many
  handlers"): the engine handler (code), the simulator handler (trace replay with the *same*
  policy code, as hearth.sim does today), the byte handler (unit-typed bytes per tier) and the
  timing handler (max-plus critical path).
- **LIR (Loop IR).** An Exo-shaped scheduled program: loops, buffers annotated with memories
  (zmm, L1-tile, DRAM, VRAM, shared memory), `@instr` calls whose bodies are *generated from the
  semantics table*. That closes Exo's unchecked-`@instr` gap by construction (G02, R05).
- **XIR / PIR.** Instruction-level SSA for x86-64 (keyed by XED iclass) and for a PTX subset.
  Encoding and object emission are deterministic final steps, validated by round-tripping through
  the XED decoder.

**Schedules.** The rewrite library is borrowed from Exo's model (MIT), with the value domain
changed from reals to IEEE operations over a fixed DAG. Every rewrite carries a licence tag
(`exact`, `int_assoc`, `real`), and in `exact` mode only `exact` and `int_assoc` are available.
Legality uses Exo-style effect analysis plus affine dependence checks, with a typed escape hatch
for gathers (MoE routing, paged KV). Winning schedules are pinned per `(kernel, target profile)`
in source, as Helion does (R05).

**Cost signatures.** For each FIR or LIR node the compiler derives
`bytes{nvme, dram_rd, dram_wr, pcie_h2d, pcie_d2h, vram}`, `ops{int8_mac, f32_add, f32_mul, …}` and
`syncs{barrier, h2d_event}` as symbolic expressions in load-bound parameters (layer sizes, k,
dtypes) and runtime observables (hit rates per tier). Evaluating them against a machine profile
gives two numbers per node: the floor `T_floor = max_ρ bytes_ρ / BW_ρ` (perfect overlap) and a
serial estimate `T_serial = Σ_ρ bytes_ρ/BW_ρ + compute + syncs·latency`. This generalises Hearth's
physics equation (brief), including the DRAM write that every DMA'd NVMe miss costs (R08 §7).
Bounds carry soundness tiers: `phys` (datasheet peak), `emp` (audited measurement) and `est`
(model). Only `phys` and audited `emp` bounds may prune a search or quarantine a result
(revisit D3-ii).

**Incremental queries.** mithc is a salsa-style query database whose keys are content hashes:
`parse(file)`, `core(def)`, `effects(def)`, `kir(def)`, `apply(def, schedule, target)`,
`t1(def, target)`, `cost(def, profile)`, `specialize(def, model_hash)`. Results that are expensive
to recompute (T1 witnesses, SMT certificates, measurements) persist in the evidence ledger under
the same keys. An edit invalidates exactly the dependent closure, and stale evidence is
reported, never silently reused.

**Backends and their sequencing.**

| Stage | Backend | Scope | Correctness evidence for kernels |
|---|---|---|---|
| B0 | Rust Core interpreter + Lean reference interpreter | everything (comptime, tests, oracles) | reference |
| B1 | **C11 emitter**: `#pragma STDC FP_CONTRACT OFF`, MSVC `/fp:precise`, GCC/Clang `-ffp-contract=off`, no fast-math; intrinsics for scheduled kernels | all of Mithril; Hearth port target | validated(LIR) + tested(binary, hash corpus) |
| B1.5 | **Lift-and-match**: decode the C compiler's kernel objects with XED, lift to XIR', run T1/T2 against KIR | kernels emitted by MSVC/Clang/GCC | validated(machine code) when every iclass is in the table; otherwise downgraded to tested |
| B2 | **PTX expert tier** (sm_120), loaded with `cuModuleLoadData` from `nvcuda.dll`, explicit `.rn` | Q4/Q8/MXFP4 expert GEMV, activation quantisation, norms, SwiGLU, rank combine | validated(PTX) + tested(cross-device hash corpus) |
| B3 | **x86-64 direct kernel emitter** (LIR→XIR→COFF/ELF) | staged-kernel subset | validated(machine code) by construction |
| B4 | Copy-and-patch JIT | optional load-time variants | as B3 |
| B5 | NEON via C11 (macOS arm64 CI), later an emitter with ASL-derived semantics | kernels | tested, later validated |
| — | LLVM | optional, never required | — |

**DEVIATION (sequencing).** `design-inputs.md` orders the backends C11 → direct x86 emitter →
PTX. I insert B1.5 and make the order of B2 and B3 conditional. The direct emitter's main value
is that T1 applies to the code actually executed. Decode is bandwidth-bound, so the emitter is
not expected to beat MSVC's intrinsics code by much [inference]. Lift-and-match delivers the same
evidence for C-compiled kernels, *if* the compilers only emit instructions covered by the
semantics table. G02 estimates Hearth's kernels at about 105 instruction forms (74 mnemonics),
only about 10 of them FP-sensitive. **Rule:** if lift-and-match validates at least 95% of the
kernel set at M1, the PTX expert tier comes before the direct emitter, because the GPU tier is
the largest lossless lever on this machine (SIMULATED 3.6–4.8x for in-RAM MoE, G03). If coverage
is below 95%, the direct emitter goes first, as in the inputs. Either way, the decision is
recorded in the ledger as a scoped verdict with a resurrection trigger.

---

## 5. Verification and evidence

**Trusted computing base (kept small and attacked on purpose):**
1. `mithcheck` T1: the FP-DAG matcher, the audited IEEE-exact rewrite list and the lockstep-loop
   rule. Lean proves the rewrite list and loop rule sound (R07).
2. The **x86 semantics table**: hand-written, keyed by XED iclass, with an explicit FP-environment
   layer (MXCSR.RC, forced DAZ/FTZ, NaN selection, MAX/MIN operand order, integer-indefinite
   results). Each entry is fuzz-validated on Zen 5 with SNaN/QNaN in each operand position, ±0,
   subnormals and every mask pattern, with Bochs as a second oracle. Estimated at 25–40
   parameterised families and 1.5–3k lines (G02). Intel's XML is not used, because of its licence
   (G02). A smaller PTX table covers `add/mul.rn.f32`, `cvt`, `dp4a` and shuffles.
3. **T2 certificate checking.** SMT (bit-vector) answers are accepted only with checkable
   certificates (LRAT/DRAT, or `bv_decide`-style), verified by a small checker.
4. **Core type/effect checker** (Rust), differential-tested against the Lean reference.
5. **mithrt's audited Unsafe layer.**
6. **The sealed evaluator** (§8).

Untrusted: schedulers, autoschedulers, LLM output, e-graph extraction, cost models, simulators
and, for T1-validated kernels, the C compiler.

**Checker tiers.**

| Tier | Checks | Speed | Failure mode |
|---|---|---|---|
| T0 | types, effects, capabilities, binding times, second-class references, `timing_only` confinement | ms, every edit | sound |
| T1 | realisation FP-DAG equals the KIR DAG modulo the audited exact rewrites; lockstep loops | near-linear in unrolled DAG size (R07) | sound, incomplete; "unknown" means reject |
| T2 | integer/bit-vector side conditions: ranges, no saturation, exact int→float, alignment, VNNI bias | sub-second QF_BV per obligation (R07) | certificate or reject |
| T3 | tolerance certificates for `real(bound)`, runtime margin checks at discontinuities | opt-in | labelled lossy |
| Contracts | `requires/ensures/invariant` discharged by SMT (Dafny-style); optional Lean through a Comparator-style gate | seconds | timeout means unknown |
| Tests | property tests, mutation testing integrated with the type system (AST-aware, incremental, equivalent mutants pruned by e-graph) | — | graded by mutation score |

**Evidence lattice and ledger.** `proof > validated > tested > measured(hw) > assumed`. A claim is
`(subject_hash, property, spec_hash, grade, evidence_kind, toolchain_hash, target,
hw_fingerprint, origin, signer)`. Correctness properties admit `proof`, `validated` and `tested`;
performance properties admit only `measured`, or `simulated`/`predicted` explicitly labelled as
such. Fact Plane policies (Datalog) state requirements. For example: every kernel reachable from
a `pub output` needs `isa_identity ≥ validated`, or `tested` with mutation score ≥ 0.9 plus the
hash corpus; every `deterministic(...)` region needs its named test passing at the current hash;
no number in `docs/` lacks an origin. **Negative results are first-class.** A tombstone records a
scoped verdict, a failure class (hardware, tooling, search, effort, evaluation, composition,
scale, fundamental-under-assumption), the incumbent's search budget and machine-checkable
resurrection triggers (R02). Hearth's "multi-layer lookahead REJECTED for this model, drive and
cache sizes" becomes a class-H tombstone that is retriggered by a second NVMe, a VRAM tier or
prediction-aware eviction.

**Spec ownership (separation of powers).** Roles get disjoint write capabilities: Author (specs),
Builder (implementations), Prover (proofs), Adversary (mutants, counterexamples) and Gatekeeper
(sealing, promotion). Spec strength is graded two-sided: mutation kill rate on sealed mutant
pools (commit-reveal), vacuity checks and Clover-style consistency. `assume` and `sorry` are
forbidden in accepted code. This addresses the measured bottleneck that LLM-written specs are
sound and complete only about half the time (R03).

---

## 6. Runtime and targets

**CPU ISA tiers as data.** Target profiles name feature sets, not syntax: `x86-64-v3` (+AVX-VNNI
for Intel client), `avx512{f,bw,vl,vnni,bf16,vbmi}` (Zen 4/5), AVX10.2 (pending), AMX (Xeon only;
Zen 5 has none), NEON (+SME on Apple). The cost model chooses vector width, so mobile Zen 5 and
Intel client chips do not get "always zmm". Under `canon.v1`, however, the *lane count* of a float
reduction is part of the meaning: 16 lanes map to one zmm, two ymm or a half-warp (G03, R08).
Dispatch uses cpuid plus XCR0 at load, through an atomically published table. There are no P/E
paths (R08).

**Memory and storage tiers** (machine profile `this-pc`, all origin-typed):

| Tier | Figure | Origin |
|---|---|---|
| DRAM read, all-core | ~77 GB/s (96 GB/s theoretical) | measured AIDA64 class (R08) |
| DRAM read, one CCD | 64 GB/s cap | documented Infinity Fabric limit (R08) |
| NVMe 990 PRO | 7.16 GB/s demand peak, 6.72 GB/s prefetch | measured, Hearth (R11) |
| PCIe 5.0 x16 | ~63 GB/s theoretical, ~50 GB/s planning | spec / simulator assumption (G03) |
| VRAM RTX 5070 | 672 GB/s, 12 GiB (~1.5 GB used by the display) | datasheet; usage measured (G03) |
| USB HDD | cold archive only | — |

Profiles are produced by `mithc profile measure` (STREAM per CCD and all-core, NVMe at
request-size and queue-depth grid, PCIe H2D/D2H, VRAM GEMV) inside the evaluator, so the floors
the compiler prints rest on measurements of *this* box.

**Threads.** A persistent spin-then-sleep pool (no OpenMP, whose 5–10 µs per region was ruled
out), with Hearth's measured heuristics ported. `par for` uses dynamic chunk claiming over
provably disjoint writes. Decode threads must span both CCDs to exceed 64 GB/s. Barriers per layer
are counted in cost signatures (R08, R11).

**I/O.** `File.read_at` lowers to Windows OVERLAPPED + `FILE_FLAG_NO_BUFFERING` (a synchronous
handle measured 0.62 vs 5.73 GB/s, R11) and to POSIX `pread` + `O_DIRECT`/`F_NOCACHE` with a
buffered fallback. Demand and prefetch queues are separate; at least one reader is reserved for
demand; reads are chunked and cancellable (revisit D2-B). io_uring and IoRing come later, with
ownership-transfer buffer APIs (G05). SPDK is not used.

**GPU tier (owner-gated).** Device arenas in VRAM, a hot-expert cache, the backbone resident. Cold
experts are computed on the CPU, never uploaded per token: PCIe 5.0 x16 is slower than the CPU
reading its own DRAM (R08, G03). Experts are bit-exact across devices: exact int32 block sums
(dp4a; INT8 `mma` only after its exactness on sm_120 is confirmed, G03 open question 3), then the
ordered `add.rn` epilogue. The serial chain is n/64 adds: 32 for d = 2048 (G03).

**Determinism scopes.** `cross_device` (the canon core, bit-identical on every target in the
build's target set), `device(t)` (for example tensor-core float MMA or vendor libraries, opt-in
with their own goldens), `schedule_dependent` (allowed only in values that never reach a
`pub output`). Determinism is defined as `logits = f(binary, version_root, inputs, kv_policy)`
with ISA and device removed from the list once `cross_device` holds (R12, G03).

**Hot-swap.** Versioned dispatch tables are published with a release store at token boundaries
(Hearth's `hx_store_tick`). The old version is reclaimed when its `Frozen` refcount drops; there is
no epoch reclamation API in v1 (G05). Weights are immutable and content-addressed
(`Weights<V>`); typed overlays (SlabReplace, LowRank, AddExpert, …) are committed at token
boundaries; sequences are pinned to their start version (R12). No self-modifying code, INVD or
CMPXCHG16B tricks.

**Honest performance targets for Hearth (roofline arithmetic).**

| Workload | Bytes/token by tier | Floor | Hearth C today | Mithril target |
|---|---|---|---|---|
| Qwen3-30B-A3B, Q4 experts + Q8 dense ("cfg B"), in RAM, short context | DRAM 2.27 GB (R08 §7.1) | 29.5 ms → 33.9 tok/s at 77 GB/s [inference, R08] | 19–22 tok/s measured (≈43–50 GB/s effective) | 26–29 tok/s (≈59–65 GB/s effective) [inference; R08 says ~45→~65 GB/s gives 28–29] |
| same, 4K context | DRAM 2.67 GB (+0.40 GB KV) | 28.8 tok/s at 77 GB/s | — | ≥ C, bit-identical |
| Qwen3-30B-A3B, NVMe-bound, 2 GiB cache | NVMe ~401–402 MB/token measured; MIN floor ~193 MB/token [inference, low-medium] | clairvoyant ceiling ~20 tok/s [inference, revisit D2-B] | 13.02 tok/s measured | 15–17 tok/s at ≤ 1.15x MIN bytes [inference] |
| Prefill, 512 tokens | compute-bound region; ridge ~213 ops/byte (R08) | ~2,700 tok/s at peak [inference] | 345–433 tok/s measured (R11) | ≥ 1.5x C, bit-identical [inference]; attention value pass already shown 18 → 94 GMAC/s bit-identically (measured prototype, R11) |
| Kimi-K2-class, 40 GB cache, one 990 PRO | NVMe 2.25–5.62 GB/token at h = 0.8–0.5; DRAM 11.37 GB backbone | 3.41 tok/s all-in-DRAM ceiling (R08 §7.4) | 0.55–0.83 tok/s, synthetic container (measured worst case) | inside the 0.8–2.9 band [inference]; no claim above 3.4 |
| Qwen3-30B-A3B with GPU tier (dense + hot experts in VRAM) | VRAM ~1.26 GB dense + hot experts; DRAM cold experts | expert term alone, all experts on CPU: 0.963 GB/77 GB/s = 12.5 ms → 80 tok/s [inference] | — (no GPU path) | SIMULATED 23 → 112 tok/s (G03); gate: measured ≥ 2x CPU-only, bit-identical |

Two cautions. First, every target is a hypothesis to be measured under INV-HONEST, not a
promise. Second, any measurement that beats a `phys` floor (for example implied DRAM traffic above
96 GB/s) is quarantined as an evaluator bug or a hack (§8).

---

## 7. Agent protocol and toolchain

**The loop an agent runs.**

1. **Orient.** `mithc pack --tier 0` (≤ 8 KB, always in context): grammar summary, keywords, the
   false-friend table, about 10 snippets, the `canon.v1` rules, the effect list, commands and the
   diagnostic format. Tier 1 (5–15k tokens) is loaded with `mithc guide <topic>`. Tier 2 is the
   retrieved manual (G01).
2. **Find, don't invent.** `mithc query --type "&[Q4] -> f32" --effects "{}"` returns existing
   definitions by type and effect, so agents do not hallucinate APIs. `mithc hole ?name` returns
   the expected type, in-scope bindings, relevant definitions and applicable schedules
   (Hazel/ChatLSP, R03).
3. **Edit by anchor.** `mithc edit --def q4_matvec#9f3a --old "<snippet>" --new "<snippet>"`. The
   anchor is name plus definition hash. A stale hash returns `StaleAnchor` with the current text.
   There are no line numbers. An edit is accepted only after an atomic parse and T0 gate, and the
   response lists the new hash and the evidence it invalidated (R03, revisit "Agent Edit Protocol").
4. **Check.** `mithc check --json` in milliseconds. Diagnostics are root-cause grouped, with
   cascades folded (RustAssistant's grouping took GPT-3.5 from 4.97% to 44.76% fixed, R03). Each
   carries a stable code, an anchor span, expected vs actual, the violated rule, any false-friend
   note, and fixes rated by applicability with the obligations they create:

   ```json
   {"code":"E-NUM-031","severity":"error","anchor":"q4_dot#77c1/n18",
    "message":"schedule step 'split-accumulator' reassociates a float chain",
    "rule":"canon.v1 §1: block order is sequential",
    "false_friend":"C compilers vectorise this under -ffast-math; Mithril never does in exact",
    "fixes":[{"applicability":"machine","edit":{"anchor":"sched/q4_dot.zen5#s3","replace":"tile r by 16 as lanes(f32x16);"},
              "obligations":["t1","bench"]}]}
   ```
5. **Prove.** `mithc prove` discharges contracts, T1 and T2 and writes the evidence.
6. **Explain cost.** `mithc explain q4_matvec --profile this-pc --shape rows=768,n=2048` reports
   bytes per tier, ops, the binding resource, the floor, achieved time (once measured) and the
   fraction of roof. For this shape (one Qwen3 expert projection): 768 × 32 blocks × 34 B =
   835,584 B, a floor of 10.9 µs at 77 GB/s, DRAM-bound [inference].
7. **Benchmark.** `mithc bench` submits a job to the sealed evaluator and gets back
   `Measured<Time>{profile, load, ci95, baseline}` plus a plausibility verdict. Agents never time
   code themselves.
8. **Hand over.** `mithc handover` writes the session manifest: commands actually run, evidence
   added or invalidated, open holes, typed measurements, new tombstones, next tasks. It replaces
   hand-written handover prose (R11 GOV).

**Surfaces.** CLI with `--json` everywhere; an LSP (holes, hover with effect rows and cost);
an MCP server exposing `check`, `hole`, `query`, `edit`, `explain`, `cost`, `prove`, `bench`
(async), `ledger.query` and `handover`; SARIF 2.1.0; an AGENTS.md snippet; `mithc lift` for
C11/Rust subsets into `.mith` (SPEAC/LLMLift pattern, the cold-start escape hatch, G01). Where
Mithril owns the logits (Hearth-hosted local models), grammar- and type-constrained decoding
applies: type constraints cut compile errors by 52–75% (R03). It is off by default under
INV-LOSSLESS-DEFAULT.

**Cold-start measurement from day one.** A Mithril MultiPL-E, a false-friend probe set, a card-size
sweep and sealed Hearth-shaped tasks, with C11 and Rust control arms. The metrics are verified
pass@1 and the *checker-accepted-but-wrong* rate (revisit "Cold-agent comprehension harness").

---

## 8. The Forge and its trust model

The Forge is the toolchain's built-in search loop. Its novelty is in *what* it searches and *how
correctness is established*, not in the proposer.

**What it searches, and the certificate each space carries.**

| Space | Example | Certified by (once) | Per-candidate cost |
|---|---|---|---|
| Schedules (`exact`) | AVX-512 attention value pass, prefill tiling | licence-checked rewrites + T1/T2 | check + bench |
| `timing_only` policies | eviction, prefetch issue rules, mirror choice | effect check + store-core certificate O1–O5 | simulate + bench |
| Placements | which experts live in VRAM; CPU vs GPU for misses | `cross_device` determinism of placed kernels | simulate + bench |
| Lossless layouts | row-interleaved repacks, MXFP4 integer path | format round-trip proof + T1 on derived kernels | check + bench |
| Lossy variants | lower-bit cold experts, reduced k | *separate lane*: `approx` grade, statistical quality gates; never a default | full gates |
| Compiler rewrite rules | new exact rewrites proposed Ruler-style | proof obligation (SMT/Lean) before admission | proof |
| Cost-model heuristics | autoscheduler priors | none needed (never decides correctness) | bench |
| Language editions | new construct or stdlib API | RFC + cold-agent harness + human ADR | agent study |

**Objective: physics-normalised.** Fitness is measured time per correct token (or per kernel
call) on a named profile, reported as a fraction of the `phys`/`emp` floor, with gap attribution.
For cache policy that means the MIN bytes floor, a windowed AGL stall LP, Demand-MIN, and
attribution of the gap to eviction, wrong prefetch and lateness (revisit D2-B). Hit rate is a
descriptor, never the objective: depth-4 lookahead raised hits from 73% to 86% but cut decode
from 13.0 to 10.0 tok/s (measured, design-inputs). Replay-conditioned lower bounds prune
candidates. In the simulated pilot they pruned 16–41% per cache size, where physics-only rooflines
pruned none of 144 (revisit D3-ii).

**Archive.** The archive is the evidence ledger. QD niches are machine profile × model family ×
tier regime (in-RAM, NVMe-bound, GPU-hybrid) × shape bucket. Descriptors are bytes per token by
tier, stall fraction, arithmetic intensity, vector width and determinism scope. Each cell keeps an
elite plus its tombstones. Selection is HGM-style Thompson sampling over clades; exact duplicates
are rejected for free by normalisation and e-graphs before any LLM or benchmark spend (R01, R02).

**Trust model.**
- Only checker-accepted candidates are scored. A checker "unknown" or timeout counts as rejection
  (R07).
- The evaluator is built by a frozen bootstrap toolchain, pinned by hash, and hidden from
  proposers. A candidate compiler never builds the evaluator or the verifier (trusting-trust,
  R01).
- Candidates run in a separate process under a Windows Job Object (or a WSL2 container), with no
  network, read-only goldens and supervisor-held limits. An in-process sandbox is not enough
  (R01: STOP, AI Scientist).
- The runtime owns the clock, joins every thread, stream and I/O request before stopping it,
  controls warm and cold state (CLFLUSHOPT sweeps on Windows, since WBINVD is ring 0, R08),
  poisons fresh allocations, requires materialised outputs and hashes them. This blocks the
  documented hacks: unwatched-stream timing (32.8% of CUDA-L1 kernels), `torch.empty` reuse,
  overwritten timers (30.4% of o3 RE-Bench runs) (R01, R05).
- **Physics plausibility gate.** A result that beats a `phys` floor (bandwidth, or Belady for
  policies without prefetch) is quarantined as an evaluator bug or a hack.
- **Statistics.** Speed claims need anytime-valid e-values against an interleaved same-machine
  baseline. Noisy claims, such as the current llama.cpp comparison, are refused until the evidence
  is sufficient (revisit "Statistical Gödel gate").
- Held-out traces and prompts, split by model and prompt family. Simulator scores stay labelled
  SIMULATED until calibrated against the engine (R01, R02).
- **Human promotion** for any default, any `canon` change and any language edition (ADR).

**Going further than DGM and AlphaEvolve.**
1. *Certify spaces, not candidates.* DGM validates every child empirically, and its evaluators were
   gamed (faked logs, removed markers). Here the classes of change that cannot alter output are
   certified once, and search inside them needs only performance evidence. This is the tractable
   Gödel machine that six revisit branches converged on.
2. *Physics-normalised fitness with gap attribution.* This gives a stopping rule ("within 5% of
   floor"), a hack detector ("above floor") and a diagnosis ("eviction, not lateness").
3. *Exact counterfactual replay.* Bit-determinism makes archived trajectories replayable, so
   meta-level selection policies are tested offline before they steer live runs (R01).
4. *Scoped tombstones with triggers.* When the hardware changes (GPU admitted, second NVMe), dormant
   clades and rejected ideas are re-scored automatically (R02).
5. *The bytes term is searchable.* Formats, placements and policies sit in the search space, not
   only instruction sequences. On a memory-bound engine that is where the speed is (R06).

---

## 9. The Hearth port

**Approach.** A strangler fig behind Hearth's internal `hx_*.h` seams. Mithril emits C11 with the
same `hx_*` symbols, so Mithril modules replace C objects one at a time inside `hearth_core`.
`hearth-c-ref` (a frozen C build) is kept permanently as a differential oracle (R11).

**Stages and acceptance gates.** Every stage also requires the C tests, the golden suite and the
cross-binary hash corpus, with interleaved load-gated A/B runs for performance.

| Stage | Scope | Acceptance gates |
|---|---|---|
| 0 Freeze and instrument | tag the base; build `hearth-c-ref`; measure the machine profile; generate the cross-binary corpus: SHA-256 of logits and routes for every `make_tiny` architecture × {F32, Q4} × ISA, big_q4, 512 real-Qwen3 decode steps, `hearth_quantize` bytes, `hearth_matmul` across ISA/T/row splits/NaN-inf; record CRT identity | corpus reproducible across two runs; ADR-0010 (specified transcendentals) landed *before* the corpus if maintainers accept it (G04) |
| 1 Leaf numerics | half conversions, `quant.c` formats and quantisers, scalar kernels, then AVX2, then AVX-512 from one meaning plus three schedules | `test_quant` (117,681 checks); golden ISA/batch identity; quantiser byte diff vs C (closes the oracle hole); single-thread AVX-512 Q4 ≥ 69.6 GB/s L2-resident; T1 validates or names each unmatched step |
| 2 Container parser | `modelfile.c` as `format` descriptions → generated parser (EverParse-style) | `test_modelfile` fuzz cases; golden malformed-file test; identical accept/reject and parsed configs vs C on a generated fuzz corpus; zero user-level Unsafe |
| 3 Pool | persistent pool, `par for` | `test_pool`; dispatch latency within noise of ~0.75 µs at 16 threads, including WSL2 crowded-pool cases; permutation-scheduler tests pass |
| 4 Store logic | `store.c` as MVS + `timing_only` hint ports, calling the existing C platform functions through the audited-layer interface | `test_platform`, `test_store`; golden scheduling independence; ≥ 7 GB/s demand reads on the 990 PRO; chaos suite (random/anti-LRU/out-of-range/over-budget/FTZ hook/drifted mirror) kills 100% of seeded core mutants |
| 5 Forward pass | `model.c` as flows and kernels, specialised at load | full golden suite via `check_golden.py --run`; hash corpus; 512-step real-model decode hashes; tok/s parity at 2/4/8 GiB caches and 512/2048-token prefill (e-value, interleaved) |
| 6 API | export `hearth.h` exactly (19 functions, same struct layouts) from an `abi` block | Python toolkit and ctypes ABI-mirror tests pass unchanged; retire the C core only after maintainer sign-off |
| 6b Platform | replace `platform_win.c`/`platform_posix.c` with mithrt's audited layer, last | `test_platform`; direct-I/O ≥ 7 GB/s; large-page arenas; timed waits never return early; TSan-clean pool/store |
| 7 Physics wins | bytes-first policies via the Forge, AVX-512 attention value pass, tiled VNNI prefill, native MXFP4, then the GPU expert tier | each win measured vs `hearth-c-ref` on `this-pc`, bit-identical (or in the lossy lane with quality gates) |

R11 ports the platform together with the store (its Stage 4); G05 argues the platform is the
riskiest port and should come last. I reconcile them: store *logic* moves at Stage 4 because its
gates must pass before the forward pass, but it calls the existing C platform functions through
the audited-layer interface. The platform itself is replaced last (Stage 6b), once its exact needs
are known.

**Constitutional decisions for Hearth's maintainers** (each needs an ADR; several trip the
decision circuit breaker):

1. **INV-DEP and ADR-0001.** A Mithril core conflicts with "C11 + OS APIs only". Recommendation:
   check the generated C11 into the repo and build it with only a C compiler. Mithril then acts as
   a code generator, which keeps the spirit of INV-DEP during the port. Decide later whether
   `mithc` may become a build dependency.
2. **ADR-0010, specified transcendentals.** Replace "platform libm" in NUMERICS §4 with `cr`
   sinf/cosf (128 calls per token) and either `cr` or `canon.v1` expf. Measured motivation: UCRT's
   FMA3 dispatch; a no-FMA canon expf prototype was bit-identical across scalar, AVX2 and AVX-512
   over all 2^32 inputs, and its AVX-512 version ran at 0.204 ns/element against 1.12 for scalar
   UCRT expf (measured, G04). No golden
   re-lock is needed, because goldens are relational. This enables a cross-OS hash gate (INV-DET-4).
3. **Is the RTX 5070 in scope for compute?** Does `nvcuda.dll` count as an OS API, or must the GPU
   path use Vulkan? Should the display move to the iGPU to free ~1.5 GB of VRAM? (G03)
4. **INV-DET-3 across devices** for the canon core, and INV-DET-1 extended to list device
   placement as an axis. Tighten GPU acceptance to "bit-identical for any op with dynamic
   placement" (G03).
5. **MXFP4 in canon.v1.1.** MXFP4 uses 32-element scale blocks while activation blocks are 64.
   The order needs a decision, for example two sub-block terms added in order: `acc += isum_a·(sa·dx);
   acc += isum_b·(sb·dx)`. Decide before the first MXFP4 golden.
6. **Attention accumulation.** Keep sequential-in-t for CPU, or redefine it as fixed chunks so
   long-context GPU attention can parallelise without breaking identity (G03). Needed only if
   attention moves to the GPU.
7. **FORMAT v2 per-slab content hashes.** These make mirrors lossless by construction. Today
   `check_mirror` samples only the first page (G05), which conflicts with INV-DET-1.
8. **An MXCSR invariant**: pool threads run with default MXCSR, checked at worker start (G02).
9. **ABI `struct_size` fields** on `hearth_options` and `hearth_stats` before they grow again (R11).
10. **Which heat-decay value is normative**: 0.9 in `hx_model.h` or 0.995 in ADR-0004 and
    `hx_store.h` (R11).
11. **A maintainer-owned cross-binary hash corpus** as a sealed golden layer. The current goldens
    are relational and tolerance-based, so a port could change outputs silently without it (R11).

**Live Hearth defects to report, not fix** (found by the research; design-inputs): the mirror
check samples only the first page; `hx_store_heat` returns an unguarded pointer (a data race); the
`read_errors` ABI break wrote past the ctypes buffer; MXCSR is never asserted; heat decay differs
between code and ADR; the server has storage channels (`cached_tokens`, `/stats`,
unauthenticated `/health`); and with `n_io=1` a demand read can wait behind a prefetch.

---

## 10. Roadmap

Milestones are ordered by dependency. Durations are deliberately omitted; gates decide.

| # | Milestone | Deliverable | Measurable gate | Pre-registered kill criterion |
|---|---|---|---|---|
| M0 | Surface and harness | Lark grammar; Tier-0/Tier-1 cards; Core checker in Rust with the Lean reference interpreter skeleton; C11 emitter for the scalar subset; cold-agent harness with C11/Rust control arms | frontier agents with Tier 0+1 reach verified pass@1 ≥ 0.8x the Rust arm on a 100-task Mithril MultiPL-E slice; false-friend probe error rate ≤ the Rust arm's | VP@1 < 0.6x Rust after two card revisions → drop the standalone surface for a Rust subset with attributes (a design-inputs change, needs owner sign-off) |
| M1 | Kernel slice | KIR, Exo-derived schedules with an IEEE-exact mode, x86 semantics table (Hearth's ~105 forms, fuzzed on Zen 5), T1/T2, lift-and-match; Hearth `quant*.c` regenerated from one meaning | all Stage-1 gates; T1 validates ≥ 95% of generated kernels with ≤ 40 audited rewrites; zero T1 false positives under a mutant-kernel campaign | any T1 false positive that cannot be traced to a table bug and fixed → stop and redesign T1; < 80% coverage after the rewrite budget → kernels drop to tested grade, and the direct emitter becomes mandatory |
| M2 | Formats and parser | `format` types (Q4, Q8, BF16/F16, MXFP4); derived pack/unpack/dot; generated container parser | Stage-2 gates; MXFP4 round trip exact against checkpoint bytes; MXFP4 integer path derived automatically, with no hand-written kernel | derived kernels > 10% slower than hand-scheduled ones after one tuning pass → formats stay declarative for parsing only, and kernels are scheduled by hand |
| M3 | Store, pool, `timing_only` | MVS store, pool, audited mithrt layer, hint ports, simulator handler sharing policy code | Stage-3 and Stage-4 gates; 100% of 100+ generated policies bit-identical on goldens (P1); audited Unsafe ≤ 1,500 lines per OS | the store needs user-level Unsafe, or the audited layer exceeds 1,500 lines per OS → revisit the memory model (regions/capsules) before going on |
| M4 | Full engine and ABI | forward pass, load-time specialisation, `hearth.h` export | Stage-5 and Stage-6 gates; decode and prefill ≥ 1.00x C at e-value α = 0.05 | Mithril-Hearth < 0.95x C on decode after one optimisation pass → do not retire C; publish the tombstone with the gap attribution |
| M5 | Physics wins under exactness | Forge on policies (oracle-scored), AVX-512 attention value pass, tiled VNNI prefill | in-RAM Qwen3 cfg B ≥ 26 tok/s measured; NVMe-bound 2 GiB ≥ 15 tok/s at ≤ 1.15x MIN bytes; prefill 2048 ≥ 1.5x C; all bit-identical | no Forge candidate beats the incumbent by ≥ 5% on held-out traces within the pre-set budget → tombstone the policy line and stop spending |
| M6 | GPU expert tier (owner-gated) | PIR/PTX backend, VRAM tier, placement plans, cross-device hash corpus | canonical expert GEMV on sm_120 ≥ 0.7x llama.cpp MMVQ on the same card; logits hash-identical across placements; end-to-end ≥ 2x CPU-only measured | canonical GEMV < 0.5x MMVQ, or cross-device identity fails irreparably → the GPU stays a `device(t)` opt-in lane with its own goldens |
| M7 | Maintainability verdict and self-host decision | cold-agent study: seeded Hearth tasks in Mithril vs C; Forge at the compiler-rule level | agents in Mithril-Hearth reach higher VP@1 at ≤ cost than in C-Hearth | not better → Mithril stays Hearth's kernel/generator language; no self-hosting and no general-purpose expansion |

---

## 11. Non-goals and top risks

**Non-goals (v1).** Visual-generation primitives (R13); a general GPU backend; LLVM as a
requirement; µop-level superoptimisation as the main path; formal speed proofs on out-of-order
CPUs; self-modifying code, INVD or CMPXCHG16B swaps; SPDK by default; compiling weights into
instructions; online supercompilation; SMT "bounded loss divergence"; projectional or JSON-wrapped
agent I/O; a Python-embedded primary surface; GC, unwinding, multi-shot continuations, macros,
inheritance, general dependent types; P/E-core paths; training beyond overlays; timing-based
approximation by default; implicit spec-to-code regeneration.

**Top risks and mitigations.**

| Risk | Why it matters | Mitigation |
|---|---|---|
| Cold start: agents write Mithril badly | training-data prior dominates (R03, G01) | Rust-shaped surface, Tier-0 card, holes, grouped diagnostics, lifter; M0 kill criterion |
| T1 incompleteness on horizontal-reduction shuffles | kernels drop to tested grade | lockstep rule, targeted rewrites, Lean-checked list; downgrade is explicit, not silent (R07) |
| Semantics-table errors (AMD vs Intel NaN behaviour) | a wrong table makes T1 unsound | Zen 5 fuzzing per entry, Bochs second oracle, the hash corpus as an independent check (G02) |
| C compiler emits instructions outside the table | lift-and-match coverage falls | census at M1; direct emitter as fallback; downgrade to tested |
| Windows perf parity with MSVC intrinsics and the measured pool heuristics | a slower port is not adopted | interleaved A/B with e-values; port heuristics verbatim first |
| Constitutional conflict (INV-DEP, ADR-0001) | the port cannot merge | checked-in generated C; ADR drafted at Stage 0 |
| Evaluator hacking by agents | false wins | sealed evaluator, runtime clock, poisoned allocations, physics gates, human promotion |
| Simulator miscalibration | wrong search direction (the lookahead reversal) | SIMULATED labels; engine measurement before promotion |
| Libm identity during migration | the port cannot match C bit for bit | ADR-0010 first; otherwise a parity shim and one re-baseline (G04) |
| GPU: WDDM timeouts, compositor VRAM use, INT8 `mma` exactness unverified | GPU tier slips or loses exactness | dp4a first; the decisive sm_120 GEMV experiment before any backend work (G03) |
| Scope explosion (one maintainer, many layers) | nothing ships | milestones gated on Hearth stages; kill criteria |
| Moving target (17 uncommitted files, open CI failures, R11) | the port chases a changing base | Stage-0 freeze and tag |

---

## 12. Novel versus prior art

**What I believe is new here** (as far as the dossiers' searches reached; several noted that
their web-search budgets ran out, so "new" means "not found"):

1. **Exactness grades with overflow-proved integer accumulators as reorder licences, unified
   across CPU SIMD and GPU.** This gives bit-exact expert GEMV across Zen 5 and sm_120 and makes
   CPU-vs-GPU placement output-invariant. G03 found no engine whose output is independent of VRAM
   contents; batch-invariance work gives same-device determinism only.
2. **Bytes-per-tier cost signatures** that are symbolic at build time, numeric at load time and
   measured at run time, typed by unit and origin, with soundness tiers deciding which bounds may
   prune or quarantine (R08, revisit D2-C/D3-ii). Rooflines exist as analysis tools; making them
   part of each definition's checked interface and of the search loop's fitness is the step.
3. **Lift-and-match.** T1 checks *the C compiler's object code* against the exact meaning using an
   owned, silicon-fuzzed AVX-512 FP semantics table. No public AVX-512 FP semantics exists (G02).
   KLEE-FP did the matching for 51 OpenCV SSE kernels in 2011, but not over compiler output
   against a separate meaning (R07).
4. **`timing_only` hint ports with a one-time demonic-hint core certificate.** This makes every
   type-correct cache and prefetch policy bit-identical by construction (revisit D2-A).
5. **Declarative block-scaled format types** that derive integer-exact dot meanings and their
   overflow proofs (R06; ggml and KleidiAI hand-write per-format kernels).
6. **A ledger that unifies proofs, validations, tests, measurements, prune certificates and
   tombstones with resurrection triggers**, and the Forge objective normalised by physics with
   gap attribution (R02, revisit INSIGHTS).

**What I deliberately took from prior art.** Schedules: Halide's split, Exo's checked rewrites and
C output (MIT), Helion's pinned configs (R05). Verification: KLEE-FP matching; Alive2, CryptOpt
and VeriISLE translation validation (R07); s2n-bignum's co-simulated ISA model and XED iclass keys
(G02); Dafny-style contracts (R03). Language: Koka/Effekt/Austral effects-as-capabilities, salsa
queries, Unison content addressing, Terra/MetaOCaml/Zig staging, DyC binding times (R09); Hylo
MVS, Swift `Mutex`, OxCaml capsules (G05); EverParse-style formats (revisit S11). Agent tooling:
Hazel/ChatLSP holes, rustc JSON diagnostics, SARIF (R03, R04). Numerics: CORE-MATH and LLVM-libc
correctly rounded functions (G04); Thinking Machines' batch-invariance diagnosis (G03). Search:
DGM's archive, HGM clades, MAP-Elites (R01, R02); Albers–Garg–Leonardi and Belady/MIN (revisit
D2-B). Above all, Hearth's own canonical numerics, golden gate, mutation testing and INV-HONEST,
which were already a working prototype of most of this discipline.

**Open questions this proposal does not settle.** The size of the audited rewrite list needed for
zero false positives on Hearth's shuffles; INT8 `mma` exactness on sm_120; the canonical GEMV's
speed on sm_120 relative to MMVQ (the decisive GPU number); whether lift-and-match reaches 95%
coverage on MSVC output; the MXFP4 and attention-chunk orders for canon.v1.1; whether `canon.v2`
(explicit FMA) is worth a golden reset; the Tier-0 card size optimum for a whole new language; and
whether the owner admits the GPU and amends INV-DEP.
