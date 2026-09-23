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

(Record the entries that were corrected, if any. If none, write
"The Factbook's lists were complete for every entry where they
existed. No second source was needed.")
