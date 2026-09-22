// Command lookup prints the alpha-2, alpha-3, numeric, and name of a
// single country. Used by the cross-language verification in Phase 6.6.
//
//	cd wrappers/go && go run ./cmd/lookup US
//	# US USA 840 United States of America
package main

import (
	"fmt"
	"os"

	iso3166 "github.com/slimissa/iso3166-go"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: lookup CODE")
		os.Exit(2)
	}

	reg, err := iso3166.Load()
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}

	c := reg.Active(os.Args[1])
	if c == nil {
		fmt.Fprintln(os.Stderr, "not found:", os.Args[1])
		os.Exit(1)
	}

	fmt.Printf("%s %s %s %s\n", c.Alpha2, c.Alpha3, c.Numeric, c.Name)
}
