"""The window's API (speakon.Api) on top of a real Store and Learned, without starting the app."""

import json
import threading
import types
from unittest import mock

import pytest

import config as C
import learn
import speakon as S
import store
from learn import entry_id


@pytest.fixture
def app(data_dir):
    C.LEARNED_FILE.write_text(json.dumps({"fixes": [{"heard": "a", "wanted": "A", "count": 1, "enabled": True}],
                                          "terms": ["x"], "lowercase": ["and"]}))
    a = types.SimpleNamespace(store=store.Store(), learned=learn.Learned(C.LEARNED_FILE), levels=[0.0] * 3, level=0,
                              recording=False, busy=False, preview="", status="", learning={},
                              mic=mock.MagicMock(), keys=mock.MagicMock(), tray=mock.MagicMock(),
                              load_model=mock.MagicMock(), notify=lambda text: None, set_status=lambda text: None,
                              learn_corrections=lambda pairs, notify=True: pairs)
    a.settings = a.store.settings
    a.stats = lambda: S.SpeakOn.stats(a)
    a.update_setting = lambda key, value: S.SpeakOn.update_setting(a, key, value)
    return a


def test_history_actions_hit_the_entry_shown(app):
    api = S.Api(app)
    app.store.add_history({"time": "2026-10-03T10:00:00", "text": "hello"})
    hid = api.history()[0]["i"]
    app.store.add_history({"time": "2026-10-03T10:01:00", "text": "newer"})   # a dictation lands meanwhile
    with mock.patch.object(S, "pyperclip") as clip:
        api.copy(hid)
    clip.copy.assert_called_once_with("hello")
    with mock.patch.object(S, "find_corrections", return_value=[("hello", "Hallo")]) as find:
        assert api.edit_history(hid, "Hallo").startswith("Learned")
    assert find.call_args.args[2] == ["and"]
    assert app.store.history_text(hid) == "Hallo"
    api.delete_history(hid)
    assert [h["text"] for h in api.history()] == ["newer"]


def test_edit_of_deleted_dictation(app):
    assert S.Api(app).edit_history("gone", "x") == "That dictation no longer exists"


def test_state_reports_history_version(app):
    app.store.add_history({"time": "2026-10-03T10:00:00", "text": "a"})
    assert S.Api(app).state()["history_version"] == app.store.history_version


def test_dictionary_page(app):
    api = S.Api(app)
    app.store.set_dictionary("foo\n")
    rows = api.dictionary()
    assert [(r["write"], r["learned"]) for r in rows] == [("foo", False), ("A", True), ("x", True)]
    api.save_entry(rows[0]["id"], "Foo", "foo")
    assert app.store.dictionary == "foo -> Foo\n"
    api.save_entry(rows[1]["id"], "Ay", "a")                      # editing a learned fix moves it to the file
    assert app.store.dictionary.endswith("a -> Ay\n")
    assert app.learned.data["fixes"][0]["enabled"] is False
    api.delete_entry(entry_id("d", "foo -> Foo"))
    assert "Foo" not in app.store.dictionary
    api.delete_entry(next(r["id"] for r in api.dictionary() if r["write"] == "x"))
    assert app.learned.data["terms"] == []


def test_import_wispr_dictionary(app):
    api = S.Api(app)
    with mock.patch.object(S.learn, "wispr_available", return_value=True), \
            mock.patch.object(S.learn, "wispr_dictionary", return_value=[("", "Zed"), ("a", "Ay")]):
        assert api.import_wispr_dictionary() == "Imported 2 entries from Wispr Flow"
        assert api.import_wispr_dictionary() == "Already up to date"


def test_voice_page_toggle(app):
    api = S.Api(app)
    with mock.patch.object(S.learn, "wispr_available", return_value=False):
        fix = api.voice()["fixes"][0]
    api.toggle_learned(fix["id"], False)
    assert app.learned.data["fixes"][0]["enabled"] is False


def test_update_setting_saves_and_applies(app):
    S.SpeakOn.update_setting(app, "model", "large")
    app.load_model.assert_called_once()
    assert json.loads(C.SETTINGS_FILE.read_text())["model"] == "large"
    S.SpeakOn.update_setting(app, "mic", "3")
    assert app.settings["mic"] == 3


def test_record_shortcut_saves_both_settings(app):
    captured = {"done": threading.Event(), "result": ["ctrl", "f9"]}
    captured["done"].set()
    app.keys.start_capture.return_value = captured
    assert S.Api(app).record_shortcut()
    saved = json.loads(C.SETTINGS_FILE.read_text())
    assert saved["custom_hotkey"] == ["ctrl", "f9"] and saved["hotkey"] == "custom"


def test_failed_piece_is_reported_and_the_rest_still_delivered(app):
    d = types.SimpleNamespace(finish=lambda: "first part", error=RuntimeError("terminated"), reused_preview=False,
                              nchunks=2, seconds=3.0)
    delivered = []
    app.released_at = 0
    app.deliver = lambda raw, dictation, err: delivered.append((raw, err))
    S.SpeakOn.finish(app, d)
    assert delivered[0][0] == "first part" and isinstance(delivered[0][1], RuntimeError)
