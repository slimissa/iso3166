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
            by_numeric.insert(c.numeric.clone(), i);
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
        let key = alpha_2.to_ascii_uppercase();
        self.by_alpha2.get(&key).map(|&i| &self.active[i])
    }

    /// Alias for [`active`](Self::active).
    pub fn by_alpha2(&self, alpha_2: &str) -> Option<&Country> {
        self.active(alpha_2)
    }

    /// All entries (active and withdrawn) with this alpha-2 code. A
    /// small number of codes appear twice because ISO reassigned them
    /// (AI, SK).
    pub fn with_alpha2(&self, alpha_2: &str) -> Vec<&Country> {
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

    /// Look up an alpha-3 code. Case-insensitive.
    pub fn by_alpha3(&self, alpha_3: &str) -> Option<&Country> {
        let key = alpha_3.to_ascii_uppercase();
        self.by_alpha3.get(&key).map(|&i| &self.active[i])
    }

    /// Look up a numeric code. The argument is zero-padded to three
    /// digits, so `"20"` and `"020"` are equivalent.
    pub fn by_numeric(&self, numeric: &str) -> Option<&Country> {
        let padded = format!("{:0>3}", numeric);
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
}
