package iso3166

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func mustLoad(t *testing.T) *CountryRegistry {
	t.Helper()
	reg, err := Load()
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	return reg
}

func TestLoads(t *testing.T) {
	reg := mustLoad(t)
	if len(reg.All()) == 0 {
		t.Fatal("registry is empty")
	}
	if reg.Version() == "" {
		t.Fatal("version is empty")
	}
}

func TestUSEntry(t *testing.T) {
	us := mustLoad(t).Active("US")
	if us == nil {
		t.Fatal("Active(US) is nil")
	}
	if us.Alpha2 != "US" || us.Alpha3 != "USA" || us.Numeric != "840" {
		t.Fatalf("unexpected codes: %+v", us)
	}
	if us.Name != "United States of America" {
		t.Fatalf("name: got %q", us.Name)
	}
	if us.Status != "officially-assigned" {
		t.Fatalf("status: got %q", us.Status)
	}
	if !us.Independent {
		t.Fatal("independent: want true")
	}
	if us.Region == nil || *us.Region != "Americas" {
		t.Fatalf("region: got %v", us.Region)
	}
}

func TestCaseInsensitive(t *testing.T) {
	reg := mustLoad(t)
	if reg.Active("us") != reg.Active("US") {
		t.Fatal("active('us') != active('US')")
	}
	if reg.ByAlpha3("usa") != reg.ByAlpha3("USA") {
		t.Fatal("byAlpha3 casing mismatch")
	}
}

func TestMissing(t *testing.T) {
	reg := mustLoad(t)
	if reg.Active("XX") != nil {
		t.Fatal("active(XX) should be nil")
	}
	if reg.ByAlpha3("XXX") != nil {
		t.Fatal("byAlpha3(XXX) should be nil")
	}
	if reg.ByNumeric("999") != nil {
		t.Fatal("byNumeric(999) should be nil")
	}
	if reg.Active("") != nil {
		t.Fatal("active('') should be nil")
	}
}

func TestByNumericZeroPads(t *testing.T) {
	reg := mustLoad(t)
	a := reg.ByNumeric("20")
	b := reg.ByNumeric("020")
	if a == nil || b == nil {
		t.Fatal("byNumeric returned nil")
	}
	if a != b {
		t.Fatal("byNumeric('20') != byNumeric('020')")
	}
	if a.Alpha2 != "AD" {
		t.Fatalf("expected AD, got %s", a.Alpha2)
	}
}

func TestWithdrawnNotActive(t *testing.T) {
	reg := mustLoad(t)
	if reg.Active("AN") != nil {
		t.Fatal("AN should not be active")
	}
	matches := reg.WithAlpha2("AN")
	if len(matches) != 1 {
		t.Fatalf("WithAlpha2(AN): got %d entries", len(matches))
	}
	if matches[0].Status != "withdrawn" {
		t.Fatalf("AN status: got %q", matches[0].Status)
	}
}

func TestReassignedCodesHaveTwoEntries(t *testing.T) {
	reg := mustLoad(t)
	for _, code := range []string{"AI", "SK"} {
		matches := reg.WithAlpha2(code)
		if len(matches) != 2 {
			t.Fatalf("%s: got %d entries, want 2", code, len(matches))
		}
		statuses := map[string]bool{}
		for _, m := range matches {
			statuses[m.Status] = true
		}
		if !statuses["officially-assigned"] || !statuses["withdrawn"] {
			t.Fatalf("%s: statuses are %v", code, statuses)
		}
	}
}

func TestAllActiveSorted(t *testing.T) {
	active := mustLoad(t).AllActive()
	for i := 1; i < len(active); i++ {
		if active[i-1].Alpha2 > active[i].Alpha2 {
			t.Fatalf("not sorted at %d: %s > %s",
				i, active[i-1].Alpha2, active[i].Alpha2)
		}
	}
}

func TestSummaryConsistency(t *testing.T) {
	reg := mustLoad(t)
	s := reg.Summary()
	if s.Total != len(reg.All()) {
		t.Fatalf("total: got %d, want %d", s.Total, len(reg.All()))
	}
	if s.Active != len(reg.AllActive()) {
		t.Fatalf("active: got %d, want %d", s.Active, len(reg.AllActive()))
	}
	if s.Withdrawn != len(reg.AllWithdrawn()) {
		t.Fatalf("withdrawn: got %d, want %d", s.Withdrawn, len(reg.AllWithdrawn()))
	}
}

func TestLoadFromMissing(t *testing.T) {
	if _, err := LoadFrom("/nonexistent.json"); err == nil {
		t.Fatal("LoadFrom(/nonexistent.json) did not return an error")
	}
}

func TestLoadFromMalformed(t *testing.T) {
	p := filepath.Join(t.TempDir(), "bad.json")
	if err := os.WriteFile(p, []byte("{not json"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadFrom(p); err == nil {
		t.Fatal("LoadFrom on malformed JSON did not return an error")
	}
}

// ----------------------------------------------------------------
// Cross-language consistency tests
// ----------------------------------------------------------------

type fixtureDoc struct {
	LookupAlpha2 []struct {
		Input       string  `json:"input"`
		Alpha2      string  `json:"alpha_2"`
		Alpha3      string  `json:"alpha_3"`
		Numeric     string  `json:"numeric"`
		Name        string  `json:"name"`
		Status      string  `json:"status"`
		Independent bool    `json:"independent"`
		Region      *string `json:"region"`
	} `json:"lookup_alpha2"`
	LookupAlpha2Missing []string `json:"lookup_alpha2_missing"`
	LookupAlpha3        []struct {
		Input  string `json:"input"`
		Alpha2 string `json:"alpha_2"`
	} `json:"lookup_alpha3"`
	LookupNumeric []struct {
		Input  string `json:"input"`
		Alpha2 string `json:"alpha_2"`
	} `json:"lookup_numeric"`
	Counts struct {
		Total     int            `json:"total"`
		Active    int            `json:"active"`
		Withdrawn int            `json:"withdrawn"`
		ByStatus  map[string]int `json:"by_status"`
	} `json:"counts"`
	OverlapCodes map[string][]string `json:"overlap_codes"`
	RegionQuery  []struct {
		Region      string   `json:"region"`
		MinCount    int      `json:"min_count"`
		MustContain []string `json:"must_contain"`
	} `json:"region_query"`
	Currencies   map[string][]string `json:"currencies"`
	LookupFields []struct {
		Input         string   `json:"input"`
		OfficialName  *string  `json:"official_name"`
		CurrencyCodes []string `json:"currency_codes"`
		CallingCodes  []string `json:"calling_codes"`
		TLDs          []string `json:"tlds"`
	} `json:"lookup_fields"`
	LookupWithdrawn []struct {
		Input          string  `json:"input"`
		Alpha2         string  `json:"alpha_2"`
		Name           string  `json:"name"`
		Status         string  `json:"status"`
		WithdrawalDate *string `json:"withdrawal_date"`
	} `json:"lookup_withdrawn"`
	CountriesWith map[string][]string `json:"countries_with"`
	Search        []struct {
		Query       string   `json:"query"`
		MinCount    int      `json:"min_count"`
		MustContain []string `json:"must_contain"`
	} `json:"search"`
}

func loadFixture(t *testing.T) fixtureDoc {
	t.Helper()
	path := filepath.Join("..", "..", "tests", "cross_language_consistency.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	var doc fixtureDoc
	if err := json.Unmarshal(data, &doc); err != nil {
		t.Fatalf("parse fixture: %v", err)
	}
	return doc
}

func TestFixtureLookupAlpha2(t *testing.T) {
	reg := mustLoad(t)
	for _, c := range loadFixture(t).LookupAlpha2 {
		got := reg.Active(c.Input)
		if got == nil {
			t.Fatalf("active(%q) is nil", c.Input)
		}
		if got.Alpha2 != c.Alpha2 || got.Alpha3 != c.Alpha3 || got.Numeric != c.Numeric {
			t.Fatalf("%s: codes mismatch: %+v", c.Input, got)
		}
		if got.Name != c.Name {
			t.Fatalf("%s: name got %q want %q", c.Input, got.Name, c.Name)
		}
		if got.Status != c.Status {
			t.Fatalf("%s: status got %q want %q", c.Input, got.Status, c.Status)
		}
		if got.Independent != c.Independent {
			t.Fatalf("%s: independent got %v want %v",
				c.Input, got.Independent, c.Independent)
		}
		switch {
		case c.Region == nil && got.Region != nil:
			t.Fatalf("%s: region got %q want nil", c.Input, *got.Region)
		case c.Region != nil && got.Region == nil:
			t.Fatalf("%s: region got nil want %q", c.Input, *c.Region)
		case c.Region != nil && got.Region != nil && *c.Region != *got.Region:
			t.Fatalf("%s: region got %q want %q", c.Input, *got.Region, *c.Region)
		}
	}
}

func TestFixtureLookupAlpha2Missing(t *testing.T) {
	reg := mustLoad(t)
	for _, code := range loadFixture(t).LookupAlpha2Missing {
		if reg.Active(code) != nil {
			t.Fatalf("active(%q) should be nil", code)
		}
	}
}

func TestFixtureLookupAlpha3(t *testing.T) {
	reg := mustLoad(t)
	for _, c := range loadFixture(t).LookupAlpha3 {
		got := reg.ByAlpha3(c.Input)
		if got == nil {
			t.Fatalf("byAlpha3(%q) is nil", c.Input)
		}
		if got.Alpha2 != c.Alpha2 {
			t.Fatalf("%s: alpha_2 got %q want %q", c.Input, got.Alpha2, c.Alpha2)
		}
	}
}

func TestFixtureLookupNumeric(t *testing.T) {
	reg := mustLoad(t)
	for _, c := range loadFixture(t).LookupNumeric {
		got := reg.ByNumeric(c.Input)
		if got == nil {
			t.Fatalf("byNumeric(%q) is nil", c.Input)
		}
		if got.Alpha2 != c.Alpha2 {
			t.Fatalf("%s: alpha_2 got %q want %q", c.Input, got.Alpha2, c.Alpha2)
		}
	}
}

func TestFixtureCounts(t *testing.T) {
	reg := mustLoad(t)
	fx := loadFixture(t)
	s := reg.Summary()
	if s.Total != fx.Counts.Total {
		t.Fatalf("total: got %d want %d", s.Total, fx.Counts.Total)
	}
	if s.Active != fx.Counts.Active {
		t.Fatalf("active: got %d want %d", s.Active, fx.Counts.Active)
	}
	if s.Withdrawn != fx.Counts.Withdrawn {
		t.Fatalf("withdrawn: got %d want %d", s.Withdrawn, fx.Counts.Withdrawn)
	}
	for status, expected := range fx.Counts.ByStatus {
		if got := s.ByStatus[status]; got != expected {
			t.Fatalf("status %s: got %d want %d", status, got, expected)
		}
	}
}

func TestFixtureOverlapCodes(t *testing.T) {
	reg := mustLoad(t)
	for code, expected := range loadFixture(t).OverlapCodes {
		matches := reg.WithAlpha2(code)
		got := map[string]bool{}
		for _, m := range matches {
			got[m.Status] = true
		}
		if len(got) != len(expected) {
			t.Fatalf("%s: got %d statuses, want %d", code, len(got), len(expected))
		}
		for _, want := range expected {
			if !got[want] {
				t.Fatalf("%s: missing status %q", code, want)
			}
		}
	}
}

func TestFixtureRegionQuery(t *testing.T) {
	reg := mustLoad(t)
	for _, c := range loadFixture(t).RegionQuery {
		results := reg.Region(c.Region)
		if len(results) < c.MinCount {
			t.Fatalf("region %s: got %d want >= %d",
				c.Region, len(results), c.MinCount)
		}
		have := map[string]bool{}
		for _, r := range results {
			have[r.Alpha2] = true
		}
		for _, code := range c.MustContain {
			if !have[code] {
				t.Fatalf("region %s missing %s", c.Region, code)
			}
		}
	}
}

func TestFixtureCurrencies(t *testing.T) {
	reg := mustLoad(t)
	for code, expected := range loadFixture(t).Currencies {
		got := reg.Currencies(code)
		if len(got) != len(expected) {
			t.Fatalf("%s: got %v want %v", code, got, expected)
		}
	}
}

func TestFixtureCountriesWith(t *testing.T) {
	reg := mustLoad(t)
	for curr, expected := range loadFixture(t).CountriesWith {
		got := reg.CountriesWith(curr)
		if len(got) != len(expected) {
			t.Fatalf("%s: got %d entries want %d",
				curr, len(got), len(expected))
		}
	}
}

func TestFixtureSearch(t *testing.T) {
	reg := mustLoad(t)
	for _, c := range loadFixture(t).Search {
		results := reg.Search(c.Query)
		if len(results) < c.MinCount {
			t.Fatalf("search %q: got %d want >= %d",
				c.Query, len(results), c.MinCount)
		}
		have := map[string]bool{}
		for _, r := range results {
			have[r.Alpha2] = true
		}
		for _, code := range c.MustContain {
			if !have[code] {
				t.Fatalf("search %q missing %s", c.Query, code)
			}
		}
	}
}

func TestFixtureLookupWithdrawn(t *testing.T) {
	reg := mustLoad(t)
	for _, c := range loadFixture(t).LookupWithdrawn {
		matches := reg.WithAlpha2(c.Input)
		found := false
		for _, m := range matches {
			if m.Status == "withdrawn" && m.Name == c.Name {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("%s: withdrawn entry not found", c.Input)
		}
	}
}

func TestFixtureLookupFields(t *testing.T) {
	reg := mustLoad(t)
	for _, c := range loadFixture(t).LookupFields {
		got := reg.Active(c.Input)
		if got == nil {
			t.Fatalf("%s missing", c.Input)
		}
		if got.OfficialName == nil || c.OfficialName == nil || *got.OfficialName != *c.OfficialName {
			t.Fatalf("%s: official_name mismatch", c.Input)
		}
		// compare slices
		if !sliceEq(got.CurrencyCodes, c.CurrencyCodes) {
			t.Fatalf("%s: currency_codes mismatch", c.Input)
		}
		if !sliceEq(got.CallingCodes, c.CallingCodes) {
			t.Fatalf("%s: calling_codes mismatch", c.Input)
		}
		if !sliceEq(got.TLDs, c.TLDs) {
			t.Fatalf("%s: tlds mismatch", c.Input)
		}
	}
}

func sliceEq(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
