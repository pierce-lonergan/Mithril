@echo off
rem run_solvers3.cmd -- second solver for the decomposed integer lemmas and for the monolithic R17/R18 queries
rem (one solver process at a time).
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set PY=D:\mithril\x2\venv\Scripts\python.exe -B
set O=D:\mithril\x2\proofs
echo START %DATE% %TIME%
%PY% D:\mithril\x2\src\proofs\z3_int.py --sem-root D:\mithril\x2\src --out %O%\int_export.json --smt2-dir %O%\smt2int --timeout 600 --only R13/P,R13/W,R13/M,R14/M,R12/P,R12/M,R15/P,R15/M,R16/P,R16/M,R18/M
echo EXPORT_RC=%ERRORLEVEL%
%PY% D:\mithril\x2\src\proofs\second_solver.py --smt2-dir %O%\smt2int --out %O%\cvc5_int.json --timeout 600
echo CVC5_INT_RC=%ERRORLEVEL%
%PY% D:\mithril\x2\src\proofs\second_solver.py --smt2-dir %O%\smt2 --out %O%\cvc5_b.json --timeout 600 --names R17,R18
echo CVC5_B_RC=%ERRORLEVEL%
echo END %DATE% %TIME%
