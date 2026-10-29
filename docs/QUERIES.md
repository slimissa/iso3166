# Derived Queries — v1.10.0 Design

**Status:** the contract for v1.10.0. The wrappers, the CLI, the README,
the docstrings and the tests all implement and point at this document.
**Rationale:** [QUERIES-DECISIONS.md](QUERIES-DECISIONS.md) explains why the
queries are what they are. This file says what they do.
**Data:** `iso3166.json` at v1.9.3 (252 active entries, 25 withdrawn entries).
Every example in this file was produced from that file and reproduces on it;
`test-derived-queries.sh` test 22 re-runs the index and every inline example.

A reader who reads only this file can predict the return value of every
query on every input. If you find an input this file does not let you
predict, that is a bug in this file.

## Worked examples index

One row per example. "Input" is the JSON argument list, "Expected" the JSON
result (`null` is the `None` / `nil` / `Option::None` / "no answer" of the
language). "Exact / approximate" says whether the tree contains what is
needed to answer exactly (see each query's section). "Tree source" names the
field and array the answer is read from.

| # | Query | Input (JSON arguments) | Expected (JSON) | Exact / approximate | Tree source |
|---|---|---|---|---|---|
| E01 | `is_eu` | `["DE"]` | `true` | approximate | hardcoded `KNOWN_EU_MEMBERS` (not a tree field) |
| E02 | `is_eu` | `["de"]` | `true` | approximate | hardcoded `KNOWN_EU_MEMBERS` (not a tree field) |
| E03 | `is_eu` | `["GB"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` (not a tree field) |
| E04 | `is_eu` | `["CH"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` (not a tree field) |
| E05 | `is_eu` | `["XK"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` (not a tree field) |
| E06 | `is_eu` | `["UK"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` (not a tree field) |
| E07 | `is_eu` | `["EU"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` (not a tree field) |
| E08 | `is_eu` | `["ZZ"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` (not a tree field) |
| E09 | `is_eea` | `["DE"]` | `true` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `{IS, LI, NO}` (not tree fields) |
| E10 | `is_eea` | `["NO"]` | `true` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `{IS, LI, NO}` (not tree fields) |
| E11 | `is_eea` | `["IS"]` | `true` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `{IS, LI, NO}` (not tree fields) |
| E12 | `is_eea` | `["LI"]` | `true` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `{IS, LI, NO}` (not tree fields) |
| E13 | `is_eea` | `["CH"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `{IS, LI, NO}` (not tree fields) |
| E14 | `is_eurozone` | `["DE"]` | `true` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `currency_codes` (active) |
| E15 | `is_eurozone` | `["BG"]` | `true` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `currency_codes` (active) |
| E16 | `is_eurozone` | `["SE"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `currency_codes` (active) |
| E17 | `is_eurozone` | `["AD"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `currency_codes` (active) |
| E18 | `is_eurozone` | `["ME"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `currency_codes` (active) |
| E19 | `is_eurozone` | `["GF"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `currency_codes` (active) |
| E20 | `is_eurozone` | `["GB"]` | `false` | approximate | hardcoded `KNOWN_EU_MEMBERS` + `currency_codes` (active) |
| E21 | `region_tree` | `["FR"]` | `["Europe", "Western Europe"]` | exact | `region`, `subregion`, `intermediate_region` |
| E22 | `region_tree` | `["US"]` | `["Americas", "Northern America"]` | exact | `region`, `subregion`, `intermediate_region` |
| E23 | `region_tree` | `["MX"]` | `["Americas", "Latin America and the Caribbean", "Central America"]` | exact | `region`, `subregion`, `intermediate_region` |
| E24 | `region_tree` | `["YU"]` | `["Southern Europe"]` | exact | `region`, `subregion`, `intermediate_region` |
| E25 | `region_tree` | `["DD"]` | `["Western Europe"]` | exact | `region`, `subregion`, `intermediate_region` |
| E26 | `region_tree` | `["TW"]` | `[]` | exact | `region`, `subregion`, `intermediate_region` |
| E27 | `region_tree` | `["AQ"]` | `[]` | exact | `region`, `subregion`, `intermediate_region` |
| E28 | `region_tree` | `["ZZ"]` | `[]` | exact | `region`, `subregion`, `intermediate_region` |
| E29 | `borders_transitively` | `["US", 1]` | `["CA", "MX"]` | exact | `borders` (active) |
| E30 | `borders_transitively` | `["DE", 1]` | `["AT", "BE", "CH", "CZ", "DK", "FR", "LU", "NL", "PL"]` | exact | `borders` (active) |
| E31 | `borders_transitively` | `["DE", 2]` | `["AD", "AT", "BE", "BY", "CH", "CZ", "DK", "ES", "FR", "HU", "IT", "LI", "LT", "LU", "MC", "NL", "PL", "RU", "SI", "SK", "UA"]` | exact | `borders` (active) |
| E32 | `borders_transitively` | `["LI", 2]` | `["AT", "CH", "CZ", "DE", "FR", "HU", "IT", "SI", "SK"]` | exact | `borders` (active) |
| E33 | `borders_transitively` | `["AQ", 2]` | `[]` | exact | `borders` (active) |
| E34 | `borders_transitively` | `["US", 0]` | `[]` | exact | `borders` (active) |
| E35 | `borders_transitively` | `["DD", 2]` | `[]` | exact | `borders` (active) |
| E36 | `succession_path` | `["YU", "RS"]` | `["YU", "CS", "RS"]` | exact | `replaced_by` (withdrawn) |
| E37 | `succession_path` | `["YU", "ME"]` | `["YU", "CS", "ME"]` | exact | `replaced_by` (withdrawn) |
| E38 | `succession_path` | `["YU", "YU"]` | `["YU"]` | exact | `replaced_by` (withdrawn) |
| E39 | `succession_path` | `["DD", "DE"]` | `["DD", "DE"]` | exact | `replaced_by` (withdrawn) |
| E40 | `succession_path` | `["AN", "CW"]` | `["AN", "CW"]` | exact | `replaced_by` (withdrawn) |
| E41 | `succession_path` | `["SK", "IN"]` | `["SK", "IN"]` | exact | `replaced_by` (withdrawn) |
| E42 | `succession_path` | `["SU", "RU"]` | `null` | exact | `replaced_by` (withdrawn) |
| E43 | `succession_path` | `["US", "GB"]` | `null` | exact | `replaced_by` (withdrawn) |
| E44 | `succession_path` | `["YU", "ZZ"]` | `null` | exact | `replaced_by` (withdrawn) |
| E45 | `successors` | `["YU"]` | `["CS", "ME", "RS"]` | exact | `replaced_by` (withdrawn) |
| E46 | `successors` | `["CS"]` | `["ME", "RS"]` | exact | `replaced_by` (withdrawn) |
| E47 | `successors` | `["AN"]` | `["BQ", "CW", "SX"]` | exact | `replaced_by` (withdrawn) |
| E48 | `successors` | `["SK"]` | `["IN"]` | exact | `replaced_by` (withdrawn) |
| E49 | `successors` | `["RS"]` | `[]` | exact | `replaced_by` (withdrawn) |
| E50 | `successors` | `["US"]` | `[]` | exact | `replaced_by` (withdrawn) |
| E51 | `successors` | `["SU"]` | `[]` | exact | `replaced_by` (withdrawn) |
| E52 | `predecessors` | `["RS"]` | `["CS", "YU"]` | exact | `replaced_by` (withdrawn) |
| E53 | `predecessors` | `["ME"]` | `["CS", "YU"]` | exact | `replaced_by` (withdrawn) |
| E54 | `predecessors` | `["CS"]` | `["YU"]` | exact | `replaced_by` (withdrawn) |
| E55 | `predecessors` | `["CW"]` | `["AN"]` | exact | `replaced_by` (withdrawn) |
| E56 | `predecessors` | `["IN"]` | `["SK"]` | exact | `replaced_by` (withdrawn) |
| E57 | `predecessors` | `["YU"]` | `[]` | exact | `replaced_by` (withdrawn) |
| E58 | `predecessors` | `["US"]` | `[]` | exact | `replaced_by` (withdrawn) |
| E59 | `calling_code_for` | `["+44 20 7946 0958"]` | `["GB", "GG", "IM", "JE"]` | exact | `calling_codes` (active) |
| E60 | `calling_code_for` | `["44 20 7946 0958"]` | `["GB", "GG", "IM", "JE"]` | exact | `calling_codes` (active) |
| E61 | `calling_code_for` | `["+44 (0) 20.7946.0958"]` | `["GB", "GG", "IM", "JE"]` | exact | `calling_codes` (active) |
| E62 | `calling_code_for` | `["+49 30 1234567"]` | `["DE"]` | exact | `calling_codes` (active) |
| E63 | `calling_code_for` | `["+7 495 123 4567"]` | `["KZ", "RU"]` | exact | `calling_codes` (active) |
| E64 | `calling_code_for` | `["+1 202 555 0100"]` | `["AG", "AI", "AS", "BB", "BM", "BS", "CA", "DM", "DO", "GD", "GU", "JM", "KN", "KY", "LC", "MP", "MS", "PR", "SX", "TC", "TT", "UM", "US", "VC", "VG", "VI"]` | exact | `calling_codes` (active) |
| E65 | `calling_code_for` | `["+1-867-555-0100"]` | `["AG", "AI", "AS", "BB", "BM", "BS", "CA", "DM", "DO", "GD", "GU", "JM", "KN", "KY", "LC", "MP", "MS", "PR", "SX", "TC", "TT", "UM", "US", "VC", "VG", "VI"]` | exact | `calling_codes` (active) |
| E66 | `calling_code_for` | `["+999 123"]` | `[]` | exact | `calling_codes` (active) |
| E67 | `calling_code_for` | `["nonsense"]` | `[]` | exact | `calling_codes` (active) |
| E68 | `calling_code_for` | `[""]` | `[]` | exact | `calling_codes` (active) |
| E69 | `currency_at` | `["DE", "2000-01-01"]` | `["EUR"]` | approximate | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E70 | `currency_at` | `["DE", "1990-01-01"]` | `["EUR"]` | approximate | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E71 | `currency_at` | `["PA", "2000-01-01"]` | `["PAB", "USD"]` | approximate | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E72 | `currency_at` | `["AQ", "2000-01-01"]` | `[]` | approximate | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E73 | `currency_at` | `["EU", "2000-01-01"]` | `null` | exact | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E74 | `currency_at` | `["DD", "1990-01-01"]` | `null` | exact | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E75 | `currency_at` | `["DD", "1990-10-03"]` | `["EUR"]` | approximate | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E76 | `currency_at` | `["DD", "1991-01-01"]` | `["EUR"]` | approximate | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E77 | `currency_at` | `["YU", "2004-01-01"]` | `["EUR", "RSD"]` | approximate | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E78 | `currency_at` | `["AN", "2010-11-30"]` | `null` | exact | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E79 | `currency_at` | `["AN", "2010-12-01"]` | `["ANG", "USD"]` | approximate | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E80 | `currency_at` | `["SU", "2000-01-01"]` | `null` | exact | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E81 | `currency_at` | `["DE", "2000-13-01"]` | `null` | exact | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E82 | `currency_at` | `["ZZ", "2000-01-01"]` | `null` | exact | `currency_codes` (active); `withdrawal_date`, `replaced_by` (withdrawn) |
| E83 | `region_countries` | `["Europe", "Western Europe"]` | `["AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"]` | exact | `region`, `subregion` (active) |
| E84 | `region_countries` | `["europe", "western europe"]` | `["AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"]` | exact | `region`, `subregion` (active) |
| E85 | `region_countries` | `["Americas", "Northern America"]` | `["BM", "CA", "GL", "PM", "US"]` | exact | `region`, `subregion` (active) |
| E86 | `region_countries` | `["Antarctica"]` | `[]` | exact | `region`, `subregion` (active) |
| E87 | `region_countries` | `["Nonexistent"]` | `[]` | exact | `region`, `subregion` (active) |
| E88 | `is_active_on` | `["DE", "1990-01-01"]` | `true` | exact | `introduced` (active); `withdrawal_date` (withdrawn) |
| E89 | `is_active_on` | `["DE", "1970-01-01"]` | `false` | exact | `introduced` (active); `withdrawal_date` (withdrawn) |
| E90 | `is_active_on` | `["BJ", "2000-01-01"]` | `null` | unknown (source silent) | `introduced` (active); `withdrawal_date` (withdrawn) |
| E91 | `is_active_on` | `["DD", "1990-01-01"]` | `true` | exact (withdrawn: end date only) | `introduced` (active); `withdrawal_date` (withdrawn) |
| E92 | `is_active_on` | `["DD", "1990-10-04"]` | `false` | exact | `introduced` (active); `withdrawal_date` (withdrawn) |
| E93 | `is_active_on` | `["YU", "2010-01-01"]` | `false` | exact | `introduced` (active); `withdrawal_date` (withdrawn) |
| E94 | `is_active_on` | `["ZZ", "2000-01-01"]` | `false` | exact | `introduced` (active); `withdrawal_date` (withdrawn) |
| E95 | `is_active_on` | `["EU", "2000-01-01"]` | `null` | unknown (not officially assigned) | `introduced` (active); `withdrawal_date` (withdrawn) |

## Conventions that apply to every query

**Codes.** Every `code` argument is an ISO 3166-1 alpha-2 string. It is
trimmed and upper-cased before use, so `"de"` and `" DE "` mean `"DE"`.
The empty string and non-string values match nothing.

**Unknown codes are not errors.** A code that is in neither the active nor
the withdrawn array of the tree is simply unknown. Boolean queries return
`false`, list queries return an empty list, and optional queries return
`None`. Only the CLI turns "unknown" into an exit code (see each query).

**Active entries win.** Two codes exist twice in the tree: `AI` is
Anguilla (active) and the French Afars and Issas (withdrawn, replaced by
`DJ`), and `SK` is Slovakia (active) and Sikkim (withdrawn, replaced by
`IN`). Every query that reads a field of a code (region, borders,
calling codes, currency codes) reads the **active** entry when there is one,
and the withdrawn entry only when the code is not active. The succession
graph is built from withdrawn entries only, because only withdrawn entries
carry `replaced_by`. Consequence: `successors("SK")` is `["IN"]`
(Sikkim's successor) even though `SK` is also active Slovakia, and
`region_tree("SK")` is Slovakia's region. This is documented behavior, not
an accident; callers who need to tell the two apart use the registry's
alpha-2 lookup that returns every entry (Go: `WithAlpha2`).

**List results are sorted and are copies.** Unless a query says otherwise, a
list result is sorted ascending by plain string comparison of the alpha-2
codes, and it is a new list: changing it never changes the registry. In
JavaScript the result is a frozen array (`Object.freeze`); in Go and Rust it
is a fresh slice or `Vec`.

**`None` means "the tree cannot answer."** It never means "false" and never
means "empty". Where a query can fail to answer, its section lists every
case.

**Dates** are strings in the form `YYYY-MM-DD`, a real calendar date, year
1 or later. Anything else (`"2000-13-01"`, `"20000101"`, `"2000-1-1"`) is a
malformed date and yields `None`, the same as "cannot answer". Dates compare
as strings, which is correct for this format.

**Naming across surfaces.**

| Query | Python / Rust | JavaScript | Go | CLI |
|---|---|---|---|---|
| EU membership | `is_eu` | `isEu` | `IsEU` | `is-eu` |
| EEA membership | `is_eea` | `isEea` | `IsEEA` | `is-eea` |
| Eurozone membership | `is_eurozone` | `isEurozone` | `IsEurozone` | `is-eurozone` |
| Region hierarchy | `region_tree` | `regionTree` | `RegionTree` | `region-tree` |
| Border closure | `borders_transitively` | `bordersTransitively` | `BordersTransitively` | `borders-transitively` |
| Succession path | `succession_path` | `successionPath` | `SuccessionPath` | `succession-path` |
| All descendants | `successors` | `successors` | `Successors` | `successors` |
| All ancestors | `predecessors` | `predecessors` | `Predecessors` | `predecessors` |
| Phone number lookup | `calling_code_for` | `callingCodeFor` | `CallingCodeFor` | `calling-code-for` |
| Currency on a date | `currency_at` | `currencyAt` | `CurrencyAt` | `currency-at` |
| Countries in a region | `region_countries` | `regionCountries` | `RegionCountries` | `region-countries` |
| Code assigned on a date | `is_active_on` | `isActiveOn` | `IsActiveOn` | `is-active-on` |
| Date a code was added | field `introduced` | `introduced` | `Introduced` | `introduced` |

**Examples inside sections** are written language-neutrally as
`` `query(args)` → `result` `` using JSON literals (`true`, `false`,
`null`, lists). They are the same cases as the index, in prose context.

**The one hardcoded list.** `KNOWN_EU_MEMBERS` is the 27 EU member states
as of v1.9.3: `AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL
PL PT RO SK SI ES SE`. It is not a field of the tree, so
`check_docs_match_tree.py` cannot verify it and it carries no dates. It is
the only data in the registry that is not read from `iso3166.json`, and it
is the reason the three EU queries are approximate and deprecated (below).
`EEA_NON_EU` is `IS LI NO`.

## Query 1 — `is_eu`, `is_eea`, `is_eurozone` (approximate)

**Signatures.**

```python
reg.is_eu(code: str) -> bool            # Python
reg.is_eea(code: str) -> bool
reg.is_eurozone(code: str) -> bool
```
```js
reg.isEu(code) -> boolean               // JavaScript (also isEea, isEurozone)
```
```rust
reg.is_eu(code: &str) -> bool           // Rust (also is_eea, is_eurozone)
```
```go
reg.IsEU(code string) bool              // Go (also IsEEA, IsEurozone)
```
```bash
iso3166 is-eu DE        # CLI (also is-eea, is-eurozone)
# prints true or false to stdout; exit code 0 on success (whether true or false),
# 1 if the code is not found, 2 on usage error, 3 if the registry is missing
```

**Semantics.** These three answers are **approximate**. The tree has no
membership field, so the answers come from the hardcoded `KNOWN_EU_MEMBERS`
list described above, a snapshot with no dates. `is_eu(code)` is true
exactly when the normalized code is in that list. `is_eea(code)` is true when
`is_eu(code)` is true or the code is `IS`, `LI` or `NO`. `is_eurozone(code)`
is true when the code is in `KNOWN_EU_MEMBERS` **and** the active entry's
`currency_codes` is exactly `["EUR"]`. All three are false for unknown codes.

**CLI contract.** The CLI prints true/false to stdout; the boolean is the
answer and the exit code is the plumbing, the same as for every other
subcommand. `iso3166 is-eu DE` prints `true` and exits 0; `iso3166 is-eu GB`
prints `false` and exits 0 (GB exists, so the command succeeded); `iso3166
is-eu XX` prints `error: not found: XX` on stderr and exits 1; `iso3166 is-eu
--bogus` is a usage error and exits 2; a missing registry file exits 3. With
`--json` the output is `{"code": "DE", "is_eu": true, "result": "true"}` (the
key is `is_eea` or `is_eurozone` for the other two). The wrappers return the
same boolean as a value. A shell script that needs the answer reads stdout, not
`$?`.

**Data read.** `KNOWN_EU_MEMBERS` and `EEA_NON_EU` (hardcoded, not in the
tree), and for `is_eurozone` only, `currency_codes` of the active entry.

**Edge cases, with the tree's values.**

- `is_eu("GB")` → `false`. The United Kingdom left the EU in 2020, and `GB`
  is not in the list. The tree also has an active entry `UK`
  (exceptionally reserved), and `is_eu("UK")` → `false`.
- `is_eu("CH")` → `false`: European, not a member.
- `is_eu("XK")` → `false`: Kosovo has `region: null` and no
  `currency_codes` entry (null) in the tree, and is not in the list.
- `is_eu("EU")` → `false`: `EU` is an active (exceptionally reserved) entry
  for the European Union itself; the Union is not one of its own members.
- `is_eu("ZZ")` → `false`: unknown code. (The CLI prints `error: not found: ZZ`
  on stderr and exits 1 here.)
- `is_eurozone("AD")` → `false`: Andorra's `currency_codes` is `["EUR"]` but
  it is not in `KNOWN_EU_MEMBERS`. The same holds for `MC`, `SM`, `VA`
  and `ME`, which all use the euro without being in the eurozone.
- `is_eurozone("GF")` → `false`: French Guiana's `currency_codes` is
  `["EUR"]` and legally it is part of the eurozone through France, but it is
  a separate ISO code that is not in the list. The same holds for `GP`,
  `MQ`, `RE`, `YT`, `PM`, `BL`, `MF`, `TF` and `AX`. This is a documented
  false negative of the approximation.
- `is_eurozone("SE")` → `false`: Sweden is an EU member whose
  `currency_codes` is `["SEK"]`.
- `is_eurozone("BG")` → `true`: at v1.9.3 the tree gives Bulgaria
  `["EUR"]`.

**Worked examples** (all in the index):

- `is_eu("DE")` → `true` (approximate)
- `is_eu("GB")` → `false` (approximate)
- `is_eea("NO")` → `true` (approximate)
- `is_eea("CH")` → `false` (approximate)
- `is_eurozone("DE")` → `true` (approximate)
- `is_eurozone("AD")` → `false` (approximate)

**Deprecation trigger.** `is_eu`, `is_eea` and `is_eurozone` are deprecated
the day v1.12.0 ships `is_eu_member_at(code, date)`, which is date-scoped and
backed by an `eu_membership[]` field in the tree. Until then they are the
best answer the tree supports, and they say "approximate" in their
docstrings and CLI help.

**What it does not answer.** Whether a country was a member at a past date
(the list has no dates; needs `is_eu_member_at`). Whether an overseas
territory is inside the eurozone (separate ISO codes are not in the list).
Whether a country is in the Schengen area, a customs union or the EEA by a
mechanism other than the listed codes.

## Query 2 — `region_tree`

**Signatures.**

```python
reg.region_tree(code: str) -> list[str]
```
```js
reg.regionTree(code) -> readonly string[]
```
```rust
reg.region_tree(code: &str) -> Vec<String>
```
```go
reg.RegionTree(code string) []string
```
```bash
iso3166 region-tree FR
# prints "Europe, Western Europe"; --json prints a list; exit 0 if the code is
# known (even if the list is empty), 1 if the code is not in the tree
```

**Semantics.** Returns the entry's `region`, `subregion` and
`intermediate_region`, in that order, with null (and empty) values removed.
The result is not padded: a missing level shifts the later levels up, so the
list is not a fixed `[region, subregion, intermediate_region]` triple. An
active entry is preferred over a withdrawn one. An unknown code returns the
empty list.

**Data read.** `region`, `subregion`, `intermediate_region` of the entry.

**Edge cases, with the tree's values.**

- `region_tree("TW")` → `[]`. Taiwan has `region: null` and
  `subregion: null` in the tree. (It is not `["Asia"]`; that would be an
  invention.) This is a limitation of the tree, not a bug in the query. The
  five active entries with a null region are `AQ`, `EU`, `TW`, `UK` and `XK`.
- `region_tree("AQ")` → `[]`: Antarctica has a null region.
- `region_tree("US")` → `["Americas", "Northern America"]`.
- `region_tree("MX")` →
  `["Americas", "Latin America and the Caribbean", "Central America"]`.
- `region_tree("YU")` → `["Southern Europe"]`. Withdrawn entries have a null
  `region` but may have a subregion; the query drops only nulls, so the
  result is a lone subregion. `region_tree("DD")` →
  `["Western Europe"]`.
- `region_tree("ZZ")` → `[]`: unknown code.

**Worked examples.** `region_tree("FR")` → `["Europe", "Western Europe"]`;
`region_tree("TW")` → `[]`; `region_tree("MX")` as above.

**Deprecation trigger.** None.

**What it does not answer.** Which continent a null-region entry belongs to.
The tree does not say, and the query does not guess.

## Query 3 — `borders_transitively`

**Signatures.**

```python
reg.borders_transitively(code: str, max_hops: int = 2) -> list[str]
```
```js
reg.bordersTransitively(code, maxHops = 2) -> readonly string[]
```
```rust
reg.borders_transitively(code: &str, max_hops: usize) -> Vec<String>
```
```go
reg.BordersTransitively(code string, maxHops int) []string
```
```bash
iso3166 borders-transitively DE --max-hops 2
# one code per line; --json prints a list; exit 0 if the code is known
# (even if the list is empty), 1 if not in the tree
```

**Semantics.** The set of codes reachable from `code` by following the
`borders` arrays of active entries for at most `max_hops` steps, excluding
`code` itself, sorted. One hop is the entry's own `borders`. If `max_hops`
is less than 1, or the code is unknown, the result is empty. Withdrawn
entries have `borders: null`, and so do `EU` and `UK`; such a code returns the empty list.
(Rust and Go take `max_hops` explicitly; the Python and JavaScript default
is 2, and the CLI default is 2.)

**Data read.** `borders` of active entries.

**Edge cases, with the tree's values.**

- `borders_transitively("US", 1)` → `["CA", "MX"]`: the tree gives the
  United States exactly those two land neighbors.
- `borders_transitively("DE", 1)` →
  `["AT", "BE", "CH", "CZ", "DK", "FR", "LU", "NL", "PL"]` (9 codes).
- `borders_transitively("DE", 2)` → 21 codes (all in the index),
  including `AD`, `BY`, `ES`, `HU`, `IT`, `LI`, `LT`, `MC`, `RU`, `SI`,
  `SK` and `UA`; it never contains `DE`, even though Germany is a neighbor
  of its neighbors.
- `borders_transitively("AQ", 2)` → `[]`: Antarctica has an empty `borders`
  list.
- `borders_transitively("US", 0)` → `[]`.
- `borders_transitively("DD", 2)` → `[]`: withdrawn, no borders.

**Deprecation trigger.** None; `borders` is a permanent field.

**What it does not answer.** Sea borders, distance, or whether two countries
are connected by a road. Only the land-border graph in the tree.

## Query 4 — `succession_path`

**Signatures.**

```python
reg.succession_path(from_code: str, to_code: str) -> list[str] | None
```
```js
reg.successionPath(fromCode, toCode) -> readonly string[] | null
```
```rust
reg.succession_path(from: &str, to: &str) -> Option<Vec<String>>
```
```go
reg.SuccessionPath(fromCode, toCode string) ([]string, bool)   // bool is false for "no path"
```
```bash
iso3166 succession-path YU RS
# prints "YU -> CS -> RS"; --json prints a list or null; exit 0 if a path exists,
# 1 if there is none or either code is not in the tree
```

**Semantics.** The shortest path from `from_code` to `to_code` along
`replaced_by` edges (each withdrawn code points to the codes that replaced
it), including both endpoints. If several shortest paths exist, the one
found first in the registry's `replaced_by` order is returned. A code to
itself is the one-element path `[code]` if the code exists. If there is no
path, or either code is unknown, the result is `None`.

**Data read.** `replaced_by` of withdrawn entries. Active codes have no
outgoing edges.

**Edge cases, with the tree's values.**

- `succession_path("YU", "RS")` → `["YU", "CS", "RS"]`: Yugoslavia was
  replaced by `CS` (Serbia and Montenegro), which was replaced by `RS`
  and `ME`.
- `succession_path("YU", "ME")` → `["YU", "CS", "ME"]`.
- `succession_path("YU", "YU")` → `["YU"]`.
- `succession_path("DD", "DE")` → `["DD", "DE"]`: East Germany to Germany,
  one edge.
- `succession_path("AN", "CW")` → `["AN", "CW"]`: Netherlands Antilles to
  Curaçao.
- `succession_path("SU", "RU")` → `null`. The USSR (`SU`) has
  `replaced_by: null` in the tree, so no edge leaves it. This is a
  limitation of the tree, not a bug in the query. Five withdrawn entries
  have no successor in the tree (`JT`, `MI`, `NT`, `SU`, `WK`), and all of
  them behave this way.
- `succession_path("US", "GB")` → `null`: neither is withdrawn.
- `succession_path("YU", "ZZ")` → `null`: unknown endpoint.
- `succession_path("SK", "IN")` → `["SK", "IN"]`: follows Sikkim's edge, as
  described under "Active entries win".

**Deprecation trigger.** None; `replaced_by` is a permanent field.

**What it does not answer.** Why a country was replaced, or the order in
which two parallel successors split off.

## Query 5 — `successors` and `predecessors` (transitive closure)

**Signatures.**

```python
reg.successors(code: str) -> list[str]
reg.predecessors(code: str) -> list[str]
```
```js
reg.successors(code) / reg.predecessors(code) -> readonly string[]
```
```rust
reg.successors(code: &str) -> Vec<String>     // and predecessors
```
```go
reg.Successors(code string) []string          // and Predecessors
```
```bash
iso3166 successors YU       # human output lists the chain, then the closure
iso3166 successors YU --json
iso3166 predecessors RS
# exit 0 if the code is in the tree (even if the answer is empty), 1 if not
```

**Semantics.** `successors(code)` is the **transitive closure** of
`replaced_by` starting at `code`: every code reachable by following
`replaced_by` edges one or more times, including intermediate codes that were
themselves later withdrawn, excluding `code` itself, sorted. These are
**all descendants**. `predecessors(code)` is the reverse: **all ancestors**,
every withdrawn code from which `code` can be reached by one or more
`replaced_by` edges, excluding `code`, sorted. Both are empty for a code
with no edges in the relevant direction, and for unknown codes.

This is the same definition on every surface. In v1.9.x the CLI returned
only terminal successors (codes that were never replaced); from v1.10.0 the
CLI returns the full closure, matching the wrappers. This is a breaking change
for CLI users and is announced in the release notes.

**Data read.** `replaced_by` of withdrawn entries (forward edges for
`successors`, the same edges reversed for `predecessors`).

**Edge cases, with the tree's values.**

- `successors("YU")` → `["CS", "ME", "RS"]`: `CS` is included because it is
  reachable (`YU` → `CS`), even though `CS` was itself withdrawn.
- `successors("CS")` → `["ME", "RS"]`.
- `successors("AN")` → `["BQ", "CW", "SX"]`.
- `successors("RS")` → `[]`: active, no edges.
- `successors("US")` → `[]`: active.
- `successors("SU")` → `[]`: withdrawn but with `replaced_by: null`.
- `successors("SK")` → `["IN"]`: Sikkim's edge, although `SK` is also active
  Slovakia (see "Active entries win").
- `predecessors("RS")` → `["CS", "YU"]`.
- `predecessors("ME")` → `["CS", "YU"]`.
- `predecessors("CS")` → `["YU"]`: an intermediate code has ancestors too.
- `predecessors("CW")` → `["AN"]`; `predecessors("IN")` → `["SK"]`.
- `predecessors("YU")` → `[]`: no withdrawn entry lists `YU` in its `replaced_by`.
- `predecessors("US")` → `[]`.

**Deprecation trigger.** None.

**What it does not answer.** Which descendants are still active (look each returned code up), and which branch of a split a particular
territory went to.

## Query 6 — `calling_code_for`

**Signatures.**

```python
reg.calling_code_for(number: str) -> list[str]
```
```js
reg.callingCodeFor(number) -> readonly string[]
```
```rust
reg.calling_code_for(number: &str) -> Vec<String>
```
```go
reg.CallingCodeFor(number string) []string
```
```bash
iso3166 calling-code-for "+44 20 7946 0958"
# one code per line; --json prints a list; exit 0 if any match, 1 if none
```

**Semantics.** Returns the sorted alpha-2 codes of every **active** entry that
has a `calling_codes` value which is a prefix of the number's digits. The
characters space, hyphen, dot, parentheses and plus are ignored. If any
other character remains, or no digit remains, the result is empty. A number
may be written with or without the leading plus. Because the tree stores
country calling codes only (for example `"1"`, `"44"`), this is a
**country-level** lookup: it cannot narrow a shared code by area code.

**Data read.** `calling_codes` of active entries.

**Edge cases, with the tree's values.**

- `calling_code_for("+44 20 7946 0958")` → `["GB", "GG", "IM", "JE"]`. The
  tree gives `44` to all four. The registry returns every candidate and the
  caller decides.
- `calling_code_for("+1 202 555 0100")` → all 26 NANP entries:
  `AG AI AS BB BM BS CA DM DO GD GU JM KN KY LC MP MS PR SX TC TT UM US VC VG VI`.
  The tree has `"1"`, not area codes, so Washington's `202` cannot narrow it
  to `US`, and `+1 867` (Canada's Yukon) also returns all 26.
- `calling_code_for("+7 495 123 4567")` → `["KZ", "RU"]`.
- `calling_code_for("+49 30 1234567")` → `["DE"]`.
- `calling_code_for("+999 123")` → `[]`: no entry has a calling code that
  prefixes `999123`.
- `calling_code_for("nonsense")` → `[]`; `calling_code_for("")` → `[]`.
- `EU`, `UK` and `XK` have no calling codes in the tree and are never
  returned.

**Deprecation trigger.** None.

**What it does not answer.** Which of several countries sharing a code owns
a number (needs area-code data the tree does not carry), whether a number is
valid, or whether it is mobile or landline.

## Query 7 — `currency_at` (approximate)

**Deprecated by** v1.11.1's exact implementation. In v1.11.0, `currency_at`
remains approximate for active entries; the approximation is documented per
entry below. The `introduced` field exists as of v1.11.0, but this query does
not read it yet. Until v1.11.1, `currency_at` is exact only where the answer
is `null` (unknown code, malformed date, withdrawn before its date).

**Signatures.**

```python
reg.currency_at(code: str, date: str) -> list[str] | None
```
```js
reg.currencyAt(code, date) -> readonly string[] | null
```
```rust
reg.currency_at(code: &str, date: &str) -> Option<Vec<String>>
```
```go
reg.CurrencyAt(code, date string) ([]string, bool)   // bool is false for "no answer"
```
```bash
iso3166 currency-at DE 2000-01-01
# one code per line; --json prints a list or null; exit 0 if answered, 1 if not
# help text: "approximate for active entries"
```

**Semantics.** The currency in force on `date`, **approximate**. The tree's
`introduced` field (v1.11.0) is the date a code was added to ISO 3166-1, not
the date a currency was adopted, and this query does not read it. So it cannot
say when an active country adopted its current currency. The query therefore applies these rules in order:

1. A malformed date → `None`.
2. If the code is **active**, return a copy of its current `currency_codes`
   whatever the date (or `None` if `currency_codes` is null). This is the
   approximation: it is right only for dates after the current currency was
   adopted.
3. If the code is **withdrawn** and its `withdrawal_date` is missing or after
   the date → `None`. The tree has no currency for any withdrawn entry
   (all 25 have `currency_codes: null`), so nothing is known before
   withdrawal.
4. If the code is withdrawn and the date is on or after `withdrawal_date`,
   follow `replaced_by` transitively and return the sorted union of the
   **current** `currency_codes` of the active codes reached. This is also
   approximate: the successor's current currency is not necessarily the one
   used on that date. If no currency is found, `None`.
5. Unknown code → `None`.

**Data read.** `currency_codes` of active entries; `withdrawal_date` and
`replaced_by` of withdrawn entries.

**Edge cases, with the tree's values.**

- `currency_at("DE", "2000-01-01")` → `["EUR"]` (**approximate**). Germany
  adopted the euro in 2002; on that date the true answer was `DEM`. The tree
  cannot say so, and the query returns the current currency instead of
  failing.
- `currency_at("DE", "1990-01-01")` → `["EUR"]` (**approximate**). This is the
  tree's answer for an active entry: `introduced` does not hold currency history, so it
  cannot say that Germany used `DEM` in 1990, and the contract is to return the
  current currency, labeled approximate, rather than to refuse. Callers who need
  a historical answer must not rely on it before v1.11.1.
- `currency_at("DD", "1990-01-01")` → `null`. East Germany (`DD`) was
  withdrawn on 1990-10-03, the date is earlier, and the tree has no
  currency for `DD` (`currency_codes: null`). The East German mark is not in
  the tree, so the query returns `None`. This is a limitation of the tree,
  not a bug in the query.
- `currency_at("DD", "1990-10-03")` → `["EUR"]` (approximate): the withdrawal
  date itself counts, and the answer is Germany's current currency.
- `currency_at("DD", "1991-01-01")` → `["EUR"]` (approximate; true answer
  `DEM`).
- `currency_at("YU", "2004-01-01")` → `["EUR", "RSD"]` (approximate): `YU`
  → `CS` → `RS` (`RSD`) and `ME` (`EUR`).
- `currency_at("AN", "2010-11-30")` → `null` (one day before the Netherlands
  Antilles' `withdrawal_date`, 2010-12-01); `currency_at("AN", "2010-12-01")`
  → `["ANG", "USD"]` (approximate): `BQ` has `USD`, `CW` and `SX` have `ANG`.
- `currency_at("PA", "2000-01-01")` → `["PAB", "USD"]` (approximate): a
  multi-currency active entry.
- `currency_at("AQ", "2000-01-01")` → `[]`: the tree gives Antarctica an
  empty `currency_codes` list. (Empty means "no currency", `null` means
  "unknown".)
- `currency_at("EU", "2000-01-01")` → `null`: `EU` has `currency_codes:
  null`; `UK` and `XK` likewise.
- `currency_at("SU", "2000-01-01")` → `null`: withdrawn, no successor.
- `currency_at("DE", "2000-13-01")` → `null`: malformed date.
- `currency_at("ZZ", "2000-01-01")` → `null`: unknown code.

**Deprecation trigger.** `currency_at` is deprecated by v1.11.1, which
replaces the approximation with an exact answer built on `introduced`.
v1.11.0 ships the field and `is_active_on`; it does not change this query.

**What it does not answer.** Any currency before the current one for an
active entry (the tree has no history), any currency for a withdrawn entry
before its withdrawal, or which of several currencies in a multi-currency
entry is primary.

## Query 8 — `region_countries`

**Signatures.**

```python
reg.region_countries(region: str, subregion: str | None = None) -> list[str]
```
```js
reg.regionCountries(region, subregion = null) -> readonly string[]
```
```rust
reg.region_countries(region: &str, subregion: Option<&str>) -> Vec<String>
```
```go
reg.RegionCountries(region, subregion string) []string   // "" means no subregion filter
```
```bash
iso3166 region-countries Europe --subregion "Western Europe"
# one code per line; --json prints a list; exit 0 if any, 1 if none
```

**Semantics.** The sorted alpha-2 codes of **active** entries whose `region`
equals `region` and, when a subregion is given, whose `subregion` equals it.
Comparison is case-insensitive. An empty region matches nothing. Entries with
a null region (`AQ`, `EU`, `TW`, `UK`, `XK`) belong to no region. Withdrawn
entries are never returned.

**Data read.** `region` and `subregion` of active entries.

**Edge cases, with the tree's values.**

- `region_countries("Europe", "Western Europe")` →
  `["AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"]` (9 codes).
- `region_countries("europe", "western europe")` → the same nine
  (case-insensitive).
- `region_countries("Europe")` → 51 codes at v1.9.3.
- `region_countries("Americas", "Northern America")` →
  `["BM", "CA", "GL", "PM", "US"]`.
- `region_countries("Antarctica")` → `[]`. Antarctica is not a region in the
  tree; `AQ` has `region: null`. (It is not `["AQ"]`.)
- `region_countries("Nonexistent")` → `[]`.

**Deprecation trigger.** None.

**What it does not answer.** Membership of null-region entries in any
region, or anything about withdrawn codes.

## Query 9 — `is_active_on` (tri-state)

**Signatures.**

```python
reg.is_active_on(code: str, date: str) -> bool | None
```
```js
reg.isActiveOn(code, date) -> boolean | null
```
```rust
reg.is_active_on(code: &str, date: &str) -> Option<bool>
```
```go
reg.IsActiveOn(code, date string) *bool   // nil means unknown
```
```bash
iso3166 is-active-on DE 1990-01-01
# prints true, false or unknown; --json prints
# {"code", "date", "is_active_on": true|false|null, "result": "true|false|unknown"}
# exit 0 true, 1 false, 4 unknown, 2 on a malformed DATE or usage error
# help text: "tri-state: prints true, false, or unknown"
iso3166 introduced DE
# prints the date, or "unknown"; exit 0 known, 4 unknown (null), 1 code not found
```

**Semantics.** Was `code` an assigned ISO 3166-1 code on `date`? The answer is
tri-state, because `introduced` is null for some entries and the registry must
not turn "the source is silent" into a confident answer. In order:

1. A date that is not a real `YYYY-MM-DD` → `false`.
2. Code in neither array → `false`.
3. The code is **active** (an active entry wins when a code is in both arrays,
   AI and SK): `introduced` null → `null`; else `date >= introduced`.
4. The code is **withdrawn**: `date > withdrawal_date` → `false`. Otherwise,
   `introduced` is set → `introduced <= date`; null → `true`. All 25 withdrawn
   entries have a null `introduced`, so the withdrawn answer is `true` up to
   and including `withdrawal_date`. The start is unknown, so a date before the
   code existed (before 1974) also returns `true`. Do not rely on that.

`introduced` is the date the ISO 3166-1 standard added the code (see
[docs/decisions/introduced-field.md](decisions/introduced-field.md)). It is not
the date a country became independent or adopted a currency.

**Data read.** `introduced` of active entries; `withdrawal_date` and
`introduced` of withdrawn entries.

**Edge cases, with the tree's values.**
- `is_active_on("DE", "1990-01-01")` → `true`: `DE` was introduced 1974-09-15.
- `is_active_on("DE", "1970-01-01")` → `false`: before `introduced`.
- `is_active_on("BJ", "2000-01-01")` → `null`: `BJ` is quarantined, so its
  `introduced` is null.
- `is_active_on("DD", "1990-01-01")` → `true`: withdrawn 1990-10-03, start unknown.
- `is_active_on("DD", "1990-10-04")` → `false`: after `withdrawal_date`. The
  withdrawal date itself is inclusive (`DD` on 1990-10-03 is `true`).
- `is_active_on("YU", "2010-01-01")` → `false`: `YU` was withdrawn 2003-07-23.
- `is_active_on("ZZ", "2000-01-01")` → `false`: unknown code.
- `is_active_on("EU", "2000-01-01")` → `null`: not officially assigned.
- `is_active_on("DE", "1990-13-01")` → `false`: malformed date. The CLI exits 2
  instead, as a usage error.

**CLI.** `is-active-on` exits 0 for `true`, 1 for `false` and 4 for `unknown`.
This differs from the EU predicates, which exit 0 for both `true` and `false`.
`introduced` exits 0 when known, 4 when null and 1 when the code is not found.

**Deprecation trigger.** None.

**What it does not answer.** When a withdrawn code started, or whether any
code existed before 1974. Dates are as sourced by the Wikipedia exception in
the ADR, not by ISO.

## Known Nulls

The `introduced` field is null for 76 active entries (27 quarantined, 46 source
silent, 3 not officially assigned) and 25 withdrawn entries. Reasons are in
`tools/introduced_snapshot.json`'s `meta.null_reasons`. 176 active entries have
a date. `is_active_on` returns `null` for the 76 active nulls.

## What no query answers

These are not registry facts and are out of scope for v1.10.0: whether a
country is a democracy, its population or GDP, its capital, its official
language (`languages[]` is not "official"), whether it is a member of NATO
or any club, a country's time zones, subdivisions, sanctions status, or
whether it is landlocked. The ones that need new fields are scheduled in
[QUERIES-DECISIONS.md](QUERIES-DECISIONS.md).

## Consistency contract

All four wrappers and the CLI must return the value in the index for every
row. `tools/check_cross_language.sh` enforces this by running the fixture's
`derived_queries` cases (generated by `tools/gen_consistency_fixture.py`,
which contains the same cases as the index above) through the Python,
JavaScript, Go and Rust wrappers and the CLI. The CLI differs from the
wrappers only in presentation: text output, and that an unknown code is
reported on stderr with exit code 1 instead of an empty, false or `None`
result. Exit codes are the CLI's standard ones for every subcommand: 0
success, 1 not found, 2 usage error, 3 registry missing. The tri-state
subcommands (`is-active-on`, `introduced`) add 4, unknown.
