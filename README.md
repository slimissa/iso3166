# ISO 3166 Country Registry

**A canonical, versioned, machine-readable registry of ISO 3166 country codes.**

One JSON file. Zero runtime dependencies. Four language wrappers.

[![Validate](https://github.com/slimissa/iso3166/actions/workflows/validate.yml/badge.svg)](https://github.com/slimissa/iso3166/actions/workflows/validate.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Schema](https://img.shields.io/badge/schema-1.0.0-green.svg)](./schema.json)
[![Registry](https://img.shields.io/badge/registry-1.0.1-orange.svg)](./iso3166.json)

---

## Why?

Every system that touches international finance, trade, shipping, or
identity maintains its own country list. They drift. Some use alpha-3,
some alpha-2, some numeric. Some include territories, some merge them.
Some include Kosovo, some don't.

This registry provides one versioned, schema-validated JSON file that
any tool can depend on. The JSON is the contract. The SQL, CSV,
Parquet, CLI, and wrappers are five ways to consume it without writing
a parser.

---

## Quick start

### Direct download

```bash
curl -O https://raw.githubusercontent.com/slimissa/iso3166/main/iso3166.json
```

### Python

```bash
pip install -e wrappers/python
```

```python
from iso3166 import CountryRegistry

reg = CountryRegistry()
us = reg.active("US")
print(us.alpha_3, us.name)             # USA United States of America
print(reg.by_numeric("840").alpha_2)   # US
print(len(reg.region("Europe")))       # number of European entries
```

### JavaScript

```bash
npm install ./wrappers/javascript
```

```javascript
const { CountryRegistry } = require("iso3166-registry");
const us = new CountryRegistry().active("US");
console.log(us.alpha_3, us.name);
```

### Go

```go
import iso3166 "github.com/slimissa/iso3166-go"

reg, _ := iso3166.Load()
if us := reg.Active("US"); us != nil {
    fmt.Println(us.Alpha3, us.Name)
}
```

### Rust

```rust
use iso3166_registry::CountryRegistry;

let reg = CountryRegistry::load().unwrap();
if let Some(us) = reg.active("US") {
    println!("{} {}", us.alpha_3, us.name);
}
```

### Command line

```bash
iso3166 lookup US
iso3166 list --region Europe
iso3166 info
iso3166 validate US FR DE
```

See [the CLI reference](#command-line-interface) below.

---

## Registry contents

| Layer | Count | Purpose |
|-------|-------|---------|
| Officially-assigned ISO 3166-1 | 249 | Every currently-assigned alpha-2 code |
| Exceptionally-reserved | 2 | `UK`, `EU` |
| User-assigned | 1 | `XK` (Kosovo) |
| Withdrawn ISO 3166-3 | 15 | Historical codes with successors |
| **Total** | **267** | |

The active array contains 252 entries; the withdrawn array contains 15.
Two alpha-2 codes — `AI` and `SK` — appear in both, because ISO
reassigned them: `AI` was French Afars and Issas (withdrawn 1977,
replaced by `DJ`), then became Anguilla; `SK` was Sikkim (withdrawn
1975, replaced by `IN`), then became Slovakia.

### What's in a country entry

```json
{
  "alpha_2": "US",
  "alpha_3": "USA",
  "numeric": "840",
  "name": "United States of America",
  "status": "officially-assigned",
  "independent": true,
  "official_name": "United States of America",
  "region": "Americas",
  "subregion": "Northern America",
  "intermediate_region": null,
  "currency_codes": null,
  "calling_codes": null,
  "tlds": null,
  "languages": null,
  "borders": null,
  "note": null,
  "last_verified": "2026-09-22",
  "withdrawal_date": null,
  "replaced_by": null
}
```

Every entry has `alpha_2`, `alpha_3`, `numeric`, `name`, `status`, and
`independent`. The remaining fields are optional; when a source doesn't
provide a value, the field is `null` rather than omitted. See
[`docs/PROVENANCE.md`](./docs/PROVENANCE.md) for which fields are
populated in v1.0.0 and which are deferred.

---

## Command-line interface

The `iso3166` command is installed by the Python wrapper. Eight
subcommands:

| Subcommand | Purpose |
|------------|---------|
| `lookup CC` | All fields for one country |
| `list` | Filter across the registry |
| `currency CC` | Currencies in circulation in a country |
| `country CURRENCY` | Countries where a currency circulates |
| `region REGION` | All countries in a region |
| `info` | Registry metadata |
| `validate CC...` | Exit 0 if all codes exist, 1 otherwise |
| `search QUERY` | Substring search on names and codes |

Five output modes, mutually exclusive: `--json`, `--jsonl`, `--csv`,
`--tsv`, `--raw FIELD`.

Exit codes: **0** success, **1** code not found, **2** usage error,
**3** registry missing or invalid.

Color is on when stdout is a TTY, off when piped. Override with
`ISO3166_COLOR=never|auto|always`, or `--color` / `--no-color`.
`NO_COLOR` (any value) forces off unless `--color=always` is given.

### Examples

```bash
# Look up a country.
iso3166 lookup US

# Every country in Europe, as JSON.
iso3166 list --region Europe --json

# Codes only.
iso3166 list --region Europe --raw alpha_2

# Validate a list of codes.
iso3166 validate US FR DE JP || echo "one or more unknown"
```

`--csv` output is byte-compatible with `iso3166.csv` at the repo root.

---

## Repository contents

```
iso3166/
├── iso3166.json                 # The registry (267 entries)
├── schema.json                  # JSON Schema draft-07 contract
├── VERSION                      # Single source of version truth
├── CHANGELOG.md
├── LICENSE                      # Apache 2.0
├── README.md                    # This file
├── CONTRIBUTING.md
├── requirements-dev.txt         # Tool-time dependencies (jsonschema, pyarrow)
├── .gitattributes               # Forces LF for generated artifacts
├── .gitignore
│
├── docs/
│   ├── PROVENANCE.md            # Sources, refresh cadence, known gaps
│   ├── LAYERS.md                # RAW / CURATED / AGGREGATED model
│   ├── v1.0.0-verification.md   # Release verification report
│   └── decisions/
│       ├── v1.0.0-decisions.md  # D1–D8
│       └── withdrawn-codes.md   # ADR for ISO 3166-3 successor handling
│
├── iso3166.sql                  # SQL — ANSI SQL-92
├── iso3166.postgresql.sql       # SQL — PostgreSQL 12+
├── iso3166.mysql.sql            # SQL — MySQL 8+ / MariaDB 10.4+
├── iso3166.sqlite.sql           # SQL — SQLite 3.37+
├── iso3166.csv                  # CSV — RFC 4180
├── iso3166.excel.csv            # CSV — UTF-8 BOM for Windows Excel
├── iso3166.european.csv         # CSV — semicolon-delimited
├── iso3166.tsv                  # TSV
├── iso3166.parquet              # Parquet — typed, columnar
│
├── tools/
│   ├── build_initial_data.py    # One-shot importer (archival)
│   ├── initial_exceptions.json  # Overrides for the initial import
│   ├── parse_source.py          # Frozen ground-truth code sets
│   ├── validate.py              # Six-layer validator
│   ├── export_sql.py            # SQL exporter (--check for CI)
│   ├── export_csv.py            # CSV/TSV exporter (--check)
│   ├── export_parquet.py        # Parquet exporter (--check)
│   ├── sync_wrappers.py         # Bundled JSON sync (--check)
│   ├── gen_consistency_fixture.py  # Regenerate the cross-language fixture
│   ├── check_version_consistency.py
│   ├── gen_iso4217_snapshot.py  # Cross-registry snapshot generator
│   ├── iso4217_snapshot.json    # ISO 4217 codes for cross-reference
│   ├── iso3166_cli.py           # CLI
│   └── check_cross_language.sh  # Four-wrapper agreement check
│
├── tests/
│   └── cross_language_consistency.json  # Shared contract for all wrappers
│
├── wrappers/
│   ├── python/                  # pip install -e wrappers/python
│   ├── javascript/              # npm install ./wrappers/javascript
│   ├── go/                      # go get github.com/slimissa/iso3166-go
│   └── rust/                    # cargo add --path wrappers/rust
│
├── bin/
│   └── iso3166                  # Shell wrapper (prefers installed CLI)
│
└── .github/workflows/validate.yml  # 14 CI jobs
```

---

## Data model

Twelve required-or-optional fields per entry, plus three for withdrawn:

| Field | Type | Notes |
|-------|------|-------|
| `alpha_2` | string | Primary key. `^[A-Z]{2}$`. |
| `alpha_3` | string | `^[A-Z]{3}$`. |
| `numeric` | string | `^[0-9]{3}$`. Zero-padded string, not integer. |
| `name` | string | ISO 3166 English short name. |
| `status` | string | `officially-assigned` / `user-assigned` / `exceptionally-reserved` / `withdrawn`. |
| `independent` | boolean | ISO's sovereignty flag. |
| `official_name` | string\|null | ISO's full official name. |
| `region` | string\|null | UN M49 macro-region. |
| `subregion` | string\|null | UN M49 sub-region. |
| `intermediate_region` | string\|null | UN M49 intermediate region. |
| `currency_codes` | list\|null | ISO 4217 alpha-3 codes. |
| `calling_codes` | list\|null | ITU-T E.164 prefixes. |
| `tlds` | list\|null | IANA ccTLDs. |
| `languages` | list\|null | ISO 639-3 codes. |
| `borders` | list\|null | Adjacent alpha-2 codes. |
| `note` | string\|null | Anything the standard doesn't capture. |
| `last_verified` | string\|null | ISO date of last manual check. |
| `withdrawal_date` | string\|null | Withdrawn entries only. |
| `replaced_by` | list\|null | Withdrawn entries only. |

`numeric` is a string, not an integer, because `numeric` is a reserved
word in SQL and because leading zeros (`004` for Afghanistan) are
meaningful.

The `borders` field, when populated, points only to **active** codes:
a border is a currently-existing country, not a historical one. The
`replaced_by` field may point to any code in the registry, active or
withdrawn, because succession chains are legitimate (`YU` → `CS` →
`RS`, `ME`).

---

## Validation

Six layers, each independently runnable:

```bash
python3 tools/validate.py iso3166.json
python3 tools/validate.py iso3166.json --only ground-truth
python3 tools/validate.py iso3166.json --skip cross-reference --skip coverage
python3 tools/validate.py iso3166.json --strict-count
```

| Layer | What it checks |
|-------|----------------|
| 1. Schema | JSON structure against `schema.json` |
| 2. Integrity | Format patterns, no empty strings, calendar-valid dates |
| 3. Business | Uniqueness, status consistency, withdrawal rules |
| 4. Cross-reference | `currency_codes` vs. ISO 4217 snapshot; `borders` and `replaced_by` resolvable within the registry |
| 5. Ground-truth | Codes-by-status vs. `tools/parse_source.py`'s frozen sets |
| 6. Coverage | `meta.count_*` vs. actual; `VERSION` vs. `meta.version` |

Exit codes: 0 pass, 1 data error, 2 usage, 3 schema violation.

### Cross-language verification

```bash
bash tools/check_cross_language.sh US GB JP TW XK UK
```

Runs the same lookup through all four wrappers, diffs the output
literally, and exits non-zero if any disagree. This is the executable
form of the ecosystem's central claim: the JSON is the contract.

---

## Versioning

Two version numbers, one source:

- **`VERSION`** — the registry data version. Single source of truth.
  **`meta.version`**, the README badge, and the Parquet footer must all
  match it. `tools/check_version_consistency.py` enforces this on every
  push.

The schema version lives independently in `schema.json`:
`$id` carries it, and it changes only when the format contract changes.

The registry follows [Semantic Versioning](https://semver.org/):

- **Major**: breaking schema changes (removed fields, renamed keys)
- **Minor**: new entries, new optional fields, new tooling
- **Patch**: data corrections

Wrapper package versions track the registry version.

---

## Consumed by

| Project | How it uses this registry |
|---------|---------------------------|
| [ISO 4217](https://github.com/slimissa/iso4217) | Cross-references country codes from currency `entity` fields |
| [Exchange Calendar](https://github.com/slimissa/exchange-calendar) | Exchange JSON carries a `country_code` referencing alpha-2 |
| [Corporate Actions](https://github.com/slimissa/corporate-actions) | Instrument entries reference the country of listing |
| [LAS_Shell](https://github.com/slimissa/Las_shell) | Reads country codes for market status and prompt display |
| [Tempus](https://github.com/slimissa/Tempus) | Planned compile-time `Country<ISO3166>` type validation |

*Using this registry in your project? Open a PR to add your name here.*

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). The short version:

1. Open an issue before starting large changes.
2. Data corrections go in `iso3166.json` with a first-party source cited.
3. Run `python3 tools/validate.py iso3166.json --strict-count` — must exit 0.
4. Run `bash tools/check_cross_language.sh US` — must exit 0.
5. Submit a PR. CI runs 14 jobs.

**No third-party sources.** Wikipedia, countrycode.org, aggregator CSVs
and blog posts are not acceptable as the origin of a field. If a value
can't be traced to ISO, the UN Statistics Division, IANA, or the ITU,
it stays `null`.

---

## License

Apache 2.0. See [LICENSE](./LICENSE).

The country data in this registry is factual information sourced from
public standards. The compilation, schema, tooling, wrappers, and
documentation are licensed works.

---

## Author

**Le P'tit** — [github.com/slimissa](https://github.com/slimissa)

---

## What's next

- **v1.1.0** — enrich `official_name`, complete the ISO 3166-3 withdrawn set.
- **v1.2.0** — populate `currency_codes`, `calling_codes`, `tlds`; publish to PyPI, npm, crates.io.
- **v1.3.0** — `languages` and `borders`, once a first-party source for adjacency is identified.

See [`CHANGELOG.md`](./CHANGELOG.md) and
[`docs/decisions/v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md).

