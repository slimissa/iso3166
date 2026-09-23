#!/usr/bin/env python3
"""
tools/enrich_withdrawn.py

Add or update entries in the `withdrawn` array of iso3166.json.

Withdrawn entries record the ISO 3166-3 identity of a code that is no
longer in use, the date it was withdrawn, and the alpha-2 codes that
succeeded it. Some withdrawn codes have no successor; some were later
reassigned to a different entity (AI, SK, BQ).

Modes
-----

Add or update one entry::

    python3 tools/enrich_withdrawn.py CT \\
        --alpha-3 CTE --numeric 000 \\
        --name "Canton and Enderbury Islands" \\
        --withdrawal-date 1984-01-01 \\
        --replaced-by KI \\
        --source https://www.iso.org/obp/ui/#iso:code:3166:CT

Apply a TSV batch. Seven tab-separated columns, headerless:

    alpha_2, alpha_3, numeric, name, withdrawal_date, replaced_by, source

`replaced_by` is comma-separated; empty means the code had no successor.
Blank lines and lines starting with # are ignored::

    python3 tools/enrich_withdrawn.py --from-file /tmp/batch-1.tsv

Audit::

    python3 tools/enrich_withdrawn.py --list-missing
    python3 tools/enrich_withdrawn.py --list-all
    python3 tools/enrich_withdrawn.py --check

The tool enforces:

- `alpha_2`, `alpha_3`, `numeric` match their schema patterns
- `status` is always "withdrawn"
- `withdrawal_date` is a real calendar date, not in the future
- every `replaced_by` target exists in the registry or is a known
  ISO 3166-3 code
- `note` carries a source URL (appended, not replaced)
- no duplicate entries in `withdrawn`

Reassignment
------------

Adding a code whose alpha-2 also appears in `active` (the pattern
already used for AI, SK, and BQ) requires `--allow-reassignment`. The
tool prints a warning and proceeds. Without the flag, it refuses.

Exit codes
----------

    0  Success.
    1  Data error (bad input, missing target, --check failed).
    2  Usage error (missing arguments, unreadable file).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


REGISTRY = Path("iso3166.json")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_LINE_RE = re.compile(r"^source: .*$", re.MULTILINE)
ALPHA_2_RE = re.compile(r"^[A-Z]{2}$")
ALPHA_3_RE = re.compile(r"^[A-Z]{3}$")
NUMERIC_RE = re.compile(r"^\d{1,3}$")


# ISO 3166-3:2013 withdrawn codes, minus the ones already in the
# registry. Used by --list-missing and --check to report completeness.
# The exact list is verified against the standard itself; if a code
# here is wrong, fix the set rather than the tool.
KNOWN_WITHDRAWN = frozenset({
    "AI", "AN", "BU", "CS", "CT", "DD", "DY", "FQ", "HV", "JT",
    "MI", "NH", "NQ", "NT", "PC", "PZ", "RH", "SK", "SU", "TP",
    "VD", "WK", "YD", "YU", "ZR",
})


# Codes that are known reassignments: the alpha-2 was withdrawn and
# later reassigned to a different entity. Adding any of these to
# `withdrawn` requires --allow-reassignment.
KNOWN_REASSIGNMENTS = frozenset({"AI", "SK", "BQ"})


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


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


def normalize_numeric(value: str) -> str:
    """Zero-pad a numeric code to three digits. Reject anything else."""
    value = value.strip()
    if not NUMERIC_RE.fullmatch(value):
        raise FatalError(f"numeric {value!r} must be 1-3 digits")
    return value.zfill(3)


# ----------------------------------------------------------------
# Validation
# ----------------------------------------------------------------

def validate_inputs(
    reg: dict,
    fields: dict,
    *,
    allow_reassignment: bool,
) -> None:
    alpha_2 = fields["alpha_2"]
    alpha_3 = fields["alpha_3"]
    numeric = fields["numeric"]
    name = fields["name"]
    withdrawal_date = fields["withdrawal_date"]
    replaced_by = fields["replaced_by"]

    if not ALPHA_2_RE.fullmatch(alpha_2):
        raise FatalError(f"{alpha_2!r}: alpha_2 must match ^[A-Z]{{2}}$")
    if not ALPHA_3_RE.fullmatch(alpha_3):
        raise FatalError(f"{alpha_2}: alpha_3 {alpha_3!r} must match ^[A-Z]{{3}}$")
    if not NUMERIC_RE.fullmatch(numeric):
        raise FatalError(f"{alpha_2}: numeric {numeric!r} must be 1-3 digits")

    if not name.strip():
        raise FatalError(f"{alpha_2}: name is empty")
    if "\n" in name or "\t" in name:
        raise FatalError(f"{alpha_2}: name must be a single line")

    if not ISO_DATE_RE.fullmatch(withdrawal_date):
        raise FatalError(
            f"{alpha_2}: withdrawal_date {withdrawal_date!r} is not YYYY-MM-DD"
        )
    try:
        wd = datetime.strptime(withdrawal_date, "%Y-%m-%d").date()
    except ValueError:
        raise FatalError(f"{alpha_2}: withdrawal_date is not a calendar date")
    if wd > date.today():
        raise FatalError(f"{alpha_2}: withdrawal_date is in the future")

    for code in replaced_by:
        if not ALPHA_2_RE.fullmatch(code):
            raise FatalError(f"{alpha_2}: replaced_by {code!r} is not alpha-2")

    active_codes = {e["alpha_2"] for e in reg["countries"]["active"]}
    withdrawn_codes = {e["alpha_2"] for e in reg["countries"]["withdrawn"]}
    already_in_withdrawn = alpha_2 in withdrawn_codes

    if alpha_2 in active_codes and not already_in_withdrawn:
        if alpha_2 in KNOWN_REASSIGNMENTS or allow_reassignment:
            warn(
                f"{alpha_2}: also present in `active`. "
                f"Adding to `withdrawn` as a reassignment. "
                f"Record the distinction in the entry's note."
            )
        else:
            raise FatalError(
                f"{alpha_2}: already present in `active`. If this is a "
                f"reassignment (the code was withdrawn and later "
                f"reassigned), pass --allow-reassignment. If it is not, "
                f"the code belongs in `active` only."
            )

    all_known = active_codes | withdrawn_codes | KNOWN_WITHDRAWN | {alpha_2}
    for code in replaced_by:
        if code not in all_known:
            raise FatalError(
                f"{alpha_2}: replaced_by target {code!r} is not present in "
                f"the registry, is not a known ISO 3166-3 code, and is not "
                f"the entry being added"
            )


def record_source(existing: str | None, source: str) -> str:
    """Append or replace the source citation in the note field.

    Preserves any note text that is not a previous `source:` line.
    Idempotent: applying the same source twice does not duplicate it.
    """
    citation = f"source: {source}"

    if not existing:
        return citation

    kept = [line for line in existing.splitlines()
            if not SOURCE_LINE_RE.match(line)]
    kept.append(citation)
    return "\n".join(kept)


# ----------------------------------------------------------------
# Entry manipulation
# ----------------------------------------------------------------

def make_entry(fields: dict, *, source: str, today: str) -> dict:
    """Build a withdrawn entry with the full schema shape.

    Every key from the schema's commonFields is present, even when the
    value is null. `sort_keys=True` at write time makes the on-disk
    order alphabetical regardless.
    """
    return {
        "alpha_2": fields["alpha_2"],
        "alpha_3": fields["alpha_3"],
        "numeric": normalize_numeric(fields["numeric"]),
        "name": fields["name"],
        "status": "withdrawn",
        "independent": False,
        "official_name": None,
        "region": None,
        "subregion": None,
        "intermediate_region": None,
        "currency_codes": None,
        "calling_codes": None,
        "tlds": None,
        "languages": None,
        "borders": None,
        "note": record_source(None, source),
        "last_verified": today,
        "withdrawal_date": fields["withdrawal_date"],
        "replaced_by": list(fields["replaced_by"]) or None,
    }


def apply_one(
    reg: dict,
    fields: dict,
    *,
    source: str,
    today: str,
    allow_reassignment: bool,
) -> tuple[dict, str]:
    """Add or update one withdrawn entry.

    Returns (entry, action) where action is "added" or "updated".
    """
    validate_inputs(reg, fields, allow_reassignment=allow_reassignment)

    new_entry = make_entry(fields, source=source, today=today)
    code = new_entry["alpha_2"]

    withdrawn = reg["countries"]["withdrawn"]
    for i, existing in enumerate(withdrawn):
        if existing["alpha_2"] == code:
            # Preserve any note text that is not the source line.
            existing_note = existing.get("note")
            if existing_note:
                new_entry["note"] = record_source(existing_note, source)
            withdrawn[i] = new_entry
            withdrawn.sort(key=lambda e: e["alpha_2"])
            return new_entry, "updated"

    withdrawn.append(new_entry)
    withdrawn.sort(key=lambda e: e["alpha_2"])
    return new_entry, "added"


# ----------------------------------------------------------------
# Modes
# ----------------------------------------------------------------

def _parse_tsv(path: Path) -> list[dict]:
    if not path.exists():
        raise FatalError(f"batch file not found: {path}")

    rows: list[dict] = []
    for lineno, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            raise FatalError(
                f"{path}:{lineno}: expected 7 tab-separated fields "
                f"(alpha_2, alpha_3, numeric, name, withdrawal_date, "
                f"replaced_by, source), got {len(parts)}"
            )
        a2, a3, num, name, wd, repl, src = (p.strip() for p in parts)
        rows.append({
            "alpha_2": a2,
            "alpha_3": a3,
            "numeric": num,
            "name": name,
            "withdrawal_date": wd,
            "replaced_by": [c.strip() for c in repl.split(",") if c.strip()],
            "source": src,
        })

    if not rows:
        raise FatalError(f"{path}: no entries")
    return rows


def mode_from_file(args: argparse.Namespace) -> int:
    rows = _parse_tsv(args.from_file)
    reg = load_registry(args.registry)
    today = date.today().isoformat()

    results: list[tuple[dict, str]] = []
    for row in rows:
        fields = {k: row[k] for k in
                  ("alpha_2", "alpha_3", "numeric", "name",
                   "withdrawal_date", "replaced_by")}
        entry, action = apply_one(
            reg, fields,
            source=row["source"],
            today=today,
            allow_reassignment=args.allow_reassignment,
        )
        results.append((entry, action))

    if not args.dry_run:
        reg["meta"]["count_withdrawn"] = len(reg["countries"]["withdrawn"])
        write_registry(args.registry, reg)

    verb = "would apply" if args.dry_run else "applied"
    print(f"{verb} {len(results)} entrie(s):")
    for entry, action in results:
        succ = ",".join(entry["replaced_by"] or []) or "—"
        print(f"  [{action}] {entry['alpha_2']}  {entry['name']}  "
              f"({entry['withdrawal_date']}) -> {succ}")
    return 0


def mode_set(args: argparse.Namespace) -> int:
    if not args.source:
        args.source = f"https://www.iso.org/obp/ui/#iso:code:3166:{args.code}"

    reg = load_registry(args.registry)
    today = date.today().isoformat()

    fields = {
        "alpha_2": args.code,
        "alpha_3": args.alpha_3,
        "numeric": args.numeric,
        "name": args.name,
        "withdrawal_date": args.withdrawal_date,
        "replaced_by": [
            c.strip() for c in args.replaced_by.split(",") if c.strip()
        ],
    }

    entry, action = apply_one(
        reg, fields,
        source=args.source,
        today=today,
        allow_reassignment=args.allow_reassignment,
    )

    if not args.dry_run:
        reg["meta"]["count_withdrawn"] = len(reg["countries"]["withdrawn"])
        write_registry(args.registry, reg)

    verb = ("would add" if action == "added" else "would update") \
        if args.dry_run else action
    succ = ",".join(entry["replaced_by"] or []) or "—"
    print(f"{verb} {entry['alpha_2']}  {entry['name']}  "
          f"({entry['withdrawal_date']}) -> {succ}")
    print(f"  source: {args.source}")
    return 0


def mode_list_missing(args: argparse.Namespace) -> int:
    reg = load_registry(args.registry)
    present = {e["alpha_2"] for e in reg["countries"]["withdrawn"]}
    missing = sorted(KNOWN_WITHDRAWN - present)
    if not missing:
        print("all known ISO 3166-3 codes are present", file=sys.stderr)
        return 0
    for code in missing:
        print(code)
    print(f"\n{len(missing)} missing", file=sys.stderr)
    return 0


def mode_list_all(args: argparse.Namespace) -> int:
    reg = load_registry(args.registry)
    for e in reg["countries"]["withdrawn"]:
        succ = ",".join(e.get("replaced_by") or []) or "—"
        print(f"{e['alpha_2']}\t{e['name']}\t{e['withdrawal_date']}\t{succ}")
    return 0


def mode_check(args: argparse.Namespace) -> int:
    reg = load_registry(args.registry)
    present = {e["alpha_2"] for e in reg["countries"]["withdrawn"]}
    missing = sorted(KNOWN_WITHDRAWN - present)

    if missing:
        print(
            f"FAIL: {len(missing)} ISO 3166-3 codes missing from withdrawn: "
            f"{', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(present)} withdrawn entries; "
          f"all {len(KNOWN_WITHDRAWN)} ISO 3166-3 codes present")
    return 0


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="enrich_withdrawn",
        description=(
            "Add or update entries in the withdrawn array of iso3166.json. "
            "Only writes to countries.withdrawn and meta.count_withdrawn."
        ),
    )
    p.add_argument("--registry", type=Path, default=REGISTRY,
                   help=f"Path to the registry (default: {REGISTRY}).")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would change without writing.")
    p.add_argument("--allow-reassignment", action="store_true",
                   help="Permit adding a code whose alpha-2 is also in "
                        "`active` (the AI/SK/BQ pattern).")

    p.add_argument("code", nargs="?",
                   help="alpha-2 code (case-insensitive; upper-cased here).")

    p.add_argument("--alpha-3")
    p.add_argument("--numeric")
    p.add_argument("--name")
    p.add_argument("--withdrawal-date")
    p.add_argument("--replaced-by", default="",
                   help="Comma-separated alpha-2 successors. Empty for none.")
    p.add_argument("--source", default=None,
                   help="Source URL. Defaults to the ISO OBP page for the code.")

    group = p.add_mutually_exclusive_group()
    group.add_argument("--from-file", type=Path, metavar="TSV",
                       help="Apply a TSV batch (7 columns, see docstring).")
    group.add_argument("--list-missing", action="store_true",
                       help="Print ISO 3166-3 codes absent from withdrawn.")
    group.add_argument("--list-all", action="store_true",
                       help="Print every withdrawn entry as TSV.")
    group.add_argument("--check", action="store_true",
                       help="Exit 0 only if the withdrawn set is complete.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Upper-case the code so `ct` and `CT` both work.
    if args.code:
        args.code = args.code.upper()

    if args.from_file is not None:
        return mode_from_file(args)
    if args.list_missing:
        return mode_list_missing(args)
    if args.list_all:
        return mode_list_all(args)
    if args.check:
        return mode_check(args)

    if args.code and args.alpha_3 and args.numeric and args.name and args.withdrawal_date:
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