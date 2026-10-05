"""How long the wait after letting go of the key takes.

Replays a WAV through the live pipeline on a simulated clock: the worker is busy for as long as each
piece or preview really takes, while the audio keeps coming, as in the app. After the speech the key
is held for --hold seconds of quiet, then let go. The wait is what is still running at that moment
(a piece, or a preview the release keeps) plus the release step itself.

    python tools/bench_release.py <wav> "<what it says>" [<wav> "<text>" ...] [--repeat 3] [--hold 0.4 0.8]
                                  [--engine DIR]   # measure the engine.py in DIR instead (another version)
"""

import argparse
import os
import statistics
import sys
import time
import types
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser()
p.add_argument("pairs", nargs="+", help="wav text wav text ...")
p.add_argument("--repeat", type=int, default=3)
p.add_argument("--hold", type=float, nargs="+", default=[0.4], help="seconds of quiet before letting go")
p.add_argument("--threads", type=int, default=None, help="override the engine's ONNX thread count")
p.add_argument("--model", default="parakeet-v2")
p.add_argument("--engine", default=None, help="folder with the engine.py to measure (default: this one)")
A = p.parse_args()

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
if A.engine:
    sys.path.insert(0, str(Path(A.engine).resolve()))
import config as C  # noqa: E402
import engine as E  # noqa: E402
from selftest import recall  # noqa: E402

CLOCK = [0.0]
E.time = types.SimpleNamespace(time=lambda: CLOCK[0])   # the preview timer runs on audio time


def load(path):
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2), path
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def timed(fn, *args):
    t = time.perf_counter()
    fn(*args)
    return time.perf_counter() - t


def piece(d):
    d._do(*d.jobs.get())
    d.chunks_done += 1


def old_finish(d):
    """The release step of versions before _finish_tail."""
    n = len(d.blocks)
    if n > d.done_to:
        if n - d.done_to <= E.SHORT_TAIL_BLOCKS:
            d.spec = None
        d._do(d.done_to, n, d.threshold())


def release_time(eng, audio, hold):
    """Feed the audio like the app does, then let go: (wait, seconds left at release, text)."""
    audio = np.concatenate([audio, np.zeros(int(hold * E.SAMPLE_RATE), np.float32)])
    d = E.Dictation(eng, live_preview=True, start_worker=False)
    busy_until, running = 0.0, None        # what the worker is doing, and when it is done
    for i in range(0, len(audio) - E.BLOCK + 1, E.BLOCK):
        d.feed(audio[i:i + E.BLOCK])
        now = CLOCK[0] = (i + E.BLOCK) / E.SAMPLE_RATE
        if now < busy_until or (i // E.BLOCK) % 3:          # busy, or between its 80 ms checks
            continue
        running = None
        if not d.jobs.empty():
            busy_until, running = now + timed(piece, d), ("piece", None, None)
        else:
            before, last = d.spec, d.last_preview
            took = timed(d._maybe_preview)
            if d.last_preview != last:
                run = {k: d.spec[k] for k in ("start", "n", "span") if k in d.spec} if d.spec else None
                busy_until, running = now + took, ("preview", before, run)
    end = CLOCK[0]
    wait = 0.0
    d.finishing = True
    if running and busy_until > end:
        kind, before, run = running
        if kind == "piece" or (hasattr(d, "_heard_all") and run and d._heard_all(run)):
            wait += busy_until - end                        # it runs to the end: wait for the rest of it
        else:
            d.spec = before                                 # cancelled at once: as if it never ran
    while not d.jobs.empty():
        wait += timed(piece, d)
    tail = (len(d.blocks) - d.done_to) * E.BLOCK / E.SAMPLE_RATE
    wait += timed(d._finish_tail) if hasattr(d, "_finish_tail") else timed(old_finish, d)
    return wait, tail, d.committed_text()


def main():
    clips = [(load(w), t) for w, t in zip(A.pairs[::2], A.pairs[1::2])]
    eng = E.Engine(C.MODELS_DIR)
    if A.threads:
        E.PARAKEET_THREADS = A.threads
    eng.load(A.model)
    print(f"engine {E.__file__}, model {A.model}, threads {getattr(E, 'PARAKEET_THREADS', 'default')}, "
          f"cpus {os.cpu_count()}")
    for hold in A.hold:
        waits, recalls = [], []
        for audio, expected in clips:
            runs = [release_time(eng, audio, hold) for _ in range(A.repeat)]
            med = statistics.median(r[0] for r in runs)
            wait, tail, text = min(runs, key=lambda r: abs(r[0] - med))
            waits.append(med)
            recalls.append(recall(expected, text))
            print(f"  hold {hold:.1f}s, {len(audio) / E.SAMPLE_RATE:4.1f}s speech, {tail:4.1f}s left: wait {med:.3f}s "
                  f"(runs {', '.join(f'{r[0]:.3f}' for r in runs)}) | recall {recalls[-1]:.0%} | {text}")
        print(f"hold {hold:.1f}s: mean wait {statistics.mean(waits):.3f}s, mean recall {statistics.mean(recalls):.1%}")


if __name__ == "__main__":
    main()
