# mithi

`mithi` is the independent checker and tree-walking interpreter for Mithril's X1 subset (DR-010,
ROADMAP §3.2, X1 DESIGN §9). It implements the core calculus of
[docs/m0/core-calculus.md](../../docs/m0/core-calculus.md) ("the note", MCore v0.1) for the X1
subset and is judged against the note's hand verdicts in
[verdicts.json](../../docs/m0/core-calculus/verdicts.json).

**Status: v0 DRAFT, 2026-10-16 (M0 week 0), revised the same day after an independent review, and
revised again on 2026-10-23 after a blind adversarial review and the note's third review round (see
[Review log](#review-log)). Not frozen.** Written by the mithi track (Claude). The note's author
and every reviewer are the same model family, so every agreement below is between contexts of one
family (same family, independent context), and mithi was developed, and revised, with the note's
verdicts in view: it is not a blind replication (the 2026-10-23 review's predictions were blind;
the revision was not). Every rule interpretation mithi had to make is listed under
[Interpretations](#interpretations-each-needs-review). Since 2026-10-23, claims about what Rust
accepts or computes are measured with the pinned rustc 1.99.1 where a test says so [M], not
inferred.

## Build, test, run

- Toolchain: `rust-toolchain.toml` pins Rust 1.99.1 [M: rustc 1.99.1 (58cf8f9c3 2026-10-13), host
  x86_64-pc-windows-gnu, installed 2026-10-16]. No dependencies; `Cargo.lock` lists mithi only.
  The MSVC host (x86_64-pc-windows-msvc) should build the same sources, since mithi uses std only
  [inference: not built on MSVC].
- Keep build output out of the repository and use at most two jobs on shared machines:

  ```sh
  export CARGO_TARGET_DIR=/path/outside/the/repo   # e.g. D:\mithril\target on the desktop
  export CARGO_BUILD_JOBS=2
  cargo build -p mithi
  cargo test -p mithi -- --test-threads=2
  ```

- Grammar check (needs Python and the `lark` package; written against lark 1.3.1):
  `python grammar/test_grammar.py [--mithi target/debug/mithi] [--mutants 150]`.
- Freeze build (DESIGN §9.3; not yet frozen): the `freeze` profile in the workspace `Cargo.toml`
  (release, no debug information, stripped, one codegen unit, overflow checks on), with the
  checkout path remapped so that the binary does not depend on where the repository lives. The path
  has a space on the laptop, so the flag goes through `CARGO_ENCODED_RUSTFLAGS`:

  ```sh
  CARGO_ENCODED_RUSTFLAGS="--remap-path-prefix=<absolute repo path>=." cargo build -p mithi --profile freeze
  ```

  [M: 2026-10-16, laptop, host x86_64-pc-windows-gnu, the sources of this revision: 3,544,576
  bytes; the binary contains no occurrence of the user name in the checkout path. Its SHA-256 is
  not recorded here because the sources are not frozen; the host triple is part of what a freeze
  records.]
- `MITHI_TIME=1` prints the time of each analysis pass; `MITHI_T2_DEBUG=1` prints each goal T2
  cannot prove (with its facts); `MITHI_OWN_DEBUG=1` traces loans.

Command line (`mithi` with no arguments prints the usage):

```text
mithi check [--json] [options] FILE...        type-check and run every MCore analysis
mithi run   [options] --entry NAME FILE...    run a function with no parameters
mithi test  [options] FILE...                 run every #[test] function
mithi parse FILE...                           parse only (accept/reject per file)

--canonical-prelude      add prelude/canonical.mith (derivations section P)
--prelude FILE           add a prelude file (repeatable)
--module NAME            check the user files as module NAME (e.g. store)
--manifest FILE          read a mith.toml subset: [grants], declare_deterministic, [evidence] fixtures
--doc-snippets           accept documentation shorthand `…`
--loose-host NAME        loose `let` statements become the body of prelude function NAME
--subset checker|agent   checker (default) or the X1 agent subset (E-X1-NOTYET-<KW>), note Q9
--no-user-traits         the no-traits arm (E-TRAIT-OFF)
```

An option that takes a value exits with code 2 when the value is missing, and an unknown `--subset`
value exits with code 2 (a typo must not select the checker subset). The checker and interpreter
run on a thread with a 1 GiB stack reservation, and the parser rejects syntactic nesting deeper than
512 levels (E-PARSE), so deep programs end in a diagnostic or the interpreter's 2000-frame limit,
not a stack overflow. A panic ends with exit code 3 and, with `--json`, `{"verdict":
"internal-error"}`: an infrastructure failure of the oracle, never a verdict.

`check --json` prints `{"mithi", "std_sha256", "verdict", "primary", "diagnostics": [...],
"facts": {...}}`. `std_sha256` is the SHA-256 of the std and canonical prelude texts compiled into
the binary. A diagnostic has `code`, `kind`, `class` (the §5.16 precedence class), `severity`,
`message`, `at` (`def`, the source `anchor` and `loc` as file:line:column) and `notes`. `primary`
is the first diagnostic in the precedence order of note §5.16. The facts give, per function, the
row, the exercised row, may_trap, kcall and the output grade. The output does not depend on hash
seeds (all maps whose order reaches a diagnostic are ordered; `tests/review_determinism.rs`).

## Layout

| Path | What |
|---|---|
| `src/lexer.rs`, `src/parser.rs`, `src/ast.rs` | Rust-style lexer and recursive-descent parser (see [Grammar and parser](#grammar-and-parser)) |
| `src/lower.rs`, `src/program.rs`, `src/types.rs` | name resolution, the prelude override rule, `format` code generation (⊢_fmt), item tables, impl conformance and coherence |
| `src/typeck.rs`, `src/infer.rs`, `src/captures.rs`, `src/thir.rs` | type checking with local inference, method probing (autoderef, unsize, autoref), a trait solver, closure capture modes; typed bodies |
| `src/fmtspec.rs` | Rust's `format!` placeholder grammar, shared by the checker and the interpreter |
| `src/analysis/` | the MCore judgements, one file each (below) |
| `src/interp.rs` | the interpreter (note §6): values, places, deterministic traps |
| `src/check.rs`, `src/diag.rs`, `src/manifest.rs` | driver, diagnostics and precedence (§5.16), `mith.toml` subset |
| `src/sha256.rs`, `src/json.rs` | in-tree SHA-256 and JSON (no dependencies) |
| `std/std.mith` | the X1 std mithi checks and runs against (Option, Result, Vec, iterators, canon, f16, Mutex, SlabBuf, Hint, …) |
| `prelude/canonical.mith` | derivations §P transcribed; additions marked `[mithi addition]` |
| `tests/verdicts.rs` | the agreement test against verdicts.json |
| `tests/corpus.rs`, `tests/corpus/*.mith` | X1-shaped programs and Rust-meaning checks, checked and run |
| `tests/ownership.rs` | 97 ownership and borrowing cases with Rust's verdicts |
| `tests/interp.rs` | traps, `par for` order and index, abandonment (named locals and temporaries), deep recursion, f16 widening, canon sum order |
| `tests/review_*.rs`, `tests/common/` | the regression tests of the 2026-10-16 review (below) |
| `tests/review_2026_10_23.rs` | the regression tests of the 2026-10-23 review, with rustc-measured expectations for ownership and run-time values |

## What is implemented

By judgement of the note (section numbers are the note's):

| Judgement | Where | Codes |
|---|---|---|
| Subset rule, Dc/D codes visible at type level (§5.0) | `typeck.rs`, `analysis/ctx.rs`, `lower.rs` | E-AMBIENT-IO, E-MACRO, E-FF-ADDR, E-FF-F16, E-FF-SUM, E-FF-TIES, E-FF-EXP, E-FF-POWI, E-FF-CLOCK (the FF class checks also run on each instantiation of a generic function reached from exact code), E-DYN, E-ASYNC, E-LIFETIME, E-GLOBAL-STATE, E-FP-ENV, E-FF-CELL, E-DROP-IMPL |
| Static-dispatch traits (§5.12) | `lower.rs` | impl method signatures against the trait's (E-TYPE); E-COHERENCE for overlapping impls, a derive plus a manual impl of one trait, and impls of std traits for types with no local component (orphan rule); E-SPECIALIZE for `default fn` |
| Out-of-scope constructs (§12, Q10) | `check.rs`, `parser.rs` | E-OUT-OF-SCOPE-<KW> (FLOW, STORE, EVOLVE, EXPORT, COMPTIME, E8M0, E2M1X2, MEMCAP and the other platform names) |
| Kinds, well-formedness, T-Ret signature part, instantiation (§5.1, §5.6, §5.7 rule 4) | `analysis/wf.rs` | E-REF-FIELD, E-REF-ESCAPE, E-LOCAL-RETURN, E-LOCAL-INSTANTIATE, E-LINEAR-INSTANTIATE, E-LINEAR-COPY, E-TRAIT-OFF, E-MONO-DEPTH (direct self-recursion at a growing type), E-X1-NOTYET-<KW> (agent subset, including PATH, ENV and INCLUDE) |
| Rows, grants, exercised rows (§5.2, F-36, F-71) | `analysis/rows.rs` | E-ROW-UNDECLARED, E-IMPL-ROW, E-GRANT-UNSAFE, E-GRANT-FOREIGN; C-ALLOC labels on every allocating std operation; a function used as a value is charged where it is named; exercised rows are transitive |
| Grade contexts (§5.3) | `analysis/ctx.rs` | context-dependent class codes |
| Ownership, linearity, loans (§5.4, §5.6, §5.8) | `analysis/own.rs` | E-MOVE-USED, E-MOVE-LOOP, E-MOVE-BORROWED, E-LINEAR-DROP, E-LINEAR-PARTIAL, E-BORROW-CONFLICT, E-BORROW-OUTLIVE, E-LOCAL-MUT-STORE |
| Grades: scope, NaN bit, deps, observers, T-Cover, X' (§5.3, §5.5, §5.7, §5.9, §5.11) | `analysis/grade.rs` | E-GRADE, E-NAN-RAW-SINK, E-IMPL-GRADE |
| T-Par (§5.9) | `analysis/par.rs` | E-PAR-BREAK, E-PAR-EFFECT, E-PAR-DISJOINT, E-PAR-RACE |
| Trap sites, obligations, T2 (§5.10) | `analysis/t2.rs` | E-KERNEL-OBLIGATION, E-FOOTPRINT; the may_trap fact |
| ⊢_k and kcall (§5.10) | `analysis/kernel.rs` | E-KERNEL-ROW, E-KERNEL-CALL |
| T-Det (§5.11) | `analysis/det.rs` | E-DET-GRANT, E-DET-POLICY, E-DET-EVIDENCE, E-DET-RESULT |
| ⊢_to (§5.13) | `analysis/policy.rs` | E-TO-ROW, E-TO-RESULT, E-TO-PARAM, E-TO-LOOP, E-TO-RECURSION, E-TO-AUTHORITY, E-TO-CALL |
| ⊢_fmt (§5.14) | `lower.rs` | generated `Nib{N}o{K}` storage with `elem` accessor (derivation D-C1); codes outside the X1 list (`e8m0`, `e2m1x2`) are E-OUT-OF-SCOPE-<CODE> |
| ⊢_sch, completeness side (§5.14) | `analysis/sched.rs` | E-SCHED-AMBIGUOUS, E-SCHED-REASSOC, E-SCHED-TARGET |
| ⊢_spec (§5.14) | `analysis/spec.rs` | E-CLAIM-KIND, E-CLAIM-INADMISSIBLE |
| Meaning and traps (§6) | `interp.rs` | trap kinds ovf(op), div0, divovf, shift, idx, slice, range, unwrap, expect, hole(name), assert, panic, unreachable, req(f), ens(f), inv(T) |

Ownership works on places rooted at a local, directly or through a reference: `(*r).f` is rooted at
`r` with a path that starts with `*`, as NLL roots it, so reborrows of `&mut` parameters and
accesses through them are checked against each other. Loans are named by creation site (F-80);
loops are evaluated to a fixpoint of the state at their head, including the states at `continue`,
and the state after a loop joins its exits and its `break`s. `break` and `continue` end the scopes
they leave (T-Jump), and a Linear binding in a `match` arm exists in that arm only. A parameter
carries one symbolic loan per reference position of its type (F-62), and destructuring keeps each
component's positions. Closure bodies own their by-move captures; a closure's loan transfer
(λ_q, λ_σ) applies wherever it may run: called directly, or passed to a std or user function.
Higher-ranked closure parameters (F-107) carry a loan that may not be stored into a capture or
returned.

Grades resolve every write through a reference to the places it may point to (`target*`, F-39):
a provenance per reference-carrying value (the places, and the address grade of what chose among
them), through `if`/`match`, patterns (`Some(r)`, `for r in v.iter_mut()`, `(a, b) =
v.split_at_mut(1)`), projections and std results, aggregates, std storing calls, and nested `&mut`
(reach sets, F-91). A reference whose provenance is unknown writes, weakly, every place the body
lends mutably and every `&mut`-carrying parameter's referent.

T2 is mithi's own decision procedure, not an SMT solver: polynomial atoms over SSA and place
versions, interval reasoning, `!=` facts at interval ends, Fourier–Motzkin elimination with
degree-2 products for nonlinear goals, constant-trip loops of up to 64 iterations unrolled, every
other loop havocking what it writes (no loop invariants, DR-012). Atom intervals and equalities are
path facts, restored at branches and joined at merges. Remainders and quotients of non-negative
values by a positive divisor keep their relation to the operands (`j % n <= n - 1`, `<= j`), as do
right shifts (`i >> s <= i`), and a value merged from two branches keeps a relational fact of one
branch when the other branch's value satisfies it by its interval (the per-arm implication, used
as a case split: `let j = if i < n { i } else { 0 }; y[j]`). A write through a reference, a `&mut`
argument, a reference held in a local, or a closure call gives every place it may write a new
version (F-44); a write whose place cannot be resolved gives every address-taken local one. When
its evaluation budget runs out, every trap site of the body counts as undischarged. It emits no
certificates. An obligation it cannot prove stays a runtime check (may_trap) outside kernels and is
E-KERNEL-OBLIGATION inside them.

The interpreter runs the serial projection: `par for` runs in index order, so the lowest failing
index wins and the trap report names it (`[par i=2]`, §6.4); `deterministic` blocks have no dynamic
effect (§6.6); a trap reports its kind, definition and source anchor and the Linear values it
abandons, newest first, including temporaries already evaluated in an argument list or aggregate
(§6.3, F-42); `requires`/`ensures` are checked at run time; `canon::sum16` uses 16 lanes
(index & 15) and then the 8, 4, 2, 1 tree; f16 widening is exact (tested on all 65,536 inputs);
`f32::max`/`f32::min` follow the FF-NANMAX pin; `f32::NAN` is `0x7fc00000` at run time and raw for
the checker (note §5.3); `format!` follows Rust's placeholder grammar (positional arguments, fill
and alignment, sign, `#`, zero padding, width and precision including `N$` and `.*`, Display,
Debug and `{:#?}`, radix and exponent formats). A closure copied or cloned owns a copy of its
by-move state, and one called in place keeps it (K-CloCopy, F-104) [M: rustc 1.99.1 gives the same
values, `tests/review_2026_10_23.rs`].

## Agreement with the note

`tests/verdicts.rs` [M: `cargo test -p mithi --test verdicts -- --nocapture`, laptop, 2026-10-23,
against the working-tree verdicts.json with SHA-256
`777d7d6f2dc5509bbe4f80971dbe0766f4fb99872e63ecf2d14fb768fb9f7795`: the note's third review round,
uncommitted, which differs from its last commit `5e16fbb`; the snippet hashes it records all
matched]:

| Set | Rule | Result |
|---|---|---|
| Canonical and derived items D-C1..D-C8, D-D01..D-D27 | `verdict` for x1 / x1-front-end, `x1_expected` otherwise; primary code must match | **35/35 agree** (29 accept, 6 reject with the expected E-OUT-OF-SCOPE-<KW>) |
| Snippet hashes | SHA-256 per verdicts.json's hash rule | 35/35 match |
| Gate negatives N-01..N-06 | uncommented in their parent snippet (N-05: the release line deleted) | **6/6 agree** (E-DYN, E-REF-FIELD, E-REF-ESCAPE, E-LOCAL-RETURN, E-LINEAR-DROP, E-REF-ESCAPE) |
| Supplementary items: every negative item with `gate_item` false, N-07..N-109 (reported, not gate items, Q11) | constructions written in the test from the prose, the expected verdict read from verdicts.json; an item with no construction fails the test unless listed as not constructed | **107/107 constructions agree** (102 items; N-19, N-70, N-73, N-77 and N-87 have two constructions each); N-38 not constructed (a hint port's stack budget, M4) |
| N-19's reason | `n19_reason`: with the call, the body is blamed for the Linear capture `l` and `c` is consumed; without it, `c` is not consumed | holds |
| Secondary facts (row, may_trap) | where verdicts.json states them; a difference fails the test | 23/23 same |

How to read this: at this revision no item disagrees, so no item needs a "mithi or note wrong"
diagnosis. The test's `DIAGNOSED` list has one entry, N-43, which applies only against the
verdicts.json of commit `5e16fbb`: there N-43 expects E-BORROW-OUTLIVE, while the third round
(F-107) and rustc 1.99.1 (E0521 [M]) give E-LOCAL-MUT-STORE, so this revision passes whether or not
the third round's verdicts.json lands first [M: both versions run, 2026-10-23; 63/63 with N-43
diagnosed against `5e16fbb`'s]. The note's third round (§12.2)
listed 18 verdict or code disagreements of mithi at `dcd4c87` (N-43 and 17 items of N-70..N-109)
and two interpreter values (N-96, N-97); each was a mithi change, made here (Review log, 2026-10-23).
Earlier, before the 2026-10-16 review, the harness covered N-07..N-39 only, and 15 of the 28 later
items disagreed; each was a mithi defect. None was resolved by editing the note. The supplementary
constructions are mithi's (and the reviewers') reading of prose and are weaker evidence than the
snippet items. The 2026-10-23 review found that agreement does not mean soundness: N-19 agreed for
the wrong reason (now `n19_reason` checks the reason), and the review's write-through-reference,
`par` and closure-transfer holes were in no item until they were added as regression tests.

Harness conventions (stated in `tests/verdicts.rs`):

- "prelude" = mithi's std + `prelude/canonical.mith` (derivations §P) + the canonical snippets
  other snippets name (D-C1, D-C2, D-C3), read from the documents at their recorded lines;
- a snippet that defines an item with the same path as a prelude item replaces it (derivations §V,
  F-87);
- snippets §P places in `mod store` (D-C5, D-D05, D-D06, D-D14, D-D15, D-D22) are checked in module
  `store`; the manifest grants `declare_deterministic = ["store"]` (01 §11);
- `…` is accepted as an elided body (`--doc-snippets`); D-C7's loose statements are the body of the
  prelude's `snippet_c7` (`--loose-host`).

## Other tests

[M: `cargo test -p mithi -j4 -- --test-threads=4`, 2026-10-23, laptop, rustc 1.99.1: 48 Rust tests,
all pass; 11 s wall time with the build up to date. Earlier: 39 tests, 2026-10-16]

- `tests/corpus.rs`: nine programs, each accepted and each with `#[test]` functions that pass under
  the interpreter: six in the shape of the X1 public smoke set (DESIGN §5.2: S-NORM-0, S-EVICT-0,
  S-STORE-0, S-FMT-0, S-ROUTE-0 simplified to plain top-k, S-Q4-0), ordinary Rust-shaped code
  (`misc`), std methods (`stdx`), and Rust's meaning for casts, integer and float operations,
  formatting and ordering (`semantics`; expected values are Rust's documented results, rustc was
  not run [inference]). All were written by mithi's author, so they are a regression suite, not the
  other-family twins ROADMAP §3.2 asks for.
- `tests/ownership.rs`: 97 small programs with Rust's verdict (reject with the note's code, or
  accept), from Rust's rules [inference: rustc was not run on them, except r26, measured on
  2026-10-23], the bodiless-function rule, and `r19_blames_the_second_call` (r19's error must be at
  the second `c()`, not in the closure body).
- `tests/review_2026_10_23.rs`: 98 table cases from the 2026-10-23 review and the reviser's
  companions (grade write targets 26 and 14 accepted twins, T-Cover 3, `par` 11, closures and loans
  33, T2 8, rows and policies 3), and a run-time test of closure state, `mem::swap` of references
  and `Option::as_mut`. Each ownership expectation and run-time value is rustc 1.99.1's [M].
- `tests/interp.rs`: every trap kind with its anchor, `par for` lowest index named in the report,
  abandonment order (locals and temporaries), recursion to the frame limit without a crash,
  exhaustive f16 widening, the canon sum16 tree order.
- `tests/review_*.rs` (the review of 2026-10-16): 519 table cases generated from the reviewers'
  probes and the reviser's companion cases, each verdict checked when the table was generated
  (ownership and loans 138, `par` 96, kernels and T2 49, rows, grades and policies 108, surface
  128), plus run-time checks of `format!` and labelled blocks, a determinism test (20 repeated
  checks in one process give identical JSON), and a classification of every allocating std
  builtin (C-ALLOC).
- unit tests: SHA-256 vectors, the manifest parser.

Performance [M: 2026-10-16, laptop, debug build]: a straight-line body of 4,000
`let x{k+1} = x{k} + 1;` over a `u32` parameter checks in 0.4–0.6 s, and 20,000 in about 0.9 s
(before the review, 400 took 14 s: T2 collected every fact for every goal, and the ownership pass
scanned every holder for every use). [M: 2026-10-23, laptop, debug build, best of two runs, the
revision against the pre-revision binary]: 4,000 lines 0.22 s against 0.19 s; 20,000 lines 0.63 s
against 0.61 s; 400 sequential `if`/`else` joins with a `%` index 0.19 s against 0.19 s, 1,600 of
them 1.26 s against 1.22 s, and 1,600 joins whose index is chosen by `i < y.len()` 4.56 s against
4.29 s. A first version of the relational join facts made 400 joins 8x slower (a full
Fourier–Motzkin proof at every join); they now use an interval proof only.

## Not implemented

- The CLI commands and flags of DESIGN §9.2 other than `check`, `test`, `run` and
  `--no-user-traits`: `vectors` (x1v), `lift-check`, `--mutate`, `--token-map obf-v1` (DESIGN §10.4).
- `canon::topk(k, Ties::LowerIndex, Nan::Last)` (X1 DESIGN §5.1a): its Mithril signature is not
  fixed and whether it is in the X1 std is X1 record Owner question 20.
- Scoped threads, `Condvar` and the seeded green-thread scheduler of DESIGN §9.2: the interpreter
  is serial.
- `HashMap` and C-HASH, `Box`, `Rc`; trait objects are E-DYN by design.
- Execution of `cr::` and `canon_v1::` transcendentals (D-D21 softmax type-checks but cannot run;
  E-HOST-UNSUPPORTED at run time), and of `Frozen`, `SlabBuf` and `BlobFile` I/O.
- E-DET-STALE (needs ledger hashes), E-PAR-SEND (every X1 type is Send and Sync), E-TO-STACK and (t9)
  (M4). E-MONO-DEPTH covers direct self-recursion only (not chains through other generic
  functions).
- Arithmetic operators on type parameters (`a + b` with `B: Add<Output = B>`) and `sum::<T>` into a
  type parameter: E-TYPE, a false rejection; generic numeric code cannot be written (review
  finding R1-21(d)). The FF class check does run per instantiation for what does type-check.
- Moves inside closures by field (Rust 2021's disjoint capture): a closure captures whole locals.
- Field-sensitive grade cells (the note's OP-24): a grade cell is a whole local or a whole
  parameter referent, so a cover of a field or a row is a partial update (F-89), and a struct's
  untouched raw float field keeps the whole cell raw.
- Per-position result loans of std signatures (F-90) beyond what the provenance and loan rules
  above give: `next` on an iterator returns references into what the iterator borrows, through
  the iterator's own loans and provenance.
- Std: only the functions declared in `std/std.mith`; anything else is E-TYPE ("no method named …"),
  a false rejection when Rust has the method.
- `comptime` (out of scope), const generics beyond literal lengths, `u128` arithmetic beyond `i128`,
  privacy, multi-file modules (every enclosing module is treated as glob-imported, a deviation),
  `pack`/`unpack` and the integer view of formats, the OP-16 spec scope rule.
- `format!` named arguments (`{name}`, `name$`): E-TYPE; a width or precision on a compound Debug
  value pads the whole value (Rust passes it to the fields).
- Grouped diagnostics, fix suggestions and the JSON hole report of 05.
- The differential check of DESIGN §10.1 at scale (10^5 generated programs and their mutations);
  only the small comparison under [Grammar and parser](#grammar-and-parser) was run, and its
  single-token mutants are reported, not gated.
- The P-3 type comparison of DESIGN §9.5 (the type of accepted expressions): verdicts.json records
  types for almost no item, so `tests/verdicts.rs` compares verdicts and primary codes only.
- A build-time source commit in the `check --json` header (`std_sha256` covers the std and prelude
  texts; the binary's own hash is the freeze record's).

## Interpretations (each needs review)

1. **E-FF-CLOCK scope.** mithi reports reading a clock as E-FF-CLOCK only in code reachable from a
   kernel or in a `timing_only` context; elsewhere a clock read is the `time` effect and grades as
   nondeterministic (this is what makes N-13 an E-GRADE, as verdicts.json expects). The
   2026-10-23 review found that the note's §5.0 with (k5) can be read the other way (a clock read
   in a `#[grade(exact)]` function as E-FF-CLOCK); mithi keeps N-13's reading, and the note's text
   is handed to the CC track (finding 15).
2. **Bodiless functions** in user code are accepted only under `--doc-snippets` (N-03 is a
   signature only); otherwise a function outside a trait without a body is E-TYPE, as Rust rejects
   it.
3. **Prelude override and placement** as in the harness conventions above; `Lease` is also declared
   in the prelude because `Store::lease` names it.
4. **Fixture anchors**: a fixture's subject is a definition whose whole body is the block, or
   `<definition path>@det<k>` for the k-th `deterministic` block (from 0) [prov, mithi: until 05
   fixes anchor syntax].
5. **Prelude additions**: `StoreState.heat` and `.counter`, `Lease` in `mod store`, a
   `forward_token` stub, bodies for `Matrix` accessors that their `ensures` fix (each `ensures` is
   still checked).
6. **`--subset checker` is the default** (provisional, pending note Q9). With `--subset agent`, the
   canonical snippets that use `par for`, `deterministic`, `schedule`, `spec` or `linear` are
   rejected with E-X1-NOTYET-<KW>, which the agreement rule counts as a disagreement.
7. **Codes the note does not name** (provisional, listed in `src/diag.rs` `MITHI_CODES`): E-PARSE,
   E-MOVE-USED, E-UNRESOLVED, E-X1-NOTYET-CANON (also in X1 DESIGN §5.1a), E-HOST-UNSUPPORTED,
   E-GRANT-LOSSY, E-SCHED-TARGET. The E-X1-NOTYET-<KW> suffixes other than CANON follow the note's
   §12 pattern (PATH for `#[path]`, ENV for `env!`/`option_env!`, INCLUDE for the `include*!`
   macros, X1 DESIGN §9.1).
8. **IEEE and bit-level methods as primitives for (k3).** `std.mith` marks as `#[exact_std]`, so
   that kernels may call them, methods that C-EXACT-STD (§12) does not list: on f32 `to_bits`,
   `from_bits`, `abs`, `sqrt`, `mul_add`, `round`, `round_ties_even`, `floor`, `ceil`, `trunc`,
   `recip`, `copysign`, `clamp`, `total_cmp`, `partial_cmp` and the `is_*` predicates; on f64 the
   same kind (not `max` and `min` since 2026-10-23: F-113, their signed zero is unpinned, so they
   are not exact_std and their results carry the platform taint); `<[T]>::is_empty`; and the
   integer `is_power_of_two`. C-EXACT-STD
   says every other std function is E-KERNEL-CALL; mithi reads §5.3's IEEE operations, payload-blind
   functions and observers as primitives rather than std functions [prov, mithi: pending note
   review; `is_power_of_two`, `partial_cmp` and `is_empty` are the least clear].
9. **Direct policy calls return hint values.** At X1 a `policy fn` is called directly (no hint
   port, §12), and mithi grades the result of every call of a policy fn γ_sh, as F-57 grades hint
   values, so a policy's result reaching an exact sink is E-GRADE [prov, mithi].
10. **One index function per place in a `par for`.** §5.9's write premise asks each write to be
   injective in the iteration variable; two writes with different index functions (`y[i]` and
   `y[i+1]`) are each injective but meet across iterations. mithi requires the writes to one place
   in one iteration to use one index function, or one factor k with constant offsets less than
   |k| apart (`y[2*i]`, `y[2*i+1]`); index functions are affine forms read off the syntax, with
   casts only when lossless and constant factors only when non-zero [prov, mithi; see
   [Findings](#findings-for-the-note-and-the-x1-design)].
11. **Labelled blocks** are elaborated as §3.2 says (a one-trip loop, `'a: loop { break 'a { … } }`).
   An unlabelled `break` directly inside a labelled block is E-TYPE (rustc E0695) and `continue 'a`
   naming a block is E-TYPE (E0696); an unlabelled `continue` inside a labelled block continues the
   innermost loop, which the parser labels if it has no label.
12. **λ_q and λ_σ** (F-61, F-93, F-94, F-99; revised 2026-10-23): wherever a closure may run (a
   direct call, or a std or user call whose argument type mentions the closure), every by-mut
   captured place that can hold a loan receives the call's non-closure argument loans (not those
   at higher-ranked parameters), the closure's by-ref capture loans and what its by-move captures
   carry, and each capture's current loans in place of its capture symbol, but never a loan **on** a
   by-mut captured place. A capture that is a reference goes through `store_into`, so a transfer
   into a parameter's referent is E-LOCAL-MUT-STORE. A closure that writes its by-move state gets
   the same loans in the closure value (λ_σ). This over-approximates what the body stores; before
   2026-10-23 closures passed to a call got no transfer at all, and the closure's own capture loans
   were transferred (a false E-BORROW-CONFLICT, N-84).
13. **Symbolic loans per reference position** (F-62; replaces "per parameter", 2026-10-23): a
   parameter has one symbolic loan per reference position of its type. A by-value destructuring
   of a local whose position is known (`let (v, d) = t;`, `Some(r) = o`) gives each binding only
   the loans at its own positions, and E-LOCAL-MUT-STORE accepts a stored symbolic loan of the
   destination's parameter only on the destination's own path (its position, a position inside
   it, or a reference it is reached through). Where a local's position is unknown (a reborrow, a
   call result), the old per-parameter rule applies.
14. **Implicit reborrow.** A `&mut` local passed where the callee declares a `&mut` parameter is
   reborrowed (`&mut *r`), as Rust does at that coercion site, not moved, also through an unsize
   coercion (`&mut [u32; 4]` for `&mut [u32]`, 2026-10-23); elsewhere (`let a = r;`) it moves.
15. **Linear scrutinees.** A `match` that consumes a Linear value needs every arm to consume its
   Linear payload (`Some(_)`, a `ref` binding, or `_` over variants that carry one is
   E-LINEAR-DROP); `if let` on a Linear place consumes it on both paths only when the other
   variants carry no Linear value, and otherwise only on the matching path. The note now states
   this (F-111).
16. **Strong update through a whole-place argument** (F-78, F-91): when an argument lends a whole
   place (`&mut x`, `&mut *y` of a `&mut` parameter) at a parameter `&mut τ` whose τ holds no
   reference, the callee's final referent grade replaces the place's; any other argument (an
   element, a field, a local reference, a may-alias set) is a weak update of its reach set. The
   update also joins the argument's address grade (finding 7 of 2026-10-23: T-Call as written
   omits it).
17. **Where E-BORROW-OUTLIVE is anchored** (2026-10-23): at the closing brace of the scope that ends
   (for `break`/`continue`, at the jump), not at the scope's start, so that within class 4 the
   cause (`E-REF-ESCAPE`, an `E-LOCAL-MUT-STORE` at the store) comes first by source position, as
   rustc reports E0515 for `ow05` [M]. The note's §5.16 does not fix anchors (finding 16).
18. **Higher-ranked closure parameters** (F-107, measured): a closure parameter is higher-ranked
   when the closure is passed where an `Fn*` bound writes that parameter as a reference, or when
   its written type mentions a reference **and the closure has no expected signature**. rustc
   1.99.1 compiles `v.iter().for_each(|x: &u32| out = x)` and `.map(|x: &u32| x)` [M: scratch
   probes r2, r4], so an annotation does not make a parameter higher-ranked when a bound gives the
   closure its signature; the note's F-107 says it does (handed to the CC track). Storing such a
   parameter's loan outside the closure body is E-LOCAL-MUT-STORE; returning it from a closure
   without an expected signature is E-REF-ESCAPE.
19. **(t7) for helpers** (2026-10-23): a non-policy helper that fails ⊢_to apart from (t2) is one
   E-TO-CALL at the call site in the policy, with the helper's failures as notes. A cycle in the
   policy's call graph stays E-TO-RECURSION wherever it is: (t9) reads (t5)'s "no recursion" as a
   property of the whole call graph.
20. **References of unknown provenance** (grades): a write through one is a weak update of every
   place the body lends mutably and every `&mut`-carrying parameter's referent; a read joins every
   lent place's grade. Sound, coarse; it is reached only when no provenance rule applies.
21. **Relational facts at joins** (T2): kept only when the other branch's value satisfies them by
   an interval bound or an existing fact, not by a full proof (performance, above). The note says
   T2 is QF_BV + LIA; mithi's T2 is weaker (finding 18).
22. **`par` writes** (2026-10-23): a `&mut`-carrying local used as a value (an implicit reborrow,
   a move, a copy) is a write of its whole root; a call of a closure created outside the body
   writes its by-mut captures and the places its by-move `&mut` captures point to, and a call of an
   FnMut or FnOnce closure or type parameter writes the closure itself. Two writes through a
   footprinted projection must name the same footprint (the same invariant argument), else
   E-PAR-DISJOINT (F-95, conservatively: no footprint arithmetic). An index is the iteration
   variable only when its binder is immutable and never assigned (F-103).
23. **Cover-Proj is a partial update** (F-89): the receiver's cell keeps its scope, and its NaN bit
   is reset only when the footprint's field holds all of the receiver struct's float content.
   A consequence the CC track should confirm: the third round's control probe `a20_coverproj_ctrl`
   (no write to the raw `scale` field) is now rejected, because the caller's `scale` passes through
   raw.

Open question (provisional, pending Q9, not decided in code): X1 DESIGN §9.1 says "T2 is not part
of X1" and lists `ensures` and `invariant` proofs as outside the agent subset, while note §5.10 makes
an undischarged kernel obligation E-KERNEL-OBLIGATION. With `--subset agent`, mithi keeps its own T2
for kernel obligations and accepts `ensures` clauses (checked at run time), so which decision
procedure decides acceptance of `kernel fn` in the agent arm is open.

## Self-review on 2026-10-16

After the agreement tests passed, mithi was probed with programs outside the note's items. That
found and fixed, in mithi only (each case is now in `tests/ownership.rs` or `tests/corpus/`):

- moves out of a place behind a reference or an index were accepted (now E-MOVE-BORROWED), and a
  move of a borrowed local was accepted (now E-BORROW-CONFLICT, access mode Move of §5.4);
- a move of one field moved the whole local, so moving two fields was rejected (Rust's partial
  moves are now tracked per field path);
- loans were lost through std calls on a reborrow (`s.iter()` with `s: &[T]`) and through the
  `Vec` to slice deref (`v.iter()`), so iterator invalidation (`for x in v.iter() { v.push(*x) }`)
  was accepted; two `&mut` borrows in one argument list were accepted;
- disjoint field borrows (`&mut s.a`, `&mut s.b`) were rejected;
- `s.clone()` with `s: &String` resolved to `<&String as Clone>::clone` (Rust's by-value probing
  step was missing), and `String == &str` was rejected;
- `{:x}`, `{:b}`, `{:o}` printed decimal, and zero padding ignored the sign.

The self-review did not find the defects the independent review found (below); agreement numbers
do not show that mithi is free of such gaps. The checker precondition's planted corpus and its
accepted twins (DESIGN §9.5: written by another model family without access to mithi's source)
are the stronger check; they do not exist yet.

## Review log

**2026-10-16. Reviewers: two, Claude, same family, independent context** (neither wrote mithi or
the note). Lenses: reviewer 1, soundness of T2, ownership, `par`, linearity, grades and rows
against the note, and agreement with verdicts.json beyond N-39; reviewer 2, soundness, robustness
(stack depth, budgets), determinism, performance, std signatures, build and freeze hygiene, and
test quality. The reviewers' probe files (929 programs and 249 one-line cases) are in the session
scratch area, not in the repository; the reviser rebuilt mithi and re-ran every probe, and the
ones a finding rests on are now test cases.

Counts: 39 findings (reviewer 1: 7 blockers, 9 majors, 5 minors; reviewer 2: 2 blockers, 7 majors,
9 minors). **All 39 accepted**: 34 fixed in full; 5 fixed in part with the rest recorded above
(R1-21(d): arithmetic on type parameters, under Not implemented; R2-6: the coercion-row check is
replaced by charging a function's row where it is named, since mithi's fn types carry no row; R2-16:
the mutant comparison stays reported, not gated, and the 10^5-program check is not run; R2-17: no
P-3 type comparison; R2-18: the build commit in the JSON header, and the root `.gitignore`, which is
outside this track's files). No finding was rejected. Within findings, four probe expectations were
judged wrong and the tests record the reviser's verdict instead:

| Probe | Reviewer expected | mithi and the reason |
|---|---|---|
| br2/e11 `struct P { a: &mut u32 }` | E-BORROW-CONFLICT | E-REF-FIELD: a reference field is J2's rejection (note §5.1), before any borrow |
| c2/i06 two `impl T for S` | E-TYPE | E-COHERENCE: conflicting impls are the note's coherence code (§5.12; the reviewer's own c3/s04 expects it) |
| c12/y04 `#[derive(PartialEq)]` over `T: PartialEq` and `fn(u32)` | E-TYPE | accept: function pointers implement PartialEq in Rust [inference] |
| c7/p39 `y[i + 0] = …; y[0 + i] = …` | reject | accept: both writes are element i of the iteration's own index, so there is no race |

One existing test was corrected in the same pass: `tests/ownership.rs` m12 (`if let Some(x) = o {
return x.len(); } let p = o;`) is accepted by Rust, since the move happens in the matching arm,
which returns [inference: MIR moves per arm]; m12 now has no `return` (E-MOVE-USED) and m12b keeps
the accepted form.

What changed, by finding (R = reviewer, numbered in the order given):

- R1-1 T2 path sensitivity: atom intervals and equalities moved into the per-path state, joined at
  merges; facts a short-circuit operand's calls add are kept as side facts of the outcome that
  evaluated them. The probes that trapped at run time with may_trap=false are now
  E-KERNEL-OBLIGATION.
- R1-2 T2 versions through `&mut` calls, local references and closure calls (F-44); R2-1 the
  budget: every trap site counts as undischarged when it runs out.
- R1-3 signed shift amounts: both `0 <= s` and `s < bits` are obligations (also for `<<=`/`>>=`);
  R1-21(c) `!=` facts make `-a` with `requires a != i32::MIN` provable.
- R1-4 = R2-2 places through references; R2-3 loop fixpoint with loans; R1-6 T-Jump at `break` and
  `continue`; R1-7 E-LOCAL-MUT-STORE for storing std calls and by-value `&mut` holders, and
  T-CallClo's transfer (N-43, N-44, N-46); R1-9 `T: Copy`; R1-10 captures of called callables
  (N-63 is then E-MONO-DEPTH, now implemented for direct recursion); R1-11 Linear arm bindings,
  plus the arm-discard check; aggregate components are live until the aggregate is built.
- R1-5 = R2-4 T-Par (casts, constant factors, multiple writes, whole-place reads), R1-15 labelled
  jumps out of a `par for`, R1-21(a, b) `n - 1 - i` and `2*i .. 2*i + 2` accepted, N-47's
  overlapping footprints rejected.
- R1-8 the supplementary harness reads verdicts.json (N-07..N-69); the 15 disagreeing items were
  fixed in mithi: N-40/41 (F-60: closure summaries per call, by-move state in the closure value),
  N-45 (F-62), N-52 (F-67), N-53/54 (F-68: closure exit context), N-55, N-58 (struct fields count
  as float content), N-65 (F-69), N-69 (F-85: break values), N-47, N-61, N-63; N-56 (F-71:
  transitive exercised rows) and N-62 (F-78: strong update) were constructed by the reviser and
  fixed too.
- R1-12 C-ALLOC labels (`collect`, `to_vec`, `format!`, clones of heap values) with a
  classification test; R1-13 `f32::NAN` and NaN-valued constants raw; R1-14 labelled blocks
  (grammar, parser, elaboration); R1-16 abandoned Linear temporaries; R1-17 f16 operators and
  `dbg!` report only their false-friend codes; R1-18 policy results graded γ_sh (Interpretation 9);
  R1-19 Interpretation 8; R1-20 the secondary-facts test asserts and the par trap names its index;
  R1-21(d) the FF check per instantiation.
- R2-5 and R2-12 grade fixpoints without caps that cut them short; R2-6 function values; R2-7 impl
  signatures, coherence, E-SPECIALIZE, duplicate definitions (R2-14); R2-8 the large-stack thread,
  the nesting limit and the deep-recursion test; R2-9 ordered maps and the determinism test; R2-10
  std bounds (`sort` needs Ord, `contains` PartialEq, `to_vec` Clone, `sum` the item type), derive
  bounds and the formatting traits; R2-11 the `format!` grammar; R2-13 option validation and the
  PATH/ENV codes; R2-15 T2's atom index and pruned Fourier–Motzkin rows, and the ownership pass's
  quadratic scans; R2-16 the grammar's differences closed (`matches!` patterns, `2.`, one level of
  nested comments, Unicode scalar escapes in the grammar and the lexer); R2-17 the review tests;
  R2-18 the freeze profile and `std_sha256`.

Found while revising, beyond the findings (each now a test case): a move inside a `loop` that
`break`s was not seen after the loop (`loop { let _x = v; break; } v.len()` was accepted); a `&mut`
local passed to a `&mut` parameter was moved instead of reborrowed (a false E-MOVE-USED on
`inc(r); inc(r)`); `(&mut x, &x)` and `[&mut x, &mut x]` were accepted (aggregate components are
now live until the aggregate is built); a closure result borrowing a by-mut capture was accepted
(the §5.7 result discipline, reviewer probe cl/c12, now E-REF-ESCAPE); and a `return` inside a
closure body counted as a return of the enclosing function.

Command for Pierce (outside this track's files; not run): add a repository `.gitignore` with the
line `/target/`, so that a `cargo build` without `CARGO_TARGET_DIR` leaves no untracked output.

Not yet done after the review: a second, independent review of the revision (the fixes were made
by one context with the expected verdicts in view), and the other-family planted corpus.

**2026-10-23. Reviewer: one, Claude, same family, independent context; blind and adversarial
(verdicts.json was read only after the predictions were written).** This is the review the
checker precondition (ROADMAP §3.2) asks for after the 2026-10-16 revision, within the
same-family limit. Lenses: soundness of grades, `par`, ownership and T2 against the note; rows and
policies; the note's own rules; run-time meaning against Rust. Probes [M, laptop, the pre-revision
build of this worktree]: 154 blind probes in set 1 (141 matched the reviewer's prediction), 34 in
set 2 (26 matched), and about 70 follow-up programs; they are in the session scratch area
(`mithirev/probes.py`, `probes2.py`, `x/*.mith`, runner `run.py`), not in the repository. Of the 21
differences, 10 were mithi bugs, 1 a std gap, 5 ambiguities of the note, 1 open (OP-20, ln15) and 4
the reviewer's own errors (ff14, kc21, os02, gr22; stated by the reviewer and confirmed here).

Counts: 20 findings (3 blockers, 5 majors, 12 minors). **All 20 accepted**; none was rejected.
12 were mithi defects, fixed with regression tests. 7 were findings against the note: mithi now
implements the sound reading of each where it has one, and the note's text is handed to the CC
track ([Findings](#findings-for-the-note-and-the-x1-design) 7 to 13), because the note is that
track's file and that track was revising it the same day. 1 was this log. In 4 findings the
proposed fix was adopted in part or replaced (6, 10, 13, 16), with the reason in the table.

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | blocker | writes through references not registered in `refs` were dropped; `refs` held one target | Fixed (`grade.rs`): every reference-carrying value has a provenance (places, address grade) through `if`/`match`, patterns, `for` items, projections and std results, aggregates, std storing calls (`push`, `swap`), nested `&mut` (reach sets); unknown provenance writes every lent place weakly. h9, h10, h12, h13, h16–h20, h22–h27 now reject; their canonical twins are accepted |
| 2 | blocker | `par` W missed implicit reborrows (`set0(y, i)`) and calls of closures or FnMut parameters | Fixed (`par.rs`, shared helper `implicit_mut_uses` in `analysis/mod.rs`): c1, pa14, c6, c8, pa15, c10 are E-PAR-DISJOINT; `Fn` closures and `F: Fn` parameters stay accepted |
| 3 | blocker | λ_q applied only at direct closure calls | Fixed (`own.rs` `closure_transfer`): at every call whose argument type mentions the closure, std or user, with the closure arguments' own loans excluded (F-99). g3, g4, g5, g7 are E-BORROW-OUTLIVE, as rustc E0597 [M] |
| 4 | major | by-move captures were moved in the state the body was checked in | Fixed: the body owns its by-move captures; a body that moves one, or a Linear by-move capture, makes the closure FnOnce (`captures.rs`, which also captures a pattern-moved scrutinee by value); a Linear by-move capture must be consumed in the body (T-Lin, K-LinClo). a1, a2, a5, b1–b4, ln06 accepted (rustc compiles them [M]); a4 and r19 reject at the second call; `n19_reason` and `r19_blames_the_second_call` check the reason |
| 5 | major | T-Cover premise 3 missed `poke(y)` | Fixed (`t2.rs`, the shared helper): e1b and kc38 are E-NAN-RAW-SINK |
| 6 | major | one symbolic loan per parameter; stores at `F: FnMut(&u32)` bounds accepted | Fixed: per-position symbolic loans, kept through destructuring (e2, ow33 E-LOCAL-MUT-STORE; rustc: "lifetime may not live long enough" [M]); higher-ranked closure parameters (f14, f15 E-LOCAL-MUT-STORE; rustc E0521 [M]). **In part:** the destination's own path is accepted, not only its exact position, so `let x = v[0]; v.push(x)` stays accepted (rustc compiles it [M]) |
| 7 | major | note: T-Call's `θ_mut,j` update lacks the address grade | mithi joins it at T-Call and T-CallClo (h9 E-GRADE); the note's text is handed to the CC track (Findings 7) |
| 8 | major | note: E-LOCAL-MUT-STORE does not cover closure-call transfers | mithi stores a transfer into a reference capture through `store_into`: g1 and its unannotated twin are E-LOCAL-MUT-STORE (rustc rejects both [M]); handed to CC (Findings 8) |
| 9 | minor | implicit reborrow missed through an unsize | Fixed: d3 accepted (rustc compiles [M]) |
| 10 | minor | T2 lost `j % n < n`, `i >> 1 <= i`, branch-merged indices | Fixed: relational facts for `%`, `/`, `>>`, and at joins when the other branch's value satisfies them by its interval (kc27, e4, f5, kc10 accepted; negative controls still E-KERNEL-OBLIGATION). **In part:** a full proof at each join made long bodies quadratic, so it is interval-only (Interpretation 21) |
| 11 | minor | `let j = i; y[j]` rejected | Fixed: an immutable, once-bound `let` copy is read through (pa11 accepted) |
| 12 | minor | `uses { unsafe }` E-PARSE; declared `foreign` unchecked | Fixed: rw08 E-GRANT-UNSAFE, u1 E-GRANT-FOREIGN; the Lark grammar still rejects `uses { unsafe }` (Grammar table) |
| 13 | minor | a helper's (t5) failure reported as E-TO-LOOP | Fixed: E-TO-CALL at the call site with the helper's failures as notes (po10). **In part:** recursion stays E-TO-RECURSION (Interpretation 19; pol/p08 unchanged) |
| 14 | minor | `Option::as_mut` missing | Added (std, interpreter): ow31 accepted; h22/h23-style writes through it grade correctly |
| 15 | minor | note: FF-CLOCK's class in non-kernel exact code | mithi keeps N-13's reading (Interpretation 1); handed to CC (Findings 9) |
| 16 | minor | note: §5.16 does not fix anchors or ties | mithi anchors E-BORROW-OUTLIVE at the scope's end (Interpretation 17): ow05 is E-REF-ESCAPE, as rustc E0515 [M]. **Not adopted:** a sort by the class line's list index; handed to CC (Findings 10) |
| 17 | minor | note: (t5) `0..slots.len()`, (t6) "escaping closure" | mithi keeps the literal reading (po04 E-TO-LOOP, po11 E-TO-AUTHORITY); handed to CC, to pin before the freeze (Findings 11) |
| 18 | minor | note: §5.10 Φ omits SSA definitions and per-arm implications | mithi keeps the implications T2 can check cheaply (finding 10); handed to CC (Findings 12) |
| 19 | minor | note: no T-Lin premise for closure bodies; N-67 abandons on a normal path | mithi implements the premise (finding 4); both texts handed to CC (Findings 13) |
| 20 | minor | this README: the 63/63 claim, r19, the blind-review gap | This entry; the agreement section; `n19_reason`; `r19_blames_the_second_call` |

**The note's third round (§12.2 of the note, the CC track, 2026-10-23, uncommitted).** It added
N-70 to N-109 to verdicts.json, listed 18 verdict or code disagreements and two run-time values of
mithi at `dcd4c87` as changes for this track, and left `supplementary_items` failing until the
items were constructed. This revision constructs all 40 items (44 constructions) and makes each
agree: Cover-Proj's partial update (F-89, N-74); reach sets (F-91, N-77); by-move closure state and
its stores (F-92, F-93: N-78 to N-81); capture symbols instead of capture loans (F-94, N-84);
footprints and receivers in `par` (F-95, F-102: N-87, N-93); immutable binders (F-103: N-94, N-95);
closure Copy and Clone with their own state (F-104: N-96 and N-97 now evaluate to 1 and 0, as rustc
[M]; `c.clone()` accepted when no capture is by mut); higher-ranked annotated parameters (F-107:
N-43's new code, N-101, N-102); per-position loans (N-103); f64 `max`/`min` (F-113, N-108). The
CC track should confirm one consequence: its control probe `a20_coverproj_ctrl` is now rejected
(Interpretation 23).

Found while revising, beyond the findings (each now a test case):

- **typeck applied the `&&T → &T` coercion before trying zero dereferences**, so
  `mem::swap(&mut r1, &mut r2)` with `r1: &mut u32` swapped the referents: mithi computed 1001
  where rustc 1.99.1 gives 110 [M]. A false friend in the interpreter, now fixed (`typeck.rs`
  `coerce`). Fixing it exposed that the ownership pass exchanged loans only between two plain
  places; br/b12 (`swap(&mut r, o.as_mut().unwrap())`) was briefly accepted and is E-BORROW-OUTLIVE
  again.
- **The interpreter shared a closure's by-move state between copies** (`let mut d = c; d(); c()`
  gave 2; rustc gives 1 [M]).
- **Grade holes the reviewer did not probe:** references stored by `Vec::push` or swapped by
  `mem::swap`, a user projection called with an unsized argument (`*first(&mut a) = h`), a moved
  reference (`let s = r; *s = h`), a reference inside a tuple, and the `&mut` items that
  `iter_mut().for_each` and a user `fn each<F: FnMut(&mut u32)>` hand to a closure.

Changed test expectations, each with its evidence: `review_par` c7:p34 E-PAR-DISJOINT → E-PAR-RACE
(finding 11 makes `let k = i` affine; the read of `y[0]` is the race); `review_ownership`
reviser:closure-transfer-ok accept → E-LOCAL-MUT-STORE (`|x: &u32|` is higher-ranked; rustc E0521
[M]), with the accepted unannotated twin added; `ownership` r26 E-BORROW-OUTLIVE → E-REF-ESCAPE
(rustc E0515 [M]; Interpretation 17); `review_grades` gr/g04 E-NAN-RAW-SINK → E-GRADE (F-113).

Regression sweep [M, laptop, 2026-10-23]: the pre-revision binary and this revision on the 2,057
`.mith` probe files of the earlier reviews, fixes and note rounds in the session scratch area
(`mithi-rev`, `mithi-fix`, `mithi`, `cc3`), with no flags and with `--canonical-prelude`: 19
verdicts changed, every one a third-round item of the note in the direction §12.2 expects or a
fixed false rejection (m07b, m22, m23), plus `a20_coverproj_ctrl` (above). Every ownership
expectation of the new tests was measured with rustc 1.99.1 (`--edition 2021`, the toolchain
pinned in `rust-toolchain.toml`, already installed under `.rustup-mithril`; nothing was installed).

Not yet done: a second review of this revision (the fixes were made by one context, with
verdicts.json and the reviewer's predictions in view); the other-family planted corpus; the
Lark grammar's `uses { unsafe }`; field-sensitive grade cells (OP-24).

## Findings for the note and the X1 design

1. **A kernel that writes an `ActQ8` must discharge the `ActQ8` invariant**
   (`sum == q.iter().map(|v| *v as i32).sum::<i32>()`) statically. mithi's T2 cannot relate an
   iterator sum to a loop that builds it, so a quantising kernel is E-KERNEL-OBLIGATION whether it
   builds the struct whole or field by field. If X1 reference solutions quantise activations inside
   `kernel fn`, this is an amber candidate (ROADMAP §3.6) unless T2 gains a rule for it.
2. **Loop-carried indices are unprovable without loop invariants (DR-012).** A top-k kernel that
   keeps `best_i` and indexes with it later is E-KERNEL-OBLIGATION; the corpus's top-k keeps the
   best value alongside the index instead. Candidate for the note's §11 idiom list. Since
   2026-10-23 a value merged from two branches keeps a relation of one branch (`j <= n - 1`) when
   the other branch's value satisfies it by its interval (Interpretation 21), so `let j = if i < n
   { i } else { 0 }` is in bounds; relations that need a full proof at the join are still lost.
3. **`ActQ8::__invariant` may trap in mithi** (mithi does not prove the iterator sum free of
   overflow), whereas the note calls it provable by unrolling. The difference is a fact, not a
   verdict; no item depends on it.
4. **`f32::NAN`'s bits** need the Surface Map pin the note's §5.3 asks for; until then mithi treats
   it as raw.
5. **§5.9's write premise is per write.** Two writes to one place in an iteration, each injective
   (`y[i]` and `y[i+1]`), race across iterations; the note should say that the writes to one place
   share one index function, or give a stride rule (mithi's reading: Interpretation 10).
6. **§5.8 does not say how a refutable pattern consumes a Linear value** (`if let A(t) = e` when
   another variant also carries a Linear value, `Some(_)`, a `_` arm). mithi's reading is
   Interpretation 15. (Closed by the note's F-111 on 2026-10-23.)

Items 7 to 15 come from the review of 2026-10-23 (Review log). They are for the CC track, which
owns the note; none of them was in the note's draft of that day, which this track did not edit.
Each states the problem, the evidence and a proposed text.

7. **T-Call omits the address grade of a `&mut` argument** (finding 7). In §5.5, T-Call's second
   and third update lines and T-CallClo's `θ_mut,j` line write `θ_mut,j(γ̄) ⊔ pc`. When the
   callee overwrites `*a_j` without reading it, the choice of the place made under h vanishes:
   `let r = if h > 1 { &mut y } else { &mut z }; w(r, 4); y` with `fn w(o: &mut u32, k: u32) { *o = k
   }` is `cross_device` by the rule as written although y is 4 or 0 depending on h. Proposed: use
   `θ_mut,j(γ̄) ⊔ γ_addr(a_j) ⊔ pc`, with γ_addr as in T-Assign (the grades of the references a_j
   traverses and of its index and slice expressions). Add h9 and h11 (E-GRADE) as supplementary
   items. mithi does this (Interpretation 16).
8. **E-LOCAL-MUT-STORE does not cover a closure-call transfer into a parameter's referent**
   (finding 8). §5.4's premise lists "by assignment, or through a storing std call", and T-Call
   says a user call adds no loan to the caller's places. `fn put(o: &mut Vec<&u32>, d: &u32) { let
   mut c = |x| o.push(x); c(d); }` passes both, and its caller dangles; rustc rejects it [M: "lifetime
   may not live long enough"; with `|x: &u32|`, E0521]. Proposed: "by assignment, through a storing
   std call, or through a closure-call loan transfer (λ_q, λ_σ) whose target* reaches a place
   through parameter j"; restate OP-22's remainder as a soundness obligation. Add g1 and its
   unannotated twin (E-LOCAL-MUT-STORE).
9. **FF-CLOCK's class outside kernels** (finding 15). §5.0 makes `cls` depend on ctx, and (k5)
   lists FF-CLOCK among the constructs whose class is Dc in exact context, so a clock read in a
   `#[grade(exact, _)]` function reads as E-FF-CLOCK; 01's FF-CLOCK row and N-13's verdict
   (E-GRADE) say otherwise. Proposed: a per-row table in §5.0 (`cls(FF-CLOCK, ctx) = Dc` in kernels,
   kcall helpers reached from kernels and `timing_only` code; C elsewhere, where the `time` label's
   `nondet` taint gives E-GRADE at the sink), and (k5) reworded to "no construct whose class is Dc
   in a kernel".
10. **§5.16 fixes no anchors and no tie-break at one anchor** (finding 16). ow05 `fn f(v: &[u32]) ->
   &u32 { let l = [1u32, 2]; &l[0] }` gives E-BORROW-OUTLIVE and E-REF-ESCAPE (both class 4); po09
   gives four ⊢_to codes at one anchor. Proposed: name each code's anchor (E-REF-ESCAPE at the
   returned expression, E-BORROW-OUTLIVE at the end of the dying scope, E-LOCAL-MUT-STORE at the
   store, ⊢_to codes at the item header or the offending construct) and break remaining ties by an
   order the note lists. mithi anchors E-BORROW-OUTLIVE at the scope's end (Interpretation 17), so
   ow05 is E-REF-ESCAPE, as rustc reports E0515 [M]; the third round's N-79 already assumes this
   anchor ("the store is the first failure by source position").
11. **(t5) and (t6) are ambiguous for common policy code** (finding 17). (t5) allows "loops only
   over core-provided slices or constant ranges", so `for i in 0..slots.len()` is E-TO-LOOP
   although static fuel is "a polynomial in view lengths"; (t6)'s "no escaping closure", read as
   clo_E, rejects `move || k` with a Copy capture that does not escape. Proposed: allow `a..b` with
   constants or `v.len()` of a core-provided view, and say whether (t6) means clo_E or a closure
   that escapes the policy's extent. Either change flips mithi's verdicts on po04 and po11, so it
   should be pinned before the X1-subset freeze.
12. **§5.10's Φ omits SSA definitions and per-arm implications** (finding 18). Whether `let j = if
   c { a } else { b }` gives T2 a relation between j and a or b is unstated, while "QF_BV + LIA"
   implies it. Proposed: "Φ also contains each SSA definition x_k = e, and for x_k defined by
   `if`/`match` the per-arm implications (c ⇒ x_k = e_arm)"; or state that only interval facts
   survive a join. mithi keeps the implications its interval check can confirm (Interpretation
   21), so kc10 is accepted; a fuller T2 is not part of this revision.
13. **Two linearity gaps** (finding 19). (a) T-CloL/T-CloE never require a closure body to consume
   its by-move Linear captures, but N-19 "with the call" is E-LINEAR-DROP only by that premise.
   Proposed: "each by-move captured Linear value is consumed exactly once on every normal path of
   the body (T-Lin); otherwise E-LINEAR-DROP". mithi implements it; `n19_reason` checks it. (b)
   N-67 (accept) abandons Linear values of ignored `Ret` records on a normal outcome (F-83), but
   §5.8 says "Trap paths are exempt" as if trap paths were the only abandonment. Proposed: list the
   `par` Ret-join as a second abandonment site with its reason, or add a T-Par premise that makes
   N-67 a reject.
14. **F-107's annotation rule is broader than rustc** (found while revising). rustc 1.99.1
   compiles `v.iter().for_each(|x: &u32| out = x)` and `v.iter().map(|x: &u32| x).collect()`
   [M: scratch probes r2, r4]: a closure that gets an expected signature from a non-higher-ranked
   bound takes its regions from that bound, and the annotation does not make the parameter
   higher-ranked. Proposed: "a parameter is higher-ranked by its annotation only when the closure
   has no expected signature". mithi implements this reading (Interpretation 18); N-43, N-101 and
   N-102 are unaffected.
15. **F-89 rejects the third round's own control probe** `a20_coverproj_ctrl` (Cover-Proj over
   `M2.blocks` with an untouched `scale: f32`): `scale` is the caller's value, raw in general, so
   the partial update keeps the cell's NaN bit raw. This follows from F-89 as written; the CC track
   should confirm it is intended, or make cells field-sensitive (OP-24).

## Grammar and parser

`grammar/mithril_v0.lark` describes the X1 surface (05 §3 style: keyword-first items, explicit
whitespace terminals, no `%ignore`, only `%import common`; 116 rules and 21 terminals, 13,052 bytes
[M: 2026-10-16]; the ≤ 3k-token target of 05 §3 was not measured, and at 3–4 bytes per token it is
probably exceeded [inference]). The grammar is parsed with Lark's Earley parser; optional
whitespace is the nullable rule `_s`, which made parsing about 8x faster than inline `_WS?`
[M: 3.4 s against about 25 s for the 35 snippets, one run each].

`python grammar/test_grammar.py --mithi <mithi> --mutants 150` [M: 2026-10-16, lark 1.3.1]:

- canonical snippets 8/8 parse (D-C8 is the README taste snippet), derived snippets 27/27, gate
  negatives 6/6 (with the test's documentation extension for `…` and a signature without a body),
  mithi's corpus programs 10/10, malformed programs 16/16 rejected (including Unicode escapes above
  10FFFF and of a surrogate), and 6/6 forms both must accept (labelled blocks, `matches!` with a
  struct pattern and with a guard, `2.`, a nested block comment, `'\u{10FFFF}'`);
- `mithi parse` and the grammar agree on 67/67 inputs, 6/6 documentation inputs and 150/150
  single-token deletions of the snippets (sampled with a fixed seed; reported, not gated);
- the grammar checks (without the comparison) took 31.1 s on the laptop [M, one run; 22.4 s in an
  earlier run of the same day, so the time varies with load].

mithi's parser is hand-written and accepts a superset of the grammar. Known differences (the
grammar rejects, mithi accepts unless stated):

| Input | Why |
|---|---|
| `if(x)`, `return(x)`, `&mut[u8]` | the grammar requires whitespace after a keyword in these positions; mithi lexes as Rust does |
| lifetimes, `unsafe`, `async`/`.await`, raw pointers, `<T as Trait>::X`, inner attributes, `where` on a struct, `default fn` | mithi parses them so that the checker can name the rejection (E-LIFETIME, E-ASYNC, E-SPECIALIZE, …) |
| `name!(arbitrary tokens)` | mithi skips an unknown macro's tokens and reports E-MACRO |
| `…`, a function without body or `;`, loose `let` at file level | documentation forms; the grammar has them only through the test's extension and the `loose` start symbol |
| `\| \|` (spaced empty closure) | the grammar spells it `\|\|` |
| block comments nested more than one level | Rust nests them without limit; a regular expression cannot, and the grammar allows one level |
| `if x == S { a: 1 } {}` (grammar accepts, mithi rejects) | mithi forbids struct literals in conditions as Rust does; the grammar does not encode that restriction |
| `uses { unsafe }` | the grammar's `effect` is a `NAME`, which excludes the keyword `unsafe`; mithi parses it (since 2026-10-23) so that J3 can name the rejection, E-GRANT-UNSAFE. The grammar should accept `unsafe` there too (outside this track's files) |
