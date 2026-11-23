from pathlib import Path

def test_release_pattern_sections():
    """Pin the presence of key rules in RELEASE_PATTERN.md."""
    text = Path("docs/RELEASE_PATTERN.md").read_text(encoding="utf-8")
    
    assert "Non-zero exit halts the release" in text, "Missing Rule A"
    assert "proves its own reachability" in text, "Missing Rule B"
    assert "The `[Unreleased]` convention" in text, "Missing [Unreleased] rule"
    assert "Absence claims" in text, "Missing absence-claims corollary"
    assert "grep on structured data" in text, "Missing 6d diagnostic note"


def test_rule_24_present():
    """Pin rule 24 (state docs) in both the pattern and the receipts."""
    pattern = Path("docs/RELEASE_PATTERN.md").read_text(encoding="utf-8")
    notes = Path("docs/README-AUDIT-NOTES.md").read_text(encoding="utf-8")
    assert "Rule 24" in pattern, "Missing Rule 24 in RELEASE_PATTERN.md"
    assert "Rule 24" in notes, "Missing Rule 24 receipt in README-AUDIT-NOTES.md"


def test_rules_25_and_26_present():
    """Pin rules 25 and 26 in both the pattern and the receipts."""
    pattern = Path("docs/RELEASE_PATTERN.md").read_text(encoding="utf-8")
    notes = Path("docs/README-AUDIT-NOTES.md").read_text(encoding="utf-8")
    for rule in ("Rule 25", "Rule 26"):
        assert rule in pattern, f"Missing {rule} in RELEASE_PATTERN.md"
        assert rule in notes, f"Missing {rule} receipt in README-AUDIT-NOTES.md"


def test_rules_26_to_29_pin_one_sentence_each():
    """Pin one sentence of each of Rules 26, 27, 28 and 29.

    The presence tests above only find the words "Rule 26". These pin the
    claim each rule makes, so softening a rule's body fails here even when its
    heading survives. The text is hard-wrapped, so whitespace is normalised.
    """
    text = " ".join(Path("docs/RELEASE_PATTERN.md").read_text(encoding="utf-8").split())
    assert "A derived file that the release does not regenerate drifts silently." in text, \
        "Rule 26 lost its sentence: an unregenerated derived file drifts"
    assert "`grep -q` exits at the first match" in text, \
        "Rule 27 lost its sentence: grep -q exits at the first match (SIGPIPE)"
    assert "A command that takes a run ID from that output gets an empty ID" in text, \
        "Rule 28 lost its sentence: an empty gh run list gives an empty run ID"
    assert "bash ignores `set -e` inside any compound command whose exit status is tested" in text, \
        "Rule 29 lost its sentence: set -e is ignored where the status is tested"
