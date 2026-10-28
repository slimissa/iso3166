#!/usr/bin/env python3
"""
tools/build_introduced_snapshot.py

Generates tools/introduced_snapshot.json from tools/wikipedia_dates.json
and iso3166.json. Deterministic. The snapshot is a derived artifact.

Algorithm for `introduced` (active entries):
  1. status != officially-assigned          -> null (not part of the standard)
  2. code in QUARANTINE                      -> null (source conflicts with tree)
  3. code in LIST_1974                       -> "1974-09-15"
  4. code in wikipedia_dates.json "data"     -> that date
  5. otherwise                               -> null (source silent)
Withdrawn entries are always null.

Usage:
  python3 tools/build_introduced_snapshot.py          # write snapshot
  python3 tools/build_introduced_snapshot.py --check  # exit 1 on drift
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools" / "wikipedia_dates.json"
TREE = ROOT / "iso3166.json"
OUT = ROOT / "tools" / "introduced_snapshot.json"
EDITION_1974 = "1974-09-15"
REVIEW_BY = "2027-10-28"
SOURCE_ACCESSED = "2026-10-28"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Maintainer-supplied list of codes in the original 1974 edition.
LIST_1974 = [
    "AD", "AE", "AF", "AG", "AL", "AM", "AO", "AR", "AT", "AU", "AZ",
    "BB", "BD", "BE", "BG", "BH", "BI", "BJ", "BM", "BN", "BO", "BR",
    "BS", "BT", "BW", "BY", "BZ", "CA", "CF", "CG", "CH", "CI", "CL",
    "CM", "CN", "CO", "CR", "CU", "CV", "CY", "CZ", "DE", "DJ", "DK",
    "DM", "DO", "DZ", "EC", "EE", "EG", "ES", "ET", "FI", "FJ", "FR",
    "GA", "GB", "GD", "GE", "GH", "GL", "GM", "GN", "GQ", "GR", "GT",
    "GW", "GY", "HK", "HN", "HT", "HU", "ID", "IE", "IL", "IN", "IQ",
    "IR", "IS", "IT", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM",
    "KP", "KR", "KW", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS",
    "LT", "LU", "LV", "LY", "MA", "MC", "MG", "ML", "MM", "MN", "MO",
    "MR", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NE", "NG",
    "NI", "NL", "NO", "NP", "NR", "NZ", "OM", "PA", "PE", "PG", "PH",
    "PK", "PL", "PT", "PY", "QA", "RO", "RU", "RW", "SA", "SB", "SC",
    "SD", "SE", "SG", "SI", "SK", "SL", "SM", "SN", "SO", "SR", "ST",
    "SV", "SY", "SZ", "TD", "TG", "TH", "TJ", "TM", "TN", "TO", "TR",
    "TT", "TV", "TW", "TZ", "UA", "UG", "US", "UY", "UZ", "VA", "VC",
    "VE", "VN", "VU", "WS", "YE", "ZA", "ZM", "ZW"
]

# Codes in LIST_1974 or the source `data` whose date is contradicted by the
# tree or by well-known history. They are set to null until the maintainer
# overrides them. Remove an entry here to accept the list/source value.
QUARANTINE = {
    "AM": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "AZ": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "BA": ("likely", "2002-05-20 is a change newsletter; Bosnia added ~1992"),
    "BJ": ("confirmed", "successor of DY, withdrawn 1977-02-01 (tree)"),
    "BY": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "CZ": ("likely", "successor state of Czechoslovakia/Yugoslavia; not a 1974 code"),
    "DJ": ("confirmed", "successor of AI, withdrawn 1977-06-27 (tree)"),
    "EE": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "ER": ("likely", "2012-02-15 is a change newsletter; Eritrea was added later (~1993)"),
    "GE": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "KG": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "KI": ("confirmed", "successor of CT, withdrawn 1984-01-01 (tree)"),
    "KZ": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "LT": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "LV": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "MD": ("likely", "2008-03-31 is a change newsletter; Moldova added ~1992"),
    "MM": ("confirmed", "successor of BU, withdrawn 1989-12-05 (tree)"),
    "RU": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "SH": ("likely", "2010-02-22 is a change newsletter; Saint Helena predates it"),
    "SI": ("likely", "successor state of Czechoslovakia/Yugoslavia; not a 1974 code"),
    "SK": ("likely", "successor state of Czechoslovakia/Yugoslavia; not a 1974 code"),
    "TJ": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "TM": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "UA": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "UZ": ("likely", "post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition"),
    "VU": ("confirmed", "successor of NH, withdrawn 1980-07-30 (tree)"),
    "ZW": ("confirmed", "successor of RH, withdrawn 1980-04-18 (tree)")
}


def build():
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    data = src["data"]
    active = tree["countries"]["active"]
    withdrawn = tree["countries"]["withdrawn"]
    codes_all = {e["alpha_2"] for e in active} | {e["alpha_2"] for e in withdrawn}
    unknown = sorted(set(data) - codes_all)
    if unknown:
        raise SystemExit("source codes unknown to the tree: %s" % unknown)
    list_set = set(LIST_1974)
    not_active = sorted(list_set - {e["alpha_2"] for e in active})
    if not_active:
        raise SystemExit("1974 list codes not active in tree: %s" % not_active)

    out, reasons = {}, {}
    counts = {"active_from_1974_list": 0, "active_from_data": 0,
              "active_null_not_assigned": 0, "active_null_quarantined": 0,
              "active_null_source_silent": 0, "withdrawn_null": 0}
    for e in sorted(active, key=lambda x: x["alpha_2"]):
        c = e["alpha_2"]
        if e.get("status") != "officially-assigned":
            out[c] = None
            reasons[c] = "not officially assigned (%s)" % e.get("status")
            counts["active_null_not_assigned"] += 1
        elif c in QUARANTINE:
            out[c] = None
            reasons[c] = "quarantined [%s]: %s" % QUARANTINE[c]
            counts["active_null_quarantined"] += 1
        elif c in list_set:
            out[c] = EDITION_1974
            counts["active_from_1974_list"] += 1
        elif c in data:
            out[c] = data[c]
            counts["active_from_data"] += 1
        else:
            out[c] = None
            reasons[c] = "source silent"
            counts["active_null_source_silent"] += 1
    # AI and SK are both active and withdrawn (reassigned codes). Keys are
    # alpha_2, so a withdrawn entry never overwrites an active one; the
    # active value is already null or sourced for these two codes.
    withdrawn_codes = []
    for e in sorted(withdrawn, key=lambda x: x["alpha_2"]):
        withdrawn_codes.append(e["alpha_2"])
        counts["withdrawn_null"] += 1
        if e["alpha_2"] not in out:
            out[e["alpha_2"]] = None
            reasons[e["alpha_2"]] = "withdrawn: start date not sourced"

    for c, v in out.items():
        if v is not None:
            if not DATE_RE.match(v):
                raise SystemExit("malformed date %s=%s" % (c, v))
            if v < "1974-01-01" or v > SOURCE_ACCESSED:
                raise SystemExit("date out of range %s=%s" % (c, v))
    snap = {
        "meta": {
            "counts": dict(sorted(counts.items())),
            "default_date_1974_edition": EDITION_1974,
            "generator": "tools/build_introduced_snapshot.py",
            "withdrawn_codes": withdrawn_codes,
            "null_reasons": dict(sorted(reasons.items())),
            "review_by": REVIEW_BY,
            "shared_codes_active_and_withdrawn": sorted(set(withdrawn_codes) & {e["alpha_2"] for e in active}),
            "source": src["meta"]["source"],
            "source_accessed": SOURCE_ACCESSED,
            "source_permalink": src["meta"]["permalink"],
        },
        "data": dict(sorted(out.items())),
    }
    return json.dumps(snap, indent=2, ensure_ascii=False) + "\n"


def main(argv):
    text = build()
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("introduced_snapshot.json is out of date", file=sys.stderr)
            return 1
        print("introduced_snapshot.json is up to date")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
