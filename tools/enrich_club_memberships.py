#!/usr/bin/env python3
"""tools/enrich_club_memberships.py

Populate four date-scoped membership arrays on every ACTIVE entry of
iso3166.json from the Phase 1 snapshots (docs/decisions/club-memberships.md):

    eu_membership          <- tools/eu_membership_snapshot.json
    eea_membership         <- tools/eea_membership_snapshot.json
    eurozone_membership    <- tools/eurozone_membership_snapshot.json
    customs_union          <- tools/customs_union_snapshot.json

Each array is a list of {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD" | null}
ranges. `to` is the last day of membership, inclusive; null means current.
An entry that is not in a snapshot gets []. Withdrawn entries do not carry
these fields. The arrays are copies of the snapshot lists, so the snapshot
stays the single source of truth.

One exception (v1.12.1): the EEA snapshot may carry
meta.provisional_application, {code: {"from", "to"}}, the range during
which the EEA Enlargement Agreement applied provisionally before its formal
entry into force. It is unioned into eea_membership, so the array says when
EEA rules applied, formal or provisional. The provisional `to` must be the
day before the state's first formal `from` (no gap, no overlap).

Modes (exactly one):
  --check   Exit 1 if iso3166.json differs from what --write would produce.
  --write   Rewrite iso3166.json (same formatting as the other enrichers).

Exit codes: 0 ok, 1 mismatch or bad snapshot, 2 usage or missing file.

After --write, regenerate the derived copies:
    python3 tools/sync_wrappers.py && python3 tools/gen_consistency_fixture.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "iso3166.json"

FIELDS = {
    "eu_membership": "tools/eu_membership_snapshot.json",
    "eea_membership": "tools/eea_membership_snapshot.json",
    "eurozone_membership": "tools/eurozone_membership_snapshot.json",
    "customs_union": "tools/customs_union_snapshot.json",
}


def _die(msg: str, code: int = 2) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def check_ranges(label: str, code: str, ranges) -> None:
    if not isinstance(ranges, list) or not ranges:
        _die(f"{label}: {code}: want a non-empty list of ranges", 1)
    prev_to = None
    for i, r in enumerate(ranges):
        if not isinstance(r, dict) or set(r) != {"from", "to"}:
            _die(f"{label}: {code}[{i}]: want exactly the keys from, to", 1)
        try:
            frm = date.fromisoformat(r["from"])
            to = date.fromisoformat(r["to"]) if r["to"] is not None else None
        except (TypeError, ValueError):
            _die(f"{label}: {code}[{i}]: not a real ISO date", 1)
        if len(r["from"]) != 10 or (r["to"] is not None and len(r["to"]) != 10):
            _die(f"{label}: {code}[{i}]: dates must be YYYY-MM-DD", 1)
        if to is not None and to < frm:
            _die(f"{label}: {code}[{i}]: to before from", 1)
        if i > 0:
            if prev_to is None:
                _die(f"{label}: {code}[{i}]: range follows an open-ended one", 1)
            if frm <= date.fromisoformat(prev_to):
                _die(f"{label}: {code}[{i}]: overlaps or is out of order", 1)
        prev_to = r["to"]


def union_ranges(ranges: list) -> list:
    """Sort and merge overlapping or adjacent ranges (to is inclusive)."""
    out: list = []
    for r in sorted(ranges, key=lambda x: x["from"]):
        if out:
            prev = out[-1]
            if prev["to"] is None:
                continue
            nxt_day = (date.fromisoformat(prev["to"]) + timedelta(days=1)).isoformat()
            if r["from"] <= nxt_day:
                if r["to"] is None or r["to"] > prev["to"]:
                    prev["to"] = r["to"]
                continue
        out.append(dict(r))
    return out


def apply_provisional(rel: str, data: dict, prov) -> dict:
    """Union meta.provisional_application into the formal ranges."""
    if prov is None:
        return data
    if not isinstance(prov, dict):
        _die(f"{rel}: meta.provisional_application must be an object", 1)
    merged = {c: [dict(r) for r in rs] for c, rs in data.items()}
    for code, r in prov.items():
        if code not in data:
            _die(f"{rel}: provisional_application: {code} has no formal range", 1)
        check_ranges("provisional_application", code, [r])
        if r["to"] is None:
            _die(f"{rel}: provisional_application: {code} must end before the formal date", 1)
        formal_from = data[code][0]["from"]
        day_after = (date.fromisoformat(r["to"]) + timedelta(days=1)).isoformat()
        if day_after != formal_from:
            _die(f"{rel}: provisional_application: {code} ends {r['to']}; the day after is "
                 f"{day_after}, but the formal range starts {formal_from} (gap or overlap)", 1)
        merged[code] = union_ranges(merged[code] + [dict(r)])
    return merged


def load_snapshot(field: str, rel: str, active: set) -> dict:
    p = ROOT / rel
    if not p.is_file():
        _die(f"{rel} not found (install the Phase 1 snapshots first)")
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _die(f"{rel}: invalid JSON: {exc}", 1)
    data = doc.get("data")
    if not isinstance(data, dict) or not data:
        _die(f"{rel}: missing or empty data object", 1)
    for code, ranges in data.items():
        if code not in active:
            _die(f"{rel}: {code} is not an active alpha_2 in iso3166.json", 1)
        check_ranges(field, code, ranges)
    return apply_provisional(rel, data, doc.get("meta", {}).get("provisional_application"))


def build(reg: dict) -> dict:
    """Return a copy of reg with the four fields set on every active entry."""
    active = {e["alpha_2"] for e in reg["countries"]["active"]}
    snaps = {f: load_snapshot(f, rel, active) for f, rel in FIELDS.items()}
    out = json.loads(json.dumps(reg))
    for e in out["countries"]["active"]:
        for f, snap in snaps.items():
            e[f] = [dict(r) for r in snap.get(e["alpha_2"], [])]
        # keep keys sorted, like every other enricher
    out["countries"]["active"] = [
        {k: e[k] for k in sorted(e)} for e in out["countries"]["active"]
    ]
    for e in out["countries"]["withdrawn"]:
        for f in FIELDS:
            e.pop(f, None)
    return out


def render(reg: dict) -> str:
    return json.dumps(reg, indent=2, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="enrich_club_memberships")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    if not REGISTRY.is_file():
        _die(f"{REGISTRY} not found")
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    want = render(build(reg))
    have = REGISTRY.read_text(encoding="utf-8")

    if args.check:
        if have != want:
            print("enrich_club_memberships: iso3166.json is out of date; "
                  "run --write", file=sys.stderr)
            return 1
        print("enrich_club_memberships: OK")
        return 0
    if have == want:
        print("enrich_club_memberships: no change")
        return 0
    REGISTRY.write_text(want, encoding="utf-8")
    n = len(reg["countries"]["active"])
    print(f"enrich_club_memberships: wrote 4 arrays on {n} active entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
