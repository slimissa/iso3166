# Introduced evidence: which documents may date a code

Status: **accepted**
Date: 2026-11-25
Supersedes: none
Amends: [`introduced-field.md`](./introduced-field.md) (its "Source (the exception)" section)
Superseded by: none

## Context

`introduced` is the date ISO 3166-1 added a code. Until now every value came
from two inputs that are not ISO documents: a maintainer-supplied list of
1974 codes (`LIST_1974` in `tools/build_introduced_snapshot.py`) and the
Wikipedia "Changes" table (`tools/wikipedia_dates.json`). Neither cites the
page of an ISO document for the code it dates. The registry could not say,
per code, why a value is what it is.

[`introduced-field.md`](./introduced-field.md) also says that the ISO Online
Browsing Platform (OBP) "does not publish assignment dates on per-country
pages". That is true for codes assigned before the OBP kept a history, and
false for later ones: the OBP page of SS has a "Change history of country
code" table whose oldest entry is "2011-08-09 Assign code elements". The
maintainer's harvest of 249 OBP pages (2026-10-20/21) shows six such
assignment entries; the oldest entry on any page is 2007-09-21.

## Decision

A ledger, [`tools/introduced_evidence.json`](../../tools/introduced_evidence.json),
holds one row per key of `tools/introduced_snapshot.json` (active and
withdrawn, 275 rows). Each row says what the registry holds (`current`),
what a source proposes (`candidate`), what kind of source it is (`class`),
which document and where in it (`doc`, `quote_ref`), the verdict, and the
reason. `tools/check_introduced_evidence.py` checks it, in CI and in the
release gate.

### The four classes

| Class | What it is | Can it set a value? |
|-------|-----------|---------------------|
| `iso_primary` | An ISO or ISO 3166/MA document: an ISO 3166 newsletter, an ISO 3166 edition or amendment, the ISO 3166-3 list, or an OBP code page with its change history. An Internet Archive capture of a file that iso.org itself hosted counts as that document, cited by both URLs. | Yes, and it is the only class that can |
| `ma_member` | A body that is a member of the ISO 3166/MA quoting ISO, for example UNECE Recommendation No. 3. | No, not alone. It can corroborate an `iso_primary` row |
| `lead_only` | A pointer to a document: Wikipedia, FreeBSD `share/misc/iso3166`, statoids, iso3166-updates, a library catalogue. A row with no candidate at all is also `lead_only`: no reading exists. | No. It says where to look |
| `inference` | A conclusion, not a reading: the 1974 list, "in no newsletter, so in the 1974 edition", or "a successor state cannot be a 1974 code". | No. It is recorded so nothing hides behind it |

### Why only `iso_primary` can set a value

`introduced` claims a fact about ISO 3166-1: the day ISO added the code.
Only ISO's own documents can witness that day. The others repeat ISO
(`ma_member`), retell it (`lead_only`) or reason about it (`inference`).
Each can be right, and each has been wrong in a way that cannot be seen
from the outside: the Wikipedia table mixes newsletters that added a code
with ones that changed it, and the 1974 list held codes that the tree
itself proves are later successors (BJ, DJ, KI, MM, VU, ZW). A rule that
lets a second-hand source set a date as long as nothing contradicts it
keeps such errors indefinitely. A rule that only the primary document sets a
date makes every value traceable to a page.

An `ma_member` document is closer to ISO than a lead, but it quotes an
edition, and its own date is not the assignment date. It can raise
confidence in an `iso_primary` row; it cannot stand in for one.

### Rules the check enforces

1. One row per snapshot key, sorted; fixed keys; closed vocabularies for
   `class` and `verdict`.
2. `current` equals the snapshot.
3. `adopted` only with `iso_primary`, and only with a `doc` that has a
   title, at least one URL, a locator (page, clause, entry) and the sha256
   of the bytes read. The documents themselves are not committed.
4. Every `adopted` candidate equals the entry's `introduced` in
   `iso3166.json`.
5. A `conflict` row has a candidate that differs from `current`.

### How a value changes

Only through `tools/build_introduced_snapshot.py`, and only for a row that
is `iso_primary` and `adopted`. Every other row keeps its value and states
its true provenance: the 1974 dates are `inference`, reason "maintainer
list; ISO 3166:1974 text not yet obtained".

A primary date that contradicts the current value is a `conflict` row. It is
adopted only if the document is unambiguous about that code. Two primary
documents that disagree are a `conflict` with both cited, and nothing is
adopted.

### OBP change history

Only an entry that assigns the code dates it ("Assign code elements", "Add
new entry"). "Addition of code to align ISO 3166-1 and ISO 3166-2"
(2011-12-13) is housekeeping and never an assignment date. An entry whose
meaning is unclear is treated as not an assignment.

### No reconstruction by elimination

"The code is in no newsletter, so it was in the 1974 edition" is an
inference. The editions of 1981, 1988, 1993 and 1997 consolidated changes
too, so absence from the newsletters does not place a code in 1974. Such a
conclusion is recorded as `inference` and never adopted.

## Consequences

- The Wikipedia exception in [`PROVENANCE.md`](../PROVENANCE.md) narrows to
  the rows still `lead_only` or `inference`, with counts.
- A value that has only a lead or an inference behind it stays, and says so.
  The registry does not null 161 dates because their source is weak; it
  labels them.
- The 1974–2009 evidence must come from ISO 3166 newsletters and editions.
  The OBP change history starts in 2007.

## Alternatives considered

- Null every value without an `iso_primary` row: rejected for now. It would
  turn every labelled value without a primary row into an unknown and change
  `is_active_on` answers, with no new evidence behind the change.
- Accept `ma_member` alone: rejected. A quoting body's date is not the
  assignment date.
- Commit the ISO documents: rejected. They are ISO's copyrighted documents,
  and a sha256 with the URLs makes the reading checkable without a copy.
