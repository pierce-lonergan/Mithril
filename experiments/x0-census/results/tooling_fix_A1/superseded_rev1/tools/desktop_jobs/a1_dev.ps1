# x0fix track (X0-A1), 2026-10-23: the NON-Hearth reproduction a1_escape.c in replay mode under A, A-ninja, B-cmake
# (Windows) and C, D (WSL, inside the keepalive VM). One job at a time; one compiler at a time; XED -j 2; no GPU.
# -NoInit keeps an existing run (to add configurations); -Win / -Wsl choose the configurations.
param([string]$Tree = 'D:\mithril\x0fixA1\tree_dev\x0-census', [string]$Run = 'D:\mithril\x0fixA1\runs\A1dev',
      [string]$J = 'D:\mithril\jobs\x0fixA1', [string]$Tag = 'A1dev', [string]$Win = 'A,A-ninja,B-cmake',
      [string]$Wsl = 'C,D', [switch]$NoInit)
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
New-Item -ItemType Directory -Force "$J\tmp" | Out-Null
$env:TEMP = "$J\tmp"; $env:TMP = "$J\tmp"
$PY = 'C:\Python313\python.exe'
$X = "$Tree\scripts"
$env:X0 = $Tree
function WinPath2Wsl([string]$p) { '/mnt/' + $p.Substring(0,1).ToLower() + $p.Substring(2).Replace([char]92, [char]47) }
$X0W = WinPath2Wsl $Tree
$K = "$X\runbook\80_census_win.cmd"
$WS = "$X0W/scripts/runbook/81_census_wsl.sh"
$RW = WinPath2Wsl $Run
$SET = "$X\smoke\a1\a1_set.json"; $SETW = WinPath2Wsl $SET
"START $(Get-Date -Format o) X0W=$X0W WS=$WS RW=$RW SETW=$SETW" | Out-File -Append "$J\${Tag}_progress.txt"
if (-not $NoInit) {
  if (Test-Path $Run) { Remove-Item -Recurse -Force $Run }
  & $PY -I "$X\x0_driver.py" init --run $Run --kind smoke --source "$X\smoke\a1" --profile regression *> "$J\${Tag}_init.log"
}
foreach ($c in ($Win.Split(',') | Where-Object { $_ })) {
  cmd /v:on /c "$K $Run $c replay --set $SET" *> "$J\${Tag}_$c.log"
  "$c done $(Get-Date -Format o)" | Out-File -Append "$J\${Tag}_progress.txt"
}
foreach ($c in ($Wsl.Split(',') | Where-Object { $_ })) {
  wsl.exe -d Ubuntu -- env X0=$X0W bash $WS $RW $c replay --set $SETW *> "$J\${Tag}_$c.log"
  "$c done $(Get-Date -Format o)" | Out-File -Append "$J\${Tag}_progress.txt"
}
"DONE $(Get-Date -Format o)" | Out-File -Append "$J\${Tag}_progress.txt"
