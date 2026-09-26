"""Score speech engines on the user's own Wispr Flow recordings.

Reference = Wispr's raw ASR text (asrText), normalised. Word error rate (WER) =
(substitutions + deletions + insertions) / reference words. Lower is better.

usage: python tools/eval_wispr.py <wispr_eval dir> <n clips> <config> [<config> ...]
configs: pk3, pk3-stream, pk2, pk2-stream, small.en, base.en, turbo, large-v3-turbo-stream
"""

import json
import os
import random
import re
import sys
import time
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import engine as E  # noqa: E402

MODELS_DIR = os.path.expanduser(r"~\SpeakOn\models")

EQUIV = {"gonna": "going to", "wanna": "want to", "gotta": "got to", "ok": "okay", "yeah": "yes",
         "alright": "all right", "percent": "%"}
FILLERS = {"um", "uh", "uhm", "hmm", "mm", "ah", "eh", "er", "erm"}


def norm(text):
    t = (text or "").lower().replace("’", "'")
    t = re.sub(r"[^\w\s'%]", " ", t)
    words = []
    for w in t.split():
        w = w.strip("'")
        if not w or w in FILLERS:
            continue
        words.extend(EQUIV.get(w, w).split())
    return words


def align(ref, hyp):
    """Levenshtein alignment -> (errors, [(ref_word|None, hyp_word|None), ...])"""
    n, m = len(ref), len(hyp)
    d = np.zeros((n + 1, m + 1), dtype=np.int32)
    d[:, 0] = np.arange(n + 1)
    d[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, pairs = n, m, []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i, j] == d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            pairs.append((ref[i - 1], hyp[j - 1])); i -= 1; j -= 1
        elif i > 0 and d[i, j] == d[i - 1, j] + 1:
            pairs.append((ref[i - 1], None)); i -= 1
        else:
            pairs.append((None, hyp[j - 1])); j -= 1
    return int(d[n, m]), pairs[::-1]


def load(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


CONFIGS = {
    "pk3": ("parakeet-v3", False), "pk3-stream": ("parakeet-v3", True),
    "pk2": ("parakeet-v2", False), "pk2-stream": ("parakeet-v2", True),
    "small.en": ("small.en", False), "base.en": ("base.en", False),
    "turbo": ("large-v3-turbo", False), "small.en-stream": ("small.en", True),
}


def main():
    src, n, configs = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    meta = [m for m in json.load(open(os.path.join(src, "meta.json"), encoding="utf-8"))
            if m["lang"] == "en" and m["asr"] and 2 <= m["secs"] <= 60]
    random.Random(7).shuffle(meta)
    clips = meta[:n]
    audio_min = sum(m["secs"] for m in clips) / 60
    print(f"{len(clips)} clips, {audio_min:.1f} min of your speech", flush=True)
    results = {}
    for cfg in configs:
        model_id, stream = CONFIGS[cfg]
        eng = E.Engine(MODELS_DIR)
        eng.load(model_id)
        errs = words = 0
        t0 = time.time()
        outs = []
        for m in clips:
            a = load(m["wav"])
            hyp = E.transcribe_array(eng, a) if stream else eng.transcribe(a)
            ref = norm(m["asr"])
            e, _ = align(ref, norm(hyp))
            errs += e
            words += len(ref)
            outs.append({"id": m["id"], "hyp": hyp})
        took = time.time() - t0
        wer = errs / max(1, words)
        results[cfg] = {"wer": wer, "speed_x_realtime": audio_min * 60 / took, "outs": outs}
        print(f"{cfg:16s} WER {wer * 100:5.1f}%   {audio_min * 60 / took:5.1f}x faster than real time", flush=True)
    out = os.path.join(src, "results_" + "_".join(configs) + ".json")
    json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
