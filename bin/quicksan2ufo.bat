@echo off
setlocal

pushd "%~dp0.."

set "AUTO_COPY=0"
if /I "%~1"=="-y" (
    set "AUTO_COPY=1"
)

set "TEMP_OUTPUT=src\_ToneOZ_Quicksnow_UFO"
set "FINAL_OUTPUT=src\ToneOZ_Quicksnow_UFO"

if exist "%TEMP_OUTPUT%" (
    rmdir /S /Q "%TEMP_OUTPUT%"
)

call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\varwideufo\varwideufo.py -input res\Quicksand-VariableFont_wght.ttf -output src\_ToneOZ_Quicksnow_UFO"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

set "DO_COPY=0"
if "%AUTO_COPY%"=="1" (
    set "DO_COPY=1"
) else (
    choice /M "Copy %TEMP_OUTPUT% to %FINAL_OUTPUT% ?"
    if errorlevel 2 (
        set "DO_COPY=0"
    ) else (
        set "DO_COPY=1"
    )
)

if "%DO_COPY%"=="1" (
    if exist "%FINAL_OUTPUT%" (
        rmdir /S /Q "%FINAL_OUTPUT%"
    )
    xcopy "%TEMP_OUTPUT%" "%FINAL_OUTPUT%\" /E /I /Y >nul
    if errorlevel 1 (
        set ERR=%errorlevel%
        popd
        exit /b %ERR%
    )
)

set ERR=0

popd

exit /b %ERR%
