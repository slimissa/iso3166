"""--raw prints one line per entry for a null or empty-list value.

The packaged CLI (wrappers/python/iso3166/cli.py) always did; the repo CLI
(tools/iso3166_cli.py) printed nothing for an empty list, so
`list --region Oceania --raw tlds` printed 29 lines from one and 28 from
the other. Both CLIs are exercised here.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = json.loads((ROOT / "iso3166.json").read_text(encoding="utf-8"))
ACTIVE = REGISTRY["countries"]["active"]


def repo_cli(*args):
    return subprocess.run([sys.executable, str(ROOT / "tools" / "iso3166_cli.py"), *args],
                          capture_output=True, text=True, cwd=ROOT)


def packaged_cli(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "wrappers" / "python"))
    return subprocess.run([sys.executable, "-m", "iso3166.cli", *args],
                          capture_output=True, text=True, cwd=ROOT, env=env)


CLIS = [pytest.param(repo_cli, id="repo"), pytest.param(packaged_cli, id="packaged")]


@pytest.mark.parametrize("cli", CLIS)
def test_raw_null_and_empty_list_print_one_line(cli):
    island = next(e for e in ACTIVE if e["status"] == "officially-assigned"
                  and e.get("borders") == [])
    r = cli("lookup", island["alpha_2"], "--raw", "borders")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "\n"

    nameless = next(e for e in ACTIVE if e.get("official_name") is None)
    r = cli("lookup", nameless["alpha_2"], "--raw", "official_name")
    assert r.returncode == 0, r.stderr
    assert r.stdout == "\n"


@pytest.mark.parametrize("cli", CLIS)
def test_raw_list_has_one_line_per_entry_for_a_scalar_free_listing(cli):
    r = cli("list", "--region", "Oceania", "--raw", "tlds")
    assert r.returncode == 0, r.stderr
    expected = sum(max(len(e.get("tlds") or []), 1)
                   for e in ACTIVE if e.get("region") == "Oceania")
    assert len(r.stdout.splitlines()) == expected


def test_both_clis_print_the_same_bytes():
    for args in (("list", "--region", "Oceania", "--raw", "tlds"),
                 ("list", "--region", "Oceania", "--raw", "borders")):
        assert repo_cli(*args).stdout == packaged_cli(*args).stdout
