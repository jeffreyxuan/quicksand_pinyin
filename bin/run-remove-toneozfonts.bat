@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Remove-ToneozFonts.ps1"
endlocal