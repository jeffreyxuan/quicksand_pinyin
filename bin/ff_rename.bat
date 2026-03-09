@echo off
setlocal

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1

pushd "%~dp0.."
python3 src\py\ff_rename.py -input _output\Quicksand-Regular_pinyin_rehint.ttf -output _output\Quicksand-Regular_pinyin_renamed.ttf -namejson src\json\name_Quicksand-Regular.json
set ERR=%errorlevel%
popd

exit /b %ERR%
