@echo off
rem X0 runbook step 50: dry-configure Hearth (Release) for (A) MSVC cl and (B) clang-cl, NMake Makefiles.
rem Configure only: CMake compiles its own try-compile probes, never Hearth sources.
rem Run: cmd /c D:\mithril\x0\scripts\runbook\50_configure_win.cmd > D:\mithril\jobs\50_configure_win.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\tmp mkdir D:\mithril\jobs\tmp
set TEMP=D:\mithril\jobs\tmp
set TMP=D:\mithril\jobs\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set CMAKE="C:\Program Files\CMake\bin\cmake.exe"
set H=D:\mithril\src\hearth
set B=D:\mithril\x0\cfg
echo START %DATE% %TIME%
%CMAKE% --version
if exist %B%\A-msvc rmdir /s /q %B%\A-msvc
if exist %B%\B-clangcl rmdir /s /q %B%\B-clangcl
%CMAKE% -S %H% -B %B%\A-msvc -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=cl
echo A_RC=%ERRORLEVEL%
%CMAKE% -S %H% -B %B%\B-clangcl -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_C_COMPILER=D:/mithril/tools/llvm-win-23.1.3/bin/clang-cl.exe
echo B_RC=%ERRORLEVEL%
echo END %DATE% %TIME%
