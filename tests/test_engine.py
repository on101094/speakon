import sys
import threading
import types

import numpy as np
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


class FakeEngine:
    """Says one word per call and counts the calls."""

    def __init__(self):
        self.ready = threading.Event()
        self.ready.set()
        self.calls, self.cancels = 0, 0

    def words(self, audio, language=None, prompt="", hotwords="", preview=False):
        self.calls += 1
        return [(" hello", 0.3)]

    def cancel_preview(self):
        self.cancels += 1


def talk(d, speech, quiet):
    t = np.arange(engine.BLOCK) / engine.SAMPLE_RATE
    loud = (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    for i in range(round(speech / 0.03)):
        d.feed(loud if i % 3 else loud / 50)        # syllables: the noise floor stays below them
    for _ in range(round(quiet / 0.03)):
        d.feed(np.zeros(engine.BLOCK, np.float32))


def previewed(speech, quiet):
    eng = FakeEngine()
    d = engine.Dictation(eng, start_worker=False)
    talk(d, speech, quiet)
    d._maybe_preview()
    assert eng.calls == 1
    return eng, d


def test_release_reuses_a_preview_that_heard_everything():
    eng, d = previewed(2.0, 0.6)
    talk(d, 0, 0.3)                       # still quiet when the key is let go
    d.finishing = True
    d._finish_tail()
    assert eng.calls == 1 and d.committed_text() == "hello"


def test_release_transcribes_again_when_more_was_said():
    eng, d = previewed(2.0, 0.6)
    talk(d, 0.5, 0.1)
    d.finishing = True
    d._finish_tail()
    assert eng.calls == 2 and d.committed_text() == "hello"


def test_preview_waits_for_the_pause_to_cover_the_last_word():
    eng = FakeEngine()
    d = engine.Dictation(eng, start_worker=False)
    talk(d, 2.0, 0.12)                    # too soon after the last word: the padding is not there yet
    d._maybe_preview()
    talk(d, 0, 0.3)
    d._maybe_preview()                    # 0.45 s have not passed, but speech has stopped: hear it all now
    assert eng.calls == 2
    d._maybe_preview()                    # nothing new: no third run
    d.finishing = True
    d._finish_tail()
    assert eng.calls == 2


@pytest.mark.parametrize("more, cancelled", [(0, 0), (0.5, 1)])
def test_release_keeps_a_running_preview_only_if_it_covers_everything(more, cancelled):
    eng = FakeEngine()
    d = engine.Dictation(eng, start_worker=False)
    talk(d, 2.0, 0.6)
    n = len(d.blocks)
    d.preview_run = {"start": 0, "end": n, "n": 0, "span": d._span(0, n, d.threshold())}
    talk(d, more, 0.3)
    d.worker = types.SimpleNamespace(join=lambda: None)
    d.finish()
    assert eng.cancels == cancelled
