import sys
import threading
import types

import pytest

import engine


class FakeRunOptions:
    def __init__(self):
        self.terminate = False


class FakeSession:
    """A session whose run() blocks until told to finish, then reports whether it was terminated."""

    def __init__(self):
        self.started, self.release = threading.Event(), threading.Event()

    def run(self, outputs, feeds, opts):
        self.started.set()
        self.release.wait(5)
        return "terminated" if opts.terminate else "ok"


@pytest.fixture(autouse=True)
def fake_onnxruntime(monkeypatch):
    monkeypatch.setitem(sys.modules, "onnxruntime", types.SimpleNamespace(RunOptions=FakeRunOptions))


def run_in_thread(enc):
    out = []
    t = threading.Thread(target=lambda: out.append(enc.run(None, {})))
    t.start()
    enc._session.started.wait(5)
    return t, out


def test_cancel_stops_a_preview_run():
    enc = engine._Cancellable(FakeSession())
    enc.preview = True
    t, out = run_in_thread(enc)
    enc.cancel_preview()
    enc._session.release.set()
    t.join()
    assert out == ["terminated"]


def test_late_cancel_does_not_stop_the_final_pass():
    # the key was released just as the preview finished: the final pass has already started when
    # the cancel meant for the preview arrives
    enc = engine._Cancellable(FakeSession())
    enc.preview = False
    t, out = run_in_thread(enc)
    enc.cancel_preview()
    enc._session.release.set()
    t.join()
    assert out == ["ok"]


def test_engine_tags_each_transcription(monkeypatch):
    eng = engine.Engine.__new__(engine.Engine)
    eng.lock, eng.preview_running = threading.Lock(), False
    eng.encoder = engine._Cancellable(FakeSession())
    seen = []
    monkeypatch.setattr(eng, "_check", lambda language: language, raising=False)
    monkeypatch.setattr(eng, "_words", lambda *a: seen.append(eng.encoder.preview) or [], raising=False)
    eng.words(None, preview=True)
    eng.words(None)
    assert seen == [True, False]
