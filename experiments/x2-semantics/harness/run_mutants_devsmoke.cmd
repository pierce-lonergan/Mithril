@echo off
rem run_mutants_devsmoke.cmd -- the seeded table mutants (mutants\, FUZZ-DESIGN sec. 6.4) against the DEVELOPMENT
rem smoke results of run_devsmoke.cmd (label DEV-SMOKE; hand vectors of semantics\selftest.py). Comparator time only:
rem no table instruction runs on silicon here. Added 2026-10-23 (x2freeze): the 2026-10-16 cross-section was made
rem with the previous stub manifest, so the comparator refuses it against the rebuilt one.
rem   cmd /c D:\mithril\x2\src\harness\run_mutants_devsmoke.cmd > D:\mithril\jobs\x2build\mutants_devsmoke.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set S=D:\mithril\x2\src
set H=%S%\harness
set B=D:\mithril\x2\build
set D=D:\mithril\x2\dev
set PY=C:\Python313\python.exe -I -B
echo START %DATE% %TIME%
%PY% %H%\mutants\mutants.py --seal
%PY% %H%\mutants\run_mutants.py --sem-root %S% --manifest %B%\stubs_manifest.json --vectors %D%\devsmoke.vec --silicon %D%\devsmoke.sil --silicon2 %D%\devsmoke.sil2 --work %D%\mut --out %D%\mutants_devsmoke.summary.json
echo MUTANTS_RC=%ERRORLEVEL%
echo END %DATE% %TIME%
