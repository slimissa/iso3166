# Layers

This registry is a **RAW** layer. Every downstream artifact is
**CURATED**, derived from it deterministically. There is no AGGREGATED
layer yet; one is planned for v1.7.0 once ISO 4217 also exists in the
same shape.

## The three layers

| Layer | What it is | Where it lives |
|-------|-----------|----------------|
| **RAW** | The authoritative data. Hand-edited or generated once, then frozen. | `iso3166.json` |
| **CURATED** | Deterministic transforms of RAW. Regenerable byte-for-byte. | SQL, CSV, TSV, Parquet, CLI output |
| **AGGREGATED** | Cross-registry joins or rollups. Depends on RAW from more than one registry. | (none yet) |

## RAW — `iso3166.json`

The single source of truth. Its shape is fixed by `schema.json`.
Changes to RAW are reviewed by a human and require a first-party source
citation in the commit message.

`iso3166.json` is committed. It is not generated at build time. The
one-shot importer in `tools/build_initial_data.py` produced it once and
is archival; after v1.0.0, the JSON is edited directly.

## CURATED — the derived artifacts

Every CURATED artifact is regenerable from RAW by a single command,
producing byte-identical output. CI verifies this: each exporter has a
`--check` mode that fails the build if a committed artifact differs
from a fresh generation.

| Artifact | Generator | `--check` |
|----------|-----------|-----------|
| `iso3166.sql`, `.postgresql.sql`, `.mysql.sql`, `.sqlite.sql` | `tools/export_sql.py` | ✅ |
| `iso3166.csv`, `.excel.csv`, `.european.csv`, `.tsv` | `tools/export_csv.py` | ✅ |
| `iso3166.parquet` | `tools/export_parquet.py` | ✅ |
| CLI output | `tools/iso3166_cli.py` | via `check-cli` CI job |
| Bundled JSON in wrappers | `tools/sync_wrappers.py` | ✅ |

Determinism rules:

- Keys sorted where order doesn't matter; rows sorted by `alpha_2`
  where order does.
- LF line endings everywhere; enforced by `.gitattributes`.
- UTF-8, no BOM except in `iso3166.excel.csv` where the BOM is what
  makes Windows Excel open it without an import dialog.
- No timestamps in artifact content. Version and updated date appear
  only in Parquet footer metadata and in `meta` in the JSON.

## AGGREGATED — not yet

An AGGREGATED artifact would be, for example, `currencies_by_region`:
a rollup of ISO 4217 currency counts by ISO 3166 region. It requires
both registries to exist and be joinable on `alpha_2`. Planned for
v1.7.0.

## Why the layering matters

Every field has exactly one home. A consumer that wants a stable data
file reads RAW. A consumer that wants a database table reads CURATED.
A consumer that wants an analytical rollup reads AGGREGATED (when it
exists). No layer re-derives what a lower layer already provides.
