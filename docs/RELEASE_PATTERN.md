# Release pattern

**Status:** DRAFT — pending review by ISO 4217 and Exchange Calendar.

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

**Single generator.** `build → re-read → compare`. Three lines,
immediate, points at the build script if it fails.

**Multiple generators.** `regenerate all → gate → consistency
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
deliberately excluded. List them explicitly in the script, and
verify the list against the workflows directory before every
release.

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

### 4. Every multi-line construct goes into a file

Heredocs, loops with function calls, `bash -c "..."`, Python via
stdin — all of them. If it needs quoting across more than one
level, it goes into a file. Run the file. Check the exit code.
Then proceed.

The failure mode: a `for` loop pasted into an interactive shell
that referenced functions defined inside a script. Twice.

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

## Reviewers

This draft awaits review by:

- ISO 4217 (`slimissa/iso4217`)
- Exchange Calendar (`slimissa/exchange-calendar`)

After both have reviewed, the DRAFT marker in the header is
removed, and a `Reviewed-by:` line is added naming the reviewing
repos and the review dates.
