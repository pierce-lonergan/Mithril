# X3 meaning review (DESIGN §3.5)

Track: x3meaning · Written 2026-10-23 by the reviser (Claude, same family, independent context) ·
Status: **review done; fixes applied to `proto/`; the DESIGN body edits are proposed, not applied.**
The meaning is **not frozen**. Nothing here is gate data (prereg §4.9).

Tags as in [docs/m0/README](../../docs/m0/README.md#evidence-tags). "[M, reviewer]" marks the
reviewer's own measurements, quoted from the review; "[M]" without a name is the reviser's, on the
laptop (Ryzen 9 7940HS, Zen 4, Windows 11, Python 3.12.10, clang 23.1.3), 2026-10-23.

## 1. What was reviewed

DESIGN §3.5 asks for an independent check of the meaning against `NUMERICS.md` §3 and
`quant.c:388-427` before its hash is frozen, plus a meaning differential. The text under review was
[proto/x3gen/hearth/meaning.py](proto/x3gen/hearth/meaning.py) as committed at `e321593` (meaning
SHA-256 `aa7645c5…5f1d`), with DESIGN §3.3 and the interpreter's binary32 model
([proto/x3gen/core/fp32.py](proto/x3gen/core/fp32.py)).

| Reviewer | Lens | Family | Findings (blocker / major / minor) | Accepted | Rejected |
|---|---|---|---|---|---|
| Reviewer 1 | the meaning: formats, arithmetic, preconditions, the differential | Claude (same family as author; independent context) | 0 / 1 / 5, plus one result with no change asked | 7 | 0 |

A second reviewer looked at the checker in the same round; that review is logged in
[proto/README.md](proto/README.md#review-log).

## 2. Result: no transcription error

Reviewer 1 checked the meaning line by line against `NUMERICS.md:38-62`, `quant.c:16-35`, `:53-65`,
`:388-427` and `hx_quant.h:20-28`, `:49-57` at b5d3f14, and found no transcription error. Checked:
the formats, offsets and sizes; Q8 as signed int8 including −128; Q4 low nibble = element j, high
nibble = element j + 32, minus 8; the exact integer sum (|I| ≤ 1,040,384 < 2^24, so i2f is exact,
also at xq = −128); the operation order `(float)isum * (h2f(dw) * dx)`; `acc = acc + term` from
+0.0f; canon at the store; Y index t·ldy + r; row and token addressing. Every citation's line
numbers matched b5d3f14; P4's lines did not support its claim (finding 2).

Evidence [M, reviewer, laptop Zen 4, clang 23.1.3, configurations `clang_D_flags` and `clangcl_B`]:
inside the preconditions, 206 cases and 15,134 outputs, with NaN, signalling NaN, inf, subnormal,
−0 and maximal f16/f32 scales, Q8 codes −128 and 127, Q4 bytes 0x00, 0xFF and 0x0F, activations at
±127, T ∈ {0, 1, 2, 17, 18}, G ∈ {1, 2, 3, 7, 64, 128}, r0 > 0, ldy ∈ {r1, r1 − r0, r1 + 3}: the
interpreter, an independent oracle transcribed from NUMERICS, and all six kernels equal Hearth's
scalar kernel with 0 mismatching words. Outside the preconditions the meaning equals Hearth's scalar
kernel; at xq = −128 only the Q8 AVX2 kernels differ (Hearth's and x3's alike, 160 words); with a
wrong `sum` the bias-form kernels differ (180 words each); for n % 64 ≠ 0 the meaning refuses and
all six kernels truncate identically. Script and results: the review's scratch directory
(`scratchpad/x3meaning/adv.py`, `run_D/adv_result.json`, `run_B/adv_result.json`).

## 3. Findings and what changed

Every finding was re-checked by the reviser before it was applied.

| # | Severity | Finding | Verification | Change |
|---|---|---|---|---|
| 1 | major | P3 read "mxcsr == default" / "RNE, FTZ = DAZ = 0". Read literally it is false during normal runs (the precision flag is sticky), and it says nothing about the exception masks | Confirmed. MXCSR read during the default-mode corpus runs: 0x1FA0 (`clangcl_B`) and 0x1FBB (`clang_D_flags`, `clangcl_B_nocontract`) [M, `scripts/bitid.py`, `mxcsr_during_run`]; both satisfy the new predicate. The harness changes only RC, FTZ and DAZ and keeps every mask set | PRE3 = `"(mxcsr & 0xFFC0) == 0x1F80"`: RC = nearest, FTZ = DAZ = 0, all six exceptions masked, status flags (bits 0–5) unconstrained. Bits 16–31 are reserved and read as zero. A unit test evaluates the predicate on 0x1F80, 0x1FA0 and ten values that break one control bit each |
| 2 | minor | P4 was cited to `hx_quant.h:45-57`, but line 45 ("act may alias nothing") is about `hx_act_prepare`, and the slot contract (`:49-57`) has no aliasing clause | Confirmed by reading `hx_quant.h` at b5d3f14 (line 45 is the `hx_act_prepare` comment). Hearth's callers do pass separate buffers: `mm_set` (`model.c:341-352`) gets the weights, a prepared activation buffer (`m->xact` or `m->act`, `act_of` `:370-382`) and a scratch Y | PRE4 re-sourced as "[G] implicit in `hx_quant.h:49-57`; callers pass separate buffers", like PRE6. The condition is unchanged. The extents half of the old P4 is now its own string, "W and A readable, Y writable, over their extents" |
| 3 | minor | The checker enforced n ≥ 0, T ≥ 0 and 0 ≤ r0 ≤ r1 that the meaning text did not state; r1 ≤ rows(W) was stated nowhere; P1 lived only in a format field | Confirmed by reading `check.shape_ok` against `REQUIRES` | `REQUIRES` now has 9 strings under PRE1–PRE6, including `"n >= 0 and n % 64 == 0"`, `"T >= 0"` and `"0 <= r0 <= r1 <= rows(W)"` (PRE5) and `"A.q in [-127, 127]"` (PRE1). `check.shape_ok` now evaluates the shape conditions from that text (a whitelisted expression evaluator); every other string must be one the checker names how it carries, and PRE1's range must equal the activation format's, or the checker refuses the meaning. Unit tests cover each shape condition and both refusals |
| 4 | minor | The differential could not see canon: `fp32.fadd`/`fmul` returned 0x7FC00000 for every NaN, so a meaning without canon matched Hearth bit for bit | Confirmed by reading `fp32.py`; the reviewer measured 0 differing words for a canon-less meaning [M, reviewer] | `fp32` follows the x86 SSE/AVX NaN rules: a NaN operand propagates, quieted, the first one taking precedence; inf − inf and 0 · inf give 0xFFC00000. The meaning differential now runs a control meaning with canon removed: it differs from Hearth's scalar kernel in **640** of 2,162 outputs, while the real meaning differs in 0, against all six kernels [M, `scripts/bitid.py`, seed 20261023]. A unit test shows the canon-less meaning giving a non-canonical NaN on three inputs where `q_canon` stores 0x7FC00000 |
| 5 | minor | P6 was in the meaning but not in DESIGN §3.3, the normative table | Confirmed (DESIGN status note: "proposed … not applied") | The §3.3 row is in the proposed patch below (PRE6), with its source and the statement that it restricts the domain and does not change the arithmetic. Applying it is the DESIGN owner's step, before the hash is taken |
| 6 | minor | Preconditions P1–P6 and primitives P1–P15 shared one namespace (for example "bias form needs P2" in primitive P5's row) | Confirmed | **Modified fix:** renamed **PRE1–PRE6**, not R1–R6 as proposed, because R1–R10 already name the Owner's answers in OWNER-ANSWERS, DELEGATED and OWNER-QUEUE; "RQ" was tried and dropped because "RQ4" trips the specificity lint's `q4` pattern. Applied in `meaning.py`, the checker, `recipes.py` and `sched.py` messages, the tests and `bitid.py`; proposed for DESIGN and the prereg in the patch |
| 7 | (result) | No transcription error; freeze after the wording fixes; record the review in DESIGN §17 | — | §2 above; a §17 row is in the proposed patch |

No finding was rejected.

## 4. The meaning after the fixes

The arithmetic is unchanged; only `REQUIRES`, the docstring and comments changed. Meaning file
SHA-256 now **`62badbd6015b6abdfcffea02895e4f1f2f0d5c33f6a3e24f84ad58dd63bb7dd9`** [M], as printed in
the provenance line of every generated file. On the laptop, with that meaning and the revised
checker: 0 mismatching words between the six generated kernels and Hearth's kernels on 3 × 38,656
cases and under seven non-default MXCSR modes, reference output hash `07b12e55b1ece83b` as before;
the meaning differential 0 / 0 / 0 / 0 / 0 / 0 mismatches on 240 cases and 2,162 outputs, with the
canon control at 640 [M, `scripts/bitid.py --seeds 4`, results/bitid.json].

| Old name | New name | `REQUIRES` string |
|---|---|---|
| P1 | PRE1 | `A.q in [-127, 127]` |
| P2 | PRE2 | `A.sum == sum(A.q)` |
| P3 | PRE3 | `(mxcsr & 0xFFC0) == 0x1F80` |
| P4 | PRE4 | `Y disjoint from W and A`; `W and A readable, Y writable, over their extents` |
| P5 | PRE5 | `n >= 0 and n % 64 == 0`; `T >= 0`; `0 <= r0 <= r1 <= rows(W)` |
| P6 | PRE6 | `T <= 1 or ldy >= r1 - r0` |

## 5. Proposed DESIGN body edits (for the DESIGN owner)

The x3meaning track may edit DESIGN's status notes only, so the body edits are a patch:
[MEANING-REVIEW-design.patch](MEANING-REVIEW-design.patch) (15 edits; `git apply --check` passes on
the tree as of this writing). It contains:
- §3.3: the PRE1–PRE6 table (PRE3 wording, PRE4 source, PRE5 domain, the new PRE6 row) and a
  naming note;
- §3.5: the sketch's `requires` line;
- the precondition names elsewhere in the body: §4.2 rows P5, P9 and P12, §4.3 C3, §4.4 B7, §4.5
  item 22, §7 step 6;
- §4.5: items 29–57 of the planted suite, with their origin;
- §17: three 2026-10-23 rows (the first prototype review and the two reviewers of this round);
- the prereg, threats table: "P1 or P2" → "PRE1 or PRE2", which depends on the rename.

§17's 2026-10-16 text (finding R2-8) keeps its historical "P1 and P2".

## 6. Before the freeze

1. The DESIGN owner applies (or amends) the patch, so that §3.3 and `meaning.py` say the same thing.
2. The meaning hash is taken from `meaning.py` at that commit; the generated files' provenance line
   shows it.
3. After the freeze the meaning changes only to fix a transcription error that the differential
   exposes (DESIGN §3.5).

This review's independence is weaker than ROADMAP asks: the author, the reviewers and the reviser
are all Claude models (m0/README).
