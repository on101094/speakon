# SpeakOn for Windows — set it up with an AI coding agent

Most people should simply **[download SpeakOn](https://github.com/on101094/speakon/releases/latest)**, unzip it and double-click `SpeakOn.exe`.

If you'd rather build it from source (to change it, or because you prefer not to run a downloaded .exe), paste this into Claude Code, Codex or another coding agent on your Windows PC:

```text
Set up SpeakOn on this Windows PC from source: https://github.com/on101094/speakon
1. Clone it and read README.md and every .py file first.
2. Create a Python 3.11+ virtual environment and install requirements.txt.
3. Run the self-test without sending any keys to my apps:
   generate a 16 kHz mono WAV of a few sentences with Windows' speech synthesizer,
   then start speakon.py with SPEAKON_FAKE_MIC=<wav> SPEAKON_NO_INSERT=1 SPEAKON_SELFTEST=20
   and confirm a new entry with the right text appears in %USERPROFILE%\SpeakOn\history.json.
4. Build the .exe with build.ps1 and create Desktop and Start-menu shortcuts to it.
5. Tell me in plain language how to use it (default key: hold Ctrl + Win) and report
   the wait time after releasing the key from the self-test.
Never type or paste into my other apps while testing.
```
