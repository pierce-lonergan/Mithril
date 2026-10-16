# X0 instruction census: toolchains on the desktop

Set up on 2026-10-16 (desktop clock, EDT) on Pierce's desktop: Windows 11, Ryzen 9 9950X (Zen 5,
AVX-512), WSL2 Ubuntu 24.04.3. This step installed, built and validated tools only. **No census data
was collected, and no Hearth source was compiled.** Hearth was only dry-configured; the only
code compiled was a smoke file and small probes.

Tags: **[M]** measured in this session, with the command shown or a log in `scripts/runbook/logs/`.
**[D]** taken from documentation and not measured. **[I]** inferred.

## 1. Status

| Tool | Version / commit | Install path | Status |
|---|---|---|---|
| Clang/LLVM for Windows | 23.1.3 (`llvmorg-23.1.3`, 0d261d1ca552c95a8f007e061c787ac7132fbcbc) | `D:\mithril\tools\llvm-win-23.1.3` | working [M] |
| Clang/LLVM for Linux (WSL) | 23.1.3, same tag and commit | `/mnt/d/mithril/tools/llvm-linux-23.1.3` | working [M] |
| Intel XED, Linux static (CLI and `libxed.a`) | v2026.08.23 (0bcb6237345c5066726dcc08b3d87928df3b5b26) | `/mnt/d/mithril/tools/xed-v2026.08.23` | working [M] |
| Intel XED, Linux shared (`libxed.so`) | v2026.08.23 | `/mnt/d/mithril/tools/xed-v2026.08.23-shared` | working [M] |
| Intel XED, Windows (MSVC build, `xed.exe` and `xed.lib`) | v2026.08.23 | `D:\mithril\tools\xed-v2026.08.23-win` | working [M] |
| mbuild (XED build system) | v2026.08.23 (1b437e409221a2b5703b4d8896baa20d43e4ba1a) | `D:\mithril\src\mbuild` | used [M] |
| CMake for Linux (WSL had none) | 4.4.3 | `/mnt/d/mithril/tools/cmake-4.4.3-linux` | working [M] |
| Hearth source | b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220 (detached, clean) | `D:\mithril\src\hearth` | cloned [M] |
| Pre-installed: MSVC cl | 19.44.35229, toolset 14.44.35207, SDK 10.0.26100.0 | VS 2022 Community | used [M] |
| Pre-installed: CMake (Windows) | 4.4.3 | `C:\Program Files\CMake\bin` | used [M] |
| Pre-installed: WSL gcc / make / python3 / objdump | 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1) / GNU Make 4.3 / 3.12.3 / binutils 2.42 | `/usr/bin` | used [M] |
| Pre-installed: Windows Python | 3.13.4 | `C:\Python313` | used [M] |

Scripts: `scripts/` (see `scripts/README.md`). Exact compile commands: `flags/`.

## 2. Downloads and verification

All downloads went straight to `D:\mithril\tools\dl` with `curl.exe` on the desktop. SHA-256 values
were computed with `Get-FileHash` [M]. Log: `scripts/runbook/logs/setup_verify_llvm.log` and
`setup_verify_cmake.log`.

| File | Bytes | SHA-256 | URL |
|---|---|---|---|
| `clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz` | 901,331,280 | `9ee6a2192fbb30c776415af529927f76ca6b5d1d55699bb1315f9878e610b5b8` | https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.3/clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz |
| `...windows-msvc.tar.xz.sig` | 466 | `802811b09426a123b282147889bb0a19bfc641abe9a22e9fe5df9646e179409d` | same path + `.sig` |
| `...windows-msvc.tar.xz.jsonl` | 11,202 | `1803cbaab25bbd7be33feea6f6d78ee6a723f74a2d2453bc6299fec91709301c` | same path + `.jsonl` |
| `LLVM-23.1.3-Linux-X64.tar.xz` | 2,016,524,848 | `ca9fe385a5d9e2d88132dc0e23a00e9f87f38fa75f67207b5e457d208e71d013` | https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.3/LLVM-23.1.3-Linux-X64.tar.xz |
| `LLVM-23.1.3-Linux-X64.tar.xz.sig` | 466 | `0dda2b64d7c856831dfc818eea0d15b0a8df02e7a9d77c880a49891f00691091` | same path + `.sig` |
| `LLVM-23.1.3-Linux-X64.tar.xz.jsonl` | 10,955 | `5026a782bfc3c46691c203ee56ce4c26d2853d8f571df2ef16f2524ae7678a2f` | same path + `.jsonl` |
| `release-keys.asc` (LLVM release keys) | 13,300 | `f38bd19b7f2d22cafa755841e6ce9375b9a2e6d41f7b974e4953d6b084839001` | https://releases.llvm.org/release-keys.asc (the link given on the GitHub release page) |
| `cmake-4.4.3-linux-x86_64.tar.gz` | 64,872,980 | `d6c83076c575bc00b823522ac974bda66d0af05d6ddc30e739c12385cf32c6cc` | https://github.com/Kitware/CMake/releases/download/v4.4.3/cmake-4.4.3-linux-x86_64.tar.gz |
| `cmake-4.4.3-SHA-256.txt` | 2,015 | `1726140f0b13bf99e4ad4e89389d5aed758e1658ebfe1ed4aa2c2b32dde839f5` | same release |
| `cmake-4.4.3-SHA-256.txt.asc` | 833 | `ef0c8639a28e5d85ddbed2b625e556225d54be3b7092807fdb48475fd24ed031` | same release |
| CMake signing key | 43,109 | `aa00e8536082a5dac61372decaee67e982bac013164e7d3f0ebebc86c85efb4b` | https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xcba23971357c2e6590d9efd3ec8fef3a7bfb4eda (the link cmake.org/download gives) |

Verification [M]:
- **LLVM, three independent checks, all passed for both archives:**
  1. The local SHA-256 equals the `digest` that the GitHub release API reports for the asset.
  2. `gpg --verify <file>.sig <file>`: "Good signature from Tobias Hieta", RSA key
     `D574BD5D1D0E98895E3BF90044F2485E45D59042`, using keys from `release-keys.asc`. The temporary
     keyring is at `D:\mithril\tools\gnupg-llvm`. The key is not certified by any trusted signature,
     which is normal for a fresh keyring.
  3. `gh attestation verify --repo llvm/llvm-project <file> --bundle <file>.jsonl` exited 0. Signer
     workflow: `llvm/llvm-project/.github/workflows/release-binaries.yml@refs/tags/llvmorg-23.1.3`.
     The attested subject digests equal the SHA-256 values above. gh was not logged in, and the
     check worked with the bundle on disk. gh config and cache were redirected to `D:\mithril\tools\gh*`.
- **CMake:** the tarball's SHA-256 equals both its line in `cmake-4.4.3-SHA-256.txt` and the GitHub
  asset digest. `gpg --verify cmake-4.4.3-SHA-256.txt.asc` gave "Good signature from Brad King",
  primary key `CBA23971357C2E6590D9EFD3EC8FEF3A7BFB4EDA`, subkey `C6C265324BBEBDC350B513D02D2CEF1034921684`.
- **XED and mbuild:** cloned over HTTPS from github.com/intelxed at the newest release tag,
  `v2026.08.23` (published 2026-08-24) [M]. Tag commits: xed `0bcb6237345c5066726dcc08b3d87928df3b5b26`,
  mbuild `1b437e409221a2b5703b4d8896baa20d43e4ba1a` [M].
  - Neither release has any assets: no checksums and no signatures [M].
  - GitHub API: the xed tag is annotated (tag object `c6424829fd66ef8c3abb1ecb27a8d4003abebf6f`) but
    unsigned. The commit it points to carries a GitHub-verified signature (`verified: true`, "valid").
  - The mbuild tag is lightweight, and its commit is unsigned [M].
  - Integrity therefore rests on the commit hashes recorded here.

Why these versions: LLVM 23.1.3 is `releases/latest` of llvm/llvm-project, published
2026-10-06 [M]. CMake 4.4.3 matches the CMake already on Windows. Kitware's latest is 4.4.4 [M].

## 3. Installation and per-tool verification

### Clang for Windows: `D:\mithril\tools\llvm-win-23.1.3` (4,278,955,825 bytes) [M]
- Extracted with `tar.exe -x -f ...tar.xz --strip-components 1 -C D:\mithril\tools\llvm-win-23.1.3`
  (`runbook/12_extract_llvm_win.cmd`), rc 0, about 10 minutes to the USB disk.
- `clang-cl.exe --version` and `clang.exe --version`: "clang version 23.1.3 (https://github.com/llvm/llvm-project
  0d261d1ca552c95a8f007e061c787ac7132fbcbc)", target x86_64-pc-windows-msvc. `llvm-objdump.exe` and
  `llvm-readobj.exe --version`: "LLVM version 23.1.3" [M] (`runbook/40_verify_win.cmd`).
- clang-cl finds the MSVC headers and libraries from `vcvars64.bat` in the same cmd session. It
  compiled, linked and ran `probes/hello_avx2.c` (`<stdio.h> <math.h> <stdint.h> <immintrin.h>`), rc 0,
  output `sqrt(2)=1.414214`. `-###` shows the `-internal-isystem` paths of MSVC 14.44.35207 and
  SDK 10.0.26100.0 [M].
- SHA-256 of `bin\clang-cl.exe` = `9584244d83bb095c5a2983f814692cb50e0b8d2916585516cad8f3e8596d8261`,
  of `bin\llvm-objdump.exe` = `226901b358d1056441eb0b8acaed920d9ca9751d953939bc34162b0f75f83494` [M].

### Clang for Linux (WSL): `/mnt/d/mithril/tools/llvm-linux-23.1.3` (12,407,177,457 bytes) [M]
- Extracted inside WSL with `xz -T8 -dc ... | tar -x --strip-components=1 -C ...`
  (`runbook/13_extract_llvm_linux.sh`), rc 0, about 10 minutes. Symlinks such as `clang -> clang-23`
  were preserved on drvfs.
- `clang --version`: 23.1.3, same commit, target x86_64-unknown-linux-gnu. Dynamic dependencies are
  only libm, libz, libstdc++, libgcc_s and libc, all present [M].
- `clang -O2 -mavx512f probes/hello_avx512.c -lm` (`<math.h> <stdint.h> <stdio.h> <immintrin.h>`) compiled,
  linked with `/usr/bin/ld` and ran on the 9950X (rc 0). It used Ubuntu's glibc headers:
  "Selected GCC installation: /usr/lib/gcc/x86_64-linux-gnu/13", include path `/usr/include` [M]
  (`runbook/41_verify_wsl.sh`).
- SHA-256 of `bin/clang-23` = `913453afb492abab17025139852413ba7fd7a52b4fb75fcce58ff3fe399d0a9e`, of
  `bin/llvm-objdump` = `3fec78d88dcb975ad2b475b2e4f98575222c21ab8a94670aec25de418a05b3c7` [M].

### CMake for Linux: `/mnt/d/mithril/tools/cmake-4.4.3-linux` [M]
WSL had no cmake, and sudo needs a password, so apt was not an option [M]. The official tarball
was extracted to D: (`runbook/21_extract_cmake_linux.sh`). `cmake --version` reports 4.4.3.

### XED [M]
Sources: `D:\mithril\src\xed` and `D:\mithril\src\mbuild`, cloned in WSL (LF line endings) with
`git clone --branch v2026.08.23 --depth 1` (`runbook/05_clone_sources.sh`).

| Build | Command | Result |
|---|---|---|
| WSL, gcc 13.3, static | `python3 ./mfile.py -j 8 --static --build-dir=/mnt/d/mithril/src/xed-build-static --install-dir=/mnt/d/mithril/tools/xed-v2026.08.23 install examples` | rc 0 in 3:50. `bin/xed` is a statically linked ELF, SHA-256 `18a3184f0e04e43c7669a10516f8e3f5d67c4e124199d054c7d243d8391b0916`. `lib/libxed.a` SHA-256 `e3491c24bae5ce1feb8f64eadc82a5f7fd2cfdb4f9d9f0585b589091d9e3c8f0`. |
| WSL, gcc 13.3, shared | same command with `--shared`, `--build-dir=.../xed-build-shared`, `--install-dir=/mnt/d/mithril/tools/xed-v2026.08.23-shared` | rc 0 in 2:31. `lib/libxed.so` SHA-256 `11e78a90ba54904767b24aae689013470dafc718fd83f7079a485243bc3ed7b3`. `bin/xed` resolves `libxed.so` through `../lib` and works. |
| Windows, MSVC 19.44 | inside vcvars64: `C:\Python313\python.exe -B mfile.py --compiler=ms -j 8 --build-dir=D:\mithril\src\xed-build-win --install-dir=D:\mithril\tools\xed-v2026.08.23-win install examples` | rc 0 in 37 s. `bin\xed.exe` SHA-256 `f10d268012be8c4958bf4eb632b342481e509dd9051b3cf39a9e2bde09846368`. `lib\xed.lib` SHA-256 `20f0e26a1d60b71f3d5c275fe2f57951b6f7abf2e95bc916cf4db123493d52d7`. |

`xed -version` gives "XED version: [v2026.08.23]" for all three builds [M]. Linux XED and Windows XED
gave identical results on all four smoke objects (section 7) [M].

**XED command-line behaviour, measured:**
- `xed -64 -d 62f17c4858c1` prints `ICLASS: VADDPS`, `CATEGORY: AVX512`, `EXTENSION: AVX512EVEX`,
  `IFORM: VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512`, `ISA_SET: AVX512F_512`,
  `ATTRIBUTES: MASKOP_EVEX MXCSR` and `SHORT: vaddps zmm0, zmm0, zmm1`. `-d` decodes a single
  instruction: a 17-byte string fails with "test string was too long".
- `xed -64 -ir FILE` decodes a flat binary. This is the key mode, and it works.
  - Default verbosity (`-v 2`) gives one line per instruction:
    `XDIS <off>: <CATEGORY> <EXTENSION> <HEX> <disasm>`.
  - `-isa-set` adds the ISA_SET column.
  - `-v 4` adds a header line per instruction, `<ICLASS> <IFORM> <operand fields...>` (EVEX fields
    such as `MASK:1`, `ROUNDC:1`, `SAE`, `BCAST`, `VL:2`), followed by the operand list.
  - `-ir` never prints ATTRIBUTES, at any verbosity. The decode script therefore takes attributes
    from `-d`, once per distinct encoding.
  - `-b ADDR` sets the base address. `-as/-ae` have no effect with `-ir`: the whole file is decoded.
  - Undecodable bytes give `ERROR: GENERAL_ERROR Could not decode at offset: 0x1b len: 3 ...` and a
    final `# Errors: N`. The exit status stays 0, so errors must be parsed.
  - The Windows build also prints `#Opening/#Trying to read/#Read` lines.
- `-cet` is needed to decode `endbr64` (`f30f1efa`) as `ENDBR64`/CET. Without it, XED reports
  `NOP_GPRv_GPRv_0F1E`/PPRO. The decode script uses `-64 -cet`.
- In this XED version, the attribute `MXCSR_RD` exists only on `STMXCSR` and `VSTMXCSR` (datafiles,
  and `xed -d 0fae1c24`). FP arithmetic, `VROUNDPS` and `VCVTPS2PH` carry `MXCSR`. `MXCSR_RD`
  therefore cannot be used as "depends on the rounding mode".
- `-chip-check-list` has no Zen 4 or Zen 5 entry: `AMD_ZEN2` is the newest AMD chip, then `AMD_FUTURE`.

### Hearth source: `D:\mithril\src\hearth` [M]
`git clone https://github.com/pierce-lonergan/hearth.git` in WSL, then `git checkout
b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220`, detached. Commit date 2026-10-05T23:15:13-04:00. GitHub's
`main` pointed at this commit on 2026-10-16. `git status --porcelain` was empty after the dry
configures.

## 4. Hearth: exact compile flags per configuration [M]

Dry configure only (`runbook/50_configure_win.cmd`, `runbook/51_configure_wsl.sh`), CMake 4.4.3,
`-DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON`. Generators: "NMake Makefiles"
inside vcvars64 for A and B, "Unix Makefiles" (`/usr/bin/gmake` 4.3) for C and D. All four
configures returned 0. A second configure from scratch produced byte-identical
`compile_commands.json` files. Copies: `flags/<cfg>.compile_commands.json`. Per-file flag
extraction: `flags/quant_flags.json` (`scripts/x0_flags.py show`).

Flags below omit the per-file plumbing (source, `/Fo`, `/Fd`, `-o`, `-c`). `<inc>` stands for
`-I…/engine/include -I…/engine/src`. All 16 translation units are listed in each JSON.

| Cfg | Compiler (CMake cache) | quant.c | quant_avx2.c adds | quant_avx512.c adds |
|---|---|---|---|---|
| A | `…\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe` (MSVC 19.44.35229.0), linker link.exe | `/nologo -DHEARTH_BUILD_DLL -D_CRT_SECURE_NO_WARNINGS <inc> /DWIN32 /D_WINDOWS /O2 /Ob2 /DNDEBUG -std:c11 -MD /experimental:c11atomics /fp:precise /utf-8 /W3 /FS` | `/arch:AVX2` | `/arch:AVX512` |
| B | `D:/mithril/tools/llvm-win-23.1.3/bin/clang-cl.exe` (Clang 23.1.3, simulating MSVC 19.44), linker lld-link.exe, AR llvm-lib.exe, MT llvm-mt.exe | `/nologo -DHEARTH_BUILD_DLL -D_CRT_SECURE_NO_WARNINGS <inc> /DWIN32 /D_WINDOWS /O2 /Ob2 /DNDEBUG /std:c11 -MD /experimental:c11atomics /fp:precise /utf-8 /W3` | `/arch:AVX2` | `/arch:AVX512` |
| C | `/usr/bin/gcc` (resolves to `x86_64-linux-gnu-gcc-13`, GNU 13.3.0), linker /usr/bin/ld | `-DHEARTH_BUILD_DLL <inc> -O3 -DNDEBUG -std=gnu11 -fPIC -ffp-contract=off -Wall -Wextra -Wno-unused-parameter` | `-mavx2 -mfma -mf16c` | `-mavx512f -mavx512bw -mavx512vl -mavx512vnni -mavx2 -mfma -mf16c` |
| D | `/mnt/d/mithril/tools/llvm-linux-23.1.3/bin/clang` (Clang 23.1.3), linker /usr/bin/ld | identical to C | `-mavx2 -mfma -mf16c` | `-mavx512f -mavx512bw -mavx512vl -mavx512vnni -mavx2 -mfma -mf16c` |

Notes:
- `CMAKE_C_FLAGS` is `/DWIN32 /D_WINDOWS` for A and B and empty for C and D. `CMAKE_C_FLAGS_RELEASE`
  is `/O2 /Ob2 /DNDEBUG` for A and B and `-O3 -DNDEBUG` for C and D. C and D get `-std=gnu11` [M],
  because `C_EXTENSIONS` defaults on [D].
- **Effective flags for B, from `clang-cl -###`** [M]:
  - `/O2` becomes `-O3 -vectorize-loops -vectorize-slp -ffunction-sections`.
  - `/arch:AVX2` becomes `-target-cpu haswell`, which includes FMA, F16C and BMI2 [D]. The B smoke
    object does contain FMA and BMI2 (`SHLX`) instructions [M].
  - `/arch:AVX512` becomes `-target-cpu skylake-avx512`, which has no AVX512-VNNI. The VNNI probe in
    section 6 shows this.
  - Even with no options, the driver passes `-stack-protector 2`, which corresponds to the default
    `/GS` [D].
  - `/experimental:c11atomics` is not used: "warning: argument unused during compilation". C11
    atomics still compile, because clang has them built in (`probes/atomic_probe.c` with B's
    `quant.c` flags gave rc 0).
- **Effective flags for D, from `clang -###`** [M]: `-target-cpu x86-64` plus
  `+avx512f,+avx512bw,+avx512vl,+avx512vnni,+avx2,+fma,+f16c`, and `-ffp-contract=off` is kept.
- **Implicit Ubuntu GCC defaults in C that `compile_commands.json` does not show**
  (`gcc -v`, `gcc -Q --help=common`, `-dM -E`) [M]:
  - `-D_FORTIFY_SOURCE=3`
  - `-fstack-protector-strong`
  - `-fstack-clash-protection`
  - `-fcf-protection=full`, which emits `endbr64` at every function entry (`__CET__ 3`)
  - `-fasynchronous-unwind-tables`
  - GCC was configured with `--enable-cet --enable-default-pie`.

  The LLVM-release clang in D has none of these (only `__PIC__ 2`). In the smoke test, C emitted
  six `ENDBR64` and D emitted none.

## 5. `/fp:precise` and FP contraction [M]

Source: `runbook/40_verify_win.cmd` (log `logs/40_verify_win.log`), probe `fpc.c` = `return a*b+c;`.

**clang-cl 23.1.3:** cc1 flags reported by `clang-cl <opts> -### -c fpc.c`:

| clang-cl options | cc1 FP flags |
|---|---|
| (none) | `-fmath-errno -ffp-contract=on -fno-rounding-math` |
| `/fp:precise` | `-fmath-errno -ffp-contract=on -fno-rounding-math -complex-range=full` |
| `/fp:precise /fp:contract` | same as `/fp:precise` (still `on`) |
| `/fp:strict` | `-ffp-contract=off -frounding-math -ffp-exception-behavior=strict` |
| `/fp:fast` | `-ffp-contract=fast -ffast-math -menable-no-infs -menable-no-nans -fapprox-func -fno-signed-zeros -freciprocal-math` |
| `/O2 /fp:precise /clang:-ffp-contract=off` | `-ffp-contract=off` (warning: "overriding '-ffp-model=precise' option with '-ffp-contract=off'") |

Findings:
- `/fp:precise` maps to `-ffp-contract=on`. Clang may therefore fuse `a*b+c` written in a single
  expression into an FMA whenever the target has FMA. Under Hearth's flags that means
  `quant_avx2.c` (haswell) and `quant_avx512.c` (skylake-avx512).
- Measured codegen:
  - `clang-cl /O2 /fp:precise /arch:AVX2` and `/arch:AVX512` emit `vfmadd213ss` for `fpc.c`.
  - Adding `/clang:-ffp-contract=off` gives `vmulss` + `vaddss`, and so does `/fp:strict`.
  - In the smoke object built with B's exact `quant_avx512.c` flags, the scalar tail
    `r += a[i]*b[i]` of `smoke_avx2_dot` became `VFMADD231SS`/`VFMADD132SS` (5 instructions), and
    `smoke_contract_probe` became `VFMADD213SS`.
- **A, C and D do not contract.** Contraction appears only in B, because Hearth's CMakeLists gives
  MSVC-like compilers `/fp:precise` and gives `-ffp-contract=off` only to the non-MSVC branch.
- `-ffp-contract=off` passed to clang-cl directly is **ignored**: "warning: unknown argument ignored
  in clang-cl", and the code still has `vfmadd213ss` [M]. `/clang:-ffp-contract=off` works [M].
  `-Xclang -ffp-contract=off` was not tested.

**MSVC 19.44 (for information):**
- `cl /?` lists `/fp:<contract|except[-]|fast|precise|strict>`.
- Measured: `cl /O2 /fp:precise /arch:AVX2` and `/arch:AVX512` give `vmulss` + `vaddss`, with no
  contraction. Adding `/fp:contract` gives `vfmadd213ss`.
- [D] Microsoft's `/fp` documentation says that, from VS 2022 on, `/fp:precise` no longer generates
  contractions unless `/fp:contract` is given. The measurement agrees.

**GCC and Clang (Linux):** `-ffp-contract=off` is honoured. Without it, gcc's default is `fast` and
clang's is `on`, and both emit `vfmadd*` for `fpc.c` with `-mavx2 -mfma` [M].

## 6. Compile probes against Hearth's exact flags [M]

`runbook/60_smoke_win.cmd`, run with `x0_flags.py replay`, which takes Hearth's exact per-file
command and swaps in the probe source.

| Probe | A (cl) | B (clang-cl) |
|---|---|---|
| `vnni_probe.c` (`_mm512_dpbusd_epi32`), `quant_avx512.c` flags | rc 0 | **rc 1**: "always_inline function '_mm512_dpbusd_epi32' requires target feature 'avx512vnni'" |
| same plus `-mavx512vnni` (accepted by clang-cl as is) | | rc 0 |
| `atomic_probe.c` (`<stdatomic.h>`), `quant.c` flags | rc 0 | rc 0 (warning: `/experimental:c11atomics` unused) |
| `atomic_probe.c` without `/experimental:c11atomics` | rc 2: "C atomic support is not enabled" | |

`quant_avx512.c` calls `_mm512_dpbusd_epi32` (line 238 at b5d3f14) and has no
`__attribute__((target))`. **Configuration B will therefore not compile `quant_avx512.c` as
Hearth's CMake configures it** [I, from the probe; Hearth itself was not compiled].

## 7. Smoke validation of the decode pipeline [M]

The smoke file `scripts/smoke/smoke.c` was compiled with each configuration's exact
`quant_avx512.c` command. It has AVX-512 add/mul, masked loads/mul/store, AVX2+FMA intrinsics, a
scalar `a*b+c`, a 10-case switch and a static helper. Extraction cross-checked every symbol
against `llvm-readobj --symbols`, and decoding cross-checked every instruction boundary against
`llvm-objdump -d` (`runbook/61_smoke_wsl.sh`). Results: `scripts/smoke/results/<cfg>/`.

| Cfg | Format | Code sections | Functions | Instructions (non-padding) | Errors | Info notes |
|---|---|---|---|---|---|---|
| A | COFF | 7 × `.text$mn`, COMDAT nodup | 7 | 214 | 0 | MSVC jump table: 40 bytes in `smoke_switch`'s `.text$mn`, detected and excluded; one `66 90` pad before it |
| B | COFF | 7 × `.text`, COMDAT nodup | 7 | 174 | 0 | no table inside the code; its 21 relocations are all REL32 operands [I: the table sits in a data section] |
| C | ELF | `.text`, `.text.unlikely` | 8 (incl. `smoke_switch.cold`) | 300 | 0 | 6 inter-function gaps, all NOP padding |
| D | ELF | `.text` | 7 | 185 | 0 | 6 inter-function gaps, all NOP padding |

- 0 undecodable bytes. 0 symbol-crosscheck mismatches. 0 llvm-objdump boundary mismatches.
  0 relocations straddling an instruction. ICLASS, IFORM, ISA_SET, EXTENSION and CATEGORY agree
  between the `-ir` and `-d` passes.
- **Negative test:** with a manifest corrupted on purpose (decode started one byte into a function,
  plus an empty range), `x0_decode.py` exited 1 with `objdump_boundary_mismatch`, `undecodable`,
  `coverage_mismatch` and `xed_exit`. The checks are not vacuous.
- **Cross-platform:** Windows-native runs (Python 3.13, `xed.exe`, Windows `llvm-readobj` and
  `llvm-objdump`) and WSL runs gave identical function tuples and identical per-instruction records
  for all four objects (`runbook/62_smoke_decode_win.cmd`).
- **Differences already visible in the smoke test:**
  - Contraction exists only in B.
  - A and C use `KMOVW` (AVX512F_KOPW); B and D use `KMOVD` (AVX512BW_KOPD).
  - C emits `ENDBR64` (CET) and some 256-bit EVEX forms (AVX512F_256).
  - `MXCSR` attributes appear on all FP arithmetic. No `MXCSR_RD` appears.

## 8. Runbook (desktop)

Scripts are in `scripts/runbook/` and mirrored to `D:\mithril\x0\scripts\runbook\`. Logs from
this session are in `scripts/runbook/logs/`. Long jobs ran detached:

```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine='cmd.exe /c D:\mithril\jobs\<job>.cmd > D:\mithril\jobs\<job>.log 2>&1'; CurrentDirectory='D:\mithril\jobs'}
```

WSL jobs used a `.cmd` wrapper that runs `wsl.exe -d Ubuntu -- bash /mnt/d/...sh`. Every job sets
`CUDA_VISIBLE_DEVICES=-1`, points `TEMP`/`TMP`/`TMPDIR` at `D:\mithril\jobs\tmp`, and uses at most 8
threads (`-j 8`, `xz -T8`).

| Step | Script | Ran here |
|---|---|---|
| 05 | `05_clone_sources.sh`: xed, mbuild (tag `v2026.08.23`), hearth (`b5d3f14`) | yes |
| 10, 11 | `10_fetch_llvm.cmd`, `11_verify_llvm.ps1`: download, SHA-256, GPG, gh attestation | yes (11 re-run for the log) |
| 12, 13 | `12_extract_llvm_win.cmd`, `13_extract_llvm_linux.sh` | yes (about 10 min each, in parallel) |
| 20 to 22 | `20_fetch_verify_cmake.ps1`, `21_extract_cmake_linux.sh`, `22_verify_cmake.ps1` | yes |
| 30, 31 | `30_build_xed_wsl.sh` (static and shared), `31_build_xed_win.cmd` (MSVC) | yes |
| 40, 41 | `40_verify_win.cmd`, `41_verify_wsl.sh`: tool checks, `/fp` mapping, implicit defaults | yes, final versions |
| 50, 51 | `50_configure_win.cmd`, `51_configure_wsl.sh`: Hearth dry configure, A to D | yes, final versions |
| 60 to 62 | `60_smoke_win.cmd`, `61_smoke_wsl.sh`, `62_smoke_decode_win.cmd`: smoke, probes, decode, negative test, cross-platform comparison | yes, final versions |

Steps 40 to 62 are the committed scripts, re-run end to end at 14:38 after the scripts were
synced to `D:\mithril\x0\scripts`. Steps 05 to 31 are the scripts exactly as run. Re-running them
downloads, extracts and rebuilds again.

The census step (not done) builds `--target hearth_core` in each `D:\mithril\x0\cfg\<cfg>` tree and
then runs `x0_extract.py` and `x0_decode.py` on `CMakeFiles/hearth_core.dir/engine/src/*.c.{obj,o}`
(see `scripts/README.md`).

## 9. Disk usage [M]

- **D: (`D:\mithril`):** 21,104,308,236 bytes in 31,875 files.
  - Linux LLVM: 12.41 GB.
  - Windows LLVM: 4.28 GB.
  - Downloads (`tools\dl`): 2.98 GB. These can be deleted after verification.
  - XED build trees: 0.90 GB.
  - XED kits: 0.31 GB.
  - CMake (Linux): 0.19 GB.
  - Sources: 24 MB.
  - `x0` (configure trees, smoke): 3.8 MB.
- **C:, written directly: none.**
  - All jobs used D:. The WSL `ext4.vhdx` was 112,231,186,432 bytes before and
    112,124,231,680 bytes after, so it did not grow.
  - VS `_Instances\*\state.json` was touched (2 files, 1,120 bytes) during the vcvars runs
    [I: possibly by the VS installer's background task, which ran at 14:30].
- **C:, side effect: 320,339,968 bytes** in 14 `RdClientAutoTrace-WppAutoTrace-*.etl` files under
  `%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\`, created 14:10 to 14:48.
  - [I] Their creation times match each WSL VM start in this session. WSLg's RDP client
    (msrdc) writes one trace per VM start, 10 to 105 MB each.
  - They were not deleted.
  - The total is under the 500 MB budget but not near zero.
- The free space on C: fell by about 1.47 GB over the session (55,942,467,584 to 54,468,935,680
  bytes). Most of that is other software: OneDrive cache 1.66 GB, browsers and chat apps.

## 10. Problems and items for Pierce

1. **Configuration B cannot compile `quant_avx512.c` as configured.** clang-cl's `/arch:AVX512` is
   skylake-avx512 and lacks AVX512-VNNI, while the file uses `_mm512_dpbusd_epi32`. Options for the
   pre-registration:
   - Add `-mavx512vnni` to B for that file (measured to work, but no longer exactly Hearth's flags).
   - Change Hearth's CMake for clang-cl.
   - Record B's AVX-512 TU as "does not build".
2. **Configuration B contracts FP (`-ffp-contract=on`).** That goes against the numerics contract
   stated in Hearth's CMakeLists ("precise FP, no contraction"). A, C and D do not contract. The
   fix in Hearth would be `/clang:-ffp-contract=off` for clang-cl, because clang-cl ignores plain
   `-ffp-contract=off`. Whether the census measures B as-is or patched is a pre-registration choice.
3. **Ubuntu GCC (C) adds hidden hardening flags**, CET `endbr64` among them. The census should
   either record these or neutralise them explicitly (for example `-fcf-protection=none`). That is
   a pre-registration choice.
4. **WSLg trace files on C:** about 320 MB in this session, from about 14 WSL VM starts (see section 9).
   - To reclaim the space, Pierce can delete
     `%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\RdClientAutoTrace-WppAutoTrace-20261016-*.etl`.
     The folder also holds older traces from 10/12.
   - To avoid it during the census, keep one WSL session alive for the whole run instead of
     starting the VM per command.
   - Alternatively, set `[wsl2] guiApplications=false` in `%USERPROFILE%\.wslconfig`. That is a
     configuration change, so it is left to Pierce.
5. NMake (A, B) builds serially. That is within the CPU cap, just slower.
6. WSL has no zstd and no ninja, and `sudo` needs a password. Everything X0 needs is on D: instead.
