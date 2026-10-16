@echo off
setlocal
set CUDA_VISIBLE_DEVICES=-1
set DL=D:\mithril\tools\dl
set BASE=https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.3
cd /d %DL%
echo START %DATE% %TIME%
for %%F in (clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz.sig clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz.jsonl LLVM-23.1.3-Linux-X64.tar.xz.sig LLVM-23.1.3-Linux-X64.tar.xz.jsonl) do (
  curl.exe -sS -L --fail --retry 3 -o "%%F" "%BASE%/%%F" || echo FAIL %%F
)
curl.exe -sS -L --fail --retry 3 -o release-keys.asc https://releases.llvm.org/release-keys.asc || echo FAIL keys
curl.exe -sS -L --fail --retry 3 -o clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz "%BASE%/clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz" || echo FAIL win
echo WIN_DONE %DATE% %TIME%
curl.exe -sS -L --fail --retry 3 -o LLVM-23.1.3-Linux-X64.tar.xz "%BASE%/LLVM-23.1.3-Linux-X64.tar.xz" || echo FAIL linux
echo LINUX_DONE %DATE% %TIME%
dir %DL%
echo 0 > D:\mithril\jobs\dl_llvm.rc
