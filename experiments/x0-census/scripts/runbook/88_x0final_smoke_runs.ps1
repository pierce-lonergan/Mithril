# X0 runbook step 88 (x0final, pre-freeze, desktop; NON-Hearth inputs only): the census driver end to end on
#   R2: the census MOCK (scripts/smoke/mock, Hearth's table shape and CMake flag logic, NOT Hearth; rewritten by the
#       x0final revision of 2026-10-17 without any Hearth line, record §2) in CENSUS mode: configure, two clean builds,
#       twin, effective flags, extract, decode, attribution, loops for A (Visual Studio generator, MSBuild), A-ninja,
#       B-cmake, C, D; arm P (P.<CFG>, the reduce probe with each configuration's quant_avx512.c line); the B-proxy arm
#       (runbook/bproxy_set.json on the mock's files); census.json, judge.py, and
#       judge_regression.py --synthetic-rederivation;
#   R1: the regression set (smoke/regression_set.json: smoke_dispatch.c, rv_tricky.c, rv_tricky2.c under the frozen
#       quant_avx512.c and quant.c lines of A (A-ninja capture), A-ninja, B-cmake, C, D) in REPLAY mode, arm P,
#       census.json, judge.py, judge_regression.py --set --synthetic-rederivation, check_regression_run.py.
# Prerequisite: step 86 (the mock's configure-only captures, made from the same tree) in $F. Run one job at a time:
#   powershell -NoProfile -ExecutionPolicy Bypass -File 88_x0final_smoke_runs.ps1 -X <tree>\scripts -Runs <dir> -F <dir> -J <dir>
# The x0final revision (2026-10-17): steps 79-82 no longer default X0, so this script sets X0 from -X (Windows) and
# passes it to WSL; -Only R1 or -Only R2 runs one of the two runs. Never inside a quiet window (23:00-07:00 PT).
# Threads: one compiler or MSBuild node at a time; XED -j 2; no GPU (CUDA_VISIBLE_DEVICES=-1).
param(
  [string]$X = 'D:\mithril\x0final\x0-census\scripts',
  [string]$Runs = 'D:\mithril\x0final\runs',
  [string]$F = 'D:\mithril\x0final\runs\mockfrozen',
  [string]$J = 'D:\mithril\jobs\x0final',
  [string]$Only = ''
)
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$PY = 'C:\Python313\python.exe'
$K = "$X\runbook\80_census_win.cmd"
function WinPath2Wsl([string]$p) { '/mnt/' + $p.Substring(0,1).ToLower() + ($p.Substring(2) -replace '\\','/') }
$env:X0 = Split-Path -Parent $X
$X0W = WinPath2Wsl $env:X0
$W = "$X0W/scripts/runbook/81_census_wsl.sh"
New-Item -ItemType Directory -Force $J | Out-Null
New-Item -ItemType Directory -Force $Runs | Out-Null

# ---- R2: the mock in census mode
if ($Only -ne 'R1') {
  $R = "$Runs\R2mock"; $RW = WinPath2Wsl $R
  if (Test-Path $R) { Remove-Item -Recurse -Force $R }
  & $PY -I "$X\x0_driver.py" init --run $R --kind smoke --source "$X\smoke\mock" --mock --profile hearth *> "$J\R2_init.log"
  cmd /v:on /c "$K $R A census --target x0mock_core --design-time $F\A-vs.design_time_cl_lines.txt" *> "$J\R2_A.log"
  foreach ($c in @('A-ninja','B-cmake')) { cmd /v:on /c "$K $R $c census --target x0mock_core --frozen-db $F\$c.compile_commands.json" *> "$J\R2_$c.log" }
  $FW = WinPath2Wsl $F
  wsl.exe -d Ubuntu -- env X0=$X0W bash $W $RW C census --target x0mock_core --frozen-db "$FW/C-gcc.compile_commands.json" *> "$J\R2_C.log"
  wsl.exe -d Ubuntu -- env X0=$X0W bash $W $RW D census --target x0mock_core --frozen-db "$FW/D-clang.compile_commands.json" *> "$J\R2_D.log"
  foreach ($c in @('A','A-ninja','B-cmake')) { cmd /v:on /c "$K $R P.$c probe --from-config $c --from-file quant_avx512.c" *> "$J\R2_P.$c.log" }
  foreach ($c in @('C','D')) { wsl.exe -d Ubuntu -- env X0=$X0W bash $W $RW "P.$c" probe --from-config $c --from-file quant_avx512.c *> "$J\R2_P.$c.log" }
  cmd /v:on /c "$K $R B-proxy replay --set $X\runbook\bproxy_set.json" *> "$J\R2_B-proxy.log"
  cmd /v:on /c "$X\runbook\82_census_assemble.cmd $R" *> "$J\R2_assemble.log"
  & $PY -I "$X\smoke\judge_regression.py" "$R\census.json" -o "$R\verdict_synthetic_rederivation.json" --synthetic-rederivation *> "$J\R2_judge_synth.log"
  & $PY -I "$X\runbook\summarize_x0final.py" $R "$R\summary.json" *> "$J\R2_summary.log"
}

# ---- R1: the regression set in replay mode
if ($Only -ne 'R2') {
  $R = "$Runs\R1reg"; $RW = WinPath2Wsl $R
  $SET = "$X\smoke\regression_set.json"; $SETW = WinPath2Wsl $SET
  if (Test-Path $R) { Remove-Item -Recurse -Force $R }
  & $PY -I "$X\x0_driver.py" init --run $R --kind smoke --source "$X\smoke" --profile regression *> "$J\R1_init.log"
  foreach ($c in @('A','A-ninja','B-cmake')) { cmd /v:on /c "$K $R $c replay --set $SET" *> "$J\R1_$c.log" }
  foreach ($c in @('C','D')) { wsl.exe -d Ubuntu -- env X0=$X0W bash $W $RW $c replay --set $SETW *> "$J\R1_$c.log" }
  foreach ($c in @('A','A-ninja','B-cmake')) { cmd /v:on /c "$K $R P.$c probe --from-config $c --from-file smoke_dispatch.c" *> "$J\R1_P.$c.log" }
  foreach ($c in @('C','D')) { wsl.exe -d Ubuntu -- env X0=$X0W bash $W $RW "P.$c" probe --from-config $c --from-file smoke_dispatch.c *> "$J\R1_P.$c.log" }
  cmd /v:on /c "$X\runbook\82_census_assemble.cmd $R --qualify-tables" *> "$J\R1_assemble.log"
  & $PY -I "$X\smoke\judge_regression.py" "$R\census.json" -o "$R\verdict_regression_profile.json" --set $SET --synthetic-rederivation *> "$J\R1_judge_regprofile.log"
  & $PY -I "$X\smoke\check_regression_run.py" $R "$X\smoke\tricky_expect.json" *> "$J\R1_check.log"
  & $PY -I "$X\runbook\summarize_x0final.py" $R "$R\summary.json" *> "$J\R1_summary.log"
}
"DONE $(Get-Date -Format o)" | Out-File "$J\88_DONE.txt"
