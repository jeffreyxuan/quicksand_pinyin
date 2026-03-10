@echo off
setlocal

pushd "%~dp0.."

call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\varwideufo\varwideufo.py -input src\ToneOZ_Quicksnow_UFO -output _output\ToneOZ-Quicksnow.ttf"
set ERR=%errorlevel%

popd

exit /b %ERR%
