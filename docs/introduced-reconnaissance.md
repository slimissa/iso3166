# Reconnaissance: `introduced`, code by code

This page says, for every `introduced` value, what stands behind it, and what
would replace an inference or a lead with an ISO document. The per-code record
is the ledger [`tools/introduced_evidence.json`](../tools/introduced_evidence.json);
the rules are in [`decisions/introduced-evidence.md`](./decisions/introduced-evidence.md).
This page groups the ledger's rows and adds what the ISO Online Browsing
Platform (OBP) harvest showed.

Status as of v1.12.14 (recheck 2027-01-25). Sources read: the maintainer's
Firefox saves of 249 OBP code pages (2026-10-20/21, every active code except
EU, TW and XK; `SHA256SUMS` verified), ISO 3166-1 Newsletter VI-13
(2012-08-02), the Wikipedia permalink `oldid=1258392980`
(`tools/wikipedia_dates.json`) and the 1974 list in
`tools/build_introduced_snapshot.py`. ISO 3166 newsletters before VI-13, the
editions of 1974 to 1997 and ISO 3166-3 were not read; the recheck date is
when the pages the maintainer is asked to save should be in hand.

## Where each value stands

| Group | Codes | Value | Ledger class / verdict |
|-------|------:|-------|------------------------|
| Dated by an OBP assignment entry | 6 | the entry's date | `iso_primary` / `adopted` |
| Dated by the 1974 list | 161 | `1974-09-15` | `inference` / `unconfirmed` |
| Dated by the Wikipedia table | 9 | the table's date | `lead_only` / `unconfirmed` |
| Quarantined, candidate from the 1974 list | 23 | `null` | `inference` / `unconfirmed` |
| Quarantined, candidate from Wikipedia | 4 | `null` | `lead_only` / `unconfirmed` |
| Source silent | 46 | `null` | `lead_only`, no candidate |
| Not officially assigned (EU, UK, XK) | 3 | `null` | `lead_only`, no candidate |
| Withdrawn only | 23 | `null` | `lead_only`, no candidate |
| | **275** | | |

No value changed in this work. The six OBP dates confirm the values the
Wikipedia table had given; they are now held because ISO says so.

## What the OBP harvest proves, and what it cannot

Every harvested page has a "Change history of country code" table. Its oldest
entry on any page is 2007-09-21; the oldest entries cluster in 2010 and 2014.
The history starts when the OBP began recording, not when the code was
assigned. So it dates only codes assigned since 2007, and says nothing for a
code whose oldest entry is a correction.

Only an entry that assigns the code dates it. Six do:

| Code | Date | Entry | Harvest file |
|------|------|-------|--------------|
| BL | `2007-09-21` | "Add new entry" | `BL.html` |
| MF | `2007-09-21` | "Add new entry" | `MF.html` |
| BQ | `2010-12-15` | "Add new entry" | `BQ.html` |
| CW | `2010-12-15` | "Add new entry" | `CW.html` |
| SX | `2010-12-15` | "Add new entry" | `SX.html` |
| SS | `2011-08-09` | "Assign code elements" | `SS.html` |

"Addition of code to align ISO 3166-1 and ISO 3166-2" (2011-12-13, on AW,
BQ, CW, SX and, with "and its administrative subdivisions", SS) is
housekeeping, not an assignment. It dates nothing.

## The 161 dates of the 1974 list

They are `1974-09-15` because a maintainer-supplied list says the code was in
the first edition. That is an inference until the ISO 3166:1974 text is read.
It is not confirmed by elimination either: a code that appears in no
newsletter may have entered through the editions of 1981, 1988, 1993 or 1997,
which consolidated changes. What confirms a row: the 1974 edition, or a
later edition or newsletter that states when the code was added.

## The 9 Wikipedia dates

Each is a date from the Changes table; the OBP page's oldest entry is later
and is not an assignment, so ISO has not confirmed or contradicted any of
them here.

| Code | Wikipedia date | Oldest OBP entry |
|------|----------------|------------------|
| AX | `2004-02-13` | 2011-06-12, "Correct administrative languages" |
| GG | `2006-03-29` | 2008-09-09, "Addition of remark and administrative language French (fr, fra); Addition of the islands mentioned in the Remarks column (Column 7)" |
| IM | `2006-03-29` | 2018-11-26, "Modification of remark part 2" |
| JE | `2006-03-29` | 2013-02-06, "Add local short names" |
| ME | `2006-09-26` | 2008-04-08, "Change of full name" |
| NU | `2002-05-20` | 2011-06-12, "Correct the long name which was incorrect" |
| PS | `1999-10-01` | 2008-04-08, "Correction of local name" |
| RS | `2006-09-26` | 2010-02-19, "Addition of the country code prefix as the first code element, administrative update" |
| TL | `2002-05-20` | 2011-12-13, "Update of the language adjustment and source list update." |

What confirms a row: the ISO 3166-1 newsletter of that date (series V), read
from iso.org or an Internet Archive capture of it.

## The 27 quarantined codes

The builder refuses these candidates, with the reason in
`tools/introduced_snapshot.json`, `meta.null_reasons`. None of the 27 has an
assignment entry on its OBP page.

**Group A, post-Soviet states (14) [likely].** The tree holds `SU` withdrawn
on 1992-08-30 with no `replaced_by`, so it has no edge to these codes; the
inference that they are not 1974 codes rests on history.

| Code | Candidate (refused) | Tree evidence | Oldest OBP entry |
|------|---------------------|---------------|------------------|
| AM | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2018-11-26, "Correction of the romanization system label" |
| AZ | `1974-09-15` (1974 list); Wikipedia `2002-05-20` | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2011-12-13, "Alphabetical re-ordering, name change of administrative places, first level prefix addition and source list update." |
| BY | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2010-06-30, "Update of the administrative structure and of the list source" |
| EE | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2014-11-03, "Update List Source" |
| GE | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2018-11-26, "Correction of the romanization system label" |
| KG | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2014-10-31, "Add 1 city KG-GO; update List Source" |
| KZ | `1974-09-15` (1974 list); Wikipedia `2002-05-20` | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2016-11-15, "Addition of city KZ-BAY; update List Source" |
| LT | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2014-10-31, "Add of 7 city municipality, 44 district municipality and 9 municipality" |
| LV | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2011-12-13, "Administrative re-organization and source list update." |
| RU | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2010-06-30, "Update of the administrative structure and of the list source" |
| TJ | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2014-11-03, "Add 1 capital territory TJ-DU" |
| TM | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2010-06-30, "Update of the administrative structure and update of the list source" |
| UA | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2014-11-03, "Update subdivision name of UA-43; update List Source" |
| UZ | `1974-09-15` (1974 list) | `SU` withdrawn 1992-08-30; no `replaced_by` edge to the code | 2020-11-24, "Addition of an asterisk to region UZ-XO; Correction of the Code Source" |

**Group B, the Wikipedia row is a change newsletter (4) [likely].**

| Code | Candidate (refused) | Tree evidence | Oldest OBP entry |
|------|---------------------|---------------|------------------|
| BA | `2002-05-20` (Wikipedia) | none | 2010-06-30, "Addition of the country code prefix as the first code element, addition of names in administrative languages, update of the administrative structure and of the list source" |
| ER | `2012-02-15` (Wikipedia) | none | 2011-12-13, "Country name romanization adjustment, language adjustment, alphabetical re-ordering and source list update." |
| MD | `2008-03-31` (Wikipedia) | none | 2008-04-08, "Change of short name" |
| SH | `2010-02-22` (Wikipedia) | none | 2010-02-22, "Change of name; Addition of islands given in Clauses 9 and 10" |

SH's oldest OBP entry, 2010-02-22, is "Change of name": the same date as its
Wikipedia row, and not an assignment. That supports the quarantine reason
from an ISO document. MD's Wikipedia date (2008-03-31) is close to its oldest
OBP entry (2008-04-08, "Change of short name"), again a change.

**Group C, successors of Czechoslovakia or Yugoslavia (3) [likely].**

| Code | Candidate (refused) | Tree evidence | Oldest OBP entry |
|------|---------------------|---------------|------------------|
| CZ | `1974-09-15` (1974 list) | note on withdrawn `CS`: replaced by CZ and SK | 2010-02-19, "Addition of the country code prefix as the first code element, alphabetical re-ordering" |
| SI | `1974-09-15` (1974 list) | none direct; `YU` is replaced by `CS` | 2010-06-30, "Update of the administrative structure and languages and update of the list source" |
| SK | `1974-09-15` (1974 list) | note on withdrawn `CS`; `SK` is also withdrawn Sikkim | no history rows |

**Successors of withdrawn codes (6) [confirmed by the tree].**

| Code | Candidate (refused) | Tree evidence | Oldest OBP entry |
|------|---------------------|---------------|------------------|
| BJ | `1974-09-15` (1974 list) | successor of DY, withdrawn 1977-02-01 (tree) | 2015-11-27, "Change of spelling of BJ-AK, BJ-KO; update List Source" |
| DJ | `1974-09-15` (1974 list) | successor of AI, withdrawn 1977-06-27 (tree) | 2011-12-13, "Language adjustment and source list update." |
| KI | `1974-09-15` (1974 list) | successor of CT, withdrawn 1984-01-01 (tree) | 2009-03-03, "Addition of administrative language Gilbertese (-, gil)" |
| MM | `1974-09-15` (1974 list) | successor of BU, withdrawn 1989-12-05 (tree) | 2011-06-12, "Official name change of long name" |
| VU | `1974-09-15` (1974 list) | successor of NH, withdrawn 1980-07-30 (tree) | no history rows |
| ZW | `1974-09-15` (1974 list) | successor of RH, withdrawn 1980-04-18 (tree) | 2015-11-27, "Update List Source" |

What reopens any of the 27: an ISO document that states the code's
assignment date (a newsletter or an edition). The OBP harvest does not.

## The 46 source-silent codes

No source in the tree gives a date: `AI`, `AQ`, `AS`, `AW`, `BF`, `BV`, `CC`, `CD`, `CK`, `CX`, `EH`, `FK`, `FM`, `FO`, `GF`, `GI`, `GP`, `GS`, `GU`, `HM`, `HR`, `IO`, `KN`, `KY`, `MH`, `MK`, `MP`, `MQ`, `MS`, `NC`, `NF`, `PF`, `PM`, `PN`, `PR`, `PW`, `RE`, `SJ`, `TC`, `TF`, `TK`, `UM`, `VG`, `VI`, `WF`, `YT`. Their OBP pages have no
assignment entry. [`introduced-field.md`](./decisions/introduced-field.md)
notes that the 1974 list omits about 30 territories that were in the 1974
edition (KY, GU, PR, VG among them). That note is a lead with no document
behind it; the 1974 edition is what would show it.

## What would replace the rest

1. **ISO 3166-1 newsletters, series I to V.** They date every change from
   1974 to 2007. The index page was on iso.org (`updates_on_iso_3166.htm`)
   and is on the Internet Archive; neither was reachable from the
   environment that wrote this page. The pages to save are listed in the
   work's SPEC under "Pages to save as PDF (Firefox)".
2. **The editions of 1974, 1981, 1988, 1993 and 1997.** They are sold or held
   by national standards bodies and libraries; none was obtained.
3. **ISO 3166-3.** It dates the withdrawn entries' ends and, by successor, some
   starts ([`withdrawn-completeness.md`](./withdrawn-completeness.md)).

Until then a labelled value is kept, and a null with a reason is the honest
answer. `is_active_on(code, date)` returns `null` (unknown), not `false`, for
a code with a null `introduced`.
