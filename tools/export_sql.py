#!/usr/bin/env python3
"""
tools/export_sql.py

Generate four SQL exports from iso3166.json:
    iso3166.sql              ANSI SQL-92
    iso3166.postgresql.sql   PostgreSQL 12+
    iso3166.mysql.sql        MySQL 8+ / MariaDB 10.4+
    iso3166.sqlite.sql       SQLite 3.37+

Two tables:
    countries            one row per entry (active + withdrawn)
    country_currencies   join table (country_alpha_2, currency_code)

All list fields are pipe-delimited in a TEXT column, except currency_codes,
which lives in the join table. Pipe (|) is chosen because it does not
appear in any ISO 3166 or ISO 4217 code.

Deterministic output: sorted rows, LF line endings, UTF-8, no trailing
whitespace. Two runs on the same input produce byte-identical files.

Usage:
    python3 tools/export_sql.py                 # write all four
    python3 tools/export_sql.py --check         # verify committed artifacts
    python3 tools/export_sql.py --dialect ansi  # write only one
    python3 tools/export_sql.py --quiet

Exit codes:
    0  Success (write or --check matched)
    1  --check found a stale artifact
    2  Usage error
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


# ============================================================
# Constants
# ============================================================

DIALECTS = ("ansi", "postgresql", "mysql", "sqlite")

OUTPUT_NAME = {
    "ansi":       "iso3166.sql",
    "postgresql": "iso3166.postgresql.sql",
    "mysql":      "iso3166.mysql.sql",
    "sqlite":     "iso3166.sqlite.sql",
}

LIST_DELIM = "|"

# Column order, matching the countries table.
COUNTRY_COLUMNS = (
    "alpha_2",
    "alpha_3",
    "numeric_code",
    "name",
    "status",
    "independent",
    "official_name",
    "region",
    "subregion",
    "intermediate_region",
    "calling_codes",
    "tlds",
    "languages",
    "borders",
    "note",
    "last_verified",
    "withdrawal_date",
    "replaced_by",
)


# ============================================================
# Diagnostics
# ============================================================

class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def info(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, file=sys.stderr)


# ============================================================
# Data
# ============================================================

def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FatalError(f"registry not found: {path}", code=2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{path}: invalid JSON: {exc}", code=2) from exc


def all_entries(reg: dict[str, Any]) -> list[dict[str, Any]]:
    countries = reg.get("countries", {})
    entries = list(countries.get("active", [])) + list(countries.get("withdrawn", []))
    entries.sort(key=lambda e: e["alpha_2"])
    return entries


def currency_pairs(reg: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for e in all_entries(reg):
        a2 = e["alpha_2"]
        for c in e.get("currency_codes") or []:
            pairs.append((a2, c))
    pairs.sort()
    return pairs


# ============================================================
# Cell rendering
# ============================================================

def render_list_in_cell(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        return None
    return LIST_DELIM.join(str(x) for x in value)


def sql_quote(value: Any, *, dialect: str, col: str) -> str:
    """Render a Python value as a SQL literal (or NULL)."""
    if value is None:
        return "NULL"

    if col == "independent":
        if not isinstance(value, bool):
            raise FatalError(f"independent must be bool, got {type(value)}", code=1)
        if dialect in ("ansi", "postgresql"):
            return "TRUE" if value else "FALSE"
        return "1" if value else "0"

    if isinstance(value, str):
        # Single-quote escaping: double the quote.
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    if isinstance(value, bool):
        if dialect in ("ansi", "postgresql"):
            return "TRUE" if value else "FALSE"
        return "1" if value else "0"

    if isinstance(value, int):
        return str(value)

    raise FatalError(f"unsupported cell type {type(value)} for column {col}", code=1)


def country_row(entry: dict[str, Any], *, dialect: str) -> list[str]:
    """Return the SQL literal for each column of the countries table."""
    row: list[str] = []
    for col in COUNTRY_COLUMNS:
        json_col = "numeric" if col == "numeric_code" else col
        value = entry.get(json_col)

        if col in ("calling_codes", "tlds", "languages", "borders", "replaced_by"):
            value = render_list_in_cell(value)
        elif col == "currency_codes":
            # handled by join table; not a column here
            continue

        row.append(sql_quote(value, dialect=dialect, col=col))
    return row


# ============================================================
# Dialect-specific type maps
# ============================================================

def country_types(dialect: str) -> dict[str, str]:
    base = {
        "alpha_2":             "CHAR(2)      NOT NULL",
        "alpha_3":             "CHAR(3)      NOT NULL",
        "numeric_code":        "CHAR(3)      NOT NULL",
        "name":                "VARCHAR(255) NOT NULL",
        "status":              "VARCHAR(30)  NOT NULL",
        "official_name":       "VARCHAR(255)",
        "region":              "VARCHAR(50)",
        "subregion":           "VARCHAR(80)",
        "intermediate_region": "VARCHAR(80)",
        "calling_codes":       "VARCHAR(120)",
        "tlds":                "VARCHAR(120)",
        "languages":           "VARCHAR(80)",
        "borders":             "VARCHAR(160)",
        "note":                "TEXT",
        "last_verified":       "CHAR(10)",
        "withdrawal_date":     "CHAR(10)",
        "replaced_by":         "VARCHAR(80)",
    }

    if dialect in ("ansi", "postgresql"):
        types = dict(base)
        types["independent"] = "BOOLEAN      NOT NULL"
        return types

    if dialect == "mysql":
        types = dict(base)
        for k, v in list(types.items()):
            types[k] = v.replace("VARCHAR(255)", "VARCHAR(255)")
        types["independent"] = "TINYINT(1)   NOT NULL"
        return types

    if dialect == "sqlite":
        # SQLite has dynamic typing; declare minimal, use TEXT/INTEGER.
        types = {k: "TEXT" for k in base}
        types["independent"] = "INTEGER      NOT NULL"
        return types

    raise FatalError(f"unknown dialect: {dialect}", code=2)


def currency_types(dialect: str) -> tuple[str, str]:
    if dialect in ("ansi", "postgresql", "mysql"):
        return ("CHAR(2) NOT NULL", "CHAR(3) NOT NULL")
    if dialect == "sqlite":
        return ("TEXT NOT NULL", "TEXT NOT NULL")
    raise FatalError(f"unknown dialect: {dialect}", code=2)


# ============================================================
# SQL generation
# ============================================================

def header(dialect: str, reg: dict[str, Any]) -> str:
    meta = reg.get("meta", {})
    name = OUTPUT_NAME[dialect]
    label = {
        "ansi":       "ANSI SQL-92 (portable)",
        "postgresql": "PostgreSQL 12+",
        "mysql":      "MySQL 8+ / MariaDB 10.4+",
        "sqlite":     "SQLite 3.37+",
    }[dialect]
    return (
        f"-- {name} — {label}\n"
        f"-- Generated by tools/export_sql.py from iso3166.json.\n"
        f"-- Do not edit by hand. Regenerate with:\n"
        f"--   python3 tools/export_sql.py\n"
        f"-- Registry version: {meta.get('version', '?')}\n"
        f"-- Registry updated: {meta.get('updated', '?')}\n"
        f"--\n"
        f"-- Two tables:\n"
        f"--   countries            one row per entry (active + withdrawn)\n"
        f"--   country_currencies   join table (country_alpha_2, currency_code)\n"
        f"--\n"
        f"-- List fields (calling_codes, tlds, languages, borders, replaced_by)\n"
        f"-- are pipe-delimited ('{LIST_DELIM}') text. NULL when absent.\n"
        f"--\n"
        f"\n"
    )


def generate(dialect: str, reg: dict[str, Any]) -> str:
    parts: list[str] = [header(dialect, reg)]

    # --- DROP (idempotent) ---
    if dialect == "mysql":
        parts.append("SET FOREIGN_KEY_CHECKS = 0;\n\n")
    parts.append("DROP TABLE IF EXISTS country_currencies;\n")
    parts.append("DROP TABLE IF EXISTS countries;\n")
    if dialect == "mysql":
        parts.append("SET FOREIGN_KEY_CHECKS = 1;\n")
    parts.append("\n")

    # --- CREATE countries ---
    types = country_types(dialect)
    parts.append("CREATE TABLE countries (\n")
    lines = []
    for col in COUNTRY_COLUMNS:
        lines.append(f"    {col:<20} {types[col]}")
    # Composite primary key: alpha_2 alone is not unique because ISO
    # reassigns codes. AI and SK each appear twice (active and withdrawn),
    # so the primary key must be (alpha_2, status).
    lines.append("    PRIMARY KEY (alpha_2, status)")
    parts.append(",\n".join(lines))
    parts.append("\n)")
    if dialect == "mysql":
        parts.append(" ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    parts.append(";\n\n")

    # --- CREATE country_currencies ---
    cc_a2, cc_curr = currency_types(dialect)
    parts.append("CREATE TABLE country_currencies (\n")
    parts.append(f"    country_alpha_2 {cc_a2},\n")
    parts.append(f"    currency_code   {cc_curr},\n")
    parts.append("    PRIMARY KEY (country_alpha_2, currency_code)\n")
    # No FK to countries(alpha_2): alpha_2 is not unique on its own
    # because of reassigned codes (AI, SK). A currency code refers to
    # the country's currently-active entry. Consumers joining should
    # filter on status = 'officially-assigned' or 'user-assigned' or
    # 'exceptionally-reserved' as appropriate.
    parts.append(")")
    if dialect == "mysql":
        parts.append(" ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    parts.append(";\n\n")

    # --- INSERT countries ---
    parts.append("-- countries\n")
    cols = ", ".join(COUNTRY_COLUMNS)
    for entry in all_entries(reg):
        row = country_row(entry, dialect=dialect)
        parts.append(f"INSERT INTO countries ({cols}) VALUES ({', '.join(row)});\n")

    parts.append("\n")

    # --- INSERT country_currencies ---
    parts.append("-- country_currencies\n")
    for a2, curr in currency_pairs(reg):
        parts.append(
            f"INSERT INTO country_currencies (country_alpha_2, currency_code) "
            f"VALUES ('{a2}', '{curr}');\n"
        )

    return "".join(parts)


# ============================================================
# IO
# ============================================================

def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def check_file(path: Path, expected: str) -> bool:
    if not path.exists():
        return False
    actual = path.read_text(encoding="utf-8")
    return actual == expected


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="export_sql",
        description="Generate SQL exports from iso3166.json.",
    )
    p.add_argument("--registry", type=Path, default=Path("iso3166.json"),
                   help="Path to the registry (default: iso3166.json).")
    p.add_argument("--dialect", choices=DIALECTS, default=None,
                   help="Only generate the named dialect.")
    p.add_argument("--check", action="store_true",
                   help="Verify the committed artifacts are up to date. "
                        "Exits 1 if any is stale.")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress informational messages.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    reg = load_registry(args.registry)
    dialects = [args.dialect] if args.dialect else list(DIALECTS)

    stale: list[str] = []
    for d in dialects:
        content = generate(d, reg)
        path = Path(OUTPUT_NAME[d])
        if args.check:
            if check_file(path, content):
                info(f"  {path}: OK", quiet=args.quiet)
            else:
                print(f"  {path}: STALE", file=sys.stderr)
                stale.append(str(path))
        else:
            write_atomic(path, content)
            info(f"  wrote {path} ({len(content):,} bytes)", quiet=args.quiet)

    if args.check and stale:
        print(f"\n{len(stale)} stale artifact(s). Regenerate with:", file=sys.stderr)
        print("  python3 tools/export_sql.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
