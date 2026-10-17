@echo off
rem X0 runbook step 82 (Windows): census.json (x0_census.py) and verdict.json (judge.py) of a run.
rem   82_census_assemble.cmd RUN [--qualify-tables]
rem Pre-freeze review of 2026-10-17: a census run takes the freeze point and the run commit from the init step's
rem run.json only (x0_driver.py and x0_census.py refuse --freeze-commit / --scripts-commit there; a NON-Hearth smoke
rem run may still pass them), and the assembler and judge.py run only from the tree init verified.
setlocal
set CUDA_VISIBLE_DEVICES=-1
if "%X0%"=="" (
  echo REFUSED: set X0 to experiments\x0-census of the tree to use
  exit /b 2
)
set RUN=%~1
shift
C:\Python313\python.exe -I %X0%\scripts\x0_driver.py assemble --run %RUN% --tools %X0%\scripts\runbook\census_tools_win.json --xml D:\mithril\x0prep\x86-intel.xml %1 %2 %3 %4 %5
echo ASSEMBLE_RC=%ERRORLEVEL%
