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
    assert reg.currency_at("DE", "2000-01-01") == ["EUR"]   # approximate
    assert reg.currency_at("DD", "1990-01-01") is None      # tree has no DDM
    assert reg.currency_at("DD", "1991-01-01") == ["EUR"]   # approximate
    assert reg.currency_at("DE", "2000-13-01") is None


def test_region_countries(reg):
    assert reg.region_countries("Europe", "Western Europe") == [
        "AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"]
    assert reg.region_countries("Antarctica") == []


def test_results_are_copies(reg):
    reg.region_tree("FR").append("X")
    assert reg.region_tree("FR") == ["Europe", "Western Europe"]
