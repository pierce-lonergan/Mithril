# G05 — Can a Hylo-style mutable-value-semantics memory model express Hearth's concurrent expert store without large Unsafe islands?

Research dossier, 2026-10-11. Scope: R09 left open whether the memory model it proposed can express Hearth's `store.c`. That model is mutable value semantics (MVS), second-class references, linear resources and arenas, with raw pointers only under `Unsafe`. This dossier answers from three angles: (a) a line-level reading of `hearth/engine/src/store.c` and `hx_store.h`, (b) 2024–2026 evidence from ownership-, region- and capability-based languages, and (c) empirical data on how much `unsafe` Rust I/O, allocator and concurrency crates need.

**Method note.** This session's web-search budget was used up before this agent's first query. All external evidence comes from direct fetches of primary sources: Swift Evolution proposals, project repositories and docs, paper landing pages and crate sources. I could not run open-ended searches for experience reports, so some threads below are marked thinner than I would like. Every external claim has a link; my own reasoning is marked **[inference]**.

---

## Summary

- **Yes, with a small audited standard-library kernel and no user-level `Unsafe` in the store logic** [inference, medium-high]. `store.c` is a classic *monitor*. It has one mutex over metadata that is entirely integer-indexed: `slot_of[]`, a free stack, a demand ring and a prefetch FIFO, all of which are plain arrays. The only sharing outside the lock is the slab bytes, governed by a three-state ownership protocol (LOADING owned by one reader, READY shared read-only while `refs>0`, evictable only at `refs==0`). That protocol maps onto three standard-library primitives: a value-holding `Mutex<State>`, a linear owned `SlabBuf`, and a refcounted immutable `Frozen<SlabBuf>` that can be reclaimed when unique. Each has a deployed precedent: Swift's `Mutex<State: ~Copyable>`, Rust's `Arc::into_inner`, and the `bytes` crate's `freeze`/`try_into_mut`.
- **Hearth's I/O never lends a buffer to the kernel across a language-visible suspension point.** On Windows the handle is overlapped, but each call waits for its own request (`platform_win.c`). The buffer is therefore an ordinary `inout` borrow for the duration of a blocking call. The io_uring ownership problem, which forced tokio-uring into owned-buffer APIs ([DESIGN.md](https://github.com/tokio-rs/tokio-uring/blob/master/DESIGN.md); [without.boats](https://without.boats/blog/io-uring/)), does not arise for today's store. It would arise if Mithril adopted completion-based async I/O, and `sink` parameters model it directly [inference, high].
- **Regions or cowns are not needed in v1.** In pure MVS every value is already a "disconnected region" in Swift's sense. Swift needed SE-0414 region analysis only because classes create shared object graphs ([SE-0414](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0414-region-based-isolation.md)). What MVS still needs is a small **kind** distinguishing transferable values from the few stdlib reference-like types (`Frozen`, `Mutex`, atomics, raw pointers). That is a Sendable/Shareable marker, not a region calculus [inference, medium-high].
- **Verona/BoC is still research.** The repo says it is "not ready to be used outside of research" and is mid-"massive refactoring" ([GitHub](https://github.com/microsoft/verona)). The Python line of work had nothing ready to try for region ownership as of its May 2025 update ([Pyrona](https://microsoft.github.io/verona/pyrona.html)). BoC's published evaluation is Savina, with performance "comparable, if not better" than actors ([MSR](https://www.microsoft.com/en-us/research/publication/when-concurrency-matters-behaviour-oriented-concurrency/)). That is not systems I/O evidence.
- **Hylo has no concurrency model to borrow yet.** Its stdlib offers only `spawn_(_ f: sink [E]() -> Int)` and futures. These are built over a C runtime (`concore2full`) through FFI with type punning. There is no mutex, no atomics and no Sendable-like rule ([Spawn.hylo](https://raw.githubusercontent.com/hylo-lang/hylo/main/StandardLibrary/Sources/Concurrency/Spawn.hylo); [Future.hylo](https://raw.githubusercontent.com/hylo-lang/hylo/main/StandardLibrary/Sources/Concurrency/Future.hylo)), and the spec defines no concurrency model ([spec](https://github.com/hylo-lang/specification/blob/main/spec.md)). Mithril must design this layer itself (high).
- **The strongest 2025 design precedent is OxCaml's capsules** (POPL 2025 Distinguished Paper). A region of mutable state is accessed through a unique ghost key, and `Capsule.Mutex` acts as a dynamically unique key, so lock-protected shared state is checked statically ([POPL'25](https://popl25.sigplan.org/details/POPL-2025-popl-research-papers/23/Data-Race-Freedom-la-Mode); [OxCaml capsules](https://oxcaml.org/documentation/parallelism/capsules/)). [inference] Swift's `Mutex<State>` with an `inout` closure is the MVS-shaped special case. Mithril needs only that special case for Hearth.
- **Empirically, Rust unsafe kernels for these patterns are small and concentrated:**
  - `slab`: ~1,500 lines, 9 lines mentioning `unsafe`, 3 of them internal.
  - `generational-arena` forbids unsafe; `thunderdome` denies it.
  - glommio's DMA buffer: ~200 lines, 6 `unsafe` lines.
  - glommio's `dma_file.rs`: ~1,150 lines, 2 `unsafe` lines.
  - std's linked-list channel: ~550 lines, 17 `unsafe` lines.
  - Asterinas keeps its memory-safety TCB at ~14.0% of an OS ([USENIX ATC'25](https://www.usenix.org/conference/atc25/presentation/peng-yuke)).

  The exception is epoch reclamation: crossbeam-epoch leaks `unsafe` to clients (`Shared::deref`, `Guard::defer_destroy`) ([docs](https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/struct.Shared.html)). Mithril v1 should not offer it (medium-high).
- **The store's real risk is liveness, not memory safety.** In the PLDI 2020 study of real Rust bugs, *all* memory-safety bugs involved `unsafe`, but *all* blocking (deadlock) bugs were in safe code ([Qin et al.](https://songlh.github.io/paper/rust-study.pdf)). `store.c` already carries deadlock-avoidance machinery (`break_holds`, forward-progress slot minimum). [inference] Mithril's verification budget for the store should go to protocol model-checking, through a loom-style scheduler swapped in under the stdlib `Mutex`/`Condvar`, not to a richer type system.
- **The `Nondet` capability needs an encapsulation boundary.** Acquiring an expert reads shared mutable state, yet returns bytes that are a pure function of (file, layer, expert). A naive rule ("touching shared state ⇒ `Nondet`") would taint the logits path and defeat R09's "INV-DET-1 as a type rule". Mithril needs an audited "observationally deterministic" boundary, the `Nondet` analogue of Rust's interior `unsafe` or Swift's `@safe`, discharged by Hearth's existing scheduling-independence golden test [inference, medium-high].
- **Decision.** v1 core = MVS + second-class references + linear types + a transfer kind (`Send`-like) + a share kind (`Sync`-like). Plus an audited stdlib/Unsafe layer, estimated at a few hundred lines per OS [inference]:
  - `Mutex<T>` + `Condvar`;
  - `SlabBuf` / aligned arena chunks;
  - `Frozen<T>`;
  - `File.read_at`;
  - scoped threads and services;
  - optionally a bounded MPSC queue.

  Defer regions, cowns, BoC and concurrency-specific reference capabilities (Pony-style) to post-v1 research.

---

## Findings

### 1. Ground truth: what `store.c` actually requires

Read from `hearth/engine/src/store.c` (1,030 lines), `hx_store.h` (93) and `platform_win.c` / `platform_posix.c`. These are local observations, not web sources.

| State | Who writes | Who reads | Protection today | MVS + linear encoding [inference] |
|---|---|---|---|---|
| Slot metadata (`slots[]`: key, state, refs, pinned, hold/prot ticks, LRU seq), `slot_of[L·E]`, `free_stack`, demand ring `dq`, prefetch FIFO `pfq`, open-time `pre` list, `kq`, `miss_pending`, `failed`, `fresh[]`/`wgen`, heat/count arrays, stats, `stop` | compute thread(s) (`try_acquire`, `acquire`, `release`, `prefetch`, `tick`, `wait_any`) and readers (`next_job`, `finish`) | same | one mutex `mu` + two condvars | `Mutex<StoreState>`, where `StoreState` is a plain value: arrays of ints, floats and enums. No pointers between nodes. |
| Slab bytes of slot `si` | the single reader that `assign`ed `si` (state LOADING), outside the lock | compute thread while `refs>0` (READY), outside the lock | a protocol encoded in the metadata, *not* the lock | linear `SlabBuf` moved out of the state to the reader, then `freeze`d into a shared `Frozen<SlabBuf>`, then reclaimed when unique |
| `mf->experts[]` (offsets, sizes) | none after open | everyone | immutable | `let`-shared immutable value |
| `files[]` (main file + mirrors) | none after open | many readers concurrently (positional reads) | OS thread safety of positional I/O | shareable `File` with `read_at(inout buf, offset)` |
| Reader threads | `open` / `close` | — | joined in `close` | scoped service under `Spawn` |
| `count_f` exposed by `hx_store_heat()` | compute thread under the lock | caller, *without* the lock | none | rejected by second-class references (a borrow cannot escape `with_lock`); return a copy |

Observations [inference unless stated]:

1. **The metadata is already handle-based.** Every cross-reference in `store.c` is an integer: slot index, key = `layer·E + e`, ring positions. This is the "generational index / handles, not pointers" style that MVS forces. It needs no `Unsafe` and no stored references. Bulk invalidation is also done with **generation stamps**, not pointer surgery: a slot is held while `hold_tick == now+1`, protected while `prot_tick == now+1`, and fresh while `fresh[k] == wgen+1`. So `hx_store_tick` and `wait_any` expire whole sets in O(1) by bumping a counter. That is a pure value-level pattern.
2. **Sharing outside the lock is confined to slab bytes, and their protocol is a typestate.** The header comment states the protection lattice: pinned > `refs>0` > LOADING > held > protected. Eviction requires READY and `refs==0`, not pinned and not held (`evictable()`). The reader writes the slab only between `assign` (under the lock) and `finish` (under the lock). That is ownership transfer out of the monitor and back.
3. **I/O is blocking from the language's point of view.** On Windows, handles are opened `FILE_FLAG_OVERLAPPED` because synchronous handles serialise requests. The file's comment records a measurement of ~0.6 GB/s at 16 threads for synchronous handles versus ~5.7 GB/s overlapped, for 64 KiB unbuffered reads. Yet `hx__io` waits on `GetOverlappedResult(..., TRUE)` for its own request. On POSIX it is `pread` with `O_DIRECT` (or `F_NOCACHE` on macOS). The buffer is therefore borrowed only for the duration of one call.
4. **An unchecked "single compute thread" contract.** `hx_store.h` says the store is driven by one compute thread plus readers. The tests do exercise several caller threads under the mutex. But `hx_store_heat()` returns a raw pointer into lock-protected `count_f`, which `count_use` writes under the lock. With concurrent callers that is a C11 data race on diagnostics data. It is a small, concrete example of what second-class references reject by construction.
5. **Safety is tested dynamically, not proven.** `test_store.c` hashes every slab at acquire and again just before release, "so an eviction of an in-use slot or a torn read is caught". It runs 1–16 readers with one or several callers, plus a 60 s deadlock watchdog. Scheduling-order properties are made deterministic through a read-hook test seam. CI runs AddressSanitizer/UBSan (`CMakeLists.txt`). No ThreadSanitizer job exists.
6. **The determinism argument has a sampled step.** INV-DET-1 claims bit-identical logits regardless of mirrors. `check_mirror` compares size, preamble, header sections, and the first page of up to 16 slabs, not the full content. A mirror that differs elsewhere would silently change logits.

### 2. Swift 6: the closest deployed MVS-plus-concurrency system

- **Region-based isolation (SE-0414, Swift 6.0)** ([proposal](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0414-region-based-isolation.md)).
  - It lets non-`Sendable` values cross isolation boundaries when flow-sensitive analysis proves the whole region transfers and is not used afterwards.
  - Its stated motivation is that strict `Sendable` checking rejected race-free code and pushed developers to `@unchecked Sendable`.
  - It builds on PLDI 2022's *A Flexible Type System for Fearless Concurrency*.
  - Limitations:
    - regions are field-insensitive;
    - only `let` `Sendable` fields of a transferred class stay readable;
    - default transfers are "weak": the caller may still hold references, which affects `deinit` timing.
- **`sending` (SE-0430, Swift 6.0)** ([proposal](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0430-transferring-parameters-and-results.md)).
  - A `sending` parameter or result must be disconnected at the function boundary.
  - `sending` is weaker than `Sendable`: it requires that the whole region moves, not that the type be thread-safe.
  - A `sending` parameter is consuming by default. Writing `consuming sending` restores no-implicit-copy semantics.
- **`Mutex` (SE-0433, Swift 6.0)** ([proposal](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0433-mutex.md)).
  - Declared `struct Mutex<State: ~Copyable>: ~Copyable`, so the protected state may itself be noncopyable.
  - `withLock` hands the closure the state as an `inout` parameter with the transfer modifier. The proposal text uses `transferring`, SE-0430's pre-rename spelling.
  - The initializer consumes and transfers the initial state.
  - `Mutex` is unconditionally `Sendable` because the annotations ensure non-Sendable contents cannot enter with outside aliases or leak out unguarded.
  - [inference] This is exactly the shape `store.c` needs: protected state as a value, an exclusive projection scoped to the critical section, and values (here a slab buffer) moved in and out.
- **Non-escapable types and `Span` (SE-0446, SE-0447, Swift 6.2)** ([SE-0446](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0446-non-escapable.md); [SE-0447](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0447-span-access-shared-contiguous-storage.md)).
  - `~Escapable` values cannot be stored in globals, escapable types or class properties, nor returned. Lifetime-dependence annotations were deferred to a later proposal.
  - `Span` is a non-owning, bounds-checked, non-escapable view meant to replace `UnsafeBufferPointer` for local processing.
  - [inference] This is a mainstream language adding second-class buffer views, which is R09's design for Mithril's slab views.
- **Strict memory safety (SE-0458, Swift 6.2)** ([proposal](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0458-strict-memory-safety.md)).
  - Opt-in and warnings-based. It flags `Unsafe*Pointer`, `unowned(unsafe)`, and `nonisolated(unsafe)` under strict concurrency, among others.
  - Each acknowledgement is a narrow `unsafe` expression, meant as an audit marker.
  - `@safe` marks declarations that wrap unsafe types but are safe to use.
  - Notably, it does *not* flag `@unchecked Sendable`.
- **Migration experience.**
  - The official migration guide tells developers whose types already synchronise with locks or queues to mark the conformance `@unchecked Sendable`. It permits `nonisolated(unsafe)` only when all access is externally guarded ([CommonProblems.md](https://raw.githubusercontent.com/swiftlang/swift-migration-guide/main/Guide.docc/CommonProblems.md)).
  - The Language Steering Group's *approachable concurrency* vision documents several migration problems ([vision](https://github.com/swiftlang/swift-evolution/blob/main/visions/approachable-concurrency.md)):
    - false positives in single-threaded code;
    - `@MainActor` annotations spreading through transitive callers;
    - errors when non-Sendable arguments cross into nonisolated async functions;
    - crashes from dynamic isolation assertions in partially migrated code.
  - Swift 6 itself shipped data-race checking as an *opt-in* language mode on 2024-09-17 ([announcement](https://www.swift.org/blog/announcing-swift-6/)).
  - Swift 6.2 (2025-09-15) added default main-actor isolation, caller-context async functions and `@concurrent` ([release post](https://www.swift.org/blog/swift-6.2-released/)).
  - **[inference]** Swift's pain is concentrated where *reference types and actors* meet legacy callback/lock code. A hand-written lock-protected class like `hx_store` is precisely the case Swift's guide routes to `@unchecked`, unless it is rewritten around `Mutex<State>`. Mithril should make the `Mutex<State>` form the only form, so "lock-protected" is checked rather than asserted.
  - I could not search for independent large-codebase migration reports this session; that gap is noted in Open questions.

**Lessons for Mithril [inference, medium-high].**
- Swift needed four mechanisms (regions, `sending`, `Mutex`, `~Escapable`) because it started with shared classes.
- A language that starts from MVS needs `sending` (spelled `sink` in Hylo/Mithril), `Mutex<State>` and non-escaping views. It does not need region inference.
- Swift's main-actor dialect work is irrelevant to Hearth.

### 3. Hylo: the design is coherent, the concurrency layer is a stub

- **Implementation status.**
  - The `hylo` README says "most of our efforts now go towards the new compiler" in `hylo-new` ([hylo](https://github.com/hylo-lang/hylo)).
  - `hylo-new`'s compiler `hc` is written in Swift and links LLVM 23. It has no releases ([hylo-new](https://github.com/hylo-lang/hylo-new)).
  - The site calls the compiler and stdlib "still in their early stages" and lists "Structured concurrency made easy" with talks by Lucian Radu Teodorescu (ACCU 2022–2024), but links no concurrency design document ([hylo-lang.org](https://hylo-lang.org/)).
- **Spec.**
  - The visible specification defines single-thread sequencing.
  - It reserves `async`/`await` with no semantics.
  - It has a `Sinkable` trait but no Sendable-like rule.
  - It exposes `Builtin.Pointer` / `aligned_alloc` without an `unsafe` keyword or capability ([spec](https://github.com/hylo-lang/specification/blob/main/spec.md)).
- **Stdlib reality.**
  - `spawn_` takes a `sink [E]() -> Int` closure and returns a scope-bound `Future`. `escaping_spawn_` returns an `EscapingFuture` that can leave the scope ([Spawn.hylo](https://raw.githubusercontent.com/hylo-lang/hylo/main/StandardLibrary/Sources/Concurrency/Spawn.hylo)).
  - Futures are built on `concore2full_spawn2` via FFI. The callback reconstructs its frame with `PointerToMutable<Self>(type_punning: ...)`, and `await` "may return on a different OS thread" ([Future.hylo](https://raw.githubusercontent.com/hylo-lang/hylo/main/StandardLibrary/Sources/Concurrency/Future.hylo)).
  - The stdlib index shows `PointerToMutable` with an `unsafe[]` subscript and `MemoryAddress`, but no mutex, atomic or channel ([hylodoc](https://hylodoc.web.app)).
- **Values and borrow checking.** "Hylo allows access to a mutable value through exactly one binding at any given time." An `inout` projection "is not a reference in the usual sense" ([bindings](https://docs.hylo-lang.org/language-tour/bindings)). Borrow checking is an abstract interpretation over Hylo IR with ghost instructions ([IWACO'23](https://2023.splashcon.org/details/iwaco-2023-papers/5/Borrow-checking-Hylo)).

**[inference, high]** Hylo validates the *sequential* half of R09's model: MVS, `sink`/`inout`, and no lifetime annotations. It provides no evidence about shared mutable state across threads. Its `sink` closure into `spawn_` is the right transfer primitive. However, with no Sendable-like kind, a captured `PointerToMutable` could be shared silently. That is precisely the gap a Mithril "transfer kind" must close.

### 4. Mojo: ownership without a thread-safety story

- Mojo's argument conventions are `read` (default), `mut`, `var` (owned), `ref`, `out` and `deinit`.
  - Transfer is written `^`.
  - A mutable reference may not alias any other reference to the same value.
  - The ownership page says nothing about threads or data races ([ownership](https://mojolang.org/docs/manual/values/ownership)).
- Origins track which variable owns a value and whether it is mutable. Wildcard "unsafe any" origins disable argument exclusivity and are a "last resort" ([lifetimes](https://mojolang.org/docs/manual/values/lifetimes)).
- The roadmap ([roadmap](https://mojolang.org/docs/roadmap)):
  - marks argument conventions and "explicitly destroyed (linear) types" as done;
  - lists "Finalizing internal origins" and "Supporting mutable aliasing" as open Phase 2 memory-safety items;
  - lists first-class `async` as not started;
  - does not mention threads, data-race safety or Send/Sync-like traits.

**[inference, medium]** Mojo shows that linear types and exclusivity are deployable in a performance language. It offers no evidence on *checked* concurrent shared state. Its explicit open item "supporting mutable aliasing" is the same problem G05 asks about, unsolved.

### 5. Verona: regions, cowns and BoC, still research in 2026

- **Reggio** (OOPSLA 2023) organises objects into a forest of isolated regions, each with its own memory-management strategy. A thread allocates only in one active region, and reference capabilities enforce isolation so "data access never needs expensive atomic operations" ([arXiv 2309.02983](https://arxiv.org/abs/2309.02983)).
- **BoC** (OOPSLA 2023) creates atomic, ordered units of work over several resources. It is implemented as a C++ runtime and evaluated on Savina ([MSR](https://www.microsoft.com/en-us/research/publication/when-concurrency-matters-behaviour-oriented-concurrency/)).
- **Publications.** The project's list adds:
  - PLDI 2025 *Dynamic Region Ownership for Concurrency Safety*;
  - PPoPP 2025 *DORADD: Deterministic Parallel Execution in the Era of Microsecond-Scale Computing*;
  - ISMM 2024 abstracts on refcounting immutable cyclic data and message-passing allocators.

  It lists nothing for 2026 ([publications](https://microsoft.github.io/verona/publications.html)).
- **The PLDI 2025 paper** enforces region ownership *dynamically* in a Python-like interpreter. It makes races into "deterministic dynamic failures"; the abstract reports no overhead numbers ([MSR](https://www.microsoft.com/en-us/research/publication/dynamic-region-ownership-for-concurrency-safety/)).
- **Pyrona** reports a deep-immutability draft PEP, a CPython 3.12 prototype and a May 2025 Language Summit talk. On region ownership for Python, "nothing is ready to try yet" ([Pyrona](https://microsoft.github.io/verona/pyrona.html)).
- **The main repo** is "not ready to be used outside of research" and "under going a massive refactoring" ([GitHub](https://github.com/microsoft/verona)). verona-rt is public, with no release stated ([verona-rt](https://github.com/microsoft/verona-rt)).

**[inference, medium-high]**
- A cown is a `Mutex<Region>` whose critical sections are scheduled asynchronously.
- BoC's distinctive power is atomic acquisition of *multiple* cowns. `store.c` never needs this: one mutex, and the reader's two critical sections are bridged by ownership of the buffer, not by holding two resources.
- BoC also presumes that behaviours do not block. Hearth's compute thread *does* block (`acquire` waits on `done_cv`), so adopting BoC would mean rewriting the forward pass in continuation style.
- Regions earn their keep for shared mutable *object graphs*, which Hearth does not have.
- DORADD's deterministic-parallel framing is relevant to INV-DET and worth a follow-up read. I could not fetch its abstract (ACM 403).

### 6. Pony: reference capabilities in an I/O ecosystem, with a trusted C runtime

- Six capabilities. Only `iso`, `val` and `tag` cross actors, which avoids data races without locks ([tutorial](https://tutorial.ponylang.io/reference-capabilities/reference-capabilities.html)).
- In the 2026 stdlib, `TCPConnection.send` takes `(ByteSeq | ByteSeqIter val)`, so outgoing I/O data is immutable and shareable ([stdlib](https://stdlib.ponylang.io/net-TCPConnection/)).
- **FFI gating.** `ponyc --safe` reads "Allow only the listed modules to use C FFI" and, with no modules listed, "only builtin is allowed" ([options.c](https://raw.githubusercontent.com/ponylang/ponyc/main/src/libponyc/options/options.c)). The FFI tutorial says declared C types are trusted, not verified ([FFI](https://tutorial.ponylang.io/c-ffi/calling-c.html)). This is a deployed precedent for *package-granular* `Unsafe` authority.
- **The trusted kernel still breaks.** An August 2026 post describes swarm-randomised TCP stress tests exposing unbounded memory growth. The cause was in the runtime allocator: a global pool with cross-thread frees, never-returned small slots and no coalescing. It was replaced by a snmalloc-inspired, per-thread-owned arena allocator with batched cross-thread frees ([blog](https://www.ponylang.io/blog/2026/08/ponys-arena-allocator/)).
- The project is in a run of breaking changes toward Pony 1.0 as of September 2026 ([blog index](https://www.ponylang.io/blog/)).

**[inference, high]** Pony shows two things. Capabilities make application code race-free. And the unsafe runtime underneath, here allocator and I/O, is where bugs concentrate and where *randomised, schedule-perturbing testing* pays off. Mithril's audited layer needs the same test discipline, not just review.

### 7. OxCaml (2025): concurrency modes and capsules; Scala separation checking

- **DRFCaml** (POPL 2025, Distinguished Paper) adds *contention* and *portability* modes on top of locality, uniqueness and affinity. Its core idea is the **capsule**: "a region of memory whose access is controlled by a unique ghost key". Reader-writer locks let threads acquire partial or full ownership of a key. Soundness is proved in Iris/Coq ([POPL'25](https://popl25.sigplan.org/details/POPL-2025-popl-research-papers/23/Data-Race-Freedom-la-Mode)).
- **Shipped API.**
  - `('a, 'k) Capsule.Data.t` is branded by `'k`.
  - Access requires a `Password`; passwords are `local`.
  - Keys are `unique`.
  - `Capsule.Mutex.create` consumes a key and then acts as a dynamically unique key.
  - Reader-writer locks are "Coming Soon", and the ergonomic `Portable.Capsule` API is work in progress ([capsules](https://oxcaml.org/documentation/parallelism/capsules/)).
  - OxCaml presents itself as Jane Street's production compiler and a set of fast-moving extensions with no stability guarantees ([oxcaml.org](https://oxcaml.org/)).
- **Scala 3.** Capture checking frames capabilities as tracked references. The reference page says that "mutation and separation tracking" are "currently in development" ([Scala docs](https://docs.scala-lang.org/scala3/reference/experimental/cc.html)).

**[inference, medium-high]** OxCaml is the clearest 2025 evidence that retrofitting race freedom onto a language with *shared mutable heaps* needs new mode axes plus branded capsules. MVS avoids most of that. With no shared heap in safe code, "contended" data exists only inside stdlib sync types. The capsule-as-mutex pattern collapses to Swift's `Mutex<State>`. The capsule idea remains the right *escape valve* if Mithril later needs lock-protected object graphs: a branded region plus a key held by the lock, without full Verona regions.

### 8. Austral: linear types, no concurrency experience to report

- The spec's rationale argues linear values give "safe concurrency" because a linear value has a single owner, so no other thread can write to it. It defines no thread primitives, synchronisation or memory model in the portion I could read ([spec](https://austral-lang.org/spec/spec.html)).
- The README claims the compiler "implements every feature of the spec". It lists "No first-class async" as an anti-feature and says nothing about threads ([GitHub](https://github.com/austral/austral)).

**[inference, high]** There is no Austral concurrency experience to learn from. The useful Austral lessons are capability-flow and the acknowledged FFI gap, which R09 already covers.

### 9. Rust: how much `unsafe` do I/O, allocator and concurrency crates need, and why

**Ecosystem-wide.**
- In May 2024, 24,362 crates (19.11% of ~127,000 crates with significant code) used `unsafe` directly, and 34.35% called into a crate that does. Most uses are calls into C/C++ code ([Rust Foundation](https://rustfoundation.org/news/unsafe-rust-in-the-wild-notes-on-the-current-state-of-unsafe-rust/)).
- A 2016 analysis found most unsafe blocks small, wrapping only the operations that need it ([Ozdemir](https://cs.stanford.edu/~aozdemir/blog/unsafe-rust-syntax/)).
- A mixed-methods study (19 interviews, 160 survey responses; revised February 2026) found developers use `unsafe` mainly when they see no alternative. It also found that some *foreign aliasing and concurrency patterns* were hard to encapsulate ([McCormack et al.](https://arxiv.org/abs/2404.02230)).
- **Bugs.** Qin et al. (PLDI 2020) inspected 850 unsafe usages, 70 memory-safety bugs and 100 concurrency bugs ([paper](https://songlh.github.io/paper/rust-study.pdf)):
  - unsafe code was used extensively and "usually for good reasons (e.g., performance, code reuse)";
  - all memory-safety bugs involved unsafe code;
  - *all blocking bugs studied were in safe code*;
  - non-blocking bugs occurred in both.

**Pattern-level unsafe kernels.** I counted lines containing the `unsafe` keyword in fetched sources. That counts syntactic sites, not lines inside unsafe blocks, so it under-states block size (medium confidence).

| Pattern | Crate / file | Size | Unsafe sites | Why unsafe is needed |
|---|---|---|---|---|
| Slab arena with `usize` handles | `slab` [lib.rs](https://raw.githubusercontent.com/tokio-rs/slab/master/src/lib.rs) | ~1,500 lines | 9 lines: 3 public opt-in `*_unchecked` getters, 3 doc examples, 3 internal in `get_disjoint_mut` | disjoint multi-borrow and unchecked indexing (performance) |
| Generational arena | `generational-arena` [lib.rs](https://raw.githubusercontent.com/fitzgen/generational-arena/master/src/lib.rs) | — | 0: `#![forbid(unsafe_code)]`; `Index {index, generation: u64}` checked on every access | none |
| Generational arena | `thunderdome` [lib.rs](https://raw.githubusercontent.com/LPGhatguy/thunderdome/main/src/lib.rs) | — | 0: `#![deny(unsafe_code)]`; 8-byte keys | none |
| Lock-free concurrent slab | `sharded-slab` [README](https://raw.githubusercontent.com/hawkw/sharded-slab/main/README.md) | — | all `unsafe` confined to loom `UnsafeCell` accesses; loom permutation-tested against the C11 memory model; "currently experimental" | lock-free slot reuse with generations against ABA |
| Epoch reclamation | `crossbeam-epoch` 0.9.21 ([Guard](https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/struct.Guard.html), [Shared](https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/struct.Shared.html)) | — | client-facing: `Shared::deref/deref_mut/as_ref/into_owned` and `Guard::defer_destroy/defer_unchecked` are `unsafe fn` | reachability after unlink cannot be typed; only `defer` (`Send + 'static`) is safe |
| MPMC channel (linked blocks) | std [mpmc/list.rs](https://raw.githubusercontent.com/rust-lang/rust/master/library/std/src/sync/mpmc/list.rs) | ~550 lines | 17 lines | atomic slot hand-off, block allocation |
| 4096-aligned DMA buffer | glommio [dma_buffer.rs](https://raw.githubusercontent.com/DataDog/glommio/master/glommio/src/sys/dma_buffer.rs) | ~200 lines | 6 lines (`alloc` with `Layout(size, 4096)`, dealloc, raw slice views) | custom-aligned allocation |
| Direct-I/O file API | glommio [dma_file.rs](https://raw.githubusercontent.com/DataDog/glommio/master/glommio/src/io/dma_file.rs) | ~1,150 lines | 2 lines (advisory-lock release) | reads return an owned `ReadResult`, so no unsafe is needed for buffers |
| io_uring reactor | glommio [sys/uring.rs](https://raw.githubusercontent.com/DataDog/glommio/master/glommio/src/sys/uring.rs) | ~2,200 lines | 11 lines (SQE filling, raw pointers handed to the kernel, liburing FFI, registered-buffer allocator) | the kernel reads and writes memory asynchronously |
| io_uring owned-buffer API | tokio-uring [DESIGN.md](https://github.com/tokio-rs/tokio-uring/blob/master/DESIGN.md) | — | the raw submission API is omitted because it "would be unsafe"; buffers are passed by value and returned in `BufResult`; a dropped future leaves the buffer owned by the runtime until completion | the kernel must own in-flight buffers |
| OS-scale TCB | Asterinas [ATC'25](https://www.usenix.org/conference/atc25/presentation/peng-yuke) | Linux-ABI OS, 210+ syscalls | memory-safety TCB ~14.0% of the codebase (the OSTD framework) | page tables, devices, context switch |
| Driver isolation | Tock [capsules/core](https://raw.githubusercontent.com/tock/tock/master/capsules/core/src/lib.rs) | — | `#![forbid(unsafe_code)]` for capsules | unsafe lives in kernel and chip crates |

**Why completion I/O needs ownership.** Rust futures cancel by being dropped, and destructors may legally never run, so a *borrowed* buffer given to io_uring can be touched while the kernel writes it. Pinning prevents freeing but not access. The kernel must logically own the buffer ([without.boats, 2020](https://without.boats/blog/io-uring/)). tokio-uring adopted this, and it still calls itself "very young" ([README](https://github.com/tokio-rs/tokio-uring)).

**Safe Rust building blocks that cover `store.c` today (high).**
- `#[repr(align(x))]` raises alignment to any power of two up to 2^29 ([Reference](https://doc.rust-lang.org/reference/type-layout.html)), so 4096-aligned page types are safe.
- Windows `seek_read` is a safe positional read into `&mut [u8]` ([FileExt](https://doc.rust-lang.org/std/os/windows/fs/trait.FileExt.html)), and `custom_flags` is a safe way to add `CreateFile` flags ([OpenOptionsExt](https://doc.rust-lang.org/std/os/windows/fs/trait.OpenOptionsExt.html)).
- `Arc::into_inner` returns the value iff it holds exactly one strong reference. Of all callers racing on clones, exactly one gets it. `strong_count` is explicitly racy and must not drive decisions ([Arc](https://doc.rust-lang.org/std/sync/struct.Arc.html)).
- `bytes` (1.12.1): `BytesMut::split_to`/`split_off` are O(1) refcount splits, `freeze` is zero-cost, and `Bytes::try_into_mut` converts back when unique ([BytesMut](https://docs.rs/bytes/latest/bytes/struct.BytesMut.html); [Bytes](https://docs.rs/bytes/latest/bytes/struct.Bytes.html)).
- Scoped threads (stable since 1.63) may borrow parent stack data, including mutably, because all are joined at scope end ([thread::scope](https://doc.rust-lang.org/std/thread/fn.scope.html)).

**[inference, medium-high]** A Rust port of `store.c` could be written with zero `unsafe` in the crate, given std's `Mutex`/`Condvar`/`Arc`/threads plus a page-aligned type. The exception is overlapped reads on Windows: the safe std read path is not documented for overlapped handles, and Hearth needs overlapped handles for queue depth. That makes a ~20–40-line platform shim, the size of Hearth's own `hx__io` plus `hx__rw`. This is strong external evidence that the store's *logic* never needs an `Unsafe` island; only the platform layer does.

### 10. Verifying the protocol layer: what types cannot do, and what does

- **GhostCell** (ICFP 2021) separates permissions from data. One branded token controls access to a whole collection, which supports internally shared structures such as graphs and doubly linked lists. It is proven sound by extending RustBelt in Coq ([MPI-SWS](https://plv.mpi-sws.org/rustbelt/ghostcell/)).
- **Verus tokenized state machines** target exactly "locks that manage ownership of an underlying resource", "reference-counted smart pointers" and concurrent queues, using linear ghost state. The guide is work in progress ([Verus](https://verus-lang.github.io/verus/state_machines/)).
- **LVars** (FHPC 2013) show that shared state whose writes are monotone and whose reads are threshold-gated is deterministic by construction. An extension admits "failures but never wrong answers" ([Kuper & Newton](https://users.soe.ucsc.edu/~lkuper/papers/lvars-fhpc13.pdf)).

**[inference, medium]**
- The slab protocol ("a buffer in state LOADING is owned by the reader that assigned it") ties a permission to a runtime value in the metadata. Plain ownership types cannot express this. Three ways out:
  1. **Move the buffer itself.** Ownership travels with the value, as in the design below. Purely type-checkable.
  2. **Split permission from data.** GhostCell/capsule brands, or Verus ghost tokens; both are verification-grade.
  3. **Keep an unsafe arena with a safe facade.** Rust `slab` style.

  Option 1 is enough for Hearth.
- LVars give the semantic argument for the `Nondet` boundary. *Logically*, the store is a constant map (layer, expert) → file bytes, and every read is either that value or a failure. That is why it can be observationally deterministic even though eviction and timing are not.

---

## Implications for Mithril

**A. A concrete encoding of `store.c` with no user-level `Unsafe`** [inference, medium-high]. Pseudocode in R09's conventions:

```
type StoreState { meta: Array<SlotMeta>, slot_of: Array<Int32>, bufs: Array<SlotBuf>,
                  dq: Ring<Int32>, pfq: Ring<Int32>, heat: Array<Float64>, now: UInt64, ... }
enum SlotBuf { free(SlabBuf), loading, ready(Frozen<SlabBuf>) }      // SlabBuf: linear, 4096-aligned

fun reader(st: let Shared<Mutex<StoreState>>, files: let Array<File>) {IO, Time, Nondet}
  loop
    let job = st.with_lock(work_cv) { s in s.next_job() }            // returns sink (key, slot, SlabBuf)
    var buf = job.buf                                                 // exclusively owned, lock released
    let ok  = files[job.file].read_at(&buf.bytes, job.offset)         // inout borrow for a blocking call
    st.with_lock { s in s.finish(job, ok, sink buf) }                 // .ready(freeze(buf)) or .free(buf)

fun acquire(st: let Shared<Mutex<StoreState>>, l: Int, e: Int) -> Option<Lease>   // Lease: linear
fun release(st: ..., sink lease: Lease)                                            // compiler enforces pairing
subscript bytes(lease: let Lease): Span<UInt8>                                     // second-class view for kernels
```

- **Eviction.** Eviction calls `Frozen.into_unique(sink f)`. Hearth's `refs` stays the *policy* signal, and uniqueness becomes the *safety* check, so an accounting bug turns into a failed eviction, not a use-after-free.
- **Mapping the remaining C mechanisms.**
  - **Condvar waits** become `with_lock(cv)` forms whose `inout` state may change across the wait. That is exactly what `inout` already means [inference].
  - **Token-boundary hooks** (`tick`) stay generation-counter bumps inside the lock.
  - **The "one compute thread" contract** becomes a non-transferable `StoreClient` handle.
  - **`hx_store_heat`'s escaping pointer** becomes a copy.
- **Large pages.** Hearth allocates one arena (`hx_alloc_large`, large pages when available). Per-slot allocations would waste large-page rounding on slab sizes that are not multiples of 2 MiB, such as the 2.39 MiB Qwen3-class slab in `test_store.c`. The stdlib should therefore offer `Arena.split(n) -> Array<SlabBuf>`: owned, disjoint chunks of one allocation, with per-chunk uniqueness tracking.
  - This is part of the audited kernel.
  - `bytes`' split, freeze and `try_into_mut` is the closest precedent. [inference] Its refcount is per parent allocation, though, so sibling chunks would block reclamation. Mithril's version needs per-chunk counts.

**B. The audited layer is small and generic.** It contains:
- `Mutex<T>` + `Condvar` (OS SRWLOCK/CONDITION_VARIABLE or pthread);
- `Arena` / `SlabBuf` with chunk split;
- `Frozen<T>` (atomic refcount, `into_unique`);
- `File.read_at` (overlapped-and-wait on Windows, `pread` + `O_DIRECT`/`F_NOCACHE` on POSIX);
- scoped `Thread` / service;
- optionally a bounded MPSC ring.

[inference] This is Hearth's existing platform layer (`platform_win.c` 693 lines, `platform_posix.c` 511 lines, which also cover time, logging and paths) re-expressed. Rust analogues sit at 2–17 unsafe sites per component (table §9). Expect a few hundred lines per OS behind `Unsafe`/`Foreign`, tested with an ASan/TSan matrix and a loom-style scheduler. Not regions.

**C. What the core type system must add beyond R09** [inference, medium-high]:
1. **A transfer kind** (Swift `Sendable`, Rust `Send`, Pony `iso`/`val`). It is *derived*: an MVS value is transferable iff it contains no non-transferable stdlib handle. `sink` across `spawn` requires it. Without it, Hylo-style `spawn_` silently shares raw pointers (§3).
2. **A share kind** (Rust `Sync`, Pony `val`/`tag`) for `Frozen<T>`, `Mutex<T>`, `File` and capabilities that many threads may hold `let`.
3. **First-class capabilities in long-lived services.** R09 makes effects implicit capability parameters. Reader threads outlive the call that spawned them, so the service must *hold* `IO`/`Time`/`Nondet` capabilities, which must themselves be transfer/share-kinded. Mithril needs a rule for boxing a capability into a service whose lifetime is bounded by an owning scope (`store.close` joins it). [inference] If capabilities are second-class by default, this is the one place they become first-class, and the audit graph must show it.
4. **Not needed in v1:** region inference, cowns/BoC, Pony's six-capability lattice, OxCaml contention/portability modes, epoch reclamation. Revisit if Mithril targets shared mutable object graphs, lock-free structures or multi-resource atomic behaviours. The cheapest upgrade path is OxCaml-style branded capsules held by a `Mutex`.

**D. `Nondet` and determinism** [inference, medium-high].
- **Inside the store.** Victim choice depends on thread timing (which `refs`/holds are live when a reader calls `next_job`). So do the LFU sampling sequence, mirror selection (`outstanding[]`) and every stat. All of these are `Nondet`.
- **Across the store's API.** Its *value-level* outputs are deterministic modulo `Fail`, because bytes come from an immutable source.
- **Proposals:**
  - **(i) A `Blob` capability.** An immutable, content-verified byte source; reads from it are value-deterministic. This needs a full content hash for mirrors, not Hearth's sampled check.
  - **(ii) An audited `deterministic { }` boundary.** It discharges internal `Nondet`, `Time` and lock-observation effects from exported functions. It is the `Nondet` counterpart of Swift's `@safe` and Rust's interior `unsafe`, and is justified by a named test or proof (for Hearth, the INV-DET-1 golden test).
  - **(iii) `stats()`-style functions keep `Nondet`** in their signature.

  Without (ii), either the logits path inherits `Nondet` (making R09's type rule vacuous), or locks must be exempt from `Nondet` (making it unsound).
- **Atomics.** Atomics inside `Frozen` refcounts and `par for` work distribution are not observable and need no `Nondet`. User-visible atomics do.

**E. AI-first angle** [inference, medium].
- The audit surface becomes a list: which modules hold `Unsafe`, which hold `deterministic { }` boundaries, and which spawn services with which capabilities.
- A Darwin-Gödel-Machine-style optimiser can mutate eviction policy, prefetch depth or queue structure freely inside `StoreState` (pure values) without gaining `Unsafe`. Any edit that touches the boundary is flagged for the verifier lane.
- The loom-style scheduler gives the optimiser a liveness oracle. That matters because type safety will not catch the deadlocks it is likely to introduce (Qin et al.).

## Implications for Hearth

1. **Add a ThreadSanitizer CI job** (Linux/Clang) for `test_store` and `test_pool`. CI has ASan/UBSan but no TSan, while the store's correctness rests on lock discipline and the pool on atomics. [inference] This is the cheapest way to check, today, the property Mithril would prove by construction.
2. **Fix or document `hx_store_heat()`.** It returns an unguarded pointer to `count_f`, which `count_use` writes under the mutex. With several caller threads, which the tests exercise, that is a C11 data race (benign for diagnostics, still UB). Return a copy under the lock, or document "single compute thread only".
3. **Make mirror validation full-content (hash) or label INV-DET-1 as "assuming byte-identical mirrors".** Today `check_mirror` samples the first page of up to 16 slabs. INV-DET-1 promises independence from mirrors.
4. **Keep the handle-based, generation-stamped style.** It is what makes a safe port easy. New store features (multi-layer lookahead, prediction-aware eviction, a VRAM tier) should stay as integer handles plus stamps, not linked structures.
5. **If io_uring or IOCP completion ports are adopted** for deeper queue depth (the measured overlapped advantage suggests queue depth matters), design the buffer API as *ownership transfer* (tokio-uring style) from day one. That keeps the later Mithril port safe [inference, high].
6. **Port order for the Mithril acid test** (refines R09): `quant` → `model` → `modelfile` → `store` (logic, against the audited layer) → `platform` (becomes the audited layer). The store is no longer the riskiest Mithril port; the platform shim is.

## Where the seed discussion is right or wrong

- **B5 (no pointers; affine-stride DAGs so buffers never alias): partly right.**
  - The store's *metadata* is pointer-free in practice (integer handles), and MVS makes no-alias a default without affine analysis.
  - The *slab lifecycle* is neither affine nor static. It is a runtime typestate driven by I/O completion and refcounts, so it needs linear ownership transfer plus a refcounted freeze, not stride analysis.
  - R10 independently notes that routing makes expert selection non-affine. [inference, high]
- **C7 (memory transfers as explicit async pipelines): right in spirit, wrong in mechanism.**
  - Hearth's demand/prefetch pipeline is threads + one monitor + blocking positional reads, and needs no async language feature.
  - Completion-based async I/O *would* force owned-buffer APIs ([without.boats](https://without.boats/blog/io-uring/)).
  - R10 already corrects C7's latency numbers. [inference, high]
- **C8 (control plane + compute plane in one binary): right, with a memory-model corollary.**
  - The control plane (store) needs monitors, linear leases and capability-holding services.
  - The compute plane needs disjoint `inout` slices and ordered reductions (R09).
  - One MVS core serves both. The difference lies only in which stdlib types appear. [inference, medium-high]
- **G2 (SPSC rings + PCIe BAR apertures):** Lock-free rings are plausible stdlib components; std's linked-block channel has 17 unsafe sites in ~550 lines (§9). Hearth's queues are mutex-protected and not a bottleneck at slab granularity, so lock-free rings are *optional* for v1. BAR apertures are `Foreign`/`Unsafe` by nature. [inference, medium]
- **G1 (spdk):** User-space NVMe would move DMA ownership into user space. That is the io_uring ownership problem with even less kernel help. It would live entirely in the audited layer. [inference]
- **H7 (Mojo as the nearest competitor):** Mojo's own roadmap lists no thread-safety or Send/Sync work, and "supporting mutable aliasing" is open ([roadmap](https://mojolang.org/docs/roadmap)). On *checked* concurrent shared state, Mojo is not ahead of the Mithril design. The seed's other Mojo claims are outside this topic. [inference, medium]
- **I5 (`hot_patch` atomic pointer swap "in a single CPU cycle"): wrong emphasis, as R10 says.**
  - The swap is easy. Reclaiming the old version while readers may hold it is hard, and Rust's general solution (epoch reclamation) exposes `unsafe` to every client ([crossbeam Shared](https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/struct.Shared.html)).
  - Hearth has a cheaper option: token boundaries are natural quiescent points. If leases may not cross `tick` (they do not today: compute releases within the layer), a swap at `tick` needs only `Frozen<T>` refcounts, no epochs. [inference, medium-high]
- **I7 (safe self-modifying code):** Executable-page management is irreducibly `Unsafe` and out of the store's scope. Nothing here suggests it can be made safe by the memory model. [inference]

## Open questions

1. **Prototype gap.** No line of the proposed Mithril store has been written. The next step R09 asked for is still needed: write `store.mith` against a mock audited layer, compile it to C (R09's C backend), and run Hearth's `test_store.c` scenario suite plus the INV-DET-1 golden test. Measure (a) the size of the audited layer, (b) the cost of `Frozen` refcount traffic per token, and (c) whether `with_lock` + condvar forms express `break_holds` and `wait_any` freshness without contortion.
2. **Swift migration reports.** I could not search for independent large-codebase Swift 6 migration reports or an academic study of `@unchecked Sendable` frequency. A follow-up with search budget should quantify how often lock-based classes end up `@unchecked` in server code (swift-nio and similar).
3. **DORADD (PPoPP 2025).** Is its deterministic-parallel execution model relevant to INV-DET-1/2 for batched prefill? The abstract could not be fetched (ACM 403).
4. **Hylo's concurrency direction.** Will Hylo add a Sendable-like kind or remote parts? The ACCU 2024 talk "Concurrency Hylomorphism" may say; I could not watch it.
5. **The `Nondet` boundary design.** Should it be checked by tests (cheap; Hearth already has them), by refinement types (acquire returns bytes equal to `blob[entry]`), or by a Verus-style ghost proof? And who may declare one: any module, or only modules granted a `DeclareDeterministic` capability?
6. **Second-class capabilities versus long-lived services.** What is the minimal capture-tracking rule for boxing capabilities into scope-bounded services? Scala's separation checking is still "in development", so there is no settled precedent.
7. **Concrete unsafe-site counts** for the remaining stdlib pieces (Condvar, overlapped `read_at`) on all three CI OSes. These are estimates here.

## Sources

Hearth (local, read-only): `hearth/engine/src/store.c`, `hearth/engine/src/hx_store.h`, `hearth/engine/src/platform_win.c`, `hearth/engine/src/platform_posix.c`, `hearth/engine/src/model.c`, `hearth/engine/tests/test_store.c`, `hearth/CMakeLists.txt`, `hearth/governance/INVARIANTS.md`. Mithril: `Mithril/docs/research/R09-language-building-blocks.md`, `R10-seed-fact-check.md`.

- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0414-region-based-isolation.md
- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0430-transferring-parameters-and-results.md
- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0433-mutex.md
- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0446-non-escapable.md
- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0447-span-access-shared-contiguous-storage.md
- https://github.com/swiftlang/swift-evolution/blob/main/proposals/0458-strict-memory-safety.md
- https://github.com/swiftlang/swift-evolution/blob/main/visions/approachable-concurrency.md
- https://raw.githubusercontent.com/swiftlang/swift-migration-guide/main/Guide.docc/CommonProblems.md
- https://raw.githubusercontent.com/swiftlang/swift-migration-guide/main/Guide.docc/IncrementalAdoption.md
- https://www.swift.org/blog/announcing-swift-6/
- https://www.swift.org/blog/swift-6.2-released/
- https://www.massicotte.org/problematic-patterns
- https://github.com/hylo-lang/hylo
- https://github.com/hylo-lang/hylo-new
- https://hylo-lang.org/
- https://github.com/hylo-lang/specification/blob/main/spec.md
- https://docs.hylo-lang.org/language-tour/bindings
- https://hylodoc.web.app
- https://raw.githubusercontent.com/hylo-lang/hylo/main/StandardLibrary/Sources/Concurrency/Spawn.hylo
- https://raw.githubusercontent.com/hylo-lang/hylo/main/StandardLibrary/Sources/Concurrency/Future.hylo
- https://2023.splashcon.org/details/iwaco-2023-papers/5/Borrow-checking-Hylo
- https://mojolang.org/docs/manual/values/ownership
- https://mojolang.org/docs/manual/values/lifetimes
- https://mojolang.org/docs/roadmap
- https://github.com/microsoft/verona
- https://github.com/microsoft/verona-rt
- https://microsoft.github.io/verona/
- https://microsoft.github.io/verona/publications.html
- https://microsoft.github.io/verona/pyrona.html
- https://arxiv.org/abs/2309.02983
- https://www.microsoft.com/en-us/research/publication/when-concurrency-matters-behaviour-oriented-concurrency/
- https://www.microsoft.com/en-us/research/publication/dynamic-region-ownership-for-concurrency-safety/
- https://tutorial.ponylang.io/reference-capabilities/reference-capabilities.html
- https://tutorial.ponylang.io/c-ffi/calling-c.html
- https://raw.githubusercontent.com/ponylang/ponyc/main/src/libponyc/options/options.c
- https://stdlib.ponylang.io/net-TCPConnection/
- https://www.ponylang.io/blog/
- https://www.ponylang.io/blog/2026/08/ponys-arena-allocator/
- https://popl25.sigplan.org/details/POPL-2025-popl-research-papers/23/Data-Race-Freedom-la-Mode
- https://oxcaml.org/
- https://oxcaml.org/documentation/parallelism/capsules/
- https://docs.scala-lang.org/scala3/reference/experimental/cc.html
- https://austral-lang.org/spec/spec.html
- https://github.com/austral/austral
- https://rustfoundation.org/news/unsafe-rust-in-the-wild-notes-on-the-current-state-of-unsafe-rust/
- https://cs.stanford.edu/~aozdemir/blog/unsafe-rust-syntax/
- https://arxiv.org/abs/2404.02230
- https://songlh.github.io/paper/rust-study.pdf
- https://github.com/tokio-rs/tokio-uring
- https://github.com/tokio-rs/tokio-uring/blob/master/DESIGN.md
- https://without.boats/blog/io-uring/
- https://github.com/DataDog/glommio
- https://raw.githubusercontent.com/DataDog/glommio/master/glommio/src/io/dma_file.rs
- https://raw.githubusercontent.com/DataDog/glommio/master/glommio/src/sys/dma_buffer.rs
- https://raw.githubusercontent.com/DataDog/glommio/master/glommio/src/sys/uring.rs
- https://raw.githubusercontent.com/tokio-rs/slab/master/src/lib.rs
- https://raw.githubusercontent.com/fitzgen/generational-arena/master/src/lib.rs
- https://raw.githubusercontent.com/LPGhatguy/thunderdome/main/src/lib.rs
- https://raw.githubusercontent.com/hawkw/sharded-slab/main/README.md
- https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/
- https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/struct.Guard.html
- https://docs.rs/crossbeam-epoch/latest/crossbeam_epoch/struct.Shared.html
- https://raw.githubusercontent.com/rust-lang/rust/master/library/std/src/sync/mpmc/list.rs
- https://doc.rust-lang.org/reference/type-layout.html
- https://doc.rust-lang.org/std/os/windows/fs/trait.FileExt.html
- https://doc.rust-lang.org/std/os/windows/fs/trait.OpenOptionsExt.html
- https://doc.rust-lang.org/std/sync/struct.Arc.html
- https://doc.rust-lang.org/std/thread/fn.scope.html
- https://docs.rs/bytes/latest/bytes/struct.BytesMut.html
- https://docs.rs/bytes/latest/bytes/struct.Bytes.html
- https://www.usenix.org/conference/atc25/presentation/peng-yuke
- https://raw.githubusercontent.com/tock/tock/master/capsules/core/src/lib.rs
- https://plv.mpi-sws.org/rustbelt/ghostcell/
- https://verus-lang.github.io/verus/state_machines/
- https://users.soe.ucsc.edu/~lkuper/papers/lvars-fhpc13.pdf
