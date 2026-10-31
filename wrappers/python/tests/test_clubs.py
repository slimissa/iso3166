"""v1.12.0 club membership queries (docs/QUERIES.md, Query 10)."""
import pytest

from iso3166 import CountryRegistry
from iso3166.derived import EEA_NON_EU, KNOWN_EU_MEMBERS


@pytest.fixture(scope="module")
def reg():
    return CountryRegistry()


def test_uk_leaves_the_eu_between_2010_and_2023(reg):
    assert reg.is_eu_member_at("GB", "2010-01-01") is True
    assert reg.is_eu_member_at("GB", "2023-01-01") is False


def test_range_ends_are_inclusive(reg):
    assert reg.is_eu_member_at("GB", "2020-01-31") is True
    assert reg.is_eu_member_at("GB", "2020-02-01") is False
    assert reg.is_eu_member_at("GB", "1973-01-01") is True
    assert reg.is_eu_member_at("GB", "1972-12-31") is False


def test_greece_joins_the_eurozone_between_2000_and_2002(reg):
    assert reg.is_eurozone_member_at("GR", "2000-01-01") is False
    assert reg.is_eurozone_member_at("GR", "2000-12-31") is False
    assert reg.is_eurozone_member_at("GR", "2001-01-01") is True
    assert reg.is_eurozone_member_at("GR", "2002-01-01") is True


def test_greece_joins_the_eu_in_1981(reg):
    assert reg.is_eu_member_at("GR", "1980-01-01") is False
    assert reg.is_eu_member_at("GR", "2000-01-01") is True


def test_before_the_first_range_is_false(reg):
    assert reg.is_eu_member_at("DE", "1950-01-01") is False
    assert reg.is_eu_member_at("DE", "1958-01-01") is True


def test_customs_union_and_eea_for_gb(reg):
    assert reg.is_in_customs_union_at("GB", "2010-01-01") is True
    assert reg.is_in_customs_union_at("GB", "2023-01-01") is False
    assert reg.is_eea_member_at("GB", "2020-12-31") is True
    assert reg.is_eea_member_at("GB", "2021-01-01") is False


def test_bad_inputs_are_false_never_none(reg):
    for fn in (reg.is_eu_member_at, reg.is_eea_member_at,
               reg.is_eurozone_member_at, reg.is_in_customs_union_at):
        assert fn("DE", "2000-13-01") is False      # not a real date
        assert fn("DE", "2000-1-1") is False        # not zero padded
        assert fn("DE", "") is False
        assert fn("DE", None) is False
        assert fn("ZZ", "2000-01-01") is False      # unknown code
        assert fn("", "2000-01-01") is False
        assert fn(None, "2000-01-01") is False
        assert fn("CH", "2000-01-01") is False      # never a member


def test_codes_are_case_and_space_insensitive(reg):
    assert reg.is_eu_member_at(" gb ", "2010-01-01") is True


def test_withdrawn_and_reserved_codes_are_in_no_club(reg):
    for code in ("YU", "DD", "SU", "EU", "UK", "XK"):
        assert reg.is_eu_member_at(code, "2000-01-01") is False


def test_aliases_match_the_v1_11_1_lists_for_every_code(reg):
    """is_eu / is_eea / is_eurozone keep v1.11.1's answers."""
    for c in [e.alpha_2 for e in reg.all()] + ["ZZ", ""]:
        e = reg._by_alpha2.get(c)
        eu = c in KNOWN_EU_MEMBERS
        ea = eu or c in EEA_NON_EU
        ez = eu and bool(e and e.currency_codes is not None
                         and list(e.currency_codes) == ["EUR"])
        assert (reg.is_eu(c), reg.is_eea(c), reg.is_eurozone(c)) == (eu, ea, ez), c


def test_aliases_are_current_status(reg):
    assert reg.is_eu("DE") and reg.is_eea("NO") and reg.is_eurozone("BG")
    assert not reg.is_eu("GB") and not reg.is_eea("GB")
    assert not reg.is_eurozone("SE") and not reg.is_eurozone("AD")


def test_current_members_are_exactly_the_open_ranges(reg):
    assert sum(reg.is_eu(e.alpha_2) for e in reg.all_active()) == 27
    assert sum(reg.is_eea(e.alpha_2) for e in reg.all_active()) == 30
    assert sum(reg.is_eurozone(e.alpha_2) for e in reg.all_active()) == 21


def test_eea_provisional_application_counts(reg):
    """v1.12.1: True from provisional application, not only formal entry into force."""
    assert reg.is_eea_member_at("BG", "2010-01-01") is True
    assert reg.is_eea_member_at("BG", "2012-01-01") is True
    assert reg.is_eea_member_at("BG", "2005-01-01") is False
    assert reg.is_eea_member_at("BG", "2007-07-31") is False
    assert reg.is_eea_member_at("BG", "2007-08-01") is True
    assert reg.is_eea_member_at("CY", "2005-01-01") is True
    assert reg.is_eea_member_at("CY", "2004-04-30") is False
    assert reg.is_eea_member_at("CY", "2004-05-01") is True
    # HR: no provisional date in the source, formal only
    assert reg.is_eea_member_at("HR", "2020-01-01") is False
    assert reg.is_eea_member_at("HR", "2025-02-19") is True
