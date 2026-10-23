# X2 native fuzz harness (Zen 5)

Status: BUILT, SELF-TESTED and REVISED after one review, 2026-10-16 (x2build track; review log §11);
**REBUILT for the X2 freeze on 2026-10-23 (x2freeze track, §13): 26 census entries, the B6 correction, the final
budget formula; rebuilt again the same day for the record's revision 4 (§14).** **No vector under the X2 record has been generated for silicon or run.** The record
([docs/m0/prereg/X2-checker.md](../../../docs/m0/prereg/X2-checker.md)) is DRAFT; under the
[collection rule](../../../docs/m0/README.md) the budget (`budget.v1`) waits for it to be FROZEN and SIGNED
(D0-12, provisional chat answer: batch weekly review). What ran on silicon here: the harness's own plumbing
probes (data movement only), the **exhaustive-engine plumbing check** added after the review (self-test
step 9: the 40 V5-eligible stubs on 4,096 fixed inputs each; §8), and one **development smoke run on the
hand vectors of `semantics/selftest.py`** (label `DEV-SMOKE`, no budget row, no class cell, not evidence for
any entry's grade; §7 below). The seeded-mutant calibration (§9) re-used the review's development silicon
results and executed nothing.

Tags as in [docs/m0/README.md](../../../docs/m0/README.md). "[M] x2build 2026-10-16 desktop" = measured by
this track on the desktop (AMD Ryzen 9 9950X, Windows 11 26200.9711) over SSH. Every review so far is
Claude: **same family, independent context** (§11).

## 1. What it implements (FUZZ-DESIGN.md §1, §2, §4)

| FUZZ-DESIGN element | File | State |
|---|---|---|
| Stub generation from table entries: roles from the entry's `operands` only, bytes from the pinned XED encoder, decode-back check of iform, every role register, masking, zeroing, `{er}`/`{sae}`, broadcast and (since the review) the imm8, with a negative control; MASM `db` lines | [stubgen.py](stubgen.py) → `stubs.asm`, `stubs_table.c`, `stubs_manifest.json` | built, 491 stubs, 0 errors; 288 immediates checked |
| JIT-free leaf stubs; volatile registers only (zmm0-2, zmm16-18, k1, k2, rax, r8, r9); MXCSR restored to 0x1F80 | `stubs.asm` (generated), [x2probe.asm](x2probe.asm) | built |
| Driver: sampled mode, exhaustive mode (in-process compare **of the observable bytes only**, mismatches with a flood cap, stream hash), fingerprint, affinity pinning, SEH fault capture, `PAGE_NOACCESS` data page for F-MEMFAULT (**load side only**, §4), collection guard (label **and** budget set ids), MXCSR precondition | [x2fuzz.c](x2fuzz.c), [x2harness.h](x2harness.h), [x2sha256.c](x2sha256.c) | built, self-test PASS (9 steps), guards checked ([run_guards.cmd](run_guards.cmd)) |
| Reference interpreter in C, exact integer arithmetic, one port of each Python lane function and builder | [x2ref.c](x2ref.c), [x2ref.h](x2ref.h) | validated against Python on 1,000,006 lane cases, 0 divergences; unchanged by the revision |
| Python oracle (predictions from `semantics/table.py`) | [pyref.py](pyref.py) | used by the validation, the dev smoke and the mutant runner |
| Operand-class generators (12 f32 classes, f16 and integer analogues, 17 targeted classes), E8 environments, V3 masks, flag isolation (fillers + single-active-lane), BCAST and masked BCAST (a row per EVEX memory form with EVEX.b since 2026-10-23), F-MEMFAULT (merge and zero masking both counted since 2026-10-23), V4 `{er}`; counter-based SplitMix64 per lane case; BUDGET labels by default | [gen_vectors.py](gen_vectors.py) | self-test PASS; plan = budget on all 576 sampled rows of `budget.v1` (§13, §14) |
| Comparator: lane and execution-flag mismatches per (iform, set, class, env) cell, C-vs-Python divergence, two-run nondeterminism, harness anomalies (incl. preset sticky flags), three-way verdict of §6.3 **with Bochs compared on every record**, provenance checks of every input | [compare.py](compare.py) | self-test PASS |
| Seeded table mutants (FUZZ-DESIGN §6.4 calibration arm) and their runner | [mutants/](mutants/) | built; calibrated on development data (§9) |
| Binary formats | [vecfmt.py](vecfmt.py) | used throughout |
| Build and run scripts (desktop) | [build.cmd](build.cmd), [run_selftests.cmd](run_selftests.cmd), [run_guards.cmd](run_guards.cmd), [run_devsmoke.cmd](run_devsmoke.cmd), [run_final.cmd](run_final.cmd), [run_mutants_dev.cmd](run_mutants_dev.cmd), [mkbuildinfo.py](mkbuildinfo.py) | used |
| Bochs probe (second-oracle feasibility) | [bochs/](bochs/) | §10 |

## 2. Build [M] x2build 2026-10-16 desktop

`cmd /c D:\mithril\x2\src\harness\build.cmd` (sources copied to `D:\mithril\x2\src`, outputs in
`D:\mithril\x2\build`): `stubgen.py` (Windows Python 3.13.4, XED v2026.08.23 Windows build), `ml64` and
`cl` 19.44.35229 (`_MSC_FULL_VER` 194435229) with `/O2 /W4 /MP1` (one compiler process, so a build can run
beside another job of this track within its 2-thread budget). Build wall time about 6 s. Hashes of the
final build (the revised one) are in §8.

## 3. Stubs [M]

- 491 stubs over all 88 table entries (by masking: 311 plain, i.e. k0 or unmasked, 138 merge, 42 zero).
  By kind: 256 compare stubs, one per predicate (3 EVEX VCMPPS entries × 32 × {plain, merge}, 2 VEX
  entries × 32); 28 `{er}` stubs (4 modes × VADDPS zmm, VMULPS zmm, VADDSS, VMULSS, VDIVSS EVEX,
  VCVTDQ2PS zmm, VCVTPS2DQ zmm); 38 `{sae}` stubs (VMAXPS, VMINPS, VCVTTPS2DQ, VCVTPH2PS zmm, VMAXSS,
  VMINSS EVEX, and VCMPPS zmm × 32 predicates); 6 broadcast stubs; 163 other plain/merge/zero stubs.
- **0 encode or decode-check errors.** Every stub's bytes decode, with the pinned XED, to the entry's
  iclass, to the operand register its role names, and to the variant's masking/zeroing/rounding/broadcast
  fields. Since the review (finding R1-7) also to the variant's **imm8**: XED's `IMM0` field (printed as
  `IMM0:0x1f`, compared as a number) and, for register forms, the last byte; **288 immediate stubs, 0 errors,
  and a negative control (a wrong imm8 on the first immediate stub) is reported** [M] rev. 2026-10-16. The
  manifest is byte-identical to the first build's (`03fe7a69…`), as it must be when no check fails.
- **All 39 `provisional` iform keys of the table decode exactly as written** (e.g. `ADDSS_XMMss_XMMss`,
  `VCVTPH2PS_XMMdq_XMMq`, `CVTTSS2SI_GPR32d_XMMss`, `VCVTSI2SS_XMMdq_XMMdq_GPR32d`). This shows the
  placeholders are XED's names for those encodings; it does not show that a compiler emits them (X0's
  census decides that). Changing the keys' `iform_status` is the table owner's call, not this track's.
- XED asmparse spellings found while building (recorded in `stubgen.py`): the unmasked EVEX form needs
  an explicit `{k0}`; rounding decorators are `{rne-sae}`, `{rd-sae}`, `{ru-sae}`, `{rz-sae}`; an immediate
  needs two hex digits (`0x00`; `0` fails).

## 4. ABI and file formats

`x2case` (256 bytes, `x2ref.h`): MXCSR at 0, write mask (KMOVQ into k1) at 8, memory pointer (RAX for
memory forms) at 16, RFLAGS before (U)COMISS at 24, GPR input at 32, k2 before a compare-into-mask at 40,
src1 at 64, src2 at 128, old destination at 192. `x2out` (128 bytes): full 512-bit destination at 0,
MXCSR after at 64, RFLAGS at 72, k2 at 80, RAX at 88. The C ABI pointers arrive in rcx/rdx. Legacy
`dst_src1` forms take src1 from the old destination; GPR sources come from RAX; (U)COMISS runs with
OF/SF/AF preset to 1 so their clearing is observable; compares into k start from k2 = all ones so the
zeroing of bits ≥ lanes is observable; CVT(T)SS2SI starts from RAX = 0xDEADBEEFDEADBEEF so the 64-bit
zero extension is observable.

`vectors.bin`: 256-byte header (magic `X2VEC001`, record size 320, count, stub-manifest sha256,
generator sha256, semantics bundle, label) then 320-byte records (64-byte meta: stub id, flags
{memfault, single-lane, fillers}, set, class id, environment id, lane under test, memfault boundary,
lane cases counted, index, key; then the case). Results and predictions: 256-byte header (magic
`X2RES001`, vectors sha256 recomputed while reading, manifest, producer, producer sha256, CPU) then
160-byte records (output, status, exception code, index). A sidecar `vectors.bin.classes.json` names
every class and environment id.

**Collection guard (revised after the review, finding R1-3).** The first build keyed the guard only on the
self-declared header label, and the generator labelled every file `DEV-GEN` by default, so budget-row vectors
could run on silicon without authorisation. Now, without `--collection-authorised`:
- `x2fuzz run` refuses a vector set whose label does not start with `DEV`, `SELFTEST` or `VALID`, **and**
  pre-scans the file and refuses it if any record carries a budget set id (V1-V4, BCAST, F-MEMFAULT;
  vecfmt.SETS 1-6), whatever the label. Development tools use the sets DEV (7) and VALID (8) (`devsmoke.py`,
  `validate_interp.py`).
- `gen_vectors.py` labels budget rows `BUDGET-v1-<set>` by default; a `DEV`, `SELFTEST` or `VALID` label needs
  `--dev`, which also requires `--limit` ≤ 100,000 executions per row. The records keep their budget set ids,
  so a development slice can be generated and timed but not executed.
- `x2fuzz exhaustive --oracle silicon` refuses to start.
`run_guards.cmd` checks seven refusals (G1-G7, each exit code 2, no results file written) in every
`run_final.cmd` [M] (§8). Nothing in this build session passed `--collection-authorised`. **For the X2 record's
collection procedure** (not edited here; the record is not this track's file): collection runs pass the flag
explicitly, and vectors from the frozen budget carry `BUDGET-v1-*` labels and budget set ids.

**MXCSR precondition (finding R1-6).** FUZZ-DESIGN §2 says the flags are clear before each execution; the
first driver loaded MXCSR verbatim, so a vector with a preset sticky flag would have hidden a flag the table
predicts but silicon does not raise. Now `run` reports such a record as UNMODELED (status 2) unless the label
starts with `VALID` (the interpreter validation deliberately presets flags, and runs no silicon); `compare.py`
counts such records as harness anomalies outside VALID sets; `exhaustive` refuses an `--mxcsr` with a sticky
flag, an unmasked exception or a reserved bit (G6, G7).

**F-MEMFAULT covers the load side only (finding R1-4).** The design (FUZZ-DESIGN §3.2) requires no fault **and
no write to masked-off memory** for masked loads and stores (Hearth's `_mm512_maskz_loadu_ps`,
`_mm_mask_storeu_ps`, `_mm256_maskstore_ps`). This harness tests loads folded into the arithmetic memory forms
the table has (VADDPS/VMULPS zmm m512, merge and, since the review, zero masking): no stub writes memory, the
driver inspects no memory after a stub, and `x2out` has no memory field. The table has no masked move or store
entry yet. **Before the census adds masked moves or stores**, the ABI needs a memory window, proposed here and
not built: a 128-byte window straddling the `PAGE_NOACCESS` boundary, pre-filled with a known pattern; store
stubs take `rax = window + offset`; after the stub the driver copies the readable part of the window into an
extended result record; `compare.py` compares it with the table's predicted memory image (masked-off bytes keep
the fill) and counts any write fault as a mismatch.

## 5. The C reference interpreter [M]

Exactness: ADD/SUB align significands exactly when the exponent gap is ≤ 40 and otherwise replace the
smaller operand by a sticky unit 2^(Ex−40), which keeps the exact sum strictly inside the same interval
between rounding boundaries; MUL is exact in 48 bits; DIV normalises both significands, forms a 41-bit
quotient and a sticky bit (rounding boundaries are ≥ 2^15 quotient units apart); tininess is detected
after rounding exactly as `rounding.py` (argument in `x2ref.h`).

Validation (`validate_interp.py`, FUZZ-DESIGN §4 "validated against the Python reference on 10^6
random cases before it is used"): **1,000,006 lane cases in 111,595 executions over all 491 stubs, 0
divergences** (byte-exact on the full destination, MXCSR, RFLAGS, k2, RAX, and the status), including
1,613 executions with an unmasked exception that both report as outside the model. Random MXCSR (any
RC, DAZ, FTZ, sticky flags), random masks, operands from the 12 value classes. Run time: generation,
C prediction and Python prediction together under 15 s on one thread. Vectors sha256
`ebed8cfed4f7216bc723e99829f7c8eb86b2baaa49ddd7b2b9ec76ef9c12e3e4`. Interpreter throughput: §8.

## 6. Generator [M]

Self-test (`gen_vectors.py --selftest`, no silicon): every class draw lies in its class (1,000 per f32
class), the forced values are present (DEN± min/max, BIG 0x7F7FFFFF, QNaN payloads 0/1/0x3FFFFF, SNaN
payloads 1/0x3FFFFF), 5,400 targeted cases verified by exact rational arithmetic (TIE: exactly halfway;
OVF: within 2 ulps of 2^128; UFL; F-FTZ-EXACT: exact and tiny; F-TINY in its band), every filler raises no
flag in any E8 environment and any predicate, rows regenerate byte-identically, and full iteration of
small rows yields exactly the planned lane cases.

**Plan against `budget_rows` over the v0 table: 428 sampled rows; 420 match exactly; plan total
399,683,714 lane cases against the budget's 399,797,314.** The 8 rows that differ are all i32→f32 rows
(7 V1 rows × 16,000 short, 1 V4 row × 1,600 short), from the first open item below.

### Open items found while building (pre-freeze; for the X2 record, not decided here)

1. **FUZZ-DESIGN §3.1 says "12 integer classes" but lists 10** (0, ±1, ±(2^24−1), ±2^24, ±(2^24+1),
   2^31−1, −2^31, small, large, tie). The budget's i32→f32 rows count 12 × 1,000 × 8; the generator
   implements the 10 listed and cannot meet them. Either two classes are named or the rows say 10.
2. **F-DAZ-CVT asks for RU/RD with DAZ = 0 and 1, but E8 contains no RU+DAZ or RD+DAZ environment**, and
   the V2 rows run under E8. Only the V5 sweep (4 RC × DAZ) reaches those combinations.
3. **DIV ties exist only on the subnormal grid.** A quotient of two 24-bit significands is never exactly
   halfway between two normal binary32 values; the generator's TIE class for DIV uses subnormal ties.
4. **F-TINY for DIV is unreachable in the stated band** [2^−126 − 2^−150, 2^−126): p/q ≥ 1 − 2^−24 with
   q < 2^24 is impossible. The before/after-rounding distinction for DIV exists only under directed
   rounding, at (1 − 1/q)·2^−126; the generator uses that band (it is the RU/RD part of E8).
5. FUZZ-DESIGN §3.2 lists OVF for CVTDQ2PS, but no int32 overflows binary32 (the budget rows already
   omit it).
6. F-MEMFAULT's text names prefix, single-bit and alternating masks; its budget row counts prefix masks
   only ((n + 1) × n). The generator follows the row. Since the review it also runs every prefix mask with
   **zero** masking. At the review they were uncounted duplicates; since 2026-10-23 they are counted, so an
   EVEX row with zero masking is 2 × (n + 1) × n (FUZZ-DESIGN §9.5 item 6). F-MEMFAULT is load-side only (§4).
7. F-MASKEXC has no budget row of its own. It is exercised by V3, whose heterogeneous lane vector puts an
   SNaN, a QNaN, a DEN and an overflow-producing value into masked-off lanes under every mask.
8. **Masked broadcast has no budget row (review finding R1-8).** `merge_bcast` and `zero_bcast` stubs exist for
   VADDPS and VMULPS zmm m512, but BCAST uses `plain_bcast` only and V3 the non-broadcast memory stubs, so
   masked broadcast, the combination Hearth-style tail code is most likely to hit, is run by no row. This
   track **kept the stubs** (decode-checked; the review's cross-section ran them and they matched the table;
   mutant M13 is detected on them) and the generator implements a masked BCAST row (`gen_vectors.bcast_masked`,
   reached by a BCAST row whose class starts with `masked`; per mode 144 class pairs × 10 draws × n lanes,
   random write mask per execution; 46,080 lane cases for a zmm form, self-tested on a synthetic row).
   **Proposed for `budget.v1` before freeze:** add that row for every EVEX memory form with EVEX.b. Whether to
   add it is the record's decision (pending the X2 record's review).
9. **Masked `{er}` / `{sae}` has no stub (same finding).** `{er}` and `{sae}` stubs are generated for the plain
   (unmasked) variant only. Proposed for the record: either add merge/zero `{er}`/`{sae}` variants and V4 rows,
   or state that masking with embedded rounding is out of scope because Hearth does not use it [inference from
   b5d3f14 until the census].

## 7. Development smoke run on the selftest.py hand vectors [M] x2build 2026-10-16 desktop

Not data under the X2 record. `devsmoke.py` **extracts** the hand vectors (it does not retype them):
sections A-D of `selftest.py` run with `check` and the lane functions instrumented; each passing check
whose value came from one top-level lane-function call yields (label, operands, environment, hand
expectation). 299 hand vectors were extracted and placed in lane 0 of 780 executions over several
entries of their family (EVEX scalar and zmm, VEX, legacy; flag-neutral fillers elsewhere), plus 20
vector-level cases rebuilt under their selftest labels (C2, C3, E1-E8: masks, broadcast, scalar upper
lanes, `{er}`, full-width converts, RFLAGS). 800 executions, run twice: CPU 4 and CPU 20, in different L3
groups (measured masks 0xFFFF and 0xFFFF0000, i.e. CCD0 and CCD1).

| Measure | Result |
|---|---|
| C interpreter vs Python oracle | 0 divergences on 800 |
| Silicon run 1 vs run 2 (two CCDs) | identical (0 nondeterminism) |
| Harness anomalies (exceptions, MXCSR control changes) | 0 |
| Lane mismatches (silicon vs table) | 0 |
| Execution flag mismatches | **3**, all one hand vector |
| Hand expectation = silicon | 777 of 780 lane executions |

**The one disagreement: selftest B6 "den / +0: DE and ZE both recorded".** For `0x00000001 / +0` the
9950X returns +∞ (as predicted) but sets **ZE only**; the table (and the hand expectation, a reading
recorded in TABLE-SCHEMA §4 rule 7 and the F-FLAGPRI row of the uncertainty register) predicts DE|ZE.
Same on all three encodings tried (VDIVSS EVEX, VDIVSS VEX, DIVSS legacy) and both CCDs. Bochs 3.1 also
gives ZE only (§9), so in FUZZ-DESIGN §6.3 terms this case reads "table bug" (table ≠ silicon = Bochs).
Fixing the reading is the table owner's decision. Because it is pre-freeze information about an
uncertainty class, the X2 record should state, before freeze, that it was seen.

**The same reading fails off the hand vector (review finding R1-11, verified).** The review's development
cross-section (DEV-REVIEW-X2BUILD, identical on CPU 6 and CPU 22) shows flag-only mismatches of the B6 kind
outside `0x00000001 / +0`, in other environments and with −0. Re-compared here with the revised comparator
(§9; [devlogs/xsec.report.json](devlogs/xsec.report.json)):

| Record | Instruction | Operands | MXCSR before | Silicon MXCSR after | Table MXCSR after |
|---|---|---|---|---|---|
| 2963 | VDIVSS (VEX) | 0x004C24E3 / +0 | 0x7F80 (RZ) | 0x7F84 (ZE) | 0x7F86 (DE\|ZE) |
| 3569 | DIVSS (legacy) | 0x8078165D / −0 | 0x7F80 (RZ) | 0x7F84 | 0x7F86 |
| 3571 | DIVSS (legacy) | 0x80717657 / +0 | 0x9F80 (FTZ) | 0x9F84 | 0x9F86 |

No other table/silicon disagreement occurred in the 4,504 cross-section executions. Together with the dev
smoke this says the "DEN / ±0 raises DE and ZE" reading is wrong across environments and signs, not only for
the hand vector. **For the X2 record's pre-freeze disclosure and the F-FLAGPRI note** (not this track's file):
these three cases with the B6 hand vector. Whether the reading becomes "DEN / ±0 raises ZE only" is the table
owner's decision (provisional, pending the record's review); the harness needs no change.

The readings this smoke touched without disagreement include tininess after rounding (A13, F-TINY's UE
part), FTZ flushing an exact tiny product with UE|PE (A12), MAX under DAZ returning the flushed zero (B4),
CVT of a denormal under RU with DAZ (D2), VCVTPH2PS ignoring DAZ (D4), the other three B6 coexistence
readings (∞·DEN and DEN/DEN under DAZ give IE only; DEN + ∞ gives DE), and masked-off SNaN lanes raising
nothing (E1). One development vector per reading is not a class result.

## 8. Final build and measurements [M] x2build 2026-10-16 desktop

The numbers in §3 and §5-§7 come from one consolidated run of the **revised** sources: `run_final.cmd`
(21:51:40 to 21:52:10 desktop clock, 2026-10-16; log in [devlogs/final.log](devlogs/final.log)): build,
every self-test, the interpreter validation, the guard checks, the dev smoke, and the throughput
measurements below. The first build's run (19:10:31 to 19:11:02) is kept as `devlogs/*.build1.*`; every
result it shared with this run is identical (stub manifest, validation vectors and counts, dev smoke vectors
and counts, the exhaustive self-test stream hash `0bc9da37…`). After this run one docstring line of
`gen_vectors.py` was corrected (a section reference); no code changed, but the generator's own hash, and so
the header of the throughput slice `gen_tp.vec`, differ from the logged run.

| Item | Value |
|---|---|
| Stub manifest SHA-256 (`stubs_manifest.json`, 510,631 bytes) | `03fe7a69abc7281279a4815d8291f83ddbcc637189adea4e0d2ec1aa4421a529` (unchanged) |
| Semantics bundle (same as the laptop's) | `4c48899cb3cad78c5bba6e29129d1eb9391cb8160148b33e1ba91c7968a3ea31` |
| Interpreter sources (`X2_INTERP_SRC_SHA256`, `x2ref.h` + `x2ref.c`) | `80ad6745bbb8a05013c28c25e4a963bca49325aac3799d903313ccf5cd0703c0` (unchanged) |
| Harness sources (`X2_HARNESS_SRC_SHA256`) | `a18b07eecea415fc63ff7a47b8fdaa335e2b2dcdf3d3e09b040871571b7e633e` (first build `f82e6c7e…`) |
| `x2fuzz.exe` | `2348e97f890d8ec10a599a054ee5b06eee33860d5e00f359232daef7270b78cb` (first build `b9901a9f…`) |
| Compiler | MSVC `_MSC_FULL_VER` 194435229, `/O2 /W4 /MP1`, no warnings |
| Fingerprint | AuthenticAMD, family 26 model 68 stepping 0 (CPUID.1.EAX 0x00B40F40), "AMD Ryzen 9 9950X 16-Core Processor", microcode 0x0B404023 (registry "Update Revision", 4 bytes here), Windows 26200.9711 (25H2), L3 groups 0xFFFF and 0xFFFF0000 |
| `semantics.selftest` on the desktop | 706 checks, 0 failures |
| `x2fuzz selftest` | PASS, 9 steps: SHA-256 known answers, ABI layout, 29 interpreter known answers, stub table integrity, CPU features, MXCSR round trip (8 values), 64 random register/mask/GPR/RFLAGS/MXCSR plumbing trials on the EVEX and VEX paths, fault capture on the `PAGE_NOACCESS` page, exhaustive engine (interpreter as oracle: 0 mismatches; same stream hash on 1 and 2 threads; a seeded interpreter mutant gives exactly the expected 256 mismatches; **the mismatch-record cap stops a sweep with status `flood`**), and **step 9, the exhaustive engine's silicon plumbing check: all 40 V5-eligible stubs × 4,096 inputs (0x3F000000-0x3F000FFF, MXCSR 0x1F80) on CPU 4, 0 mismatches, and each stream hash equal to the interpreter's** (development check; the first build had no silicon test of this path, review blocker R1-1). Scratch directory `--scratch` (default `%TEMP%\x2fuzz_selftest`) |
| `compare.py --selftest` | PASS, including the review's Bochs scenario (table = silicon ≠ Bochs gives exactly one "Bochs differs"; a Bochs exception is a Bochs anomaly), four provenance refusals (swapped vectors hash, swapped manifest hash, shuffled indices, short file) and the sticky-flag anomaly |
| `gen_vectors.py --selftest` | PASS; plan = budget on 420 of 428 rows as before; 4 F-MEMFAULT rows with 34 zero-masking duplicates; masked BCAST synthetic row 46,080 lane cases in 2,880 executions |
| Guards (`run_guards.cmd`) | G1-G7 all refused with exit code 2, no results file: a BUDGET-labelled F-MEMFAULT slice (label), the same rows under a DEV label made with `--dev` (budget set ids), a DEV label without `--dev`, `--dev` without `--limit`, a silicon sweep without authorisation, MXCSR 0x1F81 (sticky flag) and 0x1F00 (unmasked exceptions) |

Throughput (no silicon involved; single runs, [M] rev. run, first-build values in brackets):

- **C interpreter, predict mode** on the validation vectors: 1,000,006 lane cases (111,595 executions)
  in 0.60 s [0.76 s] end to end, file I/O included, i.e. about 5-7 µs per execution and 0.6-0.8 µs per lane case.
- **C interpreter in the exhaustive engine** (interpreter as its own oracle, VCVTPS2DQ zmm, 2^28 lane
  cases in 16,777,216 executions, one thread, stream hash included): 6.67 s [6.55 s], i.e. **about 25 ns per
  lane case**; stream hash `2ccba7c9…`. [D] At that rate the V5 sweeps of the v0 table (5.9 × 10^11 lane cases)
  need about 4.0 h of one thread for the predictions, about 2 h on this track's 2 threads and about 30 min on
  8. FUZZ-DESIGN §5 had assumed 20-50 ns per case on 32 threads (6-15 min). The comparison of observable
  bytes added by the revision does not change the self-oracle rate measurably.
- **Python generator**: 20,000 V1 executions of VADDPS zmm (320,000 lane cases) in 1.09 s [1.23 s] wall,
  start-up included, about 55-61 µs per execution. [D] The full sampled budget of the v0 table is about
  1.15 × 10^8 executions (counted from `budget_rows` with the generator's packing). That is about 2 h of one
  thread at that rate, a lower bound because targeted classes cost more per case [G], and a 36.7 GB vectors
  file at 320 bytes per execution (results files 160 bytes per execution).

## 9. Seeded table mutants: the calibration arm of FUZZ-DESIGN §6.4 [M] x2build 2026-10-16 desktop

Built after the review (finding R1-10), adopting the review's prototype: [mutants/mutants.py](mutants/mutants.py)
holds 24 mutants as anchored one-line edits of a copy of `semantics/` (each anchor must occur exactly once,
so a mutant cannot be applied to a table it was not written for); M01-M10 are the ten §6.4 mutants, M11-M24
harness-path and further readings. [mutants/run_mutants.py](mutants/run_mutants.py) predicts a vector set
with each mutated table (`pyref.py`) and compares with **unchanged** silicon results (`compare.py`); a mutant
is detected when the disagreements differ from the unmutated baseline. Comparator time only.

**Seal.** `mutants.py --seal` prints the sha256 of `mutants.py` (LF-normalised) and of each mutant's edit:
spec sha256 `a74d50412a976ececc9355ff2434e3d7c3c08c40eea9f0627378dc4a6ab2802c` (24 mutants; per-mutant hashes in [devlogs/mutants.summary.json](devlogs/mutants.summary.json)). The X2 record must name it before the first native run of the budget (FUZZ-DESIGN §6.4);
the record is not this track's file, so this is a request to the record's author.

**Calibration on development data** ([run_mutants_dev.cmd](run_mutants_dev.cmd)). No budget silicon results
exist, so the runner was exercised on the review's development cross-section (label `DEV-REVIEW-X2BUILD`:
every stub with a few random executions plus 24 F-MEMFAULT probes, 4,528 executions; run by the review on CPU 6
and CPU 22), copied, not modified, and re-compared with the revised comparator: the provenance checks pass (vectors `2237271f…`, the review's silicon results on CPU 6 and CPU 22, manifest `03fe7a69…`); 4,528 executions, 36,176 lane cases, **0 C-vs-Python divergences, 0 nondeterminism between the two CCDs, 0 harness anomalies**; the disagreements are exactly the review's 8 deliberately faulting F-MEMFAULT probes (an active lane on the `PAGE_NOACCESS` page; 128 lane mismatches, verdict "fault", as intended) and 3 flag-only B6 cases (§7) [M] rev. 2026-10-16 desktop ([devlogs/xsec.report.json](devlogs/xsec.report.json)).

Mutants: **23 of 24 detected; all 10 of the §6.4 list detected** [M] rev. 2026-10-16 desktop, `run_mutants_dev.cmd`, 22:05:31 to 22:05:41 ([devlogs/mutants.summary.json](devlogs/mutants.summary.json)). Every count equals the review's prototype run. The miss is M23 (VPDPBUSD saturating instead of wrapping): the cross-section's random accumulators never cross ±2^31, a limit of that vector set, not of the harness; the budget's V2 wrap rows exist to catch it.

| Mutant | §6.4 list | Detected | New / changed disagreeing executions | Kinds (lane, upper, flag-only, fault) | Stubs hit |
|---|---|---|---|---|---|
| M01_tiny_before_rounding | yes | **yes** | 74 / 0 | 24, 0, 50, 0 | 1 |
| M02_max_returns_src1_on_nan | yes | **yes** | 166 / 0 | 166, 0, 0, 0 | 33 |
| M03_nan_not_quieted | yes | **yes** | 242 / 0 | 242, 0, 0, 0 | 57 |
| M04_cmp_pred_shift | yes | **yes** | 1784 / 0 | 1772, 0, 12, 0 | 279 |
| M05_indefinite_7fffffff | yes | **yes** | 201 / 0 | 201, 0, 0, 0 | 30 |
| M06_ftz_no_flush_exact | yes | **yes** | 73 / 0 | 73, 0, 0, 0 | 18 |
| M07_daz_applies_to_h2f | yes | **yes** | 16 / 0 | 16, 0, 0, 0 | 9 |
| M08_masked_lanes_raise_flags | yes | **yes** | 194 / 0 | 0, 0, 194, 0 | 55 |
| M09_pmaddubsw_swapped | yes | **yes** | 82 / 0 | 82, 0, 0, 0 | 11 |
| M10_er_disables_daz | yes | **yes** | 19 / 0 | 19, 0, 0, 0 | 11 |
| M11_zeroing_as_merge |  | **yes** | 228 / 0 | 228, 0, 0, 0 | 28 |
| M12_vex_evex_upper_preserved |  | **yes** | 2079 / 1 | 0, 2080, 0, 0 | 188 |
| M13_bcast_ignored |  | **yes** | 39 / 0 | 39, 0, 0, 0 | 6 |
| M14_comis_sets_of |  | **yes** | 32 / 0 | 32, 0, 0, 0 | 4 |
| M15_cvt2si_sign_extends |  | **yes** | 13 / 0 | 13, 0, 0, 0 | 3 |
| M16_kdest_upper_not_zeroed |  | **yes** | 1792 / 0 | 0, 1792, 0, 0 | 224 |
| M17_add_never_pe |  | **yes** | 100 / 0 | 0, 0, 100, 0 | 23 |
| M18_legacy_upper_zeroed |  | **yes** | 54 / 2 | 0, 56, 0, 0 | 7 |
| M19_er_without_sae |  | **yes** | 178 / 0 | 0, 0, 178, 0 | 28 |
| M20_rd_ru_swapped |  | **yes** | 288 / 0 | 288, 0, 0, 0 | 62 |
| M21_i2f_always_rne |  | **yes** | 51 / 0 | 51, 0, 0, 0 | 15 |
| M22_scalar_upper_from_src2 |  | **yes** | 901 / 3 | 0, 904, 0, 0 | 41 |
| M23_vpdpbusd_saturates |  | **no** | 0 / 0 | 0, 0, 0, 0 | 0 |
| M24_daz_raises_de |  | **yes** | 449 / 0 | 0, 0, 449, 0 | 252 |

What this shows: the runner and the comparator detect table misreadings of every kind the list covers, on a
cross-section with 8 executions per stub. It is not the calibration the record asks for: that target (every
§6.4 mutant detected) applies to the frozen budget's silicon results, where VPDPBUSD saturation must be caught
by the V2 wrap rows.

## 10. Second oracle: Bochs feasibility [M]

See [bochs/README.md](bochs/README.md). The comparator's Bochs path was corrected after the review (§1,
finding R1-2); the Bochs production image that would produce Bochs results files is not built.

## 11. Review log

| Date | Reviewer | Lens | Family | Findings | Outcome |
|---|---|---|---|---|---|
| 2026-10-16 | reviewer 1 | harness soundness (driver, exhaustive mode, comparator, guard, generator, stubs) | Claude, **same family, independent context** | 11: 1 blocker, 3 major, 7 minor | all 11 accepted; 10 fixed in code or docs and re-run, 1 (R1-11) recorded as information for the record |
| 2026-10-16 | reviewer 2 | proof routes (proofs/, RULES.md §8) | Claude, **same family, independent context** | 10: 4 major, 6 minor | all 10 accepted; see proofs/README.md §9 |

Reviewer 1, finding by finding (verified by the reviser before acting; "[M] rev." = re-measured 2026-10-16):

| # | Severity | Finding | Verified how | Action |
|---|---|---|---|---|
| R1-1 | blocker | exhaustive mode compared the whole `x2out`, so every silicon execution of a V5 sweep was a mismatch (unmodelled RAX / old destination); a 2^32 sweep would write ~128 GiB | code read: stubs store RAX and the destination register for every stub, `x2_predict` zeroes the block; the review's 26,368-of-26,368 measurement | **fixed**: compare the hashed observable bytes only; refuse unmodelled inputs; flood cap (10^6 records, status `flood`, exit 3); self-test step 9 runs all 40 V5-eligible stubs on silicon (4,096 inputs each): 0 mismatches, stream hashes equal to the interpreter's [M] rev. |
| R1-2 | major | Bochs consulted only where silicon disagreed: "Bochs differs" impossible, Bochs status ignored | code read | **fixed**: Bochs compared on every record; per-cell `bochs_mismatch`, `bochs_anomaly`; "Bochs differs" entries; self-test with the review's exact scenario |
| R1-3 | major | guard keyed on the self-declared label; generator default `DEV-GEN` | code read (`--label` default, `label_is_dev`) | **fixed**: generator default `BUDGET-v1-<set>`, DEV labels need `--dev` with `--limit` ≤ 100,000; `x2fuzz run` refuses budget set ids without authorisation whatever the label; guard checks G1-G7 [M] rev.; note for the record's collection procedure (§4) |
| R1-4 | major | F-MEMFAULT store side not runnable: no stub writes memory, no memory observable | code read (`masm_stub`, `cmd_run`) | **fixed in scope and docs**: FUZZ-DESIGN §9.1 and §4 here narrowed to "load side (arithmetic m512 forms) only"; memory-window ABI extension specified for before the census adds masked moves/stores; zero-masking F-MEMFAULT executions added (uncounted duplicates) |
| R1-5 | minor | no provenance check in `compare.py` | code read | **fixed**: header vectors hash, manifest hash, record count and per-record index checked for every results input; producers reported; 4 refusal self-tests |
| R1-6 | minor | MXCSR loaded verbatim; preset sticky flags would hide flags; exhaustive accepted any `--mxcsr` | code read | **fixed**: UNMODELED outside VALID sets; comparator anomaly; exhaustive refuses sticky flags, unmasked exceptions, reserved bits (G6, G7) |
| R1-7 | minor | decode-back check did not verify the immediate | code read; XED output format checked on the desktop (`IMM0:0x1f`) | **fixed**: IMM0 and last byte checked, negative control; 288 stubs, 0 errors, manifest unchanged [M] rev. |
| R1-8 | minor | masked broadcast and masked `{er}`/`{sae}` run by no budget row | code read (`bcast()` uses `plain_bcast`; `variants()` makes `{er}`/`{sae}` plain only) | **accepted, decision left to the record**: stubs kept; generator implements a masked BCAST row (self-tested); rows proposed (§6 items 8, 9) |
| R1-9 | minor | self-test wrote fixed paths under this track's job directory | code read | **fixed**: `--scratch` (default `%TEMP%\x2fuzz_selftest`), printed |
| R1-10 | minor | §6.4 mutant arm not built | `harness/` listing | **fixed**: `mutants/` adopted from the review's prototype, sealed by hash, calibrated on development data (§9) |
| R1-11 | minor (information) | B6 kind of flag-only mismatch outside the hand vector (RZ, FTZ, −0) | the review's silicon results re-compared with the revised comparator (§7) | **recorded** in §7 and FUZZ-DESIGN §9.3 for the record's pre-freeze disclosure; the reading is the table owner's decision (provisional, pending the record's review); no harness change |

## 12. Not done here

- No vector of `budget.v1` was generated for silicon, and no class cell, V5 sweep or Bochs budget ran.
- The F-MEMFAULT store side (memory-window ABI, §4) and the Bochs production image are not built.
- The masked BCAST and masked `{er}`/`{sae}` rows are proposals for the record (§6 items 8, 9).
- The mutant seal and the B6 cases must be carried into the X2 record by its author before freeze.
- The 10^6-case interpreter validation is the pre-use check of FUZZ-DESIGN §4; the week-1 measurement of
  interpreter ns per case is in §8; silicon throughput was not measured on table instructions (that would
  need non-hand vectors).

## 13. Rebuild for the X2 freeze (2026-10-23, x2freeze track) [M] desktop

Why: X0 census run 1 added 26 table entries (TABLE-SCHEMA §9.1), the B6 reading was corrected (ZE alone for a
denormal over ±0; TABLE-SCHEMA §4 rule 7), and the budget formula was made final (FUZZ-DESIGN §5, §9.5). Sources
were copied to `D:\mithril\x2\src` (zip sha256 `77367fa0…6ed3`); the previous trees are kept as
`D:\mithril\x2\{src,build,dev}.20261016` and the two intermediate rebuilds of the day as `.20261023a`/`.20261023b`.
Desktop rules kept: 2 threads at most (`/MP1`, single-thread runs, the 2-thread exhaustive self-test step),
`CUDA_VISIBLE_DEVICES=-1`, TEMP and TMP on D:, daytime, no WSL. Logs: `devlogs/*.20261023.*`.

Code changes:
- `stubgen.py`: builder `cmp_scalar` (11), lane function `cvt_i64_to_f32` (15), GPR64 operands (`rax`), EVEX
  forms without a write mask get the plain variant only, EVEX (V)UCOMISS uses xmm17/xmm18.
- `x2ref.c`/`x2ref.h`: B6 (ZE alone), `x2_cvt_i64_2f`, `X2B_CMP_SCALAR`, the scalar compare into k, legacy packed
  forms read src1 from the destination, a unary memory source is read from the src2 slot (RAX = &src2), the
  integer path no longer keys on `builder >= X2B_INT2`.
- `x2fuzz.c`: the B6 known answers corrected (plus two silicon vectors), the stub-table check admits builder 11,
  CVTSI2SS r64 is not V5-eligible (2^64 inputs).
- `pyref.py`, `gen_vectors.py`, `validate_interp.py`, `devsmoke.py`: the same semantics; 12 integer classes and
  12 64-bit classes; F-MEMFAULT zero-masking executions counted; the new forms in the dev smoke (E9 vector cases).
- `run_mutants_devsmoke.cmd` (new): the sealed table mutants against the dev smoke results.

| Item | Value |
|---|---|
| Stubs | **664**, 0 encode or decode-back errors, 432 immediates checked, negative control reported; **every stub decodes to its entry's key** (the 11 provisional keys included) |
| Stub manifest | `63aa76b2dfe98614429071ef996adb7e4e7ef4d54f00c6fde87c55b19abe3a32` |
| Semantics bundle | `c7cd6851b574af85ebd36091c66f336156f8ab657869a059302e91fc29793eb8` |
| Interpreter sources / harness sources | `bbac5d7c45e529b484cdcfc00f0163af0d7a71afd8a1e655850e046fe53f6c35` / `40038ee26787168ce41eaf706c09b6074698dabe2af9ce283dc1482b0cc8d273` |
| `x2fuzz.exe` | `4e33feb04dcad538ab624badc7cdbd0f8e3fb3abe3e502e731407c8ce1f173b8`, MSVC `_MSC_FULL_VER` 194435229, `/O2 /W4 /MP1` |
| Fingerprint | family 26 model 68 stepping 0, microcode `0x0B404023`, Windows 26200.9711, L3 groups `0xFFFF`, `0xFFFF0000` |
| `x2fuzz selftest` | PASS; 31 interpreter known answers; exhaustive engine and the silicon plumbing check (**42** V5-eligible stubs × 4,096 inputs, 0 disagreeing; stream hash of the self-oracle test `0bc9da37…`, unchanged) |
| `semantics.selftest` | 720 checks, 0 failures |
| `compare.py --selftest`, `gen_vectors.py --selftest` | PASS, PASS (plan = budget on 576 sampled rows, 539,690,903 lane cases) |
| Interpreter validation | 1,000,006 lane cases in 140,531 executions over all 664 stubs, **0 divergences** (2,032 outside the model in both); vectors `8b0fa839…1b85` |
| Guards G1-G7 | all refused (exit 2, no results file) |
| Dev smoke (DEV-SMOKE) | 303 hand vectors extracted + 30 vector cases, 1,593 executions on CPU 4 and CPU 20: **0 lane mismatches, 0 flag mismatches, 0 divergences, 0 nondeterminism, 0 anomalies**; hand = silicon on 1,563 of 1,563 lane executions; vectors `2ed8b426…f10a` |
| Seeded table mutants on the dev smoke | 21 of 24 detected (8 of the 10 of §6.4); not detected M09, M10, M23: the hand vectors have no integer case and no `{er}` case under DAZ. Not the calibration the record asks for (that runs on the frozen budget's silicon results) |

Not done here: no budget vector generated for silicon; no cross-section of the 26 new forms beyond the dev smoke's
hand vectors (they run through every new form's plain stub); the Bochs production image; the F-MEMFAULT store side.

## 14. Revision 4 rebuild (2026-10-23, after the review of the X2 record's revision 3) [M] desktop

Why: the review found that the legacy CMPPS/CMPSS entries predicted reserved immediates (8-31), that the 64-bit
conversion had no sticky-bit construction, and stale docstrings (record §12, TABLE-SCHEMA §15). Sources: zip sha256
`ee452553…0c5b` (the same 47 files as §13's) to `D:\mithril\x2\src`; the §13 trees are kept as
`D:\mithril\x2\{src,build,dev}.20261023c`. Desktop clock 16:55:03 to 16:56:25 (laptop 13:55-13:56 PT); 2 threads
at most. Logs: `devlogs/*.20261023d.*`.

Code changes:
- `x2ref.c`: `x2_predict` refuses a compare whose imm8 is outside the entry's domain (legacy 0-7, VEX/EVEX 0-31).
- `x2fuzz.c`: self-test step 4b: the legacy CMPPS and CMPSS stubs predict imm 7 and refuse imm 8.
- `pyref.py`: a refused compare immediate is reported as unmodeled (as the C interpreter does).
- `gen_vectors.py`: CVT-BND for CVTSI2SS r64 adds ties ± 1 above 2^32 (`c_tie_sticky64`: T + 1 has the round bit
  set and only bit 0 below it, 8-38 places down; T − 1 has the round bit clear and every bit below set; a fifth of
  the row's draws, 16,024 of 80,000 lane cases [M, laptop]) with a self-test (300 draws: one away from a tie, never
  a tie, never exact, both directions); docstrings and comments on F-MEMFAULT counting, masked broadcast and the
  64-bit classes corrected. Final file `4261242d38952a1487819c8aa1b17bdd103e7d55f3bb6736f8282ac5245aa6e2` (LF): a
  docstring-only correction after the run below; its self-test and the guards were re-run on the desktop with it
  (PASS; G1-G7 refused; `devlogs/gen_selftest.20261023e.log`, `devlogs/guards.20261023e.log`).

| Item | Value |
|---|---|
| Stubs | **664**, 0 encode or decode-back errors, 432 immediates checked, negative control detected; every stub decodes to its entry's key |
| Stub manifest | `430fc5266ef730afb2d280ce3d1c0bf9c701b6ebd80ee7d9ea98083108876260` |
| Semantics bundle | `0c2a041c363e34ee27a62a873fd0adad5cf8f5711ec2aa3a16cb2f5c9709ff2d` |
| Interpreter sources / harness sources | `44e29a371dfb0799804fcbaf9fc36d8781f2de6efb5d275acac800d4dbada17c` / `a17f41baf1b6ca886a5273dab63a3b1925df57a16df16f6bb1c53811ad2eb112` |
| `x2fuzz.exe` | `0feae9334e9ba51bcae3bfa43bdbe1d9d3544a3295ce821bb5be9b8550dcde4c`, MSVC `_MSC_FULL_VER` 194435229, `/O2 /W4 /MP1` |
| Fingerprint | family 26 model 68 stepping 0, microcode `0x0B404023`, Windows 26200.9711, L3 groups `0xFFFF`, `0xFFFF0000` |
| `x2fuzz selftest` | PASS (step 4b included); exhaustive plumbing check 42 V5-eligible stubs × 4,096 inputs, 0 disagreeing; self-oracle stream `0bc9da37…`, unchanged |
| `semantics.selftest` | 725 checks, 0 failures |
| `compare.py --selftest`, `gen_vectors.py --selftest` | PASS, PASS (plan = budget on 576 sampled rows, 539,690,903 lane cases; 5,700 targeted cases checked) |
| Interpreter validation | 1,000,006 lane cases in 140,531 executions over all 664 stubs, **0 divergences** (2,032 outside the model in both); vectors `70e63c11…2452` |
| Guards G1-G7 | all refused (exit 2). The first invocation stopped after G1's refusal because the PowerShell wrapper treated the refusal message on stderr as an error; it was re-run with the redirection inside `cmd` and all seven refused |
| Dev smoke (DEV-SMOKE) | the same 303 hand vectors + 30 vector cases, 1,593 executions on CPU 4 and CPU 20: **0 lane mismatches, 0 flag mismatches, 0 divergences, 0 nondeterminism, 0 anomalies**; hand = silicon on 1,563 of 1,563; vectors `aa3e9143…baa7` |
| Seeded table mutants on the dev smoke | 21 of 24 detected; not detected M09, M10, M23 (as in §13) |
| `x2_gate.py --selftest` | PASS, 24 cases (laptop and desktop) |
