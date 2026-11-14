#!/usr/bin/env python3
"""
tools/check_version_consistency.py

Verify that the version references in this repository agree, and bump them.

The list of version sites is DATA: tools/version_axes.json. This tool, the
bump step of scripts/release.sh and the README's version-site table all
follow that one file. Each entry of its "sites" array has:

    name         unique site name, printed on every result line
    axis         the axis it belongs to (its "source" file is the reference)
    path         the file, relative to the repository root
    extractor    how to read the version: one of "extractors" in the file
    extractor_arg  the extractor's argument, where it takes one
    required     a missing file is a mismatch (true) or a skip (false)
    bumped       true: release.sh writes this site (via --bump)
    bumper       the bumper that writes it, one of "bumpers" (when bumped)
    generated_by the generator that rewrites it later in the release (a
                 site with this key is not asserted by --expect, because
                 it is regenerated after the bump)

Pre-release exception
---------------------
Before the first tagged release, VERSION is 0.x.y and the CHANGELOG's top
heading is [Unreleased]. This is the correct state and would otherwise
fail the check. Rule:

    if version < 1.0.0: [Unreleased] is accepted for CHANGELOG
    else:               the first [x.y.z] heading must equal version

A README without a badge and a Parquet file that is absent (or unreadable
without pyarrow) are skipped with a note, not failed.

Usage:
    python3 tools/check_version_consistency.py
    python3 tools/check_version_consistency.py --json
    python3 tools/check_version_consistency.py --bump 1.12.6   # release.sh
    python3 tools/check_version_consistency.py --expect 1.12.6 # release.sh
    python3 tools/check_version_consistency.py --root DIR --axes FILE

Exit codes:
    0  All sites agree (--bump: every bumped site now reads the version).
    1  Discrepancy found.
    2  A required source (VERSION, version_axes.json) is missing or invalid.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if not (PROJECT_ROOT / "iso3166.json").is_file():
    print(
        f"error: {PROJECT_ROOT / 'iso3166.json'} not found; "
        "this tool must run from a repository checkout.",
        file=sys.stderr,
    )
    sys.exit(2)

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
CHANGELOG_HEADING_RE = re.compile(r"^## \[([0-9]+\.[0-9]+\.[0-9]+|Unreleased)\]", re.MULTILINE)
# Any badge colour: shields.io accepts names (orange, blue) and hex (007ec6).
BADGE_RE = r"{label}-(\d+\.\d+\.\d+)-\w+"


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


class Skip(Exception):
    """The site cannot be read here, and that is acceptable."""


class Bad(Exception):
    """The site is unreadable or malformed: a mismatch."""


# ---------------------------------------------------------------- extractors
# Each takes (root, site, ctx) and returns the version string, or raises
# Skip / Bad. ctx["version"] is the reference version.

def _text(root: Path, site: dict) -> str:
    p = root / site["path"]
    if not p.is_file():
        raise Bad(f"{site['path']}: file not found")
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Bad(f"{site['path']}: could not read: {exc}") from exc


def ex_text(root, site, ctx):
    v = _text(root, site).strip()
    if not SEMVER_RE.match(v):
        raise Bad(f"{site['path']}: {v!r} is not x.y.z")
    return v


def ex_json_path(root, site, ctx):
    try:
        node: Any = json.loads(_text(root, site))
    except json.JSONDecodeError as exc:
        raise Bad(f"{site['path']}: invalid JSON: {exc}") from exc
    for part in site["extractor_arg"].split("."):
        node = node.get(part) if isinstance(node, dict) else None
    if not isinstance(node, str):
        raise Bad(f"{site['path']}: no string at {site['extractor_arg']!r}")
    return node


def ex_toml_section(root, site, ctx):
    text = _text(root, site)
    arg = site["extractor_arg"]
    if "." in arg:  # "<package>.<key>": a [[package]] entry of a lockfile
        pkg, key = arg.split(".", 1)
        m = re.search(rf'name = "{re.escape(pkg)}"\n{re.escape(key)} = "([^"]+)"', text)
        if not m:
            raise Bad(f"{site['path']}: no {key} for {pkg}")
        return m.group(1)
    m = re.search(rf'^{re.escape(arg)}\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        raise Bad(f"{site['path']}: no version declaration found")
    return m.group(1)


def ex_python_regex(root, site, ctx):
    m = re.search(site["extractor_arg"], _text(root, site), re.MULTILINE)
    if not m:
        raise Bad(f"{site['path']}: no version declaration found")
    return m.group(1)


def ex_badge(root, site, ctx):
    p = root / site["path"]
    if not p.is_file():
        raise Skip(f"{site['path']}: not present")
    m = re.search(BADGE_RE.format(label=re.escape(site["extractor_arg"])),
                  p.read_text(encoding="utf-8"), re.IGNORECASE)
    if not m:
        raise Skip(f"{site['path']}: no version string")
    return m.group(1)


def ex_first_released_heading(root, site, ctx):
    p = root / site["path"]
    if not p.is_file():
        raise Bad(f"{site['path']}: not found")
    headings = CHANGELOG_HEADING_RE.findall(p.read_text(encoding="utf-8"))
    released = [h for h in headings if h != "Unreleased"]
    version = ctx["version"]
    if released:
        top = released[0]
        if top == version:
            return top
        # Pre-release acceptance: the CHANGELOG heading may be exactly
        # one minor ahead of VERSION with patch 0 (x.y.z -> x.(y+1).0).
        # This is the CHANGELOG-first pattern `release.sh` uses: the
        # release section is committed before `release.sh` bumps VERSION,
        # so the checker must accept it, or `release.sh` can never run.
        try:
            top_t = tuple(int(x) for x in top.split("."))
            cur_t = tuple(int(x) for x in version.split("."))
        except ValueError:
            top_t = cur_t = None
        if (top_t is not None
                and top_t[0] == cur_t[0]
                and top_t[1] == cur_t[1]
                and top_t[2] == cur_t[2] + 1):
            ctx["notes"].append(
                f"CHANGELOG has [{top}]; VERSION is {version} "
                f"(pre-release: one patch ahead, accepted)")
            return version
    if "Unreleased" in headings and int(version.split(".", 1)[0]) < 1:
        ctx["notes"].append(
            f"CHANGELOG has [Unreleased]; VERSION is {version} < 1.0.0 "
            "(pre-release, accepted)")
        return version
    raise Bad(f"{site['path']}: no [x.y.z] heading matching VERSION "
              f"({version}); found {headings}")


def ex_parquet_footer(root, site, ctx):
    p = root / site["path"]
    if not p.is_file():
        raise Skip(f"{site['path']}: not present")
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:
        raise Skip("pyarrow not installed; Parquet footer not checked")
    try:
        meta = pq.read_schema(p).metadata or {}
    except Exception as exc:  # noqa: BLE001
        raise Skip(f"{site['path']}: could not read schema: {exc}")
    v = meta.get(site["extractor_arg"].encode())
    if v is None:
        raise Skip(f"{site['path']}: no {site['extractor_arg']} footer")
    return v.decode("utf-8")


EXTRACTORS: dict[str, Callable] = {
    "text": ex_text,
    "json_path": ex_json_path,
    "toml_section": ex_toml_section,
    "python_regex": ex_python_regex,
    "badge": ex_badge,
    "first_released_heading": ex_first_released_heading,
    "parquet_footer": ex_parquet_footer,
}


# ------------------------------------------------------------------- bumpers
# Each takes (root, site, version) and writes the site.

def _sub(root: Path, site: dict, pattern: str, version: str) -> None:
    p = root / site["path"]
    text = p.read_text(encoding="utf-8")
    new, n = re.subn(pattern, lambda m: m.group(1) + version + m.group(2), text,
                     count=1, flags=re.MULTILINE)
    if n == 0:
        raise FatalError(f"{site['path']}: pattern {pattern!r} matched nothing", 1)
    p.write_text(new, encoding="utf-8")


def wr_text(root, site, version):
    (root / site["path"]).write_text(version + "\n", encoding="utf-8")


def wr_meta_version(root, site, version):
    p = root / site["path"]
    d = json.loads(p.read_text(encoding="utf-8"))
    d["meta"]["version"] = version
    d["meta"]["updated"] = date.today().isoformat()
    p.write_text(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                 encoding="utf-8")


def wr_badge(root, site, version):
    _sub(root, site, r'(registry-)[0-9.]+(-\w+)', version)


def wr_pyproject_version(root, site, version):
    _sub(root, site, r'(^version = ")[0-9.]+(")', version)


def wr_init_version(root, site, version):
    _sub(root, site, r'(__version__ = ")[0-9.]+(")', version)


def wr_cargo_toml_version(root, site, version):
    _sub(root, site, r'(^version = ")[0-9.]+(")', version)


def wr_package_json(root, site, version):
    p = root / site["path"]
    d = json.loads(p.read_text(encoding="utf-8"))
    d["version"] = version
    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


BUMPERS: dict[str, Callable] = {
    "write_text": wr_text,
    "write_meta_version": wr_meta_version,
    "write_badge": wr_badge,
    "write_pyproject_version": wr_pyproject_version,
    "write_init_version": wr_init_version,
    "write_cargo_toml_version": wr_cargo_toml_version,
    "write_package_json": wr_package_json,
}


# ---------------------------------------------------------------- the axes

def load_axes(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FatalError(f"{path}: not found")
    try:
        axes = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{path}: invalid JSON: {exc}") from exc
    sites = axes.get("sites")
    if not isinstance(sites, list) or not sites:
        raise FatalError(f"{path}: no 'sites' array")
    seen: set[str] = set()
    for s in sites:
        for key in ("name", "path", "extractor", "bumped"):
            if key not in s:
                raise FatalError(f"{path}: site {s!r} has no {key!r}")
        if s["name"] in seen:
            raise FatalError(f"{path}: duplicate site name {s['name']!r}")
        seen.add(s["name"])
        if s["extractor"] not in EXTRACTORS:
            raise FatalError(f"{path}: site {s['name']}: unknown extractor "
                             f"{s['extractor']!r}")
        if not isinstance(s["bumped"], bool):
            raise FatalError(f"{path}: site {s['name']}: 'bumped' must be true or false")
        if s["bumped"] and s.get("bumper") not in BUMPERS:
            raise FatalError(f"{path}: site {s['name']}: unknown bumper "
                             f"{s.get('bumper')!r}")
    return axes


def reference_site(axes: dict[str, Any]) -> dict[str, Any]:
    source = axes["axes"][0]["source"]
    for s in axes["sites"]:
        if s["path"] == source:
            return s
    raise FatalError(f"axis source {source!r} is not a site")


def read_site(root: Path, site: dict, ctx: dict) -> tuple[str, str]:
    """(status, value-or-message): status is 'value', 'skip' or 'bad'."""
    try:
        return "value", EXTRACTORS[site["extractor"]](root, site, ctx)
    except Skip as exc:
        return "skip", str(exc)
    except Bad as exc:
        return "bad", str(exc)


def run(root: Path, axes: dict[str, Any], *, expect: str | None = None,
        ) -> tuple[int, dict[str, Any]]:
    ctx: dict[str, Any] = {"notes": []}
    ref = reference_site(axes)
    st, val = read_site(root, ref, {"version": "0.0.0", "notes": []})
    if st != "value":
        raise FatalError(val)
    version = expect or val
    ctx["version"] = version

    results: dict[str, Any] = {
        "version_file": val, "matches": [], "mismatches": [], "notes": ctx["notes"],
        "skips": [], "sites": [],
    }
    if expect is not None and val != expect:
        results["mismatches"].append(f"VERSION ({val}) != expected ({expect})")

    for site in axes["sites"]:
        if expect is not None and "generated_by" in site:
            continue  # regenerated after the bump; asserted by its own gate
        name, path = site["name"], site["path"]
        st, v = read_site(root, site, ctx)
        entry = {"name": name, "path": path, "extractor": site["extractor"],
                 "bumped": site["bumped"], "value": v if st == "value" else None,
                 "status": "ok"}
        required = site.get("required", True)
        if st == "bad" or (st == "skip" and expect is not None and required):
            if required:
                results["mismatches"].append(f"[{name}] {v}")
                entry["status"] = "mismatch"
            else:
                results["skips"].append(f"[{name}] {v}")
                entry["status"] = "skip"
        elif st == "skip":
            results["skips"].append(f"[{name}] {v}")
            entry["status"] = "skip"
        elif v == version:
            results["matches"].append(f"[{name}] {path} == VERSION ({version})")
        else:
            results["mismatches"].append(f"[{name}] {path} ({v}) != VERSION ({version})")
            entry["status"] = "mismatch"
        results["sites"].append(entry)
    results["registry_meta_version"] = next(
        (e["value"] for e in results["sites"] if e["path"] == "iso3166.json"), None)
    return (1 if results["mismatches"] else 0), results


def bump(root: Path, axes: dict[str, Any], version: str) -> int:
    if not SEMVER_RE.match(version):
        raise FatalError(f"{version!r} is not x.y.z")
    n = 0
    for site in axes["sites"]:
        if not site["bumped"]:
            continue
        BUMPERS[site["bumper"]](root, site, version)
        n += 1
        print(f"  bumped [{site['name']}] {site['path']} -> {version}")
    # Every bumped site must now read the new version.
    ctx = {"version": version, "notes": []}
    for site in axes["sites"]:
        if site["bumped"]:
            st, v = read_site(root, site, ctx)
            if st != "value" or v != version:
                print(f"  FAIL [{site['name']}] reads {v!r} after the bump",
                      file=sys.stderr)
                return 1
    print(f"  {n} sites bumped to {version}")
    return 0


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
        description="Verify that all version references agree (sites from "
                    "tools/version_axes.json).")
    ap.add_argument("--json", action="store_true", help="Machine-readable output.")
    ap.add_argument("--bump", metavar="X.Y.Z",
                    help="Write every site with bumped: true (used by release.sh).")
    ap.add_argument("--expect", metavar="X.Y.Z",
                    help="Assert every site, except generated ones, reads X.Y.Z.")
    ap.add_argument("--root", type=Path, default=PROJECT_ROOT,
                    help="Repository root (default: this checkout).")
    ap.add_argument("--axes", type=Path, default=None,
                    help="version_axes.json (default: <root>/tools/version_axes.json).")
    args = ap.parse_args()

    root = args.root.resolve()
    axes = load_axes(args.axes or root / "tools" / "version_axes.json")

    if args.bump:
        return bump(root, axes, args.bump)

    exit_code, results = run(root, axes, expect=args.expect)

    if args.expect and not args.json:
        if exit_code == 0:
            print(f"  all {len(results['matches'])} version sites read {args.expect}")
        else:
            for m in results["mismatches"]:
                print(f"  FAIL  {m}", file=sys.stderr)
        return exit_code
    if args.json:
        print(json.dumps({"exit_code": exit_code, **results},
                         indent=2, sort_keys=True, ensure_ascii=False))
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
