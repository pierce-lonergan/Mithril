#!/bin/bash
# X0 runbook step 61: compile the SMOKE file (never Hearth) for C (gcc) and D (clang) with the exact
# quant_avx512.c flags, then extract + decode all four smoke objects (A,B from step 60) with the
# Linux XED build, cross-checking symbols (llvm-readobj) and boundaries (llvm-objdump).
# Finishes with a negative test: corrupted manifests must make x0_decode.py fail.
# Run: wsl.exe -d Ubuntu -- bash /mnt/d/mithril/x0/scripts/runbook/61_smoke_wsl.sh > D:\mithril\jobs\61_smoke_wsl.log
exec 2>&1
export CUDA_VISIBLE_DEVICES=-1
mkdir -p /mnt/d/mithril/jobs/tmp
export TMPDIR=/mnt/d/mithril/jobs/tmp
S=/mnt/d/mithril/x0/scripts
O=/mnt/d/mithril/x0/smoke
L=/mnt/d/mithril/tools/llvm-linux-23.1.3/bin
X=/mnt/d/mithril/tools/xed-v2026.08.23/bin/xed
cd /mnt/d/mithril/x0 || exit 1
for c in C-gcc D-clang; do
  echo "==== $c: smoke.c with the flags of quant_avx512.c"
  python3 -I $S/x0_flags.py replay /mnt/d/mithril/x0/cfg/$c/compile_commands.json --as quant_avx512.c \
      --src $S/smoke/smoke.c --obj $O/$c/smoke.o --exec
  echo "${c}_SMOKE_RC=$?"
done
rm -f $O/xed_attr_cache.json
for c in A-msvc B-clangcl C-gcc D-clang; do
  f=$O/$c/smoke.obj; [ -f $f ] || f=$O/$c/smoke.o
  echo "==== $c: extract"
  python3 -I $S/x0_extract.py --readobj $L/llvm-readobj --label $c -o $O/$c/manifest.json $f
  echo "${c}_EXTRACT_RC=$?"
  rm -rf $O/$c/decode
  python3 -I $S/x0_decode.py $O/$c/manifest.json -o $O/$c/decode --xed $X --objdump $L/llvm-objdump -j 8 \
      --attr-cache $O/xed_attr_cache.json > $O/$c/decode.log
  echo "${c}_DECODE_RC=$?"
  python3 -I -c "import json; s=json.load(open('$O/$c/decode/summary.json')); print('$c', s['functions'], 'functions', s['instructions'], 'instructions', s['xed_mode'], s['anomaly_kinds'])"
done
echo "==== negative test (manifests corrupted on purpose; decode must exit 1 with errors)"
for c in A-msvc C-gcc; do
  python3 -I $S/runbook/negtest.py $O/$c/manifest.json $O/$c/manifest_neg.json
  rm -rf $O/$c/decode_neg
  python3 -I $S/x0_decode.py $O/$c/manifest_neg.json -o $O/$c/decode_neg --xed $X --objdump $L/llvm-objdump -j 8 > /dev/null
  echo "${c}_NEG_RC=$? (expect 1)"
  python3 -I -c "import json; s=json.load(open('$O/$c/decode_neg/summary.json')); print('$c NEG', s['anomaly_kinds'])"
done
echo DONE
