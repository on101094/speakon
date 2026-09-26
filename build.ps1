# Builds dist\SpeakOn\SpeakOn.exe (no Python needed to run it).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& .\.venv\Scripts\python -m PyInstaller --noconfirm --clean --windowed --name SpeakOn `
    --icon assets\icon.ico `
    --add-data "assets;assets" --add-data "ui;ui" `
    --collect-all onnx_asr --collect-all faster_whisper --collect-all ctranslate2 `
    --collect-binaries onnxruntime --collect-data onnxruntime `
    --collect-all webview --collect-all uiautomation --collect-all comtypes `
    --hidden-import pystray._win32 --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 `
    --hidden-import clr `
    speakon.py
