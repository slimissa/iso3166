# Withdrawn list against ISO 3166-3

Status as of v1.12.14 (recheck 2027-01-25). This page compares the
registry's 25 withdrawn entries with ISO 3166-3, the ISO list of former
country names. It changes no data. The withdrawn list stays as it is until a
decision record settles the modelling questions below.

## Source, and what it is worth

ISO 3166-3 itself was not read for this page. Its Online Browsing Platform
pages render only in a browser, and no archived copy was reachable from the
environment that wrote this page. The list below is a **lead**: the table of
the Wikipedia article "ISO 3166-3", read on 2026-11-25 (no revision id was
recorded; the maintainer is to save a permalink). Every row is
`lead_only, to confirm` against ISO 3166-3 before anything in it is used.
The pages to save are listed in the work's SPEC under "Pages to save as PDF".

## Counts

| | Entries |
|--|--:|
| In the lead's ISO 3166-3 table | 31 |
| In the registry's withdrawn list | 25 |
| In the lead and in the registry | 25 |
| In the lead, not in the registry | 6: BQAQ, BYAA, CSHH, FXFR, GEHH, PUUM |
| In the registry, not in the lead | 0 |

## Per entry

"In registry" gives the registry's `withdrawal_date`. "Differences" compares
the registry row with the lead row: alpha-3, numeric (the registry writes
`000` where it holds no numeric), the year the period ends, and the name.

| ISO 3166-3 | Alpha-2 | Name (lead) | Period (lead) | In registry | Differences (lead_only, to confirm) |
|------------|---------|-------------|---------------|-------------|-------------------------------------|
| BQAQ | BQ | British Antarctic Territory | 1974–1979 | no | — |
| BUMM | BU | Burma | 1974–1989 | yes (1989-12-05) | — |
| BYAA | BY | Byelorussian SSR | 1974–1992 | no | — |
| CTKI | CT | Canton and Enderbury Islands | 1974–1984 | yes (1984-01-01) | numeric 000 vs 128 |
| CSHH | CS | Czechoslovakia | 1974–1993 | no | — |
| DYBJ | DY | Dahomey | 1974–1977 | yes (1977-02-01) | numeric 000 vs 204 |
| NQAQ | NQ | Dronning Maud Land | 1974–1983 | yes (1983-01-01) | numeric 000 vs 216 |
| TPTL | TP | East Timor | 1974–2002 | yes (2002-05-20) | — |
| FXFR | FX | France, Metropolitan | 1993–1997 | no | — |
| AIDJ | AI | French Afars and Issas | 1974–1977 | yes (1977-06-27) | numeric 000 vs 262 |
| FQHH | FQ | French Southern and Antarctic Territories | 1974–1979 | yes (1979-01-01) | — |
| DDDE | DD | German Democratic Republic | 1974–1990 | yes (1990-10-03) | name "East Germany" |
| GEHH | GE | Gilbert Islands | 1974–1979 | no | — |
| JTUM | JT | Johnston Island | 1974–1986 | yes (1986-01-01) | numeric 000 vs 396 |
| MIUM | MI | Midway Islands | 1974–1986 | yes (1986-01-01) | numeric 000 vs 488 |
| ANHH | AN | Netherlands Antilles | 1974–2010 | yes (2010-12-01) | — |
| NTHH | NT | Neutral Zone | 1974–1993 | yes (1993-07-01) | numeric 000 vs 536 |
| NHVU | NH | New Hebrides | 1974–1980 | yes (1980-07-30) | — |
| PCHH | PC | Pacific Islands (Trust Territory) | 1974–1986 | yes (1986-11-03) | numeric 000 vs 582 |
| PZPA | PZ | Panama Canal Zone | 1974–1980 | yes (1980-01-01) | — |
| CSXX | CS | Serbia and Montenegro | 2003–2006 | yes (2006-09-26) | — |
| SKIN | SK | Sikkim | 1974–1975 | yes (1975-05-16) | — |
| RHZW | RH | Southern Rhodesia | 1974–1980 | yes (1980-04-18) | — |
| PUUM | PU | United States Miscellaneous Pacific Islands | 1974–1986 | no | — |
| HVBF | HV | Upper Volta | 1974–1984 | yes (1984-08-04) | — |
| SUHH | SU | USSR | 1974–1992 | yes (1992-08-30) | — |
| VDVN | VD | Viet-Nam, Democratic Republic of | 1974–1977 | yes (1976-07-02) | withdrawal year 1976 vs 1977; name "North Vietnam" |
| WKUM | WK | Wake Island | 1974–1986 | yes (1986-01-01) | numeric 000 vs 872 |
| YDYE | YD | Yemen, Democratic | 1974–1990 | yes (1990-05-22) | name "South Yemen" |
| YUCS | YU | Yugoslavia | 1974–2003 | yes (2003-07-23) | numeric 890 vs 891 |
| ZRCD | ZR | Zaire | 1974–1997 | yes (1997-05-17) | — |

Two of the differences are more than a placeholder or a name form:

- **YU numeric.** The registry has `890`, the lead `891`. The lead gives
  `891` to Serbia and Montenegro (CSXX) too, which suggests the code moved
  with the name in 2003; the registry's `890` may be the older value. To
  confirm against ISO 3166-3.
- **VD withdrawal.** The registry has 1976-07-02 (the reunification of
  Viet Nam); the lead's period ends in 1977. The ISO date and the historical
  date may differ. To confirm.

## The six entries the registry lacks

| ISO 3166-3 | Former name | Alpha-2 | Collides with | Note |
|------------|-------------|---------|---------------|------|
| BQAQ | British Antarctic Territory | BQ | active `BQ` (Bonaire, Sint Eustatius and Saba, since 2010-12-15) | code reused |
| BYAA | Byelorussian SSR | BY | active `BY` (Belarus) | name change; same code kept |
| CSHH | Czechoslovakia | CS | withdrawn `CS` (Serbia and Montenegro, CSXX) | two withdrawn entries, one alpha-2 |
| FXFR | France, Metropolitan | FX | nothing | its period starts in 1993, not 1974 |
| GEHH | Gilbert Islands | GE | active `GE` (Georgia) | code reused |
| PUUM | United States Miscellaneous Pacific Islands | PU | nothing | merged into UM with JT, MI, WK |

## What modelling the missing entries needs

**Reused alpha-2 codes (BQ, BY, GE).** An active and a withdrawn entry may
already share an alpha-2: `AI` (Anguilla / French Afars and Issas) and `SK`
(Slovakia / Sikkim) do. The validator checks uniqueness within each section,
not across them (`tools/validate.py`, `layer_business`). So BQAQ, BYAA and
GEHH fit the current schema. What does not fit is the lookup: every read by
alpha-2 prefers the active entry (`docs/QUERIES-DECISIONS.md`, "Why alpha-2
collisions resolve to the active entry"), so `is_active_on("GE",
"1977-01-01")` answers for Georgia, not for the Gilbert Islands. BYAA is a
different case from AI and SK: the code did not move to another country, the
name changed. Whether a name change belongs in the withdrawn list at all is a
decision, not a data fix.

**Two withdrawn rows with one alpha-2 (CS).** CSHH (Czechoslovakia,
1974–1993) and CSXX (Serbia and Montenegro, 2003–2006) both carry `CS`. The
registry holds only the second. Adding the first breaks three things today:

1. `tools/validate.py` rejects a duplicate `alpha_2` within `withdrawn`.
2. `is_active_on` takes the first withdrawn row with the code
   (`wrappers/python/iso3166/derived.py`), so one of the two would be
   unreachable, and the answer would depend on file order.
3. `YU` has `replaced_by: ["CS"]`, which would no longer name one entry.

A key other than alpha-2 is needed for withdrawn rows: the ISO 3166-3
four-letter code is the natural one. That is a schema change, which this
page does not make.

**The effect on `is_active_on`.** A withdrawn entry has no sourced start
date, so `is_active_on` answers True from 1974-01-01 to its
`withdrawal_date`. That is wrong for FXFR (in force from 1993) and for the
current `CS` row, which answers True for 1980 although Serbia and Montenegro
received `CS` in 2003. Today, `is_active_on("CS", "1980-01-01")` is True for
the wrong reason: in 1980 `CS` meant Czechoslovakia. Any withdrawn row added
needs a start date with an ISO source, or the query keeps answering for the
wrong period.

**The AI/SK precedent.** It covers a code reused by another country, with
the active entry winning every read. It does not cover a name change under
the same code (BYAA), a code that two withdrawn entries held (CS), or a
withdrawn entry that did not start in 1974 (FXFR).

## What would let the list change

1. The maintainer saves the ISO 3166-3 OBP pages as PDF (Firefox), and each
   row above is confirmed or corrected from them.
2. A decision record in `docs/decisions/` answers: is a name change a
   withdrawn entry; what keys a withdrawn row (alpha-2 or the four-letter
   code); and what start date a withdrawn row carries.
3. Only then does `tools/enrich_withdrawn.py` change, and the list with it.
