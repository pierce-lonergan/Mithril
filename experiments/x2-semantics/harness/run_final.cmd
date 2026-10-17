@echo off
rem run_final.cmd -- the consolidated record run of this build: build, every self-test, the interpreter
rem validation, the development smoke (hand vectors only) and two throughput measurements that touch no
rem silicon: the C interpreter (predict mode and the exhaustive engine with the interpreter as oracle) and
rem the Python generator. At most 2 threads.
rem   cmd /c D:\mithril\x2\src\harness\run_final.cmd > D:\mithril\jobs\x2build\final.log 2>&1
setlocal
set CUDA_VISIBLE_DEVICES=-1
set TEMP=D:\mithril\jobs\x2build\tmp
set TMP=D:\mithril\jobs\x2build\tmp
set S=D:\mithril\x2\src
set H=%S%\harness
set B=D:\mithril\x2\build
set D=D:\mithril\x2\dev
set PY=C:\Python313\python.exe -I -B
echo ==== BUILD %DATE% %TIME%
call %H%\build.cmd
echo ==== SELFTESTS %TIME%
call %H%\run_selftests.cmd
echo ==== GUARDS %TIME%
call %H%\run_guards.cmd
echo ==== DEVSMOKE %TIME%
call %H%\run_devsmoke.cmd
echo ==== THROUGHPUT: C interpreter, predict mode on the validation vectors (1,000,006 lane cases) %TIME%
powershell -NoProfile -Command "$t = Measure-Command { & '%B%\x2fuzz.exe' predict '%D%\valid.vec' '%D%\valid.c2' | Out-Null }; 'predict_seconds=' + $t.TotalSeconds"
echo ==== THROUGHPUT: exhaustive engine, interpreter as oracle, VCVTPS2DQ zmm, 2^28 inputs, 1 thread %TIME%
%B%\x2fuzz.exe exhaustive --iform VCVTPS2DQ_ZMMi32_MASKmskw_ZMMf32_AVX512 --variant plain --mxcsr 1f80 --lo 0 --hi 10000000 --out D:\mithril\jobs\x2build\ex_tp --oracle self --threads 1
type D:\mithril\jobs\x2build\ex_tp\summary.json
echo ==== THROUGHPUT: Python generator, V1 of VADDPS zmm, first 20000 executions %TIME%
powershell -NoProfile -Command "$t = Measure-Command { & 'C:\Python313\python.exe' -I -B '%H%\gen_vectors.py' --sem-root '%S%' --manifest '%B%\stubs_manifest.json' --out '%D%\gen_tp.vec' --iform VADDPS_ZMMf32_MASKmskw_ZMMf32_ZMMf32_AVX512 --set V1 --dev --limit 20000 --label DEV-GEN-THROUGHPUT | Out-Host }; 'gen_seconds=' + $t.TotalSeconds"
echo ==== END %DATE% %TIME%
