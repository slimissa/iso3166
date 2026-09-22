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
    if us != nil {
        fmt.Println(us.Alpha3, us.Name)          // USA United States of America
    }

    fmt.Println(reg.ByNumeric("840").Alpha2)     // US
    fmt.Println(reg.ByAlpha3("GBR").Name)        // United Kingdom ...
    fmt.Println(len(reg.Region("Europe")))       // number of European entries
    fmt.Println(len(reg.Search("united")))
    fmt.Println(reg.Summary())
}
```

`Active` returns `nil` for an unknown code. Use `WithAlpha2` to
retrieve both the active and withdrawn entries for a reassigned code
such as `AI` or `SK`.

## Tests

```bash
go test ./...
```

## License

Apache 2.0.