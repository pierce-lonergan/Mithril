@echo off
rem run_solvers_rev1.cmd -- solver-side routes after the 2026-10-16 review, ONE solver process at a time
rem (one thread). Outputs in D:\mithril\x2\proofs\rev1.
rem   1. differentials: smt_table.py (compare / COMIS / VCVTPH2PS encodings vs fp_ops), trees.py (tree
rem      transliterations vs the table compositions, and the unit-basis maps), int_differential.py (integer lane
rem      formulas vs int_ops, and the hashes of x2prove's C transliterations);
rem   2. regression of the lane-formula refactor: the old integer queries re-exported without solving, hashes
rem      compared with the first run's (z3.json, z3_b.json, int_export.json);
rem   3. Z3 on the rebuilt queries (R06-R11 instances, R20, R21, the definitional R08/R09 lemmas, R01/R04/R05 again
rem      plus their table-relation variants), the T lemmas,
rem      R12/P (bound) and R14/P (exported now), and the R02/R03 lemmas L1-L6 (exported now);
rem   4. cvc5 on every query exported in step 3.
rem   cmd /c D:\mithril\x2\src\proofs\run_solvers_rev1.cmd > D:\mithril\jobs\x2build\solvers_rev1.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set PY=D:\mithril\x2\venv\Scripts\python.exe -B
set S=D:\mithril\x2\src
set P=%S%\proofs
set O=D:\mithril\x2\proofs
set R=%O%\rev1
if not exist %R% mkdir %R%
echo START %DATE% %TIME%
echo ==== 1a smt_table differential %TIME%
%PY% %P%\smt_table.py --sem-root %S% --out %R%\differential_smt_table.json
echo SMT_TABLE_RC=%ERRORLEVEL% %TIME%
echo ==== 1b trees %TIME%
%PY% %P%\trees.py --sem-root %S% --out %R%\trees.json
echo TREES_RC=%ERRORLEVEL% %TIME%
echo ==== 1c integer differential (x2prove HASH entries first) %TIME%
%O%\x2prove.exe %R%\exhaustive_hash.json --threads 1 --only HASH-PABS-PSIGN,HASH-PACKS
%PY% %P%\int_differential.py --sem-root %S% --exhaustive %R%\exhaustive_hash.json --out %R%\int_differential.json
echo INT_DIFF_RC=%ERRORLEVEL% %TIME%
echo ==== 2 refactor regression: re-export the first run's integer queries without solving %TIME%
if not exist %R%\regress mkdir %R%\regress
%PY% %P%\z3_rules.py --sem-root %S% --out %R%\regress\z3_export.json --smt2-dir %R%\regress\smt2 --only R12,R13,R14,R15,R16,R17,R18 --export-only
%PY% %P%\z3_int.py --sem-root %S% --out %R%\regress\int_export.json --smt2-dir %R%\regress\smt2int --only R13/P,R13/W,R13/M,R14/M,R12/M,R15/P,R15/M,R16/P,R16/M,R18/M --export-only
echo REGRESS_RC=%ERRORLEVEL% %TIME%
echo ==== 3a Z3: rebuilt FP queries %TIME%
%PY% %P%\z3_rules.py --sem-root %S% --out %R%\z3.json --smt2-dir %R%\smt2 --timeout 600 --only R01,R04,R05,R06,R07,R08,R09,R10,R11,R20,R21
echo Z3_RC=%ERRORLEVEL% %TIME%
echo ==== 3b Z3: T lemmas, R12/P, R14/P %TIME%
%PY% %P%\z3_int.py --sem-root %S% --out %R%\int.json --smt2-dir %R%\smt2int --timeout 1200 --only T/red8,T/red_quads,T/red_quad1,R12/P,R14/P
echo Z3_INT_RC=%ERRORLEVEL% %TIME%
echo ==== 3c Z3: R02/R03 lemmas L1-L6 %TIME%
%PY% %P%\z3_fold.py --sem-root %S% --out %R%\fold.json --skip-concrete --smt2-dir %R%\smt2fold --timeout 600
echo FOLD_RC=%ERRORLEVEL% %TIME%
echo ==== 4 cvc5 %TIME%
%PY% %P%\second_solver.py --smt2-dir %R%\smt2 --out %R%\cvc5.json --timeout 600
echo CVC5_RC=%ERRORLEVEL% %TIME%
%PY% %P%\second_solver.py --smt2-dir %R%\smt2int --out %R%\cvc5_int.json --timeout 600
echo CVC5_INT_RC=%ERRORLEVEL% %TIME%
%PY% %P%\second_solver.py --smt2-dir %R%\smt2fold --out %R%\cvc5_fold.json --timeout 600
echo CVC5_FOLD_RC=%ERRORLEVEL% %TIME%
echo END %DATE% %TIME%
