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
    # v1.14.0: the five ISO 3166-3 entries that joined the list.
    "BQ": "BQAQ", "BY": "BYAA", "FX": "FXFR", "GE": "GEHH", "PU": "PUUM",
}

# The five new rows, field by field from their ISO pages: alpha-3, numeric
# ("000" where the page gives none, the registry's convention), short name,
# status, and the successors named in "Remark part 3". No page gives a
# withdrawal date.
NEW_ROWS = {
    "GE": ("GEL", "000", "Gilbert and Ellice Islands", "withdrawn", ["KI", "TV"]),
    "BQ": ("ATB", "000", "British Antarctic Territory", "withdrawn", ["AQ"]),
    "BY": ("BYS", "112", "Byelorussian SSR", "withdrawn", None),
    "PU": ("PUS", "849", "United States Miscellaneous Pacific Islands", "withdrawn", ["UM"]),
    "FX": ("FXX", "249", "France, Metropolitan", "withdrawn", ["FR"]),
}

# ISO 3166-1 status "Transitionally reserved", and the period each page gives.
TRANSITIONAL = {
    "AN": "2010-12 to 2060-12", "BU": "1989-12 to 2039-12", "CS": "2006-09 to 2056-09",
    "NT": "1993-07 to 2043-07", "TP": "2002-05 to 2052-05", "YU": "2003-07 to 2053-07",
    "ZR": "1997-07 to 2047-07",
}

# ISO 3166-1 status "Exceptionally reserved" among the withdrawn entries.
EXCEPTIONAL = {"FX", "SU"}


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


def test_the_withdrawn_list_holds_every_iso_3166_3_entry_but_cshh():
    assert set(WITHDRAWN) == set(ALPHA_4)
    assert len(REG["countries"]["withdrawn"]) == 30 == REG["meta"]["count_withdrawn"]
    assert not any(e["alpha_4"] == "CSHH" for e in REG["countries"]["withdrawn"])


def test_the_five_new_rows_are_as_their_iso_pages_give_them():
    for a2, (a3, num, name, status, repl) in NEW_ROWS.items():
        e = WITHDRAWN[a2]
        assert (e["alpha_3"], e["numeric"], e["name"], e["status"], e["replaced_by"]) == \
            (a3, num, name, status, repl), a2
        assert e["withdrawal_date"] is None and e["introduced"] is None, a2
        assert "ISO 3166-3: " in e["note"], a2
        # ISO gives no "Independent" value; the schema requires a boolean, so
        # the note says where false comes from.
        assert e["independent"] is False, a2
        assert any(line.startswith("independent: not stated by ISO; ")
                   for line in e["note"].splitlines()), a2
    assert "a guess" in WITHDRAWN["BY"]["note"]


def test_by_names_no_successor_because_its_code_did_not_change():
    # ISO: "Name changed to Belarus (BY, BLR, 112). Code element BYS removed".
    # replaced_by may not name the entry's own alpha-2, so it is null and the
    # note carries ISO's remark.
    assert WITHDRAWN["BY"]["replaced_by"] is None
    assert "Name changed to Belarus (BY, BLR, 112)" in WITHDRAWN["BY"]["note"]


def test_ge_bq_and_by_resolve_to_the_active_entry_like_ai_and_sk():
    active = {e["alpha_2"] for e in REG["countries"]["active"]}
    for a2 in ("AI", "BQ", "BY", "GE", "SK"):
        assert a2 in active and a2 in WITHDRAWN, a2


# Corrections (v1.14.0), each stated exactly on the entry's ISO page; the old
# value is kept in the row's note.
CORRECTIONS = {
    ("YU", "numeric"): ("890", "891"),
    ("CT", "numeric"): ("000", "128"),
    ("JT", "numeric"): ("000", "396"),
    ("MI", "numeric"): ("000", "488"),
    ("NQ", "numeric"): ("000", "216"),
    ("NT", "numeric"): ("000", "536"),
    ("PC", "numeric"): ("000", "582"),
    ("WK", "numeric"): ("000", "872"),
    ("DD", "name"): ("East Germany", "German Democratic Republic"),
    ("VD", "name"): ("North Vietnam", "Viet-Nam, Democratic Republic of"),
    ("YD", "name"): ("South Yemen", "Yemen, Democratic"),
    ("AN", "withdrawal_date"): ("2010-12-01", "2010-12-15"),
}


def test_the_corrections_hold_and_the_old_value_is_in_the_note():
    for (a2, field), (old, new) in CORRECTIONS.items():
        e = WITHDRAWN[a2]
        assert e[field] == new, (a2, field)
        assert f"{field} before v1.14.0: {old}" in e["note"].splitlines(), (a2, field)


def test_zr_keeps_its_date_because_iso_gives_only_a_month():
    # ISO: "Reserved from 1997-07". Not an exact date, so no correction.
    assert WITHDRAWN["ZR"]["withdrawal_date"] == "1997-05-17"
