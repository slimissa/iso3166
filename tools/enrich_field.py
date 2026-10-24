#!/usr/bin/env python3
"""
tools/enrich_field.py

Populate a list-typed field on officially-assigned entries in
iso3166.json.

Supported fields:

    currency_codes   list of ISO 4217 alpha-3 codes, e.g. ["USD"]
    calling_codes    list of ITU-T E.164 prefixes, e.g. ["1"], ["1-340"]
    tlds             list of IANA ccTLDs, e.g. [".us"]

Each field has a validation pattern, a snapshot file listing valid
values, and a source URL template. The tool refuses any value not in
the snapshot.

The tool only writes to the target field, last_verified, and note on
the target entry. It does not touch meta, does not reorder entries,
and does not modify other fields.

Modes
-----

Set one field on one entry:

    python3 tools/enrich_field.py US --field currency_codes --values USD
    python3 tools/enrich_field.py US --field calling_codes --values 1
    python3 tools/enrich_field.py US --field tlds --values .us

    # Multiple values are comma-separated.
    python3 tools/enrich_field.py PA --field currency_codes --values PAB,USD

Apply a TSV batch. Two tab-separated columns, headerless:

    alpha_2 <TAB> value1,value2,value3

Blank lines and lines starting with # are ignored.

    python3 tools/enrich_field.py --field currency_codes --from-file /tmp/batch.tsv

Audit:

    python3 tools/enrich_field.py --field currency_codes --list-missing
    python3 tools/enrich_field.py --field currency_codes --list-all
    python3 tools/enrich_field.py --field currency_codes --check

Exit codes:
    0  Success.
    1  Data error (--check found missing values, bad input).
    2  Usage error (missing args, unreadable snapshot).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from patterns import CALLING_CODE_RE  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if not (PROJECT_ROOT / "iso3166.json").is_file():
    print(
        f"error: {PROJECT_ROOT / 'iso3166.json'} not found; "
        "this tool must run from a repository checkout.",
        file=sys.stderr,
    )
    sys.exit(2)


REGISTRY = PROJECT_ROOT / "iso3166.json"


@dataclass(frozen=True)
class FieldConfig:
    """One enrichable list field."""
    name: str
    item_pattern: str
    snapshot_path: Path
    snapshot_key: str
    source_template: str
    describe: str
    is_scalar: bool = False
    # alpha_2 codes for which a null value is correct, not a gap.
    legitimately_null: frozenset[str] = frozenset()
    # When set, the field is required only on entries whose subregion is in
    # this set; every other entry is legitimately null. M49 defines
    # intermediate regions under two subregions only.
    required_for_subregions: frozenset[str] | None = None


FIELDS: dict[str, FieldConfig] = {
    "currency_codes": FieldConfig(
        name="currency_codes",
        item_pattern=r"^[A-Z]{3}$",
        snapshot_path=PROJECT_ROOT / "tools/iso4217_snapshot.json",
        snapshot_key="active",
        # Per-entry ISO OBP page.
        source_template="https://www.iso.org/obp/ui/#iso:code:3166:{code}",
        describe="ISO 4217 alpha-3 currency codes",
    ),
    "calling_codes": FieldConfig(
        name="calling_codes",
        item_pattern=CALLING_CODE_RE.pattern,
        snapshot_path=PROJECT_ROOT / "tools/itu_calling_code_snapshot.json",
        snapshot_key="codes",
        # One URL for the whole ITU list.
        source_template="https://www.itu.int/oth/T02020000E8/en",
        describe="ITU-T E.164 calling codes",
    ),
    "borders": FieldConfig(
        name="borders",
        item_pattern=r"^[A-Z]{2}$",
        snapshot_path=PROJECT_ROOT / "iso3166.json",
        snapshot_key=None,
        source_template="https://www.cia.gov/the-world-factbook/countries/{code}/",
        describe="adjacent country alpha-2 codes",
    ),
    "languages": FieldConfig(
        name="languages",
        item_pattern=r"^[a-z]{3}$",
        snapshot_path=PROJECT_ROOT / "tools/iso639_3_snapshot.json",
        snapshot_key="languages",
        source_template="https://www.cia.gov/the-world-factbook/countries/{code}/",
        describe="ISO 639-3 language codes",
    ),
    "tlds": FieldConfig(
        name="tlds",
        item_pattern=r"^\.[a-z]{2,}$",
        snapshot_path=PROJECT_ROOT / "tools/iana_tld_snapshot.json",
        snapshot_key="tlds",
        source_template="https://www.iana.org/domains/root/db",
        describe="IANA country-code top-level domains",
    ),
    "subregion": FieldConfig(
        name="subregion",
        item_pattern=r"^[A-Za-z][A-Za-z \-]*$",
        snapshot_path=PROJECT_ROOT / "tools/m49_subregion_snapshot.json",
        snapshot_key="subregions",
        source_template="https://unstats.un.org/unsd/methodology/m49/",
        describe="UN M49 subregion name",
        is_scalar=True,
        # docs/ENRICHMENT.md: M49 assigns no subregion to Antarctica or Taiwan.
        legitimately_null=frozenset({"AQ", "TW"}),
    ),
    "intermediate_region": FieldConfig(
        name="intermediate_region",
        item_pattern=r"^[A-Za-z][A-Za-z \-]*$",
        snapshot_path=PROJECT_ROOT / "tools/m49_intermediate_region_snapshot.json",
        snapshot_key="intermediate_regions",
        source_template="https://unstats.un.org/unsd/methodology/m49/",
        describe="UN M49 intermediate region name",
        is_scalar=True,
        # docs/ENRICHMENT.md: populated only where M49 defines one, which is
        # under these two subregions; everywhere else it is null.
        required_for_subregions=frozenset(
            {"Sub-Saharan Africa", "Latin America and the Caribbean"}
        ),
    ),
}


class FatalError(SystemExit):
    def __init__(self, message: str, code: int = 2) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


# ----------------------------------------------------------------
# IO
# ----------------------------------------------------------------

def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FatalError(f"registry not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{path}: invalid JSON: {exc}") from exc


def write_registry(path: Path, data: dict[str, Any]) -> None:
    """Deterministic write: sorted keys, 2-space indent, LF, trailing newline."""
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def load_snapshot(cfg: FieldConfig) -> frozenset[str]:
    if not cfg.snapshot_path.exists():
        raise FatalError(f"snapshot not found: {cfg.snapshot_path}")

    if cfg.snapshot_key is None:
        # Special case: borders validates against the registry's own
        # active alpha-2 codes. user-assigned and exceptionally-reserved
        # entries are valid border targets — Kosovo (XK) borders four
        # officially-assigned countries.
        reg = load_registry(cfg.snapshot_path)
        return frozenset(
            e["alpha_2"] for e in reg["countries"]["active"]
            if e["status"] in ("officially-assigned",
                                "user-assigned",
                                "exceptionally-reserved")
        )

    data = json.loads(cfg.snapshot_path.read_text(encoding="utf-8"))
    values = data.get(cfg.snapshot_key)
    if not isinstance(values, list):
        raise FatalError(
            f"{cfg.snapshot_path}: key {cfg.snapshot_key!r} is not a list"
        )
    return frozenset(values)


def validate_values(
    values: list[str],
    cfg: FieldConfig,
    known: frozenset[str],
) -> None:
    """Raise FatalError if any value fails its pattern or is not in the
    snapshot."""
    pattern = re.compile(cfg.item_pattern)
    seen: set[str] = set()

    for v in values:
        if not isinstance(v, str) or not v.strip():
            raise FatalError(f"{cfg.name}: empty value")
        if not pattern.match(v):
            raise FatalError(
                f"{cfg.name}: value {v!r} does not match {cfg.item_pattern}"
            )
        if v in seen:
            raise FatalError(f"{cfg.name}: duplicate value {v!r}")
        seen.add(v)
        if v not in known:
            raise FatalError(
                f"{cfg.name}: value {v!r} is not in {cfg.snapshot_path}"
            )


def find_active(reg: dict[str, Any], code: str) -> dict[str, Any]:
    code = code.upper()
    for entry in reg["countries"]["active"]:
        if entry["alpha_2"] == code:
            return entry
    raise FatalError(f"{code}: not present in countries.active")


def record_source(existing: str | None, source: str, field: str) -> str:
    """Append or replace this field's citation line in the note field.

    The line is `<field> source: <url>`. Only a previous line for the
    SAME field is replaced, so enriching currency_codes does not remove
    the citation written when calling_codes was enriched. Every other
    note line (other fields' citations, prose, and any legacy bare
    `source:` line from before v1.7.2) is preserved untouched.
    Idempotent: applying the same source twice does not duplicate it.
    """
    citation = f"{field} source: {source}"
    own_line = re.compile(rf"^{re.escape(field)} source:.*$")

    if not existing:
        return citation

    kept = [line for line in existing.splitlines()
            if not own_line.match(line)]
    kept.append(citation)
    return "\n".join(kept)


# ----------------------------------------------------------------
# Apply
# ----------------------------------------------------------------

def apply_one(
    reg: dict[str, Any],
    cfg: FieldConfig,
    alpha_2: str,
    values: list[str],
    *,
    known: frozenset[str],
    today: str,
) -> dict[str, Any]:
    """Set the field on one entry. Returns a summary dict for logging."""
    if not values and cfg.name not in ("currency_codes", "tlds", "languages", "borders"):
        raise FatalError(f"{alpha_2}: at least one value required")

    validate_values(values, cfg, known)

    entry = find_active(reg, alpha_2)

    if (entry["status"] != "officially-assigned"
            and cfg.name not in ("subregion", "intermediate_region", "borders")):
        raise FatalError(
            f"{entry['alpha_2']}: status is {entry['status']!r}; "
            f"only officially-assigned entries are enriched"
        )

    before = entry.get(cfg.name)
    if cfg.name == "borders" and entry["alpha_2"] in values:
        raise FatalError(
            f"{entry['alpha_2']}: borders cannot contain self"
        )

    if cfg.is_scalar:
        if len(values) != 1:
            raise FatalError(
                f"{cfg.name}: exactly one value required for a scalar "
                f"field, got {len(values)}"
            )
        entry[cfg.name] = values[0]
        written = values[0]
    else:
        entry[cfg.name] = sorted(values)
        written = sorted(values)
    entry["last_verified"] = today

    source = cfg.source_template.format(code=entry["alpha_2"])
    entry["note"] = record_source(entry.get("note"), source, cfg.name)

    return {
        "alpha_2": entry["alpha_2"],
        "field": cfg.name,
        "before": before,
        "after": written,
        "source": source,
    }


# ----------------------------------------------------------------
# Modes
# ----------------------------------------------------------------

def mode_set(args: argparse.Namespace) -> int:
    cfg = FIELDS[args.field]
    values = [v.strip() for v in args.values.split(",") if v.strip()]
    reg = load_registry(args.registry)
    known = load_snapshot(cfg)
    today = date.today().isoformat()

    summary = apply_one(
        reg, cfg, args.code, values, known=known, today=today,
    )

    if not args.dry_run:
        write_registry(args.registry, reg)

    verb = "would set" if args.dry_run else "set"
    print(f"{verb} {summary['alpha_2']}.{summary['field']} = "
          f"{summary['after']!r}")
    print(f"  source: {summary['source']}")
    if summary["before"] and summary["before"] != summary["after"]:
        print(f"  (was: {summary['before']})")
    return 0


def mode_from_file(args: argparse.Namespace) -> int:
    cfg = FIELDS[args.field]
    if not args.from_file.exists():
        raise FatalError(f"batch file not found: {args.from_file}")

    rows: list[tuple[str, list[str]]] = []
    for lineno, raw in enumerate(
        args.from_file.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise FatalError(
                f"{args.from_file}:{lineno}: expected 2 tab-separated "
                f"fields (alpha_2, comma-separated values), "
                f"got {len(parts)}"
            )
        code = parts[0].strip().upper()
        raw_values = parts[1].strip()
        if not code:
            raise FatalError(f"{args.from_file}:{lineno}: empty alpha_2")
        if raw_values == "-":
            values: list[str] = []  # known: no value for this field
        else:
            values = [v.strip() for v in raw_values.split(",") if v.strip()]
            if not values:
                raise FatalError(f"{args.from_file}:{lineno}: empty values")
        rows.append((code, values))

    if not rows:
        raise FatalError(f"{args.from_file}: no entries")

    reg = load_registry(args.registry)
    known = load_snapshot(cfg)
    today = date.today().isoformat()

    summaries: list[dict[str, Any]] = []
    for code, values in rows:
        summaries.append(
            apply_one(reg, cfg, code, values, known=known, today=today)
        )

    if not args.dry_run:
        write_registry(args.registry, reg)

    verb = "would set" if args.dry_run else "set"
    print(f"{verb} {len(summaries)} entrie(s):")
    for s in summaries:
        rendered = s["after"] if s["after"] else "(empty)"
        print(f"  {s['alpha_2']}  {s['field']} = {rendered!r}")
    return 0



def _active_assigned(reg: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in reg["countries"]["active"]
            if e["status"] == "officially-assigned"]


def _requires_value(cfg: FieldConfig, entry: dict[str, Any]) -> bool:
    """True if a null cfg.name on this entry is a defect, not a legitimate null."""
    if entry["alpha_2"] in cfg.legitimately_null:
        return False
    if cfg.required_for_subregions is not None:
        return entry.get("subregion") in cfg.required_for_subregions
    return True


def _missing(cfg: FieldConfig, assigned: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in assigned
            if e.get(cfg.name) is None and _requires_value(cfg, e)]


def mode_list_missing(args: argparse.Namespace) -> int:
    cfg = FIELDS[args.field]
    reg = load_registry(args.registry)
    assigned = _active_assigned(reg)
    missing = _missing(cfg, assigned)

    if not missing:
        nulls = sum(1 for e in assigned if e.get(cfg.name) is None)
        suffix = f" ({nulls} legitimately null)" if nulls else ""
        print(f"all {len(assigned)} officially-assigned entries have "
              f"{cfg.name}{suffix}", file=sys.stderr)
        return 0

    for e in missing:
        print(f"{e['alpha_2']}\t{e['name']}")
    print(f"\n{len(missing)} missing", file=sys.stderr)
    return 0


def mode_list_all(args: argparse.Namespace) -> int:
    cfg = FIELDS[args.field]
    reg = load_registry(args.registry)
    for e in _active_assigned(reg):
        if cfg.is_scalar:
            v = e.get(cfg.name)
            display = v if v else "—"
        else:
            values = e.get(cfg.name) or []
            display = ",".join(values) if values else "—"
        print(f"{e['alpha_2']}\t{display}")
    return 0


def mode_check(args: argparse.Namespace) -> int:
    cfg = FIELDS[args.field]
    reg = load_registry(args.registry)
    assigned = _active_assigned(reg)
    missing = _missing(cfg, assigned)

    if missing:
        print(
            f"FAIL: {len(missing)} of {len(assigned)} officially-assigned "
            f"entries lack {cfg.name}:",
            file=sys.stderr,
        )
        for e in missing:
            print(f"  {e['alpha_2']}  {e['name']}", file=sys.stderr)
        return 1

    nulls = [e for e in assigned if e.get(cfg.name) is None]
    if nulls:
        print(f"OK: {len(assigned) - len(nulls)} of {len(assigned)} "
              f"officially-assigned entries have {cfg.name}; "
              f"{len(nulls)} legitimately null")
    else:
        print(f"OK: {len(assigned)} of {len(assigned)} officially-assigned "
              f"entries have {cfg.name}")
    return 0


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="enrich_field",
        description=(
            "Populate a list-typed field on officially-assigned entries. "
            "Only writes the target field, last_verified, and note."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Supported fields: "
            + ", ".join(sorted(FIELDS.keys()))
            + "\n\nExamples:\n"
            "  python3 tools/enrich_field.py US --field currency_codes --values USD\n"
            "  python3 tools/enrich_field.py US --field calling_codes --values 1\n"
            "  python3 tools/enrich_field.py US --field tlds --values .us\n"
            "  python3 tools/enrich_field.py --field currency_codes --from-file /tmp/batch.tsv\n"
            "  python3 tools/enrich_field.py --field tlds --check\n"
        ),
    )
    p.add_argument("--registry", type=Path, default=REGISTRY,
                   help=f"Path to the registry (default: {REGISTRY}).")
    p.add_argument("--field", required=True, choices=sorted(FIELDS.keys()),
                   help="Which list field to populate.")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would change without writing.")

    p.add_argument("code", nargs="?",
                   help="alpha-2 code (case-insensitive).")
    p.add_argument("--values", default=None,
                   help="Comma-separated values to set on the entry.")

    group = p.add_mutually_exclusive_group()
    group.add_argument("--from-file", type=Path, metavar="TSV",
                       help="Apply a TSV batch: alpha_2<TAB>v1,v2,v3")
    group.add_argument("--list-missing", action="store_true",
                       help="Print entries lacking this field.")
    group.add_argument("--list-all", action="store_true",
                       help="Print every officially-assigned entry and "
                            "its current values.")
    group.add_argument("--check", action="store_true",
                       help="Exit 0 only if every officially-assigned "
                            "entry has this field.")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.code:
        args.code = args.code.upper()

    if args.from_file is not None:
        return mode_from_file(args)
    if args.list_missing:
        return mode_list_missing(args)
    if args.list_all:
        return mode_list_all(args)
    if args.check:
        return mode_check(args)

    if args.code and args.values:
        return mode_set(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)