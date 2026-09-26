"""Type text into the focused app with Windows SendInput, fast.

Each character is sent as a Unicode key event (KEYEVENTF_UNICODE), many per
SendInput call, so 200 characters take a few milliseconds instead of the
~0.5 s that one-call-per-key typing costs - and the clipboard is untouched.
Characters outside the Basic Multilingual Plane (emoji) are sent as their two
UTF-16 halves, which Unicode-aware controls recombine. Newlines are left to
the caller (they go through the clipboard, since a typed Enter would send
messages in chat apps).
"""

import ctypes
import time
from ctypes import wintypes

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


_SendInput = ctypes.windll.user32.SendInput
_SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
_SendInput.restype = wintypes.UINT

CHUNK = 48            # characters per call; slower apps (terminals, Electron) keep up with small bursts
PAUSE = 0.004


def type_text(text):
    """Returns the number of events Windows accepted (0 can mean the target runs as administrator)."""
    units = text.encode("utf-16-le")
    codes = [int.from_bytes(units[i:i + 2], "little") for i in range(0, len(units), 2)]
    sent = 0
    for start in range(0, len(codes), CHUNK):
        part = codes[start:start + CHUNK]
        arr = (INPUT * (len(part) * 2))()
        for i, c in enumerate(part):
            for j, flags in enumerate((KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)):
                ev = arr[i * 2 + j]
                ev.type = INPUT_KEYBOARD
                ev.u.ki = KEYBDINPUT(0, c, flags, 0, 0)
        sent += _SendInput(len(arr), arr, ctypes.sizeof(INPUT))
        if start + CHUNK < len(codes):
            time.sleep(PAUSE)
    return sent
