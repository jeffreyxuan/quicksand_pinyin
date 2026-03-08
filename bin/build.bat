@echo off
setlocal

call "%~dp0ff_regular.bat"
if errorlevel 1 exit /b %errorlevel%

call "%~dp0ff_fix_cmap.bat"
if errorlevel 1 exit /b %errorlevel%

call "%~dp0ff_weight_reduce.bat"
if errorlevel 1 exit /b %errorlevel%

exit /b 0
