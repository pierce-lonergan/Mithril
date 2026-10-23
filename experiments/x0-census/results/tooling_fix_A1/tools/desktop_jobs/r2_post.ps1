# x0fix track, revision after the review of 2026-10-23 (r2), after r2_job.ps1: the changed-loop list of census run 1, the
# FrameInfo events of the functions holding run 1's changed loops (read only; a1_events.py with the r2 script), and tar
# files of the job logs (rev1 and r2) and of the r2 outputs for the laptop. No compile, no decode, no WSL.
# (PowerShell variable names are case-insensitive: the build loop uses $bb, not $b, so that $B stays the r2 folder.)
param([string]$B = 'D:\mithril\x0fixA1\r2', [string]$J = 'D:\mithril\jobs\x0fixA1\r2')
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:TEMP = "$J\tmp"; $env:TMP = "$J\tmp"
$PY = 'C:\Python313\python.exe'
$S = "$B\tree\x0-census\scripts"
$T = "$B\up\tools\a1_events.py"
$E = "$B\cmp\events"
New-Item -ItemType Directory -Force $E | Out-Null
& $PY -I "$B\up\run1_loopinfo_r2.py" $B *> "$J\r2_loopinfo.log"
foreach ($bb in @('b1', 'b2')) {
  $U = "D:\mithril\x0census\run1\C\$bb\all"
  foreach ($v in @(@('C:k_avx512:matmul[Q8]', '1:d98'), @('C:k_avx512:matmul[Q4]', '1:2e90'))) {
    & $PY -I $T $S "$U\decode" "$U\manifest.json" $v[0] $v[1] | Out-File -Encoding utf8 "$E\events_C_${bb}_$($v[1].Replace(':','_')).jsonl"
  }
}
foreach ($c in @('A', 'A-ninja')) {
  $U = "D:\mithril\x0census\run1\$c\b1\all"
  & $PY -I $T $S "$U\decode" "$U\manifest.json" "${c}:k_avx2:matmul[Q8]" '7:290' | Out-File -Encoding utf8 "$E\events_${c}_b1_7_290.jsonl"
}
Set-Location 'D:\mithril\jobs\x0fixA1'
$rev1 = @(Get-ChildItem -File -Name) + @('s88')
tar.exe -cf "$B\joblogs_rev1.tar" @rev1
Set-Location $J
tar.exe -cf "$B\joblogs_r2.tar" --exclude=tmp *
Set-Location $B
$nl = @()
foreach ($d in (Get-ChildItem "$B\run1_reloop\new" -Directory)) {
  $nl += "run1_reloop/new/$($d.Name)/reloop.json"
  foreach ($s in (Get-ChildItem $d.FullName -Directory)) { $nl += "run1_reloop/new/$($d.Name)/$($s.Name)/loops.json" }
}
foreach ($d in (Get-ChildItem "$B\A1final_reloop\new" -Directory)) { $nl += "A1final_reloop/new/$($d.Name)/reloop.json" }
foreach ($r in @('R1reg', 'R2mock')) {
  foreach ($f in @('run.json', 'summary.json', 'verdict.json', 'verdict_regression_profile.json', 'verdict_synthetic_rederivation.json')) {
    if (Test-Path "$B\runs88\$r\$f") { $nl += "runs88/$r/$f" }
  }
}
tar.exe -cf "$B\r2_out.tar" cmp @nl
"post DONE $(Get-Date -Format o)" | Out-File -Append "$J\r2_progress.txt"
