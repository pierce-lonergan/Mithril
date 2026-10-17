@echo off
rem X0 runbook step 70 (pre-freeze, Windows): toolchain pins for Table 2.1, configure-only flag captures for
rem A (Visual Studio generator; design-time GetClCommandLines, no compile), A-ninja and B-cmake (Ninja),
rem clang-cl -### effective flags for B-cmake and B-proxy, and the NON-Hearth smoke compiles
rem (smoke_dispatch.c under the A and B command lines of quant_avx512.c and quant.c; reduce probe syntax-only).
rem It compiles NO Hearth source: every compiler invocation names smoke_dispatch.c, reduce_probe.c or
rem dummy.c, and `-###` / `/Zs` invocations do not generate code. One thread throughout.
rem Run: cmd /v:on /c D:\mithril\x0prep\x0\scripts\runbook\70_prefreeze_win.cmd > D:\mithril\jobs\x0prep\70_prefreeze_win.log 2>&1
setlocal enabledelayedexpansion
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\x0prep\tmp mkdir D:\mithril\jobs\x0prep\tmp
set TEMP=D:\mithril\jobs\x0prep\tmp
set TMP=D:\mithril\jobs\x0prep\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set PY=C:\Python313\python.exe -I
set L=D:\mithril\tools\llvm-win-23.1.3\bin
set XW=D:\mithril\tools\xed-v2026.08.23-win\bin\xed.exe
set CMAKE="C:\Program Files\CMake\bin\cmake.exe"
set NINJA=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe
set H=D:\mithril\src\hearth
set W=D:\mithril\x0prep
set S=%W%\x0\scripts
set C=%W%\cfg
set O=%W%\smoke
set F=%W%\flags
for %%D in (%C% %O% %F% %O%\A %O%\B %O%\A-scalar %O%\B-scalar) do if not exist %%D mkdir %%D
echo int x0_dummy;> %W%\dummy.c
echo START %DATE% %TIME%
echo ==== Hearth tree
git -C %H% rev-parse HEAD
git -C %H% status --porcelain --ignored
echo ==== MSVC (A, A-ninja, H-A)
echo VCToolsVersion=%VCToolsVersion% WindowsSDKVersion=%WindowsSDKVersion% UCRTVersion=%UCRTVersion% VCToolsInstallDir=%VCToolsInstallDir%
cl.exe 2>&1 | findstr /i "Version"
for %%B in (cl.exe c1.dll c2.dll) do certutil -hashfile "%VCToolsInstallDir%bin\Hostx64\x64\%%B" SHA256 | findstr /v /i "certutil"
msbuild -version -nologo
echo ==== LLVM for Windows (B-cmake, B-proxy)
%L%\clang-cl.exe --version
%L%\clang.exe --version
for %%B in (clang-cl.exe clang.exe llvm-objdump.exe llvm-readobj.exe llvm-dwarfdump.exe) do certutil -hashfile %L%\%%B SHA256 | findstr /v /i "certutil"
for /f "delims=" %%R in ('%L%\clang.exe -print-resource-dir') do set RDIR=%%R
echo resource-dir=!RDIR!
%PY% -c "import hashlib,os,sys; r=sys.argv[1]; fs=sorted(os.path.relpath(os.path.join(d,f),r).replace(os.sep,'/') for d,_,ff in os.walk(r) for f in ff); h=hashlib.sha256(); [h.update(f.encode()+b'\0'+hashlib.sha256(open(os.path.join(r,f),'rb').read()).digest()) for f in fs]; print('resource-dir include tree: %%d files, sha256 %%s' %% (len(fs), h.hexdigest()))" "!RDIR!\include"
echo ==== CMake, Ninja, XED
%CMAKE% --version
"%NINJA%" --version
certutil -hashfile "%NINJA%" SHA256 | findstr /v /i "certutil"
%XW% -version
certutil -hashfile %XW% SHA256 | findstr /v /i "certutil"
echo ==== configure only: A (Visual Studio 17 2022, -A x64)
if exist %C%\A-vs rmdir /s /q %C%\A-vs
%CMAKE% -S %H% -B %C%\A-vs -G "Visual Studio 17 2022" -A x64
echo A_VS_CONFIGURE_RC=!ERRORLEVEL!
echo ==== A: design-time ClCompile command lines (target GetClCommandLines; no compilation)
msbuild %C%\A-vs\hearth_core.vcxproj -t:GetClCommandLines -p:Configuration=Release -p:Platform=x64 -p:DesignTimeBuild=true -p:BuildProjectReferences=false -m:1 -nologo -v:quiet -getTargetResult:GetClCommandLines > %F%\A-vs.GetClCommandLines.json
echo A_GETCL_RC=!ERRORLEVEL!
echo objects under the A-vs tree after GetClCommandLines (expect none):
dir /s /b %C%\A-vs\*.obj 2>nul
echo ==== configure only: A-ninja and B-cmake (Ninja, Release, compile_commands.json)
for %%K in (A-ninja B-cmake) do if exist %C%\%%K rmdir /s /q %C%\%%K
%CMAKE% -S %H% -B %C%\A-ninja -G Ninja -DCMAKE_MAKE_PROGRAM="%NINJA%" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=cl
echo A_NINJA_CONFIGURE_RC=!ERRORLEVEL!
%CMAKE% -S %H% -B %C%\B-cmake -G Ninja -DCMAKE_MAKE_PROGRAM="%NINJA%" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=%L:\=/%/clang-cl.exe
echo B_CMAKE_CONFIGURE_RC=!ERRORLEVEL!
copy /y %C%\A-ninja\compile_commands.json %F%\A-ninja.compile_commands.json >nul
copy /y %C%\B-cmake\compile_commands.json %F%\B-cmake.compile_commands.json >nul
echo objects under the Ninja trees (expect only CMake's own probes):
dir /s /b %C%\A-ninja\*.obj %C%\B-cmake\*.obj 2>nul
echo ==== B-cmake effective flags: clang-cl -### with each census file's exact command, source replaced by dummy.c
for %%Q in (quant.c quant_avx2.c quant_avx512.c) do (
  echo [B-cmake %%Q]
  %PY% %S%\x0_flags.py replay %F%\B-cmake.compile_commands.json --as %%Q --src %W%\dummy.c --obj %W%\dummy.obj --extra=-### --exec > %F%\B-cmake.%%Q.cc1.txt 2>&1
  echo rc=!ERRORLEVEL!
)
echo ==== B-proxy effective flags (record section 3): B-cmake line minus /fp:precise and /arch:*, plus /clang: -O3 -std=gnu11 -ffp-contract=off and the -m flags of D
%PY% %S%\x0_flags.py proxy %F%\B-cmake.compile_commands.json --dlike D:\mithril\x0\cfg\D-clang\compile_commands.json --out %F%\B-proxy.argv.json
for %%Q in (quant.c quant_avx2.c quant_avx512.c) do (
  echo [B-proxy %%Q]
  %PY% %S%\x0_flags.py replay %F%\B-proxy.argv.json --as %%Q --src %W%\dummy.c --obj %W%\dummy.obj --extra=-### --exec > %F%\B-proxy.%%Q.cc1.txt 2>&1
  echo rc=!ERRORLEVEL!
)
echo ==== smoke (NOT Hearth): smoke_dispatch.c with the A-ninja and B-cmake lines of quant_avx512.c and quant.c
%PY% %S%\x0_flags.py replay %F%\A-ninja.compile_commands.json --as quant_avx512.c --src %S%\smoke\smoke_dispatch.c --obj %O%\A\smoke_dispatch.obj --exec
echo A_SMOKE_AVX512_RC=!ERRORLEVEL!
%PY% %S%\x0_flags.py replay %F%\A-ninja.compile_commands.json --as quant.c --src %S%\smoke\smoke_dispatch.c --obj %O%\A-scalar\smoke_dispatch.obj --exec
echo A_SMOKE_SCALAR_RC=!ERRORLEVEL!
%PY% %S%\x0_flags.py replay %F%\B-cmake.compile_commands.json --as quant_avx512.c --src %S%\smoke\smoke_dispatch.c --obj %O%\B\smoke_dispatch.obj --exec
echo B_SMOKE_AVX512_RC=!ERRORLEVEL!
%PY% %S%\x0_flags.py replay %F%\B-cmake.compile_commands.json --as quant.c --src %S%\smoke\smoke_dispatch.c --obj %O%\B-scalar\smoke_dispatch.obj --exec
echo B_SMOKE_SCALAR_RC=!ERRORLEVEL!
echo ==== reduce probe (arm P, NOT Hearth): syntax-only (/Zs) under A-ninja and B-cmake quant_avx512.c lines
%PY% %S%\x0_flags.py replay %F%\A-ninja.compile_commands.json --as quant_avx512.c --src %S%\probes\reduce_probe.c --obj %W%\dummy.obj --extra=/Zs --exec
echo A_PROBE_SYNTAX_RC=!ERRORLEVEL!
%PY% %S%\x0_flags.py replay %F%\B-cmake.compile_commands.json --as quant_avx512.c --src %S%\probes\reduce_probe.c --obj %W%\dummy.obj --extra=/Zs --exec
echo B_PROBE_SYNTAX_RC=!ERRORLEVEL!
if exist %W%\dummy.obj echo UNEXPECTED: dummy.obj exists
echo END %DATE% %TIME%
