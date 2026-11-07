"""Date validation shared by derived.py and clubs.py (v1.12.5).

A malformed date is a caller bug, not a negative answer, so the dated
queries raise ``ValueError`` instead of returning False/None.
"""
from __future__ import annotations

import datetime as _dt
import re

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def valid_date(s) -> bool:
    """True for a real calendar date written exactly as YYYY-MM-DD."""
    # fullmatch, not match with "$": "$" also matches before a trailing
    # newline, so "2010-01-01\n" would pass.
    if not isinstance(s, str) or not _DATE_RE.fullmatch(s):
        return False
    try:
        _dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return False
    return True


def require_date(date) -> str:
    """Return ``date`` as a YYYY-MM-DD string or raise ValueError.

    Accepted: a ``str`` that is a real YYYY-MM-DD date; a
    ``datetime.date``; a ``datetime.datetime`` or ``pandas.Timestamp``
    (converted with ``.date()``, so any time of day and timezone are
    discarded, not converted). Everything else raises, including
    ``None``, ints, "2010-1-1", "20100101" and "2010-13-45".
    """
    if isinstance(date, _dt.datetime):
        iso = date.date().isoformat()  # pandas.Timestamp is a datetime
    elif isinstance(date, _dt.date):
        iso = date.isoformat()
    else:
        iso = date
    if not valid_date(iso):
        raise ValueError(f"malformed date: {date!r} (want YYYY-MM-DD)")
    return iso
