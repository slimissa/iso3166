//! # iso3166-registry
//!
//! Rust wrapper for the [ISO 3166 country registry].
//!
//! ```
//! use iso3166_registry::CountryRegistry;
//!
//! let reg = CountryRegistry::load().unwrap();
//! if let Some(us) = reg.active("US") {
//!     println!("{} {}", us.alpha_3, us.name);
//! }
//! ```
//!
//! The registry JSON is embedded in the binary with `include_str!`, so
//! [`CountryRegistry::load`] never touches the filesystem. To read a
//! different file, use [`CountryRegistry::load_from`].
//!
//! Every lookup returns `Option<&Country>` or a (possibly empty)
//! borrowed slice; only `load` and `load_from` return a `Result`. This
//! mirrors the Python, JavaScript, and Go wrappers, whose cross-language
//! contract is checked against the same fixture
//! (`tests/cross_language_consistency.json`).
//!
//! [ISO 3166 country registry]: https://github.com/slimissa/iso3166

use std::fmt;
use std::path::Path;

use serde::Deserialize;

/// The bundled registry, embedded at compile time.
const BUNDLED_REGISTRY: &str = include_str!("../iso3166.json");

const ACTIVE_STATUSES: &[&str] = &[
    "officially-assigned",
    "user-assigned",
    "exceptionally-reserved",
];

/// The 27 EU member states at v1.9.3. Deprecated since v1.12.0 and no
/// longer consulted: `is_eu`, `is_eea` and `is_eurozone` read the
/// date-scoped membership arrays. Kept so existing imports compile; it
/// is a frozen snapshot and is not updated.
pub const KNOWN_EU_MEMBERS: [&str; 27] = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
    "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
];

/// EEA members that are not EU members (same status as
/// [`KNOWN_EU_MEMBERS`]).
pub const EEA_NON_EU: [&str; 3] = ["IS", "LI", "NO"];

/// One inclusive club-membership range (v1.12.0): `from` is the first
/// day of membership and `to` the last day, or `None` while the entry is
/// still a member. Not part of the public API: the queries return bools.
#[derive(Debug, Clone, Deserialize)]
pub(crate) struct MembershipRange {
    pub(crate) from: String,
    #[serde(default)]
    pub(crate) to: Option<String>,
}

fn dq_norm(code: &str) -> String {
    code.trim().to_uppercase()
}

/// True for a real calendar date written as YYYY-MM-DD, year >= 1.
fn dq_valid_date(s: &str) -> bool {
    let b = s.as_bytes();
    if b.len() != 10 || b[4] != b'-' || b[7] != b'-' {
        return false;
    }
    if !b.iter().enumerate().all(|(i, c)| i == 4 || i == 7 || c.is_ascii_digit()) {
        return false;
    }
    let y: u32 = s[0..4].parse().unwrap_or(0);
    let m: u32 = s[5..7].parse().unwrap_or(0);
    let d: u32 = s[8..10].parse().unwrap_or(0);
    if y < 1 || !(1..=12).contains(&m) || d < 1 {
        return false;
    }
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let dim = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][(m - 1) as usize];
    d <= dim
}

// ============================================================
// Errors
// ============================================================

/// Errors returned by [`CountryRegistry::load`] and
/// [`CountryRegistry::load_from`].
#[derive(Debug)]
pub enum RegistryError {
    /// The file could not be read.
    Io(std::io::Error),
    /// The file exists but is not valid JSON, or is missing required
    /// structure.
    Parse(serde_json::Error),
}

impl fmt::Display for RegistryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            RegistryError::Io(e) => write!(f, "registry IO error: {}", e),
            RegistryError::Parse(e) => write!(f, "registry parse error: {}", e),
        }
    }
}

impl std::error::Error for RegistryError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            RegistryError::Io(e) => Some(e),
            RegistryError::Parse(e) => Some(e),
        }
    }
}

impl From<std::io::Error> for RegistryError {
    fn from(e: std::io::Error) -> Self {
        RegistryError::Io(e)
    }
}

impl From<serde_json::Error> for RegistryError {
    fn from(e: serde_json::Error) -> Self {
        RegistryError::Parse(e)
    }
}

// ============================================================
// Data types
// ============================================================

/// One entry from the registry.
///
/// The optional fields are `Option<String>` / `Option<Vec<String>>` and
/// are `None` when the registry entry has no value.
#[derive(Debug, Clone, Deserialize)]
pub struct Country {
    pub alpha_2: String,
    pub alpha_3: String,
    pub numeric: String,
    pub name: String,
    pub status: String,
    pub independent: bool,
    #[serde(default)]
    pub official_name: Option<String>,
    #[serde(default)]
    pub region: Option<String>,
    #[serde(default)]
    pub subregion: Option<String>,
    #[serde(default)]
    pub intermediate_region: Option<String>,
    #[serde(default)]
    pub currency_codes: Option<Vec<String>>,
    #[serde(default)]
    pub calling_codes: Option<Vec<String>>,
    #[serde(default)]
    pub tlds: Option<Vec<String>>,
    #[serde(default)]
    pub languages: Option<Vec<String>>,
    #[serde(default)]
    pub borders: Option<Vec<String>>,
    #[serde(default)]
    pub note: Option<String>,
    #[serde(default)]
    pub last_verified: Option<String>,
    #[serde(default)]
    pub withdrawal_date: Option<String>,
    #[serde(default)]
    pub replaced_by: Option<Vec<String>>,
    #[serde(default)]
    pub introduced: Option<String>,
    // v1.12.0 club memberships (active entries only; absent = empty).
    #[serde(default)]
    pub(crate) eu_membership: Vec<MembershipRange>,
    #[serde(default)]
    pub(crate) eea_membership: Vec<MembershipRange>,
    #[serde(default)]
    pub(crate) eurozone_membership: Vec<MembershipRange>,
    #[serde(default)]
    pub(crate) customs_union: Vec<MembershipRange>,
}

impl Country {
    /// True if the entry's status is one of the three active statuses.
    pub fn is_active(&self) -> bool {
        ACTIVE_STATUSES.contains(&self.status.as_str())
    }
}

/// The registry's `meta` block.
#[derive(Debug, Clone, Deserialize)]
pub struct Meta {
    pub version: String,
    pub updated: String,
    #[serde(default)]
    pub source: Option<String>,
    #[serde(default)]
    pub schema_version: Option<String>,
    #[serde(default)]
    pub count_active: Option<u64>,
    #[serde(default)]
    pub count_withdrawn: Option<u64>,
}

/// Summary returned by [`CountryRegistry::summary`].
#[derive(Debug, Clone)]
pub struct Summary {
    pub version: String,
    pub updated: String,
    pub total: usize,
    pub active: usize,
    pub withdrawn: usize,
    pub by_status: std::collections::BTreeMap<String, usize>,
}

#[derive(Debug, Deserialize)]
struct RegistryFile {
    meta: Meta,
    countries: CountriesSection,
}

#[derive(Debug, Deserialize)]
struct CountriesSection {
    #[serde(default)]
    active: Vec<Country>,
    #[serde(default)]
    withdrawn: Vec<Country>,
}

// ============================================================
// Helpers
// ============================================================

/// Left-pad a numeric code to three digits. Returns `None` for `""` and
/// for the sentinel `"000"` (so `"0"` is rejected too). Whitespace is
/// not trimmed.
fn pad_numeric(numeric: &str) -> Option<String> {
    if numeric.is_empty() {
        return None;
    }
    let padded = format!("{:0>3}", numeric);
    if padded == "000" {
        None
    } else {
        Some(padded)
    }
}

// ============================================================
// Registry
// ============================================================

/// An immutable view of the registry. Cheap to query; holds all
/// entries in memory.
///
/// All lookup methods return borrowed data tied to the registry's
/// lifetime. `CountryRegistry` is `Send + Sync` and safe to share
/// across threads for concurrent reads.
pub struct CountryRegistry {
    meta: Meta,
    active: Vec<Country>,
    withdrawn: Vec<Country>,
    // Indices into `active` for fast lookups.
    by_alpha2: std::collections::HashMap<String, usize>,
    by_alpha3: std::collections::HashMap<String, usize>,
    by_numeric: std::collections::HashMap<String, usize>,
    // For AI/SK, the withdrawn entry lives in `withdrawn`. We track the
    // active index for the simple lookups and search both vectors for
    // `with_alpha2`.
}

impl CountryRegistry {
    /// Load the registry embedded in the binary.
    pub fn load() -> Result<Self, RegistryError> {
        Self::from_str(BUNDLED_REGISTRY)
    }

    /// Load the registry from a file.
    pub fn load_from(path: impl AsRef<Path>) -> Result<Self, RegistryError> {
        let text = std::fs::read_to_string(path)?;
        Self::from_str(&text)
    }

    fn from_str(text: &str) -> Result<Self, RegistryError> {
        let file: RegistryFile = serde_json::from_str(text)?;

        let mut by_alpha2 = std::collections::HashMap::with_capacity(file.countries.active.len());
        let mut by_alpha3 = std::collections::HashMap::with_capacity(file.countries.active.len());
        let mut by_numeric = std::collections::HashMap::with_capacity(file.countries.active.len());

        for (i, c) in file.countries.active.iter().enumerate() {
            by_alpha2.insert(c.alpha_2.clone(), i);
            by_alpha3.insert(c.alpha_3.clone(), i);
            // "000" is a placeholder shared by several entries (XK, EU,
            // UK, ...); it is never a valid key.
            if c.numeric != "000" {
                by_numeric.insert(c.numeric.clone(), i);
            }
        }

        Ok(CountryRegistry {
            meta: file.meta,
            active: file.countries.active,
            withdrawn: file.countries.withdrawn,
            by_alpha2,
            by_alpha3,
            by_numeric,
        })
    }

    // ------------------------------------------------------------
    // Metadata
    // ------------------------------------------------------------

    pub fn meta(&self) -> &Meta {
        &self.meta
    }

    pub fn version(&self) -> &str {
        &self.meta.version
    }

    pub fn updated(&self) -> &str {
        &self.meta.updated
    }

    // ------------------------------------------------------------
    // Collections
    // ------------------------------------------------------------

    /// Every active entry, in registry order.
    pub fn all_active(&self) -> &[Country] {
        &self.active
    }

    /// Every withdrawn entry, in registry order.
    pub fn all_withdrawn(&self) -> &[Country] {
        &self.withdrawn
    }

    // ------------------------------------------------------------
    // Lookup
    // ------------------------------------------------------------

    /// Look up an alpha-2 code. Case-insensitive. Returns `None` if
    /// absent. Only active entries; withdrawn codes are reachable via
    /// [`with_alpha2`](Self::with_alpha2).
    pub fn active(&self, alpha_2: &str) -> Option<&Country> {
        if alpha_2.is_empty() {
            return None;
        }
        let key = alpha_2.to_ascii_uppercase();
        self.by_alpha2.get(&key).map(|&i| &self.active[i])
    }

    /// Alias for [`active`](Self::active).
    pub fn by_alpha2(&self, alpha_2: &str) -> Option<&Country> {
        self.active(alpha_2)
    }

    /// All entries (active and withdrawn) with this alpha-2 code. A
    /// small number of codes appear twice because ISO reassigned them
    /// (AI, SK); the active entry comes first.
    pub fn with_alpha2(&self, alpha_2: &str) -> Vec<&Country> {
        if alpha_2.is_empty() {
            return Vec::new();
        }
        let key = alpha_2.to_ascii_uppercase();
        let mut out = Vec::new();
        for c in &self.active {
            if c.alpha_2 == key {
                out.push(c);
            }
        }
        for c in &self.withdrawn {
            if c.alpha_2 == key {
                out.push(c);
            }
        }
        out
    }

    /// All entries (active and withdrawn) with this alpha-3 code.
    /// Case-insensitive.
    pub fn with_alpha3(&self, alpha_3: &str) -> Vec<&Country> {
        if alpha_3.is_empty() {
            return Vec::new();
        }
        let key = alpha_3.to_ascii_uppercase();
        self.active
            .iter()
            .chain(self.withdrawn.iter())
            .filter(|c| c.alpha_3 == key)
            .collect()
    }

    /// All entries (active and withdrawn) with this numeric code.
    /// Zero-padded like [`by_numeric`](Self::by_numeric); the sentinel
    /// `"000"` matches nothing.
    pub fn with_numeric(&self, numeric: &str) -> Vec<&Country> {
        match pad_numeric(numeric) {
            None => Vec::new(),
            Some(padded) => self
                .active
                .iter()
                .chain(self.withdrawn.iter())
                .filter(|c| c.numeric == padded)
                .collect(),
        }
    }

    /// Look up an alpha-3 code. Case-insensitive. Returns `None` if
    /// absent or empty.
    pub fn by_alpha3(&self, alpha_3: &str) -> Option<&Country> {
        if alpha_3.is_empty() {
            return None;
        }
        let key = alpha_3.to_ascii_uppercase();
        self.by_alpha3.get(&key).map(|&i| &self.active[i])
    }

    /// Look up a numeric code. The argument is zero-padded to three
    /// digits, so `"20"` and `"020"` are equivalent. `""`, `"0"` and
    /// `"000"` return `None`, and whitespace is not trimmed.
    pub fn by_numeric(&self, numeric: &str) -> Option<&Country> {
        let padded = pad_numeric(numeric)?;
        self.by_numeric.get(&padded).map(|&i| &self.active[i])
    }

    // ------------------------------------------------------------
    // Queries
    // ------------------------------------------------------------

    /// Currency codes in circulation in a country. Empty if the country
    /// is unknown or has none.
    pub fn currencies(&self, alpha_2: &str) -> &[String] {
        match self
            .active(alpha_2)
            .and_then(|c| c.currency_codes.as_deref())
        {
            Some(v) => v,
            None => &[],
        }
    }

    /// Active countries where a currency circulates.
    pub fn countries_with(&self, currency_code: &str) -> Vec<&Country> {
        if currency_code.is_empty() {
            return Vec::new();
        }
        let target = currency_code.to_ascii_uppercase();
        self.active
            .iter()
            .filter(|c| {
                c.currency_codes
                    .as_ref()
                    .is_some_and(|v| v.iter().any(|x| x == &target))
            })
            .collect()
    }

    /// Active countries in a macro-region. Case-insensitive.
    pub fn region(&self, region_name: &str) -> Vec<&Country> {
        if region_name.is_empty() {
            return Vec::new();
        }
        let target = region_name.to_ascii_lowercase();
        self.active
            .iter()
            .filter(|c| {
                c.region
                    .as_ref()
                    .is_some_and(|r| r.to_ascii_lowercase() == target)
            })
            .collect()
    }

    /// Active countries in a sub-region. Case-insensitive.
    pub fn subregion(&self, subregion_name: &str) -> Vec<&Country> {
        if subregion_name.is_empty() {
            return Vec::new();
        }
        let target = subregion_name.to_ascii_lowercase();
        self.active
            .iter()
            .filter(|c| {
                c.subregion
                    .as_ref()
                    .is_some_and(|r| r.to_ascii_lowercase() == target)
            })
            .collect()
    }

    /// Case-insensitive substring search on name, official_name,
    /// alpha_2, and alpha_3. Searches both active and withdrawn.
    pub fn search(&self, query: &str) -> Vec<&Country> {
        if query.is_empty() {
            return Vec::new();
        }
        let q = query.to_ascii_lowercase();
        let mut out = Vec::new();
        for c in self.active.iter().chain(self.withdrawn.iter()) {
            let mut haystack = c.name.to_ascii_lowercase();
            if let Some(o) = &c.official_name {
                haystack.push(' ');
                haystack.push_str(&o.to_ascii_lowercase());
            }
            haystack.push(' ');
            haystack.push_str(&c.alpha_2.to_ascii_lowercase());
            haystack.push(' ');
            haystack.push_str(&c.alpha_3.to_ascii_lowercase());
            if haystack.contains(&q) {
                out.push(c);
            }
        }
        out
    }

    // ------------------------------------------------------------
    // Summary
    // ------------------------------------------------------------

    pub fn summary(&self) -> Summary {
        let mut by_status = std::collections::BTreeMap::new();
        for c in self.active.iter().chain(self.withdrawn.iter()) {
            *by_status.entry(c.status.clone()).or_insert(0) += 1;
        }
        Summary {
            version: self.meta.version.clone(),
            updated: self.meta.updated.clone(),
            total: self.active.len() + self.withdrawn.len(),
            active: self.active.len(),
            withdrawn: self.withdrawn.len(),
            by_status,
        }
    }

    // ------------------------------------------------------------
    // Derived queries (v1.10.0 — design in docs/QUERIES.md)
    //
    // docs/QUERIES.md is the contract; each method names its section.
    //
    // Mirrors wrappers/python/iso3166/derived.py. Unknown codes are not
    // errors: bool queries return false, list queries return an empty
    // Vec, optional queries return None. Active entries win over
    // withdrawn ones (AI and SK exist twice); the succession graph is
    // built from withdrawn entries only.
    //
    // is_eu, is_eea, is_eurozone are current-status aliases since v1.12.0;
    // the *_at club queries are exact (docs/QUERIES.md, "Query 10").
    // currency_at (v1.11.1) is bounded by the entry's lifetime but
    // returns current currencies: the tree stores no currency history.
    // ------------------------------------------------------------

    fn dq_entry(&self, code: &str) -> Option<&Country> {
        let c = dq_norm(code);
        if c.is_empty() {
            return None;
        }
        if let Some(&i) = self.by_alpha2.get(&c) {
            return Some(&self.active[i]);
        }
        self.withdrawn.iter().find(|w| w.alpha_2 == c)
    }

    fn dq_edges(&self) -> std::collections::HashMap<&str, Vec<&str>> {
        let mut m = std::collections::HashMap::new();
        for w in &self.withdrawn {
            if let Some(rb) = &w.replaced_by {
                if !rb.is_empty() {
                    m.insert(w.alpha_2.as_str(), rb.iter().map(String::as_str).collect());
                }
            }
        }
        m
    }

    fn dq_closure(
        start: &str,
        edges: &std::collections::HashMap<&str, Vec<&str>>,
    ) -> Vec<String> {
        let mut seen: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        let mut stack = vec![start.to_string()];
        while let Some(cur) = stack.pop() {
            if let Some(next) = edges.get(cur.as_str()) {
                for n in next {
                    if *n != start && seen.insert((*n).to_string()) {
                        stack.push((*n).to_string());
                    }
                }
            }
        }
        seen.into_iter().collect()
    }

    /// Ranges of one club for an active entry; empty for any other code.
    fn club_ranges(
        &self,
        pick: fn(&Country) -> &[MembershipRange],
        code: &str,
    ) -> &[MembershipRange] {
        match self.by_alpha2.get(&dq_norm(code)) {
            Some(&i) => pick(&self.active[i]),
            None => &[],
        }
    }

    /// `from <= date <= to` for some range (`to` None = open-ended). A
    /// malformed date, an unknown code or a code in no range is false.
    fn club_at(
        &self,
        pick: fn(&Country) -> &[MembershipRange],
        code: &str,
        date: &str,
    ) -> bool {
        if !dq_valid_date(date) {
            return false;
        }
        self.club_ranges(pick, code).iter().any(|r| {
            r.from.as_str() <= date
                && match r.to.as_deref() {
                    None => true,
                    Some(to) => date <= to,
                }
        })
    }

    /// Current member: some range is open-ended.
    fn club_now(&self, pick: fn(&Country) -> &[MembershipRange], code: &str) -> bool {
        self.club_ranges(pick, code).iter().any(|r| r.to.is_none())
    }

    /// True if `code` is an EU member state today (its `eu_membership`
    /// array has an open-ended range). Current-status alias; see
    /// [`is_eu_member_at`](Self::is_eu_member_at) for date-scoped
    /// membership. See docs/QUERIES.md, "Query 1".
    pub fn is_eu(&self, code: &str) -> bool {
        self.club_now(|c| &c.eu_membership, code)
    }

    /// True if `code` is a party to the EEA Agreement today. Current-status
    /// alias; see [`is_eea_member_at`](Self::is_eea_member_at).
    /// See docs/QUERIES.md, "Query 1".
    pub fn is_eea(&self, code: &str) -> bool {
        self.club_now(|c| &c.eea_membership, code)
    }

    /// True if `code` is in the eurozone today. Euro users that are not
    /// members (AD, MC, SM, VA, ME, XK) and overseas codes (GF, GP, MQ, RE,
    /// YT, AX, ...) are false. Current-status alias; see
    /// [`is_eurozone_member_at`](Self::is_eurozone_member_at).
    /// See docs/QUERIES.md, "Query 1".
    pub fn is_eurozone(&self, code: &str) -> bool {
        self.club_now(|c| &c.eurozone_membership, code)
    }

    /// Was `code` an EU member state on `date`? Founders count from
    /// 1958-01-01 (the EEC). Both ends of a range are inclusive, so GB is
    /// a member on 2020-01-31 and not on 2020-02-01. A malformed date, an
    /// unknown code, or a code in no range is `false`; the answer is
    /// never unknown. See docs/QUERIES.md, "Query 10".
    pub fn is_eu_member_at(&self, code: &str, date: &str) -> bool {
        self.club_at(|c| &c.eu_membership, code, date)
    }

    /// Was `code` a party to the EEA Agreement on `date`, formally or
    /// provisionally? True from the first day the EEA Enlargement Agreement
    /// applied provisionally (2004-05-01 for the 2004 ten, 2007-08-01 for BG
    /// and RO); HR has formal dates only.
    /// See docs/QUERIES.md, "Query 10".
    pub fn is_eea_member_at(&self, code: &str, date: &str) -> bool {
        self.club_at(|c| &c.eea_membership, code, date)
    }

    /// Was `code` in the eurozone on `date`? Members count from 1 January
    /// of their adoption year. See docs/QUERIES.md, "Query 10".
    pub fn is_eurozone_member_at(&self, code: &str, date: &str) -> bool {
        self.club_at(|c| &c.eurozone_membership, code, date)
    }

    /// Was `code` in the EU customs union on `date`? AD and TR cover
    /// industrial goods only (scope is in the snapshot meta).
    /// See docs/QUERIES.md, "Query 10".
    pub fn is_in_customs_union_at(&self, code: &str, date: &str) -> bool {
        self.club_at(|c| &c.customs_union, code, date)
    }

    /// `[region, subregion, intermediate_region]` with nulls dropped.
    /// See docs/QUERIES.md, "Query 2".
    pub fn region_tree(&self, code: &str) -> Vec<String> {
        match self.dq_entry(code) {
            None => Vec::new(),
            Some(e) => [&e.region, &e.subregion, &e.intermediate_region]
                .into_iter()
                .filter_map(|v| v.as_ref())
                .filter(|v| !v.is_empty())
                .cloned()
                .collect(),
        }
    }

    /// Sorted codes within `max_hops` of `code` through `borders`,
    /// excluding `code` itself. See docs/QUERIES.md, "Query 3".
    pub fn borders_transitively(&self, code: &str, max_hops: usize) -> Vec<String> {
        let start = dq_norm(code);
        if start.is_empty() || max_hops < 1 || self.dq_entry(&start).is_none() {
            return Vec::new();
        }
        let mut seen: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        seen.insert(start.clone());
        let mut frontier = vec![start.clone()];
        for _ in 0..max_hops {
            let mut next = Vec::new();
            for cur in &frontier {
                if let Some(&i) = self.by_alpha2.get(cur) {
                    for b in self.active[i].borders.iter().flatten() {
                        if seen.insert(b.clone()) {
                            next.push(b.clone());
                        }
                    }
                }
            }
            if next.is_empty() {
                break;
            }
            frontier = next;
        }
        seen.remove(&start);
        seen.into_iter().collect()
    }

    /// Shortest `replaced_by` path, both endpoints included, or `None`.
    /// See docs/QUERIES.md, "Query 4".
    pub fn succession_path(&self, from: &str, to: &str) -> Option<Vec<String>> {
        let a = dq_norm(from);
        let b = dq_norm(to);
        self.dq_entry(&a)?;
        self.dq_entry(&b)?;
        if a == b {
            return Some(vec![a]);
        }
        let edges = self.dq_edges();
        let mut prev: std::collections::HashMap<String, Option<String>> =
            std::collections::HashMap::new();
        prev.insert(a.clone(), None);
        let mut q = std::collections::VecDeque::new();
        q.push_back(a);
        while let Some(cur) = q.pop_front() {
            if let Some(next) = edges.get(cur.as_str()) {
                for n in next {
                    if prev.contains_key(*n) {
                        continue;
                    }
                    prev.insert((*n).to_string(), Some(cur.clone()));
                    if *n == b {
                        let mut path = vec![b.clone()];
                        while let Some(Some(p)) = prev.get(path.last().unwrap()) {
                            path.push(p.clone());
                        }
                        path.reverse();
                        return Some(path);
                    }
                    q.push_back((*n).to_string());
                }
            }
        }
        None
    }

    /// Returns all descendants: the transitive closure of `replaced_by`,
    /// intermediate codes included, excluding `code`, sorted. The CLI
    /// returns the same set. See docs/QUERIES.md, "Query 5".
    pub fn successors(&self, code: &str) -> Vec<String> {
        let c = dq_norm(code);
        if c.is_empty() {
            return Vec::new();
        }
        Self::dq_closure(&c, &self.dq_edges())
    }

    /// Returns all ancestors: every withdrawn code from which `code` is
    /// reachable through `replaced_by`, sorted. See docs/QUERIES.md,
    /// "Query 5".
    pub fn predecessors(&self, code: &str) -> Vec<String> {
        let c = dq_norm(code);
        if c.is_empty() {
            return Vec::new();
        }
        let mut rev: std::collections::HashMap<&str, Vec<&str>> = std::collections::HashMap::new();
        for (src, dsts) in self.dq_edges() {
            for d in dsts {
                rev.entry(d).or_default().push(src);
            }
        }
        Self::dq_closure(&c, &rev)
    }

    /// Sorted codes whose `calling_codes` is a prefix of the number's
    /// digits. Country level only: "+44" returns GB, GG, IM and JE, and
    /// "+1" returns every NANP entry. See docs/QUERIES.md, "Query 6".
    pub fn calling_code_for(&self, number: &str) -> Vec<String> {
        let digits: String = number
            .chars()
            .filter(|ch| !matches!(ch, ' ' | '-' | '(' | ')' | '.' | '+'))
            .collect();
        if digits.is_empty() || !digits.chars().all(|ch| ch.is_ascii_digit()) {
            return Vec::new();
        }
        let mut out: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        for e in &self.active {
            for cc in e.calling_codes.iter().flatten() {
                if digits.starts_with(cc.as_str()) {
                    out.insert(e.alpha_2.clone());
                }
            }
        }
        out.into_iter().collect()
    }

    /// Currency in force on `date` (YYYY-MM-DD), bounded by the entry's
    /// lifetime. The tree stores no currency history, so the list is the
    /// entry's current `currency_codes`.
    ///
    /// Active with `introduced`: `None` before it, else `currency_codes`
    /// (DE in 1990 returns `["EUR"]`, not DEM). Active without
    /// `introduced` (source silent): `None`. Withdrawn: `None` after
    /// `withdrawal_date` (or before a known `introduced`), else the
    /// union of the terminal successors' current currencies. For
    /// withdrawn entries, returns the successor's current currency; the
    /// withdrawn entry's historical currency is not in the tree. For
    /// null `introduced` (all 25) it may differ from the withdrawn
    /// entry's historical currency. `None` means "cannot answer".
    /// See docs/QUERIES.md, "Query 7".
    pub fn currency_at(&self, code: &str, date: &str) -> Option<Vec<String>> {
        if !dq_valid_date(date) {
            return None;
        }
        let c = dq_norm(code);
        if let Some(&i) = self.by_alpha2.get(&c) {
            let e = &self.active[i];
            return match e.introduced.as_deref() {
                Some(intro) if date >= intro => e.currency_codes.clone(),
                _ => None,
            };
        }
        let wd = self.withdrawn.iter().find(|w| w.alpha_2 == c)?;
        match &wd.withdrawal_date {
            Some(d) if date <= d.as_str() => {}
            _ => return None,
        }
        if let Some(intro) = wd.introduced.as_deref() {
            if date < intro {
                return None;
            }
        }
        let edges = self.dq_edges();
        let mut out: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
        let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
        let mut stack = vec![c];
        while let Some(cur) = stack.pop() {
            if !seen.insert(cur.clone()) {
                continue;
            }
            if let Some(&i) = self.by_alpha2.get(&cur) {
                out.extend(self.active[i].currency_codes.iter().flatten().cloned());
            } else if let Some(next) = edges.get(cur.as_str()) {
                stack.extend(next.iter().map(|s| s.to_string()));
            }
        }
        if out.is_empty() {
            None
        } else {
            Some(out.into_iter().collect())
        }
    }

    /// Was `code` an assigned ISO 3166-1 code on `date` (YYYY-MM-DD)?
    ///
    /// Tri-state: `Some(false)` for a malformed date, an unknown code, a
    /// date before `introduced`, or a date after a withdrawn entry's
    /// `withdrawal_date`; `Some(true)` when the code was in force;
    /// `None` (unknown) for an active entry whose `introduced` is null.
    /// Active entries are resolved first (AI and SK exist twice). A
    /// withdrawn entry has no sourced start date: `false` after
    /// `withdrawal_date`, `None` before 1974-01-01 (ISO 3166 did not
    /// exist), and `true` from 1974-01-01 up to and including
    /// `withdrawal_date`.
    ///
    /// `is_active_on("DE", "1990-01-01")` is `Some(true)`,
    /// `is_active_on("DE", "1970-01-01")` is `Some(false)` and
    /// `is_active_on("BJ", "2000-01-01")` is `None`, and so is
    /// `is_active_on("DD", "1800-01-01")` (before 1974).
    /// See docs/QUERIES.md, "Query 9".
    pub fn is_active_on(&self, code: &str, date: &str) -> Option<bool> {
        if !dq_valid_date(date) {
            return Some(false);
        }
        let c = dq_norm(code);
        if let Some(&i) = self.by_alpha2.get(&c) {
            return self.active[i]
                .introduced
                .as_deref()
                .map(|intro| date >= intro);
        }
        let wd = match self.withdrawn.iter().find(|w| w.alpha_2 == c) {
            Some(w) => w,
            None => return Some(false),
        };
        let end = match wd.withdrawal_date.as_deref() {
            Some(d) => d,
            None => return Some(false),
        };
        if date > end {
            return Some(false);
        }
        match wd.introduced.as_deref() {
            Some(intro) => Some(intro <= date),
            // Start unknown: ISO 3166 began in 1974, nothing earlier is known.
            None if date < "1974-01-01" => None,
            None => Some(true),
        }
    }

    /// Sorted active codes in `region` (and `subregion`). Case-insensitive.
    /// See docs/QUERIES.md, "Query 8".
    pub fn region_countries(&self, region: &str, subregion: Option<&str>) -> Vec<String> {
        if region.is_empty() {
            return Vec::new();
        }
        let r = region.to_lowercase();
        let s = subregion.filter(|s| !s.is_empty()).map(str::to_lowercase);
        let mut out: Vec<String> = self
            .active
            .iter()
            .filter(|e| e.region.as_deref().unwrap_or("").to_lowercase() == r)
            .filter(|e| match &s {
                None => true,
                Some(s) => e.subregion.as_deref().unwrap_or("").to_lowercase() == *s,
            })
            .map(|e| e.alpha_2.clone())
            .collect();
        out.sort();
        out
    }
}

#[cfg(test)]
mod tests {
    //! Wrapper-local input-contract tests. They do not read the shared
    //! fixture, so they run unconditionally.
    use super::*;

    fn reg() -> CountryRegistry {
        CountryRegistry::load().expect("load bundled registry")
    }

    #[test]
    fn by_numeric_sentinel_empty_and_whitespace() {
        let r = reg();
        for v in ["", "000", "0", " 20", "020 ", "530"] {
            assert!(r.by_numeric(v).is_none(), "by_numeric({:?})", v);
        }
        assert_eq!(r.by_numeric("20").unwrap().alpha_2, "AD");
        assert_eq!(r.by_numeric("020").unwrap().alpha_2, "AD");
    }

    #[test]
    fn empty_string_lookups_and_queries() {
        let r = reg();
        assert!(r.active("").is_none());
        assert!(r.by_alpha2("").is_none());
        assert!(r.by_alpha3("").is_none());
        assert!(r.region("").is_empty());
        assert!(r.subregion("").is_empty());
        assert!(r.search("").is_empty());
        assert!(r.countries_with("").is_empty());
        assert!(r.with_alpha2("").is_empty());
        assert!(r.with_alpha3("").is_empty());
        assert!(r.with_numeric("").is_empty());
    }

    #[test]
    fn withdrawn_symmetry() {
        let r = reg();
        assert!(r.by_alpha3("ANT").is_none());
        assert!(r.by_numeric("530").is_none());
        let a3: Vec<&str> = r.with_alpha3("ant").iter().map(|c| c.alpha_2.as_str()).collect();
        assert_eq!(a3, vec!["AN"]);
        let num: Vec<&str> = r.with_numeric("530").iter().map(|c| c.alpha_2.as_str()).collect();
        assert_eq!(num, vec!["AN"]);
        assert!(r.with_numeric("000").is_empty());
    }

    #[test]
    fn with_alpha2_lists_active_first() {
        let r = reg();
        for code in ["AI", "SK"] {
            let flags: Vec<bool> = r.with_alpha2(code).iter().map(|c| c.is_active()).collect();
            assert_eq!(flags, vec![true, false], "{}", code);
        }
    }
    #[test]
    fn club_memberships_are_date_scoped() {
        let r = reg();
        assert!(r.is_eu_member_at("GB", "2010-01-01"));
        assert!(!r.is_eu_member_at("GB", "2023-01-01"));
        assert!(r.is_eu_member_at("GB", "2020-01-31"));
        assert!(!r.is_eu_member_at("GB", "2020-02-01"));
        assert!(!r.is_eu_member_at("GR", "1980-01-01"));
        assert!(r.is_eu_member_at("GR", "2000-01-01"));
        assert!(!r.is_eurozone_member_at("GR", "2000-01-01"));
        assert!(!r.is_eurozone_member_at("GR", "2000-12-31"));
        assert!(r.is_eurozone_member_at("GR", "2001-01-01"));
        assert!(r.is_eurozone_member_at("GR", "2002-01-01"));
        assert!(!r.is_eu_member_at("DE", "1950-01-01"));
        assert!(r.is_in_customs_union_at("GB", "2010-01-01"));
        assert!(!r.is_in_customs_union_at("GB", "2023-01-01"));
        assert!(r.is_eea_member_at("GB", "2020-12-31"));
        assert!(!r.is_eea_member_at("GB", "2021-01-01"));
        for bad in ["2000-13-01", "2000-1-1", ""] {
            assert!(!r.is_eu_member_at("DE", bad));
        }
        assert!(!r.is_eu_member_at("ZZ", "2000-01-01"));
        assert!(!r.is_eu_member_at("", "2000-01-01"));
        assert!(r.is_eu_member_at(" gb ", "2010-01-01"));
    }

    #[test]
    fn eea_provisional_application_counts() {
        let r = reg();
        assert!(r.is_eea_member_at("BG", "2010-01-01"));
        assert!(!r.is_eea_member_at("BG", "2005-01-01"));
        assert!(!r.is_eea_member_at("BG", "2007-07-31"));
        assert!(r.is_eea_member_at("BG", "2007-08-01"));
        assert!(r.is_eea_member_at("CY", "2005-01-01"));
        assert!(!r.is_eea_member_at("CY", "2003-01-01"));
        assert!(!r.is_eea_member_at("HR", "2020-01-01"));
    }

    #[test]
    fn aliases_match_the_v1_11_1_lists_for_every_code() {
        let r = reg();
        let mut codes: Vec<String> = r.all_active().iter().map(|c| c.alpha_2.clone()).collect();
        codes.push("ZZ".to_string());
        for c in &codes {
            let eu = KNOWN_EU_MEMBERS.contains(&c.as_str());
            let ea = eu || EEA_NON_EU.contains(&c.as_str());
            let ez = eu
                && r.active(c).is_some_and(|e| {
                    matches!(&e.currency_codes, Some(cc) if cc.len() == 1 && cc[0] == "EUR")
                });
            assert_eq!((r.is_eu(c), r.is_eea(c), r.is_eurozone(c)), (eu, ea, ez), "{}", c);
        }
        let n = |f: fn(&CountryRegistry, &str) -> bool| {
            r.all_active().iter().filter(|c| f(&r, &c.alpha_2)).count()
        };
        assert_eq!((n(CountryRegistry::is_eu), n(CountryRegistry::is_eea), n(CountryRegistry::is_eurozone)), (27, 30, 21));
    }

    #[test]
    fn derived_queries_worked_examples() {
        let r = reg();
        assert!(r.is_eu("DE") && r.is_eu("de"));
        assert!(!r.is_eu("GB") && !r.is_eu("CH") && !r.is_eu("XK"));
        assert!(r.is_eea("NO") && !r.is_eea("CH"));
        assert!(r.is_eurozone("DE") && r.is_eurozone("BG"));
        assert!(!r.is_eurozone("AD") && !r.is_eurozone("ME") && !r.is_eurozone("GB"));
        assert_eq!(r.region_tree("FR"), ["Europe", "Western Europe"]);
        assert!(r.region_tree("TW").is_empty() && r.region_tree("AQ").is_empty());
        assert_eq!(r.borders_transitively("US", 1), ["CA", "MX"]);
        assert!(r.borders_transitively("AQ", 2).is_empty());
        assert_eq!(r.succession_path("YU", "RS").unwrap(), ["YU", "CS", "RS"]);
        assert_eq!(r.succession_path("YU", "YU").unwrap(), ["YU"]);
        assert!(r.succession_path("US", "GB").is_none());
        assert!(r.succession_path("SU", "RU").is_none());
        assert_eq!(r.successors("YU"), ["CS", "ME", "RS"]);
        assert_eq!(r.predecessors("RS"), ["CS", "YU"]);
        assert_eq!(r.calling_code_for("+44 20 7946 0958"), ["GB", "GG", "IM", "JE"]);
        assert!(r.calling_code_for("+999 123").is_empty());
        assert!(r.calling_code_for("nonsense").is_empty());
        assert_eq!(r.currency_at("DE", "2000-01-01").unwrap(), ["EUR"]);
        assert!(r.currency_at("DE", "1970-01-01").is_none());
        assert_eq!(r.currency_at("DD", "1990-01-01").unwrap(), ["EUR"]);
        assert!(r.currency_at("DD", "1990-10-04").is_none());
        assert!(r.currency_at("BJ", "2000-01-01").is_none());
        assert!(r.currency_at("DE", "2000-13-01").is_none());
        assert_eq!(
            r.region_countries("Europe", Some("Western Europe")),
            ["AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"]
        );
        assert!(r.region_countries("Antarctica", None).is_empty());
    }
}
