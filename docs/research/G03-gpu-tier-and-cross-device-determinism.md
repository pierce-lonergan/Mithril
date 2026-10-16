# G03 — Is there a GPU in scope, and can canonical-order bit-exactness survive on it at useful speed?

*Research dossier for the Mithril architecture phase. Written 2026-10-11. It resolves a conflict
between the brief ("No GPU used by Hearth today"), R13 (Hearth's simulator lists an RTX 5070) and
R06 (the fastest consumer MoE engines are GPU+RAM hybrids). It then asks whether Hearth's
canonical floating-point order (INV-DET-3) can run on that GPU at useful speed.*

*Method note: the shared WebSearch budget ran out after my first query. Everything below comes
from reading the Hearth repo, from read-only local hardware queries, and from direct fetches of
primary documents, papers and repositories (NVIDIA docs, arXiv, GitHub, Khronos, OCP). I may have
missed 2026 developments that only a search would surface. Where I could not verify something,
I say so.*

---

## Summary

- **There is a GPU, and Hearth already plans for it.** Hearth's `this-pc` simulator profile
  records an RTX 5070 with 12 GiB, 672 GB/s and about 50 GB/s over PCIe 5.0 x16. A unit test
  locks these values in. A read-only query on 2026-10-11 confirmed an NVIDIA GeForce RTX 5070:
  12,227 MiB, compute capability 12.0, PCIe Gen5 x16 capable, driver 616.92. It currently drives
  a display, with about 1.5 GB in use at idle, and an AMD Radeon iGPU is also present. The brief
  is literally true, since Hearth *uses* no GPU, but its Machine line leaves the card out. **The
  owner still has to confirm that the GPU is in scope for compute.** *(high)*
- **For models that fit in 64 GB, the GPU tier is the largest lossless lever.**
  - Hearth's own simulator (SIMULATED, my read-only runs) puts the backbone and hot experts in
    VRAM. That takes Qwen3-30B-A3B from 23 to 112 tok/s and gpt-oss-120b from 15 to 55 tok/s.
  - Measured, project-reported hybrids on 12 GB cards reach 48–94 tok/s on a 125B MoE at
    2–3 bits (Strata).
  - For out-of-core 1T models the lever shrinks to about 1.4× (SIMULATED, and it needs a LOSSY
    Q4 backbone).

  *(medium: simulated, or measured by the project itself)*
- **Batch invariance is not cross-device determinism.**
  - Thinking Machines' kernels, vLLM's `VLLM_BATCH_INVARIANT`, SGLang's deterministic mode and
    cuBLASLt's new experimental batch-invariance mode all make one device and stack deterministic.
  - Thinking Machines says outright that its kernels are not hardware- or version-invariant.
  - cuBLAS guarantees reproducibility only on the same architecture, the same SM count and the
    same toolkit.
  - cuBLASLt batch invariance is limited to compute capability 10.x, so it **excludes the RTX
    5070 (12.0)**.

  *(high)*
- **The cost of batch invariance has been measured, but only on servers.**
  - Thinking Machines: matmul about 20% slower than cuBLAS; end-to-end 26 → 42 s.
  - SGLang: 25–45% slower, 34.35% on average.
  - vLLM + TorchTitan bitwise RL: 2.4× slower.
  - RepOps (cross-hardware claim, FP32): matmul 30–70% slower, inference 58–218% slower.

  None of these measures batch-1 decode on a consumer card. *(high for the quoted numbers)*
- **CUDA can express Hearth's order exactly at the instruction level.** `__fadd_rn`/`__fmul_rn`,
  and PTX `add`/`mul` with an explicit `.rn`, are never contracted into FMA. IEEE division and
  sqrt and denormal support are the defaults without fast-math. `nvcc --fmad` defaults to *true*,
  so it has to be overridden. *(high)*
- **Some things cannot be reproduced bit for bit:**
  - tensor-core float MMA (multi-term fused summation with truncation, and it varies by
    architecture);
  - MX block-scaled dot products (order "implementation-defined" in the spec);
  - CUDA's libm (`expf`/`sinf`/`cosf` at 2 ulp; host and device implementations are
    independent);
  - LLVM libc's GPU build (`sinf`/`cosf` 1 ulp away from correct rounding).

  *(high)*
- **Exact integer accumulation is the way out [inference].** Hearth's Q8/Q4 canonical definition
  is an *exact int32* sum per 64-element block, followed by a short float epilogue in fixed order.
  Integer sums do not depend on order, so dp4a and INT8 tensor cores (246.9 dense TOPS on the
  5070) can compute them without breaking bit-identity. MXFP4 can be converted to integers the
  same way. F32/BF16 `dot16` maps exactly onto a half-warp with a shuffle tree. Consequences:
  - Batch-1 decode should keep close to native speed.
  - Float prefill loses tensor cores, which lowers its ceiling about 4×.
  - Hearth's sequential-in-t attention accumulation must be redefined into fixed chunks.

  *(medium; no published measurement exists)*
- **Kernel DSLs do not guarantee order.**
  - CUDA Tile IR: `reduce`/`scan` evaluation order is implementation-defined and deterministic
    only for the same kernel on the same device; `mmaf` accumulation order is unspecified.
  - Triton: `tl.dot` defaults to TF32 for f32 inputs, and no reduction order is documented.
  - TileLang: targets CUDA SM70–SM120 and an LLVM CPU backend, but documents no determinism.
  - Vulkan: can be made exact only with `NoContraction` + `RoundingModeRTE` + `DenormPreserve`
    and a software division.

  *(high)*
- **CPU-vs-GPU bit-identity is claimed but not demonstrated.** RepOps (x86-64/arm64 CPUs plus
  NVIDIA compute capability 7.5–9) and RepDL (FP32, correctly rounded math) claim it, but neither
  paper publishes comparison data across devices, and neither covers consumer Blackwell. The
  verifiable-inference field designs around tolerance instead (TOPLOC). *(medium)*
- **Decision: make INV-DET-3 cross-device for a "canonical core".**
  - A dynamic GPU expert cache with per-device numerics would make logits depend on what is
    resident in VRAM. That breaks INV-DET-1 and INV-LOSSLESS-DEFAULT.
  - Allow device-specific orders only as named, opt-in contracts, each with its own goldens.
  - Mithril v1 needs the VRAM tier in its store model and device-neutral numeric contracts now.
  - The first GPU deliverable should be a narrow PTX backend for the expert tier. A full GPU
    backend belongs in v2.

  *(medium-high)*

---

## Findings

### F1. What Hearth records about the GPU, and what the machine reports

**The Hearth repo (read-only).**
- **`this-pc` profile.** It sets `gpu_name="RTX 5070"`, `vram_gib=12.0`, `pcie_gbs=50.0` and
  `vram_gbs=672.0`. Its notes say "RTX 5070 12 GB (PCIe 5.0 x16 ~50 GB/s achievable, 672 GB/s
  VRAM)" ([hardware.py](../../../hearth/python/hearth/sim/hardware.py)).
- **SIMULATOR.md §2.2.** The table row for `this-pc` lists "RTX 5070 12 GiB, 672 GB/s, PCIe
  50 GB/s". The assumptions add "RTX 5070: PCIe 5.0 x16, about 50 GB/s achievable"
  ([SIMULATOR.md](../../../hearth/docs/SIMULATOR.md)).
- **GPU modes are roadmap only.** §3 of the same file says GPU modes are "roadmap R01. The engine
  is CPU-only today" ([SIMULATOR.md](../../../hearth/docs/SIMULATOR.md)).
- **A unit test locks the numbers in:**
  `assert (pc.dram_gbs, pc.nvme_gbs, pc.vram_gib, pc.vram_gbs) == (60.0, 6.5, 12.0, 672.0)`
  ([test_sim.py](../../../hearth/tests/py/test_sim.py)).
- **Task R01-cuda** is titled "CUDA/HIP backend: VRAM expert tier, W4A16 GEMV, GPUDirect Storage
  path". Its acceptance criterion is "bit-identical to CPU kernels or documented tolerance", and
  its status is `todo` ([tasks.json](../../../hearth/governance/tasks.json)).
- **ADR-0003:** "A GPU backend must reproduce these semantics or document its tolerance (task
  R01)" ([ADR-0003](../../../hearth/governance/decisions/ADR-0003-canonical-numerics.md)).
- **NUMERICS.md:** "Any SIMD/GPU kernel must reproduce the scalar definition exactly"
  ([NUMERICS.md](../../../hearth/docs/NUMERICS.md)).
- **README roadmap:** "CUDA / HIP backend with a VRAM expert tier; Vulkan and Metal"
  ([README](../../../hearth/README.md)).
- **INV-DET-1 scope.** It is stated "For a fixed binary and ISA". Device is not one of the
  listed axes ([INVARIANTS.md](../../../hearth/governance/INVARIANTS.md)).

Nothing in the repo is a *measurement* of the GPU. 672 GB/s is the datasheet peak: NVIDIA's
Blackwell whitepaper lists 672 GB/s for the RTX 5070
([RTX Blackwell whitepaper](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf)).
The same profile discounts DRAM from about 78 GB/s measured to 60 GB/s "assumed for streaming
kernels" ([hardware.py](../../../hearth/python/hearth/sim/hardware.py)).
- **[inference]** The GPU what-ifs therefore use a peak number where the CPU paths use a
  discounted one, which makes them optimistic.

**Local read-only queries (Win32_VideoController and `nvidia-smi`, 2026-10-11).**

| Field | Value |
|---|---|
| Adapter | NVIDIA GeForce RTX 5070 |
| Memory | 12,227 MiB |
| PCIe link | max Gen 5, width 16; Gen 1 while idle |
| Compute capability | 12.0 |
| Driver | 616.92, WDDM |
| Display | active, 1,503 MiB used at idle |
| Other adapters | AMD Radeon iGPU |
| CUDA toolkit | none: `nvcc` absent, `CUDA_PATH` unset |
| Driver-shipped libraries | `nvcuda.dll` and `vulkan-1.dll` present in System32 |

NVIDIA's list also gives the RTX 5070 as compute capability 12.0, and B200 and B300 as 10.0 and
10.3 ([CUDA GPUs](https://developer.nvidia.com/cuda-gpus)).

**Owner confirmation needed:**
1. Is the GPU in scope for Hearth and Mithril compute?
2. May the display move to the iGPU? That would free about 1.5 GB of VRAM. *[inference]*
3. Is depending on the driver API (`nvcuda.dll`) or Vulkan acceptable under INV-DEP ("C11 + OS
   APIs only")? See [INVARIANTS.md](../../../hearth/governance/INVARIANTS.md).

### F2. The card itself (RTX 5070, GB205, compute capability 12.0)

From NVIDIA's RTX Blackwell whitepaper, Appendix C, Table 6
([whitepaper](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf)):

| Item | RTX 5070 |
|---|---|
| SMs / CUDA cores / Tensor Cores | 48 / 6,144 / 192 (5th gen) |
| Boost clock | 2,512 MHz |
| Peak FP32 (non-tensor) | 30.9 TFLOPS |
| Peak INT32 (non-tensor) | 30.9 TOPS |
| FP16 / BF16 tensor, FP32 accumulate | 61.7 dense / 123.5 sparse TFLOPS |
| TF32 tensor | 30.9 / 61.7 TFLOPS |
| INT8 tensor | 246.9 / 493.9 TOPS |
| FP4 tensor | 493.9 / 987.8 TFLOPS ("988 AI TOPS") |
| Memory | 12 GB GDDR7, 192-bit, 28 Gbps, 672 GB/s |
| L2 | 49,152 KB |
| TGP | 250 W |

- **Shared FP32/INT32 cores.** The INT32 cores are unified with the FP32 cores, and each unified
  core works as one or the other in any given clock.
- **FP64.** It runs at 1/64 of the FP32 rate. This is stated for GB202; that it also applies to
  GB205 is my **[inference]**.
- **Product page.** NVIDIA lists 6,144 cores, 2.51 GHz, 12 GB GDDR7, PCIe Gen 5 and 250 W
  ([NVIDIA RTX 5070 family](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5070-family/)).
- **[inference]** VRAM bandwidth (672 GB/s) is about 9–11× the CPU's DRAM bandwidth (60–78 GB/s
  per the Hearth profile).
- **[inference]** PCIe 5.0 x16, about 63 GB/s theoretical (R08), is *below* DRAM bandwidth. Cold
  experts should therefore be computed where they live rather than shipped over the bus, which
  is R08's conclusion and Strata's design.

### F3. Batch invariance: what has been achieved, what it costs, and what it does not cover

**Thinking Machines, September 2025.**
- **Diagnosis.** The real cause of nondeterminism in LLM inference is missing *batch invariance*.
  Typical forward passes have no atomics and are deterministic run to run.
- **Demonstration.** Qwen3-235B-A22B-Instruct-2507 produced 80 distinct completions out of 1,000
  at temperature 0. They diverged at token 103. With batch-invariant RMSNorm, matmul and
  attention, all 1,000 were identical.
- **Method.** No split-K. One kernel configuration for every shape. Decode attention uses a
  *fixed split size* rather than a fixed number of splits.
- **Cost.** The batch-invariant matmul is about 20% slower than cuBLAS. On Qwen3-8B with 1,000
  sequences, default vLLM took 26 s, unoptimised deterministic vLLM 55 s, and deterministic vLLM
  with a better attention kernel 42 s.
- **Scope.** The author states that the kernels are *not* invariant to hardware or software
  version: a different GPU or PyTorch version may give different values.

([Thinking Machines](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/);
code: [batch_invariant_ops](https://github.com/thinking-machines-lab/batch_invariant_ops), MIT).
*(high)*

**SGLang** (LMSYS, 2025-09-22).
- **Method.** Thinking Machines' batch-invariant ops, plus a fixed split-KV size in the
  FlashInfer, FA3 and Triton backends. Chunked-prefill boundaries are aligned to the split size.
- **Results.** Slowdown averaged 34.35% for FlashInfer and FA3, against the 61.5% the post
  attributes to Thinking Machines; most cases fell between 25% and 45%. Triton was slower, up to
  +55.1% on an H200. Deterministic mode gave 1 unique output in 50 trials, against 2–18 in normal
  mode.
- **Scope then.** TP1 and TP2 only, dense models only.

([LMSYS](https://lmsys.org/blog/2025-09-22-sglang-deterministic/)). The current docs show a
Qwen3-30B-A3B MoE example under `--enable-deterministic-inference`. They give no overhead
numbers and say nothing about cross-hardware behaviour
([SGLang docs](https://docs.sglang.io/advanced_features/deterministic_inference.html)). *(high)*

**vLLM.**
- **Feature.** `VLLM_BATCH_INVARIANT=1` is in beta and supports NVIDIA compute capability 8.0 and
  above. The docs give no overhead numbers and do not address reproducibility across hardware
  ([vLLM docs](https://docs.vllm.ai/en/latest/features/batch_invariance.html)).
- **Tracker issue #27433** (opened 2025-10-23):
  - PR #53247 adds per-architecture tuned persistent matmuls, about 3× faster decode kernels on
    the RTX 4090D and H20.
  - PR #53649 adds Blackwell Triton autotuning, which cut end-to-end latency by 33.6%.
  - On Blackwell, the FA4 scheduler is forced back to FA2.
  - An RTX 5090 user reported varying outputs in November 2025.
  - I found no confirmed result on sm_120 consumer hardware
    ([vLLM #27433](https://github.com/vllm-project/vllm/issues/27433)).
- **vLLM + TorchTitan bitwise-exact RL.** Training and inference numerics matched bit for bit on
  Qwen3 1.7B, giving a KL of exactly 0.0. The bitwise run was 2.4× slower
  ([vLLM blog](https://vllm.ai/blog/2025-11-10-bitwise-consistent-train-inference)). *(high)*

**cuBLAS 13.4.**
- **What is guaranteed.** Routines give bitwise-identical results run to run "on GPUs with the
  same architecture and the same number of SMs". This is not guaranteed across toolkit versions,
  or with multiple active streams unless workspaces are separated. Atomics mode (`symv`/`hemv`)
  is not reproducible.
- **New experimental batch invariance in cuBLASLt.** With
  `CUBLASLT_MATMUL_DESC_BATCH_INVARIANCE_FLAGS`, any M or N sub-range of a problem is bitwise
  identical to the same part of the full problem. Conditions:
  - It holds only if the descriptor, K, the workspace size and the split-K configuration are
    identical.
  - It disables split-K.
  - It is "Only GPUs with compute capabilities 10.x".
  - Supported precisions are fp32 (COMPUTE_32F), fp16, bf16, FP8 and FP4.
  - A process-wide `CUBLAS_BATCH_INVARIANCE_FLAGS` environment variable also exists.

([cuBLAS PDF, §2.1.4, §3.1.5, §3.3.8](https://docs.nvidia.com/cuda/pdf/CUBLAS_Library.pdf);
[HTML](https://docs.nvidia.com/cuda/cublas/index.html)). **[inference]** The RTX 5070 is
compute capability 12.0, so NVIDIA's own batch-invariant GEMM does not run on it. Even where it
does run, it promises invariance only across shapes, not across devices. *(high)*

**Reading [inference].**
- All the deployed systems give *same-device, same-stack* determinism. Their costs (20% to 2.4×)
  were measured in compute-bound server batches on H100/H200-class hardware.
- Hearth's INV-DET-2 (batch == sequential) is the same property, and Hearth reached it
  independently (R07).
- What none of them provide is INV-DET-3 across a CPU/GPU boundary. Vendor libraries cannot
  provide it either: their implementations change across architectures and versions by design.

### F4. What CUDA guarantees at the instruction level

- **No contraction with explicit rounding.** The CUDA floating-point guide says intrinsics with
  explicit rounding (`__fadd_rn`, `__fmul_rn`, `__dadd_rn`, `__dmul_rn`) are "guaranteed to
  remain independent and will not be merged into fused multiply-add instructions".
- **IEEE defaults.** The default IEEE mode is `-ftz=false -prec-div=true -prec-sqrt=true`:
  correctly rounded single-precision division and sqrt, with denormals supported. Fast mode
  flushes denormals and approximates division and sqrt.
- **CPU and GPU.** The guide says individual IEEE operations give the same results on CPU and
  GPU. It attributes differences to FMA, to reordering under parallelism, to higher host
  precision, and to math functions that are not correctly rounded.

([CUDA FP guide](https://docs.nvidia.com/cuda/floating-point/index.html)). *(high)*

- **nvcc flags.** `--fmad` defaults to **true** and contracts multiplies and adds into FMA.
  `--use_fast_math` implies `--ftz=true --prec-div=false --prec-sqrt=false --fmad=true`
  ([nvcc docs](https://docs.nvidia.com/cuda/cuda-compiler-driver-nvcc/index.html)). A canonical
  build must pass `-fmad=false` or use the `_rn` intrinsics everywhere, and must never use
  fast-math. That mirrors Hearth's `-ffp-contract=off` ([NUMERICS.md](../../../hearth/docs/NUMERICS.md)).
- **PTX ISA.**
  - `add.f32` and `mul.f32` *without* a rounding modifier "may be optimized to use
    fused-multiply-add". *With* an explicit modifier they are "treated conservatively by the code
    optimizer".
  - `fma` requires an explicit rounding mode, computes the product and sum at infinite precision,
    and rounds once.
  - `dp4a` is a four-way byte dot product accumulated into 32 bits.
  - Subnormals are supported by default unless `.ftz` is given.

  ([PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html)). *(high)*
- **Math library.** The CUDA programming guide lists `expf` at 2 ulp, `sinf`/`cosf` at 2 ulp and
  `sqrtf` at 0 ulp by default. It says host and device implementations of math functions "are
  independent"
  ([CUDA math appendix](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/mathematical-functions.html)).
- **Loading without the toolkit.** `cuModuleLoadData`/`Ex` accepts "hand-written" PTX, cubin,
  fatbin or Tile IR data ([CUDA driver API](https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__MODULE.html)).
  **[inference]** A compiler can therefore emit PTX text with explicit `.rn` modifiers and load it
  through the driver DLL already on this machine, with no CUDA toolkit dependency.
- **Throughput cost of avoiding FMA [inference].** The 30.9 TFLOPS FP32 peak counts an FMA as two
  operations. Separate rounded multiply and add halve useful float throughput to about 15.4 T
  multiply-add pairs per second.
  - Batch-1 decode at 672 GB/s with BF16 weights streams about 336 G weights/s and needs about
    0.67 TFLOP/s. That is well under even the non-FMA rate, so decode is unaffected.
  - Prefill is affected, because it is compute-bound (F7).

### F5. What cannot be reproduced: tensor-core float MMA, MX formats, vendor libm

- **Tensor-core summation is not IEEE, and its shape changes by architecture.** FPRev (Xie, Gao,
  Wang, Xue; arXiv 2411.00442, revised July 2025) infers accumulation orders from outputs.
  - For FP16 tensor-core matmul through cuBLAS it found 5-, 9- and 17-way multi-term fused
    summation on V100, A100 and H100.
  - These are executed "in a non-standard, IEEE-754-incompliant way". Summands are aligned to the
    largest exponent and truncated.
  - Float32 NumPy summation order was the same on the three CPUs tested, but dot and GEMV orders
    differed between CPUs.
  - RTX GPUs were not tested.

  ([FPRev](https://arxiv.org/abs/2411.00442); [HTML](https://arxiv.org/html/2411.00442)). *(high)*
- **FP8 tensor-core accumulation is limited.** DeepSeek-V3 reports that FP8 GEMM on H800 keeps
  only about 14 bits of accumulation precision, with up to about 2% relative error at K = 4096.
  It promotes partial sums to FP32 CUDA cores every N_C = 128 elements
  ([DeepSeek-V3](https://arxiv.org/html/2412.19437)).
- **CUDA Tile IR's own `mmaf` text.** It says native Hopper FP8 accumulation uses an intermediate
  precision only "larger than half-precision", and gives no accumulation order
  ([Tile IR ops](https://docs.nvidia.com/cuda/tile-ir/latest/sections/operations.html)). *(high)*
- **MX formats leave the dot product open.** The OCP MX v1.0 spec defines MXFP4 as E2M1 elements
  in blocks of 32 with an E8M0 power-of-two scale. Representable magnitudes run 0.5–6.0. "The
  internal precision of the dot product and order of operations is implementation-defined"
  ([OCP MX v1.0](https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf)).
  **[inference]** Native block-scaled FP4 MMA on Blackwell therefore cannot serve as a canonical
  order.
- **Even shared libm source drifts on GPUs.**
  - LLVM libc aims to be correctly rounded in all rounding modes. Its GPU builds use
    `LIBC_MATH_SKIP_ACCURATE_PASS`, and their measured maximum distance from the correctly rounded
    result is 0 ulp for `expf` but 1 ulp for `sinf`, `cosf` and `logf`, on both AMD and NVIDIA
    ([LLVM libc math](https://libc.llvm.org/headers/math/index.html)).
  - The GPU libc page does not list `math.h` among supported headers
    ([libc GPU](https://libc.llvm.org/gpu/index.html)).
  - CORE-MATH supplies correctly rounded binary32 functions (MIT), exhaustively checked for the
    univariate ones. glibc has taken many binary32 functions since 2.42. It makes no GPU claim
    ([CORE-MATH](https://core-math.gitlabpages.inria.fr/)).
  - **[inference]** Bit-identity across devices requires that Mithril *own* the transcendental
    implementations. That means either correctly rounded algorithms compiled with their accurate
    path on every target, or a fixed sequence of basic IEEE operations.
  - **[inference]** Many correctly rounded binary32 implementations compute internally in double.
    FP64 runs at 1/64 rate on GeForce, so a GPU port should prefer float-only algorithms. The call
    counts are small anyway: per activation element, not per weight.

### F6. Published cross-hardware and CPU-vs-GPU bit-identical work

**RepOps (Gensyn).**
- **Source.** It is part of Verde (Arun et al., arXiv 2502.19405, February 2025).
- **Claim.** It "eliminates hardware 'non-determinism' by controlling the order of floating point
  operations performed on all hardware".
- **Method.** Matmul outer loops run in parallel and the inner accumulation runs in a fixed
  order. exp, sin, cos and tanh are reimplemented.
- **Tested hardware.** NVIDIA T4, RTX 3090 and A100, FP32 only.
- **Measured overhead:**
  - matmul 30–60% for sizes above 2¹⁰, 60–70% steady state on the RTX 3090, about 35% on the T4,
    and about 200% at size 256;
  - inference: DistilBERT +74% (T4) and +84% (A100); Llama-3.1-1B +218% (T4) and +58% (A100);
    Llama-3.1-8B +98% (A100-80GB).
- **No comparison data.** The paper does not publish a cross-GPU or CPU-vs-GPU bitwise
  comparison.

([Verde](https://arxiv.org/abs/2502.19405); [HTML](https://arxiv.org/html/2502.19405)). The demo
repository lists x86-64 and arm64 CPUs and NVIDIA compute capability 7.5–9 (T4 through RTX 4090,
H100/H200) as supported. It shows no results
([repop-demo](https://github.com/gensyn-ai/repop-demo)). Consumer Blackwell (12.0) is outside
that list. *(medium: the claim is credible, but its evidence is not in the paper)*

**RepDL (Microsoft Research; Xie, Zhang, Chen, arXiv 2510.09180, October 2025).**
- **Claim.** Bitwise-identical training and inference "on the same or different CPU or GPU
  systems".
- **Method.** "Correct rounding and order invariance". Summation is sequential by default, with
  pairwise as an option.
- **Scope.** FP32 only; low-precision matrix units are future work.
- **No numbers.** The paper gives no overhead measurements.
- **Notably, it *enables* FMA contraction** (F8 §4). MIT; a research project.

([RepDL](https://github.com/microsoft/RepDL); [paper](https://arxiv.org/abs/2510.09180);
[HTML](https://arxiv.org/html/2510.09180)). *(medium)*

**CPU-only precedent.** kimi-k3-in-c reports byte-identical output across memory budgets and
across Linux and Windows builds. It achieves this with scalar-order AVX2/NEON, a fixed partition
and `-ffp-contract=off` (R06, citing its README). It does not cover a GPU.

**Counter-evidence: the field usually tolerates differences rather than removing them.**
- TOPLOC (Prime Intellect et al., arXiv 2501.16007) hashes activations with a locality-sensitive
  hash that is "robust across diverse hardware configurations, GPU types, and algebraic
  reorderings" ([TOPLOC](https://arxiv.org/abs/2501.16007)).
- Yuan et al. (arXiv 2506.09501) measured up to 9% accuracy variation and up to 9,000 tokens of
  length difference for DeepSeek-R1-Distill-Qwen-7B under BF16 greedy decoding. The changes came
  from varying GPU count, GPU type and batch size. Their LayerCast pipeline computes in FP32 as a
  mitigation, not as a bit-exactness guarantee
  ([Yuan et al.](https://arxiv.org/abs/2506.09501)).

*(high)*

**Bottom line [inference].** No published system demonstrates bit-identical LLM inference between
a Zen 5 CPU and a consumer Blackwell GPU. The two libraries that claim cross-device identity both
restrict themselves to FP32 non-tensor arithmetic with owned kernels. That is exactly the regime
Hearth's canonical order already lives in.

### F7. Kernel DSLs and APIs: what they promise about order

- **CUDA Tile IR.**
  - For `reduce` and `scan`, "the exact evaluation order is implementation-defined". The result
    is deterministic "across runs of the same kernel on the same device", and the compiler may
    reorganise using associativity and commutativity.
  - Tile blocks execute in a "non-deterministic" order.
  - `addf` uses the target's native addition. It has a `rounding` attribute
    (`nearest_even`, …) and an f32 `flush_to_zero` flag.
  - `exp` defaults to `full`, which is backed by the CUDA Math API.

  ([Tile IR semantics](https://docs.nvidia.com/cuda/tile-ir/latest/sections/semantics.html),
  [operations](https://docs.nvidia.com/cuda/tile-ir/latest/sections/operations.html)).
  **[inference]** A canonical reduction cannot be written as a Tile IR `reduce`. It has to be an
  explicit chain of `addf` with `nearest_even`. Tile IR suits device-scoped contracts, not the
  cross-device core.
- **cuTile Python** documents neither reduction order nor determinism
  ([cuTile ops](https://docs.nvidia.com/cuda/cutile-python/operations.html)).
- **Triton.** `tl.dot` defaults to `input_precision="tf32"` for f32 inputs, which "may" truncate
  without rounding; an `"ieee"` option exists
  ([tl.dot](https://triton-lang.org/main/python-api/generated/triton.language.dot.html)).
  `tl.reduce` documents no combination order
  ([tl.reduce](https://triton-lang.org/main/python-api/generated/triton.language.reduce.html)).
  Batch-invariant Triton kernels get determinism through configuration discipline (F3), not
  through a language guarantee.
- **TileLang.** Its targets are CUDA "SM70 through SM120", ROCm, Metal, Ascend and an
  experimental LLVM CPU backend (added 2026-06-18). It added SM120 NVF4 block-scaled MMA on
  2026-07-30. The README says nothing about determinism
  ([TileLang](https://github.com/tile-ai/tilelang)). It is the closest precedent for "one source,
  CPU and GPU", but without a numeric contract.
- **Vulkan / SPIR-V.**
  - `OpFAdd`/`OpFSub`/`OpFMul` are "correctly rounded", but the rounding mode is
    implementation-defined unless the entry point declares `RoundingModeRTE`.
  - Without `NoContraction`, the flags AllowContract and AllowReassoc are assumed.
  - `OpFDiv` is 2.5 ULP.
  - Denormals may be flushed unless `DenormPreserve` is declared.

  ([Vulkan SPIR-V environment](https://docs.vulkan.org/spec/latest/appendices/spirvenv.html)).
  **[inference]** A Vulkan backend can match canonical order only with `NoContraction` on every
  operation, RTE and DenormPreserve (both optional device features), and software-correct
  division and sqrt. That is possible but depends on the driver. CUDA PTX is the more direct
  route on this machine.

### F8. Can Hearth's canonical order run on the RTX 5070 at useful speed? Kernel by kernel [inference]

This section is my analysis against [NUMERICS.md](../../../hearth/docs/NUMERICS.md). No
measurement exists. *(medium overall)*

| NUMERICS op | Canonical definition | GPU mapping that reproduces it bit for bit | Speed consequence |
|---|---|---|---|
| §3 Q8/Q4 matvec | Exact int32 sum per 64-block; `acc = acc + (float)isum * (dw*dx)` in block order | dp4a or INT8 `mma` for the integer part: any order is exact, since \|isum\| ≤ 64·127·127 ≈ 1.03 M < 2³¹. Per-block products are rounded individually, then accumulated serially with `add.rn` | Decode stays bandwidth-bound. The serial chain is n/64 adds: 32 for Qwen3-30B (d = 2048), 45 for gpt-oss-120b (2,880), 112 for 7,168. Prefill can use INT8 tensor cores (246.9 dense TOPS) with an epilogue per K block and no split-K |
| §1 F32/F16/BF16 `dot16`, router | 16 lane accumulators, then an 8-4-2-1 tree, no FMA | One half-warp per row. Lane j accumulates a[j], a[j+16], … in order, then `__shfl_down` by 8, 4, 2, 1 with `__fadd_rn`. This is the exact tree, with coalesced 64-byte loads | CUDA cores only, no tensor cores. Prefill ceiling about 15.4 T non-FMA pairs/s versus 61.7 TFLOPS dense BF16 tensor, about 4× lower. Decode unaffected |
| §2 activation quantisation | Exact amax, IEEE `/`, `nearbyintf` | Warp max (order-free and exact), IEEE `/` under `prec-div=true`, `__float2int_rn` | None |
| §4 RMSNorm, softmax sums | `sum16` | Half-warp, as above | None |
| §4 SiLU, sigmoid, softmax `expf`; RoPE `sinf`/`cosf` | Platform libm | Replace with a Mithril-owned canonical function on every target. RoPE cos/sin can be computed on the host and uploaded, a few KB per token | Small: calls scale with activations, not weights |
| §5.1/5.2 attention | Scores via `dot16`; `o = Σ_t p_t v_t` **sequential in t** | One thread per (head, d), serial over t; no split-KV allowed | Long-context decode is latency-bound. A 32k serial chain is on the order of 10⁵ cycles per layer. Fix: redefine as fixed chunks (sequential inside each chunk, chunks combined in order), the CPU-side analogue of SGLang/Thinking Machines' fixed split size |
| §5.3 MoE combine | Sum in rank order, whatever finished first | Identical on either device | This is what lets CPU and GPU share experts |

**Conclusions from the table.**
1. **Hearth's numerics are unusually friendly to GPUs.** The heavy work (expert GEMV/GEMM on
   Q8/Q4) is exact integer arithmetic, plus an O(n/64) float epilogue in fixed order. Integer
   associativity lets INT8 tensor cores and dp4a reorder freely without changing a bit. This is
   the opposite of the BF16 tensor-core paths that batch-invariance work struggles with.
2. **MXFP4 can be converted to integers as well.** Doubling an E2M1 value gives an integer in
   {0, 1, 2, 3, 4, 6, 8, 12}. The E8M0 scale is a power of two. MXFP4 × Q8 block dots are
   therefore exact int32 sums times power-of-two scales, as long as no overflow or underflow
   occurs. The model's native FP4 experts (Kimi K3, gpt-oss) could use the INT8 tensor-core path
   deterministically. The native FP4 MMA could not (F5).
3. **The costly items are float prefill and long-context attention.** Float GEMM loses tensor
   cores. Attention needs an ADR-level change to its canonical order.
4. **Explicit FMA is a legitimate option for the next canonical version.** `fma` is a single
   correctly rounded IEEE operation on both Zen 5 and CUDA (PTX `fma.rn`), so writing it
   *explicitly* is deterministic. Only *implicit* contraction breaks identity. RepDL enables
   contraction for this reason (F6). Adopting it would double the GPU's useful float rate and
   help AVX-512 too, but it changes every golden.
5. **Overhead estimate for decode: small, but unmeasured.** The constraint touches reduction
   trees and epilogues, not bytes moved. My guess is within 0–30% of llama.cpp-class GEMV on the
   same card, with **low confidence** until a prototype is measured. The server numbers in F3 do
   not transfer, because they are compute-bound batches.

### F9. Decode numbers: 30B–120B MoE on a 12 GB Blackwell (or similar) card with a 64 GB host

**Measured, as reported by projects and communities:**

| Source | Hardware | Model / quant | Decode |
|---|---|---|---|
| Strata README | RTX 5070 12 GB, Ryzen 5 7600, 64 GB | Qwen3.8-Flash-Next 125B, Q2_0 / IQ2_XS / IQ3_XXS / IQ3_S / Coder | 94 / 79 / 62 / 53 / 55 tok/s; prompt 2,650 / 2,090 / 1,750 / 1,620 / 2,180 tok/s (4K answers, 32K prompts) |
| Strata README | same class, 64 GB | UD-Q4_K_XL (does not fit RAM) | 7–8.5 tok/s, "mostly SSD-bound" |
| Strata community | RTX 4070 12 GB (Ada), i5-12600KF, 32 GB DDR4 | IQ2_XS | 48.23 tok/s (modified local build) |
| Strata community | RTX 5060 Ti 16 GB, 128 GB | IQ3_S | 48.2 / 47.7 tok/s |
| Strata community | RX 9070 16 GB, 64 GB | IQ3_XXS | 58.7 tok/s at about 4K |
| llama.cpp PR #29887 (fork commit) | RTX 5060 Ti 16 GB, 62 GB RAM, `--cpu-moe`, 8,000 MiB cache | Qwen3.8-Flash-Next UD-IQ3_XXS | 14.95–19.26 tok/s |
| llama.cpp gpt-oss guide | RTX 5090, `--n-cpu-moe 21` | gpt-oss-120b | about 30 tok/s at zero context; about 8 GB VRAM minimum for 120B |
| Hardware Corner | RTX 5090, `--n-cpu-moe 21` | gpt-oss-120B | 9.60 tok/s (87 ctx), 8.14 (5,650 ctx) |

Sources: [Strata](https://github.com/Niko1221/Strata),
[community benchmarks](https://raw.githubusercontent.com/Niko1221/Strata/main/docs/COMMUNITY_BENCHMARKS.md),
[PR #29887](https://github.com/ggml-org/llama.cpp/pull/29887),
[gpt-oss guide #15396](https://github.com/ggml-org/llama.cpp/discussions/15396),
[Hardware Corner](https://www.hardware-corner.net/guides/gpt-oss-offloading-moe-layers/).

Caveats:
- Strata does not say whether its table includes its speculative decoding (1.6–1.8×). It says
  nothing about determinism.
- The two RTX 5090 figures for gpt-oss-120b differ by 3×, which shows how settings-dependent
  these reports are.
- I found **no measured Qwen3-30B-A3B or gpt-oss-120b decode figure on an RTX 5070 specifically**.
  That is unverified, partly because of the search budget.

**Anecdote that bears on determinism.** In PR #29887 a commenter saw repeated "the" tokens with
the GPU expert cache on and not with it off. They called it correlation only
([PR #29887](https://github.com/ggml-org/llama.cpp/pull/29887)). Whether a cache changes output is
exactly what per-device numerics would cause (§Implications). The multi-GPU follow-up halved
decode (33 → 16 tok/s) at a 43.5% hit rate
([PR #30112](https://github.com/ggml-org/llama.cpp/pull/30112)). *(low for the anecdote, high for
the regression report)*

**Simulated (Hearth's own simulator, my read-only runs on 2026-10-11).**
- Settings: `this-pc` profile, LRU, prefetch recall 0.8, synthetic Zipf 1.1 with reuse 0.25,
  1,500 tokens, Q4 experts (4.25 bpw), Q8 backbone (8.25 bpw), context 1,024. Calibration
  defaults; the GPU paths are uncalibrated. No files were written.
- Shapes come from Hearth's verified presets
  ([presets.py](../../../hearth/python/hearth/presets.py)). gpt-oss-120b has 117B parameters in
  total and 5.1B active, with MXFP4 MoE weights
  ([model card](https://huggingface.co/openai/gpt-oss-120b)). The simulator models its experts as
  Hearth Q4, which also has 4.25 bpw.

| Model | CPU only | GPU `dense` | GPU `dense+experts` | Usable VRAM 10.5 GiB | VRAM at 500 GB/s |
|---|---|---|---|---|---|
| Qwen3-30B-A3B | 23.2 tok/s | 46.1 | **112.4** (VRAM serves 89% of expert loads; GPU-bound) | 109.1 | 99.8 |
| gpt-oss-120b | 15.2 | 25.8 | **54.7** (65%; DRAM-bound) | 52.5 | 51.7 |

- For comparison, Hearth *measured* about 19–22 tok/s CPU-only on Qwen3-30B-A3B Q4 (brief), so
  the CPU column is plausible.
- The simulator's published Kimi-K2 table gives the GPU lever as 1.37× (1.2 → 1.65 tok/s). It
  needs a LOSSY Q4 backbone to fit 12 GiB, and Kimi-K3's backbone does not fit at all
  ([SIMULATOR.md §8.7–8.8](../../../hearth/docs/SIMULATOR.md)).
- **[inference]** The GPU tier is worth roughly 2–5× when the model's experts fit in RAM, and
  about 1.4× when NVMe dominates. In both cases it is far more than any CPU code-generation gain
  on a DRAM-bound decode.

---

## Implications for Mithril

1. **Mithril v1 needs a GPU-tier store; the GPU backend can be narrow and come second.**
   - **Store.** The store/placement model should treat VRAM as a cache tier with capacity,
     bandwidth and transfer cost from day one. The verified machine has one, and R06/R08 show
     placement decides performance. Retrofitting device placement into a CPU-only semantics is
     the expensive mistake to avoid **[inference]**.
   - **Backend.** The first GPU deliverable should be a *narrow* backend: Q8/Q4/MXFP4 expert
     GEMV, activation quantisation, norms, SwiGLU and rank-order combine. It should emit PTX with
     explicit `.rn` and load through `nvcuda.dll`, which needs no toolkit (F4).
   - **Order of work.** The CPU backend is milestone 1 and the expert-tier GPU backend milestone 2.
     Attention, prefill GEMM and visual generation (R13) follow in v2.
   - **Gating.** All GPU work waits for owner confirmation (F1) and an INV-DEP ruling.
2. **Make INV-DET-3 cross-device for a named canonical core** (recommended, medium-high
   confidence).
   - **The argument.** INV-DET-1 promises identical logits whatever the cache budget, eviction
     policy and pinning ([INVARIANTS.md](../../../hearth/governance/INVARIANTS.md)). With an LRU
     GPU expert cache, whether expert *e* runs on the CPU or the GPU depends on cache state. If
     the two devices compute different bits, logits depend on cache state, which violates
     INV-DET-1. A GPU tier on by default would also violate INV-LOSSLESS-DEFAULT ("Defaults never
     change model output").
   - **Per-device goldens are therefore insufficient** for anything whose placement is dynamic.
     They suit only *statically* placed, opt-in fast paths such as a tensor-core BF16 prefill.
3. **Express numerics as named, versioned contracts, not as backend behaviour [inference].**
   Suggested shape:
   - **`order` specifications are first-class values** attached to every reduction. Examples:
     `lanes(16) then tree(8,4,2,1)`, `blocks(64, exact_i32) then seq`,
     `chunks(256, seq) then seq`. A contract family such as `canon.v1` bundles them. Goldens are
     keyed by contract version, not by device: one hash covers scalar, AVX2, AVX-512, PTX/sm_120,
     and later NEON or Vulkan.
   - **Determinism scope is an effect or type:** `det.cross_device`, `det.device(<target>)`,
     `approx(tol)`. The placement checker rejects any value of device scope that flows into a
     computation whose placement is decided at runtime (cache-driven). Device-specific orders
     (`canon.sm120.tc.v1` using tensor-core MMA, for example) are separate opt-in contracts with
     their own goldens, labelled like LOSSY levers.
   - **Exact accumulators come with overflow proofs.** An `i32` accumulator over a 64-block of
     int8 × int8 is proved bounded (64·127·127 < 2³¹). That proof *licenses reordering*, so
     backends may use VNNI, dp4a or IMMA freely. This is the main source of GPU speed under
     bit-exactness (F8).
   - **Float operations are explicit.** Only `fadd_rn`, `fmul_rn`, `fma_rn`, `fdiv_rn` and
     `fsqrt_rn` exist in canonical code, and there is no implicit contraction. A backend
     implements each operation exactly or refuses to compile; it never falls back silently. That
     rules out Triton's default TF32, Tile IR `reduce`, vendor libm and cuBLAS inside the
     canonical core.
   - **Transcendentals are Mithril source**, in the canonical library, compiled to every target.
     Platform libm is banned from canonical code. This also closes R07's cross-OS hole.
4. **Choose device-neutral canonical orders [inference].** Fixed chunk sizes that depend neither
   on thread count nor on batch are cheap on both CPU and GPU. Fully sequential definitions
   (Hearth's attention over t) are not. The order library should prefer `chunks(c)` forms.
5. **Vendor libraries belong behind device-scoped contracts only.** cuBLAS, cuDNN, FlashAttention
   and Tile IR's `reduce`/`mmaf` give at best same-device determinism (F3, F7). They are fine for
   `det.device` or `approx` paths such as visual generation, and never for the canonical core.
6. **Verification follows the same split.** Run differential CPU-vs-GPU hash tests per kernel per
   contract, and mutation testing on the order specs themselves. A kernel that breaks the order
   fails a hash, which is the same signal Hearth uses today (ADR-0003 consequences).
7. **R13 scope.** Visual generation needs tensor cores (R13) and is therefore a *device-scoped*
   workload. It should not stretch the cross-device contract.

## Implications for Hearth

1. **Fix the record.** The project record should state that the machine has an RTX 5070 that
   Hearth does not use. That is for the owner to do; I did not edit Hearth.
2. **GPU numbers in the simulator.** The `this-pc` profile uses the datasheet VRAM peak (672 GB/s)
   and assumes 12 GiB. The display currently takes about 1.5 GB. My sensitivity runs show only a
   3–11% effect on the headline what-ifs. The profile should still be recalibrated once a GPU
   GEMV is measured, to satisfy INV-HONEST's measured-versus-simulated rule.
3. **Tighten R01's acceptance.** "Bit-identical to CPU kernels or documented tolerance" should
   become **bit-identical for any op whose placement is dynamic (experts)**. Tolerance would be
   allowed only for opt-in, statically placed paths. Otherwise a VRAM expert cache silently
   breaks INV-DET-1 and INV-LOSSLESS-DEFAULT.
4. **NUMERICS changes needed before a GPU backend (each needs an ADR and golden updates):**
   - a canonical transcendental implementation (also needed for Linux/Windows/macOS identity);
   - fixed-chunk attention value accumulation instead of sequential-in-t;
   - possibly a `canon.v2` with explicit FMA, measured first;
   - NaN canonicalisation on the GPU store path;
   - an explicit ban on tensor-core float MMA, cuBLAS and fast-math in canonical kernels.
5. **A positioning opportunity [inference].** Strata and Fiddler compute missed experts on the
   CPU; llama.cpp uploads them over PCIe (R06). With cross-device bit-identity, Hearth's choice
   between those policies becomes a pure cost-model decision with *identical output*. No engine
   I found offers "output independent of what is in VRAM". The PR #29887 anecdote suggests users
   would notice.
6. **INV-DET-1 wording.** Add "compute device placement" to its list of axes once a GPU tier
   exists. Until then, scope it to "fixed binary, ISA and device plan".
7. **Which GPU API.** CUDA through the driver API alone (PTX text, no toolkit) is the shortest
   route on this machine. Vulkan is more portable but needs optional float-control features and
   software division (F7). Either needs an INV-DEP ruling.

## Where the seed discussion is right or wrong

- **C8 (unified host/device language): right in direction, and more relevant than it looked,**
  since this machine has a usable GPU (F1). The unifying mechanism should be *one numeric contract
  plus explicit placement*, not just one binary.
- **C1 (roofline): right.** The GPU adds a 672 GB/s tier. PCIe 5.0 x16 is slower than DRAM, so
  the roofline argues for computing cold experts in place (F2; R08).
- **B2 and the repo tagline ("delving deep into x86-64 silicon"): too narrow.** On the owner's own
  PC, the largest lossless lever is the GPU tier (SIMULATED 3.6–4.8× for in-RAM MoE, F9), not
  x86 µop scheduling. Decode is DRAM-bound, so CPU code generation cannot move it much
  **[inference]**.
- **B6 (vector-width polymorphism): half right.** Width should be abstract in the source. Under
  bit-exactness, though, the *lane count of a reduction is semantics*: 16 lanes map to zmm, two
  ymm and a half-warp. It cannot be chosen freely by the backend (F8).
- **D3 (out-of-core MoE 0.8–2.5 → 12–22 tok/s; 5–9×): the magnitude is plausible only for in-RAM
  low-bit models, and the credit is misplaced.** Measured 12 GB hybrids reach 48–94 tok/s on a
  125B MoE at 2–3 bits. The SSD-bound 4-bit case is 7–8.5 tok/s (F9). The gains come from
  placement and quantisation, not from a language.
- **D4 (speculative DMA hides 70–85%): contradicted.** Hearth measured one-layer-ahead prefetch
  arriving late about 70% of the time when NVMe-bound (brief). Upload-on-miss over PCIe halved
  decode at a 43.5% hit rate (PR #30112).
- **D7 (15–20+ tok/s on out-of-core 100B+ MoE on a desktop): wrong for truly out-of-core 4-bit**
  (7–8.5 tok/s measured by Strata; Kimi-K2 1.2–1.7 SIMULATED). **Right if "out-of-core" means
  "does not fit VRAM, fits RAM"**: gpt-oss-120b at about 55 tok/s SIMULATED here, and about
  30 tok/s on a 5090 per the llama.cpp guide.
- **E1/E7/E8 (CPU AVX-512 rasteriser, DRM/KMS scan-out, 30+ FPS diffusion): misdirected for this
  box.**
  - The GPU exists, and diffusion needs tensor cores (R13).
  - DRM/KMS is a Linux kernel display subsystem ([kernel docs](https://docs.kernel.org/gpu/drm-kms.html)),
    while this machine runs Windows 11 (brief).
  - These are device-scoped workloads outside the canonical core.
- **G1 (study openai/triton, tile-ai/tilelang): right to study them, but neither has a determinism
  contract.** Triton defaults to TF32 for f32 `dot`. TileLang documents none (F7).

## Open questions

1. **Owner decisions:**
   - Is the RTX 5070 in scope for Hearth and Mithril compute?
   - Can the display move to the iGPU?
   - Does `nvcuda.dll` count as an "OS API" under INV-DEP, or is Vulkan required?
2. **Measured cost of canonical GEMV on sm_120.** Prototype a Q4/Q8 expert GEMV with exact integer
   blocks and an `add.rn` epilogue, and compare it with llama.cpp's MMVQ on the same card. This is
   the single number that decides "useful speed". It is unmeasured.
3. **Is INT8 `mma` on sm_120 exact two's-complement int32 accumulation (no saturation without
   `.satfinite`)?** I could not read the PTX `mma` section: the fetched text was truncated. The
   dp4a semantics are confirmed.
4. **Attention redesign.** Which chunk size `c` keeps CPU AVX-512 and GPU decode efficient? Does
   anything change for MLA's absorbed form and for Kimi's KDA linear attention?
5. **Canonical transcendentals.** Port correctly rounded code (CORE-MATH-style, float-only for the
   GPU) or define a fixed polynomial? How fast is each on Zen 5 and sm_120?
6. **`canon.v2` with explicit FMA.** Is the AVX-512 and GPU speed-up worth a full golden reset?
7. **WDDM behaviour.** Do Windows display-driver timeouts or VRAM sharing with the compositor affect
   long kernels or the usable expert tier? Unverified.
8. **Strata.** Does its 53–94 tok/s on the RTX 5070 include speculative decoding? Are its outputs
   identical with the GPU cache on and off?
9. **2026 developments I may have missed.** Without search I could not check for newer published
   CPU-vs-GPU bit-identical LLM inference, PyTorch batch-invariant modes, or cuBLAS batch
   invariance on compute capability 12.x. All three are unverified.

## Sources

Local (Hearth repo, read-only; and local hardware queries):
- ../../../hearth/python/hearth/sim/hardware.py
- ../../../hearth/docs/SIMULATOR.md
- ../../../hearth/tests/py/test_sim.py
- ../../../hearth/governance/tasks.json
- ../../../hearth/governance/decisions/ADR-0003-canonical-numerics.md
- ../../../hearth/docs/NUMERICS.md
- ../../../hearth/governance/INVARIANTS.md
- ../../../hearth/README.md
- ../../../hearth/python/hearth/presets.py
- Local read-only `nvidia-smi` and `Win32_VideoController` queries, 2026-10-11 (no URL)

Web:
- https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
- https://github.com/thinking-machines-lab/batch_invariant_ops
- https://lmsys.org/blog/2025-09-22-sglang-deterministic/
- https://docs.sglang.io/advanced_features/deterministic_inference.html
- https://docs.vllm.ai/en/latest/features/batch_invariance.html
- https://github.com/vllm-project/vllm/issues/27433
- https://vllm.ai/blog/2025-11-10-bitwise-consistent-train-inference
- https://docs.nvidia.com/cuda/cublas/index.html
- https://docs.nvidia.com/cuda/pdf/CUBLAS_Library.pdf
- https://developer.nvidia.com/cuda-gpus
- https://docs.nvidia.com/cuda/floating-point/index.html
- https://docs.nvidia.com/cuda/cuda-compiler-driver-nvcc/index.html
- https://docs.nvidia.com/cuda/parallel-thread-execution/index.html
- https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/mathematical-functions.html
- https://docs.nvidia.com/cuda/cuda-math-api/cuda_math_api/group__CUDA__MATH__SINGLE.html
- https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__MODULE.html
- https://docs.nvidia.com/cuda/tile-ir/latest/sections/semantics.html
- https://docs.nvidia.com/cuda/tile-ir/latest/sections/operations.html
- https://docs.nvidia.com/cuda/cutile-python/operations.html
- https://triton-lang.org/main/python-api/generated/triton.language.dot.html
- https://triton-lang.org/main/python-api/generated/triton.language.reduce.html
- https://github.com/tile-ai/tilelang
- https://docs.vulkan.org/spec/latest/appendices/spirvenv.html
- https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf
- https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5070-family/
- https://arxiv.org/abs/2411.00442 ; https://arxiv.org/html/2411.00442
- https://arxiv.org/html/2412.19437
- https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf
- https://libc.llvm.org/headers/math/index.html
- https://libc.llvm.org/gpu/index.html
- https://core-math.gitlabpages.inria.fr/
- https://arxiv.org/abs/2502.19405 ; https://arxiv.org/html/2502.19405
- https://github.com/gensyn-ai/repop-demo
- https://github.com/microsoft/RepDL ; https://arxiv.org/abs/2510.09180 ; https://arxiv.org/html/2510.09180
- https://arxiv.org/abs/2501.16007
- https://arxiv.org/abs/2506.09501
- https://github.com/Niko1221/Strata
- https://raw.githubusercontent.com/Niko1221/Strata/main/docs/COMMUNITY_BENCHMARKS.md
- https://github.com/ggml-org/llama.cpp/pull/29887
- https://github.com/ggml-org/llama.cpp/pull/30112
- https://github.com/ggml-org/llama.cpp/discussions/15396
- https://www.hardware-corner.net/guides/gpt-oss-offloading-moe-layers/
- https://huggingface.co/openai/gpt-oss-120b
- https://docs.kernel.org/gpu/drm-kms.html
