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


# ---------------------------------------------------------------------
# Input contract (v1.8.0). Wrapper-local: these do not read the shared
# fixture, so they run unconditionally.
# ---------------------------------------------------------------------

def test_list_fields_are_tuples(reg):
    us = reg.active("US")
    for name in ("currency_codes", "calling_codes", "tlds", "languages", "borders"):
        value = getattr(us, name)
        assert value is None or isinstance(value, tuple), name
    assert isinstance(us.currency_codes, tuple)
    assert hash(us) is not None


def test_replaced_by_is_tuple(reg):
    an = reg.with_alpha2("AN")[0]
    assert isinstance(an.replaced_by, tuple)
    assert an.replaced_by == ("BQ", "CW", "SX")


def test_by_numeric_sentinel_and_whitespace(reg):
    for value in ("", "000", "0", " 20", "020 ", "530"):
        assert reg.by_numeric(value) is None, value
    assert reg.by_numeric(20).alpha_2 == "AD"
    assert reg.by_numeric("20").alpha_2 == "AD"
    assert reg.by_numeric("020").alpha_2 == "AD"


def test_empty_string_lookups(reg):
    assert reg.active("") is None
    assert reg.by_alpha2("") is None
    assert reg.by_alpha3("") is None
    assert reg.by_numeric("") is None


def test_empty_string_queries(reg):
    assert reg.region("") == []
    assert reg.subregion("") == []
    assert reg.search("") == []
    assert reg.countries_with("") == []
    assert reg.with_alpha2("") == []
    assert reg.with_alpha3("") == []
    assert reg.with_numeric("") == []


def test_withdrawn_symmetry(reg):
    assert reg.by_alpha3("ANT") is None
    assert reg.by_numeric("530") is None
    assert [c.alpha_2 for c in reg.with_alpha3("ANT")] == ["AN"]
    assert [c.alpha_2 for c in reg.with_numeric("530")] == ["AN"]
    assert reg.with_alpha3("ant") == reg.with_alpha3("ANT")
    assert reg.with_numeric("000") == []


def test_with_alpha2_active_first(reg):
    for code in ("AI", "SK"):
        matches = reg.with_alpha2(code)
        assert [m.is_active for m in matches] == [True, False], code
