# Reconnaissance: country-level sanctions

This page records why the registry has no sanctions data, what the four
candidate sources are, and what would change that. It is a reconnaissance
note, not a design: no field, query or workflow described here exists.

Status as of v1.12.14 (recheck 2027-05-25). Nothing in this page is compliance advice. The
registry is an identity table; it is not a screening tool and must not be used
to decide whether a transaction is permitted.

## What the tree records

These statements are the only ones in the repository about sanctions. Each is
quoted from the file named.

| Fact | Where |
|------|-------|
| The sanctions release, v1.14.0, has not shipped. No `sanctions_regime` field and no `is_sanctioned_at` query exists. | `README.md`, section 20 |
| A first attempt stopped because no first-party source was reachable. | `README.md`, section 20 |
| `sanctions-freshness.yml` does not exist. | `README.md`, section 14 |
| Deferred: `is_sanctioned_at(code, regime, date)`, which needs a `sanctions_regime[]` field. | `docs/QUERIES-DECISIONS.md`, deferred table |
| Trigger: a compliance consumer exists and a reliable country-level source is found. | `README.md`, section 24 |

The tree does not record which sources the first attempt tried, in what
order, or what each returned. This page does not reconstruct that. The table
below lists the sources by name only, and says plainly that none of them was
examined for this page.

## Word choice: stopped, not declined

The first attempt (planned then as v1.13.0) was stopped by a missing source. It was not rejected on
principle. The registry has no decision record that says sanctions are out of
scope forever; the deferred table says the opposite, with a trigger.
[`SCOPE.md`](./SCOPE.md) uses the same wording.

## The four candidate sources

| Source | Publisher type | Examined in this repository? |
|--------|----------------|------------------------------|
| OFAC (US Department of the Treasury) | A national sanctions authority | No |
| EU sanctions (the consolidated list of the European Union) | A supranational body | No |
| UN sanctions (the Security Council consolidated list) | An international organisation | No |
| UK OFSI (Office of Financial Sanctions Implementation) | A national sanctions authority | No |

"No" means this repository holds no snapshot, no excerpt and no recorded
reading of the source. Anything said about what these publishers release is
background and is not verified here; before any of it is relied on it needs a
snapshot in the tree with a permalink and a vendoring date, as every other
vendored source has.

## Why none of them qualifies today

The registry's rule is in [`PROVENANCE.md`](./PROVENANCE.md): a field comes
from a first-party source or it stays `null`, and "an empty field is honest;
a wrong field is not". Four gaps stand between those sources and a field.

1. **The fact needed is a table the sources are not known to publish.** The
   deferred query asks about a code, a regime and a date. That needs, per
   country, a regime name with a start date and an end date. The sources above
   are known for lists of designated persons, entities and programmes. Turning
   them into country-level date ranges would be an editorial step by the
   registry, which the rule does not allow. The tree says only that the first
   attempt found no reachable first-party source; it does not say whether this
   gap, reachability, or both was the cause.
2. **There is no standards body for it.** `PROVENANCE.md` defines first-party
   as the standards body that defines the code. For a sanctions regime the
   authority is the sanctioning government or body, and each regime has its
   own. Four publishers means four first-party sources with four formats and
   four meanings of "regime".
3. **No stable file is recorded.** Every vendored snapshot in `tools/` carries
   a source and either a `review_by` date one cadence period after its
   vendoring date, or `closed` with a `closed_reason`
   (`tests/test_snapshot_meta.py`). Those that track a changing source also
   record a version or permalink (see `tools/introduced_snapshot.meta.json`).
   A sanctions source would need the same, and a live list that changes
   without a version has no permalink to record.
4. **Dates are the hard part.** The temporal layer is built on dated ranges
   (`introduced`, `withdrawal_date`, the four club arrays). A sanctions field
   that lacked an effective-from and an effective-to date would not fit that
   layer, and one with guessed dates would break the registry's central
   promise.

## What a source must provide to reopen the decision

These are proposed acceptance criteria, derived from how the existing
snapshots are accepted. They are not a locked decision; a decision record
would adopt, change or replace them.

- Machine-readable, so a generator can build the snapshot deterministically.
- Stable: a versioned or permalinked file, not a page that changes silently.
- Country-level, with an effective-from and, where it ended, an effective-to
  date per regime. A person or entity list does not qualify on its own.
- First-party for the regime it describes.
- A licence that allows vendoring a copy into `tools/`.

A source that meets all five lets the release start. A source that meets four
does not: the missing one is recorded here and the decision stays deferred.

## The two triggers, stated together

`README.md` section 24 gives one trigger with two parts. Both must hold:

1. A compliance consumer exists. Without one there is nobody to check the
   design against, and the registry's other deferred items follow the same
   rule.
2. A reliable country-level source is found, meeting the criteria above.

If only the second holds, the source is recorded here and nothing ships.

## What reopening would add

From the deferred table, and nothing beyond it:

- A `sanctions_regime[]` field.
- An `is_sanctioned_at(code, regime, date)` query.
- A freshness workflow. `sanctions-freshness.yml` is the name the README uses
  for its absence.

The semantics of unknown regimes, unknown codes and missing dates are not
decided. They would be settled in a decision record before any code, as for
`is_active_on` (see `QUERIES-DECISIONS.md`, "Why is_active_on is tri-state").

## Reopening procedure

1. Name the consumer and the question it needs answered.
2. Vendor the candidate source into `tools/` with its permalink, vendoring
   date and `review_by`.
3. Run it against the criteria above and record the result in this file.
4. Write the decision record in `docs/decisions/`.
5. Only then add the field, the query, the wrappers, the fixture rows and the
   workflow, in the order the "When someone asks for a ninth query" section of
   `QUERIES-DECISIONS.md` gives.

## What this page does not settle

- Which of the four sources is best. None has been examined.
- Whether country-level sanctions dates can be published by a first-party
  source at all. That is the open question.
- Whether the registry should ever carry the field, as opposed to a separate
  companion file. The README's wording for subdivisions is a companion file;
  nothing is recorded for sanctions.
