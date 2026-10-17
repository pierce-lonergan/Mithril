@echo off
rem run_selftests.cmd -- the harness self-tests and the interpreter validation on the desktop.
rem Silicon executes table instructions only in x2fuzz selftest step 9, the exhaustive-engine plumbing check
rem (V5-eligible stubs, 4,096 fixed inputs each; development, not data under the X2 record).
rem   cmd /c D:\mithril\x2\src\harness\run_selftests.cmd > D:\mithril\jobs\x2build\selftests.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set S=D:\mithril\x2\src
set H=%S%\harness
set B=D:\mithril\x2\build
set D=D:\mithril\x2\dev
set PY=C:\Python313\python.exe -I -B
if not exist %D% mkdir %D%
echo ==== 1 x2fuzz selftest %TIME%
%B%\x2fuzz.exe selftest --cpu 4 --scratch D:\mithril\jobs\x2build\selftest_scratch
echo X2FUZZ_SELFTEST_RC=%ERRORLEVEL%
echo ==== 2 semantics selftest (reference) %TIME%
cd /d %S%
C:\Python313\python.exe -B -m semantics.selftest > %D%\semantics_selftest.log 2>&1
echo SEMANTICS_SELFTEST_RC=%ERRORLEVEL%
findstr /c:"checks:" /c:"bundle" %D%\semantics_selftest.log
echo ==== 3 compare selftest %TIME%
%PY% %H%\compare.py --selftest
echo COMPARE_SELFTEST_RC=%ERRORLEVEL%
echo ==== 4 gen_vectors selftest %TIME%
%PY% %H%\gen_vectors.py --sem-root %S% --manifest %B%\stubs_manifest.json --selftest > %D%\gen_selftest.log 2>&1
echo GEN_SELFTEST_RC=%ERRORLEVEL%
type %D%\gen_selftest.log
echo ==== 5 interpreter validation (C vs Python, >= 10^6 lane cases) %TIME%
%PY% %H%\validate_interp.py gen --sem-root %S% --manifest %B%\stubs_manifest.json --out %D%\valid.vec --lane-cases 1000000
%B%\x2fuzz.exe predict %D%\valid.vec %D%\valid.c
echo PREDICT_RC=%ERRORLEVEL% %TIME%
%PY% %H%\pyref.py --sem-root %S% --manifest %B%\stubs_manifest.json %D%\valid.vec %D%\valid.py
echo PYREF_RC=%ERRORLEVEL% %TIME%
%PY% %H%\validate_interp.py check --manifest %B%\stubs_manifest.json --vectors %D%\valid.vec --c %D%\valid.c --py %D%\valid.py --out %D%\valid.report.json
echo VALIDATE_RC=%ERRORLEVEL%
echo ==== END %TIME%
