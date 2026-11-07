"""The malformed-input contract (v1.12.5): silent failures are errors.

Before v1.12.5 the dated queries (`is_active_on` and the four club `*_at`
queries) answered `false` for a malformed date, and a `datetime.date` or
`pandas.Timestamp` came out as `false` too. A backtest that passed
`datetime.date` objects was told "never a member" on every row. The CLI
exited 2 on the same input, so the library and the CLI disagreed.

The 8 malformed inputs x 5 queries live in the fixture
(`derived_queries.error_cases`, written by tools/gen_consistency_fixture.py)
and are checked on every surface by tools/cross_language_derived.py. This
file runs them per surface: Python, JavaScript, Go, Rust and the CLI. A
surface whose toolchain is not installed is skipped, never passed.

It also pins the Python-only part of the contract: what is converted
(`datetime.date`, `datetime.datetime`, `pandas.Timestamp`) and what raises
(`None`, ints, NaT).
"""
from __future__ import annotations

import datetime
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "wrappers" / "python"))

import cross_language_derived as xl  # noqa: E402
from iso3166 import CountryRegistry  # noqa: E402

ERROR_CASES = xl.load_error_cases()
TOOLS = {"javascript": "node", "go": "go", "rust": "cargo"}
QUERIES = (
    "is_active_on", "is_eu_member_at", "is_eea_member_at",
    "is_eurozone_member_at", "is_in_customs_union_at",
)


def test_fixture_has_8_inputs_for_each_of_5_queries():
    assert len(ERROR_CASES) == 40
    assert {c["query"] for c in ERROR_CASES} == set(QUERIES)
    assert len({c["args"][1] for c in ERROR_CASES}) == 8


@pytest.mark.parametrize("surface", list(xl.ERROR_SURFACES))
def test_malformed_date_fails_loudly(surface):
    tool = TOOLS.get(surface)
    if tool and not shutil.which(tool):
        pytest.skip(f"{tool} is not installed")
    failures = xl.ERROR_SURFACES[surface](ERROR_CASES)
    assert not failures, "\n".join(failures)


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


@pytest.mark.parametrize("q,args", [
    ("is_eu_member_at", ("DE",)), ("is_eea_member_at", ("NO",)),
    ("is_eurozone_member_at", ("GR",)), ("is_in_customs_union_at", ("GB",)),
    ("is_active_on", ("DE",)),
])
def test_python_date_objects_are_converted_not_coerced_to_false(reg, q, args):
    f = getattr(reg, q)
    for iso in ("1990-01-01", "2001-01-01", "2010-01-01", "2020-01-31"):
        d = datetime.date.fromisoformat(iso)
        assert f(*args, d) == f(*args, iso)
        # a datetime keeps only its date: time of day and tz are discarded
        dt = datetime.datetime(d.year, d.month, d.day, 23, 59,
                               tzinfo=datetime.timezone.utc)
        assert f(*args, dt) == f(*args, iso)


def test_python_date_object_gives_the_real_answer_not_false(reg):
    # The v1.12.4 bug: this was False.
    assert reg.is_eu_member_at("DE", datetime.date(2010, 1, 1)) is True
    assert reg.is_eu_member_at("GB", datetime.date(2020, 1, 31)) is True
    assert reg.is_eu_member_at("GB", datetime.date(2020, 2, 1)) is False


def test_python_pandas_timestamp_and_nat(reg):
    pd = pytest.importorskip("pandas")
    assert reg.is_eu_member_at("DE", pd.Timestamp("2010-01-01")) is True
    assert reg.is_eu_member_at("DE", pd.Timestamp("2010-01-01 15:30", tz="Asia/Tokyo")) is True
    with pytest.raises(ValueError, match="malformed date"):
        reg.is_eu_member_at("DE", pd.NaT)


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
