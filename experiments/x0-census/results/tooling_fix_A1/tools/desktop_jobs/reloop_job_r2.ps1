# x0fix track (X0-A1), 2026-10-23: a1_reloop.py (read-only on RUN) with each given x0_loops.py, Windows configurations
# with C:\Python313, WSL configurations inside the running keepalive VM. One process at a time; no GPU.
# r2 (revision after the review of 2026-10-23): the a1_reloop.py path is a parameter (-T), and the WSL TMPDIR follows -J.
param([string]$Run, [string]$Out, [string]$Tag, [string]$WinCfgs = '', [string]$WslCfgs = '',
      [string]$Scripts = 'old=D:\mithril\x0fixA1\cmp\old\x0_loops.py;new=D:\mithril\x0fixA1\cmp\new\x0_loops.py',
      [string]$J = 'D:\mithril\jobs\x0fixA1', [string]$T = 'D:\mithril\x0fixA1\cmp\tools\a1_reloop.py')
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
New-Item -ItemType Directory -Force "$J\tmp" | Out-Null
$env:TEMP = "$J\tmp"; $env:TMP = "$J\tmp"
function W([string]$p) { '/mnt/' + $p.Substring(0,1).ToLower() + $p.Substring(2).Replace([char]92, [char]47) }
"START $(Get-Date -Format o)" | Out-File -Append "$J\${Tag}_progress.txt"
foreach ($pair in $Scripts.Split(';')) {
  $name, $script = $pair.Split('=')
  foreach ($c in ($WinCfgs.Split(',') | Where-Object { $_ })) {
    & C:\Python313\python.exe -I $T $Run $c $script "$Out\$name" *> "$J\${Tag}_${name}_$c.log"
    "$name $c rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Append "$J\${Tag}_progress.txt"
  }
  foreach ($c in ($WslCfgs.Split(',') | Where-Object { $_ })) {
    wsl.exe -d Ubuntu -- env CUDA_VISIBLE_DEVICES=-1 TMPDIR=$(W "$J\tmp") python3 -I (W $T) (W $Run) $c (W $script) (W "$Out\$name") *> "$J\${Tag}_${name}_$c.log"
    "$name $c rc=$LASTEXITCODE $(Get-Date -Format o)" | Out-File -Append "$J\${Tag}_progress.txt"
  }
}
"DONE $(Get-Date -Format o)" | Out-File -Append "$J\${Tag}_progress.txt"
