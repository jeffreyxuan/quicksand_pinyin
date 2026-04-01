@echo off
setlocal

pushd "%~dp0.."

set "OUTPUT_FILE=_output\ToneOZ-Quicksnow.ttf"
set "PUBLISH_DIR=C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest"
set "ANCHOR_SFD=src\ufo\anchor\ToneOZ-Quicksnow_anchor.sfd"
set "ANCHOR_W300_SFD=src\ufo\anchor\ToneOZ-Quicksnow-W300_anchor.sfd"
set "ANCHOR_W700_SFD=src\ufo\anchor\ToneOZ-Quicksnow-W700_anchor.sfd"
set "ANCHOR_JSON=src\json\fonttool_fix_anchor_rules.json"

if exist "%ANCHOR_SFD%" (
    call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\extract_sfd_anchors.py -input %ANCHOR_SFD% -output %ANCHOR_JSON%"
    if errorlevel 1 (
        set ERR=%errorlevel%
        popd
        exit /b %ERR%
    )
) else (
    if not exist "%ANCHOR_W300_SFD%" if not exist "%ANCHOR_W700_SFD%" (
        echo Warning: no anchor SFD found. Continuing without anchor export.
    )
)

call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\ufo_merge.py -input src\ufo -with res\Quicksand-VariableFont_wght.ttf -output %OUTPUT_FILE%"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

call bin\make_static_instances.bat
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

if not exist "%PUBLISH_DIR%" (
    mkdir "%PUBLISH_DIR%"
    if errorlevel 1 (
        set ERR=%errorlevel%
        popd
        exit /b %ERR%
    )
)

copy /Y "%OUTPUT_FILE%" "%PUBLISH_DIR%\"

set ERR=%errorlevel%

popd

exit /b %ERR%
