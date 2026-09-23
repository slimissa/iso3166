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


FIXTURE = Path("tests/cross_language_consistency.json")
REGISTRY = Path("iso3166.json")


def _summarize(entry: dict[str, Any]) -> dict[str, Any]:
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
        })

    return {
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
    }


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
