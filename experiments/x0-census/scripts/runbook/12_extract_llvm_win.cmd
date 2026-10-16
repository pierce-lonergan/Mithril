@echo off
set CUDA_VISIBLE_DEVICES=-1
echo START %DATE% %TIME%
mkdir D:\mithril\tools\llvm-win-23.1.3
tar.exe -x -f D:\mithril\tools\dl\clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz --strip-components 1 -C D:\mithril\tools\llvm-win-23.1.3
set RC=%ERRORLEVEL%
echo END %DATE% %TIME% rc=%RC%
echo %RC% > D:\mithril\jobs\x_win.rc
