#!/usr/bin/env python3
"""
tools/gen_consistency_fixture.py

Regenerate tests/cross_language_consistency.json from iso3166.json.

Run this whenever iso3166.json changes. The fixture is committed and
read by all four wrapper test suites; it must not be edited by hand
except to add new test cases.

Usage:
    python3 tools/gen_consistency_fixture.py
    python3 tools/gen_consistency_fixture.py --check

--check exits 1 if the committed fixture is stale.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if not (PROJECT_ROOT / "iso3166.json").is_file():
    print(
        f"error: {PROJECT_ROOT / 'iso3166.json'} not found; "
        "this tool must run from a repository checkout.",
        file=sys.stderr,
    )
    sys.exit(2)


FIXTURE = PROJECT_ROOT / "tests/cross_language_consistency.json"
REGISTRY = PROJECT_ROOT / "iso3166.json"
INDEPENDENT_SNAPSHOT = Path(__file__).resolve().parent / "independent_snapshot.json"

# independent case (v1.7.3). Codes below are pinned by hand; every one
# must exist in countries.active (build() asserts it).
INDEPENDENT_TRUE = ["AE", "AT", "BE", "BR", "CA", "CH", "DE", "FR", "GB", "US"]
INDEPENDENT_FALSE = ["AQ", "AW", "BM", "BQ", "EU", "GL", "HK", "MO", "PR", "TW"]
# SENTINEL bounds, broad on purpose so any plausible extraction passes.
# After running tools/enrich_independent.py --write, set these to the
# extracted count of independent=true active entries -10 / +10 and
# regenerate, in the same commit as the data.
INDEPENDENT_COUNT_TRUE_MIN = 185
INDEPENDENT_COUNT_TRUE_MAX = 205

# Input-contract cases (v1.8.0, docs/decisions/input-contract.md).
# Each wrapper's test reads the per-section `enforced` flag and skips
# when it is false. It was False while the wrappers landed one by one;
# it is True now that all four implement the contract (v1.8.0).
ENFORCE_INPUT_CONTRACT = True

SUCCESSOR_INPUTS = ["YU", "CS", "AN", "SK", "RS", "US", "SU"]
PREDECESSOR_INPUTS = ["ME", "RS", "CS", "YU", "IN", "US"]
AMBIGUOUS_ALPHA2 = ["AI", "SK"]
NUMERIC_ABSENT_INPUTS = ["", "000", "0", " 20", "020 "]


def _summarize(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "alpha_2": entry["alpha_2"],
        "alpha_3": entry["alpha_3"],
        "numeric": entry["numeric"],
        "name": entry["name"],
        "status": entry["status"],
        "independent": entry["independent"],
        "region": entry.get("region"),
    }


def build(reg: dict[str, Any]) -> dict[str, Any]:
    countries = reg["countries"]
    active = countries["active"]
    withdrawn = countries["withdrawn"]
    all_entries = active + withdrawn

    by_a2 = {e["alpha_2"]: e for e in active}
    by_a3 = {e["alpha_3"]: e for e in active}
    by_num = {e["numeric"]: e for e in active}

    lookup_samples = ["US", "GB", "TW", "XK", "UK"]
    lookup = []
    for code in lookup_samples:
        e = by_a2.get(code)
        if e is None:
            continue
        row = {"input": code}
        row.update(_summarize(e))
        lookup.append(row)
    # Add one lowercase row.
    us = by_a2.get("US")
    if us:
        row = {"input": "us"}
        row.update(_summarize(us))
        lookup.append(row)

    lookup_a3 = []
    for code in ("USA", "GBR", "TWN"):
        e = by_a3.get(code)
        if e:
            lookup_a3.append({"input": code, "alpha_2": e["alpha_2"]})
    if us:
        lookup_a3.append({"input": "usa", "alpha_2": "US"})

    lookup_num = []
    for num in ("840", "826", "158"):
        e = by_num.get(num)
        if e:
            lookup_num.append({"input": num, "alpha_2": e["alpha_2"]})

    by_status = Counter(e["status"] for e in all_entries)
    counts = {
        "total": len(all_entries),
        "active": len(active),
        "withdrawn": len(withdrawn),
        "by_status": {
            "officially-assigned": by_status.get("officially-assigned", 0),
            "user-assigned": by_status.get("user-assigned", 0),
            "exceptionally-reserved": by_status.get("exceptionally-reserved", 0),
            "withdrawn": by_status.get("withdrawn", 0),
        },
    }

    overlap: dict[str, list[str]] = {}
    active_codes = {e["alpha_2"] for e in active}
    for e in withdrawn:
        if e["alpha_2"] in active_codes:
            overlap.setdefault(e["alpha_2"], []).append("officially-assigned")
            overlap[e["alpha_2"]].append("withdrawn")

    region_samples = [
        ("Europe",   ["GB", "FR", "DE", "IT"]),
        ("Asia",     ["JP", "CN", "IN"]),
        ("Africa",   ["ZA", "EG", "NG"]),
        ("Americas", ["US", "CA", "BR", "MX"]),
        ("Oceania",  ["AU", "NZ"]),
    ]
    region_query = []
    for region, must in region_samples:
        in_region = [e["alpha_2"] for e in active if (e.get("region") or "") == region]
        region_query.append({
            "region": region,
            "min_count": max(1, len(in_region) - 5),
            "must_contain": [c for c in must if c in in_region],
        })

    # Withdrawn lookup cases: a handful of representative codes.
    withdrawn_samples = ["SU", "YU", "CS", "AN", "CT"]
    lookup_withdrawn = []
    by_a2_withdrawn = {e["alpha_2"]: e for e in withdrawn}
    for code in withdrawn_samples:
        e = by_a2_withdrawn.get(code)
        if e is None:
            continue
        lookup_withdrawn.append({
            "input": code,
            "alpha_2": e["alpha_2"],
            "name": e["name"],
            "status": "withdrawn",
            "withdrawal_date": e.get("withdrawal_date"),
        })

    # Field-completeness cases for the four enriched list fields.
    # Includes the GB .uk exception and a dual-currency case.
    field_samples = ["US", "GB", "JP", "DE", "EC", "PA", "CH", "FR", "RU", "LS"]
    by_a2_active = {e["alpha_2"]: e for e in active}
    lookup_fields = []
    for code in field_samples:
        e = by_a2_active.get(code)
        if e is None:
            continue
        lookup_fields.append({
            "input": code,
            "official_name": e.get("official_name"),
            "currency_codes": e.get("currency_codes") or [],
            "calling_codes": e.get("calling_codes") or [],
            "tlds": e.get("tlds") or [],
            "languages": e.get("languages") or [],
            "borders": e.get("borders") or [],
            "intermediate_region": e.get("intermediate_region"),
        })

    # Subregion cases for representative withdrawn entries.
    withdrawn_subregion_samples = ["AN", "BU", "CS", "DD", "ZR"]
    lookup_withdrawn_fields = []
    by_a2_withdrawn = {e["alpha_2"]: e for e in withdrawn}
    for code in withdrawn_subregion_samples:
        e = by_a2_withdrawn.get(code)
        if e is None:
            continue
        lookup_withdrawn_fields.append({
            "input": code,
            "subregion": e.get("subregion"),
        })

    return {
        "lookup_withdrawn_fields": lookup_withdrawn_fields,
        "lookup_fields": lookup_fields,
        "lookup_withdrawn": lookup_withdrawn,
        "_comment": (
            "Cross-language consistency fixture. Every wrapper's test suite "
            "reads this file and asserts that its public API produces these "
            "results. Adding a language does not require editing this file; "
            "adding a test case does. Regenerate with "
            "tools/gen_consistency_fixture.py."
        ),
        "version": "1.0.0",
        "lookup_alpha2": lookup,
        "lookup_alpha2_missing": ["XX", "ZZ", "", "USA"],
        "lookup_alpha3": lookup_a3,
        "lookup_numeric": lookup_num,
        "counts": counts,
        "overlap_codes": overlap,
        "region_query": region_query,
        "currencies": {
            code: (by_a2_active[code].get("currency_codes") or [])
            for code in ("US", "GB", "JP")
            if code in by_a2_active
        },
        "countries_with": {
            curr: sorted(
                e["alpha_2"] for e in active
                if curr in (e.get("currency_codes") or [])
            )
            for curr in ("USD", "EUR", "GBP")
        },
        "search": [
            {"query": "united", "min_count": 4, "must_contain": ["AE", "GB", "UM", "US"]},
            {"query": "korea",  "min_count": 2, "must_contain": ["KP", "KR"]},
            {"query": "guinea", "min_count": 3, "must_contain": ["GN", "GW", "PG"]},
        ],
        "optional_absent": collect_optional_absent(reg),
        "independent": independent_case(reg),
        "empty_inputs": empty_inputs_case(),
        "lookup_numeric_absent": numeric_absent_case(),
        "lookup_alpha2_ambiguous": alpha2_ambiguous_case(reg),
        "successors": successors_case(reg),
        "predecessors": predecessors_case(reg),
        "derived_queries": derived_queries_case(reg),
    }

# Literal expected values for the v1.10.0 derived queries. They are typed
# here, not computed by any wrapper, so the wrappers are checked against
# an independent source, and they are the same cases as the "Worked
# examples index" in docs/QUERIES.md (test-derived-queries.sh test 22
# checks that every index row appears here).
def derived_queries_case(reg: dict[str, Any]) -> dict[str, Any]:
    cases: list[tuple[str, list[Any], Any]] = [
        ('is_eu', ['DE'], True),
        ('is_eu', ['de'], True),
        ('is_eu', ['GB'], False),
        ('is_eu', ['CH'], False),
        ('is_eu', ['XK'], False),
        ('is_eu', ['UK'], False),
        ('is_eu', ['EU'], False),
        ('is_eu', ['ZZ'], False),
        ('is_eea', ['DE'], True),
        ('is_eea', ['NO'], True),
        ('is_eea', ['IS'], True),
        ('is_eea', ['LI'], True),
        ('is_eea', ['CH'], False),
        ('is_eurozone', ['DE'], True),
        ('is_eurozone', ['BG'], True),
        ('is_eurozone', ['SE'], False),
        ('is_eurozone', ['AD'], False),
        ('is_eurozone', ['ME'], False),
        ('is_eurozone', ['GF'], False),
        ('is_eurozone', ['GB'], False),
        ('region_tree', ['FR'], ['Europe', 'Western Europe']),
        ('region_tree', ['US'], ['Americas', 'Northern America']),
        ('region_tree', ['MX'], ['Americas', 'Latin America and the Caribbean', 'Central America']),
        ('region_tree', ['YU'], ['Southern Europe']),
        ('region_tree', ['DD'], ['Western Europe']),
        ('region_tree', ['TW'], []),
        ('region_tree', ['AQ'], []),
        ('region_tree', ['ZZ'], []),
        ('borders_transitively', ['US', 1], ['CA', 'MX']),
        ('borders_transitively', ['DE', 1], ['AT', 'BE', 'CH', 'CZ', 'DK', 'FR', 'LU', 'NL', 'PL']),
        ('borders_transitively', ['DE', 2], ['AD', 'AT', 'BE', 'BY', 'CH', 'CZ', 'DK', 'ES', 'FR', 'HU', 'IT', 'LI', 'LT', 'LU', 'MC', 'NL', 'PL', 'RU', 'SI', 'SK', 'UA']),
        ('borders_transitively', ['LI', 2], ['AT', 'CH', 'CZ', 'DE', 'FR', 'HU', 'IT', 'SI', 'SK']),
        ('borders_transitively', ['AQ', 2], []),
        ('borders_transitively', ['US', 0], []),
        ('borders_transitively', ['DD', 2], []),
        ('succession_path', ['YU', 'RS'], ['YU', 'CS', 'RS']),
        ('succession_path', ['YU', 'ME'], ['YU', 'CS', 'ME']),
        ('succession_path', ['YU', 'YU'], ['YU']),
        ('succession_path', ['DD', 'DE'], ['DD', 'DE']),
        ('succession_path', ['AN', 'CW'], ['AN', 'CW']),
        ('succession_path', ['SK', 'IN'], ['SK', 'IN']),
        ('succession_path', ['SU', 'RU'], None),
        ('succession_path', ['US', 'GB'], None),
        ('succession_path', ['YU', 'ZZ'], None),
        ('successors', ['YU'], ['CS', 'ME', 'RS']),
        ('successors', ['CS'], ['ME', 'RS']),
        ('successors', ['AN'], ['BQ', 'CW', 'SX']),
        ('successors', ['SK'], ['IN']),
        ('successors', ['RS'], []),
        ('successors', ['US'], []),
        ('successors', ['SU'], []),
        ('predecessors', ['RS'], ['CS', 'YU']),
        ('predecessors', ['ME'], ['CS', 'YU']),
        ('predecessors', ['CS'], ['YU']),
        ('predecessors', ['CW'], ['AN']),
        ('predecessors', ['IN'], ['SK']),
        ('predecessors', ['YU'], []),
        ('predecessors', ['US'], []),
        ('calling_code_for', ['+44 20 7946 0958'], ['GB', 'GG', 'IM', 'JE']),
        ('calling_code_for', ['44 20 7946 0958'], ['GB', 'GG', 'IM', 'JE']),
        ('calling_code_for', ['+44 (0) 20.7946.0958'], ['GB', 'GG', 'IM', 'JE']),
        ('calling_code_for', ['+49 30 1234567'], ['DE']),
        ('calling_code_for', ['+7 495 123 4567'], ['KZ', 'RU']),
        ('calling_code_for', ['+1 202 555 0100'], ['AG', 'AI', 'AS', 'BB', 'BM', 'BS', 'CA', 'DM', 'DO', 'GD', 'GU', 'JM', 'KN', 'KY', 'LC', 'MP', 'MS', 'PR', 'SX', 'TC', 'TT', 'UM', 'US', 'VC', 'VG', 'VI']),
        ('calling_code_for', ['+1-867-555-0100'], ['AG', 'AI', 'AS', 'BB', 'BM', 'BS', 'CA', 'DM', 'DO', 'GD', 'GU', 'JM', 'KN', 'KY', 'LC', 'MP', 'MS', 'PR', 'SX', 'TC', 'TT', 'UM', 'US', 'VC', 'VG', 'VI']),
        ('calling_code_for', ['+999 123'], []),
        ('calling_code_for', ['nonsense'], []),
        ('calling_code_for', [''], []),
        ('currency_at', ['DE', '2000-01-01'], ['EUR']),
        ('currency_at', ['DE', '1990-01-01'], ['EUR']),
        ('currency_at', ['PA', '2000-01-01'], ['PAB', 'USD']),
        # v1.11.1: bounded by the entry's lifetime (introduced / withdrawal_date).
        ('currency_at', ['DE', '1970-01-01'], None),
        ('currency_at', ['BJ', '2000-01-01'], None),
        ('currency_at', ['AQ', '2000-01-01'], None),
        ('currency_at', ['EU', '2000-01-01'], None),
        ('currency_at', ['DD', '1990-01-01'], ['EUR']),
        ('currency_at', ['DD', '1990-10-03'], ['EUR']),
        ('currency_at', ['DD', '1990-10-04'], None),
        ('currency_at', ['DD', '1991-01-01'], None),
        ('currency_at', ['YU', '2003-07-23'], ['EUR', 'RSD']),
        ('currency_at', ['YU', '2004-01-01'], None),
        ('currency_at', ['AN', '2010-11-30'], ['ANG', 'USD']),
        ('currency_at', ['AN', '2010-12-01'], ['ANG', 'USD']),
        ('currency_at', ['SU', '2000-01-01'], None),
        ('currency_at', ['DE', '2000-13-01'], None),
        ('currency_at', ['ZZ', '2000-01-01'], None),
        ('region_countries', ['Europe', 'Western Europe'], ['AT', 'BE', 'CH', 'DE', 'FR', 'LI', 'LU', 'MC', 'NL']),
        ('region_countries', ['europe', 'western europe'], ['AT', 'BE', 'CH', 'DE', 'FR', 'LI', 'LU', 'MC', 'NL']),
        ('region_countries', ['Americas', 'Northern America'], ['BM', 'CA', 'GL', 'PM', 'US']),
        ('region_countries', ['Antarctica'], []),
        ('region_countries', ['Nonexistent'], []),
        # v1.11.0: tri-state. null = unknown (introduced is null).
        ('is_active_on', ['DE', '1990-01-01'], True),
        ('is_active_on', ['DE', '1970-01-01'], False),
        ('is_active_on', ['BJ', '2000-01-01'], None),
        ('is_active_on', ['DD', '1990-01-01'], True),
        ('is_active_on', ['DD', '1990-10-04'], False),
        ('is_active_on', ['YU', '2010-01-01'], False),
        ('is_active_on', ['ZZ', '2000-01-01'], False),
        ('is_active_on', ['EU', '2000-01-01'], None),
        ('is_active_on', ['DD', '1800-01-01'], None),
    ]
    codes = {e["alpha_2"] for e in reg["countries"]["active"]} | {
        e["alpha_2"] for e in reg["countries"]["withdrawn"]
    }
    for q, args, _ in cases:
        if q == "succession_path" and args[1] != "ZZ" and not all(a in codes for a in args):
            raise SystemExit(f"derived_queries: unknown code in {q} {args}")
    return {
        "_comment": (
            "Derived queries (v1.10.0; docs/QUERIES.md). Each case is a "
            "method name in snake_case, string/int arguments, and the "
            "expected JSON result. Every wrapper and the CLI must produce "
            "it. is_eu, is_eea and is_eurozone are approximate. currency_at "
            "(v1.11.1) is bounded by lifetime but returns current currencies. "
            "is_active_on (v1.11.0) is tri-state: null means unknown."
        ),
        "enforced": True,
        "cases": [
            {"query": q, "args": a, "expected": x} for q, a, x in cases
        ],
    }


def independent_case(reg: dict[str, Any]) -> dict[str, Any]:
    """Fixture case pinning the independent field for all wrappers.

    `enforced` is True only once tools/independent_snapshot.json is
    populated. Before the data commit the registry still carries the old
    values, so wrappers skip the value assertions instead of failing.
    """
    codes = {e["alpha_2"] for e in reg["countries"]["active"]}
    missing = sorted(set(INDEPENDENT_TRUE + INDEPENDENT_FALSE) - codes)
    if missing:
        raise SystemExit(f"independent fixture: not active entries: {missing}")
    try:
        snap = json.loads(INDEPENDENT_SNAPSHOT.read_text(encoding="utf-8"))
    except FileNotFoundError:
        snap = {}
    return {
        "_comment": "Pins the independent field. All four wrappers must return the same boolean.",
        "enforced": bool(snap.get("entries")),
        "true": list(INDEPENDENT_TRUE),
        "false": list(INDEPENDENT_FALSE),
        "count_true_min": INDEPENDENT_COUNT_TRUE_MIN,
        "count_true_max": INDEPENDENT_COUNT_TRUE_MAX,
    }


def empty_inputs_case() -> dict[str, Any]:
    """Empty string -> None/null/nil for lookups, [] for list queries."""
    cases = [
        {"method": m, "input": "", "expected": None}
        for m in ("active", "by_alpha3", "by_numeric")
    ] + [
        {"method": m, "input": "", "expected": []}
        for m in ("region", "subregion", "search", "countries_with")
    ]
    return {
        "_comment": "Empty string -> nil/empty for every lookup (DEC-2).",
        "enforced": ENFORCE_INPUT_CONTRACT,
        "cases": cases,
    }


def numeric_absent_case() -> dict[str, Any]:
    """Inputs for which by_numeric must return None."""
    return {
        "_comment": (
            "by_numeric returns None: empty, sentinel 000, single-digit 0 "
            "(pads to 000), and whitespace-padded input (not trimmed)."
        ),
        "enforced": ENFORCE_INPUT_CONTRACT,
        "cases": list(NUMERIC_ABSENT_INPUTS),
    }


def alpha2_ambiguous_case(reg: dict[str, Any]) -> dict[str, Any]:
    """Codes present in both active and withdrawn: active entry first."""
    active = {e["alpha_2"] for e in reg["countries"]["active"]}
    cases: dict[str, Any] = {}
    for code in AMBIGUOUS_ALPHA2:
        n_withdrawn = sum(
            1 for e in reg["countries"]["withdrawn"] if e["alpha_2"] == code
        )
        if code not in active or n_withdrawn != 1:
            raise SystemExit(f"alpha2_ambiguous: {code} is not active+withdrawn")
        cases[code] = {"first": "active", "count": 2}
    return {
        "_comment": (
            "AI and SK appear in both active and withdrawn. with_alpha2 "
            "must return the active entry first, count 2."
        ),
        "enforced": ENFORCE_INPUT_CONTRACT,
        "cases": cases,
    }


def _closure(start: str, edges: dict[str, list[str]]) -> list[str]:
    """Transitive closure over `edges` from `start`, excluding it, sorted."""
    seen: set[str] = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        for nxt in edges.get(cur, ()):
            if nxt != start and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return sorted(seen)


def _forward_edges(reg: dict[str, Any]) -> dict[str, list[str]]:
    return {
        e["alpha_2"]: list(e["replaced_by"])
        for e in reg["countries"]["withdrawn"] if e.get("replaced_by")
    }


def successors_case(reg: dict[str, Any]) -> dict[str, Any]:
    """All descendants (transitive closure) of each input, v1.10.0."""
    known = {e["alpha_2"] for e in reg["countries"]["active"]} | {
        e["alpha_2"] for e in reg["countries"]["withdrawn"]
    }
    edges = _forward_edges(reg)
    cases = []
    for code in SUCCESSOR_INPUTS:
        if code not in known:
            raise SystemExit(f"successors: {code} not in registry")
        cases.append({"input": code, "successors": _closure(code, edges)})
    return {
        "_comment": (
            "All descendants of the input: the transitive closure of "
            "replaced_by, intermediate codes included, excluding the input, "
            "sorted. Changed in v1.10.0 from terminal successors only "
            "(a breaking change for the CLI); see docs/QUERIES.md, Query 5."
        ),
        "enforced": ENFORCE_INPUT_CONTRACT,
        "cases": cases,
    }


def predecessors_case(reg: dict[str, Any]) -> dict[str, Any]:
    """All ancestors (transitive closure, reversed) of each input, v1.10.0."""
    reverse: dict[str, list[str]] = {}
    for src, dsts in _forward_edges(reg).items():
        for d in dsts:
            reverse.setdefault(d, []).append(src)
    cases = [
        {"input": code, "predecessors": _closure(code, reverse)}
        for code in PREDECESSOR_INPUTS
    ]
    return {
        "_comment": (
            "All ancestors of the input: every withdrawn code from which it "
            "is reachable through replaced_by, sorted. Changed in v1.10.0 "
            "from terminal-only; see docs/QUERIES.md, Query 5."
        ),
        "enforced": ENFORCE_INPUT_CONTRACT,
        "cases": cases,
    }


def collect_optional_absent(reg):
    """Return the fixture vector for absent optional fields."""
    active = reg["countries"]["active"]

    # A non-officially-assigned entry with no official_name.
    null_name = next(
        e["alpha_2"] for e in active
        if e["status"] != "officially-assigned" and e.get("official_name") is None
    )
    # An officially-assigned entry with an empty borders list.
    empty_borders = next(
        e["alpha_2"] for e in active
        if e["status"] == "officially-assigned" and e.get("borders") == []
    )

    return [
        {"input": null_name, "field": "official_name", "expected": None},
        {"input": empty_borders, "field": "borders", "expected": []},
    ]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    reg = json.loads(args.registry.read_text(encoding="utf-8"))
    doc = build(reg)

    text = json.dumps(doc, indent=2, sort_keys=False, ensure_ascii=False) + "\n"

    if args.check:
        if FIXTURE.exists() and FIXTURE.read_text(encoding="utf-8") == text:
            print("fixture: OK")
            return 0
        print("fixture: STALE", file=sys.stderr)
        return 1

    FIXTURE.write_text(text, encoding="utf-8")
    print(f"wrote {FIXTURE} ({len(text):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
