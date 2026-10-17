#!/bin/bash
# X0 runbook step 71 (pre-freeze, WSL): toolchain pins for Table 2.1 (GCC, glibc, Ubuntu, Linux LLVM, CMake),
# effective flags for C (gcc -Q --help=common,optimizers and gcc -###) and D (clang -###) with each census
# file's exact command line and the source replaced by dummy.c, and the NON-Hearth smoke compiles
# (smoke_dispatch.c under the C and D command lines of quant_avx512.c and quant.c; reduce probe syntax-only).
# It compiles NO Hearth source. One thread. Needs step 51's configure trees (D:\mithril\x0\cfg\C-gcc, D-clang).
# Run (keepalive VM already up): wsl.exe -d Ubuntu -- bash /mnt/d/mithril/x0prep/x0/scripts/runbook/71_prefreeze_wsl.sh
exec 2>&1
export CUDA_VISIBLE_DEVICES=-1
mkdir -p /mnt/d/mithril/jobs/x0prep/tmp
export TMPDIR=/mnt/d/mithril/jobs/x0prep/tmp
W=/mnt/d/mithril/x0prep
S=$W/x0/scripts
F=$W/flags
O=$W/smoke
L=/mnt/d/mithril/tools/llvm-linux-23.1.3/bin
CM=/mnt/d/mithril/tools/cmake-4.4.3-linux/bin/cmake
CFG=/mnt/d/mithril/x0/cfg
mkdir -p $F $O/C $O/C-scalar $O/D $O/D-scalar
echo 'int x0_dummy;' > $W/dummy_wsl.c
echo "START $(date -Is)"
echo "==== Ubuntu / kernel"
cat /etc/os-release | grep -E '^(PRETTY_NAME|VERSION_ID|VERSION_CODENAME)='
uname -r
echo "==== GCC (C)"
gcc --version | head -1
readlink -f /usr/bin/gcc
gcc -v 2>&1 | tail -3
echo "dumpspecs sha256: $(gcc -dumpspecs | sha256sum | cut -d' ' -f1)"
CC1=$(gcc -print-prog-name=cc1); echo "cc1: $CC1"; sha256sum "$CC1"
sha256sum "$(readlink -f /usr/bin/gcc)"
dpkg-query -W -f='${Package} ${Version}\n' gcc-13 cpp-13 libgcc-13-dev libc6 libc6-dev linux-libc-dev binutils 2>&1
echo "==== LLVM for Linux (D)"
$L/clang --version | head -1
sha256sum "$(readlink -f $L/clang)" $L/llvm-objdump $L/llvm-readobj $L/llvm-dwarfdump
RD=$($L/clang -print-resource-dir); echo "resource-dir=$RD"
python3 -I -c "import hashlib,os,sys; r=sys.argv[1]; fs=sorted(os.path.relpath(os.path.join(d,f),r) for d,_,ff in os.walk(r) for f in ff); h=hashlib.sha256(); [h.update(f.encode()+b'\0'+hashlib.sha256(open(os.path.join(r,f),'rb').read()).digest()) for f in fs]; print('resource-dir include tree: %d files, sha256 %s' % (len(fs), h.hexdigest()))" "$RD/include"
echo "==== CMake (Linux)"
$CM --version | head -1
echo "==== C effective flags: gcc -Q --help=common,optimizers and gcc -### per census file (source -> dummy)"
for q in quant.c quant_avx2.c quant_avx512.c; do
  python3 -I $S/x0_flags.py replay $CFG/C-gcc/compile_commands.json --as $q --src $W/dummy_wsl.c --obj $W/dummy_wsl.o \
      --extra=-Q --extra=--help=common,optimizers --exec > $F/C-gcc.$q.gccq.txt 2>&1
  echo "C $q gccq rc=$? lines=$(wc -l < $F/C-gcc.$q.gccq.txt)"
  python3 -I $S/x0_flags.py replay $CFG/C-gcc/compile_commands.json --as $q --src $W/dummy_wsl.c --obj $W/dummy_wsl.o \
      --extra=-### --exec > $F/C-gcc.$q.cc1.txt 2>&1
  echo "C $q -### rc=$?"
  python3 -I $S/x0_flags.py replay $CFG/D-clang/compile_commands.json --as $q --src $W/dummy_wsl.c --obj $W/dummy_wsl.o \
      --extra=-### --exec > $F/D-clang.$q.cc1.txt 2>&1
  echo "D $q -### rc=$?"
done
cp $CFG/C-gcc/compile_commands.json $F/C-gcc.compile_commands.json
cp $CFG/D-clang/compile_commands.json $F/D-clang.compile_commands.json
echo "==== smoke (NOT Hearth): smoke_dispatch.c with the C and D lines of quant_avx512.c and quant.c"
for c in C D; do
  db=$CFG/C-gcc/compile_commands.json; [ $c = D ] && db=$CFG/D-clang/compile_commands.json
  python3 -I $S/x0_flags.py replay $db --as quant_avx512.c --src $S/smoke/smoke_dispatch.c --obj $O/$c/smoke_dispatch.o --exec
  echo "${c}_SMOKE_AVX512_RC=$?"
  python3 -I $S/x0_flags.py replay $db --as quant.c --src $S/smoke/smoke_dispatch.c --obj $O/$c-scalar/smoke_dispatch.o --exec
  echo "${c}_SMOKE_SCALAR_RC=$?"
  python3 -I $S/x0_flags.py replay $db --as quant_avx512.c --src $S/probes/reduce_probe.c --obj $W/dummy_wsl.o \
      --extra=-fsyntax-only --exec
  echo "${c}_PROBE_SYNTAX_RC=$?"
done
[ -e $W/dummy_wsl.o ] && echo "UNEXPECTED: dummy_wsl.o exists"
echo "END $(date -Is)"
