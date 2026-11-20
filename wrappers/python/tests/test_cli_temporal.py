"""
Date-scoped subcommands (v1.12.5): is-eu-member-at and friends, and active-on; a malformed date is exit 2, never an answer.

Split from test_cli.py in v1.12.8; the tests are unchanged.
"""
from cli_support import run_cli as _run


def test_member_at_prints_the_boolean_with_exit_0_or_1():
    cases = [
        ("is-eu-member-at", "GB", "2010-01-01", "true\n", 0),
        ("is-eu-member-at", "GB", "2023-01-01", "false\n", 1),
        ("is-eea-member-at", "NO", "2000-01-01", "true\n", 0),
        ("is-eurozone-member-at", "GR", "2000-01-01", "false\n", 1),
        ("is-eurozone-member-at", "GR", "2002-01-01", "true\n", 0),
        ("is-in-customs-union-at", "GB", "2010-01-01", "true\n", 0),
        ("is-in-customs-union-at", "GB", "2023-01-01", "false\n", 1),
        ("is-eu-member-at", "ZZ", "2010-01-01", "false\n", 1),   # unknown code: in no club
    ]
    for cmd, code, date, out, rc in cases:
        r = _run(cmd, code, date)
        assert (r.stdout, r.returncode) == (out, rc), (cmd, code, date)


def test_member_at_malformed_date_exit_2_and_json_shape():
    import json
    bad = _run("is-eu-member-at", "GB", "2010-13-01")
    assert bad.returncode == 2 and "malformed date" in bad.stderr and bad.stdout == ""
    out = json.loads(_run("is-eu-member-at", "GB", "2010-01-01", "--json").stdout)
    assert out == {"code": "GB", "date": "2010-01-01",
                   "is_eu_member_at": True, "result": "true"}


def test_active_on_prints_one_line_per_code_and_json_object():
    # v1.12.5, Query 11.
    import json
    r = _run("active-on", "1990-01-01")
    assert r.returncode == 0
    lines = r.stdout.splitlines()
    assert len(lines) == 275
    assert "DE\ttrue" in lines and "BJ\tunknown" in lines and "BU\tfalse" in lines
    j = _run("active-on", "1990-01-01", "--json")
    d = json.loads(j.stdout)
    assert len(d) == 275 and d["BJ"] is None and d["DE"] is True
    assert _run("active-on", "1990-13-01").returncode == 2
