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
#
# Exits 0 on success, non-zero on the first failure. The output names
# the step that failed and the command to diagnose.

set -euo pipefail

# --- arguments ---------------------------------------------------------

if [ $# -lt 1 ] || [ $# -gt 3 ]; then
    echo "usage: $0 <version> [--dry-run | --force]" >&2
    exit 2
fi

VERSION="$1"
DRY_RUN=0
FORCE=0
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --force)   FORCE=1;   shift ;;
        *)
            echo "error: unknown flag: $1 (expected --dry-run or --force)" >&2
            exit 2
            ;;
    esac
done

if [ "$DRY_RUN" = "1" ] && [ "$FORCE" = "1" ]; then
    echo "error: --dry-run and --force are mutually exclusive" >&2
    exit 2
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "error: version must be X.Y.Z (got: $VERSION)" >&2
    exit 2
fi

# --- constants ---------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

POLLED_WORKFLOWS=(
    "validate.yml"
)
# Every command of the artifact freshness checks and of the gate is recorded
# here as "<exit code><TAB><command>"; step 7 writes it into the report.
GATE_REC=/tmp/release-gate.rec
CI_POLL_INTERVAL=20
CI_POLL_MAX=90     # 30 minutes max
CI_START_TIMEOUT=180  # die if no CI run appears within this many seconds


check_workflows_covered() {
    local actual
    actual="$(find .github/workflows -maxdepth 1 \( -name '*.yml' -o -name '*.yaml' \) \
        -exec basename {} \; 2>/dev/null \
        | grep -v -E '^(monitor|fetch|refresh|update|schedule)' || true)"
    if [ -z "$actual" ]; then
        return
    fi
    while read -r wf; do
        [ -z "$wf" ] && continue
        local found=0
        for d in "${POLLED_WORKFLOWS[@]}"; do
            if [ "$wf" = "$d" ]; then
                found=1
                break
            fi
        done
        if [ "$found" -eq 0 ]; then
            die "workflow $wf is not in POLLED_WORKFLOWS; add it to the array"
        fi
    done <<< "$actual"
}

check_manifest_has_version() {
    if ! python3 -c "
import json, sys
manifest = json.load(open('tools/release_claims.json'))
sys.exit(0 if '$VERSION' in manifest else 1)
"; then
        die "release_claims.json has no entry for version $VERSION"
    fi
}

# Detect template variables that were renamed but not updated
# everywhere. A heredoc referencing an undefined variable only
# fails at expansion time, not parse time. See RELEASE_PATTERN.md
# operator hygiene.
check_no_orphan_variables() {
    local orphans
    orphans="$(grep -nE '\$\{[A-Z_]+\}|\$[A-Z_]{3,}' scripts/release.sh \
        | grep -vE '^[0-9]+:\s*#' \
        | grep -oE '\$\{?[A-Z_]+' \
        | sort -u \
        | while read -r v; do
            v="${v#\$}"
            v="${v#\{}"
            # A variable is defined if it appears as assignment anywhere.
            if ! grep -qE "(^|\s)${v}=" scripts/release.sh; then
                echo "$v"
            fi
        done || true)"

    if [ -n "$orphans" ]; then
        echo "orphan variables (defined nowhere, expanded somewhere):" >&2
        echo "$orphans" | sed 's/^/  /' >&2
        die "release script references undefined variables"
    fi
}

# --- helpers -----------------------------------------------------------

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
step() { printf '\n=== %s ===\n' "$*"; }

run() {
    if [ "$DRY_RUN" = "1" ]; then
        printf '[dry-run] %s\n' "$*"
    else
        "$@"
    fi
}

# gate CMD...: print a step label, run CMD, record its exit code, return it.
# Inside the gate subshell a non-zero return stops the gate (set -e).
gate() {
    local rc=0
    printf '=== gate: %s\n' "$*"
    "$@" || rc=$?
    printf '%s\t%s\n' "$rc" "$*" >> "$GATE_REC"
    printf '=== exit: %s\n' "$rc"
    return "$rc"
}

# BEGIN artifact-freshness
# Committed artifacts must equal what the tree generates. The order is the
# point: check first (committed against the tree), regenerate second, diff
# against HEAD third. A --check run AFTER regeneration compares a file with
# itself and can never fail, so the gate holds no such line.
#
# This runs at HEAD before the version bump (normal mode), or at the release
# commit (--force). After the bump the artifacts differ from HEAD by design;
# tools/check_release_diff.py in the gate takes over there.
#
# countries_by_region.parquet is not in the byte diff: its --check compares
# tables, not bytes (the bytes vary with the pyarrow version), and stage 1
# has already run that comparison.
FRESHNESS_ARTIFACTS=(
    'iso3166*.sql' 'iso3166*.csv' 'iso3166*.tsv'
    iso3166.parquet
    wrappers/go/iso3166.json wrappers/javascript/iso3166.json
    wrappers/python/iso3166/iso3166.json wrappers/rust/iso3166.json
    tests/cross_language_consistency.json docs/WITHDRAWN.md
)
artifact_freshness() {
    local mode="${1:-full}" cmd out gen rc
    echo "  [1/3] --check: committed artifacts against the tree"
    for cmd in \
        "python3 tools/export_sql.py --check" \
        "python3 tools/export_csv.py --check" \
        "python3 tools/export_parquet.py --check" \
        "python3 tools/export_aggregated.py --check" \
        "python3 tools/sync_wrappers.py --check" \
        "python3 tools/gen_consistency_fixture.py --check" \
        "python3 tools/gen_withdrawn_doc.py --check"
    do
        rc=0
        out=$($cmd 2>&1) || rc=$?
        printf '%s\t%s\n' "$rc" "$cmd" >> "$GATE_REC"
        if [ "$rc" -ne 0 ]; then
            echo "FRESHNESS FAIL: $cmd"
            printf '%s\n' "$out" | tail -8
            die "committed artifact is stale ($cmd); regenerate, commit, push and wait for CI, then re-run"
        fi
    done
    if [ "$mode" = "check-only" ]; then
        echo "  (check-only: regeneration and diff skipped)"
        return 0
    fi
    echo "  [2/3] regenerating the artifacts"
    for gen in export_sql export_csv export_parquet export_aggregated \
               sync_wrappers gen_consistency_fixture gen_withdrawn_doc; do
        python3 "tools/$gen.py" >/dev/null || die "tools/$gen.py failed"
    done
    echo "  [3/3] git diff --exit-code: regenerated artifacts against HEAD"
    rc=0
    git diff --exit-code --stat -- "${FRESHNESS_ARTIFACTS[@]}" || rc=$?
    printf '%s\t%s\n' "$rc" "git diff --exit-code -- ${FRESHNESS_ARTIFACTS[*]}" >> "$GATE_REC"
    if [ "$rc" -ne 0 ]; then
        echo "FRESHNESS FAIL: git diff --exit-code"
        die "regeneration changed committed artifacts; commit them first"
    fi
}
# END artifact-freshness

# --- step 0: preflight -------------------------------------------------

step "0/7 preflight"

: > "$GATE_REC"

[ -d .git ] || die "not in a git repository"

if [ -n "$(git status --porcelain)" ]; then
    git status --short
    die "working tree is dirty; commit or stash first"
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
[ "$BRANCH" = "main" ] || die "must be on main (currently on $BRANCH)"

git fetch origin main --quiet
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse origin/main)
[ "$LOCAL_SHA" = "$REMOTE_SHA" ] || die "main is not up to date with origin/main"
# Refuse if CI on HEAD has not completed green.
# The pre-release commit must be CI-verified before the release commit is created;
# otherwise the release commit inherits any red state and CI fails at step 4.
HEAD_RUNS=$(gh run list --limit 20 --json headSha,status,conclusion \
    --jq ".[] | select(.headSha == \"$LOCAL_SHA\") | \"\(.status) \(.conclusion)\"" \
    2>/dev/null || echo "")
if [ -z "$HEAD_RUNS" ]; then
    die "no CI runs found for HEAD ($LOCAL_SHA); push first and wait for CI"
fi
if echo "$HEAD_RUNS" | grep -qE '^(queued|in_progress|pending|waiting) '; then
    die "CI on HEAD ($LOCAL_SHA) is still running; wait for it to complete"
fi
# Every run on HEAD must have concluded "success". The named conclusions
# first, for a clear message; GitHub's "cancelled" is what cancel-in-progress
# produces, and "startup_failure" is a runner that never started.
if echo "$HEAD_RUNS" | grep -qE ' (failure|cancelled|timed_out|startup_failure)$'; then
    die "CI on HEAD ($LOCAL_SHA) is not green (failure, cancelled, timed_out, or startup_failure); fix and push before releasing"
fi
# Anything else that is not exactly "completed success" (skipped, neutral,
# action_required, stale, a status such as "requested") did not verify HEAD
# either; a list of bad conclusions cannot be complete, so this one is not.
if echo "$HEAD_RUNS" | grep -qvx 'completed success'; then
    BAD_RUNS=$(echo "$HEAD_RUNS" | grep -vx 'completed success' | sort -u | paste -sd, -)
    die "CI on HEAD ($LOCAL_SHA) did not conclude 'success' (got: $BAD_RUNS); fix and push before releasing"
fi
echo "  CI on HEAD is green"

grep -q "^## \[$VERSION\]" CHANGELOG.md \
    || die "CHANGELOG.md has no '## [$VERSION]' section; write it before releasing"

# Current version must differ from target, unless --force.
CURRENT_VERSION=$(cat VERSION)
RESUME_MODE=0
if [ "$CURRENT_VERSION" = "$VERSION" ]; then
    if [ "$FORCE" = "0" ]; then
        die "VERSION already reads $VERSION; nothing to do (use --force to resume from post-commit state)"
    fi
    RESUME_MODE=1
    echo "  VERSION already $VERSION; resuming in post-commit mode (--force)"
    # The tag lands on HEAD, so HEAD must BE the release commit. A commit on
    # top of it would be tagged as the release. When no release commit exists
    # at all, step 3 reports that.
    HEAD_SUBJECT=$(git log -1 --format=%s)
    if [ "$HEAD_SUBJECT" != "chore: release v$VERSION" ] \
       && [ -n "$(git log -n 1 --format=%H --grep="^chore: release v$VERSION\$")" ]; then
        die "resume mode: HEAD is not the release commit (HEAD subject: '$HEAD_SUBJECT'; expected subject: 'chore: release v$VERSION'); --force tags HEAD, so it refuses to tag a different commit"
    fi
else
    if [ "$FORCE" = "1" ]; then
        echo "  --force given but VERSION ($CURRENT_VERSION) != target ($VERSION); running as normal release"
    fi
fi

# Tag must not exist locally or on origin.
if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null 2>&1; then
    die "tag v$VERSION already exists locally; delete it or pick a different version"
fi
if [ -n "$(git ls-remote --tags origin "refs/tags/v$VERSION")" ]; then
    die "tag v$VERSION already exists on origin; pick a different version"
fi

check_no_orphan_variables
check_workflows_covered
if [ "$RESUME_MODE" = "1" ]; then
    echo "  artifact freshness: checked in step 2 (resume mode)"
elif [ "$DRY_RUN" = "1" ]; then
    artifact_freshness check-only
else
    artifact_freshness full
fi
echo "  tree clean"
echo "  on main at $LOCAL_SHA"
echo "  CHANGELOG has section for $VERSION"
echo "  current version: $CURRENT_VERSION; tag v$VERSION is free"

# --- step 1: bump ------------------------------------------------------

step "1/7 bump version sites to $VERSION"

if [ "$RESUME_MODE" = "1" ]; then
    echo "  (skipped: VERSION already $VERSION, resume mode)"
elif [ "$DRY_RUN" = "0" ]; then
    printf '%s\n' "$VERSION" > VERSION

    python3 - "$VERSION" <<'PYEOF'
import json, re, sys
from datetime import date
from pathlib import Path

version = sys.argv[1]
today = date.today().isoformat()

p = Path("iso3166.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["meta"]["version"] = version
d["meta"]["updated"] = today
p.write_text(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
             encoding="utf-8")

def sub_file(path, pattern, replacement):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    new = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    if new == text:
        sys.exit(f"sub had no effect on {path}: pattern {pattern!r}")
    p.write_text(new, encoding="utf-8")

sub_file("wrappers/python/pyproject.toml",
         r'^version = "[0-9.]+"',
         f'version = "{version}"')
sub_file("wrappers/python/iso3166/__init__.py",
         r'__version__ = "[0-9.]+"',
         f'__version__ = "{version}"')
sub_file("wrappers/rust/Cargo.toml",
         r'^version = "[0-9.]+"',
         f'version = "{version}"')
sub_file("README.md",
         r'registry-[0-9.]+-orange',
         f'registry-{version}-orange')

p = Path("wrappers/javascript/package.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["version"] = version
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
PYEOF

    (cd wrappers/rust && cargo build --quiet)   # regenerates Cargo.lock
else
    echo "[dry-run] would set VERSION and the wrapper manifests to $VERSION"
fi

# Verify all eight sites agree.
if [ "$RESUME_MODE" = "1" ]; then
    echo "  (sites already verified by the previous release attempt, resume mode)"
elif [ "$DRY_RUN" = "0" ]; then
    declare -a SITES=(
        "$(cat VERSION)"
        "$(python3 -c "import json; print(json.load(open('iso3166.json'))['meta']['version'])")"
        "$(grep -oP '^version = "\K[0-9.]+' wrappers/python/pyproject.toml)"
        "$(grep -oP '__version__ = "\K[0-9.]+' wrappers/python/iso3166/__init__.py)"
        "$(python3 -c "import json; print(json.load(open('wrappers/javascript/package.json'))['version'])")"
        "$(grep -oP '^version = "\K[0-9.]+' wrappers/rust/Cargo.toml | head -1)"
        "$(grep -A1 'name = \"iso3166-registry\"' wrappers/rust/Cargo.lock | grep -oP 'version = "\K[0-9.]+' | head -1)"
        "$(grep -oP 'registry-\K[0-9.]+(?=-orange)' README.md)"
    )
    for s in "${SITES[@]}"; do
        [ "$s" = "$VERSION" ] || die "version site mismatch: one reads $s, expected $VERSION"
    done
    echo "  all 8 version sites read $VERSION"
fi

# --- step 2: regenerate + gate -----------------------------------------

step "2/7 regenerate artifacts and run the gate"

if [ "$DRY_RUN" = "0" ]; then
    if [ "$RESUME_MODE" = "1" ]; then
        artifact_freshness full
    fi
    python3 tools/export_sql.py
    python3 tools/export_csv.py
    python3 tools/export_parquet.py
    python3 tools/export_aggregated.py
    python3 tools/sync_wrappers.py
    python3 tools/gen_consistency_fixture.py
    python3 tools/gen_withdrawn_doc.py
    python3 tools/gen_state_doc.py

    # Resume mode skips the commit step, so anything regeneration changed
    # stays uncommitted while the tag lands on HEAD without it.
    if [ "$RESUME_MODE" = "1" ]; then
        DIRTY="$(git status --porcelain)"
        if [ -n "$DIRTY" ]; then
            printf '%s\n' "$DIRTY" >&2
            die "resume mode: regeneration changed files that the release commit does not contain: $(printf '%s\n' "$DIRTY" | sed 's/^...//' | tr '\n' ' ')- the tag would point at a tree without them; discard them (git checkout -- <file>) or release a new version"
        fi
    fi

    GATE_LOG=/tmp/release-gate.log
    # Run the gate as a plain statement and read its status from $?. A
    # subshell on the left of `||` (or inside `if`) ignores `set -e` in bash,
    # so only its last command would count (docs/RELEASE_PATTERN.md, Rule 29).
    GATE_RC=0
    set +e
    (
        set -e
        gate python3 tools/check_version_consistency.py
        gate python3 tools/check_release_claims.py "$VERSION"
        gate python3 tools/check_mojibake.py
        gate python3 tools/check_snapshot_freshness.py
        gate python3 tools/check_registry_freshness.py
        gate python3 tools/validate.py iso3166.json --strict-count --strict-independent --require-schema
        gate python3 tools/check_introduced.py
        gate python3 tools/check_introduced_meta.py
        gate python3 tools/check_state_doc.py --strict
        gate python3 tools/check_docs_match_tree.py
        gate python3 tools/enrich_official_name.py --check
        gate python3 tools/enrich_withdrawn.py --check
        gate python3 tools/enrich_field.py --field currency_codes --check
        gate python3 tools/enrich_field.py --field calling_codes --check
        gate python3 tools/enrich_field.py --field tlds --check
        gate python3 tools/enrich_field.py --field languages --check
        gate python3 tools/enrich_field.py --field borders --check
        gate python3 tools/enrich_field.py --field subregion --check
        gate python3 tools/enrich_field.py --field intermediate_region --check
        gate python3 tools/enrich_field.py --only-value
        gate python3 tools/enrich_club_memberships.py --check
        gate python3 tools/check_release_diff.py
        gate python3 -m pytest tests/ -v
        gate python3 -m pytest wrappers/python/tests/ -q
        gate python3 tools/build_introduced_snapshot.py --check
        gate python3 tools/build_club_snapshots.py --check
        gate bash tests/test_release_force.sh
        gate bash tools/check_cross_language.sh US GB JP
        gate bash -c 'cd wrappers/rust && cargo clippy --all-targets -- -D warnings'
    ) > "$GATE_LOG" 2>&1
    GATE_RC=$?
    set -e
    [ "$GATE_RC" -eq 0 ] || { tail -20 "$GATE_LOG"; die "gate failed (exit $GATE_RC); see $GATE_LOG"; }

    echo "  gate passed"
    tail -3 "$GATE_LOG"
else
    echo "[dry-run] would regenerate artifacts and run the gate"
fi

# --- step 3: commit ----------------------------------------------------

step "3/7 commit release"

if [ "$RESUME_MODE" = "1" ]; then
    if ! grep -Fqx "chore: release v$VERSION" <(git log --format=%s); then
        die "resume mode: no 'chore: release v$VERSION' commit in history; --force can only resume from a post-commit state"
    fi
    echo "  (skipped: release commit already in history, HEAD at $(git rev-parse --short HEAD), resume mode)"
elif [ "$DRY_RUN" = "0" ]; then
    git add -A
    if [ -z "$(git diff --cached --name-only)" ]; then
        die "nothing staged; version sites may already be correct"
    fi

    # validate.yml ignores pushes that touch only these root paths
    # (paths-ignore). A release commit made only of them would not
    # trigger CI, and step 4 would wait for runs that never appear.
    # Keep this list in sync with paths-ignore in validate.yml.
    CI_RELEVANT="$(git diff --cached --name-only \
        | grep -v -F -x -e .gitignore -e .gitattributes -e LICENSE || true)"
    [ -n "$CI_RELEVANT" ] \
        || die "staged changes touch only paths ignored by validate.yml; CI will not run on this commit. Inspect: git diff --cached --stat"

    git commit -F - <<MSG
chore: release v$VERSION

See CHANGELOG.md for the full list.
MSG

    RELEASE_SHA=$(git rev-parse HEAD)
    echo "  release commit: $RELEASE_SHA"
else
    echo "[dry-run] would commit release"
fi

# --- step 4: push and wait for CI --------------------------------------

step "4/7 push and wait for CI"

if [ "$RESUME_MODE" = "1" ]; then
    git fetch origin main --quiet
    LOCAL_SHA=$(git rev-parse HEAD)
    ORIGIN_SHA=$(git rev-parse origin/main)
    if [ "$LOCAL_SHA" != "$ORIGIN_SHA" ]; then
        die "resume mode: HEAD $LOCAL_SHA is not on origin/main ($ORIGIN_SHA); push first"
    fi
    echo "  (skipped: HEAD already pushed at $LOCAL_SHA, resume mode)"
elif [ "$DRY_RUN" = "0" ]; then
    git push origin main

    RELEASE_SHA=$(git rev-parse HEAD)
    echo "  pushed $RELEASE_SHA; waiting for CI"

    elapsed=0
    while [ "$elapsed" -lt $((CI_POLL_INTERVAL * CI_POLL_MAX)) ]; do
        sleep "$CI_POLL_INTERVAL"
        elapsed=$((elapsed + CI_POLL_INTERVAL))

        RUNS=$(gh run list --limit 30 \
            --json databaseId,headSha,status,conclusion,workflowName \
            --jq ".[] | select(.headSha == \"$RELEASE_SHA\") | \"\(.databaseId)|\(.status)|\(.conclusion // \"pending\")|\(.workflowName)\"" \
            2>/dev/null || echo "")

        if [ -z "$RUNS" ]; then
            if [ "$elapsed" -ge "$CI_START_TIMEOUT" ]; then
                die "no CI run for $RELEASE_SHA appeared within ${CI_START_TIMEOUT}s; check paths-ignore, Actions status, and gh auth (gh errors are suppressed here)"
            fi
            echo "  no runs yet (${elapsed}s)"
            continue
        fi

        ALL_COMPLETE=true
        FAILED=false
        while IFS='|' read -r id status conclusion name; do
            if [ "$status" != "completed" ]; then
                ALL_COMPLETE=false
                break
            fi
            if [ "$conclusion" != "success" ]; then
                FAILED=true
                echo "  workflow '$name' (run $id) concluded '$conclusion'" >&2
            fi
        done <<< "$RUNS"

        if [ "$FAILED" = "true" ]; then
            die "CI failed on $RELEASE_SHA"
        fi

        if [ "$ALL_COMPLETE" = "true" ]; then
            echo "  CI passed after ${elapsed}s"
            break
        fi

        echo "  waiting... (${elapsed}s)"
    done

    if [ "$elapsed" -ge $((CI_POLL_INTERVAL * CI_POLL_MAX)) ]; then
        die "CI did not complete within $((CI_POLL_INTERVAL * CI_POLL_MAX))s"
    fi
fi

# --- step 5: tag -------------------------------------------------------

step "5/7 tag v$VERSION"

TAG_MESSAGE_FILE="/tmp/release-tag-message.txt"
if [ "$DRY_RUN" = "0" ]; then
    # Derive the tag message from the CHANGELOG section.
    python3 - "$VERSION" > "$TAG_MESSAGE_FILE" <<'PYEOF'
import re, sys
from pathlib import Path
version = sys.argv[1]
text = Path("CHANGELOG.md").read_text(encoding="utf-8")
pattern = rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)"
m = re.search(pattern, text, re.M | re.S)
if not m: sys.exit(f"CHANGELOG section for {version} not found")
print(f"ISO 3166 Country Registry v{version}")
print()
print(m.group(1).strip())
PYEOF

    echo "  tag message written to $TAG_MESSAGE_FILE"
    echo "  ---"
    head -6 "$TAG_MESSAGE_FILE"
    echo "  ---"

    # Guard: an empty tag message means the CHANGELOG extraction failed.
    [ -s "$TAG_MESSAGE_FILE" ] \
        || die "tag message file is empty: $TAG_MESSAGE_FILE"

    # Delete the local tag and die. Used by every post-create check
    # below so that a failed verification never leaves a tag behind
    # and never reaches the push (rule 8: pushed tags are immutable).
    drop_local_tag_and_die() {
        if ! git tag -d "v$VERSION" >/dev/null 2>&1; then
            die "$1; git tag -d also failed; tag may still exist locally"
        fi
        die "$1; local tag deleted before push"
    }

    git tag -a "v$VERSION" -F "$TAG_MESSAGE_FILE" --cleanup=verbatim

    TAG_SHA=$(git rev-list -n1 "v$VERSION")
    [ "$TAG_SHA" = "$(git rev-parse HEAD)" ] \
        || drop_local_tag_and_die "tag points at $TAG_SHA, not HEAD ($(git rev-parse HEAD))"

    if ! git for-each-ref "refs/tags/v$VERSION" --format='%(contents)' > /tmp/recorded_tag.txt; then
        drop_local_tag_and_die "could not read tag message from git"
    fi

    set +e
    # Normalize trailing newlines to prevent false positives
    diff -q <(printf '%s' "$(cat /tmp/recorded_tag.txt)") <(printf '%s' "$(cat "$TAG_MESSAGE_FILE")") > /dev/null
    diff_status=$?
    set -e

    if [ "$diff_status" -eq 2 ]; then
        drop_local_tag_and_die "diff command failed to compare tag messages"
    elif [ "$diff_status" -eq 1 ]; then
        drop_local_tag_and_die "tag message in git does not match the file"
    fi

    # Push only after every local verification has passed.
    git push origin "v$VERSION"
    echo "  tag v$VERSION -> $TAG_SHA (verified before push)"
fi

# --- step 6: GitHub release --------------------------------------------

step "6/7 GitHub release"

if [ "$DRY_RUN" = "0" ]; then
    RELNOTES=/tmp/release-notes.txt
    python3 - "$VERSION" > "$RELNOTES" <<'PYEOF'
import re, sys
from pathlib import Path

version = sys.argv[1]
text = Path("CHANGELOG.md").read_text(encoding="utf-8")
pattern = rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)"
m = re.search(pattern, text, re.M | re.S)
if not m:
    sys.exit(f"CHANGELOG section for {version} not found")
print(m.group(1).strip())
PYEOF

    gh release create "v$VERSION" \
        --title "ISO 3166 Country Registry v$VERSION" \
        --notes-file "$RELNOTES" \
        --verify-tag

    # Verify the body isn't a placeholder.
    BODY=$(gh release view "v$VERSION" --json body --jq .body)
    if printf '%s' "$BODY" | grep -qE '<clean release text here>|<release text>|<your version here>'; then
        echo "release body looks wrong:" >&2
        printf '%s\n' "$BODY" | head -10 >&2
        die "release body contains placeholder text; fix with 'gh release edit v$VERSION --notes-file $RELNOTES'"
    fi
    echo "  release created and verified"
fi

# --- step 7: verification report ---------------------------------------

step "7/7 verification report"

if [ "$DRY_RUN" = "0" ]; then
    REPORT=docs/v"$VERSION"-verification.md
    TAG_SHA=$(git rev-list -n1 "v$VERSION")
    TODAY=$(date +%Y-%m-%d)

    python3 tools/write_verification_report.py \
        --version "$VERSION" --commit "$TAG_SHA" --tag "v$VERSION" \
        --date "$TODAY" --workflows "${POLLED_WORKFLOWS[*]}" \
        --gate-rec "$GATE_REC" --gate-log "$GATE_LOG" --out "$REPORT" \
        || die "could not write the verification report (no gate evidence recorded?)"

    git add "$REPORT" "$REPORT.sha256"
    git commit -m "docs: v$VERSION verification report"
    git push origin main
    echo "  verification report committed"
fi

step "done — v$VERSION released"