# Derived Queries — Design Decisions

This file records **why** the v1.10.0 queries are what they are. It is the
rationale, not the specification. The specification, with every signature,
edge case and worked example, is [QUERIES.md](QUERIES.md); where the two
differ, QUERIES.md wins and this file is wrong.

## The rule everything follows from

A derived query is a hypothesis until it has been run against the tree.
The first draft of this design was written from memory of what the data
"should" contain, and it was wrong in places that only the data could
reveal. Examples of what the tree said when asked:

- The design expected `currency_at("DD", "1990-01-01")` to return the East
  German mark. All 25 withdrawn entries have `currency_codes: null`; the
  currency is not in the tree, so the query returns `None`.
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
carry. `currency_at` needs an `introduced` date the tree does not carry. There
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
`DEM`); this is the confirmed v1.10.0 contract, documented as approximate. The
alternative, returning `None` for every active entry, would make the query
useless for the common case of a recent date, so the documented
approximation was preferred.

**Replacements.** `is_eu`, `is_eea` and `is_eurozone` are deprecated by
`is_eu_member_at(code, date)` in v1.12.0, which needs an `eu_membership[]`
field. `currency_at`: Deprecated by v1.11.1, which builds on v1.11.0's `introduced` field to make
currency_at exact for active entries. That sentence is the deprecation trigger. Each replacement is named in the same release notes that
introduce the approximation.

**The single hardcoded list.** `KNOWN_EU_MEMBERS` is the only data in the
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
not lie. The withdrawn case is the exception: it is `true` up to
`withdrawal_date` even though the start is unknown. That is the one place the
query can mislead (a date before 1974), and the contract says so rather than
returning `null` for every withdrawn code.

## Why is_active_on is the first exact temporal query

`currency_at` is approximate because it needs a currency history the tree
does not have. `is_active_on` needs one date per code, which `introduced` and
`withdrawal_date` provide. Where those dates exist it is exact; where they do
not it says so.

## What is deferred, and why

| Query | Deferred to | Reason |
|---|---|---|
| `is_eu_member_at(code, date)` | v1.12.0 | Needs an `eu_membership[]` field |
| `is_active_on(code, date)` | done in v1.11.0 | Needed an `introduced` field |
| `currency_at` (exact) | v1.11.1 | Depends on `introduced`; v1.11.0 ships the field only |
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
