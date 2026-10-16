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
| A | `Visual Studio 17 2022`, `-A x64`. This is Hearth's documented and CI Windows release path [M, reviser, read of Hearth `CONTRIBUTING.md:36-41`, `.github/workflows/ci.yml:159-164` and ADR-0007 line 27 at b5d3f14, 2026-10-16] | The ClCompile command lines in the MSBuild log of that build (binary log, or detailed verbosity). `CL.command.1.tlog` is a cross-check. **The census objects of A are the objects this build produces** |
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
- CMake's configure step writes these files without compiling any Hearth source (CMake's own
  compiler-check programs aside) [inference]. The repository cannot show whether any Hearth object
  was compiled before freeze. The freeze commit must therefore carry the tooling track's statement
  on that (Appendix D, item D12; OQ-7).
- **One further pre-freeze action is allowed: a compile smoke test.** The three files are compiled
  under each configuration and arm of §3 with the command lines that will be frozen. Only the exit
  status and the diagnostics text are recorded. Objects go to a temporary directory and are deleted
  without being read by any script: no decode, no hash, no size. The log is pre-freeze artefact D3.

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
| MSVC (A, A-ninja, H-A) | Toolset directory `14.44.35207`, VS 2022 Community: the compiler path in `flags/A-msvc.compile_commands.json` [M, X0 tooling track, 2026-10-16]. `cl` reports its own version, expected 19.44.x [inference]. "14.44.35207" is not the `cl` banner | ________ (`cl` banner; SHA-256 of `cl.exe`, `c1.dll`, `c2.dll`; Windows SDK and UCRT versions; MSBuild version) |
| LLVM (B-cmake, B-proxy, D, H-D) | 23.1.3, from the install directory names `llvm-win-23.1.3` and `llvm-linux-23.1.3` in `flags/*.json` [M, X0 tooling track, 2026-10-16]; the banner is not yet recorded | ________ (`clang --version`, `clang-cl --version`, LLVM commit, SHA-256 of both binaries, hash of the resource-dir headers) |
| GCC (C) | `/usr/bin/gcc` in WSL2. The previous draft's "13.3.0 (Ubuntu 24.04)" is unverified | ________ (`gcc --version`, `gcc -v`, hash of `-dumpspecs`, SHA-256 of `cc1`, `libc6-dev`/glibc version, Ubuntu release) |
| CMake; Ninja | not recorded | ________ |
| XED | tag `v2026.08.23`, which PLAN.md §2 takes from the X0 track's scratch scripts [not verified by the reviser] | ________ (tag, commit, build options, `xed -version`) |
| stdarch XML (§4.5) | not chosen | ________ (stdarch commit; SHA-256 of `intrinsics_data/x86-intel.xml`) |
| Effective flags | `flags/quant_flags.json` (explicit lines only) | ________ (per configuration and file: exact compiler argv; `clang -###` / `clang-cl -###` cc1 lines; `gcc <flags> -Q --help=common,optimizers`) |

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
  then flag B-cmake (§8, E1).
- `/arch:AVX512` in clang-cl may not enable AVX512-VNNI. If so, `quant_avx512.c` fails at
  `_mm512_dpbusd_epi32` (quant_avx512.c:237). `/experimental:c11atomics` may also be ignored or
  rejected. The pre-freeze smoke test (§2) settles both. A failure is handled by row N2 of §8.
- The Win64 ABI (xmm6 to xmm15 callee-saved) changes spills relative to D. That is why B-proxy, not
  B-cmake, is the proxy arm.

**Secondary arms.** These are reported and cannot change the verdict. A flag defect found in one of
them still produces the mandatory report (§10).

| Arm | What | Why |
|---|---|---|
| B-proxy | clang-cl with D's codegen flags for each file passed through `/clang:`, i.e. `-O3 -std=gnu11 -ffp-contract=off` plus D's `-m` flags, with `/fp:precise` and `/arch:*` removed. Target triple and ABI stay Win64 | The "clang-cl build with the release flags, labelled as a proxy for the SysV build" of ROADMAP §3.4. It feeds the proxy-fidelity metric (§5) |
| H-A, H-D | `scripts/hxcc.py` builds of the three files, with MSVC and with D's clang | Hearth's second build path (`-O2`) |
| P (reduce probe) | One translation unit per ISA. It is not Hearth code. Its noinline wrappers call `_mm512_reduce_add_ps`, `_mm512_reduce_max_ps` and `_mm512_reduce_add_epi32`, and each main-union configuration compiles it with its own `quant_avx512.c` flags | ROADMAP §3.1 and [04 §7.1](../../architecture/04-toolchain.md#71-x0-the-instruction-census-dr-008-v0-m0-before-the-lifter-exists)(c) ask how `_mm512_reduce_add_ps` is lowered, and Hearth at b5d3f14 never calls it (§4.5) |
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
3. **Form** = XED `iform`. **Mnemonic** = XED `iclass`. ROADMAP §3.1's "mnemonics" is read as XED
   iclass, the stricter of the readings on offer (OQ-1).
   - A secondary partition by XED extension separates category **S** (SIMD and mask: SSE, SSE2,
     SSE3, SSSE3, SSE4, AVX, AVX2, AVX2GATHER, FMA, F16C, AVX512EVEX, AVX512VEX) from category **G**
     (every other reachable instruction: GPR, control flow, NOP-class inside reachable code).
   - The extension names are XED's. `classify.py` checks them against the pinned release before
     freeze.
4. **FP sensitivity** (the unit of P5). The classification is fixed before any Hearth object exists.
   - Before freeze, `scripts/classify.py` enumerates every XED iclass in these extensions or ISA
     sets: X87; SSE to SSE4.2; AVX; AVX2 and AVX2GATHER; FMA; F16C; AVX-512 F, CD, BW, DQ, VL, VNNI,
     BF16 and FP16 (EVEX and the VEX k-mask forms); BMI1; BMI2.
   - It writes `experiments/x0-census/class/fp_class.csv` with the columns `iclass`, `extension`,
     `fp_sensitive` (yes|no), `reason` (SDM section or pseudocode clause) and `op_class`. The CSV's
     SHA-256 goes into Appendix D, and an independent reviewer checks it before freeze (§12).
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
       form, the iform it maps to, and the reason.
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
   - **Values, filled before freeze:** |B_iform| = ____, |B_mnem| = ____, T_forms = ____ [M, script,
     machine, date].
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
     authoritative]:

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
   - **Unroll factor.** u_acc is the emitted accumulator lanes updated per iteration divided by the
     source lanes updated per source iteration. u_ind is the primary induction increment divided by
     the source loop's bytes per iteration. Both are reported, and any disagreement between them is
     reported.
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
- **P2, contraction.** The number of FMA-class instructions in each variant's counted set:
  iclasses VFMADD\*, VFMSUB\*, VFNMADD\*, VFNMSUB\*, VFMADDSUB\*, VFMSUBADD\*, and FMA4 forms. Hearth's
  source at b5d3f14 contains no FMA intrinsic (§4.5), so any FMA-class instruction is a contraction.
  The script re-checks the source.
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
  - **(b) Approximations.** The counted set contains an approximation iclass (RCPPS, RCPSS, RSQRTPS,
    RSQRTSS and their V forms, VRCP14\*, VRSQRT14\*, VRCP28\*, VRSQRT28\*) with no matching source
    intrinsic. There are none at b5d3f14 (§4.5).
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
      folds `(v + M) − M` to `v`. If the pair is missing, the variant is flagged.
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
| `x0_flags.py` | flag capture |
| `x0_extract.py` | §4.1 and §4.2 |
| `x0_decode.py` | XED decode and the cross-decoder check |
| `x0_loops.py` | §4.7, P3(c) and P3(d) |
| `classify.py` | §4.4, before freeze |
| `baseline.py` | §4.5, before freeze |
| `judge.py` | §8: reads `census.json`, writes `verdict.json` |

The `x0_extract.py` and `x0_decode.py` present on 2026-10-16 describe, in their headers, COFF ranges
taken up to the next symbol and a linear-sweep decode [M, reviser, read, 2026-10-16]. They must
implement §4.2 before freeze (Appendix D, item D11).

**Raw outputs.** The objects, build logs, XED decode dumps, `llvm-objdump` disassembly and the twins'
line tables. Results land in `experiments/x0-census/results/` as `census.json` (Appendix C),
`verdict.json` and REPORT.md.

**Cross-decoder check.**
- For every reachable instruction, the XED instruction length must equal `llvm-objdump`'s.
- The XED iclass is compared with the `llvm-objdump` mnemonic through
  `experiments/x0-census/class/objdump_norm.csv`, which is frozen before collection.
- Every disagreement is listed. A disagreement where either side maps to an FP-sensitive iclass
  blocks validity check V2 (§8) until it is resolved.

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

**Expectations registered before data** [inference, from reading the source and the flags; none of
them measured]:
- **E1.** P3(a1) flags B-cmake (§3), so Amber (b) holds under the strict reading.
- **E2.** B-cmake fails to compile `quant_avx512.c` (row N2). The smoke test settles this before
  freeze.
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
  the pinned XED before freeze (§4.3, §4.4).
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

Per-reviewer counts are the reviser's count of the findings relayed on 2026-10-16 [M, reviser].
Totals: 34 findings (3 blocker, 19 major, 12 minor); 34 accepted, 5 of them only in part; 0 rejected
outright [D: sums of the rows above]. Each accepted finding was checked against the Hearth clone at
b5d3f14, the repository docs and `experiments/x0-census/flags/` before it was applied.

Sub-points rejected (one line each):
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
  checking them before freeze.

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
  `experiments/x0-census/flags/` are disclosed in §2.

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

## Appendix D. Freeze checklist (pre-data artefacts)

This record can be FROZEN only when every line below has its hash or value filled in. None of these
items reads a compiled Hearth object.

| # | Artefact | SHA-256 or value |
|---|---|---|
| D1 | `experiments/x0-census/TOOLCHAINS.md`, complete per Table 2.1 | ________ |
| D2 | Flag captures: the MSBuild log for A; `compile_commands.json` for A-ninja, B-cmake, C and D; `-###` and `gcc -Q` outputs. All come from configure-only runs | ________ |
| D3 | Smoke-test log (exit status and diagnostics only; objects deleted unread) | ________ |
| D4 | B-proxy and H argv for each file, written out | ________ |
| D5 | `class/fp_class.csv`, plus the commit of `classify.py`, with the review recorded in §12 | ________ |
| D6 | `B_iform.json`, `hand_map.csv`, stdarch commit, XML SHA-256, with the values written into §4.5 and the review recorded in §12 | ________ |
| D7 | `class/fp_flag_patterns.txt` | ________ |
| D8 | `class/objdump_norm.csv` | ________ |
| D9 | `class/loop_table.csv` | ________ |
| D10 | Reduce-probe sources (arm P) | ________ |
| D11 | Scripts implementing §4.2, §4.7 and §8 (`judge.py`), tested only on `scripts/smoke/` and never on Hearth objects; commit hash | ________ |
| D12 | The X0 tooling track's statement on whether any Hearth object was compiled before freeze (OQ-7) | ________ |
