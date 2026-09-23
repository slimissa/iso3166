#!/usr/bin/env python3
"""
tools/validate.py

Six-layer validator for the ISO 3166 registry.

Layers, in order:

  1. schema           JSON Schema draft-07 validation against schema.json
  2. integrity        Format patterns, no empties, calendar-valid dates
  3. business         Uniqueness, status consistency, withdrawal rules
  4. cross-reference  currency_codes vs. ISO 4217 snapshot; borders and
                      replaced_by vs. active alpha-2 codes
  5. ground-truth     Codes-by-status vs. parse_source's frozen sets
  6. coverage         meta.count_* vs. actual; VERSION vs. meta.version

Exit codes:
  0  All layers passed.
  1  Data error (integrity, business, cross-reference, ground-truth,
     or coverage failed).
  2  Usage error (missing/unreadable input, bad flags).
  3  Schema violation (layer 1 failed).

Usage:
  python3 tools/validate.py iso3166.json
  python3 tools/validate.py iso3166.json --schema schema.json
  python3 tools/validate.py iso3166.json --only business
  python3 tools/validate.py iso3166.json --skip cross-reference
  python3 tools/validate.py iso3166.json --json
  python3 tools/validate.py iso3166.json --strict-count

The validator never reads iso3166.json to derive its own expectations.
Ground truth comes from parse_source; cross-registry from the snapshot.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Callable


# ============================================================
# Constants
# ============================================================

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import parse_source  # noqa: E402


LAYER_NAMES = (
    "schema",
    "integrity",
    "business",
    "cross-reference",
    "ground-truth",
    "coverage",
)

REQUIRED_FIELDS = ("alpha_2", "alpha_3", "numeric", "name", "status", "independent")

VALID_STATUSES = {
    "officially-assigned",
    "user-assigned",
    "exceptionally-reserved",
    "withdrawn",
}
ACTIVE_STATUSES = {"officially-assigned", "user-assigned", "exceptionally-reserved"}

OPTIONAL_LIST_FIELDS = ("currency_codes", "calling_codes", "tlds", "languages", "borders", "replaced_by")
OPTIONAL_STRING_FIELDS = ("official_name", "region", "subregion", "intermediate_region", "note")

ALPHA_2_RE = re.compile(r"^[A-Z]{2}$")
ALPHA_3_RE = re.compile(r"^[A-Z]{3}$")
NUMERIC_RE = re.compile(r"^[0-9]{3}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CALLING_CODE_RE = re.compile(r"^[0-9]+$")
TLD_RE = re.compile(r"^\.[a-z]{2,}$")
LANGUAGE_RE = re.compile(r"^[a-z]{3}$")


# ============================================================
# Diagnostics
# ============================================================

class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


class LayerResult:
    """Collects one layer's output."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []
        self.skip_reason: str | None = None

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def skip(self, reason: str) -> None:
        self.skip_reason = reason

    @property
    def status(self) -> str:
        if self.skip_reason:
            return "SKIP"
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "OK"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "notes": self.notes,
            "skip_reason": self.skip_reason,
        }


# ============================================================
# Loaders
# ============================================================

def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FatalError(f"registry not found: {path}", code=2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{path}: invalid JSON: {exc}", code=2) from exc


def load_snapshot(path: Path) -> dict[str, Any] | None:
    """Load an optional cross-registry snapshot. Returns None if absent."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# ============================================================
# Layer 1 — schema
# ============================================================

def layer_schema(reg: dict[str, Any], *, schema_path: Path) -> LayerResult:
    r = LayerResult("schema")

    if not schema_path.exists():
        r.skip(f"schema file not found: {schema_path}")
        return r

    try:
        import jsonschema  # type: ignore
    except ImportError:
        r.skip("jsonschema not installed (pip install jsonschema)")
        return r

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        r.skip(f"{schema_path}: invalid JSON: {exc}")
        return r

    try:
        validator = jsonschema.Draft7Validator(schema)
    except jsonschema.exceptions.SchemaError as exc:
        r.error(f"schema.json is not a valid draft-07 schema: {exc.message}")
        return r

    for err in sorted(validator.iter_errors(reg), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        r.error(f"{path}: {err.message}")

    if not r.errors:
        active = len(reg.get("countries", {}).get("active", []))
        withdrawn = len(reg.get("countries", {}).get("withdrawn", []))
        r.note(f"validated {active + withdrawn} entries against schema.json")
    return r


# ============================================================
# Layer 2 — integrity
# ============================================================

def _is_valid_iso_date(value: str) -> bool:
    if not ISO_DATE_RE.fullmatch(value):
        return False
    try:
        y, m, d = (int(x) for x in value.split("-"))
        date(y, m, d)
        return True
    except ValueError:
        return False


def layer_integrity(reg: dict[str, Any]) -> LayerResult:
    r = LayerResult("integrity")
    countries = reg.get("countries", {})

    for section in ("active", "withdrawn"):
        for i, entry in enumerate(countries.get(section, [])):
            a2 = entry.get("alpha_2", "?")
            where = f"{section}[{i}] ({a2})"

            # Required fields, non-empty.
            for f in REQUIRED_FIELDS:
                if f not in entry:
                    r.error(f"{where}: missing required field {f!r}")
                elif entry[f] is None or entry[f] == "":
                    r.error(f"{where}: required field {f!r} is empty")

            # Pattern checks.
            if "alpha_2" in entry and not ALPHA_2_RE.fullmatch(entry["alpha_2"] or ""):
                r.error(f"{where}: alpha_2 {entry['alpha_2']!r} does not match ^[A-Z]{{2}}$")
            if "alpha_3" in entry and not ALPHA_3_RE.fullmatch(entry["alpha_3"] or ""):
                r.error(f"{where}: alpha_3 {entry['alpha_3']!r} does not match ^[A-Z]{{3}}$")
            if "numeric" in entry and not NUMERIC_RE.fullmatch(entry["numeric"] or ""):
                r.error(f"{where}: numeric {entry['numeric']!r} does not match ^[0-9]{{3}}$")

            # Types.
            if "independent" in entry and not isinstance(entry["independent"], bool):
                r.error(f"{where}: independent must be a boolean")

            # Status.
            if "status" in entry and entry["status"] not in VALID_STATUSES:
                r.error(f"{where}: status {entry['status']!r} is not valid")

            # Optional string fields.
            for f in OPTIONAL_STRING_FIELDS:
                v = entry.get(f)
                if v is not None and not isinstance(v, str):
                    r.error(f"{where}: {f} must be a string or null")
                elif isinstance(v, str) and v.strip() == "":
                    r.error(f"{where}: {f} is an empty string (use null)")

            # Optional list fields.
            for f in OPTIONAL_LIST_FIELDS:
                v = entry.get(f)
                if v is None:
                    continue
                if not isinstance(v, list):
                    r.error(f"{where}: {f} must be a list or null")
                    continue
                for item in v:
                    if not isinstance(item, str):
                        r.error(f"{where}: {f} contains a non-string value {item!r}")

            # Field-specific format checks on optional lists.
            for code in entry.get("currency_codes") or []:
                if not ALPHA_3_RE.fullmatch(code):
                    r.error(f"{where}: currency_code {code!r} is not ^[A-Z]{{3}}$")
            for code in entry.get("borders") or []:
                if not ALPHA_2_RE.fullmatch(code):
                    r.error(f"{where}: border {code!r} is not ^[A-Z]{{2}}$")
            for code in entry.get("replaced_by") or []:
                if not ALPHA_2_RE.fullmatch(code):
                    r.error(f"{where}: replaced_by {code!r} is not ^[A-Z]{{2}}$")
            for code in entry.get("calling_codes") or []:
                if not CALLING_CODE_RE.fullmatch(code):
                    r.error(f"{where}: calling_code {code!r} is not ^[0-9]+$")
            for tld in entry.get("tlds") or []:
                if not TLD_RE.fullmatch(tld):
                    r.error(f"{where}: tld {tld!r} is not ^\\.[a-z]{{2,}}$")
            for lang in entry.get("languages") or []:
                if not LANGUAGE_RE.fullmatch(lang):
                    r.error(f"{where}: language {lang!r} is not ^[a-z]{{3}}$")

            # Date fields.
            for f in ("last_verified", "withdrawal_date"):
                v = entry.get(f)
                if v is None:
                    continue
                if not isinstance(v, str) or not _is_valid_iso_date(v):
                    r.error(f"{where}: {f} {v!r} is not a valid ISO date")

    # withdrawn entries must not carry a future withdrawal_date.
    from datetime import date as _date
    for i, entry in enumerate(countries.get("withdrawn", [])):
        wd = entry.get("withdrawal_date")
        if not wd:
            continue
        try:
            parsed = _date.fromisoformat(wd)
        except ValueError:
            continue  # already reported by the format check above
        if parsed > _date.today():
            r.error(
                f"withdrawn[{i}] ({entry.get('alpha_2')}): "
                f"withdrawal_date {wd} is in the future"
            )

    if not r.errors:
        total = sum(len(countries.get(s, [])) for s in ("active", "withdrawn"))
        r.note(f"{total} entries checked")
    return r


# ============================================================
# Layer 3 — business
# ============================================================

def layer_business(reg: dict[str, Any]) -> LayerResult:
    r = LayerResult("business")
    countries = reg.get("countries", {})
    active = countries.get("active", [])
    withdrawn = countries.get("withdrawn", [])

    # Uniqueness within each section.
    for section_name, section in (("active", active), ("withdrawn", withdrawn)):
        for field in ("alpha_2", "alpha_3"):
            codes = [e.get(field) for e in section if e.get(field)]
            dupes = sorted({c for c, n in Counter(codes).items() if n > 1})
            if dupes:
                r.error(f"{section_name}: duplicate {field}: {dupes}")

    # Status consistency.
    for i, e in enumerate(active):
        status = e.get("status")
        if status not in ACTIVE_STATUSES:
            r.error(f"active[{i}] ({e.get('alpha_2')}): status {status!r} is not an active status")
        if e.get("withdrawal_date") is not None:
            r.error(f"active[{i}] ({e.get('alpha_2')}): withdrawal_date must be null")
        if e.get("replaced_by") is not None:
            r.error(f"active[{i}] ({e.get('alpha_2')}): replaced_by must be null")

    for i, e in enumerate(withdrawn):
        if e.get("status") != "withdrawn":
            r.error(f"withdrawn[{i}] ({e.get('alpha_2')}): status must be 'withdrawn'")
        if not e.get("withdrawal_date"):
            r.error(f"withdrawn[{i}] ({e.get('alpha_2')}): withdrawal_date is required")

    # Self-reference: replaced_by must not contain the entry's own alpha_2.
    for e in withdrawn:
        a2 = e.get("alpha_2")
        for target in e.get("replaced_by") or []:
            if target == a2:
                r.error(f"withdrawn ({a2}): replaced_by contains itself")

    # Overlap between active and withdrawn (informational, not an error).
    active_codes = {e.get("alpha_2") for e in active if e.get("alpha_2")}
    withdrawn_codes = {e.get("alpha_2") for e in withdrawn if e.get("alpha_2")}
    overlap = active_codes & withdrawn_codes
    if overlap:
        r.note(f"codes in both active and withdrawn (expected for reassigned codes): {sorted(overlap)}")

    # Succession graph must be acyclic. Walk replaced_by from every
    # withdrawn entry; if any path returns to its start, fail.
    graph = {
        e["alpha_2"]: list(e.get("replaced_by") or [])
        for e in withdrawn
    }

    def _find_cycle(start: str, path: list[str]) -> list[str] | None:
        if start in path:
            return path + [start]
        succ = graph.get(start, [])
        for s in succ:
            found = _find_cycle(s, path + [start])
            if found:
                return found
        return None

    for code in graph:
        cycle = _find_cycle(code, [])
        if cycle:
            r.error(
                "succession cycle detected: " + " -> ".join(cycle)
            )
            break

    if not r.errors:
        r.note(f"{len(active)} active and {len(withdrawn)} withdrawn entries are internally consistent")
    return r


# ============================================================
# Layer 4 — cross-reference
# ============================================================

def layer_cross_reference(
    reg: dict[str, Any],
    *,
    snapshot_path: Path,
) -> LayerResult:
    r = LayerResult("cross-reference")
    countries = reg.get("countries", {})
    active = countries.get("active", [])
    active_codes = {e.get("alpha_2") for e in active if e.get("alpha_2")}

    # currency_codes vs. ISO 4217 snapshot (advisory in v1.0.0 per D5).
    snapshot = load_snapshot(snapshot_path)
    if snapshot is None:
        r.warn(
            f"ISO 4217 snapshot not found: {snapshot_path}. "
            f"currency_codes cross-registry check skipped. "
            f"This is advisory in v1.0.0 (see D5) and becomes blocking in v1.0.1."
        )
    else:
        currency_codes = set()
        for section in ("active", "withdrawn"):
            for e in countries.get(section, []):
                for c in e.get("currency_codes") or []:
                    currency_codes.add(c)
        known = set()
        for key in ("currencies", "active", "codes"):
            node = snapshot.get(key)
            if isinstance(node, list):
                for item in node:
                    if isinstance(item, str):
                        known.add(item)
                    elif isinstance(item, dict) and "code" in item:
                        known.add(item["code"])
        if not known:
            r.warn(f"{snapshot_path}: could not extract any currency codes")
        else:
            unknown = sorted(currency_codes - known)
            if unknown:
                r.error(f"currency_codes not in ISO 4217 snapshot: {unknown}")
            else:
                r.note(f"{len(currency_codes)} currency codes all present in snapshot")

    # borders vs. active alpha-2 codes.
    for e in active:
        a2 = e.get("alpha_2")
        for border in e.get("borders") or []:
            if border == a2:
                r.error(f"{a2}: border contains itself")
            elif border not in active_codes:
                r.error(f"{a2}: border {border!r} is not an active alpha_2 code")

    # replaced_by vs. any code in the registry (active OR withdrawn).
    #
    # A withdrawn code's successor may itself have been withdrawn. Example:
    #   YU (Yugoslavia) -> CS (Serbia and Montenegro) -> RS, ME
    # So the check must accept codes from either section. If a successor is
    # missing from the registry entirely, that's a gap the ground-truth
    # layer will separately catch — this layer only verifies the reference
    # is resolvable within the file.
    withdrawn_codes = {
        e.get("alpha_2") for e in countries.get("withdrawn", [])
        if e.get("alpha_2")
    }
    all_codes_in_registry = active_codes | withdrawn_codes
    for e in countries.get("withdrawn", []):
        a2 = e.get("alpha_2")
        for target in e.get("replaced_by") or []:
            if target not in all_codes_in_registry:
                r.error(
                    f"{a2}: replaced_by {target!r} is not present in the registry "
                    f"(must be an active or withdrawn alpha_2 code)"
                )

    return r


# ============================================================
# Layer 5 — ground-truth
# ============================================================

def layer_ground_truth(reg: dict[str, Any]) -> LayerResult:
    r = LayerResult("ground-truth")
    countries = reg.get("countries", {})

    by_status: dict[str, set[str]] = {
        "officially-assigned": set(),
        "user-assigned": set(),
        "exceptionally-reserved": set(),
        "withdrawn": set(),
    }
    for section in ("active", "withdrawn"):
        for e in countries.get(section, []):
            status = e.get("status")
            a2 = e.get("alpha_2")
            if status in by_status and a2:
                by_status[status].add(a2)

    pairs: list[tuple[str, frozenset[str], set[str]]] = [
        ("officially-assigned", parse_source.OFFICIAL_ISO3166_CODES, by_status["officially-assigned"]),
        ("withdrawn", parse_source.WITHDRAWN_ISO3166_CODES, by_status["withdrawn"]),
        ("exceptionally-reserved", parse_source.EXCEPTIONALLY_RESERVED_CODES, by_status["exceptionally-reserved"]),
        ("user-assigned", parse_source.USER_ASSIGNED_CODES, by_status["user-assigned"]),
    ]

    for label, expected, actual in pairs:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            r.error(f"{label}: MISSING from registry {missing}")
        if extra:
            r.error(f"{label}: EXTRA in registry {extra}")
        if not missing and not extra:
            r.note(f"{label}: {len(expected)} codes match")

    return r


# ============================================================
# Layer 6 — coverage
# ============================================================

def layer_coverage(
    reg: dict[str, Any],
    *,
    version_path: Path,
    changelog_path: Path,
    strict_count: bool,
) -> LayerResult:
    r = LayerResult("coverage")
    meta = reg.get("meta", {})
    countries = reg.get("countries", {})
    active = countries.get("active", [])
    withdrawn = countries.get("withdrawn", [])

    # meta.count_* must match actual.
    if meta.get("count_active") != len(active):
        r.error(f"meta.count_active ({meta.get('count_active')}) != len(active) ({len(active)})")
    if meta.get("count_withdrawn") != len(withdrawn):
        r.error(f"meta.count_withdrawn ({meta.get('count_withdrawn')}) != len(withdrawn) ({len(withdrawn)})")

    # Officially-assigned coverage.
    official = sum(1 for e in active if e.get("status") == "officially-assigned")
    if strict_count:
        if official != parse_source.EXPECTED_OFFICIAL_COUNT:
            r.error(f"officially-assigned count {official} != {parse_source.EXPECTED_OFFICIAL_COUNT} (--strict-count)")
    else:
        if official < parse_source.EXPECTED_OFFICIAL_COUNT:
            r.warn(f"officially-assigned count {official} < {parse_source.EXPECTED_OFFICIAL_COUNT}")

    # Version consistency (D7): VERSION ↔ meta.version ↔ CHANGELOG top heading.
    version_file = version_path.read_text(encoding="utf-8").strip() if version_path.exists() else None
    meta_version = meta.get("version")

    if version_file is None:
        r.warn(f"VERSION file not found: {version_path}")
    elif meta_version != version_file:
        r.error(f"VERSION ({version_file!r}) != meta.version ({meta_version!r})")
    else:
        r.note(f"VERSION matches meta.version: {version_file}")

    if changelog_path.exists():
        text = changelog_path.read_text(encoding="utf-8")
        m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
        if not m:
            r.warn(f"{changelog_path}: no top [x.y.z] heading found")
        else:
            top = m.group(1)
            if top == "Unreleased":
                r.warn(f"{changelog_path}: top heading is [Unreleased]")
            elif meta_version and top != meta_version:
                r.warn(f"CHANGELOG top heading ({top}) != meta.version ({meta_version})")
            else:
                r.note(f"CHANGELOG top heading matches meta.version: {top}")

    return r


# ============================================================
# Runner
# ============================================================

LayerFn = Callable[..., LayerResult]


def run_layers(
    reg: dict[str, Any],
    *,
    schema_path: Path,
    snapshot_path: Path,
    version_path: Path,
    changelog_path: Path,
    only: set[str] | None,
    skip: set[str] | None,
    strict_count: bool,
) -> list[LayerResult]:
    only = only or set()
    skip = skip or set()

    results: list[LayerResult] = []

    def should_run(name: str) -> bool:
        if only and name not in only:
            return False
        if name in skip:
            return False
        return True

    if should_run("schema"):
        results.append(layer_schema(reg, schema_path=schema_path))
    if should_run("integrity"):
        results.append(layer_integrity(reg))
    if should_run("business"):
        results.append(layer_business(reg))
    if should_run("cross-reference"):
        results.append(layer_cross_reference(reg, snapshot_path=snapshot_path))
    if should_run("ground-truth"):
        results.append(layer_ground_truth(reg))
    if should_run("coverage"):
        results.append(layer_coverage(
            reg,
            version_path=version_path,
            changelog_path=changelog_path,
            strict_count=strict_count,
        ))

    return results


# ============================================================
# Reporting
# ============================================================

def print_human(results: list[LayerResult], *, verbose: bool, quiet: bool) -> None:
    total = len(results)
    width = max((len(r.name) for r in results), default=10) + 2
    print("iso3166 validate")
    print()

    for i, r in enumerate(results, 1):
        marker = f"Layer {i}/{total}"
        print(f"  {marker}  {r.name:<{width}} {r.status}")

    if not quiet:
        for r in results:
            if r.status == "OK" and not verbose:
                continue
            print()
            print(f"  [{r.name}] {r.status}")
            if r.skip_reason:
                print(f"    skipped: {r.skip_reason}")
            for note in r.notes:
                if verbose or r.status != "OK":
                    print(f"    note: {note}")
            for w in r.warnings:
                print(f"    warn: {w}")
            for e in r.errors:
                print(f"    ERROR: {e}")

    counts = Counter(r.status for r in results)
    print()
    print(
        f"Summary: {counts.get('OK', 0)} OK, "
        f"{counts.get('WARN', 0)} WARN, "
        f"{counts.get('FAIL', 0)} FAIL, "
        f"{counts.get('SKIP', 0)} SKIP"
    )


def print_json(results: list[LayerResult], exit_code: int) -> None:
    counts = Counter(r.status for r in results)
    doc = {
        "layers": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "ok": counts.get("OK", 0),
            "warn": counts.get("WARN", 0),
            "fail": counts.get("FAIL", 0),
            "skip": counts.get("SKIP", 0),
        },
        "exit_code": exit_code,
    }
    print(json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True))


def compute_exit_code(results: list[LayerResult]) -> int:
    for r in results:
        if r.name == "schema" and r.status == "FAIL":
            return 3
    for r in results:
        if r.status == "FAIL":
            return 1
    return 0


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="validate",
        description="Six-layer validator for the ISO 3166 registry.",
    )
    p.add_argument(
        "registry",
        type=Path,
        nargs="?",
        default=Path("iso3166.json"),
        help="Path to the registry (default: iso3166.json).",
    )
    p.add_argument(
        "--schema",
        type=Path,
        default=Path("schema.json"),
        help="Path to the JSON Schema (default: schema.json).",
    )
    p.add_argument(
        "--snapshot",
        type=Path,
        default=Path("tools/iso4217_snapshot.json"),
        help="Path to the ISO 4217 snapshot (default: tools/iso4217_snapshot.json).",
    )
    p.add_argument(
        "--version-file",
        type=Path,
        default=Path("VERSION"),
        help="Path to the VERSION file (default: VERSION).",
    )
    p.add_argument(
        "--changelog",
        type=Path,
        default=Path("CHANGELOG.md"),
        help="Path to the CHANGELOG (default: CHANGELOG.md).",
    )
    p.add_argument(
        "--only",
        action="append",
        choices=LAYER_NAMES,
        default=None,
        help="Run only the named layer. May be repeated.",
    )
    p.add_argument(
        "--skip",
        action="append",
        choices=LAYER_NAMES,
        default=None,
        help="Skip the named layer. May be repeated.",
    )
    p.add_argument(
        "--strict-count",
        action="store_true",
        help="Fail if the officially-assigned count is not exactly 249.",
    )
    p.add_argument("--json", action="store_true", dest="json_output",
                   help="Emit machine-readable JSON.")
    p.add_argument("--verbose", action="store_true",
                   help="Show notes even for passing layers.")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress per-layer detail; show only the summary.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    reg = load_registry(args.registry)

    results = run_layers(
        reg,
        schema_path=args.schema,
        snapshot_path=args.snapshot,
        version_path=args.version_file,
        changelog_path=args.changelog,
        only=set(args.only) if args.only else None,
        skip=set(args.skip) if args.skip else None,
        strict_count=args.strict_count,
    )

    exit_code = compute_exit_code(results)

    if args.json_output:
        print_json(results, exit_code)
    else:
        print_human(results, verbose=args.verbose, quiet=args.quiet)

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
