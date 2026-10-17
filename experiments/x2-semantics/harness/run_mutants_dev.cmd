@echo off
rem run_mutants_dev.cmd -- calibration of the seeded-table-mutant runner (mutants\, FUZZ-DESIGN sec. 6.4) on
rem DEVELOPMENT data. Comparator time only: no table instruction runs on silicon here. Input: the cross-section
rem vectors and silicon results produced by the 2026-10-16 review of this build (same family, independent
rem context; label DEV-REVIEW-X2BUILD; D:\mithril\review-x2build\harness-lens\rv.*), COPIED, not modified.
rem Also re-compares that set with the revised comparator (provenance checks, sticky-flag anomalies).
rem   cmd /c D:\mithril\x2\src\harness\run_mutants_dev.cmd > D:\mithril\jobs\x2build\mutants_dev.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set S=D:\mithril\x2\src
set H=%S%\harness
set B=D:\mithril\x2\build
set M=%B%\stubs_manifest.json
set X=D:\mithril\x2\dev\xsec
set RV=D:\mithril\review-x2build\harness-lens
set PY=C:\Python313\python.exe -I -B
if not exist %X% mkdir %X%
echo START %DATE% %TIME%
for %%f in (rv.vec rv.sil rv.sil2 rv.sil.fingerprint.json rv.sil2.fingerprint.json rv.vec.notes.json) do copy /y %RV%\%%f %X%\%%f >nul
for %%f in (rv.vec rv.sil rv.sil2) do certutil -hashfile %X%\%%f SHA256 | findstr /v "hash"
echo ==== predictions (C and Python) and the revised comparator %TIME%
%B%\x2fuzz.exe predict %X%\rv.vec %X%\rv.c
%PY% %H%\pyref.py --sem-root %S% --manifest %M% %X%\rv.vec %X%\rv.py
%PY% %H%\compare.py --manifest %M% --vectors %X%\rv.vec --silicon %X%\rv.sil --silicon2 %X%\rv.sil2 --pred %X%\rv.c --pyref %X%\rv.py --out %X%\rv.report.json
echo COMPARE_RC=%ERRORLEVEL%
echo ==== mutant seal %TIME%
%PY% %H%\mutants\mutants.py --seal
echo ==== mutants %TIME%
%PY% %H%\mutants\run_mutants.py --sem-root %S% --manifest %M% --vectors %X%\rv.vec --silicon %X%\rv.sil --work %X%\mut --out %X%\mutants.summary.json
echo MUTANTS_RC=%ERRORLEVEL%
echo END %DATE% %TIME%
