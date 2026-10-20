#!/usr/bin/env python3
"""Populate the `independent` field from ISO 3166-1 (OBP) and record an audit trail.

Semantic (schema.json): "Whether ISO 3166-1 designates the entity as
independent". Source: the ISO Online Browsing Platform page for each
alpha-2 code, https://www.iso.org/obp/ui/#iso:code:3166:<CC>.

Rules:
  * Active entries: the OBP "Independent" value, except three overrides
    applied without any lookup: XK true, TW false, EU false.
  * Active entries that are not officially assigned and have no override
    (today: UK) have no OBP entry. They are NOT guessed: the value is
    left unchanged and the entry is listed as unresolved.
  * Withdrawn entries: a hardcoded per-code table (11 true, 14 false);
    no network access. A withdrawn code missing from the table aborts
    the run.
  * All-or-nothing: if any active entry cannot be resolved from its page,
    nothing is written.

Modes (exactly one):
  --check     Compare iso3166.json with tools/independent_snapshot.json.
              Missing or empty snapshot -> exit 0 with a warning ("not yet
              run"). Populated snapshot with any mismatch -> exit 1.
  --dry-run   Fetch, resolve, print the distribution, write nothing.
  --write     Fetch, resolve, write iso3166.json and the snapshot.

Optional: --html-dir DIR reads DIR/<CC>.html instead of the network (for
pages saved from a browser, see below). --delay SECONDS paces live fetches.

Exit codes: 0 ok, 1 data problem (mismatch, unparseable page, unknown
withdrawn code), 2 usage or network failure (nothing written).

After --write, regenerate derived files and re-run the gates:
    python3 tools/export_sql.py && python3 tools/export_csv.py \\
      && python3 tools/export_parquet.py && python3 tools/sync_wrappers.py \\
      && python3 tools/gen_consistency_fixture.py
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enrich_field as ef  # noqa: E402  (registry load/write helpers)

SNAPSHOT = Path("tools/independent_snapshot.json")
OBP_URL = "https://www.iso.org/obp/ui/#iso:code:3166:{code}"
SNAPSHOT_SOURCE = "ISO 3166-1 Online Browsing Platform"
SNAPSHOT_SCHEMA_VERSION = "1.0.0"

OVERRIDES: dict[str, tuple[bool, str]] = {
    "XK": (True, "user-assigned code; independence recognised by most states"),
    "TW": (False, "ISO 3166-1 treats Taiwan as a Province of China"),
    "EU": (False, "supranational organisation, not a sovereign state"),
}
WITHDRAWN_TRUE = frozenset("BU CS DD DY HV SU TP VD YD YU ZR".split())
WITHDRAWN_FALSE = frozenset("AI AN CT FQ JT MI NH NQ NT PC PZ RH SK WK".split())
assert len(WITHDRAWN_TRUE) == 11 and len(WITHDRAWN_FALSE) == 14
assert not (WITHDRAWN_TRUE & WITHDRAWN_FALSE)

EMPTY_WARNING = "enrich_independent: snapshot empty; run --write to populate"


class NetworkError(Exception):
    """The source could not be reached at all (abort, do not guess)."""


Fetcher = Callable[[str], str]


def parse_independent(page: str) -> bool | None:
    """Return the OBP 'Independent' value, or None if it cannot be found.

    ASSUMPTION (not verified against live ISO markup): the page text
    contains the label "Independent" followed by Yes or No. Anything
    ambiguous or absent returns None; the caller treats that as a failure.
    """
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    text = re.sub(r"\s+", " ", text)
    found = {m.lower() for m in re.findall(r"\bIndependent\s*:?\s*(Yes|No)\b", text, re.I)}
    if found == {"yes"}:
        return True
    if found == {"no"}:
        return False
    return None


def live_fetcher(delay: float) -> Fetcher:
    state = {"first": True}

    def fetch(code: str) -> str:
        if not state["first"]:
            time.sleep(delay)
        state["first"] = False
        req = urllib.request.Request(
            OBP_URL.format(code=code),
            headers={"User-Agent": "iso3166-enrich_independent/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise LookupError(f"HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise NetworkError(str(exc)) from exc

    return fetch


def dir_fetcher(directory: Path) -> Fetcher:
    def fetch(code: str) -> str:
        path = directory / f"{code}.html"
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise LookupError(f"cannot read {path}") from exc

    return fetch


def resolve(reg: dict[str, Any], fetch: Fetcher) -> dict[str, Any]:
    """Compute the new values. Pure apart from `fetch`. Raises NetworkError."""
    active: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    unresolved: list[str] = []
    for e in reg["countries"]["active"]:
        code = e["alpha_2"]
        if code in OVERRIDES:
            value, why = OVERRIDES[code]
            active[code] = {"value": value, "source_url": None, "override": why}
        elif e["status"] != "officially-assigned":
            unresolved.append(code)
        else:
            try:
                value = parse_independent(fetch(code))
            except LookupError as exc:
                failures.append(f"{code}: {exc}")
                continue
            if value is None:
                failures.append(f"{code}: no 'Independent' Yes/No found on the page")
                continue
            active[code] = {"value": value, "source_url": OBP_URL.format(code=code)}
    withdrawn: dict[str, bool] = {}
    for e in reg["countries"]["withdrawn"]:
        code = e["alpha_2"]
        if code in WITHDRAWN_TRUE:
            withdrawn[code] = True
        elif code in WITHDRAWN_FALSE:
            withdrawn[code] = False
        else:
            failures.append(f"withdrawn {code}: not in the per-code table")
    return {"active": active, "withdrawn": withdrawn,
            "failures": failures, "unresolved": unresolved}


def distribution(reg: dict[str, Any], plan: dict[str, Any]) -> dict[str, int]:
    d = {"to_true": 0, "to_false": 0, "unchanged": 0}
    cur = {e["alpha_2"]: e["independent"] for e in reg["countries"]["active"]}
    for code, info in plan["active"].items():
        if info["value"] == cur[code]:
            d["unchanged"] += 1
        else:
            d["to_true" if info["value"] else "to_false"] += 1
    d["unresolved"] = len(plan["unresolved"])
    return d


def snapshot_doc(plan: dict[str, Any], now: str) -> dict[str, Any]:
    entries = {}
    for code in sorted(plan["active"]):
        info = plan["active"][code]
        row = {"value": info["value"], "source_url": info["source_url"],
               "extracted_at": now}
        if "override" in info:
            row["override"] = info["override"]
        entries[code] = row
    return {"meta": {"source": SNAPSHOT_SOURCE,
                     "schema_version": SNAPSHOT_SCHEMA_VERSION,
                     "extracted_at": now},
            "entries": entries}


def cmd_run(reg_path: Path, snap_path: Path, fetch: Fetcher, *, write: bool,
            now: str, out=print) -> int:
    reg = ef.load_registry(reg_path)
    try:
        plan = resolve(reg, fetch)
    except NetworkError as exc:
        out(f"enrich_independent: cannot reach the source ({exc}); no changes made")
        return 2
    if plan["failures"]:
        out(f"enrich_independent: {len(plan['failures'])} problem(s); nothing written:")
        for f in plan["failures"][:25]:
            out(f"  {f}")
        return 1
    d = distribution(reg, plan)
    cur_w = {e["alpha_2"]: e["independent"] for e in reg["countries"]["withdrawn"]}
    w_changed = sum(1 for c, v in plan["withdrawn"].items() if cur_w[c] != v)
    out(f"active: {d['to_true']} would become true, {d['to_false']} would become false, "
        f"{d['unchanged']} unchanged, {d['unresolved']} unresolved (no OBP entry): "
        f"{', '.join(plan['unresolved']) or 'none'}")
    out(f"withdrawn: {w_changed} of {len(plan['withdrawn'])} would change "
        f"({sum(plan['withdrawn'].values())} true, "
        f"{len(plan['withdrawn']) - sum(plan['withdrawn'].values())} false)")
    if not write:
        out("dry run: nothing written")
        return 0
    for e in reg["countries"]["active"]:
        if e["alpha_2"] in plan["active"]:
            e["independent"] = plan["active"][e["alpha_2"]]["value"]
    for e in reg["countries"]["withdrawn"]:
        e["independent"] = plan["withdrawn"][e["alpha_2"]]
    ef.write_registry(reg_path, reg)
    snap_path.write_text(
        json.dumps(snapshot_doc(plan, now), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    out(f"wrote {reg_path} and {snap_path}")
    return 0


def _warn(msg: str) -> None:
    print(msg, file=sys.stderr)


def cmd_check(reg_path: Path, snap_path: Path, out=print, warn=_warn) -> int:
    try:
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        snap = {}
    entries = snap.get("entries") or {}
    if not entries:
        warn(EMPTY_WARNING)
        return 0
    reg = ef.load_registry(reg_path)
    diffs: list[str] = []
    seen = set()
    for e in reg["countries"]["active"]:
        code = e["alpha_2"]
        seen.add(code)
        if code not in entries:
            if e["status"] == "officially-assigned" or code in OVERRIDES:
                diffs.append(f"{code}: missing from snapshot")
            continue
        if entries[code]["value"] != e["independent"]:
            diffs.append(f"{code}: iso3166.json {e['independent']} != snapshot {entries[code]['value']}")
    for code in sorted(set(entries) - seen):
        diffs.append(f"{code}: in snapshot but not an active entry")
    for e in reg["countries"]["withdrawn"]:
        want = e["alpha_2"] in WITHDRAWN_TRUE
        if e["alpha_2"] not in WITHDRAWN_TRUE | WITHDRAWN_FALSE:
            diffs.append(f"withdrawn {e['alpha_2']}: not in the per-code table")
        elif e["independent"] != want:
            diffs.append(f"withdrawn {e['alpha_2']}: iso3166.json {e['independent']} != table {want}")
    if diffs:
        out(f"enrich_independent: {len(diffs)} mismatch(es):")
        for d in diffs[:40]:
            out(f"  {d}")
        return 1
    out(f"enrich_independent: OK ({len(entries)} active entries match the snapshot)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--write", action="store_true")
    ap.add_argument("--html-dir", type=Path, default=None,
                    help="read DIR/<CC>.html instead of the network")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="seconds between live requests (default 0.5)")
    ap.add_argument("--registry", type=Path, default=ef.REGISTRY)
    ap.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    args = ap.parse_args(argv)

    if args.check:
        return cmd_check(args.registry, args.snapshot)
    fetch = dir_fetcher(args.html_dir) if args.html_dir else live_fetcher(args.delay)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return cmd_run(args.registry, args.snapshot, fetch, write=args.write, now=now)


if __name__ == "__main__":
    sys.exit(main())
