//! Small binary for the Phase 6.6 cross-language spot check.
//!
//! ```text
//! cargo run --quiet --bin lookup US
//! # US USA 840 United States of America
//! ```

use std::process::ExitCode;

use iso3166_registry::CountryRegistry;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: lookup CODE");
        return ExitCode::from(2);
    }

    let reg = match CountryRegistry::load() {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: {}", e);
            return ExitCode::from(1);
        }
    };

    match reg.active(&args[1]) {
        Some(c) => {
            println!("{} {} {} {}", c.alpha_2, c.alpha_3, c.numeric, c.name);
            ExitCode::SUCCESS
        }
        None => {
            eprintln!("not found: {}", args[1]);
            ExitCode::from(1)
        }
    }
}
