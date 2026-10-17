@echo off
rem build_prove.cmd -- build x2prove.exe (exhaustive rule routes) with the pinned MSVC, one compiler process.
rem Revised 2026-10-16 after review: build_info.h names the interpreter sources, x2prove.c and the compiler,
rem and every exhaustive.json carries them. Running is separate (run_prove_rev1.cmd).
rem   cmd /c D:\mithril\x2\src\proofs\build_prove.cmd > D:\mithril\jobs\x2build\prove_build.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set S=D:\mithril\x2\src
set O=D:\mithril\x2\proofs
if not exist %O% mkdir %O%
cd /d %O%
C:\Python313\python.exe -I -B %S%\harness\mkbuildinfo.py %S%\harness %O%\build_info.h PROVE=%S%\proofs\x2prove.c
cl /nologo /std:c11 /O2 /W4 /wd4127 /D_CRT_SECURE_NO_WARNINGS /MP1 /I%S%\harness /I%O% /Fe%O%\x2prove.exe %S%\proofs\x2prove.c %S%\harness\x2ref.c %S%\harness\x2sha256.c
echo CL_RC=%ERRORLEVEL%
certutil -hashfile %O%\x2prove.exe SHA256 | findstr /v "hash"
cl 2>&1 | findstr /c:"Version"
