@echo off
setlocal

pushd "%~dp0.."

set "OUTPUT_FILE=_output\ToneOZ-Quicksnow.ttf"
set "WOFF2_OUTPUT_FILE=_output\ToneOZ-Quicksnow.woff2"
set "PUBLISH_DIR=C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwidetest"
set "DEMO_DIR=src\demo_quicksnow"
set "IME_CLIENT_FONT_DIR=C:\Users\jeffreyx\Documents\git\peruse2021\client\font"
set "STATIC_OUTPUT_FILE=_output\static_instances\ToneOZ-Quicksnow-W450.ttf"
set "PUBLISH_STATIC_DIR1=C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwide_arplkaisimplified"
set "PUBLISH_STATIC_DIR2=C:\Users\jeffreyx\Documents\git\peruseFont_mengshen\res\fonts\varwide_arplkaitraditonal"
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

call C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONLEGACYWINDOWSSTDIO='1'; python3 src\py\ttf_to_woff2.py -input %OUTPUT_FILE% -output %WOFF2_OUTPUT_FILE%"
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
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

copy /Y "%WOFF2_OUTPUT_FILE%" "%DEMO_DIR%\"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

copy /Y "%WOFF2_OUTPUT_FILE%" "%IME_CLIENT_FONT_DIR%\"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

if not exist "%PUBLISH_STATIC_DIR1%" (
    mkdir "%PUBLISH_STATIC_DIR1%"
    if errorlevel 1 (
        set ERR=%errorlevel%
        popd
        exit /b %ERR%
    )
)

copy /Y "%STATIC_OUTPUT_FILE%" "%PUBLISH_STATIC_DIR1%\"
if errorlevel 1 (
    set ERR=%errorlevel%
    popd
    exit /b %ERR%
)

if not exist "%PUBLISH_STATIC_DIR2%" (
    mkdir "%PUBLISH_STATIC_DIR2%"
    if errorlevel 1 (
        set ERR=%errorlevel%
        popd
        exit /b %ERR%
    )
)

copy /Y "%STATIC_OUTPUT_FILE%" "%PUBLISH_STATIC_DIR2%\"

set ERR=%errorlevel%

popd

exit /b %ERR%
