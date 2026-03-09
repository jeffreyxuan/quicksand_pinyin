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

popd

echo Done.
