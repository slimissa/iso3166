"""
Smoke tests for iso3166.cli.

The wrapper ships a CLI entry point, so it must be importable and run
without the repo's tools/ directory. These tests catch the case where a
module-level import in cli.py cannot be satisfied from the installed
package.
"""
import subprocess
import sys
from pathlib import Path


def _run(*args: str) -> subprocess.CompletedProcess:
    """Run the console script in a clean environment."""
    return subprocess.run(
        [sys.executable, "-m", "iso3166.cli", *args],
        capture_output=True, text=True,
    )


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


def test_csv_matches_fixture_columns():
    """--csv header must match the shared column contract."""
    proc = _run("lookup", "US", "--csv")
    assert proc.returncode == 0, proc.stderr
    header = proc.stdout.splitlines()[0]
    expected = (
        "alpha_2,alpha_3,numeric,name,status,independent,"
        "official_name,region,subregion,intermediate_region,"
        "currency_codes,calling_codes,tlds,languages,borders,"
        "note,last_verified,withdrawal_date,replaced_by"
    )
    assert header == expected, f"\n got: {header}\nwant: {expected}"
