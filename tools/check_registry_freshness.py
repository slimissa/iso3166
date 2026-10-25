#!/usr/bin/env python3
"""
tools/check_registry_freshness.py

Enforce that `last_verified` is recent on every entry, active and
withdrawn. Threshold: 365 days. ISO 3166-1 amends every 1-3 years; a
year of staleness forces annual re-attestation without being
over-aggressive.

An entry is flagged when its last_verified is missing, not an ISO date,
in the future, or more than 365 days before today.

Usage:
    python3 tools/check_registry_freshness.py
    python3 tools/check_registry_freshness.py --today 2026-10-22
    python3 tools/check_registry_freshness.py --warn     # print, exit 0

Exit codes: 0 fresh (or --warn); 1 at least one entry flagged; 2 usage
or input error.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THRESHOLD_DAYS = 365


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        sys.exit(2)


def main(argv=None) -> int:
    ap = Parser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD)")
    ap.add_argument("--warn", action="store_true", help="report but exit 0")
    ap.add_argument("--input", type=Path, default=ROOT / "iso3166.json")
    a = ap.parse_args(argv)
    try:
        today = date.fromisoformat(a.today) if a.today else date.today()
    except ValueError:
        print(f"error: --today must be YYYY-MM-DD, got {a.today!r}", file=sys.stderr)
        return 2
    try:
        d = json.loads(a.input.read_text(encoding="utf-8"))
        groups = (("active", d["countries"]["active"]),
                  ("withdrawn", d["countries"]["withdrawn"]))
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: cannot read {a.input}: {exc}", file=sys.stderr)
        return 2

    flagged, total = [], 0
    for kind, entries in groups:
        for e in entries:
            total += 1
            lv = e.get("last_verified")
            tag = f"{e.get('alpha_2')}/{e.get('alpha_3')} ({kind})"
            try:
                age = (today - date.fromisoformat(lv)).days
            except (TypeError, ValueError):
                flagged.append((tag, f"last_verified {lv!r} is not an ISO date"))
                continue
            if age < 0:
                flagged.append((tag, f"last_verified {lv} is in the future"))
            elif age > THRESHOLD_DAYS:
                flagged.append((tag, f"last_verified {lv} is {age} days old "
                                     f"(limit {THRESHOLD_DAYS})"))
    for tag, why in flagged:
        print(f"{'WARN' if a.warn else 'STALE'}: {tag}: {why}")
    if flagged:
        print(f"{len(flagged)} of {total} entries flagged as of {today}")
        return 0 if a.warn else 1
    print(f"OK: all {total} entries verified within {THRESHOLD_DAYS} days of {today}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
