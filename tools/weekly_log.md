# SpeakOn weekly log

Numbers from `tools/weekly_check.py` and the accuracy tools, on the maintainer's own voice.
Word errors are counted against Wispr Flow's transcript of the same recording.

| Date | Version | Real median wait | Accuracy (40 recordings, live pipeline) | Change |
|---|---|---|---|---|
| 2026-09-26 | 1.1.0 | 1.33 s (before 1.1.0) | 5.9% | Instant typing, lock in finished words, 3 s context |
| 2026-09-26 | 1.1.1 | (measure next week) | 42 word errors vs 54 for pause-only pieces (short clips 17 -> 10) | Short dictations transcribed whole at release; hook skips SpeakOn's own keystrokes; mouse hook only when needed |
