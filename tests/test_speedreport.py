from datetime import datetime

import speedreport

DICT = ("{t} INFO dictation: %.1fs speech, %d chars, wait %.2fs = engine %.2f (pieces %s, preview reused %s) "
        "+ keys still held %.2f + insert %.2f [%s] lead-in %.2fs")         # as speakon.py logs it
REL = "{t} INFO release: worker %s, waited %.2fs for it, %.1fs left, final step %.2fs, preview heard all %s"


def test_report_sums_up_the_log(tmp_path):
    t = "2026-10-08 10:00:00,000"
    lines = [DICT.format(t=t) % (3.0, 40, 0.30, 0.25, 0, True, 0.0, 0.05, "type", 0.5),
             REL.format(t=t) % ("covering preview", 0.10, 3.2, 0.00, True),
             DICT.format(t=t) % (20.0, 300, 2.10, 1.90, 2, False, 0.1, 0.10, "ctrl_v", 0.5),
             REL.format(t=t) % ("piece", 1.20, 4.0, 0.60, False),
             DICT.format(t=t) % (8.0, 100, 0.90, 0.80, 1, True, 0.0, 0.10, "type", 0.5),   # before 1.2.6: no details
             "2026-10-08 10:00:01,000 INFO something else"]
    (tmp_path / "speakon.log").write_text("\n".join(lines), encoding="utf-8")
    text = speedreport.report(tmp_path, "1.2.6", "parakeet-v2", 3, now=datetime(2026, 10, 9))
    assert "3 dictations. Wait after letting go: median 0.90s" in text
    assert "Engine part (2 dictations with details)" in text
    assert "worker at release {'covering preview': 1, 'piece': 1}" in text
    assert text.splitlines()[-3].startswith("  2.10s: 20.0s speech") and "worker piece, waited 1.20s" in text


def test_report_without_a_log(tmp_path):
    assert "No dictations logged yet" in speedreport.report(tmp_path, "1.2.6", "parakeet-v2", 3)
