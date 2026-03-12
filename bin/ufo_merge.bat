@echo off
setlocal

pushd "%~dp0.."

call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\ufo_merge.py -input src\ufo -with res\Quicksand-VariableFont_wght.ttf -output _output\ToneOZ-Quicksnow.ttf"
set ERR=%errorlevel%

popd

exit /b %ERR%
