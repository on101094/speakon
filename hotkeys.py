"""Global push-to-talk watcher: single keys, key combinations (Ctrl+Win) and mouse buttons.

Runs on pynput's own listener threads and only posts events, so the Windows
low-level hook never times out (murmur's rule). Nothing is swallowed: the keys
still reach other apps, which is why a combination with Win sends a harmless
"mask" key while held - otherwise releasing Win would pop open the Start menu
(the same trick AutoHotkey uses).
"""

import ctypes
import threading

from pynput import keyboard, mouse

user32 = ctypes.windll.user32
MASK_VK = 0xE8          # unassigned virtual key

_SIDES = {
    "ctrl": {"ctrl", "ctrl_l", "ctrl_r"},
    "alt": {"alt", "alt_l", "alt_r", "alt_gr"},
    "shift": {"shift", "shift_l", "shift_r"},
    "win": {"cmd", "cmd_l", "cmd_r", "win_l", "win_r"},
    "win_l": {"cmd", "cmd_l", "win_l"},
    "win_r": {"cmd_r", "win_r"},
    "alt_r": {"alt_r", "alt_gr"},
}
_GENERIC = {"ctrl_l": "ctrl", "ctrl_r": "ctrl", "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
            "shift_l": "shift", "shift_r": "shift", "cmd": "win", "cmd_l": "win", "cmd_r": "win"}
_PUBLIC = {"cmd": "win_l", "cmd_l": "win_l", "cmd_r": "win_r", "alt_gr": "alt_r", "ctrl": "ctrl_l",
           "alt": "alt_l", "shift": "shift_l"}


_VK = {"ctrl": 0x11, "ctrl_l": 0xA2, "ctrl_r": 0xA3, "alt": 0x12, "alt_l": 0xA4, "alt_r": 0xA5,
       "alt_gr": 0xA5, "shift": 0x10, "shift_l": 0xA0, "shift_r": 0xA1, "cmd": 0x5B, "cmd_l": 0x5B,
       "cmd_r": 0x5C, "mouse_x1": 0x05, "mouse_x2": 0x06, "mouse_middle": 0x04}


def key_name(key):
    if isinstance(key, keyboard.Key):
        return key.name
    vk = getattr(key, "vk", None)
    if vk == MASK_VK:
        return "mask"
    if getattr(key, "char", None):
        return key.char.lower()
    return f"vk{vk}" if vk is not None else "unknown"


def matches(spec, name):
    return name in _SIDES.get(spec, {spec})


class HotkeyWatcher:
    def __init__(self, on_down, on_up, on_other, on_esc):
        self.on_down, self.on_up, self.on_other, self.on_esc = on_down, on_up, on_other, on_esc
        self.combo = ["ctrl", "win"]
        self.pressed = set()
        self.active = False
        self.paused = False          # while we inject our own keys
        self.capture = None          # recording a new shortcut
        self.kb = keyboard.Listener(on_press=self._press, on_release=self._release)
        self.ms = mouse.Listener(on_click=self._click)

    def start(self):
        self.kb.start()
        self.ms.start()

    def stop(self):
        self.kb.stop()
        self.ms.stop()

    def set_combo(self, keys):
        self.combo = list(keys)
        self.active = False

    def _is_active(self):
        return all(any(matches(spec, k) for k in self.pressed) for spec in self.combo)

    def _prune(self, current):
        """Forget keys whose release we missed (e.g. after Win+L locks the screen)."""
        for n in list(self.pressed):
            vk = _VK.get(n)
            if n != current and vk and not (user32.GetAsyncKeyState(vk) & 0x8000):
                self.pressed.discard(n)

    def _update(self, name, down):
        self._prune(name)
        was = self.active
        if down:
            self.pressed.add(name)
        else:
            self.pressed.discard(name)
        now = self._is_active()
        self.active = now
        if now and not was:
            if any(matches("win", k) for k in self.pressed):
                self._mask()
            self.on_down()
        elif was and not now:
            self.on_up()
        elif down and now and not any(matches(spec, name) for spec in self.combo):
            self.on_other()          # e.g. Ctrl+Win+D: a Windows shortcut, not dictation

    def _mask(self):
        user32.keybd_event(MASK_VK, 0, 0, 0)
        user32.keybd_event(MASK_VK, 0, 2, 0)

    # ----- capture a new shortcut
    def start_capture(self):
        self.capture = {"held": set(), "seen": [], "done": threading.Event()}
        return self.capture

    def _capture(self, name, down):
        c = self.capture
        if down:
            c["held"].add(name)
            if name not in c["seen"]:
                c["seen"].append(name)
        else:
            c["held"].discard(name)
            if not c["held"] and c["seen"]:
                seen = c["seen"]
                if len(seen) > 1:          # combinations: either side of a modifier works
                    seen = [_GENERIC.get(k, k) for k in seen]
                else:
                    seen = [_PUBLIC.get(k, k) for k in seen]
                order = ["ctrl", "alt", "shift", "win"]
                seen = sorted(dict.fromkeys(seen), key=lambda k: order.index(k) if k in order else 9)
                c["result"] = seen
                self.capture = None
                c["done"].set()

    # ----- listener callbacks (their own threads)
    def _press(self, key):
        name = key_name(key)
        if name == "mask" or self.paused:
            return
        if self.capture is not None:
            if name == "esc":
                self.capture["result"] = None
                self.capture["done"].set()
                self.capture = None
            else:
                self._capture(name, True)
            return
        if name == "esc":
            self.on_esc()
        if name in self.pressed:
            return                   # Windows auto-repeat
        self._update(name, True)

    def _release(self, key):
        name = key_name(key)
        if name == "mask" or self.paused:
            return
        if self.capture is not None:
            self._capture(name, False)
            return
        if name in self.pressed:
            self._update(name, False)

    def _click(self, x, y, button, pressed):
        name = {mouse.Button.x1: "mouse_x1", mouse.Button.x2: "mouse_x2",
                mouse.Button.middle: "mouse_middle"}.get(button)
        if name is None or self.paused:
            return
        if self.capture is not None:
            self._capture(name, pressed)
            return
        if pressed and name not in self.pressed:
            self._update(name, True)
        elif not pressed and name in self.pressed:
            self._update(name, False)
