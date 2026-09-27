//! Cross-language consistency tests.
//!
//! Reads `tests/cross_language_consistency.json` (three levels up from
//! this file) and asserts the Rust wrapper satisfies every case. The
//! same fixture is read by the Python, JavaScript, and Go suites.

use std::collections::HashMap;
use std::path::PathBuf;

use iso3166_registry::CountryRegistry;
use serde::Deserialize;

#[derive(Deserialize)]
struct LookupAlpha2 {
    input: String,
    alpha_2: String,
    alpha_3: String,
    numeric: String,
    name: String,
    status: String,
    independent: bool,
    region: Option<String>,
}

#[derive(Deserialize)]
struct LookupByCode {
    input: String,
    alpha_2: String,
}

#[derive(Deserialize)]
struct Counts {
    total: usize,
    active: usize,
    withdrawn: usize,
    by_status: HashMap<String, usize>,
}

#[derive(Deserialize)]
struct RegionCase {
    region: String,
    min_count: usize,
    must_contain: Vec<String>,
}

#[derive(Deserialize)]
struct SearchCase {
    query: String,
    min_count: usize,
    must_contain: Vec<String>,
}

#[derive(Deserialize)]
struct LookupWithdrawn {
    input: String,
    #[allow(dead_code)]
    alpha_2: String,
    name: String,
    #[allow(dead_code)]
    status: String,
    #[allow(dead_code)]
    withdrawal_date: Option<String>,
}

#[derive(Deserialize)]
struct LookupField {
    input: String,
    official_name: Option<String>,
    #[serde(default)]
    currency_codes: Vec<String>,
    #[serde(default)]
    calling_codes: Vec<String>,
    #[serde(default)]
    tlds: Vec<String>,
    #[serde(default)]
    #[allow(dead_code)]
    languages: Vec<String>,
    #[serde(default)]
    #[allow(dead_code)]
    borders: Vec<String>,
}

#[derive(Deserialize)]
struct Fixture {
    lookup_alpha2: Vec<LookupAlpha2>,
    lookup_alpha2_missing: Vec<String>,
    lookup_alpha3: Vec<LookupByCode>,
    lookup_numeric: Vec<LookupByCode>,
    counts: Counts,
    overlap_codes: HashMap<String, Vec<String>>,
    region_query: Vec<RegionCase>,
    currencies: HashMap<String, Vec<String>>,
    countries_with: HashMap<String, Vec<String>>,
    #[serde(default)]
    lookup_fields: Vec<LookupField>,
    #[serde(default)]
    lookup_withdrawn: Vec<LookupWithdrawn>,
    search: Vec<SearchCase>,
}

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("tests")
        .join("cross_language_consistency.json")
}

fn load_fixture() -> Fixture {
    let text = std::fs::read_to_string(fixture_path())
        .expect("read tests/cross_language_consistency.json");
    serde_json::from_str(&text).expect("parse fixture")
}

fn reg() -> CountryRegistry {
    CountryRegistry::load().expect("load bundled registry")
}

#[test]
fn lookup_alpha2() {
    let reg = reg();
    for c in load_fixture().lookup_alpha2 {
        let got = reg
            .active(&c.input)
            .unwrap_or_else(|| panic!("active({:?}) returned None", c.input));
        assert_eq!(got.alpha_2, c.alpha_2);
        assert_eq!(got.alpha_3, c.alpha_3);
        assert_eq!(got.numeric, c.numeric);
        assert_eq!(got.name, c.name);
        assert_eq!(got.status, c.status);
        assert_eq!(got.independent, c.independent);
        assert_eq!(got.region, c.region, "region mismatch for {}", c.input);
    }
}

#[test]
fn lookup_alpha2_missing() {
    let reg = reg();
    for code in load_fixture().lookup_alpha2_missing {
        assert!(
            reg.active(&code).is_none(),
            "active({:?}) should be None",
            code
        );
    }
}

#[test]
fn lookup_alpha3() {
    let reg = reg();
    for c in load_fixture().lookup_alpha3 {
        let got = reg
            .by_alpha3(&c.input)
            .unwrap_or_else(|| panic!("by_alpha3({:?}) returned None", c.input));
        assert_eq!(got.alpha_2, c.alpha_2);
    }
}

#[test]
fn lookup_numeric() {
    let reg = reg();
    for c in load_fixture().lookup_numeric {
        let got = reg
            .by_numeric(&c.input)
            .unwrap_or_else(|| panic!("by_numeric({:?}) returned None", c.input));
        assert_eq!(got.alpha_2, c.alpha_2);
    }
}

#[test]
fn counts() {
    let reg = reg();
    let fx = load_fixture();
    let s = reg.summary();
    assert_eq!(s.total, fx.counts.total);
    assert_eq!(s.active, fx.counts.active);
    assert_eq!(s.withdrawn, fx.counts.withdrawn);
    for (status, expected) in fx.counts.by_status {
        assert_eq!(
            s.by_status.get(&status).copied().unwrap_or(0),
            expected,
            "status {}: got {}, want {}",
            status,
            s.by_status.get(&status).copied().unwrap_or(0),
            expected
        );
    }
}

#[test]
fn overlap_codes() {
    let reg = reg();
    for (code, expected) in load_fixture().overlap_codes {
        let matches = reg.with_alpha2(&code);
        let mut got: Vec<String> = matches.iter().map(|m| m.status.clone()).collect();
        got.sort();
        let mut want = expected;
        want.sort();
        assert_eq!(got, want, "{}: status set mismatch", code);
    }
}

#[test]
fn region_query() {
    let reg = reg();
    for c in load_fixture().region_query {
        let results = reg.region(&c.region);
        assert!(
            results.len() >= c.min_count,
            "region {}: got {}, want >= {}",
            c.region,
            results.len(),
            c.min_count
        );
        let have: std::collections::HashSet<&str> =
            results.iter().map(|r| r.alpha_2.as_str()).collect();
        for code in &c.must_contain {
            assert!(
                have.contains(code.as_str()),
                "region {} missing {}",
                c.region,
                code
            );
        }
    }
}

#[test]
fn currencies() {
    let reg = reg();
    for (code, expected) in load_fixture().currencies {
        let got = reg.currencies(&code);
        assert_eq!(
            got.len(),
            expected.len(),
            "{}: got {:?}, want {:?}",
            code,
            got,
            expected
        );
    }
}

#[test]
fn countries_with() {
    let reg = reg();
    for (curr, expected) in load_fixture().countries_with {
        let got = reg.countries_with(&curr);
        assert_eq!(
            got.len(),
            expected.len(),
            "{}: got {} entries, want {}",
            curr,
            got.len(),
            expected.len()
        );
    }
}

#[test]
fn search() {
    let reg = reg();
    for c in load_fixture().search {
        let results = reg.search(&c.query);
        assert!(
            results.len() >= c.min_count,
            "search {:?}: got {}, want >= {}",
            c.query,
            results.len(),
            c.min_count
        );
        let have: std::collections::HashSet<&str> =
            results.iter().map(|r| r.alpha_2.as_str()).collect();
        for code in &c.must_contain {
            assert!(
                have.contains(code.as_str()),
                "search {:?} missing {}",
                c.query,
                code
            );
        }
    }
}

#[test]
fn lookup_withdrawn() {
    let reg = reg();
    for c in load_fixture().lookup_withdrawn {
        let matches = reg.with_alpha2(&c.input);
        let found = matches
            .iter()
            .any(|m| m.status == "withdrawn" && m.name == c.name);
        assert!(found, "{}: withdrawn entry not found", c.input);
    }
}

#[test]
fn lookup_fields() {
    let reg = reg();
    for c in load_fixture().lookup_fields {
        let got = reg
            .active(&c.input)
            .unwrap_or_else(|| panic!("{}: missing", c.input));
        assert_eq!(
            got.official_name.as_deref(),
            c.official_name.as_deref(),
            "{}: official_name mismatch",
            c.input
        );
        assert_eq!(
            got.currency_codes.clone().unwrap_or_default(),
            c.currency_codes,
            "{}: currency_codes mismatch",
            c.input
        );
        assert_eq!(
            got.calling_codes.clone().unwrap_or_default(),
            c.calling_codes,
            "{}: calling_codes mismatch",
            c.input
        );
        assert_eq!(
            got.tlds.clone().unwrap_or_default(),
            c.tlds,
            "{}: tlds mismatch",
            c.input
        );
    }
}
