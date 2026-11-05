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

## Open request: the currency of `GS` (fix-in-3166)

**State.** This registry has `GS` (South Georgia and the South Sandwich
Islands) with `currency_codes = ["FKP"]`; the entry's note cites the ISO
Online Browsing Platform page for `GS` (not checked from here, the page needs
a browser). ISO 4217's registry lists `GBP` for `GS`. ISO 4217's reviewed
allow-list holds both halves of that disagreement, as category
**`fix-in-3166`**, with the reference "ISO 3166 issue not yet filed (owner
action)". Its stated reason: secondary mirrors of the ISO 4217 list show "No
universal currency" for `GS`, so neither side is the standard's own
statement; GBP matches the territory's de facto currency and FKP is the
outlier.

**The other five disagreements** (ISO 4217's allow-list, 2026-11-04) are not
requests to this registry: `BT` INR (parallel currency) and `ZW` USD
(parallel currency) are `allow-list-with-reason`; `XK` EUR is
`allow-list-with-reason` (user-assigned code; `currency_codes` is `null`
here); `CU` CUC and `SV` SVC are `out-of-scope-historical` (demonetized, but
still in ISO 4217's list).

**Decision for v1.12.4.** The value of `GS` is **not changed**. Changing a
currency needs the maintainer's approval, and the choice is not clear:

| Option | Effect |
|--------|--------|
| Change `GS` to `GBP` | Matches the de facto currency and ISO 4217's registry. Departs from the source the entry cites. ISO 4217's two `GS` allow-list entries become stale; its gate fails until it removes them, on its next re-vendor of this registry. |
| Keep `FKP` | ISO 4217 re-classes the pair as `allow-list-with-reason`. No change here. |
| Set `currency_codes` to `null` | Follows "No universal currency". Both sides then differ from ISO 4217's `GBP`. |

**Tracking.** The request is for this registry to change, so the issue
belongs in `slimissa/iso3166`, not in the ISO 4217 repository (the brief for
this release said ISO 4217). **No issue was filed and none is numbered
here:** an issue number cannot be made up. Issue: not filed. When it is
filed, record its number on this line.

Draft text for the issue:

> **`GS` currency: FKP or GBP?** ISO 4217's country-currency allow-list
> (`docs/COUNTRY_CURRENCY_ALLOWLIST.md`, ADR 0010 row GS) lists the `GS`
> pair as `fix-in-3166`: this registry says `FKP`, ISO 4217's registry says
> `GBP`. Secondary mirrors show "No universal currency" for `GS`. Decide
> `GBP`, `FKP` or `null`, record the source, and tell ISO 4217 so it can
> update its allow-list on its next re-vendor.
