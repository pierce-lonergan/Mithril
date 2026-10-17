# X0 census scripts

Standard-library Python (3.8 or later), no third-party packages. Each script runs unchanged on the desktop in WSL
(`python3`, Linux XED and LLVM tools) and natively on Windows (`C:\Python313\python.exe`, Windows XED and LLVM
tools); the smoke validation below ran natively on Windows for ELF and COFF objects alike. Run with `python -I`
because the scripts read untrusted object files.

**Nothing here has been run on a Hearth object.** Every validation used NON-Hearth inputs: `smoke/smoke.c`,
`smoke/smoke_dispatch.c`, the generated instruction zoo, the probes, and synthetic unit-test inputs.

| Script | Record | Does |
|---|---|---|
| `x0obj.py` | | Minimal ELF64 / COFF (and bigobj) reader: sections, symbols, relocations, COMDAT info. Library only |
| `x0_flags.py` | §2, §5 P3(a), §3 B-proxy | `show` per-file flags; `replay` another source with a file's exact command (+ `--extra=-###`, `/Zs`, `/Z7`, `-g`); `p3a` matches `class/fp_flag_patterns.txt` against a driver argv, a `-###` cc1 line and `gcc -Q` output; `proxy` builds the B-proxy command lines |
| `x0_extract.py` | §4.1, §4.2 ranges | Dispatch tables and slots from the SOURCE (struct layout + initialisers; fails unless `--expect-variants` holds); slot -> function through the relocation on the slot (never by name); function ranges (ELF symbol size; COFF COMDAT section, else `.pdata`, else next symbol, flagged) with a `.pdata` cross-check; relocations resolved with ELF explicit and COFF in-place addends; `llvm-readobj --symbols` cross-check |
| `x0_decode.py` | §4.2, §7 cross-decoder | XED sweep of every function range (`-64 -cet`) plus the attribute pass; recursive descent from each slot entry in rounds (closure over fall-through, direct branches and calls; then every pending indirect branch resolved against the complete reach set; repeated until stable, so the output does not depend on the work-list order: `--worklist-order lifo|fifo`); GCC cold parts as function families (`cold_part_of:<parent>`); call kinds internal / interposable / external; FP trust dependencies (external callees not on an allow-list); calls through `[rip+X]` only for `__imp_` (COFF) or GOTPCREL* (ELF) slots, otherwise `unresolved_indirect`; `call reg` through reaching definitions of the register family; jump tables only in the recognised shapes (the jump's own `movsxd/mov` + `add` + `jmp`, base from `lea` through register copies, `jmp [T+rI*8]`), extent from the guarding `cmp/ja`, `and` mask or MSVC byte index table, never partial; no-return inference (frozen list, call at the end of a function or before padding, internal callees without a return); overlapping decodes; unreachable bytes split into padding and orphan; referenced non-instruction code addresses listed; linear-sweep cross-check; llvm-objdump cross-check through `class/objdump_norm.csv`; per-variant counted sets, P2, EVEX static-rounding count, lift blockers and hardening. Writes `variants.json`, `instructions.jsonl` (with CFG successor edges), `crossdecoder.json`, `anomalies.json`, `summary.json` |
| `x0_loops.py` | §4.7, P3(c), P3(d1), P3(d2) | CFG and dominators per closure function, natural loops, flow-sensitive loop-carried FP accumulators (registers and constant stack slots; lane-0 semantics for scalar ops; x0final revision: taint through any instruction, merging on equal provenance, partial results counted over cycles of the carried-location graph, compare-select as MAX/MIN, data operands only, opmasks excluded; pre-freeze review of 2026-10-17: "reads a carried
value" through any data-operand path, compare-select on a copy and in its SSE2 and/andn/or form, merging only copies or
parts of one value on every path), emitted lanes and updates per iteration, inductions, tags (lockstep, unrolled, rotated, software-pipelined, auto-vectorised, spilled, peeled, interchanged), source-loop attribution (header and back edge; the outer loop only with signs of flattening or when it encloses an emitted inner loop, the
inner loop when an emitted outer loop encloses it, nesting through the inline stack counted, else the smaller bound), P3(c), the d1 canary, and the d2 lane-provenance tracker (`track_tree16`) |
| `x0_norm.py` | §7 | The objdump -> XED iclass normaliser used by `x0_decode.py` |
| `classify.py` | §4.3, §4.4 | `class/fp_class.csv` from `class/xed_tables.tsv` |
| `baseline.py` | §4.5 | `class/B_iform.json` from the Hearth source, the stdarch XML and `class/hand_map.csv` |
| `x0_build.py` | §5 P1 compile rule, §6, App. C `builds` | Build records: `exec` runs one compile (a census configure's `compile_commands.json` entry verbatim; a frozen line replayed on another source; or the debug-info twin, build 1's line plus `/Z7` or `-g`), `msbuild` reads configuration A's per-file lines, diagnostics and objects from a detailed MSBuild log. Each record: rc, compiler_ran, the SHA-256 of exactly the binaries Table 2.1 pins (cl.exe + c1.dll + c2.dll; clang-cl.exe; the gcc driver's real file + cc1; clang's real file), argv and its SHA-256, argv_matches_frozen (plumbing-stripped comparison with the pre-freeze capture; for A, x0final revision: the design-time line plus exactly `/O2`, in order, after removing the console-only switches), the single-file ClCompile fallback for files MSBuild never reached, per-file error ownership in a CL batch, structured errors {file, line, text}, the include list (separate listing pass, `/showIncludes /Zs` or `-H -fsyntax-only`, no object), ICE detection |
| `x0_twin.py` | §4.6 | Debug-info twin of one census object: identity per executable section (bytes and relocation list, sections paired by name + function symbols; x0final revision: per function inside an equal-size section with equal relocation offsets); line tables (ELF: `.debug_line` decoded with the object's relocations so every row has its section, every row compared with `llvm-dwarfdump --debug-line`; COFF `/Z7`: `llvm-readobj --codeview` procedures, line tables, nested inline sites with their binary annotations); inline stacks (ELF: `DW_TAG_inlined_subroutine` call sites from `.debug_info`, cross-checked with `llvm-dwarfdump --debug-info`; COFF: inline-site depths); every row start checked against `llvm-objdump` instruction starts; source loops, their `for` induction variables and function extents from the census sources |
| `x0_census.py` | App. C | The census.json assembler: build records, twin records, per-configuration objects (code-section byte and relocation hashes), §6 repro comparison of builds 1 and 2, A versus A-ninja per file and per variant (`ab_compare`, `union_member`), variants with P3(a) per file, P3(b) approximation iclasses, loops, P3(c), d1, d2, sequences, cross-decoder disagreements, baseline, metrics (P1, P2, P3, P4, P5 and the secondary metrics needing no new tooling); checks the Appendix C shape (judge.validate_schema plus stricter checks) |
| `x0_driver.py` | §2-§8 | The census driver: `init` (refuses unless the record is FROZEN and the Hearth blobs match; x0final revision: also unless the tree is a clean git checkout whose record reads FROZEN at HEAD, and records HEAD as `freeze_commit`; smoke runs only on NON-Hearth trees, and never on a source that shares a pair of consecutive non-trivial lines, comments stripped, with a pinned Hearth file
outside the allow-listed dispatch-table declarations, `class/hearth_shingles.json`; pre-freeze review of 2026-10-17:
pairs instead of runs of three, every .c and .h of the source and include directories, UTF-8 only), `config` (one configuration: configure twice from scratch, build twice, twin, effective flags and P3(a), extract, decode, attribute, loops; `census`, `replay` and arm-P `probe` modes), `assemble` (census.json, then judge.py) |
| `judge.py` | §8 | `verdict.json` from `census.json` and the frozen inputs (Gatekeeper): schema check, completeness (A-ninja comparison, P3(a) results, coverage), compile rule with compiler pins, V1 to V4 (V4 includes `xed_tables.tsv`, every script and the compiler pins), conservative resolution after the week-3 bound, recomputed P2, P3(b), V2 and Amber (a), narrowing. The evaluation date is max(system UTC date, latest census run) |
| `xed_tables.c` | §4.4 | Dumps XED's own tables (`class/xed_tables.tsv`); link against the pinned `xed.lib` / `libxed.a` |
| `smoke/smoke.c`, `smoke/smoke_dispatch.c` | | NON-Hearth smoke files. `smoke_dispatch.c` mirrors the shape of Hearth's tables |
| `smoke/gen_zoo.py`, `smoke/norm_check.py` | §7 | Instruction zoo from the XML; normaliser validation |
| `smoke/rv_tricky.c`, `smoke/rv_tricky2.c` | §4.2 | Adversarial NON-Hearth regression inputs written by reviewer 2 of the x0prep review (indirect tail calls next to jump tables, GCC `.cold` switch cases, adjacent tables, calls through an extern function pointer, user no-return calls, overlapping decodes, MSVC byte index tables) |
| `smoke/tricky_expect.json`, `smoke/check_smoke.py` | §4.2 | Expected outcome per function and configuration, and the checker runbook step 72 uses (also checks lifo/fifo identity and the smoke d1 canaries) |
| `smoke/results_regression.json` | | Compact record of step 72's outputs (`runbook/summarize_regression.py`) |
| `smoke/regression_set.json`, `smoke/check_regression_run.py` | §7 | The step-72 regression set as a driver census-file set (replay of the frozen A-ninja, B-cmake, C and D lines), and the check of a driver run against `tricky_expect.json` (builds 1 and 2 must give identical decodes) |
| `smoke/judge_regression.py` | §8 | judge.py's decision list on a NON-Hearth driver run: with `--set`, judge.py's Hearth constants are replaced in that process by the set's own (expected variants read from the set's sources); `--synthetic-rederivation` forces V3 in memory so the rows after V3 are exercised. Smoke only; never a census result |
| `smoke/mock/` | §2-§8 | The census MOCK (NOT Hearth): Hearth's table shape (struct `hx_kernels`, tables `hx_kernels_scalar`, `k_avx2`, `k_avx512`, 18 variants) and Hearth's CMake flag logic. Its first version (x0final) contained verbatim Hearth helpers (record §2 disclosure); the x0final revision rewrote every kernel and helper: the d1 canary shape, 16-lane accumulators, an AVX-512 `tree16` computing the record's pairing through other instructions (d2 `match`) and an AVX2 `tree16` pairing adjacent lanes first (d2 `mismatch` by design), an interposable call, `_mm512_dpbusd_epi32` so that B-cmake fails to compile it. Marker file `X0_NOT_HEARTH` |
| `smoke/results/x0final/` | | Compact records of the x0final end-to-end runs (below): `summary.json` per run (`runbook/summarize_x0final.py`), every `verdict*.json`, the arm P sequences |
| `smoke/smoke_loop_table.csv` | | Source loop table of `smoke_dispatch.c` (smoke only) |
| `probes/reduce_probe.c` | §3 arm P | The reduce probe (NOT Hearth code) |
| `tests/` | | Unit tests on synthetic inputs: `python -I -m unittest discover -s experiments/x0-census/scripts/tests` (`test_judge`, `test_flags`, `test_loops` by x0prep; `test_twin`, `test_build`, `test_loops_x0final`, `test_census` by x0final; `test_driver_guard` and the review cases by the x0final revision) |
| `runbook/` | | Desktop job scripts in run order (see `../TOOLCHAINS.md` §8 and §11): steps 79-82 are the census driver's wrappers, 86 the mock's configure-only captures; `census_tools_win.json` / `census_tools_wsl.json` the desktop tool paths; `design_time_lines.py` extracts design-time ClCompile lines from a `-v:diag` MSBuild log; `pin_inputs.py` recomputes the V4 pins (`class/frozen_inputs.json`) and FREEZE.md's hash tables; `hearth_shingles.py` writes `class/hearth_shingles.json` from the read-only clone |

## Census pipeline (after freeze): the driver

Everything below runs on the desktop, one job at a time, outside the quiet windows (23:00-07:00 PT). `X0` must be
set (x0final revision: no default) to `experiments\x0-census` of a clean git checkout of the repository at the freeze
commit on D:, for example `git clone <origin> D:\mithril\census\Mithril` then `git -C D:\mithril\census\Mithril
checkout <freeze commit>`; the init step refuses a dirty checkout, a record that is not FROZEN at HEAD, or scripts that
differ from their pins, and records HEAD as `freeze_commit` (judge.py V4 requires it). `RUN` is a fresh run directory
on D:. *Pre-freeze review of 2026-10-17:* `freeze_commit` is now the freeze point (the first commit at which the record
reads FROZEN) and HEAD is recorded separately as `run_commit`; init also refuses a record changed other than by an
appended amendment, class/, scripts/ or flags/ paths changed since the freeze point that the amendment does not name
(listed as `post_freeze_changes` when it does), ignored files there other than `__pycache__`, and a Hearth tree not at
b5d3f14. Every `config` and `assemble` step of a census run re-checks that `X0`'s pinned scripts are the ones init
verified (and, on Windows, that the checkout is still at `run_commit`), and `assemble` refuses `--freeze-commit`.

```text
79_census_init.cmd RUN                       refuses unless the record reads FROZEN and the 7 Hearth blobs match record §2
80_census_win.cmd RUN A                      one command per configuration (Windows)
80_census_win.cmd RUN A-ninja
80_census_win.cmd RUN B-cmake
81_census_wsl.sh /mnt/d/...RUN C             (WSL, inside the keepalive VM: wsl.exe -d Ubuntu -- bash ...)
81_census_wsl.sh /mnt/d/...RUN D
80_census_win.cmd RUN P.A probe --from-config A        arm P: the reduce probe with that configuration's
80_census_win.cmd RUN P.A-ninja probe --from-config A-ninja      census quant_avx512.c line
80_census_win.cmd RUN P.B-cmake probe --from-config B-cmake
81_census_wsl.sh /mnt/d/...RUN P.C probe --from-config C
81_census_wsl.sh /mnt/d/...RUN P.D probe --from-config D
82_census_assemble.cmd RUN                    census.json (freeze commit from the init step), then verdict.json
```

Per configuration (`x0_driver.py config`): configure twice from scratch with the pre-freeze configure commands; build
twice (A: `cmake --build --config Release --target hearth_core -- /m:1` with a detailed and a binary MSBuild log,
records by `x0_build.py msbuild`; the others: each census file's `compile_commands.json` entry run verbatim, compared
with the frozen capture); the twin of build 1; the effective flags and P3(a); then for each build `x0_extract.py`
(18 variants, counted from the source), `x0_decode.py -j 2`, `x0_twin.py` per object and `x0_loops.py` with the
attribution. The B-proxy arm runs through the driver's replay mode: `80_census_win.cmd RUN B-proxy replay --set
X0/scripts/runbook/bproxy_set.json` (Hearth's three files with `flags/prefreeze/B-proxy.argv.json`). Not wired into the
driver: the H arms (argv only, in `flags/prefreeze/README.md`).

## Smoke validation (2026-10-16, desktop)

The first version of `runbook/72_smoke_dispatch_check.cmd` (log `runbook/logs/x0prep_72_smoke_dispatch_check.log`; superseded, see the next section) ran `x0_extract.py`, `x0_decode.py` and `x0_loops.py` on
`smoke_dispatch.c` compiled with the A (A-ninja lines), B-cmake, C and D command lines of `quant_avx512.c` and of
`quant.c` (8 objects) [M]. Results: `smoke/results_dispatch.json`. In every configuration all 12 slots resolved
through relocations; `llvm-readobj` symbol cross-check clean; 0 tooling gaps; 0 cross-decoder disagreements;
the only gaps are the designed `fp_trust_dep` ones (expf, and the unknown external `sd_external_log`). Seen and
handled: MSVC in-`.text` ADDR32NB jump tables (excluded as data), clang-cl `.rdata` REL32 tables, GCC/Clang
`.rodata` PC32 tables, GCC `.cold` parts in `.text.unlikely`, an interposable call under C (GCC, `-fPIC`),
clang-cl's hoisted `__imp_` pointer call, Ubuntu GCC's ENDBR64 / canary / `__stack_chk_fail` / `__memcpy_chk`,
MSVC and clang-cl `/GS` cookies, B-cmake's FMA contraction (P2 = 6 in one closure). The d1 canary passes in all
8 objects. P3(c) flags clang's two-accumulator vectorisation of the scalar `L[i & 15]` tail loop under B and D;
it is smoke code and was not investigated further. Negative test (slot entries moved one byte, relocations of one
section dropped): decode exits 1 with `other` / `unresolved_indirect` gaps and cross-decoder disagreements.

The earlier linear-sweep validation of `smoke.c` (steps 60 to 62, `smoke/results/`) is kept as history.

## Regression after the x0prep review (2026-10-16, desktop)

Reviewer 2 of the x0prep review (Claude, same family, independent context) showed that `smoke_dispatch.c` did not exercise the hard cases. On two adversarial files the decoder of that date gave silent false negatives: an indirect tail call `jmp reg` taken as resolved through an unrelated jump table, and a GCC switch table cut short where its cases moved to `.cold`. It also gave misclassifications: a call through an extern function-pointer variable listed as an external call, user no-return calls as `other` gaps on ELF only, DFS-order-dependent results, no overlap gap, an MSVC byte index table as orphan code, and cold parts as callees. `x0_decode.py` and `x0_extract.py` were revised (record §4.2), and the reviewer's files were adopted unchanged as regression inputs (`smoke/rv_tricky*.c`).

Steps `runbook/71b_regression_compile_wsl.sh` (C, D) and `runbook/72_smoke_dispatch_check.cmd` (A, B-cmake; then everything else) compile `smoke_dispatch.c`, `rv_tricky.c` and `rv_tricky2.c` with the A (A-ninja lines), B-cmake, C and D command lines of `quant_avx512.c` and `quant.c`: 24 objects, 168 variants. They decode each object twice, with opposite work-list orders, and check every variant against `smoke/tricky_expect.json`.

Result [M, x0prep reviser, 2026-10-16, final run 19:38 to 19:39 EDT after the last script change (earlier runs of the revision gave the same results); `runbook/logs/x0prep_72_regression_check.log`, `smoke/results_regression.json`]: 0 deviations; lifo and fifo outputs byte-identical for all 24 decodes. For `smoke_dispatch.c`, the slots, gaps, cross-decoder check and d1 canaries are as before. |U_iform| is unchanged except B and B-scalar (149 to 148, 121 to 120): the INT3 after clang-cl's `/GS` failure call is no longer reached. The negative test still fails as required.

## End-to-end runs of the driver (x0final revision, 2026-10-17, desktop)

After the independent review of the x0final work (record §12), runbook steps 86 and 88 ran again with the final
scripts and the REWRITTEN mock (the first mock contained verbatim Hearth helpers; record §2), 01:49 to 01:57 EDT
(22:49 to 22:57 PDT, before the quiet window) [M; logs `runbook/logs/x0final_rev_*.log`, records
`smoke/results/x0final_rev/`]:
- **R2, the rewritten mock in census mode**: compiler pins and argv checks hold everywhere (A under the exact `/O2`
  rule); builds 1 and 2 identical; A and A-ninja identical for all 36 variants; attribution exact everywhere; B-cmake's
  `quant_avx512.c` a genuine `compile_failed`; d1 `pass` everywhere; d2 `match` on the AVX-512 `tree16` and `mismatch`
  on the AVX2 `tree16` (by design) in every configuration that compiles them; no P3(c) flag. `judge.py`:
  `tooling_failure` (V3 only); with V3 forced: `amber_a` (326 > 204, P5 31), `amber_b` (A, B-cmake, C, D), `amber_c`
  (32 `fp_trust_dep`), N1 (B-cmake, C), N2 (B-cmake).
- **R1, the regression set in replay mode**: 0 deviations over 60 decode outputs (420 variants); the same P3(c) flags
  as the x0final run (12 variants under B-cmake, 12 under D); none under C.
- **Fallback**: a copy of the mock with a broken `other.c`, configuration A: MSBuild stopped after the failing batch;
  the single-file `ClCompile` fallback compiled the two SIMD files; `quant.c` rc 0 with no error of its own.
- Before these runs: a NON-Hearth Visual Studio probe measured MSBuild's stop at the first failed CL task, the
  single-file `ClCompile` command and the design-time line versus the build line; the revised decoder resolved the
  narrow-compare jump table of the reviewer's `rvx.c` under C (`runbook/logs/x0final_rev_probes.log`).

## End-to-end runs of the driver (x0final, 2026-10-17, desktop; superseded: the mock of these runs contained Hearth helpers, record §2)

Runbook step 88 (`runbook/88_x0final_smoke_runs.ps1`, after step 86's configure-only captures of the mock), NON-Hearth
inputs only; final run 00:26 to 00:35 EDT [M; logs `runbook/logs/x0final_88_*.log`, records `smoke/results/x0final/`].

- **R2, the census mock in census mode** (`smoke/mock/`: Hearth's table shape and CMake flag logic, NOT Hearth):
  A (Visual Studio generator, MSBuild; the mock's `quant.c` is batched with another file in one CL task, as Hearth's
  is), A-ninja, B-cmake, C, D, each configured and built twice from scratch, with the twin, P3(a), extract, decode,
  attribution and loops; arm P (P.<CFG>) and B-proxy. Every build's compiler binaries equal the Table 2.1 pins and
  every argv check holds; builds 1 and 2 are identical (bytes and relocations) for every object; A and A-ninja are
  identical for all 36 variants; every variant's twin attribution is exact and every loop is attributed to a source
  loop. B-cmake fails to compile the mock's `quant_avx512.c` (`_mm512_dpbusd_epi32` needs AVX512-VNNI; error located
  in the file; 146 includes recorded): a genuine `compile_failed` in both builds. d1 `pass` everywhere; all 66 `tree16`
  sites `match`; no P3(c) flag; P3(a1) on B-cmake for all three files. `judge.py`: V1, V2, V4 hold, V3 fails (no
  re-derivation): `tooling_failure`. With V3 forced (`smoke/judge_regression.py --synthetic-rederivation`): `amber_a`
  (|U_all| 316 > 204, P5_iclass 29 > 20), `amber_b` (B-cmake), `amber_c` (32 genuine `fp_trust_dep` gaps), N1
  (B-cmake, C), N2 (B-cmake).
- **R1, the regression set in replay mode** (`smoke/regression_set.json`): `smoke/check_regression_run.py` finds
  0 deviations from `smoke/tricky_expect.json` (60 decode outputs, 420 variants), builds 1 and 2 decode identically,
  d1 `pass` in every configuration, every variant's attribution exact. P3(c) flags only Clang's vectorisation of
  `smoke_dispatch.c`'s scalar `L[i & 15]` tail (two 16-lane partial results for a 16-lane source sum, B-cmake and D)
  and the loops enclosing it. `judge.py`: `tooling_failure` (none of Hearth's 18 variants; designed tooling gaps);
  with the set's own constants (`judge_regression.py --set`) V1 fails on the 184 designed tooling gaps of
  `rv_tricky*.c`, V2 and V4 hold.
- **Arm P** ran in both (P.<CFG>, the reduce probe with each configuration's `quant_avx512.c` line). The record calls
  its emitted sequences census data; the pre-freeze observation is disclosed in record §2
  (`smoke/results/x0final/R1reg_probe_sequences.txt`).

What these runs changed in the scripts (each a measured defect, fixed before the final run; record Appendix E,
rows "x0final"): calls clobber caller-saved registers in the loop analysis (GCC `-fPIC` call results looked
loop-carried); an accumulator must carry an accumulated value across the back edge (MSVC's reused mask register);
`[RBP+d]` is a stack slot only while RBP is loop-invariant (GCC uses RBP as a data pointer); the source loop comes
from the header and the back edge (vectorised inner loops of a tree); the d2 site ends at its last FP ADD and the
whitelist gains (V)SHUFPD and VPERMILPD (Clang); `x0_decode.py` accepts a code section without relocations (the probe).

