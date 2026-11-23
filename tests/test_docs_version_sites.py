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


PIN_VERSION = "0.0.0"


def pin_readme_version(tree: Path, version: str = PIN_VERSION) -> None:
    """Rewrite every version site in the fixture README to a fixed value.

    Without this, the fixture copies whatever version the checkout's
    README happens to carry. release.sh step 1 bumps the README to the
    release version before the gate runs pytest, so a test that asserts
    "bumping VERSION without bumping the README fails" would have its
    precondition already broken by step 1 and would pass even with a
    broken checker. Pinning the fixture makes the test independent of
    the checkout's state.
    """
    readme = tree / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = re.sub(r"^(\| \*\*Version\*\* \| )\d+\.\d+\.\d+",
                  rf"\g<1>{version}", text, flags=re.M)
    text = re.sub(r'("version": ")\d+\.\d+\.\d+(")',
                  rf"\g<1>{version}\g<2>", text)
    text = re.sub(r"(b')\d+\.\d+\.\d+(')", rf"\g<1>{version}\g<2>", text)
    text = re.sub(r"(registry-)\d+\.\d+\.\d+(-orange)",
                  rf"\g<1>{version}\g<2>", text)
    readme.write_text(text, encoding="utf-8")


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
    (r"\b[A-Za-z]+(?:-[a-z]+)? verification reports exist", "Forty-three verification reports exist"),
    (r"The \d+ verification reports are collapsed", "The 43 verification reports are collapsed"),
    (r"(through \[`docs/v)\d+\.\d+\.\d+(-verification\.md`\])", r"\g<1>1.12.3\2"),
])
def test_report_count_sites_all_fail(tree, pattern, repl):
    edit(tree, "README.md", pattern, repl)
    code, lines = run_check(tree)
    assert code == 1 and [ln for ln in failing(lines) if "report count" in ln]


def test_a_version_bump_without_the_readme_sites_fails(tree):
    pin_readme_version(tree)  # independent of the checkout's current version
    # Why release.sh bumps the sites with VERSION: otherwise the gate fails.
    (tree / "VERSION").write_text("1.12.5\n", encoding="utf-8")
    code, lines = run_check(tree)
    bad = failing(lines)
    assert code == 1
    for name in NEW_CHECKS[:3]:
        assert any(name in ln for ln in bad), name


def reports_in(tree: Path) -> list[str]:
    """Versions that have docs/vX.Y.Z-verification.md, oldest first."""
    vs = [m.group(1) for p in (tree / "docs").glob("v*-verification.md")
          if (m := re.fullmatch(r"v(\d+\.\d+\.\d+)-verification\.md", p.name))]
    return sorted(vs, key=lambda v: tuple(int(x) for x in v.split(".")))


def describe_reports_in_readme(tree: Path, have: list[str]) -> None:
    """Make every README report-count site say: len(have) reports, through have[-1].

    The README is edited by hand after a release, so a test that copies it
    must not depend on what it says today. Every occurrence is rewritten.
    """
    readme = tree / "README.md"
    text = readme.read_text(encoding="utf-8")
    n = len(have)
    for pattern, repl in (
        (r"\b(?:[A-Z][a-z]+(?:-[a-z]+)?|\d+) (verification reports exist)", rf"{n} \1"),
        (r"(The )\d+( verification reports)", rf"\g<1>{n}\2"),
        (r"(# )\d+( release gate records)", rf"\g<1>{n}\2"),
        (r"(through \[`docs/v)\d+\.\d+\.\d+(-verification\.md`\])",
         rf"\g<1>{have[-1]}\2"),
    ):
        text, k = re.subn(pattern, repl, text)
        assert k >= 1, f"README.md: no site for {pattern!r}"
    readme.write_text(text, encoding="utf-8")


def drop_report(tree: Path, version: str) -> None:
    own = tree / "docs" / f"v{version}-verification.md"
    own.unlink(missing_ok=True)
    own.with_name(own.name + ".sha256").unlink(missing_ok=True)


def next_patch(version: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def current_version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_the_release_flow_passes_gate_then_report(tree):
    """The release being made is VERSION, whatever VERSION is today.

    This test used to hardcode 1.12.5, so it passed until the report for the
    next release existed, and then failed on the very commit that
    release.sh step 7 creates (v1.12.6's verification-report commit).
    """
    new = current_version()
    pin_readme_version(tree, new)
    edit(tree, "CHANGELOG.md", r"^## \[\d+\.\d+\.\d+\]", f"## [{new}]")
    # Step 1: VERSION and the README sites are bumped together; the report for
    # the new version does not exist yet (it is written in step 7), and the
    # README counts the reports that do.
    drop_report(tree, new)
    describe_reports_in_readme(tree, reports_in(tree))
    code, lines = run_check(tree)
    assert code == 0, "gate state:\n" + "\n".join(failing(lines))
    # Step 7: the report for VERSION lands; the README still counts one fewer.
    (tree / "docs" / f"v{new}-verification.md").write_text("# report\n", encoding="utf-8")
    assert reports_in(tree)[-1] == new
    code, lines = run_check(tree)
    assert code == 0, "after the report:\n" + "\n".join(failing(lines))
    # The next release, without bumping the count, must fail the gate.
    (tree / "VERSION").write_text(next_patch(new) + "\n", encoding="utf-8")
    code, lines = run_check(tree)
    assert any("README version row" in ln for ln in failing(lines)), "\n".join(lines)


def test_the_through_clause_accepts_the_report_for_version(tree):
    """Newest report is VERSION's own: README one behind (count, through) is valid."""
    new = current_version()
    pin_readme_version(tree, new)
    (tree / "docs" / f"v{new}-verification.md").write_text("# report\n", encoding="utf-8")
    have = reports_in(tree)
    assert have[-1] == new and len(have) >= 2
    describe_reports_in_readme(tree, have[:-1])
    code, lines = run_check(tree)
    assert code == 0, "\n".join(failing(lines))
    assert any(ln.startswith("OK: README report count") for ln in lines)


def test_the_through_clause_fails_when_the_newest_report_is_not_version(tree):
    """Newest report is NOT VERSION's: README one behind is not allowed."""
    new = current_version()
    later = next_patch(new)
    pin_readme_version(tree, later)
    (tree / "VERSION").write_text(later + "\n", encoding="utf-8")
    edit(tree, "CHANGELOG.md", r"^## \[\d+\.\d+\.\d+\]", f"## [{later}]")
    have = reports_in(tree)
    assert have[-1] != later
    describe_reports_in_readme(tree, have[:-1])
    code, lines = run_check(tree)
    assert code == 1
    assert [ln for ln in failing(lines) if "report count" in ln], "\n".join(lines)
    # ... and the same README is fine when it counts every report.
    describe_reports_in_readme(tree, have)
    code, lines = run_check(tree)
    assert code == 0, "\n".join(failing(lines))


def test_the_checks_need_no_pyarrow(tmp_path):
    """The version-site checks read text and file names, never a Parquet file.

    This file therefore does not call pytest.importorskip("pyarrow"): that
    would skip every test here on a machine without the library even though
    none of them needs it. Instead pyarrow is made unimportable for the
    checker (a shim on PYTHONPATH, inherited by the subprocess) and the
    checks must still pass. If a check ever starts reading Parquet, this
    fails loudly, and importorskip on THAT test is then the right fix.
    """
    import os

    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "pyarrow.py").write_text(
        'raise ImportError("pyarrow is blocked for this test")\n', encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(shim))
    p = subprocess.run([sys.executable, str(CHECK), "--root", str(ROOT)],
                       capture_output=True, text=True, env=env)
    lines = (p.stdout + p.stderr).splitlines()
    assert "pyarrow is blocked" not in p.stdout + p.stderr
    assert p.returncode == 0 and not failing(lines), "\n".join(lines[-10:])
    probe = subprocess.run([sys.executable, "-c", "import pyarrow"],
                           capture_output=True, text=True, env=env)
    assert probe.returncode != 0, "the shim did not block pyarrow"
