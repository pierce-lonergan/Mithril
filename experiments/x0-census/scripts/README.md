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
| `x0_loops.py` | §4.7, P3(c), P3(d1), P3(d2) | CFG and dominators per closure function, natural loops, flow-sensitive loop-carried FP accumulators (registers and constant stack slots; lane-0 semantics for scalar ops), emitted lanes and updates per iteration, inductions, tags (lockstep, unrolled, rotated, software-pipelined, auto-vectorised, spilled), P3(c), the d1 canary, and the d2 lane-provenance tracker (`track_tree16`) |
| `x0_norm.py` | §7 | The objdump -> XED iclass normaliser used by `x0_decode.py` |
| `classify.py` | §4.3, §4.4 | `class/fp_class.csv` from `class/xed_tables.tsv` |
| `baseline.py` | §4.5 | `class/B_iform.json` from the Hearth source, the stdarch XML and `class/hand_map.csv` |
| `judge.py` | §8 | `verdict.json` from `census.json` and the frozen inputs (Gatekeeper): schema check, completeness (A-ninja comparison, P3(a) results, coverage), compile rule with compiler pins, V1 to V4 (V4 includes `xed_tables.tsv`, every script and the compiler pins), conservative resolution after the week-3 bound, recomputed P2, P3(b), V2 and Amber (a), narrowing. The evaluation date is max(system UTC date, latest census run) |
| `xed_tables.c` | §4.4 | Dumps XED's own tables (`class/xed_tables.tsv`); link against the pinned `xed.lib` / `libxed.a` |
| `smoke/smoke.c`, `smoke/smoke_dispatch.c` | | NON-Hearth smoke files. `smoke_dispatch.c` mirrors the shape of Hearth's tables |
| `smoke/gen_zoo.py`, `smoke/norm_check.py` | §7 | Instruction zoo from the XML; normaliser validation |
| `smoke/rv_tricky.c`, `smoke/rv_tricky2.c` | §4.2 | Adversarial NON-Hearth regression inputs written by reviewer 2 of the x0prep review (indirect tail calls next to jump tables, GCC `.cold` switch cases, adjacent tables, calls through an extern function pointer, user no-return calls, overlapping decodes, MSVC byte index tables) |
| `smoke/tricky_expect.json`, `smoke/check_smoke.py` | §4.2 | Expected outcome per function and configuration, and the checker runbook step 72 uses (also checks lifo/fifo identity and the smoke d1 canaries) |
| `smoke/results_regression.json` | | Compact record of step 72's outputs (`runbook/summarize_regression.py`) |
| `smoke/smoke_loop_table.csv` | | Source loop table of `smoke_dispatch.c` (smoke only) |
| `probes/reduce_probe.c` | §3 arm P | The reduce probe (NOT Hearth code) |
| `tests/` | | Unit tests on synthetic inputs: `python -I -m unittest discover -s experiments/x0-census/scripts/tests` |
| `runbook/` | | Desktop job scripts in run order (see `../TOOLCHAINS.md` §8 and §11) |

## Census pipeline (after freeze, per configuration and build)

```sh
# 0. build the hearth_core objects of the configuration (record §2: A via MSBuild with a binary log; others Ninja/Make)
# 1. dispatched variants and object model (one --pair per census file)
python -I x0_extract.py -o M.json --struct hx_kernels --struct-src <hearth>/engine/src/hx_quant.h \
    --index-names F32,F16,BF16,Q8,Q4,I32,U8 --expect-variants 18 --label <CFG> --readobj <llvm-readobj> \
    --pair <hearth>/engine/src/quant.c=<obj> --pair <hearth>/engine/src/quant_avx2.c=<obj> \
    --pair <hearth>/engine/src/quant_avx512.c=<obj>
# 2. closure, decode, cross-decoder (at most 2 worker threads on the desktop)
python -I x0_decode.py M.json -o DEC --xed <xed> --objdump <llvm-objdump> -j 2
# 3. loops, P3(c), canaries (default variant map and canary: Hearth's)
python -I x0_loops.py DEC --manifest M.json -o LOOPS.json [--attribution ATTR.json]
# 4. census.json assembly (Appendix C) and the Gatekeeper
python -I judge.py census.json -o verdict.json        # evaluation date = max(system UTC date, latest census run)
```

Not yet written (record Appendix D, item D11; see `../FREEZE.md`): the census.json assembler (which must also record, per build, the compiler binaries' SHA-256, structured errors and the include list, and per A-ninja variant `ab_compare`; record Appendix C), the debug-info twin
attribution (DWARF via `llvm-dwarfdump --debug-line`, CodeView via `llvm-readobj --codeview`) with the twin
identity check of §4.6, and therefore the selection of P3(d2) sites (every site is `unchecked` without it).

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
