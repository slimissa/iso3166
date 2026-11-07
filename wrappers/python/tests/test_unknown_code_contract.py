"""The unknown-code contract (README section 4b, v1.12.5), Python column."""
import pytest

from iso3166 import CountryRegistry


@pytest.fixture(scope="module")
def reg():
    return CountryRegistry()


def test_unknown_code_is_none_empty_none(reg):
    assert reg.active("XX") is None
    assert reg.currencies("XX") == []
    assert reg.currency_at("XX", "2000-01-01") is None
    assert reg.is_active_on("XX", "2000-01-01") is False
    assert reg.is_eu_member_at("XX", "2010-01-01") is False


def test_unknown_code_and_a_country_without_currency_look_the_same(reg):
    # currencies() cannot tell "no such country" from "no currency": AQ is a
    # real entry with none. Use active(code) is None to tell them apart.
    assert reg.currencies("XX") == reg.currencies("AQ") == []
    assert reg.active("XX") is None and reg.active("AQ") is not None


def test_lookup_is_case_insensitive_but_does_not_strip(reg):
    assert reg.active("us") is reg.active("US") and reg.active("us") is not None
    assert reg.active(" us ") is None


def test_derived_queries_do_strip(reg):
    assert reg.is_eu_member_at(" de ", "2010-01-01") is True
    assert reg.is_eu_member_at("de", "2010-01-01") is True


def test_alpha3_in_an_alpha2_lookup_is_none(reg):
    assert reg.active("USA") is None
    assert reg.by_alpha3("USA").alpha_2 == "US"


def test_empty_and_none_are_none_not_errors(reg):
    assert reg.active("") is None and reg.active(None) is None


@pytest.mark.parametrize("bad", [840, 1.5, b"US", ["US"]])
def test_non_string_code_raises_type_error(reg, bad):
    with pytest.raises(TypeError, match="must be a str"):
        reg.active(bad)


def test_numeric_int_hint(reg):
    with pytest.raises(TypeError, match="by_numeric"):
        reg.active(840)
    assert reg.by_numeric(840).alpha_2 == "US"
