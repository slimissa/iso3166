#!/usr/bin/env python3
"""
tools/check_version_consistency.py

Verify that the five version references in this repository agree.

Sources checked:
    1. VERSION                                   (file content)
    2. iso3166.json -> meta.version              (registry data)
    3. CHANGELOG.md -> top [x.y.z] heading       (release notes)
    4. README.md -> "Status: v0.X.Y" (optional)  (human-facing)
    5. iso3166.parquet -> iso3166.version        (artifact metadata)

Pre-release exception
---------------------
Before the first tagged release, VERSION is 0.x.y and the CHANGELOG's
top heading is [Unreleased]. This is the correct state and would
otherwise fail the check. Rule:

    if version < 1.0.0: [Unreleased] is accepted for CHANGELOG
    else:               CHANGELOG top heading must equal version

The rule is documented here so that it is a decision, not an accident.

The README check is best-effort: if no version is stated in the README,
the check is skipped with a note, because a README is allowed to omit
the version (the badge is optional at this stage).

The Parquet check is skipped if the file does not exist or pyarrow is
not installed; a note records the skip.

Usage:
    python3 tools/check_version_consistency.py
    python3 tools/check_version_consistency.py --json

Exit codes:
    0  All available sources agree.
    1  Discrepancy found.
    2  A required source (VERSION, iso3166.json) is missing or invalid.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


VERSION_FILE = Path("VERSION")
REGISTRY = Path("iso3166.json")
CHANGELOG = Path("CHANGELOG.md")
README = Path("README.md")
PARQUET = Path("iso3166.parquet")

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
CHANGELOG_HEADING_RE = re.compile(r"^## \[([0-9]+\.[0-9]+\.[0-9]+|Unreleased)\]", re.MULTILINE)
README_STATUS_RE = re.compile(r"Status:\s*v(\d+\.\d+\.\d+)", re.IGNORECASE)


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def read_version_file() -> str:
    if not VERSION_FILE.exists():
        raise FatalError(f"{VERSION_FILE}: not found")
    text = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not SEMVER_RE.match(text):
        raise FatalError(f"{VERSION_FILE}: {text!r} is not x.y.z")
    return text


def read_registry_version() -> str:
    if not REGISTRY.exists():
        raise FatalError(f"{REGISTRY}: not found")
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{REGISTRY}: invalid JSON: {exc}") from exc
    v = data.get("meta", {}).get("version")
    if not isinstance(v, str) or not SEMVER_RE.match(v):
        raise FatalError(f"{REGISTRY}: meta.version {v!r} is not x.y.z")
    return v


def read_changelog_top(version: str) -> tuple[str | None, str | None]:
    """Return (matched_heading, error_message).

    Keep a Changelog keeps [Unreleased] at the top of the file forever.
    The check therefore looks for a heading whose value equals VERSION
    anywhere in the file. Before the first release (VERSION < 1.0.0),
    [Unreleased] is accepted in place of a version heading.

    Returns the matched heading value on success, or (None, message) on
    failure.
    """
    if not CHANGELOG.exists():
        return None, f"{CHANGELOG}: not found"

    text = CHANGELOG.read_text(encoding="utf-8")

    headings = CHANGELOG_HEADING_RE.findall(text)
    if not headings:
        return None, f"{CHANGELOG}: no [x.y.z] or [Unreleased] headings"

    # Prefer a heading that matches VERSION exactly.
    if version in headings:
        return version, None

    # Pre-release: [Unreleased] is acceptable if VERSION is still 0.x.y.
    major = int(version.split(".", 1)[0])
    if major < 1 and "Unreleased" in headings:
        return "Unreleased", None

    return None, (
        f"{CHANGELOG}: no heading matching VERSION ({version}). "
        f"Found headings: {headings}. "
        f"Add '## [{version}]' to CHANGELOG.md."
    )


def read_readme_version() -> str | None:
    if not README.exists():
        return None
    text = README.read_text(encoding="utf-8")
    m = README_STATUS_RE.search(text)
    if not m:
        return None
    return m.group(1)


def read_parquet_version() -> tuple[str | None, str]:
    """Return (version, note). version is None if unavailable."""
    if not PARQUET.exists():
        return None, f"{PARQUET}: not present; skipped"
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:
        return None, "pyarrow not installed; Parquet footer not checked"
    try:
        schema = pq.read_schema(PARQUET)
    except Exception as exc:
        return None, f"{PARQUET}: could not read schema: {exc}"
    meta = schema.metadata or {}
    v = meta.get(b"iso3166.version")
    if v is None:
        return None, f"{PARQUET}: no iso3166.version footer"
    return v.decode("utf-8"), "ok"


def run() -> tuple[int, dict[str, Any]]:
    version = read_version_file()
    registry = read_registry_version()

    results: dict[str, Any] = {
        "version_file": version,
        "registry_meta_version": registry,
        "matches": [],
        "mismatches": [],
        "notes": [],
        "skips": [],
    }

    if version == registry:
        results["matches"].append(f"VERSION == meta.version ({version})")
    else:
        results["mismatches"].append(
            f"VERSION ({version}) != meta.version ({registry})"
        )

    changelog_value, changelog_err = read_changelog_top(version)
    if changelog_err:
        results["mismatches"].append(changelog_err)
    elif changelog_value == "Unreleased":
        results["notes"].append(
            f"CHANGELOG has [Unreleased]; VERSION is {version} < 1.0.0 "
            f"(pre-release, accepted)"
        )
    elif changelog_value == version:
        results["matches"].append(f"CHANGELOG contains [ {version} ]")
    else:
        results["mismatches"].append(
            f"CHANGELOG heading ({changelog_value}) != VERSION ({version})"
        )

    readme_v = read_readme_version()
    if readme_v is None:
        results["skips"].append("README: no version string; skipped")
    elif readme_v == version:
        results["matches"].append(f"README status == VERSION ({version})")
    else:
        results["mismatches"].append(
            f"README status ({readme_v}) != VERSION ({version})"
        )

    parquet_v, parquet_note = read_parquet_version()
    if parquet_v is None:
        results["skips"].append(f"Parquet: {parquet_note}")
    elif parquet_v == version:
        results["matches"].append(f"Parquet footer == VERSION ({version})")
    else:
        results["mismatches"].append(
            f"Parquet footer ({parquet_v}) != VERSION ({version})"
        )

    exit_code = 1 if results["mismatches"] else 0
    return exit_code, results


def print_human(results: dict[str, Any]) -> None:
    print("version consistency")
    print()
    for m in results["matches"]:
        print(f"  OK    {m}")
    for s in results["skips"]:
        print(f"  SKIP  {s}")
    for n in results["notes"]:
        print(f"  NOTE  {n}")
    for m in results["mismatches"]:
        print(f"  FAIL  {m}")
    print()
    if results["mismatches"]:
        print(f"MISMATCH: {len(results['mismatches'])} issue(s)")
    else:
        print("OK")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify that all version references agree."
    )
    ap.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = ap.parse_args()

    exit_code, results = run()

    if args.json:
        print(json.dumps(
            {"exit_code": exit_code, **results},
            indent=2, sort_keys=True, ensure_ascii=False,
        ))
    else:
        print_human(results)

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
