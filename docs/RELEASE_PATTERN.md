# Release pattern

**Status:** Adopted — reviewed by ISO 3166 and Exchange Calendar.

The `release.sh` script exists in four registries. Each was written
independently. They share eight invariants and diverge on one step.
This document captures both.

- ISO 4217 (`scripts/release.sh`, two axes, eleven version sites)
- ISO 3166 (`scripts/release.sh`, one axis, eight version sites)
- Exchange Calendar (`scripts/release.sh`, three sites, two workflows)
- ISO 10383 (`scripts/release.sh`, eight version sites, one polled workflow)

---

## The essential eight

Every `release.sh` refuses on the same eight conditions, in this
order. The order matters: cheap checks first.

### 1. Refuse on unclean state

The working tree is clean, the current branch is `main`, and `HEAD`
matches `origin/main`. All three, or the release does not start.

The `HEAD` comparison must be against a freshly-fetched
`origin/main`. Without the fetch, a stale remote-tracking ref lets
the check pass locally while the remote has moved ahead.

Why: a release built from an uncommitted state is a release whose
contents can't be reproduced. A release from a non-`main` branch is a
release nobody else has. A release from a stale `main` is a release
that will conflict with the next push.

### Preflight: CI on HEAD must be green

Before `release.sh` creates the release commit, verify CI on `HEAD` has
completed green. The reference implementation in `scripts/release.sh`:

```bash
HEAD_RUNS=$(gh run list --limit 20 --json headSha,status,conclusion \
    --jq ".[] | select(.headSha == \"$LOCAL_SHA\") | \"\(.status) \(.conclusion)\"" \
    2>/dev/null || echo "")
[ -n "$HEAD_RUNS" ] || die "no CI runs found for HEAD; push first and wait for CI"
echo "$HEAD_RUNS" | grep -qE '^(queued|in_progress|pending|waiting) ' \
    && die "CI on HEAD is still running; wait for it to complete"
echo "$HEAD_RUNS" | grep -q ' failure$' \
    && die "CI on HEAD is red; fix and push before releasing"
```

Refuse on no runs, on a run that is queued, in progress, pending or
waiting, and on a failure. Without this, the release commit inherits a
red or unfinished state and CI fails at step 4.

Sourced from the ISO 3166 v1.7.2 recovery: the pre-release commit was
still running CI when `release.sh` pushed the release commit, GitHub
cancelled the pre-release run, and the release inherited a failed
check. The check landed in v1.7.2 as a fix commit.

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

A template that references a variable by name will not fail at
parse time. `set -u` catches the failure at expansion time. Add
a preflight that greps the release script for `$VAR` patterns,
checks each is assigned somewhere, and warns on orphans. ISO
3166's `check_no_orphan_variables` is the reference
implementation.

Rule: state which shape your repo uses, and why.

### 5. Gate before commit

Every check that CI runs also runs locally, before the release
commit is created. Any non-zero exit stops the release before
anything is committed or pushed.

Why: a release that fails CI is a release that needs a revert
commit. A release that fails the gate locally is a release that
was never created.


**Gate completeness.**
The release gate includes every check that runs in CI *on push*. Scheduled or event-triggered workflows that open PRs rather than gate `main` (e.g., a `refresh.yml` or `monitor.yml`) are exempt. The exemption is named per-registry in this document.

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

### 6b. The commit message is a claim about the diff

A commit whose message describes a change the commit doesn't
contain is the same class as a CHANGELOG section that overstates
what shipped. `git diff --cached --stat` before every commit is
the verification. An empty stat means the edit didn't land.

Two instances on record: ISO 3166 v1.6.4 (`Reviewed by:` vs
`Reviewed-by:` anchor mismatch) and ISO 4217's `3687bc2`
(function body not staged). Both commits described changes that
weren't in the diff.

### 6d. grep on structured data

A diagnostic check must parse with the same parser the consumer uses. Running grep on JSON cannot match values containing escaped characters. Diagnose with `json.loads` + string comparison.

### 7. Tag only on green

The tag is created only after all polled workflows report
`completed success`. No manual override, no force. The tag message
is written to a file first, read back, then passed to `git tag -F`.

Why: this is the rule that the release process exists to enforce.
`CONTRIBUTING.md` says "don't tag on red"; the script says "you
cannot tag on red."


### Tag-message verification

The tag is created with `git tag -a v$VERSION -F "$TAG_MESSAGE_FILE"`. Git applies `--cleanup` to the message when storing it. By default, git uses `strip`, which removes leading and trailing empty lines and trailing whitespace.

If the read-back uses `git for-each-ref "refs/tags/v$VERSION" --format='%(contents)'`, the stored message must match the file byte-for-byte. 

**The pitfall:** Git's `--cleanup` may strip trailing whitespace or newlines. If the write side ends with a `\n` (from `printf` or `cat`), but `git for-each-ref` strips it on read-back, the byte lengths differ and verification fails. Use `--cleanup=verbatim` (Git 2.25+) so git stores exactly what is in the file, and normalize trailing newlines on both sides.

**The exit code trap:** `diff -q fileA fileB` exits 0 (same), 1 (differ), and 2 (error, e.g. file missing). A naive `if ! diff -q ...; then die "differ"; fi` treats an exit 2 as "differ". The check must distinguish "the messages differ" from "the check could not run". Wrap the diff in an explicit status check to route exit 2 to an error message.

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

## Registry freshness vs. snapshot freshness

**Freshness is per-source, not per-registry.**
Every committed snapshot, every vendored reference, and every per-entity file derived from an external source carries its own review date and cadence. The release gate checks each one. Single-source registries have one instance; multi-source registries have many. The mechanism is identical.

**Per-source health, not just freshness.**
A review date says "we should look at this again." A health probe says "the source is still reachable." Live pages and PDFs can disappear between review dates. The gate or CI must include a reachability check for live sources (e.g., `check-sources.yml`).

Two questions that look similar and aren't:

- **Registry freshness** — is my own source of truth current?
  Answered by comparing the registry's `meta.updated` against a
  threshold (typically 180 days).

- **Snapshot freshness** — are my vendored copies of other repos'
  sources current? Answered by checking each snapshot's
  `meta.review_by` against the current date.

Both share an exit-code contract (0 fresh, 1 stale, 2 fatal).
Their state designs differ: registry freshness is one date against
one threshold; snapshot freshness has three states (ISO date,
`closed`, `null`) because vendored sources can be static.

**Naming.** A tool named `check_snapshot_freshness.py` answers the
second question. If it is used to answer the first, the naming
collides with the purpose and a maintainer will look for the
registry's freshness check and not find it. The two questions
want two names.

**Reference implementation.** ISO 4217 has both as of v1.6.3:

- `tools/check_registry_freshness.py` — reads
  `iso4217.json → meta.updated`, 180-day threshold.
- `tools/check_snapshot_freshness.py` — adopted from ISO 3166
  v1.6.1. Globs `tools/*_snapshot.json`; reads `meta.review_by`
  from a sibling `<stem>.meta.json` when present, from the
  snapshot's own `meta` block when not.

Both run in CI, both run in the release gate. Neither supersedes
the other.

**When to add the registry check.** Any repo whose source of
truth is updated on a human cadence needs it. A repo whose source
of truth is updated by an automated pipeline that runs on every
push does not — the pipeline is the freshness guarantee. ISO
3166 is in the second category today; ISO 4217 is in the first.

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

The state can also occur **after** the tag: the release is pushed,
CI passes, the tag lands, and a post-tag step (verification report,
artifact upload, notification) fails. The tag stays; the failing
step is completed manually; a follow-up commit closes the release.

ISO 3166 v1.6.2 is the reference example: the release ran through
step 6, step 7 failed on an undefined variable in the report
template, the tag stayed at the release commit, and the report was
written manually and committed forward. No force-push, no tag
move.

---

## The one exception: release-pipeline failure

If a tag was created on a commit that was red at the moment of
creation — because the release pipeline itself was broken, not
because the release content was wrong — moving the tag is a
recovery procedure, not a violation of rule 8.

The condition is narrow. The pipeline must have failed. The
release itself must be correct. The procedure must be documented
in the registry's own ADR with a Scope section limiting it to
this case.

ISO 10383's ADR 0005 is the reference implementation. Its scope
statement: the procedure applies only when the release pipeline
itself failed after the tag was pushed — a CI-polling defect, a
script that missed a workflow, a gate that ran the wrong
command. It does not apply to post-shipment discoveries (rule
8's CHANGELOG reconciliation) or to cosmetic corrections.

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

### 5. The exit code of a pipeline is the last command's exit

`python3 tool.py | tail -3; echo $?` prints `tail`'s exit code,
not `tool.py`'s. `tail` always succeeds. The failure is invisible.

Redirect to a file, capture the exit code, then read the file:

python3 tool.py > /tmp/out 2>&1
echo "exit: $?"
tail -3 /tmp/out

The failure mode: a validator ran with a broken import, exited 1,
and the piped `tail -3` printed `0`. The release proceeded with
the validator broken.

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

### 9. Patches are edits to a file, not commands for the shell

Pasting script variables (`$VERSION`), undefined functions (`die`), or multi-line blocks (`<<'PYEOF'`) into an interactive shell fails silently or behaves destructively. The shell evaluates them in the context of the terminal, not the script. Apply patches with an editor.

### 10. A dry-run must echo the actual commands

If the dry-run preview prints `git push --tags` while the real script pushes a specific tag, the preview is lying. The echo logic must be updated in the same commit as the real logic. A false preview is worse than no preview.

### 11. A dry-run must reach the commands it is meant to preview

Post-run assertions that depend on the script having executed (e.g., `grep -q "version" README.md` after a `sed` that was skipped in dry-run) will halt the script. Wrap these assertions in `DRY_RUN` checks. If a dry-run halts before the target commands, it offers no preview.

### 12. Addendum. Testing dry-run reachability

Testing a release script's dry-run in a throwaway copy requires a local remote. `git fetch origin` in preflight overwrites any `git update-ref refs/remotes/origin/<branch>` fakery set in the copy. Use this sequence to test dry-runs properly:

```bash
git init --bare /tmp/fake-origin
git remote set-url origin /tmp/fake-origin
git push -u origin main
DRY_RUN=1 scripts/release.sh <target>
```

### 13. Commit messages use -F, not -m

Long -m "..." strings are paste-garbling-vulnerable. A heredoc or an embedded command can corrupt the message body. Write the message to /tmp/msg.txt, cat it to verify, then use git commit -F /tmp/msg.txt

### 16. Never reset VERSION to re-run release.sh

The script's job is to bump N-1 to N. If it is interrupted between the
bump and the tag, recovery is manual: create the tag, the release, and
the verification doc by hand. Resetting `VERSION` to N-1 and running the
script again is not recovery. It re-bumps over a half-released state and
can produce a second, different release commit for the same version.

### 17. Never Ctrl+C during the CI wait in step 4

Interrupting the poll leaves `main` holding an untagged release commit
and cancels any pending workflow run. Let the wait finish; if it must be
stopped, treat it as the partial-release state described under "Tagged
releases are immutable" and recover manually.

### 18. CI Queueing Latency

GitHub Actions does not register a workflow run instantly. A 60-second timeout is too aggressive and causes false-positive "no CI run appeared" failures (as happened in ISO 3166 v1.7.3). Set `CI_START_TIMEOUT` to at least 180 seconds.

### 19. Split Releases by Decision Dependency

If a release contains a tool (no decision needed) and data (requires a semantic decision or external fetch), split them. Ship the tool in `vN`, and the data in `vN+1`. A blocked data decision should never block a shippable tool fix.

### 20. Bundle Layout Guard

Rule 20: every patch bundle's `apply.sh` checks, before it applies
anything, that `commit-messages/NN-*.txt` exists for the item it is about
to apply. If the message files sit flat in the bundle root, `apply.sh`
moves them into `commit-messages/` and carries on; if a message file is
still missing after that, it stops. Delivery pipelines can flatten
subdirectories, so the guard repairs the layout itself instead of
trusting it. Seen in ISO 3166 v1.7.3, v1.8.0 and v1.8.1.

### 21. Bundle Delivery Format

Rule 21: deliver a patch bundle as one `.tar.gz` that contains the whole
directory tree. Loose files get flattened by the delivery pipeline, so
Rule 20 is the backstop, not the plan. Extract with `tar -xzf`; do not
copy files by hand out of a downloads folder. Seen in the same three
bundles.

### 22. A Preflight "CI Is Still Running" Refusal Is Normal

Rule 22: `release.sh` step 0 refuses while CI on HEAD has not completed
("CI on HEAD (...) is still running; wait for it to complete"). That is
correct behavior, not a stuck script. CI takes a few minutes. Wait with
`gh run watch`, then run `release.sh` again. Do not cancel the run or
push again to hurry it: `validate.yml` cancels an in-progress run when a
new commit arrives on the same ref, so that restarts the wait. See also
Rule 18 (`CI_START_TIMEOUT`) and v1.8.1, whose release was refused three
times while CI ran.

### 23. Preflight Refuses Any Non-Success CI Conclusion

Rule 23: the `release.sh` preflight refuses unless every CI run on HEAD
completed with `success`. It names `failure`, `cancelled`, `timed_out` and
`startup_failure` in its message, and it refuses every other conclusion
too (`skipped`, `neutral`, `action_required`, `stale`, none), because a
list of bad conclusions cannot be complete. `cancelled` is what GitHub's
`cancel-in-progress` setting produces when a newer push supersedes a run;
`startup_failure` is a workflow that never started. Neither is green.
Step 4 already refused any non-success conclusion, but only after the
release commit had been pushed to `main`. The preflight is what stops the
release before it bumps and pushes.

Reference: ISO 3166 v1.8.3. The v1.7.2 preflight matched only
`' failure$'`, so a HEAD run that ended `cancelled` passed it. A
scratch-repo `--dry-run` with a fake `gh` reported "CI on HEAD is green"
and ran to the end.

### 24. State Docs Are Generated and Verified

Rule 24: every registry ships a `docs/STATE.md` that answers "what is the
state of this registry right now?" It is generated from the registry data
(or manually curated with per-field counts), and `check_state_doc.py`
verifies every numeric claim against the tree on every push. When
STATE.md drifts, CI fails.

The doc is required because a reader who reads dozens of
`docs/v*-verification.md` files to reconstruct state is a reader who will
miss something. One document, verifiable by one command, is the contract.

Reference: ISO 3166 v1.9.0. Before v1.9.0, `PROVENANCE.md` still listed
the "known gaps in v1.0.0" and `ENRICHMENT.md` still said "four enriched
fields" while the registry carried more. Neither was checked. STATE.md
and its checker close that class.

### 25. Registry Freshness Is a Gate Check, Not a CI Check

Rule 25: `check_registry_freshness.py`, which enforces that every entry's
`last_verified` is within 365 days, runs in the release gate and not in
CI. CI's job is to catch data changes that break existing invariants; the
gate's job is to catch staleness that needs human re-attestation. A CI
freshness check would fail on day 366 whether or not the tree changed,
turning every push red without a corresponding data problem. A gate check
runs once per release, which is when re-attestation is appropriate.

Reference: ISO 3166 v1.9.1. `check_registry_freshness.py` shipped in
v1.9.0 but was wired into neither CI nor the gate; v1.9.1 wires it into the
gate only.

### 26. Every Derived Artifact Is Regenerated by release.sh Step 2

Rule 26: if a file in the repository is derived from `iso3166.json` (or
from another derived file), `release.sh` step 2 must regenerate it, and
the gate must verify it. A derived file that the release does not
regenerate drifts silently. This covers the SQL exports, the CSV and TSV
exports, the Parquet export, the aggregated Parquet, the wrapper JSON
copies, the consistency fixture, `docs/WITHDRAWN.md`, `docs/STATE.md`, and
any future derived file.

Reference: ISO 3166 v1.9.1. In v1.9.0 the AI subregion fix changed
`countries_by_region.parquet`, but `release.sh` did not regenerate it; the
file was regenerated by hand and only the gate's `--check` stood between a
forgotten regeneration and a stale release. `docs/STATE.md` was also not
regenerated, so its title version would have disagreed with VERSION after
the bump. v1.9.1 adds both to step 2.

### 27. `set -euo pipefail` With `if ! cmd | grep` Is Broken

Rule 27: under `set -o pipefail`, a check written as
`if ! upstream | grep -q pattern` reports the wrong answer when `grep`
matches. `grep -q` exits at the first match, the upstream command is still
writing and is killed by SIGPIPE, and the pipeline's exit status is the
upstream's non-zero status. `!` turns that into success, `if` runs the
error branch, and the script dies although the pattern was found. The
failure depends on output size (a short history finishes before `grep`
exits), so it passes on a small test repository and fails on a real one.

Use process substitution, which `pipefail` does not cover:

    if ! grep -Fqx "pattern" <(command); then
        die "..."
    fi

Reference: ISO 3166 v1.10.0. The `--force` resume check was
`git log --format=%s | grep -Fqx "chore: release v$VERSION"` and failed on a
tree where the release commit existed. v1.10.0 fixed it by switching to
process substitution (commit 63e9d1c). v1.10.1 adds
`tests/test_release_force.sh`, which runs `release.sh --force` in a
throwaway repository with a long history and rewrites the check back to the
pipeline form to prove the test fails on the bug.

### A10. Three files, three lifetimes

The pattern is documented in three files, not one:

- `RELEASE_PATTERN.md` holds the rules.
- `AUDIT.md` is the tool inventory: which tools exist, whether each has
  a `--check` mode, and whether each runs in CI and in the release gate.
- `README-AUDIT-NOTES.md` holds the receipts: the specific failure
  behind each rule and each audit gap.

Each file has its own lifetime. Rules change when a failure class
recurs. The audit changes when a tool is added, removed, or wired into
or out of CI or the gate. Receipts are append-only and never edited; a
correction is a new entry. Keeping them apart lets a rule stay stable
while tool state moves, and keeps incident narrative out of rule text.

### A11. CURATED checks compare exactly; AGGREGATED checks compare content

Every producer's `--check` mode uses one of two comparisons, and the
layer decides which. This extends the CURATED vs. AGGREGATED paragraph
under "Version-pinned byte outputs".

CURATED artifacts are compared exactly: byte-for-byte for
`export_parquet.py` and `sync_wrappers.py`, exact text for
`export_sql.py` and `export_csv.py`. A CURATED artifact is the source of
truth for its content, so any change in its bytes is a change of state,
and a library upgrade that alters them must fail the check. Pin the tool.

AGGREGATED artifacts are compared by logical content. They are queries
over CURATED; their invariant is that the same query gives the same
answer. `export_aggregated.py --check` uses `pd.testing.assert_frame_equal`
and is the AGGREGATED reference implementation (ISO 3166). A byte
comparison would tie the aggregate to the writer library's version for
no benefit, and a content comparison on a CURATED file would let silent
drift through.

ISO 4217's `export_parquet.py` is the CURATED reference implementation.

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

### Non-zero exit halts the release

Every command that produces an artifact the release will commit
must be checked for non-zero exit before the release proceeds.
A command that fails and is not checked leaves the previous
artifact in place; the release commits stale output.

Two mechanisms, either is valid:

- Wrap the sequence in a subshell with `set -e`. The subshell
  exits on the first non-zero return.
- Check each command's exit explicitly: `command || die "..."`.

The failure mode this prevents (ISO 3166 v1.6.9): the snapshot
generator ran without its required `--source` argument. The tool
exited non-zero; the shell continued; the release commit carried
a stale snapshot. The `--source`-less invocation was the bug;
the unchecked exit was why it reached the commit.

Applies to: artifact generators, exporters, sync scripts, and
any command whose output the release commit includes.

### Every tool proves its own reachability

Every tool that produces a committed artifact must be runnable
in CI, even on unchanged inputs. Add a `--check` or smoke
invocation to the CI workflow so the tool executes on every
push.

The check does not need to verify output; it needs to verify the
tool's code path is reachable. A `--check` that regenerates and
compares satisfies both — it exercises every code path the
generator would run and fails on unreachable ones.

The failure mode this prevents (ISO 3166 v1.6.9): the snapshot
generator carried a preservation block that referenced an
undefined variable. The tool crashed on every invocation. It
appeared to work because the snapshot it produced was set by a
manual one-liner earlier; the generator's output was never
exercised. A `--check` invocation in CI would have crashed on
the first push.

Applies to: every tool with an output path in the repo, every
generator, every exporter. A tool with no CI execution is a tool
whose unreachable paths are invisible.

### The `[Unreleased]` convention

`[Unreleased]` is permitted at the top of `CHANGELOG.md` at
release time. The target version's heading must be present in
the file. Position does not matter.

Both the CI check and `release.sh`'s precondition must locate the
target heading anywhere in the file, not require it at line 1.
The precondition uses `grep -q "^## \[$VERSION\]"` — presence,
not position.

Reasoning: keep-a-changelog keeps `[Unreleased]` permanently at
the top. Removing it for the release window produces merge
conflicts and loses the unreleased-changes record between the
CHANGELOG commit and the release commit. The precondition is
presence, not position.

The failure mode is divergence between the two tools. Exchange
Calendar's CI check skipped `[Unreleased]` and located the top
dated heading; its `release.sh` required the target heading to
be literal-top. A CHANGELOG with `[Unreleased]` above the
target version passed CI and failed the release. The rule
resolves to "permitted, presence anywhere" so both tools agree.

### Version-pinned byte outputs

**Absence claims.** Assert the absence of nondeterministic strings (`date.today()`, timestamps) in the release manifest, not just the presence of expected strings. A claim that a file contains a date-dependent value is a claim that will fail tomorrow. ISO 10383's manifest is the reference implementation.


Any build tool that produces a byte-comparable artifact must be
pinned to an exact version, not a version range. The `--check`
mode compares bytes; a different tool version produces different
bytes for the same logical content; the check fails.

ISO 3166 v1.6.8 hit this: `pyarrow>=15.0` in
`requirements-dev.txt` meant CI installed whatever 15.x or 16.x
was latest, while local had 25.0.1. The committed
`iso3166.parquet` was generated by 25.0.1; CI's regeneration
under a different version differed byte-for-byte. The pin
(`pyarrow==26.0.0`) is the fix. The class is the rule.

CSV and JSON are usually stable across versions. Anything binary
or with a structured footer (Parquet, Arrow, Avro, HDF5) is not.
Pin those.

**CURATED vs. AGGREGATED checks.** 
CURATED artifacts compare byte-for-byte. They are the source of truth for their content, so any byte change is a change of state. AGGREGATED artifacts compare content-equivalence. They are queries over CURATED; their invariant is that the same query produces the same answer. Byte-comparison on AGGREGATED files couples them to a library version for no benefit; content-comparison on CURATED files lets silent drift through.

### Implementation note

`tools/check_mojibake.py` scans the first 200 bytes of every file
for the literal string `# mojibake-scan: skip`. If present, the
file is not scanned. This is the second escape, implemented.

The first escape — prose description — is a documentation
discipline, not a mechanical rule. It applies to any pattern-
based check, not just mojibake.

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

- 2026-09-27 — reviewed by ISO 10383 during their v1.0.2 preparation.
  Two corrections applied: the implementations list named ISO 10383
  as "planned" when it shipped at v1.0.0; the tag-immutability
  section gained an exception for tags created on a red commit
  by a pipeline defect. The exception cites ISO 10383's ADR 0005
  as the reference implementation.
- 2026-09-27 — reconciled against ISO 4217 v1.7.0. Adopted the
  additions ISO 3166 had not yet absorbed: the fifth
  operator-hygiene rule, the mojibake implementation note, and
  the registry-vs-snapshot subsection. Text-level differences
  reconciled in the same commit.

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

Reviewed by:

- ISO 4217 (`slimissa/iso4217`) — 2026-09-27
- ISO 3166 (`slimissa/iso3166`) — 2026-09-27
- Exchange Calendar (`slimissa/exchange-calendar`) — 2026-10-06
- ISO 10383 (`slimissa/iso10383`) — 2026-09-28

## Attribution convention

Review-history entries name the repo each addition came from.
The document is produced by three implementations; a reader
tracing a rule's origin wants a real source. "Co-authored" is
not a source.

The document is stable. Future changes require a new review cycle.
