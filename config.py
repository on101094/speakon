"""Settings, choices and paths shared by the app and its window."""

from pathlib import Path

APP_NAME = "SpeakOn"
VERSION = "3.0.0"
# Not %APPDATA%: apps started from sandboxed hosts (MSIX) get a private, redirected copy of it.
DATA_DIR = Path.home() / APP_NAME
MODELS_DIR = DATA_DIR / "models"
AUDIO_DIR = DATA_DIR / "recordings"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_FILE = DATA_DIR / "history.json"
DICTIONARY_FILE = DATA_DIR / "dictionary.txt"
LEARNED_FILE = DATA_DIR / "learned.json"
KEEP_RECORDINGS = 30

# A shortcut is a list of key names that must all be held.
#   generic modifiers: ctrl, alt, shift, win  (either side)
#   one side only:     ctrl_r, ctrl_l, alt_r, alt_l, shift_r, shift_l, win_l, win_r
#   other keys:        f1..f24, caps_lock, scroll_lock, pause, insert, space, ...
#   mouse buttons:     mouse_x1 (back), mouse_x2 (forward), mouse_middle
HOTKEY_PRESETS = {
    "ctrl_win": ("Ctrl + Win", ["ctrl", "win"], "Wispr Flow's key"),
    "ctrl_alt": ("Ctrl + Alt", ["ctrl", "alt"], ""),
    "alt_win": ("Alt + Win", ["alt", "win"], ""),
    "ctrl_shift": ("Ctrl + Shift", ["ctrl", "shift"], ""),
    "ctrl_r": ("Right Ctrl", ["ctrl_r"], ""),
    "alt_r": ("Right Alt", ["alt_r"], "not for keyboards where it is AltGr"),
    "shift_r": ("Right Shift", ["shift_r"], ""),
    "caps_lock": ("Caps Lock", ["caps_lock"], ""),
    "f8": ("F8", ["f8"], ""),
    "f9": ("F9", ["f9"], ""),
    "f10": ("F10", ["f10"], ""),
    "f13": ("F13", ["f13"], "extra key on some keyboards"),
    "scroll_lock": ("Scroll Lock", ["scroll_lock"], ""),
    "pause": ("Pause", ["pause"], ""),
    "insert": ("Insert", ["insert"], ""),
    "mouse_x1": ("Mouse back button", ["mouse_x1"], "side button"),
    "mouse_x2": ("Mouse forward button", ["mouse_x2"], "side button"),
    "mouse_middle": ("Mouse middle button", ["mouse_middle"], "wheel click"),
}

NICE = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win", "ctrl_r": "Right Ctrl",
        "ctrl_l": "Left Ctrl", "alt_r": "Right Alt", "alt_l": "Left Alt", "shift_r": "Right Shift",
        "shift_l": "Left Shift", "win_l": "Left Win", "win_r": "Right Win", "caps_lock": "Caps Lock",
        "scroll_lock": "Scroll Lock", "mouse_x1": "Mouse back", "mouse_x2": "Mouse forward",
        "mouse_middle": "Mouse middle", "space": "Space", "insert": "Insert", "pause": "Pause",
        "page_up": "Page Up", "page_down": "Page Down", "home": "Home", "end": "End", "menu": "Menu"}


def combo_label(keys):
    return " + ".join(NICE.get(k, k.upper() if len(k) <= 3 else k.replace("_", " ").title()) for k in keys)


MODES = {
    "smart": "Hold to talk, or tap to start and tap again to stop",
    "hold": "Hold to talk",
    "toggle": "Tap to start, tap to stop",
}
PASTE_METHODS = {
    "auto": "Automatic",
    "ctrl_v": "Paste (Ctrl+V)",
    "shift_insert": "Paste (Shift+Insert)",
    "type": "Type the characters",
}
LANGUAGES = {
    "auto": "Auto-detect", "en": "English", "he": "Hebrew", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "uk": "Ukrainian", "pl": "Polish", "tr": "Turkish", "ar": "Arabic", "hi": "Hindi",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
}
DEFAULT_SETTINGS = {
    "hotkey": "ctrl_win",
    "custom_hotkey": [],
    "mode": "smart",
    "model": "parakeet-v2",
    "language": "auto",
    "mic": None,
    "paste_method": "auto",
    "restore_clipboard": True,
    "trailing_space": True,
    "live_preview": True,
    "sounds": True,
    "remove_fillers": True,
    "fuzzy_words": True,
    "spoken_commands": False,
    "keep_recordings": True,
    "learn_from_edits": True,
    "start_with_windows": False,
    "name": "",
    "theme": "system",
    "always_show_bar": True,
}


def hotkey_keys(settings):
    if settings.get("hotkey") == "custom" and settings.get("custom_hotkey"):
        return list(settings["custom_hotkey"])
    return HOTKEY_PRESETS.get(settings.get("hotkey"), HOTKEY_PRESETS["ctrl_win"])[1]


def hotkey_label(settings):
    return combo_label(hotkey_keys(settings))


def list_microphones():
    import sounddevice as sd
    mics = []
    try:
        default_api = sd.query_hostapis(sd.default.hostapi)["name"]
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and sd.query_hostapis(d["hostapi"])["name"] == default_api:
                mics.append((i, d["name"]))
    except Exception:
        pass
    return mics
