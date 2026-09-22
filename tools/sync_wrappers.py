#!/usr/bin/env python3
"""
tools/sync_wrappers.py

Copy iso3166.json into the wrapper directories that embed it:

    wrappers/go/iso3166.json
    wrappers/rust/iso3166.json

If a wrapper directory does not exist, this is a no-op for that
wrapper (with a warning). Phase 6 creates the wrapper directories;
this script is a no-op until then.

Deterministic: a straight byte copy of iso3166.json.

Usage:
    python3 tools/sync_wrappers.py
    python3 tools/sync_wrappers.py --check
    python3 tools/sync_wrappers.py --quiet

Exit codes:
    0  Success (copy done, --check matched, or no-op)
    1  --check found a stale copy
    2  Usage error
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


SOURCE = Path("iso3166.json")

TARGETS = (
    Path("wrappers/python/iso3166/iso3166.json"),
    Path("wrappers/javascript/iso3166.json"),
    Path("wrappers/go/iso3166.json"),
    Path("wrappers/rust/iso3166.json"),
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sync_wrappers",
        description="Copy iso3166.json into Go and Rust wrapper directories.",
    )
    p.add_argument("--check", action="store_true",
                   help="Verify copies are current. Exits 1 if stale.")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not SOURCE.exists():
        raise FatalError(f"source not found: {SOURCE}", code=2)

    stale: list[str] = []
    any_target = False

    for target in TARGETS:
        parent = target.parent
        if not parent.exists():
            warn(f"{parent} does not exist; skipping {target}")
            continue

        any_target = True

        if args.check:
            if target.exists() and filecmp.cmp(SOURCE, target, shallow=False):
                info(f"  {target}: OK", quiet=args.quiet)
            else:
                print(f"  {target}: STALE", file=sys.stderr)
                stale.append(str(target))
        else:
            shutil.copy2(SOURCE, target)
            info(f"  wrote {target}", quiet=args.quiet)

    if not any_target and not args.check:
        info(
            "no wrapper directories exist yet; nothing to sync. "
            "Phase 6 creates them.",
            quiet=args.quiet,
        )
        return 0

    if args.check and stale:
        print(f"\n{len(stale)} stale copy(ies). Regenerate with:", file=sys.stderr)
        print("  python3 tools/sync_wrappers.py", file=sys.stderr)
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
