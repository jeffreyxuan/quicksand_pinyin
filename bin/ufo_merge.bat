@echo off
setlocal

pushd "%~dp0.."

set "OUTPUT_FILE=_output\ToneOZ-Quicksnow.ttf"
set "PUBLISH_DIR=C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest"

call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\ufo_merge.py -input src\ufo -with res\Quicksand-VariableFont_wght.ttf -output %OUTPUT_FILE%"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

if not exist "%PUBLISH_DIR%" (
    mkdir "%PUBLISH_DIR%"
    if errorlevel 1 (
        set ERR=%errorlevel%
        popd
        exit /b %ERR%
    )
)

copy /Y "%OUTPUT_FILE%" "%PUBLISH_DIR%\"

set ERR=%errorlevel%

popd

exit /b %ERR%
