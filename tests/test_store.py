import json
import os
import threading
import time

import config as C
import store
from learn import entry_id


def test_load_backfills_ids_and_resets_unknown_hotkey(data_dir):
    C.SETTINGS_FILE.write_text(json.dumps({"hotkey": "no_such_preset", "model": "x"}))
    C.HISTORY_FILE.write_text(json.dumps([{"time": "2026-10-01T10:00:00", "text": "old"}]))
    st = store.Store()
    assert st.settings["hotkey"] == "ctrl_win"
    assert st.settings["model"] == "x"
    assert st.history[0]["id"]
    assert C.DICTIONARY_FILE.exists()


def test_construction_does_not_write_settings(data_dir):
    # main() spots a first run by settings.json not existing yet
    st = store.Store()
    st.set_setting("start_with_windows", True, save=False)
    assert not C.SETTINGS_FILE.exists()
    assert st.settings["start_with_windows"] is True


def test_set_setting_saves_and_returns_old_value(data_dir):
    st = store.Store()
    st.set_setting("model", "a")
    assert st.set_setting("model", "b") == "a"
    assert json.loads(C.SETTINGS_FILE.read_text())["model"] == "b"


def test_add_history_assigns_id_trims_and_saves(data_dir, monkeypatch):
    monkeypatch.setattr(store, "HISTORY_LIMIT", 3)
    st = store.Store()
    version = st.history_version
    for i in range(5):
        st.add_history({"time": "2026-10-03T10:00:00", "text": f"n{i}"})
    assert [h["text"] for h in st.history] == ["n4", "n3", "n2"]
    assert len({h["id"] for h in st.history}) == 3
    assert st.history_version == version + 5
    assert json.loads(C.HISTORY_FILE.read_text()) == st.history


def test_history_actions_find_the_entry_after_the_list_shifts(data_dir):
    st = store.Store()
    st.add_history({"time": "2026-10-03T10:00:00", "text": "keep"})
    hid = st.history[0]["id"]
    st.add_history({"time": "2026-10-03T10:01:00", "text": "newer"})   # lands at index 0
    assert st.history_text(hid) == "keep"
    assert st.edit_history(hid, "  kept ") == "keep"
    assert st.history_text(hid) == "kept"
    st.delete_history(hid)
    assert [h["text"] for h in st.history] == ["newer"]


def test_history_actions_on_missing_entry_are_no_ops(data_dir):
    st = store.Store()
    assert st.history_text("gone") is None
    assert st.edit_history("gone", "x") is None
    st.delete_history("gone")


def test_recent_history_is_a_copy(data_dir):
    st = store.Store()
    st.add_history({"time": "2026-10-03T10:00:00", "text": "a"})
    st.recent_history().clear()
    assert st.history


def test_dictionary_entries_by_id(data_dir):
    st = store.Store()
    st.set_dictionary("# c\nfoo\nbar -> Bar\n")
    bar = entry_id("d", "bar -> Bar")
    st.set_dictionary("first\n" + st.dictionary)                      # line numbers shift
    st.save_dictionary_entry(bar, "bar -> BAR")
    assert st.dictionary == "first\n# c\nfoo\nbar -> BAR\n"
    st.save_dictionary_entry(None, "baz")
    assert st.dictionary.endswith("baz\n")
    st.save_dictionary_entry(bar, "orphan")                           # id no longer exists: append
    assert st.dictionary.endswith("orphan\n")
    st.delete_dictionary_entry(entry_id("d", "foo"))
    assert "foo" not in st.dictionary.splitlines()
    st.delete_dictionary_entry("dmissing")
    assert C.DICTIONARY_FILE.read_text() == st.dictionary


def test_add_dictionary_lines_skips_existing(data_dir):
    st = store.Store()
    st.set_dictionary("Baz\n")
    assert st.add_dictionary_lines(["baz", "new -> New"], "from Wispr Flow") == ["new -> New"]
    assert st.dictionary == "Baz\n# from Wispr Flow\nnew -> New\n"
    assert st.add_dictionary_lines(["NEW -> new"], "again") == []


def test_reload_picks_up_hand_edits(data_dir):
    st = store.Store()
    C.DICTIONARY_FILE.write_text("edited by hand\n")
    later = time.time() + 5
    os.utime(C.DICTIONARY_FILE, (later, later))
    assert st.reload_dictionary() == "edited by hand\n"


def test_concurrent_changes_lose_nothing(data_dir):
    st = store.Store()
    for i in range(200):
        st.add_history({"time": "2026-10-03T10:00:00", "text": f"h{i}"})
    st.set_dictionary("".join(f"w{i}\n" for i in range(60)))
    targets = [h["id"] for h in st.history]
    errors = []

    def guard(job):
        def run():
            try:
                job()
            except Exception as e:   # noqa: BLE001 - collected and asserted below
                errors.append(repr(e))
        return run

    jobs = [lambda: [st.add_history({"time": "2026-10-03T11:00:00", "text": f"n{i}"}) for i in range(300)],
            lambda: [st.delete_history(h) for h in targets],
            lambda: [st.edit_history(h, "edited") for h in targets[::2]],
            lambda: [st.set_setting(f"k{i % 7}", i) for i in range(300)],
            lambda: [st.delete_dictionary_entry(entry_id("d", f"w{i}")) for i in range(60)],
            lambda: [st.save_dictionary_entry(None, f"x{i}") for i in range(60)],
            lambda: [st.recent_history(600) for _ in range(300)]]
    threads = [threading.Thread(target=guard(job)) for job in jobs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    texts = [h["text"] for h in st.history]
    assert not any(t.startswith("h") or t == "edited" for t in texts)
    assert sum(t.startswith("n") for t in texts) == 300
    assert len({h["id"] for h in st.history}) == len(st.history)
    assert sorted(st.dictionary.split()) == sorted(f"x{i}" for i in range(60))
    assert json.loads(C.HISTORY_FILE.read_text()) == st.history
    assert json.loads(C.SETTINGS_FILE.read_text()) == st.settings
