@echo off
rem X0 runbook step 86 (x0final, pre-freeze, Windows; NOT Hearth): configure-only flag captures of the census MOCK
rem (scripts\smoke\mock), the mock's stand-in for the pre-freeze captures of steps 70/70b: A (Visual Studio generator,
rem vcxproj and design-time GetClCommandLines, no compile), A-ninja and B-cmake (Ninja, compile_commands.json).
rem   86_mock_prefreeze_win.cmd OUTDIR
setlocal enabledelayedexpansion
set CUDA_VISIBLE_DEVICES=-1
if "%X0%"=="" set X0=D:\mithril\x0final\x0-census
set TEMP=D:\mithril\jobs\x0final\tmp
set TMP=D:\mithril\jobs\x0final\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set CMAKE="C:\Program Files\CMake\bin\cmake.exe"
set NINJA=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe
set M=%X0%\scripts\smoke\mock
set O=%~1
if exist %O% rmdir /s /q %O%
mkdir %O%
%CMAKE% -S %M% -B %O%\A-vs -G "Visual Studio 17 2022" -A x64
echo A_VS_CONFIGURE_RC=!ERRORLEVEL!
msbuild %O%\A-vs\x0mock_core.vcxproj -t:GetClCommandLines -p:Configuration=Release -p:Platform=x64 -p:DesignTimeBuild=true -p:BuildProjectReferences=false -m:1 -nologo -v:diag > %O%\A-vs.GetClCommandLines.diag.log 2>&1
echo GETCL_RC=!ERRORLEVEL!
C:\Python313\python.exe -I %X0%\scripts\runbook\design_time_lines.py %O%\A-vs.GetClCommandLines.diag.log %O%\A-vs.design_time_cl_lines.txt
echo DESIGN_TIME_RC=!ERRORLEVEL!
dir /s /b %O%\A-vs\*.obj 2>nul
for %%K in (A-ninja B-cmake) do if exist %O%\%%K rmdir /s /q %O%\%%K
%CMAKE% -S %M% -B %O%\A-ninja -G Ninja -DCMAKE_MAKE_PROGRAM="%NINJA%" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=cl
echo A_NINJA_CONFIGURE_RC=!ERRORLEVEL!
%CMAKE% -S %M% -B %O%\B-cmake -G Ninja -DCMAKE_MAKE_PROGRAM="%NINJA%" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=D:/mithril/tools/llvm-win-23.1.3/bin/clang-cl.exe
echo B_CMAKE_CONFIGURE_RC=!ERRORLEVEL!
copy /y %O%\A-ninja\compile_commands.json %O%\A-ninja.compile_commands.json >nul
copy /y %O%\B-cmake\compile_commands.json %O%\B-cmake.compile_commands.json >nul
dir /s /b %O%\A-ninja\*.obj %O%\B-cmake\*.obj 2>nul
