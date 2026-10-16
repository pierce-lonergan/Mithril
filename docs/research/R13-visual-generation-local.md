# R13 — Local visual generation: reality and scope

*Research dossier for the Mithril architecture phase. Written 2026-10-11. Scope: the seed discussion's visual-generation extension (claims E1–E8) checked against published results, plus a decision on whether and when visual generation belongs in Mithril. Conventions: every factual claim carries an inline source; **[inference]** marks my own reasoning or arithmetic; "unverified" means I could not confirm it. Method note: the shared WebSearch budget ran out early in this task. Most facts below come from primary pages fetched directly (arXiv abstracts and HTML, official GitHub READMEs, vendor pages). Coverage of 2026 work is therefore thinner than I would like. See Open questions.*

---

## Summary

- **Generative video on this CPU is 1–3 orders of magnitude short of real time.** Self-Forcing, the reference real-time system, runs a 1.3B Wan-based model at 832×480. It needs roughly 160–220 TFLOP/s for 16–17 fps. The Ryzen 9 9950X peaks at about 5 TFLOPS FP32, and perhaps about 10 TFLOPS with BF16 dot products. That makes it about 30–40× short at 480p. The seed's 30+ fps target at 720p/1080p (E8) is about 250× short or more. **[inference]**, high confidence on the order of magnitude.
- **Video diffusion transformers are compute-bound, not memory-bound.** A single forward pass processes tens of thousands of latent tokens: 32,760 for Wan 480p/81 frames, 75,600 for Wan 720p, 115,200 for HunyuanVideo 720p. Arithmetic intensity is therefore about N FLOP per weight byte, far above the CPU's ridge point of about 64 FLOP/byte. Hearth's main lesson (decode is bandwidth-bound) does **not** carry over **[inference]**.
- **Attention dominates at video sequence lengths.** In HunyuanVideo, attention takes 800 of 945 s for a 5-second 720p clip ([STA](https://arxiv.org/abs/2502.04507)). My FLOP count for Wan-1.3B gives an attention share of about 70% at 480p and 85% at 720p **[inference]**.
- **Caching and sparse attention are real, measured techniques.** Caching gives 1.3–5× on many-step samplers: PAB 1.34–1.58× on one GPU, TeaCache up to 4.41×, AdaCache up to 4.7×, TaylorSeer 5.0×. Sparse attention gives about 1.4–3.5× end to end: STA 945→685 s training-free and 268 s fine-tuned, SVG 2.3×, VSA 31→18 s, Radial 1.9–3.7×. Quality costs are small but nonzero, and they grow with aggressiveness ([FORA](https://arxiv.org/html/2407.01425): FID 2.27→2.82 at 2.8×, 25.24 at 8.07×).
- **The speed-ups do not multiply.** Few-step distillation removes the step redundancy that caching exploits. Δ-DiT drops from 1.6× at 20 steps to 1.12× in a 4-step setting ([Δ-DiT](https://arxiv.org/abs/2406.01125)).
- **Few-step distillation is the decisive lever.** DMD/DMD2, consistency models (sCM/rCM), rectified flow and adversarial post-training have taken video models to 1–4 steps. Measured results: rCM 15–50× on Wan up to 14B; TurboDiffusion about 100–200× end to end on an RTX 5090; APT2 1 NFE per latent frame at 24 fps, 736×416, on one H100 ([rCM](https://arxiv.org/abs/2510.08431), [TurboDiffusion](https://github.com/thu-ml/TurboDiffusion), [APT2](https://arxiv.org/abs/2506.09350)).
- **Real-time interactive video in 2025–2026 runs on datacenter GPUs or a 24 GB consumer GPU at about 480p.** Self-Forcing: 17 fps on H100, with an unquantified "real-time" claim on RTX 4090. LongLive: 20.7 fps on H100. Matrix-Game 2.0: 25 fps. Matrix-Game 3.0: up to 40 fps at 720p with 5B on A/H-series GPUs. Genie 3: 720p at 20–24 fps, hardware undisclosed. I found **no** CPU-only real-time video generator.
- **3D/4D Gaussian splatting *rendering* is the one visual workload that looks CPU-plausible.** GPUs render Mip-NeRF 360 scenes at 1080p at 286–1,937 fps (Blackwell workstation GPU). My estimate for a well-vectorised AVX-512 CPU rasterizer is about 15–50 fps at 1080p **[inference, unverified: no published CPU benchmark found]**.
- **This machine apparently has a GPU.** Hearth's own simulator profile for `this-pc` lists an RTX 5070 12 GB ([hearth/docs/SIMULATOR.md](../../../hearth/docs/SIMULATOR.md), [hardware.py](../../../hearth/python/hearth/sim/hardware.py)), even though Hearth does not use it. If that is right, local generative video is a GPU question. My scaled estimate for distilled 1.3B 480p video on that card is about 2–12 fps **[inference]**.
- **Recommendation: no visual generation in Mithril v1.** Do not add `Gaussian4D`, `solve_ode`, `rasterize_3dgs_direct` or framebuffer primitives. Instead, v1 should have the general features these workloads share with Hearth:
  - a layout/tile algebra
  - structured and data-dependent block sparsity
  - low-bit numeric types
  - bounded async streaming pipelines
  - an explicit `approx`/cache effect that keeps Hearth's determinism invariants honest

  Use a CPU 3DGS rasterizer and a video-DiT block as **benchmarks**. Generative video should enter scope only once Mithril has a GPU target (v2+).

---

## Findings

### 1. The machine's compute budget (what "local" means here)

**CPU peak.** Desktop Zen 5 has a full 512-bit FP datapath with four FP pipes ([Wikipedia: Zen 5](https://en.wikipedia.org/wiki/Zen_5)). Two of those pipes do FMA, giving 64 FP32 FLOP/cycle/core. Chips and Cheese measured this on a 9900X, the same core ([Chips and Cheese](https://chipsandcheese.com/p/zen-5s-avx-512-frequency-behavior)). Under register-only FMA load a single core stayed near 5.7 GHz. With memory operands it briefly dropped to about 4.7 GHz (same source). All-core sustained AVX-512 clocks on the 9950X are unverified.

- 16 cores × 64 FLOP × ~5 GHz ≈ **5.1 TFLOPS FP32 peak** **[inference]**.
- The CPU exposes AVX512_BF16 and VNNI. Hearth's platform handover expects `avx512bf16`, `avxvnni` and `avx512vnni` on this machine ([H02 handover](../../../hearth/governance/handovers/H02-platform-pool-gen-001.json)).
- BF16 dot products could double the FP32 rate to about 10 TFLOPS, if VDPBF16PS issues at FMA rate. That rate on Zen 5 is unverified.
- Hearth's docs assume about 20 TOPS INT8 VNNI peak ([SIMULATOR.md](../../../hearth/docs/SIMULATOR.md)).
- **Planning figure: 3–6 TFLOP/s sustained on large dense GEMMs** **[inference]**.

**Memory and cache.**
- DRAM: AIDA64 reads about 78 GB/s per Hearth's notes ([SIMULATOR.md](../../../hearth/docs/SIMULATOR.md)). The theoretical figure is 96 GB/s ([Chips and Cheese 9950X](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
- L3: 32 MB per CCD, two CCDs ([Wikipedia: Zen 5](https://en.wikipedia.org/wiki/Zen_5)). Bandwidth is about 1.4 TB/s per CCD with all its cores loaded ([Chips and Cheese 9950X](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
- Ridge point ≈ 5 TFLOPS / 78 GB/s ≈ **64 FLOP/byte** **[inference]**.

**No E-cores.** The 9950X is 16 full Zen 5 cores. The desktop iGPU is a 2-CU RDNA 2 part at up to 2.2 GHz ([Wikipedia: Zen 5](https://en.wikipedia.org/wiki/Zen_5)), which is computationally negligible: about 0.56 TFLOPS FP32 **[inference from spec]**.

**GPU reference points.**

| Device | Dense tensor throughput |
|---|---|
| H100 SXM | ≈ 989 TFLOPS BF16 (vendor lists 1,979 *with sparsity*) ([NVIDIA](https://www.nvidia.com/en-us/data-center/h100/)) |
| RTX 4090 | 330.3 TFLOPS FP16 ([Wikipedia](https://en.wikipedia.org/wiki/GeForce_RTX_40_series); accumulate precision not stated) |
| RTX 5090 | 419.2 TFLOPS |
| RTX 5070 | 123.5 TFLOPS, 12 GB GDDR7, 672 GB/s ([Wikipedia](https://en.wikipedia.org/wiki/GeForce_RTX_50_series); precision ambiguous) |

An H100 is therefore about 100–200× this CPU on dense BF16 matmul **[inference]**.

**There is probably a GPU in the box.** The brief says "No GPU used by Hearth today." Hearth's simulator profile for `this-pc` lists an RTX 5070 12 GB on PCIe 5.0 x16, about 50 GB/s achievable ([hardware.py](../../../hearth/python/hearth/sim/hardware.py)). This needs owner confirmation, but it changes the answer to "can this machine do local visual generation?"

### 2. 3D Gaussian Splatting: GPU reality, CPU feasibility

**Algorithm (what E1 gestures at).**
- 3DGS represents a scene as 1–5 million anisotropic Gaussians.
- It splits the screen into 16×16 tiles and runs one GPU radix sort per frame over 64-bit keys (tile ID in the high bits, depth in the low 32).
- It alpha-blends front to back per pixel, terminating early once opacity saturates.

Source for all three points: [3DGS paper](https://arxiv.org/html/2308.04079).

**GPU numbers.**
- Original 3DGS on an A6000: 134 fps on Mip-NeRF 360, 154 on Tanks&Temples, 137 on Deep Blending (30K iterations). Model memory was 411–734 MB ([3DGS](https://arxiv.org/html/2308.04079)).
- A 2026 study on an RTX PRO 6000 Blackwell (188 SMs) at 1080p: original 3DGS 286 fps, gsplat 541, FlashGS 893, HiGS 1,937 ([HiGS](https://arxiv.org/html/2606.00352v1)).
- For gsplat at 1080p, binning plus sorting takes 46–60% of frame time and rasterization 26–33%. The mean is 10.1M tile–Gaussian pairs per frame at 1080p with 8×8 tiles (same source).
- Mobile GPUs are much slower, which motivates sorting optimisations: up to 4.1× on sort, 1.7× overall ([mobile 3DGS](https://arxiv.org/abs/2511.16298)).
- A 28 nm ASIC renders 1080p at 129 fps on 0.219 W ([3DGS accelerator](https://arxiv.org/abs/2604.10223)).

**CPU estimate [inference, unverified: no published CPU benchmark found].** Start from gsplat's 10.1M tile–Gaussian pairs at 1080p.
- **Rasterization.** The upper bound is 10.1M × 64 ≈ 6.5×10⁸ pixel–Gaussian evaluations per frame. Each evaluation is about 25–30 FLOP-equivalents (conic quadratic, exp, alpha clamp, 3 colour FMAs, transmittance update). That totals about 16–19 GFLOP. At 20–30% of AVX-512 peak (irregular, partly non-FMA work) this is about 13–19 ms, before early-termination savings.
- **Sort.** Sorting about 10M 64-bit keys with a multithreaded radix sort takes perhaps 10–20 ms.
- **Preprocessing.** Projection and degree-3 SH evaluation are only about 1 GFLOP. But they stream the whole model each frame: about 0.4–0.7 GB, or roughly 6–12 ms at 60–78 GB/s. Compression or culling would cut that.
- **Total.** About 20–60 ms per 1080p frame, i.e. roughly 15–50 fps for large scenes. That is interactive, and better at 720p or with compressed models.

The ASIC paper reports 51.6× model-size reduction at 0.743 dB PSNR cost, which shows how much the memory term can shrink ([accelerator](https://arxiv.org/abs/2604.10223)). This is the one visual workload where a carefully vectorised CPU path is plausible.

**Splats are becoming an output format of generative models.** NVIDIA's Lyra distils a video diffusion model's implicit 3D knowledge into a 3DGS decoder for real-time rendering, and it extends to dynamic scenes ([Lyra](https://arxiv.org/abs/2509.19296)). World Labs' Marble (Nov 2025) exports Gaussian splats and meshes and renders splats in the browser with its open-source Spark renderer ([World Labs](https://www.worldlabs.ai/blog/marble-world-model)). This suggests a realistic CPU-local visual pipeline: generate the world on a GPU or in the cloud once, then render it locally and cheaply **[inference]**.

### 3. 4D / dynamic Gaussians: three incompatible representations

"4D Gaussian" does not name one primitive. Three families published in 2024 parameterise motion in completely different ways:

| Method | Motion representation | Reported speed |
|---|---|---|
| 4DGS, Wu et al., CVPR 2024 | One canonical set of 3D Gaussians, deformed every frame by a HexPlane spatio-temporal encoder plus small MLP heads (position, rotation, scale offsets) ([4DGS](https://arxiv.org/html/2310.08528)) | 82 fps at 800×800, 34 fps at 960×540, 30 fps at 1352×1014, all on RTX 3090. Storage 18–90 MB (same source). |
| Yang et al., ICLR 2024 | True 4D Gaussians: 4D mean, 4D scale, a 4D rotation built from left and right isoclinic quaternions. A 3D Gaussian is obtained per frame by conditioning on t, with marginal temporal opacity used to cull. Appearance uses 4D "spherindrical" harmonics (SH × Fourier in time) ([Yang](https://arxiv.org/html/2310.10642)) | 114 fps on Plenoptic Video. Resolution and GPU not stated on the page. |
| Spacetime Gaussians, Li et al., CVPR 2024 | 3D Gaussians plus temporal opacity and parametric motion/rotation. Neural features replace SH ([STG](https://arxiv.org/abs/2312.16812)) | Lite variant at 8K, 60 fps on RTX 4090. |

**Implication for E1 [inference].** The proposed struct `Gaussian4D { pos vec3, time f16, rot quat, scale vec3, sh_coeffs vec16, alpha f8 }` matches none of the three:
- A single `time` scalar cannot express a temporal extent. That needs at least μt and a temporal scale, or a 4D covariance.
- A single quaternion cannot express a 4D rotation.
- Degree-3 SH has 16 coefficients *per colour channel*, so 48 values, not 16.

The right abstraction is a user-defined record with layout control (SoA/AoSoA, mixed precision), not a language primitive.

### 4. Video diffusion transformers: compute profile

Latent-token arithmetic follows from published VAE compression and patch sizes. For the Wan family:

- tokens = (1 + (F−1)/4) × (H/16) × (W/16), from 4×8×8 VAE compression and a 1×2×2 patchify ([Wan paper](https://arxiv.org/html/2503.20314)).
- Wan-1.3B is d=1536, FFN 8960, 12 heads, 30 layers. Wan-14B is d=5120, FFN 13824, 40 heads, 40 layers ([Wan2.1 README](https://github.com/Wan-Video/Wan2.1)).

| Model (source) | Compression / patch | Example clip | Latent tokens per forward |
|---|---|---|---|
| Wan2.1 ([paper](https://arxiv.org/html/2503.20314)) | VAE 4×8×8, patch 1×2×2 | 832×480, 81 frames | 21×30×52 = **32,760** [inference] |
| Wan2.1 | same | 1280×720, 81 frames | 21×45×80 = **75,600** [inference] |
| HunyuanVideo 13B ([paper](https://arxiv.org/html/2412.03603), [STA](https://arxiv.org/html/2502.04507)) | 4×8×8, latent (30,48,80) | 1280×768, 117 frames | **115,200** (STA paper) |
| Mochi 1, 10B AsymmDiT ([README](https://github.com/genmoai/mochi)) | 8×8 spatial, 6× temporal, 12 ch | 480p | **44,520** visual + 256 text |
| LTX-Video, 1.9B ([abstract](https://arxiv.org/abs/2501.00103); size from [Self-Forcing Table 1](https://arxiv.org/html/2506.08009v2)) | 32×32×8 per token (1:192) | 768×512, 121 frames | ≈16×16×24 = **6,144** [inference] |
| Wan2.2 TI2V-5B ([README](https://github.com/Wan-Video/Wan2.2)) | VAE 4×16×16, with patchify 4×32×32 | 1280×704, 121 frames | ≈31×22×40 = **27,280** [inference] |
| CogVideoX-2B/5B ([README](https://github.com/zai-org/CogVideo)) | 3D VAE, compression not confirmed on fetched pages | 720×480, 49 frames, 8 fps | unverified |

**FLOPs per token per forward pass, Wan-1.3B [inference].**
- **Linear layers.** Per layer: self-attention QKVO 4d², video-side cross-attention Q/O 2d², FFN 2·d·8960. That is about 41.7M parameters per layer, × 30 ≈ 1.25B, so about **2.5 GFLOP/token** for linear layers.
- **Attention.** QKᵀ plus PV cost 4·N·d per layer. At N = 32,760 that is 30 × 4 × 32,760 × 1536 ≈ **6.0 GFLOP/token**, i.e. about 70% of FLOPs. At 720p (N = 75,600) attention is about 13.9 GFLOP versus 2.5 linear, about 85%.
- **Cross-checks.** STA measured 800/945 s in attention for HunyuanVideo 720p ([STA](https://arxiv.org/abs/2502.04507)). Wan's report says attention reaches up to 95% of training time at 1M sequence length ([Wan paper](https://arxiv.org/html/2503.20314)).

**Sanity check against measured GPU timings [inference].**
- One full Wan-1.3B 480p step costs about 8.5 GFLOP × 32,760 ≈ 2.8×10¹⁴ FLOP. With 50 steps and CFG (two passes), a 5-second clip costs about 2.8×10¹⁶ FLOP.
- Wan's README reports about 4 minutes on an RTX 4090 ([README](https://github.com/Wan-Video/Wan2.1)). That implies ≈117 TFLOP/s.
- TurboDiffusion's baseline is 184 s on an RTX 5090 ([TurboDiffusion](https://github.com/thu-ml/TurboDiffusion)). That implies ≈152 TFLOP/s.
- Both are plausible fractions of the cards' dense tensor peaks, so the per-token model is right to within about 2×.

**Arithmetic intensity [inference].** Each forward pass reuses every weight across N ≥ 4,680 tokens (one Self-Forcing chunk), so intensity is ≥ ~4,700 FLOP per weight byte for BF16 weights. That is two orders of magnitude above the CPU ridge of about 64. Video DiTs live on the **compute roof**. They are the opposite regime from Hearth's MoE decode.

**Measured costs today.**
- HunyuanVideo 720p×129 frames at 50 steps: 1,904 s on one GPU, 338 s on 8 GPUs with xDiT. Peak memory 60 GB ([HunyuanVideo README](https://github.com/Tencent-Hunyuan/HunyuanVideo)).
- CogVideoX-5B: about 180 s per clip on A100, about 90 s on H100 ([CogVideo README](https://github.com/zai-org/CogVideo)).
- Wan2.2 TI2V-5B: a 5-second 720p clip in under 9 minutes on a single consumer GPU, which needs ≥24 GB VRAM ([Wan2.2 README](https://github.com/Wan-Video/Wan2.2)).
- HunyuanVideo 1.5 (8.3B): 14 GB minimum VRAM with offload. About 75 s per clip on an RTX 4090 with the 480p I2V step-distilled model ([HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5)).
- LTX-2 (Jan 2026): a 14B video stream plus a 5B audio stream, open weights ([LTX-2 paper](https://arxiv.org/abs/2601.03233)). The repo now ships a 22B "LTX-2.5" transformer with distilled 8+4-step pipelines ([LTX-2 repo](https://github.com/Lightricks/LTX-2)).
- **VAE decode is not free.** Decoding 61 frames at 512×320 takes about 2–3 s and 6–9 GB with the full Hunyuan VAE, versus about 0.5 s and under 0.5 GB with the tiny TAEHV decoder, at some quality cost ([TAEHV](https://github.com/madebyollin/taehv)).

### 5. Step/feature caching (temporal redundancy across denoising steps)

All of these exploit redundancy **across denoising steps**, not across video frames.

| Method | Mechanism | Measured speed-up | Quality cost |
|---|---|---|---|
| FORA ([html](https://arxiv.org/html/2407.01425)) | Reuse attention/MLP outputs every N steps | DiT 250-step: 2.08× (N=2), 2.80× (N=3), 4.57× (N=5), 8.07× (N=10). PixArt-α: 1.54–1.86× | FID 2.27→2.40→2.82→4.97→25.24. PixArt FID-30K 28.15→38.20 |
| Δ-DiT ([abs](https://arxiv.org/abs/2406.01125)) | Cache block *deltas*: rear blocks early, front blocks late | 1.6× (20-step PixArt-α); **1.12× under 4-step consistency sampling** | "Improves in most cases" at 20 steps |
| PAB ([html](https://arxiv.org/html/2408.12588)) | Broadcast attention outputs; ranges differ by attention type (spatial < temporal < cross) | **Single GPU 1.25–1.58×**. 10.5× only with 8×H100 sequence parallelism | VBench 79.22→78.51 (Open-Sora); 80.39→80.30 (Open-Sora-Plan) |
| TeaCache ([abs](https://arxiv.org/abs/2411.19108), CVPR 2025) | Decide reuse from timestep-embedding-modulated input change | Up to 4.41× (Open-Sora-Plan) | −0.07% VBench |
| FasterCache ([abs](https://arxiv.org/abs/2410.19355)) | Dynamic feature reuse plus CFG-Cache (cond/uncond redundancy) | 1.67× (Vchitect-2.0) | "Comparable"; reports that naive adjacent-step reuse degrades quality |
| AdaCache ([abs](https://arxiv.org/abs/2411.02397)) | Per-video caching schedule plus motion regularisation | Up to 4.7× (Open-Sora 720p, 2 s) | Claimed none; no numbers in abstract |
| TaylorSeer ([abs](https://arxiv.org/abs/2503.06923), ICCV 2025) | *Forecast* features by finite-difference Taylor expansion instead of reusing them | 4.99× FLUX, 5.00× HunyuanVideo | "Almost lossless" (FLUX); no video metric in abstract |
| Wan built-in ([paper](https://arxiv.org/html/2503.20314)) | Attention cache plus CFG cache | 1.62× on Wan-14B | not quantified in fetched text |
| RAS ([abs](https://arxiv.org/abs/2502.10389)) | Update only "focus" regions each step, reuse the rest | 2.36× SD3, 2.51× Lumina-Next | Human study "comparable" at 1.6× |

Three conclusions **[inference]**:
1. 2–5× is the realistic training-free band. The seed's "up to 70% fewer FLOPs" (E4) corresponds to 3.3× and sits inside it, on 30–50-step samplers.
2. The quality–speed curve is steep beyond about 3× (FORA).
3. Gains collapse when the step count is already small (Δ-DiT 1.12× at 4 steps). That is precisely the regime real-time systems use.

### 6. Sparse, tiled and low-bit attention

| Method | Idea | Measured result |
|---|---|---|
| Sliding Tile Attention ([abs](https://arxiv.org/abs/2502.04507), [html](https://arxiv.org/html/2502.04507), ICML 2025) | 3D windows over tile-contiguous token order. Tile volume equals the FlashAttention block (B = T³), so every block is fully dense or empty, with no "mixed" masked blocks | Kernel 2.8–17× vs FA2, 1.6–10× vs FA3, 58.79% MFU. HunyuanVideo 945→685 s training-free; 268 s fine-tuned (−0.09% VBench). 70% of attention mass falls in a window covering 15.52% of tokens |
| VSA ([abs](https://arxiv.org/abs/2505.13389), [html](https://arxiv.org/html/2505.13389), NeurIPS 2025) | Trainable coarse-to-fine: pool (4,4,4) = 64-token cubes, pick top-K=32 cubes, then fine attention inside them | Training FLOPs −2.53×. Wan-1.3B DiT time 31→18 s; attention kernel 6×; Wan-14B 1,274→576 s. 85% of FA3 MFU |
| Sparse VideoGen ([abs](https://arxiv.org/abs/2502.01776)) | Online classification of heads as spatial or temporal | 2.28× CogVideoX-v1.5, 2.33× HunyuanVideo |
| SVG2 ([abs](https://arxiv.org/abs/2505.18875)) | k-means semantic permutation into dense blocks | 2.30× HunyuanVideo (PSNR ≤30), 1.89× Wan 2.1 (PSNR ≤26) |
| Radial Attention ([abs](https://arxiv.org/abs/2506.19852), NeurIPS 2025) | O(n log n) mask from spatio-temporal energy decay | 1.9× at default length; up to 3.7× with 4× longer videos; Wan2.1-14B, HunyuanVideo, Mochi |
| HunyuanVideo 1.5 SSTA ([README](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5)) | Selective plus sliding tile attention | 1.87× end to end, 10 s 720p vs FA3 |
| SageAttention ([abs](https://arxiv.org/abs/2410.02367), ICLR 2025) | 8-bit quantised attention | About 2.1× FA2 OPS, "almost no" end-to-end metric loss |

**Lesson for Mithril [inference].** Every winning design converts sparsity into **dense blocks sized to the hardware's matmul tile**:
- STA aligns tiles to the FlashAttention block.
- VSA uses 64-token cubes.
- SVG2 permutes tokens to make blocks dense.

STA explicitly shows that "mixed" (partially masked) blocks waste compute. Speed-ups also scale with sequence length (Radial: 1.9× → 3.7×). Sparsity therefore helps long/high-resolution video most and short real-time chunks least.

### 7. Few-step distillation

- **Consistency models** map noise directly to data: one-step FID 3.55 on CIFAR-10 and 6.20 on ImageNet-64 ([CM](https://arxiv.org/abs/2303.01469)).
- **Rectified flow** learns straight transport paths, giving good results with one Euler step ([RF](https://arxiv.org/abs/2209.03003)).
- **MeanFlow** models average velocity and reaches FID 3.43 at 1 NFE on ImageNet-256, trained from scratch ([MeanFlow](https://arxiv.org/abs/2505.13447)).
- **DMD:** one step, FID 2.62 on ImageNet-64, about 20 fps with FP16 ([DMD](https://arxiv.org/abs/2311.18828)). **DMD2:** FID 1.28, and a 500× inference-cost reduction relative to the teacher ([DMD2](https://arxiv.org/abs/2405.14867)).
- **Video, 2025–2026:**
  - CausVid distils a 50-step bidirectional model into a 4-step causal generator: 9.4 fps on one GPU, VBench-Long 84.27 ([CausVid](https://arxiv.org/abs/2412.07772)).
  - rCM (ICLR 2026) brings Wan up to 14B to 1–4 steps, a 15–50× speed-up, roughly matching DMD2 quality with better diversity ([rCM](https://arxiv.org/abs/2510.08431)).
  - TurboDiffusion combines rCM, low-bit SageAttention, trainable sparse-linear attention and W8A8. On one RTX 5090 (diffusion only, excluding text encoder and VAE) it reports: Wan2.1-1.3B-480p 184→**1.9 s**; Wan2.1-14B-720p 4,767→**24 s**; Wan2.2-I2V-A14B-720p 4,549→38 s. The README notes the checkpoints are not finalised ([TurboDiffusion](https://github.com/thu-ml/TurboDiffusion), [paper](https://arxiv.org/abs/2512.16093)).
  - APT2 does adversarial post-training to **1 NFE per latent frame** ([APT2](https://arxiv.org/abs/2506.09350)).

Distillation shrinks the cost of a clip by one to two orders of magnitude. It also makes ODE-solver sophistication (E2, F5) largely moot: at 1–4 steps the "solver" is a fixed, trained schedule **[inference]**.

### 8. Real-time, interactive and world models (2024–2026)

| System | Real-time result | Hardware | Notes |
|---|---|---|---|
| GameNGen ([abs](https://arxiv.org/abs/2408.14837)) | 20 fps DOOM, PSNR 29.4 | single TPU | 2024 |
| Oasis 500M ([site](https://oasis-model.github.io/)) | 20 fps | not stated on page | open 500M weights; Diffusion Forcing |
| StreamDiffusion ([abs](https://arxiv.org/abs/2312.12491)) | 91.07 fps image-to-image | RTX 4090 | image pipeline, not a video model |
| CausVid ([abs](https://arxiv.org/abs/2412.07772)) | 9.4 fps | single GPU | 4-step DMD, KV cache |
| **Self-Forcing** ([html](https://arxiv.org/html/2506.08009v2), [repo](https://github.com/guandeh17/Self-Forcing)) | **17.0 fps, 0.69 s latency** (chunk-wise); 8.9 fps / 0.45 s frame-wise | single H100 | Wan-1.3B, 832×480, 4 steps, chunks of 3 latent frames, rolling KV cache. README claims "real-time on RTX 4090" with no number, ≥24 GB VRAM. Same table: Wan2.1 0.78 fps; LTX-Video 8.98 fps |
| APT2 ([abs](https://arxiv.org/abs/2506.09350)) | 24 fps, 736×416 | 1×H100 (720p needs 8×H100) | 8B, 1 NFE/latent frame, up to 1 min |
| LongLive ([abs](https://arxiv.org/abs/2509.22622)) | 20.7 fps, up to 240 s | single H100 | 1.3B; frame sink; INT8 inference |
| Krea Realtime 14B ([blog](https://www.krea.ai/blog/krea-realtime-14b)) | 11 fps, about 1 s to first frames | single B200 | Wan-14B distilled via Self-Forcing, 4 steps |
| StreamDiffusionV2 ([abs](https://arxiv.org/abs/2511.07399), MLSys 2026) | 58.28 fps (14B), 64.52 fps (1.3B) | **4×H100** | time to first frame < 0.5 s |
| MotionStream ([abs](https://arxiv.org/abs/2511.01266)) | up to 29 fps, sub-second latency | "single GPU" (type unstated) | Self-Forcing + DMD |
| Matrix-Game 2.0 ([abs](https://arxiv.org/abs/2508.13009), [repo](https://github.com/SkyworkAI/Matrix-Game/tree/main/Matrix-Game-2)) | 25 fps | A100/H100 tested, ≥24 GB | open weights; mouse/keyboard actions |
| Matrix-Game 3.0 ([repo](https://github.com/SkyworkAI/Matrix-Game/tree/main/Matrix-Game-3), Mar 2026) | up to 40 fps at 720p | A/H-series, single or multi-GPU (unclear which) | 5B; 3-step distilled; camera-aware memory |
| HY-World 1.5 / WorldPlay ([repo](https://github.com/Tencent-Hunyuan/HY-WorldPlay), Dec 2025–Jan 2026) | 24 fps, 480p | 72 GB VRAM at sp=1 | 4-step distilled AR |
| Genie 3 ([blog](https://deepmind.google/discover/blog/genie-3-a-new-frontier-for-world-models/), [models page](https://deepmind.google/models/genie/)) | 720p, 20–24 fps, minutes of consistency | undisclosed | via Project Genie, an "experimental research prototype" |

The pattern **[inference]**:
- Real-time at about 480p needs roughly an H100, a well-optimised 1–2B model, and 1–4 steps.
- 720p real-time appears only with multi-GPU or datacenter parts, or undisclosed hardware.
- The smallest consumer card named in any real-time claim is a 24 GB RTX 4090, without a published fps figure.
- No published system runs real-time video generation on a CPU.

### 9. Is CPU-only real-time video generation plausible on this machine? (arithmetic)

All rows assume an optimistic **5 TFLOP/s sustained** on the 9950X, and use the per-token FLOP model from §4 **[inference throughout]**.

| Scenario | FLOP per 5-s clip (81 frames) | CPU time | Throughput |
|---|---|---|---|
| Wan-1.3B 480p, 50 steps + CFG | ≈2.8×10¹⁶ | ≈93 min | ≈0.015 fps |
| Same, 4-step distilled, no CFG | ≈1.1×10¹⁵ | ≈3.7 min | ≈0.36 fps |
| + ~88% sparse attention (STA/VSA-class) | ≈4.3×10¹⁴ | ≈85 s | ≈0.95 fps |
| Self-Forcing-style causal: 4 denoise passes + 1 KV-refresh pass per 3-latent-frame chunk, rolling context | ≈10–13 TFLOP per *output frame* | — | ≈0.4–0.5 fps |
| LTX-class 1:192 latents, ~2B model, **1 step**, DiT only | ≈3×10¹³ | ≈6 s | ≈15–20 fps *before* VAE decode (cost unknown; decoder is large in that design) |
| **E8 target:** 720p @ 30 fps, Wan-class causal model | needs ≈1.3 PFLOP/s sustained | — | ≈250× short |

**Calibration.** Self-Forcing's measured 17 fps on H100 implies about 170–220 TFLOP/s, or 17–22% of dense BF16 peak. That is a plausible utilisation, which supports the model.

**Verdict.**
- At the quality level of published real-time systems (480p, 1.3B, 4 steps), CPU-only generation is about **30–40× short** of real time.
- Fully exploited sparsity and caching still leave it about 15× short.
- E8 (720p/1080p at 30+ fps) is off by two to three orders of magnitude.
- The only corner where the CPU comes within about one order of magnitude combines all of these: extreme-compression latents (LTX-class), 1–2-step distillation, a tiny decoder (TAEHV-class), small models (~0.5–2B) and low resolution. Quality would be noticeably reduced. That is a research curiosity, not a v1 target.
- A CPU anchor point: the most aggressive one-step *image* model, SDXS-512, takes 0.82 s per 512×512 image on an i7-12700 with OpenVINO and a tiny autoencoder ([FastSD CPU](https://github.com/rupeshs/fastsdcpu)).
- stable-diffusion.cpp runs Wan2.1/2.2, LTX-2.x and HunyuanVideo 1.5 on CPU (AVX/AVX2/AVX-512) ([repo](https://github.com/leejet/stable-diffusion.cpp)), but publishes no CPU timings and calls 832×480 "a fast starting point" ([wan.md](https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/wan.md)). Offline CPU video generation is therefore *possible today*. Real-time is not.

**The GPU route on this box [inference].** These projections assume throughput scales with the 5070's dense tensor rate.
- Scaling TurboDiffusion's 1.9 s (RTX 5090, 1.3B 480p, diffusion only) by the 419.2/123.5 tensor-throughput ratio gives about 6.5 s per 81-frame clip on an RTX 5070. That is about **12 fps offline throughput** (DiT only).
- Scaling Self-Forcing's H100 result by the dense-throughput ratio (≈8×) gives about 2 fps at BF16. FP8/INT8 and sparse attention could bring it toward near-real-time at 480p.
- 14B-class models do not fit in 12 GB at 8 bits. They would need DRAM→VRAM layer streaming, see "Implications for Hearth".

### 10. Display path (E7)

DRM/KMS is a Linux kernel interface ([kernel docs](https://docs.kernel.org/gpu/drm-kms.html)). The brief's machine runs Windows 11. There, the low-latency path is the DXGI flip model: with Independent Flip and a frame-latency waitable object it can reach one frame of latency, and tearing-allowed presents can go lower ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model)).

A 1080p RGBA frame is 8.3 MB. Copying it at about 60 GB/s takes about 0.14 ms **[inference]**. Display latency is set by refresh (16.7 ms at 60 Hz) and by generation time, not by whether the copy uses non-temporal stores. Scan-out is an OS integration detail, not a language feature.

---

## Implications for Mithril

1. **No visual-generation primitives in v1.** Do not add `Gaussian4D`, `solve_ode`, `fuse_layers{temporal_residual_skip}`, `rasterize_3dgs_direct(Display::Primary)` or `Layout::SpatioTemporal3D` as built-ins. All are library-level, and E1's struct is not even a stable representation (§3).
2. **Layout/tile algebra is a genuine language feature.** It is shared by GEMM, attention, KV paging, Hearth expert slabs and video. STA's key move is re-indexing tokens so a 3D window becomes whole contiguous blocks with tile volume = kernel block size ([STA](https://arxiv.org/html/2502.04507)). That is a *layout map*, a composable function from logical (t,h,w,c) to storage order. Mithril should let a library define "spatio-temporal tile order" as a layout and let the compiler prove bounds and contiguity. Tile sizes should be derived from register blocking, L1/L2 capacity and the matmul microkernel, not from cache lines. One 64-byte line holds 32 BF16 values, while one 8×8×4 token tile at d=1536 is about 786 KB **[inference]**.
3. **Block sparsity in two flavours.** Language support should cover both:
   - (a) *static/structured* masks computable from geometry: STA windows, radial masks, causal chunks;
   - (b) *dynamic, data-dependent* block selection: VSA top-K cubes, SVG2 clusters, MoE routing.

   Lowering should always produce dense inner blocks plus a block list. Hearth's MoE routing is case (b), so one mechanism serves both workloads. This refines C5: gather/scatter into dense tiles, not per-element predication.
4. **Approximation as an explicit effect.** Step caching, broadcast, forecasting, low-bit attention, INT8 KV, lower-bit cold experts and layer skipping all trade exactness for speed. Mithril should give them a typed `approx` region or effect with:
   - a declared policy, such as interval N, threshold τ on a declared distance, or forecast order;
   - a declared or measured error contract;
   - a compiler-tracked "not bit-exact vs reference" label.

   This keeps Hearth's INV-LOSSLESS-DEFAULT and INV-HONEST enforceable mechanically: approximations are opt-in, visible in types, and reported. Policies (FORA, TeaCache, TaylorSeer) stay in libraries.
5. **Bounded streaming pipelines.** Streaming video systems all need the same machinery:
   - rolling KV caches as fixed-size rings with eviction ([Self-Forcing](https://arxiv.org/html/2506.08009v2));
   - frame sinks and cache refresh ([LongLive](https://arxiv.org/abs/2509.22622));
   - stream-batched denoising ([StreamDiffusion](https://arxiv.org/abs/2312.12491));
   - pipeline-parallel stages ([StreamDiffusionV2](https://arxiv.org/abs/2511.07399)).

   Hearth's reader threads and demand/prefetch queues have the same shape. A language-level async pipeline with bounded buffers, back-pressure and optional deadlines is general (C7) and should be in v1. "Rolling KV cache" itself is a library type.
6. **Low-bit numerics are confirmed as core.** W8A8 GEMMs, INT8/FP8 attention and FP8 GEMM appear throughout real video stacks. Wan reports FP8 GEMM at 1.13× and 8-bit attention at >1.27× ([Wan](https://arxiv.org/html/2503.20314)); see also [TurboDiffusion](https://arxiv.org/abs/2512.16093) and [SageAttention](https://arxiv.org/abs/2410.02367). This supports C6 independently of LLMs.
7. **Two visual benchmarks, not features.**
   - (a) A CPU 3DGS forward rasterizer. It is irregular, sort-heavy and early-exit-heavy, and plausibly real-time on this CPU, so it tests segmented arrays, parallel radix sort, masked SIMD early exit and SoA/AoSoA layout switches.
   - (b) A Wan-1.3B DiT block at N = 4,680–32,760 tokens. It is the compute-bound counterpoint to Hearth's memory-bound decode and tests GEMM tiling plus block-sparse attention.

   Both are good acid tests for the claim that Mithril beats hand-written C **[inference]**.
8. **The GPU backend is the gate.** All realistic local generative video, real-time or near-real-time, needs tensor-core-class throughput. If the RTX 5070 is real and available, "visual generation" belongs in the same milestone as a Mithril GPU target, or Hearth's GPU/VRAM tier, and not before.

## Implications for Hearth

- **Different physics.** Hearth's bytes/token model assumes decode is bandwidth-bound. Video DiTs are compute-bound, with about N ≥ 4,700 FLOP per weight byte **[inference]**. A CPU-only Hearth should not take on video generation beyond offline demos. Expect roughly 0.4–1 fps at 480p for a distilled 1.3B model (§9).
- **The tiered store is useful for video on a small GPU [inference].** Streaming 14 GB of 8-bit Wan-14B weights over PCIe 5.0 at about 50 GB/s (Hearth's assumption) takes about 0.28 s per denoising step. One 720p/81-frame step of a 14B model is several PFLOP, tens of seconds on a 5070. Streaming overhead is therefore about 1%. Hearth's DRAM slot arena + prefetch could run 14B-class video DiTs on a 12 GB card almost for free. For small causal chunks (4,680 tokens) the overhead rises to perhaps 15–25% unless weights stay resident.
- **Wan2.2 A14B is a timestep-routed MoE.** It has two ~14B experts, high-noise then low-noise, switching once at an SNR threshold: 27B total, 14B active ([Wan2.2](https://github.com/Wan-Video/Wan2.2)). Routing is per *step*, not per token, so Hearth's expert store reduces to one swap per generation.
- **Determinism.** Every cache or sparsity speed-up in §5–6 changes outputs. Under INV-LOSSLESS-DEFAULT they must be opt-in. The routing-trace simulator idea transfers directly: simulate cache-reuse thresholds against recorded per-step feature deltas before shipping a policy **[inference]**.
- **A cheap visual win.** Rendering pre-generated Gaussian-splat worlds (Marble/Lyra-style outputs) is plausibly CPU-real-time and fits Hearth's zero-dependency C ethos. It is a demo, not a roadmap item.

## Where the seed discussion is right or wrong

| Claim | Verdict | Evidence |
|---|---|---|
| **E1** (Gaussian4D primitive, fused AVX-512 tile-sort + blend) | **Half right.** Tile binning + sort + front-to-back blending is the real algorithm, and CPU rendering at interactive rates is plausible **[inference]**. **Wrong** as a language primitive; the struct fields match none of the three published 4D families (48 SH values, not 16; time needs extent or a 4D covariance; 4D rotation needs two quaternions) | [3DGS](https://arxiv.org/html/2308.04079), [Yang](https://arxiv.org/html/2310.10642), [4DGS](https://arxiv.org/html/2310.08528), [STG](https://arxiv.org/abs/2312.16812) |
| **E2** (compiled RK flow-matching solvers with step caches) | **Right** that modern video models are flow-matching (Wan); step caches exist. **Largely moot:** distillation to 1–4 steps (DMD, rCM, APT2 at 1 NFE) leaves little for adaptive RK solvers or Lean-bounded truncation error (**F5**) | [Self-Forcing](https://arxiv.org/html/2506.08009v2), [rCM](https://arxiv.org/abs/2510.08431), [APT2](https://arxiv.org/abs/2506.09350) |
| **E3** (3D causal spatio-temporal tiles 8×8×4 "mapped to cache lines") | **Right instinct:** 3D tiles are central (STA, VSA's 4×4×4 cubes, chunk-causal attention). **Wrong scale:** tiles match matmul/attention block sizes, not 64-byte lines | [STA](https://arxiv.org/html/2502.04507), [VSA](https://arxiv.org/html/2505.13389) |
| **E4** ("~90% features redundant frame-to-frame", CMOVcc skipping, "up to 70% fewer FLOPs") | **90%: unverified**; no source found. The nearest measured figures are RLT's up-to-80% token reduction for video *understanding* models and STA's 70%-of-mass-in-15.5%-of-tokens locality, which is locality, not redundancy. **70%: consistent** with measured step caching (2.8–4.7×) on many-step samplers, at quality cost, and it collapses at few steps. **CMOVcc: wrong mechanism**; predication computes both sides, and real systems compact into dense blocks | [RLT](https://arxiv.org/abs/2411.05222), [STA](https://arxiv.org/html/2502.04507), [FORA](https://arxiv.org/html/2407.01425), [TeaCache](https://arxiv.org/abs/2411.19108), [Δ-DiT](https://arxiv.org/abs/2406.01125) |
| **E5** (denoising "step rings" keep residuals in L3/tile SRAM) | **Mostly wrong for this CPU.** Weights (2.6 GB BF16 even for 1.3B) cannot live in 64 MB of L3. Per-chunk activations (~14 MB per 4,680×1536 BF16 tensor) could. The binding constraint is FLOPs, not traffic **[inference]** | §4 arithmetic; [Zen 5](https://en.wikipedia.org/wiki/Zen_5) |
| **E6** (speculative low-res trajectories on E-cores) | **Not applicable:** the 9950X has 16 identical Zen 5 cores (same for **B10**). The underlying draft-then-refine idea does exist as two-stage pipelines (LTX-2 8+4 steps; HunyuanVideo 1.5 super-resolution to 1080p) and preview decoders (TAEHV) | [Zen 5](https://en.wikipedia.org/wiki/Zen_5), [LTX-2](https://github.com/Lightricks/LTX-2), [HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5), [TAEHV](https://github.com/madebyollin/taehv) |
| **E7** (DRM/KMS scan-out with VMOVNTPS, single-digit-ms latency) | **Wrong platform** (Linux API; target is Windows → DXGI flip model). **Irrelevant optimisation**: the copy is about 0.1 ms; latency is vsync- and compute-bound | [Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model) |
| **E8** (30+ fps interactive 720p/1080p diffusion on consumer workstations) | **False for CPU** by about 250×+ (§9). **Not yet true for consumer GPUs at 720p**: published real-time 720p uses 8×H100 (APT2), A/H-series (Matrix-Game 3.0) or undisclosed hardware (Genie 3). About 480p real-time on a 24 GB consumer GPU is claimed (Self-Forcing on 4090, no number) | §8 table |
| **C1** (roofline) | **Right**, and video DiTs sit on the compute roof, not the bandwidth roof | §4 |
| **C3** ("AI systems waste 60–90% of compute") | **Not supported for tuned video kernels:** STA at 58.79% MFU, VSA at 85% of FA3 MFU, Wan's 8-bit attention claims 95% MFU on H20. End-to-end utilisation in my sanity checks is about 18–70%. Waste exists but is not uniformly 60–90% | [STA](https://arxiv.org/abs/2502.04507), [VSA](https://arxiv.org/abs/2505.13389), [Wan](https://arxiv.org/html/2503.20314) |
| **C5 / C6 / C7** (sparsity, low-bit types, async pipelines) | **Supported** by video evidence: block sparsity, W8A8/INT8/FP8 attention, streaming KV rings | §5–7 |
| **H7** ("nothing combines all of this") | Out of scope here, but in visual AI the combination already exists *as libraries*: TurboDiffusion = distillation + sparse/low-bit attention + W8A8 | [TurboDiffusion](https://arxiv.org/abs/2512.16093) |

## Open questions

1. **Is the RTX 5070 real and usable by Mithril/Hearth?** Hearth's simulator profile says yes; the brief says Hearth uses no GPU. Confirm with the owner. It decides whether visual generation is a v2 GPU-milestone item or out of scope entirely.
2. **Measured CPU numbers.** All-core AVX-512 clocks, sustained BF16 (VDPBF16PS) and INT8 VNNI GEMM throughput on the 9950X are unverified. A Mithril/Hearth microbenchmark should pin the "3–6 TFLOP/s" planning figure.
3. **A CPU 3DGS rasterizer has not been benchmarked publicly, as far as I found.** The 15–50 fps 1080p estimate needs a reference implementation. That would also be a good early Mithril benchmark.
4. **VAE decode on CPU** for high-compression latents (LTX-class decoders, TAEHV) is unmeasured. It may dominate any CPU video pipeline.
5. **Quality of caching under few-step regimes.** Most caching papers evaluate 30–50-step samplers. Evidence for 1–4-step video models is thin (Δ-DiT's 1.12× is image-domain).
6. **2026 coverage gap.** The search budget ran out. I could not systematically check for CPU- or NPU-targeted video models, any public release of Genie-class models, or 2026 consumer-GPU real-time results beyond Matrix-Game 3.0, HY-World 1.5 and LTX-2.x. A follow-up search pass is warranted.
7. **Scope intent.** Does the owner want visual generation at all, or was E1–E8 inherited enthusiasm from the seed chat? The recommendation above assumes it is a "later, if ever" goal.

## Sources

**Local (read-only Hearth repo)**
- hearth/docs/SIMULATOR.md (this-pc hardware profile; RTX 5070; DRAM ~78 GB/s; VNNI ~20 TOPS)
- hearth/python/hearth/sim/hardware.py
- hearth/governance/handovers/H02-platform-pool-gen-001.json (expected CPU flags incl. avx512bf16)

**Hardware**
- https://en.wikipedia.org/wiki/Zen_5
- https://en.wikipedia.org/wiki/Zen_4
- https://chipsandcheese.com/p/zen-5s-avx-512-frequency-behavior
- https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop
- https://www.nvidia.com/en-us/data-center/h100/
- https://en.wikipedia.org/wiki/GeForce_RTX_40_series
- https://en.wikipedia.org/wiki/GeForce_RTX_50_series

**Gaussian splatting (3D/4D)**
- https://arxiv.org/abs/2308.04079 and https://arxiv.org/html/2308.04079
- https://arxiv.org/html/2606.00352v1
- https://arxiv.org/abs/2604.10223
- https://arxiv.org/abs/2511.16298
- https://arxiv.org/abs/2310.08528 and https://arxiv.org/html/2310.08528
- https://arxiv.org/abs/2310.10642 and https://arxiv.org/html/2310.10642
- https://arxiv.org/abs/2312.16812
- https://arxiv.org/abs/2509.19296
- https://www.worldlabs.ai/blog/marble-world-model

**Video diffusion models**
- https://arxiv.org/html/2503.20314
- https://github.com/Wan-Video/Wan2.1
- https://github.com/Wan-Video/Wan2.2
- https://arxiv.org/html/2412.03603
- https://github.com/Tencent-Hunyuan/HunyuanVideo
- https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
- https://arxiv.org/abs/2501.00103
- https://arxiv.org/abs/2601.03233
- https://github.com/Lightricks/LTX-2
- https://arxiv.org/abs/2408.06072
- https://github.com/zai-org/CogVideo
- https://github.com/genmoai/mochi
- https://github.com/madebyollin/taehv

**Caching**
- https://arxiv.org/abs/2407.01425 and https://arxiv.org/html/2407.01425
- https://arxiv.org/abs/2406.01125
- https://arxiv.org/abs/2408.12588 and https://arxiv.org/html/2408.12588
- https://arxiv.org/abs/2411.19108
- https://arxiv.org/abs/2410.19355
- https://arxiv.org/abs/2411.02397
- https://arxiv.org/abs/2503.06923
- https://arxiv.org/abs/2502.10389
- https://arxiv.org/abs/2411.05222

**Sparse / low-bit attention**
- https://arxiv.org/abs/2502.04507 and https://arxiv.org/html/2502.04507
- https://arxiv.org/abs/2505.13389 and https://arxiv.org/html/2505.13389
- https://arxiv.org/abs/2502.01776
- https://arxiv.org/abs/2505.18875
- https://arxiv.org/abs/2506.19852
- https://arxiv.org/abs/2410.02367

**Few-step distillation**
- https://arxiv.org/abs/2303.01469
- https://arxiv.org/abs/2209.03003
- https://arxiv.org/abs/2505.13447
- https://arxiv.org/abs/2311.18828
- https://arxiv.org/abs/2405.14867
- https://arxiv.org/abs/2510.08431
- https://arxiv.org/abs/2512.16093
- https://github.com/thu-ml/TurboDiffusion

**Real-time / interactive / world models**
- https://arxiv.org/abs/2412.07772
- https://arxiv.org/abs/2506.08009 and https://arxiv.org/html/2506.08009v2
- https://github.com/guandeh17/Self-Forcing
- https://arxiv.org/abs/2506.09350
- https://arxiv.org/abs/2509.22622
- https://arxiv.org/abs/2511.07399
- https://arxiv.org/abs/2312.12491
- https://arxiv.org/abs/2511.01266
- https://www.krea.ai/blog/krea-realtime-14b
- https://arxiv.org/abs/2508.13009
- https://github.com/SkyworkAI/Matrix-Game
- https://github.com/SkyworkAI/Matrix-Game/tree/main/Matrix-Game-2
- https://github.com/SkyworkAI/Matrix-Game/tree/main/Matrix-Game-3
- https://github.com/Tencent-Hunyuan/HY-WorldPlay
- https://deepmind.google/discover/blog/genie-3-a-new-frontier-for-world-models/
- https://deepmind.google/models/genie/
- https://arxiv.org/abs/2408.14837
- https://oasis-model.github.io/

**CPU inference tooling**
- https://github.com/rupeshs/fastsdcpu
- https://github.com/leejet/stable-diffusion.cpp
- https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/wan.md
- https://github.com/leejet/stable-diffusion.cpp/blob/master/docs/performance.md

**Display**
- https://docs.kernel.org/gpu/drm-kms.html
- https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model
