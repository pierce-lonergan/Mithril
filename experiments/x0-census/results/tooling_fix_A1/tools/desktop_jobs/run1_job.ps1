# x0fix track (X0-A1), 2026-10-23, LAST STEP: the fixed x0_loops.py (and, as a check of the environment, the pinned
# frozen one) applied READ-ONLY to census run 1's existing decodes, manifests, attribution files and objects
# (D:\mithril\x0census\run1, post-data). No compile, no decode, no new census; nothing under run1 is written.
# Windows configurations with C:\Python313, WSL configurations inside the running keepalive VM; one process at a time.
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$C = 'D:\mithril\x0fixA1\cmp'
$J = 'D:\mithril\jobs\x0fixA1'
$RUN = 'D:\mithril\x0census\run1'
$OUT = 'D:\mithril\x0fixA1\run1_reloop'
$win = @(); $wsl = @()
foreach ($d in (Get-ChildItem $RUN -Directory | Sort-Object Name)) {
  if (-not (Test-Path (Join-Path $d.FullName 'config.json'))) { continue }
  $cj = Get-Content (Join-Path $d.FullName 'config.json') -Raw
  if ($cj -match '"/usr/bin/python3"') { $wsl += $d.Name } else { $win += $d.Name }
}
"START $(Get-Date -Format o) win=$($win -join ',') wsl=$($wsl -join ',')" | Out-File -Append "$J\run1_progress.txt"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$C\reloop_job.ps1" -Run $RUN -Out $OUT -Tag 'run1_reloop' -WinCfgs ($win -join ',') -WslCfgs ($wsl -join ',') -Scripts "old=$C\old\x0_loops.py;new=D:\mithril\x0fixA1\tree\x0-census\scripts\x0_loops.py" *> "$J\run1_reloop.log"
"reloop done $(Get-Date -Format o)" | Out-File -Append "$J\run1_progress.txt"
$cfgs = @($win + $wsl)
& C:\Python313\python.exe -I "$C\tools\a1_compare.py" 'D:\mithril\x0fixA1\tree\x0-census\scripts' "$OUT\new" @cfgs -o "$OUT\run1_compare_new_vs_census.json" *> "$J\run1_compare_new.log"
"compare new rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Append "$J\run1_progress.txt"
& C:\Python313\python.exe -I "$C\tools\a1_compare.py" 'D:\mithril\x0fixA1\tree\x0-census\scripts' "$OUT\old" @cfgs -o "$OUT\run1_compare_pinned_vs_census.json" *> "$J\run1_compare_old.log"
"compare old rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Append "$J\run1_progress.txt"
"DONE $(Get-Date -Format o)" | Out-File -Append "$J\run1_progress.txt"
