# run_probe.ps1 -- boot the probe image in the Bochs 3.1 MSVC build and capture the port-0xE9 output.
# Usage (desktop): powershell -File run_probe.ps1 -Image boot_0.img -Model sapphire_rapids -Tag t0 [-TimeoutS 600]
param([string]$Image, [string]$Model = 'sapphire_rapids', [string]$Tag = 'run', [int]$TimeoutS = 600)
$env:CUDA_VISIBLE_DEVICES = '-1'
$B = 'D:\mithril\src\bochs-3.1-msvc\bochs-3.1\obj-release\bochs.exe'
$W = 'D:\mithril\x2\bochs'
$H = 'D:\mithril\x2\src\harness\bochs'
Set-Location $W
$rc = Join-Path $W "bochsrc_$Tag.txt"
(Get-Content "$H\bochsrc.txt") -creplace 'IMAGE', ($W + '\' + $Image).Replace('\', '/') -creplace 'MODEL', $Model `
    -creplace 'LOGFILE', ($W + "\bochs_$Tag.log").Replace('\', '/') | Set-Content -Encoding ascii $rc
"`r`n`r`n`r`n" | Set-Content -Encoding ascii (Join-Path $W 'enter.txt')
$sw = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process -FilePath $B -ArgumentList @('-q', '-f', $rc, '-rc', "$H\dbgcmds.txt") -NoNewWindow -PassThru `
    -RedirectStandardInput (Join-Path $W 'enter.txt') -RedirectStandardOutput (Join-Path $W "out_$Tag.txt") `
    -RedirectStandardError (Join-Path $W "err_$Tag.txt")
$done = $p.WaitForExit($TimeoutS * 1000)
if (-not $done) { $p.Kill(); "TIMEOUT after $TimeoutS s" }
$sw.Stop()
"tag=$Tag image=$Image model=$Model seconds=$($sw.Elapsed.TotalSeconds) exit=$($p.ExitCode)"
"--- stdout"; Get-Content (Join-Path $W "out_$Tag.txt") | Select-String -Pattern '^T0|X2 BOCHS|LOOP|DONE|E$' | ForEach-Object { $_.Line }
"--- stderr tail"; Get-Content (Join-Path $W "err_$Tag.txt") -Tail 8
"--- log (panic/error/ips)"; Get-Content (Join-Path $W "bochs_$Tag.log") | Select-String -Pattern 'PANIC|FATAL|ERROR|ips|CPUID|cpu model|Shutdown' | Select-Object -First 20 | ForEach-Object { $_.Line }
