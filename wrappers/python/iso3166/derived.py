"""
iso3166.derived — derived queries answered from the registry tree.

v1.10.0 — design in docs/QUERIES.md (rationale in
docs/QUERIES-DECISIONS.md). That document is the contract: every
signature, edge case and worked example below is taken from it, and
each docstring names its section.

Twelve methods (the nine queries of docs/QUERIES.md; the EU
predicates and the succession pair count once each as a family),
mixed into CountryRegistry:

    is_eu, is_eea, is_eurozone            approximate
    region_tree, region_countries         exact
    borders_transitively                  exact
    succession_path, successors,
    predecessors                          exact
    calling_code_for                      exact (country-level only)
    currency_at                           approximate
    is_active_on                          tri-state (v1.11.0)

Conventions
-----------
* Codes are case-insensitive alpha-2 strings. An unknown code is not an
  error: bool queries return False, list queries return [], optional
  queries return None.
* An entry is resolved active-first. AI and SK exist twice (one active,
  one withdrawn); every field lookup uses the active entry. The
  succession graph is built from withdrawn entries only, so
  successors("SK") follows Sikkim's replaced_by (IN) even though SK is
  also active Slovakia. Callers who need to tell them apart use
  with_alpha2().
* Returned lists are fresh copies; mutating them cannot affect the
  registry.

docs/QUERIES.md was written from the tree, and its worked examples are
re-run against iso3166.json by test-derived-queries.sh.
"""
from __future__ import annotations

import re
from collections import deque
from datetime import date as _date
from typing import Optional

__all__ = ["DerivedQueries", "KNOWN_EU_MEMBERS", "EEA_NON_EU"]


# The only hardcoded list in the registry. It is the 27 EU member states
# at v1.9.3 and is not a tree fact, so check_docs_match_tree.py cannot
# verify it. This is why is_eu is deprecated in v1.12.0 (is_eu_member_at).
KNOWN_EU_MEMBERS = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
})

# EEA members that are not EU members.
EEA_NON_EU = frozenset({"IS", "LI", "NO"})

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PHONE_JUNK = " -().+"


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


class DerivedQueries:
    """Mixin: derived queries on top of the CountryRegistry indexes.

    Requires the host class to provide ``_active``, ``_withdrawn`` and
    ``_by_alpha2`` (all set by CountryRegistry.__init__).
    """

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    def _entry(self, code):
        """Active entry if there is one, else the withdrawn entry."""
        c = _norm(code)
        if not c:
            return None
        e = self._by_alpha2.get(c)
        if e is not None:
            return e
        for w in self._withdrawn:
            if w.alpha_2 == c:
                return w
        return None

    def _succession_edges(self) -> dict:
        """code -> list of replaced_by codes, from withdrawn entries."""
        cached = getattr(self, "_dq_edges", None)
        if cached is None:
            cached = {}
            for w in self._withdrawn:
                if w.replaced_by:
                    cached[w.alpha_2] = list(w.replaced_by)
            self._dq_edges = cached
        return cached

    def _reverse_edges(self) -> dict:
        cached = getattr(self, "_dq_rev", None)
        if cached is None:
            cached = {}
            for src, dsts in self._succession_edges().items():
                for d in dsts:
                    cached.setdefault(d, []).append(src)
            self._dq_rev = cached
        return cached

    def _closure(self, start: str, edges: dict) -> list:
        seen = set()
        stack = [start]
        while stack:
            cur = stack.pop()
            for nxt in edges.get(cur, ()):
                if nxt not in seen and nxt != start:
                    seen.add(nxt)
                    stack.append(nxt)
        return sorted(seen)

    # ------------------------------------------------------------
    # Query 1 — is_eu / is_eea / is_eurozone (approximate)
    # ------------------------------------------------------------

    def is_eu(self, code: str) -> bool:
        """is_eu(code: str) -> bool   [approximate]

        True if ``code`` is one of the 27 EU member states, taken from
        the hardcoded KNOWN_EU_MEMBERS list. This is an approximate
        answer: membership is not a field of the tree, so the list is
        the only source and it is a snapshot at v1.9.3, with no dates.

        Deprecated: replaced by is_eu_member_at(code, date) in v1.12.0.

        >>> CountryRegistry().is_eu("DE")
        True
        >>> CountryRegistry().is_eu("GB")   # left the EU in 2020
        False
        >>> CountryRegistry().is_eu("CH")   # European, not a member
        False
        >>> CountryRegistry().is_eu("XK")   # no region in the tree
        False

        See docs/QUERIES.md, "Query 1".
        """
        return _norm(code) in KNOWN_EU_MEMBERS

    def is_eea(self, code: str) -> bool:
        """is_eea(code: str) -> bool   [approximate]

        True for the 27 EU members plus IS, LI and NO. Approximate for
        the same reason as is_eu, and deprecated with it.

        >>> CountryRegistry().is_eea("NO")
        True
        >>> CountryRegistry().is_eea("CH")  # EFTA, but not in the EEA
        False

        See docs/QUERIES.md, "Query 1".
        """
        c = _norm(code)
        return c in KNOWN_EU_MEMBERS or c in EEA_NON_EU

    def is_eurozone(self, code: str) -> bool:
        """is_eurozone(code: str) -> bool   [approximate]

        True if ``code`` is an EU member (KNOWN_EU_MEMBERS) whose
        active entry has ``currency_codes == ["EUR"]``. Approximate:
        the EU list is a v1.9.3 snapshot, and French/Finnish overseas
        territories that use the euro (GF, GP, MQ, RE, YT, AX, ...) are
        separate ISO codes that are not EU members here, so they
        return False. Microstates and ME use the euro without being in
        the eurozone and also return False.

        Deprecated together with is_eu.

        >>> CountryRegistry().is_eurozone("DE")
        True
        >>> CountryRegistry().is_eurozone("AD")   # uses EUR, not a member
        False
        >>> CountryRegistry().is_eurozone("GB")   # GBP
        False

        See docs/QUERIES.md, "Query 1".
        """
        c = _norm(code)
        if c not in KNOWN_EU_MEMBERS:
            return False
        e = self._by_alpha2.get(c)
        return bool(e and e.currency_codes is not None
                    and list(e.currency_codes) == ["EUR"])

    # ------------------------------------------------------------
    # Query 2 — region_tree
    # ------------------------------------------------------------

    def region_tree(self, code: str) -> list:
        """region_tree(code: str) -> list[str]

        ``[region, subregion, intermediate_region]`` with null entries
        removed. Unknown code -> []. A withdrawn entry that has only a
        subregion (YU) returns just that subregion, because null levels
        are dropped, not padded.

        >>> reg.region_tree("FR")
        ['Europe', 'Western Europe']
        >>> reg.region_tree("MX")
        ['Americas', 'Latin America and the Caribbean', 'Central America']
        >>> reg.region_tree("AQ")    # no region in the tree
        []
        >>> reg.region_tree("TW")    # no region in the tree either
        []

        See docs/QUERIES.md, "Query 2".
        """
        e = self._entry(code)
        if e is None:
            return []
        return [v for v in (e.region, e.subregion, e.intermediate_region) if v]

    # ------------------------------------------------------------
    # Query 3 — borders_transitively
    # ------------------------------------------------------------

    def borders_transitively(self, code: str, max_hops: int = 2) -> list:
        """borders_transitively(code: str, max_hops: int = 2) -> list[str]

        Sorted alpha-2 codes reachable through ``borders`` in at most
        ``max_hops`` hops, excluding ``code`` itself. max_hops < 1 or an
        unknown code -> [].

        >>> reg.borders_transitively("US", 1)
        ['CA', 'MX']
        >>> reg.borders_transitively("DE", 1)
        ['AT', 'BE', 'CH', 'CZ', 'DK', 'FR', 'LU', 'NL', 'PL']
        >>> reg.borders_transitively("AQ", 2)
        []

        See docs/QUERIES.md, "Query 3".
        """
        start = _norm(code)
        if not start or max_hops < 1 or self._entry(start) is None:
            return []
        seen = {start}
        frontier = [start]
        for _ in range(max_hops):
            nxt = []
            for cur in frontier:
                e = self._by_alpha2.get(cur)
                for b in (e.borders or ()) if e else ():
                    if b not in seen:
                        seen.add(b)
                        nxt.append(b)
            if not nxt:
                break
            frontier = nxt
        seen.discard(start)
        return sorted(seen)

    # ------------------------------------------------------------
    # Queries 4 and 5 — succession
    # ------------------------------------------------------------

    def succession_path(self, from_code: str, to_code: str) -> Optional[list]:
        """succession_path(from_code: str, to_code: str) -> list[str] | None

        Shortest path through ``replaced_by`` edges, both endpoints
        included. Ties are broken by the order of ``replaced_by`` in the
        registry. None if there is no path or either code is unknown;
        a code to itself is ``[code]``.

        >>> reg.succession_path("YU", "RS")
        ['YU', 'CS', 'RS']
        >>> reg.succession_path("YU", "ME")
        ['YU', 'CS', 'ME']
        >>> reg.succession_path("US", "GB") is None
        True
        >>> reg.succession_path("SU", "RU") is None   # SU has no replaced_by
        True

        See docs/QUERIES.md, "Query 4".
        """
        a, b = _norm(from_code), _norm(to_code)
        if self._entry(a) is None or self._entry(b) is None:
            return None
        if a == b:
            return [a]
        edges = self._succession_edges()
        prev = {a: None}
        q = deque([a])
        while q:
            cur = q.popleft()
            for nxt in edges.get(cur, ()):
                if nxt in prev:
                    continue
                prev[nxt] = cur
                if nxt == b:
                    path = [b]
                    while prev[path[-1]] is not None:
                        path.append(prev[path[-1]])
                    return path[::-1]
                q.append(nxt)
        return None

    def successors(self, code: str) -> list:
        """successors(code: str) -> list[str]

        Returns all descendants: the transitive closure of ``replaced_by``
        starting at ``code``. Every code reachable by following
        ``replaced_by`` one or more times, intermediate codes that were
        themselves withdrawn included, excluding ``code``, sorted. The
        CLI ``successors`` subcommand returns the same set (in v1.9.x
        it returned terminal successors only).

        >>> reg.successors("YU")
        ['CS', 'ME', 'RS']
        >>> reg.successors("RS")
        []
        >>> reg.successors("US")
        []

        See docs/QUERIES.md, "Query 5".
        """
        c = _norm(code)
        return self._closure(c, self._succession_edges()) if c else []

    def predecessors(self, code: str) -> list:
        """predecessors(code: str) -> list[str]

        Returns all ancestors: the transitive closure of ``replaced_by`` read
        backwards. Every withdrawn code from which ``code`` can be
        reached by one or more ``replaced_by`` edges, excluding
        ``code``, sorted. The CLI ``predecessors`` subcommand returns
        the same set.

        >>> reg.predecessors("RS")
        ['CS', 'YU']
        >>> reg.predecessors("CS")
        ['YU']
        >>> reg.predecessors("YU")
        []

        See docs/QUERIES.md, "Query 5".
        """
        c = _norm(code)
        return self._closure(c, self._reverse_edges()) if c else []

    # ------------------------------------------------------------
    # Query 6 — calling_code_for
    # ------------------------------------------------------------

    def calling_code_for(self, number: str) -> list:
        """calling_code_for(number: str) -> list[str]

        Sorted alpha-2 codes of every active entry with a
        ``calling_codes`` value that is a prefix of the number's digits.
        ``+``, spaces, dashes, dots and parentheses are ignored; any
        other character, or no digits at all, -> [].

        Country level only. The tree stores "1", not area codes, so
        "+1 867 ..." (Canada) returns all 26 NANP entries, and +44
        returns GB, GG, IM and JE. The caller narrows the list.

        >>> reg.calling_code_for("+44 20 7946 0958")
        ['GB', 'GG', 'IM', 'JE']
        >>> reg.calling_code_for("+999 123")
        []
        >>> reg.calling_code_for("nonsense")
        []

        See docs/QUERIES.md, "Query 6".
        """
        if not isinstance(number, str):
            return []
        digits = "".join(ch for ch in number if ch not in _PHONE_JUNK)
        if not digits or not (digits.isascii() and digits.isdigit()):
            return []
        out = set()
        for e in self._active:
            for cc in e.calling_codes or ():
                if digits.startswith(cc):
                    out.add(e.alpha_2)
        return sorted(out)

    # ------------------------------------------------------------
    # Query 7 — currency_at (approximate)
    # ------------------------------------------------------------

    def currency_at(self, code: str, date: str) -> Optional[list]:
        """currency_at(code: str, date: str) -> list[str] | None   [approximate]

        Approximate for active entries: the tree has no ``introduced``
        field, so an active code returns its current ``currency_codes``
        for every date (DE in 1990 returns ['EUR'], not DEM).

        Withdrawn entries carry no currency_codes in the tree, so
        nothing is known before ``withdrawal_date`` (None). From that
        date on, the answer is the sorted union of the *current*
        currencies of the terminal successors, which is also
        approximate (DD in 1991 returns ['EUR'], not DEM).

        None means "cannot answer": unknown code, malformed date
        (not a real YYYY-MM-DD), no currency data, or no successor.
        An empty list means "no currency" (AQ).

        Deprecated: replaced by an exact answer in v1.11.1, built on
        ``introduced``. In v1.11.0 it remains approximate.

        >>> reg.currency_at("DE", "2000-01-01")  # approximate
        ['EUR']
        >>> reg.currency_at("DD", "1991-01-01")  # approximate
        ['EUR']
        >>> reg.currency_at("DD", "1990-01-01") is None   # unknown
        True

        The tree has no currency for DD (a limitation of the tree, not a
        bug in the query). See docs/QUERIES.md, "Query 7".
        """
        if not _valid_date(date):
            return None
        c = _norm(code)
        act = self._by_alpha2.get(c)
        if act is not None:
            return None if act.currency_codes is None else list(act.currency_codes)
        wd = next((w for w in self._withdrawn if w.alpha_2 == c), None)
        if wd is None or not wd.withdrawal_date or date < wd.withdrawal_date:
            return None
        edges = self._succession_edges()
        out, seen, stack = set(), set(), [c]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            if cur in self._by_alpha2:
                e = self._by_alpha2[cur]
                out.update(e.currency_codes or ())
            elif cur in edges:
                stack.extend(edges[cur])
        return sorted(out) or None

    # ------------------------------------------------------------
    # Query 9 — is_active_on
    # ------------------------------------------------------------

    def is_active_on(self, code: str, date: str) -> Optional[bool]:
        """is_active_on(code: str, date: str) -> bool | None   [tri-state]

        Was ``code`` an assigned ISO 3166-1 code on ``date``?

        * ``False``: malformed date (not a real YYYY-MM-DD), unknown
          code, a date before an entry's ``introduced``, or a date
          after a withdrawn entry's ``withdrawal_date``.
        * ``True``: the code was in force on that date.
        * ``None``: unknown. An active entry whose ``introduced`` is
          null (76 of 252; see docs/QUERIES.md, "Known Nulls") cannot
          be answered, because the source is silent.

        An active entry is resolved first (AI and SK exist twice). A
        withdrawn entry has no sourced start date: it is False after
        ``withdrawal_date``, None before 1974-01-01 (ISO 3166 did not
        exist, so the registry cannot say), and True from 1974-01-01
        up to and including ``withdrawal_date``.

        >>> reg.is_active_on("DE", "1990-01-01")
        True
        >>> reg.is_active_on("DE", "1970-01-01")
        False
        >>> reg.is_active_on("BJ", "2000-01-01") is None  # unknown
        True
        >>> reg.is_active_on("DD", "1800-01-01") is None   # before 1974
        True

        See docs/QUERIES.md, "Query 9".
        """
        if not _valid_date(date):
            return False
        c = _norm(code)
        act = self._by_alpha2.get(c)
        if act is not None:
            if act.introduced is None:
                return None
            return date >= act.introduced
        wd = next((w for w in self._withdrawn if w.alpha_2 == c), None)
        if wd is None or not wd.withdrawal_date:
            return False
        if date > wd.withdrawal_date:
            return False
        if wd.introduced is None:
            # Start unknown: ISO 3166 began in 1974, so nothing earlier is known.
            return None if date < "1974-01-01" else True
        return wd.introduced <= date

    # ------------------------------------------------------------
    # Query 8 — region_countries
    # ------------------------------------------------------------

    def region_countries(self, region: str, subregion: Optional[str] = None) -> list:
        """region_countries(region: str, subregion: str | None = None) -> list[str]

        Sorted alpha-2 codes of active entries in ``region`` (and
        ``subregion`` if given). Case-insensitive. Entries with no
        region (AQ, TW, XK, EU, UK) are in no region.

        >>> reg.region_countries("Europe", "Western Europe")
        ['AT', 'BE', 'CH', 'DE', 'FR', 'LI', 'LU', 'MC', 'NL']
        >>> reg.region_countries("Antarctica")   # AQ has no region
        []

        See docs/QUERIES.md, "Query 8".
        """
        if not region:
            return []
        r = region.lower()
        s = subregion.lower() if subregion else None
        return sorted(
            e.alpha_2 for e in self._active
            if (e.region or "").lower() == r
            and (s is None or (e.subregion or "").lower() == s)
        )
