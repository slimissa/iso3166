# v1.11.0 Phase 1 (v2): snapshot from explicit list

Delivered as `v1.11.0-phase1.tar.gz`. The tree (`iso3166.json`, VERSION, wrappers, CLI) is unchanged. [Confirmed: byte-compared.]

## Audit output
    VERSION: 1.10.2
    active 252 withdrawn 25
    active keys ['alpha_2', 'alpha_3', 'borders', 'calling_codes', 'currency_codes', 'independent', 'intermediate_region', 'languages', 'last_verified', 'name', 'note', 'numeric', 'official_name', 'region', 'replaced_by', 'status', 'subregion', 'tlds', 'withdrawal_date']
    status values Counter({'officially-assigned': 249, 'exceptionally-reserved': 2, 'user-assigned': 1})
    non-officially: [('EU', 'exceptionally-reserved', 'European Union'), ('UK', 'exceptionally-reserved', 'United Kingdom (exceptionally reserved)'), ('XK', 'user-assigned', 'Kosovo')]
    data 50 in active 49 in withdrawn ['CS'] unknown []
    withdrawn [('AI', '1977-06-27'), ('AN', '2010-12-01'), ('BU', '1989-12-05'), ('CS', '2006-09-26'), ('CT', '1984-01-01'), ('DD', '1990-10-03'), ('DY', '1977-02-01'), ('FQ', '1979-01-01'), ('HV', '1984-08-04'), ('JT', '1986-01-01'), ('MI', '1986-01-01'), ('NH', '1980-07-30'), ('NQ', '1983-01-01'), ('NT', '1993-07-01'), ('PC', '1986-11-03'), ('PZ', '1980-01-01'), ('RH', '1980-04-18'), ('SK', '1975-05-16'), ('SU', '1992-08-30'), ('TP', '2002-05-20'), ('VD', '1976-07-02'), ('WK', '1986-01-01'), ('YD', '1990-05-22'), ('YU', '2003-07-23'), ('ZR', '1997-05-17')]
    input-contract.md
    languages-audit-2026-09.md
    languages-borders-sources.md
    v1.0.0-decisions.md
    v1.5.0-scope.md
    v1.9.2-amendments.md
    v1.9.3-version-policy.md
    withdrawn-codes.md
    tools/check_iso4217_snapshot.py
    tools/check_snapshot_freshness.py
    tools/gen_iso4217_snapshot.py
    tools/iana_tld_snapshot.json
    tools/independent_snapshot.json
    tools/iso4217_snapshot.json
    tools/iso639_3_snapshot.json
    tools/itu_calling_code_snapshot.json
    tools/m49_intermediate_region_snapshot.json
    tools/m49_subregion_snapshot.json

## Source summary
Wikipedia ISO 3166-1 "Changes", permalink `https://en.wikipedia.org/w/index.php?title=ISO_3166-1&oldid=1258392980`, accessed 2026-10-28. The sandbox cannot reach Wikipedia, so the file was not checked against the live page. Reason for the exception: ISO OBP shows no assignment dates (see the ADR).

## Coverage (252 active, 25 withdrawn)
| Bucket | Count |
|---|---|
| 1974 list | 161 |
| Dated from `data` | 15 |
| Null: not officially assigned (EU, UK, XK) | 3 |
| Null: quarantined | 27 |
| Null: source silent | 46 |
| Total active | 252 |
| Withdrawn (all null) | 25 |

176 of 252 active codes have a date. Snapshot keys: 275, not 277, because AI and SK are both active and withdrawn.

## Validation
- All 50 codes in `data` exist in the tree. [Confirmed]
- Every active code has exactly one value or a reason. No date is in the future or before 1974-01-01. The generator enforces both.
- `--check` exits 0 after generation and after regeneration (idempotent).
- `check_snapshot_freshness.py` reads the sibling meta: `review_by 2027-10-28 (sibling)`.

## Spot checks
DE, FR, US, JP, GB = 1974-09-15; PS = 1999-10-01; AX = 2004-02-13; SS = 2011-08-09; TL = 2002-05-20. All match. EU, UK, XK, CD, BF, DD, CS = null.

## Where the prompt was wrong
1. **The list has 184 codes, not 142.** [Confirmed]
2. **27 codes you asked me to date as 1974, or took from `data`, are set to null.** Six are contradicted by your own tree (BJ, DJ, VU, ZW, KI, MM are successors of codes withdrawn after 1974). 17 are post-Soviet, Czechoslovak or Yugoslav states [Likely]. ER, SH, MD and BA are newsletter dates that look like changes [Likely]. They are in `QUARANTINE` in the generator, each with a reason. Delete a line there to accept the list's value.
3. **The list omits ~30 original-1974 territories**, so they are null rather than 1974.
4. **"Withdrawn entries ... 277 keys" is impossible** with alpha_2 keys (AI, SK).
5. **My earlier STOP report overstated some conflicts.** IN, PA, AQ, TF and YE are merges or renames of codes that already existed, so they are not offenders.
6. **Precedence in your prompt was contradictory** (JSON wins vs list wins). I applied the algorithm's order: list first. This ignores `data` rows for 30 codes (e.g. DE 2012-02-15).
7. The 1974-09-15 date itself is [Guess]; I cannot verify it.

## Extra file
`tools/wikipedia_dates.json` is included (unchanged input) because `--check` needs it in the repo.
