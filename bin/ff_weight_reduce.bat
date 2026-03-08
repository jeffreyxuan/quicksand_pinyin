@echo off
setlocal

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1

python3 src\py\ff_weight_reduce.py -input src\ff\Quicksand-Medium_pinyin.sfd -output _output\Quicksand-Medium_pinyin_weightadd-16.ttf --fontforge-bin "C:\Program Files (x86)\FontForgeBuilds\bin\fontforge.exe"
if errorlevel 1 exit /b %errorlevel%

if not exist "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest" (
    mkdir "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest"
)

copy /Y "_output\Quicksand-Medium_pinyin_weightadd-16.ttf" "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest\Quicksand-Medium_pinyin_weightadd-16.ttf"
if errorlevel 1 exit /b %errorlevel%

echo Done.


