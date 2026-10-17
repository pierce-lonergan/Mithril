#!/bin/bash
# X0 runbook step 71b (pre-freeze, WSL): compile the NON-Hearth regression inputs of step 72 -- smoke_dispatch.c and
# the adversarial rv_tricky.c / rv_tricky2.c (scripts/smoke/) -- with the C and D command lines of quant_avx512.c and
# quant.c (x0_flags.py replay; the source and object paths are the only substitutions). It compiles NO Hearth
# source. One thread. Needs step 51's configure trees (D:\mithril\x0\cfg\C-gcc, D-clang).
# Run (keepalive VM already up): wsl.exe -d Ubuntu -- bash /mnt/d/mithril/x0prep/x0/scripts/runbook/71b_regression_compile_wsl.sh
exec 2>&1
export CUDA_VISIBLE_DEVICES=-1
mkdir -p /mnt/d/mithril/jobs/x0prep/tmp
export TMPDIR=/mnt/d/mithril/jobs/x0prep/tmp
W=/mnt/d/mithril/x0prep
S=$W/x0/scripts
R=$W/reg
CFG=/mnt/d/mithril/x0/cfg
echo "START $(date -Is)"
for c in C D; do
  db=$CFG/C-gcc/compile_commands.json; [ $c = D ] && db=$CFG/D-clang/compile_commands.json
  for pair in "$c:quant_avx512.c" "$c-scalar:quant.c"; do
    cfg=${pair%%:*}; as=${pair#*:}
    for n in smoke_dispatch rv_tricky rv_tricky2; do
      mkdir -p $R/$cfg/$n
      python3 -I $S/x0_flags.py replay $db --as $as --src $S/smoke/$n.c --obj $R/$cfg/$n/$n.o --exec
      echo "${cfg}_${n}_RC=$?"
    done
  done
done
echo "END $(date -Is)"
