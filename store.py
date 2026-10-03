"""What SpeakOn saves: settings, dictation history and the custom dictionary, behind one lock.

The window's API calls, the dictation controller and worker threads all read and change these,
so every change and every save goes through here. Callers get copies or plain values back and
never hold the lock themselves."""

import json
import threading
import uuid
from pathlib import Path

import config as C
import textproc
from learn import entry_id

HISTORY_LIMIT = 5000


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


class Store:
    def __init__(self):
        self.lock = threading.RLock()
        # settings: read freely (one dict, never replaced); change only through set_setting()
        self.settings = {**C.DEFAULT_SETTINGS, **load_json(C.SETTINGS_FILE, {})}
        if self.settings["hotkey"] != "custom" and self.settings["hotkey"] not in C.HOTKEY_PRESETS:
            self.settings["hotkey"] = "ctrl_win"
        self.history = load_json(C.HISTORY_FILE, [])
        for h in self.history:  # older history.json files have no ids
            h.setdefault("id", uuid.uuid4().hex)
        self.history_version = 0  # the window re-reads history when this changes
        self.load_dictionary()

    # ----- settings
    def save_settings(self):
        with self.lock:   # one writer at a time: save_json reuses settings.tmp
            save_json(C.SETTINGS_FILE, self.settings)

    def set_setting(self, key, value, save=True):
        """Change (and save) one setting; returns the old value."""
        with self.lock:
            old = self.settings.get(key)
            self.settings[key] = value
            if save:
                self.save_settings()
            return old

    # ----- history (newest first)
    def save_history(self):
        with self.lock:
            save_json(C.HISTORY_FILE, self.history)
            self.history_version += 1

    def add_history(self, entry):
        with self.lock:
            self.history.insert(0, {"id": uuid.uuid4().hex, **entry})
            del self.history[HISTORY_LIMIT:]
            self.save_history()

    def recent_history(self, n=None):
        with self.lock:
            return list(self.history[:n])

    def _history_entry(self, hid):
        return next((h for h in self.history if h.get("id") == hid), None)

    def history_text(self, hid):
        with self.lock:
            h = self._history_entry(hid)
            return h["text"] if h else None

    def delete_history(self, hid):
        with self.lock:
            h = self._history_entry(hid)
            if h:
                self.history.remove(h)
                self.save_history()

    def edit_history(self, hid, text):
        """Replace an entry's text; returns the text it had, or None if the entry is gone."""
        with self.lock:
            h = self._history_entry(hid)
            if not h:
                return None
            before = h["text"]
            h["text"] = text.strip()
            h["edited"] = True
            self.save_history()
            return before

    # ----- dictionary (dictionary.txt; may also be edited by hand while the app runs)
    def load_dictionary(self):
        with self.lock:
            if not C.DICTIONARY_FILE.exists():
                C.DICTIONARY_FILE.write_text(textproc.DEFAULT_DICTIONARY, encoding="utf-8")
            self.dictionary = C.DICTIONARY_FILE.read_text(encoding="utf-8")
            self.dictionary_mtime = C.DICTIONARY_FILE.stat().st_mtime

    def reload_dictionary(self):
        """Pick up edits made to the file outside the app; returns the current text."""
        with self.lock:
            try:
                if C.DICTIONARY_FILE.stat().st_mtime != self.dictionary_mtime:
                    self.load_dictionary()
            except OSError:
                pass
            return self.dictionary

    def set_dictionary(self, text):
        with self.lock:
            C.DICTIONARY_FILE.write_text(text, encoding="utf-8")
            self.load_dictionary()

    def _dictionary_line(self, lines, eid):
        return next((n for n, line in enumerate(lines) if line.strip() and entry_id("d", line.strip()) == eid), None)

    def save_dictionary_entry(self, eid, line):
        """Replace the line with id `eid`, or add `line` at the end if there is none."""
        with self.lock:
            lines = self.dictionary.splitlines()
            n = self._dictionary_line(lines, eid) if eid else None
            if n is not None:
                lines[n] = line
            else:
                lines.append(line)
            self.set_dictionary("\n".join(lines) + "\n")

    def delete_dictionary_entry(self, eid):
        with self.lock:
            lines = self.dictionary.splitlines()
            n = self._dictionary_line(lines, eid)
            if n is not None:
                del lines[n]
                self.set_dictionary("\n".join(lines) + "\n")

    def add_dictionary_lines(self, lines, heading):
        """Append the lines not already in the dictionary under a `# heading`; returns those added."""
        with self.lock:
            existing = {line.strip().lower() for line in self.dictionary.splitlines()}
            added = [line for line in lines if line.lower() not in existing]
            if added:
                self.set_dictionary(self.dictionary.rstrip("\n") + f"\n# {heading}\n" + "\n".join(added) + "\n")
            return added
