@echo off
rem run_solvers2.cmd A|B -- second solver pass after the first run_solvers.cmd was stopped on R14:
rem   A: Z3 on the remaining monolithic integer rows R14-R18 (600 s each);
rem   B: cvc5 replay of the exported queries (R02/R03 1,200 s, others 600 s), monolithic R13-R16 excluded.
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set PY=D:\mithril\x2\venv\Scripts\python.exe -B
set O=D:\mithril\x2\proofs
echo START %1 %DATE% %TIME%
if "%1"=="A" %PY% D:\mithril\x2\src\proofs\z3_rules.py --sem-root D:\mithril\x2\src --out %O%\z3_b.json --smt2-dir %O%\smt2 --timeout 600 --only R14,R15,R16,R17,R18
if "%1"=="B" %PY% D:\mithril\x2\src\proofs\second_solver.py --smt2-dir %O%\smt2 --out %O%\cvc5.json --timeout 600 --long R02,R03 --long-timeout 1200 --names R01,R02,R02-lemma-commute,R02-lemma-nan,R02-lemma-order,R03,R04,R05,R06_DAZ=0,R06_DAZ=1,R07_DAZ=0,R07_DAZ=1,R08,R08_inst,R09,R09_inst,R10,R10_inst,R11,R11_inst,R12,R19,R20,R21
echo RC_%1=%ERRORLEVEL%
echo END %1 %DATE% %TIME%
