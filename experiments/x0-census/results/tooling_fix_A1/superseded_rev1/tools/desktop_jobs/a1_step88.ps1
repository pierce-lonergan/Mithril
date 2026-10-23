# x0fix track (X0-A1), 2026-10-23: runbook steps 86 (the mock's configure-only captures) and 88 (R2 mock in census
# mode with arm P and B-proxy; R1 regression set in replay mode with arm P; check_regression_run.py) with the X0-A1
# scripts of $Tree, as the desktop re-run of 2026-10-17 ran them. One job at a time; one compiler at a time; XED -j 2;
# WSL only inside the running keepalive VM; no GPU.
param([string]$Tree = 'D:\mithril\x0fixA1\tree\x0-census', [string]$Runs = 'D:\mithril\x0fixA1\runs88',
      [string]$J = 'D:\mithril\jobs\x0fixA1')
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
New-Item -ItemType Directory -Force "$J\tmp", "$J\s88", $Runs | Out-Null
$env:TEMP = "$J\tmp"; $env:TMP = "$J\tmp"
$env:X0 = $Tree
function W([string]$p) { '/mnt/' + $p.Substring(0,1).ToLower() + $p.Substring(2).Replace([char]92, [char]47) }
$F = "$Runs\mockfrozen"
"START $(Get-Date -Format o) tree=$(W $Tree) F=$(W $F)" | Out-File -Append "$J\s88_progress.txt"
& C:\Python313\python.exe -I "$Tree\scripts\runbook\pin_inputs.py" *> "$J\s88_pin_inputs.log"
"pin_inputs rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Append "$J\s88_progress.txt"
cmd /v:on /c "$Tree\scripts\runbook\86_mock_prefreeze_win.cmd $F" *> "$J\s86_win.log"
"86 win done $(Get-Date -Format o)" | Out-File -Append "$J\s88_progress.txt"
wsl.exe -d Ubuntu -- env X0=$(W $Tree) bash "$(W $Tree)/scripts/runbook/86_mock_prefreeze_wsl.sh" (W $F) *> "$J\s86_wsl.log"
"86 wsl done $(Get-Date -Format o)" | Out-File -Append "$J\s88_progress.txt"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$Tree\scripts\runbook\88_x0final_smoke_runs.ps1" -X "$Tree\scripts" -Runs $Runs -F $F -J "$J\s88" *> "$J\s88_driver.log"
"88 done $(Get-Date -Format o)" | Out-File -Append "$J\s88_progress.txt"
"DONE $(Get-Date -Format o)" | Out-File -Append "$J\s88_progress.txt"
