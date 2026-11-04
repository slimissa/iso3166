"""check_introduced.py rejects an `introduced` date later than today.

A date in the future is wrong in the source or a typo. The entry and the
snapshot can agree on it, so the comparison between them cannot see it.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from check_introduced import introduced_mismatches  # noqa: E402

TODAY = "2026-11-03"


def reg(value):
    return {"countries": {"active": [{"alpha_2": "AA", "introduced": value}]}}


def snap(value):
    return {"data": {"AA": value}, "meta": {"null_reasons": {}}}


def test_a_past_date_that_matches_passes():
    assert introduced_mismatches(reg("1974-01-01"), snap("1974-01-01"), TODAY) == []


def test_today_itself_is_not_the_future():
    assert introduced_mismatches(reg(TODAY), snap(TODAY), TODAY) == []


def test_a_future_date_that_both_files_agree_on_fails():
    errors = introduced_mismatches(reg("2030-01-01"), snap("2030-01-01"), TODAY)
    assert any("AA" in e and "2030-01-01" in e and "future" in e for e in errors)


def test_a_future_date_only_in_the_snapshot_fails():
    errors = introduced_mismatches(reg(None), snap("2030-01-01"), TODAY)
    assert any("snapshot AA" in e and "future" in e for e in errors)


def test_the_tool_exits_one_on_the_real_tree_when_today_is_moved_back():
    ok = subprocess.run([sys.executable, str(ROOT / "tools" / "check_introduced.py")],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    bad = subprocess.run([sys.executable, str(ROOT / "tools" / "check_introduced.py"),
                          "--today", "1990-01-01"], capture_output=True, text=True)
    assert bad.returncode == 1
    assert "future" in bad.stderr
