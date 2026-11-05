# ADR: Cross-registry edges, state on 2026-11-04

Status: accepted. A record of what was found, not a design. The rules are in
[`../JOINS.md`](../JOINS.md) and [`../CROSS_REGISTRY_CONTRACT.md`](../CROSS_REGISTRY_CONTRACT.md).

## Context

The fourth closure audit read the sibling registries' public repositories
and joined their country data with v1.12.3. Every join passed. The versions
they vendor, and the README's account of who reads what, did not match what
this tree said.

## The data joins (all against v1.12.3)

| Join | Result |
|------|--------|
| ISO 4217 `countries[].code` in this registry's active `alpha_2` | 0 unresolved |
| ISO 10383 MIC `country_code` (148 distinct, `ZZ` excluded) | 0 missing |
| Exchange Calendar `country_code` (74 of 74) and `country` equal to `name` | 0 missing, 0 name differences |
| This registry's `currency_codes` in ISO 4217's active currencies | 0 unknown |

## What each consumer vendors

| Consumer | Vendors | v1.12.3 is | Evidence |
|----------|---------|------------|----------|
| ISO 4217 | v1.8.0, byte-identical to the tag | 4 minors ahead | its `iso3166_snapshot.meta.json` (`source_version`, `snapshot_sha256`) |
| ISO 10383 | v1.6.9, as a derived `alpha_2_set` | 6 minors ahead | its README and meta |
| Exchange Calendar | v1.5.2, byte-identical to the tag | 7 minors ahead | its `iso3166_snapshot.meta.json` |
| Corporate Actions | nothing | n/a | no country field in `schema.json`, `actions.json` or README |
| Asset Identifiers | nothing | n/a | `instruments[].country` in `schema.json`: pattern only |
| LAS_Shell | not found | n/a | no country field in its README |
| Tempus | not found | n/a | repository not publicly reachable |

The differences between the vendored copies and v1.12.3 that a consumer can
see: `AI` `subregion` (`Caribbean` to `Latin America and the Caribbean`),
`BG` `currency_codes` (`BGN` to `EUR`, in Exchange Calendar's copy), and the
`independent` field of Exchange Calendar's v1.5.2 copy. No code set and no
`name` differs.

## Decisions

1. README section 22 is corrected: Exchange Calendar also reads `name`;
   ISO 4217 also reads `region`, `subregion` and `currency_codes`; Corporate
   Actions has no country field today; Asset Identifiers already has one;
   Tempus is not publicly reachable.
2. The lag is reported by `tools/check_consumers_current.py` and
   `check_snapshot_freshness.py --check-upstream`. Both are advisory: a
   release is not blocked because a consumer is behind, because the
   consumers' own gates already check what they vendor.
3. Consumers read `tools/consumers.json`, which lists each one's repository,
   vendored path and fields read.

## Consequences

The next audit can re-run the joins from the consumer list. A consumer that
is six minors behind is visible from here for the first time. Nothing makes
a consumer re-vendor; that stays their decision.
