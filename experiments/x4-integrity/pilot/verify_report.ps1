# X4 noise pilot -- the read-only pre-start report (X4 pilot track, 2026-10-23; revision 4 the same day).
# Reads state only: no setting is changed, no pilot run is made. The sandbox self-test runs its probes
# inside a Job Object (the nightly check of the record's section 11), which is not pilot data.
# Run on the desktop: powershell -NoProfile -File verify_report.ps1 > VERIFY-<date>.txt
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:TEMP = 'D:\mithril\x4c\tmp'; $env:TMP = 'D:\mithril\x4c\tmp'
$svc = 'D:\mithril\x4c\bin\x4svc.exe'
$cfg = 'D:\mithril\x4c\src\pilot\verify-now.cfg'
"== X4 noise-pilot pre-start report, read-only"
"host $(hostname); desktop clock $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ($((Get-TimeZone).Id)); UTC $((Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss'))"
"x4svc sha256 $((Get-FileHash $svc -Algorithm SHA256).Hash.ToLower())"
""
"== 1. x4svc verify-profile (the quiet-machine profile, MEASUREMENT section 7)"
& $svc verify-profile --data-dir 'D:\mithril-data'
"rc=$LASTEXITCODE"
""
"== 2. x4svc verify-profile --collection with the round-3 dev pins (Balanced GUID, mask 0x1 fingerprint)"
& $svc verify-profile --data-dir 'D:\mithril-data' --collection --pins 'D:\mithril\x4b\jobs\pins_dev.txt' --scratch 'D:\mithril-data\x4\scratch' --affinity 0x4 --env HEARTH_ISA=avx512 --env HEARTH_LOG=0
"rc=$LASTEXITCODE"
""
"== 3. x4svc fingerprint for mb-q4-avx512 (what a pins file would hold today; NOT a pin: the plan is still Balanced)"
& $svc fingerprint --scratch 'D:\mithril-data\x4\scratch' --affinity 0x4 --env HEARTH_ISA=avx512 --env HEARTH_LOG=0 --env CUDA_VISIBLE_DEVICES=-1
""
"== 4. x4svc verify-hygiene --as-pilot (every section 10 sensor and pre-start item)"
& $svc verify-hygiene --config $cfg --as-pilot
"rc=$LASTEXITCODE"
""
"== 5. x4svc selftest without --sealed, the job limited to one LP (a pilot night uses the microbenchmark's mask; this report uses LP 28, inside the agent's LPs); expect mode degraded-job-only"
# the scratch probe needs an EMPTY directory: a fresh one, removed afterwards
$st = "D:\mithril\x4c\tmp\selftest-$PID"
New-Item -ItemType Directory -Force $st | Out-Null
& $svc selftest --harness 'D:\mithril\x4c\bin\x4harness_hearth.exe' --probe-exe 'D:\mithril\x4c\bin\x4sb_probe.exe' --scratch $st --affinity 0x10000000 | Select-String -Pattern '^job affinity|^mode|^decision|^state|note:'
Remove-Item -Recurse -Force $st
""
"== 6. settings the pre-night checklist names (read-only queries)"
"-- active power scheme:"; powercfg /getactivescheme
"-- power schemes:"; powercfg /list
$ux = 'HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings'
$u = Get-ItemProperty $ux -ErrorAction SilentlyContinue
"-- Windows Update active hours (desktop clock): start $($u.ActiveHoursStart) end $($u.ActiveHoursEnd); smart active hours state $($u.SmartActiveHoursState)"
"-- Windows Update pause: PauseUpdatesExpiryTime=$($u.PauseUpdatesExpiryTime) PauseFeatureUpdatesEndTime=$($u.PauseFeatureUpdatesEndTime) PauseQualityUpdatesEndTime=$($u.PauseQualityUpdatesEndTime)"
$m = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Schedule\Maintenance' -ErrorAction SilentlyContinue
"-- automatic maintenance: Activation Boundary=$($m.'Activation Boundary') MaintenanceDisabled=$($m.MaintenanceDisabled) WakeUp=$($m.WakeUp)"
"-- Defender exclusion paths (non-elevated reads show a placeholder): $(((Get-MpPreference -ErrorAction SilentlyContinue).ExclusionPath) -join '; ')"
"-- Windows Search service: $((Get-Service WSearch -ErrorAction SilentlyContinue).Status)"
"-- D:\mithril-data exists: $(Test-Path 'D:\mithril-data')"
"-- WSL processes: $((Get-Process vmmemWSL, wsl, wslhost, wslservice -ErrorAction SilentlyContinue | ForEach-Object { $_.Name + '(' + $_.Id + ')' }) -join ', ')"
"-- excluded-image processes running now: $((Get-Process claude, node, cl, link, cargo, rustc, python, pythonw, OneDrive, Overwolf, CurseForge, EpicGamesLauncher -ErrorAction SilentlyContinue | Group-Object Name | ForEach-Object { $_.Name + ' x' + $_.Count }) -join ', ')"
"-- this session: id $((Get-Process -Id $PID).SessionId); console session: $(try { (Get-CimInstance Win32_ComputerSystem).UserName } catch { '?' }); query user:"
try { query user 2>&1 } catch { "query user unavailable" }
"-- free space C: / D: (GB): $([math]::Round((Get-PSDrive C).Free/1GB,1)) / $([math]::Round((Get-PSDrive D).Free/1GB,1))"
"-- C: used fraction: $([math]::Round((Get-PSDrive C).Used / ((Get-PSDrive C).Used + (Get-PSDrive C).Free), 3))"
"-- nvidia-smi: $((Get-Command nvidia-smi -ErrorAction SilentlyContinue).Source)"
