@echo off
setlocal

call "%~dp0ff_weight_reduce.bat"
exit /b %errorlevel%
