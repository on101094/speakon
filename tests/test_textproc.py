import textproc


def clean(text, dictionary=""):
    return textproc.process(text, {"spoken_commands": True}, True, dictionary)[0]


def test_shorter_rule_does_not_rewrite_a_longer_rules_output():
    d = "cloud code -> Claude Code\ncode -> Claude Code"
    assert clean("open cloud code now", d) == "Open Claude Code now"
    assert clean("I opened CloudCode and Cloud-code", d) == "I opened Claude Code and Claude Code"


def test_fixes_report_only_rules_that_matched_the_spoken_text():
    fixes = []
    textproc.apply_replacements("open cloud code", [("cloud code", "Claude Code"), ("code", "Claude Code")], fixes)
    assert fixes == [("cloud code", "Claude Code")]


def test_many_rules_keep_their_placeholders_apart():
    rules = [(f"w{i}", f"W{i}") for i in range(7000)]
    assert textproc.apply_replacements("w0 w4095 w6999", rules) == "W0 W4095 W6999"


def test_filler_before_a_full_stop_keeps_the_sentence_break():
    assert clean("We should go uh. Then we eat.") == "We should go. Then we eat."
    assert clean("That works, um.") == "That works."


def test_filler_cleanup_otherwise_unchanged():
    assert clean("Um, so I asked about uh the invoice.") == "So I asked about the invoice."
    assert clean("I think, uh, we should. Um. So yes") == "I think, we should. So yes"
    assert clean("Really? Uh. Yes.") == "Really? Yes."
    assert clean("uh... then we left") == "Then we left"
    assert clean("line one\num. two") == "Line one\nTwo"


def test_learned_lowercase_words_undo_a_capital_after_a_pause():
    text = "we should go, Refactor the thing"
    assert textproc.process(text, {}, True)[0] == "We should go, Refactor the thing"
    assert textproc.process(text, {}, True, lowercase_words=["refactor"])[0] == "We should go, refactor the thing"
