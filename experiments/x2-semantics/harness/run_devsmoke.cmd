@echo off
rem run_devsmoke.cmd -- DEVELOPMENT smoke run on the hand vectors of semantics/selftest.py (label DEV-SMOKE).
rem Not data under the X2 record: no budget row, no class cell. One thread at a time; two runs on two CPUs
rem whose L3 groups (printed in the fingerprint) differ, to exercise the two-CCD repeat.
rem   cmd /c D:\mithril\x2\src\harness\run_devsmoke.cmd > D:\mithril\jobs\x2build\devsmoke.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set S=D:\mithril\x2\src
set H=%S%\harness
set B=D:\mithril\x2\build
set D=D:\mithril\x2\dev
set PY=C:\Python313\python.exe -I -B
set M=%B%\stubs_manifest.json
if not exist %D% mkdir %D%
echo ==== build %TIME%
%PY% %H%\devsmoke.py build --sem-root %S% --manifest %M% --out %D%\devsmoke.vec
echo BUILD_RC=%ERRORLEVEL%
%B%\x2fuzz.exe predict %D%\devsmoke.vec %D%\devsmoke.c
echo PREDICT_RC=%ERRORLEVEL%
%PY% %H%\pyref.py --sem-root %S% --manifest %M% %D%\devsmoke.vec %D%\devsmoke.py
echo PYREF_RC=%ERRORLEVEL%
echo ==== silicon run 1 (CPU 4) %TIME%
%B%\x2fuzz.exe run %D%\devsmoke.vec %D%\devsmoke.sil --cpu 4
echo RUN1_RC=%ERRORLEVEL%
echo ==== silicon run 2 (CPU 20) %TIME%
%B%\x2fuzz.exe run %D%\devsmoke.vec %D%\devsmoke.sil2 --cpu 20
echo RUN2_RC=%ERRORLEVEL%
type %D%\devsmoke.sil.fingerprint.json
type %D%\devsmoke.sil2.fingerprint.json
echo ==== report %TIME%
%PY% %H%\devsmoke.py report --sem-root %S% --manifest %M% --vectors %D%\devsmoke.vec --silicon %D%\devsmoke.sil --silicon2 %D%\devsmoke.sil2 --pred %D%\devsmoke.c --pyref %D%\devsmoke.py --out %D%\devsmoke.report.json
echo REPORT_RC=%ERRORLEVEL%
echo ==== END %TIME%
