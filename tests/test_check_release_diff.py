"""check_release_diff.py: regeneration may change the version and nothing else.

Each test builds a throwaway git repository holding one SQL-style artifact,
commits it as the pre-release state, edits it, and runs the tool with --root.
"""
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_release_diff.py"

SQL_HEAD = (
    "-- iso3166.sql\n"
    "-- Registry version: 1.12.2\n"
    "-- Registry updated: 2026-11-03\n"
    "INSERT INTO countries VALUES ('DE', 'Germany');\n"
)


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   cwd=repo, check=True, capture_output=True)


def make_repo(tmp_path, version="1.12.2"):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text(version + "\n")
    (repo / "iso3166.sql").write_text(SQL_HEAD)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "pre-release")
    return repo


def run(repo):
    return subprocess.run([sys.executable, str(TOOL), "--root", str(repo)],
                          capture_output=True, text=True)


def test_a_bump_that_changes_only_the_version_and_date_passes(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "VERSION").write_text("1.12.3\n")
    (repo / "iso3166.sql").write_text(
        SQL_HEAD.replace("1.12.2", "1.12.3").replace("2026-11-03", "2026-11-04"))
    r = run(repo)
    assert r.returncode == 0, r.stderr


def test_a_changed_data_line_fails_even_on_a_bump(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "VERSION").write_text("1.12.3\n")
    (repo / "iso3166.sql").write_text(
        SQL_HEAD.replace("1.12.2", "1.12.3").replace("Germany", "Germanyy"))
    r = run(repo)
    assert r.returncode == 1
    assert "Germanyy" in r.stderr


def test_a_removed_sql_comment_is_checked_not_skipped(tmp_path):
    # A removed `-- note` line reads `--- note` in the diff; it must not be
    # mistaken for a file header and ignored.
    repo = make_repo(tmp_path)
    (repo / "VERSION").write_text("1.12.3\n")
    (repo / "iso3166.sql").write_text(
        SQL_HEAD.replace("1.12.2", "1.12.3").replace("-- iso3166.sql\n", ""))
    r = run(repo)
    assert r.returncode == 1
    assert "iso3166.sql" in r.stderr


def test_without_a_bump_no_change_at_all_is_allowed(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "iso3166.sql").write_text(SQL_HEAD.replace("2026-11-03", "2026-11-04"))
    r = run(repo)
    assert r.returncode == 1


def test_an_unchanged_tree_passes(tmp_path):
    repo = make_repo(tmp_path)
    r = run(repo)
    assert r.returncode == 0
    assert "identical" in r.stdout
