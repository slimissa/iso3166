#!/usr/bin/env python3
"""
tools/check_snapshot_freshness.py

Reads every tools/*_snapshot.json and verifies that its
meta.review_by field is not in the past.

This tool checks the snapshot's own review date. It is not the
mechanism that catches version drift between a vendored snapshot
and its source.

Two mechanisms, two concerns:

  - Cross-reference check (in the consumer's own repo). Validates
    the consumer's data against the snapshot. Fires when the
    consumer's fields diverge from the snapshot's contents. This
    is what catches drift in data the consumer uses.

  - review_by (this tool). Scheduled re-verification of the
    snapshot against its source. Fires on a calendar date,
    independent of any consumer's data. This is what catches
    changes to parts of the source the consumer does not
    reference yet.

Neither replaces the other. Do not merge them.

For each snapshot, the tool first looks for a sibling metadata
file at tools/<stem>.meta.json. If that file exists, review_by
and refresh_cadence are read from it. This is the vendored-
snapshot shape: when a snapshot is a byte-for-byte copy of an
external source, the cadence metadata lives in the sibling file
so the snapshot itself stays unmodified.

If no sibling exists, review_by is read from the snapshot's own
meta block.

Two notes on the shape:

1. The sibling file's review_by is read from
   `sibling.meta.review_by`, not from the sibling's top level.
   A flat `review_by` at the top of the sibling file will be
   reported as `unset` (warning, exit 0). The `meta` block is
   required.

2. This tool checks vendored snapshots — copies of external
   standards kept in `tools/`. The registry's own freshness is
   a separate concern. For ISO 3166, `validate.py` and the
   enrichment pipeline cover that. A future
   `check_registry_freshness.py` would be the right home for a
   registry-level check; ISO 4217 and ISO 10383 have that
   tool already.

Three-state design:

  - ISO date (YYYY-MM-DD)   fail if past, pass if future or today
  - "closed"                never checked; snapshot is static
  - null or missing         warn (not fail); review_by is unset

Usage:
    python3 tools/check_snapshot_freshness.py
    python3 tools/check_snapshot_freshness.py --json
    python3 tools/check_snapshot_freshness.py --today 2027-01-01
    python3 tools/check_snapshot_freshness.py --check-upstream

--check-upstream (opt-in, needs the network, never run by the gate) also reads
`meta.source_version` and `meta.source_repo` of each snapshot that carries
them (today: iso4217_snapshot.json), lists the repository's stable vX.Y.Z
tags with `git ls-remote --tags`, and prints a WARN when the vendored
version is more than 3 stable tags behind the latest. It never changes the
exit code: a calendar `review_by` cannot see a sibling that shipped ten
releases, and this check can, but a new upstream tag with no data change
should not block a release. An unreachable upstream is a WARN, not a pass.

Exit codes:
    0  all snapshots fresh
    1  at least one snapshot is past due
    2  fatal (no snapshots found, malformed file)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_GLOB = "tools/*_snapshot.json"


def sibling_meta_path(snapshot_path: Path) -> Path:
    """Return tools/<stem>.meta.json for tools/<stem>.json."""
    return snapshot_path.with_name(snapshot_path.stem + ".meta.json")

UPSTREAM_BEHIND_LIMIT = 3
STABLE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

EXIT_OK = 0
EXIT_STALE = 1
EXIT_FATAL = 2


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = EXIT_FATAL) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise FatalError(f"invalid ISO date: {value!r}") from exc


def evaluate(path: Path, today: date) -> dict[str, Any]:
    """
    Return a dict with keys: file, status, detail, review_by, meta_source.

    meta_source is one of:
      "sibling"   metadata was read from tools/<stem>.meta.json
      "snapshot"  metadata was read from the snapshot's own meta block

    status is one of:
      "fresh"    review_by is in the future or today
      "closed"   snapshot is static; never checked
      "unset"    review_by is missing or null; warning only
      "stale"    review_by is in the past
    """
    rel = str(path.relative_to(PROJECT_ROOT))

    # Prefer the sibling metadata file when it exists.
    sibling = sibling_meta_path(path)
    meta_source = "snapshot"
    if sibling.exists():
        try:
            data = json.loads(sibling.read_text(encoding="utf-8"))
        except OSError as exc:
            raise FatalError(f"{sibling}: cannot read: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise FatalError(f"{sibling}: invalid JSON: {exc}") from exc
        meta_source = "sibling"
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise FatalError(f"{path}: cannot read: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise FatalError(f"{path}: invalid JSON: {exc}") from exc

    meta = data.get("meta")

    if not isinstance(meta, dict):
        return {
            "file": rel,
            "status": "unset",
            "detail": "meta is missing or not an object",
            "review_by": None,
            "meta_source": meta_source,
        }

    review_by = meta.get("review_by")

    if review_by is None:
        return {
            "file": rel,
            "status": "unset",
            "detail": "review_by is not set",
            "review_by": None,
            "meta_source": meta_source,
        }

    if review_by == "closed":
        return {
            "file": rel,
            "status": "closed",
            "detail": "static snapshot, no review required",
            "review_by": "closed",
            "meta_source": meta_source,
        }

    if not isinstance(review_by, str):
        return {
            "file": rel,
            "status": "unset",
            "detail": f"review_by has unexpected type: {type(review_by).__name__}",
            "review_by": None,
            "meta_source": meta_source,
        }

    d = parse_iso_date(review_by)
    if d < today:
        return {
            "file": rel,
            "status": "stale",
            "detail": f"review_by {review_by} is past due",
            "review_by": review_by,
            "meta_source": meta_source,
        }

    return {
        "file": rel,
        "status": "fresh",
        "detail": f"review_by {review_by}",
        "review_by": review_by,
        "meta_source": meta_source,
    }


def repo_url(repo: str) -> str:
    """owner/name -> a GitHub URL; a URL or a local path is used as given."""
    if "://" in repo or repo.startswith(("/", ".", "file:")):
        return repo
    return f"https://github.com/{repo}"


def parse_version(text: str) -> tuple[int, int, int]:
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)$", text.strip())
    if not m:
        raise ValueError(f"not a stable X.Y.Z version: {text!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def stable_tags(repo: str, timeout: int = 60) -> list[tuple[int, int, int]]:
    """Stable vX.Y.Z tags of repo, sorted. Raises OSError if unreadable."""
    try:
        p = subprocess.run(
            ["git", "ls-remote", "--tags", repo_url(repo)],
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OSError(f"git ls-remote failed: {exc}") from exc
    if p.returncode != 0:
        raise OSError(p.stderr.strip().splitlines()[-1] if p.stderr.strip()
                      else f"git ls-remote exited {p.returncode}")
    tags = set()
    for line in p.stdout.splitlines():
        ref = line.split("\t")[-1].removeprefix("refs/tags/")
        m = STABLE_TAG.match(ref)
        if m:
            tags.add(tuple(int(x) for x in m.groups()))
    return sorted(tags)


def snapshot_meta(path: Path) -> dict[str, Any]:
    sibling = sibling_meta_path(path)
    src = sibling if sibling.exists() else path
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    meta = data.get("meta") if isinstance(data, dict) else None
    return meta if isinstance(meta, dict) else {}


def check_upstream(path: Path) -> dict[str, Any] | None:
    """None when the snapshot names no source_version/source_repo pair."""
    meta = snapshot_meta(path)
    version, repo = meta.get("source_version"), meta.get("source_repo")
    if not version or not repo:
        return None
    rel = str(path.relative_to(PROJECT_ROOT))
    out: dict[str, Any] = {"file": rel, "repo": repo, "vendored": str(version)}
    try:
        have = parse_version(str(version))
        tags = stable_tags(repo)
    except ValueError as exc:
        return {**out, "status": "warn", "detail": f"bad source_version: {exc}"}
    except OSError as exc:
        return {**out, "status": "warn",
                "detail": f"upstream unreachable ({exc}); gap unknown"}
    if not tags:
        return {**out, "status": "warn", "detail": "no stable tags upstream"}
    behind = sum(1 for t in tags if t > have)
    latest = ".".join(map(str, tags[-1]))
    out.update(behind=behind, latest=latest)
    if behind > UPSTREAM_BEHIND_LIMIT:
        out.update(status="warn", detail=(
            f"vendored {version} of {repo} is {behind} stable tags behind "
            f"(latest {latest}; limit {UPSTREAM_BEHIND_LIMIT})"))
    else:
        out.update(status="ok", detail=(
            f"vendored {version} of {repo}: {behind} stable tag(s) behind "
            f"(latest {latest})"))
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check_snapshot_freshness",
        description=(
            "Verify meta.review_by on every tools/*_snapshot.json. "
            "Exit 0 if all snapshots are fresh or marked closed."
        ),
    )
    p.add_argument("--json", action="store_true",
                   help="Emit machine-readable JSON.")
    p.add_argument("--today", metavar="YYYY-MM-DD", default=None,
                   help="Override today's date, for testing.")
    p.add_argument("--check-upstream", action="store_true",
                   help="Also compare meta.source_version with the source "
                        "repository's stable tags (network; warn only).")
    p.add_argument("--root", type=Path, default=None,
                   help="Check the snapshots of the repository at ROOT "
                        "(used by the tests).")
    return p


def report_text(results: list[dict[str, Any]], today: date) -> None:
    rule = "=" * 78
    print(rule)
    print("  Snapshot freshness check")
    print(rule)
    print(f"  Today:     {today.isoformat()}")
    print(f"  Snapshots: {len(results)}")
    print(rule)
    for r in results:
        marker = {
            "fresh":  "OK  ",
            "closed": "SKIP",
            "unset":  "WARN",
            "stale":  "FAIL",
        }[r["status"]]
        source = r.get("meta_source", "snapshot")
        suffix = " (sibling)" if source == "sibling" else ""
        print(f"  [{marker}] {r['file']}: {r['detail']}{suffix}")
    print(rule)

    stale = [r for r in results if r["status"] == "stale"]
    unset = [r for r in results if r["status"] == "unset"]

    if stale:
        print(f"  FAIL: {len(stale)} snapshot(s) past due")
    elif unset:
        print(f"  OK with {len(unset)} warning(s): review_by unset")
    else:
        print("  OK: all snapshots fresh")
    print(rule)


def report_json(results: list[dict[str, Any]], today: date) -> None:
    payload = {
        "today": today.isoformat(),
        "total": len(results),
        "fresh": sum(1 for r in results if r["status"] == "fresh"),
        "closed": sum(1 for r in results if r["status"] == "closed"),
        "unset": sum(1 for r in results if r["status"] == "unset"),
        "stale": sum(1 for r in results if r["status"] == "stale"),
        "results": results,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    global PROJECT_ROOT
    args = build_parser().parse_args(argv)
    if args.root:
        PROJECT_ROOT = args.root.resolve()

    today = parse_iso_date(args.today) if args.today else date.today()

    snapshots = sorted(PROJECT_ROOT.glob(SNAPSHOT_GLOB))
    if not snapshots:
        raise FatalError(f"no files matched {SNAPSHOT_GLOB} under {PROJECT_ROOT}")

    results = [evaluate(p, today) for p in snapshots]
    upstream = ([u for u in (check_upstream(p) for p in snapshots) if u]
                if args.check_upstream else [])

    if args.json:
        report_json(results, today)
        if args.check_upstream:
            print(json.dumps({"upstream": upstream}, indent=2, ensure_ascii=False))
    else:
        report_text(results, today)
        if args.check_upstream:
            print("  Upstream versions (--check-upstream; warnings only)")
            if not upstream:
                print("  (no snapshot carries source_version and source_repo)")
            for u in upstream:
                marker = "OK  " if u["status"] == "ok" else "WARN"
                print(f"  [{marker}] {u['file']}: {u['detail']}")
            print("=" * 78)

    return EXIT_STALE if any(r["status"] == "stale" for r in results) else EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
