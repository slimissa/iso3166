#!/usr/bin/env python3
"""Gate: every active entry's `introduced` equals the introduced snapshot.

Reads iso3166.json and tools/introduced_snapshot.json (both located
relative to this file). Exit 0: they agree. Exit 1: they differ, a date is
in the future, or an input is missing or unreadable.

Flag: --today YYYY-MM-DD replaces today's date for the future-date rule
(used by the tests).

Rules, for every entry in countries.active:
  - the snapshot must have an entry for the alpha-2 code;
  - the entry must carry `introduced`, and it must equal the snapshot's
    data[alpha_2];
  - where the snapshot value is null, the entry's value must be null, and
    meta.null_reasons must carry a reason for that code;
  - no `introduced` date, in the entry or in the snapshot, may be later than
    today. A date in the future is an error in the source or a typo, and the
    two files can agree on it (both wrong), so the comparison alone misses it.

Withdrawn entries are not compared: the snapshot holds one value per code,
and AI and SK exist in both sections.

validate.py runs the same comparison in its integrity layer
(`introduced_mismatches`), so `--only integrity` and the full run both
enforce it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

_MISSING = object()


_FULL_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def introduced_mismatches(
    reg: dict[str, Any],
    snapshot: dict[str, Any],
    today: str | None = None,
) -> list[str]:
    """Return one message per active entry that disagrees with the snapshot,
    and one per `introduced` date (entry or snapshot) later than today."""
    data = snapshot.get("data")
    if not isinstance(data, dict):
        return ["tools/introduced_snapshot.json has no 'data' object"]
    today = today or date.today().isoformat()
    reasons = (snapshot.get("meta") or {}).get("null_reasons") or {}
    errors: list[str] = []
    for a2, value in sorted(data.items()):
        if isinstance(value, str) and _FULL_DATE.match(value) and value > today:
            errors.append(
                f"snapshot {a2}: introduced {value} is in the future (today is {today})"
            )
    for i, entry in enumerate(reg.get("countries", {}).get("active", [])):
        a2 = entry.get("alpha_2", "?")
        where = f"active[{i}] ({a2})"
        tree = entry.get("introduced", _MISSING)
        if a2 not in data:
            errors.append(f"{where}: no entry for {a2} in tools/introduced_snapshot.json")
            continue
        snap = data[a2]
        if isinstance(tree, str) and _FULL_DATE.match(tree) and tree > today:
            # Equal on both sides is the case the comparison cannot see.
            errors.append(
                f"{where}: introduced {tree} is in the future (today is {today})"
            )
        if tree is _MISSING:
            errors.append(f"{where}: 'introduced' is missing in iso3166.json; snapshot has {snap!r}")
        elif tree != snap:
            errors.append(
                f"{where}: introduced is {tree!r} in iso3166.json "
                f"but {snap!r} in tools/introduced_snapshot.json"
            )
        elif snap is None and a2 not in reasons:
            errors.append(
                f"{where}: snapshot value is null but meta.null_reasons has no reason for {a2}"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--today", default=None, metavar="YYYY-MM-DD",
                        help="Replace today's date for the future-date rule.")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    reg_path = root / "iso3166.json"
    snap_path = root / "tools" / "introduced_snapshot.json"
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read inputs: {exc}", file=sys.stderr)
        return 1

    errors = introduced_mismatches(reg, snap, args.today)
    if errors:
        for msg in errors:
            print(f"FAIL: {msg}", file=sys.stderr)
        print(f"\n{len(errors)} problem{'' if len(errors) == 1 else 's'} between "
              "iso3166.json, tools/introduced_snapshot.json and today's date",
              file=sys.stderr)
        return 1

    active = reg.get("countries", {}).get("active", [])
    nulls = sum(1 for e in active if e.get("introduced") is None)
    print(f"OK: introduced matches the snapshot for {len(active)} active entries "
          f"({nulls} null, each with a documented reason)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
