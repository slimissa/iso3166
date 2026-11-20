# iso3166-registry (Rust)

Rust wrapper for the [ISO 3166 country registry](https://github.com/slimissa/iso3166).

## Install

Source-only until v1.2.0. From a checkout of this repository:

```toml
[dependencies]
iso3166-registry = { path = "path/to/wrappers/rust" }
```

Or vendor the `wrappers/rust` directory directly.

Publication to crates.io is tracked for v1.2.0.

## Library

```rust
use iso3166_registry::CountryRegistry;

fn main() {
    let reg = CountryRegistry::load().unwrap();

    if let Some(us) = reg.active("US") {
        println!("{} {}", us.alpha_3, us.name);   // USA United States of America
    }

    println!("{}", reg.by_numeric("840").unwrap().alpha_2);   // US
    println!("{}", reg.by_alpha3("GBR").unwrap().name);
    println!("{}", reg.region("Europe").len());
    println!("{}", reg.search("united").len());
    println!("{:?}", reg.summary());
}
```

`active()` returns `Option<&Country>`; use `with_alpha2()` to retrieve
both the active and withdrawn entries for a reassigned code such as
`AI` or `SK`.

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

```rust
use iso3166_registry::CountryRegistry;

fn main() {
    let reg = CountryRegistry::load().unwrap();

    assert!(reg.is_eu("DE"));                                   // current member only
    assert_eq!(reg.region_tree("FR"), ["Europe", "Western Europe"]);
    assert_eq!(reg.borders_transitively("US", 1), ["CA", "MX"]); // max_hops is required
    assert_eq!(reg.succession_path("YU", "ME"), Some(vec!["YU".into(), "CS".into(), "ME".into()]));
    assert_eq!(reg.successors("YU"), ["CS", "ME", "RS"]);
    assert_eq!(reg.calling_code_for("+49"), ["DE"]);
    assert_eq!(reg.is_eu_member_at("GB", "2010-01-01"), Ok(true));
    assert_eq!(reg.is_eu_member_at("GB", "2023-01-01"), Ok(false));
    assert_eq!(reg.is_active_on("YU", "1990-01-01"), Ok(Some(true)));  // Some(true) / Some(false) / None
}
```

A malformed date is `Err(InvalidDate)` from `is_active_on`, `active_on` and the
four `*_member_at` queries; `currency_at` answers `None`. `is_valid_date(s)` is
public, so a caller can check a date first. A query with no answer returns
`None` (`succession_path`, `currency_at`) or an empty `Vec`; an unknown code
never fails. `Country`, `Meta` and `Summary` are `#[non_exhaustive]`.

## Tests

```bash
cargo test
```

## License

Apache 2.0.