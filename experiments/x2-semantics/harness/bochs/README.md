# Bochs as the X2 second oracle: feasibility, measured

Status: feasibility probe, 2026-10-16 (x2build track). Answers FUZZ-DESIGN.md §6.1's open points by
measurement where it could. **Not the second-oracle run of the X2 record**: no budget vector ran in
Bochs. The probe executes 12 hand-coded cases taken from `semantics/selftest.py` (development data, same
status as the harness dev smoke). Tags as in [docs/m0/README.md](../../../../docs/m0/README.md); "[M]" =
measured by this track on the desktop (Ryzen 9 9950X, Windows 11 26200.9711) on 2026-10-16.

## 1. Source, licence, build [M]

| Item | Value |
|---|---|
| Release | Bochs 3.1, GitHub `bochs-emu/Bochs` release `REL_3_1_FINAL`, published 2026-08-23; tag commit `30cfd566ecc8deb33e56e801e32b444a7041b6d2` (GitHub API) |
| Licence | LGPL-2.1 (GitHub repository metadata). The source download involves no licence click-through |
| Asset used | `bochs-3.1-msvc-src.zip`, 9,937,055 bytes, SHA-256 `3453bb34384ad30fcc4c3be76fd31632318431bad33fc917cb307b70364434b3` = the digest GitHub publishes for the asset |
| Configuration (the package's own `config.h`, from `.conf.win64-vcpp`) | `--enable-x86-64 --enable-cpu-level=6 --enable-avx --enable-evex --enable-vmx=2 --enable-svm --enable-cet --enable-fred --enable-show-ips --enable-debugger --with-win32 --with-rfb --with-nogui` …; `config.h`: `BX_SUPPORT_AVX 1`, `BX_SUPPORT_EVEX 1`, `BX_SUPPORT_X86_64 1`, `BX_DEBUGGER 1`, `BX_SUPPORT_AMX 0` |
| Build | `build_bochs.cmd`: the package's VS2019 solution, Release x64, MSVC 14.44 (toolset v143 instead of the solution's v142, which is not installed), `msbuild /m:2` (≤ 2 compiler processes); rc 0, 30 s wall (18:16:36 to 18:17:06 desktop clock) |
| Output | `obj-release\bochs.exe`, SHA-256 `1f45343a6d933ba2f8910c6426ade7fa35c223f5c128715227cbbb3cf7cbefc9` (our build, not a published binary) |

So the release's own MSVC configuration enables AVX and EVEX. FUZZ-DESIGN §6.1 left open "whether the
published Windows binaries are built that way". The published installer `Bochs-win64-3.1.exe`
(8,029,860 bytes, GitHub digest `ccbec06ec5baa81064cfe7c91862d0027b5033dbfa0b773d22e8be92094fdbb5`) was
**not downloaded or run**: it is an installer with a licence page and installs system-wide. That it is
built with the same configuration is an inference from the MSVC package, not a check. Building from the
MSVC source package removes the need for it.

## 2. CPU models [M] (`bochs.exe --help cpu`)

33 models: i386 … `corei7_skylake_x`, `corei3_cnl`, `corei7_icelake_u`, `tigerlake`, **`sapphire_rapids`**,
`arrow_lake`, `wildcat_lake`; AMD: `amd_k6_2_chomper`, `athlon_xp`, `athlon64_*`, `turion64_tyler`,
`phenom_8650_toliman`, `zambezi`, `trinity_apu`, `ryzen`. **No Zen 4 or Zen 5 model.** With
`sapphire_rapids` the guest sees vendor `GenuineIntel`, CPUID.1.EAX `0x000806F8`, CPUID.7.0.EBX
`0xF1BF27EB` (AVX512F, AVX512BW, AVX512VL among others), CPUID.0xD.0.EAX `0xE7` (x87, SSE, AVX, opmask,
ZMM_Hi256, Hi16_ZMM). So Bochs is an Intel-modelled oracle, as FUZZ-DESIGN §6.1 anticipated.

## 3. Bare-metal probe [M]

`boot.S` (GNU as/ld 2.42 in WSL, `mkimage.sh`): boot sector → protected mode → long mode (identity map
2 MB), CR4.OSFXSR|OSXMMEXCPT|OSXSAVE, XCR0 = 0xE7; stage 2 masks the 8259, installs a minimal IDT, runs
12 cases, prints `T<n> <lane 0 or k> <MXCSR>` on the debug port 0xE9, then writes `Shutdown` to port
0x8900. `run_probe.ps1` runs it with `bochsrc.txt` (`cpu: model=sapphire_rapids`, `display_library:
nogui`, `port_e9_hack: enabled=1`, `clock: sync=none`).

| # | Instruction, case (selftest label) | Bochs 3.1 | Table prediction | 9950X (harness dev smoke, same vector) |
|---|---|---|---|---|
| T1 | VADDPS zmm, 1 + 2^−24 RNE (A1) | 0x3F800000, PE | 0x3F800000, PE | same as table |
| T2 | VMULPS zmm, 0x00800001 × 0x3F7FFFFE (A13, F-TINY) | 0x00800000, PE (no UE) | 0x00800000, PE | same as table |
| T3 | VDIVSS, 0x00000001 / +0 (B6, F-FLAGPRI) | +∞, **ZE** | +∞, **DE\|ZE** | +∞, **ZE** |
| T4 | VMAXPS zmm, max(+0, −0) (B1) | −0 | −0 | same as table |
| T5 | VCVTPS2DQ zmm, 2^31 (D2) | 0x80000000, IE | 0x80000000, IE | same as table |
| T6 | VCVTPH2PS zmm, f16 0x0001 under DAZ (D4, F-H2F) | 0x33800000, no flag | 0x33800000, no flag | same as table |
| T7 | VPDPBUSD zmm, bytes 2 × 3, acc 0 | 24 | 24 | not run |
| T8 | VPMADDUBSW zmm, (255, 255) × (127, 127) (F1) | 0x7FFF (saturated) | 0x7FFF | not run |
| T9 | VCMPPS k, UNORD_Q on [1.0, QNaN, 1.0 …] | k = 0x2 | k = 0x2 | not run (C2/C3 analogues agreed) |
| T10 | VMULPS zmm under FTZ, 2^−126 × 0.5 (A12, F-FTZ-EXACT) | +0, UE\|PE | +0, UE\|PE | same as table |
| T11 | VMAXPS zmm under DAZ, max(+0, −den) (B4, F-DAZ-SEL) | −0 | −0 | same as table |
| T12 | VADDPS zmm{k1 = 0xFFFE}, SNaN in masked-off lane 0 (E1, F-MASKEXC) | lane 1 = 3.0, no IE | 3.0, no flag | same as table |

Every in-scope instruction tried executes in Bochs's `sapphire_rapids` model (VADDPS, VMULPS, VMAXPS,
VCVTPS2DQ, VCVTPH2PS, VPDPBUSD, VPMADDUBSW at 512 bits, VCMPPS into k, write masks, VDIVSS). Bochs agrees
with the table on 11 of 12. **T3 is the dev-smoke disagreement again:** Bochs and the 9950X both set ZE
alone, the table predicts DE|ZE; in §6.3's terms that is "table bug". On T2, T6, T10 and T11 the table's
reading came from Bochs's SoftFloat (`table_source: sdm+bochs`), so Bochs's agreement there is, as
FUZZ-DESIGN §6.3 says, not independent evidence.

Output of the final run (`out_tq0.txt`, guest lines): `T1 3F800000 1FA0`, `T2 00800000 1FA0`,
`T3 7F800000 1F84`, `T4 80000000 1F80`, `T5 80000000 1F81`, `T6 33800000 1FC0`, `T7 00000018 1F80`,
`T8 7FFF7FFF 1F80`, `T9 00000002 1F80`, `T10 00000000 9FB0`, `T11 80000000 1FC0`, `T12 40400000 1F80`.

**FUZZ-DESIGN §6.1 uncertainty answered:** the port-0xE9 hack is a run-time bochsrc option
(`port_e9_hack: enabled=1`) and works in this build without a configure flag; the shutdown port 0x8900
ends a run cleanly (Bochs reports it as a PANIC-level message by design).

**Guest pitfall found:** without an IDT, any run still executing about 3×10^7 ticks after the BIOS handed
over triple-faulted at a fixed emulated time (tick 184,002,469) [M]. With a minimal IDT the event showed
as vector 8 (`EXC 00000008`) [M]. That is consistent with IF having been set again by the BIOS (for
example across INT 13h) while the 8259 still delivers IRQ0 at its real-mode base vector 8 [inference].
`cli` plus masking both 8259s at stage-2 entry removed it: no event in runs of up to 3×10^7 further
instructions [M]. The production image needs the same.

## 4. Throughput [M]

Wall time of the whole probe (BIOS boot, 12 tests, then LOOPS × {VADDPS zmm0, zmm1, zmm2; DEC; JNZ}),
one host thread, debugger compiled in, `clock: sync=none`:

| LOOPS | wall s | guest ticks at shutdown |
|---|---|---|
| 0 | 0.438 (0.418 and 0.447 in two runs of the image before the 8259 fix) | 181,473,037 |
| 10^6 | 0.550 | 184,473,037 |
| 10^7 | 1.506 | 211,473,037 |

The tick difference is exactly 3 instructions per iteration. Slope [D]: (1.506 − 0.438) s / 10^7 =
**≈ 107 ns per iteration**, i.e. about 9.4 × 10^6 VADDPS zmm per second, about 1.5 × 10^8 f32 lane
additions per second, on the same operands every iteration (SoftFloat cost can depend on the operands;
not measured). FUZZ-DESIGN §5 assumed Bochs 10^3-10^4 times slower than silicon [G]; against an assumed
silicon rate of 10^9-10^10 VADDPS zmm per second [G] the measured raw rate is about 10^3 times slower
[D from M and G]. The planned Bochs budget, 7.5 × 10^7 lane cases [D], is under 1 s of raw arithmetic at
this rate. The cost of a real run will be moving vectors into the guest, the in-guest compare and the
stream hash, which are not built (FUZZ-DESIGN §6.1's 3-5 agent-day item).

## 5. What remains for the second oracle

- The production image: a disk-image vector loader, the same stub bytes position-independent, the in-guest
  compare and the stream hash (FUZZ-DESIGN §6.1). This probe shows the boot path, the AVX-512 state, the
  output channel and the shutdown path work.
- Bochs models Intel parts only (§2), so a Zen 5 behaviour that differs from Intel reads as "Bochs
  differs" in §6.3.
- **Intel SDE was not downloaded.** Its download requires accepting the Intel licence by click-through;
  that is for Pierce (see the track summary). It also still needs the emulation probe of FUZZ-DESIGN §6.2
  before any agreement counts.
