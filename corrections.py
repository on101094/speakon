"""Learn from corrections the user makes right after dictating (like Wispr Flow).

After SpeakOn inserts text, it watches that one text box for a short while through
Windows UI Automation (the accessibility interface screen readers use). It only
reads the box it just typed into, never keystrokes, and skips password fields.
When the watch ends (time is up, the user moved on, or dictated again), the
inserted text is lined up against what the box now contains. A word the user
replaced with a similar-looking or similar-sounding word ("replicanto" ->
"Replikanto") is reported as a correction to remember. Rewording ("the" -> "a"),
new sentences and deletions are ignored.
"""

import difflib
import logging
import re
import threading
import time

import textproc

WATCH_SECONDS = 90
log = logging.getLogger("speakon")
POLL_SECONDS = 1.0
MAX_CHARS = 30000


def _words(text):
    """[(original word without surrounding punctuation, key)]"""
    out = []
    for raw in re.findall(r"\S+", text or ""):
        w = raw.strip(".,!?;:\"'()[]{}“”‘’…")
        if w:
            out.append((w, "".join(c for c in w.lower() if c.isalnum())))
    return out


def looks_like_correction(old, new, ordinary=()):
    """Is `new` a corrected spelling of `old` (not a different word the user chose instead)?"""
    ko = "".join(c for c in old.lower() if c.isalnum())
    kn = "".join(c for c in new.lower() if c.isalnum())
    if not ko or not kn or ko == kn and old == new:
        return False
    common = textproc.COMMON_WORDS | textproc.EVERYDAY_WORDS | set(ordinary)
    old_words, new_words = set(old.lower().split()), set(new.lower().split())
    if old_words <= common and new_words <= common:
        return False                                  # grammar / wording change, e.g. "the" -> "a"
    if ko == kn:
        return len(kn) >= 3 and any(c.isupper() for c in new)  # capitalisation of a name: "orb" -> "ORB"
    if len(kn) < 3:
        return False
    short, long_ = sorted((ko, kn), key=len)
    if len(long_) - len(short) >= 3 and (long_.startswith(short) or long_.endswith(short)):
        return False                                  # words added or removed, not a new spelling
    dist = textproc._levenshtein(ko, kn) / max(len(ko), len(kn))
    sounds = ko.isalpha() and kn.isalpha() and textproc._soundex(ko) == textproc._soundex(kn)
    return dist <= 0.34 or (sounds and dist <= 0.5)


def find_corrections(inserted, now, ordinary=()):
    """Line up the text SpeakOn inserted with what the box contains now -> [(old, new)]"""
    ins, cur = _words(inserted), _words(now)
    if not ins or not cur:
        return []
    ik, ck = [k for _, k in ins], [k for _, k in cur]
    sm = difflib.SequenceMatcher(None, ik, ck, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    if sum(b.size for b in blocks) < 0.5 * len(ik):
        return []                                     # our text is (mostly) gone: nothing to learn
    first, last = blocks[0], blocks[-1]
    f0 = max(0, first.b - first.a)
    f1 = min(len(ck), last.b + last.size + (len(ik) - last.a - last.size))
    region = cur[f0:f1]
    sm = difflib.SequenceMatcher(None, ik, [k for _, k in region], autojunk=False)
    found = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":                             # same letters, different capitals: "orb" -> "ORB"
            for (o, _), (n, _) in zip(ins[a0:a1], region[b0:b1]):
                if o != n and looks_like_correction(o, n, ordinary):
                    found.append((o, n))
            continue
        if op != "replace" or a1 - a0 > 2 or b1 - b0 > 2:
            continue
        old = " ".join(w for w, _ in ins[a0:a1])
        new = " ".join(w for w, _ in region[b0:b1])
        if looks_like_correction(old, new, ordinary):
            found.append((old, new))
    return found


class EditWatcher:
    def __init__(self, on_corrections, ordinary=lambda: ()):
        self.on_corrections = on_corrections
        self.ordinary = ordinary
        self.current = None
        self.lock = threading.Lock()

    def watch(self, inserted, control=None):
        """Start watching the focused text box (or `control`) after inserting `inserted`."""
        with self.lock:
            if self.current:
                self.current.set()                    # finish the previous watch first
            stop = threading.Event()
            self.current = stop
        threading.Thread(target=self._run, args=(inserted, control, stop), daemon=True).start()

    def stop(self):
        with self.lock:
            if self.current:
                self.current.set()

    @staticmethod
    def _read(ctrl):
        import uiautomation as auto
        try:
            if ctrl.GetPropertyValue(auto.PropertyId.IsPasswordProperty):
                return None
        except Exception:
            pass
        for get in (lambda: ctrl.GetValuePattern().Value,
                    lambda: ctrl.GetTextPattern().DocumentRange.GetText(MAX_CHARS)):
            try:
                text = get()
                if isinstance(text, str) and text:
                    return text[:MAX_CHARS]
            except Exception:
                continue
        return None

    def _run(self, inserted, control, stop):
        import uiautomation as auto
        try:
            with auto.UIAutomationInitializerInThread():
                ctrl = control or auto.GetFocusedControl()
                if ctrl is None:
                    return
                key = "".join(k for _, k in _words(inserted))
                last = None
                for _ in range(10):                   # the paste may land a moment later
                    text = self._read(ctrl)
                    if text and key[:40] in "".join(k for _, k in _words(text)):
                        last = text
                        break
                    if stop.wait(0.2):
                        return
                if last is None:
                    log.info("correction watch: could not read the text box in this app")
                    return                            # can't read this box, or our text isn't there
                deadline = time.time() + WATCH_SECONDS
                while time.time() < deadline and not stop.wait(POLL_SECONDS):
                    text = self._read(ctrl)
                    if text is None:
                        break                         # box closed
                    if not find_corrections(inserted, text, ()) and difflib.SequenceMatcher(
                            None, key, "".join(k for _, k in _words(text))).find_longest_match(
                            0, len(key), 0, len("".join(k for _, k in _words(text)))).size < 0.5 * len(key):
                        break                         # message sent / box cleared: keep the last reading
                    last = text
                pairs = find_corrections(inserted, last, self.ordinary())
                log.info("correction watch ended: box readable, %d change(s) learned", len(pairs))
                if pairs:
                    self.on_corrections(pairs)
        except Exception:
            log.exception("correction watch failed")


if __name__ == "__main__":
    tests = [
        ("For example, replicanto. It writes it with C.", "For example, Replikanto. It writes it with C."),
        ("we use the orb setup", "we use the ORB setup"),
        ("I think the plan is good", "I think a plan is good"),
        ("send it to Take Profit Rader today", "send it to Take Profit Trader today"),
        ("hello there", "completely different text now"),
        ("The long worked twice", "The long walked twice"),
        ("open the TradingView MCP now", "open the TradingView-MCP folder now"),
    ]
    for ins, now in tests:
        print(f"{ins!r} -> {now!r}: {find_corrections(ins, now)}")
