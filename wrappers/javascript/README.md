# iso3166-registry (JavaScript)

JavaScript wrapper for the [ISO 3166 country registry](https://github.com/slimissa/iso3166).

## Install

From the repository:

```bash
npm install ./wrappers/javascript
```

Zero runtime dependencies. Requires Node 18 or newer for the built-in
test runner (the library itself works on Node 12+).

Publication to npm is tracked for v1.2.0.

## Library

```javascript
const { CountryRegistry } = require("iso3166-registry");

const reg = new CountryRegistry();

const us = reg.active("US");
console.log(us.alpha_3, us.name);                // USA United States of America

console.log(reg.byNumeric("840").alpha_2);       // US
console.log(reg.byAlpha3("GBR").name);           // United Kingdom ...

console.log(reg.region("Europe").length);        // number of European entries
console.log(reg.search("united").length);
console.log(reg.summary());
```

`active()` returns `null` for an unknown code. Use `withAlpha2()` to
retrieve both the active and withdrawn entries for a reassigned code
such as `AI` or `SK`.

## Derived queries (v1.10.0+)

The registry answers questions that need more than one entry: club membership, the region tree, land borders, succession, calling codes, currency and existence on a date. There are 17 queries, specified once in [docs/QUERIES.md](../../docs/QUERIES.md); this wrapper implements all of them, and `tools/check_cross_language.sh` checks the Python, JavaScript, Rust and Go wrappers and the CLI against the same 129 cases of `tests/cross_language_consistency.json`, so each answers the same question the same way.

| Query | Method | Since |
|-------|--------|-------|
| 1. `is_eu` | `reg.isEu()` | v1.10.0 |
| 1. `is_eea` | `reg.isEea()` | v1.10.0 |
| 1. `is_eurozone` | `reg.isEurozone()` | v1.10.0 |
| 2. `region_tree` | `reg.regionTree()` | v1.10.0 |
| 8. `region_countries` | `reg.regionCountries()` | v1.10.0 |
| 3. `borders_transitively` | `reg.bordersTransitively()` | v1.10.0 |
| 4. `succession_path` | `reg.successionPath()` | v1.10.0 |
| 5. `successors` | `reg.successors()` | v1.10.0 |
| 5. `predecessors` | `reg.predecessors()` | v1.10.0 |
| 6. `calling_code_for` | `reg.callingCodeFor()` | v1.10.0 |
| 7. `currency_at` | `reg.currencyAt()` | v1.10.0 |
| 9. `is_active_on` | `reg.isActiveOn()` | v1.11.0 |
| 11. `active_on` | `reg.activeOn()` | v1.12.5 |
| 10. `is_eu_member_at` | `reg.isEuMemberAt()` | v1.12.0 |
| 10. `is_eea_member_at` | `reg.isEeaMemberAt()` | v1.12.0 |
| 10. `is_eurozone_member_at` | `reg.isEurozoneMemberAt()` | v1.12.0 |
| 10. `is_in_customs_union_at` | `reg.isInCustomsUnionAt()` | v1.12.0 |

```javascript
const { CountryRegistry } = require("iso3166-registry");

const reg = new CountryRegistry();

reg.isEu("DE");                              // true   (current member only)
reg.regionTree("FR");                        // ["Europe", "Western Europe"]
reg.bordersTransitively("US", 1);            // ["CA", "MX"]   (maxHops defaults to 2)
reg.successionPath("YU", "ME");              // ["YU", "CS", "ME"]
reg.successors("YU");                        // ["CS", "ME", "RS"]
reg.callingCodeFor("+49");                   // ["DE"]
reg.isEuMemberAt("GB", "2010-01-01");        // true
reg.isEuMemberAt("GB", "2023-01-01");        // false
reg.isActiveOn("YU", "1990-01-01");          // true   (true / false / null: tri-state)
```

A malformed date (`"2010-13-45"`, `"2020-01-01\n"`) throws a `TypeError` from
`isActiveOn`, `activeOn` and the four `*MemberAt` queries; `currencyAt` answers
`null`. So does an extra argument. A query with no answer returns `null`
(`successionPath`, `currencyAt`) or an empty array; an unknown code never
throws. Results are frozen: `activeOn(date)` returns a frozen object, and
`KNOWN_EU_MEMBERS` is a Set that refuses `add`, `delete` and `clear`.

## Tests

```bash
npm test
```

## License

Apache 2.0.