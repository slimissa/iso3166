# Layers

This registry uses a three-tier Medallion Architecture (RAW → CURATED → AGGREGATED).

A layer may only read from the layer immediately below it. The code structurally enforces this.

## The three layers

| Layer | What it is | Where it lives |
|-------|-----------|----------------|
| **RAW** | The authoritative data. | `iso3166.json` |
| **CURATED** | Deterministic transforms of RAW. | SQL, CSV, TSV, Parquet, CLI output |
| **AGGREGATED** | Rollups and pre-computed metrics derived from CURATED. | `countries_by_region.parquet` |

## RAW — `iso3166.json`

The single source of truth. Its shape is fixed by `schema.json`. Changes to RAW are reviewed by a human and require a first-party source citation in the commit message.

`iso3166.json` is committed. It is not generated at build time. The one-shot importer in `tools/build_initial_data.py` produced it once and is archival; after v1.0.0, the JSON is edited directly.

## CURATED — the derived artifacts

Every CURATED artifact is regenerable from RAW by a single command, producing byte-identical output. CI verifies this: each exporter has a `--check` mode that fails the build if a committed artifact differs from a fresh generation.

**Byte-for-byte validation:** CURATED `--check` modes use strict byte comparison. A library upgrade (e.g., `pyarrow` changing its internal compression bytes) that alters the output file *must* fail the check. The artifact is the source of truth for its content, so any byte change is a change of state. The tool version must be pinned (see `RELEASE_PATTERN.md`).

| Artifact | Generator | `--check` |
|----------|-----------|-----------|
| `iso3166.sql`, `.postgresql.sql`, `.mysql.sql`, `.sqlite.sql` | `tools/export_sql.py` | ✅ |
| `iso3166.csv`, `.excel.csv`, `.european.csv`, `.tsv` | `tools/export_csv.py` | ✅ |
| `iso3166.parquet` | `tools/export_parquet.py` | ✅ |
| CLI output | `tools/iso3166_cli.py` | via `check-cli` CI job |
| Bundled JSON in wrappers | `tools/sync_wrappers.py` | ✅ |
| `tests/cross_language_consistency.json` | `tools/gen_consistency_fixture.py` | ✅ |
| `docs/WITHDRAWN.md` | `tools/gen_withdrawn_doc.py` | ✅ |
| `docs/STATE.md` (also reads the CI workflow, release script and snapshots) | `tools/gen_state_doc.py` | via `tools/check_state_doc.py`, which compares numbers, not bytes |

**Determinism rules:**

- Keys sorted where order doesn't matter; rows sorted by `alpha_2` where order does.
- LF line endings everywhere; enforced by `.gitattributes`.
- UTF-8, no BOM except in `iso3166.excel.csv` where the BOM is what makes Windows Excel open it without an import dialog.
- No timestamps in artifact content. Version and updated date appear only in Parquet footer metadata and in `meta` in the JSON.

## AGGREGATED — `countries_by_region.parquet`

An analytical rollup of ISO 3166 country counts by region and subregion. It reads **only** from the CURATED `iso3166.parquet` layer. It must never read the RAW `iso3166.json`. This rule is structurally enforced by `tests/test_architecture.py`, which uses Python's `ast` module to reject any `json` imports or `.json` string literals in the aggregator script.

**Content-equivalence validation:** AGGREGATED `--check` modes use logical content comparison (`pd.testing.assert_frame_equal`). If a library upgrade changes the physical bytes of the Parquet file but the tabular data remains identical, the check passes. The aggregate is a query over CURATED, not a source of truth. Byte comparison on AGGREGATED files couples them to a library version for no benefit.

| Artifact | Generator | `--check` |
|----------|-----------|-----------|
| `countries_by_region.parquet` | `tools/export_aggregated.py` | ✅ (content-equivalence) |

## Why the layering matters

Every field has exactly one home. A consumer that wants a stable data file reads RAW. A consumer that wants a database table reads CURATED. A consumer that wants an analytical rollup reads AGGREGATED. No layer re-derives what a lower layer already provides.