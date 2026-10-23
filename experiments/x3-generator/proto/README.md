# X3 generator prototype (`x3gen`, proto)

Track: x3gen · Written 2026-10-23 on the laptop · Revised the same day after two review rounds
([Review log](#review-log)) · Status: **development prototype**. Nothing here is gate data (prereg
[X3-generator.md](../../../docs/m0/prereg/X3-generator.md) §4.9: building and unit-testing the
generator is development, not collection). The record is DRAFT. The meaning is **reviewed but not
frozen**: DESIGN §3.5's review found no transcription error, its wording fixes are applied here, and
the matching DESIGN §3.3 edits wait for the DESIGN owner ([MEANING-REVIEW.md](../MEANING-REVIEW.md)).
Nothing was measured for performance.

Tags as in [docs/m0/README](../../../docs/m0/README.md#evidence-tags). Every [M] below was measured
on 2026-10-23 on the laptop (Ryzen 9 7940HS, Zen 4, reported as "AMD64 Family 25 Model 116 Stepping
1"; Windows 11; Python 3.12.10; clang 23.1.3), single-threaded, by the command named, with its raw
output in [results/](results/). "[M, reviewer]" marks a reviewer's own measurements, quoted from
the review. Results were re-run after the second review round on the final code.

## What it is

The throwaway Python generator that [DESIGN §2](../DESIGN.md) chose over Exo:

- **one meaning** of Hearth's Q8/Q4 matmul slot in canonical IEEE order ([x3gen/hearth/meaning.py](x3gen/hearth/meaning.py));
- **schedules** built only from P_X3 primitives, each refusing applications that would change the
  FP DAG or the footprint ([x3gen/core/sched.py](x3gen/core/sched.py));
- **lowering** to a lane program and a **printer** that emits scalar, AVX2 and AVX-512 C for
  Hearth's `hx_kernels` seam ([generated/](generated/), [seam/x3-seam.patch](seam/x3-seam.patch));
- the **global checks C1–C4**: symbolic execution of the lane program on a bounded shape set, plus
  rules on the program text that carry each shape's result to every block count G
  ([x3gen/core/check.py](x3gen/core/check.py), [x3gen/core/sem.py](x3gen/core/sem.py)), judged
  first on a planted suite;
- a CRT-free C **bit-identity harness** against Hearth's own kernels ([bitid/](bitid/), [scripts/bitid.py](scripts/bitid.py)).

## Layout, and how each part counts (DESIGN §9.1)

| Path | Contents | Counted as |
|---|---|---|
| `x3gen/hearth/meaning.py` | formats, slot, preconditions, the meaning | M |
| `x3gen/hearth/schedules/*.py` | the three schedules | **S** |
| `x3gen/core/*.py` | IR, primitives, recipes, lowering, printer, interpreter, checker | L |
| `x3gen/isa/*.py` | one entry per intrinsic (C spelling, class, IEEE op, semantics key) | I |
| `generated/` | the six variants, `x3_gen.h`, the primitive log (`x3gen_report.json`) | printer output |
| `bitid/`, `scripts/`, `tests/` | harness, drivers, unit tests, planted suite | not counted |

## The meaning (M)

Per output (t, r): `acc = +0.0f`; for g = 0..G−1: `acc = acc + i2f(I) * (h2f(Wd) * Ad)` with
`I = Σ_{i<64} wq·xq` exact; store `canon(acc)`. Sources, all at Hearth b5d3f14: `NUMERICS.md:38-48`
(order), `:50` (Q4 bias identity), `:56-58` (canonical NaN), `:60-62` (batched = single);
`quant.c:388-405` and `:407-427` (scalar definition), `:16-35` (`q_f16`), `:53-65` (`q_canon`),
`:339-346` (PRE1 range, PRE2 sum); `hx_quant.h:20-28` (formats), `:49-57` (slot). The
preconditions are named **PRE1–PRE6** (not P1–P6, which are primitives) and carried as the strings
of `meaning.REQUIRES`:

| ID | `REQUIRES` string(s) | Source |
|---|---|---|
| PRE1 | `A.q in [-127, 127]` (also ActQ8's `value_range`, checked equal) | `quant_avx2.c:11`; `quant.c:339-340` |
| PRE2 | `A.sum == sum(A.q)` | `quant.c:343-346`; `NUMERICS.md:35` |
| PRE3 | `(mxcsr & 0xFFC0) == 0x1F80`: RC nearest, FTZ = DAZ = 0, all six exceptions masked; status flags free | 02 §2. MXCSR reads 0x1FA0 or 0x1FBB during the default-mode runs [M, `bitid.py`] |
| PRE4 | `Y disjoint from W and A`; `W and A readable, Y writable, over their extents` | [G] implicit in `hx_quant.h:49-57`; callers pass separate buffers (`model.c:341-352`, `:370-382`) |
| PRE5 | `n >= 0 and n % 64 == 0`; `T >= 0`; `0 <= r0 <= r1 <= rows(W)` | `quant.c:86-87`; `hx_quant.h:50-53` |
| PRE6 | `T <= 1 or ldy >= r1 - r0` | [G] implicit in `hx_quant.h:49-57`; callers (below) |

PRE6 makes the output map (t, r) → t·ldy + r injective, so "each output written once" is defined.
Hearth's slot contract (`hx_quant.h:49-57`) leaves it implicit; Hearth's callers pass ldy equal to
the matrix's row count (`model.c:448-452`, `:881`, `:888`) and split rows inside [0, rows)
(`model.c:298-300`), so they satisfy it. Outside PRE6 the result depends on the kernel's store order:
on Q4, n = 128, rows [0, 12), T = 3, ldy = 4, Hearth's AVX2 kernel differs from its scalar kernel in
4 words, and each x3 kernel equals the Hearth kernel of its own ISA [M, `scripts/bitid.py`,
`output_map_precondition_demo`]. The checker evaluates PRE5 and PRE6 on every shape **from the
`REQUIRES` text itself** and refuses a shape outside them (a harness error, not a verdict); it
refuses a `REQUIRES` string it does not know how it carries, and a PRE1 range that differs from the
format's. Store addresses are decoded through the injective map, so ldy < r1 is checked too. The
DESIGN §3.3 table that matches is in [MEANING-REVIEW-design.patch](../MEANING-REVIEW-design.patch).

The **meaning differential** (DESIGN §3.5): x3gen's interpreter runs the meaning tree itself with an
emulated binary32 (`rne_f32`, DESIGN §5.1; NaN results follow the x86 rules, so canon is visible)
and agrees with all six kernels on 240 random cases, 2,162 outputs, special scales included:
0 mismatches. A control meaning with canon removed differs from Hearth's scalar kernel in 640 of
those outputs, so the differential can see canon [M, `scripts/bitid.py`, seed 20261023]. Before the
fix it could not: the old `fp32` canonicalised every NaN, and the canon-less meaning matched
[M, reviewer]. The meaning review's own evidence is in [MEANING-REVIEW.md](../MEANING-REVIEW.md).

## Schedules and primitives

| Primitive | Implemented check (refuses …) | Used by |
|---|---|---|
| P1 split | non-constant factor; `dup_last` on an FP-carried loop | all SIMD |
| P2 reorder / distribute | interchanging two FP-carried loops; moving a loop across an FP-carried one unless every accumulator is private to it | all |
| P3 expand | expansion over an FP-carried loop; an accumulator not re-initialised inside | AVX2, AVX-512 |
| P4 vectorize | a reduction loop; lanes ≠ split factor; `dup_last` without masked store; guarded tiles | AVX2, AVX-512 |
| P5 lower_isum | interval proofs: maddubs pairs ≤ 32,767, int16 combine only if proved, dpbusd ≤ 2^31, \|I\| < 2^24; bias form needs PRE2; sign transfer needs PRE1 | all |
| P6 tail | via P1/P4 (cover once; dead lanes masked) | all SIMD |
| P7 unroll | non-constant trip count; then **every** application, because lowering has no unrolling (a logged unroll would record a fact with no effect) | — |
| P8 specialize | any predicate but `T == 1` (B12) | AVX2, AVX-512 |
| P9 hoist | anything but read-only W work; missing no-alias precondition; unblocked token loop | AVX2, AVX-512 |
| P10 block | composite of P1, P2, P3, P2-distribute, P2, each checked | AVX2, AVX-512 |
| P11 prefetch | non-W stream, non-positive distance | — |
| P12 map_fp | an entry whose `ieee` field does not name the meaning op (checked in lowering) | all (implicit) |
| P13 canon_store | lowerings outside {cmp_unord + blendv, cmp_unord + mask_mov, scalar branch} | all |
| P14 load_scales | packings other than GPR u64 + cvtph, or scalar h2f_bits | all |
| P15 commute | anything but fadd/fmul; a view with a store that lacks P13's canon (commutation is exact only up to the NaN payload, which canon erases) | — |

Every application is logged with its facts ([generated/x3gen_report.json](generated/x3gen_report.json)).
[tests/test_prims.py](tests/test_prims.py) has one or more refusing applications per primitive,
including planted 8, 16 and 22 at primitive level; [tests/test_check.py](tests/test_check.py) covers
the checker rules added after both reviews, and [tests/test_fp32_printer.py](tests/test_fp32_printer.py)
the x86 NaN rules, canon's visibility and the printer: 69 unit tests pass [M].

The schedules reproduce the hand kernels' structure: scalar rows-outside-tokens; AVX2 8-row tiles,
`dup_last` tail with masked store, a `T == 1` copy, token blocks of 8 with weight work hoisted,
maddubs/madd with an hadd transpose, Q4 bias and Q8 sign transfer chosen by the interval proof; AVX-512
whole 16-row tiles in quads with vpdpbusd and an unpack reduction, then 4-row tails one row per
128-bit lane.

## Global checks C1–C4 (DESIGN §4.3)

`check.check_func` runs, in order: C2 on the program text; C scoping; the static C1 rules; C1–C4 on
every shape of a bounded set, by symbolic execution with symbolic data (leaves are named by load
address only; lane maps are not trusted); then a coverage rule.

- **C1.** Each stored lane must equal the meaning's chain for the (t, r) its own store address
  names, as a hash-consed term derived from the meaning tree. A term equal only up to commutation
  is accepted only if a P15 application is logged (none is).
- **C2.** On the whole program text, executed or not: every statement carries a logged provenance
  id, and every call names a known isa entry outside the banned classes (FMA, double,
  approximation, MXCSR). The same test runs again on every executed statement. The provenance test
  is membership of a logged id, **bound to the primitive only at instruction-class level**: FP
  arithmetic only under P12 (fadd, fmul, i2f), P14 (h2f) or P15; FP compares, selects and stores
  only under P13; prefetch only under P11. It cannot tell which application of an allowed primitive
  created a node, so it does not establish DESIGN §4.3's "no node created outside P1–P15" in
  general; soundness rests on C1, C3 and C4 and on the class lint. **No verbatim C:** every string
  the printer copies is checked, here and again in the printer: identifiers (plain C names, no
  keyword, macro-style, `_t`, helper or intrinsic name), declared and cast types (a closed list),
  `lit` (decimal digits only), comment text (cannot end the comment), no call nested in another
  call's argument (the operator spellings such as `{0} - {1}` add no parentheses), a placeholder
  glued to a suffix (`x3_f32bits({0}u)`) takes only a non-negative literal, a call result is
  declared with the call's own type, and each argument has the kind its parameter takes, so C
  performs no numeric conversion the checker would read as bits (an integer to a float parameter or
  the reverse). The translation unit's fixed text (header comments, includes, guard) has closed
  forms in the printer.
- **C3.** Bit-vector layer: values that depend on at most two input bytes are tables, proved by
  enumeration over the declared domains (PRE1 removes −128). Ring layer: exhaustively verified
  polynomial fits, then a normal form with PRE2, compared with the meaning's sum. Every saturating
  or wrapping instruction needs an interval proof.
- **C4.** Exact output set, written once each; loads inside W rows [r0, r1) and A's blocks; no load
  or store when T = 0 or r0 = r1; shapes must satisfy PRE5 and PRE6, evaluated from `REQUIRES`.

**From the bounded shapes to every block count G.** Each shape fixes (n, T, r0, r1, ldy). These rules
extend its result to every G ≥ 1 with the same (T, r0, r1, ldy):

- *Text rules* (`structure`, `scopes`). G is declared once, at the top, as n / 64, and n is read
  nowhere else. A name is tainted if an integer definition of it reads n, G, a block index or a
  tainted name (a fixed point, so copies of G are tainted). A tainted value never reaches a branch,
  a `?:` condition, a comparison, a bit operation, a loop bound, a product with another tainted
  value or a C type narrower than 64 bits. The only loop with a tainted bound is the canonical
  `for (g = 0; g < G; g++)`, and such loops do not nest. Inside one, the only state carried from
  block to block is an FP accumulation `X = add(X, y)`, X is read nowhere else in the loop, and no
  store runs. C scoping holds: every name read is declared in an enclosing scope, and no declaration
  repeats or shadows a visible name, so the checker's flat environment means what the printed C
  means.
- *Affine forms* (`Machine`). Every G-dependent integer carries its form c0 + cG·G + cg·g. Such a
  value used as data is rejected. Every input load must be inside a block loop, at
  row·G·bs + g·bs + field (W) or (t·G + g)·72 + field (A), with the row, token and field independent
  of G and g and the field inside one block. Store addresses must not depend on G or g.
- *C integer types* (`Machine.sty`, `_fits`; review 2 finding 1). Index arithmetic is evaluated in
  the C types the printer emits: every parameter, `Let`, `For` and `Arr` has its declared type,
  literals are `int` (only values in int range; `lit` is decimal digits), and each operator applies
  the integer promotions and the usual arithmetic conversions. Every operand converted to the common
  type, every result, every cast and every initialisation or assignment must be representable in its
  C type, or the program is rejected: an unsigned wrap, a signed overflow and a narrowing are
  rejections, never wraps. `/`, `%` and comparisons between signed and unsigned operands are
  rejected outright. For a G-dependent value the range must hold for every 1 ≤ G ≤ Gmax and
  0 ≤ g < G, checked at the vertices of that triangle, where Gmax is the largest block count the
  shape's buffers allow (n = 64·G is an `int64_t`; W's first r1 rows and A's T·G blocks are objects of
  at most SIZE_MAX bytes; this is C's bound, wider and so stricter than the PTRDIFF_MAX compilers
  enforce).
- *Coverage.* Over the shape set, every statement runs and every `If` and `?:` takes both arms.
  Code that never runs is code the per-shape checks have not seen, and is rejected. Statements and
  branch sites are identified by their **position** in the program (the index path through
  statement lists, loop bodies and branch arms, plus the sub-expression path of a `?:`), not by
  object identity, so one statement object placed at two positions is two sites (review 2
  finding 3).

Under these rules control flow does not depend on G, each block runs the same operations on the
leaves of block g of a fixed row and token, and the only cross-block state is the accumulations.
The trace for any G is the checked trace with each block loop's body repeated, so the stored terms
are canon(F_{t,r}(G)) and the loads stay in bounds for every G ≥ 1 [inference: argued here, not
machine-checked]. The argument also needs the printed C to compute what the checker computed;
the C-type, verbatim-text and argument-kind rules are what make that so for the constructs the
printer emits. T, r0, r1 and ldy are **not** generalised: row and token tails are executed
concretely, which is what DESIGN §4.3's symbolic addresses would remove.

Results [M, `scripts/check_all.py`, `tests/planted.py`]:

- **Accept.** All six generated variants pass on 31 / 53 / 47 shapes (scalar / AVX2 / AVX-512):
  every row-tail width, every token-tail width (T = 1–9, 16, 17), G = 1–5 on both the `T == 1` and
  `T > 1` paths, r0 > 0, T = 0, r0 = r1, and three output layouts (r0 = 0 with ldy = r1; ldy =
  r1 − r0 < r1; T = 1 with ldy = 1). Every statement runs (30 / 37 / 302 / 263 / 505 / 433, in the
  order scalar Q8, Q4, AVX2 Q8, Q4, AVX-512 Q8, Q4) and every branch site takes both arms
  (0 / 0 / 12 / 12 / 7 / 7 sites). That is 9,558 stores and 23,388 `i2f` operands proved, with 0
  commutations.
- **Reject.** All 57 planted programs are rejected: DESIGN §4.5's 28; 13 added after the first
  review (29–41: DAG changes that only switch on outside the bounded shapes, plus a C-scope
  mismatch); 12 from the second review's checker reviewer (42–53: C integer semantics, verbatim
  print channels, an object placed twice, a narrow array); and 4 the reviser found while fixing them
  (54–57: a nested operator call, a glued placeholder, a retyped call result, an integer to a float
  parameter); [tests/planted.py](tests/planted.py). By the stage that fired first: static C2 audit
  19, static C1 rules 15, per-shape execution 20, coverage 2, C scoping 1. Per-shape execution alone
  rejects 48 of 57; the nine it misses need a text rule (32, 51 coverage; 33, 47, 48, 53, 54 the C2
  audit; 39 carried state; 41 C scoping). The pre-fix checker **accepted all 16 of 42–57**
  [M, the HEAD tree exported read-only to scratch, `run_one` on each], and printed by the pre-fix
  printer every one of them changes outputs in C except 52 (below).
- **This is evidence about these mutants, not adequacy.** Every planted item, and the checker, was
  written by the same model family. Before the second review the record said "rejects all 41"; that
  review's fresh mutants by other methods found 12 accepted programs, 11 of which change outputs in
  C [M, reviewer]. More holes of other kinds may remain.
- **Findings.** The first run accepted planted 16 and 18; the shape set then ran the `T == 1` copy
  only with G ≤ 2. The structural rule and G = 3–5 shapes were added in response. The first review
  showed that this rule, plus bounded execution, still accepted programs that change the DAG only
  for G ≥ 6, T ≥ 18, r1 − r0 ≥ 64 or n ≥ 4096; the text rules replaced it. The second review showed
  that the checker computed over Z where C does not, read only some of the strings the printer
  copies, and keyed coverage on object identity; the C-type, verbatim-text and position rules
  replaced those.
- **No new false rejection seen.** The reviewer's blind fuzzer (600 single-site mutants, seed
  20261023, all six variants) on the final checker: 13 accepted, 587 rejected, 0 crashes; all 13
  accepted mutants are equivalent (11 swaps of commutative integer arguments; `(r1 − r) < 16`
  instead of `< 8` in the row-tail clamp, which leaves nr ≥ 8 for every full tile and so the same
  lanes and masks; `<=` instead of `<` in the token-tail clamp, equal at the boundary), and all 13 also
  pass at G = 6, 7, T = 19 and 40 rows [M, reviewer's `fuzz.py`, re-run by the reviser]. The
  reviewer's strength-reduced block offset (`gacc += 34`) is still rejected (Deviations, item 1).

## Results

| What | Result | Tag |
|---|---|---|
| Bit identity, generated vs Hearth's scalar, AVX2 and AVX-512 hand kernels | 0 mismatching words. 38,656 cases per configuration × 3 configurations (X0 config B flags + `-mavx512vnni`; the same + `/clang:-ffp-contract=off`; config D's flags, Windows target). Shapes: 2 dtypes × 4 seeds × 4,832 (n, rows, T): n ∈ {64, 128, 192, 320, 4096} × rows 1–67 × T ∈ {1..9, 16}, plus, on 19 row counts from 1 to 67, n ∈ {384, 448, 8192} (G = 6, 7, 128) and T ∈ {17, 23, 24, 25, 33, 40}. ldy runs over rows .. rows + 5, so the tight layout ldy = rows is included. Checks: whole call (padding included), batched = single, random row splits, no writes for T = 0 / r0 = r1, sub-range footprint. All buffers between no-access guard pages: 0 faults | [M] `scripts/bitid.py --seeds 4` |
| The same corpus under seven non-default MXCSR modes | 0 mismatching words between each x3 kernel and the Hearth kernel of the same ISA, and between every kernel and Hearth's scalar kernel, in RD, RU, RZ, FTZ, DAZ, FTZ + DAZ and RZ + FTZ + DAZ, every case, all 3 configurations: 12,198,518 words per mode per configuration. The modes act: Hearth's scalar result differs from its default-mode result in 5,459,089 (RD), 5,415,243 (RU), 5,873,585 (RZ), 142,121 (FTZ), 234,442 (DAZ, and FTZ + DAZ) and 5,962,714 (RZ + FTZ + DAZ) words. Kernels with the same FP DAG agree under every mode, so this is a stronger identity test than the default mode alone; the meaning itself is defined under PRE3 | [M] |
| Coverage of that corpus | Per configuration, 11,202,184 reference outputs: 6,386,970 normal, 3,280,397 NaN, 1,363,763 inf, 151,923 zero, 19,131 subnormal. Scales: W 159,845 NaN, 159,813 inf, 1,635,878 subnormal; A 25,771 NaN, 70,980 inf, 843,456 subnormal. Reference hash `07b12e55b1ece83b` (FNV-1a 64), equal under all three configurations | [M] |
| Object scan | 0 FMA, approximation or MXCSR-writing instructions in the generated and the hand objects, all configurations. MXCSR during the default-mode runs 0x1FA0 (`clangcl_B`) and 0x1FBB (the other two): control bits 0x1F80 (PRE3 holds), status flags set by the corpus; the harness, not the kernels, sets the other modes | [M] |
| C harness adequacy | 40 of 57 planted mutants change outputs or fault (quick corpus, `clangcl_B`). Not seen: 13 (rewrites W with the same bytes), 24 (early canon, invisible in outputs), 28 (in-bounds load at T = 0), 52 (a narrow `int16_t` copy of rb, which wraps only for n > 61,632, outside the corpus); the checker rejects all four. The revised printer refuses to print 9 (43, 47–50, 53–56: the defence in depth of C2); 3 use test-only entries with no C spelling; 22 is a precondition change. Printed by the pre-fix printer, 43, 47–50 and 53 change 44,996–53,964 words [M, reviewer] and 54–57 change 171,443 / 70,371 / 200,745 / 67,962 words [M, reviser] | [M] `scripts/mutants_c.py` |
| isa entries vs silicon | 58 (entry, immediate) pairs × 20,000 random and edge vectors: 0 mismatches. `scalar.h2f_bits`: 0 of 65,536 inputs differ from Hearth `q_f16` or F16C, bit for bit. The 4 canon lowerings: 0 mismatches over all 2^32 patterns each (4–5 s each). Not re-run after either review: `isa/` did not change, and the one oracle change (`fp32`'s NaN payloads) does not reach it, because it compares NaN results by NaN-ness only (`isa_validate.py:429-430`) | [M] `scripts/isa_validate.py --n 20000` (first revision) |
| Seam patch | Applies to b5d3f14 (`git apply --check` rc 0), patch SHA-256 `55250a45…2559` unchanged. Off: objects identical to pristine except the COFF TimeDateStamp. On: the AVX2/AVX-512 tables hold the generated functions (4 of 4, run time) and the scalar table's relocations name them. Warnings: 6 unused static hand functions, as DESIGN §6 predicts. Re-run after the second review with the regenerated files | [M] `scripts/seam.py` |

The generated C differs from the committed `e321593` output in the two provenance lines (generator
and meaning SHA-256) and in one line of each AVX-512 function: the tail mask is now
`(__mmask8)((1 << nr) - 1)` instead of `((1u << nr) - 1u)`, because `lit` admits decimal digits only.
Every corpus result above is identical to the committed run except its timings [M, comparison of
`results/bitid.json` with the committed one].

### The schedule-lines ratio (prereg §4.7, DESIGN §9)

| Quantity | Value | Tag |
|---|---|---|
| H, X3-LOC-C over the dispatched Q4/Q8 closure, `quant_avx2.c` 129 + `quant_avx512.c` 174 | **303** (4,188 tokens): reproduces DESIGN §9.2 | [M] `scripts/count_lines.py` |
| S_max = ⌊0.30 · H⌋ | 90 | [target] |
| Schedule text (X3-LOC-PY, black 26.5.1, line length 100): scalar 8, AVX2 15, AVX-512 20 | 43 (420 tokens) | [M] |
| Library lines flagged by the specificity lint | 7, all `prefetch` (P11's own name) matched by the lint's `tch` pattern: false positives counted until an independent reviewer signs them off. Neither 2026-10-23 review ruled on them. The second revision first raised the count to 94 (`re.fullmatch`, the keyword `switch`, "RQ4", "hx_"); it was rewritten to avoid those tokens rather than count them | [M] |
| **S** (conservative: schedule + flagged lines) | **50** | [M] |
| **S / H** | **0.165** (0.142 without the 7 flagged lines) | [D] |
| S_tok / H_tok | 0.100 | [D] |
| Beside it: M 67, L 4,187 (the checker is 2,267 of it: `check.py` 1,876, `sem.py` 391), I 229; (M + S) / H = 0.386; generated C 119 / 615 / 992 LOC | | [M], [D] |

This is development data on untuned schedules (tuning adds lines, DESIGN §10), on an unfrozen record,
and not a G4 verdict. The generator is large next to the 303 lines it replaces, as DESIGN §9.3 asks to
state plainly; the two reviews' fixes added 1,044 lines of library, all in the checker, the printer,
the primitive checks and `fp32`, and none of schedule. The recipes in `core/recipes.py` carry the
instruction idioms (hadd transpose, quad unpack and reduction); whether that is generic library or
"hand-writing in disguise" (DESIGN §12) is for an independent reviewer to judge; neither 2026-10-23
review ruled on it.

## How to run (from this directory)

```text
python -I scripts/gen.py generated                                     # regenerate (deterministic)
python -I -m unittest discover -s tests                                # 69 unit tests
python -I scripts/check_all.py                                         # C1-C4 on the six variants
python -I tests/planted.py                                             # the planted suite (57)
python -I scripts/count_lines.py HEARTH_CLONE BLACK_DIR                # H, S, lint
python -I scripts/bitid.py --hearth HEARTH_CLONE --llvm LLVM --scratch DIR --seeds 4
python -I scripts/isa_validate.py --hearth HEARTH_CLONE --llvm LLVM --scratch DIR --n 20000
python -I scripts/seam.py --hearth HEARTH_CLONE --llvm LLVM --scratch DIR
python -I scripts/mutants_c.py --hearth HEARTH_CLONE --llvm LLVM --scratch DIR
```

`proto/generated` must be regenerated whenever `core/` or `isa/` change; a unit test fails otherwise.
Hearth sources are read from the clone and copied only into the scratch directory; the scalar
reference kernels are extracted from `quant.c` by line range there. Nothing from Hearth is copied
into this repository except DESIGN §5.1's `scalar.h2f_bits`, a transcription of `q_f16`.

## Toolchains installed on the laptop (user directory; no PATH, registry or installer)

| Tool | Where | Verification |
|---|---|---|
| LLVM 23.1.3, `clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz` (901,331,280 B) | `C:\Users\Pierce Lonergan\tools\llvm-23.1.3` | SHA-256 `9ee6a219…b5b8`, equal to GitHub's published digest and to X0's desktop record; GPG "Good signature" from D574 BD5D 1D0E 9889 5E3B F900 44F2 485E 45D5 9042 (Tobias Hieta, key from releases.llvm.org/release-keys.asc). `clang-cl.exe` SHA-256 `9584244d…8d8261`, equal to X0's desktop binary [M] |
| black 26.5.1 (py3-none-any) with click 8.4.2, colorama 0.4.6, mypy-extensions 1.1.0, packaging 26.2, pathspec 1.1.1, platformdirs 4.11.5, pytokens 0.4.1 | `C:\Users\Pierce Lonergan\tools\black-26.5.1` (pip `--target`, offline, `--no-deps`) | Each wheel's SHA-256 equal to PyPI's published digest [M]. Used only for X3-LOC-PY and to format this code |

Nothing new was installed for the revision. The laptop has no MSVC or Windows SDK, so the test DLL
is built CRT-free: tiny shim headers and `bitid/rt.c` (`memcpy`, `memset`, the `/GS` cookie). These
change no kernel code generation.

## Deviations from DESIGN, and what is not done

1. **C1–C4 run on a bounded shape set**, and the rules above carry each shape's result to every G
   [inference]. T, r0, r1 and ldy are not generalised; DESIGN §4.3's symbolic addresses are not
   implemented. Known incompleteness (rejected though correct): a split of the block loop (allowed
   by P1); loads of W or A outside a block loop (no current schedule has one); and **integer
   induction variables carried across blocks**, such as a strength-reduced block offset
   `gacc += 34` instead of `g * 34` (review 2 finding 6; Hearth uses that idiom in its activation
   quantisers, `quant_avx2.c:84`, while its matmul kernels use `(size_t)g * bs`, `quant_avx2.c:241`,
   `:275`, `quant_avx512.c:283`, `:296`, `:321`). An affine form for such a variable (c0 + k·g) would
   accept it; that is not implemented.
2. **The accept half is the six generated variants.** DESIGN §4.5's transliterations of Hearth's
   six hand kernels are not written; DESIGN §4.5 and the prereg (§4 item 2, §9) require them, run
   through `check_func`, before T0. They will need more of C than the generator emits (struct
   pointer types such as `const hx_block_q8 *`, a scalar `isum` loop), so the checker's type and
   pointer models will need extending, and each extension needs the same C-semantics care.
3. **Lane maps are not mandatory.** Some FP operations carry a hint and stores carry none. The
   checker ignores hints and derives identities from addresses, which is the trusted path.
4. **No T1 export** (`.lanes.json`).
5. **Arrays of vectors.** The printer emits `__m256 acc[8]`-style arrays for accumulators expanded
   over a token block, as Hearth does. DESIGN §5.2 says straight-line SSA only and calls this an
   empirical question for tuning.
6. **Provenance header** carries a generator SHA-256 (core + isa sources), not a commit, because
   nothing here is committed.
7. **Bit identity ran outside Hearth's build.** It used Hearth's extracted scalar kernels and its
   unmodified SIMD files in a DLL, not `test_quant` or the golden suite (DESIGN §7 steps 4–5).
   Neither MSVC (configuration A) nor WSL Linux Clang (configuration D proper) is on the laptop, and
   the desktop was off limits.
8. **isa validation depth.** It used 20,000 vectors per entry against DESIGN §5.4's ≥ 10^6
   [target]. Per-lane exhaustive runs covered only `h2f` and canon; maddubs pairs were not run
   exhaustively.
9. **Review coverage.** Two same-family, independent-context review rounds (2026-10-23). The first
   covered the checker, the primitives, the meaning's preconditions, the bit-identity corpus and this
   report. The second covered the meaning against `NUMERICS.md` §3 and `quant.c:388-427` (DESIGN
   §3.5: no transcription error; [MEANING-REVIEW.md](../MEANING-REVIEW.md)) and the revised checker,
   with fresh mutants by other methods. All findings are fixed. Not yet done: DESIGN §4.5's review
   of the planted suite as such; a review of this second revision of the checker (the C-type,
   verbatim-text, position and argument-kind rules are new code that no one but the reviser has
   read); the recipes question of DESIGN §12.
10. **Unused primitives.** P15 is implemented and checked but unused. P7 refuses every application
    until lowering implements unrolling. P11's lowering exists but no schedule exercises it.
11. **DESIGN body not edited.** PRE1–PRE6 (§3.3), the renames, planted items 29–57 (§4.5) and the
    §17 rows are in [MEANING-REVIEW-design.patch](../MEANING-REVIEW-design.patch) for the DESIGN
    owner; the body is outside this track's write scope.
12. **Nothing measured for performance**, by instruction. That needs the desktop and quiet windows.
13. **C2's provenance test is bound at class level only** (review 2 finding 5). FP arithmetic,
    FP compares and selects, stores and prefetches must carry the id of the primitive whose licence
    covers them; any other statement passes with any logged id. DESIGN §4.3's "a lint rejects any
    node created outside P1–P15" is therefore met only for those classes.
14. **The C-semantics model is for the printed constructs only.** Integer types are the x86-64 ones
    on which LP64 and LLP64 agree (`long` is refused); pointer types are three byte and float
    pointers; integer literals in index arithmetic must be `int`; an intrinsic's integer parameter
    reads its argument modulo 2^w, as compilers do on x86 (implementation-defined in C). Pointer
    arithmetic is checked only where a load or store uses it, not for staying inside the object.

## Review log

| Date | Reviewer lens | Family | Findings (blocker / major / minor) | Accepted | Rejected |
|---|---|---|---|---|---|
| 2026-10-23 | Reviewer 1: checker soundness (C1–C4), primitives, meaning preconditions, bit-identity corpus, report | Claude (same family as author; independent context) | 0 / 2 / 3 | 5 | 0 |
| 2026-10-23, round 2 | Reviewer 1: the meaning against `NUMERICS.md` and `quant.c` (DESIGN §3.5) | Claude (same family as author; independent context) | 0 / 1 / 5, and one no-change result | 7 | 0 |
| 2026-10-23, round 2 | Reviewer 2: the revised checker, by fresh mutants of other methods (C-semantics differential, print-channel audit, object identity, blind fuzzing) | Claude (same family as author; independent context) | 0 / 3 / 4 | 7 | 0 |

### Round 1

The reviser (same family, another independent context) re-ran or re-read the evidence of every
finding before fixing it. All five were accepted; one probe of finding 2 was refined.

| Finding | Verification | Change |
|---|---|---|
| 1 (major): C2 runs only on executed statements; an FMA under `if (G >= 6)` was accepted | Confirmed [M, reviewer probe `probe_c1.py` re-run on the pre-fix code: both FMA mutants ACCEPTED on all 50 shapes] | `audit_static`: C2 over the whole text, every arm and loop body, before anything runs; the dynamic test stays. Planted 29, 30 (rejected by the static audit) |
| 2 (major): "holds for every G" unsupported; 8 shape-guarded mutants accepted | Confirmed [M, the same probe: all 8 ACCEPTED]. The reviser found 5 more holes of the same kind, all accepted by the pre-fix checker [M, reviser probe]: a copy `G2 = G` in a branch; an address offset by (G−1)(G−2)(G−3)(G−4)(G−5)·72; loop-carried integer counters C(g, 5); a G-dependent constant feeding a lane select; and a canon computed into shadowing declarations, which the checker's flat environment saw but the printed C does not (C stores the uncanonicalised value: 20,103 mismatching words in the C harness [M]). One probe, "(i2f·dw)·dx only when T ≥ 18", was vacuous as built: it changed the `T == 1` copy, which never runs when T ≥ 18. Planted 32 changes the `T > 1` path instead [inference: the pre-fix checker had no coverage rule and no shape with T ≥ 18, so it would accept it] | The reviewer's three fixes (coverage; no branch, `?:` or comparison on G, n or the block index; affine addresses in g), extended: taint by fixed point, no product of two G-dependent values, 64-bit types, carried state only as FP accumulations, no store in a block loop, affine forms checked on every load and store, no G-dependent data, C scoping. Claim amended to "every G ≥ 1 for the executed (T, r0, r1, ldy)". Planted 29–41 |
| 3 (minor): commutation accepted without a logged P15; P15 unchecked side condition; P7 logs a fact lowering ignores | Confirmed by reading `check.py`, `sched.py`, `lower.py` | (a) a commuted term needs `P15.commute#` in the log; (b) P15 needs P13 canon at every store of the view; (c) P7 refuses every application. Tests in `test_prims.py` and `test_check.py` |
| 4 (minor): no precondition on the output layout | Confirmed: the slot contract is silent; on the reviewer's shape Hearth's AVX2 and scalar kernels differ in 4 words [M, `output_map_precondition_demo`] | P6 (since round 2 named PRE6) in `meaning.REQUIRES`; shapes outside it refused; store decode through the injective map; three output-layout shapes added; DESIGN §3.3 row proposed in the status note |
| 5 (minor): corpus misses ldy = rows, T > 16, G > 64 and non-default MXCSR | Confirmed by reading `scripts/bitid.py` | Corpus extended (ldy = rows .. rows + 5; T up to 40; G = 6, 7, 128); `x3t_case_modes` runs seven MXCSR modes per case; separate rows above |

The reviewer's own harness reported 0 mismatching words for all six kernels in 8 MXCSR modes on
4,000 adversarial cases per configuration, and an independent binary32 model agreeing with Hearth's
scalar kernel on 725,699 outputs [M, reviewer].

### Round 2

The reviser (same family, a further independent context) re-ran or re-read the evidence of every
finding before fixing it: the reviewers' scripts were re-run on the pre-fix code where they make a
claim about it, and all of them on the final code. **Reviewer 1** (the meaning): no transcription
error; seven findings, all accepted, one (the precondition names) with a modified fix. The
per-finding record is [MEANING-REVIEW.md](../MEANING-REVIEW.md) §3. **Reviewer 2** (the checker):

| Finding | Verification | Change |
|---|---|---|
| 1 (major): index and pointer arithmetic evaluated over Z, not in the printed C's types; A1–A5 (unsigned wrap, a `0u` literal, `(int)` narrowing, `(size_t)G − 6`, a `uint32_t` holding −1) accepted, 39,909–48,248 words differ in C | Confirmed: `fresh.py` reports all five ACCEPTED on the pre-fix checker, and planted 42–46 (the same programs) are ACCEPTED by the HEAD tree [M]. The reviser found the call-side twin: an argument C converts numerically at the call (planted 57, `_mm256_set1_ps(0x7fc00000)`, ACCEPTED pre-fix, 67,962 words differ [M]) | Typed evaluation as the reviewer proposed (`Machine.sty`, `_fits`, Gmax), with literals limited to int and `lit` to digits; plus argument kinds per isa entry (`arg_kinds`). The AVX-512 tail mask is printed without `u` suffixes. Planted 42–46 and 57; unit tests `CIntegerSemantics`, `CallArgumentKinds` |
| 2 (major): Comment text, identifiers, declared types and cast types printed verbatim and never read; B1–B4 (and B1f, an FMA) accepted, 44,996–53,964 words differ | Confirmed: all five ACCEPTED pre-fix [M, `fresh.py`; planted 47–50, 53 on the HEAD tree]. The reviser found three more channels of the same kind, each ACCEPTED pre-fix and each changing outputs: a call nested in an operator-spelled argument (171,443 words), a placeholder glued to a suffix (70,371) and a call result declared with another type (200,745) [M, `prefix_c.py`, pre-fix printer] | `audit_static` checks every printed string (identifiers, types, casts, literals, comments, nesting, glued placeholders, call-result types); the printer repeats the checks and also closes the translation unit's fixed text. Planted 47–50, 53–56; unit tests `VerbatimChannels` |
| 3 (major): coverage keyed on object identity; C1 (the update object placed again under `T ≥ 19`) accepted, 31,753 words differ | Confirmed: C1 ACCEPTED and its deep-copied control rejected pre-fix [M, `fresh2.py`] | Coverage keyed on program positions (statement path, plus the sub-expression path of a `?:`). Planted 51; unit test `CoverageByPosition` |
| 4 (minor): the narrow-type rule skipped `Arr`; D1/D2 accepted | Confirmed [M, `fresh2.py`]: D1 ACCEPTED pre-fix, invisible in C below n = 61,632; D2 ACCEPTED, 3,390 words and 76 guard-page faults | Integer `Arr` holding a block-count value must be 64-bit (`structure`); the typed evaluator rejects the same independently. Planted 52 |
| 5 (minor): C2 provenance is membership only | Confirmed by reading `audit_static`; every planted item borrows a real id | **Modified fix:** both options, partly. Provenance is bound at instruction-class level (FP arithmetic to P12/P14/P15, compares, selects and stores to P13, prefetch to P11); with it, planted 10, 13, 24 and 40 are rejected by the static audit, earlier than before. The remaining limit is stated in Deviations item 13 and the DESIGN status note |
| 6 (minor): a correct strength-reduced block offset is rejected | Confirmed: `valid_bump.py` rejected pre-fix and post-fix [M]; the reviewer's blind fuzzer re-run on the final code finds 13 accepted mutants, all equivalent, and 0 crashes [M] | Listed as known incompleteness (Deviations item 1); the hand-kernel transliterations remain a pre-T0 requirement (Deviations item 2). Not implemented: an affine form for integer induction variables |
| 7 (minor): "rejects all 41" rests on the reviser's own mutants; MEANING-REVIEW.md missing | Confirmed: 12 of 12 fresh mutants accepted pre-fix [M, reviewer] | Results now say what the suite shows and what it does not; planted 42–57 added (DESIGN §4.5 "more may be added"); `planted_suite_min` stays 28; the prereg's "all 28" became "every item of the suite" (a tightening); the suite and the C harness re-run on the final code (57 of 57 rejected; 40 of 57 change outputs in C, 9 refused by the printer). MEANING-REVIEW.md written |

No finding of round 2 was rejected. Evidence scripts: the reviewers' under
`scratchpad/x3meaning/chk/` (fresh.py, fresh2.py, fuzz.py, valid_bump.py), the reviser's under
`scratchpad/x3meaning-rev/` (the HEAD tree exported read-only, `prefix_c.py`, the re-run outputs).

These reviews' independence is weaker than ROADMAP asks: the author, the reviewers and the revisers
are all Claude models (m0/README).
