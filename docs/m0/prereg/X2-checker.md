# X2: T1/T2 checker spike on transliterated Hearth kernels

Status: DRAFT, **freeze-ready revision 4 (2026-10-23, x2freeze track)**. No data may be collected under this
record. It becomes FROZEN at the commit that first adds it with this line changed to FROZEN. Revision 3 absorbed
X0 census run 1 into the table, applied the DELEGATED rows that answered this record's questions (P9, P10, P14,
P28-P34, P62), corrected one table reading (B6, §2.1), rebuilt the harness and re-ran its self-tests and the
development smoke. Revision 4 applies the same-family, independent-context review of revision 3 (§12: 9 findings,
8 fixed here, 1 for the lead engineer): the strict reading of O4 until Pierce ticks the carve-out, the cited
working-document sections pinned at the freeze commit (§2), the iclass split of O1, P28's extension named, the legacy
compare-immediate domain, a sticky-bit construction for the 64-bit conversion, P1-P6 in `verdict.json`. The harness
was rebuilt and every self-test, the guards and the development smoke re-run on it [M, 2026-10-23]. One thing
stands between this text and the freeze commit: Pierce's answer on the scope reading of §13 item O1. Everything
else that is still Pierce's (§13) is registered here with a default and can be answered before the point the record
names. Revised 2026-10-16 after two same-family reviews (§12).
ROADMAP anchor: [§3.3](../../ROADMAP.md#33-x2-t1-spike-on-transliterated-hearth-intrinsics-weeks-05-verdict-in-week-6);
DR-008, DR-010; [03-trust §6](../../architecture/03-trust.md); kill outcomes ROADMAP §4
Owner authorisation: none recorded for X2. Under the
[collection rule](../README.md#pre-registration-lifecycle-roadmap-1-rule-1-d0-12), no fuzz vector, mutant or T1
verdict run counts until this record is FROZEN and SIGNED (D0-12; batch 3 allows the interim chat form), or
FROZEN and covered by an explicit Owner instruction naming X2.
Working documents: [experiments/x2-semantics/](../../../experiments/x2-semantics/) (TABLE-SCHEMA, FUZZ-DESIGN,
MUTANTS, RULES, `semantics/`, `harness/`, `census/`, `scripts/`).

## 1. Assumption under test

A small T1/T2 checker accepts Hearth's real kernels and rejects wrong ones (ROADMAP §3.3). If this is
false, the validated-bit-identity claim (N2) dies: kernels carry `tested` evidence plus the hash
corpus, and the project continues only if X1 and X3 pass (ROADMAP §3.3 Kill; §4: "X2 kill alone" is
NARROW, "X1 kill and X2 kill" is STOP-ALL, "X2 kill and X3 kill" is STOP-L).

## 2. Inputs pinned

- **Hearth.** `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220` (GitHub `main`, 2026-10-16), the same pin as
  X0. Files: `engine/src/quant.c`, `quant_avx2.c`, `quant_avx512.c`, `hx_quant.h`; `docs/NUMERICS.md`;
  `tests/golden/` and `engine/tests/`, `tests/py/` for the mutant arms. The desktop working tree's
  uncommitted changes are out of scope.
- **Census: X0 census run 1, by hash.** Run `census-20261017T141025Z` at X0's freeze commit `152fa33`:
  `experiments/x0-census/results/census.json` sha256 `3d54f0d50862e359b20e1c50904f7218092d27f680b9b2175891fb65dbef6f06`;
  X0's scope list `results/x2_scope.json` sha256 `a805876364cd088059fdc01ec326ffe580c6c74a4e30059e3e5e4eb082ad2422`;
  the build-1 `instructions.jsonl` of A, B-cmake, C and D (sha256 `12cd20e6…e2f2`, `fa1fcd5a…9412`,
  `b8aabbf1…75c7`, `428ebfc0…1c0d`, equal to X0's `results/run1_files.sha256` [M, 2026-10-23]). Using run 1's
  union as this table's scope is the registered flow (DR-008; X0 record §11). **X0's verdict is not final**
  (UNSIGNED `tooling_failure`, V3 false over P3(c) loop flags); the union itself matched X0's independent
  re-derivation exactly (U_all 446, P5_iclass 32, the iform and FP-sensitive sets) [M, X0 REPORT §1].
  `census_absorb.py` re-derived the same union from the instruction records and cross-checked it against
  `x2_scope.json`: iform sets equal, FP sets equal [M, 2026-10-23, `census/coverage_run1_*.json`].
  **Re-scope rule.** If X0's re-run or its signed verdict changes the union, `census_absorb.py` is re-run on it:
  every FP-sensitive form it adds gets an entry and the rows `budget_rows` gives it (§4 item 12), and every other
  added form gets a disposition (§4 item 9). Before the first budget vector this is a pre-data amendment. After
  collection has started, forms and rows are only ever added, never removed (amendment marked post-data, the
  verdict reported both ways, §10). X0's arm S-helpers has not run; its addendum is handled the same way.
- **XED.** X0's pinned XED (v2026.08.23, `0bcb6237345c5066726dcc08b3d87928df3b5b26`, in X0's
  `TOOLCHAINS.md`).
- **Semantics table.** 114 entries; semantics bundle `0c2a041c363e34ee27a62a873fd0adad5cf8f5711ec2aa3a16cb2f5c9709ff2d`
  at revision 4 [M, `python -B -m semantics.table`, laptop and desktop, 2026-10-23]; every entry's content hash is in
  `experiments/x2-semantics/census/table_index.json` (sha256 `35825c1e…ed73`). The printout at the freeze commit
  is authoritative. The bundle includes `table.py`, and every entry's wiring is a hashed declarative `sem` spec
  (TABLE-SCHEMA §7). Written from the SDM only, never derived from Intel's intrinsics XML (DELEGATED P14).
  Compare immediates have a declared domain: the legacy CMPPS and CMPSS entries carry `imm_max: 7` in their `sem`
  spec (SDM: imm8 bits 7:3 reserved) and the VEX and EVEX compares take imm8 0-31; outside it an entry gives no
  prediction (the reference raises, the C interpreter refuses) [M, self-tests E10 and x2fuzz step 4b, 2026-10-23].
- **Intrinsic map.** `intrinsic_map` v0 (`INTRINSIC_MAP_V0` and `SCALAR_C_MAP_V0` in `semantics/hearth_kernels.py`),
  sha256 `4aa8e2c5e0afeb35cbfebacd50091bfb2dcd4e1efd45d9c9dc35a5ab7d64d1d0`. **Checked against census run 1**
  [D, 2026-10-23]: every FP-sensitive iclass in the dispatched closures is named by the map, up to the VEX/legacy
  spelling, except four that compilers introduce from scalar C by if-conversion or vectorisation and that no
  intrinsic denotes: VCMPSS (B-cmake and D, AVX2 F32/F16/BF16; D, AVX-512 F32/F16/BF16), CMPSS (scalar variants
  under B-cmake and D), MINSS (scalar act under A, B-cmake, D) and CVTTPS2DQ (scalar act under B-cmake and D).
  They have table entries and budget rows; T1 at intrinsic level never consumes them (a C select is C
  semantics). **`intrinsic_map.v1`** = the 130 source rows of v0, unchanged, plus the rows of every intrinsic a
  mutant operator introduces (MUTANTS.md §2), added and hashed with `rules.v1` before the pool is sealed.
- **Rule list.** `rules.v1` (the rows of RULES.md §3.1 as frozen), with `loops.v1` (RULES.md §5)
  and `kir_family_map.v1` (RULES.md §1), by hash, frozen **before** the mutant pool is revealed to T1.
- **Meanings.** The KIR meanings of every host T1 runs on, transcribed from NUMERICS.md and the C
  scalar code with one convention: a C idiom that implements a NUMERICS operation is transcribed as
  that operation (`q_rint` → round-half-even, `q_f16` → f16 widening, `q_bf16` → bf16 widening,
  `q_canon` → `canon::nan`, `v != v` → `isnan`), and everything else literally, in the C operand
  order. Hashed with the **meaning interpreter** (Python, exact IEEE binary32 evaluation of KIR under
  Env = default).
- **Mutant pool.** Generated and sealed per MUTANTS.md §3; its hash is appended to this record as a
  dated amendment at sealing, before any T1 run on it. The meaning mutants (MUTANTS.md §2) are sealed with it.
- **Seeded table mutants** (calibration arm A5, FUZZ-DESIGN §6.4): `harness/mutants/mutants.py`, spec sha256
  `a74d50412a976ececc9355ff2434e3d7c3c08c40eea9f0627378dc4a6ab2802c` (24 mutants; per-mutant hashes in
  `harness/devlogs/mutants_devsmoke.summary.20261023d.json`). All 24 still apply to the revision-4 table [M, laptop
  anchor check and desktop run, 2026-10-23].
- **Vector budget.** `experiments/x2-semantics/census/budget.v1.json`, sha256
  `7b905f54cd56a1adf7e6b382656c7c8866b05b76cb33975e6721d903077c5258`, generated by
  `semantics.census_absorb.budget_rows` (file sha256, LF, `a5b82957ba982792607f60a10dad4e99d2af1d94abafd09aea13863612c89ef4`)
  from the revision-4 table; 610 rows (§6), the same rows as revision 3's (only the semantics bundle in its header
  changed) [M, 2026-10-23]. It becomes `budget.v1` unchanged at the freeze commit.
- **Native harness** (rebuilt 2026-10-23 for revision 4, [M] desktop): stub manifest sha256
  `430fc5266ef730afb2d280ce3d1c0bf9c701b6ebd80ee7d9ea98083108876260` (664 stubs, 0 encode or decode-back errors,
  every stub decodes to its entry's key); `x2fuzz.exe` `0feae9334e9ba51bcae3bfa43bdbe1d9d3544a3295ce821bb5be9b8550dcde4c`;
  interpreter sources `44e29a371dfb0799804fcbaf9fc36d8781f2de6efb5d275acac800d4dbada17c`; harness sources
  `a17f41baf1b6ca886a5273dab63a3b1925df57a16df16f6bb1c53811ad2eb112`; generator `harness/gen_vectors.py`
  `4261242d38952a1487819c8aa1b17bdd103e7d55f3bb6736f8282ac5245aa6e2`; Python reference `harness/pyref.py`
  `e962133be4da5b30e62704f8d8c99ef1e985d3fdcd2fa3fcd482d5971c03e964`; comparator `harness/compare.py`
  `65f462a15ff207a7e011f5a42ce7bb2a0a25428e18a1b360dc417624a71b0386` (LF sha256). Every vectors and results
  file names the hashes it was made with; a later change is logged (§10).
- **Native builds.** Witness confirmation and the G and C arms use **X0 configuration A** (MSVC with
  Hearth's own flags); configuration D is built and reported as secondary.
- **Machines.** Silicon of record: the desktop (AMD Ryzen 9 9950X, family 26 model 68 stepping 0, microcode
  `0x0B404023`, Windows 26200.9711) [M, 2026-10-23 fingerprint]. The fingerprint is recorded with every result.
  The laptop (Ryzen 9 7940HS, Zen 4) is not a source of record.
- **Second oracle.** Bochs 3.1 (`REL_3_1_FINAL`, tag commit `30cfd566ecc8deb33e56e801e32b444a7041b6d2`), built
  from the release's `bochs-3.1-msvc-src.zip` (sha256 `3453bb34…34b3`, the published digest) with AVX and EVEX
  enabled; our `bochs.exe` sha256 `1f45343a…efc9`; CPU model `sapphire_rapids` (harness/bochs/README.md). The
  pre-registered fallback of §10 applies if its production image is not running by the end of week 3.
- **Tools.** MSVC `cl` 19.44.35229 (toolset 14.44.35207, SDK 10.0.26100.0) and `ml64` from that toolset, as
  pinned in `experiments/x0-census/TOOLCHAINS.md`; Python 3.13.4 (`C:\Python313`) for the harness and Gatekeeper
  scripts on the desktop, Python 3.12.10 for the reference on the laptop; z3-solver 5.3.1.0 and cvc5 1.4.2 (PyPI
  wheels, digests in proofs/README.md §1). **Bochs boot image:** the 2026-10-16 probe was assembled with GNU
  binutils 2.42 in WSL. WSL may not be started on the desktop until Pierce decides on the C: budget, so the
  production image is assembled with X0's pinned LLVM 23.1.3 Windows build on D: (`clang` integrated assembler,
  `ld.lld`, `llvm-objcopy -O binary`) unless Pierce re-allows WSL (§13 O7).
- **Working-document text.** Every working-document section this record cites for a definition, a counting rule
  or a procedure is part of this record **as it stands at the freeze commit**: FUZZ-DESIGN §2-§6 (lane case,
  execution, observables, flag isolation, value and targeted classes, E8, mask patterns, the budget's row formulas,
  the second oracle, triage, calibration), MUTANTS.md §1-§4, §6 and §7, RULES.md §1, §3.1, §4.0 and §5,
  TABLE-SCHEMA §4, §7, §8.1 and §9.1, and harness/README.md §4. A later edit to any of them changes nothing here
  except by an amendment (§10); where a later text and the frozen one differ, the frozen one governs.

### 2.1 Pre-freeze disclosures

1. **Development silicon seen before freeze** (none of it a budget row, none of it evidence for a grade): the
   2026-10-16 dev smoke (800 executions), the review cross-section DEV-REVIEW-X2BUILD (4,528 executions), the
   exhaustive-engine plumbing checks (40, now 42, stubs × 4,096 fixed inputs, repeated by every self-test run), and
   the 2026-10-23 dev smoke on the rebuilt harness (1,593 executions; 0 lane or flag mismatches, 0 divergences,
   CPU 4 and CPU 20 identical) [M, `harness/devlogs/*.20261023.*`], repeated on the revision-4 harness with the same
   1,593 hand-vector executions and the same result [M, `harness/devlogs/*.20261023d.*`].
2. **B6, a table reading settled with that data.** The reading "a denormal divided by ±0 raises DE and ZE" (v0,
   TABLE-SCHEMA §4 rule 7, uncertainty class F-FLAGPRI) disagreed with the 9950X on four development vectors
   (`0x00000001 / +0` on VDIVSS EVEX, VDIVSS VEX and DIVSS; `0x004C24E3 / +0` under RZ, `0x8078165D / −0` under
   RZ, `0x80717657 / +0` under FTZ): silicon sets ZE alone, on both CCDs; Bochs 3.1 also sets ZE alone on the
   first [M, harness/README.md §7, §10]. That is the "table bug" row of FUZZ-DESIGN §6.3 (table ≠ silicon =
   Bochs), and it matches the SDM's priority list read correctly (divide-by-zero is level 3, denormal operand
   level 4; both are pre-computation exceptions) [inference]. Revision 3 corrects the table: ZE alone
   (`fp_ops.div`, `x2ref.c`; self-test B6 now checks all four silicon vectors). The class F-FLAGPRI still runs
   in full under `budget.v1`; P5 is judged on the complete final rerun (§4 item 8), so the correction gives
   no exemption.
3. **Census run 1** (an X0 result) was read in full to absorb it; that is this record's registered input.

## 3. Arms / configurations

| Arm | What | Role |
|---|---|---|
| **A1 T1 on real variants** | T1+T2 on the transliterated intrinsic-level IR of the gating variants (§4.1) against their meanings | gate (P1, P2, P4, P6) |
| **A2 Fuzz** | every table entry in scope (§4 item 9) on the 9950X against the table's predictions, with Bochs as second oracle, under `budget.v1` and §4 item 12 | gate (P5) |
| **A3 Mutants** | the sealed `numerics_v1` pool under G, C, G+C and T1+T2 (MUTANTS.md §4), T1 run on every host of P3's denominator (§4 item 5) | gate (P3, P4) and honest reporting |
| **A4 Secondary variants** | T1+T2 on the F16 and BF16 SIMD variants, the six scalar variants and the `hx_*` helpers | P1: no effect (DELEGATED P30). Their acceptance decides whether their mutants can count as killed in P3 (P31) |
| **A5 Table calibration** | the 24 sealed seeded table mutants against the frozen budget's silicon results (FUZZ-DESIGN §6.4) | secondary, no gate effect; target: every §6.4 mutant detected [target, secondary] |
| **A6 Meaning-mutant control** | about 10 meaning mutants against the unmutated variants (MUTANTS.md §2) | secondary, no gate effect |

X2 checks the transliterated intrinsics, not compiled objects; the object audit is M2 (DR-008).

## 4. Units and counting rules (defined before data)

1. **Real variant (gating set).** The AVX2 and AVX-512 variants of `mm_q4`, `mm_q8`, `mm_f32` and
   `act_q8` in Hearth's `k_avx2` and `k_avx512` tables at b5d3f14: **8 variants**, the kernels ROADMAP
   §3.3 names. `mm_f16` and `mm_bf16` (4 SIMD variants) and the 6 scalar variants are arm A4 (DELEGATED P30).
2. **T1 accepts a variant** when all hold: (a) T1's verdict is ACCEPT for the variant against its
   meaning on the declared domain; (b) its witness replays in an independent replay script; (c) its
   premises are only of these kinds:
   - rows of `rules.v1` at their frozen hash;
   - loop rules of `loops.v1` (RULES.md §5), frozen and hashed with `rules.v1`, each with its written
     proof and a review record;
   - the **global trust-base axioms** of 03 §3.4: the target CPU conforms to the table on the case
     classes used, uniformly within each class. These are never per-kernel;
   - table entries at their frozen content hashes, reached through `intrinsic_map.v1` at its frozen
     hash, and rows of `kir_family_map.v1`;
   - T2 certificates re-checked by the certificate checker;
   - **the DOM-\* predicates of RULES.md §4.0 as frozen**. DOM-ACT-Q and DOM-ACT-SUM are
     postconditions of the act_q8 meaning, proved by T2 over it and inherited by every accepted
     act_q8 variant; for the matmul variants they are domain predicates of the claim (03 §3.4 prints
     them), discharged inside Hearth by an accepted act_q8 variant and checked at C API seams;
   - **the default-MXCSR premise** (DOM-ENV): runtime-checked once D0-5b lands; until then the declared
     precondition "MXCSR = 0x1F80 at entry", **stated in every certificate** (DELEGATED P62; Hearth b5d3f14
     neither sets nor checks MXCSR [M, grep of `engine/src`, 2026-10-16; X0 REPORT §17]);
   - **opaque-call congruence** (P3's denominator is option (b), DELEGATED P31): a call to an external
     function (`cosf`, `sinf`, `expf`, `sqrtf`) matches a call to the same callee with the same
     argument values in the same order, and the results are used identically. Its assumption (the
     callee is a deterministic function of its arguments under the default MXCSR) is global, about
     the platform library, not per-kernel.

   (d) Every table entry it uses is in A2's scope and has run its `budget.v1` rows. Anything else is a rejection.
3. **Per-kernel `assumed` axiom.** Any premise in a certificate that is not one of the kinds in
   item 2(c). The global axioms and the opaque-call premise kind of item 2(c) are never per-kernel
   axioms. One per-kernel premise in a final certificate meets the kill condition.
4. **Rule** (RULES.md §1, draft 2; fixed by DELEGATED P32-P34). A row of `rules.v1` has one left pattern, one
   right pattern, named operators (no operator variables; constant parameters only), side conditions, an Env
   column and a proof artifact. **Count = all rows of `rules.v1` at the verdict, used or not, plus the loop
   rules**, where LOOP-LOCKSTEP with its extensions as lemmas of one written proof counts **1** and each
   separately proved extension 1 more (P32), and **every named integer-identity instance is a row** (P33).
   Evaluation of table entries, family correspondence (`kir_family_map.v1`), T2 obligations and definitional
   identities are not rows (RULES.md §1). **Proved** = primary proof plus an agreeing second route (RULES.md
   §1); a Z3 QF_BV primary counts only together with an agreeing exhaustive or second-solver route (P34).
   Draft 2 counts 21 rows + 1 loop rule = **22** [D, RULES.md §3.1]; 19 of the 21 rows are proved by this
   definition, R02 and R03 are not (their concrete-pattern primary timed out; §13 O5), and LOOP-LOCKSTEP's
   written proof is not yet written [M, RULES.md §8].
5. **Mutant, stillborn, declared domain, FP-changing, level-divergent, equivalent, unresolved, kill,
   kill reason:** as defined in MUTANTS.md §1, which is part of this record (§2). In particular:
   FP-changing is defined at intrinsic level (table-semantics evaluation of the mutated vs the
   unmutated transliterated IR) and confirmed natively on the configuration A build; whole-file flag
   mutants are not in the pool (reported only). A level-divergent mutant with an object-level cause whose table
   evaluations differ at intrinsic level while the native build does not show it **counts as FP-changing and
   stays in P3's denominator** with its intrinsic-level witness (native confirmation waived for it, its absence
   reported): T1 judges intrinsic-level IR and must reject it. Only one that is **not** FP-changing at intrinsic level (its native difference comes from the compiled
   object alone) is outside P3; it is reported and forwarded to X0 and M2, and if T1 accepts it, item 6 decides
   whether that acceptance is a false accept (§13 O4). One with a table cause is handled under items 6-7;
   **an unresolved mutant at the verdict counts as FP-changing, and if T1 accepted it, as a T1
   non-kill** (no waiting state); equivalence is never shown by T1; a T1 kill counts only if T1 accepts the
   unmutated host function. **P3's denominator: every FP-changing mutant of every host group (gating, A4,
   helpers), with T1 run on every host** (option (b), DELEGATED P31; option (a) would remove a ROADMAP mutant
   class). The ≥ 200 live mutants and the ROADMAP classes apply to the whole pool.
6. **False accept.** A T1 ACCEPT for a realisation for which a declared-domain input
   exists on which the realisation's output bytes, **executed natively on the 9950X from the pinned
   build** (configuration A), differ from the **meaning's output bytes as computed by the meaning
   interpreter** (§2) under Env = default. The table-semantics replay is diagnostic only: if it
   agrees with silicon, the root cause is not the table; if it disagrees, the case goes to item 7.
   If the decoded compiled object differs from the transliteration (an object-level cause, shown by
   replaying the object's own instruction sequence through the table and reproducing the native
   output), the case is recorded as a level-divergent finding against the build, reported first in
   the result and forwarded to X0 and M2, **and it counts as a false accept**, not traceable to a table bug
   (item 7). That strict reading is registered until Pierce signs otherwise (§13 O4, §14): OWNER-QUEUE C20 classes
   the carve-out ("not a T1 false accept at intrinsic level") as narrowing what counts as a false accept toward
   X2's kill, so the delegation cannot adopt it. If Pierce ticks the carve-out when he signs, such a case is a
   level-divergent finding only; ticked after the first verdict run, it is a post-data amendment and the verdict is
   reported under both readings (§10). Witnesses come from the mutant pool, the witness search, the fuzz campaign,
   or any other source. A false accept in any **verdict run** counts and stays on record after T1 is fixed. Verdict runs are
   runs of the T1 build under evaluation on the gating variants or on the sealed pool after its reveal;
   development runs before the reveal, on inputs outside the pool, are logged but not counted.
7. **Traceable to a fixable table bug.** The false accept's root cause is a table entry whose
   prediction differs from silicon on a vector that reproduces the witness, and after that entry alone
   is fixed, the same T1 build rejects the realisation. Any other root cause (an unsound rule, a
   matcher or lifter bug, a side-condition check bug, a transliteration bug, an `intrinsic_map` bug)
   is not traceable, and kills X2 as ROADMAP's text says (DELEGATED P29: the text is kept).
8. **Table/silicon mismatch.** For one **lane case** of `budget.v1`: any bit of a lane
   observable (full-width destination register, destination opmask, RFLAGS, the 64-bit GPR) that
   differs between the 9950X and the table entry at its content hash. For one **execution**: any bit
   of MXCSR[5:0] that differs from the OR of the table's predicted flags over the execution's active
   lanes; **flag disagreements count, per execution** (DELEGATED P9). Every flag-bearing class runs under the
   flag-isolation rule of FUZZ-DESIGN §2 (flag-neutral fillers, and for EVEX forms single-active-lane
   executions). P5 counts (entry, case class, environment) cells with at least one lane or execution
   mismatch; the numbers of mismatching lane cases and executions are reported with it. A result that differs
   between two runs on silicon counts as a mismatch until explained. **"After fixes, no mismatches remain"** is
   evaluated on a complete rerun of every vector set of every entry in scope against the final table. Lane case,
   execution and the observables are as FUZZ-DESIGN §2 defines them (pinned, §2). An **environment** is one MXCSR
   setting of FUZZ-DESIGN §3.3, every exception masked; **E8** = {default `0x1F80`, RD, RU, RZ, DAZ, FTZ,
   DAZ+FTZ, RD+FTZ}; every budget row names its environment set.
9. **Table scope.** Every (iclass, iform) of census run 1's union over the `variants[]` closures (build 1) of
   configurations A, B-cmake, C and D gets exactly one **disposition**, computed by `census_absorb.py`
   (`census/coverage_run1_ABCD.json`; the release subset A, D in `coverage_run1_AD.json`):
   - **`entry`**: a table entry exists. **All 72 FP-sensitive forms (32 iclasses)** of the four-configuration
     union have entries, so the fuzz scope does not shrink if X0's amber (a) restricts the table to A and D
     (67 forms, 31 iclasses) [M, 2026-10-23]. 5 integer forms of the T1 image also have entries.
     `census_absorb.py --strict` fails on any FP-sensitive form without an entry; no reason is ever given to one.
   - **`object-level/G`** (125 forms, 55 iclasses): general-purpose, control-flow, hardening or NOP-class
     forms (X0 category G).
   - **`object-level/S`** (117 forms, 83 iclasses): non-FP SIMD or opmask forms no intrinsic of the T1 hosts
     denotes (moves and spills, legacy SSE integer and logic code in the scalar variants, broadcasts lowered from
     `set1`, opmask moves, VZEROUPPER).
   - **`object-level/S, T1-image iclass`** (127 forms, 48 iclasses): compiler encodings (memory operand,
     VEX/EVEX, width) of non-FP iclasses that `intrinsic_map` names. T1 consumes the intrinsic's own register
     form, whose entry is written before T1 accepts code containing it (TABLE-SCHEMA §8.1), with rows by
     item 12.

   The three object-level dispositions carry their written reason in the coverage file (`scope_reasons`): X2's
   T1 judges intrinsic-level IR (ROADMAP §3.3; DR-008 step 2), and these forms exist only in compiled objects,
   which the B1.5 object audit consumes (DR-008 step 3). **By iclass** [D, `census/coverage_run1_ABCD.json`; the
   four sets are disjoint, 36 + 48 + 55 + 83 = 222]: of the 186 census iclasses without an entry, the 48 T1-image
   iclasses get entries during X2 (the form each intrinsic denotes, rows by item 12, written before T1 accepts code
   using it; a Pass needs T1 to accept every host, item 5, so in practice all 48 [inference]); **138 are deferred
   to B1.5: 55 G and 83 S**. Whether this is the reading of ROADMAP's "semantics entries for every census iclass"
   is Pierce's (§13 O1). The scope also contains the image of
   `intrinsic_map.v1` over every host T1 runs on (the gating variants, the A4 hosts and helpers), and every
   instruction a mutant operator can introduce (MUTANTS.md §2). A variant using an iform outside the table is
   not accepted.
10. **Weeks.** Week numbers are PLAN's: W1 = 2026-10-23 to 10-29 [PLAN §W1], so week 6 is 2026-11-27 to 12-03
    and **"the end of week 6" is 2026-12-03**, the calendar reading (registered; at Plan B cadence the other
    reading is Pierce's, §13 O3). The amber extension is 7 calendar days (to 2026-12-10).
11. **Kill reasons.** Every T1 rejection of a mutant records one reason: `mismatch`, `footprint`,
    `mxcsr-write` (semantic) or `unknown-entry`, `special-entry`, `other` (structural). A G or C kill counts
    only if it reproduces in 2 of 2 runs; crash and timeout kills are recorded separately.
12. **Rows of entries added after freeze.** An entry added after the freeze (an intrinsic-level integer or
    data-movement entry T1 needs, an entry for an instruction a mutant operator introduces, a form a re-scope
    adds) gets exactly the rows `budget_rows` at its frozen file hash (§2) assigns to it, and its rows join A2.
    Adding such an entry is not a deviation; changing a row formula is (§10). The formula for the FMA family,
    which M-FMA introduces and which has no entry yet, is already in `budget_rows` (FUZZ-DESIGN §5).
13. **Single-oracle classes.** None by design: Bochs 3.1's opcode tables define every iclass in scope
    [inference from the tables read on 2026-10-16 (FUZZ-DESIGN §6.1) and the 12-case probe [M]; the 25 forms
    added on 2026-10-23 are not yet probed]. Any class Bochs cannot run is listed in that entry's `bochs_record`,
    and the grade rule of TABLE-SCHEMA §7 applies.

## 5. Metrics

**Primary (gate inputs).**
- P1: gating variants accepted, out of 8.
- P2: P2a = the rule count of item 4 at the verdict and whether every counted row and loop rule is
  proved; **P2b** = the loop-rule count and the proof and review status of each loop rule, with the reviewer's
  model family; P2c = the size of `kir_family_map.v1` (reported, not counted). P2a is also reported under the
  alternative readings P32-P34 did not adopt (0 or 7 loop rules; integer identities as 0 rows).
- P3: T1+T2 kill rate over FP-changing mutants (witnessed plus unresolved) in the denominator of item 5.
- P4: false accepts in verdict runs, each with its root-cause classification (items 6-7).
- P5: (entry, class, environment) cells with a table/silicon mismatch in the final complete rerun.
- P6: per-kernel `assumed` axioms in the final certificates.

**Secondary (reported, no threshold).** G, C and G+C kill rates and the sets K_T ∖ K_GC, K_GC ∖ K_T,
K_T ∖ K_G with witnesses (MUTANTS.md §6), each computed with all T1 kills and with semantic kills only;
per host group; T1 acceptance of proved-equivalent mutants; level-divergent mutants with causes;
A4, A5 and A6 results; per-entry Bochs agreement and three-way triage counts (FUZZ-DESIGN §6.3);
entry grades per environment profile; resolution of each uncertainty-register item (TABLE-SCHEMA
§12); loop rules used per variant; T1 and T2 run time per variant.

**Descriptive.** Mismatches found and fixed before the final rerun, with causes; stillborn mutants;
the flag mutants' build results; per-build CPU cost of G, C and T1+T2; measured interpreter and Bochs
throughput against the budget's assumptions.

## 6. Sample and power

No statistical inference is involved; every verdict is a deterministic count.
- Variants and rules: exhaustive (all 8 gating variants; every row).
- Mutants: the whole sealed pool, at least 200 live mutants [target, ROADMAP §3.3], flag mutants
  excluded. If fewer than 200 survive compilation, sites are added before sealing.
- **Fuzz: `budget.v1` (FUZZ-DESIGN §5), final** [D, `budget_rows` over the revision-4 table; the same rows as over revision 3]: 610 rows; sampled
  sets **539,690,903 lane cases** in 576 rows (V1 348,928,000; V2 66,640,000; V3 122,903,896; V4 595,200;
  BCAST 622,080; F-MEMFAULT 1,727); exhaustive V5 sweeps **639,953,797,120 lane cases** in 34 rows. The
  generator's plan equals the budget on all 576 sampled rows [M, `gen_vectors.py --selftest`, desktop,
  2026-10-23]. Changes made for the freeze, each stricter than v0 or required by the census (FUZZ-DESIGN §5,
  §9.5): rows for the 26 new entries; 12 integer classes as written (two classes added, I:near2^31 and
  I:inexact); F-MEMFAULT counts its zero-masking executions; a masked-broadcast row for every EVEX memory form
  with EVEX.b; BCAST rows no longer depend on the census showing a broadcast; V3 only for forms with a write
  mask; FP.CVT.i64_f32 (CVTSI2SS r64, 2^64 inputs) has V1 and V2 and no V5, and its CVT-BND row constructs,
  besides the boundaries, ties ± 1 above 2^32: just above halfway (round bit set, only bit 0 set below it, 8 to
  38 places down) and just below (round bit clear, every bit below set); 16,024 of its 80,000 lane cases
  [M, generator, laptop, 2026-10-23]; revision 4.
- **Per-iclass budget** (ROADMAP §3.3: "The vector budget per iclass is pre-registered"). Lane cases per
  iclass, summed over its table forms; "census forms" counts the forms census run 1 decoded:

  | Iclass | Family | Table forms | Census forms | Sampled lane cases | V5 lane cases |
  |---|---|---|---|---|---|
  | ADDPS | FP.ADD.f32 | 2 | 2 | 3,424,004 | — |
  | ADDSS | FP.ADD.f32 | 2 | 2 | 3,424,001 | — |
  | CMPPS | FP.CMP.f32 | 1 | 1 | 10,496,000 | — |
  | CMPSS | FP.CMP.f32 | 1 | 1 | 10,496,000 | — |
  | COMISS | FP.COMI.f32 | 2 | 2 | 2,624,001 | — |
  | CVTDQ2PS | FP.CVT.i32_f32 | 1 | 1 | 176,000 | 17,179,869,184 |
  | CVTSI2SS | FP.CVT.i32_f32, FP.CVT.i64_f32 | 2 | 2 | 352,000 | 17,179,869,184 |
  | CVTSS2SI | FP.CVT.f32_i32.rc | 1 | 0 | 256,000 | 34,359,738,368 |
  | CVTTPS2DQ | FP.CVT.f32_i32.trunc | 1 | 1 | 256,000 | 34,359,738,368 |
  | CVTTSS2SI | FP.CVT.f32_i32.trunc | 1 | 1 | 256,000 | 34,359,738,368 |
  | DIVSS | FP.DIV.f32 | 1 | 1 | 1,712,000 | — |
  | MAXPS | FP.MAX.f32 | 1 | 1 | 1,392,000 | — |
  | MAXSS | FP.MAX.f32 | 2 | 2 | 2,784,001 | — |
  | MINPS | FP.MIN.f32 | 1 | 1 | 1,392,000 | — |
  | MINSS | FP.MIN.f32 | 1 | 1 | 1,392,000 | — |
  | MULPS | FP.MUL.f32 | 1 | 1 | 1,712,000 | — |
  | MULSS | FP.MUL.f32 | 2 | 2 | 3,424,001 | — |
  | SUBSS | FP.SUB.f32 | 1 | 1 | 1,712,000 | — |
  | UCOMISS | FP.COMI.f32 | 1 | 1 | 1,312,000 | — |
  | VADDPS | FP.ADD.f32 | 8 | 8 | 30,882,348 | — |
  | VADDSS | FP.ADD.f32 | 3 | 2 | 5,251,217 | — |
  | VCMPPS | FP.CMP.f32 | 5 | 4 | 214,122,752 | — |
  | VCMPSS | FP.CMP.f32 | 2 | 2 | 83,968,008 | — |
  | VCOMISS | FP.COMI.f32 | 1 | 0 | 1,312,000 | — |
  | VCVTDQ2PS | FP.CVT.i32_f32 | 5 | 3 | 9,295,104 | 85,899,345,920 |
  | VCVTPH2PS | FP.CVT.f16_f32 | 7 | 6 | 18,026,664 | 3,670,016 |
  | VCVTPS2DQ | FP.CVT.f32_i32.rc | 5 | 2 | 9,695,104 | 171,798,691,840 |
  | VCVTSI2SS | FP.CVT.i32_f32 | 1 | 0 | 176,000 | 17,179,869,184 |
  | VCVTTPS2DQ | FP.CVT.f32_i32.trunc | 5 | 0 | 9,685,504 | 171,798,691,840 |
  | VCVTTSS2SI | FP.CVT.f32_i32.trunc | 1 | 0 | 256,000 | 34,359,738,368 |
  | VDIVSS | FP.DIV.f32 | 3 | 3 | 5,251,217 | — |
  | VMAXPS | FP.MAX.f32 | 6 | 4 | 16,757,512 | — |
  | VMAXSS | FP.MAX.f32 | 2 | 1 | 2,784,016 | — |
  | VMINPS | FP.MIN.f32 | 5 | 2 | 15,365,504 | — |
  | VMINSS | FP.MIN.f32 | 1 | 0 | 1,392,016 | — |
  | VMULPS | FP.MUL.f32 | 8 | 7 | 30,952,016 | — |
  | VMULSS | FP.MUL.f32 | 3 | 2 | 5,251,217 | — |
  | VUCOMISS | FP.COMI.f32 | 2 | 2 | 2,624,000 | — |
  | VPDPBUSD | INT.DPBUSD.u8s8 | 3 | 1 | 8,735,504 | — |
  | VPHADDD | INT.HADDD | 2 | 1 | 220,000 | — |
  | VPMADDUBSW | INT.MADDUBS.u8s8 | 5 | 1 | 10,029,680 | 21,474,836,480 |
  | VPMADDWD | INT.MADDWD.s16 | 6 | 2 | 9,065,512 | — |

  Table forms the census did not decode stay in scope through `intrinsic_map` or a mutant operator. The row
  list, class by class, is `census/budget.v1.json`.
- **Run time [D].** The C interpreter's exhaustive engine ran about 25 ns per lane case [M, 2026-10-16], so the
  V5 predictions take about 4.4 h of one thread, about 2.2 h on this track's 2 threads, plus the silicon sweep and
  the two-CCD repeat. The sampled part is about 1.5 × 10^8 executions [D, scaled from 1.15 × 10^8 executions
  for 4.0 × 10^8 lane cases], about 2.5 h of one thread to generate at 61 µs per execution [M, 2026-10-16], and
  about 48 GB of vectors at 320 bytes per execution [D], on D:. All of it fits daytime 2-thread runs within a few
  days; it never runs in a quiet window.
- **Power** [D: 1 − (1 − q)^n]:

  | Defect rate q in the sampled set | 1,000 draws (class cell, one environment) | 8,000 draws (class cell over E8, defect present in every environment) | 1,152,000 draws (a two-source iform's V1, defect spread uniformly) |
  |---|---|---|---|
  | 3 × 10^−3 | 95.0% | > 99.99% | > 99.99% |
  | 10^−4 | 9.5% | 55.1% | > 99.99% |
  | 10^−5 | 1.0% | 7.7% | > 99.99% |
  | 10^−6 | 0.1% | 0.8% | 68.4% |
  | 10^−7 | < 0.1% | < 0.1% | 10.9% |

  Mismatches rarer than about 3 × 10^−3 of a class cell are covered only by constructed classes or
  exhaustive enumeration; elsewhere the uniformity axiom (03 §3.4) carries the claim.

## 7. Analysis procedure

Deterministic Gatekeeper scripts, hashed:
- **A2 counts and triage:** `experiments/x2-semantics/harness/compare.py` (exists; sha256 in §2): per (entry,
  class, environment) cell lane and execution-flag mismatches, two-run nondeterminism, harness anomalies, the
  three-way verdict of FUZZ-DESIGN §6.3 with Bochs compared on every record, provenance checks of every input.
- **The outcome of §8:** `experiments/x2-semantics/scripts/x2_gate.py` (exists; LF sha256
  `408de00c55326302c8ca9336c0c7fcff99fe3ce2216127ce3c6c3b44427fa1a6`; self-test 24 cases: the 19 outcome rows, 4
  impossible inputs refused, the `inputs` field; PASS on the laptop and on the desktop [M, 2026-10-23]). It reads one
  gate-input file, refuses impossible inputs (P1 above 8, P3 kills above the denominator, negative counts) and
  writes `verdict.json`.
- **Not yet written** (their inputs do not exist yet): `x2_mutants.py` (A3 classification per MUTANTS.md §1, kill
  reasons, kill matrices) and the T1 run summariser that produces the gate-input file from T1's certificates and
  run manifest (P1, P2, P4, P6). Each is written, reviewed (same family, independent context) and hashed before
  the pool is sealed, and its hash is appended as a dated pre-data amendment. Neither can change a definition of
  this record; a script that disagrees with this text is a script bug.

The scripts' commit hash is recorded in the result manifest. A separate agent context re-derives P1-P6 from the
raw outputs without access to the scripts' intermediate state; its figures must match exactly.

`verdict.json` carries P1-P6 as read (field `inputs`, which the separate-context re-derivation matches), the outcome
and its reasons, the script and input hashes, and the field **`proved_loop_shapes`**: the X0 loop tags (X0
record §4 item 7) covered by loop rules that are proved and reviewed at the verdict, by the mapping of RULES.md §5,
plus any `other` loop ids argued individually. X0's narrowing row reads this field; without it X0's narrowing
holds by default.

## 8. Outcomes

The thresholds below are copied from ROADMAP §3.3 without change. `x2_gate.py` computes the row.

| Outcome | ROADMAP §3.3 text | Operational condition | Action |
|---|---|---|---|
| **Pass** | "T1 accepts 100% of real variants with ≤ 30 proved rules and rejects 100% of FP-changing mutants. After fixes, no table/silicon mismatches remain, and there are zero false accepts." | P1 = 8/8; P2a ≤ 30 with every counted row and loop rule proved; P3 = 100%; P5 = 0; P4 = 0 after table-traceable false accepts are fixed and none other occurred; P6 = 0; and the loop-rule proof reviewed by a Prover from a different model family (ROADMAP §3.3 Proofs) | X2 passes. "Either way, X2 certifies C Hearth's existing kernels" for the variants accepted, under the declared preconditions of item 4.2(c) |
| **Pass, review pending** | (ROADMAP's pass needs the different-family review) | every Pass condition except the different-family review (D0_BRIEF Q17 unanswered: operating status UNMET, DELEGATED P3) | **not a pass**: reported as `pass_review_pending`. Only if Pierce signs a Q17 line and the local Qwen3 then reviews the proof does it become `pass_local_family` (QWEN3_LOCAL_PROVISIONAL; provisional, as X1's) or `pass` (QWEN3_LOCAL_FULL) (§13 O2; `x2_gate.py`) |
| **Amber** | "If 31–40 rules are needed, X2 gets one more week and is judged again." | P2a ∈ [31, 40] at the end of week 6 and **no kill condition holds**; P1, P3 and P5 may still be short | one extension of 7 days (item 4.10), then the full table is applied again |
| **Kill** | "At the end of week 6, T1 still needs per-kernel `assumed` axioms, or more than 40 rules [P2 §10], or has made a false accept that is not traceable to a fixable table bug. N2 then dies, kernels carry `tested` evidence plus the hash corpus, and the project continues only if X1 and X3 pass." | at the end of week 6 (or of the amber week): P6 > 0, or P2a > 40, or any false accept not traceable per item 4.7 | N2 dropped; ROADMAP §4 row chosen by the Gatekeeper together with X1 and X3; a design tombstone is written (below) |
| **Gate missed** (`gate_missed`: DELEGATED P28, extended by this record) | (ROADMAP gives no band here; ROADMAP §1 rule 2 requires a written action) | at the end of week 6 (or of the amber week) no kill condition holds and the result is none of the rows above. P28's conditions: P1 < 8, or P3 < 100%, or P5 > 0, with P2a ≤ 30. **Added by this record** (none loosens anything; without them these results would have no row): P2a ≤ 30 with a counted row or loop rule not proved; a table-traceable false accept not fixed; the amber week ending again with P2a ∈ [31, 40] (ROADMAP provides no second amber) | the failing variants stay `tested`, no extension. A `gate_missed` X2 never satisfies a clause that reads X2 = pass; the M0-verdict mapping reports it as a NARROW row (DELEGATED P8). Pierce signs this line with the record, the three added conditions included; the amber-week case settles a gap P28 does not cover and is his to confirm (§14) |

**Honest reporting (ROADMAP §3.3).** "If G+C already kill every mutant T1 kills, the result reads
'stronger evidence per build at lower cost', not 'catches more bugs'." Operationalised in MUTANTS.md
§7; the report states K_T ∖ K_GC explicitly, with all T1 kills and with semantic kills only, and B1's
wording (ROADMAP §7) is evaluated from the same sets.

**Tombstone the kill would write** (DECISIONS.md §4 format, 06 §7.2 grammar):

```text
tombstone validated_kernel_identity {                 // written only if the X2 kill fires
    verdict: unproven                                 // or `infeasible`, copied from the signed report
    scope:   { kernels: hearth_b5d3f14_simd, level: intrinsic_ir, table: x2_table@sha256:…,
               rules: rules_v1@sha256:…, cpu: zen5_9950x }
    class:   T                                        // tooling: rules, matcher or table not yet adequate
    revisit_when: (t1.rules_audited <= 30 && t1.false_accepts == 0
                   && t1.coverage(dispatched_variants) >= 1.0)
               || (has(rule: max_fold_conditional) && at_burial.t1.rules_audited > 30)
    evidence: ledger:sha256:…
}
```

The trigger uses facts DR-008 already names (`t1.rules_audited`, `t1.coverage(...)`,
`t1.false_accepts`) plus a catalogue atom; its exact form is fixed when the kill's cause is known.

## 9. Threats to validity

- **Transliteration.** X2 checks intrinsic-level IR, not what compilers emit; a compiler may still
  reorder or contract. Handled by X0 (contraction screen), the level-divergent classification
  (MUTANTS.md §1, item 4.6) and the M2 object audit; the report says "intrinsic level" on every
  claim. `intrinsic_map.v1` pins which instruction each intrinsic denotes.
- **Scope of the table.** 369 census forms are object-level and have no entry (item 9); by iclass, the 48 T1-image
  iclasses get entries during X2 and 138 (55 G, 83 S) are deferred to B1.5. Nothing T1 consumes is among the
  deferred ones, and every FP-sensitive form has an entry and rows, but an M2 audit that lifts objects needs entries
  for them. The scope reading is Pierce's (§13 O1).
- **Census not final.** Run 1's verdict is unsigned. The re-scope rule (§2) only adds forms after collection
  starts, so a later union can widen A2, never narrow it.
- **Meaning fidelity (intent gap).** Meanings are transcribed from NUMERICS.md and the C scalar code.
  A wrong meaning is certified faithfully. Mitigation: each meaning is run differentially against
  Hearth's scalar variant on `test_quant`-style inputs, including NaN, infinity, subnormal and tie
  blocks, before T1 runs; the meaning-mutant control (A6) checks that T1 compares against the
  meaning at all.
- **Pool bias.** Rules are frozen before the pool is revealed; the pool is authored in a separate
  context (MUTANTS.md §3).
- **Oracle correlation.** Bochs shares the SDM reading with the table, and several of the table's readings were
  taken from Bochs's SoftFloat 3e. On those, Bochs agreement counts as zero independent evidence: the classes
  **F-TINY, F-FTZ-EXACT, F-DAZ-SEL and F-H2F**, and the entries of FP.ADD, FP.SUB, FP.MUL, FP.DIV, FP.MAX,
  FP.MIN and FP.CVT.f16_f32 (`table_source: sdm+bochs`, the legacy and memory forms of revision 3 included).
  There silicon and the signed SDM review carry the grade (TABLE-SCHEMA §7). Uniformity within a case class
  remains an axiom (03 §3.4); the power table of §6 says how rare a defect the sampled budget can see.
- **A reading corrected with pre-freeze silicon** (B6, §2.1). Disclosed; the class runs in full under the
  budget and P5 is judged on the final rerun.
- **Declared preconditions.** The certificates of C Hearth b5d3f14 rest on DOM-ENV (MXCSR = 0x1F80 at
  entry), which Hearth does not establish until D0-5b lands, and on DOM-ACT-Q/DOM-ACT-SUM at C API
  seams. Every certificate prints them (DELEGATED P62).
- **One fingerprint.** Results hold for the 9950X fingerprint; other machines rely on the conformance
  axiom and the load-time self-test (03 §6.7).
- **Equivalence circularity.** Equivalence is never shown by T1 (item 4.5).
- **Reference interpreter divergence.** The generated C interpreter is validated against the Python reference on
  10^6 random cases before use (FUZZ-DESIGN §4): revision 4, 1,000,006 lane cases over all 664 stubs, 0
  divergences [M, 2026-10-23, `harness/devlogs/valid.report.20261023d.json`]. Disagreements block the run.
- **Flaky test-arm kills.** G and C kills count only when reproduced in 2 of 2 runs (item 4.11).
- **Second oracle not yet running.** The Bochs production image (vector loader, in-guest compare) is not built;
  the pre-registered fallback (§10) bounds the delay.
- **Review independence.** Reviews are same-family, independent-context until D0-10 names other
  families; ROADMAP §3.3 asks for a Prover from a different family for the loop rule, which is why §8 has the
  `pass_review_pending` row (D0_BRIEF Q17, DELEGATED P3).

## 10. Deviation and re-run policy

- Fixes to table entries, the harness, the transliterator, `intrinsic_map` and T1's implementation
  are allowed before the verdict and are logged with cause; every fix to a table entry reruns all of
  that entry's vector sets. Fixes never erase a recorded false accept (item 4.6).
- Adding an entry under item 12, or forms under the re-scope rule of §2, is not a deviation; it is logged, and
  after collection has started it only adds rows.
- A change to a unit, a threshold, the gating set, P3's denominator option, `rules.v1` or `loops.v1`
  after the pool's reveal, a row formula of `budget_rows`, `budget.v1`'s rows for an existing entry, or the
  second oracle after collection starts is an amendment marked *post-data*; verdicts are reported under the
  original and the amended rule.
- **Pre-registered second-oracle fallback** (DELEGATED P10; FUZZ-DESIGN §6.2): "If, at the end of M0 week 3, the
  Bochs image does not run the V2 slice of three named entries (VADDPS zmm, VMAXPS zmm, VCVTPS2DQ zmm) end to end,
  the second oracle becomes SoftFloat 3e called directly (FP core only) plus Intel SDE if and only if its
  emulation probe has passed; the grade rule then counts only those classes the substitute can run, and every
  entry's `bochs_record` names the substitute. The switch is logged with its date and is not a deviation under
  §10." Week 3 ends 2026-11-12 (item 4.10). Downloading SDE needs its licence accepted by click-through, which
  only Pierce can do (§13 O8); without it, SoftFloat-direct alone is the substitute.
- Adding a configuration or a secondary arm is allowed and cannot change the verdict.

### 10.1 Collection procedure

- The first budget vector waits for this record to be FROZEN and SIGNED (header). Collection runs pass
  `--collection-authorised` to `x2fuzz`; budget vectors carry `BUDGET-v1-<set>` labels and their budget set ids
  (harness/README.md §4). Without the flag the harness refuses them; the seven refusals G1-G7 were re-checked on
  the revision-4 build [M, 2026-10-23, `harness/devlogs/guards.20261023d.log`, and again with the final generator,
`guards.20261023e.log`].
- Each vector set runs on two logical CPUs on different CCDs (CPU 4 and CPU 20); any difference is an anomaly.
- Desktop rules: at most 2 threads for this track, `CUDA_VISIBLE_DEVICES=-1`, TEMP and TMP on D:, daytime only
  (07:00-23:00 PT) and never in a quiet window, no WSL, outputs under `D:\mithril\`.

## 11. Deliverables

- `experiments/x2-semantics/results/`: fuzz comparison per entry, mutant kill matrices (with kill
  reasons, per host group), T1 certificates for the variants, the gate computation, `verdict.json`
  (with `proved_loop_shapes`); REPORT.md with every number tagged.
- `experiments/x2-semantics/census/`: the census absorption (coverage per configuration set, with every form's
  disposition and reason), `budget.v1.json`, `table_index.json`.
- Ledger records: table entries with evidence blocks; `rules.v1`, `loops.v1` and
  `kir_family_map.v1` with proof artifacts; `intrinsic_map.v1`; the sealed pool with classifications;
  T1 certificates (the C Hearth kernel certification ROADMAP §3.3 promises).
- Proposed changes to 03 §3.4, §6.3 and §6.7 (TABLE-SCHEMA §14, RULES.md §7), for the Owner to accept
  or not.

## 12. Review log

| Date | Reviewer | Family | Scope | Outcome |
|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 (lens: semantics and tests: witness analysis, domain predicates, flag observables, operand roles, content hash, coverage claims) | Claude (same family as author; independent context) | this record and experiments/x2-semantics/ | 13 findings: 0 blocker, 5 major, 8 minor. 13 accepted, 0 rejected |
| 2026-10-16 | Reviewer 2 (lens: pre-registration and gate logic: premise kinds, P3 reachability, mutant classification, false-accept definition, amber, rule count, intrinsic map, census scope, budget, oracle independence, MXCSR premise, tools) | Claude (same family as author; independent context) | this record and experiments/x2-semantics/ | 21 findings: 3 blocker, 12 major, 6 minor. 21 accepted, 0 rejected |
| 2026-10-23 | Reviewer 1 of revision 3 (scope as the freeze precondition named it: census absorption, B6 correction, budget changes, gate script, §8 rows, scope dispositions) | Claude (same family as author; independent context) | revision 3 of this record and experiments/x2-semantics/ | 9 findings: 0 blocker, 3 major, 6 minor. 9 accepted (8 fixed in revision 4; 1, DELEGATED.md's header, forwarded to the lead engineer), 0 rejected |

Totals of the 2026-10-16 reviews: 34 findings (3 blocker, 17 major, 14 minor); 34 accepted; 0 rejected. Both are
same-family, independent-context, which is weaker than ROADMAP's different-family requirement until D0-10 names
other families. Parts of accepted findings not adopted as proposed, with the reason (the full disposition is in
[TABLE-SCHEMA.md §15](../../../experiments/x2-semantics/TABLE-SCHEMA.md#15-review-log)):

- R1-7: "R19 holds for any RC applied to both sides" is wrong for RZ (Z3 counterexample, e.g.
  `0xC12D829E` [M] reviser 2026-10-16; Hearth council review 2026-10-04); R19's Env is RNE as used.
- R1-13: SEL-MIN not added; no Hearth site needs it and every row counts.
- R1-1: the proposed wording "x[60]/x[62] erase lane pairs" is imprecise (x[62] erases 4 lanes on
  AVX2, 8 on AVX-512); the exact tree rule is used instead.
- R2-2: the reviewer's provisional default (a) would loosen ROADMAP's mutant gate; (b) is the rule (P31).
- R2-4: the native false-accept definition is adopted. The carve-out added then (a native difference caused by
  the compiled object is a level-divergent finding, not a T1 false accept) is, since revision 4, an option for
  Pierce and not the registered reading (§13 O4; review of 2026-10-23, finding 2).

The 2026-10-23 review of revision 3 (findings numbered 1-9 in the reviewer's order; full disposition in
[TABLE-SCHEMA.md §15](../../../experiments/x2-semantics/TABLE-SCHEMA.md#15-review-log)). Revision 4 has not been
reviewed again; whether its changes need a further same-family pass is the lead engineer's call. Parts not adopted
exactly as proposed, with the reason:

- 1 (O1 split): adopted. "The 48 must have entries by the verdict" is stated as: each gets its entry before T1
  accepts code using it, and a Pass needs all of them [inference] (item 9); a form-keyed reading is noted too.
- 5 (gate script): adopted; the range checks also refuse negative counts and a non-boolean `p2_all_proved`.
- 6 (legacy compare immediates): the domain is declared in the hashed `sem` spec (`imm_max: 7`) and checked by
  the table's compare builders, not inside `fp_ops.cmp_pred`, because sealed table mutant M04 anchors on that line;
  the VEX and EVEX compares now also refuse imm8 above 31; `pyref.py` reports a refused immediate as unmodeled, as
  the C interpreter does.
- 7 (64-bit conversion): the tie ± 1 construction went into CVT-BND (V2, the constructed class) instead of
  replacing a V1 class, so no V1 class is lost and no row count changes; the shift is s ∈ [8, 38], not [8, 39],
  because s = 39 can exceed 2^63 − 1.
- 9 (DELEGATED.md says "None of the rows below is adopted" above rows marked ADOPTED): outside this track's files.
  The lead engineer corrects the header or moves the rows; the freeze commit must carry that correction, or §13's
  "adopted 2026-10-23" has no adopted row to point to.

## 13. Owner items

**Answered under the batch-4 delegation** (DELEGATED.md, adopted 2026-10-23 by the lead engineer; Pierce reviews
each at sitting 2, 2026-10-25; a reversal before the freeze changes this text, after it needs an amendment):

| Pre-freeze question (revision 2) | Row | Fixed as | Where here |
|---|---|---|---|
| 1 Band between gate and kill | P28 (with P8), extended here by three non-pass conditions (O9) | `gate_missed`, NARROW row | §8, §14 |
| 2 Fixable T1 bugs | P29 | keep ROADMAP's text | item 4.7 |
| 3 F16/BF16 variants | P30 | secondary; their mutants count in P3 | item 4.1, §3 |
| 4 MXCSR flags | P9 | count, per execution | item 4.8 |
| 5 Second-oracle fallback | P10 | pre-registered | §10 |
| 8 P3's denominator | P31 | option (b) | item 4.5 |
| 9 Loop rules in the count | P32 | 1 | item 4.4 |
| 10 Integer identities | P33 | each instance a row | item 4.4 |
| 11 QF_BV as primary | P34 | only with an agreeing route | item 4.4 |
| 12 Certifying under the MXCSR precondition | P62 | yes, stated in every certificate | item 4.2(c) |
| TABLE-SCHEMA Q1 (intrinsics XML) | P14 | SDM only | §2 |

**Still Pierce's** (each registered with what this record does until he answers, and by when it is needed):

| # | Item | Registered here | Needed by |
|---|---|---|---|
| O1 | **Scope reading.** ROADMAP §3.3 says "semantics entries for every census iclass". This record gives entries to every FP-sensitive census form and to the integer forms T1 needs, and gives the other 369 forms (125 GPR/control, 244 SIMD data-movement, integer, opmask) the object-level disposition of item 9. By iclass [D, `census/coverage_run1_ABCD.json`]: of the 186 census iclasses without an entry (222 − 36), **48 (T1-image) receive entries during X2** for the form their intrinsic denotes (item 9, item 12; a Pass needs all 48 [inference]); **138 are deferred to B1.5: 55 G and 83 S**. Three readings: object-level (as registered); entries for every census SIMD iclass (the 83 S iclasses added, rows by item 12; the 55 G deferred); entries for every census iclass (all 138, G included). The last means entries, stubs and rows for 138 iclasses, including memory stores the harness cannot observe yet (harness/README.md §4) [G: several agent-days]; the SIMD-only reading has no separate estimate. Under a form-keyed reading the 127 census forms of the 48 T1-image iclasses would need entries too | the object-level reading, **proposed, not adopted**: it narrows a ROADMAP build line, which the delegation may not do. Pierce ticks one of the three at §14 | **the freeze** |
| O2 | D0_BRIEF Q17 (DELEGATED P3, not delegable): may the local Qwen3 review the loop-rule proof as the "different family"? | UNMET: the kill clock does not wait; a result that meets every other Pass condition is `pass_review_pending`, not a pass (§8) | the loop-rule review (≈ W4-W8) |
| O3 | OWNER-QUEUE C04: what "the end of week 6" means at Plan B cadence | the calendar reading, 2026-12-03 (item 4.10); the later reading would be a change in the favourable direction and is his alone, before any gate data | the X2-gate rules (W2, 2026-11-01) |
| O4 | OWNER-QUEUE C20 (X2 Q13): is an object-caused native difference a level-divergent finding only (the carve-out), or a false accept? C20 is class B: the carve-out narrows what counts as a false accept toward X2's kill, and a class-B default that loosens never runs by lapse of time, so the record freezes with the strict alternative (OWNER-QUEUE, rule for class-B items) | **the strict reading**: such a case counts as a false accept, not table-traceable (item 6), every case reported first; a mutant that is FP-changing at intrinsic level stays in P3 whatever the native build shows (item 5). The carve-out applies only if Pierce ticks it at §14 | his signature; after the first verdict run, only as a post-data amendment reported both ways (§10) |
| O5 | OWNER-QUEUE D11 (X2 Q7) with proofs/README.md §5: may `rules.v1` hold the conditional MAX folds R02/R03, which 03 §6.3's blanket ban on MAX/MIN commutation forbids, and may their written proof (every lemma proved by Z3 and cvc5) serve as the primary while the concrete-pattern queries time out? Without both, P1 cannot reach 8/8 [inference] | R02/R03 stay in the draft rule list, counted and marked not proved | before T1 runs on the real variants |
| O6 | Signature of the frozen record (D0-12) | — | the first budget vector |
| O7 | WSL on the desktop (C: budget) | the Bochs boot image is assembled with LLVM 23.1.3 on Windows (§2 Tools) | no deadline |
| O8 | Intel SDE licence click-through, if the §10 fallback ever wants SDE | SoftFloat-direct alone | only on the fallback |
| O9 | P28's extension (§8): three non-pass conditions P28 does not list (an unproved counted row or loop rule with P2a ≤ 30; a table-traceable false accept not fixed; the amber week ending again with P2a ∈ [31, 40]) | as §8 states: each is `gate_missed` | his signature (§14) |

## 14. Signature block

```text
Owner: ______________________   Date: __________
Signs the record frozen at commit: ________
Scope reading (§13 O1), one of:
  [ ] object-level reading accepted (138 census iclasses deferred to B1.5; the 48 T1-image iclasses get entries in X2)
  [ ] entries for every census SIMD iclass (the 83 object-level/S iclasses added, rows by §4 item 12;
      the 55 G iclasses deferred to B1.5)
  [ ] entries for every census iclass (all 138 added, G included)
Object-caused native differences in verdict runs (§13 O4), one of:
  [ ] count as false accepts (registered; applies unless the next box is ticked)
  [ ] carve-out accepted: a level-divergent finding against the build, not a T1 false accept
gate_missed (§8; DELEGATED P28 with the three non-pass conditions this record adds, the amber week
ending again with P2a in [31, 40] among them, §13 O9):  [ ] confirmed
The second-oracle fallback of §10 is part of the record (DELEGATED P10); no separate signature.
```

Amendments (appended, dated)
