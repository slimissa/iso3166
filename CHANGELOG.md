# Changelog

All notable changes to the ISO 3166 registry are documented in this
file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- v1.1.0: enrich `official_name` for all 249 officially-assigned
  entries; complete the ISO 3166-3 withdrawn set.
- v1.2.0: populate `currency_codes`, `calling_codes`, `tlds`; publish
  wrappers to PyPI, npm, crates.io.
- v1.3.0: populate `languages` and `borders`.

## [1.5.0] — 2026-09-23

Languages second-source pass; `intermediate_region` populated.

### Added

- `intermediate_region` populated for entries where UN M49 defines
  one. Most countries stop at `subregion`; their
  `intermediate_region` remains null.
- `tools/m49_intermediate_region_snapshot.json` — the UN M49
  intermediate-region list.
- `docs/decisions/v1.5.0-scope.md` — scope decision for this
  release.

### Changed

- `tools/enrich_field.py` supports `--field intermediate_region`.
- Fixture includes the field; wrapper suites assert agreement where
  the fixture exercises it.

## [1.4.0] — 2026-09-23

Subregion on withdrawn entries; languages audit.

### Added

- `subregion` populated on 18 of the 25 withdrawn entries from the UN
  M49 classification. The remaining 7 spanned multiple subregions or
  were uninhabited; each carries a note explaining the null.
- `tools/m49_subregion_snapshot.json` — 22 UN M49 subregion names.
- `tools/audit_languages.py` — classifies each entry's languages list.
- `docs/decisions/languages-audit-2026-09.md` — audit of the
  `languages` field.

### Changed

- `tools/enrich_field.py` supports `subregion`. The field is a
  scalar; it is the first that applies to withdrawn entries.
  `find_active` now searches both arrays.
- `languages` corrected for `MT`, `IE`, `CY`, `PR` where the Factbook
  listed only the official language.
- `CONTRIBUTING.md` gains a patch-script rule and a tag-after-CI
  rule, both lessons from v1.3.0.

### Fixed

- The Rust test's `LookupField` struct declared `languages` and
  `borders` but never read them; clippy with `-D warnings` failed the
  v1.3.0 tag. Assertions added.

## [1.3.0] — 2026-09-23

Populate `languages` and `borders`; tighten the ITU snapshot.

### Added

- `languages` populated for all 249 officially-assigned entries.
  ISO 639-3 codes sourced from the CIA World Factbook.
- `borders` populated for all 249 officially-assigned entries.
  Sourced from the CIA World Factbook `Land boundaries` section.
- `tools/iso639_3_snapshot.json` — ISO 639-3 language codes.
- `docs/decisions/languages-borders-sources.md` — ADR expanding the
  first-party source rule to include government statistical
  services.

### Changed

- `tools/itu_calling_code_snapshot.json` reduced from 294 to 204
  codes. The extras were valid ITU assignments that do not map to
  an ISO 3166-1 entry.
- `tools/enrich_field.py` supports `languages` and `borders`.
- `tools/validate.py` business layer enforces border symmetry.
- The `check-fields` CI job now runs six blocking checks.

### Deferred

- `subregion` on withdrawn entries. Seven of the 25 withdrawn codes
  span multiple UN M49 subregions or are uninhabited; the field would
  carry `null` for those. Deferred to v1.4.0.

## [1.2.0] — 2026-09-23

Populate four data fields for every officially-assigned ISO 3166-1
entry.

### Added

- `official_name` populated for all 249 officially-assigned entries.
  Sourced per-entry from the ISO 3166-1 Online Browsing Platform.
- `currency_codes` populated for all 249 entries. Sourced from ISO
  3166-1 OBP country pages, cross-checked against ISO 4217.
- `calling_codes` populated for all 249 entries. Sourced from ITU-T
  E.164.
- `tlds` populated for all 249 entries. Sourced from the IANA ccTLD
  registry.
- `tools/enrich_field.py` — unified enrichment for the three list
  fields. `--field` selector; single-entry and TSV batch modes;
  `--check` gate.
- `tools/iana_tld_snapshot.json` — IANA ccTLDs.
- `tools/itu_calling_code_snapshot.json` — ITU-T E.164 codes.
- `docs/ENRICHMENT.md` — per-field source and edge-case reference.

### Changed

- `tools/validate.py` cross-reference layer now checks `tlds` against
  the IANA snapshot and `calling_codes` against the ITU snapshot.
- The `check-official-name` CI job becomes `check-fields`, running
  four blocking `--check` invocations.
- `tests/cross_language_consistency.json` now carries `lookup_fields`
  cases covering the new fields, including the `.uk` exception for GB
  and the dual-currency case for PA. All four wrapper test suites
  assert agreement.

### Fixed

- The `check-official-name` gate added in v1.0.1 is now enforced
  against complete data; the `continue-on-error: true` advisory is
  removed.

## [1.1.0] — 2026-09-23

Complete the ISO 3166-3 withdrawn set and add the tooling around it.

### Added

- `tools/enrich_withdrawn.py` — add or update withdrawn entries,
  parallel to `enrich_official_name.py`. Enforces status, date, and
  successor consistency; records the source URL in `note`.
- `iso3166 successors CODE` — follow `replaced_by` transitively to
  terminal successors.
- `iso3166 predecessors CODE` — the inverse query, computed from the
  data.
- `iso3166 list --withdrawn-since DATE --withdrawn-before DATE` —
  date filters over the withdrawn set.
- `docs/WITHDRAWN.md` — generated table of every withdrawn code and
  its successor chain.
- `tools/gen_withdrawn_doc.py` — generator with `--check`.

### Changed

- The `withdrawn` array is now complete: 25 entries, one for every
  code ISO 3166-3:2013 lists.
- `tests/cross_language_consistency.json` now carries withdrawn-lookup
  cases. All four wrapper test suites assert agreement on them.

### Fixed

- `tools/validate.py` now rejects a cyclical `replaced_by` graph and
  a `withdrawal_date` in the future.
- `iso3166 successors --raw` and `iso3166 predecessors --raw` accept
  the flag without a field name.

## [1.0.1] — 2026-09-22

Data completion and one behavioral change to the validator.

### Added

- `official_name` populated for all 249 officially-assigned ISO 3166-1
  entries. Sourced per-entry from the ISO 3166-1 Online Browsing
  Platform; each entry's `note` field records the source URL.
- `tools/enrich_official_name.py` — entry tool and completeness check.
  `--check` fails if any officially-assigned entry is missing an
  official name.

### Changed

- `tools/validate.py`: the ISO 4217 snapshot check in the
  cross-reference layer is now blocking. A missing
  `tools/iso4217_snapshot.json` produces a FAIL rather than a WARN.
  A new `--allow-missing-snapshot` flag restores the previous
  behavior for forks and downstream repositories. Recorded in
  decision D5.

### Fixed

- `wrappers/rust/Cargo.lock` records the crate at its actual version.

## [1.0.0] — 2026-09-22

Foundation. Registry data, schema, validator, exports, CLI, four
language wrappers, and CI.

### Added

- `iso3166.json` — 252 active entries (249 officially-assigned,
  1 user-assigned, 2 exceptionally-reserved) and 15 withdrawn entries
  from ISO 3166-3.
- `schema.json` — JSON Schema draft-07 contract.
- `VERSION`, `CHANGELOG.md`, `LICENSE`, `README.md`.
- `docs/PROVENANCE.md` — sources, refresh cadence, audit procedure,
  known gaps, discrepancy log.
- `docs/LAYERS.md` — RAW / CURATED / AGGREGATED model.
- `docs/decisions/v1.0.0-decisions.md` — D1–D8.
- `docs/decisions/withdrawn-codes.md` — ADR for ISO 3166-3 successors.
- `tools/build_initial_data.py` — one-shot importer (archival).
- `tools/initial_exceptions.json` — hand-maintained overrides.
- `tools/parse_source.py` — frozen ground-truth code sets, with
  `--audit`, `--verify`, and `--bootstrap` modes.
- `tools/validate.py` — six-layer validator.
- `tools/export_sql.py` — four SQL dialects.
- `tools/export_csv.py` — four delimited variants.
- `tools/export_parquet.py` — typed Parquet.
- `tools/sync_wrappers.py` — bundled JSON sync.
- `tools/gen_consistency_fixture.py` — cross-language fixture generator.
- `tools/check_version_consistency.py` — five-way version check.
- `tools/iso3166_cli.py` — CLI with eight subcommands, five output modes.
- `tools/check_cross_language.sh` — four-wrapper agreement check.
- `bin/iso3166` — shell wrapper.
- `tests/cross_language_consistency.json` — shared wrapper contract.
- `wrappers/python/` — Python wrapper + `iso3166` console script.
- `wrappers/javascript/` — JavaScript wrapper.
- `wrappers/go/` — Go wrapper.
- `wrappers/rust/` — Rust wrapper.
- Nine distribution artifacts at the repo root: four SQL files, four
  CSV/TSV files, one Parquet file.
- `.github/workflows/validate.yml` — 14 CI jobs.

### Notes

- The initial import was generated from the UN M49 overview export
  cross-checked against ISO 3166-1:2020. UN M49 omits `TW`; it is
  supplied via the exceptions file. Recorded in `docs/PROVENANCE.md`.
- `AI` and `SK` appear in both the active and withdrawn arrays because
  ISO reassigned them. Documented in
  `docs/decisions/withdrawn-codes.md` and in `parse_source.py`.

[Unreleased]: https://github.com/slimissa/iso3166/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/slimissa/iso3166/releases/tag/v1.5.0
[1.4.0]: https://github.com/slimissa/iso3166/releases/tag/v1.4.0
[1.3.0]: https://github.com/slimissa/iso3166/releases/tag/v1.3.0
[1.2.0]: https://github.com/slimissa/iso3166/releases/tag/v1.2.0
[1.1.0]: https://github.com/slimissa/iso3166/releases/tag/v1.1.0
[1.0.1]: https://github.com/slimissa/iso3166/releases/tag/v1.0.1
[1.0.0]: https://github.com/slimissa/iso3166/releases/tag/v1.0.0
