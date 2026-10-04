import sys
import threading

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="hotkeys.py uses Win32 at import time")


def test_left_side_shortcuts_match_the_generic_key_name():
    import hotkeys
    for side, generic in [("shift_l", "shift"), ("ctrl_l", "ctrl"), ("alt_l", "alt"), ("win_l", "cmd")]:
        assert hotkeys.matches(side, generic)
        assert hotkeys.matches(side, side if side != "win_l" else "cmd_l")
    assert not hotkeys.matches("shift_l", "shift_r")
    assert not hotkeys.matches("ctrl_r", "ctrl")


def test_recorded_left_shift_alone_triggers():
    import hotkeys
    w = hotkeys.HotkeyWatcher(on_down=lambda: None, on_up=lambda: None, on_other=lambda: None, on_esc=lambda: None)
    c = w.capture = {"held": set(), "seen": [], "done": threading.Event()}   # start_capture() minus the mouse hook
    w._capture("shift", True)
    w._capture("shift", False)
    assert c["result"] == ["shift_l"]
    w.set_combo(c["result"])
    w.pressed = {"shift"}
    assert w._is_active()
