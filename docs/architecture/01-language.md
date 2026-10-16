# 01 — Language

*Detailed architecture document, 2026-10-11. Audience: AI agents and the project owner. Parent:
[ARCHITECTURE §5](../ARCHITECTURE.md#5-the-language-at-a-glance). Decisions are cited as DR-xxx
([DECISIONS](../DECISIONS.md)), dossiers as [R09], [G05] or [RV: node] ([research/](../research/)),
proposals as [P3 §3.1] ([design/proposals/](../design/proposals/)).*

**Summary.** This is the language reference of the Mithril architecture. It sets the surface policy:
the subset rule of DR-002, under which code that parses as Rust means what Rust means, unsupported
Rust is rejected by name, and every new concept arrives with a new keyword or type. It also sets the
Lark-first grammar and the Rust-coincident typed holes (DR-003). It specifies the types, including a
static-dispatch trait subset (DR-005), and the memory model (DR-004): mutable value semantics,
second-class references, Hylo-style projections, a non-escaping kind for closures and iterator
adapters, linear resources, and `Send`/`Sync`. It defines effect rows as *authority* (DR-006) and
grades as *fidelity and determinism*, lists the numeric rules visible at the surface (DR-013,
DR-014), and gives minimal refinements together with the honest cost of having no Dafny-class verifier
(DR-011, DR-012). Staging, modules, `mith.lock`, and deterministic trap and error semantics follow,
including the lowest-index rule for `par for` and the fallback rule for policy traps. It ends with
the core calculus sketch that all three judges found missing from every proposal: MCore's
judgement forms, how rows and grades are typed and composed, and precise statements of the four
theorems Mithril must prove (progress and preservation, capability confinement, `timing_only`
noninterference, determinism), each with its evidence grade today. Compute, trust, toolchain and
agent-protocol material is summarised and linked, not repeated.

**Contents**

1. [Conventions](#1-conventions)
2. [Surface policy: the subset rule](#2-surface-policy-the-subset-rule)
3. [Lexical and grammar policy; typed holes](#3-lexical-and-grammar-policy-typed-holes)
4. [Types](#4-types)
5. [Memory model](#5-memory-model)
6. [Effects and capabilities](#6-effects-and-capabilities)
7. [Grades: fidelity and determinism](#7-grades-fidelity-and-determinism)
8. [Numerics at the surface](#8-numerics-at-the-surface)
9. [Contracts, refinements and specs](#9-contracts-refinements-and-specs)
10. [Staging](#10-staging)
11. [Modules, packages, `mith.lock`, editions](#11-modules-packages-mithlock-editions)
12. [Traps, errors and fail domains](#12-traps-errors-and-fail-domains)
13. [Core calculus sketch: MCore](#13-core-calculus-sketch-mcore)
14. [Open questions and reviewer notes](#14-open-questions-and-reviewer-notes)
15. [Sources](#15-sources)

---

## 1. Conventions

- **All syntax here is provisional pending the Surface Lab** ([05](05-agent-protocol.md)). The
  semantics are decided; the spelling is measured.
- **Status labels** follow [ROADMAP §1](../ROADMAP.md) rule 7: **v0** (in the `mithc` that ports
  Hearth, M1–M5), **v1** (present by Edition 1, M6–M7), **later** (planned after M7), **reserved**
  (in the types and schema but not producible), and **by-trigger** (added only when its register
  trigger fires; IDs D-nn in [ROADMAP §9](../ROADMAP.md)).
- **Numbers** carry a label: measured, simulated, [inference] or [target]. Diagnostic codes such as
  `E-REF-ESCAPE` are illustrative. They are stabilised in [05](05-agent-protocol.md).
- **Snippets** use the `mith` fence. `// E-…` comments show what the checker reports.

Where each language check lives in the pipeline (IR names as in [04](04-toolchain.md)):

```text
 .mith ─► Syntax   lossless CST, conformant to the one Lark grammar                (§3)
       ─► HIR      names resolved; todo!() holes are typed nodes                  (§3.3)
       ─► THIR     types; kinds Local/Linear/Send/Sync; loans; effect rows;        (§4–§9)
                   grades; refinement obligations; trap sites
       ─► MIR = MCore  capabilities explicit, moves explicit, trap sites explicit  (§13)
            │          interpreted by mithi, the differential oracle (DR-010)
            ├─► C11 (B1) and the object audit                                     ([04])
            └─► KIR    kernel meanings, layouts, schedule application              ([02])
```

---

## 2. Surface policy: the subset rule

### 2.1 The rule (DR-002) **[v0]**

Mithril source is standalone `.mith` text with a Rust-shaped surface. Every construct falls into
exactly one of three classes:

- **C, coincident.** It parses as Rust and means what Rust means.
- **Dc, rejected.** It is a Rust form that Mithril does not support. The checker rejects it with a
  named diagnostic that states the prior meaning, the Mithril rule and a fix.
- **D, new.** It carries a meaning Rust lacks. It is introduced by a new keyword, a new type, a new
  std name or a mandatory argument.

There is no fourth class: **nothing is reinterpreted.** The evidence for this rule is strong.
False friends (familiar syntax, changed meaning) are the costliest case for language models:

- One changed rule, 1-based indexing, cut GPT-4 from 82.5% to 40.5% on the affected HumanEval items.
- Rust API changes that keep the signature but change behaviour scored 38.0%, against 65.8% for newly
  stabilised APIs [G01 F2].
- Mojo and MoonBit, the two most agent-aware young languages, both ship long correction guides
  against parent-language habits [G01 F2.4].
- Python-embedded surfaces do worse than standalone ones: 29.8–62.0% for Python-embedded HDLs
  against 72.2% for Verilog [G01 F4].

A conservative, familiar surface whose new concepts are loud and keyword-led is the evidence-backed
choice [G01], [R03 §3].

**The parent is pinned.** "Rust meaning" is the documented behaviour of one Rust release and edition,
recorded in each Mithril edition. The Rust project adopted the Ferrocene Language Specification in
2025 [R09 §3]. Where Rust leaves a behaviour open, Mithril picks one behaviour Rust permits and says
so. Examples: Rust lets integer overflow panic in debug builds and wrap in release; Mithril picks
trapping in every build (§12.1). Rust leaves transcendental precision unspecified; Mithril's std uses
`cr` by default and requires a named `cr::` or `canon_v1::` function in exact code (§8). Rust lets
`f32::max` return either zero for `(+0.0, −0.0)`; the edition's Surface Map pins one (FF-NANMAX). A
choice Rust permits is coincident, not a reinterpretation. A change in Rust's own
behaviour is a Surface Map event (§2.3) and may move a construct between classes.

**Restriction is not reinterpretation.** Where the two languages overlap, Mithril accepts a strict
subset of Rust programs, and it rejects loudly. Mithril accepts a program that Rust would reject only
when that program uses a D construct.

### 2.2 Classes are indexed by grade context **[v0]**

Whether a familiar form is a false friend depends on where it appears [RV: D3-i]. Take bare float
`.sum()`. It has a single meaning, a sequential left fold. But in exact-graded code, an agent who
wrote it almost certainly meant the canonical 16-lane tree. So it is **C** in default code and
**Dc** in exact contexts (DR-013). In the other direction, constructs whose bit-level behaviour
matters elsewhere are harmless in `timing_only` code, where output bits cannot depend on them
[P1 §3.1]. An expression's grade context is computed from the requirements at its sinks (§7.3):
`kernel fn` bodies, claim slots, and export outputs declared exact.

### 2.3 Governed by measurement, not taste **[v0 pilot, v1 full]**

The class and spelling of each construct are decided in the Surface Lab [RV: D3-i]. Each construct
is tested in four arms:

- **F:** the familiar form.
- **M:** the familiar stem plus a mandatory disambiguator, as in `topk(k, Ties::LowerIndex, Nan::Last)`.
- **A:** deliberately unfamiliar ASCII.
- **O:** an obfuscated control.

The arms are scored by VP@1 and tokens per verified pass, on sealed tasks whose oracles kill every
known false-friend mutant. The chosen arm minimises cost subject to a pre-registered cap on
false-friend incidence. A content-addressed **Surface Map** records, for each construct, how it
prints and parses, its traps, its priors and its witness inputs, and it must obey laws such as
parse∘print = id. The harness, the statistics and the measured rate at which the subset rejects
idiomatic agent Rust are in [05](05-agent-protocol.md). The kill criteria for the whole standalone
surface are in DR-017. This is N6 in [ARCHITECTURE §1.3](../ARCHITECTURE.md): a construct survives
only if fresh agents measurably do better with it.

### 2.4 Keywords, attributes and contextual reservation **[v0]**

- **New meaning gets a keyword:** `kernel`, `schedule`, `format`, `policy`, `spec`, `claim`, `uses`,
  `requires`, `ensures`, `invariant`, `linear`, `deterministic`, `par` (before `for`), `comptime`
  (v0) and `export abi` (v0, M1).
- **Item keywords from the compute and Forge layers** (DR-002: every new concept is keyword-led):
  `flow` (v0, M4–M5), `store`, `hint port` and `certificate` (v0, M4)
  ([02 §12](02-compute.md#12-flows-and-policies)), and `evolve slot` (v0, M4; F1 campaigns at M6)
  ([06 §2.1](06-forge.md)). Clause words inside a `store` or `evolve slot` item (`fallback`,
  `validate`, `budget`, `fuel`, `reserve`, `off_lock`, `evidence`, `seed`, `objective`, `promote`,
  …) are reserved only inside that item, as schedule primitives are. All of these belong in the
  Tier 0 keyword list and the Lark `item` production ([05](05-agent-protocol.md)).
- **Added checking or metadata gets a Rust-style attribute:** `#[range(..)]`, `#[grade(..)]`,
  `#[decision("ADR-…")]`, `#[closure_budget(N)]`. An attribute may add checks; it never changes
  what accepted code means.
- **Every new keyword is contextual.** It is reserved only where an item or clause begins, so Rust
  code that uses `spec`, `format` or `policy` as identifiers still parses with its Rust meaning.
  `format!` stays the std macro.
- **Typed holes need neither** (§3.3).

### 2.5 Seed false-friend table **[v0]**

This table seeds the Tier 0 card ([05](05-agent-protocol.md)). The rows come from Hearth's real
bit-exact traps [RV: D3-i], [P1 §3.1], [P5 §3.1]. The Surface Lab may change spellings, never the
rule.

| ID | Rust form | Prior meaning | Mithril rule | Class (by context) |
|---|---|---|---|---|
| FF-FMA | `a * b + c` on floats | Rust: two roundings. GCC contracts by default outside ISO modes | Two roundings, never contracted | C (the C lifter flags C sources) |
| FF-MULADD | `a.mul_add(b, c)` | Rust: one rounding | Same. The only fused form; `canon.v1` meanings contain none | C |
| FF-SUM | float `.sum()`, `.product()`, `fold` | Rust: sequential left fold | Rust meaning by default; rejected in exact-graded and logits-path code (DR-013) | C default · Dc exact |
| FF-TIES | `max_by`, `min_by`, `min_by_key` over floats | `max_by` returns the *last* maximum; `f32` is not `Ord` | Rust meaning by default; rejected in exact contexts → `topk(k, Ties::LowerIndex, Nan::Last)` | C default, C in `timing_only` · Dc exact; `topk` D |
| FF-NANMAX | `f32::max`, `f32::min` | Rust: returns the non-NaN operand; for `(+0.0, −0.0)` either zero may be returned, and signalling-NaN handling follows the platform | Rust meaning, with the open cases pinned in the edition's Surface Map: `max(±0, ∓0) = +0.0` and `min(±0, ∓0) = −0.0` in either operand order; a signalling NaN is treated as a quiet NaN (the other operand is returned); two NaN operands give the canonical NaN. The x86 MAXPS operand rule only as `simd::maxps` | C (pinned choice); `simd::maxps` D |
| FF-ROUND | `x.round()` | Rust: ties away from zero. C `nearbyintf`: ties to even | Rust meaning; Hearth quantisers call `round_ties_even()` | C |
| FF-CAST | `x as i32` from `f32` | Rust: saturating, NaN → 0. C: undefined out of range | Rust meaning | C |
| FF-OVF | integer `+ - *` overflow | Rust: panic in debug, wrap in release | Trap in every build (Rust's debug meaning); `wrapping_*` is explicit; kernels must prove absence (DR-011) | C (Dc in kernels if unprovable) |
| FF-EXP | `x.exp()`, `x.sin()`, … | Platform libm; precision unspecified | Default code: std `cr` (a valid implementation of Rust's unspecified-precision contract). Exact code: rejected → `cr::expf` or `canon_v1::expf` (DR-014) | C default · Dc exact |
| FF-POWI | `x.powi(n)` | Rust: may use a different rounding sequence from `powf`; no particular result guaranteed | Default code: std's one rounding sequence, recorded in the Surface Map. Exact code: rejected → explicit multiplications in a fixed order, or `cr::powf` | C default · Dc exact |
| FF-F16 | arithmetic on `f16` | Unstable Rust `f16`: binary16 arithmetic | Storage only; widen with `.to_f32()` (exact) | Dc; `bf16` is D |
| FF-REF | `&T` in a field; a returned reference outside the projection rule; any lifetime `'a` | Allowed, with lifetimes | Rejected: references are second-class (§5.2) | Dc |
| FF-LOCAL | storing or returning a closure or adapter that captures a borrow | Allowed with lifetimes or `impl Trait + '_` | Rejected: non-escaping kind (§5.4) | Dc |
| FF-DYN | `dyn Trait`, `Box<dyn Fn>`, specialisation | Dynamic dispatch | Not in v1 (D-01) | Dc |
| FF-ASYNC | `async`/`await`, `macro_rules!`, proc macros | Futures; user macros | Not in v1 (D-01); use scoped services and the pool | Dc |
| FF-CELL | `Cell`, `RefCell`, `Rc`, `static mut`, unscoped `thread::spawn` | Interior mutability; ambient state | Rejected → `Mutex<T>::with_lock`, `Frozen<T>`, scoped threads (§5.8) | Dc |
| FF-UNSAFE | `unsafe {}` | Local opt-in | Only in packages granted `unsafe` in `mith.toml` | Dc outside grants |
| FF-CLOCK | `Instant::now()` | Ambient clock | Needs `uses { time }`. Forbidden in kernels, policies and Forge candidates | Dc there |
| FF-HOLE | `todo!("name")` | Panics when reached | Same, plus a typed hole (§3.3) | C |
| FF-Q4 | "a Q4 block" | llama.cpp Q4_0: 32 elements, high nibble at j+16 | Hearth Q4: 64 elements, high nibble at j+32, reachable only through a `format` | D |

---

## 3. Lexical and grammar policy; typed holes

### 3.1 One normative grammar **[v0]**

- **One normative Lark grammar** fits OpenAI's CFG-tool restrictions: explicit whitespace
  terminals, no reliance on `%ignore`, and bounded terminals [R03 §5, R03-2].
- **Keyword-first, LL-friendly productions for every D item.** Prefix parsing then stays
  incremental for the LSP, for `mithc`'s prefix-check API, and for logit masks on Hearth-hosted
  models ([05](05-agent-protocol.md)) [G01].
- **Whitespace-insensitive, ASCII-only, no glyphs.** The token-economy evidence supports only
  modest savings from surface tricks [R03-11]. Rust's own disambiguation rules (turbofish, struct
  literals in conditions) are inherited as C.
- **One parser of record.** The hand-written, error-recovering parser produces the lossless CST and
  is differentially fuzzed against the Lark grammar on the corpus. `mithc fmt` is canonical and
  enforced, and edits are formatted before anchors are matched ([05](05-agent-protocol.md)).
- **Size [target]:** the grammar must be printable inside Tier 1, a few thousand tokens [G01].

### 3.2 Identity **[v0]**

A definition is identified by the hash of its normalised HIR. Locals are alpha-renamed, and
references are replaced by the interface hashes of their targets. A rename or a body edit therefore
does not invalidate callers' type checks, and names are metadata. The query database and the ledger
keys built on these hashes are in [04](04-toolchain.md) and [03](03-trust.md).

### 3.3 Typed holes (DR-003) **[v0]**

```mith
let score = todo!("eviction_score");   // typed hole: `mithc hole eviction_score` returns context
```

- **Meaning.** Rust's meaning coincides: `todo!` panics when reached. In Mithril, reaching a hole is
  a trap at site `hole("eviction_score")` (§12).
- **In HIR the hole is a typed node.** A program with holes type-checks and runs under `mithi`.
- **The hole query.** `mithc hole eviction_score --json` returns:
  - the expected type;
  - the bindings in scope, with their types and grades;
  - the obligations at the hole: ranges, the required row and the required grade;
  - candidate functions from type-directed search;
  - the false-friend rows relevant to the hole's grade context.

  Typed-hole context is among the best-measured agent levers [R03 §6].
- **Why not `?name`.** It collides with Rust's postfix `?`, which would make it a grammar-level false
  friend.
- **Holes block release.** No correctness claim can be admitted for a definition whose closure
  contains a hole, and release profiles refuse to build it. `mithc propagate` turns broken
  dependents into holes ([05](05-agent-protocol.md)).

---

## 4. Types

| Family | Content | Status |
|---|---|---|
| Scalars | `i8..i64`, `u8..u64`, `isize`/`usize`, `bool`, `f32`, `f64` with Rust meaning. `f16` is storage-only (arithmetic is Dc). `bf16` is a new storage type (D). Widening to `f32` is exact | v0 |
| Storage codes | `nibbles<..>`, `e2m1`, `e8m0` and similar exist only inside `format` items, never as arithmetic types. Real engines lower sub-byte codes through int8 dots or lookup tables [R09], [P5 §3.3] | v0 |
| Aggregates | `struct`, `enum`, tuples, `[T; N]`, `Option`, `Result`; slices `&[T]`/`&mut [T]` (second-class); `#[repr(C)]` and static size assertions | v0 |
| Generics | Type parameters and const generics (`SlabBuf<4096>`, `Aligned<u64, 4096>`), monomorphised; `comptime` value parameters (§10) | v0 |
| Traits | Static-dispatch subset with Rust meaning (below) | v0 |
| SIMD | `Simd<T, N>`, `Mask<N>` and an `x86::` namespace generated from the semantics table, so only table-covered instructions exist [G02]. Allowed only in `schedule` lowerings and `#[target(..)]` functions ([02](02-compute.md)) | v0 |
| Formats | Declarative block formats with derived size, accessors, pack/unpack and integer views ([02](02-compute.md)) | v0 |
| Quantities | `Quantity<Unit, Origin>`, INV-HONEST as a type (below) | v0 |
| Capabilities | `Root`, `Fs`, `File<Mode>`, `BlobFile`, `Blob<T>`, `Spawner`, `Clock`. No public constructors (§6.2) | v0 |
| `std_platform` | `Mutex<T>`, `Condvar`, `Arena`, `SlabBuf`, `Frozen<T>`, `Hint<T>`, scoped threads and services (§5.8) | v0 |
| Residency, devices | `resident<T, Tier>`, `streamed<T, Tier>` and `cached<T, Tier, budget>` on flow values ([02 §14](02-compute.md#14-tiers-and-placement)); the VRAM tier is reserved | v0 / reserved |

**Inference** works inside bodies only. Public signatures (types and rows) are mandatory, and there
is no implicit `Any` [R03-3].

**Traits (DR-005).** The subset keeps Rust's meaning:

- **Included:** trait declarations, impls and bounds, associated types and consts, default methods,
  operator traits, `Iterator`, Rust's coherence and orphan rules, and `impl Trait` in argument and
  return position (static dispatch, subject to the non-escaping rule of §5.4).
- **Std derives** (`Clone`, `Copy`, `PartialEq`, `Eq`, `Debug`, `Hash`, `Default`) are C. They are
  std, not user macros.
- **Rejected (Dc, deferral D-01):** `dyn`, specialisation, `async`, and user macros.

Agents write traits constantly. Rejecting them would be a frequent Dc cost that X1 would wrongly
blame on the language. Iterator methods that merely *look* like trait methods would themselves be a
false-friend surface [P1 §3.3]. X1 runs a traits-on and a traits-off arm, so the cost of the subset
is measured (DR-005).

```mith
trait Dequant {
    fn scale(&self) -> f32;
    fn elem(&self, i: usize) -> i32;
}

fn first_value<B: Dequant>(b: &B) -> f32 {
    b.scale() * (b.elem(0) as f32)         // static dispatch, monomorphised
}
// fn first_dyn(b: &dyn Dequant) -> f32 { … }   // E-DYN: no dynamic dispatch in v1; use a generic
```

**Formats.** A format is a specification from which the compiler derives code. This one is
canonical:

```mith
/// Hearth Q4 weight block (FORMAT.md, hx_quant.h): 64 elements in 34 bytes.
format BlockQ4 {
    d: f16,                          // block scale
    q: nibbles<64, offset = 8>,      // byte j: low nibble = elem j, high nibble = elem j+32
}
// Derived by the compiler: size == 34 (checked), elem(i) -> i32 with #[range(-8..=7)],
// pack/unpack, and the integer view used by exact dot products.
```

**Quantities.** `Origin ∈ {Measured{hw, …}, Simulated{model}, Estimated, Assumed}` mirrors the
performance grades of [03](03-trust.md). Dimension errors, such as Hearth's `/tok` against `*tok`
class, are type errors. Quantities of different origins combine only through an explicit conversion
that names the weaker origin.

```mith
let bw: Quantity<GBps, Measured> = profile.dram_read_all_core;
// Formatting prints value + origin ("77 GB/s, measured, <hw fingerprint>"); an unlabelled
// number does not format. Simulated and measured quantities do not mix without conversion.
```

---

## 5. Memory model

The model is DR-004, built on R09's recommendation and G05's study of `store.c`: values first,
second-class references, projections, a non-escaping kind, linear resources, and `Send`/`Sync`.
There is no GC, no lifetime annotation, no region calculus, and no Hylo `inout`/`sink` spelling.

### 5.1 Values first **[v0]**

- **Mutable value semantics.** By-value parameters move with Rust meaning, `Copy` types copy, and
  `.clone()` is explicit.
- **One binding per mutable value.** A mutable value is reachable through exactly one binding at a
  time, as in Hylo [R09 §3].
- **No hidden copies.** Large by-value results lower to out-parameters, and hot paths have no
  hidden `memcpy` above N bytes ([04](04-toolchain.md), DR-027).

### 5.2 Second-class references **[v0]**

`&T` and `&mut T` keep Rust's spelling and Rust's meaning for as long as they exist. They may be
parameters and locals. They may not be:

- stored in struct or enum fields, statics, or escaping closures;
- returned, except by projection (§5.3).

Lifetimes do not exist, and `'a` is Dc. The consequence is the point of the design. **Every loan
created in a function body ends before that body returns, except a projection result, which is a
loan on the caller's own place.** Borrow checking is therefore intraprocedural and non-lexical, like
Rust's NLL, and no signature ever mentions a lifetime.

This buys three things:

- **A smaller spec and card.** No lifetimes, no variance [R09].
- **No-alias facts for all safe code, by construction.** These license `restrict` in the C11
  lowering ([04](04-toolchain.md), DR-027).
- **A class of race rejected outright.** Hearth's `hx_store_heat()` hands out an unguarded pointer
  into lock-protected state, a C11 data race [G05 §1]. In Mithril that program does not type-check
  (§5.8).

### 5.3 Projections **[v0]**

A **projection** is a function that returns a reference derived from exactly one borrowed
parameter. That parameter is selected by Rust's lifetime-elision rules: the receiver if there is one,
otherwise the single reference parameter. More generally, the return type's borrowed parts may be
wrapped in std containers, as in `Option<&T>` or `(&T, usize)`.

The meaning coincides with Rust's, because Rust's elided lifetime ties the result to the same
parameter. Mithril adds only the second-class restriction on how the caller uses the result. Hylo's
subscripts are the model [R09 §3], [P3 §3.1]. Slicing (`&w[a..b]`) and indexing are built-in
projections.

```mith
impl<B> Matrix<B> {
    /// A projection: the slice borrows from `self` (Rust lifetime elision). The caller may use it
    /// in its own body; nobody can store it in a field or return it further except by projection.
    pub fn row(&self, r: usize) -> &[B]
        requires r < self.rows()
        ensures result.len() == self.blocks_per_row()
    {
        &self.blocks[r * self.blocks_per_row .. (r + 1) * self.blocks_per_row]
    }
}
// struct RowCache { last: &[BlockQ4] }            // E-REF-FIELD: references are second-class;
//                                                 //   store a row index instead
// fn pick(a: &[f32], b: &[f32]) -> &[f32]         // E-REF-ESCAPE: no receiver and two borrowed
//                                                 //   parameters; return an index or a copy
```

The canonical kernel uses this projection inside a `par for`. Each `w.row(r)` is a loan on `w` that
ends at the call. In kernels, the `requires` is discharged statically, so projections in hot loops
cost no runtime check (DR-011; [02](02-compute.md) for hot-loop lowering). `row`'s `ensures`
together with `a.len() == w.blocks_per_row()` discharges `q4_row_dot`'s `requires w.len() == a.len()`
(§8) at the call; without them that obligation is unprovable, which DR-011 makes a compile error in
kernel code. The snippet is [ARCHITECTURE §5.3](../ARCHITECTURE.md#53-canonical-snippets)'s:

```mith
kernel fn q4_matvec(w: &Matrix<BlockQ4>, a: &[ActQ8], y: &mut [f32])
    requires y.len() == w.rows() && a.len() == w.blocks_per_row()
{
    par for r in 0..w.rows() {      // disjoint writes: each y[r] written by exactly one iteration
        y[r] = q4_row_dot(w.row(r), a);   // w.row(r) is a projection, not a stored borrow
    }
}
```

### 5.4 The non-escaping kind **[v0]**

**The problem.** All five proposals used iterator chains and closures that capture `&self`. Under
second-class references these values store borrows, and no proposal said how they type
[ARCHITECTURE §5.2]. Without an answer, much ordinary Rust would become Dc and feed DR-017's kill
gate.

**The answer is a derived kind, `Local`.** A type is `Local` if any of these holds:

- it is a reference;
- it contains a `Local` component;
- it is a closure that captures anything by reference, or captures a `Local` value.

Std views and iterator adapters over `Local` values are `Local`. So are std containers (`Option`,
`Result`, tuples, arrays) instantiated at a `Local` type.

**Local values obey the reference rules.** They may be parameters and locals, may be passed
downward freely, and are consumed in the body that holds them. They may never be stored in a field,
a static or an escaping closure. They may be returned only in two cases:

- (a) by projection (§5.3);
- (b) by a std adapter whose result loan is the union of its `Local` arguments' loans. These
  signatures are compiler-known and live in std.

User-declared structs and enums are never `Local` in v0. **Generics cannot reintroduce `Local`.**
Every type parameter of a user struct, enum, impl or function carries an implicit non-`Local`
bound, like Swift's default `Escapable`. Only std signatures may write `T: ?Local` (as `Option`,
`Result`, tuples, arrays and the adapters do). Instantiating a user generic at a `Local` type is
`E-LOCAL-INSTANTIATE`. Without this rule, `struct Wrapper<T> { x: T }` at `T = &U` would store a
reference in a field. And `fn first<T>(a: T, b: T) -> T` at `T = &[f32]` would return a borrow of
one of two parameters, which is the `pick` case of §5.3: the caller's loan tracking would credit the
result to one source, and so let it write to the other place while the result is live.

There is one exception, so that the common "pass a closure to my helper" idiom stays C. A user
function's type parameter bounded by a std closure trait (`Fn`, `FnMut`, `FnOnce`), including
`impl Fn…` in argument position, may be instantiated at a `Local` closure. Two conditions apply: the
parameter occurs in exactly one parameter type (as `F`, `&F` or `&mut F`), and it does not occur in
the return type, directly or through an associated type. The body is then checked with that
parameter treated as `Local`. It may be called and passed downward, never stored or returned, and it
cannot be smuggled into another parameter's place, since no other parameter type mentions it.

User-defined `Local` types and user-written `Local`-returning generics are **by-trigger**. The
trigger is a measured share of rejected idiomatic agent Rust attributable to `E-LOCAL-RETURN` or
`E-LOCAL-INSTANTIATE` ([05](05-agent-protocol.md)). The closest deployed precedent is Swift's
non-escapable types (SE-0446) [G05 §2].

```mith
use std::cmp::Reverse;

/// The closures capture `heat` by reference, so they are Local; so is the adapter chain.
/// They are consumed here. The result, an owned Option<SlotId>, escapes freely.
fn hottest(slots: &[SlotView], heat: &[u32]) -> Option<SlotId> {
    slots.iter()
        .filter(|s| !s.pinned)
        .max_by_key(|s| (heat[s.idx], Reverse(s.idx)))   // integer key; ties -> lowest idx
        .map(|s| s.id)
}

// fn live(slots: &[SlotView]) -> impl Iterator<Item = &SlotView> {   // E-LOCAL-RETURN: the
//     slots.iter().filter(|s| s.refs > 0)                          // adapter borrows `slots`;
// }                                         // take a closure parameter or return Vec<SlotId>
```

### 5.5 Closures and contextual effect polymorphism **[v0]**

Second-class closures solve the second half of the judges' gap, effect polymorphism, at no extra
cost:

- **The row of a `Local` closure body is charged to the enclosing function where the closure is
  created.** Higher-order std functions (`map`, `filter`, `with_lock`) therefore need no effect
  variables.
- **Why this is sound.** A `Local` closure can run only inside the dynamic extent of the function
  that created it, and that function's row already contains the closure's authority. This is
  Effekt's design: effects as capabilities, functions second-class by default, and explicit
  "boxing" for first-class ones [R09 §1].
- **Escaping closures** capture only non-`Local` values, by move. They carry their row in their
  type. Only `std_platform`'s `spawn` and `service` APIs accept them, and those APIs record every
  captured capability in the capability audit graph [G05 C.3].
- **No row variables in v0.** User effect polymorphism arrives with user effects and handlers, if
  ever (D-02).

### 5.6 Linear resources **[v0]**

A `linear struct` value must be consumed exactly once on every non-trapping path:

- Consuming means moving it into a call, returning it, or destructuring it.
- An implicit drop is `E-LINEAR-DROP`.
- A struct with a linear field is linear. Linear and `Copy` are mutually exclusive.
- Std linear types include `SlabBuf`, `Lease`, join handles and in-flight I/O tokens.
- What happens to linear values on a trap path is in §12.4.

```mith
linear struct Lease { slot: SlotId, slab: Frozen<SlabBuf> }    // dropping one: E-LINEAR-DROP

impl Lease {
    pub fn bytes(&self) -> &[u8] { self.slab.bytes() }          // a projection of `self`
}

/// `Store::lease` and `Store::release` are deterministic boundaries inside the store (§6.4).
fn expert_step(store: &Store, id: ExpertId, x: &[f32], y: &mut [f32]) -> Result<(), IoError>
    uses { io, spawn }
{
    let lease = store.lease(id)?;     // linear: must be consumed on every normal path
    ffn_q4(lease.bytes(), x, y);      // the loan on `lease` ends after this call
    store.release(lease);             // consumes it; deleting this line is E-LINEAR-DROP
    Ok(())
}
```

### 5.7 `Send` and `Sync` **[v0]**

These are the derived transfer and share kinds, with Rust's names and Rust's meaning [G05 C.1–2]:

- **Who may assert them.** They are derived structurally. Only `std_platform` may assert them by
  hand.
- **`par for` bodies.** Shared captures must be `Sync`. Written or moved element types must be
  `Send`.
- **`spawn` and `service`.** Moved captures must be `Send`.
- **`Local` values cross only into scoped threads** (`par for`, `scope.spawn`) that are joined
  before the scope ends. They never cross into services.
- **Std types.** `Frozen<T>` is `Send + Sync` iff `T` is. `Mutex<T>` is `Sync` iff `T: Send`.
  Capability values are `Send + Sync`.

### 5.8 Shared state and the audited `std_platform` **[v0]**

All shared mutable state goes through a small audited layer, the only place where `unsafe` appears
outside granted packages. It contains:

- `Mutex<T>` with a scoped `with_lock`, and `Condvar`;
- `Arena` split into owned 4096-aligned `SlabBuf` chunks;
- `Frozen<T>` with `into_unique`;
- `File.read_at` (OVERLAPPED + NO_BUFFERING on Windows, `pread` + O_DIRECT/F_NOCACHE on POSIX);
- scoped threads, the pool and services.

G05 found that Hearth's `store.c` is a monitor over integer-handle metadata plus a slab ownership
typestate. It is expressible over this layer with no user-level `unsafe` [inference, medium-high].
The layer is estimated at a few hundred lines per OS [inference] [G05]. Line budgets and review
rules are in [03](03-trust.md); lowering is in [04](04-toolchain.md).

```mith
/// The store's metadata is one value behind one lock. `with_lock` lends the state as `&mut` for
/// the closure only, and its result type must not be Local, so no borrow leaves the critical section.
fn note_use(st: &Mutex<StoreState>, k: ExpertKey) uses { nondet } {
    st.with_lock(|s| s.touch(k));
}
// fn heat_view(st: &Mutex<StoreState>) -> &[u32] { st.with_lock(|s| &s.heat) }
//   E-REF-ESCAPE: a borrow of locked state cannot leave `with_lock`; return a copy.
//   (Hearth's hx_store_heat() race [G05 §1], rejected by construction.)
```

**Liveness is not a typing property.** In the PLDI 2020 study of real Rust bugs, every blocking bug
was in safe code [G05]. Test builds therefore swap in a loom-style permutation scheduler under the
`std_platform` primitives ([04](04-toolchain.md)).

**Excluded from v1** [G05 C.4]: regions, cowns/BoC, Pony-style capabilities, epoch reclamation,
interior mutability, and unscoped threads. The cheapest upgrade path, if ever needed, is
OxCaml-style branded capsules held by a `Mutex`.

---

## 6. Effects and capabilities

### 6.1 Rows record authority (DR-006) **[v0]**

An effect row is written `uses { … }` after the return type and before any `requires` or
`ensures`. The set of labels is fixed. There are no user effects or handlers in v0; these are D-02,
by-trigger, and if they come they will be tail-resumptive or one-shot only [R09 §1].

| Label | Authority it grants | Taints determinism? |
|---|---|---|
| `io` | OS I/O on capability handles | No for immutable `BlobFile` reads (faults are an outcome class, §13.5). Reads of mutable sources also carry `nondet` |
| `spawn` | Create scoped threads and services | No |
| `alloc(A)` | Allocate in arena `A` | No: addresses are not observable in safe code. Exhaustion inside a `par for` body is an environment fault, not a trap (§12.3) |
| `time` | Read clocks | Clock reads also carry `nondet` |
| `foreign` | `extern "C"` calls; package grant | Only through `nondet(platform)` |
| `unsafe` | Raw pointers, unchecked operations; package grant | — |
| `fp_env` | Read or write MXCSR, rounding, FTZ/DAZ; audited runtime only | — (exact code cannot hold it) |
| `compile` | `comptime` evaluation | No |
| `lossy` | Produce output-changing approximations | Fidelity, not scope; producers are reserved |
| `nondet` | Observe scheduling, completion order, lock interleaving, user-visible atomics | **Yes**: `schedule_dependent` |
| `nondet(platform)` | Depend on platform libm or CRT behaviour | **Yes**: `device(platform)`, which is reserved, so `schedule_dependent` in v0 |
| `blob` | Read content-verified immutable bytes through `Blob<T>`, without `io` authority | No: value-deterministic |

Only `nondet` and `nondet(platform)` connect rows to grades. Every other label is authority only.
Atomics inside `Frozen` refcounts and inside `par for` work distribution are not observable, so
they carry no `nondet` [G05 D].

### 6.2 Capabilities are values rooted at entry points **[v0]**

There is one mechanism [R09 §2]. A row label is an *implicit* capability parameter, and a handle
such as `File<Direct>` or `BlobFile` is an *explicit* capability value. Exercising authority needs
both. Rows summarise the *kinds* of authority, for agents, verifiers and Forge slots. Handles
designate *which* objects. A handle that leaks into a data structure is still inert in code whose
row lacks the label.

- **Where authority enters.** `main(root: Root)` receives the root capability. Each `export abi`
  entry point declares the row it is granted, and the generated wrapper mints those capabilities
  from the audited layer. These are the only two places where authority enters a program.
- **Attenuation is ordinary code:** `root.fs().read_only(model_dir)`. There are no globals and no
  constructors for capability types outside `std_platform`, so capabilities cannot be forged
  (Theorem 2).

### 6.3 Inference and declaration **[v0]**

- **Private functions:** rows are inferred.
- **Public functions:** rows are mandatory. An inferred but undeclared label is an error, and its
  MachineApplicable fix inserts the row [P1 §3.4]. Declared rows may over-approximate.
- **Forge slots and hint ports** declare a maximum row, which is `∅` for `timing_only` policies.
- **Grants.** `unsafe`, `foreign` and `DeclareDeterministic` need package grants in `mith.toml`
  (§11).

### 6.4 The deterministic boundary **[v0, M4; needed by port stage S4]**

The canonical example:

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

`acquire` returns `Result`, as in [ARCHITECTURE §5.3](../ARCHITECTURE.md#53-canonical-snippets) and
[02 §12.1](02-compute.md#121-flows): an I/O fault surfaces as `Err`, never as a trap, as O5 and
Theorem 3 require (§13.6).

The rules (formal version: T-Det, §13.4):

1. **It removes only `nondet` from the row.** Authority stays visible: `io` and `spawn` appear in
   `acquire`'s signature. `nondet(platform)` cannot be removed, because platform dependence is a
   fact about the binary's environment, not about scheduling. It needs a specified function
   instead (DR-014).
2. **The result gets the determinism grade of a `blob` read.** Its scope is recomputed with the
   `nondet` taint masked, and its fidelity is unchanged. "Blob-grade" is a statement about the
   result's grade, not a new row entry, which is why `acquire`'s row is `{ io, spawn }`.
3. **It needs the `DeclareDeterministic` grant** for its module in `mith.toml`. A grant names exact
   modules, not prefixes: `declare_deterministic = ["store"]` covers module `store` itself, not
   `store::policy` or any other submodule. A grant never covers `policy fn` items or anything they
   call, wherever they live, and `⊢_to` rejects a `det` block outright (§13.4).
4. **It cites evidence E**: a named golden test, a model check or a proof. E joins the data-flow
   set `B` of the result and of everything computed from it (§7.2). Every downstream
   *value-level* claim, such as `deterministic(cross_device)` of an output or an end-to-end logits
   claim, takes the meet with E's grade. With the golden test above, every such downstream
   `deterministic` claim is at most `tested`, which is exactly DR-021's labelling for non-kernel
   logits-path code. With the store-core theorem as E, it is `validated`. Input-universal claims
   are not capped. A `refines` claim on an exact kernel that consumes `lease.bytes()` holds for all
   inputs, so it keeps its T1 grade (`validated` or better, as DR-021 requires).
5. **It loses its licence when E goes stale.** `E-DET-STALE` is an error in every profile that
   requires the grade, and `next:` proposes re-running E ([05](05-agent-protocol.md)).

These rules close the escape hatch that P1's signature-level `seals {Io, Spawn, Nondet}` opened.
That form hid authority from callers and never lowered the downstream grade [P2 §3.5], [panel].
G05 explains why some boundary is necessary: without one, either the logits path inherits `nondet`
or locks get an unsound exemption [G05 D].

---

## 7. Grades: fidelity and determinism

### 7.1 Two lattices on values

| Lattice | Elements (bottom ⊑ top) | Meaning | Producible |
|---|---|---|---|
| Fidelity | `exact ⊑ real(bound) ⊑ approx(profile)` | Bit-exact with respect to the specified IEEE computation, within a certified bound of it, or statistically close to it | `exact` **[v0]**; `real`, `approx` **reserved** (D-07) |
| Determinism scope | `cross_device ⊑ device(t) ⊑ schedule_dependent` | Same bits on every conforming target; same bits on targets of class `t`; may vary with scheduling | `cross_device`, `schedule_dependent` **[v0]**; `device(t)` **reserved** (D-06) |

Reserve-the-lattice [P5]: the reserved elements are present in types, schemas and the ledger from
v0 but cannot be produced, so growing into them needs no language change.

### 7.2 Composition takes the join

The result of an operation takes the **join** of three things: the grades of its operands, the
grade of the control context (`pc`), and the operation's intrinsic taint. The join is the lossier
fidelity and the less deterministic scope. Using the meet would be a sign error under this ordering
[panel, J-PL on P4].

Writes under a tainted `pc` raise the grade of the written place, the standard information-flow
discipline. D2-A borrows the Zdancewic and Myers factoring of timing [RV: D2-A]. Each graded value
also carries the set `B` of `deterministic` boundaries it depends on by data flow. The rule for
how `B` caps a claim is defined once, normatively, in [03 §3.2](03-trust.md#32-effective-grade).
This document uses it as follows:

- **Value-level claims take the meet over `B(o)`.** These are claims about particular produced
  values: `deterministic(scope)` of an output `o`, and end-to-end logits claims. Their effective
  grade is the meet of the claim's evidence, the spec-strength cap, its premises and dependencies,
  and `⨅ grade(b)` for `b ∈ B(o)`.
- **Input-universal claims are never capped by boundaries upstream of their inputs.** These are
  `refines`, `confined` and `safe`, which quantify over all inputs. A kernel's `refines` claim
  says nothing about where its input bytes came from, so a boundary that produced those bytes
  cannot weaken it. A boundary *inside* the claim's subject still counts, through the subject's
  own dependencies.

This is the data-flow reading. A call-closure reading would cap a function that merely calls
`acquire` even for a claim unrelated to the bytes it returns. It would also fail to follow bytes
that a caller acquired and passed in. [03 §3.2](03-trust.md#32-effective-grade) adopts this rule:
its boundary term is `⨅ grade(b)` for `b ∈ B(o)`, for value-level claims (deterministic, end-to-end
logits) only, and input-universal claims exclude upstream boundaries.

**Shared mutable state has a fixed grade.** The contents of `std_platform` shared-mutable types
(`Mutex<T>`, and state guarded by a `Condvar`) are not tracked flow-sensitively. Every read of them
has the declared grade `(exact, schedule_dependent, ∅)`, unless the read occurs inside a `det`
block, where T-Det masks the taint. So a value read out of a `Mutex` through `with_lock` is never
`cross_device`, even when the closure writes it into a caller's `&mut` place rather than returning
it (T-Call, §13.4).

### 7.3 Requirements, defaults and the link rule

Grades are inferred as **transfer functions**: a result's grade is the function's intrinsic taint
joined with the grades of the inputs it depends on. A function has one transfer for its return
value and one for each `&mut` parameter, because a callee can write schedule-dependent data into a
caller's place as easily as it can return it (T-Call, §13.4). `mithc outline` shows them.
Requirements are checked at sinks:

- **`kernel fn` outputs** default to `exact × cross_device`.
- **`#[grade(exact, cross_device)]`** can mark any function's outputs.
- **Profile defaults in `mith.toml`:** `fidelity = "exact"`, `allow_lossy = false`.
- **Claim slots and Forge slots** state the grade they require ([03](03-trust.md),
  [06](06-forge.md)).

**INV-LOSSLESS-DEFAULT is a link rule.** A configuration default that reaches `lossy` code is a
link error, and `approx` is never a default (DR-015).

### 7.4 Effects versus grades

| | Effects (rows) | Grades |
|---|---|---|
| Record | What code *may do* (authority) | What produced values *are* (fidelity, determinism) |
| Attached to | Functions and closures | Values, places, outcomes |
| Composition | Union | Join |
| Checked | At calls, against available capabilities | At sinks, against requirements |
| Removed by | Nothing, except `deterministic`, which removes `nondet` | `deterministic` masks only the `nondet` taint |
| Connection | `nondet` and `nondet(platform)` taint the scope | — |

---

## 8. Numerics at the surface

`canon.v1` is Hearth's NUMERICS.md made normative. Its rules:

- strict IEEE binary32, round to nearest even;
- no contraction and no reassociation;
- `mul_add` as the only fused form;
- canonical NaN `0x7fc00000` at kernel sinks, and at every other float sink of `cross_device`
  scope (checked by the NaN-canonicality rule of §13.6, Theorem 4);
- named reductions `canon::sum16`, `canon::dot16` and `canon::sum_seq`.

The full semantics, the reduction library, the cross-device rules and the canon migration protocol
are in [02](02-compute.md) and [03](03-trust.md). This section lists only what the surface shows.

- **Coincidences that matter.** Rust never contracts `a * b + c`, so the familiar form is C here and
  the false friend is C's default, which the lifter flags [RV: D3-i]. `as` casts saturate. `round()`
  rounds ties away from zero, and quantisers call `round_ties_even()`.
- **Bare float reductions (DR-013).** In exact contexts, `.sum()`, `max_by` and float `min_by_key`
  are rejected. The diagnostic offers two fixes ([05](05-agent-protocol.md) has the full format):

  ```json
  {"code":"E-FF-SUM","construct":"float Iterator::sum","you_wrote":"xs.iter().sum::<f32>()",
   "prior":"Rust: sequential left fold","context":"exact grade (kernel fn rms_scale)",
   "fixes":[{"applicability":"Safe","replace":"canon::sum_seq(xs)"},
            {"applicability":"MeaningChanging","replace":"canon::sum16(xs)",
             "invalidates":["refines(rms_scale_avx512, rms_scale)"]}]}
  ```

  `canon::sum_seq` is defined as Rust's left fold, including the start value of the pinned Rust
  reference, so the first fix is Safe. NUMERICS-style sequential accumulation from `+0.0f` is
  written as an explicit loop, as in `q4_row_dot` below. See reviewer note R4.
- **Transcendentals (DR-014).** Exact code must name `cr::expf` (correctly rounded) or
  `canon_v1::expf` (a fixed op-DAG, vectorisable and bit-identical across ISAs). Elsewhere std
  defaults to `cr`. Platform libm is reachable only through `foreign` with `nondet(platform)`.
  The measured motivation [G04]:
  - UCRT switches between FMA3 and non-FMA3 paths at startup, and the two disagree on 44,232 `sinf`
    inputs (measured).
  - A no-FMA canonical `expf` prototype ran at 0.204 ns/element on AVX-512, against 1.12 ns for
    scalar UCRT, and was bit-identical across ISAs over all 2^32 inputs (measured).

  Hearth lands ADR-0010 before the hash corpus is built ([07](07-hearth-port.md)).
- **Exact integer accumulators with overflow proofs license reordering.** This is the route to
  VNNI, and later to dp4a and INT8 tensor cores, without breaking bit identity [R07], [G03]. The
  canonical meaning:

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
```

- **The FP environment is authority.** `fp_env` cannot be held by exact code or by policies.
  Exact code can run on the caller's thread, and a host can set FTZ/DAZ per thread or process-wide.
  So every `export abi` and `hx_*` entry **sets** the default MXCSR on entry and restores the
  caller's value on exit, and pool workers set and assert the default at start
  ([ARCHITECTURE §6.3](../ARCHITECTURE.md), [04 §9.2](04-toolchain.md)). Every T1 certificate
  records "default MXCSR" as a precondition checked at entry: a runtime-checked trust-base entry,
  not an axiom and not a discharged obligation ([03 §3.4](03-trust.md#34-trust-bases)).

---

## 9. Contracts, refinements and specs

### 9.1 Minimal refinements (DR-011) **[v0]**

Refinements come in three forms:

- **`#[range(lo..=hi)]`** on integer fields (applied elementwise for arrays) and on parameters.
- **`requires` / `ensures`** on functions. These keywords are familiar to models trained on
  Dafny and Verus code [R03 §10].
- **`invariant`** blocks on structs.

How obligations are discharged:

- **By T2** where possible: bit-vector and linear-integer SMT with certificates ([03](03-trust.md)).
- **Outside kernels**, an undischarged obligation becomes a runtime trap check (§12), and the claim
  is graded `tested`.
- **In `kernel` code, an unprovable refinement is a compile error, never a silent runtime trap.**
  An inner-loop check can also defeat vectorisation [panel, J-SYS].

```mith
struct ActQ8 { d: f32, sum: i32, #[range(-127..=127)] q: [i8; 64] }      // 72 bytes
invariant ActQ8 { sum == q.iter().map(|v| *v as i32).sum::<i32>() }    // integer sum: exact

pub fn block_index(#[range(0..=511)] row: u32, #[range(0..=63)] col: u32) -> u32
    ensures result < 32_768
{
    row * 64 + col      // T2: no overflow, and 511 * 64 + 63 = 32_767 satisfies the ensures
}
```

### 9.2 What v1 deliberately lacks (DR-012)

A Dafny-class auto-active verifier would need four parts:

- verification-condition generation over MCore, including loops and their invariants;
- quantifier instantiation (triggers);
- frame reasoning;
- an aliasing model.

Mutable value semantics makes one part cheap. The only mutable reach of a function is its `&mut`
parameters and its owned locals, so frames are syntactic [inference]. The rest is research-grade
engineering. The mature tools, Dafny and Verus, are the product of long-running research teams
[inference]. The measured agent success rates belong to those tools, not to anything Mithril would
build. On vericoding, the model union reached Dafny 82.2%, Verus 44.2% and Lean 26.8%, and Verus is
the Rust-shaped analogue [R03 §10]. No Mithril document may present 82% as Mithril's expected rate.

What v1 discharges:

- integer side conditions: overflow, bounds, ranges, alignment, exactness of int-to-float casts;
- quantifier-free `requires`/`ensures` over integers, indices and lengths;
- bounded quantifiers over small constant ranges, by unrolling.

Everything else is checked at run time outside kernels, or by tests and T1 `refines` witnesses, and
graded accordingly. DR-012's revisit trigger is a backlog of claims that need loop invariants.

### 9.3 Specs and claims (summary)

Claims live in `spec` items owned by the Author role and hash-locked. Builders cannot edit them, and
each claim kind admits only certain evidence. The ledger, the grades, spec strength and escrow are
specified in [03](03-trust.md).

```mith
/// Claims live in spec items owned by the Author role and hash-locked; Builders cannot edit them.
spec q4_matvec_claims for q4_matvec {
    claim refines(q4_matvec_avx512, q4_matvec) requires validated;     // T1 witness on the object
    claim refines(q4_matvec_avx2, q4_matvec) requires validated;
    claim perf(q4_matvec_avx512) requires measured
        noninferior(to: hearth_c_ref::mm_q4_avx512, margin: 3%);
}
```

---

## 10. Staging

- **v0.** `comptime` is same-language, Zig-style evaluation, run by `mithi` under `compile`. Add
  const generics, monomorphisation, and **schedules as data** attached to `kernel fn`s
  ([02](02-compute.md)). One meaning plus per-ISA schedules replaces Hearth's scalar, AVX2 and
  AVX-512 triplets [R09 §4]. ISA variants are selected at load through a function table, as Hearth
  does today.
- **By-trigger, D-03: `Code<T>` quotes.** They are generative only, which keeps MetaOCaml's
  guarantee that well-typed generators emit well-typed code [R09 §4].
- **By-trigger, D-04: `@bind(load)` binding-time specialisation.** Keys must be finite (enums,
  bounded integers, shapes). Every residual carries a contract to refine the generic definition.
  Specialising on weight *values* is rejected, since compiling weights into instructions is a
  rejected idea ([DECISIONS](../DECISIONS.md)). The honest expectation is help for fixed-trip prefill
  and attention loops, and little for bandwidth-bound decode [P3 §3.7] [inference].
- **Later: a Python schedule-and-search API.** It is untrusted and emits schedule data that is
  checked like any other schedule [G01].

---

## 11. Modules, packages, `mith.lock`, editions

- **Modules [v0].** `mod`, `use` and `pub` keep Rust meaning, and one file is one module.
- **`mith.toml` [v0]** is Cargo-shaped. It declares capability grants, owners by path and role,
  sealed paths, profiles with evidence minima, and the edition:

```toml
[package]  name = "hearth-core"   edition = "2026"
[grants]   unsafe = ["std_platform"]   foreign = ["std_platform"]
           declare_deterministic = ["store"]
[owners]   "kernels/meaning/**" = "role:author"   "kernels/schedule/**" = "role:builder"
           "spec/**" = "role:author"   "bench/harness/**" = "role:gatekeeper"
[sealed]   specs = ["spec/**"]   golden = ["tests/golden/**"]
[profiles.default]  fidelity = "exact"   allow_lossy = false
                    evidence_min = { kernels = "validated", logits_path = "tested" }
```

  Grants name exact modules, not prefixes, and `declare_deterministic` never covers `policy` items
  (§6.4, rule 3).

- **`mith.lock` [v0]** pins:
  - dependency content hashes;
  - the toolchain hash;
  - the edition, with its pinned Rust reference (§2.1);
  - hashes of sealed specs and goldens;
  - name → definition-hash bindings (§3.2), written by SEAL operations: `mithc` updates them when an
    edit lands ([03 §4.4](03-trust.md#44-operation-classes), [05](05-agent-protocol.md));
  - per-machine profile pins written by promotion grants (DR-015, [06](06-forge.md)).
- **`export abi` blocks [v0]** generate the C header, a ctypes mirror and layout tests from one
  source, with mandatory `struct_size` fields. Under the contract variance lattice, appending fields
  is free, while removing or reordering them needs an ADR. That rule would have caught Hearth's
  `read_errors` ABI break [R11], [RV: D2-F].
- **`#[decision("ADR-0004")]`** on constants raises a drift diagnostic when code and decision record
  disagree, as Hearth's heat decay does: 0.9 in code, 0.995 in ADR-0004 [R11].
- **Editions [v1].** Syntax freezes early and changes additively. Every break ships a
  MachineApplicable `mithc fix` migration that preserves the corpus, because every break becomes
  stale-prior debt for models [G01 F2.4].
- **Registry: none in v0.** Dependencies are path and git only.

---

## 12. Traps, errors and fail domains

This section closes a gap the judges found in every proposal. It must answer two questions: which
error wins when parallel iterations fail, and why a policy that traps must not produce an error.

### 12.1 Two channels **[v0]**

- **Recoverable errors** use `Result` and `?`, with Rust meaning (C).
- **Traps** are what Rust calls panics:
  - `panic!`, a failed `assert!`, a failed runtime `requires` check;
  - integer overflow, an out-of-bounds index, division by zero;
  - `unwrap`/`expect` on `None` or `Err`, `unreachable!`;
  - reaching `todo!`.

  As under Rust's `panic = "abort"` strategy, traps never unwind and `catch_unwind` is Dc. Unlike
  it, a trap ends only its fail domain (§12.2), never the host process (INV-SAFE). Trapping is not
  authority, so it is not a row label. Instead every function summary carries a computed
  **`may_trap`** fact (§12.6).

### 12.2 Fail domains **[v0]**

A trap ends evaluation up to the nearest **fail domain**:

| Fail domain | What a trap becomes |
|---|---|
| An `export abi` entry point | The error code declared for traps in the `export abi` block. Output buffers are unspecified, as for any C API error |
| A hint-port policy call | The fallback policy's decision for that call, plus a strike; k strikes eject the policy (§12.5) |
| A test or harness case | A recorded failure |

`par for` is *not* a domain. It propagates, under the lowest-index rule of §12.3. In the C11
lowering, traps propagate by status return, never by `setjmp` or unwinding tables
([04](04-toolchain.md)).

### 12.3 Deterministic failure in `par for` **[v0]**

A `par for` means its **serial projection**: the same loop run in index order, as Cilk defines it
[R09 §5]. Mithril adds a licence to run iterations in parallel, under conditions that make the
iteration order unobservable (T-Par, §13.4):

- **Disjoint writes.** Each iteration writes only places indexed injectively by its iteration
  variable. These are single elements `y[π(i)]`, or sub-slices `&mut y[lo(i)..hi(i)]` passed by
  projection, where T2 proves `lo(i) ≤ hi(i) ≤ lo(i+1)` over the range. This is Hearth's pool rule:
  "every output element is produced entirely by one thread" (`hx_pool.h`).
- **No cross-iteration reads of written places.** Let `W` be the places the loop writes. Any read
  of a place in `W` must be at the same iteration's own index, `π(i)` or inside `[lo(i), hi(i))`.
  Captured `&mut` places are split per iteration, so `y[r] = y[r - 1] + x[r]`, or a read of `y[j]`
  for any `j` other than the iteration's own index, is `E-PAR-RACE`. Reads of shared, unwritten
  inputs are unrestricted.
- **Thread kinds.** Shared captures are `Sync`; written elements are `Send`.
- **No `break`.** It is `E-PAR-BREAK`.
- **Restricted rows.** The body's row is limited to `blob` and to `alloc(A)` on `Sync` arenas.
  `io`, `spawn`, `time`, `nondet`, `foreign`, `unsafe` and `fp_env` inside a `par for` are
  `E-PAR-EFFECT`.

The iteration order is unobservable only under the write rule and the read rule together. Disjoint
writes alone still admit a read of a neighbour's output, which is a data race.

**Early exit.** `return`, `?` and traps are allowed in the body. The **outcome is that of the
lowest index whose iteration does not complete normally**, which is what the serial loop would do.
Worker threads record their lowest early-exit index, and the join takes the minimum. The join waits
for every iteration below the lowest recorded early exit, so the reported outcome never depends on
which iterations above it happened to run. A consequence: if a lower iteration diverges while a
higher one traps, the loop diverges, as the serial projection does (Theorem 4, condition (iv)).

There is one deviation from the serial projection. After an early exit, the contents of places the
loop writes are **unspecified**: iterations above the winning index may already have run. Test
builds poison those places with a fixed pattern, so any dependence on them is caught. The
determinism theorem (Theorem 4) excludes them. Two further rules close what an early exit or the
schedule could otherwise expose:

- **Linear values in written places are abandoned.** If the loop writes linear values (leases,
  `SlabBuf`s), then on early exit the join abandons (§12.4), in ascending index order, every linear
  value the loop wrote. The written places are left holding no live linear value (`None` for
  `Option` elements). Otherwise iterations above the winning index would leave leases in
  unspecified places that nobody consumes, leaking store reference counts.
- **Arena exhaustion is an environment fault, not a trap.** Whether iteration `i` exhausts an
  arena depends on what the other iterations have allocated, which depends on the schedule. So
  exhausting an arena inside a `par for` body yields `Fault(oom(A))`, reported without an index.
  Like I/O faults, it is excluded from Theorem 4 (§13.6). Code whose out-of-memory outcome must
  itself be deterministic splits the arena into per-iteration bounded sub-arenas before the loop.
  Exhausting a sub-arena is then a trap at that iteration's index, and the lowest-index rule
  applies.

```mith
fn check_entries(entries: &[ExpertEntry], file_len: u64) -> Result<(), FormatError> {
    par for i in 0..entries.len() {
        let end = entries[i].offset.checked_add(entries[i].nbytes)
            .ok_or(FormatError::Overflow { entry: i })?;      // `?` leaves the loop
        if end > file_len { return Err(FormatError::OutOfBounds { entry: i }); }
    }
    Ok(())   // entries 3 and 9 both bad: the result is entry 3 at any thread count
}
```

### 12.4 Linear values on a trap path **[v0]**

When a trap leaves a frame, any live linear values in that frame are **abandoned** in reverse order
of creation:

- Each `std_platform` linear type has an `abandon` routine. For example, an abandoned `Lease`
  decrements the store's reference count and records the abandonment.
- User linear structs abandon field by field.
- `abandon` routines are audited code and may not trap.

This is the deterministic, explicit counterpart of drop-on-unwind. It is the riskiest part of this
design [inference], and X1's reference solutions and the store port (S4) are where it is tested.

### 12.5 Policy traps fall back, never `Err` **[v0; policies and hint ports at M4]**

Suppose a `timing_only` policy could make the store return `Err` by trapping, overrunning its fuel
or emitting garbage. It would then satisfy the noninterference theorem ("golden output *or an
error*", [RV: D2-A]) while denying service at will. So in Mithril every policy failure yields the
fallback decision for that call and a strike. `Err` arises only when a slab the computation
*demands* is unreadable on every verified copy and tier (Theorem 3). Example: in the canonical
policy, if `last_use` were ever ahead of `now`, the `u64` subtraction would trap, and the eviction
would simply use the fallback.

Policies also influence *which* reads happen, through prefetch hints and mirror choice. So the
policy-failure rule alone is not enough: a policy could prefetch a region it knows to be bad, or
steer reads to a bad mirror copy. The store core therefore also meets obligation **O6**, stated with
Theorem 3. A fault on a hint-initiated (speculative) read is swallowed and counted, never surfaced,
and a demand read tries every verified copy and tier before it returns `Err`.

**Policy state and budgets.** A policy's state block is double-buffered. Each call works on a
private copy, which is committed only when the call returns normally and its hint passes
validation. A trap, fuel exhaustion or a budget overrun discards the uncommitted copy, so the next
call sees the state as of the last committed call, never a half-written block. Fuel guarantees that
every call returns, so no preemption is needed. The watchdog is a core-side deadline checked at
commit: an overrunning call's result is discarded, not preempted, and the port uses the fallback
and records a strike.

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

The hint-port mechanics (validation, fuel, off-lock snapshots, strikes) are in
[02](02-compute.md). The certificate is in [03](03-trust.md). The snippet's comment cites O1–O5 as
in [02 §12.4](02-compute.md#124-the-store-core-certificate-o1o5); Theorem 3 needs O6 as well.

### 12.6 Totality facts **[v0]**

`may_trap` is inferred for every function and shown in `mithc outline`. Three rules depend on it:

- **`kernel fn`s must be trap-free.** Every bounds, overflow and refinement obligation is
  discharged statically (DR-011, extended to all trap sites).
- **Parsers derived from `format` descriptions** are generated to be total and contain no
  `unsafe`. Their totality and safety (INV-FMT/SAFE) are graded `tested`, by fuzzing, the `mithi`
  differential and the golden malformed-file test; only the bounds obligations that T2 discharges
  are graded `proof` ([ROADMAP §7](../ROADMAP.md#7-pre-registered-benefit-claims-b1b3) B1,
  [02](02-compute.md), [04](04-toolchain.md)).
- **Exports** may contain trap sites. The wrapper maps traps to the declared error code.

---

## 13. Core calculus sketch: MCore

### 13.1 Role and precedents

**What MCore is.** MCore is the MIR: the small normative core that every surface feature
elaborates into, and that `mithi` interprets as the differential oracle and the `comptime`
evaluator (DR-010). The normative prose core is budgeted at ≤ 30k words, Austral-sized, plus a
machine-readable core [R09 §10] [target].

**How the surface elaborates:**

- methods become functions, and `?` becomes `match`;
- closures become explicit environment records of kind `Local` or escaping;
- each row label becomes an implicit capability parameter `κ_ℓ`;
- `par for` becomes a `par` term over an index range;
- `deterministic(by: E)` becomes `det[E]`;
- every trap site becomes an explicit `trap(σ)`.

Kernel meanings are MCore functions, and KIR is derived from them ([02](02-compute.md)). In v0 that
elaboration of exact meanings into KIR, `comptime` included, is a trusted code component graded
`tested`. It sets only the code floor, so DR-021 holds, and it is mitigated by a second `comptime`
evaluation path ([03 §3.4](03-trust.md#34-trust-bases)). An independent kernel-subset extractor
inside `mithcheck`, which would remove elaboration from the trust base, is a by-trigger upgrade
([03 §14](03-trust.md), [ROADMAP §9](../ROADMAP.md)).

**Precedents.** Each piece has one:

- Rust: surface and ownership;
- Hylo: mutable value semantics and projections [R09];
- Swift: non-escapable types and `Sendable` [G05];
- Effekt and Austral: effects as capabilities rooted at `main` [R09];
- Cilk: serial-projection parallelism [R09];
- information-flow typing and the Zdancewic–Myers timing factoring [RV: D2-A];
- sched_ext: fallback policies [RV: D2-A].

What is new is the combination, stated in one calculus with machine-checkable judgements.

### 13.2 Syntax (sketch)

```text
τ   ::= iN | uN | f32 | f64 | bool | () | S<τ̄> | [τ; n] | &τ | &mut τ
      | fn(m̄ τ̄) -> τ ! ε          escaping function or closure (row in the type)
      | clo_L(m̄ τ̄) -> τ           Local closure (row charged at creation)
      | Cap<ℓ> | Frozen<τ> | Mutex<τ> | SlabBuf | Hint<τ> | …      std_platform types
m   ::= own | ref | mut            by value, &, &mut
K   ⊆ {Copy, Linear, Local, Send, Sync}                              derived kinds
ℓ   ::= io | spawn | alloc(A) | time | foreign | unsafe | fp_env | compile | lossy
      | nondet | nondet(platform) | blob
ε   ::= {ℓ, …}                     finite set; no row variables in v0
f   ::= exact | real(b) | approx(p)                  exact ⊑ real ⊑ approx (real, approx reserved)
d   ::= cross_device | device(t) | schedule_dependent                (device reserved)
γ   ::= (f, d, B)                  B = set of cited deterministic-boundary evidence
p   ::= x | p.f | p[e] | g(p, ē)                     places; g a projection
e   ::= v | p | move p | &p | &mut p | p = e | let x = e; e | g(ē) | prim_ℓ̄(ē)
      | if e {e} else {e} | match e {…} | loop {e} | return e | |x̄| e
      | par i in e..e {e} | scope {e} | det[E] {e} | trap(σ)
o   ::= Val(v) | Trap(σ, ī) | Fault(φ)   outcomes: σ trap site, ī lowest par indices, φ env fault
```

`Err(…)` from `Result` is an ordinary value. `Fault(φ)` is an environment outcome: a demanded slab
unreadable on every verified copy (§13.5), or an exhausted arena inside a `par` body (§12.3). The
boundary of the enclosing API turns it into an `Err`.

### 13.3 Judgement forms

```text
Δ ⊢ τ : K                               kinding: Local, Linear, Send, Sync are derived
Δ ⊢ ε ok@pkg                            the row is admissible under the package's grants
Δ; Γ; Σ; pc ⊢ e : τ @ γ ! ε ⊣ Γ'        expression typing
Δ; Γ ⊢ p : τ via m ⊣ Γ' [λ]             place typing; borrowing p in mode m creates loan λ
Δ ⊢ fn g … : sig(g)                     sig = (m̄ τ̄ -> τ, row, grade transfers, may_trap)
                                        grade transfers = one for the result, one per &mut parameter
Δ ⊢_to P ok                             timing_only confinement of a policy
Δ ⊢_k  g ok                             kernel well-formedness ([02])
Ψ ⊢ H                                   heap typing (runtime)
⟨H, T⟩ ─[c]→ ⟨H', T'⟩                   small step of a thread pool T; c = scheduler/environment choice
```

What each context holds:

- **Δ:** type and const variables, trait bounds, std signatures.
- **Γ:** each variable's graded type and its ownership state: `owned`, `moved` or `loaned(λ̄)`. The
  judgement is flow-sensitive and threads Γ to Γ'. The contents of `std_platform` shared-mutable
  types are the exception: they have the fixed grade of §7.2 and are not tracked in Γ.
- **Σ:** the authority available, which is the declared or inferred row of the enclosing function.
- **pc:** the grade of the control context.

**Reading the expression judgement.** It is the core of the design. *Under authority Σ and control
grade pc, e has type τ, produces a value of grade γ, exercises authority ε ⊆ Σ, and leaves
ownership state Γ'.* Rows (ε) and grades (γ) are separate outputs, composed by different operators
(§7.4).

### 13.4 Selected rules

Notation: `⊔` is the join (componentwise on γ, union on B). `taint(ℓ̄)` is `(exact,
schedule_dependent, ∅)` if `nondet ∈ ℓ̄`; it is `(exact, device(platform), ∅)` if
`nondet(platform) ∈ ℓ̄`, which is `schedule_dependent` in v0 because `device` is reserved; otherwise
it is ⊥. `fid(prim)` is `exact` for IEEE basic operations and for `cr::*` and `canon_v1::*`. It is
`approx(p)` only for primitives that require `lossy`, which are reserved.

```text
 Γ;Σ;pc ⊢ ē : τ̄ @ γ̄ ! ε̄ ⊣ Γ'      prim : τ̄ -> τ  with labels ℓ̄ ⊆ Σ
──────────────────────────────────────────────────────────────────────────────  T-Prim
 Γ;Σ;pc ⊢ prim_ℓ̄(ē) : τ @ (⊔γ̄ ⊔ pc ⊔ taint(ℓ̄) ⊔ fid(prim)) ! (∪ε̄ ∪ ℓ̄) ⊣ Γ'

 sig(g) = (m̄ τ̄ -> τ, ε_g, (γ_g, γ̄_mut), _)   ε_g ⊆ Σ   Γ;Σ;pc ⊢ ā : τ̄ @ γ̄ ! ε̄ ⊣ Γ'   (modes m̄ obeyed)
 Γ'' = Γ'[ grade(p_j) := grade(p_j) ⊔ γ_mut,j ⊔ ⊔γ̄_deps(j) ⊔ pc   for each a_j = &mut p_j ]
         [ grade(q) := grade(q) ⊔ wr_q ⊔ pc   for each q captured by mut in a clo_L argument ]
──────────────────────────────────────────────────────────────────────────────  T-Call
 Γ;Σ;pc ⊢ g(ā) : τ @ (γ_g ⊔ ⊔γ̄_deps ⊔ pc) ! (∪ε̄ ∪ ε_g) ⊣ Γ''
   -- ε_g ⊆ Σ is the capability check: κ_ℓ for each ℓ ∈ ε_g is passed implicitly
   -- γ_mut,j: g's transfer for its j-th &mut parameter; γ̄_deps(j): the argument grades it uses
   -- wr_q: the grade the closure body writes into q, typed with its parameters at the grades
   --   sig(g) declares for them (with_lock declares the fixed shared-state grade of §7.2)

 Γ;Σ;pc ⊢ c : bool @ γc ! εc ⊣ Γ1     Γ1;Σ;pc⊔γc ⊢ e_i : τ @ γ_i ! ε_i ⊣ Γ2   (i = 1, 2)
──────────────────────────────────────────────────────────────────────────────  T-If
 Γ;Σ;pc ⊢ if c {e1} else {e2} : τ @ (γ1 ⊔ γ2 ⊔ γc) ! (εc ∪ ε1 ∪ ε2) ⊣ Γ2

 Γ;Σ;pc ⊢ e : τ @ γ ! ε ⊣ Γ'    p owned and not loaned in Γ'
──────────────────────────────────────────────────────────────────────────────  T-Assign
 Γ;Σ;pc ⊢ p = e : () @ pc ! ε ⊣ Γ'[grade(p) := grade(p) ⊔ γ ⊔ pc]

──────────────────────────────────────────────────────────────────────────────  T-Trap
 Γ;Σ;pc ⊢ trap(σ) : τ @ pc ! ∅ ⊣ Γ        -- any τ; sets may_trap; the outcome depends on pc

 Γ;Σ ∪ {nondet};pc ⊢ e : τ @ (f, d, B) ! ε ⊣ Γ'     DeclareDeterministic granted to the module
 E admitted, current, and its claim is deterministic(e)     d° = d with the nondet taint masked
──────────────────────────────────────────────────────────────────────────────  T-Det
 Γ;Σ;pc ⊢ det[E] {e} : τ @ (f, d° ⊔ pc.d, B ∪ {E}) ! (ε \ {nondet}) ⊣ Γ'
   -- nondet(platform) is neither removed nor masked; fidelity f is unchanged
```

(`d°` is well defined because derivations record taint provenance. It is the scope the body would
receive if `taint(nondet)` were ⊥.)

**Kinds, second-class references and projections:**

```text
 τ = &σ or &mut σ,  or τ has a Local component,  or τ = clo_L(…)      ⟹  Δ ⊢ τ : Local
 struct/enum S { f̄ : τ̄ } ok  only if  ∀i. Δ ⊬ τ_i : Local                         (E-REF-FIELD)

 Every type parameter T of a user struct, enum, impl or fn carries an implicit bound T : ¬Local;
 only std signatures may write T : ?Local.
 S<σ̄> or g::<σ̄> with S, g user-declared is well formed only if ∀k. Δ ⊬ σ_k : Local
                                                                            (E-LOCAL-INSTANTIATE)
   Exception: a fn type parameter F bounded by Fn/FnMut/FnOnce (or impl Fn… in argument position)
   that occurs in exactly one parameter type, as F, &F or &mut F, and not in the return type
   (directly or through an associated type), may be instantiated at clo_L; g's body is checked
   with Δ ⊢ F : Local.
   -- this closes the generic bypass of E-REF-FIELD and T-Ret: Wrapper<&U>, first::<&[f32]>

 fn g(x̄ : m̄ τ̄) -> τ  with Δ ⊢ τ : Local is accepted only if                     (T-Ret)
   (a) the Local parts of τ are references selected by Rust's elision rules from exactly one
       parameter x★ (the receiver if present); at each call the result carries a loan on the
       place passed for x★, in that parameter's mode — a projection; or
   (b) g is a std adapter whose declared result loan is the union of its Local arguments' loans.
   Otherwise E-REF-ESCAPE / E-LOCAL-RETURN.

 Loans (intraprocedural, non-lexical): a loan ends at the last use of the value carrying it.
   While a mut loan on p is live, no other use of p or of any place overlapping p.
   While a shared loan on p is live, no write to or move of p.
```

**Closures and linearity:**

```text
 |x̄| e captures by ref/mut, or captures a Local value      Γ;Σ;pc ⊢ e : τ @ γ ! ε_e
──────────────────────────────────────────────────────────────────────────────  T-CloL
 Γ;Σ;pc ⊢ |x̄| e : clo_L(…) -> τ @ pc ! ε_e        -- the body's row is charged here, once;
                                                   -- calling a clo_L later adds nothing
   -- grades are not charged once: the closure's writes into places it captures by mut act as
   --   &mut transfers, applied by T-Call at each direct call and at each call that receives it

 all captures by move and not Local   ⟹   |x̄| e : fn(…) -> τ ! ε_e          (escaping; T-CloE)

 Δ ⊢ τ : Linear and x : τ owned in Γ  ⟹  on every non-trapping path x is consumed exactly once
   before leaving scope; an implicit drop is E-LINEAR-DROP.                         (T-Lin)
```

**Parallel loops:**

```text
 Γ;Σ;pc ⊢ a, b : usize @ γa, γb     body e checked with i : usize @ (γa ⊔ γb)
 W = the places e writes; each is p[π(i)] with π injective in i (affine check), or a
   projection &mut p[lo(i)..hi(i)] with lo(i) ≤ hi(i) ≤ lo(i+1) on a..b, by T2  (E-PAR-DISJOINT)
 every read in e of a place in W is at the same iteration's own index π(i) or
   within [lo(i), hi(i)); captured &mut places are split per iteration            (E-PAR-RACE)
 shared captures Sync; written/moved element types Send; no break                 (E-PAR-BREAK)
 ε_e ⊆ {blob} ∪ {alloc(A) | A : Sync}                                              (E-PAR-EFFECT)
──────────────────────────────────────────────────────────────────────────────  T-Par
 Γ;Σ;pc ⊢ par i in a..b {e} : () @ (γ_e ⊔ γa ⊔ γb ⊔ pc) ! ε_e
   -- no schedule taint is added: under the write premise AND the read premise together, the
   --   iteration order is unobservable (writes alone still admit y[r] = y[r-1] + …, a race)
   -- early exit: lowest index wins; the join waits for every iteration below it, then abandons,
   --   in ascending index order, every linear value the loop wrote into W (§12.3)
   -- exhausting A inside e is Fault(oom(A)), not a trap; per-iteration sub-arenas make it a
   --   trap at that index instead (§12.3)
```

**`timing_only` confinement:**

```text
 Δ ⊢_to P ok  iff
   row(P) = ∅;   result type Hint<…>;   parameters are core-provided views (payload types opaque);
   state, if any, is a fixed-size, double-buffered block owned by the port, committed only on
   normal return (§12.5);   loops only over core-provided slices or constant ranges (static fuel);
   no recursion;   no det block (a DeclareDeterministic grant never covers policy items);
   callees satisfy ⊢_to
```

### 13.5 Dynamic semantics and outcomes

A configuration `⟨H, T⟩` is a heap of values and `std_platform` objects, plus a pool of threads.
Each step is labelled by a choice `c` from an oracle, which covers:

- which thread steps;
- the order of `par for` chunks and I/O completions;
- the hint values at a hint port, chosen demonically.

A **scheduler** `s` is a strategy for these choices. An **environment** `e` is *not* a choice made
per I/O event. It is a fixed function `e : (slab, tier copy) → {ok, fault}`, chosen before the run.
A copy that fails its content-hash check (O4) counts as `fault`, and a transient error that the
core's bounded retries absorb counts as `ok`. Bytes read from an `ok` copy are the file's content. A
policy therefore cannot cause a fault by issuing a read at a particular moment. It can only steer
which copies get read, and O6 (Theorem 3) makes that harmless. `e` also fixes arena capacities, the
source of `Fault(oom(A))` (§12.3).

**Demand set.** `demand(x)` is the sequence of slabs that the computation of `x` requires, in the
order the reference (fallback, serial) run first requires them. By INV-DET-1 it depends only on
`x`, not on hints or schedules. A read is a *demand read* if its slab is in `demand(x)` and the
computation is waiting for it. Every other read, such as a prefetch, is *speculative*.

`eval_{s,e,T}(P, x) ∈ o` is the outcome on a conforming target `T`. Targets are the C11 backend with the C compiler (trusted for
non-kernel code) plus T1-validated kernels ([03](03-trust.md), [04](04-toolchain.md)).

Trap semantics follow §12: lowest index within `par`, then abandonment, then a fail domain.

### 13.6 Theorems to prove

**Theorem 1 (type safety: progress and preservation).** This covers well-typed MCore without
`unsafe`, with `std_platform` meeting its interface specification.

- *Preservation.* Suppose `Δ;Γ;Σ;pc ⊢ e : τ @ γ ! ε ⊣ Γ'`, `Ψ ⊢ H`, and `⟨H, e⟩ ─[c]→ ⟨H', e'⟩`. Then
  there are `Ψ' ⊇ Ψ` and `Γ₁` such that `Ψ' ⊢ H'` and `Δ;Γ₁;Σ;pc ⊢ e' : τ @ γ' ! ε' ⊣ Γ'`, with
  `γ' ⊑ γ` and `ε' ⊆ ε`.
- *Progress.* A well-typed closed configuration is in one of four states: all threads are values;
  some thread can step for some choice `c`; every non-value thread is blocked on a `std_platform`
  synchronisation or I/O operation; or the active thread is `trap(σ)` at a site the checker
  recorded.
- *Corollaries.* No use after move. No access through an ended loan. No data race, meaning no two
  unordered accesses to one location of which at least one is a write. No linear value dropped on a
  normal path.
- *Not claimed:* deadlock freedom and termination. These are covered by the permutation scheduler
  and liveness monitors (§5.8, [02](02-compute.md)).

**Theorem 2 (capability confinement).** This covers well-typed programs whose `unsafe` and
`foreign` code lies only in granted packages.

- *(a) No forging.* In every reachable configuration, every capability value was produced by
  `std_platform` attenuation from a `Root` minted at `main` or at an `export abi` entry. It reached
  its holder by parameter passing, by return, or by a recorded service capture.
- *(b) Row soundness.* During a call to `g`, every executed primitive with labels `ℓ̄` satisfies
  `ℓ̄ ⊆ row(g) ∪ ε_C ∪ N_g`. Here `ε_C` is the union of the rows charged when the `Local` closures
  passed into the call were created; those rows belong to `g`'s callers. `N_g` is `{nondet}` if
  the primitive executes inside a `det` block lexically within `g` or one of its callees, and `∅`
  otherwise. T-Det grants `nondet` inside the block and removes it from the row, so without `N_g`
  the statement would be false for every function containing a `det` block.
- *(c) Slot corollary.* A candidate for a Forge slot or hint port with maximum row `ε_s`, called
  with no closure arguments, executes no primitive outside `ε_s`. For `timing_only` slots,
  `ε_s = ∅` and `N_g = ∅`, because `⊢_to` forbids `det` blocks in the policy and its callees. So a
  policy cannot observe lock interleavings or atomics, which `timing_blind` replay and
  simulator-engine equivalence rely on. T0 checks this on emitted object code, independently of the
  front end. Its instruction check is a *positive allowlist* of table-covered iclasses, so anything
  not on the list is excluded without being named. Examples of excluded instructions:
  - timing and counter sources: RDTSC, RDTSCP, RDPMC, RDPRU (an AMD timing source on Zen), RDPID;
  - nondeterministic sources: RDRAND, RDSEED;
  - FP-environment writes and state restores that can smuggle one: LDMXCSR, VLDMXCSR, FLDCW,
    FLDENV, FRSTOR, FNINIT, FXRSTOR and the XRSTOR family;
  - CPUID, RDFSBASE/RDGSBASE and segment-override loads;
  - syscalls and indirect calls.

  T0 also allows stores only to the state block or stack, and requires fuel.
  [03 §6.2](03-trust.md#62-t0-confinement-on-the-binary) is normative for the list.

**Theorem 3 (`timing_only` noninterference).** Let `C` be a core whose hint ports satisfy the
store-core obligations O1–O5 ([02 §12.4](02-compute.md#124-the-store-core-certificate-o1o5)) and O6
below, and let `F` be each port's fallback ([02](02-compute.md), [03](03-trust.md)).

- **O6, fault isolation.** A fault on a speculative (hint-initiated) read is swallowed and counted,
  never surfaced. It leaves the slab in the state it had before the read, so a later demand read
  starts afresh. A demand read tries every verified copy on every tier before it returns `Err`. When
  several demanded slabs fail, the core reports the first in `demand(x)` order.

Let `P` be any policy with `Δ ⊢_to P ok` whose object code passes the T0 allowlist. Then the
following holds for every input `x`, for every hint stream `h` (demonic: any sequence of hint values,
not only those `P` can produce), for every I/O completion order `σ`, and for every environment `e`
(a fixed function from slab copies to `{ok, fault}`, §13.5):

```text
 out(C[P], x, h, σ, e) = Err(φ)                 iff some slab in demand(x) is fault on every
                                                    copy and tier under e; φ names the first such
                                                    slab in demand(x) order
                       = out(C[F], x, σ₀, ok)   otherwise   (ok: the all-ok environment)
```

The condition for `Err` mentions only `x` and `e`, so **no policy behaviour is ever a cause of
`Err`.** Prefetching a known-bad region produces only swallowed speculative faults (O6). Steering a
read to a bad mirror copy only makes the demand read move on to the next copy (O4, O6). Any hint
value, a trap inside `P`, fuel exhaustion or a budget overrun yields `F`'s decision for that call
and a strike, with `P`'s uncommitted state discarded (§12.5). The proof splits in two:

- **Lemma 3a, confinement** (this document plus the T0 binary check). Each call of `P` can change
  nothing except its returned `Hint` and its private copy of the state block, which the core commits
  only on normal, in-budget return. It cannot change the FP environment or other ambient machine
  state. Static fuel bounds every call, so it always returns. A wall-clock overrun is detected by
  the core-side deadline at commit, and the result is discarded rather than preempted.
- **Lemma 3b, the core certificate** ([03](03-trust.md)). With hints quantified demonically, the
  output depends only on `x` and `e`, and the set of reads that can surface a fault is `demand(x)`.

Payload opacity is *not* a premise of Lemma 3a, because Lemma 3b already quantifies over all hint
streams. Opacity is kept for simulator and engine policy equivalence and for confidentiality
[RV: D3-iii] [inference].

**Theorem 4 (determinism).** Let `P` be well-typed and let `o` be an output whose outcome grade has
scope `cross_device`. The outcome grade joins the grades of the returned value with the `pc` of
every reachable return, trap and early exit (T-If, T-Trap). Take any schedulers `s, s'` (thread
interleavings, `par for` chunking, I/O completion orders, hint streams at certified ports), any
conforming targets `T, T'`, and any environments `e, e'` that are *non-failing for `x`*: no slab
in `demand(x)` is fault on every copy, and no arena is exhausted inside a `par` body. Then
`eval_{s,e,T}(P, x)|o = eval_{s',e',T'}(P, x)|o`. Equal here means one of three things:

- the same bits, every float at a `cross_device` sink being NaN-canonical (below);
- the same trap site with the same lowest `par for` indices;
- the same `Err` value.

If an environment is failing for `x`, that run's outcome is `Fault(φ)`, and so `Err` at the API,
never a different value. For scope `device(t)` (reserved), the same holds over targets of class `t`.

**NaN payloads are not portable,** so the checker enforces canonical NaNs, not only at kernel
sinks. NaN propagation differs between x86 and arm64, and between compilers, in both payload and
sign. The checker tracks a one-bit NaN-canonicality fact on float values alongside `γ`. A value is
*canonical* after `canon::nan`, an integer-to-float conversion or a literal, or when T2 proves it
not NaN. It is *raw* after any other float operation. Two rules follow:

- **Sinks.** Every float output whose required scope is `cross_device` must be canonical (kernel
  outputs, `#[grade(.., cross_device)]` outputs, exports declared exact). Otherwise
  `E-NAN-RAW-SINK`, whose fix inserts `canon::nan`.
- **Observers.** An operation that exposes a raw value's payload or NaN sign carries the taint
  `device(platform)`, which is `schedule_dependent` in v0. These operations are `to_bits`,
  `to_le_bytes`/`to_be_bytes`/`to_ne_bytes`, `is_sign_positive`/`is_sign_negative`, and `copysign`
  with a raw sign source. Comparisons and `is_nan` are payload-blind and carry no taint.

The theorem has four conditions:

- (i) Every `deterministic` boundary in `B(o)`, the data-flow set of §7.2, is backed by its cited
  evidence. The statement is a value-level claim, so its effective grade is the meet of those
  grades.
- (ii) The trust base of [03](03-trust.md) holds: the semantics table, the T1 rewrite list,
  `std_platform`, the elaboration of exact meanings into KIR (§13.1), and the C compiler for
  non-kernel code.
- (iii) Early-exit exclusion: the contents of places written by an early-exited `par for` are
  excluded (§12.3). Linear values among them have been abandoned in index order.
- (iv) Termination-insensitivity: equality is claimed only when both runs terminate. Theorem 1
  claims neither termination nor deadlock freedom, so a run that diverges or deadlocks under one
  scheduler voids the comparison. Within `par for`, the join waits for every iteration below the
  lowest recorded early exit. So if a lower iteration diverges while a higher one traps, every run
  diverges, as the serial projection does, and no run reports the higher trap.

Hearth's INV-DET-1/2/3 become instances. Kernels discharge them by per-build T1 witnesses, policies
by Theorem 3, and the store path by its boundary evidence.

**Lemma (erasure).** Rows, grades, kinds and loans are compile-time only. Elaboration to C11
inserts runtime code only for undischarged obligations outside kernels (trap checks) and for the
`abandon` of live linear values on trap paths and after an early-exited `par for`. The
NaN-canonicality fact is compile-time too; only the `canon::nan` calls it demands run. Effects and
grades therefore add zero runtime cost
[target], which `mithc audit` checks on generated C ([04](04-toolchain.md)).

### 13.7 Evidence plan: what each statement is worth today

Grades follow the trust-base-relative rules of [03](03-trust.md). Lean mechanisation of MCore is
by-trigger (DR-010, D-08). Until it fires, the front end's soundness rests on tests and on `mithi`,
and the ledger says so [panel].

| Statement | Proof route | Grade today | Upgrade path |
|---|---|---|---|
| Theorem 1 | Paper proof in the normative core; `mithi` against `mithc` differential testing on the corpus; checker property tests and mutation of the checker | `tested` | Lean MCore when D-08 fires |
| Theorem 2 (a, b) | Theorem 1 plus a no-forging lemma over `std_platform` capability types; capability audit graph in the Fact Plane | `tested` | Lean MCore (D-08) |
| Theorem 2 (c) at binary level | T0 allowlist decision procedure on lifted object code (a T0 verdict: `proof` in form) | Effective `validated(partition)` from its table premises; for `confined(S)`, `validated(bounded: …)` via the store-core theorem; code floor `tested` (the T0 pass, DR-010), printed beside it, not met. timing_only slots set `code_floor = "tested"` ([03 §3.2, §3.4–§3.5](03-trust.md#34-trust-bases)) | Mechanised T0 checker (D-08); second checker (D-09) |
| Theorem 3 | Lemma 3a (T0 binary check, graded as in the row above) plus Lemma 3b (store core incl. O6: bounded model check, chaos suite with bad-mirror and faulted-prefetch cases, 100% core-mutant kill) | Effective `validated(bounded: …)` (Lemma 3b's grade, the store-core theorem) with code floor `tested` (the T0 pass), when the binary check ran; `tested` otherwise | Early proof target under DR-010: Lean or Verus proof of the store core |
| Theorem 4 | Theorem 1 plus an information-flow noninterference argument for the scope lattice, plus boundary evidence | `tested` (golden scheduling, ISA and batch identity; cross-binary hash corpus); kernel instances `validated` by T1, code floor `tested` | Lean MCore (D-08) |
| Erasure lemma | Inspection of generated C; object audit | `tested` | — |

ROADMAP's M0 core-calculus gate ([ROADMAP §3.6](../ROADMAP.md)) requires three things: every
canonical snippet derives by hand under these rules and is accepted by `mithi`; every Tier 0 rule
traces back to this section; and a Prover and an Adversary from another model family review it.

---

## 14. Open questions and reviewer notes

**Open questions**

1. **Is lexical charging enough?** Will charging `Local` closure rows at creation make some
   higher-order std signatures over-approximate rows that agents find confusing? The Surface Lab
   measures this through the `next:` hints of `E-ROW-UNDECLARED`.
2. **Do agent idioms need richer `Local` types?** How often do X1 reference solutions need
   user-defined `Local` types, for example a struct holding two slices? The answer sets the
   by-trigger threshold in §5.4.
3. **Is `abandon` enough on trap paths?** It needs to express everything Hearth's error paths do
   today, such as releasing slot references on a failed `hx_model_eval`. The store port (S4) is the
   test.
4. **Do the T1 lockstep rule and the serial-projection rule compose for prefill?** The question is
   batched prefill with exact int32 cross-thread partials ([02](02-compute.md)).

**Reviewer notes on the outline** (decisions kept; problems flagged)

- **R1: class naming.** The outline's classes are C / Dc (rejected) / D (new). [RV: D3-i] uses D
  for *checker-invisible* divergence, the case the subset rule forbids. This document uses the
  outline's meaning. Under the rule, every divergent prior must be resolved into Dc or D, so D3-i's
  "D" cannot exist in the language.
- **R2: `confined` admissibility (resolved by [03 §3.2 and §3.4](03-trust.md#34-trust-bases),
  which are normative).** The outline says `confined(space)` "admits proof only". DR-010 grades the
  store-core theorem `validated` until mechanised and records T0 confinement as `tested`. 03
  reconciles these. "Proof only" constrains the *form* of evidence: a T0 verdict on the binary,
  never test results. The effective grade meets the verdict's premises: `validated(partition)` from
  table premises, and for `confined(S)`, `validated(bounded: …)` via the store-core theorem. The
  code floor, `tested` (the T0 pass), is printed beside it and not met, and timing_only slots set
  `code_floor = "tested"` (03 §3.5). §13.7 uses exactly this format.
- **R3: no `fail` label.** The outline's effect list has no `fail`, yet §5 requires deterministic
  Fail semantics. This document models traps as an outcome plus a `may_trap` summary fact, not as
  authority (§12). Sibling docs should not add a `fail` row label, and should say "trap" (§12): a
  trap ends its fail domain (§12.2); it never unwinds and never aborts the host.
- **R4: the "Safe" `sum_seq` fix.** DR-013 calls the `canon::sum_seq` fix Safe. That is exact only
  if `sum_seq` reproduces the pinned Rust start value. [RV: D3-i] reports, marked [inference], that
  Rust's empty float sum is −0.0, while NUMERICS sequential accumulations start at `+0.0f`. This
  document defines `sum_seq` with Rust's start value and writes NUMERICS-style accumulation as
  explicit loops. Resolved: [02 §5](02-compute.md#5-the-canon-library) uses the same definition.
- **R5: what "blob-grade" means.** The outline says a boundary turns results into "blob-grade
  values", yet the canonical `acquire` row is `uses { io, spawn }`. This document reads blob-grade
  as a *grade* (scope reset, evidence attached), not a row entry, which resolves the open point in
  [ARCHITECTURE §5.3](../ARCHITECTURE.md).
- **R6: clocks.** In the outline, only `nondet` and `nondet(platform)` taint scope. Clock reads must
  taint as well, so `time` primitives also carry `nondet` (§6.1). The same holds for reads of mutable
  files.
- **R7: `acquire` returns `Result` (resolved).** The outline's `acquire` returned a bare
  `Frozen<SlabBuf>`, so an I/O fault could surface only as a trap. §6.4 now prints
  [ARCHITECTURE §5.3](../ARCHITECTURE.md#53-canonical-snippets)'s Result-returning form, whose
  `Err` comes only from environment faults (HX_E_IO, O5).

---

## 15. Sources

- **Research dossiers:**
  - [R09](../research/R09-language-building-blocks.md): effects as capabilities, MVS, staging,
    deterministic parallelism, spec budget;
  - [G05](../research/G05-shared-mutable-state-memory-model.md): `store.c` analysis, Swift
    `Mutex`/`~Escapable`, transfer and share kinds, the `Nondet` boundary;
  - [R03](../research/R03-llm-language-ergonomics.md): false friends, typed holes, grammar policy,
    verification-language evidence;
  - [G01](../research/G01-new-language-cold-start-evidence.md): cold-start and false-friend
    measurements, tiered card, Lark grammar;
  - [G04](../research/G04-transcendental-libm-numeric-spec.md): UCRT divergence, `cr` versus
    `canon`, measured `expf` prototype;
  - also cited: [R07](../research/R07-verification-superoptimization.md),
    [R11](../research/R11-hearth-port-requirements.md),
    [G02](../research/G02-x86-avx512-formal-semantics-sources.md),
    [G03](../research/G03-gpu-tier-and-cross-device-determinism.md).
- **Revisit archive** ([revisited-ideas](../research/revisited-ideas.md)): D2-A (timing_only
  effect), D3-i (divergence-marking surface), D3-iii (tenant labels), D2-F (contract variance).
- **Proposals:** [P1 §3](../design/proposals/P1-agents-language.md) (subset rule, false-friend
  table, holes), [P2 §3](../design/proposals/P2-tractable-godel.md) (lattices, boundary grant and
  grade propagation), [P3 §3](../design/proposals/P3-physics-first.md) (projections, effect table),
  [P5 §3](../design/proposals/P5-minimum-viable.md) (fixed effect set, minimal refinements,
  deferrals). The judges' digest is the source of every [panel] citation.
- **Hearth (read-only):** `docs/NUMERICS.md` §1–§3, `engine/src/hx_pool.h` (the pool determinism
  rule), `engine/src/hx_model.h` (error codes), `engine/src/store.c` via [G05].
