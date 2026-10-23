# X2: the x86 semantics table, entry schema v0

Status: DRAFT, M0 week 0, revised 2026-10-16 after two same-family reviews (§15); **census run 1 absorbed and
the B6 reading corrected on 2026-10-23 (x2freeze track; §9.1, §4 rule 7)**. Track X2
([ROADMAP §3.3](../../docs/ROADMAP.md#33-x2-t1-spike-on-transliterated-hearth-intrinsics-weeks-05-verdict-in-week-6),
DR-008, DR-010, [03-trust §6.7](../../docs/architecture/03-trust.md)). This file defines what one
table entry is, how it carries its evidence, and how T1 and T2 consume it. The executable index
of v0 entries is [semantics/table.py](semantics/table.py); the reference semantics are in
[semantics/](semantics/).

Evidence tags follow [docs/m0/README.md](../../docs/m0/README.md). "[M] X2-agent 2026-10-16
laptop" means: measured by this track's agent (the author, or the reviser where marked "rev") on
2026-10-16 on the shared laptop (AMD Ryzen 9 7940HS, Zen 4, Windows 11 Pro 10.0.26200, Python
3.12.10), not on the 9950X.

**Files of this track**

| File | What |
|---|---|
| TABLE-SCHEMA.md | This file: entry format, operand model, FP-environment layer, NaN model, evidence, hashing, T1/T2 consumption, intrinsic map, census absorption, review log |
| [semantics/](semantics/) | Bit-exact Python reference semantics with an explicit MXCSR, self-tests, SMT encoding prototype, census absorber and budget generator |
| [FUZZ-DESIGN.md](FUZZ-DESIGN.md) | The 9950X fuzz harness, the second oracle, the per-iform vector budget |
| [MUTANTS.md](MUTANTS.md) | The `numerics_v1` mutant pool and the G / G+C / T1+T2 kill-rate protocol |
| [RULES.md](RULES.md) | The T1 exact-rewrite rule list, the domain predicates, T2 range obligations, loop rules |
| [../../docs/m0/prereg/X2-checker.md](../../docs/m0/prereg/X2-checker.md) | DRAFT pre-registration |

---

## 1. What the table is for

The table is Mithril's single source of truth for what an x86 instruction does to bits
[G02 Implications 1-3]. It is hand-written from the Intel SDM, never derived mechanically from
Intel's intrinsics XML (licence: G02 open question 2, an Owner question, §13). Every consumer is
generated from it:

| Consumer | Uses | Status |
|---|---|---|
| T1 matcher | per-entry FP node label (family, operand roles, env profile) and the NaN layer for the NaN-order side condition | v0 spike (X2) |
| T2 | integer and bit-vector terms (QF_BV) for ranges, saturation, masks, bitwise identities | v0 spike (X2) |
| Fuzz harness | the reference interpreter that predicts silicon, per case class; the operand roles that place values in registers | design: FUZZ-DESIGN.md |
| Load-time self-test | the stored case-class vectors per dispatched iclass (03 §6.7) | M5 |
| Exo-style `instr` bodies | the entry semantics, so no hand-written body can disagree | M2 |
| Lean export | entry semantics as definitions | by-trigger, D-08 |

In this spike the reference interpreter is Python ([semantics/](semantics/)), exact by construction
(integer and `Fraction` arithmetic, no host floating point in any result bit). The fuzz harness
needs a fast C interpreter generated from the same entries (FUZZ-DESIGN.md §4); the Python one is
its oracle during development.

## 2. The key

**Key = (XED iclass, XED iform).** XED is Apache-2.0 [G02 §6]. Pinned for v0: XED `main` at commit
`0bcb6237345c5066726dcc08b3d87928df3b5b26` (2026-08-24; latest tag `v2026.08.23`), read through the
GitHub API [M] X2-agent 2026-10-16. X0 pins the same release, v2026.08.23 (0bcb6237…), in
`experiments/x0-census/TOOLCHAINS.md` [M, X0 tooling track]; every key is re-checked when the census
lands (§9).

Facts about the key that the schema must respect (read from the pinned XED datafiles [M]):

1. **EVEX iform strings are in the datafiles; VEX and legacy ones are not.** XED derives the VEX and
   legacy names when it builds its tables [inference]. Each key therefore carries
   `iform_status ∈ {xed-datafile, xed-decode, provisional}`: *xed-datafile* = read from the
   datafiles (41 entries, all EVEX); *xed-decode* = observed in a real XED decode, namely X0's smoke
   objects decoded with XED v2026.08.23 (`experiments/x0-census/scripts/smoke/results/*/functions.json`,
   read by the reviser on 2026-10-16) (8 entries: `VADDPS_XMMdq_XMMdq_XMMdq`,
   `VADDSS_XMMdq_XMMdq_XMMd`, `VADDSS_XMMdq_XMMdq_MEMd`, `VMULSS_XMMdq_XMMdq_XMMd`,
   `VMULSS_XMMdq_XMMdq_MEMd`, `VUCOMISS_XMMdq_XMMd`, and the EVEX memory forms
   `VADDPS_ZMMf32_MASKmskw_ZMMf32_MEMf32_AVX512`, `VMULPS_ZMMf32_MASKmskw_ZMMf32_MEMf32_AVX512`);
   *provisional* = placeholders (39 entries), replaced by the exact strings X0's census decodes.
   The smoke decode already caught one wrong placeholder: v0's `VUCOMISS_XMMss_XMMss` is
   `VUCOMISS_XMMdq_XMMd` [M]. The VEX `VCVTSI2SS`, `VCVTTSS2SI` and `VCOMISS` placeholders were
   reshaped to the operand widths of their datafile records (`…_XMMdq_XMMdq_GPR32d`,
   `…_GPR32d_XMMd`, `VCOMISS_XMMd_XMMd`) [inference from XED's naming convention].
   `census_absorb.py` lists every provisional key the census never produced. **Since 2026-10-23** every key
   X0 census run 1 decoded is `xed-decode` (the table now has 41 `xed-datafile`, 62 `xed-decode`, 11
   `provisional`; all 664 stubs decode to their entry's key, the 11 provisional ones included) [M].
2. **{er} and {sae} variants share an iform.** In `avx512-foundation-isa.xed.txt`, e.g.
   `VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512` appears twice: once for the plain form and once
   for the EVEX.b rounding form (`TXT=ROUNDC` on REG0). The iform therefore does not determine the
   rounding source; the census's operand variant (§9) does.
3. **Memory forms are separate iforms** (`..._MEMf32_AVX512`), and broadcast `{1toN}` is an
   operand property of the memory form (`MEM0:…:TXT=BCASTSTR`), not a separate iform.
4. **XED attributes give an FP-sensitivity cross-check.** FP arithmetic, conversion, compare and
   min/max EVEX forms carry the `MXCSR` attribute; VPDPBUSD, VPMADDUBSW and VPMADDWD do not [M].
   `census_absorb.py` reports every disagreement between the table's family and XED's attribute,
   as X0 §4.4 requires.

**Family.** Every entry belongs to an operation family, which is X0's FP-semantic operation class
(X0 §4.4: drop the `V` prefix, merge packed and scalar of one element type): `FP.ADD.f32` holds
ADDSS, VADDSS, VADDPS (VEX and EVEX, all widths). One family shares one lane function and one NaN
rule; entries add the operand shape, encoding and masking. Integer families are `INT.*`; data
movement is `MOV.*`/`SHUF.*`/`PERM.*`/`LOGIC.*`.

## 3. Operand model

An entry describes one instruction form as a pure function from source operands and an
environment to destination values plus flags. **Every field below except `evidence` is in the hashed
declarative part** (§7), and since the 2026-10-16 revision every field is implemented in
`table.py` (v0 stored neither `operands`, `upper`, `scalar` nor `elem`; findings R1-4, R2-9):

```text
entry := {
  key        { iclass, iform, iform_status: xed-datafile | xed-decode | provisional }
  family     FP.ADD.f32 | FP.MAX.f32 | INT.MADDUBS.u8s8 | MOV.PERM.d | ...
  encoding   legacy | vex | evex
  vl         128 | 256 | 512                   -- operation vector length in bits
  lanes      n                                 -- element count (1 for scalar forms)
  elem       { src: f32 | f16 | i32 | u8,s8 | i16 ..., dst: ... }
  operands   [ { xed: REG0 | REG1 | ... | MEM0 | IMM0 | implicit,
                 role: dst | dst_src1 | acc | src1 | src2 | src | mask | imm,
                 kind: xmm | ymm | zmm | k | gpr32 | mem | imm8 | rflags,
                 access: r | w | rw, width?, broadcast?: 1toN } ]
  operands_status  xed-datafile | pattern       -- XED operand order read from the datafiles, or by pattern
  masking    none | merge,zero | zero(k-dest)
  upper      zero_to_vlmax (vex/evex) | preserve (legacy) | zero_extend_64 (gpr32) | n/a (k, rflags)
  scalar     none | { lane0_from: op(src1[0], src2[0]), upper_lanes_from: src1 | dst }
  fp_env     null (not FP-sensitive) | profile (§4)
  nan_rule   NAN.* id (§5) | none | n/a
  nan_role   { <role>: transparent | erasing | observer }   -- RULES.md §2; unlisted = observer
  lane_fn    reference-semantics function name (semantics/fp_ops.py, int_ops.py)
  sem        { builder, fn?, trunc?, src_eb?, dst_eb?, signalling?, saturate? }  -- the wiring
  table_source  sdm | sdm+bochs                  -- where the reading came from (§7, §12)
  precond    [ "mxcsr.exception_masks == all", ... ]
  observables [ dst.zmm_full_width | dst.opmask | dst.gpr64(zero-extended) | rflags(...), mxcsr.flags(per execution) ]
  uncertain  [ fuzz-class ids whose outcome the SDM reading does not settle ]
  sdm        [ page cites ]
  evidence   { ... }                           -- §7; excluded from the content hash
}
```

**Operand roles are data.** The `xed` names and their order were read from the `OPERANDS:` lines of
the pinned XED datafiles for 25 (iclass, encoding) records, among them EVEX VADDPS, VMAXSS, VCMPPS,
VCVTPS2DQ, VCVTPH2PS, VPDPBUSD, VPMADDUBSW; VEX VADDPS, VMAXSS, VCMPPS, VCVTPS2DQ, VCVTPH2PS,
VPHADDD, VPMADDWD, VUCOMISS, VCOMISS, VCVTSI2SS, VCVTTSS2SI; legacy ADDSS, MAXSS, (U)COMISS,
CVT(T)SS2SI, CVTSI2SS [M, X2 reviser, 2026-10-16], which covers 44 of the 88 entries; the other
entries follow the same encoding pattern (`operands_status: pattern`) and are checked by the stub generator's decode step
(FUZZ-DESIGN §4). The pattern is: EVEX REG0 = destination, REG1 = write mask, **REG2 = src1**,
REG3 or MEM0 = src2; VEX REG0 = destination, **REG1 = src1**, REG2 or MEM0 = src2; legacy
**REG0 = destination and src1** (read-write), REG1 or MEM0 = src2; VPDPBUSD REG0 = the read-write
accumulator. The NaN model is defined by operand position (`NAN.ARITH2` picks src1, `NAN.SELECT2`
returns src2), so **the lifter and the stub generator read roles only from these fields**, never from
a mapping of their own; self-test I6 asserts that every FP entry's roles agree with its NaN rule and
its encoding's first-source convention.

Semantics of each operand feature, as implemented in [semantics/vec.py](semantics/vec.py) and the
builders of [semantics/table.py](semantics/table.py):

- **Lanes.** A register value is a `vl`-bit integer, lane 0 least significant. Element views are
  re-derived per entry (bytes for VPMADDUBSW, dwords for VPDPBUSD).
- **Write masks `{k}{z}` (EVEX).** Active lane: result written, its exceptions recorded. Inactive
  lane: merge keeps the old destination lane, `{z}` writes zero; **an inactive lane raises no
  exception** [SDM Vol 1 §15.6, reading; class F-MASKEXC]. `k0` as a write mask means "unmasked".
  Compare-into-mask (VCMPPS k1{k2}) is zeroing by definition: bit i = k2[i] ∧ pred(lane i).
  Integer EVEX entries apply the mask with their destination element width.
- **Upper bits.** VEX and EVEX writes zero the destination above `vl` up to 512 bits; legacy SSE
  preserves it (`table.write_full`). This matters to T1 when a ymm result is later read as a zmm.
- **Scalar forms (SS).** Lane 0 = op(src1[0], src2[0]); lanes 1-3 come from src1; EVEX masking
  applies to lane 0 only. Legacy ADDSS has src1 = dst. **Scalar converts** (finding R1-6): legacy
  CVTSI2SS keeps lanes 1-3 and bits 511:128 of the destination; VCVTSI2SS takes lanes 1-3 from src1
  and zeroes bits 511:128; CVT(T)SS2SI with a 32-bit destination zero-extends into bits 63:32 of the
  GPR. Self-test E8 checks each full width.
- **Broadcast.** `{1toN}` replicates one memory element to every lane before the operation.
- **Embedded rounding `{er}`** (512-bit register forms and scalar forms only) overrides MXCSR.RC and
  implies `{sae}`; **`{sae}`** suppresses flag recording. Neither changes DAZ or FTZ [reading; class
  F-ER in FUZZ-DESIGN.md].
- **Memory operands.** The value semantics treat a memory source as a vector value. Alignment
  requirements (#GP for misaligned VMOVAPS or legacy SSE memory operands), fault suppression for
  masked-off lanes, and the address itself are **footprint facts**, which T1's footprint check
  (03 §6.3) and T2 consume; fault suppression is tested on silicon by class F-MEMFAULT.
- **Immediates.** The predicate of VCMPPS, the shuffle control of VPSHUFD and so on are entry
  parameters. Every immediate value that appears in a census is its own fuzz case class (Hearth uses
  CMPPS predicates 3 `UNORD_Q` and 7 `ORD_Q`, and PSHUFD controls `0x4E` and `0xB1`).
- **Non-vector destinations.** (U)COMISS writes RFLAGS (ZF, PF, CF; OF = SF = AF = 0); CVT(T)SS2SI
  writes a GPR. Both are observables.

## 4. The explicit FP-environment layer

MXCSR is ambient state, so it is an explicit input to every FP entry
([semantics/fpenv.py](semantics/fpenv.py)):

```text
Env := { rc: RNE | RD | RU | RZ      -- MXCSR[14:13], or EVEX {er}
         daz: bool                   -- MXCSR[6]
         ftz: bool                   -- MXCSR[15]
         sae: bool                   -- {sae}, implied by {er}
         masks: all                  -- MXCSR[12:7]; any clear mask is outside the model (#XM) }
Out := { value bits, flags ⊆ {IE, DE, ZE, OE, UE, PE} }   -- MXCSR[5:0], sticky OR unless sae
```

Each FP entry declares an **environment profile**: which parts it reads and writes.

| Profile | rc | DAZ | FTZ | DE | Flags | Entries |
|---|---|---|---|---|---|---|
| `ENV_ARITH` | MXCSR or {er} | honoured | honoured | reported | IE DE ZE OE UE PE | ADD, SUB, MUL, DIV (PS/SS) |
| `ENV_SELECT` | unused | honoured, selected value is the flushed zero (UNCERTAIN F-DAZ-SEL) | unused | reported | IE DE | MAX, MIN |
| `ENV_CMP` | unused | honoured | unused | reported | IE DE | CMPPS/SS, (U)COMISS |
| `ENV_CVT_I2F` | MXCSR or {er} | n/a | n/a (never tiny) | never | PE | CVTDQ2PS, CVTSI2SS |
| `ENV_CVT_F2I` | MXCSR or {er} | honoured (UNCERTAIN F-DAZ-CVT) | n/a | never | IE PE | CVTPS2DQ, CVTSS2SI |
| `ENV_CVTT_F2I` | fixed RZ | as above | n/a | never | IE PE | CVTTPS2DQ, CVTTSS2SI |
| `ENV_CVT_H2F` | unused (exact) | **ignored** (SDM VCVTPH2PS; UNCERTAIN F-H2F) | unused | never (UNCERTAIN F-H2F) | IE | VCVTPH2PS |

Rules the layer implements ([semantics/rounding.py](semantics/rounding.py)):

1. **Rounding.** The exact result (a rational) is rounded by `rc`; ties to even under RNE.
2. **Overflow.** If the result rounded with unbounded exponent exceeds the largest finite value:
   RNE gives ±∞, RZ gives ±MAX, RD gives +MAX or −∞, RU gives +∞ or −MAX; flags OE|PE.
3. **Tininess after rounding.** A result is tiny iff its value rounded to 24 significant bits with
   unbounded exponent is nonzero and below 2^−126 (SDM Vol 1 §4.9.1.5). Bochs's SoftFloat 3e
   implements exactly this test (`isTiny = (exp < -1) || (sig + roundIncrement < 0x80000000)` in
   `s_roundPackToF32.cc`, read [M] X2-agent 2026-10-16). The difference from tininess before
   rounding is visible only for products and quotients whose exact value lies in a band just below
   2^−126; the hand-derived vector `(2^−126(1+2^−23)) × (1−2^−23)` (self-test A13) separates the two
   readings. Fuzz class F-TINY decides it on silicon.
4. **FTZ.** With FTZ = 1 and a tiny result, the result is a zero with the sign of the true result
   and flags UE|PE, even when the tiny result was exact (Bochs agrees; UNCERTAIN on silicon, class
   F-FTZ-EXACT).
5. **Gradual underflow (FTZ = 0).** The value is rounded to the 2^−149 grid by `rc`; UE is raised
   only when that rounding is inexact (masked underflow), with PE.
6. **DAZ.** A denormal *source* becomes a zero of the same sign before any computation, and DE is
   not raised (SDM Vol 1 §10.2.3.4). Without DAZ a denormal source raises DE (for entries whose
   profile reports DE).
7. **Flag priority.** A NaN source suppresses DE: SNaN invalid, then QNaN operand, then other
   invalid, then denormal, then overflow/underflow, then inexact (SDM Vol 1 §4.9.2, reading;
   UNCERTAIN class F-FLAGPRI). Divide-by-zero sits at the level of "other invalid", above denormal.
   **Corrected 2026-10-23 (B6): a denormal divided by ±0 gives ZE alone** (v0 said DE|ZE; the 9950X set ZE
   alone on four development vectors, three encodings, RZ, FTZ and −0, both CCDs, and Bochs 3.1 agreed
   [M, harness/README.md §7, §10]; the X2 record discloses it, §2.1). The other coexisting readings stand:
   DEN + ∞ gives DE; under DAZ, DEN × ∞ and DEN / DEN are invalid after flushing and give IE only (self-test
   B6, which checks the four silicon vectors too). F-FLAGPRI still tests all of them (finding R1-11).
8. **Instructions that override MXCSR** (VDPBF16PS, VCVTNEPS2BF16: forced RNE, DAZ and FTZ; MXCSR
   neither read nor written [G02 §6]) and approximations (RCP14, RSQRT14) are **special entries**:
   out of v0, admitted one at a time with their own fuzz record, and kept out of kernels whose
   meaning is defined by IEEE operations [G02 Implications 6].

**The default environment as a precondition (finding R2-14).** Mithril's runtime sets the
default MXCSR 0x1F80 on entry (ARCHITECTURE §6.3), and 03 §3.4 lists it as a runtime-checked
trust-base entry. **Hearth at b5d3f14 does not**: there is no MXCSR write or check in `engine/src`
[M, grep by reviewer 2 and by the reviser, 2026-10-16]; Hearth's own council review of 2026-10-04
found that round-toward-zero breaks cross-ISA identity; the guard is D0-5b, unsigned. So X2
certifies C Hearth b5d3f14 under the **declared precondition** "MXCSR = 0x1F80 at entry"
(RULES.md §4.0 DOM-ENV), **provisional, pending D0-5b**; it becomes the runtime-checked entry of
03 §3.4 once the guard lands. v0 called it runtime-checked, which overstated what a certificate for
the pinned C code rests on.

**Grades are per environment profile instance.** An entry can be `validated` for `env = default`
while its non-default cases (DAZ = 1, FTZ = 1, directed RC) are still `tested`. An uncertainty that
only touches non-default environments (F-DAZ-SEL, F-DAZ-CVT, F-FTZ-EXACT, the DAZ part of F-H2F)
therefore cannot block a default-MXCSR certificate, but it must be resolved before any entry is
graded for that environment. This is a proposed refinement of 03 §6.7 (§14).

## 5. The NaN model: bit-vectors over FPA

SMT-LIB FPA has one NaN per sort and deliberately no NaN-to-bits function [G02 §1]. x86 results,
however, carry NaN payloads, signs and quiet bits that depend on operand order. The table
therefore puts **a bit-vector NaN layer around an FPA core**:

- lanes are `(_ BitVec 32)`; FPA values come from bit reinterpretation (`(_ to_fp 8 24)` on a
  bit-vector);
- the FPA result goes back to bits only on the non-NaN path, where the map is injective, so the
  solver's internal NaN never leaks;
- NaN selection, quieting and the default NaN are `ite` terms over the input bits.

Named NaN rules (each entry cites one by id; `table.NAN_RULES` lists the operand roles each needs):

| Rule | Behaviour | Applies to |
|---|---|---|
| `NAN.ARITH2` | src1 NaN → quiet(src1); else src2 NaN → quiet(src2); else invalid (∞−∞, 0·∞, 0/0, ∞/∞) → QNaN indefinite `0xFFC00000`. IE iff an SNaN source or invalid. quiet(x) = x \| `0x00400000`: sign and payload kept | ADD, SUB, MUL, DIV (PS/SS) |
| `NAN.SELECT2` | any NaN source, or both sources zero of either sign → **src2 unchanged** (an SNaN is not quieted); else the larger (smaller) value. IE for any NaN (QNaN included: signalling comparison) | MAX, MIN (PS/SS) |
| `NAN.CMP` | NaN → relation "unordered"; IE on an SNaN for quiet predicates, on any NaN for signalling ones; 32 predicates (`fp_ops.CMP_PREDICATES`) | CMPPS/SS, (U)COMISS |
| `NAN.CVT_F2I` | NaN, ±∞, or a rounded value outside [−2^31, 2^31−1] → integer indefinite `0x80000000` with IE (no PE). −2^31 itself converts exactly | CVT(T)PS2DQ, CVT(T)SS2SI |
| `NAN.CVT_H2F` | f16 NaN → sign \| `0x7F800000` \| frac≪13 \| quiet bit; IE iff the f16 was an SNaN | VCVTPH2PS |

**What "src1" means.** It is the operand whose `role` is `src1` (or `dst_src1`) in the entry's
`operands` list: XED REG2 (`xmm2`/vvvv) in EVEX `VADDPS zmm1{k1}, zmm2, zmm3`, REG1 in VEX
`VADDPS xmm1, xmm2, xmm3`, but REG0, the destination, in legacy `ADDPS xmm1, xmm2`. For
`_mm_add_ps(a, b)` it is `a` only if the compiler kept the order, which C compilers need not do for
commutative FP operations. This is why Hearth canonicalises NaN on store (NUMERICS §3) and why T1's
commutation rules carry the NaN-order side condition (RULES.md §2). For MAX/MIN the order is
semantic for every NaN and every pair of zeros: `max(+0, −0)` returns −0 and `max(−0, +0)` returns
+0 (self-test B1).

The SMT text the generator emits for a VADDPS lane under the default environment (prototype:
[semantics/smt_encoding.py](semantics/smt_encoding.py)):

```smt2
(define-fun nan32 ((x (_ BitVec 32))) Bool
  (and (= ((_ extract 30 23) x) #xFF) (not (= ((_ extract 22 0) x) #b00000000000000000000000))))
(define-fun quiet32 ((x (_ BitVec 32))) (_ BitVec 32) (bvor x #x00400000))
(define-fun x86.addps.lane ((a (_ BitVec 32)) (b (_ BitVec 32))) (_ BitVec 32)
  (let ((r (fp.add RNE ((_ to_fp 8 24) a) ((_ to_fp 8 24) b))))
    (ite (nan32 a) (quiet32 a)
    (ite (nan32 b) (quiet32 b)
    (ite (fp.isNaN r) #xFFC00000
         (fp.to_ieee_bv r))))))       ; non-NaN path only; Z3: fpToIEEEBV
(define-fun x86.maxps.lane ((a (_ BitVec 32)) (b (_ BitVec 32))) (_ BitVec 32)
  (ite (or (nan32 a) (nan32 b)
           (and (= ((_ extract 30 0) a) #b0000000000000000000000000000000)
                (= ((_ extract 30 0) b) #b0000000000000000000000000000000)))
       b
       (ite (fp.gt ((_ to_fp 8 24) a) ((_ to_fp 8 24) b)) a b)))
```

`fp.to_ieee_bv` is a Z3 extension, not standard SMT-LIB. A portable encoding declares a fresh
bit-vector `rb` with `(= ((_ to_fp 8 24) rb) r)` under `(not (fp.isNaN r))`, which pins `rb`
uniquely because `to_fp` is injective on non-NaN values (±0 are distinct in FPA). FTZ is encoded by
rounding the same operation in `(_ FloatingPoint 10 24)`, where nothing is subnormal, and flushing
when that result is nonzero and below 2^−126 (rule 3 of §4).

Cross-check of the two implementations [M] X2 reviser 2026-10-16 laptop, `python -B -m
semantics.smt_encoding`, z3-solver 5.3.1: **32,192 comparisons, 0 mismatches**, covering `add`,
`sub`, `mul`, `div`, `max`, `min` under default, DAZ only, FTZ only and DAZ + FTZ, and `cvt f32→i32`
under RNE and RZ with and without DAZ, on 1,000 random pairs from a pool of special and random bit
patterns plus every conversion boundary (2^31, −2^31, −2^31 − 256, 2^31 − 128, ±0.5, ±1.5, ±2.5,
NaN). The v0 check (10,000 comparisons; add, mul, div, max, min; two environments) left out `sub`
and `cvt_f2i`, on which the R19 proof rests (finding R1-10). Both encode the same SDM reading, so
this checks the encoding, not the reading; silicon checks the reading.

## 6. Example entries

```text
entry VADDPS  form VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512      iform_status xed-datafile
  family FP.ADD.f32 · encoding evex · vl 512 · lanes 16 x f32 · masking merge|zero · upper zero_to_vlmax
  operands  REG0 dst zmm (w) · REG1 mask k · REG2 src1 zmm · REG3 src2 zmm      operands_status xed-datafile
            (the MEMf32 form: MEM0 src2, broadcast 1to16)
  fp_env    ENV_ARITH (rc: MXCSR or {er}+sae on this reg-reg form)
  nan_rule  NAN.ARITH2 · nan_role {src1: transparent, src2: transparent} · table_source sdm+bochs
  sem       {builder: packed_fp2, fn: fp_ops.add} · precond mxcsr.exception_masks == all
  observables dst.zmm_full_width, mxcsr.flags(per execution)
  uncertain F-TINY, F-FTZ-EXACT, F-FLAGPRI, F-MASKEXC, F-ER
  sdm       Vol 2 ADDPS; Vol 1 Table 4-7; Vol 1 §4.9.1.5
  evidence  sdm_review: — · fuzz_record: — · bochs_record: — · grade: untested
  content_hash sha256:… (table.index())

entry VMAXPS  form VMAXPS_YMMf32_MASKmskw_YMMf32_YMMf32_AVX512      iform_status xed-datafile
  family FP.MAX.f32 · lanes 8 x f32 · fp_env ENV_SELECT · nan_rule NAN.SELECT2
  nan_role {src1: observer, src2: observer} (03 §6.3, conservative)
  lane i: if isnan(a) || isnan(b) || (a == 0 && b == 0) then b      -- b unchanged, SNaN not quieted
          else if a > b then a else b
  uncertain F-DAZ-SEL (DAZ=1 only), F-FLAGPRI, F-MASKEXC

entry VCVTPS2DQ form VCVTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512        iform_status xed-datafile
  family FP.CVT.f32_i32.rc · fp_env ENV_CVT_F2I · nan_rule NAN.CVT_F2I · nan_role {src: erasing}
  sem {builder: packed_fp1, fn: fp_ops.cvt_f32_to_i32, trunc: false, src_eb: 32, dst_eb: 32}
  lane i: NaN | ±inf | round_rc(a) ∉ [-2^31, 2^31-1] -> 0x80000000 (IE); else round_rc(a) (PE if inexact)
  uncertain F-DAZ-CVT (DAZ=1 only), F-MASKEXC, F-ER
```

## 7. Evidence and the content hash

**Content hash.** `content_hash = sha256(canonical_json(entry minus evidence) ‖ 0x00 ‖
bundle_hash)`, where `bundle_hash` is a sha256 over the seven semantics modules (`bits`, `fpenv`,
`rounding`, `fp_ops`, `int_ops`, `vec`, **`table`**) with line endings normalised
(`table.content_hash`).

**What the hash covers, and what it does not (findings R1-5, R2-10).** v0 claimed the hash
"over-invalidates but cannot under-invalidate". That was false: the closures that bound operands to
lane functions lived in `table.py`, which was not in the bundle, and the wiring itself (argument
order, `trunc`, `src_eb`, the COMISS `signalling` flag) was not a declarative field. Swapping two
arguments inside the VPDPBUSD closure changed the semantics and left every content hash unchanged.
Since the revision:

- every entry's wiring is a declarative `sem` spec, hashed with the entry, and `_sem` is built from
  it by `table.build_sem` (self-test I8 asserts that every `_sem` carries its spec and that editing a
  spec, or swapping two operand roles, re-keys the entry);
- `table.py`, which holds the builders, is in the bundle, so a builder edit re-keys every entry
  (over-invalidation, accepted in v0);
- **known remaining limits**: the Python interpreter and its standard library (`fractions`) are not
  hashed; the generated C interpreter, the harness and the stubs are hashed separately and named in
  every `fuzz_record` (FUZZ-DESIGN §1), so a fuzz record binds both the entry hash and the
  interpreter hash. v1 replaces the bundle with each entry's own dependency closure (the source of
  its `sem` builder and every function it reaches) once the C generator exists.

Evidence records name the content hash they were produced against, so the ledger's invalidation rule
(03 §4.5) applies unchanged: a changed entry has no evidence.

**Evidence block** (attached by the ledger, never written by hand):

| Field | Content | Produced by |
|---|---|---|
| `sdm_review` | SDM pages read, reviewer, model family, date, the uncertainty classes the reviewer raised | review step (FUZZ-DESIGN §7) |
| `fuzz_record` | ledger hash of the vector set and results; silicon fingerprint (CPU family/model/stepping, microcode revision, OS build); interpreter and stub hashes; per case class: vectors run, value mismatches, flag mismatches per execution | native harness on the 9950X |
| `bochs_record` | Bochs commit, configure flags, CPU model, per class: vectors run, agreements | second oracle |
| `exhaustive_record` | for lane functions with ≤ 2^32 inputs: enumeration result, stream hash and the generator's hash | native harness, exhaustive mode |
| `cross_oracles` | integer entries: equivalence against Hydride, VeGen or Alive2 terms where they overlap [G02 Implications 5] | T2 tooling |
| `grade` | computed, never set (below) | ledger |

**Grade rule** (03 §6.7, made operational; per entry and per environment profile instance):

- `validated(exhaustive)`: the lane function's whole domain was enumerated on the fingerprint
  with zero mismatches: VCVTPH2PS 2^16 per environment; **f32 → i32 conversions 2^32 per (RC, DAZ)**;
  **i32 → f32 conversions 2^32 per RC** (v0 said "2^32 per RC" for all unary conversions, although
  the f32 → i32 profile also reads DAZ; finding R1-12) **and** the conditions of
  `validated(partition)` hold.
- `validated(partition)`: every case class FUZZ-DESIGN.md declares for the entry ran on the
  fingerprint with zero mismatches on every declared observable; the second oracle agreed on every
  class it can run; the SDM review is signed. **Where the entry's or the class's `table_source`
  includes Bochs, Bochs agreement on that class counts as zero independent evidence**, and the class
  rests on silicon plus the signed SDM review (finding R2-13; the classes are listed in §12 and in
  prereg §9). Uniformity within a class remains the axiom of 03 §3.4.
- `tested`: anything less. A two-source FP entry can never be exhaustive (2^64 inputs), so its best
  grade is `validated(partition)`.

## 8. How T1 and T2 consume an entry

1. **Lift.** The lifter (04-toolchain) decodes with XED and looks up (iclass, iform); at intrinsic
   level it resolves each intrinsic through `intrinsic_map.v1` (§8.1). **An unknown key is a
   rejection**: the variant drops to `tested` and is not dispatched in release (DR-008). The same
   happens for an entry whose grade for the instantiated environment is below the slot's premise
   requirement. Operand roles come only from the entry's `operands` field.
2. **Instantiate the environment.** Kernels run under the default MXCSR, so T1 instantiates
   `Env = default` and records "MXCSR = 0x1F80 at entry" in the certificate: **a declared
   precondition for C Hearth b5d3f14, provisional pending D0-5b**, and the runtime-checked
   trust-base entry of 03 §3.4 once the guard lands (§4). Code that writes MXCSR never reaches T1
   (T0 bans LDMXCSR in policy code; X0 reports FP-environment instructions in kernels).
3. **Symbolic evaluation.** Data-movement, bitwise and integer entries are evaluated as QF_BV terms,
   so shuffles, permutes, extracts and blends become lane routing (KLEE-FP's method [R07 §5]). FP
   entries become DAG nodes labelled by (family, environment profile instance, operand roles).
4. **Match.** The matcher compares the lifted FP DAG with the KIR DAG node for node: same family
   label, same operands in the same roles, modulo the rewrite rules (RULES.md). The NaN layer and
   the entries' `nan_role` fields are consulted only for side conditions: which consumers observe NaN
   payload, sign or operand position (RULES.md §2).
5. **Discharge.** Integer subterms, mask contents, ranges, footprints and the domain predicates
   (RULES.md §4.0) go to T2 as QF_BV obligations built from the same entries.
6. **Certify.** The certificate lists the content hashes of every entry used and the hash of
   `intrinsic_map.v1`. They are premise components of the claim's trust base (03 §3.4), so the
   claim's effective grade is capped by the weakest entry grade.

### 8.1 `intrinsic_map.v1`: from intrinsics to table keys (finding R2-8)

Table entries are keyed by (iclass, iform), but an intrinsic has no iform: register or memory form,
VEX or EVEX, and the 128/256-bit AVX-512VL forms (`_mm_mask_mov_ps`, `_mm_cmp_ps_mask`,
`_mm_mask_storeu_ps`, `_mm256_maskz_loadu_epi16`) all differ. The scalar C inside the SIMD files has
no intrinsic at all (`amax / 127.0f`, `d != 0.0f ? 1.0f / d : 0.0f`, `(int8_t)q`, `a->sum * bias`).
v0 left this step undefined, which made "every instruction the transliteration uses" (prereg §4
item 9) circular. The map is a frozen, hashed artefact:

- **intrinsic → (iclass, encoding, vl) of the register form**, or "cast" (no instruction), or
  "seq: …" (a sequence intrinsic with its expansion). Encoding rule: every `_mm512_*` intrinsic and
  every masked or k-producing 128/256-bit intrinsic is EVEX; every other 128/256-bit intrinsic is VEX,
  in both files (unmasked VEX and EVEX forms share a family and lane function; the census records
  which one a compiler emitted).
- **Scalar C operators in the SIMD files** map to named VEX scalar forms: `/` → VDIVSS, `*` →
  VMULSS, `+` → VADDSS, `-` → VSUBSS, `==`/`!=` → VUCOMISS (quiet; the truth value from ZF and PF),
  `<`/`>`/`<=`/`>=` → VCOMISS (IEEE relational operators signal on QNaN), `(float)int32` →
  VCVTSI2SS, `(int32)float` → VCVTTSS2SI. Integer C operators keep C integer semantics and are QF_BV
  terms for T2 (signed overflow is UB, so T2 proves its absence); they use no table entry.
- **Sequence intrinsics** carry explicit expansions: `set1` → a constant or a broadcast, `setzero`
  → the zero idiom (+0.0 lanes), `_mm512_abs_ps` → VPANDD with a broadcast `0x7FFFFFFF`,
  `_mm512_reduce_add_ps` (introduced only by an M-TREE mutant) → the halving tree of Intel's
  documentation.
- The transliterator resolves every operation through `table.find(iclass, iform)` and records the
  content hashes it used.

Draft v0 of the map is `INTRINSIC_MAP_V0` and `SCALAR_C_MAP_V0` in
[semantics/hearth_kernels.py](semantics/hearth_kernels.py), hash
`4aa8e2c5e0afeb35cbfebacd50091bfb2dcd4e1efd45d9c9dc35a5ab7d64d1d0` [M] rev. It covers all 130
intrinsics of `quant_avx2.c` and `quant_avx512.c` at b5d3f14 (self-test I9): 31 resolve to a table
entry today, 67 name an instruction (43 distinct iclasses) that has no entry yet, 19 are sequences
and 13 are casts [M] rev. The intrinsic → instruction mapping is the Intel intrinsics documentation
as read by the X2 agents [inference]; before freeze it is checked against X0's per-variant iclass
multisets, and the entries for the 43 iclasses are written. The map must also cover every intrinsic
a mutant operator can introduce (MUTANTS.md §2). The Python compositions in `hearth_kernels.py`
already resolve every FP instruction and every integer instruction with an entry through
`table.find` and record their content hashes (`entries_used()`: 26 entries after a self-test run);
the data-movement operations they still call directly are listed by `unregistered_used()` (22
`int_ops` functions) [M] rev.

## 9. Absorbing the X0 census

X0 has not reported yet. v0 covers the **intrinsic-implied set**: the 130 distinct `_mm*`
intrinsics in `quant_avx2.c` and `quant_avx512.c` at b5d3f14 (my count matches G02's 130 [M]
X2-agent 2026-10-16), plus the scalar SS instructions that `quant.c`'s scalar variants and the
scalar C inside the SIMD files are predicted to emit (`amax / 127.0f` → DIVSS; `q_rint` → ADDSS,
SUBSS; `(int)` casts → CVTTSS2SI; `(float)isum` → CVTSI2SS; `d != 0.0f`, `v != v` → UCOMISS)
[inference: compiler behaviour, to be replaced by the census].

**Input (finding R2-9).** v0's absorber read X0's per-object `functions.json` (every function in an
object, quantisers and helpers outside the dispatched closures included), ignored the EVEX operand
fields, and matched labels that X0's smoke outputs do not use (`A-msvc`, not `A`). The revised
absorber reads the census of record:

```text
python -B -m semantics.census_absorb --census census.json --insts instructions.jsonl \
       --configs A,D [--label-map A=<label>,D=<label>] --budget -o coverage.json
```

- **Scope:** the `variants[]` of the selected configurations only (their `closure` symbols), the
  release configurations A and D at minimum and all four unless X0's amber (a) fires (ROADMAP §3.1,
  DR-008).
- **Operand variants:** each instruction record's XED fields (`MASK`, `ZEROING`, `ROUNDC`, `SAE`,
  `BCAST`; X0's `x0_decode.py` records them) give `plain | merge | zeroing | bcast | sae |
  er:ROUNDC=<v>`; they decide which V3, V4 and BCAST rows the budget needs.
- **Refusals:** a configuration whose label matches no instruction record, and any configuration
  whose closure iforms in `instructions.jsonl` differ from the iforms `census.json` lists for it (a
  join cross-check). The absorber never guesses.
- **Legacy mode** (`--functions`) reads smoke `functions.json` files, reports them as whole-object
  data, and never feeds the verdict. Run on X0's four smoke outputs it finds every `xed-decode` key
  of the table (self-test J1) [M] rev.

| Bucket | Meaning | Action before T1 may accept code containing it |
|---|---|---|
| `covered_exact` | entry exists for this (iclass, iform) | none |
| `needs_form_instance` | the family exists, this operand shape does not | add an entry instance (same lane function), add its case classes to the budget |
| `needs_family` | no entry for the iclass | write the family from the SDM; FP-sensitivity decided with a written reason; a `nan_role` (default observer) and a `table_source`; unclassified ones are listed |
| `operand_variants_seen` | (iclass, iform, operand variant, count) | budget rows for every variant seen (FUZZ-DESIGN §5) |
| `fp_env_instructions` | LDMXCSR, STMXCSR, FLDCW, … in a kernel | reported to X0 and X2's verdict; T1 rejects code that writes MXCSR |
| `xed_mxcsr_disagree` | table FP-sensitivity ≠ XED `MXCSR` attribute | resolve in writing (X0 §4.4 cross-check) |
| `provisional_unseen` | a provisional key the census never produced | rename to the census string or delete |
| `entries_without_nan_role` | a table entry lacking `nan_role` | add one; until then it is an observer |

**Prediction for X0's P5 count [inference].** The predicted FP-semantic operation classes over all
variants (scalar included) are the 12 families v0 already holds: ADD, SUB, MUL, DIV, MAX, MIN, CMP,
COMI, CVT i32→f32, CVT f32→i32 (RC), CVT f32→i32 (truncating), CVT f16→f32. G02's "about ten"
counted only the intrinsics; SUB, DIV, COMI and the truncating conversion come from scalar C. X0's
smoke decode already shows VSQRTSS (from a smoke helper) and FMA forms (from the contraction probe)
[M, X0 smoke results]; neither is in a Hearth kernel's source, and the census decides whether a
compiler emits them there. This stays below ROADMAP §3.1's amber threshold of 20 unless a compiler
introduces classes no source line asks for, which is exactly what X0 measures.

### 9.1 Census run 1 absorbed (2026-10-23, x2freeze track)

X0 census run 1 (`census.json` sha256 `3d54f0d5…6f06`; build-1 `instructions.jsonl` of A, B-cmake, C, D read from
the desktop run root, hashes equal to X0's `run1_files.sha256`) was absorbed with the revised absorber:

```text
python -B -m semantics.census_absorb --census census.json --insts A.b1.instructions.jsonl B-cmake.b1.instructions.jsonl \
       C.b1.instructions.jsonl D.b1.instructions.jsonl --configs A,B-cmake,C,D \
       --x2-scope x2_scope.json --budget --strict -o census/coverage_run1_ABCD.json
```

- **Absorber fixes found on the real data** [M]: run 1's instruction records carry no `label` (the configuration is
  the prefix of `variant`), and XED's `BCAST` field is the broadcast *type*, set also on VBROADCASTSS and
  VPBROADCAST*; embedded broadcast is `BCRC` on a memory form. v0 would have refused the input and, after a label
  map, tagged every broadcast instruction "bcast". Both are fixed and self-tested.
- **Result** [M]: 446 forms in 222 iclasses (release subset A, D: 384 forms), equal to X0's `x2_scope.json` and to
  its re-derivation; 72 FP-sensitive forms in 32 iclasses; 0 FP-environment instructions; 0 `{er}`/`{sae}`; 0
  disagreements between this table's FP sensitivity and XED's `MXCSR` attribute. Operand variants on FP forms:
  EVEX.b broadcast on VMULPS xmm and zmm memory forms, merge and zero masking on VADDPS zmm.
- **Entries added** (26): 25 FP forms the census found beyond v0 (legacy packed ADDPS (reg, m128), MULPS, MAXPS,
  MINPS, CMPPS, CVTDQ2PS, CVTTPS2DQ; legacy ADDSS, MULSS, MAXSS m32 and COMISS m32; CMPSS; VEX and EVEX VCMPSS;
  EVEX VUCOMISS; CVTSI2SS with a 64-bit source, a new family FP.CVT.i64_f32; VEX VADDPS xmm/ymm, VMAXPS ymm,
  VMULPS ymm and VDIVSS memory forms; EVEX VMULPS xmm m128/m32bcst; VCVTPH2PS VEX m128 and EVEX m256) and the
  VPMADDWD ymm memory form. New builder `cmp_scalar`; `cmp_k` takes `scalar`; `cvt_i2f_scalar` takes a 64-bit
  source. Every FP-sensitive census form now has an entry (`--strict` passes).
- **Dispositions** of every census form (the X2 record, item 4.9): `entry` 77, `object-level/G` 125,
  `object-level/S` 117, `object-level/S, T1-image iclass` 127, each with its written reason in the coverage file.
- **`intrinsic_map` against the census** [D]: every census FP iclass is named by the map up to the VEX/legacy
  spelling except VCMPSS, CMPSS, MINSS and CVTTPS2DQ, which compilers introduce from scalar C (if-conversion,
  vectorisation); they have entries and rows, and T1 at intrinsic level does not consume them.
- **FP-semantic operation classes**: 13 (v0's 12 plus FP.CVT.i64_f32).

## 10. The v0 index

`python -B -m semantics.table` prints the index; `table.index()` returns every entry with its
content hash. At the time of writing [M] X2 reviser 2026-10-16:

- **88 entries**: 41 `xed-datafile` (EVEX), 8 `xed-decode`, 39 `provisional`. The revision added
  the two EVEX memory forms and two VEX memory forms observed in X0's smoke decode and the VEX
  VCVTTPS2DQ forms (the M-TRUNC operator introduces them).
- **12 FP-sensitive families**: FP.ADD, FP.SUB, FP.MUL, FP.DIV, FP.MAX, FP.MIN, FP.CMP, FP.COMI,
  FP.CVT.i32_f32, FP.CVT.f32_i32.rc, FP.CVT.f32_i32.trunc, FP.CVT.f16_f32.
- **Integer families with entries**: INT.MADDUBS.u8s8 (VPMADDUBSW), INT.MADDWD.s16 (VPMADDWD),
  INT.DPBUSD.u8s8 (VPDPBUSD), INT.HADDD (VPHADDD).
- **Implemented in `int_ops.py` but not yet registered as entries** (they are needed for the
  composition checks): VPABSB, VPSIGNB, VPADDD/W, VPSUBD, VPCMPGTD, VPSLLD, VPSRLW, VPAND, VPANDN,
  VPXOR, VPMOVZXWD, VPACKSSDW, VPACKSSWB, VPMOVDB, VPSHUFD, VSHUFPS, VMOVHLPS, VPERMD,
  VPERM2I128, VPUNPCKL/HDQ, VPUNPCKL/HQDQ, VSHUFI64X2, VEXTRACT*/VINSERT*, broadcasts, VBLENDVPS,
  masked moves, VMASKMOVPS stores. They become entries when the census gives their exact iforms;
  `intrinsic_map` v0 names 43 such iclasses (§8.1).
- **Semantics bundle hash** `4c48899cb3cad78c5bba6e29129d1eb9391cb8160148b33e1ba91c7968a3ea31`
  (changes whenever a bundled module, `table.py` included, changes).

**Revision of 2026-10-23** [M]: **114 entries** (41 `xed-datafile`, 62 `xed-decode`, 11 `provisional`), **13
FP-sensitive families** (FP.CVT.i64_f32 added), semantics bundle
`c7cd6851b574af85ebd36091c66f336156f8ab657869a059302e91fc29793eb8`; every content hash is in
`census/table_index.json`. `python -B -m semantics.selftest` runs **720 checks, 0 failures** on the laptop and on
the desktop (B6 corrected and extended; E9 checks the new forms; I6 admits the maskless EVEX VUCOMISS).

**Revision 4 (2026-10-23, after the review of the X2 record's revision 3)** [M]: compare immediates have a declared
domain. The legacy CMPPS and CMPSS entries carry `imm_max: 7` in their hashed `sem` spec (SDM: imm8 bits 7:3
reserved for the legacy encoding) and the VEX and EVEX compares take 0-31; outside it the builder raises
`UnmodeledEnvironment`, `pyref.py` reports "unmodeled" and the C interpreter refuses, so no consumer gets a
prediction for a reserved immediate (v0 masked imm with 31 and predicted the VEX predicate, e.g. EQ_UQ for legacy
CMPPS imm 8). Semantics bundle `0c2a041c363e34ee27a62a873fd0adad5cf8f5711ec2aa3a16cb2f5c9709ff2d`; every content
hash changed with it (`census/table_index.json`). `python -B -m semantics.selftest` runs **725 checks, 0 failures**
on the laptop and on the desktop (E10: imm 7 predicted, imm 8 refused on both legacy entries, VEX VCMPSS imm 8
predicted). The v0 figures follow.

Self-test status: `python -B -m semantics.selftest` runs **706 checks, 0 failures** in about 6 s
wall time; `--full` runs the same 706 checks with the complete 1,536-case witness scan in about 15 s
[M] X2 reviser 2026-10-16 laptop. (v0: 467 checks; its first run had 4 failures, all in hand-derived
expectations that forgot the DE flag of a denormal source operand; the expectations were corrected
and the correction is recorded in the test file.) Coverage, stated precisely (v0 overstated it;
finding R1-10):

- **Hand-derived (A-F):** signed zeros, NaN payloads in each position, ties to even, every rounding
  mode, overflow, gradual underflow, the tininess band, FTZ, DAZ; **all 32 compare predicates ×
  {1 < 2, 1 = 1, 2 > 1, (QNaN, 1), (SNaN, 1)}, result and IE** (C5, 192 checks, added in the
  revision; v0 checked the truth value of 6 predicates); conversion boundaries 2^24 and 2^31,
  integer indefinite, f16 subnormals and NaNs; write masks, broadcast, scalar forms, {er};
  full-width destinations of the scalar forms and scalar converts (E8); coexisting-flag readings
  (B6) and SEL-MAX spot vectors (B7); saturation and wrap cases for the integer entries.
- **Derived (G-J):** Hearth lane maps, act_q8 and block sums across ISAs, the DOM-ACT-SUM witness
  (G7), T2 bounds, mutant witnesses on nine blocks, the commute-before-MAXPS rule against
  simulation (H5), registry integrity (fields, roles against NaN rules, `nan_role` whitelist, wiring
  hashed, intrinsic map; I5-I9), the census absorber (synthetic census and X0's smoke outputs), and a
  host-float cross-check (8,000 random RNE operations, 0 disagreements; double rounding through
  binary64 is innocuous for +, −, ×, ÷ since 53 ≥ 2·24 + 2).
- **Not covered by the self-test:** the SMT terms (checked by `smt_encoding`'s differential, §5),
  every iform's full budget (FUZZ-DESIGN §5), and anything about silicon.

## 11. Out of scope for the table v0

Unmasked exceptions and #XM; #GP and page faults (footprint, not value; fault *suppression* is
tested as F-MEMFAULT); x87; AVX-512 FP16 (Zen 5 has none [G02 §1]); VDPBF16PS, VCVTNEPS2BF16, RCP14
and RSQRT14 (special entries, §4 rule 8); performance effects of denormals; MXCSR writes (T0 bans them
in policy code; in kernels they are census findings); transcendental functions (they are meanings
built from table operations, DR-014, or opaque calls outside T1's table; prereg §4 item 2(c) admits
opaque-call congruence as a global premise kind under Owner question 8's option (b)).

## 12. Uncertainty register

Each item is an SDM reading that the reference semantics implement but that has not been checked
on silicon. All are fuzz classes in FUZZ-DESIGN.md §3. **Items that touch the default-MXCSR
environment: F-TINY (UE flag only), F-FLAGPRI (flags only), F-MASKEXC (flags only), F-H2F (DE and IE
flags; its value part needs DAZ = 1) and F-MEMFAULT (footprint, not value).** v0's sentence named
only F-FLAGPRI and the masked-lane claim while its own F-TINY row said "flags only (UE)" (finding
R1-11). `table_source` says where the implemented reading came from; where it includes Bochs, Bochs
agreement on that class is not independent evidence (§7).

| ID | Reading implemented | Alternative a chip might implement | Touches default MXCSR? | table_source |
|---|---|---|---|---|
| F-TINY | tininess after rounding | before rounding | flags only (UE) | sdm+bochs |
| F-FTZ-EXACT | FTZ flushes exact tiny results too, flags UE\|PE | exact tiny results pass through | no (FTZ = 1) | sdm+bochs |
| F-DAZ-SEL | MAX/MIN under DAZ return the flushed zero | return the original denormal bits | no (DAZ = 1) | sdm+bochs |
| F-DAZ-CVT | CVT(T)PS2DQ honour DAZ | ignore DAZ | no (DAZ = 1) | sdm |
| F-FLAGPRI | a NaN source suppresses DE; DEN / ±0 gives **ZE alone** (corrected 2026-10-23 from DE\|ZE on silicon and Bochs evidence, §4 rule 7); DEN + ∞ gives DE; under DAZ, DEN × ∞ and DEN / DEN are invalid (IE only) | DE also raised with a NaN; DE\|ZE for DEN / 0; no DE when the result is ∞; DAZ applied after the invalid check | flags only | sdm |
| F-MASKEXC | masked-off lanes raise no exception | flags from masked lanes | flags only | sdm |
| F-ER | {er} leaves DAZ/FTZ in force | {er} also suppresses DAZ/FTZ | no ({er} unused by Hearth) | sdm |
| F-H2F | VCVTPH2PS ignores DAZ and never raises DE on f16 subnormals; IE on an f16 SNaN, which comes back quiet | DAZ flushes f16 subnormals; DE raised; no IE | flags (DE, IE); value only with DAZ = 1 | sdm+bochs |
| F-MEMFAULT | masked-off lanes of masked loads and stores neither fault nor write | a fault or a write in a masked-off lane | footprint only | sdm |

## 13. Owner questions

*Answered 2026-10-23 under the batch-4 delegation (DELEGATED.md; Pierce reviews at sitting 2): question 1 by P14
(SDM only), question 2 by P9 (flags count, per execution), question 3 by P30 (secondary; their mutants count in
P3).*

1. **Licence (G02 open question 2).** v0 is written from SDM reading only, with no mechanical
   derivation from Intel's intrinsics XML. Should the table stay that way, or may a local draft
   generator parse the XML to propose integer entries for review? Provisional, reversible: SDM-only.
   (`intrinsic_map` v0 was written from the documentation as read, not parsed from the XML.)
2. **MXCSR flags in the gate.** This track counts a flag disagreement as a table/silicon mismatch
   (stricter than value-only), per execution (FUZZ-DESIGN §2). T1 never consumes flags. Confirm, or
   rule flags out of the gate before data.
3. **F16 and BF16 variants.** ROADMAP §3.3 names the Q4, Q8, F32 and act-q8 kernels. The draft
   pre-registration gates on those 8 SIMD variants and reports F16/BF16 (4 variants) as a secondary
   arm for P1; under its Owner question 8 option (b) their mutants still count in P3. Should they
   gate P1?

## 14. Proposed changes to architecture documents (not made here)

1. **03 §6.3, "Never on the list: … MAX/MIN operand commutation".** Unconditional commutation is
   wrong: Z3 finds counterexamples with a NaN operand, and restricted to non-NaN operands it finds
   max(+0, −0) ≠ max(−0, +0) [M] rev (self-test B1 checks the same pair). v0 attributed the ±0
   counterexample to the unrestricted probe, which returns a NaN case (finding R1-9). Hearth's act_q8
   SIMD variants compute `amax` as a lane-parallel NaN-skipping max tree, while the scalar meaning is
   a sequential fold. T1 cannot accept them without *conditional* rules: max is associative and
   commutative on sign-bit-0, non-NaN operands (RULES.md R02/R03, with the base step R01 SEL-MAX;
   lemmas proved by Z3 in ≤ 0.01 s [M]). Proposal: replace the blanket ban with "MAX/MIN commutation
   only under R02/R03's side conditions".
2. **03 §6.7.** Add per-environment-profile grading (§4 above), and the rule that Bochs agreement is
   not independent evidence on readings taken from Bochs (§7).
3. **ARCHITECTURE §8.2 / G02.** The "about ten FP-sensitive mnemonics" omit the scalar SS
   instructions that compilers emit for the scalar C inside the kernels (DIVSS, SUBSS, CVTTSS2SI,
   CVTSI2SS, UCOMISS) [inference; X0 will settle it].
4. **03 §3.4.** The default-MXCSR entry is runtime-checked only where the runtime checks it. For
   certificates of C Hearth before D0-5b lands it is a declared precondition; the trust-base printout
   should say which (§4).

## 15. Review log

| Date | Reviewer lens | Family | Findings (by severity) | Accepted | Rejected |
|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1: semantics and tests (witness analysis, domains, flag observables, operand roles, hashing, coverage) | Claude (same family as author; independent context) | 13: 0 blocker, 5 major, 8 minor | 13 (2 with a corrected sub-claim, below) | 0 |
| 2026-10-16 | Reviewer 2: pre-registration and gate logic (premise kinds, P3 reachability, mutant classification, false accepts, amber, rule count, intrinsic map, census scope, budget, oracle independence, MXCSR premise, tools) | Claude (same family as author; independent context) | 21: 3 blocker, 12 major, 6 minor | 21 (2 with a modification, below) | 0 |

| 2026-10-23 | Reviewer 1 of the X2 record's revision 3 (census absorption, B6 correction, the 26 new entries, budget changes, gate script, §8 rows, scope dispositions) | Claude (same family as author; independent context) | 9: 0 blocker, 3 major, 6 minor | 9 (8 fixed in revision 4; 1 forwarded to the lead engineer; 4 with a modification, below) | 0 |

**Disposition of the 2026-10-23 review (revision 3 → revision 4).** Findings in the reviewer's order:

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | major | O1 offered a binary choice and did not split the 186 iclasses without an entry | fixed (modified: the 48 T1-image entries are due before T1 accepts code using them, and a Pass needs all 48 [inference], rather than "by the verdict"): record §4 item 9, §9, §13 O1 (138 deferred = 55 G + 83 S [D]); §14 has three options |
| 2 | major | O4's carve-out was the registered default although OWNER-QUEUE C20 is class B (narrows a false accept); the P3 exclusion could drop an intrinsic-level FP-changing mutant | fixed: strict reading registered (record §4 item 6, §13 O4, §14 line); P3 exclusion narrowed to mutants not FP-changing at intrinsic level (record item 5; MUTANTS.md §1, §6) |
| 3 | major | cited working-document sections were not pinned at the freeze commit; E8 undefined in the record | fixed: record §2 "Working-document text"; item 8 defines environment and E8 |
| 4 | minor | §8 `gate_missed` attributed three extra conditions to P28 | fixed: §8 row names P28's conditions and the three added ones; §13 O9; §14 line |
| 5 | minor | `verdict.json` lacked P1-P6; no range checks | fixed: field `inputs`; ValueError on impossible inputs; 24 self-test cases (modified: negative counts and a non-boolean `p2_all_proved` also refused) |
| 6 | minor | legacy CMPPS/CMPSS predicted imm 8-31 | fixed (modified: the domain is a hashed `sem` field checked in the compare builders, not in `fp_ops.cmp_pred`, where sealed mutant M04 anchors; VEX/EVEX compares refuse imm > 31; `pyref.py` reports unmodeled) |
| 7 | minor | FP.CVT.i64_f32 had no sticky-bit class and "the same 12-class design" was inexact | fixed (modified: the construction is in CVT-BND (V2), not a replaced V1 class, so no row count changes; s ∈ [8, 38] since s = 39 can exceed 2^63 − 1; comment corrected) |
| 8 | minor | stale passages after the DELEGATED adoptions | fixed: MUTANTS.md §6, RULES.md §1, §3.1, §5, `gen_vectors.py` docstrings and comments, harness/README.md §4, §6 |
| 9 | minor | DELEGATED.md says no proposed row is adopted above rows marked ADOPTED | accepted, outside this track's files: forwarded to the lead engineer (record §12) |

Totals of the 2026-10-16 reviews: 34 findings (3 blocker, 17 major, 14 minor); 34 accepted, 0 rejected outright. Two pairs
overlap (R1-5 with R2-10, the hash; R1-4 with R2-9's missing schema fields) and were fixed once.
Parts of findings **not** adopted, with the reason:

- **R1-7, on R19 (RINT-MAGIC).** The claim "R19 holds for any RC applied to both sides" is wrong for
  RZ: `(v + 1.5·2^23) − 1.5·2^23` is positive before the subtraction, so RZ rounds it down (floor),
  not toward zero. Z3 proves the rule for RD and RU and returns a counterexample for RZ (e.g.
  `0xC12D829E`: −11 against −10) [M] rev, matching Hearth's 2026-10-04 council finding. RULES.md
  records R19's Env as RNE (as used), with RD/RU proved and RZ refuted.
- **R1-13, SEL-MIN.** SEL-MAX was added (R01); SEL-MIN was proved (Z3, 0.00 s [M] rev) but not added
  to `rules.v1`, because no Hearth site needs it and every row counts whether used or not.
- **R1-1, tree erasure wording.** The proposed text "x[60]/x[62] erase lane pairs" is imprecise:
  on AVX2 x[62] erases four lanes {0, 2, 4, 6}, on AVX-512 eight. MUTANTS.md §5 uses the exact rule
  (`nan_tree_fate`), verified against simulation on all 1,536 cases.
- **R2-2, provisional default.** The reviewer proposed option (a) (gating hosts only in P3's
  denominator) as the provisional default. Option (a) removes required ROADMAP mutant classes
  (M-ROPE) from the gate, which loosens "rejects 100% of FP-changing mutants"; the revision makes
  option (b) (every host joins T1, with an opaque-call premise kind) the provisional default and
  offers (a) to the Owner as an explicit loosening (prereg Owner question 8).
- **R2-4, carve-out.** The native false-accept definition is adopted. A native difference whose
  cause is the compiled object differing from the transliteration (shown by replaying the object's
  own instructions through the table) is recorded as a level-divergent finding, not a T1 false
  accept, since X2's T1 judges intrinsic-level IR; the alternative is put to the Owner (prereg
  Owner question 13).
