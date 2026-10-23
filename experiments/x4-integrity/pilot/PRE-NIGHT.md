# X4 noise pilot: the pre-night checklist (for Pierce)

**Track:** x4pilot (X4 pilot track, Claude). **Date:** 2026-10-23. **Record:**
[X4-noise-pilot](../../../docs/m0/prereg/X4-noise-pilot.md) (DRAFT; this file carries its section 11
commands, made exact against the desktop as read on 2026-10-23). Tags: **[M]** measured (read on the
desktop, read-only), **[G]** judgment, **[inference]**.

**You run these yourself.** No agent has run any of them, and no agent changes a system or security
setting. The measurement service only reads each setting. A pilot night refuses to start (night
refusal) while a required item fails, and voids or discards later on what its sensors see. Each item
is your call. Not applying an advisory item means more discarded blocks, and the void rate feeds D-22.

What fails today is listed in [VERIFY-2026-10-23-rev4.txt](VERIFY-2026-10-23-rev4.txt), the raw
output of the read-only report [verify_report.ps1](verify_report.ps1) on the revision-4 build
(revision 3's is [VERIFY-2026-10-23.txt](VERIFY-2026-10-23.txt)), and summarised in the last section.

**Revision 4 (after the 2026-10-23 review):** A2 and A3 say what each Windows Update and maintenance
setting does and does not prevent; A4 no longer suggests excluding the dev build folder; A6 registers
the task at normal priority and adds a once-only readability check from your own (non-elevated)
session; A7 lists the new mechanical values; B adds "no SSH or agent access during the window".

---

## A. Once, before the first pilot night

Elevated PowerShell on the desktop unless marked otherwise. The desktop clock runs on US Eastern
time [M]; every time below says which clock it means.

**A1. The measurement power plan** (required: `verify-profile` items 7.1 and 7.2).
```powershell
powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
#   prints "Power Scheme GUID: <NEW-GUID>  (High performance)"; write <NEW-GUID> down
powercfg /changename <NEW-GUID> MITHRIL-MEASURE
powercfg /setacvalueindex <NEW-GUID> SUB_PROCESSOR CPMINCORES 100
powercfg /setacvalueindex <NEW-GUID> SUB_PROCESSOR CPMAXCORES 100
# check (not elevated is fine): both lines must read 0x00000064
powercfg /qh <NEW-GUID> SUB_PROCESSOR CPMINCORES | Select-String 'Current AC'
powercfg /qh <NEW-GUID> SUB_PROCESSOR CPMAXCORES | Select-String 'Current AC'
```
Your choice, recorded at signing: keep MITHRIL-MEASURE active 24/7 (it changes GEMS's daytime power
and heat), or switch it on each night (B3) and back in the morning. Facts: the active plan today is
Balanced `381b4222-f694-41f0-9685-ff5bb260df2e`, whose core-parking values are already 100/100 on AC
[M, `powercfg /qh`]; the record pins a dedicated plan by GUID anyway, so a change to Balanced cannot
silently change the measurement profile.

**A2. Windows Update must not restart the machine inside the window** (required in practice: a
restart ends the night). Today's active hours are 06:00 to 00:00 desktop time [M], so restarts are
allowed 00:00 to 06:00 Eastern = 21:00 to 03:00 PT, which overlaps the window. Your choice; the
two options differ (revision 4):
- Settings > Windows Update > **Pause updates** for the pilot week: no restart and no update
  download or servicing in the window. This is the option that also avoids discarded blocks:
  Windows Update servicing (`TiWorker`, `MoUsoCoreWorker`, ...) above 1% of one core over a block
  discards it, and three discards void the session.
- Settings > Windows Update > Advanced options > Active hours > Manually: **8:00 PM to 2:00 PM**
  (desktop time; the 18-hour maximum, = 17:00 to 11:00 PT, covering 23:00 to 07:00 PT). This blocks
  only the automatic **restart**; downloads and servicing still run in the window and discard blocks.

**A3. Automatic maintenance outside the window.** No `Activation Boundary` is set [M], so Windows uses
its default daily time, 2:00 AM local [inference] = 2:00 AM Eastern = **23:00 PT, the window's
start**. Control Panel > System and Security > Security and Maintenance > Maintenance > Change
maintenance settings: run at, for example, **4:00 PM** (desktop time = 13:00 PT), and untick "Allow
scheduled maintenance to wake up my computer". Read back (not elevated):
```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\Maintenance' | Select-Object 'Activation Boundary'
```
This moves the daily maintenance run only. Idle-triggered tasks (compatibility telemetry, .NET
image generation, defragmentation and the like) are not moved by it: they start when the machine is
idle, exactly as on a pilot night. The pilot discards any block they touch above 1% of one core
(revision 4 lists `CompatTelRunner`, `ngen`, `ngentask`, `mscorsvw`, `defrag`, `DismHost`, `cleanmgr`,
`wermgr` and `MpCmdRun`), so they cost discarded blocks, not wrong data.

**A4. Data directory, Defender and the indexer** (advisory).
```powershell
# not elevated:
New-Item -ItemType Directory -Force D:\mithril-data\x4\pilot, D:\mithril-data\x4\scratch, D:\mithril-data\x4\pins
# elevated, a security trade-off (your call). It also covers the pinned pilot binaries, which a
# pilot night launches from D:\mithril-data\x4\bin (in a daytime dry run MsMpEng used more than one
# full core over a block [M, 2026-10-23]):
Add-MpPreference -ExclusionPath 'D:\mithril-data'
```
(Revision 4: revision 3 also suggested excluding `D:\mithril\x4c\bin`. That is the agents' dev build
folder, not what a pilot night runs; excluding it would leave anything built or dropped there
unscanned for no gain, so the suggestion is withdrawn.)
Facts [M]: `C:\Users` is already excluded from Defender real-time scanning, so the model file
(`C:\Users\pierce lonergan\hearth-data\...`) is too; `D:\mithril-data` does not exist yet. The service
discards a block when Defender, the indexer or Windows Update servicing uses more than 1% of one core
over it, whether or not the exclusion is set. Indexer: Control Panel > Indexing Options > Modify,
untick `D:\mithril-data` if D: is indexed.

**A5. Free space on C:** (advisory). C: (the 990 PRO that holds the model) is **91.5% full, 158.5 GB
free** [M]. MEASUREMENT section 7.4 asks for at least about 20% free so the SLC cache behaves [G]. The
end-to-end decode only reads the model, so this affects read timing at most; freeing space, or
accepting it, is your call. Record the choice at signing.

**A6. How the driver is started** (required: the input sensor). `GetLastInputInfo` sees only the
session it runs in. Over SSH the driver runs in session 0 and cannot see the console, so a PILOT
night refuses ("interactive input ... in console session false" [M, 2026-10-23]). Start it in your
console session (session 1), either:
- by hand: a PowerShell window, at about 22:55 PT, `D:\mithril-data\x4\bin\x4svc.exe pilot-night --config
  D:\mithril-data\x4\pilot.cfg --pilot` (it waits for 23:00 PT, at most one hour); or
- with a scheduled task you create (this is the job wrapper of OWNER-QUEUE B13; a standing rule, so
  only you create it):
  ```powershell
  $a = New-ScheduledTaskAction -Execute 'D:\mithril-data\x4\bin\x4svc.exe' -Argument 'pilot-night --config D:\mithril-data\x4\pilot.cfg --pilot' -WorkingDirectory 'D:\mithril-data\x4'
  $t = New-ScheduledTaskTrigger -Daily -At 1:55AM          # desktop (Eastern) time = 22:55 PT
  # revision 4: priority 4 = normal. The default, 7, runs the task below normal [M, reviewer:
  # (New-ScheduledTaskSettingsSet).Priority = 7], and the driver refuses a night unless it runs at
  # NORMAL_PRIORITY_CLASS with normal memory priority
  $s = New-ScheduledTaskSettingsSet -Priority 4 -ExecutionTimeLimit (New-TimeSpan -Hours 9) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName 'Mithril-X4-pilot-night' -Action $a -Trigger $t -Settings $s   # no -User: runs as you, only while you are logged on, in your session [inference]
  ```
  Not tested by any agent: check once that the driver's first line of output (or its night
  directory's `voids.log`) shows `in console session Some(true)` and `driver at NORMAL_PRIORITY_CLASS
  ... ok` before relying on it. Disable it after the pilot week (`Disable-ScheduledTask -TaskName
  'Mithril-X4-pilot-night'`).
- **Once, before night 1, the readability check from your own session** (revision 4, required: every
  sensor reading so far was taken over SSH, which runs elevated [M: integrity level High]; your
  console session is not elevated, and whether Defender's, Windows Update's and the NVMe's readings
  work there is [inference] until checked). From a normal (not "Run as administrator") PowerShell
  window in your console session:
  ```powershell
  D:\mithril-data\x4\bin\x4svc.exe verify-hygiene --config D:\mithril-data\x4\pilot.cfg --as-pilot > D:\mithril-data\x4\launch-check.txt
  ```
  and, if you use the task, once through a temporary task with the same settings:
  ```powershell
  $c = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c D:\mithril-data\x4\bin\x4svc.exe verify-hygiene --config D:\mithril-data\x4\pilot.cfg --as-pilot > D:\mithril-data\x4\launch-check-task.txt' -WorkingDirectory 'D:\mithril-data\x4'
  Register-ScheduledTask -TaskName 'Mithril-X4-launch-check' -Action $c -Settings $s; Start-ScheduledTask -TaskName 'Mithril-X4-launch-check'
  # when D:\mithril-data\x4\launch-check-task.txt is written:
  Unregister-ScheduledTask -TaskName 'Mithril-X4-launch-check' -Confirm:$false
  ```
  The lead engineer commits both outputs with the pre-night amendment. Every `sensor:` line must read
  `ok`; the driver line must say `elevated Some(false)` and `integrity RID Some("0x2000")`.

**A7. Values the lead engineer fills before the first night** (the record's pre-night amendment; no
setting involved, listed so you know what the amendment holds): the freeze commit, the seed (printed by
`x4svc pilot-plan`), the SHA-256 of the binaries that will run (copied from the `D:\mithril\x4c\bin`
build into `D:\mithril-data\x4\bin`, so a later dev rebuild cannot change them: `x4harness_hearth.exe`,
`x4sb_probe.exe`, `x4svc.exe`), K, the two goldens, the LP masks
(`x4svc topology`: p = LP 2, mask 0x4; orchestrator LP 30 [M]; the driver checks them against the
topology at every night start), and (revision 4) the per-run overhead o_rt of each run type, the
end-to-end t_run,plan and time cap (3 daytime dev runs at N = 2,048 on 8 LPs), the SHA-256 of the
filled `pilot.cfg`, and your two A6 readability outputs. K now comes from 3 `x4svc dev-run` runs of
2^18 calls (each over 1 s, so the bracket checks it). The pins file per run type is made **after A1**
with (revision 4: the environment block now holds `CUDA_VISIBLE_DEVICES=-1`, so it is named here):
```powershell
D:\mithril-data\x4\bin\x4svc.exe fingerprint --scratch D:\mithril-data\x4\scratch --affinity 0x4 --env HEARTH_ISA=avx512 --env HEARTH_LOG=0 --env CUDA_VISIBLE_DEVICES=-1 |
  Select-String '^(power|fingerprint)' | ForEach-Object { $_.Line } | Set-Content -Encoding ascii D:\mithril-data\x4\pins\mb-q4-avx512.txt
```
(ASCII on purpose: Windows PowerShell's `>` writes UTF-16, which the strict pins parser rejects), and
for `e2e-decode` with its affinity and every `env` line of its run type, in the configuration's order
(the model path contains a space, so that argument is quoted):
```powershell
D:\mithril-data\x4\bin\x4svc.exe fingerprint --scratch D:\mithril-data\x4\scratch --affinity 0xbfffffff `
  --env HEARTH_ISA=avx512 --env HEARTH_LOG=0 --env CUDA_VISIBLE_DEVICES=-1 --env HEARTH_THREADS=16 --env HEARTH_IO_THREADS=8 --env HEARTH_CACHE_GB=8 `
  --env "X4_MODEL_PATH=C:\Users\pierce lonergan\hearth-data\qwen3-30b-a3b-q4.hearth" |
  Select-String '^(power|fingerprint)' | ForEach-Object { $_.Line } | Set-Content -Encoding ascii D:\mithril-data\x4\pins\e2e-decode.txt
```
(the values shown are C01's answer, R8; the block is sorted before hashing, so the order of the
`--env` options does not matter).

## B. Every pilot night, by 22:50 PT

1. Stop GEMS jobs and pause the GPU queue (your R5 answer). Close the launchers and every image on
   the excluded list: today these were running [M]: Claude Code / Claude desktop (`claude.exe` x12),
   `python` x16, OneDrive, Overwolf, CurseForge x7, EpicGamesLauncher, and WSL. An excluded process
   that **starts** or **uses any CPU** during a session voids it; one left running idle does not, but
   idle launchers rarely stay at zero CPU.
2. `wsl --shutdown` (WSL was running today: `vmmemWSL`, four `wsl`, `wslservice` [M]).
3. If you switch the plan nightly: `powercfg /setactive <MITHRIL-MEASURE GUID>`.
4. Optional preview, read-only, not elevated:
   `D:\mithril-data\x4\bin\x4svc.exe verify-hygiene --config D:\mithril-data\x4\pilot.cfg`.
   The driver runs the same items itself at the start (with `selftest`, which must print
   `mode: degraded-job-only`, and `verify-profile --collection --pins` per run type) and refuses the
   night on any failure.
5. Start the driver in your console session (A6), or let the task do it. Then leave the machine: any
   input, a new console or RDP session, a GPU job above 5% or the NVMe at 70 C or more voids the
   running session.
6. **No SSH or agent access to the desktop from 23:00 to 07:00 PT** (revision 4; your D0-7a answer
   says "no agents running then"). A new `sshd`, `sshd-session`, `powershell`, `pwsh` or `cmd`
   process voids the running session, so a laptop agent's `desk.sh`, or your own SSH login, costs a
   session. Scheduled tasks that start a shell in the window do the same; the void log names the
   process and its parent, so such a task can be found and moved.

**Morning, after 07:00 PT:** if you switch the plan nightly, `powercfg /setactive
381b4222-f694-41f0-9685-ff5bb260df2e`. The night's records are in `D:\mithril-data\x4\pilot\night-<date>`
(`manifest.txt` holds the hash of every record file).

## C. What fails today (read-only, 2026-10-23, 15:33 desktop time = 12:33 PT, revision-4 build)

From [VERIFY-2026-10-23-rev4.txt](VERIFY-2026-10-23-rev4.txt) [M] (`x4svc.exe` `68125f5e…02f9`; the
revision-3 report of 12:49 desktop time is [VERIFY-2026-10-23.txt](VERIFY-2026-10-23.txt)):

| Item | Today | Who fixes it |
|---|---|---|
| 7.1 power plan = the pinned measurement plan | FAIL: Balanced active | Pierce, A1 |
| 7.2 core parking 100/100 | ok (Balanced reads 100/100 through `powercfg /qh`) | re-checked on A1's plan |
| collection: pins files and fingerprint | FAIL: no pins file exists | lead engineer, after A1 (A7) |
| binary SHA-256 pins (harness, probe, x4svc) | not pinned (the DRAFT has no freeze yet) | lead engineer (A7) |
| placement equals the topology rule (revision 4) | ok: mb `0x4`, e2e `0xbfffffff`, orchestrator LP 30 | - |
| input sensor in the console session | FAIL over SSH (session 0) | the launch path, A6 |
| driver priority and memory priority (revision 4) | ok over SSH (NORMAL, 5); the scheduled task must be registered with `-Priority 4` (A6) | Pierce, A6 |
| readability from a non-elevated session (revision 4) | not checked: every reading so far ran elevated (integrity RID `0x3000`) | Pierce, A6 (once) |
| Windows Update active hours / pause | FAIL: active hours 06:00-00:00 desktop time (restarts allowed 21:00-03:00 PT); no pause set | Pierce, A2 |
| maintenance outside the window | FAIL: no Activation Boundary (default 2:00 AM Eastern = 23:00 PT) | Pierce, A3 |
| excluded processes idle | advisory: claude x12, python x28, OneDrive, Overwolf, CurseForge x7, EpicGamesLauncher running (WSL: only `wslservice`) | Pierce, nightly B1-B2 |
| `D:\mithril-data` | absent | Pierce or the driver, A4 |
| Defender exclusion of the data directory | advisory, not set (`C:\Users` is excluded) | Pierce, A4 |
| C: free space >= ~20% | advisory: 8.5% free (158.1 GB) | Pierce, A5 |
| sandbox self-test | ok: `degraded-job-only` with the job's affinity limit (revision 4: without the limit, under a confined launcher, it reads `refused`) | - |
| sensors | ok: machine load (`GetSystemTimes`) and per-LP load and effective clock (PDH, 32 of 32 LPs at 2 s), disk queue / writes / modified pages, process CPU (every listed image readable, elevated), WTS sessions, GPU via `nvidia-smi` (0% at 15:33), NVMe 42 C, power-scheme GUID; **no ACPI thermal-zone counter**, so CPU package temperature is unavailable (recorded, not gated) | - |
