# x0fix track (X0-A1), 2026-10-23: the PINNED x0_loops.py (8c7ecc9e, the freeze's) re-run read-only on census run 1, from
# a tree whose class/ files equal the pins (x0_loops.py's default --loop-table is ../class/loop_table.csv next to the
# script), to show that this environment reproduces run 1's own loops.json byte for byte. Then a1_compare.py on it.
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$C = 'D:\mithril\x0fixA1\cmp'
$J = 'D:\mithril\jobs\x0fixA1'
$T = 'D:\mithril\x0fixA1\tree_pinned'
"START $(Get-Date -Format o)" | Out-File -Append "$J\run1p_progress.txt"
if (Test-Path $T) { Remove-Item -Recurse -Force $T }
New-Item -ItemType Directory -Force $T | Out-Null
Set-Location $T
tar.exe -xf D:\mithril\x0fixA1\x0census_final.tar
Copy-Item -Force "$C\old\x0_loops.py" "$T\x0-census\scripts\x0_loops.py"
"pinned x0_loops $((Get-FileHash "$T\x0-census\scripts\x0_loops.py" -Algorithm SHA256).Hash) loop_table $((Get-FileHash "$T\x0-census\class\loop_table.csv" -Algorithm SHA256).Hash)" | Out-File -Append "$J\run1p_progress.txt"
$OUT = 'D:\mithril\x0fixA1\run1_reloop'
if (Test-Path "$OUT\old") { Remove-Item -Recurse -Force "$OUT\old" }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$C\reloop_job.ps1" -Run 'D:\mithril\x0census\run1' -Out $OUT -Tag 'run1p_reloop' -WinCfgs 'A,A-ninja,B-cmake,B-proxy,P.A,P.A-ninja,P.B-cmake' -WslCfgs 'C,D,P.C,P.D' -Scripts "old=$T\x0-census\scripts\x0_loops.py" *> "$J\run1p_reloop.log"
"reloop done $(Get-Date -Format o)" | Out-File -Append "$J\run1p_progress.txt"
$cfgs = @('A','A-ninja','B-cmake','B-proxy','P.A','P.A-ninja','P.B-cmake','C','D','P.C','P.D')
& C:\Python313\python.exe -I "$C\tools\a1_compare.py" 'D:\mithril\x0fixA1\tree\x0-census\scripts' "$OUT\old" @cfgs -o "$OUT\run1_compare_pinned_vs_census.json" *> "$J\run1p_compare_old.log"
"compare old rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Append "$J\run1p_progress.txt"
& C:\Python313\python.exe -I "$C\tools\a1_compare.py" 'D:\mithril\x0fixA1\tree\x0-census\scripts' "$OUT\new" @cfgs --before-dir "$OUT\old" -o "$OUT\run1_compare_new_vs_pinned.json" *> "$J\run1p_compare_newold.log"
"compare new-vs-pinned rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Append "$J\run1p_progress.txt"
"DONE $(Get-Date -Format o)" | Out-File -Append "$J\run1p_progress.txt"
