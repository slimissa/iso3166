# v1.12.0 Phase 1: Club memberships snapshot

Tree: v1.11.1 (bcb0d0a), unchanged. Deliverable: four snapshots, their meta files,
the generator, an ADR, and this file. No code, wrapper or CLI change.

## Source audit
Reached Wikipedia 2026-10-29 through the research tool (web_fetch), not through the
bash sandbox, which cannot reach it. The pages were read in full. Table cells for
dates were partly stripped in the fetched text, so dates were taken from the prose
and tables that survived, and the eurozone dates were checked against the Council
of the EU timeline. No date was invented. The ones that are inferences are listed under "Confidence".

### EU (Member state of the European Union)
| Date | Members |
|---|---|
| Founder, no date in table | BE, DE, FR, IT, LU, NL |
| 1973-01-01 | DK, IE, GB |
| 1981-01-01 | GR |
| 1986-01-01 | ES, PT |
| 1995-01-01 | AT, FI, SE |
| 2004-05-01 | CY, CZ, EE, HU, LV, LT, MT, PL, SK, SI |
| 2007-01-01 | BG, RO |
| 2013-07-01 | HR |
| Brexit | GB left 2020-01-31, transition ended 2020-12-31 |

### EEA
Founding 1994-01-01 (EU states of the time except AT/FI/SE which were EFTA members, plus IS, NO). LI 1995-05-01.
2004 ten: formal 2005-12-06, provisional 2004-05-01. BG, RO: formal 2011-11-09, provisional 2007-08-01. HR: formal 2025-02-19, provisional date not in source.
GB: 1994-01-01 to 2020-12-31 (table says 2020-01-31; prose says 2020-12-31).
Switzerland is not in the EEA (bilateral treaties).

### Eurozone
1999-01-01: AT, BE, DE, ES, FI, FR, IE, IT, LU, NL, PT. GR 2001-01-01. SI 2007. CY, MT 2008. SK 2009. EE 2011. LV 2014. LT 2015. HR 2023. BG 2026-01-01 (21 members). No state has left. The 2002-01-01 cash changeover is not a membership date.

### EU Customs Union
All EU members (from max of accession and 1968-07-01), GB until 2020-12-31, plus bilateral: MC (1968, year only), AD (1991-01-01, excludes agriculture), TR (1995-12-31, excludes agriculture), SM (2002-04-01).
Excluded: GI (provisional 2026-07-15, not in force), Akrotiri and Dhekelia (no ISO code).

## Confidence
- [Confirmed] All accession dates; eurozone dates; GB EU end 2020-01-31; EEA formal dates for 2004, 2007 and 2013 (Wikipedia table).
- [Likely] 1958-01-01 for founders; GB EEA end 2020-12-31; customs union start 1968-07-01; HR formal EEA date 2025-02-19 (the fetched table text was partly stripped; verify against the live table).
- [Guess] MC customs union day (1968-07-01); EEA provisional date for HR (not recorded).

## Output counts
EU 28, EEA 31, eurozone 21, customs union 32.

## Self-check
- [x] 4 snapshots, each with meta and data, each with a sibling meta file.
- [x] Counts >= 27 / 30 / 20 / 30.
- [x] GB EU range ends 2020-01-31.
- [x] GR eurozone range starts 2001-01-01.
- [x] ADR names source, coverage, null policy, annual refresh.
- [x] `check_snapshot_freshness.py` reports all four OK.
- [x] `build_club_snapshots.py --check` exits 0.
- [ ] oldid permalinks: not obtainable here. Open item.
- Not run: tests/test_architecture.py, test_enrich_independent.py and test_export_aggregated.py fail identically on the clean tree (pytest missing in this sandbox), so they say nothing about this change.
