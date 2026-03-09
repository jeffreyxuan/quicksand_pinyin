@echo off
setlocal

call "%~dp0ff_regular.bat"
if errorlevel 1 exit /b %errorlevel%

call "%~dp0ff_fix_cmap.bat"
if errorlevel 1 exit /b %errorlevel%

call "%~dp0ff_rehint.bat"
if errorlevel 1 exit /b %errorlevel%

call "%~dp0ff_rename.bat"
if errorlevel 1 exit /b %errorlevel%

call "%~dp0ff_weight_reduce.bat"
if errorlevel 1 exit /b %errorlevel%

copy /Y "_output\Quicksand-Regular_pinyin_renamed.ttf" "_output\Quicksand-Regular_pinyin.ttf"
if errorlevel 1 exit /b %errorlevel%

if not exist "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest" (
    mkdir "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest"
)

copy /Y "_output\Quicksand-Regular_pinyin_renamed.ttf" "C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest\Quicksand-Regular_pinyin.ttf"
if errorlevel 1 exit /b %errorlevel%

exit /b 0
