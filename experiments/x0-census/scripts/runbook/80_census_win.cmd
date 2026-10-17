@echo off
rem X0 runbook step 80 (CENSUS, Windows; only after the record is FROZEN): one configuration of the census.
rem   80_census_win.cmd RUN CFG [MODE] [more x0_driver.py config arguments]
rem   CFG = A | A-ninja | B-cmake (census mode), P.A | P.A-ninja | P.B-cmake (MODE probe, add --from-config CFG),
rem         or any configuration of a NON-Hearth smoke run (MODE replay or census with a --mock run).
rem Environment: X0 = experiments\x0-census of the tree to use; required (x0final revision: no default, so a run
rem cannot silently use another copy of the scripts). For the census: the clean checkout of the freeze commit.
rem It configures twice from scratch, builds twice, builds the debug-info twin, captures the effective flags and P3(a),
rem then extracts, decodes (-j 2), attributes and analyses the loops of both builds (x0_driver.py, record sections 2-7).
rem One compiler or MSBuild node at a time; XED with at most 2 workers; no GPU.
rem The census proper: 79_census_init.cmd first (it refuses unless the record is FROZEN and the Hearth blobs match).
setlocal enabledelayedexpansion
set CUDA_VISIBLE_DEVICES=-1
if "%X0%"=="" (
  echo REFUSED: set X0 to experiments\x0-census of the tree to use
  exit /b 2
)
if not exist D:\mithril\jobs\x0final\tmp mkdir D:\mithril\jobs\x0final\tmp
set TEMP=D:\mithril\jobs\x0final\tmp
set TMP=D:\mithril\jobs\x0final\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set RUN=%~1
set CFG=%~2
set MODE=%~3
if "%MODE%"=="" set MODE=census
shift & shift & shift
set MORE=
:more
if "%~1"=="" goto go
set MORE=%MORE% %1
shift
goto more
:go
echo START %DATE% %TIME% RUN=%RUN% CFG=%CFG% MODE=%MODE% MORE=%MORE%
C:\Python313\python.exe -I %X0%\scripts\x0_driver.py config --run %RUN% --config %CFG% --mode %MODE% --tools %X0%\scripts\runbook\census_tools_win.json %MORE%
echo CONFIG_RC=!ERRORLEVEL!
echo END %DATE% %TIME%
