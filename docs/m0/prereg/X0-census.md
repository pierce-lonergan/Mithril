# X0: instruction census of Hearth's quant kernels

Status: DRAFT (to be FROZEN at the commit that first adds it with this line changed to FROZEN, and
not before every item of Appendix D is done)
ROADMAP anchor: [§3.1](../../ROADMAP.md#31-x0-instruction-census-weeks-015); DR-008; G02 open question 6
Owner authorisation: **answered on both parts of OQ-6, pending ratification at sitting 1 (Sunday 2026-10-18)**:
the instruction part through D0-12 ([OWNER-QUEUE.md](../OWNER-QUEUE.md) R3, "D0-12i CONFIRMED") and the spend part
through D0-10a (R1: metered budget $0) [M, OWNER-ANSWERS.md and OWNER-QUEUE.md, read 2026-10-17]. Until ratification
the answers are decisions as stated in chat, not yet AUTHORITY facts (OWNER-ANSWERS.md preamble; OWNER-QUEUE.md
"Status, one wording in every owner-track file").
- **OQ-6, instruction part (lead engineer's note, 2026-10-17; restated by the reviser after the pre-freeze review of
  2026-10-17).** Pierce's batch-1 answer to the D0-12 question is recorded verbatim in
  [OWNER-ANSWERS.md](../OWNER-ANSWERS.md) (commit 11210a8, cited as in D0_BRIEF, not re-checked with git): "Batch
  weekly review" [M, OWNER-ANSWERS.md]. The option text he selected read: "You sign all records ready that week in one
  sitting. Collection under any record waits for that sitting, except X0, which you already authorised." [M, same
  table]. The lead engineer reads this as Pierce confirming the X0 collection instruction [G: the lead engineer's
  reading of an option text the lead engineer wrote and Pierce selected; OWNER-QUEUE R3 records the same reading,
  "D0-12i CONFIRMED", for confirmation at sitting 1]. On that reading collection runs once this record is FROZEN; the
  Gatekeeper's verdict still waits for the signature at the weekly sitting (collection rule, below).
- **OQ-6, spend part.** D0-10a's answer, verbatim, is "No metered API" [M, OWNER-ANSWERS.md]; OWNER-QUEUE R1 reads it as
  a metered budget of $0, with Claude work on the Claude Code plan only, and lists "X0 OQ-6's spend cap ($0 metered)"
  among what it settles [M, OWNER-QUEUE.md]. The earlier draft's proposal of $1.5k for X0 [inference, ROADMAP §3.1
  upper bound] is superseded. Collection is local compilation and decoding on the desktop and the laptop.
- If sitting 1 does not ratify either reading, or Pierce withdraws the instruction, collection stops and every result
  collected so far is marked as collected under an unratified or withdrawn authorisation.
- History, kept for provenance: the previous draft quoted an Owner instruction of 2026-10-16, "Start the parts that
  need no owner decision: X0, instruction census", whose only other copy, in
  [D0_BRIEF §4.1](../../D0_BRIEF.md#41-d0-12-pre-registration-sign-off), asked Pierce to confirm or withdraw it [M,
  reviser, repository grep, 2026-10-16]; [PLAN.md](../PLAN.md) §1 and §8 repeat it. The user request relayed on
  2026-10-16, "please do this on ultra code mode and you have permission to do whatever you need to do to fulfil this
  project in its entirety", is read by the lead engineer as operational permission that does not delegate the D0
  owner decisions (OWNER-ANSWERS.md). The x0prep track's relayed account of the chat answers (D0-12 batch weekly
  review with the X0 exception; D0-10 no metered API; the only other family the local Qwen3 pilot) is superseded by
  the verbatim log in OWNER-ANSWERS.md; its sentences that these answers "do not answer [OQ-6] formally" and that
  "nothing else in D0 is decided" no longer hold (pre-freeze review of 2026-10-17).
- Under the [collection rule](../README.md#pre-registration-lifecycle-roadmap-1-rule-1-d0-12), the
  Gatekeeper evaluates no verdict until the record is SIGNED.

Pre-freeze preparation. The x0prep track (2026-10-16) produced the Appendix D artefacts, reworked the census
scripts, and changed this DRAFT where Appendix E lists. It compiled no Hearth source and decoded no Hearth
object; every validation used NON-Hearth smoke files (§2; but see §2 for the Hearth lines that `smoke_dispatch.c`
carried until 2026-10-17). The same track revised the scripts and this DRAFT
after its own independent review of 2026-10-16 (§12; Appendix E rows marked "post-review"), under the same
restriction. The x0final track (2026-10-16, evening) added the missing D11 pieces (the build records, the debug-info
twin attribution, the `census.json` assembler and the census driver) and the record text they needed (Appendix E rows
marked "x0final"), and validated them end to end on NON-Hearth inputs only (§2, §7). The x0final revision (2026-10-17)
handled the independent review of the x0final work (§12): it disclosed that the first census mock contained verbatim
Hearth helpers (§2, E6), replaced the mock, made the Gatekeeper, the build records, the accumulator and source-loop
rules, the twin attribution and the freeze-commit tie stricter (Appendix E rows marked "x0final revision"), and re-ran
the end-to-end validation (§7). The pre-freeze review revision (2026-10-17, laptop only) handled the independent review
of the x0final revision and of the lead engineer's OQ-6 and ruling edits (§12): it disclosed that the regression file
`smoke_dispatch.c` carried Hearth's own lines (§2, E6), widened the E6 label to the P3(c) results those lines bear on,
strengthened the shingle guard, made the accumulator and source-loop rules count what they missed, tied the census to
the freeze point and re-checked the pinned scripts at every step, pinned the header environment, and corrected the
header's authorisation text (Appendix E rows marked "pre-freeze review"). Its end-to-end re-run on the desktop was made
on 2026-10-17: the first run raised P3(c) flags through dependency-breaking idioms, which one pre-freeze tooling fix
removed, and the final run with the re-pinned scripts shows the x0final revision's outcomes (§4.7, §7, Appendix E row
"desktop re-run"). The record stays DRAFT.

Conventions. Evidence tags follow [docs/m0/README](../README.md#evidence-tags). "Reviser" means the
agent that revised this DRAFT on 2026-10-16. It worked on the laptop running this session (hostname
DESKTOP-F441IUK) against the read-only Hearth clone; in the sections added later, "reviser" is the agent of the revision
named there (x0final revision, pre-freeze review revision). Small integers inside definitions, such as a
register width's lane count or a list index, are definitions rather than evidence and carry no tag.
Week numbers ("week 3", "week 6") refer to M0's timeline in ROADMAP §2, whose dates are
[inference].

## 1. Assumption under test

We know which instructions real compilers emit for Hearth's kernels under Hearth's strict FP flags
[G02, open question 6]. If this is false, X2's semantics table has the wrong scope and the object
audit (B1.5) may be unsound.

## 2. Inputs pinned

**Source.** Hearth `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220`, which is GitHub `main` as of
2026-10-16 and was committed 2026-10-05T23:15:13−04:00 [M, reviser, `git rev-parse HEAD` and
`git log -1` in the read-only clone, 2026-10-16]. Census files and their git blob hashes [M, reviser,
`git rev-parse b5d3f14:<path>`, 2026-10-16]:

| Path | Blob |
|---|---|
| `engine/src/quant.c` | `e95496945c254335c0d25aafb374575e0db930fe` |
| `engine/src/quant_avx2.c` | `a2004d22fd50c62b9bffa52b77b02870cd066986` |
| `engine/src/quant_avx512.c` | `9c7586b16e589989edec35c4bf8c1eee373da886` |
| `engine/src/hx_quant.h` | `df7e75e3e14f7281e80d47b20fab67a2ab5c99cb` |
| `engine/src/hx_platform.h` | `53141baa62f703508b50c5e511617732c97f5b2e` |
| `engine/include/hearth.h` | `0bbc9c9d93da2832d8ca5a5f494c3c1e120beaec` |
| `CMakeLists.txt` | `217ca743186ac066ee7c13b4ef416bb3704e3d30` |

The census script recomputes these hashes and refuses to run on any mismatch.

- The desktop's Hearth working tree has 21 uncommitted R3 entries (17 modified, 4 untracked)
  [M, sprint brief, as recorded in PLAN.md §2; not verified by the reviser]. They are out of scope.
  The report states whether the working-tree diff touches a dispatched kernel. If a census of that
  tree is ever needed, it gets a separate record.

**Build path per configuration.** "Hearth's own flags" means the per-file command lines that Hearth's
`CMakeLists.txt` produces for `CMAKE_BUILD_TYPE=Release` (multi-config generators: `--config
Release`), with nothing added or removed. §4.6 defines the one exception, the debug-info twin.

| Config | Generator | Where the exact command line comes from |
|---|---|---|
| A | `Visual Studio 17 2022`, `-A x64`. This is Hearth's documented and CI Windows release path [M, reviser, read of Hearth `CONTRIBUTING.md:36-41`, `.github/workflows/ci.yml:159-164` and ADR-0007 line 27 at b5d3f14, 2026-10-16] | The ClCompile command lines in the MSBuild log of that build (binary log, or detailed verbosity). `CL.command.1.tlog` is a cross-check. **The census objects of A are the objects this build produces.** Pre-freeze, x0prep froze the generated `hearth_core.vcxproj` (Release ClCompile metadata: `Optimization` MaxSpeed, `InlineFunctionExpansion` AnySuitable, `FloatingPointModel` Precise, `EnableEnhancedInstructionSet` AdvancedVectorExtensions2 / AdvancedVectorExtensions512 for the two SIMD files) and MSBuild's design-time command lines (`-t:GetClCommandLines`, which runs no compiler) [M, x0prep, `experiments/x0-census/flags/prefreeze/`, 2026-10-16]. The design-time lines omit `/O2` and are therefore not the build lines; a difference between them and the binlog lines other than optimisation switches is reported |
| A-ninja (cross-check) | Ninja, `CMAKE_EXPORT_COMPILE_COMMANDS=ON` | `compile_commands.json`. CMake ignores that option under Visual Studio generators [inference, CMake documentation as recalled by reviewer 1 and the reviser; not re-checked against the pinned CMake], which is why a second build is needed |
| B-cmake | Ninja | `compile_commands.json` |
| C, D | Unix Makefiles, as Hearth's Linux CI uses it (`ci.yml:104-107` configures without `-G`) [M, reviser, read, 2026-10-16] | `compile_commands.json` |

- A versus A-ninja: for each of the three files, the code sections of the two objects are compared
  (bytes and relocation lists, §4.6). A difference is a finding. Any variant whose code differs is
  censused under both builds. A-ninja's version then joins the main union and the P2/P3 screen (§8).
- **Out of scope for the verdict: `scripts/hxcc.py`.** It is Hearth's module-level developer build
  (ADR-0007), with MSVC `/std:c17 /O2 /Oi` and, for other compilers, `-std=c11 -O2 -g`
  (`hxcc.py:125-127, 154-159`). The CMake path is the one that builds the shipped `hearth.dll` and
  the CI artefacts. hxcc builds are reported as secondary arm H (§3).
- Hearth's `CMakeLists.txt:7` says "prefer scripts/build.ps1", but that file does not exist at
  b5d3f14 [M, reviser, `ls scripts/` in the clone, 2026-10-16].
- CMake's C11 setting with extensions left on gives `-std=gnu11` to GCC and Clang
  (`CMakeLists.txt:9`). The captured lines confirm this [M, X0 tooling track,
  `experiments/x0-census/flags/quant_flags.json`, 2026-10-16]. P3(a) therefore checks *effective*
  settings, not only explicit flags.

**Pre-freeze activity, disclosed.**
- `experiments/x0-census/flags/` holds `compile_commands.json` files for A (from a non-VS
  generator), B, C and D, plus an extract, `quant_flags.json`. The X0 tooling track produced them on
  the desktop; the file times read 2026-10-16 11:28 local [M, reviser, `ls -la` and read,
  2026-10-16].
- x0prep added configure-only runs on 2026-10-16: A with the Visual Studio generator, A-ninja and B-cmake
  with Ninja (under `D:\mithril\x0prep\cfg`), and `-###` / `gcc -Q --help` expansions of each file's exact
  command line with a dummy source. Captures: `experiments/x0-census/flags/prefreeze/` (D2, D4) [M].
- **Statement on pre-freeze compilation (D12, OQ-7)** [M, x0prep, desktop scan and job-script review,
  2026-10-16 17:30 EDT; details in `experiments/x0-census/TOOLCHAINS.md` §11]: no object, archive or listing of
  any Hearth translation unit exists on the desktop's `D:\mithril`; the `hearth_core.dir\engine\src` directories
  of every configure tree are empty; every desktop job script compiles only non-Hearth files (smoke files,
  probes, XED, CMake's own checks) and none builds a Hearth target; the Hearth working tree has no build
  output (`git status --porcelain --ignored` empty). Only configure-only CMake runs touched Hearth. Not
  verifiable from files: interactive SSH commands of the tooling session are not logged; for those the
  statement rests on that track's own account.
  Outside `D:\mithril`, the desktop's WSL home holds objects of the three census files from Hearth's own
  development, not b5d3f14 census builds and built with other flags, including ASan and TSan builds:
  `/home/pierce_lonergan/hx_t02v/obj_tq/quant{,_avx2,_avx512}.o` and `obj_tq_asan/` (2026-10-04 11:40),
  `t08g2/tsan/quant{,_avx2,_avx512}.o` and `t08g2/obj_*quant*.o` (2026-10-04 18:53). No `.o` under `/home` is newer
  than 2026-10-15 [M, x0prep review scan (reviewer 1) and the reviser's read-only `find`/`ls` re-check, desktop,
  2026-10-16]. No Mithril track produced, read or decoded them. Census and re-derivation agents must not open them.
- x0final (2026-10-16, evening) completed the freeze kit (Appendix D, D11) and ran the census driver end to end on
  NON-Hearth inputs only: the regression files and the reduce probe with the frozen command lines, and a census
  *mock* (`scripts/smoke/mock/`, Hearth's table shape and CMake flag logic, marker file `X0_NOT_HEARTH`), configured
  and built under A, A-ninja, B-cmake, C and D. It compiled no Hearth *file* and decoded no Hearth object; the driver
  refuses a smoke run on any file whose bytes are a pinned Hearth blob, and refuses a census run unless this record
  reads FROZEN [M, x0final, `scripts/runbook/logs/x0final_*`]. The first version of the mock was not Hearth-free,
  however: see the disclosure below. The x0final revision (2026-10-17, after the independent review of §12) replaced
  the mock and re-ran the end-to-end runs (§7).
  - **Disclosure: arm P was observed before freeze.** The x0final task asked for the end-to-end run to include the
    reduce probe, and x0final compiled and decoded `scripts/probes/reduce_probe.c` with the frozen `quant_avx512.c`
    lines of A-ninja (also standing in for A), B-cmake, C and D, and with the census mock's lines. §3 calls the
    probe's emitted sequences census data, so arm P's outcome is known before freeze for those lines [M, x0final,
    `scripts/smoke/results/x0final/`]: the `_mm512_reduce_add_ps` wrappers give the halving tree (`match`) under C
    (both wrappers) and under D (the by-value wrapper; the loading wrapper is `unchecked`); under A-ninja (MSVC uses
    `vpsrldq`) and B-cmake (Clang loads the halves with memory-operand adds) they are `unchecked`; the max and epi32
    wrappers are not tracked. Arm P is secondary and cannot change the verdict. A's own line (from the census
    build's MSBuild log) was not used. Whether this disclosure suffices or arm P needs re-scoping is the lead
    engineer's and the Owner's call. The x0final revision's re-run (§7) compiled the probe again with the same
    lines; nothing about Hearth's own code follows from it.
  - **Disclosure: Hearth helper code was compiled and analysed before freeze, inside the first census mock**
    (found by the independent review of 2026-10-16/17, §12; reviewer 2's blocker). The first mock (SHA-256 of its
    files `quant.c` `9721e8eb…`, `quant_avx2.c` `cb638987…`, `quant_avx512.c` `851e2c31…`, `hx_quant.h` `c0958d00…`,
    as pinned in `FREEZE.md` until this revision) was described as stand-in kernels written for the test, but it
    contained verbatim copies of Hearth b5d3f14 code [M, x0final revision, line comparison of that mock with
    `git show b5d3f14:` in the read-only clone, 2026-10-17]: the body of `tree16` in both SIMD files (Hearth
    quant_avx2.c:35-41 and quant_avx512.c:35-43), `canon4` in both (the NaN constant written as a literal), `red8`
    (quant_avx2.c:71-76), `hsum_i32` (quant_avx512.c:54-60), `q_rint`'s body (quant.c:46-49), the `s` loop header
    of `dot16_conv`'s tree (quant.c:362) and the BF16 widening load (quant_avx512.c:113-115). 13, 22 and 26
    distinct normalised lines longer than 25 characters of the mock's `quant.c`, `quant_avx2.c` and `quant_avx512.c`
    occur in the Hearth file of the same name [M, same comparison; equal to the reviewer's counts]. Compiled with the
    frozen flag logic under A, A-ninja, B-cmake, C and D in step 88 (run `smoke-20261017T042641Z`), this code gave
    d1 `pass` in every configuration, all 66 `tree16` sites `match` (A, A-ninja, C, D; B-cmake: `quant_avx2.c`
    only) and no P3(c) flag, and those outcomes were read before freeze. So the D12 statement ("no Hearth source
    compiled") holds for Hearth's files but not for this code, and the outcome of P3(d1) and P3(d2) for Hearth's own
    helpers was indicated before freeze (§8, E6). The canary shape (v + M) − M and the s = 8, 4, 2, 1 pairing are
    defined by this record, so any test of the d1 and d2 detectors exercises them; what was disclosed here is the
    compilation of Hearth's own text of those helpers inside Hearth's surrounding code shape.
    - Remedy (x0final revision): every helper and kernel of the mock was rewritten with other intrinsics and other
      text (the AVX-512 `tree16` computes the record's pairing through `vshuff32x4`/`vpermilps` on whole registers;
      the AVX2 `tree16` deliberately pairs adjacent lanes first, so d2 must report `mismatch` on real compiler output);
      the mock's header comment and `X0_NOT_HEARTH` were corrected; and `x0_driver.py` now refuses any smoke source
      (and the headers next to it) that shares three consecutive normalised non-trivial lines with a pinned Hearth
      file, using `class/hearth_shingles.json` (SHA-256 of every such run of the seven pinned files, hashes only;
      redefined by the pre-freeze review revision, below: pairs, comments stripped).
      The guard refuses every file of the first mock (1, 2, 8 and 11 shared runs in `hx_quant.h`, `quant.c`,
      `quant_avx2.c`, `quant_avx512.c`) and passes the new mock, the regression files and the probes [M, x0final
      revision, laptop, 2026-10-17; `tests/test_driver_guard.py`]. The mock's `CMakeLists.txt` still mirrors
      Hearth's flag logic, by design (it must produce the same kind of command lines).
    - *Guard redefined by the pre-freeze review revision (2026-10-17; stricter).* The review showed that the guard let
      through two-line Hearth runs and lines that differed only by a trailing comment, skipped lines starting with `*`
      (dereferences) as comments, scanned only the census files and the headers next to them, and read non-UTF-8 files
      with replacement characters. Now comments, including trailing ones, are stripped before normalising; the unit is
      a **pair** of consecutive normalised non-trivial lines (k = 2; `class/hearth_shingles.json` holds the 1,071 pair
      hashes of the seven pinned files, made from the read-only clone's files after checking their blob hashes, no git
      command); every `.c` and `.h` file of the source and include directories is scanned (the mock's `other.c`
      included); a file that is not UTF-8 is refused; and a pair is admitted only when both of its lines are on the
      allow-list of **13 structural lines**, the dispatch-table shape that record §4.1 requires a mock to share:
      `typedef struct hx_kernels {`, `hx_matmul_fn matmul[7];`, `void (*act_quantize_q8)(const float *x, hx_act_q8
      *out, int64_t n);`, `} hx_kernels;`, `extern const hx_kernels hx_kernels_scalar;`, `const hx_kernels
      *hx_kernels_avx2_table(void);`, `const hx_kernels *hx_kernels_avx512_table(void);`, `const hx_kernels
      hx_kernels_scalar = {`, `static const hx_kernels k_avx2 = {`, `static const hx_kernels k_avx512 = {` and the
      three ISA initialisers `HEARTH_ISA_SCALAR,`, `HEARTH_ISA_AVX2,`, `HEARTH_ISA_AVX512,`. Single shared lines are not
      refused: generic loop headers and declarations recur in any C code (`for (int64_t r = r0; r < r1; r++) {` and the
      like; 1 to 11 per regression file after the rewrite below). Measured [M, reviser, laptop, 2026-10-17;
      `tests/test_driver_guard.py`]: the new guard refuses every file of the first mock (2, 4, 11 and 14 pairs in
      `hx_quant.h`, `quant.c`, `quant_avx2.c`, `quant_avx512.c`) and the earlier `smoke_dispatch.c` (3 pairs), and passes
      the rewritten `smoke_dispatch.c`, the current mock, `rv_tricky.c`, `rv_tricky2.c`, `smoke.c` and every probe.
    - **Lead engineer's ruling (2026-10-17, before freeze): P3(d1) and P3(d2) stay confirmatory.** These canaries
      can only flag a defect (Amber (b)). They can never produce a pass. Demoting them to descriptive after their
      outcome was indicated would move a gate criterion after data has been seen, which ROADMAP §1 rule 1 forbids
      ("Thresholds never move once data has been seen"); the verbatim-copy indication counts as data seen. The
      disclosure stands: every report of d1 or d2 carries the label "outcome indicated before freeze by a verbatim copy
      (E6)". The Owner may tighten this at signing. Loosening it after the census has run is possible only as a
      post-data amendment, with the verdict reported both ways (§10, Appendix A, docs/m0/README). *Wording of the third
      and last sentences corrected by the reviser after the pre-freeze review of 2026-10-17; the ruling is unchanged.*
      *Extended by the reviser (pre-freeze review, reporting only):* the same label is carried by the P3(c) results of
      the scalar F32, F16, BF16 and act variants (disclosure below); `judge.py` writes it into `verdict.json`
      ("canaries", and every Amber (b) entry with a d1 or d2 flag). Whether those P3(c) results need more than the
      label is the lead engineer's call before freeze.
  - **Disclosure: the regression file `smoke_dispatch.c` carried Hearth's own lines** (found by the pre-freeze review
    of 2026-10-17, §12; correcting "NON-Hearth" in this section and in D3 for these lines). The file, written by x0prep as a
    stand-in with Hearth's table shape, contained, after comment stripping, three verbatim two-line runs of Hearth
    b5d3f14 [M, reviser, overlap scan of the file against the read-only clone's files, blob hashes verified, laptop,
    2026-10-17]: the s = 8, 4, 2, 1 tree of `dot16_conv` (its lines 75-76 = quant.c:362-363), the body of `q_rint`
    (82-83 = quant.c:47-48, which differ only by Hearth's trailing comment) and the `act_q8_scalar` amax loop body
    (169-170 = quant.c:330-331); its lines 102 and 104 are near copies of `dot16_conv`'s accumulation (quant.c:360,
    `w[i]` for `wi`), and 14 single lines longer than 25 characters are shared, mostly loop headers. It was compiled
    under the frozen `quant_avx512.c` and `quant.c` lines of every configuration and analysed since x0prep (runbook
    steps 70-72 and 71b; step 88 of x0final and of the x0final revision). Two §4.7 rules were tuned on the P3(c) flags
    this text produced: the back-edge rule (x0final, a false flag on the vectorised tree) and the enclosing-loop rule
    (x0final revision, a false flag in 12 variants under C). So, besides d1 and d2 (E6), the P3(c) outcomes of the
    scalar F32, F16 and BF16 variants (`dot16_conv`'s loops quant.c:355, :362, :363) and of the scalar act variant
    (the amax loop quant.c:329) were indicated before freeze by a verbatim copy. The record's canary shapes (v + M) − M
    and the s = 8, 4, 2, 1 pairing remain defined by this record; what is disclosed is Hearth's own text of them and of
    the amax loop.
    - Remedy (pre-freeze review revision): the three runs were rewritten with the same semantics and the same line
      numbers (`for (int j = 0; j < s; ++j) L[j] += L[j + s];`, the constant renamed, `amax = m > amax ? m : amax;`), so
      `smoke_loop_table.csv` and `tricky_expect.json` stay valid; whether the compiled objects are unchanged is checked
      by the desktop re-run (§7, pending). The E6 label now also covers those P3(c) results (the ruling above; `judge.py` writes it).
      *Checked by the desktop re-run of 2026-10-17 (§7):* the decoded code of the rewritten file equals the x0final
      revision's under A, A-ninja and C, in both builds and both objects (`smoke_dispatch.c` and its scalar build);
      under B-cmake and D (Clang) one function differs, `sd_float_common`, whose flattened s = 8, 4, 2, 1 tree has the
      same instruction count and iclass multiset but FP additions with commuted operands and another schedule; the
      `rv_tricky*.c` objects and every arm-P object are unchanged [M, desktop, decode comparison,
      `runbook/logs/prefreeze_rerun_checks.log` §3].
- **No Hearth source is compiled before freeze, not even as an unread smoke test.** (The previous draft
  allowed a compile smoke test of the three files; x0prep removed it, Appendix E.) Whether each census file
  compiles under each configuration is therefore census data, classified by the compile rule of §5 P1. The
  pre-freeze smoke tests (D3) use only NON-Hearth files: `scripts/smoke/smoke.c`,
  `scripts/smoke/smoke_dispatch.c` (except the Hearth lines it carried until 2026-10-17, disclosed above), the
  adversarial regression files `scripts/smoke/rv_tricky.c` and
  `scripts/smoke/rv_tricky2.c` (added after the §12 review), the probes in `scripts/runbook/probes/`,
  `scripts/probes/reduce_probe.c` (syntax check only) and the generated instruction zoo of
  `scripts/smoke/gen_zoo.py`.
- **Known before freeze from flags alone** [M, x0prep, `flags/prefreeze/`]: B-cmake's expanded cc1 lines carry
  `-ffp-contract=on` for all three files, so P3(a1) flags B-cmake (E1) whatever the objects contain; A-ninja,
  B-proxy, C (GCC effective values) and D match no pattern of `fp_flag_patterns.txt`. A probe calling
  `_mm512_dpbusd_epi32`, compiled with B-cmake's exact `quant_avx512.c` command, fails with "always_inline
  function '_mm512_dpbusd_epi32' requires target feature 'avx512vnni'" [M, tooling track, `TOOLCHAINS.md` §6];
  Hearth's file itself was not compiled (E2).

**Machine.** The desktop (Ryzen 9 9950X, Windows 11) and WSL2 on it [M, sprint brief, per PLAN.md
§2]. Once everything in Table 2.1 is pinned, the host is assumed not to affect emitted code [G]. §6
tests repeatability on this one host only.

**Decoder.** Intel XED, built from github.com/intelxed/xed at the tag and commit in Table 2.1. It
runs in 64-bit long mode (`xed -64`, i.e. `XED_MACHINE_MODE_LONG_64`) with chip `XED_CHIP_ALL`. The
cross-decoder is `llvm-objdump` from the LLVM of configuration D.

**Table 2.1, pinned toolchain.** This record cannot be FROZEN while a cell in the right-hand column
is empty. Each value written there carries [M] with the command, machine and date.
`experiments/x0-census/TOOLCHAINS.md` mirrors this table and adds the raw outputs.

| Item | Candidate now, with provenance | Recorded before freeze |
|---|---|---|
| MSVC (A, A-ninja, H-A) | Toolset directory `14.44.35207`, VS 2022 Community: the compiler path in `flags/A-msvc.compile_commands.json` [M, X0 tooling track, 2026-10-16]. `cl` reports its own version, expected 19.44.x [inference]. "14.44.35207" is not the `cl` banner | Banner "Microsoft (R) C/C++ Optimizing Compiler Version 19.44.35229 for x64"; SHA-256 `cl.exe` `fe251ef5…a36619`, `c1.dll` `6176d88c…a6604b`, `c2.dll` `b057a185…b3cec`; Windows SDK 10.0.26100.0; UCRT 10.0.26100.0; MSBuild 17.14.60.43110 [M, x0prep, step 70 on the desktop, 2026-10-16; full hashes in `TOOLCHAINS.md` §11] |
| LLVM (B-cmake, B-proxy, D, H-D) | 23.1.3, from the install directory names `llvm-win-23.1.3` and `llvm-linux-23.1.3` in `flags/*.json` [M, X0 tooling track, 2026-10-16]; the banner is not yet recorded | `clang --version` / `clang-cl --version`: "clang version 23.1.3 (https://github.com/llvm/llvm-project 0d261d1ca552c95a8f007e061c787ac7132fbcbc)"; Windows `clang-cl.exe` = `clang.exe` SHA-256 `9584244d…8d8261`; Linux `clang-23` `913453af…0d9a0e`; resource-dir include trees: Windows 322 files `5587c91b…a61a12`, Linux 327 files `18b182d3…2f31c` [M, x0prep, steps 70 and 71, 2026-10-16] |
| GCC (C) | `/usr/bin/gcc` in WSL2. The previous draft's "13.3.0 (Ubuntu 24.04)" is unverified | "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"; configured `--enable-default-pie --enable-cet`; `-dumpspecs` SHA-256 `3a269a0e…70e0dc`; `cc1` SHA-256 `5d167913…8e2f4`; `libc6-dev` 2.39-0ubuntu8.9; Ubuntu 24.04.3 LTS [M, x0prep, step 71, 2026-10-16] |
| CMake; Ninja | not recorded | CMake 4.4.3 (Windows and Linux); Ninja 1.12.1 bundled with VS 2022, SHA-256 `5020138b…1b89123` [M, x0prep, step 70] |
| XED | tag `v2026.08.23`, which PLAN.md §2 takes from the X0 track's scratch scripts [not verified by the reviser] | Tag v2026.08.23, commit `0bcb6237345c5066726dcc08b3d87928df3b5b26`; builds and `mfile.py` options in `TOOLCHAINS.md` §3; `xed -version` "[v2026.08.23]"; Windows `xed.exe` SHA-256 `f10d2680…846368`; decode mode `-64 -cet` [M, tooling track and x0prep] |
| stdarch XML (§4.5) | not chosen | rust-lang/stdarch `main` at `eb9b3025937c85bd271a3ca46a681cd52739db12` (2026-10-16); `intrinsics_data/x86-intel.xml` SHA-256 `6762a50652a35ef663fd532ed83b789d19bbc2ac7e94b1771f19d666d96c2c30`, version 3.6.9 dated 07/12/2024 [M, x0prep, `git ls-remote` and download on the laptop, 2026-10-16] |
| Effective flags | `flags/quant_flags.json` (explicit lines only) | `experiments/x0-census/flags/prefreeze/`: exact argv (A-ninja, B-cmake, C, D `compile_commands.json`; A: vcxproj and design-time lines, the build lines come from the census binlog); cc1 lines from `-###` for B-cmake, B-proxy and D; `gcc -Q --help=common,optimizers` and `gcc -###` for C [M, x0prep, steps 70, 70b, 71] |

## 3. Configurations

**Main union.** These builds use Hearth's own CMake command lines, and they feed P1 to P5 and the
verdict.

| Config | Compiler | Host, ABI | Role |
|---|---|---|---|
| A | MSVC `cl` (Table 2.1), Visual Studio generator | Windows, Win64 | **release** (win-x64) |
| A-ninja | the same `cl`, Ninja generator | Windows, Win64 | cross-check of A. It joins the union only for variants whose code differs from A (§2) |
| B-cmake | `clang-cl` (Table 2.1) | Windows, Win64 | not a release compiler. Hearth's CMake lines for clang-cl |
| C | GCC (Table 2.1) | WSL2, SysV | not a release compiler. One of Hearth's Linux CI compilers |
| D | `clang`, the same LLVM as B-cmake | WSL2, SysV | **release** (Linux) |

Configurations A and D are the release compilers of DR-008 and of ROADMAP §3.1's amber clause.
There are 18 variants per configuration [M, reviser, read of `hx_kernels_scalar` (quant.c:429-433),
`k_avx2` (quant_avx2.c:341-345) and `k_avx512` (quant_avx512.c:365-369) at b5d3f14, 2026-10-16].
That gives 72 variants in the main union, not counting A-ninja [D: 18 × 4].

**What B-cmake receives.** Hearth's `if(MSVC)` branches (`CMakeLists.txt:39-41, 52-54`) also apply to
clang-cl. B-cmake therefore gets `/fp:precise`, `/arch:AVX2`, `/arch:AVX512` and
`/experimental:c11atomics`, and no `-ffp-contract=off` [M, reviser, read of the CMakeLists and of
`flags/quant_flags.json`, 2026-10-16]. Expectations, written now so that they cannot be explained
away later [inference, not verified]:
- The expanded cc1 line will carry `-ffp-contract=on`, because clang's C default is `on`
  ([04 §6.2](../../architecture/04-toolchain.md#62-strict-fp-flags-per-compiler-v0)). P3(a1) would
  then flag B-cmake (§8, E1). *Now measured on flags* [M, x0prep, `flags/prefreeze/B-cmake.*.cc1.txt`]:
  all three files carry `-ffp-contract=on`; on smoke code the B-cmake objects contain FMA-class
  instructions (P2 = 6 in one smoke closure) [M, `scripts/smoke/results_dispatch.json`].
- `/arch:AVX512` in clang-cl may not enable AVX512-VNNI. If so, `quant_avx512.c` fails at
  `_mm512_dpbusd_epi32` (quant_avx512.c:237). `/experimental:c11atomics` may also be ignored or
  rejected. *Now measured on a probe, not on Hearth* [M, tooling track, `TOOLCHAINS.md` §4 and §6;
  x0prep cc1 lines]: `/arch:AVX512` expands to `-target-cpu skylake-avx512`, which lacks AVX512-VNNI, and a
  probe calling `_mm512_dpbusd_epi32` with B-cmake's exact `quant_avx512.c` command fails;
  `/experimental:c11atomics` is ignored with a warning and C11 atomics still compile.
- **A compile failure of a census file under B-cmake (or C) is a recorded finding of that configuration, not
  a tooling failure** (§5 P1 compile rule): the file's variants get the genuine gap `compile_failed`, rows N1
  and N2 of §8 apply (the union is a lower bound; a build-defect draft is written), and the configuration's
  effective flags are still screened by P3(a), so Amber (b) can hold for B-cmake even when
  `quant_avx512.c` does not compile. The census does not add `-mavx512vnni` or any other flag to B-cmake;
  the B-proxy arm (secondary) carries D's `-m` flags and is expected to compile.
- **Config C (Ubuntu GCC) carries hidden hardening defaults** [M, `flags/prefreeze/C-gcc.*.cc1.txt`]:
  `-D_FORTIFY_SOURCE=3 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
  -fcf-protection` (configured `--enable-cet --enable-default-pie`). They are part of C's effective flags and
  are neither added nor neutralised. Their code (ENDBR64 at function entries, stack-protector canaries,
  `__stack_chk_fail`, `__*_chk` calls) is expected and is listed under lift blockers (§4.2); it is not a P1 gap
  (`__stack_chk_fail`, `__memcpy_chk` and the other allow-listed externals are not FP trust dependencies). XED
  must run with `-cet`, or ENDBR64 decodes as a reserved NOP (`NOP_GPRv_GPRv_0F1E`) [M, `TOOLCHAINS.md` §3];
  every decode in this record uses `xed -64 -cet`.
- The Win64 ABI (xmm6 to xmm15 callee-saved) changes spills relative to D. That is why B-proxy, not
  B-cmake, is the proxy arm.

**Secondary arms.** These are reported and cannot change the verdict. A flag defect found in one of
them still produces the mandatory report (§10).

| Arm | What | Why |
|---|---|---|
| B-proxy | clang-cl with D's codegen flags for each file passed through `/clang:`, i.e. `-O3 -std=gnu11 -ffp-contract=off` plus D's `-m` flags, with `/fp:precise` and `/arch:*` removed. Target triple and ABI stay Win64. Written out in `flags/prefreeze/B-proxy.argv.json` by `x0_flags.py proxy` (the added flags precede the per-file plumbing); its cc1 lines carry `-ffp-contract=off` and D's target features [M, x0prep, D4] | The "clang-cl build with the release flags, labelled as a proxy for the SysV build" of ROADMAP §3.4. It feeds the proxy-fidelity metric (§5) |
| H-A, H-D | `scripts/hxcc.py` builds of the three files, with MSVC and with D's clang, non-debug, non-ASan, with `--shared` (so `HEARTH_BUILD_DLL` is defined as in `hearth_core`; for H-D this adds `-fPIC -fvisibility=hidden`). Argv written out in `flags/prefreeze/README.md` from `hxcc.py` lines 75-81, 118-134 and 153-164 [M, x0prep, read; `--shared` is a record choice] | Hearth's second build path (`-O2`) |
| P (reduce probe) | `scripts/probes/reduce_probe.c`. It is not Hearth code. Its noinline wrappers call `_mm512_reduce_add_ps`, `_mm512_reduce_max_ps` and `_mm512_reduce_add_epi32` (by value and through a load), and each main-union configuration compiles it with its own `quant_avx512.c` flags. Intel defines these `_reduce_` intrinsics only for 512-bit vectors, so there is one translation unit. Pre-freeze it was only syntax-checked (`/Zs`, `-fsyntax-only`) with the A, B-cmake, C and D `quant_avx512.c` commands, rc 0 for all four [M, x0prep, steps 70 and 71]; its emitted sequences are census data | ROADMAP §3.1 and [04 §7.1](../../architecture/04-toolchain.md#71-x0-the-instruction-census-dr-008-v0-m0-before-the-lifter-exists)(c) ask how `_mm512_reduce_add_ps` is lowered, and Hearth at b5d3f14 never calls it (§4.5) |
| S-helpers | Every external-linkage function in `quant.c` that fills no table slot: `hx_sum16`, `hx_dot16`, `hx_rmsnorm`, `hx_softmax`, `hx_swiglu`, `hx_sigmoid`, `hx_rope`, `hx_axpy`, `hx_quantize_row`, `hx_dequantize_row` and the rest, under every main-union configuration | The canonical exact helpers and the authoritative quantisers ([07 §2.6](../../architecture/07-hearth-port.md#26-what-evidence-each-gate-produces-dr-021); ROADMAP M2) |
| S-object | Every executable section of the three objects | \|U_object\| |

## 4. Units and counting rules

1. **Dispatched variant.** One non-NULL function pointer in a per-ISA `hx_kernels` table
   (`hx_quant.h:59-63`). It is either a non-NULL entry of `matmul[]` (dtype indices F32, F16, BF16,
   Q8 and Q4) or `act_quantize_q8`, in `hx_kernels_scalar`, `k_avx2` or `k_avx512`.
   - The script lists the tables from the source and fails if it finds anything other than 18
     variants per configuration.
   - In each object, a slot is mapped to its function through the relocation on that slot's field
     in the table's data (COFF `ADDR64`; ELF `R_X86_64_64` or its PIC equivalent), never by name.
     This handles clones, identical-code-folding aliases and renamed static functions.
2. **A variant's code** (the *counted set*).
   - **Entry.** The target of the slot's relocation.
   - **Recursive descent.** From the entry, follow fall-through, direct conditional and
     unconditional jumps, and direct calls. Branch targets resolve through relocations (COFF
     `REL32`/`ADDR32NB`; ELF `PC32`/`PLT32`) or through in-section displacements with no
     relocation. A target in another executable section, such as GCC `.text.unlikely`/`.cold` parts
     or MSVC COMDATs, is followed.
   - **Call kinds.**
     - *Internal*: a callee defined in the same object with internal or hidden linkage, or any
       defined callee in COFF. Its reachable code joins the closure.
     - *Interposable* (ELF only): a callee that is a default-visibility global definition in the
       object, called directly or through `PLT32`. `hearth_core` is built with
       `POSITION_INDEPENDENT_CODE ON` (`CMakeLists.txt:50`), and hidden visibility is set only on the
       `hearth` target (`:75`). The call is listed as interposable and the body joins the closure.
     - *External*: a call to an undefined symbol. It is listed and stays out of the closure. Calls
       to libm or CRT floating-point functions are also listed as FP trust dependencies (P1).
   - **Indirect branches.** Jump tables are resolved through their relocations. MSVC places them in
     `.text` after the function; GCC and Clang place them in `.rodata` [inference, both]. Their targets
     join the counted set. An indirect branch that cannot be resolved is a P1 gap.
   - **Function bytes.** ELF: `[st_value, st_value + st_size)`. COFF has no symbol size, so ranges
     come from COMDAT section bounds (`/Gy`, implied by `/O2` [inference]) and are cross-checked
     against `.pdata` BeginAddress/EndAddress. A mismatch is a P1 gap of class tooling.
   - **Data in code.** Bytes covered by a relocation that is not an instruction's displacement or
     immediate, and jump-table regions, are data and are never decoded.
   - **Unreachable bytes** inside a closure function's range are either *padding* (all 0xCC,
     NOP-class or zero) or *orphan*. Orphan bytes are reported with their offsets and decoded only
     as a secondary output. They never enter U.
   - **Cross-check.** A linear sweep over the same ranges is a cross-check. Any linear-sweep
     instruction that is neither reachable nor padding is reported.
   - **Lift blockers.** [04 §7.2](../../architecture/04-toolchain.md#72-the-lifter-v0-m2) step 3 makes
     any call or indirect branch a lift failure, so each variant gets counts and lists of: internal
     calls, external calls, interposable calls, indirect branches, jump tables, and hardening code.
     Hardening code means ENDBR64, stack-protector canary loads and `__stack_chk_fail` calls, and
     `/GS` cookie checks.
   - **Precisions fixed before freeze** (x0prep; implemented in `x0_extract.py` / `x0_decode.py`, revised after
     the review of §12, and validated on NON-Hearth smoke objects of all four configurations, including the
     adversarial regression inputs of runbook step 72; `scripts/README.md`):
     - *Relocation arithmetic.* ELF RELA addends are explicit; COFF addends are the in-place field. Branch and
       RIP-relative targets: ELF `PC32`/`PLT32`/`GOTPCREL*` give S + A + (end − P); COFF `REL32_k` gives
       S + addend + (end − P − 4 − k). Jump-table entries at P in a table based at B: ELF `PC32` gives
       S + A − (P − B); COFF `REL32` gives S + addend − (P + 4 − B); ELF `64`/`32`/`32S` and COFF
       `ADDR32NB`/`ADDR64` give S + addend.
     - *Jump tables.* A table is the one loaded by the indirect jump's own address computation, recognised in
       the jump's basic block: `movsxd rX,[rB+rI*4]`, or `mov eX,[rB+rI*4+T]` with T through an `ADDR32NB`
       relocation; then `add rX,rB`; then `jmp rX`. Every reaching definition of rB must be `lea rB,[rip+T]`,
       or `lea rB,[__ImageBase]` in the `ADDR32NB` form; definitions are followed through whole-register copies,
       including a spill to an XMM register and back. The other accepted form is `jmp [T+rI*8]` with a relocated
       displacement.
       - The entry count n comes from the bound on rI that guards the jump. Either the jump's block has a single
         predecessor, a conditional branch on `cmp rI,imm`: `ja` falling through to the jump gives n = imm+1,
         `jae` gives n = imm, and the taken `jbe`/`jb` forms are also accepted. Or the jump's own block masks
         rI with `and rI,2^k−1`, which gives n = 2^k. Between the bound and the table load, the only writes to
         rI allowed are zero- or sign-extending moves and whole-register copies. *x0final revision (review of
         2026-10-16/17):* the compare may also be on rI's 8- or 16-bit register (`cmp dl,imm`) when the nearest
         definition of rI's family in the compare's block is a MOVZX from an operand of that same width (GCC:
         `movzbl (mem),%edx; cmpb $9,%dl; ja`), which leaves every upper bit zero; any other narrow compare stays
         `unresolved_indirect`. Measured on the reviewer's NON-Hearth `rvx.c` under C: `rvx_vrp`'s table, unresolved
         before (117 orphan bytes), resolves to 10 entries with 0 orphan bytes, as under A, B-cmake and D; the other
         seven variants of the object decode as before [M, x0final revision, desktop, 2026-10-17;
         `runbook/logs/x0final_rev_probes.log`]. For an MSVC byte index table `movzx eI,byte [rB+rJ+T2]`,
         T2 is bounded the same way on rJ, n = largest byte + 1, and T2's bytes are data.
       - Exactly n entries of the expected relocation type must exist at the table's stride. Each must land on
         an instruction start inside the jump's function or its GCC cold parts. An entry range that overlaps
         another address referenced by the counted set is rejected.
       - Anything else makes the jump `unresolved_indirect`: no recognised shape, no bound, or a missing or
         misplaced entry ("jump table truncated at entry k of n"). A partial table is never accepted. Table
         bytes in a code section are data.
     - *Function families.* A GCC cold part is a function symbol named exactly `<parent>.cold` or
       `<parent>.cold.N` in the same object. Jumps between a function and its cold parts are intra-procedural:
       the cold part joins the closure with kind `cold_part_of:<parent>`, and no call or tail call is recorded.
       A jump (`jmp` or `jcc`) to another function's start is a tail call. A jump into the middle of another
       function is a gap `other`.
     - *Calls through memory or registers.*
       - `call/jmp [rip+X]` is a call (tail call) to X only when the operand holds X's address. On COFF, X is
         `__imp_<name>`. On ELF, the relocation is `GOTPCREL`, `GOTPCRELX` or `REX_GOTPCRELX` to an undefined X.
       - Everything else is `unresolved_indirect` ("indirect call through variable X"). This includes a
         `PC32`/`REL32` relocation to a variable, such as an extern function pointer.
       - `call/jmp reg` is a call to an imported X only if every reaching definition of reg's 64-bit register
         family is a MOV loading the same import or GOT slot. A call on the path clobbers the caller-saved
         registers of the object's ABI. Otherwise the branch is `unresolved_indirect`.
       - Under `/guard:cf`, `call [__guard_dispatch_icall_fptr]` is `unresolved_indirect` ("CFG dispatch").
         `call [__guard_check_icall_fptr]` is an allow-listed check call.
     - *Order independence.* The descent runs in rounds. Each round computes the closure over direct edges, then
       resolves every pending indirect branch against the complete reach set of the round. Rounds repeat until no
       instruction is added. A branch whose resolution changes between rounds is a gap `other`. Runbook step 72
       decodes every regression object twice, with opposite work-list orders, and requires byte-identical
       outputs.
     - *No return.* A call does not fall through in three cases. Execution falling off the end of a function
       range after any other instruction is a gap `other`.
       - The callee is on the frozen list (`__stack_chk_fail`, `__stack_chk_fail_local`, `abort`, `exit`,
         `_exit`, `__assert_fail`, `__chk_fail`, `__fortify_fail`, `longjmp`, `__longjmp_chk`,
         `_invalid_parameter_noinfo_noreturn`, `__report_gsfailure`, `__report_rangecheckfailure`, `__fastfail`,
         `ExitProcess`). The list applies to direct, memory-operand and import-register calls alike.
       - The call's next byte is the end of its function, or padding up to the end. This is the compiler's own
         no-return knowledge. It is recorded in `lift_blockers.noreturn_inferred` and is not a gap.
       - The callee is an internal function whose family has no reachable return and no tail call to a function
         that can return. The descent is repeated until this set is stable.
       - A mid-function call to an external no-return function that is on no list is assumed to return. The
         bytes after it then join the counted set, which over-counts.
     - *Overlapping decodes.* Two reachable instructions whose bytes overlap are a gap `other`.
     - *FP trust dependencies (P1).* "Calls to libm or CRT floating-point functions" is made strict: **every
       external callee is an FP trust dependency unless it is on the frozen allow-list** of `x0_decode.py`
       (`memcpy`, `memmove`, `memset`, `memcmp`, `__memcpy_chk`, `__memset_chk`, `__memmove_chk`,
       `__stack_chk_fail`, `__stack_chk_fail_local`, `__security_check_cookie`, `__GSHandlerCheck`, `__chkstk`,
       `___chkstk_ms`, `__report_rangecheckfailure` and `__guard_check_icall_fptr`). An unknown callee is
       presumed FP-relevant.
     - *COFF function ranges.* A function alone in its COMDAT section spans the section. Otherwise its range is
       the union of its `.pdata` ranges. Otherwise it runs up to the next function symbol, which for a closure
       function is a gap `range_mismatch`.
       - The first `.pdata` entry of each function begins at its symbol. Further entries (MSVC chained-unwind
         fragments) begin inside the function's range.
       - The entries are sorted, non-overlapping and contiguous, and the last ends at or before the range end.
         Otherwise the function gets `range_mismatch`.
       - Leaf functions without `.pdata` are allowed.
     - *Slot names.* After the relocation mapping, the initialiser's function name is compared with the resolved
       function's names, with GCC `.constprop`/`.isra`/`.part`/`.cold` suffixes stripped. A mismatch is
       reported (`slot_name_check`) and is not a gap, so that identical-code folding and clones stay visible.
     - *Code addresses referenced as data.* A code address referenced by a reachable instruction that is neither
       an instruction start nor data is listed per variant (`referenced_non_instruction`). It is not
       reclassified.
     - *Hardening detected:* ENDBR64/ENDBR32; `fs:[0x28]` loads and references to `__stack_chk_guard`; calls to
       `__stack_chk_fail`; references to `__security_cookie` and calls to `__security_check_cookie`;
       `or qword ptr [rsp], 0` stack-clash probes (descriptive).
3. **Form** = XED `iform`. **Mnemonic** = XED `iclass`. ROADMAP §3.1's "mnemonics" is read as XED
   iclass, the stricter of the readings on offer (OQ-1).
   - A secondary partition by XED extension separates category **S** (SIMD and mask: SSE, SSE2,
     SSE3, SSSE3, SSE4, AVX, AVX2, AVX2GATHER, FMA, F16C, AVX512EVEX, AVX512VEX) from category **G**
     (every other reachable instruction: GPR, control flow, NOP-class inside reachable code).
   - The extension names are XED's. `classify.py` checks them against the pinned release before
     freeze. All twelve exist in XED v2026.08.23 [M, x0prep, `class/fp_class_summary.json`].
4. **FP sensitivity** (the unit of P5). The classification is fixed before any Hearth object exists.
   - Before freeze, `scripts/classify.py` enumerates every XED iclass in these extensions or ISA
     sets: X87; SSE to SSE4.2; AVX; AVX2 and AVX2GATHER; FMA; F16C; AVX-512 F, CD, BW, DQ, VL, VNNI,
     BF16 and FP16 (EVEX and the VEX k-mask forms); BMI1; BMI2.
     - **Widened by x0prep to every iclass XED defines** (1,995 iclasses, from XED's own tables dumped
       into `class/xed_tables.tsv` by `scripts/xed_tables.c`) [M]. Reason: under the rule below, a census
       iclass missing from the CSV counts as FP-sensitive, so MOV, ADD, JNZ and every other GPR or control
       iclass would have counted towards P5. Every row gets the same verdict rule; no threshold changes.
     - Result [M, x0prep, `classify.py`, laptop, 2026-10-16]: 624 of 1,995 iclasses are FP-sensitive; every
       "FP-sensitive by name" and "not FP-sensitive by name" item below is checked by the script and holds;
       0 iclasses fall back to the FP-typed-operand default. Four iclasses are "no" by the SDM reading and
       "yes" by the XED cross-check, so they are FP-sensitive: LDMXCSR and VLDMXCSR (attribute MXCSR),
       STMXCSR and VSTMXCSR (MXCSR_RD).
     - The `reason` column names the source document and instruction page (SDM Vol. 2, or for ISA sets newer
       than the SDM text the Intel ISA-extension specification that XED's ISA set names), followed by the
       description template of the classification rule that fired and any XED cross-check hits. **It is not a
       per-instruction SDM citation** (corrected after the §12 review). For some rows the template overstates
       the mechanism. Examples are VCVTPH2PS and VCVTNEEBF162PS, exact widening conversions that carry the
       conversion template ("rounding per MXCSR.RC, ..."). Such rows are FP-sensitive by the record's by-name
       conversion rule whatever the template says, so no `fp_sensitive` value depends on the template text.
       The templates were written without re-reading the SDM in this session [inference].
   - It writes `experiments/x0-census/class/fp_class.csv` with the columns `iclass`, `extension`,
     `fp_sensitive` (yes|no), `reason` (source page plus rule template, above) and `op_class`. The CSV's
     SHA-256 goes into Appendix D, and an independent reviewer checks it before freeze (§12; done
     2026-10-16 on a sample, Appendix D item D5).
   - **Definition.** An iclass is FP-sensitive if the architectural result it writes to any
     destination can depend on MXCSR.RC, MXCSR.DAZ, MXCSR.FTZ, on embedded rounding or SAE, or on
     IEEE special-value handling.
     - Destinations include GPRs, XMM/YMM/ZMM registers, opmask k-registers, EFLAGS and memory.
     - IEEE special-value handling covers NaN propagation, selection or quieting; signed-zero
       handling; denormal inputs or outputs; rounding on inexact or overflowing results; and the
       integer-indefinite results of conversions.
     - The only effects excluded are those on MXCSR's status (exception) flags.
   - **FP-sensitive by name** (`classify.py` must agree):
     - (V)ADD/SUB/MUL/DIV/SQRT/MIN/MAX in PS, SS, PD and SD forms;
     - (V)UCOMISS and (V)COMISS (and the SD forms), whose EFLAGS result depends on NaN and DAZ;
     - (V)CMPPS/SS, writing to an xmm register or to k;
     - VFPCLASSPS/SS, VGETEXP\*, VGETMANT\*, VRNDSCALE\*, (V)ROUND\*, VREDUCE\*, VRANGE\*,
       VFIXUPIMM\* and VSCALEF\*;
     - every FMA-class iclass;
     - RCP\*, RSQRT\*, VRCP14\* and VRSQRT14\*;
     - every FP-to-integer, integer-to-FP and FP-to-FP conversion, including CVTSI2SS,
       CVT(T)SS2SI, (V)CVTDQ2PS, (V)CVT(T)PS2DQ, VCVTPH2PS, VCVTPS2PH, VCVTNEPS2BF16 and VDPBF16PS;
     - x87 arithmetic.
   - **Not FP-sensitive by name:**
     - bitwise FP logic ((V)AND/ANDN/OR/XOR in PS and PD forms; VPTERNLOG\*);
     - moves, loads and stores;
     - blends, including (V)BLENDVPS, which selects by a sign bit;
     - shuffles, permutes, broadcasts, inserts and extracts;
     - operations that read and write only k-registers (KMOV\*, KAND\*, KOR\*, KORTEST\* and so on);
     - integer arithmetic, including saturating forms (VPMADDUBSW, VPMADDWD, VPDPBUSD, VPACKSS\*,
       VPMOVS\*).
   - **XED cross-check.** An iclass is also FP-sensitive if any of its iforms carries the XED
     attribute `MXCSR` or `MXCSR_RD`, or an FP-arithmetic exception class (SSE type 2 or 3; AVX-512
     E2 or E3 and their scalar variants).
     - These names come from reviewer 1 and from the X0 tooling track's `x0_decode.py`, and nobody
       has verified them against the pinned XED.
     - `classify.py` confirms them before freeze or records the substitutes it uses.
     - *Confirmed and substituted* [M, x0prep]: MXCSR and MXCSR_RD exist; MXCSR_RD occurs only on STMXCSR and
       VSTMXCSR, so "MXCSR_RD" cannot mean "uses the rounding mode". XED splits the SDM's exception types 2
       and 3 into SSE_TYPE_2, SSE_TYPE_2D, SSE_TYPE_3 (legacy) and AVX_TYPE_2, AVX_TYPE_2D, AVX_TYPE_3 (VEX);
       the AVX-512 classes are AVX512_E2, AVX512_E3 and the scalar variant AVX512_E3NF. All of these are
       used. Added (stricter): the XED attributes USES_DAZ, USES_FTZ, FLUSH_INPUT_DENORM,
       FLUSH_OUTPUT_DENORM and FIXED_ROUNDING_RNE also make an iclass FP-sensitive.
   - **Disagreement and gaps.** Where the SDM reading and the XED cross-check disagree, the iclass is
     FP-sensitive. A census iclass that is missing from `fp_class.csv` counts as FP-sensitive, and
     only a post-data amendment can change that.
     - *Stated by the x0final revision (review of 2026-10-16/17; documentation only, the CSV is unchanged):*
       instructions that load or store the FP environment are FP-sensitive in `fp_class.csv` only where XED's
       cross-check fires (LDMXCSR, VLDMXCSR, STMXCSR, VSTMXCSR). FLDCW, FLDENV, FRSTOR, FNSAVE, FXRSTOR(64), XRSTOR(64)
       and XRSTORS(64) are "no" (rule templates "reads or writes the x87 control/status/environment as bits" and
       "saves or restores processor state as bits") [M, `fp_class.csv`]. §5's FP-environment list reports every one
       of them whatever its class, and none of them counts towards P5 unless it is FP-sensitive in the CSV. Making
       them "yes" would be stricter and allowed, but it would change the D5 hash and need a new review; the
       asymmetry is recorded instead, and no verdict depends on it at the pinned inputs [inference: Hearth's
       kernels contain none of them].
   - **op_class** (secondary metric only) is computed by this frozen function:
     - strip a leading `V`;
     - arithmetic, SQRT and compare iclasses take an element type from the suffix (PS and SS give
       f32; PD and SD give f64), so ADDPS, ADDSS, VADDPS and VADDSS all give `ADD.f32`;
     - compares into an xmm register or into k give `CMP.<type>`; COMI and UCOMI stay separate
       (`COMI.f32`, `UCOMI.f32`); MAX and MIN stay separate;
     - FMA forms give `<FMADD|FMSUB|FNMADD|FNMSUB|FMADDSUB|FMSUBADD>.<type>`, whatever their
       132/213/231 order;
     - conversions and everything else keep the iclass minus the `V`, so CVTTPS2DQ, CVTPS2DQ,
       CVTDQ2PS and CVTSI2SS are four classes.
     - *Stated by the x0final revision (documentation of the frozen function as implemented; no CSV change):* only
       the PS, SS, PD and SD suffixes are typed. Every other FP iclass (PH, SH, BF16 and the like), including its FMA
       forms, keeps the iclass minus the `V`, with the 132/213/231 digits: VFMADD231SH gives FMADD231SH, VADDSH gives
       ADDSH, VADDBF16 gives ADDBF16 [M, `fp_class.csv`]. The FMA bullet above therefore applies to the PS/SS/PD/SD
       forms only. op_class is a secondary metric, and Hearth's three files use no FP16 or BF16 arithmetic
       intrinsic (§4.5).
5. **Intrinsic-implied baseline.** It is computed before freeze, from the source and the XML only.
   - **Intrinsic set.** Every distinct identifier matching `_mm[0-9]*_[a-z0-9_]+` in `quant_avx2.c`
     and `quant_avx512.c` at b5d3f14. The pattern excludes the `_MM_*` and `_CMP_*` constants.
     - There are 130 such names: 47 `_mm512_*`, 51 `_mm256_*` and 32 `_mm_*` [M, reviser,
       `grep -o … | sort -u` in the clone, 2026-10-16].
     - This matches G02's 130 (my count) [G02 §1].
   - **XML.** `rust-lang/stdarch` `intrinsics_data/x86-intel.xml`, the copy G02 used, at the commit
     in Table 2.1.
   - **Rule for each intrinsic.**
     - Look up the entry by exact name; an absent entry needs a hand mapping.
     - An entry with zero `<instruction>` elements is "no single instruction". It is counted and
       adds nothing.
     - An entry with one or more `<instruction>` elements contributes the union of their `xed`
       attributes.
     - An `<instruction>` with no `xed` attribute gets a row in `hand_map.csv`: intrinsic, name and
       form, the iform it maps to, and the reason. So does an `xed` attribute that names no iform of the
       pinned XED (added by x0prep). At the pinned inputs every instruction element has an `xed` attribute,
       and exactly one names an iform the pinned XED does not define: `_mm256_extractf128_ps`'s
       `VEXTRACTF128_XMMdq_YMMdq_IMMb`, which XED v2026.08.23 calls `VEXTRACTF128_XMMdq_YMMqq_IMMb` (one row)
       [M, x0prep].
     - No intrinsic is excluded by name. A `set1` entry that carries an instruction element
       contributes it.
   - **Sets.** B_iform is the union of iforms. B_mnem is their iclasses, taken from XED's iform to
     iclass table.
   - **Artefacts.** `B_iform.json` (intrinsic → [iform], each tagged as coming from the XML or by
     hand) and `hand_map.csv`. They are written, reviewed (§12) and hashed into Appendix D before
     freeze, and never recomputed after collection starts.
   - **Reconciliation.** The report reconciles each step against G02: 130 names, 23 with no single
     instruction, 105 forms and 74 mnemonics (my count) [G02 §1].
   - **Threshold base.** T_forms = min(|B_iform|, 105) [target; 105 is G02 §1's count and ROADMAP
     §3.1's "~105"]. A larger recomputed value is used only if the Owner's signature line accepts it
     (OQ-5).
   - **Values, filled before freeze:** |B_iform| = 102, |B_mnem| = 74, T_forms = min(102, 105) = 102,
     so the Amber (a) union threshold is |U_all| > 204 [M, `scripts/baseline.py` on the laptop
     (DESKTOP-F441IUK), 2026-10-16, inputs pinned in `class/B_iform.json`].
     - Reconciliation with G02 [M]: 130 names (47/51/32) and 23 with no single instruction both match.
       G02's "105 forms" are the 105 distinct (instruction name, form) strings of the XML; several of them
       map to one XED iform (for example `zmm, zmm, zmm` and `zmm {k}, zmm, zmm` of VADDPS), which gives 102
       XED iforms. The 74 mnemonics match (74 XED iclasses; 74 distinct XML instruction names).
     - The source re-check of P2 holds: the only sequence intrinsic in the three files is
       `_mm256_hadd_epi32` (quant_avx2.c:72-74, six uses); no FMA, RCP, RSQRT or `_reduce_` intrinsic [M].
     - 102 < 105, so OQ-5 does not arise at the pinned inputs.
   - **Not like-for-like with U.** The XML names legacy-SSE iforms for many `_mm_*` intrinsics (for
     example `ADDPS_XMMps_XMMps`), but files built with AVX flags emit VEX forms. The operand-
     normalised comparison of §5 covers this.
   - **Sequence intrinsics at b5d3f14** [M, reviser, grep of the three files, 2026-10-16].
     - `_mm256_hadd_epi32` appears 6 times, all in `red8` (quant_avx2.c:72-74).
     - No `_mm512_reduce_*`, FMA, RCP or RSQRT intrinsic appears in `quant.c`, `quant_avx2.c` or
       `quant_avx512.c`.
     - The horizontal helpers whose lowering §5 records are `tree16`, `hmax16`, `hsum_i32`,
       `red_quads`, `red_quad1`, `canon16` and `canon4` in quant_avx512.c (lines 26-76), and
       `tree16`, `hmax8`, `hsum8_i32`, `red8`, `canon8` and `canon4` (lines 27-76) plus `finish16`
       (lines 148-159) in quant_avx2.c.
6. **Debug-info twin, for source attribution only.**
   - Each file is compiled again from its captured command line with exactly one flag added:
     `/Z7` for A, A-ninja and B-cmake; `-g` for C and D.
   - A variant's attribution is *exact* only if, across every executable section in its closure,
     the twin has identical bytes **and** an identical relocation list (offset, type, target symbol
     name, addend). Otherwise it is *approximate*.
   - Line tables are read with `llvm-dwarfdump` for ELF and `llvm-readobj --codeview` for COFF
     `/Z7`.
   - Counts and verdicts come from the census objects alone.
   - *Mechanisation at freeze (x0final, `x0_twin.py`; Appendix E).* The twin is compiled from build 1's captured
     line (A: the line of the MSBuild log) with the one flag added. Executable sections of the census object and
     the twin are paired by section name plus the names of the function symbols they define; a census section
     without a partner is not identical. Relocation lists are compared as (offset, type, target symbol name,
     addend). ELF: `.debug_line` is decoded with the object's relocations, so every row has its section (in a
     relocatable object every section starts at address 0, so `llvm-dwarfdump`'s text alone cannot place a row),
     and every decoded row (address, line, file, end of sequence) must equal `llvm-dwarfdump --debug-line`'s, in
     order. COFF: `llvm-readobj --codeview` is parsed (procedures, their line tables, nested `S_INLINESITE`
     records and their binary annotations, the inlinee lines). Every line-table row must start on an instruction
     start of `llvm-objdump -d` on the twin. Any failure of these checks makes the object's attribution *none*.
     The line of an address is that of its innermost inline frame; the inline stack (ELF: the call sites of the
     `DW_TAG_inlined_subroutine` entries of `.debug_info`, decoded with relocations and compared with
     `llvm-dwarfdump --debug-info`; COFF: the inline-site depths) is kept for §4.7. Line 0 gives no line.
   - *x0final revision (independent review of 2026-10-16/17).*
     - **Attribution none is a tooling gap** (stricter). A twin that failed to build, or whose line table failed the
       self-checks above, gives every variant of the object attribution *none*, which would silently turn every d2
       site into `unchecked` and every loop to the variant-wide bound. Each such variant of a main-union
       configuration (and A-ninja) now carries the gap `other` ("twin attribution none: <reason>"), so V1 fails
       (`x0_census.py` writes it; `judge.py` also requires attribution exact or approximate for every compiled
       variant). *Approximate* stays as defined above (no gap).
     - **Identity per closure function.** When a paired executable section differs but both have the same size and
       their relocation lists the same offsets and types (no address moved), each function symbol with a size (ELF
       `st_size`) is compared on its own range [st_value, st_value + st_size): identical bytes and identical
       relocations there. A variant is then *exact* when every function of its closure is identical, either because
       its section is or because its own range is. Line rows are already mapped for equal-size sections, so the
       exact functions keep their lines. Without that precondition (a size change, as in the reviewer's experiment
       on `rvx.c`, where a twin built with a changed constant shifted the section by 2 relocations) the section rule
       above applies unchanged. COFF needs no such rule: under `/O2` (`/Gy`) each function has its own COMDAT
       section [inference].
7. **Loops.** These definitions serve P3(c) and the descriptive record.
   - **Natural loop.** The CFG is built over the variant's counted set. A natural loop is a back edge
     t→h where h dominates t. Loops that share a header are merged.
   - **Source loop.** The innermost source loop whose line range contains the header instruction's
     line, according to the twin. Attribution is exact, approximate (§4.6) or none.
     - *Made precise before freeze (x0final; Appendix E).* The header instruction's line is that of the first
       instruction of the header's block that has a line (Clang emits line 0 for some loop headers). When that line
       lies in an inlined function outside every loop of it (a load helper, a compiler intrinsic), the innermost
       source loop containing the inlined call site is taken, walking the inline stack outwards (§4.6). The same is
       done for the back edge's own instruction (the latch, whose line is the loop control). When the two source
       loops nest, the outer one is the loop's source loop; when they are unrelated, the latch's. Measured on the
       regression set: GCC and Clang vectorise the inner `j` loop of an s = 8, 4, 2, 1 tree into straight-line code,
       so the emitted `s` loop has its header on the `j` line (a row with 0 source lanes) and its back edge on the
       `s` line (8 lanes); the header alone gave a false P3(c) flag. Hearth's `dot16_conv` tree (quant.c:362-363)
       has the same shape. A source loop's line range runs from its `for`, `while` or `do` keyword to the end of
       its body, read from the census source.
     - *x0final revision (independent review of 2026-10-16/17; stricter).* Taking the outer loop unconditionally
       could hide a split in a real inner loop whose back-edge line lands on the outer loop (line merging, an
       inlined helper); Hearth's loop table has nests whose outer loop carries far more lanes than the inner one
       (quant_avx512.c:295 with 128 over :300 with 0; quant_avx2.c:274 with 64 over :292 with 0; quant.c:362 with 8
       over :363 with 0) [M, `loop_table.csv`]. The outer loop is now taken only when the inner one shows the signs
       of flattening: (i) no loop of the same variant is attributed to the inner source loop through both its header
       and its back edge, and (ii) the inner loop's `trip_count` in `loop_table.csv` is a compile-time constant or is
       the outer loop's induction variable (the variable of the outer `for`'s init clause, read from the census
       source by `x0_twin.py`; quant.c:363's `s` qualifies). The outer loop is also taken when the emitted loop's
       body encloses another emitted loop attributed to the inner source loop through header and back edge, since
       it then cannot be that inner loop (added by the reviser: measured on the regression set under C, GCC keeps
       j-loops of `smoke_dispatch.c`'s s = 8, 4, 2, 1 tree inside the emitted s-loop, so condition (i) alone checked
       the s-loop's 8 lanes against 0, a false flag in 12 variants [M, x0final revision, desktop, 2026-10-17]).
       Otherwise the loop's P3(c) bound is the smaller of the
       two loops' bounds (each: its own source lanes under exact attribution with a loop-table row, else the
       variant-wide bound). Each loop records `bound_header`, `bound_latch` and `bound_rule` (same, header, latch,
       outer or min), and `census.json` notes list every loop whose rule is outer or min. Residual risk, stated
       before data: an emitted outer loop whose header block starts with code of a real inner loop (runtime trip
       count) gets the inner loop's bound and may be flagged falsely; the notes make such a flag visible, and its
       fix would be a logged tooling fix (§10).
     - *Pre-freeze review revision (independent review of 2026-10-17; stricter).* Condition (i) is vacuous in exactly
       the case it was added for: when a real inner loop's back-edge line lands on the outer loop, that emitted loop is
       the inner source loop's only one. On the reviewer's synthetic cases the rule took the outer bound for a real
       inner loop (trip count 4) nested in an emitted outer loop (A7: 128 instead of 16) and for a helper loop inlined
       into a caller's loop, whose line ranges are disjoint (A8: "unrelated", the latch's 128) [M, reviser, laptop,
       2026-10-17]. Now: (iii) *mirror test*: an emitted loop enclosed by an emitted loop attributed to the outer source
       loop through header and back edge is the inner loop and takes the inner loop's own bound (rule `inner`); if it
       also encloses an emitted loop of the inner source loop, the smaller bound (`min`); (iv) *nesting through the
       inline stack*: when a call site of one source loop's inline stack lies inside the other source loop, the two
       nest, and the rules above apply (a helper loop with a constant trip count and no emitted loop of its own is
       taken as flattened, `outer`; one with a runtime trip count gets `min`); (v) two source loops unrelated by lines
       and by inlining get the smaller bound (`min`; before: the back edge's loop). *Changed in part from the proposal*
       ("min for nesting through inlining"): `min` alone would check a 128-lane `qtile16` g-loop against 0 whenever its
       header's first line came from the inlined `q16_unpack` loop (quant_avx512.c:261, trip count 4) [D, from
       `loop_table.csv` rows 49 and 53]; the flattening test keeps that case at 128 unless the mirror test shows the
       loop is the inner one. `bound_rule` takes the values same, header, latch, outer, inner and min, and
       `census.json` notes list every loop whose rule is outer, inner or min [M, `tests/test_loops_prefreeze.py`].
   - **Loop table.** `experiments/x0-census/class/loop_table.csv` is written from the source before
     freeze. For each source loop it records `file:line`, function, the FP accumulator variables,
     the *source accumulator lanes* (the number of independent FP partial results carried across
     iterations), the operation, and the induction pointer with the bytes it advances per source
     iteration. Illustrative rows follow [D, reviser's reading of b5d3f14; the frozen CSV is
     authoritative]. The frozen CSV has 62 rows: every `for` loop of every function reachable from the 18
     variants through the source call graph; the other 45 `for` loops of the three files lie in functions no
     variant reaches [M, x0prep, check script against the source, 2026-10-16]. Each row lists the variants
     whose closure contains it (`scalar|avx2|avx512` `.` `F32|F16|BF16|Q8|Q4|act`); the illustrative rows
     below all agree with it:

     | Source loop (header line) | FP accumulators | Source lanes | Op |
     |---|---|---|---|
     | quant.c:355 `dot16_conv` i-loop | `L[0..15]` | 16 | ADD |
     | quant.c:397 `mm_q8_scalar` g-loop | `acc` | 1 | ADD |
     | quant.c:416 `mm_q4_scalar` g-loop | `acc` | 1 | ADD |
     | quant.c:329 `act_q8_scalar` amax loop | `amax` | 1 | compare-select |
     | quant_avx2.c:175 `mm_float` 4-row i-loop | `a0,b0 … a3,b3` | 64 | ADD |
     | quant_avx2.c:201 `mm_float` 1-row i-loop | `a0,b0` | 16 | ADD |
     | quant_avx512.c:142 `mm_float` 4-row i-loop | `a0 … a3` | 64 | ADD |
     | quant_avx512.c:167 `mm_float` 1-row i-loop | `a0` | 16 | ADD |
     | quant_avx512.c:282 `qtile16` T = 1 g-loop | `acc` | 16 | ADD |

   - **Loop-carried FP accumulator.**
     - It is a register, or a constant-offset, non-escaping stack slot treated as a register (04 §7.2
       step 4), that is live into the header along the back edge.
     - The body redefines it with an FP-sensitive instruction of op_class ADD, SUB, MUL, MAX or MIN,
       packed or scalar, that reads a loop-carried value.
     - *Emitted accumulator lanes* is the sum of the defining instructions' lane counts: scalar 1;
       f32 in xmm, ymm or zmm 4, 8 or 16; f64 half of that. Masked forms count their full width.
     - *Made precise before freeze (x0prep).* Two numbers are kept apart, because "the sum of the defining
       instructions' lane counts" double-counts a serial chain that an unrolled loop updates twice per
       iteration, while the source side counts *independent partial results*:
       `acc_lanes_emitted` (the P3(c) quantity) = the sum over **distinct** loop-carried accumulator
       locations of the widest lane count of the instructions that define them, the same unit as the loop
       table's source lanes; `acc_updates_per_iter` = the sum over defining **instructions** of their lane
       counts, which feeds u_acc. A loop that keeps one 16-lane accumulator and adds into it four times per
       iteration has 16 emitted lanes and u_acc = 4 (unrolled-u), not 64 lanes; two separate 16-lane
       accumulators for one 16-lane source sum have 32 emitted lanes and are flagged.
     - *Made precise before freeze (x0final; Appendix E).* "Live into the header along the back edge" is read as the
       value carried: a location counts only if its value at the back edge was produced by an accumulating
       instruction (directly or through moves), and locations whose back-edge values come from the same producing
       instruction (a register and its spill copy) are one partial result, so `acc_lanes_emitted` sums the widest
       lane count per partial result. A call defines the caller-saved registers of the object's ABI (SysV for ELF,
       Win64 for COFF). Measured on the census mock (Appendix E): MSVC reused the mask register `xmm1` of a scalar
       max loop (written by MAXSS, reloaded with the mask before the back edge), and GCC's `-fPIC` call returned in
       `xmm0` inside a loop; the literal reading counted each as a second accumulator, a false P3(c) flag. A true
       split carries two values produced by two instructions, so it is still counted. A memory operand
       `[RBP+d]` is a stack slot only while RBP is loop-invariant (GCC at `-O3` uses RBP as an ordinary register;
       measured on the regression set, `[rbp]` stepping through `Y[r]` looked like a carried accumulator), and
       `[RSP+d]` only while no instruction other than PUSH, POP, CALL or RET writes RSP in the loop.
     - *x0final revision (independent review of 2026-10-16/17; replaces the argument above that no true split can be
       hidden, which the review showed incomplete).* The rule above missed true splits whose partial sums pass
       through a non-move instruction before the back edge, compare-select reductions, if-converted accumulations
       and register rotation, and it merged distinct accumulators that met on one path. On the reviewer's synthetic
       streams it counted 0 lanes for two 4-lane chains each permuted by `vpermilps` (true 8), 0 for two
       8-lane `vcmpps`+`vblendvps` max chains (true 16), 0 for two 16-lane add-then-`vblendmps` chains (true 32), 8
       for a rotation `t = acc0 + x; acc0 = acc1; acc1 = t` (true 16) and 8 for two accumulators of which one is
       copied into the other on one path (true 16) [M, x0final revision, laptop, 2026-10-17; reviewer 2's
       `adv_loops.py`]. The rule is now:
       - (a) *Taint.* A location written by any instruction that reads a value an accumulation produced in this
         iteration stays tainted, with provenance the union of the accumulation instructions behind its sources;
         only a write that reads no tainted value, or a call clobber, removes the taint (merge-masked writes keep
         it). MSVC's mask reload and a call's return register therefore still drop out, because neither reads a
         tainted value.
       - (b) *Merging.* Two carried locations are one partial result only when their back-edge provenance is equal
         at every latch (a register and its spill copy), not when the provenances overlap.
       - (c) *Counting.* `acc_lanes_emitted` is the sum, over the strongly connected components of the
         carried-location graph (an edge s → r when the header value of s may reach the back-edge value of r through
         data operands; the address registers of a load are not data) that contain a cycle and a location whose
         back-edge value is tainted, of the component's partial results (its tainted locations grouped by (b), plus
         each untainted carried location of the component, which holds another iteration's partial result) times
         the widest lane count of the accumulation instructions behind it. A self-loop gives 1 partial result; the
         rotation gives 2, so 16 lanes.
       - (d) *Compare-select.* A (V)BLENDV\*, VBLENDM\* or merge-masked FP move that reads a mask written by a
         (V)CMPP\*/CMPS\* and also reads one of the carried or tainted locations that compare read is an
         accumulation of op MAX/MIN, with the lane count of its destination.
       - *FMA.* FMA-class iclasses (§5 P2) count as op_class ADD for accumulator detection, as `x0_loops.py` already
         did (stated here so the record and the code agree; stricter, needed under B-cmake's `-ffp-contract=on`).
       - *Data operands; opmasks* (added by the reviser). "Reads a loop-carried value" and the data flow of (a) to
         (c) use data operands only: the base and index registers of a memory operand are not data (except for
         LEA), so a value loaded through a carried pointer is not a loop-carried value. Opmask registers k0-k7 hold
         no FP partial result and are not nodes of (c). Without these, the broader taint of (a) flagged GCC's
         vectorised quantisation loop of `smoke_dispatch.c` (no FP accumulator in the source; `x[i] * id` compared
         into k0 every iteration) as 16 lanes against 0 [M, x0final revision, desktop, 2026-10-17].
       The six streams now give 8, 16, 16 (two FMA chains, unchanged), 32, 16 and 16; the x0prep and x0final unit
       cases (mask reload, spill copy, call return, serial unroll) are unchanged [M, `tests/test_loops_x0final.py`,
       `TestPartialResultsReview`]. On real compiler output the revised rule was run end to end by the x0final
       revision's step 88 (§7).
     - *Pre-freeze review revision (independent review of 2026-10-17; stricter; replaces the move-only reading in the
       next bullet).* The review showed that (a) to (d) still missed every split whose carried value passes through an
       instruction outside the move whitelist **before** the accumulation: on its synthetic streams the rule counted 0
       lanes for two scalar accumulators carried in GPRs through `vmovd` (true 2), two chains `acc = vpermilps(acc) + x`
       (true 8), a ymm accumulator spilled as two halves (`vextractf128` to the stack, `vinsertf128` back; true 16), a
       `vcmpps` on a copy of the accumulator followed by `vblendvps` on the original (true 16) and the legacy SSE4.1
       select whose mask must be in xmm0 (true 8); 0 for two SSE2 `cmpltps`/`andps`/`andnps`/`orps` max chains (true
       8); and 8 for two accumulators swapped on one path (true 16) [M, reviser, laptop, 2026-10-17; reviewer's
       `adv_pfr.py` against the pinned `x0_loops.py`]. The rule is now:
       - *Reads a loop-carried value* (the accumulation test of the definition above, and the compare of (d)): the value read may be
         reached by the header value of a carried location along **any** data-operand path (the DEP data-flow of
         (c)), not only through register moves and stack reloads; MOVD/VMOVD count as register moves. The cycle and
         taint requirements of (c) still bound what is counted.
       - *(d) Compare-select*: the compare's sources and the select's data operands (other than the mask) must share
         an **origin**, a carried location whose header value reaches both or an accumulation behind a tainted value,
         so a compare on a copy counts. The SSE2 form is a select too: an (V)OR/XOR of (V)AND/ANDN parts of a compare
         mask (the mask followed through register moves), with the compare's lane count (CMPSS 1, CMPPS 4 or 8).
       - *(b) Merging*: two carried locations are one partial result only when their back-edge provenance is equal at
         every latch **and** they hold copies or parts of one value on every path to it (a must-analysis: a pure move,
         or a non-accumulating write whose tainted sources are all one such class, puts its destination in its
         source's class; any other write removes it). The review proposed equal DEP origins instead; the reviser
         measured that origins do not separate the swap (both carry {V0, V1} at the latch) and used the must-analysis.
       After the change the streams give 2, 8, 16, 16, 8, 8 and 16, the true counts; the halves of A3 stay one partial
       result per chain; every earlier unit case is unchanged (mask reload, call return, spill copy, serial unroll,
       induction, load through a carried pointer, T1 to T6), and three further shapes count nothing new: a counter
       converted to float feeding the accumulator, a software-pipelined load, and an argmax index selected by the same
       SSE2 mask [M, reviser, laptop, 2026-10-17; `tests/test_loops_prefreeze.py`]. On real compiler output only a small
       laptop check was possible: on the x0prep reviewer's existing NON-Hearth decodes of `rv_tricky.c` and
       `rv_tricky2.c` (8 configurations, 120 loops, none with an FP accumulator under either rule) the pinned and the
       revised script give identical loop results [M, reviser, laptop, 2026-10-17; no compile, no new decode]. The
       desktop re-run of step 88 (R1 regression replay, R2 mock), required to show that the broader reading adds no
       false P3(c) flag on real GCC, Clang and MSVC output, is pending (§7, Appendix D). *Done 2026-10-17: it did add
       false flags, through the idioms of the next bullet, and none after that fix (§7).*
     - *Desktop re-run of step 88 (2026-10-17; pre-freeze tooling fix, §10; precision).* A **dependency-breaking idiom**
       reads no value: an instruction whose register sources are one and the same register and whose result does not
       depend on that register's value, namely XOR and SUB r,r; (V)XORPS, (V)XORPD, (V)PXOR, VPXORD, VPXORQ,
       (V)PSUBB/W/D/Q and (V)PCMPGTB/W/D/Q x,x (all zero); (V)PCMPEQB/W/D/Q x,x (all ones); not with a memory or
       immediate operand, a write mask or merge masking. XED lists that register as read. Under the DEP reading of the
       bullet above, a register zeroed at the top of an outer loop therefore looked live into the outer header, and the
       inner loop's max chain, or the scalar multiply after an inner integer sum, "read a loop-carried value": the first
       re-run with the re-pinned scripts flagged loops whose source carries no FP value across iterations and whose code
       zeroes every register of the counted cycle with such an idiom before use (`xorps x,x`, `pxor`, `vpxor x,x,x`,
       `vxorps x,x,x`, `xor r,r`): on the mock, the scalar act block loop (A, A-ninja), the scalar act loop and the AVX2
       Q8/Q4 row loop (B-cmake, B-proxy, D), the scalar and AVX2 act loops (C), 26 variant builds in all, 2 to 24 lanes
       against bounds of 0, 1 or 8, all of them block or row loops that re-zero the max or sum each iteration (the
       real amax loops inside them still count their lanes after the fix, 1 scalar and 8 AVX2 where one is emitted);
       on the regression set, `sd_q8`'s row loop (smoke_dispatch.c:132, 0 source lanes) under
       B-cmake, C and D, 24 variant builds [M, desktop runs smoke-20261017T072407Z and smoke-20261017T072727Z; every
       loop re-analysed on the laptop, `runbook/logs/prefreeze_rerun_checks.log` §1]. With the idiom rule every one of
       them counts 0 lanes; the earlier flags keep their counts (Clang's two 16-lane partial results of the tail sum, 32
       lanes; the enclosing loops 16, as in the x0final revision's run, where the broader reading had made them 32)
       [M, final run, §7]. A zero or all-ones idiom's result is a constant, so the rule can hide no partial result.
       `x0_loops.py` `dependency_breaking`; unit cases in `tests/test_loops_prefreeze.py` (an outer loop over a zeroed
       max chain, a zeroed integer sum feeding a scalar multiply, a non-idiom XORPS that still carries, recognition).
     - "Reads a loop-carried value" is decided by a forward data-flow over one iteration (back edges into the
       header cut): the value read may be the one live into the header, directly or through register moves
       and stack reloads (*superseded by the pre-freeze review revision above: through any data-operand path*).
       Merge-masked writes keep the old value. For scalar unary and insert-style
       instructions (`VCVTSI2SS xmm_d, xmm_pass, r32`, `MOVSS xmm, xmm`, `VSQRTSS`, ...) only the last source
       reaches lane 0; the pass-through register does not count as read (otherwise a register reused for an
       integer sum would look like an FP accumulator). A loop-carried location written by a pure copy of a
       value an accumulation produced in the same iteration (a spilled accumulator) is an accumulator.
   - **Unroll factor.** u_acc is the emitted accumulator lanes updated per iteration
     (`acc_updates_per_iter`) divided by the source lanes updated per source iteration. u_ind is the
     primary induction increment divided by the source loop's bytes per iteration. Both are reported, and
     any disagreement between them is reported.
   - **Tags.** A loop may carry several.
     - *lockstep*: u = 1 and no other tag.
     - *unrolled-u*: u > 1; any remainder loop is noted.
     - *rotated*: the exit test is in the latch, with a zero-trip guard before the loop.
     - *peeled*: straight-line copies of the body's FP operation sequence before the header or after
       the exit.
     - *software-pipelined*: a loop-carried value defined in the body by a load rather than by
       arithmetic.
     - *auto-vectorised*: packed FP arithmetic in a loop from `quant.c`, or in any loop whose source
       is scalar.
     - *spilled*: vector stores to and reloads from the stack inside the body.
     - *interchanged*: the iteration order over independent outputs differs from the source nesting.
     - *other*: always comes with a written description.
     - *Mechanisation at freeze (x0prep, `x0_loops.py`).* lockstep, unrolled-u, rotated,
       software-pipelined, auto-vectorised (for the scalar-table variants) and spilled are computed. **peeled
       and interchanged are not detected by the frozen script**; every loop carries
       `not_computed_tags: [peeled, interchanged]`. For the narrowing (§8) such a loop is uncovered unless X2
       lists its loop id in `proved_loop_ids` (the strict reading: an unchecked shape is not a proved one).
       A loop with no FP accumulator and no computed tag is tagged lockstep with `fp_free: true`.
     - *Mechanisation at freeze, completed by x0final (`x0_loops.py`; Appendix E; supersedes the bold sentence
       above).* **peeled** is computed: every FP arithmetic op class of the body (op_class with its element type,
       §4.4, such as ADD.f32 and MUL.f32) occurs in one straight-line region (a chain of single-predecessor,
       single-successor instructions) right before the header or right after an exit. Set inclusion over-tags
       rather than under-tags, the strict direction for the narrowing. **interchanged** is computed for every loop
       of an emitted nest (one body strictly inside another) whose own and partner's source loops are exactly
       attributed: the tag holds when the inner emitted loop's source loop strictly contains the outer emitted
       loop's. A loop of an emitted nest without exact attribution of both loops keeps
       `not_computed_tags: [interchanged]` and stays uncovered for the narrowing unless X2 lists its id; a loop in
       no emitted nest has `not_computed_tags: []`.
   - **Register reuse** (ROADMAP §3.1). The number of vector registers with more than one definition
     per iteration outside accumulator chains. It is descriptive only.

## 5. Metrics

**Primary (gate inputs).** The main union is A, B-cmake, C and D, plus A-ninja where it differs from
A.

- **P1, coverage.** Checked for each configuration and variant:
  - the slot resolved (§4.1);
  - every reachable instruction decoded by XED;
  - every indirect branch resolved;
  - closure ranges consistent (§4.2).

  Each gap carries a cause code.
  - *Genuine* causes:
    - `compile_failed`;
    - `table_or_slot_absent`: the compile succeeded but the table or the slot is not in the object;
    - `xed_gap`: XED cannot decode bytes that `llvm-objdump` decodes with a valid length;
    - `fp_trust_dep`: the variant calls a libm or CRT floating-point function externally, so FP
      semantics lie outside the census.
  - *Tooling* causes: `both_decoders_fail`, `range_mismatch`, `unresolved_indirect` and `other`.

  A tooling bug misfiled as `table_or_slot_absent` would make the outcome stricter, not looser, and
  the independent re-derivation (V3) would catch it.

  **Compile rule** (made exhaustive before freeze by x0prep, because no Hearth file is compiled before
  freeze; `judge.py` decides it from the census build records, not the census script). For each
  configuration, census file and build (§6):
  - *every build*, successful or not, records the SHA-256 of its compiler binaries. They must equal the Table 2.1
    pin of the configuration, mirrored in `class/frozen_inputs.json` "compilers". Otherwise the build is
    *tooling* `other` (made explicit after the §12 review);
  - *every build* (pre-freeze review revision, 2026-10-17; stricter): the configuration's header environment, which
    Table 2.1 pins and `x0_driver.py` records in `config.json` "headers", must equal `class/frozen_inputs.json`
    "headers": Windows SDK 10.0.26100.0, UCRT 10.0.26100.0 and toolset 14.44.35207 for A, A-ninja and B-cmake (as vcvars
    sets them; a trailing path separator is ignored), libc6-dev 2.39-0ubuntu8.9 for C and D, and clang's resource-dir
    include tree for B-cmake (322 files, `5587c91b…a61a12`) and D (327 files, `18b182d3…2f31c`). Otherwise every build of
    the configuration is *tooling* `other`: with a wrong SDK or intrinsic header, an error located in an included
    system header would otherwise pass as a genuine `compile_failed`, and a success could carry other codegen. The
    review found these values recorded but never compared; the reviser also found that D's tree was recorded as null
    in the x0final revision's run (the driver passed clang-cl's `/clang:` form to any compiler whose name contains
    "cl", `clang` included) [M, reviser, read of that run's `config.json` copies, laptop, 2026-10-17]; fixed, to be
    confirmed by the desktop re-run (§7, pending); *confirmed 2026-10-17:* in both runs of the re-run every
    configuration's header environment equals its pin, D's and P.D's tree recorded as 327 files `18b182d3…`, B-cmake's,
    B-proxy's and P.B-cmake's as 322 files `5587c91b…` [M, desktop, §7];
  - *success*: exit status 0 and an object exists. *x0final revision (review of 2026-10-16/17; stricter):* and the
    pinned compiler ran (`compiler_ran`) with exactly the frozen argv (`argv_matches_frozen` true); a build with
    exit status 0 that lacks any of these is *tooling* `other`. Before this, `judge.py` accepted any exit status 0,
    so a build with Debug or added flags would have been censused as Hearth's release build;
  - *genuine* `compile_failed`: non-zero exit in both builds, the pinned compiler ran with exactly the frozen
    argv, and at least one error diagnostic is located in a census file or in a header the build recorded as
    included.
    - The census build records each error's file and line, and its include list (`/showIncludes` or `-H`
      output). The compiler's own intrinsic headers count, for example "always_inline function
      '_mm512_dpbusd_epi32' requires target feature 'avx512vnni'" at quant_avx512.c:237.
    - An internal compiler error in both builds, with the pinned compiler and the frozen argv, is also genuine.
  - *tooling* `other`: any other failure. Examples: the compiler did not start, the argv differs from the frozen
    one, no error diagnostic located in a census file or an included header (a linker error, say), an internal
    compiler error in only one build, or build 1 and build 2 disagree.
  A genuine compile failure gives every variant of the file the gap `compile_failed`: Amber (c) under A or D;
  rows N1 and N2 under B-cmake or C (and A-ninja). It never makes V fail. A census.json that lacks a variant or
  a build record for a main-union configuration or for A-ninja fails V1 (`other`).

  *Build records, mechanised before freeze (x0final, `x0_build.py`, `x0_driver.py`; Appendix E).*
  - Each build configures from scratch in its own directory. A builds the target with MSBuild (one node, detailed and
    binary logs); its records come from the log: each census file's own command line (the CL task's line with only
    that source), the diagnostics in that file's section of the output (cl echoes each source name before compiling
    it), the object named by `/Fo`, and the task's exit status (error MSB6006; a file whose object exists and whose
    section holds no error gets rc 0, because cl compiles the files of a batch independently). The other
    configurations run each census file's `compile_commands.json` entry of the fresh configure verbatim.
  - The argv is never changed. The include list comes from a separate listing pass that writes no object: the same
    argv without its per-file plumbing plus `/showIncludes /Zs` (cl, clang-cl) or `-H -fsyntax-only` (gcc, clang).
  - `compiler_sha256` holds exactly the binaries the configuration's pin lists: `cl.exe`, `c1.dll` and `c2.dll` next
    to the `cl.exe` of the argv; `clang-cl.exe`; the gcc driver's real file and its `cc1`
    (`-print-prog-name=cc1`); clang's real file.
  - `argv_matches_frozen`: the compiler path and the flags without per-file plumbing equal the pre-freeze capture of
    the same file (`flags/prefreeze/`, `flags/C-gcc.*`, `flags/D-clang.*`). For A, whose line exists only in the
    census build (§2), build 1's line is compared with the frozen design-time line of the file and every difference
    is listed. *x0final revision (review of 2026-10-16/17; stricter; replaces the tolerance of any optimisation
    switch, which accepted `/Od`, `/Ob0`, `/O1` or `/GL` and compared token multisets, ignoring the order that decides
    MSVC's last-wins switches):* once the plumbing (`/c`, `/Fo`, `/Fd`, the source) and the console-only switches
    `/nologo` and `/diagnostics:column` [inference: they change only printed output] are removed from both, the line
    matches only if it equals the frozen design-time line plus exactly `/O2` (the frozen vcxproj's Release
    `Optimization` MaxSpeed, which the design-time lines omit), every other token equal and in the same order.
    Measured on a NON-Hearth Visual Studio 17 2022 project with the pinned toolset: the build line is the design-time
    line plus `/nologo`, `/diagnostics:column`, `/O2` and `/Fd`, in order; the rule also holds for all six A build
    lines of the first mock run [M, x0final revision, desktop, 2026-10-17; `runbook/logs/x0final_rev_probes.log`].
    Build 2's line must equal build 1's.
  - *MSBuild single-file fallback (x0final revision).* MSBuild stops the target at the first failed CL task, so a
    genuine failure of one batch leaves the census files of later batches uncompiled: on the NON-Hearth probe
    project a failing two-file batch left the `/arch:AVX2` file's CL task unrun [M, same log]. For each census file
    without a CL task in the build's log, the driver then runs `msbuild <project> /t:ClCompile
    /p:Configuration=Release /p:Platform=x64 /p:SelectedFiles=<source>` (one node, detailed log), which ran the same
    CL task with the same line for that one file on the probe [M, same log], and takes the file's record from that
    log (`fallback`). A file that still has no CL task is *tooling* `other`.
  - Errors: `file(line[,col]): [fatal] error ...` (cl, clang-cl) and `file:line[:col]: [fatal] error: ...` (gcc,
    clang); an error without a location gets file null. ICE: MSVC C1001 or "INTERNAL COMPILER ERROR", Clang "PLEASE
    submit a bug report" or "frontend command failed due to signal", GCC "internal compiler error".

  `fp_trust_dep` uses the strict allow-list rule of §4.2: any external callee not on the frozen non-FP list.
- **P2, contraction.** The number of FMA-class instructions in each variant's counted set:
  iclasses VFMADD\*, VFMSUB\*, VFNMADD\*, VFNMSUB\*, VFMADDSUB\*, VFMSUBADD\*, and FMA4 forms. Hearth's
  source at b5d3f14 contains no FMA intrinsic (§4.5), so any FMA-class instruction is a contraction.
  The script re-checks the source. `judge.py` does not trust the census counter alone. Per variant it takes the
  larger of `p2_fma` and the number of FMA-class instructions in the variant's iclass counts (made explicit after
  the §12 review).
- **P3, reassociation screen.** X0 can screen for reassociation but cannot prove its absence (§8,
  Pass; OQ-3). A variant is flagged if any of the following holds.
  - **(a) Flags.** The effective settings match a pattern in
    `experiments/x0-census/class/fp_flag_patterns.txt`, which is frozen with this record (Appendix D).
    - "Effective settings" means: for A, the exact `cl` line from the MSBuild log; for A-ninja, its
      `compile_commands.json` line; for B-cmake and D, the cc1 line expanded by `clang-cl -###` or
      `clang -###`; for C, the command line plus the values printed by
      `gcc <flags> -Q --help=common,optimizers`.
    - The patterns include at least the following. They contain the forbidden list of
      [04 §6.2](../../architecture/04-toolchain.md#62-strict-fp-flags-per-compiler-v0).
      - (a1) **Contraction-enabling:** `/fp:contract`; `-ffp-contract=(on|fast|fast-honor-pragmas)`;
        a GCC effective `-ffp-contract` value other than `off`. GCC defaults to `fast` outside ISO
        modes and Clang's C default is `on` (04 §6.2), so the check reads effective values.
      - (a2) **Reassociation or value-unsafe:** `/fp:fast`, `/Qfast_transcendentals`,
        `-ffast-math`, `-Ofast`, `-ffp-model=(fast|aggressive)`, `-fassociative-math`,
        `-mreassociate`, `-funsafe-math-optimizations`, `-menable-unsafe-fp-math`,
        `-freciprocal-math`, `-fapprox-func`, `-ffinite-math-only`, `-menable-no-nans`,
        `-menable-no-infs`, `-fno-honor-nans`, `-fno-honor-infinities`, `-fno-signed-zeros`,
        `-fdenormal-fp-math=(preserve-sign|positive-zero)` and `-mdaz-ftz`.
      - Also matched, under (a2): a GCC effective value that enables `-fassociative-math`,
        `-freciprocal-math`, `-ffinite-math-only` or `-funsafe-math-optimizations`, or that
        disables `-fsigned-zeros`.
  - **(b) Approximations.** The counted set contains an approximation iclass with no matching source
    intrinsic. There are none at b5d3f14 (§4.5). The iclasses are RCPPS, RCPSS, RSQRTPS, RSQRTSS and their V
    forms, VRCP14\*, VRSQRT14\*, VRCP28\* and VRSQRT28\*.
    - Added after the §12 review, which is stricter: the FP16 and BF16 forms VRCPPH, VRCPSH, VRSQRTPH,
      VRSQRTSH, VRCPBF16 and VRSQRTBF16; VEXP2PS and VEXP2PD; and the 3DNow! PFRCP\* and PFRSQ\* iclasses.
      All exist in XED v2026.08.23 [M, `class/xed_tables.tsv`]. None is reachable under Hearth's flags
      [inference: no `-mavx512fp16` or 3DNow! flag].
  - **(c) Accumulator splitting.** In any variant and any configuration, a loop's emitted
    accumulator lanes (§4.7) exceed the source accumulator lanes of its attributed source loop.
    - If attribution is approximate or missing, the bound is the largest source-lane count among
      the variant's source loops in `loop_table.csv`, and the loop is listed as *unattributed*.
    - Lane-preserving vectorisation is not flagged. Holding `dot16_conv`'s 16 lanes in four xmm
      registers, for example, only earns the *auto-vectorised* tag.
  - **(d) Canaries,** checked mechanically for each configuration.
    - (d1) The closure of `act_q8_scalar` must contain a pair of FP instructions, scalar or packed:
      - an ADD whose constant operand has every lane equal to M = `0x4B400000` (12582912.0f,
        `q_rint`'s magic, quant.c:47);
      - then a SUB of M, or an ADD of −M (`0xCB400000`), which IEEE makes identical, that reads
        the first instruction's result through moves only.

      Constants are resolved through constant-pool relocations or GPR immediates. Any reassociation
      folds `(v + M) − M` to `v`. If the pair is missing, the variant is flagged. Any d1 value other than an
      explicit `pass` flags the variant, including an absent result or `not_evaluated`. This applies to
      every present, compiled `hx_kernels_scalar:act_quantize_q8` variant of a main-union configuration and
      build (A-ninja: union members). `x0_loops.py` exits non-zero when a canary key matches no variant (made
      explicit after the §12 review).
    - (d2) Every `tree16` site in both SIMD files is checked by a lane-provenance tracker.
      - The tracker evaluates the attributed straight-line sequence from the 16 accumulator lanes
        to the scalar result.
      - It follows a whitelist: FP ADD; VEXTRACTF128, VEXTRACTF32X4, VEXTRACTF64X4 and
        VEXTRACTF32X8; (V)MOVHLPS; (V)SHUFPS; (V)MOVSHDUP; VPERMILPS; (V)UNPCKHPD; VPERMQ and
        VPERMPD; VSHUFF32X4 and VSHUFF64X2; register moves; and stack spills and reloads, which
        count as identity. Added before freeze by x0final (stricter, Appendix E): (V)SHUFPD and VPERMILPD with an
        immediate.
      - The result must equal the s = 8, 4, 2, 1 tree of quant.c:362-363, allowing commutation of
        each add.
      - A mismatch flags the variant. A sequence that leaves the whitelist, or an approximate
        attribution, makes the site *unchecked*: it is reported and not flagged (§9).
    - *Mechanisation at freeze (x0prep, `x0_loops.py`).* (d1) runs over the closure in address order,
      tracking constants from relocated memory operands (bytes read from the object's constant pool) and from
      GPR immediates moved into vector registers, and register moves; the SUB must have the `v + M` value as
      its minuend. Unit tests cover the VEX, legacy-SSE and GPR-immediate shapes and a reversed subtraction;
      on the smoke file the pair is found in all eight smoke objects [M]. (d2): the lane-provenance tracker
      `track_tree16` implements the whitelist and the commutation rule and is unit-tested on the AVX-512 and
      AVX2 `tree16` shapes, on a wrong pairing (mismatch) and on an off-whitelist instruction (unchecked).
      Selecting the sites needs exact twin attribution (§4.6).
    - *Site selection and attribution, x0final (`x0_twin.py`, `x0_loops.py`; Appendix E).* With exact attribution, the
      reachable instructions whose innermost inline frame in a census source file lies in `tree16`'s body form the
      sites: runs along fall-through edges in address order, with at most 16 interleaved instructions of other
      lines, none of which may write a register the site reads later (else `unchecked`). Helpers inlined into
      `tree16` (`canon4`) keep their own frame and are not part of the site; frames in the compilers' intrinsic
      headers are skipped. A site's sequence ends at its last FP ADD, the scalar result of the tree. Its live-in
      vector registers must be one 16-lane register or two 8-lane registers, else `unchecked`. The whitelist above
      is extended by (V)SHUFPD and VPERMILPD with an immediate, pure 64-bit-half permutations: Clang lowers
      `_mm_movehl_ps(v, v)` to `vshufpd` (measured on the census mock), so without them every Clang site would be
      `unchecked` (stricter: more sites checked). Without exact attribution every expected site (the F32, F16 and
      BF16 variants of `k_avx2` and `k_avx512`) is `unchecked` (x0final revision: attribution *none* is also a tooling
      gap, §4.6, so this cannot pass silently). P3(c) uses a loop's own source lanes when its
      source loop is exactly attributed and has a row in `loop_table.csv`, otherwise the variant-wide bound, with the
      loop listed as unattributed.
    - *Reporting, fixed before freeze by the pre-freeze review revision (2026-10-17; no gate reading changes).* d2 can be
      vacuous without a gap: every expected site may come out `unchecked` (approximate attribution is not a gap, and a
      lowering outside the whitelist, such as MSVC's `vpsrldq` seen in arm P, is not either). `judge.py` therefore writes
      into `verdict.json` "canaries", under the label "outcome indicated before freeze by a verbatim copy (E6)": the d1
      result of every canary variant, the expected d2 sites (F32, F16, BF16 of `k_avx2` and `k_avx512`) of each
      main-union configuration and A-ninja counted by result (match, mismatch, unchecked, variants without a d2 result),
      and the P3(c) results of the scalar F32, F16, BF16 and act variants (§2 disclosure). **Registered before data:** if
      every expected d2 site under A or under D is `unchecked`, `verdict.json` "caveats" says so, and on Pass it is a
      caveat on Pass, reported with the verdict; it changes no outcome.
- **P4, table size.** |U_all|: the number of distinct XED iforms over the counted sets of all 18
  variants, scalar included, under every main-union configuration (OQ-2).
- **P5, FP-sensitive mnemonics.** P5_iclass: the number of distinct FP-sensitive XED iclasses
  (§4.4) over the same set (OQ-1).

**Secondary (reported, no threshold)**
- **Union sizes:**
  - \|U_all^S\|, category S only;
  - \|U_all^SIMD\|, the AVX2 and AVX-512 variants only, and \|U_all^SIMD,S\|, the same restricted to
    category S. The latter is the closest to like-for-like with B_iform;
  - \|U_release\|, over A and D;
  - \|U_object\|, from arm S-object;
  - \|U_helpers\| and the helpers' FP-sensitive iclasses, from arm S-helpers, as an addendum to X2's
    scope list;
  - iform sets per configuration and per variant, plus the G-category and orphan counts.
- **Delta against B_iform:** added, missing and shared forms. The delta is given twice, raw and after
  operand normalisation, which maps memory-operand forms to register forms, legacy-SSE forms to VEX,
  and opcode-direction twins to one form.
- **Mnemonics and op_class:** \|iclass union\| for the SIMD variants against \|B_mnem\|, and
  P5_opclass (§4.4).
- **Proxy fidelity:** for each variant, the Jaccard index of the iform sets of B-proxy and D, and how
  far their loop tag sets agree. This is measured evidence for X3's proxy assumption.
- **Lift blockers** for each variant under A and D (§4.2).
- **EVEX static rounding and SAE:** for each variant, the number of instructions with EVEX.b set on
  register-only operands (XED's ROUNDC and SAE fields). Such an instruction has the same iform as
  its MXCSR-governed form, so any under A or D is listed as needing a rounding-override entry in the
  table.
- **Reduce probe** (arm P): each emitted sequence and its lane pairing, compared with the XML's
  halving tree [G02 §6].

**Descriptive (the roadmap's loop-correspondence record)**
- **Horizontal sequences:** for each horizontal helper named in §4.5 and each `_mm256_hadd_epi32`
  site, the emitted iclass sequence under each configuration, located through twin attribution.
- **Per loop:** the tags of §4.7; u_acc and u_ind; rotation; peeled copies; pipelining; spills and
  reloads inside the body; register reuse; how the loop was attributed.
- **Operand order:** for every MAX, MIN and CMP site attributed to a source intrinsic or expression,
  whether the emitted operand order and predicate match the source. Hearth relies on this: "NaN in
  the first operand is skipped" (quant_avx512.c:88, quant_avx2.c:90); quant.c:338-340. MAXPS's
  operand rule is in [G02 §1].
- **FP-environment instructions anywhere in the three objects:** LDMXCSR, STMXCSR, VLDMXCSR,
  VSTMXCSR, FLDCW, FNSTCW, FLDENV, FNSTENV, FRSTOR, FNSAVE, FXRSTOR, FXRSTOR64, XRSTOR, XRSTOR64,
  XRSTORS, XRSTORS64, FNINIT and FNCLEX. The waiting forms FSTCW, FSTENV, FSAVE, FINIT and FCLEX
  decode as FWAIT followed by the FN form.
- **External calls** for each variant.

## 6. Sample and power

The census is exhaustive: every dispatched variant under every configuration. It involves no
sampling and no statistics.

Reproducibility check. Each main-union configuration is built twice from clean build directories.
For each object and each executable section, the hash of the bytes plus the relocation list must
match.
- A mismatch is a finding.
- Both builds are then censused, and P2 to P5 use the union of the two.
- If either build is flagged, the variant counts as flagged.
- *Mechanised (x0final).* `x0_driver.py` configures each build in its own fresh directory; `x0_census.py` compares
  build 1 and build 2 per file and executable section (bytes and relocation list, sections paired as for the twin)
  and records the result in `configs.<cfg>.repro`. Both builds' variants are in `census.json` (`build_index` 1 and
  2), so `judge.py` already takes the union and flags a variant if either build is flagged.

## 7. Analysis procedure

**Scripts.** All live in `experiments/x0-census/scripts/`, and the result manifest records their
commit hash.

| Script | Job |
|---|---|
| `x0_flags.py` | flag capture; P3(a) matcher (`p3a`); B-proxy lines (`proxy`) |
| `x0_extract.py` | §4.1 (tables and slots from the source, slot -> function by relocation) and the object model of §4.2 (ranges, `.pdata` check, resolved relocations) |
| `x0_decode.py` | §4.2 recursive descent and call kinds, XED decode, the cross-decoder check |
| `x0_norm.py` | the `objdump_norm.csv` normaliser |
| `x0_loops.py` | §4.7, P3(c) and P3(d) |
| `classify.py` | §4.4, before freeze |
| `baseline.py` | §4.5, before freeze |
| `judge.py` | §8: reads `census.json`, writes `verdict.json` |
| `x0_build.py` | §5 P1 build records: compiler pins, argv check, structured errors, include lists, ICE (x0final) |
| `x0_twin.py` | §4.6: twin identity, line tables, inline stacks, source loop and function extents (x0final) |
| `x0_census.py` | Appendix C: the `census.json` assembler, including §6 repro and the A versus A-ninja comparison (x0final) |
| `x0_driver.py` | the census driver: one command per configuration, then assembly and `judge.py` (x0final) |

The `x0_extract.py` and `x0_decode.py` present on 2026-10-16 describe, in their headers, COFF ranges
taken up to the next symbol and a linear-sweep decode [M, reviser, read, 2026-10-16]. They must
implement §4.2 before freeze (Appendix D, item D11). *Done by x0prep*: both were rewritten to §4.1/§4.2 and
validated on `scripts/smoke/smoke_dispatch.c` (NOT Hearth; two dispatch tables shaped like Hearth's, 12
slots) under A, B-cmake, C and D with each configuration's `quant_avx512.c` and `quant.c` command lines
[M, x0prep, runbook step 72, desktop, 2026-10-16]: 12/12 slots resolved by relocation in all 8 objects, 0
tooling gaps, 0 cross-decoder disagreements, `llvm-readobj` symbol cross-check clean; a deliberately
corrupted manifest makes the decode fail. The `census.json` assembler, the twin attribution, the build records and
the census driver, missing at that point (Appendix D, D11), were added by x0final (below).

*Revised after the §12 review.* Reviewer 2 showed that the smoke file did not exercise the hard cases. On two
adversarial NON-Hearth files, the decoder of that date produced two silent false negatives and six
misclassifications (§12). `x0_decode.py` and `x0_extract.py` were revised to the §4.2 text above. Runbook steps
71b and 72 now compile `smoke_dispatch.c` and the reviewer's adversarial files `rv_tricky.c` and `rv_tricky2.c`,
adopted unchanged in `scripts/smoke/`, under the A (A-ninja lines), B-cmake, C and D command lines of
`quant_avx512.c` and `quant.c`. That gives 24 objects. Each is decoded twice, with opposite work-list orders,
and `smoke/check_smoke.py` compares all 168 variants with `smoke/tricky_expect.json`.

Result [M, x0prep reviser, desktop, 2026-10-16; `scripts/runbook/logs/x0prep_72_regression_check.log`,
`scripts/smoke/results_regression.json`]: 0 deviations, and the two decodes of every object are byte-identical.
- `smoke_dispatch.c`: unchanged against the earlier run in slots, gaps (6 designed `fp_trust_dep`),
  cross-decoder check and d1. |U_iform| is unchanged for A, A-scalar, C, C-scalar, D and D-scalar (99, 90, 148,
  99, 140, 118). It is one lower for B and B-scalar (149→148, 121→120), because the INT3 after clang-cl's
  `/GS` failure call is no longer reached (no-return rule).
- The adversarial functions give the expected outcome in every configuration:
  - the indirect tail calls (`rv_tailsw`, `rv_pf`) are `unresolved_indirect` next to a correctly bounded table;
  - GCC's switch cases in `.cold` (`rv_coldsw`, `rv_coldsw2`) bring `<f>.cold` and `rv_cold` into the closure,
    with the `fp_trust_dep` `rv_ext_log` and no orphan bytes;
  - the call through `extern void (*rv_hook)()` is `unresolved_indirect` under A and B as well;
  - the user no-return calls give no gap;
  - the overlapping decode is a gap `other` under C and D;
  - MSVC's byte index table is data (orphan bytes 0, dword table 10 entries);
  - the GCC tables adjacent in `.rodata` keep their bounded 63 entries.

*Pre-freeze review revision (2026-10-17, laptop only; the desktop's quiet window was kept).* The runs described next
were made with the x0final revision's scripts. This revision changed code that they exercise: `x0_loops.py` (§4.7:
carried reads through any data operand, compare-select origins and its SSE2 form, merging only copies or parts of one
value, the source-loop mirror test, nesting through inlining, `min` for unrelated loops), `x0_driver.py` (the freeze
point, per-step script and blob re-checks, the shingle guard, the resource-dir call for `clang`), `x0_census.py` and
`judge.py` (§8 items 9 and 10), and the text of three runs of `smoke_dispatch.c` (§2). It ran the 179 unit tests (all
pass) and the small rule comparison of §4.7, and nothing else; it compiled and decoded nothing. **Pending, on the
desktop outside a quiet window:** runbook step 88 again (R1 regression replay, R2 mock in census mode, the fallback is
unaffected), with the re-pinned scripts, to show (a) `check_regression_run.py` still 0 deviations with the rewritten
`smoke_dispatch.c`, (b) no P3(c) flag beyond the 24 variants of the x0final revision's R1 run and none on the mock that
the earlier rules did not raise, each new flag explained or fixed before freeze, and (c) every configuration's header
environment equal to its pin (`judge.py` V1), in particular D's resource-dir tree. The re-run's P3(c) results on
`smoke_dispatch.c`'s tree, accumulation and amax loops bear on the same Hearth shapes as before and fall under the E6
label (§2). Until then the end-to-end evidence below is for the previous scripts. *Done: the re-run is described next;
the paragraphs after it are the earlier scripts' evidence.*

*End-to-end validation of the driver, pre-freeze review revision: the desktop re-run* [M, desktop DESKTOP-8RS9J1J,
2026-10-17 03:23-03:55 EDT (00:23-00:55 PDT), inside the 23:00-07:00 PT window by the lead engineer's authorisation for
that night (not a pilot quiet night); runbook steps 86 and 88 on a sync copy of the tree (`D:\mithril\x0reg`); one
compiler or MSBuild node at a time, XED `-j 2`, at most 4 threads, `CUDA_VISIBLE_DEVICES=-1`, WSL only inside the
running keepalive VM; logs `scripts/runbook/logs/prefreeze_rerun_*`, results `scripts/smoke/results/prefreeze_rerun/`].
NON-Hearth inputs only.
- *First run, with the scripts of commit 2191ff8 as pinned* (runs `smoke-20261017T072407Z` R2 and
  `smoke-20261017T072727Z` R1, `scripts_match_pins` true): (a) held, `check_regression_run.py` 0 deviations over 60
  decode outputs (420 variants); (c) held, every configuration's header environment equals its pin (A to D, B-proxy and
  every P.<CFG>; D 327 files `18b182d3…`); (b) failed: besides the 24 earlier regression variant builds, P3(c) flagged
  24 more (`sd_q8`'s row loop, 8 each under B-cmake, C and D) and 26 mock variant builds (A 2, A-ninja 2, B-cmake 6,
  B-proxy 6, C 4, D 6), and the earlier enclosing loops counted 32 lanes instead of 16. Every one of these came from
  dependency-breaking idioms read as data (§4.7, bullet "Desktop re-run of step 88"), so they are false flags. Every
  other figure of the run summaries (attribution, d1, d2, tags, P3(a), metrics, verdict outcomes) equals the x0final
  revision's.
- *Pre-freeze tooling fix* (§10, Appendix E): the idiom rule in `x0_loops.py` with four unit tests (183 in all, all
  pass), re-pinned (`x0_loops.py`, `tests/test_loops_prefreeze.py`, `class/frozen_inputs.json`; `pin_inputs.py` 0
  differences on the laptop and on the desktop's sync copy).
- *Final run with the re-pinned scripts* (runs `smoke-20261017T074224Z` R2, 03:42-03:46 EDT, and
  `smoke-20261017T074551Z` R1, 03:46-03:49 EDT; `scripts_match_pins` true; `census.json` records `x0_loops.py`
  `8c7ecc9e…`). (a) `check_regression_run.py` 0 deviations over 60 decode outputs (420 variants); d1 `pass` and
  attribution exact everywhere; builds 1 and 2 identical; 32 cross-decoder disagreements, all NOP (`rv_overlap`).
  (b) P3(c) flags exactly the x0final revision's 24 regression variant builds through the same loops (B-cmake: the tail
  loop `L19_2a0`, 32 lanes over 16, and its enclosing loops `L19_1ca` and `L19_123`, 16 over 0; D: `L2_10c0`, `L2_f34`,
  `L2_e66` likewise), none under A, A-ninja or C, and none on the mock. (c) Every configuration's header environment
  equals its pin, as in the first run. On the mock: 0 non-zero steps; every compiler pin and argv check holds; builds 1
  and 2 identical; A and A-ninja identical for all 36 variants; d1 `pass`; d2 `match` on the AVX-512 `tree16` and
  `mismatch` on the AVX2 `tree16` (designed); P3(a1) on B-cmake; B-cmake's genuine `quant_avx512.c` failure. `judge.py`:
  V1, V2, V4 true, V3 false: `tooling_failure`; with V3 forced (smoke only) `amber_a` (|U_all| 326 > 204, P5_iclass 31),
  `amber_b`, `amber_c` (32), N1 (B-cmake, C), N2 (B-cmake). Regression set: `tooling_failure`; with the set's constants
  V1 fails on the 184 designed gaps, V2 and V4 hold. Against the x0final revision's summaries the only differences are
  descriptive: fewer `software-pipelined` and more `lockstep` tags, `unrolled-u` under D 68 → 64 loops, and the B-proxy
  tag agreement of three AVX-512 slots, all from registers no longer taken as carried; arm P's probe records are
  identical. The decoded code of the rewritten `smoke_dispatch.c` is described in §2 (remedy). The MSBuild fallback was
  not repeated (its build path is unchanged).
- *Freeze point and Hearth HEAD* (§8 item 10): `x0_driver.py init`'s freeze-point logic ran with Windows git 2.45.1 and
  Python 3.13.4 against a THROWAWAY repository with this layout (record DRAFT, then FROZEN in one commit, then appended
  amendments, tooling changes and in-place edits). It accepted the freeze point itself (`freeze_commit` = `run_commit`),
  an appended amendment, and a tooling change named in the amendment with its re-pin (listed in
  `post_freeze_changes`); it refused a DRAFT record, an uncommitted edit, an untracked file, an ignored `.pyc`, an
  unnamed class/ or flags/ change, a named but not re-pinned script, an in-place edit (alone, behind an appended
  amendment, or through DRAFT and FROZEN again) and a `--record` outside the checkout: 16 of 16 scenarios as expected,
  the last one with the real Hearth source checks [M, `runbook/logs/prefreeze_rerun_checks.log` §5,
  `smoke/results/prefreeze_rerun/gitlogic_throwaway.json`]. A change outside class/, scripts/ and flags/ (FREEZE.md)
  is accepted, by design. Windows git reads `D:\mithril\src\hearth` at b5d3f14a801d… directly (rc 0); `.git/HEAD` holds
  the same commit, and `source_commit` returns it also with no git on PATH (the fallback); the seven blobs match [M,
  §4 of that log].

*End-to-end validation of the driver, x0final revision* [M, x0final revision, desktop, final run 2026-10-17 01:49-01:57
EDT (22:49-22:57 PDT), runbook steps 86 and 88 with the final scripts, runs `smoke-20261017T054918Z` (R2) and
`smoke-20261017T055241Z` (R1), `scripts_match_pins` true in both; `scripts/runbook/logs/x0final_rev_*`,
`scripts/smoke/results/x0final_rev/`]. NON-Hearth inputs only; it supersedes the x0final runs described next, whose mock
contained Hearth helpers (§2). After these runs only four pinned files changed, none in its code: two unit tests were
added to `tests/test_driver_guard.py`; the module docstrings of `x0_loops.py` and `x0_twin.py` were brought up to
date (their code is identical to the runs', checked by comparing the parsed modules without the docstring); and the
text of the mock's marker file `X0_NOT_HEARTH` was corrected (the driver checks only that it exists) [M, reviser,
laptop, 2026-10-17]. The desktop was not used again: the quiet window began at 23:00 PT.
- *Census mode on the rewritten mock*: A, A-ninja, B-cmake, C and D, two configures and builds each, the twin, P3(a),
  extract, decode, attribution, loops; arm P and B-proxy. Every build's compiler pins and argv check hold (A's under
  the exact `/O2` rule); builds 1 and 2 identical for every object; A and A-ninja identical for all 36 variants; every
  variant's attribution exact; B-cmake fails to compile the mock's `quant_avx512.c` in both builds, a genuine
  `compile_failed`. d1 `pass` everywhere; P3(d2): the AVX-512 `tree16` gives `match` and the AVX2 `tree16`, which
  pairs adjacent lanes first by design, gives `mismatch` in every configuration that compiles it (6 and 6 sites per
  configuration over both builds; B-cmake 6 `mismatch`); no P3(c) flag; P3(a1) on B-cmake for all three files.
  `judge.py`: V1, V2, V4 hold, V3 fails: `tooling_failure`. With V3 forced (smoke only): `amber_a` (|U_all| 326 > 204,
  P5_iclass 31 > 20), `amber_b` (A, C and D through the designed d2 mismatch; B-cmake through P3(a1), P2 = 20 and the
  same mismatch), `amber_c` (32 genuine `fp_trust_dep` gaps under A and D), N1 (B-cmake, C), N2 (B-cmake).
- *Replay mode on the regression set*: `check_regression_run.py` 0 deviations over 60 decode outputs (420 variants);
  d1 `pass` everywhere; attribution exact everywhere; 32 cross-decoder disagreements, all NOP (`rv_overlap`, by
  design). P3(c) flags the same variants as the x0final run (12 under B-cmake, 12 under D: Clang's two 16-lane partial
  results for `smoke_dispatch.c`'s 16-lane tail sum, and its enclosing loops), with the tail loop still at 32 lanes;
  the enclosing loops now count 16 instead of 32 (the register that the earlier rule also counted is not in a cycle).
  An intermediate run of the revision, before the data-operand, opmask and enclosing-loop precisions of §4.7, had
  flagged 16 more variants under C (GCC's quantisation loop and the s-loop of the tree); the final run flags none
  under C. `judge.py`: `tooling_failure`; with the set's constants V1 fails on the 184 designed tooling gaps, V2 and
  V4 hold.
- *MSBuild fallback*: on a copy of the rewritten mock with a broken `other.c` (configuration A only), MSBuild stopped
  after the failing batch in both builds; `quant_avx2.c` and `quant_avx512.c` were compiled by the single-file
  `ClCompile` fallback (rc 0, objects present), and `quant.c`, whose object the failing batch did produce, got rc 0
  with no error of its own (`runbook/logs/x0final_rev_fallback.log`).

*End-to-end validation of the driver, x0final (superseded; first mock, which contained Hearth helpers, §2)* [M, x0final,
desktop, final run 2026-10-17 00:26-00:35 EDT, runbook step 88; `scripts/runbook/logs/x0final_*`,
`scripts/smoke/results/x0final/`]. NON-Hearth files only.
- *Census mode on the census mock* (`scripts/smoke/mock/` as it was then: Hearth's table shape and CMake flag logic, and kernels
  whose helpers were verbatim Hearth code, §2;
  configure-only captures by step 86 serve as its frozen lines). A, A-ninja, B-cmake, C and D: two configures and
  builds from scratch each (A through MSBuild, `quant.c` batched with another file in one CL task), the twin, P3(a),
  extract, decode, attribution, loops; arm P (P.<CFG>) and B-proxy. Every build's compiler binaries equal the Table 2.1
  pins; every argv check holds; builds 1 and 2 are byte- and relocation-identical for every object; A and A-ninja are
  identical for all 36 variants; every variant's twin attribution is exact and every loop gets a source loop. B-cmake
  fails to compile the mock's `quant_avx512.c` in both builds ("always_inline function '_mm512_dpbusd_epi32' requires
  target feature 'avx512vnni'", located in the file, 146 includes recorded), a genuine `compile_failed`. d1 passes
  everywhere; every `tree16` site of the mock is `match` (A, A-ninja, C, D: 12 per configuration over both builds;
  B-cmake: 6, `quant_avx2.c` only); P3(c) flags nothing; P3(a1) matches B-cmake for all three files. `judge.py` on the
  resulting `census.json`: V1, V2 and V4 hold, V3 fails (no re-derivation), outcome `tooling_failure`, as required
  before a re-derivation exists. With V3 forced in memory (`smoke/judge_regression.py --synthetic-rederivation`, smoke
  only): `amber_a` (|U_all| 316 > 204, P5_iclass 29 > 20), `amber_b` (B-cmake, P3(a1)), `amber_c` (32 genuine
  `fp_trust_dep` gaps under A and D: the mock's SIMD files call a conversion helper defined in its `quant.c`), rows N1
  (B-cmake, C) and N2 (B-cmake).
- *Replay mode on the regression set* (`smoke_dispatch.c`, `rv_tricky.c`, `rv_tricky2.c` with the frozen
  `quant_avx512.c` and `quant.c` lines of A (A-ninja capture), A-ninja, B-cmake, C and D): `smoke/check_regression_run.py`
  finds 0 deviations from `smoke/tricky_expect.json` over 60 decode outputs (420 variants), builds 1 and 2 decode
  identically, d1 passes in every configuration, every variant's attribution is exact. P3(c) flags only Clang's
  vectorisation of `smoke_dispatch.c`'s scalar `L[i & 15]` tail loop (B-cmake and D: two 16-lane partial results for a
  16-lane source sum) and the loops enclosing it, as the x0prep run had noted. `judge.py` says `tooling_failure` (the
  regression set has none of Hearth's 18 variants, and its designed tooling gaps fail V1); with the set's own constants
  (`judge_regression.py --set`) V1 still fails on the 184 designed tooling gaps of `rv_tricky*.c`, V2 and V4 hold.
- Arm P was run too; see the disclosure in §2.

**Raw outputs.** The objects, build logs, XED decode dumps, `llvm-objdump` disassembly and the twins'
line tables. Results land in `experiments/x0-census/results/` as `census.json` (Appendix C),
`verdict.json` and REPORT.md.

**Cross-decoder check.**
- For every reachable instruction, the XED instruction length must equal `llvm-objdump`'s.
- The XED iclass is compared with the `llvm-objdump` mnemonic through
  `experiments/x0-census/class/objdump_norm.csv`, which is frozen before collection.
- Every disagreement is listed. A disagreement where either side maps to an FP-sensitive iclass
  blocks validity check V2 (§8) until it is resolved.
- `objdump_norm.csv` was validated before freeze on a NON-Hearth corpus [M, x0prep, `class/objdump_norm_validation.json`]:
  an "instruction zoo" generated from the pinned XML (one wrapper per intrinsic of the SSE to AVX-512
  F/BW/DQ/VL/CD/VNNI/BF16, FMA, F16C and BMI sets; FP compare predicates 0-31 enumerated) compiled by clang-cl
  23.1.3, a hand-written GPR/x87/prefix file, and the four `smoke.c` objects: 26,553 instructions, 982
  distinct XED iclasses (320 FP-sensitive), 0 iclass disagreements. The single length disagreement is a
  linear sweep through an MSVC jump table (data), which the census never decodes. llvm-objdump prints some
  prefixes (`lock`) on a line of their own; the table's `merge` rows join them with the next line.

**Independent re-derivation.**
- A separate agent context, labelled *same-family, independent-context* in §12 until D0-10 names
  other families, receives only: this frozen record, the census objects, `fp_class.csv`,
  `loop_table.csv` and the baseline inputs.
- It writes its own script, committed under `experiments/x0-census/rederive/`. The script must
  independently:
  - locate the 18 variant symbols and their ranges from the object symbol tables, using its own
    range and closure logic, starting from `llvm-objdump --disassemble-symbols` rather than from
    the census script's output;
  - compute the §4.2 closure;
  - decode with XED;
  - recompute P1 to P5, |B_iform|, T_forms and P5_opclass.
- Every figure must match exactly. A mismatch fails validity check V3 (§8).
- The procedure (inputs, tools, the `figures.json` format, and how "match" and the `rederivation` field of
  `census.json` are decided) is fixed in `experiments/x0-census/rederive/PROCEDURE.md` [x0prep, 2026-10-16].
  Under the Owner's D0-10 answer (relayed above) the only other family is the local Qwen3 pilot run through
  Hearth; whether it can carry a re-derivation is not established, so the re-derivation is planned as
  same-family, independent-context, and labelled so.

**Gatekeeper.** `judge.py` computes `verdict.json` from `census.json` and the frozen inputs. Agents may
run it. They never judge (ROADMAP §1 rule 3).

## 8. Outcomes

ROADMAP §3.1 gives X0 a gate, an amber band and a narrowing, but no kill. Here they are, made
operational. Every state has an outcome (ROADMAP §1 rule 2).

**Evaluation order** (`judge.py`; input `census.json`; output `verdict.json`):

1. **V, validity.** All four checks must hold:
   - V1: no tooling-class P1 gap in any main-union configuration;
   - V2: no unresolved cross-decoder disagreement involving an FP-sensitive iclass;
   - V3: the independent re-derivation matches exactly;
   - V4: the hashes of the frozen inputs (Appendix D) match the ones the scripts used.

   If V fails, the *Tooling failure* row applies.
2. The rows **C** (coverage), **B** (flag defect) and **A** (table size) are then evaluated
   independently. Any number of them may hold, and the verdict lists all that do.
3. **P, pass,** holds if V holds and none of C, B and A holds.
4. **N, narrowing,** is evaluated at week 6 and appended to the verdict (below).

| Outcome | Condition | Action |
|---|---|---|
| **Tooling failure** (not a scientific outcome) | V fails | Fix the tooling and re-run. Log every fix with a before/after table of every P1 to P5 value. Keep and report every run's `census.json`. **The fixing is bounded:** if V still fails at the end of M0 week 3 (2026-11-12 on PLAN.md's calendar) [target], the failures are resolved conservatively and evaluation continues: (i) a variant with a tooling gap counts as a genuine gap: Amber (c) under A or D, row N1 under B-cmake or C; (ii) an unresolved disagreement counts both iclasses, counts the instruction as FP-sensitive, and flags the variant under P2 or P3 if either reading is FMA-class or an approximation; (iii) where the re-derivation disagrees, the figure less favourable to Pass is used: the larger U, the larger P5, and flagged if either side flags |
| **Amber (c): coverage** | A genuine P1 gap under A or D | Reported. The uncovered variants are `tested` and are not dispatched in release (DR-008). A re-run after a fix, under a post-data amendment, may restore coverage before the M0 verdict (week 6). Otherwise this result is final |
| **Amber (b): flag defect** | P2 > 0 or P3 flagged under any main-union configuration (A, A-ninja, B-cmake, C, D), all built with Hearth's own flags | Write a flag-defect report to `experiments/x0-census/results/flag_defect_<config>.md`. The report is mandatory; filing it upstream is the Owner's call (D0_BRIEF HM-9). That configuration's variants cannot become `validated` until the flags are fixed and the configuration is censused again under a post-data amendment. If the configuration is A or D and no passing re-run exists by the M0 verdict (week 6), the affected variants drop to `tested` and are not dispatched in release (DR-008). That is the narrowed claim. For B-cmake or C, the bar on `validated` simply stays in place, and neither is a shipping compiler (04 §8.1). In every case this amber is final at the M0 verdict, and the record lists the variants still barred. Whether a defect only in B-cmake or C should make X0 amber is OQ-4. Until it is answered, it does, under the strict reading of "No FP contraction or reassociation appears under the strict flags" |
| **Amber (a): table size** | \|U_all\| > 2·T_forms, **or** P5_iclass > 20 [target, ROADMAP §3.1: "more than 20 mnemonics are FP-sensitive", with mnemonic = XED iclass per §4.3] | The table covers only the release configurations A and D. Variants built by other compilers drop to `tested` and are not dispatched in release (DR-008) |
| **Pass** | V holds, and none of Amber (a), (b) or (c) holds | The census union sets X2's table scope (DR-008). Pass certifies three things: P1 is complete under A and D; there is no contraction anywhere in the union; and P3(a) to (d) detected no reassociation. It does **not** establish that the emitted objects are free of reassociation. That question goes to the B1.5 object audit as an open item (OQ-3) |
| **Narrowing** (judged at week 6, jointly with X2) | At X2's week-6 verdict, at least one *hot-kernel loop* carries a §4.7 tag that is not in the `proved_loop_shapes` field of X2's `verdict.json`. A hot-kernel loop is any natural loop in the closure of the 18 variants under A or D, identified in `census.json` by (config, variant, loop id). A loop tagged *other* counts as covered only if X2 lists that loop's id. If X2's `verdict.json` has no such field at week 6, the narrowing holds | The object audit (B1.5) is deferred. T1 runs at intrinsic or KIR level only. The C compiler stays trusted for kernels, and B1's first item narrows (ROADMAP §3.1, §4). The narrowing is appended to X0's earlier verdict and does not revoke it. The final record carries both |

The `proved_loop_shapes` field is a request to X2's record, which this record cannot impose. Until
X2's record adopts the field, with §4.7's tag vocabulary, the default above applies.

Rows outside the gate. They change no verdict.

| Row | Condition | Action |
|---|---|---|
| N1 | A genuine P1 gap under B-cmake or C | The union is reported as a lower bound for that configuration. Its uncovered variants are `tested` |
| N2 | A non-release configuration fails to compile a census file with Hearth's own flags | A build-defect draft goes to `experiments/x0-census/results/build_defect_<config>.md`. The variants are missing from P4 and P5, as in row N1 |

**Exhaustiveness, made explicit before freeze** (x0prep, revised after the §12 review; `judge.py` implements
exactly this list. Its unit tests, `scripts/tests/test_judge.py`, exercise each branch on synthetic
`census.json` inputs, including the reviewer's adversarial cases [M, 56 tests, laptop, 2026-10-16]):
0. *Schema.* A `census.json` that does not have the Appendix C shape `judge.py` reads gives `tooling_failure`,
   with the violations listed. Examples: a variant or build record without `build_index` 1 or 2, or a field of
   the wrong type. This cannot be resolved conservatively, even after the week-3 bound.
1. *Completeness first.*
   - Each main-union configuration and A-ninja must list all 18 variants for build 1 and build 2 (§6), and a
     build record for every census file and build.
   - Each must carry a P3(a) result `{a1: [...], a2: [...]}` for every census file.
   - Each present variant of a compiled file needs a coverage block, a resolved slot (or a genuine gap saying
     why not), and a non-empty counted set.
   - Anything missing is a tooling gap `other` (V1). So is a variant record of an unexpected (table, slot), or a
     duplicate.
2. *Compile outcomes* follow the compile rule of §5 P1, including the compiler pin of every build.
   - A genuine `compile_failed` under A or D is Amber (c). Under B-cmake, C or A-ninja it is rows N1 and N2.
   - Amber (b) is still evaluated on that configuration's effective flags (P3(a) per configuration and file).
     So B-cmake can be Amber (b) with `quant_avx512.c` uncompiled.
   - A tooling compile failure fails V1.
3. *A-ninja.* The A versus A-ninja comparison is required.
   - Every A-ninja variant carries `ab_compare` (`identical` or `differs`), with `union_member` true exactly
     when it differs. An absent A-ninja configuration, a missing or inconsistent comparison, and an A-ninja
     tooling compile failure fail V1. Such a variant joins the union, so its gap counts.
   - Otherwise A-ninja joins V1, V2, P2 and P3(b) to (d) only through variants marked `union_member`. Its P3(a)
     flags count per configuration, as for every configuration. Its genuine gaps are row N1, its compile
     failures row N2, and it never contributes to Amber (c).
4. *Validity after the week-3 bound.* Resolutions (i) to (iii) apply to V1, V2 and V3.
   - Under (i), a missing P3(a) result counts as a P3(a) flag of that configuration.
   - Under (iii), a variant is flagged if the re-derivation flags it, meaning P2 > 0, P3(b), P3(c) or d1 other
     than `pass` on the re-derivation side. Every gap cause the re-derivation reports is added to the variant
     as a genuine gap.
   - Some failures cannot be resolved conservatively: a V4 failure (frozen inputs differ); a V3 failure because
     no re-derivation exists; a V3 mismatch whose `rederivation.figures` lack `u_all`, `p5_iclass` or, for any
     union variant, `{flagged, gap_causes}`. In those cases the verdict stays `tooling_failure` (final, no
     scientific verdict) and goes to the Owner at the M0 verdict.
   - After a conservative resolution, Pass holds if none of Amber (a), (b), (c) holds; `conservative_resolution`
     is then true in `verdict.json`.
   - The evaluation date is not the caller's choice. It is the later of the system's UTC date and the date of
     the latest census run in `census.json`, and both are written into `verdict.json`.
5. *Unknown cause codes* in `census.json` are rewritten in place to tooling gaps `other`, keeping the original
   code. After the bound they therefore count as genuine under (i).
6. *Recomputed, not trusted.* Amber (a), P2 and P3(b) are recomputed by `judge.py` from the variants' iform and
   iclass sets and `fp_class.csv`. V2's FP-sensitivity is recomputed from both readings of each disagreement.
   A difference from `census.json`'s own metrics is noted, and the recomputation is used.
7. *V4* covers the class files (including `xed_tables.tsv`), the XML pin, the compiler pins and every census
   script listed in `class/frozen_inputs.json` "scripts". For the scripts, the hashes on disk and
   `census.json`'s `record.scripts_sha256` must both equal the pins.
8. *Narrowing* (week 6): if X2's `verdict.json` lacks `proved_loop_shapes`, every hot-kernel loop is uncovered
   and the narrowing holds. Loops with unchecked tags (§4.7) are covered only by loop id. A loop with no tags is
   uncovered, and a compiled variant under A or D without a loop analysis contributes an uncovered entry.
9. *Added by the x0final revision (independent review of 2026-10-16/17; all stricter; `judge.py`, 66 unit tests
   including the reviewer's adversarial cases) [M, laptop, 2026-10-17]:*
   - the compile rule's *success* needs `compiler_ran`, `argv_matches_frozen` and an object (§5 P1);
   - a variant whose slot is unresolved needs the gap `table_or_slot_absent` or `compile_failed`; any other gap
     (an `fp_trust_dep`, say) leaves it a tooling gap `other`;
   - a compiled variant needs twin attribution exact or approximate; none is a tooling gap `other` (§4.6);
   - a P3(a) result that carries an error counts as not evaluated, whatever its lists hold;
   - a cross-decoder disagreement is resolved only by a `resolution` of the form `amendment:<id>`, and the resolved
     ones are listed in `verdict.json`; any other value counts as unresolved;
   - the schema check also requires `p3.c` to be a list and `p3.d2` a list of objects with result `match`,
     `mismatch` or `unchecked`, and fails when the latest census run is dated after the system's UTC date (a forged
     run date could otherwise move the evaluation date past the week-3 bound);
   - V4 requires, for a census record (`record.id` X0-census), the 40-hex freeze commit that `x0_driver.py init`
     took from a clean git checkout whose record reads FROZEN at HEAD (`git status --porcelain` empty for
     `experiments/x0-census` and this record; every pinned script on disk equal to its pin); a `record.id` other than
     X0-census or X0-census-smoke fails V4. The runbook steps 79-82 refuse to run unless `X0` names the tree to use
     (no default copy of the scripts).
10. *Added by the pre-freeze review revision (independent review of 2026-10-17; all stricter; `judge.py` 71,
    `test_driver_guard` 12, `test_census` 3 unit tests) [M, laptop, 2026-10-17]:*
   - *The freeze point.* docs/m0/README makes the commit at which the record became FROZEN the freeze point, after which
     only an appended amendment may change it; the x0final revision took HEAD instead, so a later commit that edited the
     record body, or changed scripts together with their pins, would still have passed. `x0_driver.py init` now writes
     `freeze_commit` = the first commit in HEAD's history whose record reads FROZEN, and `run_commit` = HEAD; it refuses
     unless the record at HEAD begins byte for byte with the record at the freeze point (anything else than an appended
     amendment), and unless every path under `experiments/x0-census/class`, `scripts` or `flags` that differs between
     the two commits is named in the appended text (record §10); such a run lists them as `post_freeze_changes`. It
     also refuses ignored files there other than `__pycache__` (`git status --porcelain --ignored`: a sourceless
     `scripts/<name>.pyc` would be importable), and a Hearth tree whose HEAD is not b5d3f14 (read with git, or from
     `.git/HEAD` when git refuses a WSL-made clone). V4 requires the 40-hex `run_commit` and the change list, and
     reports the two commits in `validity_detail.v4_commits` (a run after the freeze point also gets a note).
   - *Every step runs the verified scripts.* Each `config` and `assemble` step of a census run hashes the pinned scripts
     of its own tree and refuses unless they equal `run.json`'s (init's) and `class/frozen_inputs.json`'s; on Windows it
     also refuses unless the checkout is still at `run_commit` with the record FROZEN (WSL has no such re-check; the
     pins identify the code); `config` re-checks the Hearth blobs and refuses `--frozen-db` and `--design-time`, which
     would replace the frozen captures. `config.json` records the hashes; V4 requires every configuration's hashes in
     `census.json` to equal `record.scripts_sha256`.
   - *Commits come from init only.* In a census run `x0_driver.py assemble` and `x0_census.py` refuse `--freeze-commit`
     and `--scripts-commit` (before, a typed SHA replaced init's and left only a note); runbook step 82 no longer offers
     them.
   - *Source pin in V4.* A census record needs `hearth_commit` b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220 and every
     `source_blobs` entry ok.
   - *Record id.* `verdict.json` "record" is `census.json`'s `record.id` (before: always X0-census, so a smoke verdict
     was labelled as the census verdict).
   - *Header environment* in the compile rule (§5 P1) and header pins required by V4.
   - *Canary report and caveat* (§5 P3(d)): "canaries" with the E6 label, the label on Amber (b) entries with d1 or d2
     flags, and "caveats".

**Expectations registered before data** [inference, from reading the source and the flags; none of
them measured]:
- **E1.** P3(a1) flags B-cmake (§3), so Amber (b) holds under the strict reading. *Confirmed on flags
  before freeze* [M, x0prep]: P3(a1) matches B-cmake's effective flags for all three files; this needs no
  object.
- **E2.** B-cmake fails to compile `quant_avx512.c` (row N2). The previous draft planned a pre-freeze smoke
  test of the Hearth file; x0prep removed it (§2). What is known before freeze is a probe result [M, tooling
  track]: `_mm512_dpbusd_epi32` does not compile under B-cmake's exact `quant_avx512.c` command. Whether the
  Hearth file compiles is census data; either way the decision list covers it (rows N1, N2; Amber (b) on
  flags).
- **E3.** P5_iclass > 20.
  - G02's "about ten" grouped entries become 11 iclasses when written as the VEX/EVEX forms the SIMD
    files emit [D: G02 §1's list → VADDPS, VADDSS, VMULPS, VMULSS, VMAXPS, VMAXSS, VMINPS, VCMPPS,
    VCVTDQ2PS, VCVTPS2DQ, VCVTPH2PS].
  - `quant.c`, built without ISA flags, adds legacy-SSE scalar iclasses such as ADDSS, MULSS, DIVSS,
    UCOMISS or COMISS, CVTSI2SS and CVTTSS2SI [inference].
  - Scalar code in the AVX files adds VEX scalar iclasses such as VDIVSS and VUCOMISS [inference].
  - Amber (a) is therefore plausible through P5.
- **E4.** Under the full-union reading, \|U_all\| > 2·T_forms is plausible, because GPR, control-flow,
  memory-operand and hardening iforms all count.
- **E5.** Under config C, `mm_float_scalar` calls `hx_row_bytes` (quant.c:369) through an
  interposable call, because GCC treats default-visibility globals as interposable under `-fPIC`.
  Variants with local arrays carry stack-protector code.
- **E6 (added by the x0final revision; outcome indicated before freeze by a verbatim copy).** P3(d1) passes and every
  P3(d2) `tree16` site matches in A, A-ninja, C and D (B-cmake: the `quant_avx2.c` sites). *Indicated before freeze*
  [M, x0final, step 88 of 2026-10-17 00:26 EDT, superseded run]: the first census mock contained Hearth's own
  `tree16`, `canon4` and `q_rint` text (§2 disclosure), and under the frozen flag logic it gave d1 `pass` everywhere
  and all 66 `tree16` sites `match`. As with E1, this was seen before freeze; unlike E1, it was seen on Hearth's code
  inside a mock rather than on flags. Hearth's surrounding code (the loops feeding the trees, `act_q8_scalar`) was not
  in that mock, so the indication is partial. The lead engineer ruled on 2026-10-17, before freeze, that P3(d1) and
  P3(d2) remain confirmatory, with this label on every report (§2).
  - *Widened by the pre-freeze review revision (2026-10-17).* A second, earlier source of the indication is the
    regression file `smoke_dispatch.c`, which carried Hearth's own text of the tree, of `q_rint` and of the amax loop,
    and a near copy of `dot16_conv`'s accumulation (§2 disclosure). Compiled with the frozen `quant.c` lines (the lines
    Hearth's scalar kernels get), its `dot16_conv`-shaped and amax loops gave no P3(c) flag in any configuration and d1
    `pass` everywhere; the P3(c) flags of that run were all in the object compiled with the `quant_avx512.c` lines
    (Clang's vectorised tail loop, B-cmake and D, 12 variants each) [M, x0final revision, R1 run
    `smoke-20261017T055241Z`, `scripts/smoke/results/x0final_rev/R1reg_summary.json`, read by the reviser]. The
    expectation registered here: **P3(c) flags no loop of the scalar F32, F16, BF16 and act variants** under any
    main-union configuration [inference from that indication; Hearth's `dot16_conv` also converts F16 and BF16 inputs
    inside the loop, which the smoke file does not]. Every report of those P3(c) results carries the E6 label (§2,
    `judge.py` "canaries"). Two §4.7 rules were tuned on flags of this text before freeze (§2); the label discloses it,
    and whether more is needed is the lead engineer's call.
  - *Desktop re-run (2026-10-17), disclosure.* A third §4.7 rule, the dependency-breaking idioms, was made on P3(c)
    flags of the first re-run: the census mock's loops (not Hearth text since the x0final revision's rewrite), among
    them its scalar and AVX2 act loops, whose amax shape is the scalar act variant's, and `smoke_dispatch.c`'s `sd_q8`
    row loop (not one of its Hearth runs; its rewritten amax loop was not flagged in either run) [M, §7]. So the scalar
    act variant's P3(c) outcome on Hearth again concerns a shape a rule was tuned on before freeze. The rule removes
    only reads of a zeroed register, which carry no value, so it cannot hide a split; the expectation above is
    unchanged, and the label covers it.

## 9. Threats to validity

- **Function boundaries and data in code.** Recursive descent, relocation-based slot mapping,
  COMDAT ranges checked against `.pdata`, and relocation-marked data (§4.2). The linear-sweep
  cross-check and the orphan-byte report make mistakes visible.
- **Inlining and interposition.** The closure includes internal and interposable callees. Lift
  blockers report the calls themselves, which 04 §7.2 treats as lift failures.
- **Debug info changing codegen.** The twin is used only for attribution. Identity requires equal
  bytes and equal relocations (§4.6). An unattributed loop falls back to a mechanical bound (P3(c)).
- **Classification bias.** `fp_class.csv` is written and reviewed before any Hearth object exists.
  Disagreements and missing iclasses default to FP-sensitive (§4.4).
- **Baseline drift.** B_iform is frozen before data, and T_forms is capped at 105 (§4.5).
- **Unit choice.** P4 and P5 use the stricter readings (OQ-1, OQ-2). The secondary metrics report
  the coarser units beside them, so the effect of the choice is visible.
- **Generator choice.** A uses the shipping Visual Studio path. A-ninja is the cross-check (§2).
- **Implicit compiler defaults** such as Ubuntu GCC's hardening flags, MSVC `/GS` and header
  versions [inference]. Effective flags and header versions are pinned (Table 2.1), and hardening
  code is expected and classified (§4.2). Since the pre-freeze review revision `judge.py` compares the recorded header
  environment with its pins (§5 P1); before, it was recorded and never compared.
- **Forking paths through tooling fixes.** Every run is kept with before/after tables, and fixing is
  bounded at week 3 (§8).
- **Same-family review and re-derivation.** Both are labelled as such. That is weaker than ROADMAP's
  different-family requirement (README, Independence).
- **XED names unverified.** The attribute, extension and exception-class names are checked against
  the pinned XED before freeze (§4.3, §4.4). *Done by x0prep; substitutes recorded in §4.4.*
- **Classifier reasons are templates.** The `reason` column of `fp_class.csv` names the source page and the
  template of the rule that fired. It is not a per-instruction SDM citation, and it was written without
  re-reading the SDM in this session [inference] (§4.4). The XED cross-check and the "disagreement means
  FP-sensitive" rule bound the damage. The §12 review re-classified a sample of 197 iclasses blind and found no
  difference in `fp_sensitive`.
- **Heuristics in the closure and loop scripts.** Jump-table recognition, import-pointer calls, the no-return
  inference, the d1 constant tracker and the carried-value data-flow are deterministic but heuristic.
  - Since the §12 review the closure accepts only the recognised shapes of §4.2, with the table's extent taken
    from its guarding bound. Anything else is `unresolved_indirect` (tooling). The remaining risk is
    therefore a tooling gap on a legitimate shape, which V1 makes visible, rather than a silent miss.
  - Each other failure mode is conservative where possible: canary not found -> flagged; unknown external ->
    FP trust dependency.
  - Known residuals: a base or index register passed through the stack (not followed) gives a tooling gap. A
    mid-function call to an external no-return function that is on no list falls through, so the bytes after
    it are over-counted.
  - The independent re-derivation (V3) checks the figures.
- **Limits of the tracker and of attribution.** Sites outside the whitelist are *unchecked* and loops
  without exact attribution are *unattributed*. Both are listed for X2 and B1.5, not hidden. Since the x0final
  revision, attribution *none* is a tooling gap (V1) rather than a silent fallback, and the stricter source-loop rule
  of §4.7 may produce a false P3(c) flag on an emitted loop whose header block starts inside a real inner loop; every
  loop decided by that rule is listed in `census.json` notes.
- **Accumulator counting (x0final revision).** §4.7's taint and cycle rules count true splits that the earlier rule
  missed (the reviewer's six shapes). Two over-counts they introduced on real GCC output of the regression set were
  removed before data by the data-operand and opmask precisions and the enclosing-loop rule (§4.7, Appendix E). Other
  over-counts on Hearth objects would show as P3(c) flags with their partial-result cycles listed per loop. The
  pre-freeze review revision broadened "reads a loop-carried value" to any data-operand path and added the SSE2 select
  form and the must-analysis of (b), all in the counting direction; the unit cases show no new count on the shapes that
  caused earlier false flags, but its effect on real compiler output is known only from the pending desktop re-run (§7).
  *Desktop re-run (2026-10-17):* on real MSVC, clang-cl, GCC and Clang output the broader reading over-counted through
  dependency-breaking idioms (a zeroed register read as data); the idiom rule of §4.7 removed all 50 such flags, and
  the final run flags only what the x0final revision's run flagged (§7). Other over-counts of the same kind on Hearth
  objects (an instruction that ignores a source's value but is not on the idiom list) would show as P3(c) flags with
  their partial-result cycles listed per loop.
  The source-loop rule now takes the smaller bound for unrelated loops and the inner bound under the mirror test, which
  can raise a false flag where debug lines mislead; the notes list every such loop.
- **Pre-freeze exposure through the mock (x0final revision).** Hearth's own helper text was compiled before freeze
  inside the first census mock (§2 disclosure, E6). The shingle guard now prevents a repeat for exact runs of three
  lines or more (two since the pre-freeze review revision, next item); a paraphrase of Hearth code would pass it, so
  smoke inputs stay subject to review.
- **Pre-freeze exposure through the regression set (pre-freeze review revision).** `smoke_dispatch.c` carried Hearth's
  tree, `q_rint` and amax lines, and two §4.7 rules were tuned on P3(c) flags of that text, so the P3(c) outcomes of
  the scalar F32, F16, BF16 and act variants were indicated before freeze (§2, E6); they carry the E6 label. The guard
  now refuses any shared pair of lines with comments stripped (outside 13 allow-listed dispatch-table declarations) in
  every C source and header of a smoke step's directories. Single shared lines, near copies and paraphrases still pass
  it, and the canary shapes themselves (the record's (v + M) − M and s = 8, 4, 2, 1 tree, and the amax loop the smoke
  file keeps) still yield the same compiled code whatever their text; the guard cannot remove that, the label reports
  it.
- **Pre-freeze configure runs.** Disclosed in §2; OQ-7.
- **One host.** §6 tests repeatability on the desktop only.

## 10. Deviation and re-run policy

- **Tooling fixes.** A tooling fix may be followed by a re-run. The fix is logged with a before/after
  table of every P1 to P5 value, every run is kept, and the bound of §8 applies.
- **Amendments.** A change to a unit, a threshold or the configuration set after collection has begun
  is an amendment marked *post-data*. Verdicts are then reported under both the original and the
  amended rule. The same holds for an Owner answer to an OQ that changes a gate reading after
  collection has begun.
- **New configurations.** A configuration may be added (for example GCC 14) as a secondary arm, which
  cannot change the verdict. A flag defect found in any secondary arm still gets the mandatory report
  of Amber (b), without affecting the verdict.
- **Fixed flags.** Re-censusing a configuration after Hearth fixes its flags is a post-data amendment
  under Amber (b).

## 11. Deliverables

- `experiments/x0-census/results/census.json`, the census ledger record (schema in Appendix C), and
  `verdict.json`, written by `judge.py`.
- `experiments/x0-census/REPORT.md`. It contains:
  - the delta against B_iform, with the reconciliation against G02;
  - the loop-correspondence patterns T1 must handle, in the tag vocabulary of §4.7;
  - flag-defect and build-defect drafts;
  - the proxy-fidelity table for X3;
  - every number tagged.
- The census union, which becomes the scope list for X2's semantics table. The S-helpers iclasses
  are attached to it as a marked addendum.
- `experiments/x0-census/rederive/`, with the re-derivation's script and outputs.

## 12. Review log

| Date | Reviewer (lens) | Family | Scope | Findings by severity | Outcome |
|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 (codegen and extraction mechanics: toolchains, object formats, ISA semantics) [G: lens inferred from the findings] | Claude (same family as author; independent context) | DRAFT of 2026-10-16 | 17: 0 blocker, 10 major, 7 minor | 17 accepted, 2 of them with a sub-point rejected; 0 rejected outright |
| 2026-10-16 | Reviewer 2 (pre-registration integrity: threshold units, forking paths, outcome exhaustiveness, provenance) [G: lens inferred from the findings] | Claude (same family as author; independent context) | DRAFT of 2026-10-16 | 17: 3 blocker, 9 major, 5 minor | 17 accepted, 3 of them with a sub-point rejected; 0 rejected outright |
| 2026-10-16 | x0prep review, reviewer 1 (Gatekeeper and pre-freeze artefacts: adversarial `judge.py` tests on synthetic `census.json`; independent re-derivation of §4.5; blind sampled re-classification of §4.4; read-only desktop scan for D12) | Claude, same family, independent context | DRAFT with Appendix E (x0prep), `judge.py`, `class/`, D12 | 15: 0 blocker, 7 major, 8 minor | 15 accepted (one resolved by the alternative the finding offered); 0 rejected |
| 2026-10-16 | x0prep review, reviewer 2 (closure and decode soundness on adversarial NON-Hearth objects compiled with each configuration's exact lines: jump tables, cold parts, indirect calls, no-return, order dependence, data in code) | Claude, same family, independent context | `x0_extract.py`, `x0_decode.py`, §4.2 text, the smoke validation claim | 13: 2 blocker, 4 major, 7 minor | 13 accepted, 2 of them with a sub-point rejected; 0 rejected outright |
| 2026-10-16/17 | x0final review, reviewer 1 (pre-freeze artefacts and classification semantics: blind re-classification of 945 iclasses for D5; independent re-derivation of D6 from the b5d3f14 blobs and the XML) [G: lens inferred from the findings] | Claude, same family, independent context | `class/fp_class.csv`, `B_iform.json`, `hand_map.csv`, §4.4, Appendix D | 3: 0 blocker, 0 major, 3 minor | 3 accepted (documentation only; no CSV or JSON changed, so no hash changed); 0 rejected |
| 2026-10-16/17 | x0final review, reviewer 2 (pre-registration integrity and tooling soundness of the x0final additions: provenance of the census mock, the Gatekeeper's compile rule and weak checks, A's argv check, the P3(c) accumulator and source-loop rules, twin attribution, V4 traceability, MSBuild failure handling; adversarial `judge.py` and loop inputs; desktop experiments on a NON-Hearth `rvx.c`) [G: lens inferred from the findings] | Claude, same family, independent context | x0final scripts, the census mock, runbook 79-88, record §2, §4.2, §4.6, §4.7, §5, §8 | 11: 1 blocker, 6 major, 4 minor | 11 accepted: 1 with a sub-point deferred, 1 changed in part (a rule added so the proposed fix does not raise a measured false flag); 0 rejected (below) |
| 2026-10-17 | Pre-freeze review (the x0final revision's changes and the lead engineer's OQ-6 and ruling edits: adversarial synthetic loop streams A1-A9 against the pinned `x0_loops.py`; freeze-point and pin traceability through init, config, assemble and V4; the smoke sources against the read-only clone; the header environment; the authorisation text) [G: lens inferred from the findings] | Claude, same family, independent context | `x0_loops.py`, `x0_driver.py`, `x0_census.py`, `judge.py`, runbook 79-82, `smoke_dispatch.c` and the mock, record header, §2, §4.7, §5, §8, §12, Appendices A and E, `FREEZE.md` | 11: 0 blocker, 5 major, 6 minor | 11 accepted: 3 changed in part (below); 0 rejected |

Per-reviewer counts are the reviser's count of the findings relayed on 2026-10-16 [M, reviser].
Totals: 34 findings (3 blocker, 19 major, 12 minor); 34 accepted, 5 of them only in part; 0 rejected
outright [D: sums of the first two rows]. Each accepted finding of those two reviews was checked against the
Hearth clone at b5d3f14, the repository docs and `experiments/x0-census/flags/` before it was applied.
x0prep review totals: 28 findings (2 blocker, 11 major, 15 minor). All 28 were accepted: 2 with a sub-point
rejected and 1 resolved by the alternative the finding offered. None was rejected outright [D: sums of the two
x0prep rows; counts are the reviser's count of the findings relayed on 2026-10-16]. How each was checked and
handled is set out below the earlier reviews' sub-points.

Sub-points rejected in the first two reviews (one line each):
- **R1, P4 (like-for-like):** making P4's gate \|U_all^SIMD,S\| (category S in the SIMD variants) was
  rejected. It is the looser reading, which the finding itself says not to adopt without an Owner
  answer. It is kept as a secondary metric, and OQ-2 asks the question.
- **R1, outcome table, item (3):** "P2/P3 flagged only under B or C leaves the verdict unaffected"
  was rejected. ROADMAP §3.1's clause "No FP contraction or reassociation appears under the strict
  flags" names no compiler, so Amber (b) keeps every main-union configuration until OQ-4 is
  answered. The rest of the decision list was adopted.
- **R2, outcomes:** making identical build hashes part of validity check V was rejected. It
  conflicts with R2's own §6 fix (census both builds and take the union), which was adopted instead.
- **R2, P3:** "if attribution is approximate, the loop is flagged" was rejected. A debug-info
  artefact would then produce a false Hearth flag-defect report. Such loops are checked against the
  variant-wide largest source-lane count and listed as unattributed (tombstone
  `x0_unattributed_loop_flag`).
- **R2, flags:** making the Ninja objects config A's census objects was rejected. Hearth's Windows
  release and CI use the Visual Studio generator (CONTRIBUTING.md:41, ci.yml:162, ADR-0007), so those
  objects are censused as A and Ninja becomes the A-ninja cross-check, as reviewer 1 proposed
  (tombstone `x0_census_a_from_ninja`).

Corrections to reviewer evidence, none of which changed a finding's outcome:
- **R1, P4:** the finding says 35 of the 130 names are `_mm_*`. The reviser counted 32 [M, §4.5].
- **R1, analysis procedure:** the finding cites "G02 §8" for MAXPS's operand rule; the rule is in
  G02 §1.
- **R2, scope statements:** the finding names a `silu` function. `quant.c` defines `hx_swiglu` at
  lines 644-649, uses `expf` at lines 639, 647 and 651, and uses `sqrtf` at line 630.
- **R1, FP sensitivity:** the XED attribute names remain unverified, as reviewer 1 said; §4.4 requires
  checking them before freeze. *x0prep checked them against the pinned XED (§4.4).*

Pre-freeze preparation, not a review. The x0prep track (Claude, 2026-10-16) wrote `fp_class.csv`,
`B_iform.json` and `hand_map.csv`, `loop_table.csv`, `objdump_norm.csv`, `fp_flag_patterns.txt`, the
reworked scripts and `judge.py`, and changed this DRAFT (Appendix E). The two x0prep reviews of 2026-10-16
(rows above) cover:
- `fp_class.csv`: sampled, see D5;
- `B_iform.json` / `hand_map.csv`: re-derived, see D6;
- the §5 P1 and §8 decision list, through `judge.py`;
- the closure scripts;
- the D12 statement.

Status of review coverage (updated by the x0final revision, 2026-10-17):
- the x0final additions (Appendix E rows "x0final") and the §4.7 rules were reviewed on 2026-10-16/17 (rows above;
  handling below). D5 and D6 received a second blind review.
- `loop_table.csv` was cited by reviewer 2 (its nests) but not reviewed row by row; the x0prep post-review revisions
  (Appendix E rows "post-review") were exercised by reviewer 2's adversarial runs but not reviewed as such;
- the x0final revision's own changes (Appendix E rows "x0final revision") are unreviewed. Whether they need another
  independent review before freeze is the lead engineer's call. *Updated by the pre-freeze review revision
  (2026-10-17):* they, and the lead engineer's OQ-6 and ruling edits, were reviewed on 2026-10-17 (row above; handling
  below). The pre-freeze review revision's own changes (Appendix E rows "pre-freeze review") are unreviewed, and their
  effect on real compiler output awaits the desktop re-run (§7); whether they need another independent review before
  freeze is the lead engineer's call. *Updated by the desktop re-run (2026-10-17):* their effect on real compiler output
  is measured (§7); the re-run's own tooling fix (Appendix E row "desktop re-run", the §4.7 idiom rule) is unreviewed
  too and belongs to the same call.

All reviews are same-family, independent-context (README, Independence; D0-10c as recorded in OWNER-ANSWERS.md: no
other frontier family; the local Qwen3 pilot only).

**x0prep review of 2026-10-16: how each finding was handled.** Reviser: Claude, x0prep track. Every finding was
checked before it was applied.
- Findings on `judge.py` were checked by reading the version reviewed. `FREEZE.md` listed that version as
  SHA-256 `4cb2d020…`, and the reviewer found the disk bytes equal to it.
- The reviewer's scratch tests (`adv_judge.py`, `adv2.py`, 26 cases) were then run against the revised `judge.py`.
  22 pass. The other 4 fail because of the new requirements, not a defect [M, laptop]:
  - their fixture now includes A-ninja;
  - an added build record lacks the compiler hash;
  - after-bound figures are incomplete;
  - one case uses the old `error_locations` field.
  Each case behind a finding was rewritten as a unit test against the new census fields (`test_judge.py`).
- Findings on the decoder were checked against the reviewer's own outputs and disassembly of the adversarial
  objects, copied to the laptop [M, reviser, 2026-10-16].
- The D12 finding was checked by a read-only `find`/`ls` in the desktop's WSL home [M].
- After the fixes, `judge.py` passes its 56 unit tests, which include each adversarial case. Runbook step 72
  passes on all 24 regression objects (§7).

Reviewer 1 (15 findings, all accepted):
- Majors:
  - P2 is recomputed from iclasses.
  - A missing P3(a) result is a V1 gap; after the bound it counts as a flag.
  - d1 must be exactly `pass`, and `x0_loops.py` exits 1 on an unmatched canary key.
  - Unknown cause codes are rewritten in place, so they survive the conservative resolution.
  - The A versus A-ninja comparison is required (`ab_compare`, union membership, A-ninja tooling compile
    failures in V1).
  - V3 after the bound needs complete figures and adds the re-derivation's gap causes. The evaluation date is
    max(system UTC date, latest census run), and the CLI parameter is removed.
  - The coverage block, slot resolution and a non-empty counted set are required.
- Minors:
  - The compile rule checks the compiler pin and structured error locations against the census files or the
    recorded include list.
  - A schema check runs first. Unexpected and duplicate variants are gaps.
  - The narrowing treats empty tags and a missing loop analysis as uncovered.
  - V4 covers `xed_tables.tsv`, every census script and the compiler pins.
  - The approximation list is extended.
  - The `reason` column is reworded (below).
  - The D12 statement is extended.
  - This log.

Reviewer 2 (13 findings, all accepted):
- Both blockers: jump tables are tied to the jump's own address computation, with a bounded extent and no
  partial tables, and GCC cold parts belong to their parent function.
- Table extent from the guarding bound.
- Memory-operand calls through a variable are `unresolved_indirect`.
- No-return inference, with the no-return list also applied to memory and import calls.
- An order-independent, round-based descent with register families.
- An overlap gap.
- MSVC byte index tables are data.
- `.pdata` contiguity.
- Cold-part call kinds.
- The CFG dispatch pointer is removed from the allow-list.
- A slot-name warning.
- An adversarial regression set with expected outcomes (`smoke/rv_tricky*.c`, `smoke/tricky_expect.json`), so
  that step 72 fails on any deviation.

Beyond the findings, all stricter:
- The compiler pin is checked on successful builds too.
- `judge.py` also hashes the scripts on disk.
- V2's FP-sensitivity is recomputed from both readings of a disagreement. Reviewer 1's scratch test
  `test_v2_objdump_side_fp`, not among the relayed findings, showed that `judge.py` trusted the census flag.

Sub-points rejected or changed (one line each):
- **x0prep R1, `fp_class.csv` reasons:** resolved by the finding's first option, rewording §4.4 so that `reason`
  is a rule template. Per-row text was not written, because it would need the SDM re-read, which this revision
  did not do. No `fp_sensitive` value changes and the CSV hash is unchanged.
- **x0prep R2, jump-table association:** rejected only the restriction of the base-register slice to the jump's
  basic block. In loops the base is often defined outside that block [M, disassembly]: by MSVC
  (`lea rbp,[__ImageBase]` before the loop in `rv_coldsw`), by clang-cl and clang (`r14` and `r12` in
  `rv_coldsw`), and by GCC, which in `smoke_dispatch`'s `sd_q8` spills the base to `xmm4` and reloads it. The base is traced through its reaching definitions and register copies instead. The load,
  the add, the jump and the guarding bound must still sit in the jump's block.
- **x0prep R2, data in code:** rejected the generic fallback that treats any referenced non-instruction code
  address as data up to the next reachable instruction, because it would hide orphan code behind a stray
  reference. MSVC byte index tables are data with their exact bounded extent, and other such addresses are
  listed (`referenced_non_instruction`).

Corrections to reviewer evidence, none of which changed an outcome:
- **x0prep R1, D12:** the finding dates the WSL objects "2026-10-04 to 10-06". The reviser's re-check finds the
  14 quant objects dated 2026-10-04 only (11:40 and 18:53) [M].
- **x0prep R2, smoke corpus:** the four-configuration claim of the earlier validation stands for
  `smoke_dispatch.c`. Its weakness was the corpus, not the reported numbers, which the re-run reproduces except
  B and B-scalar U (§7).

**x0final review of 2026-10-16/17: how each finding was handled.** Reviser: Claude, x0final revision track (Claude,
same family, independent context from both reviewers). Every finding was checked before it was applied: the
judge and loop findings by running the reviewers' scratch inputs (`adv_judge.py`, `adv_loops.py`) against the
scripts as reviewed and again after the fix; the mock finding by comparing the mock as run with
`git show b5d3f14:` in the read-only clone; the A-argv and MSBuild findings by a NON-Hearth Visual Studio probe on
the desktop; the decoder finding by decoding the reviewer's NON-Hearth `rvx.c` objects under C before and after;
the D5/D6 findings by re-running parts of the reviewer's re-derivation and reading `fp_class.csv` [M, x0final
revision, laptop and desktop, 2026-10-17].

- x0final review, D5/D6 (reviewer 1; Claude, same family, independent context, 2026-10-16): `fp_class.csv` was
  re-classified blind on 945 iclasses (every iclass of the AVX, AVX2, AVX2GATHER, F16C, FMA, AVX512F/BW/DQ/CD and
  AVX512_VNNI ISA sets; every SSE..SSE4, MMX, BMI1 and BMI2 iclass; a seeded sample, seed 20261016, of 60 of the
  other 1,380): 0 disagreements, 296 of the 945 FP-sensitive [M, reviewer 1]. `B_iform.json` and `hand_map.csv` were
  recomputed from the b5d3f14 blobs and the XML (SHA-256 `6762a506…` on the laptop and on `D:\mithril\x0prep`): 130
  names (47/51/32), 23 with no single instruction, 1 hand-mapped xed name, |B_iform| = 102, |B_mnem| = 74, 0
  differences per intrinsic [M, reviewer 1]. The reviser re-ran the reviewer's re-derivation script against the
  pinned files: the same 130 names (47/51/32), 23 with no single instruction, 1 xed name absent from the pinned XED,
  |B_iform| 102, |B_mnem| 74, 105 XML form strings, 74 XML instruction names; and the five pinned hashes match
  [M, reviser, laptop, 2026-10-17].

Reviewer 1 (3 minor, all accepted; documentation only):
- the D5/D6 review above, also added to Appendix D;
- the FP-environment asymmetry of `fp_class.csv`, stated in §4.4 (checked: LDMXCSR, VLDMXCSR, STMXCSR and VSTMXCSR
  "yes"; FLDCW, FLDENV, FRSTOR, FNSAVE, FXRSTOR(64), XRSTOR(64), XRSTORS(64), FNSTCW and FNSTENV "no");
- op_class for PH, SH and BF16 iclasses, stated in §4.4 (checked: VFMADD231SH → FMADD231SH, VADDBF16 → ADDBF16,
  VFMADD231PS → FMADD.f32).

Reviewer 2 (11 findings, all accepted; one sub-point deferred, one fix changed in part):
- Blocker, the census mock: verified (13, 22 and 26 distinct shared lines; `tree16`, `canon4`, `red8`, `hsum_i32`,
  `q_rint`, the tree loop header, the BF16 load). Disclosed in §2 and as E6 in §8; the mock rewritten; the header
  comment and `X0_NOT_HEARTH` corrected; the shingle guard added to `x0_driver.py` (it refuses every file of the
  first mock). The first mock's runs (step 88 of 2026-10-17 00:26-00:35 EDT) are superseded and their results kept
  only as the record of what was seen.
- Major, `classify_build`: verified (an exit status 0 was "ok" whatever `argv_matches_frozen`, `compiler_ran` or
  `object_exists`); fixed and the record's *success* made stricter (§5 P1); the reviewer's two cases are unit tests.
- Major, A's argv tolerance: verified (`/Od`, `/Ob0`, `/O1`, `/GL` tolerated; multiset comparison); replaced by the
  exact delta `/O2`, in order, after measuring the build and design-time lines of a NON-Hearth VS project (§5 P1);
  unit tests for `/Od`, `/Ob0`, a missing `/O2`, `/O1`, `/GL` and a reordered `/fp` pair.
- Major, the accumulator rule: verified on the reviewer's six streams, which before the fix gave T1 (rotation) 8
  lanes against a true 16, T2 (compare and blend) 0 against 16, T3 (two FMA chains) 16 against 16, T4 (add, then
  merge blend) 0 against 32, T5 (add, then permute) 0 against 8 and T6 (copy on one path) 8 against 16 [M, reviser];
  fixed by (a) to (d) exactly as proposed (§4.7), after which all six give the true count; T1 to T6 are unit tests.
  Added by the reviser after an intermediate desktop run: the data-operand and opmask precisions (§4.7), because the
  broader taint of (a) together with the earlier treatment of address registers flagged GCC's vectorised
  quantisation loop of the regression set (no FP accumulator in the source) as 16 lanes against 0.
- Major, the outer source loop: verified (`choose_source_loop` took the outer loop with no other condition);
  conditions (i) and (ii) added as proposed, applied also to the mirror case (header in the outer loop, back edge
  in the inner one); both bounds recorded and listed (§4.7). *Changed in part:* condition (i) alone made the
  emitted s-loop of the regression set's s = 8, 4, 2, 1 tree under GCC (which keeps j-loops inside it) take the
  j-loop's bound of 0, a false flag in 12 variants of an intermediate run; the reviser added that an emitted loop
  enclosing an emitted loop of the inner source loop is the outer loop (§4.7). A residual false-flag risk of the
  stricter rule is stated there.
- Major, attribution none and whole-section identity: verified by reading `judge.py` and `x0_twin.py`. (1) attribution
  none is now a tooling gap (`x0_census.py` and `judge.py`); (2) identity per closure function, as proposed, when a
  differing section keeps its size and relocation offsets (§4.6). *Correction to the reviewer's evidence (no change
  of outcome):* in the reviewer's desktop experiment the twin's `.text` had 69 relocations against the census
  object's 67 (a source change, `-DRVX_SKEW`, not `-g` alone), so the proposed per-function rule would not have
  changed that case; it covers twins that differ only in bytes or relocation targets [M, reviewer's `attr_skew.json`,
  read by the reviser].
- Major, V4 and the freeze commit: verified (the scripts and their pins come from the same tree; `--freeze-commit`
  optional and unchecked; the runbook defaulted to the x0final scratch tree). Fixed as proposed: `x0_driver.py init`
  checks the clean git checkout and the FROZEN status line at HEAD (git is installed on the desktop:
  `C:\Program Files\Git\cmd\git.exe` [M, 2026-10-17]), writes `freeze_commit` to `run.json`, `x0_census.py` copies it
  into the record, `judge.py` V4 requires it for a census record, and steps 79-82 refuse an unset `X0`.
- Minor, MSBuild stopping at the first failed CL task: verified on the NON-Hearth probe; the single-file
  `ClCompile` fallback was measured to work on the probe, implemented in the driver and `x0_build.py`, unit-tested,
  and run end to end on a copy of the new mock with a broken `other.c` (§7).
- Minor, `judge.py`'s weak checks (a) to (d): verified with the reviewer's cases; all four fixed as proposed (§8
  item 9). (d) is enforced on the command-line path, which computes the evaluation date; a direct call of
  `judge()` with a caller-chosen date (unit tests only) bypasses it.
- Minor, the narrow bound compare: verified by decoding the reviewer's `rvx.c` objects under C before and after the
  fix (§4.2). *Sub-point deferred:* adding `rvx_vrp`-like code to the regression set (new expectations for five
  configurations and a new R1 run); the fix is validated on the reviewer's own objects instead. Open item for the
  lead engineer.
- Minor, FMA as ADD: verified (code and record disagreed); the record now states it (§4.7).

Beyond the findings: a P3(a) result that carries an error is "not evaluated" (stricter; the reviewer's scratch case
9, not among the relayed findings); the shingle guard also covers the headers next to each smoke source (stricter);
and, found by the fallback run, an error located in another source of an MSBuild CL batch, or MSBuild's own MSB6006
line, is no longer counted against a census file whose object the batch produced (precision: in the first fallback
run, 01:38 EDT, `quant.c` got rc 1 with `other.c`'s error, which the compile rule would have made a tooling `other`; the
final fallback run gives rc 0 with no error of its own) [M, x0final revision, desktop; the final run's records in
`runbook/logs/x0final_rev_fallback.log`].
Totals of the x0final review: 14 findings (1 blocker, 6 major, 7 minor), 14 accepted (1 with a sub-point deferred, 1
fix changed in part), 0 rejected [D: sums of the two x0final rows].

**Pre-freeze review of 2026-10-17: how each finding was handled.** Reviser: Claude, pre-freeze review revision track
(same family, independent context from the reviewer), laptop only: the desktop's 23:00-07:00 PT quiet window was kept,
nothing was compiled or decoded, no git command was run. Every finding was checked before it was applied: the loop
findings by running the reviewer's synthetic streams (scratch `adv_pfr.py`) against the pinned `x0_loops.py` (SHA-256
`3e8e1ab3…`, reconstructed byte for byte from the reviewer's scratch copy by reversing its two-line patch) and against
the revised one; the driver, assembler and judge findings by reading the code as pinned and by unit tests with git
stubbed; the guard finding by an overlap scan of every smoke source against the read-only clone's seven pinned files
(blob hashes verified in Python); the header finding by reading `OWNER-ANSWERS.md`, `OWNER-QUEUE.md` and docs/m0/README;
the header-environment finding by reading the x0final revision run's `config.json` copies on the laptop [M, reviser,
laptop, 2026-10-17]. After the fixes all 179 unit tests pass (71 `test_judge`, 7 `test_flags`, 17 `test_loops`, 27
`test_loops_x0final`, 16 `test_loops_prefreeze`, 14 `test_build`, 12 `test_twin`, 3 `test_census`, 12
`test_driver_guard`) and `pin_inputs.py` reports 0 differences after re-pinning [M, laptop, 2026-10-17].

- Major, accumulators read only through moves (§4.7): verified, A1 0, A2 0, A3 0, A6 0, A9 0 against true 2, 8, 16, 16,
  8. Fixed as proposed (DEP-based reads; MOVD/VMOVD as moves; compare-select through origins) and the streams are unit
  tests; after the fix 2, 8, 16, 16, 8. *Correction to the evidence (no change of outcome):* the reviewer's prototype
  gives A1 = 2 without the MOVD change; MOVD was added for the record's wording. The desktop re-run of step 88 and the
  regression replay that the finding asks for is pending (§7).
- Major, the freeze point (§8 item 10): verified (`freeze_checkout` returned HEAD; `git status` without `--ignored`).
  Fixed as proposed: freeze point and run commit recorded separately, the record must be the freeze point's plus an
  appended amendment, changed class/scripts/flags paths must be named by it, ignored files refused, V4 surfaces both
  commits. *Changed in part:* `__pycache__` directories are tolerated (Python writes them on every run; their bytecode
  is used only when its source stamp matches), and `flags/` is covered too (its captures decide `argv_matches_frozen`).
- Major, config and assemble not checking the pins: verified by reading `cmd_config`, `cmd_assemble` and
  `x0_census.py`. Fixed as proposed (per-step re-check of the scripts against `run.json` and the pins, HEAD and FROZEN
  on Windows, Hearth blobs at config time, hashes in `config.json`, V4 per configuration). Beyond the finding:
  `--frozen-db` and `--design-time`, which replace the frozen captures, are refused in a census run.
- Major, `smoke_dispatch.c` carried Hearth lines (§2, E6, §9): verified. *Correction to the evidence:* with comments
  stripped the file shares 14 lines longer than 25 characters and 3 pairs, the third being the amax loop body
  (quant.c:330-331, two shorter lines); the reviewer counted 11 and 2. Disclosed; the E6 label widened to the P3(c)
  results of the scalar F32, F16, BF16 and act variants; the guard strengthened with the reviewer's k = 2 option, comment
  stripping, every `.c`/`.h` of the source and include directories, UTF-8 only, and a 13-line structural allow-list
  recorded in §2 (single shared lines are not refused, since generic loop headers recur in any C file). Beyond the
  finding: the three runs of `smoke_dispatch.c` were rewritten (same semantics and line numbers), because the stricter
  guard refuses the file as it was and the regression replay must still run.
- Major, the header's authorisation text: verified (line 6, the $1.5k sentence, "do not answer it formally", Appendix
  A). Fixed as proposed: both parts of OQ-6 answered, pending ratification at sitting 1; the verbatim answers tagged [M];
  "he confirmed" tagged as the lead engineer's reading [G]; the superseded sentences kept only as history. The reviewer
  disclosed one read-only `git diff` of the record at the start of its review, before applying the no-git rule; it is
  recorded here as a deviation of the review process, with no effect on a finding.
- Minor, the ruling's surroundings: verified. Fixed as proposed: the ruling's last sentences reworded (a loosening after
  data is a post-data amendment reported both ways), ROADMAP §1 rule 1 quoted, the label written by `judge.py`, Appendix
  E rows for the lead engineer's header and §2/§8 edits, `FREEZE.md` items 1 and 4, and this row.
- Minor, `--freeze-commit`, the verdict's record id, the source pin: verified. Fixed as proposed.
- Minor, the source-loop rule (§4.7): verified, A7 (k.c:82, outer) and A8 (k.c:60, latch). *Changed in part:* the
  mirror test as proposed (rule `inner`); nesting through the inline stack enters the full nest rules rather than `min`
  alone, because `min` alone would check `qtile16`'s 128-lane g-loop against 0 whenever its header line came from the
  inlined `q16_unpack` loop (trip count 4); truly unrelated loops get `min` as proposed. A7 and A8 are unit tests.
- Minor, the SSE2 select and the merge on a swap: verified, A5 0 (true 8) and A4 8 with V0 and V1 merged (true 16). The
  SSE2 idiom is now a compare-select. *Changed in part:* the proposed condition "equal DEP origins at every latch" does
  not separate A4 (both locations carry the origins {V0, V1} at the latch); a must-analysis of equal provenance on every
  path is used instead, which keeps a register and its spill copy, and the two halves of A3, one partial result. A4 and
  A5 are unit tests.
- Minor, the header environment: verified (nothing compared `config.json` "headers"). Fixed as proposed: header pins in
  `class/frozen_inputs.json` from Table 2.1, compared by `judge.py` in the compile rule, required by V4; unit tests.
  Found while checking: D's resource-dir tree was recorded as null in the x0final revision's run, because the driver
  passed clang-cl's `/clang:` form to `clang`; fixed, confirmation pending on the desktop.
- Minor, d2 possibly vacuous: verified (no count of unchecked sites in `verdict.json`). Fixed as proposed: per
  configuration d2 counts under the E6 label, and the "every expected site unchecked under A or D" caveat registered in
  §5 before data.
Totals of the pre-freeze review: 11 findings (0 blocker, 5 major, 6 minor), 11 accepted (3 changed in part), 0 rejected
[D: count of the row above].

**Desktop re-run of 2026-10-17 (the items left pending above).** Claude, re-run track; desktop for the runs and the
git checks, laptop for the analysis and the edits. The regression replay and the mock run of step 88 were made twice
(§7): with the pinned scripts, which raised 50 false P3(c) flags through dependency-breaking idioms (the accumulator
finding's DEP reading on real output), and after one pre-freeze tooling fix (§4.7 idiom rule, Appendix E), with the
x0final revision's P3(c) outcomes exactly. D's resource-dir tree is recorded and equals its pin (the header finding).
The freeze-point logic (the freeze-point finding) ran against a throwaway repository with real git on the desktop: 16
of 16 scenarios accepted or refused as intended (§7). After the fix 183 unit tests pass (20 `test_loops_prefreeze`,
the rest as listed above) and `pin_inputs.py` reports 0 differences after re-pinning [M, laptop and desktop,
2026-10-17]. The fix is not independently reviewed.

## 13. Signature block

```text
Owner: ______________________   Date: __________
Signs the record frozen at commit: ________
Answers to OQ-1 … OQ-7 (Appendix A), or "deferred": ______________________________
T_forms: [ ] min(|B_iform|, 105) as registered   [ ] accept recomputed |B_iform| = ____ (OQ-5)
```

---

## Appendix A. Owner questions

The record gates on the strict reading in each case below. An answer that loosens a gate before
freeze needs a ROADMAP amendment first, because this record cannot change ROADMAP. After data, it
needs a post-data amendment, with the verdict reported both ways.

- **OQ-1, the unit of P5.** ROADMAP §3.1 says "more than 20 mnemonics are FP-sensitive", and this
  record reads mnemonic as XED iclass. G02's "about ten" used grouped entries such as "(V)ADDPS/SS",
  which are closer to §4.4's op_class. Did ROADMAP intend grouped operation classes? If so, ROADMAP
  §3.1 must be amended to say so before this record is signed.
- **OQ-2, the union in amber (a).** Is "the union" every reachable instruction of every variant
  (P4 = \|U_all\|, what this record gates on)? Or is it a like-for-like comparison with the
  intrinsic-implied forms (\|U_all^SIMD,S\|)? The full reading makes amber (a)
  plausible on GPR, memory-operand and hardening forms alone (E4).
- **OQ-3, reassociation.** ROADMAP's gate says no reassociation "appears". X0 can only screen for
  it. Does the Owner accept the screened reading for M0, or should ROADMAP route this clause to
  B1.5?
- **OQ-4, Amber (b).**
  - Is Amber (b) the intended operationalisation of the gate's contraction clause, given that
    ROADMAP's X0 entry has no amber for contraction?
  - Should a defect only in a non-release configuration (B-cmake, C) count?
  - Hearth supports MSVC, GCC and Clang (ADR-0007), but not clang-cl. Should a clang-cl defect be
    filed as "unsupported configuration"?
- **OQ-5, the baseline.** If the recomputed \|B_iform\| exceeds 105, may T_forms use it? The default
  is no (§4.5).
- **OQ-6, authorisation.** Confirm or withdraw the X0 instruction (D0_BRIEF §4.1), and set X0's spend
  limit under D0-10a. *Answered, pending ratification at sitting 1 (2026-10-18)* (pre-freeze review revision): the
  instruction part through D0-12 ("Batch weekly review", whose option text excepts X0 as already authorised; OWNER-QUEUE
  R3, "D0-12i CONFIRMED") and the spend part through D0-10a ("No metered API"; R1: $0 metered) [M, OWNER-ANSWERS.md,
  OWNER-QUEUE.md]; see the header.
- **OQ-7, pre-freeze compilation.** Confirm, through the X0 tooling track's statement in the freeze
  commit, that no Hearth object was compiled and examined before freeze. The configure-only runs in
  `experiments/x0-census/flags/` are disclosed in §2. *The statement is in §2 (x0prep's check of
  2026-10-16, with its one unverifiable part: unlogged interactive commands).*

## Appendix B. Tombstones from this revision

These use the format of DECISIONS.md §4 and the trigger grammar of
[06 §7.2](../../architecture/06-forge.md#72-the-decidable-scope-and-trigger-language).

```text
tombstone x0_p5_opclass_gate {
    verdict: misleading                    // operation classes count fewer units than ROADMAP §3.1's "mnemonics", so amber fires less often
    scope:   { record: x0_census, metric: p5 }
    class:   F                             // under: ROADMAP §3.1 counts FP-sensitive mnemonics as XED iclasses
    revisit_when: owner.answer(question: "X0-OQ1") == op_class
               || roadmap.section_hash(section: "3.1") != at_burial.roadmap.section_hash(section: "3.1")
    evidence: [ROADMAP §3.1] [G02 §1] [m0/README §M0] review 2026-10-16 (R1, R2)
    // survivor: P5_opclass, a secondary metric with no threshold
}

tombstone x0_p4_simd_only_gate {
    verdict: misleading                    // a SIMD-only or category-S union is smaller than "the union", so amber fires less often
    scope:   { record: x0_census, metric: p4 }
    class:   F                             // under: "the union" in ROADMAP §3.1 is the whole census union
    revisit_when: owner.answer(question: "X0-OQ2") == like_for_like
               || roadmap.section_hash(section: "3.1") != at_burial.roadmap.section_hash(section: "3.1")
    evidence: [ROADMAP §3.1] review 2026-10-16 (R1, R2)
    // survivor: |U_all^SIMD|, |U_all^SIMD,S| and |U_all^S| as secondary metrics
}

tombstone x0_amber_b_release_only {
    verdict: misleading                    // the gate's contraction clause names no compiler
    scope:   { record: x0_census, outcome: amber_b, configs: {b_cmake, c} }
    class:   F                             // under: the clause covers every compiler built with Hearth's own flags
    revisit_when: owner.answer(question: "X0-OQ4") == release_only
    evidence: [ROADMAP §3.1] review 2026-10-16 (R1)
    // survivor: config-scoped actions in the Amber (b) row
}

tombstone x0_unattributed_loop_flag {
    verdict: misleading                    // would turn a debug-info artefact into a false Hearth flag-defect report
    scope:   { record: x0_census, metric: p3c, attribution: {approximate, none} }
    class:   V
    revisit_when: b15.audit_reassociations(census_attribution: approximate) >= 1
    evidence: review 2026-10-16 (R2)
    // survivor: a variant-wide largest-lanes bound, with the loop listed as unattributed
}

tombstone x0_census_a_from_ninja {
    verdict: misleading                    // would census objects from a path that does not ship
    scope:   { record: x0_census, config: a }
    class:   F                             // under: Hearth's Windows release uses the Visual Studio generator
    revisit_when: hearth.windows_release_generator != "Visual Studio 17 2022"
    evidence: Hearth CONTRIBUTING.md:41, ci.yml:162, ADR-0007 @ b5d3f14; review 2026-10-16 (R2)
    // survivor: A-ninja as a byte-and-relocation cross-check
}
```

## Appendix C. `census.json` and `verdict.json`

`census.json` follows 03-trust §6.6, which keys records by (compiler hash, flags, source hash,
symbol). A field marked "[]" is a list.

```text
census.json = {
  record:   { id: "X0-census", freeze_commit, scripts_commit,
              sha256: { fp_class, loop_table, b_iform, hand_map, fp_flag_patterns, objdump_norm, xml } },
  runs:     [ { run_id, utc, kind: census|twin|repro|smoke, config, build_index: 1|2, census_sha256 } ],
  configs:  { <A|A-ninja|B-cmake|C|D|B-proxy|H-A|H-D|P>: {
              role: release|union|secondary, generator, host, abi,
              compiler: { path, banner, sha256: [ {file, sha256} ] },
              headers: { sdk, ucrt, libc_dev, resource_dir_sha256 },
              effective_flags: { <file>: { argv[], cc1_argv[]|null, gcc_q: {option: value}|null } },
              objects: { <file>: { object_sha256, source_blob_sha1, code_sections: [ {name, bytes_sha256, relocs_sha256} ] } } } },
  variants: [ { config, table: hx_kernels_scalar|k_avx2|k_avx512, slot: "matmul[F32]"|…|"act_quantize_q8",
                symbol, closure: [ {symbol, kind: entry|internal|interposable, section, start, end} ],
                coverage: { slot_resolved, gaps: [ {cause, offset, detail} ] },
                n_instructions, iforms: {iform: n}, iclasses: {iclass: n}, categories: {S: n, G: n},
                fp_sensitive: [iclass], p2_fma: n, p3: { a1: [pattern], a2: [pattern], b: [iclass],
                c: [loop_id], d1: pass|fail, d2: [ {site, result: match|mismatch|unchecked} ] },
                evex_static_rounding: n,
                lift_blockers: { internal_calls[], external_calls[], interposable_calls[],
                                 fp_trust_deps[], indirect_branches: n, jump_tables: n, hardening[] },
                loops: [ { id, header, source_loop|null, attribution: exact|approximate|none, tags[],
                           u_acc, u_ind, acc_lanes_emitted, acc_lanes_source, spills, reloads, register_reuse } ],
                sequences: [ { helper, site, iclass_seq[] } ],
                operand_order: [ { site, iclass, source, match: true|false|unattributed } ],
                unreachable: { padding_bytes, orphan_bytes, orphan_ranges[] } } ],
  baseline: { stdarch_commit, xml_sha256, intrinsics: 130, no_single_instruction, b_iform, b_mnem, t_forms },
  crossdecoder: { disagreements: [ {config, variant, offset, xed_iclass, objdump_mnemonic, fp_sensitive, resolution} ] },
  metrics:  { p1: {...}, p2: {...}, p3: {...}, p4_u_all, p5_iclass, secondary: {...} }
}

verdict.json = {
  validity: { v1, v2, v3, v4 }, tooling_runs: n, conservative_resolution: bool,
  outcomes: [ pass | amber_a | amber_b | amber_c | tooling_failure ],
  amber_a: { u_all, t_forms, p5_iclass }, amber_b: [ {config, p2, p3} ], amber_c: [ {config, variant, cause} ],
  non_gate: [ {row: N1|N2, config, detail} ],
  narrowing: null | { judged_utc, x2_verdict_sha256, uncovered: [ {config, variant, loop_id, tags[]} ] }
}
```

Fields added before freeze by x0prep (what `judge.py` reads; the others above stay):

```text
census.json += {
  record += { sha256 += { xed_tables }, scripts_sha256: { "<path under experiments/x0-census>": sha256 } },
  builds:   [ { config, file, build_index: 1|2, rc, compiler_ran: bool,
                compiler_sha256: { <binary>: sha256 },                         // must equal frozen_inputs "compilers"
                argv_sha256, argv_matches_frozen: bool,
                errors: [ { file, line, text } ], includes: [path],            // includes: /showIncludes or -H
                ice: bool } ],
  configs.<cfg>.p3a: { <file>: { a1: [pattern id], a2: [pattern id] } },      // required for A, A-ninja, B-cmake, C, D
  variants[] += { build_index: 1|2, file, union_member: bool,                  // union_member: A-ninja only
                  ab_compare: identical|differs,                               // A-ninja only; union_member == differs
                  slot_name_check: match|mismatch,                             // reported, not a gap (§4.2)
                  closure[].kind += cold_part_of:<parent>,
                  lift_blockers += { tail_calls[], noreturn_inferred[] },
                  jump_tables: [ { section_name, start, end, entry_type, n_entries, bound, site, byte_table } ],
                  unreachable += { data_bytes, referenced_non_instruction[] },
                  p3 += { d1: pass|fail|not_evaluated },                       // anything but pass flags (canary only)
                  loops[] += { acc_updates_per_iter, fp_free, not_computed_tags[] } },
  crossdecoder.disagreements[] += { normalised: [iclass] },                    // objdump reading via objdump_norm.csv
  rederivation: { present: bool, matches: bool, mismatches: [..],
                  figures: { u_all, p5_iclass, "<config>|<table>:<slot>": { flagged, gap_causes[] } } }
}
verdict.json += { eval_date, eval_date_basis: { system_utc_date, latest_census_run_date }, tooling_bound,
                  validity_detail: { schema[] | v1_tooling_gaps[], v1_config_gaps[], v2_unresolved[], v3, v4[] },
                  amber_b[].p3 += { rederivation[] },
                  amber_a += { two_t_forms, p5_limit, fp_sensitive_iclasses[], holds }, notes[] }
```

Fields added before freeze by x0final (written by `x0_census.py`; `judge.py` reads none of them, so its decisions are
unchanged; the assembler checks them):

```text
census.json += {
  record += { profile, mock, hearth_commit, source_blobs, assembled_utc },
  runs[] += { rc },                                           // census_sha256 is null: a file cannot hold its own hash
  builds[] += { kind, argv[], cwd, source, object, object_exists, object_sha256, compiler_binaries{}, frozen_diff,
                frozen_argv[], warnings, listing{argv[], rc}, log, log_sha256, utc_start, utc_end,
                cl_task_rc, batch_sources[], msbuild_log_sha256 },   // the last three: A only
  twin_builds: [ <build record of each twin, kind twin, twin_flag> ],
  configs.<cfg> += { mode, census_files[], steps[], p3a_hits{}, objects_build2{},          // objects: build 1
                     repro: { <file>: { identical, differing_sections[], only_in_build2[] } },          // §6
                     ab_compare_files: { <file>: { identical, differing_sections[] } } },  // A-ninja only, §2
  variants[] += { unit, object, ab_compare_detail, attribution: exact|approximate|none, attribution_detail,
                  p3 += { d1_sites[], d2[] += { reason, sequence[] } },
                  loops[] += { header_source_line, header_inline_stack[], header_line_from, attributed_through_frame,
                               source_loop_kind, source_loop_lines[], bound_used, unattributed, partial_results[],
                               carried_overwritten_before_back_edge[], peeled_regions[] },
                  sequences: [ { helper, site, iclass_seq[], interleaved } ] },
  metrics.secondary += { u_all_S, u_all_simd, u_all_simd_S, u_release, iforms_per_config, fp_sensitive_iclasses,
                         p5_opclass, delta_vs_b_iform_raw, evex_static_rounding, fp_environment_iclasses_in_counted_sets,
                         external_calls, ab_compare, repro_identical, attribution, loop_tags, loops_not_computed,
                         proxy_fidelity },
  schema_check: { violations[] }, notes[]
}
configurations: P.<CFG> (arm P with <CFG>'s quant_avx512.c line; table "probe", one variant per wrapper) and
B-proxy (role secondary); judge.py ignores both
```

Fields added before freeze by the x0final revision (2026-10-17; `judge.py` reads `record.freeze_commit`,
`variants[].attribution` and `crossdecoder.disagreements[].resolution` as stated in §8 item 9):

```text
run.json += { freeze_commit }                                  // x0_driver.py init, census kind: HEAD of the clean checkout
census.json += {
  record.freeze_commit, record.scripts_commit,                 // from run.json unless given; must agree
  builds[] += { fallback },                                    // A: "single-file ClCompile ..." when MSBuild never reached the file
  builds[].frozen_diff += { expected_delta, console_only_removed, same_order_without_delta },   // A
  variants[].coverage.gaps[] += { cause: other, detail: "twin attribution none: ..." },
  variants[].loops[] += { bound_header, bound_latch, bound_rule: same|header|latch|outer|min, partial_result_cycles[] },
  notes[] += "loop <config>|<variant>|b<k>|<id>: header ..., back edge ..., rule ..., bound used ..."
}
twin attribution (x0_twin.py) += { identity.sections[].functions: [ {name, start, end, identical} ] | null,
                                   sources.<file>.loop_vars: { "<line>": "<for induction variable>" } }
crossdecoder.disagreements[].resolution: "amendment:<id>" | absent       // anything else is unresolved
verdict.json += { validity_detail.v2_resolved_by_amendment[] }
```

Fields added before freeze by the pre-freeze review revision (2026-10-17; `judge.py` reads those marked *):

```text
run.json += { freeze_commit: <first commit with the record FROZEN>,      // was HEAD
              run_commit: HEAD, post_freeze_changes[]: <class/scripts/flags paths changed since, each named by an amendment>,
              record_appended_bytes }
<CFG>/config.json += { scripts_sha256: {path: sha256}, tree_recheck: {scripts, git}, source_blobs }   // census: re-checked
census.json += {
  record += { run_commit*, post_freeze_changes* },                  // record.scripts_commit = run_commit in a census run
  configs.<cfg> += { scripts_sha256*, tree_recheck, source_blobs },  // V4: scripts_sha256 == record.scripts_sha256
  configs.<cfg>.headers*,                                            // compared with frozen_inputs.json "headers"
  variants[].loops[].bound_rule += inner                             // and notes for rules outer, inner, min
}
class/frozen_inputs.json += { headers: { <cfg>: { sdk, ucrt, vctools | libc_dev, resource_dir_sha256: {files, sha256} } } }
class/hearth_shingles.json = { definition, k: 2, hearth_blobs, windows_per_file, allowed_structural_lines[13], shingles[] }
verdict.json += { record: <census.json record.id>,
                  validity_detail.v4_commits: { freeze_commit, run_commit, post_freeze, post_freeze_changes } | null,
                  canaries: { label: "outcome indicated before freeze by a verbatim copy (E6)",
                              d1: {<cfg>: ["b<k>:<d1>"]},
                              d2: {<cfg>: {match, mismatch, unchecked, variants_without_d2[]}},
                              p3c_labelled: {<cfg>: ["<table>:<slot>|b<k>:<loop ids or 'no flag'>"]} },
                  caveats[],                                         // every expected d2 site unchecked under A or D
                  amber_b[].label }                                  // when the entry has a d1 or d2 flag
```

## Appendix D. Freeze checklist (pre-data artefacts)

This record can be FROZEN only when every line below has its hash or value filled in. None of these
items reads a compiled Hearth object.

| # | Artefact | SHA-256 or value |
|---|---|---|
| D1 | `experiments/x0-census/TOOLCHAINS.md`, complete per Table 2.1 | Table 2.1 filled [M, x0prep]; `TOOLCHAINS.md` §11 mirrors it. File hash: `experiments/x0-census/FREEZE.md` |
| D2 | Flag captures: for A, the generated `hearth_core.vcxproj` and MSBuild's design-time ClCompile lines (the build lines come from the census binlog, §2); `compile_commands.json` for A-ninja, B-cmake, C and D; `-###` and `gcc -Q` outputs. All come from configure-only runs | `experiments/x0-census/flags/prefreeze/` (20 capture files and a README) plus `flags/C-gcc.compile_commands.json` and `flags/D-clang.compile_commands.json`; hashes in `FREEZE.md` |
| D3 | Smoke-test logs: NON-Hearth files only (§2): `smoke.c` and probes (steps 60-62), `smoke_dispatch.c` (steps 70-72), `smoke_dispatch.c` with `rv_tricky.c` and `rv_tricky2.c` (steps 71b and 72 after the §12 review), the instruction zoo (step 69), the x0final end-to-end driver runs on the census mock, the regression set and the reduce probe (steps 86 and 88; §7, and the arm P disclosure of §2), superseded by the x0final revision's runs with the rewritten mock (§7; the first mock's runs disclosed in §2); no Hearth file is compiled before freeze; `smoke_dispatch.c` carried Hearth lines until 2026-10-17 (§2 disclosure). **Pending (pre-freeze review revision):** step 88 re-run with the re-pinned scripts and the rewritten `smoke_dispatch.c` (§7). **Done by the desktop re-run (2026-10-17):** first run with the pinned scripts, the §4.7 idiom fix, final run with the re-pinned scripts (§7) | `scripts/runbook/logs/` (`60_*`, `61_*`, `62_*`, `x0prep_*`, `x0final_*`, `x0final_rev_*`, `prefreeze_rerun_*`), `scripts/smoke/results/x0final/`, `scripts/smoke/results/x0final_rev/`, `scripts/smoke/results/prefreeze_rerun/`; hashes in `FREEZE.md` |
| D4 | B-proxy and H argv for each file, written out | `flags/prefreeze/B-proxy.argv.json` and `flags/prefreeze/README.md`; hashes in `FREEZE.md` |
| D5 | `class/fp_class.csv`, plus the commit of `classify.py`, with the review recorded in §12 | `7cabb6913437c364f7d02c988a839ed5807462a3812cacd86e68a1c72a686c2f`; input `class/xed_tables.tsv` `1db25e7f5f02b5796d06cbb94f4cb5ab7d8230ed1091bacae485fa5c517d1d13`. **Review: done, 2026-10-16** (§12, reviewer 1 of the x0prep review; Claude, same family, independent context). A seeded random sample of 50 of the 741 FP-typed iclasses plus 147 hand-picked edge cases was re-classified blind: 197/197 agree. The XED cross-check covers all 502 iclasses hit by the named attributes or exception classes, and op_class matches on all 1,995 rows. SDM citations were not re-fetched; the template-reason finding was resolved by rewording §4.4, so the CSV and its hash are unchanged; second blind review (x0final, 945 iclasses): 0 disagreements (§12) |
| D6 | `B_iform.json`, `hand_map.csv`, stdarch commit, XML SHA-256, with the values written into §4.5 and the review recorded in §12 | `B_iform.json` `a66e1a935d887a272d5f3fb868d10a1877f8e4d7b26137a3962079b1edcb1eaa`; `hand_map.csv` `008f558ead3ee86b9484f8891470f51db0e10dbf8591a8509ca20c4219ad5d3e`; stdarch `eb9b3025937c85bd271a3ca46a681cd52739db12`; XML `6762a50652a35ef663fd532ed83b789d19bbc2ac7e94b1771f19d666d96c2c30`; values in §4.5. **Review: done, 2026-10-16** (§12, reviewer 1; Claude, same family, independent context). B_iform and hand_map were re-derived independently from the Hearth blobs and an independently downloaded XML (same SHA-256): identical. That covers 130 names (47/51/32), 23 with no single instruction, 105 XML form strings, 1 hand-mapped xed name, |B_iform| 102 and |B_mnem| 74, with 0 differences per intrinsic; second re-derivation (x0final): identical, |B_iform| 102, |B_mnem| 74 (§12) |
| D7 | `class/fp_flag_patterns.txt` | `181ab6e8b9cffbe12dd2d7bbeb4bf7a6aeed36161bc8e4ec2692261bf8a42dbc` |
| D8 | `class/objdump_norm.csv` | `d6196d60246a08733ca1581d83e81cc8be9891223e2750323b250c50dbc6e2e7` (LF bytes; validation: `class/objdump_norm_validation.json`, run on the same content with CRLF line endings) |
| D9 | `class/loop_table.csv` | `0d94b2e636fb355e3c3c56d9b452dfef6a00925860adda05e116fe99b22a35be` |
| D10 | Reduce-probe sources (arm P) | `scripts/probes/reduce_probe.c`; hash in `FREEZE.md` |
| D11 | Scripts implementing §4.2, §4.7 and §8 (`judge.py`), tested only on `scripts/smoke/` and never on Hearth objects; commit hash | §4.1/§4.2 (`x0_extract.py`, `x0_decode.py`) and §8 (`judge.py`) done, revised after the §12 review and tested (56 judge unit tests; runbook step 72 regression on 24 NON-Hearth objects, 0 deviations, order-independent). **Completed by x0final (2026-10-16/17):** the build records (`x0_build.py`), the debug-info twin attribution (`x0_twin.py`; §4.6), exact P3(c) attribution, P3(d2) site selection and the peeled and interchanged tags (`x0_loops.py`; §4.7, §5), the `census.json` assembler (`x0_census.py`; Appendix C, with compiler hashes, structured errors, include lists, §6 repro and `ab_compare`) and the census driver (`x0_driver.py`, runbook steps 79-82). Tested: 113 unit tests on synthetic inputs, and the driver end to end on NON-Hearth inputs (§7: the census mock in census mode under A, A-ninja, B-cmake, C, D; the regression set in replay mode, 0 deviations; arm P; B-proxy). **Independent review done 2026-10-16/17 (§12); revised by the x0final revision (2026-10-17):** 152 unit tests (66 `test_judge`, 7 `test_flags`, 17 `test_loops`, 27 `test_loops_x0final`, 14 `test_build`, 12 `test_twin`, 2 `test_census`, 7 `test_driver_guard`) [M, laptop, 2026-10-17], the end-to-end runs repeated with the final scripts and the rewritten mock (§7). The revision's own changes are not independently reviewed. **Pre-freeze review of 2026-10-17 (§12) done and handled by the pre-freeze review revision (2026-10-17, laptop):** 179 unit tests (71 `test_judge`, 7 `test_flags`, 17 `test_loops`, 27 `test_loops_x0final`, 16 `test_loops_prefreeze`, 14 `test_build`, 12 `test_twin`, 3 `test_census`, 12 `test_driver_guard`) [M, laptop, 2026-10-17], re-pinned; the end-to-end re-run on the desktop is pending (§7), and that revision's own changes are not independently reviewed. **Desktop re-run (2026-10-17):** done (§7); one pre-freeze tooling fix (§4.7 dependency-breaking idioms, Appendix E), 183 unit tests (20 `test_loops_prefreeze`, the others as above) [M, laptop, 2026-10-17], re-pinned; the fix is not independently reviewed. Hashes of every script in `FREEZE.md` and `class/frozen_inputs.json` "scripts" (checked by V4; widened by x0final to every file under `scripts/` except run outputs and documentation). Commit: the commit that adds them |
| D12 | The X0 tooling track's statement on whether any Hearth object was compiled before freeze (OQ-7) | §2 "Statement on pre-freeze compilation" and `TOOLCHAINS.md` §11 [M, x0prep, 2026-10-16]; qualified by the x0final revision: no Hearth file was compiled, but Hearth helper text inside the first census mock was (§2 disclosure, E6); qualified again by the pre-freeze review revision: so were three two-line runs of Hearth text inside the regression file `smoke_dispatch.c`, from x0prep until 2026-10-17 (§2 disclosure, E6) |

The hash values above were computed on 2026-10-16 by x0prep and are unchanged (recomputed by x0final and by the x0final revision of 2026-10-17, which changed `TOOLCHAINS.md` (D1: its desktop-activity account), D3's logs and records and D11's scripts, and none of the class files of D5-D9 or the D2, D4 and D10 files; and by the
pre-freeze review revision of 2026-10-17, which changed D11's scripts, `smoke_dispatch.c` among them, added the header
pins to `class/frozen_inputs.json` and remade `class/hearth_shingles.json`, and changed none of the D1, D2, D4-D10
files; and by the desktop re-run of 2026-10-17, which added D3 logs and records and changed two D11 files,
`x0_loops.py` and `tests/test_loops_prefreeze.py`, and none of the D1, D2, D4-D10 files). `FREEZE.md`
holds the complete list; every value is recomputed at freeze (`scripts/runbook/pin_inputs.py`), and
`class/frozen_inputs.json` must equal it (`judge.py` checks V4 against it).

## Appendix E. Changes made by x0prep before freeze (2026-10-16)

All changes are to a DRAFT and precede any data. None moves a threshold. Each needs the independent review
of §12.

| Where | Change | Direction |
|---|---|---|
| Header | Owner chat answers relayed (D0-10, D0-12, X0 authorised); X0 still collects only once FROZEN | none |
| §2 | Removed the pre-freeze compile smoke test of the three Hearth files; no Hearth file is compiled before freeze; D3 is smoke on NON-Hearth files only | stricter (no early look) |
| §2 | D12 statement written from a desktop scan and the job scripts; P3(a) for B-cmake disclosed as known from flags | disclosure |
| §2 table, Table 2.1 | Values filled [M]; A's pre-freeze capture is the vcxproj plus design-time lines (which omit `/O2`) | precision |
| §3 | B-cmake compile failure is a configuration finding (N1, N2), with Amber (b) still evaluated on its flags; C's hardening defaults and XED's `-cet` stated; B-proxy, H and P written out (H: `--shared` chosen) | precision |
| §4.2 | Relocation arithmetic, jump tables, import-pointer calls, no-return list, COFF ranges, hardening list; FP trust dependency = any external callee not on an allow-list | stricter (`fp_trust_dep`) |
| §4.4 | Enumeration widened to every XED iclass (so GPR iclasses are not FP-sensitive by default); XED names confirmed, substitutes and extra attributes listed; results | precision; stricter (extra attributes) |
| §4.5 | Values filled (102, 74, 102); `hand_map.csv` also covers `xed` names absent from the pinned XED | precision |
| §4.7 | `acc_lanes_emitted` counts distinct carried locations (same unit as source lanes); `acc_updates_per_iter` feeds u_acc; flow-sensitive carried reads with lane-0 semantics for scalar ops; tags computed vs not computed | precision of a unit (reviewer attention: the literal "sum of defining instructions" would flag serial unrolls) |
| §4.7, §8 | Loops whose peeled/interchanged status is unchecked count as uncovered for the narrowing unless X2 lists their id | stricter |
| §5 P1 | Compile rule (genuine vs tooling), decided by `judge.py` from build records | precision, exhaustive |
| §5 P3 | Mechanisation notes for (d1) and (d2); (d2) unchecked until twin attribution exists | disclosure |
| §7 | Script table; cross-decoder table validated on a NON-Hearth corpus; re-derivation procedure file | precision |
| §8 | Exhaustiveness list (completeness, compile outcomes, A-ninja, after-bound V4 / missing V3, unknown causes, recomputed Amber (a), narrowing default) | exhaustive |
| §12 | Statement that the x0prep artefacts are unreviewed | disclosure |
| Appendix C | Fields `judge.py` needs | precision |
| Appendix D | Values and status | — |
| §2 (post-review) | D12 statement extended: Hearth objects from Pierce's own development in the desktop's WSL home, not to be opened | disclosure |
| §4.2 (post-review) | Jump tables tied to the jump's own address computation, extent from the guarding bound, never partial; GCC cold parts as function families; calls through variables and CFG dispatch `unresolved_indirect`; reaching-definition register rule; round-based, order-independent descent; no-return inference; overlap gap; `.pdata` contiguity; slot-name warning; referenced code addresses listed | stricter |
| §4.4 (post-review) | `reason` column described as a rule template, not a per-instruction SDM citation | correction |
| §5 P1, P2, P3(b), P3(d1) (post-review) | Compiler pin on every build; located error = structured error in a census file or a recorded include; P2 recomputed from iclasses; approximation list extended (FP16/BF16 forms, VEXP2P\*, 3DNow!); any d1 other than `pass` flags | stricter |
| §7 (post-review) | Validation extended to the adversarial regression set of steps 71b and 72, with expected outcomes and a work-list-order check | precision |
| §8 (post-review) | Schema check; A-ninja comparison and P3(a) results required; coverage completeness; unknown causes rewritten in place; after the bound, V3 needs complete figures and a missing P3(a) result counts as a flag; evaluation date from the clock and the census runs; V2 and P2 recomputed; V4 covers `xed_tables.tsv`, every script and the compiler pins; narrowing counts empty tags and missing loop analyses as uncovered | stricter |
| §9, §12, Appendix C (post-review) | Threats updated; x0prep review logged; new fields | disclosure, precision |
| §4.6 (x0final) | Twin attribution implemented (`x0_twin.py`): section pairing by name and function symbols; identity of bytes and relocation lists; ELF line rows decoded with relocations and compared row by row with `llvm-dwarfdump --debug-line`; CodeView from `llvm-readobj --codeview` (annotation semantics measured on MSVC and clang-cl objects); row starts checked against `llvm-objdump`; inline stacks (ELF `.debug_info` compared with `llvm-dwarfdump --debug-info`) | precision |
| §4.7 (x0final) | Header line taken from the header block's first instruction with a line; source loop found through the inline stack when the header's line lies in an inlined function outside every loop; the back edge's own line considered too, the outer of the two nested source loops taken | precision (more loops exactly attributed, so more get their own bound; reviewer attention: the back-edge rule removed a false P3(c) flag measured on a vectorised tree, the shape of quant.c:362-363) |
| §4.7 (x0final) | Accumulator = carried location whose back-edge value an accumulating instruction produced; a register and its spill copy are one partial result; a call defines the caller-saved registers of the ABI; `[RBP+d]` and `[RSP+d]` are stack slots only while their base is loop-invariant | precision of a unit (reviewer attention: removes three false P3(c) flags measured on the mock and the regression set; a true split is still counted) |
| §4.7, §8 (x0final) | peeled and interchanged computed; interchanged stays in `not_computed_tags` for a nest without exact attribution of both loops | stricter (peeled over-tags) |
| §5 P3(d2) (x0final) | Site selection with exact attribution; the sequence ends at the tree's last FP ADD; live-in check; whitelist extended by (V)SHUFPD and VPERMILPD with an immediate | stricter (Clang sites become checkable) |
| §5 P1 (x0final) | Build records mechanised (`x0_build.py`): A's per-file lines, diagnostics and objects from the MSBuild log; include lists from a listing pass that writes no object; compiler binaries hashed exactly as pinned; argv check, with A's design-time comparison tolerating only optimisation switches and `/nologo`, `/diagnostics:column` (listed) | precision (reviewer attention: the two console-only switches) |
| §2, §6 (x0final) | The driver (`x0_driver.py`) configures and builds each configuration twice from scratch; §6 repro and the A versus A-ninja comparison per section and per variant are in `census.json` | precision |
| §3 arm P, §4.1 (x0final) | The reduce probe is extracted by symbol (`x0_extract.py --functions`) in configurations P.<CFG>; B-proxy runs through the driver's replay mode (`runbook/bproxy_set.json`); proxy fidelity computed | precision |
| §4.2 (x0final fix) | `x0_decode.py` no longer fails on a code section without relocations (found on the reduce probe under GCC and Clang) | correction |
| §7, Appendix C, Appendix D (x0final) | Scripts `x0_build.py`, `x0_twin.py`, `x0_census.py`, `x0_driver.py` and their fields; V4's script pins widened to every file under `scripts/` except run outputs | precision; stricter (V4) |
| §2, §8 E6 (x0final revision) | The first census mock contained verbatim Hearth helpers, compiled and analysed before freeze: disclosed; P3(d1)/(d2) marked "outcome indicated before freeze by a verbatim copy"; the mock rewritten; the shingle guard (`class/hearth_shingles.json`) refuses any smoke source sharing three consecutive non-trivial lines with a pinned Hearth file | disclosure; stricter (guard) |
| §4.2 (x0final revision) | A bound compare on the 8/16-bit register of the index is accepted after a same-width MOVZX | precision (a legitimate shape no longer a tooling gap) |
| §4.4 (x0final revision) | The FP-environment asymmetry of `fp_class.csv` and op_class of PH/SH/BF16 iclasses stated (CSV unchanged) | disclosure |
| §4.6 (x0final revision) | Attribution none is a tooling gap (V1); identity per closure function inside an equal-size section | stricter; precision (more exact attribution, so more own bounds and checked sites) |
| §4.7 (x0final revision) | Accumulators: taint through any instruction, merging only on equal provenance, partial results counted over cycles of the carried-location graph, compare-select as MAX/MIN, data operands only (a load through a carried pointer is not a carried value), opmask registers excluded; FMA counts as ADD (stated) | stricter (true splits the earlier rule missed are counted; reviewer attention: the data-operand and opmask precisions remove two false flags measured on the regression set under C) |
| §4.7 (x0final revision) | The outer source loop only with signs of flattening (constant or outer-bounded trip count and no emitted inner loop), or when the emitted loop encloses an emitted inner loop; otherwise the smaller bound; both bounds recorded and listed | stricter (reviewer attention: the enclosing rule removes a false flag of the reviewer's rule measured on the regression set under C) |
| §5 P1 (x0final revision) | Success needs `compiler_ran`, `argv_matches_frozen` and an object; A's line must be the design-time line plus exactly `/O2`, in order; the single-file ClCompile fallback when MSBuild stops; an error located in another source of the batch is not this file's | stricter; precision |
| §8 (x0final revision) | Exhaustiveness item 9: slot gaps, attribution, P3(a) with errors, `amendment:` resolutions, typed P3 lists, run dates, the freeze commit in V4; runbook 79-82 need `X0` | stricter |
| §12, Appendix D (x0final revision) | x0final review logged; D5/D6 second review recorded | disclosure |
| Header (lead engineer, 2026-10-17) | "OQ-6 answered" note: D0-12's verbatim answer and option text from OWNER-ANSWERS.md, read as confirming the X0 instruction | disclosure (row added by the pre-freeze review revision; the note had none) |
| §2, §8 E6 (lead engineer, 2026-10-17) | Ruling that P3(d1) and P3(d2) stay confirmatory, every report labelled "outcome indicated before freeze by a verbatim copy (E6)"; E6's last sentence | stricter (keeps the canaries in the gate; row added by the pre-freeze review revision) |
| Header, Appendix A OQ-6 (pre-freeze review) | Both parts of OQ-6 answered, pending ratification at sitting 1 (instruction: D0-12, R3; spend: D0-10a, R1, $0 metered); verbatim answers tagged [M], the reading tagged [G]; the $1.5k proposal and the relayed account superseded | correction |
| §2 ruling (pre-freeze review) | The ruling's last sentences reworded (loosening after data only as a post-data amendment reported both ways), ROADMAP §1 rule 1 quoted; the ruling unchanged | correction |
| §2, §8 E6, §9, Appendix D D3/D12 (pre-freeze review) | `smoke_dispatch.c` carried Hearth's tree, `q_rint` and amax lines (three two-line runs) and a near copy of `dot16_conv`'s accumulation, compiled and analysed since x0prep: disclosed; the E6 label widened to the P3(c) results of the scalar F32, F16, BF16 and act variants, with an expectation registered; the three runs rewritten with the same semantics and line numbers | disclosure; stricter (label) |
| §2 guard (pre-freeze review) | Shingle guard: comments stripped, pairs (k = 2), every `.c`/`.h` of the source and include directories, UTF-8 only, 13 allow-listed dispatch-table lines; fingerprints remade from the clone's files without git | stricter |
| §4.7 accumulators (pre-freeze review) | "Reads a loop-carried value" through any data-operand path; MOVD/VMOVD moves; compare-select through shared origins, and its SSE2 and/andn/or form; (b) merges only locations that are copies or parts of one value on every path | stricter (true splits counted; reviewer attention: the broader reading's effect on real output awaits the desktop re-run) |
| §4.7 source loop (pre-freeze review) | Mirror test (rule `inner`); nesting through the inline stack; `min` for unrelated loops | stricter (reviewer attention: changed in part from the proposal so that an inlined flattened helper loop does not take the caller's 128-lane loop to 0) |
| §5 P1 (pre-freeze review) | Header environment (SDK, UCRT, toolset, libc6-dev, resource-dir trees) pinned and part of the compile rule; the driver's resource-dir call fixed for `clang` | stricter |
| §5 P3(d) (pre-freeze review) | `verdict.json` "canaries" with the E6 label and per-configuration d2 counts; "every expected d2 site unchecked under A or D" registered as a caveat on Pass | disclosure (no outcome changes) |
| §7 (pre-freeze review) | The end-to-end evidence is for the previous scripts; the desktop re-run of step 88 and what it must show | disclosure |
| §8 item 10, Appendix C (pre-freeze review) | Freeze point and run commit; ignored files; amendment-named post-freeze changes; per-step script, commit and blob re-checks; `--frozen-db`/`--design-time` and `--freeze-commit` refused in a census run; source pin, per-configuration scripts and header pins in V4; `verdict.json` record id; new fields | stricter |
| §12, Appendix D D11 (pre-freeze review) | Pre-freeze review logged; 179 unit tests; re-pinned | disclosure |
| §4.7 accumulators (desktop re-run, 2026-10-17; pre-freeze tooling fix, §10) | A dependency-breaking idiom (XOR/SUB r,r; (V)XORPS/PD, (V)PXOR, VPXORD/Q, (V)PSUBB/W/D/Q, (V)PCMPGTB/W/D/Q, (V)PCMPEQB/W/D/Q x,x; no memory, immediate, write mask or merge masking) reads no value (`x0_loops.py` `dependency_breaking`, used by `uses_defs`); 4 unit tests (183 in all); re-pinned: `scripts/x0_loops.py`, `scripts/tests/test_loops_prefreeze.py`, `class/frozen_inputs.json` | precision (removes the 50 false P3(c) flags of the first re-run, 26 on the mock and 24 on the regression set, and the doubled count of the earlier enclosing loops; an idiom's result is a constant, so no partial result can be hidden; reviewer attention: unreviewed) |
| §2, §4.7, §5 P1, §7, §9, §12, Appendix D D3/D11 (desktop re-run, 2026-10-17) | Results of the re-run of step 88 (first run, fix, final run), the decode comparison of the rewritten `smoke_dispatch.c`, the header-environment confirmation, the throwaway-repository test of the freeze point and the Hearth HEAD read recorded | disclosure |
