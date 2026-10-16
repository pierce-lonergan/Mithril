#!/bin/bash
exec >/mnt/d/mithril/jobs/x_linux.log 2>&1
export CUDA_VISIBLE_DEVICES=-1
echo "START $(date -Is)"
echo $$ > /mnt/d/mithril/jobs/x_linux.pid
D=/mnt/d/mithril/tools/llvm-linux-23.1.3
mkdir -p "$D"
xz -T8 -dc /mnt/d/mithril/tools/dl/LLVM-23.1.3-Linux-X64.tar.xz | tar -x --strip-components=1 -C "$D"
rc=$?
echo "END $(date -Is) rc=$rc pipestatus=${PIPESTATUS[*]}"
echo $rc > /mnt/d/mithril/jobs/x_linux.rc
