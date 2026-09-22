# Withdrawn codes and successors

Status: **accepted**
Date: 2026-09-22
Supersedes: none
Superseded by: none

## Context

ISO 3166-1 assigns alpha-2, alpha-3, and numeric codes to countries and
territories. Codes can be withdrawn. ISO 3166-3 tracks withdrawals and
their successors. Some successor chains are longer than one hop:

YU Yugoslavia withdrawn 2003-07-23 replaced by CS
CS Serbia and Montenegro withdrawn 2006-09-26 replaced by RS, ME
text


Some withdrawn codes were later reassigned to a different entity:

AI French Afars and Issas withdrawn 1977-06-27 replaced by DJ
AI Anguilla assigned 1977-06-27
text


`AI` is both a withdrawn code and a currently-active one. So is `SK`
(Sikkim -> Slovakia). This creates three design questions.

## Decision 1: withdrawn codes live in a separate array

`iso3166.json` has `countries.active` and `countries.withdrawn`, not a
single flat array with a status field doing double duty as a section
marker. This mirrors ISO 4217's split and lets consumers who only care
about current countries ignore the historical record entirely.

Within `active`, the `status` field distinguishes three sub-cases:
`officially-assigned`, `user-assigned`, `exceptionally-reserved`.

## Decision 2: `replaced_by` may point to any code, active or withdrawn

The natural check -- "every `replaced_by` target is an active country"
-- is wrong. It rejects legitimate succession chains: `YU`'s immediate
successor `CS` was itself withdrawn, so a `YU` entry whose `replaced_by`
is `["CS"]` fails the check even though it is correct.

The correct rule: every `replaced_by` target must be a code that exists
*anywhere* in the registry, active or withdrawn. This is what
`tools/validate.py`'s cross-reference layer enforces.

This was caught during development: the initial implementation required
active targets and reported a false positive on `YU -> CS`. The fix
widened the check.

## Decision 3: reassigned codes are the primary key, not the primary key

`alpha_2` is not unique across the whole registry -- `AI` and `SK` each
appear twice. The SQL export therefore uses a composite primary key:

```sql
PRIMARY KEY (alpha_2, status)

and the country_currencies table has no foreign key to
countries(alpha_2), because alpha_2 alone doesn't identify a unique
row. A currency code refers to the country's currently-active entry, so
consumers join with an explicit status filter.

The wrapper API reflects the same reality: active("AI") returns the
Anguilla entry, and with_alpha2("AI") returns both entries. Callers
who need history use the second; everyone else uses the first.
Consequences

    The registry cannot be a simple lookup table keyed on alpha-2. Every
    consumer that joins on alpha-2 must decide whether it wants the
    active entry or the full history.

    The SQL export is slightly less convenient than it would be with a
    unique alpha-2: no single-column foreign keys.

    Succession chains are represented honestly. A consumer tracing a
    corporate lineage can walk replaced_by from any withdrawn code to
    its ultimate successor, following as many hops as the chain has.

Alternatives considered

Single flat array. One countries array with a status of
withdrawn on historical entries. Rejected: it makes the common case
(list current countries) into a filtered case, and it puts the
AI/Anguilla and SK/Slovakia overlap in the same namespace with no
structural separator.

Synthetic codes for reassigned entries. Rename the withdrawn AI
to AI_OLD or AI_1977. Rejected: ISO 3166-3 does not do this, and
inventing a code is worse than admitting that one key can carry two
entries.

Successor as a single code, not a list. replaced_by: "CS" rather
than replaced_by: ["CS"]. Rejected: some withdrawals have multiple
successors (CS -> RS, ME; AN -> BQ, CW, SX), and forcing a
single value would require an arbitrary choice.
