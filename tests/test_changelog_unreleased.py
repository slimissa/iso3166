"""A CHANGELOG with `## [Unreleased]` above the version heading is valid.

v1.12.6 made check_version_consistency.py read the CHANGELOG through
tools/version_axes.json: the version site is the FIRST RELEASED heading
(`## [x.y.z]`), and `[Unreleased]` is skipped. The old rule was "any heading
equals VERSION". These tests pin that an unreleased section with content,
sitting above the version heading, fails neither checker, and that the rule
still has a floor: with no released heading at all, the check fails.

The last test is a mutation test. The guard tests above are behavioral (they
run the real checker on a tree and require exit 0), but a guard only counts if
it can fail. That test rewrites the checker's `[Unreleased]` skip in a COPY of
the repository's own tools/check_version_consistency.py (not a monkeypatch: the
checker's EXTRACTORS table holds its own reference to the function, so
patching the module attribute would change nothing) and requires the same
tree to be rejected. If the checker is refactored so the target line moves,
the test fails loudly instead of passing vacuously.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The line of check_version_consistency.py that skips [Unreleased], and a
# broken version of it that counts [Unreleased] as the first heading.
SKIP_UNRELEASED = 'released = [h for h in headings if h != "Unreleased"]'
COUNT_UNRELEASED = "released = list(headings)"
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", "node_modules",
                                "target", ".git", "*.egg-info")


def _tree(tmp_path: Path) -> Path:
    dst = tmp_path / "repo"
    shutil.copytree(ROOT, dst, ignore=IGNORE)
    return dst


def _version_check(root: Path, tool: Path | None = None):
    return subprocess.run(
        [sys.executable,
         str(tool or ROOT / "tools" / "check_version_consistency.py"),
         "--root", str(root)], capture_output=True, text=True)


def _docs_check(root: Path):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_docs_match_tree.py"),
         "--root", str(root)], capture_output=True, text=True)


def _unreleased_with_content(root: Path) -> None:
    p = root / "CHANGELOG.md"
    s = p.read_text(encoding="utf-8")
    assert "## [Unreleased]\n" in s
    p.write_text(s.replace(
        "## [Unreleased]\n",
        "## [Unreleased]\n\n### Added\n\n- A change that is not released yet.\n",
        1), encoding="utf-8")


def test_unreleased_with_content_above_the_version_heading_passes_the_version_check(tmp_path):
    root = _tree(tmp_path)
    _unreleased_with_content(root)
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.index("## [Unreleased]") < text.index("not released yet") \
        < re.search(r"^## \[\d+\.\d+\.\d+\]", text, re.M).start()
    r = _version_check(root)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "[changelog-heading]" in r.stdout


def test_unreleased_with_content_above_the_version_heading_passes_the_docs_check(tmp_path):
    root = _tree(tmp_path)
    _unreleased_with_content(root)
    r = _docs_check(root)
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_changelog_with_no_released_heading_still_fails(tmp_path):
    root = _tree(tmp_path)
    p = root / "CHANGELOG.md"
    s = p.read_text(encoding="utf-8")
    p.write_text(re.sub(r"^## \[\d+\.\d+\.\d+\]", "## [Draft]", s, flags=re.M),
                 encoding="utf-8")
    r = _version_check(root)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "changelog-heading" in r.stdout


def test_a_checker_that_rejects_unreleased_is_caught(tmp_path):
    """Mutation test: break the [Unreleased] skip; the guard must fail."""
    root = _tree(tmp_path)
    _unreleased_with_content(root)
    tool = root / "tools" / "check_version_consistency.py"

    # Control: the repository's checker, unmutated, accepts this tree.
    ok = _version_check(root, tool)
    assert ok.returncode == 0, ok.stdout + ok.stderr

    # Mutant: [Unreleased] now counts as the first heading.
    src = tool.read_text(encoding="utf-8")
    assert src.count(SKIP_UNRELEASED) == 1, (
        "the [Unreleased] skip moved in check_version_consistency.py: "
        "update SKIP_UNRELEASED in this test")
    tool.write_text(src.replace(SKIP_UNRELEASED, COUNT_UNRELEASED),
                    encoding="utf-8")
    bad = _version_check(root, tool)
    assert bad.returncode == 1, bad.stdout + bad.stderr
    assert "[changelog-heading]" in bad.stdout and "Unreleased" in bad.stdout
