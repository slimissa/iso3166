"""The withdrawn list against ISO 3166-3 (v1.14.0).

Every value pinned here was read on the entry's ISO Online Browsing Platform
page, saved by the maintainer on 2026-11-25 (sha256 of each page in
docs/withdrawn-completeness.md, "Page hashes"). The pages are not committed;
this test keeps the registry from drifting away from what they showed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "iso3166.json").read_text(encoding="utf-8"))
WITHDRAWN = {e["alpha_2"]: e for e in REG["countries"]["withdrawn"]}

# alpha_2 -> ISO 3166-3 alpha-4, from each entry's ISO page.
ALPHA_4 = {
    "AI": "AIDJ", "AN": "ANHH", "BU": "BUMM", "CS": "CSXX", "CT": "CTKI",
    "DD": "DDDE", "DY": "DYBJ", "FQ": "FQHH", "HV": "HVBF", "JT": "JTUM",
    "MI": "MIUM", "NH": "NHVU", "NQ": "NQAQ", "NT": "NTHH", "PC": "PCHH",
    "PZ": "PZPA", "RH": "RHZW", "SK": "SKIN", "SU": "SUHH", "TP": "TPTL",
    "VD": "VDVN", "WK": "WKUM", "YD": "YDYE", "YU": "YUCS", "ZR": "ZRCD",
}

# ISO 3166-1 status "Transitionally reserved", and the period each page gives.
TRANSITIONAL = {
    "AN": "2010-12 to 2060-12", "BU": "1989-12 to 2039-12", "CS": "2006-09 to 2056-09",
    "NT": "1993-07 to 2043-07", "TP": "2002-05 to 2052-05", "YU": "2003-07 to 2053-07",
    "ZR": "1997-07 to 2047-07",
}

# ISO 3166-1 status "Exceptionally reserved" among the withdrawn entries.
EXCEPTIONAL = {"SU"}


def test_every_withdrawn_entry_carries_its_iso_3166_3_alpha_4():
    for a2, a4 in ALPHA_4.items():
        assert WITHDRAWN[a2]["alpha_4"] == a4, a2


def test_cs_is_serbia_and_montenegro_not_czechoslovakia():
    # Both ISO 3166-3 entries use CS; the registry holds CSXX. CSHH waits for
    # v2.0.0, and the row's note keeps Czechoslovakia.
    cs = WITHDRAWN["CS"]
    assert cs["alpha_4"] == "CSXX" and cs["name"] == "Serbia and Montenegro"
    assert "Czechoslovakia" in cs["note"]


def test_exceptional_reservations_carry_their_reservation_and_iso_wording():
    for a2, e in WITHDRAWN.items():
        if a2 in EXCEPTIONAL:
            assert e["reservation"] == "exceptionally-reserved", a2
            assert "ISO 3166-1 status: Exceptionally reserved." in e["note"], a2
        elif a2 not in TRANSITIONAL:
            # ISO shows the entry as formerly used.
            assert e["reservation"] is None, a2


def test_transitionally_reserved_entries_carry_the_reservation_and_record_the_period():
    for a2, period in TRANSITIONAL.items():
        e = WITHDRAWN[a2]
        assert e["reservation"] == "transitionally-reserved", a2
        line = (f"ISO 3166-1 status: Transitionally reserved. Reserved from {period}. "
                f"(https://www.iso.org/obp/ui/#iso:code:3166:{a2})")
        assert line in e["note"].splitlines(), a2


def test_status_stays_withdrawn_on_every_withdrawn_entry():
    assert {e["status"] for e in WITHDRAWN.values()} == {"withdrawn"}
