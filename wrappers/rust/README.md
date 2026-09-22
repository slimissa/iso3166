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

## Tests

```bash
cargo test
```

## License

Apache 2.0.