#!/usr/bin/env python3
"""
tools/export_csv.py

Generate four delimited exports from iso3166.json:
    iso3166.csv            RFC 4180, comma-delimited, no BOM
    iso3166.excel.csv      comma-delimited, UTF-8 BOM (Windows Excel)
    iso3166.european.csv   semicolon-delimited, no BOM (FR/DE/ES/IT Excel)
    iso3166.tsv            tab-delimited, no BOM

All four have the same 19 columns in the same order. List fields
(calling_codes, tlds, languages, borders, currency_codes, replaced_by)
are pipe-delimited in a single cell. Empty lists render as empty cells.

No comment header: a leading comment would break pandas.read_csv without
skiprows and would violate RFC 4180. Version info lives in the JSON.

Deterministic output: rows sorted by alpha_2, LF line endings, UTF-8,
minimal quoting.

Usage:
    python3 tools/export_csv.py
    python3 tools/export_csv.py --check
    python3 tools/export_csv.py --variant csv
    python3 tools/export_csv.py --quiet

Exit codes:
    0  Success (write or --check matched)
    1  --check found a stale artifact
    2  Usage error
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


# ============================================================
# Constants
# ============================================================

VARIANTS = ("csv", "excel", "european", "tsv")

OUTPUT_NAME = {
    "csv":      "iso3166.csv",
    "excel":    "iso3166.excel.csv",
    "european": "iso3166.european.csv",
    "tsv":      "iso3166.tsv",
}

VARIANT_OPTS = {
    "csv":      {"delimiter": ",", "bom": False},
    "excel":    {"delimiter": ",", "bom": True},
    "european": {"delimiter": ";", "bom": False},
    "tsv":      {"delimiter": "\t", "bom": False},
}

LIST_DELIM = "|"

COLUMNS = (
    "alpha_2",
    "alpha_3",
    "numeric",
    "name",
    "status",
    "independent",
    "official_name",
    "region",
    "subregion",
    "intermediate_region",
    "currency_codes",
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


# ============================================================
# Cell rendering
# ============================================================

def render_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        if not value:
            return ""
        return LIST_DELIM.join(str(x) for x in value)
    return str(value)


def render_row(entry: dict[str, Any]) -> list[str]:
    return [render_cell(entry.get(col)) for col in COLUMNS]


# ============================================================
# Generation
# ============================================================

def generate(variant: str, reg: dict[str, Any]) -> str:
    opts = VARIANT_OPTS[variant]
    delimiter = opts["delimiter"]

    buf = io.StringIO(newline="")
    writer = csv.writer(
        buf,
        delimiter=delimiter,
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    writer.writerow(COLUMNS)
    for entry in all_entries(reg):
        writer.writerow(render_row(entry))

    body = buf.getvalue()
    if opts["bom"]:
        return "\ufeff" + body
    return body


# ============================================================
# IO
# ============================================================

def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
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
    return path.read_text(encoding="utf-8") == expected


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="export_csv",
        description="Generate CSV/TSV exports from iso3166.json.",
    )
    p.add_argument("--registry", type=Path, default=Path("iso3166.json"),
                   help="Path to the registry (default: iso3166.json).")
    p.add_argument("--variant", choices=VARIANTS, default=None,
                   help="Only generate the named variant.")
    p.add_argument("--check", action="store_true",
                   help="Verify the committed artifacts are up to date.")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress informational messages.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    reg = load_registry(args.registry)
    variants = [args.variant] if args.variant else list(VARIANTS)

    stale: list[str] = []
    for v in variants:
        content = generate(v, reg)
        path = Path(OUTPUT_NAME[v])
        if args.check:
            if check_file(path, content):
                info(f"  {path}: OK", quiet=args.quiet)
            else:
                print(f"  {path}: STALE", file=sys.stderr)
                stale.append(str(path))
        else:
            write_atomic(path, content)
            info(f"  wrote {path} ({len(content):,} chars)", quiet=args.quiet)

    if args.check and stale:
        print(f"\n{len(stale)} stale artifact(s). Regenerate with:", file=sys.stderr)
        print("  python3 tools/export_csv.py", file=sys.stderr)
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
