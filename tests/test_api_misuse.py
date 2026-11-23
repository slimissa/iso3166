"""API misuse (v1.12.5): what the Python library does with a wrong argument.

A malformed DATE raises; a bad CODE is a plain answer. The per-surface
contract for malformed dates is in test_malformed_date_contract.py and the
Python coercion of date objects is in test_python_datetime_conversion.py.
This file keeps the Python-only misuse cases: non-string, non-date inputs,
the error message, bad codes, and the one query that is deliberately
unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "wrappers" / "python"))

from iso3166 import CountryRegistry  # noqa: E402

QUERIES = (
    "is_active_on", "is_eu_member_at", "is_eea_member_at",
    "is_eurozone_member_at", "is_in_customs_union_at",
)


@pytest.fixture(scope="module")
def reg():
    return CountryRegistry()


@pytest.mark.parametrize("q", QUERIES)
@pytest.mark.parametrize("bad", [None, 20100101, 2010, True, b"2010-01-01", ["2010-01-01"]])
def test_python_non_string_non_date_input_raises(reg, q, bad):
    with pytest.raises(ValueError, match="malformed date"):
        getattr(reg, q)("DE", bad)


def test_python_message_names_the_input_and_the_format(reg):
    with pytest.raises(ValueError) as e:
        reg.is_eu_member_at("DE", "2010-13-45")
    assert str(e.value) == "malformed date: '2010-13-45' (want YYYY-MM-DD)"


def test_bad_codes_are_still_plain_answers(reg):
    # Only a malformed DATE raises. An unknown or empty code is not a caller
    # type error: it is False (clubs) or False/None (is_active_on).
    assert reg.is_eu_member_at("XX", "2010-01-01") is False
    assert reg.is_eu_member_at("", "2010-01-01") is False
    assert reg.is_active_on("XX", "2010-01-01") is False


def test_currency_at_is_unchanged_in_v1_12_5(reg):
    # Out of scope for 1.12.5: it still answers None for a malformed date
    # (the CLI exits 2). Pinned so a later change is deliberate.
    assert reg.currency_at("DE", "2010-13-45") is None
