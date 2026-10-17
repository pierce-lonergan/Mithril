#!/bin/bash
# X0 runbook step 86 (x0final, pre-freeze, WSL; NOT Hearth): configure-only captures of the census MOCK for C and D
# (Unix Makefiles, compile_commands.json), as step 51 did for Hearth.   86_mock_prefreeze_wsl.sh OUTDIR
exec 2>&1
export CUDA_VISIBLE_DEVICES=-1
X0=${X0:-/mnt/d/mithril/x0final/x0-census}
export TMPDIR=/mnt/d/mithril/jobs/x0final/tmp
CM=/mnt/d/mithril/tools/cmake-4.4.3-linux/bin/cmake
M=$X0/scripts/smoke/mock
O=$1
rm -rf "$O/C-gcc" "$O/D-clang"
$CM -S $M -B "$O/C-gcc" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=/usr/bin/gcc
echo "C_CONFIGURE_RC=$?"
$CM -S $M -B "$O/D-clang" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=/mnt/d/mithril/tools/llvm-linux-23.1.3/bin/clang
echo "D_CONFIGURE_RC=$?"
cp "$O/C-gcc/compile_commands.json" "$O/C-gcc.compile_commands.json"
cp "$O/D-clang/compile_commands.json" "$O/D-clang.compile_commands.json"
find "$O/C-gcc" "$O/D-clang" -name '*.o' | grep -v CMakeFiles/4 || true
