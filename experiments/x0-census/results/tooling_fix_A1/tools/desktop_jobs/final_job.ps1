# x0fix track (X0-A1), 2026-10-23: with the re-pinned X0-A1 tree D:\mithril\x0fixA1\tree\x0-census, one after the other:
#   1. the NON-Hearth reproduction a1_escape.c under A, A-ninja, B-cmake, C, D (run A1final; loops by the fixed script);
#   2. the pinned (frozen, 8c7ecc9e) x0_loops.py re-run read-only on A1final's decodes (the BEFORE side);
#   3. runbook steps 86 and 88 (R2 mock, R1 regression set, check_regression_run.py).
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$C = 'D:\mithril\x0fixA1\cmp'
$J = 'D:\mithril\jobs\x0fixA1'
"START $(Get-Date -Format o)" | Out-File -Append "$J\final_progress.txt"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$C\a1_dev.ps1" -Tree 'D:\mithril\x0fixA1\tree\x0-census' -Run 'D:\mithril\x0fixA1\runs\A1final' -Tag 'A1final' *> "$J\final_a1.log"
"A1final done $(Get-Date -Format o)" | Out-File -Append "$J\final_progress.txt"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$C\reloop_job.ps1" -Run 'D:\mithril\x0fixA1\runs\A1final' -Out "$C\A1final_out" -Tag 'A1final_reloop' -WinCfgs 'A,A-ninja,B-cmake' -WslCfgs 'C,D' -Scripts "old=$C\old\x0_loops.py;new=D:\mithril\x0fixA1\tree\x0-census\scripts\x0_loops.py" *> "$J\final_reloop.log"
"A1final reloop done $(Get-Date -Format o)" | Out-File -Append "$J\final_progress.txt"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$C\a1_step88.ps1" -Tree 'D:\mithril\x0fixA1\tree\x0-census' -Runs 'D:\mithril\x0fixA1\runs88' *> "$J\final_s88.log"
"step88 done $(Get-Date -Format o)" | Out-File -Append "$J\final_progress.txt"
"DONE $(Get-Date -Format o)" | Out-File -Append "$J\final_progress.txt"
