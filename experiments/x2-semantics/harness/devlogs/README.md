# Development logs of the x2build track (2026-10-16)

**Development data, not data under the X2 record.** Nothing here comes from `budget.v1`. These files
document the harness build and self-tests, the interpreter validation, the guard checks, and the development
smoke run on the hand vectors of `semantics/selftest.py` (harness/README.md §7-§8). Two runs are kept:

- **Revised build** (after the same-family, independent-context review; `run_final.cmd`, desktop clock
  21:51:40 to 21:52:10): the files without a suffix.
- **First build** (`run_final.cmd`, 19:10:31 to 19:11:02): the same files with the suffix `.build1`.

| File | What |
|---|---|
| `final.log` | log of `run_final.cmd`: build, self-tests (x2fuzz 9 steps incl. the exhaustive silicon plumbing check), guard checks G1-G7, validation, dev smoke, throughput |
| `valid.report.json` | C interpreter against the Python oracle: 1,000,006 lane cases, 0 divergences |
| `gen_selftest.log` | generator self-test: plan against budget, F-MEMFAULT zero-masking duplicates, masked-BCAST synthetic row |
| `devsmoke.report.json` | dev smoke comparison: per-cell counts, the 3 B6 flag disagreements, hand-vector agreement, provenance |
| `devsmoke.cpu4.fingerprint.json`, `devsmoke.cpu20.fingerprint.json` | fingerprints of the two runs (CCD0, CCD1) |
| `exhaustive_selforacle_throughput.json` | exhaustive engine with the interpreter as its own oracle (2^28 lane cases, no silicon) |
| `xsec.report.json` | the review's development cross-section (DEV-REVIEW-X2BUILD) re-compared with the revised comparator (harness/README.md §7, §9) |
| `mutants.summary.json` | seeded-table-mutant calibration on that cross-section (harness/README.md §9) |

## 2026-10-23 rebuild for the X2 freeze (x2freeze track)

Development data, not data under the X2 record (harness/README.md §13). Files with the suffix `.20261023`:

| File | What |
|---|---|
| `build.20261023.log` | stub generation (664 stubs, 0 errors) and the MSVC build |
| `selftests.20261023.log` | `run_selftests.cmd`: x2fuzz selftest, semantics selftest, compare and generator self-tests, interpreter validation |
| `gen_selftest.20261023.log` | generator self-test summary (plan = budget on 576 rows) |
| `valid.report.20261023.json` | C interpreter against the Python oracle: 1,000,006 lane cases, 0 divergences |
| `guards.20261023.log` | `run_guards.cmd`: G1-G7 refused |
| `devsmoke.20261023.log`, `devsmoke.report.20261023.json` | dev smoke on the rebuilt harness: 0 mismatches |
| `devsmoke.cpu4.fingerprint.20261023.json`, `devsmoke.cpu20.fingerprint.20261023.json` | fingerprints of the two runs |
| `mutants_devsmoke.20261023.log`, `mutants_devsmoke.summary.20261023.json` | the 24 sealed table mutants against the dev smoke results (21 detected) |

## 2026-10-23 revision-4 rebuild (x2freeze track, after the review of the X2 record's revision 3)

Development data, not data under the X2 record (harness/README.md §14). Files with the suffix `.20261023d`, the
same set as above: `build`, `selftests`, `gen_selftest`, `valid.report`, `guards`, `devsmoke` (log, report,
`cpu4`/`cpu20` fingerprints), `mutants_devsmoke` (log, summary). Converted from the desktop's UTF-16 to UTF-8 with LF
line ends; content unchanged. Result: every self-test PASS, 0 interpreter divergences, G1-G7 refused, dev smoke 0
mismatches, 21 of 24 table mutants detected.

After a docstring-only correction of `gen_vectors.py` (final LF sha256 `4261242d…a6e2`), its self-test and the guard
checks were re-run on the desktop with the final file: `gen_selftest.20261023e.log` (PASS, plan = budget on 576
rows), `guards.20261023e.log` (G1-G7 refused).
