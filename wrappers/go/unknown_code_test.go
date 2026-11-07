package iso3166

import "testing"

// The unknown-code contract (README section 4b, v1.12.5), Go column.
func TestUnknownCodeContract(t *testing.T) {
	r := mustLoad(t)
	if r.Active("XX").Exists() {
		t.Error(`Active("XX") must not exist`)
	}
	if got := r.Currencies("XX"); len(got) != 0 {
		t.Errorf(`Currencies("XX") = %v, want empty`, got)
	}
	if got, ok := r.CurrencyAt("XX", "2000-01-01"); ok || got != nil {
		t.Errorf(`CurrencyAt("XX") = %v, %v; want nil, false`, got, ok)
	}
	if v, err := r.IsActiveOn("XX", "2000-01-01"); err != nil || v == nil || *v {
		t.Errorf(`IsActiveOn("XX") = %v, %v; want pointer to false`, v, err)
	}
	if got, err := r.IsEUMemberAt("XX", "2010-01-01"); err != nil || got {
		t.Errorf(`IsEUMemberAt("XX") = %v, %v; want false, nil`, got, err)
	}
}

func TestUnknownCodeLooksLikeNoCurrency(t *testing.T) {
	r := mustLoad(t)
	if len(r.Currencies("XX")) != 0 || len(r.Currencies("AQ")) != 0 {
		t.Fatal("XX and AQ both have no currencies")
	}
	if r.Active("XX").Exists() || !r.Active("AQ").Exists() {
		t.Error("tell them apart with Active(code).Exists() == false")
	}
}

func TestLookupCaseAndWhitespace(t *testing.T) {
	r := mustLoad(t)
	if !r.Active("us").Exists() || r.Active("us").Alpha2 != "US" {
		t.Error(`Active("us") must find US`)
	}
	if r.Active(" us ").Exists() {
		t.Error(`Active(" us ") must be nil: lookups do not strip`)
	}
	if got, _ := r.IsEUMemberAt(" de ", "2010-01-01"); !got {
		t.Error(`IsEUMemberAt(" de ") must strip and answer true`)
	}
	if r.Active("USA").Exists() {
		t.Error(`Active("USA") must be nil: use ByAlpha3`)
	}
}
