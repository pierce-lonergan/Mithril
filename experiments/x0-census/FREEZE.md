# X0 freeze checklist

Record: [`docs/m0/prereg/X0-census.md`](../../docs/m0/prereg/X0-census.md), status **DRAFT**. Prepared by the
x0prep track on 2026-10-16, completed by the x0final track on 2026-10-16/17, revised by the x0final revision on
2026-10-17 after the independent review of the x0final work, and revised again by the pre-freeze review revision on
2026-10-17 after the independent pre-freeze review, and completed by the desktop re-run of 2026-10-17 (Claude; laptop
DESKTOP-F441IUK for authoring, desktop DESKTOP-8RS9J1J for the tool runs; the pre-freeze review revision used the
laptop only). This file is the long form of the record's Appendix D.

**Verdict of this checklist: no blocking item remains; the freeze commit waits on the lead engineer's decisions
(item 2).** The pre-freeze review of 2026-10-17 (record §12: 11 findings, 11 accepted, 3 changed in part, 0 rejected) is
handled in the scripts and the record, and its desktop re-run (item 1) is done: one pre-freeze tooling fix (record §4.7
dependency-breaking idioms, Appendix E), 183 unit tests pass, the pins are recomputed, and the final run with the
re-pinned scripts meets every requirement of item 1. What remains before the freeze commit:
1. **Desktop re-run: DONE (2026-10-17, 03:23-03:55 EDT; record §7).** It ran inside the 23:00-07:00 PT window because
   the lead engineer authorised the desktop for that night (not a pilot quiet night), with at most 4 threads, no GPU and
   WSL only inside the running keepalive. Runbook steps 86 and 88 (R1 regression replay with arm P; R2 mock in census
   mode with arm P and B-proxy) ran twice from a sync copy of the tree:
   - *first run, scripts of commit 2191ff8 as pinned* (R2 `smoke-20261017T072407Z`, R1 `smoke-20261017T072727Z`):
     `check_regression_run.py` 0 deviations and every header environment equal to its pin, but 50 P3(c) flags that the
     earlier rules did not raise (24 regression variant builds: `sd_q8`'s row loop under B-cmake, C, D; 26 mock variant
     builds under A, A-ninja, B-cmake, B-proxy, C, D), and the earlier enclosing loops at 32 lanes instead of 16. Every
     one is a false flag: each loop zeroes the registers of its counted cycle with a dependency-breaking idiom (`xorps
     x,x`, `pxor`, `vpxor`, `vxorps`, `xor r,r`), which XED lists as a read and the broader DEP reading of §4.7 took as
     a carried value (`runbook/logs/prefreeze_rerun_checks.log` §1: each loop before and after);
   - *fix* (record §4.7 and Appendix E row "desktop re-run"): `x0_loops.py` `dependency_breaking` (an idiom reads no
     value), four unit tests in `tests/test_loops_prefreeze.py` (183 in all, all pass), re-pinned with `pin_inputs.py`
     (0 differences on the laptop and on the desktop's sync copy);
   - *final run with the re-pinned scripts* (R2 `smoke-20261017T074224Z`, R1 `smoke-20261017T074551Z`,
     `scripts_match_pins` true): `check_regression_run.py` **0 deviations** (60 decode outputs, 420 variants) with the
     rewritten `smoke_dispatch.c`; P3(c) flags **exactly the x0final revision's 24 regression variant builds** through
     the same loops and counts (Clang's tail loop 32 over 16, its enclosing loops 16 over 0; B-cmake and D) and **none
     on the mock**; **every configuration's header environment equals its pin** (A, A-ninja, B-cmake, B-proxy, C, D and
     every P.<CFG>; D and P.D: resource-dir tree 327 files `18b182d3…`; B-cmake, B-proxy, P.B-cmake: 322 files
     `5587c91b…`); every other outcome as in the x0final revision's runs (the "What was run" table).
   Also done: `x0_driver.py init`'s freeze-point logic against a throwaway repository with real git (16 of 16 scenarios
   as intended), and Windows git reads `D:\mithril\src\hearth` at b5d3f14 (the `.git/HEAD` fallback gives the same).
2. **Lead engineer's decisions: DECIDED (2026-10-17, 01:20 PT, before freeze).**
   - P3(d1) and P3(d2) stay confirmatory, with the E6 label (ruling recorded in record §2).
   - The P3(c) results of the scalar F32, F16, BF16 and act variants are reported with the widened E6 label. Nothing
     more is required. Like d1 and d2, P3(c) can only flag a defect, never produce a pass, so tuning its rules on
     regression flags cannot manufacture a passing outcome. The label tells readers which results were shaped by
     pre-freeze tuning.
   - No further independent review before freeze. The pre-freeze review revision tightened the screens. The desktop
     re-run's idiom fix was checked by an independent checker (Claude, same family, independent context, 2026-10-17)
     against all 2,534 loops common to both trees, and no real count was lost. The census output itself gets the
     independent re-derivation of §7. Stopping the review regress here is recorded as a residual risk, not hidden: the
     reviewer points listed in the previous revision of this item remain the agenda for any post-census tooling audit.
   - The `rvx_vrp` regression-set addition stays deferred. A Hearth instance of that shape would surface as a V1
     tooling gap, which is visible and blocks the verdict, rather than as a silent miss.
3. **The freeze commit**: the record's status line changed to FROZEN; `python -I scripts/runbook/pin_inputs.py`
   (no differences) and the hash tables below recomputed. Nothing under `experiments/x0-census/scripts/`, `class/` or
   `flags/` may change between this list and the freeze commit unless the record's Appendix D,
   `class/frozen_inputs.json` and this file change with it. After the freeze commit `x0_driver.py init` refuses a change
   there that an appended amendment does not name (record §8 item 10). The desktop re-run's changes (record, this
   file, `x0_loops.py`, `tests/test_loops_prefreeze.py`, `class/frozen_inputs.json`, the `prefreeze_rerun` logs and
   results) are in the working tree only: not committed.
4. **Running the census** needs a clean git checkout on the desktop of the freeze commit (or of a later commit that only
   appends an amendment) and `X0` set to its `experiments\x0-census` (below); the init step refuses anything else.
   Runs stay outside the quiet windows (23:00-07:00 PT).
5. **The Owner's signature** (D0-12): OQ-6 is answered on both parts, pending ratification at the first weekly signing
   sitting (Sunday 2026-10-18; the packet is due Saturday night): the instruction part through D0-12 (OWNER-QUEUE R3,
   "D0-12i CONFIRMED") and the spend part through D0-10a (R1: $0 metered) (record header, Appendix A). The
   Gatekeeper's verdict waits for the signature.

No Hearth *file* was compiled and no Hearth object was decoded to produce anything listed here (record §2, statement
D12). Hearth's own helper text was compiled inside the first census mock and, as three two-line runs, inside the
regression file `smoke_dispatch.c` (record §2 disclosures); the mock was rewritten, the three runs were rewritten and the
guard was strengthened. The desktop re-run compiled and decoded only the mock, the regression set and the reduce probe;
it read the Hearth clone's git HEAD and the seven files' blob hashes (no compile, no decode). Hashes are SHA-256 of the
file bytes in this working tree [M, pre-freeze review revision, 2026-10-17; recomputed by the desktop re-run,
2026-10-17]: LF line endings for every text file except `.cmd` files, which `.gitattributes` keeps as CRLF on every
checkout, so the values are the same on Windows and Linux checkouts.

## Summary

| # | Artefact | Path | Status | Missing |
|---|---|---|---|---|
| D1 | Toolchain pins, Table 2.1 | `TOOLCHAINS.md` §11; record Table 2.1 | done [M] | none |
| D2 | Flag captures (configure-only; `-###`, `gcc -Q`) | `flags/prefreeze/`, `flags/C-gcc.*`, `flags/D-clang.*` | done [M] | A's exact build lines exist only once the census build runs (by design, §2); the design-time lines omit `/O2`, which is the only difference A's check now tolerates |
| D3 | Smoke-test logs, NON-Hearth only | `scripts/runbook/logs/`, `scripts/smoke/results/x0final/` (first mock, superseded), `scripts/smoke/results/x0final_rev/`, `scripts/smoke/results/prefreeze_rerun/` | done [M]: the x0final revision re-ran steps 86 and 88 with the rewritten mock, plus the MSBuild and decoder probes and the fallback run; the desktop re-run (2026-10-17) ran steps 86 and 88 with the pre-freeze review revision's scripts and the rewritten `smoke_dispatch.c`, then, after the §4.7 idiom fix, with the re-pinned scripts (item 1); `smoke_dispatch.c` carried Hearth lines until 2026-10-17 (record §2 disclosure) | none (the MSBuild fallback run was not repeated; its build path is unchanged) |
| D4 | B-proxy and H argv | `flags/prefreeze/B-proxy.argv.json`, `flags/prefreeze/README.md` | done; B-proxy runs through the driver (`runbook/bproxy_set.json`) | the H arms are argv only, not wired into the driver |
| D5 | `fp_class.csv` (+ `classify.py`, XED tables) | `class/`, `scripts/` | done [M]; reviewed 2026-10-16 (197 iclasses) and again 2026-10-16/17 (945 iclasses, 0 disagreements) | none |
| D6 | `B_iform.json`, `hand_map.csv`, stdarch commit, XML hash | `class/`, record §4.5 | done [M]; re-derived twice, identical | none |
| D7 | `fp_flag_patterns.txt` | `class/` | done | none |
| D8 | `objdump_norm.csv` | `class/` | done, validated on a NON-Hearth corpus [M] | none |
| D9 | `loop_table.csv` | `class/` | done (62 loops) [M] | not reviewed row by row (record §12) |
| D10 | Reduce probe (arm P) | `scripts/probes/reduce_probe.c` | done [M]; run end to end (disclosure, record §2) | none |
| D11 | Scripts §4.2, §4.6, §4.7, §8, the assembler and the driver | `scripts/` | done [M]; reviewed 2026-10-16/17 and revised; reviewed again 2026-10-17 (pre-freeze review) and revised; run end to end by the desktop re-run (item 1), which fixed `x0_loops.py` (§4.7 idioms); 183 unit tests; re-pinned | the scripts' commit hash (the commit that adds them); review of the pre-freeze review revision's own changes and of the re-run's fix (lead engineer's call) |
| D12 | Statement: no Hearth compile before freeze | record §2; `TOOLCHAINS.md` §11 | done [M]; qualified by the mock disclosure and the `smoke_dispatch.c` disclosure (record §2, E6) | interactive SSH commands of the tooling session are unlogged; that part rests on that track's account |

## Running the census after freeze

`scripts/README.md`, section "Census pipeline (after freeze): the driver". On the desktop, outside a quiet window:
clone the repository to D: and check out the freeze commit, set `X0` to that checkout's `experiments\x0-census`
(steps 79-82 refuse an unset `X0`), then `runbook/79_census_init.cmd` (refuses unless the checkout is clean, the record
reads FROZEN at HEAD, every pinned script matches and the Hearth blobs match; pre-freeze review revision: records the
freeze point, the first commit with the record FROZEN, as `freeze_commit` and HEAD as `run_commit`, and refuses a
record edited other than by an appended amendment, unnamed class/scripts/flags changes since the freeze point, ignored
files there other than `__pycache__`, and a Hearth tree not at b5d3f14; if Windows git refuses the WSL-made Hearth clone,
its HEAD is read from `.git/HEAD`; measured 2026-10-17: Windows git 2.45.1 reads `D:\mithril\src\hearth` at b5d3f14
directly, and the logic accepts and refuses as intended on a throwaway repository, item 1), one
`80_census_win.cmd` / `81_census_wsl.sh` command per configuration (A, A-ninja, B-cmake, C, D; arm P as P.<CFG>;
B-proxy with `runbook/bproxy_set.json`; each step re-checks that `X0`'s scripts are the ones init verified), then
`82_census_assemble.cmd` (`census.json`, then `verdict.json`; no `--freeze-commit` in a census run). Thread
use: one compiler or MSBuild node at a time and XED `-j 2`; MSVC's back end may use extra threads within one compile
[inference]. `judge.py` will say `tooling_failure` until the independent re-derivation (`rederive/PROCEDURE.md`) fills
`census.json`'s `rederivation` block (V3).

## What was run, with results [M]

| Run | Where | Result |
|---|---|---|
| `classify.py` (+ `--check`) | laptop | 1,995 iclasses, 624 FP-sensitive, 4 SDM-no/XED-yes (LDMXCSR, VLDMXCSR, STMXCSR, VSTMXCSR), 0 default-rule rows, 0 self-check problems; deterministic |
| `baseline.py` (+ `--check`) | laptop | 130 intrinsics, 23 no single instruction, \|B_iform\| 102, \|B_mnem\| 74, T_forms 102, 105 XML form strings, 1 hand-mapped instruction, 0 problems; deterministic. Re-run by the x0final revision with reviewer 1's re-derivation script: the same counts, and the five pinned hashes match |
| Step 68: `xed_tables.c` against pinned `xed.lib` | desktop | built and run, rc 0; 9,001 iforms, 1,995 iclasses, 11,018 decoder entries |
| Step 69: instruction zoo + `norm_check.py` | desktop | 26,553 instructions, 982 XED iclasses (320 FP-sensitive), 0 iclass disagreements after the table, 1 boundary disagreement (linear sweep through MSVC jump-table data) |
| Steps 70, 70b, 71: pins and flag captures | desktop | all configure runs rc 0; only CMake's own probe objects in the configure trees; `-###` and `gcc -Q` rc 0; smoke compiles rc 0; reduce-probe syntax checks rc 0 |
| Steps 71b and 72 after the x0prep review | desktop | 24 objects, 168 variants, 0 deviations; lifo and fifo decodes byte-identical |
| Unit tests `scripts/tests/` | laptop | 183 pass after the desktop re-run's fix (71 `test_judge`, 7 `test_flags`, 17 `test_loops`, 27 `test_loops_x0final`, 20 `test_loops_prefreeze`, 14 `test_build`, 12 `test_twin`, 3 `test_census`, 12 `test_driver_guard`); among them the reviewers' adversarial cases (x0final: argv and object checks, slot gaps, `amendment:` resolutions, typed P3 lists, run dates, attribution none, freeze commit, loops T1 to T6; pre-freeze: loops A1 to A9, the freeze point, per-step re-checks, the guard, header pins, the canary report; desktop re-run: dependency-breaking idioms). 179 passed after the pre-freeze review revision, 152 before it |
| x0final probes: `smoke_dispatch.c` and `rv_tricky.c` twins (`/Z7`, `-g`) | desktop | measured the CodeView annotation semantics and the DWARF section problem of relocatable objects (x0final) |
| Step 88 of x0final with the FIRST mock (run `smoke-20261017T042641Z`, 00:26-00:35 EDT) | desktop | superseded; kept as the record of what was seen: the first mock contained verbatim Hearth helpers (record §2 disclosure); d1 `pass` everywhere, 66 `tree16` sites `match`, no P3(c) flag (`smoke/results/x0final/`, `runbook/logs/x0final_88_*.log`) |
| x0final revision, MSBuild probe (NON-Hearth VS project) | desktop, 01:06-01:09 EDT | a failing CL batch stops MSBuild before the next CL task; `/t:ClCompile /p:SelectedFiles=<file>` compiles that one file with the same CL line; the build line equals the design-time line plus `/nologo`, `/diagnostics:column`, `/O2` and `/Fd`, in order (`runbook/logs/x0final_rev_probes.log`) |
| x0final revision, decoder fix on the reviewer's NON-Hearth `rvx.c` (C, build 1) | desktop, 01:07 EDT | `rvx_vrp`: table resolved (10 entries, `movzx; cmp DL,0x9; jnbe`), orphan bytes 117 and 112 to 0, gap removed; the other 7 variants of each object unchanged |
| x0final revision, step 88 R2: the REWRITTEN mock in census mode (A, A-ninja, B-cmake, C, D), arm P, B-proxy; `census.json`; `judge.py` | desktop, 01:49-01:52 EDT | run `smoke-20261017T054918Z`, `scripts_match_pins` true: 0 non-zero steps (B-cmake's genuine `quant_avx512.c` failures are in its build records, rc 1, both builds); every compiler pin and argv check holds (A: the exact `/O2` delta); builds 1 and 2 identical; A and A-ninja identical for all 36 variants; attribution exact for every variant and loop; d1 `pass` everywhere; d2 `match` on the AVX-512 `tree16` and `mismatch` on the AVX2 `tree16` (designed) in every configuration that compiles them; no P3(c) flag; P3(a1) on B-cmake; `census.json` schema check clean; `judge.py`: V1, V2, V4 true, V3 false: `tooling_failure`; with V3 forced (smoke only): `amber_a` (U_all 326 > 204, P5_iclass 31 > 20), `amber_b` (A, C, D: designed d2 mismatch; B-cmake: P3(a1), P2 = 20, d2), `amber_c` (32 genuine `fp_trust_dep`), N1 (B-cmake, C), N2 (B-cmake) |
| x0final revision, step 88 R1: the regression set in replay mode, arm P; `census.json`; `judge.py`; `check_regression_run.py` | desktop, 01:52-01:56 EDT | run `smoke-20261017T055241Z`, `scripts_match_pins` true: `check_regression_run.py` 0 deviations over 60 decode outputs (420 variants); d1 `pass` everywhere; attribution exact everywhere; P3(c) flags the same 24 variants as the x0final run (B-cmake 12, D 12: Clang's two 16-lane partial results for `smoke_dispatch.c`'s tail sum, still 32 lanes, and its enclosing loops, now 16 lanes instead of 32), none under C; 32 cross-decoder disagreements, all NOP (`rv_overlap`); `judge.py`: `tooling_failure`; with the set's constants V1 fails on the 184 designed tooling gaps, V2 and V4 true |
| x0final revision, the single-file fallback on a copy of the new mock with a broken `other.c` (configuration A only) | desktop, 01:56 EDT | MSBuild stopped after the failing `other.c`/`quant.c` batch in both builds; `quant_avx2.c` and `quant_avx512.c` compiled by the single-file `ClCompile` fallback (rc 0, objects present, `fallback` recorded); `quant.c` rc 0 with no error of its own; `argv_matches_frozen` false only through the copy's `-I` directory (`runbook/logs/x0final_rev_fallback.log`) |
| pre-freeze review revision: the reviewer's synthetic loop streams A1-A9 against the pinned and the revised `x0_loops.py`; an overlap scan of every smoke source against the read-only clone's seven pinned files (blob hashes verified, no git); the pinned and revised `x0_loops.py` on the x0prep reviewer's existing NON-Hearth decodes of `rv_tricky.c`/`rv_tricky2.c` | laptop, 2026-10-17 | A1-A9 before: 0, 0, 0, 8 (merged), 0, 0, outer, latch, 0; after: 2, 8, 16, 16, 8, 16, inner, inner (with the call site and the enclosing loop), 8; the old `smoke_dispatch.c` shared 3 pairs and 14 long lines with Hearth, the rewritten one 0 pairs; the new guard refuses every first-mock file (2, 4, 11, 14 pairs) and passes every current smoke source; 120 loops, no FP accumulator under either rule, identical results. Nothing compiled or decoded |
| Desktop re-run, FIRST run: steps 86 and 88 with the scripts of commit 2191ff8 as pinned (sync copy `D:\mithril\x0reg\x0-census_first`) | desktop, 03:23-03:31 EDT | R2 `smoke-20261017T072407Z`, R1 `smoke-20261017T072727Z`, `scripts_match_pins` true: `check_regression_run.py` 0 deviations (60 decode outputs, 420 variants); header environments equal to their pins in every configuration; 0 non-zero steps on the mock; but P3(c) flags 50 variant builds the earlier rules did not flag: mock A 2, A-ninja 2, B-cmake 6, B-proxy 6, C 4, D 6 (scalar act block/blk loops, AVX2 act loop, AVX2 Q8/Q4 row loop), regression set B-cmake 8, C 8, D 8 (`sd_q8`'s row loop, smoke_dispatch.c:132, both objects), plus the earlier 24; enclosing loops of the earlier flags at 32 lanes. All other summary figures equal to the x0final revision's (`runbook/logs/prefreeze_rerun_first_88_*.log`, `smoke/results/prefreeze_rerun/first_*_summary.json`) |
| Analysis of those flags and the pre-freeze tooling fix | laptop, 03:28-03:41 EDT | every new flagged loop re-analysed from the run's decodes: each counted cycle's registers are zeroed in the loop by a dependency-breaking idiom (`xorps x,x`, `pxor`, `vpxor x,x,x`, `vxorps x,x,x`, `xor r,r`) that XED lists as a read; with `x0_loops.py` `dependency_breaking` every one counts 0 lanes, the earlier tail loops keep 32 and their enclosing loops return to 16 (`runbook/logs/prefreeze_rerun_checks.log` §1); 4 unit tests added (183 pass); `pin_inputs.py --write` (2 script pins changed), then 0 differences |
| Desktop re-run, FINAL run R2: step 86, then the mock in census mode (A, A-ninja, B-cmake, C, D), arm P, B-proxy; `census.json`; `judge.py`; `judge_regression.py --synthetic-rederivation` (sync copy `D:\mithril\x0reg\x0-census`, re-pinned) | desktop, 03:42-03:46 EDT | run `smoke-20261017T074224Z`, `scripts_match_pins` true, `x0_loops.py` `8c7ecc9e…` in `census.json`: 0 non-zero steps; compiler pins and argv checks hold; builds 1 and 2 identical; A and A-ninja identical (36); attribution exact; d1 `pass`; d2 6 `match` + 6 `mismatch` per configuration (B-cmake 6 `mismatch`), as designed; **no P3(c) flag**; P3(a1) on B-cmake; header environments equal to their pins; `judge.py` V1, V2, V4 true, V3 false: `tooling_failure`; synthetic: `amber_a` (326 > 204, P5_iclass 31), `amber_b` (A, B-cmake, C, D), `amber_c` 32, N1 (B-cmake, C), N2 (B-cmake); arm P probe records identical to the x0final revision's (`runbook/logs/prefreeze_rerun_88_R2_mock.log`, `smoke/results/prefreeze_rerun/R2mock_*`) |
| Desktop re-run, FINAL run R1: the regression set in replay mode, arm P; `census.json`; `judge.py`; `judge_regression.py --set`; `check_regression_run.py` | desktop, 03:46-03:49 EDT | run `smoke-20261017T074551Z`, `scripts_match_pins` true: **`check_regression_run.py` 0 deviations** over 60 decode outputs (420 variants); d1 `pass`, attribution exact, builds 1 and 2 identical; **P3(c) flags exactly the x0final revision's 24 variant builds** (B-cmake 12: `L19_2a0` 32 over 16, `L19_1ca`/`L19_123` 16 over 0; D 12: `L2_10c0`, `L2_f34`, `L2_e66` likewise), none under A, A-ninja, C; 32 NOP cross-decoder disagreements (`rv_overlap`); header environments equal to their pins; `judge.py` `tooling_failure`; with the set's constants V1 fails on the 184 designed gaps, V2 and V4 true. Against the x0final revision's summaries only descriptive tags (`software-pipelined`, `lockstep`, `unrolled-u` under D) and three B-proxy tag-agreement figures differ (`runbook/logs/prefreeze_rerun_88_R1_regression.log`, `smoke/results/prefreeze_rerun/R1reg_*`) |
| Decode comparison: the re-run against the x0final revision's run, and first against final re-run | desktop, 03:50 EDT | rewritten `smoke_dispatch.c`: decoded code identical under A, A-ninja, C (both builds, both objects); under B-cmake and D `sd_float_common` differs (same instruction count and iclass multiset; FP adds of the flattened tree with commuted operands, another schedule); `rv_tricky*.c`, the mock and arm P identical; first and final re-run identical everywhere (`runbook/logs/prefreeze_rerun_checks.log` §3) |
| Hearth HEAD and the `.git/HEAD` fallback | desktop, 03:51 EDT | `git -C D:\mithril\src\hearth rev-parse HEAD` (Windows git 2.45.1): b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220, rc 0; `.git/HEAD` the same; `x0_driver.source_commit` returns it with git and with no git on PATH; `source_blob_check` 7/7 (read only; §4 of the checks log) |
| `x0_driver.py init` freeze-point logic on a THROWAWAY repository (`D:\mithril\x0reg\gitwork\repo`: record DRAFT, FROZEN in one commit, appended amendments, tooling changes, in-place edits) | desktop, 03:52-03:53 EDT | Windows git 2.45.1, Python 3.13.4, 16/16 as intended: accepted the freeze point (freeze = run commit), an appended amendment, a named and re-pinned tooling change (`post_freeze_changes` listed) and a FREEZE.md change (outside class/scripts/flags, by design); refused a DRAFT record, an uncommitted edit, an untracked file, an ignored `.pyc`, unnamed class/ and flags/ changes, a named but not re-pinned script, an in-place edit (alone, behind an appended amendment, through DRAFT and FROZEN again) and a `--record` outside the checkout; S0-S14 with the Hearth checks stubbed, S15 with the real Hearth tree (`smoke/results/prefreeze_rerun/gitlogic_throwaway.json`, `tools/`) |

The x0final revision's final runs used scripts that differ from the pins below in many files, code included (`x0_loops.py`, `x0_driver.py`, `x0_census.py`, `judge.py`, `smoke/smoke_dispatch.c`, the runbook steps 79-82 and the tests; pre-freeze review revision, 2026-10-17), so their results stand for the earlier scripts only; the re-run of item 1 replaces them. Before that revision they differed in four files only, none in its code (`tests/test_driver_guard.py`, the docstrings of `x0_loops.py` and `x0_twin.py`, and `smoke/mock/X0_NOT_HEARTH`). The desktop was not used after 01:57 EDT, and not at all by the pre-freeze review revision. The desktop re-run's FINAL runs used exactly the pins below (`scripts_match_pins` true; `pin_inputs.py` 0 differences on the desktop's sync copy); after them only unpinned files were added (logs, results and the check tools under `smoke/results/prefreeze_rerun/tools/`).

Not run: any Hearth compile or decode; the H arms.

## Hashes per item

### D1
| File | SHA-256 |
|---|---|
| `experiments/x0-census/TOOLCHAINS.md` | `7ebc0cc7d162ba385d8bae645dae3491ab36744437b8d0a48cd4f7a8fa20e2ec` |

### D2
| File | SHA-256 |
|---|---|
| `experiments/x0-census/flags/prefreeze/A-ninja.compile_commands.json` | `fdb6ad9741a5556ef9031768c4484f62390674950012988eb833f215ca134a4a` |
| `experiments/x0-census/flags/prefreeze/A-vs.design_time_cl_lines.txt` | `a7a75a1258c7ebd5cb1e895e9b127fbf5eae85e3160060d434f2da879a9c71d8` |
| `experiments/x0-census/flags/prefreeze/A-vs.hearth_core.vcxproj` | `9892a08e16dc2473258c4e2dd1a73d344e999a8f8ac464b46a6b356cd9b4312a` |
| `experiments/x0-census/flags/prefreeze/B-cmake.compile_commands.json` | `91d00c20385640880d8ec75dc557685d3d784ce80902ab271c9ec32a24f10f0a` |
| `experiments/x0-census/flags/prefreeze/B-cmake.quant.c.cc1.txt` | `1b87b4d59f20f58cade1b2de42839712f2310a1b914db3d79a255321b6bfce1c` |
| `experiments/x0-census/flags/prefreeze/B-cmake.quant_avx2.c.cc1.txt` | `52a149f38d850f05431ee694ebb411a944d0aff9d2f897759e716bb3a5484134` |
| `experiments/x0-census/flags/prefreeze/B-cmake.quant_avx512.c.cc1.txt` | `eeb1ed3eebef53f129eab19cdc2a2b843692eb9b32b110639746bb4457b162a4` |
| `experiments/x0-census/flags/prefreeze/B-proxy.argv.json` | `7f43b546a44d417eff1fc1cf206acd1dbd702940f4953a6f9799852bc6c8dae3` |
| `experiments/x0-census/flags/prefreeze/B-proxy.quant.c.cc1.txt` | `c52fcfbf6f6ad7a9ba737c58e8b7bd4ff54818254c563e65da9063d1dda6258a` |
| `experiments/x0-census/flags/prefreeze/B-proxy.quant_avx2.c.cc1.txt` | `5b1a2c65410106eafc428948dd37211ebd9d9e0fc6fbd22e1c498683d2de3b50` |
| `experiments/x0-census/flags/prefreeze/B-proxy.quant_avx512.c.cc1.txt` | `f67a50dd7b52d24ff88dd4354cbc5e27c67b89d267bd81d20186ac1ecb8efa60` |
| `experiments/x0-census/flags/prefreeze/C-gcc.quant.c.cc1.txt` | `0bf0a344a73b6ef9dbfc054e0608e15f0f3ac7a97eca72b9662970c4911683b6` |
| `experiments/x0-census/flags/prefreeze/C-gcc.quant.c.gccq.txt` | `cb94600db13d5492d9b75600b3c22af70567b2fa10d553af265e0e755652d0ca` |
| `experiments/x0-census/flags/prefreeze/C-gcc.quant_avx2.c.cc1.txt` | `8acc690d25d734ecf1f759b9cb8dda6b461a8ab8cf4dd5f3b4a2f11e25951d40` |
| `experiments/x0-census/flags/prefreeze/C-gcc.quant_avx2.c.gccq.txt` | `cefc359f72e963641a79b9dcde371e846a416d482f55872d2b4c05f530a602ad` |
| `experiments/x0-census/flags/prefreeze/C-gcc.quant_avx512.c.cc1.txt` | `d659743daf6fd813100d01d26fb86828f822c76c350664b0c8ff07bf596237dd` |
| `experiments/x0-census/flags/prefreeze/C-gcc.quant_avx512.c.gccq.txt` | `10126ce2c53bfdbe727bc0e89e2506cd461efe0520ce152c851ed57f003632b9` |
| `experiments/x0-census/flags/prefreeze/D-clang.quant.c.cc1.txt` | `b4766b7e62dcde36345587ab54b52718f591256dd8b99672ed3234600b996812` |
| `experiments/x0-census/flags/prefreeze/D-clang.quant_avx2.c.cc1.txt` | `0c02b4b8ad6ee74b3f156b4253d1fed09a20f6b25ba0b9f1d8f7af00585c55de` |
| `experiments/x0-census/flags/prefreeze/D-clang.quant_avx512.c.cc1.txt` | `af7cfd75e6633ae2a5d21b500dfad21654f62164efb7c7f70d7c4c4fa03e89ee` |
| `experiments/x0-census/flags/prefreeze/README.md` | `643f377dbf407f7014316cf676f0a6c209a7ae69a4410e5e8ee0b54210557e36` |
| `experiments/x0-census/flags/C-gcc.compile_commands.json` | `cff48e9173e85b766ffd2ed3552e1e5a4c231fa385cd7470ec8ecf4e6563f1f6` |
| `experiments/x0-census/flags/D-clang.compile_commands.json` | `09430921fa1b0917bf56b9aa20890b0c71910890f4f57f7a8077d83f477d0225` |

### D3
| File | SHA-256 |
|---|---|
| `experiments/x0-census/scripts/runbook/logs/60_smoke_win.log` | `b1c24329c5f646f23fa30bbeae2eb0a6ab8aad7a8b8b3a08acd64790333974ef` |
| `experiments/x0-census/scripts/runbook/logs/61_smoke_wsl.log` | `06ae7c358e533683355a13f7d2a372d7483d0be7713f88aabd76368bdbec43bc` |
| `experiments/x0-census/scripts/runbook/logs/62_smoke_decode_win.log` | `31f9474789c503973c8cd403a62324723a135a6b1c630b6e917e807197d4c29d` |
| `experiments/x0-census/scripts/runbook/logs/x0final_86_mock_prefreeze.log` | `f62d01ae14f3d741cac0e9186c8a52a86f69501dd807e6cf91834ab654ad98c4` |
| `experiments/x0-census/scripts/runbook/logs/x0final_88_R1_regression.log` | `7f663c1d856ca6489cdd99151c0669571f1e7fd6a71cc4e89c6016c98a56935e` |
| `experiments/x0-census/scripts/runbook/logs/x0final_88_R2_mock.log` | `4d6e630d677c3adfd0e52f6e59e982dbe27d214d3b2177584319a688e3769180` |
| `experiments/x0-census/scripts/runbook/logs/x0final_probes_twin_formats.log` | `82c8858496a09443d48c59c56d400f3e74c14c1bd95272b1f32434da0fd14f51` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_70_prefreeze_win.log` | `de274e1f59db28ce317c7779bc709c77a3ab1f0a2eeaea3d50ffd3004a689f99` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_71_prefreeze_wsl.log` | `0c4374e0e2da91af7bdffaf86f13e7f19d16edbfd07709b73b645a658d4776ca` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_71b_regression_compile_wsl.log` | `597e8383537690af68a655cfa3735428afb4c63db62bd29392e297ea9e63c900` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_72_regression_check.log` | `df9c4c9b501e77db6076e8f0c246764a280b01d6830398c37f3bc5107bc9f969` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_72_smoke_dispatch_check.log` | `5d741762d982598926a086f6629daa1d9f506510b3ddac4ce86988a2b487f2a6` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_avs.log` | `0739b0494b68b0a3dcbb405ac9d7feb957d292f44f222f296489be17d158c25b` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_norm2.log` | `da0e33f722bc85fbfaa79e576a168117f73fbdf2363b86b2c89d0e2f22f4c58e` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_xed_tables.log` | `041939c6baac010aae67af07f74adddfa3e7fc74295e6ad6f78abc03be579424` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_zoo.log` | `0528832924f7e4ff1d5f10cf983efa162ddeeafc700a923ec023bc36d891538d` |
| `experiments/x0-census/scripts/smoke/results/x0final/R1reg_probe_sequences.txt` | `8d523a9f17966deecc5b876c4a8e45041fb5366c18fd49175d072fd24babb7ad` |
| `experiments/x0-census/scripts/smoke/results/x0final/R1reg_summary.json` | `2c0c75dfb016ed598bff5521d97bfe91e01334140a2feb452b1bc3e8932049d1` |
| `experiments/x0-census/scripts/smoke/results/x0final/R1reg_verdict.json` | `7dc5ee983d16bf540165479fcbc6f314278db49f42f35d6dde903ae1709f0c74` |
| `experiments/x0-census/scripts/smoke/results/x0final/R1reg_verdict_regression_profile.json` | `9f78a285f9286c2741a89223f25791d48b76675d4610cf9d961e623809b3161b` |
| `experiments/x0-census/scripts/smoke/results/x0final/R2mock_summary.json` | `36afe307a9ac3fdfd4ba1e6fbca8b3ac032f1abeb4a0aef4af92b716d18b23aa` |
| `experiments/x0-census/scripts/smoke/results/x0final/R2mock_verdict.json` | `9524ad5e70c6ebbea854e032aef053a27d8c51566f255c231ea095fc38d01d07` |
| `experiments/x0-census/scripts/smoke/results/x0final/R2mock_verdict_synthetic_rederivation.json` | `75f4ada28d5e5c03d75029cfcb008a5bfbdbc86497ef452bb865c7be8e9845b1` |
| `experiments/x0-census/scripts/smoke/results_dispatch.json` | `d8af4f4069a85c4bf882d3ac6a0ae759c91497378c92b2b4fe2e82bfa43d9f67` |
| `experiments/x0-census/scripts/smoke/results_regression.json` | `7595305bfba6d285400ef7d6478317974b0924719ea632f17d769bc868fb1ed6` |
| `experiments/x0-census/class/objdump_norm_validation.json` | `9db4093e7ec1c0bac7c05fb537e0778cc37dd9e9380e0902ad6890eaad953f0c` |
| `experiments/x0-census/scripts/runbook/logs/x0final_rev_probes.log` | `bf63918f784cafbe595a495363ab6b8b2dac86fc94c6e10ead19c41f56681936` |
| `experiments/x0-census/scripts/runbook/logs/x0final_rev_88_R2_mock.log` | `4b40568a7bf49909d20071138e01f305db8b2a0b0e9921f09394d918930d7652` |
| `experiments/x0-census/scripts/runbook/logs/x0final_rev_88_R1_regression.log` | `ca199d46e273d5a14873b5dc6ec1173b9e04a8f2b36da987ea6442509b6ee747` |
| `experiments/x0-census/scripts/runbook/logs/x0final_rev_fallback.log` | `07de90a2fe420ec0c75ca4b57c656cb9c8f2d6f9ec4cc2be79c737dffef1ee02` |
| `experiments/x0-census/scripts/smoke/results/x0final_rev/R1reg_probe_sequences.txt` | `5c32cba501296e553a20335cec0ff1f5abd3c1e94fdedffa30c7d5def9ebb17f` |
| `experiments/x0-census/scripts/smoke/results/x0final_rev/R1reg_summary.json` | `8d3d94b8d8c0c2c13c40d9f80a0c96d0a698ce47464b5f75c0bd8e05a178af2c` |
| `experiments/x0-census/scripts/smoke/results/x0final_rev/R1reg_verdict.json` | `70639505c4292318b33f827c6e62dff60218837e6d8b84588f4c09d1e30e507b` |
| `experiments/x0-census/scripts/smoke/results/x0final_rev/R1reg_verdict_regression_profile.json` | `be7b03ed43cc21e4ad14ba7dc1a568130c39525172deeff411496aa8d2862fca` |
| `experiments/x0-census/scripts/smoke/results/x0final_rev/R2mock_probe_sequences.txt` | `31fd5829762dd7c107b1c017758c00ab718b3658722a0756e4ba71cc329b8990` |
| `experiments/x0-census/scripts/smoke/results/x0final_rev/R2mock_summary.json` | `9d696de9ee288f74a30c5b0157c225a829a5d7f20941ce8536610a9246fad45d` |
| `experiments/x0-census/scripts/smoke/results/x0final_rev/R2mock_verdict.json` | `86cc69bf074baf7215da4eca80879fd07f9fe85b44e8c6aa9063a976839a0a3a` |
| `experiments/x0-census/scripts/smoke/results/x0final_rev/R2mock_verdict_synthetic_rederivation.json` | `8075588fe4e1e1b6b4768ba8c6e506c1a6ad98031dbcb6a8cbefa547747ce2c7` |
| `experiments/x0-census/scripts/runbook/logs/prefreeze_rerun_first_88_R2_mock.log` | `184d52ba736947b09522ef98aca9c51fb7b2edefd07d9893c70186af555e78f1` |
| `experiments/x0-census/scripts/runbook/logs/prefreeze_rerun_first_88_R1_regression.log` | `5faf2e28c5a7f31294db67aaae830e3fb8acd0b8c5c169a26562a8f113f9ad55` |
| `experiments/x0-census/scripts/runbook/logs/prefreeze_rerun_88_R2_mock.log` | `364e59be68f204bde0215ba2e0162f05bdf26cf502680450314a1ceb2bc7fa64` |
| `experiments/x0-census/scripts/runbook/logs/prefreeze_rerun_88_R1_regression.log` | `b341b1409efa44073a22d8771bf3dff6529eb1fa616017077cd26c96ddc827dd` |
| `experiments/x0-census/scripts/runbook/logs/prefreeze_rerun_checks.log` | `0fe28f4c064adf27225d7a0e6222ca264e6cc4b907714201350c5023031d50de` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/first_R2mock_summary.json` | `0b3c54077a7c14f8d18955462c5f2c902682542e7a5cd4941b69400e5d294c71` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/first_R1reg_summary.json` | `0e6906cd659d061265d29b7f28cfedd0f45b4c9c48e09e2cab600cdb848f29e8` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/R2mock_summary.json` | `04e2a547c28d1053db29436d4b02eb51fc4520ba8b621a07ec2211f7c943d40e` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/R2mock_verdict.json` | `fbdd09a8438974fc4ca9c43ec791b82422ee88f7d9b3c2e1d021901c046030df` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/R2mock_verdict_synthetic_rederivation.json` | `622691e7dc42efc1b8d63b2f90f178807e92764386346917b791d9534509b929` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/R2mock_probe_sequences.txt` | `14832cf5890acd145612683bf075d61534acd8b053b174d3904f8ff95d142ac3` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/R1reg_summary.json` | `e0614271dd74cd77c0f3d769413bad29b03e7289974e7dec0e069e9a81598aae` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/R1reg_verdict.json` | `a9317cea0d7a75df3219f974ce5c61ac388b54ddbfcc464dea3ce879d206a5d3` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/R1reg_verdict_regression_profile.json` | `fd0378e383eb8e06ba577b244bb52660e092acd77a33935b66464887ee9eb520` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/R1reg_probe_sequences.txt` | `041f5ec72bd6f3de12c157d93dc13843e3f884ce3b693ec36b404759e04d3656` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/gitlogic_throwaway.json` | `65dcf27c4c356a030d735b10f61f9147441d90edd63597b84bdf4e8f96c5cf00` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/tools/code_compare.py` | `9b28ba3e5c7f705f533baa2e8ae75f7f712f020beca1eb93af445509c5a3e1a3` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/tools/code_detail.py` | `ae076c647e29e5179468ca5fd92e2699bba6db2208330d767eb1fc5b96fccd01` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/tools/flag_analysis.py` | `13766282f338aa46868d477cb4b51d71b5cfcc4e681fa783df8f1b64a1fe9ca1` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/tools/gitlogic_test.py` | `b2e96311a704cb7686832916450a5f8544668d23953be58708c2683bec0ffd2a` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/tools/headers_check.py` | `defc33841ef5b7ff781f4c02a61bbfadb0db097f48a69f0ebadc4fa7afe232ff` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/tools/init_one.py` | `c115c6ae249b0a3bf1a43d505a63f525c1fb81b4a982c2815d9fdf140a772271` |
| `experiments/x0-census/scripts/smoke/results/prefreeze_rerun/tools/loops_debug.py` | `1b5ddda5ba7511b7769e7f9c90c4cf28366cef253b84b5a079a7a4013660196e` |

### D4
| File | SHA-256 |
|---|---|
| `experiments/x0-census/flags/prefreeze/B-proxy.argv.json` | `7f43b546a44d417eff1fc1cf206acd1dbd702940f4953a6f9799852bc6c8dae3` |
| `experiments/x0-census/flags/prefreeze/README.md` | `643f377dbf407f7014316cf676f0a6c209a7ae69a4410e5e8ee0b54210557e36` |

### D5
| File | SHA-256 |
|---|---|
| `experiments/x0-census/class/fp_class.csv` | `7cabb6913437c364f7d02c988a839ed5807462a3812cacd86e68a1c72a686c2f` |
| `experiments/x0-census/class/fp_class_summary.json` | `f8e4c69ba2ffee8a9dab9eafb8ad19f64bfc5dbc468d20b22bef5981f9caed78` |
| `experiments/x0-census/class/xed_tables.tsv` | `1db25e7f5f02b5796d06cbb94f4cb5ab7d8230ed1091bacae485fa5c517d1d13` |
| `experiments/x0-census/scripts/classify.py` | `9f094eff8cb12551ea0b5a7f4b41cd68dca3ece161e8ab273336076e065e1b4c` |
| `experiments/x0-census/scripts/xed_tables.c` | `8190b2504589a94a0c7007692877818283059e5ea6ca7b1cfa28dfae53a097d0` |

### D6
External input: rust-lang/stdarch `eb9b3025937c85bd271a3ca46a681cd52739db12`, `intrinsics_data/x86-intel.xml`,
SHA-256 `6762a50652a35ef663fd532ed83b789d19bbc2ac7e94b1771f19d666d96c2c30` (not stored here; the driver's step 82
hashes the desktop copy `D:\mithril\x0prep\x86-intel.xml` into `census.json`, and V4 compares it with this pin).

| File | SHA-256 |
|---|---|
| `experiments/x0-census/class/B_iform.json` | `a66e1a935d887a272d5f3fb868d10a1877f8e4d7b26137a3962079b1edcb1eaa` |
| `experiments/x0-census/class/hand_map.csv` | `008f558ead3ee86b9484f8891470f51db0e10dbf8591a8509ca20c4219ad5d3e` |
| `experiments/x0-census/scripts/baseline.py` | `6245e3017d43d550679e1ebb86e36837e85fd613b63a4e775d5c07a1cd67a9e6` |

### D7
| File | SHA-256 |
|---|---|
| `experiments/x0-census/class/fp_flag_patterns.txt` | `181ab6e8b9cffbe12dd2d7bbeb4bf7a6aeed36161bc8e4ec2692261bf8a42dbc` |

### D8
| File | SHA-256 |
|---|---|
| `experiments/x0-census/class/objdump_norm.csv` | `d6196d60246a08733ca1581d83e81cc8be9891223e2750323b250c50dbc6e2e7` |
| `experiments/x0-census/scripts/x0_norm.py` | `a165b3572c91ffc544c8bd4b54f8475f2769b6b1e5888bc6a660464cd11fc0a6` |
| `experiments/x0-census/scripts/runbook/gen_norm_csv.py` | `8b9f6f441b89881565d3dc24dd0de8dd594e8267592c09c4a7647115a1dfa0ef` |

### D9
| File | SHA-256 |
|---|---|
| `experiments/x0-census/class/loop_table.csv` | `0d94b2e636fb355e3c3c56d9b452dfef6a00925860adda05e116fe99b22a35be` |

### D10
| File | SHA-256 |
|---|---|
| `experiments/x0-census/scripts/probes/reduce_probe.c` | `1c04d4157d733a6dc5f8c0e7d5284973e7855345345ffbd4366680965b5d7888` |

### D11 (every pinned input of V4: the class files and every file under `scripts/` except run outputs and documentation; `class/frozen_inputs.json` holds the same map; the freeze records the scripts' commit)
| File | SHA-256 |
|---|---|
| `experiments/x0-census/class/B_iform.json` | `a66e1a935d887a272d5f3fb868d10a1877f8e4d7b26137a3962079b1edcb1eaa` |
| `experiments/x0-census/class/fp_class.csv` | `7cabb6913437c364f7d02c988a839ed5807462a3812cacd86e68a1c72a686c2f` |
| `experiments/x0-census/class/fp_flag_patterns.txt` | `181ab6e8b9cffbe12dd2d7bbeb4bf7a6aeed36161bc8e4ec2692261bf8a42dbc` |
| `experiments/x0-census/class/hand_map.csv` | `008f558ead3ee86b9484f8891470f51db0e10dbf8591a8509ca20c4219ad5d3e` |
| `experiments/x0-census/class/loop_table.csv` | `0d94b2e636fb355e3c3c56d9b452dfef6a00925860adda05e116fe99b22a35be` |
| `experiments/x0-census/class/objdump_norm.csv` | `d6196d60246a08733ca1581d83e81cc8be9891223e2750323b250c50dbc6e2e7` |
| `experiments/x0-census/class/xed_tables.tsv` | `1db25e7f5f02b5796d06cbb94f4cb5ab7d8230ed1091bacae485fa5c517d1d13` |
| `experiments/x0-census/scripts/baseline.py` | `6245e3017d43d550679e1ebb86e36837e85fd613b63a4e775d5c07a1cd67a9e6` |
| `experiments/x0-census/scripts/classify.py` | `9f094eff8cb12551ea0b5a7f4b41cd68dca3ece161e8ab273336076e065e1b4c` |
| `experiments/x0-census/scripts/judge.py` | `d8c8da25d8f65b76e6910b415a17c716c1863786c68ad4d4da49c15913567cc5` |
| `experiments/x0-census/scripts/probes/reduce_probe.c` | `1c04d4157d733a6dc5f8c0e7d5284973e7855345345ffbd4366680965b5d7888` |
| `experiments/x0-census/scripts/runbook/05_clone_sources.sh` | `5784af19f7d0a468b0ef23c08392310ba77de22f17adcd96507a9fef66833c6c` |
| `experiments/x0-census/scripts/runbook/10_fetch_llvm.cmd` | `0f347586ae948b2ec7f24b9621026933ae8a9abd87c8e0ce370601c9a99a382b` |
| `experiments/x0-census/scripts/runbook/11_verify_llvm.ps1` | `fd4a6f2d778004ca6d96e8d36f690fe1ca2c8a3def6d949f39fdc6e69deeddc5` |
| `experiments/x0-census/scripts/runbook/12_extract_llvm_win.cmd` | `ebdfe75fa71ded46bee1b919e0812d5d04aa1d89de79d1c4a6eef9bb83ab0def` |
| `experiments/x0-census/scripts/runbook/13_extract_llvm_linux.sh` | `662d3bfbb25bc7bbe9047238e9067e04d96799a75bd6af506dabddebd6ef75ee` |
| `experiments/x0-census/scripts/runbook/20_fetch_verify_cmake.ps1` | `25a2d7388f2ce6b6612d999db9f0489cef77d0507be7b46ed245541a946db94e` |
| `experiments/x0-census/scripts/runbook/21_extract_cmake_linux.sh` | `d0a5956bf46ae5e1161478317d8cfbfcc2e003aa84c1bbb97dd3cba136853024` |
| `experiments/x0-census/scripts/runbook/22_verify_cmake.ps1` | `c89d3aef4e4422acb80b3179920274682dbfc3d5701cbbbf12e6a8a9defd1565` |
| `experiments/x0-census/scripts/runbook/30_build_xed_wsl.sh` | `77c880f164ceb005aeafb0953ea40feedf0b1e1babbe44c7ce6ba27c69ed3859` |
| `experiments/x0-census/scripts/runbook/31_build_xed_win.cmd` | `3ac69a40fe8d4bd653635ed5b4e023b277a4eeac7c5c53586172590d9b032161` |
| `experiments/x0-census/scripts/runbook/40_verify_win.cmd` | `75a8ace24229ea16db95a55270edd5b7bbec0573a012f04eb6c86fa93c3b29be` |
| `experiments/x0-census/scripts/runbook/41_verify_wsl.sh` | `999cd1e55cc692e73c365ba35a29bc284928019ca5823e48ffafbbc8e78ad125` |
| `experiments/x0-census/scripts/runbook/50_configure_win.cmd` | `7277af90255ec9851e8c27d511c9a6a7ed0c41cf51a20ab5e267af19f9029801` |
| `experiments/x0-census/scripts/runbook/51_configure_wsl.sh` | `7b0d35ce1836de814868db01ac3d4179f292ff5d5a8a7c115e5786f7436a4794` |
| `experiments/x0-census/scripts/runbook/60_smoke_win.cmd` | `a150e82cd7d3a56da8eb7731e5973538632eb5d0634d6ae42941fba2a0a7bcdb` |
| `experiments/x0-census/scripts/runbook/61_smoke_wsl.sh` | `02660f1acbf04951f1b82b75740be352f69433bfb2e3b88e6611bb5cadf35d30` |
| `experiments/x0-census/scripts/runbook/62_smoke_decode_win.cmd` | `19490bce189b38a32862efb08691d9de9bccd0dadd159a856e690c82732f8947` |
| `experiments/x0-census/scripts/runbook/68_xed_tables_win.cmd` | `eced4c0ea8ad74fec4999283247c5cdbb8bd7992c6fe5031c345a1b97e98c403` |
| `experiments/x0-census/scripts/runbook/69_zoo_norm_check_win.cmd` | `41f021b2ded6b9e7ad51ff5a585b819a0dc24bad6c3a495613c7949ae154b9b7` |
| `experiments/x0-census/scripts/runbook/70_prefreeze_win.cmd` | `85364237aeeb1d63cdd2cc297535655ea1190ffcd994baab2c31934575cd856d` |
| `experiments/x0-census/scripts/runbook/70b_a_vs_design_time.cmd` | `4f3f7900439307bdcb3bb0319bd83698cd995e7f7f5769571f3c625e73a7b5e0` |
| `experiments/x0-census/scripts/runbook/71_prefreeze_wsl.sh` | `8f83ecb6517c26ee5c43fa4ef850d47a5eb42c71c58fa219763ffd7579efe351` |
| `experiments/x0-census/scripts/runbook/71b_regression_compile_wsl.sh` | `4fd3bc705875458d76dc8ec43d420d118e5173674e981855c1579b1d0f501c60` |
| `experiments/x0-census/scripts/runbook/72_smoke_dispatch_check.cmd` | `7e5b85f13499ffe19a71f14cbb6221d33b03df563f47bd66a7db77e757c0ed26` |
| `experiments/x0-census/scripts/runbook/79_census_init.cmd` | `df01e496f080aae1e9b0978f60dc8321cff8d6aebbb9a9e5f46879aba53ded61` |
| `experiments/x0-census/scripts/runbook/80_census_win.cmd` | `cbda42f370622c7efa133ceb30783a155f788b83922346616f514c1732c069d2` |
| `experiments/x0-census/scripts/runbook/81_census_wsl.sh` | `e97d9ad0399549ee12af76db288b018b9efa851f212a70b64afd0f313287a93c` |
| `experiments/x0-census/scripts/runbook/82_census_assemble.cmd` | `122bad870e9470e8164d825080f02f4525cf1775fc9771dde82ff763b52c7619` |
| `experiments/x0-census/scripts/runbook/86_mock_prefreeze_win.cmd` | `ccd47ff2dc0f3ec7d4a673716c75cf64ee82a06e8b785f2a1e87c9f9b17ce05f` |
| `experiments/x0-census/scripts/runbook/86_mock_prefreeze_wsl.sh` | `2377aeca99f47894fa8978309aa179c416a2d0ba506c4c806eab573484f90f35` |
| `experiments/x0-census/scripts/runbook/88_x0final_smoke_runs.ps1` | `2314abe3d5125d5c6cdf6fc973f5195a4e2cf05c9bd931801597c2fe8bb1c211` |
| `experiments/x0-census/scripts/runbook/bproxy_set.json` | `ae82de9e2ffe697913961724fd4f985734180f24e6b2fc30464dacec0cb98762` |
| `experiments/x0-census/scripts/runbook/cc1flags.py` | `c9259244556d544c3c5c0b2a245c75e1af51af8d4d806a8a0327bb8b9d6cfc9c` |
| `experiments/x0-census/scripts/runbook/census_tools_win.json` | `39396c67ed068efab59a8c55d2efa47ec1d4ab9bd40196f10b21836a1e7832bb` |
| `experiments/x0-census/scripts/runbook/census_tools_wsl.json` | `d9c68c51b86e48d4b747e760cad018f9facbc89d6b6e6fbd05b616cad990092b` |
| `experiments/x0-census/scripts/runbook/compare_decodes.py` | `c57d89dfcd3fae363fbed16e2a02ab068c01f4f62536e7fe789cc6ef6448cefb` |
| `experiments/x0-census/scripts/runbook/design_time_lines.py` | `3c9ce976eb477c07201c406f07769117b0afa9b11d0d8c4346dd65e6bcffbf7e` |
| `experiments/x0-census/scripts/runbook/gen_norm_csv.py` | `8b9f6f441b89881565d3dc24dd0de8dd594e8267592c09c4a7647115a1dfa0ef` |
| `experiments/x0-census/scripts/runbook/hearth_shingles.py` | `5dd2457b6073f00e0488f1d140f47ca40f3e136a6e30d1c3bfd4c704372d3f3f` |
| `experiments/x0-census/scripts/runbook/negtest.py` | `8e4d1dc04560b83c742259ffca1409aeec4fc844a04c8f5d2b8060146737a242` |
| `experiments/x0-census/scripts/runbook/negtest_dispatch.py` | `09471e5ae80a9e87758f401c1a11ea8f044529e64e2e13af3b1de2d5621689a4` |
| `experiments/x0-census/scripts/runbook/pin_inputs.py` | `4c87f3bb7b50e2dc94c07d221d9949fc6cd9bf35a40930cd1c424edc7cedd953` |
| `experiments/x0-census/scripts/runbook/probes/atomic_probe.c` | `16f9a0ee48afab092e0efed7f3c23e4633eba1f0d6766c33571ecf4a7e9cded3` |
| `experiments/x0-census/scripts/runbook/probes/fpc.c` | `77904ec7d0c2aebaff68cc9bae1ab60cc832e56e7d12e72293bf849329e6c1a4` |
| `experiments/x0-census/scripts/runbook/probes/hello_avx2.c` | `305a3a147bcb91179ee7c879a871909940d4e23f85628fa2f622d4603604b626` |
| `experiments/x0-census/scripts/runbook/probes/hello_avx512.c` | `1014fa234d4837d33138a0cb77de1c507df0cae85b63f1f17bbad7d04a11c640` |
| `experiments/x0-census/scripts/runbook/probes/vnni_probe.c` | `4e69827634c762df3e6145c83c28c7738114d6666394dbed36bd9837bd9d774c` |
| `experiments/x0-census/scripts/runbook/summarize_regression.py` | `c6de989cb8e91f2747dbf19f7524313ae4a4ebe65a0b6b672eb732e0b7bc1a92` |
| `experiments/x0-census/scripts/runbook/summarize_x0final.py` | `277cb52dfb2156d67a7f0a2327c2de34dfb5a6439c84ddafc4c631d3df441e5a` |
| `experiments/x0-census/scripts/runbook/zoo_fix.py` | `39750be8f32133e6e42f8025fc251ce219ba5f8674fe3b70ea6f03ba56722426` |
| `experiments/x0-census/scripts/smoke/check_regression_run.py` | `3a654362777d38fbd97e9bcf063d8ab6ef0984d1d5325f718d760eca4c527b8a` |
| `experiments/x0-census/scripts/smoke/check_smoke.py` | `ccf1978fdc5caa538ba18d1a9d0c64862f2b50c6a97cef9c51249bf1b7f371c4` |
| `experiments/x0-census/scripts/smoke/gen_zoo.py` | `78e87c4a14b34b87f852d601a56f750788f63d07fbe3437069bc1c81cbe63382` |
| `experiments/x0-census/scripts/smoke/judge_regression.py` | `ba5503809fae93d8052abf22f42e4f1516d8041655e8d9b27ab25d1f1c0fa104` |
| `experiments/x0-census/scripts/smoke/mock/CMakeLists.txt` | `e567e268389467308a28d0312594c75eefc6be786133820acbb9f25888f0eee6` |
| `experiments/x0-census/scripts/smoke/mock/X0_NOT_HEARTH` | `e501f0857c670b7f00db4f982a569a0b1bf99a43713b8ef1c2bf0098495633da` |
| `experiments/x0-census/scripts/smoke/mock/engine/src/hx_quant.h` | `2da36a6880855e6cc7beb5e94d6970fe91ff4ca7644c3d83dd5dc1af77033ea7` |
| `experiments/x0-census/scripts/smoke/mock/engine/src/other.c` | `bf6b372f1357a7600afd90b3cfc11d223851b42aaadcbe17a3a4075caf9fec2a` |
| `experiments/x0-census/scripts/smoke/mock/engine/src/quant.c` | `15786c5836c387b165379ffb82138b1a7e69055102792320b0803ea0f6febe70` |
| `experiments/x0-census/scripts/smoke/mock/engine/src/quant_avx2.c` | `60259f96549f35dc791f85af5e186eca5553637f3dbf2d32eca74a686b56d2ad` |
| `experiments/x0-census/scripts/smoke/mock/engine/src/quant_avx512.c` | `628ce4edcb7ccfab81769351b6025255d1724f964f1833ba801d129d235d0427` |
| `experiments/x0-census/scripts/smoke/norm_check.py` | `e1b3e1872512da4505a540a46c56879281739ae071252fba9ba7d4229781743b` |
| `experiments/x0-census/scripts/smoke/regression_set.json` | `87952f837a62bfc9318ccf23c6715d1bed43d7e088c52516861d93a3dfb5bbd7` |
| `experiments/x0-census/scripts/smoke/results_dispatch.json` | `d8af4f4069a85c4bf882d3ac6a0ae759c91497378c92b2b4fe2e82bfa43d9f67` |
| `experiments/x0-census/scripts/smoke/results_regression.json` | `7595305bfba6d285400ef7d6478317974b0924719ea632f17d769bc868fb1ed6` |
| `experiments/x0-census/scripts/smoke/rv_tricky.c` | `121e60b05a0898dff90b2820f55bb56c03637c770478aae4826412ae916499e8` |
| `experiments/x0-census/scripts/smoke/rv_tricky2.c` | `0045a5a968fa308e2ac1f19a9a8aeeebe395ce9e2808c1e589cca4b01059a9b5` |
| `experiments/x0-census/scripts/smoke/smoke.c` | `e43e2690a45b958994c3ebdbe3301a11f494fc1989e5a8365d3d9f33d3bd99a7` |
| `experiments/x0-census/scripts/smoke/smoke_dispatch.c` | `4424e77647e08a5c75c590b9f3c1b4ba0b798eb82419bb759951a6c9d0a24269` |
| `experiments/x0-census/scripts/smoke/smoke_loop_table.csv` | `0ee7ee7da78eacd1331ef59204b67e72ddc71e1fcb2b7de97cb73b6e0a266681` |
| `experiments/x0-census/scripts/smoke/tricky_expect.json` | `c5aa1f8c8a2ca82babffbb603012e02fbac5b5f5f7f303af36e0fa5733928a61` |
| `experiments/x0-census/scripts/tests/test_build.py` | `4a16108ec4c79a7a4d785bf7be8b5e8f6a8b25388d3dc84dd7c6405f985747b2` |
| `experiments/x0-census/scripts/tests/test_census.py` | `e4e33ec8858e688d7e336e6d765c25949928e19ec2577e599d430933d2e87854` |
| `experiments/x0-census/scripts/tests/test_driver_guard.py` | `199fed0ed0ea793f140cc51b619597645e6ea222d26324ee0bed856ef4ea2d48` |
| `experiments/x0-census/scripts/tests/test_flags.py` | `358209c1edafebcaefb4d39da26bf5ff177c4c284364bdc7712dd4be10e84112` |
| `experiments/x0-census/scripts/tests/test_judge.py` | `0a44d881e49bc7bf411ca70f2fd8b2480bb220bdd769551e201f4cd0b60cd72a` |
| `experiments/x0-census/scripts/tests/test_loops.py` | `1f8c5e9c2c343f138a65342a1525834bc063f1214b1c32cb3e383da22967f811` |
| `experiments/x0-census/scripts/tests/test_loops_prefreeze.py` | `831b8364b8c1fb16daad3c3fb9149253810cb3ea8eaa5556ee020deb9d0c0af9` |
| `experiments/x0-census/scripts/tests/test_loops_x0final.py` | `a4cc721eea6f13f2c090e5445e0bd60ad3a4055e970982785d687a099adf9530` |
| `experiments/x0-census/scripts/tests/test_twin.py` | `e7ffdbfc1ec3000b57f69a490189d35e01ee0b4f572347e0133521a0a89bb581` |
| `experiments/x0-census/scripts/x0_build.py` | `24914445b6545ae332ad4683e0a779fbdbb54c3373719c8c7b509a2f25f85d2a` |
| `experiments/x0-census/scripts/x0_census.py` | `37bb743918899a5a752d47184e905423e75a40b073d860976c91fe8aa1992176` |
| `experiments/x0-census/scripts/x0_decode.py` | `f2eae8e33fc08f9b2ca8cb3ee7c9f42f1910d0c5b943d2404d162753a83eaa8d` |
| `experiments/x0-census/scripts/x0_driver.py` | `924302e3c2051456afb6552ca3b97a5444dd27b83ba0c4140b80b73b4fc6da01` |
| `experiments/x0-census/scripts/x0_extract.py` | `97c1f52f4b3730cd9431e2da0f2f3f3b3c22ec723f6150ab95631291708e05df` |
| `experiments/x0-census/scripts/x0_flags.py` | `60b1e74da0560cbb95ba4016fc38fd0c23b6381a05dc3a06f70280a32c059233` |
| `experiments/x0-census/scripts/x0_loops.py` | `8c7ecc9e6a29b4ec8398661ffca9c225a2fccf7f1e1af3f9d24cd04e78df3799` |
| `experiments/x0-census/scripts/x0_norm.py` | `a165b3572c91ffc544c8bd4b54f8475f2769b6b1e5888bc6a660464cd11fc0a6` |
| `experiments/x0-census/scripts/x0_twin.py` | `d6d34b344e98fe64d17b4d7cb743a5929846563204a2d983dd7888383349d341` |
| `experiments/x0-census/scripts/x0obj.py` | `dbd4e07c836cfd189a1f10dfca2535b9de3c4142b733aee7b32d594c5fbbe981` |
| `experiments/x0-census/scripts/xed_tables.c` | `8190b2504589a94a0c7007692877818283059e5ea6ca7b1cfa28dfae53a097d0` |

### Other files of this preparation
The record's hash changes when its status line changes to FROZEN; it is listed for traceability only.
`class/hearth_shingles.json` is the smoke guard's input (record §2), not a census input, so it is not in V4; the
pre-freeze review revision remade it (pairs, comments stripped, 13 allow-listed structural lines) with
`scripts/runbook/hearth_shingles.py` from the read-only clone's files. `class/frozen_inputs.json` gained the header pins,
and the desktop re-run re-pinned it (`x0_loops.py`, `tests/test_loops_prefreeze.py`). The check tools of the re-run
(`smoke/results/prefreeze_rerun/tools/`) are evidence, not census inputs, so they are not pinned.

| File | SHA-256 |
|---|---|
| `experiments/x0-census/class/frozen_inputs.json` | `5b4d7c08b3837a7094d5bf87d1a6f89c137966e7b9aa3dac3b7d3496d0737219` |
| `experiments/x0-census/class/hearth_shingles.json` | `6c72698ee5b9894b9b4e8fd456f98781ef64b65b17f846cd655cff68162efb54` |
| `experiments/x0-census/class/README.md` | `9b741092c21c229c81d6f47084f096055ca3e33738a2a00dff19f01c530a3626` |
| `experiments/x0-census/rederive/PROCEDURE.md` | `01bb49402ff8f5c2de879f3b89f49f0130f60c3c2055f7e724989bf1b7a69ea9` |
| `experiments/x0-census/scripts/README.md` | `5e1995ef37164ff4b221f3d2d14a298475f2f874abbe382acb6704ae8f18ba56` |
| `docs/m0/prereg/X0-census.md` | `1a5e2df1ab4f0ac5c61c5cecd494db07c72632c2b1c74b9be96b15a83ba75577` |

## Desktop footprint of this preparation (for Pierce)

- x0prep: new on D: `D:\mithril\x0prep\` (sync copy of the scripts, configure trees A-vs / A-ninja / B-cmake, the
  instruction zoo, smoke and regression objects, flag captures, the stdarch XML) and `D:\mithril\jobs\x0prep\`
  (logs). C: one WSL VM start (step 71) with a detached keepalive `wsl.exe -d Ubuntu --exec sleep 43200`, started
  because none was running; it adds one WSLg trace file under `%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\`
  (about 23 MB each, see `TOOLCHAINS.md` §9). No file on C: was deleted. No system setting was changed. GPU not used.
- x0final (2026-10-16 22:48 to 2026-10-17 00:35 EDT): new on D: `D:\mithril\x0final\` and `D:\mithril\jobs\x0final\`.
  WSL ran only inside the keepalive VM that was already up. One compiler or MSBuild node at a time, XED `-j 2`;
  `CUDA_VISIBLE_DEVICES=-1` in every job; no GPU.
- x0final revision (2026-10-17 01:03 to 01:57 EDT, i.e. before the 23:00 PT quiet window): new on D: only
  `D:\mithril\x0final-rev\` (the probe project, the decoder outputs for the reviewer's `rvx.c`, sync copies of
  `experiments/x0-census`, the runs `runs\R1reg`, `runs\R2mock`, `runs\RFmockerr` and the mock's captures
  `runs\mockfrozen`) and `D:\mithril\jobs\x0final-rev\` (logs). Read only: the x0final reviewer's NON-Hearth objects
  under `D:\mithril\review-x0final\`. WSL only inside the keepalive VM already up (x0prep's, started 18:08 EDT, expiring
  about 06:08 EDT: a later WSL step needs a new detached keepalive, which means a new WSLg trace file on C:). One
  compiler or MSBuild node at a time, XED `-j 2`, `CUDA_VISIBLE_DEVICES=-1`, no GPU. Nothing written on C:, no
  system setting changed, no Hearth file compiled, no Hearth object decoded, the Hearth working tree, the WSL home
  objects and GEMS files not touched.
- pre-freeze review revision (2026-10-17, during the 23:00-07:00 PT quiet window): laptop only. No desktop or SSH use,
  no compile, no decode, no git command; it read the read-only Hearth clone's source text (blob hashes verified in
  Python), existing NON-Hearth outputs already on the laptop (the x0prep reviewer's `rv_tricky` decodes, the x0final
  revision run's `config.json` copies) and the first mock's sources (to check that the new guard refuses them). Its
  desktop re-run is item 1 above.
- desktop re-run (2026-10-17 03:21-03:56 EDT, i.e. 00:21-00:56 PDT, inside the 23:00-07:00 PT window by the lead
  engineer's authorisation for that night, which was not a pilot quiet night): new on D: only `D:\mithril\x0reg\` (two
  sync tarballs and copies of `experiments\x0-census` (`x0-census_first` at 2191ff8, `x0-census` re-pinned), the runs
  `runs_first\` and `runs\` (mockfrozen, R2mock, R1reg), the throwaway repository `gitwork\` with its harness
  `gitlogic\`, the concatenated logs `logs\` and four helper scripts; 330,834,098 bytes in 5,560 files) and
  `D:\mithril\jobs\x0reg\`, `D:\mithril\jobs\x0reg_first\` (job logs; `TEMP`/`TMP` pointed there; steps 80 and 86 also
  use `D:\mithril\jobs\x0final\tmp` as before). Read only: `D:\mithril\x0final-rev\runs` (decode comparison), the
  Hearth clone's git HEAD and the seven files' blob hashes (`git rev-parse` and Python; no `git status`, no compile, no
  decode). WSL only inside the keepalive VM started 2026-10-16 18:08 EDT (no new VM start, so no new WSLg trace file).
  One compiler or MSBuild node at a time, XED `-j 2`, at most 4 threads, `CUDA_VISIBLE_DEVICES=-1`, no GPU, one job at
  a time. No system setting changed; no git add, commit or push in the Mithril repository (read-only git commands on
  the laptop only; the throwaway repository's commits set the identity with `-c` for each command, no configuration
  written). C: [M, scan of `%LOCALAPPDATA%\Temp`, the WSLg trace folder and the profile's top
  level for files written after 03:15]: three 0-byte `<GUID>.tmp` files in `%LOCALAPPDATA%\Temp` at 03:54:59 and
  03:55:35, after every job had ended [I: written by the SSH PowerShell sessions of the last two checks or by another
  process of the account; not attributable with certainty]; they were left in place. Nothing else.

## Post-freeze tooling fix X0-A1 (appended 2026-10-23 by the x0fix track; revised the same day after its review)

Everything above this heading is the freeze-time text and is unchanged. This section is appended. It is the long form
of Amendment X0-A1 to the record. Whether and when that amendment was appended to the record is shown by the record
itself; this section is not edited when it is. **It contains census run 1 outputs and describes `x0_loops.py`, so a
fresh re-deriver must not receive it** (`rederive/PROCEDURE.md` §1).

**Statement on Hearth objects (D12 for X0-A1).** X0-A1 compiled no Hearth file and decoded no Hearth object. It
re-ran `x0_loops.py` read-only on census run 1's existing decodes, manifests, attribution files and objects
(`D:\mithril\x0census\run1`, post-data), and compiled and decoded only NON-Hearth files: the reproduction
`scripts/smoke/a1/a1_escape.c` (shingle guard: 0 shared pairs), the mock and the regression set.

**Owner approval.** X0-A1 is post-data and removes P3(c) flags, the direction favourable to Pass. DELEGATED.md's
limits exclude such a change from the delegation, so it is provisional, pending Pierce. `judge.py` reports the verdict
both ways (`verdict.json` `both_ways`).

**What changed.** See the amendment (X0-A1.1, the operative rule) and `results/tooling_fix_A1/README.md` §1:
- `scripts/x0_loops.py`: escaping stack slots (`FrameInfo`) are plain memory for the P3(c) quantity only; every other
  loop field keeps the frozen reading; a loop whose P3(c) count or partial results differ between the readings is
  `unscreened` (loop fields `unscreened`, `unscreened_reason`, `escaping_slots`, `escaping_partial_results`,
  `acc_lanes_if_escaping_slots_were_registers`, `escape_events`; variant fields `p3c_unscreened`,
  `p3c_frozen_reading`);
- `scripts/x0_census.py`: carries the two variant lists into `census.json`, adds `metrics.x0_a1` and one note per
  unscreened loop;
- `scripts/judge.py`: `both_ways`, the decision list under the frozen reading; schema check of the two lists;
- new tests and the NON-Hearth reproduction.

**Hashes before and after X0-A1** (SHA-256 of the bytes on disk; `pin_inputs.py --write`, then 0 differences on the
laptop and in the desktop's r2 tree). The freeze-time tables above keep the freeze values; for these files the value
after X0-A1 is the one here.

| File | SHA-256 at the freeze (152fa33) | SHA-256 after X0-A1 (r2) |
|---|---|---|
| `experiments/x0-census/scripts/x0_loops.py` | `8c7ecc9e6a29b4ec8398661ffca9c225a2fccf7f1e1af3f9d24cd04e78df3799` | `5519a568568ba80db3c5f12080820b4d0e049a99099e5de5fd59382021282812` |
| `experiments/x0-census/scripts/x0_census.py` | `37bb743918899a5a752d47184e905423e75a40b073d860976c91fe8aa1992176` | `1f8e482b48a42603baca0e5e8cf224d1f4e20c381b2db1ebe70711e46b832859` |
| `experiments/x0-census/scripts/judge.py` | `d8c8da25d8f65b76e6910b415a17c716c1863786c68ad4d4da49c15913567cc5` | `b3104348eb10bc338f877a38c31382b55cc98ffcc67a8c7f93ab5739f5acf4bf` |
| `experiments/x0-census/scripts/tests/test_loops_a1.py` | (new) | `a98b09252074e3f21c8a3220612f770c8509ffdbf0ed1ffab30a38c4e6f4aa34` |
| `experiments/x0-census/scripts/tests/test_a1_census_judge.py` | (new) | `fc03262a553e37a0ffc284f1d9ee1956e9281fdad1ce3977f42a9818f93d26b1` |
| `experiments/x0-census/scripts/smoke/a1/a1_escape.c` | (new) | `9e2e93add5e590bbf00989f5a631c231202fc349e06d5c7ad345fce3415c24a5` |
| `experiments/x0-census/scripts/smoke/a1/a1_loop_table.csv` | (new) | `f23a90c652a00077d05b059c1df32672006abbce8d32803a0fef6abfc23632aa` |
| `experiments/x0-census/scripts/smoke/a1/a1_set.json` | (new) | `e326915d6e15009fc047a3e2350a989451acba3d3a68fb02d877112fd5530bb5` |
| `experiments/x0-census/class/frozen_inputs.json` | `5b4d7c08b3837a7094d5bf87d1a6f89c137966e7b9aa3dac3b7d3496d0737219` | `d3ba19a9fcc954a83eff094f8cdbd3b0c08f0fc009cd25da0ec4ede76fd142b0` |
| `experiments/x0-census/scripts/README.md` (documentation, not pinned) | `5e1995ef37164ff4b221f3d2d14a298475f2f874abbe382acb6704ae8f18ba56` | `65382689a0334b10d9b67abcc3b6f8aa5c1b69f906d4442e5d81065818aac386` |

`class/frozen_inputs.json` also gained `_provenance.x0_a1`, which records this re-pin (`pin_inputs.py --write`
rewrites `_provenance.written` with fixed text, so the note is kept in a key of its own).

**Checks run** [M, 2026-10-23]. Details are in `results/tooling_fix_A1/README.md` §4.

1. *Unit tests.* 215 pass on the laptop: 183 earlier, 25 in `test_loops_a1` and 7 in `test_a1_census_judge`.
2. *Re-pin.* `pin_inputs.py --write` found 5 differences against the rev1 pins, then 0, on the laptop and in the
   desktop's r2 tree.
3. *Laptop pre-check* on NON-Hearth decodes kept on the laptop: 2,395 loops; 30 change, all unscreened, and only in the
   P3(c) fields.
4. *NON-Hearth reproduction* `smoke/a1/a1_escape.c` (shingle guard 0 pairs; run `smoke-20261023T160057Z`, the r2
   script re-run on its decodes): the pinned script flags 16 loops per build (B-cmake 2, C 6, D 8), the r2 script 0,
   with all 40 loop records `unscreened` at their frozen counts; only the P3(c) fields change.
5. *Regression replay, runbook steps 86 and 88 with the r2 tree*: R2 `smoke-20261023T172426Z` and R1
   `smoke-20261023T174221Z`, `pin_inputs.py` at 0 differences.
   - `check_regression_run.py` finds **0 deviations** (60 decode outputs, 420 variants).
   - The decodes are byte-identical to the 2026-10-17 final runs. P3(c) flags are unchanged (0 removed, 0 added).
   - 30 loop records under C are `unscreened` (R1 12, R2 18; the address-taken `L[16]` arrays), none flagged under
     either reading. Only the three P3(c) fields change on them; every other field is identical.
   - Summaries and verdicts differ from the 2026-10-17 ones only in run ids, dates, tree paths and the new `both_ways`
     block and note. Every outcome is unchanged, and `both_ways` gives the same outcomes under the frozen reading.
6. *Census run 1, read only* (`D:\mithril\x0census\run1`; no compile, no decode, no census).
   - P1 to P5 before/after (`results/tooling_fix_A1/run1/p1_p5_before_after.tsv`): only P3(c) under C changes, 4 → 0
     flagged loops and 2 → 0 flagged variants per build. P4 446, P5_iclass 32 and P5_opclass 15 before and after.
   - The 8 removed flag records are C `k_avx512` Q8 and Q4 at quant_avx512.c:316 and :352, both builds: exactly the 4
     census-only V3 mismatches of REPORT §10. None is added.
   - 14 loop records are `unscreened`, all under C: those 8, and C scalar quant.c:362 (6 records, no flag either way).
     A and A-ninja `k_avx2` Q8 quant_avx2.c:240, unscreened under rev1, is screened under r2: the only event that
     made its slot escape under rev1 (a call in the epilogue) follows the loop.
   - Only `acc_lanes_emitted`, `partial_results` and `partial_result_cycles` change, on the 14 unscreened records;
     every other field is identical.
   - Cause (a), the address-taken and stored array, applies to every removed flag. Cause (b), the variable-count
     `rep stosq` inside the loop, is present in every one, but alone it is not a sound kill.

**Not done.** X0-A1 r2 is not independently reviewed (its rev1 was; the review's 18 findings are handled in r2). No
census re-run from an amended commit; no fresh re-deriver; `REPORT.md`, `census.json` and `verdict.json` are not
regenerated. Due before the bound of 2026-11-12.

**Desktop footprint of X0-A1 (for Pierce).** Details in `results/tooling_fix_A1/README.md` §7.
- rev1 (2026-10-23, 11:32-12:27 EDT): new on D: `D:\mithril\x0fixA1\` (225,311,377 bytes at 12:24 EDT) and
  `D:\mithril\jobs\x0fixA1\`. Two WSL keepalives started by the track left the WSLg traces
  `RdClientAutoTrace-WppAutoTrace-20261023-153224-185.etl` (23,592,960 bytes) and `…-20261023-153508-687.etl`
  (104,857,600 bytes; rev1 had reported it as 0 bytes at 12:24 EDT, before it was written out) under
  `%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\` on C:.
- r2 (13:04-13:52 EDT): new on D: `D:\mithril\x0fixA1\r2\` (182,152,437 bytes in 2,824 files) and
  `D:\mithril\jobs\x0fixA1\r2\` (117,386 bytes in 73 files). One keepalive (pid 24364, 13:04:20-13:50:03 EDT) left
  `RdClientAutoTrace-WppAutoTrace-20261023-170421-962.etl` (104,857,600 bytes) on C:.
- A few small files in `%LOCALAPPDATA%\Temp` on C: written in those windows (0-byte `<GUID>.tmp`, `.ses`,
  `mat-debug-*.log`, `cv_debug.log`, a Visual Studio download set) were not attributed with certainty and were left in
  place.
- No system setting changed; at most 4 threads, one compiler at a time, `CUDA_VISIBLE_DEVICES=-1`, no GPU; the Hearth
  working tree, the WSL home and GEMS not touched; nothing deleted (the D: folders above remain for Pierce or the lead
  engineer to remove).
