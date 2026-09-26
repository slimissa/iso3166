#!/usr/bin/env bash
#
# scripts/release.sh — deterministic release for the ISO 3166 registry.
#
# Usage:  scripts/release.sh <version> [--dry-run]
#
# Verifies preconditions, bumps the version sites, regenerates
# artifacts, runs the gate, commits, pushes, waits for CI to complete
# green, tags, creates the GitHub release, and writes the verification
# report.
#
# Requires: bash, git, gh, python3, cargo. The working tree must be
# clean and on main.
#
# Exits 0 on success, non-zero on the first failure. The output names
# the step that failed and the command to diagnose.

set -euo pipefail

# --- arguments ---------------------------------------------------------

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "usage: $0 <version> [--dry-run]" >&2
    exit 2
fi

VERSION="$1"
DRY_RUN=0
if [ "${2:-}" = "--dry-run" ]; then
    DRY_RUN=1
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "error: version must be X.Y.Z (got: $VERSION)" >&2
    exit 2
fi

# --- constants ---------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WORKFLOW="validate.yml"
CI_POLL_INTERVAL=20
CI_POLL_MAX=90     # 30 minutes max

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

# --- step 0: preflight -------------------------------------------------

step "0/7 preflight"

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

grep -q "^## \[$VERSION\]" CHANGELOG.md \
    || die "CHANGELOG.md has no '## [$VERSION]' section; write it before releasing"

# Current version must differ from target.
CURRENT_VERSION=$(cat VERSION)
[ "$CURRENT_VERSION" != "$VERSION" ] \
    || die "VERSION already reads $VERSION; nothing to do"

echo "  tree clean"
echo "  on main at $LOCAL_SHA"
echo "  CHANGELOG has section for $VERSION"
echo "  current version: $CURRENT_VERSION"

# --- step 1: bump ------------------------------------------------------

step "1/7 bump version sites to $VERSION"

if [ "$DRY_RUN" = "0" ]; then
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
if [ "$DRY_RUN" = "0" ]; then
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
    python3 tools/export_sql.py
    python3 tools/export_csv.py
    python3 tools/export_parquet.py
    python3 tools/sync_wrappers.py
    python3 tools/gen_consistency_fixture.py
    python3 tools/gen_withdrawn_doc.py

    GATE_LOG=/tmp/release-gate.log
    {
        python3 tools/check_version_consistency.py
        python3 tools/check_mojibake.py
        python3 tools/validate.py iso3166.json --strict-count
        python3 tools/enrich_official_name.py --check
        python3 tools/enrich_withdrawn.py --check
        python3 tools/enrich_field.py --field currency_codes --check
        python3 tools/enrich_field.py --field calling_codes --check
        python3 tools/enrich_field.py --field tlds --check
        python3 tools/enrich_field.py --field languages --check
        python3 tools/enrich_field.py --field borders --check
        python3 tools/export_sql.py --check
        python3 tools/export_csv.py --check
        python3 tools/export_parquet.py --check
        python3 tools/sync_wrappers.py --check
        python3 tools/gen_consistency_fixture.py --check
        python3 tools/gen_withdrawn_doc.py --check
        python3 -m pytest wrappers/python/tests/ -q
    } > "$GATE_LOG" 2>&1 \
        || { tail -20 "$GATE_LOG"; die "gate failed; see $GATE_LOG"; }

    echo "  gate passed"
    tail -3 "$GATE_LOG"
else
    echo "[dry-run] would regenerate artifacts and run the gate"
fi

# --- step 3: commit ----------------------------------------------------

step "3/7 commit release"

if [ "$DRY_RUN" = "0" ]; then
    git add -A
    if [ -z "$(git diff --cached --name-only)" ]; then
        die "nothing staged; version sites may already be correct"
    fi

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

if [ "$DRY_RUN" = "0" ]; then
    git push origin main

    RELEASE_SHA=$(git rev-parse HEAD)
    echo "  pushed $RELEASE_SHA; waiting for CI"

    elapsed=0
    while [ "$elapsed" -lt $((CI_POLL_INTERVAL * CI_POLL_MAX)) ]; do
        sleep "$CI_POLL_INTERVAL"
        elapsed=$((elapsed + CI_POLL_INTERVAL))

        STATUS=$(gh run list --workflow="$WORKFLOW" --limit 10 \
            --json headSha,status,conclusion \
            --jq ".[] | select(.headSha == \"$RELEASE_SHA\") | \"\(.status) \(.conclusion)\"" \
            | head -1)

        case "$STATUS" in
            "completed success")
                echo "  CI passed after ${elapsed}s"
                break
                ;;
            "completed failure"|"completed cancelled")
                echo "  CI $STATUS" >&2
                gh run list --workflow="$WORKFLOW" --limit 5 \
                    --json headSha,databaseId \
                    --jq ".[] | select(.headSha == \"$RELEASE_SHA\") | .databaseId" \
                    | head -1 \
                    | xargs -I{} gh run view {} --log-failed 2>&1 | head -40
                die "CI failed on $RELEASE_SHA"
                ;;
            *)
                echo "  waiting... ($STATUS, ${elapsed}s)"
                ;;
        esac
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
if not m:
    sys.exit(f"CHANGELOG section for {version} not found")
print(f"ISO 3166 Country Registry v{version}")
print()
print(m.group(1).strip())
PYEOF

    echo "  tag message written to $TAG_MESSAGE_FILE"
    echo "  ---"
    head -6 "$TAG_MESSAGE_FILE"
    echo "  ---"

    git tag -a "v$VERSION" -F "$TAG_MESSAGE_FILE"
    git push origin "v$VERSION"

    TAG_SHA=$(git rev-list -n1 "v$VERSION")
    [ "$TAG_SHA" = "$(git rev-parse HEAD)" ] \
        || die "tag does not point at HEAD ($TAG_SHA vs $(git rev-parse HEAD))"
    echo "  tag v$VERSION -> $TAG_SHA"
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
    if printf '%s' "$BODY" | grep -qE '<[a-z ]+>|placeholder|TODO'; then
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

    cat > "$REPORT" <<MD
# v$VERSION verification

Date: $TODAY
Commit: $TAG_SHA
Tag: v$VERSION

## What changed

See the release notes for v$VERSION at
https://github.com/slimissa/iso3166/releases/tag/v$VERSION

## CI at the tag

Workflow: .github/workflows/$WORKFLOW
The release commit's CI completed green before the tag was pushed.

## Notes

This report is generated by \`scripts/release.sh\`. Edit by hand if
additional context is needed.
MD

    git add "$REPORT"
    git commit -m "docs: v$VERSION verification report"
    git push origin main
    echo "  verification report committed"
fi

step "done — v$VERSION released"