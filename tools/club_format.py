"""tools/club_format.py

Flat-export serialization of the four club membership arrays
(eu_membership, eea_membership, eurozone_membership, customs_union).

An array is a list of {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD" | null}
ranges (inclusive; docs/decisions/club-memberships.md). In a flat cell it
is one string:

    one range               1973-01-01:2020-01-31
    still a member          2004-05-01:                (empty `to`)
    several ranges          1990-01-01:1999-12-31|2010-01-01:

ranges are joined with "|", the same delimiter the exports use for every
other list. No code in a range contains ":" or "|", so the cell is
unambiguous. An empty array (never a member) and a missing array
(withdrawn entries) both give None; each exporter renders None in its own
way (CSV: empty cell, Parquet and SQL: NULL).

The packaged Python wrapper has its own copy of the serializer
(wrappers/python/iso3166/clubs.py, `_club_cells`) because it cannot import
from tools/. tests/test-exports-clubs.sh and the wrapper tests check that
the two produce the same bytes.
"""
from __future__ import annotations

import re
from typing import Any, Optional

CLUB_COLUMNS = (
    "eu_membership",
    "eea_membership",
    "eurozone_membership",
    "customs_union",
)

_DATE = r"\d{4}-\d{2}-\d{2}"
_RANGE_RE = re.compile(rf"^({_DATE}):({_DATE})?$")


def format_ranges(ranges: Any) -> Optional[str]:
    """Serialize a membership array, or return None for none/empty."""
    if not ranges:
        return None
    cells = []
    for r in ranges:
        if not isinstance(r, dict) or set(r) != {"from", "to"}:
            raise ValueError(f"bad membership range: {r!r}")
        frm, to = r["from"], r["to"]
        if not isinstance(frm, str) or not re.fullmatch(_DATE, frm):
            raise ValueError(f"bad 'from' date: {frm!r}")
        if to is not None and (not isinstance(to, str) or not re.fullmatch(_DATE, to)):
            raise ValueError(f"bad 'to' date: {to!r}")
        cells.append(f"{frm}:{to or ''}")
    return "|".join(cells)


def parse_ranges(cell: Optional[str]) -> list:
    """Inverse of format_ranges. None or "" gives []."""
    if not cell:
        return []
    out = []
    for part in cell.split("|"):
        m = _RANGE_RE.match(part)
        if not m:
            raise ValueError(f"bad serialized range: {part!r}")
        out.append({"from": m.group(1), "to": m.group(2)})
    return out
