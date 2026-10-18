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

CURATED_INPUT = Path("iso3166.parquet")
AGGREGATED_OUTPUT = Path("countries_by_region.parquet")

REQUIRED_COLUMNS = {"alpha_2", "region", "subregion", "independent"}


def build_aggregated() -> pd.DataFrame:
    """Read the CURATED layer and build the AGGREGATED dataframe."""
    if not CURATED_INPUT.exists():
        print(
            f"error: {CURATED_INPUT} not found. Run tools/export_parquet.py first.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Read CURATED layer
    try:
        df = pd.read_parquet(CURATED_INPUT)
    except Exception as exc:
        print(f"error: failed to read {CURATED_INPUT}: {exc}", file=sys.stderr)
        sys.exit(2)

    # Validate CURATED schema
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        print(
            f"error: {CURATED_INPUT} is missing required columns: {', '.join(missing)}",
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
    args = parser.parse_args()

    new_df = build_aggregated()

    if args.check:
        if not AGGREGATED_OUTPUT.exists():
            print(f"  {AGGREGATED_OUTPUT}: STALE (missing)", file=sys.stderr)
            return 1

        try:
            existing_df = pd.read_parquet(AGGREGATED_OUTPUT)
            # assert_frame_equal checks column names, types, and values.
            # We sort the existing_df just in case to ensure logical equality.
            existing_df = existing_df.sort_values(
                by=["region", "subregion"], na_position="first"
            ).reset_index(drop=True)
            
            pd.testing.assert_frame_equal(new_df, existing_df, check_dtype=True)
            
            if not args.quiet:
                print(f"  {AGGREGATED_OUTPUT}: OK")
            return 0
        except AssertionError as exc:
            print(f"  {AGGREGATED_OUTPUT}: STALE (content mismatch)", file=sys.stderr)
            print(f"\n{exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"  {AGGREGATED_OUTPUT}: STALE (read error: {exc})", file=sys.stderr)
            return 1

    # Write mode
    new_df.to_parquet(AGGREGATED_OUTPUT, index=False)
    if not args.quiet:
        print(
            f"  wrote {AGGREGATED_OUTPUT} "
            f"({len(new_df)} rows, "
            f"{new_df['country_count'].sum()} countries)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())