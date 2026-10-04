"""How much the text clean-up (dictionary, sound-alike snapping, capitals) helps or hurts, with no engine run.

  python tools/eval_textproc.py [other_textproc.py]

Uses the user's own dictionary + learned list on:
  1. Wispr Flow's raw text -> compared with Wispr's finished text (word errors, lower = better)
  2. Wispr's finished text  -> words the clean-up rewrote in text that was already right (lower = better)
  3. SpeakOn's own raw dictations (history.json) -> how many come out differently
Give a second textproc.py to compare against (e.g. the last release from git).
Prints numbers only, unless --show is given (then the changed words, on this computer only).
"""
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import config as C  # noqa: E402
from eval_wispr import align, norm  # noqa: E402


def load_textproc(path):
    spec = importlib.util.spec_from_file_location("tp_" + str(abs(hash(path))), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wispr_texts():
    import learn
    with learn.wispr_db() as db:
        rows = db.execute("select asrText, formattedText, coalesce(detectedLanguage, language) from History "
                          "where asrText is not null and formattedText is not null").fetchall()
    return [(a, f) for a, f, lang in rows if lang == "en" and a.strip() and f.strip()]


def main():
    show = "--show" in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    paths = [os.path.join(os.path.dirname(__file__), "..", "textproc.py")] + paths
    settings = {**C.DEFAULT_SETTINGS, **json.loads(C.SETTINGS_FILE.read_text(encoding="utf-8"))}
    dictionary = C.DICTIONARY_FILE.read_text(encoding="utf-8") if C.DICTIONARY_FILE.exists() else ""
    learned = json.loads(C.LEARNED_FILE.read_text(encoding="utf-8")) if C.LEARNED_FILE.exists() else {}
    fixes = [(f["heard"], f["wanted"]) for f in learned.get("fixes", []) if f.get("enabled", True)]
    terms, lower = learned.get("terms", []), learned.get("lowercase", [])
    texts = wispr_texts()
    hist = json.loads(C.HISTORY_FILE.read_text(encoding="utf-8")) if C.HISTORY_FILE.exists() else []
    raws = [h["raw"] for h in hist if h.get("raw") and h["raw"].isascii()]
    outs = {}
    for p in paths:
        tp = load_textproc(p)

        def clean(t):
            return tp.process(t, settings, True, dictionary, fixes, terms, lower)[0]
        errs = words = rewrites = 0
        for asr, fmt in texts:
            ref = norm(fmt)
            errs += align(ref, norm(clean(asr)))[0]
            words += len(ref)
            e, pairs = align(ref, norm(clean(fmt)))
            rewrites += e
            if show and e:
                print("  rewrote:", [(r, h) for r, h in pairs if r != h])
        outs[p] = [clean(r) for r in raws]
        print(f"{os.path.basename(os.path.dirname(os.path.abspath(p)))}/{os.path.basename(p)}: "
              f"Wispr raw -> finished {errs / max(1, words) * 100:.2f}% word errors ({errs} of {words}); "
              f"rewrote {rewrites} words of already-right text ({len(texts)} recordings)")
    if len(paths) > 1:
        a, b = outs[paths[0]], outs[paths[1]]
        diff = [(x, y) for x, y in zip(a, b) if x != y]
        print(f"your {len(raws)} SpeakOn dictations: {len(diff)} come out differently")
        if show:
            for x, y in diff:
                print("  this:", x, "\n  other:", y)


if __name__ == "__main__":
    main()
