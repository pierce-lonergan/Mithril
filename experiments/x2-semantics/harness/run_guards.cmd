@echo off
rem run_guards.cmd -- negative checks of the collection guard and of the MXCSR precondition (added 2026-10-16
rem after the review). Every command below must be REFUSED before anything executes: no table instruction
rem runs on silicon here, and no results file is written. Expected exit code: 2 for each refusal.
rem   called by run_final.cmd; alone: cmd /c D:\mithril\x2\src\harness\run_guards.cmd
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set S=D:\mithril\x2\src
set H=%S%\harness
set B=D:\mithril\x2\build
set D=D:\mithril\x2\dev\guards
set PY=C:\Python313\python.exe -I -B
set M=%B%\stubs_manifest.json
set IF=VADDPS_ZMMf32_MASKmskw_ZMMf32_MEMf32_AVX512
if not exist %D% mkdir %D%
echo ---- G1 budget rows under the default BUDGET label: x2fuzz run refuses the label
%PY% %H%\gen_vectors.py --sem-root %S% --manifest %M% --out %D%\g1.vec --iform %IF% --set F-MEMFAULT
%B%\x2fuzz.exe run %D%\g1.vec %D%\g1.res --cpu 4
echo G1_RC=%ERRORLEVEL% want 2
echo ---- G2 the same rows under a DEV label (--dev): x2fuzz run refuses the budget set ids
%PY% %H%\gen_vectors.py --sem-root %S% --manifest %M% --out %D%\g2.vec --iform %IF% --set F-MEMFAULT --dev --limit 5 --label DEV-GUARD-TEST
%B%\x2fuzz.exe run %D%\g2.vec %D%\g2.res --cpu 4
echo G2_RC=%ERRORLEVEL% want 2
echo ---- G3 a DEV label without --dev: the generator refuses
%PY% %H%\gen_vectors.py --sem-root %S% --manifest %M% --out %D%\g3.vec --iform %IF% --set V1 --limit 5 --label DEV-X
echo G3_RC=%ERRORLEVEL% want 2
echo ---- G4 --dev without --limit: the generator refuses
%PY% %H%\gen_vectors.py --sem-root %S% --manifest %M% --out %D%\g4.vec --iform %IF% --set V1 --dev
echo G4_RC=%ERRORLEVEL% want 2
echo ---- G5 exhaustive on silicon without --collection-authorised: refused
%B%\x2fuzz.exe exhaustive --iform VCVTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512 --variant plain --mxcsr 1f80 --lo 0 --hi 1000 --out %D%\g5
echo G5_RC=%ERRORLEVEL% want 2
echo ---- G6 exhaustive with a preset sticky flag (MXCSR 1F81), self oracle: refused
%B%\x2fuzz.exe exhaustive --iform VCVTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512 --variant plain --mxcsr 1f81 --lo 0 --hi 1000 --out %D%\g6 --oracle self
echo G6_RC=%ERRORLEVEL% want 2
echo ---- G7 exhaustive with an unmasked exception (MXCSR 1F00), self oracle: refused
%B%\x2fuzz.exe exhaustive --iform VCVTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512 --variant plain --mxcsr 1f00 --lo 0 --hi 1000 --out %D%\g7 --oracle self
echo G7_RC=%ERRORLEVEL% want 2
if exist %D%\g1.res echo G_RES_FILE_WRITTEN g1
if exist %D%\g2.res echo G_RES_FILE_WRITTEN g2
echo ---- END guards
