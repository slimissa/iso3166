# Reconnaissance: `introduced`, code by code

This page says, for every `introduced` value, what stands behind it, and what
would replace an inference or a lead with an ISO document. The per-code record
is the ledger [`tools/introduced_evidence.json`](../tools/introduced_evidence.json);
the rules are in [`decisions/introduced-evidence.md`](./decisions/introduced-evidence.md).
This page groups the ledger's rows and adds what the ISO documents showed.

Status as of v1.12.14 (recheck 2027-02-25). Sources read: ISO 3166-1
newsletters V-1 to V-12 (1998–2006) and VI-2, VI-10, VI-11, VI-13
(2008–2012), ISO 3166-3 newsletters I-1 to I-5, all as Internet Archive
captures of iso.org fetched with `id_` (original bytes); 249 ISO Online
Browsing Platform (OBP) code pages (2026-10-20/21) and 31 ISO 3166-3 and
reserved-code pages (2026-11-25), saved by the maintainer; the Wikipedia
permalink `oldid=1258392980` (`tools/wikipedia_dates.json`) and the 1974 list
in `tools/build_introduced_snapshot.py`. No ISO source online covers 1974 to
1997: the ISO 3166/MA index says its online newsletters start in 1997. A
request to ISO for series I–IV is the next step; the recheck date allows
three months for a reply.

## Where each value stands

| Group | Codes | Value | Ledger class / verdict |
|-------|------:|-------|------------------------|
| Dated by an ISO 3166-1 newsletter that assigns the code | 8 | the issue date | `iso_primary` / `adopted` |
| Dated by an OBP assignment entry | 6 | the entry's date | `iso_primary` / `adopted` |
| Dated by the 1974 list | 161 | `1974-09-15` | `inference` / `unconfirmed` |
| Quarantined, candidate from the 1974 list | 23 | `null` | `inference` / `unconfirmed` |
| Quarantined, candidate from Wikipedia | 5 | `null` | `lead_only` / `unconfirmed` |
| Source silent | 46 | `null` | `lead_only`, no candidate |
| Not officially assigned (EU, UK, XK) | 3 | `null` | `lead_only`, no candidate |
| Withdrawn, dated by a newsletter (CS) | 1 | `2003-07-23` | `iso_primary` / `adopted` |
| Withdrawn only, undated | 24 | `null` | `lead_only`, no candidate (FX and PU joined in v1.14.0) |
| | **277** | | |

Two values changed in this work: withdrawn `CS`, from `null` to 2003-07-23,
and `NU`, from `2002-05-20` to `null` (quarantined, below).
The other 14 ISO dates confirm the values the tree already held.

## The newsletters (series V and VI)

Each newsletter has an issue date and a change table. Only a newsletter whose
alpha-2 cell has the code as its new entry assigns it; a change of name,
alpha-3 or numeric code, a spelling fix or a subdivision change does not. The
tree already dates every code a newsletter assigns by the newsletter's issue
date (PS, TL, AX, GG, IM, JE, ME, RS and SS all equal their newsletter's
date), and VI-2 says "The changes take effect on the date of publication of
this Newsletter". No newsletter read states another effective date.

| Newsletter | Assigns | Code | Date |
|------------|---------|------|------|
| V-2 | Occupied Palestinian Territory | PS | 1999-10-01 |
| V-5 | East Timor's new code (TP → TL) | TL | 2002-05-20 |
| V-8 | Serbia and Montenegro (YU → CS) | CS (withdrawn) | 2003-07-23 |
| V-9 | Åland Islands | AX | 2004-02-13 |
| V-11 | Jersey, Guernsey, Isle of Man | JE, GG, IM | 2006-03-29 |
| V-12 | Serbia, Montenegro | RS, ME | 2006-09-26 |
| VI-10 | South Sudan ("Assign code elements") | SS | 2011-08-09 |

The French versions of V-1 to V-9 agree with the English ones on number, date
and alpha-2. No French version of V-10 to V-12 was captured. BL, MF (VI-1),
BQ, CW and SX (VI-8) are dated from the OBP; their newsletters are not among
the captures.

## What the OBP harvest proves, and what it cannot

Every harvested page has a "Change history of country code" table whose
oldest entry is 2007-09-21 or later. It dates only codes assigned since 2007.
Six entries assign a code: BL and MF ("Add new entry", 2007-09-21), BQ, CW and
SX ("Add new entry", 2010-12-15) and SS ("Assign code elements",
2011-08-09). "Addition of code to align ISO 3166-1 and ISO 3166-2"
(2011-12-13) is housekeeping and dates nothing.

## The 161 dates of the 1974 list

They are `1974-09-15` because a maintainer-supplied list says the code was in
the first edition. That is an inference until the ISO 3166:1974 text is read.
It is not confirmed by elimination: a code in no newsletter read may have
entered through the editions of 1981, 1988, 1993 or 1997. The ISO 3166-3
pages corroborate one thing without dating it: TP (East Timor) was in ISO
3166 "From 1974", under the name Portuguese Timor (Part 3 Newsletter I-1).

## NU: a date the newsletters contradict

NU's value, 2002-05-20, comes from the Wikipedia table. Newsletter V-4 of that
date lists NIUE among name changes: the present entry "NIUE" is unchanged and
the official name "Republic of Niue" is added, and the newsletter says "None
of the code elements for the country names is changed". So NU was already in
ISO 3166-1 on 2002-05-20, and the date is a name change. No ISO document read
gives NU's assignment date, so the value stays, and the ledger row records the
contradiction. The maintainer quarantined NU for the same reason as SH:
the value is now `null` [confirmed], and the refused candidate stays in the
ledger row.

## The 28 quarantined codes

The builder refuses these candidates (`meta.null_reasons` in
`tools/introduced_snapshot.json`). None is dated by an ISO document. The ISO
3166-3 pages now give evidence for most, and some give a predecessor bound:
the ledger row's `bound.not_before`, an inference that narrows the date and
never sets it.

**Former USSR (12) [likely].**

| Code | Candidate (refused) | ISO evidence | Bound |
|------|---------------------|--------------|-------|
| AM | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into AM and 12 others | not before 1992 |
| AZ | `1974-09-15` (1974 list); Wikipedia `2002-05-20` = Newsletter V-4, a name change | SUHH: removed from ISO 3166-1 in 1992, divided into AZ and 12 others | not before 1992 |
| EE | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into EE and 12 others | not before 1992 |
| GE | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into GE and 12 others | not before 1992 |
| KG | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into KG and 12 others | not before 1992 |
| KZ | `1974-09-15` (1974 list); Wikipedia `2002-05-20` = Newsletter V-4, a name change | SUHH: removed from ISO 3166-1 in 1992, divided into KZ and 12 others | not before 1992 |
| LT | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into LT and 12 others | not before 1992 |
| LV | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into LV and 12 others | not before 1992 |
| RU | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into RU and 12 others | not before 1992 |
| TJ | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into TJ and 12 others | not before 1992 |
| TM | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into TM and 12 others | not before 1992 |
| UZ | `1974-09-15` (1974 list) | SUHH: removed from ISO 3166-1 in 1992, divided into UZ and 12 others | not before 1992 |

**Belarus and Ukraine (2) [likely], and a contradiction.** ISO's SUHH page
says BY and UA "were separately coded in ISO 3166 already before the USSR was
split", and ISO 3166-3 BYAA records Byelorussian SSR under BY. That
contradicts the quarantine reason ("code cannot be in 1974 edition"). It
gives no date, so both stay null.

**The Wikipedia row is a change newsletter (5): BA, ER, MD, SH [likely], NU [confirmed].**

| Code | Candidate (refused) | ISO evidence |
|------|---------------------|--------------|
| BA | `2002-05-20` (Wikipedia) | Newsletter V-4 of that date: official name dropped; "None of the code elements ... is changed" |
| ER | `2012-02-15` (Wikipedia) | no newsletter of that date captured; VI-13 (2012-08-02) changes ER's full name |
| MD | `2008-03-31` (Wikipedia) | Newsletter VI-2 (2008-04-08): change of short name; the OBP's oldest MD entry is the same |
| NU | `2002-05-20` (Wikipedia) | Newsletter V-4 of that date: NIUE among name changes; "None of the code elements ... is changed" |
| SH | `2010-02-22` (Wikipedia) | the OBP's oldest SH entry, 2010-02-22: "Change of name; Addition of islands" |

**Successors of Czechoslovakia or Yugoslavia (3) [likely].**

| Code | Candidate (refused) | ISO evidence |
|------|---------------------|--------------|
| CZ | `1974-09-15` (1974 list) | CSHH: "Czechoslovakia was divided into Czechia (CZ, CZE, 203), and Slovakia (SK, SVK, 703)", no date (page saved after its `SHA256SUMS`) |
| SK | `1974-09-15` (1974 list) | the same; `SK` is also withdrawn Sikkim (SKIN) |
| SI | `1974-09-15` (1974 list) | YUCS: "Former Yugoslavia was divided into ... Slovenia (SI)", no date |

**Successors of withdrawn codes (6) [confirmed by the tree].**

| Code | Candidate (refused) | ISO evidence | Bound |
|------|---------------------|--------------|-------|
| BJ | `1974-09-15` | DYBJ: "Name changed to Benin (BJ, BEN, 204)" | none (no date on the page) |
| DJ | `1974-09-15` | AIDJ: "Name changed ... to Djibouti (DJ, DJI, 262)" | none |
| KI | `1974-09-15` | CTKI: "Now part of Kiribati"; GEHH: divided into Kiribati and Tuvalu | none |
| MM | `1974-09-15` | BUMM: "Reserved from 1989-12"; name changed to Myanmar | not before 1989-12 |
| VU | `1974-09-15` | NHVU: "Name changed from New Hebrides to Vanuatu" | none |
| ZW | `1974-09-15` | RHZW: "Name changed from Southern Rhodesia ... to Zimbabwe" | none |

## The 46 source-silent codes

No source in the tree gives a date for: `AI`, `AQ`, `AS`, `AW`, `BF`, `BV`, `CC`, `CD`, `CK`, `CX`, `EH`, `FK`, `FM`, `FO`, `GF`, `GI`, `GP`, `GS`, `GU`, `HM`, `HR`, `IO`, `KN`, `KY`, `MH`, `MK`, `MP`, `MQ`, `MS`, `NC`, `NF`, `PF`, `PM`, `PN`, `PR`, `PW`, `RE`, `SJ`, `TC`, `TF`, `TK`, `UM`, `VG`, `VI`, `WF`, `YT`.
None has an assignment entry on its OBP page or in a newsletter read. CD has a
bound, not before 1997-07 (ZRCD: ZR "Reserved from 1997-07", name changed to
the Democratic Republic of the Congo). HR and MK are among the successors of
Yugoslavia on the YUCS page, without a date.

## What would replace the rest

1. **ISO 3166 newsletters of series I to IV (1974–1996), or ISO's answer per
   code.** They are not online: the ISO 3166/MA index starts its newsletters in
   1997. A request to ISO Customer Service asks for them, for the assignment
   date of the 21 `[likely]` quarantined codes, and for the 1974, 1981 and
   1988 editions.
2. **The editions of 1974, 1981, 1988, 1993 and 1997**, held by national
   standards bodies and libraries.
3. **Newsletters VI-1 and VI-8**, which would add a second document for BL,
   MF, BQ, CW and SX.

Until then a labelled value is kept, and a null with a reason is the honest
answer. `is_active_on(code, date)` returns `null` (unknown), not `false`, for
an active code with a null `introduced`.
