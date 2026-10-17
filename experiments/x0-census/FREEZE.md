# X0 freeze checklist

Record: [`docs/m0/prereg/X0-census.md`](../../docs/m0/prereg/X0-census.md), status **DRAFT**. Prepared by the
x0prep track on 2026-10-16 (Claude; laptop DESKTOP-F441IUK for authoring, desktop DESKTOP-8RS9J1J for the
tool runs). This file is the long form of the record's Appendix D.

**Verdict of this checklist: NOT ready to freeze.** Eleven of the twelve items have their artefacts and hashes.
The x0prep review of 2026-10-16 (record §12; Claude, same family, independent context) closed D5 and D6. One item
and one review remain open:
- **D11 is incomplete.**
  - The `census.json` assembler is not written. It must also record the build fields `judge.py` now requires:
    compiler hashes, structured errors, include lists, and `ab_compare` per A-ninja variant.
  - The debug-info twin attribution of §4.6 is not implemented: DWARF via `llvm-dwarfdump`, CodeView via
    `llvm-readobj --codeview`, and the twin identity check. So P3(c) runs unattributed (variant-wide bound), and
    every P3(d2) site is `unchecked`.
  - The peeled and interchanged tags are not computed. §4.7 handles that strictly for the narrowing.
- **The reviser's post-review revisions are unreviewed.** These are the record's Appendix E rows marked
  "post-review", the reworked `x0_decode.py`, `x0_extract.py` and `judge.py`, and the regression set. Like
  every Appendix E change, they need an independent review (record §12) before freeze. So do the §4.7 unit
  change and `loop_table.csv`, which the 2026-10-16 reviews did not cover.

No Hearth source was compiled and no Hearth object was decoded to produce anything listed here (record §2,
statement D12). Hashes are SHA-256 of the file bytes in this working tree [M, x0prep, 2026-10-16]: LF line
endings for every text file except `.cmd` files, which `.gitattributes` keeps as CRLF on every checkout, so the
values are the same on Windows and Linux checkouts. Recompute them at freeze; they must not change between this
list and the freeze commit except where a review changes a file (then the record's Appendix D and
`class/frozen_inputs.json` change with it).

## Summary

| # | Artefact | Path | Status | Missing |
|---|---|---|---|---|
| D1 | Toolchain pins, Table 2.1 | `TOOLCHAINS.md` §11; record Table 2.1 | done [M] | none |
| D2 | Flag captures (configure-only; `-###`, `gcc -Q`) | `flags/prefreeze/`, `flags/C-gcc.*`, `flags/D-clang.*` | done [M] | A's exact build lines exist only once the census build runs (by design, §2); the design-time lines omit `/O2` |
| D3 | Smoke-test logs, NON-Hearth only | `scripts/runbook/logs/` | done [M]; post-review regression (steps 71b, 72) added | none (the previous draft's Hearth compile smoke test was removed) |
| D4 | B-proxy and H argv | `flags/prefreeze/B-proxy.argv.json`, `flags/prefreeze/README.md` | done | H uses `--shared` (record choice, review) |
| D5 | `fp_class.csv` (+ `classify.py`, XED tables) | `class/`, `scripts/` | done [M]; reviewed 2026-10-16 (blind sample of 197 iclasses, 197/197 agree; `reason` column reworded in record §4.4, CSV unchanged) | none |
| D6 | `B_iform.json`, `hand_map.csv`, stdarch commit, XML hash, values in §4.5 | `class/`, record §4.5 | done [M]; reviewed 2026-10-16 (independent re-derivation: identical) | none |
| D7 | `fp_flag_patterns.txt` | `class/` | done | none |
| D8 | `objdump_norm.csv` | `class/` | done, validated on a NON-Hearth corpus [M] | none |
| D9 | `loop_table.csv` | `class/` | done (62 loops, checked against the source) [M] | none |
| D10 | Reduce probe (arm P) | `scripts/probes/reduce_probe.c` | done, syntax-checked under A, B-cmake, C, D [M] | none |
| D11 | Scripts §4.2, §4.7, §8, tested only on smoke | `scripts/` | §4.1/§4.2 and §8 done, revised after the 2026-10-16 review and tested (56 judge tests; 24-object regression, 0 deviations); §4.7 partial | **census.json assembler; twin attribution (P3(c) exact bounds, P3(d2) site selection); peeled/interchanged tags; independent review of the post-review revisions**; the scripts' commit hash (the commit that adds them) |
| D12 | Statement: no Hearth compile before freeze | record §2; `TOOLCHAINS.md` §11 | done [M] | interactive SSH commands of the tooling session are unlogged; that part rests on that track's account |

Also required before freeze, outside Appendix D: the record's status line changed to FROZEN in the freeze
commit; the Owner's signature (D0-12; X0 is authorised for collection per the relayed chat answer, still to be
ratified at the first weekly signing session).

## What was run, with results [M]

| Run | Where | Result |
|---|---|---|
| `classify.py` (+ `--check`) | laptop | 1,995 iclasses, 624 FP-sensitive, 4 SDM-no/XED-yes (LDMXCSR, VLDMXCSR, STMXCSR, VSTMXCSR), 0 default-rule rows, 0 self-check problems; deterministic |
| `baseline.py` (+ `--check`) | laptop | 130 intrinsics, 23 no single instruction, \|B_iform\| 102, \|B_mnem\| 74, T_forms 102, 105 XML form strings, 1 hand-mapped instruction, 0 problems; deterministic |
| Unit tests `scripts/tests/` (80, after the 2026-10-16 review; 51 before) | laptop | all pass: `judge.py` decision list (56 tests on synthetic `census.json`, including every adversarial case of the review), P3(a) matcher on synthetic tokens and on the real pre-freeze captures (7), loop analysis, `track_tree16` and the d1 canary on synthetic instruction records (17) |
| Step 68: `xed_tables.c` against pinned `xed.lib` | desktop | built and run, rc 0; 9,001 iforms, 1,995 iclasses, 11,018 decoder entries |
| Step 69: instruction zoo + `norm_check.py` | desktop | 26,553 instructions, 982 XED iclasses (320 FP-sensitive), 0 iclass disagreements after the table, 1 boundary disagreement (linear sweep through MSVC jump-table data) |
| Steps 70, 70b, 71: pins and flag captures | desktop (Windows; WSL with keepalive) | all configure runs rc 0; only CMake's own probe objects in the configure trees; `-###` and `gcc -Q` rc 0; smoke compiles rc 0; reduce-probe syntax checks rc 0 |
| Step 72, first version (superseded): `x0_extract.py`, `x0_decode.py`, `x0_loops.py` on `smoke_dispatch.c` x 8 objects | desktop | 12/12 slots resolved by relocation in every object; 0 tooling gaps; 0 cross-decoder disagreements; `llvm-readobj` cross-check clean; d1 canary found in all 8; P3(c) flags clang's two-accumulator vectorisation of the smoke file's scalar `L[i & 15]` tail loop under B-cmake and D lines (smoke code, not investigated); negative test fails as required |
| Steps 71b and 72 after the review: `smoke_dispatch.c`, `rv_tricky.c`, `rv_tricky2.c` x 8 command lines (24 objects, 168 variants), each decoded twice (lifo, fifo), checked by `smoke/check_smoke.py` against `smoke/tricky_expect.json` | desktop (WSL with the existing keepalive; Windows `-j 2`) | 0 deviations; lifo and fifo `variants.json` byte-identical for all 24 decodes; `smoke_dispatch.c` as before (12/12 slots, 6 designed `fp_trust_dep`, 0 tooling gaps, 0 cross-decoder disagreements, d1 pass in all 8) except \|U_iform\| of B and B-scalar (149 to 148, 121 to 120; INT3 after clang-cl's `/GS` failure call no longer reached); the adversarial functions give the expected outcome in every configuration (record §7); negative test fails as required |

Not run: any Hearth compile or decode; the twin attribution (not written); a census.json end-to-end run
(no assembler); the H arms and the B-proxy arm on any code (argv only); the reduce probe beyond syntax checks.

## Hashes per item

### D1
| File | SHA-256 |
|---|---|
| `experiments/x0-census/TOOLCHAINS.md` | `e403759021e50f7e720b885c72b307cd49b854debbec4348d75af3e60bb0d7d6` |

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
| `experiments/x0-census/scripts/runbook/logs/x0prep_xed_tables.log` | `041939c6baac010aae67af07f74adddfa3e7fc74295e6ad6f78abc03be579424` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_zoo.log` | `0528832924f7e4ff1d5f10cf983efa162ddeeafc700a923ec023bc36d891538d` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_norm2.log` | `da0e33f722bc85fbfaa79e576a168117f73fbdf2363b86b2c89d0e2f22f4c58e` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_70_prefreeze_win.log` | `de274e1f59db28ce317c7779bc709c77a3ab1f0a2eeaea3d50ffd3004a689f99` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_avs.log` | `0739b0494b68b0a3dcbb405ac9d7feb957d292f44f222f296489be17d158c25b` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_71_prefreeze_wsl.log` | `0c4374e0e2da91af7bdffaf86f13e7f19d16edbfd07709b73b645a658d4776ca` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_72_smoke_dispatch_check.log` | `5d741762d982598926a086f6629daa1d9f506510b3ddac4ce86988a2b487f2a6` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_71b_regression_compile_wsl.log` | `597e8383537690af68a655cfa3735428afb4c63db62bd29392e297ea9e63c900` |
| `experiments/x0-census/scripts/runbook/logs/x0prep_72_regression_check.log` | `df9c4c9b501e77db6076e8f0c246764a280b01d6830398c37f3bc5107bc9f969` |
| `experiments/x0-census/scripts/smoke/results_dispatch.json` | `d8af4f4069a85c4bf882d3ac6a0ae759c91497378c92b2b4fe2e82bfa43d9f67` |
| `experiments/x0-census/scripts/smoke/results_regression.json` | `7595305bfba6d285400ef7d6478317974b0924719ea632f17d769bc868fb1ed6` |
| `experiments/x0-census/class/objdump_norm_validation.json` | `9db4093e7ec1c0bac7c05fb537e0778cc37dd9e9380e0902ad6890eaad953f0c` |

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
SHA-256 `6762a50652a35ef663fd532ed83b789d19bbc2ac7e94b1771f19d666d96c2c30` (not stored here).

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

### D11 (scripts as of this list; the freeze records their commit)
| File | SHA-256 |
|---|---|
| `experiments/x0-census/scripts/x0obj.py` | `dbd4e07c836cfd189a1f10dfca2535b9de3c4142b733aee7b32d594c5fbbe981` |
| `experiments/x0-census/scripts/x0_flags.py` | `60b1e74da0560cbb95ba4016fc38fd0c23b6381a05dc3a06f70280a32c059233` |
| `experiments/x0-census/scripts/x0_extract.py` | `c045ed3a8839fa420b6947a603b27746e5bd23ad02d9bb33d79261f1ed6053aa` |
| `experiments/x0-census/scripts/x0_decode.py` | `44dd9b33f9ba06d7c150e711928b45472edcd9bb9f23cfbecfffb23e69c0e4f9` |
| `experiments/x0-census/scripts/x0_loops.py` | `2a0f250003e40b19cc833918e169307b157efe7bafcad0124af5e89368de1b5a` |
| `experiments/x0-census/scripts/judge.py` | `2e8ab045e737f896e5b75aff68af9241a7870a54820c5ca649df49ded928fe2e` |
| `experiments/x0-census/scripts/tests/test_flags.py` | `358209c1edafebcaefb4d39da26bf5ff177c4c284364bdc7712dd4be10e84112` |
| `experiments/x0-census/scripts/tests/test_judge.py` | `829a10cc3f95e979cb76b4c09cac76c1e2efb7c31af3ccf58c8364207303d741` |
| `experiments/x0-census/scripts/tests/test_loops.py` | `1f8c5e9c2c343f138a65342a1525834bc063f1214b1c32cb3e383da22967f811` |
| `experiments/x0-census/scripts/smoke/smoke.c` | `e43e2690a45b958994c3ebdbe3301a11f494fc1989e5a8365d3d9f33d3bd99a7` |
| `experiments/x0-census/scripts/smoke/smoke_dispatch.c` | `a59508a6bf989d6b264b4716c3bd77abc759b3b75b200243aae93f525bee55a2` |
| `experiments/x0-census/scripts/smoke/smoke_loop_table.csv` | `0ee7ee7da78eacd1331ef59204b67e72ddc71e1fcb2b7de97cb73b6e0a266681` |
| `experiments/x0-census/scripts/smoke/gen_zoo.py` | `78e87c4a14b34b87f852d601a56f750788f63d07fbe3437069bc1c81cbe63382` |
| `experiments/x0-census/scripts/smoke/norm_check.py` | `e1b3e1872512da4505a540a46c56879281739ae071252fba9ba7d4229781743b` |
| `experiments/x0-census/scripts/smoke/rv_tricky.c` | `121e60b05a0898dff90b2820f55bb56c03637c770478aae4826412ae916499e8` |
| `experiments/x0-census/scripts/smoke/rv_tricky2.c` | `0045a5a968fa308e2ac1f19a9a8aeeebe395ce9e2808c1e589cca4b01059a9b5` |
| `experiments/x0-census/scripts/smoke/tricky_expect.json` | `c5aa1f8c8a2ca82babffbb603012e02fbac5b5f5f7f303af36e0fa5733928a61` |
| `experiments/x0-census/scripts/smoke/check_smoke.py` | `ccf1978fdc5caa538ba18d1a9d0c64862f2b50c6a97cef9c51249bf1b7f371c4` |
| `experiments/x0-census/scripts/runbook/68_xed_tables_win.cmd` | `eced4c0ea8ad74fec4999283247c5cdbb8bd7992c6fe5031c345a1b97e98c403` |
| `experiments/x0-census/scripts/runbook/69_zoo_norm_check_win.cmd` | `41f021b2ded6b9e7ad51ff5a585b819a0dc24bad6c3a495613c7949ae154b9b7` |
| `experiments/x0-census/scripts/runbook/70_prefreeze_win.cmd` | `85364237aeeb1d63cdd2cc297535655ea1190ffcd994baab2c31934575cd856d` |
| `experiments/x0-census/scripts/runbook/70b_a_vs_design_time.cmd` | `4f3f7900439307bdcb3bb0319bd83698cd995e7f7f5769571f3c625e73a7b5e0` |
| `experiments/x0-census/scripts/runbook/71_prefreeze_wsl.sh` | `8f83ecb6517c26ee5c43fa4ef850d47a5eb42c71c58fa219763ffd7579efe351` |
| `experiments/x0-census/scripts/runbook/71b_regression_compile_wsl.sh` | `4fd3bc705875458d76dc8ec43d420d118e5173674e981855c1579b1d0f501c60` |
| `experiments/x0-census/scripts/runbook/72_smoke_dispatch_check.cmd` | `7e5b85f13499ffe19a71f14cbb6221d33b03df563f47bd66a7db77e757c0ed26` |
| `experiments/x0-census/scripts/runbook/negtest_dispatch.py` | `09471e5ae80a9e87758f401c1a11ea8f044529e64e2e13af3b1de2d5621689a4` |
| `experiments/x0-census/scripts/runbook/zoo_fix.py` | `39750be8f32133e6e42f8025fc251ce219ba5f8674fe3b70ea6f03ba56722426` |
| `experiments/x0-census/scripts/runbook/summarize_regression.py` | `c6de989cb8e91f2747dbf19f7524313ae4a4ebe65a0b6b672eb732e0b7bc1a92` |

### Other files of this preparation
The record's hash changes when its status line changes to FROZEN; it is listed for traceability only.

| File | SHA-256 |
|---|---|
| `experiments/x0-census/class/frozen_inputs.json` | `2181f91b754ccbe033c6d6dbf54567802f8e6e15b4685f9559a50021faad5c7b` |
| `experiments/x0-census/class/README.md` | `4a23755022000b540113d55949dbac4b96673a1f28684960e5d629d49ff4fc92` |
| `experiments/x0-census/rederive/PROCEDURE.md` | `01bb49402ff8f5c2de879f3b89f49f0130f60c3c2055f7e724989bf1b7a69ea9` |
| `experiments/x0-census/scripts/README.md` | `a6f27cc86351c951f661dde0d7e9eaf8667f6e12079cbc04b6be7836352d4fea` |
| `docs/m0/prereg/X0-census.md` | `e1243b4e75121e642cf7d7f2c3406b3c10b098ba8644bfa5bdf179c0aab41894` |

## Desktop footprint of this preparation (for Pierce)

- New on D: `D:\mithril\x0prep\` (sync copy of the scripts, configure trees A-vs / A-ninja / B-cmake, the
  instruction zoo, smoke objects, flag captures, the stdarch XML) and `D:\mithril\jobs\x0prep\` (logs). Nothing
  was deleted or changed outside them; the earlier `D:\mithril\x0` trees were only read.
- C: one WSL VM start (step 71) with a detached keepalive `wsl.exe -d Ubuntu --exec sleep 43200`, started
  because none was running; it adds one WSLg trace file under
  `%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\` (about 23 MB each, see `TOOLCHAINS.md` §9). No file on C:
  was deleted. No system setting was changed.
- GPU: not used (`CUDA_VISIBLE_DEVICES=-1` in every job). Threads: one per job, at most two jobs at once.
- After the review (reviser, 2026-10-16, 19:21 to 19:39 EDT):
  - new on D: `D:\mithril\x0prep\reg\` (24 regression objects and their decode outputs) and logs and a
    disassembly listing under `D:\mithril\jobs\x0prep\`;
  - the synced scripts in `D:\mithril\x0prep\x0\` were refreshed;
  - WSL ran only inside the keepalive VM that was already up, so no new VM start and no new trace file;
  - read-only `find`/`ls` in the WSL home for the D12 re-check;
  - at most 2 threads (decode `-j 2`, one job at a time); no GPU;
  - nothing deleted outside the track's own directories; reviewer 2's `D:\mithril\review-x0prep\` was only
    listed (its outputs were read from the laptop copy).
