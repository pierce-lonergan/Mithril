@echo off
rem build.cmd -- build the X2 fuzz harness on the desktop with the pinned MSVC toolset (X0 TOOLCHAINS.md:
rem cl 19.44.35229, toolset 14.44.35207, ml64 from the same toolset). One compiler process (/MP1), so it
rem can run beside another job of this track within the 2-thread budget.
rem   cmd /c D:\mithril\x2\src\harness\build.cmd > D:\mithril\jobs\x2build\build.log 2>&1
rem Layout: sources D:\mithril\x2\src (a copy of experiments\x2-semantics), outputs D:\mithril\x2\build.
setlocal
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\x2build\tmp mkdir D:\mithril\jobs\x2build\tmp
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set S=D:\mithril\x2\src
set H=%S%\harness
set B=D:\mithril\x2\build
set PY=C:\Python313\python.exe -I -B
if not exist %B% mkdir %B%
echo START %DATE% %TIME%
%PY% %H%\stubgen.py --sem-root %S% --xed-bin D:\mithril\tools\xed-v2026.08.23-win\bin --out %B% > %B%\stubgen.log 2>&1
set RC=%ERRORLEVEL%
type %B%\stubgen.log
echo STUBGEN_RC=%RC%
%PY% %H%\mkbuildinfo.py %H% %B%\build_info.h
cd /d %B%
ml64 /nologo /c /Fo%B%\stubs.obj %B%\stubs.asm > %B%\ml64_stubs.log 2>&1
echo ML64_STUBS_RC=%ERRORLEVEL%
type %B%\ml64_stubs.log | findstr /i /c:"error" /c:"warning"
ml64 /nologo /c /Fo%B%\x2probe.obj %H%\x2probe.asm
echo ML64_PROBE_RC=%ERRORLEVEL%
cl /nologo /std:c11 /O2 /W4 /wd4127 /D_CRT_SECURE_NO_WARNINGS /MP1 /I%H% /I%B% /Fe%B%\x2fuzz.exe %H%\x2fuzz.c %H%\x2ref.c %H%\x2sha256.c %B%\stubs_table.c %B%\stubs.obj %B%\x2probe.obj advapi32.lib
echo CL_RC=%ERRORLEVEL%
cl 2>&1 | findstr /c:"Version"
echo END %DATE% %TIME%
