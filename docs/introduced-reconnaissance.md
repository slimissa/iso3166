# Reconnaissance: the 21 `[likely]` quarantined `introduced` codes

This page turns 21 inferences into 21 documented gaps. Each code below has
`introduced: null` in the registry. The null is deliberate, and so is the
reason it carries. This page records, per code, what the tree and the source
say, how strong that evidence is, and what would let the date be filled in.

Scope: the 21 codes tagged `[likely]` in `meta.null_reasons` of
[`tools/introduced_snapshot.json`](../tools/introduced_snapshot.json). The six
codes tagged `[confirmed]` (BJ, DJ, KI, MM, VU, ZW) are not covered here: the
tree itself proves they are successors of withdrawn codes. The quarantine list
lives in `QUARANTINE` in
[`tools/build_introduced_snapshot.py`](../tools/build_introduced_snapshot.py);
the decision is in
[`decisions/introduced-field.md`](./decisions/introduced-field.md).

Status as of v1.12.10. Wikipedia source: ISO 3166-1, permalink
`oldid=1258392980`, accessed 2026-10-28 (`tools/wikipedia_dates.json`). The
snapshot's `review_by` is 2027-10-28.

## How to read an entry

- **current value:** what the registry holds today. Always `null`.
- **source:** the Wikipedia table row in `tools/wikipedia_dates.json`, if any,
  and whether the maintainer-supplied 1974 list (`LIST_1974`) names the code.
  Both are third-party inputs; the exception that allows them is recorded in
  [`PROVENANCE.md`](./PROVENANCE.md).
- **tree evidence:** what `iso3166.json` itself holds that bears on the date.
  "None" means the tree is silent, not that the inference is wrong.
- **reopening trigger:** the event that lets the quarantine be removed.

Evidence strength is the same word the snapshot uses: `[likely]` means the
inference rests on the history of the state, which is not in the tree. It does
not mean the tree contradicts the candidate date.

## Summary

| Group | Codes | Quarantine reason (paraphrased) | Count |
|-------|-------|-----------------------------------|------:|
| A | AM, AZ, BY, EE, GE, KG, KZ, LT, LV, RU, TJ, TM, UA, UZ | post-Soviet state; SU withdrawn 1992-08-30 (tree) | 14 |
| B | BA, ER, MD, SH | the table row is a change newsletter | 4 |
| C | CZ, SI, SK | successor state of Czechoslovakia/Yugoslavia | 3 |
| | | **Total** | **21** |

Seventeen of the 21 are in the maintainer-supplied 1974 list (all of group A
and C), which would give `1974-09-15`. That value is rejected for each: the
quarantine overrides the list. BA, ER, MD and SH are not in that list; their
only candidate is the newsletter date of their Wikipedia row.

The tree facts used below come from four withdrawn entries: `SU` (USSR,
withdrawn 1992-08-30, no `replaced_by`), the note on `CS` (Czechoslovakia,
withdrawn 1993-01-01, replaced by CZ and SK), `YU` (withdrawn 2003-07-23,
replaced by `CS`) and `SK` (Sikkim, withdrawn 1975-05-16, replaced by IN).
[`WITHDRAWN.md`](./WITHDRAWN.md) lists them.

## Group A: post-Soviet states (14)

For every code in this group the tree evidence is the same and weak: `SU` is
withdrawn on 1992-08-30, but `SU` has no `replaced_by`, so the tree holds no
edge from `SU` to any code below. The inference that the code cannot be a 1974
addition comes from the history of the state, which the tree does not record.

### AM: Armenia

- current value: `null`.
- source: no row in `wikipedia_dates.json`; in the 1974 list (`1974-09-15`, rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to AM.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for AM.

### AZ: Azerbaijan

- current value: `null`.
- source: row `2002-05-20` (a change newsletter, not a verified addition); in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to AZ. Two candidate dates conflict.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for AZ.

### BY: Belarus

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to BY.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for BY.

### EE: Estonia

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to EE.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for EE.

### GE: Georgia

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to GE.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for GE.

### KG: Kyrgyzstan

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to KG.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for KG.

### KZ: Kazakhstan

- current value: `null`.
- source: row `2002-05-20` (a change newsletter); in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to KZ. Two candidate dates conflict.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for KZ.

### LT: Lithuania

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to LT.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for LT.

### LV: Latvia

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to LV.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for LV.

### RU: Russian Federation

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to RU.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for RU.

### TJ: Tajikistan

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to TJ.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for TJ.

### TM: Turkmenistan

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to TM.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for TM.

### UA: Ukraine

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to UA.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for UA.

### UZ: Uzbekistan

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: `SU` withdrawn 1992-08-30; no edge to UZ.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for UZ.

## Group B: the table row is a change newsletter (4)

For these four the Wikipedia table has a row, but the builder's reason says the
row's date is a newsletter that changed the entry, not the one that added the
code. The tree holds nothing about when any of the four codes was added. The
approximate years in the builder's reasons (Bosnia "~1992", Moldova "~1992",
Eritrea "~1993") are uncited comments, not values, and are not used anywhere.

### BA: Bosnia and Herzegovina

- current value: `null`.
- source: row `2002-05-20`; not in the 1974 list.
- tree evidence: none.
- reopening trigger: a primary source shows which newsletter added BA, with its date.

### ER: Eritrea

- current value: `null`.
- source: row `2012-02-15`; not in the 1974 list.
- tree evidence: none.
- reopening trigger: a primary source shows which newsletter added ER, with its date.

### MD: Republic of Moldova

- current value: `null`.
- source: row `2008-03-31`; not in the 1974 list.
- tree evidence: none. MD is also a post-Soviet state, but it is filed here because the quarantine reason names the newsletter.
- reopening trigger: a primary source shows which newsletter added MD, with its date.

### SH: Saint Helena

- current value: `null`.
- source: row `2010-02-22`; not in the 1974 list.
- tree evidence: none. The builder's reason is that the code predates the row.
- reopening trigger: a primary source confirms the original assignment date for SH, which predates its newsletter row.

## Group C: successors of Czechoslovakia or Yugoslavia (3)

### CZ: Czechia

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: the note on withdrawn `CS` says Czechoslovakia was withdrawn 1993-01-01 and replaced by CZ and SK. It is in a `note`, not a `replaced_by` edge, because the `CS` entry records the second use of the code.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for CZ.

### SI: Slovenia

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: none direct. `YU` (withdrawn 2003-07-23) has `replaced_by` `CS`, not SI, so the tree holds no link from Yugoslavia to SI.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for SI.

### SK: Slovakia

- current value: `null`.
- source: no row; in the 1974 list (rejected).
- tree evidence: the same `CS` note as CZ. `SK` is also a withdrawn entry (Sikkim, withdrawn 1975-05-16, replaced by IN), so the code was reassigned; the registry keys by `alpha_2` and the active `SK` is the one that is null.
- reopening trigger: a primary source gives the exact ISO 3166-1 assignment date for the second use of SK.

## What would reopen the whole list

Any one of these removes the need to infer:

1. ISO publishes a bulk file or an Online Browsing Platform API with assignment
   dates. The decision record makes this the stated condition for revisiting
   the Wikipedia exception.
2. The annual review (`review_by` 2027-10-28) finds a first-party source for a
   subset. Each code is independent: remove its `QUARANTINE` entry only with the
   date and the source in the commit message.

Until then, a null with a reason is the honest answer. `is_active_on(code, date)`
returns `null` (unknown), not `false`, for a code with a null `introduced`; the
README's section 10 shows it for CZ, SK and RU on 1990-01-01.
