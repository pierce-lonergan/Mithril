# R02 / R03 (MAX-FOLD): the written proof from machine-checked lemmas

Status: DRAFT, written 2026-10-16 by the x2build reviser after the same-family, independent-context review
(finding R2-7: the composition existed only as a docstring sketch, and the lemmas had no query hashes and no
second solver). **This document does not change the rows' status.** Under RULES.md §1 "proved" needs a
primary route (Z3 on the concrete pattern, or exhaustive enumeration) and an agreeing second route; the
concrete-pattern primary timed out in Z3 and cvc5 (proofs/README.md §2-§4), so R02 and R03 stay **not
proved**. Whether a written proof whose every lemma is machine-checked by two solvers may serve as the
primary is the Owner's question (RULES.md §8 row R02, with RQ-3); provisional, pending that answer.

## 1. The claim

Environment: DAZ = 0 (RULES.md §3.1 Env column; any RC and FTZ, since no rounding happens).

Let `x_0 .. x_63` be any 64 binary32 bit patterns and `v_i = x_i AND 0x7FFFFFFF` (`fabsf`, `andnot(signmask, v)`,
`_mm512_abs_ps`).

- **Meaning** (`quant.c` act_q8, scalar): `m_0 = +0.0`; `m_{i+1} = (v_i > m_i) ? v_i : m_i`, where `>` is the
  C comparison, i.e. the table's relation (`fp_ops.relation(...) == GT`, as `hearth_kernels._c_gt` evaluates it).
  The result is `m_64`.
- **R02 realization** (AVX2, `quant_avx2.c` act_q8): 8 lane chains, `L_c^0 = +0.0`,
  `L_c^{k+1} = MAXPS(v_{8k+c}, L_c^k)` (the element is **src1**, the running maximum src2), then `hmax8`
  combines `L_0^8 .. L_7^8` with MAXPS on pairs of running maxima only.
- **R03 realization** (AVX-512): 16 lane chains of 4 steps, then `hmax16` (8 MAXPS on pairs, then `hmax8`).

The rule says: the realization's result equals `m_64`, bit for bit, for every input.

## 2. Definitions

- A pattern is **sign-0** if bit 31 is 0. `NaN(t)` is the bit-vector NaN test (exponent all ones, fraction
  nonzero).
- `umax(a, b)` = unsigned maximum of two 32-bit patterns.
- `umaxN(v, m)` = `(not NaN(v) and v >u m) ? v : m`.
- For a finite set `S` of patterns, `U(S)` = the unsigned maximum of `{0} ∪ {s in S : not NaN(s)}`.
  `U(∅) = 0`, and `U(S ∪ T) = umax(U(S), U(T))` because unsigned maximum is associative, commutative and
  idempotent with identity 0 on 32-bit patterns. For a pattern `v`, `U(S ∪ {v}) = umaxN(v, U(S))`.

## 3. Lemmas (each a 2- or 3-input query; `z3_fold.py`, exported to `results/rev1/smt2fold/`)

| Lemma | Statement (all patterns 32-bit) | Z3 / cvc5, query sha256 |
|---|---|---|
| L1 meaning step (SMT-LIB `fp.gt`) | sign-0 v, sign-0 non-NaN m: `(fp.gt(v, m) ? v : m) = umaxN(v, m)` | §6 |
| L1t meaning step (table relation) | same premises: `(relation(v, m) = GT ? v : m) = umaxN(v, m)` with `smt_table.relation` (fp_ops.relation, DAZ = 0) | §6 |
| L2 chain step | sign-0 v, sign-0 non-NaN m: `MAXPS(v, m) = umaxN(v, m)` | §6 |
| L3 tree step | sign-0 non-NaN a, b: `MAXPS(a, b) = umax(a, b)` | §6 |
| L4 closure | sign-0 v, sign-0 non-NaN m: `umaxN(v, m)` is sign-0 and non-NaN | §6 |
| L5 start value | `+0.0` (all zero bits) is sign-0 and non-NaN | §6 |
| L6 abs | `v AND 0x7FFFFFFF` is sign-0 | §6 |

MAXPS is `smt_encoding.maxmin(True, ·, ·)` with DAZ = 0, whose agreement with `fp_ops.max_` is part of the
32,192-comparison differential of RULES.md §3.2. L1t uses the pure-BV relation of `smt_table.py`, checked against
`fp_ops.relation` by `smt_table.differential()` (`results/rev1/differential_smt_table.json`).

## 4. Proof

**Meaning.** Claim: for every i in 0..64, `m_i` is sign-0, non-NaN, and `m_i = U({v_0, .., v_{i-1}})`.
- i = 0: `m_0 = +0.0 = U(∅)`; sign-0 and non-NaN by L5.
- i → i + 1: `v_i` is sign-0 by L6; `m_i` is sign-0 and non-NaN by the hypothesis. By L1t (L1 for the SMT-LIB
  reading of `>`), `m_{i+1} = umaxN(v_i, m_i) = umaxN(v_i, U({v_0..v_{i-1}})) = U({v_0..v_i})` (§2). By L4,
  `m_{i+1}` is sign-0 and non-NaN.
So `m_64 = U(V)` with `V = {v_0, .., v_63}`.

**Chains.** For each lane c the same induction with L2 in place of L1t gives: `L_c^k` is sign-0, non-NaN and
equals `U(V_c^k)`, where `V_c^k` holds the k elements that entered chain c. After the last step,
`L_c = U(V_c)`, and the sets `V_c` (8 of 8 elements for R02, 16 of 4 for R03) partition V.

**Tree.** Every MAXPS of `hmax8` / `hmax16` takes two values of the form `U(A)`, `U(B)` that are sign-0 and
non-NaN (true for the chain results, and preserved below). By L3, `MAXPS(U(A), U(B)) = umax(U(A), U(B)) =
U(A ∪ B)`, which is one of its two inputs and so is sign-0 and non-NaN again. The operand order of a tree MAXPS
does not matter, because `umax` is commutative. Each tree combines disjoint sets and its leaves cover all
chains, so by induction over the tree the root is `U(⋃_c V_c) = U(V)`.

Hence realization = `U(V)` = `m_64` for every input. ∎

What the proof does **not** cover: environments with DAZ = 1 (excluded by the Env column; under DAZ MAXPS
returns the flushed zero, F-DAZ-SEL); the lane maps of `hmax8`/`hmax16` (taken from Hearth's source as the
pairing written in `z3_rules.py` `hmax8`/`hmax16`; the act_q8 compositions of `hearth_kernels.py` check them
on hand-built blocks, RULES.md §5); the soundness of the solvers (two independent solvers replayed every lemma).

## 5. Machine-checking the composition (not achieved)

- Z3 on the concrete 64-input pattern: UNKNOWN at 1,200 s (default strategy) and 1,500 s (bit-blast + SAT
  tactic); cvc5: UNKNOWN at 1,200 s [M] x2build 2026-10-16 (proofs/README.md §2-§3).
- The review (same family, independent context) substituted L1-L3 and asked for the pure-BV composition (the
  umaxN chains against the umax tree, 64 inputs): UNKNOWN in Z3 and in cvc5 at 600 s; characterising the result
  by an upper bound and membership: UNKNOWN at 300 s each [M review, desktop, 1 thread, 2026-10-16]. So the
  difficulty is the 64-deep maximum chain itself, not the FP encoding, and an R03 bit-blast run is unlikely to
  change the status [inference].

## 6. Lemma runs

[M] x2build 2026-10-16 desktop, one thread each (`results/rev1/fold.json`, `results/rev1/cvc5_fold.json`; the query files are in `results/rev1/smt2fold/`, and each sha256 identifies the exported file):

| Lemma | Z3 5.3.1 | s | cvc5 1.4.2 | s | query sha256 (`results/rev1/smt2fold/`) |
|---|---|---|---|---|---|
| L1 meaning step | **PROVED** | 0.005 | **PROVED** | 0.058 | `435afbc3a40282c775f1025ec7ec6f1f0898cf3791e9773ba5d0e554a5db711b` |
| L2 chain step | **PROVED** | 0.004 | **PROVED** | 0.042 | `65622efc4747e38d1140cf9ce2cb30c67177dc336da4331e36afad489308c72f` |
| L3 tree step | **PROVED** | 0.004 | **PROVED** | 0.039 | `9bdab0dee81abdbca4ff6114f30e424761a92c9c97aa69557c346a57cfc57d84` |
| L4 closure | **PROVED** | 0.003 | **PROVED** | 0.002 | `9466ddd1c93a103a791b8b481cd9f5c116dd07ad5243c62963f2a0c9ec8104f3` |
| L5 start value +0 is sign-0, non-NaN | **PROVED** | 0.000 | **PROVED** | 0.001 | `10bd4d579690a94cdea3bbff72c3ab1f0c838d08e8841acd9b07fc03309dda94` |
| L6 abs is sign-0 | **PROVED** | 0.000 | **PROVED** | 0.001 | `80b31edbaf60fe6cd1e84bb45d37b9cae943e66fe20546cfab9a8fbca7ae4263` |
| L1t meaning step, table relation | **PROVED** | 0.009 | **PROVED** | 0.004 | `639a1c896a6cda9288ad0f74994d8320ea92791a9aba4cfa11ae690093e0d02d` |
