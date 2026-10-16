# R07 — Verification, superoptimisation and rewriting

*Research dossier for the Mithril architecture phase. Compiled 2026-10-11. Every factual claim carries an inline source; my own reasoning is marked **[inference]**. Confidence levels (high / medium / low) are given for key claims. Method note: the shared web-search budget ran out early in this task, so most facts were checked by fetching primary sources directly (arXiv abstracts, project READMEs, papers, official docs). Anything I could not check that way is marked **unverified**.*

---

## Summary

- **The central question has a clean answer, and Hearth already sits on the cheap side of it.** If the floating-point (FP) operation order is fixed (no reassociation, no FMA contraction, same rounding mode, a canonical NaN), then checking that a vectorised kernel is bit-exact against its reference comes down mostly to **matching symbolic expression DAGs modulo a small list of IEEE-exact rewrites**. That check is sound, fast and incomplete. The integer and bit-vector side conditions go to SMT, where they are cheap and decidable. KLEE-FP showed this split on 51 OpenCV SSE kernels in 2011 ([KLEE-FP](http://srg.doc.ic.ac.uk/files/papers/kleefp-eurosys-11.pdf)). (high)
- **Equivalence with a tolerance bound is a different and weaker kind of check.** You can certify a bound for continuous, straight-line code when input ranges are known, using FPTaylor, Satire, Daisy or Gappa, or closed-form summation bounds. The bound breaks at discontinuities such as top-k routing, argmax and round-to-integer quantisation, which are everywhere in MoE inference. **[inference]** (high)
- **Using SMT FP theory as the main tool for numeric kernels is a mistake.** SMT-LIB FP is decidable and bit-precise, but it has no transcendental functions ([SMT-LIB FP](https://smt-lib.org/theories-FloatingPoint.shtml)). Precise FP encodings run slowly: Strata gave up and modelled FP as uninterpreted functions ([Strata](https://stefanheule.com/papers/pldi16-strata.pdf)). And reassociated FP code is not equivalent at all, so no solver can prove that it is. (high)
- **Translation validation suits an AI-first compiler better than a verified compiler.** The search (LLM, MCTS, stochastic) stays untrusted and only a small checker is trusted. Alive2 (47 LLVM bugs found), CryptOpt (randomised x86 search plus a Coq-verified equivalence checker) and VeriISLE (SMT verification of Cranelift lowering rules against Arm's ASL semantics) are the working models ([Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf), [CryptOpt](https://arxiv.org/abs/2211.10665), [VeriISLE](https://github.com/bytecodealliance/wasmtime/tree/main/cranelift/isle/veri)). (high)
- **LLM superoptimisation is now real but mostly unverified.** SuperCoder's "95% correctness" means passing tests, not proven equivalence ([SuperCoder](https://arxiv.org/abs/2505.11480)). LLM-Vectorizer's output could be verified by Alive2 only 38.2% of the time ([LLM-Vectorizer](https://arxiv.org/abs/2406.04693)). Kernel benchmarks have "exploitable loopholes" ([robust-kbench](https://arxiv.org/abs/2509.14279)). Verification oracles, not generators, are the scarce resource. (high)
- **Equality saturation is mature enough to build on.** The options are egg/egglog, TENSAT, Glenside and TensorRight, plus Cranelift's production *acyclic* e-graph, which deliberately does not run full saturation ([egg](https://arxiv.org/abs/2004.03082), [egglog](https://arxiv.org/abs/2304.04332), [Cranelift RFC](https://github.com/bytecodealliance/rfcs/blob/main/accepted/cranelift-egraph.md), [TensorRight](https://github.com/ADAPT-uiuc/TensorRight)). For FP, only IEEE-exact rules are admissible unless a tolerance mode is explicitly enabled. **[inference]**
- **Lean 4 is a credible proof back end and acceptance gate, not a push-button kernel verifier.** Its Float/Float32 types now have a logical model, but the docs say there are no lemmas and the model is not meant as a library ([Lean Float docs](https://lean-lang.org/doc/reference/latest/Basic-Types/Floating-Point-Numbers/)). Its strongest automation, `bv_decide`, runs a SAT solver and checks the certificate rather than replacing the solver ([Lean tactic reference](https://lean-lang.org/doc/reference/latest/Tactic-Proofs/Tactic-Reference/)). (high)
- **Formal ISA semantics are uneven.** Arm has authoritative machine-readable ASL, used by Sail and VeriISLE ([Sail](https://github.com/rems-project/sail)). x86 has the K semantics, which covers Haswell user-level only, so no AVX-512 **[inference]** ([K x86-64](https://github.com/kframework/X86-64-semantics)). There is also a partial Sail x86 translated from ACL2, and Intel's SDM pseudocode. For Zen 5 AVX-512, Mithril will have to build and co-simulation-test a model of the instruction subset it emits. (medium)
- **Seed claims (detail at the end).** B8 has the right shape but the wrong mechanism for FP kernels. F2 is a category error: `openai/math` is real, released October 2026, and is pure mathematics, and Comparator only matches Lean statements. F6 frames things wrongly: Lean wraps solvers in certificates rather than replacing them. I4 is infeasible as stated. (high)

---

## Findings

### 1. Superoptimisation: from Massalin to LLMs

**Classical line.**
- Massalin coined "superoptimizer" in 1987. Her system ran an exhaustive search over short instruction sequences, filtered candidates with a fast probabilistic test, and was feasible only for very short programs ([Wikipedia: Superoptimization](https://en.wikipedia.org/wiki/Superoptimization)).
- Later systems: the GNU Superoptimizer (1992), Denali (2001), and Bansal and Aiken's automatically generated peephole optimisers (2006) ([Wikipedia](https://en.wikipedia.org/wiki/Superoptimization)).

**STOKE (Stanford, 2013).**
- STOKE treats loop-free x86-64 superoptimisation as MCMC sampling over programs. Correctness and performance are both terms in one cost function, and the approach explicitly gives up completeness. It matched or beat `gcc` at full optimisation, and sometimes expert hand-written assembly ([STOKE paper](https://arxiv.org/abs/1211.0557)).
- Its validators are a bounded validator, exponential in the bound, and DDEC (data-driven equivalence checking), which the README calls "not very robust" ([STOKE README](https://github.com/StanfordPL/stoke)).
- The README calls it a research prototype that nobody is actively developing, so seed item G1 should treat it as a reference artifact, not a dependency ([STOKE README](https://github.com/StanfordPL/stoke)).
- A PLDI 2014 follow-up trades FP precision for speed with a tunable cost term ([STOKE README](https://github.com/StanfordPL/stoke)).

**Strata (PLDI 2016)** reused STOKE to *learn* x86-64 semantics.
- It synthesised formulas for 1,795 Haswell instruction variants. The hand-written formulas they were compared against were wrong for 50 of them, and the effort also found errors in the Intel manual ([Strata](https://stefanheule.com/papers/pldi16-strata.pdf)).
- Critically for Mithril, Strata modelled the base FP instructions as **uninterpreted functions**. Its stated reason is that precise FP-over-bitvector modelling that also performs well in SMT is hard. The authors accept that this makes equivalence checking harder in general, but found it sufficient to infer, for example, that a vector FP add is several independent scalar adds ([Strata](https://stefanheule.com/papers/pldi16-strata.pdf)). (high)

**Souper (2017)** is a synthesising superoptimiser for LLVM IR.
- Engineers hand-implemented optimisations it suggested in shipping LLVM and MSVC.
- Run as an automatic pass, it made a Clang binary about 3 MB (4.4%) smaller ([Souper](https://arxiv.org/abs/1711.04422)).

**Minotaur (OOPSLA 2024)** extends synthesis to **integer and FP SIMD** in LLVM, with formally verified results.
- Average speedup 7.3% on GMP (max 13%) and 1.5% on SPEC CPU 2017 (max 4.5%) on Cascade Lake.
- Several of its findings were upstreamed ([Minotaur](https://arxiv.org/abs/2306.00229)). The modest numbers on code already compiled at -O3 are themselves informative.

**CryptOpt (2023)** is the closest existing realisation of seed claim B8.
- It runs a randomised search over x86-64 assembly, benchmarking on the target CPU, for finite-field arithmetic.
- Each output is checked by a new **formally verified equivalence checker** that borrows techniques from SMT solvers and symbolic execution. The proof is mechanised in Coq, and the final theorem mentions little beyond the functional source program and x86-64 operational semantics.
- It produced the fastest known Curve25519 and secp256k1 field arithmetic on Intel 12th/13th-gen CPUs ([CryptOpt](https://arxiv.org/abs/2211.10665)). (high)
- **[inference]** The domain is integer-only (bignum limbs), which is exactly why equivalence checking is tractable there.

**AlphaDev (DeepMind, 2023).**
- An RL agent that builds sorting routines one assembly instruction at a time. After each move it checks correctness *by running test inputs*, and it is rewarded for latency.
- The results were reverse-engineered into C++ and merged into LLVM libc++: up to 70% faster for short sequences, about 1.7% for very long ones ([DeepMind blog](https://deepmind.google/discover/blog/alphadev-discovers-faster-sorting-algorithms/)).
- **[inference]** For sort3–sort5, exhaustive testing over orderings amounts to verification. That does not generalise to FP kernels.

**LLM era (2024–2026).**
- **Meta LLM Compiler** (7B/13B, trained on 546B tokens of LLVM IR and assembly) reached 77% of an autotuner's code-size optimisation potential. Its x86/ARM→IR disassembly round-trips 45% of the time, with 14% exact matches ([LLM Compiler](https://arxiv.org/abs/2407.02524)).
- **SuperCoder** (May 2025) is a benchmark of 8,072 assembly programs averaging 130 lines.
  - Out of the box, Claude-opus-4 was best: 51.5% test pass rate and a 1.43× average speedup over `gcc -O3`.
  - RL-tuned Qwen2.5-Coder-7B reached 95.0% "correctness" with a 1.46× speedup.
  - "Correctness" means **passing tests, not proven equivalence**, and the work is limited to x86-64 ([SuperCoder](https://arxiv.org/abs/2505.11480)). (high)
- **LLM-Vectorizer** (Taneja, Laird, Yan, Musuvathi, Lahiri, 2024) uses LLM agents with test feedback. It reports 1.1–9.4× speedups over ICC/GCC/Clang, but Alive2 could verify only **38.2%** of its TSVC vectorisations, even with domain-specific tricks to scale Alive2 ([LLM-Vectorizer](https://arxiv.org/abs/2406.04693)). (high)
- **KernelBench** (250 PyTorch workloads): frontier models matched the PyTorch baseline in under 20% of cases ([KernelBench](https://arxiv.org/abs/2502.10517)).
- **AlphaEvolve** (May 2025) pairs Gemini models with automated evaluators. It sped up a Gemini matmul kernel by 23% and a FlashAttention kernel by up to 32.5%, and found a 48-multiplication algorithm for 4×4 complex matrices ([DeepMind blog](https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/)).
- **Sakana AI's** September 2025 follow-up states that existing CUDA kernel benchmarks contain "exploitable loopholes" and too little diversity in test conditions, and proposes robust-kbench with LLM-based verifiers ([robust-kbench](https://arxiv.org/abs/2509.14279), [Sakana page](https://sakana.ai/ai-cuda-engineer/)).

**[inference] Lesson for Mithril.** Generators are cheap and plentiful; sound, fast acceptance checks are scarce. A Darwin-Gödel-Machine-style self-improvement loop rewarded on test pass rates will learn to exploit the tests. A loop rewarded only on *checker-accepted* candidates cannot, at least for the semantic half of the reward. Performance still has to be measured. (high)

### 2. Translation validation vs verified compilation

**Translation validation (TV)** checks each individual compiler run rather than the compiler itself. The lineage runs through Necula's PLDI 2000 validator for an optimising compiler ([doi](https://doi.org/10.1145/349299.349314), as cited in [Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)).

**Alive2 (PLDI 2021)** is the reference implementation of *bounded* TV.
- **What it checks:** refinement between pairs of LLVM IR functions, covering all of LLVM's undefined behaviour (undef, poison, immediate UB). It is fully automatic via SMT, targets zero false alarms, and needs no compiler changes.
- **How it bounds cost:** it unrolls loops to a bound and caps time and memory, so it *can miss bugs*.
- **Results:** 47 new LLVM bugs (28 fixed at publication) and 8 patches to the LLVM LangRef.
- **Cost:** running the LLVM unit tests under Alive2 took about 2.5 h on an 8-core machine. Timeouts and out-of-memory failures grow with the unroll factor.
- **FP encoding:** integers are bit-vectors and floats use SMT's FPA theory. x87 80-bit floats are unsupported because the theory lacks them. Alive2 chose to give a NaN bit pattern nondeterministically on bitcast.
- **Solver bugs:** the authors hit six Z3 soundness bugs during development.
- **A telling FP bug:** LLVM rewrote `fadd (fmul nsz a b), +0.0`. That is wrong because adding +0.0 turns −0.0 into +0.0 ([Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)). (high)
- **[inference]** That signed-zero case is exactly the kind of hazard that bites "harmless" SIMD rewrites. One example is initialising an accumulator from the first element instead of from 0.0f.

**Verified compilers.**
- **CompCert** is proven in Coq/Rocq to produce code that behaves exactly as the source semantics prescribe. It uses the Flocq library for FP, targets ARM, PowerPC, RISC-V and x86 (with AArch64 and x86-64 in release notes), and is sold commercially by AbsInt. Version 3.18 shipped in 08/2026, and in 2026 it was qualified for an avionics computer ([CompCert](https://compcert.org/)).
  - Csmith spent about six CPU-years and found **no** middle-end wrong-code bugs in CompCert. It did find wrong-code bugs in the *unverified* front end and an under-specified PowerPC immediate width ([Csmith paper](https://users.cs.utah.edu/~regehr/papers/pldi11-preprint.pdf)). The verified core is real; the trusted periphery is where the bugs live. (high)
- **CakeML** has HOL semantics, a verified back end to machine code for six targets, and a compiler bootstrapped inside HOL. It also includes a verified certificate checker for FP error bounds ([CakeML](https://cakeml.org/)).
- **Vellvm** is an ongoing Rocq formalisation of an LLVM-like infrastructure, with an executable IR interpreter ([Vellvm](https://github.com/vellvm/vellvm)).
- **CertiCoq/CertiRocq** compiles Gallina to Clight or WebAssembly. Large parts are verified and others are in progress ([CertiCoq](https://github.com/CertiCoq/certicoq)).

**Trade-off [inference]:**

| | Verified compiler | Translation validation |
|---|---|---|
| Trusted base | Prover + specs + unverified periphery | Checker + specs |
| Cost per new optimisation | A proof per pass, which is very high | Zero, provided the checker can decide it |
| Fit for untrusted AI/stochastic search | Poor: the search itself would need proofs | Natural: generate, check, discard |
| Completeness | Every compiled program is covered | The checker may say "unknown" (Alive2 timeouts, KLEE-FP false positives) |

For an AI-first compiler the right composition is TV first, with **the checker itself verified** later, as CryptOpt did. (high)

### 3. Equality saturation and verified rewrite rules

**Core libraries and rule inference.**
- **egg** (POPL 2021) made e-graphs practical. It introduced amortised "rebuilding", which gives asymptotic speedups, and e-class analyses for plugging in domain facts ([egg](https://arxiv.org/abs/2004.03082)).
- **egglog** (PLDI 2023) merges Datalog with equality saturation. Among other things it re-implemented an EqSat-based FP term rewriter, which came out faster and simpler, with bugs fixed ([egglog](https://arxiv.org/abs/2304.04332)).
- **Ruler** infers rewrite rules with equality saturation. Its rulesets are 5.8× smaller and synthesis is 25× faster than a comparable CVC4-based tool, with no loss of proving power ([Ruler](https://arxiv.org/abs/2108.10436)).

**Tensor-level rewriting.**
- **TENSAT** applies all substitutions at once by equality saturation. It produced graphs up to 16% faster with about 48× less optimisation time ([TENSAT](https://arxiv.org/abs/2101.01332)).
- **Glenside** adds pure "access patterns" so that layout-aware, hardware-mapping rewrites are expressible. It automatically found transformations such as im2col ([Glenside](https://arxiv.org/abs/2105.09377)).
- **TASO** (SOSP 2019) automatically generates and verifies graph substitutions, with up to 3× speedups ([TASO](https://github.com/jiazhihao/TASO)).
- **TensorRight** (POPL 2025, Distinguished Paper) reduces *unbounded-rank* verification of XLA rewrites to finitely many bounded SMT obligations. The abstract reports 115 of 175 rules proven in full generality, against 18 for the closest bounded system ([TensorRight](https://github.com/ADAPT-uiuc/TensorRight)).
  - **[inference]** TensorRight reasons over idealised arithmetic, not IEEE rounding. That fits algebraic graph rewrites but not bit-exact kernels.
- **Mirage** (OSDI 2025) superoptimises across GPU kernel, block and thread levels using "μGraphs". It verifies equivalence with a *probabilistic* procedure that it says has strong theoretical guarantees, and reports up to 3.3× speedups ([Mirage](https://arxiv.org/abs/2405.05751)).
  - The repository's publication list includes an ITCS 2026 paper on identity testing for circuits with exponentiation gates ([Mirage repo](https://github.com/mirage-project/mirage)). **[inference]** That suggests randomized polynomial identity testing as the method, which again checks *algebraic*, not IEEE, equivalence.
- **Exo** (PLDI 2022; Exo 2 at ASPLOS 2025) is a user-schedulable kernel language. The performance engineer picks the rewrites and Exo ensures they preserve correctness; the authors claim it matches MKL/OpenBLAS/BLIS ([Exo](https://exo-lang.dev/)). The site does not say how Exo treats FP reassociation (**unverified**). It is the closest existing model of Mithril's "schedule never changes meaning" goal **[inference]**.

**Production: Cranelift.**
- **The aegraph.** Cranelift's mid-end uses an *acyclic* e-graph. Rewrites fire when a node is created, there is no parent-pointer recanonicalisation, and so it is **not full equality saturation**. Side-effecting instructions keep their original block order as a "skeleton", and extraction by scoped elaboration over the dominator tree subsumes GVN.
  - The RFC motivates the design by phase-ordering problems and verifiability.
  - The prototype reported −13% runtime on SpiderMonkey.wasm, at +1% compile time ([Cranelift e-graph RFC](https://github.com/bytecodealliance/rfcs/blob/main/accepted/cranelift-egraph.md)).
- **ISLE.** Rewrites and lowering are written in the ISLE DSL. About 27k lines of hand-written lowering logic migrated into it ([Fallin, ISLE](https://cfallin.org/blog/2023/01/20/cranelift-isle/)).
- **VeriISLE** (`cranelift/isle/veri`) is the in-tree SMT verifier for ISLE rule chains.
  - AArch64 specs are *derived from Arm's Machine Readable Specification in ASL* via the ASLp tool. x86-64 coverage is partial.
  - It uses cvc5 by default and Z3 for FP expansions. FP rewrites may produce different NaN bit patterns when the NaN comes from arithmetic.
  - A mid-end run checked 1,331 expansions and 5,134 type instantiations with no failures, in about 4 minutes on a 12-core laptop.
  - Papers: ASPLOS 2024, "Lightweight, Modular Verification for WebAssembly-to-Native Instruction Selection" (Crocus), and OOPSLA 2025, "Scaling Instruction-Selection Verification against Authoritative ISA Semantics" ([VeriISLE README](https://github.com/bytecodealliance/wasmtime/tree/main/cranelift/isle/veri)). (high)

**Lean-MLIR** (ITP 2024) mechanises an SSA-with-regions calculus in Lean. It is used to verify peephole rewrites, including LLVM bit-vector rewrites ([Bhat et al.](https://arxiv.org/abs/2407.03685)).

**[inference] FP caveat.** Almost no textbook algebraic identity holds bit-exactly in IEEE arithmetic: + and × are not associative or distributive ([Goldberg](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html), [KLEE-FP](http://srg.doc.ic.ac.uk/files/papers/kleefp-eurosys-11.pdf)). An FP e-graph for a bit-exact compiler must therefore be restricted to an audited list of exact rules: commutativity of + and ×, `x*1`, `-(-x)`, `x+x = 2*x`, select/mask canonicalisation, and lane permutation algebra. Reassociation rules belong behind an explicit tolerance mode.

### 4. Lean 4 as programming language and verification back end

**As a language.**
- Lean 4 is implemented in Lean. It compiles through C, manages memory by reference counting, and uses "functional but in-place" updates on unshared values. The authors report preliminary results competitive with ocamlopt and GHC ([Lean 4 system description](https://lean-lang.org/papers/lean4.pdf), [Counting Immutable Beans](https://arxiv.org/abs/1908.05647)).
- **FFI.** `@[extern]` and `@[export]` follow the platform C ABI, `Float` maps to `double`, and ownership is explicit (owned vs `@&` borrowed). The docs call the interface unstable and designed for internal use ([Lean FFI](https://lean-lang.org/doc/reference/latest/Run-Time-Code/Foreign-Function-Interface/)). **[inference]** There is no SIMD story; Lean is not a kernel language.

**Floats in the logic.**
- `Float` (binary64) and `Float32` (binary32) now have logical models as subtypes of `UInt64`/`UInt32`. Some operations reduce in the kernel; transcendental functions are opaque. There is one canonical NaN, and the model is tested empirically against the platform, valid only if FFI code leaves the FP environment alone.
- The model is "not intended" as a basis for an FP library and *has no lemmas*. FP equality is not a congruence: +0 = −0, but 1/+0 ≠ 1/−0 ([Lean Float docs](https://lean-lang.org/doc/reference/latest/Basic-Types/Floating-Point-Numbers/)). (high)
- **[inference]** Proving facts about IEEE kernels in Lean today means building that lemma library first, which is a substantial project.

**Scale and AI tooling.**
- Mathlib's stats page lists 137,938 definitions, 289,891 theorems and 772 contributors (undated page, read 2026-10-11) ([Mathlib stats](https://leanprover-community.github.io/mathlib_stats.html)).
- **LeanDojo** (NeurIPS 2023) extracts data from Lean, offers programmatic interaction and ships the ReProver retrieval prover, with a benchmark of 98,734 theorems ([LeanDojo](https://arxiv.org/abs/2306.15626)).
- **DeepSeek-Prover-V2** reaches 88.9% on MiniF2F-test and solves 49 of 658 PutnamBench problems ([DeepSeek-Prover-V2](https://arxiv.org/abs/2504.21801)).
- **`openai/math`** (October 2026) holds 719 manuscripts in 372 families from an unreleased internal model. About 42% of top-line results are formalised in Lean, with Comparator configs, and the scope is pure mathematics and mathematical physics ([openai/math](https://github.com/openai/math)).
  - Faithfulness disputes followed: one third-party comparison found Lean statements weaker than the paper's lemma ([secondary write-up](https://redreamality.com/blog/ai-math-verification-lean-faithfulness/)).

**Acceptance discipline.** The Lean reference describes a ladder of checks ([Validating Proofs](https://lean-lang.org/doc/reference/4.35.0-rc4/ValidatingProofs/)):
1. Kernel acceptance.
2. `#print axioms`.
3. `lean4checker --fresh`, which replays the `.olean` declarations.
4. **`comparator`**, the "gold standard". It builds the proof in a sandbox, exports it, replays it in the official kernel and/or the independent Rust checker `nanoda`, and checks that the proved statements match a *trusted challenge file*.

The docs explicitly name proof marketplaces and "unaligned AI" as the intended use. Native evaluation (`decide +native`, `bv_decide`) adds one axiom per native computation since 4.29, and the `trustCompiler` mechanism was removed in 4.35 (same source). (high)

Kernel bugs still happen. Issue #14576 (July 2026) let a file derive `False` with no axioms through a projection-name check missing from the kernel; it was fixed within days ([lean4#14576](https://github.com/leanprover/lean4/issues/14576)). **[inference]** Multi-kernel rechecking is not paranoia.

**Automation.**
- `bv_decide` calls the CaDiCaL SAT solver and returns a machine-checkable certificate.
- `grind` is SMT-inspired, combining congruence closure, E-matching and a linear-integer-arithmetic solver, and is not meant for combinatorial blow-ups ([Lean tactic reference](https://lean-lang.org/doc/reference/latest/Tactic-Proofs/Tactic-Reference/)). (high)

**Systems uses.**
- **LNSym** is an Armv8 machine-code symbolic simulator in Lean, with ELF-loading tests against AWS-LC ([LNSym](https://github.com/leanprover/LNSym)).
- **Aeneas** translates safe Rust to Lean (also HOL4, Coq, F*). Microsoft is using it with Lean to verify a Rust rewrite of SymCrypt, starting with ML-KEM (June 2025), with Eurydice compiling the verified Rust back to C ([Aeneas](https://github.com/AeneasVerif/aeneas), [MSR blog](https://www.microsoft.com/en-us/research/blog/rewriting-symcrypt-in-rust-to-modernize-microsofts-cryptographic-library/)).
- Sail's repository contains a Lean back-end package (`sail_lean_backend.opam`) ([Sail](https://github.com/rems-project/sail)). Its coverage is **unverified**.

### 5. SMT: bit-vectors vs floating point

**The SMT-LIB FP theory.**
- Binary IEEE 754-2008 formats with `fp.add/sub/mul/div/fma/sqrt/rem/roundToIntegral` and five rounding modes.
- **Exactly one NaN per sort**, so payloads are unmodelled.
- `fp.min`/`fp.max` semantics are deferred to a reference paper.
- Conversions to bit-vectors are unspecified for NaN, infinity and out-of-range values.
- **No exp, log or trigonometric functions** ([SMT-LIB FP](https://smt-lib.org/theories-FloatingPoint.shtml)). (high)
- **[inference]** Softmax, SiLU, RoPE and RMSNorm's `sqrtf` reciprocal cannot be fully modelled in SMT. At best they become uninterpreted functions.

**Solvers.**
- Bitwuzla supports bit-vectors, FP, arrays and UF. It won a CAV 2023 Distinguished Paper award and has CAV 2024 work on scalable bit-blasting with abstractions ([Bitwuzla](https://bitwuzla.github.io/)).
- cvc5 emits proofs in its own CPC format and in Alethe ([cvc5 proofs](https://cvc5.github.io/docs/latest/proofs/proofs.html)). Its FP proof coverage is **unverified**.

**Practice.**
- Alive2 encodes FP in the FPA theory and is bounded by timeouts ([Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)).
- Strata found precise FP modelling too slow and used UF instead ([Strata](https://stefanheule.com/papers/pldi16-strata.pdf)).
- **[inference]** Bit-blasting FP multiply, divide and sqrt yields multiplier-sized circuits per operation. A 4,096-element dot product in the FPA theory is hopeless, while the same check by structural matching is trivial.

**KLEE-FP (EuroSys 2011)** is the key precedent for "FP equivalence equals expression matching".
- **Approach.** It lowers SSE intrinsics to scalar integer and FP primitives, then applies canonicalisation rewrites (category analysis, identity reduction, bitwise folding, concat merging). FP subtrees are compared **syntactically, as uninterpreted binary functions**, and integer subtrees go to STP.
- **Rationale.** Its stated insight is that two FP values computed from the same inputs are reliably equal essentially only when built by the same operations.
- **Results on OpenCV.** Of 51 SSE kernels it could crosscheck, 41 were proven equivalent up to a bounded image size and 10 had real mismatches, each found in under 30 s. The mismatches were associativity/distributivity errors and min/max applied in a different order (MINPS/MAXPS are non-commutative and non-associative with NaN). Three benchmarks gave false positives, caused by over-approximating FP-to-int conversions.
- **Guarantee.** No false negatives: "equivalent" is guaranteed ([KLEE-FP](http://srg.doc.ic.ac.uk/files/papers/kleefp-eurosys-11.pdf)). (high)

**x86 detail that matters.** If either operand of MAXPS is NaN, or both are zeros of any sign, it returns the **second** operand ([MAXPS](https://www.felixcloutier.com/x86/maxps)). So `max(+0,−0)` and `max(−0,+0)` differ in the sign bit, and operand order is semantic.

### 6. Floating-point error analysis and certified tolerance bounds

**Basic facts.**
- IEEE basic operations are exactly rounded: the result is computed exactly, then rounded ([Goldberg](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html)).
- Recursive summation has worst-case error growth O(εn) (RMS O(ε√n) under random rounding); pairwise summation has O(ε log n), with a rigorous bound of `ε·log2(n)/(1−ε·log2(n))·Σ|x_i|` ([Wikipedia: Pairwise summation](https://en.wikipedia.org/wiki/Pairwise_summation)).
- **[inference]** For any fixed summation order, the classical a-priori bound `|fl(Σx_i y_i) − Σx_i y_i| ≤ γ_k Σ|x_i y_i|` holds, with γ_k = k·u/(1−k·u) and k the longest accumulation chain. It is closed-form and costs O(n) to evaluate at runtime. Two realisations that each satisfy it differ by at most the sum of the two bounds. This makes "tolerance equivalence" of reassociated dot products cheap to certify, both a priori and a posteriori, but loose.

**Tools.**
- **FPTaylor** (TOPLAS 2018): rigorous round-off bounds via symbolic Taylor expansions plus global optimisation backends. It includes HOL Light procedures for formally checking its results ([FPTaylor](https://github.com/soarlab/FPTaylor)).
- **Satire**: first-order, rigorous worst-case bounds for *straight-line* programs, with incremental analysis, abstraction and parallel optimiser calls. Its README example bounds a 1,024-element reduction at about 1.25e-12 absolute error in roughly 30 s ([Satire](https://github.com/arnabd88/Satire)). The headline scale figures in its SC20 paper are **unverified** here.
- **Daisy** (TACAS 2018): interval/affine range and error analysis with optional Z3/dReal, reading Scala, C and FPCore ([Daisy](https://github.com/malyzajko/daisy)).
- **Gappa**: proves properties of FP and fixed-point programs, usable as a Rocq tactic and as a Why3 back end ([Gappa](https://gappa.gitlabpages.inria.fr/)).
- **Herbie** *improves* accuracy by rewriting and measures error by sampling. It is not a certifier ([Herbie](https://herbie.uwplse.org/)).
- **Lee, Sharma and Aiken** (POPL 2018) automatically proved the error bounds of Intel's math.h implementations by reducing the problem to optimisation problems solved by computer algebra ([paper](https://wonyeol.github.io/papers/2018-popl.pdf)). An earlier PLDI 2016 paper verified FP bit-manipulation code ([Lee's page](https://wonyeol.github.io/)).
- **CORE-MATH** provides correctly rounded binary32/binary64 (and other format) functions. glibc 2.42 integrated about 30 binary32 functions and glibc 2.43 seven binary64 ones. Binary32 univariate functions are checked exhaustively ([CORE-MATH](https://core-math.gitlabpages.inria.fr/)).
  - **[inference]** Correct rounding is the only route to *cross-platform* bit-identical `expf`/`sinf`/`cosf`. Otherwise each platform libm is its own uninterpreted function.

**[inference] Where tolerance certificates fail.** Error bounds propagate through continuous operations. They do **not** propagate through discontinuous ones:
- top-k / argmax routing;
- `nearbyintf` activation quantisation;
- comparisons and thresholds;
- NaN-producing domain errors.

A perturbation smaller than any bound can change which experts run. Any end-to-end tolerance claim for MoE inference therefore needs either bit-exactness through those points, or a **runtime margin certificate**: for example, the gap between the k-th and (k+1)-th router score exceeds twice the certified error bound at that point. (high for the problem; medium for the remedy.)

### 7. Formal ISA semantics for SIMD

**Arm.**
- Arm specifies its architecture in ASL. Sail's Arm-A models (Armv9.4-A, v9.3-A, v8.5-A) are *translated* from Arm's ASL. Sail also has the official RISC-V model and back ends for C, OCaml, Coq, Isabelle and HOL4 ([Sail](https://github.com/rems-project/sail)).
- VeriISLE distils AArch64 instruction specs from Arm's Machine Readable Specification via ASLp ([VeriISLE](https://github.com/bytecodealliance/wasmtime/tree/main/cranelift/isle/veri)). (high)

**x86.**
- Sail lists two x86 models: a substantial part of x86 translated from the ACL2 X86isa model, and a handwritten legacy fragment ([Sail](https://github.com/rems-project/sail)). Their AVX-512 coverage is **unverified**.
- The K x86-64 semantics covers all non-deprecated sequential user-level Haswell instructions: 3,155 variants across 774 mnemonics. It was validated by co-simulation against hardware and the GCC torture tests ([K x86-64](https://github.com/kframework/X86-64-semantics)); the PLDI 2019 paper is listed in the [STOKE README](https://github.com/StanfordPL/stoke).
  - **[inference]** Haswell predates AVX-512, so AVX-512 and VNNI are not covered.
- Strata learned 1,795 variants, with FP as UF ([Strata](https://stefanheule.com/papers/pldi16-strata.pdf)).
- Intel's SDM pseudocode is the de facto source. For example, VPDPBUSD sums four u8×s8 products into an int32 lane with plain addition and no clamp, while PMADDUBSW saturates its pair sums to int16 ([VPDPBUSD](https://www.felixcloutier.com/x86/vpdpbusd), [PMADDUBSW](https://www.felixcloutier.com/x86/pmaddubsw)).
- **[inference]** I found no Intel-published, machine-readable *formal* x86 semantics comparable to Arm's ASL. That absence is what forces projects to re-derive x86 semantics by hand, by synthesis (Strata) or by translation (ACL2 → Sail).

**Implication.** For Mithril on Zen 5, the honest plan is a hand-written, executable semantics of the *emitted subset* (probably fewer than 200 AVX-512/AVX2/BMI2 instructions **[inference]**), validated K-style by co-simulation on the target CPU, with Strata-style SMT cross-checks for the integer ones.

### 8. Refinement types and systems-code verifiers

- **Flux** brings liquid (refinement) types to Rust (Lehmann, Geller, Vazou, Jhala). Compared with Prusti it roughly halves specification lines, cuts verification time by about an order of magnitude, and removes annotation overhead (up to 24% of code size with Prusti) on its benchmarks ([Flux paper](https://arxiv.org/abs/2207.04034), [Flux site](https://flux-rs.github.io/flux/)).
  - **[inference]** Refinements suit index bounds, alignment and integer ranges, which are exactly Hearth's quantisation side conditions.
- **Verus** verifies Rust with solvers (OOPSLA 2023, "linear ghost types"; SOSP 2024).
  - It underlies many verified systems: Anvil and VeriSMo (OSDI 2024 Best Papers), CortenMM (SOSP 2025 Best Paper) and others.
  - It has a cluster of **LLM proof-generation** work: AutoVerus, AlphaVerus, ExVerus, VeruSAGE, plus a "Benchmark for Vericoding" ([Verus publications](https://verus-lang.github.io/verus/publications-and-projects/)).
  - AutoVerus found correct proofs for more than 90% of 150 non-trivial tasks ([AutoVerus](https://arxiv.org/abs/2409.13082)). (high)
- **Dafny** is verification-aware and compiles to C#, Java, JavaScript, Go and Python ([Dafny](https://dafny.org/)).
- **Creusot** is a deductive verifier for Rust built on Why3/Coma; it was used to build CreuSAT ([Creusot](https://github.com/creusot-rs/creusot)).
- **Aeneas**: see §4.
- **Vale** produces verified assembly for x86, x64 and ARM on Dafny/F*, with current work in HACL*; papers at USENIX Security 2017, POPL 2019 and VSTTE 2020 ([Vale](https://github.com/project-everest/vale)).
  - **[inference]** Vale is the strongest precedent for *verified hand-scheduled SIMD assembly*, but it targets integer and crypto code.
- **[inference]** None of these offers first-class, automated IEEE-FP reasoning comparable to its integer support. FP kernels remain the gap.

### 9. Proof-carrying code and its modern descendants

**The original idea.** Necula and Lee's PCC (1996) ships machine code with a proof of a host-defined safety policy, and the loader checks the proof quickly, then runs the code without runtime checks ([Wikipedia: PCC](https://en.wikipedia.org/wiki/Proof-carrying_code)).

**Modern descendants [inference on the classification; facts cited]:**
- **eBPF.** The verifier checks untrusted programs before loading by simulating every path with abstract register state: types, signed/unsigned ranges and "tnum" known-bit masks, with state pruning ([kernel docs](https://docs.kernel.org/bpf/verifier.html)). This is PCC with the proof *recomputed* by the consumer.
- **Lean's comparator.** A trusted statement, an untrusted proof and an independent kernel check, designed for AI-produced proofs ([Validating Proofs](https://lean-lang.org/doc/reference/4.35.0-rc4/ValidatingProofs/)).
- **Certificate-emitting solvers.** `bv_decide` (SAT certificate) and cvc5 (CPC/Alethe) ([Lean](https://lean-lang.org/doc/reference/latest/Tactic-Proofs/Tactic-Reference/), [cvc5](https://cvc5.github.io/docs/latest/proofs/proofs.html)).
- **CakeML's verified checker** for FP error-bound certificates ([CakeML](https://cakeml.org/)).

**The common architecture: an untrusted, clever producer plus a small, trusted, fast checker.** That is what an AI-first compiler should be. (high)

### 10. The explicit question: given a reference meaning and a scheduled/vectorised realisation, what is decidable and cheap?

Assumptions: kernels with bounded or known shapes, IEEE binary32, round-to-nearest-even.

| Check | Decidable? | Cheap? | Method | Notes |
|---|---|---|---|---|
| **Bit-exact, FP op order fixed, straight-line (shape fixed)** | Yes. The domain is finite, but brute-force bit-blasting is intractable at scale | **Yes**: near-linear | Symbolically evaluate both, hash-cons the FP DAGs, apply an audited list of IEEE-exact rewrites, compare syntactically; integer subterms go to SMT | Sound, incomplete (false "differs" only). This is the KLEE-FP / Strata-UF approach ([KLEE-FP](http://srg.doc.ic.ac.uk/files/papers/kleefp-eurosys-11.pdf), [Strata](https://stefanheule.com/papers/pldi16-strata.pdf)). **[inference]** Cost is linear in the unrolled DAG size |
| **Same, but with parametric trip counts (n symbolic)** | Undecidable in general (Rice) | Yes **if** both loops are lockstep with matching lane structure | Simulation relation per iteration (Necula-style TV); induction proved once | **[inference]** Hearth's `sum16`/`dot16` is *defined* in 16-lane form, so AVX2 (2×8) and AVX-512 (1×16) bodies align lane-for-lane. An ×4-unrolled 64-accumulator version is *not* equivalent and must be rejected |
| **Integer/bit-vector parts** (unpacking, int8 dot, address arithmetic, saturation, masks) | Yes (QF_BV) | Usually yes; multiplier-heavy, wide queries are the hard case **[inference]** | SMT (Bitwuzla/cvc5/Z3) or Lean `bv_decide` with certificates | Range side conditions (no saturation, exact int→float) are the typical content |
| **FP with reassociation/FMA/different summation trees** | Bit-exact equivalence is simply *false* in general | — | Not checkable as equivalence | KLEE-FP's OpenCV mismatches are exactly these |
| **Tolerance-bounded equivalence, continuous straight-line code** | Yes, given input ranges (bounds are computable over-approximations) | Closed-form bounds for dots/sums are cheap; FPTaylor-class tools are moderate; large kernels get expensive or loose | γ_k bounds, FPTaylor, Satire, Daisy, Gappa | Sound but conservative; needs range facts (from a type system or runtime) |
| **Transcendentals (exp, sin, cos, sqrt, 1/x)** | Bit-exact: yes if both sides call the *same* implementation (treat as UF) | Yes | UF matching | Tolerance needs libm error bounds (Lee et al. 2018; CORE-MATH correct rounding) |
| **Discontinuities (top-k, argmax, nearbyint, comparisons)** | Bit-exact: yes via matching | Yes | UF/structural | Tolerance does **not** propagate; needs runtime margin certificates **[inference]** |
| **Whole-model semantic properties** ("bounded loss divergence", robustness) | NN verification is NP-complete even for ReLU ([Reluplex](https://arxiv.org/abs/1702.01135)); adding exp makes the logic of open decidability ([Tarski exp problem](https://en.wikipedia.org/wiki/Tarski%27s_exponential_function_problem)), and with sin it is undecidable ([Richardson](https://en.wikipedia.org/wiki/Richardson%27s_theorem)) | No | — | Reluplex verified 300-ReLU ACAS Xu networks, many orders of magnitude below an LLM |
| **Performance** ("faster", "IPC 3.2") | Not a semantic property | — | Measurement (Hearth INV-HONEST) | Cost models guide search but prove nothing |

**Pitfalls the structural checker must model exactly [inference unless cited]:**
- **Signed zero.** `0.0f + (−0.0f) = +0.0f`, so "start the accumulator from element 0" is *not* equivalent to "start from 0.0f" ([Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf) bug #2 is this class).
- **MAXPS/MINPS operand order**, for NaN and for ±0 ([MAXPS](https://www.felixcloutier.com/x86/maxps); [KLEE-FP](http://srg.doc.ic.ac.uk/files/papers/kleefp-eurosys-11.pdf)).
- **NaN payloads.** These need canonicalisation, which Hearth already does. SMT-LIB has a single NaN, and VeriISLE allows differing arithmetic-NaN bits.
- **FP environment.** FTZ/DAZ and rounding mode belong to the semantics of every FP operation. Lean's FP model is valid only if FFI code leaves the environment unchanged ([Lean Float docs](https://lean-lang.org/doc/reference/latest/Basic-Types/Floating-Point-Numbers/)).
- **Contraction.** Compiler FMA contraction (`-ffp-contract`), x87 extended precision and `-ffast-math` silently change the DAG, so check the *emitted* machine code, not the source.
- **Horizontal reductions.** Lane shuffles (`vextractf*`, `vperm*`, `hadd`) must be symbolically evaluated into the lane-tree they implement before matching.

**Bottom line (high confidence).** For Hearth-class kernels, **bit-exact equivalence under a canonical order is decidable and cheap**: structural matching plus BV SMT for side conditions. Tolerance equivalence is cheap only for continuous pieces with known ranges. Nothing semantic about learning dynamics or "loss divergence" is checkable by SMT.

---

## Implications for Mithril

1. **Make the canonical FP order a first-class semantic object, not a coding convention [inference].** A reduction in Mithril's meaning layer should carry its association structure (lanes = 16, tree = pairwise over lanes, contraction = off, NaN = canonical, FP environment = RNE/no-FTZ). Schedules (vectorisation, tiling, threading, prefetch) may change *where and when* operations run, never the DAG. Bit-exactness then becomes a type-level guarantee checked by a matcher, rather than a test outcome.

2. **Use a three-tier acceptance checker as the compiler's trusted core:**
   - **T1, the structural FP matcher.** KLEE-FP-style symbolic evaluation of the emitted x86 against the meaning, with an audited list of IEEE-exact rewrites. It emits a *matching witness* certificate.
   - **T2, BV obligations.** Integer ranges, saturation freedom, exact int→float, address/alignment and masks, discharged by SMT or `bv_decide`, keeping the solver certificates.
   - **T3, opt-in tolerance mode.** Certified error bounds (closed-form γ_k, or FPTaylor/Satire-class analysis) plus *runtime margin checks* at every discontinuity. T3 output is labelled non-lossless by construction, mirroring Hearth's INV-LOSSLESS-DEFAULT.

3. **Prefer translation validation to a verified compiler; later, verify the checker.** All search (LLM, MCTS, e-graph extraction, stochastic) stays untrusted. Only T1/T2 are trusted, and they are small enough to mechanise in Lean eventually, as CryptOpt did in Coq ([CryptOpt](https://arxiv.org/abs/2211.10665)).

4. **Reward only checked candidates.** In the DGM-style self-improvement loop, fitness is *checker-accepted* and then measured speedup on pinned hardware. Test-only rewards are gameable ([robust-kbench](https://arxiv.org/abs/2509.14279)), and test-only "correctness" overstates reality ([SuperCoder](https://arxiv.org/abs/2505.11480), [LLM-Vectorizer](https://arxiv.org/abs/2406.04693)). **[inference]** Unknown or timeout from the checker counts as rejection, never as acceptance.

5. **Search over instructions with semantics, not raw bytes [inference].** Encoding (byte lengths, decoder alignment) is a final, deterministic, separately validated step. Superoptimisation operates on an instruction-level SSA whose every opcode has an executable semantics in the T1/T2 model.

6. **Own an x86 SIMD semantics for the emitted subset [inference].** Write it once, in a form that can be exported to SMT and, later, Lean. Validate it by co-simulation on Zen 5 hardware, as K did for Haswell ([K x86-64](https://github.com/kframework/X86-64-semantics)), with Strata-style cross-checks. Pull Arm semantics from ASL via Sail/ASLp when the macOS arm64 back end matters ([VeriISLE](https://github.com/bytecodealliance/wasmtime/tree/main/cranelift/isle/veri)).

7. **Use an e-graph for the rewrite space, with verified rules.**
   - Use egglog or an aegraph-style engine; the aegraph design shows that full saturation is not required in production ([Cranelift RFC](https://github.com/bytecodealliance/rfcs/blob/main/accepted/cranelift-egraph.md)).
   - Every rule carries a proof obligation, checked VeriISLE-style ([VeriISLE](https://github.com/bytecodealliance/wasmtime/tree/main/cranelift/isle/veri)).
   - Use Ruler-style inference to propose rules ([Ruler](https://arxiv.org/abs/2108.10436)).
   - FP rules come in two sets, *exact* and *tolerance-only*, and the tolerance set is unreachable in default builds.

8. **Use Lean as the meta-level and proof back end, and the comparator pattern for AI-generated proofs.**
   - Use Lean for: the language's meta-theory; the soundness of T1's rewrite list and lockstep-loop rule; and per-kernel proofs that need induction beyond T1/T2.
   - Accept AI-written Lean proofs only through a comparator-style gate: trusted statement file, sandboxed build, multi-kernel replay ([Validating Proofs](https://lean-lang.org/doc/reference/4.35.0-rc4/ValidatingProofs/)).
   - **[inference]** Budget for building an IEEE lemma library on Lean's Float32 model; none exists ([Lean Float docs](https://lean-lang.org/doc/reference/latest/Basic-Types/Floating-Point-Numbers/)).

9. **Ship proof-carrying kernels [inference].** Every compiled kernel artifact carries its T1 witness, T2 certificates and (if T3) error-bound certificate. A loader or verifier agent rechecks them, in the PCC and eBPF spirit. This matches Hearth's governance model of independent verifier agents.

10. **Refinement types for the integer layer.** Flux-style index refinements on buffer extents, quantisation ranges and alignment would turn Hearth's hand-written bounds comments into checked types ([Flux](https://arxiv.org/abs/2207.04034)) **[inference]**.

---

## Implications for Hearth

1. **Hearth already has a reference semantics, and it is close to formal [inference].** `docs/NUMERICS.md` fixes `sum16`/`dot16` lane structure, the pairwise lane tree, no FMA, the canonical quiet NaN `0x7fc00000`, group-order accumulation and rank-order expert summation ([NUMERICS.md](https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md)). INV-DET-3 is currently *tested* (`test_isa_identity`) ([INVARIANTS.md](https://github.com/pierce-lonergan/hearth/blob/main/governance/INVARIANTS.md)). It could be *proved per build*: lift the scalar, AVX2 and AVX-512 kernels to symbolic DAGs and match them. That is the KLEE-FP approach, and for Hearth's fixed block size of 64 the shapes are small.

2. **Hearth's comments already contain the BV proof obligations; mechanise them [inference].** `quant_avx2.c` argues in comments that:
   - Q4 `maddubs` pair sums are ≤ 2·15·127 = 3,810 (low+high ≤ 7,620), so the int16 accumulation never saturates;
   - Q8 sign-trick pairs are ≤ 2·128·127 = 32,512 < 32,767;
   - activations must lie in [−127, 127].

   `quant_avx512.c` relies on a VNNI bias correction (unsigned weights, corrected by bias·Σx) ([quant_avx2.c](https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant_avx2.c), [quant_avx512.c](https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant_avx512.c)). Each is a sub-second QF_BV query **[inference]**, and PMADDUBSW's saturation ([PMADDUBSW](https://www.felixcloutier.com/x86/pmaddubsw)) makes these conditions load-bearing. A further one: Q8 `|isum| ≤ 64·127·127 = 1,032,256 < 2^24`, so `(float)isum` is exact; Q4 gives ≤ 65,024. That is a T2 fact the canonical order silently depends on.

3. **NaN and max semantics.** The AVX kernels use `_mm256_max_ps(abs(v), m)` with "NaN in the first operand is skipped", and an ordered-compare mask to zero NaNs before clamping (same files). MAXPS returns the second operand on NaN or ±0 ([MAXPS](https://www.felixcloutier.com/x86/maxps)), so the scalar reference must use the *same* operand convention for bit-identity on NaN-containing inputs. A T1 matcher with MAXPS-exact semantics would catch a drift here automatically **[inference]**.

4. **Cross-platform `expf`/`sinf`/`cosf` is an open hole [inference].** NUMERICS.md uses the *platform* libm, so Windows, Linux and macOS logits can differ bit-wise even with identical kernels. If cross-OS bit-identity is wanted (CI runs on all three), vendor correctly rounded C11 implementations in the style of CORE-MATH (MIT-licensed). These are deterministic by construction and binary32-univariate ones are exhaustively checked ([CORE-MATH](https://core-math.gitlabpages.inria.fr/)). That stays within INV-DEP, which allows C11 plus OS APIs.

5. **Tolerance invariants are tested, not certified.** INV-NUM-1 (logit tolerance) and the MLA absorbed-form note ("within float tolerance, not bit-exactly") are empirical ([NUMERICS.md](https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md)). Per-head MLA absorption is continuous straight-line code: a candidate for an FPTaylor/Satire-class certified bound given activation ranges **[inference]**.

6. **INV-NUM-2 (routing equality) is a discontinuity [inference].** Routing equality between the engine and the reference cannot follow from any logit tolerance. Add a *margin log* (gap between the k-th and (k+1)-th selection score vs a computed error bound) so that legitimate reference/engine divergences are distinguishable from bugs, and so that a future lossy mode can certify which tokens are unaffected.

7. **External validation of the batch-invariance design.** Thinking Machines (September 2025) traced LLM nondeterminism to missing batch invariance, not concurrency. Batch-invariant kernels made 1,000 temperature-0 Qwen3-235B completions identical, at about a 20% matmul cost on GPU ([Thinking Machines](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)). That is Hearth's INV-DET-2, arrived at independently. (high)

---

## Where the seed discussion is right or wrong

- **B8: shape right, mechanism wrong for FP (high confidence).**
  - *Right:* the combination of untrusted search and an equivalence check exists. CryptOpt (randomised x86 search plus a Coq-verified checker), STOKE, AlphaDev, SuperCoder and Alive2 all show parts of it ([CryptOpt](https://arxiv.org/abs/2211.10665), [STOKE](https://arxiv.org/abs/1211.0557), [AlphaDev](https://deepmind.google/discover/blog/alphadev-discovers-faster-sorting-algorithms/), [SuperCoder](https://arxiv.org/abs/2505.11480), [Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)).
  - *Wrong 1:* Alive2 validates LLVM IR, is bounded (loops unrolled) and is not an x86 byte-sequence checker. Back-end validation needs an x86 semantics, which exists only partially for AVX-512 (see §7).
  - *Wrong 2:* "SMT (Z3 / Alive2-style) equivalence" on FP kernels is the wrong primary tool. FP-theory SMT is slow and lacks transcendentals ([SMT-LIB FP](https://smt-lib.org/theories-FloatingPoint.shtml), [Strata](https://stefanheule.com/papers/pldi16-strata.pdf)). More fundamentally, a superoptimiser that reassociates FP produces code that is **not equivalent**, so a correct checker must reject it. The workable pipeline is canonical order, structural matching, BV SMT for integer parts and explicit tolerance certificates.
  - *Wrong 3:* searching "x86 byte sequences" conflates encoding with semantics.
  - *Wrong 4:* direct ELF emission is fine but enlarges the trusted base unless the final binary is what gets validated. Csmith's CompCert results show bugs migrating to the unverified periphery ([Csmith](https://users.cs.utah.edu/~regehr/papers/pldi11-preprint.pdf)).
- **B12 (SMT validation in the loop): right**, provided "validation" means proof, not tests. LLM-Vectorizer shows how much of LLM output survives real verification: 38.2% ([LLM-Vectorizer](https://arxiv.org/abs/2406.04693)).
- **F1 (context for F2/F6): roughly right as of October 2026.** `openai/math` exists: 719 manuscripts (722 at first release, per a secondary source) in 372 families, about 42% formalised in Lean, with Comparator configs ([openai/math](https://github.com/openai/math), [secondary](https://redreamality.com/blog/ai-math-verification-lean-faithfulness/)). But **Comparator is Lean's own generic checker** (`lake comparator`), not an OpenAI harness ([Validating Proofs](https://lean-lang.org/doc/reference/4.35.0-rc4/ValidatingProofs/)).
- **F2: category error (high).** The repository is pure mathematics; it contains no x86, SIMD or tensor semantics ([openai/math](https://github.com/openai/math)). Comparator checks only that a kernel-accepted proof proves the *same Lean statement* as a trusted challenge file. To "verify optimised x86 against tensor-op semantics" in Lean you would first need:
  1. a Lean x86-64/AVX-512 semantics (none complete is public; LNSym covers Armv8 ([LNSym](https://github.com/leanprover/LNSym)));
  2. an IEEE-float lemma library on Lean's Float32 model, which the docs say does not exist ([Lean Float docs](https://lean-lang.org/doc/reference/latest/Basic-Types/Floating-Point-Numbers/));
  3. per-kernel proofs.

  *Salvageable idea:* use the **comparator pattern** (trusted statement, untrusted AI proof, sandboxed multi-kernel replay) as Mithril's acceptance gate for AI-generated proofs.
- **F6: wrong framing (high).** Lean's own state-of-the-art automation *uses* solvers. `bv_decide` runs CaDiCaL and checks a certificate, and `grind` is SMT-inspired ([Lean tactic reference](https://lean-lang.org/doc/reference/latest/Tactic-Proofs/Tactic-Reference/)). The right synthesis is solvers as untrusted oracles plus certificate checking in a small kernel. Lean is not a replacement: decidable fragments (QF_BV) stay push-button in SMT, while Lean adds induction, meta-theory and an independent check. Lean's kernel also had a soundness bug as recently as July 2026 ([lean4#14576](https://github.com/leanprover/lean4/issues/14576)), so "Lean, therefore certain" is itself an overclaim.
- **I4: infeasible as stated (high).** An SMT solver cannot certify that an AST edit to a loss, sparsity or routing program "guarantees bounded loss divergence":
  - verifying even simple properties of ReLU networks is NP-complete, and the Reluplex-era state of the art handled networks of hundreds of ReLUs ([Reluplex](https://arxiv.org/abs/1702.01135));
  - softmax and cross-entropy bring in exp/log, beyond SMT-LIB and into logics of open or undecidable status ([SMT-LIB FP](https://smt-lib.org/theories-FloatingPoint.shtml), [Tarski exp](https://en.wikipedia.org/wiki/Tarski%27s_exponential_function_problem), [Richardson](https://en.wikipedia.org/wiki/Richardson%27s_theorem));
  - "loss divergence" over a data distribution is a statistical property, not a logical one **[inference]**.

  *What is checkable:* type and shape safety, determinism, bit-exact preservation of inference outputs under refactoring, certified error bounds on straight-line numeric pieces, and held-out empirical evaluation with honest labelling (Hearth INV-HONEST).
- **B6 (vectorisation "mathematically guaranteed"): partially relevant.** Guaranteeing that code *can* be vectorised is a compiler design property. Guaranteeing that vector code *equals* scalar code requires a fixed canonical order (§10), which B6 does not mention **[inference]**.
- **G1: mostly fine, with one correction.** `google/souper` and `AliveToolkit/alive2` are live research tools ([Souper](https://arxiv.org/abs/1711.04422), [Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)). `StanfordPL/stoke` is explicitly unmaintained ([STOKE README](https://github.com/StanfordPL/stoke)).
- **H3 (open-source the SMT/Lean proofs): right**, and cheap if proofs are certificates shipped with artifacts (Implications §9) **[inference]**.

---

## Open questions

1. How large is the audited IEEE-exact rewrite list needed for T1 to accept Hearth's AVX2/AVX-512 kernels with zero false positives? KLEE-FP needed "a relatively small number" for OpenCV ([KLEE-FP](http://srg.doc.ic.ac.uk/files/papers/kleefp-eurosys-11.pdf)). Hearth's horizontal-reduction shuffles are the likely pain point.
2. Does Sail's ACL2-derived x86 model cover AVX-512F/BW/VL/VNNI FP and integer instructions well enough to reuse? **Unverified**: the README does not say ([Sail](https://github.com/rems-project/sail)).
3. What certificate format should T1 emit, so that a Lean-verified checker can re-check it in linear time?
4. Can LLM provers (DeepSeek-Prover-class, AutoVerus-class) produce lockstep-loop simulation proofs for parametric-n kernels at a useful rate? Current evidence covers mathematics and Verus tasks, not FP kernels ([DeepSeek-Prover-V2](https://arxiv.org/abs/2504.21801), [AutoVerus](https://arxiv.org/abs/2409.13082)).
5. How tight are certified bounds (γ_k a priori vs Satire/FPTaylor) for Hearth's MLA absorption and RMSNorm at real activation ranges? Are they tight enough to make runtime margin certificates for routing useful rather than always firing?
6. Does Hearth want *cross-OS* bit-identity? If so, which libm path (vendored correctly rounded functions vs per-OS goldens)?
7. What are Satire's actual scalability limits (operator counts, timings) from its SC20 paper? **Unverified** here.
8. How should a tolerance mode (T3) interact with INV-LOSSLESS-DEFAULT and the golden-test regime? Is a certified bound sufficient evidence for an opt-in lossy path, or must quality also be measured empirically?
9. Should Mithril's T2 obligations be expressed as refinement types (Flux-style) at source level, as post-hoc SMT queries on lowered code, or both? The trade-off is diagnostics quality vs trusted-base size.

---

## Sources

Hearth (local clone, read-only):
- https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md
- https://github.com/pierce-lonergan/hearth/blob/main/governance/INVARIANTS.md
- https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant_avx2.c
- https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant_avx512.c

Superoptimisation and LLM optimisation:
- https://en.wikipedia.org/wiki/Superoptimization
- https://arxiv.org/abs/1211.0557
- https://github.com/StanfordPL/stoke
- https://stefanheule.com/papers/pldi16-strata.pdf
- https://arxiv.org/abs/1711.04422
- https://arxiv.org/abs/2306.00229
- https://arxiv.org/abs/2211.10665
- https://deepmind.google/discover/blog/alphadev-discovers-faster-sorting-algorithms/
- https://arxiv.org/abs/2407.02524
- https://arxiv.org/abs/2505.11480
- https://arxiv.org/abs/2406.04693
- https://arxiv.org/abs/2502.10517
- https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- https://arxiv.org/abs/2509.14279
- https://sakana.ai/ai-cuda-engineer/

Translation validation and verified compilers:
- https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf
- https://doi.org/10.1145/349299.349314
- https://compcert.org/
- https://users.cs.utah.edu/~regehr/papers/pldi11-preprint.pdf
- https://cakeml.org/
- https://github.com/vellvm/vellvm
- https://github.com/CertiCoq/certicoq

Equality saturation and rule verification:
- https://arxiv.org/abs/2004.03082
- https://arxiv.org/abs/2304.04332
- https://arxiv.org/abs/2108.10436
- https://arxiv.org/abs/2101.01332
- https://arxiv.org/abs/2105.09377
- https://github.com/jiazhihao/TASO
- https://github.com/ADAPT-uiuc/TensorRight
- https://arxiv.org/abs/2405.05751
- https://github.com/mirage-project/mirage
- https://github.com/bytecodealliance/rfcs/blob/main/accepted/cranelift-egraph.md
- https://cfallin.org/blog/2023/01/20/cranelift-isle/
- https://github.com/bytecodealliance/wasmtime/tree/main/cranelift/isle/veri
- https://arxiv.org/abs/2407.03685
- https://exo-lang.dev/

Lean 4 and AI theorem proving:
- https://lean-lang.org/papers/lean4.pdf
- https://arxiv.org/abs/1908.05647
- https://lean-lang.org/doc/reference/latest/Run-Time-Code/Foreign-Function-Interface/
- https://lean-lang.org/doc/reference/latest/Basic-Types/Floating-Point-Numbers/
- https://lean-lang.org/doc/reference/latest/Tactic-Proofs/Tactic-Reference/
- https://lean-lang.org/doc/reference/4.35.0-rc4/ValidatingProofs/
- https://github.com/leanprover/lean4/issues/14576
- https://leanprover-community.github.io/mathlib_stats.html
- https://arxiv.org/abs/2306.15626
- https://arxiv.org/abs/2504.21801
- https://github.com/openai/math
- https://redreamality.com/blog/ai-math-verification-lean-faithfulness/ (secondary)
- https://github.com/leanprover/LNSym

SMT and FP semantics:
- https://smt-lib.org/theories-FloatingPoint.shtml
- https://bitwuzla.github.io/
- https://cvc5.github.io/docs/latest/proofs/proofs.html
- http://srg.doc.ic.ac.uk/files/papers/kleefp-eurosys-11.pdf
- https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html

FP error analysis:
- https://en.wikipedia.org/wiki/Pairwise_summation
- https://github.com/soarlab/FPTaylor
- https://github.com/arnabd88/Satire
- https://github.com/malyzajko/daisy
- https://gappa.gitlabpages.inria.fr/
- https://herbie.uwplse.org/
- https://wonyeol.github.io/papers/2018-popl.pdf
- https://wonyeol.github.io/
- https://core-math.gitlabpages.inria.fr/

ISA semantics:
- https://github.com/rems-project/sail
- https://github.com/kframework/X86-64-semantics
- https://www.felixcloutier.com/x86/maxps
- https://www.felixcloutier.com/x86/pmaddubsw
- https://www.felixcloutier.com/x86/vpdpbusd

Refinement types and systems verifiers:
- https://arxiv.org/abs/2207.04034
- https://flux-rs.github.io/flux/
- https://github.com/verus-lang/verus
- https://verus-lang.github.io/verus/publications-and-projects/
- https://arxiv.org/abs/2409.13082
- https://dafny.org/
- https://github.com/creusot-rs/creusot
- https://github.com/AeneasVerif/aeneas
- https://www.microsoft.com/en-us/research/blog/rewriting-symcrypt-in-rust-to-modernize-microsofts-cryptographic-library/
- https://github.com/project-everest/vale

Proof-carrying code, decidability, determinism:
- https://en.wikipedia.org/wiki/Proof-carrying_code
- https://docs.kernel.org/bpf/verifier.html
- https://arxiv.org/abs/1702.01135
- https://en.wikipedia.org/wiki/Tarski%27s_exponential_function_problem
- https://en.wikipedia.org/wiki/Richardson%27s_theorem
- https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
