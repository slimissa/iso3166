# Introduced field

Status: **accepted**
Date: 2026-10-28
Supersedes: none
Superseded by: none

## Context

The registry needs an `introduced` field on active entries to answer
"what was true on date X?" queries. Before v1.11.0, `currency_at` was
approximate because the tree had no temporal anchor.

## Decision

Add `introduced` (`YYYY-MM-DD` or `null`) to active entries. It is the
date the ISO 3166-1 standard added the code. Phase 1 (this ADR) produces
only the snapshot; wiring it into `iso3166.json` and the wrappers is Phase 2.

Algorithm, implemented in `tools/build_introduced_snapshot.py`:

1. Status other than `officially-assigned` (EU, UK, XK): null.
2. Code in the quarantine list (below): null.
3. Code in the maintainer-supplied 1974 list: `1974-09-15`.
4. Code in `wikipedia_dates.json` `data`: that date.
5. Otherwise null, reason "source silent".

Withdrawn entries are null. AI and SK are both active and withdrawn, so
the snapshot (keyed by alpha_2) has 275 keys, not 277. The active value wins.

## Source (the exception)

Wikipedia, ISO 3166-1, "Changes" (Edition/Newsletter table), permalink
`https://en.wikipedia.org/w/index.php?title=ISO_3166-1&oldid=1258392980`, accessed 2026-10-28. This is an explicit
exception to the first-party source policy:

- ISO OBP does not publish assignment dates on per-country pages (maintainer
  screenshots; the harvested `DE.html` has status but no date).
- The ISO 3166-1 standard is paywalled.
- Wikipedia's table is the only free, reachable source.

The exception is time-limited. Revisit if ISO publishes a bulk file or an
OBP API with assignment dates.

## Known defects in the source

- The file's `data` mixes newsletters that added a code with newsletters that
  only changed an entry. Rows for codes in the 1974 list are ignored (the list
  wins). Rows for ER, SH, MD and BA are quarantined as change dates.
- The 1974 list has 184 codes, not 142 as first stated, and omits about 30
  territories that were in the 1974 edition (e.g. KY, GU, PR, VG). They are null
  ("source silent"), not wrong.
- The 1974 list contains codes that cannot be 1974 additions. Quarantined
  [confirmed by tree withdrawals]: BJ, DJ, KI, MM, VU, ZW. Quarantined [likely, by history]:
  AM, AZ, BA, BY, CZ, EE, ER, GE, KG, KZ, LT, LV, MD, RU, SH, SI, SK, TJ, TM, UA, UZ.

## Precision

`introduced` is the date the code was added to ISO 3166-1. It is not the
currency introduction date, the date a country adopted a currency, or
independence. For original codes the date is the 1974 edition's date
`1974-09-15` (not independently verified; supplied by the maintainer).

## Null policy

Counts: {'active_from_1974_list': 161, 'active_from_data': 15, 'active_null_not_assigned': 3, 'active_null_quarantined': 27, 'active_null_source_silent': 46, 'withdrawn_null': 25}. Every null has a reason in
`meta.null_reasons`. Source-silent codes (46): AI, AQ, AS, AW, BF, BV, CC, CD, CK, CX, EH, FK, FM, FO, GF, GI, GP, GS, GU, HM, HR, IO, KN, KY, MH, MK, MP, MQ, MS, NC, NF, PF, PM, PN, PR, PW, RE, SJ, TC, TF, TK, UM, VG, VI, WF, YT.
Withdrawn entries are null: this table gives no reliable start date.

## Refresh cadence

Annual, or on a new ISO edition. `review_by: 2027-10-28`.

## Consequences

- `is_active_on` must treat null as unknown (tri-state), not as active.
- `currency_at` remains approximate for null entries (176 of 252 are dated).
- A source-policy exception exists and must be re-evaluated annually.

## Alternatives considered

- Skip `introduced`: rejected, the capability phase needs it.
- Blanket 1974 default: rejected, wrong for post-1974 successors (CD, BF, FM).
- Paid ISO source: not available.
- Derive from a change log: the tree has none.
