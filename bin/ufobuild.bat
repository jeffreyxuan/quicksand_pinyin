@echo off
setlocal

pushd "%~dp0.."

set "INPUT_UFO=src\ToneOZ_Quicksnow_UFO"
set "OUTPUT_TTF=_output\ToneOZ-Quicksnow.ttf"

if not "%~1"=="" (
    set "INPUT_UFO=%~1"
)

if not "%~2"=="" (
    set "OUTPUT_TTF=%~2"
)

call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\varwideufo\varwideufo.py -input %INPUT_UFO% -output %OUTPUT_TTF%"
set ERR=%errorlevel%

popd

exit /b %ERR%
