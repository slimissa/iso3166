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
- `.github/workflows/validate.yml` — 13 CI jobs.

### Notes

- The initial import was generated from the UN M49 overview export
  cross-checked against ISO 3166-1:2020. UN M49 omits `TW`; it is
  supplied via the exceptions file. Recorded in `docs/PROVENANCE.md`.
- `AI` and `SK` appear in both the active and withdrawn arrays because
  ISO reassigned them. Documented in
  `docs/decisions/withdrawn-codes.md` and in `parse_source.py`.

[Unreleased]: https://github.com/slimissa/iso3166/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/slimissa/iso3166/releases/tag/v1.0.0
