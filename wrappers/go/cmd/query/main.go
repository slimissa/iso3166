// Command query (design in docs/QUERIES.md) runs one derived query and prints the result as
// compact JSON (null when the query has no answer). Used by the
// cross-language derived-query check in tools/check_cross_language.sh.
//
//	cd wrappers/go && go run ./cmd/query is_eu DE
//	# true
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"

	iso3166 "github.com/slimissa/iso3166-go"
)

func emit(v interface{}) {
	b, err := json.Marshal(v)
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
	fmt.Println(string(b))
}

// opt turns (value, ok) into the value or nil, so a miss prints null.
func opt(v []string, ok bool) interface{} {
	if !ok {
		return nil
	}
	return v
}

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintln(os.Stderr, "usage: query METHOD ARG [ARG]")
		os.Exit(2)
	}
	reg, err := iso3166.Load()
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(3)
	}
	a := func(i int) string {
		if i < len(os.Args) {
			return os.Args[i]
		}
		return ""
	}
	switch os.Args[1] {
	case "is_eu":
		emit(reg.IsEU(a(2)))
	case "is_eea":
		emit(reg.IsEEA(a(2)))
	case "is_eurozone":
		emit(reg.IsEurozone(a(2)))
	case "region_tree":
		emit(reg.RegionTree(a(2)))
	case "borders_transitively":
		n, convErr := strconv.Atoi(a(3))
		if convErr != nil {
			n = 0
		}
		emit(reg.BordersTransitively(a(2), n))
	case "succession_path":
		emit(opt(reg.SuccessionPath(a(2), a(3))))
	case "successors":
		emit(reg.Successors(a(2)))
	case "predecessors":
		emit(reg.Predecessors(a(2)))
	case "calling_code_for":
		emit(reg.CallingCodeFor(a(2)))
	case "currency_at":
		emit(opt(reg.CurrencyAt(a(2), a(3))))
	case "region_countries":
		emit(reg.RegionCountries(a(2), a(3)))
	default:
		fmt.Fprintln(os.Stderr, "error: unknown query:", os.Args[1])
		os.Exit(2)
	}
}
