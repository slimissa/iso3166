"""The README version sites are checked (v1.12.5).

v1.12.2, v1.12.3 and v1.12.4 each shipped with README sites that still said
an older version or an older report count, because nothing checked them:
the `Version` row, the JSON sample, the Parquet example and the report count.
`tools/check_docs_match_tree.py` now does. This file asserts that

  1. the four new checks pass on the current tree, and
  2. each one FAILS when its site is broken (on a copy in a temp dir, so the
     real tree is never touched), and
  3. the release flow still passes: VERSION bumped with the README sites, and
     then the report for VERSION written after the gate.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "tools" / "check_docs_match_tree.py"

NEW_CHECKS = (
    "README version row matches VERSION",
    "README JSON sample version matches VERSION",
    "README Parquet example version matches VERSION",
    "README report count matches docs/v*-verification.md",
)

NEEDED = ["README.md", "CONTRIBUTING.md", "VERSION", "CHANGELOG.md", "scripts", ".github",
          "tools", "docs", "iso3166.json"]


def run_check(root: Path):
    p = subprocess.run([sys.executable, str(CHECK), "--root", str(root)],
                       capture_output=True, text=True)
    lines = (p.stdout + p.stderr).splitlines()
    return p.returncode, lines


def failing(lines):
    return [ln for ln in lines if ln.startswith("FAIL: ")]


@pytest.fixture()
def tree(tmp_path):
    """A copy of just what the check reads."""
    for rel in NEEDED:
        src = ROOT / rel
        dst = tmp_path / rel
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("node_modules", "target"))
        else:
            shutil.copy2(src, dst)
    for p in ROOT.glob("*.parquet"):
        shutil.copy2(p, tmp_path / p.name)
    return tmp_path


def edit(root: Path, rel: str, pattern: str, repl: str):
    p = root / rel
    s = p.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, s, count=1, flags=re.M)
    assert n == 1, f"{rel}: no site for {pattern!r}"
    p.write_text(new, encoding="utf-8")


def test_the_four_new_checks_exist_and_pass_on_this_tree():
    code, lines = run_check(ROOT)
    for name in NEW_CHECKS:
        assert f"OK: {name}" in lines, name
    assert code == 0, "\n".join(failing(lines))


@pytest.mark.parametrize("name,rel,pattern,repl", [
    (NEW_CHECKS[0], "README.md", r"^(\| \*\*Version\*\* \| )\d+\.\d+\.\d+", r"\g<1>1.0.0"),
    (NEW_CHECKS[1], "README.md", r'("version": ")\d+\.\d+\.\d+', r"\g<1>1.0.0"),
    (NEW_CHECKS[2], "README.md", r"(b')\d+\.\d+\.\d+(')", r"\g<1>1.0.0\2"),
    (NEW_CHECKS[3], "README.md", r"# \d+ (release gate records)", r"# 7 \1"),
])
def test_each_new_check_fails_when_its_site_is_wrong(tree, name, rel, pattern, repl):
    assert run_check(tree)[0] == 0
    edit(tree, rel, pattern, repl)
    code, lines = run_check(tree)
    assert code == 1
    assert [ln for ln in failing(lines) if name in ln], "\n".join(lines)
    assert len(failing(lines)) == 1, "only the broken site may fail:\n" + "\n".join(failing(lines))


@pytest.mark.parametrize("pattern,repl", [
    (r"\b[A-Z][a-z]+-[a-z]+ verification reports exist", "Forty-three verification reports exist"),
    (r"The \d+ verification reports are collapsed", "The 43 verification reports are collapsed"),
    (r"(through \[`docs/v)\d+\.\d+\.\d+(-verification\.md`\])", r"\g<1>1.12.3\2"),
])
def test_report_count_sites_all_fail(tree, pattern, repl):
    edit(tree, "README.md", pattern, repl)
    code, lines = run_check(tree)
    assert code == 1 and [ln for ln in failing(lines) if "report count" in ln]


def test_a_version_bump_without_the_readme_sites_fails(tree):
    # Why release.sh bumps the sites with VERSION: otherwise the gate fails.
    (tree / "VERSION").write_text("1.12.5\n", encoding="utf-8")
    code, lines = run_check(tree)
    bad = failing(lines)
    assert code == 1
    for name in NEW_CHECKS[:3]:
        assert any(name in ln for ln in bad), name


def test_the_release_flow_passes_gate_then_report(tree):
    # Step 1: VERSION and the README sites are bumped together; the report for
    # the new version does not exist yet (it is written in step 7).
    new = "1.12.5"
    (tree / "VERSION").write_text(new + "\n", encoding="utf-8")
    edit(tree, "README.md", r"^(\| \*\*Version\*\* \| )\d+\.\d+\.\d+", rf"\g<1>{new}")
    edit(tree, "README.md", r'("version": ")\d+\.\d+\.\d+', rf"\g<1>{new}")
    edit(tree, "README.md", r"(b')\d+\.\d+\.\d+(')", rf"\g<1>{new}\2")
    edit(tree, "README.md", r"(registry-)\d+\.\d+\.\d+(-orange)", rf"\g<1>{new}\2")
    edit(tree, "CHANGELOG.md", r"^## \[\d+\.\d+\.\d+\]", f"## [{new}]")
    code, lines = run_check(tree)
    assert code == 0, "gate state:\n" + "\n".join(failing(lines))
    # Step 7: the report for VERSION lands; the README still counts one fewer.
    (tree / "docs" / f"v{new}-verification.md").write_text("# report\n", encoding="utf-8")
    code, lines = run_check(tree)
    assert code == 0, "after the report:\n" + "\n".join(failing(lines))
    # The next release, without bumping the count, must fail the gate.
    (tree / "VERSION").write_text("1.12.6\n", encoding="utf-8")
    code, lines = run_check(tree)
    assert any("report count" in ln for ln in failing(lines))
