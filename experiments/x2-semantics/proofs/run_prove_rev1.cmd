@echo off
rem run_prove_rev1.cmd -- the exhaustive routes after the 2026-10-16 review, ONE thread (this track's other
rem thread runs the solver job beside it). Outputs in D:\mithril\x2\proofs\rev1.
rem   1. every rule under the default environment (MXCSR 0x1F80), plus the DIFF-* and HASH-* entries;
rem   2. the environment-dependent rows under the seven other MXCSR values the review used
rem      (DAZ, FTZ, DAZ+FTZ, RD, RU, RZ, RZ+DAZ+FTZ);
rem   3. R19 (RNE) under DAZ, FTZ and DAZ+FTZ.
rem   cmd /c D:\mithril\x2\src\proofs\run_prove_rev1.cmd > D:\mithril\jobs\x2build\prove_rev1.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set O=D:\mithril\x2\proofs
set R=%O%\rev1
if not exist %R% mkdir %R%
echo START %DATE% %TIME%
certutil -hashfile %O%\x2prove.exe SHA256 | findstr /v "hash"
%O%\x2prove.exe %R%\exhaustive.json --threads 1
echo PROVE1_RC=%ERRORLEVEL% %TIME%
%O%\x2prove.exe %R%\exhaustive_env.json --threads 1 --only R04,R05,R06,R07,R08,R09,R10,R11,R20,R21 --mxcsr 1fc0,9f80,9fc0,3f80,5f80,7f80,ffc0
echo PROVE2_RC=%ERRORLEVEL% %TIME%
%O%\x2prove.exe %R%\exhaustive_r19env.json --threads 1 --only R19 --mxcsr 1fc0,9f80,9fc0
echo PROVE3_RC=%ERRORLEVEL% %TIME%
echo END %DATE% %TIME%
