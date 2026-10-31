#!/usr/bin/env python3
"""
iso3166.cli

Command-line interface to the ISO 3166 country registry. Every query goes
through iso3166.registry.CountryRegistry; the CLI does not read the
registry JSON itself.

Twenty-three subcommands (ten original, nine derived queries, four
dated club-membership queries; see docs/QUERIES.md):

    lookup CC              All fields for one country (withdrawn codes
                           included; --active-only excludes them)
    list                   Filter across the registry
    currency CC            Currencies in circulation in a country
    country CURRENCY       Countries where a currency circulates
    region REGION          All countries in a region
    info                   Registry metadata
    validate CC...         Exit 0 if all codes exist, 1 otherwise
    search QUERY           Substring search on names and codes
    successors CC          All descendants via replaced_by (transitive closure)
    predecessors CC        All ancestors: withdrawn codes that lead to this code
    is-eu CC               Prints true or false: a current member only; see
                           is-eu-member-at for dated (exit 0 if CC exists)
    is-eea CC              Same, EEA (current members only)
    is-eurozone CC         Same, eurozone (current members only)
    is-eu-member-at CC DATE            Date-scoped (v1.12.0); exit 0 true, 1 false
    is-eea-member-at CC DATE           Same, EEA
    is-eurozone-member-at CC DATE      Same, eurozone
    is-in-customs-union-at CC DATE     Same, EU customs union
    region-tree CC         Region, subregion, intermediate region
    borders-transitively CC [--max-hops N]
    succession-path FROM TO
    calling-code-for NUMBER
    currency-at CC DATE    Lifetime-bounded; exit 4 when unknown
    region-countries REGION [--subregion S]

Five output modes, mutually exclusive:

    --json                 One object (single) or array (list)
    --jsonl                One JSON object per line
    --csv                  Columns match iso3166.csv byte for byte
    --tsv                  Same columns, tab-delimited
    --raw FIELD            Bare values, one per line. A missing value
                           (null) or an empty list prints one empty line,
                           so a scalar field keeps one line per entry.
                           A non-empty list prints one line per item.

Exit codes:
    0  Success
    1  Code not found (lookup, currency, country, validate, successors,
       predecessors, is-eu, is-eea, is-eurozone, region-tree, ...)
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
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from .derived import _valid_date
from .registry import Country, CountryRegistry, RegistryError


# ============================================================
# Exit codes
# ============================================================

EXIT_SUCCESS = 0
EXIT_NOT_FOUND = 1
EXIT_USAGE = 2
EXIT_REGISTRY = 3
EXIT_UNKNOWN = 4  # tri-state: the registry has no answer (null)


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

# --raw on `info` selects a key of the registry's meta block.
INFO_RAW_FIELDS = frozenset({"version", "updated", "source", "schema_version"})

# Value of a bare `--raw` (no FIELD). Contains NUL, so no command line can
# type it; main() replaces it with the command's default field.
RAW_DEFAULT = "\x00default"

VALID_RAW_FIELDS = frozenset({
    "alpha_2", "alpha_3", "numeric", "name", "status", "independent",
    "official_name", "region", "subregion", "intermediate_region",
    "currency_codes", "calling_codes", "tlds", "languages", "borders",
    "note", "last_verified", "withdrawal_date", "replaced_by",
})

# The CSV column contract, identical to tools/export_csv.py's COLUMNS.
# Defined here so the wrapper is self-contained. Nothing but a test keeps
# the two in sync: tests/test-exports-clubs.sh and test_cli.py compare
# this CLI's --csv output with iso3166.csv byte for byte.
CSV_COLUMNS = (
    "alpha_2", "alpha_3", "numeric", "name", "status", "independent",
    "official_name", "region", "subregion", "intermediate_region",
    "currency_codes", "calling_codes", "tlds", "languages", "borders",
    "note", "last_verified", "withdrawal_date", "replaced_by", "introduced",
    "eu_membership", "eea_membership", "eurozone_membership", "customs_union",
)
_CLUB_CSV_COLUMNS = CSV_COLUMNS[-4:]


def csv_render_row(entry, reg=None):
    """Render one registry entry as a row of strings, matching iso3166.csv.

    The club cells come from the registry (`reg`), because Country does not
    carry the ranges; withdrawn entries and a missing `reg` give empty cells.
    """
    club = ("",) * 4
    if reg is not None and entry.get("status") != "withdrawn":
        club = reg._club_cells(entry.get("alpha_2", ""))
    out = []
    for col in CSV_COLUMNS:
        if col in _CLUB_CSV_COLUMNS:
            out.append(club[_CLUB_CSV_COLUMNS.index(col)])
            continue
        v = entry.get(col)
        if v is None:
            out.append("")
        elif isinstance(v, bool):
            out.append("true" if v else "false")
        elif isinstance(v, list):
            out.append("|".join(str(x) for x in v) if v else "")
        else:
            out.append(str(v))
    return out


# ============================================================
# Registry loading
# ============================================================

def resolve_registry_path(explicit: Path | None) -> Path:
    """Return the path to the registry, following the documented order.

    An explicit path (--registry or $ISO3166_REGISTRY) must exist; there
    is no fallback, because silently loading a different file than the
    caller named is worse than failing. Only when neither is set does the
    function fall back to ./iso3166.json and then <repo>/iso3166.json.
    """
    if explicit is not None:
        if not explicit.exists():
            raise RegistryError(f"registry not found: {explicit}")
        return explicit

    env = os.environ.get("ISO3166_REGISTRY")
    if env:
        env_path = Path(env)
        if not env_path.exists():
            raise RegistryError(
                f"$ISO3166_REGISTRY points at a missing file: {env_path}"
            )
        return env_path

    bundled = Path(__file__).resolve().parent / "iso3166.json"
    for c in (bundled, Path("iso3166.json")):
        if c.exists():
            return c

    raise RegistryError(
        "registry file not found. Tried:\n"
        f"  {bundled}\n"
        "  ./iso3166.json\n"
        "Set --registry PATH or $ISO3166_REGISTRY."
    )


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

def _entry(c: Country) -> dict[str, Any]:
    """A Country as a plain dict: tuples become lists, keys keep order."""
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(c).items()}


def _entries(countries: Iterable[Country]) -> list[dict[str, Any]]:
    return [_entry(c) for c in countries]


def _by_alpha2(countries: Iterable[Country]) -> list[Country]:
    """Sort by alpha_2. The sort is stable, so for AI and SK the active
    entry stays ahead of the withdrawn one."""
    return sorted(countries, key=lambda c: c.alpha_2)


def _resolve(reg: CountryRegistry, code: str) -> Country | None:
    """The entry for an alpha-2 code: active if there is one, else the
    first withdrawn entry. None if the code is not in the registry."""
    c = reg.active(code)
    if c is not None:
        return c
    matches = reg.with_alpha2(code)
    return matches[0] if matches else None


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


def write_csv(entries: list[dict[str, Any]], *, delimiter: str, reg=None) -> None:
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
        writer.writerow(csv_render_row(e, reg))
    sys.stdout.write(buf.getvalue())


def write_raw(entries: list[dict[str, Any]], field: str) -> None:
    """Bare values of one field, one per line.

    Convention: a missing value (null) and an empty list both print one
    empty line, so scalar fields keep one line per entry. A non-empty
    list prints one line per item.
    """
    for e in entries:
        v = e.get(field)
        if v is None or v == []:
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
        write_csv(entries, delimiter=",", reg=getattr(args, "_reg", None))
    elif args.tsv:
        write_csv(entries, delimiter="\t", reg=getattr(args, "_reg", None))
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

def cmd_lookup(reg: CountryRegistry, args) -> int:
    if args.active_only:
        c = reg.active(args.code)
    else:
        c = _resolve(reg, args.code)
    if c is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    emit([_entry(c)], args, single=True)
    return EXIT_SUCCESS


def cmd_list(reg: CountryRegistry, args) -> int:
    if args.active and args.withdrawn:
        print("error: --active and --withdrawn are mutually exclusive",
              file=sys.stderr)
        return EXIT_USAGE

    if args.active:
        pool = _by_alpha2(reg.all_active())
    elif args.withdrawn:
        pool = _by_alpha2(reg.all_withdrawn())
    else:
        pool = _by_alpha2(reg.all())

    if args.status:
        pool = [c for c in pool if c.status == args.status]
    if args.region:
        pool = [c for c in pool if (c.region or "").lower() == args.region.lower()]
    if args.subregion:
        pool = [c for c in pool if (c.subregion or "").lower() == args.subregion.lower()]
    if args.currency:
        code = args.currency.upper()
        pool = [c for c in pool if code in (c.currency_codes or ())]

    if args.independent is True:
        pool = [c for c in pool if c.independent is True]
    elif args.independent is False:
        pool = [c for c in pool if c.independent is False]

    if args.limit is not None and args.limit >= 0:
        pool = pool[:args.limit]

    emit(_entries(pool), args)
    return EXIT_SUCCESS


def cmd_currency(reg: CountryRegistry, args) -> int:
    c = _resolve(reg, args.country)
    if c is None:
        print(f"error: not found: {args.country}", file=sys.stderr)
        return EXIT_NOT_FOUND

    codes = list(c.currency_codes or ())
    if args.json:
        write_json({"country": c.alpha_2, "currency_codes": codes})
    elif args.jsonl:
        for cc in codes:
            sys.stdout.write(json.dumps({"country": c.alpha_2, "currency": cc},
                                        sort_keys=True) + "\n")
    elif args.raw:
        # --raw on currency means "the currency code", no field needed.
        for cc in codes:
            sys.stdout.write(f"{cc}\n")
    elif args.csv or args.tsv:
        delim = "," if args.csv else "\t"
        buf = io.StringIO(newline="")
        w = csv.writer(buf, delimiter=delim, lineterminator="\n")
        w.writerow(["country_alpha_2", "currency_code"])
        for cc in codes:
            w.writerow([c.alpha_2, cc])
        sys.stdout.write(buf.getvalue())
    else:
        style = Style(resolve_color_enabled(args.color, sys.stdout))
        if not codes:
            print(f"{style.bold(c.alpha_2)}  {c.name}: (no currencies in registry)")
        else:
            print(f"{style.bold(c.alpha_2)}  {c.name}")
            for cc in codes:
                print(f"  {style.cyan(cc)}")

    return EXIT_SUCCESS


def cmd_country(reg: CountryRegistry, args) -> int:
    target = args.currency.upper()
    matches = reg.countries_with(target)
    if not matches:
        # Valid query, no results. Exit 1 so scripts can branch: a
        # currency that no country in the registry uses is not "not found"
        # in the code sense, but the caller asked for a match and got none.
        if args.json:
            write_json([])
        elif not (args.jsonl or args.csv or args.tsv or args.raw):
            print(f"(no countries use {target})")
        return EXIT_NOT_FOUND
    emit(_entries(matches), args)
    return EXIT_SUCCESS


def cmd_region(reg: CountryRegistry, args) -> int:
    matches = reg.region(args.region)
    if not matches:
        print(f"error: no countries in region: {args.region}", file=sys.stderr)
        return EXIT_NOT_FOUND
    emit(_entries(matches), args)
    return EXIT_SUCCESS


def cmd_info(reg: CountryRegistry, args) -> int:
    meta = reg.meta
    summary = reg.summary()
    by_status: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    for status, n in summary["by_status"].items():
        if status in by_status:
            by_status[status] = n

    if args.json:
        write_json({
            "meta": meta,
            "counts": {
                "total": summary["total"],
                "active": summary["active"],
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
    print(f"  total         {summary['total']}")
    print(f"  active        {summary['active']}")
    for s in VALID_STATUSES:
        print(f"    {s:<24} {by_status[s]}")
    return EXIT_SUCCESS


def cmd_validate(reg: CountryRegistry, args) -> int:
    results: list[tuple[str, bool]] = []
    for raw in args.codes:
        code = raw.upper()
        results.append((code, bool(reg.with_alpha2(code))))

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


def cmd_search(reg: CountryRegistry, args) -> int:
    matches = _by_alpha2(reg.search(args.query))
    emit(_entries(matches), args)
    return EXIT_SUCCESS if matches else EXIT_NOT_FOUND


# ============================================================
# Succession queries
# ============================================================
#
# Both commands resolve a code to the withdrawn entry when a code is
# held by an active and a withdrawn entry (AI, SK): the question being
# asked is about succession, and only withdrawn entries have any.

def _succession_index(reg: CountryRegistry) -> dict[str, Country]:
    """alpha_2 -> entry; withdrawn wins over active for AI and SK."""
    return {c.alpha_2: c for c in reg.all()}


def cmd_successors(reg: CountryRegistry, args) -> int:
    code = args.code.upper()
    by_a2 = _succession_index(reg)
    entry = by_a2.get(code)
    if entry is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND

    chain: list[str] = []
    seen: set[str] = set()

    def walk(cur: str) -> None:
        if cur in seen:
            return
        seen.add(cur)
        e = by_a2.get(cur)
        if e is None:
            return
        succ = list(e.replaced_by or ())
        if e.status == "withdrawn" and succ:
            chain.append(cur)
            for s in succ:
                walk(s)

    walk(code)
    # All descendants: the transitive closure (docs/QUERIES.md, Query 5).
    # Changed in v1.10.0 from terminal successors only.
    successors = reg.successors(code)

    def link(c: str) -> dict[str, Any]:
        e = by_a2[c]
        return {
            "alpha_2": c,
            "name": e.name,
            "withdrawal_date": e.withdrawal_date,
            "replaced_by": list(e.replaced_by or ()),
        }

    if args.json:
        write_json({
            "code": code,
            "chain": [link(c) for c in chain],
            "successors": successors,
        })
        return EXIT_SUCCESS

    if args.jsonl:
        for c in chain:
            sys.stdout.write(json.dumps(link(c), sort_keys=True) + "\n")
        return EXIT_SUCCESS

    if args.raw:
        for t in successors:
            sys.stdout.write(f"{t}\n")
        return EXIT_SUCCESS

    if args.csv or args.tsv:
        delim = "," if args.csv else "\t"
        buf = io.StringIO(newline="")
        w = csv.writer(buf, delimiter=delim, lineterminator="\n")
        w.writerow(["alpha_2", "name", "withdrawal_date", "replaced_by"])
        for c in chain:
            e = by_a2[c]
            w.writerow([
                c,
                e.name or "",
                e.withdrawal_date or "",
                ",".join(e.replaced_by or ()),
            ])
        sys.stdout.write(buf.getvalue())
        return EXIT_SUCCESS

    style = Style(resolve_color_enabled(args.color, sys.stdout))
    if not chain:
        print(f"{style.cyan(code)} — {entry.name} has no successors.")
        return EXIT_SUCCESS

    for c in chain:
        e = by_a2[c]
        succ = ", ".join(e.replaced_by or ()) or "—"
        wd_str = f" (withdrawn {e.withdrawal_date})" if e.withdrawal_date else ""
        print(f"{style.cyan(c)} — {e.name}{wd_str} -> {succ}")

    print()
    print(f"Successors (all descendants): {', '.join(successors)}")
    return EXIT_SUCCESS


def cmd_predecessors(reg: CountryRegistry, args) -> int:
    code = args.code.upper()
    by_a2 = _succession_index(reg)
    if code not in by_a2:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND

    # All ancestors: the transitive closure, read backwards
    # (docs/QUERIES.md, Query 5). Changed in v1.10.0 from terminal-only.
    predecessors = reg.predecessors(code)

    if args.json:
        write_json({"code": code, "predecessors": predecessors})
        return EXIT_SUCCESS

    if args.jsonl:
        for p in predecessors:
            sys.stdout.write(json.dumps(
                {"code": code, "predecessor": p}, sort_keys=True,
            ) + "\n")
        return EXIT_SUCCESS

    if args.raw:
        for p in predecessors:
            sys.stdout.write(f"{p}\n")
        return EXIT_SUCCESS

    if args.csv or args.tsv:
        delim = "," if args.csv else "\t"
        buf = io.StringIO(newline="")
        w = csv.writer(buf, delimiter=delim, lineterminator="\n")
        w.writerow(["predecessor"])
        for p in predecessors:
            w.writerow([p])
        sys.stdout.write(buf.getvalue())
        return EXIT_SUCCESS

    style = Style(resolve_color_enabled(args.color, sys.stdout))
    if not predecessors:
        print(f"{style.cyan(code)} has no withdrawn predecessors.")
    else:
        print(f"{style.cyan(code)} has predecessors (all ancestors): "
              f"{', '.join(predecessors)}")
    return EXIT_SUCCESS


# ============================================================
# Derived queries (v1.10.0; design in docs/QUERIES.md)
#
# Each command calls the matching CountryRegistry method, so this CLI,
# tools/iso3166_cli.py and the four wrappers answer from one contract.
#
# is-eu, is-eea and is-eurozone print "true" or "false" and exit 0
# whenever the code exists; 1 if it is not in the registry; 2 on a usage
# error; 3 if the registry is missing. The boolean is the answer, the
# exit code is the plumbing.
# ============================================================

def _dq_emit(args, value, *, human: str | None = None) -> None:
    if args.json:
        write_json(value)
    elif human is not None:
        print(human)
    elif isinstance(value, list):
        for v in value:
            print(v)
    else:
        print(value)


def _dq_predicate(reg: CountryRegistry, args, method: str) -> int:
    if _resolve(reg, args.code.strip().upper()) is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    result = bool(getattr(reg, method)(args.code))
    text = "true" if result else "false"
    if args.json:
        write_json({"code": args.code.strip().upper(), method: result, "result": text})
    else:
        print(text)
    return EXIT_SUCCESS


def cmd_is_eu(reg: CountryRegistry, args) -> int:
    return _dq_predicate(reg, args, "is_eu")


def cmd_is_eea(reg: CountryRegistry, args) -> int:
    return _dq_predicate(reg, args, "is_eea")


def cmd_is_eurozone(reg: CountryRegistry, args) -> int:
    return _dq_predicate(reg, args, "is_eurozone")


def _dq_member_at(reg: CountryRegistry, args, method: str) -> int:
    """Date-scoped club membership (v1.12.0, docs/QUERIES.md, Query 10).

    Prints "true" or "false". Exit 0 true, 1 false (that includes an unknown
    code: it is in no club), 2 on a malformed DATE, 4 if the library ever
    returns None. The library never does today, so 4 is a reserved
    tri-state slot that no input reaches.
    """
    code, date = args.code.strip().upper(), args.date
    if not _valid_date(date):
        print(f"error: malformed date: {date!r} (want YYYY-MM-DD)", file=sys.stderr)
        return EXIT_USAGE
    result = getattr(reg, method)(code, date)
    text = "unknown" if result is None else ("true" if result else "false")
    if args.json:
        write_json({"code": code, "date": date, method: result, "result": text})
    else:
        print(text)
    return EXIT_UNKNOWN if result is None else (EXIT_SUCCESS if result else EXIT_NOT_FOUND)


def cmd_is_eu_member_at(reg: CountryRegistry, args) -> int:
    return _dq_member_at(reg, args, "is_eu_member_at")


def cmd_is_eea_member_at(reg: CountryRegistry, args) -> int:
    return _dq_member_at(reg, args, "is_eea_member_at")


def cmd_is_eurozone_member_at(reg: CountryRegistry, args) -> int:
    return _dq_member_at(reg, args, "is_eurozone_member_at")


def cmd_is_in_customs_union_at(reg: CountryRegistry, args) -> int:
    return _dq_member_at(reg, args, "is_in_customs_union_at")


def cmd_region_tree(reg: CountryRegistry, args) -> int:
    if _resolve(reg, args.code.strip().upper()) is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    tree = reg.region_tree(args.code)
    _dq_emit(args, tree, human=", ".join(tree))
    return EXIT_SUCCESS


def cmd_borders_transitively(reg: CountryRegistry, args) -> int:
    if _resolve(reg, args.code.strip().upper()) is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    _dq_emit(args, reg.borders_transitively(args.code, args.max_hops))
    return EXIT_SUCCESS


def cmd_succession_path(reg: CountryRegistry, args) -> int:
    path = reg.succession_path(args.from_code, args.to_code)
    if path is None:
        if args.json:
            write_json(None)
        return EXIT_NOT_FOUND
    _dq_emit(args, path, human=" -> ".join(path))
    return EXIT_SUCCESS


def cmd_calling_code_for(reg: CountryRegistry, args) -> int:
    out = reg.calling_code_for(args.number)
    _dq_emit(args, out)
    return EXIT_SUCCESS if out else EXIT_NOT_FOUND


def cmd_currency_at(reg: CountryRegistry, args) -> int:
    code, date = args.code.strip().upper(), args.date
    if not _valid_date(date):
        print(f"error: malformed date: {date!r} (want YYYY-MM-DD)", file=sys.stderr)
        return EXIT_USAGE
    if not reg.with_alpha2(code):
        if args.json:
            write_json(None)
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    result = reg.currency_at(code, date)
    if result is None:
        if args.json:
            write_json(None)
        return EXIT_UNKNOWN
    _dq_emit(args, result)
    return EXIT_SUCCESS


def cmd_introduced(reg: CountryRegistry, args) -> int:
    code = args.code.strip().upper()
    found = reg.with_alpha2(code)
    if not found:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    value = found[0].introduced  # with_alpha2 lists the active entry first
    if args.json:
        write_json({"code": code, "introduced": value,
                    "result": "unknown" if value is None else value})
    else:
        print("unknown" if value is None else value)
    return EXIT_UNKNOWN if value is None else EXIT_SUCCESS


def cmd_is_active_on(reg: CountryRegistry, args) -> int:
    code, date = args.code.strip().upper(), args.date
    if not _valid_date(date):
        print(f"error: malformed date: {date!r} (want YYYY-MM-DD)", file=sys.stderr)
        return EXIT_USAGE
    result = reg.is_active_on(code, date)
    text = "unknown" if result is None else ("true" if result else "false")
    if args.json:
        write_json({"code": code, "date": date,
                    "is_active_on": result, "result": text})
    else:
        print(text)
    return EXIT_UNKNOWN if result is None else (EXIT_SUCCESS if result else EXIT_NOT_FOUND)


def cmd_region_countries(reg: CountryRegistry, args) -> int:
    out = reg.region_countries(args.region, args.subregion)
    _dq_emit(args, out)
    return EXIT_SUCCESS if out else EXIT_NOT_FOUND


# ============================================================
# Argparse
# ============================================================

def add_common_args(
    p: argparse.ArgumentParser,
    *,
    suppress_defaults: bool = False,
) -> None:
    """Add flags valid before or after the subcommand.

    When suppress_defaults is True (used on subparsers), the defaults are
    argparse.SUPPRESS so the subparser does not overwrite values already
    set by the parent parser. main() fills in the real defaults for
    anything left unset.
    """
    d_none = argparse.SUPPRESS if suppress_defaults else None
    d_false = argparse.SUPPRESS if suppress_defaults else False

    p.add_argument("--registry", type=Path, default=d_none,
                   help="Path to iso3166.json. Defaults to $ISO3166_REGISTRY, "
                        "then ./iso3166.json, then <repo>/iso3166.json.")
    p.add_argument("--color", choices=["never", "auto", "always"], default=d_none,
                   help="Control ANSI color. Defaults to $ISO3166_COLOR, then auto.")

    g = p.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true", default=d_false,
                   help="Emit JSON. Single object for lookup/info; array otherwise.")
    g.add_argument("--jsonl", action="store_true", default=d_false,
                   help="Emit newline-delimited JSON, one object per line.")
    g.add_argument("--csv", action="store_true", default=d_false,
                   help="Emit CSV with the same columns as iso3166.csv.")
    g.add_argument("--tsv", action="store_true", default=d_false,
                   help="Emit tab-delimited values with the same columns as iso3166.csv.")
    g.add_argument("--raw", metavar="FIELD", nargs="?", const=RAW_DEFAULT,
                   default=d_none,
                   help="Emit bare values for one field, one per line. FIELD is "
                        "optional: bare --raw means alpha_2 ('code' for validate; "
                        "info needs a FIELD).")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    add_common_args(common, suppress_defaults=True)

    p = argparse.ArgumentParser(
        prog="iso3166",
        description="Query the ISO 3166 country registry.",
    )
    add_common_args(p)

    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    sp = sub.add_parser("lookup", parents=[common], help="All fields for one country.")
    sp.add_argument("code", help="alpha-2 code (case-insensitive).")
    sp.add_argument("--active-only", action="store_true",
                    help="Do not return withdrawn codes; exit 1 for them, "
                         "like the library's active().")
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

    sp = sub.add_parser("successors", parents=[common],
                        help="All descendants (transitive closure) of CODE via replaced_by. "
                             "Breaking change in v1.10.0: was terminal successors only. "
                             "See docs/QUERIES.md, Query 5.")
    sp.add_argument("code", help="alpha-2 code.")
    sp.set_defaults(func=cmd_successors)

    sp = sub.add_parser("predecessors", parents=[common],
                        help="All ancestors (transitive closure): withdrawn codes that lead to "
                             "CODE via replaced_by. Breaking change in v1.10.0. "
                             "See docs/QUERIES.md, Query 5.")
    sp.add_argument("code", help="alpha-2 code.")
    sp.set_defaults(func=cmd_predecessors)

    # -- Derived queries (v1.10.0; docs/QUERIES.md) --
    for name, fn, text in (
        ("is-eu", cmd_is_eu,
         "Is CODE a current EU member? Prints true or false to stdout. Current member only; see is-eu-member-at for dated membership. "
         "Exit 0 if CODE exists (true or false), 1 if not found, 2 on usage error, 3 if the registry is missing. "
         "See docs/QUERIES.md, Query 1."),
        ("is-eea", cmd_is_eea,
         "Is CODE a current EEA member? Prints true or false to stdout. Current member only; see is-eea-member-at for dated membership. "
         "Exit 0 if CODE exists (true or false), 1 if not found, 2 on usage error, 3 if the registry is missing. "
         "See docs/QUERIES.md, Query 1."),
        ("is-eurozone", cmd_is_eurozone,
         "Is CODE a current eurozone member? Prints true or false to stdout. Current member only; see is-eurozone-member-at for dated membership. "
         "Exit 0 if CODE exists (true or false), 1 if not found, 2 on usage error, 3 if the registry is missing. "
         "See docs/QUERIES.md, Query 1."),
    ):
        sp = sub.add_parser(name, parents=[common], help=text, description=text)
        sp.add_argument("code", help="alpha-2 code.")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("region-tree", parents=[common],
                        help="Region, subregion, intermediate region (nulls dropped). "
                             "See docs/QUERIES.md, Query 2.")
    sp.add_argument("code", help="alpha-2 code.")
    sp.set_defaults(func=cmd_region_tree)

    sp = sub.add_parser("borders-transitively", parents=[common],
                        help="Codes within N border hops, excluding CODE. "
                             "See docs/QUERIES.md, Query 3.")
    sp.add_argument("code", help="alpha-2 code.")
    sp.add_argument("--max-hops", type=int, default=2, help="Hop limit (default 2).")
    sp.set_defaults(func=cmd_borders_transitively)

    sp = sub.add_parser("succession-path", parents=[common],
                        help="Shortest replaced_by path FROM to TO; exit 1 if none. "
                             "See docs/QUERIES.md, Query 4.")
    sp.add_argument("from_code", metavar="FROM", help="alpha-2 code.")
    sp.add_argument("to_code", metavar="TO", help="alpha-2 code.")
    sp.set_defaults(func=cmd_succession_path)

    sp = sub.add_parser("calling-code-for", parents=[common],
                        help="Countries whose calling code prefixes NUMBER "
                             "(country level; +1 and +44 are shared). "
                             "See docs/QUERIES.md, Query 6.")
    sp.add_argument("number", help='Phone number, e.g. "+44 20 7946 0958".')
    sp.set_defaults(func=cmd_calling_code_for)

    sp = sub.add_parser("currency-at", parents=[common],
                        help="Currency at DATE (YYYY-MM-DD), bounded by the entry's lifetime "
                             "(v1.11.1). Returns the entry's current currency (no "
                             "history is stored); withdrawn codes return the "
                             "successor's. Exit 0 list, 4 unknown (None), 1 code "
                             "not found, 2 malformed DATE. See docs/QUERIES.md, Query 7.")
    sp.add_argument("code", help="alpha-2 code.")
    sp.add_argument("date", help="YYYY-MM-DD.")
    sp.set_defaults(func=cmd_currency_at)

    sp = sub.add_parser("region-countries", parents=[common],
                        help="Active countries in a region (and subregion). "
                             "See docs/QUERIES.md, Query 8.")
    sp.add_argument("region", help="Region name, e.g. Europe.")
    sp.add_argument("--subregion", default=None, help="Subregion name.")
    sp.set_defaults(func=cmd_region_countries)

    # -- Temporal fields (v1.11.0) --
    sp = sub.add_parser("introduced", parents=[common],
                        help='Introduction date of CODE (YYYY-MM-DD): when ISO 3166-1 added the code. Tri-state: prints the date, or unknown. Exit 0 if known, 4 if unknown (null), 1 if CODE not found, 2 on usage error, 3 if the registry is missing. See docs/QUERIES.md, Known Nulls.', description='Introduction date of CODE (YYYY-MM-DD): when ISO 3166-1 added the code. Tri-state: prints the date, or unknown. Exit 0 if known, 4 if unknown (null), 1 if CODE not found, 2 on usage error, 3 if the registry is missing. See docs/QUERIES.md, Known Nulls.')
    sp.add_argument("code", help="alpha-2 code.")
    sp.set_defaults(func=cmd_introduced)

    # -- Club memberships (v1.12.0; docs/QUERIES.md, Query 10) --
    for name, fn, what in (
        ("is-eu-member-at", cmd_is_eu_member_at, "an EU member state"),
        ("is-eea-member-at", cmd_is_eea_member_at, "a party to the EEA Agreement"),
        ("is-eurozone-member-at", cmd_is_eurozone_member_at, "in the eurozone"),
        ("is-in-customs-union-at", cmd_is_in_customs_union_at, "in the EU customs union"),
    ):
        text = (f"Was CODE {what} on DATE (YYYY-MM-DD)? Prints true or false. "
                "Exit 0 true, 1 false (an unknown code is in no club, so false), "
                "4 reserved for unknown (never reached today); 2 on a malformed DATE "
                "or usage error, 3 if the registry is missing. "
                "See docs/QUERIES.md, Query 10.")
        sp = sub.add_parser(name, parents=[common], help=text, description=text)
        sp.add_argument("code", help="alpha-2 code.")
        sp.add_argument("date", help="YYYY-MM-DD.")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("is-active-on", parents=[common],
                        help='Was CODE assigned on DATE (YYYY-MM-DD)? Tri-state: prints true, false, or unknown. Exit 0 true, 1 false, 4 unknown; 2 on a malformed DATE or usage error, 3 if the registry is missing. See docs/QUERIES.md, Query 9.', description='Was CODE assigned on DATE (YYYY-MM-DD)? Tri-state: prints true, false, or unknown. Exit 0 true, 1 false, 4 unknown; 2 on a malformed DATE or usage error, 3 if the registry is missing. See docs/QUERIES.md, Query 9.')
    sp.add_argument("code", help="alpha-2 code.")
    sp.add_argument("date", help="YYYY-MM-DD.")
    sp.set_defaults(func=cmd_is_active_on)

    return p


# ============================================================
# Entry point
# ============================================================

_COMMON_DEFAULTS = (
    ("registry", None),
    ("color", None),
    ("json", False),
    ("jsonl", False),
    ("csv", False),
    ("tsv", False),
    ("raw", None),
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # The subparsers carry argparse.SUPPRESS defaults for the common flags
    # (see add_common_args) so they do not clobber values set by the parent
    # parser. Anything left unset gets its real default here.
    for attr, default in _COMMON_DEFAULTS:
        if not hasattr(args, attr):
            setattr(args, attr, default)

    # The parent and the subparser each have a mutually exclusive group
    # for the output modes, but they cannot see each other. Catch the
    # cross-parser case here.
    modes = [m for m in ("json", "jsonl", "csv", "tsv") if getattr(args, m, False)]
    if len(modes) > 1:
        print(
            "error: output modes are mutually exclusive; got "
            + ", ".join("--" + m for m in modes),
            file=sys.stderr,
        )
        return EXIT_USAGE

    if args.raw == RAW_DEFAULT:
        # Bare --raw: pick the command's natural field (v1.10.2).
        if args.command == "info":
            print(
                "error: --raw needs a FIELD for info; valid fields: "
                + ", ".join(sorted(INFO_RAW_FIELDS)),
                file=sys.stderr,
            )
            return EXIT_USAGE
        args.raw = "code" if args.command == "validate" else "alpha_2"

    if args.raw and args.command == "info":
        if args.raw not in INFO_RAW_FIELDS:
            print(
                f"error: --raw field {args.raw!r} is not valid for info.\n"
                f"  valid fields: {', '.join(sorted(INFO_RAW_FIELDS))}",
                file=sys.stderr,
            )
            return EXIT_USAGE
    elif args.raw and args.raw not in VALID_RAW_FIELDS and args.command != "validate":
        print(
            f"error: --raw field {args.raw!r} is not a valid field.\n"
            f"  valid fields: {', '.join(sorted(VALID_RAW_FIELDS))}\n"
            f"  (validate accepts 'code' or 'valid'; "
            f"info accepts {', '.join(sorted(INFO_RAW_FIELDS))})",
            file=sys.stderr,
        )
        return EXIT_USAGE

    try:
        path = resolve_registry_path(args.registry)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_REGISTRY

    try:
        reg = CountryRegistry(path)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_REGISTRY

    args._reg = reg  # for --csv/--tsv: the club cells are read from the registry
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
