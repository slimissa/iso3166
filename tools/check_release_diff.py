#!/usr/bin/env python3
"""Check that regenerating the artifacts changed nothing but the version.

release.sh step 2 bumps the version, regenerates every generated artifact
and then runs the gate. A --check on a file that was just regenerated
compares the file with itself, so it can never fail. This tool compares the
regenerated artifacts with the COMMITTED ones (HEAD) instead.

Between the pre-bump commit and the bumped tree, the artifacts may differ
only in the version string and the `updated` date. Any other changed line,
or any change to the content of a Parquet table, means a generator or the
data changed what the exports say, and the release stops.

When VERSION equals HEAD's VERSION (resume mode, or a re-run) no change at
all is allowed.

Usage:
    python3 tools/check_release_diff.py [--root DIR]

--root DIR compares the repository at DIR instead of this one (the tests).

Exit codes: 0 = only version changes; 1 = unexpected change; 2 = cannot run.
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # replaced by --root

# Keep in step with FRESHNESS_ARTIFACTS in scripts/release.sh.
ARTIFACTS = (
    "iso3166*.sql", "iso3166*.csv", "iso3166*.tsv",
    "iso3166.parquet", "countries_by_region.parquet",
    "wrappers/go/iso3166.json", "wrappers/javascript/iso3166.json",
    "wrappers/python/iso3166/iso3166.json", "wrappers/rust/iso3166.json",
    "tests/cross_language_consistency.json", "docs/WITHDRAWN.md",
)

# `"updated": ...` in JSON and `-- Registry updated: 2026-11-03` in SQL/MD.
UPDATED_LINE = re.compile(r'"updated"|\bupdated\b\W+\d{4}-\d{2}-\d{2}',
                          re.IGNORECASE)


def git(*args: str, binary: bool = False):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace").strip())
    return p.stdout if binary else p.stdout.decode("utf-8")


def changed_files() -> list[str]:
    out = git("diff", "--name-only", "HEAD", "--", *ARTIFACTS)
    return [l for l in out.splitlines() if l]


def check_text(path: str, versions: set[str], bump: bool) -> list[str]:
    """Every changed line must carry a version string (or `updated`)."""
    bad = []
    diff = git("diff", "-U0", "HEAD", "--", path)
    in_hunk = False
    for line in diff.splitlines():
        # A removed SQL comment reads `--- Registry ...`, so the file header
        # lines can only be told apart by position: they come before the
        # first @@ of the file.
        if line.startswith("diff --git"):
            in_hunk = False
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk or line[:1] not in "+-":
            continue
        body = line[1:]
        if bump and (any(v in body for v in versions)
                     or UPDATED_LINE.search(body)):
            continue
        bad.append(f"{path}: {line.strip()[:100]}")
    return bad


def check_parquet(path: str, bump: bool) -> list[str]:
    """Same table content; schema metadata may differ only on a bump."""
    import pyarrow.parquet as pq

    old = pq.read_table(io.BytesIO(git("show", f"HEAD:{path}", binary=True)))
    new = pq.read_table(ROOT / path)
    if not old.replace_schema_metadata(None).equals(
            new.replace_schema_metadata(None)):
        return [f"{path}: table content differs from HEAD"]
    if not bump and old.schema.metadata != new.schema.metadata:
        return [f"{path}: schema metadata differs from HEAD"]
    return []


def main(argv: list[str] | None = None) -> int:
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.root:
        ROOT = args.root.resolve()
    try:
        old_version = git("show", "HEAD:VERSION").strip()
        new_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        files = changed_files()
    except (RuntimeError, OSError) as exc:
        print(f"check_release_diff: cannot compare with HEAD: {exc}",
              file=sys.stderr)
        return 2

    bump = old_version != new_version
    versions = {old_version, new_version}
    problems: list[str] = []
    for f in files:
        if f.endswith(".parquet"):
            problems += check_parquet(f, bump)
        else:
            problems += check_text(f, versions, bump)

    if problems:
        print(f"FAIL: regeneration changed more than the version "
              f"({old_version} -> {new_version}):", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"OK: {len(files)} regenerated artifact(s) differ from HEAD only "
          f"in the version ({old_version} -> {new_version})"
          if files else "OK: regenerated artifacts are identical to HEAD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
