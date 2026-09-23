# Enrichment

How the four enriched fields in `iso3166.json` are populated, from what
sources, and where the naive rule breaks down.

The fields are populated by three tools:

| Field | Tool | Snapshot |
|-------|------|----------|
| `official_name` | `tools/enrich_official_name.py` | none (per-entry ISO OBP lookup) |
| `currency_codes` | `tools/enrich_field.py --field currency_codes` | `tools/iso4217_snapshot.json` |
| `calling_codes` | `tools/enrich_field.py --field calling_codes` | `tools/itu_calling_code_snapshot.json` |
| `tlds` | `tools/enrich_field.py --field tlds` | `tools/iana_tld_snapshot.json` |

Every field has a `--check` mode. All four are blocking in CI as of
v1.2.0 (the `check-fields` job).

---

## `official_name`

**Source.** ISO 3166-1 Online Browsing Platform, one lookup per entry:
https://www.iso.org/obp/ui/#iso:code:3166:<CC>


**Shape.** The country's long-form name exactly as ISO publishes it.
For some entries it equals the short name (`Japan`, `Israel`,
`Iceland`). For others it is longer (`United Kingdom of Great Britain
and Northern Ireland`, `Republic of Albania`). The tool does not
enforce a difference; a short name that matches the official name is
recorded as-is.

**Edge cases.**

| Pattern | Example |
|---------|---------|
| Parenthetical qualifiers | `Bolivia (Plurinational State of)`, `Venezuela (Bolivarian Republic of)`, `Micronesia (Federated States of)` |
| Parenthetical qualifiers | `Taiwan, Province of China` |
| Articles in parentheses | `Cayman Islands (the)`, `Marshall Islands (the)`, `Bahamas (the)`, `Gambia (the)` |
| Historical long-form | `Czech Republic` (short name is now `Czechia`) |
| Two-word conventions | `Viet Nam` (two words), `Holy See` |
| Special administrative regions | `China, Hong Kong Special Administrative Region`, `China, Macao Special Administrative Region` |
| Non-ASCII | `Côte d'Ivoire`, `Åland Islands` |

The tool cannot detect short-name-equals-official-name mistakes; a human
must verify each entry against OBP.

**Refresh.** On every ISO 3166-1 amendment. Manual.

---

## `currency_codes`

**Source.** ISO 3166-1 OBP country pages, cross-checked against ISO 4217
currency pages.

**Shape.** Every currency that is legal tender in the country. A list,
because several countries use more than one.

**Edge cases.**

| Case | Codes | Currency |
|------|-------|----------|
| Eurozone (EU members) | AT BE HR CY EE FI FR DE GR IE IT LV LT LU MT NL PT SK SI ES | EUR |
| Euro, non-EU | AD MC SM VA | EUR |
| Euro, overseas | RE GP MQ GF YT BL MF PM AX TF | EUR |
| USD, primary | US | USD |
| USD, dollarized | EC SV TL PW FM MH | USD |
| USD, dual legal tender | PA | PAB and USD |
| USD, territories | BQ IO GU MP AS PR UM TC VG VI | USD |
| AUD zone | AU KI NR TV | AUD |
| NZD zone | NZ CK NU TK | NZD |
| CHF zone | CH LI | CHF |
| GBP zone | GB GG JE IM | GBP |
| West African CFA | BJ BF CI GW ML NE SN TG | XOF |
| Central African CFA | CM CF TD CG GQ GA | XAF |
| CFP franc | PF NC WF | XPF |
| Rand zone | LS NA SZ | LSL, NAD, SZL — each has its own pegged currency; not ZAR |
| Rupee zone | BT NP | BTN, NPR — each pegged to INR, not INR |
| ILS | IL PS | ILS |
| MAD | EH | MAD |
| No currency | AQ | Antarctica has no currency; field stays null |

**Not in the field.** Historical currencies, pegged anchors, and
settlement-only currencies. The field lists only legal tender.

**Refresh.** On every ISO 4217 amendment. Manual.

---

## `calling_codes`

**Source.** ITU-T E.164 assigned country codes:
https://www.itu.int/oth/T02020000E8/en


**Shape.** Every calling code the ITU assigns to the territory. A list,
because a few countries share a root.

**Edge cases.**

| Root | Territories | Convention |
|------|-------------|------------|
| +1 | US, CA, and 20 Caribbean territories | Root `1` for all NANP members; the territory's alpha-2 distinguishes them |
| +7 | RU, KZ | Shared root `7` |
| +44 | GB, GG, JE, IM | Root `44` for GB; sub-prefixes for Crown dependencies are recorded only if the enrichment adds them |
| +47 | NO, SJ | Shared |
| +61 | AU, CC, CX | Shared |
| +64 | NZ, PN | Shared |
| +212 | MA, EH | Shared |
| +262 | RE, YT | Shared |
| +358 | FI, AX | Shared |
| +590 | GP, BL, MF | Shared |
| +599 | CW, BQ | Shared |

The ITU list is not what the naive reader expects: it lists the
country, not the dial plan. For NANP members, one row per country but
the code column is `1`. The ITU's appendices record sub-prefixes; this
registry does not include them.

**Refresh.** Rare. The ITU list changes on new assignments or
reorganizations. Manual.

---

## `tlds`

**Source.** IANA country-code top-level domain registry:
https://data.iana.org/TLD/tlds-alpha-by-domain.txt


**Shape.** The country-code top-level domain in dot-prefixed lowercase
form: `.us`, `.jp`, `.de`. One value for 248 of 249 entries.

**Edge cases.**

| Code | TLD | Note |
|------|-----|------|
| GB | `.uk` | The `.gb` ccTLD exists in the IANA root but is not in use; `.uk` is. This is the only entry where the TLD does not derive from the alpha-2. |

Every other officially-assigned entry uses `.` + lowercase alpha-2.
Antarctica, Bouvet Island, and Heard Island all have TLDs in the IANA
root despite being uninhabited.

The IANA snapshot is not guaranteed to contain every ccTLD for an
officially-assigned country. At the time of v1.2.0, `.bl`, `.bq`,
`.eh`, `.mf`, and `.um` exist in the ISO 3166-1 list but not in the
IANA root as two-letter entries. These codes have no TLD assigned in
practice. When the enrichment encounters such a code, verify against
IANA directly and either populate with the delegation if one exists, or
leave `tlds: null` and note it.

**Refresh.** On IANA additions. Manual. The snapshot's `meta.generated`
records the fetch date.

---

## Determinism

Every enrichment tool writes with:

- `json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False)`
- a trailing newline
- LF line endings

Two runs on the same input produce byte-identical output. The
`check-*` modes in CI rely on this.

## CI gates

As of v1.2.0, the `check-fields` job runs four blocking checks:
python3 tools/enrich_official_name.py --check
python3 tools/enrich_field.py --field currency_codes --check
python3 tools/enrich_field.py --field calling_codes --check
python3 tools/enrich_field.py --field tlds --check


A red job names the entries that are still missing a field. The
remediation is to run the enrichment tool for the batch and commit
the result.

## Refresh policy

Every field's source is a standards body. Each has its own cadence:

| Field | Source | Cadence |
|-------|--------|---------|
| `official_name` | ISO 3166-1 | per amendment |
| `currency_codes` | ISO 4217 | per amendment |
| `calling_codes` | ITU-T E.164 | rare |
| `tlds` | IANA | rare |

There is no automatic sync. Every refresh is a human-reviewed commit
with the source citation recorded in the entry's `note` field.

## `languages`

**Source.** CIA World Factbook, per country page.

**Shape.** ISO 639-3 language codes for the languages the Factbook
lists as major languages of the country. Capped at ten entries; the
`note` field records where the source lists more.

**Edge cases.**
- Multilingual: CH (deu, fra, ita, roh), BE (nld, fra, deu),
  ZA (zul, xho, afr, eng), IN (hin, eng, and twenty-two scheduled
  languages).
- Chinese: use `cmn` for Mandarin, `yue` for Cantonese. ISO 639-1's
  `zh` is ambiguous.
- Arabic: `ara` is the macrolanguage. Use it where the Factbook
  says "Arabic".
- No permanent population: AQ has `languages: []`.

**Refresh.** On CIA World Factbook update; approximately annual.

## `borders`

**Source.** CIA World Factbook `Land boundaries` section per country.

**Shape.** ISO 3166-1 alpha-2 codes of every country the Factbook
names as a land neighbor.

**Edge cases.**
- Maritime-only borders are not included: UK and France share no
  land border. IE and GB do.
- Island states have `borders: []`: IS, MT, JP, NZ, AU, PH, ID, LK,
  MG, MU, CV, CU, JM, and others.
- Non-UN-observed entities: XK (Kosovo) is a border for AL, ME, MK,
  RS. The registry carries XK as a user-assigned entry.
- Symmetry: if A borders B, B must border A. `validate.py` enforces
  this in the business layer.

**Refresh.** On CIA World Factbook update; approximately annual.

## `subregion`

**Source.** UN M49 classification.

**Shape.** The country's subregion as named by the UN M49 standard.
A scalar string, not a list. On active entries, populated from UN M49
at initial import. On withdrawn entries, populated by hand where a
single subregion applies.

**Edge cases.**
- Entries that spanned multiple subregions stay null: FQ (French
  Southern and Antarctic Territories), SU (USSR).
- Uninhabited entries stay null: CT, JT, MI, NQ, WK.
- The UN M49 does not assign a subregion to AQ (Antarctica) or to
  TW (Taiwan). Both stay null on the active side.
- Each null entry carries a note explaining why.

**Refresh.** Rare. The UN M49 subregion list is closed: 22 names.

