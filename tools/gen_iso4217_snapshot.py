#!/usr/bin/env python3
"""
tools/gen_iso4217_snapshot.py

Generate tools/iso4217_snapshot.json from an ISO 4217 registry file.

The snapshot is a minimal, committed extract of the ISO 4217 registry:
just the alpha currency codes, so that this repository can validate
currency_codes references without a runtime dependency on the sibling
registry.

Refresh procedure (manual, on every ISO 4217 release):

    git clone --depth 1 https://github.com/slimissa/iso4217.git /tmp/iso4217
    python3 tools/gen_iso4217_snapshot.py --source /tmp/iso4217/iso4217.json
    # review the diff
    git add tools/iso4217_snapshot.json
    # update tools/iso4217_snapshot.version in the file's meta block

Usage:
    python3 tools/gen_iso4217_snapshot.py --source PATH
    python3 tools/gen_iso4217_snapshot.py --check --source PATH

Exit codes:
    0  Success (wrote or --check matched)
    1  --check found a stale snapshot
    2  Usage error (bad source, unreadable)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


OUTPUT = Path("tools/iso4217_snapshot.json")

# Only 3-letter alphabetic codes are currencies. ISO 4217's
# active array contains synthetic identifiers (MXN_OLD, and similar)
# that document historical distinctions but are not currencies.
# The snapshot answers "could this be a currency code?", so it keeps
# only real codes.
CODE_RE = re.compile(r"^[A-Z]{3}$")


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def build_snapshot(source_path: Path) -> dict[str, Any]:
    if not source_path.exists():
        raise FatalError(f"source not found: {source_path}")
    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{source_path}: invalid JSON: {exc}") from exc

    meta = data.get("meta", {})
    countries = data.get("currencies", {})

    # ISO 4217 uses countries.active / countries.withdrawn in some
    # shapes and a flat currencies array in others. Handle both.
    active_codes: list[str] = []
    withdrawn_codes: list[str] = []

    if isinstance(countries, dict):
        for entry in countries.get("active", []):
            code = entry.get("code") or entry.get("alpha_3")
            if code:
                active_codes.append(code)
        for entry in countries.get("withdrawn", []):
            code = entry.get("code") or entry.get("alpha_3")
            if code:
                withdrawn_codes.append(code)
    elif isinstance(countries, list):
        for entry in countries:
            code = entry.get("code") or entry.get("alpha_3")
            status = entry.get("status", "active")
            if not code:
                continue
            if status == "withdrawn":
                withdrawn_codes.append(code)
            else:
                active_codes.append(code)

    active_codes = [c for c in active_codes if CODE_RE.match(c)]
    withdrawn_codes = [c for c in withdrawn_codes if CODE_RE.match(c)]

    if not active_codes:
        raise FatalError(
            f"{source_path}: no active currency codes found. "
            f"Check the file's shape."
        )

    return {
        "_comment": (
            "Minimal extract of the ISO 4217 registry: alpha currency "
            "codes only. Used by tools/validate.py to check that any "
            "currency_codes reference resolves. Regenerate with "
            "tools/gen_iso4217_snapshot.py on every ISO 4217 release."
        ),
        "meta": {
            "generated": str(date.today()),
            "source": "slimissa/iso4217",
            "iso4217_version": str(meta.get("version", "")),
            "iso4217_updated": str(meta.get("updated", "")),
            "count_active": len(active_codes),
            "count_withdrawn": len(withdrawn_codes),
        },
        "active": sorted(active_codes),
        "withdrawn": sorted(withdrawn_codes),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True,
                    help="Path to a checked-out iso4217.json.")
    ap.add_argument("--check", action="store_true",
                    help="Verify the committed snapshot is current.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    doc = build_snapshot(args.source)
    text = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

    if args.check:
        if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == text:
            if not args.quiet:
                print(f"  {OUTPUT}: OK")
            return 0
        print(f"  {OUTPUT}: STALE", file=sys.stderr)
        return 1

    OUTPUT.write_text(text, encoding="utf-8")
    if not args.quiet:
        print(f"  wrote {OUTPUT}: "
              f"{doc['meta']['count_active']} active, "
              f"{doc['meta']['count_withdrawn']} withdrawn")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
