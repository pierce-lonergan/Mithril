@echo off
rem X0 runbook step 60: compile the SMOKE file (never Hearth) with the exact flags CMake gives
rem quant_avx512.c in configurations A (cl) and B (clang-cl); plus two compile probes.
rem Needs step 50 (compile_commands.json). Run:
rem   cmd /v:on /c D:\mithril\x0\scripts\runbook\60_smoke_win.cmd > D:\mithril\jobs\60_smoke_win.log 2>&1
setlocal enabledelayedexpansion
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\tmp mkdir D:\mithril\jobs\tmp
set TEMP=D:\mithril\jobs\tmp
set TMP=D:\mithril\jobs\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set PY=C:\Python313\python.exe -I
set S=D:\mithril\x0\scripts
set P=D:\mithril\x0\scripts\runbook\probes
set O=D:\mithril\x0\smoke
set C=D:\mithril\x0\cfg
if not exist %O%\probe mkdir %O%\probe
cd /d D:\mithril\x0
for %%K in (A-msvc B-clangcl) do (
  echo ==== %%K: smoke.c with the flags of quant_avx512.c
  %PY% %S%\x0_flags.py replay %C%\%%K\compile_commands.json --as quant_avx512.c --src %S%\smoke\smoke.c --obj %O%\%%K\smoke.obj --exec
  echo %%K_SMOKE_RC=!ERRORLEVEL!
  echo ==== %%K: VNNI probe ^(_mm512_dpbusd_epi32^) with the flags of quant_avx512.c
  %PY% %S%\x0_flags.py replay %C%\%%K\compile_commands.json --as quant_avx512.c --src %P%\vnni_probe.c --obj %O%\probe\vnni_%%K.obj --exec
  echo %%K_VNNI_RC=!ERRORLEVEL!
  echo ==== %%K: C11 atomics probe with the flags of quant.c
  %PY% %S%\x0_flags.py replay %C%\%%K\compile_commands.json --as quant.c --src %P%\atomic_probe.c --obj %O%\probe\atomic_%%K.obj --exec
  echo %%K_ATOMIC_RC=!ERRORLEVEL!
)
echo ==== clang-cl /arch:AVX512 plus -mavx512vnni (possible fix for B, not Hearth's flags)
D:\mithril\tools\llvm-win-23.1.3\bin\clang-cl.exe /nologo /c /O2 /fp:precise /arch:AVX512 -mavx512vnni %P%\vnni_probe.c /Fo%O%\probe\vnni_B_plus_mavx512vnni.obj
echo VNNI_B_PLUS_RC=!ERRORLEVEL!
echo ==== cl without /experimental:c11atomics (expected to fail)
cl.exe /nologo /c /O2 /std:c11 %P%\atomic_probe.c /Fo%O%\probe\atomic_A_noexp.obj
echo ATOMIC_A_NOEXP_RC=!ERRORLEVEL!
echo DONE
