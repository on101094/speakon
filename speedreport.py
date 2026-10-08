"""A short report of how long dictations took, from SpeakOn's own log - no dictated text.

Settings -> Copy speed report puts it on the clipboard, so the user can paste it to whoever is
working on speed; tools/weekly_check.py reads the same lines.
"""

import os
import re
import statistics
from datetime import datetime, timedelta

LOG_RE = re.compile(r"^(\S+ \S+) INFO dictation: ([\d.]+)s speech, (\d+) chars, wait ([\d.]+)s = engine ([\d.]+) "
                    r"\(pieces (\S+), preview reused (\S+)\) \+ keys still held ([\d.]+) \+ insert ([\d.]+) \[(\w+)\]")

REL_RE = re.compile(r"^(\S+ \S+) INFO release: worker (.+?), waited ([\d.]+)s for it, ([\d.]+)s left, "
                    r"final step ([\d.]+)s, preview heard all (\S+)")


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))] if xs else 0


def read(log_dir, since):
    """Dictation timings from the log, each with the release line that follows it (1.2.6+) if any."""
    rows = []
    for f in sorted(log_dir.glob("speakon.log*"), key=lambda p: p.stat().st_mtime):   # oldest file first
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = LOG_RE.match(line)
            if m:
                rows.append({"time": datetime.strptime(m.group(1)[:19], "%Y-%m-%d %H:%M:%S"),
                             "speech": float(m.group(2)), "wait": float(m.group(4)), "engine": float(m.group(5)),
                             "pieces": m.group(6), "reused": m.group(7) == "True", "keys": float(m.group(8)),
                             "insert": float(m.group(9)), "method": m.group(10), "release": None})
                continue
            r = REL_RE.match(line)
            if r and rows and rows[-1]["release"] is None:
                rows[-1]["release"] = {"busy": r.group(2), "queued": float(r.group(3)), "left": float(r.group(4)),
                                       "final": float(r.group(5)), "heard_all": r.group(6) == "True"}
    return [r for r in rows if r["time"] >= since]


def med(xs):
    return statistics.median(xs) if xs else 0.0


def report(log_dir, version, model, threads, days=14, now=None):
    since = (now or datetime.now()) - timedelta(days=days)
    rows = read(log_dir, since)
    head = f"SpeakOn speed report - {version}, {model}, {os.cpu_count()} CPUs, {threads} threads, last {days} days"
    if not rows:
        return head + "\nNo dictations logged yet."
    waits = [r["wait"] for r in rows]
    out = [head,
           f"{len(rows)} dictations. Wait after letting go: median {med(waits):.2f}s, 90% under {pct(waits, .9):.2f}s, "
           f"worst {max(waits):.2f}s",
           f"  = engine median {med([r['engine'] for r in rows]):.2f}s + keys still held "
           f"{med([r['keys'] for r in rows]):.2f}s + insert {med([r['insert'] for r in rows]):.2f}s; "
           f"preview reused {sum(r['reused'] for r in rows)}/{len(rows)}"]
    for lo, hi in [(0, 5), (5, 15), (15, 1e9)]:
        part = [r["wait"] for r in rows if lo <= r["speech"] < hi]
        if part:
            label = f"{lo}-{hi:.0f}s" if hi < 1e9 else f"{lo}s+"
            out.append(f"  speech {label}: {len(part)} dictations, median wait {med(part):.2f}s, "
                       f"90% under {pct(part, .9):.2f}s")
    rel = [r["release"] for r in rows if r["release"]]
    if rel:
        busy = {k: sum(x["busy"] == k for x in rel) for k in sorted({x["busy"] for x in rel})}
        out.append(f"Engine part ({len(rel)} dictations with details): waiting for the worker median "
                   f"{med([x['queued'] for x in rel]):.2f}s (90% {pct([x['queued'] for x in rel], .9):.2f}s), "
                   f"final step median {med([x['final'] for x in rel]):.2f}s "
                   f"(90% {pct([x['final'] for x in rel], .9):.2f}s), audio left median "
                   f"{med([x['left'] for x in rel]):.1f}s, preview heard all "
                   f"{sum(x['heard_all'] for x in rel)}/{len(rel)}, worker at release {busy}")
    out.append("Slowest:")
    for r in sorted(rows, key=lambda r: -r["wait"])[:5]:
        x = r["release"]
        extra = (f", worker {x['busy']}, waited {x['queued']:.2f}s, {x['left']:.1f}s left, final {x['final']:.2f}s"
                 if x else "")
        out.append(f"  {r['wait']:.2f}s: {r['speech']:.1f}s speech, engine {r['engine']:.2f}s, keys {r['keys']:.2f}s, "
                   f"insert {r['insert']:.2f}s [{r['method']}]{extra}")
    return "\n".join(out)
