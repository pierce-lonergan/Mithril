@echo off
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\tmp
set TMP=D:\mithril\jobs\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
echo START %DATE% %TIME%
cd /d D:\mithril\src\xed
C:\Python313\python.exe -B mfile.py --compiler=ms -j 8 --build-dir=D:\mithril\src\xed-build-win --install-dir=D:\mithril\tools\xed-v2026.08.23-win install examples
set RC=%ERRORLEVEL%
echo END %DATE% %TIME% rc=%RC%
echo %RC% > D:\mithril\jobs\xedwin.rc
