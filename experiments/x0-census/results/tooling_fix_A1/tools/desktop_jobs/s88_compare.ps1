# x0fix track (X0-A1), 2026-10-23: the step-88 re-run with the X0-A1 scripts against the 2026-10-17 final step-88 run
# with the scripts pinned at the freeze (read-only on both).
$env:CUDA_VISIBLE_DEVICES = '-1'
foreach ($r in @('R1reg', 'R2mock')) {
  $old = Join-Path 'D:\mithril\x0reg\runs' $r
  $new = Join-Path 'D:\mithril\x0fixA1\runs88' $r
  "== $r : $old -> $new"
  & C:\Python313\python.exe -I D:\mithril\x0fixA1\cmp\tools\a1_runcompare.py $old $new -o "D:\mithril\x0fixA1\cmp\s88_$r.compare.json"
}
