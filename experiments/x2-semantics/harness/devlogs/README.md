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
