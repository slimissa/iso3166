# Release pattern

**Status:** Reviewed.

Reviewed-by:
- `slimissa/iso4217` — 2026-09-27
- `slimissa/exchange-calendar` — 2026-09-27

The `release.sh` script exists in three registries. Each was written
independently. They share eight invariants and diverge on one step.
This document captures both.

- ISO 4217 (`scripts/release.sh`, two axes, eleven version sites)
- ISO 3166 (`scripts/release.sh`, one axis, eight version sites)
- Exchange Calendar (`scripts/release.sh`, three sites, two workflows)

---

## The essential eight

Every `release.sh` refuses on the same eight conditions, in this
order. The order matters: cheap checks first.

### 1. Refuse on unclean state

The working tree is clean, the current branch is `main`, and `HEAD`
matches `origin/main`. All three, or the release does not start.

Why: a release built from an uncommitted state is a release whose
contents can't be reproduced. A release from a non-`main` branch is a
release nobody else has. A release from a stale `main` is a release
that will conflict with the next push.

### 2. Refuse on version collision or missing CHANGELOG

`VERSION` differs from the target, and `CHANGELOG.md` has a
`## [<target>]` section. Both.

Why: the version collision check is a no-op guard against re-running
a release that already completed. The CHANGELOG check ensures the
release has a description before it has a tag.

### 3. Bump all version sites, then verify

Every site that carries the version is bumped. After the bumps, all
sites are re-read and compared. Any mismatch stops the release.

Why: a partial bump is worse than no bump. It ships a registry whose
own metadata disagrees with itself.

The site list is repo-specific. See `axes.json` for the ISO 4217
and ISO 3166 shapes.

### 4. Post-rebuild verify

Two shapes. Pick the one that matches your generator count.

**Single generator.** One artifact from one generator
(Exchange Calendar: `calendar.json` from `tools/build.py`).
`build → re-read → compare`. Three lines, immediate, points at
the build script if it fails.

**Multiple generators.** Nine artifacts from four generators
(ISO 4217, ISO 3166). `regenerate all → gate → consistency
check`. The gate centralizes the comparison. The failure message
names the stale artifact.

Rule: state which shape your repo uses, and why.

### 5. Gate before commit

Every check that CI runs also runs locally, before the release
commit is created. Any non-zero exit stops the release before
anything is committed or pushed.

Why: a release that fails CI is a release that needs a revert
commit. A release that fails the gate locally is a release that
was never created.

### 6. Poll every workflow

After the release commit is pushed, poll every workflow that runs
on push to the release branch. Wait for all of them to complete.
`in_progress`, `queued`, and `pending` are not green. Only
`completed success` is.

Schedule-driven workflows (`monitor`, `fetch`, `refresh`) are
deliberately excluded. The exclusion list is enumerated by hand
and must be checked against the workflows directory before every
release; a new per-push workflow added silently to the repo would
otherwise be missed.

In a repo with multiple per-push workflows, `gh run list` returns
multiple runs per SHA. Querying only the first (`head -1`) silently
misses the others. Query all runs for the SHA and assert every one
is `completed success`.

Reference implementation:

- ISO 4217, `scripts/release.sh` at commit `1f38fb4` — the
  `poll_ci` function reads every run for the SHA and asserts
  each reads `completed success`.
- ISO 3166, `scripts/release.sh` — same shape, adopted from
  ISO 4217's fix.
- The workflow-coverage check is `check_workflows_covered`,
  present in both scripts. It enumerates `.github/workflows/`,
  excludes schedule-driven files by name prefix, and fails if
  any remaining workflow isn't in the declared poll list.

Why: a tag that lands on a green commit whose second workflow is
still running is a tag that hides a failure. v1.3.0 in ISO 3166 is
the historical example.

### 7. Tag only on green

The tag is created only after all polled workflows report
`completed success`. No manual override, no force. The tag message
is written to a file first, read back, then passed to `git tag -F`.

Why: this is the rule that the release process exists to enforce.
`CONTRIBUTING.md` says "don't tag on red"; the script says "you
cannot tag on red."

### 8. Immutable tags

**This is policy, not mechanism.** The script refuses to re-run on
an already-tagged version (invariant 7). Nothing in the code
prevents a manual `git tag -f`. The rule holds because operators
follow it, not because the tooling enforces it.

Once a tag is pushed, the code it points at is what shipped,
whether or not the CHANGELOG reflects it accurately.

Reconciliation of a tag that shipped with a known issue is a future
CHANGELOG entry acknowledging the divergence, not a force-push, not
a moved tag, not a rewritten release.

The tag is a claim about what shipped. The CHANGELOG is a claim
about what was known when. When they disagree, the CHANGELOG is
corrected and the tag is left alone.

---

## Two shapes of step 4

### Single generator

build
re-read the version from the artifact
compare to VERSION
text


Three lines. Immediate. The failure message names the file.

Exchange Calendar uses this shape: `tools/build.py` writes
`calendar.json`, then the script re-reads `meta.version` and
compares.

### Multiple generators

regenerate every artifact
run the gate (which includes a version-consistency check)
the check compares every artifact's version to VERSION

The gate centralizes the comparison. The failure message names
which artifact is stale, but the failure point is the gate, not
the rebuild step.

ISO 4217 and ISO 3166 use this shape: nine artifacts regenerate,
then `check_version_consistency.py` compares all of them.

### How to pick

If the repo has one generator, use the single-generator shape. It
catches the failure at the point of the failure.

If the repo has multiple generators, use the multi-generator
shape. An explicit re-read of each artifact is N blocks of
duplicated code; a centralized check is one.

State your choice in the release script's header comment.

---

## The wrapper-copy test question

When a wrapper bundles a copy of the registry file (Python wheel
ships `iso3166.json`, Go module vendors it, Rust crate includes
it), the release script must verify the bundled copy matches the
root. But whether that check is *primary* or *defense-in-depth*
depends on one thing:

**Do the wrapper tests read from the bundled copy or from the root
file?**

- If tests read the bundled copy, pytest is the primary guard. The
  release-step check is redundant but cheap; keep it as
  defense-in-depth.
- If tests read the root file, the release-step check is the sole
  local guard. CI's wrapper-sync check is the backstop.

Before adding the check, `grep` the test suite for the path it
loads. Case in Exchange Calendar: tests load the repo-root file,
so the release-step check is primary. Case in ISO 3166: tests load
the bundled copy, so the check is defense-in-depth.

The rule: verify which path the tests exercise before deciding the
check's role.

---

## Tagged releases are immutable

Three rules, all consequences of the same principle.

**1. Never move a pushed tag.** A moved tag breaks anyone who has
already fetched. If v2.3.0 pointed at a commit whose polling fix
hadn't landed, the tag stays where it is. The fix is in the next
release.

**2. Never force-push over a tag.** Deleting and re-creating is the
same problem with an extra step. If the tag is wrong, the next
release corrects the record.

**3. The CHANGELOG acknowledges divergence.** When a tag shipped
with an issue that was discovered later, the next CHANGELOG's
`[Unreleased]` or the next release's section names the divergence
and points at the fix's commit. This is the reconciliation. It is
not a rewrite.

### The partial-release state

The script can produce one state it cannot resolve: the release
commit is pushed, `VERSION` is bumped, and the poll times out
before the tag is created. Re-running the script fails at
precondition (invariant 2: `VERSION` already at target).

Recovery is a manual `git tag -a vX.Y.Z -F /tmp/tag-message.txt`
on the pushed SHA, then `git push origin vX.Y.Z`. The tag message
is the same one the script would have written. Nothing else needs
to change.

This is the one state where a human must finish the release the
script started. Document it in the release script's header comment.

---

## Operator hygiene

Four rules that emerged from specific failure modes across the
three implementations.

### 1. No heredocs for multi-line scripts

Inline Python or shell with quotes, braces, or shell
metacharacters will corrupt. Write the script to `/tmp/`, run it
standalone, check its exit code. Then proceed.

The failure mode: a heredoc silently absorbs the next shell
command into the file body. Happened in every release before the
rule.

### 2. `git diff` before every `git add`

If `git diff` is empty after an edit, the edit didn't land. The
commit will do nothing. The message describing the change will be
a lie.

The failure mode: a patch script that aborted at an anchor
mismatch, but the shell continued to the next command. The commit
message described a change that wasn't made.

### 3. Read every CI status before the next step

`in_progress`, `queued`, and `pending` are not green. Only
`completed success` is. Do not proceed past a CI check on any
other value.

The failure mode: a tag created while the second workflow was
still running. The tag landed on a commit that failed.

### 4. Any construct that requires the shell to parse structure
   goes into a file

The class is not "multi-line constructs." It is "any construct
that requires the shell to parse structure." A single-line
`bash -c "..."` with nested quoting fails the same way a pasted
multi-line loop does.

Heredocs, loops with function calls, `bash -c "..."`, Python via
stdin — all of them go into a file. Inline `python3 -c "..."`
for a one-liner is fine. The line is: does it need shell quoting
across more than one level?

Run the file. Check the exit code. Then proceed.

The failure mode: a `for` loop pasted into an interactive shell
that referenced functions defined inside a script. Twice.

---

## The vendored-snapshot `review_by` shape

When registry A vendors a byte-for-byte snapshot of registry B, and
the snapshot-freshness check (see ISO 3166's `check_snapshot_
freshness.py`) needs a `review_by` field, the byte-for-byte property
collides with the metadata requirement. Adding `review_by` to the
vendored file breaks the property the snapshot exists for.

Three shapes:

**1. Separate metadata file.** `tools/<source>_snapshot.meta.json`
next to the snapshot, carrying `review_by` and `refresh_cadence`.
The check reads both files. The snapshot stays byte-for-byte.
Recommended: the cadence is a property of the vendoring, not of
the vendored.

**2. In-memory wrapper.** The snapshot is vendored into a wrapper
object at check time, with `review_by` injected. Byte-for-byte
preserved on disk; the wrapper exists only in memory.

**3. Documented exception.** Byte-for-byte applies to the source's
*data*, not its metadata block. Add `review_by` directly and note
in the ADR that the metadata block is not covered.

The recommendation is shape 1. If a registry ever ships a second
consumer of the same source, the metadata file travels
independently.

---

## Snapshot drift

When registry A vendors a snapshot of registry B, nothing on A's
side detects that B has released a newer version. Two legitimate
shapes:

**1. Freshness check per vendoring registry.** Each repo that
vendors a snapshot checks that the vendored version matches the
sibling's current release. Cheap when both repos have a
discoverable version; hard when they do not.

**2. Refresh-on-demand.** The vendoring repo refreshes when it
needs a specific upstream change. No automatic drift detection.

Shape 1 is right for registries that *depend on upstream
stability* (a foreign-key join against the source, for example).
Shape 2 is right for registries that just *consume the data* at
build time.

Both are legitimate. The choice depends on the relationship, not
on a rule. State which shape your repo uses and why.

---

## The mojibake self-trigger rule

Any pattern-based check will find its own explanation. The mojibake
scanner matches corrupted bytes; a docstring that shows the
corruption by example contains those bytes. `check_version_
consistency.py` would trip on a doc that embedded a mismatch
example. A future freshness check would trip on an expired date
shown as an example.

Two escapes, both valid:

1. Describe the corruption in prose. "The circumflexed o becomes
   four bytes when a file is decoded as Latin-1 and re-encoded as
   UTF-8" rather than embedding the corrupted string.
2. Mark the file with the check's skip marker. Reserved for test
   fixtures that deliberately contain the pattern.

A third example: `check_version_consistency.py` would trip on a
doc that embedded a mismatch string — a `VERSION == meta.version`
example shown as `1.5.3 == 1.5.2`. The doc must describe the
mismatch without printing it.

The general rule: state what the pattern matches, not the pattern
itself.

---

## What this document does not cover

- Specific `release.sh` implementations. See the three repos.
- The eight version sites that ISO 4217 tracks, or the eleven that
  ISO 3166 tracks. See `axes.json` in each repo.
- The versioning policy (semver, what counts as major / minor /
  patch). See `CONTRIBUTING.md` in each repo.
- The snapshot-vendoring pattern for cross-registry checks. See
  the ISO 3166 README's "Consumed by" section and the Exchange
  Calendar ↔ ISO 3166 exchange.

---

## Review history

- 2026-09-27 — reviewed by ISO 4217. Two implementation divergences
  found in 4217's own `release.sh` (`head -1` on the poll list;
  missing `HEAD == origin/main` check). Doc unchanged; 4217's script
  fixes the divergences. Vendored-snapshot `review_by` shape
  discussed; recommendation adopted.
- 2026-09-27 — reviewed by Exchange Calendar. Invariant 8 clarified
  as policy, not mechanism. Partial-release recovery state added to
  the tag-immutability section. Operator hygiene rule sharpened
  from "multi-line construct" to "construct that requires shell
  parsing." Workflow poll list confirmed hardcoded; note added to
  invariant 6.

Reviewed-by:
- `slimissa/iso4217`
- `slimissa/exchange-calendar`

The document is stable. Future changes require a new review cycle.
