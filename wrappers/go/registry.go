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
	"sort"
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
	Introduced         *string  `json:"introduced"`
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
	out.Introduced = cloneStringPtr(c.Introduced)
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

// ============================================================
// Derived queries (v1.10.0 — design in docs/QUERIES.md)
//
// docs/QUERIES.md is the contract; each method names its section.
//
// Mirrors wrappers/python/iso3166/derived.py. Unknown codes are not
// errors: bool queries return false, list queries return an empty
// non-nil slice, optional queries return ok == false. Active entries
// win over withdrawn ones (AI and SK exist twice); the succession
// graph is built from withdrawn entries only.
//
// Approximate: IsEU, IsEEA, IsEurozone (deprecated by v1.12.0's
// is_eu_member_at) and CurrencyAt (deprecated by v1.11.1's
// introduced field).
// ============================================================

// knownEUMembers is the 27 EU member states at v1.9.3. It is the only
// hardcoded list in the registry; it is not a tree fact, which is why
// IsEU is deprecated in v1.12.0.
var knownEUMembers = map[string]bool{
	"AT": true, "BE": true, "BG": true, "HR": true, "CY": true, "CZ": true,
	"DK": true, "EE": true, "FI": true, "FR": true, "DE": true, "GR": true,
	"HU": true, "IE": true, "IT": true, "LV": true, "LT": true, "LU": true,
	"MT": true, "NL": true, "PL": true, "PT": true, "RO": true, "SK": true,
	"SI": true, "ES": true, "SE": true,
}

// eeaNonEU lists the EEA members that are not EU members.
var eeaNonEU = map[string]bool{"IS": true, "LI": true, "NO": true}

func dqNorm(code string) string { return strings.ToUpper(strings.TrimSpace(code)) }

func dqSorted(set map[string]bool) []string {
	out := make([]string, 0, len(set))
	for k := range set {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// dqEntry returns the active entry for code, else the withdrawn one.
func (r *CountryRegistry) dqEntry(code string) *Country {
	c := dqNorm(code)
	if c == "" {
		return nil
	}
	if e, ok := r.byAlpha2[c]; ok {
		return e
	}
	for _, w := range r.withdrawn {
		if w.Alpha2 == c {
			return w
		}
	}
	return nil
}

// dqEdges maps each withdrawn code to its replaced_by codes.
func (r *CountryRegistry) dqEdges() map[string][]string {
	edges := make(map[string][]string)
	for _, w := range r.withdrawn {
		if len(w.ReplacedBy) > 0 {
			edges[w.Alpha2] = w.ReplacedBy
		}
	}
	return edges
}

func dqClosure(start string, edges map[string][]string) []string {
	seen := make(map[string]bool)
	stack := []string{start}
	for len(stack) > 0 {
		cur := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		for _, n := range edges[cur] {
			if n != start && !seen[n] {
				seen[n] = true
				stack = append(stack, n)
			}
		}
	}
	return dqSorted(seen)
}

// IsEU reports whether code is one of the 27 EU member states. It is
// approximate: the list is a v1.9.3 snapshot. Deprecated by
// is_eu_member_at in v1.12.0. See docs/QUERIES.md, "Query 1".
func (r *CountryRegistry) IsEU(code string) bool { return knownEUMembers[dqNorm(code)] }

// IsEEA reports whether code is an EU member or IS, LI or NO.
// Approximate; deprecated together with IsEU. See docs/QUERIES.md,
// "Query 1".
func (r *CountryRegistry) IsEEA(code string) bool {
	c := dqNorm(code)
	return knownEUMembers[c] || eeaNonEU[c]
}

// IsEurozone reports whether code is an EU member whose active entry
// has currency_codes == ["EUR"]. Approximate: overseas territories
// that use the euro (GF, GP, MQ, RE, YT, AX, ...) are separate codes
// and return false. See docs/QUERIES.md, "Query 1".
func (r *CountryRegistry) IsEurozone(code string) bool {
	c := dqNorm(code)
	if !knownEUMembers[c] {
		return false
	}
	e, ok := r.byAlpha2[c]
	return ok && len(e.CurrencyCodes) == 1 && e.CurrencyCodes[0] == "EUR"
}

// RegionTree returns [region, subregion, intermediate_region] with
// null entries removed. An unknown code returns an empty slice. See
// docs/QUERIES.md, "Query 2".
func (r *CountryRegistry) RegionTree(code string) []string {
	out := []string{}
	e := r.dqEntry(code)
	if e == nil {
		return out
	}
	for _, v := range []*string{e.Region, e.Subregion, e.IntermediateRegion} {
		if v != nil && *v != "" {
			out = append(out, *v)
		}
	}
	return out
}

// BordersTransitively returns the sorted codes within maxHops of code
// through borders, excluding code itself. See docs/QUERIES.md, "Query 3".
func (r *CountryRegistry) BordersTransitively(code string, maxHops int) []string {
	start := dqNorm(code)
	if start == "" || maxHops < 1 || r.dqEntry(start) == nil {
		return []string{}
	}
	seen := map[string]bool{start: true}
	frontier := []string{start}
	for i := 0; i < maxHops; i++ {
		var next []string
		for _, cur := range frontier {
			if e, ok := r.byAlpha2[cur]; ok {
				for _, b := range e.Borders {
					if !seen[b] {
						seen[b] = true
						next = append(next, b)
					}
				}
			}
		}
		if len(next) == 0 {
			break
		}
		frontier = next
	}
	delete(seen, start)
	return dqSorted(seen)
}

// SuccessionPath returns the shortest replaced_by path from fromCode
// to toCode, both endpoints included. ok is false if there is no path
// or either code is unknown. See docs/QUERIES.md, "Query 4".
func (r *CountryRegistry) SuccessionPath(fromCode, toCode string) ([]string, bool) {
	a, b := dqNorm(fromCode), dqNorm(toCode)
	if r.dqEntry(a) == nil || r.dqEntry(b) == nil {
		return nil, false
	}
	if a == b {
		return []string{a}, true
	}
	edges := r.dqEdges()
	prev := map[string]string{a: ""}
	queue := []string{a}
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		for _, n := range edges[cur] {
			if _, seen := prev[n]; seen {
				continue
			}
			prev[n] = cur
			if n == b {
				path := []string{b}
				for prev[path[len(path)-1]] != "" {
					path = append(path, prev[path[len(path)-1]])
				}
				for i, j := 0, len(path)-1; i < j; i, j = i+1, j-1 {
					path[i], path[j] = path[j], path[i]
				}
				return path, true
			}
			queue = append(queue, n)
		}
	}
	return nil, false
}

// Successors returns all descendants: the transitive closure of
// replaced_by, intermediate codes included, excluding code, sorted. The
// CLI returns the same set. See docs/QUERIES.md, "Query 5".
func (r *CountryRegistry) Successors(code string) []string {
	c := dqNorm(code)
	if c == "" {
		return []string{}
	}
	return dqClosure(c, r.dqEdges())
}

// Predecessors returns all ancestors: every withdrawn code from which
// code is reachable through replaced_by, sorted. See docs/QUERIES.md,
// "Query 5".
func (r *CountryRegistry) Predecessors(code string) []string {
	c := dqNorm(code)
	if c == "" {
		return []string{}
	}
	rev := make(map[string][]string)
	for src, dsts := range r.dqEdges() {
		for _, d := range dsts {
			rev[d] = append(rev[d], src)
		}
	}
	return dqClosure(c, rev)
}

// CallingCodeFor returns the sorted codes whose calling_codes is a
// prefix of the number's digits. Country level only: "+44" returns GB,
// GG, IM and JE, and "+1" returns every NANP entry. See
// docs/QUERIES.md, "Query 6".
func (r *CountryRegistry) CallingCodeFor(number string) []string {
	var digits strings.Builder
	for _, ch := range number {
		switch ch {
		case ' ', '-', '(', ')', '.', '+':
		default:
			if ch < '0' || ch > '9' {
				return []string{}
			}
			digits.WriteRune(ch)
		}
	}
	d := digits.String()
	if d == "" {
		return []string{}
	}
	out := make(map[string]bool)
	for _, e := range r.active {
		for _, cc := range e.CallingCodes {
			if strings.HasPrefix(d, cc) {
				out[e.Alpha2] = true
			}
		}
	}
	return dqSorted(out)
}

// dqValidDate reports whether s is a real YYYY-MM-DD date, year >= 1.
func dqValidDate(s string) bool {
	if len(s) != 10 || s[4] != '-' || s[7] != '-' {
		return false
	}
	num := func(a, b int) int {
		n := 0
		for i := a; i < b; i++ {
			if s[i] < '0' || s[i] > '9' {
				return -1
			}
			n = n*10 + int(s[i]-'0')
		}
		return n
	}
	y, m, d := num(0, 4), num(5, 7), num(8, 10)
	if y < 1 || m < 1 || m > 12 || d < 1 {
		return false
	}
	feb := 28
	if (y%4 == 0 && y%100 != 0) || y%400 == 0 {
		feb = 29
	}
	dim := []int{31, feb, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}[m-1]
	return d <= dim
}

// IsActiveOn reports whether code was an assigned ISO 3166-1 code on
// date (YYYY-MM-DD). The result is tri-state: a pointer to false for a
// malformed date, an unknown code, a date before Introduced, or a date
// after a withdrawn entry's withdrawal_date; a pointer to true when the
// code was in force; nil (unknown) for an active entry whose Introduced
// is nil. Active entries are resolved first (AI and SK exist twice). A
// withdrawn entry has no sourced start date, so it is true up to and
// including withdrawal_date; a date before 1974 is also true for such a
// code and should not be relied on. See docs/QUERIES.md, "Query 9".
//
//	IsActiveOn("DE", "1990-01-01") // true
//	IsActiveOn("DE", "1970-01-01") // false
//	IsActiveOn("BJ", "2000-01-01") // nil
func (r *CountryRegistry) IsActiveOn(code, date string) *bool {
	yes, no := true, false
	if !dqValidDate(date) {
		return &no
	}
	c := dqNorm(code)
	if e, ok := r.byAlpha2[c]; ok {
		if e.Introduced == nil {
			return nil
		}
		if date >= *e.Introduced {
			return &yes
		}
		return &no
	}
	var wd *Country
	for _, w := range r.withdrawn {
		if w.Alpha2 == c {
			wd = w
			break
		}
	}
	if wd == nil || wd.WithdrawalDate == nil || date > *wd.WithdrawalDate {
		return &no
	}
	if wd.Introduced != nil && date < *wd.Introduced {
		return &no
	}
	return &yes
}

// CurrencyAt returns the approximate currency in force on date
// (YYYY-MM-DD). Active codes return their current currency_codes for
// every date. Withdrawn codes return ok == false before
// withdrawal_date and the terminal successors' current currencies from
// then on. ok == false means "cannot answer" (unknown code, malformed
// date, no data). Deprecated by v1.11.1 (approximate in v1.11.0). See
// docs/QUERIES.md, "Query 7".
func (r *CountryRegistry) CurrencyAt(code, date string) ([]string, bool) {
	if !dqValidDate(date) {
		return nil, false
	}
	c := dqNorm(code)
	if e, ok := r.byAlpha2[c]; ok {
		if e.CurrencyCodes == nil {
			return nil, false
		}
		return append([]string{}, e.CurrencyCodes...), true
	}
	var wd *Country
	for _, w := range r.withdrawn {
		if w.Alpha2 == c {
			wd = w
			break
		}
	}
	if wd == nil || wd.WithdrawalDate == nil || date < *wd.WithdrawalDate {
		return nil, false
	}
	edges := r.dqEdges()
	out := make(map[string]bool)
	seen := make(map[string]bool)
	stack := []string{c}
	for len(stack) > 0 {
		cur := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if seen[cur] {
			continue
		}
		seen[cur] = true
		if e, ok := r.byAlpha2[cur]; ok {
			for _, cc := range e.CurrencyCodes {
				out[cc] = true
			}
		} else {
			stack = append(stack, edges[cur]...)
		}
	}
	if len(out) == 0 {
		return nil, false
	}
	return dqSorted(out), true
}

// RegionCountries returns the sorted codes of active entries in region
// and, if subregion is not empty, in subregion. Case-insensitive. See
// docs/QUERIES.md, "Query 8".
func (r *CountryRegistry) RegionCountries(region, subregion string) []string {
	if region == "" {
		return []string{}
	}
	rl, sl := strings.ToLower(region), strings.ToLower(subregion)
	out := []string{}
	for _, e := range r.active {
		if e.Region == nil || strings.ToLower(*e.Region) != rl {
			continue
		}
		if sl != "" && (e.Subregion == nil || strings.ToLower(*e.Subregion) != sl) {
			continue
		}
		out = append(out, e.Alpha2)
	}
	sort.Strings(out)
	return out
}
