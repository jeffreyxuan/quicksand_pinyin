@echo off
setlocal

set TTF_AUTOHINT=C:\tool\ttfautohint\ttfautohint.exe
set INPUT_FONT=_output\Quicksand-Regular_pinyin.ttf
set OUTPUT_FONT=_output\Quicksand-Regular_pinyin_rehint.ttf

pushd "%~dp0.."
"%TTF_AUTOHINT%" "%INPUT_FONT%" "%OUTPUT_FONT%"
set ERR=%errorlevel%
popd

exit /b %ERR%
