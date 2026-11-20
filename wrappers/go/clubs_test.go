package iso3166

import (
	"errors"
	"reflect"
	"testing"
)

// ok unwraps a (bool, error) result; a club query on these valid dates
// must not fail.
func ok(b bool, err error) bool {
	if err != nil {
		panic(err)
	}
	return b
}

// v1.12.5: a malformed date is an error, not an answer of false.
func TestMalformedDatesReturnError(t *testing.T) {
	r := mustLoad(t)
	bad := []string{"2010-13-45", "2010-02-30", "2010-1-1", "20100101",
		"2010/01/01", "", "2010-01-01T00:00:00", "2010-01-01\n"}
	for _, d := range bad {
		calls := map[string]func() error{
			"IsEUMemberAt":       func() error { _, e := r.IsEUMemberAt("DE", d); return e },
			"IsEEAMemberAt":      func() error { _, e := r.IsEEAMemberAt("DE", d); return e },
			"IsEurozoneMemberAt": func() error { _, e := r.IsEurozoneMemberAt("DE", d); return e },
			"IsInCustomsUnionAt": func() error { _, e := r.IsInCustomsUnionAt("DE", d); return e },
			"IsActiveOn":         func() error { _, e := r.IsActiveOn("DE", d); return e },
		}
		for name, f := range calls {
			var ide *InvalidDateError
			if err := f(); !errors.As(err, &ide) {
				t.Errorf("%s(DE, %q): want *InvalidDateError, got %v", name, d, err)
			}
		}
	}
}

func TestClubMembershipsAreDateScoped(t *testing.T) {
	r := mustLoad(t)
	cases := []struct {
		name string
		got  bool
		want bool
	}{
		{"EU GB 2010", ok(r.IsEUMemberAt("GB", "2010-01-01")), true},
		{"EU GB 2023", ok(r.IsEUMemberAt("GB", "2023-01-01")), false},
		{"EU GB 2020-01-31", ok(r.IsEUMemberAt("GB", "2020-01-31")), true},
		{"EU GB 2020-02-01", ok(r.IsEUMemberAt("GB", "2020-02-01")), false},
		{"EU GR 1980", ok(r.IsEUMemberAt("GR", "1980-01-01")), false},
		{"EU GR 2000", ok(r.IsEUMemberAt("GR", "2000-01-01")), true},
		{"EZ GR 2000", ok(r.IsEurozoneMemberAt("GR", "2000-01-01")), false},
		{"EZ GR 2000-12-31", ok(r.IsEurozoneMemberAt("GR", "2000-12-31")), false},
		{"EZ GR 2001-01-01", ok(r.IsEurozoneMemberAt("GR", "2001-01-01")), true},
		{"EZ GR 2002", ok(r.IsEurozoneMemberAt("GR", "2002-01-01")), true},
		{"EU DE 1950", ok(r.IsEUMemberAt("DE", "1950-01-01")), false},
		{"CU GB 2010", ok(r.IsInCustomsUnionAt("GB", "2010-01-01")), true},
		{"CU GB 2023", ok(r.IsInCustomsUnionAt("GB", "2023-01-01")), false},
		{"EEA GB 2020-12-31", ok(r.IsEEAMemberAt("GB", "2020-12-31")), true},
		{"EEA GB 2021-01-01", ok(r.IsEEAMemberAt("GB", "2021-01-01")), false},
		{"unknown code", ok(r.IsEUMemberAt("ZZ", "2000-01-01")), false},
		{"empty code", ok(r.IsEUMemberAt("", "2000-01-01")), false},
		{"spaced lowercase", ok(r.IsEUMemberAt(" gb ", "2010-01-01")), true},
	}
	for _, c := range cases {
		if c.got != c.want {
			t.Errorf("%s = %v, want %v", c.name, c.got, c.want)
		}
	}
}

func TestAliasesMatchV1111ForEveryCode(t *testing.T) {
	r := mustLoad(t)
	codes := []string{"ZZ", ""}
	for _, c := range r.AllActive() {
		codes = append(codes, c.Alpha2)
	}
	var eu, eea, ez int
	for _, c := range codes {
		wantEU := knownEUMembers[c]
		wantEEA := wantEU || eeaNonEU[c]
		e, ok := r.byAlpha2[c]
		wantEZ := wantEU && ok && len(e.CurrencyCodes) == 1 && e.CurrencyCodes[0] == "EUR"
		if r.IsEU(c) != wantEU || r.IsEEA(c) != wantEEA || r.IsEurozone(c) != wantEZ {
			t.Errorf("alias mismatch for %q", c)
		}
		if r.IsEU(c) {
			eu++
		}
		if r.IsEEA(c) {
			eea++
		}
		if r.IsEurozone(c) {
			ez++
		}
	}
	if eu != 27 || eea != 30 || ez != 21 {
		t.Errorf("current members = %d/%d/%d, want 27/30/21", eu, eea, ez)
	}
}

func TestEEAProvisionalApplicationCounts(t *testing.T) {
	r := mustLoad(t)
	cases := []struct {
		code, date string
		want       bool
	}{
		{"BG", "2010-01-01", true},
		{"BG", "2005-01-01", false},
		{"BG", "2007-07-31", false},
		{"BG", "2007-08-01", true},
		{"CY", "2005-01-01", true},
		{"CY", "2003-01-01", false},
		{"HR", "2020-01-01", false},
	}
	for _, c := range cases {
		if got := ok(r.IsEEAMemberAt(c.code, c.date)); got != c.want {
			t.Errorf("IsEEAMemberAt(%s, %s) = %v, want %v", c.code, c.date, got, c.want)
		}
	}
}

// TestLoadClubsParsesAllFour: loadClubs reads the four arrays of every active
// entry into their own fields. The synthetic registry gives each array a
// different range, so a swapped or dropped field cannot pass.
func TestLoadClubsParsesAllFour(t *testing.T) {
	data := []byte(`{"countries": {"active": [
		{"alpha_2": "AA",
		 "eu_membership":       [{"from": "1958-01-01", "to": "1999-12-31"}],
		 "eea_membership":      [{"from": "1994-01-01", "to": null}],
		 "eurozone_membership": [{"from": "2002-01-01", "to": "2010-06-30"}, {"from": "2012-01-01", "to": null}],
		 "customs_union":       [{"from": "1968-07-01", "to": "1990-01-01"}]},
		{"alpha_2": "BB"}
	]}}`)
	got, err := loadClubs(data)
	if err != nil {
		t.Fatalf("loadClubs: %v", err)
	}
	aa := got["AA"]
	want := map[string][]clubRange{
		"eu":       {{from: "1958-01-01", to: "1999-12-31"}},
		"eea":      {{from: "1994-01-01", open: true}},
		"eurozone": {{from: "2002-01-01", to: "2010-06-30"}, {from: "2012-01-01", open: true}},
		"customs":  {{from: "1968-07-01", to: "1990-01-01"}},
	}
	for name, have := range map[string][]clubRange{
		"eu": aa.eu, "eea": aa.eea, "eurozone": aa.eurozone, "customs": aa.customs,
	} {
		if !reflect.DeepEqual(have, want[name]) {
			t.Errorf("AA.%s = %+v, want %+v", name, have, want[name])
		}
	}
	bb, present := got["BB"]
	if !present || len(bb.eu)+len(bb.eea)+len(bb.eurozone)+len(bb.customs) != 0 {
		t.Errorf("BB (no club fields) = %+v, present=%v; want an entry with four empty lists", bb, present)
	}

	// The bundled registry: DE is in all four.
	all, err := loadClubs(bundledRegistry)
	if err != nil {
		t.Fatalf("loadClubs(bundled): %v", err)
	}
	de := all["DE"]
	if len(de.eu) == 0 || len(de.eea) == 0 || len(de.eurozone) == 0 || len(de.customs) == 0 {
		t.Errorf("DE: eu=%d eea=%d eurozone=%d customs=%d, want all four non-empty",
			len(de.eu), len(de.eea), len(de.eurozone), len(de.customs))
	}
}
