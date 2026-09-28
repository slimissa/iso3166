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

## [1.6.4] — 2026-09-28

ISO 10383 as third reviewer; orphan preflight named as convention.

### Added

- `RELEASE_PATTERN.md` reviewer block adds ISO 10383
  (`slimissa/iso10383`).
- `RELEASE_PATTERN.md` operator-hygiene rule 4 names the
  orphan-variable preflight as a shared convention, citing ISO
  3166's `check_no_orphan_variables` as the reference.
- `RELEASE_PATTERN.md` review history records the ISO 10383
  exchange.

### Not in this release

- No code change. v1.6.4 is documentation only.

## [1.6.3] — 2026-09-28

Wrapper tests for absent optional fields; orphan-variable preflight.

### Added

- Four wrapper tests reading the `optional_absent` fixture vector:
  Python, Go, Rust, JavaScript. Each asserts that a null
  `official_name` returns null and an empty `borders` list
  returns an empty list.
- `tools/gen_consistency_fixture.py` generates the
  `optional_absent` vector from `iso3166.json`.
- `scripts/release.sh` preflight warns on orphan variables — a
  heredoc referencing a renamed variable only fails at expansion
  time. The v1.6.2 report failure was this class.
- `docs/RELEASE_PATTERN.md` names the post-tag partial-release
  state (v1.6.2 is the reference example).

### Not in this release

- Reviewer-block entry for ISO 10383. Deferred to v1.6.4.

## [1.6.2] — 2026-09-27

RELEASE_PATTERN.md reconciliation; fixture vector for absent
optional fields.

### Added

- `RELEASE_PATTERN.md` gains the tag-immutability exception for
  tags created on a red commit by a pipeline defect. Cites ISO
  10383's ADR 0005.
- `RELEASE_PATTERN.md` adopts three ISO 4217 v1.7.0 additions:
  the registry-vs-snapshot section, the pipeline-exit-code
  operator-hygiene rule, and the mojibake implementation note.
- `tests/cross_language_consistency.json` gains an
  `optional_absent` vector: `EU` with `official_name: null`,
  `AG` with `borders: []`. Tests that read the vector are
  deferred to v1.6.3.

### Changed

- `RELEASE_PATTERN.md` implementations list adds ISO 10383
  (eight version sites, one polled workflow).
- Header adopts ISO 4217's "Adopted — reviewed by" status form.
- `tools/check_snapshot_freshness.py` docstring names the `meta`
  block requirement and the registry-vs-snapshot split.

### Not in this release

- Wrapper tests that assert the `optional_absent` contract.
  Deferred to v1.6.3; one wrapper per commit, each verified.

### Fixed

- Nothing behavioural. v1.6.2 is documentation and fixture.

## [1.6.1] — 2026-09-27

Sibling metadata for freshness check; poll-every-workflow fix.

### Added

- `tools/check_snapshot_freshness.py` reads a sibling file
  (`tools/<stem>.meta.json`) before falling back to the snapshot's
  own `meta` block. This is the vendored-snapshot shape: the
  snapshot stays byte-for-byte, the cadence metadata lives
  alongside. Output marks sibling-sourced entries with
  `(sibling)`.
- `CONTRIBUTING.md` gains an "Inbound notifications" section
  naming what ISO 3166 expects to hear from ISO 4217 and
  Exchange Calendar. Previously only the outbound direction was
  documented.
- `RELEASE_PATTERN.md` invariant 6 names a reference
  implementation for the poll-every-workflow shape and for the
  workflow-coverage check.

### Fixed

- `scripts/release.sh` poll loop now enumerates every run for the
  pushed SHA and asserts each is `completed success`. The previous
  shape filtered to `validate.yml` and used `head -1`, silently
  missing any second per-push workflow. Latent on ISO 3166 (one
  workflow); the same bug was active on ISO 4217 through v1.6.1.
- `scripts/release.sh` gains `check_workflows_covered`, which
  fails at preflight if any non-schedule workflow in
  `.github/workflows/` isn't in the declared poll list.

### Changed

- The workflow list is a `POLLED_WORKFLOWS` array instead of a
  single `WORKFLOW` constant.

## [1.6.0] — 2026-09-27

Version axes contract; release pattern document.

### Added

- `tools/version_axes.json` — declarative contract describing which
  files carry the registry version, and how to extract it. Adopted
  from iso4217/axes.json. One axis, ten sites, seven extractors.
  Not yet read by `check_version_consistency.py`; the refactor
  waits for ISO 10383's version.
- `docs/RELEASE_PATTERN.md` — generalizes the three stable
  `release.sh` implementations (ISO 4217, ISO 3166, Exchange
  Calendar) into a single pattern document. Eight essential
  invariants, two shapes of step 4, wrapper-copy test question,
  tag immutability and partial-release recovery, operator hygiene,
  mojibake self-trigger rule, vendored-snapshot `review_by` shape,
  snapshot drift.

### Changed

- Nothing. v1.6.0 is additive.

## [1.5.4] — 2026-09-27

Snapshot freshness check; CI scans docs.

### Added

- `tools/check_snapshot_freshness.py`. Reads every
  `tools/*_snapshot.json` and verifies `meta.review_by` is not in
  the past. Three states: ISO date (fail if past), the literal
  string `"closed"` (never checked), and null (warn, don't fail).
- `check-snapshot-freshness` CI job.
- `meta.review_by` and `meta.refresh_cadence` fields on all six
  snapshot files. `iso4217_snapshot.json` carries a 90-day cadence;
  the language, calling-code, and TLD snapshots carry 365 days;
  the two M49 snapshots are marked `"closed"`.

### Changed

- `scripts/release.sh` gate runs the freshness check after the
  mojibake scan.
- `validate.yml` no longer filters `docs/**` and `**/*.md` from
  the push trigger. Docs-only commits now run CI. The mojibake and
  freshness checks are sub-second, and the docs are exactly where
  mojibake lives.

## [1.5.3] — 2026-09-26

Adopt the mojibake scanner from ISO 4217.

### Added

- `tools/check_mojibake.py`, forked from iso4217 v1.6.1. Detects
  UTF-8 text that has been round-tripped through Latin-1, which
  corrupts accented characters in country names. Covers the three
  literal signatures (em-dash, check mark, box-drawing) plus a
  range regex for every accented Latin-1 character.
- `check-mojibake` CI job. Sub-second, blocking.
- `CONTRIBUTING.md` rule: any doc that shows corruption by example
  will trigger the check that detects it. Describe in prose, or
  mark the file with the mojibake skip marker.

### Changed

- `scripts/release.sh` gate now runs the mojibake scan against the
  release's own CHANGELOG and docstrings before committing.

## [1.5.2] — 2026-09-23

Use `repr` for scalar field display in enrich_field.py.

### Fixed

- `tools/enrich_field.py` renders scalar field values with `repr`
  in `--dry-run` and batch mode output. A scalar now prints as
  `'South America'` and a one-element list as `['South America']`,
  making the two visually distinct. The written value was already
  correct; only the display changed.

## [1.5.1] — 2026-09-23

Enrichment tooling covers the M49 fields; the intermediate snapshot
is no longer a stub.

### Added

- `tools/enrich_field.py` supports `--field subregion` and
  `--field intermediate_region`. Both fields are populated in
  `iso3166.json` from the v1.0.0 UN M49 import but were not
  reachable through the enrichment tool until this release.

### Changed

- `tools/m49_intermediate_region_snapshot.json` populated with the
  seven UN M49 intermediate regions used by the registry:
  Caribbean, Central America, Eastern Africa, Middle Africa, South
  America, Southern Africa, Western Africa. Replaces the
  `<verify from UN source>` placeholder.

### Fixed

- `tools/enrich_field.py` treats `subregion` and
  `intermediate_region` as scalars. The prior version wrote lists
  where the schema requires strings, and printed scalar values
  character-by-character in `--list-all`.
- The `--dry-run` and batch summaries print the value that was
  actually written, not the input list. No-op updates no longer
  emit a spurious `(was: ...)` line.

### Not in this release

- Neither `subregion` nor `intermediate_region` is added to the
  `check-fields` CI gate. AQ, TW, and the three exceptionals have
  null `subregion` by design; 147 active entries have null
  `intermediate_region` by design.

## [1.5.0] — 2026-09-23


Fixture support and documentation for `intermediate_region`; version
bump.

### Added

- `tools/gen_consistency_fixture.py` emits `intermediate_region` in
  lookup cases. Wrapper suites assert agreement where the fixture
  exercises the field.
- `docs/ENRICHMENT.md` gains an `intermediate_region` section.
- `docs/decisions/v1.5.0-scope.md` records the reconnaissance result:
  `intermediate_region` was already fully populated from the v1.0.0
  UN M49 import.

### Changed

- Version bump to 1.5.0 across the eight version sites.

### Not in this release

- `tools/enrich_field.py` does not support `--field subregion` or
  `--field intermediate_region`. Both fields are populated from the
  initial M49 import and are not tool-managed. Tracked for a future
  release.
- `tools/m49_intermediate_region_snapshot.json` remains a stub.
  The field's data is validated by the schema pattern check, not by
  a snapshot cross-reference.

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

[Unreleased]: https://github.com/slimissa/iso3166/compare/v1.6.4...HEAD
[1.6.4]: https://github.com/slimissa/iso3166/releases/tag/v1.6.4
[1.6.3]: https://github.com/slimissa/iso3166/releases/tag/v1.6.3
[1.6.2]: https://github.com/slimissa/iso3166/releases/tag/v1.6.2
[1.6.1]: https://github.com/slimissa/iso3166/releases/tag/v1.6.1
[1.6.0]: https://github.com/slimissa/iso3166/releases/tag/v1.6.0
[1.5.4]: https://github.com/slimissa/iso3166/releases/tag/v1.5.4
[1.5.3]: https://github.com/slimissa/iso3166/releases/tag/v1.5.3
[1.5.2]: https://github.com/slimissa/iso3166/releases/tag/v1.5.2
[1.5.1]: https://github.com/slimissa/iso3166/releases/tag/v1.5.1
[1.5.0]: https://github.com/slimissa/iso3166/releases/tag/v1.5.0
[1.4.0]: https://github.com/slimissa/iso3166/releases/tag/v1.4.0
[1.3.0]: https://github.com/slimissa/iso3166/releases/tag/v1.3.0
[1.2.0]: https://github.com/slimissa/iso3166/releases/tag/v1.2.0
[1.1.0]: https://github.com/slimissa/iso3166/releases/tag/v1.1.0
[1.0.1]: https://github.com/slimissa/iso3166/releases/tag/v1.0.1
[1.0.0]: https://github.com/slimissa/iso3166/releases/tag/v1.0.0
