package iso3166

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"testing"
)

// The shared fixture's derived_queries.cases (docs/QUERIES.md), the same
// cases the Python, JavaScript and Rust suites and the CLI must reproduce.
type derivedCase struct {
	Query    string            `json:"query"`
	Args     []json.RawMessage `json:"args"`
	Expected json.RawMessage   `json:"expected"`
}

type derivedFixture struct {
	DerivedQueries struct {
		Enforced bool          `json:"enforced"`
		Cases    []derivedCase `json:"cases"`
	} `json:"derived_queries"`
}

func loadDerivedFixture(t *testing.T) derivedFixture {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("..", "..", "tests", "cross_language_consistency.json"))
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	var doc derivedFixture
	if err := json.Unmarshal(data, &doc); err != nil {
		t.Fatalf("parse fixture: %v", err)
	}
	return doc
}

// derivedArgs decodes the fixture arguments as the strings cmd/query passes.
func derivedArgs(t *testing.T, c derivedCase) []string {
	t.Helper()
	out := make([]string, len(c.Args))
	for i, raw := range c.Args {
		var s string
		if err := json.Unmarshal(raw, &s); err == nil {
			out[i] = s
			continue
		}
		var n int
		if err := json.Unmarshal(raw, &n); err != nil {
			t.Fatalf("%s: argument %d is neither a string nor an integer: %s", c.Query, i, raw)
		}
		out[i] = strconv.Itoa(n)
	}
	return out
}

// runDerived mirrors cmd/query's dispatch and returns the value it prints.
func runDerived(t *testing.T, r *CountryRegistry, c derivedCase) interface{} {
	t.Helper()
	a := derivedArgs(t, c)
	arg := func(i int) string {
		if i < len(a) {
			return a[i]
		}
		return ""
	}
	opt := func(v []string, ok bool) interface{} {
		if !ok {
			return nil
		}
		return v
	}
	must := func(v interface{}, err error) interface{} {
		t.Helper()
		if err != nil {
			t.Fatalf("%s(%v): %v", c.Query, a, err)
		}
		return v
	}
	switch c.Query {
	case "is_eu":
		return r.IsEU(arg(0))
	case "is_eea":
		return r.IsEEA(arg(0))
	case "is_eurozone":
		return r.IsEurozone(arg(0))
	case "region_tree":
		return r.RegionTree(arg(0))
	case "borders_transitively":
		n, err := strconv.Atoi(arg(1))
		if err != nil {
			t.Fatalf("borders_transitively: max_hops %q is not an integer", arg(1))
		}
		return r.BordersTransitively(arg(0), n)
	case "succession_path":
		return opt(r.SuccessionPath(arg(0), arg(1)))
	case "successors":
		return r.Successors(arg(0))
	case "predecessors":
		return r.Predecessors(arg(0))
	case "calling_code_for":
		return r.CallingCodeFor(arg(0))
	case "currency_at":
		return opt(r.CurrencyAt(arg(0), arg(1)))
	case "region_countries":
		return r.RegionCountries(arg(0), arg(1))
	case "is_active_on":
		return must(r.IsActiveOn(arg(0), arg(1)))
	case "is_eu_member_at":
		return must(r.IsEUMemberAt(arg(0), arg(1)))
	case "is_eea_member_at":
		return must(r.IsEEAMemberAt(arg(0), arg(1)))
	case "is_eurozone_member_at":
		return must(r.IsEurozoneMemberAt(arg(0), arg(1)))
	case "is_in_customs_union_at":
		return must(r.IsInCustomsUnionAt(arg(0), arg(1)))
	}
	t.Fatalf("derived_queries: no Go mapping for query %q", c.Query)
	return nil
}

// normalize round-trips v through JSON so a nil pointer, a typed slice and the
// fixture's expected value compare as the plain JSON values they print as.
func normalize(t *testing.T, v interface{}) interface{} {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatalf("marshal %v: %v", v, err)
	}
	var out interface{}
	if err := json.Unmarshal(b, &out); err != nil {
		t.Fatalf("unmarshal %s: %v", b, err)
	}
	return out
}

func TestFixtureDerivedQueries(t *testing.T) {
	doc := loadDerivedFixture(t)
	if !doc.DerivedQueries.Enforced {
		t.Skip("derived_queries enforced=false")
	}
	cases := doc.DerivedQueries.Cases
	if len(cases) < 129 {
		t.Fatalf("the fixture has only %d derived cases, want at least 129", len(cases))
	}
	r := mustLoad(t)
	for _, c := range cases {
		var want interface{}
		if err := json.Unmarshal(c.Expected, &want); err != nil {
			t.Fatalf("%s: bad expected %s", c.Query, c.Expected)
		}
		got := normalize(t, runDerived(t, r, c))
		if !reflect.DeepEqual(got, want) {
			t.Errorf("%s(%s) = %v, want %v", c.Query, derivedArgs(t, c), got, want)
		}
	}
}
