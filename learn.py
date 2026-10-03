"""Learning how the user speaks.

Two sources, both local:
  1. Wispr Flow's own database (flow.sqlite): hundreds of the user's recordings,
     each with the text Wispr produced. We run our engine over the recordings,
     line its output up against Wispr's text word by word, and keep the
     mishearings that repeat (e.g. "sheet" -> "shit" for this voice). Terms the
     user says often (product names, jargon...) become dictionary words.
  2. The user's own corrections in SpeakOn's history (like Wispr's "user_edits").

A learned fix is only kept if it repeats and is right most of the time the
misheard phrase appears, and it is checked on recordings it was NOT learned
from before being reported.
"""

import collections
import io
import json
import os
import random
import re
import shutil
import sqlite3
import tempfile
import threading
import wave
from pathlib import Path

import numpy as np

WISPR_DB = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Wispr Flow" / "flow.sqlite"

EQUIV = {"gonna": "going to", "wanna": "want to", "gotta": "got to", "ok": "okay", "alright": "all right"}
FILLERS = {"um", "uh", "uhm", "hmm", "mm", "ah", "eh", "er", "erm"}
NUMBER_WORDS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
                   "sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety "
                   "hundred thousand million billion first second third".split())


# ---------------------------------------------------------------- text helpers

def tokens(text):
    """Words with their original spelling, plus normalised keys for matching."""
    out = []
    for raw in re.findall(r"[\w'’.\-]+", text or ""):
        raw = raw.strip(".-'’")
        if not raw:
            continue
        key = raw.lower().replace("’", "'")
        if key in FILLERS:
            continue
        for part in EQUIV.get(key, key).split():
            out.append((raw if part == key else part, part))
    return out


def align(ref, hyp):
    n, m = len(ref), len(hyp)
    d = np.zeros((n + 1, m + 1), dtype=np.int32)
    d[:, 0] = np.arange(n + 1)
    d[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, ops = n, m, []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i, j] == d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            ops.append(("=" if ref[i - 1] == hyp[j - 1] else "s", i - 1, j - 1)); i -= 1; j -= 1
        elif i > 0 and d[i, j] == d[i - 1, j] + 1:
            ops.append(("d", i - 1, None)); i -= 1
        else:
            ops.append(("i", None, j - 1)); j -= 1
    return int(d[n, m]), ops[::-1]


def wer(pairs):
    e = w = 0
    for ref, hyp in pairs:
        r = [k for _, k in tokens(ref)]
        errs, _ = align(r, [k for _, k in tokens(hyp)])
        e += errs
        w += len(r)
    return e / max(1, w)


def diff_spans(ref_text, hyp_text, max_len=3):
    """Mismatched stretches between matching words: [(hyp_words, ref_words_original_case)]"""
    ref, hyp = tokens(ref_text), tokens(hyp_text)
    _, ops = align([k for _, k in ref], [k for _, k in hyp])
    spans, cur_r, cur_h = [], [], []
    for op, i, j in ops + [("=", None, None)]:
        if op == "=":
            if cur_r and cur_h and len(cur_r) <= max_len and len(cur_h) <= max_len:
                spans.append((tuple(hyp[x][1] for x in cur_h), tuple(ref[x][0] for x in cur_r)))
            cur_r, cur_h = [], []
        else:
            if i is not None:
                cur_r.append(i)
            if j is not None:
                cur_h.append(j)
    return spans


def ngram_counts(texts, max_n=3):
    c = collections.Counter()
    for t in texts:
        ks = [k for _, k in tokens(t)]
        for n in range(1, max_n + 1):
            for i in range(len(ks) - n + 1):
                c[tuple(ks[i:i + n])] += 1
    return c


# ---------------------------------------------------------------- learning

def learn_fixes(pairs, min_count=2, min_precision=0.6):
    """pairs: [(reference_text, engine_text)] -> [{heard, wanted, count, precision}]"""
    found = collections.Counter()
    forms = collections.defaultdict(collections.Counter)
    for ref, hyp in pairs:
        for h, r in diff_spans(ref, hyp):
            key = (h, tuple(w.lower() for w in r))
            found[key] += 1
            forms[key][" ".join(r)] += 1
    occurrences = ngram_counts([h for _, h in pairs])
    fixes = []
    for (h, r_low), count in found.items():
        if count < min_count:
            continue
        if set(h) & NUMBER_WORDS or set(r_low) & NUMBER_WORDS or any(w.isdigit() for w in h + r_low):
            continue                                  # "twenty" vs "20" is formatting, not hearing
        if "".join(h).replace("'", "") == "".join(r_low).replace("'", ""):
            continue                                  # spacing / apostrophes only
        if len(h) == 1 and len(h[0]) <= 2:
            continue                                  # too short to rewrite safely
        precision = count / max(count, occurrences[h])
        if precision < min_precision or (len(h) == 1 and precision < 0.9):
            continue                                  # one word ("course") must be wrong nearly every time
        wanted = forms[(h, r_low)].most_common(1)[0][0]
        fixes.append({"heard": " ".join(h), "wanted": wanted, "count": count, "precision": round(precision, 2)})
    fixes.sort(key=lambda f: -f["count"])
    return fixes


def apply_fixes(text, fixes):
    import textproc
    return textproc.apply_replacements(text, [(f["heard"], f["wanted"]) for f in fixes])


def learn_terms(ref_texts, min_count=3):
    """Words the user says often that are not ordinary lower-case words: GitHub, PostgreSQL, API..."""
    import textproc
    counts, lower = collections.Counter(), collections.Counter()
    for t in ref_texts:
        words = re.findall(r"[A-Za-z][\w\-.]*[\w]|[A-Za-z]", t or "")
        for i, w in enumerate(words):
            lower[w.lower()] += 1
            special = any(c.isupper() for c in w[1:]) or any(c.isdigit() for c in w) or (
                w[0].isupper() and i > 0 and not re.search(r"[.!?]\s*$", t[:t.find(w)] if w in t else ""))
            if special and len(w) >= 3 and w.lower() not in textproc.COMMON_WORDS:
                counts[w] += 1
    terms = []
    for w, c in counts.most_common():
        if len(w) < 5 and sum(ch.isupper() for ch in w) < 2:
            continue                                  # short names ("Pine") would swallow "pain"
        # a term, not a normal word that happens to start a sentence: mostly written this way
        if c >= min_count and c >= 0.7 * lower[w.lower()]:
            terms.append(w)
    return terms


# ---------------------------------------------------------------- Wispr Flow

def wispr_available():
    return WISPR_DB.exists()


def wispr_copy():
    """Read-only snapshot of Wispr's database (never opened in place)."""
    tmp = Path(tempfile.mkdtemp(prefix="speakon_wispr_")) / "flow.sqlite"
    shutil.copy2(WISPR_DB, tmp)
    return tmp


def wispr_summary():
    if not wispr_available():
        return None
    db = sqlite3.connect(f"file:{wispr_copy()}?mode=ro", uri=True)
    n, audio = db.execute("select count(*), sum(case when audio is not null and length(audio)>0 then 1 else 0 end) "
                          "from History").fetchone()
    words = db.execute("select count(*) from Dictionary where isDeleted=0").fetchone()[0]
    db.close()
    return {"dictations": n, "recordings": audio or 0, "dictionary": words}


def wispr_dictionary():
    """[(heard_or_None, wanted)] - words and snippets the user set up in Wispr Flow."""
    db = sqlite3.connect(f"file:{wispr_copy()}?mode=ro", uri=True)
    rows = db.execute("select phrase, replacement, isSnippet, source from Dictionary where isDeleted=0").fetchall()
    db.close()
    out = []
    for phrase, replacement, snippet, source in rows:
        if not phrase or phrase.strip() == "Wispr Flow" or "wisprflow.ai" in (replacement or ""):
            continue
        if replacement and len(replacement) > 120:
            continue                                   # AI prompts, not text snippets
        if replacement:
            out.append((phrase.strip(), replacement.strip()))
        else:
            out.append((None, phrase.strip()))
    return out


def wispr_clips(limit=None, languages=("en",)):
    db = sqlite3.connect(f"file:{wispr_copy()}?mode=ro", uri=True)
    rows = db.execute("""select transcriptEntityId, audio, asrText, formattedText, coalesce(detectedLanguage, language)
                         from History where audio is not null and length(audio) > 0 and asrText is not null
                         order by timestamp desc""").fetchall()
    db.close()
    clips = []
    for tid, audio, asr, fmt, lang in rows:
        if languages and lang not in languages:
            continue
        with wave.open(io.BytesIO(audio)) as w:
            if w.getframerate() != 16000 or w.getnchannels() != 1:
                continue
            a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if 1.5 <= len(a) / 16000 <= 90:
            clips.append({"id": tid, "audio": a, "ref": asr, "formatted": fmt or asr})
        if limit and len(clips) >= limit:
            break
    return clips


def learn_from_wispr(engine, transcribe, progress=lambda done, total, msg: None, limit=None):
    """Run the engine over the user's Wispr recordings and learn from the differences."""
    progress(0, 1, "Reading your Wispr Flow recordings…")
    clips = wispr_clips(limit)
    pairs = []
    for i, c in enumerate(clips):
        hyp = transcribe(c["audio"])
        pairs.append((c["ref"], hyp))
        progress(i + 1, len(clips), f"Listening to your recordings… {i + 1} of {len(clips)}")
    # honest check: learn on 70 %, measure on the other 30 %
    idx = list(range(len(pairs)))
    random.Random(11).shuffle(idx)
    cut = int(len(idx) * 0.7)
    train = [pairs[i] for i in idx[:cut]]
    test = [pairs[i] for i in idx[cut:]]
    fixes_train = learn_fixes(train)
    before = wer(test)
    after = wer([(r, apply_fixes(h, fixes_train)) for r, h in test])
    fixes = learn_fixes(pairs)
    terms = learn_terms([c["formatted"] for c in clips])
    return {"fixes": fixes, "terms": terms, "clips": len(clips), "wer_before": before, "wer_after": after,
            "pairs": pairs}


# ---------------------------------------------------------------- learned store

class Learned:
    """learned.json. Re-read whenever the file changes on disk, so edits made while the app runs
    (a tool, the weekly routine, a text editor) are never overwritten by a stale in-memory copy."""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()   # callers hold it around any read-modify-write of .data
        self._data = None
        self._mtime = None
        self._refresh()

    def _refresh(self):
        with self.lock:
            try:
                mtime = self.path.stat().st_mtime
            except OSError:
                mtime = None
            if self._data is None or mtime != self._mtime:
                data = {"fixes": [], "terms": [], "clips": 0, "edits": {}}
                try:
                    data.update(json.loads(self.path.read_text(encoding="utf-8")))
                except Exception:
                    pass
                self._data, self._mtime = data, mtime

    @property
    def data(self):
        self._refresh()
        return self._data

    def save(self):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=1, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
            self._mtime = self.path.stat().st_mtime

    def replacements(self):
        with self.lock:
            return [(f["heard"], f["wanted"]) for f in self.data["fixes"] if f.get("enabled", True)]

    def merge_fixes(self, fixes, source):
        with self.lock:
            known = {f["heard"].lower(): f for f in self.data["fixes"]}
            for f in fixes:
                old = known.get(f["heard"].lower())
                if old:
                    old.update(count=max(old["count"], f["count"]), wanted=f["wanted"])
                else:
                    self.data["fixes"].append({**f, "source": source, "enabled": True})
            self.save()

    def learn_edit(self, before, after):
        """Remember a correction; returns fixes that just reached two sightings."""
        with self.lock:
            new = []
            for h, r in diff_spans(after, before):
                key = " ".join(h) + " -> " + " ".join(r)
                n = self.data["edits"].get(key, 0) + 1
                self.data["edits"][key] = n
                if n == 2 and len(" ".join(h)) > 2:
                    new.append({"heard": " ".join(h), "wanted": " ".join(r), "count": n, "precision": 1.0})
            if new:
                self.merge_fixes(new, "your edits")
            self.save()
            return new


def learn_lowercase(texts, min_count=2):
    """Words this user normally writes in lower case mid-sentence ("quicker", "and", "the").
    Used to undo the engine's habit of capitalising a word after a short pause."""
    low, cap = collections.Counter(), collections.Counter()
    for t in texts:
        for sent in re.split(r"(?<=[.!?])\s+|\n", t or ""):
            words = re.findall(r"[A-Za-z][a-z']*", sent)
            for w in words[1:]:                      # skip the sentence's first word
                if w.islower():
                    low[w] += 1
                elif w[0].isupper() and w[1:].islower():
                    cap[w.lower()] += 1
    return sorted(w for w, n in low.items() if n >= min_count and cap[w] <= n * 0.1 and w != "i")
