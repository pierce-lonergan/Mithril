# X0 census report: instruction census of Hearth's quant kernels

Status: **verdict computed, UNSIGNED.** The Gatekeeper (`judge.py`) has computed `verdict.json`, and the computed outcome is `tooling_failure` because validity check V3 fails. Nothing in this report is a verdict. The verdict waits for Pierce's signature at the weekly sitting (D0-12, Sunday 2026-10-18). Collection ran under the X0 exception in the D0-12 option text ("except X0, which you already authorised") [M, OWNER-ANSWERS.md batch 1, as quoted in the record header].

Record: [docs/m0/prereg/X0-census.md](../../docs/m0/prereg/X0-census.md), FROZEN at `152fa33cc24225d78806bc028a1985fffbd3148b`. This report is the REPORT.md that record §11 requires. Written 2026-10-17 by the report-writer agent, on the laptop, from the files under `experiments/x0-census/results/`. It edits no record text and no census output. Proposed record text appears only in §15, as a proposal to the lead engineer.

Evidence tags (docs/m0/README):
- **[M]** is measured. Each [M] figure names the field it was read from. `census.json:<path>` means `results/census.json` (sha256 `3d54f0d5…6f06`). `verdict.json:<path>` means `results/verdict.json` (`56a68a7d…34a9`). `rederive/…` means `results/rederive/…`.
- **[D]** is derived by this writer from [M] fields. A [D] figure is a count, a set operation or a comparison over census.json and the frozen class files. The scratch scripts that computed them are not part of the record.
- **[inference]** is reasoning that has not been checked against objects.

Small integers that are definitions (18 variants, the s = 8, 4, 2, 1 pairing) carry no tag, as in the record.

---

## 1. Summary

- **Run.** The census ran once (`census-20261017T141025Z`). Host DESKTOP-8RS9J1J, 07:10-07:19 PT on 2026-10-17 [M, run.json `utc_start`; joblogs/progress.txt]. It started from a clean clone in which the freeze commit was also the run commit (`post_freeze_changes` []). Every pinned script matched its pin, and all 7 Hearth blobs matched at b5d3f14 [M, run.json].
- **Computed outcome.** `tooling_failure` [M, verdict.json:outcomes]:
  - V1 true, V2 true, V4 true [M, verdict.json:validity].
  - V3 false, because no re-derivation had run when the census was assembled [M, census.json:rederivation.present = false].
- **Re-derivation.** The independent re-derivation then ran (same family, independent context). It matched every figure except P3(c) [M, rederive/comparison.json]:
  - It matches U_all 446, P5_iclass 32, P5_opclass 15, |B_iform| 102, |B_mnem| 74 and T_forms 102.
  - It matches the iform set, the FP-sensitive iclass set, P1, P2 and d1.
  - **P3(c) differs on 29 loop flags.** The re-derivation flags 25 loops that the census does not, and the census flags 4 loops that the re-derivation does not.
  - `judge.py` was re-run with the re-derivation block. It gives the same outcome, `tooling_failure`, with V3 listing the 29 mismatches [M, rederive/verdict.json].
- **Gate inputs as measured [M]:**
  - |U_all| = 446 against 2·T_forms = 204.
  - P5_iclass = 32 against the limit of 20.
  - P2 = 0 in every configuration.
  - P3(a1) flags B-cmake (`-ffp-contract=on`) on all three files.
  - P3(c) flags 4 loops under C, in `k_avx512` Q8 and Q4.
  - d1 is `pass` everywhere, and no d2 site is `mismatch`.
  - The only P1 gaps are B-cmake's 6 `k_avx512` variants (genuine `compile_failed`).
- **If V held, the decision list would give the following.** This is a preview [D], not a verdict:
  - Amber (a) holds.
  - Amber (b) holds for B-cmake (P3(a1)) and, as the census stands, for C (P3(c)).
  - Amber (c) does not hold.
  - Rows N1 and N2 apply to B-cmake.
  - The C flags look like an over-count by the census (§10). If a logged tooling fix confirms that, Amber (b) would rest on B-cmake alone.
- **Time-critical.** V3 must be settled before the week-3 bound of 2026-11-12 [M, verdict.json:tooling_bound]. After the bound, rule (iii) flags a variant if either side flags it. The re-derivation's 25 extra flags include 3 loops under A and 13 under D, so Amber (b) would then reach both release configurations (§2.3). The re-deriver attributes those 25 flags to a bug in its own v1 script.

---

## 2. Computed verdict row (record §8), UNSIGNED

### 2.1 The verdict as computed

| Item | Value | Source |
|---|---|---|
| record | X0-census | [M] verdict.json:record |
| outcomes | `[tooling_failure]` | [M] verdict.json:outcomes |
| validity | v1 true, v2 true, **v3 false**, v4 true | [M] verdict.json:validity |
| validity_detail | v1_tooling_gaps [], v1_config_gaps [], v2_unresolved [], v2_resolved_by_amendment [], v3 [] (no re-derivation yet), v4 [] | [M] verdict.json:validity_detail |
| v4_commits | freeze_commit = run_commit = 152fa33…148b; post_freeze false; post_freeze_changes [] | [M] verdict.json:validity_detail.v4_commits |
| tooling_runs | 1 | [M] verdict.json:tooling_runs |
| conservative_resolution | false | [M] |
| eval_date / tooling_bound | 2026-10-17 / 2026-11-12 | [M] verdict.json:eval_date, tooling_bound |
| amber_a, amber_b, amber_c, non_gate | null, [], [], [] | [M]. These are **not evaluated**, not empty findings. `judge.py` returns before the rows when V fails before the bound (judge.py lines 527-530) |
| canaries, caveats | absent | [M]. Written only after the rows (judge.py line 663 ff.), so they are reported from census.json in §12 |
| narrowing | null | [M]. Judged at week 6 jointly with X2 |

Label for the sitting: **UNSIGNED. Computed by `judge.py` at 152fa33. Pending D0-12 (weekly sitting, Sun 2026-10-18).**

### 2.2 Decision-list trace (record §8 "Exhaustiveness", items 0-10)

| Step | What `judge.py` checks | Result at this run |
|---|---|---|
| 0 Schema | Appendix C shape | clean: `census.json:schema_check.violations` [] [M] |
| 1 Completeness | each main-union config and A-ninja lists all variants for builds 1 and 2; a build record for every file; P3(a) per file; coverage, slot and counted set per present variant | v1_config_gaps [] [M]. Variant records: A 36, A-ninja 36, B-cmake 24, C 36, D 36 [M, census.json:variants]. B-cmake's 12 missing records are the `k_avx512` variants of a file that did not compile (step 2) |
| 2 Compile outcomes | compiler pins, header pins, argv against the frozen capture, the genuine/tooling split | 46 build records [M]. All have `compiler_ran` true and `argv_matches_frozen` true [M, census.json:builds]. A's six lines equal the design-time line plus exactly `/O2`, with `/nologo` and `/diagnostics:column` removed, in the same order (`frozen_diff.tolerated` true) [M]. 44 builds have rc 0 and an object [M]. **B-cmake `quant_avx512.c` has rc 1 in both builds**, with 4 errors located in the census file at lines 237, 238, 239 and 240 ("always_inline function '_mm512_dpbusd_epi32' requires target feature 'avx512vnni' …"), no ICE, and 156 includes recorded [M]. That makes it a genuine `compile_failed` |
| 3 A-ninja | `ab_compare` for every variant | `identical` 36 of 36 [M, census.json:metrics.secondary.ab_compare]. No A-ninja variant is a union member |
| 4 After the week-3 bound | conservative resolution | not applicable: eval_date 2026-10-17 < 2026-11-12 [M] |
| 5 Unknown cause codes | rewritten to `other` | none present [D] |
| 6 Recomputation | Amber (a), P2 and P3(b) from iform/iclass sets | not reached by `judge.py` (V fails). This writer's recomputation [D]: U_all 446, P5_iclass 32, P2 0 (no FMA-class iclass in the union), P3(b) none. All equal census.json:metrics |
| 7 V4 | class files, XML, compiler and script pins | true [M] |
| 8 Narrowing | week 6 | not evaluated |
| 9, 10 | x0final and pre-freeze review rules (attribution, freeze point, per-step re-checks, header pins) | attribution `exact` for every variant [M, census.json:metrics.secondary.attribution]. The header environment equals its pin in every configuration (no V1 config gap) [M] |
| V2 | cross-decoder disagreements involving an FP-sensitive iclass | 0 disagreements of any kind [M, census.json:crossdecoder.disagreements] |
| V3 | re-derivation matches | census.json: `present` false [M]. Re-derivation: 29 mismatches, all P3(c) (§10) [M] |

### 2.3 Previews [D], none of them a verdict

**(a) If V held with the census figures as they stand** (record §8 rows):

| Row | Condition | Evaluates to [D] |
|---|---|---|
| Amber (a) | \|U_all\| > 2·T_forms, or P5_iclass > 20 | **holds**: 446 > 204, and 32 > 20 |
| Amber (b) | P2 > 0 or P3 flagged under A, A-ninja, B-cmake, C or D | **holds for B-cmake** (P3(a1) on all three files). **Holds for C** (P3(c): `k_avx512` Q8 and Q4, 4 loops in each build). None under A, A-ninja or D |
| Amber (c) | a genuine P1 gap under A or D | does not hold (no gap under A or D) |
| Pass | V and none of (a), (b), (c) | does not hold |
| N1 | a genuine P1 gap under B-cmake or C | **B-cmake**: 6 variants `compile_failed`, so the union is a lower bound for B-cmake |
| N2 | a non-release configuration fails to compile a census file | **B-cmake**, `quant_avx512.c` (build-defect draft in §14.2) |
| Narrowing | week 6, jointly with X2 | not evaluated |

Under OQ-4's strict reading, which applies until it is answered, a B-cmake or C defect makes X0 amber.

**(b) If the census's 4 C flags are removed by a logged tooling fix** (§10, §15), and the re-derivation is brought into agreement, Amber (b) rests on B-cmake alone. The other rows are unchanged.

**(c) If V3 is still false at 2026-11-12.** Rule (iii) applies, and the re-derivation block written by the v1 script is the one in `rederive/census_with_rederivation.json`:
- A variant is flagged if either side flags it. That adds the re-derivation's flags in 15 variants [M, rederive/census_with_rederivation.json:rederivation.figures, `flagged` true]:
  - A: `k_avx2` Q4, `k_avx512` Q8 and Q4.
  - B-cmake: scalar F32, F16, BF16 and act, and `k_avx2` Q8.
  - D: scalar F32, F16, BF16 and act, `k_avx2` Q8, and `k_avx512` Q8 and Q4.
- **Amber (b) would then hold under A and D.** Without a passing re-run by week 6, the variants would drop to `tested`.
- The re-deriver attributes all 25 of these loop flags to a bug in its own v1 script (§10).
- This is the main reason to settle V3 before the bound.

---

## 3. Run identity and integrity

| Item | Value |
|---|---|
| Run id, kind, profile, mock | `census-20261017T141025Z`, census, hearth, false [M, run.json] |
| Host, window | DESKTOP-8RS9J1J. The orchestrator ran 07:11-07:18 PT; build records span 14:11:36-14:18:53Z [M, joblogs/progress.txt; census.json:runs[].utc]. The assembly re-issue finished 07:19 PT [M, joblogs/82_assemble_2.log] |
| Commits | freeze = run = scripts commit = `152fa33cc24225d78806bc028a1985fffbd3148b`; `record_appended_bytes` 0; `post_freeze_changes` [] [M, run.json; census.json:record] |
| Pins | `scripts_match_pins` true [M, run.json]. Every configuration's `scripts_sha256` equals `record.scripts_sha256` (V4 true) [M] |
| Hearth | `source_commit` b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220; `source_blobs_ok` true, 7/7 [M, run.json] |
| Compilers | A and A-ninja: "Microsoft (R) C/C++ Optimizing Compiler Version 19.44.35229 for x64". B-cmake, B-proxy and D: "clang version 23.1.3 (… 0d261d1ca552…)". C: "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0" [M, census.json:configs.*.compiler.banner]. These are the Table 2.1 pins |
| Header environments | A, A-ninja and B-cmake: SDK and UCRT 10.0.26100.0, toolset 14.44.35207. B-cmake resource dir: 322 files `5587c91b…`. C: libc6-dev 2.39-0ubuntu8.9. D: the same libc plus resource dir 327 files `18b182d3…` [M, census.json:configs.*.headers]. All equal the pins |
| Builds | 46 census builds and 22 twin builds (`/Z7` or `-g`), all twins rc 0 [M] |
| Reproducibility (§6) | builds 1 and 2 are byte- and relocation-identical for every object [M, census.json:configs.*.repro]. B-cmake `quant_avx512.c` has `null` there because neither build produced an object. Every variant field compared (iforms, counts, coverage, P2, P3, lift blockers, sequences, loops) is equal between the builds [D] |
| A versus A-ninja | code sections identical for all three files; `ab_compare` identical 36/36 [M] |
| Attribution | `exact` for all variants of every configuration and arm [M, census.json:metrics.secondary.attribution] |
| Cross-decoder | 0 disagreements [M] |
| Variant records | 264 = A 36, A-ninja 36, B-cmake 24, C 36, D 36, B-proxy 36, and P.A, P.A-ninja, P.B-cmake, P.C, P.D at 12 each [M, census.json:variants] |
| Raw outputs | The decode dumps stay on the desktop under `D:\mithril\x0census\run1\<CFG>\b{1,2}\…\decode\`: 26 decode directories, 130 files, 106,285,526 bytes. The whole run has 1,308 files and 147,613,434 bytes [M, census runner; `results/decode_dirs.txt`]. The manifest of every file is `results/run1_files.sha256` (sha256 `7fef9db3…e084e`) [M] |

**Operational notes** (neither one is a record deviation) [M, census runner's return and job logs]:
1. Local branch `main` (ec46300) was stale and does not contain 152fa33. The runner therefore bundled branch `claude/mystifying-khorana-167d4d` at 3ed3ccb (equal to origin/main). The bundle's sha256 `bb49391c…4a03` is the same on both machines. The checkout used was the freeze commit.
2. The first step-82 call failed in argparse before writing anything (`joblogs/82_assemble.log`). The cause was a variable clash in the runner's own orchestrator: PowerShell variable names are case-insensitive. Step 82 was re-issued once and gave ASSEMBLE_RC 0 (`82_assemble_2.log`). Both logs are kept.
3. The runner started a WSL keepalive (`wsl.exe -d Ubuntu --exec sleep 14400`, pid 16880) before configurations C and D [M, progress.txt 07:14 PT]. The runner reports no other activity on C:.

---

## 4. Gate inputs P1-P5

Main union: A, B-cmake, C and D, plus A-ninja variants that differ from A (none at this run). Both builds are included and are identical.

| Metric | A | A-ninja | B-cmake | C | D | Source |
|---|---|---|---|---|---|---|
| P1 slots resolved | 18/18 | 18/18 | 12/12 compiled | 18/18 | 18/18 | [M] variants[].coverage.slot_resolved |
| P1 genuine gaps | 0 | 0 | 6 variants × 2 builds `compile_failed` (all of `k_avx512`) | 0 | 0 | [M] builds[]; [D] count |
| P1 tooling gaps | 0 | 0 | 0 | 0 | 0 | [M] verdict.json:validity_detail.v1_tooling_gaps |
| P1 `fp_trust_dep` | 0 | 0 | 0 | 0 | 0 | [M] variants[].lift_blockers.fp_trust_deps (every external callee is on the allow-list, §11) |
| P1 indirect branches | 3, all jump tables, resolved | 3, resolved | 0 | 3, resolved | 0 | [M] lift_blockers; jump_tables (scalar F32/F16/BF16: 7 entries; A `ADDR32NB` in `.text$mn`; C `PC32` in `.rodata`) |
| Orphan bytes; sweep-only instructions | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 0; 0 | [M] unreachable.orphan_bytes; sweep_crosscheck |
| Slot-name check | 18 match | 18 match | 12 match | 18 match | 18 match | [M] slot_name_check |
| **P2** (FMA-class count) | 0 | 0 | 0 | 0 | 0 | [M] metrics.p2; [D] no FMA-class iclass in any counted set |
| **P3(a)** flags | none | none | **a1_ffp_contract_on** on quant.c, quant_avx2.c and quant_avx512.c (cc1 `-ffp-contract=on`) | none | none | [M] configs.*.p3a, p3a_hits |
| **P3(b)** approximations | 0 | 0 | 0 | 0 | 0 | [M] metrics.p3.*.b |
| **P3(c)** flagged loops | 0 | 0 | 0 | **4 per build** (`k_avx512` Q8: L1_c64, L1_d98; Q4: L1_2d5f, L1_2e90) | 0 | [M] metrics.p3.C.c; variants[].p3.c |
| **P3(d1)** | pass (b1, b2) | pass | pass | pass | pass | [M] variants[act scalar].p3.d1 |
| **P3(d2)** match / mismatch / unchecked (both builds) | 36 / 0 / 6 | 36 / 0 / 6 | 24 / 0 / 18 | 36 / 0 / 12 | 46 / 0 / 20 | [M] metrics.p3.*.d2_*; [D] the A-ninja count |

| Union metric | Value | Threshold | Source |
|---|---|---|---|
| **P4** \|U_all\| (XED iforms) | **446** | 2·T_forms = 204 (T_forms = min(102, 105) = 102) | [M] census.json:metrics.p4_u_all, baseline.t_forms; re-derivation 446 [M]; [D] recomputed 446 |
| **P5** P5_iclass (FP-sensitive XED iclasses) | **32** | 20 | [M] metrics.p5_iclass; re-derivation 32 [M]; [D] recomputed 32 |
| P5_opclass (secondary) | 15 | none | [M] metrics.secondary.p5_opclass |
| \|iclass union\| | 222 | none | [D] |

`census.json:metrics.p1` is `{}` [M]. The assembler writes no P1 summary block, so the P1 rows above are counts over `variants[].coverage` and `builds[]` [D from M fields].

---

## 5. Delta against B_iform, and reconciliation with G02

### 5.1 Baseline reconciliation

All values below are [M, census.json:baseline and class/B_iform.json], and every one matches G02 §1:
- 130 intrinsic names: 47 `_mm512_*`, 51 `_mm256_*` and 32 `_mm_*`.
- 23 with no single instruction.
- The XML has 105 distinct (instruction name, form) strings. They map to **102 XED iforms**, because several XML forms (for example the masked and unmasked VADDPS zmm forms) map to one iform.
- 74 mnemonics, equal to 74 XED iclasses.
- One hand-mapped row: `_mm256_extractf128_ps`, whose XML form becomes `VEXTRACTF128_XMMdq_YMMqq_IMMb`.
- T_forms = 102 < 105, so OQ-5 does not arise.

### 5.2 Iform delta (three readings)

| Reading | Census side | \|census side\| | Added (in census, not in B_iform) | Missing (in B_iform, not emitted) | Shared | Tag |
|---|---|---|---|---|---|---|
| Raw, as the assembler computed it | U_all^{SIMD,S} | 245 | 167 | 24 | 78 | [M] census.json:metrics.secondary.delta_vs_b_iform_raw (the assembler compares the SIMD category-S union; [D] 167 + 78 = 245 = u_all_simd_S) |
| Raw, full union | U_all | 446 | 350 | 6 | 96 | [D] |
| Operand-normalised, SIMD category S | normalised U_all^{SIMD,S} | 192 | 99 | 2 | 93 | [D] |
| Operand-normalised, full union | normalised U_all | 298 (B_iform: 95) | 204 | 1 | 94 | [D] |

**Missing, raw, full union** [D]: `BLENDVPS_XMMdq_XMMdq`, `MOVHLPS_XMMq_XMMq`, `MOVQ_XMMdq_GPR64`, `PSUBD_XMMdq_XMMdq`, `VPANDD_ZMMu32_MASKmskw_ZMMu32_MEMu32_AVX512` and `VXORPS_YMMqq_YMMqq_YMMqq`.
- The first four are legacy-SSE forms that the XML names for `_mm_*` intrinsics. The AVX-flagged files emit their VEX forms instead.
- The 24 missing in the assembler's SIMD reading [M] are mostly such legacy-SSE forms (ADDPS, MULSS, MOVDQU, PSHUFD, SHUFPS, XORPS and others). The scalar `quant.c` build does emit some of them, which is why only 6 remain missing in the full union.

**Missing after normalisation** [D]:
- `VXORPS` on YMM (register form). [inference] Compilers zero a ymm register with the VEX.128 xmm form, which XED classes as an XMM iform.
- In the SIMD reading only, also `VMOVD` (GPR ← XMM). The full union has it.

**The normalisation rule** is a report-step implementation of §5's words. It is not frozen, and it is a descriptive secondary metric only. Each iform maps to (iclass, ordered operand classes, EVEX flag), as follows:
- Legacy-SSE iclasses become their `V` form when XED defines one.
- Operand tokens reduce to their class (XMM, YMM, ZMM, GPR, MASK, IMM).
- A memory operand takes the widest vector class of the instruction, or GPR when it has none. So load and store forms merge into the register form.
- Trailing opcode-byte tokens are dropped, which merges opcode-direction twins.
- Consecutive repeated operand classes collapse, so 2-operand legacy forms and 3-operand VEX forms match.
- EVEX is kept distinct from VEX.

**Where the added forms come from** (raw, full union, by XED extension) [D]: BASE 119, AVX 79, AVX512EVEX 56, SSE2 33, SSE 25, AVX2 23, AVX512VEX 8, LONGMODE 5, F16C 1, CET 1. Category G alone is 125 iforms [D]: GPR, control flow, NOP-class and hardening. As E4 expected, most of the excess over 2·T_forms comes from forms the intrinsic baseline never names.

### 5.3 Mnemonic units against B_mnem (74)

| Census side | \|iclasses\| | Added | Missing | Shared | Tag |
|---|---|---|---|---|---|
| SIMD variants (`k_avx2`, `k_avx512`), all categories | 156 | 101 | 19 | 55 | [D] |
| SIMD variants, category S only | 108 | 53 | 19 | 55 | [D] |
| Full union | 222 | none | none | none | [D] |

- **Missing** [D]: ADDPS, ADDSS, BLENDVPS, CMPPS, CVTDQ2PS, MAXPS, MAXSS, MOVD, MOVDQU, MOVHLPS, MOVQ, MOVSS, MULPS, MULSS, PADDD, PSHUFD, PSUBD, SHUFPS and XORPS. All 19 are legacy-SSE names that the XML gives for `_mm_*` intrinsics, and each is emitted in its V form.
- **Added, category S** [D]: KMOVB, KMOVD, KMOVW, KORTESTW, KXORW, VADDSS, VBLENDMPS, VBLENDPS, VBROADCASTSS, VCMPSS, VDIVSS, VEXTRACTI32X4, VINSERTI32X4, VMAXSS, VMOVAPD, VMOVD, VMOVDQA, VMOVDQA32, VMOVDQA64, VMOVDQU32, VMOVDQU64, VMOVHLPS, VMOVLHPS, VMOVLPS, VMOVQ, VMOVSHDUP, VMOVSS, VMULSS, VPADDQ, VPANDN, VPANDQ, VPBLENDMD, VPBROADCASTQ, VPBROADCASTW, VPCMPD, VPCMPEQD, VPCMPGTQ, VPERMILPS, VPINSRQ, VPINSRW, VPMAXUD, VPMOVSXDQ, VPMOVZXWQ, VPMULLQ, VPOR, VPORQ, VPSLLQ, VPTERNLOGQ, VSHUFPD, VSHUFPS, VUCOMISS, VUNPCKLPS and VZEROUPPER.

---

## 6. Iform counts per configuration and per variant

### 6.1 Per configuration (counted sets of the 18 variants, union over both builds) [D from census.json:variants]

| Config | \|iforms\| | \|iclasses\| | FP-sensitive iclasses | Note |
|---|---|---|---|---|
| A | 257 | 135 | 23 | release |
| A-ninja | 257 | 135 | 23 | identical to A |
| B-cmake | 243 | 155 | 30 | 12 variants only (lower bound, N1) |
| C | 294 | 158 | 23 | |
| D | 313 | 177 | 30 | release |
| B-proxy (secondary) | 330 | 182 | 30 | |

Secondary unions [M, census.json:metrics.secondary]: \|U_all^S\| 321; \|U_all^SIMD\| 349; \|U_all^{SIMD,S}\| 245; **\|U_release\| (A ∪ D) 384**. Category G in U_all is 125 [D].
- \|U_object\| (arm S-object) and \|U_helpers\| (arm S-helpers) were **not computed**: those arms were not run (§16).

### 6.2 Per variant: instructions / distinct iforms (build 1; build 2 identical) [M, variants[].n_instructions, len(variants[].iforms)]

| Config | Table | F32 | F16 | BF16 | Q8 | Q4 | act |
|---|---|---|---|---|---|---|---|
| A (= A-ninja) | scalar | 353 / 64 | 353 / 64 | 353 / 64 | 215 / 53 | 384 / 57 | 348 / 43 |
| A (= A-ninja) | avx2 | 394 / 56 | 659 / 60 | 698 / 60 | 600 / 90 | 578 / 87 | 161 / 56 |
| A (= A-ninja) | avx512 | 261 / 53 | 242 / 54 | 249 / 55 | 1185 / 110 | 1040 / 112 | 104 / 52 |
| B-cmake | scalar | 643 / 97 | 643 / 97 | 643 / 97 | 385 / 82 | 410 / 92 | 162 / 65 |
| B-cmake | avx2 | 791 / 95 | 830 / 86 | 873 / 84 | 745 / 94 | 685 / 91 | 153 / 49 |
| B-cmake | avx512 | not compiled | not compiled | not compiled | not compiled | not compiled | not compiled |
| C | scalar | 168 / 54 | 212 / 69 | 170 / 56 | 252 / 53 | 262 / 57 | 79 / 43 |
| C | avx2 | 368 / 52 | 426 / 60 | 434 / 63 | 709 / 85 | 659 / 87 | 133 / 48 |
| C | avx512 | 280 / 56 | 303 / 60 | 314 / 63 | 1395 / 133 | 1453 / 133 | 96 / 49 |
| D | scalar | 603 / 95 | 603 / 95 | 603 / 95 | 367 / 78 | 382 / 86 | 136 / 61 |
| D | avx2 | 754 / 92 | 819 / 82 | 851 / 81 | 798 / 90 | 727 / 89 | 131 / 44 |
| D | avx512 | 539 / 82 | 559 / 85 | 529 / 85 | 1080 / 109 | 1045 / 110 | 88 / 45 |
| B-proxy (sec.) | scalar | 643 / 97 | 643 / 97 | 643 / 97 | 385 / 82 | 410 / 92 | 162 / 65 |
| B-proxy (sec.) | avx2 | 791 / 95 | 830 / 86 | 873 / 84 | 745 / 94 | 685 / 91 | 153 / 49 |
| B-proxy (sec.) | avx512 | 547 / 86 | 565 / 89 | 534 / 89 | 1089 / 117 | 1005 / 120 | 88 / 46 |

- The scalar F32, F16 and BF16 variants share one closure body in every configuration (`mm_float_scalar` and `dot16_conv`, inlined or called), so their counts are equal except under C [M].
- B-cmake and B-proxy have **identical iform multisets** for all 12 variants of `quant.c` and `quant_avx2.c` [D]. B-cmake builds with `-ffp-contract=on`, and its `quant_avx2.c` cc1 line has `-target-cpu haswell`, which has FMA [M]. B-proxy builds with `-ffp-contract=off`. So the B-cmake contraction flag produced no different code at b5d3f14 (§14.1).

### 6.3 FP-sensitive iclasses per variant, release configurations [M, variants[].fp_sensitive]

| Variant | A | D |
|---|---|---|
| scalar F32, F16, BF16 | ADDSS CVTSI2SS MULSS UCOMISS | ADDPS ADDSS CMPSS CVTDQ2PS CVTSI2SS MULPS MULSS |
| scalar Q8, Q4 | ADDSS CVTDQ2PS CVTSI2SS MULSS UCOMISS | ADDSS CMPSS CVTDQ2PS CVTSI2SS MULSS |
| scalar act | ADDSS CVTTSS2SI DIVSS MAXSS MINSS MULSS SUBSS UCOMISS | ADDPS ADDSS CMPPS CMPSS CVTTPS2DQ CVTTSS2SI DIVSS MAXPS MAXSS MINPS MINSS MULPS MULSS UCOMISS |
| avx2 F32 | VADDPS VADDSS VCMPPS VMULPS VMULSS | VADDPS VADDSS VCMPSS VMULPS |
| avx2 F16 | VADDPS VADDSS VCMPPS VCVTPH2PS VMULPS VMULSS | VADDPS VADDSS VCMPSS VCVTPH2PS VMULPS VMULSS |
| avx2 BF16 | VADDPS VADDSS VCMPPS VMULPS VMULSS | VADDPS VADDSS VCMPSS VMULPS VMULSS |
| avx2 Q8, Q4 | VADDPS VCMPPS VCVTDQ2PS VCVTPH2PS VMULPS | same as A |
| avx2 act, avx512 act | VCMPPS VCVTPS2DQ VDIVSS VMAXPS VMAXSS VMINPS VMULPS VUCOMISS | same as A |
| avx512 F32, BF16 | VADDPS VADDSS VCMPPS VMULPS | VADDPS VADDSS VCMPSS VMULPS |
| avx512 F16 | VADDPS VADDSS VCMPPS VCVTPH2PS VMULPS | VADDPS VADDSS VCMPSS VCVTPH2PS VMULPS |
| avx512 Q8, Q4 | VADDPS VCMPPS VCVTDQ2PS VCVTPH2PS VMULPS | same as A |

Under D, Clang auto-vectorises scalar `quant.c` code [M, tags §8]. That is why packed ADDPS, MULPS, MAXPS and MINPS appear in D's scalar variants.

---

## 7. FP-sensitive iclasses (P5): the 32 members

[M, census.json:metrics.secondary.fp_sensitive_iclasses; identical to the re-derivation's set (M)]. The op_class column comes from `class/fp_class.csv`, and the presence column is [D] from census.json:variants.

| iclass | op_class | Present in | iclass | op_class | Present in |
|---|---|---|---|---|---|
| ADDPS | ADD.f32 | B-cmake, C, D | VADDPS | ADD.f32 | A, B-cmake, C, D |
| ADDSS | ADD.f32 | A, B-cmake, C, D | VADDSS | ADD.f32 | A, B-cmake, C, D |
| CMPPS | CMP.f32 | B-cmake, D | VCMPPS | CMP.f32 | A, B-cmake, C, D |
| CMPSS | CMP.f32 | B-cmake, D | VCMPSS | CMP.f32 | B-cmake, D |
| COMISS | COMI.f32 | **C only** | VCVTDQ2PS | CVTDQ2PS | A, B-cmake, C, D |
| CVTDQ2PS | CVTDQ2PS | A, B-cmake, D | VCVTPH2PS | CVTPH2PS | A, B-cmake, C, D |
| CVTSI2SS | CVTSI2SS | A, B-cmake, C, D | VCVTPS2DQ | CVTPS2DQ | A, B-cmake, C, D |
| CVTTPS2DQ | CVTTPS2DQ | B-cmake, D | VDIVSS | DIV.f32 | A, B-cmake, C, D |
| CVTTSS2SI | CVTTSS2SI | A, B-cmake, C, D | VMAXPS | MAX.f32 | A, B-cmake, C, D |
| DIVSS | DIV.f32 | A, B-cmake, C, D | VMAXSS | MAX.f32 | A, B-cmake, C, D |
| MAXPS | MAX.f32 | B-cmake, D | VMINPS | MIN.f32 | A, B-cmake, C, D |
| MAXSS | MAX.f32 | A, B-cmake, C, D | VMULPS | MUL.f32 | A, B-cmake, C, D |
| MINPS | MIN.f32 | B-cmake, D | VMULSS | MUL.f32 | A, B-cmake, C, D |
| MINSS | MIN.f32 | A, B-cmake, D | VUCOMISS | UCOMI.f32 | A, B-cmake, C, D |
| MULPS | MUL.f32 | B-cmake, D | MULSS | MUL.f32 | A, B-cmake, C, D |
| SUBSS | SUB.f32 | A, C | UCOMISS | UCOMI.f32 | A, B-cmake, C, D |

- Release-only reading (A ∪ D): **31** iclasses, because COMISS appears only under C [D].
- All 11 iclasses that E3 derived from G02's list are present [D].
- No FMA-class, approximation (RCP/RSQRT), x87, BF16-arithmetic or FP16-arithmetic iclass is present [D].
- No iclass of the union is missing from `fp_class.csv` [D].

---

## 8. Loop-correspondence patterns T1 must handle (§4.7 tag vocabulary)

### 8.1 Totals (build 1; build 2 identical) [D from census.json:variants[].loops]

| Config | Emitted natural loops | With an FP accumulator | lockstep | software-pipelined | spilled | rotated | unrolled-u | auto-vectorised | peeled | interchanged | other |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 144 | 19 | 68 | 53 | 28 | 9 | 9 | 0 | 0 | 0 | 0 |
| B-cmake | 127 | 14 | 57 | 34 | 30 | 18 | 9 | 8 | 0 | 0 | 0 |
| C | 104 | 28 | 51 | 35 | 33 | 2 | 5 | 9 | 0 | 0 | 0 |
| **D** | 197 | 29 | 93 | 59 | 42 | 21 | 17 | 8 | 0 | 0 | 0 |

- A loop may carry several tags. `not_computed_tags` is empty for every loop, and no loop is `unattributed` [M].
- Source-loop rules used [M, loops[].bound_rule; census.json notes, 374 loop notes]:
  - A: same 123, outer 16, min 5.
  - D: same 147, outer 32, min 18.
  - B-cmake: same 101, outer 17, min 7, inner 2.
  - C: same 81, outer 19, min 4.

### 8.2 Per kernel, release configurations (build 1)

Notation: `tags | u_acc/u_ind | emitted/source lanes`. The source lanes come from `class/loop_table.csv` [M]. Every entry is [M, census.json:variants[].loops] unless marked.

| Source loop (loop_table) | Source lanes | A (MSVC) | D (Clang) |
|---|---|---|---|
| quant.c:355 `dot16_conv` i-loop (scalar F32/F16/BF16) | 16 | 3 emitted loops per variant: unrolled-u (u_ind 4), lockstep, rotated; **0 emitted lanes** | 3 emitted loops, all rotated; **0 emitted lanes** |
| quant.c:362 tree s-loop | 8 | 1 lockstep loop, rule `min`, 0 lanes | flattened (no emitted loop) |
| quant.c:371/373 `mm_float_scalar` row and token loops | 0 | spilled; software-pipelined+spilled | rotated and lockstep loops, plus **auto-vectorised** + software-pipelined + spilled loops |
| quant.c:397 `mm_q8_scalar` g-loop | 1 | software-pipelined, u 1/1, 1/1 | lockstep, u 1/1, 1/1 |
| quant.c:416 `mm_q4_scalar` g-loop | 1 | software-pipelined, 1/1 | unrolled-u, u_acc 2, 1/1 |
| quant.c:329 `act_q8_scalar` amax | 1 | spilled + unrolled-u, u_acc 16, 1/1 | software-pipelined + unrolled-u, u_acc 2, 1/1; the quantise loop :335 is auto-vectorised |
| quant_avx2.c:175 `mm_float` 4-row | 64 | lockstep, u_acc 1, 64/64 | rotated (F32) or lockstep (F16, BF16), 64/64 |
| quant_avx2.c:201 `mm_float` 1-row | 16 | lockstep (F32) or rotated (F16, BF16), 16/16 | 2 emitted loops, each unrolled-u (u_acc 2), 16/16 |
| quant_avx2.c:240 `qtile8` T = 1 | 8 | spilled, u 1, 8/8 | lockstep, 8/8 |
| quant_avx2.c:274 `qtile8` T > 1 | 64 | software-pipelined + spilled, **0 emitted lanes** | software-pipelined + spilled, **0 emitted lanes**, rule `min` (bound 0) |
| quant_avx512.c:142 `mm_float` 4-row | 64 | lockstep, 64/64 | lockstep, 64/64 |
| quant_avx512.c:167 `mm_float` 1-row | 16 | lockstep (F32) or rotated (F16, BF16), 16/16 | unrolled-u, 16/16: u_acc 4 with a lockstep remainder loop (F32, F16); u_acc 2 with no remainder loop (BF16) |
| quant_avx512.c:282 `qtile16` T = 1 | 16 | software-pipelined, rule `outer`, 16/16 | software-pipelined, 16/16 |
| quant_avx512.c:295 `qtile16` T > 1 | 128 | software-pipelined, **0 emitted lanes** | software-pipelined, **0 emitted lanes**, rule `min` |
| quant_avx512.c:320 `qtile4` | 32 | software-pipelined, **0 emitted lanes** | lockstep, **0 emitted lanes** |
| act block loops (quant_avx2.c:84, quant_avx512.c:82) | 0 | lockstep, rule `outer` (the census treats the inner amax loops :88 and :86 as flattened) | the same |

**What T1 has to handle, from this table:**
- **Lane-preserving shapes only, where accumulators are visible.** No emitted loop in A or D carries more accumulator lanes than its source loop (no P3(c) flag under A or D) [M].
- The emitted shapes it must cover are:
  - lockstep register accumulators;
  - rotation (exit test in the latch);
  - software pipelining (loads carried around the back edge);
  - accumulator spills and reloads inside the body;
  - serial unrolling with one chain per accumulator (u_acc 2, 4 and 16, never a split);
  - auto-vectorisation of scalar `quant.c` loops (D: 8 loops; C: 9; B-cmake: 8) [M];
  - full flattening of constant-trip inner loops (the tree s-loop under D; the amax loops in the AVX2 and AVX-512 act kernels; `q16_unpack`).
- **No `peeled`, `interchanged` or `other` loop in any configuration** [M].
- **Accumulations P3(c) cannot see** [D]. These loops are attributed to a source loop with FP lanes, but §4.7 finds no register or constant-offset-slot accumulator in them:
  - A: 18 of 37 such loops show 0 emitted lanes (`dot16_conv` :355 ×9, :362 ×3, `qtile8` :274 ×2, `qtile16` :295 ×2, `qtile4` :320 ×2).
  - D: 15 of 44 (`dot16_conv` :355 ×9, :274 ×2, :295 ×2, :320 ×2).
  - [inference] The partial sums sit in memory arrays (`L[i & 15]`, `acc[tn]`), which §4.7 does not model.
  - P3(c) can only flag *more* emitted lanes than source lanes, so these loops are **unscreened, not cleared**. Their lane correspondence is an obligation for T1, with no help from X0.
- The narrowing (week 6) is judged per (config, variant, loop id) against X2's `proved_loop_shapes`. The tag sets above are what X2 would have to list.

---

## 9. Sequence-intrinsic lowerings and horizontal helpers

The emitted iclass sequences are located through twin attribution [M, census.json:variants[].sequences, build 1]. They are descriptive. The interleaved instructions of other lines are included as the census recorded them.

- **`_mm256_hadd_epi32`**, the only sequence intrinsic in the files (6 uses, all in `red8`, quant_avx2.c:72-74), is emitted as **VPHADDD in every configuration** (A, A-ninja, B-cmake, C and D). It is never decomposed into shuffles and adds. The cross-lane combine that follows is VPERM2I128, VPERM2I128 and VPADDD (A, C), or VPERM2I128 or VINSERTI128 and VPADDD (B-cmake, D) [M].
- **`tree16`** (the d2 sites):
  - A and C: `VADDPS VEXTRACTF128 VADDPS VMOVHLPS VADDPS VPERMILPS VADDSS`, with a leading `VEXTRACTF64X4 VADDPS` in AVX-512 code.
  - B-cmake and D: `VSHUFPD` in place of VMOVHLPS and `VMOVSHDUP` in place of VPERMILPS. The inlined `canon4` follows (`VCMPSS VBLENDVPS`).
  - D also emits sequences in which several trees are interleaved (VBLENDPS, VSHUFPS; 3 per build) [M]. The d2 results are in §12.
- **`hmax16`, `hmax8`:** the same halving shape with VMAXPS and VMAXSS. A and C use VMOVHLPS and VPERMILPS; B-cmake and D use VSHUFPD and VMOVSHDUP [M].
- **`hsum_i32`, `hsum8_i32`:** VEXTRACTI64X4 and VEXTRACTI128 (C: VEXTRACTI32X4), then VPADDD and VPSHUFD twice [M].
- **`red_quads`, `red_quad1`:** VPUNPCK{L,H}DQ, VPUNPCK{L,H}QDQ and VPADDD; VPSHUFD, VPADDD and VPERMD [M].
- **`canon4`, `canon8`, `canon16`:**
  - VCMPPS with VBLENDVPS (VEX), or VMOVAPS under a mask (MSVC AVX-512), or VBLENDMPS (GCC AVX-512).
  - Clang (D) emits VCMPPS or VCMPSS with VBROADCASTSS [M].
- **`finish16`** (AVX2 scalar tail): separate VMULSS and VADDSS, with no FMA in any configuration (P2 = 0) [M].
- **`_mm512_reduce_*`** (arm P only; Hearth never calls them). The iclass multisets of the by-value `reduce_add_ps` wrapper are below [M, census.json:variants (config P.*)]:

| Arm | Code | `reduce_add_ps` iclasses |
|---|---|---|
| P.A, P.A-ninja | byte-identical code sections [M, configs.P.*.objects] | VEXTRACTF32X8, VEXTRACTF128, VPSRLDQ ×2, VADDPS ×3, VADDSS |
| P.B-cmake | | VEXTRACTF128, VSHUFPD, VMOVSHDUP, VADDPS ×3, VADDSS, with no 512-bit extract ([inference] the Win64 ABI passes `__m512` by reference and Clang loads the halves) |
| P.C | | VEXTRACTF64X4, VEXTRACTF128, VSHUFPS, VPERMILPS, VADDPS ×3, VADDSS |
| P.D | | VEXTRACTF64X4, VEXTRACTF128, VSHUFPD, VMOVSHDUP, VADDPS ×3, VADDSS |

  - The `reduce_max_ps` wrappers follow the same pattern with VMAXPS. P.C's has four VMAXPS and no VMAXSS [M].
  - **Lane pairing against the XML's halving tree was not computed in this run.** The assembler notes it as a report or arm step. Its `sequences` field is empty for the probe [M]. The pre-freeze observation of arm P (record §2 disclosure) is still the only pairing result, and it is pre-freeze data.

---

## 10. P3(c) and the V3 mismatch

### 10.1 Classification of the 29 mismatches

[M, rederive/comparison.json, keyed by variant and header address; one row per loop, both builds merged]

| Side that flags | Config | Variants and loops (source loop, emitted lanes vs bound) |
|---|---|---|
| census only (4) | C | `k_avx512` Q8: quant_avx512.c:316 and :352. `k_avx512` Q4: :316 and :352. Each is 32 lanes against a bound of 0 |
| re-derivation only (25) | A (3) | `k_avx2` Q4: quant_avx2.c:328 (24 over 0). `k_avx512` Q8 and Q4: quant_avx512.c:349 (16 over 0) |
| | B-cmake (9) | scalar F32, F16, BF16: quant.c:371 and :373 (1 over 0 each). scalar act: quant.c:326 (1 over 0). `k_avx2` Q8: quant_avx2.c:270 and :274 (8 over 0) |
| | D (13) | the same scalar loops as B-cmake (7), `k_avx2` Q8 :270 and :274, and `k_avx512` Q8 and Q4 :349 and :291 (16 over 0) |

### 10.2 What each side says, and what census.json shows

- **The re-derivation's 25 flags.** The re-deriver traced these to its own v1 script. v1 counted any location written in the loop as carried, but §4.7 requires the value to be "live into the header along the back edge". Its diagnostic v2 adds that liveness test and removes all 25 [M, rederive/diagnostic_v2/comparison.json: 4 mismatches left, all census-only]. **v2 was written after its author had read census.json, so it is not independent for P3(c)** (§16).
- **The census's 4 C flags.** census.json shows the following [M]:
  - The counted "accumulators" are eight stack slots, STK:RSP:320 to :432 (Q8) and STK:RSP:384 to :496 (Q4), at 4 lanes each. Each slot is its own partial-result cycle. The accumulating instructions are VADDPS and VMULPS.
  - The emitted loops are attributed to quant_avx512.c:316 (`qtile4` token-chunk loop, "acc[] reset per chunk", 0 source lanes) and :352 (the 4-row remainder loop, 0 lanes) [M, loop_table.csv].
  - The inner `qtile4` g-loop, quant_avx512.c:320 (8 `__m128` accumulators, 32 source lanes), is counted at 32/32 under C.
  - This fits the census reading the inner loop's `acc[]` array as carried around the *outer* loops [inference].
  - The re-deriver reports that the array's address is taken (`lea rax/rsi,[rsp+0x140]`; 0x140 = 320). §4.7 admits only "constant-offset, non-escaping" stack slots. That would make these four flags a census over-count.
  - This writer cannot check the escape from census.json, because it holds no instruction text. The check needs the decode dumps on the desktop.
  - [inference] A true split here would mean GCC reassociated under `-O3 -ffp-contract=off` with no value-unsafe flag (P3(a) is clean for C). That would be a compiler defect, not a flag defect, which makes a false positive the likelier reading.
- **Status.**
  - Both explanations are plausible and neither is verified. The census side needs a look at the four loops in the C decode dumps (desktop).
  - If the census is confirmed wrong, the fix is a post-freeze tooling fix of `x0_loops.py`. It needs:
    - an appended amendment that names the script and re-pins it (record §8 item 10);
    - a before/after table of every P1-P5 value (§10);
    - a re-run, before 2026-11-12.
  - The census runner has already handed the lead engineer a conditional audit amendment for this. This report does not duplicate it.

---

## 11. External calls and lift blockers

Build 1; build 2 identical [M, census.json:variants[].lift_blockers, closure].

| Config | External callees (variants calling) | Internal / interposable calls | Indirect branches | Hardening |
|---|---|---|---|---|
| **A** | `__security_check_cookie` (10: scalar F32/F16/BF16, avx2 F32-Q4, avx512 Q8/Q4) | scalar F32/F16/BF16 call `dot16_conv`, `hx_row_bytes`, `mm_float_scalar` (internal) | 1 jump table in each of scalar F32/F16/BF16 (7 entries) | `/GS` cookie reference and check in the same 10 |
| **D** | `memset` (4: avx2 Q8/Q4, avx512 Q8/Q4) | scalar F32/F16/BF16 call `mm_float_scalar` (internal) | 0 | none |
| B-cmake | `__security_check_cookie` (8), `memset` (2: avx2 Q8/Q4) | `mm_float_scalar` (internal) | 0 | `/GS`. The cookie call is `noreturn_inferred` (clang-cl ends the failure path at the function end) |
| C | `__stack_chk_fail` (10) | `hx_row_bytes` **interposable** in scalar F32/F16/BF16, with its `.text.unlikely` cold part (`cold_part_of`) | 1 jump table in each of scalar F32/F16/BF16 (7 entries, `.rodata`) | ENDBR64 at every entry; stack-protector canary in the 10 variants with local arrays |

- Every external callee is on the frozen non-FP allow-list, so `fp_trust_dep` is 0 everywhere [M].
- Under 04 §7.2 step 3 every call and indirect branch is a lift failure. The A and D rows are the lift blockers for the release builds.
- **E5 confirmed** [M]:
  - Under C, `hx_row_bytes` is an interposable call (`-fPIC`, default visibility).
  - The variants with local arrays carry stack-protector code.

---

## 12. Canaries, FP environment, EVEX rounding (E6 label)

Every d1 and d2 result, and the P3(c) results of the scalar F32, F16, BF16 and act variants, carry the record's label: **"outcome indicated before freeze by a verbatim copy (E6)"**. `judge.py` writes the label into `verdict.json:canaries` only after V holds, so the results are reported here from census.json.

| Canary | A | A-ninja | B-cmake | C | D |
|---|---|---|---|---|---|
| d1 (`q_rint` (v + M) − M in `act_q8_scalar`), b1 / b2 | pass / pass | pass / pass | pass / pass | pass / pass | pass / pass |
| d1 pair sites found (b1) | 16 | 16 | 3 | 1 | 3 |
| d2 `tree16` sites, both builds: match / mismatch / unchecked | 36 / 0 / 6 | 36 / 0 / 6 | 24 / 0 / 18 | 36 / 0 / 12 | 46 / 0 / 20 |
| d2 unchecked reasons | an interleaved write to a read register (avx512 F32/F16/BF16, 1 site each) | same | live-in not one 16-lane or two 8-lane registers (2 per variant); off-whitelist (1 per variant) | interleaved write (avx2, 1 each); four 16-lane live-ins (avx512, 1 each) | live-in shape (avx2); off-whitelist (avx2 F32); interleaved write (avx512, 1 each) |
| P3(c), scalar F32/F16/BF16/act (census) | no flag | no flag | no flag | no flag | no flag |
| P3(c), same variants (re-derivation v1) | no flag | none recorded (A-ninja is not a union member) | **flags** :371, :373 and :326 (1 over 0) | no flag | **flags** :371, :373 and :326 (1 over 0) |

All figures in this table are [M], from census.json variants[].p3.d1, d1_sites, d2 and p3.c, and from rederive/comparison.json.

- **E6 as registered.** d1 passes everywhere, and no d2 site is `mismatch` [M]. "Every site matches" does **not** hold in the strict sense: 6 to 20 sites per configuration are `unchecked` [M]. Unchecked sites are reported and not flagged, and they prove nothing.
- **Pass caveat.** The caveat registered for "every expected d2 site under A or D unchecked" does not apply: A has 36 `match` and D has 46 [M].
- **Widened E6** ("P3(c) flags no loop of the scalar F32, F16, BF16 and act variants"). This holds on the census side [M]. The re-derivation v1 disagrees under B-cmake and D, through the liveness bug of §10.2. The v2 diagnostic agrees with the census.
- **Clang's d1 form** [inference from the iclass lists in §6.3]. Under B-cmake and D the scalar act variant has no SUBSS. The pair is found as ADD of M followed by ADD of −M, which d1 accepts as identical by IEEE.
- **FP-environment instructions** (LDMXCSR, STMXCSR, FLDCW, FXRSTOR, XRSTOR* and the rest): **none** in any counted set [M, census.json:metrics.secondary.fp_environment_iclasses_in_counted_sets = []]. The kernels inherit the caller's MXCSR (§17).
- **EVEX static rounding or SAE on register operands:** 0 instructions in every variant [M, metrics.secondary.evex_static_rounding = {}; variants[].evex_static_rounding all 0]. No rounding-override table entry is needed.

---

## 13. Proxy fidelity (B-proxy against D), for X3

[M, census.json:metrics.secondary.proxy_fidelity, build 1; build 2 identical]. "Tag agreement" is how far the two builds' loop tag sets agree.

| Variant | Jaccard (iforms) | Tag agreement | Variant | Jaccard | Tag agreement |
|---|---|---|---|---|---|
| scalar F32 | 0.9794 | 0.9231 | avx2 Q8 | 0.7692 | 1.0 |
| scalar F16 | 0.9794 | 0.9231 | avx2 Q4 | 0.7822 | 0.9 |
| scalar BF16 | 0.9794 | 0.9231 | avx2 act | 0.898 | 1.0 |
| scalar Q8 | 0.9277 | 0.8571 | avx512 F32 | 0.931 | 0.9444 |
| scalar Q4 | 0.9348 | 0.8571 | avx512 F16 | 0.9333 | 1.0 |
| scalar act | 0.9385 | 1.0 | avx512 BF16 | 0.9333 | 1.0 |
| avx2 F32 | 0.9479 | 1.0 | avx512 Q8 | 0.7937 | 0.7222 |
| avx2 F16 | 0.931 | 1.0 | avx512 Q4 | 0.7692 | 0.7222 |
| avx2 BF16 | 0.9412 | 0.9259 | avx512 act | 0.5424 | 1.0 |

- The lowest iform agreement is in the quantised kernels (0.77 to 0.79) and in AVX-512 act (0.54). The lowest tag agreement is AVX-512 Q8 and Q4 (0.72) [M].
- [inference] The Win64 ABI (callee-saved xmm6 to xmm15, `/GS` cookies, `__m512` by reference) accounts for part of the gap; record §3 anticipated it.
- So B-proxy is a usable but imperfect proxy for D. On these figures X3 should not treat a B-proxy result as a D result for the quantised kernels [D].

---

## 14. Defect drafts

Nothing has been filed. Whether to file either draft upstream is Pierce's decision (record §8, D0_BRIEF HM-9). The record's own files, `results/flag_defect_<config>.md` and `results/build_defect_<config>.md`, are due when the corresponding row holds. No row holds yet (the verdict is `tooling_failure`), so the drafts sit here.

### 14.1 Flag defect, B-cmake (P3(a1); Amber (b) once V holds) — draft Hearth issue text

> **clang-cl builds of the quant kernels compile with FP contraction enabled (`-ffp-contract=on`)**
>
> At b5d3f14, `CMakeLists.txt`'s `if(MSVC)` branches (lines 39-41 and 52-54) also apply to clang-cl. A clang-cl build therefore gets `/fp:precise`, `/arch:AVX2` or `/arch:AVX512`, and no `-ffp-contract=off`. Clang's C default is `-ffp-contract=on`, and the expanded cc1 lines of `quant.c`, `quant_avx2.c` and `quant_avx512.c` all carry it (`clang-cl -###`, LLVM 23.1.3). Hearth's strict-FP policy forbids contraction: the GCC and Clang branches pass `-ffp-contract=off`.
>
> Measured effect at b5d3f14: none yet. The clang-cl objects of `quant.c` and `quant_avx2.c` contain no FMA-class instruction. Their instruction-form multisets are identical to a clang-cl build with `-ffp-contract=off`. The file compiled for AVX2 targets `haswell`, which has FMA, so the flag is a latent defect: a source change that writes `a*b + c` in one expression would be contracted in clang-cl builds only.
>
> Suggested fix (to be verified): in the clang-cl case, pass `-ffp-contract=off` (for example as `/clang:-ffp-contract=off`, or with a `CMAKE_C_COMPILER_ID STREQUAL "Clang"` test inside the MSVC branch). Then confirm with `clang-cl -###` that the cc1 line carries `-ffp-contract=off`. clang-cl is not a shipping compiler for Hearth (MSVC and Linux Clang are), so this affects developer and CI builds that use clang-cl.

Evidence:
- [M] census.json:configs.B-cmake.p3a and p3a_hits ("cc1", "-ffp-contract=on") for all three files.
- [M] metrics.p2.B-cmake = 0.
- [M] cc1 `-target-cpu haswell` for quant_avx2.c.
- [D] B-cmake and B-proxy have identical iform multisets for the 12 variants of quant.c and quant_avx2.c.

### 14.2 Build defect, B-cmake (row N2) — draft Hearth issue text

> **`quant_avx512.c` does not compile with clang-cl: `_mm512_dpbusd_epi32` needs AVX512-VNNI, which `/arch:AVX512` does not enable**
>
> With Hearth's own CMake lines for clang-cl (LLVM 23.1.3; `/arch:AVX512` expands to `-target-cpu skylake-avx512`), `engine/src/quant_avx512.c` fails in `dot_quad` at lines 237-240: "always_inline function '_mm512_dpbusd_epi32' requires target feature 'avx512vnni', but would be inlined into function 'dot_quad' that is compiled without support for 'avx512vnni'". The failure is deterministic: two clean builds give the same four errors. MSVC (`cl` 19.44, the same `/arch:AVX512`) compiles the file. GCC 13.3 and Clang 23.1.3 on Linux also compile it, because the CMake Linux lines pass `-mavx512vnni`.
>
> Suggested fix (to be verified): give clang-cl the VNNI feature for this file, for example with `/clang:-mavx512vnni`, matching the Linux `-m` flags, or a target attribute on the VNNI helpers. Also check that the AVX-512 table is selected at run time only when the CPU reports AVX512-VNNI, which this census did not examine.

Evidence:
- [M] census.json:builds[B-cmake, quant_avx512.c, b1 and b2]: rc 1; 4 errors at lines 237-240; `compiler_ran` and `argv_matches_frozen` true; no ICE; 156 includes.
- [M] cc1 `-target-cpu skylake-avx512`.
- [M] C and D argv include `-mavx512vnni`.

Consequence for the census [M]: B-cmake's six `k_avx512` variants are absent (row N1). The B-cmake union is a lower bound. B-cmake is still screened by P3(a) on all three files (record §8 item 2), which is why Amber (b) can hold for it.

### 14.3 Configuration C (P3(c)): no draft

The four C flags are under audit as a probable census over-count (§10.2). If the audit confirms them as true accumulator splits, the matching draft would be a **compiler** report against GCC 13.3 (reassociation without permission under `-ffp-contract=off` and no value-unsafe flag), not a Hearth flag defect. In that case Amber (b) for C would still stand under the strict reading of OQ-4.

---

## 15. X2 table scope

`results/x2_scope.json` (written by this report step; sha256 `a8058763…2422`) [D from census.json [M]] lists:
- the 446 iforms of U_all, each with iclass, XED extension, category S/G, FP-sensitivity, op_class, the configurations and variants that emit it, whether a release configuration (A or D) emits it, and whether it is in B_iform;
- the 222 iclasses;
- the 32 FP-sensitive iclasses.

It is the census union as X2's scope list (record §11, DR-008), with these qualifications:
- **It is a draft scope, from an UNSIGNED `tooling_failure` verdict.** The union itself is not in dispute: U_all, P5 and the iform and FP-sensitive sets match the re-derivation exactly [M]. It becomes the signed scope only with the verdict.
- **If Amber (a) holds at signing,** record §8 limits the table to the release configurations. That subset is **384 iforms and 31 FP-sensitive iclasses**, the entries marked `release: true` [D].
- **No rounding-override entries** are needed (0 EVEX static rounding or SAE), and **no FP-environment instruction** is in scope [M].
- **S-helpers addendum: missing.** Arm S-helpers (`hx_sum16`, `hx_dot16`, `hx_rmsnorm`, …) was not run, so the "marked addendum" of §11 is an empty placeholder in the JSON.
- **For X2's semantics, beyond the iform list:**
  - the operand-order dependence of MAXPS, MAXSS, MINPS and MINSS (Hearth relies on "NaN in the first operand is skipped"). This was not measured: `variants[].operand_order` is empty [M];
  - the MXCSR state that every FP-sensitive iclass inherits from the caller.

### Proposed amendment text (for the lead engineer; not applied)

The verdict does not need this text. Record §5 and §3 list the following secondary and descriptive outputs, and run 1 did not produce them. If the lead engineer wants their deferral on the record, a possible appended text is:

> *Amendment X0-A? (post-data, descriptive only; no unit, threshold or configuration changes).* Census run `census-20261017T141025Z` did not run the secondary arms H-A, H-D, S-helpers and S-object. It did not compute the operand-order record (§5, `variants[].operand_order`), the arm-P lane pairing against the XML halving tree, or the per-loop register reuse. The report does not state whether the desktop Hearth R3 working tree touches a dispatched kernel (§2), because the census agents were barred from that tree. These outputs cannot change the verdict (§3 "Secondary arms"). They are deferred to a later run against the same objects or the same frozen lines, and X2's scope addendum (§11) waits for arm S-helpers. The operand-normalised delta of §5 is computed in REPORT.md by the rule stated there, which is not frozen and is descriptive only.

---

## 16. Threats and residual risks

1. **V3 is unresolved, and the clock runs.** The 29 P3(c) mismatches must be settled by 2026-11-12. Otherwise rule (iii) extends Amber (b) to A and D through flags that the re-deriver itself attributes to its own v1 bug (§2.3).
2. **Re-derivation independence for P3(c).** The diagnostic v2 that removes the 25 flags was written after its author had read census.json [M, re-deriver's return]. A V3 match built on v2 would not meet PROCEDURE §1 for P3(c). The lead engineer has three options:
   - commission a fresh independent context to fix the liveness test from the record text alone;
   - rule that a bug fix confined to §4.7's stated liveness condition is admissible, and label it;
   - accept the conservative resolution.
3. **Same-family re-derivation** (Claude, independent context) is weaker than ROADMAP's different-family requirement. This is labelled throughout (record §9).
4. **P3(c) is blind to memory-held accumulators.** These shapes are unscreened, not cleared (§8.2):
   - 18 of 37 (A) and 15 of 44 (D) emitted loops attributed to FP-accumulating source loops show 0 emitted lanes [D];
   - they include `dot16_conv`'s 16-lane `L[]` and the 64-, 128- and 32-lane `qtile` accumulator arrays.
5. **P3(c) may also over-count.** The census itself may over-count on stack arrays whose address escapes (§10.2). This is unverified and needs the desktop decode dumps.
6. **d2 coverage is partial.** The unchecked `tree16` sites are A 6 of 42, B-cmake 18 of 42, C 12 of 48 and D 20 of 66 (both builds) [M]. They are neither flagged nor shown to match.
7. **Pre-freeze exposure (E6).** The d1 and d2 outcomes and the scalar P3(c) outcomes were indicated before freeze through verbatim Hearth text in the first mock and in `smoke_dispatch.c`. Three §4.7 rules were tuned on flags of such shapes (record §2, §8 E6). The label is carried in §12.
8. **One host, one run, one toolchain pin.** Repeatability holds within the desktop: builds 1 and 2 are identical [M]. Nothing is shown for other compiler versions, flags, hosts or Hearth commits.
9. **Lower bound for B-cmake.** 6 variants are uncompiled (N1).
10. **Missing secondary outputs.** These are listed in §15: H arms, S-helpers, S-object, operand order, arm-P pairing, register reuse and the R3 statement. Two of them, the MAXPS operand order and the MXCSR inheritance, bear directly on Hearth's NaN and rounding claims.
11. **Heuristic analyses.** Jump-table recognition, the no-return inference, the d1 constant tracker and the carried-value data flow are deterministic but heuristic (record §9). V3 is the check on them, and V3 has not passed.
12. **Report-step rules.** The operand-normalised delta (§5.2) uses this writer's rule. It is descriptive and gates nothing.
13. **Operations.** A stale local `main` was bypassed by bundling the branch that contains the freeze commit, and the bundle hashes match. One failed step-82 call wrote nothing. Neither affects the data [M, §3], but both are recorded.

---

## 17. What X0 does not show

X0 **screens**; T1 **proves**. This census does not establish any of the following.

- **It does not show that the emitted objects are free of reassociation.** P3 can detect certain signatures:
  - contraction flags;
  - approximation iclasses;
  - more accumulator lanes than the source;
  - a broken (v + M) − M canary;
  - a mis-paired `tree16` inside a small whitelist.

  A reassociation outside those signatures passes unseen: inside memory-held accumulators, outside the whitelist, or in straight-line code. Even a full Pass would leave this question to the B1.5 object audit (record §8 Pass row, OQ-3).
- **It does not show that any emitted sequence is semantically equal to its source.** A `match` on a d2 site means the lane pairing equals the s = 8, 4, 2, 1 tree up to commutation of each add. It is not a proof of the whole kernel. Lockstep and rotated tags describe loop shape, not value equivalence.
- **It does not cover code outside the 18 variants' closures**: the helpers, the rest of the objects, or the linked `hearth.dll` (linker folding or layout). It also does not cover the hxcc build path.
- **It does not establish the run-time FP environment.** No kernel sets MXCSR [M], so every FP-sensitive instruction depends on the caller's MXCSR.RC, DAZ and FTZ, which X0 does not observe.
- **It does not test behaviour.** No kernel was executed and no numeric output was compared.
- **It says nothing about compilers, versions or flags other than Table 2.1's.** Nor about Hearth commits other than b5d3f14, or the uncommitted R3 working tree.
- **Its verdict is not final.** V3 fails, the verdict is unsigned, and the narrowing waits for X2 at week 6.

---

## 18. Open items

1. **Lead engineer: resolve V3 before 2026-11-12.**
   - Audit the 4 C loops (census side) against the desktop decode dumps (`D:\mithril\x0census\run1\C\b{1,2}\all\decode\`).
   - Decide how the re-derivation's liveness fix may enter (§16 item 2).
   - Then make any tooling fix under an appended amendment, with a before/after table and a re-run.
2. **Pierce, at the sitting:**
   - sign or withhold the verdict (D0-12);
   - decide whether to file §14.1 and §14.2 upstream (HM-9);
   - answer OQ-4 if he wishes (it decides whether a B-cmake or C defect makes X0 amber).
3. **Write `results/flag_defect_B-cmake.md` and `results/build_defect_B-cmake.md`** from §14 once the verdict has V true and the rows hold.
4. **Run the secondary items** listed in §15's proposed amendment, or record their deferral:
   - arms H-A, H-D, S-helpers (the X2 addendum) and S-object;
   - operand order;
   - arm-P lane pairing;
   - register reuse.
5. **State whether the desktop Hearth R3 working tree touches a dispatched kernel** (record §2, PLAN R9). This needs Pierce's permission to read that tree, read-only.
6. **Narrowing at week 6**, jointly with X2's `proved_loop_shapes` (§8).

---

## 19. Files

| File | sha256 | Role |
|---|---|---|
| `results/census.json` | `3d54f0d50862e359b20e1c50904f7218092d27f680b9b2175891fb65dbef6f06` [M] | census ledger (Appendix C) |
| `results/verdict.json` | `56a68a7d4412b5f6c48bbf66ea27463be76b5feb0367730794317ba9d7ca34a9` [M] | computed verdict, UNSIGNED |
| `results/run.json` | `2c83bf7231c058d0e595479b29cbca2e4b757c67c84c4aaad3014d6d6e8ac401` [M] | init record |
| `results/run1_files.sha256` | `7fef9db36811e2712efa90e12fa112dff613b108dee4be17b307df5f78ee084e` [M] | manifest of the 1,308 desktop files |
| `results/summaries/`, `results/joblogs/`, `results/decode_dirs.txt` | none | per-configuration summaries and job logs |
| `results/rederive/figures.json` (= `rederive/figures.json`) | `c5cc075f…` [M] | re-derivation figures (v1, frozen) |
| `results/rederive/comparison.json` | `ccf54e99…` [M] | the 29 mismatches |
| `results/rederive/census_with_rederivation.json` | `d39ed903…` [M] | census.json plus the `rederivation` block |
| `results/rederive/verdict.json` | `1a8d4669…` [M] | `judge.py` on the above, UNSIGNED, `tooling_failure` |
| `results/rederive/diagnostic_v2/` | `0f2686ce…` (comparison) [M] | v2 diagnostic, not independent for P3(c) |
| `rederive/rederive_x0.py`, `rederive_x0_v2.py`, `compare_x0.py` | `fb573c3e…`, `eab24c4e…`, `376c1f75…` [M] | re-derivation scripts |
| `results/x2_scope.json` | `a805876364cd088059fdc01ec326ffe580c6c74a4e30059e3e5e4eb082ad2422` [M] | X2 scope list (this report step) |

Nothing has been committed or pushed. The record body was not edited.

---

## 20. Review log

The report writer's text was blocked from disk by the agent harness ("Subagents should return findings as text"). The
lead engineer wrote it to this file verbatim on 2026-10-17 (sections 1-19 above, unchanged). The adversarial reviewer
(Claude, same family, independent context, 2026-10-17) therefore reviewed the results without the report text. Its
nine findings and the lead engineer's dispositions:

| # | Severity | Finding (abridged) | Disposition |
|---|---|---|---|
| 1 | blocker | REPORT.md absent | Resolved: written verbatim from the report writer's return (above). |
| 2 | major | The 29 P3(c) mismatches are tooling artefacts on **both** sides. The reviewer sampled 4 of 29. On the census side it traced C's 4 flags to `x0_loops.py` not treating GCC's `rep stosq` zeroing of `acc[]` as a kill. The re-deriver traced the same 4 flags to an address-taken stack array (`lea …,[rsp+0x140]`) that §4.7 excludes as escaping. The other 25 are unexamined by the reviewer; the re-deriver attributes them to its own v1 liveness bug | Accepted. §10 already reports the outcome as `tooling_failure` (V3) only. Both diagnoses of the census-side flags are candidate causes. The tooling fix must handle both, and its before/after table must show which one applied. |
| 3 | major | The way out must stay inside the frozen procedure. `rederive_x0_v2.py` was written after reading census.json, so it cannot satisfy V3. The current re-deriver has seen census outputs. Any census-tooling fix needs an appended amendment, a re-pin and a re-run | Accepted. Plan: (1) Amendment X0-A1 (post-data, tooling only) appended to the record, naming the `x0_loops.py` change; (2) re-pin, unit tests, regression replay; (3) census re-run from the amended commit; (4) a **fresh** re-deriver in a new context that has not seen any census output writes its own script from PROCEDURE.md; (5) `judge.py`. Due before the week-3 bound, 2026-11-12. |
| 4 | major | Overclaiming risk: Amber (a)/(b)/(c), N1 and N2 are not outcomes of this run | Already satisfied: §1 and §2.3 label every row "preview [D], not a verdict". |
| 5 | minor | The E6 label must appear in the report, because `verdict.json` has no canaries block on an early return | Already satisfied: §12. |
| 6 | minor | Arms not run and metrics not computed must be listed | Already satisfied: §6, §9, §15 (proposed Amendment X0-A?), §16. |
| 7 | minor | Both B-cmake defects belong to Hearth's `CMakeLists.txt` (`if(MSVC)` also matches clang-cl), not to clang-cl | Already satisfied in §14.1-14.2 wording. Nothing is filed; Pierce decides. |
| 8 | minor | Disclose the failed and re-issued step 82, and the WSL keepalive | Already satisfied: §3 operational notes 2 and 3. The keepalive (`sleep 14400`) expires by itself about 11:10 PT. |
| 9 | minor | `x2_scope.json` has untagged figures and anticipates Amber (a) | Accepted. To be fixed with the X0-A1 re-run outputs. |
