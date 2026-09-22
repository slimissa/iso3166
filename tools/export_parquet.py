#!/usr/bin/env python3
"""
tools/export_parquet.py

Generate a single Parquet export from iso3166.json:
    iso3166.parquet

Typed columns (via pyarrow):
    alpha_2, alpha_3, numeric_code (int16), name, status, independent (bool),
    official_name, region, subregion, intermediate_region,
    currency_codes (list<string>), calling_codes (list<string>),
    tlds (list<string>), languages (list<string>), borders (list<string>),
    note, last_verified, withdrawal_date, replaced_by (list<string>)

Footer metadata carries iso3166.version, iso3166.updated,
iso3166.schema_version.

Depends on pyarrow. If pyarrow is not installed, the tool prints a
warning and exits 0 (advisory). Phase 7's CI installs pyarrow, so the
artifact is regenerated and checked there.

Deterministic: rows sorted by alpha_2. Parquet files are not guaranteed
byte-identical across runs (file metadata includes row group statistics
that are stable, but the writer may embed timestamps). The --check mode
therefore compares logical content, not bytes.

Usage:
    python3 tools/export_parquet.py
    python3 tools/export_parquet.py --check
    python3 tools/export_parquet.py --quiet

Exit codes:
    0  Success (write, --check matched, or pyarrow absent)
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


OUTPUT = Path("iso3166.parquet")

COLUMNS = (
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


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def info(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, file=sys.stderr)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


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


def to_columns(reg: dict[str, Any]) -> dict[str, list[Any]]:
    """Return column-oriented data ready for pyarrow.Table.from_pydict."""
    entries = all_entries(reg)
    cols: dict[str, list[Any]] = {c: [] for c in COLUMNS}

    for e in entries:
        for c in COLUMNS:
            json_col = "numeric" if c == "numeric_code" else c
            v = e.get(json_col)

            if c == "numeric_code":
                # Convert "840" -> 840. Value 000 is valid; store as 0.
                try:
                    v = int(v) if v is not None else None
                except (TypeError, ValueError):
                    v = None

            cols[c].append(v)

    return cols


def build_table(reg: dict[str, Any]):
    import pyarrow as pa  # type: ignore

    cols = to_columns(reg)

    fields = [
        pa.field("alpha_2",             pa.string(),  nullable=False),
        pa.field("alpha_3",             pa.string(),  nullable=False),
        pa.field("numeric_code",        pa.int16(),   nullable=False),
        pa.field("name",                pa.string(),  nullable=False),
        pa.field("status",              pa.string(),  nullable=False),
        pa.field("independent",         pa.bool_(),   nullable=False),
        pa.field("official_name",       pa.string()),
        pa.field("region",              pa.string()),
        pa.field("subregion",           pa.string()),
        pa.field("intermediate_region", pa.string()),
        pa.field("currency_codes",      pa.list_(pa.string())),
        pa.field("calling_codes",       pa.list_(pa.string())),
        pa.field("tlds",                pa.list_(pa.string())),
        pa.field("languages",           pa.list_(pa.string())),
        pa.field("borders",             pa.list_(pa.string())),
        pa.field("note",                pa.string()),
        pa.field("last_verified",       pa.string()),
        pa.field("withdrawal_date",     pa.string()),
        pa.field("replaced_by",         pa.list_(pa.string())),
    ]

    schema = pa.schema(fields)

    meta = reg.get("meta", {})
    schema = schema.with_metadata({
        b"iso3166.version":        str(meta.get("version", "")).encode(),
        b"iso3166.updated":        str(meta.get("updated", "")).encode(),
        b"iso3166.schema_version": str(meta.get("schema_version", "")).encode(),
        b"iso3166.generator":      b"tools/export_parquet.py",
    })

    arrays = []
    for f in fields:
        arrays.append(pa.array(cols[f.name], type=f.type))

    return pa.Table.from_arrays(arrays, schema=schema)


def write_parquet(reg: dict[str, Any], path: Path) -> None:
    import pyarrow.parquet as pq  # type: ignore

    table = build_table(reg)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    os.close(fd)
    try:
        pq.write_table(table, tmp, compression="snappy")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def check_parquet(reg: dict[str, Any], path: Path) -> bool:
    """Compare the on-disk Parquet's logical content to a fresh build."""
    if not path.exists():
        return False
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:
        return False

    try:
        existing = pq.read_table(path)
    except Exception:
        return False

    fresh = build_table(reg)

    # Compare schema (field names + types, ignoring metadata).
    if existing.schema.remove_metadata() != fresh.schema.remove_metadata():
        return False

    # Compare columns as Python lists.
    for name in [f.name for f in fresh.schema]:
        if existing.column(name).to_pylist() != fresh.column(name).to_pylist():
            return False
    return True


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="export_parquet",
        description="Generate a Parquet export from iso3166.json.",
    )
    p.add_argument("--registry", type=Path, default=Path("iso3166.json"))
    p.add_argument("--check", action="store_true")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        import pyarrow  # noqa: F401  # type: ignore
    except ImportError:
        warn(
            "pyarrow is not installed; skipping Parquet generation. "
            "Install with: pip install pyarrow"
        )
        return 0

    reg = load_registry(args.registry)

    if args.check:
        if check_parquet(reg, OUTPUT):
            info(f"  {OUTPUT}: OK", quiet=args.quiet)
            return 0
        print(f"  {OUTPUT}: STALE", file=sys.stderr)
        print("Regenerate with: python3 tools/export_parquet.py", file=sys.stderr)
        return 1

    write_parquet(reg, OUTPUT)
    size = OUTPUT.stat().st_size
    info(f"  wrote {OUTPUT} ({size:,} bytes)", quiet=args.quiet)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
