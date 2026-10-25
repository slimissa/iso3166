# Audit notes

This file holds the receipts: for each rule in
[`RELEASE_PATTERN.md`](./RELEASE_PATTERN.md) and each gap in
[`AUDIT.md`](./AUDIT.md), the specific failure that motivated it.

It is append-only. An entry is never edited after it is written; a
correction is a new entry. Facts about this repository trace to
`CHANGELOG.md` and the `docs/vX.Y.Z-verification.md` reports. Facts about
other registries (F31, and ISO 4217 in A11) come from cross-registry
coordination and cannot be checked from this repository.

### Rule 16 — Never reset VERSION to re-run release.sh

v1.7.2's first release attempt (`86b799f`) was cancelled. For the second
attempt `VERSION` was reset to 1.7.1 in `a269aaf` while every other
version site stayed at 1.7.2, so CI on HEAD went red and the release was
blocked. The reset was reverted in `1c31328` and the tag was created by
hand (`docs/v1.7.2-verification.md`).

### Rule 17 — Never Ctrl+C during the CI wait in step 4

v1.7.2's first release attempt (`86b799f`) was cancelled when the CI wait
was interrupted. That left `main` holding an untagged release commit and
started the partial-release recovery described in
`docs/v1.7.2-verification.md`.

### Rule 18 — CI queueing latency: CI_START_TIMEOUT of at least 180 seconds

v1.7.3's release commit (`845807a`) was pushed by `release.sh`, but the
60-second CI-start timeout fired before GitHub registered the run, which
started at about 90 seconds. The tag was created by hand once CI was
green. v1.7.4 raised `CI_START_TIMEOUT` from 60 to 180 seconds.

### Rule 19 — Split releases by decision dependency

v1.7.2 shipped the `enrich_field.py` citation fix and the note migration,
which needed no data decision, and deferred the `independent` correction.
v1.7.3 then carried that data, harvested from 249 manually saved ISO OBP
pages. The rule was codified in v1.7.4 from these two recoveries.

### Rule 20 — Bundle layout guard

v1.7.3, v1.8.0, and v1.8.1 all shipped with `commit-messages/*.txt`
flat in the bundle root instead of in `commit-messages/`. The
delivery pipeline flattens subdirectories. `apply.sh`'s layout check
caught each case and refused before applying anything. v1.8.2's
`apply.sh` self-heals (moves the files into `commit-messages/`)
rather than refusing, because the layout is a delivery artifact,
not a content defect.

### Rule 21 — Bundle delivery format

The three flat-layout incidents were delivery-mechanism failures,
not bundle-content failures. Delivering as `vX.Y.Z-patches.tar.gz`
preserves subdirectory structure through extraction; delivering as
loose files does not. v1.8.2 is the first bundle delivered as a
`.tar.gz`.

### Rule 22 — Preflight "CI running" is normal

v1.8.1 hit three consecutive `release.sh` refusals within 10 seconds
of pushing. The script correctly saw `CI on HEAD is still running`
each time. The script is not stuck; CI takes 3-4 minutes (Rust test
dominates). Attempting to retry or cancel interrupts a working run
and makes the wait longer. Use `gh run watch` and wait for green.

### A10 — Three-file split: rules, audit, receipts

From v1.6.5 through v1.6.8 the CHANGELOG records repeated additions to
`RELEASE_PATTERN.md` (rule 6b, the attribution convention, the
`[Unreleased]` convention, reviewer-block updates). By v1.8.0 the file
mixed rules, incident narratives and tool state, and the tool state had
drifted: its opening list gives ISO 3166 eight version sites and its
closing section says eleven. v1.8.1 splits it into `RELEASE_PATTERN.md`,
`AUDIT.md` and this file.

### A11 — CURATED vs AGGREGATED checks

v1.7.0 added the AGGREGATED layer and the CURATED (byte) versus
AGGREGATED (content) distinction to the pattern. In this repository
`tools/export_parquet.py --check` compares bytes (`read_bytes()`), but the
module docstring still says it compares "logical content, not bytes".
A11 fixes which reading is correct (CURATED compares exactly), so the
docstring is the error; v1.8.1 changes no code and does not correct it.

### A12 — Verify the tag message before pushing the tag

In v1.7.0, `release.sh` was interrupted during tag-message verification by
a trailing-newline false positive, and the GitHub release was created by
hand. v1.7.1 adopted ISO 4217's A12: verify the tag message before push
and delete the local tag on any verification failure. The v1.7.2 and
v1.7.3 tags were created by hand for other reasons, and the v1.7.1, v1.7.4
and v1.8.0 reports record CI green before the tag but not the tag-message
check, so this repository holds no recorded confirmation of it.

### F31 — Upstream-drift detection

ISO 4217 held its vendored copy of this registry at v1.6.9 through
v1.8.0, a gap of six releases (v1.7.0 to v1.7.4, then v1.8.0). Its
`review_by` check is calendar-based, not release-based, so it did not flag
the gap. Upstream-drift detection is deferred to v1.9.1.

### Rule 23 — Preflight refuses any non-success CI conclusion

The CI check in the `release.sh` preflight was added in v1.7.2, after a
run was cancelled when the release commit pushed, but it matched only
`failure`, so `cancelled`, `timed_out` and `startup_failure` still
passed. Found in v1.8.2 verification by reading the script, and
reproduced in v1.8.3: a `--dry-run` in a scratch repo with a fake `gh`
printed "CI on HEAD is green" for a `cancelled` run. Step 4 already
refused non-success conclusions, so no tag could be created on unverified
code; the cost was a release commit pushed to `main` first.

### Rule 24 — State docs are generated and verified

`docs/PROVENANCE.md` still described the known gaps in v1.0.0 while the
registry shipped v1.8.x. `docs/ENRICHMENT.md` said "four enriched fields"
while the registry carried more. Neither was checked by any tool.
STATE.md plus `check_state_doc.py` (v1.9.0) close the class: a single
state doc that is machine-verified on every push.

### Rule 25 — Registry freshness is a gate check, not a CI check

v1.9.0 shipped `check_registry_freshness.py` but wired it into neither CI
nor the release gate, so a registry whose `last_verified` values had aged
past 365 days would still have released. v1.9.1 adds it to the gate only: a
CI check would turn every push red on day 366 with no data change behind it.

### Rule 26 — Every derived artifact is regenerated by release.sh step 2

v1.9.0's AI subregion fix changed `countries_by_region.parquet`, which
`release.sh` step 2 did not regenerate; the file was regenerated by hand.
Only the gate's `export_aggregated.py --check` would have caught a
forgotten regeneration, and only after the release was already under way.
The same gap applied to `docs/STATE.md`. v1.9.1 regenerates both in step 2.

### Doc truth 1 — README gate count

The README said "Fourteen checks run in sequence" and listed eleven
groups, while the gate subshell in `scripts/release.sh` runs 26. The count
had been written once and never checked; v1.9.2 corrects it and
`check_docs_match_tree.py` compares it on every push.

### Doc truth 2 — ENRICHMENT.md field count

`docs/ENRICHMENT.md` said "four enriched fields" and its tables listed
four, while it documents eight sections and `check-fields` runs eight
checks. This is the same drift Rule 24's receipt records; v1.9.2 fixes the
text and the checker derives the count from `tools/enrich_field.py`.

### Doc truth 3 — PROVENANCE.md was a v1.0.0 snapshot

`docs/PROVENANCE.md` marked populated fields "(future)", named the wrong
source for `languages`, omitted `official_name` and `borders`, and set an
18-month audit threshold while the freshness gate enforces 365 days.
v1.9.2 keeps the v1.0.0 sections as history and adds a current-as-of
version that the checker ties to VERSION.

### Doc truth 4 — CONTRIBUTING.md CI job list

`CONTRIBUTING.md` said every push runs 14 jobs; `validate.yml` had 20.
Six jobs were unlisted. v1.9.2 lists them all and the checker requires
every job id to be named.

### Doc truth 5 — Decisions drifted without a record

D2's approximate counts, D3's field count and D7's five version sites no
longer match the tree, and nothing recorded it. `docs/decisions/
v1.9.2-amendments.md` records the divergence and the release where the
repository evidences it; it does not edit the original decisions.
