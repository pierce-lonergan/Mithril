#!/bin/bash
exec >/mnt/d/mithril/jobs/xedbuild.log 2>&1
export CUDA_VISIBLE_DEVICES=-1
echo $$ > /mnt/d/mithril/jobs/xedbuild.pid
echo "START $(date -Is)"
cd /mnt/d/mithril/src/xed || exit 1
TAG=v2026.08.23
python3 ./mfile.py -j 8 --static --build-dir=/mnt/d/mithril/src/xed-build-static --install-dir=/mnt/d/mithril/tools/xed-$TAG install examples
rc1=$?
echo "STATIC_END $(date -Is) rc=$rc1"
python3 ./mfile.py -j 8 --shared --build-dir=/mnt/d/mithril/src/xed-build-shared --install-dir=/mnt/d/mithril/tools/xed-$TAG-shared install examples
rc2=$?
echo "SHARED_END $(date -Is) rc=$rc2"
echo "$rc1 $rc2" > /mnt/d/mithril/jobs/xedbuild.rc
