# X0: instruction census of Hearth's quant kernels

Status: DRAFT (to be FROZEN at the commit that first adds it with this line changed to FROZEN, and
not before every item of Appendix D is done)
ROADMAP anchor: [§3.1](../../ROADMAP.md#31-x0-instruction-census-weeks-015); DR-008; G02 open question 6
Owner authorisation: **provisional, pending D0-12** (sign-off) **and D0-10a** (M0 budget).
- The previous draft quoted an Owner instruction of 2026-10-16: "Start the parts that need no owner
  decision: X0, instruction census". The only other copy in the repository is
  [D0_BRIEF §4.1](../../D0_BRIEF.md#41-d0-12-pre-registration-sign-off). That copy quotes this record
  and asks Pierce to confirm or withdraw the instruction [M, reviser, repository grep for the quoted
  text, 2026-10-16]. [PLAN.md](../PLAN.md) §1 and §8 repeat it, citing the sprint brief.
- The user request relayed to this revision's workflow on 2026-10-16 reads, verbatim: "please do
  this on ultra code mode and you have permission to do whatever you need to do to fulfil this
  project in its entirety".
- Whether that request counts as the explicit instruction the collection rule requires is
  Pierce's call (OQ-6). Collection under the FROZEN record proceeds on that basis provisionally,
  pending D0-12 and D0-10a, and the step can be reversed. If Pierce withdraws the instruction,
  collection stops, and every result collected so far is marked as collected under a withdrawn
  authorisation.
- Until he confirms it in writing (D0_BRIEF §4.1), collection covers local compilation and decoding
  only, on the desktop and the laptop, with no metered API spend beyond the agent sessions
  themselves. Any spend cap belongs to D0-10a. The brief proposes $1.5k for X0 [inference, ROADMAP
  §3.1 upper bound], and Pierce has not decided it.
- Under the [collection rule](../README.md#pre-registration-lifecycle-roadmap-1-rule-1-d0-12), the
  Gatekeeper evaluates no verdict until the record is SIGNED.
- Owner chat answers of 2026-10-16, as relayed by the x0prep task brief [relayed, not seen first-hand by
  x0prep; to be ratified at the first weekly signing session]: D0-12, signing is a batch weekly review and
  collection under any record waits for that sitting, **except X0, which the Owner has already authorised**;
  D0-10, no metered API spend for any model family, and the only family besides Claude is the local Qwen3 pilot
  run through Hearth. Nothing else in D0 is decided. These answers bear on OQ-6 but do not answer it formally;
  X0 still collects only after it is FROZEN, and the Gatekeeper still waits for the signature.

Pre-freeze preparation. The x0prep track (2026-10-16) produced the Appendix D artefacts, reworked the census
scripts, and changed this DRAFT where Appendix E lists. It compiled no Hearth source and decoded no Hearth
object; every validation used NON-Hearth smoke files (§2). The same track revised the scripts and this DRAFT
after its own independent review of 2026-10-16 (§12; Appendix E rows marked "post-review"), under the same
restriction.

Conventions. Evidence tags follow [docs/m0/README](../README.md#evidence-tags). "Reviser" means the
agent that revised this DRAFT on 2026-10-16. It worked on the laptop running this session (hostname
DESKTOP-F441IUK) against the read-only Hearth clone. Small integers inside definitions, such as a
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
- **No Hearth source is compiled before freeze, not even as an unread smoke test.** (The previous draft
  allowed a compile smoke test of the three files; x0prep removed it, Appendix E.) Whether each census file
  compiles under each configuration is therefore census data, classified by the compile rule of §5 P1. The
  pre-freeze smoke tests (D3) use only NON-Hearth files: `scripts/smoke/smoke.c`,
  `scripts/smoke/smoke_dispatch.c`, the adversarial regression files `scripts/smoke/rv_tricky.c` and
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
         rI allowed are zero- or sign-extending moves and whole-register copies. For an MSVC byte index table `movzx eI,byte [rB+rJ+T2]`,
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
7. **Loops.** These definitions serve P3(c) and the descriptive record.
   - **Natural loop.** The CFG is built over the variant's counted set. A natural loop is a back edge
     t→h where h dominates t. Loops that share a header are merged.
   - **Source loop.** The innermost source loop whose line range contains the header instruction's
     line, according to the twin. Attribution is exact, approximate (§4.6) or none.
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
     - "Reads a loop-carried value" is decided by a forward data-flow over one iteration (back edges into the
       header cut): the value read may be the one live into the header, directly or through register moves
       and stack reloads. Merge-masked writes keep the old value. For scalar unary and insert-style
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
  - *success*: exit status 0 and an object exists;
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
        count as identity.
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
      **Selecting the sites needs exact twin attribution, which the frozen scripts do not yet implement
      (Appendix D, D11): until it exists, every (d2) site is `unchecked`.**
    - P3(c) without attribution uses the variant-wide bound of (c) above for every loop (all loops
      unattributed); the twin attribution (§4.6) is the same missing piece.
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

The `x0_extract.py` and `x0_decode.py` present on 2026-10-16 describe, in their headers, COFF ranges
taken up to the next symbol and a linear-sweep decode [M, reviser, read, 2026-10-16]. They must
implement §4.2 before freeze (Appendix D, item D11). *Done by x0prep*: both were rewritten to §4.1/§4.2 and
validated on `scripts/smoke/smoke_dispatch.c` (NOT Hearth; two dispatch tables shaped like Hearth's, 12
slots) under A, B-cmake, C and D with each configuration's `quant_avx512.c` and `quant.c` command lines
[M, x0prep, runbook step 72, desktop, 2026-10-16]: 12/12 slots resolved by relocation in all 8 objects, 0
tooling gaps, 0 cross-decoder disagreements, `llvm-readobj` symbol cross-check clean; a deliberately
corrupted manifest makes the decode fail. Still missing before freeze: the `census.json` assembler and the
twin attribution (Appendix D, D11).

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
  code is expected and classified (§4.2).
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
  without exact attribution are *unattributed*. Both are listed for X2 and B1.5, not hidden.
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

Still unreviewed:
- the §4.7 unit change and `loop_table.csv`, which neither reviewer covered;
- the reviser's own revisions in response to these reviews (Appendix E, rows marked "post-review"). These
  need an independent review before freeze.

All reviews are same-family, independent-context (README, Independence; D0-10 as relayed in the header).

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
  limit under D0-10a.
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

## Appendix D. Freeze checklist (pre-data artefacts)

This record can be FROZEN only when every line below has its hash or value filled in. None of these
items reads a compiled Hearth object.

| # | Artefact | SHA-256 or value |
|---|---|---|
| D1 | `experiments/x0-census/TOOLCHAINS.md`, complete per Table 2.1 | Table 2.1 filled [M, x0prep]; `TOOLCHAINS.md` §11 mirrors it. File hash: `experiments/x0-census/FREEZE.md` |
| D2 | Flag captures: for A, the generated `hearth_core.vcxproj` and MSBuild's design-time ClCompile lines (the build lines come from the census binlog, §2); `compile_commands.json` for A-ninja, B-cmake, C and D; `-###` and `gcc -Q` outputs. All come from configure-only runs | `experiments/x0-census/flags/prefreeze/` (20 capture files and a README) plus `flags/C-gcc.compile_commands.json` and `flags/D-clang.compile_commands.json`; hashes in `FREEZE.md` |
| D3 | Smoke-test logs: NON-Hearth files only (§2): `smoke.c` and probes (steps 60-62), `smoke_dispatch.c` (steps 70-72), `smoke_dispatch.c` with `rv_tricky.c` and `rv_tricky2.c` (steps 71b and 72 after the §12 review), the instruction zoo (step 69); no Hearth file is compiled before freeze | `scripts/runbook/logs/` (`60_*`, `61_*`, `62_*`, `x0prep_*`); hashes in `FREEZE.md` |
| D4 | B-proxy and H argv for each file, written out | `flags/prefreeze/B-proxy.argv.json` and `flags/prefreeze/README.md`; hashes in `FREEZE.md` |
| D5 | `class/fp_class.csv`, plus the commit of `classify.py`, with the review recorded in §12 | `7cabb6913437c364f7d02c988a839ed5807462a3812cacd86e68a1c72a686c2f`; input `class/xed_tables.tsv` `1db25e7f5f02b5796d06cbb94f4cb5ab7d8230ed1091bacae485fa5c517d1d13`. **Review: done, 2026-10-16** (§12, reviewer 1 of the x0prep review; Claude, same family, independent context). A seeded random sample of 50 of the 741 FP-typed iclasses plus 147 hand-picked edge cases was re-classified blind: 197/197 agree. The XED cross-check covers all 502 iclasses hit by the named attributes or exception classes, and op_class matches on all 1,995 rows. SDM citations were not re-fetched; the template-reason finding was resolved by rewording §4.4, so the CSV and its hash are unchanged |
| D6 | `B_iform.json`, `hand_map.csv`, stdarch commit, XML SHA-256, with the values written into §4.5 and the review recorded in §12 | `B_iform.json` `a66e1a935d887a272d5f3fb868d10a1877f8e4d7b26137a3962079b1edcb1eaa`; `hand_map.csv` `008f558ead3ee86b9484f8891470f51db0e10dbf8591a8509ca20c4219ad5d3e`; stdarch `eb9b3025937c85bd271a3ca46a681cd52739db12`; XML `6762a50652a35ef663fd532ed83b789d19bbc2ac7e94b1771f19d666d96c2c30`; values in §4.5. **Review: done, 2026-10-16** (§12, reviewer 1; Claude, same family, independent context). B_iform and hand_map were re-derived independently from the Hearth blobs and an independently downloaded XML (same SHA-256): identical. That covers 130 names (47/51/32), 23 with no single instruction, 105 XML form strings, 1 hand-mapped xed name, |B_iform| 102 and |B_mnem| 74, with 0 differences per intrinsic |
| D7 | `class/fp_flag_patterns.txt` | `181ab6e8b9cffbe12dd2d7bbeb4bf7a6aeed36161bc8e4ec2692261bf8a42dbc` |
| D8 | `class/objdump_norm.csv` | `d6196d60246a08733ca1581d83e81cc8be9891223e2750323b250c50dbc6e2e7` (LF bytes; validation: `class/objdump_norm_validation.json`, run on the same content with CRLF line endings) |
| D9 | `class/loop_table.csv` | `0d94b2e636fb355e3c3c56d9b452dfef6a00925860adda05e116fe99b22a35be` |
| D10 | Reduce-probe sources (arm P) | `scripts/probes/reduce_probe.c`; hash in `FREEZE.md` |
| D11 | Scripts implementing §4.2, §4.7 and §8 (`judge.py`), tested only on `scripts/smoke/` and never on Hearth objects; commit hash | §4.1/§4.2 (`x0_extract.py`, `x0_decode.py`) and §8 (`judge.py`) done, revised after the §12 review and tested (56 judge unit tests; runbook step 72 regression on 24 NON-Hearth objects, 0 deviations, order-independent). §4.7 (`x0_loops.py`) is done except the twin attribution (and so P3(d2) site selection and exact P3(c) attribution) and the peeled/interchanged tags. The `census.json` assembler is not written; it must also record the build fields judge.py now requires (compiler hashes, structured errors, include lists, `ab_compare`). **Incomplete.** Hashes of every script in `FREEZE.md` and `class/frozen_inputs.json` "scripts" (checked by V4). Commit: the commit that adds them |
| D12 | The X0 tooling track's statement on whether any Hearth object was compiled before freeze (OQ-7) | §2 "Statement on pre-freeze compilation" and `TOOLCHAINS.md` §11 [M, x0prep, 2026-10-16] |

The hash values above were computed on 2026-10-16 by x0prep. `FREEZE.md` holds the complete list; every value
is recomputed at freeze, and `class/frozen_inputs.json` must equal it (`judge.py` checks V4 against it).

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
