# Tool audit

This file is the tool inventory for the registry: which tools exist,
whether each has a `--check` mode, and whether it runs in CI
(`.github/workflows/validate.yml`) and in the release gate
(`scripts/release.sh`). It is the counterpart to two other files:

- [`RELEASE_PATTERN.md`](./RELEASE_PATTERN.md) holds the rules.
- [`README-AUDIT-NOTES.md`](./README-AUDIT-NOTES.md) holds the receipts:
  the specific failure behind each rule and each gap listed here.

This file changes when a tool is added, removed, or wired into (or out
of) CI or the gate. State as of v1.8.0.

## Category A — Producers

Tools that write committed artifacts.

| Tool | --check | CI | Gate |
|------|---------|----|------|
| `export_sql.py` | yes | yes | yes |
| `export_csv.py` | yes | yes | yes |
| `export_parquet.py` | yes | yes | yes |
| `export_aggregated.py` | yes | yes | yes |
| `sync_wrappers.py` | yes | yes | yes |
| `gen_consistency_fixture.py` | yes | yes | yes |
| `gen_withdrawn_doc.py` | yes | yes | yes |
| `build_introduced_snapshot.py` | yes | yes | yes |
| `build_club_snapshots.py` | yes | yes | yes |
| `gen_iso4217_snapshot.py` | yes | no (needs the source file) | yes (`--check --source "$CURRENCY_SOURCE"`) |

## Category B — Validators

Tools that verify data.

| Tool | CI | Gate |
|------|----|------|
| `validate.py` | yes | yes |
| `check_version_consistency.py` | yes | yes |
| `check_mojibake.py` | yes | yes |
| `check_snapshot_freshness.py` | yes | yes |
| `check_consumers_current.py` | no | no (advisory, network) |
| `check_introduced.py` | via `validate.py` | yes |
| `check_introduced_meta.py` | yes | yes |
| `check_release_claims.py` | no | yes |
| `check_cross_language.sh` | yes | yes |
| `parse_source.py --verify` | yes | yes |

## Category C — Enrichment

Tools that modify the registry.

| Tool | --check | CI | Gate |
|------|---------|----|------|
| `enrich_field.py` | yes | yes | yes |
| `enrich_official_name.py` | yes | yes | yes |
| `enrich_withdrawn.py` | yes | yes | yes |
| `enrich_independent.py` | yes | yes | no |

## Notes

Rows with a `no` are the gaps. After v1.12.9 four rows remain:
`check_consumers_current.py` (advisory, network, deliberately outside
both); `gen_iso4217_snapshot.py` (gate only; it needs a source file);
`enrich_independent.py` (CI only); `check_release_claims.py` (gate
only).

- **`gen_iso4217_snapshot.py`.** It has no `--check` mode without
  `--source`: it compares the snapshot with a registry file from
  `slimissa/iso4217`. The gate reads that file from `$CURRENCY_SOURCE`
  (default `iso4217.json`, a gitignored local copy) and step 0 refuses
  to start without it. CI has no such file, so CI runs
  `check_iso4217_snapshot.py` (well-formedness) instead.

- **`parse_source.py`.** The gate and CI run `--verify` against
  `iso3166.json` (it checks the registry's code sets against the frozen
  sets exactly). CI also runs `--audit`; `--audit` is not in the gate.
- **`enrich_field.py`.** CI (`check-fields`) and the gate run `--check`
  for all seven of its fields: `borders`, `calling_codes`,
  `currency_codes`, `intermediate_region`, `languages`, `subregion`,
  `tlds`.
- **`check_cross_language.sh`.** CI passes six codes (`US GB JP TW XK
  UK`); the gate passes three (`US GB JP`).
- **`validate.py`.** CI adds `--verbose`; the gate does not.

Tools that are not in any category above:

- `check_iso4217_snapshot.py` runs in CI and, from v1.12.3, in the gate
  (after `check_registry_freshness.py`). It checks that
  `iso4217_snapshot.json` is well-formed.
- `iso3166_cli.py` is the command-line interface. CI exercises it in
  the CLI-contract step; it is not a gate step.
- `tests/test_release_force.sh` is a shell test, not a tool. It runs
  `release.sh --force` in a throwaway repository, in CI (`check-force-test`)
  and in the gate.
- `audit_languages.py` is advisory, writes nothing, and runs in
  neither CI nor the gate.
- `build_initial_data.py` and `migrate_notes_to_per_field.py` are
  one-shot tools (the first-cut import and the v1.7.2 citation
  migration). They run in neither.
