@echo off
rem X0 runbook step 62 (optional): run the same extract + decode natively on Windows (Python 3.13,
rem Windows LLVM tools, MSVC-built XED) and compare with the WSL results of step 61.
rem Run: cmd /v:on /c D:\mithril\x0\scripts\runbook\62_smoke_decode_win.cmd > D:\mithril\jobs\62_smoke_decode_win.log 2>&1
setlocal enabledelayedexpansion
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\tmp mkdir D:\mithril\jobs\tmp
set TEMP=D:\mithril\jobs\tmp
set TMP=D:\mithril\jobs\tmp
set PY=C:\Python313\python.exe -I
set XW=D:\mithril\tools\xed-v2026.08.23-win\bin\xed.exe
set L=D:\mithril\tools\llvm-win-23.1.3\bin
set S=D:\mithril\x0\scripts
set O=D:\mithril\x0\smoke
for %%C in (A-msvc B-clangcl C-gcc D-clang) do (
  if exist %O%\%%C\smoke.obj (set OBJ=%O%\%%C\smoke.obj) else (set OBJ=%O%\%%C\smoke.o)
  %PY% %S%\x0_extract.py --readobj %L%\llvm-readobj.exe --label %%C -o %O%\%%C\manifest_win.json !OBJ!
  if exist %O%\%%C\decode_win rmdir /s /q %O%\%%C\decode_win
  %PY% %S%\x0_decode.py %O%\%%C\manifest_win.json -o %O%\%%C\decode_win --xed %XW% --objdump %L%\llvm-objdump.exe -j 8 > %O%\%%C\decode_win.log
  echo %%C_WIN_DECODE_RC=!ERRORLEVEL!
  %PY% %S%\runbook\compare_decodes.py %O%\%%C\decode %O%\%%C\decode_win
)
echo DONE
