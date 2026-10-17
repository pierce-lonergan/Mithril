@echo off
rem run_int.cmd -- decomposed QF_BV routes for R12-R16 (one solver process).
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
echo START %DATE% %TIME%
D:\mithril\x2\venv\Scripts\python.exe -B D:\mithril\x2\src\proofs\z3_int.py --sem-root D:\mithril\x2\src --out D:\mithril\x2\proofs\int.json --timeout 1200
echo INT_RC=%ERRORLEVEL%
echo END %DATE% %TIME%
