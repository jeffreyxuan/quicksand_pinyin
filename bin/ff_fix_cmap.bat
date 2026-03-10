@echo off
setlocal

if "%~1"=="" exit /b 2
if "%~2"=="" exit /b 2

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1

pushd "%~dp0.."
python3 src\py\ff_fix_cmap.py -input "%~1" -output "%~2" --otfccbuild otfccbuild.exe
set ERR=%errorlevel%
popd

exit /b %ERR%
