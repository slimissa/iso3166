#!/usr/bin/env bash
# tests/test_release_force.sh
#
# Exercises scripts/release.sh --force in a throwaway git repository with
# a stub `gh`, a stub `cargo`, and a stub `pytest` module. It never touches
# the real repository.
#
#   bash tests/test_release_force.sh        # exit 0 on pass, 1 on fail
#
# Scenarios (the version under test is 0.0.1, a release commit exists):
#   1. no --force            -> "VERSION already reads"            (exit 1)
#   2. --force --dry-run     -> "mutually exclusive"               (exit 2)
#   3. --force, release commit in a long history -> resumes, exit 0, and
#      the report carries the gate evidence and a matching .sha256
#   4. --force, no release commit for 0.0.2     -> clean error     (exit 1)
#   5. mutation: the same release.sh with the resume check rewritten as
#      `if ! git log | grep -q` must FAIL scenario 3. This proves
#      scenario 3 catches the SIGPIPE + pipefail bug (RELEASE_PATTERN.md,
#      "set -euo pipefail + if ! cmd | grep").
#   6. a check in the MIDDLE of the gate fails (stub check_mojibake.py exits
#      1) -> release.sh dies with "gate failed" and creates no tag.
#   7. mutation: the gate subshell rewritten to sit on the left of `||`
#      (bash then ignores `set -e` in it, so only the last command counts)
#      lets that same failing check through. This proves scenario 6
#      catches the bug (RELEASE_PATTERN.md, Rule 29).
#   8. a commit lands on top of the release commit -> --force refuses,
#      naming HEAD's subject and the expected subject (exit 1, no tag).
#   9. regeneration produces an uncommitted file (a stale docs/STATE.md)
#      -> --force refuses, naming the file (exit 1, no tag).
#  10. a release.sh run INSIDE the gate (as this test runs inside the real
#      gate) must not truncate the outer run's record: the outer report
#      keeps every command (the v1.12.3 report kept 11 of 38).
#  11. two runs print two different gate-record paths, none of them fixed.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_SH="$HERE/../scripts/release.sh"
[ -f "$REAL_SH" ] || { echo "FAIL: $REAL_SH not found" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Every release.sh run in this test keeps its record and log in a mktemp
# directory under $TMPDIR. Point TMPDIR at this test's own directory so they
# are removed with it and do not pile up in /tmp.
export TMPDIR="$TMP"
fails=0
pass() { echo "ok   $1"; }
fail() { echo "FAIL $1" >&2; fails=$((fails + 1)); }

# --- stubs --------------------------------------------------------------
mkdir -p "$TMP/bin"

# Stub gh: every CI run is green; release create/view succeed.
cat > "$TMP/bin/gh" <<'GH'
#!/usr/bin/env bash
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
        # The report writer is real: step 7 must produce a report with the
        # gate evidence, and a stub would hide a broken report.
        cp "$HERE/../tools/write_verification_report.py" tools/write_verification_report.py
        printf 'def test_stub():\n    assert True\n' > tests/test_stub.py
        # The gate names tests/test_release_force.sh (this very test). In the
        # throwaway repo it is a stub that succeeds, so it cannot recurse.
        printf '#!/usr/bin/env bash\nexit 0\n' > tests/test_release_force.sh
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

# run_sh DIR ARGS... : run the repo's release.sh, capture output + exit code.
#
# The throwaway repo's Python env has no pytest installed (the stub tests
# above are stubs, not real pytest tests). The real release.sh gate calls
# `python3 -m pytest tests/ -q`, so we stub the pytest MODULE (not the
# binary) by prepending a directory with a `pytest.py` that exits 0.
# The stub lives OUTSIDE the throwaway repo, so `git status` in the repo
# never sees it and preflight stays clean.
run_sh() {
    local dir="$1"; shift
    mkdir -p "$TMP/.pytest_stub"
    if [ ! -f "$TMP/.pytest_stub/pytest.py" ]; then
        printf 'import sys\nsys.exit(0)\n' > "$TMP/.pytest_stub/pytest.py"
    fi
    set +e
    OUT="$(cd "$dir" && PYTHONPATH="$TMP/.pytest_stub${PYTHONPATH:+:$PYTHONPATH}" bash scripts/release.sh "$@" 2>&1)"
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
   && git -C "$REPO" rev-parse -q --verify refs/tags/v0.0.1 >/dev/null \
   && grep -q "^Gate commands:" "$REPO/docs/v0.0.1-verification.md" \
   && grep -q "^Exit codes:" "$REPO/docs/v0.0.1-verification.md" \
   && (cd "$REPO" && sha256sum -c --status docs/v0.0.1-verification.md.sha256); then
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

# 6. Fail-closed gate: a failing check in the middle of the gate stops the
#    release. Resume mode runs the gate, so --force reaches it.
FAILING_STUB='#!/usr/bin/env python3\nraise SystemExit(1)\n'
make_midgate_failure() {
    (
        cd "$1"
        printf "$FAILING_STUB" > tools/check_mojibake.py
        # --force tags HEAD, so HEAD must stay the release commit: amend it.
        git add -A && git commit -q --amend -m "chore: release v0.0.1"
        git push -q -f origin main
    )
}
CLOSED_REPO="$TMP/repo_closed"
build_repo "$CLOSED_REPO" "$REAL_SH"
make_midgate_failure "$CLOSED_REPO"
run_sh "$CLOSED_REPO" 0.0.1 --force
if [ "$RC" -ne 0 ] && grep -q "gate failed" <<<"$OUT" \
   && ! git -C "$CLOSED_REPO" rev-parse -q --verify refs/tags/v0.0.1 >/dev/null; then
    pass "6. a failing check in the middle of the gate stops the release (no tag)"
else fail "6. mid-gate failure was not fatal (rc=$RC): $(tail -4 <<<"$OUT")"; fi

# 7. Mutation: put the gate subshell on the left of `||` again. The same
#    failing check must then get through, which is what scenario 6 detects.
GATE_GOOD='    ) > "$GATE_LOG" 2>&1
    GATE_RC=$?
'
GATE_BAD='    ) > "$GATE_LOG" 2>&1 || GATE_RC=$?
'
if ! python3 - "$REAL_SH" "$TMP/release_open.sh" "$GATE_GOOD" "$GATE_BAD" <<'PY'
import sys
src, dst, good, bad = sys.argv[1:5]
t = open(src).read()
if t.count(good) != 1:
    sys.exit(1)
open(dst, "w").write(t.replace(good, bad, 1))
PY
then
    fail "7. mutation: release.sh no longer ends the gate with 'GATE_RC=\$?'; update this test"
else
    OPEN_REPO="$TMP/repo_open"
    build_repo "$OPEN_REPO" "$TMP/release_open.sh"
    make_midgate_failure "$OPEN_REPO"
    run_sh "$OPEN_REPO" 0.0.1 --force
    if [ "$RC" -eq 0 ] && git -C "$OPEN_REPO" rev-parse -q --verify refs/tags/v0.0.1 >/dev/null; then
        pass "7. mutation (gate subshell left of ||) lets a failing check through; scenario 6 catches it"
    else
        fail "7. mutation not caught (rc=$RC): the mid-gate failure was fatal even with the gate left of ||"
    fi
fi

# 8. A commit on top of the release commit: --force must refuse. The old
#    check (the subject exists anywhere in history) tagged that commit.
TOP_REPO="$TMP/repo_top"
build_repo "$TOP_REPO" "$REAL_SH"
(
    cd "$TOP_REPO"
    printf 'later\n' > later.txt
    git add -A && git commit -q -m "feat: a change after the release commit"
    git push -q origin main
)
run_sh "$TOP_REPO" 0.0.1 --force
if [ "$RC" -eq 1 ] \
   && grep -q "HEAD is not the release commit" <<<"$OUT" \
   && grep -q "feat: a change after the release commit" <<<"$OUT" \
   && grep -q "chore: release v0.0.1" <<<"$OUT" \
   && ! git -C "$TOP_REPO" rev-parse -q --verify refs/tags/v0.0.1 >/dev/null; then
    pass "8. a commit on top of the release commit: --force refuses (no tag)"
else fail "8. --force tagged or mis-reported with a commit on top (rc=$RC): $(tail -4 <<<"$OUT")"; fi

# 9. Regeneration leaves an uncommitted file: --force must refuse.
STALE_REPO="$TMP/repo_stale"
build_repo "$STALE_REPO" "$REAL_SH"
(
    cd "$STALE_REPO"
    printf 'stale\n' > docs/STATE.md
    printf '#!/usr/bin/env python3\nopen("docs/STATE.md", "a").write("regenerated\\n")\n' > tools/gen_state_doc.py
    git add -A && git commit -q --amend -m "chore: release v0.0.1"
    git push -q -f origin main
)
run_sh "$STALE_REPO" 0.0.1 --force
if [ "$RC" -eq 1 ] \
   && grep -q "regeneration changed files that the release commit does not contain" <<<"$OUT" \
   && grep -q "docs/STATE.md" <<<"$OUT" \
   && ! git -C "$STALE_REPO" rev-parse -q --verify refs/tags/v0.0.1 >/dev/null; then
    pass "9. regeneration left docs/STATE.md uncommitted: --force refuses (no tag)"
else fail "9. --force tagged over an uncommitted regeneration (rc=$RC): $(tail -4 <<<"$OUT")"; fi

# 10. A nested release.sh inside the gate. The outer repo's
#     tests/test_release_force.sh (a stub everywhere else) runs a full
#     --force release in a second repo, in the middle of the outer gate.
NEST_B="$TMP/repo_nest_b"
build_repo "$NEST_B" "$REAL_SH"
NEST_A="$TMP/repo_nest_a"
build_repo "$NEST_A" "$REAL_SH"
(
    cd "$NEST_A"
    cat > tests/test_release_force.sh <<NESTED
#!/usr/bin/env bash
cd "$NEST_B" && bash scripts/release.sh 0.0.1 --force >/dev/null 2>&1
exit 0
NESTED
    git add -A && git commit -q --amend -m "chore: release v0.0.1"
    git push -q -f origin main
)
run_sh "$NEST_A" 0.0.1 --force
REPORT_A="$NEST_A/docs/v0.0.1-verification.md"
# The outer run records 8 freshness commands plus every gate line, once each.
# A nested run that shares the file adds its own records (or truncates the
# outer ones), so only an exact count shows the files are separate.
EXPECTED="$(python3 - "$REAL_SH" <<'PY'
import sys
t = open(sys.argv[1], encoding="utf-8").read()
gate = t.split("set -e\n", 1)[1].split(') > "$GATE_LOG"', 1)[0]
print(8 + sum(1 for l in gate.splitlines() if l.strip()))
PY
)"
GOT="$(awk '/^Gate commands:/{f=1;next} /^Exit codes:/{f=0} f&&/^ *[0-9]+\. /{n++} END{print n+0}' "$REPORT_A" 2>/dev/null)"
if [ "$RC" -eq 0 ] && [ -f "$REPORT_A" ] \
   && git -C "$NEST_B" rev-parse -q --verify refs/tags/v0.0.1 >/dev/null \
   && [ "$GOT" -eq "$EXPECTED" ]; then
    pass "10. a nested release.sh inside the gate leaves the outer record exact ($GOT commands)"
else fail "10. the outer record is not exact: $GOT commands, expected $EXPECTED (rc=$RC, nested tag: $(git -C "$NEST_B" tag 2>/dev/null))"; fi

# 11. Two runs, two record paths.
RUN_C="$TMP/repo_run_c"; RUN_D="$TMP/repo_run_d"
build_repo "$RUN_C" "$REAL_SH"; build_repo "$RUN_D" "$REAL_SH"
run_sh "$RUN_C" 0.0.1 --force; OUT_C="$OUT"
run_sh "$RUN_D" 0.0.1 --force; OUT_D="$OUT"
REC_C="$(sed -n 's/^  gate record: //p' <<<"$OUT_C")"; REC_D="$(sed -n 's/^  gate record: //p' <<<"$OUT_D")"
if [ -n "$REC_C" ] && [ -n "$REC_D" ] && [ "$REC_C" != "$REC_D" ] \
   && [ "$REC_C" != "/tmp/release-gate.rec" ] && [ "$REC_D" != "/tmp/release-gate.rec" ]; then
    pass "11. two runs use two different gate records ($(basename "$(dirname "$REC_C")") and $(basename "$(dirname "$REC_D")"))"
else fail "11. the two runs shared a gate record ('$REC_C' / '$REC_D')"; fi

if [ "$fails" -ne 0 ]; then echo "FAIL: $fails scenario(s) failed" >&2; exit 1; fi
echo "PASS"