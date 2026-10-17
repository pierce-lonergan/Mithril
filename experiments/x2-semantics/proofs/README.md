# X2 rule proofs (rules.v1 draft 2): runs of 2026-10-16, revised after review

Status: DRAFT. The proofs RULES.md §3.1 marked "not yet run" were run on 2026-10-16 by the x2build track
("first run"), plus the second routes of rows whose primary was already proved. A same-family,
independent-context review of that run (§9) found that several routes did not evaluate the table where the
record said they did; the reviser corrected the routes and re-ran what changed ("rev1", the same evening).
Every number here is [M] x2build 2026-10-16 on the desktop (AMD Ryzen 9 9950X, Windows 11 26200.9711), unless
tagged otherwise. `rules.v1` is not frozen; nothing here is a verdict-run result of the X2 record (the gate
counts rules only at the verdict). A failed or inconclusive proof is reported as such.

"Proved" follows RULES.md §1: the primary route succeeded **and** an independent second route agreed. For
integer rows a QF_BV primary counts only with an agreeing exhaustive or second-solver route (provisional,
pending the Owner's answer to RQ-3). **Since the review, a route counts as evidence about the table only if it
evaluates the table's entries** (directly, or through an encoding checked against them by a recorded
differential); routes that check an IEEE definition, a transliteration against itself, or an algebraic
identity with no table operation are listed with that label and do not count as table routes.

## Routes and tools

| Route | Tool | What it evaluates | Artefact |
|---|---|---|---|
| Exhaustive enumeration through the C reference interpreter of the table (`../harness/x2ref.c`, validated against the Python reference on 1,000,006 lane cases, 0 divergences) | `x2prove.c`, MSVC 19.44.35229 `/O2`; first run 2 threads, rev1 1 thread | per rule, `route_kind`: **table** (lane functions, or whole instructions through `x2_predict` and the EVEX masking function `x2_masked`), **table+translit** (a data-movement op without a table entry transliterated from `int_ops.py`: AND, BLENDVPS, PABSB/PSIGNB, packs), **algebraic** (no table operation: R15, R16), **differential** (DIFF-*, HASH-*) | `results/exhaustive.json` (first run), `results/rev1/exhaustive*.json` |
| Z3 (primary for FP rows; QF_BV for integer rows) | `z3_rules.py`, `z3_int.py`, z3-solver 5.3.1.0 (PyPI wheel, SHA-256 `10829bb3…bd8e67` = PyPI digest), 1 thread | ADD/SUB/MUL/MAX/MIN/CVT through `semantics/smt_encoding.py` (32,192-comparison differential, RULES.md §3.2); **since rev1** compare, (U)COMISS and VCVTPH2PS through `smt_table.py` (pure BV, transliterated from `fp_ops.py`, own differential); integer lane formulas from `int_lanes.py` (own differential); reduction trees from `trees.py` (own differential and unit-basis check) | `results/z3.json`, `z3_b.json`, `int.json`, `int_export.json`; `results/rev1/z3.json`, `int.json` |
| Second solver: each exported query replayed | `second_solver.py`, cvc5 1.4.2 (PyPI wheel, SHA-256 `0ee0a518…11b9da` = PyPI digest), 1 thread | the same SMT-LIB 2 file | `results/cvc5*.json`, `results/rev1/cvc5*.json` |
| R02/R03 written proof from lemmas | `z3_fold.py` (lemmas, Z3), cvc5 replay, [R02-R03-proof.md](R02-R03-proof.md) | lemmas on the same encodings | `results/fold.json`, `results/rev1/fold.json`, `cvc5_fold.json` |
| Encoding differentials | `smt_table.py`, `int_differential.py`, `trees.py` | SMT terms evaluated on concrete inputs against `semantics/fp_ops.py`, `int_ops.py`, `hearth_kernels.py` | `results/rev1/differential_smt_table.json`, `int_differential.json`, `trees.json` |

Data-movement operations that have no table entry yet (BLENDVPS, masked moves, PACKSSDW/PACKSSWB,
PABSB/PSIGNB, VPAND) are transliterated from `semantics/int_ops.py` in the C and SMT routes, as the Python
compositions do (`hearth_kernels.unregistered_used()`); their transliterations are now tied to `int_ops.py`
by §2. Their entries are a table task. The EVEX masking of masked moves is the table's own masking function
(`int_ops.masked`, `x2_masked`).

Hashes (rev1): `x2prove.c` `a4507f7936139bf689294bd50a794370e1b2a0fd68b855bf6c56e5ef8bc48803` (first run
`11fcad86…`); interpreter sources `80ad6745bbb8a05013c28c25e4a963bca49325aac3799d903313ccf5cd0703c0` (unchanged);
`x2prove.exe` `0070718e5b98cd178028fb60a38034b1efc3162aa41cd0e582a7bc0fca5e218b` (first run `de0b45cb…`); every
rev1 `exhaustive*.json` names the x2prove source, interpreter source and compiler itself (finding R2-9).

## 1. Exhaustive routes [M]

"In condition" = inputs that satisfy the rule's side condition; "fail in" must be 0 for the route to agree
with the rule; "fail out" shows whether the side condition is load-bearing.

### 1.1 Default environment (MXCSR 0x1F80)

rev1 (`results/rev1/exhaustive.json`, 1 thread, desktop clock 21:52:42 to 22:03:40); every count equals the first run's
(`results/exhaustive.json`, 2 threads, 321 s) where the route is unchanged. Times are single runs.

| Row | Route kind | Domain | Inputs | In condition | Fail in | Fail out | Notes | s (rev1, 1 thread) |
|---|---|---|---|---|---|---|---|---|
| R04 MIN-SEL-127 | table | all v | 4,294,967,296 | 4,278,190,082 (non-NaN) | **0** | 16,777,214 | every NaN v fails: the side condition is load-bearing | 18.7 |
| R05 MAX-SEL-M127 | table | all v | 4,294,967,296 | 4,278,190,082 | **0** | 16,777,214 | as R04 | 18.9 |
| R06 ISNAN-UNORD | table: VCMPPS ymm (VEX) through `x2_predict` | all v | 4,294,967,296 | all | **0** | 0 | first run: compare lane function | 15.6 |
| R07 NOTNAN-ORD | table: VCMPPS ymm | all v | 4,294,967,296 | all | **0** | 0 | | 15.4 |
| R08 ANDMASK-SELECT | table+translit: VCMPPS ymm ORD_Q, AND | act_q8 instance, all p | 4,294,967,296 | all | **0** | 0 | the first run's "generic" (x, c) loop compared C `&` with its own definition; removed | 15.4 |
| R09 BLENDV-SELECT | table+translit: VCMPPS ymm UNORD_Q, BLENDVPS | canon8 instance, all v | 4,294,967,296 | all | **0** | 0 | generic loop removed (as R08) | 15.5 |
| R10 MASKMOV-SELECT | **table**: VCMPPS zmm into k through `x2_predict`, merge-masked move through `x2_masked` | canon16 instance, all v | 4,294,967,296 | all | **0** | 0 | first run: transliterated `blendk_lane`; its generic loop compared the transliteration with its own definition (finding R2-1) | 19.2 |
| R11 MASKZMOV-SELECT | **table**: VCMPPS zmm into k (ORD_Q), zero-masked move through `x2_masked` | act_q8 instance, all p | 4,294,967,296 | all | **0** | 0 | as R10 | 18.3 |
| R12 INT-DOT-VNNI | table: `x2_dpbusd_lane` | pairs (u0, x0, u1, x1) at byte positions (0,1) **and (2,3)**, acc 0 | 8,589,934,592 | all | **0** | 0 | plus every product at each of the 4 positions with 8 accumulators (0, ±1, ±2^31 boundaries, …): 2,097,152 cases, 0 failures (the first run covered positions 0-1 with acc 0 only; finding R2-5) | 15.7 |
| R13 INT-DOT-MADDUBS-Q4 | table: `x2_maddubs_word` | n0, n1 ∈ [0,15], x0, x1 ∈ [−127,127] | 16,646,400 | all | **0** | 0 | pair sum range exactly **[−3,810, 3,810]** | 0.03 |
| R14 INT-DOT-SIGNTRICK-Q8 | table+translit: `x2_maddubs_word`, PABSB/PSIGNB | w ∈ [−128,127]², x ∈ [−127,127]² (DOM-ACT-Q) | 4,261,478,400 | all | **0** | 0 | pair range exactly **[−32,512, 32,512]**; per product over x ∈ [−128,127]: **128 failures, all x = −128, w < 0** | 6.7 |
| R15 INT-BIAS-NIB | **algebraic** (no table operation) | (n − 8)·x = n·x − 8·x, n ∈ [0,15], x ∈ [−127,127] | 4,080 | all | 0 | 0 | cannot fail for these ranges; reported as the per-element algebra only (finding R2-8) | 0.0 |
| R16 INT-BIAS-XOR80 | **algebraic** | u8(q ⊕ 0x80) = q + 128; q·x = u8(q ⊕ 0x80)·x − 128·x | 65,280 | all | 0 | 0 | as R15 | 0.0 |
| R17 INT-NARROW-PACKS | table+translit: packs | all int32 q | 4,294,967,296 | 255 (\|q\| ≤ 127) | **0** | 4,278,189,826 | outside the condition the two agree only on 16,777,470 values | 4.2 |
| R19 RINT-MAGIC (RNE) | table | all v | 4,294,967,296 | 2,247,884,802 | **0** | 14,630,912 | 0 failures for \|v\| ≤ 2^22; smallest failing \|v\| is 0x4A800002 = 2^22 + 1 | 115.4 |
| R19 under RD on both sides | table | all v | 4,294,967,296 | 2,247,884,802 | **0** | 18,825,216 | agrees with Z3 (RULES.md) | 119.7 |
| R19 under RU on both sides | table | all v | 4,294,967,296 | 2,247,884,802 | **0** | 14,630,912 | agrees with Z3 | 119.3 |
| R19 under RZ on both sides | table | all v | 4,294,967,296 | 2,247,884,802 | **1,123,942,273** | 136,396,927 | **refuted**, as RULES.md records; first counterexample v = 0x80000001 (−2^−149): LHS −1, RHS 0 | 119.6 |
| R20 F16-WIDEN | table | all 2^16 h | 65,536 | all | **0** | 0 | Hearth `q_f16` with `(float)m · 2^−24` through CVTSI2SS and MULSS | 0.0 |
| R21 ISNAN-UCOMI | table: `x2_comis` | all v | 4,294,967,296 | all | **0** | 0 | | 11.3 |

R13's and R14's pair-level enumerations confirm RULES.md §4.1-4.2's T2 bounds (3,810 and 32,512) exactly.

### 1.2 Other environments (finding R2-4)

The first run used MXCSR 0x1F80 for every row except R19's RC variants, so the Env column of RULES.md §3.1
was machine-checked for no row. rev1 (`results/rev1/exhaustive_env.json`, `exhaustive_r19env.json`) runs the
environment-dependent rows under the seven other values the review used: 0x1FC0 (DAZ), 0x9F80 (FTZ),
0x9FC0 (DAZ+FTZ), 0x3F80 (RD), 0x5F80 (RU), 0x7F80 (RZ), 0xFFC0 (RZ+DAZ+FTZ).

Failures inside the side condition per (row, MXCSR) [M] rev1, 1 thread, desktop clock 22:03:40 to 22:20:48 (1,028 s), each over all 2^32 inputs (R20: 2^16):

| Row | 0x1FC0 DAZ | 0x9F80 FTZ | 0x9FC0 DAZ+FTZ | 0x3F80 RD | 0x5F80 RU | 0x7F80 RZ | 0xFFC0 RZ+DAZ+FTZ |
|---|---|---|---|---|---|---|---|
| R04 | **16,777,214** | 0 | **16,777,214** | 0 | 0 | 0 | **16,777,214** |
| R05 | **16,777,214** | 0 | **16,777,214** | 0 | 0 | 0 | **16,777,214** |
| R06 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R07 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R09 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R21 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

- **R04, R05: 0 failures whenever DAZ = 0 (any RC, FTZ); exactly 16,777,214 in-condition failures whenever DAZ = 1** (every denormal v: under DAZ MINPS/MAXPS return the flushed zero, the C select the original bits). The Env column's "DAZ = 0" is therefore load-bearing, as RULES.md §3.1 states; this is now in the record. (The review measured the same counts with its own probe [M review].)
- R06-R11, R20, R21: 0 failures under all 8 values, matching their Env column "any". R10 and R11 run here through VCMPPS into k (`x2_predict`) and `x2_masked`, not the first run's transliteration.
- **R19 (RNE) under DAZ (0x1FC0), FTZ (0x9F80) and DAZ+FTZ (0x9FC0): 0 failures inside the condition** (failures outside 14,630,912 each, as under 0x1F80; 114 s each) [M] rev1 22:20:48 to 22:26:29. With RD and RU (§1.1) and the RZ refutation, R19's Env column ("RNE only") is now checked for DAZ and FTZ too: RNE with any DAZ/FTZ.
- Every entry names its MXCSR in `exhaustive_env.json` / `exhaustive_r19env.json`; first counterexamples are recorded there.

### 1.3 Differential entries of x2prove (finding R2-5)

| Entry | What | Cases | Failures |
|---|---|---|---|
| DIFF-MADDUBS | C transliteration of the Z3 `word()` formula vs the table's `x2_maddubs_word`, all (u0, u1, s0, s1) | 4,294,967,296 | **0** (7.8 s) |
| DIFF-DPBUSD | C transliteration of the Z3 VPDPBUSD lane formula vs `x2_dpbusd_lane`: every (u, x) at each byte position × 8 accumulators, plus 2^27 pseudo-random (acc, 4 × (u, x)) | 136,314,880 | **0** (0.4 s) |
| HASH-PABS-PSIGN | sha256 over the C PABSB (256) and PSIGNB (2^16) transliterations | 65,792 | equals the `int_ops.py` hash `afab1070…63fb15` (§2) |
| HASH-PACKS | sha256 over the C packs transliteration for q ∈ [−2^17, 2^17) and the 64 int32 extremes at each end | 262,272 | equals the `int_ops.py` hash `2ad3f0f5…2af22f` (§2) |

## 2. Encoding differentials (rev1) [M]

| Check | Against | Comparisons | Mismatches |
|---|---|---|---|
| `smt_table.py`: compare (all 32 predicates), COMIS (quiet and signalling), VCVTPH2PS, masked-move lane, on 68 values incl. NaN payloads, ±0, ±∞, denormals, boundaries (4,624 pairs), every one of the 2^16 binary16 inputs, under default, DAZ, FTZ, DAZ+FTZ, RD, RZ+DAZ | `fp_ops.cmp_pred`, `fp_ops.comis`, `fp_ops.cvt_f16_to_f32`, `int_ops.masked` | 1,342,912 (887,808 + 55,488 + 393,216 + 6,400) | **0** (8.2 s) |
| `int_differential.py`: the Z3 lane formulas of `int_lanes.py` evaluated on PABSB (all 256), PSIGNB (all 2^16), the PMADDUBSW word (every single-product pair in both positions, saturation corners, 20,000 random), the VPDPBUSD lane (every (u, x) at byte position 0 × 8 accumulators, 20,000 random over all positions), packs (every q in [−2^16, 2^16), the int32 extremes, 20,000 random) | `int_ops.pabsb`, `psignb`, `pmaddubsw`, `pdpbusd`, `packssdw`/`packsswb` | 912,472 | **0** (90.6 s) |
| `int_differential.py`: hashes of x2prove's C transliterations (§1.3) | the same hashes from `int_ops.py` | 2 hashes | **0** (equal) |
| `trees.py` differential: the tree transliterations (the code that builds the T lemmas) on 2,000 random inputs per tree | `hearth_kernels.red8`, `red_quads`, `red_quad1` (the table's VPHADDD entry and `int_ops` moves) | 6,000 | **0** |
| `trees.py` unit basis: the table compositions on every unit vector (64 + 64 + 16) | the row-indicator maps (lane i = total of row i; red_quads lane 4k+j = quad j's 128-bit lane k) | 144 | **0** |

The unit-basis check is a second, solver-free route to the tree lemmas: every operation in the three trees
is a lane move or a wrapping 32-bit add, so each output lane is a Z/2^32-linear form in the input lanes, and
its values on the unit vectors determine it [D]. (The review made the same check, [M review].)

**Refactor regression.** The integer lane formulas moved into `int_lanes.py` so that queries and
differential share one definition. The first run's integer queries re-exported through it without solving
(`results/rev1/regress/`) are **identical to the first run's files modulo Z3's let-variable numbering**
(`smt2_equiv.py`: 8 of 8 in `smt2/`, 10 of 10 in `smt2int/`; 4 byte-identical). Their sha256 differ for the
others because Z3 numbers shared subterms (`?x2739`) by internal AST ids that depend on every term built
before in the same process; **a query hash identifies the exported file, not the query's meaning**.

## 3. Z3 routes [M]

### 3.1 First run (as recorded; with the review's corrections)

`results/z3.json` (1,200 s per query; stopped on purpose while on the monolithic R14) and `results/z3_b.json`
(R14-R18 monolithic, 600 s). Each entry records the query's SHA-256; the queries are in `results/smt2/`
(**31 files**; the builder's summary said 32) and `results/smt2int/` (**11 files**).

| Query | Result | s | Status after review |
|---|---|---|---|
| R01 SEL-MAX, all bits | **PROVED** | 0.001 | stands; the select condition is SMT-LIB `fp.gt` (rev1 adds the table-relation form) |
| R02 MAX-FOLD-8x8, concrete 64-input pattern (default strategy) | **UNKNOWN (timeout)** | 1,200.1 | stands |
| R02, same claim, bit-blast + SAT tactic (`z3_fold.py`) | **UNKNOWN (timeout)** | 1,500.1 | stands |
| R03 MAX-FOLD-16x4, concrete pattern | **UNKNOWN (timeout)** | 1,200.1 | stands |
| R02/R03 lemmas commute, NaN, order | **PROVED** ×3 | ≤ 0.009 | stand |
| R02/R03 L1-L6 | **PROVED** ×6 | ≤ 0.007 | stand; no query hash in `fold.json`: re-run with export in rev1 (§5) |
| R04, R05 (non-NaN v) | **PROVED** ×2 | 0.003 | stand (select condition `fp.gt`/`fp.lt`; rev1 adds the table-relation form) |
| R06, R07, DAZ = 0 and 1 | PROVED ×4 | ≤ 0.005 | **superseded**: SMT-LIB `fp.isNaN`/`fp.lt`/`fp.eq`/`fp.gt` in place of the table's VCMPPS, i.e. a check of the IEEE definition (finding R2-2) |
| R08, R09 generic | PROVED ×2 | 0.000 | **definitional** lemmas about the transliterated AND / BLENDVPS (no table entry); not table evidence |
| R08/inst, R09/inst | PROVED ×2 | ≤ 0.003 | **superseded** (as R06) |
| R10, R11 generic | PROVED ×2 | 0.000 | **withdrawn**: each query was `(not (= t t))`, a syntactic tautology (finding R2-1) |
| R10/inst, R11/inst | PROVED ×2 | 0.000 | **superseded**: `fp.isNaN` against the BV NaN test, no masking semantics |
| R12 INT-DOT-VNNI monolithic (one row, flat lane total, no int32 wrap) | **PROVED** | 30.1 | stands for one row; the red_quads/red_quad1 lane maps are the rev1 T lemmas (finding R2-3) |
| R13 monolithic | **UNKNOWN (timeout)** | 1,200.1 | stands |
| R14 monolithic (600 s cap) | **UNKNOWN (timeout)** | 600.1 | stands |
| R14 monolithic without DOM-ACT-Q | **COUNTEREXAMPLE**, as expected | 68.4 | stands |
| R15, R16 monolithic, with no wrap | **PROVED**, **PROVED** | 94.8, 107.2 | stand (one row, flat sum; the primary of R15/R16, §6) |
| R17 INT-NARROW-PACKS | **PROVED** | 0.001 | stands; its packs formula is now tied to `int_ops` (§2) |
| R18 INT-SUM-ACT monolithic (AVX2 and AVX-512 trees, no wrap) | **PROVED** | 48.1 | stands (its trees are modelled) |
| R19 RINT-MAGIC (RNE, \|v\| ≤ 127) | **PROVED** | 0.22 | stands |
| R20 F16-WIDEN | PROVED | 0.04 | **superseded**: the table side was `fp.to_fp` of binary16, not the table's entry; it also used `fp.to_ieee_bv`, so cvc5 could not replay it |
| R21 ISNAN-UCOMI | PROVED | 0.003 | **superseded**: ZF/PF hand-modelled from `fp.isNaN`/`fp.eq` |

Decomposed integer routes (`z3_int.py`, `results/int.json`, `int_export.json`):

| Query | Result | s | Status after review |
|---|---|---|---|
| R13/P, R13/W, R13/M | **PROVED** ×3 | ≤ 0.02 | stand; M covers one row's partials, the red8 lane map is T/red8 (rev1) |
| R14/P (PABSB/PSIGNB word, DOM-ACT-Q) | **PROVED** | 407.4 | stands; had no export and no hash (finding R2-6): re-run with export in rev1 |
| R14/P without DOM-ACT-Q | **COUNTEREXAMPLE** (x1 = −128, w1 = −5), as expected | 4.9 | stands |
| R14/M | **PROVED** | 0.000 | stands (as R13/M) |
| R12/P | PROVED | 0.06 | **reworded**: its equality part was a reassociation of itself; rev1 states it as a bound lemma |
| R12/M, R15/P, R15/M, R16/P, R16/M, R18/M | **PROVED** ×6 | ≤ 0.013 | stand |

### 3.2 rev1 (`results/rev1/z3.json`, `int.json`; 600 s per query, R14/P 1,200 s)

| Query | Encoding of the table side | Z3 5.3.1 | s |
|---|---|---|---|
| R01 (re-run), R01/table (the select's `>` as the table's relation) | `smt_encoding.maxmin`; `smt_table.relation` | **PROVED**, **PROVED** | 0.001, 0.024 |
| R04, R04/table; R05, R05/table (non-NaN v) | as R01 | **PROVED** ×4 | ≤ 0.003 |
| R06/DAZ=0, R06/DAZ=1 (`cmp_pred(3, v, v)` = isnan v) | `smt_table.cmp_pred` | **PROVED** ×2 | 0.000 |
| R07/DAZ=0, R07/DAZ=1 | `smt_table.cmp_pred` (7) | **PROVED** ×2 | 0.000 |
| R08/inst/DAZ=0, /DAZ=1 (act_q8: AND with the VEX compare mask) | `cmp_pred` (7); AND transliterated | **PROVED** ×2 | 0.001 |
| R09/inst/DAZ=0, /DAZ=1 (canon8: BLENDVPS with the compare mask) | `cmp_pred` (3); BLENDVPS transliterated | **PROVED** ×2 | 0.000 |
| R10/inst/DAZ=0, /DAZ=1 (canon16: merge-masked move, k from the compare) | `cmp_pred` (3); `smt_table.masked_lane` (= `int_ops.masked`) | **PROVED** ×2 | 0.000 |
| R11/inst/DAZ=0, /DAZ=1 (act_q8 AVX-512: zero-masked move) | `cmp_pred` (7); `masked_lane`, zero | **PROVED** ×2 | 0.000 |
| R08, R09 generic (definitional: AND / BLENDVPS with an all-ones-or-zero mask) | transliterations only; **not table evidence** | **PROVED** ×2 | 0.000 |
| R20 (Hearth `q_f16` vs the table's VCVTPH2PS; the FPA product's bits as a variable r with `fp(r) = product`) | `smt_table.cvt_h2f` (pure BV) | **PROVED** | 0.033 |
| R21/DAZ=0, R21/DAZ=1 (`v != v` through the table's UCOMISS) | `smt_table.comis` | **PROVED** ×2 | 0.000 |
| R14/P (exported and hashed this time) | `int_lanes.word`, `pabs`, `psign` | **PROVED** | 472.5 |
| R12/P, now a bound lemma (\|zext(u)·sext(x)\| ≤ 32,385 under DOM-ACT-Q) | `int_lanes` | **PROVED** | 0.046 |
| T/red8 (8 rows × 8 free int32 partials: lane i = Σ row i) | `trees.red8` | **PROVED** | 0.000 |
| T/red_quads (4 quads × 16 lanes: lane 4k+j = Σ quad j's 128-bit lane k) | `trees.red_quads` | **PROVED** | 0.000 |
| T/red_quad1 (16 lanes: lane k = Σ 128-bit lane k) | `trees.red_quad1` | **PROVED** | 0.000 |

Every query solved fast because, on the bit-vector encodings, Z3's rewriter normalises both sides to the same
term or to a small case split [inference]; the differentials of §2 show the encodings are the table's, and the
negative controls of `trees.py` (each T lemma with lanes 0 and 1 of the map swapped) are refuted, so the T
lemmas are not vacuous (all three refuted, `results/rev1/trees.json`, re-run 22:08 desktop clock after the job). Query files: `results/rev1/smt2/` (23 files),
`results/rev1/smt2int/` (5), `results/rev1/smt2fold/` (7); each file's sha256 is in the JSON entry.

## 4. Second solver: cvc5 [M]

### 4.1 First run

`results/cvc5.json`, `cvc5_int.json`, `cvc5_b.json`, replaying exactly Z3's exported files (no set-logic; cvc5
uses ALL). Timeouts: R02/R03 1,200 s, others 600 s.

| Query | cvc5 1.4.2 | s |
|---|---|---|
| R01 | **PROVED** | 0.009 |
| R02 lemmas (commute, NaN, order) | **PROVED** ×3 | ≤ 0.035 |
| R02, R03 concrete patterns | **UNKNOWN (timeout)** ×2 | 1,200.0 each |
| R04, R05 | **PROVED** ×2 | 0.006 |
| R06, R07 (DAZ = 0 and 1), R08-R11 generic and instance | PROVED ×12 | ≤ 0.005 |
| R12 monolithic | **UNKNOWN (timeout)** | 600.0 |
| R17 | **PROVED** | 0.004 |
| R18 monolithic | **UNKNOWN (timeout)** | 600.1 |
| R19, R20 | not run: `fp.to_ieee_bv` | |
| R21 | PROVED | 0.004 |
| R12/P, R12/M, R13/P, R13/W, R13/M, R14/M, R15/P, R15/M, R16/P, R16/M, R18/M | **PROVED** ×11 (R15/M 100.5 s, R16/M 31.7 s, the rest ≤ 0.5 s) | |

The R06-R11 and R21 replays agree with Z3 on the superseded and withdrawn queries of §3.1 and carry the same
limitation.

### 4.2 rev1 (`results/rev1/cvc5.json`, `cvc5_int.json`, `cvc5_fold.json`; 600 s per query)

All **23** rev1 queries of `results/rev1/smt2/` (R01, R01/table, R04, R04/table, R05, R05/table, R06 and R07 under DAZ = 0 and 1, the R08-R11 instances under DAZ = 0 and 1, the definitional R08 and R09, R20, R21 under DAZ = 0 and 1): **PROVED ×23** (each ≤ 0.339 s). R20 is replayed for the first time (no `fp.to_ieee_bv`).

All **5** of `results/rev1/smt2int/`: R12/P **PROVED** (0.075 s), **R14/P PROVED (194.2 s)**, T/red8, T/red_quads, T/red_quad1 **PROVED** (≤ 0.002 s). R14/P's query sha256 `41f3a1c1de7611e932ddf3014f980f019d2a3da0c1cbfbbbc997b9954c597618` equals the one the review exported independently, and the review's cvc5 replay of that file took 218.7 s [M review].

All **7** of `results/rev1/smt2fold/` (L1-L6, L1t): **PROVED ×7** (§5).

## 5. R02 / R03 (MAX-FOLD)

The written proof is now [R02-R03-proof.md](R02-R03-proof.md) (finding R2-7): the per-step invariant
(meaning and lane chains both compute the unsigned NaN-skipping maximum of the elements seen, starting from
+0), induction, and the tree step, citing each lemma by its query hash. rev1 exports every lemma and replays
it in cvc5; it also adds L1t, the meaning step with the C `>` as the table's relation (`smt_table.relation`)
instead of SMT-LIB `fp.gt`.

rev1 lemma runs (`results/rev1/fold.json`, `cvc5_fold.json`; 600 s per query):

| Lemma | Z3 5.3.1 | s | cvc5 1.4.2 | s | query sha256 (`results/rev1/smt2fold/`) |
|---|---|---|---|---|---|
| L1 meaning step | **PROVED** | 0.005 | **PROVED** | 0.058 | `435afbc3a40282c775f1025ec7ec6f1f0898cf3791e9773ba5d0e554a5db711b` |
| L2 chain step | **PROVED** | 0.004 | **PROVED** | 0.042 | `65622efc4747e38d1140cf9ce2cb30c67177dc336da4331e36afad489308c72f` |
| L3 tree step | **PROVED** | 0.004 | **PROVED** | 0.039 | `9bdab0dee81abdbca4ff6114f30e424761a92c9c97aa69557c346a57cfc57d84` |
| L4 closure | **PROVED** | 0.003 | **PROVED** | 0.002 | `9466ddd1c93a103a791b8b481cd9f5c116dd07ad5243c62963f2a0c9ec8104f3` |
| L5 start value +0 is sign-0, non-NaN | **PROVED** | 0.000 | **PROVED** | 0.001 | `10bd4d579690a94cdea3bbff72c3ab1f0c838d08e8841acd9b07fc03309dda94` |
| L6 abs is sign-0 | **PROVED** | 0.000 | **PROVED** | 0.001 | `80b31edbaf60fe6cd1e84bb45d37b9cae943e66fe20546cfab9a8fbca7ae4263` |
| L1t meaning step, table relation | **PROVED** | 0.009 | **PROVED** | 0.004 | `639a1c896a6cda9288ad0f74994d8320ea92791a9aba4cfa11ae690093e0d02d` |

**Status unchanged: R02 and R03 are not proved under RULES.md §1** (no primary route succeeded). The review
also measured that the composition step as a pure-BV query with L1-L3 substituted is UNKNOWN in Z3 and cvc5 at
600 s, and the upper-bound / membership characterisation UNKNOWN at 300 s [M review], so the hardness is the
64-deep maximum chain itself and an R03 bit-blast run is unlikely to change the status [inference]. Whether a
written proof whose every lemma two solvers checked may serve as the primary is the Owner's question
(provisional, pending the Owner, with RQ-3).

## 6. Row status (RULES.md §1 "proved" = primary and an agreeing second route), corrected after review

| Row | Table routes that agree (rev1 where re-run) | Not counted as table evidence | Status |
|---|---|---|---|
| R01 | Z3 and cvc5, with `fp.gt` and with the table's relation | | **PROVED** |
| R02, R03 | none on the concrete pattern (Z3 default 1,200 s, Z3 bit-blast 1,500 s for R02, cvc5 1,200 s: all timeouts); the written proof's lemmas L1-L6 and L1t: Z3 and cvc5 PROVED, hashed (§5) | | **NOT PROVED** under §1 (Owner question: may the written proof serve as the primary?) |
| R04, R05 | Z3 (`fp.gt`/`fp.lt` and table relation), cvc5, exhaustive 2^32 under 8 MXCSR values (in-condition failures only with DAZ = 1, which the Env column excludes) | | **PROVED** for DAZ = 0 |
| R06, R07 | Z3 and cvc5 on `smt_table.cmp_pred` (DAZ = 0, 1); exhaustive 2^32 through VCMPPS under 8 MXCSR values | first-run Z3/cvc5 queries (IEEE definition) | **PROVED** |
| R08, R09 | Z3 and cvc5 on the Hearth instance with the table's compare (DAZ = 0, 1); exhaustive 2^32 through VCMPPS under 8 MXCSR values | the generic lemmas (definitional; AND / BLENDVPS have no entry); first-run instance queries | **PROVED** for the Hearth instance |
| R10, R11 | Z3 and cvc5 on the instance with the table's compare and `int_ops.masked`; exhaustive 2^32 through VCMPPS-into-k and `x2_masked` under 8 MXCSR values | first-run generic queries (`t == t`, withdrawn) and instance queries | **PROVED** for the Hearth instance |
| R12 | Z3 QF_BV monolithic one-row (30.1 s), decomposed M, P (bound), T/red_quads, T/red_quad1 (Z3, cvc5); exhaustive through `x2_dpbusd_lane` (2^33 pairs, all positions × 8 accumulators); unit-basis tree maps | | **PROVED** (QF_BV primary with an agreeing exhaustive route, provisional RQ-3 reading) |
| R13 | exhaustive pair level through `x2_maddubs_word`; decomposed P, W, M, T/red8 (Z3, cvc5) | | **PROVED** |
| R14 | exhaustive pair level (PABSB/PSIGNB transliterated, tied to `int_ops` by hash); decomposed P (Z3 472 s, cvc5 194 s), M, T/red8 (Z3, cvc5) | | **PROVED** |
| R15, R16 | Z3 monolithic with no wrap (primary); decomposed P, M (Z3, cvc5) | per-element enumeration: algebraic identity, no table operation | **PROVED** |
| R17 | exhaustive 2^32 (packs transliterated, tied to `int_ops` by hash); Z3, cvc5 (packs formula tied to `int_ops`) | | **PROVED** |
| R18 | Z3 monolithic (no wrap); decomposed M (Z3, cvc5) | | **PROVED** (cvc5 timed out on the monolithic query) |
| R19 | Z3 (RNE); exhaustive 2^32 under RNE and under DAZ, FTZ, DAZ+FTZ; RD and RU agree; RZ refuted | | **PROVED** for its Env (RNE) |
| R20 | Z3 and cvc5 on `smt_table.cvt_h2f`; exhaustive 2^16 under 8 MXCSR values | first-run Z3 query (`fp.to_fp`) | **PROVED** |
| R21 | Z3 and cvc5 on `smt_table.comis` (DAZ = 0, 1); exhaustive 2^32 under 8 MXCSR values | first-run Z3/cvc5 queries | **PROVED** |

**Count [D]: 19 of the 21 rows of `rules.v1` draft 2 are proved by §1's definition on the corrected routes;
R02 and R03 are not** (unchanged from the first run, but now on routes that evaluate the table). The loop rule
LOOP-LOCKSTEP (written proof plus a different-family Prover, RULES.md §5) was not part of this run. Under the
strict counting default the rule count is unchanged at 22 (21 rows + 1 loop rule); P2a's "every counted row and
loop rule proved" is not met today because of R02, R03 and the loop rule. The act_q8 SIMD variants need R02/R03
(RULES.md §7 question 1 and prereg Owner question 7).

## 7. Result files, hashes and reproducibility

First run (`results/`), SHA-256: `exhaustive.json` 99880c5c…a2c0, `z3.json` 4b946510…5d635, `z3_b.json`
8610baff…dbcc3, `cvc5.json` 09c51a7d…949e5, `cvc5_int.json` 2fd1ab24…80885, `cvc5_b.json` e42244ab…63bb2,
`int.json` (including R14/P; produced before the export option existed, so it has no query hashes) 63782da9…b5bed,
`int_export.json` (the exported subset, with query hashes; R14/P missing) 47120ce3…f723ec, `fold.json` 01dde79d…139a.
The concatenation of every query in `smt2/` (31 files) and `smt2int/` (11 files), sorted as `cat` lists them,
hashes to `22f5afdd045fd21b47bb22d183f5f302d5c3034fb5dd4e557b5c9c049a0b89e9`. Job logs: `results/logs/`.

rev1 (`results/rev1/`; JSON files normalised to LF line endings, as the repository stores text), SHA-256:

| File | SHA-256 |
|---|---|
| `cvc5.json` | `bb70b8f6c5238d37983a5907ddf8aef1595d254d248afcd82de19035743dee4b` |
| `cvc5_fold.json` | `7a7b5c25007a4568d58e3257d74a689c56395400ef68bcfab7cd81ab81e5b4e6` |
| `cvc5_int.json` | `6d5c1197cdc28938db20709ae1541c535160d2875049c2c97fec3887168fd9a8` |
| `differential_smt_table.json` | `97a1fae185c93b580850ef81e5be73abe217d3c17f1e66a1b12f66e0efde7e9b` |
| `exhaustive.json` | `3d04ebbe30e10f0536550943c7d0a64eb94396c2c9b2ad758491df282af7d71b` |
| `exhaustive_env.json` | `a0a8b8a05867107af541c43b88002c7c9b1806401b5106aa963c8d1b90ad604a` |
| `exhaustive_hash.json` | `0087505b00c7eb2b6746800615744ae6d0358f78bb1db548c7fe9d4b83c6c03f` |
| `exhaustive_r19env.json` | `d19133b42d870c75045f71b3d10a3dee5434d02f6267f6bbd1c62b64849a1441` |
| `fold.json` | `8abc14531fce9e86cf6447826dfe4235e9cac62c98d27399bb2b0de3f6b40e9c` |
| `int.json` | `d2c9608b8ea208071c84dc72d173b8204aa6cb4a914c0e1edbcf3542b10df6a0` |
| `int_differential.json` | `195c597bbc69a36c121d38be7f8f08112c132db23979a0518c1226d5bb74a7ba` |
| `trees.json` | `ce756375e2b627350d765eeade824265bbb5b973d4a7c788c3cd7c83d39ef71c` |
| `z3.json` | `126fa6922bf256b382f4c7c9849f600bc162a8b83c9b48a64769cee199f3af3a` |

Query files: `smt2/` 23, `smt2int/` 5, `smt2fold/` 7; every file's sha256 equals the `query_sha256` of its JSON
entry (35 of 35 checked); their concatenation (`smt2/`, `smt2int/`, `smt2fold/`, each sorted) hashes to
`0163e8fed8451031db1e0984ca1936243344aa09c97ba83b3f0c820a7c4c725c`. `regress/` holds the re-exported first-run
integer queries and `equiv_smt2.json`, `equiv_smt2int.json` (§2). Logs: `results/rev1/logs/` (build, the two
jobs, the tree controls). Binaries: `x2prove.exe` `0070718e…5e218b` (§ Routes).

**Timings are single runs** [M], load-dependent; other jobs of other tracks shared the desktop. The review
replayed part of the first run on the same machine (2026-10-16 20:36-21:00 EDT, at most 2 threads)
[M review]: every verdict and every exhaustive count reproduced exactly; exhaustive times within 2 % (e.g. R19
59.2 s vs 60.1 s); Z3 times R12 20.1 s vs 30.1 s, R15 84.7 vs 94.8, R18 48.2 vs 48.1, R14 without DOM-ACT-Q 51.5
vs 68.4, R14/P 482 vs 407; cvc5 R14/P 218.7 s. rev1's own times are a further sample (§1, §3.2, §4.2).

## 8. Process notes

First run: the first solver job was stopped on purpose while Z3 worked on the monolithic R14 (after R13's
1,200 s timeout), and the remaining queries were split into a Z3 job (600 s cap) and a cvc5 job. Because of a
stop-order slip, an orphaned cvc5 process ran for about one minute beside the two new jobs (three solver
processes of this track for that minute) before it was stopped; its partial output was discarded and the
replay was redone by the cvc5 job. The R02 bit-blast attempt ran beside the main Z3 job; R03's attempt was
stopped. rev1: two jobs of one thread each (`run_prove_rev1.cmd`, `run_solvers_rev1.cmd`, then
`../harness/run_mutants_dev.cmd` in the second job), 21:52:42 to 22:26:29 (exhaustive job) and 21:52:42 to 22:05:41 (solver and mutant job) desktop clock, logs in `results/rev1/logs/`. `build_prove.cmd` now only builds (with `build_info.h`); in the first run it also ran x2prove (`results/logs/prove.log`). `run_solvers*.cmd`, `run_int.cmd`, `run_fold.cmd` are the first run's scripts, kept as they ran; rev1 used `build_prove.cmd`, `run_prove_rev1.cmd` and `run_solvers_rev1.cmd`, at most 2 threads of this track at any time.

## 9. Review log

| Date | Reviewer | Lens | Family | Findings | Outcome |
|---|---|---|---|---|---|
| 2026-10-16 | reviewer 2 | proof routes: do the queries and loops evaluate the table, the environments, the trees; reproducibility | Claude, **same family, independent context** | 10: 4 major, 6 minor | all 10 accepted; routes corrected and re-run (rev1); row count unchanged at 19 of 21 on the corrected routes |
| 2026-10-16 | reviewer 1 | harness soundness | Claude, same family, independent context | 11 | see ../harness/README.md §11 |

| # | Severity | Finding | Verified how | Action |
|---|---|---|---|---|
| R2-1 | major | R10/R11 generic queries are `t == t`; their instance queries have no masking or compare semantics; the C generic loops of R08-R11 compare transliterations with their own definitions | read `results/smt2/R10.smt2` (`(not (= ?x2739 ?x2739))`), `R11.smt2`, `R10_inst.smt2`; `x2prove.c` (first run) | **fixed**: generic R10/R11 queries deleted; R08/R09 generic queries kept and labelled definitional; C generic loops removed; R10/R11 instances through `x2_predict` (VCMPPS into k) and `x2_masked`, R08/R09 instances through `x2_predict` (VEX VCMPPS); Z3 instances on `smt_table` (§3.2) |
| R2-2 | major | the "Z3 primary" of R06, R07, R08-R11 instances, R20, R21 does not encode the table entries | read the queries and `smt_encoding.py` (no compare/COMIS/H2F term, differential covers arithmetic only) | **fixed**: `smt_table.py` (pure-BV compare relation, 32 predicates, COMIS, VCVTPH2PS, masked lane), differential 1,342,912 comparisons, 0 mismatches; queries rebuilt under DAZ = 0 and 1; R20 without `fp.to_ieee_bv`; also R01/R04/R05 and R02's L1 with the table relation |
| R2-3 | major | no route models red8 / red_quads / red_quad1; M lemmas are flat sums; the z3_int docstring claimed otherwise | read `z3_int.py`, `z3_rules.py` and Hearth b5d3f14 `quant_avx2.c:71-76`, `quant_avx512.c:64-76` | **fixed**: `trees.py` (transliterations used both for the T lemmas and concretely), T lemmas in Z3 and cvc5, differential against `hearth_kernels` and unit-basis check; docstring and monolithic query descriptions corrected ("one row") |
| R2-4 | major | exhaustive routes under 0x1F80 only; Env column not machine-checked | `x2prove.c` main (first run) | **fixed**: `--mxcsr` list, one entry per (row, MXCSR); R04-R11, R20, R21 under 8 values; R19 (RNE) under DAZ/FTZ (§1.2) |
| R2-5 | minor | integer lane formulas have no differential; R12/P's equality is a reassociation; R12's exhaustive route covers positions 0-1 with acc 0 | read | **fixed**: `int_lanes.py` (one definition), `int_differential.py` (912,472 checks), DIFF-MADDUBS / DIFF-DPBUSD exhaustive in C, HASH-* ties the C transliterations to `int_ops`; R12/P reworded as a bound lemma; R12 exhaustive extended to positions (2,3) and 8 accumulators |
| R2-6 | minor | R14/P has no exported file, no hash, no second solver | `int.json` has no `query_sha256`; `int_export.json` omits R14/P | **fixed**: exported, hashed, replayed in cvc5 (§3.2, §4.2) |
| R2-7 | minor | L1-L6 not exported or hashed, no second solver; the composition only a docstring | `fold.json` keys | **fixed**: exported with hashes, cvc5 replay, [R02-R03-proof.md](R02-R03-proof.md); R02/R03 stay not proved |
| R2-8 | minor | R15/R16 "exhaustive" routes are C identities with no table operation | `x2prove.c` R15/R16 | **fixed**: relabelled `algebraic`; the Z3 monolithic query (with the no-wrap conjunct) named as primary; overflow obligations point to RULES.md §4.3 |
| R2-9 | minor | `exhaustive.json` has no source/interpreter/compiler hashes or per-row MXCSR; `--only` matched substrings | `exhaustive.json` keys; `strstr` in main | **fixed**: `build_info.h` with `X2_PROVE_SRC_SHA256`, interpreter hash, compiler, per-entry `mxcsr`; exact `--only` tokens, unknown names refused |
| R2-10 | minor | solver times are single runs; "32" queries in the builder's summary, 31 in `smt2/` | file listing | **fixed in the record text**: §7 labels times as single runs and adds the review's replay times; counts stated (31 + 11 first run) |
