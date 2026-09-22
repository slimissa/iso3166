#!/usr/bin/env python3
"""
tools/enrich_official_name.py

Populate the `official_name` field of entries in iso3166.json.

The official name is what ISO 3166-1 publishes as the entry's full name
on the Online Browsing Platform (OBP). For some entries it is identical
to the short name (Japan, Israel); for others it is much longer
("United Kingdom of Great Britain and Northern Ireland"). Both are
recorded as-is; the field is not "the name if it differs".

Modes:

    # Set one entry. The source defaults to the ISO OBP page for the code.
    python3 tools/enrich_official_name.py AL "Republic of Albania"

    # Override the source for an entry sourced from elsewhere.
    python3 tools/enrich_official_name.py XK "Republic of Kosovo" \
        --source "https://example.org/citation"

    # Apply a TSV batch: CODE<TAB>Official Name, one per line.
    # Blank lines and lines starting with # are ignored.
    python3 tools/enrich_official_name.py --from-file /tmp/batch-1.tsv

    # Show what is still missing, as CODE<TAB>short name.
    python3 tools/enrich_official_name.py --list-missing

    # Show every officially-assigned entry with its current values.
    python3 tools/enrich_official_name.py --list-all

    # CI gate: exit 0 only if every officially-assigned entry has
    # official_name, exit 1 otherwise.
    python3 tools/enrich_official_name.py --check

The tool only writes to `official_name`, `last_verified`, and `note` on
the target entry. It does not touch `meta`, does not reorder entries,
and does not modify other fields.

Exit codes:
    0  Success.
    1  Data error (entry missing, wrong status, --check failed).
    2  Usage error (bad arguments, missing file).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


REGISTRY = Path("iso3166.json")
OFFICIAL_NAME_SOURCE_RE = re.compile(r"^official_name source: .*$", re.MULTILINE)
OBP_URL_TEMPLATE = "https://www.iso.org/obp/ui/#iso:code:3166:{code}"


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


# ----------------------------------------------------------------
# IO
# ----------------------------------------------------------------

def load_registry(path: Path) -> dict:
    if not path.exists():
        raise FatalError(f"registry not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{path}: invalid JSON: {exc}") from exc


def write_registry(path: Path, data: dict) -> None:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


# ----------------------------------------------------------------
# Entry manipulation
# ----------------------------------------------------------------

def find_active(reg: dict, alpha_2: str) -> dict:
    code = alpha_2.upper()
    for entry in reg["countries"]["active"]:
        if entry["alpha_2"] == code:
            return entry
    raise FatalError(f"{code}: not present in countries.active")


def record_source_in_note(existing: str | None, source: str) -> str:
    """Append or replace the source citation in the note field.

    Preserves any text that is not a previous `official_name source:`
    line. Idempotent: applying the same source twice does not duplicate
    the line.
    """
    citation = f"official_name source: {source}"

    if not existing:
        return citation

    kept = [line for line in existing.splitlines()
            if not OFFICIAL_NAME_SOURCE_RE.match(line)]
    kept.append(citation)
    return "\n".join(kept)


def apply_one(
    reg: dict,
    alpha_2: str,
    official_name: str,
    *,
    source: str | None,
    today: str,
) -> dict:
    """Set official_name on one entry. Returns a summary dict for logging."""
    if not official_name or not official_name.strip():
        raise FatalError(f"{alpha_2}: official_name is empty")
    if "\n" in official_name or "\t" in official_name:
        raise FatalError(f"{alpha_2}: official_name must be a single line")

    official_name = official_name.strip()
    entry = find_active(reg, alpha_2)

    if entry["status"] != "officially-assigned":
        raise FatalError(
            f"{entry['alpha_2']}: status is {entry['status']!r}; "
            f"official_name is only populated for officially-assigned entries"
        )

    code = entry["alpha_2"]
    effective_source = source or OBP_URL_TEMPLATE.format(code=code)

    before = entry.get("official_name")
    entry["official_name"] = official_name
    entry["last_verified"] = today
    entry["note"] = record_source_in_note(entry.get("note"), effective_source)

    return {
        "alpha_2": code,
        "short_name": entry["name"],
        "before": before,
        "after": official_name,
        "source": effective_source,
    }


# ----------------------------------------------------------------
# Modes
# ----------------------------------------------------------------

def mode_set(args: argparse.Namespace) -> int:
    reg = load_registry(args.registry)
    today = date.today().isoformat()

    summary = apply_one(
        reg, args.code, args.official_name,
        source=args.source, today=today,
    )

    if not args.dry_run:
        write_registry(args.registry, reg)

    verb = "would set" if args.dry_run else "set"
    print(f"{verb} {summary['alpha_2']} ({summary['short_name']}):")
    print(f"  official_name: {summary['after']}")
    print(f"  source:        {summary['source']}")
    if summary["before"] and summary["before"] != summary["after"]:
        print(f"  (was: {summary['before']})")
    return 0


def mode_from_file(args: argparse.Namespace) -> int:
    if not args.from_file.exists():
        raise FatalError(f"batch file not found: {args.from_file}")

    rows: list[tuple[str, str]] = []
    for lineno, raw in enumerate(args.from_file.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise FatalError(
                f"{args.from_file}:{lineno}: expected 'CODE<TAB>Official Name', "
                f"got {line!r}"
            )
        code, name = parts[0].strip(), parts[1].strip()
        if not code or not name:
            raise FatalError(f"{args.from_file}:{lineno}: empty code or name")
        rows.append((code, name))

    if not rows:
        raise FatalError(f"{args.from_file}: no entries")

    reg = load_registry(args.registry)
    today = date.today().isoformat()

    summaries = [
        apply_one(reg, code, name, source=args.source, today=today)
        for code, name in rows
    ]

    if not args.dry_run:
        write_registry(args.registry, reg)

    verb = "would set" if args.dry_run else "set"
    print(f"{verb} {len(summaries)} entries:")
    for s in summaries:
        print(f"  {s['alpha_2']}  {s['after']}")
    return 0


def mode_list_missing(args: argparse.Namespace) -> int:
    reg = load_registry(args.registry)
    missing = [
        e for e in reg["countries"]["active"]
        if e["status"] == "officially-assigned" and not e.get("official_name")
    ]
    if not missing:
        print("all officially-assigned entries have official_name", file=sys.stderr)
        return 0

    for e in missing:
        print(f"{e['alpha_2']}\t{e['name']}")
    print(f"\n{len(missing)} missing", file=sys.stderr)
    return 0


def mode_list_all(args: argparse.Namespace) -> int:
    reg = load_registry(args.registry)
    for e in reg["countries"]["active"]:
        if e["status"] != "officially-assigned":
            continue
        short = e["name"]
        official = e.get("official_name") or "(missing)"
        print(f"{e['alpha_2']}\t{short}\t{official}")
    return 0


def mode_check(args: argparse.Namespace) -> int:
    reg = load_registry(args.registry)
    assigned = [e for e in reg["countries"]["active"]
                if e["status"] == "officially-assigned"]
    missing = [e for e in assigned if not e.get("official_name")]

    if missing:
        print(
            f"FAIL: {len(missing)} of {len(assigned)} officially-assigned "
            f"entries lack official_name:",
            file=sys.stderr,
        )
        for e in missing:
            print(f"  {e['alpha_2']}  {e['name']}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(assigned)} of {len(assigned)} officially-assigned "
        f"entries have official_name"
    )
    return 0


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="enrich_official_name",
        description=(
            "Populate the official_name field of entries in iso3166.json. "
            "Only writes official_name, last_verified, and note on the "
            "target entry."
        ),
    )
    p.add_argument("--registry", type=Path, default=REGISTRY,
                   help=f"Path to the registry (default: {REGISTRY}).")
    p.add_argument("--source", default=None,
                   help="Source URL. Defaults to the ISO OBP page for the code.")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would change without writing.")

    p.add_argument("code", nargs="?", help="alpha-2 code (case-insensitive).")
    p.add_argument("official_name", nargs="?",
                   help="The official name to record.")

    group = p.add_mutually_exclusive_group()
    group.add_argument("--from-file", type=Path,
                       help="Apply a TSV batch: CODE<TAB>Official Name.")
    group.add_argument("--list-missing", action="store_true",
                       help="Print officially-assigned entries without official_name.")
    group.add_argument("--list-all", action="store_true",
                       help="Print every officially-assigned entry and its official_name.")
    group.add_argument("--check", action="store_true",
                       help="Exit 0 only if all officially-assigned entries have official_name.")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.from_file is not None:
        return mode_from_file(args)
    if args.list_missing:
        return mode_list_missing(args)
    if args.list_all:
        return mode_list_all(args)
    if args.check:
        return mode_check(args)

    if args.code and args.official_name:
        return mode_set(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)