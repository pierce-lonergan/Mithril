@echo off
rem x0prep: design-time ClCompile command lines of the A (Visual Studio generator) tree, from a diagnostic
rem MSBuild log of target GetClCommandLines (CLCommandLine task: builds command lines, runs no compiler).
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x0prep\tmp
set TMP=D:\mithril\jobs\x0prep\tmp
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
set C=D:\mithril\x0prep\cfg\A-vs
set F=D:\mithril\x0prep\flags
msbuild %C%\hearth_core.vcxproj -t:GetClCommandLines -p:Configuration=Release -p:Platform=x64 -p:DesignTimeBuild=true -p:BuildProjectReferences=false -m:1 -nologo -v:diag > %F%\A-vs.GetClCommandLines.diag.log 2>&1
echo GETCL_DIAG_RC=%ERRORLEVEL%
copy /y %C%\hearth_core.vcxproj %F%\A-vs.hearth_core.vcxproj >nul
certutil -hashfile %F%\A-vs.hearth_core.vcxproj SHA256
echo objects under A-vs (expect only CMake's own probes):
dir /s /b %C%\*.obj 2>nul
