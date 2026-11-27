package iso3166

import (
	"encoding/json"
	"os"
	"path/filepath"
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

// v1.12.5, Query 11: ActiveOn is IsActiveOn for every code.
func TestActiveOn1990(t *testing.T) {
	r := mustLoad(t)
	m, err := r.ActiveOn("1990-01-01")
	if err != nil {
		t.Fatal(err)
	}
	if len(m) != 277 {
		t.Fatalf("len = %d, want 277", len(m))
	}
	var yes, no, unknown int
	for code, v := range m {
		want, _ := r.IsActiveOn(code, "1990-01-01")
		if (v == nil) != (want == nil) || (v != nil && *v != *want) {
			t.Errorf("ActiveOn[%s] disagrees with IsActiveOn", code)
		}
		switch {
		case v == nil:
			unknown++
		case *v:
			yes++
		default:
			no++
		}
	}
	// CS (withdrawn) is dated 2003-07-23 by Newsletter V-8: false on 1990-01-01.
	// NU is quarantined (Newsletter V-4 renames Niue in 2002): unknown, not false.
	// PU and FX (v1.14.0) have no withdrawal date: unknown.
	if yes != 169 || no != 29 || unknown != 79 {
		t.Errorf("true/false/unknown = %d/%d/%d, want 169/29/79", yes, no, unknown)
	}
	if _, err := r.ActiveOn("1990-13-01"); err == nil {
		t.Error("malformed date must return an error")
	}
}

// v1.14.0: a withdrawn entry whose ISO page gives no withdrawal date.
func TestIsActiveOnWithdrawnWithoutWithdrawalDateIsUnknown(t *testing.T) {
	raw, err := os.ReadFile("iso3166.json")
	if err != nil {
		t.Fatal(err)
	}
	var data map[string]any
	if err := json.Unmarshal(raw, &data); err != nil {
		t.Fatal(err)
	}
	for _, e := range data["countries"].(map[string]any)["withdrawn"].([]any) {
		m := e.(map[string]any)
		switch m["alpha_2"] {
		case "NT":
			m["withdrawal_date"], m["alpha_4"], m["introduced"] = nil, "NTHH", nil
		case "MI":
			m["withdrawal_date"], m["alpha_4"], m["introduced"] = nil, "MIUM", "1975-01-01"
		}
	}
	out, _ := json.Marshal(data)
	path := filepath.Join(t.TempDir(), "iso3166.json")
	if err := os.WriteFile(path, out, 0o644); err != nil {
		t.Fatal(err)
	}
	r, err := LoadFrom(path)
	if err != nil {
		t.Fatal(err)
	}
	for _, c := range []struct {
		code, date string
		want       *bool
	}{
		{"NT", "1980-01-01", nil}, {"NT", "2025-01-01", nil},
		{"MI", "1974-06-01", ptrBool(false)}, {"MI", "1980-01-01", nil},
	} {
		got, err := r.IsActiveOn(c.code, c.date)
		if err != nil {
			t.Fatal(err)
		}
		if (got == nil) != (c.want == nil) || (got != nil && *got != *c.want) {
			t.Errorf("IsActiveOn(%s, %s) = %v, want %v", c.code, c.date, fmtBool(got), fmtBool(c.want))
		}
	}
}

func TestAlpha4AndReservationOnWithdrawnEntriesOnly(t *testing.T) {
	r := mustLoad(t)
	raw, err := os.ReadFile("iso3166.json")
	if err != nil {
		t.Fatal(err)
	}
	var data struct {
		Countries struct {
			Withdrawn []struct {
				Alpha2      string  `json:"alpha_2"`
				Alpha4      *string `json:"alpha_4"`
				Reservation *string `json:"reservation"`
			} `json:"withdrawn"`
		} `json:"countries"`
	}
	if err := json.Unmarshal(raw, &data); err != nil {
		t.Fatal(err)
	}
	want := map[string]string{}
	for _, w := range data.Countries.Withdrawn {
		want[w.Alpha2] = fmtStr(w.Alpha4) + "/" + fmtStr(w.Reservation)
	}
	got := map[string]string{}
	for _, c := range r.AllWithdrawn() {
		got[c.Alpha2] = fmtStr(c.Alpha4) + "/" + fmtStr(c.Reservation)
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("withdrawn alpha_4/reservation = %v, want %v", got, want)
	}
	for _, c := range r.AllActive() {
		if c.Alpha4 != nil {
			t.Errorf("active %s has alpha_4 %q", c.Alpha2, *c.Alpha4)
		}
		if c.Reservation != nil {
			t.Errorf("active %s has reservation %q", c.Alpha2, *c.Reservation)
		}
	}
}

func ptrBool(b bool) *bool { return &b }

func fmtBool(b *bool) string {
	if b == nil {
		return "nil"
	}
	if *b {
		return "true"
	}
	return "false"
}

func fmtStr(s *string) string {
	if s == nil {
		return "<nil>"
	}
	return *s
}
