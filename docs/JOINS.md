# Joins: what the other registries read from this one

Status: normative for this registry's fields. The other registries' own
`docs/JOINS.md` files describe their side of each join; where they disagree
with this file about an ISO 3166 field, this file is the one to fix.

ISO 3166 is the root of the join graph: other registries key on `alpha_2`.
ISO 10383's JOINS.md says a join is documented where the target of the join
lives, because a consumer "cannot see the shape from its own side". This is
that document for ISO 3166. The consumer list is `tools/consumers.json`; the
rules every registry follows are in
[`CROSS_REGISTRY_CONTRACT.md`](./CROSS_REGISTRY_CONTRACT.md).

Facts below were read from the consumers' public repositories on 2026-11-04.
A row that says "none recorded" means no reader was found there on that day,
not that none exists.

## The fields consumers read

| Field | Read by | How: join key and comparison rule |
|-------|---------|-----------------------------------|
| `alpha_2` | ISO 4217, ISO 10383, Exchange Calendar | **Join key.** The consumer's country code must equal an `alpha_2` of an **active** entry, compared as an exact uppercase string. ISO 4217 checks `countries[].code` against the active list; ISO 10383 checks every MIC's `country_code` (`ZZ` allowed there); Exchange Calendar checks every exchange's `country_code`. Asset Identifiers declares `instruments[].country` with the pattern `^[A-Z]{2}$` and does not vendor this registry yet. |
| `name` | Exchange Calendar | Its `country` value must equal `name` **byte for byte**: no case folding, no Unicode normalization, no trimming. |
| `region` | ISO 4217 | Read from the vendored snapshot to group currencies by region. The string is used as it is; this registry owns the value. |
| `subregion` | ISO 4217 | As `region`. In v1.12.3 the allowed values are the 17 M49 subregions in `tools/m49_subregion_snapshot.json`. |
| `currency_codes` | ISO 4217 | ISO 4217's `check_country_codes.py --membership` compares each country's list with ISO 4217's own country-to-currency entries, against a reviewed allow-list. A `null` list means "no currency recorded" and is treated as empty. The reverse edge: every code here must be an active code in `tools/iso4217_snapshot.json` (validator layer 4). |
| `independent` | none recorded | Part of the surface a consumer may read. Nothing in the consumers' public files reads it on 2026-11-04. |

## Rules for every join

1. **Join on active only.** `SK` and `AI` appear in both `countries.active`
   and `countries.withdrawn` (a withdrawn code was reissued). A consumer must
   resolve a code against the **active** list. A code found only in the
   withdrawn list does not resolve.
2. **`ZZ` is not a country.** It is allowed in ISO 10383's `country_code` for
   MICs with no single country. It is not an `alpha_2` here and no other
   registry may use it as one.
3. **Names compare byte for byte.** A consumer that stores a `name` stores
   the string it vendored and compares it exactly.
4. **Vendor a tag, record it.** A consumer vendors the `iso3166.json` of a
   tagged release (`vX.Y.Z`), byte for byte, and records the tag and the
   file's SHA-256 next to it (contract rule 2). Whether a copy is current is
   answered by `tools/check_consumers_current.py` (advisory, network).
5. **A country can lack a field.** `currency_codes` and `subregion` can be
   `null` or empty (`AQ`, `EU`, `UK`, `XK`). A consumer must not treat that as
   an error.

## Consumer impact

From v1.12.4 on, each release's CHANGELOG section carries one line,
`Consumer impact:`, that names which of the consumed fields above changed
in the release (`alpha_2`, `name`, `region`, `subregion`, `currency_codes`,
`independent`, and the set of active codes), or says `none`. A consumer
decides from that line whether to re-vendor.

## Not consumers of a field

- **Corporate Actions**: no country field in its public `schema.json`,
  `actions.json` or README on 2026-11-04. The edge is planned.
- **Asset Identifiers**: has `instruments[].country` in its schema (a
  pattern check only); it does not vendor this registry yet.
- **LAS_Shell**, **Tempus**: no country field found, or no public repository
  reachable, on 2026-11-04.

## Open disagreements

Recorded in [`decisions/cross-registry-edges.md`](./decisions/cross-registry-edges.md):
six countries where this registry's `currency_codes` and ISO 4217's
country-to-currency entries differ, one of them (`GS`) an open request to this
registry.
