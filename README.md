# SpeakOn

**[⬇ Download SpeakOn for Windows](https://github.com/on101094/speakon/releases/latest)** — unzip, double-click `SpeakOn.exe`.

**Windows only.** There is no Mac version. On a Mac, you're welcome to have your own AI coding assistant adapt the code. Prefer building on Windows from source? See [prompts/windows.md](prompts/windows.md).

Private, fast voice-to-text for Windows. Hold **Ctrl + Win** (the same key as Wispr Flow), speak, let go: your words appear wherever the cursor is, in any app. Everything runs on this computer.

SpeakOn combines the best parts of four open-source dictation apps, and learns from your own Wispr Flow history:

| Came from | What it contributed |
|---|---|
| **SpeakType** (Mac) | Push-to-talk, history, Whisper models, transcribing audio files |
| **FluidVoice** (Mac) | NVIDIA **Parakeet** engine (much faster than Whisper on a normal CPU), live words while you speak, filler removal, spoken commands, the bottom-of-screen mic overlay, learning from your corrections |
| **Handy** (Windows/Mac/Linux) | Silence trimming, "sounds-like" dictionary matching, start/stop sounds, hold-or-tap modes |
| **murmur** (Mac + Windows) | Dictionary rules (longest first, whole words, "CloudCode" → "Claude Code" but never "Cloudflare"), warnings for risky entries, fixes shown in history, safe text insertion |
| **Wispr Flow** (your own data) | Its hotkey (Ctrl + Win), its look, and — read from its local database — your dictionary, snippets and hundreds of your recordings, used to learn how you speak |

Only ideas were taken from FluidVoice (GPL-3.0); no code was copied.

## Why it's fast

SpeakOn transcribes **while you talk**. At every natural pause, the finished part is transcribed in the background, together with the few seconds before it so sentences stay whole. When you let go, only the last words are left: the text is typically ready in **0.2–0.5 s**. The Home page shows the real wait for every dictation.

## How it learns your voice

- **Your voice → Learn now** reads Wispr Flow's local database (a copy; Wispr's file is never changed), runs SpeakOn over your recordings, compares with what Wispr wrote, and keeps the mishearings that repeat for *your* voice (for example a word it keeps mishearing in your accent). It checks itself on recordings it did not learn from and shows the before/after mistake rate.
- **Fix a word right after dictating**, in any app: SpeakOn watches the text box it just typed into for about a minute (through Windows accessibility, only that box, never your keystrokes or password fields). If you change a word to a similar-looking one ("replicanto" → "Replikanto"), it remembers and writes it right from then on. Undo any learned fix under *Your voice*.
- **Edit a dictation** on Home → *Save & learn*. When the same correction happens twice, SpeakOn applies it automatically from then on.
- **Dictionary → Import from Wispr Flow** brings over your Wispr words and snippets.

## Using it

- Hold **Ctrl + Win**, talk, let go. Or **tap** once to keep listening and tap again to finish. **Esc** cancels.
- Never cuts off your first word: the microphone stays ready and the half second before you press the shortcut is included (held only in memory; can be turned off in Settings).
- A small bar rests at the bottom of the screen and opens into the mic pill while you dictate (can be turned off in Settings).
- Settings: shortcut (many presets, mouse side buttons, or *Record shortcut* for any combination), model, microphone, light/dark mode (sun/moon switch in the sidebar), start with Windows.
- Data (models, history, dictionary, learned fixes, last 30 recordings): `C:\Users\<you>\SpeakOn`.

## Good to know

- Windows blocks normal programs from typing into programs running as administrator. The text is still on Home (Copy).
- If Wispr Flow is running too, it listens for the same Ctrl + Win: quit one of them, or give SpeakOn another key.
- **Updates:** once a day SpeakOn asks GitHub for the latest version number (nothing about you or your dictations is sent). When there is a new one, Home shows **Update now**: it downloads the new version, checks its SHA-256 fingerprint against the one GitHub publishes, and SpeakOn closes and opens again a few seconds later. Your settings, history and learned words are not touched. Turn the check off in Settings.
- Parakeet covers 25 European languages. For Hebrew and other languages, pick a Whisper model in Settings.

## Install

Windows 10/11, no graphics card needed.

```
git clone https://github.com/on101094/speakon.git
cd speakon
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pythonw speakon.py
```

The first start downloads the speech model (~630 MB) once. To build a stand-alone `SpeakOn.exe`: `.venv\Scripts\pip install pyinstaller` then `powershell -File build.ps1` (output in `dist\SpeakOn`).

## For developers

| File | What it does |
|---|---|
| `speakon.py` | App: recording, hotkey events, inserting text, tray, the window's API |
| `store.py` | Settings, history and the dictionary file: loading, saving and changes, behind one lock |
| `engine.py` | Parakeet / Whisper and the transcribe-while-you-talk pipeline with context at pauses |
| `textproc.py` | Clean-up and dictionary (`python textproc.py` runs its checks) |
| `learn.py` | Learning from Wispr Flow recordings and from your edits |
| `corrections.py` | Learns from words you fix right after dictating |
| `hotkeys.py` | Global shortcut watcher (key combinations, mouse buttons, Start-menu mask) |
| `mic.py` | Keeps the microphone ready with a half-second lead-in, reopens it after sleep or unplugging |
| `overlay.py` | The bottom-centre mic pill (per-pixel-alpha layered window) |
| `ui/index.html` | The window |
| `tests/` | `python -m pytest tests` - settings, history, dictionary, learned fixes and the window's API (runs on every push, on Windows and Linux) |
| `tools/eval_wispr.py` | Scores engines on your Wispr Flow recordings |

Self-test without a microphone and without sending keys: `SPEAKON_FAKE_MIC=<16 kHz mono .wav>`, `SPEAKON_NO_INSERT=1`, `SPEAKON_SELFTEST=<seconds>`. `python tools/selftest.py <wav> "<what it says>"` does all of that, checks the new history entry and closes the app; CI runs it on Windows for every push.
