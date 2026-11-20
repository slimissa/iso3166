"""
Derived-query subcommands (v1.10.0): successors, predecessors, region-tree, region-countries, borders-transitively, succession-path, calling-code-for and currency-at.

Split from test_cli.py in v1.12.8; the tests are unchanged.
"""
from cli_support import run_cli as _run


def test_successors_yu():
    proc = _run("successors", "YU")
    assert proc.returncode == 0, proc.stderr
    assert "YU" in proc.stdout and "CS" in proc.stdout
    assert "Successors (all descendants): CS, ME, RS" in proc.stdout
    raw = _run("successors", "YU", "--raw", "alpha_2")
    assert raw.stdout.split() == ["CS", "ME", "RS"]   # all descendants, v1.10.0


def test_successors_without_successors():
    proc = _run("successors", "SU")
    assert proc.returncode == 0, proc.stderr
    assert "has no successors" in proc.stdout


def test_predecessors_me():
    proc = _run("predecessors", "ME", "--raw", "alpha_2")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["CS", "YU"]


def test_predecessors_intermediate_code_has_ancestors():
    # All ancestors (transitive closure), v1.10.0: CS was replaced from YU.
    proc = _run("predecessors", "CS", "--raw", "alpha_2")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["YU"]


def test_successors_json_key_is_successors():
    import json
    proc = _run("successors", "YU", "--json")
    assert json.loads(proc.stdout)["successors"] == ["CS", "ME", "RS"]



# --- bare --raw (v1.10.2) ------------------------------------------------


def test_region_tree_and_region_countries():
    assert _run("region-tree", "FR").stdout == "Europe, Western Europe\n"
    assert _run("region-tree", "AQ").stdout == "\n"
    wc = _run("region-countries", "Europe", "--subregion", "Western Europe")
    assert wc.stdout.split() == ["AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"]
    assert _run("region-countries", "Antarctica").returncode == 1


def test_borders_transitively_and_succession_path():
    assert _run("borders-transitively", "US", "--max-hops", "1").stdout.split() == ["CA", "MX"]
    assert _run("succession-path", "YU", "RS").stdout == "YU -> CS -> RS\n"
    assert _run("succession-path", "SU", "RU").returncode == 1


def test_calling_code_for_and_currency_at():
    assert _run("calling-code-for", "+44 20 7946 0958").stdout.split() == ["GB", "GG", "IM", "JE"]
    assert _run("calling-code-for", "+999 123").returncode == 1
    assert _run("currency-at", "DE", "2000-01-01").stdout == "EUR\n"   # current currency
    dd = _run("currency-at", "DD", "1990-10-04")
    assert dd.returncode == 4 and dd.stdout == ""   # after withdrawal: unknown
    assert _run("currency-at", "BJ", "2000-01-01").returncode == 4   # introduced is null
    assert _run("currency-at", "ZZ", "2000-01-01").returncode == 1   # not found
    assert _run("currency-at", "DE", "2000-13-01").returncode == 2   # malformed date


def test_succession_unknown_code_exit_1():
    assert _run("successors", "XX").returncode == 1
    assert _run("predecessors", "XX").returncode == 1
