@echo off
setlocal

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1

pushd "%~dp0.."
python3 src\py\ff_fix_cmap.py -input "_output\Quicksand-Regular_pinyin.ttf" -output "_output\Quicksand-Regular_pinyin.ttf" --otfccbuild otfccbuild.exe
set ERR=%errorlevel%
popd

exit /b %ERR%
