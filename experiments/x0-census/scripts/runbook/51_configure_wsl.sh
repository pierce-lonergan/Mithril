#!/bin/bash
# X0 runbook step 51: dry-configure Hearth (Release) for (C) GCC 13.3 and (D) Clang 23.1.3 in WSL, Unix Makefiles.
# Configure only: CMake compiles its own try-compile probes, never Hearth sources.
# Run: wsl.exe -d Ubuntu -- bash /mnt/d/mithril/x0/scripts/runbook/51_configure_wsl.sh > D:\mithril\jobs\51_configure_wsl.log
exec 2>&1
export CUDA_VISIBLE_DEVICES=-1
mkdir -p /mnt/d/mithril/jobs/tmp
export TMPDIR=/mnt/d/mithril/jobs/tmp
CM=/mnt/d/mithril/tools/cmake-4.4.3-linux/bin/cmake
H=/mnt/d/mithril/src/hearth
B=/mnt/d/mithril/x0/cfg
echo "START $(date -Is)"
$CM --version | head -1
command -v make && make --version | head -1
git -C $H rev-parse HEAD
rm -rf $B/C-gcc $B/D-clang
$CM -S $H -B $B/C-gcc -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=/usr/bin/gcc
echo "C_RC=$?"
$CM -S $H -B $B/D-clang -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=/mnt/d/mithril/tools/llvm-linux-23.1.3/bin/clang
echo "D_RC=$?"
echo "END $(date -Is)"
