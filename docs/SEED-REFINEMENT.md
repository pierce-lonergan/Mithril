# Refining the seed discussion

Mithril started from an earlier AI chat that the owner pasted into this project. It proposed an
"x86-native language that beats C", then added its own reality check, a table of claimed gains, a
visual-generation extension, an `openai/math` connection, a reading list, a go-to-market plan, and a
"living tissue" vision of self-modifying models. This document takes that discussion section by
section (A–I). For each section it records what the instinct was, what the research found, and
what Mithril keeps, transforms, defers or rejects, with a link to where each surviving idea now
lives. The fact-check [R10] rated the 59 numbered claims as follows: 4 true, 20 mostly-true, 17
misleading, 6 false, 5 likely-fabricated and 7 unverifiable. The pattern is consistent. The design
instincts survive and carry real weight in the architecture: verified superoptimisation, roofline
honesty, hardware-surfacing types, low-bit formats, explicit memory pipelines, machine-actionable
diagnostics, and agents as first-class users. The numbers mostly do not survive. The speed-up
table, the IPC and power figures, "30+ FPS" and the `openai/math` family citations were never
measured or checked. Mithril's answer is structural rather than editorial: a performance number
becomes a typed quantity that carries its origin, and an unchecked claim enters the ledger as a
hypothesis (a claim whose verdict is `unknown`, so it licenses nothing until it is tested; §6).

**Contents**
1. [How to read this document](#1-how-to-read-this-document)
2. [The tally](#2-the-tally)
3. [A. Layers below C](#3-a-layers-below-c)
4. [B. An x86-native language that beats C](#4-b-an-x86-native-language-that-beats-c)
5. [C. The reality check](#5-c-the-reality-check)
6. [D. The claimed gains](#6-d-the-claimed-gains)
7. [E. Visual generation](#7-e-visual-generation)
8. [F. The openai/math repository](#8-f-the-openaimath-repository)
9. [G. Projects and theory to study](#9-g-projects-and-theory-to-study)
10. [H. Go-to-market and agent discovery](#10-h-go-to-market-and-agent-discovery)
11. [I. "Living tissue"](#11-i-living-tissue)
12. [Rejected seed ideas as design-level tombstones](#12-rejected-seed-ideas-as-design-level-tombstones)
13. [What the discussion got most right](#13-what-the-discussion-got-most-right)
14. [Sources](#14-sources)

---

## 1. How to read this document

**Sources.** The orchestrator's digest of the seed discussion numbers every concrete claim A1–I8,
in the original order. [R10](research/R10-seed-fact-check.md) gives one verdict per claim:
*true, mostly-true, misleading, false, likely-fabricated* or *unverifiable*. Every other dossier
(R01–R13, G01–G05) ends with a section called "Where the seed discussion is right or wrong".
Those sections add detail, and where they disagree with R10 this document says so. Decisions
(DR-xxx) are recorded in [DECISIONS.md](DECISIONS.md). [ARCHITECTURE.md §14](ARCHITECTURE.md)
summarises this document.

**Each section** covers three things. *The instinct* is what the discussion was reaching for,
stated charitably. *The evidence* gives the verdict counts and key corrections, with citations.
*What Mithril does* follows, with one table row per claim.

**Dispositions.**
- **Keep**: adopted substantially as stated.
- **Transform**: the instinct survives; the mechanism, number or surface is replaced.
- **Defer**: plausible but outside v1; parked behind a trigger or a later milestone.
- **Reject (claim)**: a number, citation or factual assertion the evidence does not support.
- **Reject (mechanism)**: a mechanism that is wrong, unsafe, or does not fit the target machine.
- **Context**: a fact with no design consequence of its own.

**Labels.** Status labels map to milestones as in [ROADMAP §1](ROADMAP.md) rule 7:
- **v0**: in the mithc that ports Hearth (M1–M5);
- **v1**: present by Edition 1 (M6–M7);
- **later**: planned after M7;
- **reserved**: in the types and schema but not producible;
- **by-trigger**: added only when its register trigger fires.

Status cells name the delivering milestone where one applies. Every number is marked
measured, simulated, [inference] or [target]. "Project-reported" marks a third party's own
measurement that we have not reproduced. All Mithril syntax shown here is provisional until the
Surface Lab has tested it ([05-agent-protocol](architecture/05-agent-protocol.md)).

Reviewer note: seed IDs collide with other Mithril names. The seed's B1–B12 clash with backends
B1–B4 and with the ROADMAP's benefit claims B1–B3, and the seed's D1–D7 clash with owner decisions
D0 and revisit nodes such as D2-A. This document writes "seed B8", "backend B1" and "benefit claim
B1" wherever the context is ambiguous. Sibling documents should do the same.

---

## 2. The tally

R10's verdict table, recounted row by row, matches its summary:

| Section | Claims | true | mostly-true | misleading | false | likely-fabricated | unverifiable |
|---|---|---|---|---|---|---|---|
| A Layers below C | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| B x86-native blueprint | 12 | 1 | 7 | 4 | 0 | 0 | 0 |
| C Reality check | 8 | 0 | 3 | 4 | 0 | 0 | 1 |
| D Claimed gains | 7 | 0 | 1 | 2 | 0 | 2 | 2 |
| E Visual generation | 8 | 0 | 3 | 3 | 0 | 1 | 1 |
| F openai/math | 6 | 0 | 1 | 2 | 2 | 1 | 0 |
| G Projects to study | 2 | 1 | 1 | 0 | 0 | 0 | 0 |
| H Go-to-market | 7 | 2 | 2 | 2 | 0 | 1 | 0 |
| I Living tissue | 8 | 0 | 1 | 0 | 4 | 0 | 3 |
| **Total** | **59** | **4** | **20** | **17** | **6** | **5** | **7** |

Mithril's dispositions of the same 59 claims:

| Disposition | Count | Claims |
|---|---|---|
| Keep | 8 | B1, B11, C1, C2, G1, H2, H3, H5 |
| Transform | 19 | A1, B3, B4, B5, B6, B8, B9, B12, C4, C6, C7, C8, E3, E4, F2, G2, H4, I4, I5 |
| Defer | 6 | B7, D1, E2, I1, I3, I8 |
| Reject (claim) | 12 | C3, D2, D3, D4, D6, D7, E8, F3, F4, F5, H1, H7 |
| Reject (mechanism) | 13 | B2, B10, C5, D5, E1, E5, E6, E7, F6, H6, I2, I6, I7 |
| Context | 1 | F1 |

Four patterns stand out.

1. **Mechanisms held up; outcomes did not.** Sections A–C, the engineering blueprint, contain 21
   claims. None is false or fabricated: 12 are true or mostly-true and 8 are misleading. All 6
   false and all 5 likely-fabricated claims sit in D, E, F, H and I, the sections about outcomes
   (speed-ups, frame rates, IPC), citations (math families) and guarantees (loss bounds,
   forgetting).
2. **The target machine was misread.** Several claims assume a Linux, Intel-hybrid,
   compute-bound machine: E-cores (B10, E6), `isolcpus` and WBINVD (B11), DRM/KMS (E7), and SPDK
   with PCIe BAR access (G1, G2). The real target is Windows 11 on a homogeneous 16-core Zen 5
   desktop. Its decode is bandwidth-bound, and it has a 12 GB RTX 5070 the discussion never
   mentions [G03].
3. **"Guaranteed" was overused.** Examples: "mathematically guaranteed" vectorisation (B6), SMT
   that "guarantees bounded loss divergence" (I4), "eliminating catastrophic forgetting" (I6),
   "zero stack spills" (F3). Mithril adopts R10's rule: guarantee emission properties and
   equivalence to a meaning, and measure everything else [R10, Implication 4].
4. **The discussion refuted itself.** Its own reality check (C1, C2) rules out most of its gains
   table (D3, D6). Mithril automates that check: cost signatures report every result as a fraction
   of a measured roof (N7, [02-compute](architecture/02-compute.md)).

---

## 3. A. Layers below C

**The instinct.** To beat C you must understand what lies beneath it: assembly, machine code,
microcode, hardware description languages, transistors.

**The evidence.** One claim, rated mostly-true [R10 F-A]. The layering is right, and microcode is
signed and patched. Two nuances matter.
- Most x86 instructions decode in hard-wired decoders; only complex ones use the microcode
  sequencer. Zen 5 decodes two 4-wide streams and has a 6K-entry µop cache [R10, citing Agner
  Fog].
- No language or compiler can reach microcode or HDL on a stock CPU.

The decisive finding came from verification. No public source has formal AVX-512 floating-point
semantics: ACL2 has 0 EVEX entries, Sail x86 has none, and s2n-bignum covers AVX2 integer code only
[G02]. "Understanding the layer below C" therefore becomes a concrete, large work item, not a
descent into microcode.

**What Mithril does.** Mithril formally models nothing below the architectural ISA. The
microarchitecture appears only as measured data.
- The **x86 semantics table** is the formal floor (layer L5). It is hand-written, keyed by Intel XED
  iclass, has an explicit FP-environment layer, is fuzz-validated on Zen 5 with Bochs as a second
  oracle, and generates SMT terms and a C reference interpreter [G02, P2 §5.2].
- The **machine profile** (layer L8) holds measured bandwidths, latencies and uops.info-style
  instruction costs, keyed by a hardware fingerprint [R08, P3 §1].

| Claim | Seed said | R10 | Mithril | Where it lives | Status |
|---|---|---|---|---|---|
| A1 | C → asm → machine code → microcode → HDL → transistors | mostly-true | Transform: formal floor = ISA semantics table; µarch = measured profile; microcode/HDL out of scope | [03-trust](architecture/03-trust.md) (semantics table); [ARCH §4](ARCHITECTURE.md) (L5, L8) | v0 (M2) |

---

## 4. B. An x86-native language that beats C

**The instinct.** C's abstract machine hides aliasing and the hardware, so it leaves throughput
on the table. The fix proposed: a language whose types expose cache lines, streaming stores and
vector masks, with no pointers; a compiler that searches machine code with RL, MCTS or LLMs and
proves each result with SMT; and benchmarks rigorous enough to trust.

**The evidence.** 12 claims: 1 true (B4), 7 mostly-true, 4 misleading (B2, B6, B9, B10).
- **Verification tooling (B8).** Alive2 checks LLVM IR, not x86. Its x86 coverage is 136
  integer-intrinsic entries, with no FP, VNNI or BF16 [G02]. STOKE's validator has no AVX-512, and
  STOKE is unmaintained [R10, R07]. Worse, a superoptimiser that reassociates floats produces code
  that is *not* equivalent, so a correct checker must reject it. FP-theory SMT is the wrong primary
  tool [R07]. Whole-kernel SMT does not scale either: Alive2 verified 38.2% of LLM vectorisations
  [R05, R07].
- **Search needs a checker and works on small kernels (B3, B9, B12).** SuperCoder reached 95.0%
  correctness and 1.46× over gcc -O3 (measured, project-reported) [R10]. The remaining 5% of wrong
  outputs is why a checker must gate every result. AlphaDev's gains shrink to about 1.7% on large
  inputs, and nothing shows a whole -O3 pipeline being replaced [R01].
- **IPC is a hackable reward (B3).** Adding cheap instructions raises IPC and slows the task.
  Timing rewards are the most exploited signal in this literature; 32.8% of CUDA-L1 kernels hacked
  the timing [R01, R02].
- **LLVM is not the obstacle (B2).** LLVM has per-CPU scheduling models. The real gap is that
  `znver5` still reuses `Znver4Model` [R10]. Every leading engine and kernel DSL is built on
  standard compilers [R05, R06]. Instruction-length tuning is worth little on Zen 5, which runs hot
  loops from the µop cache [R08].
- **Wrong machine (B10, B11).** The 9950X has 16 identical cores, and Intel hybrids equalise the
  ISA so that threads can migrate [R10, R08]. WBINVD is ring 0, `isolcpus` is Linux-only, TMA is
  Intel's method, and RDTSC ticks at a reference rate [R10]. An `mprotect` sandbox is
  insufficient: agents have disabled sandbox flags (STOP, 0.42% of runs) [R01].
- **Data rights (B12).** Intel's terms forbid text-and-data mining, so its tables cannot be
  vendored [G02].
- **Vectorisation (B6).** A language can guarantee that vector code is *emitted*, not that it is
  faster [R10]. Under bit-exactness, a reduction's lane count is part of its meaning [G03].
- **Aliasing (B1)** is the strongest point. Hearth's attention value pass only vectorises because
  it is a hand-annotated `restrict` loop. It runs at 18.0 GMAC/s, while a bit-identical
  register-blocked AVX-512 prototype reaches 94 GMAC/s (measured) [R11]. Strict FP order is a
  deliberate Hearth choice (INV-DET-3), not a defect of C [R10].

**What Mithril does.** Seed B8 became the heart of Mithril, with its mechanism replaced. Its
shape (untrusted search, a small trusted checker, then emit) is N1 and N2 in
[ARCHITECTURE §1](ARCHITECTURE.md). The pieces:
- Each kernel has one exact meaning in canonical order (`canon.v1`).
- **T1** matches FP-DAGs modulo an audited list of IEEE-exact rewrites.
- **T2** discharges bit-vector SMT obligations for the integer parts.
- The checker validates the output, not each rewrite, using correspondence maps that the schedule
  supplies.

Search moves from byte sequences to schedule spaces and certified spaces; this is the Reasoning
Compiler pattern [R05]. The backend is strict C11 plus an object audit (backend B1.5) of the
roughly 20 hot kernels, preceded by an instruction census (DR-008). A direct x86 emitter is built
only on a trigger (DR-009).

```mith
/// A schedule may only apply DAG-preserving primitives. T1 validates the emitted object code.
schedule q4_matvec_avx512 for q4_matvec on x86_64(avx512f, avx512bw, avx512vnni) {
    tile r by 16;                   // 16 rows per pass
    vectorize j using vpdpbusd;     // integer block sums via VNNI: licensed by the exact-i32 range proof
    keep_order acc;                 // the float epilogue order comes from the meaning
    prefetch w ahead 2 blocks;
}
```

This snippet is B6 and B8 after correction. Vector width and instruction choice are explicit,
checkable decisions. Reordering is licensed only where an overflow proof makes integer arithmetic
exact, and the float order stays fixed.

Reviewer note (resolved): DR-027 cited the value pass's 18 → 94 GMAC/s gap as the payoff of
emitting `restrict`. Per R11, the 18.0 GMAC/s portable loop *already* uses `restrict`; 94 GMAC/s
comes from register blocking. `restrict` is what lets the portable loop vectorise at all. The
remaining 5× is a schedule and codegen gap, which suits a T1-validated schedule. The decision
stands, and DECISIONS (DR-027 Evidence) and 04-toolchain (§6.4) now give this justification.

Reviewer note (Owner action): the repository's public description still carries the seed's pitch,
"a hardware-native, microarchitecture-synthesized language and JIT runtime delving deep into
x86-64 silicon to yield unyielding throughput". This section rejects each part of it: µop-level
synthesis as the main path (seed B2), a JIT at the core (the copy-and-patch JIT is backend B4, by
trigger) and throughput credited to a language ([ARCH §15](ARCHITECTURE.md), non-goals: speed is
credited to placement and bytes). R03 and G03 flag the same tagline as a cost to agent ergonomics
and as aimed at the wrong lever [R03, G03]. ARCH §17 and ROADMAP §11 should add an Owner decision
to revise it. Suggested wording, consistent with the thesis in ARCH §1: "A small, Rust-shaped
systems language for AI agents: exact-by-default kernels checked by translation validation, and
every claim backed by an evidence ledger."

| Claim | Seed said | R10 | Mithril | Where it lives | Status |
|---|---|---|---|---|---|
| B1 | C hides aliasing and hardware | mostly-true | Keep: MVS plus exclusive `&mut` give alias facts; emit `restrict` (DR-027) | [04-toolchain](architecture/04-toolchain.md) (C11 lowering); [01-language](architecture/01-language.md) (memory model) | v0 (M1; `restrict` M2; `std_platform` M4) |
| B2 | Skip LLVM IR; target µop-port SSA | misleading | Reject (mechanism); its kernel of truth (stale cost models) becomes measured machine profiles | [02-compute](architecture/02-compute.md) (cost signatures) | v0 (M2) |
| B3 | RL on cycle timings; reward = IPC | mostly-true | Transform: objective = time or bytes per *correct* output, e-value gated; IPC/TMA as diagnostics | [06-forge](architecture/06-forge.md); [03-trust](architecture/03-trust.md) (promotion rule) | v0 (F1-live, M4); v1 (F1 campaigns, M6) |
| B4 | `line64` alignment; streaming → NT stores | true | Transform: alignment as a type (`Aligned<_, N>`); NT stores as a schedule/library choice with a fence [R08, R09] | [01-language](architecture/01-language.md) (types); [02-compute](architecture/02-compute.md) (schedules) | v0 (alignment, M1), later (NT) |
| B5 | No pointers; affine strides prove no-alias | mostly-true | Transform: MVS, second-class refs, projections (DR-004); `par for` disjoint writes; block-sparse iteration for MoE routing | [01-language](architecture/01-language.md); [02-compute](architecture/02-compute.md) | v0 (M1; `par for` M4) |
| B6 | No scalar loops; vectorisation "guaranteed" | misleading | Transform: explicit schedules; lane count is semantics (`canon::sum16`); guarantee = emission plus T1 | [02-compute](architecture/02-compute.md) (schedules, reductions) | v0 (M2) |
| B7 | Branch-entropy tracking: Jcc vs CMOV | mostly-true | Defer: profile-driven if-conversion as an F2 heuristic hook (may be slower, never wrong) | [06-forge](architecture/06-forge.md) (F2) | later |
| B8 | Polyhedral → MCTS/LLM superopt → SMT → ELF | mostly-true | Transform: N1/N2; T1/T2 over an owned semantics table; polyhedral for legality only; C11 plus object audit | [03-trust](architecture/03-trust.md) (T0–T3); [04-toolchain](architecture/04-toolchain.md) | v0 (M2) |
| B9 | MCTS plus value net replaces -O3 | misleading | Transform: search schedule and certified spaces; F2 heuristics choose among certified rewrites | [06-forge](architecture/06-forge.md) (F1, F2) | v1 (F1 schedule search, M6), later (F2) |
| B10 | Dual P-core/E-core paths | misleading | Reject (mechanism): ISA-level dispatch at load (cpuid plus XCR0) | [04-toolchain](architecture/04-toolchain.md) (runtime) | v0 (M2) |
| B11 | PMU harness, pinning, warm/cold runs | mostly-true | Keep, strengthened: runtime-owned measurement service, interleaved, load-gated, e-values (DR-018); Windows-adapted | [06-forge](architecture/06-forge.md) (measurement, desktop statistics) | v0 (M0; live engine M4) |
| B12 | mprotect sandbox; Agner/Intel tables; fine-tune intent → -O3 | mostly-true | Transform: process/VM isolation; Zen-5-fuzzed tables; fine-tunes only on validated corpora, with novelty pressure, since imitating -O3 reproduces the incumbent [R02] | [03-trust](architecture/03-trust.md) (threat model); [05-agent-protocol](architecture/05-agent-protocol.md) | v0 (M2 tables), by-trigger (fine-tune, DR-023) |

---

## 5. C. The reality check

**The instinct.** No language beats the roofline, and dense GEMM is already near peak. So aim at
what seems wasted: unfused operations, sparsity, oversized number formats, memory latency, and the
split between host and device.

**The evidence.** 8 claims: 3 mostly-true (C1, C2, C4), 4 misleading (C3, C5, C6, C7), 1
unverifiable (C8).
- **C1, roofline.** Right, and much of the other evidence builds on it. Theoretical bandwidth is
  89.6 GB/s for DDR5-5600 and 96 GB/s for DDR5-6000 [inference: 2 channels × 8 B × transfer rate].
  Measured: about 77 GB/s all-core read (AIDA64 on 9950X boards; Hearth's notes record about
  78 GB/s on this PC) [R08, R10]. Each CCD's Infinity Fabric link caps reads at 64 GB/s; that figure
  is arithmetic, not a measurement (32 B/clk × FCLK 2 GHz), so it moves with FCLK and belongs in the
  machine profile [R08]. Out of core, the NVMe drive is the binding roof at 7.16 GB/s demand reads
  (measured) [R11].
- **C2.** Qualitatively right; the sourced range is 80–95% of peak, not 90–98% [R05].
- **C3, "60–90% wasted".** Unsourced. Hearth's decode runs about 15–35% below achievable
  bandwidth [R11, inference], and transcendentals take about 0.2–8% of decode [G04]. Where
  offloaded MoE engines lose time, it is I/O wait: 59–71% (rabbit, kimi-k3-in-c) [R06]. The cause
  is bytes and placement, not unfused element-wise operations.
- **C4, fusion.** It pays in prefill and batched GEMM. In batch-1 decode, activations already stay
  in L1/L2 [R10]. Fusion must also keep canonical order: Hearth keeps per-(token, rank) expert
  buffers so completion order cannot change a sum [R11]. Fusing SiLU needs an `expf` defined
  inside vector code [G04].
- **C5, VGATHER.** A zmm `VPGATHERDD` on Zen 5 costs 64 µops and about 12.6 cycles of reciprocal
  throughput (measured, uops.info via [R10]), the cost of about 25 contiguous loads [inference].
  Hearth already found that packing scales in general-purpose registers beat `vpgatherdd` in both
  kernels [R11]. MoE sparsity is coarse: whole multi-MB expert slabs [R06].
- **C6, low-bit via popcount.** Fast CPU kernels use lookup tables (T-MAC, bitnet.cpp TL1/TL2) or
  int8 dot products, not popcount [R10, R05, R06]. Hearth already uses `vpdpbusd` [R11]. The
  spirit is right: fewer bits mean fewer bytes, and bytes are the decode lever [R08]. The real gain
  is generating every format × ISA variant from one definition [R09].
- **C7, prefetch "dozens ahead", DRAM ~200 cycles.** DRAM latency is about 70 ns (measured),
  roughly 400 cycles at 5.7 GHz [R10, R08], and hardware prefetch usually beats software prefetch
  on Zen 5 [R10]. The pipelines that pay are NVMe→DRAM and DRAM→VRAM [R06]. In Hearth, deeper
  lookahead added 7–17% NVMe bytes per token per extra layer and *slowed* decode [R11].
- **C8, one host/device language.** Right in direction, and more relevant than the discussion
  knew, because the machine has a usable GPU. The unifying mechanism is one numeric contract plus
  explicit placement [G03]. One MVS core serves both the control plane and the compute plane
  [G05]. It need not be one *binary* [R12].

**What Mithril does.** This is the most fully adopted section.
- **C1 became N7**, physics-typed compilation: cost signatures in bytes per tier, `mithc explain`
  showing the roofline floor and fraction of roof, and quarantine for physically implausible
  results.
- **C6 became declarative block-scaled formats.** Sub-byte codes exist only inside a `format`, so
  there is no bare int4 arithmetic for a popcount lowering to grab [P3 §3.2, P4 §3.3]:

```mith
/// Hearth Q4 weight block (FORMAT.md, hx_quant.h): 64 elements in 34 bytes.
format BlockQ4 {
    d: f16,                          // block scale
    q: nibbles<64, offset = 8>,      // byte j: low nibble = elem j, high nibble = elem j+32
}
// Derived by the compiler: size == 34 (checked), elem(i) -> i32 with #[range(-8..=7)],
// pack/unpack, and the integer view used by exact dot products.
```

- **C7 became tiered residency.** Demand and prefetch reads have different priorities, compute runs
  in completion order, and a canonical-order combine fixes the result. Prefetch and eviction are
  `timing_only` policies that cannot change logits. Seed B4's alignment shows up as a type:

```mith
/// Unbuffered positional read of one expert slab. Authority is explicit in the signature.
fn read_slab(file: &BlobFile, off: Aligned<u64, 4096>, buf: &mut SlabBuf) -> Result<(), IoError>
    uses { io }
{
    file.read_at(off, buf.bytes_mut())   // std_platform: OVERLAPPED+NO_BUFFERING / pread+O_DIRECT
}
```

| Claim | Seed said | R10 | Mithril | Where it lives | Status |
|---|---|---|---|---|---|
| C1 | Roofline binds; DDR5 ~100 GB/s | mostly-true | Keep: N7 cost signatures, fraction-of-roof reporting | [02-compute](architecture/02-compute.md) (cost signatures, roofline) | v0 (M2) |
| C2 | GEMM at 90–98% of peak | mostly-true | Keep as context: no "10× GEMM" goals | [02-compute](architecture/02-compute.md) (honest perf ceilings) | — |
| C3 | 60–90% of compute wasted | misleading | Reject (claim): replaced by measured gap attribution | [02-compute](architecture/02-compute.md); [06-forge](architecture/06-forge.md) | v0 (M2) |
| C4 | Whole-layer fusion | mostly-true | Transform: fusion as schedules under canon; prefill first; specified `expf` | [02-compute](architecture/02-compute.md) (schedules, transcendentals, batched prefill) | v0 (M2; batched prefill M5) |
| C5 | Sparsity via VGATHER/VSCATTER | misleading | Reject (mechanism): block-sparse iteration, contiguous slabs, prefetch | [02-compute](architecture/02-compute.md) (block sparsity, tiers) | v0 (M4–M5) |
| C6 | Sub-byte primitives → popcount/BMI2/VNNI | misleading | Transform: `format` declarations; VNNI or LUT/`vpshufb`; MXFP4 native | [02-compute](architecture/02-compute.md) (formats); [07-hearth-port](architecture/07-hearth-port.md) (MXFP4) | v0 (M2); later (MXFP4 order, `canon.v1.1`) |
| C7 | Async pipelines; deep prefetch; DRAM ~200 cycles | misleading | Transform: tiered residency, demand/prefetch priority, `timing_only` policies | [02-compute](architecture/02-compute.md) (flows and policies, tiers) | v0 (M4–M5) |
| C8 | Unified host/device binary | unverifiable | Transform: one language, one numeric contract, explicit placement | [02-compute](architecture/02-compute.md) (placement, GPU tier) | reserved (VRAM tier), by-trigger (PTX, DR-022) |

---

## 6. D. The claimed gains

**The instinct.** Put numbers on the ambition. Asking "what would this buy?" was the right
question. The answers were the weakest part of the discussion.

**The evidence.** 7 claims: 1 mostly-true (D1), 2 misleading (D2, D5), 2 likely-fabricated (D3,
D6), 2 unverifiable (D4, D7). None of the numbers came with a source.

| Claim | Evidence | Mithril |
|---|---|---|
| D1: 80B MoE at 1.58 bits ≈ 16–18 GB (mostly-true) | Arithmetic right: 15.8 GB at 1.58 bpw, 16.7–20 GB with real packings [inference, R10]. But the quality requires native ternary training, and the only native 1.58-bit open model found is about 2B [R08]. Applied after training, it breaks INV-LOSSLESS-DEFAULT [R08]. | Defer: lower-bit cold experts only as an opt-in `lossy`/`approx` lane, never a default (DR-015). Status: reserved, later. |
| D2: 300B+ in 64–128 GB "without paging" (misleading) | Fitting needs ≤ 3.0–3.4 bpw for 128 GB and about 1.6–1.7 bpw for 64 GB [inference, R06, R08]. Paging is Hearth's thesis, not a defect [R10]. | Reject (claim). |
| D3: gains table, 5–9× / 3–5× / 1.8–2.4× (likely-fabricated) | Out-of-core 12–22 tok/s is impossible for Kimi-K2-class models (32B active) here: assuming a 40 GB expert cache and a Q8 backbone, the ceiling is 3.4 tok/s even with every expert in DRAM [inference] [R08]. Kimi-K3, the model Hearth plans to add, is far lower and trunk-bound (104B active, a ~109 GB BF16 trunk that does not fit in 64 GB). Losslessly, streaming the ≈ 59 GB of trunk that cannot stay resident at Hearth's measured 7.16 GB/s costs ≈ 8.2 s/token, so ≤ ~0.12 tok/s, and about 12 s/token once the routed experts stream too [inference] ([07-hearth-port](architecture/07-hearth-port.md) §11). Hearth's simulator figures (0.36 tok/s NVMe-bound, 1.04 tok/s all-in-DRAM; simulated, uncalibrated) assume an all-MLA model with a smaller, resident Q8 trunk, so they are not comparable and are not lossless K3 figures (07 §11, §13). With experts in RAM beside a GPU, real engines already beat the "after" column (Strata 53–94 tok/s on a 125B model at 2–3 bits, measured, project-reported) [R06, G03]. The external anchor for hybrid offload is KTransformers at 13.7–15.9 tok/s on dual Xeon plus a 4090 (measured, project-reported) [R10]. Gains come from placement and quantisation, not from a language [G03]. | Reject (claim): pre-registered benefit claims and DR-018 gates ([ROADMAP](ROADMAP.md)). |
| D4: speculative DMA hides 70–85% (unverifiable) | Overlap hides time, not bytes [R08]. Hearth's one-layer-ahead prefetch arrives late about 70% of the time when NVMe-bound (72.8% simulated) [R11]. Upload-on-miss over PCIe halved decode at a 43.5% hit rate (llama.cpp PR #30112) [G03]. | Reject (claim): tested by Hearth, tombstoned (below). |
| D5: VPOPCNTDQ replaces FMAs (misleading) | `VPOPCNTQ zmm` and `VPDPBUSD zmm` both run at 0.5 c reciprocal throughput on Zen 5 (measured) [R10]. Popcount needs binarised activations [R08]. | Reject (mechanism): see C6. |
| D6: IPC 0.8–1.4 → 2.6–3.8, power −40–60% (likely-fabricated) | At the bandwidth roof, cores must wait. A Q4 GEMV uses about 3% of instruction capacity [R08, inference]. Energy cuts of that size are sourced only for bitnet.cpp running ternary *models* [R06]. | Reject (claim): IPC is a diagnostic only. |
| D7: 15–20+ tok/s out-of-core 100B+ (unverifiable) | At about 7 GB/s, 15 tok/s allows about 0.47 GB per token from storage. That needs a ≥ 97% hit rate or about 2–3 GB of active bytes [R10, inference]. Plausible for about 5B-active models such as gpt-oss-120b (8.9–20.4 tok/s band, [inference]) [R08], or for models that fit RAM beside a GPU [G03]. Impossible for 12B+ active models streamed out of core [R08]. | Reject (claim) as general; scoped targets must state hit rate and active bytes. |

**The honest picture** for this machine
([02-compute](architecture/02-compute.md), [ARCHITECTURE §12](ARCHITECTURE.md)):
- The Qwen3-30B-A3B lossless ceiling is about 34 tok/s at 77 GB/s measured DRAM [inference].
- Hearth decodes at 19–22 tok/s against llama.cpp's ~25 (measured, noisy, not a clean
  head-to-head), which leaves about 1.5× of honest CPU headroom [inference].
- The GPU tier is the largest lossless lever: 3.6–4.8× for in-RAM MoE (simulated) [G03].
- Kimi-K2-class models (32B active) on one NVMe fall in a 0.8–2.9 tok/s band, assuming a 40 GB
  expert cache, a Q8 backbone and a 50–80% hit rate, under a 3.4 tok/s all-in-DRAM cap
  [inference] [R08]. Kimi-K3 is far lower and trunk-bound: losslessly ≤ ~0.12 tok/s (≈ 59 GB of
  trunk streamed per token at 7.16 GB/s ≈ 8.2 s; about 12 s/token with experts) [inference]
  ([07-hearth-port](architecture/07-hearth-port.md) §11). Hearth's simulator figures (0.36 tok/s
  NVMe-bound, 1.04 tok/s all-in-DRAM, simulated) assume a smaller resident Q8 trunk and are not
  comparable. Either way the seed's 12–22 tok/s is out of reach: 4–8× above the top of the K2-class
  band and ≈ 100× or more above K3's lossless bound [inference].

Speed comes from bytes, placement and scheduling, not from syntax.

**What Mithril does.** It has no gains table. Seed D is where the ledger idea becomes a type (N3,
INV-HONEST):

```mith
let bw: Quantity<GBps, Measured> = profile.dram_read_all_core;
// Formatting prints value + origin ("77 GB/s, measured, <hw fingerprint>"); an unlabelled
// number does not format. Simulated and measured quantities do not mix without conversion.
```

A gains table could not even be printed under this rule: every cell would need an origin, a
hardware fingerprint and a ledger entry. Seed claims enter the ledger as hypotheses and become
tombstones or elites only after they are executed [P4 §8.7], because ideation-stage judgments
mislead [R02]. "Hypothesis" is not a new status or a separate ledger. In the one ledger's fact
schema ([03-trust](architecture/03-trust.md) §4.1, [ARCH §8.3](ARCHITECTURE.md)) a seed claim is a
`claim` fact with verdict `unknown` and grade `assumed` in its property kind (like an `ext.*` fact,
it can fire a revisit but never a promotion), with the seed and its R10 verdict as provenance.
Status is a Fact Plane view, never stored, and "hypothesis" names the view of claims whose verdict
is still `unknown`. An `unknown` verdict satisfies no slot, so a hypothesis cannot license a
default, a promotion or a headline. Nothing executes it automatically. A test is pre-registered (a
ROADMAP benefit claim, a Forge task or a port-stage check), and its result is admitted as a new
fact: an `accept` with a scope (an elite) or a `reject` with a scope and a trigger (a tombstone).
The append-only store keeps the hypothesis beside it. The design-level entries in §12 are buried
differently: they rest on cited dossier evidence and are admitted with the Owner key
([DECISIONS](DECISIONS.md) §1). Seed D4 has, in effect, already been executed on Hearth:

```text
tombstone lookahead_depth_4 {                       // a ledger fact, shown as text
    verdict: slower                                 // decode 13.0 -> 10.0 tok/s (measured)
    scope:   { model: qwen3_30b_a3b, drives: 1 (990 PRO), cache_gib: 2..=4 }
    class:   H                                      // hardware-contingent
    revisit_when: nvme_read_gbps > 12.0 || tier_exists(vram) || drives >= 2
    evidence: ledger:sha256:…
}
```

Deeper prefetch is not declared dead. It is declared slower *on one drive at this bandwidth*. When
a second drive, a faster drive or a VRAM tier appears, its trigger fires, which queues it for a
revisit: rebuild from the recipe, re-measure, and only then search
([06-forge](architecture/06-forge.md) §7.4). Revisits are priority-sampled, so a fired trigger
makes the idea eligible again; it does not adopt it. This is the owner's "revisit unfruitful
spaces" instinct, applied to the seed itself.

Reviewer note: 06-forge §7.5 (after P4 §8.7) says seed claims enter "a claims ledger". There is
only one ledger. If a named status is wanted, ARCH §8.3 and 03-trust §4.1 should list `hypothesis`
as the Fact Plane view defined above rather than as a stored field.

---

## 7. E. Visual generation

**The instinct.** Machinery that can schedule MoE inference should also serve real-time visual
generation: 4D Gaussians, flow-matching solvers, spatio-temporal tiles, skipping redundant work,
on-chip residency, and direct scan-out.

**The evidence.** 8 claims: 3 mostly-true (E1, E2, E7), 3 misleading (E3, E4, E6), 1 unverifiable
(E5), 1 likely-fabricated (E8).
- **E1, `Gaussian4D`.** The algorithm (tile binning, sort, front-to-back blend) is real. The
  struct is wrong: degree-3 spherical harmonics need 48 coefficients, not 16; time needs an extent
  or a 4D covariance; a 4D rotation needs two quaternions. Real-time 3DGS is a GPU result [R10,
  R13].
- **E2.** Flow-matching samplers are ODE solvers, but distillation to 1–4 steps leaves little for
  adaptive RK [R13].
- **E3.** 4×8×8 is Wan's *VAE* compression ratio; the DiT patch is 1×2×2. Tiles match attention
  block sizes, not cache lines [R10, R13].
- **E4.** The exploited redundancy runs *across denoising steps*: FORA, Δ-DiT, TeaCache (up to
  4.41×) and PAB (up to 10.5×), all project-reported [R10]. Skipping happens per block; CMOV
  computes both sides [R13].
- **E5.** Even a 1.3B model's weights are 2.6 GB in BF16, and the residual stream is about 100 MB
  at 480p, against 32 MB of L3 per CCD [R10, R13, inference].
- **E6.** There are no E-cores [R10]. **E7.** DRM/KMS is Linux-only; Windows uses the DXGI flip
  model, and the copy takes about 0.1 ms [R13].
- **E8.** On CPU this is ≈30–40× short of Self-Forcing-class 16 fps at 480p on raw peak, and
  ≥ 250× short of the seed's 720p/1080p 30 fps target [R13, inference]. The state of the art is
  about 16 FPS at 480p on one H100 (Self Forcing, measured, project-reported) [R10].

**What Mithril does.** Video diffusion sits on the compute roof and needs tensor cores [R13,
G03]. DR-024 settles the scope: no visual-generation primitives in v1. Mithril builds only the
general features this workload would need: a layout/tile algebra, block-sparse iteration, and a
**reserved** approx/cache effect for step-to-step caching. Generative video waits for a GPU backend
(v2+). The syntax sketch (`tensor<float8,[B,64,64,16],Layout::...>`, `fuse_layers { ... }`) hides
new meaning behind semi-familiar tokens. That is the false-friend pattern that costs LLMs most
[G01, R03], and the subset rule (DR-002) rejects it.

| Claim | R10 | Mithril | Where it lives | Status |
|---|---|---|---|---|
| E1 | mostly-true | Reject (mechanism) as a primitive; at most a library type | [02-compute](architecture/02-compute.md) (visual-generation scope boundary) | — |
| E2 | mostly-true | Defer: moot under few-step distillation | [DECISIONS](DECISIONS.md) (DR-024) | later |
| E3 | misleading | Transform: general layout/tile algebra | [02-compute](architecture/02-compute.md) (formats/layouts) | v0 where the port needs it, v1 otherwise |
| E4 | misleading | Transform: step caching via the reserved approx/cache effect, opt-in, lossy-labelled | [02-compute](architecture/02-compute.md) (reserved approx/cache effect) | reserved |
| E5 | unverifiable | Reject (mechanism) | — | — |
| E6 | misleading | Reject (mechanism) | — | — |
| E7 | mostly-true | Reject (mechanism): wrong platform, negligible gain | — | — |
| E8 | likely-fabricated | Reject (claim) | [ARCH §15](ARCHITECTURE.md) (non-goals) | — |

---

## 8. F. The openai/math repository

**The instinct.** A large corpus of machine-checked mathematics should help a verified compiler.
It might supply proof infrastructure, and perhaps theorems relevant to register allocation,
routing and solvers.

**The correction: the repository is real; the cited families are wrong.** R10 checked it directly
[R10 F-F; also R04, R07]:
- `openai/math` exists. It was created on 2026-10-06 under Apache-2.0 and had about 13.9k stars
  when checked. Its README says an internal OpenAI model produced the manuscripts from roughly
  4,000 posed problems.
- It catalogues **719 manuscripts in 372 families** (third-party trackers counted 722 at launch).
  It has a Lean 4 library on toolchain v4.34.1, with about 42% of top-line results formalised. The
  repository itself warns that results are at different stages of verification.
- **Comparator** is not an OpenAI harness. It is `leanprover/comparator` (created 2025-06), a
  generic judge. It checks that a `Solution` proves the *same statements* as a trusted
  `Challenge`, allows only whitelisted axioms, runs under the `landrun` sandbox, and can replay on
  a second kernel (nanoda).

So F1 is mostly-true. The family claims fail against the catalogue's own overview:

| Seed says | Catalogue says | Verdict |
|---|---|---|
| 087 = SDP thresholds → register allocation with "zero stack spills" | 087 is the Mahler conjectures and symplectic width. The SDP-related result is **102** (Unique Games and approximation thresholds), a *hardness* result that gives no allocator | F3 false |
| 197 = Mézard–Parisi, "dual to" MoE routing and L3-slice partitioning | 197 is nonsofic groups (Kaplansky direct finiteness). Mézard–Parisi is **221**. No basis for the "duality" was found, and software cannot choose L3 slices | F4 false |
| Formalised ODE bounds → Lean-verified adaptive RK solvers | No ODE or numerical-analysis discipline exists in the catalogue (mathlib separately has ODE basics) | F5 likely-fabricated |

The surrounding claims fail as well.
- "Zero stack spills" is impossible whenever live values exceed the 16 GPRs or 32 zmm registers,
  and register allocation by graph colouring is the classic NP-hard formulation [R10].
- **F2 is a category error.** The repository has no x86, SIMD or tensor semantics, and Comparator
  matches Lean statements only [R07, R04]. Checking x86 in Lean would first need an AVX-512
  semantics (none is public) and an IEEE Float32 lemma library (none exists) [R07, G02].
- **F6 is backwards.** Lean's best automation *uses* solvers: `bv_decide` runs a SAT solver and
  checks its certificate [R10, R07]. For agent-written proofs, SMT-backed auto-active verification
  wins. Vericoding off-the-shelf rates: Dafny 82%, Verus 44%, Lean 27% (measured,
  project-reported) [G01, R04]. Lean's kernel also had a soundness bug as recently as July 2026
  [R07].

**What Mithril does.** Two durable ideas survive, and neither depends on the family claims.
1. **The Comparator pattern** becomes the acceptance gate for agent-supplied proofs: a trusted
   statement, an untrusted proof, an axiom whitelist, sandboxed replay, and an optional second
   kernel. It maps onto spec escrow: the Author role owns the statement, and the Builder or Prover
   supplies the proof ([03-trust](architecture/03-trust.md)).
2. **Solvers and proof assistants are complementary.** SMT (T2) does the everyday work. Lean is
   used later and only for TCB-critical pieces: the T1 exact-rewrite list (first checked by Z3 FPA
   or exhaustive binary32 testing) and the `timing_only` store-core theorem. Core mechanisation
   waits for a trigger (DR-010). Mithril says plainly that the Dafny 82% figure does not transfer
   automatically to a Rust-shaped language; Verus scores 44% (DR-012).

Treat the catalogue's headline results, such as its claimed proof of the Unique Games Conjecture,
with care until they are independently verified. No Mithril decision depends on them [R10].

| Claim | R10 | Mithril | Where it lives | Status |
|---|---|---|---|---|
| F1 | mostly-true | Context: repository real; Comparator is the Lean FRO's tool | — | — |
| F2 | misleading | Transform: Comparator-style gate for agent proofs | [03-trust](architecture/03-trust.md) (verification tiers, roles) | later |
| F3 | false | Reject (claim) | — | — |
| F4 | false | Reject (claim) | — | — |
| F5 | likely-fabricated | Reject (claim); RK solvers are also moot (E2) | — | — |
| F6 | misleading | Reject (mechanism): SMT plus certificates now, Lean later | [03-trust](architecture/03-trust.md); [01-language](architecture/01-language.md) (specs) | v0 (T2, M2), by-trigger (Lean) |

---

## 9. G. Projects and theory to study

**The instinct.** Learn from existing superoptimisers, validators, kernel DSLs and profilers.

**The evidence.** 2 claims: G1 true, G2 mostly-true. All eight repositories exist (checked
2026-10-11). Triton has moved to `triton-lang`, STOKE is unmaintained, Souper and Alive2 work on
LLVM IR, and SPDK documents Linux and FreeBSD only [R10]. The list leaves out the systems most
relevant to Mithril:
- Exo, Halide, MLIR/IREE, ISPC, Highway, KleidiAI and the oneDNN ukernel API [R05];
- Hydride, MISAAL, VeGen, Minotaur, s2n-bignum and Bochs [G02];
- CryptOpt, the closest existing realisation of seed B8, and KLEE-FP, whose structural FP
  equivalence underlies T1 [R07];
- Jasmin [R10].

Polyhedral methods belong in legality analysis, not global scheduling [R05]. TMA is Intel's
method [R10]. Triton and TileLang have no determinism contract [G03]. SPSC rings are optional in
v1 [G05]. PCIe BARs are `foreign`/`unsafe` and not reachable from a Windows user process [G05,
R10].

**What Mithril does.** It borrows openly: Exo's schedule model (MIT) with an IEEE-exact mode added
[R05], KLEE-FP's technique [R07], Intel XED (Apache-2.0) as the semantics-table key [G02], and the
Hylo, Austral and Koka lineages for memory and effects [R09].

| Claim | R10 | Mithril | Where it lives | Status |
|---|---|---|---|---|
| G1 | true | Keep, extended (list above) | [ARCH §19](ARCHITECTURE.md); [03-trust](architecture/03-trust.md) | — |
| G2 | mostly-true | Transform: polyhedral for legality only; SPSC optional; BAR/SPDK outside v1 | [02-compute](architecture/02-compute.md); [04-toolchain](architecture/04-toolchain.md) | — |

---

## 10. H. Go-to-market and agent discovery

**The instinct.** The first users are coding agents. Make the language easy to try, easy to embed
and easy to learn, and give it diagnostics a machine can act on.

**The evidence.** 7 claims: 2 true (H2, H5), 2 mostly-true (H3, H4), 2 misleading (H6, H7), 1
likely-fabricated (H1).
- **H1.** "IPC 1.1 → 3.2" is an invented number, and `curl | bash` is a supply-chain
  anti-pattern [R10]. The honest headline metrics are tok/s with bytes per token per tier, hit
  rate counted correctly, and the noise floor [R06].
- **H4.** The direction is right; the delivery is wrong. An index kept always in context works:
  Vercel's 8 KB AGENTS.md index scored 100% against 53% with no docs. An on-demand skill was never
  invoked in 56% of runs, and "comprehensive" docs added only +0.7 pp in SkillsBench (all measured,
  project-reported) [G01]. The grammar should be a Lark file [R03]. There is no evidence that
  agents consume llms.txt, and `llms-full.txt` is not part of the proposal [R10, R04].
- **H5.** Probably the highest-leverage idea in the discussion. Grouped errors moved GPT-3.5 from
  4.97% to 44.76% fixed in RustAssistant [R03], and DGM's discovered gains were mostly tool and
  feedback ergonomics [R01]. rustc JSON and SARIF are precedents [R04].
- **H6.** Seeding synthetic repositories conflicts with GitHub's Acceptable Use Policies [R10] and
  does not move frontier pretraining. Mojo still ships a correction skill [R04, G01].
- **H7.** Mojo *does* have inline assembly [R10]. Exo, Jasmin, STOKE, SuperCoder, MoonBit and Bend
  each cover part of the space [R03, R04, R05]. What R04 found missing is hardware-cost-aware
  semantics plus determinism contracts plus verification for CPU inference (medium confidence).

**What Mithril does.**
- **H5, adopted and extended.** Every verb takes `--json` and ends with `next: [...]`; output is
  SARIF 2.1.0 with LSP and MCP surfaces. Each fix states its applicability and evidence
  consequences. Example: a bare float `.sum()` in exact code is rejected. The *Safe* fix is
  `canon::sum_seq`; the *MeaningChanging* fix is `canon::sum16`, which lists the ledger entries it
  invalidates (DR-013).
- **H4** becomes the tiered card: Tier 0 of at most 8 KB in AGENTS.md, a project card of at most
  4 KB, and Tier 1 via `mithc guide`. llms.txt remains a cheap extra.
- **H6** is replaced by Mithril MultiPL-E plus sealed tasks, with local-only fine-tunes.
- **H7** is replaced by an honest novelty claim: the combination, made checkable (N1–N8).

| Claim | R10 | Mithril | Where it lives | Status |
|---|---|---|---|---|
| H1 | likely-fabricated | Reject (claim): honest headline metrics | [02-compute](architecture/02-compute.md) (honest perf ceilings) | — |
| H2 | true | Keep: export `hearth.h` exactly (S6a); C11 with no hidden runtime; a Python *binding* is fine, a Python-*embedded* surface is not [G01] | [07-hearth-port](architecture/07-hearth-port.md); [04-toolchain](architecture/04-toolchain.md) | v0 (S6a, M5) |
| H3 | mostly-true | Keep: certificates ship in the ledger. Semantics are hand-written from the SDM, not derived from Intel XML, to keep them publishable [G02] | [03-trust](architecture/03-trust.md) (ledger) | v0 (M2 certificates; signed ledger M3) |
| H4 | mostly-true | Transform: tiered cards, Lark grammar, `mithc guide` | [05-agent-protocol](architecture/05-agent-protocol.md) (cards, grammar) | v0 (M1) |
| H5 | true | Keep, extended: JSON/SARIF, applicability, evidence obligations, false-friend names | [05-agent-protocol](architecture/05-agent-protocol.md) (diagnostics) | v0 (M1) |
| H6 | misleading | Reject (mechanism): eval corpus plus local fine-tunes | [05-agent-protocol](architecture/05-agent-protocol.md) (harness, MultiPL-E) | v0 (harness) |
| H7 | misleading | Reject (claim) | [ARCH §1](ARCHITECTURE.md) | — |

---

## 11. I. "Living tissue"

**The instinct.** Models should keep learning while they serve, without forgetting. The proposed
means: surgical weight edits, experts that grow on demand, an evolutionary loop over the training
program, safe hot-swaps between tokens, and self-modifying code.

**The evidence.** 8 claims: 1 mostly-true (I1), 4 false (I4, I5, I6, I7), 3 unverifiable (I2,
I3, I8). Two-thirds of the discussion's false claims are here.
- **I1.** The mechanism is real. AlphaEdit projects each update onto a null space estimated from
  about 100k Wikipedia triples, thresholded at eigenvalue 1e-2, and was tested to about
  2,000–3,000 edits [R10]. At scale editing degrades, and retrieval beats it for facts [R12].
- **I2, I3.** PEER and memory layers are the nearest precedents for retrieval-style routing, but
  "unallocated subspace of an expert" has no operational definition. Growing capacity while
  freezing old weights is demonstrated; entropy-triggered expert birth is not [R12].
- **I4.** The loop half is plausible: ShinkaEvolve evolved an MoE load-balancing loss [R01]. The
  SMT half is false. ReLU-network verification is NP-complete, softmax brings in transcendental
  logic, and "loss divergence" over a data distribution is a statistical property, not a logical
  one [R07]. The DGM's defining move was to replace proofs with empirical validation [R02].
- **I5.** On Zen 5, LOCK CMPXCHG16B takes about 17 cycles reciprocal throughput and 19+ cycles
  latency, at 26 µops (measured) [R10, R08]. It is not needed: an aligned 8-byte release store
  publishes a pointer. The hard part is reclamation [G05, R12].
- **I6.** Null-space methods *mitigate* forgetting. Σ_prior is a sample statistic, and the null
  space is thresholded and shrinks. "At the machine-code level" is a category error [R12, R10].
- **I7.** INVD is ring-0 only and *discards* dirty lines, so it would corrupt memory. CLFLUSH does
  not serialise instruction fetch. Cross-modifying code needs a serialising instruction or
  `FlushInstructionCache` [R10, R08]. Weight updates are data, not code [R12].
- **I8.** A vision statement. Per-sequence learning is real when the architecture is built for it
  (Titans, KDA); persistent self-updating is research that reports forgetting [R12].

**What Mithril does.** It keeps the question and replaces the mechanisms.
- **Hot-swap** (I5, I7) happens only at quiescent token-boundary epochs: versioned dispatch tables,
  a release-store of an aligned pointer, and reclamation by quiescence plus `Frozen<T>` refcounts
  [P4 §6.5]. If leases cannot cross a `tick`, as in Hearth today, epochs are unnecessary [G05].
  There is no self-modifying code. Runtime code generation exists only as the deferred
  copy-and-patch JIT (backend B4, with W^X and `FlushInstructionCache`).
- **Living models** (I1, I3, I8) are post-v1 (DR-025). Weights are immutable and
  content-addressed. Typed overlays (`SlabReplace`, `LowRank`, `AddExpert`, ...) are applied
  copy-on-write per expert, committed at token-boundary epochs, carry signed provenance and pass
  statistical gates. Retrieval is the default path for facts [P4 §6.6, R12]. The KDA
  recurrent-state snapshot API is designed together with overlays when Hearth adds Kimi-K3.
- **I4's loop half** is the Forge. Overlays are candidates in the lossy lane, judged by a
  hash-locked gate set, and never a default [P4 §8.12].
- **I6** survives at most as a later runtime-checked contract with a measured residual, never as a
  type-level guarantee [R12].

Reviewer note: P4 §8.12 produced overlays under a dedicated training effect, but the canonical
effect list has none. Living models are post-v1, so this document names no such effect;
01-language should say whether one is reserved ("reserve the lattice"). Hot-swap is *later*, as in
04-toolchain §9.2 and §15, since its first consumers (overlays, live policy swap) are post-v1.

| Claim | R10 | Mithril | Where it lives | Status |
|---|---|---|---|---|
| I1 | mostly-true | Defer: `LowRank` overlay under gates; claims scoped to the measured key set | [06-forge](architecture/06-forge.md) (living models) | later |
| I2 | unverifiable | Reject (mechanism): no operational definition | — | — |
| I3 | unverifiable | Defer: `AddExpert` overlay under gates; no automatic birth | [06-forge](architecture/06-forge.md) (living models) | later |
| I4 | false | Transform: loop half = Forge with statistical gates; SMT half rejected | [06-forge](architecture/06-forge.md); [03-trust](architecture/03-trust.md) (promotion) | v0 (F1-live, M4); v1 (F1 campaigns, M6); later (overlays) |
| I5 | false | Transform: pointer publish at token-boundary epochs | [04-toolchain](architecture/04-toolchain.md) (runtime, `std_platform`) | later |
| I6 | false | Reject (mechanism) as a type | [06-forge](architecture/06-forge.md) | — |
| I7 | false | Reject (mechanism): no SMC; W^X copy-and-patch only | [04-toolchain](architecture/04-toolchain.md) (backends) | by-trigger (backend B4) |
| I8 | unverifiable | Defer: KDA state API designed with overlays (DR-025) | [07-hearth-port](architecture/07-hearth-port.md) (Kimi-K3) | later |

---

## 12. Rejected seed ideas as design-level tombstones

In Mithril a rejection is not a deletion. Each rejected idea becomes a scoped tombstone with a
failure class (H hardware, T tooling, S search, E effort, V evaluation, C composition, X scale, F
fundamental-under-assumption) and a decidable resurrection trigger. `mithc revisit --design`
re-checks those triggers whenever the environment changes (N4,
[06-forge](architecture/06-forge.md)). A fired design trigger re-opens nothing by itself: it
produces a report for the Owner, because design changes are AUTHORITY operations (06-forge §7.5).

The canonical records live in [DECISIONS.md](DECISIONS.md) §4 (tombstones) and §3 (DR triggers).
This table is a seed-specific summary. **Where a DECISIONS record exists, it governs**; the table
names the record and paraphrases its class and trigger. Three rows (element gathers, popcount
lowering, 1.58-bit execution) have no DECISIONS record yet. Their class and trigger are this
document's proposal, and `mithc revisit --design`, which reads only DECISIONS.md, does not
evaluate them until they are added there.

| Seed idea (claims) | DECISIONS record | Class | Trigger fires when |
|---|---|---|---|
| P/E-core dual code paths (B10, E6) | `pe_core_dual_paths` | H | a supported target exposes different ISA features on different core types |
| µop-port superoptimisation as the main path (B2) | `uop_port_superopt_main_path` | H | the hot path's binding resource becomes core issue rather than a memory tier |
| Direct ELF output / bypassing LLVM as a goal (B2, B8) | `bypass_llvm_as_goal`; DR-009 | T | ≥ 5% of a kernel gap is attributed to LLVM's scheduling model. DR-009 builds the emitter on an unpinnable compiler rewrite or a ≥ 5% codegen-attributable kernel gap |
| Element gathers as the sparsity lowering (C5) | none yet (proposed) | H | a target's fuzzed cost table shows zmm gathers near contiguous-load throughput |
| Popcount lowering for low-bit weights (C6, D5) | none yet (proposed) | F (under int8 activations) | a format with binarised (±1) activations enters the format library |
| IPC as objective or headline (B3, D6, H1) | `ipc_objective` | F (under bandwidth-bound kernels) | a kernel set becomes core-issue-bound *and* measured IPC rank-correlates ≥ 0.95 with inverse wall time. Headlines stay tok/s and bytes per token per tier (H1) |
| Deep prefetch as "the lever" (C7, D4) | `lookahead_depth_4` (Hearth engine tombstone, imported at S0, [07-hearth-port](architecture/07-hearth-port.md)) | H | NVMe reads exceed 12 GB/s, a second drive is added, or a VRAM tier exists (§6) |
| SPDK / user-space NVMe as default (G1) | `spdk_bypass_default` | H | NVMe I/O needs at least one full core at link bandwidth, or overlapped reads fall below 80% of aggregate drive bandwidth |
| Lean replacing SMT (F2, F6) | `lean_replacing_smt` | T | published vericoding rates put Lean at or above Dafny, or Lean matches SMT on the Mithril proof suite |
| Visual-generation primitives (E1–E8) | DR-024 | H (this document's; DRs carry no class) | the Owner puts visual generation in scope and the PTX backend is live |
| 1.58-bit execution of existing models (D1) | none yet (proposed) | X | a natively ternary-trained MoE of the size Hearth targets is released |
| SMT bounds on loss divergence (I4) | `static_model_quality_guarantees` | F | a static quality certificate at model scale is admitted to the ledger |
| Forgetting-free subspace types (I6) | `static_model_quality_guarantees` | F | the same trigger; until then the runtime-checked contract stays a later lane, never a type-level guarantee |
| Self-modifying code via INVD/CLFLUSH (I7) | `runtime_self_modifying_code` | F | no supported target enforces W^X, or Hearth requires a hot-swap inside a token. A revisit would still find INVD ring-0 only and destructive; runtime codegen is backend B4, by trigger |
| CMPXCHG16B "single-cycle" hot patch (I5) | `runtime_self_modifying_code` (scope includes `cmpxchg16b_hotpatch`) | F | the same trigger; today an aligned pointer publish suffices |
| Seeding synthetic GitHub repositories (H6) | `seed_synthetic_repos` | E | a frontier vendor documents a policy-compliant corpus intake path. Local fine-tunes re-open separately under DR-023 |

Reviewer note: DECISIONS §4 should add the three rows marked "none yet", for example as a §4.4
"Seed-specific tombstones" block, so that `mithc revisit --design` can evaluate them. Until then
this table is their only record.

---

## 13. What the discussion got most right

The discussion had good instincts. Mithril keeps more of it than the verdict counts suggest. The
claims that failed were mostly measurements nobody had taken; the claims that survived were mostly
design ideas.

1. **"Search, then prove" (B3, B8, B12).** Pairing an untrusted optimiser with an equivalence
   checker is the right shape. It became Mithril's central construction: certified modification
   spaces searched with performance evidence alone (N1), and IEEE-exact translation validation of
   SIMD kernels (N2). The corrections made it workable: canonical order and DAG matching instead
   of FP SMT, and schedules instead of bytes.
2. **The roofline (C1, C2).** The discussion's own reality check was its most important passage.
   It is why every Mithril result is reported as a fraction of a measured roof (N7). It is also
   why the honest Hearth picture is about 1.5× of CPU headroom, with the GPU tier as the largest
   lever.
3. **Hardware-aware types (B4, B5, C6, C7).** Alignment as a type, alias-freedom by construction,
   low-bit formats as first-class declarations, and memory movement as explicit, prioritised
   pipelines all survive. They live in formats, MVS, projections and tiered residency, not in new
   primitive types.
4. **Machine-actionable diagnostics (H5).** This is the best-evidenced lever for agents, and
   Mithril adds applicability levels and evidence obligations to it.
5. **Agents as users (H4 and the premise itself).** R04 sharpens the premise: what is AI-first is
   the toolchain and the semantics, not the syntax. The cards, the cold-agent harness and language
   governance by measured comprehension (N6) follow from taking it seriously.
6. **Changing a model while it serves (I1, I5, I8).** The mechanisms were wrong, but the question
   was right. Its answer shapes the runtime even though living models come after v1: immutable
   weights, typed overlays and token-boundary epochs.
7. **"Revisit what we dismissed."** This came from the owner's brief, not the chat, and it is the
   deepest idea in the seed material. The evidence backs it. The DGM fell from 50.0% to 23.0% on
   SWE-bench without open-ended exploration [R02]. Six independent revisit branches converged on
   "prove the space, not the candidate" [RV: §6]. Mithril makes it a mechanism, scoped tombstones
   with machine-checkable triggers and `mithc revisit` (N4), and applies it first to the seed
   discussion itself.

The failures, too, became features.
- Unmeasured numbers led to `Quantity<Unit, Origin>` and ledger-backed claims.
- Unchecked citations led to seed claims entering as hypotheses: `unknown`-verdict claims that
  license nothing until a test settles them (§6).
- A misread machine led to hardware fingerprints on every performance claim.
- Over-promised guarantees led to one rule: guarantee emission and equivalence, and measure
  everything else.

---

## 14. Sources

- Verdicts: [R10](research/R10-seed-fact-check.md) (verdict table, findings F-A to F-I, "Ideas that
  survive").
- "Where the seed discussion is right or wrong" sections:
  [R01](research/R01-self-improving-systems.md), [R02](research/R02-open-endedness-revisiting.md),
  [R03](research/R03-llm-language-ergonomics.md), [R04](research/R04-ai-first-languages-landscape.md),
  [R05](research/R05-kernel-dsls-and-schedules.md), [R06](research/R06-local-inference-moe-landscape.md),
  [R07](research/R07-verification-superoptimization.md), [R08](research/R08-hardware-reality.md),
  [R09](research/R09-language-building-blocks.md), [R11](research/R11-hearth-port-requirements.md),
  [R12](research/R12-living-models.md), [R13](research/R13-visual-generation-local.md),
  [G01](research/G01-new-language-cold-start-evidence.md),
  [G02](research/G02-x86-avx512-formal-semantics-sources.md),
  [G03](research/G03-gpu-tier-and-cross-device-determinism.md),
  [G04](research/G04-transcendental-libm-numeric-spec.md),
  [G05](research/G05-shared-mutable-state-memory-model.md).
- Revisit archive: [revisited-ideas.md](research/revisited-ideas.md) (§4 adoptions, §5 still dead,
  §6 cross-cutting insights).
- Proposals: [P2](design/proposals/P2-tractable-godel.md) §5.2;
  [P3](design/proposals/P3-physics-first.md) §1, §3.2;
  [P4](design/proposals/P4-living-forge.md) §3.3, §6.5, §6.6, §8.7, §8.12.
- Sibling documents: [ARCHITECTURE.md](ARCHITECTURE.md), [01-language](architecture/01-language.md),
  [02-compute](architecture/02-compute.md), [03-trust](architecture/03-trust.md),
  [04-toolchain](architecture/04-toolchain.md), [05-agent-protocol](architecture/05-agent-protocol.md),
  [06-forge](architecture/06-forge.md), [07-hearth-port](architecture/07-hearth-port.md),
  [ROADMAP.md](ROADMAP.md), [DECISIONS.md](DECISIONS.md).
