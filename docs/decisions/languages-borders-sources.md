# Languages and borders: source selection

Status: proposed
Date: <today>
Supersedes: none

## Context

The `languages` and `borders` fields cannot be sourced from ISO, the
UN Statistics Division, IANA, or the ITU. Those bodies define codes
and classifications; they do not publish which languages are official
in a country, nor which countries share a land border.

The registry's sourcing rule since v1.0.0 is that every field traces
to a first-party source. First-party has meant ISO and the standard
bodies in the ecosystem. This ADR addresses the case where no such
body exists for a field.

## Decision

`languages` and `borders` are populated from the CIA World Factbook,
one lookup per entry, with the source URL recorded in the entry's
`note` field. The World Factbook is a US federal government
publication, updated continuously, and freely available.

The registry's source rule is restated as: **first-party means a
government standards body or a government statistical service.**
The list of accepted sources expands to:

- ISO (country codes, currency codes, language codes)
- UN Statistics Division (region classification)
- ITU (calling codes)
- IANA (ccTLDs)
- CIA World Factbook (languages, borders)
- UNESCO Institute for Statistics (languages, backup)
- National statistics offices (languages, backup)

Third-party aggregators remain excluded: Wikipedia, Ethnologue,
Glottolog, countrycode.org, blog posts, and CSVs from unrelated
projects.

## Alternatives considered

**Defer both fields indefinitely.** Rejected: `languages` and
`borders` are the last two fields a consumer of the registry needs
to build a complete country fact table. Deferring them leaves the
registry incomplete.

**Manual curation from constitutional texts and border treaties.**
Rejected: primary sources, but ~500 individual citations and weeks
of work for fields most consumers do not need. The government
publication is a reasonable proxy and is itself traceable to
primary sources.

**Natural Earth.** Rejected: public-domain geospatial data, but the
`borders` field is a list of ISO 3166 alpha-2 codes, not a geometry.
Extracting adjacency from a shapefile adds a dependency and a
transformation step; the World Factbook publishes the adjacency
list directly.

## Consequences

- `docs/ENRICHMENT.md` gains sections for `languages` and `borders`
  that name the World Factbook as the source.
- The CONTRIBUTING first-party source list is updated to include the
  expanded set.
- A future v1.4.0 may add a fallback to a national statistics office
  when the World Factbook is silent on an entry.