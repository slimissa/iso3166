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

from iso3166 import CountryRegistry


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


def test_successors_yu():
    proc = _run("successors", "YU")
    assert proc.returncode == 0, proc.stderr
    assert "YU" in proc.stdout and "CS" in proc.stdout
    assert "Terminal successors: ME, RS" in proc.stdout
    raw = _run("successors", "YU", "--raw", "alpha_2")
    assert raw.stdout.split() == ["ME", "RS"]


def test_successors_without_successors():
    proc = _run("successors", "SU")
    assert proc.returncode == 0, proc.stderr
    assert "has no successors" in proc.stdout


def test_predecessors_me():
    proc = _run("predecessors", "ME", "--raw", "alpha_2")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["CS", "YU"]


def test_succession_unknown_code_exit_1():
    assert _run("successors", "XX").returncode == 1
    assert _run("predecessors", "XX").returncode == 1


def test_info_raw_accepts_meta_keys():
    reg = CountryRegistry()
    for key in ("version", "updated", "source", "schema_version"):
        proc = _run("info", "--raw", key)
        assert proc.returncode == 0, (key, proc.stderr)
        assert proc.stdout == f"{reg.meta[key]}\n"
    assert _run("info", "--raw", "bogus").returncode == 2


def test_raw_missing_value_and_empty_list_print_one_blank_line():
    reg = CountryRegistry()
    null_name = next(
        c.alpha_2 for c in reg.all_active()
        if c.status != "officially-assigned" and c.official_name is None
    )
    empty_borders = next(
        c.alpha_2 for c in reg.all_active()
        if c.status == "officially-assigned" and c.borders == ()
    )
    assert _run("lookup", null_name, "--raw", "official_name").stdout == "\n"
    assert _run("lookup", empty_borders, "--raw", "borders").stdout == "\n"
    assert _run("lookup", "US", "--raw", "currency_codes").stdout == "USD\n"


def test_search_empty_query_matches_nothing():
    assert _run("search", "").returncode == 1
