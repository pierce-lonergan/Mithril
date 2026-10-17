# X4 measurement service v0 + sandbox prototype — implementation notes

**Track:** x4-integrity (x4svc). **Status:** v0 implemented and self-tested on the desktop; **no gate
data collected**. **Date:** 2026-10-16. Author: X4 track (Claude, same-family independent-context).
Evidence tags as in [MEASUREMENT-SERVICE.md](MEASUREMENT-SERVICE.md): **[M]** measured here, **[D]**
derived, **[G]** judgment, **[target]** a pre-registered threshold, **[inference]**.

This builds the designs in [MEASUREMENT-SERVICE.md](MEASUREMENT-SERVICE.md), [SANDBOX.md](SANDBOX.md),
[DESIGN.md](DESIGN.md) and the catch targets in [HACK-SUITE.md](HACK-SUITE.md). It changes **no**
system settings and runs **none** of the sealed catalogue (a) hacks, no A/A or planted-regression
calibration, and no Hearth benchmark. It exercises the machinery with the track's own `dev_*` probes
on synthetic workloads only (a busy loop, a sleep, a deliberately leaking thread), recorded as
**non-gate**.

## Language split (as the design specifies, section 2)

- **C11 harness** (`service/harness/`, MSVC `cl` 19.44): owns the precise clock (`x4h_now_ns`, Hearth's
  `hx_now_ns` QPC formula at b5d3f14), wraps thread creation, joins threads/I-O, takes the post-`t1`
  thread census + MXCSR read, poisons output, hashes, and reports typed fields over a pipe. It is the
  *precise* record, not the trusted one (it shares the workload's address space).
- **Rust orchestrator** (`service/orchestrator/`, `cargo`/`rustc` 1.91.1 MSVC): the supervisor. Holds
  the Job Object limits, times START/STOP on its own QPC, accounts job CPU, owns and rehashes the
  output section, runs the e-processes, emits `Quantity<Unit, Origin>`, and is the **trusted**
  out-of-process integrity bracket (section 3 step 8a). No third-party crates (F0 hygiene, 03 §14).
- **Python** only offline: the calibration reference `stats/x4_calibration.py` (unchanged) and the dev
  driver `service/tools/x4_devcheck.py`.

## What is built and verified

### Measurement service — C harness (`service/harness/`, `service/proto/x4proto.h`)
Runtime-owned clock bracket with START/t0 … join-all-threads-and-I/O … t1/STOP; post-stop thread
census (`CreateToolhelp32Snapshot` + per-thread `GetThreadContext` MXCSR, affinity, priority, cycle
counts); poisoned fresh allocations (`0xA5` + per-run salt, guard pages, residual + slack-overflow
counts); output rehash (BCrypt SHA-256); output view frozen `PAGE_READONLY` at `t1` under SEH.
Verified [M, desktop MSVC, 2026-10-16] with `x4_devcheck.py` — **11/11 dev probes** produce the
expected signal:

| dev probe | harness signal (detector) | result |
|---|---|---|
| dev_write / dev_busy / dev_sleep / dev_io / dev_parked | clean report, t1>t0, I/O joined, parked worker allowed | ok |
| dev_leak_registered | `REGISTERED_UNPARKED>=1` (a3 unjoined work) | ok |
| dev_raw_thread | `NEW_UNREGISTERED>=1` (a3b thread created after t0 outside the wrapper) | ok |
| dev_mxcsr_worker | `MXCSR_BAD_THREADS>=1` (a9 FTZ/DAZ on a worker) | ok |
| dev_partial_output | `POISON_RESIDUAL_WORDS>0` (a4 unwritten output) | ok |
| dev_overflow | `SLACK_MODIFIED_BYTES>0` (write past the extent) | ok |
| dev_priority | `PRIORITY_BAD>=1` (a31) standalone; neutralized by the job limit under the orchestrator | ok |

### Measurement service — Rust orchestrator (`service/orchestrator/`)
- **Out-of-process integrity bracket** (`proto.rs`, `sandbox.rs`): QPC wall bracket Δ_o vs harness Δ_h
  with `τ_clock = max(1 ms, 2·pilot_max|Δ_h−Δ_o|)` capped at 0.1% of Δ_o; job CPU charged after STOP
  vs `κ_post`; orchestrator's own SHA-256 of the output section vs harness hash vs golden/incumbent.
  `decide_run` returns Accept or a named IntegrityFail; **a clean run Accepts, every injected fault is
  an IntegrityFail**.
- **e-processes exactly as specified** (`eprocess.rs`): aGRAPA bettor, superiority/non-inferiority/kill
  `EProcess`, the R/S/Rk/06 scorers with the predictable running-median reference, pinned **hex**
  margins (`m_NI=0x1.e44a9a3bed663p-6`, `m_kill=0x1.f30b2d0091d82p-6`), clips, θ=0.5/0.8. Differential
  test `tests/golden_diff.rs` reproduces `x4_calibration.py --golden` (24 blocks, three wealth paths)
  **bit for bit** [M].
- **Stationarity / trend** (`stats.rs`): S1 sentinel mean, S2 χ² variance envelope, S3 Mann–Kendall
  with the lag-1 Hamed–Rao factor, S4 median envelope; the pooled mean z-test; the tail check; exact
  binomial OC (matches ROADMAP's 0.9206/0.1183/0.0113 [D]); Clopper–Pearson; discard-asymmetry.
- **ABAB interleaving behind a load gate** (`scheduler.rs`): randomised ABBA/BAAB from a pinned seed
  (SplitMix64), the load gate (profile-hash/quiet-window/CPU-load/background/NVMe), the three failure
  kinds, `n`/`N` block counts, the three-discard hygiene void. Void decisions take only sensor/time
  inputs — the module never imports the e-process (blindness, section 5.3).
- **`Quantity<Unit, Origin>`** (`quantity.rs`): const-generic `Unit` so `/tok` vs `*tok` is a compile
  error; `Origin ∈ {Measured{hw}, Simulated{model}, Estimated, Assumed}`; origins combine only through
  an explicit weaker-origin conversion; no `Display` that would print an unlabelled number.
- **Profile verifier** (`profile.rs`, `profile_win.rs`): read-only (`powercfg /getactivescheme`,
  `/query SUB_PROCESSOR`, `(Get-MpPreference).ExclusionPath`), **refuses to run when the profile is not
  met and prints the exact commands Pierce must run** — never runs them. Live on the desktop it
  correctly reported NOT MET on the Balanced plan and printed the §7.1/7.2/7.3 fix commands [M].

### Sandbox prototype (`sandbox/`)
- **Job Object with supervisor-held limits** (`sandbox.rs`): active-process cap 1, process-memory
  limit, kill-on-close, die-on-unhandled-exception, priority class, optional affinity mask; the child
  is created **suspended**, assigned to the job **before it runs code**, with no `CREATE_BREAKAWAY`.
  The child holds no job handle. Verified inside the real sandbox: `in_job=true`,
  `child_creation_blocked=true` [M].
- **Startup self-test** (`sandbox/probes/`, SEH-guarded so one faulting probe cannot sink the test):
  token (AppContainer / elevated / admin-enabled / MithrilMeasure); job (in-job, cannot create a child,
  cannot break away, cannot clear limits, priority/affinity self-elevation); **positive-control
  network** (orchestrator opens a loopback listener; inside must be *denied*, outside must *succeed*);
  brokers (named pipe, WMI, Task Scheduler, out-of-proc COM); sealed data by path + 8.3 + `::$DATA` +
  `\\?\` + hard link + junction; scratch empty/writable; direct I/O; large pages; MXCSR. The
  orchestrator runs the same probes outside as the control and applies the **refusal table**
  (`selftest.rs`). Verified end-to-end [M]: in degraded mode (no AppContainer / MithrilMeasure /
  firewall, none of which we may set) → **hearth-c-ref = Run, untrusted = Refuse**, with Pierce's
  one-time commands printed.
- **Read-only goldens**: the sealed store is unreachable-by-ACL in the design; the alternate-name
  probes (8.3/case/`::$DATA`/`\\?\`/hard-link/junction) are implemented and run inside the sandbox.

## Build and test (desktop, MSVC, ≤ 2 threads, `CUDA_VISIBLE_DEVICES=-1`)
Sources live in the repo; binaries build on the desktop under `D:\mithril\x4\`:
- C: `cl /O2 /W4 /std:c11 /MT` → `D:\mithril\x4\bin\x4harness.exe`, `x4sb_probe.exe` (clean at /W4) [M].
- Rust: `cargo test -j2 --release` → **39 unit + 2 golden-differential tests pass** [M];
  `cargo build -j2 --release` → `D:\mithril\x4\cargo-target\release\x4svc.exe` (no warnings) [M].
- `CARGO_HOME`/`CARGO_TARGET_DIR` point at `D:\` so nothing lands on `C:`. WSL was not started.

Demonstrations run [M, desktop, 2026-10-16]:
- `x4svc run --harness … --workload dev_write` → Accept; `dev_leak_registered` → IntegrityFail(a3);
  `dev_mxcsr_worker` → IntegrityFail(a9); `dev_partial_output` → IntegrityFail(a4); `dev_t0_poke` →
  IntegrityFail(a5 clock bracket, |Δ_h−Δ_o| ≈ 497 ms); `--golden-zero` → IntegrityFail(hash mismatch).
- `x4svc verify-profile` → NOT MET, prints Pierce's commands, exit 1.
- `x4svc selftest …` → Job Object core verified inside; refusal table as above.

## What needs Pierce's one-time commands (no agent runs these; see SANDBOX.md / MEASUREMENT-SERVICE.md §7)
All require elevation and/or a system/security change, so they are the Owner's (06 §6.7, DECISIONS.md):
1. The quiet-machine profile: `powercfg /duplicatescheme … MITHRIL-MEASURE`, core-parking 100/100,
   Defender exclusion of the data dir (§7.1–7.3). The service verifies and refuses without them.
2. `New-LocalUser MithrilMeasure` (SANDBOX §3.3) — the separate low-privilege principal.
3. The sealed-store ACLs (`icacls … /inheritance:r`, no ACE for MithrilMeasure/ALL APPLICATION
   PACKAGES) (SANDBOX §2.1).
4. The outbound firewall rule for MithrilMeasure (SANDBOX §3.2).
The AppContainer/LPAC launch itself needs **no** system change (it is a runtime
`CreateAppContainerProfile` + `STARTUPINFOEX`); it is the next build step and is **not yet wired** —
until it is, the refusal table keeps untrusted workloads out (fails closed).

## Known gaps / honest limitations (carried into the prereg)
- **AppContainer/LPAC launch not yet implemented**; LPAC token-attribute detection is stubbed
  (`attempted=0`, not determined) — AppContainer (`TokenIsAppContainer`) is the bit the refusal table
  reads, and it works. Large-page + direct-I/O inside an AppContainer remain **unverified on this box**.
- **Pilot-derived constants are provisional**: `τ_clock`, `κ_post`, `ε_spin`, `ε_idle`, the clips and
  `N` are wired as inputs but carry placeholder values until the σ-pilot fills them in (prereg §7). The
  dev demonstrations used provisional budgets; they are not gate numbers.
- **a31 priority** is *neutralized* by the Job Object priority-class limit under the orchestrator
  (Accept, nothing to flag); the census detector itself is proven standalone (`dev_priority`,
  `PRIORITY_BAD=1` outside a job). a31 **affinity** is only asserted when a job affinity mask is pinned
  (`--affinity`), by design (threads must match A's mask).
- The sandbox self-test probes are **samples, not proofs** (SANDBOX §6); the real adversary is M4.
- Every review so far is **same-family, independent-context**; no gate verdict is computed here.
- **F0 line budget** (03 §14, ≤ 1,500 line-reviewed lines [target]): v0 is ~4,170 lines total
  [M, `wc -l`] — core measurement path ~3,034 (incl. inline `#[cfg(test)]` modules, the Win32 FFI
  declarations in `sandbox.rs`, and the special functions in `stats.rs`), sandbox self-test ~774,
  dev/tests/main ~706. Counted as line-reviewed F0 logic (excluding test modules, FFI boilerplate and
  the `dev_*`/tools code, which are not on the trusted measured path), the core is smaller, but a
  disciplined split and trim to bring the reviewed core under 1,500 is **future work before freeze**,
  and is flagged here rather than hidden.

## Files (this track only)
- `service/proto/x4proto.h` — the C↔Rust wire protocol.
- `service/harness/{x4h.h,x4h.c,dev_workloads.c}` — the C harness and the non-gate `dev_*` workloads.
- `service/orchestrator/` — the Rust crate (`quantity`, `eprocess`, `stats`, `scheduler`, `proto`,
  `profile`, `selftest`; `sandbox`, `profile_win` on Windows; `tests/golden_diff.rs` +
  `tests/golden_fixture.rs`; `src/main.rs` CLI).
- `service/tools/x4_devcheck.py` — the dev self-test driver (non-gate).
- `sandbox/probes/{x4sb_probes.h,x4sb_probes.c,x4sb_probe_main.c}` — the self-test probes and the
  outside positive-control exe.
