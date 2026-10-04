# SpeakOn weekly log

Numbers from `tools/weekly_check.py` and the accuracy tools, on the maintainer's own voice.
Word errors are counted against Wispr Flow's transcript of the same recording.

| Date | Version | Real median wait | Accuracy (40 recordings, live pipeline) | Change |
|---|---|---|---|---|
| 2026-09-26 | 1.1.0 | 1.33 s (before 1.1.0) | 5.9% | Instant typing, lock in finished words, 3 s context |
| 2026-09-26 | 1.1.1 | (measure next week) | 42 word errors vs 54 for pause-only pieces (short clips 17 -> 10) | Short dictations transcribed whole at release; hook skips SpeakOn's own keystrokes; mouse hook only when needed |
| 2026-09-27 | 1.2.0 | (measure next week) | live 5.87% on 40 clips (unchanged); first word kept 57/60 when mic starts 300 ms early vs 43/60 when 60 ms late | Mic kept ready with 0.5 s lead-in (start 150 ms -> 0.1 ms); silence before first piece only when it opens mid-word; edits that add words no longer learned as corrections |
| 2026-10-03 | 1.2.1 | 1.44 s (104 dictations; engine median 1.19 s, 90% under 3.30 s) | live 5.87% (unchanged), pause-only 7.54% (weekly_check set); clean-up step on 671 Wispr texts: 10.01% -> 9.22% word errors, wrong rewrites of right text 222 -> 123 words | Sound-alike snapping no longer turns "trading session" into TradingView or "evaluations as" into evaluation-only, keeps small words ("on TradingView"), ordinary words never snap targets. Settings window polled 8x/s even when hidden: idle CPU ~77% of a core -> ~6% |
| 2026-10-03 | 1.2.2 | replays at idle 0.24-1.73 s for the same clips that took 3-13 s while the PC was loaded | no engine change | Above-normal CPU priority only while dictating: with every core busy, waits 3.05 -> 1.37 s, 2.50 -> 1.68 s, 1.02 -> 0.47 s; back to normal priority as soon as the text is written |
| 2026-10-04 | 1.2.3 | not measured (no recordings of the maintainer's voice in CI) | CI self-test (synthesized sentence): 90-95% of words; no engine model change | Bug fixes: unreadable learned/history/settings files kept aside instead of overwritten; dictionary rules no longer rewrite each other's output; full stop kept when a filler is removed; a late preview cancel no longer stops the final pass; a failed piece is reported; left-side one-key shortcuts; Learn now keeps correction terms and learns lower-case words; History actions by id; old model freed on switch |
