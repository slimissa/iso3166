#!/usr/bin/env python3
"""Gate: tools/introduced_snapshot.meta.json is complete and agrees with the
snapshot's own meta block.

Reads tools/introduced_snapshot.meta.json and tools/introduced_snapshot.json
(both located relative to this file). Takes no flags. Exit 0: valid. Exit 1:
a problem, or an input is missing or unreadable.

Why this exists: build_introduced_snapshot.py writes introduced_snapshot.json
and its inline `meta` block, but the sibling .meta.json is hand-written. The
generator never reads it, so `build_introduced_snapshot.py --check` cannot
notice when it is incomplete or has drifted. check_snapshot_freshness.py
reads `review_by` from the sibling, so a wrong sibling silently changes when
the snapshot is considered stale.

Rules:
  - The sibling carries its fields under a `meta` object (a flat top-level
    `review_by` is read as unset by check_snapshot_freshness.py).
  - Required in sibling meta: review_by, source, vendored_at.
  - Required in the snapshot's inline meta: review_by, source,
    source_accessed.
  - Each required value is a non-empty string; review_by, vendored_at and
    source_accessed are calendar-valid YYYY-MM-DD dates; review_by is not
    before vendored_at.
  - The two files agree: review_by == review_by, source == source,
    source_permalink == source_permalink (when either has one), and the
    sibling's vendored_at == the inline source_accessed. `vendored_at` is
    the sibling's name for the date the source was read.

Whether review_by has passed is check_snapshot_freshness.py's job, not this
tool's.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

SIBLING_NAME = "tools/introduced_snapshot.meta.json"
SNAPSHOT_NAME = "tools/introduced_snapshot.json"

SIBLING_REQUIRED = ("review_by", "source", "vendored_at")
INLINE_REQUIRED = ("review_by", "source", "source_accessed")
DATE_KEYS = {"review_by", "vendored_at", "source_accessed"}
# (sibling key, inline key): the pairs that must be equal.
PAIRS = (
    ("review_by", "review_by"),
    ("source", "source"),
    ("source_permalink", "source_permalink"),
    ("vendored_at", "source_accessed"),
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(value: str) -> date | None:
    if not _DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _check_block(name: str, block: Any, required: tuple[str, ...]) -> list[str]:
    problems: list[str] = []
    if not isinstance(block, dict):
        return [f"{name}: no 'meta' object"]
    for key in required:
        value = block.get(key)
        if key not in block:
            problems.append(f"{name}: meta.{key} is missing")
        elif not isinstance(value, str) or not value.strip():
            problems.append(f"{name}: meta.{key} must be a non-empty string, got {value!r}")
        elif key in DATE_KEYS and _valid_date(value) is None:
            problems.append(f"{name}: meta.{key} is not a calendar-valid YYYY-MM-DD date: {value!r}")
    return problems


def meta_problems(sibling: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    """Return one message per problem; an empty list means valid."""
    sib = sibling.get("meta") if isinstance(sibling, dict) else None
    inl = snapshot.get("meta") if isinstance(snapshot, dict) else None
    problems = _check_block(SIBLING_NAME, sib, SIBLING_REQUIRED)
    problems += _check_block(SNAPSHOT_NAME, inl, INLINE_REQUIRED)
    if not isinstance(sib, dict) or not isinstance(inl, dict):
        return problems

    review, vendored = _valid_date(str(sib.get("review_by", ""))), _valid_date(str(sib.get("vendored_at", "")))
    if review and vendored and review < vendored:
        problems.append(
            f"{SIBLING_NAME}: meta.review_by {sib['review_by']} is before meta.vendored_at {sib['vendored_at']}"
        )
    for sib_key, inl_key in PAIRS:
        if sib_key not in sib and inl_key not in inl:
            continue
        a, b = sib.get(sib_key), inl.get(inl_key)
        if a is None or b is None:
            continue  # a missing required key was already reported above
        if a != b:
            problems.append(
                f"{SIBLING_NAME} meta.{sib_key} is {a!r} but {SNAPSHOT_NAME} meta.{inl_key} is {b!r}"
            )
    return problems


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    try:
        sibling = json.loads((root / SIBLING_NAME).read_text(encoding="utf-8"))
        snapshot = json.loads((root / SNAPSHOT_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read inputs: {exc}", file=sys.stderr)
        return 1

    problems = meta_problems(sibling, snapshot)
    if problems:
        for msg in problems:
            print(f"FAIL: {msg}", file=sys.stderr)
        print(f"\n{len(problems)} problem(s) in {SIBLING_NAME}", file=sys.stderr)
        return 1

    meta = sibling["meta"]
    print(f"OK: {SIBLING_NAME} is complete and agrees with the snapshot "
          f"(source read {meta['vendored_at']}, review by {meta['review_by']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
