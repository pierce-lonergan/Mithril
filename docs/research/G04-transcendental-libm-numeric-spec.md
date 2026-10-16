# G04 — Transcendentals in the numeric spec: platform CRT as an opaque call vs a vendored correctly rounded (and vectorisable) libm

*Research dossier, 2026-10-11. Scope: resolve the contradiction between R11 (bit parity with the C binary requires calling the same platform CRT `expf`/`sinf`/`cosf` as opaque calls) and R07/R09 (a correctly rounded libm gives bit identity across Windows, Linux and macOS).*

*Method note.* The shared web-search budget for this run ran out before this agent's first search. Evidence therefore comes from (a) direct fetches of primary sources whose URLs were known or found by following links (project pages, docs, arXiv, GitHub), (b) the Hearth repository, and (c) **new measurements made for this dossier** on the project machine: AMD Ryzen 9 9950X, Windows 11 Pro 10.0.26200, `ucrtbase.dll` 10.0.26100.9444, MSVC toolset 14.44.35207 (VS 2022), `/O2 /fp:precise`. Machine load was not controlled, because other agents were running. All timings are single-thread, best of 7 to 9 runs, and **measured** (INV-HONEST). Inria's GitLab and HAL, and sourceware.org, returned bot-protection pages, so the CORE-MATH papers, CORE-MATH's performance chart data and glibc's upstream NEWS could not be read directly. glibc NEWS was read through the GitHub mirror. Unverified items are marked as such.

---

## Summary

- **Both sides are partly right, and they are answering different questions.** R11 is correct that, today, the only way for a port to reproduce the *current* C binary bit for bit is to call the same CRT functions. R07/R09 are correct that the end state should be a *specified* function. The contradiction disappears if the specification change happens **in C Hearth first**, under an ADR. The port's C-binary parity oracle then stays valid, and becomes stronger because it also holds across operating systems. (high confidence)
- **"The same CRT" is not a fixed function, even on one OS.** Microsoft documents that UCRT picks an FMA3 or non-FMA3 implementation of its transcendental functions at startup, by CPUID, and that results can differ ([MS Learn](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/get-fma3-enable-set-fma3-enable)). Measured here over all 2^32 inputs, the two paths disagree on 1 `expf` input, 44,232 `sinf` inputs and 18,018 `cosf` inputs, of which 9,007 lie in [0, 40960]. For a Qwen3-30B-A3B-shaped RoPE table, that changes cos values at 17 of the first 40,960 positions. (high, measured)
- **MSVC UCRT is documented as *not* correctly rounded.** Microsoft describes it as a close approximation, usually within ±1 ulp ([MS Learn](https://learn.microsoft.com/en-us/cpp/porting/floating-point-migration-issues)). The August 2026 accuracy survey measures worst-case errors of 0.501 ulp (`expf`) and 0.530 ulp (`sinf`, `cosf`) ([Gladman et al. 2026](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)). Measured here, UCRT `expf` misrounds 23,276 inputs, and `sinf`/`cosf` misround about 2.87 M inputs each (about 0.41 M with |x| ≤ 65536). (high)
- **In glibc 2.44, Apple's libm and UCRT, `expf`/`sinf`/`cosf` are still not correctly rounded. LLVM libc 22's are.** The worst-case errors are 0.502, 0.561 and 0.561 ulp for glibc 2.44; 0.514, 0.846 and 0.846 for Apple 26.5.2; and 0.500 for all three in LLVM libc 22.1.8 ([Gladman et al. 2026](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)). CORE-MATH publishes glibc patches for `expf`/`sinf`/`cosf`, but glibc 2.41–2.43 adopted other functions ([CORE-MATH](https://core-math.gitlabpages.inria.fr/); [glibc NEWS mirror](https://raw.githubusercontent.com/bminor/glibc/master/NEWS)). (high)
- **Scalar correct rounding costs little.** On a Ryzen 1700, LLVM libc's correctly rounded `expf` takes 9 cycles reciprocal throughput against 7 for glibc. Its `sinf` takes 12 against 25 and its `cosf` 13 against 32, so the correctly rounded versions are *faster* there ([LLVM libc](https://libc.llvm.org/headers/math/index.html)). For Hearth, the cost of scalar correct rounding would be around 1% of decode or 2,048-token prefill time. [inference] (medium)
- **Vectorised correct rounding exists but is immature.** The only implementation found is crmvec, an MIT library first published in 2026 by one developer with 0 stars. It reports an AVX2 correctly rounded `expf` at 1.5 ns/element against 0.7 for glibc libmvec and 2.7 for scalar CORE-MATH, on Zen 3 ([crmvec speed.md](https://raw.githubusercontent.com/anun333/crmvec/main/docs/speed.md)). Its method is a vector fast path, then a rounding test, then a scalar CORE-MATH fallback for the lanes the test cannot decide ([how-it-works.md](https://raw.githubusercontent.com/anun333/crmvec/main/docs/how-it-works.md)). (medium; self-reported)
- **A third option the dossiers missed: a *specified algorithm* (a canonical function) instead of correct rounding.** A fixed sequence of IEEE basic operations is bit-identical on every ISA by construction. The prototype built here (no FMA, degree-7 polynomial) gives **0 mismatches across scalar, AVX2 and AVX-512 over all 2^32 inputs**. It is 99.19% correctly rounded, with a maximum error of 1 ulp, and runs at **0.204 ns/element (AVX-512) against 1.12 ns for scalar UCRT `expf`** (measured). Java's StrictMath (fdlibm) is the precedent at language level ([Oracle](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StrictMath.html)). (high for the bit identity, medium for the cost)
- **Letting the compiler vectorise platform libm calls changes bits.** With `/fp:fast /arch:AVX2`, MSVC turns `expf`/`sinf` loops into `__vdecl_expf8`/`__vdecl_sinf8`. That is 4.9× faster for `expf`, but 51% of `expf` results and 25% of `sinf` results on [-10, 10] then differ from scalar UCRT, by up to 3 ulp. Under `/fp:precise` it does not vectorise these loops. (high, measured)
- **Transcendentals are a small share of Hearth's time today, and it will grow.** Using measured per-call costs, they take about 0.2% of decode CPU time at 512 context, about 1% at 4,096 and about 8% at 32,768, and about 3% of a 2,048-token prefill. RoPE `sin`/`cos` are negligible: 128 calls per token. Once the 94–136 GMAC/s AVX-512 attention kernel lands, scalar `expf` could become about 15–20% of long-context attention time. [inference] (medium)
- **Hearth's golden tests do not pin absolute logits.** They are relational (scheduling, batch and ISA identity) and tolerance-based against numpy ([test_golden_invariants.py](https://github.com/pierce-lonergan/hearth/blob/main/tests/golden/test_golden_invariants.py)). Switching the transcendental implementation therefore needs an ADR, because NUMERICS §4 is normative and INV-LOSSLESS-DEFAULT applies, plus updated C reference tests. It does **not** need a golden hash re-lock. The re-baseline is cheapest if it happens *before* R11's proposed cross-binary hash corpus exists. (high)
- **Documented cases of libm changes altering results exist, but none found is an LLM case outside Hearth.** Glatard et al. trace operating-system-dependent neuroimaging results to glibc versions in which `expf`/`sinf`/`cosf` differed by one bit ([Frontiers 2015](https://www.frontiersin.org/article/10.3389/fninf.2015.00012/abstract)). Hearth's own macOS CI broke on RoPE because Apple clang fused `sinf`+`cosf` into `__sincosf_stret` ([ci-first-runs](https://github.com/pierce-lonergan/hearth/blob/main/governance/reviews/2026-10-05-ci-first-runs.md)). llama.cpp's switch from an f16 lookup table to a vectorised `expf` changed outputs by design ([PR #7154](https://github.com/ggml-org/llama.cpp/pull/7154)). (medium)

---

## Findings

### F1. The contradiction, and what Hearth does today

- NUMERICS.md is normative. It says `expf`, `sinf`, `cosf` and `sqrtf` "come from the platform libm and are called the same way from every code path". SiLU, sigmoid, softmax and RoPE are defined in terms of these functions ([NUMERICS.md](https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md)).
- `cosf`/`sinf` are called through function pointers read back from a volatile local, so no compiler can fuse them into `sincos`, inline them or vectorise them. `expf` is called directly inside the `hx_softmax`, `hx_swiglu` and `hx_sigmoid` loops ([quant.c:644-666](https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant.c#L644), [model.c:219-235](https://github.com/pierce-lonergan/hearth/blob/main/engine/src/model.c#L219)). Handover T08 confirmed with `dumpbin` that the MSVC `/O2` DLL contains no `__vdecl_*` or SVML symbols ([T08-forward-gen-001](https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/T08-forward-gen-001.json)).
- RoPE cos/sin values are computed once per token position, as `rope_dim/2` pairs, and shared by all layers and heads ([model.c:419-430](https://github.com/pierce-lonergan/hearth/blob/main/engine/src/model.c#L419)). For Qwen3-30B-A3B (head_dim 128) that is 128 libm calls per token ([config.json](https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/main/config.json)).
- INV-DET-1 is scoped "for a fixed binary and ISA". INV-DET-3 requires scalar, AVX2 and AVX-512 to be bit-identical ([INVARIANTS.md](https://github.com/pierce-lonergan/hearth/blob/main/governance/INVARIANTS.md)).
- R11 concludes that Mithril must call the same CRT symbols as opaque FFI calls to stay bit-identical to C, and that a Mithril-native libm breaks this ([R11](R11-hearth-port-requirements.md)). R07 says correct rounding is "the only route" to cross-platform bit-identical `expf`/`sinf`/`cosf` and proposes vendoring CORE-MATH-style C11 ([R07](R07-verification-superoptimization.md)). R09 lists it as an open scope decision ([R09](R09-language-building-blocks.md)).
- [inference] R11 is right about *parity with the existing binary*. R07 overstates in one respect: correct rounding is **a** route to cross-platform bit identity, not the only one (F5.3, F8).

### F2. Accuracy and correct-rounding status of the relevant libms (binary32)

Worst-case error in ulps, exhaustive over all binary32 inputs. Source: the August 2026 edition of the survey by Gladman, Innocente, Mather, Ozaki and Zimmermann ([accuracy.pdf](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)). 0.500 means correctly rounded.

| library (version) | expf | sinf | cosf | tanhf |
|---|---|---|---|---|
| GNU libc 2.44 | 0.502 | 0.561 | 0.561 | 0.500 |
| LLVM libc 22.1.8 | **0.500** | **0.500** | **0.500** | **0.500** |
| MSVC (VS 2026, `/MT`) | 0.501 | 0.530 | 0.530 | 1.24 |
| Apple 26.5.2 (M1) | 0.514 | 0.846 | 0.846 | 0.817 |
| Intel IML 2026.1.0 | 0.506 | 0.546 | 0.548 | 0.514 |
| AMD LibM 5.3 | 0.501 | 0.530 | 0.729 | 0.500 |
| musl 1.2.6 | 0.502 | 0.501 | 0.501 | 2.19 |
| CUDA 13.3.1 | 1.94 | 1.50 | 1.52 | 1.82 |
| ROCm 7.2.4 | 1.00 | 1.61 | 1.61 | 1.41 |

- The survey notes two hardware effects. First, glibc and Intel's library contain runtime dispatchers that select different code (FMA, AVX2, AVX-512) on different CPUs. Second, the very same binary can give different results on Intel and AMD where `rcp`/`rsqrt` instructions are used ([accuracy.pdf §1](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)).
- For MSVC, the survey notes that `/MT` (static `libucrt.lib`) and `/MD` (`ucrtbase.dll`, which ships with the OS) can give different results, for example for `erff`. `/MD` results can therefore vary with the Windows version ([accuracy.pdf, notes on MSVC](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)).
- Intel's library ships undocumented `cr_sinf`, `cr_cosf`, `cr_sincosf` and others under the C23-reserved `cr_` prefix, with some exception-flag bugs. There is no `cr_expf` in the list ([accuracy.pdf §2.2](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)). The CORE-MATH FAQ confirms that `cr_` names are reserved for correctly rounded versions ([CORE-MATH FAQ](https://core-math.gitlabpages.inria.fr/faq.html)).
- IEEE 754-2019 *recommends* but does not require correctly rounded functions ([accuracy.pdf](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)).
- **glibc adoption.** CORE-MATH lists about 30 binary32 functions as integrated into glibc 2.42 and 7 binary64 functions (acosh, asinh, atanh, erf, erfc, lgamma, tgamma) into glibc 2.43. It links unofficial glibc patch branches for `expf`, `sinf`, `cosf` and `sincosf` ([CORE-MATH](https://core-math.gitlabpages.inria.fr/)). glibc's own NEWS shows part of the binary32 set (for example `cbrtf`, `erff`, `expm1f`, `log10f`, `tanf`, `sinhf`, `tgammaf`) already arriving in 2.41 ([glibc NEWS mirror](https://raw.githubusercontent.com/bminor/glibc/master/NEWS)). [inference] R11's drift risk is real: if glibc adopts those patches, Hearth's Linux logits change with no change to Hearth.
- AMD LibM has used CORE-MATH's `tanhf` since version 4.2 ([CORE-MATH](https://core-math.gitlabpages.inria.fr/)). That matters for engines that use the tanh form of GELU. [inference]

### F3. MSVC UCRT, documented and newly measured

**Documented.** Microsoft states that, because correct rounding in every case can be prohibitively expensive, the CRT functions aim for a close approximation, usually within ±1 ulp of the correctly rounded result, with some worse cases. It also states that implementations differ by architecture and are chosen at run time by CPU feature, so results may vary across CPUs, and that the VS 2015 move to the Universal CRT changed algorithms ([floating-point migration issues](https://learn.microsoft.com/en-us/cpp/porting/floating-point-migration-issues)). The `_set_FMA3_enable` page says that on x64 the CRT startup code turns the FMA3 implementations of the transcendental functions on or off according to CPU support. These implementations use different algorithms, and differences may be visible between machines with and without FMA3 ([_get_FMA3_enable/_set_FMA3_enable](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/get-fma3-enable-set-fma3-enable)).

**Measured here (exhaustive, all 2^32 bit patterns).** UCRT was called through a volatile function pointer, as Hearth does. The FMA3 path was toggled with `_set_FMA3_enable`. The reference was the UCRT binary64 function, rounded to binary32, with inputs within 2^-50 relative of a rounding boundary excluded as "ambiguous". The survey reports MSVC binary64 worst cases of 1.50 ulp (exp), 0.799 (sin) and 0.897 (cos), well inside that guard ([accuracy.pdf Table 3](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)).

| function | not correctly rounded, FMA3 path | not correctly rounded, non-FMA3 path | of those, |x| ≤ 65536 (FMA3 / non-FMA3) | FMA3 ≠ non-FMA3 (all / |x|≤65536 / x∈[0,40960]) |
|---|---|---|---|---|
| expf | 23,276 | 23,277 | 23,276 / 23,277 | 1 / 1 / 0 (x ≈ −68.53) |
| sinf | 2,866,966 | 2,910,002 | 408,738 / 408,738 | 44,232 / 0 / 0 |
| cosf | 2,876,120 | 2,858,108 | 419,760 / 401,748 | 18,018 / 18,014 / 9,007 |

- The `/MT` (toolset 14.44.35207) and `/MD` (ucrtbase 10.0.26100.9444) builds produced identical output hashes for all three functions on both paths. For these functions on this Windows build, the two runtimes agree. Nothing guarantees that they keep agreeing after a Windows update (see the survey note above). [inference]
- **Density of misrounded `expf` results by input range** (FMA3 path), per million binary32 inputs: [−104, −30) 73.8; [−30, −10) 80.7; [−10, −1) 83.6; [−1, 0) 8.24; [0, 1) 5.08; [1, 10) 87.1; [10, 89) 85.5. Softmax arguments (x − max ≤ 0) and SiLU arguments therefore hit misrounded inputs at roughly 1 in 12,000 for |x| ≥ 1.
- **RoPE census.** This is a Qwen3-30B-A3B-shaped table: θ_base = 1e6 and 64 frequencies, with `inv_freq[j] = (float)(1/1e6^(2j/128))`, which approximates the converter's tensor. Over positions below 4,096 (262,144 angles), the FMA3 and non-FMA3 paths differ on 10 cos values (10 positions) and 0 sin values. UCRT misrounds 263 cos and 208 sin values, touching 449 positions (11.0%). Below 40,960: 17 positions differ between paths, and 5,368 positions (13.1%) contain at least one misrounded cos or sin.
- [inference] Consequences for INV-DET-1. The same Hearth binary run with `--isa scalar` on an FMA3 machine and on a CPU without FMA3 would produce different logits at specific positions, even though the "ISA" is the same. In practice x86 CPUs with AVX2 also have FMA3, so the hazard is limited to old or low-end CPUs, hypervisors that mask CPUID bits, or code that calls `_set_FMA3_enable(0)`. The invariant's wording does not cover it.
- [inference] Consequences for a correct-rounding switch. With about 0.3 M SwiGLU `expf` calls per decoded token for Qwen3-30B-A3B (48 × 8 × 768), and attention softmax adding 1,536 calls per context position, almost every token would contain several misrounded UCRT results. Replacing UCRT with a correctly rounded function would therefore change essentially every token's logits bits, and 11–13% of RoPE positions as well. This is a real output change, but a one-time one.

### F4. Throughput and latency: correctly rounded versus platform libms

| implementation | expf | sinf | cosf | conditions | source |
|---|---|---|---|---|---|
| LLVM libc, correctly rounded (recip. throughput / latency, cycles) | 9 / 44 | 12 / 51 | 13 / 53 | Ryzen 1700, Clang 12, FMA; ranges [−10,10], [−π,π], [0,2π] | [LLVM libc](https://libc.llvm.org/headers/math/index.html) |
| glibc on the same rows (Ubuntu 20.04, so glibc 2.31 [inference]) | 7 / 38 | 25 / 57 | 32 / 59 | same | [LLVM libc](https://libc.llvm.org/headers/math/index.html) |
| LLVM libc, correctly rounded tanhf vs glibc (Ubuntu 22.04) | — | — | — | tanhf 13 vs 55 throughput, 57 vs 123 latency | [LLVM libc](https://libc.llvm.org/headers/math/index.html) |
| CORE-MATH scalar (ns/element) | 2.7 | 4.0 | 4.4 | Ryzen 5 PRO 5650U (Zen 3), gcc 13.3, memory-bound loop | [crmvec speed.md](https://raw.githubusercontent.com/anun333/crmvec/main/docs/speed.md) |
| crmvec AVX2, correctly rounded (ns/element) | 1.5 | 2.0 | 1.8 | same | same |
| glibc libmvec AVX2, not correctly rounded (ns/element) | 0.7 | 0.5 | 0.7 | same | same |
| UCRT FMA3 path (ns/call, throughput / latency chain) | 1.12 / 7.34 | 2.13 / 10.53 | 1.98 / 10.61 | Ryzen 9 9950X, ranges [−10,0] and [−π,π], via volatile function pointer; floor for an identity call is 0.7–1.1 ns | **measured here** |
| UCRT non-FMA3 path | 1.34 / 8.67 | 2.29 / 9.04 | 2.35 / 10.76 | same | **measured here** |
| UCRT on RoPE angles, p < 4096 (FMA3) | — | 1.78 / 8.98 | 1.73 / 9.09 | same | **measured here** |

- CORE-MATH's site has a chart of average cycles against glibc, Intel, LLVM libc and AMD LibM on a Xeon Silver 4214 with GCC 15.2.0, glibc built `-O3 -march=native` and linked statically. The numbers are not available as text, so they are **unverified here** ([CORE-MATH](https://core-math.gitlabpages.inria.fr/)). The site also states that its functions are tested with and without FMA.
- crmvec's scalar `LD_PRELOAD` replacement costs "0.36 to 3.3 times glibc" per function. A complete FreeSurfer run is about 13% slower with it ([crmvec README](https://github.com/anun333/crmvec)).
- The survey's authors state that for binary32 (and most binary64) functions correct rounding is now known to be achievable at very low cost, with reference implementations that outperform current libraries. They point to the 2025 ACM Computing Surveys article by Brisebarre, Hanrot, Muller and Zimmermann ([accuracy.pdf](https://members.loria.fr/PZimmermann/papers/accuracy.pdf); [doi:10.1145/3747840](https://doi.org/10.1145/3747840), not read here).
- RLIBM: the abstracts claim "faster than state-of-the-art" (RLIBM-32, PLDI 2021) and more than 2× over earlier RLIBM prototypes (RLibm-MultiRound, PLDI 2025). The only absolute figure extracted is that `fesetround` costs about 40 cycles on average on an EPYC 7313P ([arXiv 2104.04043](https://arxiv.org/abs/2104.04043); [arXiv 2504.07409](https://arxiv.org/html/2504.07409)). LLVM's `logf`, `log2f` and `log10f` use RLIBM polynomials, and its `expf`/`exp2f` use RLIBM-derived range reduction ([RLIBM page](https://people.cs.rutgers.edu/~sn349/rlibm/)). No per-function RLIBM speed against glibc was obtained. **Unverified.**
- **Apple libm performance:** no source found. **Unverified.**
- [inference] Scalar correct rounding costs roughly 0.8–1.3× a good platform libm for `expf`, and less for `sinf`/`cosf`. It is not a performance obstacle at scalar level. The gap opens only against *vector* libms such as libmvec, SVML and `__vdecl`, which are 2–10× faster per element and are not correctly rounded.

### F5. Vectorisation: which results can SIMD lanes reproduce?

**F5.1 Vector libms do not reproduce scalar bits (measured).** MSVC with `/O2 /fp:precise`, with or without `/arch:AVX2`, did not vectorise a plain `y[i] = expf(x[i])` or `sinf` loop (report code 1200), and results matched scalar UCRT on 1,048,576 samples. With `/fp:fast /arch:AVX2`, MSVC emitted `__vdecl_expf4/8` and `__vdecl_sinf4/8`. That gave `expf` at 0.225 ns/element against 1.10 scalar, and `sinf` at 0.234 ns/element. On uniform [−10, 10], 537,338 of 1,048,576 `expf` results (51.2%) and 266,211 `sinf` results (25.4%) differed from scalar UCRT, by up to 3 ulp and 2 ulp. ggml has the same effect: its softmax uses its own `ggml_v_expf` in SIMD lanes, documented at roughly 1.5 + 0.5 ulp worst case, and libm `expf` in the scalar tail. An element's value therefore depends on its index modulo the vector width and on the ISA ([vec.h](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cpu/vec.h), [vec.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cpu/vec.cpp)). glibc advertises auto-vectorised `exp`/`sin`/`cos` on AArch64 only under `-ffast-math` (2.39 NEWS, [mirror](https://raw.githubusercontent.com/bminor/glibc/master/NEWS)), and Hearth forbids `-ffast-math` ([ADR-0003](https://github.com/pierce-lonergan/hearth/blob/main/governance/decisions/ADR-0003-canonical-numerics.md)).

**F5.2 Correctly rounded *and* vectorised: one implementation found.** crmvec is a drop-in `libmvec.so.1` for Linux with SSE2, AVX, AVX2 and AVX-512 entry points on x86-64, covering 26 functions in float and double. Its results are meant to equal CORE-MATH bit for bit, and its one-argument float functions are checked on all 2^32 inputs ([crmvec](https://github.com/anun333/crmvec)). The mechanism is a vector fast path accurate to about 2^-31 to 2^-37, a rounding test, and a scalar CORE-MATH call for undecided lanes, which it says are "well under 1%" of inputs. `sinf`/`cosf` are evaluated in double precision, and non-nearest rounding modes send every lane to scalar code ([how-it-works.md](https://raw.githubusercontent.com/anun333/crmvec/main/docs/how-it-works.md)). Caveats: the x86 build needs gcc; there are no published AVX-512 or Zen 5 numbers; it has 125 commits and 0 stars; it uses a CORE-MATH snapshot dated 2026-10-06 ([crmvec](https://github.com/anun333/crmvec)). [inference] Because correctly rounded results are unique, any correct implementation, scalar or SIMD, on any OS, yields the same bits, which is exactly the property INV-DET-3 needs. The cost is the fallback. If 0.5% of lanes are undecided, about 8% of 16-lane AVX-512 vectors take at least one scalar detour, which makes the timing data-dependent but not the result. No other correctly rounded SIMD library was found. SLEEF and Intel SVML offer bounded-ulp vector functions, not correctly rounded ones ([SLEEF](https://sleef.org/)). Given the search outage, **other implementations may exist**.

**F5.3 A specified algorithm vectorises exactly (measured).** IEEE 754 makes every basic operation (+, −, ×, ÷, sqrt, conversions) correctly rounded. A transcendental *defined* as a fixed sequence of such operations, with no FMA contraction and fixed constants, therefore gives the same bits in every lane of every ISA. This is the canonical-order principle Hearth already uses for `sum16`/`dot16`. The prototype built here used Cody–Waite reduction with a 1.5·2^23 rounding trick, a degree-7 Taylor polynomial in Horner form and two-step 2^k scaling, written once in scalar C and once each in AVX2 and AVX-512 intrinsics (appendix). Results:
- **Bit identity:** scalar ≡ AVX2 ≡ AVX-512 on all 2^32 inputs, with 0 mismatches. The disassembly contains no FMA instructions.
- **Accuracy** on (−104, 88): 99.19% correctly rounded; 18,232,838 inputs (0.81%) are off by exactly 1 ulp, and none by 2 or more. This is an untuned prototype. A minimax polynomial or a float-float final step should get closer to correct rounding but will not reach it. [inference]
- **Speed** on [−10, 0], one thread: AVX-512 0.204 ns/element, AVX2 0.383, non-inlined scalar 2.73, and UCRT scalar 1.12 in the same harness. The canonical AVX-512 version is **5.5× faster than the platform call Hearth uses today** and roughly as fast as MSVC's non-reproducible `__vdecl_expf8` at 0.225.
- Precedents: Java's `StrictMath` defines `exp`, `sin`, `cos` and others as the results of the fdlibm 5.3 algorithms, transliterated into Java, for portability ([StrictMath](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StrictMath.html)). SLEEF states that its scalar functions return the same value for the same argument on every architecture ([SLEEF](https://sleef.org/)).

### F6. Documented cases of libm or implementation changes altering numeric outputs

- **Neuroimaging (glibc).** FSL, FreeSurfer and CIVET results varied between Linux distributions. The authors traced this to single-precision math functions whose implementations changed between glibc versions (2.5 and 2.18 are named), with `expf`, `cosf` and `sinf` differing by one bit. Long pipelines amplified the differences: some Dice coefficients fell to 0.59, and about a third of subjects' fMRI ICA results changed ([Glatard et al. 2015](https://www.frontiersin.org/article/10.3389/fninf.2015.00012/abstract)). A 2026 follow-up on Parkinson's MRI measures is cited by the accuracy survey ([bioRxiv, via accuracy.pdf ref. 10](https://www.biorxiv.org/content/10.64898/2026.01.09.698203v1); not read here).
- **glibc algorithm changes.** 2.27 introduced new generic `expf`, `exp2f`, `logf`, `log2f`, `powf`, `sinf`, `cosf` and `sincosf`, plus FMA-optimised x86-64 `expf`, `sinf`, `cosf` and `sincosf`. 2.29 replaced the generic `exp`, `exp2`, `log`, `log2`, `pow`, `sinf`, `cosf`, `sincosf` and `tanf` ([glibc NEWS mirror](https://raw.githubusercontent.com/bminor/glibc/master/NEWS)). [inference] Any bit-exact downstream check on Linux would have changed at those upgrades.
- **MSVC.** VS 2015's move to the Universal CRT introduced new algorithms and bug fixes that Microsoft says can cause detectable result differences ([MS Learn](https://learn.microsoft.com/en-us/cpp/porting/floating-point-migration-issues)).
- **Hearth itself (ML inference).** On the first macOS arm64 CI run, the engine differed from its naive NUMERICS reference by about 1e-5 (max |diff| 1.14e-5) on the RoPE paths only. The leading hypothesis was Apple clang fusing `sinf`+`cosf` into `__sincosf_stret`. Routing both through non-inlinable wrappers made the test pass, and glibc's `sincosf` was verified to equal separate calls exhaustively ([ci-first-runs](https://github.com/pierce-lonergan/hearth/blob/main/governance/reviews/2026-10-05-ci-first-runs.md), [R3-forward-gen-002](https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/R3-forward-gen-002.json)).
- **llama.cpp (ML inference).** PR #7154 (May 2024) replaced ggml's 65,536-entry f16 lookup table for SiLU and softmax with vectorised `expf`. It reported softmax 1.5–2.1× faster and claimed a worst case around 2 ulp, which changes outputs by construction. A later server non-determinism bug was traced to `-ffinite-math-only`, which the new SiLU path depends on, and fixed by a build check (PR #7726) ([PR #7154](https://github.com/ggml-org/llama.cpp/pull/7154)). No before/after perplexity figures were posted.
- No published case was found of a *platform libm upgrade* changing LLM inference outputs in PyTorch, ONNX Runtime or similar engines. **Unverified either way** (search unavailable). [inference] Most such engines use their own vector exp (SLEEF, MLAS, ggml), so the platform libm matters less to them than to Hearth.
- **Language-level acknowledgement.** Rust documents `f32::exp`, `sin` and `cos` as having non-deterministic precision that can vary by platform, Rust version, and even between calls in one execution ([Rust std](https://doc.rust-lang.org/std/primitive.f32.html)). Java's `Math` explicitly does not promise bit-for-bit results, allowing platform-native implementations within 1 ulp, semi-monotonic. `StrictMath` exists to give fixed results ([Math](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Math.html)).

### F7. Share of time spent in exp, SiLU, softmax and RoPE in Hearth-class engines

No public llama.cpp profile with per-op time shares was obtained. The only figures in PR #7154 are op-level softmax speedups ([PR #7154](https://github.com/ggml-org/llama.cpp/pull/7154)). The estimates below combine Hearth's operation counts for Qwen3-30B-A3B (48 layers, 32 query heads, 8 of 128 experts, moe_intermediate 768 ([config](https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/main/config.json))) with the measured UCRT costs (1.12 ns/`expf`, about 2 ns/`sinf` or `cosf`) and Hearth's measured phase timings. **All shares are [inference].**

- **Calls per decoded token:** SwiGLU `expf` 294,912; router softmax 6,144; attention softmax 1,536 × context length; RoPE 128 `sin`/`cos`.
- **Decode** at 21.9 tok/s, fully cached, 16 threads, about 45.7 ms per token, so about 731 ms of core time ([H03-forward-gen-002](https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/H03-forward-gen-002.json)). `expf` core time is about 1.2 ms at 512 context (0.2%), 7.4 ms at 4,096 (1.0%) and 56.7 ms at 32,768 (7.8%). RoPE takes about 0.26 µs per token. Out-of-core decode is NVMe-bound, so the shares are smaller there.
- **2,048-token prefill:** 226.3 tok/s (about 9.05 s), of which attention is 5.87 s ([H03-forward-gen-001](https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/H03-forward-gen-001.json)). Attention-softmax `expf` count = 1,536 × Σ_{t≤2048} t ≈ 3.22 × 10^9, which is about 3.6 s of core time, or about 0.23 s of wall time on 16 cores (about 4% of attention). SwiGLU adds about 0.04 s. Total: about 3% of prefill.
- **After kernel work.** The AVX-512 value-pass prototype runs at 94–136 GMAC/s against 15–18 for the portable loop ([H03-forward-gen-001](https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/H03-forward-gen-001.json)). If the QK and PV passes speed up about 5×, scalar `expf` would be about 15–20% of long-context attention time. A vectorised canonical `expf` at 0.2 ns would bring that back to about 3%.
- **Cost of scalar correct rounding:** at LLVM libc's 9/7 throughput ratio, about +0.3% decode time at 4,096 context and about +0.9% at 2,048-token prefill. At a pessimistic 2.4× (CORE-MATH scalar against UCRT, different machines), about +1.5% and +4%.

### F8. What a switch would actually break in Hearth's governance

- The golden suite checks INV-NUM-1/2 against the numpy reference within 1e-3 relative error, and INV-DET-1/2/3 as equalities between runs of the same build. **It stores no absolute logit hashes** ([test_golden_invariants.py](https://github.com/pierce-lonergan/hearth/blob/main/tests/golden/test_golden_invariants.py)). A libm change that is applied consistently to every code path leaves every golden test valid without re-locking `MANIFEST.sha256`.
- What does change: NUMERICS §4, which is normative and needs an ADR ([INVARIANTS.md preamble](https://github.com/pierce-lonergan/hearth/blob/main/governance/INVARIANTS.md)); INV-LOSSLESS-DEFAULT, because outputs change; and the bit-exact C references in `engine/tests/test_model.c` and `test_quant.c`, which must call the same function, or an independent implementation of the same correctly rounded or canonical specification ([T08-forward-gen-001](https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/T08-forward-gen-001.json)).
- R11's cross-binary SHA-256 logit corpus does **not exist yet** ([R11](R11-hearth-port-requirements.md)). [inference] Doing the switch first means that corpus is created once, on the final semantics. Doing it later means one re-baseline of the corpus.
- INV-DEP permits "C11 + OS APIs only: no third-party libraries" ([INVARIANTS.md](https://github.com/pierce-lonergan/hearth/blob/main/governance/INVARIANTS.md)). Whether *vendored* MIT source counts as a third-party library is a maintainer question. A Hearth-authored canonical `expf` avoids the question. CORE-MATH is MIT ([CORE-MATH](https://core-math.gitlabpages.inria.fr/)), but whether its `expf`/`sinf`/`cosf` compile under MSVC is **unverified**: CORE-MATH is tested on x86_64 Linux, and crmvec's x86 build needs gcc.

---

## Implications for Mithril

1. **Make transcendental semantics normative, not opaque, in the deterministic numeric profile.** [inference; high] `exp`, `sin`, `cos`, `tanh` and similar functions should be *specified pure functions*, with exactly one result per input. Two specification kinds should be admissible:
   - **`cr`**: correctly rounded, round-to-nearest-even. This is the standard-library default, with the C23 `cr_` naming convention as an interop anchor ([CORE-MATH FAQ](https://core-math.gitlabpages.inria.fr/faq.html)). Any correct implementation, on any ISA, OS or GPU, gives the same bits, and an independent implementation can serve as a test oracle.
   - **`canon.vN`**: a named, *versioned* algorithm written in Mithril as a DAG of IEEE basic operations with FMA contraction forbidden (or mandated everywhere). This is the StrictMath/fdlibm pattern. It is bit-identical across ISAs by construction (F5.3) and vectorises at full speed, but it is not correctly rounded, so changing it means a new version number and an ADR.
2. **The compiler may vectorise, inline or fuse a specified transcendental only into implementations proven bit-equal to the specification.**
   - For `canon` functions the proof is structural. It is the same order-preserving lowering Mithril already needs for `sum16`/`dot16` (R11).
   - For `cr` binary32 univariate functions, an exhaustive check is cheap. The probe here ran all 2^32 inputs for 3 functions × 2 CRT paths plus a binary64 reference in about 22 s on 32 threads.
   - Vector `cr` implementations use the fast-path, rounding-test and scalar-fallback structure (F5.2). The language should make this pattern expressible, as masked lanes with a scalar escape, and its timing variance visible to the cost model.
3. **Allow platform libm only through explicit FFI, with a `nondet(platform)` effect that the deterministic profile rejects.** The one exception is a `parity` shim used to compare against legacy C binaries during migration. Both Rust and Java make this distinction (F6). The diagnostic should be machine-actionable (seed H5): for example, `{"error":"OpaqueLibmInCanonicalContext","fix":"use cr.exp or canon.exp.v1"}`.
4. **Never silently substitute a vector math library.** MSVC's `/fp:fast` behaviour, where 51% of `expf` outputs change, is the anti-pattern (F5.1). A Mithril "fast-math" mode must be an explicitly non-canonical effect, never a default.
5. **Verification story.** SMT FP theory has no transcendentals (R07). A `canon` function is made only of basic operations, so SMT or structural equivalence applies. `cr` functions are verified by exhaustive comparison with MPFR or CORE-MATH for binary32. Binary64 needs proofs or the published worst-case tables, which is out of scope for Hearth today, since Hearth is binary32. [inference]
6. **The GPU tier reuses the same specification.** CUDA `expf` has a worst case of 1.94 ulp and ROCm 1.00 ([accuracy.pdf](https://members.loria.fr/PZimmermann/papers/accuracy.pdf)). A future GPU backend matches the CPU bits only if it implements the same `cr` or `canon` function with no FMA contraction. [inference]

## Implications for Hearth

Recommended plan [inference; medium–high]:

1. **ADR-0010, "Specified transcendentals", in C Hearth, before R11's cross-binary hash corpus is built.**
   - Change NUMERICS §4 from "platform libm" to named functions: `hx_cr_sinf` and `hx_cr_cosf`, which are scalar and correctly rounded, at negligible cost (128 calls per token); and `hx_expf`.
   - For `hx_expf`, either (a) correctly rounded scalar code, costing about 1% (F7), or (b) a Hearth-authored `canon.v1` written in C11 with scalar, AVX2 and AVX-512 versions in canonical order, which would make softmax and SwiGLU *faster* and keeps INV-DEP clean.
   - Record the measured output-change rate (F3) under INV-LOSSLESS-DEFAULT.
2. **Update the bit-exact C references** in `test_model.c` and `test_quant.c`. Golden tests need no re-lock (F8).
3. **Add cross-OS hash equality to CI** (Windows MSVC, Linux gcc/clang, macOS arm64) as a new invariant, for example "INV-DET-4: logits are bit-identical across supported OS/compiler/ISA". Once no platform libm is in the output path, this becomes achievable, and it catches compiler contractions and `sincos` fusion automatically. [inference] Other cross-platform hazards (F16 conversion, `nearbyintf`, contraction flags) are already pinned by NUMERICS.
4. **Reword INV-DET-1** if the CRT stays in the output path. It should say "fixed binary, CRT/libm build and CPU feature set", because of the UCRT FMA3 dispatch (F3).
5. **Then port to Mithril** using the same functions. R11's acceptance oracle ("byte-identical to the C build") holds unchanged and now holds across operating systems as well. No opaque CRT calls are needed in Mithril.
6. **If maintainers decline the change to C**, run R11's plan with an `extern opaque` parity shim. Record the `ucrtbase.dll` and glibc versions and the `_get_FMA3_enable()` state in the corpus metadata, and plan one corpus re-baseline under an ADR when the specification changes.
7. **Hygiene, whatever is decided:** log `_get_FMA3_enable()`, the libm identity and the CPU flags in benchmark and trace headers. Note that `expf` is called directly, not through the volatile-pointer guard used for `sinf`/`cosf`. It is safe under `/fp:precise` and `-ffp-contract=off`, as measured and as verified by T08, but a future `-ffast-math`-style flag would silently swap in a vector libm.

## Where the seed discussion is right or wrong

- **B6 (vector-width polymorphism, "vectorisation mathematically guaranteed") is wrong for transcendentals unless their semantics are specified.** Vectorising a platform libm call changes 25–51% of results (F5.1). With `cr` or `canon` semantics it becomes right, and a canonical `expf` gains 5.5× (F5.3).
- **B8 (SMT, Z3/Alive2-style, equivalence checking):** right only after transcendentals are reduced to basic operations (the `canon` kind). For `cr` binary32 functions, exhaustive testing is cheaper and complete. This agrees with R07's critique.
- **C3 ("60–90% of compute wasted", including on unfused elementwise ops) is not supported for Hearth's transcendentals.** They take about 0.2–8% of decode and about 3% of 2,048-token prefill (F7, [inference]). The claim's magnitude is unsourced.
- **C4 (whole-layer fusion GEMM→bias→norm→activation):** right in direction, but fusing SiLU into an expert-matmul epilogue requires an `expf` that is defined *inside vector code*. That is a direct argument for `canon`/`cr` semantics over opaque calls.
- **F2/F6 (Lean harness replacing SMT):** Lean's `Float` transcendentals are opaque (R07), so Lean cannot reason about platform libm calls either. A `cr` or `canon` specification makes the property statable.
- **H5 (machine-actionable diagnostics):** a natural fit for flagging opaque libm use in canonical code (Implications for Mithril, item 3).
- Between the dossiers: R11 is **right** that parity with the existing binary needs the same CRT, but **incomplete**, because "the same CRT" varies with CPU features and, under `/MD`, with the Windows version (F3, F2). R07 is **wrong** that correct rounding is the *only* route to cross-platform identity, since specified algorithms also work (F5.3, F6). It is also **unverified** on "stays within INV-DEP", since MSVC compilability and the vendoring policy are open (F8). R07's figure "glibc 2.42 integrated about 30 binary32 functions" is roughly right, though some arrived in 2.41. R11's statement that `expf`/`sinf`/`cosf` were not adopted remains true as of glibc 2.44 (F2).

## Open questions

1. Do CORE-MATH's `expf`, `sinf` and `cosf` (or LLVM libc's) build with MSVC as C11, given possible use of `__int128`, GCC builtins or attributes? If not, how large is the port?
2. Does vendoring MIT source satisfy INV-DEP ("no third-party libraries")? This is a maintainer decision.
3. How fast is a correctly rounded vector `expf` with fast path and fallback on Zen 5 AVX-512? No measurement exists. crmvec reports AVX2 on Zen 3 only, self-reported.
4. How accurate can a no-FMA, float-only `canon.v1` `expf` get (for example ≤ 0.51 ulp with a minimax polynomial plus a float-float step), and at what extra cost over the 0.204 ns prototype?
5. Is the UCRT FMA3 path bit-identical on Intel and AMD, and across Windows updates of `ucrtbase.dll`? Only one machine and one build were tested here.
6. What is the measured profile share of `expf` in Hearth on real Qwen3 weights at 4k–32k context? F7 gives estimates only.
7. Apple libm throughput, and whether any macOS 26.x update changed `sinf`/`cosf`. Nothing was found.
8. Will glibc merge CORE-MATH's `expf`/`sinf`/`cosf` patches, and when? The patch branches exist, and the timeline is unknown.
9. Is there a vectorised correctly rounded library other than crmvec (for example in Intel IML, AMD AOCL or Arm Performance Libraries)? Not found, and the search was unavailable.
10. Should Mithril standardise `cr` for all functions and allow `canon.vN` only by opt-in, or the reverse for the hot functions (`exp`) of ML engines?

---

## Appendix: measurement notes (reproducible; scratch code not committed)

- `probe.c`: all 2^32 inputs, 32 threads, in blocks of 2^26. Each block is computed with `_set_FMA3_enable(1)`, then with `(0)`, then compared. The reference is UCRT binary64 `exp`/`sin`/`cos` rounded to binary32, with a 2^-50 relative ambiguity guard (8 / 66 / 66 ambiguous inputs). Built `/O2 /fp:precise` as both `/MD` and `/MT`. Run time about 22 s for all three functions.
- `veccall.c`: MSVC vectorisation behaviour under `/fp:precise` versus `/fp:fast /arch:AVX2`, on 2^20 uniform inputs in [−10, 10].
- `rope_check.c`: θ = (float)p · inv_freq[j], 64 frequencies, θ_base 1e6, p < 4,096, 32,768 and 40,960.
- `canon_exp.c`: the prototype canonical `expf`. Scalar definition, mirrored op for op in AVX2 and AVX-512:

```c
/* no FMA; every line is one IEEE binary32 op (or an exact integer op) */
if (x != x) return NaN_canonical;
xc = clamp(x, -104, 89);
kf = (xc * 0x1.715476p+0f + 0x1.8p23f) - 0x1.8p23f;   /* round(x*log2 e) */
r  = (xc - kf * 0x1.62e4p-1f) - kf * 0x1.7f7d1cp-20f;  /* Cody-Waite, k*ln2hi exact */
p  = Horner(r; 1/7!, 1/6!, 1/5!, 1/4!, 1/3!, 1/2, 1, 1);  /* mul then add, 7 steps */
k  = (int)kf; k1 = k >> 1; k2 = k - k1;
return (p * 2^k1) * 2^k2;                              /* two-step scaling */
```

---

## Sources

- https://core-math.gitlabpages.inria.fr/
- https://core-math.gitlabpages.inria.fr/faq.html
- https://members.loria.fr/PZimmermann/papers/accuracy.pdf
- https://members.loria.fr/PZimmermann/papers/
- https://doi.org/10.1145/3747840
- https://www.biorxiv.org/content/10.64898/2026.01.09.698203v1
- https://libc.llvm.org/headers/math/index.html
- https://people.cs.rutgers.edu/~sn349/rlibm/
- https://arxiv.org/abs/2104.04043
- https://arxiv.org/abs/2111.12852
- https://arxiv.org/abs/2504.07409
- https://arxiv.org/html/2504.07409
- https://github.com/anun333/crmvec
- https://raw.githubusercontent.com/anun333/crmvec/main/README.md
- https://raw.githubusercontent.com/anun333/crmvec/main/docs/speed.md
- https://raw.githubusercontent.com/anun333/crmvec/main/docs/how-it-works.md
- https://sleef.org/
- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/get-fma3-enable-set-fma3-enable
- https://learn.microsoft.com/en-us/cpp/porting/floating-point-migration-issues
- https://raw.githubusercontent.com/bminor/glibc/master/NEWS
- https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cpu/vec.h
- https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-cpu/vec.cpp
- https://github.com/ggml-org/llama.cpp/pull/7154
- https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/main/config.json
- https://doc.rust-lang.org/std/primitive.f32.html
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StrictMath.html
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Math.html
- https://www.frontiersin.org/article/10.3389/fninf.2015.00012/abstract
- https://github.com/pierce-lonergan/hearth/blob/main/docs/NUMERICS.md
- https://github.com/pierce-lonergan/hearth/blob/main/engine/src/quant.c#L644
- https://github.com/pierce-lonergan/hearth/blob/main/engine/src/model.c#L219
- https://github.com/pierce-lonergan/hearth/blob/main/engine/src/model.c#L419
- https://github.com/pierce-lonergan/hearth/blob/main/governance/INVARIANTS.md
- https://github.com/pierce-lonergan/hearth/blob/main/governance/decisions/ADR-0003-canonical-numerics.md
- https://github.com/pierce-lonergan/hearth/blob/main/governance/reviews/2026-10-05-ci-first-runs.md
- https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/R3-forward-gen-002.json
- https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/T08-forward-gen-001.json
- https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/H03-forward-gen-001.json
- https://github.com/pierce-lonergan/hearth/blob/main/governance/handovers/H03-forward-gen-002.json
- https://github.com/pierce-lonergan/hearth/blob/main/tests/golden/test_golden_invariants.py
- Mithril dossiers (local): docs/research/R07-verification-superoptimization.md, R09-language-building-blocks.md, R11-hearth-port-requirements.md
