#!/usr/bin/env python3
"""
tools/build_initial_data.py

One-shot importer that produces the first-cut iso3166.json.

This script is *not* part of the ongoing build. It exists to make the
initial import reproducible and auditable. After v1.0.0, iso3166.json
is the source of truth and this script is archival.

Inputs:
    --un-m49 PATH       The UN M49 overview CSV.
    --exceptions PATH   Hand-maintained overrides (see below).
    --schema PATH       Optional; validate output against this schema.

Output:
    --out PATH          iso3166.json (overwritten if present).

Column resolution:
    The M49 CSV has been published with slightly different column names
    over time. The script resolves each needed column by trying a list
    of known aliases. If none match, it fails with a clear message
    listing the aliases it tried and the columns it saw.

Exceptions file structure:
    {
      "officially_assigned": {
        "US": {"independent": true, "official_name": "...", "note": null}
      },
      "exceptionally_reserved": {
        "UK": {"alpha_3": "UKM", "numeric": "000", "name": "...", "note": "..."}
      },
      "user_assigned": {
        "XK": {"alpha_3": "XKX", "numeric": "000", "name": "...", "independent": true, "note": "..."}
      },
      "withdrawn": [
        {"alpha_2": "AN", "alpha_3": "ANT", "numeric": "530", "name": "...",
         "withdrawal_date": "2010-12-01", "replaced_by": ["BQ", "CW", "SX"]}
      ]
    }

Exit codes:
    0  Success. Output written and validated.
    1  Data error (bad CSV, bad exceptions, validation failure).
    2  Usage error (missing arguments, unreadable file).
    3  Schema validation failure (output written but does not conform).

Usage:
    python3 tools/build_initial_data.py \\
        --un-m49 /tmp/un_m49.csv \\
        --exceptions tools/initial_exceptions.json \\
        --out iso3166.json \\
        --schema schema.json

    # Preview without writing:
    python3 tools/build_initial_data.py \\
        --un-m49 /tmp/un_m49.csv \\
        --exceptions tools/initial_exceptions.json \\
        --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


# ============================================================
# Constants
# ============================================================

REGISTRY_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0.0"
SOURCE_STRING = "ISO 3166-1:2020 (cross-checked against UN M49)"
EXPECTED_OFFICIAL_COUNT = 249
M49_URL = "https://unstats.un.org/unsd/methodology/m49/overview/"

REQUIRED_FIELDS = ("alpha_2", "alpha_3", "numeric", "name", "status", "independent")

REQUIRED_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "alpha_2": ("ISO-alpha2 Code", "ISO_alpha2_Code", "Alpha-2 Code", "alpha-2"),
    "alpha_3": ("ISO-alpha3 Code", "ISO_alpha3_Code", "Alpha-3 Code", "alpha-3"),
    "numeric": ("M49 Code", "M49_Code", "Numeric Code", "numeric"),
    "name": ("Country or Area", "Country_or_Area", "Country Name", "Country", "Name"),
}

OPTIONAL_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "region": ("Region Name", "Region_Name", "Region"),
    "subregion": ("Sub-region Name", "Sub_region_Name", "Subregion", "Sub-region"),
    "intermediate_region": (
        "Intermediate Region Name",
        "Intermediate_Region_Name",
        "Intermediate Region",
        "Intermediate_Region",
    ),
}

ALPHA_2_RE = re.compile(r"^[A-Z]{2}$")
ALPHA_3_RE = re.compile(r"^[A-Z]{3}$")
NUMERIC_RE = re.compile(r"^[0-9]{3}$")

VALID_STATUS = {"officially-assigned", "user-assigned", "exceptionally-reserved", "withdrawn"}

# Statuses that may appear in the "active" array.
ACTIVE_STATUSES = {"officially-assigned", "user-assigned", "exceptionally-reserved"}


# ============================================================
# Diagnostics
# ============================================================

class FatalError(SystemExit):
    """Raised for user-facing fatal errors. Always exits with a specific code."""

    def __init__(self, message: str, code: int = 1) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def info(message: str, *, quiet: bool = False) -> None:
    if not quiet:
        print(message, file=sys.stderr)


# ============================================================
# Column resolution
# ============================================================

def _normalize_header(header: str) -> str:
    """Return a lowercase, whitespace-collapsed version of a CSV header."""
    return " ".join(header.strip().lower().split())


def resolve_required_column(
    fieldnames: list[str],
    internal: str,
) -> str:
    """Return the actual CSV column name for a required internal field."""
    aliases = REQUIRED_COLUMN_ALIASES[internal]
    by_normalized = {_normalize_header(f): f for f in fieldnames}
    for alias in aliases:
        key = _normalize_header(alias)
        if key in by_normalized:
            return by_normalized[key]
    raise FatalError(
        f"could not find a column for {internal!r}.\n"
        f"  tried aliases: {list(aliases)}\n"
        f"  available columns: {fieldnames}",
        code=2,
    )


def resolve_optional_column(
    fieldnames: list[str],
    internal: str,
) -> str | None:
    """Return the actual CSV column name for an optional field, or None."""
    aliases = OPTIONAL_COLUMN_ALIASES[internal]
    by_normalized = {_normalize_header(f): f for f in fieldnames}
    for alias in aliases:
        key = _normalize_header(alias)
        if key in by_normalized:
            return by_normalized[key]
    return None


# ============================================================
# Data model
# ============================================================

def _normalize_numeric(value: Any) -> str:
    """Return a 3-digit zero-padded numeric code as a string, or '000' if unparseable."""
    text = str(value or "").strip()
    if not text:
        return "000"
    # Some exports render numeric codes as floats ("4.0").
    if "." in text:
        text = text.split(".", 1)[0]
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return "000"
    return digits.zfill(3)


def make_active_entry(
    *,
    alpha_2: str,
    alpha_3: str,
    numeric: str,
    name: str,
    status: str,
    independent: bool,
    official_name: str | None = None,
    region: str | None = None,
    subregion: str | None = None,
    intermediate_region: str | None = None,
    note: str | None = None,
    last_verified: str,
) -> dict[str, Any]:
    """Construct one active entry with all schema fields present."""
    return {
        "alpha_2": alpha_2,
        "alpha_3": alpha_3,
        "numeric": numeric,
        "name": name,
        "status": status,
        "independent": independent,
        "official_name": official_name,
        "region": region,
        "subregion": subregion,
        "intermediate_region": intermediate_region,
        "currency_codes": None,
        "calling_codes": None,
        "tlds": None,
        "languages": None,
        "borders": None,
        "note": note,
        "last_verified": last_verified,
        "withdrawal_date": None,
        "replaced_by": None,
    }


def make_withdrawn_entry(
    override: dict[str, Any],
    *,
    last_verified: str,
) -> dict[str, Any]:
    """Construct one withdrawn entry from an exceptions-file record."""
    for required in ("alpha_2", "alpha_3", "numeric", "name", "withdrawal_date"):
        if required not in override:
            raise FatalError(
                f"withdrawn entry missing required field {required!r}: {override!r}"
            )

    return {
        "alpha_2": override["alpha_2"],
        "alpha_3": override["alpha_3"],
        "numeric": _normalize_numeric(override["numeric"]),
        "name": override["name"],
        "status": "withdrawn",
        "independent": bool(override.get("independent", False)),
        "official_name": override.get("official_name"),
        "region": None,
        "subregion": None,
        "intermediate_region": None,
        "currency_codes": None,
        "calling_codes": None,
        "tlds": None,
        "languages": None,
        "borders": None,
        "note": override.get("note"),
        "last_verified": last_verified,
        "withdrawal_date": override["withdrawal_date"],
        "replaced_by": override.get("replaced_by"),
    }


# ============================================================
# IO — CSV and exceptions
# ============================================================

def _detect_delimiter(sample: str) -> str:
    """Return the delimiter the CSV header is using. Prefers comma, falls back to semicolon."""
    # Count occurrences in the first non-empty line.
    first_line = ""
    for line in sample.splitlines():
        if line.strip():
            first_line = line
            break
    if not first_line:
        return ","
    commas = first_line.count(",")
    semis = first_line.count(";")
    tabs = first_line.count("\t")
    # Pick the delimiter that appears most.
    best = max((commas, ","), (semis, ";"), (tabs, "\t"))
    return best[1] if best[0] > 0 else ","


def read_m49_csv(path: Path) -> list[dict[str, Any]]:
    """Read the UN M49 CSV and return country-level rows only (no region aggregates)."""
    if not path.exists():
        raise FatalError(f"UN M49 CSV not found: {path}", code=2)
    if not path.is_file():
        raise FatalError(f"UN M49 path is not a regular file: {path}", code=2)

    try:
        sample = path.read_text(encoding="utf-8-sig")[:8192]
    except OSError as exc:
        raise FatalError(f"cannot read UN M49 CSV: {exc}", code=2) from exc

    if sample.lstrip().startswith("<"):
        raise FatalError(
            f"{path}: looks like HTML, not CSV.\n"
            f"  The UN M49 'Download' button is JavaScript-triggered; curl on the\n"
            f"  overview page returns the HTML page. Open the page in a browser,\n"
            f"  click Download → CSV, and use the file that arrives in your\n"
            f"  Downloads folder.",
            code=1,
        )

    delimiter = _detect_delimiter(sample)
    info(f"  detected delimiter: {delimiter!r}")

    try:
        handle = path.open(encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise FatalError(f"cannot open UN M49 CSV: {exc}", code=2) from exc

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    skipped_no_alpha2 = 0

    with handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise FatalError(f"{path}: empty CSV (no header row)", code=1)
        cols = {name: resolve_required_column(reader.fieldnames, name)
                for name in REQUIRED_COLUMN_ALIASES}
        optional_cols = {name: resolve_optional_column(reader.fieldnames, name)
                         for name in OPTIONAL_COLUMN_ALIASES}

        for lineno, raw in enumerate(reader, start=2):
            alpha_2 = (raw.get(cols["alpha_2"]) or "").strip().upper()
            if not alpha_2:
                skipped_no_alpha2 += 1
                continue
            if alpha_2 in seen:
                duplicates.append(alpha_2)
                continue
            seen.add(alpha_2)

            def get_opt(internal: str) -> str | None:
                col = optional_cols[internal]
                if col is None:
                    return None
                value = (raw.get(col) or "").strip()
                return value or None

            rows.append({
                "alpha_2": alpha_2,
                "alpha_3": (raw.get(cols["alpha_3"]) or "").strip().upper(),
                "numeric": _normalize_numeric(raw.get(cols["numeric"])),
                "name": (raw.get(cols["name"]) or "").strip(),
                "region": get_opt("region"),
                "subregion": get_opt("subregion"),
                "intermediate_region": get_opt("intermediate_region"),
                "_lineno": lineno,
            })

    if duplicates:
        warn(f"skipped {len(duplicates)} duplicate alpha-2 rows: "
             f"{sorted(set(duplicates))[:10]}"
             f"{'...' if len(set(duplicates)) > 10 else ''}")
    if skipped_no_alpha2:
        info(f"skipped {skipped_no_alpha2} rows with empty alpha-2 "
             f"(region aggregates)")

    return rows


def load_exceptions(path: Path) -> dict[str, Any]:
    """Load the exceptions file. Missing file → empty exceptions + warning."""
    default: dict[str, Any] = {
        "officially_assigned": {},
        "exceptionally_reserved": {},
        "user_assigned": {},
        "withdrawn": [],
    }

    if not path.exists():
        warn(f"exceptions file not found: {path} (continuing with empty exceptions)")
        return default

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{path}: invalid JSON: {exc}", code=1) from exc
    except OSError as exc:
        raise FatalError(f"cannot read exceptions file: {exc}", code=2) from exc

    if not isinstance(data, dict):
        raise FatalError(f"{path}: top-level value must be an object", code=1)

    for key in ("officially_assigned", "exceptionally_reserved", "user_assigned"):
        if key not in data:
            data[key] = {}
        elif not isinstance(data[key], dict):
            raise FatalError(f"{path}: {key!r} must be an object", code=1)

    if "withdrawn" not in data:
        data["withdrawn"] = []
    elif not isinstance(data["withdrawn"], list):
        raise FatalError(f"{path}: 'withdrawn' must be an array", code=1)

    return data


# ============================================================
# Transformation
# ============================================================

def build_active_entries(
    m49_rows: list[dict[str, Any]],
    exceptions: dict[str, Any],
    *,
    last_verified: str,
) -> list[dict[str, Any]]:
    """Merge M49 rows with exceptions to produce the active array."""
    active: list[dict[str, Any]] = []
    overrides = exceptions.get("officially_assigned", {})

    seen_in_m49: set[str] = set()

    for row in m49_rows:
        a2 = row["alpha_2"]
        seen_in_m49.add(a2)
        ov = overrides.get(a2, {}) or {}
        active.append(make_active_entry(
            alpha_2=a2,
            alpha_3=row["alpha_3"],
            numeric=row["numeric"],
            name=ov.get("name", row["name"]),
            status="officially-assigned",
            independent=bool(ov.get("independent", False)),
            official_name=ov.get("official_name"),
            region=row.get("region"),
            subregion=row.get("subregion"),
            intermediate_region=row.get("intermediate_region"),
            note=ov.get("note"),
            last_verified=last_verified,
        ))

    # Additions: officially-assigned overrides whose alpha_2 is not in the
    # M49 export (e.g. TW, which ISO assigns but the UN omits). These must
    # be complete — alpha_3, numeric, and name are required.
    for a2, ov in overrides.items():
        if a2 in seen_in_m49:
            continue
        missing = [k for k in ("alpha_3", "numeric", "name") if not ov.get(k)]
        if missing:
            raise FatalError(
                f"officially-assigned override for {a2} is an addition "
                f"(not present in M49) but is missing: {', '.join(missing)}",
                code=1,
            )
        info(f"  adding {a2} from exceptions (not in M49)", quiet=True)
        active.append(make_active_entry(
            alpha_2=a2.upper(),
            alpha_3=ov["alpha_3"],
            numeric=_normalize_numeric(ov["numeric"]),
            name=ov["name"],
            status="officially-assigned",
            independent=bool(ov.get("independent", False)),
            official_name=ov.get("official_name"),
            region=ov.get("region"),
            subregion=ov.get("subregion"),
            intermediate_region=ov.get("intermediate_region"),
            note=ov.get("note"),
            last_verified=last_verified,
        ))

    for a2, ov in exceptions.get("exceptionally_reserved", {}).items():
        active.append(make_active_entry(
            alpha_2=a2.upper(),
            alpha_3=ov["alpha_3"],
            numeric=_normalize_numeric(ov.get("numeric", "000")),
            name=ov["name"],
            status="exceptionally-reserved",
            independent=bool(ov.get("independent", False)),
            official_name=ov.get("official_name"),
            note=ov.get("note"),
            last_verified=last_verified,
        ))

    for a2, ov in exceptions.get("user_assigned", {}).items():
        active.append(make_active_entry(
            alpha_2=a2.upper(),
            alpha_3=ov["alpha_3"],
            numeric=_normalize_numeric(ov.get("numeric", "000")),
            name=ov["name"],
            status="user-assigned",
            independent=bool(ov.get("independent", False)),
            official_name=ov.get("official_name"),
            note=ov.get("note"),
            last_verified=last_verified,
        ))

    active.sort(key=lambda e: e["alpha_2"])
    return active


def build_withdrawn_entries(
    exceptions: dict[str, Any],
    *,
    last_verified: str,
) -> list[dict[str, Any]]:
    entries = [make_withdrawn_entry(ov, last_verified=last_verified)
               for ov in exceptions.get("withdrawn", [])]
    entries.sort(key=lambda e: e["alpha_2"])
    return entries


def build_document(
    active: list[dict[str, Any]],
    withdrawn: list[dict[str, Any]],
    *,
    updated: str,
) -> dict[str, Any]:
    return {
        "meta": {
            "version": REGISTRY_VERSION,
            "updated": updated,
            "source": SOURCE_STRING,
            "schema_version": SCHEMA_VERSION,
            "count_active": len(active),
            "count_withdrawn": len(withdrawn),
        },
        "countries": {
            "active": active,
            "withdrawn": withdrawn,
        },
    }


# ============================================================
# Validation
# ============================================================

def validate_document(doc: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty means OK)."""
    errors: list[str] = []
    active = doc["countries"]["active"]
    withdrawn = doc["countries"]["withdrawn"]

    # Required fields present.
    for section_name, section in (("active", active), ("withdrawn", withdrawn)):
        for i, entry in enumerate(section):
            for field in REQUIRED_FIELDS:
                if field not in entry or entry[field] in (None, ""):
                    errors.append(
                        f"{section_name}[{i}] ({entry.get('alpha_2', '?')}) "
                        f"missing/empty {field!r}"
                    )
            if section_name == "withdrawn" and not entry.get("withdrawal_date"):
                errors.append(
                    f"withdrawn[{i}] ({entry.get('alpha_2', '?')}) "
                    f"missing withdrawal_date"
                )
            if entry.get("status") not in VALID_STATUS:
                errors.append(
                    f"{section_name}[{i}] ({entry.get('alpha_2', '?')}) "
                    f"invalid status {entry.get('status')!r}"
                )
            if section_name == "active" and entry.get("status") not in ACTIVE_STATUSES:
                errors.append(
                    f"active[{i}] ({entry.get('alpha_2', '?')}) "
                    f"must not have status {entry.get('status')!r}"
                )
            if section_name == "withdrawn" and entry.get("status") != "withdrawn":
                errors.append(
                    f"withdrawn[{i}] ({entry.get('alpha_2', '?')}) "
                    f"must have status 'withdrawn', got {entry.get('status')!r}"
                )

    # Unique alpha_2 and alpha_3 within each section.
    for section_name, section in (("active", active), ("withdrawn", withdrawn)):
        for field in ("alpha_2", "alpha_3"):
            codes = [e[field] for e in section]
            dupes = sorted({c for c, n in Counter(codes).items() if n > 1})
            if dupes:
                errors.append(f"{section_name}: duplicate {field}: {dupes}")

    # Pattern checks.
    for section_name, section in (("active", active), ("withdrawn", withdrawn)):
        for entry in section:
            a2 = entry.get("alpha_2", "")
            a3 = entry.get("alpha_3", "")
            num = entry.get("numeric", "")
            if not ALPHA_2_RE.fullmatch(a2):
                errors.append(f"{section_name}: bad alpha_2 {a2!r}")
            if not ALPHA_3_RE.fullmatch(a3):
                errors.append(f"{section_name}: bad alpha_3 {a3!r} (for {a2})")
            if not NUMERIC_RE.fullmatch(num):
                errors.append(f"{section_name}: bad numeric {num!r} (for {a2})")

    # Meta counts match.
    if doc["meta"].get("count_active") != len(active):
        errors.append(
            f"meta.count_active ({doc['meta'].get('count_active')}) "
            f"!= len(active) ({len(active)})"
        )
    if doc["meta"].get("count_withdrawn") != len(withdrawn):
        errors.append(
            f"meta.count_withdrawn ({doc['meta'].get('count_withdrawn')}) "
            f"!= len(withdrawn) ({len(withdrawn)})"
        )

    return errors


def validate_against_schema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    """Validate against a JSON Schema. Returns a list of errors (empty means OK)."""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return [
            "jsonschema is not installed; skipping schema validation "
            "(pip install jsonschema)"
        ]

    if not schema_path.exists():
        return [f"schema file not found: {schema_path}"]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{schema_path}: invalid JSON: {exc}"]

    try:
        validator = jsonschema.Draft7Validator(schema)
    except jsonschema.exceptions.SchemaError as exc:
        return [f"{schema_path}: not a valid draft-07 schema: {exc.message}"]

    out: list[str] = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        out.append(f"{path}: {err.message}")
    return out


# ============================================================
# Output
# ============================================================

def write_json(doc: dict[str, Any], path: Path) -> None:
    """Write the document deterministically: sorted keys, 2-space indent, trailing newline."""
    text = json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def print_summary(doc: dict[str, Any], *, target: int | None) -> None:
    active = doc["countries"]["active"]
    withdrawn = doc["countries"]["withdrawn"]
    by_status = Counter(e["status"] for e in active)

    print("")
    print("=" * 60)
    print("Registry summary")
    print("=" * 60)
    print(f"  version            {doc['meta']['version']}")
    print(f"  updated            {doc['meta']['updated']}")
    print(f"  source             {doc['meta']['source']}")
    print(f"  active total       {len(active)}")
    for status in ("officially-assigned", "user-assigned", "exceptionally-reserved"):
        if by_status[status]:
            print(f"    {status:<30} {by_status[status]}")
    print(f"  withdrawn total    {len(withdrawn)}")
    if target is not None:
        delta = by_status["officially-assigned"] - target
        marker = "OK" if delta == 0 else f"OFF BY {delta:+d}"
        print(f"  expected official  {target} ({marker})")
    print("=" * 60)
    print("")


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_initial_data",
        description=(
            "One-shot importer: produce the first-cut iso3166.json from the "
            "UN M49 CSV plus a hand-maintained exceptions file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "To obtain the UN M49 CSV:\n"
            f"  1. Open {M49_URL}\n"
            "  2. Click 'Download' and choose CSV.\n"
            "  3. Save it locally, e.g. /tmp/un_m49.csv.\n"
        ),
    )
    parser.add_argument(
        "--un-m49", type=Path, required=True, metavar="PATH",
        help="Path to the UN M49 overview CSV.",
    )
    parser.add_argument(
        "--exceptions", type=Path, default=Path("tools/initial_exceptions.json"),
        metavar="PATH",
        help="Path to the hand-maintained exceptions file "
             "(default: tools/initial_exceptions.json).",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("iso3166.json"), metavar="PATH",
        help="Where to write the registry (default: iso3166.json).",
    )
    parser.add_argument(
        "--schema", type=Path, default=None, metavar="PATH",
        help="Optional. Validate the output against this JSON Schema.",
    )
    parser.add_argument(
        "--date", default=None, metavar="YYYY-MM-DD",
        help="Override the 'updated' and 'last_verified' dates. "
             "Defaults to today. Use for reproducibility.",
    )
    parser.add_argument(
        "--strict-count", action="store_true",
        help=f"Fail if the officially-assigned count is not {EXPECTED_OFFICIAL_COUNT}.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Build and validate, but do not write the output file.",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress informational messages. Errors still go to stderr.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    today = args.date or date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
        raise FatalError(f"--date must be YYYY-MM-DD, got {today!r}", code=2)

    info(f"Reading UN M49 CSV: {args.un_m49}", quiet=args.quiet)
    m49_rows = read_m49_csv(args.un_m49)
    info(f"  {len(m49_rows)} country-level rows", quiet=args.quiet)

    info(f"Reading exceptions: {args.exceptions}", quiet=args.quiet)
    exceptions = load_exceptions(args.exceptions)
    info(
        f"  {len(exceptions['officially_assigned'])} officially-assigned overrides, "
        f"{len(exceptions['exceptionally_reserved'])} exceptionally-reserved, "
        f"{len(exceptions['user_assigned'])} user-assigned, "
        f"{len(exceptions['withdrawn'])} withdrawn",
        quiet=args.quiet,
    )

    info("Building entries", quiet=args.quiet)
    active = build_active_entries(m49_rows, exceptions, last_verified=today)
    withdrawn = build_withdrawn_entries(exceptions, last_verified=today)
    doc = build_document(active, withdrawn, updated=today)

    info("Validating structure", quiet=args.quiet)
    structural_errors = validate_document(doc)
    if structural_errors:
        print("error: structural validation failed:", file=sys.stderr)
        for err in structural_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print_summary(doc, target=EXPECTED_OFFICIAL_COUNT)

    if args.strict_count:
        official = sum(1 for e in active if e["status"] == "officially-assigned")
        if official != EXPECTED_OFFICIAL_COUNT:
            raise FatalError(
                f"officially-assigned count is {official}, expected "
                f"{EXPECTED_OFFICIAL_COUNT} (--strict-count)",
                code=1,
            )

    if args.schema is not None:
        info(f"Validating against schema: {args.schema}", quiet=args.quiet)
        schema_errors = validate_against_schema(doc, args.schema)
        real_errors = [e for e in schema_errors if "jsonschema is not installed" not in e]
        if real_errors:
            print("error: schema validation failed:", file=sys.stderr)
            for err in real_errors[:50]:
                print(f"  - {err}", file=sys.stderr)
            if len(real_errors) > 50:
                print(f"  ... and {len(real_errors) - 50} more", file=sys.stderr)
            return 3
        if schema_errors:
            for msg in schema_errors:
                warn(msg)

    if args.dry_run:
        info("--dry-run: not writing output", quiet=args.quiet)
        return 0

    info(f"Writing: {args.out}", quiet=args.quiet)
    try:
        write_json(doc, args.out)
    except OSError as exc:
        raise FatalError(f"cannot write {args.out}: {exc}", code=2) from exc

    info(f"Done. Wrote {args.out}", quiet=args.quiet)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
