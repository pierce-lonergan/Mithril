# X2: T1 exact-rewrite rules, T2 range obligations, loop rules

Status: DRAFT, M0 week 0, revised 2026-10-16 after two same-family reviews (review log in
[TABLE-SCHEMA.md §15](TABLE-SCHEMA.md#15-review-log) and the
[pre-registration §12](../../docs/m0/prereg/X2-checker.md#12-review-log)). ROADMAP §3.3: T1 matches
FP DAGs modulo an audited exact-rewrite list with the NaN-order side condition; T2 discharges ranges
such as the Q4 `maddubs` bound 3,810 and the Q8 sign-trick bound 32,512; each rewrite rule is checked
by Z3 FPA or exhaustive binary32; the lockstep loop rule, extended to the shapes X0 finds, gets a
written proof reviewed by a Prover from a different family; the gate is ≤ 30 proved rules [target].
This file proposes the list (`rules.v1` draft 2), its counting rule, side conditions, environments
and proof routes, re-derives the T2 bounds and the domain predicates, and states the loop rule. Tags
as in [TABLE-SCHEMA.md](TABLE-SCHEMA.md). Z3 timings are single runs on the laptop (Ryzen 9 7940HS)
with z3-solver 5.3.1 from PyPI via `python -B -m semantics.smt_encoding`: [M] X2 author 2026-10-16
for the v0 probes, [M] X2 reviser 2026-10-16 for the probes marked "rev". **The proofs this list marked
"not yet run" were run on 2026-10-16 by the x2build track on the desktop (exhaustive, Z3, cvc5), reviewed
the same day (same family, independent context) and partly re-run with corrected routes; their status is
§8 and [proofs/README.md](proofs/README.md).**

---

## 1. What counts as a rule (counting rule, draft 2)

- **A rule** is one row of the frozen file `rules.v1`: one left-hand pattern and one right-hand
  pattern over **named operators** (no operator variables; parameters are constants bound by side
  conditions), a side-condition set, an **Env** column (the environment profiles in which the row is
  sound), and a proof artifact. **Every row counts toward the ≤ 30 [target], used or not.** T1 refuses
  to apply a row outside its Env column.
- **Not rules** (each with its reason):
  - *Evaluation of table entries.* Data movement, bitwise operations, masked and zero-masked forms
    with T2-known masks, and broadcasts are evaluated to QF_BV terms through their entries. This is
    what an instruction *is*, not an identity between two different terms; its premise is the entry,
    graded with the table (v0 counted it once as R23 "for conservatism"; draft 2 removes it, as
    reviewer 2 proposed, finding R2-7).
  - *Family correspondence.* A KIR operation and the table family it denotes (KIR `add` ↔ FP.ADD;
    KIR `f16_to_f32` ↔ FP.CVT.f16_f32; C `!=` on floats ↔ FP.COMI with ZF = 0 or PF = 1, per
    `SCALAR_C_MAP_V0`) match node for node; that is the "same operation" of 03 §6.3. The
    correspondence list is frozen and hashed with `rules.v1` as `kir_family_map.v1`, each row with a
    differential check against the reference semantics; P2 reports its size separately (P2c) and it
    does not count.
  - *T2 obligations.* Ranges, saturation freedom, mask contents, footprints and the domain facts of
    §4 are instance facts with certificates.
  - *Definitional identities.* Where the KIR operation is *defined* by the same bit operation the
    code performs (bf16 → f32 is a 16-bit shift in `canon.v1`), both sides evaluate to the same term.
- **Integer identities (strict default; fixed by DELEGATED P33 on 2026-10-23, Pierce reviews at sitting 2).** An equality
  between two *different* integer terms that T1 or T2 invokes (a reassociated dot product, a bias
  correction, the sign trick, a narrowing) is counted as a row, one row per named identity instance.
  The alternative reading, that per-instance QF_BV equalities decided by T2 with certificates are T2
  obligations (03 §6.3: "Integer subterms become T2 obligations"), would count them as 0. P2 reports
  both counts; the gate uses the per-instance count, the larger (fixed by DELEGATED P33, 2026-10-23).
- **Loop rules (strict default; fixed by DELEGATED P32 on 2026-10-23, Pierce reviews at sitting 2).** ROADMAP §3.3 names "the
  lockstep loop rule, extended to the unroll, rotation and peel shapes X0 finds", with one written
  proof. Draft 2 counts LOOP-LOCKSTEP with all its extensions as **1 rule** when the extensions are
  lemmas inside that one written proof; any extension that needs its own proof counts as a further
  rule. v0 excluded loop rules from the count and said "ROADMAP §3.3 separates them"; ROADMAP
  separates only the proof method, so that sentence is withdrawn (finding R2-6).
- **Proved** means: the primary proof succeeded **and** an independent second route agreed. Primary:
  Z3 FPA with the bit-vector NaN layer, or exhaustive enumeration over all binary32 inputs of the
  rule's free variables. For integer rows the primary is exhaustive enumeration over the per-product
  domain (at most 2^32 inputs) or a Z3 QF_BV proof; a QF_BV primary counts only with an agreeing
  exhaustive or second-solver route (RQ-3, fixed by DELEGATED P34, 2026-10-23). Second route: exhaustive enumeration where the free inputs fit in 32 bits;
  otherwise a second solver, or the case-exhaustive check of the NaN and signed-zero layer plus the
  IEEE 754 definition for non-NaN values (03 §6.3). Solvers are untrusted (03 §6.5); unknown or
  timeout is "not proved".
- **Intrinsic level.** X2 checks transliterated intrinsics (ROADMAP §3.3). A compiler's idioms
  (commuting operands, padding with −0.0, `x·2 → x+x`, if-conversion) do not occur at that level, so
  rules needed only for compiled objects are **not** in `rules.v1` for X2. They are kept in §3.2 as
  object-level candidates for the M2 audit, which will have its own count.

## 2. The NaN-order side condition, made precise

Some rules preserve every non-NaN result bit and preserve NaN-ness, but may change a NaN's payload,
sign or quiet bit (`NAN.ARITH2` picks the first source's NaN; an SNaN comes back quiet). Call two
values **NaN-class equal** if their bits are equal or both are NaN. The condition for applying such a
rule at node n:

> Every path from n to an observable sink passes through a **payload-erasing** node before it
> reaches a **bit observer**.

Each table entry declares, per operand, a hashed field `nan_role ∈ {transparent, erasing,
observer}` (`semantics/table.py`). **Transparency and erasure are whitelists; anything else is an
observer**, so an instruction the census adds and nobody classifies is treated soundly by default
(finding R1-8). `census_absorb.py` reports any entry without a `nan_role`.

| Role | Entries (draft 2) | One-line justification (hashed in `NAN_ROLE_JUSTIFICATION`) |
|---|---|---|
| transparent | FP.ADD, FP.SUB, FP.MUL, FP.DIV (both sources) | `NAN.ARITH2` output is NaN iff an input is NaN or the operation is invalid on non-NaN values, so NaN-class-equal inputs give NaN-class-equal outputs |
| transparent (by evaluation) | pure lane moves (permutes, shuffles, extracts, inserts, broadcasts, constant-mask blends, masked moves with T2-known masks) once they have entries | they route lanes without reading their bits |
| erasing | FP.CMP and FP.COMI (both sources); FP.CVT.f32_i32 (rc and trunc) | the result depends only on NaN-ness (every NaN converts to `0x80000000`) |
| erasing (idiom) | `canon::nan` (R06 + R09/R10) and NaN → 0 selection (R07 + R08/R11) | the select replaces every NaN lane by a constant |
| observer | MAX/MIN (conservative, 03 §6.3); CVT i32→f32 and CVT f16→f32 (their input is not an f32 value); every integer, bitwise and sign-driven entry (BLENDV selector, MOVMSK, mask-from-sign); stores to observable memory; anything unlisted | — |

T1 checks the condition as a reachability property on the lifted DAG. Proof of soundness (sketch,
for the written-proof review): by induction over the DAG in topological order, every node between
n and the first erasing node on each path has NaN-class-equal values before and after the rewrite
(the rule's own lemma for n; transparency for the rest); erasing nodes then produce identical bits;
observers are only reached through erasing nodes, so observed bits are identical.

**A refinement this analysis exposes [D, proposed, not adopted].** MAXPS and MINPS are themselves
transparent for NaN-class equality in both operand positions: a NaN first source makes them return
the second source unchanged whatever the NaN's payload; a NaN second source is returned, so the
outputs are NaN-class equal. So the conservative clause costs completeness only. Whether to relax it
is an architecture question (§7); this draft keeps 03's conservative clause. **What does change
results is commuting the operands of MAX/MIN themselves**, which is never on the list
unconditionally. Z3 finds counterexamples with a NaN operand (one run gave a = `0x00000000`,
b = `0xFFFFFFFF` [M] rev; the model differs between runs); restricted to non-NaN operands Z3 finds
max(+0, −0) ≠ max(−0, +0) (a = `0x00000000`, b = `0x80000000` [M] rev, probe added 2026-10-16); the
same pair is hand-checked in self-test B1. (v0 attributed the ±0 counterexample to the unrestricted
Z3 probe, which in fact returns a NaN case; finding R1-9.)

**Application to Hearth b5d3f14 [inference until T1 runs].** At intrinsic level the gating variants
keep the scalar code's operand order for every add and mul (read from the source: `add(acc, mul(w,
x))` against `L + w·x`; `add(acc, mul(cvt(is), mul(dw, dx)))` against `acc + (float)isum·(dw·dx)`;
`mul(v, id)` against `x·id`; the tree16 halving order equals `sum16`), so draft 2 needs no
commutation row. The NaN-order condition still governs the object-level commutation rows (§3.2):
every commutation a compiler may introduce sits upstream of an erasing node (the dot16 tree adds feed
`canon4`; the Q8/Q4 epilogue feeds `canon8`/`canon16`; in act_q8 the product `v·id` is zeroed by the
ORD mask before it reaches MINPS). The only stored value without canonicalisation is act_q8's
`d = amax / 127`.

## 3. The rule list (`rules.v1` draft 2)

### 3.1 Rows

"Needed by" G = a gating variant (8, prereg §4.1); B = only the hosts that join P3 under Owner
question 8's provisional option (b) (scalar variants, F16/BF16 variants, `hx_*` helpers). All
"needed by" entries are [inference from reading b5d3f14] until T1 runs. Env "default" = RC = RNE,
DAZ = FTZ = 0 (MXCSR 0x1F80). "v0" gives the v0 row the draft-2 row came from.

| ID | v0 | Rule (LHS ↔ RHS) | Side conditions | Env | Needed by | Primary proof, status | Second route |
|---|---|---|---|---|---|---|---|
| R01 SEL-MAX | new | `select(gt(a, b), a, b) ↔ MAX(a, b)` (MAXPS/MAXSS, src1 = a) | none: equal for all bits, NaN and ±0 included (SDM MAXPS pseudocode returns SRC2 on NaN or both zeros, as the C select does) | DAZ = 0 (any RC, FTZ): under DAZ MAXPS returns the flushed zero (F-DAZ-SEL), the select the original bits | act_q8 AVX2, AVX-512 (meaning `if (a > amax) amax = a`); base step of R02/R03 | Z3 all bits: **PROVED 0.00 s** [M] rev | case-exhaustive NaN/±0 layer (self-test B7 spot vectors) + IEEE comparison; second solver |
| R02 MAX-FOLD-8x8 | R16 | sequential 64-step chain of R01 over `\|x_i\|` from +0.0 ↔ 8 lane chains of 8 `MAXPS(\|v\|, m)` then `hmax8` | every element enters as **src1**, the running max as src2; running max starts at +0.0; every element's sign bit is 0 by a BV fact (`andnot(signmask, v)`); tree steps combine running maxima only | DAZ = 0 | act_q8 AVX2 | Z3 on the concrete 64-input pattern: run 2026-10-16, see §8. Lemmas: MAXPS commutes on sign-0 non-NaN **PROVED 0.01 s**; `MAXPS(NaN, m) = m` **PROVED 0.00 s**; sign-0 non-NaN order = unsigned BV order **PROVED 0.00 s** [M] v0 and rev | written proof from the lemmas (NaN elements become +0.0, then unsigned integer max is associative and commutative); second solver |
| R03 MAX-FOLD-16x4 | R16 | as R02 with 16 lane chains of 4 and `hmax16` | as R02 (`_mm512_abs_ps` = sign-bit clear) | DAZ = 0 | act_q8 AVX-512 | as R02 | as R02 |
| R04 MIN-SEL-127 | R17 | `select(gt(v, c), c, v) ↔ MIN(v, c)`, c = 127.0 | **value fact: v is not NaN**, established by T2/dataflow because v is the output of an R08/R11 NaN → 0 select (v0 called this "dominated by an erasing node", which mixed a value fact with payload erasure; finding R1-13); c non-NaN and nonzero | DAZ = 0 | act_q8 clamp, AVX2 and AVX-512 | Z3 (c = 127, non-NaN v): **PROVED 0.00 s** [M] v0; with NaN v: COUNTEREXAMPLE (e.g. `0xFF813EFB`) [M] rev, so the side condition is load-bearing | exhaustive 2^32 over v |
| R05 MAX-SEL-M127 | R18 | `select(lt(v, c), c, v) ↔ MAX(v, c)`, c = −127.0 | as R04 | DAZ = 0 | act_q8 clamp | Z3 (c = −127, non-NaN v): **PROVED 0.00 s** [M] rev | exhaustive 2^32 over v |
| R06 ISNAN-UNORD | R15 (part) | `CMP(v, v, UNORD_Q) ↔ isnan(v)` (lane all-ones / k bit set iff NaN) | none | any | `canon8`, `canon16`, `canon4` in F32, Q4, Q8, both ISAs (6 variants) | table entry evaluation + Z3: run 2026-10-16, see §8 | exhaustive 2^32 over v |
| R07 NOTNAN-ORD | R15 (part) | `CMP(v, v, ORD_Q) ↔ not(isnan(v))` | none | any | act_q8 NaN zeroing, both ISAs | run 2026-10-16, see §8 | exhaustive 2^32 over v |
| R08 ANDMASK-SELECT | R13 | `and(x, cmpmask(c)) ↔ select(c, x, +0.0)` (VEX compare lanes are all-ones or zero) | the mask is the output of a compare entry | any | AVX2 act_q8 NaN zeroing | BV lemma: run 2026-10-16, see §8 | exhaustive per lane (x × {true, false}) |
| R09 BLENDV-SELECT | R14 (part) | `blendv(a, b, cmpmask(c)) ↔ select(c, b, a)` | mask from a compare entry | any | AVX2 `canon8`, `canon4` (F32, Q4, Q8) | BV lemma: run 2026-10-16, see §8 | exhaustive per lane |
| R10 MASKMOV-SELECT | R14 (part) | `mask_mov(a, k, b) ↔ select(k, b, a)` | k from a compare-into-mask entry | any | AVX-512 `canon16`, `canon4` | BV lemma: run 2026-10-16, see §8 | exhaustive per lane |
| R11 MASKZMOV-SELECT | R14 (part) | `maskz_mov(k, p) ↔ select(k, p, +0.0)` | k from a compare-into-mask entry | any | AVX-512 act_q8 NaN zeroing | BV lemma: run 2026-10-16, see §8 | exhaustive per lane |
| R12 INT-DOT-VNNI | R21 (instance) | 4 × VPDPBUSD per quad, `red_quads` / `red_quad1` ↔ Σ_i u_i·x_i in index order (int32) | T2: no int32 wrap (`64·255·127 = 2,072,640`) | any | AVX-512 Q4, Q8 | Z3 QF_BV per instance: run 2026-10-16, see §8 | per-product exhaustive (u8 × s8, 2^16) + additivity; second solver |
| R13 INT-DOT-MADDUBS-Q4 | R21 (instance) | `maddubs(n, x)` pairs, VPADDW of low and high, `madd(·, 1)`, `red8` ↔ Σ n_i·x_i | T2: no saturation (3,810), no VPADDW wrap (7,620), red8 sum ≤ 121,920 | any | AVX2 Q4 | run 2026-10-16, see §8 | per-product exhaustive (16 × 255, `bounds.py`) |
| R14 INT-DOT-SIGNTRICK-Q8 | R22 (part) | `maddubs(PABSB(w), PSIGNB(x, w))`, `madd`, `red8` ↔ Σ w_i·x_i | **DOM-ACT-Q** (x ≠ −128); no saturation (32,512) | any | AVX2 Q8 | per-product identity exhaustive over 256 × 255 pairs: holds; fails for x = −128, w < 0 [D] (`bounds.py`, self-test H2, G6) | Z3 QF_BV per instance |
| R15 INT-BIAS-NIB | R22 (part) | Σ (n_i − 8)·x_i ↔ Σ n_i·x_i − 8·a.sum | **DOM-ACT-SUM**; no wrap | any | AVX2 Q4, AVX-512 Q4 | Z3 QF_BV: run 2026-10-16, see §8 | per-element algebra; self-test G5 on 30 blocks; G7 shows DOM-ACT-SUM is load-bearing |
| R16 INT-BIAS-XOR80 | R22 (part) | Σ q_i·x_i ↔ Σ (q_i xor 0x80)·x_i − 128·a.sum (u8(q xor 0x80) = q + 128) | **DOM-ACT-SUM**; no wrap | any | AVX-512 Q8 | Z3 QF_BV: run 2026-10-16, see §8 | exhaustive over q (2^8) for the byte identity; G5, G7 |
| R17 INT-NARROW-PACKS | new | `packsswb(packssdw(q))` lane ↔ `(int8_t)q` | T2: \|q\| ≤ 127 | any | AVX2 act_q8 store | run 2026-10-16, see §8 | exhaustive over q ∈ [−2^31, 2^31) restricted by the fact (255 values) |
| R18 INT-SUM-ACT | R21 (instance) | lane-parallel `padd` over k, then the horizontal int32 tree ↔ Σ q_i sequential | T2: \|Σ q\| ≤ 8,128, no wrap | any | act_q8 AVX2, AVX-512 (`sum`) | run 2026-10-16, see §8 | Z3 QF_BV; per-instance |
| R19 RINT-MAGIC | R19 | `cvtt((v + M) − M) ↔ round_ne_to_int(v)`, M = 1.5·2^23 | T2: \|v\| ≤ 127 (provable up to \|v\| ≤ 2^22) | **RNE only** as used. With the same RC on both sides it also holds for RD and RU (Z3 **PROVED**, 0.26-0.31 s over two runs [M] rev) but **fails for RZ** on negative non-integers (COUNTEREXAMPLE, e.g. `0xC12D829E`, −10.84...: LHS −11, RHS −10 [M] rev), which is the cross-ISA defect Hearth's council review of 2026-10-04 reported | B: scalar act_q8 (`q_rint` then `(int)`) | Z3 for \|v\| ≤ 127: **PROVED 0.28 s** [M] v0 | exhaustive 2^32 |
| R20 F16-WIDEN | R10 | Hearth's `q_f16(h)` (integer bit code, plus `(float)m · 2^−24` for subnormals) ↔ KIR `f16_to_f32(h)` | none | any (both sides exact on normal f32 values) | B: scalar `mm_f16`, scalar Q4/Q8 block scales | run 2026-10-16, see §8 | **exhaustive 2^16** |
| R21 ISNAN-UCOMI | R15 (part) | `UCOMISS(v, v)` with ZF = 0 or PF = 1 (C `v != v`) ↔ isnan(v) | none | any | B: scalar `q_canon`, scalar act_q8 `v != v` | run 2026-10-16, see §8 | exhaustive 2^32 |

**Count [D: rows above + loop rules].** Strict default: **21 rows + 1 loop rule = 22 ≤ 30**
[target]: 11 FP/bridging rows (R01-R11) + 7 integer rows (R12-R18) needed by the gating variants, +3
rows (R19-R21) needed only under option (b), + LOOP-LOCKSTEP counted once. Sensitivity:
- if all 7 loop rules count separately (RQ-1): 21 + 7 = **28**;
- if integer identities are T2 instances (RQ-2): 14 + 1 = **15**;
- under option (a) of P3's denominator (excluded by DELEGATED P31 as a loosening; shown for comparison only):
  R19-R21 drop, 18 + 1 = **19**.
Every reading is ≤ 30 before T1 runs. The remaining risk is that T1 development on the real variants
needs rows this reading did not foresee; rows may be added until `rules.v1` is frozen, which happens
before the mutant pool is revealed (§6). At intrinsic level the census cannot add rewrite rows (it
changes table scope and loop shapes, not the source), so v0's "slack for idioms the census finds"
does not apply to X2.

**Changes from v0 (finding R2-7).** Deleted: R04 UNIT-MUL, R05 NEG-XOR, R08 POW2-SCALE,
R09 CVT-I2F-EXACT, R24 CVTT-INTEGRAL (reserves; unused rows count, so they bought nothing), R12
MASK-ALLONES (operator variable; masked entries with T2-known masks are evaluated, §1), R23 BV-EVAL
(evaluation, §1). Split: R14 into R09-R11, R15 into R06, R07, R21, R16 into R02/R03, R21/R22 into the
named instances R12-R18. Moved to the object-level candidates (§3.2): R01 COMM-ADD, R02 COMM-MUL,
R03 SZ-ADD, R06 SUB-ADDNEG, R07 POW2-DOUBLE, R20 SELECT-SPECULATE. Added: R01 SEL-MAX (finding
R1-13), R17 INT-NARROW-PACKS. A SEL-MIN row (`select(lt(a, b), a, b) ↔ MIN(a, b)`, Z3 **PROVED**
0.00 s [M] rev) was considered and **not added**: no Hearth site needs it, and an unused row would
still count.

### 3.2 Object-level candidates (not in `rules.v1` for X2; carried to the M2 object audit)

| Candidate | Rule | Side conditions | Env | Status [M] |
|---|---|---|---|---|
| COMM-ADD | `a + b ↔ b + a` | NaN-order (§2) | any (the definition is symmetric) | Z3: NaN-ness preserved and equal non-NaN bits **PROVED 0.01-0.03 s** v0, rev; all bits: COUNTEREXAMPLE, e.g. (`0xFFC60B6D`, `0x7FB9F492`) v0, (`0xFFBFFF89`, `0x7FC0004F`) rev |
| COMM-MUL | `a · b ↔ b · a` | NaN-order | any | **PROVED 0.04 s** v0 |
| SZ-ADD | `x + (−0.0) ↔ x` | NaN-order (an SNaN x is quieted: Z3 counterexamples e.g. `0x7F87245D` v0, `0xFFA38146` and `0x7F96A485` rev) | **default only**: fails for x = +0 under RD (self-test A5: +0 + −0 = −0) and for a denormal x under DAZ | non-NaN x: **PROVED 0.00-0.01 s** |
| SUB-ADDNEG | `x − y ↔ x + xor(y, signbit)` | NaN-order | any | not yet run |
| POW2-DOUBLE | `x · 2.0 ↔ x + x` | none | proved for default only | Z3 all bits **PROVED 0.05-0.06 s** |
| SELECT-SPECULATE | if-conversion of `d != 0 ? 1/d : 0` | f's flags unobserved; no memory effect | any | value-semantics lemma |

With these six, a combined intrinsic + object list would hold 21 + 6 = 27 rows plus the loop rule
(28) under the strict reading [D], close to the 30 budget. That is a forward risk for M2, reported here because it is
pre-data information; it does not affect X2's count.

**Never on the list** (03 §6.3, unchanged): reassociation or distribution of FP operations, FMA
contraction or fusion, unconditional MAX/MIN operand commutation (counterexamples above),
`x + 0.0 → x` (Z3 counterexample x = −0 [M]), `x − x → 0`, `x · 0 → 0`, accumulator splitting.

**Self-checks of the encoding behind these proofs.** The SMT terms used here agree with the Python
reference semantics on **32,192 concrete comparisons with 0 mismatches** [M] rev, 2026-10-16:
`add`, `sub`, `mul`, `div`, `max`, `min` under default, DAZ only, FTZ only and DAZ + FTZ, and
`cvt f32→i32` under RNE and RZ (truncating) with and without DAZ, including 2^31 (`0x4F000000`),
−2^31 (`0xCF000000`), −2^31 − 256 (`0xCF000001`), 2^31 − 128 and NaN. v0 checked only add, mul,
div, max and min under two environments (10,000 comparisons), although R19's proof uses `sub` and
`cvt_f2i` (finding R1-10). Both implementations encode the same SDM reading; silicon checks the
reading.

### 3.3 Proof cost [D]

- **Why the Z3 times are so small.** The commutation probes take 0.01-0.04 s, which suggests Z3
  normalises `fp.add(a, b)` and `fp.add(b, a)` to one term before bit-blasting [inference]. That is a
  sound proof only if Z3's rewriter is sound, and Z3 produces no checkable FPA proof. Hence the second
  route in every row. Counterexample bit patterns differ between runs (compare the v0 and rev values
  above); they are quoted as examples, not as reproducible outputs.
- **Exhaustive binary32** is available for every row with at most 32 free input bits: R04, R05
  (per constant), R06, R07, R19, R21 (one f32 input), R20 (2^16), R08-R11 (per lane), and the
  per-product parts of R13-R16. Cost: both sides of a rule evaluated 2^32 times through the
  generated C reference interpreter. Anchor: [G04] ran all 2^32 binary32 inputs for 9 function
  evaluations in about 22 s on 32 threads of the 9950X [M, G04], about 1.8 × 10^9 evaluations per
  second [D]. Assuming 20-50 ns per evaluation of the interpreter [G], one rule costs
  2^33 × (20-50) ns / 32 threads ≈ **5-13 s** [D from G] on the desktop. Seven such rules: under
  2 minutes [D from G].
- **Two-source rows cannot be exhaustive.** 2^64 input pairs × 2 evaluations at 1.8 × 10^9 per
  second would take about 650 years [D: 2^65 / 1.8×10^9 s ≈ 2.0 × 10^10 s]. R01 and the lemmas of
  R02/R03 therefore rest on Z3 plus a second solver plus the case-exhaustive NaN/signed-zero check:
  the NaN layer has finitely many cases per operand class (QNaN, SNaN, ±0, ±∞, denormal, normal),
  which are enumerated with representative payloads, and the non-NaN part is the IEEE 754 definition
  of comparison.
- **Certificates.** For a re-checkable proof, the FP circuit can be bit-blasted to CNF and solved by
  a SAT solver emitting LRAT, which the T2 certificate checker (03 §14, ≤ 800 lines) can re-check.
  A miter of two FP comparators is in the order of 10^4-10^5 clauses [G]; solve time is unknown
  until measured.

## 4. Domains and T2 range obligations, re-derived from Hearth's code

Method: each saturation and overflow obligation is decomposed into per-product facts over the
declared domains, which are **enumerated exhaustively through the table's own lane functions**
(`semantics/bounds.py`, run by the self-test, section H); pair and block bounds then follow by
additivity, because the summed terms range over independent operands. All numbers [D] with the
formula given, computed by the X2 agents on 2026-10-16.

### 4.0 Domain predicates (numbered, checkable; finding R1-2)

| ID | Predicate | Holds at b5d3f14 because | Used by |
|---|---|---|---|
| **DOM-ACT-Q** | ∀ i < 64: −127 ≤ a.q[i] ≤ 127 | every `act_quantize_q8` variant clamps to ±127 before converting (`quant.c` `act_q8_scalar`; `act_q8_avx2`, `act_q8_avx512`) | R14 (x ≠ −128), §4.2 |
| **DOM-ACT-SUM** | a.sum = Σ_{i<64} a.q[i] as int32, hence \|a.sum\| ≤ 8,128 [D: 64 · 127] | every `act_quantize_q8` variant writes `sum` as the sum of the stored quants | R15, R16: `quant_avx2.c:262, :308` (`is - a->sum*8`) and `quant_avx512.c:270, :333` (`a->sum * bias`); the scalar meaning (`quant.c` `mm_q8_scalar`, `mm_q4_scalar`) never reads `.sum` |
| **DOM-W** | any weight bytes (Q8 `q`, Q4 `qs`), any f16 scale bits | the kernels must be safe for any byte; `test_quant.c` `test_nonfinite` feeds random bytes | §4.1-4.3 bounds use w ∈ [−128, 127], n ∈ [0, 15] |
| **DOM-ENV** | MXCSR = 0x1F80 at entry (all exceptions masked, RNE, DAZ = FTZ = 0) | **not established at b5d3f14**: no MXCSR write or check in `engine/src` [M, reviewer 2 and reviser grep, 2026-10-16]; the guard is D0-5b, unsigned | every FP row's Env column; the table's `precond` |
| **DOM-SHAPE** | the length and non-overlap facts of 03 §3.4's example (`a.len = w.blocks_per_row`, `y ∩ (w ∪ a) = ∅`, `n` a multiple of 64 for the Q kernels) | Hearth's API contract | footprint check (03 §6.3) |

**Discharge.** DOM-ACT-Q and DOM-ACT-SUM are not assumed about the activation quantiser: they are
**postconditions of the act_q8 meaning**, proved by T2 over the meaning (clamp, then convert; the sum
of at most 64 values of magnitude ≤ 127 does not wrap), and every act_q8 variant that T1 accepts
inherits them through its bit-identity with the meaning. For the matmul variants they are domain
predicates of the `refines` claim (03 §3.4 prints exactly `a[*].q ∈ [-127,127] · a[*].sum = Σq` in
its example); at a C API seam where a caller passes activation blocks that did not come from an
accepted act_q8 variant they become seam checks (03 §2.4). DOM-ENV is a declared precondition until
D0-5b lands, after which it is the runtime-checked entry of 03 §3.4 (prereg §4 item 2(c)).
v0 defined the activation domain by provenance ("produced by `act_quantize_q8`"), which is not a
checkable predicate, and listed only "no wrap; x ≠ −128" under the integer ring row.

### 4.1 Q4 `maddubs` bound 3,810: CONFIRMED

`quant_avx2.c` `qtile8`, Q4: `maddubs(lo, x0)` and `maddubs(hi, x1)` with nibbles as the unsigned
operand.
- Per product `n · x`: range [−1,905, 1,905], exhaustive over 16 × 255 pairs through the table's
  VPMADDUBSW; pair sum within ±3,810 = 2·15·127. No saturation (|3,810| < 32,767).
- The code then adds the two pair sums with `_mm256_add_epi16` (VPADDW, wrapping): within
  ±7,620 = 2·3,810. No wrap. **This second obligation is as load-bearing as the first** (Hearth's
  comment states it as "low+high ≤ 7620").
- Margin: if `x = −128` were possible the pair bound would be 3,840; still safe.
- `red8` then holds Σ n·x **before** the bias subtraction `is − a->sum·8`: within ±121,920 =
  64·15·127 (self-test H3'). No int32 wrap.
- Block sum: `|Σ(n − 8)·x| ≤ 64·8·127 = 65,024 < 2^24`, so `(float)isum` is exact (self-test D1:
  `cvt(65,024) = 0x477E0000`, exact).

### 4.2 Q8 sign-trick bound 32,512: CONFIRMED, with a sharper precondition

`quant_avx2.c` `qtile8`, Q8: `maddubs(abs_epi8(w), sign_epi8(x, w))`.
- `u = PABSB(w) ∈ [0, 128]` (PABSB of −128 is `0x80`, read as 128 by the unsigned operand).
- `s = PSIGNB(x, w)`: for `x ∈ [−127, 127]`, `|s| ≤ 127`.
- Pair sum within ±32,512 = 2·128·127 < 32,767. No saturation.
- **Identity.** Exhaustively over all 256 × 255 (w, x) pairs, `u · s = w · x` holds. Over the full
  int8 range of x it fails in exactly 128 cases, `x = −128` with `w < 0`, because PSIGNB negates −128
  to −128. Saturation still cannot occur there (pair range [−32,768, 32,512]), so **the obligation
  that actually protects correctness is DOM-ACT-Q (`x ≠ −128`)**, not only the 32,512 bound.
  Self-test G6 is the witness: `w = −1, x = −128` gives −128 on the AVX2 path and +128 in the
  scalar meaning.
- Block sum: `|Σ w·x| ≤ 64·128·127 = 1,040,384` for any weight byte, `64·127·127 = 1,032,256` for
  quantiser output; both `< 2^24`, so the conversion is exact (self-test D1: `cvt(−1,032,256) =
  0xC97C0400`, exact).

### 4.3 The other obligations of the kernels in scope

| Obligation | Bound [D] | Where |
|---|---|---|
| AVX-512 VNNI Q8: `u = q xor 0x80 = q + 128 ∈ [0, 255]`; `Σ u·x ≤ 64·255·127 = 2,072,640`; bias term `128·Σx ≤ 128·8,128 = 1,040,384` (DOM-ACT-SUM); no int32 wrap | `< 2^31` | `quant_avx512.c` `dot_quad`, `q16_step`, `qtile4` |
| AVX-512 VNNI Q4: `u = n ∈ [0, 15]`, bias 8 | `64·15·127 = 121,920` | same |
| AVX2 Q4 `red8` before `is − a->sum·8` | `64·15·127 = 121,920` | `quant_avx2.c` `qtile8` (`:262`, `:308`) |
| `a->sum * bias` as C `int32_t` multiply (signed overflow is UB, so T2 proves its absence) | `≤ 128 · 8,128 = 1,040,384` (DOM-ACT-SUM) | same; AVX2 uses `* 8` |
| act_q8 quants after the clamp | `\|q\| ≤ 127`, `\|Σq\| ≤ 8,128` | all ISAs (postconditions DOM-ACT-Q, DOM-ACT-SUM) |
| VPACKSSDW / VPACKSSWB / VPMOVDB of act quants do not saturate or truncate | `\|q\| ≤ 127` | AVX2 packs (R17); AVX-512 `cvtepi32_epi8` |
| Masks: AVX-512 tail `tm = (1 << (n − n16)) − 1` with `0 ≤ n − n16 < 16`; AVX2 `smask` lanes `< nr`; `qtile4` `sm = (1 << nr) − 1` | exact values | footprint (03 §6.3) |
| Footprint: stores only to `Y` rows `[r0, r1)` and act blocks; loads only inside `W`, `act`, `X`; masked-off lanes of `maskz_loadu` (`x + n16`) and `maskstore` may lie past the array end and rely on fault suppression (fuzz class F-MEMFAULT) | per variant | T1 footprint check |

All are QF_BV queries over a handful of bit-vectors once the domain facts are asserted; each should
take well under a second [G].

## 5. Loop rules

Counting: 1 (§1, RQ-1; fixed by DELEGATED P32, 2026-10-23). The architecture states them in 03 §6.4; this is the
statement X2 will prove in writing and X0's shapes will extend.

**LOOP-LOCKSTEP.** Let the meaning loop be `for i in 0..N { σ_M := S_M(σ_M, i) }` and the machine loop
have head state `σ_L`, guard `g_L`, body `S_L`. Let `R(σ_L, σ_M, i)` be a correspondence relation with
a register part (each machine register lane equals a named meaning value under the lane map) and a
memory part (output locations the meaning has written, `y[0..i)` in its order, hold equal values;
no other output location has been written; inputs are unchanged). If

- **Base:** `R(σ_L0, σ_M0, 0)`;
- **Guard:** `R(σ_L, σ_M, i) ⇒ (g_L(σ_L) ⇔ i < N)`;
- **Step:** for every symbolic state, `R(σ_L, σ_M, i) ∧ i < N ∧ Inv ⇒ R(S_L(σ_L), S_M(σ_M, i), i + 1)`,
  checked as a one-iteration DAG match plus the footprint check, where `Inv` is the hinted invariant;
- **Exit:** `R(σ_L, σ_M, N) ∧ ¬g_L(σ_L) ⇒` the outputs are equal;

then the machine loop refines the meaning loop on the declared domain. `R`, `Inv` and the lane map are
untrusted hints: a wrong hint only causes rejection.

**Extensions (lemmas of the same written proof; each reduces to LOOP-LOCKSTEP, 03 §6.4):**
UNROLL(u, remainder) composes u meaning iterations in order per machine iteration; ROTATE and
software pipelining add pending terms to `R` with no cross-iteration FP combination the meaning
lacks; PEEL concatenates segments in iteration order with masked lanes excluded by blend or
zero-mask; SPILL promotes constant-offset, non-escaping stack slots to SSA values; HREDUCE evaluates
shuffles into a lane tree that must equal the meaning's named tree; ROWTILE matches each output's
DAG separately under the meaning's disjoint writes.

**X0's narrowing request (`proved_loop_shapes`).** X0's record (§8, Narrowing row) reads the field
`proved_loop_shapes` of X2's `verdict.json`, in the tag vocabulary of X0 §4 item 7. X2 adopts it
(prereg §7). A tag is listed only if the extension that covers it is proved and reviewed at the
verdict:

| X0 tag | Covered by | Note |
|---|---|---|
| lockstep | LOCKSTEP | |
| unrolled-u | UNROLL | |
| rotated | ROTATE | |
| peeled | PEEL | |
| software-pipelined | ROTATE (pending terms) | |
| spilled | SPILL | |
| interchanged | ROWTILE | independent outputs only |
| auto-vectorised | none | needs reassociation, which is never on the list; never listed |
| other | per loop id only, after a written argument | |

**How Hearth's kernels map onto them [inference from the source, before the census].**

| Kernel | Machine loop ↔ meaning | Rules |
|---|---|---|
| `mm_float` AVX-512 | step 16; zmm lane j ↔ `L[j]`; masked tail ↔ the final partial chunk; `tree16` ↔ the 8-4-2-1 tree; 4-row tile ↔ 4 independent outputs | LOCKSTEP, PEEL (mask), HREDUCE, ROWTILE; R06 + R10 for `canon4` |
| `mm_float` AVX2 | step 16; `lo`/`hi` ymm ↔ `L[0..8)`/`L[8..16)`; tail on a stored copy (`finish16`) ↔ the partial chunk | LOCKSTEP, PEEL, SPILL (the stored copy), HREDUCE, ROWTILE; R06 + R09 |
| Q8/Q4 AVX2 `qtile8`, AVX-512 `qtile16`/`qtile4` | block loop g ↔ meaning g; inner integer sums ↔ the exact block sum; lanes = rows; token tiling TCH = 8 ↔ independent outputs | LOCKSTEP, ROWTILE; R12-R16 for the integer part; R06 + R09/R10 for the canonicalisation |
| `act_q8` all ISAs | per-block loop ↔ meaning blocks; the inner k loops are fixed-trip and fully unrolled at intrinsic level | LOCKSTEP; R01-R05, R07, R08/R11, R17, R18 inside the block |

The composition-level lane maps these rows assume (`red8`, `red_quads`, `red_quad1`, `tree16` in both
ISAs) were checked by composing table semantics against Hearth's stated maps, bit for bit, in the
self-test (section G) [D]; the act_q8 variants and the Q4/Q8 block sums agree across scalar, AVX2 and
AVX-512 on the hand-built blocks there. Since the 2026-10-16 revision these compositions resolve every
FP and integer instruction through `table.find` and record the content hashes they ran on
(`hearth_kernels.entries_used()`); data-movement operations without entries yet are listed by
`unregistered_used()`.

**Review.** ROADMAP §3.3 asks for a Prover from a different model family. D0-10 has not named the
families, so the review is provisional, pending D0-10: a same-family, independent-context review,
labelled as such, with the gap visible in the review log (docs/m0/README.md).

## 6. When the census lands

1. The census sets the table's scope (entries, operand variants, budget rows); at intrinsic level it
   adds no rewrite rows. Every loop shape it finds outside the extensions above is reported for X0's
   narrowing (ROADMAP §3.1).
2. A new row is added only before `rules.v1` is frozen for the verdict run, which is before the
   mutant pool is revealed; after that, an addition is an amendment marked post-data and the verdict
   is reported with and without it.
3. A loop shape outside the extensions is reported, not silently proved.

## 7. Architecture and Owner questions raised (not decided here)

1. 03 §6.3 bans MAX/MIN operand commutation outright, but the act_q8 SIMD variants need R02/R03
   (conditional, sign-bit-0 non-NaN operands). Proposed: allow it only under their side conditions.
2. 03 §6.3 lists MAXPS/MINPS among NaN observers. §2 above shows they are transparent for NaN-class
   equality. Keeping them as observers is sound and, for Hearth, costs nothing [inference]; relaxing
   it would need its own proof row.
*RQ-1 to RQ-3 were answered on 2026-10-23 under the batch-4 delegation with their strict defaults (DELEGATED P32,
P33, P34); the X2 record item 4.4 states them. Question 1 (R02/R03 against 03 §6.3) and the question whether the
R02/R03 written proof may serve as the primary stay Pierce's (OWNER-QUEUE D11; the X2 record §13 O5).*

3. **RQ-1 (Owner): do loop rules count toward ≤ 30?** Provisional default (strict): LOCKSTEP with
   its extensions as lemmas of one written proof counts as 1; each separately proved extension counts
   1 more. Options: 0 (v0's reading, looser), 1 (default), 7 (strictest).
4. **RQ-2 (Owner): do integer identities count as rows?** Provisional default (strict): each named
   identity instance counts (R12-R18). The alternative treats them as T2 per-instance obligations
   (03 §6.3), count 0.
5. **RQ-3 (Owner): does a Z3 QF_BV proof satisfy ROADMAP's "Z3 FPA or exhaustive binary32" for
   integer rows?** Provisional: only together with an agreeing exhaustive or second-solver route.

## 8. Proof runs of 2026-10-16 (x2build track), revised after review

The rows marked "not yet run" in §3.1, and the second routes of rows whose primary was already proved,
were run on 2026-10-16 on the desktop (AMD Ryzen 9 9950X, Windows 11 26200.9711). A same-family,
independent-context review of that run (proofs/README.md §9; 10 findings, all accepted) showed that several
routes did not evaluate the table where this section said they did: the R10/R11 "generic BV lemma" queries
were the tautology `t == t`; the C "generic" loops of R08-R11 compared transliterations with their own
definitions; the Z3 queries of R06, R07, the R08-R11 instances, R20 and R21 used SMT-LIB's `fp.isNaN`,
`fp.eq` and `fp.to_fp` in place of the table's VCMPPS, UCOMISS and VCVTPH2PS (a check of the IEEE
definition); no route modelled the reduction trees of R12-R14; the exhaustive routes ran under MXCSR 0x1F80
only; R15/R16's "exhaustive" routes contain no table operation. The routes were corrected and re-run the same
evening ("rev1"). Method, run time [M], result and artefact hash per route: [proofs/README.md](proofs/README.md);
artefacts in `proofs/results/` (first run) and `proofs/results/rev1/`.

Routes after the revision: exhaustive enumeration through the C reference interpreter of the table
(`proofs/x2prove.c`; lane functions, or whole instructions through `x2_predict` and the EVEX masking function
`x2_masked`; every entry states its route kind and MXCSR); Z3 5.3.1 on encodings that are either
`semantics/smt_encoding.py` (arithmetic, MAX/MIN, CVT) or the new pure-BV table encodings of
`proofs/smt_table.py` (compare relation and its 32 predicates, COMIS, VCVTPH2PS, masked lane), `proofs/int_lanes.py`
(integer lane formulas) and `proofs/trees.py` (reduction trees), each checked against the Python reference by a
recorded differential (1,342,912 + 912,472 + 6,000 comparisons and 144 unit vectors, 0 mismatches); cvc5 1.4.2
replaying every exported query. A route that checks an IEEE definition, a transliteration against itself or an
algebraic identity without table operations is labelled so and is not counted as a table route. "Proved" is
§1's definition. Nothing here freezes `rules.v1` or counts toward the gate before the verdict run; every review
is **same family, independent context** until D0-10 names another family.

| Row | Primary route, result [M] | Second route, result [M] | Status by §1 |
|---|---|---|---|
| R01 SEL-MAX | Z3 all bits: PROVED (0.001 s); rev1 also with the C `>` as the table's relation: PROVED (0.024 s) | cvc5 on both queries: PROVED | **PROVED** |
| R02 MAX-FOLD-8x8 | Z3 on the concrete 64-input pattern: **UNKNOWN (timeout 1,200 s)**; bit-blast + SAT tactic: **UNKNOWN (timeout 1,500 s)**; cvc5: UNKNOWN (1,200 s) | the written proof [proofs/R02-R03-proof.md](proofs/R02-R03-proof.md) from lemmas L1-L6 and L1t (the meaning step with the table's relation), **Z3 and cvc5 PROVED on every lemma, each exported with its hash** (rev1; the first run had Z3 only and no hashes) | **not proved**: the primary did not succeed. Whether a written proof whose every lemma two solvers checked may serve as the primary is a counting-rule question (Owner, with RQ-3) |
| R03 MAX-FOLD-16x4 | Z3 concrete pattern: **UNKNOWN (timeout 1,200 s)**; cvc5: UNKNOWN (1,200 s) | the same written proof (it does not depend on the lane count) | **not proved**, as R02 |
| R04 MIN-SEL-127 | Z3 (non-NaN v): PROVED, with `fp.gt` and with the table's relation | exhaustive 2^32 through the table: 0 failures on the non-NaN v; the 16,777,214 NaN v all fail (side condition load-bearing); **under the 7 other MXCSR values: 0 failures whenever DAZ = 0; with DAZ = 1 exactly 16,777,214 in-condition failures (every denormal v), so the Env column's DAZ = 0 is load-bearing**; cvc5: PROVED | **PROVED** for its Env (DAZ = 0) |
| R05 MAX-SEL-M127 | as R04 | as R04 | **PROVED** for its Env (DAZ = 0) |
| R06 ISNAN-UNORD | Z3 on the table's compare lane (`smt_table.cmp_pred`, predicate 3), DAZ = 0 and 1: PROVED | exhaustive 2^32 through VCMPPS ymm (`x2_predict`) under all 8 MXCSR values: 0 failures; cvc5: PROVED | **PROVED** (the first run's Z3 query checked the IEEE definition and is superseded) |
| R07 NOTNAN-ORD | as R06 (predicate 7) | as R06 | **PROVED** |
| R08 ANDMASK-SELECT | Z3 on the act_q8 instance with the table's compare lane, AND transliterated (VANDPS has no entry), DAZ = 0 and 1: PROVED | exhaustive 2^32 (VCMPPS ymm through `x2_predict`, AND) under 8 MXCSR values: 0 failures; cvc5: PROVED. The generic `and(x, cmpmask(c))` lemma is definitional (no table entry) and not counted | **PROVED** for the Hearth instance |
| R09 BLENDV-SELECT | as R08, canon8 instance, BLENDVPS transliterated | as R08 | **PROVED** for the Hearth instance |
| R10 MASKMOV-SELECT | Z3 on the canon16 instance: k from the table's compare lane (UNORD_Q), merge-masked move as `int_ops.masked`, DAZ = 0 and 1: PROVED | exhaustive 2^32: VCMPPS zmm into k through `x2_predict`, the move through `x2_masked`, under 8 MXCSR values: 0 failures; cvc5: PROVED. The first run's generic query was `t == t` and is **withdrawn**; the generic form is the definition of EVEX merge masking (§1, "not rules") | **PROVED** for the Hearth instance |
| R11 MASKZMOV-SELECT | as R10, act_q8 instance, zero masking (ORD_Q) | as R10 | **PROVED** for the Hearth instance |
| R12 INT-DOT-VNNI | Z3 QF_BV, monolithic one-row query with no-wrap: PROVED, 30.1 s; decomposed: R12/M PROVED, R12/P (now a bound lemma) PROVED; **tree lemmas T/red_quads and T/red_quad1** (rev1): PROVED | exhaustive through `x2_dpbusd_lane`: pairs at byte positions (0,1) and (2,3), 2^33, and every product at all 4 positions with 8 accumulators: 0 failures; cvc5: R12/M, R12/P, T lemmas PROVED, monolithic UNKNOWN (600 s); the tree maps also by unit-basis evaluation of the table compositions | **PROVED** (QF_BV primary with an agreeing exhaustive route, the provisional RQ-3 reading) |
| R13 INT-DOT-MADDUBS-Q4 | exhaustive pair level through the table's VPMADDUBSW word (16,646,400): 0 failures; pair sums exactly [−3,810, 3,810] | Z3 QF_BV decomposed (P, W, M) and **T/red8** (rev1): PROVED; cvc5: P, W, M PROVED, T/red8 PROVED; monolithic: UNKNOWN in Z3 (1,200 s) | **PROVED** |
| R14 INT-DOT-SIGNTRICK-Q8 | exhaustive pair level (4,261,478,400 under DOM-ACT-Q; PABSB/PSIGNB transliterated and tied to `int_ops` by hash): 0 failures; pair range exactly [−32,512, 32,512]; per product over x ∈ [−128, 127]: exactly 128 failures, all x = −128, w < 0 | Z3 QF_BV decomposed: P PROVED (407 s first run, 472 s rev1), M PROVED, T/red8 PROVED; without DOM-ACT-Q a counterexample (x = −128, w = −5); cvc5: M PROVED, **P (exported and hashed in rev1) PROVED (194.2 s)**, T/red8 PROVED; monolithic: UNKNOWN (600 s) | **PROVED** |
| R15 INT-BIAS-NIB | Z3 QF_BV monolithic, including the no-wrap conjunct: PROVED, 94.8 s | Z3 decomposed (P, M): PROVED; cvc5 on P, M: PROVED. The per-element enumeration (4,080) is the **algebraic identity with no table operation** and is not a table route; the overflow obligation of `a->sum*8` is a §4.3 T2 fact | **PROVED** |
| R16 INT-BIAS-XOR80 | Z3 QF_BV monolithic with no wrap: PROVED, 107.2 s | Z3 decomposed (P, M) and cvc5 on P, M: PROVED; per-element enumeration algebraic (as R15); `a->sum*bias` overflow: §4.3 | **PROVED** |
| R17 INT-NARROW-PACKS | exhaustive 2^32 (packs transliterated; the transliteration equals `int_ops` on [−2^17, 2^17) and the int32 extremes, by hash): 0 failures on the 255 values with \|q\| ≤ 127 | Z3 QF_BV: PROVED, 0.001 s; cvc5: PROVED; the Z3 packs formula equals `int_ops` on 151,200 inputs | **PROVED** |
| R18 INT-SUM-ACT | Z3 QF_BV decomposed (order lemma M with the AVX2 and AVX-512 shuffle trees modelled, PROVED) with the bound \|Σq\| ≤ 8,128 [D]; monolithic: PROVED with no wrap, 48.1 s | cvc5: on M PROVED; on the monolithic query UNKNOWN (timeout 600 s) | **PROVED**; the second solver agreed on the decomposed form |
| R19 RINT-MAGIC | Z3 (RNE, \|v\| ≤ 127): PROVED (0.22 s) | exhaustive 2^32 through the table: 0 failures on 2,247,884,802 in-range v; 0 failures up to \|v\| ≤ 2^22; RD and RU on both sides: 0 failures; **RZ on both sides: 1,123,942,273 failures** (the refutation §3.1 records); **RNE with DAZ, FTZ and DAZ+FTZ (rev1): 0 failures in the condition** | **PROVED** for the Env of the row (RNE, any DAZ/FTZ) |
| R20 F16-WIDEN | Z3, all 2^16 h, against the table's VCVTPH2PS (`smt_table.cvt_h2f`, pure BV): PROVED (0.033 s); the first run compared with `fp.to_fp` and is superseded | exhaustive 2^16 through the table under 8 MXCSR values: 0 failures; **cvc5 (now replayable without `fp.to_ieee_bv`): PROVED** | **PROVED** |
| R21 ISNAN-UCOMI | Z3 on the table's UCOMISS (`smt_table.comis`), DAZ = 0 and 1: PROVED | exhaustive 2^32 through `x2_comis` under 8 MXCSR values: 0 failures; cvc5: PROVED | **PROVED** |

**Count under §1's definition [D from the rows above], on the corrected routes:** **19 of the 21 rows are
proved; R02 and R03 are not**, because their primary route timed out in both solvers. R08-R11 are proved for
the Hearth instances the rows name (their generic form is evaluation of table entries, §1). The count itself is
unchanged (22 under the strict default: 21 rows + LOOP-LOCKSTEP). With R02, R03 and LOOP-LOCKSTEP not proved,
P2a's "every counted row and loop rule proved" is not met today. The act_q8 SIMD variants need R02/R03 (§7
question 1). LOOP-LOCKSTEP's written proof was not part of this run; it stays to be written and reviewed (§5).
For R01 (two inputs, no exhaustive route), the RC and FTZ independence of its Env column rests on the encoding
(MAX/MIN have no RC or FTZ input), which the differential of §3.2 checks under four environments only.
