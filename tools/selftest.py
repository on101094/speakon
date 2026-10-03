"""End-to-end self-test: dictate a WAV through the fake microphone and check what lands in history.

Starts speakon.py with SPEAKON_FAKE_MIC / SPEAKON_NO_INSERT / SPEAKON_SELFTEST (see README), waits
for a new entry in history.json, compares its text with what the WAV says, then closes the app.
Never sends keys to other windows. Runs in CI; also usable by hand:

    python tools/selftest.py speech.wav "the sentence spoken in it"
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config as C  # noqa: E402


def history_ids():
    try:
        return {h.get("id") for h in json.loads(C.HISTORY_FILE.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return set()


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def recall(expected, got):
    """Share of the expected words (with repeats) that appear in what was transcribed."""
    want, have = collections.Counter(words(expected)), collections.Counter(words(got))
    return sum(min(n, have[w]) for w, n in want.items()) / max(1, sum(want.values()))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("wav", help="16 kHz mono 16-bit WAV")
    p.add_argument("expected", help="what the WAV says")
    p.add_argument("--timeout", type=float, default=900, help="seconds to wait (first run downloads the model)")
    p.add_argument("--min-recall", type=float, default=0.8)
    a = p.parse_args()

    with wave.open(a.wav) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (16000, 1, 2):
            sys.exit(f"{a.wav} must be 16 kHz mono 16-bit, got {w.getframerate()} Hz, {w.getnchannels()} ch")
        seconds = w.getnframes() / w.getframerate()

    before = history_ids()
    env = {**os.environ, "SPEAKON_FAKE_MIC": str(Path(a.wav).resolve()), "SPEAKON_NO_INSERT": "1",
           "SPEAKON_SELFTEST": f"{seconds + 2:.1f}"}
    print(f"Dictating {seconds:.1f} s of audio; waiting up to {a.timeout:.0f} s for the result...", flush=True)
    proc = subprocess.Popen([sys.executable, str(ROOT / "speakon.py"), "--tray"], env=env, cwd=ROOT)
    entry, start = None, time.time()
    try:
        while time.time() - start < a.timeout:
            if proc.poll() is not None:
                break
            new = [h for h in json.loads(C.HISTORY_FILE.read_text(encoding="utf-8"))
                   if h.get("id") not in before] if C.HISTORY_FILE.exists() else []
            if new:
                entry = new[0]
                break
            time.sleep(2)
    finally:
        proc.kill()

    log = C.DATA_DIR / "logs" / "speakon.log"
    if entry is None:
        reason = f"SpeakOn exited with code {proc.returncode}" if proc.returncode is not None else "timed out"
        print(f"FAIL: no new history entry ({reason}).")
        if log.exists():
            print("--- speakon.log (last 40 lines) ---")
            print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]))
        sys.exit(1)

    score = recall(a.expected, entry["text"])
    print(f"Expected: {a.expected}\nGot:      {entry['text']}")
    print(f"Word recall {score:.0%} (need {a.min_recall:.0%}), wait after release {entry.get('latency')} s, "
          f"model {entry.get('model')}")
    sys.exit(0 if score >= a.min_recall else 1)


if __name__ == "__main__":
    main()
