@echo off
setlocal

pushd "%~dp0.."

set "AUTO_COPY=0"
if /I "%~1"=="-y" (
    set "AUTO_COPY=1"
)

call :convert_font "res\Quicksand-VariableFont_wght.ttf" "src\_ToneOZ_Quicksnow_UFO" "src\ToneOZ_Quicksnow_UFO"
if errorlevel 1 (
    set "ERR=%errorlevel%"
    popd
    exit /b %ERR%
)

call :convert_font "res\NotoSans-VariableFont_wdth,wght.ttf" "src\_NotoSans-VariableFont_wdth,wght_UFO" "src\NotoSans-VariableFont_wdth,wght_UFO"
if errorlevel 1 (
    set "ERR=%errorlevel%"
    popd
    exit /b %ERR%
)

set "ERR=0"

popd

exit /b %ERR%

:convert_font
set "INPUT_FILE=%~1"
set "TEMP_OUTPUT=%~2"
set "FINAL_OUTPUT=%~3"

if exist "%TEMP_OUTPUT%" (
    rmdir /S /Q "%TEMP_OUTPUT%"
)

call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\varwideufo\varwideufo.py -input %INPUT_FILE% -output %TEMP_OUTPUT%"
if errorlevel 1 (
    exit /b %errorlevel%
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
        exit /b %errorlevel%
    )
)

exit /b 0
