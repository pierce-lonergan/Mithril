@echo off
rem X0 runbook step 82 (Windows): census.json (x0_census.py) and verdict.json (judge.py) of a run.
rem   82_census_assemble.cmd RUN [--freeze-commit SHA] [--scripts-commit SHA] [--qualify-tables]
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
