#!/usr/bin/env python3
"""
check_introduced_evidence.py: the `introduced` evidence ledger is well formed
and agrees with the tree.

Reads tools/introduced_evidence.json, tools/introduced_snapshot.json and
iso3166.json. The decision is docs/decisions/introduced-evidence.md.

Rules
-----
 1. Format. The file has `rows`, a list. Each row has exactly the keys
    code, current, candidate, class, doc, quote_ref, verdict, reason, and
    may have recheck_date, more_docs (further documents, each held to rule
    5) and bound (a predecessor bound: {"not_before": YYYY[-MM[-DD]],
    "doc": a document held to rule 5}; inference only, it sets nothing). class is iso_primary, ma_member, lead_only or
    inference; verdict is adopted, conflict or unconfirmed; current and
    candidate are null or YYYY-MM-DD; a recheck_date is YYYY-MM-DD.
 2. One row per code. The codes are exactly the keys of the snapshot's
    `data`, once each, in sorted order.
 3. current is the snapshot's value for the code.
 4. adopted only with iso_primary. An ma_member, lead_only or inference row
    is never adopted.
 5. An iso_primary row names its document: doc has title, urls (at least
    one), locator and a 64-hex sha256 (D2/D3: the bytes read are not
    committed, their hash is).
 6. Every adopted row has a candidate equal to the entry's `introduced` in
    iso3166.json (the active entry, or a withdrawn entry whose code is not
    also active), and equal to current. An adopted date is not earlier than
    the row's bound, if it has one.
 9. A document URL on web.archive.org is an `id_` capture
    (https://web.archive.org/web/<14-digit timestamp>id_/...) and comes with
    the iso.org URL it captured (D2).
 7. A conflict row has a candidate that differs from current.
 8. A recheck_date must not have passed (--today, default today).

Exit codes: 0 all rules hold; 1 a rule is broken (each is printed);
2 an input is missing or is not JSON.

Usage:
    python3 tools/check_introduced_evidence.py
    python3 tools/check_introduced_evidence.py --root path/to/repo --today 2027-01-01
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
KEYS = ("code", "current", "candidate", "class", "doc", "quote_ref", "verdict", "reason")
OPTIONAL = ("recheck_date", "more_docs", "bound")
CLASSES = ("iso_primary", "ma_member", "lead_only", "inference")
VERDICTS = ("adopted", "conflict", "unconfirmed")
DOC_KEYS = ("title", "number", "date", "urls", "locator", "sha256", "retrieved")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ARCHIVE_RE = re.compile(r"^https://web\.archive\.org/web/\d{14}id_/(https?://(www\.)?iso\.org[:/].*)$")
BOUND_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def doc_problems(doc) -> list[str]:
    """Rule 5 and rule 9 for one document; empty when it is citable."""
    if not isinstance(doc, dict) or set(doc) != set(DOC_KEYS):
        return [f"doc keys are not {list(DOC_KEYS)}"]
    out = []
    if not (isinstance(doc.get("title"), str) and doc["title"].strip()
            and isinstance(doc.get("urls"), list) and doc["urls"]
            and all(isinstance(u, str) and u.startswith("http") for u in doc["urls"])
            and isinstance(doc.get("locator"), str) and doc["locator"].strip()
            and isinstance(doc.get("sha256"), str) and SHA_RE.match(doc["sha256"])):
        out.append("needs doc with title, urls, locator and a 64-hex sha256")
    urls = doc.get("urls") if isinstance(doc.get("urls"), list) else []
    for u in urls:
        if isinstance(u, str) and "web.archive.org" in u:
            m = ARCHIVE_RE.match(u)
            if not m:
                out.append(f"archive URL {u!r} is not an id_ capture of an iso.org URL")
            elif not any(isinstance(o, str) and "web.archive.org" not in o and "iso.org" in o for o in urls):
                out.append(f"archive URL {u!r} without the iso.org URL it captured")
    return out


def _is_date(v) -> bool:
    if not isinstance(v, str) or not DATE_RE.match(v):
        return False
    try:
        date.fromisoformat(v)
    except ValueError:
        return False
    return True


def problems(ledger: dict, snapshot: dict, tree: dict, today: date) -> list[str]:
    out: list[str] = []
    rows = ledger.get("rows") if isinstance(ledger, dict) else None
    if not isinstance(rows, list):
        return ["ledger has no `rows` list"]
    data = snapshot.get("data", {})
    introduced = {e["alpha_2"]: e.get("introduced") for e in tree["countries"]["active"]}
    for e in tree["countries"].get("withdrawn", []):
        introduced.setdefault(e["alpha_2"], e.get("introduced"))

    codes = [r.get("code") if isinstance(r, dict) else None for r in rows]
    if codes != sorted(data):
        missing = sorted(set(data) - set(codes))
        extra = sorted(set(c for c in codes if c) - set(data))
        dup = sorted({c for c in codes if c and codes.count(c) > 1})
        out.append("rows are not one per snapshot code in sorted order"
                   + (f"; missing {missing}" if missing else "")
                   + (f"; not in snapshot {extra}" if extra else "")
                   + (f"; duplicated {dup}" if dup else ""))

    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            out.append(f"rows[{i}] is not an object")
            continue
        c = r.get("code", f"rows[{i}]")
        keys = set(r)
        if not set(KEYS) <= keys or keys - set(KEYS) - set(OPTIONAL):
            out.append(f"{c}: keys {sorted(keys)} are not {list(KEYS)} (+ optional {list(OPTIONAL)})")
            continue
        for k in ("current", "candidate"):
            if r[k] is not None and not _is_date(r[k]):
                out.append(f"{c}: {k} {r[k]!r} is not null or YYYY-MM-DD")
        if r["class"] not in CLASSES:
            out.append(f"{c}: class {r['class']!r} not in {list(CLASSES)}")
        if r["verdict"] not in VERDICTS:
            out.append(f"{c}: verdict {r['verdict']!r} not in {list(VERDICTS)}")
        if not isinstance(r["reason"], str) or not r["reason"].strip():
            out.append(f"{c}: reason is empty")
        if r["quote_ref"] is not None and not isinstance(r["quote_ref"], str):
            out.append(f"{c}: quote_ref is not a string or null")
        doc = r["doc"]
        if doc is not None and (not isinstance(doc, dict) or set(doc) != set(DOC_KEYS)):
            out.append(f"{c}: doc keys are not {list(DOC_KEYS)}")
            doc = None
        if "recheck_date" in r:
            if not _is_date(r["recheck_date"]):
                out.append(f"{c}: recheck_date {r['recheck_date']!r} is not YYYY-MM-DD")
            elif date.fromisoformat(r["recheck_date"]) < today:
                out.append(f"{c}: recheck_date {r['recheck_date']} has passed ({today.isoformat()})")

        if c in data and r["current"] != data[c]:
            out.append(f"{c}: current {r['current']!r} != snapshot {data[c]!r}")
        if r["verdict"] == "adopted" and r["class"] != "iso_primary":
            out.append(f"{c}: adopted with class {r['class']}; only iso_primary can be adopted")
        if r["class"] == "iso_primary":
            for p in doc_problems(doc):
                out.append(f"{c}: iso_primary {p}")
        if "more_docs" in r:
            if not isinstance(r["more_docs"], list) or not r["more_docs"]:
                out.append(f"{c}: more_docs is not a non-empty list")
            else:
                for j, d in enumerate(r["more_docs"]):
                    for p in doc_problems(d):
                        out.append(f"{c}: more_docs[{j}] {p}")
        bound = r.get("bound")
        if "bound" in r:
            if not isinstance(bound, dict) or set(bound) != {"not_before", "doc"} \
                    or not isinstance(bound.get("not_before"), str) or not BOUND_RE.match(bound["not_before"]):
                out.append(f"{c}: bound is not {{not_before: YYYY[-MM[-DD]], doc}}")
                bound = None
            else:
                for p in doc_problems(bound["doc"]):
                    out.append(f"{c}: bound {p}")
        if r["verdict"] == "adopted":
            if r["candidate"] is None:
                out.append(f"{c}: adopted with no candidate")
            elif c not in introduced:
                out.append(f"{c}: adopted, but {c} is not an entry of iso3166.json")
            elif introduced[c] != r["candidate"]:
                out.append(f"{c}: adopted {r['candidate']} != iso3166.json introduced {introduced[c]!r}")
            elif r["current"] != r["candidate"]:
                out.append(f"{c}: adopted {r['candidate']} != current {r['current']!r}")
            if bound and r["candidate"] and r["candidate"][:len(bound["not_before"])] < bound["not_before"]:
                out.append(f"{c}: adopted {r['candidate']} is before its bound {bound['not_before']}")
        if r["verdict"] == "conflict" and r["candidate"] == r["current"]:
            out.append(f"{c}: conflict, but candidate equals current")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = ap.parse_args(argv)
    try:
        ledger = json.loads((args.root / "tools/introduced_evidence.json").read_text(encoding="utf-8"))
        snapshot = json.loads((args.root / "tools/introduced_snapshot.json").read_text(encoding="utf-8"))
        tree = json.loads((args.root / "iso3166.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    found = problems(ledger, snapshot, tree, args.today)
    rows = ledger.get("rows", []) if isinstance(ledger, dict) else []
    counts: dict[str, int] = {}
    for r in rows:
        if isinstance(r, dict):
            k = f"{r.get('class')}/{r.get('verdict')}"
            counts[k] = counts.get(k, 0) + 1
    for p in found:
        print(f"FAIL: {p}")
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    if found:
        print(f"{len(found)} problem(s) in tools/introduced_evidence.json ({summary})")
        return 1
    print(f"OK: {len(rows)} rows ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
