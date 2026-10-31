package iso3166

import (
	"encoding/json"
	"fmt"
)

// ============================================================
// Club memberships (v1.12.0; docs/QUERIES.md, "Query 10")
//
// Four clubs, each a list of inclusive {from, to} ranges on every active
// entry of iso3166.json (`to` null = still a member; [] = never):
// eu_membership, eea_membership, eurozone_membership, customs_union.
//
// Every *At query follows one rule set:
//   - a malformed date, an unknown code, or a code in no range -> false
//   - from <= date <= to for some range (`to` null = no upper bound) -> true
//   - before the first range or after the last `to` -> false
//
// The *At queries return a plain bool, never "unknown": an empty array is a
// statement, not a silence. IsEU, IsEEA and IsEurozone remain as
// current-status aliases: true when the code has a range whose `to` is null.
//
// The ranges are read in a second, narrow decode so that Country (and the
// lookup command's output) is unchanged.
// ============================================================

// clubRange is one inclusive range. `to` is "" while the entry is a member.
type clubRange struct {
	from string
	to   string
	open bool
}

type clubSet struct {
	eu, eea, eurozone, customs []clubRange
}

type rawRange struct {
	From string  `json:"from"`
	To   *string `json:"to"`
}

func toRanges(in []rawRange) []clubRange {
	out := make([]clubRange, len(in))
	for i, r := range in {
		out[i] = clubRange{from: r.From, open: r.To == nil}
		if r.To != nil {
			out[i].to = *r.To
		}
	}
	return out
}

// loadClubs reads the four arrays of every active entry.
func loadClubs(data []byte) (map[string]clubSet, error) {
	var file struct {
		Countries struct {
			Active []struct {
				Alpha2   string     `json:"alpha_2"`
				EU       []rawRange `json:"eu_membership"`
				EEA      []rawRange `json:"eea_membership"`
				Eurozone []rawRange `json:"eurozone_membership"`
				Customs  []rawRange `json:"customs_union"`
			} `json:"active"`
		} `json:"countries"`
	}
	if err := json.Unmarshal(data, &file); err != nil {
		return nil, fmt.Errorf("invalid club memberships: %w", err)
	}
	out := make(map[string]clubSet, len(file.Countries.Active))
	for _, e := range file.Countries.Active {
		out[e.Alpha2] = clubSet{
			eu:       toRanges(e.EU),
			eea:      toRanges(e.EEA),
			eurozone: toRanges(e.Eurozone),
			customs:  toRanges(e.Customs),
		}
	}
	return out, nil
}

func clubAt(ranges []clubRange, date string) bool {
	if !dqValidDate(date) {
		return false
	}
	for _, r := range ranges {
		if r.from <= date && (r.open || date <= r.to) {
			return true
		}
	}
	return false
}

func clubNow(ranges []clubRange) bool {
	for _, r := range ranges {
		if r.open {
			return true
		}
	}
	return false
}

// IsEUMemberAt reports whether code was an EU member state on date
// (YYYY-MM-DD). Founders count from 1958-01-01 (the EEC). Both ends of a
// range are inclusive, so GB is a member on 2020-01-31 and not on
// 2020-02-01. See docs/QUERIES.md, "Query 10".
//
//	IsEUMemberAt("GB", "2010-01-01") // true
//	IsEUMemberAt("GB", "2023-01-01") // false
func (r *CountryRegistry) IsEUMemberAt(code, date string) bool {
	return clubAt(r.clubs[dqNorm(code)].eu, date)
}

// IsEEAMemberAt reports whether code was a party to the EEA Agreement on
// date, formally or provisionally: it is true from the first day the EEA
// Enlargement Agreement applied provisionally (2004-05-01 for the 2004
// ten, 2007-08-01 for BG and RO). HR has formal dates only. See
// docs/QUERIES.md, "Query 10".
func (r *CountryRegistry) IsEEAMemberAt(code, date string) bool {
	return clubAt(r.clubs[dqNorm(code)].eea, date)
}

// IsEurozoneMemberAt reports whether code was in the eurozone on date.
// Members count from 1 January of their adoption year. See
// docs/QUERIES.md, "Query 10".
//
//	IsEurozoneMemberAt("GR", "2000-01-01") // false
//	IsEurozoneMemberAt("GR", "2002-01-01") // true
func (r *CountryRegistry) IsEurozoneMemberAt(code, date string) bool {
	return clubAt(r.clubs[dqNorm(code)].eurozone, date)
}

// IsInCustomsUnionAt reports whether code was in the EU customs union on
// date. AD and TR cover industrial goods only (scope is in the snapshot
// meta). See docs/QUERIES.md, "Query 10".
func (r *CountryRegistry) IsInCustomsUnionAt(code, date string) bool {
	return clubAt(r.clubs[dqNorm(code)].customs, date)
}
