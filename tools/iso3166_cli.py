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
    1  Code not found (lookup, currency, country, validate, is-eu, ...)
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
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence


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

# Value of a bare `--raw` (no FIELD). Contains NUL, so no command line can
# type it; main() replaces it with the command's default field.
RAW_DEFAULT = "\x00default"

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

    here = Path(__file__).resolve().parent.parent / "iso3166.json"
    for c in (Path("iso3166.json"), here):
        if c.exists():
            return c

    raise RegistryError(
        "registry file not found. Tried:\n"
        "  ./iso3166.json\n"
        f"  {here}\n"
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

    # Date filters over the withdrawn set.
    since = getattr(args, "withdrawn_since", None)
    before = getattr(args, "withdrawn_before", None)
    if since or before:
        if not args.withdrawn:
            print(
                "error: --withdrawn-since and --withdrawn-before require --withdrawn",
                file=sys.stderr,
            )
            return EXIT_USAGE

        def _parse(s: str, flag: str):
            try:
                return datetime.strptime(s, "%Y-%m-%d").date()
            except ValueError:
                print(f"error: {flag}: {s!r} is not YYYY-MM-DD", file=sys.stderr)
                return None

        if since:
            since_d = _parse(since, "--withdrawn-since")
            if since_d is None:
                return EXIT_USAGE
            pool = [e for e in pool
                    if e.get("withdrawal_date")
                    and datetime.strptime(e["withdrawal_date"], "%Y-%m-%d").date() >= since_d]

        if before:
            before_d = _parse(before, "--withdrawn-before")
            if before_d is None:
                return EXIT_USAGE
            pool = [e for e in pool
                    if e.get("withdrawal_date")
                    and datetime.strptime(e["withdrawal_date"], "%Y-%m-%d").date() < before_d]

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
# Succession queries
# ============================================================

def _succession_closure(start: str, edges: dict[str, list[str]]) -> list[str]:
    """Transitive closure over `edges` from `start`, excluding `start`.

    Used for both directions: forward edges give all descendants of a
    code, reversed edges give all ancestors. See docs/QUERIES.md,
    "Query 5".
    """
    seen: set[str] = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        for nxt in edges.get(cur, ()):
            if nxt != start and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return sorted(seen)


def cmd_successors(reg, args) -> int:
    """All descendants (transitive closure) of a code via replaced_by.

    Breaking change in v1.10.0: v1.9.x returned terminal successors only.
    """
    code = args.code.upper()
    by_a2 = {e["alpha_2"]: e for e in all_entries(reg)}
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
        succ = list(e.get("replaced_by") or [])
        if e.get("status") == "withdrawn" and succ:
            chain.append(cur)
            for s in succ:
                walk(s)

    walk(code)
    edges = {
        e["alpha_2"]: list(e["replaced_by"])
        for e in reg["countries"]["withdrawn"] if e.get("replaced_by")
    }
    successors = _succession_closure(code, edges)

    if args.json:
        write_json({
            "code": code,
            "chain": [
                {
                    "alpha_2": c,
                    "name": by_a2[c].get("name"),
                    "withdrawal_date": by_a2[c].get("withdrawal_date"),
                    "replaced_by": by_a2[c].get("replaced_by") or [],
                }
                for c in chain
            ],
            "successors": successors,
        })
        return EXIT_SUCCESS

    if args.jsonl:
        for c in chain:
            e = by_a2[c]
            sys.stdout.write(json.dumps({
                "alpha_2": c,
                "name": e.get("name"),
                "withdrawal_date": e.get("withdrawal_date"),
                "replaced_by": e.get("replaced_by") or [],
            }, sort_keys=True) + "\n")
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
                e.get("name") or "",
                e.get("withdrawal_date") or "",
                ",".join(e.get("replaced_by") or []),
            ])
        sys.stdout.write(buf.getvalue())
        return EXIT_SUCCESS

    style = Style(resolve_color_enabled(args.color, sys.stdout))
    if not chain:
        e = by_a2[code]
        print(f"{style.cyan(code)} — {e.get('name', '')} has no successors.")
        return EXIT_SUCCESS

    for c in chain:
        e = by_a2[c]
        succ = ", ".join(e.get("replaced_by") or []) or "—"
        wd = e.get("withdrawal_date") or ""
        wd_str = f" (withdrawn {wd})" if wd else ""
        print(f"{style.cyan(c)} — {e.get('name', '')}{wd_str} -> {succ}")

    print()
    print(f"Successors (all descendants): {', '.join(successors)}")
    return EXIT_SUCCESS


def cmd_predecessors(reg, args) -> int:
    """All ancestors (transitive closure, reversed) of a code.

    Breaking change in v1.10.0: v1.9.x listed only withdrawn codes whose
    terminal successors included the code.
    """
    code = args.code.upper()
    by_a2 = {e["alpha_2"]: e for e in all_entries(reg)}
    if code not in by_a2:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND

    reverse: dict[str, list[str]] = {}
    for e in reg["countries"]["withdrawn"]:
        for d in e.get("replaced_by") or ():
            reverse.setdefault(d, []).append(e["alpha_2"])
    predecessors = _succession_closure(code, reverse)

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
# Derived queries (v1.10.0)
#
# Independent of the wrappers on purpose: this file works on the raw
# registry dict, so tools/check_cross_language.sh compares two separate
# implementations. Semantics follow docs/QUERIES.md as corrected in
# SPEC.md ("Where the design was wrong").
#
# is-eu, is-eea and is-eurozone follow the CLI's standard exit codes like
# every other subcommand: the boolean is the answer (stdout), the exit
# code is the plumbing. Prints "true" or "false" and exits 0 whenever the
# code exists; 1 if it is not in the registry; 2 on a usage error; 3 if
# the registry is missing. See docs/QUERIES.md, Query 1.
# ============================================================

import re as _re
from datetime import date as _date

# Club membership fields (v1.12.0): date-scoped {from, to} ranges on every
# active entry. This file reads them from the raw dict, on purpose
# independent of the wrappers' implementation.
CLUB_FIELDS = ("eu_membership", "eea_membership", "eurozone_membership", "customs_union")


def _dq_active(reg):
    return {e["alpha_2"]: e for e in reg["countries"]["active"]}


def _dq_edges(reg):
    return {
        e["alpha_2"]: list(e["replaced_by"])
        for e in reg["countries"]["withdrawn"]
        if e.get("replaced_by")
    }


def _dq_closure(start, edges):
    seen, stack = set(), [start]
    while stack:
        cur = stack.pop()
        for n in edges.get(cur, ()):
            if n != start and n not in seen:
                seen.add(n)
                stack.append(n)
    return sorted(seen)


def _dq_emit(args, value, *, human=None) -> None:
    if args.json:
        write_json(value)
    elif human is not None:
        print(human)
    elif isinstance(value, list):
        for v in value:
            print(v)
    else:
        print(value)


def _dq_predicate(reg, args, fn, key) -> int:
    """Print "true" or "false"; exit 0 if the code exists, 1 if not.

    With --json prints {"code": CODE, KEY: true, "result": "true"}.
    """
    code = args.code.strip().upper()
    if find_entry(reg, code) is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    result = bool(fn(reg, code))
    text = "true" if result else "false"
    if args.json:
        write_json({"code": code, key: result, "result": text})
    else:
        print(text)
    return EXIT_SUCCESS


def _dq_club_now(reg, code, field):
    """Current member: some range of the active entry has to == null."""
    e = _dq_active(reg).get(code)
    return bool(e) and any(r["to"] is None for r in e.get(field) or ())


def _dq_club_at(reg, code, field, date):
    """from <= date <= to for some range (to null = open). Never None."""
    if not _dq_valid_date(date):
        return False
    e = _dq_active(reg).get(code)
    return bool(e) and any(
        r["from"] <= date and (r["to"] is None or date <= r["to"])
        for r in e.get(field) or ()
    )


def _dq_is_eu(reg, code):
    return _dq_club_now(reg, code, "eu_membership")


def _dq_is_eea(reg, code):
    return _dq_club_now(reg, code, "eea_membership")


def _dq_is_eurozone(reg, code):
    return _dq_club_now(reg, code, "eurozone_membership")


def cmd_is_eu(reg, args) -> int:
    return _dq_predicate(reg, args, _dq_is_eu, "is_eu")


def cmd_is_eea(reg, args) -> int:
    return _dq_predicate(reg, args, _dq_is_eea, "is_eea")


def cmd_is_eurozone(reg, args) -> int:
    return _dq_predicate(reg, args, _dq_is_eurozone, "is_eurozone")


def _dq_member_at(reg, args, key, field) -> int:
    """Date-scoped club membership (v1.12.0, docs/QUERIES.md, Query 10).

    Prints "true" or "false". Exit 0 true, 1 false (an unknown code is in no
    club), 2 on a malformed DATE. Exit 4 is reserved for a tri-state
    "unknown" that no input reaches today.
    """
    code, date = args.code.strip().upper(), args.date
    if not _dq_valid_date(date):
        print(f"error: malformed date: {date!r} (want YYYY-MM-DD)", file=sys.stderr)
        return EXIT_USAGE
    result = _dq_club_at(reg, code, field, date)
    text = "true" if result else "false"
    if args.json:
        write_json({"code": code, "date": date, key: result, "result": text})
    else:
        print(text)
    return EXIT_SUCCESS if result else EXIT_NOT_FOUND


def cmd_is_eu_member_at(reg, args) -> int:
    return _dq_member_at(reg, args, "is_eu_member_at", "eu_membership")


def cmd_is_eea_member_at(reg, args) -> int:
    return _dq_member_at(reg, args, "is_eea_member_at", "eea_membership")


def cmd_is_eurozone_member_at(reg, args) -> int:
    return _dq_member_at(reg, args, "is_eurozone_member_at", "eurozone_membership")


def cmd_is_in_customs_union_at(reg, args) -> int:
    return _dq_member_at(reg, args, "is_in_customs_union_at", "customs_union")


def cmd_region_tree(reg, args) -> int:
    e = find_entry(reg, args.code.strip())
    if e is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    tree = [v for v in (e.get("region"), e.get("subregion"),
                        e.get("intermediate_region")) if v]
    _dq_emit(args, tree, human=", ".join(tree))
    return EXIT_SUCCESS


def cmd_borders_transitively(reg, args) -> int:
    start = args.code.strip().upper()
    if find_entry(reg, start) is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    act = _dq_active(reg)
    seen, frontier = {start}, [start]
    for _ in range(max(args.max_hops, 0)):
        nxt = []
        for cur in frontier:
            for b in (act.get(cur) or {}).get("borders") or ():
                if b not in seen:
                    seen.add(b)
                    nxt.append(b)
        if not nxt:
            break
        frontier = nxt
    seen.discard(start)
    _dq_emit(args, sorted(seen))
    return EXIT_SUCCESS


def cmd_succession_path(reg, args) -> int:
    a, b = args.from_code.strip().upper(), args.to_code.strip().upper()
    path = None
    if find_entry(reg, a) and find_entry(reg, b):
        if a == b:
            path = [a]
        else:
            edges, prev, queue = _dq_edges(reg), {a: None}, [a]
            for cur in queue:
                for n in edges.get(cur, ()):
                    if n in prev:
                        continue
                    prev[n] = cur
                    if n == b:
                        path = [b]
                        while prev[path[-1]] is not None:
                            path.append(prev[path[-1]])
                        path.reverse()
                        break
                    queue.append(n)
                if path:
                    break
    if path is None:
        if args.json:
            write_json(None)
        return EXIT_NOT_FOUND
    _dq_emit(args, path, human=" -> ".join(path))
    return EXIT_SUCCESS


def cmd_calling_code_for(reg, args) -> int:
    digits = "".join(ch for ch in args.number if ch not in " -().+")
    out = []
    if digits and digits.isascii() and digits.isdigit():
        out = sorted({
            e["alpha_2"] for e in reg["countries"]["active"]
            for cc in (e.get("calling_codes") or ()) if digits.startswith(cc)
        })
    _dq_emit(args, out)
    return EXIT_SUCCESS if out else EXIT_NOT_FOUND


def _dq_valid_date(s) -> bool:
    if not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return False
    try:
        _date(int(s[:4]), int(s[5:7]), int(s[8:]))
    except ValueError:
        return False
    return True


def _dq_currency_at(reg, code, date):
    """List or None. Mirrors CountryRegistry.currency_at (v1.11.1)."""
    act = _dq_active(reg).get(code)
    if act is not None:
        intro = act.get("introduced")
        if intro is None or date < intro:
            return None
        cc = act.get("currency_codes")
        return None if cc is None else list(cc)
    wd = next((w for w in reg["countries"]["withdrawn"]
               if w["alpha_2"] == code), None)
    if wd is None or not wd.get("withdrawal_date") or date > wd["withdrawal_date"]:
        return None
    intro = wd.get("introduced")
    if intro is not None and date < intro:
        return None
    edges, out, seen, stack = _dq_edges(reg), set(), set(), [code]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if cur in _dq_active(reg):
            out.update(_dq_active(reg)[cur].get("currency_codes") or ())
        else:
            stack.extend(edges.get(cur, ()))
    return sorted(out) or None


def cmd_currency_at(reg, args) -> int:
    code, date = args.code.strip().upper(), args.date
    if not _dq_valid_date(date):
        print(f"error: malformed date: {date!r} (want YYYY-MM-DD)", file=sys.stderr)
        return EXIT_USAGE
    known = code in _dq_active(reg) or any(
        w["alpha_2"] == code for w in reg["countries"]["withdrawn"])
    if not known:
        if args.json:
            write_json(None)
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    result = _dq_currency_at(reg, code, date)
    if result is None:
        if args.json:
            write_json(None)
        return EXIT_UNKNOWN
    _dq_emit(args, result)
    return EXIT_SUCCESS


def _dq_is_active_on(reg, code, date):
    """Tri-state: True, False or None. Mirrors CountryRegistry.is_active_on."""
    if not _dq_valid_date(date):
        return False
    act = _dq_active(reg).get(code)
    if act is not None:
        intro = act.get("introduced")
        return None if intro is None else date >= intro
    wd = next((w for w in reg["countries"]["withdrawn"]
               if w["alpha_2"] == code), None)
    if wd is None or not wd.get("withdrawal_date"):
        return False
    if date > wd["withdrawal_date"]:
        return False
    intro = wd.get("introduced")
    if intro is None:
        # Start unknown: ISO 3166 began in 1974, nothing earlier is known.
        return None if date < "1974-01-01" else True
    return intro <= date


def cmd_introduced(reg, args) -> int:
    code = args.code.strip().upper()
    e = find_entry(reg, code)
    if e is None:
        print(f"error: not found: {args.code}", file=sys.stderr)
        return EXIT_NOT_FOUND
    value = e.get("introduced")
    if args.json:
        write_json({"code": code, "introduced": value,
                    "result": "unknown" if value is None else value})
    else:
        print("unknown" if value is None else value)
    return EXIT_UNKNOWN if value is None else EXIT_SUCCESS


def cmd_is_active_on(reg, args) -> int:
    code, date = args.code.strip().upper(), args.date
    if not _dq_valid_date(date):
        print(f"error: malformed date: {date!r} (want YYYY-MM-DD)", file=sys.stderr)
        return EXIT_USAGE
    result = _dq_is_active_on(reg, code, date)
    text = "unknown" if result is None else ("true" if result else "false")
    if args.json:
        write_json({"code": code, "date": date,
                    "is_active_on": result, "result": text})
    else:
        print(text)
    return EXIT_UNKNOWN if result is None else (EXIT_SUCCESS if result else EXIT_NOT_FOUND)


def cmd_region_countries(reg, args) -> int:
    r = args.region.lower()
    s = args.subregion.lower() if args.subregion else None
    out = sorted(
        e["alpha_2"] for e in reg["countries"]["active"]
        if (e.get("region") or "").lower() == r
        and (s is None or (e.get("subregion") or "").lower() == s)
    )
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
    sp.add_argument("--withdrawn-since", metavar="YYYY-MM-DD",
                    help="With --withdrawn: only entries withdrawn on or after this date.")
    sp.add_argument("--withdrawn-before", metavar="YYYY-MM-DD",
                    help="With --withdrawn: only entries withdrawn before this date.")
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

    # -- Derived queries (v1.10.0) --
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
            print("error: --raw needs a FIELD for info", file=sys.stderr)
            return EXIT_USAGE
        args.raw = "code" if args.command == "validate" else "alpha_2"

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
