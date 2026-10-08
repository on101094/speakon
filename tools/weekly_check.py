"""Weekly health check for SpeakOn - used by the improvement routine.

  python tools/weekly_check.py            report from real use (last 7 days)
  python tools/weekly_check.py --eval 40  + accuracy on 40 of the user's Wispr Flow recordings

Reads only SpeakOn's own data folder (and a read-only copy of Wispr Flow's database for --eval).
Prints numbers and lengths, never dictated text, unless --show-text is given.
"""

import json
import os
import re
import statistics
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import config as C  # noqa: E402

LOG_RE = re.compile(r"^(\S+ \S+) INFO dictation: ([\d.]+)s speech, (\d+) chars, wait ([\d.]+)s = engine ([\d.]+) "
                    r"\(pieces (\S+), preview reused (\S+)\) \+ keys still held ([\d.]+) \+ insert ([\d.]+) \[(\w+)\]")

REL_RE = re.compile(r"^(\S+ \S+) INFO release: worker (.+?), waited ([\d.]+)s for it, ([\d.]+)s left, "
                    r"final step ([\d.]+)s, preview heard all (\S+)")


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))] if xs else 0


def report(days=7, show_text=False):
    since = datetime.now() - timedelta(days=days)
    hist = json.loads(C.HISTORY_FILE.read_text(encoding="utf-8")) if C.HISTORY_FILE.exists() else []
    recent = [h for h in hist if datetime.fromisoformat(h["time"]) >= since and not h.get("file")]
    print(f"== SpeakOn weekly check ({datetime.now():%Y-%m-%d}) - last {days} days ==")
    print(f"dictations: {len(recent)}, words: {sum(len(h['text'].split()) for h in recent)}, "
          f"speech: {sum(h.get('seconds', 0) for h in recent) / 60:.1f} min")
    waits = [h["latency"] for h in recent if "latency" in h]
    if waits:
        print(f"wait after release: median {statistics.median(waits):.2f}s, 90% under {pct(waits, .9):.2f}s, "
              f"worst {max(waits):.2f}s")
    rows, rel = [], []
    for folder in [C.DATA_DIR / "logs"]:
        for f in sorted(folder.glob("speakon.log*")):
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                r = REL_RE.match(line)
                if r and datetime.strptime(r.group(1)[:19], "%Y-%m-%d %H:%M:%S") >= since:
                    rel.append({"busy": r.group(2), "queued": float(r.group(3)), "left": float(r.group(4)),
                                "final": float(r.group(5)), "heard_all": r.group(6) == "True"})
                m = LOG_RE.match(line)
                if m and datetime.strptime(m.group(1)[:19], "%Y-%m-%d %H:%M:%S") >= since:
                    rows.append({"speech": float(m.group(2)), "chars": int(m.group(3)), "wait": float(m.group(4)),
                                 "engine": float(m.group(5)), "reused": m.group(7) == "True",
                                 "keys": float(m.group(8)), "insert": float(m.group(9)), "method": m.group(10)})
    if rows:
        print(f"timing log ({len(rows)} dictations): engine median {statistics.median(r['engine'] for r in rows):.2f}s, "
              f"keys-held median {statistics.median(r['keys'] for r in rows):.2f}s, "
              f"insert median {statistics.median(r['insert'] for r in rows):.2f}s, "
              f"preview reused {sum(r['reused'] for r in rows)}/{len(rows)}")
        if rel:   # 1.2.6+: what the engine part of the wait was spent on
            busy = {k: sum(r["busy"] == k for r in rel) for k in sorted({r["busy"] for r in rel})}
            print(f"engine part ({len(rel)} dictations): waiting for the worker median "
                  f"{statistics.median(r['queued'] for r in rel):.2f}s (90% {pct([r['queued'] for r in rel], .9):.2f}s), "
                  f"final step median {statistics.median(r['final'] for r in rel):.2f}s "
                  f"(90% {pct([r['final'] for r in rel], .9):.2f}s), "
                  f"audio left median {statistics.median(r['left'] for r in rel):.1f}s, "
                  f"preview heard all {sum(r['heard_all'] for r in rel)}/{len(rel)}, worker at release {busy}")
        slow = sorted(rows, key=lambda r: -r["wait"])[:5]
        print("slowest:", ", ".join(f"{r['wait']:.2f}s ({r['speech']:.0f}s speech, engine {r['engine']:.2f}, "
                                    f"insert {r['insert']:.2f})" for r in slow))
    errors = []
    for f in sorted((C.DATA_DIR / "logs").glob("speakon.log*")):
        errors += [ln for ln in f.read_text(encoding="utf-8", errors="ignore").splitlines()
                   if " ERROR " in ln or "Traceback" in ln]
    print(f"errors in log: {len(errors)}", *(errors[-5:]), sep="\n  " if errors else "")
    learned = json.loads(C.LEARNED_FILE.read_text(encoding="utf-8")) if C.LEARNED_FILE.exists() else {}
    fixes = learned.get("fixes", [])
    mine = [f for f in fixes if f.get("source") == "your corrections"]
    print(f"learned fixes: {len(fixes)} total, {len(mine)} from the user's own corrections: "
          + ", ".join(f"{f['heard']} -> {f['wanted']}{'' if f.get('enabled', True) else ' (off)'}" for f in mine))
    edited = [h for h in recent if h.get("edited")]
    print(f"dictations edited in SpeakOn: {len(edited)}")
    if show_text:
        for h in recent[:40]:
            print(f"  {h['time'][5:16]} {h.get('app', '')}: {h['text'][:160]}")


def evaluate(n):
    import random

    import engine as E
    import learn
    from eval_stream import run
    from eval_wispr import align, norm
    if not learn.wispr_available():
        print("Wispr Flow database not found - skipping accuracy check")
        return
    clips = learn.wispr_clips()
    random.Random(7).shuffle(clips)
    clips = clips[:n]
    eng = E.Engine(C.MODELS_DIR)
    eng.load("parakeet-v2")
    for name, previews in (("pause pieces only", False), ("live pipeline (what the app does)", True)):
        errs = words = 0
        for c in clips:
            ref = norm(c["ref"])
            e, _ = align(ref, norm(run(eng, c["audio"], previews)))
            errs += e
            words += len(ref)
        print(f"accuracy on {len(clips)} Wispr recordings - {name}: {errs / max(1, words) * 100:.2f}% word errors",
              flush=True)


if __name__ == "__main__":
    report(show_text="--show-text" in sys.argv)
    if "--eval" in sys.argv:
        evaluate(int(sys.argv[sys.argv.index("--eval") + 1]))
