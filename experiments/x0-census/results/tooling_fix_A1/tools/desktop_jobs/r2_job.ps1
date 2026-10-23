# x0fix track, X0-A1 revision after the independent review of 2026-10-23 ("r2"). With the re-pinned r2 tree, one step
# after the other (one process at a time; one compiler at a time; XED -j 2; no GPU; WSL only inside the running
# keepalive VM; TEMP/TMP on D:):
#   1. pin check of the tree (pin_inputs.py, expect 0 differences);
#   2. census run 1, READ ONLY (D:\mithril\x0census\run1: decodes, manifests, attribution files, objects; nothing written
#      there): the r2 x0_loops.py re-run on every recorded loops step (a1_reloop.py). No compile, no decode, no census;
#   3. the NON-Hearth reproduction run A1final (a1_escape.c, 2026-10-23): the r2 x0_loops.py on its decodes (read only);
#   4. runbook steps 86 and 88 with the r2 tree (R2 mock, R1 regression set, check_regression_run.py; assembler and
#      judge of the r2 tree);
#   5. comparisons (a1_compare, a1_allfields, a1_otherfields, a1_runcompare), all read only on their inputs.
param([string]$B = 'D:\mithril\x0fixA1\r2', [string]$J = 'D:\mithril\jobs\x0fixA1\r2')
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
New-Item -ItemType Directory -Force "$J\tmp", "$B\cmp" | Out-Null
$env:TEMP = "$J\tmp"; $env:TMP = "$J\tmp"
$PY = 'C:\Python313\python.exe'
$U = "$B\up"
$T = "$B\tree"
$TL = "$U\tools"
$P = "$J\r2_progress.txt"
"START $(Get-Date -Format o)" | Out-File -Append $P
if (Test-Path $T) { Remove-Item -Recurse -Force $T }
New-Item -ItemType Directory -Force $T | Out-Null
Set-Location $T
tar.exe -xf "$U\x0census_r2.tar"
$X = "$T\x0-census\scripts"
foreach ($f in @('x0_loops.py', 'x0_census.py', 'judge.py')) {
  "$f $((Get-FileHash "$X\$f" -Algorithm SHA256).Hash)" | Out-File -Append $P
}
& $PY -I "$X\runbook\pin_inputs.py" *> "$J\r2_pin_inputs.log"
"pin_inputs rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Append $P

# 2. census run 1 (read only)
$RUN = 'D:\mithril\x0census\run1'
$win = @(); $wsl = @()
foreach ($d in (Get-ChildItem $RUN -Directory | Sort-Object Name)) {
  if (-not (Test-Path (Join-Path $d.FullName 'config.json'))) { continue }
  $cj = Get-Content (Join-Path $d.FullName 'config.json') -Raw
  if ($cj -match '"/usr/bin/python3"') { $wsl += $d.Name } else { $win += $d.Name }
}
"run1 win=$($win -join ',') wsl=$($wsl -join ',')" | Out-File -Append $P
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$U\reloop_job_r2.ps1" -Run $RUN -Out "$B\run1_reloop" -Tag 'r2_run1' -WinCfgs ($win -join ',') -WslCfgs ($wsl -join ',') -Scripts "new=$X\x0_loops.py" -J $J -T "$TL\a1_reloop.py" *> "$J\r2_run1_reloop.log"
"run1 reloop done $(Get-Date -Format o)" | Out-File -Append $P

# 3. the reproduction's decodes (read only)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$U\reloop_job_r2.ps1" -Run 'D:\mithril\x0fixA1\runs\A1final' -Out "$B\A1final_reloop" -Tag 'r2_A1final' -WinCfgs 'A,A-ninja,B-cmake' -WslCfgs 'C,D' -Scripts "new=$X\x0_loops.py" -J $J -T "$TL\a1_reloop.py" *> "$J\r2_A1final_reloop.log"
"A1final reloop done $(Get-Date -Format o)" | Out-File -Append $P

# 4. steps 86 and 88 with the r2 tree
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$U\a1_step88.ps1" -Tree "$T\x0-census" -Runs "$B\runs88" -J $J *> "$J\r2_s88.log"
"step88 done $(Get-Date -Format o)" | Out-File -Append $P

# 5. comparisons
$cfgs = @($win + $wsl)
& $PY -I "$TL\a1_compare.py" $X "$B\run1_reloop\new" @cfgs -o "$B\cmp\run1_compare_new_vs_census.json" *> "$J\r2_cmp_run1.log"
"cmp run1 rc=$LASTEXITCODE" | Out-File -Append $P
& $PY -I "$TL\a1_allfields.py" reloop "$B\run1_reloop\new" @cfgs -o "$B\cmp\run1_allfields.json" *> "$J\r2_allfields_run1.log"
"allfields run1 rc=$LASTEXITCODE" | Out-File -Append $P
& $PY -I "$TL\a1_otherfields.py" 'D:\mithril\x0fixA1\run1_reloop\old' "$B\run1_reloop\new" -o "$B\cmp\run1_otherfields.json" *> "$J\r2_otherfields_run1.log"
"otherfields run1 rc=$LASTEXITCODE" | Out-File -Append $P
$rc = @('A', 'A-ninja', 'B-cmake', 'C', 'D')
$OLDR = 'D:\mithril\x0fixA1\cmp\A1final_out\old'
& $PY -I "$TL\a1_compare.py" $X "$B\A1final_reloop\new" @rc --before-dir $OLDR -o "$B\cmp\A1final_compare.json" *> "$J\r2_cmp_A1final.log"
"cmp A1final rc=$LASTEXITCODE" | Out-File -Append $P
& $PY -I "$TL\a1_allfields.py" reloop "$B\A1final_reloop\new" @rc --before-dir $OLDR -o "$B\cmp\A1final_allfields.json" *> "$J\r2_allfields_A1final.log"
"allfields A1final rc=$LASTEXITCODE" | Out-File -Append $P
& $PY -I "$TL\a1_otherfields.py" $OLDR "$B\A1final_reloop\new" -o "$B\cmp\A1final_otherfields.json" *> "$J\r2_otherfields_A1final.log"
"otherfields A1final rc=$LASTEXITCODE" | Out-File -Append $P
foreach ($r in @('R1reg', 'R2mock')) {
  & $PY -I "$TL\a1_runcompare.py" (Join-Path 'D:\mithril\x0reg\runs' $r) (Join-Path "$B\runs88" $r) -o "$B\cmp\s88_$r.compare.json" *> "$J\r2_s88cmp_$r.log"
  & $PY -I "$TL\a1_allfields.py" runs (Join-Path 'D:\mithril\x0reg\runs' $r) (Join-Path "$B\runs88" $r) -o "$B\cmp\s88_$r.allfields.json" *> "$J\r2_s88all_$r.log"
  & $PY -I "$TL\a1_runcompare.py" (Join-Path 'D:\mithril\x0fixA1\runs88' $r) (Join-Path "$B\runs88" $r) -o "$B\cmp\s88_$r.vs_rev1.compare.json" *> "$J\r2_s88rev1_$r.log"
  "s88 compares $r done" | Out-File -Append $P
}
"DONE $(Get-Date -Format o)" | Out-File -Append $P
