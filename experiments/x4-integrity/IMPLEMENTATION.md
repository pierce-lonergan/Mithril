# X4 measurement service v0 + sandbox prototype — implementation notes

**Track:** x4-integrity (x4svc). **Status:** v0 built, unit-/golden-tested and end-to-end demonstrated on
the desktop after two review rounds (round 2: 26 findings, 3 blockers; round 3, 2026-10-16/17: 19
findings, 4 blockers, see the end of this file), each fixed **end to end**; **no gate data collected**.
**Date:** 2026-10-16/17. Author/reviser: X4 track (Claude, same-family, independent context).
Evidence tags: **[M]** measured here, **[D]** derived, **[G]** judgment, **[target]** a pre-registered
threshold, **[inference]**.

This builds the designs in [MEASUREMENT-SERVICE.md](MEASUREMENT-SERVICE.md), [SANDBOX.md](SANDBOX.md),
[DESIGN.md](DESIGN.md) and [HACK-SUITE.md](HACK-SUITE.md). It changes **no** system settings and runs
**none** of the sealed catalogue (a) hacks, no A/A or planted-regression calibration, and no Hearth
benchmark. It exercises the machinery with the track's own `dev_*` probes on synthetic workloads only,
recorded as **non-gate**.

## Trust classes (new; review finding R1-5/R2-10, the lane distinction)

Every run-acceptance check now carries its evidence class (`proto::TrustClass`), and the verdict names
the class of each failing check:

- **Out-of-process** — computed in the orchestrator, where no workload code runs: the QPC START/STOP
  bracket, the child's `QueryProcessCycleTime` sampled at START/STOP/exit, the orchestrator's own copy
  and SHA-256 of the output section taken **when STOP is decoded** and again after exit, strict frame
  order, the exit code, and the bytes before the extent. These are the only checks that count as
  detector evidence for an **untrusted** workload.
- **In-process** — a field the C harness computed inside the child, which shares its address space with
  the workload (census, MXCSR, affinity/priority, poison residual). Precise for a cooperative workload,
  **forgeable** by an adversarial one; the backstop is the out-of-process bracket and, at M4, binary T0.
  The frames themselves are written from that address space: a workload can forge the whole stream
  (START, STOP, CENSUS, REPORT) and end the process itself. `dev_forge_frames` does exactly that and
  is **Accepted** when its out-of-process evidence is clean [M] (table below). This is the documented
  trust boundary, not a timing hole, because of the cycle partition that follows.

**Cycle partition (review round 3).** Every CPU cycle of the child, from the resume of its first thread
to its exit, falls in exactly one out-of-process window, each with a bound, wherever the frames land:
- **pre-START** (launch → START receipt): `init_max_ns` wall and `init_max_cycles` process cycles, so
  work moved into the untimed init, or before `main`, is bounded;
- **timed** (START → STOP receipt): at most `declared_threads + extra_cores` cores' worth of cycles per
  wall-second, at a rate the orchestrator calibrates itself (`QueryThreadCycleTime` against QPC on its
  own thread, ≈ 4.296 × 10⁹ /s on this box [M]); so threads that do parallel work and exit before the
  census still count;
- **post-STOP**: `kappa_post_cycles`, a coarse ceiling (it must exceed the harness's own census and
  hash, 0.47–0.96 × 10⁹ cycles on 4 KB dev runs [M]); never cited as the fine a3b detector.
The output must equal the golden in the orchestrator's **own** copy taken at STOP receipt, so a forged
early STOP cannot shorten the timed window below the work that produced the output.

## Language split (as the design specifies, section 2)
- **C11 harness** (`service/harness/`, MSVC `cl` 19.44 [M]): the precise clock (`hx_now_ns` QPC at
  b5d3f14), thread wrapper, join of registered threads/parked workers/overlapped I/O, post-`t1` census
  (`CreateToolhelp32Snapshot` + per-thread `GetThreadContext` MXCSR, `GetThreadGroupAffinity`, priority,
  cycle counts), poisoned allocations with a guard page, output rehash (BCrypt), output view frozen
  `PAGE_READONLY` at `t1` under SEH. The **precise** record, not the trusted one.
- **Rust orchestrator** (`service/orchestrator/`, `cargo`/`rustc` 1.91.1 MSVC [M], no third-party
  crates): the supervisor and the **trusted out-of-process bracket**. Protocol **v2** throughout.
- **Python** only offline: the calibration reference `stats/x4_calibration.py` (unchanged; its sha stays
  pinned) and the dev driver `service/tools/x4_devcheck.py`.

## What is built and verified [M, desktop DESKTOP-8RS9J1J 9950X, 2026-10-16; MSVC + cargo, 3 threads, CUDA_VISIBLE_DEVICES=-1, artefacts on D:]

### Rust orchestrator — protocol v2 and the run contract (`proto.rs`, `sandbox.rs`)
- **Strict frame order** (`proto::SeqValidator`, online, and `validate_sequence`): a measured run is
  exactly HELLO(0) START(1) STOP(2) CENSUS(3) REPORT(4), or a prefix + one FAIL; any duplicate,
  reorder, bad seq, wrong payload size or extra frame is an **out-of-process** integrity failure. A
  `Framer` holds frames split across pipe reads (no mis-stamping; review R1-2).
- **STOP-time sampling** (`sandbox.rs` reader thread): the moment a STOP frame is decoded, the
  orchestrator samples `QueryProcessCycleTime`, copies the output extent and SHA-256s the copy, and
  counts residual poison — not at pipe EOF (review R1-1/R2-1, the empty-window blocker). CPU after STOP
  is charged **in cycles** against `kappa_post` (review R2-2); job accounting is a coarse secondary.
- **The bracket** (`decide_run`): `|Δ_h − Δ_o| ≤ τ_clock`, with `τ_clock = max(1 ms, 2·pilot max)` and,
  if that floor exceeds 0.1 % of Δ_o, the run is **ineligible** (`bracket_too_short`), the stricter
  reading — never a loosened tolerance (review R1-6/R2-3). START/STOP both required; `t1 ≤ t0` rejected;
  exit code must be 0; the orchestrator's STOP copy must equal its exit copy, the harness hash and the
  golden (review R1-7). Every check runs; Accept only if none fails; all failures are reported.
- **Watchdog**: the job is terminated at a time cap; a run capped **before** STOP is `TimeCapped` (a
  slow outlier, section 8.7), after STOP is an integrity failure.
- **Reduced-rights section + explicit environment + fresh scratch** (review R2-8): the child gets the
  section through a handle duplicated with only `SECTION_MAP_READ|WRITE`; an explicit, sorted,
  byte-identical environment block (`runenv.rs`, SHA-256 in the record) and a fresh scratch directory as
  its cwd. RAII handle guards; `SetInformationJobObject` checked in the self-test launcher (review R1-8).
- **Round 3 additions** (`proto.rs`, `sandbox.rs`, `main.rs`):
  - HELLO receipt and the first-thread resume are stamped; `decide_run` gains `pre_start_wall`,
    `pre_start_cycles` and `window_cores` (all out-of-process). `window_cores` is evaluated only where
    the bracket is eligible: on µs windows the cycle sampling skew alone gives 0.8–0.9 "cores" [M].
  - The trailing page after the extent must stay zero in the orchestrator's own view (a pagefile-backed
    section starts zero-filled): the child's no-access guard can be lifted by the child, so it is not
    relied on (`outside_changed`).
  - The child inherits **exactly two handles** (the pipe's write end and the section) through
    `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` in both launchers (run and self-test).
  - `x4svc run` requires `--scratch` (no `%TEMP%` default, which is on C: on the desktop [M]), wipes
    and recreates `<scratch>\run` before each pass and **refuses to start unless it is empty**; a
    failed cleanup is reported. New options: `--threads` (declared threads), `--param`, `--env K=V`
    (pinned variables, e.g. `HEARTH_*`), `--dev-canary` (dev only).
  - `x4svc fingerprint --scratch D [--affinity M] [--env K=V]...` prints the §5.2 fields and SHA-256 and
    the two pins-file lines; `verify-profile --collection --pins FILE` loads a strict pins file
    (`profile::parse_pins`) and checks the plan GUID and the fingerprint of the run type. The
    fingerprint changes with the job affinity (`0dec56c7…` at mask 0x1, `95abf0b0…` at 0x2 [M]).
- **`sha256.rs` wired in**: the orchestrator's rehash, env-block hash and fingerprint hash use the
  dependency-free FIPS-180-4 implementation (FIPS vectors + the 1 M-'a' vector pass [M]); it is a
  **different** implementation from the harness's BCrypt, so harness-hash == orchestrator-hash compares
  two independent computations.

Demonstrated end to end with `x4svc run` driving the Job Object + bracket [M, 2026-10-16 ≈ 21:00 PT, final
round-3 binaries; "round 2" = the previous `x4svc.exe`, kept as `x4svc_r2.exe`, with the same harness]:

| run | round 2 | round 3 | on which detector |
|---|---|---|---|
| `dev_sleep_long` (1.1 s, clean) | Accept | **Accept** | — (\|Δ_h−Δ_o\| ≈ 3 µs; pre-START 68 ms / 0.27 × 10⁹ cycles; 0.000 cores; post-STOP 0.48 × 10⁹) |
| `dev_init_precompute` (1.5 s busy in init) | **Accept** | IntegrityFail | **pre_start_wall** (1.57 s) + **pre_start_cycles** (6.7 × 10⁹) [OOP] |
| `dev_forge_frames` (whole stream forged from init, no precompute) | Accept | **Accept** | none: in-process record forged; every cycle in a bounded window (pre-START 49 ms, 0.000 cores, post-STOP 5.7 × 10⁶) |
| `dev_forge_frames --param 1500` (precompute before the forged START) | — | IntegrityFail | **pre_start_wall** + **pre_start_cycles** [OOP] |
| `dev_par_exited` (2 raw threads joined inside run()), declared 1 | **Accept** | IntegrityFail | **window_cores** (2.00 cores > 1 + 0.25) [OOP]; in-process record clean |
| `dev_par_exited --affinity 1` | — | Accept | 0.994 cores, Δ_o 2.18 s ≈ 2 × 1.10 s: pinning removes the gain |
| `dev_par_exited --threads 2` | — | Accept | 2.00 cores at a declared 2 |
| `dev_handle_canary` (count of inheritable handles in the child) | IntegrityFail, status **129** (29 inherited handles) | **Accept** (exactly 2) | the handle list [OOP launch] |
| `dev_handle_canary --dev-canary` (an inheritable event not listed) | — | Accept, 5 of 5 | not received |
| `dev_guard_lift` (guard page re-protected RW, 128 B written past the extent) | **Accept** | IntegrityFail | **outside_extent_oop** (128 B at STOP and exit) [OOP] |
| `run` without `--scratch` | default `%TEMP%` (C:) | exit 2 | required option |
| `dev_early_stop` (= rev_early_stop) | IntegrityFail | IntegrityFail | **protocol** (forged STOP seq 999) + start_stop [OOP] |
| `dev_main_ftz` (= rev_main_ftz) | IntegrityFail | IntegrityFail | **mxcsr_harness**, mxcsr_threads (a9) [IP] |
| `dev_rc` (= rev_rc) | IntegrityFail | IntegrityFail | **workload_rc** [IP] |
| `dev_aff_narrow --affinity 3` (= rev_aff_narrow) | IntegrityFail | IntegrityFail | **affinity** (a31) [IP] |
| `dev_leak_registered` | IntegrityFail | IntegrityFail | **registered_unparked** + post_t1_cpu (a3/a3b) [IP] (see the harness fix below) |
| `dev_mxcsr_worker` / `dev_mxcsr_joined` | IntegrityFail | IntegrityFail | mxcsr_threads / mxcsr_exit (a9) [IP] |
| `dev_t0_poke` | IntegrityFail | IntegrityFail | **clock_bracket** (a5, \|Δ_h−Δ_o\| ≈ 500 ms) [OOP] |
| `dev_partial_output` / `dev_init_output` | IntegrityFail | IntegrityFail | poison_residual, OOP **and** IP |
| `dev_overflow` | IntegrityFail | IntegrityFail | guard-page **FAULT** + exit_code 0x1 [OOP] |
| `dev_write --golden 00…0` | IntegrityFail | IntegrityFail | **golden_hash** (OOP copy ≠ golden) |
| `dev_write` (25–51 µs) / `dev_parked` (30 ms) | IntegrityFail | IntegrityFail | **bracket_too_short** only (a microbenchmark must be ≥ 1 s) |

The four reviewer probes that were **Accepted** in the round-1 build stay rejected; the four round-3 gaps
that the round-2 build **Accepted** (init precompute, parallel exited threads, lifted guard page, handle
inheritance) are now rejected or closed [M]. `x4_devcheck.py` (the C-harness-only signals): **24/24**
in three consecutive runs [M]; the four new cases assert that the in-process record is **clean** for the
round-3 gaps, which keeps the blind spot explicit.

**Harness fix found while verifying (round 3).** `dev_leak_registered`'s worker spins ≈ 70 ms, so it is
alive at the t1 snapshot but has usually exited by the census; `REGISTERED_UNPARKED` counted only
threads alive at the census and read 0 in 3 of 3 runs of the round-2 harness (one of which also had
no post-`t1` violation, i.e. no in-process signal at all) [M]. The harness now counts a registered,
unparked thread present at the t1 snapshot, the a3 definition ("not joined before t1"): 3 of 3 [M].

### Rust orchestrator — the statistical core (`eprocess.rs`, `stats.rs`, `scheduler.rs`, `session.rs`)
- **e-processes** (`eprocess.rs`): aGRAPA bettor, superiority/NI/kill, pinned hex margins; `theta ∈ [0,1]`
  and finite inputs asserted; the `max(20, 1/alpha_i)` threshold (review R2-6); the R/Rk run reference
  before any history is now the **pilot incumbent median**, not 0.0 (review R2-7), so a first block of
  real log-times is not a spurious outlier; a time-capped run scores as a slow outlier (`try_score`).
  Non-finite d is rejected, never mapped to −c (review R2-13).
- **Differential test** (`tests/golden_diff.rs` + `golden_fixture.rs`, regenerated from the unchanged
  `x4_calibration.py`): the original 24-block golden path **plus four extra sequences (180 blocks)** that
  make every path bet on many blocks (review R2-14), reproduced **bit for bit**; Mann–Kendall/CP/χ²
  reference vectors to ≤ 1e-9/1e-12. All pass [M].
- **Pilot estimators, round 3** (`stats.rs`): `rms_about_zero` is the noise-pilot record's σ̂_d (RMS of
  A/A d about 0, df = B, between-session variation kept); `sigma_upper_90(σ̂, df)` takes df explicitly;
  `quantile_nearest_rank`; χ²₀.₁₀ quantiles checked against Wilson–Hilferty at df 33–480 (the pilot's
  block counts). `pooled_sd` stays for σ̂_run and the descriptive within-session SD.
- **Stats** (`stats.rs`): S1–S4 voids, pooled mean test, exact binomial OC (0.9206/0.1183/0.0113 [D]),
  Clopper–Pearson, tail check, **pilot estimators** `σ̂_d`/`σ̂_U`/`σ̂_run` and the **carry-over contrast**
  (review R2-8/§4.1).
- **Session engine** (`session.rs`, new; review R2-12): run results → ln(ns) log-times → randomised
  ABBA/BAAB from a pinned seed → scorers → e-processes, behind the load gate; **void decisions take only
  sensor/time inputs** (the module never reads wealth) and wealth is logged at every discard/void; an
  integrity failure stops the session; a time cap scores a slow outlier.
- **Quantity** (`quantity.rs`): `Measured` only from a `VerifiedProfile`; `combine_add` succeeds only for
  identical origins, and mixing needs an explicit `weaken` to a named weaker origin — `Measured{A}` and
  `Measured{B}` no longer silently collapse (review R2-10).
- **Profile verifier** (`profile.rs`, `profile_win.rs`): Defender exclusion is **advisory**, not required
  (review R2-16); a **collection mode** refuses until the plan GUID and the §5.2 fingerprint hash are
  pinned; the `Fingerprint` struct has the §5.2 fields, a canonical serialisation and a SHA-256. Live on
  the desktop it reported **NOT MET** on the Balanced plan and printed Pierce's §7.1/7.2 commands, with
  7.3 shown as advisory [M].

### Sandbox self-test (`selftest.rs`, `sandbox/probes/`)
- Fails closed (review R2-11): every expected probe must be present and attempted inside or both classes
  are refused; a sealed file reachable inside refuses both; the Job-only state is **RunDegraded** for
  hearth-c-ref (never a plain Run) and the mode label is carried into the verdict.
- Verified end-to-end on this (un-provisioned) box [M]: `in_job=true`, child creation/breakaway/clear-
  limits/priority/affinity self-elevation all blocked, loopback positive control (deny inside, succeed
  outside), WMI/TaskScheduler reachable (no AppContainer), sealed stand-in reachable → **mode "refused",
  both classes Refuse** — the correct fail-closed outcome until Pierce runs the SANDBOX.md commands and
  the AppContainer launch is wired. Without `--sealed` (the trusted-C noise pilot's nightly check) the
  same box gives **mode "degraded-job-only"**: hearth-c-ref RunDegraded, untrusted Refuse [M, round 3].

## Build and test (desktop, MSVC + cargo, 3 threads, `CUDA_VISIBLE_DEVICES=-1`, artefacts under `D:\mithril\x4b`)
- C: MSVC `cl` 19.44.35229 x64, `/nologo /MP3 /O2 /W4 /std:c11 /MT /DWIN32 /D_WINDOWS
  /D_CRT_SECURE_NO_WARNINGS` → `x4harness.exe`, `x4sb_probe.exe`, **clean at /W4** [M].
- Rust: `cargo` 1.91.1 (ea2d97820 2025-10-10) / `rustc` 1.91.1 (ed61e7d7e 2025-11-07), MSVC host, called
  by absolute path (`…\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\cargo.exe`; the repo-root
  `rust-toolchain.toml` pins 1.99.1 GNU for `mithi` and would otherwise be picked up). `cargo test -j3
  --release` → **62 unit + 4 golden/differential tests pass**; `cargo build -j3 --release` → `x4svc.exe`,
  **no warnings** [M, round 3]. `CARGO_HOME`/`CARGO_TARGET_DIR` on `D:`; WSL not used.
- Dev build SHA-256 (not pins; the noise pilot pins its own build) [M, round 3 final, 21:11 PT]:
  `x4harness.exe` `618afa1fbde4afb96bf1170beac073f7c4dde29b70276b2bf2b8ba9e99bd4c5b`, `x4svc.exe`
  `2c9ea62090d69dd85d668fae6626178957f5e359a36f9b2a250b1a20948c8967`, `x4sb_probe.exe`
  `569fb0baecf9b588088f2ee1a243667203bdc1ff9d02269c5e974a244fe45109`. A comment-only header change
  changed the harness hash: the MSVC build is not bit-reproducible as configured (the linker stamps
  the image) [M], so a pin names the binary file that runs, and a rebuild is a new pin.
- The eight reviewer `spec_*` expectations that failed on the reviewed build (tau_clock cap, missing
  START/STOP, nonzero rc, harness MXCSR, t1≤t0, first-block pilot median, NaN scoring, cross-profile
  Measured mixing) are each now covered by a passing unit test in `proto.rs` / `eprocess.rs` /
  `quantity.rs` [M].

## What does NOT work / honest limitations (carried into the prereg)
- **AppContainer/LPAC launch is still not wired** (the next build step; needs no system change,
  `CreateAppContainerProfile` + `STARTUPINFOEX`). Until it is, the refusal table keeps every untrusted
  workload out (fails closed). **Further prerequisites before any untrusted workload is admitted**
  (review round 3, R1-1; none is needed for the trusted-C noise pilot): (1) inputs that cannot be
  precomputed, i.e. a per-run challenge the orchestrator writes into the input region at START, with
  goldens per challenge from the reference arm, a design change for X4-calibration and the Forge;
  (2) an init budget rule for candidates relative to the incumbent's measured init (the pre-START bound
  now exists, its policy for candidates does not); (3) an out-of-process census (thread list, MXCSR,
  affinity and priority read by the orchestrator), because every in-process field is forgeable. LPAC token-attribute detection is stubbed (`attempted=0`). Large-page +
  direct-I/O inside an AppContainer remain **unverified on this box** [known weakness].
- **The out-of-process post-STOP cycle check is coarse.** On this box the harness's own post-STOP census
  + hash costs **0.47–0.96 × 10⁹ cycles** on 4 KB dev runs [M, round 3], so `kappa_post` must exceed it;
  the cycle window therefore catches only gross overruns. The **fine** a3b detector is the in-process post-`t1` CPU rule (shown firing on
  `dev_leak_registered`, a continuous spinner) plus the STOP-time output rehash. `dev_after_t1`'s
  one-shot 30 ms burst is timing-sensitive and is **not** asserted as a reliable catch.
- **Pilot-derived constants are provisional placeholders**: `τ_clock`, `κ_post` (now in cycles),
  `ε_spin`, `ε_idle`, `init_max` (wall, cycles), the extra-core slack, the clips, `N`, the pilot
  incumbent median and the fingerprint hash are inputs
  carrying dev values until the σ-pilot fills them in by the frozen rule (prereg; the dev demonstrations
  are **not** gate numbers).
- **The noise pilot's "observe mode"** (each pilot-derived tolerance at its hard ceiling, values
  recorded; X4-noise-pilot §3) is not yet a service setting: the v0 CLI's τ_clock floor is 1 ms. The
  §10 hygiene sensors of that record (load, Defender/indexer/Update activity, input, excluded
  processes, GPU, SMART, disk queue) do not exist in v0, and the Hearth workload set for `x4harness`
  is not built. All are acceptance items before the first pilot night.
- **No fingerprint/profile hash is pinned**, so `x4svc run` emits `Estimated`, never `Measured`;
  `--dev-self-golden` grades against the run's own first-pass hash and is a dev convenience only.
- **No full session calibration was run** (that is gate data). The session engine is unit-tested on
  scripted runs, not yet wired to drive real `hearth-c-ref` runs end to end (the A/A loop);
  `mithc profile measure` (STREAM/NVMe), the F1-sim byte counter and the revisit engine are other
  X4 sub-tracks, out of this task's scope.
- Reviews are **same-family, independent-context**; no gate verdict is computed here.
- **F0 line budget** (03 §14, ≤ 1,500 line-reviewed lines [target]): total is 4,980 Rust src lines and
  1,433 C (harness + proto, incl. the non-gate `dev_workloads.c`) [M, `wc -l`, round 3]. Counting
  non-blank, non-`//` lines before `#[cfg(test)]`, the platform-independent **trusted decision core** is
  ≈ **1,607** (`proto` 571, `stats` 305, `eprocess` 245, `session` 170, `scheduler` 102, `quantity` 93,
  `sha256` 88, `runenv` 33), plus `sandbox.rs` 675 (mostly FFI declarations) and `profile.rs` 216 [M].
  Round 3 added ≈ 60 lines to the core. A split and trim under the target remains **future work before
  freeze**, flagged here rather than hidden.

## Review round 2 (2026-10-16): 26 findings, 3 blockers — fixed end to end
Two same-family independent-context reviewers (9 + 17 findings; blockers: empty post-STOP CPU window,
unenforced protocol order, bypassable integrity bracket). All 26 accepted and **fixed end to end** this
round; the C harness was already at protocol v2, and the Rust orchestrator is now v2 and consistent with
it. Evidence that the three blockers are closed [M, desktop, 2026-10-16]: `rev_early_stop` → IntegrityFail
(protocol); post-STOP CPU sampled at STOP in cycles; the bracket's three OOP checks each fire in the
`x4svc run` table above.

## What needs Pierce's one-time commands (no agent runs these; see SANDBOX.md / MEASUREMENT-SERVICE.md §7; summarised in the X4 noise-pilot pre-night checklist)
1. The quiet-machine profile (power plan GUID, core-parking 100/100, Defender exclusion) — §7.1–7.3.
2. `New-LocalUser MithrilMeasure` (SANDBOX §3.3).
3. The sealed-store ACLs (SANDBOX §2.1) and the outbound firewall rule (SANDBOX §3.2).
The service verifies these read-only and refuses on a mismatch; it never applies them.

## Review round 3 (2026-10-16/17): 19 findings, 4 blockers

Two reviewers (Claude, same family, independent context): reviewer 1 on evaluator integrity (6: 1
blocker, 3 major, 2 minor), reviewer 2 on the noise-pilot record (13: 3 blockers, 6 major, 4 minor;
disposition in that record's §12). The reviser (Claude, same family, independent context) checked each
against the code, the Hearth clone and the desktop, and reproduced every reviewer-1 gap with a dev probe
on the round-2 binary before fixing it [M]. **Accepted: 19** (5 of them with a modified fix); parts of
two findings were not adopted (below).

| # | Severity | Finding | Verified | Disposition |
|---|---|---|---|---|
| R1-1 | blocker | Init laundering and a forgeable frame stream let an untrusted workload be Accepted with work outside the timed window | yes: `dev_init_precompute` and `dev_forge_frames` Accepted by round 2 [M] | **Accepted, modified.** (a) adopted and made stricter: the bound runs from the first-thread resume, not from HELLO, so code before `main` is covered too; wall and cycles. The forgery itself is not prevented (it cannot be, in-process); instead the cycle partition bounds every cycle, and the forged stream with precompute is rejected [M]. (b) the per-run challenge is a design change for X4-calibration/Forge and is listed as an admission prerequisite for untrusted workloads, which stay refused. (c) not adopted as written: an orchestrator-defined START does not bound precompute by itself; the pre-START bound does. The OOP census part of (c) is an admission prerequisite |
| R1-2 | major | Parallel work by threads that exit before the census is unbounded out of process | yes: `dev_par_exited` Accepted by round 2 [M] | **Accepted.** `window_cores` with an orchestrator-calibrated rate; job-mask pinning shown to remove the gain [M]; declared threads per run type in the noise-pilot record. The CLI does not force the mask (dev probes need others); the record pins it per run type |
| R1-3 | major | `bInheritHandles = 1` leaks every inheritable handle of the orchestrator into the child | yes: 29 inheritable handles in the round-2 child [M] | **Accepted.** Handle list in both launchers; exactly 2 after [M]; canary not received 5/5 [M] |
| R1-4 | major | Post-STOP cycles sampled at decode undercount; a pipe flood widens the gap | partly | **Accepted in part.** The window stays a coarse ceiling (stated in `proto.rs`, measured 0.47–0.96 × 10⁹ cycles [M]). Cycles between the child's STOP write and its decode are not lost: they fall in the timed window, which `window_cores` now bounds. **Not adopted:** the pipe-flood vector (any byte that is not the next expected frame is a protocol failure under the strict framer, so the reader cannot be kept busy before STOP without failing the run), and the harness pre-STOP cycle snapshot (in-process and forgeable; the in-process post-`t1` rule already covers cooperative workloads) |
| R1-5 | minor | The trailing guard page is checked by nobody; the child can lift it | yes: `dev_guard_lift` Accepted by round 2 [M] | **Accepted.** Trailing page compared to zero at STOP and exit out of process [M] |
| R1-6 | minor | Scratch wipe errors discarded; a dirty scratch could carry state | yes (code) | **Accepted.** Wipe, recreate, require empty, refuse otherwise; `--scratch` required (the `%TEMP%` default was on C: [M]) |
| R2-1…13 | 3 blockers, 6 major, 4 minor | noise-pilot record | yes (sources; desktop facts re-read) | **All accepted** (one with a corrected fact: the desktop clock is US Eastern [M]); code side: `rms_about_zero`, explicit-df `sigma_upper_90`, `quantile_nearest_rank`, `--pins`, `x4svc fingerprint`, required `--scratch`; the comment in `main.rs` now states 2 × the pilot maximum. Builder note for the design owner: MEASUREMENT-SERVICE §3 step 8a still says 2 × p99.9 for κ_post (outside this track's files) |

Found while verifying (not a reviewer finding): the census-only `REGISTERED_UNPARKED` count (fixed
above) and a false positive in the first version of the canary probe (a same-valued, non-inherited
signalled handle in the child; the probe now also requires the inherit flag) [M].

## Files (this track only)
- `service/proto/x4proto.h` — the C↔Rust wire protocol (v2).
- `service/harness/{x4h.h,x4h.c,dev_workloads.c}` — the C harness and the non-gate `dev_*` workloads
  (round 3 adds `dev_init_precompute`, `dev_par_exited`, `dev_guard_lift`, `dev_handle_canary`,
  `dev_forge_frames`; each reads clean in-process and is caught, or bounded, out of process).
- `service/orchestrator/src/` — `proto` (framer, strict order, the run contract, trust classes),
  `eprocess`, `stats`, `scheduler`, `session`, `quantity`, `profile`, `selftest`, `runenv`, `sha256`;
  `sandbox`, `profile_win` on Windows; `tests/{golden_diff,golden_fixture}.rs`; `src/main.rs` CLI.
- `service/tools/x4_devcheck.py` — the dev self-test driver (non-gate).
- `sandbox/probes/{x4sb_probes.h,x4sb_probes.c,x4sb_probe_main.c}` — the self-test probes and the
  outside positive-control exe.
