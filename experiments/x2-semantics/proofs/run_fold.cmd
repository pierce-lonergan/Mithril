@echo off
rem run_fold.cmd -- R02/R03 lemma route and the bit-blast tactic attempt (one solver process).
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
echo START %DATE% %TIME%
D:\mithril\x2\venv\Scripts\python.exe -B D:\mithril\x2\src\proofs\z3_fold.py --sem-root D:\mithril\x2\src --out D:\mithril\x2\proofs\fold.json --timeout 1500
echo FOLD_RC=%ERRORLEVEL%
echo END %DATE% %TIME%
