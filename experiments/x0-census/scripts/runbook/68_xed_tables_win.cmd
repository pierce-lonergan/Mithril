@echo off
rem x0prep: build and run the XED table dumper (1 thread). Not Hearth code.
setlocal
set CUDA_VISIBLE_DEVICES=-1
if not exist D:\mithril\jobs\x0prep\tmp mkdir D:\mithril\jobs\x0prep\tmp
set TEMP=D:\mithril\jobs\x0prep\tmp
set TMP=D:\mithril\jobs\x0prep\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set K=D:\mithril\tools\xed-v2026.08.23-win
set W=D:\mithril\x0prep\xedtab
cd /d %W%
cl.exe /nologo /O1 /MT /I%K%\include xed_tables.c /Fe:%W%\xed_tables.exe /link %K%\lib\xed.lib
echo BUILD_RC=%ERRORLEVEL%
%W%\xed_tables.exe > %W%\xed_tables.tsv
echo RUN_RC=%ERRORLEVEL%
certutil -hashfile %W%\xed_tables.tsv SHA256
