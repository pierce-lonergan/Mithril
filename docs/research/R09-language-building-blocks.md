# R09 — Language semantics building blocks and compiler construction

Research dossier for Mithril, written 2026-10-11. Every factual claim carries an inline source. My own reasoning is marked **[inference]**. Confidence levels are given for the key claims. Research note: the shared web-search budget ran out partway through this task, so the later claims were checked by fetching official pages directly. Anything I could not check is marked "unverified".

---

## Summary

- **Effects = capabilities is the unifying idea.** Effekt compiles effect handlers by passing capabilities ([Effekt history](https://effekt-lang.org/evolution)). Austral builds capability security out of linear types and a single `RootCapability` handed to `main` ([Borretti 2023](https://borretti.me/article/how-capabilities-work-austral)). The WASI component model aims for "capability-safe" interfaces ([CM Goals](https://github.com/WebAssembly/component-model/blob/main/design/high-level/Goals.md)). Mithril should make effect rows and capability values one mechanism. That gives AI agents and verifiers a single, greppable record of what code is allowed to touch. [inference, high]
- **Restrict handlers to one-shot, lexically scoped ones.** OCaml 5 shipped untyped, one-shot effects with roughly 1% overhead on code that does not use them ([PLDI'21](https://arxiv.org/abs/2104.00250); [manual](https://ocaml.org/manual/5.4/effects.html)). Koka compiles typed handlers to C without a GC ([README](https://github.com/koka-lang/koka)). Koka, Effekt and Hylo all still describe themselves as research or early-stage. Mithril should adopt typed effect rows but forbid multi-shot continuations. [inference, high]
- **Memory model.** Use mutable value semantics with second-class references (Hylo-style [inout/sink](https://hylo-lang.org/)), plus linear resource types (Austral, Swift `~Copyable` [SE-0390](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0390-noncopyable-structs-and-enums.md)) and explicit arenas/regions. Raw pointers live only in code that holds an `Unsafe` capability. This avoids Rust's lifetime annotations and keeps the spec small. Rust's model is the best validated: RustBelt ([POPL'18](https://plv.mpi-sws.org/rustbelt/popl18/)), Tree Borrows ([PLDI'25](https://doi.org/10.1145/3735592)). But it is large. [inference, medium-high]
- **Staging is the right tool for Hearth's kernels.** Terra showed that a high-level stage can generate low-level code which then runs without the generator's runtime ([PLDI'13](https://www.doi.org/10.1145/2491956.2462166)). MetaOCaml guarantees that well-typed generators emit well-typed code ([BER MetaOCaml](https://tagteam.harvard.edu/hub_feeds/1936/feed_items/2100420)). Zig makes stage 0 the same language ([Zig overview](https://ziglang.org/learn/overview/)). Halide separates the algorithm from the schedule ([halide-lang.org](https://halide-lang.org/)). Mithril should combine these: same-language `comptime` plus typed `Code<T>` quotes plus separate schedules. Kernel *generators*, not hand-written ISA variants, then become the search space that AI optimisation explores. [inference, high]
- **Determinism by default is achievable and already practised by Hearth.** Cilk defines correctness relative to the serial projection, and Cilksan can certify race-freedom for a given input ([OpenCilk glossary](https://opencilk.org/doc/reference/glossary); [OpenCilk](https://opencilk.org/doc/users-guide/getting-started)). Hearth's pool rule is that "every output element is produced entirely by one thread" (`hearth/engine/src/hx_pool.h`). Mithril should build that rule into the type system (disjoint `inout` splits) and gate nondeterminism behind a `Nondet` capability. [inference, high]
- **The compiler should be a query database keyed by content hashes.** It should combine rustc/salsa-style memoised queries ([rustc-dev-guide](https://rustc-dev-guide.rust-lang.org/query.html); [salsa](https://github.com/salsa-rs/salsa)) with Unison-style hash identities ([InfoWorld](https://www.infoworld.com/article/4100673/futuristic-unison-functional-language-debuts.html)). This is the main enabler for an agent loop that generates and evaluates thousands of variants and caches their verification results. [inference, high]
- **Hot swap should follow Erlang's two-version rule, not self-modifying code.** In Erlang a module has a *current* and an *old* version, and only fully qualified calls switch to the new code ([Erlang docs](https://www.erlang.org/doc/system/code_loading.html)). The seed's "single-cycle CMPXCHG16B hot_patch" and CLFLUSH/INVD self-modifying code (I5, I7) are the wrong level of abstraction. [inference, high]
- **Backend: emit C11 first, add a custom x86-64 kernel emitter second, keep LLVM optional.** QBE has no vector types ([QBE IL](https://c9x.me/compile/doc/il.html)). The rustc Cranelift backend lists SIMD as not yet supported ([cg_clif](https://github.com/rust-lang/rustc_codegen_cranelift)). LLVM churns between versions: Hylo requires LLVM 20 specifically ([Hylo README](https://github.com/hylo-lang/hylo)). MLIR's `x86` dialect already exposes AVX-512, AVX10 and AMX operations ([MLIR x86](https://mlir.llvm.org/docs/Dialects/X86/)). A C backend must pin down FP contraction, because GCC defaults to `-ffp-contract=fast` outside ISO C modes ([GCC](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)) and Clang defaults to `on` ([Clang](https://clang.llvm.org/docs/UsersManual.html)). [high]
- **Spec budget.** I measured these on 2026-10-11 (HTML tags stripped, approximate): Austral spec ≈28k words, Go spec ≈40k, Lua 5.4 manual ≈45k, Zig 0.15.1 langref ≈63k. Mithril's normative core should fit in an Austral-sized ≤30k words (roughly 40k tokens [inference]), with a machine-readable formal core. Wasm 3.0 was the first Wasm standard produced with the SpecTec toolchain ([webassembly.org](https://webassembly.org/news/2025-09-17-wasm-3.0/)). [medium]
- **Implementation language: write the compiler in Rust, with an executable reference semantics in Lean 4.** OCaml is the strong alternative. Lean 4 is self-hosted and its compiler emits C ([de Moura & Ullrich](https://lean-lang.org/papers/lean4.pdf)). Rust has salsa, Cranelift and Tree-Borrows-level semantic scrutiny. [inference, medium]

---

## Findings

### 1. Algebraic effects and handlers

| System | Effect typing | Continuations | Compilation | Maturity (own words) |
|---|---|---|---|---|
| Koka v3 | Effect types on every function; pure and effectful are distinguished ([README](https://github.com/koka-lang/koka)) | Multi-shot allowed (general handlers) | Evidence passing plus Perceus RC, "compile directly to C code without needing a garbage collector or runtime system" ([README](https://github.com/koka-lang/koka)) | "research language … not quite ready for production use"; the README listed v3.2.9 (2026-09-17) when fetched |
| OCaml 5.x | **None**: "the compiler does not statically ensure that all the effects performed by the program are handled"; an unhandled effect raises `Effect.Unhandled` at runtime ([manual 5.4](https://ocaml.org/manual/5.4/effects.html)) | One-shot only; resuming twice raises `Continuation_already_resumed` ([manual](https://ocaml.org/manual/5.4/effects.html)) | Native runtime; mean 1% overhead on a macro suite that does not use handlers ([Sivaramakrishnan et al., PLDI'21](https://arxiv.org/abs/2104.00250)) | Production. 5.3 (Jan 2025) added deep-handler syntax ([changelog](https://ocaml.org/changelog/2025-01-08-ocaml-530)); 5.4 (Oct 2025) added labelled tuples, immutable arrays and atomic record fields ([release](https://ocaml.org/releases/5.4.0)) |
| Effekt | Effects as capabilities ([OOPSLA'20](https://effekt-lang.org/evolution)); boxes for first-class functions ([OOPSLA'22](https://effekt-lang.org/evolution)) | Multi-shot, with constant-time one-shot capture and resume in the LLVM backend ([ICFP'25, Muhcu et al.](https://effekt-lang.org/evolution)) | LLVM, replacing a deprecated MLton pipeline that was dropped for its complexity ([history](https://effekt-lang.org/evolution)) | Research project |
| Unison 1.0 | "Abilities" track needed effects in types; handlers provide them ([AlternativeTo summary](https://alternativeto.net/news/2025/11/unison-1-0-released-with-stable-language-cloud-deployment-and-improved-tools)) | — | Codebase stored as ASTs; definitions identified by hash ([InfoWorld](https://www.infoworld.com/article/4100673/futuristic-unison-functional-language-debuts.html)) | 1.0 on 2025-11-25. Secondary coverage reports the team admitting runtime performance "isn't great" ([byteiota](https://byteiota.com/unison-1-0-content-addressed-code-hits-production/), unverified against a primary source) |
| OxCaml (Jane Street) | Type-system additions "to statically rule out data races"; layouts; native SIMD access; allocation control ([Jane Street blog, 2025-06-14](https://blog.janestreet.com/introducing-oxcaml/)) | (OCaml 5) | Flambda2 middle-end | Jane Street's production compiler, but its extensions carry "no promises of stability" ([oxcaml.org](https://oxcaml.org/)) |

Perceus, the reference-counting method behind Koka, is described as precise, "garbage free", sound in a linear resource calculus, and able to support *functional-but-in-place* (FBIP) reuse ([Reinking et al., PLDI'21](https://www.microsoft.com/en-us/research/publication/perceus-garbage-free-reference-counting-with-reuse-2/)). Lean 4 uses a closely related RC design with borrowed parameters and destructive updates ([Ullrich & de Moura, IFL'19](https://arxiv.org/abs/1908.05647)).

**Assessment [inference]:**
- Effect *typing* is mature enough to adopt. Koka has had row-typed effects across multiple major versions.
- *General* handlers with multi-shot continuations are not needed by Hearth. They also complicate the C ABI, stack layout and determinism.
- OCaml's experience suggests the cheap and valuable subset is one-shot continuations plus a runtime that keeps ordinary code fast.
- For a systems language without a GC, the cheapest subset is narrower still: *tail-resumptive* handlers, which compile to plain calls on a handler record passed as evidence, plus scoped `Fail`/`Cancel`. Async I/O can then be written as structured tasks rather than captured continuations.
- **Confidence: high** that typed rows plus restricted handlers fit Mithril. **Medium** on how far to go toward one-shot (non-tail) handlers.

### 2. Object capabilities and capability-safe languages

**Object-capability rules.** A reference can be obtained only by initial conditions, parenthood, endowment or introduction ("only connectivity begets connectivity"). Languages that allow forging or ambient access, such as Java reflection or `java.io.File` imports, break the model ([Wikipedia: Object-capability model](https://en.wikipedia.org/wiki/Object-capability_model)). The same page lists Original-E, Joe-E, Caja, Pony, Newspeak, Wyvern and others. (Mark Miller's E thesis could not be fetched in this session; unverified here.)

**Pony.** Pony has six reference capabilities (`iso`, `val`, `ref`, `box`, `trn`, `tag`). Data crosses actors only when it is immutable (`val`) or isolated (`iso`), so the compiler can prevent concurrent writes without locks ([Pony tutorial](https://tutorial.ponylang.io/reference-capabilities/reference-capabilities.html)). [inference] Six capabilities, plus viewpoint adaptation, are a known learning-curve cost. A smaller lattice suffices if references are second-class.

**Austral.**
- Capabilities are linear values. They cannot be copied or created from nothing, and the only built-in is `RootCapability`, passed to `main` ([Borretti, 2023-05-05](https://borretti.me/article/how-capabilities-work-austral)).
- Capability security is "simply a consequence of linear types" ([same](https://borretti.me/article/how-capabilities-work-austral)).
- The weak point is FFI. Modules that use it are only marked `pragma Unsafe_Module`. An `Unsafe` capability threaded from root is proposed but not implemented ([same](https://borretti.me/article/how-capabilities-work-austral)).
- Austral is "designed to be simple enough to be understood by a single person" ([austral-lang.org](https://austral-lang.org/)).
- Its borrowing is Rust-like, with explicit `Region` type parameters on references ([Austral spec](https://austral-lang.org/spec/spec.html)).

**WASI and the component model.**
- The component model's goals include "capability-safe, language-agnostic interfaces" and fine-grained sandboxing per component ([Goals.md](https://github.com/WebAssembly/component-model/blob/main/design/high-level/Goals.md)).
- WASI 0.3.0 was released on 2026-06-11. It moves async into the canonical ABI via `future<T>`/`stream<T>` ([wasi.dev](https://wasi.dev/releases/wasi-p3); [Bytecode Alliance](https://bytecodealliance.org/articles/WASI-0.3)).
- Wasmtime 46 ships it with component-model async on by default ([Bytecode Alliance](https://bytecodealliance.org/articles/WASI-0.3)).

**Assessment [inference]:**
- Capabilities are the right security and *explainability* primitive for an AI-first language. A Darwin-Gödel-Machine-style loop that edits code needs a hard guarantee that a candidate edit cannot gain I/O, network or `Unsafe` authority it was not granted.
- Austral shows the guarantee follows from linearity plus no global mutable state.
- Effekt shows effect handlers *are* capability passing.
- Mithril should therefore have one concept: **an effect in a function's row is a capability parameter that is passed implicitly.**
- **Confidence: high.**

### 3. Ownership, value semantics, regions and linear types

**Rust.**
- The ownership and borrowing type system was proven sound for a realistic subset, including unsafe libraries, in RustBelt (Iris/Coq) ([POPL'18](https://plv.mpi-sws.org/rustbelt/popl18/)).
- The aliasing model for unsafe code is still evolving. Tree Borrows (PLDI 2025) rejects 54% fewer test cases than Stacked Borrows across the 30,000 most-used crates, and is proven in Rocq to keep most Stacked Borrows optimisations ([Villani et al.](https://doi.org/10.1145/3735592)).
- The Rust Project adopted the Ferrocene Language Specification (FLS) in March 2025, and says this "does not change the status of the Reference" ([Rust blog](https://blog.rust-lang.org/2025/03/26/adopting-the-fls/)).
- [inference] A decade on, Rust's *unsafe* semantics are still research topics. Mithril should not try to out-specify Rust on aliasing. It should shrink the surface where aliasing exists.

**Hylo (mutable value semantics, MVS).**
- Parameters are passed `let` / `inout` / `sink` / `set`. Subscripts yield in-place projections, and `sink` methods consume values ([hylo-lang.org](https://hylo-lang.org/)).
- A mutable value is reachable through exactly one binding at a time ([Hylo docs](https://docs.hylo-lang.org/language-tour/bindings)).
- The compiler emits LLVM. It says it is "under active development; expect things to break", and most effort has moved to `hylo-new` ([GitHub](https://github.com/hylo-lang/hylo)).
- The ECOOP 2025 PLSS talk says the design "has solidified into a coherent system" ([ECOOP'25](https://2025.ecoop.org/details/plss-2025-papers/12/Designing-Hylo-a-programming-language-for-safe-systems-programming)).
- Maturity: **low** for implementation, **medium** for design.

**Swift.**
- `~Copyable` structs and enums have unique ownership and `deinit`. Parameters must be `borrowing`, `consuming` or `inout`. Shipped in Swift 5.9 ([SE-0390](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0390-noncopyable-structs-and-enums.md)).
- Swift 6 (2024-09-17) added generics over noncopyable types and an opt-in language mode that turns data races into compile errors ([swift.org](https://www.swift.org/blog/announcing-swift-6/)).
- This is evidence that linear and affine types are deployable in a mainstream language. **High.**

**Regions and arenas.**
- **MLKit** compiles Standard ML with region inference combined with reference-tracing GC, which can be disabled for real-time use. Release 4.7.17 came out on 2025-12-16, and ReML adds explicit regions and effects ([MLKit](https://elsman.com/mlkit/)). Region inference alone does not always reclaim all dead memory, which is why the GC was added ([Hallenberg thesis](https://elsman.com/mlkit/pdf/nhthesis.pdf)).
- **Cyclone** had region subtyping integrated with stack allocation and GC (PLDI 2002). Porting C needed changes to about 8% of the code, and only 6% of those changes were region annotations ([Grossman et al.](https://www.cs.umd.edu/~mwh/papers/GrossmanMJHWC02.html)).
- **Verona/Reggio** has regions plus "cowns" (concurrent owners wrapping an `iso` region) ([OOPSLA'23](https://arxiv.org/abs/2309.02983)), and Behaviour-Oriented Concurrency ([Cheeseman et al., OOPSLA'23](https://www.microsoft.com/en-us/research/publication/when-concurrency-matters-behaviour-oriented-concurrency/)). The repository says it is "not ready to be used outside of research" and is undergoing "a massive refactoring" ([GitHub](https://github.com/microsoft/verona)).
- **MPL / disentanglement.** A parallel functional language with a heap tree that mirrors the task tree is proven to need at most O(R*·P) memory, where R* is sequential live memory and P the processor count ([Arora, Westrick, Acar, POPL'21](https://popl21.sigplan.org/details/POPL-2021-research-papers/18/Provably-Space-Efficient-Parallel-Functional-Programming)).

**Assessment and recommended memory model [inference]:**
- Hearth's memory is almost entirely arena-shaped:
  - a fixed slot arena of 4096-aligned slabs;
  - KV cache buffers;
  - per-layer scratch;
  - refcounted slots that are never evicted while `refcount>0` (`hearth/engine/src/hx_store.h`).
- That is a region-plus-linear-lease pattern, not a general object graph. The proposed Mithril model has five parts:
  1. Values by default (MVS). Parameters are `let` (shared read), `inout` (exclusive), `sink` (consume).
  2. **Second-class references.** Borrows cannot be stored in structs or returned except via projections. This removes lifetime annotations from the language, at the price of some expressiveness. Hylo and Austral both show the trade is livable.
  3. **Linear types** for resources: file handles, slot leases, thread join handles, capabilities. They must be consumed exactly once.
  4. **Explicit arenas** as values with an `Alloc<A>` effect. Lexical `region` blocks cover temporaries.
  5. Raw pointers, address arithmetic and C structs only under an `Unsafe` capability.
- Reference counting (Perceus-style) is a library option for the control plane, not the default.
- **Confidence: medium-high.** The main risk is that second-class references make some Hearth data structures awkward, such as the queues between reader threads and compute. Those would sit behind small `Unsafe`-capability modules with verified interfaces.

### 4. Multi-stage programming, partial evaluation and supercompilation

**Terra** (DeVito et al., PLDI 2013) stages a statically typed, manually managed, C-interoperable language from Lua.
- The two languages share a lexical environment, but Terra code runs without Lua's runtime. It is JIT-compiled through LLVM or saved as a `.o` ([doi](https://www.doi.org/10.1145/2491956.2462166); [terralang.org](https://terralang.org/)).
- The paper reports a Terra BLAS auto-tuner within 20% of ATLAS, and a stencil DSL 2.3× faster than hand-written C ([doi](https://www.doi.org/10.1145/2491956.2462166)). These are the authors' figures for their hardware.

**MetaOCaml.**
- A well-typed generator produces only well-scoped, well-typed code ([Kiselyov](https://tagteam.harvard.edu/hub_feeds/1936/feed_items/2100420)).
- Version N114 integrates quotation translation with type checking, at no cost to ordinary OCaml ([MetaOCaml Theory and Implementation](https://arxiv.org/pdf/2309.08207)).
- Staging is term-level only and does not interact with modules ([PEPM'16](https://www.cs.tsukuba.ac.jp/~kam/papers/pepm2016b.pdf)).
- Generated code cannot be inspected during staging ([Scoped and Typed Staging by Evaluation](https://arxiv.org/pdf/2310.13413)).

**Zig comptime.**
- Functions and blocks can be evaluated at compile time. "A generic data structure is simply a function that returns a `type`", and there is "no preprocessor, and no macros" ([Zig overview](https://ziglang.org/learn/overview/)).
- [inference] This is the most LLM-friendly staging design: there is only one language to learn. Its weakness is that comptime code is checked lazily, only when instantiated, so generator bugs surface late.

**Scala LMS** separates stages "only through types", as a library rather than quasi-quotes. It was used for Delite, OptiML, Spiral-style numeric kernels and SQL engines ([CACM 2012](https://infoscience.epfl.ch/record/178274/files/lms-cacm2012.pdf); [Rompf 2016](https://www.cs.purdue.edu/homes/rompf/papers/rompf-draft2016b.pdf)).

**Julia `@generated` functions.**
- The generator sees only argument *types*, must be "completely pure", may run once or many times, and cannot call methods defined later because of world age ([Julia manual](https://docs.julialang.org/en/v1/manual/metaprogramming/)).
- A core developer calls them an escape hatch with compile-time and world-age costs ([Discourse](https://discourse.julialang.org/t/why-not-use-generated/29531.md)).

**Halide and ISPC.**
- Halide separates the algorithm (what is computed) from the schedule (order, locality, tiling, vectorisation, parallelism) and targets x86, ARM, RISC-V and GPUs ([halide-lang.org](https://halide-lang.org/)).
- ISPC compiles SPMD code to SSE, AVX2 and AVX-512 (and NEON and Intel GPUs), and shares pointers with C without copying ([ispc.github.io](https://ispc.github.io/)).
- These are the two proven ways to *guarantee* vector mapping: the programmer opts into a model where vectorisation follows from the semantics. [inference]

**Partial evaluation and Futamura projections.**
- Specialising an interpreter to a program gives an executable. Specialising the specializer to an interpreter gives a compiler. Self-application gives a compiler generator. Futamura described these in 1971 ([Wikipedia](https://en.wikipedia.org/wiki/Partial_evaluation)).
- Truffle writes languages as self-modifying AST interpreters and derives compiled code with Graal ([GraalVM](https://www.graalvm.org/latest/graalvm-as-a-platform/language-implementation-framework/)), via partial evaluation ([Marr 2015](https://stefan-marr.de/2015/10/tracing-vs-partial-evaluation-comparing-meta-compilation-approaches-for-self-optimizing-interpreters/)).
- A DLS 2021 paper says it knows of no production runtime that uses the generic *second* projection ([CompGen](https://conf.researchr.org/details/dls-2021/dls-2021-papers/5/CompGen-Generation-of-Fast-JIT-Compilers-in-a-Multi-language-VM)).
- PLDI 2025's "Partial Evaluation, Whole-Program Compilation" (Fallin & Bernstein) adds context and specialised-value intrinsics that let an existing interpreter be partially evaluated into compiled code ([doi](https://dl.acm.org/doi/10.1145/3729259); [summary](https://danglingpointers.substack.com/p/partial-evaluation-whole-program)).

**Supercompilation.**
- The most concrete modern result is Bolingbroke's GHC pass (2013): a geometric mean of 42% runtime and 34% allocation reduction on a benchmark suite ([UCAM-CL-TR-835](https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-835.html)).
- I found no 2024–2026 production adoption (unverified absence).
- **Maturity: low.** Termination and code-size control remain hard. [inference]

**Assessment [inference, high]:**
- Staging is the most important building block for Mithril after the memory model.
- Hearth today hand-writes one scalar, one AVX2 and one AVX-512 variant of each kernel. It selects among them at runtime and requires all three to be bit-identical (`hearth/engine/src/hx_quant.h`; INV-DET-3).
- In Mithril that should be **one generator**, parameterised by ISA, quant format and tile shape. Its output for each ISA is *checked* against the scalar canonical definition by testing and, for small kernels, by translation validation.
- The generator family is also the natural search space for an AI optimiser. The agent mutates schedules and generators, not raw assembly, and every variant inherits the correctness argument.
- Truffle-style partial evaluation matters mainly for Mithril's own tooling. One executable semantics (an interpreter) could yield the compiler's constant folder and comptime evaluator. It is not needed for Hearth.

### 5. Deterministic parallelism and structured concurrency

**Cilk / OpenCilk.**
- A deterministic Cilk program behaves like its serial projection under every parallel schedule ([OpenCilk glossary](https://opencilk.org/doc/reference/glossary)).
- For a given input, Cilksan finds a determinacy race if one exists under any schedule, or certifies that none exists ([OpenCilk](https://opencilk.org/doc/users-guide/getting-started)).

**Rayon** "guarantees data-race free executions" with work-stealing `join`/`par_iter`. Its front page makes no claim about deterministic results or reduction order ([docs.rs](https://docs.rs/rayon/latest/rayon/)). [inference] Data-race freedom is weaker than determinism: a parallel float `reduce` can still give scheduling-dependent bits. That is exactly what INV-DET-1/3 forbid.

**Structured concurrency.**
- Nathaniel Smith's 2018 "nursery" essay argues that spawned tasks must not outlive their scope ([vorpus.org](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/)). The idea is credited to Martin Sústrik in 2016 ([Gavin Howard](https://gavinhoward.com/2019/12/structured-concurrency-definition)).
- Java's `StructuredTaskScope` is still a preview in JDK 26 (JEP 525, sixth preview) ([OpenJDK](https://openjdk.org/jeps/525)). Mainstream adoption is slow even for a well-understood idea.
- Zig 0.16 (April 2026) separates `io.async` (may run out of order, infallible) from `io.concurrent` (must run concurrently, can fail with `ConcurrencyUnavailable`). Its evented backend is "work-in-progress, experimental" ([Zig 0.16 notes](https://ziglang.org/download/0.16.0/release-notes.html)). Zig 0.15 had removed the `async`/`await` keywords ([0.15.1 notes](https://ziglang.org/download/0.15.1/release-notes.html)).
- Verona's BoC offers "asynchronously creating atomic and ordered units of work" over several resources ([OOPSLA'23](https://www.microsoft.com/en-us/research/publication/when-concurrency-matters-behaviour-oriented-concurrency/)).

**Hearth practice.**
- The pool assigns work dynamically through an atomic counter, but each output element is written by exactly one thread, so results never depend on scheduling (`hearth/engine/src/hx_pool.h`).
- Reductions follow a fixed 16-lane canonical tree (`hearth/docs/NUMERICS.md`).
- The store runs long-lived reader threads with demand and prefetch queues under one mutex (`hearth/engine/src/hx_store.h`).

**Assessment [inference, high]:** Mithril's parallel subset should have three parts.
1. **`par for` over an index space**, whose body receives disjoint `inout` sub-slices of the outputs. The type system proves disjointness for affine index maps; other cases need `Unsafe`. Dynamic scheduling is allowed because results cannot depend on it.
2. **Reductions take an explicit order**: a named canonical tree such as `sum16`. Float `reduce` without an order is a type error.
3. **Structured `scope { spawn … }`** for I/O tasks, with cancellation through a scoped `Cancel` effect. Long-lived workers (reader threads, the pool) are scope-owned services created under `Spawn` and `IO` capabilities.

Atomics, racy reads and time-dependent decisions (spin limits, eviction heat) require a `Nondet` capability. The type system can then show that the logits path is `Nondet`-free while the cache policy is not. That is INV-DET-1, stated as a type rule.

### 6. Incremental compilation, content addressing, hermetic builds, hot swap

**Query-based compilers.**
- rustc is moving to demand-driven, memoised queries with a recorded dependency graph ([rustc-dev-guide](https://rustc-dev-guide.rust-lang.org/query.html)).
- Incremental compilation uses a red-green "try-mark-green" algorithm, so unchanged results are not even deserialised ([incremental](https://rustc-dev-guide.rust-lang.org/queries/incremental-compilation.html)).
- Salsa generalises this as "on-demand, incrementalized computation" over inputs and pure functions ([salsa](https://github.com/salsa-rs/salsa)). It shipped versions 0.19–0.24 during 2025 ([lib.rs](https://lib.rs/crates/salsa); [mirror](https://git.joshthomas.dev/mirrors/salsa/src/salsa-v0.24.0)).
- In March 2025 rust-analyzer adopted the new Salsa, making the crate the unit of incrementality and preparing for parallelism and persistent caches ([r/rust announcement mirror](https://redlib.hackliberty.org/r/rust/comments/1jbyunp/call_for_testing_rustanalyzer)).
- Zig's incremental compilation remained "still experimental" in 0.15 ([notes](https://ziglang.org/download/0.15.1/release-notes.html)). [inference] Retrofitting incrementality is hard; designing for it from day one is cheap.

**Content-addressed code (Unison).** Definitions are identified by a hash of their syntax tree with dependencies replaced by hashes. The project claims "perfect" incremental compilation with a shared cache ([InfoWorld](https://www.infoworld.com/article/4100673/futuristic-unison-functional-language-debuts.html)).

**Hermetic builds.**
- Bazel defines hermeticity as the same inputs plus configuration giving the same output, isolated from the host. It recommends sandboxing and remote execution to find leaks ([bazel.build](https://bazel.build/basics/hermeticity)).
- Nix content-addressed derivations were still experimental and opt-in in 2025 ([Zakaria 2025](https://fzakaria.com/2025/03/08/demystifying-nix-s-intensional-model); [NixOS wiki](https://wiki.nixos.org/wiki/Ca-derivations)).

**Hot code swapping (BEAM).**
- A module has at most a current and an old version, and only fully qualified calls switch to current code ([Erlang docs](https://www.erlang.org/doc/system/code_loading.html)).
- On a third load the old code is purged and "any processes lingering in it are terminated" ([same](https://www.erlang.org/doc/system/code_loading.html)).

**Assessment [inference, high]:**
- Mithril's compiler should be a salsa-style query database whose keys are content hashes of normalised definitions.
- Verification artifacts — test results, translation-validation certificates, benchmark measurements labelled measured/simulated as INV-HONEST requires — attach to hashes.
- An AI agent evaluating 1,000 kernel variants then recompiles and re-verifies only what changed. A rename invalidates nothing.
- Hot swap means versioned dispatch tables switched at a declared quiescent point, for example between tokens, following the BEAM rule. Code pages are written once (W^X) and never patched in place.

### 7. C interop

- **Zig.**
  - Historically, `@cImport` translated C headers, including inline functions, into Zig ([overview](https://ziglang.org/learn/overview/)).
  - Zig 0.16 **deprecates `@cImport`**. C translation moves to the build system with an official translate-c package ([0.16 notes](https://ziglang.org/download/0.16.0/release-notes.html)).
  - Forum threads report translate-c failures after the 0.16 upgrade ([Ziggit tag](https://ziggit.dev/tag/zig-0-16)).
  - [inference] Even Zig is moving C parsing out of the core compiler.
- **rust-bindgen** uses libclang to parse headers and emits `#[repr(C)]` structs and `extern "C"` declarations ([rust-bindgen](https://github.com/rust-lang/rust-bindgen)).
- **Nim** uses `importc`/`exportc` and can emit C, C++ or Objective-C that embeds into host projects ([Nim backends](https://nim-lang.org/docs/backends.html)).
- **Hearth** exposes a flat C ABI (`hearth_open`, `hearth_eval`, `hearth_matmul`, …) with `__declspec(dllexport)` or visibility attributes, consumed by a numpy/ctypes toolkit (`hearth/engine/include/hearth.h`).

**Assessment [inference, high]:**
- *Export* `extern "C"` with exact layout control (`repr(C)`, alignment, calling convention) is a day-one requirement.
- *Import* should be an offline tool (libclang- or Aro-based) that generates checked-in Mithril declarations, not an in-compiler C front end. That keeps the spec and compiler small.
- Every foreign call needs the `Foreign` (⊂ `Unsafe`) capability.

### 8. Backend options

| Option | Evidence | Fit for Mithril/Hearth [inference] |
|---|---|---|
| **Emit C** | Koka compiles to C without a runtime ([README](https://github.com/koka-lang/koka)). Lean 4's compiler "produces C code" ([de Moura & Ullrich](https://lean-lang.org/papers/lean4.pdf)). Nim emits C/C++/ObjC ([docs](https://nim-lang.org/docs/backends.html)). Some Zig targets "require using either Zig's C backend with GCC or an external LLVM/Clang fork" ([0.16](https://ziglang.org/download/0.16.0/release-notes.html)) | **Best first backend.** It matches Hearth's C11 toolchain (MSVC/GCC/Clang) and the INV-DEP spirit, and links into Hearth file by file. Must pin FP semantics: GCC defaults to `-ffp-contract=fast` unless in an ISO mode such as `-std=c11` ([GCC](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)); Clang defaults to `on` for C/C++ ([Clang](https://clang.llvm.org/docs/UsersManual.html)); Hearth already forces `-ffp-contract=off` and MSVC `/fp:precise` (`hearth/CMakeLists.txt`, `NUMERICS.md`). Inherits C UB unless generated code avoids it |
| **LLVM** | Used by Terra, ISPC, Halide and Hylo ([Terra](https://terralang.org/); [ISPC](https://ispc.github.io/); [Hylo](https://github.com/hylo-lang/hylo)). Hylo needs exactly LLVM 20 because "major LLVM versions aren't compatible" ([README](https://github.com/hylo-lang/hylo)) | Optional release backend. Heavy dependency and version churn are costly for an AI-maintained toolchain |
| **Cranelift** | About "an order of magnitude faster" code generation than LLVM, code about 14% slower; ISLE lowering DSL with formal-verification work ([cranelift.dev](https://cranelift.dev/)). rustc's Cranelift backend lists SIMD as not yet supported, with `std::arch` partial ([cg_clif](https://github.com/rust-lang/rustc_codegen_cranelift)) | Good for a fast debug or JIT tier of control-plane code. Not for AVX-512 kernels (unverified whether Cranelift emits AVX-512 at all) |
| **MLIR** | The `x86` dialect has AMX tile load/store/mul, AVX-512 `dot`/`mask.compress`/`cvt…bf16`, and AVX10 `dot.i8` ([MLIR x86](https://mlir.llvm.org/docs/Dialects/X86/)), plus a generic `vector` dialect ([MLIR](https://mlir.llvm.org/docs/Dialects/Vector/)) | Attractive for a kernel IR, but MLIR is C++ and LLVM-coupled. Borrow its *dialect ideas* (vector, x86) rather than the dependency |
| **QBE** | "70% of the performance of industrial optimizing compilers in 10% of the code"; amd64, arm64, riscv64 ([QBE](https://c9x.me/compile/)); IL has four base types (w, l, s, d) and no vector types ([IL](https://c9x.me/compile/doc/il.html)) | Unsuitable for SIMD kernels. Its size is a model for a small backend |
| **Copy-and-patch** | Code generation about two orders of magnitude faster than LLVM -O0, with output 14% faster than -O0 ([Xu & Kjolstad](https://arxiv.org/abs/2011.13127)). CPython's experimental JIT uses it, with LLVM needed only at build time ([PEP 744](https://peps.python.org/pep-0744/)) | Good basis for the "JIT runtime" in Mithril's repo description: stencils compiled ahead of time from the C backend, patched at runtime |
| **Custom native** | Zig's self-hosted x86_64 backend became the Debug default in 0.15 with about 5× faster compiles than LLVM, except on Windows/BSDs ([0.15.1](https://ziglang.org/download/0.15.1/release-notes.html)). Zig Tier 1 requires generating machine code "without relying on LLVM" ([0.16](https://ziglang.org/download/0.16.0/release-notes.html)) | Feasible for a narrow kernel subset (straight-line vector code, fixed loops), where superoptimisation (seed B3/B8) can act. A full custom backend is multi-year work, as Zig's history shows |

### 9. Compiler implementation language for an AI-maintained compiler

**Evidence:**
- Austral's compiler is written in OCaml ([github.com/austral/austral](https://github.com/austral/austral); this comes from a search summary of the repository and was not fetched directly).
- Lean 4 is "a reimplementation of the Lean theorem prover in Lean itself", and its compiler emits C ([de Moura & Ullrich](https://lean-lang.org/papers/lean4.pdf)).
- Hylo's compiler is written in Swift ([hylo-lang.org](https://hylo-lang.org/)). Effekt and Koka are written in Scala and Haskell [inference from the repositories; not separately fetched].
- Rust hosts rustc, rust-analyzer, salsa and Cranelift ([salsa](https://github.com/salsa-rs/salsa); [cranelift.dev](https://cranelift.dev/)).
- Zig's breaking releases are a maintenance tax: 0.16 is described as one of its most breaking releases ([youngju.dev](https://www.youngju.dev/blog/2026-07-16-zig-016-io-interface.en)).
- MultiPL-E found Codex matching or exceeding its Python performance on several other languages. It was built to study how language frequency and language features affect code-LLM performance ([Cassano et al. 2022](https://arxiv.org/abs/2208.08227)). Only the abstract was read, so I make no claim about its per-language results.

**Trade-offs [inference]:**
- **Rust.** Strong types catch an agent's mistakes at compile time. It has the largest relevant library ecosystem (salsa, Cranelift) and a large LLM training corpus. Compile times are slow and the borrow checker adds friction for graph-heavy IRs (usually handled with arenas and indices).
- **OCaml.** The classic compiler language: pattern matching, fast builds, small runtime. Its corpus is smaller and OCaml 5 effects are untyped. OxCaml is unstable.
- **Lean 4.** Proofs of the core calculus and a verified evaluator can live next to the implementation. Smaller corpus, slower elaboration at scale, and fewer systems libraries.
- **Zig/C.** Matches Hearth's world, but there are no memory-safety guarantees for code that agents rewrite constantly. Zig is still pre-1.0 and churning.

**Recommendation [inference, medium]:**
- Write `mithc` in Rust.
- Keep an executable reference semantics of the core in Lean 4, with type soundness proved over time. Differentially test `mithc` against that interpreter, the way Hearth tests its engine against the numpy reference (INV-NUM-1).
- Self-hosting is a later milestone, after the Hearth port.

### 10. How big can a spec be and still fit in context?

Words measured by this agent on 2026-10-11 with `curl | strip-tags | wc -w`. Counts are approximate and include navigation text.

| Document | ≈ words |
|---|---|
| Austral spec ([link](https://austral-lang.org/spec/spec.html)) | 28,300 (includes rationale prose) |
| Go language spec ([link](https://go.dev/ref/spec)) | 40,000 |
| Lua 5.4 reference manual ([link](https://www.lua.org/manual/5.4/manual.html)) | 45,000 (includes C API and stdlib) |
| Zig 0.15.1 language reference ([link](https://ziglang.org/documentation/0.15.1/)) | 63,300 (many code samples) |
| QBE IL reference ([link](https://c9x.me/compile/doc/il.html)) | 5,800 |

Wasm 3.0 (2025-09-17) is the first Wasm standard produced with the SpecTec toolchain. The announcement says this should make the specification more reliable. Wasm 3.0 also standardises a deterministic profile for non-deterministic operations such as NaN results ([webassembly.org](https://webassembly.org/news/2025-09-17-wasm-3.0/)).

[inference] Mithril should target a normative prose core of 25–30k words, Austral-sized, about 35–45k tokens at about 1.3–1.5 tokens per word. It should sit beside a machine-readable formal core (SpecTec-like or Lean) of comparable size. The standard library and the x86 intrinsic catalogue are separate, retrievable documents. A Wasm-style deterministic profile is a directly reusable precedent for Hearth's INV-DET-3.

---

## Recommended minimal core: "Mithril Core" (synthesis) [inference throughout]

The aim is the smallest calculus that can express all of Hearth: threads, direct I/O, SIMD kernels, the C ABI and bit-exact numerics, while staying spec-small.

**1. Types**
- Fixed-width integers and IEEE `f16/bf16/f32/f64`.
- `vec<T,N>` and `mask<N>` as first-class values.
- Structs, enums, fixed arrays and slices.
- `linear` (must-consume) and `affine` qualifiers.
- `Aligned<N, T>`, for Hearth's 4096-aligned slabs and the seed's `line64` (B4).
- Packed sub-byte formats (Q4 4.25 bpw, INT2, FP4) are **library types defined by staged generators**, not primitives (see C6).

**2. Strict float semantics**
- No contraction, no reassociation, no fast-math anywhere in the language.
- `fma(a,b,c)` is an explicit operation, and reductions name their tree.
- This makes Hearth's canonical order the language default rather than a build-flag convention.

**3. Mutable value semantics**
- Parameter modes `let | inout | sink`. References are second-class and projections replace returned references.
- There are no lifetime parameters. The no-alias property of seed B5 holds for all safe code *by construction*, not through an affine-stride DSL.

**4. Effects = capabilities**
- Function types carry an effect row, e.g. `fn read(f: let File, buf: inout Aligned<4096,[u8]>) -> usize / {IO}`.
- Effects are implicit capability parameters (Effekt-style) originating from `main(root: Root)` (Austral-style).
- Built-ins: `IO`, `Spawn`, `Alloc<A>`, `Nondet`, `Time`, `Fail<E>`, `Cancel`, `Unsafe`, `Foreign ⊂ Unsafe`, `Compile` (stage 0 only).
- User handlers are restricted to tail-resumptive or one-shot forms, so evidence passing compiles them to direct calls.

**5. Regions and linearity**
- `region { … }` blocks and first-class `Arena` values.
- Linear `Lease<T>` for cache slots (Hearth's refcount>0 pin rule), linear `File`, `Thread`, and capability values.

**6. Parallelism**
- `par for i in 0..n split(out) { … }` with disjoint output views.
- Ordered reductions only, plus `scope { spawn … }`.
- Anything racy needs `Nondet`. "The logits path is `Nondet`-free" becomes a checkable property.

**7. Staging**
- Two stages. Stage 0 is ordinary Mithril run by the compiler's interpreter under `Compile` (Zig comptime).
- Typed quotes `Code<T>` with hygienic splices give the MetaOCaml well-typed-output guarantee for kernels. Schedules are stage-0 data (Halide).
- One kernel generator emits scalar, AVX2 and AVX-512 versions. The compiler checks each against the scalar canonical definition: exhaustively or by random testing for all kernels, and with SMT/translation validation for small straight-line kernels (seed B8).

**8. `Unsafe`-capability island**
- Raw pointers, inline asm, `extern "C"` import and export, volatile and atomics.
- Because `Unsafe` is a capability flowing from `root`, the audit surface is the capability graph. This fixes Austral's acknowledged FFI gap.

**9. Program identity and compilation**
- Definitions are content-addressed. The compiler is a query DB keyed by hash, and verification artifacts are cached per hash.
- Hot swap goes through versioned dispatch tables at quiescent points, BEAM-style.

**10. Backends**
- C11 first (strict FP pragmas and flags, no UB-reliant output).
- Then a direct x86-64 emitter for the staged-kernel subset, with copy-and-patch for JIT.
- LLVM optional later.

Deliberately excluded: GC, exceptions-as-unwinding, inheritance, implicit conversions, macros, multi-shot continuations, general dependent types. Each would add spec mass without serving Hearth.

---

## Implications for Mithril

1. Make "effects = capabilities" and "values plus second-class references plus linear resources" the two pillars of the spec. Both have working precedents (Effekt/Austral and Hylo/Swift), and together they remove whole sections a Rust-style spec would need: lifetimes, variance, ambient authority. [inference, high]
2. Treat staging as the core optimisation interface. The seed's ambitions — superoptimisation (B3, B8, B9), vector-width polymorphism (B6) and bit-width types (C6) — become *generators and schedules that an agent searches over*. Each candidate stays inside a typed, verifiable envelope. [inference, high]
3. Build the compiler as a hash-keyed query DB from the first commit. An AI-first language lives or dies on how cheaply an agent can try, verify and roll back a change. [inference, high]
4. Ship the C backend first and test it with Hearth's own golden tests. Defer custom codegen until a kernel subset is stable and measured (INV-HONEST discipline). [inference, high]
5. Keep the normative core at or below about 30k words, with an executable Lean semantics and a SpecTec-style machine-readable grammar and typing rules. Publish both as `llms-full.txt` (seed H4). [inference, medium]
6. Keep effect-handler generality, region inference and supercompilation out of v1. Each is research-grade and adds spec and compiler complexity without a Hearth need. [inference, medium-high]

## Implications for Hearth

1. **Port order follows purity.**
   - First, the quant kernels: pure, already specified normatively in `NUMERICS.md`, with three ISA variants that should collapse into one Mithril generator.
   - Second, elementwise ops and the forward pass.
   - Third, the pool (`par for` plus disjoint outputs).
   - Last, the store: reader threads, queues, mutex, direct I/O, the most `Unsafe`/`Nondet`-heavy code.
   - Each step links Mithril-emitted C11 into the existing engine through the C ABI and must pass the unchanged golden tests (INV-VERIFY). [inference, high]
2. **INV-DET-1/2/3 become type-level facts.** No `Nondet` on the logits path; ordered reductions only; strict float semantics as the default. The CMake flag `-ffp-contract=off` stops being the only line of defence. [inference, high]
3. **INV-SAFE and INV-FMT improve.** The container parser (`modelfile.c`) is the canonical place where malformed input must never crash. In Mithril, safe slices with checked indexing plus a `Fail` effect give this by construction. Only mmap and direct-I/O buffers need `Unsafe`. [inference, medium-high]
4. **The store's design maps onto Mithril.** Slot arena → `Arena` plus linear `Lease`. Prefetch and demand queues → a scoped service under `{IO, Spawn, Nondet}`. 4096-aligned direct I/O → `Aligned<4096,[u8]>` buffers. Mirrors and eviction policy are `Nondet`, but provably cannot affect logits. That is INV-DET-1 again. [inference, medium]
5. **INV-DEP is preserved if Mithril emits C11 plus OS APIs.** The generated code has no runtime library dependency, as with Koka's and Lean's C output. [inference, high]

## Where the seed discussion is right or wrong

- **B1 (C's abstract machine hides aliasing and hardware): partly right.** Aliasing is the strongest point. Value semantics plus second-class references give no-alias facts for free (Hylo). "Hides microarchitecture" is a backend issue, not a semantics one. [inference]
- **B2 (do not target LLVM; target a µop-port SSA): partly right, mostly premature.** LLVM is heavy and version-coupled ([Hylo README](https://github.com/hylo-lang/hylo)). But MLIR already exposes AVX-512, AVX10 and AMX ops ([MLIR x86](https://mlir.llvm.org/docs/Dialects/X86/)), and a C backend serves Hearth on day one. A port-aware machine IR is a research add-on for the kernel subset only. [inference, medium-high]
- **B4 (`line64` alignment type, streaming stores): right in spirit.** Alignment as a type (`Aligned<N,T>`) is cheap. Non-temporal stores should be a scheduling or library choice, not a core semantic. [inference]
- **B5 (no pointers, affine-stride DAGs): partly wrong.** Safe-code no-alias is achievable via MVS, but Hearth's queues, slot tables and file handles are not affine-stride arrays. An `Unsafe` island is unavoidable; Austral needs one too ([Borretti](https://borretti.me/article/how-capabilities-work-austral)). [inference, high]
- **B6 ("vectorisation mathematically guaranteed"): wrong as stated.** Guarantees come from opting into SPMD or schedule models (ISPC, Halide). Under INV-DET-3 the reduction order must also be fixed by the program. Arbitrary scalar loops cannot be guaranteed to vectorise. [inference, high]
- **B8 (affine IR → search → SMT check → emit): plausible for a kernel subset.** Cranelift's ISLE and formal-verification work show the approach is real for lowering rules ([cranelift.dev](https://cranelift.dev/)). Full-program SMT equivalence is not. [inference, medium]
- **C6 (sub-byte ints as primitives lowering to VNNI): right goal, wrong mechanism.** Hearth already calls `_mm512_dpbusd_epi32` (VNNI) from hand-written C (`hearth/engine/src/quant_avx512.c`). The gain is not reaching the instruction; it is *generating* every format × ISA variant from one staged definition. Formats belong in libraries. [inference, high]
- **C8 (unified host/device in one binary): right, and staging is the proven mechanism** (Terra: generator and generated code share scope, but the generated code runs standalone ([PLDI'13](https://www.doi.org/10.1145/2491956.2462166))). [inference, high]
- **H4 (`llms.txt` with EBNF and snippets): right**, and it depends on keeping the core spec small (§10). [inference]
- **H7 ("nothing combines all of this"): partly right.** Terra (staging + low level), Halide (schedules), ISPC (SPMD) and Koka/Effekt (effects) each cover a piece. The novel combination is effects-as-capabilities + MVS + typed staging + determinism-by-type. [inference, medium]
- **I4 (SMT check "guarantees bounded loss divergence" before hot-swap): unverified and out of language scope.** No source was given. A language can guarantee that a swap is type-safe and capability-confined, not that it preserves model quality. [inference]
- **I5 (`hot_patch` = atomic CMPXCHG8B/16B swap "in a single CPU cycle"): wrong framing.** No latency source was given, and I did not verify instruction latencies here. Hot-swap correctness comes from the quiescence protocol (Erlang's current/old rule ([docs](https://www.erlang.org/doc/system/code_loading.html))), not instruction speed. [inference, high]
- **I7 (self-modifying code via CLFLUSH/INVD): wrong level and dangerous.** Unverified in this session: INVD is a privileged instruction that discards cache contents, unusable from user mode. Use W^X stencil pages (copy-and-patch, [PEP 744](https://peps.python.org/pep-0744/)) and versioned dispatch tables instead. [inference, medium-high]
- **G1/G2 (study Souper/STOKE/Alive2, polyhedral, Lean): compatible.** This dossier recommends Lean for the reference semantics. Alive2-style translation validation fits the staged-kernel check. [inference]

## Open questions

1. Can second-class references express Hearth's reader-thread queues and the store's metadata without large `Unsafe` islands, or does Mithril need Verona-style regions or cowns for shared mutable state? This needs a prototype port of `store.c`.
2. How should effect rows be inferred so that they stay invisible in leaf code but explicit at module boundaries? Effekt's approach is not yet characterised for spec size.
3. Should `Code<T>` quotes allow inspecting generated code (Möbius-style, [arXiv](https://arxiv.org/pdf/2310.13413)), which an AI optimiser wants, or stay purely generative like MetaOCaml, which is simpler and safer?
4. How much of `libm` (`expf`, `sinf`, `cosf`) should Mithril own? `NUMERICS.md` relies on the platform libm being called the same way everywhere. A Mithril-native correctly rounded libm would make bit-identity portable across OSes. That is a scope decision.
5. Is Cranelift's x86-64 backend usable for AVX-512 at all? Unverified; the search budget ran out. If not, the "fast tier" is copy-and-patch from C-compiled stencils.
6. Lean 4 versus Rust (or OCaml) for `mithc` needs a small bake-off: implement the type checker for the core in both and measure agent edit success rates and iteration time. (MultiPL-E-style evidence suggests corpus size matters, but there is no direct study of compiler-maintenance tasks.)
7. What is the exact form of the Wasm 3.0 deterministic profile, and is it reusable as a citation-grade precedent for Mithril's strict-float default? Not read in detail.

## Sources

- https://effekt-lang.org/evolution
- https://github.com/koka-lang/koka
- https://www.microsoft.com/en-us/research/publication/perceus-garbage-free-reference-counting-with-reuse-2/
- https://arxiv.org/abs/1908.05647
- https://ocaml.org/manual/5.4/effects.html
- https://arxiv.org/abs/2104.00250
- https://ocaml.org/changelog/2025-01-08-ocaml-530
- https://ocaml.org/releases/5.4.0
- https://blog.janestreet.com/introducing-oxcaml/
- https://oxcaml.org/
- https://www.infoworld.com/article/4100673/futuristic-unison-functional-language-debuts.html
- https://alternativeto.net/news/2025/11/unison-1-0-released-with-stable-language-cloud-deployment-and-improved-tools
- https://byteiota.com/unison-1-0-content-addressed-code-hits-production/
- https://en.wikipedia.org/wiki/Object-capability_model
- https://tutorial.ponylang.io/reference-capabilities/reference-capabilities.html
- https://borretti.me/article/how-capabilities-work-austral
- https://borretti.me/article/introducing-austral (found by search; the fetch failed)
- https://github.com/austral/austral (from a search summary; not fetched)
- https://austral-lang.org/
- https://austral-lang.org/spec/spec.html
- https://github.com/WebAssembly/component-model/blob/main/design/high-level/Goals.md
- https://github.com/WebAssembly/WASI
- https://wasi.dev/releases/wasi-p3
- https://bytecodealliance.org/articles/WASI-0.3
- https://plv.mpi-sws.org/rustbelt/popl18/
- https://doi.org/10.1145/3735592 (Tree Borrows, PLDI 2025; PDF https://iris-project.org/pdfs/2025-pldi-treeborrows.pdf)
- https://blog.rust-lang.org/2025/03/26/adopting-the-fls/
- https://hylo-lang.org/
- https://docs.hylo-lang.org/language-tour/bindings
- https://github.com/hylo-lang/hylo
- https://2025.ecoop.org/details/plss-2025-papers/12/Designing-Hylo-a-programming-language-for-safe-systems-programming
- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0390-noncopyable-structs-and-enums.md
- https://www.swift.org/blog/announcing-swift-6/
- https://elsman.com/mlkit/
- https://elsman.com/mlkit/pdf/nhthesis.pdf
- https://www.cs.umd.edu/~mwh/papers/GrossmanMJHWC02.html
- https://arxiv.org/abs/2309.02983
- https://www.microsoft.com/en-us/research/publication/when-concurrency-matters-behaviour-oriented-concurrency/
- https://github.com/microsoft/verona
- https://popl21.sigplan.org/details/POPL-2021-research-papers/18/Provably-Space-Efficient-Parallel-Functional-Programming
- https://www.doi.org/10.1145/2491956.2462166
- https://terralang.org/
- https://tagteam.harvard.edu/hub_feeds/1936/feed_items/2100420
- https://arxiv.org/pdf/2309.08207
- https://www.cs.tsukuba.ac.jp/~kam/papers/pepm2016b.pdf
- https://arxiv.org/pdf/2310.13413
- https://ziglang.org/learn/overview/
- https://ziglang.org/download/0.15.1/release-notes.html
- https://ziglang.org/download/0.16.0/release-notes.html
- https://ziggit.dev/tag/zig-0-16
- https://www.youngju.dev/blog/2026-07-16-zig-016-io-interface.en
- https://infoscience.epfl.ch/record/178274/files/lms-cacm2012.pdf
- https://www.cs.purdue.edu/homes/rompf/papers/rompf-draft2016b.pdf
- https://docs.julialang.org/en/v1/manual/metaprogramming/
- https://discourse.julialang.org/t/why-not-use-generated/29531.md
- https://halide-lang.org/
- https://ispc.github.io/
- https://en.wikipedia.org/wiki/Partial_evaluation
- https://www.graalvm.org/latest/graalvm-as-a-platform/language-implementation-framework/
- https://stefan-marr.de/2015/10/tracing-vs-partial-evaluation-comparing-meta-compilation-approaches-for-self-optimizing-interpreters/
- https://conf.researchr.org/details/dls-2021/dls-2021-papers/5/CompGen-Generation-of-Fast-JIT-Compilers-in-a-Multi-language-VM
- https://dl.acm.org/doi/10.1145/3729259
- https://danglingpointers.substack.com/p/partial-evaluation-whole-program
- https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-835.html
- https://opencilk.org/doc/reference/glossary
- https://opencilk.org/doc/users-guide/getting-started
- https://docs.rs/rayon/latest/rayon/
- https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/
- https://gavinhoward.com/2019/12/structured-concurrency-definition
- https://openjdk.org/jeps/525
- https://rustc-dev-guide.rust-lang.org/query.html
- https://rustc-dev-guide.rust-lang.org/queries/incremental-compilation.html
- https://github.com/salsa-rs/salsa
- https://lib.rs/crates/salsa
- https://git.joshthomas.dev/mirrors/salsa/src/salsa-v0.24.0
- https://redlib.hackliberty.org/r/rust/comments/1jbyunp/call_for_testing_rustanalyzer
- https://bazel.build/basics/hermeticity
- https://fzakaria.com/2025/03/08/demystifying-nix-s-intensional-model
- https://wiki.nixos.org/wiki/Ca-derivations
- https://www.erlang.org/doc/system/code_loading.html
- https://github.com/rust-lang/rust-bindgen
- https://nim-lang.org/docs/backends.html
- https://lean-lang.org/papers/lean4.pdf
- https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html
- https://clang.llvm.org/docs/UsersManual.html
- https://cranelift.dev/
- https://github.com/rust-lang/rustc_codegen_cranelift
- https://mlir.llvm.org/docs/Dialects/X86/
- https://mlir.llvm.org/docs/Dialects/Vector/
- https://c9x.me/compile/
- https://c9x.me/compile/doc/il.html
- https://arxiv.org/abs/2011.13127
- https://peps.python.org/pep-0744/
- https://webassembly.org/news/2025-09-17-wasm-3.0/
- https://go.dev/ref/spec
- https://www.lua.org/manual/5.4/manual.html
- https://ziglang.org/documentation/0.15.1/
- https://arxiv.org/abs/2208.08227
- https://github.com/pierce-lonergan/hearth (local files cited: engine/src/hx_pool.h, engine/src/hx_store.h, engine/src/hx_quant.h, engine/src/quant_avx512.c, engine/include/hearth.h, docs/NUMERICS.md, governance/INVARIANTS.md, CMakeLists.txt)
