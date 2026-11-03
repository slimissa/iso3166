#!/usr/bin/env python3
"""Gate: every active entry's `introduced` equals the introduced snapshot.

Reads iso3166.json and tools/introduced_snapshot.json (both located
relative to this file). Takes no flags. Exit 0: they agree. Exit 1: they
differ, or an input is missing or unreadable.

Rules, for every entry in countries.active:
  - the snapshot must have an entry for the alpha-2 code;
  - the entry must carry `introduced`, and it must equal the snapshot's
    data[alpha_2];
  - where the snapshot value is null, the entry's value must be null, and
    meta.null_reasons must carry a reason for that code.

Withdrawn entries are not compared: the snapshot holds one value per code,
and AI and SK exist in both sections.

validate.py runs the same comparison in its integrity layer
(`introduced_mismatches`), so `--only integrity` and the full run both
enforce it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_MISSING = object()


def introduced_mismatches(reg: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    """Return one message per active entry that disagrees with the snapshot."""
    data = snapshot.get("data")
    if not isinstance(data, dict):
        return ["tools/introduced_snapshot.json has no 'data' object"]
    reasons = (snapshot.get("meta") or {}).get("null_reasons") or {}
    errors: list[str] = []
    for i, entry in enumerate(reg.get("countries", {}).get("active", [])):
        a2 = entry.get("alpha_2", "?")
        where = f"active[{i}] ({a2})"
        tree = entry.get("introduced", _MISSING)
        if a2 not in data:
            errors.append(f"{where}: no entry for {a2} in tools/introduced_snapshot.json")
            continue
        snap = data[a2]
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


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    reg_path = root / "iso3166.json"
    snap_path = root / "tools" / "introduced_snapshot.json"
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read inputs: {exc}", file=sys.stderr)
        return 1

    errors = introduced_mismatches(reg, snap)
    if errors:
        for msg in errors:
            print(f"FAIL: {msg}", file=sys.stderr)
        print(f"\n{len(errors)} active entr{'y' if len(errors) == 1 else 'ies'} "
              "disagree with tools/introduced_snapshot.json", file=sys.stderr)
        return 1

    active = reg.get("countries", {}).get("active", [])
    nulls = sum(1 for e in active if e.get("introduced") is None)
    print(f"OK: introduced matches the snapshot for {len(active)} active entries "
          f"({nulls} null, each with a documented reason)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
