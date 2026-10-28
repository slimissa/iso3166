#!/usr/bin/env bash
# tests/test_release_force.sh
#
# Exercises scripts/release.sh --force in a throwaway git repository with
# a stub `gh` and stub tools. It never touches the real repository.
#
#   bash tests/test_release_force.sh        # exit 0 on pass, 1 on fail
#
# Scenarios (the version under test is 0.0.1, a release commit exists):
#   1. no --force            -> "VERSION already reads"            (exit 1)
#   2. --force --dry-run     -> "mutually exclusive"               (exit 2)
#   3. --force, release commit in a long history -> resumes, exit 0
#   4. --force, no release commit for 0.0.2     -> clean error     (exit 1)
#   5. mutation: the same release.sh with the resume check rewritten as
#      `if ! git log | grep -q` must FAIL scenario 3. This proves
#      scenario 3 catches the SIGPIPE + pipefail bug (RELEASE_PATTERN.md,
#      "set -euo pipefail + if ! cmd | grep").
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_SH="$HERE/../scripts/release.sh"
[ -f "$REAL_SH" ] || { echo "FAIL: $REAL_SH not found" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fails=0
pass() { echo "ok   $1"; }
fail() { echo "FAIL $1" >&2; fails=$((fails + 1)); }

# --- stubs --------------------------------------------------------------
mkdir -p "$TMP/bin"
cat > "$TMP/bin/gh" <<'GH'
#!/usr/bin/env bash
# Stub: every CI run is green; release create/view succeed.
case "$1 $2" in
    "run list")     echo "completed success" ;;
    "release view") echo "release body" ;;
    *)              : ;;
esac
GH
chmod +x "$TMP/bin/gh"
# Stub cargo: the gate runs `cargo clippy` in wrappers/rust (step 2).
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/bin/cargo"
chmod +x "$TMP/bin/cargo"
export PATH="$TMP/bin:$PATH"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t

# build_repo DIR RELEASE_SH : a repo whose scripts/release.sh is RELEASE_SH
build_repo() {
    local dir="$1" sh="$2"
    rm -rf "$dir" "$dir.origin"
    git init -q --bare -b main "$dir.origin"
    git init -q -b main "$dir"
    (
        cd "$dir"
        git remote add origin "$dir.origin"
        mkdir -p scripts tools tests docs wrappers/python/tests wrappers/rust
        : > docs/.gitkeep; : > wrappers/rust/.gitkeep
        cp "$sh" scripts/release.sh
        # Every tools/X.py the script names becomes a stub that succeeds.
        grep -oE 'tools/[A-Za-z0-9_]+\.py' scripts/release.sh | sort -u | while read -r f; do
            printf '#!/usr/bin/env python3\nraise SystemExit(0)\n' > "$f"
        done
        printf '#!/usr/bin/env bash\nexit 0\n' > tools/check_cross_language.sh
        printf 'def test_stub():\n    assert True\n' > tests/test_stub.py
        printf 'def test_stub():\n    assert True\n' > wrappers/python/tests/test_stub.py
        printf '0.0.0\n' > VERSION
        printf '# Changelog\n\n## [0.0.2] - 2000-01-02\n\n- two\n\n## [0.0.1] - 2000-01-01\n\n- one\n' > CHANGELOG.md
        git add -A && git commit -q -m "init"
        # A long history so `git log --format=%s` exceeds the pipe buffer.
        # Generated with fast-import; the release commit is the newest.
        python3 - <<'PY' | git fast-import --quiet
n = 6000
print("commit refs/heads/main\nmark :1\ncommitter t <t@t> 1000000000 +0000\ndata 5\nbulk0\nfrom refs/heads/main^0\n")
for i in range(2, n + 1):
    msg = f"bulk commit number {i}"
    print(f"commit refs/heads/main\nmark :{i}\ncommitter t <t@t> {1000000000 + i} +0000\ndata {len(msg)}\n{msg}\nfrom :{i-1}\n")
PY
        git reset -q --hard main
        printf '0.0.1\n' > VERSION
        git add -A && git commit -q -m "chore: release v0.0.1"
        git push -q origin main
    )
}

# run_sh DIR ARGS... : run the repo's release.sh, capture output + exit code
run_sh() {
    local dir="$1"; shift
    set +e
    OUT="$(cd "$dir" && bash scripts/release.sh "$@" 2>&1)"
    RC=$?
    set -e
}

REPO="$TMP/repo"
build_repo "$REPO" "$REAL_SH"

# 1. Without --force the script refuses to resume.
run_sh "$REPO" 0.0.1
if [ "$RC" -eq 1 ] && grep -q "VERSION already reads 0.0.1" <<<"$OUT"; then
    pass "1. no --force: refuses with 'VERSION already reads' (exit 1)"
else fail "1. no --force (rc=$RC): $(tail -3 <<<"$OUT")"; fi

# 2. --force and --dry-run are mutually exclusive.
run_sh "$REPO" 0.0.1 --force --dry-run
if [ "$RC" -eq 2 ] && grep -q "mutually exclusive" <<<"$OUT"; then
    pass "2. --force --dry-run: 'mutually exclusive' (exit 2)"
else fail "2. --force --dry-run (rc=$RC): $(tail -3 <<<"$OUT")"; fi

# 3. --force resumes when the release commit exists (long history).
run_sh "$REPO" 0.0.1 --force
if [ "$RC" -eq 0 ] \
   && grep -q "resuming in post-commit mode" <<<"$OUT" \
   && grep -q "release commit already in history" <<<"$OUT" \
   && git -C "$REPO" rev-parse -q --verify refs/tags/v0.0.1 >/dev/null; then
    pass "3. --force resumes from the post-commit state and tags v0.0.1 (exit 0)"
else fail "3. --force resume (rc=$RC): $(tail -5 <<<"$OUT")"; fi

# 4. --force with no release commit in history is a clean error.
(
    cd "$REPO"
    printf '0.0.2\n' > VERSION
    git add -A && git commit -q -m "bump without a release commit"
    git push -q origin main
)
run_sh "$REPO" 0.0.2 --force
if [ "$RC" -eq 1 ] && grep -q "no 'chore: release v0.0.2' commit in history" <<<"$OUT"; then
    pass "4. --force without a release commit: clean error (exit 1)"
else fail "4. --force, no release commit (rc=$RC): $(tail -3 <<<"$OUT")"; fi

# 5. Mutation: the buggy pipeline form of the resume check must fail
#    scenario 3. If the rewrite does not apply, the test is stale.
GOOD='grep -Fqx "chore: release v$VERSION" <(git log --format=%s)'
BUGGY='git log --format=%s | grep -Fqx "chore: release v$VERSION"'
if ! grep -qF -- "$GOOD" "$REAL_SH"; then
    fail "5. mutation: release.sh no longer contains the process-substitution check; update this test"
else
    python3 - "$REAL_SH" "$TMP/release_buggy.sh" "$GOOD" "$BUGGY" <<'PY'
import sys
src, dst, good, bad = sys.argv[1:5]
t = open(src).read()
assert good in t
open(dst, "w").write(t.replace(good, bad, 1))
PY
    BUGGY_REPO="$TMP/repo_buggy"
    build_repo "$BUGGY_REPO" "$TMP/release_buggy.sh"
    run_sh "$BUGGY_REPO" 0.0.1 --force
    if [ "$RC" -ne 0 ] && grep -q "no 'chore: release v0.0.1' commit in history" <<<"$OUT"; then
        pass "5. mutation (git log | grep under pipefail) is caught by scenario 3"
    else
        fail "5. mutation not caught (rc=$RC): the long-history scenario no longer triggers SIGPIPE"
    fi
fi

if [ "$fails" -ne 0 ]; then echo "FAIL: $fails scenario(s) failed" >&2; exit 1; fi
echo "PASS"
