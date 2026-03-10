@echo off
setlocal

if "%~1"=="" exit /b 2
if "%~2"=="" exit /b 2

set TTF_AUTOHINT=C:\tool\ttfautohint\ttfautohint.exe

pushd "%~dp0.."
"%TTF_AUTOHINT%" "%~1" "%~2"
set ERR=%errorlevel%
popd

exit /b %ERR%
