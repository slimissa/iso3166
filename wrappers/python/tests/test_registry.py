"""
Unit tests for iso3166.registry.

These are wrapper-specific tests. The cross-language contract is tested
separately in test_consistency.py.
"""
from iso3166 import CountryRegistry, Country, RegistryError

import pytest


@pytest.fixture(scope="module")
def reg() -> CountryRegistry:
    return CountryRegistry()


def test_loads(reg):
    assert len(reg) > 0
    assert reg.version != ""


def test_us(reg):
    us = reg.active("US")
    assert us is not None
    assert us.alpha_2 == "US"
    assert us.alpha_3 == "USA"
    assert us.numeric == "840"
    assert us.name == "United States of America"
    assert us.status == "officially-assigned"
    assert us.independent is True
    assert us.region == "Americas"


def test_case_insensitive(reg):
    assert reg.active("us") == reg.active("US")
    assert reg.by_alpha3("usa") == reg.by_alpha3("USA")


def test_missing(reg):
    assert reg.active("XX") is None
    assert reg.by_alpha3("XXX") is None
    assert reg.by_numeric("999") is None


def test_numeric_zero_padded(reg):
    # by_numeric accepts "20" and "020" identically.
    assert reg.by_numeric("20") is not None
    assert reg.by_numeric("20") == reg.by_numeric("020")


def test_withdrawn_not_in_active(reg):
    # AN is a withdrawn code.
    assert reg.active("AN") is None
    matches = reg.with_alpha2("AN")
    assert len(matches) == 1
    assert matches[0].status == "withdrawn"


def test_reassigned_codes_have_two_entries(reg):
    # AI and SK each appear twice.
    for code in ("AI", "SK"):
        matches = reg.with_alpha2(code)
        statuses = sorted(m.status for m in matches)
        assert statuses == ["officially-assigned", "withdrawn"], \
            f"{code}: got {statuses}"


def test_all_active_sorted(reg):
    codes = [c.alpha_2 for c in reg.all_active()]
    assert codes == sorted(codes)


def test_summary_counts(reg):
    s = reg.summary()
    assert s["total"] == len(reg)
    assert s["active"] == len(reg.all_active())
    assert s["withdrawn"] == len(reg.all_withdrawn())


def test_country_immutable(reg):
    us = reg.active("US")
    with pytest.raises((AttributeError, TypeError)):
        us.alpha_2 = "XX"  # type: ignore[misc]


def test_registry_error_on_missing_file(tmp_path):
    with pytest.raises(RegistryError):
        CountryRegistry(tmp_path / "nope.json")


def test_registry_error_on_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(RegistryError):
        CountryRegistry(p)
