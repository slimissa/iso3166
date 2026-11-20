# iso3166-registry (Python)

Python wrapper for the [ISO 3166 country registry](https://github.com/slimissa/iso3166).

## Install

From the repository:

```bash
pip install -e wrappers/python
```

This installs the `iso3166` command and the `iso3166` importable
package.

Publication to PyPI is tracked for v1.2.0.

## Library

```python
from iso3166 import CountryRegistry

reg = CountryRegistry()

us = reg.active("US")
print(us.alpha_3, us.name)              # USA United States of America
print(reg.by_numeric("840").alpha_2)    # US
print(reg.by_alpha3("GBR").name)        # United Kingdom of Great Britain and Northern Ireland
print(reg.region("Europe")[0].alpha_2)  # AD (sorted by alpha_2)
print(len(reg.search("united")))        # multiple
print(reg.summary())
```

`active()` returns `None` for an unknown code. Use `with_alpha2()` to
retrieve both the active and withdrawn entries for a reassigned code
such as `AI` or `SK`.

## Derived queries (v1.10.0+)

The registry answers questions that need more than one entry: club membership, the region tree, land borders, succession, calling codes, currency and existence on a date. There are 17 queries, specified once in [docs/QUERIES.md](../../docs/QUERIES.md); this wrapper implements all of them, and `tools/check_cross_language.sh` checks the Python, JavaScript, Rust and Go wrappers and the CLI against the same 129 cases of `tests/cross_language_consistency.json`, so each answers the same question the same way.

| Query | Method | Since |
|-------|--------|-------|
| 1. `is_eu` | `reg.is_eu()` | v1.10.0 |
| 1. `is_eea` | `reg.is_eea()` | v1.10.0 |
| 1. `is_eurozone` | `reg.is_eurozone()` | v1.10.0 |
| 2. `region_tree` | `reg.region_tree()` | v1.10.0 |
| 8. `region_countries` | `reg.region_countries()` | v1.10.0 |
| 3. `borders_transitively` | `reg.borders_transitively()` | v1.10.0 |
| 4. `succession_path` | `reg.succession_path()` | v1.10.0 |
| 5. `successors` | `reg.successors()` | v1.10.0 |
| 5. `predecessors` | `reg.predecessors()` | v1.10.0 |
| 6. `calling_code_for` | `reg.calling_code_for()` | v1.10.0 |
| 7. `currency_at` | `reg.currency_at()` | v1.10.0 |
| 9. `is_active_on` | `reg.is_active_on()` | v1.11.0 |
| 11. `active_on` | `reg.active_on()` | v1.12.5 |
| 10. `is_eu_member_at` | `reg.is_eu_member_at()` | v1.12.0 |
| 10. `is_eea_member_at` | `reg.is_eea_member_at()` | v1.12.0 |
| 10. `is_eurozone_member_at` | `reg.is_eurozone_member_at()` | v1.12.0 |
| 10. `is_in_customs_union_at` | `reg.is_in_customs_union_at()` | v1.12.0 |

```python
from iso3166 import CountryRegistry

reg = CountryRegistry()

reg.is_eu("DE")                              # True   (current member only)
reg.region_tree("FR")                        # ['Europe', 'Western Europe']
reg.borders_transitively("US", 1)            # ['CA', 'MX']   (max_hops defaults to 2)
reg.succession_path("YU", "ME")              # ['YU', 'CS', 'ME']
reg.successors("YU")                         # ['CS', 'ME', 'RS']
reg.calling_code_for("+49")                  # ['DE']
reg.is_eu_member_at("GB", "2010-01-01")      # True
reg.is_eu_member_at("GB", "2023-01-01")      # False
reg.is_active_on("YU", "1990-01-01")         # True   (True / False / None: tri-state)
```

A malformed date (`"2010-13-45"`, `"2020-01-01\n"`) raises `ValueError` from
`is_active_on`, `active_on` and the four `*_member_at` queries; `currency_at`
answers `None`. A query with no answer returns `None` (`succession_path`,
`currency_at`) or an empty list; an unknown code never raises. The same
queries are on the command line (`iso3166 is-eu DE`, `iso3166 succession-path YU ME`).

## CLI

```bash
iso3166 lookup US
iso3166 list --region Europe
iso3166 info
iso3166 validate US FR DE
```

See the [top-level README](https://github.com/slimissa/iso3166) for the
full CLI reference.

## Tests

```bash
python3 -m pytest wrappers/python/tests/
```

## License

Apache 2.0.