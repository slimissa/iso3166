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

[Unreleased]: https://github.com/slimissa/iso3166/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/slimissa/iso3166/releases/tag/v1.1.0
[1.0.1]: https://github.com/slimissa/iso3166/releases/tag/v1.0.1
[1.0.0]: https://github.com/slimissa/iso3166/releases/tag/v1.0.0
