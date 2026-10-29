//! Driver for the cross-language derived-query check (design in docs/QUERIES.md).
//!
//! ```text
//! cargo run --quiet --bin query is_eu DE        # true
//! cargo run --quiet --bin query region_countries Europe "Western Europe"
//! ```
//!
//! Prints the result as compact JSON (`null` for `None`). The method
//! names are the snake_case names used in the fixture.

use std::process::ExitCode;

use iso3166_registry::CountryRegistry;

fn json<T: serde::Serialize>(v: &T) -> String {
    serde_json::to_string(v).expect("serialize")
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: query METHOD ARG [ARG]");
        return ExitCode::from(2);
    }
    let reg = match CountryRegistry::load() {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: {}", e);
            return ExitCode::from(3);
        }
    };
    let a = |i: usize| args.get(i).map(String::as_str).unwrap_or("");
    let out = match args[1].as_str() {
        "is_eu" => json(&reg.is_eu(a(2))),
        "is_eea" => json(&reg.is_eea(a(2))),
        "is_eurozone" => json(&reg.is_eurozone(a(2))),
        "region_tree" => json(&reg.region_tree(a(2))),
        "borders_transitively" => match a(3).parse::<usize>() {
            Ok(n) => json(&reg.borders_transitively(a(2), n)),
            Err(_) => json(&Vec::<String>::new()),
        },
        "succession_path" => json(&reg.succession_path(a(2), a(3))),
        "successors" => json(&reg.successors(a(2))),
        "predecessors" => json(&reg.predecessors(a(2))),
        "calling_code_for" => json(&reg.calling_code_for(a(2))),
        "currency_at" => json(&reg.currency_at(a(2), a(3))),
        "is_active_on" => json(&reg.is_active_on(a(2), a(3))),
        "region_countries" => {
            let sub = if args.len() > 3 { Some(a(3)) } else { None };
            json(&reg.region_countries(a(2), sub))
        }
        other => {
            eprintln!("error: unknown query: {}", other);
            return ExitCode::from(2);
        }
    };
    println!("{}", out);
    ExitCode::SUCCESS
}
