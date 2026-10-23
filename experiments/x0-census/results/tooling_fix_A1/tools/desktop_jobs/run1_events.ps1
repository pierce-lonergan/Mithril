# x0fix track (X0-A1), 2026-10-23: FrameInfo events of the functions holding run 1's four flagged C loops (read only).
$env:CUDA_VISIBLE_DEVICES = '-1'
$S = 'D:\mithril\x0fixA1\tree\x0-census\scripts'
$T = 'D:\mithril\x0fixA1\cmp\tools\a1_events.py'
foreach ($b in @('b1', 'b2')) {
  $U = "D:\mithril\x0census\run1\C\$b\all"
  foreach ($v in @(@('C:k_avx512:matmul[Q8]', '1:d98'), @('C:k_avx512:matmul[Q4]', '1:2e90'))) {
    & C:\Python313\python.exe -I $T $S "$U\decode" "$U\manifest.json" $v[0] $v[1] *> "D:\mithril\x0fixA1\run1_reloop\events_C_${b}_$($v[1].Replace(':','_')).jsonl"
  }
}
Get-ChildItem D:\mithril\x0fixA1\run1_reloop\events_* | Select-Object Name, Length
