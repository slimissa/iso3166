#!/usr/bin/env python3
"""
tools/export_aggregated.py

Generate the AGGREGATED layer (countries_by_region.parquet) from the 
CURATED layer (iso3166.parquet).

Architecture Rule: The AGGREGATED layer must only read from the CURATED 
layer. This script must never read the RAW layer (iso3166.json) and must 
not import the `json` module.

Usage:
    python3 tools/export_aggregated.py
    python3 tools/export_aggregated.py --check
    python3 tools/export_aggregated.py --input IN.parquet --output OUT.parquet

By default the input and output are resolved against the repository root,
not the current directory, so the tool works from any directory. --input
and --output override them; the tests use them to run against a temporary
directory without touching the committed files.

Exit codes:
    0  Success (write or --check matched)
    1  --check found a stale artifact
    2  Usage error (missing input or malformed schema)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# No iso3166.json fail-fast check here, unlike the other tools:
# tests/test_architecture.py forbids this file from naming the RAW layer.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURATED_INPUT = PROJECT_ROOT / "iso3166.parquet"
AGGREGATED_OUTPUT = PROJECT_ROOT / "countries_by_region.parquet"

REQUIRED_COLUMNS = {"alpha_2", "region", "subregion", "independent"}


def _shown(path: Path) -> str:
    """A path for messages: relative to the repository root when inside it."""
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def build_aggregated(input_path: Path = CURATED_INPUT) -> pd.DataFrame:
    """Read the CURATED layer and build the AGGREGATED dataframe."""
    if not input_path.exists():
        print(
            f"error: {_shown(input_path)} not found. Run tools/export_parquet.py first.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Read CURATED layer
    try:
        df = pd.read_parquet(input_path)
    except Exception as exc:
        print(f"error: failed to read {_shown(input_path)}: {exc}", file=sys.stderr)
        sys.exit(2)

    # Validate CURATED schema
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        print(
            f"error: {_shown(input_path)} is missing required columns: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(2)

    # Build AGGREGATED layer
    # groupby with dropna=False ensures null subregions (e.g., Antarctica) are kept
    agg_df = (
        df.groupby(["region", "subregion"], dropna=False)
        .agg(
            country_count=("alpha_2", "count"),
            independent_count=("independent", "sum"),
        )
        .reset_index()
    )

    # Ensure deterministic types (sum of boolean yields int, but we enforce it)
    agg_df["country_count"] = agg_df["country_count"].astype("int64")
    agg_df["independent_count"] = agg_df["independent_count"].astype("int64")

    # Sort deterministically: by region, then subregion.
    # na_position="first" handles regions with null subregions consistently.
    agg_df = agg_df.sort_values(
        by=["region", "subregion"], na_position="first"
    ).reset_index(drop=True)

    return agg_df


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the AGGREGATED layer.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artifact matches a fresh build.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress success output.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help=f"CURATED parquet to read (default: {_shown(CURATED_INPUT)} in the repository root).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"AGGREGATED parquet to write or check (default: {_shown(AGGREGATED_OUTPUT)} in the repository root).",
    )
    args = parser.parse_args()

    input_path = args.input or CURATED_INPUT
    output_path = args.output or AGGREGATED_OUTPUT
    new_df = build_aggregated(input_path)

    if args.check:
        if not output_path.exists():
            print(f"  {_shown(output_path)}: STALE (missing)", file=sys.stderr)
            return 1

        try:
            existing_df = pd.read_parquet(output_path)
            # assert_frame_equal checks column names, types, and values.
            # We sort the existing_df just in case to ensure logical equality.
            existing_df = existing_df.sort_values(
                by=["region", "subregion"], na_position="first"
            ).reset_index(drop=True)
            
            pd.testing.assert_frame_equal(new_df, existing_df, check_dtype=True)
            
            if not args.quiet:
                print(f"  {_shown(output_path)}: OK")
            return 0
        except AssertionError as exc:
            print(f"  {_shown(output_path)}: STALE (content mismatch)", file=sys.stderr)
            print(f"\n{exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"  {_shown(output_path)}: STALE (read error: {exc})", file=sys.stderr)
            return 1

    # Write mode
    new_df.to_parquet(output_path, index=False)
    if not args.quiet:
        print(
            f"  wrote {_shown(output_path)} "
            f"({len(new_df)} rows, "
            f"{new_df['country_count'].sum()} countries)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())