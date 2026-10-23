# X4 noise pilot: the pre-night checklist (for Pierce)

**Track:** x4pilot (X4 pilot track, Claude). **Date:** 2026-10-23. **Record:**
[X4-noise-pilot](../../../docs/m0/prereg/X4-noise-pilot.md) (DRAFT; this file carries its section 11
commands, made exact against the desktop as read on 2026-10-23). Tags: **[M]** measured (read on the
desktop, read-only), **[G]** judgment, **[inference]**.

**You run these yourself.** No agent has run any of them, and no agent changes a system or security
setting. The measurement service only reads each setting. A pilot night refuses to start (night
refusal) while a required item fails, and voids or discards later on what its sensors see. Each item
is your call. Not applying an advisory item means more discarded blocks, and the void rate feeds D-22.

What failed on 2026-10-23 is listed in [VERIFY-2026-10-23-rev4.txt](VERIFY-2026-10-23-rev4.txt), the
raw output of the read-only report [verify_report.ps1](verify_report.ps1) on the revision-4 build, and
summarised in the last section (with the revision-5 rows).

**Revision 4 (after the 2026-10-23 review):** A2 and A3 say what each Windows Update and maintenance
setting does and does not prevent; A4 no longer suggests excluding the dev build folder; the task is
registered at normal priority; a once-only readability check from your own (non-elevated) session; B
adds "no SSH or agent access during the window".

**Revision 5 (review round 5, 2026-10-23): the order changed.** Everything that reads the machine for a
pin now runs **where the driver will run**, your non-elevated console session: an elevated SSH session
reads some fingerprint fields differently, and every night would then refuse (under a restricted token,
every CIM field of the fingerprint read `unavailable` [M]). So: your decisions (section 0), your
settings (A1–A5), then the lead engineer's copies and draft configuration (L1), then you make the pins,
run the readability check and, inside a window, one attended end-to-end run (A6–A9), then the lead
engineer's pre-night amendment (L2), then the nights (B). The scheduled task is called the **pilot
launcher** (the desktop job wrapper of OWNER-QUEUE B13 does not exist and the record no longer relies on
it). The driver no longer needs elevation: it reads Defender's and the indexer's CPU through documented
performance counters when it cannot open them [M, restricted token, IMPLEMENTATION.md "Review round 5"].

---

## 0. Decide (chat or sitting 2; recorded in the record's section 13 at signing)

- **C07** (the run-level R scorer and pooled tail check): the X4-calibration record, and so this pilot,
  cannot freeze before it (DELEGATED P23: not delegable).
- **R1-11**: is the pre-START wall ceiling judged in the pilot, or only recorded? (registered: judged)
- **Priority class** of the pilot and of `x3_bench`: NORMAL (registered, recommended) or HIGH.
- **Plan A (W6) or Plan B (W10)** for the weeks of the rate rule (registered: Plan B). It is fixed at
  signing, before any pilot data.
- MITHRIL-MEASURE **active 24/7 or switched nightly** (A1, B3).
- **GEMS image names** not already excluded (or "none beyond the record's list"), and confirm the local
  Qwen3 server runs as `python`/`pythonw` (Hearth's `hearth serve` is a Python program [inference]).
- **C: free space**: 8.5% free [M, 2026-10-23]; accept it or free some (A5).
- **Defender exclusion** of `D:\mithril-data`: set it or not (A4).
- Sign the FROZEN record (tag `prereg-sign-x4-noise-pilot`); ratify C01, C02, C25, D0-7a and D0-10d.

## A. Once, your settings (elevated PowerShell unless marked)

The desktop clock runs on US Eastern time [M]; every time below says which clock it means.

**A1. The measurement power plan** (required: `verify-profile` items 7.1 and 7.2).
```powershell
powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
#   prints "Power Scheme GUID: <NEW-GUID>  (High performance)"; write <NEW-GUID> down
powercfg /changename <NEW-GUID> MITHRIL-MEASURE
powercfg /setacvalueindex <NEW-GUID> SUB_PROCESSOR CPMINCORES 100
powercfg /setacvalueindex <NEW-GUID> SUB_PROCESSOR CPMAXCORES 100
# only if you chose 24/7 (revision 5):
powercfg /setactive <NEW-GUID>
# checks (not elevated is fine): the first two must read 0x00000064, the third 0x00000000 (no sleep on AC)
powercfg /qh <NEW-GUID> SUB_PROCESSOR CPMINCORES | Select-String 'Current AC'
powercfg /qh <NEW-GUID> SUB_PROCESSOR CPMAXCORES | Select-String 'Current AC'
powercfg /qh <NEW-GUID> SUB_SLEEP STANDBYIDLE | Select-String 'Current AC'
```
Facts [M, read-only]: the active plan today is Balanced `381b4222-f694-41f0-9685-ff5bb260df2e`, whose
core-parking values are already 100/100 on AC; standby on AC reads 0 (never) on both Balanced and High
performance, the plan MITHRIL-MEASURE is copied from. A machine that sleeps ends the night. The record
pins a dedicated plan by GUID anyway, so a change to Balanced cannot silently change the profile.

**A2. Windows Update must not restart the machine inside the window** (required in practice: a
restart ends the night). Today's active hours are 06:00 to 00:00 desktop time [M], so restarts are
allowed 00:00 to 06:00 Eastern = 21:00 to 03:00 PT, which overlaps the window. Your choice; the two
options differ:
- Settings > Windows Update > **Pause updates** for the pilot week: no restart and no update download or
  servicing in the window. This is the option that also avoids discarded blocks: Windows Update
  servicing (`TiWorker`, `MoUsoCoreWorker`, ...) above 1% of one core over a block discards it, and
  three discards void the session.
- Settings > Windows Update > Advanced options > Active hours > Manually: **8:00 PM to 2:00 PM**
  (desktop time; the 18-hour maximum, = 17:00 to 11:00 PT, covering 23:00 to 07:00 PT). This blocks
  only the automatic **restart**; downloads and servicing still run in the window and discard blocks.

**A3. Automatic maintenance outside the window.** No `Activation Boundary` is set [M], so Windows uses
its default daily time, 2:00 AM local [inference] = 2:00 AM Eastern = **23:00 PT, the window's start**.
Control Panel > System and Security > Security and Maintenance > Maintenance > Change maintenance
settings: run at, for example, **4:00 PM** (desktop time = 13:00 PT), and untick "Allow scheduled
maintenance to wake up my computer". Read back (not elevated):
```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\Maintenance' | Select-Object 'Activation Boundary'
```
This moves the daily maintenance run only. Idle-triggered tasks (compatibility telemetry, .NET image
generation, defragmentation and the like) are not moved by it: they start when the machine is idle,
exactly as on a pilot night. The pilot discards any block they touch above 1% of one core
(`CompatTelRunner`, `ngen`, `ngentask`, `mscorsvw`, `defrag`, `DismHost`, `cleanmgr`, `wermgr`,
`MpCmdRun`), so they cost discarded blocks, not wrong data.

**A4. Data directory, Defender and the indexer.**
```powershell
# not elevated (required: the pilot's data, scratch, pins and pinned binaries live here):
New-Item -ItemType Directory -Force D:\mithril-data\x4\pilot, D:\mithril-data\x4\scratch, D:\mithril-data\x4\pins, D:\mithril-data\x4\bin
# elevated, advisory, a security trade-off (your call; section 0). It also covers the pinned binaries
# in D:\mithril-data\x4\bin (in a daytime dry run MsMpEng used more than one full core over a block [M]):
Add-MpPreference -ExclusionPath 'D:\mithril-data'
```
Facts [M]: `C:\Users` is already excluded from Defender real-time scanning, so the model file
(`C:\Users\pierce lonergan\hearth-data\...`) is too; `D:\mithril-data` does not exist yet. The service
discards a block when Defender, the indexer or Windows Update servicing uses more than 1% of one core
over it, whether or not the exclusion is set. Indexer: Control Panel > Indexing Options > Modify, untick
`D:\mithril-data` if D: is indexed.

**A5. Free space on C:** (advisory). C: (the 990 PRO that holds the model) is **91.5% full, 158.5 GB
free** [M]. MEASUREMENT section 7.4 asks for at least about 20% free so the SLC cache behaves [G]. The
end-to-end decode only reads the model, so this affects read timing at most; freeing space, or accepting
it, is your call (section 0).

## L1. The lead engineer, after A4 (no setting involved)

From a build of the frozen service commit (`build_pilot.bat`, which refuses on any toolchain or Hearth
mismatch): copy `x4svc.exe`, `x4harness_hearth.exe`, `x4sb_probe.exe` (and `x4plant.exe`, unused at night)
into `D:\mithril-data\x4\bin`; make the mechanical values by the record's rules (K and o_rt from 3
`dev-run`s of the pinned harness on LP 2; t_run,plan(e2e), its o_rt and the end-to-end golden from 3
daytime runs at N = 2,048 on 8 LPs; the seed; the binary hashes); write the filled
`D:\mithril-data\x4\pilot.cfg` from `pilot.cfg.template` (with your section 0 names in
`excluded_images_at_signing`), and give you its canonical hash: `x4svc config-hash --config
D:\mithril-data\x4\pilot.cfg`.

## A6–A9. Once, from your own console session, after L1 (not elevated)

**A6. How the driver is started** (required: the input sensor sees only the session the driver runs
in; over SSH it runs in session 0 and a PILOT night refuses [M]). Start it in your console session,
either by hand at about 22:55 PT (B5), or with the **pilot launcher**, a scheduled task you create (a
standing rule, so only you create it):
```powershell
$a = New-ScheduledTaskAction -Execute 'D:\mithril-data\x4\bin\x4svc.exe' -Argument 'pilot-night --config D:\mithril-data\x4\pilot.cfg --pilot --config-sha256 <CANONICAL-HASH from L2>' -WorkingDirectory 'D:\mithril-data\x4'
$t = New-ScheduledTaskTrigger -Daily -At 1:55AM          # desktop (Eastern) time = 22:55 PT
# priority 4 = normal. The default, 7, runs the task below normal [M, reviewer], which the driver refuses
$s = New-ScheduledTaskSettingsSet -Priority 4 -ExecutionTimeLimit (New-TimeSpan -Hours 9) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'Mithril-X4-pilot-launcher' -Action $a -Trigger $t -Settings $s   # no -User: runs as you, only while you are logged on, in your session [inference]
```
Register it after L2 (it carries the canonical hash). Not tested by any agent: check once that the
night's `voids.log` shows `in console session Some(true)` and `driver at NORMAL_PRIORITY_CLASS ... ok`.
Disable it after the pilot week (`Disable-ScheduledTask -TaskName 'Mithril-X4-pilot-launcher'`).

**A7. The two pins files** (required; revision 5: you make them, in the launch context, after A1, with
the plan the nights will use active: for the nightly option, run `powercfg /setactive <NEW-GUID>` first
and switch back afterwards). Every line is kept on purpose: the `# key=value` lines let the driver name
a field that differs. ASCII on purpose: Windows PowerShell's `>` writes UTF-16, which the strict pins
parser rejects.
```powershell
D:\mithril-data\x4\bin\x4svc.exe fingerprint --scratch D:\mithril-data\x4\scratch --affinity 0x4 --env HEARTH_ISA=avx512 --env HEARTH_LOG=0 --env CUDA_VISIBLE_DEVICES=-1 |
  Set-Content -Encoding ascii D:\mithril-data\x4\pins\mb-q4-avx512.txt
D:\mithril-data\x4\bin\x4svc.exe fingerprint --scratch D:\mithril-data\x4\scratch --affinity 0xbfffffff `
  --env HEARTH_ISA=avx512 --env HEARTH_LOG=0 --env CUDA_VISIBLE_DEVICES=-1 --env HEARTH_THREADS=16 --env HEARTH_IO_THREADS=8 --env HEARTH_CACHE_GB=8 `
  --env "X4_MODEL_PATH=C:\Users\pierce lonergan\hearth-data\qwen3-30b-a3b-q4.hearth" |
  Set-Content -Encoding ascii D:\mithril-data\x4\pins\e2e-decode.txt
```
(the values shown are C01's and C02's answers, R8; the environment block is sorted before hashing, so
the order of the `--env` options does not matter). If you use the pilot launcher, make them once more
through a temporary task with the same settings and compare: the two files must be identical.

**A8. The readability check** (required, once): every `sensor:` line must read `ok`, and the driver
line must say `elevated Some(false)` and `integrity RID Some("0x2000")`.
```powershell
D:\mithril-data\x4\bin\x4svc.exe verify-hygiene --config D:\mithril-data\x4\pilot.cfg --as-pilot > D:\mithril-data\x4\launch-check.txt
```
and, if you use the pilot launcher, once through a temporary task with the same settings:
```powershell
$s = New-ScheduledTaskSettingsSet -Priority 4 -ExecutionTimeLimit (New-TimeSpan -Hours 9) -MultipleInstances IgnoreNew
$c = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c D:\mithril-data\x4\bin\x4svc.exe verify-hygiene --config D:\mithril-data\x4\pilot.cfg --as-pilot > D:\mithril-data\x4\launch-check-task.txt' -WorkingDirectory 'D:\mithril-data\x4'
Register-ScheduledTask -TaskName 'Mithril-X4-launch-check' -Action $c -Settings $s; Start-ScheduledTask -TaskName 'Mithril-X4-launch-check'
# when D:\mithril-data\x4\launch-check-task.txt is written:
Unregister-ScheduledTask -TaskName 'Mithril-X4-launch-check' -Confirm:$false
```
Its "process CPU" line names the images read through the performance counters (Defender, the indexer:
expected from a non-elevated session); none may be listed as unreadable.

**A9. One attended end-to-end run at the pilot placement** (required once, revision 5; inside a
window, 23:00 to 07:00 PT, before you launch the first night; C01 lifts the 8-thread cap only there).
It is not pilot data. Do B1–B2 first, then:
```powershell
D:\mithril-data\x4\bin\x4svc.exe dev-run --config D:\mithril-data\x4\pilot.cfg --run-type e2e-decode > D:\mithril-data\x4\e2e-attended.txt
```
It takes a few minutes (N = 2,048 tokens on 31 LPs). The lead engineer reads it the next day: the
verdict must be `Accept`, the golden the pinned one, every observe margin at most 1, and the peak process
memory under 75% of the 24 GiB limit; otherwise the record needs a design revisit before night 1
(never a raised ceiling).

## L2. The lead engineer: the pre-night amendment

Commits your two pins files, `launch-check*.txt`, `e2e-attended.txt`, the filled `pilot.cfg` and its
canonical hash, the binary hashes and the mechanical values (record section Amendments), and tells you
the canonical hash for the launch command (B5, A6).

## B. Every pilot night, by 22:50 PT

1. Stop GEMS jobs and pause the GPU queue (your R5 answer). Close the launchers and every image on the
   excluded list: on 10-23 these were running [M]: Claude Code / Claude desktop (`claude.exe` x12),
   `python` x16, OneDrive, Overwolf, CurseForge x7, EpicGamesLauncher, and WSL. An excluded process that
   **starts** or **uses any CPU** during a session voids it; one left running idle does not, but idle
   launchers rarely stay at zero CPU.
2. `wsl --shutdown` (WSL was running on 10-23: `vmmemWSL`, four `wsl`, `wslservice` [M]).
3. If you switch the plan nightly: `powercfg /setactive <MITHRIL-MEASURE GUID>`.
4. Optional preview, read-only, not elevated:
   `D:\mithril-data\x4\bin\x4svc.exe verify-hygiene --config D:\mithril-data\x4\pilot.cfg`.
   The driver runs the same items itself at the start (with `selftest`, which must print
   `mode: degraded-job-only`, and `verify-profile --collection --pins` per run type) and refuses the
   night on any failure.
5. Start the driver in your console session at about 22:55 PT (it waits for 23:00 PT, at most one hour),
   or let the pilot launcher do it:
   `D:\mithril-data\x4\bin\x4svc.exe pilot-night --config D:\mithril-data\x4\pilot.cfg --pilot --config-sha256 <CANONICAL-HASH>`.
   It refuses at once if the configuration's canonical hash is not that value. Then leave the machine:
   any input, a new console or RDP session, a GPU job above 5% or the NVMe at 70 C or more voids the
   running session.
6. **No SSH or agent access to the desktop from 23:00 to 07:00 PT** (your D0-7a answer says "no agents
   running then"). A new `sshd`, `sshd-session`, `powershell`, `pwsh` or `cmd` process voids the running
   session, so a laptop agent's `desk.sh`, or your own SSH login, costs a session. Scheduled tasks that
   start a shell in the window do the same; the void log names the process and its parent.

**Morning, after 07:00 PT:** if you switch the plan nightly, `powercfg /setactive
381b4222-f694-41f0-9685-ff5bb260df2e`. The night's records are in `D:\mithril-data\x4\pilot\night-<date>`
(`manifest.txt` holds the hash of every record file). A night cut short by a crash, a restart or a power
loss is closed by the next night's driver; **after the last pilot night only**, if it was cut short, the
lead engineer runs `x4svc pilot-close --config D:\mithril-data\x4\pilot.cfg --config-sha256
<CANONICAL-HASH>` (outside the window, with no other x4svc running), then `x4svc pilot-estimate`.

## C. What fails today (read-only, 2026-10-23)

From [VERIFY-2026-10-23-rev4.txt](VERIFY-2026-10-23-rev4.txt) [M] (15:33 desktop time = 12:33 PT,
`x4svc.exe` `68125f5e…02f9`), with revision 5's rows (IMPLEMENTATION.md "Review round 5"):

| Item | Today | Who fixes it |
|---|---|---|
| 7.1 power plan = the pinned measurement plan | FAIL: Balanced active | you, A1 |
| 7.2 core parking 100/100 | ok (Balanced reads 100/100 through `powercfg /qh`) | re-checked on A1's plan |
| standby on AC (revision 5) | 0 (never) on Balanced and High performance [M] | re-checked on A1's plan |
| collection: pins files and fingerprint | FAIL: no pins file exists | you, A7 (revision 5: not the lead engineer) |
| binary SHA-256 pins (harness, probe, x4svc) | not pinned (the DRAFT has no freeze yet) | lead engineer, L1/L2 |
| configuration canonical hash (revision 5) | not made (no filled configuration) | lead engineer, L1/L2 |
| placement equals the topology rule | ok: mb `0x4`, e2e `0xbfffffff`, orchestrator LP 30 | - |
| input sensor in the console session | FAIL over SSH (session 0) | the launch path, A6 |
| driver priority and memory priority | ok over SSH (NORMAL, 5); the task must be registered with `-Priority 4` | you, A6 |
| readability from a non-elevated session | revision 5: under a restricted token every listed image reads (Defender, the indexer and other unopenable processes through the performance counters) [M]; your own session not yet checked | you, A8 (once) |
| the end-to-end run type at its pilot placement | never run (only N = 8 on at most 3 threads [M]) | you, A9 (once, in a window) |
| Windows Update active hours / pause | FAIL: active hours 06:00-00:00 desktop time (restarts allowed 21:00-03:00 PT); no pause set | you, A2 |
| maintenance outside the window | FAIL: no Activation Boundary (default 2:00 AM Eastern = 23:00 PT) | you, A3 |
| excluded processes idle | advisory: claude x12, python x28, OneDrive, Overwolf, CurseForge x7, EpicGamesLauncher running (WSL: only `wslservice`) | you, nightly B1-B2 |
| `D:\mithril-data` | absent | you, A4 |
| Defender exclusion of the data directory | advisory, not set (`C:\Users` is excluded) | you, A4 |
| C: free space >= ~20% | advisory: 8.5% free (158.1 GB) | you, A5 |
| sandbox self-test | ok: `degraded-job-only` with the job's affinity limit | - |
| sensors | ok: machine load (`GetSystemTimes`) and per-LP load and effective clock (PDH, 32 of 32 LPs at 2 s), disk queue / writes / modified pages, process CPU, WTS sessions, GPU via `nvidia-smi`, NVMe temperature, power-scheme GUID; **no ACPI thermal-zone counter**, so CPU package temperature is unavailable (recorded, not gated) | - |
