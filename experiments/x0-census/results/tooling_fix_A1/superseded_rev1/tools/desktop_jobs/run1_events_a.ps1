# x0fix track (X0-A1), 2026-10-23: FrameInfo events of the function holding run 1's A and A-ninja k_avx2 Q8 loop L7_290
# (newly unscreened; read only), and the disassembly around the call at 7:b47.
$env:CUDA_VISIBLE_DEVICES = '-1'
$S = 'D:\mithril\x0fixA1\tree\x0-census\scripts'
$T = 'D:\mithril\x0fixA1\cmp\tools\a1_events.py'
foreach ($c in @('A', 'A-ninja')) {
  $U = "D:\mithril\x0census\run1\$c\b1\all"
  & C:\Python313\python.exe -I $T $S "$U\decode" "$U\manifest.json" "${c}:k_avx2:matmul[Q8]" '7:290' | Out-File -Encoding utf8 "D:\mithril\x0fixA1\run1_reloop\events_${c}_b1_7_290.jsonl"
}
$U = 'D:\mithril\x0census\run1\A\b1\all'
& C:\Python313\python.exe -I -c "import json,sys; rows=[json.loads(l) for l in open(sys.argv[1],encoding='utf-8')]; rows=[r for r in rows if r.get('variant')=='A:k_avx2:matmul[Q8]' and r.get('section')==7 and 0xb00<=r['offset']<=0xb50 and r.get('role')=='reachable']; [print(hex(r['offset']), r.get('disasm')) for r in sorted(rows,key=lambda r:r['offset'])]" "$U\decode\instructions.jsonl" | Out-File -Encoding utf8 'D:\mithril\x0fixA1\run1_reloop\disasm_A_b1_7_b00.txt'
