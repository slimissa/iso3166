"""
Core CLI behavior: the entry point imports and runs, lookup, --active-only, validate, search and the exit codes (1 not found, 2 usage, 3 registry missing).

Split from test_cli.py in v1.12.8; the tests are unchanged.
"""
import subprocess
import sys

from iso3166 import CountryRegistry
from cli_support import run_cli as _run


def test_module_imports():
    # If this fails, cli.py has a module-level import that only resolves
    # inside the repo, not inside an installed wheel.
    proc = subprocess.run(
        [sys.executable, "-c", "import iso3166.cli"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_info_runs():
    proc = _run("info")
    assert proc.returncode == 0, proc.stderr
    assert "ISO 3166 Country Registry" in proc.stdout


def test_lookup_us():
    proc = _run("lookup", "US")
    assert proc.returncode == 0, proc.stderr
    assert "United States of America" in proc.stdout


def test_lookup_missing_exit_1():
    proc = _run("lookup", "XX")
    assert proc.returncode == 1


def test_registry_missing_exit_3():
    proc = _run("--registry", "/nonexistent.json", "info")
    assert proc.returncode == 3


def test_usage_error_exit_2():
    proc = _run("bogus")
    assert proc.returncode == 2


def test_cli_uses_registry_not_raw_json():
    import iso3166.cli as cli

    for name in ("load_registry", "all_entries", "find_entry", "active_entries"):
        assert not hasattr(cli, name), f"cli.{name} should be gone"
    assert cli.CountryRegistry is CountryRegistry


def test_lookup_withdrawn_included_by_default():
    proc = _run("lookup", "AN")
    assert proc.returncode == 0, proc.stderr
    assert "Netherlands Antilles" in proc.stdout


def test_lookup_active_only_excludes_withdrawn():
    proc = _run("lookup", "AN", "--active-only")
    assert proc.returncode == 1
    assert "not found" in proc.stderr


def test_lookup_active_only_keeps_active():
    proc = _run("lookup", "US", "--active-only")
    assert proc.returncode == 0, proc.stderr
    assert "United States of America" in proc.stdout


def test_lookup_active_only_prefers_active_for_ai():
    proc = _run("lookup", "AI", "--active-only", "--raw", "name")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "Anguilla\n"


def test_validate_withdrawn_exits_0():
    assert _run("validate", "AN").returncode == 0
    assert _run("validate", "AN", "XX").returncode == 1


def test_search_empty_query_matches_nothing():
    assert _run("search", "").returncode == 1
