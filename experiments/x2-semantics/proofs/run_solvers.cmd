@echo off
rem run_solvers.cmd -- Z3 routes (primary) then the cvc5 replay (second solver), one solver process at a time.
rem   cmd /c D:\mithril\x2\src\proofs\run_solvers.cmd > D:\mithril\jobs\x2build\solvers.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set PY=D:\mithril\x2\venv\Scripts\python.exe -B
set O=D:\mithril\x2\proofs
if not exist %O%\smt2 mkdir %O%\smt2
echo START Z3 %DATE% %TIME%
%PY% D:\mithril\x2\src\proofs\z3_rules.py --sem-root D:\mithril\x2\src --out %O%\z3.json --smt2-dir %O%\smt2 --timeout 1200
echo Z3_RC=%ERRORLEVEL% %TIME%
echo START CVC5 %DATE% %TIME%
%PY% D:\mithril\x2\src\proofs\second_solver.py --smt2-dir %O%\smt2 --out %O%\cvc5.json --timeout 1200
echo CVC5_RC=%ERRORLEVEL% %TIME%
echo END %DATE% %TIME%
