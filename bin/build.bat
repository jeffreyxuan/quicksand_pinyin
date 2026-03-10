@echo off
setlocal

pushd "%~dp0.."

set "INPUT_FILEPATH=src\ff\Quicksand-Regular_pinyin.sfd"
for %%I in ("%INPUT_FILEPATH%") do set "INPUT_FILENAME=%%~nI"

set "INIT_OUTPUT=_output\%INPUT_FILENAME%_init.ttf"
set "FIX_CMAP_OUTPUT=_output\%INPUT_FILENAME%_fix_cmap.ttf"
set "REHINT_OUTPUT=_output\%INPUT_FILENAME%_rehint.ttf"
set "RENAME_OUTPUT=_output\%INPUT_FILENAME%_rename.ttf"
set "WEIGHT_REDUCE_OUTPUT=_output\%INPUT_FILENAME%_weightadd-16.ttf"
set "FINAL_OUTPUT=_output\%INPUT_FILENAME%.ttf"

call "%~dp0ff_regular.bat" "%INPUT_FILEPATH%" "%INIT_OUTPUT%"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

call "%~dp0ff_fix_cmap.bat" "%INIT_OUTPUT%" "%FIX_CMAP_OUTPUT%"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

call "%~dp0ff_rehint.bat" "%FIX_CMAP_OUTPUT%" "%REHINT_OUTPUT%"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

call "%~dp0ff_rename.bat" "%REHINT_OUTPUT%" "%RENAME_OUTPUT%"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

call "%~dp0ff_weight_reduce.bat" "%RENAME_OUTPUT%" "%WEIGHT_REDUCE_OUTPUT%"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

copy /Y "%RENAME_OUTPUT%" "%FINAL_OUTPUT%"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

if not exist "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest" (
    mkdir "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest"
)

copy /Y "%FINAL_OUTPUT%" "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest\%INPUT_FILENAME%.ttf"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

popd

exit /b 0
