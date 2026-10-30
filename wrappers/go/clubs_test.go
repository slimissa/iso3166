package iso3166

import "testing"

func TestClubMembershipsAreDateScoped(t *testing.T) {
	r := mustLoad(t)
	cases := []struct {
		name string
		got  bool
		want bool
	}{
		{"EU GB 2010", r.IsEUMemberAt("GB", "2010-01-01"), true},
		{"EU GB 2023", r.IsEUMemberAt("GB", "2023-01-01"), false},
		{"EU GB 2020-01-31", r.IsEUMemberAt("GB", "2020-01-31"), true},
		{"EU GB 2020-02-01", r.IsEUMemberAt("GB", "2020-02-01"), false},
		{"EU GR 1980", r.IsEUMemberAt("GR", "1980-01-01"), false},
		{"EU GR 2000", r.IsEUMemberAt("GR", "2000-01-01"), true},
		{"EZ GR 2000", r.IsEurozoneMemberAt("GR", "2000-01-01"), false},
		{"EZ GR 2000-12-31", r.IsEurozoneMemberAt("GR", "2000-12-31"), false},
		{"EZ GR 2001-01-01", r.IsEurozoneMemberAt("GR", "2001-01-01"), true},
		{"EZ GR 2002", r.IsEurozoneMemberAt("GR", "2002-01-01"), true},
		{"EU DE 1950", r.IsEUMemberAt("DE", "1950-01-01"), false},
		{"CU GB 2010", r.IsInCustomsUnionAt("GB", "2010-01-01"), true},
		{"CU GB 2023", r.IsInCustomsUnionAt("GB", "2023-01-01"), false},
		{"EEA GB 2020-12-31", r.IsEEAMemberAt("GB", "2020-12-31"), true},
		{"EEA GB 2021-01-01", r.IsEEAMemberAt("GB", "2021-01-01"), false},
		{"bad month", r.IsEUMemberAt("DE", "2000-13-01"), false},
		{"not padded", r.IsEUMemberAt("DE", "2000-1-1"), false},
		{"empty date", r.IsEUMemberAt("DE", ""), false},
		{"unknown code", r.IsEUMemberAt("ZZ", "2000-01-01"), false},
		{"empty code", r.IsEUMemberAt("", "2000-01-01"), false},
		{"spaced lowercase", r.IsEUMemberAt(" gb ", "2010-01-01"), true},
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
