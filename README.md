# ISO 3166 Country Registry

**A canonical, versioned, machine-readable registry of ISO 3166 country codes: 252 active entries and 25 withdrawn ones, each with 24 fields (20 on withdrawn entries), and four date-scoped club-membership arrays (EU, EEA, eurozone, customs union).**

One JSON file is the source of truth. Everything else (SQL, CSV, TSV, Parquet, one aggregated table, four language wrappers, a command-line tool, five temporal snapshots) is regenerated from it or checked against it, and re-verified on every push.

[![Validate](https://github.com/slimissa/iso3166/actions/workflows/validate.yml/badge.svg)](https://github.com/slimissa/iso3166/actions/workflows/validate.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Schema](https://img.shields.io/badge/schema-1.0.0-green.svg)](./schema.json)
[![Registry](https://img.shields.io/badge/registry-1.12.2-orange.svg)](./iso3166.json)

---

## Contents

1. [At a glance](#1-at-a-glance)
2. [Why this exists](#2-why-this-exists)
3. [Where to start](#3-where-to-start)
4. [Quick start](#4-quick-start)
5. [The data model: three layers](#5-the-data-model-three-layers)
6. [The registry file](#6-the-registry-file)
7. [The temporal identity layer](#7-the-temporal-identity-layer)
8. [Flat exports: SQL, CSV, TSV, Parquet](#8-flat-exports-sql-csv-tsv-parquet)
9. [Countries and aggregated tables](#9-countries-and-aggregated-tables)
10. [Worked example: a strategy across four dates](#10-worked-example-a-strategy-across-four-dates)
11. [Command-line interface](#11-command-line-interface)
12. [Language wrappers](#12-language-wrappers)
13. [Validation](#13-validation)
14. [Continuous integration](#14-continuous-integration)
15. [Release pipeline](#15-release-pipeline)
16. [Versioning](#16-versioning)
17. [Project structure](#17-project-structure)
18. [Documentation index](#18-documentation-index)
19. [Contributing](#19-contributing)
20. [Known limitations](#20-known-limitations)
21. [FAQ](#21-faq)
22. [Consumed by](#22-consumed-by)
23. [License and author](#23-license-and-author)
24. [What's next](#24-whats-next)

---

## 1. At a glance

| | |
|---|---|
| **Active entries** | 252: 249 `officially-assigned`, 2 `exceptionally-reserved` (`EU`, `UK`), 1 `user-assigned` (`XK`) |
| **Withdrawn entries** | 25 (`AN`, `BU`, `CS`, `DD`, `SU`, `YU` and 19 more; see [`docs/WITHDRAWN.md`](./docs/WITHDRAWN.md)) |
| **Total** | 277. `AI` and `SK` are in both arrays: an active code reused for a different entity than the withdrawn one (Anguilla and Slovakia, against the withdrawn `AI` and `SK`; see [Section 6](#a-dual-status-code)). |
| **Fields per active entry** | 24 (twenty on withdrawn entries: the four club arrays are active-only). 8 are enrichable, 1 is temporal, 4 are club arrays. |
| **Derived queries** | 16: 12 in the Python `derived.py` mixin and 4 dated club queries in `clubs.py`, specified in [`docs/QUERIES.md`](./docs/QUERIES.md) |
| **Surfaces** | 5: four language wrappers (Python, JavaScript, Rust, Go) and one command line with 25 subcommands |
| **Club memberships** | 4: `eu_membership`, `eea_membership`, `eurozone_membership`, `customs_union`, as inclusive `{from, to}` ranges |
| **Snapshots** | 5 temporal snapshots (`introduced`, EU, EEA, eurozone, customs union); 12 `*_snapshot.json` files in `tools/` in all |
| **Flat exports** | 9: 4 SQL, 4 CSV/TSV, 1 Parquet. One more Parquet file is the aggregated layer. |
| **Gate checks** | 30 checks run in sequence in the release gate; CI runs 23 jobs; the test suites hold 271 tests ([Section 13](#13-validation)) |
| **Cross-language cases** | 129 derived-query cases in one shared fixture, plus the lookup and field cases around them |
| **Version** | 1.12.2 (schema 1.0.0) |
| **Version sites** | 10 files carry the version; `scripts/release.sh` bumps 8 of them ([Section 16](#16-versioning)) |
| **Dependencies** | The JSON needs none. The Python, JavaScript and Go wrappers need none; the Rust crate needs `serde` and `serde_json`. Tool time: `jsonschema`, `pyarrow==26.0.0`, `pandas`, `pytest`. |

If a number on this page disagrees with the tree, the tree wins; `tools/check_docs_match_tree.py` checks the counts, versions and lists it can.

---

## 2. Why this exists

Every system that touches international finance, trade, shipping or identity keeps its own country list, and the lists drift. Some use alpha-2, some alpha-3, some the numeric code. Some include territories, some merge them, some include Kosovo and some do not.

**Country codes are a join dimension.** Every fact table needs them and none should own them. But identity is not enough. A fact table that carries only `alpha_2` also needs three more facts about it:

- **Time.** When did the code exist? `is_active_on("DE", "1960-01-01")` is `false`; `is_active_on("XK", "2000-01-01")` is `null`, because the source is silent and the registry says so instead of guessing.
- **Currency.** What does the country use? The registry carries the *current* currencies of an entry and bounds the answer to the entry's lifetime. It does not carry historical currencies (see [Known limitations](#20-known-limitations)).
- **Clubs.** Was the country in the EU, the EEA, the eurozone or the EU customs union on a given day? `is_eu_member_at("GB", "2010-01-01")` is `true`; `is_eu("GB")` is `false`.

This registry provides all of these as first-class, date-scoped facts in one versioned, schema-validated file. The answers are tri-state (`true`, `false`, `null`) where the source can be silent (`is_active_on`) and binary where the source is a complete range list (the four club queries). The JSON is the contract; the SQL, CSV, Parquet, wrapper and CLI forms are ways to consume it without writing a parser.

Not every field is first-party. Most enrichable fields come from ISO, the UN Statistics Division, IANA, the ITU, ISO 639-3 or the CIA World Factbook, but `introduced` and the four club arrays are sourced from Wikipedia under a documented, explicit exception ([`docs/decisions/introduced-field.md`](./docs/decisions/introduced-field.md), [`docs/decisions/club-memberships.md`](./docs/decisions/club-memberships.md)). [Section 7](#7-the-temporal-identity-layer) says exactly which, and when each snapshot is next reviewed.

---

## 3. Where to start

| If you are... | Start with |
|---------------|------------|
| A programmer who wants a library | [Language wrappers](#12-language-wrappers) |
| A database engineer | [`iso3166.postgresql.sql`](./iso3166.postgresql.sql) and the other dialects; see [Flat exports](#8-flat-exports-sql-csv-tsv-parquet) |
| An analyst in Excel, Sheets, pandas or DuckDB | [`iso3166.csv`](./iso3166.csv) or [`iso3166.parquet`](./iso3166.parquet), then the [worked example](#10-worked-example-a-strategy-across-four-dates) |
| A shell user | [Command-line interface](#11-command-line-interface) |
| Asking "was X in the EU in 2010?" | [The temporal identity layer](#7-the-temporal-identity-layer): `is_eu_member_at` |
| Asking "what currency did Y use in 1990?" | `currency_at`, and read its limits first: it returns the *current* currency, not the historical one ([Section 7](#7-the-temporal-identity-layer)) |
| Evaluating whether to trust the data | [`docs/PROVENANCE.md`](./docs/PROVENANCE.md) and [Known limitations](#20-known-limitations) |
| Contributing a correction | [Contributing](#19-contributing) and [`CONTRIBUTING.md`](./CONTRIBUTING.md) |
| Building a registry with the same discipline | [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) |

---

## 4. Quick start

### Direct download

```bash
curl -O https://raw.githubusercontent.com/slimissa/iso3166/main/iso3166.json
```

For anything reproducible, pin a release tag instead of `main`. The versions are listed in [`CHANGELOG.md`](./CHANGELOG.md).

### Python (3.9+)

```bash
pip install -e wrappers/python
```

```python
from iso3166 import CountryRegistry

reg = CountryRegistry()
us = reg.active("US")
print(us.alpha_3, us.name)                    # USA United States of America
print(us.currency_codes, us.calling_codes)    # ('USD',) ('1',)
print(reg.by_numeric("840").alpha_2)          # US

# The temporal layer
print(reg.is_eu_member_at("GB", "2010-01-01"))   # True   (the UK left on 2020-01-31)
print(reg.is_eu("GB"))                           # False  (current status only)
print(reg.is_active_on("XK", "2000-01-01"))      # None   (source silent)
```

### JavaScript (Node 18+)

```bash
npm install ./wrappers/javascript
```

```javascript
const { CountryRegistry } = require("iso3166-registry");

const reg = new CountryRegistry();
console.log(reg.active("US").alpha_3);            // USA
console.log(reg.isEuMemberAt("GB", "2010-01-01")); // true
```

### Rust (edition 2021)

```toml
[dependencies]
iso3166-registry = { path = "wrappers/rust" }
```

```rust
use iso3166_registry::CountryRegistry;

let reg = CountryRegistry::load().unwrap();
if let Some(us) = reg.active("US") {
    println!("{} {} {:?}", us.alpha_3, us.name, us.currency_codes);
}
println!("{}", reg.is_eu_member_at("GB", "2010-01-01")); // true
```

### Go (1.21+)

The module path is `github.com/slimissa/iso3166-go`; its source is [`wrappers/go`](./wrappers/go). From a clone, point a `replace` directive at it.

```go
import iso3166 "github.com/slimissa/iso3166-go"

reg, _ := iso3166.Load()
if us := reg.Active("US"); us != nil {
    fmt.Println(us.Alpha3, us.Name, us.CurrencyCodes)
}
fmt.Println(reg.IsEUMemberAt("GB", "2010-01-01")) // true
```

### Any SQL database

```bash
psql -f iso3166.postgresql.sql              # PostgreSQL 12+
mysql < iso3166.mysql.sql                   # MySQL 8+ / MariaDB 10.4+
sqlite3 registry.db < iso3166.sqlite.sql    # SQLite 3.37+
psql -f iso3166.sql                         # ANSI SQL-92 (portable)
```

```sql
-- Club cells are one string per club: 'from:to|from:to', an empty end means "still a member".
SELECT alpha_2, eu_membership FROM countries WHERE alpha_2 = 'GB';
-- GB | 1973-01-01:2020-01-31
```

### pandas and DuckDB

```python
import pandas as pd
df = pd.read_parquet("iso3166.parquet")
print(df.shape)                                       # (277, 24)
print(df.loc[df.alpha_2 == "GB", "eu_membership"].iloc[0])   # 1973-01-01:2020-01-31
```

### Command line

```bash
bin/iso3166 is-eu DE                          # true
bin/iso3166 is-eu-member-at GB 2010-01-01     # true
bin/iso3166 successors YU --raw alpha_2       # CS, ME, RS (one per line)
```

---

## 5. The data model: three layers

The repository follows a three-layer model, documented in [`docs/LAYERS.md`](./docs/LAYERS.md). The layering rule is **a layer reads only the layer immediately below it**, and for the one place where it matters most, a test enforces it.

| Layer | What lives here | Rule |
|-------|-----------------|------|
| **RAW** | [`iso3166.json`](./iso3166.json) | The authoritative data, committed. Changes are reviewed by a human and cite a source. After v1.0.0 the JSON is edited directly or through an enrichment tool, never regenerated from scratch. |
| **CURATED** | 9 flat exports; 4 wrapper copies of the JSON; the cross-language fixture; `docs/WITHDRAWN.md`; `docs/STATE.md` | Regenerated from RAW by deterministic tools. Every generator has a `--check` mode that fails the build on a stale artifact. |
| **AGGREGATED** | [`countries_by_region.parquet`](./countries_by_region.parquet) | An analytical rollup. Reads only the CURATED `iso3166.parquet`, never the RAW JSON. |

**Where the rule is enforced by a tool, not by convention.** `tests/test_architecture.py` parses the syntax tree of `tools/export_aggregated.py` with Python's `ast` module and fails on any `import json`, any `from json import ...`, and any string literal that ends in `.json`. The aggregator cannot reach the RAW layer without that test failing. The enforcement covers this one edge: the other edges (for example, the exporters reading RAW and the wrappers embedding it) are enforced by the `--check` modes, which catch drift but not the choice of input.

**Two comparison semantics, on purpose.** CURATED `--check` modes compare bytes, so a library upgrade that changes the output bytes fails the check and the tool version must be pinned (`requirements-dev.txt` pins `pyarrow==26.0.0`). The AGGREGATED `--check` compares logical content with `pd.testing.assert_frame_equal`, because an aggregate is a query over CURATED, not a source of truth. [`docs/LAYERS.md`](./docs/LAYERS.md) gives the reasoning.

| Artifact | Layer | Generator | `--check` |
|----------|-------|-----------|-----------|
| `iso3166.sql`, `.postgresql.sql`, `.mysql.sql`, `.sqlite.sql` | CURATED | `tools/export_sql.py` | yes |
| `iso3166.csv`, `.excel.csv`, `.european.csv`, `.tsv` | CURATED | `tools/export_csv.py` | yes |
| `iso3166.parquet` | CURATED | `tools/export_parquet.py` | yes |
| `wrappers/{python/iso3166,javascript,go,rust}/iso3166.json` | CURATED | `tools/sync_wrappers.py` | yes |
| `tests/cross_language_consistency.json` | CURATED | `tools/gen_consistency_fixture.py` | yes |
| `docs/WITHDRAWN.md` | CURATED | `tools/gen_withdrawn_doc.py` | yes |
| `docs/STATE.md` | CURATED | `tools/gen_state_doc.py` | `tools/check_state_doc.py` (numbers, not bytes) |
| `countries_by_region.parquet` | AGGREGATED | `tools/export_aggregated.py` | yes (logical content) |

The release script regenerates in layer order: SQL, CSV, Parquet, aggregated, wrapper copies, fixture, `WITHDRAWN.md`, `STATE.md`.

---

## 6. The registry file

[`iso3166.json`](./iso3166.json) has two top-level keys, `meta` and `countries`. `countries` holds two arrays, `active` (252) and `withdrawn` (25).

```json
{
  "meta": {
    "count_active": 252,
    "count_withdrawn": 25,
    "schema_version": "1.0.0",
    "source": "ISO 3166-1:2020 (cross-checked against UN M49)",
    "updated": "2026-10-31",
    "version": "1.12.2"
  },
  "countries": { "active": [ "..." ], "withdrawn": [ "..." ] }
}
```

### An active entry

`US`, with the multi-line `note` shortened here to its first two lines (every populated field adds one `<field> source:` line to it):

```json
{
  "alpha_2": "US",
  "alpha_3": "USA",
  "numeric": "840",
  "name": "United States of America",
  "official_name": "United States of America",
  "status": "officially-assigned",
  "independent": true,
  "region": "Americas",
  "subregion": "Northern America",
  "intermediate_region": null,
  "currency_codes": ["USD"],
  "calling_codes": ["1"],
  "tlds": [".us"],
  "languages": ["eng"],
  "borders": ["CA", "MX"],
  "introduced": "1974-09-15",
  "eu_membership": [],
  "eea_membership": [],
  "eurozone_membership": [],
  "customs_union": [],
  "withdrawal_date": null,
  "replaced_by": null,
  "last_verified": "2026-10-21",
  "note": "currency_codes source: https://www.iso.org/obp/ui/#iso:code:3166:US\ncalling_codes source: https://www.itu.int/oth/T02020000E8/en\n..."
}
```

### A club member

`GB`, which was in the EU from 1973 to 2020 and in the EEA until the end of 2020:

```json
{
  "alpha_2": "GB",
  "eu_membership": [{"from": "1973-01-01", "to": "2020-01-31"}],
  "eea_membership": [{"from": "1994-01-01", "to": "2020-12-31"}]
}
```

(Other keys omitted.) A range's `to` is the last day, inclusive; `null` means the country is still a member; `[]` means it never was.

### A withdrawn entry

`DD`, East Germany, withdrawn 1990-10-03 and replaced by `DE`. A withdrawn entry has 20 fields, and most enrichable fields are `null`:

```json
{
  "alpha_2": "DD",
  "alpha_3": "DDR",
  "numeric": "278",
  "name": "East Germany",
  "status": "withdrawn",
  "independent": true,
  "official_name": null,
  "region": null,
  "subregion": "Western Europe",
  "intermediate_region": null,
  "currency_codes": null,
  "calling_codes": null,
  "tlds": null,
  "languages": null,
  "borders": null,
  "introduced": null,
  "withdrawal_date": "1990-10-03",
  "replaced_by": ["DE"],
  "last_verified": "2026-09-23",
  "note": "source: https://unstats.un.org/unsd/methodology/m49/"
}
```

### A dual-status code

Two codes are in both arrays. **`SK`** is active Slovakia (`officially-assigned`, `introduced: null`, quarantined) and withdrawn Sikkim (`alpha_3: SKM`, `numeric: 000`, withdrawn 1975-05-16, `replaced_by: ["IN"]`). **`AI`** is active Anguilla and a withdrawn entry for the French Territory of the Afars and Issas. A consumer must therefore key on `(alpha_2, status)`: the SQL `countries` table does, and the derived queries that take a code alone let the active entry win ([`docs/QUERIES.md`](./docs/QUERIES.md)). The aggregated table counts both entries.

### Field reference

Every active entry carries twenty-four fields; every withdrawn entry carries twenty. The counts below are over the 252 active entries. A list field counts as populated when it is non-empty.

| Field | Type | Null | Empty `[]` | Meaning |
|-------|------|-----:|-----------:|---------|
| `alpha_2` | string | 0 | | ISO 3166-1 alpha-2 code; `^[A-Z]{2}$` |
| `alpha_3` | string | 0 | | ISO 3166-1 alpha-3 code |
| `numeric` | string | 0 | | Three-digit numeric code as a string, leading zeros preserved (`"020"`). Named `numeric_code` in the SQL and Parquet exports. |
| `name` | string | 0 | | Short English name |
| `status` | string | 0 | | See [Enums](#enums) |
| `independent` | boolean | 0 | | `true` for 195 of 252 entries |
| `official_name` | string or null | 3 | | Populated for every `officially-assigned` entry (249 of 249); null for `EU`, `UK`, `XK` |
| `region` | string or null | 5 | | UN M49 region; null for `AQ`, `EU`, `TW`, `UK`, `XK` |
| `subregion` | string or null | 5 | | UN M49 subregion; null for the same five |
| `intermediate_region` | string or null | 147 | | Defined by M49 only under Sub-Saharan Africa and Latin America and the Caribbean (105 populated) |
| `currency_codes` | list or null | 3 | 1 | Current ISO 4217 codes; null for `EU`, `UK`, `XK`, empty for `AQ` |
| `calling_codes` | list or null | 3 | 0 | ITU country calling codes, digits only |
| `tlds` | list or null | 3 | 5 | IANA ccTLDs, with the leading dot |
| `languages` | list or null | 3 | 1 | ISO 639-3 codes |
| `borders` | list or null | 2 | 88 | Land neighbours as alpha-2 codes; `[]` for islands and enclaves |
| `introduced` | date or null | 76 | | The date the ISO 3166-1 standard added the code ([Section 7](#7-the-temporal-identity-layer)) |
| `eu_membership` | list of ranges | 0 | 224 | 28 entries have at least one range |
| `eea_membership` | list of ranges | 0 | 221 | 31 entries |
| `eurozone_membership` | list of ranges | 0 | 231 | 21 entries |
| `customs_union` | list of ranges | 0 | 220 | 32 entries |
| `withdrawal_date` | date or null | 252 | | Null on every active entry; set on withdrawn entries |
| `replaced_by` | list or null | 252 | | Null on every active entry; set on withdrawn entries |
| `last_verified` | date | 0 | | Last date a human or tool verified the entry |
| `note` | string | 0 | | One `<field> source:` line per populated field |

### Coverage

| Group | Count | Notes |
|-------|------:|-------|
| Active | 252 | |
| `officially-assigned` | 249 | |
| `exceptionally-reserved` | 2 | `EU`, `UK` |
| `user-assigned` | 1 | `XK` |
| Withdrawn | 25 | Every one carries `withdrawal_date`; none has `introduced` |
| Europe / Asia / Americas / Africa / Oceania | 51 / 50 / 57 / 60 / 29 | Active entries by `region`; 5 have none |
| `currency_codes` populated | 248 of 252 | Missing `AQ`, `EU`, `UK`, `XK` |
| `calling_codes` populated | 249 of 252 | Missing `EU`, `UK`, `XK` |
| `tlds` populated | 244 of 252 | Missing `BL`, `BQ`, `EH`, `EU`, `MF`, `UK`, `UM`, `XK` |
| `languages` populated | 248 of 252 | Missing `AQ`, `EU`, `UK`, `XK` |
| `borders` populated | 162 of 252 | |
| `subregion` populated | 247 of 252 | Missing `AQ`, `EU`, `TW`, `UK`, `XK` |

[`docs/STATE.md`](./docs/STATE.md) is the generated version of this table, and `tools/check_state_doc.py` verifies it against the tree.

### Enums

**`status`** is the one closed vocabulary on identity. Active entries use three of its four values; `withdrawn` is for the other array.

| Value | Meaning | Count |
|-------|---------|------:|
| `officially-assigned` | In ISO 3166-1 | 249 |
| `exceptionally-reserved` | Reserved by the ISO 3166/MA at request (`EU`, `UK`) | 2 |
| `user-assigned` | Free for users (`XK`) | 1 |
| `withdrawn` | No longer in the standard | 25 |

**`region`** is one of `Africa`, `Americas`, `Asia`, `Europe`, `Oceania`, or `null`. The registry has no `classification` or `relationship` enum; those belong to the ISO 4217 registry.

Design decisions behind these fields are recorded in [`docs/decisions/v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md) (with [amendments](./docs/decisions/v1.9.2-amendments.md)), [`withdrawn-codes.md`](./docs/decisions/withdrawn-codes.md), [`introduced-field.md`](./docs/decisions/introduced-field.md) and [`club-memberships.md`](./docs/decisions/club-memberships.md).

---

## 7. The temporal identity layer

Three facts change over time for a country code: whether the code existed, which club the country was in, and what currency it used. This section is what the registry answers, how, and where it stops.

### `introduced`: when the code existed

`introduced` is the date the ISO 3166-1 standard added the code. It is not the date a country became independent or adopted a currency. Of 252 active entries, **176 are dated and 76 are null**.

| `introduced` | Count | Meaning |
|--------------|------:|---------|
| Dated from the 1974 edition | 161 | The code was in the first ISO 3166-1 list, dated `1974-09-15` |
| Dated from the data | 15 | A later edition's date, taken from the source table |
| Null, **quarantined** | 27 | The candidate date is not credible; see below |
| Null, **source silent** | 46 | The source table gives no date |
| Null, **not officially assigned** | 3 | `EU`, `UK`, `XK` are not in ISO 3166-1 |

The 25 withdrawn entries have no `introduced` either; 23 of them are recorded in `meta.null_reasons` as "start date not sourced".

**The 27 quarantined codes.** The builder refuses a date it cannot defend rather than writing it. A code is quarantined when the Wikipedia table's date is a *change newsletter*, not an assignment date, or when the code cannot have been in the 1974 edition. Each is null in the registry and carries its reason in `tools/introduced_snapshot.json`, `meta.null_reasons`.

| Reason | Count | Codes |
|--------|------:|-------|
| Successor of a withdrawn code in the tree [confirmed] | 6 | `BJ` (of `DY`), `DJ` (of `AI`), `KI` (of `CT`), `MM` (of `BU`), `VU` (of `NH`), `ZW` (of `RH`) |
| Post-Soviet state; cannot be in the 1974 edition [likely] | 14 | `AM`, `AZ`, `BY`, `EE`, `GE`, `KG`, `KZ`, `LT`, `LV`, `RU`, `TJ`, `TM`, `UA`, `UZ` |
| Successor state of Czechoslovakia or Yugoslavia [likely] | 3 | `CZ`, `SI`, `SK` |
| The source date is a change newsletter [likely] | 4 | `BA`, `ER`, `MD`, `SH` |

### `is_active_on(code, date)`: tri-state

Was `code` an assigned ISO 3166-1 code on `date`? The answer is `true`, `false` or `null`, and `null` means "the source is silent", never "no".

- Active entry, `introduced` set: `date >= introduced`.
- Active entry, `introduced` null: `null`. (`XK`, `BJ`, and the other 74.)
- Withdrawn entry: `false` after `withdrawal_date`; `true` from 1974-01-01 up to and including it; `null` before 1974, because ISO 3166 did not exist.
- Malformed date or unknown code: `false`.

```text
is_active_on("DE", "1990-01-01")  -> true     introduced 1974-09-15
is_active_on("DE", "1960-01-01")  -> false    before introduced
is_active_on("BJ", "2000-01-01")  -> null     quarantined
is_active_on("DD", "1990-10-03")  -> true     the withdrawal date is inclusive
is_active_on("DD", "1990-10-04")  -> false    after withdrawal_date
```

On the CLI the three answers are exit 0 (`true`), 1 (`false`) and 4 (`unknown`).

### `currency_at(code, date)`: lifetime-bounded, not historical

`currency_at` is exact about *when the code exists* and approximate about *what the currency was*. Before `introduced`, after `withdrawal_date`, and wherever `introduced` is null, the answer is `None`. Otherwise it returns a copy of the entry's **current** `currency_codes`. The registry stores no currency history, so:

```text
currency_at("DE", "1990-01-01") -> ["EUR"]   Germany then used the Deutsche Mark
currency_at("DD", "1990-01-01") -> ["EUR"]   a withdrawn entry returns its successor's current currency
currency_at("DE", "1960-01-01") -> None      before introduced
```

A caller who needs the currency actually in force on a past date must not rely on this query. A historical-currency source is a separate release ([Known limitations](#20-known-limitations)).

### The four club queries: date-scoped, binary

`is_eu_member_at`, `is_eea_member_at`, `is_eurozone_member_at` and `is_in_customs_union_at` take a code and a date and answer `true` or `false`. They are never null: the membership arrays are complete range lists, and `[]` is a definite "never a member". Ranges are inclusive on both ends.

```text
is_eu_member_at("GB", "2020-01-31")        -> true    the last day of membership
is_eu_member_at("GB", "2020-02-01")        -> false
is_eurozone_member_at("GR", "2000-01-01")  -> false   Greece adopted the euro on 2001-01-01
```

`is_eu`, `is_eea` and `is_eurozone` are **current-status aliases**: they read the same arrays at today's date. `is_eu("GB")` is `false` because the UK is not a member today, not because it never was.

The start of each club in the data: the EU from `1958-01-01` (the founding six), the EU customs union from `1968-07-01`, the EEA from `1994-01-01`, the eurozone from `1999-01-01`. The 1974 boundary applies to `introduced` and `is_active_on`, not to the club arrays.

### The five snapshots

Five committed snapshots feed the temporal fields. Each has a sibling `.meta.json`, and `tools/check_snapshot_freshness.py` fails the release gate when a `review_by` date passes.

| Snapshot | Feeds | Source | Vendored | `review_by` |
|----------|-------|--------|----------|-------------|
| `introduced_snapshot.json` | `introduced` | Wikipedia: ISO 3166-1 Changes (edition and newsletter table), permalinked `oldid=1258392980` | 2026-10-28 | 2027-10-28 |
| `eu_membership_snapshot.json` | `eu_membership` | Wikipedia: Member state of the European Union | 2026-10-29 | 2027-10-29 |
| `eea_membership_snapshot.json` | `eea_membership` | Wikipedia: European Economic Area; provisional dates from EFTA and the EEA Legal Texts | 2026-10-29 | 2027-10-29 |
| `eurozone_membership_snapshot.json` | `eurozone_membership` | Wikipedia: Euro area, cross-checked against the Council of the EU timeline | 2026-10-29 | 2027-10-29 |
| `customs_union_snapshot.json` | `customs_union` | Wikipedia: European Union Customs Union | 2026-10-29 | 2027-10-29 |

Wikipedia is an explicit, documented exception to the registry's first-party rule: ISO 3166 does not publish club membership or per-code introduction dates, so no first-party source exists. The four club snapshots cite the page title URL, not an `oldid` permalink; the ADR records this as a known deviation to fix at the first review.

### EEA: provisional application is modeled

Twelve countries applied the EEA Agreement provisionally before it formally entered into force for them. The EEA snapshot records both ranges and `tools/enrich_club_memberships.py` unions them into `eea_membership`, so `is_eea_member_at` answers for the day the country actually applied the agreement.

| Provisional application | Countries |
|-------------------------|-----------|
| 2004-05-01 to 2005-12-05 | `CY`, `CZ`, `EE`, `HU`, `LT`, `LV`, `MT`, `PL`, `SI`, `SK` |
| 2007-08-01 to 2011-11-08 | `BG`, `RO` |

`HR` has formal dates only: its provisional application is not dated in the sources read. The UK's EEA end date is `2020-12-31`; the source's state table says 31 January 2020, its prose says 31 December 2020, and the snapshot records the prose date and flags it as likely.

### Known gaps

- No historical currencies; `currency_at` returns the current currency for the lifetime-bounded answer.
- `introduced` is null for 76 active entries and all 25 withdrawn ones; `is_active_on` answers `null` for them.
- Nothing before 1974 can be dated for the identity layer. The club arrays reach back to 1958.
- The club ranges come from Wikipedia and are reviewed once a year.

---

## 8. Flat exports: SQL, CSV, TSV, Parquet

All nine flat exports are CURATED. They are regenerated from `iso3166.json`, committed, and compared in CI by each generator's `--check` mode.

| Artifact | Columns | Rows | Generator |
|----------|--------:|-----:|-----------|
| `iso3166.sql`, `.postgresql.sql`, `.mysql.sql`, `.sqlite.sql` | 23 (`countries`) + 2 (`country_currencies`) | 277 + 249 | `tools/export_sql.py` |
| `iso3166.csv`, `.excel.csv`, `.european.csv`, `.tsv` | 24 | 277 | `tools/export_csv.py` |
| `iso3166.parquet` | 24 | 277 | `tools/export_parquet.py` |

Rows are active and withdrawn entries together (252 + 25). Filter on `status` (`<> 'withdrawn'`) for active only.

**Serialization of lists and clubs.** A list field is one string with items joined by `|` (`ES|FR`, `AT|BE|CH|CZ|DK|FR|LU|NL|PL`). A club array is one string of `from:to` ranges joined by `|`: `1973-01-01:2020-01-31` is one range, and an empty end (`2004-05-01:`) means still a member. A country that was never a member, and every withdrawn entry, has an empty cell (CSV, TSV) or `NULL` (SQL, Parquet). The logic is in `tools/club_format.py`.

### SQL

Four self-contained files, one per dialect, each with the same two tables.

| File | Target |
|------|--------|
| [`iso3166.sql`](./iso3166.sql) | ANSI SQL-92, portable default |
| [`iso3166.postgresql.sql`](./iso3166.postgresql.sql) | PostgreSQL 12+ |
| [`iso3166.mysql.sql`](./iso3166.mysql.sql) | MySQL 8+ / MariaDB 10.4+ |
| [`iso3166.sqlite.sql`](./iso3166.sqlite.sql) | SQLite 3.37+ |

`countries` has 23 columns and the primary key `(alpha_2, status)`, which is what lets `AI` and `SK` appear twice. `country_currencies` is a join table of `(country_alpha_2, currency_code)`, 249 rows. `currency_codes` is therefore not a column of `countries`. The four club arrays are `VARCHAR(80)` strings in the format above. Loading `iso3166.sqlite.sql` into SQLite yields 277 and 249 rows.

```sql
SELECT alpha_2, name FROM countries WHERE status <> 'withdrawn' AND region = 'Europe';
SELECT country_alpha_2 FROM country_currencies WHERE currency_code = 'EUR';
```

### CSV and TSV

Four files, one per audience. LF line endings, a header row, 24 columns, 277 data rows.

| File | Audience | Quirk |
|------|----------|-------|
| [`iso3166.csv`](./iso3166.csv) | Every CSV parser | RFC 4180, comma-delimited |
| [`iso3166.excel.csv`](./iso3166.excel.csv) | Excel on Windows | UTF-8 BOM; the only file with one |
| [`iso3166.european.csv`](./iso3166.european.csv) | European Excel locales | Semicolon-delimited |
| [`iso3166.tsv`](./iso3166.tsv) | Terminal, clipboard, Sheets | Tab-separated |

Columns, in order: `alpha_2`, `alpha_3`, `numeric`, `name`, `status`, `independent`, `official_name`, `region`, `subregion`, `intermediate_region`, `currency_codes`, `calling_codes`, `tlds`, `languages`, `borders`, `note`, `last_verified`, `withdrawal_date`, `replaced_by`, `introduced`, `eu_membership`, `eea_membership`, `eurozone_membership`, `customs_union`.

Read `numeric` and `calling_codes` as text: `020` is Andorra, and a spreadsheet will turn it into `20`. Note that `note` contains newlines inside a quoted field.

### Parquet

[`iso3166.parquet`](./iso3166.parquet): columnar, typed, 24 columns, 277 rows. Columns follow the CSV, except that `numeric` is named `numeric_code`.

- `currency_codes`, `calling_codes`, `tlds`, `languages`, `borders` and `replaced_by` are native lists of strings (for example `list<string>` for `currency_codes`), not pipe-joined.
- `independent` is a native boolean.
- The four club columns are **strings**, in the `from:to|from:to` format. Parquet could hold structs; the registry serializes the clubs so that the CSV, SQL and Parquet cells are identical.
- Null is a real null.

**Footer metadata.** The file carries `iso3166.version`, `iso3166.updated`, `iso3166.schema_version` and `iso3166.generator`. A consumer who receives only the `.parquet` file can tell which registry version produced it, and the footer version is one of the version sites.

```python
import pyarrow.parquet as pq
print(pq.read_table("iso3166.parquet").schema.metadata[b"iso3166.version"])   # b'1.12.2'
```

### Comparison semantics and the build pin

`export_sql.py --check`, `export_csv.py --check` and `export_parquet.py --check` regenerate in memory and compare with the committed file; `export_aggregated.py --check` compares logical content. Parquet bytes depend on the `pyarrow` version, so [`requirements-dev.txt`](./requirements-dev.txt) pins `pyarrow==26.0.0`. There is no `constraints.txt` in this repository, and no test checks that every CI install line is pinned (see [Known limitations](#20-known-limitations)).

---

## 9. Countries and aggregated tables

The registry has one grain: one row per `(alpha_2, status)` entry. The only table at another grain is the AGGREGATED layer.

### `countries_by_region.parquet`

**AGGREGATED.** How many entries sit in each region and subregion, and how many are independent? One row per `(region, subregion)`. 30 rows. Generated from the CURATED `iso3166.parquet` by `tools/export_aggregated.py`.

| Column | Type | Notes |
|--------|------|-------|
| `region` | string, nullable | UN M49 region; null for 13 of the 30 rows |
| `subregion` | string, nullable | Null for one row |
| `country_count` | int | Entries in the group |
| `independent_count` | int | Entries with `independent = true` |

Four properties to know before you join to it:

- **It counts all 277 entries, active and withdrawn.** `country_count` sums to 277 and `independent_count` to 206, not to the 252 and 195 of the active entries. For active-only counts, query `iso3166.parquet`.
- **Null does not equal null.** A withdrawn entry has no `region`, so the 25 withdrawn entries and the 5 active entries without a region (`AQ`, `EU`, `TW`, `UK`, `XK`) fall into rows with a null `region`. Join on region with `IS NOT DISTINCT FROM`, or an ordinary `=` join silently drops them.
- **The join key is the pair.** `Melanesia` and `Micronesia` appear under Oceania and, for withdrawn entries, with a null region; `Southern Europe` appears under Europe and under a null region. Join on `(region, subregion)`.
- **`AI` and `SK` are counted twice**, once as the active entry and once as the withdrawn one.

The file carries no `iso3166.*` footer metadata, and is not a version site.

---

## 10. Worked example: a strategy across four dates

A strategy desk holds positions keyed by `alpha_2` and needs to know, as of four dates, which countries were in the EU and the eurozone. The script below reads only `iso3166.parquet` with DuckDB, parses the club cells, and asks the same questions the wrapper queries answer. It was run against v1.12.1 with DuckDB 2.0.0 and PyArrow 26.0.0; the Python wrapper gives the same counts.

```bash
pip install duckdb pyarrow
```

Save the script and run it from the repository root:

```python
import duckdb

con = duckdb.connect()
con.execute("CREATE VIEW c AS SELECT * FROM 'iso3166.parquet' WHERE status <> 'withdrawn'")

# A club cell is one string: 'from:to|from:to'; an empty end means "still a member".
con.execute("""
CREATE MACRO member_at(cell, d) AS (
    coalesce(list_bool_or(list_transform(
        string_split(cell, '|'),
        lambda r: split_part(r, ':', 1) <= d
         AND (split_part(r, ':', 2) = '' OR split_part(r, ':', 2) >= d)
    )), false)
)
""")

print("Q1-Q3: who was in the EU, and in the eurozone, on four dates?")
for d in ("1990-01-01", "2000-01-01", "2010-01-01", "2023-01-01"):
    eu, ez = con.execute(
        "SELECT count(*) FILTER (WHERE member_at(eu_membership, ?)),"
        "       count(*) FILTER (WHERE member_at(eurozone_membership, ?)) FROM c",
        [d, d],
    ).fetchone()
    print(f"  {d}  EU={eu:2d}  eurozone={ez:2d}")

print("\nQ4: the current alias against the dated query, for GB")
for d in ("2010-01-01", "2020-01-31", "2020-02-01"):
    (n,) = con.execute(
        "SELECT count(*) FROM c WHERE alpha_2='GB' AND member_at(eu_membership, ?)", [d]
    ).fetchone()
    print(f"  GB in the EU on {d}: {bool(n)}")
(cur,) = con.execute(
    "SELECT count(*) FROM c WHERE alpha_2='GB' AND member_at(eu_membership, '2026-10-31')"
).fetchone()
print(f"  GB in the EU today:  {bool(cur)}   (is_eu('GB') is the same current-status answer)")

print("\nQ5: which countries list EUR as a currency, and how many are in the eurozone today?")
eur, ez_now, only = con.execute("""
SELECT count(*) FILTER (WHERE list_contains(currency_codes, 'EUR')),
       count(*) FILTER (WHERE list_contains(currency_codes, 'EUR')
                          AND member_at(eurozone_membership, '2026-10-31')),
       string_agg(alpha_2, ' ' ORDER BY alpha_2) FILTER (WHERE list_contains(currency_codes, 'EUR')
                          AND NOT member_at(eurozone_membership, '2026-10-31'))
FROM c
""").fetchone()
print(f"  EUR in currency_codes: {eur}; eurozone members: {ez_now}; EUR without membership: {eur - ez_now}")
print(f"  those {eur - ez_now}: {only}")
```

Output:

```text
Q1-Q3: who was in the EU, and in the eurozone, on four dates?
  1990-01-01  EU=12  eurozone= 0
  2000-01-01  EU=15  eurozone=11
  2010-01-01  EU=27  eurozone=16
  2023-01-01  EU=27  eurozone=20

Q4: the current alias against the dated query, for GB
  GB in the EU on 2010-01-01: True
  GB in the EU on 2020-01-31: True
  GB in the EU on 2020-02-01: False
  GB in the EU today:  False   (is_eu('GB') is the same current-status answer)

Q5: which countries list EUR as a currency, and how many are in the eurozone today?
  EUR in currency_codes: 36; eurozone members: 21; EUR without membership: 15
  those 15: AD AX BL GF GP MC ME MF MQ PM RE SM TF VA YT
```

What the numbers say:

- **The EU was 12, then 15, then 27, then 27 again.** 2010 and 2023 have the same count with different members: the UK is in 2010, Croatia (2013) is in 2023.
- **A current alias would have answered all four dates the same.** `is_eu` over the 252 entries gives 27 today. A fact table dated 1990 joined on `is_eu` mislabels 15 countries that were not yet members and the UK, which was.
- **"Uses the euro" is not "is in the eurozone".** 36 entries list `EUR`; 21 are members. The other 15 are microstates and overseas territories (`AD`, `MC`, `SM`, `VA`, `ME`, the French departments and collectivities) that use the euro without membership. The registry keeps both facts.

---

## 11. Command-line interface

The command is `iso3166`. Two files implement it: the packaged CLI (`wrappers/python/iso3166/cli.py`, installed as the `iso3166` console script by `pip install -e wrappers/python`) and the repo CLI (`tools/iso3166_cli.py`). `bin/iso3166` runs the installed script when one is on the `PATH`, and otherwise the repo CLI. All commands are read-only and offline. Twenty-five subcommands:

| Subcommand | Purpose |
|------------|---------|
| `lookup CODE` | All fields for one code |
| `list` | Filter across the registry |
| `currency CODE` | Currencies in circulation in a country |
| `country CCY` | Countries where a currency circulates |
| `region NAME` | All countries in a region |
| `info` | Registry metadata |
| `validate CODE...` | Exit 0 if every code exists, 1 otherwise |
| `search QUERY` | Substring search on names and codes |
| `successors CODE` | All descendants through `replaced_by` (transitive closure) |
| `predecessors CODE` | All ancestors: withdrawn codes that lead to the code |
| `is-eu`, `is-eea`, `is-eurozone` | Current membership; prints `true` or `false` |
| `is-eu-member-at CODE DATE`, `is-eea-member-at`, `is-eurozone-member-at`, `is-in-customs-union-at` | Dated membership |
| `region-tree CODE` | Region, subregion, intermediate region |
| `borders-transitively CODE [--max-hops N]` | Neighbours within N hops |
| `succession-path FROM TO` | Shortest `replaced_by` path |
| `calling-code-for NUMBER` | Countries for a phone number |
| `currency-at CODE DATE` | Lifetime-bounded current currency |
| `region-countries REGION [--subregion S]` | Codes in a region |
| `introduced CODE` | The `introduced` date, or `unknown` |
| `is-active-on CODE DATE` | Tri-state: `true`, `false`, `unknown` |

**Global options:** `--registry PATH`, `--color {never,auto,always}`. **Output modes**, mutually exclusive: `--json`, `--jsonl`, `--csv`, `--tsv`, `--raw [FIELD]`.

**Exit codes:**

| Code | Meaning |
|-----:|---------|
| 0 | Success. For `is-eu`, `is-eea` and `is-eurozone`, the code exists (the answer is on stdout). For the dated queries, the answer is `true`. |
| 1 | Code not found, or the dated answer is `false` |
| 2 | Usage error, including a malformed date |
| 3 | Registry file missing or invalid |
| 4 | Tri-state `unknown` (`is-active-on`, `introduced`, `currency-at`) |

```console
$ bin/iso3166 is-eu GB ; echo "[exit $?]"
false
[exit 0]
$ bin/iso3166 is-eu XX ; echo "[exit $?]"
error: not found: XX
[exit 1]
$ bin/iso3166 is-eu-member-at GB 2010-01-01 ; echo "[exit $?]"
true
[exit 0]
$ bin/iso3166 is-eu-member-at GB 2023-01-01 ; echo "[exit $?]"
false
[exit 1]
$ bin/iso3166 is-active-on XK 2000-01-01 ; echo "[exit $?]"
unknown
[exit 4]
$ bin/iso3166 currency-at DE 1990-01-01
EUR
$ bin/iso3166 successors YU --raw alpha_2
CS
ME
RS
$ bin/iso3166 is-eu-member-at GB 2010-13-45 ; echo "[exit $?]"
error: malformed date: '2010-13-45' (want YYYY-MM-DD)
[exit 2]
```

```bash
# Guard a pipeline on a dated fact, and tell "false" from "unknown" from "typo".
bin/iso3166 is-active-on "$CODE" "$DATE" >/dev/null
case $? in 0) echo active ;; 1) echo not-active ;; 4) echo unknown ;; 2) echo usage ;; esac
```

The two CLIs differ in one place: for `--raw`, the packaged CLI prints one empty line for a null or empty-list value so that a scalar field keeps one line per entry, and the repo CLI prints none. `list --region Oceania --raw tlds` prints 29 lines from the packaged CLI and 28 from the repo CLI. The difference is not reconciled in v1.12.1.

---

## 12. Language wrappers

Four wrappers, one contract. Each embeds a byte-identical copy of `iso3166.json` and is verified against the shared fixture [`tests/cross_language_consistency.json`](./tests/cross_language_consistency.json).

| Language | Package | Source | Minimum | Import | Tests |
|----------|---------|--------|---------|--------|------:|
| Python | `iso3166-registry` | [`wrappers/python`](./wrappers/python) | Python 3.9 | `from iso3166 import CountryRegistry` | 104 |
| JavaScript | `iso3166-registry` | [`wrappers/javascript`](./wrappers/javascript) | Node 18 | `require("iso3166-registry")` | 52 |
| Rust | `iso3166-registry` | [`wrappers/rust`](./wrappers/rust) | edition 2021 | `use iso3166_registry::CountryRegistry;` | 27 |
| Go | `github.com/slimissa/iso3166-go` | [`wrappers/go`](./wrappers/go) | Go 1.21 | `import iso3166 "github.com/slimissa/iso3166-go"` | 41 |

The Python and JavaScript counts are from running the suites; the Rust and Go counts are `#[test]` and `func Test` declarations counted statically, because the audit environment had no `cargo` or `go`. Each wrapper has its own README with the full API. Python, JavaScript and Go have no runtime dependencies; the Rust crate depends on `serde` and `serde_json`.

### One API, four spellings

| Query | Python | JavaScript | Rust | Go |
|-------|--------|------------|------|----|
| Load | `CountryRegistry()` | `new CountryRegistry()` | `CountryRegistry::load()` | `Load()` |
| Active entry | `.active("US")` | `.active("US")` | `.active("US")` | `.Active("US")` |
| Current EU | `.is_eu(c)` | `.isEu(c)` | `.is_eu(c)` | `.IsEU(c)` |
| EU on a date | `.is_eu_member_at(c, d)` | `.isEuMemberAt(c, d)` | `.is_eu_member_at(c, d)` | `.IsEUMemberAt(c, d)` |
| Customs union on a date | `.is_in_customs_union_at(c, d)` | `.isInCustomsUnionAt(c, d)` | `.is_in_customs_union_at(c, d)` | `.IsInCustomsUnionAt(c, d)` |
| Code existed on a date | `.is_active_on(c, d)` (`bool \| None`) | `.isActiveOn(c, d)` (`boolean \| null`) | `.is_active_on(c, d)` (`Option<bool>`) | `.IsActiveOn(c, d)` (`*bool`) |
| Currency on a date | `.currency_at(c, d)` (`list \| None`) | `.currencyAt(c, d)` | `.currency_at(c, d)` (`Option<Vec<String>>`) | `.CurrencyAt(c, d)` (`([]string, bool)`) |
| Descendants | `.successors(c)` | `.successors(c)` | `.successors(c)` | `.Successors(c)` |
| Succession path | `.succession_path(a, b)` | `.successionPath(a, b)` | `.succession_path(a, b)` | `.SuccessionPath(a, b)` |
| Region tree | `.region_tree(c)` | `.regionTree(c)` | `.region_tree(c)` | `.RegionTree(c)` |
| Phone number to countries | `.calling_code_for(n)` | `.callingCodeFor(n)` | `.calling_code_for(n)` | `.CallingCodeFor(n)` |

The tri-state spelling is the part that differs by language: a missing answer is `None`, `null`, `None` or a nil pointer, never `false`.

### The shared fixture

`tests/cross_language_consistency.json` is generated by `tools/gen_consistency_fixture.py` from the registry and checked in the gate with `--check`. Its `derived_queries` section holds 129 cases (a method name, arguments and the expected result), marked `enforced`; every wrapper and the CLI must produce them. The rest of the fixture holds the lookup, field, status-count and ambiguity cases. Adding a language does not require editing the fixture.

### Verify every wrapper agrees

```bash
bash tools/check_cross_language.sh US GB JP TW XK UK
```

The script runs the same `lookup` through all four wrappers and diffs the output literally. A code that no wrapper finds counts as agreement. Exit 0: all agreed. Exit 1: output differed. Exit 2: usage error or missing prerequisite. Exit 3: a wrapper failed to run. The CI job passes six codes; the release gate passes three (`US GB JP`).

---

## 13. Validation

[`tools/validate.py`](./tools/validate.py) has six independent layers, each runnable alone.

```bash
python3 tools/validate.py iso3166.json                                      # all six
python3 tools/validate.py iso3166.json --only ground-truth
python3 tools/validate.py iso3166.json --skip cross-reference --skip coverage
python3 tools/validate.py iso3166.json --strict-count --strict-independent --require-schema   # what the gate and CI run
```

Without `jsonschema` installed, layer 1 reports SKIP and `validate.py` can still exit 0 on the other five layers. `--require-schema` closes that: with the flag, a missing `jsonschema` (or an unreadable `schema.json`) exits 2 and names `pip install jsonschema`. The gate and the `validate-json` CI job both pass it.

| Layer | What it checks |
|-------|----------------|
| 1. Schema | JSON structure against `schema.json` |
| 2. Integrity | Format patterns, no empty strings, calendar-valid dates; `introduced` on every active entry equals `tools/introduced_snapshot.json` |
| 3. Business | Uniqueness, status consistency, withdrawal rules, border symmetry, acyclic succession |
| 4. Cross-reference | `currency_codes` against the ISO 4217 snapshot; `borders` and `replaced_by` resolvable. The other snapshot-backed fields (`calling_codes`, `tlds`, `languages`, `subregion`, `intermediate_region`) are checked against their snapshots by `enrich_field.py --only-value`, not by this layer |
| 5. Ground truth | Codes by status against the frozen sets in `tools/parse_source.py` |
| 6. Coverage | `meta.count_*` against the actual counts; `VERSION` against `meta.version` |

Exit codes: 0 pass, 1 data error, 2 usage, 3 schema violation. A clean run prints `Summary: 6 OK, 0 WARN, 0 FAIL, 0 SKIP`.

### The release gate: 30 checks

Everything below runs in the release gate, in this order, inside one `set -e` subshell. The first failure stops the release.

| # | Command | What it catches |
|--:|---------|-----------------|
| 1 | `check_version_consistency.py` | Any version site disagreeing with `VERSION` |
| 2 | `check_release_claims.py "$VERSION"` | A claim for this version in `tools/release_claims.json` that is false (20 for 1.12.2) |
| 3 | `check_mojibake.py` | UTF-8 / Latin-1 round-trip corruption and unclosed code fences in text files |
| 4 | `check_snapshot_freshness.py` | A `*_snapshot.json` whose `meta.review_by` has passed |
| 5 | `check_registry_freshness.py` | An entry whose `last_verified` is more than 365 days old |
| 6 | `check_iso4217_snapshot.py` | `tools/iso4217_snapshot.json` that does not parse, holds duplicate codes, or disagrees with its own meta counts |
| 7 | `validate.py iso3166.json --strict-count --strict-independent --require-schema` | Any of the six validator layers; a count mismatch; an `independent` regression in Northern America; a missing `jsonschema` (the schema layer must run) |
| 8 | `check_introduced.py` | An active entry whose `introduced` differs from `tools/introduced_snapshot.json` |
| 9 | `check_introduced_meta.py` | `introduced_snapshot.meta.json` missing `review_by`, `source` or `vendored_at`, or disagreeing with the snapshot's own `meta` |
| 10 | `check_state_doc.py --strict` | A number in `docs/STATE.md` that differs from the tree |
| 11 | `check_docs_match_tree.py` | A count, version or list stated in README, ENRICHMENT, PROVENANCE, CONTRIBUTING or LAYERS that the tree contradicts (13 checks) |
| 12 | `enrich_official_name.py --check` | `official_name` differing from its source |
| 13 | `enrich_withdrawn.py --check` | The withdrawn array differing from its source |
| 14 | `enrich_field.py --field currency_codes --check` | A `currency_codes` value missing on an entry, or not in the ISO 4217 snapshot |
| 15 | `enrich_field.py --field calling_codes --check` | A `calling_codes` value missing on an entry, or not in the ITU snapshot |
| 16 | `enrich_field.py --field tlds --check` | A `tlds` value missing on an entry, or not in the IANA snapshot |
| 17 | `enrich_field.py --field languages --check` | A `languages` value missing on an entry, or not in the ISO 639-3 snapshot |
| 18 | `enrich_field.py --field borders --check` | A `borders` value missing on an entry, or not an active alpha-2 code |
| 19 | `enrich_field.py --field subregion --check` | A `subregion` value missing on an entry, or not in the M49 snapshot |
| 20 | `enrich_field.py --field intermediate_region --check` | An `intermediate_region` value missing where M49 defines one, or not in the M49 snapshot |
| 21 | `enrich_field.py --only-value` | Any value of the seven snapshot-backed fields that is not in its snapshot; skips the presence check, so a value problem is reported on its own |
| 22 | `enrich_club_memberships.py --check` | The four club arrays differing from their snapshots |
| 23 | `check_release_diff.py` | A regenerated artifact that differs from `HEAD` in anything but the version string and the `updated` date (Parquet: in table content) |
| 24 | `python3 -m pytest tests/ -v` | The root suite (47 tests, including the architecture test and the index-vs-fixture test) |
| 25 | `python3 -m pytest wrappers/python/tests/ -q` | The Python wrapper suite (104 tests) |
| 26 | `build_introduced_snapshot.py --check` | `introduced_snapshot.json` differing from what its generator produces (the hand-written sibling `.meta.json` is checked by `check_introduced_meta.py`) |
| 27 | `build_club_snapshots.py --check` | A club snapshot or its `.meta.json` differing from what the generator produces |
| 28 | `bash tests/test_release_force.sh` | A regression in `release.sh --force` resume mode or in the gate's fail-closed behavior: 9 scenarios in a throwaway repository, two of them mutations that must be caught, two that refuse a commit on top of the release commit and an uncommitted regeneration |
| 29 | `check_cross_language.sh US GB JP` | A wrapper that disagrees on a lookup |
| 30 | `cargo clippy --all-targets -- -D warnings` | A clippy warning in the Rust crate |

The gate is not the whole test surface. The JavaScript suite (`npm test`), the Go suite (`go test`) and the Rust suite (`cargo test`) run in CI only, in `wrapper-javascript`, `wrapper-go` and `wrapper-rust`. The full wrapper surface is gated by the CI check the release script waits for before tagging.

### Tests

| Suite | Command | Tests |
|-------|---------|------:|
| Root (Python) | `python3 -m pytest tests/ -q` | 47 |
| Python wrapper | `(cd wrappers/python && python3 -m pytest tests -q)` | 104 |
| JavaScript | `(cd wrappers/javascript && node --test)` | 52 |
| Rust | `(cd wrappers/rust && cargo test)` | 27 (declarations) |
| Go | `(cd wrappers/go && go test ./...)` | 41 (declarations) |
| **Total** | | **271** |

### Additional checks

Beyond the six-layer validator, the repo carries eleven auxiliary checks, listed with where each one runs. Cross-language agreement is checked separately by `tools/check_cross_language.sh`.

| Tool | Purpose | Runs in |
|------|---------|---------|
| `tools/check_version_consistency.py` | Reads the registry-axis version sites; fails on any disagreement. | CI and release gate |
| `tools/check_mojibake.py` | Scans every text file for UTF-8/Latin-1 round-trip corruption. Fails on any hit. | CI and release gate |
| `tools/check_snapshot_freshness.py` | Reads `meta.review_by` on each `tools/*_snapshot.json`; fails on any date in the past. | CI and release gate |
| `tools/check_iso4217_snapshot.py` | Well-formedness of `tools/iso4217_snapshot.json`: parses, no duplicate codes, meta counts agree. | CI and release gate |
| `tools/check_release_claims.py` | Verifies machine-checkable claims about the version being released. | release gate only |
| `tools/check_release_diff.py` | After the version bump and regeneration, every generated artifact differs from `HEAD` only in the version string and the `updated` date; Parquet tables must hold the same data. | release gate only |
| `tools/check_registry_freshness.py` | Fails when any entry's `last_verified` is older than 365 days. | release gate only |
| `tools/check_state_doc.py` | Verifies every number in `docs/STATE.md` against the tree. | CI and release gate |
| `tools/check_docs_match_tree.py` | Verifies the counts, versions and lists that the README, ENRICHMENT, PROVENANCE, CONTRIBUTING and LAYERS docs state about the tree. | CI and release gate |
| `tools/check_introduced.py` | Every active entry's `introduced` equals `tools/introduced_snapshot.json`; a null needs a `meta.null_reasons` entry. The same comparison runs in the validator's integrity layer. | release gate; CI through `validate.py` |
| `tools/check_introduced_meta.py` | `tools/introduced_snapshot.meta.json` has `review_by`, `source` and `vendored_at` (valid dates, `review_by` not before `vendored_at`) and agrees with the snapshot's own `meta` (`review_by`, `source`, `source_permalink`, `source_accessed`). The generator never reads this hand-written file. | release gate and CI (`check-snapshots`) |

---

## 14. Continuous integration

One workflow, [`.github/workflows/validate.yml`](./.github/workflows/validate.yml), with 23 CI jobs. It runs on pushes to `main` and to `v*` branches, on pull requests to `main`, and on manual dispatch, and ignores pushes that touch only `.gitignore`, `.gitattributes` or `LICENSE`. It has read-only `contents` permission and cancels an in-progress run for the same ref.

There is no sanctions workflow. `sanctions-freshness.yml` does not exist: v1.13.0, the sanctions release, has not shipped.

| Job | What it runs |
|-----|--------------|
| `validate-json` | `validate.py` (strict), root `pytest`, `parse_source.py --verify` and `--audit`; matrix of Ubuntu 22.04 and 24.04, Python 3.11 and 3.12 |
| `check-version-consistency` | `check_version_consistency.py` |
| `check-iso4217-snapshot` | `check_iso4217_snapshot.py` |
| `check-wrapper-sync` | `sync_wrappers.py --check`, `gen_consistency_fixture.py --check` |
| `check-sql-export` | `export_sql.py --check` |
| `check-csv-export` | `export_csv.py --check` |
| `check-parquet-export` | `export_parquet.py --check`, `export_aggregated.py --check` |
| `check-cli` | `lookup US` succeeds; `lookup XX`, an unknown command and a missing registry fail with the right exit status |
| `check-docs` | An inline check of the repository's documentation |
| `check-withdrawn` | `enrich_withdrawn.py --check` |
| `check-withdrawn-doc` | `gen_withdrawn_doc.py --check` |
| `check-fields` | `enrich_official_name.py`, seven `enrich_field.py --field F`, and `enrich_club_memberships.py`, all `--check` |
| `check-state-doc` | `check_state_doc.py --strict` |
| `check-docs-match-tree` | `check_docs_match_tree.py` |
| `check-mojibake` | `check_mojibake.py` |
| `check-snapshot-freshness` | `check_snapshot_freshness.py` |
| `check-snapshots` | `build_introduced_snapshot.py --check`, `build_club_snapshots.py --check`, `check_introduced_meta.py` |
| `check-force-test` | `bash tests/test_release_force.sh` |
| `cross-language` | `check_cross_language.sh US GB JP TW XK UK`; needs `check-wrapper-sync` |
| `wrapper-python` | Wrapper tests on Python 3.11 and 3.12; `pip-audit` |
| `wrapper-javascript` | `npm test` on a Node matrix |
| `wrapper-go` | `go vet`, `go test`, `govulncheck` on a Go matrix |
| `wrapper-rust` | `cargo clippy -D warnings`, `cargo test`, `cargo audit` |

`registry freshness` runs in the release gate only, not in CI.

---

## 15. Release pipeline

Releases are cut by [`scripts/release.sh`](./scripts/release.sh):

```bash
bash scripts/release.sh <version> --dry-run   # print every step; changes nothing
bash scripts/release.sh <version>             # release
bash scripts/release.sh <version> --force     # resume from a post-commit state
```

It requires bash 4+, git, `gh`, python3 and cargo, runs on Linux only (it uses GNU `grep -P`), and needs a clean tree on `main`. In order:

0. **Preflight.** Inside a git repository, tree clean, branch `main`, `HEAD` equal to `origin/main`, CI on `HEAD` complete and green, a `## [<version>]` section in `CHANGELOG.md`, the tag free locally and on `origin`, `VERSION` different from the target, and the committed artifacts equal to what the tree generates: every export `--check` runs first, then the generators run, then `git diff --exit-code` compares the regenerated files with `HEAD` (in `--force` mode this runs at the start of step 2, where `HEAD` is the release commit). The release's entry in `tools/release_claims.json` is not a preflight item: gate line 2 (`check_release_claims.py`) exits 2 when the entry is missing. A `--check` after regeneration would compare a file with itself, so the gate has none; `tools/check_release_diff.py` checks the bumped, regenerated tree against `HEAD` instead.
1. **Bump the version sites** (below).
2. **Regenerate and gate.** Regenerates SQL, CSV, Parquet, aggregated, wrapper copies, the fixture, `WITHDRAWN.md` and `STATE.md`, then runs the gate: 30 checks run in sequence, listed in [Section 13](#13-validation). The first failure stops the release.
3. **Commit** `chore: release v<version>`, after checking that staged paths are not all ignored by the workflow's `paths-ignore`.
4. **Push and wait for CI.** Every workflow run for the release SHA must complete with `success`. A run that does not start within 180 seconds, a failed run, or a poll timeout stops the release before the tag exists.
5. **Tag** `v<version>` only on green. The tag message is read from the changelog section, checked for a header and body, written with `git tag -a -F ... --cleanup=verbatim`, read back with git and compared with the file; a mismatch or a wrong target deletes the local tag and pushes nothing. Then `git push origin v<version>`.
6. **GitHub release** with `gh release create`; the body is read back and refused if it contains placeholder text.
7. **Verification report.** Writes `docs/v<version>-verification.md` through `tools/write_verification_report.py`, committed and pushed with a sibling `docs/v<version>-verification.md.sha256`. Every command of the artifact freshness checks and of the gate is recorded with its exit code as it runs. The report lists them under **Gate commands:** and **Exit codes:**, numbered alike, with a `Result:` line and the SHA-256 of `/tmp/release-gate.log`. The sibling file holds the report's own SHA-256 in the format `sha256sum -c` reads, run from the repository root. The gate log itself is not committed: keep it, and its hash shows it is the log the report describes.

**`--force`** resumes from a post-commit state: when `VERSION` already equals the target because a previous run committed the release but did not reach the tag. It skips bump, commit and push, checks that `HEAD` **is** the `chore: release v<version>` commit (a commit on top of it is refused, because the tag lands on `HEAD`) and is on `origin/main`, **re-runs the gate and the CI check**, and refuses if regeneration left uncommitted files, then tags, releases and writes the report. `--force` and `--dry-run` are mutually exclusive, and `tests/test_release_force.sh` exercises the mode; it runs in the release gate and in the `check-force-test` CI job. `docs/README-AUDIT-NOTES.md` records the failures behind the rules: never reset `VERSION` to re-run the script, never interrupt the CI wait.

Forty-two verification reports exist, `docs/v1.0.0-verification.md` through [`docs/v1.12.2-verification.md`](./docs/v1.12.2-verification.md), from v1.12.3 each recording the commands and exit codes of its gate (see step 7); the earlier ones record the date, commit, tag and workflows, and some add a hand-written summary of the gate. Tags are immutable. The shared release pattern is [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md).

---

## 16. Versioning

One version number, held by ten files. `tools/check_version_consistency.py` verifies all of them.

| # | Site | Why it is a site |
|--:|------|------------------|
| 1 | `VERSION` | The source of truth |
| 2 | `iso3166.json` `meta.version` | A consumer holding only the JSON can tell what it is |
| 3 | `CHANGELOG.md` top released heading | The release history names the version it describes |
| 4 | `README.md` registry badge | The version a reader sees first |
| 5 | `iso3166.parquet` footer `iso3166.version` | A consumer holding only the Parquet can tell |
| 6 | `wrappers/python/pyproject.toml` | The Python package version |
| 7 | `wrappers/python/iso3166/__init__.py` `__version__` | The version the imported module reports |
| 8 | `wrappers/javascript/package.json` | The npm package version |
| 9 | `wrappers/rust/Cargo.toml` | The crate version |
| 10 | `wrappers/rust/Cargo.lock` | The locked crate version |

`scripts/release.sh` bumps eight of them (sites 1, 2, 4 and 6 to 10) and asserts all eight agree. The changelog heading (3) is written by hand before the release, and the Parquet footer (5) follows from regeneration. The checker prints nine result lines: the first covers sites 1 and 2.

Deliberate exclusions:

- **Go is not a site.** Go modules carry no version in `go.mod`; the version is the git tag.
- **The SQL and CSV files are not sites.** The SQL headers state the version in a comment, and `--check` fails if it is stale.
- **The aggregated Parquet has no footer version.**

`tools/version_axes.json` declares the same sites as a stable contract but is not read by the checker: the refactor waits for a fourth implementation. The schema has its own version (`schema.json`, currently 1.0.0, shown in the schema badge); a schema change does not bump the registry sites. The registry follows [Semantic Versioning](https://semver.org/): major for breaking schema changes, minor for new entries, new optional fields or new tooling, patch for data corrections. Wrapper package versions track the registry version.

---

## 17. Project structure

Every tracked file is named below. The 42 verification reports are collapsed into one line.

```text
iso3166/
  .gitattributes                            # LF endings for text artifacts; parquet is binary
  .gitignore                                # Ignore rules
  CHANGELOG.md                              # Release history (version site)
  CONTRIBUTING.md                           # Rules, change workflows, CI job list
  LICENSE                                   # Apache 2.0
  README.md                                 # This file (version badge is a version site)
  VERSION                                   # Registry version, source of truth
  countries_by_region.parquet               # AGGREGATED: 30 rows, grain (region, subregion)
  iso3166.csv                               # CURATED: CSV, RFC 4180, 24 columns
  iso3166.european.csv                      # CURATED: CSV, semicolon-delimited
  iso3166.excel.csv                         # CURATED: CSV with UTF-8 BOM
  iso3166.json                              # RAW: the registry (252 active, 25 withdrawn)
  iso3166.mysql.sql                         # CURATED: SQL, MySQL 8+ / MariaDB 10.4+
  iso3166.parquet                           # CURATED: Parquet, 24 columns (version site: footer)
  iso3166.postgresql.sql                    # CURATED: SQL, PostgreSQL 12+
  iso3166.sql                               # CURATED: SQL, ANSI SQL-92 (portable)
  iso3166.sqlite.sql                        # CURATED: SQL, SQLite 3.37+
  iso3166.tsv                               # CURATED: TSV
  requirements-dev.txt                      # Tool-time dependencies; pins pyarrow==26.0.0
  schema.json                               # JSON Schema for iso3166.json (schema version 1.0.0)
  .github/
    workflows/
      validate.yml                          # The only workflow: 23 CI jobs
  bin/
    iso3166                                 # Repo-local shim: installed `iso3166` if present, else tools/iso3166_cli.py
  docs/
    AUDIT.md                                # Tool inventory: --check mode, CI and release-gate coverage of each tool
    ENRICHMENT.md                           # How each enriched field is sourced and refreshed
    LAYERS.md                               # RAW / CURATED / AGGREGATED model
    PROVENANCE.md                           # Per-field source, access date and refresh cadence
    QUERIES-DECISIONS.md                    # Why each derived query is shaped as it is; deferred queries
    QUERIES.md                              # Signature, semantics and worked examples of every derived query
    README-AUDIT-NOTES.md                   # Append-only receipts: the failure behind each release rule
    RELEASE_PATTERN.md                      # Release invariants shared across the registry family
    SPEC-phase1.md                          # v1.11.0 Phase 1 spec: the `introduced` snapshot
    SPEC-v1.12.0-phase1.md                  # v1.12.0 Phase 1 spec: the club-membership snapshots
    STATE.md                                # Generated current-state doc; numbers verified by check_state_doc.py
    WITHDRAWN.md                            # Generated list of the 25 withdrawn codes
    v*-verification.md                      # 42 release gate records, v1.0.0 to v1.12.2
    v*-verification.md.sha256               # SHA-256 of each report, from v1.12.3 (sha256sum -c)
    decisions/
      club-memberships.md                   # ADR: club membership arrays, sources, null policy
      input-contract.md                     # ADR: the input contract of the four wrappers (v1.8.0)
      introduced-field.md                   # ADR: the `introduced` field and its quarantine rules
      languages-audit-2026-09.md            # Audit of the `languages` field, 2026-09
      languages-borders-sources.md          # Source selection for `languages` and `borders`
      v1.0.0-decisions.md                   # The locked v1.0.0 design decisions
      v1.5.0-scope.md                       # v1.5.0 scope: reconnaissance of the remaining fields
      v1.9.2-amendments.md                  # Where the tree no longer matches the v1.0.0 decisions
      v1.9.3-version-policy.md              # Version strings in PROVENANCE.md and CONTRIBUTING.md
      withdrawn-codes.md                    # ADR: withdrawn codes and successors
  scripts/
    release.sh                              # The release pipeline (steps 0 to 7, 30-check gate)
  tests/
    cross_language_consistency.json         # Shared fixture for all four wrappers (generated)
    test_architecture.py                    # AST guardrail: export_aggregated.py must not read RAW JSON
    test_check_release_diff.py              # check_release_diff.py allows only version and date changes after a bump
    test_enrich_field_citations.py          # record_source writes one source line per field
    test_enrich_field_values.py             # enrich_field.py --only-value compares values with the snapshot
    test_enrich_independent.py              # enrich_independent.py logic that needs no live ISO markup
    test_export_aggregated.py               # Aggregated export tests
    test_export_check_order.py              # The artifact freshness block fails at --check, before regeneration
    test_index_matches_fixture.py           # docs/QUERIES.md worked-examples index equals the fixture's derived_queries
    test_release_force.sh                   # Shell test of release.sh --force resume mode (release gate and CI)
    test_validate_require_schema.py         # validate.py --require-schema exits 2 without jsonschema
    test_verification_report_evidence.py    # The report records every gate command, exit code and the log hash
    test_release_pattern.py                 # Release-pattern properties
  tools/
    audit_languages.py                      # Classify each entry's languages list
    build_club_snapshots.py                 # Generate the four club snapshots and their meta files
    build_initial_data.py                   # Archival: one-shot importer that produced the first iso3166.json
    build_introduced_snapshot.py            # Generate introduced_snapshot.json from wikipedia_dates.json
    check_cross_language.sh                 # Run a lookup through all four wrappers and diff the output
    check_docs_match_tree.py                # Prose claims (README, ENRICHMENT, ...) vs the tree
    check_introduced.py                     # Every active entry's `introduced` equals introduced_snapshot.json
    check_introduced_meta.py                # introduced_snapshot.meta.json is complete and agrees with the snapshot
    check_iso4217_snapshot.py               # Well-formedness of iso4217_snapshot.json
    check_mojibake.py                       # UTF-8 / Latin-1 round-trip corruption detector
    check_registry_freshness.py             # `last_verified` within 365 days on every entry
    check_release_claims.py                 # Verify the claims for one version in release_claims.json
    check_release_diff.py                   # Regenerated artifacts differ from HEAD only in the version
    check_snapshot_freshness.py             # Every snapshot's meta.review_by not in the past
    check_state_doc.py                      # Verify docs/STATE.md against the tree
    check_version_consistency.py            # Version sites agree
    club_format.py                          # Serialize club arrays to 'from:to|from:to' for flat exports
    cross_language_derived.py               # Run every derived-query fixture case through the Python wrapper
    customs_union_snapshot.json             # Snapshot: EU customs union (annual)
    customs_union_snapshot.meta.json        # Vendoring metadata and review_by
    eea_membership_snapshot.json            # Snapshot: EEA, with provisional-application dates
    eea_membership_snapshot.meta.json       # Vendoring metadata and review_by
    enrich_club_memberships.py              # Populate the four club arrays on active entries (--check)
    enrich_field.py                         # Populate one list field from its snapshot (--field F --check, --only-value)
    enrich_independent.py                   # Populate `independent` from ISO OBP, with an audit trail
    enrich_official_name.py                 # Populate `official_name` (--check)
    enrich_withdrawn.py                     # Maintain the withdrawn array (--check)
    eu_membership_snapshot.json             # Snapshot: EU membership (annual)
    eu_membership_snapshot.meta.json        # Vendoring metadata and review_by
    eurozone_membership_snapshot.json       # Snapshot: eurozone membership (annual)
    eurozone_membership_snapshot.meta.json  # Vendoring metadata and review_by
    export_aggregated.py                    # Generate countries_by_region.parquet from iso3166.parquet (--check)
    export_csv.py                           # Generate the four CSV/TSV files (--check)
    export_parquet.py                       # Generate iso3166.parquet (--check, bytes)
    export_sql.py                           # Generate the four SQL files (--check)
    gen_consistency_fixture.py              # Regenerate the cross-language fixture (--check)
    gen_iso4217_snapshot.py                 # Generate iso4217_snapshot.json from an ISO 4217 registry file
    gen_state_doc.py                        # Generate docs/STATE.md
    gen_withdrawn_doc.py                    # Generate docs/WITHDRAWN.md (--check)
    iana_tld_snapshot.json                  # Snapshot: IANA ccTLDs (248)
    independent_snapshot.json               # Snapshot: ISO OBP `independent` extract
    initial_exceptions.json                 # Archival: hand-maintained overrides for the initial import
    introduced_snapshot.json                # Snapshot: `introduced` dates and null_reasons
    introduced_snapshot.meta.json           # Vendoring metadata and review_by
    iso3166_cli.py                          # The repo CLI (25 subcommands)
    iso4217_snapshot.json                   # Snapshot: ISO 4217 codes, v1.8.0
    iso639_3_snapshot.json                  # Snapshot: ISO 639-3 languages (7,927 codes)
    itu_calling_code_snapshot.json          # Snapshot: ITU calling codes (204)
    m49_intermediate_region_snapshot.json   # Snapshot: UN M49 intermediate regions (7, closed)
    m49_subregion_snapshot.json             # Snapshot: UN M49 subregions (17, closed)
    migrate_notes_to_per_field.py           # Archival: one-shot per-field source-note migration
    parse_source.py                         # Frozen ground-truth code sets
    patterns.py                             # Regular expressions shared by more than one tool
    release_claims.json                     # Machine-checkable claims per version
    sync_wrappers.py                        # Copy iso3166.json into the four wrapper directories (--check)
    validate.py                             # Six-layer validator (--require-schema fails when the schema layer cannot run)
    version_axes.json                       # Declarative version-site contract (not yet read by the check)
    wikipedia_dates.json                    # Input to build_introduced_snapshot.py
    write_verification_report.py            # Write docs/vX-verification.md with the gate evidence and its .sha256
  wrappers/
    go/
      README.md                             # Go API
      clubs.go                              # Dated club queries
      clubs_test.go                         # Club query tests
      derived_test.go                       # Derived-query fixture test
      go.mod                                # Module github.com/slimissa/iso3166-go (no version site)
      iso3166.json                          # CURATED: byte-identical copy of the registry
      registry.go                           # CountryRegistry and the derived queries
      registry_test.go                      # Registry and fixture tests
      cmd/
        lookup/
          main.go                           # Lookup binary used by check_cross_language.sh
        query/
          main.go                           # Query binary
    javascript/
      README.md                             # JavaScript API
      clubs.js                              # Dated club queries
      derived.js                            # Derived queries
      index.js                              # CountryRegistry
      iso3166.json                          # CURATED: byte-identical copy of the registry
      package.json                          # Package iso3166-registry (version site)
      test/
        clubs.test.js                       # Club query tests
        consistency.test.js                 # Shared-fixture test
        derived.test.js                     # Derived-query tests
        registry.test.js                    # Registry tests
    python/
      README.md                             # Python API
      pyproject.toml                        # Package iso3166-registry (version site)
      iso3166/
        __init__.py                         # Exports; __version__ (version site)
        cli.py                              # Packaged CLI, `iso3166` console script (25 subcommands)
        clubs.py                            # Dated club queries (4)
        derived.py                          # Derived queries (12)
        iso3166.json                        # CURATED: byte-identical copy of the registry
        registry.py                         # Country and CountryRegistry
      tests/
        test_cli.py                         # CLI tests
        test_clubs.py                       # Club query tests
        test_consistency.py                 # Shared-fixture test
        test_derived.py                     # Derived-query tests
        test_registry.py                    # Registry tests
    rust/
      Cargo.lock                            # Lockfile (version site)
      Cargo.toml                            # Crate iso3166-registry (version site)
      README.md                             # Rust API
      iso3166.json                          # CURATED: byte-identical copy of the registry
      src/
        lib.rs                              # CountryRegistry and the derived queries
        bin/
          lookup.rs                         # Lookup binary used by check_cross_language.sh
          query.rs                          # Query binary
      tests/
        consistency.rs                      # Shared-fixture test
```

---

## 18. Documentation index

| Document | What does it answer? |
|----------|----------------------|
| [`docs/LAYERS.md`](./docs/LAYERS.md) | Which layer does a file belong to, how is it produced, and how is it checked? |
| [`docs/PROVENANCE.md`](./docs/PROVENANCE.md) | Where does each field come from, how often is it refreshed, and what is not covered? |
| [`docs/ENRICHMENT.md`](./docs/ENRICHMENT.md) | How are the enriched fields populated, and where does the naive rule break? |
| [`docs/QUERIES.md`](./docs/QUERIES.md) | What are the signature, semantics and edge cases of each derived query? |
| [`docs/QUERIES-DECISIONS.md`](./docs/QUERIES-DECISIONS.md) | Why is each query shaped as it is, and which queries are deferred? |
| [`docs/STATE.md`](./docs/STATE.md) | What is the current state of the registry, with every number verified? |
| [`docs/WITHDRAWN.md`](./docs/WITHDRAWN.md) | Which codes are withdrawn, when, and replaced by what? |
| [`docs/AUDIT.md`](./docs/AUDIT.md) | Which tools exist, and does each run in CI and in the release gate? |
| [`docs/RELEASE_PATTERN.md`](./docs/RELEASE_PATTERN.md) | What invariants does every release refuse on? |
| [`docs/README-AUDIT-NOTES.md`](./docs/README-AUDIT-NOTES.md) | What failure is behind each release rule? |
| [`docs/decisions/`](./docs/decisions) | Why was each design choice made? Ten decision documents, from [`v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md) to [`club-memberships.md`](./docs/decisions/club-memberships.md). |
| `docs/SPEC-phase1.md`, `docs/SPEC-v1.12.0-phase1.md` | What did the Phase 1 research of the `introduced` and club-membership snapshots find? |
| `docs/v<version>-verification.md` | What did the gate print when this version shipped? |
| [`CHANGELOG.md`](./CHANGELOG.md) | What changed in each release? |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | How do I correct data, add a code, or change a tool? |
| `wrappers/*/README.md` | What is the full API of each wrapper? |

---

## 19. Contributing

Open an issue before starting a large change. Data corrections go through an enrichment tool, not a hand edit of `iso3166.json`. [`CONTRIBUTING.md`](./CONTRIBUTING.md) covers data corrections, adding or withdrawing a code, wrapper contributions and release prerequisites. The quick workflow:

1. Set up (once): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt && pip install -e wrappers/python`
2. Change the data through its tool (`tools/enrich_*.py`), or change the tool.
3. Validate; it must exit 0: `python3 tools/validate.py iso3166.json --strict-count --strict-independent`
4. Regenerate the derived files, in layer order:
   `python3 tools/export_sql.py && python3 tools/export_csv.py && python3 tools/export_parquet.py && python3 tools/export_aggregated.py && python3 tools/sync_wrappers.py && python3 tools/gen_consistency_fixture.py && python3 tools/gen_withdrawn_doc.py && python3 tools/gen_state_doc.py`
5. Check for drift: `for t in export_sql export_csv export_parquet export_aggregated sync_wrappers gen_consistency_fixture gen_withdrawn_doc enrich_club_memberships; do python3 tools/$t.py --check || break; done`
6. Check the conventions: `python3 tools/check_version_consistency.py && python3 tools/check_mojibake.py && python3 tools/check_docs_match_tree.py && python3 tools/check_state_doc.py --strict`
7. Run the tests: `python3 -m pytest tests/ -q && python3 -m pytest wrappers/python/tests/ -q`
8. Run the cross-language check: `bash tools/check_cross_language.sh US GB JP` (needs `node`, `cargo` and `go`).
9. Rehearse the release: `bash scripts/release.sh <version> --dry-run`
10. Open a pull request. CI runs 23 jobs.

**Source discipline.** Every enrichable field is first-party (ISO, UN, IANA, ITU, ISO 639-3, a documented government statistical service). Wikipedia, countrycode.org and aggregator CSVs are not acceptable as the origin of a field, with one explicit, documented exception: `introduced` and the four club arrays ([Section 7](#7-the-temporal-identity-layer)).

**Rules for scripts and commits.** No heredocs for patch scripts: write `/tmp/script.py`, run it, check its exit code. No live corruption examples in docs. Commit messages are claims about the diff: run `git diff --cached --stat` first. No tag before CI is green; the release script enforces it.

---

## 20. Known limitations

Stated plainly, because a canonical registry is a claim and a claim needs its edges drawn.

- **`introduced` is null for 76 of 252 active entries and all 25 withdrawn ones:** 27 quarantined (6 confirmed, 21 likely), 46 source-silent, 3 not officially assigned. `is_active_on` answers `null` for them.
- **The quarantine reasons for 21 of the 27 are `[likely]`,** inferred from the post-Soviet and post-Yugoslav succession and from newsletter dates, not from a primary record. Six are `[confirmed]` against the tree's own withdrawn entries.
- **No historical currencies.** `currency_at` returns the entry's current currency inside its lifetime and `None` outside it. `currency_at("DE", "1990-01-01")` is `["EUR"]`, not the Deutsche Mark. For a withdrawn entry it returns the successor's current currency up to and including `withdrawal_date`.
- **Nothing before 1974 can be answered.** ISO 3166-1 starts in 1974; for a withdrawn entry before 1974-01-01 `is_active_on` is `null`. The club arrays reach back further (the EU to 1958) and are not bounded by it.
- **The `introduced` and club data are Wikipedia-sourced** under a documented exception, not first-party. Each snapshot is reviewed annually (`review_by` 2027-10-28 and 2027-10-29), and the four club snapshots cite a page title URL, not an `oldid` permalink.
- **EEA provisional application is dated for 12 countries.** Croatia has formal dates only. The UK's EEA end (2020-12-31) is the page prose's date, and the state table disagrees; it is flagged likely in the snapshot.
- **Five active entries have no region:** `AQ`, `EU`, `TW`, `UK`, `XK`. In `countries_by_region.parquet` they, and the 25 withdrawn entries, fall into rows with a null `region`.
- **The aggregated table counts withdrawn entries.** Its 277 sums to the total, not to the 252 active entries, and `AI` and `SK` are counted twice.
- **The club arrays are strings in CSV, TSV, SQL and Parquet,** in the `from:to|from:to` format, not native lists or structs. A consumer who wants ranges parses the string or reads the JSON.
- **The SQL export has no `currency_codes` column;** currencies are in the `country_currencies` join table (249 rows).
- **The packaged CLI and the repo CLI differ in `--raw`:** the packaged one prints an empty line for a null or empty-list value, and the repo one does not (29 and 28 lines for `list --region Oceania --raw tlds`). The module docstrings are stale too: the repo CLI's says eight subcommands, the packaged one's says twenty-three, and both implement twenty-five.
- **The release gate does not run the JavaScript, Go or Rust test suites.** It runs the Python suites, `cargo clippy` and the cross-language lookup; the other three run in CI, which the release script waits for before tagging. The Rust and Go test counts in this README are static counts of declarations, not test runs.
- **`pyarrow` is pinned in `requirements-dev.txt` only.** There is no `constraints.txt` and no test that fails on an unpinned install line. The `check-parquet-export` job also runs an unpinned `pip install pyarrow pandas`, which is a no-op after the pinned install but not structurally guarded.
- **`check_registry_freshness.py` runs in the release gate only, not in CI,** and `independent_snapshot.json` has no `review_by`, so the snapshot freshness check reports `review_by unset` as a warning.
- **`independent` has no ISO OBP extract for `UK`** (`tools/independent_snapshot.json`), so that one value has no OBP source (`docs/STATE.md`, limitation 1).
- **The sanctions release (v1.13.0) has not shipped.** No `sanctions_regime` field and no `is_sanctioned_at` query exists. A first attempt stopped because no first-party source was reachable.
- **The geography release (v1.14.0) is deferred.** There is no `regions.json` and no `timezones[]`.
- **No subdivisions.** ISO 3166-2 is not covered.
- **Language packages are not published** to PyPI, npm, crates.io or a Go proxy. Install from a clone.
- **The release script is Linux-only,** and its network-dependent steps (`gh`) need access to GitHub.

---

## 21. FAQ

**Why does `is_eu("GB")` return false?**
`is_eu` is the *current-status* alias: the UK left the EU on 2020-01-31, so it is not a member today. For a date, use `is_eu_member_at("GB", "2010-01-01")`, which is `true`.

**Why is `currency_at("DE", "1990-01-01")` `["EUR"]` and not the Deutsche Mark?**
The registry stores no currency history. `currency_at` bounds the answer to the entry's lifetime (`introduced` to `withdrawal_date`) and returns the *current* currencies inside it. It returns `None` before `introduced`, so `currency_at("DE", "1960-01-01")` is `None`.

**What does a null in `introduced` mean?**
The source did not give a date the registry can defend. 27 are quarantined with a recorded reason, 46 are source-silent, 3 (`EU`, `UK`, `XK`) are not in ISO 3166-1. `is_active_on` returns `null` for them, never `false`. See [`docs/decisions/introduced-field.md`](./docs/decisions/introduced-field.md).

**Why are the club arrays strings in CSV, SQL and Parquet?**
So the cell is identical across all nine files (`1973-01-01:2020-01-31`, ranges joined with `|`). The JSON and the wrappers hold real `{from, to}` ranges.

**How do I query "which countries were in the EU in 2010?"**
Call `is_eu_member_at(code, "2010-01-01")` for each code, or filter the ranges in the JSON, or use the DuckDB macro in [Section 10](#10-worked-example-a-strategy-across-four-dates). The answer is 27.

**Is the EEA provisional date modeled, or only the formal one?**
Both. The snapshot holds the formal entry into force and, for 12 countries, the earlier provisional-application range; `enrich_club_memberships.py` unions them into `eea_membership`.

**What is the difference between `is_active_on` and `is_eu_member_at`?**
`is_active_on` asks whether the *code* existed, and is tri-state because `introduced` can be null. `is_eu_member_at` asks whether the *country* was in a club, and is binary because the ranges are complete. Both are date-scoped.

**Why do `AI` and `SK` appear twice?**
Each is an active code (Anguilla, Slovakia) that ISO reused after an earlier entry with the same code was withdrawn. Key on `(alpha_2, status)`. Queries that take a code alone prefer the active entry.

**Why do 36 entries list EUR but only 21 are in the eurozone?**
Membership and currency are different facts. Andorra, Monaco, San Marino, the Vatican, Montenegro, and several French and Finnish territories use the euro without being members.

**Why does `successors("YU")` return three codes?**
It returns the full transitive closure: `CS`, `ME`, `RS`. Before v1.10.0 the CLI returned terminal successors only.

**Why do some CSV values look like `1974-09-15` text and not dates?**
Dates are plain `YYYY-MM-DD` text in every flat file except Parquet. Parse them on read.

**How do I know which version produced a file I was handed?**
JSON: `meta.version`. Parquet: footer key `iso3166.version`. SQL: the `-- Registry version:` comment in the header.

---

## 22. Consumed by

ISO 3166 is a root of the join graph: other registries reference `alpha_2`. This registry in turn vendors an ISO 4217 snapshot to validate `currency_codes`. The proof column says where the evidence lives.

| Project | Edge | Proof |
|---------|------|-------|
| [ISO 4217](https://github.com/slimissa/iso4217) | Vendors a byte-for-byte snapshot of this registry at `tools/iso3166_snapshot.json`; every `countries[].code` must resolve in `countries.active[].alpha_2` | In ISO 4217's README and CI. Not checkable from this tree. |
| [ISO 10383](https://github.com/slimissa/iso10383) | Vendors a snapshot (252 codes, v1.6.9 per its README); every MIC's `country_code` must resolve, or be `ZZ` | In ISO 10383's README and CI. Not checkable from this tree. |
| [Exchange Calendar](https://github.com/slimissa/exchange-calendar) | Vendors a snapshot; every exchange's `country_code` must resolve | In that repository's CI, as recorded in the previous README. Not checkable from this tree. |
| [Corporate Actions](https://github.com/slimissa/corporate-actions) | Instrument entries reference the country of listing | Recorded as stated in the previous README. Not checkable from this tree. |
| Asset Identifiers | Planned: will reference `alpha_2` for country of listing | None yet |
| [LAS_Shell](https://github.com/slimissa/Las_shell) | Reads country codes for market status and prompt display | None in this tree |
| [Tempus](https://github.com/slimissa/Tempus) | Planned compile-time `Country<ISO3166>` validation | None in this tree |
| ISO 4217 (reverse edge) | This registry's `currency_codes` must resolve in an ISO 4217 snapshot | `tools/iso4217_snapshot.json` (v1.8.0, `review_by` 2027-10-25), checked by validator layer 4 and `check_iso4217_snapshot.py` |

No external adopter is recorded. *Using this registry in your project? Open a pull request to add a row.*

---

## 23. License and author

Apache 2.0. See [`LICENSE`](./LICENSE). The country data in this registry is factual information sourced from public standards. The compilation, schema, tooling, wrappers and documentation are licensed works.

**Le P'tit**, [github.com/slimissa](https://github.com/slimissa)

---

## 24. What's next

Nothing is scheduled. Each item below starts when its trigger fires.

| Deferred item | Trigger to start | Where decided |
|---------------|------------------|---------------|
| **v1.13.0, sanctions:** `sanctions_regime`, `is_sanctioned_at(code, regime, date)` | A compliance consumer exists and a reliable country-level source is found | `docs/QUERIES-DECISIONS.md` (deferred table) |
| **v1.14.0, geography:** `regions.json`, `timezones[]` | A consumer asks for `regions.json` or `timezones[]` | `docs/QUERIES-DECISIONS.md` |
| **v1.15.0, ecosystem:** the documentation release | The six registries are stable enough to be documented as a platform | This section |
| **v1.16.0, subdivisions:** ISO 3166-2 as a `subdivisions.json` companion | A consumer asks for ISO 3166-2 subdivisions | `docs/QUERIES-DECISIONS.md` |
| **v2.0.0:** a breaking schema change | A consumer needs one | This section |
| **Read `tools/version_axes.json` in the version check** | A fourth implementation of the release pattern exists | `tools/version_axes.json` |
| **`source_hash`** | A stable raw source appears; the current sources are not stable files | Previous README |
| **Pin the CI `pyarrow` install and add a `constraints.txt`** | The next release that touches CI | [Known limitations](#20-known-limitations) |

See [`CHANGELOG.md`](./CHANGELOG.md) for release history and [`docs/decisions/`](./docs/decisions) for locked decisions.
