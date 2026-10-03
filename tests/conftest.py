"""Shared test setup.

On Windows (and in CI) the real modules are imported. Elsewhere, the Windows-only modules are
replaced with stand-ins so the data-handling code (store, learn, the window's API) can still be
tested; nothing that needs a real microphone, keyboard hook or window is exercised here."""

import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.platform != "win32":
    import ctypes
    ctypes.windll = mock.MagicMock()
    ctypes.WinDLL = mock.MagicMock()
    ctypes.WINFUNCTYPE = mock.MagicMock()
    for name in ["winreg", "winsound", "pyperclip", "pystray", "sounddevice", "webview", "PIL", "PIL.Image",
                 "pynput", "pynput.keyboard", "pynput.mouse", "uiautomation",
                 "hotkeys", "mic", "overlay", "sendinput"]:   # the last four use Win32 at import time
        sys.modules.setdefault(name, mock.MagicMock())

import config as C  # noqa: E402


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point every data file at an empty temporary folder."""
    for attr, name in [("DATA_DIR", ""), ("SETTINGS_FILE", "settings.json"), ("HISTORY_FILE", "history.json"),
                       ("DICTIONARY_FILE", "dictionary.txt"), ("LEARNED_FILE", "learned.json")]:
        monkeypatch.setattr(C, attr, tmp_path / name if name else tmp_path)
    return tmp_path
