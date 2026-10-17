# X4-noise-pilot: quiet-night noise pilot
Status: DRAFT

ROADMAP anchor: [§3.5](../../ROADMAP.md#35-x4-evaluator-integrity-kit-weeks-06) (X4), §10 (quiet hours); [06 §6.3, §6.6, §6.8](../../architecture/06-forge.md); DR-023; D-22. Design: [MEASUREMENT-SERVICE.md §3, §4, §5.3–5.4, §7](../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md); split out of the [X4-integrity DRAFT](X4-integrity.md) (§3 σ-pilot, §7 pinned rules).

This is a **DRAFT** and a **SMALL** record (revision 2, 2026-10-16/17, after one same-family, independent-context review round, §12). It pre-registers only the σ-pilot: a measurement that **no gate judges**. Its results fill in, by the frozen rules of §7, the data-dependent constants of the measurement service and the quiet-night rate. Under the [collection rule](../README.md#pre-registration-lifecycle-roadmap-1-rule-1-d0-12) **no data may be collected under it** until it is FROZEN and either SIGNED (D0-12) or covered by an explicit Owner instruction. It may make a ROADMAP threshold more precise, never loosen it. Evidence tags: **[M]** measured, **[D]** derived, **[G]** judgment, **[target]** a pre-registered threshold, **[inference]**. Owner decisions are Pierce's and are marked *provisional, pending …*.

**Freeze gate.** This record may be frozen only when every field §3 marks *fixed at freeze* holds a value from the named source (an Owner answer, or the OWNER-QUEUE default registered for it) and the X4-calibration record is FROZEN (§10). After signing, nothing in §3 is chosen; the pre-night amendment carries only the mechanically determined values of § Amendments.

---

## 1. Assumption under test, and what follows if it is false
Strictly, the pilot tests **nothing**: it is descriptive calibration, excluded from every tally ([X4-integrity §3](X4-integrity.md)). Its working premise [G]: on the quiet-machine profile the per-run and per-block noise of a `hearth-c-ref` A/A comparison is small and stationary enough that the e-process horizons `N` and clips `c` derived from it are affordable within ROADMAP §10's quiet hours. **If it is false** (σ_d large, heavy outliers, non-stationary nights), the derived `N` and quiet-hour totals rise. That feeds **owner question 1** of the X4 record and the **D-22** second-box trigger (ROADMAP §9). The pilot never kills and never passes a gate.

## 2. Inputs pinned (sources, commits, versions, machines)
- **Binaries.** A/A: both arms are the identical binary of each run type in §3. Each is identified by the §3 row (source commit, build command, workload) and pinned by its build-closure SHA-256 in the pre-night amendment.
- **Machine.** The desktop DESKTOP-8RS9J1J: Ryzen 9 9950X, 64 GB DDR5, Samsung 990 PRO, Windows 11 Pro 10.0.26200 [M]. **Its clock runs on US Eastern time** [M, `Get-TimeZone`, 2026-10-16], so the 23:00–07:00 PT window is 02:00–10:00 on the desktop clock. Every time in this record is PT; the job wrapper and the session driver convert explicitly. The §5.2 fingerprint per run type is printed by `x4svc fingerprint` and pinned in the pre-night amendment.
- **Service.** The X4 measurement service at its frozen commit (`x4svc.exe`, `x4harness.exe`), having passed the acceptance check of §10.
- **Toolchains (exact build commands; recorded here, not elsewhere).**
  - C: MSVC `cl` 19.44.35229 for x64 [M] via `vcvars64.bat` of Visual Studio 2022 Community, flags `/nologo /MP3 /O2 /W4 /std:c11 /MT /DWIN32 /D_WINDOWS /D_CRT_SECURE_NO_WARNINGS`.
  - Rust: `cargo` 1.91.1 (ea2d97820 2025-10-10) and `rustc` 1.91.1 (ed61e7d7e 2025-11-07), host x86_64-pc-windows-msvc [M]. The build calls `%USERPROFILE%\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\cargo.exe build -j 3 --release` by absolute path, with `CARGO_TARGET_DIR` and `CARGO_HOME` on D:. It refuses to build unless `rustc -V` prints the version above. The repository-root `rust-toolchain.toml` pins 1.99.1 on the GNU host for `mithi`; a rustup-proxy `cargo` from a full checkout would pick that toolchain instead and give a different binary hash, so it is not used.
- **Schedule seed.** `seed` = the first 16 hex digits of SHA-256(`"X4-noise-pilot"` ‖ the freeze-commit hash as 40 lowercase hex). It fixes each session's ABBA/BAAB draws and the session order (§6).
- **Statistics code.** The functions named in §4–§5 in `experiments/x4-integrity/service/orchestrator/src/stats.rs` at the frozen service commit.

## 3. Arms / configurations
A **block** is one A/B comparison in randomised ABBA/BAAB order (4 runs). A **run** is one arm to its stopping point. Both binaries are **trusted C** (`hearth-c-ref` at b5d3f14), so the pilot runs in the sandbox's **degraded-job-only** mode (`x4svc selftest` without `--sealed` prints `mode: degraded-job-only`, `hearth-c-ref: RunDegraded` [M, 2026-10-16]). It needs no AppContainer, `MithrilMeasure` user or firewall rule.

**Run-type identities.** The microbenchmark below is the exact binary and kernel the X4 A/A calibration uses; the X4-calibration record must name the same row, or this pilot does not cover it.

| Field | `mb-q4-avx512` (microbenchmark) | `e2e-decode` (end-to-end) |
|---|---|---|
| Source | Hearth clone `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220` (read-only); the `hearth_core` matvec kernel table | same commit; the public `hearth.h` API (`hearth_open`, `hearth_eval`), greedy loop as `engine/tools/hearth_bench.c` at b5d3f14 |
| Harness | `x4harness.exe` linked with the Hearth workload set (built by the X4 track; §10) | same |
| Kernel / work | `matmul[Q4]` of the AVX-512 table, shape of `x3_bench` (X3 DESIGN §8.2: n = 4096, 240 rows × 2,176 B, activations 64 × 72 B, T = 1, seeded fill as `test_quant.c:1452-1456`); K calls per run | prompt = `hearth_bench`'s 32 LCG-seeded token ids (seed 1); then **N = 2,048** greedy decode tokens [target] |
| Stopping point | K calls, K fixed in the pre-night amendment as ⌈10 s / median per-call time of 3 dry runs of 2^16 calls⌉ (dev runs, not pilot data) | N decode tokens |
| Output hashed | Y (240 × 4 B) | the logits of the last token (vocab × 4 B) |
| Model file | none | *fixed at freeze from C02*; default (registered if unanswered): the existing Qwen3-30B-A3B Q4 `.hearth` file on the 990 PRO, opened read-only. Never the USB HDD |
| Environment block (besides `SystemRoot`, `TEMP`, `TMP`) | `HEARTH_ISA=avx512`, `HEARTH_LOG=0` (errors only: `HX_LOG_ERROR = 0`, `hx_platform.h:164` [M, clone]) | `HEARTH_ISA=avx512`, `HEARTH_LOG=0`, `HEARTH_THREADS`, `HEARTH_IO_THREADS`, `HEARTH_CACHE_GB`: *fixed at freeze* with the placement below |
| Warm / cold | warm (inputs in L2 after the harness's fill; no I/O) | cold: direct I/O (`direct_io = 1`), so the Windows standby list never holds model bytes between runs (MEASUREMENT §3) |
| Affinity (job mask) and declared threads | one logical processor `p` on CCD0, its SMT sibling idle; `p` = the first LP of the second physical core of CCD0 as `GetLogicalProcessorInformationEx` reports it (mask printed and pinned in the pre-night amendment); declared threads 1 | *conditional on C01, recorded at signing*: if C01 = lift inside windows, all LPs except the orchestrator's reserved LP on CCD1; otherwise **`e2e-reduced-8t`**: 8 LPs on CCD0, `HEARTH_THREADS` + `HEARTH_IO_THREADS` = 8. Declared threads = `HEARTH_THREADS` + `HEARTH_IO_THREADS` |
| Priority class | `NORMAL_PRIORITY_CLASS` (MEASUREMENT §7.6 [target]) | same |
| Orchestrator | `x4svc` reader thread on one reserved LP on CCD1 | same |
| Sessions × blocks [target] | 20 × 24 (480 blocks) | 3 × 12 (36 blocks) |

Open before freeze (each blocks the freeze, none is chosen after signing): C02 (model path), C01 (placement and the three `HEARTH_*` values), C25 (if the answer is "X3-local calibration", the microbenchmark row is re-derived from the X4-calibration record's microbenchmark). One conflict for the lead engineer: X3 DESIGN §8.2 runs `x3_bench` at `HIGH_PRIORITY_CLASS`, X4 at `NORMAL_PRIORITY_CLASS`; under the C25 default the two records must agree before either freezes.

**Bracket in the pilot (observe mode).** The pilot estimates the integrity tolerances, so it must not be censored by placeholder values of them. Each pilot-derived tolerance runs **at its hard ceiling** below; the observed value is recorded per run; a run whose value exceeds the ceiling is an integrity failure (it stops the pilot as now, §10):

| Tolerance (per run type) | Recorded per run | Hard ceiling in the pilot [target] |
|---|---|---|
| τ_clock | \|Δ_h − Δ_o\| | 0.1% of Δ_o (the X4 cap) |
| κ_post (process cycles after STOP) | `cycles_exit − cycles_stop` | 2.0 × 10⁹ cycles (≈ 0.47 s of one core at the orchestrator-calibrated 4.296 × 10⁹ cycles/s [M]; dev runs of 4 KB output measured 0.47–0.96 × 10⁹ [M, 2026-10-16]) |
| ε_spin, ε_idle (post-`t1` per-thread CPU beyond the 50 µs pool spin) | the harness's largest post-`t1` cycles per class | ε_spin ≤ 50 µs, ε_idle ≤ 1 ms of CPU, at the calibrated rate |
| init_max (launch → START: wall, process cycles) | `start_ns`, `cycles_start` | microbenchmark 2 s and 8.6 × 10⁹ cycles; end-to-end 120 s and 120 s × declared threads × the calibrated rate [G] |
| extra cores in [START, STOP] | (cycles_stop − cycles_start) / (Δ_o × rate) − declared threads | 0.25 core |

Every other check (protocol order, the orchestrator's copies and hashes, poison, the trailing page, MXCSR, census, affinity/priority, exit code, workload status) is enforced exactly as in a calibration. Running "at the ceiling" needs a pilot setting of the service that the v0 CLI does not yet have (the τ_clock floor is 1 ms there); it is an acceptance item (§10).

## 4. Units and counting rules (defined before data)
- **Run type**: a §3 column. Every estimator is per run type; nothing is pooled across run types.
- **σ̂_d** (per run type): the root mean square of the A/A block statistic `d = ln(T_B/T_A)` **about the null mean 0**, over all non-discarded blocks of all non-voided sessions of that run type; `B` = that block count; `df = B` (the mean is known, not estimated: identical binaries, randomised order). Function: `stats::rms_about_zero`. Between-session variation stays in σ̂_d because the e-process sees it. This is the X4-integrity §7 / MEASUREMENT §5.4 quantity ("pooled SD of the pilot's A/A block d") made precise, not the within-session SD.
- **σ̂_U** = σ̂_d · √(B / χ²₀.₁₀,B): the one-sided 90% upper bound, `stats::sigma_upper_90(σ̂_d, B)`.
- **σ̂_run**: the pooled within-(session, arm) SD of per-run ln(ns), `df = Σ(n_g − 1)`, `stats::pooled_sd`.
- **Pilot incumbent median**: the grand median of per-run ln(ns), by run type.
- **t_run**: per-run Δ_o (ns); its median and 1st/99th percentiles by run type. All quantiles in this record are **nearest-rank**: the ⌈p·n⌉-th smallest value, `stats::quantile_nearest_rank`.
- **Per-run slow-outlier rate and p0** (two passes): pass 1 computes σ̂_run and the pilot incumbent median from all non-discarded runs; pass 2 replays the R scorer per session in run order with `c_run = 4·σ̂_run` and the pass-1 median as the reference before an arm has history, and counts slow flags. p0 = the one-sided 95% Clopper–Pearson upper bound of that rate (`stats::clopper_pearson_upper`).
- **Void and discard rates**: discarded blocks ÷ attempted blocks; voided sessions ÷ attempted sessions, by tier (§10).
- **Counted set**: every non-discarded block of every non-voided session. The pilot has no gate, so there is no "first 100" rule.
- **Descriptive only**: the within-session SD of d (`stats::pooled_sd` over sessions) and s_between, the SD of session means of d.

## 5. Metrics: primary, secondary, descriptive
- **Primary (the pilot's deliverables; none is a gate input):** σ̂_d, B and σ̂_U; σ̂_run and the pilot incumbent median; t_run (median, 1st/99th); the slow-outlier rate and p0; the maxima of every §3 observe-mode quantity (|Δ_h − Δ_o|, post-STOP cycles, post-`t1` spin and idle cycles, init wall and cycles, extra cores); the §4.1 start-state envelopes (package temperature and effective clock, modified-page bytes) and the pre-run 2-s CPU load distribution; the productive block-hours per night and the void and discard rates with causes.
- **Descriptive:** the full per-run and per-block record; S3/S4 statistics; the S4 grand median and s_between; the within-session SD of d; the carry-over contrast `co_BA − co_AB` with its SE; temperature and NVMe SMART traces.

## 6. Sample, schedule and quiet-hour fit
480 microbenchmark blocks give σ̂_d a relative SE ≈ **3%** under normality [D: 1/√(2·480)]; 36 end-to-end blocks ≈ **12%** [D]. No power claim: the pilot estimates, it does not test.

**Quiet-hour fit [D from G].** Microbenchmark: 20 × 24 × 4 = 1,920 runs × ~10 s = 5.3 h. End-to-end: 3 × 12 × 4 = 144 runs × ~120 s × cool-down factor 1.5 = 7.2 h. Per-run overhead (2-s load sample, 1-s disk-write check, process launch) ≈ 3 s [G]: 1.6 h + 0.1 h [D]. Session set-up ~120 s × 23 sessions = 0.8 h. Total ≈ **15.0 h** [D from G], at ≈ 5–6 productive h per night [G].

**Nights and order.** Pierce's answer gives 4 pilot-week nights (D0-10d, *provisional, pending ratification*). The pilot uses pilot-week nights 1–3; night 4 is `mithc profile measure` or, if the pilot is incomplete, a fourth pilot night. Sessions run in the order the seed (§2) draws over the 23 sessions; a voided session's slot goes to the next unrun session. **No session starts unless its planned end (blocks × 4 × t_run,plan × c + 120 s) is no later than 06:45 PT.** A session cut by 07:00 PT is a hygiene void. After the last pilot-week night the estimators are computed on whatever non-voided blocks exist; σ̂_U widens automatically with a smaller B. If fewer than **240 microbenchmark blocks or 2 end-to-end sessions** exist, the pilot is incomplete and continues only on nights Pierce re-signs.

## 7. Analysis procedure (deterministic, named) and the two frozen rules
All estimators are the functions named in §4 at the frozen service commit, run over the pilot's raw per-run records after the night's void log is closed and hashed (§10). The outputs enter X4 by two rules fixed here:

**(a) Fill-in rule.** By a dated *post-pilot amendment to this record* (cited by the X4-calibration record, which must be FROZEN before the first pilot night and names these values as its inputs):
- `n = max(6, ⌈12·σ̂_U²/δ²⌉)`, `δ = 3%`, `N = 2n`; `c = max(3σ̂_d, 2·m_NI)`, `c_kill = max(3σ̂_d, m_kill + 3σ̂_d)`, `c_run = 4·σ̂_run`; p0 as §4; the S4 grand median and s_between; the §4.1 envelopes per the MEASUREMENT §4.1 table.
- Every §3 observe-mode tolerance = **2 × its maximum over non-voided nights**, per run type, with τ_clock also floored at 1 ms: τ_clock, κ_post, ε_spin, ε_idle, init_max (wall and cycles) and the extra-core slack (floored at 0.05 core). **A value above its §3 ceiling is a design revisit before collection, never a loosened constant.**
- Load-gate threshold = min(40%, the pilot's nearest-rank 99th percentile of pre-run 2-s load + 2 pp).

**(b) Rate rule: pilot σ̂ → nights per week (re-signed).** A closed formula with fixed inputs; Pierce re-signs the computed number, he does not choose its inputs.
- `N_rt = 2·max(6, ⌈12·σ̂_U,rt²/δ²⌉)` per run type `rt`; `t_rt` = the pilot's median t_run [M]; `c_mb = 1`, `c_e2e = 1.5`; per-run overhead 3 s [G] added to `t_rt`.
- `H_cal = 1.25 × [ 100·N_mb (A/A, to N; C05 default) + 2 × 100·(N_mb + 2 + ⌈N_mb/6⌉) (planted 3% and 4%, to N, with calibration and sentinel blocks) + 20·N_mb (A/A′) + 10·N_mb (positive control) + 2 × 256 (long runs) + 8·N_mb (X3 microbenchmark tests, PLAN §6.2) ] × 4 × t_mb × c_mb + 1.25 × [ 20·N_e2e (end-to-end A/A, to N; C05 default) + 2·N_e2e (X3 decode guard, PLAN §6.2) ] × 4 × t_e2e × c_e2e`, in hours. Blocks count toward N as A/B block time only (C29 default). The 25% contingency is OWNER-QUEUE A17's default, *provisional, pending A17*.
- `usable_h` = the pilot's median productive block-hours per non-voided night [M], capped at 8; `void_rate` = the pilot's hygiene-void rate by block-hours [M]; `weeks` = whole weeks from the first calibration night to the end of W10 under Plan B (the operative cadence, OWNER-QUEUE conventions), or W6 if the signing names Plan A.
- `nights_per_week = clamp(⌈H_cal / ((1 − void_rate) × usable_h × weeks)⌉, 4, 7)` [target]. If the unclamped value exceeds 7, that is recorded as a D-22 trigger fact and X4 waits (amber, ROADMAP §3.7); the schedule is not loosened and ROADMAP §10 is not changed.
- Any C05/C29/A17 answer that differs from the default registered here changes this formula only by a pre-data amendment signed before the pilot's σ̂ is known.

The Gatekeeper (deterministic code + Owner key) records the fill-in and the rate; agents run the scripts and write the dossier, never judge (ROADMAP §1 rule 3).

## 8. Outcomes
The pilot has **no pass/amber/kill**; it is excluded from every gate ([X4-integrity §3, §10](X4-integrity.md)).
- **Produced:** the §5 estimators enter the two rules of §7. σ_d per run type is the M0 deliverable ([06 §6.6](../../architecture/06-forge.md)); it is estimated **only** from runs that reached their stopping point.
- **D-22 feed:** an unclamped rate above 7, or a high void rate, is a D-22 fact (ROADMAP §9); this record states facts, it does not decide.
- **Incomplete:** as §6.

## 9. Threats to validity and how each is handled
- **Non-stationary nights fake low or high σ_d.** Randomised ABBA/BAAB; S3/S4 reported; between-session variation is kept in σ̂_d because the e-process sees it (§4).
- **Carry-over within a night.** The §4.1 per-run start-state gate and the carry-over contrast; a gate timeout discards the block (§10).
- **Interactive use, GEMS or a stray job in the window.** The §10 sensors void the session; the job wrapper refuses Mithril starts inside a window; GEMS is a co-tenant Pierce keeps out (D0-10d). Whether GEMS counts as "the Owner's own use" for D-22 is open (A18 / D0_BRIEF Q7).
- **Censored tolerances.** Observe mode up to stated ceilings (§3).
- **Selection through voids.** Discard and void decisions are computed by a sensor-only function that never receives run times or d (§10).
- **Profile not applied.** `x4svc verify-profile --collection --pins` refuses the night on any mismatch; the service never changes a setting.
- **Circularity.** The pilot's constants are used by the *later* calibration only.

## 10. Deviation, void tiers, dependencies
**Three tiers, matching MEASUREMENT §5.3.** Every discard and void is computed by the scheduler's sensor-only function, which never receives run times or d. The night's void log is closed and its SHA-256 recorded before any estimator runs. The statistical voids S1–S4 are **not applied** in the pilot (S1 has no sentinels in pure A/A; S2 and S4 need the pilot's own outputs); S3 and S4 are reported.

| Tier | Trigger (detector; number [target]) | Effect |
|---|---|---|
| Night refusal (pre-start only) | `verify-profile --collection --pins` not MET; `selftest` mode not `degraded-job-only` | no session starts that night |
| Block discard | 2-s pre-run CPU load ≥ 40% (the ROADMAP/Hearth value; the pilot-derived threshold applies from the calibration on); §4.1 start-state not reached within 60 s (absolute items only in the pilot: disk queue 0 and writes ≤ 1 MiB/s over 1 s; temperature and clock recorded, not gated); `MsMpEng`, `SearchIndexer` or `TiWorker` CPU > 1% of one core averaged over [t0 of the first run, t1 of the last run] [G] | block not scored; 3 or more discards in a session make it a hygiene void |
| Session hygiene void | any `GetLastInputInfo` change or a new console/RDP session; any process from the pinned excluded list starting or using CPU in the window: agent and build images (`claude`, `node`, `cl`, `link`, `cargo`, `rustc`, `python` other than the driver), the local Qwen3 server, `vmmemWSL`/`wsl`, the GEMS images Pierce lists at signing, and the launchers observed on the desktop (`OneDrive`, `Overwolf`, `CurseForge`, `EpicGamesLauncher`) [M, 2026-10-16]; GPU utilisation > 5% [G]; NVMe SMART composite temperature ≥ 70 °C at a block start [G]; a session cut by 07:00 PT; any Mithril job other than this pilot's orchestrator and harness, or Mithril threads above the §3 placement | session removed from the estimators, counted in the void rate, its slot re-used (§6) |

A night with any **integrity failure** (the service's own bracket, census or hash) is not a void: it stops the pilot as an evaluator bug until fixed, never re-run silently. A service fix that changes any pinned hash discards all earlier pilot blocks (restart); a fix that changes no pinned hash keeps them.

**Dependencies (all before the first pilot night).**
- This record SIGNED (D0-12) and the **X4-calibration record FROZEN** (commit named), with C01, C02, C05, C24, C25 and C29 answered or their OWNER-QUEUE defaults registered (OWNER-QUEUE, "Moved earlier by R5").
- **D0-7a = YES** (unattended runs). *If D0-7a is not YES, the pilot does not run; its nights move to the week after the sitting that signs it.* (Attended nights do not work here: presence that touches the machine voids the session.)
- D0-10d ratified (*provisional, pending ratification*); the **job wrapper live** (PLAN B13, from 10-23).
- The Hearth workload set for `x4harness` (§3) built from b5d3f14 by the X4 track and hashed. Not yet built [M: IMPLEMENTATION.md].
- **The service's acceptance check**, extended beyond unit, golden and `dev_*` tests: (a) a dry night on dev workloads that drives full ABBA/BAAB sessions through the session engine, outputs discarded; (b) each §10 sensor shown firing on a planted trigger (none exists in v0 [M: grep of `service/`, 2026-10-16]); (c) `verify-profile --collection --pins <committed pins file>` reporting MET (the `--pins` input and `x4svc fingerprint` exist since 2026-10-16 [M]); (d) the observe-mode pilot setting of §3.

## 11. Pre-night checklist (Pierce runs these; the service only verifies)
The service changes **no** system settings ([06 §6.7](../../architecture/06-forge.md)). Facts read from the desktop on 2026-10-16 [M]: active plan Balanced `381b4222-f694-41f0-9685-ff5bb260df2e`; Windows Update active hours 06:00–00:00 **desktop (Eastern) time**, so restarts are allowed 00:00–06:00 ET = 21:00–03:00 PT, overlapping the window; no maintenance `Activation Boundary` set (Windows then uses its default, 02:00 local [inference] = 23:00 PT, the window's start); WSL running (`vmmemWSL`, `wslservice`); `%TEMP%` on C:; `D:\mithril-data` absent.

**One-time (elevated where noted).**
1. Measurement plan and core parking (elevated): `powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c` (record the printed GUID), `powercfg /changename <GUID> MITHRIL-MEASURE`, `powercfg /setacvalueindex <GUID> SUB_PROCESSOR CPMINCORES 100`, `powercfg /setacvalueindex <GUID> SUB_PROCESSOR CPMAXCORES 100`. Whether the plan stays active 24/7 or is switched nightly is Pierce's choice, *provisional, pending his answer at signing* (24/7 changes GEMS's daytime power and heat).
2. Data directory: `mkdir D:\mithril-data`; Defender exclusion (elevated; a security trade-off, Pierce's call): `Add-MpPreference -ExclusionPath 'D:\mithril-data'` and, if he agrees, `D:\mithril\x4b`. Search indexer: remove `D:\mithril-data` in Control Panel > Indexing Options. **v0 does not verify the indexer.**
3. Windows Update: set active hours to cover the window, e.g. 20:00–14:00 desktop time (= 17:00–11:00 PT, the 18-h maximum), in Settings > Windows Update > Advanced options; or pause updates for the pilot week there.
4. Maintenance: read `Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\Maintenance'`; if no `Activation Boundary` is set or it falls in 02:00–10:00 desktop time, move automatic maintenance outside that range in Control Panel > Security and Maintenance > Automatic Maintenance.
5. After the lead engineer commits the pins file: nothing further; the service reads it.

**Nightly, by 22:50 PT.**
1. GEMS jobs and the GPU queue stopped; the launchers listed in §10 closed.
2. `wsl --shutdown`.
3. If the plan is switched nightly: `powercfg /setactive <MITHRIL-MEASURE GUID>` (and in the morning `powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e`).
4. `x4svc selftest --harness <x4harness.exe> --probe-exe <x4sb_probe.exe> --scratch D:\mithril-data\x4` → expect `mode: degraded-job-only`.
5. `x4svc verify-profile --collection --pins <committed pins file> --scratch D:\mithril-data\x4 --affinity <run type mask> [--env K=V]...` → expect `collection: MET`, once per run type.
Every `x4svc run` passes `--scratch` on `D:\mithril-data` (the CLI refuses without one since 2026-10-16 [M]).

## 12. Review log (independent reviewers, with model family)
ROADMAP asks for a **different model family**; this setup has only Claude, so reviews are logged as **same-family, independent-context**, which is weaker than the requirement (see [m0/README](../README.md)).

| Date | Reviewer (lens) | Family | Scope | Findings (blocker / major / minor) | Accepted | Rejected |
|---|---|---|---|---|---|---|
| 2026-10-16/17 | Reviewer 2 (pilot design: units, tolerances, rate rule, estimators, voids, stopping, dependencies, checklist, cap, amendments, toolchain, signability) | Claude (same family, independent context) | this record | 13 (3 / 6 / 4) | 13 | 0 |
| 2026-10-16/17 | Reviewer 1 (evaluator integrity of the service this record runs on) | Claude (same family, independent context) | the service; affects §3 and §10 here | 6 (1 / 3 / 2) | see [IMPLEMENTATION.md](../../../experiments/x4-integrity/IMPLEMENTATION.md) | |

Disposition (reviser, Claude, same family, independent context from both reviewers; every finding checked against the sources and, where it named the desktop, re-read there):
- **Units not fixed (blocker):** accepted; §3 identity table; fields that depend on open Owner answers block the freeze instead of being chosen after signing.
- **Tolerances censored by placeholders (blocker):** accepted; §3 observe mode with hard ceilings, extended to the three new out-of-process tolerances; §7(a) uses 2 × the maxima throughout; "99.9th percentile" removed. MEASUREMENT §3 step 8a still says 2 × p99.9: builder note for the design's owner (that file is outside this track).
- **Rate rule open to choice (blocker):** accepted; closed formula in §7(b).
- **σ̂_d redefined as within-session SD (major):** accepted; σ̂_d is the RMS about 0, df = B (`stats::rms_about_zero`, new); `sigma_upper_90` now takes df explicitly; within-session SD is descriptive only.
- **Void rules (major):** accepted; three tiers with detectors and numbers; S1–S4 not applied; blindness and void-log hashing stated; the sensors are acceptance items.
- **Unbounded stopping, overheads (major):** accepted (§6). Precision: the reviewer's 1.6 h overhead is for the 1,920 microbenchmark runs; the end-to-end adds 0.1 h.
- **Dependencies (major):** accepted (§10).
- **Checklist (major):** accepted, with one correction: the desktop clock is US Eastern [M], so active hours 06:00–00:00 allow restarts 21:00–03:00 PT (not 00:00–06:00 PT); the overlap with the window, and so the finding, stands. `--pins` and `x4svc fingerprint` were built and exercised this round [M].
- **Thread cap (major):** accepted; placement conditional on C01; §10 trigger reworded.
- **Amendment governance, toolchain, quantiles and passes (minor):** accepted (§2, § Amendments, §4).
- **Signability (minor):** accepted as a scheduling note: the record stays DRAFT (track rule) and is ≈ 180 lines; whether it can be frozen for the 10-17 packet depends on C01/C02/C25 and the X4-calibration freeze, so OWNER-QUEUE item 3b should be read as 10-25 unless those land first [inference].

## 13. Signature block
```text
Owner: ______________________   Date: __________
Signs the record frozen at commit: ________
Records at signing: C01 answer (placement) ______  plan active 24/7 or nightly ______  GEMS image names ______
Also re-signs, after the pilot: the nights-per-week figure computed by §7(b).
```

## Amendments (appended, dated)
_None yet._ Two kinds are pre-registered here:
- **Pre-night amendment (before the first night; no new signature).** It may contain only mechanically determined values: the build-closure SHA-256 of each §3 binary built by the §2 commands (the hash of the files that will run: the MSVC build as configured is not bit-reproducible [M, IMPLEMENTATION.md], so a later rebuild is a new pin and a new amendment); the fingerprint and pins-file lines printed by `x4svc fingerprint` per run type; the environment-block SHA-256 per run type; the LP `p`, its mask and K by the §3 rules; the seed by the §2 rule. Any other change is a new record.
- **Post-pilot amendment.** The §5 estimators, the §7(a) values and the §7(b) computation, dated, with the void log's hash; the X4-calibration record cites it.
