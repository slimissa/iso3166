package iso3166

import (
	"reflect"
	"testing"
)

func TestDerivedQueriesWorkedExamples(t *testing.T) {
	r := mustLoad(t)
	for code, want := range map[string]bool{"DE": true, "de": true, "GB": false, "CH": false, "XK": false} {
		if got := r.IsEU(code); got != want {
			t.Errorf("IsEU(%q) = %v, want %v", code, got, want)
		}
	}
	if !r.IsEEA("NO") || r.IsEEA("CH") {
		t.Error("IsEEA: NO must be true, CH false")
	}
	if !r.IsEurozone("DE") || !r.IsEurozone("BG") || r.IsEurozone("AD") || r.IsEurozone("ME") || r.IsEurozone("GB") {
		t.Error("IsEurozone worked examples")
	}
	eq := func(name string, got, want []string) {
		t.Helper()
		if !reflect.DeepEqual(got, want) {
			t.Errorf("%s = %v, want %v", name, got, want)
		}
	}
	eq("RegionTree(FR)", r.RegionTree("FR"), []string{"Europe", "Western Europe"})
	eq("RegionTree(TW)", r.RegionTree("TW"), []string{})
	eq("RegionTree(AQ)", r.RegionTree("AQ"), []string{})
	eq("BordersTransitively(US,1)", r.BordersTransitively("US", 1), []string{"CA", "MX"})
	eq("BordersTransitively(AQ,2)", r.BordersTransitively("AQ", 2), []string{})
	if p, ok := r.SuccessionPath("YU", "RS"); !ok {
		t.Error("SuccessionPath(YU,RS) not ok")
	} else {
		eq("SuccessionPath(YU,RS)", p, []string{"YU", "CS", "RS"})
	}
	if _, ok := r.SuccessionPath("US", "GB"); ok {
		t.Error("SuccessionPath(US,GB) must not exist")
	}
	if _, ok := r.SuccessionPath("SU", "RU"); ok {
		t.Error("SuccessionPath(SU,RU) must not exist: SU has no replaced_by")
	}
	eq("Successors(YU)", r.Successors("YU"), []string{"CS", "ME", "RS"})
	eq("Predecessors(RS)", r.Predecessors("RS"), []string{"CS", "YU"})
	eq("CallingCodeFor(+44)", r.CallingCodeFor("+44 20 7946 0958"), []string{"GB", "GG", "IM", "JE"})
	eq("CallingCodeFor(+999)", r.CallingCodeFor("+999 123"), []string{})
	eq("CallingCodeFor(nonsense)", r.CallingCodeFor("nonsense"), []string{})
	if c, ok := r.CurrencyAt("DE", "2000-01-01"); !ok {
		t.Error("CurrencyAt(DE) not ok")
	} else {
		eq("CurrencyAt(DE)", c, []string{"EUR"})
	}
	if _, ok := r.CurrencyAt("DE", "1970-01-01"); ok {
		t.Error("CurrencyAt(DE,1970) must be unknown (before introduced)")
	}
	if c, ok := r.CurrencyAt("DD", "1990-01-01"); !ok {
		t.Error("CurrencyAt(DD,1990-01-01) not ok")
	} else {
		eq("CurrencyAt(DD,1990)", c, []string{"EUR"})
	}
	if _, ok := r.CurrencyAt("DD", "1990-10-04"); ok {
		t.Error("CurrencyAt(DD,1990-10-04) must be unknown (after withdrawal)")
	}
	if _, ok := r.CurrencyAt("BJ", "2000-01-01"); ok {
		t.Error("CurrencyAt(BJ) must be unknown (introduced is null)")
	}
	if _, ok := r.CurrencyAt("DE", "2000-13-01"); ok {
		t.Error("malformed date must be unknown")
	}
	eq("RegionCountries(Europe,WE)", r.RegionCountries("Europe", "Western Europe"),
		[]string{"AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"})
	eq("RegionCountries(Antarctica)", r.RegionCountries("Antarctica", ""), []string{})
}
