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
| `gen_iso4217_snapshot.py` | yes | no | no |

## Category B — Validators

Tools that verify data.

| Tool | CI | Gate |
|------|----|------|
| `validate.py` | yes | yes |
| `check_version_consistency.py` | yes | yes |
| `check_mojibake.py` | yes | yes |
| `check_snapshot_freshness.py` | yes | yes |
| `check_release_claims.py` | no | yes |
| `check_cross_language.sh` | yes | yes |
| `parse_source.py --verify` | yes | no |

## Category C — Enrichment

Tools that modify the registry.

| Tool | --check | CI | Gate |
|------|---------|----|------|
| `enrich_field.py` | yes | yes | yes |
| `enrich_official_name.py` | yes | yes | yes |
| `enrich_withdrawn.py` | yes | yes | yes |
| `enrich_independent.py` | yes | no | no |

## Notes

Rows with a `no` are the gaps. Four are visible in the tables:
`gen_iso4217_snapshot.py` and `enrich_independent.py` are checked
neither in CI nor in the gate; `check_release_claims.py` runs in the
gate only; `parse_source.py --verify` runs in CI only.

- **`parse_source.py`.** `release.sh` does not call it at all. CI runs
  both `--verify` and `--audit`.
- **`enrich_field.py`.** CI and the gate run `--check` for five of its
  seven fields: `borders`, `calling_codes`, `currency_codes`,
  `languages`, `tlds`. `subregion` and `intermediate_region` have no
  `--check` invocation in either place.
- **`check_cross_language.sh`.** CI passes six codes (`US GB JP TW XK
  UK`); the gate passes three (`US GB JP`).
- **`validate.py`.** CI adds `--verbose`; the gate does not.

Tools that are not in any category above:

- `check_iso4217_snapshot.py` runs in CI. It checks that
  `iso4217_snapshot.json` is well-formed. It is not run by the gate.
- `iso3166_cli.py` is the command-line interface. CI exercises it in
  the CLI-contract step; it is not a gate step.
- `audit_languages.py` is advisory, writes nothing, and runs in
  neither CI nor the gate.
- `build_initial_data.py` and `migrate_notes_to_per_field.py` are
  one-shot tools (the first-cut import and the v1.7.2 citation
  migration). They run in neither.
