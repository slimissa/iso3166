"""
Output formats: --raw, --csv, --tsv (byte-identical to the root exports) and the blank line for a null or empty value.

Split from test_cli.py in v1.12.8; the tests are unchanged.
"""
from pathlib import Path

from iso3166 import CountryRegistry
from cli_support import run_cli as _run


def test_csv_matches_fixture_columns():
    """--csv header must match the shared column contract."""
    proc = _run("lookup", "US", "--csv")
    assert proc.returncode == 0, proc.stderr
    header = proc.stdout.splitlines()[0]
    expected = (
        "alpha_2,alpha_3,numeric,name,status,independent,"
        "official_name,region,subregion,intermediate_region,"
        "currency_codes,calling_codes,tlds,languages,borders,"
        "note,last_verified,withdrawal_date,replaced_by,introduced,"
        "eu_membership,eea_membership,eurozone_membership,customs_union,"
        "alpha_4,reservation"
    )
    assert header == expected, f"\n got: {header}\nwant: {expected}"


def test_bare_raw_defaults_to_alpha_2():
    bare = _run("successors", "YU", "--raw")
    assert bare.returncode == 0, bare.stderr
    assert bare.stdout.split() == ["CS", "ME", "RS"]
    assert bare.stdout == _run("successors", "YU", "--raw", "alpha_2").stdout
    assert _run("lookup", "DE", "--raw").stdout == "DE\n"
    assert _run("predecessors", "RS", "--raw").stdout.split() == ["CS", "YU"]


def test_bare_raw_validate_uses_code_and_info_needs_a_field():
    assert _run("validate", "DE", "--raw").stdout == _run("validate", "DE", "--raw", "code").stdout
    info = _run("info", "--raw")
    assert info.returncode == 2 and "needs a FIELD for info" in info.stderr


def test_raw_code_is_still_not_a_field_outside_validate():
    # `code` is not a registry field (it is alpha_2); only validate accepts it.
    proc = _run("successors", "YU", "--raw", "code")
    assert proc.returncode == 2 and "not a valid field" in proc.stderr


# --- derived queries (v1.10.0; docs/QUERIES.md) --------------------------


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


def test_csv_and_tsv_are_byte_identical_to_the_root_exports():
    """README: --csv output is byte-compatible with iso3166.csv (v1.12.1:
    24 columns, including the four club membership columns)."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[3]
    for flag, name in (("--csv", "iso3166.csv"), ("--tsv", "iso3166.tsv")):
        want = root / name
        if not want.is_file():
            import pytest
            pytest.skip(f"{name} not in this checkout")
        proc = _run("list", flag)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout == want.read_text(encoding="utf-8"), name


def test_jsonl_prints_one_json_object_per_line():
    import json

    proc = _run("list", "--jsonl", "--limit", "3")
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert len(lines) == 3
    objs = [json.loads(ln) for ln in lines]  # each line is a complete JSON document
    assert [o["alpha_2"] for o in objs] == ["AD", "AE", "AF"]
    assert proc.stdout.endswith("\n") and "\n\n" not in proc.stdout
    # the whole registry, one object per line: active plus withdrawn
    full = _run("list", "--jsonl")
    assert len(full.stdout.splitlines()) == len(CountryRegistry().all())


def test_limit_truncates_and_a_negative_limit_is_ignored():
    first = _run("list", "--raw", "alpha_2", "--limit", "3")
    assert first.stdout.splitlines() == ["AD", "AE", "AF"]
    everything = _run("list", "--raw", "alpha_2")
    assert len(everything.stdout.splitlines()) == len(CountryRegistry().all())
    assert _run("list", "--raw", "alpha_2", "--limit", "-1").stdout == everything.stdout
    # --limit 0 selects nothing: the table says so, JSON Lines prints nothing
    assert _run("list", "--limit", "0").stdout == "(no results)\n"
    assert _run("list", "--jsonl", "--limit", "0").stdout == ""
