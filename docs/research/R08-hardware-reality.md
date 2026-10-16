# R08 — Hardware reality check and roofline ceilings

Scope: what the hardware Hearth and Mithril target can actually do, with sources, and the
decode ceilings it allows on the brief's machine: Ryzen 9 9950X, 64 GB DDR5, one Samsung 990 PRO
PCIe 4.0 NVMe, Windows 11. Claims marked **[inference]** are my own reasoning or arithmetic.
Claims I could not check are marked **unverified**. The shared web-search budget ran out partway
through this dossier. After that I used direct page fetches only, so a few items stay unverified
and are listed under Open questions.

## Summary

- **Batch-1 decode on this machine is limited by bytes moved, and only by bytes moved (high).**
  DDR5-6000 dual-channel has a theoretical peak of 96 GB/s. AIDA64 measures about 77 GB/s on
  9950X boards, and each CCD's Infinity Fabric link caps reads at 64 GB/s. In an all-core run
  the 9950X can execute roughly 340 AVX-512 instructions for every 64-byte line it fetches from
  DRAM. A Q4 GEMV needs about 10 of them **[inference]**. Instruction-level cleverness cannot raise
  decode speed. Only reading fewer bytes, or reading them from a faster tier, can.
- **Qwen3-30B-A3B ceiling (arithmetic below):** Hearth's format (Q4 experts, Q8 dense) reads
  2.27 GB per token, so the ceiling is **~34 tok/s at 77 GB/s** (42 tok/s at the 96 GB/s peak). A
  uniform Q4 model reads 1.66 GB per token, giving **~46 tok/s** (58 at peak). Hearth measures
  19–22 tok/s, which is 43–50 GB/s effective, or 56–65% of measured bandwidth. There is about
  1.5x of honest headroom. A 5x gain is not available.
- **100B-class MoE in RAM:** the active parameter count decides everything. A gpt-oss-120b-shaped
  model (5.1B active) has a ceiling of **15–22 tok/s at 77 GB/s**, but its 60.8 GiB checkpoint
  does not fit in 64 GB alongside the OS. A GLM-4.5-Air-shaped model (12B active) has a ceiling of
  **~11 tok/s** even if it were fully resident.
- **Kimi-K2-class (32B active, 1T total) from one PCIe 4.0 NVMe with a 40 GB cache:** even with
  every expert in DRAM the ceiling is **3.4 tok/s** (Q8 backbone) or 4.5 tok/s (Q4 backbone). At
  plausible hit rates of 50–80% the band is **0.8–2.9 tok/s**, depending on how well I/O overlaps
  compute. Seed claims of 12–22 tok/s out-of-core (D3) and 15–20+ tok/s for 100B+ models (D7) are
  physically impossible for this class of model on this machine.
- **Zen 5 desktop has a real 512-bit datapath** (4×512-bit pipes; 2×512-bit loads and 1×512-bit
  store per cycle), with no AVX-512 clock penalty. Simple SIMD ops now have **2-cycle latency**, and
  it takes about 8 independent chains to saturate the core. Mobile Zen 5 is 256-bit. Supported
  subsets: F/CD/BW/DQ/VL, IFMA, VBMI, VBMI2, VNNI, BF16, BITALG, VPOPCNTDQ, GFNI, VAES,
  VPCLMULQDQ, **VP2INTERSECT**. There is no AVX512-FP16 and no AMX (high).
- **Gathers are a poor primitive on AMD.** A 16-lane VPGATHERDD on Zen 5 issues 64 µops at about
  12.6 cycles throughput, roughly 1.3 elements per cycle. Intel gathers are faster but carry the
  Downfall/GDS microcode mitigation on affected parts. In-register lookup tables (VPERMB at 2 per
  cycle on Zen 5) and contiguous slabs are the right lowering (high).
- **Intel consumer chips have no AVX-512** from Alder Lake through Arrow Lake, Lunar Lake and
  Panther Lake (AVX2 plus AVX-VNNI only). Nova Lake is documented in Intel's ISA-extensions manual
  with AVX10.2/AVX-512, but its 512-bit support on E-cores is reported inconsistently. AMX exists
  only on Xeon (medium-high).
- **Seed systems-level claims I5 and I7 are wrong.** LOCK CMPXCHG16B on Zen 5 runs at about 17–19
  cycles uncontended and is microcoded (26 µops), not "a single cycle". INVD is a ring-0
  instruction that *discards* dirty data, and it plays no part in JIT code patching. x86 needs a
  serializing instruction on the executing core for cross-modifying code, not cache flushes.
- **Seed claims C1 and B7 are roughly right.** C1 says dual-channel DDR5 tops out near 100 GB/s.
  B7 says a mispredict costs 15–20 cycles; Agner Fog measures 15–25 on Zen 5, and Golden Cove's
  best case is 17. **C7's "DRAM→L1 ~200 cycles" is about 2x too optimistic**: 70–77 ns is about
  400–440 cycles at 5.7 GHz.
- **Two cheap upgrades would move Hearth more than any compiler work.** A PCIe 5.0 NVMe drive (or a
  second drive) makes Kimi-class decode DRAM-bound at about 3 tok/s. A GPU that holds the backbone
  removes about 11 GB per token of DRAM traffic. Neither breaks the NVMe-miss bound
  **[inference]**.

## Findings

### 1. AMD Zen 5 desktop core (Ryzen 9 9950X)

**Datapath and clocks.**
- Desktop Ryzen 9000 and EPYC 9005 have the full 512-bit datapath. Mobile Ryzen AI 300/400 parts
  use 256-bit, so 512-bit throughput is halved there
  ([Wikipedia Zen 5](https://en.wikipedia.org/wiki/Zen_5);
  [numberworld teardown](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).
- Granite Ridge (desktop) has 4×512-bit execution pipes:
  - 2 FADD pipes, 2 FMUL/FMA pipes, 4 integer-add/bitwise pipes;
  - 2×512-bit loads and 1×512-bit store per cycle;
  - a 384×512-bit vector register file
  ([numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/);
  [Agner Fog, microarchitecture manual §25](https://www.agner.org/optimize/microarchitecture.pdf)).
- Agner notes that the write unit is 256 bits wide, so 512-bit stores run at half the throughput
  of 256-bit stores
  ([Agner](https://www.agner.org/optimize/microarchitecture.pdf)).
- Chips and Cheese found no clock drop and no transition period when switching to 512-bit code on
  Zen 5
  ([Chips and Cheese](https://chipsandcheese.com/p/zen-5s-avx-512-frequency-behavior)).
- Under a heavy all-core AVX-512 load (y-cruncher BBP) a 9950X averaged about 3.82 GHz at roughly
  183 W ([numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).
- Phoronix measured a +56% geometric mean from enabling AVX-512 on the 9950X across 90 benchmarks,
  against +41% on Zen 4
  ([Phoronix](https://www.phoronix.com/review/amd-zen5-avx-512-9950x)).

**Latency is the new bottleneck.**
- Formerly 1-cycle SIMD ops now have an effective latency of 2 cycles. FADD is 2 cycles when chained
  from another FADD and 3 otherwise; FMUL is 3 and FMA is 4
  ([Agner](https://www.agner.org/optimize/microarchitecture.pdf);
  [numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).
- AVX-512 compares into mask registers take 3, 4 and 6 cycles for 128, 256 and 512 bits
  ([Agner](https://www.agner.org/optimize/microarchitecture.pdf)).
- Yee estimates that about 8-way ILP is needed to saturate Zen 5, against 2-way on earlier AVX-512
  designs ([numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).
- Agner concludes that on Zen 5 latency, not throughput, usually limits performance
  ([Agner](https://www.agner.org/optimize/microarchitecture.pdf)).
- **[inference]** This is where a scheduling-aware compiler can genuinely pay off: prefill GEMMs,
  attention, and reductions with fixed canonical order (Hearth's INV-DET-3). Bandwidth-bound decode
  GEMV gains nothing from it.

**ISA subsets.**
- Zen 4 supports F, CD, VL, DQ, BW, IFMA, VBMI, VBMI2, VPOPCNTDQ, BITALG, VNNI, VPCLMULQDQ, GFNI,
  VAES and BF16. Zen 5 adds VP2INTERSECT. Neither has AVX512-FP16, which Wikipedia lists for Zen 6
  (TBD) ([Wikipedia AVX-512](https://en.wikipedia.org/wiki/AVX-512)).
- Zen 5 also adds 256-bit AVX-VNNI ([Wikipedia Zen 5](https://en.wikipedia.org/wiki/Zen_5)).
- VP2INTERSECT on Zen 5 has 1-cycle throughput at all widths. Tiger Lake's version took about 25
  cycles and 46 µops ([numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).

**Measured instruction costs relevant to the seed (uops.info).**

| instruction | Zen 5 throughput (cycles/instr) | µops | comparison | source |
|---|---|---|---|---|
| VPDPBUSD zmm (int8 dot product) | 0.50 (latency 3) | 1 | Zen 4: 1.0; Alder Lake-P: 1.0; Emerald Rapids: 0.50 | [uops.info](https://uops.info/html-instr/VPDPBUSD_ZMM_ZMM_ZMM.html) |
| VPOPCNTQ zmm | 0.50 | 1 | Zen 4: 1.0; Ice Lake: 1.0 | [uops.info](https://uops.info/html-instr/VPOPCNTQ_ZMM_ZMM.html) |
| VPERMB zmm (64-entry byte LUT) | 0.50 (latency 4–5) | 1 | Zen 4: 1.0; Alder Lake-P: 1.0 | [uops.info](https://uops.info/html-instr/VPERMB_ZMM_ZMM_ZMM.html) |
| VPGATHERDD zmm (16 lanes) | 12.63 | 64 | Zen 4: 16.57/81 µops; Alder Lake-P: 5.75; Emerald Rapids: 6.0 | [uops.info](https://uops.info/html-instr/VPGATHERDD_ZMM_K_VSIB_ZMM.html) |
| VPGATHERDD ymm (8 lanes) | 5.67 | 32 | Zen 4: 8.0; Alder Lake-P: 3.03; Arrow Lake-P: 3.10 | [uops.info](https://uops.info/html-instr/VPGATHERDD_YMM_VSIB_YMM_YMM.html) |
| LOCK CMPXCHG16B m128 | 17.13 (latency 19) | 26 | Zen 4: 10.0/15; Alder Lake-P: 28.8; Arrow Lake-P: 21.0 | [uops.info](https://uops.info/html-instr/CMPXCHG16B_LOCK_M128.html) |
| LOCK CMPXCHG m64 | 19.72 (latency 16) | 6 | Zen 4: 7.93/9; Alder Lake-P: 19.03/19 | [uops.info](https://uops.info/html-instr/CMPXCHG_LOCK_M64_R64.html) |

Notes on the table:
- **Gathers.** A Zen 5 gather delivers about 1.3–1.4 elements per cycle **[inference: 16/12.63,
  8/5.67]**. The core can issue 4 scalar loads per cycle
  ([Agner](https://www.agner.org/optimize/microarchitecture.pdf)), so a scalar-load emulation can
  compete. Yee also reports that Zen 5 gather/scatter "still trails Intel"
  ([numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).
- **Locked operations.** Zen 5 is slower than Zen 4 here, about 2x on uncontended locked ops
  ([uops.info](https://uops.info/html-instr/CMPXCHG_LOCK_M64_R64.html)).

**Front end.**
- Zen 5 has two decode clusters, each 4-wide and fetching 32 bytes per cycle. Agner reports no
  penalty for instructions with many prefixes, and a 6K-entry µop cache that delivers up to 6 µops
  per cycle ([Agner](https://www.agner.org/optimize/microarchitecture.pdf);
  [Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
- **[inference]** Seed B2's "instruction byte lengths to avoid decoder stalls" therefore has low
  value for hot loops on Zen 5. Those loops run from the µop cache.

**Caches.**
- L1I is 32 KB (8-way). L1D is 48 KB (12-way, 4-cycle latency). L2 is 1 MB per core (16-way,
  14 cycles). L3 is 32 MB per 8-core CCD, so the 9950X has 64 MB in total
  ([Wikipedia Zen 5](https://en.wikipedia.org/wiki/Zen_5);
  [Agner](https://www.agner.org/optimize/microarchitecture.pdf)).
- Agner's table lists 96 MB of L3 at about 55 cycles. That is evidently the 3D V-Cache part.
- All-core L3 bandwidth is about 1.4 TB/s, and aggregate L1 bandwidth exceeds 10 TB/s
  ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
- Agner reports that hardware prefetching usually beats explicit software prefetch on Zen 5. He
  also reports a false dependence when a load address is a multiple of 1024 bytes from a preceding
  store ([Agner](https://www.agner.org/optimize/microarchitecture.pdf)).

**Branch mispredict penalty.**

| core | penalty | source |
|---|---|---|
| Zen 4 | 15–18 cycles | [Agner](https://www.agner.org/optimize/microarchitecture.pdf) |
| Zen 5 | 15–25 cycles | [Agner](https://www.agner.org/optimize/microarchitecture.pdf) |
| Zen 5 (AMD optimization guide, quoted secondhand) | 12–18, common case 15 | [TechPowerUp forum quote](https://techpowerup.com/forums/goto/post?id=5319760) (unverified against the PDF) |
| Golden Cove | 17 best case | [AnandTech](https://at-web1.www.anandtech.com/show/16881/a-deep-dive-into-intels-alder-lake-microarchitectures/3); [HWCooling](https://www.hwcooling.net/en/intel-alder-lake-golden-cove-cpu-core-unveiled-microarch-analysis/) |
| Alder Lake P-core | "sometimes exceeding 20" | [Agner](https://www.agner.org/optimize/microarchitecture.pdf) |
| Lion Cove | no published figure found | [Chips and Cheese](https://chipsandcheese.com/p/intels-lion-cove-p-core-and-gaming) discusses only extra recovery cost from L2 misses |

- An AMD engineer raised GCC's Zen 4/5 mispredict cost. That gave about 12% on one SPEC benchmark,
  which suggests the old cost model underestimated the penalty
  ([Phoronix](https://phoronix.com/news/AMD-Zen-5-Mispredict-Cost)).

### 2. Memory system on AM5 (the binding constraint)

**DRAM speed and bandwidth.**
- AMD officially supports DDR5-5600 with two DIMMs (89.6 GB/s theoretical **[inference]**). With
  four DIMMs (4×1R or 4×2R) the official speed is only DDR5-3600, which is 57.6 GB/s
  ([Wikipedia Zen 5](https://en.wikipedia.org/wiki/Zen_5)).
- DDR5-6000 EXPO is technically an overclock. Chips and Cheese tested at 6000 because AMD's
  reviewer guide calls it the sweet spot
  ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
- The theoretical peak at 6000 MT/s is 96 GB/s
  ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).

**Per-CCD cap.**
- Each CCD's Infinity Fabric link moves 32 B/clk read and 16 B/clk write at FCLK 2 GHz. That is
  **64 GB/s read and 32 GB/s write per CCD**
  ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
- **[inference]** Threads confined to one CCD cannot read faster than 64 GB/s. A decode thread pool
  must span both CCDs to reach about 77 GB/s.

**Measured bandwidth.**
- AIDA64 on a 9950X with DDR5-6000 CL28 measured 76.9 GB/s read, 81.3 GB/s write and 72.9 GB/s
  copy, with 76.5 ns latency. A second board measured 75.6 GB/s read
  ([ReHWolution](https://www.rehwolution.it/?p=118349); figures via search summary).
- Hearth's own notes for this PC record about 78 GB/s AIDA64 read. Its simulator assumes about
  60 GB/s achievable for streaming kernels (hearth `docs/SIMULATOR.md`, §2.2).
- Yee measured about 60 GB/s at DDR5-5000. He estimates that a 9950X would need around DDR5-20000
  to stop bottlenecking y-cruncher
  ([numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).

**Latency.**
- DRAM latency is just over 70 ns
  ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
  **[inference]** At 5.7 GHz that is about 400–440 cycles.
- Little's law at 77 GB/s and about 80 ns requires about 6.2 KB in flight, around 96 cache lines
  chip-wide **[inference]**.

**Cross-CCD communication.**
- Core-to-core latency across CCDs was "nearly 200 ns" on launch firmware, against under 80 ns on
  a 7950X3D ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
  I could not verify whether later firmware improved this.
- **[inference]** Barrier-heavy per-layer synchronization across CCDs is not free. At 20 tok/s it
  is negligible. At 100+ tok/s on small models it starts to matter.

**Compute-to-bandwidth ratio.**
- Yee computes break-even at about 340 AVX-512 instructions per 512-bit load from DRAM in an
  all-core run ([numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).
- **[inference]** A Q4 GEMV consumes 64 bytes (128 weights) with roughly 2 VPDPBUSD plus 4–8
  unpack and scale instructions. That uses about 3% of the core's instruction capacity at full
  memory bandwidth. Decode cores are mostly waiting, by design.

### 3. Other CPU targets

**Intel consumer.**
- Alder Lake shipped with AVX-512 fused off, because Gracemont E-cores support only AVX2 and
  threads migrate between core types
  ([Agner §13](https://www.agner.org/optimize/microarchitecture.pdf);
  [Wikipedia AVX-512](https://en.wikipedia.org/wiki/AVX-512)).
- Arrow Lake (October 2024) disables AVX-512 for the same reason. It offers AVX2, FMA3, AVX-VNNI
  and AVX-IFMA, drops SMT, and officially runs DDR5-6400 on CUDIMMs
  ([Wikipedia Arrow Lake](https://en.wikipedia.org/wiki/Arrow_Lake_(microprocessor))).
- Lunar Lake (September 2024) lists AVX2 with no AVX-512 and uses on-package LPDDR5X-8533
  ([Wikipedia Lunar Lake](https://en.wikipedia.org/wiki/Lunar_Lake)).
- Panther Lake (CES, January 2026; Intel 18A; Cougar Cove P-cores and Darkmont E-cores) lists AVX2,
  AVX-VNNI and AVX-IFMA. It does not list AVX-512, AVX10 or APX. It supports LPDDR5X-9600 and
  DDR5-7200 on two channels
  ([Wikipedia Panther Lake](https://en.wikipedia.org/wiki/Panther_Lake_(microprocessor))).
  **[inference]** A 128-bit LPDDR5X-9600 interface is 153.6 GB/s.
- Nova Lake:
  - Intel's ISA-extensions manual reportedly lists AVX10.2 plus AVX-512 for Nova Lake
    ([Guru3D](https://www.guru3d.com/story/intel-avx102-support-arriving-in-nova-lake-processors);
    [IgorsLab](https://www.igorslab.de/en/intel-nova-lake-brings-avx10-2-and-apx-the-technological-liberation-for-the-x86-platform/)).
  - Linux kernel patches are reported to name it as a 512-bit platform on both P- and E-cores
    ([Tom's Hardware headline](https://www.tomshardware.com/pc-components/cpus/avx-512-support-is-reportedly-returning-with-intels-next-gen-nova-lake-cpus-latest-linux-kernel-patches-reveal-p-cores-and-e-cores-will-gain-native-512-bit-execution)).
    Secondary reporting conflicts on the E-core width.
  - Status: medium confidence that Nova Lake has AVX10.2. E-core 512-bit support and the launch
    date are unverified.
- **[inference]** A Mithril x86 backend needs an AVX2 + AVX-VNNI (256-bit) tier for every Intel
  client chip through Panther Lake.

**AMX.**
- AMX is on Xeon only: Sapphire Rapids first, then Granite Rapids, which adds AMX-FP16. It uses 8
  tiles of 16×64 bytes and delivers 2048 INT8 or 1024 BF16 ops per cycle per core on 4th-gen Xeon
  ([Wikipedia AMX](https://en.wikipedia.org/wiki/Advanced_Matrix_Extensions)).
- **[inference]** Zen 5's VNNI peak is 2×64 MACs = 256 int8 ops per cycle per core. AMX is 8x that
  per core, which helps prefill but not decode.
- No AMD or consumer AMX appears in these sources.
- ktransformers ships AMX-INT8/BF16 and AVX-512 kernels for hybrid CPU/GPU MoE inference
  ([ktransformers](https://github.com/kvcache-ai/ktransformers)).

**Apple.**
- M4 is ARMv9.2-A with SME and no SVE. Memory bandwidth is 120 GB/s for M4, 273 GB/s for M4 Pro and
  546 GB/s for M4 Max ([Wikipedia M4](https://en.wikipedia.org/wiki/Apple_M4)).
- M5 (October 2025) has 153.6 GB/s. Wikipedia reports M5 Pro and M5 Max (March 2026) at up to 307
  and 614 GB/s, and an M5 Ultra in August 2026
  ([Wikipedia M5](https://en.wikipedia.org/wiki/Apple_M5)). I did not cross-check these against
  Apple's own pages.
- On M4, SME is FP32-centric at above 2.3 FP32 TFLOPS. JIT-generated SME kernels beat the vendor
  BLAS in most tested configurations
  ([Remke & Breuer, "Hello SME!", arXiv:2409.18779](https://arxiv.org/abs/2409.18779)).
- **[inference]** On Apple, CPU code gets NEON in normal mode and SVE-style instructions only
  inside SME streaming mode.

**ARM SVE.**
- SVE is implemented in A64FX (512-bit) and Graviton3 (2×256)
  ([Wikipedia AArch64](https://en.wikipedia.org/wiki/AArch64)). Apple M4 does not implement it
  ([Wikipedia M4](https://en.wikipedia.org/wiki/Apple_M4)).
- I could not verify SVE status for Snapdragon X or Neoverse V2/N2 parts after the search budget
  ran out (unverified).

### 4. ISA semantics the seed relies on

**Gathers after Downfall/GDS.**
- GDS (CVE-2022-40982) is an Intel vulnerability. Its microcode mitigation slows AVX2/AVX-512
  `vgather*` and CLWB ([Red Hat](https://access.redhat.com/solutions/7027704)).
- Intel reportedly told partners the impact can reach 50% on gather-heavy workloads. Skylake
  through Ice Lake and Tiger Lake are affected; the newest generations at the time were not
  ([Phoronix](https://www.phoronix.com/review/downfall); figures via search summary).
- Red Hat reports low single-digit slowdowns for realistic gather users. Linux can disable the
  mitigation with `gather_data_sampling=off`
  ([Red Hat](https://access.redhat.com/solutions/7027704);
  [Ubuntu](https://ubuntu.com/security/vulnerabilities/gds-downfall)).
- AMD Zen 5 is not affected. Its gathers are slow for microarchitectural reasons (the table in §1).
- Unverified: whether uops.info's Ice Lake and Skylake gather rows (4–5 µops) were measured before
  or after GDS microcode.

**Non-temporal stores and loads.**
- MOVNTDQ and VMOVNTDQ do not allocate in cache. They use write-combining semantics, are weakly
  ordered, need SFENCE or MFENCE before another agent consumes the data, and #GP on misaligned
  addresses (64 B for the 512-bit form)
  ([felixcloutier MOVNTDQ](https://www.felixcloutier.com/x86/movntdq)).
- MOVNTDQA's non-temporal hint is only advisory on ordinary write-back memory, and the CPU may treat
  it as a normal load. It is implemented only on WC memory
  ([felixcloutier MOVNTDQA](https://www.felixcloutier.com/x86/movntdqa)).
- **[inference]** A `streaming` qualifier (B4) can soundly lower *stores* to NT plus a fence. It
  cannot promise cache-bypassing *loads* of weights on normal memory. For batch-1 decode there is no
  weight reuse to protect, since about 1.7 GB per token against 64 MB of L3 leaves nothing to keep.

**Self-modifying and cross-modifying code.**
- The SDM section "Handling Self- and Cross-Modifying Code" still lists two options: a jump after
  modification, or a serializing instruction.
- A July 2025 Xen commit inserts a serializing instruction after patching. It notes that the
  jump-only option may be insufficient (errata) and that a request to drop it is pending
  ([Xen commit](https://lists.xen.org/archives/html/xen-changelog/2025-07/msg00562.html);
  [Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)).
- Linux's `sync_core()` exists specifically for code modified through an alias or on another CPU.
  It uses SERIALIZE where available and IRET-to-self otherwise, and describes CPUID as conventional
  but "nasty" because it usually exits to a hypervisor
  ([linux sync_core.h](https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/include/asm/sync_core.h)).
- SERIALIZE is enumerated by CPUID.07H:EDX[14]
  ([felixcloutier SERIALIZE](https://www.felixcloutier.com/x86/serialize)). I did not verify
  whether Zen 5 supports it.
- For user-space JIT on Linux, `membarrier(MEMBARRIER_CMD_PRIVATE_EXPEDITED_SYNC_CORE)` (since
  4.16, registration required) guarantees that every running thread of the process has executed a
  core-serializing instruction
  ([membarrier(2)](https://manpages.debian.org/bookworm/manpages-dev/membarrier.2.en.html)).
- On Windows, applications that generate or modify code are told to call `FlushInstructionCache`
  ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache)).
- On Apple silicon, JIT requires MAP_JIT, a per-thread W^X toggle and an explicit icache
  invalidate. Apple's page did not render for me, so these details are from general knowledge and
  medium confidence ([Apple](https://developer.apple.com/documentation/apple-silicon/porting-just-in-time-compilers-to-apple-silicon)).

**INVD, WBINVD and CLFLUSH.**
- INVD invalidates caches **without write-back**, so modified data is lost. It requires CPL 0
  ([felixcloutier INVD](https://www.felixcloutier.com/x86/invd)).
- WBINVD writes back and invalidates. It requires CPL 0, is serializing, and its completion time
  scales with cache size, which can delay interrupts
  ([felixcloutier WBINVD](https://www.felixcloutier.com/x86/wbinvd.html)).
- CLFLUSH runs at any privilege level. It evicts one line from every level of the coherence domain
  and writes it back if dirty, but it is not ordered against prefetches or speculative fetches
  ([felixcloutier CLFLUSH](https://www.felixcloutier.com/x86/clflush)).
- **[inference]** None of the three serializes the instruction stream that is already fetched, so
  none of them is the tool for code patching.

**Atomics.**
- LOCK CMPXCHG16B on Zen 5 measures about 19 cycles latency and 17 cycles throughput, microcoded at
  26 µops (table in §1).
- **[inference]** Contended across CCDs, the cost is bounded below by the cross-CCD latency
  (around 100–200 ns class).
- An 8-byte aligned pointer store is already atomic on x86, and TSO gives it release ordering. This
  is SDM Vol. 3A "Guaranteed Atomic Operations" and "Memory Ordering"; I did not re-fetch those
  sections, so medium-high confidence
  ([Intel SDM](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)).
  A between-token hot swap therefore needs a release store plus safe reclamation (RCU or epochs),
  not CMPXCHG16B.

**Hybrid P/E dual code paths (B10).**
- Intel disables ISA features that are not common to both core types so threads can migrate
  freely. Agner argues that per-core-type optimization by applications is unrealistic, and that
  scheduling belongs to the OS and Thread Director
  ([Agner §13](https://www.agner.org/optimize/microarchitecture.pdf)).
- **[inference]** The OS can migrate a thread right after any core-type check, so per-core-type
  code would have to be correct on both types anyway. The 9950X is homogeneous, and Zen 5c shares
  Zen 5's ISA. The right design is per-ISA dispatch at load time (Hearth already does this) plus
  work-stealing that tolerates cores of different speeds.

### 5. Storage and I/O

**NVMe throughput.**
- The 990 PRO is PCIe 4.0 with up to 7,450 MB/s read and 6,900 MB/s write
  ([Samsung](https://www.samsung.com/us/computing/memory-storage/solid-state-drives/990-pro-pcie-4-0-nvme-ssd-2tb-mz-v9p2t0b-am/)).
- A PCIe 4.0 x4 link carries 7.877 GB/s per direction, and PCIe 5.0 x4 carries 15.754 GB/s
  ([Wikipedia PCIe](https://en.wikipedia.org/wiki/PCI_Express)).
- Hearth measured **6.5–7.2 GB/s** on this drive with its store benchmark, using 2.39 MiB (Qwen3 Q4)
  and 22.3 MiB (Kimi-K2 Q4) expert slabs with direct I/O. That is near link speed
  (hearth `docs/results/usb-hdd-store-bench.md`).
- In engine runs, NVMe-bound Qwen3 decode sustained about 5.2 GB/s (402 MB × 13 tok/s)
  (hearth `docs/results/policy-default.md`).
- **[inference]** Reads of 1–20 MB behave like sequential reads. Per-request overhead is
  irrelevant: at 6.5 GB/s, 22 MB reads are only about 300 IOPS, and 2.4 MB reads about 2,700.
- Gen5 consumer drives advertise about 14–15 GB/s sequential reads. I could not confirm that figure
  from a vendor page after the search budget ran out (unverified). The PCIe 5.0 x4 link caps them
  at 15.75 GB/s.
- Unverified: sustained thermal behaviour, and M.2 slots that share a chipset uplink. Hearth's
  simulator already models a shared-uplink cap (`io_cap_gbs`).

**Windows I/O.**
- `FILE_FLAG_NO_BUFFERING` requires transfer sizes and offsets that are multiples of the sector
  size, and sector-aligned buffers. VirtualAlloc's page alignment satisfies this
  ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/fileio/file-buffering)).
- IoRing (`ioringapi.h`, Windows build 22000+) documents batched read, buffer and handle
  registration, cancel, and completion-event APIs
  ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/ioringapi/)). Write
  support in later builds is unverified.
- DirectStorage targets game-asset loading into GPU buffers with GPU decompression samples
  ([GitHub](https://github.com/microsoft/DirectStorage)).
- **[inference]** For Hearth's CPU tier, overlapped unbuffered I/O with a few large requests in
  flight already saturates the drive. IoRing saves syscalls Hearth does not need to save.
  DirectStorage matters only for a future NVMe-to-VRAM path.

**Linux I/O.**
- O_DIRECT alignment depends on filesystem and kernel. Since Linux 6.1, `statx(STATX_DIOALIGN)`
  reports it
  ([open(2)](https://manpages.debian.org/bookworm/manpages-dev/open.2.en.html)).
- io_uring uses shared SQ/CQ rings to batch submissions, with optional SQPOLL and fixed buffers
  ([io_uring(7)](https://manpages.debian.org/testing/liburing-dev/io_uring.7.en.html)).

### 6. GPU tier

**Backends.**
- llama.cpp ships CUDA, HIP, Vulkan, Metal, SYCL and other backends. Its x86 CPU paths cover
  AVX/AVX2/AVX-512/AMX ([llama.cpp](https://github.com/ggml-org/llama.cpp)).
- **[inference]** Vulkan compute is the only cross-vendor option on Windows that needs no vendor
  SDK. It fits INV-DEP better than CUDA, which needs the CUDA toolkit or driver API.

**Cards and link bandwidth.**

| card | VRAM | memory bandwidth |
|---|---|---|
| RTX 5090 | 32 GB | 1,792 GB/s |
| RTX 5080 | 16 GB | 960 GB/s |
| RTX 5070 Ti | 16 GB | 896 GB/s |
| RTX 5070 | 12 GB | 672 GB/s |

- All four are PCIe 5.0
  ([Wikipedia RTX 50](https://en.wikipedia.org/wiki/GeForce_RTX_50_series);
  [NVIDIA](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/)).
- PCIe 4.0 x16 carries 31.5 GB/s per direction, and PCIe 5.0 x16 carries 63.0 GB/s
  ([Wikipedia PCIe](https://en.wikipedia.org/wiki/PCI_Express)).
- Hearth's simulator profile for this PC lists an RTX 5070. The brief says no GPU is used today, so
  I have not verified that one is installed.
- **[inference]** PCIe 5.0 x16 (63 GB/s) is *slower* than the CPU reading DRAM (about 77 GB/s). For
  batch-1 decode, shipping experts over PCIe is worse than computing them on the CPU where they
  live. The GPU's job is to hold the backbone (attention, shared experts, LM head) and hot experts
  in VRAM. This is the ktransformers and llama.cpp `-cmoe` pattern
  ([ktransformers](https://github.com/kvcache-ai/ktransformers);
  [llama.cpp gpt-oss guide](https://github.com/ggml-org/llama.cpp/discussions/15396)).

### 7. Roofline ceilings on the brief's machine (arithmetic shown)

**Constants.**
- DRAM: 96 GB/s theoretical peak, 77 GB/s measured AIDA64 read, 60 GB/s conservative streaming
  estimate (Hearth simulator).
- NVMe: 6.5 GB/s, the low end of Hearth's measured range.
- Bytes per weight: Hearth Q4 is 4.25 bpw and Q8 is 8.25 bpw (hearth `docs/SIMULATOR.md`).
- Decode time per token is at least (DRAM bytes / DRAM bandwidth) + (NVMe bytes / NVMe bandwidth)
  when serial. With perfect overlap it is the max of the two terms. DMA'd misses also cost a DRAM
  write.
- The embedding table is excluded, because decode reads only one row of it **[inference]**.

**7.1 Qwen3-30B-A3B in RAM.**
- Config: 48 layers, hidden 2048, 128 experts with top-8, expert FFN 768, 32 Q heads and 4 KV heads
  of dimension 128, vocabulary 151,936, untied embeddings. The model has 30.5B total and 3.3B
  active parameters
  ([HF card](https://huggingface.co/Qwen/Qwen3-30B-A3B);
  [config.json](https://huggingface.co/Qwen/Qwen3-30B-A3B/raw/main/config.json)).

Parameter counts **[inference]**:

| component | arithmetic | parameters |
|---|---|---|
| one expert | 3 × 2048 × 768 | 4.72M (2.51 MB = 2.39 MiB at Q4, matching Hearth's slab) |
| routed experts per token | 48 × 8 × 4.72M | 1.812B |
| attention | 48 × (2048×4096×2 + 2048×512×2) | 0.906B |
| LM head | 151,936 × 2048 | 0.311B |
| routers | — | 12.6M |
| total with embedding | — | 3.35B (matches "3.3B active") |

Bytes per token **[inference]**:
- **Hearth config B (Q4 experts, Q8 dense):** 1.812B × 4.25/8 + 1.217B × 8.25/8 + 0.05 GB of F32
  routers = **2.27 GB**.
- **Uniform Q4 (config A):** 3.03B × 4.25/8 + 0.05 = **1.66 GB**.
- **KV cache:** 48 × 2 × 4 × 128 × 2 B = 96 KiB per position. That adds 0.40 GB per token at 4K
  context.

| config | GB/token | 96 GB/s | 77 GB/s | 60 GB/s |
|---|---|---|---|---|
| B, short context | 2.27 | 42.3 | 33.9 | 26.5 |
| B, 4K context | 2.67 | 35.9 | 28.8 | 22.5 |
| A, short context | 1.66 | 57.8 | 46.4 | 36.2 |
| A, 4K context | 2.06 | 46.6 | 37.3 | 29.1 |

- Hearth's measured 19–22 tok/s on config B is 43–50 GB/s effective **[inference]**.
- llama.cpp's ~25 tok/s, if it used about 4.85 bpw on average, would be about 46 GB/s
  **[inference; quant type unverified]**.
- Both engines sit at about 60% of measured bandwidth. About 1.5x headroom remains to the measured
  roof, and 2x to the theoretical roof.

**7.2 Compute roof and ridge point.**
- Zen 5 runs VPDPBUSD zmm at 2 per cycle. 2 × 64 MACs × 2 ops × 16 cores gives **16.4 int8 TOPS at
  4.0 GHz** and 20.5 at 5.0 GHz. FP32 FMA gives 4.1–5.1 TFLOPS
  ([uops.info](https://uops.info/html-instr/VPDPBUSD_ZMM_ZMM_ZMM.html); arithmetic **[inference]**).
- The ridge point is 16.4 TOPS ÷ 77 GB/s ≈ **213 ops/byte**.
- Batch-1 Q4 decode runs at 2 ops ÷ 0.53 bytes ≈ 3.8 ops/byte, **56x below the ridge**.
- Prefill is different **[inference]**:
  - At peak, prefill could reach about 2,700 tok/s (6.06 GFLOP per token).
  - MoE prefill splits tokens across experts. A 512-token chunk gives each expert about 32 tokens,
    which is about 120 ops/byte, still below the ridge. A 2,048-token chunk reaches about 480
    ops/byte and becomes compute-bound.
  - Prefill and attention are where codegen quality, and therefore Mithril, can multiply speed.
    Hearth's 38 tok/s BF16 prefill is far below any compute roof.

**7.3 100B-class MoE in RAM.**
- gpt-oss-120b: 116.83B total and 5.13B active parameters. MLP weights are 114.71B, attention
  0.96B, embed+unembed 1.16B. It has 36 layers and 128 experts with top-4, MoE weights in MXFP4,
  and a 60.8 GiB checkpoint
  ([model card, arXiv:2508.10925](https://arxiv.org/html/2508.10925);
  [HF](https://huggingface.co/openai/gpt-oss-120b)).
- Per token **[inference]**:
  - experts: 114.71B × 4/128 = 3.585B, which is 1.90 GB at 4.25 bpw;
  - attention plus unembed in BF16: 3.08 GB, for a total of **4.98 GB**;
  - or with Q8 dense: **3.49 GB**.
- Ceilings at 96, 77 and 60 GB/s: **19.3 / 15.4 / 12.0 tok/s** with BF16 dense and
  **27.5 / 22.0 / 17.2 tok/s** with Q8 dense.
- The 60.8 GiB (65.3 GB) checkpoint does not fit beside the OS in 64 GB. With about 85% of experts
  resident and about 0.29 GB per token of misses, the result is **8.9–14.6 tok/s** for BF16 dense
  and **10.8–20.4 tok/s** for Q8 dense (serial to overlapped) **[inference]**.
- GLM-4.5-Air: 106B total and 12B active parameters
  ([HF](https://huggingface.co/zai-org/GLM-4.5-Air)). At about 4.5 bpw that is 6.75 GB per token,
  giving **14.2 / 11.4 / 8.9 tok/s** ceilings. Its roughly 60 GB of weights would not fully fit
  either **[inference]**.

**7.4 Kimi-K2-class streamed from one PCIe 4.0 NVMe with a 40 GB cache.**
- Config: 61 layers with 1 dense, hidden 7168, 384 experts with top-8 plus 1 shared, expert FFN
  2048, MLA attention (q_lora 1536, kv_lora 512, 64 heads), vocabulary 163,840. The model has 1T
  total and 32B active parameters
  ([HF card](https://huggingface.co/moonshotai/Kimi-K2-Instruct);
  [config.json](https://huggingface.co/moonshotai/Kimi-K2-Instruct/raw/main/config.json)).
- Kimi K2 Thinking applies INT4 QAT to its MoE weights, so Q4 experts are the lossless floor for
  that release ([HF](https://huggingface.co/moonshotai/Kimi-K2-Thinking)).

Parameter counts **[inference]**:

| component | arithmetic | parameters |
|---|---|---|
| attention per layer | — | 101.1M (×61 = 6.17B) |
| one expert | 3 × 7168 × 2048 | 44.04M (23.4 MB = 22.3 MiB at Q4, matching Hearth) |
| routed experts per token | 60 × 8 | 21.14B |
| shared experts | — | 2.64B |
| dense FFN | — | 0.40B |
| LM head | — | 1.17B |
| routers | — | 0.165B |
| total with embedding | — | 32.9B |

Bytes per token **[inference]**:
- Routed experts E = 21.14B × 4.25/8 = **11.23 GB**.
- Backbone: **11.37 GB** at Q8 (with F32 routers), or **5.85 GB** at Q4 (BF16 routers).
- All experts total 539 GB, so a 40 GB cache holds **7.4%** of them.
- MLA KV adds 70 KB per position, 0.29 GB at 4K context, ignored below.

All-in-DRAM ceiling **[inference]**:
- (11.37 + 11.23) / 77 gives **3.41 tok/s** with a Q8 backbone. A Q4 backbone gives 4.51.
- At 96 GB/s the figures are 4.25 and 5.62.

With misses from NVMe at 6.5 GB/s and DRAM at 77 GB/s (columns are serial / perfectly overlapped
tok/s) **[inference]**:

| hit rate h | NVMe GB/token | NVMe time (s) | Q8 backbone | Q4 backbone |
|---|---|---|---|---|
| 0.50 | 5.62 | 0.864 | 0.81 / 1.16 | 0.86 / 1.16 |
| 0.62 (Hearth sim, Zipf 1.1) | 4.27 | 0.657 | 0.99 / 1.52 | 1.07 / 1.52 |
| 0.70 | 3.37 | 0.518 | 1.17 / 1.93 | 1.28 / 1.93 |
| 0.80 | 2.25 | 0.346 | 1.50 / 2.89 | 1.68 / 2.89 |
| 0.90 | 1.12 | 0.173 | 2.08 / 3.25 | 2.44 / 4.23 |
| 0.95 | 0.56 | 0.086 | 2.58 / 3.32 | 3.17 / 4.37 |

Cross-checks:
- Hearth's simulator reports 1.20 tok/s at 62% LFU hit on this profile, and 2.62 tok/s with all
  experts in DRAM at 60 GB/s (hearth `docs/SIMULATOR.md` §8).
- Hearth's synthetic 1T container measured 1.2–1.8 s per token (0.55–0.83 tok/s) worst case
  (brief).
- These agree with the serial h ≈ 0.5 row.
- **[inference]** The cache holds 7.4% of experts. Measured Qwen3 traces show about 45% reuse from
  one token to the next. Hit rates of 50–75% are the plausible band until real Kimi traces exist.

**7.5 Sensitivity (all [inference]).**
- A single Gen5 drive at about 13 GB/s gives 1.68 / 2.97 tok/s at h = 0.7, which is DRAM-bound.
- 2-bit experts with a Q4 backbone at the 96 GB/s physical peak cap out at about **8.6 tok/s**.
- Putting the backbone on a GPU removes the 11.4 GB DRAM term, but the NVMe term stays. At
  h = 0.7, NVMe alone is 0.52 s per token, so the ceiling is still about 1.9 tok/s.
- Mixtral 8x7B (12.9B active; [Mistral](https://mistral.ai/news/mixtral-of-experts)) at about
  4.5 bpw is 7.26 GB per token. On an RTX 5090 that is a ceiling of about 247 tok/s.
- Qwen3-30B-A3B at uniform Q4 fits a 5090 with a ceiling of about 1,080 tok/s. On a 5070 the
  ceiling would be about 405 tok/s, but the roughly 17 GB of weights do not fit in 12 GB.

## Implications for Mithril

1. **Make bytes the first-class cost.** Every kernel and graph should carry a
   *bytes-per-token-by-tier* annotation (VRAM/DRAM/NVMe), and the compiler should print the
   resulting roofline ceiling next to any performance claim. This matches Hearth's INV-HONEST. A
   superoptimizer reward of "IPC" (B3) is the wrong objective for decode. The right objective is
   achieved bandwidth ÷ roof for bandwidth-bound kernels and FLOP/s ÷ roof for compute-bound ones
   **[inference]**.
2. **Treat ISA tiers as data, not syntax.** Required tiers are x86-64-v3 + AVX-VNNI (all Intel
   client chips through Panther Lake), AVX-512 with VNNI/VBMI/BF16/VP2INTERSECT (Zen 4/5, Xeon),
   AVX10.2 (Nova Lake, pending), AMX (Xeon), NEON plus optional SME (Apple), and SVE
   (Graviton-class). Vector width should be a cost-model decision: mobile Zen 5 executes zmm at half
   rate, and Intel client chips have no zmm at all. "Always zmm" (B6) is wrong
   **[inference from §1, §3]**.
3. **Cost-model instructions per microarchitecture from measured tables.** Use uops.info and Agner
   data, not intuition. On Zen 5, gathers are microcoded and slow; VPERMB, VPDPBUSD and VPOPCNTQ
   all run at 2 per cycle; locked ops cost about 17–20 cycles; simple SIMD has 2-cycle latency.
   Lower sparsity to contiguous expert slabs and in-register LUTs, not to VGATHER (C5)
   **[inference]**.
4. **Point the scheduler or superoptimizer at latency-bound code.** That means prefill GEMM,
   attention, softmax and norm chains, which need 8-way ILP on Zen 5. Decode GEMV is about 97% idle
   at the bandwidth roof **[inference]**.
5. **Hot-swap and JIT semantics must be stated precisely.**
   - Publish new versions with a release store of an aligned 8-byte pointer, and reclaim old ones
     with epochs or RCU.
   - For patched code, call `FlushInstructionCache` on Windows, use membarrier SYNC_CORE (or
     per-thread CPUID/SERIALIZE) on Linux, and use MAP_JIT, the W^X toggle and icache invalidation
     on Apple.
   - Never INVD or WBINVD (ring 0). Never rely on CLFLUSH for code coherence.
   - These semantics must preserve Hearth's bit-identical invariants across the swap boundary
     **[inference]**.
6. **Do not emit per-core-type code paths (B10).** Keep per-ISA dispatch at load time and
   work-stealing that tolerates heterogeneous core speeds **[inference]**.
7. **Make topology a language and runtime concept.** On the 9950X, one CCD cannot exceed 64 GB/s,
   and cross-CCD synchronization costs on the order of 100s of ns. Thread placement and the number
   of barriers per layer belong in the cost model **[inference]**.
8. **Design the benchmark harness for Windows.** WBINVD is unavailable in user mode, so cold runs
   need CLFLUSHOPT sweeps or eviction buffers. perf_event_open does not exist on Windows (B11)
   **[inference]**.

## Implications for Hearth

1. **Qwen3-30B-A3B target.** Raising effective bandwidth from about 45 to about 65 GB/s (85% of
   AIDA) would give **~28–29 tok/s** on the lossless config B. That beats llama.cpp's ~25 without
   changing output. Going further needs fewer bytes: opt-in lossy Q4 dense lifts the 77 GB/s
   ceiling from 33.9 to 46 tok/s **[inference]**.
2. **Check that decode threads span both CCDs and that reads are balanced across them.** A single
   CCD caps at 64 GB/s
   ([Chips and Cheese](https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop)).
3. **Kimi-class on one 990 PRO is NVMe-bound at about 1–2 tok/s for plausible hit rates.** Hearth
   has two levers here:
   - Minimize NVMe bytes per token. Hearth's own finding is that NVMe bytes per token predict
     speed better than hit rate.
   - Overlap I/O with compute. That moves a token from the serial to the overlapped column, a gain
     of up to +65% at h = 0.7.

   Hardware levers are a Gen5 drive or a second drive, which becomes DRAM-bound at about 3 tok/s,
   and more RAM. Four DIMMs drop to DDR5-3600 officially, so more RAM costs bandwidth
   ([Wikipedia Zen 5](https://en.wikipedia.org/wiki/Zen_5)) **[inference]**.
4. **Prefill is compute-bound and far from its roof.** Use large prefill chunks (2K+ tokens) so
   per-expert reuse crosses the ridge. Prefill is the place where AVX-512 kernel work pays
   **[inference]**.
5. **I/O.** The current overlapped unbuffered design already saturates the drive. IoRing is
   optional, and DirectStorage matters only for an NVMe-to-VRAM tier **[inference]**.
6. **GPU tier.** Put the backbone, hot experts and attention in VRAM. Compute cold experts on the
   CPU from DRAM, and never stream experts over PCIe per token at batch 1. Vulkan compute is the
   INV-DEP-friendly route **[inference]**.
7. **The simulator's constants are consistent with sources.** DRAM 60 GB/s is conservative against
   77 measured. NVMe 6.5 GB/s matches measurement. 20 int8 TOPS matches VPDPBUSD 2 per cycle at
   about 5 GHz, though about 16 TOPS is more realistic at all-core AVX-512 clocks
   ([numberworld](https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/)).

## Where the seed discussion is right or wrong

**Roughly right.**
- **C1** (dual-channel DDR5 tops out at about 100 GB/s; the roofline is binding): right. Theoretical
  peak is 96 GB/s at 6000 MT/s and measured bandwidth is about 77 GB/s.
- **B7** (a mispredict costs 15–20 cycles): roughly right. Zen 5 measures 15–25 and Golden Cove's
  best case is 17. Compile-time "branch entropy" is mostly data-dependent, and compilers already
  if-convert to CMOV **[inference]**.
- **B4** (line64 alignment; streaming lowers to NT stores): the store half is sound if it emits a
  fence. The NT-load half is not, because the hint is advisory on WB memory.

**Wrong or misleading.**
- **C5** (sparsity compiled to VGATHER/VSCATTER): poor fit. Zen 5 gathers cost about 1.3
  elements per cycle at 64 µops, and Intel gathers carry GDS microcode costs on affected parts. MoE
  sparsity is block-level, which means contiguous slab reads.
- **C6** (bit-width primitives lowering to popcount/BMI2/VNNI): the bit-width part is valuable,
  because fewer bits mean fewer bytes, and bytes are the decode lever. The instruction choice is
  secondary while decode is memory-bound.
- **C7** (DRAM→L1 about 200 cycles): about 2x low. 70–77 ns is about 400–440 cycles at 5.7 GHz.
  Agner also finds hardware prefetch usually beats software prefetch on Zen 5.
- **D1** (80B at 1.58 bits is about 16–18 GB): the arithmetic is right (80B × 1.58/8 = 15.8 GB;
  about 20 GB with 2-bit packing). It requires a model trained natively ternary. The only native
  1.58-bit open model in my sources is about 2B
  ([BitNet b1.58 2B4T](https://arxiv.org/abs/2504.12285)). Applied after training to existing
  models, it breaks INV-LOSSLESS-DEFAULT.
- **D2** (300B+ in 64–128 GB without paging): needs ≤3.0 bpw to fit 128 GB (112.5 GB) and about
  1.6 bpw for 64 GB (60 GB, leaving nothing for the OS). Big AM5 configurations also lose bandwidth
  with four DIMMs. Only possible with heavy lossy quantization.
- **D3** (gain table), row by row:
  - "Out-of-core 12–22 tok/s" is **impossible** for Kimi-class on this machine. The ceiling is 3.4
    tok/s even with every expert in DRAM. It is plausible only for models with about 5B active
    parameters.
  - "CPU-only 100B MoE 6–10 tok/s" is within physics for a model with about 12B active (ceiling
    about 11.4). The quoted 1–2 tok/s baseline is unverified and implausible for a competent engine.
  - "VRAM-resident 8x7B 85–130 tok/s" is within physics (5090 ceiling about 247). The baseline is
    unverified.
  - "TTFT 1.5–2x" is plausible, because prefill is compute-bound **[inference]**.
- **D4** (speculative DMA hides 70–85% of transfer latency): ill-posed. Overlap hides time, not
  bytes. When NVMe-bound, at most the smaller of the two terms can be hidden. Hearth measured 70%
  of one-layer-ahead prefetches arriving late when NVMe-bound.
- **D5** (VPOPCNTDQ replaces FMAs): VPOPCNTQ and VPDPBUSD both run at 2 per cycle on Zen 5.
  Popcount needs binarized activations, and compute is not the bottleneck.
- **D6** (IPC 0.8–1.4 → 2.6–3.8; cache-miss stalls under 8%): contradicts being at the bandwidth
  roof, where cores necessarily wait. A Q4 GEMV uses about 3% of instruction capacity. The power
  claim is unverified.
- **D7** (15–20+ tok/s on out-of-core 100B+ MoE): **possible only for models with about 5B active
  parameters** such as gpt-oss-120b (8.9–20.4 tok/s band). It is **impossible** for 12B+ active
  models out-of-core, and for Kimi-class.
- **I5** (CMPXCHG16B hot patch "in a single CPU cycle"): wrong by about 17–20x uncontended (26
  µops), worse when contended. It is also unnecessary, since a release store of an 8-byte pointer
  plus reclamation does the job.
- **I7** (invalidate the icache with CLFLUSH/INVD): wrong on three counts.
  - INVD is ring 0 and discards dirty data.
  - CLFLUSH does not serialize the fetched instruction stream.
  - x86 needs a serializing instruction on the executing core (or OS help: membarrier,
    FlushInstructionCache).
- **B10** (dual P/E code paths): not useful. Intel keeps the ISA identical across core types
  precisely so threads can migrate, and the 9950X is homogeneous.
- **B11** (WBINVD for cold runs): needs ring 0 and is unavailable to a user-mode harness.
- **B2** (avoid decoder stalls by instruction length): low value on Zen 5. It has 2×32 B/cycle
  fetch, no prefix penalty, and hot loops run from the µop cache.

## Open questions

1. What do STREAM-style per-CCD and all-core read bandwidths look like on the user's exact board
   and firmware, with Hearth's kernels, pinned versus spread? Has later AGESA changed cross-CCD
   latency?
2. Lion Cove and Cougar Cove mispredict penalties: no published figure was found.
3. Were uops.info's Intel gather rows measured before or after GDS microcode? What is the
   post-mitigation gather throughput on Alder Lake and Raptor Lake?
4. Nova Lake: final AVX10.2 vector width on E-cores, APX, and launch date. Does Zen 5 support
   SERIALIZE (unverified)?
5. Gen5 NVMe sustained 1–20 MB read throughput under thermal load. Does the second M.2 slot on the
   user's board share a chipset uplink? (Vendor specs unverified after the search budget ran out.)
6. Real Kimi-K2 routing skew. Which hit rate does a 40 GB (7.4%) cache actually achieve with LRU
   and prediction-aware eviction? This decides whether the 1 or the 3 tok/s column applies.
7. Is there an open, native-ternary MoE above about 2B parameters? This would make D1 relevant to a
   lossless default. Unverified, because the search budget ran out.
8. What is the exact Apple JIT procedure on current macOS? The documentation page did not render.
   Also, do GitHub's macOS arm64 runners expose SME (M4-class) or only NEON?

## Sources

- https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop
- https://chipsandcheese.com/p/zen-5s-avx-512-frequency-behavior
- https://chipsandcheese.com/p/intels-lion-cove-p-core-and-gaming
- https://numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/
- https://www.agner.org/optimize/microarchitecture.pdf (edition updated 2026-05-23)
- https://en.wikipedia.org/wiki/Zen_5
- https://en.wikipedia.org/wiki/AVX-512
- https://www.phoronix.com/review/amd-zen5-avx-512-9950x
- https://phoronix.com/news/AMD-Zen-5-Mispredict-Cost
- https://techpowerup.com/forums/goto/post?id=5319760
- https://at-web1.www.anandtech.com/show/16881/a-deep-dive-into-intels-alder-lake-microarchitectures/3
- https://www.hwcooling.net/en/intel-alder-lake-golden-cove-cpu-core-unveiled-microarch-analysis/
- https://uops.info/html-instr/VPDPBUSD_ZMM_ZMM_ZMM.html
- https://uops.info/html-instr/VPOPCNTQ_ZMM_ZMM.html
- https://uops.info/html-instr/VPERMB_ZMM_ZMM_ZMM.html
- https://uops.info/html-instr/VPGATHERDD_ZMM_K_VSIB_ZMM.html
- https://uops.info/html-instr/VPGATHERDD_YMM_VSIB_YMM_YMM.html
- https://uops.info/html-instr/CMPXCHG16B_LOCK_M128.html
- https://uops.info/html-instr/CMPXCHG_LOCK_M64_R64.html
- https://www.rehwolution.it/?p=118349
- https://www.phoronix.com/review/downfall
- https://access.redhat.com/solutions/7027704
- https://ubuntu.com/security/vulnerabilities/gds-downfall
- https://www.felixcloutier.com/x86/movntdq
- https://www.felixcloutier.com/x86/movntdqa
- https://www.felixcloutier.com/x86/serialize
- https://www.felixcloutier.com/x86/invd
- https://www.felixcloutier.com/x86/wbinvd.html
- https://www.felixcloutier.com/x86/clflush
- https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html
- https://lists.xen.org/archives/html/xen-changelog/2025-07/msg00562.html
- https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/include/asm/sync_core.h
- https://manpages.debian.org/bookworm/manpages-dev/membarrier.2.en.html
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache
- https://developer.apple.com/documentation/apple-silicon/porting-just-in-time-compilers-to-apple-silicon
- https://en.wikipedia.org/wiki/Arrow_Lake_(microprocessor)
- https://en.wikipedia.org/wiki/Lunar_Lake
- https://en.wikipedia.org/wiki/Panther_Lake_(microprocessor)
- https://www.guru3d.com/story/intel-avx102-support-arriving-in-nova-lake-processors
- https://www.igorslab.de/en/intel-nova-lake-brings-avx10-2-and-apx-the-technological-liberation-for-the-x86-platform/
- https://www.tomshardware.com/pc-components/cpus/avx-512-support-is-reportedly-returning-with-intels-next-gen-nova-lake-cpus-latest-linux-kernel-patches-reveal-p-cores-and-e-cores-will-gain-native-512-bit-execution
- https://en.wikipedia.org/wiki/Advanced_Matrix_Extensions
- https://en.wikipedia.org/wiki/Apple_M4
- https://en.wikipedia.org/wiki/Apple_M5
- https://arxiv.org/abs/2409.18779
- https://en.wikipedia.org/wiki/AArch64
- https://en.wikipedia.org/wiki/PCI_Express
- https://en.wikipedia.org/wiki/GeForce_RTX_50_series
- https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/
- https://www.samsung.com/us/computing/memory-storage/solid-state-drives/990-pro-pcie-4-0-nvme-ssd-2tb-mz-v9p2t0b-am/
- https://learn.microsoft.com/en-us/windows/win32/fileio/file-buffering
- https://learn.microsoft.com/en-us/windows/win32/api/ioringapi/
- https://github.com/microsoft/DirectStorage
- https://manpages.debian.org/bookworm/manpages-dev/open.2.en.html
- https://manpages.debian.org/testing/liburing-dev/io_uring.7.en.html
- https://github.com/ggml-org/llama.cpp
- https://github.com/ggml-org/llama.cpp/discussions/15396
- https://github.com/kvcache-ai/ktransformers
- https://huggingface.co/Qwen/Qwen3-30B-A3B
- https://huggingface.co/Qwen/Qwen3-30B-A3B/raw/main/config.json
- https://huggingface.co/moonshotai/Kimi-K2-Instruct
- https://huggingface.co/moonshotai/Kimi-K2-Instruct/raw/main/config.json
- https://huggingface.co/moonshotai/Kimi-K2-Thinking
- https://huggingface.co/openai/gpt-oss-120b
- https://arxiv.org/html/2508.10925
- https://huggingface.co/zai-org/GLM-4.5-Air
- https://mistral.ai/news/mixtral-of-experts
- https://arxiv.org/abs/2504.12285
- Hearth repository (local clone; public at https://github.com/pierce-lonergan/hearth):
  `docs/SIMULATOR.md`, `docs/results/usb-hdd-store-bench.md`, `docs/results/policy-default.md`,
  `docs/results/qwen3-routing-and-cache-policy.md`
