- Your learned words are safe: if a SpeakOn file can't be read (a typo after editing it by hand, or the PC switching off while saving), SpeakOn now keeps a copy of it (`learned.json.broken-<date>`, and the same for history and settings) instead of saving an empty one over it. Before, one typo in `learned.json` plus one correction wiped everything SpeakOn had learned.
- Dictionary fixes no longer stack: with `cloud code -> Claude Code` and `code -> Claude Code`, "cloud code" now becomes "Claude Code", not "Claude Claude Code".
- Removing "uh." or "um." keeps the full stop that ended the sentence ("We should go uh. Then we eat." -> "We should go. Then we eat.").
- The end of a dictation is no longer lost if you let go just as the live preview finishes. If part of a dictation does fail, you now get a message instead of quietly shorter text.
- Left Shift, Left Ctrl or Left Alt on its own now works as a recorded shortcut.
- Learn now keeps the words you taught SpeakOn by correcting them, and also learns which words you normally write in lower case, so a word capitalised after a pause ("we should go, Refactor it") is put back. Run Learn now again to pick this up.
- In History, edit, delete and copy always act on the dictation you clicked, even if a new one arrives at that moment.
- Lighter: less memory after switching speech model, less CPU while the window is open, and the Your voice page no longer leaves copies of Wispr Flow's database in your temp folder.

Download SpeakOn-1.2.3-windows-x64.zip, unzip, run SpeakOn.exe. Windows only.
