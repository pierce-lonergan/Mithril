@echo off
rem X0 runbook step 72 (pre-freeze, Windows): regression of x0_extract.py, x0_decode.py and x0_loops.py on NON-Hearth
rem inputs only -- smoke_dispatch.c (two Hearth-shaped dispatch tables, 12 slots) and the adversarial rv_tricky.c /
rem rv_tricky2.c (indirect tail calls next to jump tables, GCC .cold switch cases, adjacent tables, calls through an
rem extern function-pointer variable, user noreturn calls, overlapping decodes, MSVC byte index tables) -- each
rem compiled with the A (A-ninja lines), B-cmake, C and D command lines of quant_avx512.c and quant.c (8 objects
rem per source; C and D come from step 71b). Every decode runs twice, with --worklist-order lifo and fifo, and the
rem two variants.json must be byte-identical. smoke\check_smoke.py compares every variant with
rem smoke\tricky_expect.json; any deviation fails the step (CHECK_RC=1). Then the negative test: a manifest whose
rem slot entries are moved by one byte must produce gaps. Two worker threads at most (-j 2), one job at a time.
rem Run: cmd /v:on /c D:\mithril\x0prep\x0\scripts\runbook\72_smoke_dispatch_check.cmd > D:\mithril\jobs\x0prep\72_smoke_dispatch_check.log 2>&1
setlocal enabledelayedexpansion
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\x0prep\tmp mkdir D:\mithril\jobs\x0prep\tmp
set TEMP=D:\mithril\jobs\x0prep\tmp
set TMP=D:\mithril\jobs\x0prep\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set PY=C:\Python313\python.exe -I
set L=D:\mithril\tools\llvm-win-23.1.3\bin
set XW=D:\mithril\tools\xed-v2026.08.23-win\bin\xed.exe
set W=D:\mithril\x0prep
set S=%W%\x0\scripts
set F=%W%\flags
set R=%W%\reg
echo START %DATE% %TIME%
echo ==== compile (NOT Hearth): A and B lines of quant_avx512.c and quant.c
for %%N in (smoke_dispatch rv_tricky rv_tricky2) do (
  for %%C in (A A-scalar B B-scalar) do if not exist %R%\%%C\%%N mkdir %R%\%%C\%%N
  %PY% %S%\x0_flags.py replay %F%\A-ninja.compile_commands.json --as quant_avx512.c --src %S%\smoke\%%N.c --obj %R%\A\%%N\%%N.obj --exec
  echo A_%%N_RC=!ERRORLEVEL!
  %PY% %S%\x0_flags.py replay %F%\A-ninja.compile_commands.json --as quant.c --src %S%\smoke\%%N.c --obj %R%\A-scalar\%%N\%%N.obj --exec
  echo A-scalar_%%N_RC=!ERRORLEVEL!
  %PY% %S%\x0_flags.py replay %F%\B-cmake.compile_commands.json --as quant_avx512.c --src %S%\smoke\%%N.c --obj %R%\B\%%N\%%N.obj --exec
  echo B_%%N_RC=!ERRORLEVEL!
  %PY% %S%\x0_flags.py replay %F%\B-cmake.compile_commands.json --as quant.c --src %S%\smoke\%%N.c --obj %R%\B-scalar\%%N\%%N.obj --exec
  echo B-scalar_%%N_RC=!ERRORLEVEL!
)
for %%C in (A A-scalar B B-scalar C C-scalar D D-scalar) do (
  for %%N in (smoke_dispatch rv_tricky rv_tricky2) do (
    set D=%R%\%%C\%%N
    if exist !D!\%%N.obj (set OBJ=!D!\%%N.obj) else (set OBJ=!D!\%%N.o)
    set ST=rv_kernels
    set NV=6
    if %%N==smoke_dispatch (set ST=sd_kernels& set NV=12)
    if %%N==rv_tricky2 set NV=3
    echo ==== %%C %%N: extract
    %PY% %S%\x0_extract.py -o !D!\manifest.json --struct !ST! --struct-src %S%\smoke\%%N.c --expect-variants !NV! --label %%C --readobj %L%\llvm-readobj.exe --pair %S%\smoke\%%N.c=!OBJ!
    echo %%C_%%N_EXTRACT_RC=!ERRORLEVEL!
    for %%O in (lifo fifo) do (
      %PY% %S%\x0_decode.py !D!\manifest.json -o !D!\%%O --xed %XW% --objdump %L%\llvm-objdump.exe -j 2 --worklist-order %%O --attr-cache %R%\xed_attr_cache.json > !D!\decode_%%O.log
      echo %%C_%%N_DECODE_%%O_RC=!ERRORLEVEL!
    )
    %PY% -c "import json,sys; s=json.load(open(sys.argv[1])); print(sys.argv[2], 'variants', s['n_variants'], 'resolved', s['n_resolved'], 'gaps', s['gap_counts'], 'xdis', s['crossdecoder_disagreements'], 'U_iform', s['u_iforms'], 'anomalies', s['anomalies'])" !D!\lifo\summary.json %%C_%%N
  )
  echo ==== %%C smoke_dispatch: loops, P3^(c^), canary d1
  %PY% %S%\x0_loops.py %R%\%%C\smoke_dispatch\lifo --manifest %R%\%%C\smoke_dispatch\manifest.json -o %R%\%%C\smoke_dispatch\loops.json --loop-table %S%\smoke\smoke_loop_table.csv --variant-map "sd_table:matmul[0]=sd.f32,sd_table:matmul[1]=sd.f16,sd_table:matmul[2]=sd.bf16,sd_table:matmul[3]=sd.q8,sd_table:matmul[4]=sd.q4,sd_table:act_quantize=sd.act,sd_table_global:matmul[0]=sd.f16,sd_table_global:matmul[1]=sd.f32,sd_table_global:matmul[2]=sd.q8,sd_table_global:matmul[3]=sd.bf16,sd_table_global:matmul[4]=sd.q4,sd_table_global:act_quantize=sd.act" --canary-variant "sd_table:act_quantize,sd_table_global:act_quantize" > %R%\%%C\smoke_dispatch\loops.log
  echo %%C_LOOPS_RC=!ERRORLEVEL!
  type %R%\%%C\smoke_dispatch\loops.log
)
echo ==== expectations (smoke\tricky_expect.json) and lifo/fifo identity
%PY% %S%\smoke\check_smoke.py %S%\smoke\tricky_expect.json %R%
echo CHECK_RC=!ERRORLEVEL! ^(expect 0^)
echo ==== negative test: slot entries moved by one byte (A and C smoke_dispatch); decode must report gaps
for %%C in (A C) do (
  %PY% %S%\runbook\negtest_dispatch.py %R%\%%C\smoke_dispatch\manifest.json %R%\%%C\smoke_dispatch\manifest_neg.json
  %PY% %S%\x0_decode.py %R%\%%C\smoke_dispatch\manifest_neg.json -o %R%\%%C\smoke_dispatch\decode_neg --xed %XW% --objdump %L%\llvm-objdump.exe -j 2 > nul
  echo %%C_NEG_RC=!ERRORLEVEL! ^(expect 1^)
  %PY% -c "import json,sys; s=json.load(open(sys.argv[1])); print(sys.argv[2], 'NEG gaps', s['gap_counts'], 'xdis', s['crossdecoder_disagreements'])" %R%\%%C\smoke_dispatch\decode_neg\summary.json %%C
)
echo ==== compact record of the outputs
%PY% %S%\runbook\summarize_regression.py %R% %R%\results_regression.json
echo END %DATE% %TIME%
