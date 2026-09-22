# Provenance

Every field in `iso3166.json` traces to a first-party source. This
document records those sources, the refresh cadence, the audit
procedure, and the known gaps in v1.0.0.

## Sources

| Field(s) | Source | URL |
|----------|--------|-----|
| `alpha_2`, `alpha_3`, `numeric`, `name`, `independent` | ISO 3166-1:2020 | https://www.iso.org/iso-3166-country-codes.html |
| `region`, `subregion`, `intermediate_region` | UN M49 | https://unstats.un.org/unsd/methodology/m49/ |
| `withdrawal_date`, `replaced_by` | ISO 3166-3:2013 | https://www.iso.org/standard/63545.html |
| `currency_codes` (future) | ISO 4217, via committed snapshot | https://github.com/slimissa/iso4217 |
| `tools/iso4217_snapshot.json` | ISO 4217, regenerated from the sibling registry | https://github.com/slimissa/iso4217 |
| `tlds` (future) | IANA ccTLD registry | https://www.iana.org/domains/root/db |
| `calling_codes` (future) | ITU-T E.164 | https://www.itu.int/ |
| `languages` (future) | ISO 639-3 | https://iso639-3.sil.org/ |

## What is a first-party source

A first-party source is the standards body that defines the code: ISO
for ISO 3166, the UN Statistics Division for M49, IANA for TLDs, the
ITU for calling codes. Anything else — Wikipedia, countrycode.org,
aggregator CSVs, blog posts — is a third-party source and is not
acceptable as the origin of a field.

If a field cannot be traced to a first-party source, it is left
`null`. It is never populated from a third-party source. An empty
field is honest; a wrong field is not.

## Refresh cadence

| Trigger | Action |
|---------|--------|
| ISO publishes an amendment to ISO 3166-1 | Manual update within 30 days; new patch release |
| ISO publishes an amendment to ISO 3166-3 | Manual update within 30 days; new patch release |
| UN M49 publishes an update | Manual cross-check; update `region` fields if changed |
| ISO 4217 publishes a new version | Snapshot refresh (see D5); patch release if `currency_codes` change |
| Quarterly | Audit sweep: re-verify `last_verified` on curated entries; flag any older than 18 months |

There is no automatic sync. Every update is a human-reviewed commit
with the source cited in the commit message and the CHANGELOG entry.

## Audit procedure

To audit a single entry:

1. Look up the `alpha_2` code in the current ISO 3166-1 online
   browsing platform (`https://www.iso.org/obp/ui/#search/code/`).
2. Confirm `alpha_3`, `numeric`, and `name` match.
3. Confirm the `independent` flag against ISO's designation.
4. For non-ISO fields, confirm the source listed above.
5. If `last_verified` is older than 12 months, update it to today's
   date and record the audit in the commit message.

To audit the registry as a whole:

1. `python3 tools/validate.py` — must exit 0.
2. `python3 tools/validate.py --ground-truth` — must confirm all 249
   officially-assigned codes are present.
3. `python3 tools/validate.py --cross-registry` — must confirm every
   `currency_codes` entry exists in the ISO 4217 snapshot.
4. Diff the entry count against the last release:
   `git diff <last-tag> -- iso3166.json | grep -c '^+.*alpha_2'`.
   Any change must be explained in the CHANGELOG.

## Known gaps in v1.0.0

These are fields that are deliberately empty in the first release.
They are populated in later releases, one field at a time.

| Field | Why it's empty | Target release |
|-------|----------------|----------------|
| `official_name` | Requires reading ISO's full official-name column; ~250 rows | v1.1.0 |
| `currency_codes` | Requires ISO 4217 snapshot (D5) plus a country-to-currency mapping | v1.2.0 |
| `calling_codes` | Requires ITU E.164 ingestion | v1.2.0 |
| `tlds` | Requires IANA ccTLD ingestion; note that some territories share a TLD | v1.2.0 |
| `languages` | Requires ISO 639-3 ingestion; note that multilingual countries need careful handling | v1.3.0 |
| `borders` | Requires a first-party source for adjacency; UN M49 does not provide one | v1.3.0 |

## Known limitations in v1.0.0

- **The `independent` flag is only populated for a small set of countries.**
  The full population is a Phase 1.5 enrichment. Until then, `independent`
  defaults to `false` for entries not in `tools/initial_exceptions.json`.
  This is not a data error; it is an incomplete population, and consumers
  should not rely on the flag being correct until v1.1.0.
- **The withdrawn list is a representative sample, not the full ISO 3166-3
  set.** The mechanism is proven; the population is completed in v1.1.0.
- **User-assigned code ranges (`AA`, `QM–QZ`, `XA–XZ`, `ZZ`) are not
  enumerated.** Only specific user-assigned codes in production use
  (`XK` for Kosovo) are entries. The ranges are documented here, not in
  the JSON.
- **Exceptionally-reserved codes are limited to `UK` and `EU`.** Others
  exist; they are added on discovery.

## Discrepancy log

Any discrepancy between sources is recorded here, with the resolution.

| Date | Discrepancy | Resolution |
|------|-------------|------------|
| 2026-09-22 | UN M49 omits `TW` (Taiwan). ISO 3166-1 assigns it. | `TW` supplied manually via `tools/initial_exceptions.json`, sourced from the ISO 3166-1 official list, with the omission noted in the entry's `note` field. |

