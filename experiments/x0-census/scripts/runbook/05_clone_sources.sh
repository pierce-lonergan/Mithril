#!/bin/bash
exec 2>&1
set -u
export CUDA_VISIBLE_DEVICES=-1
cd /mnt/d/mithril/src || exit 1
git -c advice.detachedHead=false clone --quiet --branch v2026.08.23 --depth 1 https://github.com/intelxed/xed.git xed && echo XED_CLONED
git -c advice.detachedHead=false clone --quiet --branch v2026.08.23 --depth 1 https://github.com/intelxed/mbuild.git mbuild && echo MBUILD_CLONED
git clone --quiet https://github.com/pierce-lonergan/hearth.git hearth && echo HEARTH_CLONED
cd /mnt/d/mithril/src/hearth && git -c advice.detachedHead=false checkout --quiet b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220 && echo HEARTH_CHECKED_OUT
for r in xed mbuild hearth; do cd /mnt/d/mithril/src/$r; echo "$r HEAD=$(git rev-parse HEAD) describe=$(git describe --tags --always 2>/dev/null) status_lines=$(git status --porcelain | wc -l)"; done
cd /mnt/d/mithril/src/hearth && git log -1 --format='%H %cI %s' && ls
