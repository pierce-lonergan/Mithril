# X2: the `numerics_v1` mutant pool and the kill-rate protocol

Status: DESIGN, DRAFT, revised 2026-10-16 after two same-family reviews (review log in
[TABLE-SCHEMA.md §15](TABLE-SCHEMA.md#15-review-log)). No mutant has been generated. ROADMAP §3.3
asks for a pool of at least 200 mutants [target, P2 §10] covering FMA contraction, lane count and
tree shape, RNE→trunc, the 127→128 clamp, a dropped scale, a tie flip, removed NaN
canonicalisation, the NEOX/GPT-J RoPE swap and a commute before MAXPS, with kill rates measured under
goldens alone (G), goldens plus contributor tests (G+C) and T1+T2, and an honest-reporting rule. The
same pool serves ROADMAP §7 B1 ("T1+T2 kill at least as many mutants as G+C, plus at least one class
G misses") and the M2 gate. Tags as in [TABLE-SCHEMA.md](TABLE-SCHEMA.md).

---

## 1. Units (fixed before any mutant exists)

- **Mutant.** One local source edit to Hearth at b5d3f14, applied to a scratch copy: (operator ID,
  file, line, column, original text, replacement text), stored as a unified diff. One edit per
  mutant; no higher-order mutants in v1. A change of compiler flags is not a source edit: the
  whole-file flag mutants of v0 (`/fp:contract`, `-ffp-contract=fast`) leave the transliterated IR
  unchanged, so they are **not in `numerics_v1` for X2** (finding R2-3). They are listed, built and
  reported only, as evidence for X0's P2 screen and the M2 object audit.
- **Host function.** The function the edit lands in. Hosts: the 18 dispatched variants (`quant.c`
  scalar table, `k_avx2`, `k_avx512`) with their inlined helpers, and the canonical scalar helpers
  in `quant.c` that NUMERICS §4 defines (`hx_sum16`, `hx_dot16`, `hx_rmsnorm`, `hx_softmax`,
  `hx_swiglu`, `hx_sigmoid`, `hx_rope`, `hx_axpy`). `hx_rope` is in scope because the RoPE-swap
  class needs it. Quantisers (`quantize_q8`, `quantize_q4`) are out of scope for T1 (they are not
  kernels) and are excluded from the pool. **Host groups:** *gating* (the 8 variants of prereg §4.1
  and their inlined helpers), *A4* (the 6 scalar and 4 F16/BF16 SIMD variants), *helpers* (`hx_*`).
  Which groups enter P3's denominator was Owner question 8 of the prereg; **option (b)** is fixed (DELEGATED
  P31, 2026-10-23; Pierce reviews at sitting 2): every group, with T1 run on every host (finding R2-2; §6).
- **Stillborn.** A mutant that fails to compile under X0 configuration A (MSVC `cl` 19.44.35229,
  toolset 14.44.35207, SDK 10.0.26100.0, as pinned in `experiments/x0-census/TOOLCHAINS.md`) or D
  (Clang 23.1.3, same file) with Hearth's flags. Counted and listed, then excluded from every rate.
- **Declared domain.** The domain predicates of [RULES.md §4.0](RULES.md#40-domain-predicates-numbered-checkable-finding-r1-2):
  any bit patterns for f32/f16/bf16 inputs and weights and any bytes in Q8/Q4 blocks (DOM-W);
  activation blocks satisfying **DOM-ACT-Q** (every `q[i] ∈ [−127, 127]`) and **DOM-ACT-SUM**
  (`sum = Σ q[i]` as int32); MXCSR = 0x1F80 at entry (DOM-ENV, a declared precondition pending
  D0-5b); the shape and non-overlap facts (DOM-SHAPE). v0 defined the activation domain by
  provenance ("produced by `act_quantize_q8`"), which no checker can evaluate (finding R1-2).
- **FP-changing (WITNESSED), defined at intrinsic level.** There is an input in the declared domain
  on which the **table-semantics evaluation of the mutated transliterated IR** differs from that of
  the unmutated IR in observable output bytes (`Y` rows, and `hx_act_q8` blocks `d`, `sum`, `q`), and
  the difference is **confirmed natively** on the 9950X with the pinned build (configuration A,
  Hearth's flags). The witness is stored with both outputs.
- **Level-divergent.** The native run and the table evaluation disagree about whether the mutant
  changes the output. The comparator assigns a cause before the verdict:
  - *object level*: the compiled mutant's instruction sequence (decoded by X0's tools) differs from
    its transliteration, for example a contraction or reordering the compiler introduced. The mutant
    is **level-divergent**: reported with its cause and forwarded to X0 and M2. **If its table-semantics
    evaluations differ at intrinsic level** while the native build does not show the difference, it **counts
    as FP-changing and stays in P3's denominator** with its intrinsic-level witness (the native confirmation
    above is waived for it, and its absence is reported): T1 judges intrinsic-level IR and must reject it.
    Only a mutant that is **not** FP-changing at intrinsic level (its native difference comes from the
    compiled object alone) is outside P3; if T1 accepts it, prereg §4 item 6 decides whether that is a false
    accept (strict reading registered; the carve-out is Pierce's, prereg §13 O4). Narrowed on
    2026-10-23 (review of the prereg's revision 3, finding 2): the earlier text excluded every object-caused
    level-divergent mutant, which could drop an intrinsic-level FP-changing mutant from "rejects 100%";
  - *table*: a table entry's prediction differs from silicon on a vector that reproduces the
    divergence. That is a table bug: the entry is fixed under A2, the mutant is re-classified under
    the fixed table, and if T1 had accepted it, that acceptance is handled as a false accept under
    prereg §4 items 6 and 7 (never excused by this classification);
  - *undetermined* by the verdict: counted as FP-changing (strict).
- **Equivalent (PROVED).** No input in the declared domain makes the table-semantics evaluations
  differ, shown by a route that does not use T1: exhaustive enumeration over the function's relevant
  input space, an SMT proof by a solver run outside `mithcheck`, or a written proof reviewed in an
  independent context. T1's acceptance is never evidence of equivalence (T1 is what is under test).
- **Unresolved.** Neither witnessed nor proved equivalent **at the verdict**. Counted as FP-changing
  for the T1 requirement. If T1 accepted an unresolved mutant, that mutant is a **T1 non-kill** at
  the verdict (P3 < 100%); it is not a false accept, because no witness exists. There is no waiting
  state (v0 said the verdict "waits", which could never end for a mutant that is unwitnessable at
  table level; finding R2-3).
- **Kill, with a recorded reason.** An arm kills a mutant if it reports failure.
  - G and C: a failing check, a nonzero exit, a crash or a timeout. A G or C kill counts only if it
    **reproduces in 2 of 2 runs**; crash and timeout kills are recorded separately from assertion
    failures (an out-of-bounds write may corrupt nondeterministically; finding R2-19).
  - T1+T2: any rejection, with its reason ∈ {`mismatch` (DAG or integer obligation), `footprint`,
    `mxcsr-write`, `unknown-entry` (no table entry for an instruction the mutant introduces),
    `special-entry` (an approximation such as RCPSS, excluded from exact kernels), `other`}. The
    first three are **semantic** kills; the last three are **structural** (finding R2-15).
  - A T1 kill counts only if T1 **accepts the unmutated host function**; otherwise every mutant of
    that host is "T1 not applicable" and counts as not killed.

## 2. Operator classes and site counts

Site counts are estimates from reading the b5d3f14 sources [G: X2 agents, 2026-10-16, not a
mechanical count]; the operator scripts produce the exact site lists, which are reviewed before the
pool is sealed. "Expected equivalent" marks operators whose sites are predicted equivalent at
intrinsic level [inference]; they stay in the pool as negative controls (T1 should accept them where
its rules reach, and a rejection is incompleteness, not a gate failure).

| ID | Class (ROADMAP name) | Operator | Sites (≈) | Notes |
|---|---|---|---|---|
| M-FMA | FMA contraction | `add(acc, mul(a, b))` → `fmadd(a, b, acc)` at every SIMD accumulate; `L + w*x` → `fmaf` in scalar; Q8/Q4 epilogue `acc + cvt(is)*(dw*dx)` → fused | 28 | the whole-file flag mutants moved to the reported-only list (§1) |
| M-TREE | lane count and tree shape | tree16: pairings (s = 1,2,4,8 order; adjacent pairs), `_mm512_reduce_add_ps`; 8 accumulator lanes instead of 16 in AVX2 (`lo` and `hi` merged); split accumulator (two partials per lane); sequential 16-lane sum | 25 | `_mm512_reduce_add_ps` gets an explicit halving-tree expansion in `intrinsic_map.v1` (Intel's documented reduction: pairs (j, j+8), (j, j+4), (j, j+2), (0, 1)), equal to `tree16`, so it is predicted equivalent at intrinsic level; how a compiler lowers it is M2's question |
| M-TRUNC | RNE→trunc | `cvtps_epi32` → `cvttps_epi32` (AVX2, AVX-512 act); `q_rint(v)` → `(float)(int)v` (scalar act) | 5 | |
| M-CLAMP | 127→128 clamp | `±127.0f` → `±128.0f` in the clamp (upper, lower, both) per act variant | 9 | equivalent except when `id = 1/d` overflows to +∞ (§5) |
| M-SCALE | dropped scale | drop `* a->d`, drop `dw`, `(dw * dx)` → `dw`; drop the `- sum * bias` correction | 16 | |
| M-REASSOC | FP product reassociation (new, finding R2-18) | epilogue `cvt(is)·(dw·dx)` → `(cvt(is)·dw)·dx` | 6 | AVX2 `qtile8` (two paths), AVX-512 `q16_step`, `qtile4`, scalar Q8, Q4; reassociation is on the never-list |
| M-TIE | tie flip | RNE → half-away (`cvttps(p + copysign(0.5, p))`); `q_rint` → `floorf(v + 0.5f)` | 8 | |
| M-NAN | removed NaN canonicalisation | drop `canon8` / `canon16` / `canon4` / `q_canon`; canonical constant `0x7fc00000` → `0xffc00000`; predicate `UNORD_Q` → `ORD_Q` in canonicalisation, `ORD_Q` → `UNORD_Q` in act zeroing | 16 | |
| M-ROPE | NEOX/GPT-J RoPE swap | `style == 1` test inverted; `ia`/`ib` swapped; sign of the `s` terms flipped | 5 | host `hx_rope` (helpers group); it calls `cosf`/`sinf`, so T1 needs the opaque-call premise of prereg §4 item 2(c) |
| M-MAXORD | commute before MAXPS | (a) swap MAXPS/MINPS operands: `max(\|v\|, m)` → `max(m, \|v\|)`, clamp min/max swaps; (b) commute an add/mul feeding a MAX/MIN or an un-canonicalised sink; (c) swap MAX operands inside `hmax8`/`hmax16` | 15 | (c) expected equivalent: NaN-free, sign-bit-0 operands (RULES.md R02/R03) |
| M-INIT | accumulator start (NUMERICS: from +0.0) | `setzero` → first product; `+0.0` → `−0.0` start | 10 | the Alive2 signed-zero class [R07 §2] |
| M-ORDER | group / rank order | reverse the block loop `g`; reverse the 16-lane fill order | 6 | |
| M-INT | integer exactness | `maddubs` operand order swapped; sign trick dropped; bias 8→7, 128→127; `xor 0x80` → `or 0x80`; `vpdpbusd` → `vpdpbusds`; `madd(add_epi16(..))` → saturating `adds_epi16` | 20 | `vpdpbusds` and `adds_epi16` expected equivalent under the T2 bounds |
| M-LANE | lane maps | permutation index off by one; `perm2x128` 0x20 ↔ 0x31; `unpacklo/hi` swapped in `red_quads`; `pshufd` 0x4E ↔ 0xB1 in `hsum` | 15 | the `hsum` swap is expected equivalent (integer sum) |
| M-TAIL | tails and footprint | `smask` and `tm` off by one; tail bound `rem` ± 1; row clamp `nr − 1` → `nr` | 12 | several write outside `Y`: they test T1's footprint check |
| M-MASK | masking (new, finding R2-18) | `maskz` ↔ `mask` merge (`maskz_mov` ↔ `mask_mov`); drop the mask of `maskz_loadu` (`x + n16` read past the array end); `mask_add` → `add` (garbage lanes); `maskstore` → `storeu` (write past `Y`); `mask_storeu` → `storeu` | 8 | the dropped-mask loads and stores test the footprint check and fault suppression (FUZZ-DESIGN F-MEMFAULT) |
| M-CVT | conversions | `cvtepi32_ps` → unsigned `cvtepu32_ps`; f16 path `cvtph_ps` → bf16-style shift; bf16 shift 16 → 15; `cvtepu16` → `cvtepi16` before the shift | 10 | the last is expected equivalent (sign bits shifted out); f16/bf16 sites land in `ld16` inside `mm_float`, so their hosts are A4 variants |
| M-RCP | reciprocal and division | `1/d` → `rcp_ss(d)`; `amax / 127` → `amax * (1/127.0f)`; `d != 0` → `d > 0` | 6 | `d > 0` expected equivalent (d ≥ 0 or NaN, and both branches then give q = 0); RCPSS is a special entry, so its kill reason is structural |
| M-ENV | FP environment | set FTZ, DAZ, RU or RZ at kernel entry (restored at exit) | 4 | T1 must reject: MXCSR written inside the kernel |
| M-NARROW | narrowing | `cvtepi32_epi8` → `cvtsepi32_epi8`; `packs_epi16` → `packus_epi16` | 4 | the first expected equivalent under \|q\| ≤ 127 |
| | | **Total** | **≈ 228** [G] | ≥ 200 [target] before stillborn removal; the operator script must reach ≥ 200 **live** mutants or add sites before sealing (the flag mutants never count toward the 200) |

**Instructions an operator can introduce.** `intrinsic_map.v1` (TABLE-SCHEMA §8.1) and the table
must cover every intrinsic any listed operator can introduce **before** the pool is sealed, so that a
kill is semantic where it can be: FMA (`VFMADD*PS/SS`), `VCVTTPS2DQ` (VEX entries added
2026-10-16), `VCVTUDQ2PS`, `VPDPBUSDS`, `VPADDSW`, `VPMOVSDB`, `VPACKUSWB`, the masked and
zero-masked move, load and store forms, and the `_mm512_reduce_add_ps` expansion. `RCPSS` stays a
special entry by design (TABLE-SCHEMA §4 rule 8). The operator list is public already, so adding
these entries leaks nothing about the sealed pool.

**Meaning-mutant control (new, finding R2-18).** About 10 edits to the meanings (KIR), for example
clamp 127 → 126, the sum16 tree order changed, the Q4 bias 8 → 7, `round_ne` → `round_tz`, the NaN
→ 0 select removed, run against the **unmutated** variants. T1 must reject every one: target 100%
[target, proposed, secondary]. A T1 that accepted a meaning mutant would not be comparing the code
with the meaning. Authored by the same Adversary context as the pool, sealed with it.

## 3. Generation against Hearth's sources

1. **Pin.** Hearth b5d3f14 (`a801d43…`), the three kernel files plus `hx_quant.h`. The desktop
   working tree's uncommitted R3 changes are out of scope (as in X0 §2).
2. **Operators as scripts.** Each operator is a small rewrite over the token stream of the
   intrinsic-C subset Hearth uses (calls `_mm*_…(…)`, constants, comparisons, loop bounds). It
   enumerates its sites and emits one diff per site. The script, its site list and the resulting
   pool are hashed.
3. **Authorship and sealing.** The pool is written by an Adversary context separate from whoever
   writes T1's rules (03 §8.1 roles; independence logged as same-family, independent-context until
   D0-10). Order of events, pre-registered: (i) the rewrite list `rules.v1` is frozen and hashed;
   (ii) the pool is generated and its hash recorded in the pre-registration's amendment log;
   (iii) only then is the pool revealed to T1. This stops rules being tuned to the pool.
4. **Build.** Each live mutant builds the Hearth engine under configuration A (for G and C; D is
   built and reported as secondary) and is transliterated into the spike's intrinsic-level IR by the
   same transliterator that handles the real variants (for T1), through the frozen
   `intrinsic_map.v1`. The transliterator is mechanical, so it does not depend on which mutant it
   sees; its correctness rests on T1 accepting the unmutated variants and on a spot check of 10% of
   mutant transliterations by diff against the source edit.
5. **Witness search** (to classify FP-changing vs equivalent): the targeted generators of
   FUZZ-DESIGN.md §3 adapted to kernel inputs (NaN in each position of a block, infinities, subnormal
   and tie blocks, every tail length 0-15, every row count mod 16), plus 10^5 random kernel calls per
   mutant, run natively and through the table semantics. For max-fold mutants (M-MAXORD) the
   generator is **chain-aware** (finding R1-1): for every lane chain c (8 for AVX2, 16 for AVX-512)
   and every position p in 0..63, the block maximum heads chain c, a QNaN sits at p, every other
   element is smaller; the derived rule `hearth_kernels.commute_max_visible` predicts the witnesses
   and the run confirms them.

## 4. The three arms

| Arm | What runs | Kill |
|---|---|---|
| **G** | `tests/golden/` at b5d3f14 (maintainer-owned, hash-locked by `MANIFEST.sha256`): engine vs numpy reference within tolerance, scheduling independence, batch = sequential, rewind, ISA identity end to end, kernel ISA and batch identity via `hearth_matmul`, malformed files | any failing test, reproduced in 2 of 2 runs |
| **C** | `engine/tests/*.c` (`test_quant`, `test_model`, …) and `tests/py/` at b5d3f14: contributor tests | any failing check or nonzero exit, reproduced in 2 of 2 runs |
| **G+C** | union | killed by G or by C |
| **T1+T2** | the `mithcheck` spike on the transliterated host function against its meaning (KIR transcribed from NUMERICS and the C scalar code) | any rejection, with its reason, provided T1 accepts the unmutated function |

**Builds.** G and C run on engine builds from **X0 configuration A** (MSVC `cl` 19.44.35229, toolset
14.44.35207, Hearth's own flags); configuration D builds are run and reported as a secondary
matrix (finding R2-19). All arms run on the 9950X, where all three ISAs execute. A mutant in a SIMD
variant is reachable by G and C only through the ISA-identity checks, which compare with the scalar
variant; a mutant in a scalar variant changes the reference those checks compare against, so G and C
see it only through the numpy tolerance tests and the independent NUMERICS reference inside
`test_quant.c`.

## 5. Witness analysis done so far [D: table-semantics simulation]

`semantics/hearth_kernels.py` transliterates `act_q8` (scalar, AVX2, AVX-512) from table operations,
and `selftest.py` section H runs five mutants on nine hand-built 64-element blocks (the ninth was
added on 2026-10-16 as a regression witness from review). All three unmutated variants agree on
every block. The blocks that distinguish each mutant [M] X2 agents, 2026-10-16, laptop:

| Mutant | Distinguishing blocks (of: gauss-like, nan-inf, nan-only, subnormal-scale, flt-max, ties, zeros, small-normal-scale, nan-erases-chain-max) | Reading |
|---|---|---|
| M-TRUNC (`cvtps` → `cvttps`) | gauss-like, nan-only, flt-max, ties, small-normal-scale | ordinary data witnesses it |
| M-TIE (half-away) | ties | needs exact .5 products |
| M-CLAMP (127 → 128) | subnormal-scale only | equivalent unless `id = 1/d` overflows to +∞, i.e. block `amax` below about 127 · 2^−128 ≈ 3.7 × 10^−37 [D]; the block with `amax = 10^−36` (d subnormal, id finite) does not witness it |
| M-NAN (ORD zeroing removed) | nan-inf, nan-only, nan-erases-chain-max | a NaN product becomes `min(NaN, 127) = 127` instead of 0 |
| M-MAXORD (a) (`max(m, \|v\|)`) | nan-only, nan-erases-chain-max | see below |

**When the commuted max is visible (corrected 2026-10-16, finding R1-1).** With `m = max(m, |v|)`,
a NaN at position p of lane chain c (AVX2: c = p mod 8; AVX-512: c = p mod 16) sets `m_c = NaN`. The
next element q of chain c sets `m_c = |x_q|`, because MAXPS returns its second source when the first
is NaN, so **every chain-c element before p is discarded**. The mutant is visible iff

- (i) the block maximum is in chain c before p, and nothing after p in chain c, and no other chain,
  reaches it; or
- (ii) p is the end of its chain, so the NaN enters `hmax8`/`hmax16`. Each tree step is
  `MAXPS(low half, high half)`: a NaN on the high (second-source) side propagates and absorbs its
  sibling; at the first step where it is on the low side, the step returns the sibling and every lane
  merged into the NaN so far is erased (`hearth_kernels.nan_tree_fate`). On AVX2, x[63] (lane 7)
  reaches the root, so `d` becomes NaN; x[62] erases lanes {0, 2, 4, 6}; x[61] erases {1, 5};
  x[60] erases {0, 4}; x[56..59] erase only their own lane, which (i) already covers. On AVX-512,
  x[63] reaches the root; x[62] erases the 8 even lanes; x[60] erases {0, 4, 8, 12}; x[56] erases
  {0, 8}; and so on.

v0 said only a NaN that is last in its chain matters, because "the next element of the same lane
chain overwrites it". That overwrite is the damage, not a repair. Reviewer 1's scan of one NaN over
positions 1..63 with the maximum at x[0] witnessed the mutant at AVX2 x[8, 16, 24, 32, 40, 48, 56,
60, 62, 63] and AVX-512 x[16, 32, 48, 56, 60, 62, 63] [M, reviewer 1, 2026-10-16, laptop]; the
reviser reproduced both lists [M, X2 reviser, 2026-10-16]. v0's "x[60], x[62] and x[63] and nowhere
else" was an artefact of where the maximum sat in its one random block. The derived rule
`commute_max_visible` agrees with table-semantics simulation on **all 1,536** (ISA, chain-head
maximum, NaN position) cases, 0 disagreements [M, X2 reviser, 2026-10-16, laptop, `selftest
--full`, about 15 s]; the default self-test checks 384 of them.

**Prediction for G and C, restated for the right reason [inference from the source].** Hearth's
`test_act_quant` places NaNs at x[1] and x[201]. x[1] heads its chain in both ISAs (k = 0), so
nothing precedes it. x[201] is local index 9 of block 3: AVX2 chain 1 at k = 1, which could erase
local x[1] = x[193], but x[200] = −∞ gives amax = +∞ in both versions; on AVX-512 it is chain 9 at
k = 0, a chain head. So `test_act_quant` alone misses the mutant. `test_nonfinite` draws a NaN for
about 1 in 40 activation elements [D: P(wild) = 1/4 × P(NaN | wild) = 1/10] over roughly 160
quantised cases × 3 blocks × 5.5 tokens ≈ 2,600 blocks [D from the source's loop bounds]; with NaNs
that frequent, condition (i) or (ii) holds in some block, so C is predicted to kill it [inference];
G's inputs are finite, so G is predicted to miss it [inference]. These are predictions, written down
before data.

**Golden blind spots visible in the source [inference, to be measured].** G's kernel test uses
`rows = 37, cols = 256, T = 5`, standard-normal data: no NaN, no infinity, no subnormal, no exact ties,
and `cols % 16 = 0`, so the float tail paths (`finish16`, the AVX-512 `tm` mask) never run under G.
G's end-to-end tests use tiny synthetic models with finite activations. G is therefore predicted to
miss M-NAN, M-MAXORD, M-CLAMP, M-TIE, the float-tail M-TAIL and M-MASK mutants and M-ENV (FTZ/DAZ
need subnormals); C covers each of those input classes somewhere (`fcols` includes 1, 5, 15, 17, …;
`K_TIES`, `K_TINY`, `test_nonfinite`, `test_half_all_values`). The likely honest outcome is
therefore "G+C ≈ T1 on kill rate; T1 gives the same assurance per build, from the code, without the
input-class engineering" (§7) [inference].

## 6. Metrics

Over the live, non-stillborn pool, excluding only the level-divergent mutants that are not FP-changing at
intrinsic level (§1):

- **Primary (gate, P3).** The T1+T2 kill rate over FP-changing mutants (WITNESSED plus UNRESOLVED),
  which must be 100% (ROADMAP §3.3). **Denominator: option (b), fixed by DELEGATED P31 (2026-10-23;
  Pierce reviews it at sitting 2):** every host group (gating, A4, helpers), with T1 run on every host; a
  host T1 does not accept makes its mutants non-kills. Option (a), which would restrict the denominator to
  the gating group and report the rest as a secondary matrix, is excluded: it would take M-ROPE out of the
  gate, a loosening. Under either option the pool
  requirement (≥ 200 live mutants, every ROADMAP class present) applies to the whole pool, and the
  number of live FP-changing mutants per host group is reported.
- **Primary (gate, P4).** The count of FP-changing mutants T1 accepts with a witness (false
  accepts), which must be 0 apart from table-traceable ones (prereg §4 items 6-7).
- **Secondary (reported).** Kill rates of G, C and G+C over the same set; per-class and per-host-group
  rates; the sets K_T ∖ K_GC, K_GC ∖ K_T and K_T ∖ K_G with their witness inputs; each computed
  **twice**: with all T1 kills, and with semantic kills only (mismatch, footprint, mxcsr-write;
  finding R2-15); T1's acceptance rate on PROVED equivalent mutants (completeness on negative
  controls); the meaning-mutant control's rejection rate; the number of UNRESOLVED and
  level-divergent mutants and how each was classified; G and C crash and timeout kills separately.
- **Cost (reported).** CPU seconds per build for G, C, and T1+T2 on the 9950X, measured on the
  unmutated build, three runs each, median.

## 7. Honest-reporting rule (ROADMAP §3.3, made operational)

Let K_T be the FP-changing mutants T1+T2 kills and K_GC those G+C kills. Every statement below is
evaluated twice, with all T1 kills and with semantic T1 kills only, and both readings are printed.

1. If K_T ⊆ K_GC, the report says **"stronger evidence per build at lower cost"**, never "catches
   more bugs", and gives the per-build cost of each arm. "Stronger" means: T1's verdict covers every
   input in the declared domain, G+C's covers the inputs they ran.
2. If K_T ∖ K_GC ≠ ∅, the report lists those mutants, their classes, kill reasons and witness inputs,
   and says for each whether a test that G+C lacks would have killed it (an input-class gap) or not.
3. K_GC ∖ K_T must be empty for a pass (any member is a false accept or a T1 non-kill). If it is not,
   the report leads with it.
4. B1's wording ("at least as many as G+C, plus at least one class G misses") is evaluated from the
   same sets and reported verbatim, pass or fail, under both readings.
5. A result is never re-scored with a different pool, a different unit or a re-classified mutant
   after the pool is revealed, except under an amendment marked post-data and reported both ways.

## 8. Cost [inference]

About 228 mutants × (one engine build, G, C) on the desktop, each G and C run twice for the
reproducibility rule: with a build in the order of a minute and `test_quant` plus the Python tests
in the order of minutes [G], about two to four daytime days of machine time, run outside quiet
windows (DR-023). T1+T2 time per mutant is expected to be seconds (KIR-sized DAGs) [G]. Writing and
reviewing the operator scripts, the meaning mutants and the witness search: about 4-6 agent-days and
5-7 owner hours of review [G]. Option (b) adds T1 transliterations and meanings for the 10 A4
variants and 8 helpers: about 2-4 agent-days [G].
