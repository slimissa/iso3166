#!/usr/bin/env python3
"""
tools/check_release_claims.py

Read tools/release_claims.json and verify every claim for a given
version against the current repository state.

Each claim is one of:

  {"file": "path"}                     — path must exist
  {"file": "path", "contains": "text"} — path must exist and include text
  {"file": "path", "absent": "text"}   — path must exist and NOT include text

"contains" and "absent" may be combined in one claim. Both need a
non-empty string. A claim with any other key fails, so a misspelled key
cannot silently turn into a bare existence check. Existence-only claims
never read the file, so they work for binary artifacts; "contains" and
"absent" claims read it as UTF-8 and fail cleanly on a binary file.

Usage:
    python3 tools/check_release_claims.py 1.6.5
    python3 tools/check_release_claims.py 1.6.5 --list
    python3 tools/check_release_claims.py 1.6.5 --json

Exit codes:
    0  all claims verified
    1  at least one claim failed
    2  fatal (manifest missing, version not in manifest, malformed entry)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = PROJECT_ROOT / "tools" / "release_claims.json"


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def load_manifest() -> dict:
    if not MANIFEST.exists():
        raise FatalError(f"manifest not found: {MANIFEST}")
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{MANIFEST}: invalid JSON: {exc}") from exc


CLAIM_KEYS = frozenset({"file", "contains", "absent"})


def check_claim(claim: dict) -> tuple[bool, str]:
    if "file" not in claim:
        return False, "claim has no 'file' key"
    name = claim["file"]
    if not isinstance(name, str):
        return False, f"'file' must be a string, got {name!r}"
    unknown = sorted(set(claim) - CLAIM_KEYS)
    if unknown:
        return False, f"{name}: unknown claim key(s): {', '.join(unknown)}"
    for key in ("contains", "absent"):
        if key in claim and (not isinstance(claim[key], str) or not claim[key]):
            return False, f"{name}: '{key}' must be a non-empty string"

    path = PROJECT_ROOT / name
    if not path.exists():
        return False, f"missing file: {name}"
    if "contains" not in claim and "absent" not in claim:
        return True, f"{name} exists"

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, f"{name}: binary file, cannot read as UTF-8"

    details = []
    if "contains" in claim:
        needle = claim["contains"]
        if needle not in content:
            return False, f"{name} does not contain {needle!r}"
        details.append(f"contains {needle!r}")
    if "absent" in claim:
        needle = claim["absent"]
        if needle in content:
            return False, f"{name} contains forbidden {needle!r}"
        details.append(f"does not contain {needle!r}")
    return True, f"{name} " + " and ".join(details)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="check_release_claims")
    p.add_argument("version")
    p.add_argument("--list", action="store_true",
                   help="Print claims without checking")
    p.add_argument("--json", action="store_true",
                   help="Machine-readable output")
    args = p.parse_args(argv)

    manifest = load_manifest()
    claims = manifest.get(args.version)
    if claims is None:
        raise FatalError(
            f"no claims for version {args.version} in {MANIFEST.name}. "
            f"Every release must have a manifest entry."
        )
    if not isinstance(claims, list):
        raise FatalError(f"claims for {args.version} is not a list")

    results = []
    for claim in claims:
        if not isinstance(claim, dict):
            results.append((False, f"not an object: {claim!r}"))
            continue
        results.append(check_claim(claim))

    if args.json:
        print(json.dumps({
            "version": args.version,
            "total": len(results),
            "passed": sum(1 for ok, _ in results if ok),
            "failed": sum(1 for ok, _ in results if not ok),
            "results": [{"ok": ok, "detail": d} for ok, d in results],
        }, indent=2))
    else:
        rule = "=" * 60
        print(rule)
        print(f"  release claims — v{args.version}")
        print(rule)
        for ok, detail in results:
            marker = "OK  " if ok else "FAIL"
            print(f"  [{marker}] {detail}")
        print(rule)
        failed = [d for ok, d in results if not ok]
        if failed:
            print(f"  {len(failed)} claim(s) failed")
        else:
            print(f"  all {len(results)} claim(s) verified")

    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
