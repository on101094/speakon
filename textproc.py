"""Clean-up applied to every transcript before it is pasted.

Ideas taken from the source apps:
  - filler removal and stutter collapsing (Handy, FluidVoice)
  - fuzzy "custom words": edit distance + Soundex over 1-3 word n-grams, so
    "chat GPT" / "charge be" snap to "ChatGPT" / "ChargeBee" (Handy)
  - "heard -> wanted" corrections, longest first, whole matches only, glued
    forms still match ("CloudCode", "cloud-code"), never touching "Cloudflare";
    every fix that fires is reported so history can show it (murmur)
  - warnings for entries that would rewrite ordinary words (murmur)
  - spoken commands: "new line", "new paragraph", "comma", ... (FluidVoice)
"""

import re
import unicodedata

UNIVERSAL_FILLERS = {"uh", "uhm", "umm", "uhh", "uhhh", "ehh", "ehm", "ahm", "hmm", "hm", "mmm", "erm"}
ENGLISH_FILLERS = {"um", "ah", "eh"}
WORD_CORRECTION_THRESHOLD = 0.18  # Handy's default

SPOKEN_COMMANDS = [
    ("new paragraph", "\n\n"),
    ("new line", "\n"),
    ("question mark", "?"),
    ("exclamation mark", "!"),
    ("exclamation point", "!"),
    ("full stop", "."),
    ("period", "."),
    ("comma", ","),
    ("semicolon", ";"),
    ("colon", ":"),
]

COMMON_WORDS = set("""a about all also and any are as at back be because but by call can case check class
close cloud code come could data day did do does down each even file find first for from get give go good
great group had has have he her here him his how i if in into is it its just key know like line list look
make man many may me more most my need new no not now number of off on one only open or other our out over
page part people point put read right run said same say see set she should show side so some state still
such take team test than that the their them then there these they thing think this time to two type up us
use user very want was way we well were what when where which who will with word work would year you your""".split())

DEFAULT_DICTIONARY = """# SpeakOn dictionary - one entry per line. Lines starting with # are ignored.
#
# A word or name you want spelled right (sound-alikes get snapped to it):
#   ChatGPT
#   Supabase
#
# A fix, when you hear X write Y (always applied, whole words only):
#   cloud code -> Claude Code
#   speak on -> SpeakOn
"""


# ---------------------------------------------------------------- dictionary

def parse_dictionary(raw):
    """Returns (terms, [(heard, wanted), ...])."""
    terms, replacements = [], []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "->" in line:
            heard, wanted = (p.strip() for p in line.split("->", 1))
            if heard:
                replacements.append((heard, wanted))
        else:
            terms.append(line)
    return terms, replacements


def _split_words(phrase):
    return [w for w in re.split(r"[\s\-]+", phrase) if w]


def apply_replacements(text, replacements, fixes=None):
    """The guaranteed pass: longest trigger first, whole matches only, glued forms match."""
    text = unicodedata.normalize("NFC", text)
    for heard, wanted in sorted(replacements, key=lambda r: len(r[0]), reverse=True):
        words = [re.escape(w) for w in _split_words(unicodedata.normalize("NFC", heard))]
        if not words:
            continue
        pattern = r"(?<!\w)" + r"[\s\-]*".join(words) + r"(?!\w)"
        found = re.search(pattern, text, flags=re.IGNORECASE)
        if found:
            if fixes is not None and found.group(0) != wanted:
                fixes.append((found.group(0), wanted))
            text = re.sub(pattern, lambda _m, w=wanted: w, text, flags=re.IGNORECASE)
    return text


def dictionary_warnings(line):
    """Warnings for one dictionary line (empty list = looks safe)."""
    line = line.strip()
    if not line or line.startswith("#"):
        return []
    out = []
    if "->" in line:
        heard, wanted = (p.strip() for p in line.split("->", 1))
        words = _split_words(heard)
        if len(words) == 1 and words[0].lower() in COMMON_WORDS:
            out.append(f'"{heard}" is an ordinary word - every use of it will be rewritten. Use a longer phrase.')
        elif len(words) == 1 and len(words[0]) <= 3:
            out.append(f'"{heard}" is very short and will match often. Use a longer phrase.')
        if heard == wanted:
            out.append(f'This rewrites "{heard}" to itself, so it changes nothing.')
        if not wanted:
            out.append(f'"{heard}" will be deleted from your text.')
    else:
        k = _key(line)
        if k in COMMON_WORDS:
            out.append(f'"{line}" is an ordinary word - sound-alikes will be changed to this spelling.')
        elif len(k) <= 3:
            out.append(f'"{line}" is very short, so sound-alike words may be snapped to it.')
    return out


# ---------------------------------------------------------------- fuzzy custom words (port of Handy)

def _key(word):
    return "".join(c.lower() for c in word if c.isalnum())


def _soundex(s):
    codes = {**dict.fromkeys("bfpv", "1"), **dict.fromkeys("cgjkqsxz", "2"),
             **dict.fromkeys("dt", "3"), "l": "4", **dict.fromkeys("mn", "5"), "r": "6"}
    s = s.lower()
    out, last = s[0].upper(), codes.get(s[0], "")
    for ch in s[1:]:
        code = codes.get(ch, "")
        if code and code != last:
            out += code
        if ch not in "hw":
            last = code
    return (out + "000")[:4]


def _levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _split_punct(word):
    start = next((i for i, c in enumerate(word) if c.isalnum()), len(word))
    end = next((i for i in range(len(word), 0, -1) if word[i - 1].isalnum()), 0)
    return word[:start], word[end:] if end else ""


def _best_match(candidate, entries):
    if not candidate or not candidate.isascii() or not candidate.isalnum() or len(candidate) > 50:
        return None
    best, best_score = None, WORD_CORRECTION_THRESHOLD
    for word, key in entries:
        max_len = max(len(candidate), len(key))
        if abs(len(candidate) - len(key)) > max(max_len * 0.25, 2.0):
            continue
        score = _levenshtein(candidate, key) / max_len
        if candidate.isalpha() and key.isalpha() and _soundex(candidate) == _soundex(key):
            score *= 0.3
        if score < best_score:
            best, best_score = word, score
    return (best, best_score) if best else None


def _keep_case(original, replacement):
    letters = [c for c in original if c.isalpha()]
    if len(letters) > 1 and all(c.isupper() for c in letters):
        return replacement.upper()
    return replacement


def apply_custom_words(text, terms, fixes=None, protected=()):
    # emails, file names, web addresses and codes are literal: never matched by sound
    entries = [(t, _key(t)) for t in terms if _key(t) and _key(t).isascii()
               and not re.search(r"[@/_]|\.\w", t) and sum(c.isdigit() for c in t) <= 2]
    if not entries:
        return text
    protected = {_key(w) for p in protected for w in p.split()} - {""}
    words = text.split(" ")
    out, i = [], 0
    while i < len(words):
        best = None
        for n in (3, 2, 1):
            if i + n > len(words):
                continue
            chunk = words[i:i + n]
            if any(_split_punct(w)[1] or "\n" in w for w in chunk[:-1]):  # don't cross punctuation
                continue
            if n == 1 and _key(chunk[0]) in COMMON_WORDS:   # never turn "cloud" into "Claude"
                continue
            if any("@" in w or "://" in w for w in chunk):
                continue
            if any(_key(w) in protected for w in chunk):
                continue                              # a fix already wrote this word on purpose
            cand = "".join(_key(w) for w in chunk)
            if any(cand in (k + "s", k + "es", k + "'s") for _, k in entries):
                continue                              # plural / possessive of a term: leave it
            m = _best_match(cand, entries)
            if m and (best is None or m[1] < best[2]):
                best = (n, m[0], m[1])
        if best:
            n, word, _ = best
            prefix, _ = _split_punct(words[i])
            _, suffix = _split_punct(words[i + n - 1])
            fixed = _keep_case(words[i], word)
            if n == 1 and word.islower() and _key(words[i]) == _key(word):
                fixed = " ".join(words[i:i + n])[len(prefix):]  # same word: never lower-case what was said
                fixed = fixed[:len(fixed) - len(_split_punct(words[i + n - 1])[1])] if _split_punct(words[i + n - 1])[1] else fixed
            original = " ".join(words[i:i + n])[len(prefix):len(" ".join(words[i:i + n])) - len(suffix)]
            if fixes is not None and original != fixed:
                fixes.append((original, fixed))
            out.append(prefix + fixed + suffix)
            i += n
        else:
            out.append(words[i])
            i += 1
    return " ".join(out)


# ---------------------------------------------------------------- fillers, stutters, commands

def remove_fillers(text, english):
    fillers = UNIVERSAL_FILLERS | (ENGLISH_FILLERS if english else set())
    alt = "|".join(sorted(map(re.escape, fillers), key=len, reverse=True))
    text = re.sub(r"(?<!\w)(?:" + alt + r")(?!\w)[,.…]*", "", text, flags=re.IGNORECASE)
    return tidy(text)


def collapse_stutters(text):
    # "I I I I think" -> "I think" (3+ repeats, like Handy)
    return re.sub(r"(?i)\b(\w+)(?:[\s,]+\1\b){2,}", r"\1", text)


def apply_spoken_commands(text):
    for phrase, symbol in SPOKEN_COMMANDS:
        pat = r"[\s,.]*(?<!\w)" + phrase.replace(" ", r"\s+") + r"(?!\w)[,.!?]*[ \t]*"
        rep = symbol if symbol.startswith("\n") else symbol + " "
        text = re.sub(pat, lambda _m, r=rep: r, text, flags=re.IGNORECASE)
    text = re.sub(r"([.!?]\s+|\n)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text.strip(" ")


EVERYDAY_WORDS = set("""a about after again all also am an and any are as at back be because been before being
better both but by can could did do does doing done down each even ever every few for from get gets getting go
goes going good got had has have having he her here him his how if in into is it its just know last less let like
more most much must my need never new next no not now of off on once one only or other our out over own quick
quicker quickly really right same see she should so some still such than that the their them then there these
they thing things think this those through to too under until up us very want wanted was way we well were what
when where which while who why will with without would yes yet you your""".split())


def fix_midsentence_caps(text, lowercase_words=(), protected=()):
    """The engine capitalises a word after a short pause ("with C And replikanto", "It's in fact Quicker").
    Lower-case such words when they are ordinary words this user normally writes in lower case."""
    words = set(lowercase_words) | EVERYDAY_WORDS
    keep = {p.lower() for p in protected if any(c.isupper() for c in p)}   # names only, not "by the way"

    def fix(m):
        word, i = m.group(0), m.start()
        before = text[:i].rstrip(" ")
        if i == 0 or text[i - 1] not in " ,;(" or not before or before[-1] in '.!?:\n"“':
            return word                               # sentence start, or not a separate word
        low = word.lower()
        if low in words and low not in keep and low != "i" and not low.startswith("i'"):
            return low
        return word
    return re.sub(r"\b[A-Z][a-z']+\b", fix, text)


def tidy(text):
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,;:])(?=[.!?])", "", text)       # ", ." -> "."
    text = re.sub(r"^[\s,.;:]+", "", text)
    text = text.strip()
    if text[:1].islower():
        text = text[0].upper() + text[1:]
    return text


def process(text, settings, english, dictionary="", extra_fixes=(), extra_terms=(), lowercase_words=()):
    """Returns (clean text, [(heard, written), ...] dictionary fixes that fired).
    extra_fixes / extra_terms / lowercase_words: what SpeakOn learned about this user."""
    fixes = []
    if not text:
        return text, fixes
    if settings.get("remove_fillers", True):
        text = remove_fillers(text, english)
        text = collapse_stutters(text)
    terms, replacements = parse_dictionary(dictionary)
    known = {h.lower() for h, _ in replacements}
    replacements += [(h, w) for h, w in extra_fixes if h.lower() not in known]
    terms += [t for t in extra_terms if t not in terms]
    text = apply_replacements(text, replacements, fixes)
    if settings.get("fuzzy_words", True):
        text = apply_custom_words(text, terms, fixes, [w for _, w in replacements if w])
    if english:
        protected = terms + [w for _, w in replacements]
        text = fix_midsentence_caps(text, lowercase_words, [p for t in protected for p in t.split()])
    if settings.get("spoken_commands", False):
        text = apply_spoken_commands(text)
    return tidy(text), fixes


if __name__ == "__main__":
    d = "ChatGPT\nChargeBee\nKubernetes\nspeak on -> SpeakOn\ncloud code -> Claude Code\nClaude"
    s = {"spoken_commands": True}
    tests = [
        "Um, so I asked chat GPT about uh the charge be invoice.",
        "I I I I think we should use kubernetes, new line and speak on comma really",
        "hmm okay period new paragraph next point question mark",
        "I opened CloudCode and Cloud-code, then checked Cloudflare and the cloud.",
    ]
    for t in tests:
        print(repr(t), "\n  ->", process(t, s, True, d))
    for line in ["code -> Claude Code", "cloud code -> Claude Code", "the", "Supabase", "ai -> AI"]:
        print(line, "=>", dictionary_warnings(line))
