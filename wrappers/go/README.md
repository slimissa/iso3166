# iso3166-go

Go wrapper for the [ISO 3166 country registry](https://github.com/slimissa/iso3166).

## Install

Source-only until v1.2.0. From a checkout of this repository:

```bash
go mod edit -replace github.com/slimissa/iso3166-go=./path/to/wrappers/go
```

Or vendor the `wrappers/go` directory directly.

Publication to the Go module proxy is tracked for v1.2.0, at which
point the module will resolve as
`github.com/slimissa/iso3166-go`. Because the module lives in a
subdirectory of the repository, the release tag will be
`wrappers/go/vX.Y.Z`, following the standard convention for
subdirectory modules.

## Library

```go
package main

import (
    "fmt"
    "log"

    iso3166 "github.com/slimissa/iso3166-go"
)

func main() {
    reg, err := iso3166.Load()
    if err != nil {
        log.Fatal(err)
    }

    us := reg.Active("US")
    if us.Exists() {
        fmt.Println(us.Alpha3, us.Name)          // USA United States of America
    }

    fmt.Println(reg.ByNumeric("840").Alpha2)     // US
    fmt.Println(reg.ByAlpha3("GBR").Name)        // United Kingdom ...
    fmt.Println(len(reg.Region("Europe")))       // number of European entries
    fmt.Println(len(reg.Search("united")))
    fmt.Println(reg.Summary())
}
```

`Active`, `ByAlpha2`, `ByAlpha3` and `ByNumeric` return a `Country`
**by value** (changed from `*Country` in v1.8.0). An unknown, empty or
withdrawn code returns the zero `Country`; test it with `Exists()`, not
`== nil`. The returned value owns private copies of its slices and
string pointers, so changing it never changes the registry.

```go
if c := reg.ByNumeric("20"); c.Exists() { // "20" and "020" are equal
    fmt.Println(c.Alpha2)                  // AD
}
```

`ByNumeric` returns the zero `Country` for `""`, `"0"` and `"000"`, and
does not trim whitespace. `WithAlpha2`, `WithAlpha3` and `WithNumeric`
return every entry, active and withdrawn, for a code; for a reassigned
code such as `AI` or `SK` the active entry comes first. The list queries
(`All`, `Region`, `Search`, `WithAlpha2`, ...) still return
`[]*Country`; treat those entries as read-only.

Migration from v1.7: replace `c != nil` with `c.Exists()` and
`c == nil` with `!c.Exists()`. See
[docs/decisions/input-contract.md](../../docs/decisions/input-contract.md).

## Derived queries (v1.10.0+)

The registry answers questions that need more than one entry: club membership, the region tree, land borders, succession, calling codes, currency and existence on a date. There are 17 queries, specified once in [docs/QUERIES.md](../../docs/QUERIES.md); this wrapper implements all of them, and `tools/check_cross_language.sh` checks the Python, JavaScript, Rust and Go wrappers and the CLI against the same 129 cases of `tests/cross_language_consistency.json`, so each answers the same question the same way.

| Query | Method | Since |
|-------|--------|-------|
| 1. `is_eu` | `reg.IsEU()` | v1.10.0 |
| 1. `is_eea` | `reg.IsEEA()` | v1.10.0 |
| 1. `is_eurozone` | `reg.IsEurozone()` | v1.10.0 |
| 2. `region_tree` | `reg.RegionTree()` | v1.10.0 |
| 8. `region_countries` | `reg.RegionCountries()` | v1.10.0 |
| 3. `borders_transitively` | `reg.BordersTransitively()` | v1.10.0 |
| 4. `succession_path` | `reg.SuccessionPath()` | v1.10.0 |
| 5. `successors` | `reg.Successors()` | v1.10.0 |
| 5. `predecessors` | `reg.Predecessors()` | v1.10.0 |
| 6. `calling_code_for` | `reg.CallingCodeFor()` | v1.10.0 |
| 7. `currency_at` | `reg.CurrencyAt()` | v1.10.0 |
| 9. `is_active_on` | `reg.IsActiveOn()` | v1.11.0 |
| 11. `active_on` | `reg.ActiveOn()` | v1.12.5 |
| 10. `is_eu_member_at` | `reg.IsEUMemberAt()` | v1.12.0 |
| 10. `is_eea_member_at` | `reg.IsEEAMemberAt()` | v1.12.0 |
| 10. `is_eurozone_member_at` | `reg.IsEurozoneMemberAt()` | v1.12.0 |
| 10. `is_in_customs_union_at` | `reg.IsInCustomsUnionAt()` | v1.12.0 |

```go
package main

import (
    "fmt"
    "log"

    iso3166 "github.com/slimissa/iso3166-go"
)

func main() {
    reg, err := iso3166.Load()
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println(reg.IsEU("DE"))                         // true   (current member only)
    fmt.Println(reg.RegionTree("FR"))                   // [Europe Western Europe]
    fmt.Println(reg.BordersTransitively("US", 1))       // [CA MX]   (maxHops is required)
    fmt.Println(reg.SuccessionPath("YU", "ME"))         // [YU CS ME] true
    fmt.Println(reg.Successors("YU"))                   // [CS ME RS]
    fmt.Println(reg.CallingCodeFor("+49"))              // [DE]
    fmt.Println(reg.IsEUMemberAt("GB", "2010-01-01"))   // true <nil>
    fmt.Println(reg.IsEUMemberAt("GB", "2023-01-01"))   // false <nil>

    active, _ := reg.IsActiveOn("YU", "1990-01-01")     // *bool: true / false / nil (tri-state)
    fmt.Println(*active)                                // true
}
```

A malformed date is a `*InvalidDateError` from `IsActiveOn`, `ActiveOn` and the
four `*MemberAt` / `IsInCustomsUnionAt` queries; `CurrencyAt` answers
`(nil, false)`. `ValidDate(s)` is exported, so a caller can check a date first.
A query with no answer returns `ok == false` (`SuccessionPath`, `CurrencyAt`) or
an empty slice; an unknown code never fails. `go run ./cmd/query METHOD ARG...`
prints any query as JSON; a `max_hops` that is not an integer exits 2.

## Tests

```bash
go test ./...
```

## License

Apache 2.0.