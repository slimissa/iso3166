# iso3166-go

Go wrapper for the [ISO 3166 country registry](https://github.com/slimissa/iso3166).

## Install

```bash
go get github.com/slimissa/iso3166-go

Until the module is published (v1.2.0), install from the repository:
bash

go get github.com/slimissa/iso3166@v0.1.0

or vendor it:
bash

go mod edit -replace github.com/slimissa/iso3166-go=./path/to/wrappers/go

Library
go

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
        fmt.Println(us.Alpha3, us.Name)   // USA United States of America
    }

    fmt.Println(reg.ByNumeric("840").Alpha2)      // US
    fmt.Println(reg.ByAlpha3("GBR").Name)         // United Kingdom ...
    fmt.Println(len(reg.Region("Europe")))        // number of European entries
    fmt.Println(len(reg.Search("united")))
    fmt.Println(reg.Summary())
}

Active returns nil for an unknown code. Use WithAlpha2 to retrieve
both the active and withdrawn entries for a reassigned code such as
AI or SK.
Tests
bash

go test ./...

License

Apache 2.0.
