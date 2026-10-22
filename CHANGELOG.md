# Changelog

All notable changes to the ISO 3166 registry are documented in this
file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.8.1] — 2026-10-DD

Pattern documentation parity with ISO 4217 and ISO 10383. No code
or data changes.

### Changed

- `docs/RELEASE_PATTERN.md` adopts A10 (three-file split: rules,
  tool inventory, rewrite receipts) and A11 (CURATED compares bytes;
  AGGREGATED compares logical content, with `assert_frame_equal` as
  the reference implementation).

### Added

- `docs/AUDIT.md` — tool inventory: producers, validators, enrichers.
  Each row records whether the tool runs in CI and in the release gate;
  producers and enrichers also record whether a `--check` mode exists.
- `docs/README-AUDIT-NOTES.md` — receipts for rules 16-19 and A10-A12,
  plus F31 (upstream-drift detection, deferred to v1.9.1).

### Notes

- This release is documentation only. It does not change `iso3166.json`,
  the wrappers, the CLI, or the release script.
- The three-file split matches the shape adopted by ISO 4217 v1.8.4
  and ISO 10383 v1.0.4. Receipts and audit inventory are repo-specific.
- `docs/AUDIT.md` records four gaps and this release does not close
  them: `gen_iso4217_snapshot.py` and `enrich_independent.py` run in
  neither CI nor the release gate; `check_release_claims.py` runs in the
  gate only; `parse_source.py --verify` runs in CI only.
- `tools/export_parquet.py` compares bytes in `--check` but its docstring
  still says it compares logical content. The mismatch is recorded in
  `docs/README-AUDIT-NOTES.md` (A11) and not corrected here.
- F31 (upstream-drift detection): ISO 4217 held their snapshot at
  v1.6.9 through our v1.8.0 because their freshness check is
  calendar-based, not release-based. Deferred to v1.9.1 as their
  audit-closure follow-up.

## [1.8.0] — 2026-10-22

Input contract. The four language wrappers now agree on empty strings,
sentinel numeric codes, and withdrawn-entry behavior. Breaking changes
in all four wrappers; migration notes below and in
`docs/decisions/input-contract.md`.

### BREAKING

- **Python**: `Country.currency_codes`, `calling_codes`, `tlds`,
  `languages`, `borders`, `replaced_by` are now `tuple[str, ...]`
  instead of `list[str]`. Consumers that do `isinstance(x, list)`
  must switch to `isinstance(x, tuple)`. Indexing, iteration, and
  `in` are unchanged. Use `list(x)` where a mutable copy is needed.
- **JavaScript**: `Country` list fields are now deep-frozen. Consumers
  that did `us.currency_codes.push(...)` will throw. Use `.slice()`
  or spread `[...us.currency_codes]` to copy first.
- **Go**: `Active`, `ByAlpha2`, `ByAlpha3`, `ByNumeric` now return
  `Country` (value) instead of `*Country` (pointer). Consumers that
  compare with `== nil` must switch to `country.Alpha2 == ""` or
  check a new `Exists() bool` method. The returned value owns private
  copies of its slices and string pointers, so mutating it can no
  longer corrupt the registry.
- **Rust**: no signature changes; `by_numeric` and `with_numeric` now
  reject `""` and the sentinel `"000"` as documented in the ADR.
- **All wrappers**: `by_numeric("000")` and `by_numeric("0")` now
  return null/nil/None. They previously returned Kosovo (`XK`), whose
  numeric code is the placeholder `"000"`. `by_numeric("")` now
  returns null/nil/None in Python, JavaScript and Rust (it previously
  returned `XK`; Go already returned nil). `search("")` now returns an
  empty list in Python, JavaScript and Rust (it previously returned
  every entry). `region("")` and `subregion("")` now return an empty
  list in Python and JavaScript (they previously returned the entries
  that have no region or sub-region).

### Added

- **DEC-2 ADR** at `docs/decisions/input-contract.md`.
- `with_alpha3`, `with_numeric` (Python/Rust), `withAlpha3`,
  `withNumeric` (JavaScript), `WithAlpha3`, `WithNumeric` (Go) —
  symmetric to the existing `with_alpha2`. They return withdrawn
  entries as well as active ones.
- Go: `Country.Exists()`.
- Python wrapper CLI: `successors` and `predecessors` subcommands,
  a `--active-only` flag on `lookup`, and `--raw version|updated|
  source|schema_version` on `info`.
- Fixture cases: `empty_inputs`, `lookup_numeric_absent`,
  `lookup_alpha2_ambiguous`, `successors`, `predecessors`, each with
  its own `enforced` flag.

### Fixed

- Python wrapper CLI now uses `CountryRegistry` (previously
  reimplemented queries, causing `lookup` and `active()` to
  disagree on withdrawn codes). `lookup` still returns withdrawn
  entries by default; `--active-only` matches `active()`.
- Python wrapper CLI: `--raw` prints one empty line for a missing
  value and for an empty list (an empty list previously printed
  nothing). `search ""` now matches nothing instead of everything.
- `tools/check_cross_language.sh` treats a code that all four
  wrappers report as not found (for example a withdrawn code such as
  `AN`) as agreement instead of a failure.

### Notes

- This is the input contract release. Consumers can now rely on
  empty-string and sentinel-code behavior being identical across
  all four wrappers, enforced by the shared fixture.

## [1.7.4] — 2026-10-21

Release-pipeline robustness and citation completeness.

### Fixed

- `scripts/release.sh` — increased `CI_START_TIMEOUT` from 60s to 180s.
  GitHub Actions regularly takes 90-120s to register a workflow run;
  the 60s limit caused a false-positive partial-release state in v1.7.3.
- `iso3166.json` — added missing `official_name source:` citations for
  11 entries (BR, CN, DE, FR, GB, IN, JP, RU, TW, US, ZA) that had
  official names but no recorded source URL.

### Added

- `.gitignore` — ignores `pages/` so manual ISO OBP harvests are never
  accidentally committed to the repository.
- `docs/RELEASE_PATTERN.md` — rules 18 (CI queueing latency) and 19
  (split releases by decision dependency) codified from the v1.7.2 and
  v1.7.3 recoveries.

### Notes

- All 249 officially-assigned entries now carry an `official_name source:`
  line. `enrich_official_name.py --check` is fully green.
  
## [1.7.3] — 2026-10-20

`independent` corrected for the active set per ISO 3166-1's designation.

### Changed

- **Downstream coordination.** ISO 4217, ISO 10383, and Exchange
  Calendar hold snapshots of this registry. All three should
  re-vendor on this release. The `independent` field is corrected
  for 184 active entries (previously `false` for most sovereign
  states); the schema does not change, so re-vendoring is
  mechanical.
- `independent` re-derived from ISO 3166-1 OBP per-entry lookup
  (the schema's stated source), not CIA Factbook independence dates.
  Overrides: `XK` true, `TW` false, `EU` false. Withdrawn entries
  set per-code (11 true for sovereign states, 14 false for
  dependencies and territories).

### Added

- `tools/enrich_independent.py` — populate `independent` from OBP;
  `--check` compares `iso3166.json` against the companion snapshot
  (exit 0 with a warning while the snapshot is empty).
- `tools/independent_snapshot.json` — audit trail: `{value,
  source_url, extracted_at}` per alpha-2.
- `tests/cross_language_consistency.json` — `independent` case, 20
  entries plus count bounds; all four wrappers assert once the
  snapshot is populated (`enforced`), and skip until then.
- `tools/validate.py` — Northern America business-layer rule
  (warn-only until `--strict-independent` is enabled).

### Fixed

- `docs/RELEASE_PATTERN.md` — rules 16 (don't reset VERSION) and
  17 (don't Ctrl+C during CI wait) from v1.7.2 recovery; preflight
  CI gate documented.

### Notes

- `UK` is exceptionally reserved and has no OBP entry. It is not
  overridden; its `independent` value is left unchanged and the tool
  lists it as unresolved.
- 11 entries (BR, CN, DE, FR, GB, IN, JP, RU, TW, US, ZA) have
  `official_name` populated but no `official_name source:` line.
  Not invented. `TODO(v1.7.4)`.

## [1.7.2] — 2026-10-20

Source citation repair. `enrich_field.py` no longer overwrites prior
fields' source citations; 250 notes reconstructed to carry one
`<field> source:` line per populated field. No schema change; no
consumer-visible data change beyond the `note` field format.

### Fixed

- `tools/enrich_field.py` — `record_source` writes
  `<field> source: <url>` instead of bare `source: <url>`.
  Prior to this release, each enrichment run overwrote the
  previous field's citation. `enrich_withdrawn.py` and
  `enrich_official_name.py` unchanged: the former's `--source`
  covers the whole entry, the latter already uses
  `official_name source:`. 
- CI (`check CLI contract`) — the `--csv US row matches iso3166.csv`
  check compared `tail -1` of the CLI output against `grep '^US,'` of
  `iso3166.csv`. That works only when the `note` field is single-line;
  after this release's migration, US's note carries eight per-field
  citations across eight physical lines, and the check compared the
  first line against the last. Replaced with a Python check that
  parses both sides with `csv.reader` and asserts full-row equality.
- `scripts/release.sh` — preflight now refuses to run if CI on HEAD
  has not completed green. First instance: v1.7.2's initial release
  attempt, when the pre-release commit was still running CI; GitHub
  cancelled it when the release commit pushed, and the release
  inherited the failed check.
  
### Changed

- `iso3166.json` — 250 notes reconstructed. Prior to this release,
  238 entries carried two source lines for up to eight enriched
  fields. The migration reconstructs each field's URL from
  `enrich_field.py`'s `FIELDS[field].source_template.format(code=alpha_2)`
  (a pure function of field and alpha-2), not guessed. Entries
  whose surviving bare URL did not match a populated field's
  template are left untouched and flagged.

### Added

- `tools/migrate_notes_to_per_field.py` — one-shot, idempotent
  migration from the pre-v1.7.2 note format.
- `tests/test_enrich_field_citations.py` — 5 cases.

### Notes

- 11 entries have `official_name` populated but no
  `official_name source:` line: BR, CN, DE, FR, GB, IN, JP, RU,
  TW, US, ZA. The migration does not invent a citation.
  `TODO(v1.7.3)`: re-run `enrich_official_name.py` on these 11.
- The `independent` field correction is deferred to v1.7.3.
  Downstream registries (ISO 4217, ISO 10383, Exchange Calendar)
  continue to hold their snapshots; no re-vendor needed on v1.7.2.

## [1.7.1] — 2026-10-20

Trust the script. Release-pipeline safety fixes; no data or schema changes.

### Fixed

- `requirements-dev.txt` — repaired the corruption committed in
  `e5080fd` (`pyarrow==26.0.0pandas` plus duplicate `pandas` lines).
  CI has been failing on `pip install -r requirements-dev.txt` on
  every push since the corruption landed. Contributors following
  `CONTRIBUTING.md` were blocked.
- `scripts/release.sh` — verify tag message before push, delete local
  tag on any verification failure. Adopted from ISO 4217's A12.
- `scripts/release.sh` — refuse if the target tag already exists
  locally or on origin. Prevents "commit pushed, tag orphaned" after
  a manual recovery.
- `scripts/release.sh` — refuse a release whose staged changes touch
  only paths ignored by `validate.yml`, and exit early if CI does not
  start within 60 seconds.

### Added

- CI: `pip install --dry-run -r requirements-dev.txt` step in all four
  jobs that install dev requirements.
- CI: `pip-audit --strict`, `govulncheck`, and `cargo audit` in wrapper
  jobs, per `RELEASE_PATTERN.md` rule 9 (adopted from ISO 4217 during
  v1.8.4 coordination).

### Notes

- Platform requirement (`Linux-only, GNU tools`) documented in the
  `scripts/release.sh` header as of `6d4d60f`.
- Audit results: `pip-audit` clean; `govulncheck` clean; `cargo audit`
  clean at 12 crate dependencies.
- Downstream coordination: this release does not change the
  `iso3166.json` data or schema. ISO 4217, ISO 10383, and Exchange
  Calendar can re-vendor the same snapshot. The `independent` field
  correction ships in v1.7.2 and will require re-vendoring at that
  time.
  
## [1.7.0] — 2026-10-18

Add AGGREGATED layer and enforce Medallion Architecture.

### Added
- `tools/export_aggregated.py` — groups the CURATED Parquet layer by region and subregion, writing `countries_by_region.parquet`.
- `tests/test_architecture.py` — AST guardrail ensuring the AGGREGATED layer never imports `json` or reads `.json` files.
- `tests/test_export_aggregated.py` — full test suite for the new tool, isolated via `tmp_path`.
- `docs/LAYERS.md` updated to document the three-tier architecture.

### Changed
- `RELEASE_PATTERN.md` updated with the CURATED (byte) vs AGGREGATED (content) check distinction.

## [1.6.9] — 2026-10-16

Bulgaria adopts the euro; ISO 4217 snapshot refreshed.

### Fixed

- BG `currency_codes` updated from `["BGN"]` to `["EUR"]` via
  `enrich_field.py`. ISO 4217 amendment 180 withdrew BGN and
  placed Bulgaria under the euro.
- `tools/iso4217_snapshot.json` refreshed from ISO 4217 v1.8.0.
  BGN is no longer in the active set.

### Notes

- The BG change was present as a working-tree edit during
  v1.6.7 and reverted in v1.6.8 cleanup. It lands here as a
  proper enrichment-tool change with a source citation.

## [1.6.8] — 2026-10-16

Four findings from Exchange Calendar's v2.4.0 review.

### Fixed

- `tools/check_mojibake.py` gains cp1252 and U+FFFD signatures.
  The cp1252 em-dash prefix family — the lead bytes of an 
  em-dash reinterpreted through Windows-1252 — was not caught.
  Neither was the U+FFFD replacement character.
- The first signature's docstring described `e2 80 9a` as a
  corrupted em-dash; it is U+201A, a legitimate character. The
  docstring now names each signature accurately.
- `scripts/release.sh` `check_no_orphan_variables` — the comment
  filter `^\s*#` never matched because `grep -n` prefixed line
  numbers. A `$VAR` inside a comment fired the check.

### Added

- `docs/RELEASE_PATTERN.md` names the `[Unreleased]` convention.
  Presence, not position: both the CI check and `release.sh`
  locate the target heading anywhere in `CHANGELOG.md`.
- `tools/check_snapshot_freshness.py` docstring names the two
  mechanisms: the consumer's cross-reference check and
  `review_by`. Neither replaces the other.

### Changed

- `docs/RELEASE_PATTERN.md` reviewer block records Exchange
  Calendar v2.4.0 as of 2026-10-06.

## [1.6.7] — 2026-09-29

Gate fails fast on first failing check; v1.6.6 claims landed.

### Fixed

- `scripts/release.sh` gate block changed from a brace group to
  a subshell with `set -e`. A brace group on the left of `||`
  disables `set -e`, so every check inside was advisory. v1.6.6
  shipped with two failing claims because the gate reported
  "passed" regardless of the results. The subshell restores
  fail-fast: any failing check stops the release.
- `docs/RELEASE_PATTERN.md` gains operator-hygiene rule 6b: the
  commit message is a claim about the diff, verified by
  `git diff --cached --stat` before every commit. The v1.6.6
  commit claimed two doc additions; only the attribution
  section landed.

### Not in this release

- No changes to registry data, schema, or wrappers.

## [1.6.6] — 2026-09-29

Orphan check fails; manifest precondition; attribution convention.

### Fixed

- `scripts/release.sh` `check_no_orphan_variables` now dies on
  finding, not warns. The check name implies fail-on-finding;
  v1.6.3 shipped the warn shape.
- The orphan-check info line no longer fires unconditionally.

### Added

- `scripts/release.sh` preflight calls
  `check_manifest_has_version`, failing before any version-site
  mutation if `tools/release_claims.json` has no entry for the
  version being released.
- `RELEASE_PATTERN.md` operator-hygiene rule 6b: the commit
  message is a claim about the diff; verify with
  `git diff --cached --stat` before every commit.
- `RELEASE_PATTERN.md` attribution convention: review-history
  entries name the repo each addition came from.

## [1.6.5] — 2026-09-28

Release-claims gate; v1.6.4 doc corrections landed.

### Added

- `tools/check_release_claims.py` — verifies machine-checkable
  claims about a release against the repository state.
- `tools/release_claims.json` — per-version manifest of claims.
- `scripts/release.sh` gate runs the claims check before the
  artifact regeneration. A missing manifest entry or a failing
  claim stops the release.
- `CONTRIBUTING.md` documents the convention.

### Fixed

- The v1.6.4 reviewer block and orphan-preflight convention,
  claimed but not applied, are now in `docs/RELEASE_PATTERN.md`.

## [1.6.4] — 2026-09-28

ISO 10383 as third reviewer; orphan preflight named as convention.

### Added

- `RELEASE_PATTERN.md` review history records the ISO 10383
  exchange.

### Not landed

- The reviewer-block entry and the orphan-preflight convention
  were claimed but not applied in this release. Corrected in
  v1.6.5.

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

[Unreleased]: https://github.com/slimissa/iso3166/compare/v1.7.0...HEAD
[1.7.0]: https://github.com/slimissa/iso3166/releases/tag/v1.7.0
[1.6.9]: https://github.com/slimissa/iso3166/releases/tag/v1.6.9
[1.6.8]: https://github.com/slimissa/iso3166/releases/tag/v1.6.8
[1.6.7]: https://github.com/slimissa/iso3166/releases/tag/v1.6.7
[1.6.6]: https://github.com/slimissa/iso3166/releases/tag/v1.6.6
[1.6.5]: https://github.com/slimissa/iso3166/releases/tag/v1.6.5
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
