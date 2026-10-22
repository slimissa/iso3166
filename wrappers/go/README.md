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

## Tests

```bash
go test ./...
```

## License

Apache 2.0.