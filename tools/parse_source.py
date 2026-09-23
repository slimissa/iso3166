#!/usr/bin/env python3
"""
tools/parse_source.py

Frozen ground-truth code sets for the ISO 3166 registry.

The sets below are the source of truth for which codes belong in the
registry. They are maintained by hand, sourced from ISO's own published
lists, and updated only when ISO publishes an amendment. Every change
to these sets requires:

  1. A first-party citation (ISO 3166-1 online browsing platform,
     ISO 3166-3 standard, or the UN M49 export).
  2. A CHANGELOG entry.
  3. A patch release.

Why a literal, not a derived set
--------------------------------
If this module read iso3166.json and produced the code set at import
time, then tools/validate.py checking iso3166.json against that set
would be checking the file against itself. That is a no-op, and false
confidence is worse than no check.

Instead, the sets below are frozen Python literals. They were derived
once, from first-party sources, reviewed by a human, and committed.
They do not change unless a human edits this file. The --bootstrap
mode emits the literals from a registry file; --audit re-derives them
from sources and compares; --verify checks a registry file against
them.

Sourcing
--------
OFFICIAL_ISO3166_CODES
    249 officially-assigned ISO 3166-1 alpha-2 codes, per ISO 3166-1:2020.
    Cross-checked against the UN M49 overview export, which contains 248
    of the 249 (it omits TW; see docs/PROVENANCE.md, discrepancy log).

WITHDRAWN_ISO3166_CODES
    ISO 3166-3:2013 withdrawn alpha-2 codes. The initial population is
    the representative set committed in Phase 1; the full set is
    completed in v1.1.0.

EXCEPTIONALLY_RESERVED_CODES
    ISO 3166-1 exceptionally-reserved alpha-2 codes in production use
    in this registry. Currently UK and EU. ISO defines more; they are
    added on discovery (see docs/PROVENANCE.md).

USER_ASSIGNED_CODES
    ISO 3166-1 user-assigned alpha-2 codes in production use. Currently
    XK. The user-assigned ranges (AA, QM-QZ, XA-XZ, ZZ) are documented
    in docs/PROVENANCE.md, not enumerated here, because they are ranges
    and not specific codes.

Overlap note
------------
AI and SK appear in BOTH OFFICIAL_ISO3166_CODES and
WITHDRAWN_ISO3166_CODES. They were reassigned by ISO: AI was French
Afars and Issas (withdrawn 1977, replaced by DJ), then became Anguilla;
SK was Sikkim (withdrawn 1975, replaced by IN), then became Slovakia.
Both are correct in both sets. As a result, ALL_KNOWN_CODES has 265
members, not the 267 that a naive sum would give.

SU is in WITHDRAWN, not EXCEPTIONALLY_RESERVED. ISO 3166-1 lists SU as
exceptionally reserved AND ISO 3166-3 lists it as withdrawn; this
registry resolves in favor of the withdrawn treatment to match the
data.

Usage
-----
Audit the frozen sets against the sources:

    python3 tools/parse_source.py --audit \\
        --m49 /tmp/iso3166-sources/un_m49.csv \\
        --exceptions tools/initial_exceptions.json

Verify a registry file against the frozen sets:

    python3 tools/parse_source.py --verify iso3166.json

Bootstrap the literals from a registry file (used to regenerate this
file's sets when a code is added; review the diff before committing):

    python3 tools/parse_source.py --bootstrap iso3166.json

All modes exit:
    0  All checks passed.
    1  Discrepancy found.
    2  Usage error (missing or unreadable input).

All modes are read-only and idempotent. They are suitable for CI:
--audit on every push (cheap, catches drift in the frozen sets), and
--verify in the release gate (catches a registry file that no longer
matches the frozen sets).

Do not scrape
-------------
Third-party aggregators (Wikipedia, countrycode.org, blog posts, CSVs
from unrelated projects) are not acceptable as the origin of a code.
If a code cannot be traced to ISO, it does not belong in this file.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


# ============================================================
# Frozen ground-truth sets
# ============================================================
#
# Do not edit these by hand without a first-party citation. See the
# module docstring for the update procedure and the AI/SK overlap note.
#
# The --bootstrap command regenerates these four literals from a
# registry file. Use it when adding a code, not to regenerate the
# whole file routinely. Review the diff before committing.

OFFICIAL_ISO3166_CODES: frozenset[str] = frozenset({
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT",
    "AU", "AW", "AX", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI",
    "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BV", "BW", "BY",
    "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
    "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
    "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK",
    "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL",
    "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
    "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR",
    "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN",
    "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS",
    "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
    "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW",
    "MX", "MY", "MZ", "NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP",
    "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM",
    "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
    "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM",
    "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF",
    "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW",
    "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
})

WITHDRAWN_ISO3166_CODES: frozenset[str] = frozenset({
    "AI", "AN", "BU", "CS", "CT", "DD", "DY", "FQ", "HV", "JT", "MI", "NH",
    "NQ", "NT", "PC", "PZ", "RH", "SK", "SU", "TP", "VD", "WK", "YD", "YU",
    "ZR",
})

EXCEPTIONALLY_RESERVED_CODES: frozenset[str] = frozenset({
    "EU", "UK",
})

USER_ASSIGNED_CODES: frozenset[str] = frozenset({
    "XK",
})


# ============================================================
# Derived constants
# ============================================================

EXPECTED_OFFICIAL_COUNT = 249

ALL_KNOWN_CODES: frozenset[str] = (
    OFFICIAL_ISO3166_CODES
    | WITHDRAWN_ISO3166_CODES
    | EXCEPTIONALLY_RESERVED_CODES
    | USER_ASSIGNED_CODES
)


# ============================================================
# Diagnostics
# ============================================================

class FatalError(SystemExit):
    """Raised for user-facing fatal errors. Always exits with a specific code."""

    def __init__(self, message: str, code: int = 1) -> None:
        print(f"error: {message}", file=sys.stderr)
        super().__init__(code)


def info(message: str, *, quiet: bool = False) -> None:
    if not quiet:
        print(message, file=sys.stderr)


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


# ============================================================
# Shared IO helpers
# ============================================================

def _detect_delimiter(sample: str) -> str:
    """Return the delimiter the CSV header is using. Prefers comma, falls back to semicolon."""
    first_line = ""
    for line in sample.splitlines():
        if line.strip():
            first_line = line
            break
    if not first_line:
        return ","
    commas = first_line.count(",")
    semis = first_line.count(";")
    tabs = first_line.count("\t")
    best = max((commas, ","), (semis, ";"), (tabs, "\t"))
    return best[1] if best[0] > 0 else ","


def _normalize_header(header: str) -> str:
    return " ".join(header.strip().lower().split())


def _resolve_column(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    by_norm = {_normalize_header(h): h for h in fieldnames}
    for c in candidates:
        key = _normalize_header(c)
        if key in by_norm:
            return by_norm[key]
    return None


def _status_map(registry_path: Path) -> dict[str, set[str]]:
    """Read a registry file and return {status: {alpha_2, ...}}."""
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FatalError(f"registry not found: {registry_path}", code=2)
    except json.JSONDecodeError as exc:
        raise FatalError(f"{registry_path}: invalid JSON: {exc}", code=1)

    result: dict[str, set[str]] = {
        "officially-assigned": set(),
        "user-assigned": set(),
        "exceptionally-reserved": set(),
        "withdrawn": set(),
    }

    countries = data.get("countries", {})
    for section in ("active", "withdrawn"):
        for entry in countries.get(section, []):
            status = entry.get("status")
            a2 = entry.get("alpha_2")
            if not status or not a2:
                continue
            result.setdefault(status, set()).add(a2.upper())

    return result


# ============================================================
# Sources: UN M49 and exceptions file
# ============================================================

def _read_m49_codes(path: Path) -> set[str]:
    """Return the alpha-2 codes from a UN M49 export."""
    if not path.exists():
        raise FatalError(f"UN M49 CSV not found: {path}", code=2)
    if not path.is_file():
        raise FatalError(f"UN M49 path is not a regular file: {path}", code=2)

    try:
        sample = path.read_text(encoding="utf-8-sig")[:8192]
    except OSError as exc:
        raise FatalError(f"cannot read UN M49 CSV: {exc}", code=2) from exc

    if sample.lstrip().startswith("<"):
        raise FatalError(
            f"{path}: looks like HTML, not CSV.\n"
            f"  The UN M49 'Download' button is JavaScript-triggered; curl on\n"
            f"  the overview page returns the HTML page. Open the page in a\n"
            f"  browser, click Download -> CSV, and use the downloaded file.",
            code=1,
        )

    delimiter = _detect_delimiter(sample)
    info(f"  M49 delimiter: {delimiter!r}")

    codes: set[str] = set()
    try:
        handle = path.open(encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise FatalError(f"cannot open UN M49 CSV: {exc}", code=2) from exc

    with handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise FatalError(f"{path}: empty CSV (no header row)", code=1)

        col = _resolve_column(
            reader.fieldnames,
            ("ISO-alpha2 Code", "ISO_alpha2_Code", "Alpha-2 Code", "alpha-2"),
        )
        if col is None:
            raise FatalError(
                f"{path}: no alpha-2 column found.\n"
                f"  tried: ISO-alpha2 Code, ISO_alpha2_Code, Alpha-2 Code, alpha-2\n"
                f"  available: {reader.fieldnames}",
                code=1,
            )

        for row in reader:
            a2 = (row.get(col) or "").strip().upper()
            if a2:
                codes.add(a2)

    return codes


def _read_exceptions(path: Path) -> dict[str, set[str]]:
    """Return the codes from an exceptions file, grouped by status."""
    if not path.exists():
        raise FatalError(f"exceptions file not found: {path}", code=2)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FatalError(f"{path}: invalid JSON: {exc}", code=1) from exc
    except OSError as exc:
        raise FatalError(f"cannot read exceptions file: {exc}", code=2) from exc

    if not isinstance(data, dict):
        raise FatalError(f"{path}: top-level value must be an object", code=1)

    result: dict[str, set[str]] = {
        "officially-assigned": set(),
        "user-assigned": set(),
        "exceptionally-reserved": set(),
        "withdrawn": set(),
    }

    for a2 in (data.get("officially_assigned") or {}):
        result["officially-assigned"].add(a2.upper())
    for a2 in (data.get("user_assigned") or {}):
        result["user-assigned"].add(a2.upper())
    for a2 in (data.get("exceptionally_reserved") or {}):
        result["exceptionally-reserved"].add(a2.upper())
    for entry in (data.get("withdrawn") or []):
        a2 = entry.get("alpha_2") if isinstance(entry, dict) else None
        if a2:
            result["withdrawn"].add(a2.upper())

    return result


# ============================================================
# Reporting
# ============================================================

def _report_discrepancy(
    label: str,
    expected: set[str],
    actual: set[str],
) -> bool:
    """Print any difference between two sets. Return True if there is one."""
    missing = expected - actual
    extra = actual - expected
    if not missing and not extra:
        print(f"  {label:<38} OK ({len(expected)} codes)")
        return False
    if missing:
        print(f"  {label:<38} MISSING {sorted(missing)}")
    if extra:
        print(f"  {label:<38} EXTRA {sorted(extra)}")
    return True


# ============================================================
# Command: --bootstrap
# ============================================================

def _format_set_block(name: str, values: set[str]) -> str:
    """Return the Python literal for a sorted frozenset, wrapped to ~76 cols."""
    items = sorted(values)
    if not items:
        return f"{name}: frozenset[str] = frozenset()"

    lines: list[str] = []
    current = "    "
    for item in items:
        token = f'"{item}", '
        if len(current) + len(token) > 76:
            lines.append(current.rstrip())
            current = "    "
        current += token
    if current.strip():
        lines.append(current.rstrip())

    body = "\n".join(lines)
    return f"{name}: frozenset[str] = frozenset({{\n{body}\n}})"


def cmd_bootstrap(registry_path: Path) -> int:
    """Print the four frozen sets as Python literals."""
    by_status = _status_map(registry_path)

    blocks = [
        _format_set_block("OFFICIAL_ISO3166_CODES", by_status["officially-assigned"]),
        _format_set_block("WITHDRAWN_ISO3166_CODES", by_status["withdrawn"]),
        _format_set_block("EXCEPTIONALLY_RESERVED_CODES", by_status["exceptionally-reserved"]),
        _format_set_block("USER_ASSIGNED_CODES", by_status["user-assigned"]),
    ]
    print("\n\n".join(blocks))
    return 0


# ============================================================
# Command: --audit
# ============================================================

def cmd_audit(m49_path: Path, exceptions_path: Path) -> int:
    """Compare the frozen sets against the sources they were derived from."""
    print("Audit: frozen sets vs. sources")
    print()

    if not OFFICIAL_ISO3166_CODES:
        raise FatalError(
            "OFFICIAL_ISO3166_CODES is empty. Run --bootstrap and paste the "
            "output into tools/parse_source.py.",
            code=1,
        )

    any_discrepancy = False

    info(f"Reading UN M49: {m49_path}")
    m49_codes = _read_m49_codes(m49_path)
    info(f"  {len(m49_codes)} alpha-2 codes in M49")

    info(f"Reading exceptions: {exceptions_path}")
    exceptions = _read_exceptions(exceptions_path)

    # --- Official codes: M49 ∪ additions, minus reserved/user ---
    # Every M49 code that is not exceptionally-reserved or user-assigned
    # must be in OFFICIAL. Then every officially_assigned exception that
    # is not in M49 must also be in OFFICIAL (these are the additions,
    # e.g. TW).
    expected_official = (
        m49_codes | exceptions["officially-assigned"]
    ) - (EXCEPTIONALLY_RESERVED_CODES | USER_ASSIGNED_CODES)

    any_discrepancy |= _report_discrepancy(
        "frozen OFFICIAL vs. sources",
        expected_official,
        set(OFFICIAL_ISO3166_CODES),
    )

    # Show the additions explicitly. The reader wants to see TW named.
    additions = exceptions["officially-assigned"] - m49_codes
    print(f"  {'M49-absent additions':<38} {sorted(additions) or 'none'}")

    print()

    # --- Other statuses: compare against the exceptions file ---
    any_discrepancy |= _report_discrepancy(
        "frozen WITHDRAWN vs. exceptions",
        set(WITHDRAWN_ISO3166_CODES),
        exceptions["withdrawn"],
    )
    any_discrepancy |= _report_discrepancy(
        "frozen EXCEPTIONAL vs. exceptions",
        set(EXCEPTIONALLY_RESERVED_CODES),
        exceptions["exceptionally-reserved"],
    )
    any_discrepancy |= _report_discrepancy(
        "frozen USER vs. exceptions",
        set(USER_ASSIGNED_CODES),
        exceptions["user-assigned"],
    )

    print()
    print(f"  {'frozen OFFICIAL count':<38} {len(OFFICIAL_ISO3166_CODES)}")
    print(f"  {'expected count':<38} {EXPECTED_OFFICIAL_COUNT}")
    if len(OFFICIAL_ISO3166_CODES) != EXPECTED_OFFICIAL_COUNT:
        print("  ^^ MISMATCH")
        any_discrepancy = True

    print()
    if any_discrepancy:
        print("audit: DISCREPANCIES FOUND", file=sys.stderr)
        return 1
    print("audit: OK")
    return 0


# ============================================================
# Command: --verify
# ============================================================

def cmd_verify(registry_path: Path) -> int:
    """Check that a registry file matches the frozen sets exactly."""
    print(f"Verify: {registry_path}")
    print()

    if not OFFICIAL_ISO3166_CODES:
        raise FatalError(
            "OFFICIAL_ISO3166_CODES is empty. Run --bootstrap and paste the "
            "output into tools/parse_source.py.",
            code=1,
        )

    by_status = _status_map(registry_path)

    any_discrepancy = False
    any_discrepancy |= _report_discrepancy(
        "officially-assigned",
        set(OFFICIAL_ISO3166_CODES),
        by_status["officially-assigned"],
    )
    any_discrepancy |= _report_discrepancy(
        "withdrawn",
        set(WITHDRAWN_ISO3166_CODES),
        by_status["withdrawn"],
    )
    any_discrepancy |= _report_discrepancy(
        "exceptionally-reserved",
        set(EXCEPTIONALLY_RESERVED_CODES),
        by_status["exceptionally-reserved"],
    )
    any_discrepancy |= _report_discrepancy(
        "user-assigned",
        set(USER_ASSIGNED_CODES),
        by_status["user-assigned"],
    )

    print()
    if any_discrepancy:
        print("verify: DISCREPANCIES FOUND", file=sys.stderr)
        return 1
    print("verify: OK")
    return 0


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="parse_source",
        description=(
            "Frozen ground-truth code sets for the ISO 3166 registry. "
            "Bootstrap, audit, or verify."
        ),
    )

    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--bootstrap",
        metavar="REGISTRY",
        type=Path,
        help="Print the four frozen sets as Python literals for pasting "
             "into this file.",
    )
    group.add_argument(
        "--audit",
        action="store_true",
        help="Compare the frozen sets against UN M49 and the exceptions "
             "file. Requires --m49.",
    )
    group.add_argument(
        "--verify",
        metavar="REGISTRY",
        type=Path,
        help="Check a registry file against the frozen sets exactly.",
    )

    p.add_argument(
        "--m49",
        metavar="PATH",
        type=Path,
        help="Path to the UN M49 overview CSV (required with --audit).",
    )
    p.add_argument(
        "--exceptions",
        metavar="PATH",
        type=Path,
        default=Path("tools/initial_exceptions.json"),
        help="Path to the exceptions file "
             "(default: tools/initial_exceptions.json).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational messages on stderr.",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.bootstrap is not None:
        return cmd_bootstrap(args.bootstrap)

    if args.audit:
        if args.m49 is None:
            raise FatalError("--audit requires --m49 PATH", code=2)
        return cmd_audit(args.m49, args.exceptions)

    if args.verify is not None:
        return cmd_verify(args.verify)

    raise FatalError("no command given", code=2)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FatalError as exc:
        sys.exit(exc.code)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
