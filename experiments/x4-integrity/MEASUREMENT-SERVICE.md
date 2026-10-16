# X4 measurement service v0 — architecture

**Track:** x4-integrity. **Status:** DESIGN (implementation follows next). **Date:** 2026-10-16 (revision 2, after two same-family, independent-context reviews; see the [prereg review log](../../docs/m0/prereg/X4-integrity.md#12-review-log-independent-reviewers-with-model-family)).
**Anchors:** ROADMAP §3.5 (X4), §1 rule 4, §8 (M0 row), §10 (quiet hours); [06-forge §5, §6](../../docs/architecture/06-forge.md); [03-trust §9, §10, §14](../../docs/architecture/03-trust.md); DR-018; DR-023; D-22.

Every number in this file carries an evidence tag: **[M]** measured, **[D]** derived, **[S]** simulated, **[G]** judgment, **[inference]** inferred from a sibling doc, **[target]** a pre-registered threshold. Dossier numbers keep their source label, e.g. "7.16 GB/s (measured) [R11]". Simulated numbers come from [stats/x4_calibration.py](stats/x4_calibration.py) (seed 20261016, sha256 `6ac99140…`); the table and variant behind each is named in [stats/README.md](stats/README.md).

This document specifies the v0 measurement service that X4 calibrates and that every later performance gate uses. It is **F0** (trusted, frozen; [03 §14](../../docs/architecture/03-trust.md) caps it at ≤ 1,500 line-reviewed lines [target]). It is designed here and built next; nothing in X4 changes system settings — settings this service needs are emitted as exact commands **for Pierce to run** (§7), and the service **verifies** the profile and **refuses to run** when it is not met (§7.4).

---

## 1. What it is and what it is not

The service answers one request: *"is candidate B non-inferior to / faster than incumbent A on niche H, with anytime-valid evidence?"* It owns the clock, the process lifecycle, the interleaving and the statistics. Candidates never time themselves and never see the scorer (the lesson of every row in [03 §10](../../docs/architecture/03-trust.md)). It emits signed `Quantity<Unit, Origin>` facts and e-values, never a verdict (the Gatekeeper judges; [03 §9](../../docs/architecture/03-trust.md)).

In X4 it is exercised on `hearth-c-ref` against itself (A/A and planted-regression calibration, ROADMAP §3.5) and, through `hx_kernels`, on X3's generated kernels. It is **not** the Forge supervisor, **not** the sandbox (that is [SANDBOX.md](SANDBOX.md)), and **not** the Gatekeeper.

---

## 2. Language choice: a C harness child under a Rust orchestrator

**Decision [G]:** the per-run harness that starts the workload, owns the precise clock and joins all work is **C11**, statically linked with `hearth-c-ref`'s platform layer; the orchestrator that schedules sessions, holds the limits, keeps the integrity bracket (§3 step 8a), runs the e-processes and signs facts is **Rust**. Python is used only for offline analysis and the X4 calibration study ([stats/](stats/)), never on the measured path.

Justification, each point tied to evidence:

- **The precise clock and the join must sit inside the measured process, in the same ABI as the workload.** Hearth's own `hx_now_ns` is a monotonic C call ([hx_platform.h](../../docs/research/R11-hearth-port-requirements.md)) and its thread/pool joins (`hx_thread_join`, pool drain) are C [M, Hearth `engine/src/pool.c`, clone b5d3f14]. A C harness calls them directly with no FFI boundary between "stop the clock" and "the work finished", which is exactly the boundary CUDA-L1's unwatched-stream hack (82/250, 32.8%) and o3's timer overwrite (30.4% of RE-Bench runs) exploit [R01].
- **Mithril's own `mithc` cannot build F0** (S2, [06 §9](../../docs/architecture/06-forge.md)); and there is no Mithril compiler yet. The service must exist at M0, so it cannot be written in Mithril. It is built by the frozen bootstrap toolchain ([03 §9](../../docs/architecture/03-trust.md)).
- **The orchestrator wants memory safety, strong typing for `Quantity<Unit, Origin>`, and no runtime pauses.** Rust gives the typed fact schema (§9) and the e-process arithmetic (§8) without a GC, and it is the language the real `mithc` is written in (DR-026). The orchestrator never runs inside the measured process; it spawns the C harness as a child (under the Job Object of [SANDBOX.md](SANDBOX.md)) and reads back only typed results over a pipe.
- **Trust positions (corrected in revision 2).** For an in-process workload — `hearth-c-ref`, an `hx_kernels`-linked X3 kernel, and at M4 a Forge candidate — the workload **shares the C harness's address space**. It can in principle write the harness's `t0`, its poison salt and its output hash, so the in-process clock is the *precise* clock, not the *trusted* one. The three positions are: **(1) the limits**, held by the kernel on a Job Object whose only handle the orchestrator holds; **(2) the integrity bracket** — the orchestrator's own wall-clock bracket of the run, the job's CPU accounting, and the orchestrator's rehash of the output section (§3 step 8a) — held in the orchestrator process, where no workload code runs; **(3) the harness and the workload**, together in the child. A run counts only if (2) agrees with (3). Until binary T0 confinement exists (M4), (2) is the only defence against a workload that corrupts the harness; this is why a5 (timer overwrite) has an X4 detector at all ([HACK-SUITE.md §4.1](HACK-SUITE.md)).
- **Why not Python on the measured path.** The GIL, allocator and GC make the join and the timing non-deterministic, and Python is where the AI Scientist edited its own time limit [R01]. Python stays offline.

```
 Rust orchestrator  (F0; owns the Job Object handle, profile hash, alpha ledger, integrity bracket; signs facts)
    | CreateProcess: explicit env block, fresh scratch,            ^ typed result + START/STOP messages over a pipe
    |   job limits incl. affinity/priority (SANDBOX.md §2)          | orchestrator timestamps START/STOP itself (QPC)
    | creates the output SECTION, maps it into the child (RW)      | and maps the same section read-only for its rehash
    v                                                              |
 C harness process  (F0; hx_now_ns t0/t1, thread census, joins threads/pool/IO, MXCSR checks, poisons, hashes)
    | in-process call (same address space: NOT a trust boundary)  ^ output written into the orchestrator's section
    v                                                              |
 workload: hearth-c-ref @tag, or an hx_kernels-linked kernel/candidate (untrusted unless it is hearth-c-ref)
```

The split maps onto [03 §14](../../docs/architecture/03-trust.md)'s "measurement service ≤ 1,500 lines": the C harness is the clock/join/census/poison/hash core; the Rust orchestrator is the session loop, the integrity bracket, the e-process and signing. Both are line-reviewed and built by the frozen bootstrap.

---

## 3. One run: the clock contract

A **run** executes one arm (A or B) once. The orchestrator and the C harness do the following; steps marked (O) are the orchestrator's, the rest the harness's.

0. **(O) Launch into a fresh, identical context.**
   - A fresh process every run, created with an **explicit, minimal environment block** that is byte-identical for both arms and for the correctness stage. Hearth reads its configuration from the environment (`HEARTH_THREADS`, `HEARTH_IO_THREADS`, `HEARTH_CACHE_GB`, `HEARTH_ISA`, `HEARTH_LOG` in `api.c:119–128`, via `hx_env_*` in `platform_win.c:633–653` and `platform_posix.c:482`) [M, clone b5d3f14], so an inherited environment could configure the arms differently or let a workload tell timing runs from correctness runs. The block's SHA-256 enters `origin_proof` (§9).
   - A **fresh, empty scratch directory** per run, created by the orchestrator, granted to the child only, deleted after the run; bytes written to it are counted and recorded. Nothing persists from run *k* to run *k+1* except the profile-pinned machine state, which the start-state gate (§4.1) checks.
   - The job's affinity mask and priority class are set (§7.6).
   - **Every run is a fresh process with fresh scratch. The reference arm's outputs are never written anywhere the candidate's token can read. Goldens are compared out of process** (by the orchestrator, §3 step 8a). *(This replaces revision 1's sentence about running the candidate arm first, which contradicted the randomised ABBA/BAAB order of §4 and named the wrong risk.)*
1. **Gate the environment** (§7.4) and pass the **per-run start-state gate** (§4.1). If the profile hash does not match or any hygiene check fails, abort the run and discard its block (§5.3); never silently continue.
2. **Poison fresh allocations.** Every buffer the workload may read as input or write as output is a fresh allocation, pattern-filled (`0xA5` plus a per-run random 64-bit salt in the first and last cache line) and guard-paged. The **output buffer is a view of the orchestrator's section** (step 0), so the bytes the orchestrator rehashes are the bytes the workload wrote. This closes the `torch.empty` stale-reference reuse (METR) [R01]: a workload that forgets to write its output leaves poison, and the hash mismatches.
3. **Set and check the FP environment on every thread.** The default MXCSR (round-to-nearest, no FTZ/DAZ) is Hearth's MXCSR invariant [R11]. MXCSR is per thread, so a check on the harness thread alone misses a worker that sets FTZ/DAZ, or a change restored before return. The harness therefore (a) wraps `hx_thread_create` so every Hearth-created thread (pool workers `pool.c`, store readers `store.c:971`, loader workers `modelfile.c:576` [M, clone]) asserts the default MXCSR on entry, and (b) after `t1` suspends every other thread in the process in turn and reads its `CONTEXT.MxCsr` (`GetThreadContext` with `CONTEXT_FLOATING_POINT`; the x64 `CONTEXT` carries MXCSR [inference from the Windows SDK headers; not exercised on this box]), asserting the default, then resumes it. Any non-default value **rejects the run** as a9 (an integrity failure, not a hygiene void). The a9 plant includes a denormal-producing input so the output-hash route is exercised too ([HACK-SUITE.md](HACK-SUITE.md) a9).
4. **Start the clock.** Send `START` to the orchestrator (typed, one message), then `t0 = hx_now_ns()` (monotonic) [M, Hearth]. Snapshot the process's thread list and per-thread CPU times (`GetThreadTimes`). The workload has **no `time` capability**; RDTSC/RDTSCP/RDPMC are banned in Forge candidates by T0 ([03 §6.2](../../docs/architecture/03-trust.md)). In X4 the ban is not enforceable on the binary, so integrity rests on step 8a.
5. **Run the workload** to its declared stopping point (N decode tokens, or K matvec repetitions).
6. **Join everything before stopping the clock, then take a thread census.** All registered threads joined or parked (`hx_thread_join`; pool tasks drained to the quiescent state), and all outstanding I/O completions reaped (Windows: every overlapped request's event signalled and `GetOverlappedResult` returned; POSIX: completions reaped) **before** `t1 = hx_now_ns()`. `STOP` is sent to the orchestrator immediately after `t1`, so the orchestrator's bracket closes where the harness clock does. Then, before the hash:
   - **Thread census.** Enumerate the process's threads (`CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD)` filtered by PID). **Any thread created after `t0` that was not created through the registered `hx_thread_create` wrapper rejects the run** — this covers a raw `CreateThread`/`_beginthreadex`, an OS thread-pool callback (`TrySubmitThreadpoolCallback`, timer queues) and anything else that creates a thread. Hearth's engine creates threads only through that wrapper (`platform_win.c:212` is the one `CreateThread` in `engine/src`, and there is no `_beginthreadex`) [M, grep of the clone at b5d3f14, 2026-10-16]. Threads that existed before `t0` (including the Windows loader's worker threads, which a fresh process may still hold [inference; not observed here]) are allowed, subject to the CPU rule.
   - **Post-`t1` CPU rule.** Read every thread's CPU time again just before the hash. Any thread other than the harness thread that consumed more than its allowance in `[t1, hash]` **rejects the run**: a pool worker may spin for Hearth's pool spin window (`POOL_SPIN_US` = 50 µs, `model.c:58` [M, clone]) plus ε_spin; every other thread gets ε_idle. Both ε are pre-registered from the pilot (§5.4) [target]. This is the a3b detector: work that finishes between `t1` and the hash leaves CPU time on some thread after `t1`.
   - **Freeze the output.** `VirtualProtect` the output view `PAGE_READONLY` before hashing; a late write faults and rejects the run.
   GPU streams are later (by-trigger, DR-022).
7. **Materialise and hash the output.** The harness reads the output as a materialised value (never a thunk/lazy tensor, CUDA-L1 [R01]) and computes its hash. The harness's hash is a cross-check; **the hash that counts is the orchestrator's** (step 8a). For exact slots it is compared to the meaning's golden; for `timing_only` policies to the incumbent's logits hash on every run ([06 §5.1](../../docs/architecture/06-forge.md)). A mismatch rejects the run and quarantines the candidate.
8. **Report** `(t1 − t0, harness_output_hash, counters, thermal_start, thermal_end, background_sample, thread_census, mxcsr_ok, affinity_ok, start_state)` to the orchestrator as typed fields (after `STOP`, which step 6 already sent).
8a. **(O) Out-of-process integrity bracket** (new in revision 2; closes the in-process gap of §2):
   - **Wall bracket.** The orchestrator timestamps receipt of `START` and `STOP` with its own `QueryPerformanceCounter`, on its reserved logical core ([06 §6.7](../../docs/architecture/06-forge.md)): Δ_o. The run counts only if |Δ_h − Δ_o| ≤ τ_clock, where Δ_h = t1 − t0 and **τ_clock = max(1 ms, 2 × the pilot's largest |Δ_h − Δ_o|)**, capped at **0.1% of Δ_o** [target]. A timer overwrite that shaves 3% off a 10 s microbenchmark run (≈ 300 ms [D]) is two orders of magnitude above that cap. If pilot jitter exceeds the cap, this design is revisited before collection, never loosened after.
   - **Orchestrator rehash.** On receipt of `STOP` the orchestrator copies the output section (it is small: logits or a kernel output) and hashes the copy; this hash is the run's `output_hash`. It must equal the harness's hash and the golden/incumbent hash. Work that continues after `STOP` changes the section after the copy and fails the comparison with the harness's later hash.
   - **Job CPU accounting.** The orchestrator reads `JOBOBJECT_BASIC_ACCOUNTING_INFORMATION` (total user + kernel time) at `START`, at `STOP`, and after it terminates the job (it terminates the job as soon as it holds the copy and the typed report). CPU charged after `STOP` must be ≤ κ_post [target, from the pilot: 2 × the pilot's 99.9th percentile]; more means the workload kept running after the clock stopped.
   - Any failure here is an **integrity failure**: the run is rejected and the candidate quarantined, with a ledger fact naming stage measurement (6). It is not a hygiene void and is never re-run silently.
9. **(O) Tear down.** Delete the scratch tree; record bytes written, peak memory (`PeakProcessMemoryUsed`) and the census.

**Warm vs cold.** Both are supported. A cold run first evicts the model bytes: direct I/O (`FILE_FLAG_NO_BUFFERING`, used by Hearth's `hx__open` at `platform_win.c:380` [M, clone]) so the Windows standby list never holds them between runs [R11], plus a CLFLUSHOPT sweep or eviction-buffer pass over the working set, because WBINVD is ring 0 and `perf_event_open` does not exist on Windows [R08]. The cold/warm choice is part of the niche key and identical for A and B.

---

## 4. Blocks, interleaving and the load gate

A **block** compares A and B back to back in a randomised **ABBA** or **BAAB** order (each run in a fresh harness process with identical thread placement). **ROADMAP §3.5's "ABAB interleaving" is implemented as randomised ABBA/BAAB, which is more precise and not looser: ABBA cancels linear drift within a block, literal ABAB does not.** The block statistic is the paired mean log-ratio `d = log(T_B / T_A)` ([06 §6.1](../../docs/architecture/06-forge.md)):

- log-ratios make effects multiplicative, so the margin δ = 3% is `log(1.03)` [D];
- ABBA cancels linear drift within a block; random order makes position effects mean-zero [inference, 06 §6.1]. With identical binaries this randomisation alone makes d conditionally symmetric whatever the drift (§8.2).

**Load gate.** Interleaving is mandatory for e-process validity under drift ([06 §6.2](../../docs/architecture/06-forge.md)); it is only *entered* once the load gate passes:

- the profile hash matches (§7);
- a quiet window is active (§7, [06 §6.8](../../docs/architecture/06-forge.md));
- the 2-second CPU load is below a **calibrated** threshold. Hearth's practice on a busy machine is 40% [R11; `engine/tools/hearth_bench.c` itself does not gate]. X4's rule [target]: threshold = min(40%, the pilot's 99th percentile of pre-run 2-s load + 2 percentage points);
- background services idle (§7.3 hygiene);
- NVMe temperature below threshold, no large writes in the settle interval.

If the gate drops mid-block, the block is discarded (not scored). Three or more discarded blocks in one session [target] make it a hygiene void (§5.3). **Discard and void decisions are computed by a function that does not receive the e-process state** (§5.3).

### 4.1 Per-run start-state gate (new in revision 2)

A fresh process does not reset package temperature, NVMe SLC/GC state, the modified-page list or power state, so one arm's run can tax the next (ABBA/BAAB is unbiased only without such carry-over). Before **every** run's `t0` the harness checks, and records in the run fact:

| Item | Source | Pass rule [target, values from the pilot] |
|---|---|---|
| CPU package temperature, effective clock of the measured core(s) | read-only sensors (the same source as §5.2's thermal fields) | within the pilot's 1st–99th percentile envelope of pre-run values, ± 2 °C / ± 2% |
| Modified (dirty) page list | `Memory\Modified Page List Bytes` performance counter | ≤ the pilot's 99th percentile + 64 MiB |
| Outstanding disk writes | `PhysicalDisk\Current Disk Queue Length` and write bytes/s over 1 s | queue 0 and write rate ≤ 1 MiB/s |
| NVMe SMART temperature (NVMe-bound runs) | SMART, read-only | below the §7.4 threshold |

If an item fails, the harness waits (up to a settle timeout of 60 s [target]) and re-checks; on timeout the block is discarded (a hygiene discard, blind to the e-process). Whether every counter is readable by the non-admin measurement user is **unverified on this box** [known weakness].

**Carry-over contrast (reported secondary).** From the position structure — in ABBA the second A follows B; in BAAB the first A follows B and the second follows A — the service estimates first-order carry-over: `co_BA = mean(log T_A | previous run B) − mean(log T_A | previous run A)` and `co_AB` likewise for B, and reports `co_BA − co_AB` with its standard error [D]. A planted carry-over saboteur (a15c) must be caught by the start-state gate or flagged by this contrast.

---

## 5. Poisoned allocations, fingerprint, stationarity — the hygiene core

### 5.1 Poisoned fresh allocations
As §3 step 2. The pattern and salt are regenerated per run; the harness asserts, after the workload, that output buffers were fully overwritten (no residual poison byte survives in the declared output extent) and records the assertion in the fact. [Closes R01 rows 7, 9.]

### 5.2 Hardware fingerprint (the machine-profile hash)
A run carries a fingerprint; a mismatch voids every dependent measurement and `PruneCert` ([06 §5.2](../../docs/architecture/06-forge.md)). Contents, each a stable field:

| Field | Source | Why |
|---|---|---|
| CPU model, stepping, microcode revision | CPUID + OS | silicon identity; microcode changes codegen behaviour |
| BIOS/AGESA version, PBO/Curve-Optimizer state | OS/WMI (read-only) | cross-CCD latency changed with AGESA [R08]; boost affects clocks |
| Memory speed and timings (DDR5 rating, actual) | SPD/WMI | the machine runs above its official DDR5-5600 rating [RV: D3-ii] |
| Per-CCD topology, FCLK | CPUID/OS | one CCD caps at 64 GB/s read [R08]; placement must match A/B |
| PCIe generation and width per drive | OS | 7.877 GB/s phys for PCIe 4.0 x4 [R08] |
| NVMe model, firmware, capacity, free space, SLC state hint | SMART | SLC/GC and thermal affect reads [R08] |
| I/O mode (direct/buffered), OS build, active power-plan GUID | OS | buffered I/O adds page-cache capacity [RV: D3-ii] |
| GPU driver version (for later D0-6) | OS | reserved; not in scope until DR-022 |
| Core id + SMT-sibling-idle flag used for single-thread runs | harness config | per-core boost varies with CPPC preferred cores [06 §6.7] |
| **Job affinity mask and priority class** (§7.6) | job limits | CCD pinning; identical for A and B |
| **Environment-block hash** (§3 step 0) | orchestrator | identical configuration for both arms and all stages |

The hash is over the canonical serialisation of these fields. The harness reads them; it never sets them (the job limits are set by the orchestrator through documented job APIs, not system settings). The expected hash for an X4 session is pinned in the pre-registration ([prereg/X4-integrity.md](../../docs/m0/prereg/X4-integrity.md)).

### 5.3 Voids, stationarity and the tally rules (rewritten in revision 2)

[06 §6.3](../../docs/architecture/06-forge.md) voids a session when the A/A sentinel e-process exceeds its threshold, a monotone-trend test exceeds the profile envelope, the incumbent's median leaves its envelope, or a closing check fails; [06 §6.1](../../docs/architecture/06-forge.md) step 2 voids it when the session's σ̂ leaves the profile envelope. Revision 1 copied those rules; the reviews showed that the sentinel rule could not fire, that a voided-and-re-run session could select away bad outcomes, and that the trend test was under-specified. X4 now pre-registers the following.

**Three kinds of failure, kept apart.**

| Kind | Triggered by | Effect on the session | Effect on calibration tallies |
|---|---|---|---|
| **Integrity failure** | §3 step 3 (MXCSR), step 6 (census, post-`t1` CPU, late write), step 7/8a (hash, bracket, accounting) | the run is rejected and the candidate quarantined; never re-run silently | not a void: in a planted-hack run it is the catch; in an A/A run it is an evaluator bug that stops the calibration |
| **Hygiene void** (external sensors only) | profile-hash mismatch; Defender/indexer/Update activity; interactive use; load gate failing on ≥ 3 blocks; start-state gate timeouts (§4.1); closing temperature check | session void, re-run | removed from the tally, counted in the void rate |
| **Statistical void** | rules S1–S4 below | session void, re-run | **stays in the tally**; if its tested e-process had reached 20 before the void, it **counts as an alarm** |

**Blindness.** Discard and void decisions are computed by a function whose inputs are sensor readings, run times and the calibration/sentinel blocks; its type has no access to the wealth of any tested e-process. The wealth at every void and discard is nevertheless **logged**, and two checks flag a session series (calibration amber; in production, Adversary review): (a) per-arm discarded-run counts — an exact two-sided binomial test of B-discards against A-discards at p = 0.5, α = 0.01 [target]; (b) the log-wealth at void times against the log-wealth at the same block index in non-voided sessions — one-sided Mann–Whitney toward low wealth, α = 0.01 [target].

**Statistical voids (each two-sided at α = 0.01 [target]).**
- **S1 — sentinel mean (label asymmetry).** On the sentinel blocks without a run-outlier flag: void if |mean d_sent| > z₀.₉₉₅ · σ̂_pilot / √k′ (k′ = unflagged sentinels). *Why not revision 1's rule:* the sentinel superiority e-process at θ = 0.5 can grow by at most 1.5× per block, so with 2 sentinels (σ_d 2%, N = 12) its wealth cannot exceed 2.25, and with 8 (σ_d 4%) it reaches 20 only if all 8 sit at the clip (25.6) [D]. The rule could never fire.
- **S2 — variance envelope (06 §6.1 step 2).** On the calibration and sentinel blocks without a run-outlier flag, clipped at c: void if Σx²/m falls outside [χ²₀.₀₀₅,ₘ/m, χ²₀.₉₉₅,ₘ/m] · σ̂²_pilot. Outlier-flagged blocks are excluded because outliers are already loss-scored (§8.1). With n_cal = 2 and m ≥ 4 the envelope is wide, as R2 noted; it is a guard against gross noise inflation, not a precise σ̂.
- **S3 — trend.** A two-sided Mann–Kendall test on **each arm's** per-run log-times, with the Hamed–Rao variance correction **restricted to lag 1, always applied, floored at 1**; void if either arm rejects. *Why this form:* in simulation the full Hamed–Rao correction (every significant lag) was liberal at these sample sizes — 10.0% false voids at σ_d 2% and 3.0% at 4% with iid noise, against ≈ 2% nominal for two arms — while the lag-1 form gave 2.2% / 1.0% under iid noise and 6.0% / 4.0% under AR(1) φ = 0.6 noise, with ≥ 0.96 power against a monotone drift of 3σ over the session [S, stats/ table 3f]. The trend test is **not** run on the sentinel d: with randomised order, A/A d is conditionally symmetric under any drift, so a trend there is not expected even when the machine drifts. The trend in the A/B block d is **reported only** (it indicates an effect that drifts, which makes the null ill-posed) and never voids.
- **S4 — incumbent median envelope.** Void if the incumbent's session-median log-time leaves pilot grand median ± max(3·s_between, 1%), with s_between the SD of the pilot's session medians [target].

Simulated false-void rates of S1+S2 together, in planted-regression sessions: 1.7–2.3% at σ_d 2% for outlier rates 0–5%, and 1.7–6.0% at σ_d 4% [S, table 3e]; S1+S2 detect a 2% label asymmetry within one session only 13–14% of the time [S, table 3e] — the pooled test (§8.2) is the real asymmetry detector.

**Pure A/A calibration sessions have no sentinels** (every block is A/A; the tested superiority e-process is itself the A/A statistic). S2 uses all blocks; S3 and S4 apply.

**Tally rules for calibrations.**
- The counted set is **exactly the first 100 sessions that are not hygiene-voided**, in a pre-registered randomised schedule (the order of A/A, planted-3%, planted-4% and end-to-end sessions across nights is drawn once, before the first session, and its seed is pinned).
- A statistically voided session stays in the count; its alarm, if any, counts.
- **Void-rate bound:** if more than 10% [target] of a calibration's sessions are voided (both kinds), the calibration is **amber, not pass**, and the void rate feeds D-22.
- Every calibration tally is reported **with and without** the voided sessions.

**Production gates (M4 on).** A void never hands a candidate another try at the same α_i: α_i is charged **per session attempt** (§8.6), and the re-run is a new attempt with a new charge.

### 5.4 Pilot-derived parameters (the σ-pilot)

Every data-dependent constant is fixed **by a frozen rule from a pilot that no gate judges** — the X4 noise pilot of [PLAN §8](../../docs/m0/PLAN.md) (record `X4-noise-pilot`): 20 microbenchmark A/A sessions × 24 blocks and 3 end-to-end A/A sessions × 12 blocks [target], excluded from every tally. The values are filled in by a dated *pre-data fill-in amendment* to the X4 record before the first counted session. The rules:

| Parameter | Rule [target] |
|---|---|
| σ̂_d (per run type) | pooled SD of the pilot's A/A block d (hygiene-voided blocks removed) |
| σ̂_U (for planning) | one-sided 90% upper bound: σ̂_d · √((B−1)/χ²₀.₁₀,B−1), B = pilot blocks |
| n, N | n = max(6, ⌈12 σ̂_U² / δ²⌉), δ = 3%; N = 2n |
| c, c_kill, c_run | c = max(3σ̂_d, 2 m_NI); c_kill = max(3σ̂_d, m_kill + 3σ̂_d); c_run = 4σ̂_run, σ̂_run = pooled within-session SD of per-run log-times |
| p0 (tail check) | one-sided 95% Clopper–Pearson upper bound of the pilot's slow-outlier rate per run (R scorer) |
| S4 envelope | pilot grand median, s_between |
| Load-gate threshold | min(40%, pilot 99th percentile of pre-run 2-s load + 2 pp) |
| §4.1 envelopes | as in the §4.1 table |
| τ_clock, κ_post, ε_spin, ε_idle | 2 × the pilot's largest observed value (τ_clock also floored at 1 ms and capped at 0.1% of Δ) |
| Planted levels (§8.3) | K′ from the clip-bias formula at σ̂_d |

---

## 6. STREAM / NVMe profiler: `mithc profile measure`

`mithc profile measure` runs inside the evaluator so floors rest on this exact box ([06 §5.2](../../docs/architecture/06-forge.md), [02 §13.2](../../docs/architecture/02-compute.md)). In X4 it is a C+Rust tool (no `mithc` yet); the verb name is reserved for M2. It records, as `Quantity<_, Measured{fingerprint}>`:

- **STREAM per CCD and all-core.** Triad/Copy/Scale/Add, threads pinned to one CCD and then spread across both. Expected: ≈ 64 GB/s per-CCD read cap, ≈ 77 GB/s all-core (measured AIDA64) [R08]; the **phys** ceiling is 96 GB/s (DDR5-6000 dual channel) [R08]. These seed the `emp` bound as `emp_bound = min(phys, max observed × (1 + h))`, h ≥ CI + 5% [inference, 02 §13.2].
- **NVMe request-size × queue-depth grid.** Request sizes spanning Hearth's slab sizes (2.39 MiB Qwen3, 22.3 MiB Kimi) [R11] × queue depths; direct I/O. Expected demand-read peak ≈ 7.16 GB/s, prefetch batch ≈ 6.72 GB/s [R11]; **phys** ceiling 7.877 GB/s (PCIe 4.0 x4) [R08]. Mirrors sum links; a shared chipset uplink caps via `io_cap_gbs` [Hearth SIMULATOR.md].
- PCIe H2D/D2H and a VRAM GEMV are **reserved** (D0-6, DR-022); not measured in X4.

**Bound tiers (normative, [02 §13.2](../../docs/architecture/02-compute.md)).** Only `phys` (link/DIMM/datapath limits) and audited `emp` peaks may prune or quarantine; `est` (the simulator's time model) may only rank. A measured peak is a lower bound on the attainable roof, so an `emp` term enters as an upper bound only with pre-registered headroom. This is the F1-sim plausibility input ([F1-SIM.md](F1-SIM.md), [06 §5.3](../../docs/architecture/06-forge.md)).

---

## 7. Quiet-machine profile — settings Pierce runs, service verifies

**We never change system settings; those are Owner decisions ([06 §6.7](../../docs/architecture/06-forge.md), DECISIONS.md).** Each setting below is listed as (a) the exact command **for Pierce to run** and (b) how the service **verifies** it at gate time and **refuses to run** on mismatch. Commands are PowerShell / elevated where noted; the service reads state read-only. None of these commands has been run by the X4 track.

> Verification policy: the service reads each item into the fingerprint (§5.2) or a boolean gate. On any mismatch it **refuses the session** with a diagnostic naming the failing item and the command to fix it. It never edits the setting.

### 7.1 Power plan and boost
- **Set (Pierce, elevated):** create and select a dedicated measurement plan, so the GUID is pinned in the fingerprint:
  ```
  powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c MITHRIL-MEASURE
  powercfg /setactive MITHRIL-MEASURE
  powercfg /setacvalueindex MITHRIL-MEASURE SUB_PROCESSOR PROCTHROTTLEMIN 100   # optional: disable idle downclock
  powercfg /setactive MITHRIL-MEASURE
  ```
  (The GUID after `/duplicatescheme` is the one `powercfg /list` prints for MITHRIL-MEASURE; record it. `powercfg` may require the new scheme's GUID rather than a name in the later commands; use the GUID it printed. Not run here.)
- **Verify:** `powercfg /getactivescheme` GUID equals the pinned one, read into the fingerprint. Refuse if different. [A dedicated plan is an Owner choice, 06 §6.7.]

### 7.2 Core parking and CPPC preferred cores
- **Set (Pierce, elevated):** expose and disable core parking so single-thread pinning is stable:
  ```
  powercfg /setacvalueindex MITHRIL-MEASURE SUB_PROCESSOR CPMINCORES 100
  powercfg /setacvalueindex MITHRIL-MEASURE SUB_PROCESSOR CPMAXCORES 100
  powercfg /setactive MITHRIL-MEASURE
  ```
- **Verify:** query the active plan's `CPMINCORES`/`CPMAXCORES` (via `powercfg /query MITHRIL-MEASURE SUB_PROCESSOR`); refuse if parking is enabled.

### 7.3 Defender and Search indexer exclusions
- **Set (Pierce, elevated — security trade-off, Owner's call [06 §6.7]):** exclude the data directory (traces, model bytes, scratch) from real-time scanning and from the Search indexer:
  ```
  Add-MpPreference -ExclusionPath 'D:\mithril-data'
  # Search indexer: remove the data dir from indexed locations in
  #   Control Panel > Indexing Options  (no stable CLI; documented step for Pierce)
  ```
- **Verify:** `Get-MpPreference | Select-Object -Expand ExclusionPath` contains the data dir; the service **samples Defender and the indexer activity around each block** ([06 §6.7](../../docs/architecture/06-forge.md)) and **discards** any block during which either is active (a hygiene discard, §5.3). The exclusion is recommended, not required: without it the service still runs but discards more blocks (void rate feeds D-22).
- **Windows Update / maintenance:** windows avoid the scheduled maintenance hour; the service samples Update/maintenance activity and discards on hit. Pierce confirms the maintenance window:
  ```
  Get-ScheduledTask -TaskPath '\Microsoft\Windows\TaskScheduler\' | Where-Object State -ne 'Disabled'
  ```

### 7.4 NVMe thermal and SLC
- **Set (Pierce):** no setting to change; keep ≥ ~20% free space so the SLC cache behaves [G], and avoid large writes before a session. The service records SMART temperature and free space.
- **Verify:** SMART temperature at start and end below the pre-registered threshold [target]; a cool-down between NVMe-bound runs (factor c ≈ 1.5, [ROADMAP §10](../../docs/ROADMAP.md)); no large write within the settle interval; and the per-run start-state gate (§4.1). Refuse/void otherwise.

### 7.5 Scheduler lock during quiet windows
- **Set (Pierce):** declare the quiet window (e.g. overnight) and grant the unattended-run authority (D0-7). During a window the supervisor holds a machine-wide lock: no agent sessions, compiles, object audits or local generation (DR-023).
- **Verify:** the service checks it holds the lock and that no excluded process class is running; it yields to interactive use at once and hygiene-voids the running session ([06 §6.8](../../docs/architecture/06-forge.md)).

### 7.6 CCD pinning, affinity and priority (new in revision 2)
ROADMAP §3.5 lists CCD pinning in the quiet-machine profile; revision 1 had no control for it, so nothing stopped a B process raising its own priority or moving its threads to the faster CCD.
- **Set (orchestrator, per job — not a system setting):** `JOB_OBJECT_LIMIT_AFFINITY` and `JOB_OBJECT_LIMIT_PRIORITY_CLASS` on the job, **identical for both arms**. Microbenchmarks: affinity = the one pinned physical core (SMT sibling left idle, [06 §6.7](../../docs/architecture/06-forge.md)); end-to-end decode: the production placement across both CCDs minus the orchestrator's reserved logical core. Priority class: `NORMAL_PRIORITY_CLASS` [target]. The kernel enforces both on the job; a process in the job cannot widen them.
- **Verify (harness, after the run):** every thread's affinity is within the job mask and every thread's priority equals the declared value (Hearth sets neither — it only reads the process mask, `platform_win.c:241` [M, clone]); a thread that changed its own relative priority (`SetThreadPriority`, which the job limit does not block) or narrowed its affinity to a different core set than A's **rejects the run** (integrity; a31). The mask and class enter the fingerprint (§5.2).

**Profile hash.** §5.2 fields plus the gate booleans above form the profile hash. The service refuses to emit any fact under a hash that does not match the session's pre-registered expected hash. This is the mechanism by which "quiet-machine profile not met → refuse to run" is enforced, as ROADMAP §3.5 requires.

---

## 8. Anytime-valid e-values: the exact e-processes

All three nulls use a **betting (test-martingale) e-process on a clipped block statistic** ([06 §6.2](../../docs/architecture/06-forge.md)). Betting martingales are valid for every bounded distribution in a composite null; a Gaussian likelihood ratio is not [inference, 06 §6.2]. Validity rests on Ville's inequality: under H0, `P(sup_n K_n ≥ 1/α) ≤ α`, where `K_n` is the wealth process. Every constant below is pinned in `PREREG` in [stats/x4_calibration.py](stats/x4_calibration.py) and copied into the prereg §7.

### 8.1 The clipped statistic and the scorers (one gate scorer, named)

Per slot, a symmetric clip `c` is pre-registered **before collection** by the pilot rule (§5.4) [target]:
```
c = max(3 · σ̂_d , 2 · m_NI),      m_NI = RN(ln 1.03) = 0x1.e44a9a3bed663p-6
```
Four scorers exist; **exactly one drives each gate**.

| Scorer | Rule | Used for |
|---|---|---|
| **R (gate scorer)** | a *run* is an outlier if it deviates from its own arm's running median (earlier runs of this session; before the arm has any, the incumbent's; before that, the pilot incumbent median) by more than `c_run = 4σ̂_run`; a block with an outlier run is scored **+c**; otherwise `x = clip(d, −c, c)` | superiority and non-inferiority, every gate |
| **S** | `x = clip(d, −c, c)`, no loss scoring | the A/A calibration's second statistic (§8.2) |
| **Rk** | as R, but a block with an outlier run is scored **−c_kill** | the kill e-process only (§8.4) |
| 06 literal | `x = d` if \|d\| ≤ c, else **+c** | descriptive only, reported beside R |

**R is named as the gate scorer provisionally, pending owner question 4.** [06 §6.2](../../docs/architecture/06-forge.md) is normative and specifies the literal block rule; its literal form scores a large *true improvement* as a loss — a 20% improvement never reaches 20 within 400 blocks under the literal rule (share 0.000 at σ_d 1%, 2% and 4%), and a 5% improvement at σ_d 2% needs a median of 155 blocks against 10 under R [S, stats/ table 2e]. X4 may not amend 06; it proposes R and asks the Owner to confirm or amend. If the Owner keeps the literal rule before freeze, the literal rule becomes the gate scorer and the calibration is re-simulated; in no case are two scorers allowed to pass a gate ("either passes" would be two looks).

The estimand of each gate is `E[x]` under its scorer; facts also report the unclipped mean and the per-direction outlier counts. Outlier scoring as **+c** is conservative for superiority and non-inferiority (an outlier can never help the candidate) and **anti-conservative for the kill test** (it pushes toward a false kill) — hence Rk (§8.4).

### 8.2 Superiority e-process (promotion / A/A null)
- **Null** `H0: E[x] ≥ 0` (the candidate is no faster). Rejecting it shows an improvement (E[x] < 0), not an improvement of at least the MDE ([06 §6.5](../../docs/architecture/06-forge.md)).
- **Bet variable** `g = −x/c`, so `g ≥ −1` and `E[g | past] ≤ 0` under H0 (x ≤ c by construction).
- **Wealth** `K_n = Π (1 + λ_i g_i)`, `λ_i ∈ [0, θ]` predictable, θ = 0.5 [target]. **Reject (declare superiority) when `K_n ≥ max(20, 1/α_i)`** (DR-018 floor; α_i charged on entry to stage 6, [06 §6.5](../../docs/architecture/06-forge.md)). Because λ ≤ 0.5 and g ≤ 1, wealth grows at most 1.5× per block, so 20 needs **at least 8 blocks** (log 20 / log 1.5 = 7.39 [D]); at σ_d 2% (N = 12) a crossing can only happen in blocks 8–12.
- **What the A/A calibration tests (corrected in revision 2).** With identical binaries and randomised ABBA/BAAB order, d is conditionally symmetric about 0 **whatever the drift** (the two orders give d and −d for the same run noise), so the A/A false-alarm rate is held below Ville's 5% by the randomisation alone. The A/A gate therefore tests **harness label symmetry** (does the service treat "A" and "B" differently?), not the desktop's exchangeability in general; drift that interacts with a *real* difference between A and B is invisible to it. ROADMAP §3.5 says the A/A rule "tests exchangeability on this desktop"; X4 reads that as label exchangeability and raises the wording as owner question 8. Its power is low at small N: a 2% label asymmetry crosses within N in 0.20% of sessions at σ_d 2% and 50.0% at σ_d 4% (R scorer, aGRAPA) [S, table 2b]. The AR(1) φ = 0.6 rows give 0.0000 at both σ_d [S, table 2b], as the symmetry argument predicts.
- **A/A gate (ROADMAP §3.5, made more precise).** ≤ 2 of ≥ 100 microbenchmark sessions reach 20 **under R and, separately, under S** [target]; both must pass. S has no loss scoring, so it does not bias the statistic against superiority and is the more sensitive to label asymmetry (2% asymmetry, σ_d 4%, 2% outliers: 0.463 under S against 0.363 under R [S, table 3b]). The gate horizon is N (the longest a single superiority test runs, §8.6); running the A/A sessions to 2N is offered to the Owner with its cost (owner question 9).
- **Tightening secondaries (they can turn a pass into amber, never a fail into a pass).**
  - *Pooled mean test:* a two-sided z-test of the mean symmetric-clipped A/A d over all counted microbenchmark blocks (≈ 100 × N: 1,200 at σ_d 2%, 4,400 at 4%) at α = 0.01 [target]; SE ≈ 0.058% / 0.060% [D]; power 0.81 / 0.77 against a 0.2% asymmetry and ≈ 1.00 against 0.5% [D, table 3b]. A rejection makes the A/A calibration amber (find the label asymmetry, fix, re-run on fresh sessions).
  - *A/A′ layout arm:* 20 microbenchmark sessions [target] of `hearth-c-ref` against **A′, the same source linked in a permuted object order** (bit-identical outputs, byte-different binary). Identical binaries cannot reveal layout effects that separate any real candidate from the incumbent [Mytkowicz et al., "Producing wrong data without doing anything obviously wrong", ASPLOS 2009 — cited from memory, not re-checked]. The A vs A′ mean d and its CI are reported as the layout-noise floor; it is descriptive, and an MDE below it is flagged.
  - *Stationarity positive control:* 10 sessions [target] with a fixed (non-randomised) AABB order under a planted heater ramp calibrated in the pilot to ≥ 3σ̂_run of drift over a session; **S3/S4 or the start-state gate must void ≥ 9 of 10** [target]. Simulated S3 power at a 3σ ramp: 0.96–1.00 [S, table 3f]. This proves the voids can fire; it is not part of the A/A count.
- The exact binomial OC of the ≤ 2/100 rule is in [stats/](stats/) §1: 0.9206 / 0.1183 / 0.0113 at true rates of 1% / 5% / 8% [D], confirming ROADMAP's 0.92 / 0.12 / 0.01 [inference] to two decimals; the rule fails an e-process sitting exactly at Ville's bound (5%) with probability 0.88 [D], and passes half the time at 2.7% [D]. Those figures assume independent sessions; with sessions sharing nights (intra-night correlation 0.05, 4 nights × 25) the pass probability at a true 5% rate rises to 0.24 and at 8% to 0.06 [D, table 1b] — correlation makes the rule more lenient, which the schedule's spreading of sessions across nights mitigates.

### 8.3 Non-inferiority e-process on a ratio, with blocks (parity gate)
- **Null** `H0: E[x] ≥ m_NI` (the candidate is at least 3% slower) ([06 §6.2](../../docs/architecture/06-forge.md), DR-018). **Margins, stated:** `m_NI = log 1.03` (time) is the **stricter** reading of ROADMAP §1 rule 4's "ratio < 0.97" (throughput); under the literal reading `−log 0.97 = 0.03046` a 3% time slowdown (throughput 0.97087) would lie in the alternative, and the planted 3% level would measure power, not size. `m_kill = −log 0.97` is ROADMAP's literal kill margin. The planted 3% level sits at the `m_NI` boundary.
- **Bet variable** `g = (m_NI − x)/(c − m_NI)`; needs `c > m_NI` (guaranteed by `c ≥ 2 m_NI`), giving `g ≥ −1`. **Reject (declare non-inferiority) when `K_n ≥ max(20, 1/α_i)`.**
- **Planted-regression calibration** (ROADMAP §3.5), made precise:
  - **Mechanism.** The injected slowdown is **proportional extra work of the same kind**: arm B runs `K′ = ⌈e^{μ*} · K⌉` matvec repetitions where A runs K. A fixed-cycle busy-loop "spin" is rejected (TOMBSTONES §6, `fixed_cycle_spin_planted_regression`): it is core-bound while the L2-resident matvec is not, so its realised ratio moves with boost and thermal state. Extra repetitions keep the ratio invariant to clock state up to the fixed overhead inside the timed region.
  - **Level on the estimand, not on the raw ratio.** The calibration needs the NI null to be *true for the gate's estimand* `E[x]`. Symmetric clipping pulls `E[x]` below `E[d]` when `E[d] > 0` (revision 1's own table: the literal scorer at a planted ×1.03, σ_d 2%, had mean x 0.02898 < m_NI 0.02956 [S, table 2a]). So μ* is the true mean log-ratio at which `E[clip(d)] = log(1 + L)`, plus an overshoot of **0.25%** [target]: the clip bias alone is +0.060% (3%, σ_d 2%), +0.017% (3%, σ_d 4%), +0.184% (4%, σ_d 2%) and +0.033% (4%, σ_d 4%) in time [D, table 3g]. The calibration therefore runs at most 0.25% inside the null at the 3% level — stated so the leniency is visible.
  - **Separate long run (ROADMAP's "a separate long run confirms").** Before the sessions, k_conf = 256 blocks per level [G; SE = σ̂/16 = 0.125% at σ̂ 2%, 0.25% at 4% [D]]: accepted iff the realised mean x lies within ±2.576·SE of the construction target; otherwise K′ is corrected by the measured shortfall and the run repeated (each attempt recorded).
  - **Premise check (pooled).** After the sessions, the one-sided 99% lower confidence bound of mean x over all ≥ 100 planted sessions (≈ 1,200 blocks at σ_d 2%, SE ≈ 0.06% [D]) must be ≥ log(1 + L). If it is not, the calibration is **not a pass** (amber: re-run on fresh sessions with K′ raised); it can never rescue a failed count.
  - **Gate:** ≤ 2 of ≥ 100 sessions per level reach 20 within N [target]. Simulated: ≤ 0.70% at every drafted variant (max 0.0070: σ_d 4%, 0.5% outlier runs, literal scorer, ×1.03, aGRAPA) [S, table 2a] and ≤ 1.0% for R across outlier rates 0–10% (max 0.0100: σ_d 4%, 2% outlier runs) [S, table 3a].
- **Blocks and horizon.** `n = max(6, 12·σ̂_U²/δ²)` (§5.4); sessions run to the amber limit `N = 2·n` ([ROADMAP §1 rule 4](../../docs/ROADMAP.md)).

### 8.4 Time-to-pass at true parity and the kill null
- **Time-to-pass** ([06 §6.6](../../docs/architecture/06-forge.md), ROADMAP §3.5): the A/A sessions also run the NI e-process; at a true ratio of 1.00 it *should* reach 20. Times are **right-censored at the session horizon**; with only administrative censoring the Kaplan–Meier estimate reduces to the empirical CDF, and a quantile beyond the horizon is published as "> H" together with the share within the horizon. Simulated (R scorer, aGRAPA, no outliers): median 9, p90 11, share within N 0.947 at σ_d 2% (N = 12); median 23, p90 36, share 0.968 at σ_d 4% (N = 44) [S, table 2c]. Across the four σ_d-2% variants of table 2c the share within N spans 0.882–0.960 and the p90 11–13, so **at σ_d 2% the p90 sits at or beyond N** and will often be published as "> 12".
- **Outlier-rate sensitivity.** The share within N at true parity falls as environmental outliers rise: at σ_d 2%, 0.959 / 0.886 / 0.794 / 0.685 / 0.311 / 0.089 at outlier-run rates 0 / 0.5% / 1% / 2% / 5% / 10%; at σ_d 4%, 0.976 / 0.949 / 0.946 / 0.915 / 0.803 / 0.603 [S, table 3a]. The per-run outlier rate is therefore a secondary metric measured in the pilot, and owner question 6 asks for a signed revision of N, the clip rule and the throughput figures before M4 if it puts P(NI within N at parity) below 0.8.
- **Kill null** (ROADMAP §1 rule 4: a kill needs a confirmed regression, UCB on the ratio below 0.97): `H0: E[y] ≤ m_kill`, `m_kill = −log 0.97`, one-sided *lower*, with `g = (y − m_kill)/(c_kill + m_kill) ≥ −1`, on the **Rk** statistic y.
  - **Revision 1 was unreachable at low σ_d.** With c = 0.06 and θ = 0.5 the per-block factor is at most 1.163, so 20 needs ≥ 20 blocks and the largest wealth within N = 12 is 6.1 [D] — every regression at σ_d 2% ended amber (table 2d: 0.0000 at ×1.10).
  - **Revised constants [target]:** `c_kill = max(3σ̂_d, m_kill + 3σ̂_d)`, θ_kill = 0.8 (valid: any predictable λ ∈ [0, 1] keeps 1 + λg ≥ 0), outlier blocks scored −c_kill (so environmental noise can never create a kill), and **the kill e-process continues into the amber second N-session when the build-closure hash is unchanged** (one e-process across two sessions with fresh randomisation; §8.6). Largest factor at σ_d 2%: 1.397 (≥ 9 blocks to 20) [D].
  - **Simulated [S, table 3c]:** no false kills at parity for outlier rates 0–10%, and ≤ 0.4% at the kill boundary (true ratio 1/0.97, 2% outliers, σ_d 4%, within 2N). Power, σ_d 2%: ×1.10 → 0.048 within one N-session, 0.992 within 2N; ×1.06 → 0.000 / 0.664. σ_d 4%: ×1.06 → 0.888 within N; ×1.10 → 1.000. **So at σ_d 2% a kill needs both N-sessions** (owner question 5).
  - Revision 1's statement "power at a true 10% regression is 1.0" held at σ_d 4% only; it is withdrawn.

### 8.5 The betting strategy
The reference bettor is **aGRAPA** (`λ = min(θ, max(0, μ̂/(σ̂² + μ̂²)))` from the running mean and variance of g, with one prior pseudo-observation), with **ONS** and **mixture-of-fixed-λ** bettors as reported alternatives; all three are valid. aGRAPA reaches 20 fastest in [stats/](stats/) [S, tables 2c, 2e]. **Only aGRAPA is pre-registered for gates.** Its state, priors, variance floor (1e-12) and update order are pinned in `PREREG` (prereg §7): priors x0 = −0.02 (superiority), 0 (NI), m_kill + 0.02 (kill), each with sd0 = clip/3.

### 8.6 α-budget accounting, the amber session and the differential check
- α_i is fixed **on entry to a confirmatory test**, whatever the outcome ([06 §6.5](../../docs/architecture/06-forge.md)). Threshold `max(20, 1/α_i)`, floor e ≥ 20 (DR-018). Screening spends nothing.
- **Voided sessions:** α_i stays charged when a session voids; a re-run is a **new attempt with a new α_i** (§5.3). This closes void-selective re-running (a11b).
- **The amber second N-session (ROADMAP §1 rule 4), defined.** For superiority and non-inferiority the second session is a **new test**: fresh wealth and a new α_i charge (restarting at the same α_i would double the error bound). This keeps the longest single superiority/NI test at N, which the calibrations cover. For the **kill** e-process the second session **continues** the first iff the build-closure hash is unchanged (one e-process, threshold 20, so the false-kill bound stays 1/20); if the binary changed, the kill e-process restarts.
- **Two tiers** ([06 §6.5](../../docs/architecture/06-forge.md), [03 §7.2](../../docs/architecture/03-trust.md)): union-bound α budget for defaults and F1-A; e-LOND online FDR ≤ q for grant-promoted opt-in profiles. **In X4 nothing is promoted**, so no α is spent; the ledger records a zero-spend baseline, and the planted a11/a11b/a30 hacks run against it with a test budget. Budget sizes and q/γ are Owner decisions (D0-7, D0-10).
- **Differential check, bit for bit.** The Rust e-process and the Python reference must produce **bit-identical** wealth paths for the golden block sequence `x4_calibration.py --golden` prints (every `K_i` as a hex float). Rules: IEEE-754 binary64, round-to-nearest-even, operations in the order written in `PREREG`, no FMA contraction; the margins are **pinned hex constants**, not computed with a platform `log` (this laptop's `math.log(1.03)` is 8 ulps from RN(ln 1.03), because it takes the log of fl(1.03) [M, CPython 3.12.10, 2026-10-16]); a crossing is the first block with `K_i ≥ 20.0` in that float64 product. "Within floating-point tolerance" (revision 1) left crossings near 20 undecided and is withdrawn.

### 8.7 Tail check (mandatory in 06 §6.2; specified here for the first time)
[06 §6.2](../../docs/architecture/06-forge.md) makes a slow-tail check mandatory because the clipped estimand caps each outlier block's penalty at c: a candidate whose runs are 30% slow 15% of the time has a true mean log-ratio of 0.039 (> m_NI) yet a clipped `E[x]` well inside the NI alternative, and revision 1 credited it within N in ≈ 11–13% of sessions at σ_d 2% [S, table 3d; reviewer 2's probe found 11.6%].

**Rule [target].** Deny NI or superiority credit iff `P(Bin(n_B, p0) ≥ k_B) ≤ 0.05`, where k_B counts B's slow-direction outlier runs (R rule; a run stopped at the time cap counts) and n_B its runs, **pooled over the candidate's screening session(s) and the confirmatory session on that niche**, evaluated once n_B ≥ N (the session continues past a crossing until then); p0 is the one-sided 95% Clopper–Pearson upper bound of the pilot's A/A slow-outlier rate per run (§5.4). The check only adds rejections, so it spends no α.

**Why this form, and what remains [S, table 3d].** Evaluated at the crossing on the confirmatory session alone (06's literal reading) the check barely bites, because the sessions that cross are the ones that happened to have few stalls: credit falls only from 0.130 to 0.110 (15% of runs 30% slow, σ_d 2%). Pooling with screening and waiting for N runs gives 0.038; the one-sided level of **5%** (stricter than 06's 1% [target], proposed under owner question 4) gives **0.017**; for 10% of runs 50% slow, 0.284 → 0.065. At σ_d 4% the same cases end at 0.001 and 0.014. The cost at true parity is small: credited share 0.954 → 0.951 (σ_d 2%, no outliers) [S]. **Residual:** a rare-stall candidate still gets NI credit in ≈ 2–7% of attempts at σ_d 2% — a known weakness of the clipped estimand that the M4 Adversary must probe (a34).

---

## 9. Output schema: `Quantity<Unit, Origin>`

Every emitted number is a `Quantity<Unit, Origin>` with `Origin ∈ {Measured{hw,…}, Simulated{model}, Estimated, Assumed}` ([01 §4.4](../../docs/architecture/01-language.md), [ARCHITECTURE §5.2](../../docs/ARCHITECTURE.md)). An unlabelled performance number does not format; unit errors (Hearth's `/tok` vs `*tok` class) are type errors [RV: D2-C]. The signed measurement fact mirrors [06 §6.1](../../docs/architecture/06-forge.md):

```text
measurement m:<hash> {                                   // ledger fact, data not source
    subject:  A = hearth-c-ref@<tag> h:<...>   B = <candidate|hearth-c-ref@<tag>+extra_work(K'/K)|A'> h:<...>
    slot:     <none for X4 calibration | store_evict | q4_matvec ...>
    niche:    { hw: mp:9950x/<profile-hash>, model: qwen3_30b_a3b, cache_gib: 2, run_type: microbench|e2e_decode }
    design:   randomised ABBA/BAAB blocks, n=<..>, N=<..>, sentinels at <positions>, schedule seed <..>, held-out traces sealed h:<...>
    clip:     c = <..>, c_kill = <..>, c_run = <..>  (rules: prereg §7; sigma_hat_d = <..> : Quantity<Ratio, Measured{pilot}>)
    effect:   gate scorer R: mean x <..>; S: <..>; 06 literal: <..> : Quantity<LogRatio, Measured{mp:9950x/<hash>}>
    report:   unclipped mean log-ratio <..>   outlier runs: slow A <..> B <..> fast A <..> B <..>   carry-over co_BA-co_AB <..>
    tail:     k_B <..> of n_B <..> (pooled with screening h:<..>), p0 <..>, P = <..>: pass|deny
    e_value:  { null: superiority, scorer: R, e: <..>, bettor: agrapa, alpha_charged: 0 (X4 calibration) }
    e_value:  { null: non_inferiority, margin: m_ni 0x1.e44a9a3bed663p-6, scorer: R, e: <..>, alpha_charged: 0 }
    e_value:  { null: kill, margin: m_kill 0x1.f30b2d0091d82p-6, scorer: Rk, e: <..>, continues: <session h:|none> }
    time_to_20: { superiority: <blocks|->, non_inferiority: <blocks|->, censored_at: <H> }
    checks:   { profile_hash: match, stationarity: {S1..S4}: pass, output_hash (orchestrator) == golden|incumbent on every run,
                harness_hash == orchestrator_hash, bracket |dh-do| <= tau_clock, post_STOP_cpu <= kappa_post,
                thread_census: pass, post_t1_cpu: pass, mxcsr_all_threads: default, affinity_priority: job values,
                bytes == replay (if timing_blind), poison_overwritten: true, start_state: pass }
    voided:   <k> runs/blocks, kind <hygiene|statistical>, reason <..>, wealth_at_void <..>
    origin_proof: fingerprint h:<...>, env_block h:<...>, toolchain h:<...>, evaluator h:<...>, scratch_bytes_written <..>
}
```

Origins never silently mix: a `Measured` and a `Simulated` quantity combine only through an explicit conversion that names the weaker origin ([01 §4.4](../../docs/architecture/01-language.md)). X4 emits `Measured{fingerprint}` for the engine runs and `Simulated{hearth.sim}` for F1-sim ([F1-SIM.md](F1-SIM.md)); the two never add.

---

## 10. Throughput, quiet hours and the D-22 trigger

- **σ_d per run type and niche is the M0 deliverable** ([06 §6.6](../../docs/architecture/06-forge.md), open question 1); no later campaign starts without it. X4 produces it from the pilot and the A/A sessions run to their horizon (never from sessions stopped at an NI pass, which would bias it — §10 of the prereg).
- **Throughput** is published as candidates per quiet hour at MDE 5% and 2% (ROADMAP §3.5), from the measured σ_d and the time-to-20 of §8.4.
- **Quiet-hour arithmetic** [D from G inputs] is in [stats/](stats/) §4 (10 s micro, 120 s e2e, cool-down 1.5, 120 s setup per session). **X4 alone exceeds ROADMAP §10's M0 line at both σ_d ends.** ROADMAP's column is "σ_d = 2% / 4%", so its "≈ 60–215" pairs 60 h with σ_d 2% and 215 h with σ_d 4%. The ROADMAP-comparable part of X4's plan (A/A, planted, end-to-end A/A, plus X3's plan figure) is **111.2 h at σ_d 2% and 368.8 h at 4%** (+85% and +72%); with the pilot, the separate long runs, the A/A′ arm and the positive control the totals are **≈ 122–135 h and ≈ 325–403 h** (end-to-end A/A stopped at the NI pass, or run to N) [D, stats/ table 4]. A ROADMAP-style reconstruction (A/A at n, planted at N, end-to-end at n, no setup, plus X3) gives 60.9 h and 223.4 h [D], matching COST.md §1.4's 60.3 / 221.0 h [D there] — so the likely cause is that §10 used n blocks per session where §3.5 requires the planted sessions (and X4's A/A and end-to-end sessions) to run to N = 2n [inference]. X4 may not edit §10; this is owner question 1.
- **D-22 (second box) trigger** ([06 §6.9](../../docs/architecture/06-forge.md), ROADMAP §9): the service records the void rate, the confirmatory-queue wait and the measured parity-gate hours; any one over its bound, or a failed calibration, or a quiet-window conflict with Pierce's use, fires D-22. With planned hours above ROADMAP's line, the "planned hours exceed the available windows" disjunct is the one most at risk.

---

## 11. What X4 verifies about this service (gate inputs)

1. **Every planted timing hack is caught at its declared stage** (IF-5): the clock-owner, bracket, join, census, poison, MXCSR, affinity, env-block and output-hash rules each have a planted hack that must fail ([HACK-SUITE.md](HACK-SUITE.md) batch (a), with the X4 detector table in §4.1 there).
2. **A/A calibration passes** (ROADMAP §3.5): ≤ 2 of ≥ 100 microbenchmark A/A sessions reach superiority e ≥ 20, under R and under S; the pooled mean test and the void-rate bound do not turn it amber.
3. **Planted-regression calibration passes:** the NI e-process reaches 20 in ≤ 2 of ≥ 100 sessions at each of 3% and 4%, with the premise check met; the time-to-pass at true parity is published (censored).
4. **The stationarity positive control fires** (≥ 9 of 10).
5. **The Rust e-process reproduces the golden wealth path bit for bit** (§8.6).

A failed A/A calibration bars every superiority gate; a failed planted-regression calibration bars every parity gate, until the cause is fixed and the calibration passes again on fresh sessions (ROADMAP §3.5 kill, D0-8, D-22).
