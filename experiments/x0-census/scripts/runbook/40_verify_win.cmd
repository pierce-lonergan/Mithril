@echo off
rem X0 runbook step 40: verify LLVM 23.1.3 for Windows (clang-cl, clang, llvm-objdump, llvm-readobj)
rem and record how clang-cl and cl map /fp:* and /arch:*.
rem Run on the desktop:  cmd /c D:\mithril\x0\scripts\runbook\40_verify_win.cmd > D:\mithril\jobs\40_verify_win.log 2>&1
setlocal enabledelayedexpansion
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\tmp mkdir D:\mithril\jobs\tmp
set TEMP=D:\mithril\jobs\tmp
set TMP=D:\mithril\jobs\tmp
set L=D:\mithril\tools\llvm-win-23.1.3\bin
set P=D:\mithril\x0\scripts\runbook\probes
set CC1=C:\Python313\python.exe -I D:\mithril\x0\scripts\runbook\cc1flags.py
set W=D:\mithril\x0\winverify
if not exist %W% mkdir %W%
cd /d %W%
echo ==== versions (before vcvars)
%L%\clang-cl.exe --version
%L%\clang.exe --version
%L%\llvm-objdump.exe --version | findstr /i "version"
%L%\llvm-readobj.exe --version | findstr /i "version"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
echo ==== vcvars VCToolsVersion=%VCToolsVersion% WindowsSDKVersion=%WindowsSDKVersion%
where cl.exe
cl.exe 2>&1 | findstr /i "Version"
echo ==== clang-cl: compile+link+run against MSVC headers/libs from vcvars
%L%\clang-cl.exe /nologo /O2 /arch:AVX2 %P%\hello_avx2.c /Fe:%W%\hello_clangcl.exe /Fo:%W%\hello_clangcl.obj
echo clang-cl rc=!ERRORLEVEL!
%W%\hello_clangcl.exe
echo run rc=!ERRORLEVEL!
echo ==== cl: compile+link+run
cl.exe /nologo /O2 /arch:AVX2 %P%\hello_avx2.c /Fe:%W%\hello_cl.exe /Fo:%W%\hello_cl.obj
%W%\hello_cl.exe
echo run rc=!ERRORLEVEL!
echo ==== clang-cl -### : cc1 FP/ISA flags per driver option set
for %%F in ("" "/fp:precise" "/fp:strict" "/fp:fast" "/fp:precise /fp:contract" "/O2 /fp:precise" "/O2 /fp:precise /arch:AVX2" "/O2 /fp:precise /arch:AVX512" "/O2 /fp:precise /clang:-ffp-contract=off") do (
  echo [clang-cl %%~F]
  %L%\clang-cl.exe %%~F -### -c %P%\fpc.c 2>&1 | %CC1%
)
echo ==== /experimental:c11atomics under clang-cl
%L%\clang-cl.exe /nologo /std:c11 /experimental:c11atomics -### -c %P%\atomic_probe.c 2>&1 | findstr /i /c:"warning:" /c:"error:"
echo ==== a*b+c codegen (fpc.c): FMA contraction or not
for %%F in ("/O2 /fp:precise /arch:AVX2" "/O2 /fp:precise /arch:AVX512" "/O2 /fp:precise /arch:AVX2 /clang:-ffp-contract=off" "/O2 /fp:precise /arch:AVX2 -ffp-contract=off" "/O2 /fp:strict /arch:AVX2") do (
  echo [clang-cl %%~F]
  %L%\clang-cl.exe /nologo %%~F /FA /Fa%W%\fpc.asm /c %P%\fpc.c /Fo%W%\fpc.obj 2>&1
  findstr /i /r "vfmadd vmulss vaddss" %W%\fpc.asm
)
for %%F in ("/O2 /fp:precise /arch:AVX2" "/O2 /fp:precise /arch:AVX512" "/O2 /fp:precise /fp:contract /arch:AVX2") do (
  echo [cl %%~F]
  cl.exe /nologo %%~F /FA /Fa%W%\fpc.asm /c %P%\fpc.c /Fo%W%\fpc.obj 2>&1 | findstr /v /i "fpc.c"
  findstr /i /r "vfmadd vmulss vaddss" %W%\fpc.asm
)
echo ==== cl /? : /fp options
cl.exe /? 2>&1 | findstr /i /c:"fp:"
echo DONE
