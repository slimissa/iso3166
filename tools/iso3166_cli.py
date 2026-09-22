#!/usr/bin/env python3
"""
tools/iso3166_cli.py

Command-line interface to the ISO 3166 country registry.

Eight subcommands:

    lookup CC              All fields for one country
    list                   Filter across the registry
    currency CC            Currencies in circulation in a country
    country CURRENCY       Countries where a currency circulates
    region REGION          All countries in a region
    info                   Registry metadata
    validate CC...         Exit 0 if all codes exist, 1 otherwise
    search QUERY           Substring search on names and codes

Five output modes, mutually exclusive:

    --json                 One object (single) or array (list)
    --jsonl                One JSON object per line
    --csv                  Columns match iso3166.csv byte for byte
    --tsv                  Same columns, tab-delimited
    --raw FIELD            Bare values, one per line

Exit codes:
    0  Success
    1  Code not found (lookup, currency, country, validate)
    2  Usage error (bad flag, missing argument)
    3  Registry file missing or invalid

Registry resolution order:
    --registry PATH
    $ISO3166_REGISTRY
    ./iso3166.json (current directory)
    <repo>/iso3166.json (next to this script's parent)

Color is on when stdout is a TTY, off when piped. Override with
ISO3166_COLOR=never|auto|always, or --color/--no-color. NO_COLOR
(any value) forces off unless --color=always is given.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


# ============================================================
# Exit codes
# ============================================================

EXIT_SUCCESS = 0
EXIT_NOT_FOUND = 1
EXIT_USAGE = 2
EXIT_REGISTRY = 3


# ============================================================
# Constants
# ============================================================

VALID_STATUSES = (
    "officially-assigned",
    "user-assigned",
    "exceptionally-reserved",
    "withdrawn",
)
ACTIVE_STATUSES = (
    "officially-assigned",
    "user-assigned",
    "exceptionally-reserved",
)

VALID_RAW_FIELDS = frozenset({
    "alpha_2", "alpha_3", "numeric", "name", "status", "independent",
    "official_name", "region", "subregion", "intermediate_region",
    "currency_codes", "calling_codes", "tlds", "languages", "borders",
    "note", "last_verified", "withdrawal_date", "replaced_by",
})

# Import the CSV column contract so --csv output is byte-compatible
# with iso3166.csv. Both files live in tools/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_csv import COLUMNS as CSV_COLUMNS, render_row as csv_render_row  # noqa: E402


# ============================================================
# Registry loading
# ============================================================

class RegistryError(Exception):
    """Raised when the registry cannot be located or parsed."""


def resolve_registry_path(explicit: Path | None) -> Path:
    """Return the path to the registry, following the documented order."""
    candidates: list[Path] = []

    if explicit is not None:
        candidates.append(explicit)

    env = os.environ.get("ISO3166_REGISTRY")
    if env:
        candidates.append(Path(env))

    candidates.append(Path("iso3166.json"))
    candidates.append(Path(__file__).resolve().parent.parent / "iso3166.json")

    for c in candidates:
        if c.exists():
            return c

    joined = "\n  ".join(str(c) for c in candidates)
    raise RegistryError(
        "registry file not found. Tried:\n  " + joined + "\n"
        "Set --registry PATH or $ISO3166_REGISTRY."
    )


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RegistryError(f"registry not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryError(f"{path}: invalid JSON: {exc}") from exc


# ============================================================
# Color
# ============================================================

class Style:
    """Minimal ANSI styling. All methods are no-ops when disabled."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def bold(self, s: str) -> str: return self._wrap("1", s)
    def dim(self, s: str) -> str: return self._wrap("2", s)
    def red(self, s: str) -> str: return self._wrap("31", s)
    def green(self, s: str) -> str: return self._wrap("32", s)
    def yellow(self, s: str) -> str: return self._wrap("33", s)
    def cyan(self, s: str) -> str: return self._wrap("36", s)


def resolve_color_enabled(flag: str | None, stream) -> bool:
    """Decide whether to colorize. flag is --color's value or None."""
    if flag == "always":
        return True
    if flag == "never":
        return False

    env = os.environ.get("ISO3166_COLOR", "auto")
    if env == "always":
        return True
    if env == "never":
        return False
    if env not in ("auto", ""):
        # Unknown value: fall through to auto.
        pass

    if os.environ.get("NO_COLOR"):
        return False

    return hasattr(stream, "isatty") and stream.isatty()


# ============================================================
# Registry accessors
# ============================================================

def all_entries(reg: dict[str, Any]) -> list[dict[str, Any]]:
    countries = reg.get("countries", {})
    entries = list(countries.get("active", [])) + list(countries.get("withdrawn", []))
    entries.sort(key=lambda e: e.get("alpha_2", ""))
    return entries


def active_entries(reg: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in all_entries(reg) if e.get("status") in ACTIVE_STATUSES]


def find_entry(reg: dict[str, Any], code: str) -> dict[str, Any] | None:
    """Look up a single entry by alpha_2. Prefers active entries."""
    code = code.upper()
    matches = [e for e in all_entries(reg) if e.get("alpha_2") == code]
    if not matches:
        return None
    # Prefer an active entry; AI and SK each have two.
    for e in matches:
        if e.get("status") in ACTIVE_STATUSES:
            return e
    return matches[0]


# ============================================================
# Output — human
# ============================================================

def _fmt_scalar(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        if not v:
            return "—"
        return "|".join(str(x) for x in v)
    return str(v)


def render_human_entry(entry: dict[str, Any], style: Style) -> str:
    a2 = entry.get("alpha_2", "")
    name = entry.get("name", "")
    lines = [f"{style.bold(a2)}  {name}", ""]
    for key in (
        "alpha_2", "alpha_3", "numeric", "name", "status", "independent",
        "official_name", "region", "subregion", "intermediate_region",
        "currency_codes", "calling_codes", "tlds", "languages", "borders",
        "note", "last_verified", "withdrawal_date", "replaced_by",
    ):
        lines.append(f"  {key + ':':<22} {_fmt_scalar(entry.get(key))}")
    return "\n".join(lines)


def render_human_list(entries: list[dict[str, Any]], style: Style) -> str:
    if not entries:
        return "(no results)"
    lines = []
    for e in entries:
        a2 = e.get("alpha_2", "")
        a3 = e.get("alpha_3", "")
        num = e.get("numeric", "")
        name = e.get("name", "")
        status = e.get("status", "")
        lines.append(f"  {style.cyan(a2)}  {a3}  {num}  {name:<46}  {style.dim(status)}")
    return "\n".join(lines)


# ============================================================
# Output — structured
# ============================================================

def write_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    sys.stdout.write("\n")


def write_jsonl(items: Iterable[dict[str, Any]]) -> None:
    for item in items:
        sys.stdout.write(json.dumps(item, ensure_ascii=False, sort_keys=True))
        sys.stdout.write("\n")


def write_csv(entries: list[dict[str, Any]], *, delimiter: str) -> None:
    """Emit entries as CSV/TSV, byte-compatible with iso3166.csv."""
    buf = io.StringIO(newline="")
    writer = csv.writer(
        buf,
        delimiter=delimiter,
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    writer.writerow(CSV_COLUMNS)
    for e in entries:
        writer.writerow(csv_render_row(e))
    sys.stdout.write(buf.getvalue())


def write_raw(entries: list[dict[str, Any]], field: str) -> None:
    for e in entries:
        v = e.get(field)
        if v is None:
            sys.stdout.write("\n")
        elif isinstance(v, list):
            for item in v:
                sys.stdout.write(f"{item}\n")
        elif isinstance(v, bool):
            sys.stdout.write(("true" if v else "false") + "\n")
        else:
            sys.stdout.write(f"{v}\n")


# ============================================================
# Output dispatch
# ============================================================

def emit(
    entries: list[dict[str, Any]],
    args: argparse.Namespace,
    *,
    single: bool = False,
) -> None:
    """Route the result set to the selected output mode.

    single=True means the caller expects exactly one entry (lookup);
    JSON emits an object rather than an array.
    """
    if args.json:
        if single and len(entries) == 1:
            write_json(entries[0])
        else:
            write_json(entries)
    elif args.jsonl:
        write_jsonl(entries)
    elif args.csv:
        write_csv(entries, delimiter=",")
    elif args.tsv:
        write_csv(entries, delimiter="\t")
    elif args.raw:
        write_raw(entries, args.raw)
    else:
        style = Style(resolve_color_enabled(args.color, sys.stdout))
        if single and len(entries) == 1:
            print(render_human_entry(entries[0], style))
        else:
            print(render_human_list(entries, style))


# ============================================================
# Subcommand handlers
# ============================================================

def cmd_lookup(reg, args) -> int:
    entry = find_entry(reg, args.code)
    if entry is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    emit([entry], args, single=True)
    return EXIT_SUCCESS


def cmd_list(reg, args) -> int:
    pool = all_entries(reg)

    if args.active and args.withdrawn:
        print("error: --active and --withdrawn are mutually exclusive",
              file=sys.stderr)
        return EXIT_USAGE
    if args.active:
        pool = [e for e in pool if e.get("status") in ACTIVE_STATUSES]
    elif args.withdrawn:
        pool = [e for e in pool if e.get("status") == "withdrawn"]

    if args.status:
        pool = [e for e in pool if e.get("status") == args.status]
    if args.region:
        pool = [e for e in pool if (e.get("region") or "").lower() == args.region.lower()]
    if args.subregion:
        pool = [e for e in pool if (e.get("subregion") or "").lower() == args.subregion.lower()]
    if args.currency:
        c = args.currency.upper()
        pool = [e for e in pool if c in (e.get("currency_codes") or [])]

    if args.independent is True:
        pool = [e for e in pool if e.get("independent") is True]
    elif args.independent is False:
        pool = [e for e in pool if e.get("independent") is False]

    if args.limit is not None and args.limit >= 0:
        pool = pool[:args.limit]

    emit(pool, args)
    return EXIT_SUCCESS


def cmd_currency(reg, args) -> int:
    entry = find_entry(reg, args.country)
    if entry is None:
        print(f"error: not found: {args.country}", file=sys.stderr)
        return EXIT_NOT_FOUND

    codes = entry.get("currency_codes") or []
    if args.json:
        write_json({"country": entry["alpha_2"], "currency_codes": codes})
    elif args.jsonl:
        for c in codes:
            sys.stdout.write(json.dumps({"country": entry["alpha_2"], "currency": c},
                                        sort_keys=True) + "\n")
    elif args.raw:
        # --raw on currency means "the currency code", no field needed.
        for c in codes:
            sys.stdout.write(f"{c}\n")
    elif args.csv or args.tsv:
        delim = "," if args.csv else "\t"
        buf = io.StringIO(newline="")
        w = csv.writer(buf, delimiter=delim, lineterminator="\n")
        w.writerow(["country_alpha_2", "currency_code"])
        for c in codes:
            w.writerow([entry["alpha_2"], c])
        sys.stdout.write(buf.getvalue())
    else:
        style = Style(resolve_color_enabled(args.color, sys.stdout))
        if not codes:
            print(f"{style.bold(entry['alpha_2'])}  {entry.get('name', '')}: (no currencies in registry)")
        else:
            print(f"{style.bold(entry['alpha_2'])}  {entry.get('name', '')}")
            for c in codes:
                print(f"  {style.cyan(c)}")

    return EXIT_SUCCESS


def cmd_country(reg, args) -> int:
    target = args.currency.upper()
    matches = [e for e in active_entries(reg)
               if target in (e.get("currency_codes") or [])]
    if not matches:
        # Valid query, no results. Exit 1 so scripts can branch — a
        # currency that no country in the registry uses is not "not found"
        # in the code sense, but the caller asked for a match and got none.
        if args.json:
            write_json([])
        elif not (args.jsonl or args.csv or args.tsv or args.raw):
            print(f"(no countries use {target})")
        return EXIT_NOT_FOUND
    emit(matches, args)
    return EXIT_SUCCESS


def cmd_region(reg, args) -> int:
    target = args.region.lower()
    matches = [e for e in active_entries(reg)
               if (e.get("region") or "").lower() == target]
    if not matches:
        print(f"error: no countries in region: {args.region}", file=sys.stderr)
        return EXIT_NOT_FOUND
    emit(matches, args)
    return EXIT_SUCCESS


def cmd_info(reg, args) -> int:
    meta = reg.get("meta", {})
    entries = all_entries(reg)
    by_status: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    for e in entries:
        s = e.get("status")
        if s in by_status:
            by_status[s] += 1

    if args.json:
        write_json({
            "meta": meta,
            "counts": {
                "total": len(entries),
                "active": len(active_entries(reg)),
                "by_status": by_status,
            },
        })
        return EXIT_SUCCESS

    if args.jsonl:
        sys.stdout.write(json.dumps(meta, ensure_ascii=False, sort_keys=True) + "\n")
        return EXIT_SUCCESS

    if args.raw:
        sys.stdout.write(f"{meta.get(args.raw, '')}\n")
        return EXIT_SUCCESS

    style = Style(resolve_color_enabled(args.color, sys.stdout))
    print(style.bold("ISO 3166 Country Registry"))
    print()
    print(f"  version       {meta.get('version', '?')}")
    print(f"  updated       {meta.get('updated', '?')}")
    print(f"  source        {meta.get('source', '?')}")
    print(f"  schema        {meta.get('schema_version', '?')}")
    print()
    print(style.bold("Counts"))
    print(f"  total         {len(entries)}")
    print(f"  active        {len(active_entries(reg))}")
    for s in VALID_STATUSES:
        print(f"    {s:<24} {by_status[s]}")
    return EXIT_SUCCESS


def cmd_validate(reg, args) -> int:
    results: list[tuple[str, bool]] = []
    for raw in args.codes:
        code = raw.upper()
        entry = find_entry(reg, code)
        results.append((code, entry is not None))

    all_valid = all(v for _, v in results)
    valid = [c for c, v in results if v]
    invalid = [c for c, v in results if not v]

    if args.json:
        write_json({"all_valid": all_valid, "valid": valid, "invalid": invalid})
    elif args.jsonl:
        for c, v in results:
            sys.stdout.write(json.dumps({"code": c, "valid": v}, sort_keys=True) + "\n")
    elif args.raw:
        if args.raw == "code":
            for c, _ in results:
                sys.stdout.write(f"{c}\n")
        elif args.raw == "valid":
            for _, v in results:
                sys.stdout.write(("true" if v else "false") + "\n")
        else:
            print(f"error: --raw for validate accepts 'code' or 'valid', got {args.raw!r}",
                  file=sys.stderr)
            return EXIT_USAGE
    elif args.csv or args.tsv:
        delim = "," if args.csv else "\t"
        buf = io.StringIO(newline="")
        w = csv.writer(buf, delimiter=delim, lineterminator="\n")
        w.writerow(["code", "valid"])
        for c, v in results:
            w.writerow([c, "true" if v else "false"])
        sys.stdout.write(buf.getvalue())
    else:
        style = Style(resolve_color_enabled(args.color, sys.stdout))
        for c, v in results:
            if v:
                print(f"  {style.cyan(c)}  {style.green('ok')}")
            else:
                print(f"  {style.cyan(c)}  {style.red('not found')}")

    return EXIT_SUCCESS if all_valid else EXIT_NOT_FOUND


def cmd_search(reg, args) -> int:
    q = args.query.lower()
    pool = all_entries(reg)

    matches = []
    for e in pool:
        haystack = " ".join([
            e.get("name") or "",
            e.get("official_name") or "",
            e.get("alpha_2") or "",
            e.get("alpha_3") or "",
        ]).lower()
        if q in haystack:
            matches.append(e)

    emit(matches, args)
    return EXIT_SUCCESS if matches else EXIT_NOT_FOUND


# ============================================================
# Argparse
# ============================================================

def add_common_args(p: argparse.ArgumentParser) -> None:
    """Add flags that are valid before or after the subcommand."""
    p.add_argument("--registry", type=Path, default=None,
                   help="Path to iso3166.json. Defaults to $ISO3166_REGISTRY, "
                        "then ./iso3166.json, then <repo>/iso3166.json.")
    p.add_argument("--color", choices=["never", "auto", "always"], default=None,
                   help="Control ANSI color. Defaults to $ISO3166_COLOR, then auto.")

    g = p.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true",
                   help="Emit JSON. Single object for lookup/info; array otherwise.")
    g.add_argument("--jsonl", action="store_true",
                   help="Emit newline-delimited JSON, one object per line.")
    g.add_argument("--csv", action="store_true",
                   help="Emit CSV with the same columns as iso3166.csv.")
    g.add_argument("--tsv", action="store_true",
                   help="Emit tab-delimited values with the same columns as iso3166.csv.")
    g.add_argument("--raw", metavar="FIELD",
                   help="Emit bare values for one field, one per line.")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    add_common_args(common)

    p = argparse.ArgumentParser(
        prog="iso3166",
        description="Query the ISO 3166 country registry.",
    )
    add_common_args(p)

    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    sp = sub.add_parser("lookup", parents=[common], help="All fields for one country.")
    sp.add_argument("code", help="alpha-2 code (case-insensitive).")
    sp.set_defaults(func=cmd_lookup)

    sp = sub.add_parser("list", parents=[common], help="Filter across the registry.")
    sp.add_argument("--status", choices=VALID_STATUSES)
    sp.add_argument("--region")
    sp.add_argument("--subregion")
    sp.add_argument("--currency")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--independent", dest="independent", action="store_true", default=None)
    g.add_argument("--no-independent", dest="independent", action="store_false")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--active", action="store_true")
    g.add_argument("--withdrawn", action="store_true")
    sp.add_argument("--limit", type=int)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("currency", parents=[common],
                        help="Currencies in circulation in a country.")
    sp.add_argument("country")
    sp.set_defaults(func=cmd_currency)

    sp = sub.add_parser("country", parents=[common],
                        help="Countries where a currency circulates.")
    sp.add_argument("currency")
    sp.set_defaults(func=cmd_country)

    sp = sub.add_parser("region", parents=[common],
                        help="All countries in a region.")
    sp.add_argument("region")
    sp.set_defaults(func=cmd_region)

    sp = sub.add_parser("info", parents=[common], help="Registry metadata.")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("validate", parents=[common],
                        help="Exit 0 if all codes exist, 1 otherwise.")
    sp.add_argument("codes", nargs="+")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("search", parents=[common],
                        help="Substring search on names and codes.")
    sp.add_argument("query")
    sp.set_defaults(func=cmd_search)

    return p


# ============================================================
# Entry point
# ============================================================

def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.raw and args.raw not in VALID_RAW_FIELDS and args.command != "validate":
        print(
            f"error: --raw field {args.raw!r} is not a valid field.\n"
            f"  valid fields: {', '.join(sorted(VALID_RAW_FIELDS))}\n"
            f"  (validate accepts 'code' or 'valid')",
            file=sys.stderr,
        )
        return EXIT_USAGE

    try:
        path = resolve_registry_path(args.registry)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_REGISTRY

    try:
        reg = load_registry(path)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_REGISTRY

    try:
        return args.func(reg, args)
    except BrokenPipeError:
        # Piping to head, etc. Exit cleanly.
        try:
            sys.stdout.close()
        except Exception:
            pass
        return EXIT_SUCCESS


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
