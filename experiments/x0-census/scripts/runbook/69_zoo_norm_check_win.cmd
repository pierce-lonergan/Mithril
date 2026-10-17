@echo off
rem x0prep: compile the NON-Hearth instruction zoo with clang-cl and check objdump_norm.csv on it and on the
rem four smoke objects. 1 thread. Logs under D:\mithril\jobs\x0prep.
setlocal enabledelayedexpansion
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\x0prep\tmp mkdir D:\mithril\jobs\x0prep\tmp
set TEMP=D:\mithril\jobs\x0prep\tmp
set TMP=D:\mithril\jobs\x0prep\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set L=D:\mithril\tools\llvm-win-23.1.3\bin
set XW=D:\mithril\tools\xed-v2026.08.23-win\bin\xed.exe
set S=D:\mithril\x0prep\x0\scripts
set Z=D:\mithril\x0prep\zoo
if not exist %Z% mkdir %Z%
cd /d %Z%
echo START %DATE% %TIME%
for /L %%I in (1,1,8) do (
  C:\Python313\python.exe -I %S%\smoke\gen_zoo.py --xml D:\mithril\x0prep\x86-intel.xml --outdir %Z% --exclude %Z%\exclude.txt
  %L%\clang-cl.exe /nologo /c /O1 -mavx512f -mavx512bw -mavx512dq -mavx512vl -mavx512cd -mavx512vnni -mavx512bf16 -mavx2 -mfma -mf16c -mbmi -mbmi2 -mlzcnt -mpopcnt -Wno-everything -ferror-limit=0 zoo_avx.c /Fozoo_avx.obj > zoo_avx.log 2>&1
  set RA=!ERRORLEVEL!
  %L%\clang-cl.exe /nologo /c /O1 -msse4.2 -mpopcnt -Wno-everything -ferror-limit=0 zoo_sse.c /Fozoo_sse.obj > zoo_sse.log 2>&1
  set RS=!ERRORLEVEL!
  echo ITER %%I ZOO_AVX_RC=!RA! ZOO_SSE_RC=!RS!
  if "!RA!!RS!"=="00" goto compiled
  C:\Python313\python.exe -I D:\mithril\x0prep\zoo_fix.py %Z%
)
:compiled
%L%\clang-cl.exe /nologo /c /O1 -mavx2 -Wno-everything zoo_asm.c /Fozoo_asm.obj > zoo_asm.log 2>&1
echo ZOO_ASM_RC=!ERRORLEVEL!
echo COMPILED %DATE% %TIME%
C:\Python313\python.exe -I %S%\smoke\norm_check.py --xed %XW% --objdump %L%\llvm-objdump.exe -o %Z%\norm_zoo.json %Z%\zoo_avx.obj %Z%\zoo_sse.obj %Z%\zoo_asm.obj D:\mithril\x0\smoke\A-msvc\smoke.obj D:\mithril\x0\smoke\B-clangcl\smoke.obj D:\mithril\x0\smoke\C-gcc\smoke.o D:\mithril\x0\smoke\D-clang\smoke.o
echo NORM_RC=!ERRORLEVEL!
echo END %DATE% %TIME%
