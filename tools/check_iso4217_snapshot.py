#!/usr/bin/env python3
"""
tools/check_iso4217_snapshot.py

Well-formedness check for tools/iso4217_snapshot.json. Advisory in
v1.0.0. Verifies the file parses, has no duplicate codes, all codes
match ^[A-Z]{3}$, and meta counts agree with the actual arrays.

The source-vs-snapshot freshness check is manual:
    tools/gen_iso4217_snapshot.py --check --source PATH

Exit codes:
    0  Well-formed.
    1  Malformed.
    2  File missing.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


SNAPSHOT = Path("tools/iso4217_snapshot.json")
CODE_RE = re.compile(r"^[A-Z]{3}$")


def main() -> int:
    if not SNAPSHOT.exists():
        print(f"error: {SNAPSHOT} missing", file=sys.stderr)
        return 2

    try:
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: {SNAPSHOT}: invalid JSON: {exc}", file=sys.stderr)
        return 1

    active = data.get("active", [])
    withdrawn = data.get("withdrawn", [])
    meta = data.get("meta", {})

    problems: list[str] = []
    if meta.get("count_active") != len(active):
        problems.append(
            f"meta.count_active is {meta.get('count_active')}, "
            f"len(active) is {len(active)}"
        )
    if meta.get("count_withdrawn") != len(withdrawn):
        problems.append(
            f"meta.count_withdrawn is {meta.get('count_withdrawn')}, "
            f"len(withdrawn) is {len(withdrawn)}"
        )
    for code in active + withdrawn:
        if not CODE_RE.match(code):
            problems.append(f"bad currency code: {code!r}")
    if len(set(active)) != len(active):
        problems.append("duplicate entries in active")
    if len(set(withdrawn)) != len(withdrawn):
        problems.append("duplicate entries in withdrawn")

    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        return 1

    print(f"OK: {len(active)} active, {len(withdrawn)} withdrawn, all well-formed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
