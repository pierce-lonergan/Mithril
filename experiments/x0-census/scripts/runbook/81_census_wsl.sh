#!/bin/bash
# X0 runbook step 81 (CENSUS, WSL; only after the record is FROZEN): one configuration of the census in WSL.
#   81_census_wsl.sh RUN CFG [MODE] [more x0_driver.py config arguments]
#   CFG = C | D (census mode), P.C | P.D (MODE probe, add --from-config C|D), or a configuration of a NON-Hearth smoke run.
# RUN is a /mnt/d/... path. X0 = experiments/x0-census of the tree to use, as a /mnt/d/... path; required (x0final
# revision: no default). For the census: the clean checkout of the freeze commit.
# Run inside the existing keepalive VM: wsl.exe -d Ubuntu -- bash $X0/scripts/runbook/81_census_wsl.sh RUN CFG
exec 2>&1
export CUDA_VISIBLE_DEVICES=-1
if [ -z "$X0" ]; then echo "REFUSED: set X0 to experiments/x0-census of the tree to use"; exit 2; fi
mkdir -p /mnt/d/mithril/jobs/x0final/tmp
export TMPDIR=/mnt/d/mithril/jobs/x0final/tmp
RUN=$1; CFG=$2; MODE=${3:-census}
shift 3 2>/dev/null || shift $#
echo "START $(date -Is) RUN=$RUN CFG=$CFG MODE=$MODE MORE=$*"
python3 -I "$X0/scripts/x0_driver.py" config --run "$RUN" --config "$CFG" --mode "$MODE" --tools "$X0/scripts/runbook/census_tools_wsl.json" "$@"
echo "CONFIG_RC=$?"
echo "END $(date -Is)"
