# X2: Zen 5 fuzz harness design

Status: DESIGN, DRAFT, revised 2026-10-16 after two same-family reviews (review log in
[TABLE-SCHEMA.md §15](TABLE-SCHEMA.md#15-review-log)). **Harness built and self-tested 2026-10-16
(x2build track; [harness/](harness/README.md), status in §9), then revised the same day after one
same-family, independent-context review of the build (§9.6).** No vector of the budget has been
generated for silicon or run; the only table instructions executed on silicon were a development smoke
run on the hand vectors of `semantics/selftest.py` (§9.3) and the exhaustive engine's plumbing check
(40 V5-eligible stubs × 4,096 fixed inputs, §9.1). Under the collection rule of
[docs/m0/README.md](../../docs/m0/README.md), the first native run of the budget waits for the X2
record ([docs/m0/prereg/X2-checker.md](../../docs/m0/prereg/X2-checker.md)) to be FROZEN and either
SIGNED or covered by an explicit Owner instruction (D0-12, provisional chat answer of 2026-10-16: batch
weekly review). Tags as in [TABLE-SCHEMA.md](TABLE-SCHEMA.md);
"[M] X2-agent 2026-10-16" means read or measured by this track's agent (author or reviser) on that
date.

ROADMAP §3.3 asks for: the FP-sensitive iclasses run on the 9950X with SNaN/QNaN payloads in each
operand, ±0, subnormals, every mask pattern, VCVTPS2DQ indefinite results and MAXPS/MINPS NaN order;
Bochs as the second oracle; a pre-registered per-iclass vector budget. This file is the plan for all
three, plus the integer and data-movement entries.

---

## 1. Pipeline

Two modes share the stubs, the reference interpreter and the comparator.

```text
SAMPLED MODE (V1-V4, BCAST, F-MEMFAULT)
table entry (content hash)                         vector set (sha256)
   |  case classes (§3), budget.v1.json (§5)            |
   v                                                    v
generator (Python, seeded) --> vectors.bin --> native harness (C + byte-exact stubs, MSVC, 9950X)
                                   |                    |  results.bin + fingerprint
                                   |                    v
                                   +--> reference interpreter (generated C; Python oracle on a sample)
                                   |                    |  predictions.bin
                                   +--> Bochs image (same stubs, bare metal)  --> bochs.bin
                                                        v
                              comparator (deterministic script) --> per (entry, class, env) counts,
                              every disagreement with its 3-way verdict (§6) --> ledger fuzz_record

EXHAUSTIVE MODE (V5)
native driver: for x in enumeration(entry, env):  silicon = stub(x); predicted = interp(x)
               if silicon != predicted: append (x, silicon, predicted) to mismatches.bin
               sha256.update(x || silicon)
output: mismatches.bin, the stream hash, the count, the fingerprint
```

Every artefact is content-addressed: the vector set by its sha256, the stubs by the XED-encoded
bytes, the reference by the table bundle hash and the generated interpreter's own hash, the result by
(vector hash, stub hash, interpreter hash, fingerprint). The comparator is a Gatekeeper script:
agents run it, they never judge its output (ROADMAP §1 rule 3).

**Why two modes (finding R2-12).** The exhaustive sweeps are about 5.9 × 10^11 lane cases for the
v0 table [D, §5]; through files that is about 2.4 TB of inputs alone at 4 bytes per case [D], plus
outputs and predictions, which the pipeline above cannot carry. In exhaustive mode the driver
enumerates the inputs itself, links the generated C interpreter, compares in-process, and writes
only the mismatches plus a sha256 over the (input, silicon output) stream. The second-CCD repeat (§4)
compares stream hashes. Run times are re-estimated from a week-1 measurement of the interpreter's
ns per case before freeze; if the budget does not fit the daytime windows, the record is amended
before data, never after.

## 2. What a test is

- **Lane case.** One (source lane values, environment, mask bit, immediate) tuple pushed through one
  table entry. It is the counting unit of the budget (§5).
- **Execution.** One run of one instruction with every lane populated: a zmm execution carries 16
  f32 lane cases, a ymm one 8.
- **Lane observables.** Every bit of the destination register at full 512-bit width (to see
  upper-bit zeroing and merge-masked lanes), the destination opmask for compares, RFLAGS (ZF, PF, CF,
  OF, SF, AF) for (U)COMISS, the full 64-bit GPR for CVT(T)SS2SI. A value mismatch is attributed to
  the lane case whose destination bits differ.
- **Execution observable: MXCSR[5:0] (finding R1-3).** The flags are one sticky OR over all active
  lanes of an execution, so a flag value cannot be attributed to one lane. The harness clears the
  flags before each execution and reads MXCSR after it. The **predicted** flags of an execution are
  the OR of the table's predicted flags over its active lanes (masked-off lanes contribute nothing,
  per the reading that class F-MASKEXC tests). A **flag mismatch** is counted per (entry, class,
  environment, execution).
- **Flag isolation.** A wrong per-lane flag prediction is invisible whenever another active lane in
  the same execution raises that flag legitimately. So every **flag-bearing class** (F-FLAGPRI,
  F-TINY, F-FTZ-EXACT, F-DAZ-SEL, F-DAZ-CVT, F-H2F, F-MASKEXC, UFL, OVF, TIE, CVT-BND, CANCEL) is run
  with **flag-neutral fillers**: every lane except the one under test holds a case for which the
  table predicts no flag in that environment (`1.0 + 1.0`, `max(1.0, 2.0)`, `cmp(1.0, 2.0)` with a
  quiet predicate, `cvt(1.0)`, `cvt_i2f(1)`). For EVEX forms the same cases also run as
  single-active-lane executions through the write mask; those results are interpreted only after
  F-MASKEXC has passed. Scalar forms are single-lane by construction. Mixed executions (the V1 grid)
  compare the OR; any flag mismatch there is triaged by re-running each active lane in isolation.
- **Mismatch.** Any lane-observable bit, or any execution-observable flag bit, that differs between
  silicon and the table's prediction. Flags count (TABLE-SCHEMA §13 Owner question 2). The
  pre-registration (§4 item 8) defines the unit formally.

## 3. Generator classes

### 3.1 Value classes for one f32 source

| # | Class | Draws | Why |
|---|---|---|---|
| 1, 2 | `Z+`, `Z−` | exactly +0, −0 | signed-zero rules; MAX/MIN ±0 order |
| 3, 4 | `DEN+`, `DEN−` | min (`0x00000001`), max (`0x007FFFFF`), uniform random fraction | DAZ, DE, gradual underflow |
| 5, 6 | `NORM+`, `NORM−` | uniform exponent in [1, 254], uniform fraction | the IEEE core |
| 7 | `ONE` | random sign, exponent in [120, 134] | the range Hearth actually sees; ties and cancellation are common |
| 8 | `BIG` | random sign, exponent 254, `0x7F7FFFFF` always included | overflow |
| 9, 10 | `INF+`, `INF−` | +∞, −∞ | invalid operations, MAX/MIN |
| 11 | `QNAN` | quiet bit set, uniform payload and sign; payloads `0`, `1`, `0x3FFFFF` always included | NaN selection, payload and sign propagation |
| 12 | `SNAN` | quiet bit clear, nonzero uniform payload and sign; payloads `1`, `0x3FFFFF` always included | quieting, IE, MAXPS returning an SNaN unchanged |

Two-source entries use the full **class-pair grid** (12 × 12 = 144 pairs), so every NaN kind sits in
each operand position against every other class, including NaN against NaN with distinct payloads
(the operand-order test). Draws use a counter-based generator (SplitMix64 keyed by entry hash, class
pair, environment and index), so any single case can be regenerated from its coordinates. Integer
sources of conversions use 12 integer classes: 0, ±1, ±(2^24 − 1), ±2^24, ±(2^24 + 1), 2^31 − 1,
−2^31, small random, large random, random with a tie at 24 bits.

### 3.2 Targeted classes (constructed, not sampled)

| Class | Construction | Entries |
|---|---|---|
| `TIE` | exact RNE ties: a + b with b = half an ulp of a (and odd/even mantissas); for MUL, products of 24-bit significands whose low bits are exactly a half | ADD SUB MUL DIV CVT |
| `OVF` | results within 2 ulps of 2^128, both signs, every RC | ADD SUB MUL DIV CVTDQ2PS |
| `F-TINY` | products and quotients whose exact value lies in [2^−126 − 2^−150, 2^−126), plus the hand vector `0x00800001 × 0x3F7FFFFE` | MUL DIV (with FTZ = 0 and 1) |
| `UFL` | exact and inexact results on the subnormal grid, results that round up to 2^−126 | ADD SUB MUL DIV |
| `CANCEL` | a + (−a), a − a, and sums whose exact value is a nonzero subnormal | ADD SUB |
| `ZEROS` | all four ±0 pairs; ±0 against DEN under DAZ | ADD SUB MUL DIV MAX MIN CMP COMI |
| `CVT-BND` | ±2^31, ±(2^31 − 128), −(2^31 + 256), ±2^24 ± k, ±0.5, ±1.5, ±2.5, (−1, 0), every RC, DAZ on DEN | CVTPS2DQ CVTTPS2DQ CVT(T)SS2SI CVTDQ2PS CVTSI2SS |
| `F-DAZ-SEL` | MAX/MIN with a DEN in either position and DAZ = 1 | MAX MIN |
| `F-DAZ-CVT` | CVT(T)PS2DQ of DEN± under RU/RD with DAZ = 0 and 1 | CVTPS2DQ CVTTPS2DQ CVT(T)SS2SI |
| `F-FTZ-EXACT` | exact tiny results (e.g. `2^−126 × 0.5`) with FTZ = 1 | MUL DIV ADD |
| `F-FLAGPRI` | coexisting conditions: a NaN in one source and a DEN in the other; an SNaN with an overflow-producing partner; **DEN / ±0** (model: DE and ZE); **DEN × ∞ under DAZ** and **DEN / DEN under DAZ** (model: invalid after flushing, IE only); **DEN + ∞** (model: DE with an exact ∞ result) (extended 2026-10-16, finding R1-11) | all FP |
| `F-MASKEXC` | SNaN / DEN / overflow-producing values in masked-off lanes, flag-free values in active lanes | all EVEX FP |
| `F-ER` | {er} in each of the 4 modes with DAZ and FTZ set, on DEN and tiny-result classes | 512-bit reg-reg and scalar EVEX forms that allow {er} |
| `F-H2F` | every f16 subnormal under DAZ = 0 and 1 (model: DAZ ignored, no DE); every f16 SNaN (model: quieted, IE) (new, finding R1-11) | VCVTPH2PS |
| `PRED` | every one of the 32 predicates against the class-pair grid (VEX/EVEX: imm 0-31; legacy: 0-7) | CMPPS CMPSS |
| `BCAST` | every memory form with EVEX.b: the {1toN} broadcast of each value class against the class grid in the register operand (new, finding R2-11) | EVEX memory forms |
| `F-MEMFAULT` | every masked load or store iform in scope: the vector placed so that masked-off lanes fall on a `PAGE_NOACCESS` page, for every prefix mask, single-bit masks and alternating masks; required: no fault (SEH in the MSVC driver) and no write to masked-off memory. Hearth relies on this in `_mm512_maskz_loadu_ps(tm, x + n16)`, `_mm256_maskz_loadu_epi16` and `_mm_mask_storeu_ps` (AVX-512) and `_mm256_maskstore_ps` (AVX2); T1's footprint check rests on it (new, finding R2-11) | masked moves, loads, stores |

### 3.3 Environments

`E8` = {default `0x1F80`, RD, RU, RZ, DAZ, FTZ, DAZ+FTZ, RD+FTZ}, all with every exception masked
(the model's scope). Entries whose profile ignores a field still run under it, because "ignores" is
itself a claim to test (VCVTPH2PS must give identical results under DAZ = 0 and 1). **Compares and
(U)COMISS run under all of E8** (v0 ran them under {default, DAZ} only, contradicting this
paragraph; finding R1-12). `{er}` and `{sae}` are separate classes on the forms that allow them.
Each budget row names its environment set explicitly (§5); the two rows that do not use E8 give their
reason there.

### 3.4 Mask patterns

- **ROADMAP's "every mask pattern" (finding R2-20).** It applies to the FP-sensitive iclasses. On
  Zen 5 these have at most 16 lanes (f32 in a zmm; there is no AVX512-FP16), so the requirement is
  met **exhaustively**: all 65,536 masks for 16-lane forms, all 256 for 8-lane and all 16 for
  4-lane forms, each with merge and with zero masking, on four rotations of a fixed heterogeneous
  lane vector (one SNaN, one QNaN, one DEN, one overflow-producing value, one tie, and ordinary
  values), so every masked-off lane is also an exception-suppression test.
- **Integer and data-movement entries with 32 or 64 lanes** (word and byte elements, e.g. VPMADDUBSW
  zmm, VMOVDQU16). ROADMAP's fuzz sentence does not cover them; structured sampling is an extra:
  all-zero, all-one, every single-bit and single-zero mask, alternating patterns, every prefix mask
  `(1 << r) − 1` (Hearth's tail masks, `quant_avx512.c` `tm` and `sm`), and 4,096 random masks. The
  sufficiency argument is lane separability: the table's masked semantics make lane i depend only on
  k[i]; silicon departing from that would show up on some single-bit or prefix mask under the
  uniformity axiom (03 §3.4).
- **Compare into k with a source mask:** the same patterns as the compare's lane count (zeroing
  only).

### 3.5 Integer and data-movement entries

| Entry | Classes | Exhaustive? |
|---|---|---|
| VPMADDUBSW | the full pair domain (u0, u1, s0, s1) ∈ u8² × s8²: 2^32 pair cases; each ymm execution carries 16 pairs | yes: 2^28 ymm executions |
| VPMADDWD | word classes {0, ±1, 0x7FFF, 0x8000, random} pair grid; the all-0x8000 wrap case; random | no (2^64): partition |
| VPDPBUSD | byte classes {0, 1, 0x7F, 0x80, 0xFF, random} × accumulator {0, ±1, 2^31 − 1, −2^31, random}; products summing across ±2^31 (wrap, no saturation) | no: partition |
| VPHADDD | wrap at ±2^31 within and across 128-bit lanes; lane-crossing check | no: partition |
| VPABSB, VPSIGNB | full byte domains (PABSB: 256; PSIGNB: 2^16) | yes |
| packs and narrowing (VPACKSSDW, VPACKSSWB, VPMOVDB) | saturation boundaries ±32,767/±32,768, ±127/±128, the act range [−127, 127], 10,000 random | partly (the act range exhaustively) |
| permutes, shuffles, unpacks, extracts, inserts, broadcasts (MOV/SHUF/PERM classes) | every immediate and index pattern Hearth uses, each on an identity vector (lane i holds i) and 1,000 random vectors | per used immediate |
| bitwise (VPAND, VPANDN, VPXOR, VANDPS, VANDNPS) and blends (VBLENDVPS, masked moves) | per lane exhaustive where a lane's inputs total ≤ 2^16 bits of freedom after fixing the mask; otherwise the mask × {0, all-ones, sign-only, random} grid | partly |
| opmask (KMOV*, compare-into-k, KORTEST) | every 16-bit value for the 16-lane forms | yes |

These entries run under the default environment only: their semantics do not read MXCSR (XED gives
VPDPBUSD, VPMADDUBSW and VPMADDWD no `MXCSR` attribute [M, X2 author 2026-10-16]; the absorber's
`xed_mxcsr_disagree` bucket checks every other entry against the census's attributes).

## 4. The native harness (desktop, MSVC, JIT-free)

**Why not intrinsics.** A C intrinsic does not pin the instruction: the compiler may commute
operands, fold a load into a memory form, pick VEX instead of EVEX, or schedule `vldmxcsr` away from
the instruction. The harness must execute exactly the iform under test.

**Stubs.** One leaf routine per (iform, operand variant: reg/mem, broadcast, {er} mode, immediate),
written as raw bytes:

1. The generator reads the entry's **operand roles** (`operands` field: XED operand name, role,
   kind) and asks XED's encoder (the pinned XED) for the bytes of the instruction under test, placing
   src1 in zmm1 (or zmm17 to force EVEX), src2 in zmm2 (or zmm18), the destination in zmm0 (or
   zmm16), the write mask in k1. It never hard-codes roles (finding R1-4).
2. It decodes the bytes back with XED and asserts that the decoded iform equals the entry key and
   that each decoded operand register is the one the role mapping put there. This tests the table
   key and the operand roles together.
3. The stub is emitted as MASM `db` lines in a `.asm` file assembled by `ml64` (shipped with MSVC),
   so the assembler never chooses an encoding:

```asm
; stub: VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512, merge, no {er}
; rcx -> case { mxcsr, k, src1[64], src2[64], dst_old[64] },  rdx -> out { dst[64], mxcsr }
stub_0042 PROC
    vldmxcsr dword ptr [rcx]           ; environment, flags pre-cleared by the driver
    kmovw    k1, word ptr [rcx+4]
    vmovdqu64 zmm1, zmmword ptr [rcx+64]
    vmovdqu64 zmm2, zmmword ptr [rcx+128]
    vmovdqu64 zmm0, zmmword ptr [rcx+192]
    db 062h, 0F1h, 074h, 049h, 058h, 0C2h   ; the XED-encoded instruction (illustrative bytes)
    vstmxcsr dword ptr [rdx+64]
    vmovdqu64 zmmword ptr [rdx], zmm0
    ret
stub_0042 ENDP
```

   The bytes above are illustrative only; the real bytes come from XED. Stubs use only zmm0-5,
   zmm16-31 and k1-k7, which are volatile in the Windows x64 ABI, and restore MXCSR to `0x1F80`
   before returning.
4. **JIT-free.** All code is assembled and linked ahead of time. The harness never writes to
   executable memory and never calls `VirtualProtect` on code, so it runs under default W^X and under
   the X4 sandbox's job object. (F-MEMFAULT allocates its `PAGE_NOACCESS` data page with
   `VirtualAlloc`; that is data, not code.)

**Driver (C11, MSVC `cl` 19.44.35229, toolset 14.44.35207, SDK 10.0.26100.0, as pinned in
`experiments/x0-census/TOOLCHAINS.md`; the X0 configuration A compiler).** v0 wrote "`cl`
14.44.35207", which is the toolset number, not the compiler version (finding R2-21). The driver maps
`vectors.bin` (sampled mode) or enumerates inputs (exhaustive mode), pins itself to one logical CPU
with `SetThreadAffinityMask`, runs every case, writes `results.bin` or the exhaustive outputs, and
records the fingerprint: CPUID family/model/stepping, the microcode revision from
`HKLM\HARDWARE\DESCRIPTION\System\CentralProcessor\0` ("Update Revision"), OS build, harness, stub and
interpreter hashes. Each vector set runs on two logical CPUs on different CCDs; any difference
between the two (results, or exhaustive stream hashes) is an anomaly (silicon is expected to be
uniform across cores).

**Throughput [G].** A stub costs tens of cycles plus its loads, so on the order of 10^7 executions
per second per thread. The reference interpreter is the bottleneck: the Python one runs on the
order of 10^4-10^5 lane cases per second [G], fine for development and for re-checking samples. The
budget needs a C interpreter generated from the table (exact integer arithmetic with 128-bit
intermediates for products and long division for quotients), validated against the Python reference
on 10^6 random cases before it is used. Time on the desktop is daytime only and never overlaps a
quiet-machine window (DR-023).

## 5. The per-iform vector budget (`budget.v1`, for pre-registration)

**What is frozen (finding R2-11).** The budget is the file `budget.v1.json`, generated by
`semantics.census_absorb.budget_rows` from the table and the census's operand variants
(`python -B -m semantics.census_absorb --census … --insts … --budget -o …`), frozen with the
generator's hash. One row per (iform, operand variant, set, class, environment set) with a count in
**lane cases**; nothing in it is a range or depends on an undefined word. The census changes the
rows (more iforms, more operand variants), never the formulas below.

| Set | Family kind | Count per iform (lane cases) | Environments |
|---|---|---|---|
| V1 | FP two-source (ADD SUB MUL DIV MAX MIN, packed and scalar) | 144 pairs × 1,000 × 8 = **1,152,000** | E8 |
| V1 | FP compare CMPPS/CMPSS (VEX, EVEX) | 144 × 1,000 × 8 × **32 predicates** = 36,864,000 (legacy: 8 predicates) | E8 |
| V1 | (U)COMISS | 144 × 1,000 × 8 = 1,152,000 | E8 |
| V1 | FP unary conversions, VCVTPH2PS | 12 classes × 1,000 × 8 = 96,000 | E8 |
| V1 | integer entries | §3.5 classes × 100,000 | default (no MXCSR input, §3.5) |
| V2 | FP two-source | 10,000 × 8 per class, classes fixed per family: ADD/SUB {TIE, OVF, UFL, CANCEL, ZEROS, F-FTZ-EXACT, F-FLAGPRI}; MUL/DIV {TIE, OVF, F-TINY, UFL, ZEROS, F-FTZ-EXACT, F-FLAGPRI}; MAX/MIN {ZEROS, F-DAZ-SEL, F-FLAGPRI} | E8 |
| V2 | compares | {ZEROS, F-FLAGPRI} × 10,000 × 8 × predicates | E8 |
| V2 | conversions | i32→f32 {CVT-BND}; f32→i32 {CVT-BND, F-DAZ-CVT}; f16→f32 {F-H2F}; each 10,000 × 8 | E8 |
| V2 | integer entries | wrap and saturation boundaries × 10,000 | default |
| V3 | EVEX, ≤ 16 lanes | 2^n masks × {merge, zero} (compare into k: zero only) × 4 rotations × n lanes; 16 lanes: 8,388,608 | default: lane separability of masking does not depend on the environment in the model; the environment's effects are covered by V1/V2 |
| V3 | EVEX, 32/64 lanes | (2 + 2n + 4 + n + 4,096) structured masks × 2 × 4 × n | default |
| V4 | {er} forms (512-bit reg-reg and EVEX scalar ADD SUB MUL DIV, CVTDQ2PS, CVTPS2DQ) | 4 modes × 144 × 100 × 2 = 115,200 (conversions: 4 × 12 × 100 × 2) | {DAZ = FTZ = 0, DAZ = FTZ = 1} (F-ER tests whether {er} leaves DAZ/FTZ in force) |
| BCAST | EVEX memory forms with EVEX.b | 144 × 100 × n | default |
| F-MEMFAULT | masked loads and stores | (n + 1) prefix masks × n, plus single-bit and alternating masks | default |
| V5 | f32→i32 (CVT, CVTT, packed and scalar) | **2^32 × 4 RC × DAZ {0, 1}** = 34,359,738,368 | 4 RC × 2 DAZ |
| V5 | i32→f32 | 2^32 × 4 RC = 17,179,869,184 (DAZ, FTZ do not apply to an integer source; they are still sampled in V1 across E8) | 4 RC |
| V5 | VCVTPH2PS | 2^16 × 8 = 524,288 | E8 |
| V5 | VPMADDUBSW | pair domain 2^32 | default |

**Totals for the v0 table (88 entries) [D: `budget_rows` over `table.ENTRIES`, X2 reviser
2026-10-16]:** V1 237,756,000; V2 46,470,000; V3 114,514,768; V4 595,200; BCAST 460,800;
F-MEMFAULT 546; sampled total **399,797,314** (≈ 4.0 × 10^8) lane cases; V5 **588,413,140,992**
(≈ 5.9 × 10^11). v0's total left V3 out and quoted V2 as a range (finding R2-11).

**Run time [D from G].** At an assumed 20-50 ns per case for the generated C interpreter on 32
threads, predictions for the sampled part take about 0.25-0.6 s and the exhaustive part about
6-15 minutes; native execution is faster than the reference. These replace v0's estimate, which left
out I/O and the two-CCD repeat; the exhaustive part now runs in exhaustive mode (§1), and the real
figures come from the week-1 measurement.

**Power [D: detection probability 1 − (1 − q)^n].** No statistical inference decides the gate; this
table says what the sampled budget can and cannot see (finding R2-16).

| Defect rate q within the sampled set | 1,000 draws (one class cell, one environment) | 8,000 draws (one class cell over E8, if the defect is present in every environment) | 1,152,000 draws (a whole two-source iform's V1, if the defect is spread uniformly) |
|---|---|---|---|
| 3 × 10^−3 | 95.0% | > 99.99% | > 99.99% |
| 10^−4 | 9.5% | 55.1% | > 99.99% |
| 10^−5 | 1.0% | 7.7% | > 99.99% |
| 10^−6 | 0.1% | 0.8% | 68.4% |
| 10^−7 | < 0.1% | < 0.1% | 10.9% |

Mismatches rarer than about 3 × 10^−3 of a class cell in one environment are covered only by the
constructed classes (V2, V4, BCAST, F-MEMFAULT) or by exhaustive enumeration (V5); elsewhere the
uniformity axiom (03 §3.4) carries the claim. The 8.4 million V3 lane cases per 16-lane form add no
value-space power: they use 4 rotations of one fixed vector, and they test masking.

**Second-oracle budget.** Bochs is far slower than silicon [G]. It runs V1 at r = 100, all of V2,
V4 and BCAST, and V3 with the structured patterns plus 1,024 random masks, for **every** iform; no
exhaustive sweeps and no F-MEMFAULT. For the v0 table that is about **7.5 × 10^7** lane cases [D:
74,578,576 from the same rows]. Where Bochs cannot run a class (for example a CPU model lacking a
feature), the entry's `bochs_record` says so and the grade rule of TABLE-SCHEMA §7 applies.

## 6. The second oracle

### 6.1 Bochs: feasibility [M] X2-agent 2026-10-16, read from github.com/bochs-emu/Bochs

- **Alive and current.** `master` last pushed 2026-10-16; latest release tag `REL_3_1_FINAL`
  (2026-08-23).
- **Instruction coverage.** `cpu/decoder/ia_opcodes_evex.def` defines EVEX VPDPBUSD (masked and
  unmasked, `BX_ISA_AVX512_VNNI`), EVEX VCVTPH2PS (masked), EVEX VMAXPS (masked), EVEX VCVTPS2DQ
  (masked), EVEX VPMADDUBSW (`BX_ISA_AVX512_BW`) and VCMPPS into an opmask. `ia_opcodes.def` defines
  the VEX forms, including VCVTPH2PS (`BX_ISA_AVX_F16C`), VPHADDD, VPMADDWD and VEX VPDPBUSD
  (`BX_ISA_AVX_VNNI`).
- **CPU models.** `cpu/cpudb/intel/sapphire_rapids.cc` and `tigerlake.cc` enable `BX_ISA_AVX_F16C`
  and `BX_ISA_AVX512_VNNI`. The AMD models (`cpudb/amd/`) include only an older `ryzen`; there is no
  Zen 4 or Zen 5 model, so Bochs answers as an Intel-modelled CPU.
- **Windows build.** `.conf.win64-vcpp` configures with `--enable-avx --enable-evex` (and
  `--enable-x86-64`), so an MSVC build with AVX-512 is the project's own supported configuration.
  Whether the published Windows binaries are built that way was not checked.
- **FP behaviour relevant to the uncertainty register.** SoftFloat 3e: tininess after rounding and
  FTZ flushing with UE|PE (`s_roundPackToF32.cc`); `f32_max` flushes both sources under DAZ, then
  returns `a` only if `a > b` (`f32_max.cc`); VCVTPH2PS forces DAZ off and suppresses DE
  (`avx/avx_cvt.cc`); default NaN `0xFFC00000` (`specialize.h`). **These are also where this
  table's readings came from** (§6.3).
- **How to run vectors in Bochs (revised, finding R2-17).** Bochs emulates a whole machine; it has
  no user mode. The plan:
  - **Boot assembler.** A boot stub that goes from real mode through protected mode to long mode
    needs flat 16-, 32- and 64-bit code. `ml64`, the only pinned assembler, cannot produce real-mode
    code or a flat binary. Proposed: GNU `as` and `ld`/`objcopy -O binary` from the WSL binutils 2.42
    that X0's `TOOLCHAINS.md` already records as pre-installed [M, X0 tooling track], with `.code16`,
    `.code32` and `.code64` sections. No new download; the version is pinned in the prereg (§2
    Tools) at freeze.
  - **Image.** The boot stub sets CR4.OSXSAVE and XCR0 to enable the x87/SSE/AVX/opmask/ZMM state,
    then reads the vector set **and the table's predictions** from a second disk image (the budget
    above is about 7.5 × 10^7 lane cases [D], far more than fits in a BIOS-loaded boot image), runs
    **the same stub bytes** (position-independent) over each case, **compares in the guest**, and
    writes only the mismatches plus a sha256 over the (input, Bochs output) stream to the output
    device.
  - **Output device.** The Bochs debug port 0xE9 or a serial port captured to a file. Whether the
    port-E9 hack needs a configure or bochsrc option was not checked [uncertainty]; the serial port
    is the fallback.
  - **Effort and throughput.** 3-5 agent-days, medium risk [G], up from v0's 2-4 agent-days because
    of the disk image and the in-guest compare. Throughput is unknown and is measured in week 1 on a
    10^6-case slice; the budget assumes Bochs is 10^3-10^4 times slower than silicon [G].

**What Bochs's agreement is worth.** Bochs is independent of AMD silicon and of this table's code.
It is **not** independent of this table's *reading of the SDM*: where both read the SDM the same way
and Zen 5 does something else, silicon is the only check; where both misread it identically and Zen
5 happens to agree with the misreading, nothing catches it. Bochs also models Intel behaviour, so a
real Intel/AMD difference shows up as "table = silicon ≠ Bochs" (§6.3).

### 6.2 Fallbacks and what they cost in independence

| Oracle | Independent of silicon? | Independent of our SDM reading? | Cost |
|---|---|---|---|
| Bochs (bare-metal image) | yes | partly (open source, own reading), and **not at all** on the readings this table took from Bochs (§6.3) | 3-5 agent-days to build the image |
| Bochs SoftFloat 3e called directly per lane | yes, arithmetic core only | partly | ~1 day; does not test lane wiring, masks, operand order or which NaN is selected per instruction, so it covers only the FP core |
| Intel SDE 10.13.1 (2026-07-28, free under the Intel Simplified Software License; runs Windows binaries, so it runs the native harness unchanged) [M, intel.com page read 2026-10-16] | **only if it emulates rather than executes natively.** The SDE page says SDE skips an instruction "to be emulated" and branches to an emulation routine, and does not state what happens to instructions the host supports. Every instruction in scope is supported natively by the 9950X and by the Zen 4 laptop, so SDE may simply re-run silicon | Intel's own model of Intel parts; closed source | a probe is required before any SDE agreement counts: per-instruction cost under SDE versus native (emulation is orders of magnitude slower [G]), or SDE's own emulation statistics if it reports them. If emulation cannot be shown, SDE agreement counts as zero independent evidence |
| Zen 4 laptop silicon (Ryzen 9 7940HS) | no: AMD silicon, different microarchitecture | n/a | cheap, but daytime-only and shared with a benchmark; it can show a Zen-5-specific deviation, never confirm the reading |

Recommendation: Bochs as planned; SoftFloat-direct as a stopgap for the FP core in week 1 while the
image is built; SDE only after the emulation probe passes, and then reported as "Intel model,
independence: emulated (probe hash …)".

**Fallback as a pre-signed conditional amendment (finding R2-17).** v0 left the fallback as an Owner
question to be answered when needed, which would make it a post-data change. Proposed text for the
Owner to sign *with* the record, so that it is pre-data:

> If, at the end of M0 week 3, the Bochs image does not run the V2 slice of three named entries
> (VADDPS zmm, VMAXPS zmm, VCVTPS2DQ zmm) end to end, the second oracle becomes SoftFloat 3e called
> directly (FP core only) plus Intel SDE if and only if its emulation probe has passed; the grade
> rule then counts only those classes the substitute can run, and every entry's `bochs_record`
> names the substitute. The switch is logged with its date and is not a deviation under §10.

### 6.3 Three-way triage, and which agreement counts

For each disagreeing case the comparator assigns one verdict:

| Table | Silicon | Bochs | Verdict | Action |
|---|---|---|---|---|
| ≠ | = Bochs | | table bug | fix the entry; its content hash changes; rerun every class of the entry |
| ≠ | ≠ Bochs | = table | Zen 5 differs from the shared reading | the table follows silicon (it models the target CPU); entry marked `vendor_deviation`; the load-time self-test vectors include the case |
| = | | ≠ | Bochs differs (bug or Intel/AMD difference) | recorded; the entry cannot reach `validated(partition)` until the difference is explained by a minimal reproducer reported upstream and a reviewed local Bochs patch, or by a documented Intel/AMD difference; no waiver by agents |
| any | rerun differs from run | | nondeterminism | stop; investigate the harness and the machine |
| any | harness defect found | | tooling | fix, log, rerun the affected vector sets |

**Bochs-derived readings (finding R2-13).** Several readings in this table were cross-read against,
or follow, Bochs's SoftFloat 3e: tininess after rounding, FTZ flushing exact tiny results with
UE|PE, MAX/MIN selecting the flushed zero under DAZ, VCVTPH2PS ignoring DAZ without DE. On those, a
Bochs agreement is **not** independent evidence. Every entry and every uncertainty class carries
`table_source ∈ {sdm, sdm+bochs}` (`semantics/table.py`; TABLE-SCHEMA §12); where it includes Bochs,
Bochs agreement counts as **zero** independent evidence for the grade, and the class is validated by
silicon plus the signed SDM review alone. By name: **F-TINY, F-FTZ-EXACT, F-DAZ-SEL, F-H2F**, and
the entries of FP.ADD, FP.SUB, FP.MUL, FP.DIV, FP.MAX, FP.MIN and FP.CVT.f16_f32.

"After fixes, no table/silicon mismatches remain" (ROADMAP §3.3) is judged on a full rerun of every
vector set of every entry in scope against the final table.

### 6.4 Calibration arm: seeded table mutants (new, finding R2-18)

Does the frozen budget actually find table bugs? About 10 seeded **table mutants**, each a copy of
the table with one plausible misreading, run against the silicon results of the frozen budget:
tininess before rounding; MAXPS returning src1 on NaN; NaN not quieted by ADDPS; CMPPS predicate
table shifted by one; the integer indefinite `0x7FFFFFFF`; FTZ not flushing exact tiny results;
DAZ applied to VCVTPH2PS; masked-off lanes raising flags; VPMADDUBSW operands swapped; `{er}`
disabling DAZ. Each must produce at least one mismatch. Target: 100% detected [target, proposed,
secondary, reported with the verdict; no gate effect]. Silicon results are reused, so the arm costs
only comparator time. The mutants are written and sealed before the first native run.

## 7. Review of entries

Each FP entry gets an SDM review before its first fuzz run: a separate agent context with an
adversarial brief reads the SDM pages cited in the entry and lists every behaviour the entry does
not model or models differently, as candidate uncertainty classes. Reviews are logged
**same-family, independent-context** until D0-10 names other model families (docs/m0/README.md).
Owner review time concentrates on the 12 FP families (ROADMAP §3.3 cost note).

## 8. Open items

- The census may add FP iclasses (for example VSQRTSS, which X0's smoke decode already shows
  [M, X0 smoke results, read 2026-10-16], VROUNDSS, VPERMILPS-class moves); each needs a family, an
  SDM review, a `nan_role`, a `table_source` and its rows in `budget.v1` before T1 may accept code
  containing it.
- Measure Bochs throughput and the C interpreter's ns per case in week 1; if the budget does not fit
  the daytime windows, the pre-registration is amended before data (never after).
- Decide whether the Zen 4 laptop runs the vector sets as a secondary fingerprint (not a gate input).

## 9. Build status (x2build track, 2026-10-16)

Status of what §1-§6 specify, as built and measured on 2026-10-16 by the x2build track. Details,
hashes and the open items are in [harness/README.md](harness/README.md) and
[harness/bochs/README.md](harness/bochs/README.md). "[M]" here = measured by that track on the desktop
(Ryzen 9 9950X, microcode revision 0x0B404023 from the registry value "Update Revision", which is 4 bytes
on this machine; Windows 11 26200.9711). One review of the build has run (same family, independent
context; two lenses: harness soundness and proof routes); the revision it led to is folded into this
section, and §9.6 logs it.

### 9.1 Built

- **Stubs (§4).** `harness/stubgen.py` builds every stub from the entry's operand roles through the
  pinned XED encoder and decodes each one back: **491 stubs over all 88 entries, 0 encode or check
  errors** [M]. All **39 `provisional` iform keys decode exactly as written** [M]; the census still
  decides which forms compilers emit. MASM `db` stubs, JIT-free, volatile registers only, MXCSR restored.
  Since the review the decode-back check also verifies the **imm8 of all 288 immediate stubs**, with a
  negative control (a wrong imm8 is reported) [M]; the manifest hash is unchanged.
- **Driver (§4).** `harness/x2fuzz.c`, MSVC 19.44.35229: sampled mode, exhaustive mode (in-process
  compare, mismatches, chunked stream hash independent of thread count), fingerprint (CPUID, microcode,
  OS build, L3 groups, binary and source hashes), CPU pinning, SEH fault capture with a `PAGE_NOACCESS`
  data page (F-MEMFAULT, **load side only**: loads folded into the arithmetic m512 forms; the store half of
  §3.2 needs the memory-window ABI extension proposed in harness/README.md §4 before the census adds masked
  moves or stores). A **collection guard** refuses, without `--collection-authorised`, non-development labels,
  **any record of a budget set (V1-V4, BCAST, F-MEMFAULT) whatever its label**, and silicon sweeps; the
  generator labels budget rows `BUDGET-v1-*` by default. Vectors with a preset sticky MXCSR flag are outside
  the model (§2) outside VALID sets. Measured L3 groups: LPs 0-15 and 16-31, so CPU 4 and CPU 20 are on
  different CCDs [M].
- **Exhaustive mode, corrected after review (blocker R1-1).** The first build compared the whole output block,
  including RAX and the old destination that the table does not model, so **every silicon execution of a V5
  sweep would have been a mismatch** (the review measured 26,368 of 26,368, 0 observable mismatches) and a
  2^32 sweep would have written about 128 GiB of mismatch records. The engine now compares exactly the
  observable bytes it hashes (destination by kind, MXCSR), refuses inputs the interpreter does not model, and
  stops with status `flood` after 10^6 mismatch records. A new self-test step runs **every V5-eligible stub
  (40) on silicon over 4,096 fixed inputs and requires 0 mismatches and the interpreter's stream hash**:
  PASS [M] (development check, not data under the X2 record).
- **Reference interpreter (§4).** `harness/x2ref.c`, exact integer arithmetic. **Validated against the
  Python reference on 1,000,006 random lane cases over all 491 stubs: 0 divergences** [M], the pre-use
  check §4 asks for. Throughput: about 24 ns per lane case in the exhaustive engine (VCVTPS2DQ zmm, 2^28 lane cases in 6.55 s on one thread, stream hash included) and about 0.76 µs per lane case end to end in predict mode with file I/O [M]; at 24 ns the V5 sweeps need about 4 h of one thread for predictions, about 2 h on 2 threads [D] (§5 assumed 6-15 min on 32 threads).
- **Generator (§3, §5).** `harness/gen_vectors.py`: the value classes, targeted classes, E8, V3 masks,
  flag isolation, V4, BCAST, F-MEMFAULT, counter-based SplitMix64 per lane case. Its plan equals
  `budget_rows` on **420 of 428 sampled rows**; the 8 others are the i32→f32 rows (open item 1 below)
  [M]. Throughput: about 61 µs per execution on a V1 slice [M]; the full sampled budget is about 1.15 × 10^8 executions, about 2 h single-threaded (a lower bound) and a 36.7 GB vectors file [D].
- **Comparator (§1, §6.3).** `harness/compare.py`: per-cell lane and per-execution flag mismatches,
  C-vs-Python divergence, two-run nondeterminism, harness anomalies, the three-way verdict;
  single-active-lane duplicates are tallied apart (§2: interpreted after F-MASKEXC). Since the review the
  Bochs output is compared with the table on **every** record, so the "Bochs differs" row of §6.3
  (table = silicon ≠ Bochs) is produced (the first build consulted Bochs only where silicon already
  disagreed and could never produce it), a non-OK Bochs status is a Bochs anomaly, and every results input
  must name the vectors file's and the manifest's sha256 and carry each vector record's index (provenance).
- **Calibration arm (§6.4), built after review.** `harness/mutants/`: 24 seeded table mutants (the 10 of
  §6.4 and 14 harness-path ones: zeroing, upper bits, broadcast, k-destination upper bits, GPR extension,
  scalar upper lanes, flag-only) as anchored one-line edits of a copy of `semantics/`, and a runner that
  predicts with the mutated table and compares against unchanged silicon results. Sealed by the sha256 of
  `mutants.py` (harness/README.md §9), which the X2 record must name before the first native run. Calibrated
  on development data (the review's cross-section): harness/README.md §9.

### 9.2 Not built or not run

- No `budget.v1` vector was generated for silicon, and no class cell, V5 sweep or Bochs budget ran
  (collection rule).
- The Bochs production image (vector loader, in-guest compare, stream hash) is not built (§9.4).
- Intel SDE was not downloaded: its download requires a licence click-through. Listed for the Owner.
- The F-MEMFAULT store side (memory-window ABI, harness/README.md §4) is not built; no table entry needs it yet.
- The mutant arm has not run on budget silicon results (none exist); its 100% target is for the frozen budget.

### 9.3 Development smoke run on the selftest.py hand vectors [M] (not data under the X2 record)

299 hand vectors extracted from `semantics/selftest.py` (not retyped) in 780 lane-0 executions, plus 20
vector-level cases (masks, broadcast, `{er}`, scalar upper lanes, full-width converts, RFLAGS), run on
CPU 4 and CPU 20: 0 lane mismatches, 0 nondeterminism, 0 C-vs-Python divergences, 0 harness anomalies,
**3 execution flag mismatches, all one hand vector: selftest B6, `0x00000001 / +0`. The 9950X sets ZE
alone, while the table and the hand expectation say DE|ZE** (VDIVSS EVEX, VDIVSS VEX and DIVSS legacy
alike). Bochs 3.1 also sets ZE alone (§9.4). This touches the F-FLAGPRI reading of TABLE-SCHEMA §4 rule 7.
It is pre-freeze information about an uncertainty class, so the X2 record should disclose it before
freeze. Whether the reading changes is the table owner's decision, not this track's.

The revised build reproduced the smoke exactly (same vectors, same counts). The review's development
cross-section (4,504 random executions over all 491 stubs, CPU 6 and CPU 22) shows the same flag-only
disagreement **off the hand vector** and nowhere else [M review; re-compared by the revised comparator,
harness/README.md §7]: VDIVSS (VEX) `0x004C24E3 / +0` under RZ, DIVSS `0x8078165D / −0` under RZ, and DIVSS
`0x80717657 / +0` under FTZ: silicon ZE only, table DE|ZE. So the reading "DEN / ±0 raises DE and ZE" fails
across environments and signs. These three cases belong in the record's pre-freeze disclosure with B6
(provisional, pending the record's review; the reading is the table owner's decision).

### 9.4 Second oracle: Bochs, measured (answers to §6.1)

- Bochs 3.1 built from the release's own MSVC source package (GitHub asset, SHA-256 matching the
  published digest; LGPL-2.1, no click-through). Its configuration has `BX_SUPPORT_AVX 1` and
  `BX_SUPPORT_EVEX 1`, so the release's Windows configuration includes AVX-512 [M]. The published
  installer was not run.
- 33 CPU models, with `sapphire_rapids`, `arrow_lake` and `wildcat_lake` among the AVX-512 ones; no Zen 4
  or Zen 5 model [M].
- A bare-metal probe (`harness/bochs/boot.S`: long mode, XCR0 = 0xE7, output on port 0xE9) ran 12 cases
  in about 0.44 s wall: every in-scope instruction tried executes, and Bochs equals the table on 11 of 12
  [M]. The exception is B6 again: ZE alone, as on the 9950X. **The port-0xE9 hack is a bochsrc option
  (`port_e9_hack: enabled=1`); no configure flag is needed** [M].
- Throughput [M]: about **107 ns per (VADDPS zmm + DEC + JNZ)** iteration on one host thread with the
  debugger compiled in, i.e. about 9.4 × 10^6 VADDPS zmm (1.5 × 10^8 f32 lane operations) per second.
  The raw arithmetic is not the bottleneck for the 7.5 × 10^7-lane-case Bochs budget [D]; vector I/O and
  the in-guest compare are.
- Guest pitfall [M]: without masking the 8259 and an IDT, long runs triple-fault at a fixed emulated time
  (an IRQ0 arriving at vector 8).

### 9.5 Open items for the record (pre-freeze; not decided here)

1. §3.1 says "12 integer classes" and lists 10; the i32→f32 rows (12 × 1,000 × 8 and 4 × 12 × 100 × 2)
   cannot be met: 113,600 lane cases short over 8 rows.
2. F-DAZ-CVT asks for RU/RD with DAZ = 0 and 1, but E8 has no RU+DAZ or RD+DAZ; only V5 reaches them.
3. DIV ties exist only on the subnormal grid; the TIE class for DIV uses those.
4. F-TINY's band [2^−126 − 2^−150, 2^−126) is unreachable for DIV (a quotient of 24-bit significands
   cannot lie in it); the tininess distinction for DIV exists only under directed rounding.
5. §3.2 lists OVF for CVTDQ2PS; no int32 overflows binary32 (the rows already omit it).
6. F-MEMFAULT's text names single-bit and alternating masks; its row counts prefix masks only. Since the
   review the generator also runs every prefix mask with zero masking as uncounted duplicates; proposed:
   count them (2 × (n + 1) × n). F-MEMFAULT is load-side only until the memory-window ABI exists (§9.1).
7. F-MASKEXC has no row of its own; V3's heterogeneous vector puts SNaN, QNaN, DEN and
   overflow-producing values in masked-off lanes under every mask.
8. The B6 observation of §9.3, now with the review's three further cases (RZ, FTZ, −0).
9. (Review R1-8) No budget row runs masked broadcast (`merge_bcast`, `zero_bcast` exist and are kept);
   proposed: a BCAST row "masked {1toN} × 144 × 10 × {merge, zero}" per EVEX memory form with EVEX.b (the
   generator implements it). `{er}`/`{sae}` stubs exist unmasked only: add masked variants and V4 rows, or
   state that masked embedded rounding is out of scope.
10. (Review R1-10) The mutant list of §6.4 is built and sealed by the sha256 of `harness/mutants/mutants.py`
    (`a74d5041…`, harness/README.md §9); the record should name it before the first native run and keep
    the target "every §6.4 mutant detected on the frozen budget's silicon results".
11. (Review R1-3) The record's collection procedure should state that collection runs pass
    `--collection-authorised` and that budget vectors carry `BUDGET-v1-*` labels and budget set ids.

### 9.6 Review of the build (log)

| Date | Reviewer | Lens | Family | Findings | Outcome |
|---|---|---|---|---|---|
| 2026-10-16 | reviewer 1 | harness soundness | Claude, **same family, independent context** | 11 (1 blocker, 3 major, 7 minor) | all accepted; 10 fixed and re-run, 1 information for the record (B6 cases); details in harness/README.md §11 |
| 2026-10-16 | reviewer 2 | proof routes (RULES.md §8) | Claude, same family, independent context | 10 (4 major, 6 minor) | all accepted; routes corrected and re-run; details in proofs/README.md §9 |

The blocker (exhaustive mode compared unmodelled bytes, so a V5 sweep on silicon would have reported every
execution as a mismatch) was found before any V5 sweep ran. Same-family review is weaker than ROADMAP's
different-family requirement (docs/m0/README.md); that gap stays open until D0-10.
