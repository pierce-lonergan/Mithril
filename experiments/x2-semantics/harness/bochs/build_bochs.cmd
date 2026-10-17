@echo off
rem build_bochs.cmd -- build Bochs 3.1 (official release asset bochs-3.1-msvc-src.zip, SHA-256
rem 3453bb34384ad30fcc4c3be76fd31632318431bad33fc917cb307b70364434b3, GitHub REL_3_1_FINAL) with the pinned
rem MSVC. The package's own config.h is used unchanged (configured by .conf.win64-vcpp: --enable-avx
rem --enable-evex --enable-x86-64 --enable-cpu-level=6 --enable-show-ips --with-nogui ...). Its VS2019 solution
rem asks for toolset v142; only v143 (MSVC 14.44) is installed, so the toolset is overridden.
rem At most 2 projects build in parallel and no project uses /MP, so at most 2 compiler processes run.
rem   cmd /c D:\mithril\x2\src\harness\bochs\build_bochs.cmd > D:\mithril\jobs\x2build\bochs_build.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d D:\mithril\src\bochs-3.1-msvc\bochs-3.1\vs2019
echo START %DATE% %TIME%
msbuild bochs.sln /nologo /v:minimal /m:2 /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.26100.0
echo MSBUILD_RC=%ERRORLEVEL%
echo END %DATE% %TIME%
dir /s /b D:\mithril\src\bochs-3.1-msvc\bochs-3.1\vs2019\*.exe
