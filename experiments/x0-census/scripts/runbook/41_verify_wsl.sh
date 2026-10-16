#!/bin/bash
# X0 runbook step 41: verify LLVM 23.1.3 for Linux inside WSL (Ubuntu 24.04, glibc headers) and record
# compiler defaults that compile_commands.json does not show.
# Run: wsl.exe -d Ubuntu -- bash /mnt/d/mithril/x0/scripts/runbook/41_verify_wsl.sh > D:\mithril\jobs\41_verify_wsl.log
exec 2>&1
export CUDA_VISIBLE_DEVICES=-1
mkdir -p /mnt/d/mithril/jobs/tmp /mnt/d/mithril/x0/wslverify
export TMPDIR=/mnt/d/mithril/jobs/tmp
L=/mnt/d/mithril/tools/llvm-linux-23.1.3/bin
P=/mnt/d/mithril/x0/scripts/runbook/probes
W=/mnt/d/mithril/x0/wslverify
CC1="python3 -I /mnt/d/mithril/x0/scripts/runbook/cc1flags.py"
cd "$W" || exit 1
echo "==== versions"
$L/clang --version
$L/llvm-objdump --version | grep -i "llvm version"
$L/llvm-readobj --version | grep -i "llvm version"
gcc --version | head -1; readlink -f /usr/bin/gcc; make --version | head -1; python3 --version
echo "==== shared-library deps of clang"; ldd "$(readlink -f $L/clang)"
echo "==== clang: compile+link+run, -mavx512f, Ubuntu glibc headers (<math.h> <stdint.h> <immintrin.h>)"
$L/clang -O2 -mavx512f -v $P/hello_avx512.c -o $W/hello512_clang -lm 2>&1 | grep -E "^ /|Selected GCC"
echo "compile rc=${PIPESTATUS[0]}"
$W/hello512_clang; echo "run rc=$?"
echo "==== clang -### cc1 FP/ISA flags (Hearth's quant_avx512.c flag set)"
$L/clang -O3 -DNDEBUG -std=gnu11 -fPIC -ffp-contract=off -mavx512f -mavx512bw -mavx512vl -mavx512vnni -mavx2 -mfma -mf16c -### -c $P/fpc.c 2>&1 | $CC1
echo "[clang -O3, no -ffp-contract]"; $L/clang -O3 -### -c $P/fpc.c 2>&1 | $CC1
echo "==== a*b+c codegen with -mavx2 -mfma"
for c in gcc $L/clang; do
  for f in "-ffp-contract=off" ""; do
    echo "[$(basename $c) -O3 -mavx2 -mfma $f]"
    $c -O3 -mavx2 -mfma $f -masm=intel -S -o - $P/fpc.c | grep -E "vfmadd|vmulss|vaddss"
  done
done
echo "==== implicit defaults with Hearth's C flags (-O3 -DNDEBUG -std=gnu11 -fPIC -ffp-contract=off)"
F="-O3 -DNDEBUG -std=gnu11 -fPIC -ffp-contract=off"
echo "[gcc predefined]"; echo | gcc $F -dM -E -x c - | grep -E "FORTIFY|__PIE__|__PIC__|__CET__|__SSP|__FAST_MATH|FLT_EVAL_METHOD__" | sort
echo "[clang predefined]"; echo | $L/clang $F -dM -E -x c - | grep -E "FORTIFY|__PIE__|__PIC__|__CET__|__SSP|__FAST_MATH|FLT_EVAL_METHOD__" | sort
echo "[gcc cc1 options]"; gcc $F -c -x c /dev/null -o /dev/null -v 2>&1 | grep -E "/cc1 " | tr ' ' '\n' | grep -E "^-f|^-m|^-D|^-O" | tr '\n' ' '; echo
echo "[gcc configure]"; gcc -v 2>&1 | grep -o -E "\-\-enable-(default-pie|default-ssp|cet)[^ ]*" | sort -u
echo DONE
