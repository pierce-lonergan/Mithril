#!/bin/bash
exec >/mnt/d/mithril/jobs/x_cmake.log 2>&1
export CUDA_VISIBLE_DEVICES=-1
echo "START $(date -Is)"
D=/mnt/d/mithril/tools/cmake-4.4.3-linux
mkdir -p "$D"
tar -xzf /mnt/d/mithril/tools/dl/cmake-4.4.3-linux-x86_64.tar.gz --strip-components=1 -C "$D"
rc=$?
"$D/bin/cmake" --version
echo "END $(date -Is) rc=$rc"
echo $rc > /mnt/d/mithril/jobs/x_cmake.rc
