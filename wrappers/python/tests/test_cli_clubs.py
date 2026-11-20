"""
Club-membership subcommands (v1.12.0): is-eu, is-eea, is-eurozone, and the club cells of the flat exports.

Split from test_cli.py in v1.12.8; the tests are unchanged.
"""
from cli_support import run_cli as _run


def test_is_eu_prints_the_boolean_and_exits_0():
    de = _run("is-eu", "DE")
    assert (de.stdout, de.returncode) == ("true\n", 0)
    gb = _run("is-eu", "GB")
    assert (gb.stdout, gb.returncode) == ("false\n", 0)   # GB exists: exit 0


def test_is_eu_unknown_code_exit_1_and_usage_error_exit_2():
    xx = _run("is-eu", "XX")
    assert xx.returncode == 1 and "not found: XX" in xx.stderr
    assert xx.stdout == ""
    bogus = _run("is-eu", "--bogus")
    assert bogus.returncode == 2 and "usage: iso3166 is-eu" in bogus.stderr


def test_is_eea_and_is_eurozone():
    assert _run("is-eea", "NO").stdout == "true\n"
    assert _run("is-eea", "CH").stdout == "false\n"
    assert _run("is-eurozone", "DE").stdout == "true\n"
    assert _run("is-eurozone", "AD").stdout == "false\n"
    assert _run("is-eurozone", "XX").returncode == 1


def test_is_eu_json_shape():
    import json
    out = json.loads(_run("is-eu", "DE", "--json").stdout)
    assert out == {"code": "DE", "is_eu": True, "result": "true"}


def test_is_eu_missing_registry_exit_3():
    assert _run("is-eu", "DE", "--registry", "/nonexistent/iso3166.json").returncode == 3


def test_is_eu_help_says_current_member_only():
    h = " ".join(_run("is-eu", "--help").stdout.split())
    assert "Current member only" in h and "is-eu-member-at" in h


def test_csv_club_cells_for_a_former_member_a_current_member_and_a_withdrawn_entry():
    import csv
    import io

    rows = {}
    for r in csv.DictReader(io.StringIO(_run("list", "--csv").stdout, newline="")):
        rows[(r["alpha_2"], r["status"] == "withdrawn")] = r
    gb = rows[("GB", False)]
    assert gb["eu_membership"] == "1973-01-01:2020-01-31"
    assert gb["eurozone_membership"] == ""
    assert rows[("DE", False)]["eu_membership"] == "1958-01-01:"
    # AI and SK exist twice; the withdrawn one must not inherit the active ranges.
    assert rows[("SK", True)]["eu_membership"] == ""
    assert rows[("SK", False)]["eu_membership"] == "2004-05-01:"
