"""X2 reference semantics for the x86 instructions Hearth's kernels use.

Status: M0 spike (DRAFT). Every function here works on raw bit patterns (Python ints) with an
explicit FP environment (`fpenv.Env`). Results are computed with exact rational/integer arithmetic
(`fractions.Fraction`); host floating point is never used for result bits. `crosscheck.py` uses the
host only as an optional, separate cross-check.

Layout
  bits.py           binary32 / binary16 fields, classes, exact values, constants
  fpenv.py          MXCSR model, effective environment (RC, DAZ, FTZ, {er}, {sae}), flag bits
  rounding.py       x86 rounding of an exact value to binary32 (tininess after rounding, FTZ)
  fp_ops.py         FP lane functions: add/sub/mul/div, max/min, cmp (32 predicates),
                    (u)comis, cvt i32->f32, f32->i32 (RC and truncating), f16->f32
  int_ops.py        integer lane-group functions (pmaddubsw, pmaddwd, pdpbusd, phaddd, ...)
                    and data movement (shuffles, permutes, unpacks, blends, packs)
  vec.py            vector register model: lanes, write masks {k}{z}, broadcast, scalar forms
  table.py          the entry registry keyed by (XED iclass, iform): operand roles, NaN roles,
                    declarative wiring (`sem` specs built by `build_sem`), content hashes; part of
                    the hashed semantics bundle since 2026-10-16
  bounds.py         T2 range re-derivations from Hearth's code (Q4 3,810; Q8 32,512; ...)
  hearth_kernels.py transliterations of Hearth helpers and act_q8 resolved through table entries,
                    the draft intrinsic map (intrinsic_map v0), numerics_v1 mutant witnesses and the
                    derived commute-before-MAXPS witness rule
  census_absorb.py  absorbs X0's census.json + instructions.jsonl (or smoke functions.json) into a
                    table-coverage report with operand variants, and generates budget.v1 rows
  crosscheck.py     optional host-float cross-check of RNE results
  selftest.py       hand-derived vectors from SDM pseudocode; run: python -B -m semantics.selftest

Source of truth for every rule: the Intel SDM as read by the author, cross-read against Bochs
(SoftFloat 3e) where noted. Items marked UNCERTAIN in the code are SDM readings that silicon fuzzing
(FUZZ-DESIGN.md) must confirm. Nothing here is derived mechanically from Intel's intrinsics XML.
"""

__all__ = ["bits", "fpenv", "rounding", "fp_ops", "int_ops", "vec", "table"]
SEMANTICS_VERSION = "x2-spike-0.2"   # 2026-10-16: review revision (operand roles, hashed wiring)
