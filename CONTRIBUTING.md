# Contributing

Thanks for helping improve the ISO 3166 registry.

## Before you start

For anything more than a data correction, **open an issue first**. The
registry is small and deliberate; large PRs that arrive unannounced
are hard to review.

## Data corrections

1. Edit `iso3166.json`.
2. Run the validator and resolve any errors:

   ```bash
   python3 tools/validate.py iso3166.json --strict-count
   ```

3. Cite a first-party source in the commit message: ISO 3166 online
   browsing platform, the UN M49 overview export, IANA's ccTLD
   registry, or the ITU's E.164 list.
4. Submit a PR.

### What counts as a first-party source

- **ISO 3166-1** — `https://www.iso.org/iso-3166-country-codes.html`
  and `https://www.iso.org/obp/ui/#search/code/`
- **UN M49** — `https://unstats.un.org/unsd/methodology/m49/`
- **IANA ccTLDs** — `https://www.iana.org/domains/root/db`
- **ITU-T E.164** — `https://www.itu.int/`
- **ISO 3166-3** — the standard itself

Third-party aggregators (Wikipedia, countrycode.org, blog posts, CSVs
from unrelated projects) are **not acceptable** as the origin of a
field. If a value can't be traced to a first-party source, it stays
`null`. An empty field is honest; a wrong field is not.

## Adding a new code

When ISO assigns a new alpha-2 code:

1. Add the entry to the `active` array in `iso3166.json`.

2. Update `tools/parse_source.py`:

   ```bash
   python3 tools/parse_source.py --bootstrap iso3166.json > /tmp/fresh.txt
   ```

   Diff `/tmp/fresh.txt` against the frozen sets in `parse_source.py`
   and paste the updated sets in.

3. Regenerate every derived artifact:

   ```bash
   python3 tools/export_sql.py
   python3 tools/export_csv.py
   python3 tools/export_parquet.py
   python3 tools/sync_wrappers.py
   python3 tools/gen_consistency_fixture.py
   ```

4. Bump `VERSION` and `meta.version` (minor bump).

5. Add a `CHANGELOG.md` entry citing the ISO amendment.

6. Run the full check:

   ```bash
   python3 tools/check_version_consistency.py
   python3 tools/validate.py iso3166.json --strict-count
   bash tools/check_cross_language.sh US
   ```

## Removing or withdrawing a code

Do not simply delete an entry. ISO 3166 withdrawals move a code from
`active` to `withdrawn` with a `withdrawal_date` and, where applicable,
a `replaced_by` list. See
[`docs/decisions/withdrawn-codes.md`](./docs/decisions/withdrawn-codes.md).

## Wrapper contributions

Each wrapper has its own test suite and reads the shared fixture at
`tests/cross_language_consistency.json`. Adding a test case means
editing the fixture, not the wrapper's tests. See the fixture's
`_comment` field.

After changing any wrapper:

```bash
bash tools/check_cross_language.sh US GB JP TW XK UK
```

must exit 0.

## Tooling

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` lists `jsonschema` (for the validator) and
`pyarrow` (for the Parquet exporter). Neither is a runtime dependency
of the registry data.

## CI

Every push to `main` runs 14 jobs:

- `validate-json` — six-layer validator + ground-truth verify, on a
  matrix of Ubuntu × Python versions.
- `check-version-consistency` — `VERSION` vs. `meta.version` vs.
  `CHANGELOG` vs. Parquet footer.
- `check-iso4217-snapshot` — the ISO 4217 snapshot parses, has no
  duplicates, and has consistent meta counts.
- `check-wrapper-sync` — bundled JSONs and the fixture are fresh.
- `check-sql-export`, `check-csv-export`, `check-parquet-export` —
  derived artifacts match a fresh generation.
- `check-cli` — exit codes 0/1/2/3; `--csv` byte-identical to
  `iso3166.csv`.
- `check-docs` — README counts match `iso3166.json`.
- `cross-language` — all four wrappers agree.
- `wrapper-python`, `wrapper-javascript`, `wrapper-go`, `wrapper-rust`
  — language-specific test suites.

A red job names the failing command and the exact assertion. Every
command the CI runs is also runnable locally.

## No tag before CI is green

A tag on a red commit is a lie in the history books. Before tagging
any release:

1. The full CI run for the exact commit being tagged must be green.
2. `python3 tools/check_version_consistency.py` must exit 0.
3. `python3 tools/validate.py iso3166.json --strict-count` must exit 0.
4. `bash tools/check_cross_language.sh US` must exit 0.

If any of those fails, fix it, push, wait for green, and only then tag.

## Commit messages

Format:

```text
<type>: <short summary>

<optional body>
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.

Example:

```text
fix: rename numeric to numeric_code in SQL exports

numeric is a reserved word in several SQL dialects. The JSON field
keeps its name; the SQL column is renamed at export time.

Closes #42.
```

## License

By contributing, you agree that your contributions will be licensed
under the Apache 2.0 license that covers the repository.

## Patch scripts

Inline Python patch scripts are used to modify tools when a direct edit
would be error-prone. Two rules:

1. **Wrap the patch in `set -e`.** Without it, an anchor mismatch raises
   `SystemExit` but the surrounding shell continues to the next command.
   Several v1.3.0 fixes were silently skipped this way.
2. **Print the target before aborting.** A failed anchor should print
   the first 80 characters of the text it looked for, so the reviewer
   can see what's actually in the file.

Example:

    set -e
    python3 - <<'PYEOF'
    from pathlib import Path
    p = Path("tools/some_tool.py")
    src = p.read_text(encoding="utf-8")
    old = "..."
    if old not in src:
        print(f"target not found; first 80 chars: {old[:80]!r}")
        raise SystemExit(1)
    p.write_text(src.replace(old, "new", 1), encoding="utf-8")
    print("patched")
    PYEOF

If the patch script prints "target not found", stop and paste the
message back to the reviewer before running the next command.

## Tag only after CI completes

`gh run watch` returns when a run completes. A `gh run list` query
that shows `status: in_progress` is not a green light. Confirm:

    STATUS=$(gh run list --workflow=validate.yml --limit 1 \
        --json status,conclusion --jq '.[0] | "\(.status) \(.conclusion)"')
    [ "$STATUS" = "completed success" ] || echo "not ready: $STATUS"

Tag only when `STATUS` reads `completed success`.

