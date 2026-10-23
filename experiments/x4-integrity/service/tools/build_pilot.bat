@echo off
rem X4 noise-pilot build (X4 pilot track, 2026-10-23; revisions 4 and 5 the same day): the binaries a
rem pilot night runs, built on the desktop with MSVC and cargo at no more than 3 parallel jobs, every
rem artefact under ROOT (the first argument; default D:\mithril\x4c).
rem
rem   build_pilot.bat [ROOT]     sources in ROOT\src\{service,sandbox,pilot}; outputs in ROOT\{obj,bin,...}
rem
rem   0. refuses unless the Hearth clone is b5d3f14 with a clean tree and (revision 5, review round 5)
rem      cl is 19.44.35229 for x64, CMake 4.4.3, Ninja 1.12.1 and rustc 1.91.1 (record section 2).
rem      This file keeps CRLF line endings (.gitattributes: *.bat text eol=crlf).
rem   1. hearth-c-ref: a clean out-of-tree CMake Release build of Hearth b5d3f14 (Ninja, -j 3) into an
rem      EMPTY %HB% (revision 4: the build is part of this script, not a prerequisite); the nine
rem      engine objects are hashed into the log. Eight of them are linked unchanged.
rem   2. platform_win.c recompiled with CMake's exact hearth_core flags plus six renames, so the shim
rem      (hearth_x4_shim.c) supplies hx_thread_create/join, hx_cond_wait/timedwait and (revision 4)
rem      hx_cond_signal/broadcast (the wake accounting of x4h_quiesce).
rem   3. x4harness_hearth.exe = harness + shim + Hearth workload set + sandbox probes + the objects,
rem      all /MD like the CMake build (one C runtime in the process). 3b: DEV ONLY, never pinned:
rem      x4harness_hearth_q0.exe, the same with x4h.c built /DX4H_QUIESCE_IGNORE_WAKES, to show the
rem      race the wake accounting closes (dry_quiesce_wake).
rem   4. the dev harness x4harness.exe, x4sb_probe.exe and the dry-run plant x4plant.exe (/MT).
rem   5. x4svc.exe: cargo test (3 jobs, 3 test threads) and cargo build, release.
rem Sources: ROOT\src\{service,sandbox,pilot} (a copy of experiments/x4-integrity/; the unit tests read
rem pilot\pilot.cfg.template).
setlocal
set "R=%~1"
if "%R%"=="" set "R=D:\mithril\x4c"
set CUDA_VISIBLE_DEVICES=-1
if not exist %R%\tmp mkdir %R%\tmp
set TEMP=%R%\tmp
set TMP=%R%\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set H=D:\mithril\src\hearth
set HB=%R%\hearth-build
set S=%R%\src\service
set P=%R%\src\sandbox\probes
set O=%R%\obj
set B=%R%\bin
set CMAKE="C:\Program Files\CMake\bin\cmake.exe"
set "NINJA=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
set "TC=C:\Users\Pierce Lonergan\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin"
set "RUSTC=%TC%\rustc.exe"
if not exist %O% mkdir %O%
if not exist %O%\q0 mkdir %O%\q0
if not exist %B% mkdir %B%
if not exist %O%\dev mkdir %O%\dev
echo ==== [0] source and toolchain
for /f %%h in ('git -C %H% rev-parse HEAD') do set HEAD=%%h
echo hearth HEAD %HEAD%
if not "%HEAD%"=="b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220" (echo REFUSED: the Hearth clone is not b5d3f14 & exit /b 1)
set DIRTY=
for /f "delims=" %%l in ('git -C %H% --no-optional-locks status --porcelain') do set DIRTY=1
if defined DIRTY (echo REFUSED: the Hearth clone has local changes & exit /b 1)
echo hearth tree clean
set CLV=
for /f "delims=" %%v in ('cl 2^>^&1 ^| findstr /c:"Version 19.44.35229 for x64"') do set "CLV=%%v"
if not defined CLV (echo REFUSED: cl is not 19.44.35229 for x64 & cl 2>&1 | findstr /i version & exit /b 1)
echo %CLV%
set CMV=
for /f "tokens=3" %%v in ('%CMAKE% --version ^| findstr /b cmake') do set "CMV=%%v"
echo cmake version %CMV%
if not "%CMV%"=="4.4.3" (echo REFUSED: CMake is not 4.4.3 & exit /b 1)
set NJV=
for /f "delims=" %%v in ('"%NINJA%" --version') do set "NJV=%%v"
echo ninja %NJV%
if not "%NJV%"=="1.12.1" (echo REFUSED: Ninja is not 1.12.1 & exit /b 1)
set RV=
for /f "delims=" %%v in ('"%RUSTC%" -V') do set "RV=%%v"
echo %RV%
if not "%RV%"=="rustc 1.91.1 (ed61e7d7e 2025-11-07)" (echo REFUSED: rustc is not 1.91.1 & exit /b 1)
"%TC%\cargo.exe" -V
echo ==== [1] hearth-c-ref: clean CMake Release build into an empty %HB%
if exist %HB% rmdir /s /q %HB%
%CMAKE% -S %H% -B %HB% -G Ninja "-DCMAKE_MAKE_PROGRAM=%NINJA%" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=cl -DCMAKE_EXPORT_COMPILE_COMMANDS=ON >nul
echo configure rc=%ERRORLEVEL%
%CMAKE% --build %HB% -j 3 >nul
echo build rc=%ERRORLEVEL%
set HO=%HB%\CMakeFiles\hearth_core.dir\engine\src
powershell -NoProfile -Command "Get-ChildItem '%HO%\*.obj' | Sort-Object Name | ForEach-Object { '{0}  {1}' -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name }"
echo ==== [2] platform_win.c with the thread/condvar renames (CMake hearth_core flags)
cl /nologo -DHEARTH_BUILD_DLL -D_CRT_SECURE_NO_WARNINGS -I%H%\engine\include -I%H%\engine\src /DWIN32 /D_WINDOWS /O2 /Ob2 /DNDEBUG -std:c11 -MD /experimental:c11atomics /fp:precise /utf-8 /W3 /Dhx_thread_create=hx__os_thread_create /Dhx_thread_join=hx__os_thread_join /Dhx_cond_wait=hx__os_cond_wait /Dhx_cond_timedwait=hx__os_cond_timedwait /Dhx_cond_signal=hx__os_cond_signal /Dhx_cond_broadcast=hx__os_cond_broadcast /Fo%O%\platform_win_x4.obj -c %H%\engine\src\platform_win.c
echo platform_win rc=%ERRORLEVEL%
echo ==== [3] harness, shim, Hearth workload set, probes (/MD)
cl /nologo /MP3 /O2 /W4 -std:c11 -MD /experimental:c11atomics /utf-8 /DWIN32 /D_WINDOWS /D_CRT_SECURE_NO_WARNINGS /I%S%\proto /I%S%\harness /I%P% /I%H%\engine\include /I%H%\engine\src /Fo%O%\ -c %S%\harness\x4h.c %S%\harness\hearth_x4_shim.c %S%\harness\hearth_workloads.c %P%\x4sb_probes.c
echo harness-objs rc=%ERRORLEVEL%
set HOBJ=%HO%\pool.c.obj %HO%\quant.c.obj %HO%\modelfile.c.obj %HO%\store.c.obj %HO%\model.c.obj %HO%\api.c.obj %HO%\quant_avx2.c.obj %HO%\quant_avx512.c.obj
cl /nologo %O%\x4h.obj %O%\hearth_x4_shim.obj %O%\hearth_workloads.obj %O%\x4sb_probes.obj %O%\platform_win_x4.obj %HOBJ% /Fe:%B%\x4harness_hearth.exe /link bcrypt.lib advapi32.lib
echo x4harness_hearth rc=%ERRORLEVEL%
echo ==== [3b] DEV ONLY (never pinned): x4harness_hearth_q0.exe, quiesce without the wake accounting
cl /nologo /O2 /W4 -std:c11 -MD /experimental:c11atomics /utf-8 /DWIN32 /D_WINDOWS /D_CRT_SECURE_NO_WARNINGS /DX4H_QUIESCE_IGNORE_WAKES /I%S%\proto /I%S%\harness /I%P% /Fo%O%\q0\x4h.obj -c %S%\harness\x4h.c
cl /nologo %O%\q0\x4h.obj %O%\hearth_x4_shim.obj %O%\hearth_workloads.obj %O%\x4sb_probes.obj %O%\platform_win_x4.obj %HOBJ% /Fe:%B%\x4harness_hearth_q0.exe /link bcrypt.lib advapi32.lib
echo x4harness_hearth_q0 rc=%ERRORLEVEL%
echo ==== [4] dev harness, outside probe, dry-run plant (/MT)
cl /nologo /MP3 /O2 /W4 /std:c11 /MT /DWIN32 /D_WINDOWS /D_CRT_SECURE_NO_WARNINGS /I%S%\proto /I%S%\harness /I%P% %S%\harness\x4h.c %S%\harness\dev_workloads.c %P%\x4sb_probes.c /Fe:%B%\x4harness.exe /Fo:%O%\dev\
echo x4harness rc=%ERRORLEVEL%
cl /nologo /O2 /W4 /std:c11 /MT /DWIN32 /D_WINDOWS /D_CRT_SECURE_NO_WARNINGS /I%S%\proto /I%S%\harness /I%P% %P%\x4sb_probe_main.c %P%\x4sb_probes.c /Fe:%B%\x4sb_probe.exe /Fo:%O%\dev\
echo x4sb_probe rc=%ERRORLEVEL%
cl /nologo /O2 /W4 /std:c11 /MT /DWIN32 /D_WINDOWS %S%\tools\x4plant.c /Fe:%B%\x4plant.exe /Fo:%O%\dev\
echo x4plant rc=%ERRORLEVEL%
echo ==== [5] x4svc (cargo 1.91.1 msvc by absolute path, 3 jobs)
set CARGO_HOME=%R%\cargo-home
set CARGO_TARGET_DIR=%R%\cargo-target
cd /d %S%\orchestrator
"%TC%\cargo.exe" test -j 3 --release -- --test-threads=3 2>&1
echo cargo-test rc=%ERRORLEVEL%
"%TC%\cargo.exe" build -j 3 --release 2>&1
echo cargo-build rc=%ERRORLEVEL%
copy /y %CARGO_TARGET_DIR%\release\x4svc.exe %B%\x4svc.exe >nul
echo ==== sha256
powershell -NoProfile -Command "Get-ChildItem %B%\*.exe | ForEach-Object { '{0}  {1}  {2}' -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Length, $_.Name }"
endlocal
