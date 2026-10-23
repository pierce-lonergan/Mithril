# X4 measurement service v0 + sandbox prototype — implementation notes

**Track:** x4-integrity (x4svc). **Status:** v0 built, unit-/golden-tested and end-to-end demonstrated on
the desktop after two review rounds (round 2: 26 findings, 3 blockers; round 3, 2026-10-16/17: 19
findings, 4 blockers, see the end of this file), each fixed **end to end**; **no gate data collected**.
**2026-10-23:** made ready for the noise-pilot nights by the X4 pilot track (observe mode, the hygiene
sensors, the Hearth workload set, the night driver and its dry run; see
[Noise-pilot readiness](#noise-pilot-readiness-x4-pilot-track-2026-10-23)); the same day that work had
its review round (two reviewers, 37 findings, all accepted, several with a modified fix) and was
revised as **revision 4** (see [Review round 4](#review-round-4-2026-10-23-37-findings-revision-4));
revision 4 had its own review round the same day (one reviewer, 13 findings, all accepted; 2 with a
part not adopted, 1 with a part left to the lead engineer) and was revised as **revision 5** (see [Review round 5](#review-round-5-2026-10-23-13-findings-revision-5));
revision 5 is **not yet reviewed**, and no pilot session, A/A, planted-regression or HACK-SUITE run was
made.
**Date:** 2026-10-16/17. Author/reviser: X4 track (Claude, same-family, independent context).
Evidence tags: **[M]** measured here, **[D]** derived, **[G]** judgment, **[target]** a pre-registered
threshold, **[inference]**.

This builds the designs in [MEASUREMENT-SERVICE.md](MEASUREMENT-SERVICE.md), [SANDBOX.md](SANDBOX.md),
[DESIGN.md](DESIGN.md) and [HACK-SUITE.md](HACK-SUITE.md). It changes **no** system settings and runs
**none** of the sealed catalogue (a) hacks, no A/A or planted-regression calibration, and no Hearth
benchmark. It exercises the machinery with the track's own `dev_*` probes on synthetic workloads only,
recorded as **non-gate**.

## Noise-pilot readiness (X4 pilot track, 2026-10-23)

**Goal:** the [X4-noise-pilot](../../docs/m0/prereg/X4-noise-pilot.md) nights can start as soon as
Pierce signs. **Desktop rules kept:** MSVC 19.44.35229 and cargo/rustc 1.91.1 (msvc host, by absolute
path), at most 3 parallel jobs and 3 busy threads (every job and run confined to LPs 26-28), every
artefact under `D:\mithril\x4c`, `CUDA_VISIBLE_DEVICES=-1`, TEMP/TMP on D:, no WSL, no system or
security setting changed, nothing written to C:. **Runs made:** unit tests, Hearth's own
`test_quant`/`test_platform`, the dev-probe regression, short dev runs and the dry run. **No** pilot
session, A/A, planted-regression or HACK-SUITE catalogue run. This work is **unreviewed**.

### What was built
1. **Observe mode** (record §3; `observe.rs`, `proto::Tolerances::observe_ceiling`). τ_clock is judged
   at its ceiling, 0.1% of Δ_o (the 1 ms floor still makes runs under 1 s ineligible); κ_post, the
   init bounds and the extra-core slack take the record's ceilings per run type; ε_spin and ε_idle go
   to the harness as cycle allowances at the orchestrator-calibrated rate (pool spin 50 µs + ε_spin
   50 µs, and 1 ms); the orchestrator now keeps the CENSUS frame and derives the per-class post-t1
   maxima from it. Every quantity, its ceiling and its margin is written per run (`runs.jsonl`,
   field `observe`).
2. **Hygiene sensors**, read-only, through documented interfaces only (`sensors_win.rs`): per-LP load
   and effective clock (PDH), disk queue / write rate / modified page list (PDH), per-process CPU
   (Toolhelp + `QueryProcessCycleTime`, which reads MsMpEng unelevated), `GetLastInputInfo` with the
   console-session check, the WTS session list, `PowerGetActiveScheme`, GPU utilisation through
   `nvidia-smi --query-gpu` (a query, no GPU work), NVMe temperature and volume bus type through
   `IOCTL_STORAGE_QUERY_PROPERTY` on no-access handles, and the processor topology. The three-tier
   rules are pure and blind (`hygiene.rs`: no function receives a run time, d or wealth); excluded and
   background image lists are configuration (GEMS names are filled at signing).
3. **The Hearth workload set** (`harness/hearth_workloads.c`, `harness/hearth_x4_shim.c`,
   `tools/build_pilot.bat`). A clean out-of-tree CMake/Ninja Release build of Hearth b5d3f14 at
   `D:\mithril\x4c\hearth-build` (hearth-c-ref, not X0 data); `x4harness_hearth.exe` links eight of its
   engine objects unchanged plus `platform_win.c` recompiled with CMake's exact flags and four renames,
   so the shim routes Hearth's thread creation through the registered wrapper and marks threads in a
   condition wait as parked. Workloads: `mb_q4_avx512` (x3_bench's shape, record §3), `e2e_decode`
   (the decode run type, model from the pinned `X4_MODEL_PATH`, configured from C02's default, the
   real Qwen3-30B-A3B Q4 container on the 990 PRO), and `dry_mb_tiny` (dry runs only). New harness
   API `x4h_quiesce()` (pool drained before t1, MEASUREMENT §3 step 6).
4. **The night driver** (`pilot.rs`, `pilotcfg.rs`; `x4svc pilot-night`). Strict configuration file;
   PILOT refuses without the freeze commit, the signature tag and the seed of the record's rule, and
   refuses `dry_*` workloads; schedule = the record's §2/§6 rules (seeded order, first unrun session
   that fits by 06:45 PT, Pacific time computed from UTC); pre-start night refusal; each session through
   `session::run_session` with real runs (`sandbox::run_once`, observe mode) and the real sensors; the
   e2e cool-down; records `runs.jsonl`, `blocks.jsonl` (with the four run seqs of each block),
   `sessions.jsonl`, `sensors.jsonl`, `voids.log`, `progress.txt` and `manifest.txt` (SHA-256 of every
   record file). Engine changes (`session.rs`, `scheduler.rs`): the gate is read before every run (a
   mid-block drop discards the block); sensor hooks `block_start`, `session_void`, `after_block`; a
   post-block discard counts toward the three-discard void; each block records its first run index.
5. **The dry run** (`pilot-night --dry-run [--plants]`): a whole night's schedule on a virtual Pacific
   clock with `dry_mb_tiny`, real sensors, records stamped `DRY-RUN` under `<scratch>\dry\` only; then
   one planted trigger per section 10 sensor, each a 2-block session that must end in its tier.
6. **Tools and files:** `x4svc topology`, `verify-hygiene [--as-pilot]`, `pilot-plan`, `dev-run`;
   `pilot/dev.cfg`, `pilot/dry.cfg`, `pilot/pilot.cfg.template`, `pilot/verify-now.cfg`,
   `pilot/PRE-NIGHT.md` (Pierce's commands), `pilot/verify_report.ps1` and its output
   `pilot/VERIFY-2026-10-23.txt`; `tools/dev_regress.ps1`; `tools/x4plant.c` (dry-run plant).

### Found while testing, and fixed [M, desktop, 2026-10-23]
1. **Start-up threads on a one-LP job counted as unregistered.** With the job pinned to one logical
   processor, two threads the process creates for itself 18-61 ms after start (the Windows loader's
   workers [inference]) appeared after the pre-init snapshot: `new_unregistered = 1` in 2 of 3
   `dev_sleep_long` runs and 3 of 3 `mb_q4_avx512` runs at a one-LP mask. Every pilot microbenchmark run
   (mask `0x4`) would have stopped the pilot. Fix (`x4h.c`, `settle_thread_set`): before the workload's
   init the harness sleeps 40 ms, then takes a thread snapshot every 10 ms until no new thread id has
   appeared for 30 ms (at most 300 ms). After it: 0 of 12 such runs, and none in the dry runs below.
   Cost: a longer pre-START window (bounded out of process): `dev_sleep_long` on one LP now takes
   0.25-0.39 s and 0.83-1.41 × 10⁹ cycles before START (round 3, unpinned: 68 ms, 0.27 × 10⁹), the
   Toolhelp snapshots walking every thread on the machine being the likely cost [inference]; the pilot
   microbenchmark's 0.76-0.88 s and 3.0 × 10⁹ cycles (warm-up included) stay at margins 0.44 and 0.35 of
   its init ceilings. The dev `x4svc run` placeholder `init_max_cycles` was raised from 1.0 to
   2.0 × 10⁹, still far below `dev_init_precompute`'s 6.7 × 10⁹.
2. **κ_post and a large address space.** With Hearth's default 8 GiB expert cache, STOP-to-exit was
   4.0 × 10⁹ cycles, over the record's 2.0 × 10⁹ ceiling, because the process's teardown is charged to
   it. The orchestrator now samples the child's cycles at REPORT receipt and judges κ_post over
   [STOP, REPORT]; the teardown [REPORT, exit] is recorded (`teardown_cycles`), and without a REPORT
   the bound still runs to exit. After: 0.75 × 10⁹ judged, 1.6 × 10⁹ teardown, Accept. Builder note
   for the design's owner (MEASUREMENT-SERVICE.md is outside this track): §3 step 8a should say so.
3. **Core parking could never verify.** `profile_win.rs` read CPMINCORES/CPMAXCORES with
   `powercfg /query`, which omits hidden settings, so item 7.2 always read None and refused, even after
   Pierce's commands. It now uses `powercfg /qh <scheme> SUB_PROCESSOR <alias>`; Balanced reads
   100/100 on AC. Builder note for MEASUREMENT-SERVICE §7.2 ("via `powercfg /query`").
4. **The self-test refused on a non-empty scratch.** Its scratch probe requires an empty directory;
   with the dry-run records under the scratch root it reported `mode: refused`. The driver now gives
   the self-test a fresh empty directory of its own.
5. **Daytime start state.** The disk queue (`_Total`, an instantaneous count) was rarely 0 in the
   daytime, so a first dry night voided every session on "start state not reached". The record's rule
   is unchanged for PILOT (queue 0, writes ≤ 1 MiB/s, enforced by the configuration parser); dry runs
   use a `disk_queue_max` of their own.
6. **Short PDH windows.** At 100 ms, per-LP load is quantised by the 15.6 ms clock tick and `_Total`
   was sometimes invalid (the gate then reads 100%, failing closed). The pilot uses the record's 2 s
   window (enforced); the load plant uses 1 s.
7. **The excluded-process pre-start item** refused a PILOT night whenever such a process merely ran;
   the record voids only when one starts or uses CPU, so the item is advisory now.
8. **The input sensor and the launch path.** Over SSH the driver runs in session 0, where
   `GetLastInputInfo` cannot see the console; a PILOT night refuses. The driver must be started in
   Pierce's console session (PRE-NIGHT.md A6).

### Verified [M, desktop DESKTOP-8RS9J1J, 2026-10-23]
- **Builds:** `build_pilot.bat` (MSVC /W4 and rustc: no warnings); `cargo test -j 3 --release --
  --test-threads=3`: **79 unit + 4 golden/differential tests pass** (62 before; new tests cover observe
  mode, the per-run gate and the sensor hooks, the configuration and schedule rules, Pacific time and
  the hygiene tiers).
- **hearth-c-ref:** the clean Ninja build of b5d3f14 (24 targets, rc 0); Hearth's own `test_quant
  --small --no-bench`: **117,681 checks, 0 failures**; `test_platform`: 251 of 255, the 4 failures all
  in its affinity test, which pins children to LPs 0-2 and so cannot pass under this track's 3-LP
  confinement [inference from `test_platform.c:1274-1295`].
- **Regression of the round-3 table** (`tools/dev_regress.ps1`, every probe pinned inside LPs 27-28):
  **22 of 22** verdicts as before, and `x4_devcheck.py` **24 of 24**, after the settle change.
- **Dev runs of the pilot's workloads** (`dev-run`, observe mode, LP 28 or LPs 27-28; not pilot data):

| run | Δ_o | verdict | notes |
|---|---|---|---|
| `mb_q4_avx512`, K = 200,000 | 1.138 s | Accept | \|Δ_h−Δ_o\| 6.3 µs (margin 0.006); STOP→REPORT 0.66 × 10⁹ cycles (0.33); init 0.73 s / 2.87 × 10⁹ cycles (0.36 / 0.33); 1.000 cores |
| `mb_q4_avx512`, K = 65,536, three runs | 0.372-0.373 s | bracket_too_short only (< 1 s) | 5.68 µs per call: indicative K ≈ 1.76 × 10⁶ for 10 s; golden `55b9c367…a036` on every run and K |
| `e2e_decode`, N = 8, caller + 1 I/O thread, 1 GiB cache | 2.97 s | Accept | init (`hearth_open`) 0.49 s; the I/O thread parked through the shim; golden `86653fe5…0f35` |
| `e2e_decode`, N = 8, caller + 1 pool worker + 1 I/O thread | 3.21 s | Accept | both registered threads parked; `x4h_quiesce` held; same golden (bit-identical across thread counts) |
| `e2e_decode`, N = 8, 8 GiB cache | 2.91 s | Accept (after fix 2) | STOP→REPORT 0.75 × 10⁹, teardown 1.6 × 10⁹; same golden |

- **Topology** (`x4svc topology`): CCD0 = LPs 0-15, CCD1 = LPs 16-31; `p` = LP 2 (`0x4`); the
  orchestrator's LP = 30; the e2e mask under C01's default `0xbfffffff`.
- **The model file** (C02's default): `C:\Users\pierce lonergan\hearth-data\qwen3-30b-a3b-q4.hearth`,
  17,028,976,640 B, `arch = qwen3_moe`, `source = Qwen3-30B-A3B` (read from its metadata, read-only), on
  the 990 PRO (bus NVMe); D: is the USB HDD (bus USB).

- **The dry night** (`pilot-night --dry-run --plants`, `pilot/dry.cfg`, DRY-RUN, not data; evidence
  in [`pilot/dry-run-2026-10-23/`](pilot/dry-run-2026-10-23/): the console log, `manifest.txt`,
  `sessions.jsonl`, `plants.jsonl`, `voids.log`, byte-equal to the hashes in the manifest). A full
  virtual night 23:00-06:45 PT on the seed `6a314c1f9fc1d48b` (the record's rule applied to 40 zeros)
  ran in **33 min** of wall time: 19 of 23 sessions started in seed order (the first unrun session that
  fits; `e2e-decode-02`/`-03` and two microbenchmark sessions did not fit after 05:30 and 06:42),
  **18 completed** with all their blocks (17 × 24 microbenchmark blocks and one 12-block end-to-end
  stand-in session) and **1 hygiene-voided after 12 blocks** by a real trigger: "another Mithril
  measurement process: x4svc", the self-test this track ran by hand during the session. 1,732 session
  runs; 436 blocks with ABBA 209 / BAAB 227; every run IntegrityFail **only** on `bracket_too_short`
  (sub-second dry runs, counted by the dry rule) apart from the three golden-mismatch runs that were
  meant to fail (two golden-learning passes, one integrity plant); observe values: STOP→REPORT
  0.57-1.39 × 10⁹ cycles (margin ≤ 0.69), teardown ≤ 9.3 × 10⁶, init 0.22-0.42 s and 0.69-1.52 × 10⁹
  cycles, idle-class post-t1 ≤ 2.2 × 10⁵ cycles (margin ≤ 0.05), |Δ_h − Δ_o| ≤ 72 µs. A first dry night
  before fix 5 voided every session on the start state, which exercised the void path and slot re-use
  of all 23 sessions.
- **Planted triggers** (the same dry nights, then again on the final build with `--max-sessions 1`,
  `pilot/dry-run-2026-10-23/final-build/`): every one fired in its tier and the control session
  completed with no discard. Real triggers: an excluded image starting (`x4plant_gems.exe`, a copy of
  the track's plant), another Mithril measurement process (`x4harness_foreign.exe`), CPU load from 3
  busy threads on LPs 26-28 (15.05% against a dry threshold of baseline + 4 pp = 11.23%), 256 MiB of
  write-through writes to D: (start state not reached, the session voided after 3 discards), the NVMe
  temperature at a block start against a dry threshold 1-2 °C below the reading, an integrity failure
  (wrong golden: the session stops). Injected readings, so only the decision path is shown: Defender
  CPU over a block, interactive input, an RDP session, GPU utilisation, a power-scheme change; the
  07:00 cut on the virtual clock; and the start rule (nothing starts at 06:44). The plant on the
  pre-final build missed once, because the plant processes inherited the orchestrator's one-LP mask
  (one LP of load, not three); the dry configuration now names the plant mask (`plant_affinity`).
  **Which binaries this covers (restated in revision 4, review R1-14):** the final-build dry run
  (13:05 ET) ran `x4svc.exe` `1f0a4c25…b225`, `x4harness_hearth.exe` `8061f12b…c9c0` and
  `x4sb_probe.exe` `808d4164…8450`; the harness and probe were rebuilt at 13:08 ET
  (`69c0ed9b…ae5c`, `9de4c5d4…0d7b`, listed below), after it, so no builder dry run covers them; a
  reviewer's plant pass on those two with 2 LPs fired 13 of 13 and its start rule held [M, reviewer,
  `D:\mithril\x4c\scratch\review\dry\`]. They are kept in `D:\mithril\x4c\bin-r3\`. Revision 4 rebuilt
  every binary; its evidence and hashes are in [Review round 4](#review-round-4-2026-10-23-37-findings-revision-4).
- **Refusals:** `pilot-night --pilot` refuses a DRY-RUN or DEV configuration, `--dry-run` refuses a DEV
  one, and the template does not parse until its values are filled [M]. The PILOT path itself was not
  run (no record is signed); its rules are unit-tested (`pilotcfg`, `hygiene`) and its pre-start items
  are shown by `verify-hygiene --as-pilot`.
- **Read-only pre-start report:** [`pilot/VERIFY-2026-10-23.txt`](pilot/VERIFY-2026-10-23.txt),
  summarised in [`pilot/PRE-NIGHT.md`](pilot/PRE-NIGHT.md) section C. Failing today: the power plan
  (Balanced), the pins files, the binary pins, the input sensor over SSH, Windows Update active hours
  and the maintenance time; the self-test reads `degraded-job-only`; every sensor reads.

### Not done, and limits (honest list; updated for revision 4)
- **No pilot session, A/A, planted-regression or HACK-SUITE run** (by rule). The PILOT mode has never
  run end to end; its first real night is the first test of the real sensors at 2 s / 1 s windows and
  60 s settles, of the 120-s session settle, the per-session profile check, the console-session
  launch, and of the e2e run type at the pilot placement.
- **The e2e run type was run only at dev size** (N = 8, at most 3 threads, 1 or 8 GiB cache) inside
  this track's budget; the pilot's 24 threads on 31 LPs, N = 2,048 and its golden were not run.
  Revision 4 makes its t_run,plan, time cap and the per-run overhead o_rt mechanical pre-night values
  (record § Amendments); they, K, the goldens, the pins and the binary hashes are not filled here.
  *Revision 5:* one attended run at the pilot placement inside a window before night 1 (PRE-NIGHT A9);
  at dev size with the 8 GiB cache the peak process memory was 9.68 GiB of the 24 GiB limit [M, Review
  round 5].
- **Some sensors are shown firing only on injected readings** (input, RDP, Defender, scheme): they
  cannot be planted for real without touching the console or security software. The GPU rule fired on
  real readings in revision 4's superseded dry runs (13-99%, GEMS in daytime) [M]. The load gate was shown
  firing at a dry threshold, not at the record's 40% (that needs about 13 busy LPs, over this track's
  budget). No ACPI thermal-zone counter exists here, so the package temperature of MEASUREMENT §4.1 is
  unavailable [M].
- **Readability at Medium integrity is unverified**: every sensor reading so far ran in an elevated
  SSH session [M]; Pierce's once-only check (PRE-NIGHT A6) settles it. *Revision 5:* under a restricted
  token the background images could not be opened; the sensor now reads them through PDH and every
  listed image reads [M, Review round 5]; Pierce's own session (A8) is still the check that counts.
- **The pre-START wall ceiling** (review R1-11) is an Owner decision before freeze; the service judges
  it (the stricter reading).
- **The driver checks a signature's shape, not the signature**: a PILOT configuration must name the
  freeze commit, the tag and the rule's seed, but `x4svc` does not run `git verify-tag` (there is no
  checkout of this repository on the desktop [M]); the authority is Pierce's launch under the signed
  record (record §10, and every manifest says so).
- ~~**No estimator CLI**~~ *Revision 5:* written, `x4svc pilot-estimate` (`src/estimate.rs`, unit-tested,
  and run on a dry night's records in its `--dry-test` mode; Review round 5).
- **The record's X3/X4 priority-class conflict** is a recommendation (record §3), not a decision.
- **F0 line budget:** the platform-independent core is ≈ 1,707 lines (`proto` 593, `stats` 305,
  `eprocess` 245, `session` 214, `scheduler` 136, `quantity` 93, `sha256` 88, `runenv` 33), plus the
  pure modules `pilotcfg` 657, `observe` 200 and `hygiene` 190, and the Windows adapters `pilot.rs`
  (1,676 lines in all) and `sensors_win.rs` (699) [M, revision 4: non-blank non-`//` lines before
  `#[cfg(test)]` for the core; `wc -l` for the adapters]. Further over the 1,500 target; the split
  remains future work before freeze.
- **Unreviewed.** Revision 4 (below) has had no review of its own.

### Binaries of the revision-3 build [M, `D:\mithril\x4c\bin` at ≈ 13:10 ET, now `D:\mithril\x4c\bin-r3`, 2026-10-23; dev build, not pins; superseded by revision 4]
`x4svc.exe` `1f0a4c252308f885ce6f6bd799ce610a948652c1d0734b949634ecad7699b225`;
`x4harness_hearth.exe` `69c0ed9b62a0ef1d33ad0b57f349d66e38b74cc9b8abbc3e85dafc8c63d5ae5c`;
`x4sb_probe.exe` `9de4c5d4a3e3c8a8b5c161f07758894d7610a64e51a6fe258d5ee88992240d7b`;
`x4harness.exe` `dbe48760cd70e844f301cf41efff3658118ed5630837a3597e96d86a91f1b098`;
`x4plant.exe` `d4ee48bb64c02f2acf6c2be810e207ea52ff6448488fc2b8dd25cbb155ab30ff`. The last C rebuild
changed only a comment in `x4h.c` after the final-build dry run (which ran `x4harness_hearth.exe`
`8061f12b…c9c0`); two `mb_q4_avx512` dev runs on it were accepted (Δ_o 1.136 s). The MSVC link is not
bit-reproducible (every C rebuild changed every C hash; `x4svc.exe` did not change when its sources
did not), so the pre-night amendment pins the copies that will run.

## Review round 4 (2026-10-23): 37 findings, revision 4

Two reviewers (Claude, same family, independent context) reviewed the pilot-readiness work above and
revision 3 of the record: reviewer 1 on evaluator integrity and hygiene (20 findings: 11 major, 9
minor; read-only desktop checks and a dry night of its own), reviewer 2 on the pilot design (17: 9
major, 8 minor). The reviser (Claude, same family, independent context from both) checked each
against the code, re-read the desktop where a finding named it, and fixed each **end to end**. **All
37 accepted**; 10 with a modified fix or a part not adopted (marked "modified" or "part"). The record's own disposition is
in its §12; this table is the service side.

| # | Sev | Finding | Verified | Disposition |
|---|---|---|---|---|
| R1-1, R2-1 | major | PILOT held only the windows, start state, priority and pins; every other record constant was free | yes (code) | **Fixed.** `pilotcfg::pilot_rules`: every fixed value of record §3, §3a, §6, §10 must hold exactly (thresholds, windows, setup, run types and order, workloads, outputs, N, env blocks, threads = HEARTH_THREADS + HEARTH_IO_THREADS, observe ceilings, exit grace, time caps, sessions × blocks, cooldown, plant_affinity 0), image lists must contain the record's; `init_max_cycles = derive` (120 s × threads × the night's rate). Unit test: 56 single-value mutations of a filled template, each refused [M] |
| R1-2, R2-14 | major / minor | PDH drops per-LP instances; pre-start read 200 ms; a missing `_Total` fails the gate closed | yes, cause corrected: the dropped status is `PDH_CSTATUS_INVALID_DATA` (0xc0000bba) at 100–200 ms windows, not `PDH_CALC_NEGATIVE_VALUE`; 0 drops in 11 reads at 2 s [M] | **Fixed.** The gate's machine load is `GetSystemTimes` over the window (PDH `_Total` recorded beside it); PDH_CALC_NEGATIVE_VALUE instances kept as 0, any other dropped instance recorded with its status (`dropped_lps`), never read as idle; the pre-start item uses the 2-s window and needs every LP (up to 3 reads) |
| R1-3, R2-3 | major | e2e cool-down after the gate; load sampled before the settle loop | yes (code) | **Fixed.** `GateSensor::before_run` (cool-down) → `session_void` → `read` (settle first, 2-s load last) → run; the run's empty scratch is made right after the previous run, so only an emptiness check lies between the gate and the launch (wiping on the USB disk there gave 0.1–0.4 s spikes in a superseded dry night [M]); the gate-to-launch gap is recorded per run (`gate_gap_ms`); unit test of the order |
| R1-4, R2-4 | major | Processes that start and exit between checks, a busy SMT sibling and GPU between block starts are invisible | yes (code; reviewer's dry night: 183 of 592 passing gates with LP 29 > 50% [M, re-read]) | **Fixed, modified.** A 250-ms process poller (union of every listed process seen, exited ones up to their last poll, pid + creation time, own children exempt by parent pid) feeds the void and discard rules; GPU and NVMe at every check; per-run PDH bracket (per-LP load and clock over [launch, exit]); other CPU per block (system busy − job − orchestrator); background list extended (`MpCmdRun`, `CompatTelRunner`, `defrag`, `ngen`, `ngentask`, `mscorsvw`, `DismHost`, `cleanmgr`, `wermgr`). The 10% per-LP rule applies to one-LP run types only (the record's "SMT sibling idle"); not adopted for the 31-LP e2e mask. PDH GPU-engine counters not adopted (nvidia-smi at every check; residual stated) |
| R1-5 | major | bg discard divided by the observed block time; the 07:00 cut depends on run times | yes (code) | **Fixed.** Denominator = planned block time 4 × (t_run,plan × c + o_rt); cut sessions end `cut` with their blocks; record §9 reports σ̂_d with and without them |
| R1-6, R2-9 | major | Overhead not in the plan; the dry clock advanced by plan only; e2e t_run,plan a judgment | yes (code) | **Fixed, modified.** `overhead_s` (o_rt) per run type in the plan; the dry clock carries the real time of checks, launch and teardown; `sessions.jsonl` has planned_s and actual_s; t_run,plan(e2e) is a mechanical pre-night value measured at the 8-LP daytime placement (the pilot placement exists only inside a window: C01, D0-7a), an overestimate; e2e time cap = max(600, 3 × plan) |
| R1-7 | major | An SSH login during a night is undetected | yes (code; the reviewer's process chain) | **Fixed, simplified.** `excluded_started_images` (sshd, sshd-session, powershell, pwsh, cmd): a new process voids; the ancestor-chain exemption is unnecessary (ancestors exist at the baseline); PRE-NIGHT B6 |
| R1-8 | major | The self-test ran before pinning and with no job affinity | yes: `refused` without a job mask, `degraded-job-only` with it [M, below] | **Fixed.** `selftest --affinity`; the driver passes the first run type's mask and pins itself before the pre-start items; dry.cfg's command uses `start /affinity` |
| R1-9 | major | A default scheduled task runs below normal | yes (reviewer's [M]; documented priority mapping) | **Fixed, part.** PRE-NIGHT A6 registers with `-Priority 4`; the driver records class, memory priority, elevation and integrity in the manifest and refuses a PILOT night unless NORMAL and MEMORY_PRIORITY_NORMAL. I/O priority has no documented reader; not checked |
| R1-10 | major | Readability evidence is from an elevated SSH session | yes [M: elevated, integrity RID 0x3000 over SSH] | **Fixed, part.** Retagged in the record; PRE-NIGHT A6 adds Pierce's once-only check from his console session and from the task, committed with the pre-night amendment (an agent cannot run it: its session is elevated) |
| R1-11 | major | The pre-START wall ceiling stops the pilot on host noise | yes (reviewer's seq 620: 3.64 s wall, 0.78 × 10⁹ cycles [M, re-read]) | **Owner decision, not taken here.** The stricter reading (judged) is kept, its consequence is in record §9, the question is open before freeze (§3); the run core rule makes the cause rarer [inference] |
| R1-12, R2-2 | minor / major | progress.txt only at session end; an integrity stop did not hold across nights; no binary pins in progress | yes (code) | **Fixed, modified.** Synced `started` line (seed, harness and x4svc SHA-256) before the first run; an interrupted session is written `interrupted` (a void, per R1-12; R2-2's night refusal for it is not adopted, so a power cut does not stall the pilot); an uncleared integrity stop or another seed/binary refuses the night; `integrity_cleared = <session>@<amendment commit>`; manifest rewritten after every session with progress.txt's hash |
| R1-13 | minor | Dry records could reach the pilot data area; no estimator | yes (code) | **Fixed, part.** A DRY-RUN scratch under `D:\mithril-data\` is refused; the estimator's input rule is in record §7; the estimator itself is still not written |
| R1-14 | minor | The final-build evidence does not cover the binaries in `bin` | yes (hashes) | **Fixed.** Restated above; revision 4's evidence names its binaries (below) |
| R1-15 | minor | The suggested Defender exclusion of the dev build folder | yes | **Fixed.** Withdrawn from PRE-NIGHT A4 and record §11 |
| R1-16 | minor | Active hours do not stop servicing; maintenance does not move idle tasks | yes | **Fixed.** PRE-NIGHT A2, A3 |
| R1-17 | minor | The 120-s setup existed only on the dry clock | yes (code) | **Fixed.** A real settle; run-LP clock and NVMe at its end in `sessions.jsonl` |
| R1-18 | minor | The run's env block lacks `CUDA_VISIBLE_DEVICES=-1` | yes | **Fixed.** In dev.cfg, dry.cfg, the template, record §3 (a pre-freeze env-hash change) |
| R1-19 | minor | `remove_dir_all` under any non-C: scratch | yes | **Fixed.** Scratch ≥ 2 levels under `D:\mithril\` or `D:\mithril-data\` |
| R1-20 | minor | `--max-sessions` in a PILOT night | yes | **Fixed.** `--max-sessions`, `--plants`, `--plant-exe` refused with `--pilot` |
| R2-5 | major | No terminate on REPORT; teardown wall not recorded | yes (code) | **Fixed.** Exit grace 5 s after REPORT (`exit_grace_ms`), then `TerminateJobObject` and `no_exit_after_report` [OOP]; `teardown_wall_ns` with ceiling and margin |
| R2-6 | major | `profile_ok` hard-coded true | yes | **Fixed, modified.** Full `verify-profile --collection --pins` at every session start (PILOT; fingerprint per session in `sessions.jsonl`); after every block only core parking is re-read (a full fingerprint spawns PowerShell/CIM between runs); a change discards the block and voids at the next gate |
| R2-7 | major | ε_spin's recorded value includes the pool spin | yes | **Fixed.** `eps_spin_observed_us` (net of 50 µs) and `eps_idle_observed_us` per run; record §3a, §7(a) |
| R2-8 | major | Which clock is T | yes | **Fixed.** T = Δ_h (MEASUREMENT §3 step 8); `ln_delta_h_ns` in `blocks.jsonl`; record §4 |
| R2-10 | minor | Quiesce can return while a signalled thread has not yet run | yes: race shown, 3 of 3 runs [M, below] | **Fixed, different mechanism.** The proposed global wake epoch would stall quiesce whenever a signal wakes one of several waiters (the others keep old epochs and never re-park), so every multi-reader e2e run would time out. Instead the shim (six renames) counts each condition variable's waiters and pending wakes; `x4h_quiesce` waits for zero pending wakes and re-checks after a yield. Dev probe `dry_quiesce_wake` |
| R2-11 | minor | nvidia-smi's CPU lands in the load sample | yes | **Fixed** by the order (settle ≥ 1 s between the snapshot and the 2-s load); `after_gpu_query` recorded |
| R2-12 | minor | The K rule's calls and the order mapping | yes: 2¹⁶ calls = 0.37 s | **Fixed.** K from 2¹⁸-call runs (1.49 s, bracket eligible [M, below]); record §2 states the draw mapping |
| R2-13 | minor | No cool-down before a session's first e2e run | yes | **Fixed.** The previous run's NVMe-bound flag and Δ_o live in the night context |
| R2-15 | minor | The signature tag is never verified | yes | **Fixed by stating it** (record §10, manifest line): there is no checkout of this repository on the desktop [M]; Pierce's launch is the authority |
| R2-16 | minor | The build does not enforce b5d3f14 or a clean tree; CMake outside the script | yes | **Fixed.** HEAD and porcelain checks, rustc version check, the CMake build into an empty directory, nine object hashes in the log |
| R2-17 | minor | Other Mithril and WSL images missing | yes | **Fixed.** `mithi`, `mithc`, `vmmem`, `wslhost`; Mithril detection by image name, stated |

### Verified on the revision-4 build [M, desktop DESKTOP-8RS9J1J, 2026-10-23, every job confined to LPs 26-28, `CUDA_VISIBLE_DEVICES=-1`, artefacts under `D:\mithril\x4c`]
- **Build** (`tools/build_pilot.bat`, revision 4; log `D:\mithril\x4c\jobs\build_pilot_r4.log`): the
  script's own checks passed (Hearth HEAD `b5d3f14a…e220`, clean tree; `cl` 19.44.35229, CMake 4.4.3,
  Ninja 1.12.1, rustc 1.91.1 (ed61e7d7e 2025-11-07), cargo 1.91.1); the clean Hearth build into an
  empty directory and every C and Rust step returned rc 0 with **no warnings** (MSVC /W4, rustc). The
  nine engine objects' SHA-256 are in the log (e.g. `pool.c.obj` `f410620e…0b2`, `store.c.obj`
  `c9924dd4…32a`). Binaries (dev build, not pins):
  `x4harness_hearth.exe` `962a670b853a8a16e26a5188cae792c696758c444b109d45acdfed7ce46110d7`;
  `x4sb_probe.exe` `f3d9dd3915fd6ba391e91ca3608e6344e06f5d31b4e138236e8a08807fe4e720`;
  `x4harness.exe` `fcaecb688f95c0b1057542c7edcd9bf0d640e026046c59af7ac29cac4f9f1997`;
  `x4plant.exe` `1f1c73909c9dd32710c2b8a77a8f3bb460e901af589b094f62fbf438465f504e`;
  `x4harness_hearth_q0.exe` (dev only, never pinned)
  `1b4a209e576c3bcb2c4817ef13dd76e62f10039e8d50e9adb5c7dfcb5b3a0ae7`; and the final `x4svc.exe`
  `68125f5e173d87df4fbe09c565e0964de311b0d6a34607182fd28641772b02f9`, rebuilt by cargo after the
  script run as the last driver changes landed (the C binaries are from the one script run). **Every
  line below ran on exactly these binaries** (earlier `x4svc.exe` builds of the day, `865d279d…`,
  `054cad20…`, `8e4d1730…`, `fde9b878…`, ran the intermediate checks that led to those changes and are
  superseded; so is a full dry night stopped part-way on `8e4d1730…`).
- **Tests:** `cargo test -j 3 --release`: **85 unit + 4 golden/differential tests pass** (79 before;
  new: the PILOT mutation table, 56 single-value loosenings of a filled template, each refused; the
  path guards; the poller union and pid reuse; the started-only and own-child rules; the run core rule;
  the hook order; the exit grace; the net ε; the progress file).
- **Regression** (`tools/dev_regress.ps1`, `x4_devcheck.py`): **22 of 22** verdicts as in round 3 and
  **24 of 24** harness signals.
- **The quiescence race (R2-10)** (`dev-run` of `dry_quiesce_wake`, 2,000 signal-then-quiesce rounds
  per run, two registered workers and the caller on LPs 27-28): on the dev-only build without the wake
  accounting, **3 of 3 runs** returned workload status 230 (quiesce returned while a signalled worker
  had not yet run) and left the output poisoned; on the pilot build, **0 of 3** (each run's only
  failure is `bracket_too_short`, the 42-ms probe being under the 1-s floor).
- **Dev runs of the pilot workloads** (`dev-run`, observe mode): `mb_q4_avx512`, 2¹⁸ calls on LP 28:
  Δ_h 1.490357 s (5.69 µs per call), |Δ_h − Δ_o| 7.8 µs, STOP→REPORT 0.93 × 10⁹ cycles, teardown
  1.2 ms, pre-START 0.80 s / 3.17 × 10⁹ cycles, net ε_idle 11.1 µs, **Accept** with the bracket
  eligible (the K rule's run length); `e2e_decode`, N = 8, LPs 27-28: Δ_o 2.96 s, teardown 97 ms /
  0.41 × 10⁹ cycles, **Accept**, golden `86653fe5…0f35` as before.
- **Self-test (R1-8):** with `--affinity 0x10000000` probe 15 (widen affinity) is blocked inside and
  the mode is **`degraded-job-only`**; the same call without it, under the confined launcher, gives
  probe 15 SUCCEEDED and **`refused`** (the reviewer's finding, reproduced).
- **Sensors (R1-2):** 2-s load reads: 32 of 32 LPs in 11 of 11 reads (0 clamped, 0 dropped);
  100–200 ms reads drop instances with `PDH_CSTATUS_INVALID_DATA` (`0xc0000bba`) [M]; in the dry
  night's 100-ms gates 944 of 1,637 readings had a dropped LP and 226 a missing PDH `_Total`, while
  `GetSystemTimes` read every time.
- **Parser and CLI (R1-1, R1-20):** the template filled with dummy values parses as PILOT and plans
  23 sessions (17.97 h at o_rt 5 s and t_run,plan(e2e) 150 s); the same with `load_max_pct = 100` is
  refused ("PILOT differs from the record's fixed values"); `pilot-night --pilot --max-sessions 1` is
  refused; `pilot-night --pilot` outside the window is refused.
- **The read-only pre-start report** on these binaries: [`pilot/VERIFY-2026-10-23-rev4.txt`](pilot/VERIFY-2026-10-23-rev4.txt)
  (summarised in PRE-NIGHT.md section C).
- **The dry night** (`pilot-night --dry-run --plants`, `pilot/dry.cfg`, DRY-RUN, not data; evidence in
  [`pilot/dry-run-2026-10-23/rev4/`](pilot/dry-run-2026-10-23/rev4/): the console log, `manifest.txt`,
  `sessions.jsonl`, `plants.jsonl`, `voids.log`, `progress.txt`, byte-equal to the manifest's hashes,
  plus `summary.txt` and `checks.txt`). A virtual night 23:00–06:45 PT ran 17 sessions in seed order
  (16 microbenchmark, 1 end-to-end stand-in), **all completed with no discard**; 6 did not fit after
  06:33 (with o_rt in the plan, two fewer than revision 3's dry night). 1,630 runs, every one
  IntegrityFail only on `bracket_too_short` (sub-second dry runs, counted by the dry rule) except the
  three wrong-golden runs meant to fail. Planned vs actual per session: 1,560 s vs 1,145–1,172 s
  (microbenchmark, at the dry 100-ms windows), 9,000 s vs 8,743 s (end-to-end stand-in). Observe
  values: STOP→REPORT margin ≤ 0.53, teardown ≤ 2.8 ms, pre-START p99 0.33 s (max 1.08 s) and ≤ 1.20 ×
  10⁹ cycles, net ε_idle ≤ 20.4 µs, |Δ_h − Δ_o| ≤ 104 µs. **Gate-to-launch gap:** p50 0.23 ms, p99 22
  ms, max 72 ms. Other CPU on the machine per block (daytime, other agents and GEMS present): p50 4.8
  core-s; the orchestrator's own p50 0.19 core-s; the job's p50 1.34 core-s. **Plants, all fired in
  their tier** (and the control completed with no discard): an excluded process that starts, runs 1 s
  and exits **before the next check** (seen only by the poller); a started-only image; another Mithril
  process (also exited before the check); CPU load (3 busy threads, against a dry threshold of baseline
  + 4 pp); **the run core rule** (1 busy thread on the run LP, against 10%); disk writes; NVMe
  temperature (a dry threshold 1 °C below the reading); and, injected, Defender CPU, input, an RDP
  session, GPU 50%, a power-scheme change; the 07:00 cut (end `cut`); an integrity failure; the start
  rule held at 06:44. (In the superseded dry nights the GPU rule fired on real readings of 13–99%, GEMS in
  daytime, before the injection.)

### Builder notes for MEASUREMENT-SERVICE.md (outside this track's files)
In addition to the four of revision 3 (§3 step 8a κ_post over [STOP, REPORT]; §4 the gate per run;
§7.2 `powercfg /qh`; §7.3 an empty self-test scratch): §3 step 6, quiescence also waits for pending
condition-variable wakes (the shim's accounting); §3 step 8a, the job is terminated 5 s after REPORT
if the child has not exited (`no_exit_after_report`, out of process), and the teardown wall is
recorded; §4, the machine load is read from `GetSystemTimes`, the start state is settled before the
2-s load is read, and the cool-down comes before the checks; §4/§5.3, background CPU is judged over
the planned block time; §7.3, the self-test's job gets the run type's affinity limit.

## Review round 5 (2026-10-23): 13 findings, revision 5

One reviewer (Claude, same family, independent context) reviewed revision 4 with desktop checks of its
own (a rebuild, dry nights at the record's windows, PILOT-configuration variants, and readings under a
restricted token: `runas /trustlevel:0x20000`, Administrators deny-only, which approximates Pierce's
non-elevated token; its label still reads High). The reviser (Claude, same family, independent context
from the reviewer) checked each finding against the code and re-measured each desktop claim on its own
build in `D:\mithril\x4rev4r` (3 threads: LPs 26-28; `CUDA_VISIBLE_DEVICES=-1`; TEMP/TMP on D:; no WSL;
no setting changed). **All 13 accepted; F8 and F12 with a part not adopted, F1 with a part left to the lead engineer.** The record's disposition is in its
§12; this table is the service side.

| # | Sev | Finding | Verified | Disposition |
|---|---|---|---|---|
| F1 | blocker | The record cannot freeze: no X4-calibration record; C07 not delegable; the §7 estimator unwritten | yes (no such file; DELEGATED P23; IMPLEMENTATION "Not done") | **Fixed, part.** `x4svc pilot-estimate` written (`src/estimate.rs`: a dependency-free JSON reader, the §7 input checks, the §4 counted set and estimators, the §7(a) 2x fill-in with ceiling flags, the load threshold, envelopes, discard causes, block-hours; 4 unit tests) and run on a dry night (`--dry-test`). The freeze chain is stated in the record. *Not done here:* splitting X4-calibration out of the X4-integrity DRAFT and freezing it after Pierce's C07 (outside this track's files; not delegable) |
| F2 | blocker | Non-elevated, the background images are unreadable: PILOT refuses, every block would be discarded | **yes, reproduced** on the revision-4 binary under the restricted token: `unreadable listed images ["mpdefendercoreservice","msmpeng","searchindexer"]`, and a dry session voided after 3 discards "msmpeng CPU unreadable, ..." [M] | **Fixed, option (a).** `sensors_win::processes_where` reads any listed process it cannot open through the documented PDH `\Process(*)` raw counters (`% Processor Time` = kernel + user time in 100 ns, `ID Process`, `Elapsed Time` = creation FILETIME; both equal to the elevated `GetProcessTimes` values [M, `pdhtest.ps1`]); PDH repeats duplicate instance names without `#n` [M: five `python` under one name], so the three arrays are paired by position with the names checked; `hygiene::cpu_cycles_since` converts the tick-based time at the calibrated rate for the background rule and treats any increase as CPU use for an excluded image. Under the restricted token every listed image now reads and the same dry session completes with 0 discards [M, below]. Option (b), an elevated driver, is not needed |
| F3 | major | Pins made elevated over SSH; the driver reads the fingerprint in Pierce's session | yes [M: under the restricted token every CIM field reads `unavailable`, hash `6a58b257…` vs `e02fdb2b…` elevated] | **Fixed.** PRE-NIGHT reordered: Pierce makes the pins in the launch context (A7), keeping every `# key=value` line; `pilot::pins_field_diff` names each differing field in the collection failure [M, below] |
| F4 | major | The B13 job wrapper does not exist; A6 called the task "the B13 wrapper" | yes (grep) | **Fixed, second option.** Record §9/§10 rely on the started-only, excluded and Mithril-image voids; the task is the "pilot launcher" (PRE-NIGHT A6, `pilot.rs`, `verify-now.cfg`) |
| F5 | major | A PILOT configuration that differs from the record still parses | **yes, reproduced** for each of the reviewer's variants | **Fixed.** `pilot_rules` by equality: e2e `time_cap_s` = max(600, 3·t_run,plan); `memory_gib` 2 / 24 (now record §3); `disk_write_max_bytes_s` = 1048576; image lists equal to the record's (signing names in `excluded_images_at_signing`, required in PILOT, may be empty); record path; data, scratch, probe, harness and pins paths; the tag name; one harness hash for both run types; o_rt and t_run,plan(e2e) whole seconds within [4, 15] s and [1, 600] s [G]; a `<FILL` placeholder never parses. The rest (K, o_rt, t_run,plan values, hashes, goldens) is bound by the **canonical configuration SHA-256** (`pilotcfg::config_canonical_sha256`, the file without its `integrity_cleared` lines; `x4svc config-hash`): `pilot-night --pilot` requires `--config-sha256` and refuses on a mismatch before it creates anything; the estimator requires it too. Each night's manifest also records the pins files' SHA-256 (the pins are not in the configuration's hash). Unit tests: 21 more single-value mutations (77 in all) and the committed template filled is the record |
| F6 | major | A crash leaves the manifest `open` with stale hashes; §7 then rejects the night | yes (code) | **Fixed.** The manifest is written `open` before the first session; the next night's driver, or `x4svc pilot-close` (refused inside the window or while another x4svc runs), writes `manifest-closed-after-interrupt.txt` with the current hashes, the open manifest's hash and the sessions started without an end line, then marks them `interrupted`; progress.txt is hashed by prefix (`bytes=`), since it only grows; the estimator accepts a cut-short last line only in such a night. Shown on a dry night killed 30 s in [M, below] |
| F7 | major | Partial blocks of integrity_stop / error sessions counted; integrity_cleared changes the config hash | yes (code) | **Fixed, modified.** Counted set = sessions ending `completed` (the estimator reports the excluded ends); a set-up error is written `error`; the canonical hash leaves out `integrity_cleared` lines, so no "clearing amendment hash" is needed |
| F8 | major | Open Owner choices outside §13; Plan A/B could be chosen after σ̂ | yes | **Fixed, part.** Record §13 lists C07, R1-11, the priority class, Plan A/B (named at signing; blank = B), the 24/7 plan, GEMS names, the Qwen3 server image, C: space, the Defender exclusion and non-elevation. *Not adopted:* "fill the Qwen3 image from Pierce's list": no such list exists; Hearth's server is Python at b5d3f14 (`python/hearth/server.py`, `hearth serve`), so `python`/`pythonw`, already excluded [inference]; the template's FILL became `excluded_images_at_signing` |
| F9 | major | e2e at its pilot placement first runs on night 1 | yes | **Fixed.** PRE-NIGHT A9: one attended `dev-run --config pilot.cfg --run-type e2e-decode` inside a window before night 1; `dev-run` now prints Δ_o, Δ_h, run wall, peak process memory and exit code; its values go into the pre-night amendment; a ceiling exceeded, a golden mismatch or a peak above 75% of the limit is a design revisit |
| F10 | minor | D0-7a still read as unanswered | yes | **Fixed** (record §3a, §10) |
| F11 | minor | The build script prints but does not check cl/CMake/Ninja; LF endings; A1 lacks `/setactive` and a standby check | yes (the root `.gitattributes` already checks `*.bat` out as CRLF; the working copy was LF) | **Fixed.** `build_pilot.bat [ROOT]` refuses on each mismatch (shown on modified copies [M]); CRLF in the working tree; A1 adds `powercfg /setactive` (24/7) and `powercfg /qh <GUID> SUB_SLEEP STANDBYIDLE` (reads 0 on AC on Balanced and High performance [M, read-only]) |
| F12 | minor | The dry night never ran the record's windows, a bracket-eligible run or the capped path | yes | **Fixed, part.** `pilot/dry-record.cfg`: record windows and start state, a 1.25-s bracket-eligible stand-in and a 2-s-capped stand-in [M, below]; the driver's own D: writes are in the start-state sample (record §10). *Not adopted:* real plants for input, RDP, Defender, GPU and the power scheme (they would touch the console or security software) |
| F13 | major | The owner actions with exact commands | yes | **Fixed.** PRE-NIGHT.md rewritten in the new order (0 decide, A1–A5, L1, A6–A9, L2, B) |

### Verified on the revision-5 build [M, desktop DESKTOP-8RS9J1J, 2026-10-23, `D:\mithril\x4rev4r`, LPs 26-28]

Every line below ran, in one sequence (17:15–17:25 desktop time = 14:15–14:25 PT), on exactly these
binaries of one `build_pilot.bat D:\mithril\x4rev4r` run (dev build, not pins): `x4svc.exe`
`b290899f94c7999a35323c8390510a8f2a1bea6fe046958f9e49ae7fa5bf1e0d`, `x4harness_hearth.exe`
`6d65c5b5d6e8d4b51f40718746954b8a22bb5caed1e3734d01d661964470dab1`, `x4sb_probe.exe`
`f1a5b271cb4db0746ffb83994255a3857651ad7d776478308534754ffc671e8c` (all six in
[`pilot/rev5-evidence-2026-10-23/SHA256-binaries.txt`](pilot/rev5-evidence-2026-10-23/SHA256-binaries.txt));
the raw outputs are in [`pilot/rev5-evidence-2026-10-23/`](pilot/rev5-evidence-2026-10-23/) (`final.txt`
is the sequence's own log). After that run only comments changed in `pilot.rs` (one line, same line
count), `dry-record.cfg`'s header and the docs; a cargo rebuild of the final sources passes the same 94
+ 4 tests and gives `x4svc.exe` `0873c5d836f6c4859a9d78632ec327d3f5909593858e5497dca128443fabf540`
(a relink; that the linker's time stamp alone makes the difference is [inference]; the pre-night amendment pins
the copy that will run). It is the `x4svc.exe` now in `D:\mithril\x4rev4r\bin`.
- **Build:** the script's checks passed (`cl` 19.44.35229 for x64, CMake 4.4.3, Ninja 1.12.1, rustc
  1.91.1, Hearth b5d3f14 clean); every step rc 0; **94 unit + 4 golden/differential tests pass** (85
  before; new: the estimator's 4, the canonical hash, the committed template filled = the record, the PDH
  fallback rules, the pins field diff, the night closure). The mutation table holds 76 single-value
  changes (21 new), each refused. **Refusals:** copies of the script with one expected version changed
  each print `REFUSED: cl is not 19.44.99999 for x64`, `REFUSED: CMake is not 4.4.2`, `REFUSED: Ninja is
  not 1.12.0` and stop before step [1].
- **Dev runs** (`dev-run`, new summary line): `mb_q4_avx512`, 2¹⁸ calls on LP 28: Δ_h 1.487744 s, run wall
  2.345 s, peak process memory 3.2 MB, Accept, golden `55b9c367…a036`; `e2e_decode`, N = 8, 1 + 1 threads,
  **8 GiB cache, 24 GiB limit**: Δ_o 2.70 s, **peak process memory 10,389,274,624 B (9.68 GiB, 40% of the
  limit)**, Accept, golden `86653fe54db5f08cd62905f71e654bfaf905d7851f1b3069df9f943f1de40f35` (as the
  revision-3 builder's `86653fe5…0f35`).
- **Record-window dry night** (`pilot/dry-record.cfg`, elevated, `--max-sessions 2`): 36 gates at 2 s /
  1 s / 60 s, **start state reached 36 of 36** (settle ≤ 1,001 ms, disk writes ≤ 650,914 B/s against the
  1,048,576 limit, no dropped LP, machine load ≤ 3.25%); **24 microbenchmark stand-in runs Accept with the
  bracket judged** (Δ_o 1.246–1.269 s, max τ margin 0.0225); **12 end-to-end stand-in runs TimeCapped** at
  2.007–2.009 s with the cool-down between them; both sessions completed, 0 discards. `pilot-estimate
  --dry-test` read the night: σ̂_d, B, σ̂_U, σ̂_run, the median, t_run, the R replay, every observe maximum
  with its 2x fill-in, the load threshold, the envelopes and the block-hours (`dry-record-night/`), and
  printed "DRY-RUN ACCEPTANCE TEST ... not pilot data"; asked for PILOT on the same directory it refuses.
- **Restricted token (F2, F3)**, `runas /trustlevel:0x20000`: `verify-hygiene --as-pilot`, revision 4:
  `[FAIL] process CPU ... unreadable listed images ["mpdefendercoreservice","msmpeng","searchindexer",
  "python" x5,"searchprotocolhost"]`; revision 5: `[ ok ] ... unreadable listed images []; read through PDH
  [the same nine]`; elevated: none needs PDH. The same pins file made elevated (every line kept) gives
  `fingerprint hash 6a58b257… != pinned e02fdb2b… (fields differing from the pins file: bios.version:
  pinned "1.G0 2024-12-19", now "unavailable"; board.product ...; cpu.logical_processors ...; cpu.model
  ...; disk.models_firmware ...; mem.configured_speed_mts ...; mem.modules ...)` (CIM through a
  restricted token; Pierce's real session may read them, which is why A7 makes the pins there).
- **Restricted token, one dry session each** (`dry-record.cfg`'s first session): **revision 4: hygiene void
  after 3 discards** ("background activity over the block: msmpeng CPU unreadable, mpdefendercoreservice CPU
  unreadable, searchindexer CPU unreadable[, searchprotocolhost CPU unreadable]"); **revision 5: 3 blocks,
  0 discards, completed**. With the background threshold set to 0.000001% of one core, revision 5 discards
  on real PDH readings: "msmpeng 0.879% ..., searchindexer 0.049% of one core over the planned block",
  then 1.123% and 1.221% [M, daytime], so the rule uses the reading. The orchestrator's own CPU per
  end-to-end stand-in block (the 250-ms poller included): 3.06% of one core elevated, 5.61% under the
  restricted token, where every poll also collects the PDH process counters (on its reserved LP).
- **Configuration binding (F5, F7):** `pilot-plan` on 22 variants of the filled committed template: the
  filled file, one with an `integrity_cleared` line and one with an empty signing list parse; **all 19
  others are refused**, including each of the reviewer's accepted ones (time cap 100000, memory 1 GiB for
  either run type, disk-write 1, extra excluded or background images, another record path, o_rt 1000,
  t_run,plan 5000 with cap 15000, another e2e harness, any tag name) and the new rules (no signing key,
  o_rt 5.5, pins or probe elsewhere, two harness hashes, a placeholder left). `config-hash`: the file and
  its copy with an `integrity_cleared` line have different file hashes and the same canonical hash
  `2da8c33c…683f`. `pilot-night --pilot` without `--config-sha256`, and with a wrong one, refuse before
  making anything; with the right one it proceeds to the window check and refuses outside the window;
  `D:\mithril-data` still does not exist.
- **Crash path (F6):** a dry night (`dry-crash.cfg`, a copy of `dry-record.cfg` with its own scratch)
  killed 30 s in: its manifest reads `status=open` (written before the first session); `pilot-estimate`
  refuses ("is open ... run `x4svc pilot-close`"); `pilot-close` writes
  `manifest-closed-after-interrupt.txt` (`interrupted=e2e-decode-01`, the open manifest's hash, progress
  by prefix) and appends `e2e-decode-01 interrupted`; a second `pilot-close` finds nothing open; the
  estimator then reads the night (`sessions_by_end = interrupted:1`, no block counted); one byte appended
  to `voids.log` afterwards makes it refuse ("voids.log does not match its manifest SHA-256").
- **Not shown here:** the restricted token is not Pierce's Medium token (its label reads High), so A8 in
  his session remains required; the PILOT path end to end (no signed record; refused outside a window);
  a cut-short last record line on a real crash (unit-tested only: the kill landed between writes); the
  e2e run type at its pilot placement (A9).
- **Residual (not fixed):** the night start does not refuse while another `x4svc` runs (a driver hung
  past 07:00 into the next evening would have its open manifest closed by the new night; `pilot-close`
  does refuse in that case) [G: rare]; `--dry-test` reads one dry night run without plants (plant sessions
  write no progress lines).

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
- **The noise pilot's "observe mode"**, the §10 hygiene sensors and the Hearth workload set were
  missing here on 2026-10-17; they were built on 2026-10-23 (see
  [Noise-pilot readiness](#noise-pilot-readiness-x4-pilot-track-2026-10-23), which also lists what is
  still not done).
- **No fingerprint/profile hash is pinned**, so `x4svc run` emits `Estimated`, never `Measured`;
  `--dev-self-golden` grades against the run's own first-pass hash and is a dev convenience only.
- **No full session calibration was run** (that is gate data). The session engine is unit-tested on
  scripted runs and, since 2026-10-23, drives real `hearth-c-ref` runs end to end in the dry run
  (`pilot-night --dry-run`), never in a pilot, A/A or calibration session;
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
- Added 2026-10-23 (X4 pilot track): `service/harness/{hearth_workloads.c,hearth_x4_shim.c}` (the Hearth
  workload set and the thread/condvar shim; `x4h_quiesce` and the pre-init settle in `x4h.{h,c}`);
  `service/orchestrator/src/{observe,pilotcfg,hygiene}.rs` (pure) and `{sensors_win,pilot}.rs`
  (Windows), with changes to `proto`, `sandbox`, `session`, `scheduler`, `profile_win`, `main`, `lib`;
  `service/tools/{build_pilot.bat,dev_regress.ps1,x4plant.c}`; `pilot/` (`dev.cfg`, `dry.cfg`,
  `pilot.cfg.template`, `verify-now.cfg`, `PRE-NIGHT.md`, `verify_report.ps1`, `VERIFY-2026-10-23.txt`,
  `dry-run-2026-10-23/`). The desktop build lives in `D:\mithril\x4c` (sources copied to `src\`, the
  Hearth build in `hearth-build\`, binaries in `bin\`); `D:\mithril\x4b` is the round-3 build.
- Revision 4 (2026-10-23, review round 4): changes to the files above (no new module); the
  `dry_quiesce_wake` probe in `hearth_workloads.c`; the dev-only build `x4harness_hearth_q0.exe`
  (never pinned); `pilot/VERIFY-2026-10-23-rev4.txt` and `pilot/dry-run-2026-10-23/rev4/`. The
  revision-3 binaries are kept in `D:\mithril\x4c\bin-r3\`.
- Revision 5 (2026-10-23, review round 5): `service/orchestrator/src/estimate.rs` (new, pure: the
  section 7 estimator, `x4svc pilot-estimate`); changes to `pilotcfg`, `hygiene`, `sensors_win`, `pilot`,
  `main`, `lib`; `service/tools/build_pilot.bat` (`[ROOT]`, version refusals, CRLF); `pilot/dry-record.cfg`
  (new), `pilot/pilot.cfg.template`, `pilot/PRE-NIGHT.md` (rewritten in the new order),
  `pilot/verify-now.cfg` (a comment); `pilot/rev5-evidence-2026-10-23/` (the raw outputs). The reviser's
  desktop build lives in `D:\mithril\x4rev4r` (sources in `src\`, binaries in `bin\`, jobs and logs in
  `jobs\`, the evidence folder `evidence\`).
