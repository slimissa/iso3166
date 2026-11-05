# Cross-registry contract

**Status: proposed** by ISO 3166 on 2026-11-04. The other registries have not
adopted it. It binds a registry when that registry's maintainer adopts it;
[`RELEASE_PATTERN.md`](./RELEASE_PATTERN.md) is the precedent (adopted after
review by two registries). The proposal comes from the fourth closure audit,
which compared this registry with its consumers by hand.

**Scope.** Six registries: ISO 3166, ISO 4217, ISO 10383, Exchange Calendar,
Corporate Actions, Asset Identifiers. A *provider* owns a join key. A
*consumer* vendors it or references it. A registry can be both: this one
vendors a snapshot of ISO 4217 and is vendored by three registries.

## The nine rules

1. **Provider publishes a version.** `VERSION`, `meta.version` in the data
   file, an annotated git tag `vX.Y.Z`, and the tagged data file at a stable
   path. The provider's `docs/JOINS.md` lists every consumer, the join key,
   and the fields each consumer reads (for ISO 3166:
   [`JOINS.md`](./JOINS.md)).
2. **Consumer records what it vendored.** Next to every vendored file, a
   `*.meta.json` with `source`, `source_version`, `vendored_from` (the tag
   URL), `snapshot_sha256`, `vendored_at` and `review_by`. The file is
   byte-identical to the tag, or the meta names the generator and says it is
   derived.
3. **Consumer checks reproduction (blocking, offline).** The vendored file's
   SHA-256 equals the hash in its meta, and a derived file is regenerated and
   compared.
4. **Consumer checks upstream (advisory, scheduled).** Compare `source_version`
   with the highest stable provider tag and report the gap in minor versions.
   It never blocks a release by itself. It blocks only when the provider's
   *consumed* fields differ (the code set, `name`, `region`, `subregion`,
   currency pairs).
5. **Provider states consumer impact.** Every CHANGELOG release section has a
   `Consumer impact:` line naming the consumed fields it changed, or `none`.
6. **Join semantics are fixed once, in the provider's JOINS.md.** Join on the
   **active** list only (`SK` and `AI` also appear withdrawn); `ZZ` is a MIC
   value, not a country; names compare byte for byte.
7. **Disagreements are recorded once.** A reviewed allow-list in the consumer
   repository (ISO 4217's model), and every `fix-in-<provider>` entry filed as
   an issue in the provider's repository within one release of the entry.
8. **Evidence is per run.** Release evidence uses unique temporary paths (a
   nested run must not share a file with the run that started it), and the
   verification report records every gate command with its exit code.
9. **The audit method is one script.** Run from the provider repository, it
   reads each consumer's meta, hashes the vendored file, runs the joins, and
   prints the tables of a cross-registry audit. Rules 2 to 4 make that a loop
   over files, not a manual review.

## Where this registry stands on 2026-11-04

| Rule | ISO 3166 as provider | ISO 3166 as consumer of ISO 4217 |
|------|----------------------|----------------------------------|
| 1 | yes: `VERSION`, `meta.version`, annotated tags, [`JOINS.md`](./JOINS.md) (new in v1.12.4) | n/a |
| 2 | n/a | partly: `source_repo` and `source_version` since v1.12.4; no `vendored_from`, no `snapshot_sha256`, no `vendored_at` |
| 3 | n/a | no: `check_iso4217_snapshot.py` checks well-formedness, not a hash |
| 4 | `check_consumers_current.py` for its consumers (advisory, network, run by hand) | `check_snapshot_freshness.py --check-upstream` (opt-in); nothing schedules either |
| 5 | from v1.12.4 | n/a |
| 6 | yes: [`JOINS.md`](./JOINS.md) | n/a |
| 7 | the `GS` request is recorded, **not filed** ([ADR](./decisions/cross-registry-edges.md)) | n/a |
| 8 | yes from v1.12.4 (per-run temp directory, full record in the report) | n/a |
| 9 | **no.** `check_consumers_current.py` and `--check-upstream` cover rule 4 only; the joins of the fourth audit were run by hand | n/a |

The other registries' standing is not recorded here, because only each
maintainer can say it. What the fourth audit found in their public files:
ISO 4217 records `source_version`, `vendored_from`, `snapshot_sha256`,
`vendored_at` and `review_by`, and has an opt-in upstream check; ISO 10383
records `source_version`, `vendored_from`, `vendored_at` and `review_by` (no
hash) and has a drift check (`check_iso3166_current.py`); Exchange Calendar
records `source`, `source_version` and `review_by` (no `vendored_from`, hash or
`vendored_at`).

## Changing this file

A rule changes only when every registry that has adopted it agrees. Until
then this file describes what ISO 3166 does and what it asks of the others.
