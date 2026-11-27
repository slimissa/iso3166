# Withdrawn entries: ISO 3166-3 alpha-4 and ISO's reservation of the alpha-2

Status: **accepted**
Date: 2026-11-26
Supersedes: none
Superseded by: none
Amends: [withdrawn-codes.md](withdrawn-codes.md) (Decision 1, the CS case)

## Context

ISO 3166-3 gives every former country name a four-letter code: the
withdrawn alpha-2 followed by two letters for what replaced it (`AIDJ`,
French Afars and Issas, now Djibouti; `CSXX`, Serbia and Montenegro). The
registry keyed its withdrawn list on alpha-2 alone, which cannot tell the
two ISO 3166-3 entries that share `CS` apart (CSHH, Czechoslovakia; CSXX,
Serbia and Montenegro).

ISO also still reserves the alpha-2 of nine former ISO 3166-1 entries. The
alpha-2 page of each on the ISO Online Browsing Platform shows one of two
statuses: "Exceptionally reserved" for FX (France, Metropolitan, "reserved
at the request of France") and SU (USSR, "reserved at the request of the
Foundation for Internet Development"), and "Transitionally reserved" for
AN, BU, CS, NT, TP, YU and ZR (reserved for 50 years after the change).
Every other ISO 3166-3 entry is "Formerly used". The registry recorded none
of this, and did not hold FX.

`docs/withdrawn-completeness.md` compares the list with every ISO 3166-3
page.

## Decision 1: `alpha_4` on withdrawn entries

Every entry of `countries.withdrawn` carries `alpha_4`: the ISO 3166-3
four-letter code, or null when no ISO page shows it. Active entries do not
carry the key. The value is taken only from the entry's ISO page; it must
match `^[A-Z]{4}$`, start with the entry's alpha-2, and be unique within the
withdrawn list (`tools/validate.py`, integrity and business layers).

The withdrawn list stays keyed by `alpha_2` in v1.x. `alpha_4` is a
field, not a key: every lookup by alpha-2 behaves as before.

## Decision 2: `reservation` on withdrawn entries

Every entry of `countries.withdrawn` carries `reservation`: the status ISO
3166-1 shows today for the entry's alpha-2, taken from its alpha-2 page on
the ISO Online Browsing Platform. Active entries do not carry the key.

| `reservation` | Meaning | Entries |
|---------------|---------|---------|
| `exceptionally-reserved` | ISO shows the alpha-2 as "Exceptionally reserved" | FX, SU |
| `transitionally-reserved` | ISO shows the alpha-2 as "Transitionally reserved" | AN, BU, CS, NT, TP, YU, ZR |
| null | ISO shows this entry as formerly used, with no current reservation of its alpha-2 | every other withdrawn entry |

The values use hyphens, as the `status` vocabulary does. The two sets are
`WITHDRAWN_EXCEPTIONAL_RESERVATION_CODES` and
`WITHDRAWN_TRANSITIONAL_RESERVATION_CODES` in `tools/parse_source.py`, and
the validator's ground-truth layer checks the data against them. Where an
entry has both an alpha-2 page and an ISO 3166-3 page and they disagree,
the alpha-2 page decides. The reservation period ISO states ("Reserved from
2010-12 to 2060-12") is recorded in the row's `note`, not in a field.

## Decision 2a: `status` gains no value

`status` keeps meaning "in use or not": every withdrawn entry has
`withdrawn`, the reserved ones included, and v1.14.0 adds no status value.
ISO's reservation is a fact about the alpha-2 today, recorded beside the
status rather than in it.

A status value for it would have collided with one already in use. The
active entries EU and UK have `status` `exceptionally-reserved`: ISO
reserves those codes and they are in use. Giving the same value to SU
and FX would make them active for every reader that tells active rows
from withdrawn ones by `status`: the flat exports (CSV, TSV, SQL, Parquet)
hold both lists in one table, the documented SQL filter `status IN
('officially-assigned', 'user-assigned', 'exceptionally-reserved')` selects
the active rows, and every wrapper's `is_active` tests the same three
values. A second spelling one character away from it (an underscore for
the withdrawn case) avoids that, but leaves two values that differ only in
punctuation, which a reader would confuse. A separate field avoids both.

## Decision 3: `withdrawal_date` may be null on an ISO 3166-3 entry

A withdrawn entry needs a `withdrawal_date`, except an entry whose ISO
page exists (it carries `alpha_4`) and gives no date. Such an entry has
null rather than a date from elsewhere. `is_active_on` answers null
(unknown) for it, and false only before a known `introduced`: the source
says the code was withdrawn, not when.

## Decision 4: CSHH waits for v2.0.0

Adding Czechoslovakia as a second withdrawn `CS` row would break every
lookup keyed by alpha-2: the validator's uniqueness check, the CLI's
`_by_alpha2(reg.all_withdrawn())`, the alpha-2 sets of `is_active_on`, the
SQL key `(alpha_2, status)`, and consumers that index the withdrawn list by
alpha-2 (ISO 4217's `tools/export_aggregated.py` fails on a duplicate). In
v2.0.0 the withdrawn key becomes `(alpha_2, alpha_4)` and CSHH joins. Until
then the CS row's `note` keeps Czechoslovakia.

## Schema version

`schema.json` moves from 1.0.0 to 1.1.0, and `meta.schema_version` follows:
the change is additive (two new fields on withdrawn rows, `alpha_4` and
`reservation`, and a null now allowed for `withdrawal_date` where it was
required in practice). No `status` value is added.
`tools/validate.py` now checks that `meta.schema_version` equals the version
in the schema's `$id`.

A consumer that pins the schema version refuses the new file until it
accepts 1.1.0. ISO 4217's `tools/vendor_iso3166.py` does
(`meta.schema_version != "1.0.0"`, at 028863f); its vendored copy keeps
working, and re-vendoring needs a 1.1.0 detector.

## Exports

`alpha_4` and `reservation` are the last two columns of every flat export
(CSV, TSV, the four SQL dialects, Parquet), after the club columns, so no
existing column moves. Both are empty for active rows.

## Consequences

- Each withdrawn row names the ISO 3166-3 entry it is.
- Each withdrawn row says whether ISO still reserves its alpha-2, and how.
- `status = 'withdrawn'` still selects every withdrawn row, and the active
  filters are unchanged.
- The withdrawn list can hold every ISO 3166-3 entry except CSHH.
