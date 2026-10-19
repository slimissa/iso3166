from pathlib import Path

def test_release_pattern_sections():
    """Pin the presence of key rules in RELEASE_PATTERN.md."""
    text = Path("docs/RELEASE_PATTERN.md").read_text(encoding="utf-8")
    
    assert "Non-zero exit halts the release" in text, "Missing Rule A"
    assert "proves its own reachability" in text, "Missing Rule B"
    assert "The `[Unreleased]` convention" in text, "Missing [Unreleased] rule"
    assert "Absence claims" in text, "Missing absence-claims corollary"
    assert "grep on structured data" in text, "Missing 6d diagnostic note"
