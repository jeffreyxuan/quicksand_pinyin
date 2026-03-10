@echo off
setlocal

if "%~1"=="" exit /b 2
if "%~2"=="" exit /b 2

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1

pushd "%~dp0.."
python3 src\py\ff_weight_reduce.py -input "%~1" -output "%~2" --fontforge-bin "C:\Program Files (x86)\FontForgeBuilds\bin\fontforge.exe"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

if not exist "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest" (
    mkdir "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest"
)

copy /Y "%~2" "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest\%~nx2"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

popd

echo Done.
