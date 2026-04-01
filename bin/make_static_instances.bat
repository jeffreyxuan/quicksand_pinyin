@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\.."

C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\make_static_instances.py -input _output\ToneOZ-Quicksnow.ttf -output-dir _output\static_instances"

set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
