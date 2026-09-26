"""SpeakOn - fast, private voice-to-text for Windows.

Hold Ctrl + Win (Wispr Flow's key), speak, let go: your words appear wherever
the cursor is. Everything runs on this computer. Built from SpeakType,
FluidVoice, Handy and murmur, and it learns from your own Wispr Flow history.
"""

import ctypes
import json
import math
import os
import queue
import struct
import sys
import threading
import time
import wave
import winreg
import winsound
from datetime import date, datetime, timedelta
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

import numpy as np
import pyperclip
import pystray
import sounddevice as sd
import webview
from PIL import Image
from pynput import keyboard

import config as C
import engine as eng
import learn
import textproc
from hotkeys import HotkeyWatcher
from overlay import FlowBar

HISTORY_LIMIT = 5000
MIN_SECONDS = 0.3
TAP_SECONDS = 0.35
TYPE_LIMIT = 200
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def resource(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / name


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


def foreground_app():
    try:
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = kernel32.OpenProcess(0x1000, False, pid.value)
        if not h:
            return ""
        buf = ctypes.create_unicode_buffer(512)
        size = ctypes.c_ulong(512)
        ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        kernel32.CloseHandle(h)
        return Path(buf.value).stem if ok else ""
    except Exception:
        return ""


def modifiers_down():
    return any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C))


def set_start_with_windows(enabled):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            if getattr(sys, "frozen", False):
                cmd = f'"{sys.executable}" --tray'
            else:
                cmd = f'"{Path(sys.executable).with_name("pythonw.exe")}" "{Path(__file__).resolve()}" --tray'
            winreg.SetValueEx(key, C.APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, C.APP_NAME)
            except FileNotFoundError:
                pass


def make_tone(path, freqs, ms=60, volume=0.14):
    rate = 44100
    frames = bytearray()
    for f in freqs:
        n = int(rate * ms / 1000)
        for i in range(n):
            env = min(1.0, i / (rate * 0.004)) * min(1.0, (n - i) / (rate * 0.025))
            frames += struct.pack("<h", int(32767 * volume * env * math.sin(2 * math.pi * f * i / rate)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


class FakeMic:
    """Plays a 16 kHz mono .wav into the pipeline in real time (testing without a microphone)."""

    def __init__(self, path, callback):
        with wave.open(path) as w:
            self.audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        self.callback = callback
        self.running = False

    def start(self):
        self.running = True

        def run():
            silence = np.zeros(eng.BLOCK, np.float32)
            i = 0
            while self.running:
                block = self.audio[i:i + eng.BLOCK] if i + eng.BLOCK <= len(self.audio) else silence
                self.callback(block.reshape(-1, 1), eng.BLOCK, None, None)
                i += eng.BLOCK
                time.sleep(eng.BLOCK / eng.SAMPLE_RATE)
        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self.running = False

    def close(self):
        pass


# ---------------------------------------------------------------- the app

class SpeakOn:
    def __init__(self, start_hidden=False):
        C.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.settings = {**C.DEFAULT_SETTINGS, **load_json(C.SETTINGS_FILE, {})}
        if self.settings["hotkey"] != "custom" and self.settings["hotkey"] not in C.HOTKEY_PRESETS:
            self.settings["hotkey"] = "ctrl_win"
        self.history = load_json(C.HISTORY_FILE, [])
        self.history_version = 0
        self.learned = learn.Learned(C.LEARNED_FILE)
        self.load_dictionary()
        self.events = queue.Queue()
        self.engine = eng.Engine(C.MODELS_DIR)
        self.stream = None
        self.dictation = None
        self.recording = self.latched = self.from_button = self.busy = False
        self.level = 0.0
        self.levels = [0.0] * 18
        self.preview = ""
        self.status = "Starting…"
        self.learning = {"running": False, "progress": 0, "message": "", "finished_at": None}
        self.window = None
        self.quitting = False
        self.kb = keyboard.Controller()
        self.sound_start, self.sound_stop = C.DATA_DIR / "start.wav", C.DATA_DIR / "stop.wav"
        if not self.sound_start.exists():
            make_tone(self.sound_start, [740, 988])
            make_tone(self.sound_stop, [988, 740])

        self.keys = HotkeyWatcher(
            on_down=lambda: self.events.put(("hot_down", time.time())),
            on_up=lambda: self.events.put(("hot_up", time.time())),
            on_other=lambda: self.events.put(("other_key",)),
            on_esc=lambda: self.events.put(("esc",)))
        self.keys.set_combo(C.hotkey_keys(self.settings))
        self.keys.start()
        self.bar = FlowBar(self.bar_state)
        self.tray = pystray.Icon(C.APP_NAME, Image.open(resource("assets/icon.png")), C.APP_NAME, self.tray_menu())
        self.tray.run_detached()
        threading.Thread(target=self.controller, daemon=True).start()
        self.load_model()
        self.start_hidden = start_hidden

    # ----- persistence
    def save_settings(self):
        save_json(C.SETTINGS_FILE, self.settings)

    def save_history(self):
        save_json(C.HISTORY_FILE, self.history)
        self.history_version += 1

    def load_dictionary(self):
        if not C.DICTIONARY_FILE.exists():
            C.DICTIONARY_FILE.write_text(textproc.DEFAULT_DICTIONARY, encoding="utf-8")
        self.dictionary = C.DICTIONARY_FILE.read_text(encoding="utf-8")
        self.dictionary_mtime = C.DICTIONARY_FILE.stat().st_mtime

    def reload_dictionary(self):
        try:
            if C.DICTIONARY_FILE.stat().st_mtime != self.dictionary_mtime:
                self.load_dictionary()
        except OSError:
            pass

    def set_dictionary(self, text):
        C.DICTIONARY_FILE.write_text(text, encoding="utf-8")
        self.load_dictionary()

    def update_setting(self, key, value):
        if key == "mic":
            value = None if value in (None, "", "None") else int(value)
        old = self.settings.get(key)
        self.settings[key] = value
        self.save_settings()
        if key == "model" and value != old:
            self.load_model()
        if key in ("hotkey", "custom_hotkey"):
            self.keys.set_combo(C.hotkey_keys(self.settings))
        if key == "start_with_windows":
            try:
                set_start_with_windows(bool(value))
            except Exception as e:
                self.notify(f"Could not change the startup setting: {e}")
        self.tray.update_menu()

    # ----- status / stats
    def set_status(self, text):
        self.status = text
        try:
            self.tray.title = f"{C.APP_NAME} · {text}"[:127]
            self.tray.update_menu()
        except Exception:
            pass

    def notify(self, text):
        try:
            self.tray.notify(text[:250], C.APP_NAME)
        except Exception:
            pass

    def stats(self):
        today = date.today()
        days = {h["time"][:10] for h in self.history}
        streak, d = 0, today
        if d.isoformat() not in days:
            d -= timedelta(days=1)
        while d.isoformat() in days:
            streak += 1
            d -= timedelta(days=1)
        week = (today - timedelta(days=6)).isoformat()
        recent = [h for h in self.history if h["time"][:10] >= week]
        words = sum(len(h["text"].split()) for h in recent)
        secs = sum(h.get("seconds", 0) for h in recent if not h.get("file"))
        waits = [h["latency"] for h in self.history[:50] if "latency" in h]
        return {"streak": streak, "words_week": words,
                "wpm": int(sum(len(h["text"].split()) for h in recent if not h.get("file")) / (secs / 60)) if secs > 20 else 0,
                "avg_wait": sum(waits) / len(waits) if waits else None}

    def bar_state(self):
        return {"recording": self.recording and not self.from_button, "busy": self.busy and not self.from_button,
                "level": self.level, "preview": self.preview if self.settings["live_preview"] else "",
                "latched": self.latched, "idle_bar": self.settings.get("always_show_bar", True)}

    def tray_menu(self):
        return pystray.Menu(
            pystray.MenuItem(lambda _: self.status, None, enabled=False),
            pystray.MenuItem(lambda _: f"Hold {C.hotkey_label(self.settings)} to dictate", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open SpeakOn", lambda: self.show_window("home"), default=True),
            pystray.MenuItem("Dictionary", lambda: self.show_window("dictionary")),
            pystray.MenuItem("Settings", lambda: self.show_window("settings")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit SpeakOn", lambda: self.quit()),
        )

    def show_window(self, page=None):
        if self.window:
            self.window.show()
            self.window.restore()
            if page:
                try:
                    self.window.evaluate_js(f"showPage({json.dumps(page)})")
                except Exception:
                    pass

    def quit(self):
        self.quitting = True
        self.close_stream()
        self.keys.stop()
        self.tray.stop()
        if self.window:
            self.window.destroy()

    def load_model(self):
        def work():
            try:
                self.engine.load(self.settings["model"], self.set_status)
            except Exception as e:
                self.notify(f"Could not load the speech model: {e}")
        threading.Thread(target=work, daemon=True).start()

    # ----- controller thread
    def controller(self):
        while True:
            ev = self.events.get()
            try:
                getattr(self, "do_" + ev[0])(*ev[1:])
            except Exception as e:
                self.set_status(f"Error: {e}")

    def do_hot_down(self, t):
        if self.recording:
            if self.latched:
                self.do_stop()
            return
        self.pressed_at = t
        self.do_start()

    def do_hot_up(self, t):
        if not self.recording or self.latched:
            return
        mode = self.settings["mode"]
        if mode == "toggle" or (mode == "smart" and t - self.pressed_at < TAP_SECONDS):
            self.latched = True
        else:
            self.do_stop()

    def do_other_key(self):
        if self.recording and not self.latched and not self.from_button:
            self.do_cancel()

    def do_esc(self):
        if self.recording:
            self.do_cancel()

    def do_toggle(self):
        if self.recording:
            self.do_stop()
        else:
            self.do_start(True)

    def hotwords(self):
        terms, _ = textproc.parse_dictionary(self.dictionary)
        return ", ".join((terms + self.learned.data.get("terms", []))[:30])  # short: long prompts drift

    def do_start(self, from_button=False):
        if self.recording or self.busy:
            return
        if self.engine.error and not self.engine.model_id:
            self.notify("No speech model loaded - open Settings and pick a model.")
            return
        s = self.settings
        self.reload_dictionary()
        lang = None if s["language"] == "auto" else s["language"]
        self.preview = ""
        d = self.dictation = eng.Dictation(self.engine, lang, self.hotwords(), s["live_preview"],
                                           on_preview=self.set_preview)

        def callback(indata, frames, t, status):
            block = indata[:, 0].copy()
            self.level = eng.block_rms(block)
            d.feed(block)

        fake = os.environ.get("SPEAKON_FAKE_MIC")
        try:
            if fake:
                self.stream = FakeMic(fake, callback)
            else:
                self.stream = sd.InputStream(samplerate=eng.SAMPLE_RATE, channels=1, dtype="float32",
                                             blocksize=eng.BLOCK, device=s["mic"], callback=callback)
            self.stream.start()
        except Exception as e:
            d.cancel()
            self.notify(f"Microphone problem: {e}")
            return
        self.recording = True
        self.from_button = from_button
        self.latched = from_button
        self.target_app = "" if from_button else foreground_app()
        self.play(self.sound_start)

    def close_stream(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def do_cancel(self):
        self.recording = False
        self.close_stream()
        if self.dictation:
            self.dictation.cancel()
        self.level = 0.0
        self.preview = ""

    def do_stop(self):
        if not self.recording:
            return
        self.recording = False
        self.level = 0.0
        self.released_at = time.time()
        self.close_stream()
        d = self.dictation
        if d.seconds < MIN_SECONDS:
            d.cancel()
            return
        self.play(self.sound_stop)
        self.busy = True
        threading.Thread(target=self.finish, args=(d,), daemon=True).start()

    def finish(self, d):
        raw, err = "", None
        try:
            raw = d.finish()
        except Exception as e:
            err = e
        try:
            self.deliver(raw, d, err)
        finally:
            self.busy = False
            self.preview = ""

    def clean(self, raw):
        s = self.settings
        english = (s["language"] in ("auto", "en") and raw.isascii()) or eng.is_english_only(s["model"])
        return textproc.process(raw, s, english, self.dictionary, self.learned.replacements(),
                                self.learned.data.get("terms", []))

    def deliver(self, raw, d, err):
        if err:
            self.notify(f"Transcription failed: {err}")
        text, fixes = self.clean(raw)
        if not text:
            return
        if os.environ.get("SPEAKON_NO_INSERT"):
            pass                                   # self-test: never send keys to other windows
        elif self.from_button:
            pyperclip.copy(text)
            self.set_status("Copied - paste it anywhere")
        else:
            self.insert(text + (" " if self.settings["trailing_space"] and not text.endswith("\n") else ""))
        latency = time.time() - self.released_at
        entry = {"time": datetime.now().isoformat(timespec="seconds"), "text": text, "raw": raw, "fixes": fixes,
                 "app": self.target_app, "seconds": round(d.seconds, 1), "model": self.settings["model"],
                 "latency": round(latency, 2)}
        if self.settings["keep_recordings"]:
            try:
                C.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                name = datetime.now().strftime("%Y%m%d-%H%M%S") + ".wav"
                eng.save_wav(C.AUDIO_DIR / name, d.audio())
                entry["audio"] = name
                for old in sorted(C.AUDIO_DIR.glob("*.wav"))[:-C.KEEP_RECORDINGS]:
                    old.unlink()
            except Exception:
                pass
        self.history.insert(0, entry)
        del self.history[HISTORY_LIMIT:]
        self.save_history()

    def set_preview(self, text):
        self.preview = text

    def play(self, path):
        if self.settings["sounds"]:
            try:
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            except Exception:
                pass

    # ----- inserting text where the cursor is
    def insert(self, text):
        deadline = time.time() + 2.0
        while modifiers_down() and time.time() < deadline:   # e.g. Win still held: Ctrl+V would be Win+Ctrl+V
            time.sleep(0.02)
        self.keys.paused = True
        try:
            self._insert(text)
        finally:
            time.sleep(0.05)
            self.keys.paused = False

    def _insert(self, text):
        method = self.settings["paste_method"]
        if method == "type" or (method == "auto" and len(text) <= TYPE_LIMIT and "\n" not in text):
            self.kb.type(text)
            return
        old = None
        if self.settings["restore_clipboard"]:
            try:
                old = pyperclip.paste()
            except Exception:
                old = None
        pyperclip.copy(text)
        time.sleep(0.06)
        if method == "shift_insert":
            with self.kb.pressed(keyboard.Key.shift):
                self.kb.tap(keyboard.Key.insert)
        else:
            with self.kb.pressed(keyboard.Key.ctrl):
                self.kb.tap("v")
        if old:
            def restore():
                time.sleep(0.8)
                pyperclip.copy(old)
            threading.Thread(target=restore, daemon=True).start()


# ---------------------------------------------------------------- what the window can ask for

class Api:
    def __init__(self, app):
        self._app = app

    def state(self):
        a = self._app
        a.levels = a.levels[1:] + [min(1.0, a.level * 12) if a.recording else 0.0]
        return {"recording": a.recording, "busy": a.busy, "preview": a.preview, "status": a.status,
                "levels": a.levels, "hotkey_keys": C.hotkey_label(a.settings).split(" + "),
                "name": a.settings.get("name", ""), "history_version": a.history_version,
                "learning": a.learning, **a.stats()}

    def toggle_record(self):
        self._app.events.put(("toggle",))

    # history
    def history(self, query=""):
        q = (query or "").lower().strip()
        today = date.today()
        out = []
        for i, h in enumerate(self._app.history[:600]):
            if q and q not in h["text"].lower() and q not in h.get("app", "").lower():
                continue
            t = datetime.fromisoformat(h["time"])
            d = t.date()
            day = "Today" if d == today else "Yesterday" if d == today - timedelta(days=1) else t.strftime("%A, %d %B")
            out.append({"i": i, "day": day, "clock": t.strftime("%H:%M"), "text": h["text"], "app": h.get("app", ""),
                        "seconds": h.get("seconds", 0), "wait": h.get("latency"), "fixes": h.get("fixes", [])})
        return out

    def copy(self, i):
        pyperclip.copy(self._app.history[i]["text"])

    def delete_history(self, i):
        del self._app.history[i]
        self._app.save_history()

    def edit_history(self, i, text):
        a = self._app
        h = a.history[i]
        before = h["text"]
        h["text"] = text.strip()
        h["edited"] = True
        a.save_history()
        if a.settings["learn_from_edits"] and before != h["text"]:
            new = a.learned.learn_edit(before, h["text"])
            if new:
                return "Learned: " + ", ".join(f'"{f["heard"]}" → "{f["wanted"]}"' for f in new)
            return "Saved · SpeakOn will learn this fix if it happens again"
        return "Saved"

    # dictionary
    def dictionary(self):
        a = self._app
        a.reload_dictionary()
        out = []
        for n, line in enumerate(a.dictionary.splitlines()):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            hear, write = ((x.strip() for x in s.split("->", 1)) if "->" in s else ("", s))
            out.append({"id": f"d{n}", "write": write, "hear": hear, "kind": "fix" if hear else "word",
                        "learned": False, "warnings": textproc.dictionary_warnings(s)})
        for n, f in enumerate(a.learned.data["fixes"]):
            if f.get("enabled", True):
                out.append({"id": f"l{n}", "write": f["wanted"], "hear": f["heard"], "kind": "fix", "learned": True,
                            "warnings": []})
        for n, t in enumerate(a.learned.data.get("terms", [])):
            out.append({"id": f"t{n}", "write": t, "hear": "", "kind": "word", "learned": True, "warnings": []})
        return out

    def check_entry(self, write, hear):
        write, hear = (write or "").strip(), (hear or "").strip()
        if not write:
            return []
        return textproc.dictionary_warnings(f"{hear} -> {write}" if hear else write)

    def save_entry(self, entry_id, write, hear):
        a = self._app
        write, hear = (write or "").strip(), (hear or "").strip()
        if not write:
            return
        line = f"{hear} -> {write}" if hear else write
        if entry_id and entry_id[0] in "lt":
            self.delete_entry(entry_id)
            entry_id = None
        lines = a.dictionary.splitlines()
        if entry_id and entry_id.startswith("d"):
            lines[int(entry_id[1:])] = line
        else:
            lines.append(line)
        a.set_dictionary("\n".join(lines) + "\n")

    def delete_entry(self, entry_id):
        a = self._app
        n = int(entry_id[1:])
        if entry_id[0] == "d":
            lines = a.dictionary.splitlines()
            del lines[n]
            a.set_dictionary("\n".join(lines) + "\n")
        elif entry_id[0] == "l":
            a.learned.data["fixes"][n]["enabled"] = False
            a.learned.save()
        elif entry_id[0] == "t":
            del a.learned.data["terms"][n]
            a.learned.save()

    def open_dictionary_file(self):
        os.startfile(str(C.DICTIONARY_FILE))

    def import_wispr_dictionary(self):
        if not learn.wispr_available():
            return "Wispr Flow's data was not found on this PC"
        a = self._app
        existing = {line.strip().lower() for line in a.dictionary.splitlines()}
        added = []
        for hear, write in learn.wispr_dictionary():
            line = f"{hear} -> {write}" if hear else write
            if line.lower() not in existing:
                added.append(line)
        if added:
            a.set_dictionary(a.dictionary.rstrip("\n") + "\n# from Wispr Flow\n" + "\n".join(added) + "\n")
        return f"Imported {len(added)} entries from Wispr Flow" if added else "Already up to date"

    # your voice
    def voice(self):
        a = self._app
        summary = learn.wispr_summary() if learn.wispr_available() else None
        if summary:
            w = (f"Found {summary['recordings']} of your recordings and {summary['dictionary']} dictionary entries "
                 "in Wispr Flow.")
        else:
            w = "Wispr Flow's data was not found on this PC."
        info = a.learned.data.get("report")
        if info:
            w += " " + info
        return {"wispr": w, "fixes": a.learned.data["fixes"], "terms": len(a.learned.data.get("terms", [])),
                "clips": a.learned.data.get("clips", 0)}

    def toggle_learned(self, i, on):
        self._app.learned.data["fixes"][i]["enabled"] = bool(on)
        self._app.learned.save()

    def learn_from_wispr(self):
        a = self._app
        if a.learning["running"] or not learn.wispr_available():
            return

        def progress(done, total, msg):
            a.learning.update(progress=done / max(1, total), message=msg)

        def work():
            a.learning.update(running=True, progress=0, message="Starting…")
            try:
                a.engine.ready.wait()
                r = learn.learn_from_wispr(a.engine, lambda audio: eng.transcribe_array(a.engine, audio), progress)
                a.learned.merge_fixes(r["fixes"], "Wispr Flow")
                a.learned.data["terms"] = r["terms"][:80]
                a.learned.data["clips"] = r["clips"]
                a.learned.data["report"] = (f"On recordings it did not learn from, mistakes went from "
                                            f"{r['wer_before'] * 100:.1f}% to {r['wer_after'] * 100:.1f}% of words.")
                a.learned.save()
                a.learning.update(message=f"Done · learned {len(r['fixes'])} fixes and {len(r['terms'])} of your terms. "
                                          + a.learned.data["report"])
            except Exception as e:
                a.learning.update(message=f"Could not finish: {e}")
            finally:
                a.learning.update(running=False, progress=1, finished_at=time.time())
        threading.Thread(target=work, daemon=True).start()

    # settings
    def options(self):
        a = self._app
        s = a.settings
        hot = [(k, f"{v[0]}" + (f"  ·  {v[2]}" if v[2] else "")) for k, v in C.HOTKEY_PRESETS.items()]
        if s.get("custom_hotkey"):
            hot.append(("custom", "Custom: " + C.combo_label(s["custom_hotkey"])))
        return {"settings": s, "hotkeys": hot, "mode": list(C.MODES.items()),
                "model": [(k, v[2]) for k, v in eng.MODELS.items()], "language": list(C.LANGUAGES.items()),
                "mic": [("None", "Windows default microphone")] + [(str(i), n) for i, n in C.list_microphones()],
                "paste_method": list(C.PASTE_METHODS.items()), "data_dir": str(C.DATA_DIR)}

    def set_setting(self, key, value):
        self._app.update_setting(key, value)

    def record_shortcut(self):
        a = self._app
        cap = a.keys.start_capture()
        cap["done"].wait(20)
        keys = cap.get("result")
        a.keys.capture = None
        if not keys:
            return None
        a.settings["custom_hotkey"] = keys
        a.update_setting("hotkey", "custom")
        return C.combo_label(keys)

    def open_data_folder(self):
        os.startfile(str(C.DATA_DIR))

    def transcribe_file(self):
        a = self._app
        paths = a.window.create_file_dialog(
            webview.OPEN_DIALOG, file_types=("Audio and video (*.wav;*.mp3;*.m4a;*.flac;*.ogg;*.opus;*.webm;*.mp4;*.mkv;*.mov;*.aac;*.wma)",
                                             "All files (*.*)"))
        if not paths:
            return None
        path = paths[0]
        a.set_status(f"Transcribing {Path(path).name}…")
        t0 = time.time()
        audio = eng.load_audio_file(path)
        raw = eng.transcribe_array(a.engine, audio, None, a.hotwords())
        text, fixes = a.clean(raw)
        a.history.insert(0, {"time": datetime.now().isoformat(timespec="seconds"), "text": text, "raw": raw,
                             "fixes": fixes, "app": "File: " + Path(path).name, "seconds": round(len(audio) / 16000, 1),
                             "model": a.settings["model"], "file": True})
        a.save_history()
        a.set_status(f"Ready · {a.settings['model']}")
        return f"Done in {time.time() - t0:.0f}s - it's at the top of Home"


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    mutex = kernel32.CreateMutexW(None, False, "SpeakOnSingleInstance")
    if kernel32.GetLastError() == 183:
        h = user32.FindWindowW(None, C.APP_NAME)
        if h:
            user32.ShowWindow(h, 9)
            user32.SetForegroundWindow(h)
        return
    app = SpeakOn(start_hidden="--tray" in sys.argv)
    api = Api(app)
    first_run = not C.SETTINGS_FILE.exists()
    app.save_settings()
    win = webview.create_window(C.APP_NAME, str(resource("ui/index.html")), js_api=api, width=1120, height=780,
                                min_size=(880, 600), hidden=app.start_hidden, background_color="#FFFFFF")
    app.window = win

    def on_closing():
        if app.quitting:
            return True
        win.hide()
        if not getattr(app, "_told", False):
            app._told = True
            app.notify(f"SpeakOn keeps running in the tray. Hold {C.hotkey_label(app.settings)} to dictate.")
        return False
    win.events.closing += on_closing
    if os.environ.get("SPEAKON_SELFTEST"):
        secs = float(os.environ["SPEAKON_SELFTEST"])

        def selftest():
            app.engine.ready.wait()
            time.sleep(1)
            app.events.put(("hot_down", time.time()))
            time.sleep(0.1)
            app.events.put(("hot_up", time.time()))      # short tap: latches on
            time.sleep(secs)
            app.events.put(("hot_down", time.time()))    # tap again: stop
        threading.Thread(target=selftest, daemon=True).start()
    if first_run:
        app.notify(f"Hold {C.hotkey_label(app.settings)} anywhere, speak, and let go.")
    webview.start(private_mode=False, storage_path=str(C.DATA_DIR / "webview"))
    del mutex


if __name__ == "__main__":
    main()
