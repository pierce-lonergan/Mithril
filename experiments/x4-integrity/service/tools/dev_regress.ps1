# X4 dev regression (X4 pilot track, 2026-10-23): the round-3 x4svc run table and x4_devcheck.py,
# re-run on the current build after the pilot-readiness changes. Dev probes only (non-gate data),
# inside the track's 3-LP budget (LPs 26-28): the orchestrator is confined to LP 26 and every run's
# job mask is a subset of LPs 27-28 (the round-3 table ran some probes unpinned).
$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:TEMP = 'D:\mithril\x4c\tmp'; $env:TMP = 'D:\mithril\x4c\tmp'
$svc = 'D:\mithril\x4c\bin\x4svc.exe'
$h = 'D:\mithril\x4c\bin\x4harness.exe'
$sc = 'D:\mithril\x4c\scratch'
$cases = @(
  @('dev_sleep_long', @('--affinity','0x10000000'), 'Accept'),
  @('dev_init_precompute', @('--affinity','0x10000000'), 'pre_start_wall'),
  @('dev_forge_frames', @('--affinity','0x10000000'), 'Accept'),
  @('dev_forge_frames', @('--affinity','0x10000000','--param','1500'), 'pre_start_wall'),
  @('dev_par_exited', @('--affinity','0x18000000'), 'window_cores'),
  @('dev_par_exited', @('--affinity','0x18000000','--threads','2'), 'Accept'),
  @('dev_par_exited', @('--affinity','0x10000000'), 'Accept'),
  @('dev_handle_canary', @('--affinity','0x10000000'), 'Accept'),
  @('dev_handle_canary', @('--affinity','0x10000000','--dev-canary'), 'Accept'),
  @('dev_guard_lift', @('--affinity','0x10000000'), 'outside_extent_oop'),
  @('dev_early_stop', @('--affinity','0x10000000'), 'protocol'),
  @('dev_main_ftz', @('--affinity','0x10000000'), 'mxcsr_harness'),
  @('dev_rc', @('--affinity','0x10000000'), 'workload_rc'),
  @('dev_aff_narrow', @('--affinity','0x18000000'), 'affinity'),
  @('dev_leak_registered', @('--affinity','0x18000000'), 'registered_unparked'),
  @('dev_mxcsr_worker', @('--affinity','0x18000000'), 'mxcsr_threads'),
  @('dev_mxcsr_joined', @('--affinity','0x18000000'), 'mxcsr_exit'),
  @('dev_t0_poke', @('--affinity','0x10000000'), 'clock_bracket'),
  @('dev_partial_output', @('--affinity','0x10000000'), 'poison_residual'),
  @('dev_overflow', @('--affinity','0x10000000'), 'FAULT'),
  @('dev_write', @('--affinity','0x10000000','--golden','0000000000000000000000000000000000000000000000000000000000000000'), 'golden_hash'),
  @('dev_write', @('--affinity','0x10000000'), 'bracket_too_short')
)
$pass = 0; $n = 0
foreach ($c in $cases) {
  $n++
  $args2 = @('run','--harness',$h,'--workload',$c[0],'--scratch',$sc) + $c[1]
  if (-not ($c[1] -contains '--golden')) { $args2 += '--dev-self-golden' }
  $p = Start-Process -FilePath $svc -ArgumentList $args2 -NoNewWindow -PassThru -RedirectStandardOutput "$sc\..\tmp\reg_out.txt" -RedirectStandardError "$sc\..\tmp\reg_err.txt"
  try { $p.ProcessorAffinity = [IntPtr]0x4000000 } catch {}
  $p.WaitForExit()
  $out = (Get-Content "$sc\..\tmp\reg_out.txt" -Raw) + (Get-Content "$sc\..\tmp\reg_err.txt" -Raw)
  $verdict = ($out -split "`n" | Where-Object { $_ -match '^verdict' }) -join ' '
  $checks = ($out -split "`n" | Where-Object { $_ -match '^\s+\[' } | ForEach-Object { ($_ -replace '^\s+\[[^\]]+\]\s+','') -replace ':.*$','' }) -join ','
  $ok = $out -match [regex]::Escape($c[2])
  if ($ok) { $pass++ }
  '{0,-4} {1,-22} {2,-60} expect {3,-20} got {4} [{5}]' -f ($(if ($ok) {'ok'} else {'MISS'})), $c[0], ($c[1] -join ' '), $c[2], $verdict.Trim(), $checks
}
"run table: $pass of $n as expected"
'==== x4_devcheck.py (harness-only signals), confined to LPs 26-28'
$p = Start-Process -FilePath 'C:\Python313\python.exe' -ArgumentList @('-I','D:\mithril\x4c\src\service\tools\x4_devcheck.py',$h) -NoNewWindow -PassThru -RedirectStandardOutput "$sc\..\tmp\devcheck_out.txt" -RedirectStandardError "$sc\..\tmp\devcheck_err.txt"
try { $p.ProcessorAffinity = [IntPtr]0x1C000000 } catch {}
$p.WaitForExit()
Get-Content "$sc\..\tmp\devcheck_out.txt" | Select-Object -Last 30
Get-Content "$sc\..\tmp\devcheck_err.txt" | Select-Object -Last 5
"devcheck exit $($p.ExitCode)"
