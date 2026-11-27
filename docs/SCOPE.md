# Scope: what we did not build

The registry is an identity table for ISO 3166 codes with a temporal layer.
This page names what it does not do, so a missing feature is a recorded
decision and not a surprise. Each item has a status, the reason the tree
gives, and the trigger that would start it.

Status as of v1.12.14 (recheck 2027-05-25). Nothing is scheduled; each item starts when its trigger
fires (`README.md`, section 24). Where the repository records no reason, this
page says so and does not supply one.

| Item | Planned release | Status | Trigger |
|------|-----------------|--------|---------|
| Sanctions | v1.15.0 | out-of-scope until the trigger | A compliance consumer exists and a reliable country-level source is found |
| Geography: `regions.json`, `timezones[]` | v1.16.0 | out-of-scope until the trigger | A consumer asks for `regions.json` or `timezones[]` |
| Subdivisions (ISO 3166-2) | v1.18.0 | out-of-scope until the trigger | A consumer asks for ISO 3166-2 subdivisions |
| `root`, `siblings`, `descendants` queries | none | out-of-scope, no decision recorded | A consumer asks, then a decision record |

## Sanctions (v1.15.0)

- **Status:** out-of-scope. The first attempt, planned then as v1.13.0, stopped; it was not refused. v1.13.0 became the `introduced` evidence release, and v1.14.0 the withdrawn list against ISO 3166-3.
- **What is missing:** a `sanctions_regime` field and an `is_sanctioned_at(code, regime, date)` query.
- **Why:** a first attempt found no reachable first-party source (`README.md`, section 20).
- **Reopening trigger:** a compliance consumer exists and a reliable country-level source is found, with dates, in a stable machine-readable form.
- **Detail:** [`sanctions-reconnaissance.md`](./sanctions-reconnaissance.md) names the four candidate sources and the proposed acceptance criteria.

The registry must not be used to screen transactions or parties. It carries no
sanctions data of any kind.

## Geography (v1.16.0)

- **Status:** out-of-scope. Deferred.
- **What is missing:** `regions.json` and a `timezones[]` field. The `timezone_of(code)` query waits on the field. The existing `region`, `subregion` and `intermediate_region` fields are UN M49 and are not affected.
- **Why:** the deferred table lists `timezone_of(code)` as needing a `timezones[]` field. The tree records no source for time zones.
- **Related:** `is_landlocked(code)` is listed as "v1.16.0 or never", because it is not derivable from `borders` and needs coastline data.
- **Reopening trigger:** a consumer asks for `regions.json` or `timezones[]`.
- **Where decided:** [`QUERIES-DECISIONS.md`](./QUERIES-DECISIONS.md), "What is deferred, and why".

## Subdivisions (ISO 3166-2)

- **Status:** out-of-scope. Deferred to v1.18.0.
- **What is missing:** ISO 3166-2 as a `subdivisions.json` companion file, and the `subdivisions_of(code)` query that needs it.
- **Why:** the registry covers ISO 3166-1. The README lists "No subdivisions" as a known limitation (section 20). The tree records no further reason.
- **Reopening trigger:** a consumer asks for ISO 3166-2 subdivisions.
- **Shape if reopened:** a companion file, not new fields on the country entry. That is the wording of the deferred table; the schema is not designed.

## Root, siblings and descendants queries

- **Status:** out-of-scope. Not implemented in the CLI or in any wrapper.
- **`root` and `siblings`:** the repository records no decision about them. This page gives no reason for their absence, as the README does not.
- **`descendants`:** there is no query by that name. `successors CODE` is the descendants query, the transitive closure of `replaced_by`, and `predecessors CODE` is its reverse. Nothing is missing here except the name.
- **Reopening trigger:** a consumer asks for `root` or `siblings`. The request follows the "When someone asks for a ninth query" steps in `QUERIES-DECISIONS.md`: run it against the tree, add it to `QUERIES.md` with signatures and edge cases, add the fixture rows, and record a decision.
- **What a decision must settle first:** what "root" and "sibling" mean for a code whose `replaced_by` has several targets, such as `CS` replaced by `RS` and `ME`. The tree does not answer it.

## Recorded elsewhere

These are not in the four-item list above but are recorded as not built.
Each has its own decision in the file named.

| Item | Status | Where |
|------|--------|-------|
| `population_of`, `gdp_of` | never: "the registry is identity, not demographics" | `QUERIES-DECISIONS.md` |
| `flag_emoji(code)` | never: derivable from `alpha_2` | `QUERIES-DECISIONS.md` |
| `currency_at` with historical currencies | a later release; needs a currency history source | `QUERIES-DECISIONS.md` |
| Area-code narrowing for `calling_code_for` | not scheduled; needs numbering-plan data | `QUERIES-DECISIONS.md` |
| `source_hash` | waits for a stable raw source | `README.md`, section 24 |
| Published language packages | not published to PyPI, npm, crates.io or a Go proxy | `README.md`, section 20 |
| v1.17.0 ecosystem documentation | when the six registries are stable enough | `README.md`, section 24 |
| v2.0.0 withdrawn key `(alpha_2, alpha_4)`, and `CSHH` (Czechoslovakia) as a second withdrawn `CS` | the release that takes it; it breaks every lookup keyed by alpha-2 alone | `decisions/withdrawn-alpha4.md` |
| v2.0.0 any other breaking schema change | when a consumer needs one | `README.md`, section 24 |

## How an item leaves this page

1. The trigger fires: a named consumer, or the source the item waits for.
2. A decision record goes in `docs/decisions/` before any code.
3. The release that ships the item removes its row here and in the README's
   sections 20 and 24, and adds it to `CHANGELOG.md`.

An item stays on this page until step 3. A row that says "out-of-scope"
describes the tree at the version of the status line above, not a promise
about any later one.
