import json
import os
import sqlite3
import threading
import time

import config as C
import learn


def make(data_dir, **data):
    C.LEARNED_FILE.write_text(json.dumps({"fixes": [], "terms": [], **data}))
    return learn.Learned(C.LEARNED_FILE)


def test_entries_and_ids_survive_reordering(data_dir):
    lr = make(data_dir, fixes=[{"heard": "a", "wanted": "A", "count": 1, "enabled": True},
                               {"heard": "b", "wanted": "B", "count": 1, "enabled": True}], terms=["x", "y"])
    rows = lr.entries()
    assert [r["write"] for r in rows] == ["A", "B", "x", "y"]
    b = next(r["id"] for r in rows if r["write"] == "B")
    lr.data["fixes"].insert(0, {"heard": "c", "wanted": "C", "count": 1, "enabled": True})
    lr.set_fix_enabled(b, False)
    assert [f["enabled"] for f in lr.data["fixes"]] == [True, True, False]
    assert "B" not in [r["write"] for r in lr.entries()]                 # disabled fixes are hidden


def test_remove_term(data_dir):
    lr = make(data_dir, terms=["x", "y"])
    y = next(r["id"] for r in lr.entries() if r["write"] == "y")
    lr.data["terms"].insert(0, "w")
    lr.remove_term(y)
    assert json.loads(C.LEARNED_FILE.read_text())["terms"] == ["w", "x"]


def test_summary_does_not_write_ids_into_the_file(data_dir):
    lr = make(data_dir, fixes=[{"heard": "a", "wanted": "A", "count": 1}], terms=["x"], clips=3, report="R")
    s = lr.summary()
    assert s["report"] == "R" and s["terms"] == 1 and s["clips"] == 3 and s["fixes"][0]["id"]
    assert "id" not in lr.data["fixes"][0]


def test_lowercase_is_a_copy(data_dir):
    lr = make(data_dir, lowercase=["and"])
    lr.lowercase().append("x")
    assert lr.data["lowercase"] == ["and"]


def test_apply_wispr(data_dir):
    lr = make(data_dir, terms=["Replikanto"])                          # learned from the user's own correction
    lr.apply_wispr([{"heard": "d", "wanted": "D", "count": 2, "precision": 1.0}],
                   ["t0"] + [f"t{i}" for i in range(100)], 9, "report")
    saved = json.loads(C.LEARNED_FILE.read_text())
    assert saved["terms"][0] == "Replikanto"                          # kept, not replaced
    assert saved["terms"][1:] == [f"t{i}" for i in range(79)]         # Wispr's top 80, no duplicates
    assert saved["clips"] == 9 and saved["report"] == "report"
    assert saved["fixes"][0]["heard"] == "d" and saved["fixes"][0]["source"] == "Wispr Flow"


def test_unreadable_file_does_not_wipe_what_was_learned(data_dir):
    lr = make(data_dir, fixes=[{"heard": "a", "wanted": "A", "count": 1}], terms=["x"])
    assert lr.entries()
    C.LEARNED_FILE.write_text('{"fixes": [ typo')
    later = time.time() + 5
    os.utime(C.LEARNED_FILE, (later, later))
    lr.merge_fixes([{"heard": "b", "wanted": "B", "count": 1, "precision": 1.0}], "t")
    saved = json.loads(C.LEARNED_FILE.read_text())
    assert [f["heard"] for f in saved["fixes"]] == ["a", "b"] and saved["terms"] == ["x"]
    backups = list(data_dir.glob("learned.json.broken-*"))
    assert len(backups) == 1 and backups[0].read_text() == '{"fixes": [ typo'


def test_unreadable_file_at_start_is_kept_aside(data_dir):
    C.LEARNED_FILE.write_text("not json")
    lr = learn.Learned(C.LEARNED_FILE)
    assert lr.data["fixes"] == []
    assert list(data_dir.glob("learned.json.broken-*"))


def make_wispr_db(path, wal_rows):
    db = sqlite3.connect(path)
    db.execute("pragma journal_mode=wal")
    db.execute("pragma wal_autocheckpoint=0")
    db.execute("create table History (audio blob)")
    db.execute("create table Dictionary (phrase text, replacement text, isSnippet int, source text, isDeleted int)")
    db.execute("insert into Dictionary values ('Zed', null, 0, 'manual', 0)")
    db.commit()
    for _ in range(wal_rows):                       # still only in flow.sqlite-wal, like Wispr's newest rows
        db.execute("insert into Dictionary values ('New', null, 0, 'manual', 0)")
    db.commit()
    return db                                       # kept open so the -wal file is not checkpointed away


def test_wispr_snapshot_includes_wal_rows_and_is_deleted(tmp_path, monkeypatch):
    wispr = tmp_path / "wispr" / "flow.sqlite"
    wispr.parent.mkdir()
    live = make_wispr_db(wispr, wal_rows=2)
    assert wispr.with_name("flow.sqlite-wal").exists()
    monkeypatch.setattr(learn, "WISPR_DB", wispr)
    monkeypatch.setattr(learn.tempfile, "tempdir", str(tmp_path / "temp"))
    (tmp_path / "temp").mkdir()
    assert learn.wispr_summary()["dictionary"] == 3
    assert [w for _, w in learn.wispr_dictionary()] == ["Zed", "New", "New"]
    assert list((tmp_path / "temp").iterdir()) == []
    live.close()


def test_concurrent_merges_lose_nothing(data_dir):
    lr = make(data_dir)

    def merge(start):
        for i in range(start, start + 100):
            lr.merge_fixes([{"heard": f"x{i}", "wanted": f"X{i}", "count": 1, "precision": 1.0}], "t")

    threads = [threading.Thread(target=merge, args=(n * 100,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(json.loads(C.LEARNED_FILE.read_text())["fixes"]) == 400


def test_learn_lowercase_from_finished_text():
    texts = ["We should refactor it.", "then refactor the rest", "Ask Bob. Bob said yes. Then bob left"]
    assert learn.learn_lowercase(texts) == ["refactor"]       # "bob" is mostly capitalised, so it stays out


def test_apply_wispr_stores_the_users_lowercase_words(data_dir):
    lr = make(data_dir, lowercase=["old"])
    lr.apply_wispr([], [], 1, "r")                                  # older callers: list left alone
    assert lr.lowercase() == ["old"]
    lr.apply_wispr([], [], 1, "r", ["refactor"])
    assert json.loads(C.LEARNED_FILE.read_text())["lowercase"] == ["refactor"]
