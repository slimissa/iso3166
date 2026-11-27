"""Derived queries (v1.10.0): worked examples on real tree data."""
import pytest

from iso3166 import CountryRegistry


@pytest.fixture(scope="module")
def reg():
    return CountryRegistry()


@pytest.mark.parametrize("code,want", [
    ("DE", True), ("de", True), ("GB", False), ("CH", False), ("XK", False), ("ZZ", False),
])
def test_is_eu(reg, code, want):
    assert reg.is_eu(code) is want


def test_is_eea_and_eurozone(reg):
    assert reg.is_eea("NO") and not reg.is_eea("CH")
    assert reg.is_eurozone("DE") and reg.is_eurozone("BG")
    assert not (reg.is_eurozone("AD") or reg.is_eurozone("ME") or reg.is_eurozone("GB"))


def test_region_tree(reg):
    assert reg.region_tree("FR") == ["Europe", "Western Europe"]
    assert reg.region_tree("TW") == []   # the tree has no region for TW
    assert reg.region_tree("AQ") == []


def test_borders(reg):
    assert reg.borders_transitively("US", 1) == ["CA", "MX"]
    assert reg.borders_transitively("AQ", 2) == []
    assert "DE" not in reg.borders_transitively("DE", 3)


def test_succession(reg):
    assert reg.succession_path("YU", "RS") == ["YU", "CS", "RS"]
    assert reg.succession_path("YU", "YU") == ["YU"]
    assert reg.succession_path("US", "GB") is None
    assert reg.succession_path("SU", "RU") is None
    assert reg.successors("YU") == ["CS", "ME", "RS"]
    assert reg.successors("US") == []
    assert reg.predecessors("RS") == ["CS", "YU"]
    assert reg.predecessors("YU") == []


def test_calling_code_for(reg):
    assert reg.calling_code_for("+44 20 7946 0958") == ["GB", "GG", "IM", "JE"]
    assert {"US", "CA"} <= set(reg.calling_code_for("+1 202 555 0100"))
    assert reg.calling_code_for("+999 123") == []
    assert reg.calling_code_for("nonsense") == []


def test_currency_at(reg):
    assert reg.currency_at("DE", "2000-01-01") == ["EUR"]   # current currency
    assert reg.currency_at("DE", "1970-01-01") is None      # before introduced
    assert reg.currency_at("DD", "1990-01-01") == ["EUR"]   # successor's currency
    assert reg.currency_at("DD", "1990-10-04") is None      # after withdrawal
    assert reg.currency_at("BJ", "2000-01-01") is None      # introduced is null
    assert reg.currency_at("DE", "2000-13-01") is None


def test_region_countries(reg):
    assert reg.region_countries("Europe", "Western Europe") == [
        "AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"]
    assert reg.region_countries("Antarctica") == []


def test_results_are_copies(reg):
    reg.region_tree("FR").append("X")
    assert reg.region_tree("FR") == ["Europe", "Western Europe"]


def test_active_on_is_is_active_on_for_every_code(reg):
    # v1.12.5, Query 11. 275 keys = 252 active + 23 withdrawn-only codes.
    r = reg.active_on("1990-01-01")
    assert len(r) == 275 and list(r) == sorted(r)
    for code, v in r.items():
        assert v is reg.is_active_on(code, "1990-01-01"), code


def test_active_on_1990_counts_and_the_none_trap(reg):
    r = reg.active_on("1990-01-01")
    n = lambda v: sum(1 for x in r.values() if x is v)  # noqa: E731
    # CS (withdrawn) is dated 2003-07-23 by Newsletter V-8, so it is False on 1990-01-01.
    # NU is quarantined (Newsletter V-4 renames Niue in 2002), so it is None, not False.
    assert (n(True), n(False), n(None)) == (169, 29, 77)
    act = {e.alpha_2 for e in reg.all_active()}
    a = {c: v for c, v in r.items() if c in act}
    assert len(a) == 252
    assert (sum(v is True for v in a.values()), sum(v is False for v in a.values()),
            sum(v is None for v in a.values())) == (161, 14, 77)
    assert r["DE"] is True and r["DD"] is True and r["BU"] is False
    assert r["BJ"] is None and r["CZ"] is None and r["RU"] is None
    assert len([c for c, v in r.items() if v]) == 169  # truthiness drops the 76


def test_active_on_raises_on_a_malformed_date(reg):
    import pytest
    with pytest.raises(ValueError, match="malformed date"):
        reg.active_on("1990-13-01")


# v1.14.0: a withdrawn entry whose ISO page gives no withdrawal date.
def _undated_registry(tmp_path):
    import json
    from importlib import resources
    data = json.loads(resources.files("iso3166").joinpath("iso3166.json").read_text(encoding="utf-8"))
    for e in data["countries"]["withdrawn"]:
        if e["alpha_2"] == "NT":
            e.update(withdrawal_date=None, alpha_4="NTHH", introduced=None)
        if e["alpha_2"] == "MI":
            e.update(withdrawal_date=None, alpha_4="MIUM", introduced="1975-01-01")
    p = tmp_path / "iso3166.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return CountryRegistry(p)


def test_is_active_on_a_withdrawn_entry_without_withdrawal_date_is_unknown(tmp_path):
    r = _undated_registry(tmp_path)
    assert r.is_active_on("NT", "1980-01-01") is None
    assert r.is_active_on("NT", "2025-01-01") is None
    assert r.is_active_on("MI", "1974-06-01") is False   # before a known introduced
    assert r.is_active_on("MI", "1980-01-01") is None


def test_alpha_4_and_reservation_are_carried_by_withdrawn_entries_only(reg):
    import json
    from importlib import resources
    data = json.loads(resources.files("iso3166").joinpath("iso3166.json").read_text(encoding="utf-8"))
    want = {e["alpha_2"]: (e["alpha_4"], e["reservation"]) for e in data["countries"]["withdrawn"]}
    assert {c.alpha_2: (c.alpha_4, c.reservation) for c in reg.all_withdrawn()} == want
    assert all(c.alpha_4 is None and c.reservation is None for c in reg.all_active())
