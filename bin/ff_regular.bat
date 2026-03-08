@echo off
setlocal

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1

pushd "%~dp0.."
python3 src\py\ff_regulay.py
if errorlevel 1 (
    popd
    exit /b %errorlevel%
)

if not exist "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest" (
    mkdir "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest"
)

copy /Y "_output\Quicksand-Regular_pinyin.ttf" "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest\Quicksand-Regular_pinyin.ttf"
set COPY_ERR=%errorlevel%

popd
if %COPY_ERR% neq 0 exit /b %COPY_ERR%

echo Done.
