import json
import threading

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
    lr = make(data_dir)
    lr.apply_wispr([{"heard": "d", "wanted": "D", "count": 2, "precision": 1.0}], [f"t{i}" for i in range(100)], 9,
                   "report")
    saved = json.loads(C.LEARNED_FILE.read_text())
    assert len(saved["terms"]) == 80 and saved["clips"] == 9 and saved["report"] == "report"
    assert saved["fixes"][0]["heard"] == "d" and saved["fixes"][0]["source"] == "Wispr Flow"


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
