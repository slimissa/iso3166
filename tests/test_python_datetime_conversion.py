"""Python-only date coercion (v1.12.5): what is converted, what raises.

A `datetime.date`, a `datetime.datetime` and a `pandas.Timestamp` are
converted to their calendar date before the query runs. Before v1.12.5 they
came out as `false`: a backtest that passed `datetime.date` objects was told
"never a member" on every row.

This is the Python-specific part of the contract. The cross-surface part is
test_malformed_date_contract.py. The pandas tests skip visibly when pandas is
not installed.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "wrappers" / "python"))

from iso3166 import CountryRegistry  # noqa: E402


@pytest.fixture(scope="module")
def reg():
    return CountryRegistry()


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
