# Derived Queries — Design Decisions

This file records **why** the v1.10.0 queries are what they are. It is the
rationale, not the specification. The specification, with every signature,
edge case and worked example, is [QUERIES.md](QUERIES.md); where the two
differ, QUERIES.md wins and this file is wrong.

v1.12.0 added Query 10 (club memberships) and retired the approximation of
Query 1; the sections "Why the approximate queries are approximate" and
"Why club memberships are arrays on the entry" record both.

## The rule everything follows from

A derived query is a hypothesis until it has been run against the tree.
The first draft of this design was written from memory of what the data
"should" contain, and it was wrong in places that only the data could
reveal. Examples of what the tree said when asked:

- The design expected `currency_at("DD", "1990-01-01")` to return the East
  German mark. All 25 withdrawn entries have `currency_codes: null`; the
  currency is not in the tree, so the query returns the successor's current
  currency (`["EUR"]`, v1.11.1) and documents that it is not the mark.
- The design expected `region_tree("TW")` to be `["Asia"]` and
  `region_countries("Antarctica")` to be `["AQ"]`. Both `TW` and `AQ` have
  `region: null`.
- The design expected `succession_path("SU", "RU")` to exist. `SU` has
  `replaced_by: null`.
- The design expected `+44` to mean `GB`. The tree gives `44` to `GB`, `GG`,
  `IM` and `JE`, and gives `1` to 26 entries with no area codes.
- The design built `is_eurozone` on "uses EUR and is not `AD`, `MC`, `SM` or
  `VA`". Eleven more entries use EUR (`AX`, `BL`, `GF`, `GP`, `MF`, `MQ`,
  `PM`, `RE`, `TF`, `YT` and `ME`), which would have made `ME` an EU member.
- The design said the withdrawal field is `withdrawn_date`. It is
  `withdrawal_date`.

So the rule is: **where the tree and an idea disagree, the tree wins, and
the idea is rewritten.** QUERIES.md is written from the tree. Its worked
examples are re-run against `iso3166.json` by test 22 of
`test-derived-queries.sh`, so the document cannot drift from the data.

## Why these eight

The eight were chosen by value per consumer among questions the v1.9.3 tree
can answer.

| Query | Who needs it | Frequency |
|---|---|---|
| `is_eu`, `is_eea`, `is_eurozone` | Anything that treats EU countries differently (pricing, VAT, consent) | High |
| `region_tree`, `region_countries` | Map displays, "give me all countries in X" | High |
| `borders_transitively` | Travel, shipping, customs | Medium |
| `succession_path`, `successors`, `predecessors` | Joining historical records to current codes | Medium |
| `calling_code_for` | Phone-based onboarding and fraud checks | Medium |
| `currency_at` | Backtesting, historical reporting | High |

Eight queries, eleven methods: the EU predicates and the two succession
closures count once each as a family.

## Why the approximate queries are approximate, and why they ship anyway

`is_eu`, `is_eea` and `is_eurozone` need membership facts the tree does not
carry. (`currency_at` was in this group in v1.10.0, when the tree carried no
`introduced` date; see "Why currency_at is exact for dated entries".) There
were three options:

1. **Do not ship them until the fields exist** (v1.11.0, v1.12.0). Rejected:
   every consumer already computes these answers, by hand and without
   documentation, and each version differs on the edge cases.
2. **Ship them as exact, hardcoding the missing data.** Rejected: data that
   is not in `iso3166.json` cannot be checked by the tree's gates, and it
   would drift silently while claiming to be exact.
3. **Ship them labeled approximate, with the limitation documented at every
   surface, and deprecate them when the exact field exists.** Chosen.

The approximation is deliberately **visible**. The word "approximate" is in
the docstring, the CLI help and the README table of every approximate query,
and QUERIES.md says for each example whether the tree can answer exactly.
Where the tree has no answer at all (a withdrawn entry before its
withdrawal), the query returns `None` instead of inventing one. Where the tree
has a current answer but not a dated one (an active entry), the query returns
the current answer and says so; `currency_at("DE", "1990-01-01")` returns
`["EUR"]`, which is the tree's answer and approximate for that date (Germany used
`DEM`); this was the v1.10.0 contract, documented as approximate. The
alternative, returning `None` for every active entry, would make the query
useless for the common case of a recent date, so the documented
approximation was preferred. v1.11.1 keeps that choice for the currency
itself and bounds the answer by the entry's lifetime.

**Replacements.** (Resolved in v1.12.0; this paragraph is the v1.10.0 plan.)
`is_eu`, `is_eea` and `is_eurozone` were to be deprecated by
`is_eu_member_at(code, date)`, which needs an `eu_membership[]` field. `currency_at` is no longer deprecated: v1.11.1 makes it exact for dated
entries (below). Each replacement is named in the same release notes that
introduce the approximation.

**The single hardcoded list** (retired in v1.12.0; see "Why club memberships
are arrays on the entry"). `KNOWN_EU_MEMBERS` was the only data in the
registry that is not read from `iso3166.json`. It is the reason
`check_docs_match_tree.py` cannot check the EU answers, and therefore the
reason they are deprecated rather than maintained. `is_eurozone` is built
from that list plus `currency_codes`, rather than from "uses EUR minus a
list of exceptions", because a second hardcoded exception list would have
been a second thing to keep correct. The cost: overseas territories that
use the euro (`GF`, `GP`, `MQ`, `RE`, `YT`, `AX`, ...) return `false`.

## Why multi-valued answers are lists

`calling_code_for("+44 20 7946 0958")` returns four codes, and
`calling_code_for("+1 202 555 0100")` returns 26. The registry cannot
tell which is right, because the caller knows the area code and the tree does
not. A query that guessed would be silently wrong; a query that returns every
candidate is never wrong, and leaves the one decision to the party that has the
information. The same reasoning makes `currency_at` return a list: a
withdrawn entry that split (`AN`, `YU`) has several successors, each with its
own currency.

## Why `None` and not an exception

`None` (`nil`, `Option::None`, `false` from a Go `bool`) means "the tree
cannot answer". Unknown codes and malformed dates do not raise. This keeps
the four languages identical: Rust and Go have no exceptions to mirror, and a
query that raised in Python but returned a value elsewhere would fail the
cross-language check. The cost is that "unknown code" and "known code with no
answer" look the same for optional-valued queries; the CLI distinguishes the
boolean predicates (exit 2 for unknown).

## Why successors and predecessors are the full transitive closure

Before v1.10.0 the CLI's `successors` returned only **terminal** successors
(codes that were never replaced), and the cross-language fixture enforced
that. The new wrapper queries returned **all descendants**, and the first
design text said both at once. They cannot both be right, and carrying two
meanings for one name across five surfaces is worse than either.

All descendants was chosen:

- `succession_path("YU", "RS")` already passes through `CS`; a `successors`
  that hid `CS` would disagree with the path next to it.
- Terminal successors are recoverable from the closure (keep the codes that are
  active), but the closure is not recoverable from the terminals.
- `predecessors("CS")` is meaningful (`["YU"]`) only under the closure
  definition; under the terminal definition it was empty.

This is a **breaking change for CLI users**: `successors YU --raw` used to
print `ME` and `RS` and now prints `CS`, `ME` and `RS`; the `--json` key
`terminal_successors` is replaced by `successors`; `predecessors CS` used to
print nothing. The fixture's `successors` and `predecessors` sections change
with it. The release notes say so under "BREAKING".

## Why the CLI is a first-class surface

`iso3166 is-eu DE` is the first thing a new user tries. If the CLI and the
Python wrapper disagreed about `is_eu("GB")`, the user would stop trusting
both. So the CLI implements the same semantics, and `tools/check_cross_language.sh`
runs every fixture case through the CLI as well as the four wrappers. The CLI
is a separate implementation over the raw JSON (not a wrapper around the Python
class), so the check compares two independent computations, not one.

The three boolean predicates follow the CLI's standard exit codes like every
other subcommand: 0 success, 1 code not found, 2 usage error, 3 registry
missing. The boolean is printed to stdout (`true` or `false`) and `is-eu GB`
exits 0, because GB exists and the command did its job. An earlier draft
encoded the answer in the exit status (0 true, 1 false, 2 not found), in the
style of `grep` or `test`. That was rejected: it makes `iso3166 is-eu GB ||
handle_error` treat an existing country as "not found", and it gives exit code 1
two meanings inside one CLI. The answer is data, the exit code is plumbing, and
this matches the wrappers, where the boolean is the return value and an unknown
code is a separate case.

**Known divergence in v1.10.0, closed in v1.10.1.** The `iso3166` console
script that `pip install` creates is `wrappers/python/iso3166/cli.py`, a
different file from `tools/iso3166_cli.py`. v1.10.0 changed only the latter
(and `bin/iso3166`, which runs it when no installed script is found), so the
packaged script kept its v1.9.x subcommands and terminal-only `successors`.
v1.10.1 ports the nine subcommands and the closure semantics into the packaged
script. It calls the matching `CountryRegistry` methods instead of
reimplementing them, because `tools/` is not part of the pip package and a
wrapper that imported it would break outside a checkout.

## Why alpha-2 collisions resolve to the active entry

`AI` and `SK` each name two entries. Every field read prefers the active one
because that is what a consumer asking about "SK" in 2026 means. The
succession graph can only use withdrawn entries (only they have
`replaced_by`), so `successors("SK")` is `["IN"]`. The two rules can disagree
about one code; the disagreement is stated in QUERIES.md instead of hidden by
choosing one meaning for everything.

## Why the worked examples are in the design document

The examples in QUERIES.md are the test fixture. They are an index table that
a script can parse, so the design and the tests cannot drift apart: test 22
re-runs every row and every inline example against the tree, and checks that
each row also appears in the cross-language fixture. A claim in the
document is a claim a machine has checked.

## Why is_active_on is tri-state

`introduced` is null for 76 of 252 active entries, because the source is silent
or contradicted by the tree. A boolean query would have to turn each null into
`true` or `false`, and either answer is a claim the registry cannot back. So
the query returns `false` only when the answer is known to be no (before
`introduced`, after `withdrawal_date`, unknown code, malformed date), `true`
when it is known to be yes, and `None` / `null` / `nil` / `Option::None` when
the registry does not know. The snapshot's null is honest, so the query must
not lie. Withdrawn codes have no sourced start. The query returns `true`
between 1974-01-01 and `withdrawal_date`, which is a weaker claim ("it
existed at some point before withdrawal") than the active case, and `null`
before 1974-01-01.

## Why 1974 is the floor

ISO 3166 was first published in 1974, so no alpha-2 code existed before then,
and the 1974 edition is the earliest date any registry entry can carry (the
snapshot's own earliest `introduced` is `1974-09-15`). The first version of
this query returned `true` for any date up to `withdrawal_date`, so
`is_active_on("DD", "1800-01-01")` said East Germany's code was active in 1800.
That is a false positive the registry can avoid at no cost: before 1974 the
answer is `null`, not `true`. The floor is `1974-01-01` rather than
`1974-09-15` because the withdrawn entries have no start date at all; the
September date belongs to the edition, not to a given code. The floor does
not apply to active entries, which are answered by their own `introduced`.

## Why currency_at is exact for dated entries

v1.10.0 shipped `currency_at` as an approximation because the tree had no
temporal anchor: an active entry returned its current currency for every date,
including dates before the country existed. v1.11.0 added `introduced`
(176 of 252 active entries have a date). v1.11.1 uses it.

"Exact" here means exact about *when the code exists*, and nothing more:

- An active entry with `introduced` returns `None` before it and its current
  `currency_codes` from then on. `currency_at("DE", "1970-01-01")` is `None`.
- A withdrawn entry with `withdrawal_date` returns the successor's current
  currency up to and including `withdrawal_date`, and `None` after it, because
  the code no longer exists.
- An active entry whose `introduced` is null returns `None`: the source is
  silent, so the registry will not guess. That is 76 entries (27 quarantined, 46
  source silent, 3 not officially assigned). The "approximation for active
  entries without `introduced`" is gone for them, replaced by `None`.

What is **not** exact is the currency. The tree stores no currency history, so
`currency_at("DE", "1990-01-01")` returns `["EUR"]` and
`currency_at("DD", "1990-01-01")` returns the successor's `["EUR"]`, although
the euro did not exist in 1990 and East Germany used the East German mark. The
docstring of every wrapper and the CLI help say so. The withdrawn rule is the
reverse of v1.11.0's, which returned `None` before `withdrawal_date` and the
successor's currency after it. The new rule treats the withdrawn code's
lifetime as the span in which it was valid; it trades one approximation (a
successor's currency after the code is gone) for another (a successor's
currency while the code was alive).

`currency_at` is not deprecated. v1.12.0 (club memberships) leaves it as is.
If a later release wants the historical currency of a withdrawn entry, that is
a separate release and needs a source for currency history, which the tree
does not have.

## Why club memberships are arrays on the entry

The four clubs (EU, EEA, eurozone, EU customs union) are stored on every active
entry of `iso3166.json` as lists of `{from, to}` ranges. Three alternatives were
considered.

1. **A separate `clubs.json` companion.** Rejected: the gates, the schema and
   the wrapper copies already work on `iso3166.json`, and a companion would be
   a second file that can disagree with it about which codes exist.
2. **One `club_memberships` object per entry, keyed by club.** Rejected: four
   top-level arrays keep each club a plain list, one schema definition
   (`membership`), and a one-line read in every language. A fifth club costs one
   field, not a change to the shape.
3. **Four arrays, `[]` for non-members.** Chosen. The snapshots stay the source
   of truth (their null policy is "no key"); the tree gets `[]` so a field is
   never absent on an active entry, and `validate.py` can require it.

Ranges, not a single date, because the UK left, and a future member may leave and
rejoin: the array has several ranges then. `to` is the **last day** and
inclusive, so `GB` is a member on 2020-01-31, the day it left, and a reader
never has to decide whether `to` is exclusive.

Withdrawn entries carry none of the four: a withdrawn ISO code was never a
member of anything that exists today, and the schema forbids the fields there.

**The hardcoded list is gone.** `KNOWN_EU_MEMBERS` and `EEA_NON_EU` are no
longer read. The three EU predicates read the arrays and answer exactly what
they answered at v1.11.1 for every code in the registry (a test compares them
code by code), so v1.10.0 callers see no change. The two constants stay
exported, unused, so that imports do not break; they are not updated.

**Territories.** Membership is per ISO code and does not inherit from the
sovereign state, so `GF`, `GP`, `MQ`, `RE`, `YT` and `AX` have `[]` and the
queries return `false` for them, the same limitation the approximate versions
had. Greenland (`GL`, in the Community 1973 to 1985) is also `[]`. These are
documented false negatives, not facts the registry asserts.

## Why the dated queries never return null

`is_active_on` is tri-state because `introduced` is null for 76 active entries:
the source is silent and the registry says so. Membership is different. The
snapshot states membership for every active entry, and `[]` is a statement.
There is no input for which the registry "does not know", so `null` would be a
value nothing returns. The four queries return a plain boolean in every
language (no `Option`, no pointer), and a malformed date, an unknown code and a
date outside every range are all `false`.

The CLI still lists exit code 4 for the tri-state contract, so that a script
that handles 0, 1 and 4 for `is-active-on` handles these commands too. Nothing
produces it today. If a future snapshot is allowed to say "unknown" (for
example, a quarantined date), that is when a `null` appears, in every surface at
once.

## Why the dated CLI commands exit 1 for false

`is-eu` exits 0 for both answers and uses the exit code for "not found", the
v1.10.0 contract. The dated commands follow `is-active-on` instead: 0 true, 1
false, 2 malformed date. An unknown code is `false` (exit 1), not "not found",
because the library's answer for it is `false` and the CLI must agree with the
library. The cross-language check enforces that agreement.

## Why provisional application is included

v1.12.0 started every EEA range at the formal entry into force, as Wikipedia's
state table lists it. That made `is_eea_member_at("BG", "2010-01-01")` false,
although the EEA Enlargement Agreement had applied to BG since 2007-08-01. A
reader who asks whether a state was in the EEA on a date wants to know whether
EEA rules applied then; a treaty that is applied provisionally is applied. So
v1.12.1 counts provisional application. The EEA agreement for the 2004 ten
was provisionally applicable from 2004-05-01 and entered into force on
2005-12-06; for BG and RO, provisionally from 2007-08-01 and in force on
2011-11-09 (EFTA, EEA Legal Texts, "EEA Enlargement"; Wikipedia, EEA Agreement).

**Where the union lives.** The wrappers read `iso3166.json`, not the
snapshots, and the flat exports are a view of the same arrays. Two places to
check (the array and a side table of provisional ranges) would have meant five
query implementations that can drift apart, and an export that disagrees with
the library. So the provisional ranges are unioned into `eea_membership`
when the tree is built (`tools/enrich_club_memberships.py`), and no wrapper has
query logic for them. "True for either range" is the union of the two ranges,
which is one contiguous range. The formal date is not lost: it is the
snapshot's `data`, and the provisional range is the snapshot's
`meta.provisional_application`. The cost: the arrays in `iso3166.json` no longer
equal the snapshot `data` for these twelve states, and `--check` now compares
against the union.

**Inclusive ends.** Every range in the registry ends on its last day. The
provisional range therefore ends on the day before the formal entry into force
(2005-12-05, 2011-11-08), and the enrich tool rejects a provisional range that
leaves a gap or an overlap with the formal one. That check is a guard against
a mistyped date, not a formality: a date one year off (2006-12-06) is a
gap, and it fails.

**Croatia.** HR signed the EEA enlargement agreement on 2014-04-11 and it
entered into force on 2025-02-19. The sources read for this release give no
date for any provisional application, so HR has the formal date only and
`is_eea_member_at("HR", "2020-01-01")` is false. If a primary source dates it,
add an `HR` entry to `meta.provisional_application` (ending 2025-02-18) and
the fixture case; nothing else changes.

Three other dates are inferences, listed in docs/decisions/club-memberships.md:
1958-01-01 for the six founders, 2020-12-31 for the UK's EEA and customs-union
end, and 1968-07-01 for the customs union's start.

## Why is_active_on is the first exact temporal query

`currency_at` needs a currency history the tree does not have, so it is exact
only about the entry's lifetime. `is_active_on` needs one date per code, which
`introduced` and `withdrawal_date` provide. Where those dates exist it is
exact; where they do not it says so.

## What is deferred, and why

| Query | Deferred to | Reason |
|---|---|---|
| `is_eu_member_at(code, date)` and the three sibling club queries | done in v1.12.0 | Needed the four membership arrays |
| `is_active_on(code, date)` | done in v1.11.0 | Needed an `introduced` field |
| `currency_at` (lifetime-bounded) | done in v1.11.1 | Uses `introduced` and `withdrawal_date` |
| `currency_at` with historical currencies | a later release | Needs a source for currency history; none is in the tree |
| `is_sanctioned_at(code, regime, date)` | v1.13.0 | Needs a `sanctions_regime[]` field |
| `timezone_of(code)` | v1.14.0 | Needs a `timezones[]` field |
| `subdivisions_of(code)` | v1.16.0 | Needs a `subdivisions.json` companion |
| `is_landlocked(code)` | v1.14.0 or never | Not derivable from `borders`; needs coastline data |
| `population_of`, `gdp_of` | never | The registry is identity, not demographics |
| `flag_emoji(code)` | never | Derivable from `alpha_2`; not a registry concern |
| Area-code narrowing for `calling_code_for` | not scheduled | Needs numbering-plan data the tree does not carry |
| Packaged `iso3166` console script parity | done in v1.10.1 | Was out of scope for v1.10.0 (see above) |

## When someone asks for a ninth query

1. Run it against the tree. If the tree cannot answer it exactly, decide
   whether an approximate answer, clearly labeled, is useful; if not, defer it.
2. If it is answerable and valuable, add it to QUERIES.md with its signatures,
   edge cases with tree values, and worked examples, and add the examples to the
   index and to the fixture generator.
3. If it needs a new field, add it to the deferred table with the release that
   adds the field.
