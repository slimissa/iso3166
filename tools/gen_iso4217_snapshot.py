#!/usr/bin/env python3
"""
tools/gen_iso4217_snapshot.py

Generate tools/iso4217_snapshot.json from an ISO 4217 registry file.

The snapshot is a minimal, committed extract of the ISO 4217 registry:
just the alpha currency codes, so that this repository can validate
currency_codes references without a runtime dependency on the sibling
registry.

Refresh procedure (manual, on every ISO 4217 release):

    git fetch --tags
    git checkout vX.Y.Z
    python3 tools/gen_iso4217_snapshot.py --source path/to/iso4217.json
    # review the diff
    git add tools/iso4217_snapshot.json

The generator preserves meta.review_by and meta.refresh_cadence from
the existing snapshot. Set review_by manually once if it is null; the
tool preserves the value on every subsequent run.

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


OUTPUT = PROJECT_ROOT / "tools/iso4217_snapshot.json"

# Only 3-letter alphabetic codes are currencies. ISO 4217's
# active array contains synthetic identifiers (MXN_OLD, and
# similar) that document historical distinctions but are not
# currencies. The snapshot answers "could this be a currency
# code?", so it keeps only real codes.
CODE_RE = re.compile(r"^[A-Z]{3}$")


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def _read_existing_meta() -> tuple[str | None, str | None]:
    """Read review_by and refresh_cadence from the committed snapshot.

    Returns (None, None) if the file doesn't exist or is malformed.
    The preservation is best-effort — a corrupted snapshot should not
    stop a refresh.
    """
    if not OUTPUT.exists():
        return None, None
    try:
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    meta = existing.get("meta", {})
    if not isinstance(meta, dict):
        return None, None
    return meta.get("review_by"), meta.get("refresh_cadence")


def _extract_codes(source: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return (active_codes, withdrawn_codes) from a parsed source.

    Handles both shapes the ISO 4217 registry has used:
      - currencies: { active: [...], withdrawn: [...] }
      - currencies: [ { code, status }, ... ]
    """
    currencies = source.get("currencies", {})
    active: list[str] = []
    withdrawn: list[str] = []

    if isinstance(currencies, dict):
        for entry in currencies.get("active", []):
            code = entry.get("code") or entry.get("alpha_3")
            if code:
                active.append(code)
        for entry in currencies.get("withdrawn", []):
            code = entry.get("code") or entry.get("alpha_3")
            if code:
                withdrawn.append(code)
    elif isinstance(currencies, list):
        for entry in currencies:
            code = entry.get("code") or entry.get("alpha_3")
            if not code:
                continue
            if entry.get("status") == "withdrawn":
                withdrawn.append(code)
            else:
                active.append(code)

    active = sorted({c for c in active if CODE_RE.match(c)})
    withdrawn = sorted({c for c in withdrawn if CODE_RE.match(c)})
    return active, withdrawn


def build_snapshot(source_path: Path) -> dict[str, Any]:
    if not source_path.exists():
        raise FatalError(f"source not found: {source_path}")
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{source_path}: invalid JSON: {exc}") from exc

    source_meta = source.get("meta", {})
    active, withdrawn = _extract_codes(source)

    if not active:
        raise FatalError(
            f"{source_path}: no active currency codes found. "
            f"Check the file's shape."
        )

    review_by, refresh_cadence = _read_existing_meta()

    return {
        "_comment": (
            "Minimal extract of the ISO 4217 registry: alpha currency "
            "codes only. Used by tools/validate.py to check that any "
            "currency_codes reference resolves. Regenerate with "
            "tools/gen_iso4217_snapshot.py on every ISO 4217 release."
        ),
        "meta": {
            # No `generated` field: --check compares the whole file, so a
            # date stamped at generation time would make it fail the day
            # after. `iso4217_version` and `iso4217_updated`, copied from
            # the source registry, are the freshness signals.
            "source": "slimissa/iso4217",
            "iso4217_version": str(source_meta.get("version", "")),
            "iso4217_updated": str(source_meta.get("updated", "")),
            "count_active": len(active),
            "count_withdrawn": len(withdrawn),
            "review_by": review_by,
            "refresh_cadence": refresh_cadence or "quarterly",
        },
        "active": active,
        "withdrawn": withdrawn,
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
    text = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

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