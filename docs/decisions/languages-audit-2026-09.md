# Languages audit — 2026-09

## Context

The `languages` field was populated in v1.3.0 from the CIA World
Factbook. This audit classifies every officially-assigned entry's
language list and identifies entries where the Factbook's list may be
incomplete.

## Classification

Regenerate with `python3 tools/audit_languages.py`.

| Class | Action |
|-------|--------|
| Empty | AQ only; no permanent population |
| Single-language | Reviewed; corrections applied where the Factbook lists additional languages |
| Multi-language | No action |

## Second source

Where the Factbook's list was demonstrably incomplete, the second
source is the UNESCO Institute for Statistics (`uis.unesco.org`). UIS
is a government statistical service, which fits the expanded source
rule from `docs/decisions/languages-borders-sources.md`.

## Corrections

Four entries were corrected: `MT`, `IE`, `CY` and `PR`. For each, the
Factbook listed only the official language, and v1.4.0 added the other
language (CHANGELOG, `[1.4.0]`). The registry holds:

| Entry | `languages` |
|-------|-------------|
| `CY` | `ell`, `tur` |
| `IE` | `eng`, `gle` |
| `MT` | `eng`, `mlt` |
| `PR` | `eng`, `spa` |

The CHANGELOG does not name the source of the added languages, and the
`note` of each of the four entries cites the Factbook page for
`languages`, not UIS. No correction is recorded as coming from UIS, so the
second-source rule above has no recorded use.
