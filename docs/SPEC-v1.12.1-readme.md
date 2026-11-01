# SPEC.md: the v1.12.1 README rewrite

Base: `slimissa/iso3166` v1.12.1, the tree in `iso3166-main_1.zip` (189 files, no `.git` directory, so the commit and tag cannot be inspected here). Delivered: `README.md`, this file, and `commit-messages/01-readme-rewrite.txt`. No code, data, gate, CI or version change.

Confidence tags: [Confirmed] observed in this session; [Likely] strong inference; [Guess] unverified.

## Result

- `README.md`: 24 numbered sections plus a table of contents, 1,300+ lines. Every number in it comes from the audit below.
- It replaces a README that is itself gated. `tools/check_docs_match_tree.py` and `tools/check_release_claims.py` read it, so the rewrite had to keep `29 checks run in sequence`, every `N CI jobs` at 21, a `### Additional checks` section whose `carries eight auxiliary checks` count equals its table rows, the phrase `twenty-four fields`, and the `registry-1.12.1` badge. The prompt did not mention this. [Confirmed]
- **The prompt disagrees with the tree in 14 places** (next section). The tree won each time. The two most visible: there are 16 derived queries, not 15, and the release gate has 29 checks, not 30.

## Checks run against the new README (in a copy of the tree)

| Check | Result |
|-------|--------|
| `tools/check_version_consistency.py` | OK (9 result lines, 10 files) |
| `tools/check_mojibake.py` | OK, 180 files scanned |
| `tools/check_docs_match_tree.py` | OK, 13 of 13 |
| `tools/check_state_doc.py --strict` | OK |
| `tools/check_release_claims.py 1.12.1` | OK, 23 of 23 claims |
| `python3 -m pytest tests/ -q` | 27 passed |
| `wrappers/python` pytest | 104 passed |
| `wrappers/javascript` `node --test` | 52 passed |
| README table of contents | 24 headings, 24 anchors, 0 broken; code fences balanced |
| Quick-start snippets (Python, JavaScript) | Run; outputs match the comments |
| Worked example (DuckDB 2.0.0, PyArrow 26.0.0) | Run; counts equal the Python wrapper's |
| SQLite load of `iso3166.sqlite.sql` | 277 and 249 rows, `GB` club cell `1973-01-01:2020-01-31` |

**Not run, and why.** Rust and Go suites: no `cargo` or `go` in the sandbox, so their test counts (27, 41) are static counts of `#[test]` and `func Test` declarations, and the README says so. `scripts/release.sh --dry-run`: needs `gh` and network. The sibling repositories' claims in "Consumed by": not in this tree; the README marks them "not checkable from this tree". Rendering on github.com: only anchors were checked, with a slug function. [Confirmed]

## Where the prompt was wrong

| # | Prompt said | Tree says | README does |
|--:|-------------|-----------|-------------|
| 1 | 15 derived queries | 16. `derived.py` has 12 public queries (`is_eu`, `is_eea`, `is_eurozone`, `region_tree`, `borders_transitively`, `succession_path`, `successors`, `predecessors`, `calling_code_for`, `currency_at`, `is_active_on`, `region_countries`); `clubs.py` has 4. The prompt's own list omits `is_active_on` though its Section 7 uses it. The previous README also says sixteen. | 16 |
| 2 | 30 gate checks | 29. `docs/STATE.md` says 29, `check_state_doc.py` verifies it, and counting the non-blank lines of the gate subshell the way `gen_state_doc.py` does gives 29. The 29th is `cargo clippy`. | 29; a 29-row table, not 30 |
| 3 | 130 cross-language cases | 129 `derived_queries.cases`. No count of the fixture gives 130: the non-derived sections hold 74 entries, 203 with the derived cases. | 129, stated as derived-query cases |
| 4 | 8 version sites, "not 9, not 11" | 10 files hold the version (`tools/version_axes.json` lists 10). The checker prints 9 result lines (the first covers two files). `release.sh` bumps and asserts 8. | 10 files, 8 bumped, with the reasons |
| 5 | `pyarrow==25.0.1` | `requirements-dev.txt` pins `pyarrow==26.0.0`. There is no `constraints.txt`. | 26.0.0; the missing constraints file is a limitation |
| 6 | Architecture guardrail in `tools/test_architecture.py`, ADR 0007 | `tests/test_architecture.py`. No ADR is numbered; `docs/decisions/` holds ten unnumbered documents. The layering rule is documented in `docs/LAYERS.md`. | The real path and `LAYERS.md` |
| 7 | "Two null regions (XK, TW)" | Five active entries have no region: `AQ`, `EU`, `TW`, `UK`, `XK`. `countries_by_region.parquet` also has 13 rows with a null region because withdrawn entries have none. | 5, with the 13 rows explained |
| 8 | `countries_by_region.parquet` is a country-grain join table ("grain, join keys") | 4 columns, 30 rows, grain `(region, subregion)`; it counts all 277 entries including the 25 withdrawn, and sums to 277, not 252. | Documented as is, with the 277 caveat |
| 9 | FAQ: `currency_at("DE", "1990-01-01")` is `None` because DE's `introduced` is 1974 | It returns `["EUR"]`: 1990 is after 1974, so the lifetime bound passes and the current currency is returned. It is `None` for 1960. | The correct FAQ answer |
| 10 | "Which countries use EUR? 21, plus the overseas territories as nulls" | 36 entries list `EUR`; 21 are in the eurozone; the other 15 (`AD`, `AX`, `BL`, `GF`, `GP`, `MC`, `ME`, `MF`, `MQ`, `PM`, `RE`, `SM`, `TF`, `VA`, `YT`) have non-null `EUR`. | 36 / 21 / 15 |
| 11 | "The 1974 list is the boundary" for club membership | The 1974 boundary is for `introduced` and `is_active_on`. The club arrays start at 1958 (EU), 1968 (customs union), 1994 (EEA), 1999 (eurozone). | Both stated separately |
| 12 | Four enums: status, classification, region, relationship | `status` and `region` only. `classification` and `relationship` are ISO 4217's. | Two enums, with a sentence saying so |
| 13 | A "fixture anchor rule" (ISO 10383's) and "5 snapshot reproductions" in the gate; "export_* --check x 6" | Neither exists in this tree. The gate has 4 `export_*` checks, plus `sync_wrappers`, `gen_consistency_fixture`, `gen_withdrawn_doc` and 10 `enrich_*` checks. No snapshot has a `gen_* --check` reproduction except an advisory ISO 4217 one. | Omitted; the 29 real rows listed |
| 14 | "Packaged CLI diverges in `--raw` (deferred to v1.12.x)" | The divergence is real (29 lines against 28 for `list --region Oceania --raw tlds`), but nothing in the tree records a deferral. The repo CLI docstring says eight subcommands, the packaged one twenty-three; both have 25. | Divergence stated, no deferral claimed |

Smaller departures:

- "A pandas + DuckDB script": the worked example uses DuckDB alone. pandas adds nothing to it.
- "Every file present in the tree named": 148 files are named individually; the 41 `docs/v*-verification.md` reports are one line with a count. The generator that renders the tree fails on any uncommented file, so nothing else is missing.
- "At a glance has 14 rows": it has exactly 14.
- The roadmap items v1.13.0, v1.14.0 and v1.16.0 come from the prompt and match `docs/QUERIES-DECISIONS.md`. v1.15.0 and v2.0.0 as stated in the prompt appear nowhere else in the tree; the previous README put subdivisions at v2.0.0.
- "Consumed by" rows for ISO 4217, ISO 10383 and Exchange Calendar come from the sibling READMEs supplied with the prompt and the previous README, not from this tree.

## Known facts not in the README

| Fact | Where it lives | Why omitted |
|------|----------------|-------------|
| Per-field sources, access dates and refresh cadence | `docs/PROVENANCE.md` | Long, and already gated by `check_docs_match_tree.py` |
| Per-field enrichment rules and where the naive rule breaks | `docs/ENRICHMENT.md` | Same |
| The 25 withdrawn codes in full | `docs/WITHDRAWN.md` | Generated; the README names six and links |
| The 23 `null_reasons` for withdrawn entries | `tools/introduced_snapshot.json` | Only the 27 active quarantines are tabled |
| The 13 checks inside `check_docs_match_tree.py` | The tool's docstring | Summarised in one gate row |
| The seven non-temporal snapshots (ISO 4217, ISO 639-3, ITU, IANA, M49 x2, `independent`) | `docs/STATE.md`, `PROVENANCE.md` | Only the five temporal snapshots are tabled; the others are named in the tree and in `docs/STATE.md` |
| `parse_source.py --verify` / `--audit`, `pip-audit`, `govulncheck`, `cargo audit` in CI | `validate.yml` | Mentioned per job, not explained |
| The 41 verification reports' contents | `docs/v*-verification.md` | Listed as a count |
| CHANGELOG detail, including the v1.10.0 breaking change to `successors` | `CHANGELOG.md` | One FAQ line |
| Tooling that is archival: `build_initial_data.py`, `migrate_notes_to_per_field.py`, `initial_exceptions.json` | Tree comments | Marked archival in the structure tree only |

## Audit output

The audit is three scripts. `/tmp/audit-readme.sh` is the entry point and calls the other two; each section header below is the script's. Run it from the repository root with `pyarrow==26.0.0`, `pandas`, `duckdb` and `pytest` installed (`bash /tmp/audit-readme.sh .`). The scripts are reproduced in the appendix. Output of the run on the v1.12.1 tree:

```text

== 1. Counts ==
active 252 withdrawn 25 total 277
meta {'count_active': 252, 'count_withdrawn': 25, 'schema_version': '1.0.0', 'source': 'ISO 3166-1:2020 (cross-checked against UN M49)', 'updated': '2026-10-31', 'version': '1.12.1'}
status {'officially-assigned': 249, 'exceptionally-reserved': 2, 'user-assigned': 1}
region {'Europe': 51, 'Asia': 50, 'Americas': 57, 'Africa': 60, None: 5, 'Oceania': 29}
independent true 195

== 2. Fields and nulls (active) ==
fields per active entry: 24
withdrawn fields: 20 ['customs_union', 'eea_membership', 'eu_membership', 'eurozone_membership']
  alpha_2                null=  0 empty_list=  0
  alpha_3                null=  0 empty_list=  0
  borders                null=  2 empty_list= 88
  calling_codes          null=  3 empty_list=  0
  currency_codes         null=  3 empty_list=  1
  customs_union          null=  0 empty_list=220
  eea_membership         null=  0 empty_list=221
  eu_membership          null=  0 empty_list=224
  eurozone_membership    null=  0 empty_list=231
  independent            null=  0 empty_list=  0
  intermediate_region    null=147 empty_list=  0
  introduced             null= 76 empty_list=  0
  languages              null=  3 empty_list=  1
  last_verified          null=  0 empty_list=  0
  name                   null=  0 empty_list=  0
  note                   null=  0 empty_list=  0
  numeric                null=  0 empty_list=  0
  official_name          null=  3 empty_list=  0
  region                 null=  5 empty_list=  0
  replaced_by            null=252 empty_list=  0
  status                 null=  0 empty_list=  0
  subregion              null=  5 empty_list=  0
  tlds                   null=  3 empty_list=  5
  withdrawal_date        null=252 empty_list=  0

== 3. Queries and CLI ==
python derived queries (def in wrappers/python/iso3166/derived.py + clubs.py):
2
python registry methods:
    def from_dict(cls, d: dict[str, Any]) -> "Country":
    def is_active(self) -> bool:
    def path(self) -> Path:
    def meta(self) -> dict[str, Any]:
    def version(self) -> str:
    def updated(self) -> str:
    def all(self) -> list[Country]:
    def all_active(self) -> list[Country]:
    def all_withdrawn(self) -> list[Country]:
    def active(self, alpha_2: str) -> Optional[Country]:
    def with_alpha2(self, alpha_2: str) -> list[Country]:
    def with_alpha3(self, alpha_3: str) -> list[Country]:
    def with_numeric(self, numeric: str) -> list[Country]:
    def by_alpha2(self, alpha_2: str) -> Optional[Country]:
    def by_alpha3(self, alpha_3: str) -> Optional[Country]:
    def by_numeric(self, numeric: str) -> Optional[Country]:
    def currencies(self, alpha_2: str) -> list[str]:
    def countries_with(self, currency_code: str) -> list[Country]:
    def region(self, region_name: str) -> list[Country]:
    def subregion(self, subregion_name: str) -> list[Country]:
    def search(self, query: str) -> list[Country]:
    def summary(self) -> dict[str, Any]:
repo CLI subcommands (tools/iso3166_cli.py):
    sp = sub.add_parser("lookup", parents=[common], help="All fields for one country.")
    sp = sub.add_parser("list", parents=[common], help="Filter across the registry.")
    sp = sub.add_parser("currency", parents=[common],
    sp = sub.add_parser("country", parents=[common],
    sp = sub.add_parser("region", parents=[common],
    sp = sub.add_parser("info", parents=[common], help="Registry metadata.")
    sp = sub.add_parser("validate", parents=[common],
    sp = sub.add_parser("search", parents=[common],
    sp = sub.add_parser("successors", parents=[common],
    sp = sub.add_parser("predecessors", parents=[common],
        sp = sub.add_parser(name, parents=[common], help=text, description=text)
    sp = sub.add_parser("region-tree", parents=[common],
    sp = sub.add_parser("borders-transitively", parents=[common],
    sp = sub.add_parser("succession-path", parents=[common],
    sp = sub.add_parser("calling-code-for", parents=[common],
    sp = sub.add_parser("currency-at", parents=[common],
    sp = sub.add_parser("region-countries", parents=[common],
    sp = sub.add_parser("introduced", parents=[common],
        sp = sub.add_parser(name, parents=[common], help=text, description=text)
    sp = sub.add_parser("is-active-on", parents=[common],
packaged CLI subcommands (wrappers/python/iso3166/cli.py):
    sp = sub.add_parser("lookup", parents=[common], help="All fields for one country.")
    sp = sub.add_parser("list", parents=[common], help="Filter across the registry.")
    sp = sub.add_parser("currency", parents=[common],
    sp = sub.add_parser("country", parents=[common],
    sp = sub.add_parser("region", parents=[common],
    sp = sub.add_parser("info", parents=[common], help="Registry metadata.")
    sp = sub.add_parser("validate", parents=[common],
    sp = sub.add_parser("search", parents=[common],
    sp = sub.add_parser("successors", parents=[common],
    sp = sub.add_parser("predecessors", parents=[common],
        sp = sub.add_parser(name, parents=[common], help=text, description=text)
    sp = sub.add_parser("region-tree", parents=[common],
    sp = sub.add_parser("borders-transitively", parents=[common],
    sp = sub.add_parser("succession-path", parents=[common],
    sp = sub.add_parser("calling-code-for", parents=[common],
    sp = sub.add_parser("currency-at", parents=[common],
    sp = sub.add_parser("region-countries", parents=[common],
    sp = sub.add_parser("introduced", parents=[common],
        sp = sub.add_parser(name, parents=[common], help=text, description=text)
    sp = sub.add_parser("is-active-on", parents=[common],

== 4. Club membership counts ==
eu_membership entries with >=1 period: 28
eea_membership entries with >=1 period: 31
eurozone_membership entries with >=1 period: 21
customs_union entries with >=1 period: 32
sample eu GB: [[{'from': '1973-01-01', 'to': '2020-01-31'}]]
sample eea NO: [[{'from': '1994-01-01', 'to': None}]]

== 5. Exports ==
countries_by_region.parquet
iso3166.csv
iso3166.european.csv
iso3166.excel.csv
iso3166.mysql.sql
iso3166.parquet
iso3166.postgresql.sql
iso3166.sql
iso3166.sqlite.sql
iso3166.tsv
flat export files (csv/tsv/sql/parquet, excl aggregated):
9
csv columns 24 rows 277
['alpha_2', 'alpha_3', 'numeric', 'name', 'status', 'independent', 'official_name', 'region', 'subregion', 'intermediate_region', 'currency_codes', 'calling_codes', 'tlds', 'languages', 'borders', 'note', 'last_verified', 'withdrawal_date', 'replaced_by', 'introduced', 'eu_membership', 'eea_membership', 'eurozone_membership', 'customs_union']
parquet columns 24 rows 277
['alpha_2', 'alpha_3', 'numeric_code', 'name', 'status', 'independent', 'official_name', 'region', 'subregion', 'intermediate_region', 'currency_codes', 'calling_codes', 'tlds', 'languages', 'borders', 'note', 'last_verified', 'withdrawal_date', 'replaced_by', 'introduced', 'eu_membership', 'eea_membership', 'eurozone_membership', 'customs_union']
parquet footer {'iso3166.version': '1.12.1', 'iso3166.updated': '2026-10-31', 'iso3166.schema_version': '1.0.0', 'iso3166.generator': 'tools/export_parquet.py'}
aggregated columns 4 rows 30 ['region', 'subregion', 'country_count', 'independent_count']
iso3166.sql:526
iso3166.postgresql.sql:526
iso3166.mysql.sql:526
iso3166.sqlite.sql:526
iso3166.sql:19:CREATE TABLE countries (
iso3166.sql:46:CREATE TABLE country_currencies (
iso3166.postgresql.sql:19:CREATE TABLE countries (
iso3166.postgresql.sql:46:CREATE TABLE country_currencies (
iso3166.mysql.sql:22:CREATE TABLE countries (
iso3166.mysql.sql:49:CREATE TABLE country_currencies (
iso3166.sqlite.sql:19:CREATE TABLE countries (
iso3166.sqlite.sql:46:CREATE TABLE country_currencies (
CREATE TABLE countries (
    alpha_2              CHAR(2)      NOT NULL,
    alpha_3              CHAR(3)      NOT NULL,
    numeric_code         CHAR(3)      NOT NULL,
    name                 VARCHAR(255) NOT NULL,
    status               VARCHAR(30)  NOT NULL,
    independent          BOOLEAN      NOT NULL,
    official_name        VARCHAR(255),
    region               VARCHAR(50),
    subregion            VARCHAR(80),
    intermediate_region  VARCHAR(80),
    calling_codes        VARCHAR(120),
    tlds                 VARCHAR(120),
    languages            VARCHAR(80),
    borders              VARCHAR(160),
    note                 TEXT,
    last_verified        CHAR(10),
    withdrawal_date      CHAR(10),
    replaced_by          VARCHAR(80),
    introduced           CHAR(10),
    eu_membership        VARCHAR(80),
    eea_membership       VARCHAR(80),
    eurozone_membership  VARCHAR(80),
    customs_union        VARCHAR(80),
    PRIMARY KEY (alpha_2, status)
);
CREATE TABLE country_currencies (
    country_alpha_2 CHAR(2) NOT NULL,
    currency_code   CHAR(3) NOT NULL,
    PRIMARY KEY (country_alpha_2, currency_code)
);

== 6. Tests ==
root pytest:
...........................                                              [100%]
27 passed in 4.21s
wrapper python:
........................................................................ [ 69%]
................................                                         [100%]
104 passed in 5.50s
wrapper js (node --test):
# tests 52
# pass 52
# fail 0
wrapper rust #[test] count (static):
wrappers/rust/tests/consistency.rs:19
wrappers/rust/src/lib.rs:8
wrapper go func Test count (static):
wrappers/go/clubs_test.go:3
wrappers/go/derived_test.go:1
wrappers/go/registry_test.go:37
cross-language fixture:
dict ['lookup_withdrawn_fields', 'lookup_fields', 'lookup_withdrawn', '_comment', 'version', 'lookup_alpha2', 'lookup_alpha2_missing', 'lookup_alpha3', 'lookup_numeric', 'counts']
   lookup_withdrawn_fields 5
   lookup_fields 10
   lookup_withdrawn 5
   lookup_alpha2 6
   lookup_alpha2_missing 4
   lookup_alpha3 4
   lookup_numeric 3
   counts 4
   overlap_codes 2
   region_query 5
   currencies 3
   countries_with 3
   search 3
   optional_absent 2
   independent 6
   empty_inputs 3
   lookup_numeric_absent 3
   lookup_alpha2_ambiguous 3
   successors 3
   predecessors 3
   derived_queries 3
node: present
cargo: MISSING (suite not run here)
go: MISSING (suite not run here)

== 7. Gate steps (release.sh) ==
grep -cE 'python3 tools/|bash tools/' scripts/release.sh = 34
gate subshell lines (between 'set -e' and the closing paren):
1:         python3 tools/check_version_consistency.py
2:         python3 tools/check_release_claims.py "$VERSION"
3:         python3 tools/check_mojibake.py
4:         python3 tools/check_snapshot_freshness.py
5:         python3 tools/check_registry_freshness.py
6:         python3 tools/validate.py iso3166.json --strict-count --strict-independent
7:         python3 tools/check_state_doc.py --strict
8:         python3 tools/check_docs_match_tree.py
9:         python3 tools/enrich_official_name.py --check
10:         python3 tools/enrich_withdrawn.py --check
11:         python3 tools/enrich_field.py --field currency_codes --check
12:         python3 tools/enrich_field.py --field calling_codes --check
13:         python3 tools/enrich_field.py --field tlds --check
14:         python3 tools/enrich_field.py --field languages --check
15:         python3 tools/enrich_field.py --field borders --check
16:         python3 tools/enrich_field.py --field subregion --check
17:         python3 tools/enrich_field.py --field intermediate_region --check
18:         python3 tools/enrich_club_memberships.py --check
19:         python3 tools/export_sql.py --check
20:         python3 tools/export_csv.py --check
21:         python3 tools/export_parquet.py --check
22:         python3 tools/export_aggregated.py --check
23:         python3 tools/sync_wrappers.py --check
24:         python3 tools/gen_consistency_fixture.py --check
25:         python3 tools/gen_withdrawn_doc.py --check
26:         python3 -m pytest tests/ -v
27:         python3 -m pytest wrappers/python/tests/ -q
28:         bash tools/check_cross_language.sh US GB JP
322:    GATE_LOG=/tmp/release-gate.log
354:    ) > "$GATE_LOG" 2>&1 \
355:        || { tail -20 "$GATE_LOG"; die "gate failed; see $GATE_LOG"; }
358:    tail -3 "$GATE_LOG"

== 8. CI ==
validate.yml
jobs: 21
   validate-json
   check-version-consistency
   check-iso4217-snapshot
   check-wrapper-sync
   check-sql-export
   check-csv-export
   check-parquet-export
   check-cli
   check-docs
   check-withdrawn
   check-withdrawn-doc
   check-fields
   check-state-doc
   check-docs-match-tree
   check-mojibake
   check-snapshot-freshness
   cross-language
   wrapper-python
   wrapper-javascript
   wrapper-go
   wrapper-rust
on: name: validate

on:
  push:
    branches: [main, "v*"]
    paths-ignore:
      - ".gitignore"
      - ".gitattributes"
      - "LICENSE"
  pull_request:
    branches: [main]
    paths-ignore:
      - ".gitignore"
      - ".gitattributes"
      - "LICENSE"
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read


sanctions-freshness.yml present?
ls: cannot access '.github/workflows/sanctions-freshness.yml': No such file or directory

== 9. Version sites ==
version consistency

  OK    VERSION == meta.version (1.12.1)
  OK    CHANGELOG contains [ 1.12.1 ]
  OK    README status == VERSION (1.12.1)
  OK    Parquet footer == VERSION (1.12.1)
  OK    wrappers/python/pyproject.toml == VERSION (1.12.1)
  OK    wrappers/python/iso3166/__init__.py == VERSION (1.12.1)
  OK    wrappers/javascript/package.json == VERSION (1.12.1)
  OK    wrappers/rust/Cargo.toml == VERSION (1.12.1)
  OK    wrappers/rust/Cargo.lock == VERSION (1.12.1)

OK
release.sh claims:
7:# Verifies preconditions, bumps the version sites, regenerates
234:step "1/7 bump version sites to $VERSION"
305:    echo "  all 8 version sites read $VERSION"
375:        die "nothing staged; version sites may already be correct"
version_axes.json sites:
10

== 10. Snapshots and review_by ==
tools/customs_union_snapshot.json
tools/customs_union_snapshot.meta.json
tools/eea_membership_snapshot.json
tools/eea_membership_snapshot.meta.json
tools/eu_membership_snapshot.json
tools/eu_membership_snapshot.meta.json
tools/eurozone_membership_snapshot.json
tools/eurozone_membership_snapshot.meta.json
tools/iana_tld_snapshot.json
tools/independent_snapshot.json
tools/introduced_snapshot.json
tools/introduced_snapshot.meta.json
tools/iso4217_snapshot.json
tools/iso639_3_snapshot.json
tools/itu_calling_code_snapshot.json
tools/m49_intermediate_region_snapshot.json
tools/m49_subregion_snapshot.json
tools/wikipedia_dates.json
--- tools/customs_union_snapshot.meta.json
{'source': 'Wikipedia: European Union Customs Union (tables for non-EU participants and bilateral unions), plus EU accession dates from the EU snapshot', 'source_permalink': 'https://en.wikipedia.org/wiki/European_Union_Customs_Union', 'vendored_at': '2026-10-29', 'review_by': '2027-10-29', 'refresh_cadence': 'annual'}
--- tools/eea_membership_snapshot.meta.json
{'source': "Wikipedia: European Economic Area (state table, 'Entered into force' column); provisional-application dates from EFTA, EEA Legal Texts (EEA Enlargement) and Wikipedia, EEA Agreement", 'source_permalink': 'https://en.wikipedia.org/wiki/European_Economic_Area', 'vendored_at': '2026-10-29', 'review_by': '2027-10-29', 'refresh_cadence': 'annual'}
--- tools/eu_membership_snapshot.meta.json
{'source': 'Wikipedia: Member state of the European Union (member and withdrawal tables)', 'source_permalink': 'https://en.wikipedia.org/wiki/Member_state_of_the_European_Union', 'vendored_at': '2026-10-29', 'review_by': '2027-10-29', 'refresh_cadence': 'annual'}
--- tools/eurozone_membership_snapshot.meta.json
{'source': "Wikipedia: Eurozone (Euro area), prose on enlargements; cross-checked against the Council of the EU 'Timeline - Joining the euro area' page", 'source_permalink': 'https://en.wikipedia.org/wiki/Euro_area', 'vendored_at': '2026-10-29', 'review_by': '2027-10-29', 'refresh_cadence': 'annual'}
--- tools/introduced_snapshot.meta.json
{'source': 'Wikipedia: ISO 3166-1 Changes (Edition/Newsletter table)', 'source_permalink': 'https://en.wikipedia.org/w/index.php?title=ISO_3166-1&oldid=1258392980', 'vendored_at': '2026-10-28', 'review_by': '2027-10-28', 'refresh_cadence': 'annual'}
tools/customs_union_snapshot.json top-keys: ['meta', 'data'] meta.review_by: 2027-10-29
tools/eea_membership_snapshot.json top-keys: ['meta', 'data'] meta.review_by: 2027-10-29
tools/eu_membership_snapshot.json top-keys: ['meta', 'data'] meta.review_by: 2027-10-29
tools/eurozone_membership_snapshot.json top-keys: ['meta', 'data'] meta.review_by: 2027-10-29
tools/iana_tld_snapshot.json top-keys: ['_comment', 'meta', 'tlds'] meta.review_by: 2027-09-27
tools/independent_snapshot.json top-keys: ['meta', 'entries'] meta.review_by: n/a
tools/introduced_snapshot.json top-keys: ['meta', 'data'] meta.review_by: 2027-10-28
tools/iso4217_snapshot.json top-keys: ['_comment', 'active', 'meta', 'withdrawn'] meta.review_by: 2027-10-25
tools/iso639_3_snapshot.json top-keys: ['_comment', 'languages', 'meta'] meta.review_by: 2027-09-27
tools/itu_calling_code_snapshot.json top-keys: ['_comment', 'codes', 'meta'] meta.review_by: 2027-09-27
tools/m49_intermediate_region_snapshot.json top-keys: ['_comment', 'intermediate_regions', 'meta'] meta.review_by: closed
tools/m49_subregion_snapshot.json top-keys: ['_comment', 'meta', 'subregions'] meta.review_by: closed

== 11. Introduced: dated / null / quarantined ==
dated 176 null 76
meta keys: ['meta'] ['source', 'source_permalink', 'vendored_at', 'review_by', 'refresh_cadence']
snapshot top keys: ['meta', 'data']
null_reasons type: dict
null_reasons total entries: 99
   46 x source silent
   23 x withdrawn: start date not sourced
   14 x quarantined [likely]: post-Soviet state; SU withdrawn 1992-08-30 (tree); code cannot be in 1974 edition
   3 x quarantined [likely]: successor state of Czechoslovakia/Yugoslavia; not a 1974 code
   2 x not officially assigned (exceptionally-reserved)
   1 x quarantined [likely]: 2002-05-20 is a change newsletter; Bosnia added ~1992
   1 x quarantined [confirmed]: successor of DY, withdrawn 1977-02-01 (tree)
   1 x quarantined [confirmed]: successor of AI, withdrawn 1977-06-27 (tree)
   1 x quarantined [likely]: 2012-02-15 is a change newsletter; Eritrea was added later (~1993)
   1 x quarantined [confirmed]: successor of CT, withdrawn 1984-01-01 (tree)
   1 x quarantined [likely]: 2008-03-31 is a change newsletter; Moldova added ~1992
   1 x quarantined [confirmed]: successor of BU, withdrawn 1989-12-05 (tree)
   1 x quarantined [likely]: 2010-02-22 is a change newsletter; Saint Helena predates it
   1 x quarantined [confirmed]: successor of NH, withdrawn 1980-07-30 (tree)
   1 x not officially assigned (user-assigned)
   1 x quarantined [confirmed]: successor of RH, withdrawn 1980-04-18 (tree)

== 12. EEA provisional ==
top keys: ['meta', 'data']
meta keys: ['source', 'source_permalink', 'permalink_note', 'accessed_at', 'review_by', 'refresh_cadence', 'generator', 'count', 'semantics', 'gb_end_note', 'provisional_application', 'provisional_accessed_at', 'provisional_note', 'cyprus_note']
provisional_application: {"BG": {"from": "2007-08-01", "to": "2011-11-08"}, "CY": {"from": "2004-05-01", "to": "2005-12-05"}, "CZ": {"from": "2004-05-01", "to": "2005-12-05"}, "EE": {"from": "2004-05-01", "to": "2005-12-05"}, "HU": {"from": "2004-05-01", "to": "2005-12-05"}, "LT": {"from": "2004-05-01", "to": "2005-12-05"}, "LV": {"from": "2004-05-01", "to": "2005-12-05"}, "MT": {"from": "2004-05-01", "to": "2005-12-05"}, "PL": {"from": "2004-05-01", "to": "2005-12-05"}, "RO": {"from": "2007-08-01", "to": "2011-11-08"}, "SI": {"from": "2004-05-01", "to": "2005-12-05"}, "SK": {"from": "2004-05-01", "to": "2005-12-05"}}

== 13. Gate count by the method tools/gen_state_doc.py uses ==
gate lines (non-empty, STATE method): 29
of which pytest: 2 enrich *--check: 10 export_* --check: 4
 1 python3 tools/check_version_consistency.py
 2 python3 tools/check_release_claims.py "$VERSION"
 3 python3 tools/check_mojibake.py
 4 python3 tools/check_snapshot_freshness.py
 5 python3 tools/check_registry_freshness.py
 6 python3 tools/validate.py iso3166.json --strict-count --strict-independent
 7 python3 tools/check_state_doc.py --strict
 8 python3 tools/check_docs_match_tree.py
 9 python3 tools/enrich_official_name.py --check
10 python3 tools/enrich_withdrawn.py --check
11 python3 tools/enrich_field.py --field currency_codes --check
12 python3 tools/enrich_field.py --field calling_codes --check
13 python3 tools/enrich_field.py --field tlds --check
14 python3 tools/enrich_field.py --field languages --check
15 python3 tools/enrich_field.py --field borders --check
16 python3 tools/enrich_field.py --field subregion --check
17 python3 tools/enrich_field.py --field intermediate_region --check
18 python3 tools/enrich_club_memberships.py --check
19 python3 tools/export_sql.py --check
20 python3 tools/export_csv.py --check
21 python3 tools/export_parquet.py --check
22 python3 tools/export_aggregated.py --check
23 python3 tools/sync_wrappers.py --check
24 python3 tools/gen_consistency_fixture.py --check
25 python3 tools/gen_withdrawn_doc.py --check
26 python3 -m pytest tests/ -v
27 python3 -m pytest wrappers/python/tests/ -q
28 bash tools/check_cross_language.sh US GB JP
29 (cd wrappers/rust && cargo clippy --all-targets -- -D warnings)
release steps:
156:step "0/7 preflight"
234:step "1/7 bump version sites to $VERSION"
310:step "2/7 regenerate artifacts and run the gate"
365:step "3/7 commit release"
401:step "4/7 push and wait for CI"
467:step "5/7 tag v$VERSION"
533:step "6/7 GitHub release"
567:step "7/7 verification report"
603:step "done — v$VERSION released"
STATE.md says:
46:21 jobs (see `.github/workflows/validate.yml`). Release gate has 29 checks (`scripts/release.sh`, step 2).
OK: every claim in STATE.md matches the tree

== 14. SQL shape ==
countries columns: 23
INSERT INTO countries: 277
INSERT INTO country_currencies: 249
header: -- iso3166.sql — ANSI SQL-92 (portable)
header: -- Generated by tools/export_sql.py from iso3166.json.
header: -- Do not edit by hand. Regenerate with:

== 15. Worked-example numbers (real queries through the Python wrapper) ==
1990-01-01 EU 12 eurozone 0
2000-01-01 EU 15 eurozone 11
2010-01-01 EU 27 eurozone 16
2023-01-01 EU 27 eurozone 20
is_eu now 27 is_eurozone now 21
currency_codes contains EUR: 36
  of which in the eurozone now: 21
  EUR but not eurozone: 15 ['AD', 'AX', 'BL', 'GF', 'GP', 'MC', 'ME', 'MF', 'MQ', 'PM', 'RE', 'SM', 'TF', 'VA', 'YT']
GB: is_eu False | is_eu_member_at 2010-01-01 True | 2020-01-31 True | 2020-02-01 False
DE: introduced ['1974-09-15'] | currency_at 1990-01-01 ['EUR'] | is_active_on 1960-01-01 False
XK is_active_on 2000-01-01: None
DD currency_at 1990-01-01: ['EUR']
GR eurozone_membership: [[{'from': '2001-01-01', 'to': None}]]
GR is_eurozone_member_at 2000-01-01: False
null-region entries: ['AQ', 'EU', 'TW', 'UK', 'XK']
introduced min/max: 1974-09-15 2011-08-09

== 16. Aggregated table ==
rows 30 sum country_count 277 sum independent_count 206
rows with null region: 13 | null region and null subregion: 1
footer: {}
agg: #!/usr/bin/env python3
agg: """
agg: tools/export_aggregated.py
agg: 
agg: Generate the AGGREGATED layer (countries_by_region.parquet) from the 
agg: CURATED layer (iso3166.parquet).
agg: 
agg: Architecture Rule: The AGGREGATED layer must only read from the CURATED 
agg: layer. This script must never read the RAW layer (iso3166.json) and must 
agg: not import the `json` module.
agg: 
agg: Usage:
agg:     python3 tools/export_aggregated.py
agg:     python3 tools/export_aggregated.py --check
agg:     python3 tools/export_aggregated.py --input IN.parquet --output OUT.parquet
agg: 
agg: By default the input and output are resolved against the repository root,
agg: not the current directory, so the tool works from any directory. --input
agg: and --output override them; the tests use them to run against a temporary
agg: directory without touching the committed files.
agg: 
agg: Exit codes:
agg:     0  Success (write or --check matched)
agg:     1  --check found a stale artifact
agg:     2  Usage error (missing input or malformed schema)
agg: """
agg: from __future__ import annotations
agg: 
agg: import argparse
agg: import sys

== 17. File counts ==
tracked files in the tree: 219
verification reports: 41
ADR/decision docs: 10
pyarrow pin in requirements-dev.txt:
13:pyarrow==26.0.0
constraints.txt present?
ls: cannot access 'constraints.txt': No such file or directory
docs/JOINS.md present?
ls: cannot access 'docs/JOINS.md': No such file or directory
tools/test_architecture.py present?
ls: cannot access 'tools/test_architecture.py': No such file or directory
tests/test_architecture.py present?
tests/test_architecture.py
examples/ present?
ls: cannot access 'examples': No such file or directory
ADR numbered 0007 present?
0

== 18. Drift gates (each must print OK) ==
tools/export_sql.py --check               /home/claude/t/iso3166-main/iso3166.sqlite.sql: OK
   rc=0
tools/export_csv.py --check               /home/claude/t/iso3166-main/iso3166.tsv: OK
   rc=0
tools/export_parquet.py --check           /home/claude/t/iso3166-main/iso3166.parquet: OK
   rc=0
tools/export_aggregated.py --check        countries_by_region.parquet: OK
   rc=0
tools/sync_wrappers.py --check            /home/claude/t/iso3166-main/wrappers/rust/iso3166.json: OK
   rc=0
tools/gen_consistency_fixture.py --checkfixture: OK
   rc=0
tools/gen_withdrawn_doc.py --check      /home/claude/t/iso3166-main/docs/WITHDRAWN.md: OK
   rc=0
tools/enrich_club_memberships.py --checkenrich_club_memberships: OK
   rc=0

== 19. Validator and aux checks ==
  Layer 6/6  coverage          OK

Summary: 6 OK, 0 WARN, 0 FAIL, 0 SKIP
13
==============================================================================
  OK with 1 warning(s): review_by unset
==============================================================================
OK: all 277 entries verified within 365 days of 2026-11-01
  all 23 claim(s) verified
tools/check_* files:
tools/check_cross_language.sh
tools/check_docs_match_tree.py
tools/check_iso4217_snapshot.py
tools/check_mojibake.py
tools/check_registry_freshness.py
tools/check_release_claims.py
tools/check_snapshot_freshness.py
tools/check_state_doc.py
tools/check_version_consistency.py

== 20. CLI exit codes and outputs (repo CLI via bin/iso3166) ==
$ bin/iso3166 is-eu DE
true
[exit 0]
$ bin/iso3166 is-eu GB
false
[exit 0]
$ bin/iso3166 is-eu XX
error: not found: XX
[exit 1]
$ bin/iso3166 is-eu-member-at GB 2010-01-01
true
[exit 0]
$ bin/iso3166 is-eu-member-at GB 2023-01-01
false
[exit 1]
$ bin/iso3166 is-active-on XK 2000-01-01
unknown
[exit 4]
$ bin/iso3166 is-active-on DE 1960-01-01
false
[exit 1]
$ bin/iso3166 currency-at DE 1990-01-01
EUR
[exit 0]
$ bin/iso3166 successors YU --raw alpha_2
CS
ME
RS
[exit 0]
$ bin/iso3166 introduced DE
1974-09-15
[exit 0]
$ bin/iso3166 validate US FR DE
  US  ok
  FR  ok
  DE  ok
[exit 0]
$ bin/iso3166 --registry /nonexistent.json info
error: registry not found: /nonexistent.json
[exit 3]
$ bin/iso3166 is-eu-member-at GB 2010-13-45
error: malformed date: '2010-13-45' (want YYYY-MM-DD)
[exit 2]
--- --raw divergence (repo CLI vs packaged CLI), one null list field
28
29
29

== 21. CI jobs and what each runs ==
validate-json: needs=-
     pip install --dry-run -r requirements-dev.txt
     pip install -r requirements-dev.txt
     python3 tools/validate.py iso3166.json --strict-count --strict-independent --verbose
     python3 -m pytest tests/ -v
     python3 tools/parse_source.py --verify iso3166.json
     python3 tools/parse_source.py --audit \
check-version-consistency: needs=-
     pip install --dry-run -r requirements-dev.txt
     pip install -r requirements-dev.txt
     python3 tools/check_version_consistency.py
check-iso4217-snapshot: needs=-
     python3 tools/check_iso4217_snapshot.py
check-wrapper-sync: needs=-
     python3 tools/sync_wrappers.py --check
     python3 tools/gen_consistency_fixture.py --check
check-sql-export: needs=-
     python3 tools/export_sql.py --check
check-csv-export: needs=-
     python3 tools/export_csv.py --check
check-parquet-export: needs=-
     pip install --dry-run -r requirements-dev.txt
     pip install -r requirements-dev.txt
     python3 tools/export_parquet.py --check
     pip install pyarrow pandas
     python3 tools/export_aggregated.py --check
check-cli: needs=-
     python3 tools/iso3166_cli.py lookup US >/dev/null
     python3 tools/iso3166_cli.py lookup XX >/dev/null 2>&1 && exit 1
     python3 tools/iso3166_cli.py bogus >/dev/null 2>&1 && exit 1
     python3 tools/iso3166_cli.py --registry /nonexistent.json info >/dev/null 2>&1 && exit 1
     python3 - <<'PY'
check-docs: needs=-
     python3 - <<'PY'
check-withdrawn: needs=-
     python3 tools/enrich_withdrawn.py --check
check-withdrawn-doc: needs=-
     python3 tools/gen_withdrawn_doc.py --check
check-fields: needs=-
     python3 tools/enrich_official_name.py --check
     python3 tools/enrich_field.py --field currency_codes --check
     python3 tools/enrich_field.py --field calling_codes --check
     python3 tools/enrich_field.py --field tlds --check
     python3 tools/enrich_field.py --field languages --check
     python3 tools/enrich_field.py --field borders --check
     python3 tools/enrich_field.py --field subregion --check
     python3 tools/enrich_field.py --field intermediate_region --check
     python3 tools/enrich_club_memberships.py --check
check-state-doc: needs=-
     python3 tools/check_state_doc.py --strict
check-docs-match-tree: needs=-
     python3 tools/check_docs_match_tree.py
check-mojibake: needs=-
     python3 tools/check_mojibake.py
check-snapshot-freshness: needs=-
     python3 tools/check_snapshot_freshness.py
cross-language: needs=['[check-wrapper-sync]']
     bash tools/check_cross_language.sh US GB JP TW XK UK
     node-version: "22"
     go-version: "1.22"
wrapper-python: needs=-
     pip install --dry-run -r requirements-dev.txt
     pip install -r requirements-dev.txt
     python3 -m pytest wrappers/python/tests/ -v
     python3 -m pip install -e wrappers/python
     python3 -m pip install pytest
     python3 -m pip install pip-audit
wrapper-javascript: needs=-
     npm test
     node-version: ${{ matrix.node }}
wrapper-go: needs=-
     go vet ./...
     go test ./... -v
     go-version: ${{ matrix.go }}
     go install golang.org/x/vuln/cmd/govulncheck@v1.1.4
wrapper-rust: needs=-
     cargo clippy --all-targets -- -D warnings
     cargo test
     cargo install cargo-audit --locked
     cargo audit

== 22. Release script facts ==
#!/usr/bin/env bash
#
# scripts/release.sh — deterministic release for the ISO 3166 registry.
#
# Usage:  scripts/release.sh <version> [--dry-run | --force]
#
# Verifies preconditions, bumps the version sites, regenerates
# artifacts, runs the gate, commits, pushes, waits for CI to complete
# green, tags, creates the GitHub release, and writes the verification
# report.
#
# --force: resume from a post-commit state. When VERSION already
#   equals the target (because a previous run committed the release
#   but did not reach the tag, e.g. CI failed after the commit), the
#   script normally refuses with "VERSION already reads X; nothing to
#   do". With --force, it skips the bump, commit, and push steps
#   (they have already happened), verifies a 'chore: release vX.Y.Z'
#   commit exists in history and HEAD is on origin/main, runs the
#   gate, then tags, creates the release, and writes the verification
#   report. The gate and the CI check are NOT bypassed. --force and
#   --dry-run are mutually exclusive.
#
# Requires: bash 4+, git, gh, python3, cargo, GNU coreutils. The
# working tree must be clean and on main.
#
# Platform: Linux-only. Tested on Ubuntu 22.04. Uses GNU grep -P,
# find -exec basename, and other GNU-only constructs. macOS/BSD
# compatibility is not verified. If you need to cut a release from
# macOS, run scripts/release.sh inside a Linux container (Docker:
# ubuntu:22.04 with bash, git, gh, python3, cargo installed).
--- preflight / tag / github release / verification doc lines
79:CI_START_TIMEOUT=180  # die if no CI run appears within this many seconds
100:            die "workflow $wf is not in POLLED_WORKFLOWS; add it to the array"
111:        die "release_claims.json has no entry for version $VERSION"
137:        die "release script references undefined variables"
158:[ -d .git ] || die "not in a git repository"
162:    die "working tree is dirty; commit or stash first"
166:[ "$BRANCH" = "main" ] || die "must be on main (currently on $BRANCH)"
171:[ "$LOCAL_SHA" = "$REMOTE_SHA" ] || die "main is not up to date with origin/main"
179:    die "no CI runs found for HEAD ($LOCAL_SHA); push first and wait for CI"
182:    die "CI on HEAD ($LOCAL_SHA) is still running; wait for it to complete"
188:    die "CI on HEAD ($LOCAL_SHA) is not green (failure, cancelled, timed_out, or startup_failure); fix and push before releasing"
195:    die "CI on HEAD ($LOCAL_SHA) did not conclude 'success' (got: $BAD_RUNS); fix and push before releasing"
200:    || die "CHANGELOG.md has no '## [$VERSION]' section; write it before releasing"
207:        die "VERSION already reads $VERSION; nothing to do (use --force to resume from post-commit state)"
219:    die "tag v$VERSION already exists locally; delete it or pick a different version"
222:    die "tag v$VERSION already exists on origin; pick a different version"
303:        [ "$s" = "$VERSION" ] || die "version site mismatch: one reads $s, expected $VERSION"
355:        || { tail -20 "$GATE_LOG"; die "gate failed; see $GATE_LOG"; }
369:        die "resume mode: no 'chore: release v$VERSION' commit in history; --force can only resume from a post-commit state"
375:        die "nothing staged; version sites may already be correct"
385:        || die "staged changes touch only paths ignored by validate.yml; CI will not run on this commit. Inspect: git diff --cached --stat"
408:        die "resume mode: HEAD $LOCAL_SHA is not on origin/main ($ORIGIN_SHA); push first"
412:    git push origin main
428:            if [ "$elapsed" -ge "$CI_START_TIMEOUT" ]; then
429:                die "no CI run for $RELEASE_SHA appeared within ${CI_START_TIMEOUT}s; check paths-ignore, Actions status, and gh auth (gh errors are suppressed here)"
449:            die "CI failed on $RELEASE_SHA"
461:        die "CI did not complete within $((CI_POLL_INTERVAL * CI_POLL_MAX))s"
492:        || die "tag message file is empty: $TAG_MESSAGE_FILE"
498:        if ! git tag -d "v$VERSION" >/dev/null 2>&1; then
499:            die "$1; git tag -d also failed; tag may still exist locally"
501:        die "$1; local tag deleted before push"
504:    git tag -a "v$VERSION" -F "$TAG_MESSAGE_FILE" --cleanup=verbatim
508:        || drop_local_tag_and_die "tag points at $TAG_SHA, not HEAD ($(git rev-parse HEAD))"
511:        drop_local_tag_and_die "could not read tag message from git"
521:        drop_local_tag_and_die "diff command failed to compare tag messages"
523:        drop_local_tag_and_die "tag message in git does not match the file"
527:    git push origin "v$VERSION"
550:    gh release create "v$VERSION" \
556:    BODY=$(gh release view "v$VERSION" --json body --jq .body)
560:        die "release body contains placeholder text; fix with 'gh release edit v$VERSION --notes-file $RELNOTES'"
570:    REPORT=docs/v"$VERSION"-verification.md
599:    git push origin main

== 23. Cross-language script ==
#!/usr/bin/env bash
#
# tools/check_cross_language.sh
#
# Run the same country lookup through all four language wrappers and
# verify they produce byte-identical output. This is the executable form
# of the ecosystem's central claim: "the JSON is the contract, and every
# wrapper agrees on what it says."
#
# Usage:
#   bash tools/check_cross_language.sh [CODE ...]
#
# Default code: US
#
# A code that no wrapper finds (for example a withdrawn code such as AN,
# which active() does not return) counts as agreement: every wrapper
# exits 1 for "not found". A wrapper that exits with any other non-zero
# status, or that finds the code while another does not, is a mismatch.
#
# Exit codes:
#   0  All wrappers agreed on every code.
#   1  At least one code produced different output across wrappers.
#   2  Usage error or missing prerequisite.
#   3  A wrapper failed to run (build error, missing toolchain, etc.).
#
# Environment:
#   SKIP_BUILD=1    Skip the Rust/Go build step. Use when the binaries
#                   are already built and you want a fast re-run.
#   PY=python3      Override the Python interpreter.
#
set -euo pipefail

# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

PY="${PY:-python3}"
./docs/QUERIES-DECISIONS.md:225:temporal anchor: an active entry returned its current currency for every date,
./docs/RELEASE_PATTERN.md:159:`Reviewed-by:` anchor mismatch) and ISO 4217's `3687bc2`
./docs/RELEASE_PATTERN.md:413:The failure mode: a patch script that aborted at an anchor
./docs/decisions/introduced-field.md:12:approximate because the tree had no temporal anchor.
./docs/ENRICHMENT.md:97:**Not in the field.** Historical currencies, pegged anchors, and

== 24. Query 9 and Query 7 conventions ==
## Query 9 — `is_active_on` (tri-state)

**Signatures.**

```python
reg.is_active_on(code: str, date: str) -> bool | None
```
```js
reg.isActiveOn(code, date) -> boolean | null
```
```rust
reg.is_active_on(code: &str, date: &str) -> Option<bool>
```
```go
reg.IsActiveOn(code, date string) *bool   // nil means unknown
```
```bash
iso3166 is-active-on DE 1990-01-01
# prints true, false or unknown; --json prints
# {"code", "date", "is_active_on": true|false|null, "result": "true|false|unknown"}
# exit 0 true, 1 false, 4 unknown, 2 on a malformed DATE or usage error
# help text: "tri-state: prints true, false, or unknown"
iso3166 introduced DE
# prints the date, or "unknown"; exit 0 known, 4 unknown (null), 1 code not found
```

**Semantics.** Was `code` an assigned ISO 3166-1 code on `date`? The answer is
tri-state, because `introduced` is null for some entries and the registry must
not turn "the source is silent" into a confident answer. In order:

1. A date that is not a real `YYYY-MM-DD` → `false`.
2. Code in neither array → `false`.
3. The code is **active** (an active entry wins when a code is in both arrays,
   AI and SK): `introduced` null → `null`; else `date >= introduced`.
4. The code is **withdrawn**: `date > withdrawal_date` → `false`. Otherwise,
   `introduced` is set → `introduced <= date`. If `introduced` is null (all 25
   withdrawn entries): `date < 1974-01-01` → `null`; else `true`. The start is
   unknown, but ISO 3166 did not exist before 1974, so the registry cannot
   answer for earlier dates and says so. From 1974-01-01 up to and including
   `withdrawal_date` the answer is `true`: the code existed at some point
   before withdrawal, but the exact start is not sourced.

`introduced` is the date the ISO 3166-1 standard added the code (see
[docs/decisions/introduced-field.md](decisions/introduced-field.md)). It is not
the date a country became independent or adopted a currency.

**Data read.** `introduced` of active entries; `withdrawal_date` and
`introduced` of withdrawn entries.

**Edge cases, with the tree's values.**
- `is_active_on("DE", "1990-01-01")` → `true`: `DE` was introduced 1974-09-15.
- `is_active_on("DE", "1970-01-01")` → `false`: before `introduced`.
- `is_active_on("BJ", "2000-01-01")` → `null`: `BJ` is quarantined, so its
  `introduced` is null.
- `is_active_on("DD", "1990-01-01")` → `true`: withdrawn 1990-10-03, start unknown.
- `is_active_on("DD", "1800-01-01")` → `null`: before 1974, the floor for ISO 3166.
- `is_active_on("DD", "1990-10-04")` → `false`: after `withdrawal_date`. The
  withdrawal date itself is inclusive (`DD` on 1990-10-03 is `true`).
- `is_active_on("YU", "2010-01-01")` → `false`: `YU` was withdrawn 2003-07-23.
- `is_active_on("ZZ", "2000-01-01")` → `false`: unknown code.
## Query 7 — `currency_at` (lifetime-bounded)

**Signatures.**

```python
reg.currency_at(code: str, date: str) -> list[str] | None
```
```js
reg.currencyAt(code, date) -> readonly string[] | null
```
```rust
reg.currency_at(code: &str, date: &str) -> Option<Vec<String>>
```
```go
reg.CurrencyAt(code, date string) ([]string, bool)   // bool is false for "no answer"
```
```bash
iso3166 currency-at DE 2000-01-01
# one code per line; --json prints a list or null
# exit 0 list, 4 unknown (None), 1 code not found, 2 malformed DATE
```

**Exactness.** `currency_at` is exact for active entries with `introduced` set
and exact for withdrawn entries with `withdrawal_date` set, in one respect:
*when the code exists*. Before `introduced` or after `withdrawal_date` the
answer is `None`. It is unknown (`None`) where `introduced` is null. The
currency itself is the **current** one: the tree stores no currency history,
so `currency_at("DE", "1990-01-01")` returns `["EUR"]` although Germany used
the Deutsche Mark then. Callers who need the currency actually in force on a
past date must not rely on this query; a source for historical currencies is
a separate release.

**Semantics.** In order:

1. A malformed date → `None`. Unknown code → `None`.
2. **Active** entry (an active entry wins when a code is in both arrays, AI and
   SK):
   a. `introduced` null → `None` (source silent; 76 of 252 entries).
   b. `date < introduced` → `None`.
   c. Otherwise a copy of its current `currency_codes` (`None` if null).

== 25. Entries by special status and quarantined codes ==
exceptionally-reserved ['EU', 'UK']
user-assigned ['XK']
quarantined 27 ['AM', 'AZ', 'BA', 'BJ', 'BY', 'CZ', 'DJ', 'EE', 'ER', 'GE', 'KG', 'KI', 'KZ', 'LT', 'LV', 'MD', 'MM', 'RU', 'SH', 'SI', 'SK', 'TJ', 'TM', 'UA', 'UZ', 'VU', 'ZW']
quarantined and active: 27
source silent: 46
not officially assigned: ['EU', 'UK', 'XK']
withdrawn not sourced: 23
introduced snapshot meta (all): {'counts': {'active_from_1974_list': 161, 'active_from_data': 15, 'active_null_not_assigned': 3, 'active_null_quarantined': 27, 'active_null_source_silent': 46, 'withdrawn_null': 25}, 'default_date_1974_edition': '1974-09-15', 'generator': 'tools/build_introduced_snapshot.py', 'withdrawn_codes': ['AI', 'AN', 'BU', 'CS', 'CT', 'DD', 'DY', 'FQ', 'HV', 'JT', 'MI', 'NH', 'NQ', 'NT', 'PC', 'PZ', 'RH', 'SK', 'SU', 'TP', 'VD', 'WK', 'YD', 'YU', 'ZR'], 'review_by': '2027-10-28', 'shared_codes_active_and_withdrawn': ['AI', 'SK'], 'source': 'Wikipedia: ISO 3166-1 Changes (Edition/Newsletter table)', 'source_accessed': '2026-10-28', 'source_permalink': 'https://en.wikipedia.org/w/index.php?title=ISO_3166-1&oldid=1258392980'}
provisional EEA: ['BG', 'CY', 'CZ', 'EE', 'HU', 'LT', 'LV', 'MT', 'PL', 'RO', 'SI', 'SK'] | groups: [('2004-05-01', '2005-12-05'), ('2007-08-01', '2011-11-08')]

== 26. SQL dialect headers and CSV list serialisation ==
--- iso3166.sql
-- iso3166.sql — ANSI SQL-92 (portable)
-- Generated by tools/export_sql.py from iso3166.json.
-- Do not edit by hand. Regenerate with:
--   python3 tools/export_sql.py
-- Registry version: 1.12.1
-- Registry updated: 2026-10-31
--
-- Two tables:
--   countries            one row per entry (active + withdrawn)
--   country_currencies   join table (country_alpha_2, currency_code)
--
-- List fields (calling_codes, tlds, languages, borders, replaced_by)
--- iso3166.postgresql.sql
-- iso3166.postgresql.sql — PostgreSQL 12+
-- Generated by tools/export_sql.py from iso3166.json.
-- Do not edit by hand. Regenerate with:
--   python3 tools/export_sql.py
-- Registry version: 1.12.1
-- Registry updated: 2026-10-31
--
-- Two tables:
--   countries            one row per entry (active + withdrawn)
--   country_currencies   join table (country_alpha_2, currency_code)
--
-- List fields (calling_codes, tlds, languages, borders, replaced_by)
--- iso3166.mysql.sql
-- iso3166.mysql.sql — MySQL 8+ / MariaDB 10.4+
-- Generated by tools/export_sql.py from iso3166.json.
-- Do not edit by hand. Regenerate with:
--   python3 tools/export_sql.py
-- Registry version: 1.12.1
-- Registry updated: 2026-10-31
--
-- Two tables:
--   countries            one row per entry (active + withdrawn)
--   country_currencies   join table (country_alpha_2, currency_code)
--
-- List fields (calling_codes, tlds, languages, borders, replaced_by)
--- iso3166.sqlite.sql
-- iso3166.sqlite.sql — SQLite 3.37+
-- Generated by tools/export_sql.py from iso3166.json.
-- Do not edit by hand. Regenerate with:
--   python3 tools/export_sql.py
-- Registry version: 1.12.1
-- Registry updated: 2026-10-31
--
-- Two tables:
--   countries            one row per entry (active + withdrawn)
--   country_currencies   join table (country_alpha_2, currency_code)
--
-- List fields (calling_codes, tlds, languages, borders, replaced_by)
alpha_2	alpha_3	numeric	name	status	independent	official_name	region	subregion	intermediate_region	currency_codes	calling_codes	tlds	languages	borders	note	last_verified	withdrawal_date	replaced_by	introduced	eu_membership	eea_membership	eurozone_membership	customs_union
AD	AND	020	Andorra	officially-assigned	true	Principality of Andorra	Europe	Southern Europe		EUR	376	.ad	cat	ES|FR	"official_name source: https://www.iso.org/obp/ui/#iso:code:3166:AD
currency_codes source: https://www.iso.org/obp/ui/#iso:code:3166:AD
{'alpha_2': 'GB', 'currency_codes': 'GBP', 'borders': 'IE', 'introduced': '1974-09-15', 'eu_membership': '1973-01-01:2020-01-31', 'eea_membership': '1994-01-01:2020-12-31'}
{'borders': 'AT|BE|CH|CZ|DK|FR|LU|NL|PL', 'tlds': '.de'}
iso3166.csv:  61 6c 70
iso3166.excel.csv:  ef bb bf
iso3166.european.csv:  61 6c 70
iso3166.tsv:  61 6c 70

== 27. SQL runs (SQLite) ==
sqlite3 not installed
py sqlite3 countries: 277 country_currencies: 249
[('GB', '1973-01-01:2020-01-31')]
[('AI', 'officially-assigned'), ('AI', 'withdrawn'), ('SK', 'officially-assigned'), ('SK', 'withdrawn')]

== 28. Wrapper vs fixture: derived-case count ==
derived_queries.cases 129 enforced True

== 29. File counts excluding caches ==
189

```

## Appendix: the audit scripts

### /tmp/audit-readme.sh

```bash
#!/usr/bin/env bash
# audit-readme.sh: every number in the v1.12.1 README comes from here.
# Run from the repository root.
set -uo pipefail
cd "${1:-.}"

hr() { printf '\n== %s ==\n' "$1"; }

hr "1. Counts"
python3 - <<'PY'
import json
d = json.load(open("iso3166.json"))
a, w = d["countries"]["active"], d["countries"]["withdrawn"]
print("active", len(a), "withdrawn", len(w), "total", len(a) + len(w))
print("meta", d["meta"])
from collections import Counter
print("status", dict(Counter(e["status"] for e in a)))
print("region", dict(Counter(e["region"] for e in a)))
print("independent true", sum(1 for e in a if e["independent"] is True))
PY

hr "2. Fields and nulls (active)"
python3 - <<'PY'
import json
d = json.load(open("iso3166.json"))
a, w = d["countries"]["active"], d["countries"]["withdrawn"]
keys = sorted(a[0])
print("fields per active entry:", len(keys))
print("withdrawn fields:", len(sorted(w[0])), sorted(set(w[0]) ^ set(a[0])))
for k in keys:
    nulls = sum(1 for e in a if e[k] is None)
    empt = sum(1 for e in a if e[k] == [])
    print(f"  {k:22s} null={nulls:3d} empty_list={empt:3d}")
PY

hr "3. Queries and CLI"
echo "python derived queries (def in wrappers/python/iso3166/derived.py + clubs.py):"
grep -hE '^(    )?def [a-z]' wrappers/python/iso3166/derived.py wrappers/python/iso3166/clubs.py | grep -v '_' -c || true
grep -hE '^def [a-z]' wrappers/python/iso3166/derived.py wrappers/python/iso3166/clubs.py
echo "python registry methods:"
grep -E '^    def [a-z]' wrappers/python/iso3166/registry.py
echo "repo CLI subcommands (tools/iso3166_cli.py):"
grep -E "add_parser\(" tools/iso3166_cli.py
echo "packaged CLI subcommands (wrappers/python/iso3166/cli.py):"
grep -E "add_parser\(" wrappers/python/iso3166/cli.py

hr "4. Club membership counts"
python3 - <<'PY'
import json
d = json.load(open("iso3166.json"))
a = d["countries"]["active"]
for k in ("eu_membership", "eea_membership", "eurozone_membership", "customs_union"):
    print(k, "entries with >=1 period:", sum(1 for e in a if e[k]))
print("sample eu GB:", [e["eu_membership"] for e in a if e["alpha_2"] == "GB"])
print("sample eea NO:", [e["eea_membership"] for e in a if e["alpha_2"] == "NO"])
PY

hr "5. Exports"
ls iso3166.csv iso3166.european.csv iso3166.excel.csv iso3166.tsv iso3166.sql iso3166.postgresql.sql iso3166.mysql.sql iso3166.sqlite.sql iso3166.parquet countries_by_region.parquet
echo "flat export files (csv/tsv/sql/parquet, excl aggregated):"
ls iso3166*.csv iso3166*.tsv iso3166*.sql iso3166.parquet | wc -l
python3 - <<'PY'
import csv, pyarrow.parquet as pq
r = list(csv.reader(open("iso3166.csv", encoding="utf-8")))
print("csv columns", len(r[0]), "rows", len(r) - 1)
print(r[0])
t = pq.read_table("iso3166.parquet")
print("parquet columns", t.num_columns, "rows", t.num_rows)
print(t.schema.names)
print("parquet footer", {k.decode(): v.decode() for k, v in t.schema.metadata.items() if k.startswith(b"iso3166")})
a = pq.read_table("countries_by_region.parquet")
print("aggregated columns", a.num_columns, "rows", a.num_rows, a.schema.names)
PY
grep -c '^INSERT' iso3166.sql iso3166.postgresql.sql iso3166.mysql.sql iso3166.sqlite.sql
grep -n 'CREATE TABLE' iso3166.sql iso3166.postgresql.sql iso3166.mysql.sql iso3166.sqlite.sql
sed -n '/CREATE TABLE/,/);/p' iso3166.postgresql.sql | head -50

hr "6. Tests"
echo "root pytest:"
python3 -m pytest tests/ -q 2>&1 | tail -4
echo "wrapper python:"
(cd wrappers/python && python3 -m pytest tests -q 2>&1 | tail -4)
echo "wrapper js (node --test):"
(cd wrappers/javascript && node --test 2>&1 | grep -E "^# (tests|pass|fail)")
echo "wrapper rust #[test] count (static):"
grep -c '#\[test\]' wrappers/rust/tests/*.rs wrappers/rust/src/lib.rs
echo "wrapper go func Test count (static):"
grep -c '^func Test' wrappers/go/*_test.go
echo "cross-language fixture:"
python3 - <<'PY'
import json
f = json.load(open("tests/cross_language_consistency.json"))
print(type(f).__name__, list(f)[:10] if isinstance(f, dict) else len(f))
for k, v in (f.items() if isinstance(f, dict) else []):
    if isinstance(v, (list, dict)):
        print("  ", k, len(v))
PY
for t in node cargo go; do command -v $t >/dev/null && echo "$t: present" || echo "$t: MISSING (suite not run here)"; done

hr "7. Gate steps (release.sh)"
echo -n "grep -cE 'python3 tools/|bash tools/' scripts/release.sh = "
grep -cE 'python3 tools/|bash tools/' scripts/release.sh
echo "gate subshell lines (between 'set -e' and the closing paren):"
awk '/GATE_LOG=/{g=1} g&&/^        (python3|bash)/{n++; print n": "$0} /\) >"\$GATE_LOG"|GATE_LOG" 2>&1/{if(g)exit}' scripts/release.sh
grep -n 'GATE_LOG' scripts/release.sh | head

hr "8. CI"
ls .github/workflows
python3 - <<'PY'
import re
t = open(".github/workflows/validate.yml", encoding="utf-8").read()
jobs = t.split("\njobs:\n", 1)[1]
names = re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", jobs, re.M)
print("jobs:", len(names))
for n in names: print("  ", n)
print("on:", t.split("jobs:")[0][:400])
PY
echo "sanctions-freshness.yml present?"; ls .github/workflows/sanctions-freshness.yml 2>&1 | head -1

hr "9. Version sites"
python3 tools/check_version_consistency.py
echo "release.sh claims:"; grep -n 'version sites' scripts/release.sh
echo "version_axes.json sites:"; python3 -c "import json;print(len(json.load(open('tools/version_axes.json'))['sites']))"

hr "10. Snapshots and review_by"
ls tools/*snapshot*.json tools/wikipedia_dates.json
for f in tools/*snapshot.meta.json; do echo "--- $f"; python3 -c "
import json,sys
m=json.load(open('$f'))['meta']
print({k:v for k,v in m.items() if k not in ('null_reasons','provisional_application')})
"; done
python3 - <<'PY'
import json, glob
for f in sorted(glob.glob("tools/*snapshot.json")):
    d = json.load(open(f))
    m = d.get("meta") if isinstance(d, dict) else None
    print(f, "top-keys:", list(d)[:6] if isinstance(d, dict) else len(d), "meta.review_by:", (m or {}).get("review_by", "n/a"))
PY

hr "11. Introduced: dated / null / quarantined"
python3 - <<'PY'
import json
from collections import Counter
d = json.load(open("iso3166.json"))
a = d["countries"]["active"]
print("dated", sum(1 for e in a if e["introduced"]), "null", sum(1 for e in a if e["introduced"] is None))
m = json.load(open("tools/introduced_snapshot.meta.json"))
print("meta keys:", list(m), list(m.get("meta", {})))
s = json.load(open("tools/introduced_snapshot.json"))
print("snapshot top keys:", list(s)[:8])
mm = s.get("meta", {})
nr = mm.get("null_reasons") or m.get("meta", {}).get("null_reasons")
print("null_reasons type:", type(nr).__name__)
if isinstance(nr, dict):
    c = Counter()
    for k, v in nr.items():
        c[v if isinstance(v, str) else json.dumps(v)[:60]] += 1
    print("null_reasons total entries:", len(nr))
    for k, v in c.most_common(): print("  ", v, "x", k)
else:
    print(json.dumps(nr)[:1500])
PY

hr "12. EEA provisional"
python3 - <<'PY'
import json
s = json.load(open("tools/eea_membership_snapshot.json"))
print("top keys:", list(s))
mm = s.get("meta", {})
print("meta keys:", list(mm))
p = mm.get("provisional_application")
print("provisional_application:", json.dumps(p)[:1500])
PY

bash /tmp/audit-readme-part2.sh
bash /tmp/audit-readme-part3.sh

```

### /tmp/audit-readme-part2.sh

```bash
#!/usr/bin/env bash
# Part 2 of the README audit. Called from /tmp/audit-readme.sh. Run from repo root.
set -uo pipefail

hr() { printf '\n== %s ==\n' "$1"; }

hr "13. Gate count by the method tools/gen_state_doc.py uses"
python3 - <<'PY'
s = open("scripts/release.sh", encoding="utf-8").read()
gate = s.split("set -e\n", 1)[1].split(') > "$GATE_LOG"', 1)[0]
lines = [ln for ln in gate.splitlines() if ln.strip()]
print("gate lines (non-empty, STATE method):", len(lines))
print("of which pytest:", sum("pytest" in l for l in lines),
      "enrich *--check:", sum("enrich_" in l and "--check" in l for l in lines),
      "export_* --check:", sum("export_" in l and "--check" in l for l in lines))
for i, l in enumerate(lines, 1):
    print(f"{i:2d} {l.strip()}")
PY
echo "release steps:"; grep -nE '^step "' scripts/release.sh
echo "STATE.md says:"; grep -n "Release gate has" docs/STATE.md
python3 tools/check_state_doc.py --strict | tail -1

hr "14. SQL shape"
python3 - <<'PY'
import re
t = open("iso3166.postgresql.sql", encoding="utf-8").read()
m = re.search(r"CREATE TABLE countries \((.*?)\n\);", t, re.S)
cols = [l.split()[0] for l in m.group(1).splitlines() if l.strip() and not l.strip().startswith(("PRIMARY", "--"))]
print("countries columns:", len(cols))
print("INSERT INTO countries:", len(re.findall(r"^INSERT INTO countries", t, re.M)))
print("INSERT INTO country_currencies:", len(re.findall(r"^INSERT INTO country_currencies", t, re.M)))
PY
head -3 iso3166.sql | sed 's/^/header: /'

hr "15. Worked-example numbers (real queries through the Python wrapper)"
PYTHONPATH=wrappers/python python3 - <<'PY'
import json
from iso3166 import CountryRegistry
reg = CountryRegistry()
act = json.load(open("iso3166.json"))["countries"]["active"]
codes = [e["alpha_2"] for e in act]
for dt in ("1990-01-01", "2000-01-01", "2010-01-01", "2023-01-01"):
    eu = [c for c in codes if reg.is_eu_member_at(c, dt)]
    ez = [c for c in codes if reg.is_eurozone_member_at(c, dt)]
    print(dt, "EU", len(eu), "eurozone", len(ez))
print("is_eu now", sum(reg.is_eu(c) for c in codes), "is_eurozone now", sum(reg.is_eurozone(c) for c in codes))
eur = sorted(e["alpha_2"] for e in act if e["currency_codes"] and "EUR" in e["currency_codes"])
ez = sorted(c for c in codes if reg.is_eurozone(c))
print("currency_codes contains EUR:", len(eur))
print("  of which in the eurozone now:", len(set(eur) & set(ez)))
print("  EUR but not eurozone:", len(set(eur) - set(ez)), sorted(set(eur) - set(ez)))
print("GB: is_eu", reg.is_eu("GB"), "| is_eu_member_at 2010-01-01", reg.is_eu_member_at("GB", "2010-01-01"),
      "| 2020-01-31", reg.is_eu_member_at("GB", "2020-01-31"), "| 2020-02-01", reg.is_eu_member_at("GB", "2020-02-01"))
print("DE: introduced", [e["introduced"] for e in act if e["alpha_2"] == "DE"],
      "| currency_at 1990-01-01", reg.currency_at("DE", "1990-01-01"),
      "| is_active_on 1960-01-01", reg.is_active_on("DE", "1960-01-01"))
print("XK is_active_on 2000-01-01:", reg.is_active_on("XK", "2000-01-01"))
print("DD currency_at 1990-01-01:", reg.currency_at("DD", "1990-01-01"))
print("GR eurozone_membership:", [e["eurozone_membership"] for e in act if e["alpha_2"] == "GR"])
print("GR is_eurozone_member_at 2000-01-01:", reg.is_eurozone_member_at("GR", "2000-01-01"))
print("null-region entries:", [e["alpha_2"] for e in act if e["region"] is None])
print("introduced min/max:", min(e["introduced"] for e in act if e["introduced"]), max(e["introduced"] for e in act if e["introduced"]))
PY

hr "16. Aggregated table"
python3 - <<'PY'
import pyarrow.parquet as pq
df = pq.read_table("countries_by_region.parquet").to_pandas()
print("rows", len(df), "sum country_count", int(df.country_count.sum()), "sum independent_count", int(df.independent_count.sum()))
print("rows with null region:", int(df.region.isna().sum()), "| null region and null subregion:", int((df.region.isna() & df.subregion.isna()).sum()))
print("footer:", {k.decode(): v.decode() for k, v in pq.read_table("countries_by_region.parquet").schema.metadata.items() if k.startswith(b"iso3166")})
PY
sed -n 1,30p tools/export_aggregated.py | sed 's/^/agg: /'

hr "17. File counts"
echo -n "tracked files in the tree: "; find . -type f -not -path './.git/*' | wc -l
echo -n "verification reports: "; ls docs/v*-verification.md | wc -l
echo -n "ADR/decision docs: "; ls docs/decisions | wc -l
echo "pyarrow pin in requirements-dev.txt:"; grep -n pyarrow requirements-dev.txt
echo "constraints.txt present?"; ls constraints.txt 2>&1 | head -1
echo "docs/JOINS.md present?"; ls docs/JOINS.md 2>&1 | head -1
echo "tools/test_architecture.py present?"; ls tools/test_architecture.py 2>&1 | head -1
echo "tests/test_architecture.py present?"; ls tests/test_architecture.py
echo "examples/ present?"; ls examples 2>&1 | head -1
echo "ADR numbered 0007 present?"; ls docs/decisions | grep -c '^0007' || true

```

### /tmp/audit-readme-part3.sh

```bash
#!/usr/bin/env bash
# Part 3 of the README audit: reproducible command outputs quoted in the README.
# Called from /tmp/audit-readme.sh. Run from repo root. Needs pyarrow==26.0.0.
set -uo pipefail

hr() { printf '\n== %s ==\n' "$1"; }

hr "18. Drift gates (each must print OK)"
for c in "tools/export_sql.py" "tools/export_csv.py" "tools/export_parquet.py" "tools/export_aggregated.py" \
         "tools/sync_wrappers.py" "tools/gen_consistency_fixture.py" "tools/gen_withdrawn_doc.py" \
         "tools/enrich_club_memberships.py"; do
    printf '%-40s' "$c --check"; python3 $c --check 2>&1 | tail -1; echo "   rc=${PIPESTATUS[0]}"
done

hr "19. Validator and aux checks"
python3 tools/validate.py iso3166.json --strict-count --strict-independent 2>&1 | tail -3
python3 tools/check_docs_match_tree.py | grep -c '^OK'
python3 tools/check_mojibake.py 2>&1 | tail -1
python3 tools/check_snapshot_freshness.py 2>&1 | tail -2
python3 tools/check_registry_freshness.py 2>&1 | tail -1
python3 tools/check_release_claims.py 1.12.1 2>&1 | tail -1
echo "tools/check_* files:"; ls tools/check_*

hr "20. CLI exit codes and outputs (repo CLI via bin/iso3166)"
run() { printf '$ %s\n' "$*"; "$@"; echo "[exit $?]"; }
run bin/iso3166 is-eu DE
run bin/iso3166 is-eu GB
run bin/iso3166 is-eu XX
run bin/iso3166 is-eu-member-at GB 2010-01-01
run bin/iso3166 is-eu-member-at GB 2023-01-01
run bin/iso3166 is-active-on XK 2000-01-01
run bin/iso3166 is-active-on DE 1960-01-01
run bin/iso3166 currency-at DE 1990-01-01
run bin/iso3166 successors YU --raw alpha_2
run bin/iso3166 introduced DE
run bin/iso3166 validate US FR DE
run bin/iso3166 --registry /nonexistent.json info
run bin/iso3166 is-eu-member-at GB 2010-13-45
echo "--- --raw divergence (repo CLI vs packaged CLI), one null list field"
python3 tools/iso3166_cli.py list --region Oceania --raw tlds | wc -l
PYTHONPATH=wrappers/python python3 -m iso3166.cli list --region Oceania --raw tlds | wc -l
python3 tools/iso3166_cli.py list --region Oceania --raw name | wc -l

hr "21. CI jobs and what each runs"
python3 - <<'PY'
import re
t = open(".github/workflows/validate.yml", encoding="utf-8").read()
jobs = t.split("\njobs:\n", 1)[1]
parts = re.split(r"^  ([A-Za-z0-9_-]+):\s*$", jobs, flags=re.M)
for name, body in zip(parts[1::2], parts[2::2]):
    runs = re.findall(r"^\s+(?:- )?run: (.+)$", body, re.M)
    runs += re.findall(r"^\s{10,}((?:python3|bash|node|cargo|go|npm|pytest)\b.+)$", body, re.M)
    runs = [r for r in runs if not r.startswith("|")]
    needs = re.findall(r"needs: (.+)", body)
    print(f"{name}: needs={needs or '-'}")
    for r in dict.fromkeys(runs): print("    ", r[:110])
PY

hr "22. Release script facts"
sed -n 1,30p scripts/release.sh
echo "--- preflight / tag / github release / verification doc lines"
grep -nE 'die "|gh release|git tag|git push|verification\.md|CI_START_TIMEOUT|TIMEOUT' scripts/release.sh | head -50

hr "23. Cross-language script"
sed -n 1,40p tools/check_cross_language.sh
grep -rn -i "anchor" --include=*.md --include=*.py --include=*.js --include=*.sh . 2>/dev/null | grep -v '^./docs/v' | head -5

hr "24. Query 9 and Query 7 conventions"
sed -n '/^## Query 9/,/^## Query 10/p' docs/QUERIES.md | sed -n 1,60p
sed -n '/^## Query 7/,/^## Query 8/p' docs/QUERIES.md | sed -n 1,40p

hr "25. Entries by special status and quarantined codes"
python3 - <<'PY'
import json
d = json.load(open("iso3166.json"))["countries"]["active"]
for st in ("exceptionally-reserved", "user-assigned"):
    print(st, [e["alpha_2"] for e in d if e["status"] == st])
nr = json.load(open("tools/introduced_snapshot.json"))["meta"]["null_reasons"]
act = {e["alpha_2"] for e in d}
q = sorted(k for k, v in nr.items() if v.startswith("quarantined"))
print("quarantined", len(q), q)
print("quarantined and active:", len([k for k in q if k in act]))
print("source silent:", sorted(k for k, v in nr.items() if v == "source silent" and k in act).__len__())
print("not officially assigned:", sorted(k for k, v in nr.items() if v.startswith("not officially")))
print("withdrawn not sourced:", len([k for k, v in nr.items() if v.startswith("withdrawn")]))
print("introduced snapshot meta (all):", {k: v for k, v in json.load(open("tools/introduced_snapshot.json"))["meta"].items() if k != "null_reasons"})
e = json.load(open("tools/eea_membership_snapshot.json"))["meta"]["provisional_application"]
print("provisional EEA:", sorted(e), "| groups:", sorted({(v["from"], v["to"]) for v in e.values()}))
PY

hr "26. SQL dialect headers and CSV list serialisation"
for f in iso3166.sql iso3166.postgresql.sql iso3166.mysql.sql iso3166.sqlite.sql; do echo "--- $f"; sed -n 1,12p $f | cut -c1-110; done
head -c 700 iso3166.tsv | head -3 | cut -c1-300
python3 - <<'PY'
import csv
r = list(csv.DictReader(open("iso3166.csv", encoding="utf-8")))
gb = [x for x in r if x["alpha_2"] == "GB"][0]
print({k: gb[k] for k in ("alpha_2", "currency_codes", "borders", "introduced", "eu_membership", "eea_membership")})
de = [x for x in r if x["alpha_2"] == "DE"][0]
print({k: de[k] for k in ("borders", "tlds")})
PY
for f in iso3166.csv iso3166.excel.csv iso3166.european.csv iso3166.tsv; do printf '%s: ' $f; head -c 3 $f | od -An -tx1; done

hr "27. SQL runs (SQLite)"
if command -v sqlite3 >/dev/null; then
  rm -f /tmp/r.db; sqlite3 /tmp/r.db < iso3166.sqlite.sql && sqlite3 /tmp/r.db "SELECT count(*) FROM countries; SELECT count(*) FROM country_currencies; SELECT alpha_2, eu_membership FROM countries WHERE alpha_2='GB'; SELECT alpha_2,status FROM countries WHERE alpha_2 IN ('SK','AI') ORDER BY 1,2;"
else echo "sqlite3 not installed"; fi
python3 - <<'PY'
import sqlite3
c = sqlite3.connect(":memory:")
c.executescript(open("iso3166.sqlite.sql", encoding="utf-8").read())
print("py sqlite3 countries:", c.execute("select count(*) from countries").fetchone()[0],
      "country_currencies:", c.execute("select count(*) from country_currencies").fetchone()[0])
print(c.execute("select alpha_2, eu_membership from countries where alpha_2='GB'").fetchall())
print(c.execute("select alpha_2,status from countries where alpha_2 in ('SK','AI') order by 1,2").fetchall())
PY

hr "28. Wrapper vs fixture: derived-case count"
python3 -c "
import json; f=json.load(open('tests/cross_language_consistency.json')); print('derived_queries.cases', len(f['derived_queries']['cases']), 'enforced', f['derived_queries']['enforced'])"
hr "29. File counts excluding caches"
find . -type f -not -path './.git/*' -not -path '*/__pycache__/*' -not -path '*/.pytest_cache/*' -not -path '*/node_modules/*' -not -path '*/target/*' | wc -l

```

### /tmp/worked_example.py

```python
"""Four dates, one registry file: which countries were in which club?

Run from the repository root:  python3 /tmp/worked_example.py
Needs: pip install duckdb pyarrow
"""
import duckdb

con = duckdb.connect()
con.execute("CREATE VIEW c AS SELECT * FROM 'iso3166.parquet' WHERE status <> 'withdrawn'")

# A club cell is one string: 'from:to|from:to', an empty end means "still a member".
con.execute("""
CREATE MACRO member_at(cell, d) AS (
    coalesce(list_bool_or(list_transform(
        string_split(cell, '|'),
        lambda r: split_part(r, ':', 1) <= d
         AND (split_part(r, ':', 2) = '' OR split_part(r, ':', 2) >= d)
    )), false)
)
""")

print("Q1-Q3: who was in the EU, and in the eurozone, on four dates?")
for d in ("1990-01-01", "2000-01-01", "2010-01-01", "2023-01-01"):
    eu, ez = con.execute(
        "SELECT count(*) FILTER (WHERE member_at(eu_membership, ?)),"
        "       count(*) FILTER (WHERE member_at(eurozone_membership, ?)) FROM c",
        [d, d],
    ).fetchone()
    print(f"  {d}  EU={eu:2d}  eurozone={ez:2d}")

print("\nQ4: the current alias against the dated query, for GB")
for d in ("2010-01-01", "2020-01-31", "2020-02-01"):
    (n,) = con.execute(
        "SELECT count(*) FROM c WHERE alpha_2='GB' AND member_at(eu_membership, ?)", [d]
    ).fetchone()
    print(f"  GB in the EU on {d}: {bool(n)}")
(cur,) = con.execute(
    "SELECT count(*) FROM c WHERE alpha_2='GB' AND member_at(eu_membership, '2026-10-31')"
).fetchone()
print(f"  GB in the EU today:  {bool(cur)}   (is_eu('GB') is the same current-status answer)")

print("\nQ5: which countries list EUR as a currency, and how many are in the eurozone today?")
eur, ez_now, only = con.execute("""
SELECT count(*) FILTER (WHERE list_contains(currency_codes, 'EUR')),
       count(*) FILTER (WHERE list_contains(currency_codes, 'EUR')
                          AND member_at(eurozone_membership, '2026-10-31')),
       string_agg(alpha_2, ' ' ORDER BY alpha_2) FILTER (WHERE list_contains(currency_codes, 'EUR')
                          AND NOT member_at(eurozone_membership, '2026-10-31'))
FROM c
""").fetchone()
print(f"  EUR in currency_codes: {eur}; eurozone members: {ez_now}; EUR without membership: {eur - ez_now}")
print(f"  those {eur - ez_now}: {only}")

```

### /tmp/gen_tree.py

Renders the Section 17 tree from the tracked-file list and fails if any file lacks a comment. Its comment table is not reproduced here; the output is the tree in the README.
