@echo off
rem X0 runbook step 79 (CENSUS init, Windows): x0_driver.py init for the census run. It REFUSES unless the record's status
rem line reads FROZEN and the seven Hearth files carry the blob hashes of record section 2.
rem   79_census_init.cmd RUN [RECORD]   (RECORD: default %X0%\..\..\docs\m0\prereg\X0-census.md, the checkout's record)
rem x0final revision: X0 must name experiments\x0-census of a clean git checkout of the freeze commit on the desktop
rem (for example `git clone` of the repository, then `git checkout <freeze commit>`); there is no default tree, and
rem x0_driver.py init refuses a dirty checkout or a record that is not FROZEN at HEAD.
rem Pre-freeze review of 2026-10-17: init records the freeze point (the first commit with the record FROZEN) and HEAD
rem separately; it refuses a record edited other than by an appended amendment, class/, scripts/ or flags/ changes
rem the amendment does not name, ignored files there other than __pycache__, and a Hearth tree not at b5d3f14.
setlocal
set CUDA_VISIBLE_DEVICES=-1
if "%X0%"=="" (
  echo REFUSED: set X0 to experiments\x0-census of the clean checkout at the freeze commit
  exit /b 2
)
set REC=%~2
if "%REC%"=="" set REC=%X0%\..\..\docs\m0\prereg\X0-census.md
C:\Python313\python.exe -I %X0%\scripts\x0_driver.py init --run %~1 --kind census --source D:\mithril\src\hearth --record %REC%
echo INIT_RC=%ERRORLEVEL%
