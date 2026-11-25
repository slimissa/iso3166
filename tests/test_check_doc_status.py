"""tools/check_doc_status.py: status lines carry a recheck date, and it has not passed."""
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_doc_status as cds  # noqa: E402


def _repo(tmp_path: Path, line: str, version: str = "1.12.14") -> Path:
    (tmp_path / "VERSION").write_text(version + "\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "page.md").write_text(f"# Page\n\n{line}\nMore text.\n", encoding="utf-8")
    return tmp_path


def _run(root: Path, today: str) -> int:
    return cds.main(["--root", str(root), "--today", today])


def test_the_repository_passes_today():
    assert _run(ROOT, date.today().isoformat()) == 0


def test_every_status_line_in_the_repository_has_a_recheck_date():
    found = cds.collect(ROOT)
    assert {s.path for s in found} >= {
        "docs/SCOPE.md", "docs/sanctions-reconnaissance.md", "docs/introduced-reconnaissance.md"}
    assert all(s.recheck is not None for s in found)


def test_past_date_fails(tmp_path, capsys):
    root = _repo(tmp_path, "Status as of v1.12.14 (recheck 2027-01-25). Text.")
    assert _run(root, "2027-01-26") == 1
    out = capsys.readouterr().out
    assert "PASSED: docs/page.md:3 v1.12.14 recheck 2027-01-25" in out
    assert "FAIL: 1 status line problem(s) on 2027-01-26" in out


def test_due_today_passes(tmp_path):
    root = _repo(tmp_path, "Status as of v1.12.14 (recheck 2027-01-25). Text.")
    assert _run(root, "2027-01-25") == 0


def test_missing_recheck_fails(tmp_path, capsys):
    root = _repo(tmp_path, "Status as of v1.12.10. Text.")
    assert _run(root, "2026-11-25") == 1
    assert "NO RECHECK: docs/page.md:3 v1.12.10" in capsys.readouterr().out


def test_version_later_than_version_file_fails(tmp_path, capsys):
    root = _repo(tmp_path, "Status as of v1.13.0 (recheck 2027-01-25). Text.")
    assert _run(root, "2026-11-25") == 1
    assert "FUTURE: docs/page.md:3 v1.13.0 is later than VERSION 1.12.14" in capsys.readouterr().out


def test_a_status_phrase_inside_a_sentence_is_not_a_status_line(tmp_path, capsys):
    root = _repo(tmp_path, "The rule: `Status as of vX` lines carry a date.")
    assert _run(root, "2026-11-25") == 0
    assert "OK: 0 status line(s)" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["2027-13-01", "2027/01/25", "2027-1-25", "soon"])
def test_malformed_date_is_an_error(tmp_path, capsys, bad):
    root = _repo(tmp_path, f"Status as of v1.12.14 (recheck {bad}). Text.")
    assert _run(root, "2026-11-25") == 2
    assert "ERROR: docs/page.md:3: recheck date" in capsys.readouterr().err


def test_missing_version_file_is_an_error(tmp_path):
    assert _run(tmp_path, "2026-11-25") == 2
