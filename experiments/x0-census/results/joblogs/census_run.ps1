# X0 census run (after freeze), desktop orchestrator: runbook steps 80, 81, 82 in sequence, one job at a time.
# Init (step 79) already ran: run D:\mithril\x0census\run1, census-20261017T141025Z, freeze = run commit 152fa33.
# Threads: one compiler or MSBuild node at a time, XED -j 2 (driver defaults); no GPU; runs only 07:00-23:00 PT.
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:X0 = 'D:\mithril\x0census\Mithril\experiments\x0-census'
$X0 = $env:X0
$R = 'D:\mithril\x0census\run1'
$RW = '/mnt/d/mithril/x0census/run1'
$X0W = '/mnt/d/mithril/x0census/Mithril/experiments/x0-census'
$J = 'D:\mithril\jobs\x0census'
$K = "$X0\scripts\runbook\80_census_win.cmd"
$W = "$X0W/scripts/runbook/81_census_wsl.sh"
$P = "$J\progress.txt"
function PT { [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow, 'Pacific Standard Time') }
function InWindow { $h = (PT).Hour; return ($h -ge 7 -and $h -lt 23) }
function Log([string]$m) { ("{0} PT{1} {2}" -f (Get-Date).ToString('o'), (PT).ToString('HH:mm'), $m) | Out-File -Append -Encoding utf8 $P }
function RcOf([string]$log, [string]$pat) { $l = Select-String -Path $log -Pattern $pat -ErrorAction SilentlyContinue | Select-Object -Last 1; if ($l) { $l.Line } else { 'no rc line' } }
function Win([string]$name, [string]$args2) {
  if (-not (InWindow)) { Log "STOP outside window before $name"; exit 3 }
  Log "BEGIN $name"
  cmd /v:on /c "$K $R $args2 > $J\80_$name.log 2>&1"
  Log ("END {0} {1}" -f $name, (RcOf "$J\80_$name.log" 'CONFIG_RC='))
}
function Wsl([string]$name, [string]$args2) {
  if (-not (InWindow)) { Log "STOP outside window before $name"; exit 3 }
  Log "BEGIN $name"
  cmd /c "wsl.exe -d Ubuntu -- env X0=$X0W CUDA_VISIBLE_DEVICES=-1 bash $W $RW $args2 > $J\81_$name.log 2>&1"
  Log ("END {0} {1}" -f $name, (RcOf "$J\81_$name.log" 'CONFIG_RC='))
}
Log "START orchestrator pid $PID"
# ---- step 80: Windows configurations (census mode), arm P on Windows, B-proxy (secondary, replay mode)
Win 'A' 'A census'
Win 'A-ninja' 'A-ninja census'
Win 'B-cmake' 'B-cmake census'
Win 'P.A' 'P.A probe --from-config A'
Win 'P.A-ninja' 'P.A-ninja probe --from-config A-ninja'
Win 'P.B-cmake' 'P.B-cmake probe --from-config B-cmake'
Win 'B-proxy' "B-proxy replay --set $X0\scripts\runbook\bproxy_set.json"
# ---- step 81: WSL configurations, inside a keepalive VM
$ka = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'wsl.exe' -and $_.CommandLine -match 'sleep' }
if (-not $ka) {
  $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = 'wsl.exe -d Ubuntu --exec sleep 14400'; CurrentDirectory = 'D:\mithril\jobs\x0census' }
  Log ("KEEPALIVE started: wsl.exe -d Ubuntu --exec sleep 14400, pid {0} rc {1}" -f $r.ProcessId, $r.ReturnValue)
  Start-Sleep -Seconds 20
} else { Log "KEEPALIVE already running" }
Log ("WSL running: " + ((wsl.exe -l --running | Out-String) -replace "`0", '' -replace "\s+", ' '))
Wsl 'C' 'C census'
Wsl 'D' 'D census'
Wsl 'P.C' 'P.C probe --from-config C'
Wsl 'P.D' 'P.D probe --from-config D'
# ---- step 82: census.json, then verdict.json
if (-not (InWindow)) { Log "STOP outside window before assemble"; exit 3 }
Log "BEGIN assemble"
cmd /c "$X0\scripts\runbook\82_census_assemble.cmd $R > $J\82_assemble.log 2>&1"
Log ("END assemble {0}" -f (RcOf "$J\82_assemble.log" 'ASSEMBLE_RC='))
Log "DONE"
