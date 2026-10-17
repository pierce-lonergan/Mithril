# X0 independent re-derivation: procedure (record §7, validity check V3)

Status: written before freeze by the x0prep track (2026-10-16). The re-derivation itself happens after the census
objects exist and is census data. This file only fixes who does it, with what, and how "match" is decided.

## 1. Who

A separate agent context with an adversarial brief. It is labelled **same family (Claude), independent context**
in record §12. The Owner's D0-10 chat answer of 2026-10-16 (relayed by the x0prep brief; to be ratified at the
first weekly signing session) allows no metered API and names only the local Qwen3 pilot (run through Hearth)
besides Claude; whether that pilot can carry a re-derivation is not established. Same-family is weaker than
ROADMAP's different-family requirement; the gap is stated in every review log entry.

The re-deriving context must not have seen `scripts/x0_extract.py`, `x0_decode.py`, `x0_loops.py`, `judge.py`, the
census outputs, or any conversation of the census run. It may read the record.

## 2. What it receives (and nothing else)

1. The FROZEN record `docs/m0/prereg/X0-census.md` at the freeze commit.
2. The census objects (`.obj`/`.o`) of every main-union configuration and build, plus the debug-info twins, copied
   into an empty directory together with a manifest of their SHA-256 values. It does not receive the census
   manifests, decode dumps or `census.json`.
3. `class/fp_class.csv`, `class/loop_table.csv`, `class/xed_tables.tsv`, `class/objdump_norm.csv`.
4. The baseline inputs: Hearth b5d3f14 `engine/src/quant_avx2.c` and `quant_avx512.c`, and the stdarch XML at
   commit `eb9b3025937c85bd271a3ca46a681cd52739db12` (SHA-256 `6762a50652a35ef663fd532ed83b789d19bbc2ac7e94b1771f19d666d96c2c30`).
5. Tools: the pinned XED v2026.08.23 (`xed.exe` / `xed`, `-64 -cet`), LLVM 23.1.3 `llvm-objdump`, `llvm-readobj`,
   `llvm-dwarfdump`, Python 3 standard library.

## 3. What it must write, independently

A script committed under `experiments/x0-census/rederive/` (its own name), which:

1. Locates the 18 dispatched variants from the record's definition (§4.1): the three table initialisers in the
   source, and in each object the relocation on each slot. Function symbols and ranges come from
   `llvm-objdump --disassemble-symbols` / `llvm-readobj --symbols --sections --relocations`, not from the census
   scripts' outputs.
2. Computes the §4.2 closure with its own recursive descent, range and call-kind logic.
3. Decodes every reachable instruction with XED.
4. Recomputes: P1 (per variant: slot resolved, gaps with cause codes), P2 (FMA-class count), P3(a) is not
   recomputed (it is a flag check on the frozen captures), P3(b), P3(c) (loops, accumulators, lanes; using
   `loop_table.csv`), P3(d1), P4 = |U_all|, P5_iclass, P5_opclass (op_class from `fp_class.csv`), |B_iform|,
   |B_mnem| and T_forms from the source and the XML.
5. Writes `rederive/figures.json` with exactly these keys:
   `{"p1": {"<config>|<table>:<slot>": {"slot_resolved": bool, "gap_causes": [..]}}, "p2": {"<config>": n},
     "p3b": [...], "p3c": {"<config>|<table>:<slot>": [loop ids]}, "p3d1": {"<config>": "pass|fail"},
     "u_all": n, "p5_iclass": n, "p5_opclass": n, "b_iform": n, "b_mnem": n, "t_forms": n,
     "iforms": [sorted], "fp_sensitive_iclasses": [sorted]}`.

## 4. How "match" is decided (V3)

A deterministic comparison (to be added to `judge.py`'s input as `census.json` field `rederivation`):

* every number in `figures.json` equals the census figure;
* the sorted iform set and the sorted FP-sensitive iclass set are identical;
* P1 gap cause sets are identical per variant; P3(c) loop flags are identical per variant (loop ids may differ in
  spelling; a flag is matched by variant and by the header address);
* `rederivation.present = true`, `rederivation.matches = (all of the above)`, `rederivation.mismatches = [...]`,
  and `rederivation.figures = {"u_all": .., "p5_iclass": .., "<config>|<table>:<slot>": {"flagged": bool,
  "gap_causes": [..]}}`, so that the conservative resolution of record §8 (iii) can take the figure less favourable
  to Pass.
  - `flagged` is the re-derivation side's own screen for that variant: true if any of P2 > 0, P3(b), P3(c) (a
    flagged loop) or P3(d1) other than `pass` holds there.
  - `gap_causes` is the variant's P1 gap cause list on the re-derivation side.
  - An entry is required for every union variant: the 18 variants of A, B-cmake, C and D, and the A-ninja variants
    that differ from A.
  - After the week-3 bound, `judge.py` refuses a conservative resolution of a V3 mismatch unless `u_all`,
    `p5_iclass` and every such entry are present. The verdict then stays `tooling_failure`. With them, a variant is
    flagged if either side flags it, and every re-derivation gap cause becomes a genuine gap of the variant (Amber (c)
    under A or D, row N1 otherwise). Added after the x0prep review of 2026-10-16.

Any mismatch fails V3. Before the week-3 bound this is a tooling failure (fix and re-run, logging before/after
tables); after it, record §8 (iii) applies. A missing re-derivation after the bound leaves the verdict at
`tooling_failure` (judge.py, decision list step 2).
