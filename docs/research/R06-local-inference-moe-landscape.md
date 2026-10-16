# R06 — Local inference and MoE offloading landscape

*Research dossier for Mithril (and the pending Hearth landscape review). Compiled 2026-10-11.
Method note: the shared web-search budget ran out partway through. After that, every claim was
checked by fetching the primary page directly (GitHub repos, PRs, arXiv abstracts, Hugging Face
model cards, vendor docs). Where only an abstract was available, the dossier says so. Numbers are
attributed to whoever measured them. "[inference]" marks my own reasoning or arithmetic.*

---

## Summary

- **Out-of-core MoE on consumer machines went mainstream in 2026.** At least four public engines
  stream routed experts from NVMe and keep the dense part resident or streamed. Three are
  Apache-2.0 or MIT: Colibri (C), kimi-k3-in-c (C99) and rabbit (Rust, MIT/Apache). The fourth,
  PulsarForge (C11, MIT), targets Windows. All four run 744B–2.8T models on 8–128 GB of RAM, at
  **0.05–2.5 tok/s** for the largest models
  ([colibri](https://github.com/JustVugg/colibri), [kimi-k3-in-c](https://github.com/FareedKhan-dev/kimi-k3-in-c),
  [rabbit](https://github.com/ferrumox/rabbit), [pulsarforge](https://github.com/siris9476/pulsarforge)).
  Hearth's niche of "stream experts from NVMe, deterministic, pure C" is no longer unique. Its
  differentiators have to be measured rigor, determinism and the levers below. *(high)*
- **The fastest consumer results come from GPU+RAM hybrids, not NVMe streaming.** Strata (MIT,
  21k stars) decodes a 125B MoE at 53–94 tok/s on a 12 GB RTX 5070 with 64 GB RAM. It keeps
  hot experts in VRAM, holds all experts in RAM and computes misses on the CPU
  ([Strata](https://github.com/Niko1221/Strata)). llama.cpp merged an LRU **GPU expert cache**
  on 2026-10-07. The author measured 1.57–2.20× faster decode with it
  ([PR #29887](https://github.com/ggml-org/llama.cpp/pull/29887)). *(high)*
- **Kimi K3 verified:** 2.8T total / 104B active, 93 layers (69 KDA + 24 Gated MLA), Attention
  Residuals, "Stable LatentMoE" with 896 experts, 16 active, 2 shared, latent dimension 3584 and
  expert hidden size 3072. Weights are **MXFP4 trained with QAT**; activations are MXFP8
  ([MoonshotAI/Kimi-K3](https://github.com/MoonshotAI/Kimi-K3)). For Hearth the important number
  is the **~109 GB BF16 trunk**: on a 64 GB machine even the dense part must be streamed
  ([kimi-k3-in-c README](https://raw.githubusercontent.com/FareedKhan-dev/kimi-k3-in-c/main/README.md)). *(high)*
- **MXFP4 is now the native expert format for many frontier open models.** It covers gpt-oss,
  Kimi K3 and Qwen3.8-Max in rabbit's checkpoint. DeepSeek-V4-Flash ships "FP4" experts, but
  the model card does not say whether that means MXFP4. MXFP4 costs 4.25 bits per weight, the
  same as Hearth's Q4 ([gpt-oss paper](https://arxiv.org/html/2508.10925v1),
  [DeepSeek-V4-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash)). Running these
  models in their native format is lossless, which fits Hearth's INV-LOSSLESS-DEFAULT. *(high)*
- **In the NVMe-bound regime, hit rate is the wrong objective; bytes per token is the right
  one.** Two independent sources agree. In Hearth's own ablation, deeper lookahead raised hit
  rate but slowed decode by 4–23%
  ([Hearth policy-default](https://github.com/pierce-lonergan/hearth/blob/main/docs/results/policy-default.md)).
  In kimi-k3-in-c, the fastest configuration had a 0% resident hit rate and read 79% more
  expert bytes than the slowest, and LRU stayed 25 points below Belady
  ([kimi-k3-in-c README](https://raw.githubusercontent.com/FareedKhan-dev/kimi-k3-in-c/main/README.md)). *(high)*
- **llama.cpp remains the reference for breadth.** It has `--cpu-moe`/`--n-cpu-moe` (Aug 2025),
  an MXFP4 type (Aug 2025), `--fit` auto-placement, `--load-mode dio` (DirectIO) and the GPU
  expert cache (Oct 2026). **ik_llama.cpp** (MIT) is 1.8–5× faster than mainline at CPU prompt
  processing on a Ryzen 7950X, the closest published CPU to Hearth's 9950X
  ([ik_llama.cpp #164](https://github.com/ikawrakow/ik_llama.cpp/discussions/164)). *(high)*
- **KTransformers (Apache-2.0, SOSP 2025)** set the CPU/GPU hybrid pattern: attention on the
  GPU, routed experts on CPU AMX/AVX-512 kernels. Its runtime switch uses AMX only when experts
  average more than 4 tokens and falls back to AVX-512 for decode
  ([KTransformers AMX doc](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/AMX.md)).
  Zen 5 has full-width AVX-512 but the sources say nothing about AMX, so the AVX-512/VNNI path
  is the one that applies to Hearth's machine ([Zen 5](https://en.wikipedia.org/wiki/Zen_5)). *(medium)*
- **Lossy speed tricks are common across the field and should stay opt-in for Hearth.** They
  include fewer experts (KTransformers 6 of 8, AdapMoE −25%, ik_llama "smart expert
  reduction"), low-precision cache-miss experts (HOBBIT, EdgeMoE) and dynamic-k truncation
  (PulsarForge). *(high)*
- **Speculative decoding can hurt MoE offload.** Colibri's research notes measured a 32% loss
  with MTP at about 85% expert hit rate, and its DeepSeek V4 engine keeps speculation off
  ([colibri](https://github.com/JustVugg/colibri)). *(medium)*
- **For Mithril:** none of the gains in this landscape came from instruction-level
  superoptimisation. They came from a short list of things the language must express directly:
  - tiered storage and async I/O with priorities, plus compute that starts as each expert's
    bytes arrive;
  - block-scaled quantization layouts (MXFP4, NVFP4, k-quants, interleaved and tiled repacks);
  - kernel variants chosen by ISA and by runtime batch shape;
  - canonical reduction order;
  - trace-replayable cache and placement policies, judged by a roofline/bytes cost model.

  *[inference, strongly supported]*

---

## Findings

### F1. The target models and formats (2025–2026)

| Model | Total / active | Routed experts (top-k, shared) | Attention | Native weight precision | Source |
|---|---|---|---|---|---|
| Qwen3-30B-A3B | 30.5B / 3.3B | 128 (8) | GQA 32Q/4KV, 48 layers | BF16 | [HF](https://huggingface.co/Qwen/Qwen3-30B-A3B) |
| Qwen3-235B-A22B | 235B / 22B | 128 (8) | GQA 64Q/4KV, 94 layers | BF16 | [HF](https://huggingface.co/Qwen/Qwen3-235B-A22B) |
| Qwen3-Next-80B-A3B | 80B / 3B | 512 (10, +1 shared), expert dim 512 | 3:1 Gated DeltaNet : gated attention, 48 layers, MTP | BF16 | [HF](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct) |
| DeepSeek-V3 | 671B / 37B | 256 (8, +1 shared), 3 dense layers of 61, expert dim 2048 | MLA (kv_lora 512), 1 MTP layer | FP8 E4M3, 128×128 blocks | [paper](https://arxiv.org/abs/2412.19437), [config](https://huggingface.co/deepseek-ai/DeepSeek-V3/blob/main/config.json) |
| DeepSeek-V3.2-Exp | ~671–685B | V3.1-Terminus base | + DeepSeek Sparse Attention (indexer) | FP8 | [HF](https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Exp) |
| DeepSeek-V4-Flash | 284B / 13B | not stated on card | CSA + HCA hybrid, 1M ctx | **FP4 experts + FP8** rest | [HF](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) |
| Kimi K2 | 1T / 32B | 384 (8, +1 shared), expert dim 2048, 61 layers (1 dense) | MLA, 64 heads | block-FP8; K2-Thinking: INT4 QAT on MoE | [K2](https://huggingface.co/moonshotai/Kimi-K2-Instruct), [K2-Thinking](https://huggingface.co/moonshotai/Kimi-K2-Thinking) |
| **Kimi K3** | **2.8T / 104B** | **896 (16, +2 shared), latent 3584, expert dim 3072, 93 layers (1 dense)** | **69 KDA + 24 Gated MLA, AttnRes, 1M ctx** | **MXFP4 weights (QAT), MXFP8 activations** | [Kimi-K3](https://github.com/MoonshotAI/Kimi-K3) |
| gpt-oss-120b / 20b | 116.8B / 5.1B; 20.9B / 3.6B | 128 (4) / 32 (4) | alternating dense and 128-token banded window, GQA 64Q/8KV | **MXFP4 MoE weights, ~4.25 bpw** | [paper](https://arxiv.org/html/2508.10925v1) |

**Kimi K3, verified.** The brief's guess was "latent MoE + KDA". That is correct but
incomplete. K3 also has Attention Residuals (block-level, over 12-layer blocks in the
kimi-k3-in-c implementation), the SiTU-GLU activation, sigmoid routing with a selection-only
bias, and "Quantile Balancing"
([Kimi-K3](https://github.com/MoonshotAI/Kimi-K3),
[kimi-k3-in-c](https://raw.githubusercontent.com/FareedKhan-dev/kimi-k3-in-c/main/README.md)).
KDA is the linear-attention module from Kimi Linear. It extends Gated DeltaNet with finer
gating and a DPLR transition. At 1M context it reported up to 75% less KV cache and up to 6×
decode throughput versus full MLA, measured at 48B/3B scale
([arXiv 2510.26692](https://arxiv.org/abs/2510.26692)). Each KDA layer carries a fixed
recurrent state; kimi-k3-in-c sizes the total at 96 heads × 128×128 per layer, about 626 MB.
The MXFP4 expert is exactly 17,547,264 bytes, and one token touches about 25.83 GB of routed
experts ([kimi-k3-in-c](https://raw.githubusercontent.com/FareedKhan-dev/kimi-k3-in-c/main/README.md)).

[inference] The arithmetic checks out. One expert has 3 × 3584 × 3072 = 33.03M parameters; at
0.53125 bytes per parameter that is 17.55 MB. One token touches 92 MoE layers × 16 experts,
which comes to 25.8 GB. For comparison, K2 at 4.25 bpw is 60 × 8 × 23.4 MB ≈ 11.2 GB per
token, so K3 needs about 2.3× more expert bytes per token than the K2-shaped container Hearth
already tested.

The trunk is the bigger issue. kimi-k3-in-c packs it to 108.81 GB in BF16, which means about
half of K3's 104B active parameters are dense. That breaks Hearth's "dense resident" assumption
on a 64 GB box.

**Formats.**
- **MXFP4** (OCP MX): E2M1 elements with one E8M0 power-of-two scale per 32 values.
- **NVFP4**: E2M1 elements with one FP8 E4M3 scale per 16 values plus a per-tensor FP32 scale,
  4.5 bpw. NVIDIA claims ≤1% accuracy loss for DeepSeek-R1-0528 PTQ, and Blackwell tensor
  cores support it natively
  ([NVIDIA blog](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/)).
- **MLX** supports `affine` (2–8 bit), `mxfp4`, `mxfp8` and `nvfp4` quantization modes
  ([MLX docs](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html)).

[inference] E2M1 values are {0, 0.5, 1, 1.5, 2, 3, 4, 6}. Doubled they become small integers
{0…12}. An MXFP4×int8 dot product can therefore be computed in **exact integer arithmetic** and
scaled by a power of two afterwards. That makes it compatible with Hearth's bit-exact
canonical-order kernels.

**GGUF types.** llama.cpp's quantize README publishes bits per weight for every type. For
example: IQ1_S 2.00, IQ2_XXS 2.38, IQ3_XXS 3.25, IQ4_XS 4.46, Q4_K_M 4.89, Q6_K 6.56 and Q8_0
8.50. Per-tensor overrides go through `--tensor-type` regexes and imatrix-guided quantization
([quantize README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)).
ik_llama.cpp adds the IQ_K/IQ_KS families, trellis quants IQ1_KT–IQ4_KT, and row-interleaved
R4/R8/R16 variants ([ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp)). ExLlamaV3's EXL3
format is described as a streamlined QTIP variant
([exllamav3](https://github.com/turboderp-org/exllamav3)).

### F2. llama.cpp / ggml (MIT, C/C++)

- **Expert offload.** `--cpu-moe` keeps all MoE weights on the CPU. `--n-cpu-moe N` does the
  same for the first N layers. Both are implemented as tensor overrides, and an explicit `-ot`
  takes priority. slaren merged them on 2025-08-04
  ([PR #15077](https://github.com/ggml-org/llama.cpp/pull/15077)). Community results:
  - gpt-oss-120B on an RTX 3090 went from about 3.4 to 8 tok/s with `--n-cpu-moe 21`
    ([Hardware Corner](https://www.hardware-corner.net/guides/gpt-oss-offloading-moe-layers/)).
  - The official gpt-oss guide reports about 30 tok/s on an RTX 5090 with `--n-cpu-moe 21`,
    and names roughly 8 GB of VRAM as the minimum for 120B
    ([discussion #15396](https://github.com/ggml-org/llama.cpp/discussions/15396)).
- **GPU expert cache (new, Oct 2026).** PR #29887 runs MUL_MAT_ID on host-resident experts on
  the GPU, from an LRU cache that uploads only misses. It applies to batches of ≤32 tokens and
  is ported from the qvac-fabric fork. Author's numbers on an EPYC 7742 with PCIe 4.0 x16,
  model Qwen3.8-Flash-Next Q4_0 with 65.4 GiB of experts:

  | GPU | Setting | Decode | Speed-up | Hit rate |
  |---|---|---|---|---|
  | RTX 4090 | `--fit` default | 25.0 tok/s | 1.00× | – |
  | RTX 4090 | `--fit --moe-cache-mib 6544` | 39.4 tok/s | 1.57× | 72% |
  | RTX 5090 | `-cmoe --moe-cache-mib 19000` | 67.8 tok/s | 2.20× | 89% |

  ([PR #29887](https://github.com/ggml-org/llama.cpp/pull/29887)). The multi-GPU follow-up
  reached 64.39 vs 34.78 tok/s on 2×4090, but **prompt processing fell to 0.73×**. One GLM-5.3
  Flash user reported decode *halving*, from 33 to 16 tok/s, at a 43.5% hit rate
  ([PR #30112](https://github.com/ggml-org/llama.cpp/pull/30112)). A cache that misses heavily
  turns into a PCIe-bound upload loop. *(high, author-reported)*
- **Loading and placement.**
  - `--load-mode {mmap, mlock, mmap+mlock, dio}`. Default `auto` means mmap; `dio` is DirectIO.
  - `--fit` (default on) adjusts unset arguments to fit device memory.
  - `--repack` (default enabled) repacks weights.
  - `--numa {distribute, isolate, numactl}`.

  ([llama-cli manpage](https://dyn.manpages.debian.org/unstable/llama.cpp-tools/llama-cli.1.en.html)).
  [inference] Repacking is on by default, which may explain part of the ~25 vs ~22 tok/s Q4
  decode gap Hearth saw on its noisy run. Hearth's pending larger-than-RAM BF16 head-to-head
  should compare `--load-mode dio` against the default mmap, not only mmap.
- **Formats.** PR #15091 (merged around 2025-08-05) added a new **MXFP4 ggml type**, attention
  sinks and a fused swiglu_oai op. It covered CPU, CUDA, Vulkan and Metal from day one
  ([PR #15091](https://github.com/ggml-org/llama.cpp/pull/15091)). The gpt-oss guide recommends
  running the native MXFP4 files without further quantization
  ([#15396](https://github.com/ggml-org/llama.cpp/discussions/15396)). On Arm, KleidiAI kernels
  are picked at runtime by CPU feature, tensor type and op shape
  ([build.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)).
- **Better than Hearth:** model and format breadth, GPU backends, auto-fit, a mature ecosystem.
  **Worse than Hearth:** no determinism contract, no NVMe-tier expert store with
  demand/prefetch priorities, and the page cache stands in as the "cache policy" when weights
  exceed RAM [inference].

### F3. ik_llama.cpp (MIT, C/C++)

This fork diverged in 2024 and focuses on CPU and CUDA. It adds IQ_K and trellis quants,
`-rtr` row-interleaved repacking, fused FFN ops for MoE (Feb 2025), MLA/FlashMLA for DeepSeek,
"Smart Expert Reduction" (Mar 2025), tensor overrides (Feb 2025), regex-driven custom quant
mixes, and better hybrid MoE offload (May 2025)
([ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp)).

The maintainer's CPU comparison used LLaMA-3.1-8B on a **Ryzen 7950X** (Zen 4) and an M2 Max:

| Workload | Mainline llama.cpp | ik_llama.cpp | Speed-up |
|---|---|---|---|
| PP-512, BF16 | 78.6 tok/s | 256.9 tok/s | 3.27× |
| PP-512, IQ4_XS | 74.4 tok/s | 269.9 tok/s | 3.63× |
| PP-512, IQ3_S | 30.2 tok/s | 156.5 tok/s | 5.18× |
| TG-128, IQ4_XS, 2 threads | 8.15 tok/s | 13.58 tok/s | 1.67× |

The best result was a Q8_K_R8 type at about 370 tok/s PP
([discussion #164](https://github.com/ikawrakow/ik_llama.cpp/discussions/164)).
[inference] The TG gains were measured at 2 threads, where decode is compute-bound. At full
thread counts decode is DRAM-bound and the gap should shrink. The PP gains are the
transferable part: row-interleaved layouts and quant-specific GEMM kernels. That matters for
Hearth's prefill (38 tok/s BF16 streamed; 285–365 tok/s cached Q4).

### F4. KTransformers (Apache-2.0, Python/C++) and SGLang integration

- **Pattern.** MLA attention runs on the GPU and routed experts on the CPU. AMX kernels
  pre-arrange weights into tile layouts (16 rows × 64 B) and fuse Gate and Up. The authors
  measured 21 TFLOPS BF16 and 35 TOPS INT8 on a 4th-gen Xeon. **AMX is used only when experts
  average more than 4 tokens; decode and short prefill switch to an AVX-512 kernel on the same
  layout** ([AMX.md](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/AMX.md)).
- **Measured (DeepSeek-V3 Q4_K_M, 2× Xeon Gold 6454S, DDR5-4800, one RTX 4090D).**

  | Configuration | Decode | Prefill |
  |---|---|---|
  | llama.cpp, 8 experts | 4.51 tok/s | 10.31 tok/s |
  | KTransformers V0.2, 8 experts | 12.21 tok/s | – |
  | KTransformers V0.2, 6 experts (lossy) | 13.69 tok/s | – |
  | KTransformers V0.3 AMX, 8 experts, 2K prompt | – | 255.26 tok/s |

  ([tutorial](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/DeepseekR1_V3_tutorial.md)).
  NUMA handling copies critical matrices to both nodes. *(high, vendor-measured)*
- **kt-kernel (2025–2026).**
  - Back-ends: AMXINT4/INT8, AVX-512 (VNNI/BF16), AVX2/llamafile, RAWINT4 (native INT4 shared
    between CPU and GPU for Kimi-K2-Thinking), FP8.
  - SGLang flags such as `--kt-num-gpu-experts`, `--kt-expert-placement-strategy`
    (uniform/frequency/front-loading/random), `--kt-enable-dynamic-expert-update` and
    `--kt-max-deferred-experts-per-token`.
  - Warns that AMXINT4 can drop accuracy sharply on Qwen3-30B-A3B.

  ([kt-kernel](https://github.com/kvcache-ai/ktransformers/tree/main/kt-kernel)). The README
  lists SGLang integration (Oct 2025), CPU-GPU expert scheduling (Jan 2026) and an SOSP 2025
  paper ([KTransformers](https://github.com/kvcache-ai/ktransformers)).
- **Better than Hearth:** tiled prefill kernels, GPU attention, frequency-based GPU expert
  placement with online updates, NUMA replication. **Not applicable as-is:** AMX (Intel only),
  and the "6 experts" result changes outputs.

### F5. The 2026 disk-streaming engines (direct competitors)

**Colibri, JustVugg/colibri (Apache-2.0, pure C, one file per model family).**
- **Models:** 13 engines, including GLM-5.2/5.3, Kimi K3, DeepSeek V4/V4.1 Flash, MiMo-V2.6,
  Qwen3.8-Flash-Next, Qwen3.6 and OLMoE.
- **Residency:** dense weights in RAM, routed experts on disk behind a per-layer LRU, plus a
  **pinned hot set learned from the user's own conversations** (`.coli_usage`).
- **I/O:** each expert's three matrices are read in one `pread`; loader threads fetch while
  resident experts compute; `DIRECT=1` enables O_DIRECT; `COLI_MODEL_MIRROR` reads from a second
  drive, which measured **+37.5% decode** on two NVMe drives.
- **Extras:** NUMA interleave, cluster mode, and CUDA/Metal/Vulkan/HIP expert tiers.
- **Prediction:** a router-lookahead thread prefetches the next layer; GLM-5.2 routing is 71.6%
  predictable one layer ahead.
- **MTP:** helps on Qwen3.8-Flash-Next (+16–20%) but measured a **32% loss at about 85% hit
  rate**.
- **Measured:** Qwen3.6-35B-A3B at 6.0 tok/s CPU-only on a Ryzen 7 PRO 8700GE and 30 tok/s with
  an RTX 3070. GLM-5.2 (744B) at 1.83 tok/s on a Ryzen AI Max+ 395 with 128 GB, and 0.05–0.1
  tok/s cold on a 25 GB laptop. DeepSeek V4 Flash at 1.24 tok/s on a 5950X with 63 GB. Kimi K3
  at about 9.4 s/token with experts read at 6.3 GB/s.
- **Testing:** CI checks every engine against its reference implementation on tiny fixtures.

([colibri README](https://github.com/JustVugg/colibri)). One aggregator lists about 38k stars,
creation on 2026-07-01 and v1.12.1
([gitnova](https://gitnova.dev/en/r/JustVugg/colibri)). *(high for features; numbers are
project-reported)*

**kimi-k3-in-c, FareedKhan-dev (Apache-2.0, C99 + OpenMP, about 9k stars).**
- **Scope:** full K3 (KDA, Gated MLA, AttnRes, latent MoE). Experts run directly on packed
  MXFP4. The trunk stays BF16 because int8 trunk quantization gave about 1% reconstruction
  error and int4 about 17%.
- **Determinism, the same philosophy as Hearth INV-DET-3:**
  - output is **byte-identical across memory budgets from 8 GB to 224 GB** and across
    Linux/Windows builds;
  - AVX2 and NEON reproduce the scalar order;
  - accumulation is in double precision with a fixed 4-way partition;
  - builds use `-ffp-contract=off`;
  - comparisons are by hashed output bits.
- **I/O:**
  - `pread` with O_DIRECT; no mmap;
  - a **pinned trunk prefix plus a streaming ring** for the remaining trunk layers;
  - trunk layers are now pinned largest-first and read in parallel 64 MiB chunks;
  - expert reads use 1 MiB chunks at queue depth up to 16;
  - the LRU tracks EMPTY and INFLIGHT slot states;
  - fetch runs in three phases: reserve serially, read in disk-offset order, publish.
- **Measured:** on a 2× EPYC 7763 with 228 GB RAM (AVX2, no AVX-512) and O_DIRECT cold reads of
  3.2 GB/s:
  - 26.5 s/token at 8 GB, 19.8 at 64 GB, 5.6 at 128 GB and above;
  - a sustained 10.7–11.8 s/token at 128 GB.
- **Lessons it publishes:**
  - **Trunk-first budget split gave 1.69×** at a fixed 128 GB.
  - The expert cache did nothing below about 36 GB of arena.
  - LRU stayed at 36% while Belady reached 39–62%; Quantile Balancing deliberately flattens
    usage, so there is no hot set.
  - A hit counter that counts prefetches as hits once reported 100% "hits" against a 0% true
    resident hit rate.
  - Three identical runs varied by 33%, so a 5.4% hugepage gain was not claimed.
  - Dropped loads now abort the run with "RUN INVALID".

([README](https://raw.githubusercontent.com/FareedKhan-dev/kimi-k3-in-c/main/README.md),
[CHANGELOG](https://github.com/FareedKhan-dev/kimi-k3-in-c/blob/main/CHANGELOG.md),
[trendshift](https://trendshift.io/repositories/100217)). *(high)*

**rabbit, ferrumox (MIT or Apache-2.0, Rust).**
- **Models:** Qwen3.8-Max (2.446T, 1.37 TB MXFP4), Kimi K3, GLM-5.2 and Kimi Linear 48B.
- **I/O:** io_uring batches with **per-expert early drain**, so an expert's matmul starts when
  its own bytes arrive. `--shard-dirs` splits the checkpoint across two NVMe drives (61%/39%
  read split).
- **Residency:** a usage-learned pinned set (`.rabbit_usage`) and the OS page cache as an extra
  tier.
- **Kernels and formats:** scalar, AVX2 and AVX-512/VNNI kernels; MXFP4, FP8, int2/4/8.
- **Measured:** on a Ryzen AI 9 HX 370 with 123 GB and 2× NVMe:
  - 4.71 s/token on Qwen3.8-Max and 5.93 s/token on K3;
  - **59% of decode time is expert wait, 31% expert matmul, 9% attention/DeltaNet.**
- **Testing:** 461 checkpoint-free tests, including batched-prefill == stepwise and
  session-restore bit-identity.

([rabbit](https://github.com/ferrumox/rabbit)). *(high, project-reported)*

**PulsarForge, siris9476 (MIT, C11, Windows/MSVC first).**
- **Approach:** streams int4 experts from a *USB SSD* through an unbuffered reader with LRU;
  predictive prefetch with a reported **80.8% recall**; demand reads take priority over
  speculative ones.
- **Format:** a **Huffman-compressed container (`.forgezh`)**.
- **Lossy options:** dynamic-k truncation and a cache-aware router.
- **Measured:** on an i7-8550U laptop with 32 GB, GLM-5.2 744B went from about 196 s/token to
  about 4.5 s/token, and Qwen3-30B-A3B runs at about 6.8 tok/s. The author also reports its
  2.17-bit output often failed to terminate where Colibri's int4 did.
- **Practice:** publishes negative results.

([pulsarforge](https://github.com/siris9476/pulsarforge)). *(medium, small project)*

**lumabri:** I could not find this project. The direct URL github.com/lumabri returned 404, and
it does not appear on the topic pages I fetched. *Unverified, so it is not assessed.*

### F6. GPU-hybrid consumer engines

- **Strata, Niko1221 (MIT, C/C++ on ggml, about 21k stars).**
  - **Model:** Qwen3.8-Flash-Next (125B hybrid MoE, 24,576 experts in total, 10 per token).
  - **Placement:** the GPU holds the few thousand most-used experts, RAM holds all of them,
    the CPU computes the rest in parallel, and speculative decoding adds 1.6–1.8×.
  - **Measured:**

    | Hardware | Quant | Decode | Prompt processing |
    |---|---|---|---|
    | RTX 5070 12 GB + Ryzen 5 7600 + 64 GB | Q2_0 | 94 tok/s | 2,650 tok/s |
    | same machine | IQ3_S | 53 tok/s | – |
    | RX 9070 XT 16 GB | Q2_0 | 60 tok/s | – |

    UD-Q4_K_XL is "mostly SSD-bound" at 7–8.5 tok/s on a 64 GB PC.

  ([Strata](https://github.com/Niko1221/Strata)). An NVFP4 fork reports 177 tok/s on an RTX
  5090 + **Ryzen 9 9950X3D** + 128 GB with Windows 11. It uses AVX-512 CPU experts and int8 K/V
  with a Hadamard rotation ([strata-nvfp4](https://github.com/sergqwer/strata-nvfp4)).
  [inference] This is the closest published hardware to Hearth's, and shows what a GPU tier is
  worth when all experts fit in RAM.
- **FreeToken, FlashML-org (Apache-2.0, Python; arXiv 2608.16157).** Authors include Keutzer,
  Song Han, Zaharia and Stoica. Techniques: bandwidth-adaptive CPU-GPU co-execution, global LRU
  expert cache, double-buffered prefill streaming, **runtime VRAM rebalancing between expert
  cache and KV**, and recurrent-state/KV checkpoints. It runs the 753B GLM-5.2 on a single
  workstation GPU. The abstract gives no tok/s figures
  ([repo](https://github.com/FlashML-org/FreeToken), [arXiv](https://arxiv.org/abs/2608.16157)).
- **ExLlamaV3 (MIT).** EXL3 is a QTIP variant; it adds CPU offload for large MoE with AVX2 and
  AVX-512 ([exllamav3](https://github.com/turboderp-org/exllamav3)).
- **Design split in the landscape [inference]:**
  - When an expert misses on the GPU, llama.cpp's cache *uploads* it (PR #29887).
  - Strata and Fiddler *compute it on the CPU* where it already lives.

  The PR #30112 regression shows that upload-on-miss loses at low hit rates. Choosing between
  the two is a cost-model decision.

### F7. Activation sparsity and model co-design

- **PowerInfer (MIT):** hot neurons on the GPU, cold ones on the CPU, with predictors. It
  reported up to 11.69× over llama.cpp on an RTX 4090. The result depends on ReLU-sparse models
  ([PowerInfer](https://github.com/SJTU-IPADS/PowerInfer)).
- **PowerInfer-2:** neuron-cluster I/O pipelining and a segmented neuron cache on phones; 47B
  at 11.68 tok/s on a smartphone ([arXiv 2406.06282](https://arxiv.org/abs/2406.06282)).
- **SmallThinker (21B-A3B, 4B-A0.6B):** a **pre-attention router**, so the engine can prefetch
  experts from storage *during attention*. Both models exceed 20 tok/s Q4_0 on consumer CPUs in
  about 8 GB and 1 GB ([arXiv 2507.20984](https://arxiv.org/abs/2507.20984)).
  [inference] This is the cleanest evidence that *the model* can be designed to hide I/O.
  Hearth's two-step predictor approximates the same thing for models that lack it.
- **LLM in a flash (ACL 2024):** windowing plus **row-column bundling** for larger contiguous
  flash reads; models up to 2× DRAM; 4–5× (CPU) and 20–25× (GPU) over naive loading
  ([arXiv 2312.11514](https://arxiv.org/abs/2312.11514)). Hearth's one-slab-per-expert layout
  and Colibri's single pread per expert are the MoE form of bundling.

### F8. LUT-based low-bit kernels

- **T-MAC (MIT, EuroSys 2025).** It replaces dequantize-and-multiply with bit-plane table
  lookups, and throughput scales linearly as bit width falls. Measured up to 4× over llama.cpp
  and 70% less energy. BitNet-3B runs at 30 tok/s on 1 core and 71 tok/s on 8 cores of an M2
  Ultra, and about 11 tok/s on a Raspberry Pi 5. The project warns that low-bandwidth x86 sees
  smaller gains, and an NPU follow-up ("t-man") arrived in 2025
  ([T-MAC](https://github.com/microsoft/T-MAC), [arXiv 2407.00088](https://arxiv.org/abs/2407.00088)).
- **bitnet.cpp (MIT).** Kernels I2_S, TL1 and TL2, the latter two LUT-based. Measured 2.37–6.17×
  speed-up and 72–82% less energy on x86, and 1.37–5.07× on Arm. It claims a 100B ternary model
  at 5–7 tok/s on one CPU. Parallel-kernel gains of 1.15–2.1× were added in Jan 2026
  ([BitNet](https://github.com/microsoft/BitNet), [arXiv 2410.16144](https://arxiv.org/abs/2410.16144)).
- [inference] On a Zen 5 desktop at 4 bits, decode is DRAM- or NVMe-bound and kernel arithmetic
  is not the bottleneck. LUT kernels matter for Hearth in two cases: making **≤2–3-bit cold
  experts** cheap to compute, and speeding up prefill. Ternary only pays off for models
  *trained* ternary, and no frontier ternary MoE exists in the sources reviewed.

### F9. Research offloading systems: what each one adds

| System | Key mechanism | Reported result | Code license |
|---|---|---|---|
| mixtral-offloading (Eliseev & Mazur) | LRU expert cache (k=2–4), next-layer gate applied to the current hidden state, HQQ 2–3-bit experts | Mixtral 2.0–3.1 tok/s on T4 / 3060 / 3080M / A100 ([html](https://arxiv.org/html/2312.17238)) | MIT ([repo](https://github.com/dvmazur/mixtral-offloading)) |
| MoE-Infinity | request-level activation tracing guides cache and prefetch, batch size 1 | 3.1–16.7× lower per-token latency than vLLM, Ollama, DeepSpeed ([arXiv](https://arxiv.org/abs/2401.14361)) | Apache-2.0 ([repo](https://github.com/EfficientMoE/MoE-Infinity)); now supports DeepSeek-V4-Flash FP4, GLM-5.x, gpt-oss |
| Fiddler (ICLR 2025) | CPU-GPU orchestration instead of weight transfer | 1.26× single-batch, 11.57× beam search ([arXiv](https://arxiv.org/abs/2402.07033)) | (repo efeslab/fiddler; license unverified) |
| HOBBIT | **low-precision versions for less critical cache-miss experts**; token-, layer- and sequence-level policies; built on llama.cpp | up to 9.93× decode ([arXiv](https://arxiv.org/abs/2411.01433)) | unverified |
| ProMoE | proactive caching from intermediate results | decode 2.07× avg (up to 5.02×), prefill 2.20× ([arXiv](https://arxiv.org/abs/2410.22134)) | unverified |
| AdapMoE | sensitivity-based adaptive gating, prefetch, cache management | −25% activated experts, 1.35× ([arXiv](https://arxiv.org/abs/2408.10284)) | unverified |
| Pre-gated MoE | the model selects next-block experts ahead of time (training change) | qualitative only in abstract ([arXiv](https://arxiv.org/abs/2308.12066)) | unverified |
| EdgeMoE | experts on storage, expert-wise bitwidth, preloading prediction | no numbers in abstract ([arXiv](https://arxiv.org/abs/2308.14352)) | unverified |
| MoE-Lightning | CGOPipe CPU-GPU-I/O pipeline; **Hierarchical Roofline Model** policy search | up to 10.3× throughput, Mixtral 8x7B on T4 ([arXiv](https://arxiv.org/abs/2411.11217)) | unverified |
| MoE-Gen | module-based batching (throughput) | 8–31× over FlexGen, MoE-Lightning, DeepSpeed ([arXiv](https://arxiv.org/abs/2503.09716)) | unverified |
| Klotski | expert-aware multi-batch pipeline, correlation prefetcher | up to 85× throughput ([arXiv](https://arxiv.org/abs/2502.06888)) | unverified |
| FineMoE | fine-grained patterns plus prompt semantic hints | −47% latency, +39% hit rate ([arXiv](https://arxiv.org/abs/2502.05370)) | unverified |
| MoE-SpAc (2026) | **speculative-decoding drafts as the expert-lookahead signal**; online integer-programming balancer | +42% TPS over an SD baseline, 4.04× avg ([arXiv](https://arxiv.org/abs/2603.09983)) | unverified |

[inference] Most of these numbers are throughput results (batching, beam search) or GPU-VRAM
results, and their baselines differ. For single-user decode on CPU+NVMe, the transferable ideas
are:
- trace-guided caching (MoE-Infinity);
- mixed precision for misses (HOBBIT/EdgeMoE, lossy);
- a roofline policy model (MoE-Lightning);
- draft tokens as a free lookahead signal (MoE-SpAc).

### F10. vLLM, SGLang, Apple MLX

- **vLLM (Apache-2.0).**
  - `--cpu-offload-gb` uses UVA zero-copy, fetching weights every forward pass.
  - `--offload-backend prefetch` with `--offload-group-size`/`--offload-prefetch-step` gives
    layer-group async prefetch.
  - `--cpu-offload-params` can target expert tensors (example: `mlp.experts.w2_weight`).
  - KV offload goes through `--kv-offloading-backend native|lmcache`.

  There is **no MoE-specific streaming from disk**
  ([engine args](https://docs.vllm.ai/en/latest/configuration/engine_args.html)). The CPU
  backend recommends AVX-512 (Zen 4+), supports BF16/FP16/FP32 and AWQ/GPTQ/W8A8, and offers
  Apple support through the MLX-based vllm-metal plugin
  ([CPU install](https://docs.vllm.ai/en/latest/getting_started/installation/cpu.html)).
- **SGLang (Apache-2.0).** The CPU/GPU MoE hybrid path is KTransformers' kt-kernel (see F4).
- **MLX (MIT).** Unified memory, lazy evaluation, CUDA and CPU backends on Linux, and
  mxfp4/nvfp4 quant modes ([MLX](https://github.com/ml-explore/mlx),
  [quantize](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html)).
  Several 2026 macOS projects stream MoE experts from the SSD (e.g. Routide in Swift+MLX,
  Galactus), per GitHub topic listings
  ([model-offloading](https://github.com/topics/model-offloading),
  [moe-inference](https://github.com/topics/moe-inference)). These are tiny projects with no
  verified numbers.

### F11. Licences: what Hearth may reuse

| Project | Licence | Reuse |
|---|---|---|
| llama.cpp / ggml, ik_llama.cpp, Strata, bitnet.cpp, T-MAC, PowerInfer, MLX, mixtral-offloading, PulsarForge, exllamav3 | MIT | code reusable with attribution |
| Colibri, kimi-k3-in-c, KTransformers, MoE-Infinity, FreeToken, vLLM, SGLang | Apache-2.0 | reusable; preserve NOTICE, state changes |
| rabbit | MIT or Apache-2.0 | reusable |
| Model weights (Kimi K3 License; modified MIT for K2; Qwen licence; MIT for DeepSeek V3.2/V4; Apache-2.0 for gpt-oss) | various | weights keep their own terms ([Kimi-K3](https://github.com/MoonshotAI/Kimi-K3), [K2](https://huggingface.co/moonshotai/Kimi-K2-Instruct), [V4-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash), [gpt-oss](https://huggingface.co/openai/gpt-oss-120b)) |

No GPL or AGPL code turned up among the projects that matter. Hearth's README already credits
the main projects as idea sources and states that no code was copied
([Hearth README](https://github.com/pierce-lonergan/hearth)).

### F12. Cross-cutting evidence: what actually moves decode speed out of core

1. **Bytes per token across tiers dominate.**
   - Rabbit: 59% of decode is expert wait.
   - kimi-k3-in-c: 71.1% I/O share in one workstation run.
   - Hearth: decode tracks NVMe bytes per token better than hit rate, and the 990 PRO saturated
     at about 5.2 GB/s effective (402 MB × 13 tok/s).

   ([rabbit](https://github.com/ferrumox/rabbit),
   [k3-in-c](https://raw.githubusercontent.com/FareedKhan-dev/kimi-k3-in-c/main/README.md),
   [Hearth](https://github.com/pierce-lonergan/hearth/blob/main/docs/results/policy-default.md))
2. **More drives add bandwidth.** Colibri's mirror measured +37.5%; rabbit shards 61/39 across
   two drives.
3. **Budget allocation between tiers matters as much as the eviction policy.** kimi-k3-in-c got
   1.69× from trunk-first allocation, and its cache did nothing below 36 GB.
4. **Prefetch helps only when bandwidth is idle.** Hearth's depth-2 to depth-4 lookahead lost
   4–23% while the drive was saturated.
5. **Usage-learned pinning is now standard** (Colibri, rabbit). Hearth found static pins go
   stale when the task changes, so pins must adapt.
6. **Speculation must be bytes-aware.** Colibri measured an MTP loss at 85% hit rate.
7. **Metric hygiene matters.** Separate prefetched hits from resident hits, refuse silent
   dropped loads, and measure the noise floor (kimi-k3-in-c).

---

## Implications for Mithril

These follow from the evidence above; each is an [inference] about what the language must
express.

1. **Tiered residency and async I/O as first-class semantics.** Every winning engine has the
   same shape. Weights live in a tier (VRAM, DRAM, NVMe×n). An acquire is a future with a
   priority class (demand or prefetch, where demand pre-empts — PulsarForge, Hearth) and is
   cancellable. Compute starts per item as its bytes arrive (rabbit's early drain, Hearth's
   completion-order compute), and placement must never change results (Colibri, kimi-k3-in-c,
   Hearth). Mithril needs typed `resident<tier>` / `streamed<tier>` tensors, alignment
   constraints (4096-B slabs, O_DIRECT), and a portable async-read abstraction that lowers to
   io_uring, IOCP/overlapped I/O, or a pread pool. Determinism under any completion order should
   be a checkable property, not a convention.
2. **Quantization formats as layout types, not "int4 primitives".** A real format is a
   structure:
   - element code (E2M1, int4 with offset, ternary, trellis);
   - block size (16, 32, 64, 256-superblock);
   - scale type (E8M0, E4M3 plus an FP32 tensor scale, f16, 6-bit sub-scales);
   - physical arrangement (row-interleaved R4/R8, AMX 16×64-B tiles, fused gate/up).

   Mithril should describe formats declaratively and derive pack/unpack and dot-product kernels
   from those descriptions. Round-trip and exactness proofs should be machine-checked, in the way
   kimi-k3-in-c checks MXFP4 exactly against checkpoint bytes. Integer-exact fast paths, such as
   MXFP4 doubled to int8, should be found automatically.
3. **Kernels specialised on ISA and on runtime shape.** KTransformers switches between AMX and
   AVX-512 at more than 4 tokens per expert; llama.cpp's GPU cache applies only at ≤32 tokens;
   ik_llama repacks per quant. Mithril must support multiversioned kernels dispatched on CPU
   features and on dynamic batch-per-expert. Seed B10's P/E-core dual paths are a minor case of
   this.
4. **Canonical floating-point order as part of a kernel's type.** Hearth and kimi-k3-in-c both
   obtained cross-ISA bit-identity: fixed reduction trees, no FMA contraction, double or fixed
   16-lane accumulation. The language should make reduction order and contraction explicit and
   verifiable per kernel, GPU kernels included. Colibri notes that GPU float ordering makes long
   outputs drift.
5. **A built-in cost model whose objective is bytes per token per tier.** MoE-Lightning's HRM,
   Hearth's physics equation and the kimi-k3-in-c budget split all show that placement (trunk vs
   cache, GPU vs CPU compute of a miss, prefetch depth) is an optimisation over a roofline model,
   with measurement as the final check. This is where a Darwin-Gödel-style search loop belongs:
   searching placement, precision and policy configurations against measured bytes/token with
   noise floors. It does not belong in µop scheduling of a memory-bound loop.
6. **Policies as replayable, simulatable objects.** Hearth's simulator and kimi-k3-in-c's
   `sim_cache.py` replay traces. Both projects were also wrong in simulation: kimi-k3-in-c's
   simulation was "wrong in both directions", and Hearth's simulated lookahead win was rejected
   on hardware. Mithril should let one policy definition run in simulation and in the engine, and
   attach provenance to every reported number (measured vs simulated, hardware) — Hearth's
   INV-HONEST.
7. **Architecture breadth.** The language must express:
   - recurrent-state layers (KDA, Gated DeltaNet), with a state type that supports checkpoint
     and resume (kimi-k3-in-c state files with checksum and atomic rename; FreeToken's
     recurrent-state anchors);
   - latent and compressed attention (MLA, CSA/HCA, DSA indexers);
   - latent-MoE projections, attention residuals and MTP heads.
8. **Verification harness in the language.** Tiny-random-model teacher forcing against the
   reference is used by kimi-k3-in-c, rabbit (461 tests) and Colibri CI. Malformed-file
   hardening is used by kimi-k3-in-c v1.1 and Hearth INV-FMT. Equivalence of batched and
   stepwise evaluation is checked by rabbit and Hearth INV-DET-2. All of these are generic
   properties Mithril could state once and check everywhere.

---

## Implications for Hearth

Levers are ranked by strength of evidence and fit with Hearth's invariants.

1. **Native MXFP4 experts.** *(high)* MXFP4 is lossless for gpt-oss, Kimi K3, and probably
   DeepSeek-V4-Flash and Qwen3.8-Max. It is the same 4.25 bpw as Hearth's Q4, and it can use
   exact integer dot products [inference]. This is a prerequisite for real K3. kimi-k3-in-c
   (Apache-2.0) and llama.cpp (MIT) are both reference implementations that can be reused with
   attribution. NVFP4 (4.5 bpw, E4M3 scales) is a second step.
2. **Real Kimi K3 support needs a trunk-streaming tier.** *(high)* The BF16 trunk is about
   109 GB and does not fit in 64 GB. kimi-k3-in-c measured 19.8 s/token at 64 GB versus 5.6 at
   128 GB and above. Adopt its pinned-largest-first trunk plus streaming ring, the KDA recurrent
   state (about 626 MB), AttnRes and the latent-MoE projections.
   [inference] Lower bounds on the 990 PRO:
   - routed experts alone, at about 5.2 GB/s effective: about 5 s/token with no cache hits;
   - an opt-in Q8 trunk (about 58 GB, against ~1% reconstruction error per kimi-k3-in-c) would
     make the trunk mostly resident.

   A second NVMe drive is the cheapest multiplier.
3. **Optimise bytes per token, not hit rate.** *(high, Hearth's own data plus kimi-k3-in-c)*
   - Make the tier-budget split (trunk vs expert cache vs KV) a tuned parameter.
   - Use batch-union reads for prefill and speculative verification; kimi-k3-in-c's
     chunk-union prefill read about half the expert bytes.
   - Evaluate lossless entropy coding of expert slabs. PulsarForge ships a Huffman container,
     but its gain is unverified.
   - Report "true resident hit rate" and NVMe MB per token as the primary metrics.
4. **GPU/VRAM tier.** *(high value, medium fit)*
   - Evidence: llama.cpp's LRU GPU cache at about 10% of expert bytes gave 1.57–2.2×; Strata
     reaches 53–177 tok/s on 125B; Colibri has CUDA/Vulkan/Metal tiers.
   - Design lessons:
     - compute misses on the CPU when the hit rate is low (Strata/Fiddler) rather than
       uploading them (the PR #30112 regression);
     - rebalance VRAM between experts and KV at runtime (FreeToken).
   - INV-DET-3 conflict: the GPU tier must either implement the canonical order (slower) or be
     an opt-in tolerance mode.
5. **Usage-learned adaptive pinning.** *(medium)* Colibri and rabbit persist per-user expert
   heat. Hearth's evidence that static pins go stale argues for a persisted prior that decays
   into LRU or fast-decay LFU. It should be validated on K3-style flattened routing (Quantile
   Balancing), where kimi-k3-in-c found no hot set.
6. **Prefill kernels for Zen 5.** *(medium)* The ik_llama row-interleaved repack and its
   quant-specific GEMMs gave 3–5× PP on a 7950X. KTransformers' expert-major tiled layout with a
   batch-size switch also applies. Zen 5 offers full 512-bit AVX-512, VP2INTERSECT and better
   BF16; AMX is not mentioned in the sources. Target AVX-512 VNNI/BF16 tiles. Hearth's roadmap
   item "expert-major chunked prefill with VNNI/AMX" matches.
7. **Gate speculative decoding by a bytes model.** *(medium)* Colibri measured an MTP loss at
   about 85% hit rate and turns speculation off for DeepSeek V4. Hearth's prompt-lookup
   speculation should enable itself only when the predicted extra expert bytes per accepted
   token are favourable. Draft tokens can also feed the predictor (MoE-SpAc).
8. **Close the head-to-head.** *(high priority, from the pending item)* Run llama.cpp Q4_0
   versus Hearth Q4 in RAM on a quiet machine with llama.cpp's default `--repack`. Then run BF16
   larger-than-RAM, comparing llama.cpp `--load-mode dio` against mmap. Publish the noise floor;
   kimi-k3-in-c saw 33% spread.
   [inference] Both engines are below the DRAM roofline. About 22 tok/s at roughly 1.8 GB/token
   is about 40 GB/s against 89.6 GB/s theoretical for DDR5-5600 dual channel
   ([Zen 5](https://en.wikipedia.org/wiki/Zen_5)). The Q4 decode gap is a kernel and layout
   problem worth profiling.
9. **Lossy opt-ins, never defaults.** *(literature-backed)*
   - lower-bit cold or miss experts (HOBBIT/EdgeMoE; Hearth roadmap);
   - reduced or dynamic k (KTransformers 6/8, AdapMoE, ik smart expert reduction, PulsarForge
     dynamic-k).

   Each must report quality deltas, per INV-LOSSLESS-DEFAULT.
10. **Linux io_uring with per-expert early drain, and sharding as an alternative to
    mirroring.** *(medium)* Rabbit does both. Sharding halves the disk cost of using two drives.
11. **Positioning.** *[inference]* Colibri (about 38k stars, 13 engines, GPU tiers) and
    kimi-k3-in-c (determinism, K3) already occupy "pure-C NVMe streaming". Hearth's credible
    breakout is to be the **measured, invariant-governed** engine. That means published
    falsifications (as with the lookahead result), bytes-optimal policies, bit-exact
    CPU/GPU/streamed equivalence, and a Mithril port that proves the language on this workload.

---

## Where the seed discussion is right or wrong

- **C1 (roofline; dual-channel DDR5 about 100 GB/s): right in spirit.** DDR5-5600 dual channel
  is 89.6 GB/s theoretical [inference from
  [Zen 5 memory spec](https://en.wikipedia.org/wiki/Zen_5)]. Out of core, the binding roofline
  is **NVMe (about 3–7 GB/s per drive) and PCIe**, not DRAM. Rabbit's 59% expert wait and
  Hearth's saturated 5.2 GB/s show this.
- **C3 ("60–90% wasted"): unsourced.** A version of it holds for offloaded MoE: 59–71% of time
  is I/O wait (rabbit, kimi-k3-in-c). The causes are storage bandwidth and placement, not
  unfused elementwise ops.
- **C5 (sparsity via VGATHER): mostly wrong for MoE.** MoE sparsity is at expert granularity
  (multi-MB slabs: 17.5 MB in K3, about 23 MB in K2-shaped containers). The tools that work are
  I/O scheduling and batching-by-expert, not gather instructions [inference].
- **C6 (arbitrary bit-width primitives): direction right, mechanism wrong.** Formats are
  block-scaled structures (see Mithril implication 2). The fast low-bit CPU kernels use **table
  lookups** (T-MAC, bitnet.cpp TL1/TL2), not popcount or BMI2.
- **C7 (explicit async pipelines): right, at the wrong layer.** The pipelines that pay off are
  NVMe→DRAM and DRAM→VRAM (Hearth, rabbit, llama.cpp moe-cache), not PREFETCHT0 dozens of
  iterations ahead.
- **D1 (1.58-bit 80B MoE ≈ 16–18 GB): arithmetic fine, premise unsupported.** 80e9 × 1.58/8 ≈
  15.8 GB [inference], but that needs a model *trained* ternary. bitnet.cpp's flagship is 2.4B
  (BitNet b1.58 2B4T), and kimi-k3-in-c measured 17% reconstruction error for int4 PTQ of the K3
  trunk.
- **D2 (300B+ MoE in 64–128 GB without paging): false at ≥4 bpw.** 300B × 4.25/8 ≈ 159 GB
  [inference]. Fitting needs about 3.4 bpw for 128 GB and about 1.7 bpw for 64 GB. Strata fits
  125B on 64 GB only at IQ2/IQ3.
- **D3 (5–9× out-of-core gains to 12–22 tok/s): misframed.**
  - When experts sit in **RAM with a GPU**, real engines already exceed the claimed "after"
    numbers: Strata 53–94 tok/s on 125B; llama.cpp moe-cache 40–68 tok/s.
  - When experts sit on **NVMe** for 700B–2.8T models, measured rates are 0.05–2.5 tok/s
    (Colibri, rabbit, kimi-k3-in-c).
  - Physics caps K3 at about 25.8 GB/token of experts [inference]: even at a 90% hit rate on one
    7 GB/s drive, the bound is under 3 tok/s.
- **D4 ("speculative DMA hides 70–85% of transfer latency"): contradicted where bandwidth binds.**
  Hearth measured one-layer prefetch late about 70% of the time. Deeper prefetch raised hit rate
  but cut decode 4–23% because it adds bytes. Hiding latency does not create bandwidth.
- **D5 (VPOPCNTDQ replaces FMAs): only for binary or ternary models.** It is not used by
  4-bit engines; LUT kernels won instead (F8).
- **D6 (IPC 0.8–1.4 → 2.6–3.8, power −40–60%): unsupported, and IPC is the wrong metric** for
  memory-bound decode. The only sourced energy reductions of that size (55–82%) come from
  bitnet.cpp running *ternary models*, which is a model change.
- **D7 (15–20+ tok/s on out-of-core 100B+ on a desktop):** achievable for about 100–125B models
  when experts fit in RAM and a GPU holds the hot set (Strata). Not achievable when NVMe-bound:
  Colibri CPU-only on Qwen3.8-Flash-Next measured 1.9–4 tok/s.
- **B2/B8/B9 (bypass LLVM; MCTS superoptimiser as the main lever): not supported by this
  landscape.** Every top engine is C, C++ or Rust built with standard compilers plus intrinsics,
  and their gaps to the roofline come from layout, placement and I/O [inference].
- **B11/H1 ("IPC 1.1 → 3.2" as the headline): the wrong headline for this workload.** The honest
  headline metrics are tok/s with bytes per token per tier, the hit rate counted correctly, and
  the noise floor (kimi-k3-in-c, Hearth INV-HONEST).
- **H2 (drop-in C-FFI accelerator): consistent with the landscape.** llama.cpp-derived stacks
  (Strata, ferrumox/fox, HOBBIT built on llama.cpp) show that embedding is how adoption happens.
- **I5/I7 (hot-patching or self-modifying code): no engine in this landscape needs them.**
  Runtime ISA dispatch and policy objects cover the need (Hearth, rabbit, llama.cpp KleidiAI
  dispatch).

---

## Open questions

1. **lumabri:** not located. Ask the user for the URL.
2. **Hearth vs llama.cpp on the 9950X:** where does the Q4 in-RAM decode gap come from — repack,
   kernels, or threading? How does `--load-mode dio` behave for larger-than-RAM BF16? Both still
   need a quiet-machine measurement.
3. **K3 routing locality in true incremental decode.** kimi-k3-in-c's trace used full-recompute
   decoding, which inflates reuse. Does Quantile Balancing really erase hot sets, making caching
   nearly useless below about 36 GB?
4. **Quality cost of an int8 or Q8 K3 trunk.** kimi-k3-in-c reports about 1% reconstruction
   error. Perplexity or KL data are needed before offering it even as opt-in.
5. **What exactly are DeepSeek-V4-Flash "FP4" and Qwen3.8's formats** (MXFP4 or other), and what
   are their expert layouts? The model card did not say.
6. **KTransformers `--kt-max-deferred-experts-per-token`:** is it lossy (deferring expert outputs
   across layers)? Semantics unverified.
7. **Can a GPU kernel reproduce Hearth's canonical order** at a useful speed, or must the GPU
   tier be a tolerance mode?
8. **PulsarForge's Huffman container:** how many bytes does entropy coding save on 4-bit experts,
   and at what decode cost? Unverified.
9. **FreeToken (arXiv 2608.16157)** full-paper numbers, and the KTransformers SOSP 2025 paper's
   measured tables. I read only abstracts and READMEs.
10. **Licences unverified** for Fiddler, HOBBIT, ProMoE, AdapMoE and Strata's bundled
    third-party parts. Check before reusing any code.

---

## Sources

- Hearth: https://github.com/pierce-lonergan/hearth ; https://github.com/pierce-lonergan/hearth/blob/main/docs/results/policy-default.md
- llama.cpp: https://github.com/ggml-org/llama.cpp
- llama.cpp PR #15077 (--n-cpu-moe): https://github.com/ggml-org/llama.cpp/pull/15077
- llama.cpp PR #15091 (gpt-oss, MXFP4): https://github.com/ggml-org/llama.cpp/pull/15091
- llama.cpp PR #29887 (GPU MoE cache): https://github.com/ggml-org/llama.cpp/pull/29887
- llama.cpp PR #30112 (multi-GPU MoE cache): https://github.com/ggml-org/llama.cpp/pull/30112
- llama.cpp gpt-oss guide: https://github.com/ggml-org/llama.cpp/discussions/15396
- llama.cpp quantize README: https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md
- llama.cpp build docs: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
- llama-cli manpage: https://dyn.manpages.debian.org/unstable/llama.cpp-tools/llama-cli.1.en.html
- Developer's Digest on moe-cache: https://www.developersdigest.tech/blog/llama-cpp-moe-offload-n-cpu-moe-vs-moe-cache-2026
- Hardware Corner gpt-oss offload: https://www.hardware-corner.net/guides/gpt-oss-offloading-moe-layers/
- DEV Community MoE offloading: https://dev.to/someoddcodeguy/understanding-moe-offloading-5co6
- ik_llama.cpp: https://github.com/ikawrakow/ik_llama.cpp
- ik_llama.cpp CPU benchmarks: https://github.com/ikawrakow/ik_llama.cpp/discussions/164
- KTransformers: https://github.com/kvcache-ai/ktransformers
- KTransformers DeepSeek tutorial: https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/DeepseekR1_V3_tutorial.md
- KTransformers AMX: https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/AMX.md
- kt-kernel: https://github.com/kvcache-ai/ktransformers/tree/main/kt-kernel
- Colibri: https://github.com/JustVugg/colibri ; https://gitnova.dev/en/r/JustVugg/colibri ; https://gigazine.net/gsc_news/en/20260710-colibri-glm/
- kimi-k3-in-c: https://github.com/FareedKhan-dev/kimi-k3-in-c ; https://raw.githubusercontent.com/FareedKhan-dev/kimi-k3-in-c/main/README.md ; https://github.com/FareedKhan-dev/kimi-k3-in-c/blob/main/CHANGELOG.md ; https://trendshift.io/repositories/100217
- rabbit: https://github.com/ferrumox/rabbit
- PulsarForge: https://github.com/siris9476/pulsarforge
- Strata: https://github.com/Niko1221/Strata ; https://github.com/sergqwer/strata-nvfp4
- FreeToken: https://github.com/FlashML-org/FreeToken ; https://arxiv.org/abs/2608.16157
- ExLlamaV3: https://github.com/turboderp-org/exllamav3
- PowerInfer: https://github.com/SJTU-IPADS/PowerInfer
- PowerInfer-2: https://arxiv.org/abs/2406.06282
- SmallThinker: https://arxiv.org/abs/2507.20984
- bitnet.cpp: https://github.com/microsoft/BitNet ; https://arxiv.org/abs/2410.16144
- T-MAC: https://github.com/microsoft/T-MAC ; https://arxiv.org/abs/2407.00088
- MoE-Infinity: https://arxiv.org/abs/2401.14361 ; https://github.com/EfficientMoE/MoE-Infinity
- Fiddler: https://arxiv.org/abs/2402.07033
- HOBBIT: https://arxiv.org/abs/2411.01433
- ProMoE: https://arxiv.org/abs/2410.22134
- AdapMoE: https://arxiv.org/abs/2408.10284
- Pre-gated MoE: https://arxiv.org/abs/2308.12066
- EdgeMoE: https://arxiv.org/abs/2308.14352
- MoE-Lightning: https://arxiv.org/abs/2411.11217
- LLM in a flash: https://arxiv.org/abs/2312.11514
- mixtral-offloading: https://arxiv.org/abs/2312.17238 ; https://arxiv.org/html/2312.17238 ; https://github.com/dvmazur/mixtral-offloading
- FineMoE: https://arxiv.org/abs/2502.05370
- Klotski: https://arxiv.org/abs/2502.06888
- MoE-Gen: https://arxiv.org/abs/2503.09716
- MoE-SpAc: https://arxiv.org/abs/2603.09983
- vLLM engine args: https://docs.vllm.ai/en/latest/configuration/engine_args.html
- vLLM CPU backend: https://docs.vllm.ai/en/latest/getting_started/installation/cpu.html
- MLX: https://github.com/ml-explore/mlx ; https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html
- Kimi K3: https://github.com/MoonshotAI/Kimi-K3
- Kimi Linear (KDA): https://arxiv.org/abs/2510.26692
- Kimi K2: https://huggingface.co/moonshotai/Kimi-K2-Instruct ; https://huggingface.co/moonshotai/Kimi-K2-Thinking
- gpt-oss: https://huggingface.co/openai/gpt-oss-120b ; https://arxiv.org/html/2508.10925v1
- NVFP4: https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/
- Qwen3: https://huggingface.co/Qwen/Qwen3-30B-A3B ; https://huggingface.co/Qwen/Qwen3-235B-A22B ; https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct
- DeepSeek: https://arxiv.org/abs/2412.19437 ; https://huggingface.co/deepseek-ai/DeepSeek-V3/blob/main/config.json ; https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Exp ; https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash
- Zen 5: https://en.wikipedia.org/wiki/Zen_5
- GitHub topics: https://github.com/topics/moe-inference ; https://github.com/topics/model-offloading ; https://github.com/topics/mixture-of-experts ; https://github.com/topics/moe ; https://github.com/topics/llm-inference ; https://github.com/topics/local-llm
