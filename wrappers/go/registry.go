// Package iso3166 loads and queries the ISO 3166 country registry.
//
// Usage:
//
//	reg, err := iso3166.Load()
//	if err != nil {
//	    log.Fatal(err)
//	}
//	if us := reg.Active("US"); us.Exists() {
//	    fmt.Println(us.Alpha3, us.Name)
//	}
//
// The registry file is bundled inside the package (iso3166.json).
// An alternative path can be passed to LoadFrom.
//
// Active, ByAlpha2, ByAlpha3 and ByNumeric return a Country by value; a
// miss returns the zero Country, for which Exists reports false. The
// value owns private copies of its slice and pointer fields, so
// changing it cannot change the registry. The list queries return nil
// (or an empty slice) on a miss. Only Load and LoadFrom return an
// error. This mirrors the Python and JavaScript
// wrappers, whose cross-language contract is checked against the same
// fixture (tests/cross_language_consistency.json).
package iso3166

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

//go:embed iso3166.json
var bundledRegistry []byte

// sentinelNumeric is the placeholder numeric code shared by entries that
// have no assigned numeric code.
const sentinelNumeric = "000"

// Country is one entry from the registry. All pointer fields are nil
// when the registry entry has no value for them.
type Country struct {
	Alpha2             string   `json:"alpha_2"`
	Alpha3             string   `json:"alpha_3"`
	Numeric            string   `json:"numeric"`
	Name               string   `json:"name"`
	Status             string   `json:"status"`
	Independent        bool     `json:"independent"`
	OfficialName       *string  `json:"official_name"`
	Region             *string  `json:"region"`
	Subregion          *string  `json:"subregion"`
	IntermediateRegion *string  `json:"intermediate_region"`
	CurrencyCodes      []string `json:"currency_codes"`
	CallingCodes       []string `json:"calling_codes"`
	TLDs               []string `json:"tlds"`
	Languages          []string `json:"languages"`
	Borders            []string `json:"borders"`
	Note               *string  `json:"note"`
	LastVerified       *string  `json:"last_verified"`
	WithdrawalDate     *string  `json:"withdrawal_date"`
	ReplacedBy         []string `json:"replaced_by"`
}

// Exists reports whether the Country came from a successful lookup. The
// zero Country, returned on a miss, has an empty Alpha2.
func (c Country) Exists() bool { return c.Alpha2 != "" }

// clone returns a copy that shares no slice or pointer with c.
func (c *Country) clone() Country {
	out := *c
	out.OfficialName = cloneStringPtr(c.OfficialName)
	out.Region = cloneStringPtr(c.Region)
	out.Subregion = cloneStringPtr(c.Subregion)
	out.IntermediateRegion = cloneStringPtr(c.IntermediateRegion)
	out.Note = cloneStringPtr(c.Note)
	out.LastVerified = cloneStringPtr(c.LastVerified)
	out.WithdrawalDate = cloneStringPtr(c.WithdrawalDate)
	out.CurrencyCodes = cloneStrings(c.CurrencyCodes)
	out.CallingCodes = cloneStrings(c.CallingCodes)
	out.TLDs = cloneStrings(c.TLDs)
	out.Languages = cloneStrings(c.Languages)
	out.Borders = cloneStrings(c.Borders)
	out.ReplacedBy = cloneStrings(c.ReplacedBy)
	return out
}

func cloneStrings(in []string) []string {
	if in == nil {
		return nil
	}
	out := make([]string, len(in))
	copy(out, in)
	return out
}

func cloneStringPtr(in *string) *string {
	if in == nil {
		return nil
	}
	v := *in
	return &v
}

// IsActive reports whether the entry is one of the three active statuses.
func (c Country) IsActive() bool {
	switch c.Status {
	case "officially-assigned", "user-assigned", "exceptionally-reserved":
		return true
	}
	return false
}

// Meta mirrors the registry's meta block.
type Meta struct {
	Version        string `json:"version"`
	Updated        string `json:"updated"`
	Source         string `json:"source"`
	SchemaVersion  string `json:"schema_version"`
	CountActive    int    `json:"count_active"`
	CountWithdrawn int    `json:"count_withdrawn"`
}

// Summary is returned by CountryRegistry.Summary.
type Summary struct {
	Version   string         `json:"version"`
	Updated   string         `json:"updated"`
	Total     int            `json:"total"`
	Active    int            `json:"active"`
	Withdrawn int            `json:"withdrawn"`
	ByStatus  map[string]int `json:"by_status"`
}

type registryFile struct {
	Meta      Meta `json:"meta"`
	Countries struct {
		Active    []Country `json:"active"`
		Withdrawn []Country `json:"withdrawn"`
	} `json:"countries"`
}

// CountryRegistry is an immutable view of the registry. It is safe for
// concurrent reads.
type CountryRegistry struct {
	meta      Meta
	all       []*Country
	active    []*Country
	withdrawn []*Country

	byAlpha2  map[string]*Country
	byAlpha3  map[string]*Country
	byNumeric map[string]*Country

	path string
}

// Load reads the registry bundled inside the package.
func Load() (*CountryRegistry, error) {
	return LoadFrom("")
}

// LoadFrom reads the registry from path. An empty path uses the
// bundled copy.
func LoadFrom(path string) (*CountryRegistry, error) {
	var data []byte
	var err error

	if path == "" {
		data = bundledRegistry
	} else {
		data, err = os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("registry not found: %s: %w", path, err)
		}
	}

	var file registryFile
	if err := json.Unmarshal(data, &file); err != nil {
		return nil, fmt.Errorf("invalid registry JSON: %w", err)
	}

	r := &CountryRegistry{
		meta: file.Meta,
		path: path,
	}

	r.active = make([]*Country, len(file.Countries.Active))
	for i := range file.Countries.Active {
		r.active[i] = &file.Countries.Active[i]
	}
	r.withdrawn = make([]*Country, len(file.Countries.Withdrawn))
	for i := range file.Countries.Withdrawn {
		r.withdrawn[i] = &file.Countries.Withdrawn[i]
	}

	r.all = make([]*Country, 0, len(r.active)+len(r.withdrawn))
	r.all = append(r.all, r.active...)
	r.all = append(r.all, r.withdrawn...)

	r.byAlpha2 = make(map[string]*Country, len(r.active))
	for _, c := range r.active {
		r.byAlpha2[c.Alpha2] = c
	}
	r.byAlpha3 = make(map[string]*Country, len(r.active))
	for _, c := range r.active {
		r.byAlpha3[c.Alpha3] = c
	}
	r.byNumeric = make(map[string]*Country, len(r.active))
	for _, c := range r.active {
		// "000" is a placeholder shared by several entries (XK, EU, UK,
		// ...); it is never a valid key.
		if c.Numeric != sentinelNumeric {
			r.byNumeric[c.Numeric] = c
		}
	}

	return r, nil
}

// Meta returns a copy of the registry's meta block.
func (r *CountryRegistry) Meta() Meta { return r.meta }

// Version returns meta.version.
func (r *CountryRegistry) Version() string { return r.meta.Version }

// Updated returns meta.updated.
func (r *CountryRegistry) Updated() string { return r.meta.Updated }

// Path returns the path LoadFrom was given, or "" for the bundled copy.
func (r *CountryRegistry) Path() string { return r.path }

// All returns every entry (active and withdrawn).
func (r *CountryRegistry) All() []*Country {
	out := make([]*Country, len(r.all))
	copy(out, r.all)
	return out
}

// AllActive returns the active entries.
func (r *CountryRegistry) AllActive() []*Country {
	out := make([]*Country, len(r.active))
	copy(out, r.active)
	return out
}

// AllWithdrawn returns the withdrawn entries.
func (r *CountryRegistry) AllWithdrawn() []*Country {
	out := make([]*Country, len(r.withdrawn))
	copy(out, r.withdrawn)
	return out
}

// Active looks up an alpha-2 code. Case-insensitive. A miss returns the
// zero Country (Exists reports false). Only active entries; withdrawn
// codes are reachable via WithAlpha2.
func (r *CountryRegistry) Active(alpha2 string) Country {
	if alpha2 == "" {
		return Country{}
	}
	c, ok := r.byAlpha2[strings.ToUpper(alpha2)]
	if !ok {
		return Country{}
	}
	return c.clone()
}

// WithAlpha2 returns all entries (active and withdrawn) with this
// alpha-2 code. A small number of codes appear twice because ISO
// reassigned them (AI, SK); the active entry comes first.
func (r *CountryRegistry) WithAlpha2(alpha2 string) []*Country {
	if alpha2 == "" {
		return nil
	}
	upper := strings.ToUpper(alpha2)
	var out []*Country
	for _, c := range r.all {
		if c.Alpha2 == upper {
			out = append(out, c)
		}
	}
	return out
}

// WithAlpha3 returns all entries (active and withdrawn) with this
// alpha-3 code. Case-insensitive.
func (r *CountryRegistry) WithAlpha3(alpha3 string) []*Country {
	if alpha3 == "" {
		return nil
	}
	upper := strings.ToUpper(alpha3)
	var out []*Country
	for _, c := range r.all {
		if c.Alpha3 == upper {
			out = append(out, c)
		}
	}
	return out
}

// WithNumeric returns all entries (active and withdrawn) with this
// numeric code. The argument is zero-padded like ByNumeric; the
// sentinel "000" matches nothing.
func (r *CountryRegistry) WithNumeric(numeric string) []*Country {
	padded, ok := padNumeric(numeric)
	if !ok {
		return nil
	}
	var out []*Country
	for _, c := range r.all {
		if c.Numeric == padded {
			out = append(out, c)
		}
	}
	return out
}

// ByAlpha2 is an alias for Active.
func (r *CountryRegistry) ByAlpha2(alpha2 string) Country {
	return r.Active(alpha2)
}

// ByAlpha3 looks up an alpha-3 code. Case-insensitive. A miss returns
// the zero Country. Only active entries.
func (r *CountryRegistry) ByAlpha3(alpha3 string) Country {
	if alpha3 == "" {
		return Country{}
	}
	c, ok := r.byAlpha3[strings.ToUpper(alpha3)]
	if !ok {
		return Country{}
	}
	return c.clone()
}

// ByNumeric looks up a numeric code. The argument is zero-padded to
// three digits, so "20" and "020" are equivalent. "", "0" and "000"
// return the zero Country, and whitespace is not trimmed. Only active
// entries.
func (r *CountryRegistry) ByNumeric(numeric string) Country {
	padded, ok := padNumeric(numeric)
	if !ok {
		return Country{}
	}
	c, ok := r.byNumeric[padded]
	if !ok {
		return Country{}
	}
	return c.clone()
}

// padNumeric left-pads a numeric code to three digits. It reports false
// for "" and for the sentinel "000" (so "0" is rejected too).
func padNumeric(numeric string) (string, bool) {
	if numeric == "" {
		return "", false
	}
	padded := numeric
	for len(padded) < 3 {
		padded = "0" + padded
	}
	if padded == sentinelNumeric {
		return "", false
	}
	return padded, true
}

// Currencies returns the currency codes in circulation in a country.
// Returns nil if the country is unknown or has none.
func (r *CountryRegistry) Currencies(alpha2 string) []string {
	c, ok := r.byAlpha2[strings.ToUpper(alpha2)]
	if alpha2 == "" || !ok || c.CurrencyCodes == nil {
		return nil
	}
	out := make([]string, len(c.CurrencyCodes))
	copy(out, c.CurrencyCodes)
	return out
}

// CountriesWith returns the active countries where a currency
// circulates.
func (r *CountryRegistry) CountriesWith(currencyCode string) []*Country {
	if currencyCode == "" {
		return nil
	}
	target := strings.ToUpper(currencyCode)
	var out []*Country
	for _, c := range r.active {
		for _, cc := range c.CurrencyCodes {
			if cc == target {
				out = append(out, c)
				break
			}
		}
	}
	return out
}

// Region returns the active countries in a macro-region.
// Case-insensitive.
func (r *CountryRegistry) Region(name string) []*Country {
	if name == "" {
		return nil
	}
	target := strings.ToLower(name)
	var out []*Country
	for _, c := range r.active {
		if c.Region != nil && strings.ToLower(*c.Region) == target {
			out = append(out, c)
		}
	}
	return out
}

// Subregion returns the active countries in a sub-region.
// Case-insensitive.
func (r *CountryRegistry) Subregion(name string) []*Country {
	if name == "" {
		return nil
	}
	target := strings.ToLower(name)
	var out []*Country
	for _, c := range r.active {
		if c.Subregion != nil && strings.ToLower(*c.Subregion) == target {
			out = append(out, c)
		}
	}
	return out
}

// Search does a case-insensitive substring search on name,
// official_name, alpha_2, and alpha_3.
func (r *CountryRegistry) Search(query string) []*Country {
	if query == "" {
		return nil
	}
	q := strings.ToLower(query)
	var out []*Country
	for _, c := range r.all {
		haystack := c.Name
		if c.OfficialName != nil {
			haystack += " " + *c.OfficialName
		}
		haystack += " " + c.Alpha2 + " " + c.Alpha3
		if strings.Contains(strings.ToLower(haystack), q) {
			out = append(out, c)
		}
	}
	return out
}

// Summary returns counts per status and the total entry counts.
func (r *CountryRegistry) Summary() Summary {
	byStatus := make(map[string]int)
	for _, c := range r.all {
		byStatus[c.Status]++
	}
	return Summary{
		Version:   r.meta.Version,
		Updated:   r.meta.Updated,
		Total:     len(r.all),
		Active:    len(r.active),
		Withdrawn: len(r.withdrawn),
		ByStatus:  byStatus,
	}
}
