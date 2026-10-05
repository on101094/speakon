"""How long the wait after letting go of the key takes, and where it goes.

Replays a WAV through the live pipeline (pieces + previews, as if the computer were instant), then
times only the release step - the part the user waits for - and splits it into the ONNX models the
engine runs (audio features, encoder, decoder) and everything else.

    python tools/bench_release.py <wav> "<what it says>" [<wav> "<text>" ...] [--repeat 3] [--threads 3]
"""

import argparse
import collections
import os
import statistics
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import engine as E  # noqa: E402
from selftest import recall  # noqa: E402

SPENT = collections.defaultdict(float)
CALLS = collections.Counter()


def instrument_onnx():
    import onnxruntime as ort
    real_run = ort.InferenceSession.run

    def run(self, *args, **kwargs):
        name = Path(getattr(self, "_model_path", "") or "?").stem
        t = time.perf_counter()
        try:
            return real_run(self, *args, **kwargs)
        finally:
            SPENT[name] += time.perf_counter() - t
            CALLS[name] += 1
    ort.InferenceSession.run = run


def load(path):
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2), path
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def release_time(eng, audio):
    """Feed the audio like the app does, then time the release step alone."""
    d = E.Dictation(eng, live_preview=True, start_worker=False)
    for i in range(0, len(audio) - E.BLOCK + 1, E.BLOCK):
        d.feed(audio[i:i + E.BLOCK])
        if (i // E.BLOCK) % 15 == 14:                  # previews every 0.45 s, pieces as they are cut
            while not d.jobs.empty():
                d._do(*d.jobs.get())
                d.chunks_done += 1
            d.last_preview = 0
            d._maybe_preview()
    while not d.jobs.empty():                          # anything already cut finishes before release
        d._do(*d.jobs.get())
    tail = (len(d.blocks) - d.done_to) * E.BLOCK / E.SAMPLE_RATE
    SPENT.clear(); CALLS.clear()
    t = time.perf_counter()
    d.finishing = True                                 # the app's "finish" job, inline
    n = len(d.blocks)
    if n > d.done_to:
        if n - d.done_to <= E.SHORT_TAIL_BLOCKS:
            d.spec = None
        d._do(d.done_to, n, d.threshold())
    total = time.perf_counter() - t
    return total, tail, d.committed_text(), dict(SPENT), dict(CALLS)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pairs", nargs="+", help="wav text wav text ...")
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--threads", type=int, default=None, help="override the engine's ONNX thread count")
    p.add_argument("--model", default="parakeet-v2")
    a = p.parse_args()
    clips = list(zip(a.pairs[::2], a.pairs[1::2]))

    instrument_onnx()
    eng = E.Engine(C.MODELS_DIR)
    if a.threads:
        E.PARAKEET_THREADS = a.threads
    eng.load(a.model)
    print(f"model {a.model}, threads {getattr(E, 'PARAKEET_THREADS', 'default')}, cpus {os.cpu_count()}")
    for wav, expected in clips:
        audio = load(wav)
        runs = [release_time(eng, audio) for _ in range(a.repeat)]
        med = statistics.median(r[0] for r in runs)
        total, tail, text, spent, calls = min(runs, key=lambda r: abs(r[0] - med))
        parts = ", ".join(f"{k} {v:.3f}s/{calls[k]}x" for k, v in sorted(spent.items(), key=lambda kv: -kv[1]))
        other = total - sum(spent.values())
        print(f"{len(audio) / E.SAMPLE_RATE:5.1f}s audio, {tail:4.1f}s left at release: wait {med:.3f}s "
              f"(runs {', '.join(f'{r[0]:.3f}' for r in runs)}) = {parts}, python {other:.3f}s | "
              f"recall {recall(expected, text):.0%}")
        print(f"      got: {text}")


if __name__ == "__main__":
    main()
