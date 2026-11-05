#!/usr/bin/env python3
"""Compare each consumer's vendored copy of this registry with this version.

tools/consumers.json lists the registries that vendor iso3166.json. For each
one this tool fetches the consumer's vendoring metadata from GitHub
(`<snapshot_path>` with `.json` replaced by `.meta.json`, on branch main),
reads `source_version`, and prints how many minor versions it is behind
VERSION.

Advisory: it needs the network and is not part of the release gate. The
consumers' own gates check that a vendored copy is byte-identical to the tag
it names; nothing on their side, or on this one, blocks a release because the
tag is old. This is the one place the root registry can see the lag.

Usage:
    python3 tools/check_consumers_current.py
    python3 tools/check_consumers_current.py --limit 3
    python3 tools/check_consumers_current.py --json

Exit codes:
    0  every consumer is fewer than --limit (default 5) minors behind
    1  at least one consumer is --limit or more minors behind
    2  a consumer's metadata could not be read, or consumers.json is missing
       or malformed (a comparison that could not run is not a pass)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = "https://raw.githubusercontent.com"
DEFAULT_LIMIT = 5
VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version(text: str) -> tuple[int, int, int]:
    m = VERSION_RE.match(str(text).strip())
    if not m:
        raise ValueError(f"not an X.Y.Z version: {text!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def minors_behind(current: tuple[int, int, int],
                  vendored: tuple[int, int, int]) -> int:
    """Minor versions between vendored and current; a major gap counts as
    its own size in minors of the older line plus the new line's minors."""
    if vendored > current:
        return 0
    if vendored[0] != current[0]:
        return 10_000   # across a major version: always over any limit
    return current[1] - vendored[1]


def meta_url(base: str, consumer: dict[str, Any]) -> str:
    snap = consumer["snapshot_path"]
    meta = re.sub(r"\.json$", ".meta.json", snap)
    return f"{base.rstrip('/')}/{consumer['repo']}/main/{meta}"


def fetch_json(url: str, timeout: int = 30) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def source_version(meta: dict[str, Any]) -> str | None:
    """Top level (ISO 4217, ISO 10383) or under `meta` (Exchange Calendar)."""
    if isinstance(meta.get("source_version"), str):
        return meta["source_version"]
    inner = meta.get("meta")
    if isinstance(inner, dict) and isinstance(inner.get("source_version"), str):
        return inner["source_version"]
    return None


def load_consumers(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    consumers = data.get("consumers") if isinstance(data, dict) else None
    if not isinstance(consumers, list) or not consumers:
        raise ValueError(f"{path}: no 'consumers' list")
    for c in consumers:
        for key in ("name", "repo", "snapshot_path"):
            if not isinstance(c.get(key), str):
                raise ValueError(f"{path}: a consumer lacks {key!r}: {c!r}")
    return consumers


def evaluate(consumer: dict[str, Any], current: tuple[int, int, int],
             base: str) -> dict[str, Any]:
    row: dict[str, Any] = {"name": consumer["name"], "repo": consumer["repo"],
                           "fields_read": consumer.get("fields_read", [])}
    url = meta_url(base, consumer)
    try:
        meta = fetch_json(url)
        sv = source_version(meta)
        if sv is None:
            return {**row, "status": "error",
                    "detail": f"no source_version in {url}"}
        gap = minors_behind(current, parse_version(sv))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {**row, "status": "error", "detail": f"{url}: {exc}"}
    return {**row, "status": "ok", "vendored": sv, "minors_behind": gap}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--consumers", type=Path, default=ROOT / "tools" / "consumers.json")
    ap.add_argument("--base-url", default=DEFAULT_BASE,
                    help="Where <repo>/main/<path> is served (a file:// URL in the tests).")
    ap.add_argument("--version", default=None,
                    help="Compare with this version instead of the VERSION file.")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help="Minors behind at which a consumer counts as behind.")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)

    try:
        consumers = load_consumers(args.consumers)
        text = args.version or (ROOT / "VERSION").read_text(encoding="utf-8")
        current = parse_version(text)
    except (ValueError, OSError) as exc:
        print(f"check_consumers_current: {exc}", file=sys.stderr)
        return 2

    rows = [evaluate(c, current, args.base_url) for c in consumers]
    for r in rows:
        if r["status"] == "ok":
            r["behind"] = r["minors_behind"] >= args.limit

    if args.as_json:
        print(json.dumps({"version": ".".join(map(str, current)),
                          "limit": args.limit, "consumers": rows},
                         indent=2, ensure_ascii=False))
    else:
        print(f"iso3166 {'.'.join(map(str, current))}; limit {args.limit} minors")
        for r in rows:
            if r["status"] != "ok":
                print(f"  [ERR ] {r['name']}: {r['detail']}")
                continue
            gap = r["minors_behind"]
            shown = "a major version" if gap >= 10_000 else f"{gap} minor(s)"
            print(f"  [{'BEHIND' if r['behind'] else 'OK    '}] {r['name']}: "
                  f"vendors {r['vendored']}, {shown} behind "
                  f"(reads {', '.join(r['fields_read']) or 'unlisted fields'})")

    if any(r["status"] == "error" for r in rows):
        return 2
    return 1 if any(r.get("behind") for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
