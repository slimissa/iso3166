"""The CHANGELOG may carry the NEXT version's heading before VERSION is bumped.

release.sh commits the release section first and bumps VERSION afterwards, so
check_version_consistency.py must accept a first released heading that is the
next patch, the next minor (patch 0) or the next major (0.0). Until v1.13.0 it
accepted only the next patch, and the v1.13.0 CHANGELOG commit failed CI.
Anything else, such as skipping a version, still fails.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_version_consistency", ROOT / "tools" / "check_version_consistency.py")
cvc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cvc)

SITE = {"path": "CHANGELOG.md"}


def _check(tmp_path: Path, heading: str, version: str) -> str:
    (tmp_path / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [Unreleased]\n\n## [{heading}] — 2026-11-25\n\n"
        f"- a change\n\n## [{version}] — 2026-11-24\n\n- an older change\n",
        encoding="utf-8")
    return cvc.ex_first_released_heading(tmp_path, SITE, {"version": version, "notes": []})


@pytest.mark.parametrize("heading", ["1.12.15", "1.13.0", "2.0.0"])
def test_the_next_version_is_accepted(tmp_path, heading):
    assert _check(tmp_path, heading, "1.12.14") == "1.12.14"


@pytest.mark.parametrize("heading", ["1.12.16", "1.13.1", "1.14.0", "2.0.1", "3.0.0", "1.12.13"])
def test_any_other_version_is_rejected(tmp_path, heading):
    with pytest.raises(cvc.Bad):
        _check(tmp_path, heading, "1.12.14")


def test_the_current_version_is_accepted(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [1.12.14] — 2026-11-24\n\n- x\n", encoding="utf-8")
    assert cvc.ex_first_released_heading(
        tmp_path, SITE, {"version": "1.12.14", "notes": []}) == "1.12.14"
