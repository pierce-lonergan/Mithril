# R10 — Fact-check of the seed discussion

Scope: every numbered claim (A1–I8) in the user-supplied seed discussion digest
(`scratchpad/seed-discussion.md`), checked against vendor manuals, measured instruction tables,
papers and repositories. Today is 2026-10-11. Verdicts: true / mostly-true / misleading / false /
unverifiable / likely-fabricated. **[inference]** marks my own reasoning or arithmetic. Confidence
is given for key claims.

**Process note.** The web-search budget shared by all agents in this run ran out partway through
this task. Everything below was checked by fetching primary pages directly (GitHub API, raw repo
files, arXiv abstracts, uops.info, Agner Fog's manual, vendor docs). A few items could not be
checked and are marked "unverified" (see Open questions).

---

## Summary

- **Overall: the instincts are good and the numbers are bad.** Of 59 claims, 24 are true or
  mostly-true (4 true, 20 mostly-true), 17 misleading, 6 false, 5 likely-fabricated and 7
  unverifiable or speculative (the verdict table has one row per claim). The design ideas (hardware-aware
  types, verified superoptimisation, explicit async memory pipelines, low-bit primitive types)
  hold up. The quantitative claims (the speed-up table, IPC and power figures, "up to 70%",
  "30+ FPS") have no sources, and several break the memory roofline that governs Hearth.
- **openai/math exists.** It was created 2026-10-06 under Apache-2.0 and has about 13.9k stars.
  It catalogues 719 manuscripts in 372 families; launch-day reports said 722. It has a Lean 4
  library (toolchain v4.34.1), about 42% of top-line results are formalised, and checking uses
  the external **leanprover/comparator** tool. So F1 is **mostly-true**
  ([repo](https://github.com/openai/math), [README](https://raw.githubusercontent.com/openai/math/main/README.md)).
  The family-level claims are wrong:
  - **Family 087** is the Mahler conjectures, not SDP or register allocation.
  - **Family 197** is Kaplansky's direct-finiteness conjecture. The Mézard–Parisi spin-glass
    family is **221**.
  - The catalogue's disciplines include no ODE or numerical-analysis section.
  
  So F3 and F4 are **false** and F5 is **likely-fabricated** (high confidence).
- **Self-modifying-code mechanics (I7) are false.** INVD is a ring-0 instruction that throws
  away dirty cache lines. Using it would corrupt memory. x86 does not need CLFLUSH for
  instruction-cache coherence. What it needs is a serializing instruction for cross-modifying
  code (SDM §8.1.3) or, on Windows, `FlushInstructionCache`
  ([INVD](https://www.felixcloutier.com/x86/invd), [MS docs](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache)).
- **"Single CPU cycle" CMPXCHG16B (I5) is false.** On Zen 5, LOCK CMPXCHG16B measures about
  17 cycles reciprocal throughput and 19+ cycles latency. On Alder Lake-P it is about 24–28
  cycles ([uops.info](https://uops.info/html-instr/CMPXCHG16B_LOCK_M128.html)). A pointer swap
  doesn't need it anyway: an aligned 8-byte store or XCHG is enough.
- **"Guaranteed" claims are false:**
  - **SMT "guaranteeing bounded loss divergence" (I4).** Exact neural-network verification is
    NP-complete and scales to small networks ([Reluplex](https://arxiv.org/abs/1702.01135)). The
    DGM itself validates edits empirically because proofs are impractical
    ([DGM](https://arxiv.org/abs/2505.22954)).
  - **Null-space projection "eliminating catastrophic forgetting" (I6).** AlphaEdit's guarantee
    is exact only in theory. In practice it thresholds eigenvalues at 1e-2 over an estimated key
    set, and it was tested to about 3,000 edits ([AlphaEdit](https://arxiv.org/html/2410.02355v4)).
- **The low-bit kernel claims (C6, D5) point at the wrong instruction.** The fastest ternary and
  low-bit CPU kernels use lookup tables or int8 dot products, not popcount:
  - bitnet.cpp uses TL (lookup-table) and I2_S kernels
    ([bitnet.cpp](https://arxiv.org/abs/2502.11880)).
  - T-MAC uses `tbl`/`pshuf` lookups and avoids FMA
    ([T-MAC](https://raw.githubusercontent.com/microsoft/T-MAC/main/README.md)).
  - Popcount fits binary XNOR networks. Low-bit types as language primitives is still a good
    idea.
- **VGATHER as the sparsity primitive (C5) is a poor fit on Hearth's CPU.** A zmm `VPGATHERDD`
  takes 64 µops and about 12.6 cycles on Zen 5 (16.6 on Zen 4)
  ([uops.info](https://uops.info/html-instr/VPGATHERDD_ZMM_K_VSIB_ZMM.html)). MoE sparsity is
  coarse (whole experts), so the right lowering is contiguous slabs plus prefetch, not
  element gathers **[inference, high]**.
- **The latency constants are off:**
  - The branch mispredict penalty of 15–20 cycles (B7) is about right: 15–18 on Zen 4 and
    15–25 on Zen 5 per Agner Fog.
  - "DRAM→L1 ~200 cycles" (C7) is too low. The 9950X measures about 70 ns, which is roughly
    400 cycles at 5.7 GHz ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
- **P/E-core dual code paths (B10) don't apply to the target machine.** The Ryzen 9 9950X has
  16 identical Zen 5 cores. On Intel hybrid parts the visible ISA is equalised (AVX-512 is
  disabled), and the OS migrates threads freely
  ([Alder Lake](https://en.wikipedia.org/wiki/Alder_Lake)).
- **The video-generation speedups (E4) are real but the mechanism is described wrongly.**
  FORA, Δ-DiT, TeaCache (up to 4.41×) and PAB (up to 10.5×) reuse computation **across
  denoising steps**, not across frames, and they skip whole blocks, not CMOV-selected
  elements ([TeaCache](https://arxiv.org/abs/2411.19108), [PAB](https://arxiv.org/abs/2408.12588)).
- **"Nothing combines all of this" (H7) is true only trivially.** Each piece exists:
  - Exo: a user-schedulable hardware language.
  - Jasmin: a verified assembly-level language.
  - STOKE and SuperCoder: superoptimisers. SuperCoder reaches 1.46× over gcc -O3 at 95%
    correctness ([SuperCoder](https://arxiv.org/abs/2505.11480)).
  - Mojo: does have inline assembly.

---

## Findings

### F-A. Below C (A1)

The layering is broadly right. Microcode updates are signed and loaded by firmware or the OS
([Intel microcode guidance](https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/best-practices/microcode-update-guidance.html),
not re-fetched in this pass). One nuance matters for Mithril: most x86 instructions decode to
µops in hard-wired decoders, and only complex instructions use the microcode sequencer
**[inference, high]**. Zen 5 can decode two 4-wide streams and has a 6K-entry µop cache. Most
instructions generate one µop
([Agner Fog, microarchitecture manual §25](https://www.agner.org/optimize/microarchitecture.pdf)).
Neither a language nor a compiler can reach "microcode" or "HDL" on a stock CPU.

### F-B. The x86-native blueprint (B1–B12)

**B1, C abstract machine.** Mostly-true. Same-type pointer aliasing, pointer escape and
strict-FP semantics (no reassociation without fast-math) do block vectorisation and reordering
**[inference, high]**. But C has `restrict` and type-based alias rules. Hearth's INV-DET-3
*deliberately* keeps the strict-FP constraint (canonical FP order, no FMA contraction), so
"C leaves throughput on the table" partly reflects a choice Hearth made on purpose.

**B2, don't target LLVM IR.** Misleading. LLVM IR is portable, but LLVM's backend carries
per-CPU scheduling models with ports, latencies and throughputs. llvm-mca exists to analyse
code against them ([llvm-mca](https://llvm.org/docs/CommandGuide/llvm-mca.html)). The kernel of
truth: mainstream models lag new silicon. On LLVM `main`, `znver5` still reuses
`Znver4Model` ([X86.td](https://raw.githubusercontent.com/llvm/llvm-project/main/llvm/lib/Target/X86/X86.td)).
So measured, per-machine cost models (uops.info-style) are a real gap, but it's a cost-model
gap, not a reason to abandon an SSA IR.

**B3, RL on cycle timings.** Mostly-true. This is an active research direction:
- AlphaDev rewarded correctness and speed. It found sort3–5 routines up to 70% faster on short
  inputs, which went into LLVM libc++, and a 9–16-byte hash 30% faster, which went into Abseil
  ([DeepMind](https://deepmind.google/discover/blog/alphadev-discovers-faster-sorting-algorithms/)).
- SuperCoder (2025, v4 Aug 2026) trained Qwen2.5-Coder-7B with RL on a correctness-plus-speedup
  reward over 8,072 assembly programs. It reached 95.0% correctness and 1.46× average speedup
  over gcc -O3; Claude Opus 4 reached 51.5% and 1.43×
  ([arXiv 2505.11480](https://arxiv.org/abs/2505.11480)).

  The 5% incorrect rate is why an equivalence checker must gate any result.

**B4, `line64` and streaming stores.** True. MOVNTI and VMOVNTPS exist and are the standard
lowering for non-temporal writes **[inference, high]**. Zen 5 nuance: 512-bit stores run at
half the throughput of 256-bit stores ([Agner §25.8–25.9](https://www.agner.org/optimize/microarchitecture.pdf)).
For decode, weights are *read*, so NT stores mostly matter for KV-cache or activation writes
**[inference]**.

**B5, no pointers / affine strides.** Mostly-true for static-control code. The polyhedral model
covers affine loop nests ([Pluto, PLDI 2008](https://doi.org/10.1145/1375581.1375595)). MoE
routing is data-dependent, so expert selection is not affine. Mithril needs a non-affine
escape (indirect slab tables) with explicit disjointness proofs **[inference, high]**.

**B6, vectorisation "mathematically guaranteed".** Misleading. A language can guarantee that
it *emits* vector code, as SPMD languages do. It cannot guarantee a speedup when the work is
gathers, cross-lane reductions or memory-bound streams **[inference, high]**. On Zen 5,
gathers are much slower than contiguous loads (see C5).

**B7, branch-entropy primitives.** Mostly-true. Agner Fog measures 15–18 cycles on Zen 4 and
15–25 on Zen 5, and gives Zen 1–3 an average of about 18
([Agner manual, branch prediction chapter](https://www.agner.org/optimize/microarchitecture.pdf)).
Caveats:
- Branch entropy is data-dependent and generally not knowable at compile time. It needs
  profiling or annotation **[inference, high]**.
- Zen 5 predicts very well: it looks two branches ahead and fully predicts loops up to 128
  iterations (Agner §25.15). That shrinks the payoff.

**B8, pipeline ending in an Alive2-style check.** Mostly-true with a correction:
- Alive2 validates **LLVM IR** transformations only, not x86 machine code
  ([Alive2 README](https://raw.githubusercontent.com/AliveToolkit/alive2/master/README.md);
  [PLDI'21](https://doi.org/10.1145/3453483.3454030)).
- STOKE's x86 validator supports only a subset of instructions, GPRs and ymm0–15, and no
  AVX-512. STOKE is unmaintained
  ([STOKE README](https://raw.githubusercontent.com/StanfordPL/stoke/develop/README.md);
  [ASPLOS'13](https://doi.org/10.1145/2451116.2451150)).

So an AVX-512 equivalence checker is something Mithril would have to build or extend.

**B9, MCTS replaces -O3.** Misleading. The evidence covers short, hot kernels: AlphaDev's
sort3–5 and SuperCoder's programs averaging about 130 lines. Nothing shows whole-program
replacement **[inference, high]**.

**B10, P-core/E-core dual paths.** Misleading for this project:
- The 9950X has no E-cores. Desktop Granite Ridge uses only full Zen 5 cores with the full
  512-bit datapath ([Zen 5](https://en.wikipedia.org/wiki/Zen_5)).
- On Intel hybrid parts, AVX-512 is disabled or fused off so P and E cores expose a common
  ISA. Thread Director only *hints* to the scheduler ([Alder Lake](https://en.wikipedia.org/wiki/Alder_Lake)).
- Per-core-type code therefore needs hard affinity, and the OS can still migrate a thread
  mid-function **[inference, high]**.

**B11, benchmark harness.** Mostly-true, with errors:
- WBINVD (and INVD) are CPL-0 only, so user space can't use them
  ([WBINVD](https://www.felixcloutier.com/x86/wbinvd)). CLFLUSH and CLFLUSHOPT work at any
  privilege level ([CLFLUSH](https://www.felixcloutier.com/x86/clflush)).
- RDTSC is not serializing. LFENCE before and after it is the documented way to order it
  ([RDTSC](https://www.felixcloutier.com/x86/rdtsc)). On modern parts the TSC ticks at a
  constant reference rate, so core cycles need the PMU **[inference, high]**.
- Top-Down analysis is Intel's method
  ([Yasin, ISPASS 2014](https://doi.org/10.1109/ISPASS.2014.6844459)). AMD exposes an
  analogous pipeline-utilisation breakdown (unverified in this pass).
- isolcpus/taskset are Linux-only, while Hearth's primary box runs Windows 11.

**B12, next steps.** Mostly-true. Use measured tables (uops.info has Zen 5 columns, as quoted
throughout this file) alongside Agner Fog. SuperCoder already follows the intent→asm-with-
validation pattern.

### F-C. "Reality check" claims (C1–C8)

**C1, roofline and about 100 GB/s.** Mostly-true:
- The 9950X officially supports dual-channel DDR5-5600
  ([Zen 5](https://en.wikipedia.org/wiki/Zen_5)), which is 89.6 GB/s theoretical
  **[inference: 2 ch × 8 B × 5600 MT/s]**.
- Chips and Cheese cites 96 GB/s theoretical at DDR5-6000 and about 64 GB/s read per CCD
  over Infinity Fabric. Single-CCD decode cannot saturate DRAM
  ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).

**C2, dense GEMM at 90–98% of peak.** Mostly-true for tuned libraries on their target CPU, not
universally. BLIS's own performance notes call MKL "dismal" on Zen 1 and "underwhelming" on
Zen 2 ([BLIS Performance.md](https://raw.githubusercontent.com/flame/blis/master/docs/Performance.md)).
I did not verify the exact percentages here.

**C3, "60–90% wasted compute".** Misleading and unsourced. For batch-1 decode, low FLOP
utilisation is set by the memory roofline, not by waste a compiler can recover. Hearth's own
physics model states this (brief) **[inference, high]**.

**C4, whole-layer fusion.** Mostly-true for prefill and batched GEMM. For batch-1 decode, the
activation vector is a few KB (e.g., 2048 floats). Intermediate activation writes already stay
in L1/L2, while traffic is dominated by weight bytes. Fusion therefore saves little in decode
**[inference, high]**.

**C5, VGATHER/VSCATTER.** Misleading. uops.info measures zmm `VPGATHERDD` at:

| CPU | Reciprocal throughput | µops |
|---|---|---|
| Zen 4 | 16.6 cycles | 81 |
| Zen 5 | 12.6 cycles | 64 |
| Alder Lake-P | 5.75 cycles | — |

([uops.info](https://uops.info/html-instr/VPGATHERDD_ZMM_K_VSIB_ZMM.html)). Zen 5 can do two
512-bit loads per cycle (Agner §25.8), so one gather costs about as much as 25 contiguous
64-byte loads **[inference]**. On Intel, the Gather Data Sampling microcode mitigation also
affects gathers; Intel did not quantify the impact on the advisory page
([Intel GDS](https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/advisory-guidance/gather-data-sampling.html)).
Block-sparse is the right idea; element gathers are the wrong default.

**C6, low-bit primitive types lowering to popcount/BMI2/VNNI.** Misleading in mechanism, right
in spirit:
- bitnet.cpp uses **TL** kernels (lookup tables over 2 or 3 weight groups, about 1.67 bpw for
  TL2) and **I2_S** (2-bit codes with an int8 path). It reports up to 6.25× over full
  precision and 2.32× over low-bit baselines
  ([arXiv 2502.11880](https://arxiv.org/abs/2502.11880); [arXiv 2410.16144](https://arxiv.org/pdf/2410.16144)).
- T-MAC precomputes partial sums into LUTs and uses `tbl`/`pshuf`, avoiding both FMA and
  dequantisation ([T-MAC](https://raw.githubusercontent.com/microsoft/T-MAC/main/README.md)).
- VNNI is a fair target: zmm `VPDPBUSD` runs at 0.5 c reciprocal throughput on Zen 5
  ([uops.info](https://uops.info/html-instr/VPDPBUSD_ZMM_ZMM_ZMM.html)).
- Popcount computes binary (±1 × ±1) dot products. With int8 activations it needs bit-serial
  decomposition, which loses to LUT/VNNI **[inference, medium-high]**.

**C7, prefetch "dozens of iterations ahead", DRAM about 200 cycles.** Misleading:
- The 9950X measures just over 70 ns DRAM latency
  ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)), about
  400 cycles at 5.7 GHz **[inference]**.
- Agner's Zen 5 chapter says hardware prefetching usually beats explicit software prefetch
  (§25.16).
- Software prefetch earns its place for data-dependent addresses (the next expert's slab),
  not for streams **[inference, high]**.

**C8, unified host/device binary.** Unverifiable as stated. It's a design aspiration with
precedents in single-source CUDA, SYCL and Mojo **[inference]**.

### F-D. Claimed gains (D1–D7)

**D1, 80B MoE: about 45 GB at 4-bit, 16–18 GB at 1.58 bits.** The arithmetic is mostly-true:
- At 4.5 bpw, 80e9 × 4.5 / 8 = 45 GB.
- At 1.58 bpw it is 15.8 GB; real packings come to 16.7 GB (TL2, 1.67 bpw) or 20 GB (I2_S,
  2 bpw) **[inference]**.
- The catch: BitNet-class quality comes from **native ternary training**. BitNet b1.58 2B4T
  was trained natively on 4T tokens ([arXiv 2504.12285](https://arxiv.org/abs/2504.12285)).
- No 80B ternary-native MoE is known to me (unverified). "1.58-bit" community quants of
  existing models are mixed-precision, not pure ternary. Unsloth's DeepSeek-R1 UD-IQ1_S is
  131 GB, with down_proj at mixed 2.06/1.56 bits
  ([HF card](https://huggingface.co/unsloth/DeepSeek-R1-GGUF)).

**D2, 300B+ in 64–128 GB without paging.** Misleading:
- 300e9 × 2 bpw = 75 GB, which fits 128 GB but not 64 GB, and needs a ternary-trained 300B
  model **[inference]**.
- Hearth already runs a 1T-shaped container out of core, so "without paging" is the wrong
  goal. Paging is Hearth's thesis.

**D3, speed-up table.** Likely-fabricated: no sources, and the rows conflict with rooflines.
Real anchors:

| Setup | Hardware | Prefill / decode | Source |
|---|---|---|---|
| KTransformers, DeepSeek-V3 Q4 | dual Xeon Gold 6454S + one 4090D | 97 / 13.7 tok/s | [tutorial](https://raw.githubusercontent.com/kvcache-ai/ktransformers/main/doc/en/DeepseekR1_V3_tutorial.md) |
| llama.cpp, same setup | same | 10.3 / 4.5 tok/s | same |
| KTransformers v0.2.1 | same CPU + 4090 | about 15.9 tok/s decode | same |
| Hearth, Qwen3-30B-A3B Q4 | 9950X, CPU only | 19–22 tok/s decode | brief (noisy) |
| llama.cpp, same model | same | about 25 tok/s decode | brief (noisy) |

Row-by-row problems:
- **CPU-only "100B MoE 1–2 tok/s".** This baseline is pessimistic for sparse models.
  gpt-oss-120b has 117B total / 5.1B active parameters with MXFP4 experts
  ([HF](https://huggingface.co/openai/gpt-oss-120b)). That is roughly 3 GB per token, giving
  a roofline near 20+ tok/s at about 70 GB/s effective **[inference, medium]**.
- **"VRAM-resident 8x7B 85–130 tok/s".** Mixtral has 13B active parameters
  ([arXiv 2401.04088](https://arxiv.org/abs/2401.04088)), about 7 GB per token at 4 bits. That
  gives about 145 tok/s on a 1 TB/s GPU, and the 4-bit model does not fit in 24 GB. The claim
  sits at the roofline, so a language cannot add 2× there **[inference, medium]**.

**D4, speculative DMA hides 70–85%.** Unverifiable:
- Hearth measured one-layer-ahead prefetch arriving late about 70% of the time when NVMe-bound
  (brief).
- When storage bandwidth is the bottleneck, overlap cannot hide transfer time, because hiding
  latency is not adding bandwidth **[inference, high]**.
- Prior systems report gains from trace-guided caching and prefetch: MoE-Infinity reports
  3.1–16.7× per-token latency gains over named baselines
  ([arXiv 2401.14361](https://arxiv.org/abs/2401.14361)). Pre-gated MoE co-designs the gate to
  enable prefetch ([arXiv 2308.12066](https://arxiv.org/abs/2308.12066)). Neither establishes
  "70–85%".

**D5, VPOPCNTDQ replaces FMAs.** Misleading (see C6). On Zen 5, `VPOPCNTQ zmm` and
`VPDPBUSD zmm` both measure 0.5 c reciprocal throughput
([popcnt](https://uops.info/html-instr/VPOPCNTQ_ZMM_ZMM.html),
[vpdpbusd](https://uops.info/html-instr/VPDPBUSD_ZMM_ZMM_ZMM.html)), so port pressure is no
argument for popcount. Decode is memory-bound in any case.

**D6, IPC 0.8–1.4 → 2.6–3.8; stalls 35% → <8%; power −40–60%.** Likely-fabricated: no
measurement or hardware is given:
- Zen 5's ceiling is 8 IPC, with about 6 typical in Agner's single-thread tests (§25.1, §25.21).
- High IPC in a memory-bound decode loop would mean the CPU is doing work other than waiting
  on DRAM.
- The only nearby real data point: T-MAC reports 0.66 J/token versus llama.cpp CPU's 2.12 on
  Jetson AGX Orin (ARM) ([T-MAC](https://raw.githubusercontent.com/microsoft/T-MAC/main/README.md)).
  That shows the direction can be real on other hardware; it is not evidence for these numbers.

**D7, 15–20+ tok/s out-of-core 100B+ MoE on a desktop.** Unverifiable and highly
configuration-dependent **[inference]**:
- With about 7 GB/s NVMe, 15 tok/s allows at most about 0.47 GB per token from storage.
- A model with 5 GB of active expert bytes per token at a 90% DRAM hit rate still pulls
  0.5 GB from NVMe. That gives roughly 7 tok/s once the DRAM term is added.
- 15–20 tok/s needs a hit rate of about 97% or more, or about 2–3 GB of active bytes.
- Hearth's Kimi-K2-shaped run is at 1.2–1.8 s/token.

### F-E. Visual generation (E1–E8)

- **E1.** Mostly-true concept with a field error:
  - 3DGS uses degree-3 spherical harmonics, i.e. 3 × 16 = **48** coefficients per Gaussian, not
    `vec16` ([reference code](https://raw.githubusercontent.com/graphdeco-inria/gaussian-splatting/main/scene/gaussian_model.py)).
  - Real-time 1080p (≥30 fps) 3DGS is a GPU result
    ([arXiv 2308.04079](https://arxiv.org/abs/2308.04079)).
  - The cited "4DGS" (Wu et al., CVPR 2024) uses 3D Gaussians plus 4D neural voxels and a
    deformation MLP. It reaches 82 FPS at 800×800 on an RTX 3090
    ([arXiv 2310.08528](https://arxiv.org/abs/2310.08528)).
- **E2.** Mostly-true: flow-matching samplers are ODE solvers. Distillation to 1–4 steps
  reduces the value of fused RK step caches **[inference]**.
- **E3.** Misleading. 4×8×8 is the *VAE* compression ratio (Wan-VAE). The DiT patch is
  1×2×2 ([Wan, arXiv 2503.20314](https://arxiv.org/html/2503.20314v2)).
- **E4.** Misleading. The redundancy that is exploited lies *across denoising steps*:
  - FORA caches attention/MLP outputs across steps
    ([arXiv 2407.01425](https://arxiv.org/abs/2407.01425)).
  - Δ-DiT: about 1.6× at 20 steps ([arXiv 2406.01125](https://arxiv.org/abs/2406.01125)).
  - TeaCache: up to 4.41× ([arXiv 2411.19108](https://arxiv.org/abs/2411.19108)).
  - PAB: up to 10.5×, from a U-shaped attention-difference pattern
    ([arXiv 2408.12588](https://arxiv.org/abs/2408.12588)).
  
  A 70% FLOP cut is within that range, but "90% frame-to-frame" and CMOV-level skipping are
  unsupported. Skipping happens at whole-block granularity **[inference, high]**.
- **E5.** Unverifiable, and likely infeasible at stated resolutions **[inference]**. Wan-1.3B
  at 480p uses about 32.8k tokens × 1536 hidden, roughly 100 MB of bf16 residual stream. That
  is above one CCD's 32 MB L3.
- **E6.** Misleading for this machine: there are no E-cores (B10).
- **E7.** Mostly-true technically, but Linux DRM/KMS only, and irrelevant on Windows
  **[inference]**.
- **E8.** Likely-fabricated for consumer CPUs. State of the art in 2025–26:
  - Self Forcing: about 16 FPS at 480p on one H100 and about 10 FPS on an RTX 4090
    ([project](https://self-forcing.github.io/)).
  - Wan2.1-1.3B: about 4 min for a 5-s 480p clip on a 4090
    ([Wan README](https://raw.githubusercontent.com/Wan-Video/Wan2.1/main/README.md)).
  - StreamDiffusion: 91 fps, but image-to-image on a 4090
    ([arXiv 2312.12491](https://arxiv.org/abs/2312.12491)).

### F-F. The openai/math repository (F1–F6)

I searched thoroughly and the repository exists:
- Created 2026-10-06T21:47Z, last pushed 2026-10-08, Apache-2.0, about 13.9k stars
  ([GitHub API](https://api.github.com/repos/openai/math)).
- Its README describes manuscripts "produced by an internal OpenAI model" from roughly 4,000
  posed problems, at about three hours of ChatGPT Pro thinking compute per result.
- It catalogues 719 manuscripts in 372 families. Results are "at different stages of
  verification" and not all are formalised ("~42%")
  ([README](https://raw.githubusercontent.com/openai/math/main/README.md)).
- Third-party trackers quoted 722 manuscripts at launch
  ([lean-genius issue](https://github.com/rjwalters/lean-genius/issues/43839)).
- The Lean toolchain is `leanprover/lean4:v4.34.1`
  ([lean-toolchain](https://raw.githubusercontent.com/openai/math/main/lean/lean-toolchain)).

**Comparator** is not an openai/math harness. It is `leanprover/comparator` (created
2025-06), a "trustworthy judge" with these properties:
- It checks that a `Solution` module proves the *same theorem statements* as a trusted
  `Challenge` module.
- Only whitelisted axioms are permitted.
- Checking runs under the `landrun` sandbox, with an optional second kernel (nanoda)
  ([Comparator README](https://raw.githubusercontent.com/leanprover/comparator/master/README.md);
  [openai/math Comparator instructions](https://raw.githubusercontent.com/openai/math/main/lean/ComparatorChallenges/README.md)).

The family claims, checked against the catalogue
([overview.pdf](https://raw.githubusercontent.com/openai/math/main/overview.pdf), dated
October 6, 2026):

| Seed says | Catalogue says | Verdict |
|---|---|---|
| 087 = SDP thresholds / approximation algorithms | 087 = "The Mahler conjectures and symplectic width" | false |
| (SDP family) | 102 = "The Unique Games Conjecture and optimal approximation thresholds", a *hardness* result; 095, 117 and 126 also involve semidefinite lifts and gaps | — |
| 197 = Mézard–Parisi | 197 = "Nonsofic groups and group-ring counterexamples" (Kaplansky direct finiteness) | false |
| (Mézard–Parisi) | 221 = "The Mézard–Parisi formula for diluted spin glasses" | — |
| ODE bounds for RK solvers | No ODE or numerical-analysis discipline; the closest are "Dynamical systems and ergodic theory" and "Partial differential equations" | likely-fabricated |

Treat the catalogue's headline claims with care. It claims proofs of the Unique Games
Conjecture and L = RL = BPL, and the repo itself warns that results are at different
verification stages.

Even if the 102 results hold, they are NP-hardness-of-approximation theorems. They say
near-optimal approximation is hard; they give no allocator. Register allocation via
graph colouring is the classic NP-hard formulation
([Chaitin et al. 1981](https://doi.org/10.1016/0096-0551(81)90048-5)). "Zero stack spills" is
impossible whenever live values exceed the 16 GPRs or 32 zmm registers **[inference, high]**.

The "duality" between spin-glass free energy and MoE routing or L3-slice partitioning (F4) is
a metaphor with no published basis that I could find. Software cannot choose L3 slices
**[inference, medium-high]**. Family 124 (three-machine unit-job scheduling with precedence
constraints) is the only scheduling result. It concerns makespan on identical machines, not
port scheduling.

F2/F6: Lean *can* host verification, but nothing in openai/math formalises x86 or tensor
semantics. Lean does not "replace" SMT solvers. Lean 4 itself ships `bv_decide`, a bit-blaster
that calls a SAT solver and checks its LRAT certificate
([BVDecide.lean](https://raw.githubusercontent.com/leanprover/lean4/master/src/Std/Tactic/BVDecide.lean)),
so the two are complementary. Mathlib already has ODE theory such as Picard–Lindelöf
([mathlib docs](https://leanprover-community.github.io/mathlib4_docs/Mathlib/Analysis/ODE/PicardLindelof.html)).

### F-G. Projects to study (G1–G2)

All eight G1 repos exist (GitHub API, checked 2026-10-11): google/souper, StanfordPL/stoke,
AliveToolkit/alive2, openai/triton (now redirects to triton-lang/triton), tile-ai/tilelang,
spdk/spdk, andikleen/pmu-tools and asmjit/asmjit. STOKE is explicitly unmaintained
([README](https://raw.githubusercontent.com/StanfordPL/stoke/develop/README.md)). Souper and
Alive2 operate on LLVM IR. SPDK documents Linux and FreeBSD builds only
([SPDK README](https://raw.githubusercontent.com/spdk/spdk/master/README.md)); a separate
`wpdk/wpdk` repo exists for Windows, maturity unverified. User-space PCIe BAR access needs
VFIO/UIO-style drivers, which is not available to a Windows user process **[inference, high]**.
The G2 references are real: Pluto, MLIR affine and Yasin's Top-Down method.

### F-H. Go-to-market (H1–H7)

- **H1.** "IPC 1.1 → 3.2" is an invented demo number (likely-fabricated). `curl | bash` is also
  a supply-chain anti-pattern **[inference]**.
- **H2.** True and sound. Hearth already exposes a C ABI (`hearth.h`).
- **H3.** Mostly-true as a recommendation.
- **H4.** Mostly-true. llms.txt is an informal *proposal* (Jeremy Howard, 2024-09-03; v2
  updated 2026-08-10). Evidence of consumption is mainly on-demand fetches by agents and tools.
  `llms-full.txt` is not part of the spec page ([llmstxt.org](https://llmstxt.org/)).
- **H5.** True. There is precedent for machine-readable diagnostics, e.g. GCC's SARIF output
  formats ([GCC docs](https://gcc.gnu.org/onlinedocs/gcc/Diagnostic-Message-Formatting-Options.html)).
- **H6.** Misleading and risky. GitHub's Acceptable Use Policies ban coordinated inauthentic
  activity and excessive automated bulk activity
  ([GitHub AUP](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)).
  Seeding synthetic repos to sway training data is the kind of thing those rules target.
  Better: good in-context docs, llms.txt, an MCP/LSP server, and real example programs.
- **H7.** Misleading on two counts:
  - **Mojo does support inline assembly** via `inlined_assembly`
    ([Mojo stdlib](https://github.com/modular/modular/blob/main/Mojo/stdlib/std/sys/_assembly.mojo)).
  - Every capability on the list exists somewhere:
    - Exo: user-schedulable hardware targeting ([PLDI'22](https://doi.org/10.1145/3519939.3523446)).
    - Jasmin: an assembly-level language with verified compilation
      ([CCS'17](https://doi.org/10.1145/3133956.3134078)).
    - STOKE and SuperCoder: superoptimisation.
    - TileLang and Triton: tile kernels.
  - Nobody has combined them, which makes the scope a risk as much as an opportunity
    **[inference]**.

### F-I. "Living tissue" (I1–I8)

- **I1.** Mostly-true. ROME and MEMIT are closed-form rank-one and rank-k editors.
  - AlphaEdit (ICLR 2025) projects each update onto the null space of preserved keys K₀. It
    computes this by SVD of K₀K₀ᵀ, dropping eigenvectors with eigenvalue > 1e-2.
  - K₀ is estimated from about 100k Wikipedia triples.
  - Tests ran to 2,000–3,000 sequential edits, with an average 36.7% boost over
    locate-then-edit baselines
    ([AlphaEdit HTML](https://arxiv.org/html/2410.02355v4);
    [ICLR](https://proceedings.iclr.cc/paper_files/paper/2025/hash/29c8c615b3187ee995029284702d3f43-Abstract-Conference.html)).
  - Without projection, sequential ROME/MEMIT edits degrade gradually, then collapse
    catastrophically ([Gupta et al.](https://arxiv.org/abs/2401.07453)).
- **I2.** Unverifiable and speculative. MoE routers are linear top-k layers. The closest
  precedent for retrieval-style routing is PEER, which uses product-key retrieval over a
  million tiny experts ([arXiv 2407.04153](https://arxiv.org/abs/2407.04153)).
- **I3.** Unverifiable and speculative. "Stem-cell" expert growth is a research idea, not an
  established method.
- **I4.** False:
  - Exact verification of ReLU networks is NP-complete, and Reluplex scaled to ACAS-Xu-sized
    networks ([arXiv 1702.01135](https://arxiv.org/abs/1702.01135);
    [CAV'17](https://doi.org/10.1007/978-3-319-63387-9_5)).
  - Loss divergence depends on the data distribution, not only the program.
  - The DGM explicitly swapped Gödel-machine proofs for empirical benchmark validation, run in
    a sandbox with human oversight ([arXiv 2505.22954](https://arxiv.org/abs/2505.22954)).
- **I5.** False. See the Summary for the measured numbers. CMPXCHG8B is the 8-byte form, which
  only matters for 32-bit code. At token timescales (tens of ms), atomic cost is irrelevant;
  safe memory reclamation is the real problem **[inference, high]**.
- **I6.** False. Orthogonal or null-space methods *mitigate* forgetting:
  - OWM claims to "overcome" forgetting, but within the null space it can still represent
    ([OWM](https://arxiv.org/abs/1810.01256)).
  - GPM says it "mitigates" forgetting ([GPM](https://arxiv.org/abs/2103.09762)).
  - The null space shrinks as tasks accumulate **[inference, high]**.
  
  "At the machine-code level" is a category error: projection is linear algebra on the update,
  whatever code computes it.
- **I7.** False:
  - INVD is CPL-0 and discards modified lines
    ([INVD](https://www.felixcloutier.com/x86/invd)).
  - The documented cross-modifying-code protocol in SDM §8.1.3 is: write the code, publish a
    flag, have each executing thread run a serializing instruction (e.g. CPUID), then jump.
    Xen and OpenJDK both adopted explicit serialization
    ([Xen 2025](https://lists.xen.org/archives/html/xen-changelog/2025-07/msg00562.html);
    [OpenJDK 8220351](https://mail.openjdk.org/pipermail/hotspot-dev/2019-March/037296.html)).
  - On Windows the API is `FlushInstructionCache`.
  - For token-boundary hot-swap, function-pointer indirection avoids self-modifying code
    entirely **[inference, high]**.
- **I8.** Unverifiable. It is a vision statement.

---

## Implications for Mithril

1. **Make the cost model a measured artifact, not a belief.** The seed's numbers fail because
   they were never measured. Mithril should ship per-microarchitecture tables (uops.info-style)
   and treat any performance claim without a hardware tag as a compile warning. This mirrors
   Hearth's INV-HONEST. LLVM's `znver5` reusing the Zen 4 model shows the gap is real.
2. **Verification follows the Comparator pattern, not "replace SMT".** Use a trusted
   specification module and an untrusted implementation, with an axiom whitelist and a sandbox.
   This maps directly onto spec-vs-superoptimised-kernel checking. Bit-level obligations can go
   to SAT/SMT with certificates (`bv_decide`-style). An AVX-512 x86 semantics is the missing
   piece and a major work item, since STOKE stops at ymm and Alive2 stops at LLVM IR.
3. **Low-bit types are primitives, and their lowering is chosen per target.** Lower to
   LUT/shuffle or VNNI, as T-MAC and bitnet.cpp do, and not to popcount. Never lower sparsity to
   element gathers by default on AMD.
4. **Drop "guaranteed" language** around vectorisation, forgetting, loss bounds and spills.
   Mithril can guarantee *emission* properties and *equivalence* to a spec. It cannot
   guarantee performance or learning outcomes.
5. **Self-modification goes through indirection plus OS APIs**: W^X remapping, then
   `FlushInstructionCache` or `mprotect`, then serialization. Mithril's `hot_patch` should be
   an atomic pointer publish with epoch-based reclamation.
6. **Drop P/E dual paths.** Instead, target ISA levels (AVX2, AVX-512, AVX10) with runtime
   dispatch, which Hearth already does.

## Implications for Hearth

1. **Decode is roofline-bound. Gains come from bytes, not instructions.** Lower-bit cold
   experts (an open Hearth item) are the realistic version of D1. The kernel family to use is
   T-MAC/bitnet-style LUT with `vpshufb`, which must keep INV-DET-3 bit-exactness across
   scalar, AVX2 and AVX-512. Integer LUT accumulation helps here because it is order-exact if
   int32 never overflows **[inference]**.
2. **Use both CCDs for decode.** One CCD reads about 64 GB/s over Infinity Fabric, below the
   DRAM peak.
3. **Software prefetch only for data-dependent next-expert addresses.** Leave streaming to the
   hardware prefetcher (Agner §25.16).
4. **Verify the D3/D7 numbers against Hearth's physics model.** Any target such as
   "15–20 tok/s out of core" should come with an explicit hit rate and active-bytes budget.
5. **Treat the KTransformers DeepSeek-V3 rows as the external anchor** for hybrid offload
   (13.7–15.9 tok/s decode on dual Xeon + one 4090). The clean llama.cpp head-to-head on the
   9950X remains the key local anchor.

## Where the seed discussion is right or wrong

**Right (keep):**
- B3/B12: RL or LLM superoptimisation gated by verification. SuperCoder and AlphaDev validate
  this.
- B4: hardware-surfacing types.
- B5: alias-free affine regions.
- B7: entropy-aware branch lowering, with profiling.
- B8: a superoptimiser → equivalence check → emit pipeline.
- C1/C2: the roofline honesty.
- C6: low-bit primitives in spirit.
- C7: async memory pipelines.
- G1/G2: the reading list.
- H2/H5: FFI and JSON diagnostics.
- I1: AlphaEdit-style null-space editing as a mechanism.

**Wrong (drop or fix):**
- I7: INVD/CLFLUSH.
- I5: single-cycle CMPXCHG.
- I4: SMT loss guarantees.
- I6: forgetting "eliminated".
- F3/F4/F5: wrong family numbers and invented content.
- B10/E6: E-cores on a 9950X.
- C5: gather as the sparsity primitive.
- C6/D5: popcount ternary.
- C7: 200 cycles.
- E3: a VAE ratio presented as attention tiles.
- E4: frame-to-frame instead of step-to-step redundancy.
- H6: synthetic repos.
- H7: "Mojo can't do asm".

**Invented numbers:** D3, D6, E8 and H1. D4 and D7 cannot be verified.

### Verdict table (one row per claim)

| ID | Verdict | Correction / nuance | Key source |
|---|---|---|---|
| A1 | mostly-true | Microcode is signed/patched; most µops come from hard-wired decoders; HDL is not reachable | [Agner](https://www.agner.org/optimize/microarchitecture.pdf) |
| B1 | mostly-true | restrict/TBAA exist; strict FP is also a deliberate Hearth choice (INV-DET-3) | [inference] |
| B2 | misleading | LLVM has per-CPU scheduling models; real gap: znver5 reuses Znver4Model | [X86.td](https://raw.githubusercontent.com/llvm/llvm-project/main/llvm/lib/Target/X86/X86.td) |
| B3 | mostly-true | Already done: AlphaDev; SuperCoder 1.46× vs -O3 at 95% correct | [2505.11480](https://arxiv.org/abs/2505.11480) |
| B4 | true | MOVNTI/VMOVNTPS exist; Zen 5 512-bit stores at half rate | [Agner](https://www.agner.org/optimize/microarchitecture.pdf) |
| B5 | mostly-true | Holds for affine code; MoE routing is non-affine | [Pluto](https://doi.org/10.1145/1375581.1375595) |
| B6 | misleading | Emission guaranteed, speedup not | [inference] |
| B7 | mostly-true | Zen 4: 15–18, Zen 5: 15–25 cycles; entropy needs profiling | [Agner](https://www.agner.org/optimize/microarchitecture.pdf) |
| B8 | mostly-true | Alive2 is LLVM-IR only; STOKE validator has no AVX-512 | [Alive2](https://raw.githubusercontent.com/AliveToolkit/alive2/master/README.md) |
| B9 | misleading | Evidence covers small kernels only | [DeepMind](https://deepmind.google/discover/blog/alphadev-discovers-faster-sorting-algorithms/) |
| B10 | misleading | 9950X has no E-cores; hybrid ISA is equalised; OS migrates threads | [Alder Lake](https://en.wikipedia.org/wiki/Alder_Lake) |
| B11 | mostly-true | WBINVD is ring-0; TMA is Intel; RDTSC is reference-rate; isolcpus is Linux-only | [WBINVD](https://www.felixcloutier.com/x86/wbinvd) |
| B12 | mostly-true | Prefer measured uops.info tables | [uops.info](https://uops.info/html-instr/VPDPBUSD_ZMM_ZMM_ZMM.html) |
| C1 | mostly-true | 89.6–96 GB/s theoretical; about 64 GB/s read per CCD | [C&C](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop) |
| C2 | mostly-true | Holds on tuned targets; MKL is weak on early Zen | [BLIS](https://raw.githubusercontent.com/flame/blis/master/docs/Performance.md) |
| C3 | misleading | Unsourced; decode utilisation is set by the roofline | [inference] |
| C4 | mostly-true | Helps prefill/batched; little gain in batch-1 decode | [inference] |
| C5 | misleading | Zen 5 zmm gather: 64 µops, about 12.6 c | [uops.info](https://uops.info/html-instr/VPGATHERDD_ZMM_K_VSIB_ZMM.html) |
| C6 | misleading | SOTA uses LUT or VNNI, not popcount | [bitnet.cpp](https://arxiv.org/abs/2502.11880) |
| C7 | misleading | About 70 ns ≈ 400 cycles; hardware prefetch usually wins | [C&C](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop) |
| C8 | unverifiable | Aspiration; CUDA/SYCL/Mojo are precedents | [inference] |
| D1 | mostly-true | Arithmetic is OK (16.7–20 GB real); needs a ternary-trained model | [2504.12285](https://arxiv.org/abs/2504.12285) |
| D2 | misleading | 300B×2 bpw = 75 GB; no such model; paging is Hearth's thesis | [inference] |
| D3 | likely-fabricated | Unsourced; conflicts with rooflines and KTransformers/llama.cpp data | [KT](https://raw.githubusercontent.com/kvcache-ai/ktransformers/main/doc/en/DeepseekR1_V3_tutorial.md) |
| D4 | unverifiable | Overlap cannot hide storage-bandwidth limits; Hearth sees 70% late | [2401.14361](https://arxiv.org/abs/2401.14361) |
| D5 | misleading | VPOPCNTQ and VPDPBUSD are both 0.5 c on Zen 5 | [uops.info](https://uops.info/html-instr/VPOPCNTQ_ZMM_ZMM.html) |
| D6 | likely-fabricated | No measurement; high IPC contradicts memory-bound decode | [Agner](https://www.agner.org/optimize/microarchitecture.pdf) |
| D7 | unverifiable | Needs ≥97% hit rate or ≤3 GB active bytes per token | [inference] |
| E1 | mostly-true | SH is 48 coefficients, not 16; real-time 3DGS is a GPU result | [3DGS code](https://raw.githubusercontent.com/graphdeco-inria/gaussian-splatting/main/scene/gaussian_model.py) |
| E2 | mostly-true | Flow-matching samplers are ODE solvers; distillation reduces steps | [inference] |
| E3 | misleading | 4×8×8 is the VAE ratio; DiT patch is 1×2×2 | [Wan](https://arxiv.org/html/2503.20314v2) |
| E4 | misleading | Redundancy is across steps (FORA, Δ-DiT, TeaCache, PAB), not frames | [PAB](https://arxiv.org/abs/2408.12588) |
| E5 | unverifiable | Residual stream of about 100 MB exceeds a 32 MB L3 | [inference] |
| E6 | misleading | No E-cores on the target | [Zen 5](https://en.wikipedia.org/wiki/Zen_5) |
| E7 | mostly-true | Linux-only; not applicable to Windows | [inference] |
| E8 | likely-fabricated | SOTA is about 16 FPS at 480p on an H100 | [Self Forcing](https://self-forcing.github.io/) |
| F1 | mostly-true | 719 (722 at launch) manuscripts, 372 families, Lean v4.34.1, ~42% formalised; Comparator is leanprover's tool | [README](https://raw.githubusercontent.com/openai/math/main/README.md) |
| F2 | misleading | No x86 or tensor semantics in the repo; the Comparator pattern is reusable | [Comparator](https://raw.githubusercontent.com/leanprover/comparator/master/README.md) |
| F3 | false | 087 is Mahler; the SDP family (102) is hardness; zero spills is impossible in general | [overview](https://raw.githubusercontent.com/openai/math/main/overview.pdf) |
| F4 | false | 197 is Kaplansky; Mézard–Parisi is 221; "duality" is unsupported | [overview](https://raw.githubusercontent.com/openai/math/main/overview.pdf) |
| F5 | likely-fabricated | No ODE/numerical family; mathlib has ODE basics | [overview](https://raw.githubusercontent.com/openai/math/main/overview.pdf) |
| F6 | misleading | Lean and SMT are complementary (bv_decide) | [BVDecide](https://raw.githubusercontent.com/leanprover/lean4/master/src/Std/Tactic/BVDecide.lean) |
| G1 | true | All repos exist; triton moved; STOKE is unmaintained | [GitHub API](https://api.github.com/repos/StanfordPL/stoke) |
| G2 | mostly-true | Real references; SPDK/BAR access is Linux/FreeBSD-centric | [SPDK](https://raw.githubusercontent.com/spdk/spdk/master/README.md) |
| H1 | likely-fabricated | Invented IPC numbers; curl\|bash is risky | [inference] |
| H2 | true | Sound; Hearth has a C ABI | brief |
| H3 | mostly-true | Reasonable recommendation | [inference] |
| H4 | mostly-true | Informal proposal; llms-full.txt is not in the spec | [llmstxt.org](https://llmstxt.org/) |
| H5 | true | GCC SARIF and other JSON diagnostics are precedents | [GCC](https://gcc.gnu.org/onlinedocs/gcc/Diagnostic-Message-Formatting-Options.html) |
| H6 | misleading | Conflicts with GitHub AUP on inauthentic and bulk activity | [GitHub AUP](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies) |
| H7 | misleading | Mojo has inline asm; Exo, Jasmin, STOKE and SuperCoder cover the parts | [Mojo](https://github.com/modular/modular/blob/main/Mojo/stdlib/std/sys/_assembly.mojo) |
| I1 | mostly-true | AlphaEdit is real; projection is approximate; tested to about 3k edits | [AlphaEdit](https://arxiv.org/html/2410.02355v4) |
| I2 | unverifiable | Speculative; PEER is the closest precedent | [PEER](https://arxiv.org/abs/2407.04153) |
| I3 | unverifiable | Speculative | [inference] |
| I4 | false | NN verification is NP-complete; DGM uses empirical validation | [DGM](https://arxiv.org/abs/2505.22954) |
| I5 | false | About 17–19+ cycles on Zen 5; an aligned MOV/XCHG is enough | [uops.info](https://uops.info/html-instr/CMPXCHG16B_LOCK_M128.html) |
| I6 | false | Mitigates, doesn't eliminate; "machine-code level" is a category error | [GPM](https://arxiv.org/abs/2103.09762) |
| I7 | false | INVD is ring-0 and destroys data; use serialization or FlushInstructionCache | [INVD](https://www.felixcloutier.com/x86/invd) |
| I8 | unverifiable | Vision statement | — |

## Open questions

- **CPU-only llama.cpp decode for about 100B MoEs** (gpt-oss-120b class) on DDR5 desktops.
  I could not fetch measured numbers because the search budget was exhausted. Hearth should
  measure this on the 9950X.
- **Intel GDS mitigation cost on gathers.** Intel's performance-analysis page was not checked.
- **AMD's microcode-signature advisory (AMD-SB-7033).** The fetch timed out. It is relevant
  only to the A1 nuance.
- **Pure-ternary quality after post-training quantization.** Can a BF16-trained MoE be
  ternarised post hoc without large quality loss, or is native training mandatory? This
  decides whether D1 is ever reachable for Hearth's models.
- **Independent verification of openai/math results**, especially family 102 (UGC) and
  family 124 (scheduling), before any Mithril design leans on them.
- **x86 semantics in Lean.** Does an AVX-512-complete x86 semantics in Lean or Sail exist by
  2026? Not verified in this pass. This decides the cost of Mithril's verification story.

## Sources

- https://github.com/openai/math
- https://api.github.com/repos/openai/math
- https://raw.githubusercontent.com/openai/math/main/README.md
- https://raw.githubusercontent.com/openai/math/main/overview.pdf
- https://raw.githubusercontent.com/openai/math/main/lean/lean-toolchain
- https://raw.githubusercontent.com/openai/math/main/lean/ComparatorChallenges/README.md
- https://raw.githubusercontent.com/leanprover/comparator/master/README.md
- https://github.com/rjwalters/lean-genius/issues/43839
- https://raw.githubusercontent.com/leanprover/lean4/master/src/Std/Tactic/BVDecide.lean
- https://leanprover-community.github.io/mathlib4_docs/Mathlib/Analysis/ODE/PicardLindelof.html
- https://www.felixcloutier.com/x86/invd
- https://www.felixcloutier.com/x86/wbinvd
- https://www.felixcloutier.com/x86/clflush
- https://www.felixcloutier.com/x86/rdtsc
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache
- https://lists.xen.org/archives/html/xen-changelog/2025-07/msg00562.html
- https://mail.openjdk.org/pipermail/hotspot-dev/2019-March/037296.html
- https://uops.info/html-instr/CMPXCHG16B_LOCK_M128.html
- https://uops.info/html-instr/VPGATHERDD_ZMM_K_VSIB_ZMM.html
- https://uops.info/html-instr/VPOPCNTQ_ZMM_ZMM.html
- https://uops.info/html-instr/VPDPBUSD_ZMM_ZMM_ZMM.html
- https://www.agner.org/optimize/microarchitecture.pdf
- https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop
- https://en.wikipedia.org/wiki/Zen_5
- https://en.wikipedia.org/wiki/Alder_Lake
- https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/advisory-guidance/gather-data-sampling.html
- https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/best-practices/microcode-update-guidance.html (not re-fetched)
- https://llvm.org/docs/CommandGuide/llvm-mca.html
- https://raw.githubusercontent.com/llvm/llvm-project/main/llvm/lib/Target/X86/X86.td
- https://raw.githubusercontent.com/AliveToolkit/alive2/master/README.md
- https://doi.org/10.1145/3453483.3454030
- https://raw.githubusercontent.com/StanfordPL/stoke/develop/README.md
- https://doi.org/10.1145/2451116.2451150
- https://doi.org/10.1109/ISPASS.2014.6844459
- https://doi.org/10.1145/1375581.1375595
- https://doi.org/10.1016/0096-0551(81)90048-5
- https://doi.org/10.1145/3519939.3523446
- https://doi.org/10.1145/3133956.3134078
- https://github.com/modular/modular/blob/main/Mojo/stdlib/std/sys/_assembly.mojo
- https://deepmind.google/discover/blog/alphadev-discovers-faster-sorting-algorithms/
- https://arxiv.org/abs/2505.11480
- https://arxiv.org/abs/2502.11880
- https://arxiv.org/pdf/2410.16144
- https://raw.githubusercontent.com/microsoft/T-MAC/main/README.md
- https://arxiv.org/abs/2504.12285
- https://huggingface.co/unsloth/DeepSeek-R1-GGUF
- https://huggingface.co/openai/gpt-oss-120b
- https://huggingface.co/Qwen/Qwen3-30B-A3B
- https://arxiv.org/abs/2401.04088
- https://raw.githubusercontent.com/kvcache-ai/ktransformers/main/doc/en/DeepseekR1_V3_tutorial.md
- https://raw.githubusercontent.com/kvcache-ai/ktransformers/main/README.md
- https://arxiv.org/abs/2401.14361
- https://arxiv.org/abs/2308.12066
- https://raw.githubusercontent.com/flame/blis/master/docs/Performance.md
- https://arxiv.org/abs/2407.01425
- https://arxiv.org/abs/2406.01125
- https://arxiv.org/abs/2411.19108
- https://arxiv.org/abs/2408.12588
- https://arxiv.org/abs/2308.04079
- https://raw.githubusercontent.com/graphdeco-inria/gaussian-splatting/main/scene/gaussian_model.py
- https://arxiv.org/abs/2310.08528
- https://arxiv.org/html/2503.20314v2
- https://raw.githubusercontent.com/Wan-Video/Wan2.1/main/README.md
- https://self-forcing.github.io/
- https://arxiv.org/abs/2506.08009
- https://arxiv.org/abs/2312.12491
- https://raw.githubusercontent.com/spdk/spdk/master/README.md
- https://llmstxt.org/
- https://gcc.gnu.org/onlinedocs/gcc/Diagnostic-Message-Formatting-Options.html
- https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies
- https://arxiv.org/html/2410.02355v4
- https://proceedings.iclr.cc/paper_files/paper/2025/hash/29c8c615b3187ee995029284702d3f43-Abstract-Conference.html
- https://arxiv.org/abs/2401.07453
- https://arxiv.org/abs/2407.04153
- https://arxiv.org/abs/1702.01135
- https://doi.org/10.1007/978-3-319-63387-9_5
- https://arxiv.org/abs/2505.22954
- https://arxiv.org/abs/1810.01256
- https://arxiv.org/abs/2103.09762

## Ideas that survive and are worth building on

1. **Verified superoptimisation loop.** An LLM or RL proposer is gated by an equivalence
   checker, then emitted with measured cycles as the reward (B3, B8, B12). SuperCoder's 95%
   correctness shows the checker is mandatory.
2. **The Comparator pattern** (F2, reframed): a trusted spec module, an untrusted
   implementation, an axiom whitelist and a sandboxed checker. Bit-level goals go to
   certificate-producing SAT (`bv_decide`).
3. **Low-bit types as primitives**, lowered to LUT/`vpshufb` or VNNI (C6, reframed), with
   bit-exact integer accumulation compatible with INV-DET-3.
4. **Hardware-surfacing types**: `line64`, streaming stores, alias-free affine regions with a
   checked non-affine escape for routing (B4, B5).
5. **Explicit async memory pipelines** with data-dependent software prefetch only where the
   hardware prefetcher can't see the address (C7, reframed). This maps onto Hearth's
   multi-layer lookahead.
6. **Measured, per-microarchitecture cost models** as versioned data, plus mandatory
   hardware tags on performance claims (B2/B11 reframed, INV-HONEST).
7. **Entropy-aware branch lowering driven by profiles**, not static guesses (B7).
8. **Machine-actionable JSON diagnostics, llms.txt and an LSP/MCP surface** for agents (H4,
   H5). Skip synthetic-repo seeding (H6).
9. **Atomic hot-swap via pointer publish plus epoch reclamation** at token boundaries (I5, I7,
   reframed). No self-modifying code is needed.
10. **AlphaEdit-style null-space editing as an optional, measured library feature** (I1). Its
    claims stay scoped to "mitigates forgetting on the measured key set".
11. **Step-to-step activation caching** (TeaCache/PAB-style) as a scheduling primitive if
    Mithril ever targets diffusion (E4, reframed).
