# X3 design: one meaning regenerates the Q4/Q8 matvec triplets

Track: x3 · Written: 2026-10-16 · Revised: 2026-10-16, after two same-family reviews (§17) ·
Status: design only. Nothing has been built, compiled or measured for X3 yet. The only measurements
in this document are the line counts in §9, taken from the Hearth source, and the Exo facts in §2.2,
read from public pages. Toolchain facts quoted from X0 are X0's measurements, cited as such. The
operating characteristics in §8.8 are simulated [S] with the script in Appendix C.
ROADMAP anchor: [§3.4](../../docs/ROADMAP.md#34-x3-one-meaning-regenerates-the-triplets-weeks-14),
with §1 rule 4, §10 and DR-018. Pre-registration: [docs/m0/prereg/X3-generator.md](../../docs/m0/prereg/X3-generator.md)
(DRAFT). ROADMAP is authoritative for every gate, amber band, kill and cost. This document makes
those terms precise but never loosens them. Where it proposes something ROADMAP leaves undefined, it
says so and lists the point in §14 (Owner questions).

**Status note, 2026-10-23 (x3gen and x3meaning tracks, laptop; changes no definition in this
document; revised the same day after two independent review rounds).** A development prototype of
x3gen exists in [proto/](proto/README.md). It contains:
- the meaning, reviewed under §3.5 (no transcription error; [MEANING-REVIEW.md](MEANING-REVIEW.md)),
  with its preconditions renamed **PRE1–PRE6** and reworded (PRE3 is now the MXCSR predicate
  `(mxcsr & 0xFFC0) == 0x1F80`; PRE5 states the whole shape domain; PRE6, `T ≤ 1 or ldy ≥ r1 − r0`,
  is new). **Not frozen**: §3.3 below still has the old rows until the patch is applied;
- P1–P15, each with its own precondition check (P7 refuses every application, because lowering has
  no unrolling);
- lowering and the printer for the six variants;
- the seam patch;
- C1–C4 as a symbolic checker over a bounded shape set. Rules on the program text (C2 on every
  statement, executed or not, and on every string the printer copies; taint, affine-address and
  carried-state rules for C1; C scoping; statement and branch coverage keyed on program positions)
  and index arithmetic evaluated in the printed C's integer types carry each shape's result to every
  block count G [inference]. T, r0, r1 and ldy stay bounded.

Development data only, [M] on the laptop, re-run on the final code:
- **Bit identity.** The generated kernels match Hearth's scalar, AVX2 and AVX-512 kernels on
  3 × 38,656 cases (n up to 8192, T up to 40, ldy = rows included) with NaN, inf and subnormal
  scales, and also under seven non-default MXCSR modes. The meaning differential: 0 mismatches
  against all six kernels; a control meaning without canon differs in 640 of 2,162 outputs, so the
  differential now sees canon.
- **Checker.** It accepts the six variants and rejects all 57 planted programs: the 28 of §4.5 and
  29 added after the reviews (29–57). That is evidence about these mutants only. Before round 2 the
  prototype rejected all 41 it then had, yet round 2's checker reviewer found 12 fresh mutants it
  accepted, 11 of which change outputs in C; they are items 42–53 now. Every item and the checker
  come from one model family.
- **Line counts.** S = 43 schedule lines, or 50 counting 7 specificity-lint false positives
  (`prefetch`), against H = 303 (reproduced exactly), so S/H = 0.165 [D].

Reviews: round 1, 0 blocker / 2 major / 3 minor; round 2, the meaning (0 / 1 / 5 and a no-change
result) and the checker (0 / 3 / 4). All accepted and fixed; same family, independent contexts
([proto README, Review log](proto/README.md#review-log); [MEANING-REVIEW.md](MEANING-REVIEW.md)).

Proposed for this document (not applied: the body is outside these tracks' write scope), as a patch
the DESIGN owner can apply, [MEANING-REVIEW-design.patch](MEANING-REVIEW-design.patch):
- §3.3, the PRE1–PRE6 table: PRE3's MXCSR predicate; PRE4 re-sourced as a judgment ("implicit in
  `hx_quant.h:49-57`; callers pass separate buffers"); PRE5's shape domain; the new PRE6 row,
  recorded as a domain restriction, not a change to the arithmetic. This must land before the
  meaning's hash is taken;
- the precondition renames elsewhere in the body (§3.5, §4.2, §4.3 C3, §4.4 B7, §4.5 item 22,
  §7 step 6) and in the prereg's threats table;
- §4.5, items 29–57 of `proto/tests/planted.py`, as "more may be added" allows;
- §17, the three 2026-10-23 review rows.

Also proposed, not in the patch: §4.3, the implemented forms (C2's lint on the whole text and on
every printed string; the coverage, taint, affine-address, carried-state, scoping and C-type rules
of C1). And a stated limit for §4.3 C2: the prototype binds provenance to primitives only at
instruction-class level (FP arithmetic to P12/P14/P15; FP compares, selects and stores to P13;
prefetch to P11), so "a lint rejects any node created outside P1–P15" holds only for those classes.

Not done:
- the T1 export;
- transliterations of the hand kernels (§4.5; needed before T0);
- C1–C4 over symbolic addresses in T, r0, r1 and ldy;
- MSVC and Linux builds;
- any timing;
- a review of the second checker revision, and §4.5's review of the planted suite as such.

[proto/README.md](proto/README.md) lists the deviations from this document.

**Evidence tags.** [M] measured, with who and when. [D] derived, with the formula. [S] simulated.
[G] judgment. [inference]. [target] a pre-registered choice. Numbers quoted from a dossier keep its
label, for example "69.6 GB/s (measured, busy machine) [R11]". "x3 track" means the agent that wrote
this file, working on 2026-10-16.

**Contents**
1. What X3 must show
2. Generator choice: a throwaway Python generator, not Exo
3. The meaning
4. The schedule primitive set P_X3
5. x3gen architecture
6. Linking generated C into a scratch Hearth through `hx_kernels`
7. Bit-identity protocol
8. Measurement protocol
9. The schedule-lines rule (at most 30%)
10. The two-week tuning budget
11. Outcomes and what follows from each
12. Risks
13. Tombstones (proposed for DECISIONS.md §4)
14. Owner questions
15. Proposed changes to other documents
16. Cost and calendar
17. Review log
- Appendix A. `count_lines.py` (draft)
- Appendix B. Run and verdict record schemas
- Appendix C. `oc_sim.py`, the operating-characteristics simulator

---

## 1. What X3 must show

ROADMAP §3.4, made concrete:

- **Scope: six variants.** The Q4 and Q8 weight `matmul` slots of Hearth's `hx_kernels` table, each
  for three ISAs: scalar, AVX2 and AVX-512. That makes {Q4, Q8} × {scalar, AVX2, AVX-512} = 6
  generated functions.
  - The slot is a matmul over T tokens, with type `hx_matmul_fn` (`hx_quant.h:49-57`). "Matvec" is
    its T = 1 case. The generated functions must implement the whole slot contract (all T ≥ 0,
    any row range `[r0, r1)`, `ldy`). `test_quant` and the decode guard both call them with T > 1:
    prefill evaluates the prompt in one call.
  - **Out of scope.** `act_quantize_q8`, the F32/F16/BF16 slots and the canonical helpers stay
    hand-written and identical in both arms.
- **One meaning.** A single kernel meaning, generic over the weight format
  F ∈ {BlockQ4, BlockQ8}. Hearth's hand kernels are shaped the same way: each SIMD file has one
  `mm_quant(q4, …)` (`quant_avx2.c:322-332`, `quant_avx512.c:342-356`).
- **Schedules.** One or more schedule files per ISA. Each applies only primitives from P_X3 (§4).
  Their text is counted under §9.
- **Comparator.** Hearth's own hand kernels at the pinned commit, built with the release flags.
  This is `hearth-c-ref@b5d3f14`. It is **provisional, pending D0-3**, which names the permanent
  `hearth-c-ref` lineage.
- **Gate, amber and kill.** Copied verbatim into the pre-registration (§8 there), and operationalised
  here in §7–§11.

---

## 2. Generator choice: a throwaway Python generator, not Exo

ROADMAP §3.4 allows either "a throwaway Python prototype of DAG-preserving schedule primitives, or Exo
(MIT, emits C)". **Recommendation: a throwaway Python generator (`x3gen`).** It borrows Exo's
vocabulary but does not depend on Exo. The reasons are in §2.4. Exo is buried as a scoped, revivable
tombstone (§13).

### 2.1 Criteria

1. **Soundness for canon.v1.** Could the tool's own equivalence check be used as evidence that the
   FP op-DAG is unchanged? (DR-021; 02 §1.)
2. **Instruction coverage.** Can it express what the hand kernels use without new trusted
   instruction assertions? That means `vpdpbusd`, `vpmaddubsw`, `vpmaddwd`, `vpsignb`, `vpabsb`,
   `vcvtph2ps`, the nibble unpack and the 0x80 xor bias.
3. **MSVC.** MSVC is the release compiler for win-x64. Does the tool's C output compile there?
4. **T1 compatibility.** Can it hand X2 a transliterated intrinsic program with correspondence maps?
5. **Cost and risk.** Can it be built and tuned within ~20 owner hours and $1–3k [inference,
   ROADMAP §3.4], on Python 3.12?
6. **Transfer to M2.** How much of what X3 learns carries over to KIR and `mithc` (Rust, DR-026)?

### 2.2 What could be verified about Exo

All rows were read by the x3 track on 2026-10-16. The GitHub pages were read on the `main` branch;
the fetch tool did not report a commit hash.

| Fact | Value | Source and tag |
|---|---|---|
| Licence | MIT. Compatible with Mithril's Apache-2.0 [R05] | PyPI JSON `info.license` = "MIT License", plus the GitHub repository page [M, x3 track] |
| Releases | 6 on PyPI: 0.0.1 (2022-02-16), 0.0.2 (2022-03-01), 0.1.2 (2024-06-05), 0.2.0 (2024-06-24), 0.2.1 (2024-08-28), **1.0.0 (2024-11-05), the latest**. No GitHub releases are listed | pypi.org/pypi/exo-lang/json; github.com/exo-lang/exo [M, x3 track] |
| Maturity label | Classifier "Development Status :: 3 - Alpha" | PyPI [M, x3 track] |
| Python | Classifiers 3.9 and 3.10. The README says "3.9 and above" and recommends 3.9 or 3.10 if a build fails. **Not tested on 3.12** here | PyPI; README [M, x3 track] |
| Dependencies | PySMT ≥ 0.9.5, z3-solver ≥ 4.13.0.0, asdl, asdl-adt, build, yapf | PyPI `requires_dist` [M, x3 track] |
| Activity | 744 stars, 58 forks, 1,262 commits on `main` | GitHub page [M, x3 track]. R05 gives "about 740 stars" |
| Documented primitives | 53, in six documents: loop 14, buffer 12, other 16, backend 4, sub-procedure 4, config 3 | `docs/primitives/*.md` [M, x3 track]; classified in §2.3 |
| Value semantics | Data values are modelled as **real numbers**, so reassociation counts as equivalence | Exo paper §4, via [R05 F2]. The docs read here do not mention floating point at all [M, x3 track] |
| `@instr` trust | "The instruction's body acts as a specification, encoding its semantics for Exo's pattern matching". Templates are arbitrary C. Nothing in the docs says the body is checked against the template | `docs/instructions.md` [M, x3 track]; [R05 F2] |
| x86 instruction library | About 59 `@instr`: about 37 f32, 17 f64, 4 ui16, plus `prefetch`. 12 are AVX-512. **No** `vpdpbusd`, `maddubs`, `madd_epi16` or `cvtph_ps` instruction, and no i8/ui8-typed instruction | `src/exo/platforms/x86.py` read through a summarising fetch tool [M, x3 track]. To be re-read at a pinned commit before any decision cites it |
| Template ≠ body, example 1 | `mm256_add_epi16`: the template is `_mm256_adds_epu16(…)`, a **saturating** unsigned add; the body is the plain `out[i] = x[i] + y[i]` | same file; decorator string quoted verbatim by the tool [M, x3 track] |
| Template ≠ body, example 2 | `mm512_fmadd_ps`: the template is `_mm512_fmadd_ps` (one rounding); the body is `C[i] += A[i] * B[i]`, which Hearth's flags compile as two roundings. Under real-number semantics `replace` may map a meaning's `acc += a*b` onto this FMA instruction. That is exactly the contraction NUMERICS bans (`NUMERICS.md:10-11`) | same file [M, x3 track] |
| Generated C on MSVC | **Unverified.** No source was found either way | — |
| Bitwise ops on `ui8` data (nibble extraction) | **Unverified.** `docs/Procedures.md` does not cover the expression language | — |

### 2.3 Exo's primitives under IEEE-exact canon.v1

Exo checks every primitive with data values modelled as real numbers. So a primitive preserves the
IEEE FP op-DAG only if it never moves a floating-point operation relative to another FP operation on
the same value chain.
Classes:
- **A**: preserves the DAG in general. The primitive restructures control or storage only.
- **C**: preserves the DAG only under a side condition that Exo does not check. It is usable only
  with x3gen's DAG check (§4.3).
- **B**: banned.

| Exo primitive (doc) | Class | Why |
|---|---|---|
| `divide_loop`, `mult_loops`, `cut_loop`, `shift_loop`, `join_loops`, `unroll_loop`, `specialize` (loop) | A | Order-preserving bijections of the iteration space, or exact duplication |
| `remove_loop`, `add_loop` (loop) | A | Idempotent blocks only. **B** with `unsafe_disable_check=True` |
| `divide_with_recompute` (loop) | C | Recomputing a reduction iteration would apply an accumulate twice. Allowed only on loops that carry no reduction |
| `reorder_loops`, `lift_scope` (loop) | C | Over the reals, Exo accepts interchanges that change the order of adds into one FP accumulator. Allowed only if no two moved loops both reduce into the same FP location (§4, P2) |
| `fission`, `fuse` (loop) | C | Same issue across statements. **B** with `unsafe_disable_checks=True` |
| `bind_expr`, `resize_dim`, `expand_dim`, `rearrange_dim`, `divide_dim`, `mult_dim`, `unroll_buffer`, `lift_alloc`, `sink_alloc`, `reuse_buffer`, `delete_buffer` (buffer) | A | Storage and naming only. `bind_expr` keeps "the precision of the bound expression" |
| `stage_mem` (buffer) | A when `accum=False`, **unverified**; **B** when `accum=True` | With `accum=True` the window is zeroed, accumulated, then added back. That turns `((x + a) + b)` into `x + (a + b)`: reassociation. Whether `accum=False` on a reduce-only block loads and stores back, or silently zero-initialises and accumulates, was not checked against Exo's source; it must be re-read at a pinned Exo commit before this row is cited |
| `rename`, `eliminate_dead_code`, `delete_pass`, `insert_pass`, `inline_window`, `fold_into_reduce` (other) | A | Naming, dead code, or `x = x + e` ↔ `x += e`, which has the same operand order |
| `inline_assign` (other) | C | `x = e; y = f(x)` → `y = f(e)` removes a rounding whenever x's buffer type is narrower than e's type (an f16 or i8 buffer). Usable only when the bound buffer's type equals the expression's type |
| `simplify` (other) | C | Exact on control expressions. Folding data expressions (`x + 0.0`, `x * 1.0`) is not IEEE-exact (03 §6.3 "never" list). Whether Exo folds data expressions is unverified |
| `reorder_stmts` (other) | C | Swapping two reduces into one FP location is accepted over the reals. **B** in that case |
| `commute_expr` (other) | C | Exact only under the NaN-order side condition (03 §6.3) |
| `merge_writes` (other) | C | `x = a; x += b` → `x = a + b` keeps the DAG. **B** for `x += a; x += b` → `x += a + b` (reassociation) |
| `split_write` (other) | C | The inverse. **B** for `x += a + b` → `x += a; x += b` |
| `left_reassociate_expr` (other) | **B** | Reassociation by definition |
| `rewrite_expr` (other) | **B** | "if the two are equivalent in the context": equivalence over the reals, a general escape hatch |
| `lift_reduce_constant` (other) | **B** | Factors a constant out of a sum: distribution |
| `make_instr` (other) | **B** | Creates an unchecked instruction assertion |
| `set_precision` (backend) | **B** | Changes FP types. Exo checks it only as "back-end consistency" |
| `set_window` (backend) | A | Annotation |
| `set_memory` (backend) | C | A memory's codegen templates are trusted, like `@instr`, which is why `replace` is banned below. Usable only for memories whose templates are validated like `isa/` entries (§5.4) |
| `parallelize_loop` (backend) | **B** for X3 | OpenMP lowering; X3 is single-thread, and a parallel reduction would race |
| `extract_subproc`, `inline` (sub-procedure) | A | Code motion between procedures |
| `replace` (sub-procedure) | **B** as shipped | Unification against an `@instr` body whose template is unchecked (§2.2 examples). Admissible only with instruction semantics validated against silicon (§5.4), which Exo lacks |
| `call_eqv` (sub-procedure) | **B** as shipped | Equivalence "due to being scheduled from the same procedure", which inherits the real-number check |
| `bind_config`, `delete_config`, `write_config` (config) | A | Control state only. Irrelevant to these kernels |

Tally [D, from the table, counting `stage_mem` as C because its class depends on a flag]: 32 A,
13 C, 8 B, for 53 in total (the draft said 34 A and 11 C before `inline_assign` and `set_memory`
were reclassified, §17). Four of the A or C rows become B when an `unsafe_*` flag is set. The C
rows show the problem: Exo would admit the very rewrites canon.v1 forbids, and a separate IEEE check
is needed either way. Every row was read from the docs without a pinned commit (§2.2), so the table
is evidence for the generator choice only, and the `exo_as_x3_generator` tombstone (§13) carries the
same caveat.

### 2.4 Decision

| Criterion | Exo 1.0.0 | x3gen (throwaway Python) |
|---|---|---|
| 1. Soundness | Its check is over the reals, so it is not evidence (§2.3). An independent DAG check is needed anyway | The DAG check is the core of the tool (§4.3), modelled on T1 (03 §6.3–6.4) |
| 2. Instructions | None of the six instructions listed in criterion 2 exists, and no instruction takes i8 or ui8 operands (§2.2). Each would be a new trusted `@instr`, and the bit-level unpack may need one too (unverified). An unchecked `@instr` on the bit-identity path is a ROADMAP kill (b) risk by construction | Instruction semantics live in a small table, each entry differentially tested against the compiled intrinsic (§5.4) |
| 3. MSVC | Unverified | The printer emits plain C11 plus intrinsics in Hearth's style (07 §7 emission rules) |
| 4. T1 input | Exo IR is internal (ASDL), with no lane-map export | The lane program *is* a transliterated intrinsic IR with lane maps (§5.2) |
| 5. Cost and risk | Alpha; last release 2024-11-05; classifiers stop at Python 3.10 | ~1.5–2.5k lines of Python [inference], standard library only. `black` is pinned only for line counting |
| 6. Transfer to M2 | Teaches Exo's IR, which M2 will not use (DR-026: `mithc` in Rust) | The IR is shaped like KIR (02 §1–2, §5 Order objects), so the primitive set and its checks transfer directly as a candidate certified space |

**Borrowed from Exo:** the primitive vocabulary (`divide_loop` ↔ `split`, `reorder_loops` ↔
`reorder`, `expand_dim` ↔ `expand`, `specialize`, `unroll_loop`) and the rule that the schedule is a
script over a fixed program. **Not borrowed:** real-number equivalence, unchecked `@instr`,
`replace` by unification.

The decision is reversible. If the Owner prefers Exo, §2.3 is the ban list Exo would need, and the
DAG checker of §4.3 must run on Exo's output in any case.

---

## 3. The meaning

### 3.1 Sources

| Element | Hearth source (b5d3f14) |
|---|---|
| Canonical matvec, Q8/Q4 | `docs/NUMERICS.md:38-48` (§3); line 45 `isum` exact int32, with Q4 `wq = nibble - 8`; line 46 `acc = acc + (float)isum * (dw[g] * dx[g])` |
| Q4 bias identity | `NUMERICS.md:50` ("an implementation may compute Σ nibble*xq − 8*sum") |
| Canonical NaN | `NUMERICS.md:56-58`; `quant.c:53-65` (`HX_CANON_NAN`, `q_canon`) |
| Batched = single | `NUMERICS.md:60-62`; `hx_quant.h:49-57` |
| No contraction | `NUMERICS.md:10-12`; `CMakeLists.txt:52-58` (`/fp:precise`; `-ffp-contract=off`) |
| Scalar definition | `quant.c:1-8` ("The scalar code here IS the numeric definition"); `mm_q8_scalar` `quant.c:388-405`; `mm_q4_scalar` `quant.c:407-427` |
| Formats | `hx_quant.h:20-28`: Q8 block 66 B (`uint16 d; int8 q[64]`); Q4 block 34 B (byte j: low nibble = element j, high nibble = element j+32; stored q+8); `hx_act_q8` 72 B (`float d; int32 sum; int8 q[64]`) |
| f16 → f32 | `q_f16`, `quant.c:16-35`, "identical to F16C vcvtph2ps (signalling NaNs come back quiet)" |
| Activation range and sum | `act_q8_scalar`, `quant.c:323-348`: clamp to ±127 at lines 339-340, `sum` at 343-346; the precondition is stated at `quant_avx2.c:11` |

### 3.2 Normative definition

Inputs (the `hx_matmul_fn` contract, `hx_quant.h:49-57`):
- W: R rows of G = n/64 blocks of format F;
- A: T × G activation blocks `hx_act_q8`;
- Y and `ldy`, and the row range r0 ≤ r1.

Let i range over 0..63. Then:

```text
wq(r,g,i) = (F = Q8) ?  W[r][g].q[i]                                       int8 storage value
          : (F = Q4) ?  (i < 32 ? (W[r][g].qs[i] & 0x0f) : (W[r][g].qs[i-32] >> 4)) - 8
xq(t,g,i) = A[t][g].q[i]          dx(t,g) = A[t][g].d          dw(r,g) = f16_to_f32(W[r][g].d)

for every t in [0, T), r in [r0, r1):                  -- independent outputs; any order
    acc_0 = +0.0f
    for g = 0, 1, ..., G-1:                            -- canonical order: Order = blocks(64, exact_i32).then(seq)
        I(r,g,t)  = sum_i wq(r,g,i) * xq(t,g,i)        -- exact integer (Z)
        p   = fmul(dw(r,g), dx(t,g))                   -- IEEE binary32, RNE   (op 1)
        q   = fmul(i2f(I(r,g,t)), p)                   -- IEEE binary32, RNE   (op 2); i2f exact, see E1
        acc_{g+1} = fadd(acc_g, q)                     -- IEEE binary32, RNE   (op 3)
    Y[t*ldy + r] = canon(acc_G)                        -- NaN -> 0x7fc00000, else identity
no other location of Y is written
```

- Operand order in op 1 is `dw · dx`, which is how all three hand variants write it:
  `quant.c:400,422`, `quant_avx2.c:263,309-310`, `quant_avx512.c:271,334`.
- Op 2 multiplies `i2f(I)` by `p`, never `(i2f(I)·dw)·dx`.
- T = 0 or r0 = r1 means nothing is stored.

### 3.3 Preconditions, exactness facts and integer views

| ID | Statement | Source | Role |
|---|---|---|---|
| P1 | xq ∈ [−127, 127] | `quant_avx2.c:11`; guaranteed by `act_q8_*` (`quant.c:339-340`); checked by `test_act_quant` (`test_quant.c:979`) | Needed by the AVX2 `vpsignb` trick: `sign(-128)` overflows |
| P2 | `A[t][g].sum = Σ_i xq(t,g,i)` | `quant.c:343-346`; `NUMERICS.md:35`; `test_quant.c:981` | Licenses the bias identities (Q4 −8·sum; AVX-512 Q8 −128·sum) |
| P3 | MXCSR is the default: RNE, FTZ = DAZ = 0 | 02 §2; Hearth never asserts it today (B1 MXCSR item) | dx can be subnormal (`test_act_quant` subnormal blocks, `test_quant.c:957`), so DAZ would change results |
| P4 | Y is disjoint from W and A, W and A are read-only, and all are readable over their extents | `hx_quant.h:45-57` | Licenses hoisting, and the footprint check |
| P5 | n % 64 = 0 | `hx_row_bytes`, `quant.c:86-87` | G is an integer |
| E1 | \|I\| ≤ 64·8·127 = **65,024** (Q4); \|I\| ≤ 64·128·127 = **1,040,384** (Q8, **storage range** [−128, 127]); both < 2^24 = 16,777,216 [D] | Q8 raw-byte weights are fed by `test_nonfinite` (`test_quant.c:1238`) | `i2f` is exact, so its rounding mode is irrelevant |
| E2 | f16→f32 is exact; `vcvtph2ps` = `q_f16` on all 65,536 inputs | `quant.c:16`; `test_half_all_values`, `test_quant.c:1000-1024` | "Exact widening" row of 03 §6.3 |

**Finding for 02-compute §7.2.** Its table bounds the Q8 block sum with 64·127·127 = 1,032,256, the
quantiser's range. The kernel slot also accepts raw int8 codes, and `test_nonfinite` supplies −128,
so the obligation should use 64·128·127 = 1,040,384 [D]. Both bounds are below 2^24, so exactness is
unaffected, but a T2 obligation stated on the quantiser range would be unsound for raw inputs.
Proposed in §15.

Inputs dw and dx may be any binary32, including NaN, ±inf and subnormals
(`test_quant.c:1239-1243` writes NaN, inf and subnormal block scales). The meaning handles them by
IEEE rules plus `canon` at the sink.

### 3.4 The FP-DAG per output (checker form)

Per output (t, r), with G = n/64, the DAG is a chain of 3G IEEE operations plus one `canon`. For the
benchmark shape, n = 4096 and G = 64, so that is 192 operations per output [D]. Its canonical
serialisation, which both the checker (§4.3) and the T1 export use:

```text
Y(t,r) = canon( F(G) )      F(0) = +0.0f
F(g+1) = add( F(g), mul( i2f(I(r,g,t)), mul( h2f(Wd(r,g)), Ad(t,g) ) ) )
leaves:  Wd(r,g) = bits of W[r][g].d (u16)   Ad(t,g) = A[t][g].d (f32)   I(r,g,t) = exact-int leaf
```

`I(r,g,t)` is an opaque exact-integer leaf in the FP DAG. Its value is proved separately as a
polynomial identity over Z, with interval side conditions (§4.3 C3).

### 3.5 Meaning source, as x3gen will hold it (sketch; not Mithril syntax)

```python
# x3gen/hearth/meaning.py: meaning text M (counted and reported, not schedule text)
BlockQ4 = fmt("BlockQ4", size=34, d=f16, q=nibbles(64, offset=8, hi_at=32))   # hx_quant.h:23
BlockQ8 = fmt("BlockQ8", size=66, d=f16, q=i8(64))                           # hx_quant.h:22
ActQ8 = fmt("ActQ8", size=72, d=f32, sum=i32, q=i8(64, range=(-127, 127)))   # hx_quant.h:24, P1

@kernel(slot="hx_matmul_fn", requires=["A.sum == sum(A.q)", "mxcsr == default"])  # P2, P3
def q_matmul(F, W: F[R, G], A: ActQ8[T, G], Y: out_f32[T * ldy], r0, r1):
    for t in outputs(T):
        for r in outputs(r0, r1):
            acc = f32(+0.0)
            for g in seq(G):
                isum = exact_sum(W[r, g].q.int(i) * A[t, g].q[i] for i in range(64))
                acc = acc + f32(isum) * (W[r, g].d.to_f32() * A[t, g].d)
            Y[t * ldy + r] = canon_nan(acc)
```

The meaning is frozen, with its hash, at the end of week 1, after an independent reviewer has
checked it against `NUMERICS.md` §3 and `quant.c:388-427`. A *meaning differential* must also pass:
x3gen's interpreter runs the meaning on the kernel corpus of §7 step 6 and must equal the hand scalar
kernel byte for byte. After the freeze, the meaning may change only to fix a transcription error that
the differential exposes. Every such change is logged, and none may be made to ease scheduling.

### 3.6 The hand triplets realise this meaning

This table is the evidence that a DAG-preserving generator can, in principle, reach the hand
kernels.

| Element | Scalar | AVX2 | AVX-512 |
|---|---|---|---|
| Lanes | none | lane i = row r+i, 8 rows (`quant_avx2.c:225-226`) | lane i = row r+i, 16 rows (`quant_avx512.c:250-252`) |
| Row tail | n/a | dead lanes repeat the last row; masked store (`:237`, `:266-267`) | `qtile4`, one row per 128-bit lane, masked store (`:308-340`) |
| Integer sum | direct (`quant.c:399`, `:419-420`) | Q4: `maddubs`/`madd`, −8·sum (`:252`, `:262`); Q8: `abs`/`sign` + `maddubs` (`:256-258`) | `vpdpbusd` on unsigned codes (Q4 nibbles; Q8 xor 0x80), −bias·sum (`:189-221`, `:236-241`, `:270`) |
| FP epilogue | `acc + (float)isum * (dw * dx)` (`quant.c:400`, `:422`) | the same 3 ops (`:263`, `:309-310`) | the same 3 ops (`:271`, `:334`) |
| T > 1 | per token | 8 tokens per pass; unpacked weights reused (`:270-312`) | 8 tokens per pass (`TCH`, `:21`, `:291-305`) |
| Canon at store | `q_canon` (`quant.c:402`, `:424`) | `canon8` (`:27-29`, `:265`) | `canon16`/`canon4` (`:26-32`, `:288`, `:304`, `:338`) |

Every hand variant keeps each output's chain in g order, starting from +0.0, with exactly the ops of
§3.2. All the freedom is in lanes, integer arithmetic, loads and loop structure. This is the "central
rule" of 02 §1, observed in Hearth's own code.

---

## 4. The schedule primitive set P_X3

### 4.1 Licences

| Licence | Meaning | Rewrites allowed |
|---|---|---|
| `exact` | The per-output FP-DAG of §3.4 is unchanged, node for node | Restructuring of control, storage and lanes. Commutation only under the NaN-order condition |
| `int_assoc` | Only exact-integer leaves change form | Any integer evaluation whose polynomial over Z equals Σ wq·xq, with no saturation and no wrap (interval-proved) |
| `timing_only` | No architectural data effect | Prefetch hints only |

These are the three licences of 02 §8.1, restricted to what X3 needs. X3's rewrite list is a subset
of T1's audited list (03 §6.3):
- commutation, under the NaN-order condition;
- exact conversion (int → f32 with \|v\| ≤ 2^24);
- exact widening (f16 → f32);
- data movement;
- masking;
- the integer ring.

Nothing outside that list is used, so if X2 is ready, T1 needs no new rule for X3's output.

### 4.2 The primitives

Each primitive is checked twice. First, its own precondition is checked when it is applied. Second,
the global checks C1–C4 of §4.3 run on the final lane program. The second check is the one that
carries soundness ("validate the output, not each rewrite", 03 §6.3). A primitive whose own check
has a bug is still caught there.

| # | Primitive (x3gen) | Licence | Precondition | Why the FP-DAG per output is unchanged | Check |
|---|---|---|---|---|---|
| P1 | `split(loop, k, tail=cut\|guard)` | exact | k a positive constant | `i = k·io + ii` is an order-preserving bijection: the lexicographic order of (io, ii) is the order of i. Every chain sees the same g sequence | Affine bijection check, symbolic; tail covers `N mod k` exactly once |
| P2 | `reorder(L1, L2)`, interchange | exact | **Only loops that carry no FP dependence move past each other.** A loop is *FP-carried* if its index appears in the affine map from loop indices to g (so after a P1 split of g, both g_o and g_i are FP-carried). **No interchange is allowed between two FP-carried loops**, and an FP-carried loop never moves past another FP-carried loop of the same nest. Every FP accumulator in the moved body is private (expanded, P3) to each iteration of any loop moved outside its initialisation | Interchange never reverses a loop. Each chain (t, r) still sees g = 0..G−1 in increasing order. Distinct chains share no FP value, so their interleaving cannot be observed | Dependence analysis: the loop-carried FP set must be {acc[t,r] via the FP-carried loops}, and no accumulator instance may be shared across the moved loops' iterations. Backstopped by C1's per-chain visit-order check (§4.3), which does not trust this precondition |
| P3 | `expand(acc, over=loop)` | exact | The scalar is re-initialised in every iteration of `loop` | Storage only: one location per chain | Liveness check |
| P4 | `vectorize(loop, lanes, kind="outputs")` | exact | The loop ranges over independent outputs (r or t), and the lane count is fixed | Lanes never meet in an FP operation. Each lane executes its own scalar chain, and the lane map records lane ↔ output | No FP operation reads two lanes that hold different outputs (no horizontal FP op, no FP shuffle feeding an FP op); the lane map is emitted |
| P5 | `lower_isum(using, layout, signed=bias\|sign_transfer)` | int_assoc | The target is an `exact_sum` leaf; every instruction used has validated semantics (§5.4); P1 and P2 hold | Only the integer leaf I(r,g,t) changes form. Its value over Z is unchanged, and i2f of it is exact by E1 | C3, two layers (§4.3): the bit-vector layer proves each integer-consumer input lane equal to a named term (nibble, q+128, \|w\|, x·sgn(w)) by per-lane exhaustive enumeration; the ring layer proves the normal form equals Σ wq·xq. Interval proofs of no saturation (`vpmaddubsw` pair ≤ 3,810 for Q4 and ≤ 32,512 for Q8; Q4 low+high int16 sum ≤ 7,620 [D]) and no int32 wrap (`vpdpbusd` partials ≤ 64·255·127 = 2,072,640 for Q8, unsigned + bias [D]) |
| P6 | `tail(loop, narrow(w)\|mask\|dup_last, store=mask)` | exact | The tail covers `(r1−r0) mod lanes` rows. Dead lanes are never stored and never meet a live lane in an FP op. Every load is in bounds | Live lanes compute their own chain. Dead-lane values cannot be observed | C4, value-carrying: every store writes, in each live lane, canon(F_{t,r}(G)) to the address t·ldy + r recomputed from the store's own symbolic address and mask, for every tail width; every load lies in a declared extent. Dead-lane isolation as in P4 |
| P7 | `unroll(loop, u\|full)` | exact | Constant trip count, or a remainder loop | u consecutive iterations composed in order (03 §6.4, "unroll by u") | C1 on the unrolled body against u meaning iterations |
| P8 | `specialize(pred)` | exact | pred ∈ {`T == 1`} plus the tail predicates of P6. **No specialisation on n, R, r0, r1 or data values** | Each copy is the same program on a sub-domain | C1–C4 run on every copy |
| P9 | `hoist(op, out_of=loop)` | exact | op is pure: a load of read-only input (P4), an integer op, an exact conversion, or an IEEE op whose operands are invariant in `loop` (under P3, the same op on the same operands gives the same bits). It does not cross a store that may alias | The same node is computed once and shared (hash-consed). The DAG is identical | Invariance analysis plus the read-only and no-alias facts |
| P10 | `block(r by L, t by B)`, register blocking | exact | A composite of P1, P2, P3, P4 and P7 | As its components | As its components, plus C1–C4 |
| P11 | `prefetch(buf, ahead=k, unit, hint)` | timing_only | Inserts only `_mm_prefetch`: no destination register, no store; address arithmetic is integer | `PREFETCHh` has no architectural data result | Removing every prefetch op yields the unprefetched lane program exactly (IR diff) |
| P12 | `map_fp(op → instr)` | exact | The instruction's table semantics is the same IEEE op, lane-wise, RNE under P3 (`vaddps`, `vmulps`, `vcvtdq2ps`, `vcvtph2ps`) | One-to-one op replacement | The table entry equals the lifted scalar op; the entry is validated against silicon (§5.4) |
| P13 | `canon_store(lowering)` | exact | lowering ∈ {`cmp_unord` + `mask_mov`, `cmpunord` + `blendv`, scalar branch}. **Lifting rule:** before P15's dataflow check and C1 run, a lowering is lifted to one `canon(v)` node only if its selector is `cmp_unord(v, v)` on the same SSA value v that it selects from, and its replacement operand is the constant 0x7fc00000 in every lane. Any other `blendv`, `mask_mov` or branch on a comparison is not canon; it is a NaN-observing consumer (03 §6.3) | `canon` at the sink, exactly once per output | Each lowering is checked exhaustively over all 2^32 binary32 inputs against `q_canon` (daytime, compiled C). C1 requires exactly one lifted canon on every path from an accumulator's final value to its store |
| P14 | `load_scales(pack=gpr64, convert)` | exact | Integer packing of the f16 bit patterns, then an exact widening | Data movement plus exact widening (03 §6.3 rows) | Symbolic bit identity of each packed lane with its source `d` field |
| P15 | `commute(op)` | exact, with side condition | No NaN-observing consumer between op and `canon` (03 §6.3). For this meaning that holds: the chain has no MAX/MIN, no bitwise op and no sign-driven select before `canon` | Exact for every non-NaN value. NaN-ness is preserved and the payload is erased at the sink | Dataflow check on the DAG **after** P13's lifting rule, so a valid canon lowering is the sink and is not itself flagged; an unlifted select is flagged |

**"Reorder of non-FP-dependent loops"**, as the task phrases it, is P2. A loop is *FP-dependent* if
it carries an FP value from one iteration to the next. In this meaning only g is, and after a P1
split so are all the pieces of g (P2's definition). Loops t, r and i (i being exact integer) may be
split, interchanged, vectorised and unrolled freely, subject to P2's privacy condition. Loop g may be
split (P1) or unrolled (P7), but its pieces are never interchanged, reversed or reordered, and g is
never split into accumulators (B1).

### 4.3 The global checks (on the lane program)

The lane program (§5.2) is what gets printed as C. It is checked in four ways. **No check trusts
anything the generator asserts.** Lane maps, loop correspondences and accumulator names are
mandatory hints: every FP operation and every store must carry one, a missing hint is "unknown",
and a wrong hint can only cause rejection, never acceptance (03 §6.3, "correspondence maps are
untrusted hints"). Identities are recomputed from symbolic addresses.

**Leaf naming (used by C1, C3 and C4).** Every value loaded from an input is named by the symbolic
address of its load, with rb = G·bs and bs ∈ {34, 66} (`hx_quant.h:20-28`):
- Wd(r,g) is the u16 at W + r·rb + g·bs; weight byte j of block (r,g) is the u8 at
  W + r·rb + g·bs + 2 + j;
- Ad(t,g) is the f32 at A + (t·G + g)·72; its sum is the i32 at offset 4 and activation byte i is
  the i8 at offset 8 + i.

A lane holding Wd(r,g) is therefore "row r" because of where it was loaded from, not because a lane
map says so.

- **C1. Per-chain FP-DAG match.**
  - **Visit order.** For each chain (t, r), the sequence of g values whose terms are added into its
    accumulator, across every loop nest, peeled or remainder segment and P8 copy, must be exactly
    0, 1, …, G−1. The implemented sufficient check: (i) every FP-carried loop index (P2) enters the
    map to g with a positive coefficient; (ii) the nest order of the FP-carried loops is the
    lexicographic order of that map, so the outer index has the larger stride; (iii) the segments
    (main, remainder, peeled) cover [0, G) exactly once and are concatenated in increasing g,
    checked on their symbolic bounds; (iv) within an unrolled body the u terms are added in
    increasing g (03 §6.4, "unroll by u" and "peeling" rows). Anything the check cannot establish is
    "unknown", which is rejection.
  - **One-step match.** For each FP-carried body (u iterations if unrolled), the checker
    symbolically executes it with a symbolic accumulator per live lane and requires
    `acc_out[k] = add(acc_in[k], mul(i2f(I_k), mul(h2f(Wd(r_k,g)), Ad(t_k,g))))` for every live lane
    k, where (t_k, r_k) is **derived from the load addresses** of the leaves that reach lane k. The
    lane map is compared with the derived identity, and a mismatch is a rejection.
  - **Accumulator injectivity.** The map from chain (t, r) to (accumulator storage location or
    register, lane) must be one-to-one over every iteration of every loop that is not FP-carried.
    Two chains never share an accumulator instance.
  - **Initial value and sink.** The initial value is the bit pattern 0x00000000 (+0.0f) in every
    live lane; −0.0 is rejected. Every path from an accumulator's final value to its store passes
    through exactly one canon node (after P13's lifting rule), in every P8 copy and every tail path,
    with only data movement between the last add and the canon.
  - This is the lockstep rule of 03 §6.4 at generator level. Equality is structural over hash-consed
    terms, up to P15's commutation.
- **C2. Licence audit.** Every node in the final program carries the provenance id of the primitive
  application that created it. A lint rejects any node created outside P1–P15, and any primitive
  call with an unsafe flag.
- **C3. Integer identity, in two layers.**
  - **(a) Bit-vector layer.** Loaded bytes are 8-bit vectors named as above. `and`, `or`, `xor`,
    `andnot`, `srli`/`slli` (epi16/32/64), `abs_epi8`, `sign_epi8`, shuffles, unpacks, permutes,
    inserts, extracts, packs and broadcasts are evaluated lane by lane with their bit-exact `isa/`
    semantics (validated, §5.4). At every input of an integer-arithmetic consumer (`maddubs`,
    `madd`, `dpbusd`, `add`/`sub`/`mullo` epi16/epi32, scalar integer multiply and add), each lane
    must be proved equal to one named term: a Q8 weight byte; the low or high nibble of Q4 byte j;
    q + 128 (the xor bias); \|w\| as u8; x·sgn(w) as s8; an activation byte; or a constant. The proof
    is exhaustive enumeration of that lane's inputs under the declared ranges, which is at most 2^16
    cases: the two source bytes of a 16-bit shift, or the (w, x) byte pair of `sign_epi8`, with
    x ∈ [−127, 127] (P1) and w ∈ [−128, 127]. Example: after `srli_epi16(v, 4)`, the low byte of a
    word holds (b_lo >> 4) | ((b_hi & 0x0f) << 4); only the following `& 0x0f` makes it the high
    nibble of b_lo, and only enumeration over (b_lo, b_hi) shows it.
  - **(b) Ring layer.** With the leaves named by (a), each `I` is normalised as a polynomial over Z.
    One lemma is used: abs_u8(w)·sign_s8(x, w) = w·x for w ∈ [−128, 127] and x ∈ [−127, 127],
    proved by enumerating all 2^16 cases and listed in the report as a checker lemma. The bias
    identities (Q4 −8·sum, AVX-512 −bias·sum) use P2, `sum = Σ xq`. Saturating and wrapping integer
    ops are replaced by exact ops only after interval arithmetic proves that they neither saturate
    nor wrap; otherwise the check rejects. The normal form must equal Σ wq·xq: at most 64 bilinear
    terms plus linear bias terms. The check is deterministic, not randomised.
  - No multi-instruction idiom is trusted anywhere in C3 (§5.1); each step is a single validated
    entry plus enumeration or ring algebra.
- **C4. Value-carrying footprint** (03 §6.3, footprint item 1).
  - **Stores.** For every store, its own symbolic address and mask determine, for each live lane k,
    an output location t_k·ldy + r_k. The value written there must be canon(F_{t_k,r_k}(G)), the
    chain C1 matched for exactly that (t_k, r_k). The stored locations must equal
    {t·ldy + r : t < T, r0 ≤ r < r1}, each written exactly once.
  - **Loads** stay inside W's rows [r0, r1) (with `dup_last` clamping), A's T·G blocks, or the frame.
  - **Every runtime shape.** C4 runs for every row-tail width nr ∈ 1..lanes, every token-tail width
    tn ∈ 1..TCH, and the degenerate cases T = 0 and r0 = r1, where no load or store may execute. A
    P9-hoisted load out of a loop that may run zero times must therefore be guarded.
  - Checked on symbolic addresses with interval arithmetic.

A checker "unknown" is a rejection (02 §1).

### 4.4 Banned in X3

Each item below is either rejected by C1–C4 or refused by the lint before checking. Any of them in a
gate variant makes the variant inadmissible, and its use to reach bit-identity is kill condition (b)
(§11).

| ID | Banned | Why | Exo counterpart |
|---|---|---|---|
| B1 | FP reassociation: split accumulators over g, a tree over g, `left_reassociate`, partial sums | Changes the association (02 §8.2; NUMERICS §3) | `left_reassociate_expr`, `stage_mem(accum=True)`, `reorder_stmts`/`fuse`/`fission` over one FP location |
| B2 | FMA contraction, or any FMA-class instruction in a variant's object | NUMERICS:10-11 | `replace` with `mm512_fmadd_ps` |
| B3 | Distribution or factoring, for example `(i2f(I)·dw)·dx` | Changes the association of op 2 | `lift_reduce_constant` |
| B4 | Additive-identity edits: dropping `acc_0 = +0.0`, or `x + 0.0 → x` | `+0.0 + (−0.0) = +0.0`, so the sign of a zero result changes (03 §6.3 "never" list) | `simplify` on data |
| B5 | Precision changes: double accumulation, f16 arithmetic | Not the meaning's ops | `set_precision` |
| B6 | Approximation instructions (RCP*, RSQRT*) or non-default rounding | Not exact | — |
| B7 | MXCSR or FP-environment writes | Violates P3 | — |
| B8 | Cross-lane FP operations between different outputs | Reassociation across outputs | — |
| B9 | Escape hatches: verbatim C or intrinsic text in a schedule, an unchecked instruction template, `unsafe_*` flags, editing generated C by hand (07 §7) | Unchecked | `make_instr`, `rewrite_expr`, `call_eqv` |
| B10 | Threads (`parallel`) | X3 is single-thread. Hearth's pool splits rows outside the kernel | `parallelize_loop` |
| B11 | Extra NaN handling inside the chain | Not needed; it keeps C1 simple | — |
| B12 | Specialising on n, R, r0, r1 or data values | Overfits the benchmark shape; anti-gaming | `specialize` on shape |

### 4.5 Checker precondition: planted bad schedules

The checker is judged before it judges the generator, as `mithi` is in X1. Before T0 (§10), x3gen's
checks must reject **100% of a planted suite of at least 28 DAG-changing or footprint-violating
lane programs** [target] (items 1–28 below; more may be added, none removed), and must **accept
100% of the correct ones** [target]. The accept half is concrete: lane-program transliterations of
all six hand kernels at b5d3f14, covering the T == 1 and T > 1 paths, the AVX2 `dup_last` row tail,
the AVX-512 `qtile4` tail and the token tail tn < TCH, written once, reviewed against the C source,
and hashed. A checker that rejects a hand kernel is incomplete, and is fixed before T0; otherwise a
correct generator could be failed by the checker and counted toward kill (a). The reject suite:
1. split accumulator over g (two partial accumulators);
2. FMA on `acc + q`;
3. `(i2f(I)·dw)·dx`;
4. `acc = q_0` with no +0.0 initial value;
5. a pairwise tree over g;
6. `dw·dx` computed in double, then rounded;
7. accumulation in double;
8. Q8 `maddubs` on biased u = q+128 (a pair reaches 2·255·127 = 64,770 > 32,767 [D], so it
   saturates);
9. Q4 bias −7·sum instead of −8·sum;
10. rows vectorised with a horizontal FP sum over g;
11. `canon` omitted;
12. g unrolled by 2 with `acc + (q0 + q1)`;
13. a prefetch replaced by a load-and-store;
14. llama.cpp's Q4_0 nibble order (high nibble at j+16), a false friend (02 §7.1);
15. a tail that stores a dead lane one past `r1`, the class of Hearth's three one-past SIMD writes
    (T02 [R11]);
16. g split by k, then g_o and g_i interchanged, with one accumulator (a pure permutation of the
    adds: no split accumulator, no tree, no FMA);
17. g reversed;
18. the remainder segment of a split g executed before the main segment;
19. a T-blocked accumulator array indexed `acc[t mod 4]` with TCH = 8 (two chains share storage);
20. Q4 `srli_epi16(v, 4)` without the following `& 0x0f`;
21. Q8 `sign_epi8` with its operands swapped;
22. x = −128 admitted in the declared activation range (breaks P1 and the sign lemma);
23. canon on the T == 1 path only, missing on the T > 1 path;
24. canon applied before the final add of the chain;
25. acc_0 = `set1(−0.0)`, which differs from +0.0 whenever I = 0 and dw·dx < 0;
26. lane k's result stored to row r + lanes − 1 − k (a correct chain at the wrong address);
27. the AVX-512 quad order (rows j, j+4, j+8, j+12) stored without the `red_quads` reorder;
28. a P9-hoisted A load executed when T = 0.

Items 16–28 were added after review (§17): 16–19 target C1's visit-order and injectivity checks,
20–22 C3's bit-vector layer, 23–25 the canon and initial-value rules, and 26–28 C4's
value-carrying store check.

The suite is written by the same model family as x3gen, and the review log says so (m0/README
independence rule).

### 4.6 Schedule sketches (illustrative; counted text will differ)

```python
# x3gen/hearth/schedules/avx512.py: schedule text S (every non-blank, non-comment line counts, §9)
def schedule(k):
    k = k.specialize(T=1)
    for p in k.paths():
        p.vectorize("r", 16, kind="outputs", tail=Tail.narrow(4, store="mask"))
        p.lower_isum(using="vpdpbusd", group=4, signed="bias")
        p.load_scales(pack="gpr64", convert="vcvtph2ps")
        p.prefetch("W", ahead=2, unit="g")
    k.path(T=">1").block("t", 8, expand="acc").hoist(["W.q", "W.d"], out_of="t")
    return k
```

The AVX2 schedule has the same shape, with `vectorize("r", 8, …, tail=Tail.dup_last(store="mask"))`
and `lower_isum(using=("vpmaddubsw", "vpmaddwd"), signed={"q4": "bias", "q8": "sign_transfer"})`.
The scalar schedule is the identity. On these sketches, S would be about 25–35 lines [inference],
against a cap of 90 (§9). Tuning will add lines.

---

## 5. x3gen architecture

### 5.1 Layout

All of it lives in `experiments/x3-generator/x3gen/`. It is pure-Python standard library, run on the
desktop's Python version, which is recorded. The laptop has Python 3.12.10 [M, x3 track].

| Path | Contents | Counted as (§9) | Trust |
|---|---|---|---|
| `core/ir.py`, `core/meaning.py` | Loop-nest IR with typed values; f32 chains with `Order`; exact-int leaves with intervals; formats | library L | untrusted, tested |
| `core/prims.py` | P1–P15 with their precondition checks | library L | untrusted; C1–C4 carry soundness |
| `core/lower.py` | Lowering to the lane program (§5.2) | library L | untrusted |
| `core/check.py` | C1–C4: symbolic executor, polynomial normaliser, interval arithmetic, provenance lint | library L | **trusted within X3**; backstopped by §7 and by T1 if X2 is ready |
| `core/printer.py` | Lane program → C11 + intrinsics, one statement per line, provenance header, LF, deterministic (07 §7 rules 1–4, plus rule 5 below); at most 300 lines [target] | library L | **trusted within X3**; small, reviewed; tested differentially (§5.4) |
| `core/interp.py` | Concrete interpreter of meaning and lane program, with binary32 emulated as specified below | library L | test oracle |
| `isa/{scalar,avx2,avx512}.py` | One entry per intrinsic: concrete semantics, symbolic semantics, C spelling. No multi-instruction idioms, with one named exception, `scalar.h2f_bits` (below) | instruction library I | each entry validated (§5.4) |
| `hearth/meaning.py` | §3.5 | meaning M | reviewed |
| `hearth/schedules/*.py` and any other file under `hearth/` | the schedules | **schedule text S** | — |
| `tests/` | unit tests, the planted suite (§4.5), the hand-kernel transliterations, interpreter differentials | not counted | — |

**Printer rule 5: one floating-point operation per C full-expression.** Every FP arithmetic operator
or FP intrinsic result is assigned to a named local, and no generated C full-expression, scalar or
vector, contains more than one FP arithmetic operator or FP intrinsic call. The printer re-parses its
own output and rejects it if any full-expression has two. Reason, measured by X0 on the desktop
(`experiments/x0-census/TOOLCHAINS.md` §4–§6, [M, X0 track, 2026-10-16]): clang-cl 23.1.3 maps
Hearth's `/fp:precise` to `-ffp-contract=on`, maps `/arch:AVX2` to `-target-cpu haswell` (which has
FMA), and fused a scalar `a*b+c` into `vfmadd213ss` under Hearth's exact `quant_avx512.c` flags. Under
`-ffp-contract=on` Clang fuses only within one source expression [inference, from the Clang
option's documented meaning; not re-read here], so rule 5 removes the opportunity in any scalar tail,
scalar canon branch or h2f path of a SIMD translation unit. The object scan (§7 step 3) remains the
backstop.

**Binary32 emulation in `interp.py`.** The standard library has no binary32 arithmetic, and the
obvious route fails: on the laptop's Python 3.12.10, `struct.pack('<f', x)` raises `OverflowError`
for 1e39 and for 3.4028235677973366e38 (the RNE tie to 2^128), and quiets the signalling NaN
0x7fa00001 to 0x7fe00001 [M, x3 reviser, 2026-10-16; subnormal ties rounded to even correctly in the
same probe]. The interpreter therefore uses one function, `rne_f32(x: float) -> int` (bits):
- NaN in, NaN out (NaN-ness only; payloads are erased by canon at every sink);
- \|x\| ≥ 3.4028235677973366e38, the midpoint between the largest finite binary32 and 2^128, rounds
  to ±inf (ties go to the even neighbour, which is 2^128, so the midpoint itself is inf);
- otherwise `struct.unpack('<I', struct.pack('<f', x))`, which rounds to nearest even, subnormals
  included.

`+` and `×` are computed in double and then rounded once by `rne_f32`. A product of two binary32
values is exact in double (24 + 24 ≤ 53 bits), so that is a single rounding. For sums, double
rounding through binary64 is innocuous because 53 ≥ 2·24 + 2 [inference: the condition is from
memory of Figueroa, "When is double rounding innocuous?", ACM SIGNUM Newsletter, 1995; the citation
was not re-checked]. `rne_f32` and the interpreter's `add`/`mul` are tested against compiled C on
edge sets (±0, ±min subnormal, subnormal ties, max finite, the overflow midpoint ± 1 ulp of double,
±inf, quiet and signalling NaN) and on 10^6 random pairs [target] before any differential uses them.

**The one multi-op `isa/` entry: `scalar.h2f_bits`.** The scalar variant needs f16 → f32, and the
x86-64 baseline has no single instruction for it (F16C is not assumed in `quant.c`'s translation
unit). Hearth's `q_f16` is `HX_INLINE static` inside `quant.c` (`quant.c:16-35`), so generated code
cannot call it, and the extern `hx_f16_to_f32` (`hx_platform.h:155`, `platform_common.inc:19`)
would add an out-of-line call per (row, block) that the hand scalar kernel does not pay. The scalar
schedule therefore uses a printed `static inline` bit routine transcribed from `q_f16`, emitted from
one named entry, `scalar.h2f_bits`. It is the only exception to the single-intrinsic lint (§9.1). It
is validated as exact widening by exhaustive comparison over all 65,536 inputs, **bit for bit**,
against `_mm_cvtph_ps` (F16C) and against `hx_f16_to_f32`. `q_f16` is documented as identical to
`vcvtph2ps` including NaN quieting (`quant.c:15`); `test_half_all_values` (`test_quant.c:1000`)
checks scalar against the SIMD ISAs over all 65,536 values through the F16 matmul slot, where canon
erases NaN payloads, so the bit-for-bit NaN comparison here is stricter than Hearth's own test. It is
counted under I, not S, and listed by name in the report. If tuning shows a cost, that is a
gap-attribution item, not a reason to change the form.

### 5.2 The lane program

The lane program is a structured SSA program: loops, `if`, and straight-line blocks of intrinsic
calls over typed vector values (`m512`, `m512i`, `m256`, `m256i`, `m128`, `m128i`, GPR integers).
Every operation names exactly one `isa/` entry and carries the provenance id of the primitive that
made it. Every FP operation and every store carries a lane map, which is mandatory but untrusted: a
missing map is "unknown" (rejection), and C1–C4 recompute identities from load and store addresses
(§4.3). It is:
1. the object C1–C4 check;
2. what the printer prints, one operation per line, in Hearth's intrinsic style (07 §7 rule 4);
3. the **T1 export**: a JSON file `x3_q_<isa>.lanes.json` with the lane map, the register-to-value
   map and the loop correspondence. It is the "transliterated intrinsic-level IR with lane
   correspondence maps" that X2 consumes ([ROADMAP §3.3](../../docs/ROADMAP.md#33-x2-t1-spike-on-transliterated-hearth-intrinsics-weeks-05-verdict-in-week-6)).
   Its format will be agreed with the X2 track. Until then x3gen writes its own and maintains an
   adapter.

The printer emits straight-line SSA locals, never arrays of vectors indexed in loops. This is a
deliberate code-shape choice for MSVC, whose handling of `__m512i u[16]`-style arrays the hand code
relies on (`quant_avx512.c:284`). Whether it helps or hurts MSVC is an empirical question, settled
during tuning.

### 5.3 Generated files

The generated files are `x3_q_scalar.c`, `x3_q_avx2.c`, `x3_q_avx512.c` and `x3_gen.h`. Each `.c`
defines `hx_x3_mm_q8_<isa>` and `hx_x3_mm_q4_<isa>` with the `hx_matmul_fn` signature
(`hx_quant.h:56-57`). The SIMD files are guarded by `#if defined(HX_ARCH_X86_64)`, like the hand
files.

The provenance header records:
- the x3gen commit;
- the meaning hash;
- the schedule hash;
- the target;
- the line "do not edit; regenerate with x3gen".

The generated C is the printer's output byte for byte. Its SHA-256 is recorded, and any hand edit
makes the variant inadmissible (B9; 07 §7).

### 5.4 Validating instruction semantics (daytime, desktop)

Each `isa/` entry is checked against the compiled intrinsic, built with the release flags of both
compilers:
- **≥ 10^6 random vectors** [target] per entry;
- **structured edges**: per-lane extremes (0, ±1, ±127, −128, 255, 0x80), all-ones and all-zero
  masks, NaN, ±inf, ±0 and subnormals for FP entries;
- **exhaustive per-lane domains where the lane function has ≤ 2^32 inputs** [target]. This covers
  the `vpmaddubsw` pair, `vpsignb`, `vpabsb`, `vcvtph2ps` (2^16) and the canon lowerings (2^32).

The printer is tested by differential execution. On ≥ 1,000 seeded small shapes [target]
(rows 1–33, T 1–9, n ∈ {64, 128, 320}), `interp.py` runs the lane program and the compiled C runs the
printed program. They must agree byte for byte.

Where X2's fuzzed semantics table has an entry for the same iclass, the two must agree; any
disagreement blocks the use of that entry. These runs are short and run in daytime, never inside a
quiet window (DR-023).

---

## 6. Linking generated C into a scratch Hearth through `hx_kernels`

**Scratch tree.**
- It is a copy of Hearth `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220` in the desktop's data directory,
  outside the repository and outside synced folders (DR-019).
- The Hearth blob ids are:
  - `quant.c` e9549694…;
  - `quant_avx2.c` a2004d22…;
  - `quant_avx512.c` 9c7586b1…;
  - `hx_quant.h` df7e75e3…;
  - `test_quant.c` b4e97853…;
  - `NUMERICS.md` 7c558db5…;
  - `test_golden_invariants.py` a1acdbaf….

  [M, x3 track, `git rev-parse b5d3f14:<path>`]
- One patch, `x3-seam.patch`, is applied and its SHA-256 recorded. It touches only the lines below
  and leaves every test file unchanged.

```c
/* quant.c, around the scalar table (lines 429-433); the same pattern is used in
   quant_avx2.c:341-345 and quant_avx512.c:365-369 */
#ifdef HEARTH_X3_GEN
#  include "x3_gen.h"
#  define X3_Q8 hx_x3_mm_q8_scalar
#  define X3_Q4 hx_x3_mm_q4_scalar
#else
#  define X3_Q8 mm_q8_scalar
#  define X3_Q4 mm_q4_scalar
#endif
const hx_kernels hx_kernels_scalar = {
    HEARTH_ISA_SCALAR,
    {mm_f32_scalar, mm_f16_scalar, mm_bf16_scalar, X3_Q8, X3_Q4, NULL, NULL},
    act_q8_scalar,
};
```

```cmake
# CMakeLists.txt, before add_library(hearth_core ...) at line 48
option(HEARTH_X3_GEN "X3 scratch only: dispatch generated Q4/Q8 kernels" OFF)
set(X3_GEN_DIR "" CACHE PATH "x3gen output directory")
if(HEARTH_X3_GEN)
  list(APPEND CORE_SOURCES ${X3_GEN_DIR}/x3_q_scalar.c)        # no ISA flags, like quant.c
  if(X86)
    list(APPEND CORE_SOURCES ${X3_GEN_DIR}/x3_q_avx2.c ${X3_GEN_DIR}/x3_q_avx512.c)
    if(MSVC)   # identical to lines 40-41
      set_source_files_properties(${X3_GEN_DIR}/x3_q_avx2.c PROPERTIES COMPILE_OPTIONS "/arch:AVX2")
      set_source_files_properties(${X3_GEN_DIR}/x3_q_avx512.c PROPERTIES COMPILE_OPTIONS "/arch:AVX512")
    else()     # identical to lines 43-44
      set_source_files_properties(${X3_GEN_DIR}/x3_q_avx2.c PROPERTIES COMPILE_OPTIONS "-mavx2;-mfma;-mf16c")
      set_source_files_properties(${X3_GEN_DIR}/x3_q_avx512.c PROPERTIES COMPILE_OPTIONS
        "-mavx512f;-mavx512bw;-mavx512vl;-mavx512vnni;-mavx2;-mfma;-mf16c")
    endif()
  endif()
endif()
# after add_library: target_compile_definitions(hearth_core PRIVATE $<$<BOOL:${HEARTH_X3_GEN}>:HEARTH_X3_GEN>)
#                    target_include_directories(hearth_core PRIVATE ${X3_GEN_DIR})
```

**Arms.**
- **A**: the pristine b5d3f14 tree, built with the release flags. This is `hearth-c-ref@b5d3f14`,
  provisional pending D0-3.
- **B**: the patched tree with `HEARTH_X3_GEN=ON`.
- Each compiler gets its own A/B pair.
- The hand Q4/Q8 functions stay in B's objects, unreferenced. Compilers may warn about unused
  static functions. Any such warnings are recorded, not suppressed.
- **Layout variants.** For each arm and compiler, the harness's own link step (not Hearth's CMake,
  so no Hearth source changes) links the same `hearth_core` object files into K = 3 executables
  [target]: variant 0 in CMake's object order, variants 1 and 2 in seeded permutations of the object
  order (§8.4). Each variant's SHA-256 and linker map are recorded, including the start address mod
  64 of every measured kernel function. All variants must pass the per-run output-hash check.

**Seam inertness check.** The patched tree is also built with `HEARTH_X3_GEN=OFF`. The `.text`
section of every `hearth_core` object must be byte-identical to arm A's (SHA-256, extracted with
`llvm-objcopy` or `dumpbin /rawdata`). That shows the patch changes nothing when inactive. If it
fails, the patch is fixed before anything else happens.

**Toolchains.** Exactly those pinned for X0's configurations A (MSVC `cl` 14.44.35207, release
win-x64) and B (clang-cl 23.1.3, proxy for SysV Clang) in `experiments/x0-census/TOOLCHAINS.md`,
with CMake's command lines for `CMAKE_BUILD_TYPE=Release` taken from `compile_commands.json`. Every
command line, including clang-cl's expanded `-cc1` line, is recorded for both arms, and the report
lists the effective optimisation level, `-ffp-contract` value and `-target-cpu` of each
translation unit beside the ABI and CRT differences of §8.1.

**What X0 measured about configuration B** (`TOOLCHAINS.md` §4–§6, [M, X0 track, 2026-10-16], on
the desktop; Hearth itself was not compiled there):
- CMake gives clang-cl the MSVC branch of Hearth's CMakeLists (`CMakeLists.txt:37-41, 52-54`):
  `/O2 /Ob2 /DNDEBUG` and `/fp:precise`, never `-ffp-contract=off`. Linux Clang (configuration D)
  gets `-O3 -DNDEBUG -ffp-contract=off`.
- clang-cl's `/O2` expands to `-O3 -vectorize-loops -vectorize-slp -ffunction-sections`, so the
  optimisation level matches D's `-O3`.
- `/fp:precise` expands to `-ffp-contract=on`, and a probe `a*b+c` compiled with
  `/O2 /fp:precise /arch:AVX2` or `/arch:AVX512` became `vfmadd213ss`. `/clang:-ffp-contract=off`
  removes it; a bare `-ffp-contract=off` is ignored by clang-cl. MSVC `/fp:precise` does not
  contract. Configurations A, C and D therefore do not contract; B does.
- `/arch:AVX2` becomes `-target-cpu haswell` and `/arch:AVX512` becomes `-target-cpu
  skylake-avx512`, which has no AVX512-VNNI; D uses `-target-cpu x86-64` plus explicit features. So
  B also differs from D in its tuning target.
- A probe calling `_mm512_dpbusd_epi32` with `quant_avx512.c`'s B flags fails ("requires target
  feature 'avx512vnni'"); adding `-mavx512vnni` (accepted by clang-cl as is) compiles. X0 infers
  that Hearth's own `quant_avx512.c` will not build under B as configured.

**Consequences for X3, provisional pending §14 Q8.**
- Both arms of the clang-cl configuration get one shared flag, `-mavx512vnni`, on
  `quant_avx512.c` and `x3_q_avx512.c`, recorded as a shared flag deviation before data. Without it
  arm A cannot build.
- Contraction under B is a risk for both arms. The generated files are protected by printer rule 5
  (§5.1) and the object scan (§7 step 3). If arm A itself fails §7 step 4 under B because the hand
  files contract, the clang-cl configuration adds `/clang:-ffp-contract=off` to both arms as a second
  shared deviation, listed before data; that change is the Owner's call (Q8).
- A **descriptive bracket arm**, "B-gnu": clang-cl with `/clang:-ffp-contract=off` and, if X0's
  flag-replay probe confirms the spelling, GNU-style ISA features in place of `/arch:` (so that the
  tuning target matches D). It is measured only if quiet hours remain and never gates. It shows how
  far the proxy's conclusions depend on contraction and tuning target.

---

## 7. Bit-identity protocol

The protocol runs in daytime, under each release compiler: MSVC and clang-cl on Windows, plus Linux
Clang in WSL2 (X0 configuration D, required at step 8). It runs on arms A and B built as in §6, on
the desktop (the 9950X; all three ISAs are runnable there, which the protocol asserts). Every step
must pass for all six variants. Any failure makes the affected variant inadmissible until it is
fixed.

| Step | What | Pass condition |
|---|---|---|
| 1 | Build A, B and B-OFF; record hashes | Builds succeed; the seam inertness check (§6) holds |
| 2 | Generator checks | C1–C4 pass for all 6 variants. The provenance lint finds no banned primitive (B1–B12). The generated C equals the printer output byte for byte and passes printer rule 5's self-check (§5.1). All 28 planted lane programs of §4.5 are still rejected, and the six hand-kernel transliterations are still accepted |
| 3 | Object scan (reusing X0's XED tooling on B's generated functions and their call closure) | Zero FMA-class iclasses, zero approximation iclasses (RCP*, RSQRT*, VRCP14*, VRSQRT14*) and zero MXCSR writes. Any instruction outside X0's census union is listed (needed for T1) |
| 4 | `test_quant --no-bench` on A and on B, under each compiler; also with `HEARTH_ISA=avx2` and `HEARTH_ISA=scalar` set for the parent, as T02 did | B: exit code 0, "0 failures", and **a check count equal to A's count under the same compiler and machine**. For context, the count was 117,681 checks at T02-kernels-gen-002 (MSVC 14.44, /O2, `--no-bench`) [R11]; the count at b5d3f14 is whatever A reports [M at run time]. B's printed ISA list must be "scalar avx2 avx512" |
| 5 | Golden suite through `check_golden.py --run` against B's library | All tests pass, with no skips. Specifically `test_isa_identity` (`test_golden_invariants.py:124-135`) and `test_kernel_isa_and_batch_identity` for Q8 and Q4 (`:138-162`). The X3 runner first asserts `hearth_cpu_isa() == AVX512`, because `test_isa_identity` silently drops an ISA that raises `HearthError` (`:131-132`) |
| 6 | Cross-binary kernel corpus (X3-local, in the shape of 07 §2.3's "Kernels" part) | `hearth_matmul` output bytes from B equal A's for Q4 and Q8 × ISA {1, 2, 3} × T ∈ {1..9, 16} × rows ∈ {1..67} × n ∈ {64, 128, 192, 320, 4096} × r-splits as in `test_quant.c:1078-1088`. That is 2 × 3 × 10 × 67 × 5 = 20,100 whole-range calls per compiler [D], plus the row-split repetitions, each output hashed with SHA-256. **Input rule, so that P1 and P2 always hold:** activation codes q and `sum` always come from the hand `act_quantize_q8` of the **scalar** ISA, as in `test_nonfinite` (`test_quant.c:1238-1251`, which randomises only W and builds activations with `act_quantize_q8`). Raw or special values are injected only into W's code bytes, W's f16 `d` (NaN, ±inf, subnormal) and A's f32 `d` after quantisation (NaN, ±inf, subnormal). A separate descriptive "precondition-violating" corpus (raw activation bytes, inconsistent `sum`) may be run; it is never gated |
| 7 | Meaning and printer differentials (§3.5, §5.4) | Byte equality |
| 8 | WSL2 Linux Clang (X0 configuration D, the actual Linux release compiler): steps 1, 4 and 6 on Linux builds of A and B | As above |
| 9 | If X2 is ready (§11): T1 on the four SIMD lane programs (Q4/Q8 × AVX2/AVX-512) | T1 accepts all four |

**Why this suffices without T1.** `test_quant` checks the following:
- every ISA against the scalar variant with `memcmp` (`test_quant.c:1069-1071`);
- batched against single-token calls (`:1073-1077`);
- row splits against the whole (`:1078-1088`);
- the scalar variant against `ref_qrow`, an independent NUMERICS implementation inside the test
  (`:1104-1133`);
- a pinned FNV-1a hash of the scalar Q8/Q4 outputs (`:54-62`, `:901-937`).

In arm B all three variants are generated. So "SIMD equals scalar" alone would not catch a
consistently wrong generator. `ref_qrow`, the pinned hashes and the cross-binary corpus (step 6)
close that gap.

---

## 8. Measurement protocol

### 8.1 Configurations

| Set | Configurations | Count | Status |
|---|---|---|---|
| Primary | {MSVC, clang-cl} × {scalar, AVX2, AVX-512} × {Q4, Q8} | 12 | **confirmatory**. ROADMAP says "per ISA", so the scalar variants are included (§14 Q2) |
| Decode guard | {MSVC, clang-cl} × dispatched ISA (AVX-512) | 2 | **confirmatory** |
| Descriptive | L2, T = 8 (12 configurations); decode with `isa = avx2` (2); the one-binary layout control (§8.6); the B-gnu bracket arm (§6); per-call trace runs (§8.2); `test_quant`'s built-in bench table | — | reported, never gated, run only if quiet hours remain |

The release compilers are MSVC (win-x64) and Clang (Linux). The clang-cl arm is labelled "proxy for
SysV Clang". It differs from SysV Clang in its ABI (Win64 makes XMM6–15 callee-saved), its flag
spelling and its CRT (§12), and, as X0 measured (§6), in FP contraction (`-ffp-contract=on` against
`off`) and in its tuning target (`haswell` or `skylake-avx512` against `x86-64` plus features). Its
optimisation level is the same (`-O3`). Linux Clang gets bit-identity (§7 step 8) but no timing,
because ROADMAP §3.4 puts the Clang timing arm on this desktop.

### 8.2 The primary harness, `x3_bench`

`x3_bench` is a C program written by X3. It is built identically against each arm's `hearth_core`,
in K = 3 layout variants per arm and compiler (§6). It reproduces the shape of `test_quant`'s L2
bench (`test_quant.c:1525-1552`):
- n = 4096 columns, a 512 KiB target, T = 1, one thread.
- Q4: 240 rows × 2,176 B = 522,240 B. Q8: 112 rows × 4,224 B = 473,088 B
  [D: rows = ⌊⌊524,288/rb⌋/16⌋·16].
- Activations: 64 blocks × 72 B = 4,608 B. Both fit Zen 5's 1 MB L2 per core [R08 §1].
- Weights are filled as `fill_weights` does (`test_quant.c:1452-1456`): seeded random quant bytes,
  scales 0x2c00. Activations come from the hand `act_quantize_q8` of the same ISA on seeded Gaussian
  input, identical in both arms.

**A run** is one fresh process. In order:
1. Pin the measuring thread to one fixed logical processor (LP) p on CCD0, chosen in the pilot. Its
   SMT sibling s and its CCD are read from `GetLogicalProcessorInformationEx` (the processor-core and
   L3-cache relations), not assumed from LP numbering. The process runs at `HIGH_PRIORITY_CLASS`,
   never `REALTIME_PRIORITY_CLASS`. The supervisor and the load sampler are pinned to one reserved LP
   on CCD1 (06 §6.7). p, s, the CCD, the reserved LP and the priority class are in the run record.
2. Allocate 64-byte-aligned buffers and touch them.
3. Fill the inputs.
4. Clock probe "pre" (§8.4).
5. Warm up for 0.5 s.
6. **The timed segment, exactly:** `t0 = hx_now_ns();` then R calls of
   `k->matmul[dt](W, n, act, 1, Y, rows, 0, rows)` with nothing else in the loop, then
   `t1 = hx_now_ns();`. No per-call timestamp, trace buffer, logging or check runs between the two
   reads. `time_s = (t1 − t0)·10^−9`. R is fixed per configuration in the pilot so that an A run's
   timed segment lasts about 10 s [target; 06 §6.6 microbenchmark t_run].
7. Clock probe "post".
8. Hash Y. **The hash must equal A's reference hash for that configuration, or the run is void and
   flagged as a bit-identity failure.**

Y is poisoned with `0x7fc0dead` before the timed loop. The run reports `time_s` (the statistic's
input) and throughput, as weight bytes × R / time_s in GB/s, which is context only. Context:
69.6 GB/s for AVX-512 Q4, measured L2-resident on a busy machine; 72.0 in a second run [R11;
T02-kernels-gen-002].

**Per-call traces** (gap attribution only) come from separate descriptive runs, never from a gate
run or a gate session. In those runs one timestamp per 2^16 calls goes into a preallocated array of
at most 512 uint64 values (4 KiB) [target]; a 10 s run fills about 20 entries [D: 1.33·10^6 calls ÷
65,536]. The reason: one AVX-512 Q4 call takes about 7.5 µs [D: 522,240 B ÷ 69.6 GB/s], so R is
about 1.33 million per 10 s run [D], and a per-call uint64 trace would be about 10.7 MB per run [D],
streamed through the same 1 MB L2 that holds W [R08]. Common work inside the timed segment adds the
same time to both arms and compresses the ratio toward 1, which biases a non-inferiority test toward
passing.

**Paths and environment.** Every arm and layout variant is installed at an absolute path of the same
length (for example `D:\x3\bin\A\v0\x3_bench.exe` and `D:\x3\bin\B\v2\x3_bench.exe`). Every run is
launched with the same explicit environment block (same variables, values and order), whose hash is
in the run record. Mytkowicz et al., "Producing wrong data without doing anything obviously wrong!"
(ASPLOS 2009), report measurement bias from link order and environment size of the same order as
δ [cited by reviewer 1; not re-read by the reviser]; §6's layout variants and this rule address it.

### 8.3 The decode guard harness, `x3_decode`

`x3_decode` is a C program against the public `hearth.h` API (`hearth_open`, `hearth_info`,
`hearth_eval`, `hearth_get_stats`). It mirrors `hearth-bench`'s greedy loop
(`engine/tools/hearth_bench.c:1-20`). Options:
- `isa = HEARTH_ISA_AVX512`;
- `n_threads = 0`, which means physical cores, the production placement (06 §6.7);
- `cache_gb` in **GiB** (`hearth.h:68`): ⌈11 × expert_bytes / 2^30⌉ / 10, that is 1.1 × the
  routed-expert bytes rounded up to 0.1 GiB, with `expert_bytes` read from `hearth_model_info`
  (`hearth.h:93`) after a probe open. For the "about 15.4 GB of Q4 experts" quoted from [DR-022]
  that is ≈ 14.3 GiB × 1.1 ≈ 15.8 GiB [D];
- `warm_start = 1`;
- prompt 16 tokens (seeded), 32 warm-up tokens, then **256 timed decode tokens** [target].

**Asserted in every run, or the run is void:** `hearth_model_info.isa == HEARTH_ISA_AVX512` and
`hearth_model_info.n_threads` equal to the value the pilot recorded, the same in A and B
(`hearth.h:98-99`). Both are in the run record.

**Timing.** T is the increase of `hearth_stats.wall_s` ("time inside hearth_eval", `hearth.h:105`)
over the 256 timed tokens, read with `hearth_get_stats` before and after the segment. The harness's
own work between calls is therefore outside T. Each step's logits are SHA-256-hashed after
`hearth_eval` returns, outside `wall_s`. The `hx_now_ns` span of the whole segment is recorded as a
secondary figure.

**"Cached"** is defined operationally: `cache_misses` grows by 0 over the timed segment
(`hearth_get_stats`), otherwise the run is void. Whether `warm_start` fills every slot is unverified:
`hearth.h:78` says it fills "the unpinned cache with the next-hottest experts". So the pilot checks
that at least 95% [target] of its decode runs meet the zero-miss rule. If fewer do, the design
(cache size, warm-up length) is amended before any A/B data, as a pre-data amendment.

**B's logits-hash sequence must equal A's on every run**, which makes every decode run a
cross-binary bit-identity check on the real model.

The model is the real Qwen3-30B-A3B Q4 container from the data directory if it is present, with its
SHA-256 pinned before freeze. Otherwise it is the synthetic Qwen3-30B-A3B Q4 container on which
Hearth measured 21.88 tok/s fully cached (synthetic weights, 16 threads, shared machine at 16–47%
load, 4 repetitions) [R11; H03-forward-gen-002]. The choice is §14 Q10. The container's dtype mix is
recorded. If it has no Q8 tensor, the report says the guard exercises Q4 only.

Decode is about 97% idle at the bandwidth roof [R08], so it cannot detect a codegen regression. It is
a guard only (ROADMAP §3.4).

### 8.4 Sessions

The session design follows 06 §6.1, made concrete.

- **Session.** A contiguous stretch inside one quiet window, for one compiler, one run type (micro or
  decode), one machine-profile hash (06 §5.2) and one measurement LP. A quiet window may hold several
  sessions back to back. Quiet windows are the Owner's (D0-10d); unattended runs need D0-7a.
- **Composition** [target]. A session first runs 2 A/A calibration blocks per active configuration.
  It then runs, for each active configuration k, b_k = min(n_k, L_k − blocks of k already counted in
  the current attempt) A/B blocks (§8.5), plus ⌈Σ b_k / 4⌉ A/A sentinel blocks at seeded random
  positions. In micro sessions the A/B and sentinel blocks of all active configurations are
  interleaved in seeded random order, so drift hits every configuration alike. A configuration stays
  active until a decision (§8.5) stops it, and is dropped only at a session boundary.
- **Blocks.** Each block is ABBA or BAAB for one configuration, drawn from a seeded PRNG whose seed is
  the first 8 bytes of SHA-256(freeze commit hash ‖ session id). The same PRNG draws, independently,
  one layout variant (§6) for the block's A runs and one for its B runs; both ids are recorded.
- **Load gate** [target; X4's profile replaces these values when X4 is live, and the replacement is
  recorded]. Percentages are per logical processor unless marked machine-wide. Sources: PDH
  `\Processor Information(0,n)\% Processor Time` per LP and `\Process(*)\% Processor Time` per
  process, sampled every 250 ms by the sampler on its reserved LP. A run is void, and so is its
  block, if any of these holds:
  - micro runs: the pinned LP's SMT sibling is above 1% in any sample during the run;
  - micro runs: any other LP on the pinned CCD is above 5% in any sample during the run;
  - all runs: machine-wide load from processes other than the measured process, the sampler and the
    supervisor, normalised over the 32 LPs, is at least 2% averaged over the 2 s before the run, at
    least 3% averaged over the run, or at least 10% in any sample during it;
  - all runs: `MsMpEng` (Defender) or `SearchIndexer` uses at least 1% of one LP over the same
    windows.

  Why per LP: read machine-wide, the draft's "< 3% mean, < 10% peak" allowed about 0.96 LP of
  foreign work on average and 3.2 LPs at peak [D: 0.03 × 32, 0.10 × 32]. Landing on the pinned
  core's sibling, that slows the measured thread in either arm at random. Windows tends to schedule
  onto CPPC-preferred cores, which on this part may well be on CCD0 [inference, unverified].
- **Clock probe** [target]. A fixed 50 ms integer spin loop is timed on LP p before the warm-up
  ("pre") and after the timed segment ("post"). In decode runs, whose threads keep Hearth's
  production placement, the probe runs in a short-lived helper thread pinned to p, before
  `hearth_open` and after the timed segment. The run is void if
  \|post/pre − 1\| > 1.5%, or if either rate is more than 3% from the session median of pre rates.
  Both rates are recorded. A package-temperature source is used only if the Owner installs one
  (§14 Q11).
- **Calibration envelope** (06 §6.1 step 2) [target]. Let m be the number of the session's opening
  A/A calibration blocks and σ̂²_cal = (1/m)·Σ d² over them. The session is void if
  m·σ̂²_cal / σ̂²_AA > χ²_{m, 0.99}, with σ̂_AA from the pilot (§8.5). Examples: m = 12 (six
  configurations), χ²_{12, 0.99} = 26.217; m = 2 (decode), χ²_{2, 0.99} = 9.210 [standard table
  values].
- **Stationarity** (06 §6.3). A session is void if any of these holds:
  - the A/A sentinel test (§8.5) reaches 20;
  - **trend** [target]: with each A run time divided by its configuration's session median, a
    stratified Mann–Kendall test (per-configuration S statistics and variances summed) gives a
    two-sided p < 0.01, **and** the pooled Sen slope (the median over configurations of each one's
    Sen slope, per hour) times the session span exceeds 2% in absolute value. Both are required:
    with 100 or more A runs per session a p-value alone flags benign sub-percent drift that ABBA
    already cancels, and 06 §6.3 asks for a trend that "exceeds the profile envelope", which is a
    magnitude;
  - A's session median for any configuration leaves the pilot envelope (±5% of the pilot median for
    that configuration [target]);
  - the calibration envelope above fails.

  Void sessions keep their samples, never pool them, and count toward the void rate, reported by
  reason (D-22).

### 8.5 Statistics

This section implements DR-018, ROADMAP §1 rule 4 and 06 §6.2. The pre-registration carries the
formulas and constants (prereg §7). Operating characteristics are in §8.8; the simulator is
Appendix C.

**Block statistic.** A block's runs are at positions 1–4. Pair 1 is positions (1, 2) and pair 2 is
positions (3, 4), so each pair holds one A run and one B run in ABBA and in BAAB.
d = ½[ln(T_B^(1)/T_A^(1)) + ln(T_B^(2)/T_A^(2))], where T is the timed-segment time of a run (§8.2,
§8.3). A time ratio of 1.03 is a throughput ratio of 1/1.03.

**Boundaries.**
- Pass test: β = ln(1.03) = 0.029558802 [D] on the time scale. ROADMAP §1 rule 4 says
  "ratio < 0.97", that is −ln(0.97) = 0.030459207 [D]; 06 §6.2 says H0: E[x] ≥ log(1.03). β is the
  stricter of the two: it passes only if the throughput ratio is ≥ 0.970874 [D]. §14 Q5 flags the
  discrepancy.
- Regression tests: θ97 = 0.030459207 and θ90 = −ln(0.90) = 0.105360516 [D].

**Pilot quantities**, per run type and compiler [target]. They come from the pilot's A/A blocks in the
fallback, or from X4's A/A data for the same harness and run type when X4 is live. They are frozen
when the confirmatory phase starts and never change afterwards, even if X4 goes live later.
- σ̂_AA = sqrt((1/m)·Σ d²) over the m pilot A/A blocks (the A/A mean is 0 by design).
- Q99 = the empirical 0.99-quantile of \|d\| over the same blocks (linear interpolation, type 7).
- t_run = (median wall time of the pilot's A/A blocks, from the first run's start to the last run's
  end) ÷ 4. This replaces the draft's undefined `t_run_s` and 06's illustrative 10 s and 120 s.

**Two clips, two estimands** [target].
- **Pass test: c_pass = max(Q99, θ97 + 3·σ̂_AA).** The clip must sit well above the margin: a clip at
  or below β would make the null empty, and every configuration would pass. With
  c_pass ≥ θ97 + 3σ, the loss-scored clipped mean at the ROADMAP boundary falls short of the true mean
  by at most about σ·(φ(3) − 3·(1 − Φ(3))) ≈ 0.0004·σ under Gaussian noise [D], far below
  θ97 − β = 0.0009 [D]. So a configuration exactly at ratio 0.97 is still in the pass test's null.
  There is no 0.25 floor. The draft's floor (c ≥ 0.25 with cap 0.5/(c − β)) limited the growth of
  wealth to at most ln(1 + 2.27 × 0.02956) ≈ 0.065 per block even without noise, so reaching 20
  needed at least 46 blocks [D], more than N holds at σ_d ≤ 2% (§8.8, §17).
- **Regression tests: a_reg = max(Q99, 4·σ̂_AA), the half-width of clamps centred on each boundary:**
  x^θ = θ + clamp(d − θ, −a_reg, a_reg). Under any noise that is symmetric about the true mean μ,
  E[x^θ] − θ has the sign of μ − θ, so testing E[x^θ] ≤ θ tests μ ≤ θ. With skewed noise the test is
  about the pre-registered estimand E[x^θ], and the report says so. The draft's clamp, symmetric about
  0 with c ≥ 0.25, kept every bet below 0.5/(c + θ) and could not confirm a ratio of 0.85 within N at
  σ_d ≤ 2% (§8.8). Outliers are not scored as losses here, because that would bias a regression claim
  against B.

**E-processes**: aGRAPA (Waudby-Smith and Ramdas, "Estimating means of bounded random variables by
betting", arXiv:2010.09686; title and authors checked by the x3 track on 2026-10-16). For a stream
v_1, v_2, … with a known lower bound lo < 0, the wealth is W_t = Π_{j≤t}(1 + λ_j·v_j), with the
cap fraction 0.9 [target] (the draft's 0.5 cut the largest allowed bet by 1.8× [D: 0.9/0.5] with
no gain in validity, since any cap below 1 keeps every factor positive):

```text
lambda_{t+1} = clip( m_t / (s2_t + m_t^2), 0, cap )        cap = 0.9 / |lo|   (so 1 + lambda*v >= 0.1)
m_t  = (m_0  + sum_{j<=t} v_j) / (t + 1)
s2_t = (s2_0 + sum_{j<=t} (v_j - m_t)^2) / (t + 1)          one pseudo-observation (m_0, s2_0)
```

- **Pass test K.** H0: E[x | past] ≥ β, with x = d if \|d\| ≤ c_pass, else +c_pass (outlier blocks
  scored as losses for B, 06 §6.2). v = β − x ∈ [β − c_pass, β + c_pass]; cap = 0.9/(c_pass − β);
  pseudo-observation (β, σ̂²_AA), which bets as if at parity from the first block. **Pass_k ⇔ K
  reaches 20** (ROADMAP §1 rule 4; boundary at the stricter ln 1.03, §14 Q5).
- **Regression tests M97 and M90.** H0^θ: E[x^θ | past] ≤ θ. v = clamp(d − θ, −a_reg, a_reg);
  cap = 0.9/a_reg; pseudo-observation (0, σ̂²_AA). **R97_k ⇔ M97 reaches 20**: the anytime-valid
  upper confidence bound on the ratio is below 0.97, a confirmed regression. **R90_k ⇔ M90 reaches
  20**: below 0.90.
- **Sentinel test**, per session. Over the session's A/A sentinel blocks, pooled across its
  configurations, v = clamp(d, −a_reg, a_reg). Two one-sided aGRAPA processes run on +v and on −v,
  each with pseudo-observation (0, σ̂²_AA) and cap 0.9/a_reg, and E_sent = ½(E⁺ + E⁻). E_sent ≥ 20
  voids the session (06 §6.3).

Each is a test supermartingale for its null whenever every λ is predictable and every factor stays
non-negative, whatever the noise law inside the null (06 §6.2). That assumes blocks are exchangeable
given the past, which X4's calibrations test (§8.6).

**When decisions are taken** [target].
1. Only at the end of a session that passed every void check, after all of its scheduled blocks have
   run, even if a process crossed 20 mid-session.
2. "Reaches 20" means W_t ≥ 20 at some valid block index t ≥ 6 of the configuration's e-process. **No
   Pass, R97 or R90 is declared before 6 valid A/B blocks (at least 12 runs per arm).**
3. Precedence at a session end is R90, then R97, then Pass. If K and M97 have both reached 20 by the
   same session end, in either order, the configuration is R97 and the report records an estimand
   conflict. (The draft voided the session in that case, which would have given the configuration
   another chance to pass.)
4. Once R97 has fired, Pass is unavailable for that configuration; M90 keeps running until N.
5. A configuration stops at Pass, at R90, or at N. At N, R97 without R90 is amber (a), and neither K
   nor M97 at 20 is inconclusive (§8.6).

**Plan and limit.**
- n_k = max(6, ⌈12·σ̂²_AA/δ²⌉), with δ = 0.03 (ROADMAP §10).
- Planned hours h_k = n_k × 4 × t_run,k × 1.5 / 3600, and **N_k = 2·h_k** [§1 rule 4].
- **N is consumed per block.** Each valid A/B block of k consumes 4·t_run,k of N_k, so N_k holds
  L_k = 3·n_k A/B blocks [D: 2 × 1.5 × n_k]. Calibration, sentinel and void blocks consume none.
  Actual wall-clock hours are reported beside. This makes "hours" deterministic for the verdict
  script. Whether ROADMAP §10's c ≈ 1.5 (for NVMe cool-downs) should count toward N (L = 3n) or not
  (L = 2n) is §14 Q14; §8.8 gives the operating characteristics under both readings.
- A session schedules at most n_k A/B blocks of k, so a decision is checked at least every n_k blocks
  and one N spans at least three sessions.

**The inconclusive path carries the wealth forward** [target]. A configuration that reaches N_k with
neither K nor M97 at 20 enters ROADMAP §1 rule 4's inconclusive path (§8.6). In its second N-session,
K, M97 and M90 **continue with the wealth carried forward** (K_total = K_attempt1 × K_attempt2, and
likewise M97 and M90), on the re-frozen schedule, with a fresh L_k budget and the same c_pass, a_reg,
σ̂_AA and update state. The threshold stays 20.
- The product is a test supermartingale for the composite null "every variant evaluated for this
  configuration is inferior": each block's conditional mean is in the null whichever variant was
  current, and the re-tuned variant is chosen from past data, so it is predictable.
- So the per-configuration false-pass probability over both attempts is ≤ 1/20. Two fresh tests at 20
  would allow up to 2/20, which would loosen ROADMAP §1 rule 4's error rate.
- A carried Pass supports "at least one of the (at most two) evaluated variants is non-inferior". That
  is the claim X3's assumption needs: one meaning plus schedules can reach parity. The verdict record
  names both schedule hashes. The alternative, splitting α (threshold 40 in each attempt, with
  per-variant claims), is §14 Q17.

**No fixed-n analysis.** ROADMAP §3.4's "≥ 10 runs per arm [P5]" is a floor only, and rule 2 above
gives at least 12 runs per arm before any decision. No fixed-n test, interval or point estimate is
ever a gate input; point ratios are reported as context.

### 8.6 The X4 service, the fallback, and the inconclusive path

| X4 state when X3's confirmatory phase starts | X3 uses | Verdict status |
|---|---|---|
| **Live and calibrated**: service hash frozen; for this run type **and this harness binary**, the A/A calibration (≤ 2 of ≥ 100 sessions reach 20) and the planted-regression calibration (≤ 2 of ≥ 100 per level) have both passed [ROADMAP §3.5] | The service runs X3's sessions (gate, pinning, poisoning, fingerprint, ABBA, e-values) with §8.4–§8.5's rules. X3 supplies binaries, R and configurations | Final |
| **Live, not yet calibrated** | The service, as above | A G2/G3 Pass is recorded as **PASS-PROVISIONAL** (below). R97 and R90 stand, unless the A/A calibration of the same harness fails, which bars them until a re-measurement |
| **Not live** | X3's fallback `x3_ab.py`, implementing §8.4–§8.5 exactly. ROADMAP's "≥ 10 runs per arm" is met by rule 2 of §8.5 and is a floor only | As in the second row |

**PASS-PROVISIONAL** [proposed; §14 Q6]. A G2 or G3 Pass computed before a non-inferiority
(planted-regression) calibration has passed **on the same harness binary hashes and run type** does
not satisfy the gate and cannot seed M2's schedule space. A/A pilot blocks test only the superiority
null, not the non-inferiority null (ROADMAP §1 rule 4). The status becomes Pass when such a
calibration passes, by one of two routes:
- **preferred:** X4 runs its ROADMAP §3.5 planted-regression calibration with `x3_bench` as its
  microbenchmark harness. X3 supplies arm A's binaries and a variant with a calibrated +3% and +4%
  spin, whose realised ratio a separate long run confirms. Decode rests on the microbenchmark
  calibration plus per-session sentinels, as ROADMAP §3.5 says for end-to-end run types;
- **fallback:** X3 runs the same protocol locally on one configuration per compiler (AVX-512 Q4):
  ≥ 100 sessions per level, each run to N, at most 2 reaching 20 [target, ROADMAP §3.5's rule]. At
  σ_d = 2% one session is about (18 A/B + 2 calibration + 5 sentinel blocks) × 4 × 13 s ≈ 0.36 h, so
  about 36 h per level per compiler [D], which is outside X3's budget without an Owner decision.

If the calibration fails, G2 and G3 are barred and re-measured after the fix (ROADMAP §3.5). ROADMAP
§3.7 says X4's lateness does not delay the other verdicts, so X3's verdict is issued in week 6 in
every state, and a PASS-PROVISIONAL is reported as such (§11, amber (d), proposed).

**The inconclusive path** (ROADMAP §1 rule 4), for each configuration that ends N inconclusive: gap
attribution (§10), one bounded tuning window of 7 calendar days [target, §14 Q9] in which only the
inconclusive configurations' schedules may change, then one more N-session with the wealth carried
forward (§8.5). With T_start at the latest at the start of week 3, the window closes in about week 5,
and the first confirmatory nights fall in weeks 4.5–5 (§16). The path therefore cannot finish by the
week-6 Gatekeeper verdict. If it is open in week 6, the X3 status in the M0 verdict is **"amber (b)
pending: second session for configurations {…} scheduled by date D"**, and the final X3 row follows
when the path ends. Whether ROADMAP §3.7 ("the other verdicts do not wait") allows this is §14 Q16.

**Pilot** (fallback only, run under the FROZEN record before any A/B block):
- 20 A/A blocks per compiler on the micro configurations, rotating across the six;
- 10 A/A blocks per compiler on decode.

The pilot fixes R, the measurement LP, the per-configuration median envelopes, t_run, σ̂_AA, Q99,
c_pass, a_reg and n_k, and it runs the decode zero-miss check (§8.3). Its data are never pooled with
A/B data. Cost ≈ 1.4–2.2 quiet hours [D: (2·20·4·13 s + 2·10·4·t_dec) × 1.5 ÷ 3600, with t_dec =
15–40 s; the draft's 4.7 h assumed a 120 s decode run]. After the pilot, `oc_sim.py` is re-run at the
measured σ̂_AA and the result published before the first A/B block (§8.8). That is a computation
under the frozen rule, not an amendment.

**Layout.** The pre-registered control is the layout randomisation of §6 and §8.4: every block draws
its A and B layout variants at random, so the estimand averages over K = 3 link orders per arm
instead of resting on one accidental layout per binary. The report gives the point ratio per layout
variant; a configuration whose per-variant point ratios straddle 0.97 is labelled "layout-sensitive"
(descriptive; it cannot change the verdict). The **one-binary layout control** stays descriptive: a
single binary that links both the hand and the generated functions, with arm A' = hand, run as
6 A'/B blocks for gap attribution.

### 8.7 Quiet-machine hours

Assumptions: t_run = 13 s for micro runs [inference: 10 s timed + 0.5 s warm-up + about 0.5 s of
process start, fill and probes + the 2 s pre-run load window], and 15–40 s for decode runs
[inference: 256 tokens ÷ 21.88 tok/s ≈ 11.7 s timed [D; R11, H03-forward-gen-002], plus an
unmeasured open and warm start of about 14.3 GiB of experts, the prompt and 32 warm-up tokens]. The
pilot measures the real values. c = 1.5 as in ROADMAP §10.

| σ_d | n | ROADMAP §10 plan, 14 configurations | Expected at true parity, with pilot | Expected at a true ratio of 0.99, with pilot | Worst case: every configuration through the full inconclusive path, with pilot |
|---|---|---|---|---|---|
| 1% | 6 | 1.9–2.4 h | 4.6–6.4 h | 6.5–8.7 h | 19.0–24.6 h |
| 2% | 6 | 1.9–2.4 h | 7.5–9.9 h | 9.6–12.6 h | 19.0–24.6 h |
| 4% | 22 | 6.8–8.7 h | 13.4–17.5 h | 20.4–26.3 h | 56.2–71.8 h |

[Plan: D from the ROADMAP §10 formula. Expected: S + D, the mean A/B blocks and sessions per
configuration from `oc_sim.py` (§8.8), then hours = (A/B + 2·sessions + A/B/4) × 4·t_run × 1.5 ÷ 3600
over 12 micro and 2 decode configurations, plus the pilot. Worst case: D, 6n A/B blocks and 6
sessions per configuration. Each range spans t_dec = 15–40 s.]

- The overhead of calibration and sentinel blocks is derived from the schedule as
  (A/B + 2·sessions + A/B/4) ÷ A/B, not assumed: (6 + 2 + 1.5)/6 = 1.58 for one session of n = 6,
  and (22 + 4 + 5.5)/22 = 1.43 for n = 22 over two sessions [D]. The draft's ×1.25–1.4 understated
  it, and its worst-case "≈ 150–165 h" had an arithmetic slip (115.2 × 1.4 + 4.7 = 166.0 [D]). This
  table supersedes both.
- The expected hours exceed the plan because a decision is checked only at session ends, every
  session pays 2 calibration blocks per configuration, and the median Pass decision at parity comes
  at 12 A/B blocks for σ_d = 2% and 26 for σ_d = 4% [S].
- At σ_d = 4% the worst case, about 56–72 h, is a large share of M0's 60–215 h envelope (ROADMAP
  §10). If planned hours exceed the available windows, D-22 fires (ROADMAP §9).

### 8.8 Operating characteristics [S]

**Source.** `oc_sim.py` (Appendix C), standard-library Python, SHA-256
`7b9162e9a1159567ff59884458ebe54b1d46b62e1da7606896deac2c5293ab33` of the scratch copy. Run by the x3
reviser on 2026-10-16 on the laptop: 3,000 replicates per row, seed 20261016, about 29 s of CPU for
every scenario set. Model: d = −ln ρ + Gaussian noise with SD σ_d, where ρ is the true throughput
ratio. The pilot is simulated too (20 A/A blocks for micro, 10 for decode), so c_pass, a_reg and n
vary as they will in the experiment. Monte Carlo standard error ≤ 0.009 per probability [D:
sqrt(0.25/3000)]. It replaces the draft's "oracle bettor" check (ln 20 ÷ (β²/2σ²) ≈ 2.7 blocks), which
used the unbounded Gaussian growth rate that no capped bettor reaches.

**Per configuration, micro, L = 3n** (decode with a 10-block pilot is within 0.035 of these rows at
ratios 1.00, 0.99, the boundaries and 0.90):

| σ_d | True ratio | P(Pass), first N | P(Pass), after the inconclusive path | P(R97 → amber (a)) | P(R90 → kill) | P(inconclusive at the end → amber (b)) | Median A/B blocks at a Pass |
|---|---|---|---|---|---|---|---|
| 1% | 1.00 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 6 |
| 1% | 0.99 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 12 |
| 1% | 1/1.03 (β boundary) | 0.002 | 0.012 | 0.001 | 0.000 | 0.988 | 30 |
| 1% | 0.97 (ROADMAP boundary) | 0.001 | 0.005 | 0.003 | 0.000 | 0.991 | 30 |
| 1% | 0.95 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | – |
| 1% | 0.90 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | – |
| 1% | 0.85 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | – |
| 1% | 0.80 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | – |
| 2% | 1.00 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 12 |
| 2% | 0.99 | 0.900 | 1.000 | 0.000 | 0.000 | 0.000 | 18 |
| 2% | 1/1.03 (β boundary) | 0.002 | 0.009 | 0.000 | 0.000 | 0.991 | 30 |
| 2% | 0.97 (ROADMAP boundary) | 0.001 | 0.007 | 0.005 | 0.000 | 0.988 | 30 |
| 2% | 0.95 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | – |
| 2% | 0.90 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | – |
| 2% | 0.85 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | – |
| 2% | 0.80 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | – |
| 4% | 1.00 | 0.988 | 0.999 | 0.000 | 0.000 | 0.001 | 26 |
| 4% | 0.99 | 0.863 | 0.983 | 0.000 | 0.000 | 0.017 | 41 |
| 4% | 1/1.03 (β boundary) | 0.020 | 0.026 | 0.010 | 0.000 | 0.964 | 48 |
| 4% | 0.97 (ROADMAP boundary) | 0.010 | 0.014 | 0.018 | 0.000 | 0.968 | 54 |
| 4% | 0.95 | 0.000 | 0.000 | 0.988 | 0.000 | 0.012 | – |
| 4% | 0.90 | 0.000 | 0.000 | 0.993 | 0.007 | 0.000 | – |
| 4% | 0.85 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | – |
| 4% | 0.80 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | – |

**Gate level** (12 micro and 2 decode configurations, all at the same true ratio, assumed
independent) [S + D: products of the per-configuration rates]:

| σ_d | True ratio | P(gate Pass), first N | P(gate Pass), after the full inconclusive path | L = 2n reading: first N / full path |
|---|---|---|---|---|
| 1% | 1.00 | 1.000 | 1.000 | 1.000 / 1.000 |
| 1% | 0.99 | 1.000 | 1.000 | 0.982 / 1.000 |
| 2% | 1.00 | 0.995 | 1.000 | 0.535 / 1.000 |
| 2% | 0.99 | 0.231 | 0.996 | 0.000 / 0.764 |
| 4% | 1.00 | 0.822 | 0.990 | 0.546 / 0.982 |
| 4% | 0.99 | 0.118 | 0.751 | 0.009 / 0.464 |

(The L = 2n column uses the micro rows for all 14 configurations.) At a common true ratio of 1.00 or
0.99 no configuration reaches R97 or R90 in these runs, so P(amber (b)) = 1 − P(gate Pass).

**Robustness at σ_d = 2%**, with 5% of blocks given an extra N(0, (5σ_d)²) term:
- symmetric outliers: P(Pass | 1.00) = 0.946 in the first N and 0.999 after the path; P(Pass | 0.97)
  = 0.008; P(R90 | 0.90) = 0.001;
- one-sided, B looks faster (an arm-exchangeability violation): P(Pass) = 0.075 at a Gaussian centre
  of 1/1.03. The outlier term moves the mean of d by −0.05 × 5σ_d × sqrt(2/π) ≈ −0.0040 [D], so the
  true mean ratio is about 0.975, inside the non-inferior region;
- one-sided, B looks slower: P(R97) = 0.069 at a Gaussian centre of 0.97; the mean moves by +0.0040
  [D], to a true mean ratio of about 0.966.

The last two rows show the tests tracking the shifted mean, not a failure of validity. Arm asymmetry
of this kind is what the A/A sentinels and X4's calibrations exist to catch.

**The draft, for the review log** (same simulator, `design=draft`): P(Pass | 1.00) in the first N =
0.000 at σ_d = 1% and 2%, and 0.717 at 4%. P(R90 | 0.85) = 0.000 at 1% and 0.001 at 2%; P(R90 | 0.80)
= 0.280 at 2%. This reproduces reviewer 1's blocker.

**Reading.**
- False pass: at most 0.026 at the β boundary and 0.014 at the ROADMAP boundary [S], inside Ville's
  1/20.
- False kill: P(R90 | 0.90) ≤ 0.007 [S].
- Power at parity meets the pre-registered gate-level target, P(gate Pass | parity) ≥ 0.8 after the
  full inconclusive path [target], at σ_d ≤ 4% under both readings of N.
- At a common true ratio of 0.99 with σ_d = 4% it gives 0.751 (0.464 at L = 2n). ROADMAP §10's
  n = 12σ²/δ² underestimates what a bounded bettor needs when the margin shrinks to 2%. §14 Q15.
- Before the first A/B block, the table is recomputed at the pilot's σ̂_AA. If the gate-level
  P(Pass | parity) after the full path is then below 0.8, the report says so before any A/B data, and
  the Owner decides whether to proceed under this record or to replace it with a new signed record
  (ROADMAP §1 rule 1; §14 Q15).

---

## 9. The schedule-lines rule (at most 30%)

### 9.1 Counting definitions

- **X3-LOC-C, for C.** A physical line counts if it still contains a non-whitespace character after
  C comments (`/* */`, `//`) are deleted, with string and char literals respected. Tokens are C
  lexical tokens of the same text.
- **X3-LOC-PY, for Python.**
  1. Format the file with `black` at line length 100. The `black` version is pinned in the X3
     manifest.
  2. Count the physical lines that are not blank, not comment-only, and not inside a docstring (the
     first-statement string of a module, class or function).
  
  Tokens come from `tokenize`, excluding COMMENT, NL, NEWLINE, INDENT, DEDENT, ENCODING, ENDMARKER
  and docstring STRING tokens.
- **H (hand-written lines).**
  - Count X3-LOC-C over the **closure** of the dispatched Q4/Q8 table entries in **`quant_avx2.c` and
    `quant_avx512.c`**.
  - The closure is the roots `mm_q8_<isa>` and `mm_q4_<isa>` plus every top-level function or
    `#define` of the same file whose name appears in a closure member, transitively.
  - Header-defined names and the table initialisers are excluded. Shared helpers count once per file.
- **S (schedule text).** Count X3-LOC-PY over every file under `x3gen/hearth/` except `meaning.py`
  and `tests/`. Add:
  - every line of `core/` or `isa/` that the **specificity lint** flags (below), unless an
    independent reviewer signs it off as generic;
  - every key-value of any tuned-parameter file (JSON, TOML) that a schedule reads.
- **Specificity lint.** These patterns, case-insensitive, over identifiers, strings and literals in
  `core/` and `isa/`, mark a line as Hearth-specific:
  - identifiers matching `q4|q8|qk|nib|hx_|hearth|act_?q8|block_?q|tch|qtile|bias_?8|bias_?128`;
  - integer literals equal to a Hearth block size (34, 66, 72), or `0x0f`/`0xf0` used as a nibble
    mask outside a format-derived constant.
  
  In addition, every `isa/` entry must name exactly one intrinsic; a composite idiom fails the lint.
  There is exactly one named exception, `scalar.h2f_bits` (§5.1), validated by exhaustive
  comparison over all 65,536 inputs, counted under I and listed in the report. Any other exception
  needs a pre-data amendment.

### 9.2 H, measured

| File (b5d3f14) | Closure members | LOC | Tokens |
|---|---|---|---|
| `quant_avx2.c` | `HX_CANON_NAN`, `Q4_BS`, `Q8_BS`, `TCH`, `canon8`, `ld4s`, `ld_u16`, `mm_q4_avx2`, `mm_q8_avx2`, `mm_quant`, `qtile8`, `red8` | **129** | 1,718 |
| `quant_avx512.c` | `HX_CANON_NAN`, `Q4_BS`, `Q8_BS`, `TCH`, `act_bcast`, `canon16`, `canon4`, `dot_quad`, `ld4s`, `ld_u16`, `mm_q4_avx512`, `mm_q8_avx512`, `mm_quant`, `q16_scales`, `q16_step`, `q16_unpack`, `qtile16`, `qtile4`, `red_quad1`, `red_quads`, `unpack_quad` | **174** | 2,470 |
| **H (SIMD)** | | **303** | **4,188** |
| `quant.c`, for reference | `HX_CANON_NAN`, `mm_q4_scalar`, `mm_q8_scalar`, `q_canon`, `q_f16` | 66 | 719 |

[M, x3 track, 2026-10-16. Script: Appendix A, SHA-256 `69c6c3fdb6f86cb846304d21ec56eed37fb7556095ddbf251a20a404be5f62f3`
of the scratch copy. Input blob ids in §6. The AVX2 count was hand-checked against line ranges:
4 macros + 3 + 5 + 4 + 6 + 90 + 11 + 3 + 3 = 129.]

**Threshold.** S ≤ ⌊0.30 × 303⌋ = **90 lines** [target, derived from ROADMAP's 30%].

**Why the SIMD-only denominator.** It is the strict reading. Counting the scalar closure too
(H = 369, cap 110) would loosen the rule. The scalar function is the meaning in Hearth, not a
schedule (`quant.c:5`). §14 Q1 asks the Owner to confirm.

### 9.3 Reported beside S (descriptive; no threshold)

- M, the meaning's LOC.
- L, the library's LOC (`core/`).
- I, the instruction table's LOC.
- The generated C's LOC per file.
- (M + S)/H, the text a maintainer edits per kernel family.
- S_tok/H_tok, the token ratio. A pass on lines with a failure on tokens is reported as a
  line-packing warning.

The generator itself, L + I, is a one-off cost amortised over every future kernel. The report states
it plainly rather than hiding it, because "one generator replaces 303 lines" is only meaningful next
to the size of the generator.

---

## 10. The two-week tuning budget

- **T0, functional completion.** T0 is the first x3gen commit at which all six variants pass §7
  steps 1–7 under MSVC and clang-cl.
- **The window.** It opens at T_start = min(T0, the start of sprint week 3) [target] and closes 14
  calendar days later [target: ROADMAP's "two weeks"].
  - Capping T_start stops a late T0 from postponing the kill indefinitely.
  - A configuration that has no admissible bit-identical variant when the window closes counts as
    "< 90%" for kill (a) (§11).
- **Allowed during the window:**
  - edits to schedule files;
  - new or changed P_X3 primitives, each with a written DAG-preservation argument and a check,
    reviewed and added to the planted suite with at least one negative test;
  - new `isa/` entries, each validated (§5.4);
  - printer changes, each with the differential test re-run.
- **Frozen during the window:**
  - the meaning (frozen at the end of week 1);
  - the harnesses, flags, toolchains, hand kernels and the measurement protocol.
- **Exploratory timing during the window** may run in daytime on the desktop. It is labelled
  exploratory and never pooled with confirmatory data (06 §6.4). No confirmatory block runs on a
  schedule that is still being tuned.
- **Effort cap.** X3's total stays within ~20 owner hours and $1–3k [inference, ROADMAP §3.4]. Owner
  time goes to:
  - prereg sign-off (2 h);
  - meaning review (2 h);
  - primitive and checker review (4 h);
  - patch review (1 h);
  - tuning reviews (4 h);
  - the verdict and report (3 h);
  - a buffer (4 h).
- **Gap attribution, for any configuration below parity** (feeds an amber M2 item):
  1. **Census diff.** X0's XED tooling on the hand and generated objects: instructions per hot-loop
     iteration, loads and stores, spills and reloads, branches.
  2. **llvm-mca.** Block throughput of each hot loop at the pinned LLVM version with
     `-mcpu=znver5`, labelled [S]. LLVM's znver5 reuses the Znver4 model (DECISIONS
     `bypass_llvm_as_goal`).
  3. **Layout.** The per-layout-variant point ratios (§8.6) and the one-binary control of §8.6.
  4. **Per-call time traces**, from separate descriptive runs only (§8.2), never from gate runs.

  Hardware counters on Windows need a profiler that the Owner installs, so they are not assumed
  (§14 Q11).
- **Close.** At window close, the final schedules are frozen (by hash) and the generator is
  regenerated. §7 is re-run in full, and then the confirmatory sessions start in the next quiet
  windows.

---

## 11. Outcomes and what follows from each

The pre-registration carries the exact gate, amber and kill text from ROADMAP §3.4 and the decision
table. In short, with K the pass test, R97 and R90 the regression tests, and N the limit (§8.5), and
with "reaches 20" evaluated only at session ends from block 6 on (§8.5):

| Outcome | Condition | Consequence |
|---|---|---|
| **Pass** | All of the following: §7 passes for all variants under every release compiler; K reaches 20 for all 12 primary configurations and both decode configurations, without R97 having fired first (§8.5 rule 4); a non-inferiority calibration has passed on the same harness binaries and run type (§8.6); S ≤ 90; and, if X2 is ready, T1 accepts the four SIMD lane programs | "One meaning plus schedules" stays in the plan. M2 builds KIR schedules (02 §8) starting from P_X3 as the candidate certified schedule space |
| **Amber (a)** | Some primary configuration has R97 but not R90 by N: confirmed below 97%, not confirmed below 90% | The gap goes to M2 as a named item with gap attribution (ROADMAP §3.4) |
| **Amber (b)** | Inconclusive: neither K nor R97 reaches 20 within N, then one bounded tuning window (7 days [target, §14 Q9]), then one more N with the wealth carried forward; still neither | As §1 rule 4: a signed record with a scoped tombstone (`x3_parity_unresolved`, §13). At M0 nothing ships, so "C as the default behind the seam" means the hand kernels stay. If the path is still open at the week-6 verdict, X3 is reported as "amber (b) pending", with the second session's date (§8.6, §14 Q16) |
| **Amber (c), proposed** | Decode guard R97 or R90, or S > 90, or T1 rejects a variant through its own incompleteness (an independent DAG diff shows the variant equal to the meaning) | ROADMAP defines no band for these. The proposal is amber with a named M2 item; §14 Q3 |
| **Amber (d), proposed: pass pending calibration** | Every Pass condition holds except the non-inferiority calibration on the same harness binaries and run type (PASS-PROVISIONAL, §8.6) | Action: the calibration runs (X4, or X3-local with Owner approval). It becomes Pass when the calibration passes; if the calibration fails, G2 and G3 are barred and re-measured after the fix. M2 may not seed from P_X3 meanwhile. §14 Q6 |
| **Kill (a)** | After the window, some primary configuration has R90 ≥ 20, or has no admissible bit-identical variant | "One generator" leaves the plan. Kernels become explicit-SIMD `.mith` checked by T1 (ROADMAP §3.4, §4 "X3 kill alone": NARROW). With an X2 kill as well, the outcome is STOP-L. The tombstone `one_generator_for_kernel_triplets` is written (§13) |
| **Kill (b)** | Any variant submitted to the gate contains a banned primitive or escape hatch (§4.4, mechanical lint), or the report shows with DAG-diff evidence that bit-identity is unreachable without one | As kill (a) |

Precedence: kill over amber over pass. A T1 rejection traced to a real DAG change makes the variant
inadmissible. That counts toward kill (a) if it is not fixed within the window.

---

## 12. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Correlated bugs: x3gen's checker and generator share an author | A wrong DAG passes C1 | `ref_qrow`, the pinned hashes and the cross-binary corpus (§7) are independent of x3gen; T1 if X2 is ready; the planted suite (§4.5) |
| Code layout differs between binaries | Each binary has one fixed layout; artefacts of a few percent, the size of δ, could flip pass, amber (a) or inconclusive (size on Zen 5 with these kernels unmeasured) | Layout randomisation: K = 3 link-order variants per arm and compiler, drawn per block (§6, §8.4); equal-length paths and a fixed environment block (§8.2); per-variant ratios and a "layout-sensitive" label; the one-binary control for attribution (§8.6) |
| MSVC handles generated SSA code worse than hand arrays (or better) | Parity under MSVC is the real question (ROADMAP §3.4) | Code shape is a tuning knob. MSVC is confirmatory |
| clang-cl cannot compile VNNI with Hearth's flags (**measured by X0**: the probe fails without `-mavx512vnni`) | The clang-cl arm cannot build | One shared flag, `-mavx512vnni`, on both arms' AVX-512 files, listed before data (§6, §14 Q8) |
| clang-cl `/fp:precise` contracts (**measured by X0**: `-ffp-contract=on`; a scalar `a*b+c` became `vfmadd213ss` under `/arch:AVX2` and `/arch:AVX512`) | Bit-identity fails under clang-cl, in the generated or the hand files | Printer rule 5: one FP operation per C full-expression (§5.1); the object scan (§7 step 3); `-cc1` lines recorded; if arm A itself fails §7 step 4 under B, a shared `/clang:-ffp-contract=off` (§6, §14 Q8) |
| The sequential tests are underpowered, so X3 collapses to amber (b) by construction (the draft's 0.25 clip floor did this) | No pass and no kill can happen | Two clips (§8.5); the OC simulation (§8.8) published before freeze and re-run at the pilot's σ̂; gate-level power target ≥ 0.8 at parity [target]; §14 Q15 |
| Common work inside the timed segment | The ratio is compressed toward 1, biasing toward a pass | The timed segment is two clock reads around the R calls only; traces in separate runs; decode timed by `wall_s` with hashing outside it (§8.2, §8.3) |
| The microbenchmark is unrepresentative (one shape, L2) | Parity that does not transfer | The decode guard; T = 8 descriptive; B12 bans shape specialisation |
| Test-count drift (117,681 is a historic count) | A false mismatch | The reference is A's count at b5d3f14, same compiler and same day |
| X4 not calibrated in time | A Pass cannot satisfy the gate (PASS-PROVISIONAL, amber (d)) | §8.6 rules; X4 adopts `x3_bench` as its microbenchmark harness (§15) |
| The inconclusive path runs past week 6 | X3's row is not final at the M0 verdict | "amber (b) pending" with a scheduled date (§8.6); §14 Q16 |
| Not enough quiet nights | The verdict slips | D0-10d; D-22 |
| Meaning mis-transcribed | A consistent but wrong generator | Independent meaning review plus the meaning differential (§3.5) |
| Tuning against the confirmation shape | Winner's curse | Frozen schedules and fresh seeds for confirmation; exploratory data never pooled (06 §6.4) |
| The generator is "hand-writing in disguise" | The 30% rule is gamed | §9.1: specificity lint, single-intrinsic `isa/` entries, `black` formatting, token ratio |
| Same-family review | Weaker independence than ROADMAP asks | Labelled in every review log (m0/README) |

---

## 13. Tombstones (proposed for DECISIONS.md §4)

These use the §4 format and the 06 §7.2 trigger grammar. `ext.*` facts are entered by the Owner
with a citation; they are graded `assumed` and can fire a revisit, never a promotion (DECISIONS §1).
These are proposals only: X3 does not edit DECISIONS.md.

```text
tombstone exo_as_x3_generator {
    verdict: costlier                      // an IEEE DAG check is needed anyway; no int8-dot or cvtph instrs; @instr templates unchecked
    scope:   { experiment: x3, role: generator_dependency, tool: exo_lang_1_0_0 }
    class:   T
    revisit_when: ext.exo.ieee_exact_mode == true
               || (ext.exo.instr_semantics_checked == true && ext.exo.instr_available(name: vpdpbusd) == true)
    evidence: [R05 F2] [X3-DESIGN §2.2-2.4]     // PyPI 1.0.0 (2024-11-05); x86.py read 2026-10-16
    // caveat: docs and x86.py read on main without a pinned commit; stage_mem(accum=False) unverified
    // survivor: x3gen borrows Exo's primitive vocabulary; P_X3 seeds the KIR schedule space (02 §8.1)
}

tombstone exo_real_equivalence_as_exact_evidence {
    verdict: unsound                       // reals: reassociation passes; replace() may map acc += a*b onto mm512_fmadd_ps
    scope:   { use: refines_evidence, contract: canon_v1, checker: exo_effect_analysis }
    class:   F                             // under IEEE-exact canon.v1
    revisit_when: ext.exo.ieee_exact_mode == true || canon.version != at_burial.canon.version
    evidence: [R05 F2] [X3-DESIGN §2.2-2.3]
    // survivor: IEEE-exact DAG check (x3gen C1-C4; T1 at M2)
}

tombstone fp_reassociating_schedule_primitives {
    verdict: unsound                       // split accumulators, FMA, factoring, +0.0 removal, stage-accumulate (X3 B1-B5)
    scope:   { slots: exact_kernels, contract: canon_v1 }
    class:   F                             // under canon.v1 order and no contraction (NUMERICS:10-12)
    revisit_when: canon.version != at_burial.canon.version || exists(c in ledger.certs: c.kind == T3)
    evidence: [R05] [R07] [X3-DESIGN §4.4]
    // survivor: real(bound) schedules with a T3 certificate (reserved, D-07)
}

tombstone decode_as_codegen_parity_evidence {
    verdict: vacuous                       // decode GEMV ~97% idle at the bandwidth roof [R08]
    scope:   { metric: decode_tok_s, claim: kernel_codegen_parity, hw: 9950x }
    class:   F                             // under bandwidth-bound decode
    revisit_when: !(cost.decode.binding_resource in {dram, nvme, vram, pcie})
    evidence: [R08] [ROADMAP §3.4]
    // survivor: decode kept as a guard; parity rests on the L2-resident microbenchmark
}

tombstone clang_parity_as_msvc_evidence {
    verdict: misleading                    // MSVC zmm register allocation and scheduling differ from Clang's
    scope:   { claim: generator_parity, measured_with: clang_cl, release_target: win_x64 }
    class:   T
    revisit_when: meas.rank_corr(x3_ratio(compiler: msvc), x3_ratio(compiler: clang_cl)) >= 0.95
    evidence: [ROADMAP §3.4]
    // survivor: per-release-compiler A/B; clang-cl labelled proxy
}
```

The review of 2026-10-16 (§17) rejected four parts of the draft's measurement design. They are
proposed as tombstones too, so that the reasons survive. The `sim.x3_oc(…)` facts are the outputs of
`oc_sim.py` (Appendix C), recorded with the script's hash.

```text
tombstone wide_clip_pass_bettor {
    verdict: infeasible                    // clip >= 0.25, cap 0.5/(c - beta): growth <= 0.065/block, >= 46 blocks to reach 20
    scope:   { experiment: x3, test: pass, clip_floor: 0.25, bet_cap: 0.5, limit: roadmap_10_n_rule }
    class:   V
    revisit_when: sim.x3_oc(design: draft, sigma_d: 0.02).p_pass_parity_first_n >= 0.8
    evidence: [X3-DESIGN §8.5, §8.8]       // sim: 0.000 at sigma_d 1% and 2% (3,000 replicates)
    // survivor: c_pass = max(Q99, theta97 + 3 sigma_AA), cap 0.9/(c_pass - beta)
}

tombstone zero_centred_regression_clamp {
    verdict: infeasible                    // clamp about 0 with c >= 0.25: P(R90 | ratio 0.85) = 0.001 within N at sigma_d 2%
    scope:   { experiment: x3, test: regression, clamp_centre: zero, limit: roadmap_10_n_rule }
    class:   V
    revisit_when: sim.x3_oc(design: draft, sigma_d: 0.02).p_r90_at_ratio_085 >= 0.8
    evidence: [X3-DESIGN §8.8]
    // survivor: clamps centred on each boundary, half-width a_reg = max(Q99, 4 sigma_AA)
}

tombstone fresh_eprocess_on_retest {
    verdict: unsound                       // two fresh tests at 20 allow a false pass of up to 2/20 per configuration
    scope:   { experiment: x3, path: inconclusive_second_session, threshold: 20 }
    class:   F                             // under a per-configuration false-pass bound of 1/20
    revisit_when: prereg(x3.false_pass_bound_per_config) >= 0.1
    evidence: [X3-DESIGN §8.5] [ROADMAP §1 rule 4]
    // survivor: wealth carried forward (composite null); or alpha split, threshold 40 per attempt (§14 Q17)
}

tombstone void_on_estimand_conflict {
    verdict: gameable                      // voiding a session where Pass and R97 both fire gives another chance to pass
    scope:   { experiment: x3, rule: pass_r97_conflict }
    class:   F                             // under a fixed per-configuration error budget
    revisit_when: prereg(x3.false_pass_bound_per_config) >= 0.1
    evidence: [X3-DESIGN §8.5 rule 3]
    // survivor: precedence R90 > R97 > Pass, with the conflict reported
}
```

These two are written only if their outcome fires. Each would be copied from the signed report.

```text
tombstone one_generator_for_kernel_triplets {          // written only if X3 kill (a) or (b) fires
    verdict: slower | unsound                          // (a) R90 confirmed after tuning | (b) needs a banned primitive
    scope:   { kernels: {q4_matmul, q8_matmul}, isas: {scalar, avx2, avx512}, compilers: {msvc, clang_cl},
               hearth: b5d3f14, generator: x3gen@<hash> }
    class:   S                                         // (a): two weeks of search; (b) would be F under canon.v1
    revisit_when: has(primitive: kir_schedule_search) || meas.kernel_gap_attributed(codegen) >= 0.05
    evidence: ledger:sha256:…
}

tombstone x3_parity_unresolved {                       // written only on amber (b), the inconclusive path
    verdict: unproven
    scope:   { configs: <the inconclusive set>, sigma_d: <measured>, hours: <spent> }
    class:   V                                         // measurement-limited
    revisit_when: hw.measurement_hosts >= 2 || meas.sigma_d(run: x3_micro) <= 0.5 * at_burial.meas.sigma_d(run: x3_micro)
    evidence: ledger:sha256:…
}
```

---

## 14. Owner questions

These must be answered before the pre-registration is FROZEN. Each answer is recorded in the record,
not here.

1. **H's denominator.** H = 303, the SIMD-only Q4/Q8 closure (strict, chosen here). The alternative
   is H = 369, which also counts the scalar closure and gives a cap of 110. Also confirm the closure
   rule, under which shared helpers count once per file.
2. **Scalar variants confirmatory.** ROADMAP §3.4 says "per ISA", so they are confirmatory here.
   ROADMAP §10's S1 row makes scalar screening-only. Dropping them would save ≈ 0.4–1.5 quiet hours
   [D].
3. **Bands ROADMAP leaves undefined** (§1 rule 2 needs every band defined). Proposed:
   - S > 90 → amber;
   - a confirmed decode-guard regression → amber;
   - a T1 rejection through T1 incompleteness → amber;
   - no admissible variant at window close → counts as < 90% (kill (a)).
4. **Kill confirmation level.** The level is 1/20 per configuration, with no multiplicity correction
   across 12. Family-wise, a false kill needs some configuration truly at about 0.90, so it is
   negligible otherwise. A Bonferroni level (1/240) would make kills rarer, which loosens the kill,
   so it is not adopted.
5. **Margin boundary.** ROADMAP's "ratio < 0.97" (time boundary 0.030459) disagrees with 06's
   "E[x] ≥ log(1.03)" (0.029559). The stricter log(1.03) is used. Which is canonical?
6. **X4 timing and PASS-PROVISIONAL.** Without a planted-regression calibration on the same harness
   binaries and run type, a G2/G3 Pass is recorded as PASS-PROVISIONAL and reported as amber (d),
   "pass pending calibration" (§8.6, §11). It does not satisfy the gate and cannot seed M2 until the
   calibration passes. (a) Is that the intended reading of ROADMAP §3.5 and §3.7? (b) Should X4 adopt
   `x3_bench` as its microbenchmark harness, so that its calibration covers X3? (c) If X4 cannot,
   is the X3-local calibration (about 36 h per level per compiler at σ_d = 2% [D]) worth its cost?
7. **Comparator.** `hearth-c-ref@b5d3f14`, provisional pending D0-3. If S0 tags `port-base-1` with
   the R3 changes, which touch `quant.c`, before X3 collects data, should X3 re-pin by a pre-data
   amendment, re-measuring H?
8. **clang-cl flags.** X0 measured that configuration B cannot compile `_mm512_dpbusd_epi32` with
   Hearth's flags, contracts under `/fp:precise` (`-ffp-contract=on`), and tunes for `haswell` or
   `skylake-avx512`; its `/O2` is already `-O3` (§6). Proposed, provisional: X0 configuration B's
   command lines plus one shared `-mavx512vnni` on both arms' AVX-512 files, and, only if arm A
   fails §7 step 4 under B, a shared `/clang:-ffp-contract=off`. The bracket arm B-gnu
   (`/clang:-ffp-contract=off` and GNU-style ISA features) is descriptive. The alternative is to make
   B-gnu the confirmatory clang-cl arm, which mimics the SysV build more closely but departs further
   from what CMake gives clang-cl. Which should be confirmatory?
9. **The bounded tuning window** of §1 rule 4's inconclusive path is set at 7 days [target]. Is that
   length right?
10. **Decode container.** The real Qwen3-30B-A3B Q4, preferred because its logits hashes are
    meaningful, or the synthetic container behind the 21.88 tok/s figure?
11. **Machine settings.** Installing a temperature or counter source (for example AMD uProf), a
    measurement power plan and a Defender exclusion are Owner decisions (06 §6.7). Without them X3
    uses the clock probe and voids.
12. **WSL2 Linux Clang.** Bit-identity there is included in the gate (§7 step 8). That is a
    tightening; confirm it.
13. **Generator choice.** Confirm x3gen over Exo (§2.4). The decision is reversible until T0.
14. **What counts toward N.** ROADMAP §1 rule 4's N is twice the hours §10 plans, and §10's plan
    includes c ≈ 1.5 "for NVMe cool-downs". If N is consumed only by A/B block time (this design,
    §8.5), it holds 3n blocks; if cool-downs and gaps count too, about 2n. The choice changes power,
    not any error rate: at σ_d = 2% and parity, the gate-level P(Pass) in the first N is 0.995 with
    3n and 0.535 with 2n [S, §8.8]. Which reading is intended?
15. **ROADMAP §10's n-formula and bounded bets.** n = max(6, 12σ²/δ²) assumes roughly Gaussian
    efficiency. With the capped bettor X3 must use (06 §6.2), the gate-level power at parity after
    the full inconclusive path is ≥ 0.99 at σ_d ≤ 4% [S], but at a common true ratio of 0.99 and
    σ_d = 4% it is 0.751 (0.464 under the 2n reading) [S]. X3 does not lengthen N on its own. Should
    §10's formula be revised for bounded-bet sample sizes (for example, sizing N from `oc_sim.py`),
    and should the record proceed if the pilot's σ̂ gives a gate-level P(Pass | parity) below the
    0.8 [target] of prereg §6?
16. **The inconclusive path and week 6.** The path (gap attribution, 7-day window, second N) cannot
    finish by the week-6 verdict (§8.6). Proposed: report X3 as "amber (b) pending: second session
    scheduled by date D". Does ROADMAP §3.7 ("the other verdicts do not wait") allow that, or should
    T_start be capped earlier (for example at week 2.5 [target]), which can shorten the tuning that
    follows a late T0?
17. **α across the two attempts.** Chosen: carry every wealth forward, threshold 20, which bounds a
    false pass per configuration by 1/20 and supports "at least one evaluated variant is
    non-inferior" (§8.5). The alternative splits α (threshold 40 in each attempt) and supports a
    per-variant claim, at about 1.23× the blocks per attempt [D: ln 40 / ln 20]. Which claim does the
    Owner want?
18. **Regression estimand.** The regression tests use clamps centred on each boundary (§8.5), which
    test the true mean under symmetric noise and, under skewed noise, the pre-registered clamped mean.
    The draft's clamp about 0 could not confirm a kill-size regression within N (§8.8). Confirm the
    centred estimand, or name another that keeps the kill reachable.

---

## 15. Proposed changes to other documents

X3 edits none of these. These are proposals for their owners.

- **02-compute §7.2.** Use the storage range for the Q8 block-sum bound: 1,040,384, not 1,032,256
  (§3.3).
- **02-compute §8.1 and ARCHITECTURE §7.1.** Cite the concrete Exo evidence of §2.2 (the
  `mm512_fmadd_ps` body, the `mm256_add_epi16` template) where the documents say "Exo treats floats
  as reals".
- **ROADMAP §3.4.** Define the bands of §14 Q3. State that "matvec" means the Q4/Q8 matmul slot
  measured at T = 1.
- **ROADMAP §1 rule 4 and 06 §6.2.** Reconcile the margin boundary (§14 Q5).
- **06 §6.2.** State that a pass test's clip must exceed the margin by several σ (X3 uses
  c ≥ θ97 + 3σ̂), because a clip at or near the margin empties the null; and that a regression or
  kill test needs its own estimand (X3 centres its clamps on each boundary), because a wide symmetric
  clip makes kills unreachable within N (§8.5, §8.8).
- **ROADMAP §10.** Note that the n-formula understates bounded-bet sample sizes when the effective
  margin shrinks, and say what counts toward N (§14 Q14, Q15).
- **X4 (MEASUREMENT-SERVICE).** Adopt `x3_bench` (by hash) as the microbenchmark harness of the
  planted-regression calibration, so that X3's G2 can become final (§8.6, §14 Q6); and adopt per-LP
  load-gate units and the magnitude-plus-p trend rule of §8.4 if X4 has not fixed them otherwise.
- **DECISIONS §4.** Add the tombstones of §13.
- **Hearth (report only, 07 §10 style).** `test_isa_identity` silently drops an ISA whose engine
  raises `HearthError` (`test_golden_invariants.py:131-132`). On a CI machine without AVX-512 the
  AVX-512 path then goes unchecked, while the test still passes.

---

## 16. Cost and calendar [inference]

- **Money and hours.** $1–3k and about 20 owner hours (ROADMAP §3.4). The owner-hour split is in
  §10.
- **Quiet hours** (§8.7, with t_run = 13 s micro and 15–40 s decode [inference]). About 5–18 h
  expected at true parity for σ_d = 1–4%, including a 1.4–2.2 h pilot; about 7–26 h at a true ratio
  of 0.99; about 19–72 h in the worst case, every configuration through the full inconclusive path
  [S + D]. These replace the draft's 9–24 h and 23–79 h, which used a 120 s decode run and an assumed
  overhead factor.
- **Calendar.** Sprint weeks, from ROADMAP §2:

  | Week | Work |
  |---|---|
  | 1 | Meaning, IR, checker, scalar variant; meaning freeze at week end |
  | 1.5–2.5 | AVX2 and AVX-512 schedules, lane program, printer, instruction validation, planted suite |
  | ≤ start of 3 | T_start |
  | 3–4 | Tuning, with daytime exploratory timing |
  | 4.5–5 | Window close, re-verification, pilot, confirmatory nights |
  | 5–6 | Report; Gatekeeper verdict in week 6 |
  | 5–7+ | Only if some configuration is inconclusive at N: gap attribution, a 7-day window, a second N. Reported in week 6 as "amber (b) pending" with the scheduled date (§8.6, §14 Q16) |

- **Owner decisions needed** (D0 brief §2):
  - D0-10d, the quiet windows, before the pilot;
  - D0-12, sign-off before the pilot and the A/B;
  - D0-7a, unattended night measurement;
  - D0-10a, the budget;
  - D0-3 for the comparator lineage. Provisional use of `b5d3f14` until then.

  X3 needs neither D0-1 nor D0-2: these kernels call no transcendental.

---

## 17. Review log

| Date | Reviewer lens | Family | Findings (blocker / major / minor) | Accepted | Rejected |
|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1: statistics, measurement protocol, quiet-hour cost, calendar | Claude (same family as author; independent context) | 1 / 9 / 5 | 15 | 0 |
| 2026-10-16 | Reviewer 2: checker soundness (C1–C4), instruction semantics, toolchains, Exo classification, test oracle | Claude (same family as author; independent context) | 0 / 3 / 6 | 9 | 0 |
| **Total** | | | **1 / 12 / 11 = 24** | **24** | **0** |

The reviser (same family, a third independent context) checked every finding against the sources
before applying it: Hearth b5d3f14 (`CMakeLists.txt`, `quant_avx2.c`, `quant_avx512.c`, `quant.c`,
`hx_quant.h`, `hearth.h`, `test_quant.c`, `platform_common.inc`), ROADMAP §1, §3.4, §3.5, §3.7 and
§10, 06 §6–§7, 03 §6.3–§6.4, X0's `TOOLCHAINS.md`, the reviser's simulation (§8.8) and its Python
probes (§5.1). All 24 findings were accepted, so there are no rejection lines. Two were refined and
one carried a citation slip:
- **Reviewer 1, finding 1 (blocker).** The reviewer proposed c_pass from the pilot's 99th percentile
  with a floor of 3·σ̂_AA, and c_reg ≥ 0.25 for the regression tests. A 3σ̂ floor alone is unsound at
  small σ: at σ_d = 1% it puts the clip at about β, which empties the pass test's null. The floor is
  therefore θ97 + 3σ̂ (§8.5). Keeping c_reg ≥ 0.25 left R90 at a true ratio of 0.85 out of reach
  within N at σ_d ≤ 2%, even with the 0.9 cap: a clamp about 0 allows at most
  ln(1 + 0.9 × 0.057/0.355) ≈ 0.135 of log-wealth per block, so at least 22 blocks against N's 18
  [D]. The regression clamps are therefore centred on each boundary (§8.5), and §14 Q18 asks the
  Owner to confirm that estimand.
- **Reviewer 1, finding 14 (clang-cl flags).** Partly superseded by X0's measurements. clang-cl's
  `/O2` already expands to `-O3`, so the suggested `/clang:-O3` is unnecessary. The contraction
  (`-ffp-contract=on`), the `haswell` and `skylake-avx512` targets and the missing VNNI are
  confirmed by X0 [M, X0 track] (§6). The bracket arm keeps `/clang:-ffp-contract=off` and adds
  GNU-style features.
- **Reviewer 1, finding 5 (timed segment).** The substance stands; the citation does not quite:
  `hearth_stats.wall_s` is at `hearth.h:105` at b5d3f14, not `:101`. §8.3 cites the verified line.

What changed, by finding:

| Reviewer, finding | Change |
|---|---|
| R1-1 (blocker): the capped bettor cannot reach 20 within N | Two clips and estimands, caps of 0.9, pseudo-observations from the pilot; `oc_sim.py` replaces the oracle-bettor check (§8.5, §8.8, Appendix C). Verified: the draft gives P(Pass \| parity) = 0.000 in the first N at σ_d ≤ 2% [S] |
| R1-2: gate-level power not stated | Gate-level table and a [target] P(gate Pass \| parity) ≥ 0.8 after the full path (§8.8; prereg §6) |
| R1-3: fresh e-processes double α | Wealth carried forward at threshold 20; the α-split alternative is §14 Q17; tombstone `fresh_eprocess_on_retest` |
| R1-4: the fallback's provisional pass is never checked | PASS-PROVISIONAL and amber (d); no decision before 6 blocks; ≥ 10 runs per arm is a floor only (§8.5, §8.6, §11) |
| R1-5: common work inside the timed segment | Timed segment defined as two clock reads around the R calls; traces only in separate runs, ≤ 4 KiB; decode timed by `wall_s`, with hashing outside it (§8.2, §8.3) |
| R1-6: load-gate units; the SMT sibling never checked | Per-LP rules, sibling and same-CCD voids, sampler and supervisor on a CCD1 LP, HIGH priority, LP ids recorded (§8.2, §8.4, Appendix B) |
| R1-7: the trend test is a bare p-value on pooled times | Per-configuration normalisation, stratified Mann–Kendall plus Sen slope; void only if p < 0.01 and the drift exceeds 2% (§8.4) |
| R1-8: decode t_run undefined | t_run = the pilot's median block wall time ÷ 4; hours recomputed with 13 s micro and 15–40 s decode runs (§8.5, §8.7) |
| R1-9: the inconclusive path cannot finish by week 6 | "amber (b) pending" status; §14 Q16; a calendar row (§8.6, §16) |
| R1-10: per-binary layout artefacts | K = 3 link-order variants drawn per block; equal-length paths and a fixed environment; a "layout-sensitive" label (§6, §8.2, §8.4, §8.6) |
| R1-11: stopping details | Session-end evaluation; precedence R90 > R97 > Pass; no Pass after R97; clips frozen at the confirmatory start; the sentinel bettor; the calibration envelope; the block formula with positions (§8.4, §8.5); tombstone `void_on_estimand_conflict` |
| R1-12: overhead factor; 165 → 166 | Overhead derived from the schedule; the slip noted; the table replaced (§8.7) |
| R1-13: clock probe before the run only | Probe before and after; void at 1.5% drift within a run or 3% from the session median (§8.4) |
| R1-14: clang-cl proxy flags | X0's measured facts in §6 and §8.1; a shared VNNI flag; a conditional shared contraction fix; the B-gnu bracket arm; §14 Q8 |
| R1-15: decode guard details | ISA and thread-count assertions; `cache_gb` in GiB from `expert_bytes`; a pilot zero-miss check ≥ 95% (§8.3) |
| R2-1: the lane map is not tied to addresses | Address-derived leaf names; mandatory but untrusted lane maps; a value-carrying C4 over every tail width and over T = 0 and r0 = r1; planted cases 26–28 (§4.3, §4.5, §5.2) |
| R2-2: C1's order check over loop nests; accumulator aliasing | C1 restated over each chain's visit sequence; FP-carried loops defined and never interchanged; an injectivity check; planted cases 16–19 (§4.2, §4.3, §4.5) |
| R2-3: C3 is not a polynomial identity for abs/sign and 16-bit shifts | A bit-vector layer with per-lane enumeration of ≤ 2^16 cases and a ring layer with the sign lemma; the accept half made concrete (the six hand kernels); planted cases 20–22 (§4.3, §4.5) |
| R2-4: clang-cl contraction in scalar expressions | Printer rule 5 with a self-check; X0's contraction facts recorded (§5.1, §6) |
| R2-5: P13's canon lowering against P15's BLENDV rule | A lifting rule; exactly one canon per path in C1; planted cases 23–25 (§4.2, §4.3, §4.5) |
| R2-6: Exo classification | `inline_assign` and `set_memory` moved to C; `stage_mem(accum=False)` marked unverified; tally 32 A, 13 C, 8 B; the caveat carried into the tombstone (§2.3, §13) |
| R2-7: binary32 emulation in Python | `rne_f32` specified; the `struct` failure modes measured; the double-rounding argument tagged [inference] (§5.1) |
| R2-8: corpus inputs break P1 and P2 | Activation codes and sums come only from the scalar `act_quantize_q8`; special values only in W's bytes, W.d and A.d (§7 step 6) |
| R2-9: scalar h2f | One named multi-op entry, `scalar.h2f_bits`, validated bit for bit over 65,536 inputs and counted under I (§5.1, §9.1) |

This review's independence is weaker than ROADMAP asks: the author, both reviewers and the reviser
are all Claude models (m0/README).

---

## Appendix A. `count_lines.py` (draft)

This becomes `experiments/x3-generator/scripts/count_lines.py`. It is the scratch copy that produced
§9.2. The Python LOC counter for S, which uses `black` and `tokenize`, is still to be written. It
lands with the script before freeze.

```python
"""x3 line counter. X3-LOC-C: a physical line counts iff, after deleting C comments (respecting
string/char literals), it has a non-whitespace character. Closure: roots = dispatched Q8/Q4 table
entries of one file, plus every top-level function or #define of the same file named in a member,
transitively. Header names and the hx_kernels initializer are excluded."""
import hashlib, json, re, sys
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|0[xX][0-9a-fA-F]+[uUlL]*|\d+\.?\d*(?:[eE][+-]?\d+)?[fFuUlL]*"
                   r"|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|<<=|>>=|->|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\|"
                   r"|[-+*/%&|^~!<>=?:;,.()\[\]{}#]")

def strip_comments(src):
    out, i, n, mode = [], 0, len(src), None
    while i < n:
        c = src[i]
        if mode is None:
            if src.startswith("/*", i): mode, i = "block", i + 2; continue
            if src.startswith("//", i): mode, i = "line", i + 2; continue
            if c in "\"'": mode = c
            out.append(c)
        elif mode == "block":
            if src.startswith("*/", i): mode, i = None, i + 2; continue
            if c == "\n": out.append("\n")
        elif mode == "line":
            if c == "\n": mode = None; out.append("\n")
        else:
            out.append(c)
            if c == "\\" and i + 1 < n: out.append(src[i + 1]); i += 2; continue
            if c == mode: mode = None
        i += 1
    return "".join(out)

def items(text):
    lines, res, i = text.split("\n"), {}, 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"#define\s+([A-Za-z_]\w*)", ln)
        if m: res[m.group(1)] = ("macro", [ln]); i += 1; continue
        if ln and (ln[0].isalpha() or ln[0] == "_") and not ln.startswith(("typedef", "#")):
            j, depth, opened = i, 0, False           # end where brace depth returns to 0
            while j < len(lines):
                depth += lines[j].count("{") - lines[j].count("}")
                opened = opened or "{" in lines[j]
                if (opened and depth == 0) or (not opened and lines[j].rstrip().endswith(";")): break
                j += 1
            block = lines[i:j + 1]
            head = " ".join(block).split("{", 1)[0]
            if "(" in head and "=" not in head:
                res[IDENT.findall(head.split("(", 1)[0])[-1]] = ("func", block)
            i = j + 1; continue
        i += 1
    return res

def closure(defs, roots):
    seen, todo = set(), list(roots)
    while todo:
        n = todo.pop()
        if n in seen or n not in defs: continue
        seen.add(n)
        todo += [x for x in IDENT.findall("\n".join(defs[n][1])) if x in defs and x not in seen]
    return sorted(seen)

def count(path, roots):
    raw = open(path, "rb").read()
    defs = items(strip_comments(raw.decode("utf-8")))
    mem = closure(defs, roots)
    return {"file": path.split("/")[-1], "sha256": hashlib.sha256(raw).hexdigest(), "members": mem,
            "loc": sum(1 for n in mem for l in defs[n][1] if l.strip()),
            "tokens": sum(len(TOKEN.findall("\n".join(defs[n][1]))) for n in mem)}

if __name__ == "__main__":
    src = sys.argv[1]
    plan = [("quant.c", ["mm_q8_scalar", "mm_q4_scalar"]), ("quant_avx2.c", ["mm_q8_avx2", "mm_q4_avx2"]),
            ("quant_avx512.c", ["mm_q8_avx512", "mm_q4_avx512"])]
    out = [count(src + "/" + f, r) for f, r in plan]
    print(json.dumps(out, indent=1))
    print("H_simd_loc", out[1]["loc"] + out[2]["loc"], "H_simd_tok", out[1]["tokens"] + out[2]["tokens"])
```

The listing above is reformatted for length. Its byte hash therefore differs from the scratch copy's
`69c6c3fd…`, but the logic is the same. The committed script is the reference, and the report
re-runs it.

## Appendix B. Run and verdict record schemas

```json
{ "run": { "session": "s-…", "block": 17, "config": "msvc/avx512/q4/micro", "arm": "A|B|A'", "pos": 1,
           "pair": 1, "kind": "ab|aa_cal|aa_sentinel|pilot|trace", "attempt": 1, "start_utc": "…",
           "end_utc": "…", "time_s": 10.02, "reps": 1331000, "weight_bytes": 522240,
           "output_sha256": "…", "expected_sha256": "…",
           "layout_variant": 2, "binary_sha256": "…", "exe_path_len": 31, "env_block_sha256": "…",
           "lp": 4, "lp_sibling": 5, "ccd": 0, "sampler_lp": 30, "priority_class": "HIGH",
           "load_pre_machine_pct": 0.4, "load_mean_machine_pct": 0.9, "load_max_machine_pct": 3.1,
           "sibling_max_pct": 0.2, "ccd_other_max_pct": 1.7, "defender_max_pct_of_lp": 0.0,
           "indexer_max_pct_of_lp": 0.0, "probe_pre_rate": 1.0003, "probe_post_rate": 0.9991,
           "profile_hash": "…", "void": false, "void_reason": null,
           "decode": { "tokens": 256, "wall_s_delta": 11.7, "segment_ns": 11712000000,
                       "cache_miss_delta": 0, "isa": 3, "n_threads": 16, "cache_gb": 15.8,
                       "logits_seq_sha256": "…" } } }
```

```json
{ "session": { "id": "s-…", "compiler": "msvc", "run_type": "micro", "attempt": 1,
               "calibration": { "m": 12, "sigma2_cal": 0.0003, "chi2_stat": 9.1, "chi2_crit": 26.217 },
               "sentinel_e": 1.8, "trend": { "mk_p": 0.21, "sen_slope_per_h": 0.002, "span_h": 1.2 },
               "median_envelope_ok": true, "void": false, "void_reasons": [] } }
```

```json
{ "verdict": { "record_commit": "…", "x4_state": "live_calibrated|live_uncalibrated|fallback",
               "noninferiority_calibration": "passed|pending|failed",
               "pilot": { "msvc/micro": { "sigma_aa": 0.018, "q99": 0.041, "c_pass": 0.084, "a_reg": 0.072,
                                          "t_run_s": 13.1, "n": 6, "L": 18 } },
               "oc_at_pilot_sigma": { "script_sha256": "…", "p_gate_pass_parity_full_path": 0.99 },
               "configs": { "msvc/avx512/q4/micro": { "state": "PASS|PASS_PROVISIONAL|R97|R90|INCONCLUSIVE|INCONCLUSIVE_PENDING|NO_VARIANT",
                     "attempts": 1, "schedule_hashes": ["…"], "K": 31.2, "M97": 0.4, "M90": 0.1,
                     "decided_at_block": 12, "ab_blocks": 12, "N_blocks": 18, "wall_hours": 0.21,
                     "estimand_conflict": false, "ratio_point": 0.996, "ratio_unclipped": 0.995,
                     "ratio_point_by_layout": [0.995, 0.997, 0.996], "layout_sensitive": false,
                     "outliers_slow": 0, "outliers_fast": 0 } },
               "S_loc": 41, "H_loc": 303, "S_tok": 402, "H_tok": 4188, "x2_ready": false, "t1": null,
               "banned_primitive_uses": 0,
               "outcome": "PASS|AMBER(a|b|b-pending|c|d)|KILL(a|b)", "reasons": ["…"] } }
```

The numbers in these schemas are placeholders that show types. They are not results.

## Appendix C. `oc_sim.py`, the operating-characteristics simulator

This becomes `experiments/x3-generator/scripts/oc_sim.py`, frozen with the record. It produced §8.8
(scratch copy SHA-256 `7b9162e9a1159567ff59884458ebe54b1d46b62e1da7606896deac2c5293ab33`, run as
`python -I oc_sim.py 3000 20261016 MODE` for each mode). Unlike Appendix A's listing, this one is
byte-identical to the scratch copy. After the pilot, the verdict pipeline re-runs it at the measured
σ̂_AA (§8.6, §8.8).

```python
"""oc_sim.py: operating characteristics of X3's sequential tests (DESIGN §8.5; prereg §6-§7).

Standard library only; deterministic for a given (reps, seed). It simulates the pre-registered
procedure, not an idealised bettor:
  pilot A/A blocks -> sigma_hat (RMS about 0), Q99|d|, c_pass, a_reg, n = max(6, ceil(12 s^2/delta^2));
  L = round(limit_mult * n) A/B blocks per N (limit_mult = 3 is the N = 2 x 1.5 x n reading);
  sessions of n A/B blocks; decisions only at session ends and only from block 6 on;
  K (pass, loss-scored clip, pseudo-mean beta), M97 and M90 (centred clamps, pseudo-mean 0);
  aGRAPA bets capped at 0.9 / (worst-case loss per unit bet);
  precedence R90 > R97 > Pass; once R97 has fired, Pass is unavailable;
  inconclusive path: one more L-block budget with every wealth carried forward.
Block statistic d = mu + noise, mu = -ln(rho), rho = true throughput ratio B/A.
design="draft" reproduces the DRAFT reviewed on 2026-10-16 (clip max(0.25, 2 max|d|), caps 0.5,
symmetric clamp about 0, pseudo-variance c^2/4).
Usage: python -I oc_sim.py REPS SEED MODE      MODE in: main draft zeroprior contam skew skewpos
                                                decode limit2
Prints one JSON line per scenario.
"""
import json
import math
import random
import sys

DELTA = 0.03
BETA = math.log(1.03)            # 0.029558802, pass-test boundary on the time scale
TH97 = -math.log(0.97)           # 0.030459207
TH90 = -math.log(0.90)           # 0.105360516
LOG_E = math.log(20.0)           # e-value threshold 20
MIN_BLOCKS = 6
CAP_FRAC = 0.9                   # bet cap = 0.9 / (worst-case loss per unit bet): wealth factor >= 0.1


def q99(xs):
    """Empirical 0.99 quantile, linear interpolation (type 7)."""
    s = sorted(xs)
    h = (len(s) - 1) * 0.99
    lo = math.floor(h)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (h - lo) * (s[hi] - s[lo])


class AGrapa:
    """W_t = prod_{j<=t} (1 + lam_j * v_j) with lam_j predictable:
    lam_{t+1} = clip(m_t / (s2_t + m_t^2), 0, cap), with one pseudo-observation (m0, s0sq):
      m_t  = (m0 + sum_{j<=t} v_j) / (t + 1)
      s2_t = (s0sq + sum_{j<=t} (v_j - m_t)^2) / (t + 1)
    crossed_at = first t >= MIN_BLOCKS with W_t >= 20."""
    __slots__ = ("m0", "s0sq", "cap", "t", "sv", "svv", "logw", "crossed_at")

    def __init__(self, m0, s0sq, cap):
        self.m0, self.s0sq, self.cap = m0, s0sq, cap
        self.t, self.sv, self.svv, self.logw, self.crossed_at = 0, 0.0, 0.0, 0.0, None

    def lam(self):
        t = self.t
        m = (self.m0 + self.sv) / (t + 1)
        ss = self.svv - 2.0 * m * self.sv + t * m * m
        den = (self.s0sq + ss) / (t + 1) + m * m
        return 0.0 if den <= 0.0 else min(max(m / den, 0.0), self.cap)

    def step(self, v):
        self.logw += math.log1p(self.lam() * v)
        self.t += 1
        self.sv += v
        self.svv += v * v
        if self.crossed_at is None and self.t >= MIN_BLOCKS and self.logw >= LOG_E:
            self.crossed_at = self.t


def draw(rng, mu, sigma, contam, side):
    """Gaussian block noise; with probability contam an extra N(0, (5 sigma)^2) outlier term,
    symmetric (side 0), one-sided making B look faster (side -1) or slower (side +1)."""
    d = rng.gauss(mu, sigma)
    if contam and rng.random() < contam:
        e = rng.gauss(0.0, 5.0 * sigma)
        d += e if side == 0 else side * abs(e)
    return d


def one_rep(rng, rho, sigma, m_pilot, contam, side, design, k_prior, limit_mult):
    mu = -math.log(rho)
    aa = [draw(rng, 0.0, sigma, contam, side) for _ in range(m_pilot)]
    s_hat = math.sqrt(sum(x * x for x in aa) / m_pilot)
    if design == "draft":
        c = max(0.25, 2.0 * max(abs(x) for x in aa))
        c_pass = a_reg = c
        cap_k, cap97, cap90 = 0.5 / (c - BETA), 0.5 / (c + TH97), 0.5 / (c + TH90)
        s0 = c * c / 4.0
    else:
        q = q99([abs(x) for x in aa])
        c_pass = max(q, TH97 + 3.0 * s_hat)          # loss-scored clip of the pass test
        a_reg = max(q, 4.0 * s_hat)                  # half-width of the centred regression clamps
        cap_k, cap97, cap90 = CAP_FRAC / (c_pass - BETA), CAP_FRAC / a_reg, CAP_FRAC / a_reg
        s0 = s_hat * s_hat
    n = max(MIN_BLOCKS, math.ceil(12.0 * s_hat * s_hat / (DELTA * DELTA)))
    L = int(round(limit_mult * n))
    K = AGrapa(BETA if k_prior == "beta" else 0.0, s0, cap_k)
    M97 = AGrapa(0.0, s0, cap97)
    M90 = AGrapa(0.0, s0, cap90)
    state, sessions, blocks, attempt, budget = None, 0, 0, 1, L
    while True:
        b_s = min(n, budget - blocks)
        if b_s <= 0:
            if state is None and attempt == 1:      # inconclusive: one more N, wealth carried
                attempt, budget = 2, budget + L
                continue
            break
        sessions += 1
        for _ in range(b_s):
            d = draw(rng, mu, sigma, contam, side)
            x = d if abs(d) <= c_pass else c_pass    # outliers scored as losses for B
            K.step(BETA - x)
            if design == "draft":
                xs = min(a_reg, max(-a_reg, d))
                M97.step(xs - TH97)
                M90.step(xs - TH90)
            else:
                M97.step(min(a_reg, max(-a_reg, d - TH97)))
                M90.step(min(a_reg, max(-a_reg, d - TH90)))
            blocks += 1
        if M90.crossed_at is not None:               # session-end evaluation
            state = "R90"
            break
        if M97.crossed_at is not None:
            state = "R97"                            # Pass unavailable; R90 may still fire by N
            continue
        if K.crossed_at is not None:
            state = "PASS"
            break
    return (state or "INCONCLUSIVE"), attempt, blocks, sessions, n, c_pass, a_reg


def scenario(reps, seed, rho, sigma, m_pilot=20, contam=0.0, side=0, design="final",
             k_prior="beta", limit_mult=3.0):
    rng = random.Random(seed)
    cnt, pass_blocks, ns, cps, ars = {}, [], [], [], []
    tot_blocks = tot_sessions = pass1 = 0
    for _ in range(reps):
        st, att, b, s, n, cp, ar = one_rep(rng, rho, sigma, m_pilot, contam, side, design,
                                           k_prior, limit_mult)
        key = st + "@" + str(att)
        cnt[key] = cnt.get(key, 0) + 1
        tot_blocks += b
        tot_sessions += s
        ns.append(n)
        cps.append(cp)
        ars.append(ar)
        if st == "PASS":
            pass_blocks.append(b)
            pass1 += att == 1
    pass_blocks.sort()
    med = lambda v: sorted(v)[len(v) // 2]
    return {"rho": rho, "sigma_d": sigma, "m_pilot": m_pilot, "contam": contam, "side": side,
            "design": design, "k_prior": k_prior, "limit_mult": limit_mult, "reps": reps,
            "seed": seed, "P": {k: round(v / reps, 4) for k, v in sorted(cnt.items())},
            "P_pass_attempt1": round(pass1 / reps, 4),
            "P_pass_total": round(len(pass_blocks) / reps, 4),
            "median_blocks_at_pass": pass_blocks[len(pass_blocks) // 2] if pass_blocks else None,
            "mean_ab_blocks": round(tot_blocks / reps, 2),
            "mean_sessions": round(tot_sessions / reps, 2),
            "median_n": med(ns), "median_c_pass": round(med(cps), 4), "median_a_reg": round(med(ars), 4)}


RHOS = (1.00, 0.99, 1 / 1.03, 0.97, 0.95, 0.90, 0.85, 0.80)

if __name__ == "__main__":
    reps, seed, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    runs = []
    if mode == "main":
        runs = [dict(rho=r, sigma=s) for s in (0.01, 0.02, 0.04) for r in RHOS]
    elif mode == "draft":
        runs = [dict(rho=r, sigma=s, design="draft", k_prior="zero")
                for s in (0.01, 0.02, 0.04) for r in (1.00, 0.95, 0.85, 0.80)]
    elif mode == "zeroprior":
        runs = [dict(rho=r, sigma=s, k_prior="zero") for s in (0.01, 0.02, 0.04) for r in RHOS[:4]]
    elif mode in ("contam", "skew", "skewpos"):
        side = {"contam": 0, "skew": -1, "skewpos": 1}[mode]
        runs = [dict(rho=r, sigma=0.02, contam=0.05, side=side) for r in RHOS]
    elif mode == "decode":
        runs = [dict(rho=r, sigma=s, m_pilot=10) for s in (0.01, 0.02, 0.04)
                for r in (1.00, 0.99, 1 / 1.03, 0.97, 0.90)]
    elif mode == "limit2":
        runs = [dict(rho=r, sigma=s, limit_mult=2.0) for s in (0.01, 0.02, 0.04)
                for r in (1.00, 0.99, 1 / 1.03, 0.97, 0.95, 0.85, 0.80)]
    for i, kw in enumerate(runs):
        print(json.dumps(scenario(reps, seed + i, **kw)), flush=True)
```
