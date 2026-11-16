#!/usr/bin/env python3
"""
tools/gen_registry_release.py

Emit registry_release.json: one machine-readable manifest of a release. A
consumer who wants to verify a release reads this file and hashes the files
it lists, instead of discovering them by hand.

Fields (registry_release.schema.json is the contract):

    registry         "iso3166"
    version          VERSION
    format_version   iso3166.json meta.format_version, else "1.0.0"
    schema_version   the version in schema.json's $id
    released         iso3166.json meta.updated: the DATA update date.
                     release.sh sets it to the release day at the bump, so
                     the manifest is a pure function of the tree and --check
                     stays deterministic (a "today" read here would drift at
                     midnight)
    released_at      the TAG date. null in the tagged tree. release.sh stamps
                     it (--stamp-released-at) in the verification-report
                     commit, after the tag. Write mode keeps a stamped value;
                     --check ignores it (it must be null or a valid date)
    commit           null, by design: the file ships in the release commit
                     and cannot contain that commit's SHA
    tag              "v<version>"
    tag_object       null, same reason
    distribution     "source-only"
    source           {name, snapshot, sha256}: meta.source, and
                     meta.source_snapshot / meta.source_hash when the
                     registry carries them (it does not yet: null)
    files            16 artifacts: path, layer, bytes, sha256
    counts           entries by status, introduced dated/null, tests per
                     suite (the README Tests table), gate commands
                     (scripts/release.sh), claims (tools/release_claims.json)
    vendors          vendored snapshots (ISO 4217: version, review_by)

Usage:
    python3 tools/gen_registry_release.py                       # write
    python3 tools/gen_registry_release.py --check --version X.Y.Z
    python3 tools/gen_registry_release.py --stamp-released-at YYYY-MM-DD

--check regenerates in memory and compares byte for byte with the committed
file. --version X.Y.Z must equal VERSION.

Exit codes:
    0  written / the committed file matches.
    1  the committed file differs from the tree.
    2  usage error or a missing or unreadable input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_NAME = "registry_release.json"

# (path, layer). Layers: raw = a per-format dump of the registry rows;
# curated = hand-maintained source of truth; aggregated = a derived table;
# bundled = a copy shipped inside a wrapper; snapshot = a vendored snapshot.
FILES: tuple[tuple[str, str], ...] = (
    ("iso3166.json", "curated"),
    ("schema.json", "curated"),
    ("iso3166.sql", "raw"),
    ("iso3166.postgresql.sql", "raw"),
    ("iso3166.mysql.sql", "raw"),
    ("iso3166.sqlite.sql", "raw"),
    ("iso3166.csv", "raw"),
    ("iso3166.excel.csv", "raw"),
    ("iso3166.european.csv", "raw"),
    ("iso3166.tsv", "raw"),
    ("iso3166.parquet", "raw"),
    ("countries_by_region.parquet", "aggregated"),
    ("wrappers/python/iso3166/iso3166.json", "bundled"),
    ("wrappers/javascript/iso3166.json", "bundled"),
    ("wrappers/go/iso3166.json", "bundled"),
    ("wrappers/rust/iso3166.json", "bundled"),
)
VENDORS = (("iso4217", "tools/iso4217_snapshot.json"),)

SUITES = {
    "Root (Python)": "root",
    "Python wrapper": "python_wrapper",
    "JavaScript": "javascript",
    "Rust": "rust",
    "Go": "go",
}


class InputError(Exception):
    pass


def valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def committed_manifest(path: Path) -> dict[str, Any] | None:
    """The committed manifest, or None when absent or not a JSON object."""
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _read(root: Path, rel: str) -> bytes:
    p = root / rel
    if not p.is_file():
        raise InputError(f"{rel}: not found")
    return p.read_bytes()


def _json(root: Path, rel: str) -> Any:
    try:
        return json.loads(_read(root, rel).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"{rel}: invalid JSON: {exc}") from exc


def gate_count(release_sh: str) -> int:
    """Indented `gate ...` lines of scripts/release.sh."""
    return len(re.findall(r"^[ \t]+gate[ \t]", release_sh, re.M))


def test_counts(readme: str) -> dict[str, int]:
    """Tests per suite, from the README Tests table (leading integers)."""
    sec = readme.split("### Tests", 1)[-1].split("###", 1)[0]
    out: dict[str, int] = {}
    for name, key in SUITES.items():
        m = re.search(rf"^\| {re.escape(name)} \|[^|]*\| (\d+)", sec, re.M)
        if not m:
            raise InputError(f"README.md: no '{name}' row in the Tests table")
        out[key] = int(m.group(1))
    out["total"] = sum(out.values())
    return out


def build(root: Path, version: str) -> dict[str, Any]:
    reg = _json(root, "iso3166.json")
    meta = reg.get("meta", {})
    schema = _json(root, "schema.json")
    m = re.search(r"/(\d+\.\d+\.\d+)$", str(schema.get("$id", "")))
    if not m:
        raise InputError("schema.json: $id does not end in /x.y.z")
    active = reg["countries"]["active"]
    claims = _json(root, "tools/release_claims.json").get(version)
    if claims is None:
        raise InputError(f"tools/release_claims.json: no claims for {version}")

    files = []
    for rel, layer in FILES:
        data = _read(root, rel)
        files.append({"path": rel, "layer": layer, "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})

    vendors = []
    for name, rel in VENDORS:
        snap = _json(root, rel).get("meta", {})
        vendors.append({
            "name": name,
            "version": snap.get("source_version"),
            "review_by": snap.get("review_by"),
            "source": snap.get("source_repo"),
            "path": rel,
            "sha256": hashlib.sha256(_read(root, rel)).hexdigest(),
        })

    return {
        "registry": "iso3166",
        "version": version,
        "format_version": meta.get("format_version", "1.0.0"),
        "schema_version": m.group(1),
        "released": meta.get("updated"),
        "released_at": None,
        "commit": None,
        "tag": f"v{version}",
        "tag_object": None,
        "distribution": "source-only",
        "source": {
            "name": meta.get("source"),
            "snapshot": meta.get("source_snapshot"),
            "sha256": meta.get("source_hash"),
        },
        "files": files,
        "counts": {
            "active": len(active),
            "withdrawn": len(reg["countries"]["withdrawn"]),
            "officially_assigned": sum(e["status"] == "officially-assigned"
                                       for e in active),
            "introduced_dated": sum(e.get("introduced") is not None
                                    for e in active),
            "introduced_null": sum(e.get("introduced") is None for e in active),
            "tests": test_counts(_read(root, "README.md").decode("utf-8")),
            "gates": gate_count(_read(root, "scripts/release.sh").decode("utf-8")),
            "claims": len(claims),
        },
        "vendors": vendors,
    }


def render(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emit or check registry_release.json.")
    ap.add_argument("--check", action="store_true",
                    help="Compare an in-memory regeneration with the committed file.")
    ap.add_argument("--stamp-released-at", metavar="YYYY-MM-DD",
                    help="Set released_at (the tag date) in the committed file. "
                         "Used by release.sh after the tag.")
    ap.add_argument("--version", metavar="X.Y.Z",
                    help="The version the manifest is for; must equal VERSION.")
    ap.add_argument("--root", type=Path, default=PROJECT_ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    out = root / OUT_NAME

    if args.stamp_released_at is not None:
        if args.check:
            print("error: --stamp-released-at and --check are separate modes",
                  file=sys.stderr)
            return 2
        if not valid_date(args.stamp_released_at):
            print(f"error: {args.stamp_released_at!r} is not a YYYY-MM-DD date",
                  file=sys.stderr)
            return 2
        doc = committed_manifest(out)
        if doc is None or "released_at" not in doc:
            print(f"error: {OUT_NAME}: not found or has no released_at; "
                  "run tools/gen_registry_release.py", file=sys.stderr)
            return 2
        doc["released_at"] = args.stamp_released_at
        out.write_text(render(doc), encoding="utf-8")
        print(f"stamped released_at {args.stamp_released_at}")
        return 0

    try:
        version = _read(root, "VERSION").decode("utf-8").strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise InputError(f"VERSION: {version!r} is not x.y.z")
        if args.version is not None and args.version != version:
            print(f"error: --version {args.version} but VERSION is {version}",
                  file=sys.stderr)
            return 2
        doc = build(root, version)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # released_at is the one field that is not a function of the tree: it is
    # stamped after the tag. Write mode keeps it; --check ignores its value
    # but requires it to be null or a real date.
    previous = committed_manifest(out)
    stamped = previous.get("released_at") if previous else None
    if stamped is not None and not valid_date(stamped):
        if args.check:
            print(f"DRIFT: {OUT_NAME}: released_at {stamped!r} is not null or a "
                  "YYYY-MM-DD date", file=sys.stderr)
            return 1
        stamped = None
    doc["released_at"] = stamped
    text = render(doc)

    if args.check:
        if not out.is_file():
            print(f"error: {OUT_NAME}: not found; run tools/gen_registry_release.py",
                  file=sys.stderr)
            return 2
        if out.read_text(encoding="utf-8") != text:
            print(f"DRIFT: {OUT_NAME} does not match the tree; "
                  "run tools/gen_registry_release.py", file=sys.stderr)
            return 1
        print(f"OK: {OUT_NAME} matches the tree ({version})")
        return 0

    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
