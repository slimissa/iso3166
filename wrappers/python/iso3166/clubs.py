"""
iso3166.clubs — date-scoped club membership queries (v1.12.0).

Four clubs, each stored on every active entry of iso3166.json as a list
of inclusive {from, to} ranges (``to`` is null while the entry is still
a member; an empty list means it never was):

    eu_membership        is_eu_member_at          is_eu
    eea_membership       is_eea_member_at         is_eea
    eurozone_membership  is_eurozone_member_at    is_eurozone
    customs_union        is_in_customs_union_at

Rules for every ``*_at`` query (docs/QUERIES.md, "Query 10"):

* A malformed date (not a real YYYY-MM-DD) -> False.
* An unknown code, a code that is in no range, or a withdrawn code
  -> False.
* ``from <= date <= to`` for any range (``to`` null = no upper bound)
  -> True. Both ends are inclusive: the UK is a member on 2020-01-31
  and not on 2020-02-01.
* A date before the first range or after the last range's ``to``
  -> False.

The ``*_at`` queries return a plain bool, never None: membership is a
fact the data states for every entry (an empty list is a statement, not
a silence), so there is no "unknown" state to report. The CLI keeps exit
code 4 for the tri-state contract but nothing here reaches it.

``is_eu``, ``is_eea`` and ``is_eurozone`` (v1.10.0) remain as
current-status aliases: True when the code has a range whose ``to`` is
null. They read the same arrays, so the hardcoded member lists of
v1.10.0 to v1.11.1 are no longer consulted.
"""
from __future__ import annotations

import re
from datetime import date as _date

__all__ = ["ClubMemberships", "CLUB_FIELDS"]

CLUB_FIELDS = (
    "eu_membership",
    "eea_membership",
    "eurozone_membership",
    "customs_union",
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _norm(code) -> str:
    return code.strip().upper() if isinstance(code, str) else ""


def _valid_date(s) -> bool:
    if not isinstance(s, str) or not _DATE_RE.match(s):
        return False
    try:
        _date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return False
    return True


class ClubMemberships:
    """Mixin: club membership queries.

    Requires the host class to call ``_init_clubs`` from ``__init__`` with
    the raw ``countries.active`` list.
    """

    def _init_clubs(self, active_entries) -> None:
        """Index the four arrays as tuples of (from, to) pairs.

        Immutable, so a caller cannot change an answer by mutating
        anything this class hands out (it hands out only bools).
        """
        clubs: dict = {}
        for e in active_entries:
            clubs[e["alpha_2"]] = {
                f: tuple((r["from"], r["to"]) for r in (e.get(f) or ()))
                for f in CLUB_FIELDS
            }
        self._clubs = clubs

    def _club_cells(self, code) -> tuple:
        """The four flat-export cells for an ACTIVE code (CSV rendering).

        "from:to" ranges joined with "|", an empty `to` meaning still a
        member, "" when never a member. Same bytes as
        tools/club_format.py; the callers must pass only active entries
        (a withdrawn alpha_2 can equal an active one: AI, SK).
        """
        by_field = self._clubs.get(_norm(code), {})
        return tuple(
            "|".join(f"{frm}:{to or ''}" for frm, to in by_field.get(f, ()))
            for f in CLUB_FIELDS
        )

    def _club_at(self, field: str, code, date) -> bool:
        if not _valid_date(date):
            return False
        ranges = self._clubs.get(_norm(code), {}).get(field, ())
        for frm, to in ranges:
            if frm <= date and (to is None or date <= to):
                return True
        return False

    def _club_now(self, field: str, code) -> bool:
        """Current member: some range is open-ended."""
        ranges = self._clubs.get(_norm(code), {}).get(field, ())
        return any(to is None for _frm, to in ranges)

    def is_eu_member_at(self, code: str, date: str) -> bool:
        """is_eu_member_at(code: str, date: str) -> bool   [exact]

        Was ``code`` an EU member state on ``date``? Founders count from
        1958-01-01 (the EEC), so the question is about the Community and
        its successor, not only the Union founded in 1993.

        >>> reg.is_eu_member_at("GB", "2010-01-01")
        True
        >>> reg.is_eu_member_at("GB", "2020-01-31")   # last day
        True
        >>> reg.is_eu_member_at("GB", "2020-02-01")
        False
        >>> reg.is_eu_member_at("GR", "1980-01-01")   # joined 1981
        False
        >>> reg.is_eu_member_at("DE", "1950-01-01")   # before the EEC
        False

        See docs/QUERIES.md, "Query 10".
        """
        return self._club_at("eu_membership", code, date)

    def is_eea_member_at(self, code: str, date: str) -> bool:
        """is_eea_member_at(code: str, date: str) -> bool   [exact]

        Was ``code`` a party to the EEA Agreement on ``date``? Dates are
        the agreement's formal entry into force for that state, so a
        state that applied it provisionally earlier (BG, RO, the 2004
        ten, HR) is False until the formal date. See
        docs/decisions/club-memberships.md, decision 1.

        >>> reg.is_eea_member_at("NO", "1994-01-01")
        True
        >>> reg.is_eea_member_at("GB", "2020-12-31")
        True
        >>> reg.is_eea_member_at("CH", "2020-01-01")  # never a member
        False

        See docs/QUERIES.md, "Query 10".
        """
        return self._club_at("eea_membership", code, date)

    def is_eurozone_member_at(self, code: str, date: str) -> bool:
        """is_eurozone_member_at(code: str, date: str) -> bool   [exact]

        Was ``code`` in the eurozone on ``date``? A state is a member
        from 1 January of its adoption year (1999-01-01 for the first
        eleven, the launch of the euro as book-entry money).

        >>> reg.is_eurozone_member_at("GR", "2000-12-31")
        False
        >>> reg.is_eurozone_member_at("GR", "2001-01-01")
        True
        >>> reg.is_eurozone_member_at("AD", "2020-01-01")  # uses EUR, not a member
        False

        See docs/QUERIES.md, "Query 10".
        """
        return self._club_at("eurozone_membership", code, date)

    def is_in_customs_union_at(self, code: str, date: str) -> bool:
        """is_in_customs_union_at(code: str, date: str) -> bool   [exact]

        Was ``code`` in the EU customs union on ``date``? EU members
        count from the later of accession and 1968-07-01; MC, AD, TR and
        SM are included from their agreements (AD and TR cover industrial
        goods only; the partial scope is in the snapshot's meta, not in
        this boolean). GB is a member until 2020-12-31.

        >>> reg.is_in_customs_union_at("GB", "2010-01-01")
        True
        >>> reg.is_in_customs_union_at("GB", "2023-01-01")
        False
        >>> reg.is_in_customs_union_at("TR", "1995-12-31")
        True

        See docs/QUERIES.md, "Query 10".
        """
        return self._club_at("customs_union", code, date)
