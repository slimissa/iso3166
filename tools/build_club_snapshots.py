#!/usr/bin/env python3
"""
tools/build_club_snapshots.py

Generates the four club-membership snapshots (and their sibling meta files):

  tools/eu_membership_snapshot.json
  tools/eea_membership_snapshot.json
  tools/eurozone_membership_snapshot.json
  tools/customs_union_snapshot.json

Deterministic. The tables below are transcribed by hand from Wikipedia
(see docs/decisions/club-memberships.md and SPEC.md "Source audit").
Nothing is fetched at run time.

Range semantics: {"from": first day of membership, "to": last day of
membership (inclusive) or null if still a member}. Countries that are not
in a club have no key. Ranges for a country are sorted and disjoint.

Usage:
  python3 tools/build_club_snapshots.py          # write snapshots
  python3 tools/build_club_snapshots.py --check  # exit 1 on drift
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TREE = ROOT / "iso3166.json"
TOOLS = ROOT / "tools"

ACCESSED_AT = "2026-10-29"
REVIEW_BY = "2027-10-29"
CADENCE = "annual"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

WP = "https://en.wikipedia.org/wiki/"
PERMALINK_NOTE = (
    "Canonical title URL, not an oldid permalink: the research tool "
    "returned page text without revision ids. Pin an oldid at the next review."
)

# ---- EU (Wikipedia: Member state of the European Union) -----------------
EEC_ENTRY = "1958-01-01"  # table says only "Founder"; see ADR [Likely]
EU_FOUNDERS = ["BE", "DE", "FR", "IT", "LU", "NL"]
EU_JOIN = {
    "1973-01-01": ["DK", "IE", "GB"],
    "1981-01-01": ["GR"],
    "1986-01-01": ["ES", "PT"],
    "1995-01-01": ["AT", "FI", "SE"],
    "2004-05-01": ["CY", "CZ", "EE", "HU", "LT", "LV", "MT", "PL", "SI", "SK"],
    "2007-01-01": ["BG", "RO"],
    "2013-07-01": ["HR"],
}
GB_EU_LEFT = "2020-01-31"          # Wikipedia: ceased to be a member state
GB_TRANSITION_END = "2020-12-31"   # Wikipedia: transition arrangements ended

# ---- EEA (Wikipedia: European Economic Area, state table) ---------------
# `from` = "Entered into force" column (formal). Provisional application
# dates are carried in meta.provisional_application, not in the ranges.
EEA_JOIN = {
    "1994-01-01": ["AT", "BE", "DE", "DK", "ES", "FI", "FR", "GB", "GR", "IE",
                   "IS", "IT", "LU", "NL", "NO", "PT", "SE"],
    "1995-05-01": ["LI"],
    "2005-12-06": ["CY", "CZ", "EE", "HU", "LT", "LV", "MT", "PL", "SI", "SK"],
    "2011-11-09": ["BG", "RO"],
    "2025-02-19": ["HR"],
}
EEA_PROVISIONAL = {
    "2004-05-01": {"codes": ["CY", "CZ", "EE", "HU", "LT", "LV", "MT", "PL", "SI", "SK"],
                   "formal": "2005-12-06"},
    "2007-08-01": {"codes": ["BG", "RO"], "formal": "2011-11-09"},
    "unknown_in_source": {"codes": ["HR"], "formal": "2025-02-19",
                          "note": "Wikipedia says 'provisionally applied' after the April 2014 signing, with no date"},
}

# ---- Eurozone (Wikipedia: Eurozone / Euro area) -------------------------
EZ_JOIN = {
    "1999-01-01": ["AT", "BE", "DE", "ES", "FI", "FR", "IE", "IT", "LU", "NL", "PT"],
    "2001-01-01": ["GR"],
    "2007-01-01": ["SI"],
    "2008-01-01": ["CY", "MT"],
    "2009-01-01": ["SK"],
    "2011-01-01": ["EE"],
    "2014-01-01": ["LV"],
    "2015-01-01": ["LT"],
    "2023-01-01": ["HR"],
    "2026-01-01": ["BG"],
}

# ---- Customs union (Wikipedia: European Union Customs Union) ------------
CU_ESTABLISHED = "1968-07-01"  # page: Establishment 1968; Jungholz "from 1 July 1968"
CU_NON_EU = {
    "MC": "1968-07-01",  # page gives year only ("1968"); day is a [Guess]
    "AD": "1991-01-01",  # excludes agricultural produce
    "TR": "1995-12-31",  # excludes agricultural produce
    "SM": "2002-04-01",
}


def _rng(frm, to=None):
    return {"from": frm, "to": to}


def build_eu():
    d = {c: [_rng(EEC_ENTRY)] for c in EU_FOUNDERS}
    for frm, codes in EU_JOIN.items():
        for c in codes:
            d[c] = [_rng(frm)]
    d["GB"] = [_rng("1973-01-01", GB_EU_LEFT)]
    return d


def build_eea():
    d = {}
    for frm, codes in EEA_JOIN.items():
        for c in codes:
            d[c] = [_rng(frm)]
    d["GB"] = [_rng("1994-01-01", GB_TRANSITION_END)]
    return d


def build_ez():
    d = {}
    for frm, codes in EZ_JOIN.items():
        for c in codes:
            d[c] = [_rng(frm)]
    return d


def build_cu():
    d = {}
    for c, rs in build_eu().items():
        r = rs[0]
        frm = max(r["from"], CU_ESTABLISHED)
        to = GB_TRANSITION_END if c == "GB" else r["to"]
        d[c] = [_rng(frm, to)]
    for c, frm in CU_NON_EU.items():
        d[c] = [_rng(frm)]
    return d


SNAPSHOTS = {
    "eu_membership_snapshot": {
        "build": build_eu,
        "source": "Wikipedia: Member state of the European Union (member and withdrawal tables)",
        "page": "Member_state_of_the_European_Union",
        "extra": {
            "semantics": "from = first day of membership; to = last day of membership, inclusive",
            "founders_date_note": "Table says 'Founder' without a date. 1958-01-01 = EEC in force. ECSC began 1952-07-23; Treaty of Rome signed 1957-03-25. [Likely]",
            "precision": {"1958-01-01": "likely"},
        },
    },
    "eea_membership_snapshot": {
        "build": build_eea,
        "source": "Wikipedia: European Economic Area (state table, 'Entered into force' column)",
        "page": "European_Economic_Area",
        "extra": {
            "semantics": "from = formal entry into force of the EEA Agreement for that state; to = last day, inclusive",
            "gb_end_note": "State table says Exit 31 January 2020; the page prose and the 'United Kingdom membership of the EEA' page say the EEA Agreement applied to the UK until 31 December 2020. 2020-12-31 used. [Likely]",
            "provisional_application": EEA_PROVISIONAL,
            "cyprus_note": "Application suspended in Northern Cyprus.",
        },
    },
    "eurozone_membership_snapshot": {
        "build": build_ez,
        "source": "Wikipedia: Eurozone (Euro area), prose on enlargements; cross-checked against the Council of the EU 'Timeline - Joining the euro area' page",
        "page": "Euro_area",
        "extra": {
            "semantics": "from = 1 January of the adoption year; to = null (no state has left)",
            "founding_note": "1999-01-01 is the launch of the euro as book-entry currency. Notes and coins: 2002-01-01.",
            "excluded": "AD, MC, SM, VA (formal monetary agreements) and XK, ME (unilateral) use the euro but are not eurozone members per ECB; not in data.",
        },
    },
    "customs_union_snapshot": {
        "build": build_cu,
        "source": "Wikipedia: European Union Customs Union (tables for non-EU participants and bilateral unions), plus EU accession dates from the EU snapshot",
        "page": "European_Union_Customs_Union",
        "extra": {
            "semantics": "from = first day in the customs union; to = last day, inclusive",
            "eu_members_rule": "from = max(EU accession date, 1968-07-01); founders therefore start 1968-07-01. [Likely]",
            "gb_end_note": "UK left the EU 2020-01-31; the page says the UK is no longer in the customs union and transition ended 2020-12-31. Northern Ireland arrangements (Windsor Framework) are NOT modelled.",
            "partial_scope": {
                "AD": "bilateral union; excludes agricultural produce",
                "TR": "bilateral union; excludes agricultural produce",
                "SM": "bilateral union (Agreement on Cooperation and Customs Union)",
                "MC": "integral part of the EU customs territory via the Franco-Monegasque Customs Convention",
            },
            "imprecise_dates": {"MC": "Wikipedia gives only the year 1968; 1968-07-01 aligned to the EUCU establishment. [Guess]"},
            "excluded": {
                "GI": "Gibraltar: bilateral customs union signed 2026-07-14, provisionally applied from 2026-07-15, entry into force TBD per Wikipedia. Not in data until in force.",
                "Akrotiri and Dhekelia": "In the EU customs territory from 2004-05-01 but has no ISO 3166-1 code.",
                "sub-national": "Büsingen, Heligoland, Livigno, Ceuta, Melilla and similar carve-outs are not modelled.",
            },
        },
    },
}


def validate(name, data, active):
    for c, rs in data.items():
        assert c in active, f"{name}: {c} not an active alpha_2 in iso3166.json"
        assert rs, f"{name}: {c} has an empty range list"
        prev_to = None
        for r in rs:
            assert set(r) == {"from", "to"}, f"{name}:{c} bad keys"
            assert DATE_RE.match(r["from"]), f"{name}:{c} bad from"
            date.fromisoformat(r["from"])
            if r["to"] is not None:
                assert DATE_RE.match(r["to"])
                assert r["to"] >= r["from"], f"{name}:{c} to < from"
            if prev_to is not None:
                assert r["from"] > prev_to, f"{name}:{c} overlapping ranges"
            prev_to = r["to"]


def render(stem, spec, active):
    data = spec["build"]()
    validate(stem, data, active)
    data = {k: data[k] for k in sorted(data)}
    snap = {
        "meta": {
            "source": spec["source"],
            "source_permalink": WP + spec["page"],
            "permalink_note": PERMALINK_NOTE,
            "accessed_at": ACCESSED_AT,
            "review_by": REVIEW_BY,
            "refresh_cadence": CADENCE,
            "generator": "tools/build_club_snapshots.py",
            "count": len(data),
            **spec["extra"],
        },
        "data": data,
    }
    sibling = {
        "meta": {
            "source": spec["source"],
            "source_permalink": WP + spec["page"],
            "vendored_at": ACCESSED_AT,
            "review_by": REVIEW_BY,
            "refresh_cadence": CADENCE,
        }
    }
    return (json.dumps(snap, indent=2, ensure_ascii=False) + "\n",
            json.dumps(sibling, indent=2, ensure_ascii=False) + "\n")


def load_active():
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    return {c["alpha_2"] for c in tree["countries"]["active"]}


def main(argv):
    check = "--check" in argv
    active = load_active()
    drift = False
    for stem, spec in SNAPSHOTS.items():
        body, sib = render(stem, spec, active)
        for path, text in ((TOOLS / f"{stem}.json", body),
                           (TOOLS / f"{stem}.meta.json", sib)):
            if check:
                if not path.exists() or path.read_text(encoding="utf-8") != text:
                    print(f"drift: {path.relative_to(ROOT)}")
                    drift = True
            else:
                path.write_text(text, encoding="utf-8")
                print(f"wrote {path.relative_to(ROOT)}")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
