#!/usr/bin/env bash
# tools/check_cli_agreement.sh
#
# The repo CLI (tools/iso3166_cli.py) and the packaged CLI
# (wrappers/python/iso3166/cli.py) must print the same bytes for --raw.
# Before v1.12.6 an empty list printed one line from the packaged CLI and
# none from the repo CLI (29 vs 28 lines for `list --region Oceania --raw tlds`).
#
# The packaged CLI is run from the source tree (PYTHONPATH), not through
# bin/iso3166: bin/iso3166 falls back to the repo CLI when `iso3166` is not
# installed, which would compare the repo CLI with itself.
#
# Exit codes: 0 same bytes in every case; 1 any difference; 2 cannot run.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2

repo_cli()     { python3 tools/iso3166_cli.py "$@"; }
packaged_cli() { PYTHONPATH=wrappers/python python3 -m iso3166.cli "$@"; }

CASES=(
    "list --region Oceania --raw tlds"
    "list --region Oceania --raw borders"
    "lookup AQ --raw borders"
    "lookup JP --raw borders"
    "lookup EU --raw official_name"
    "list --raw official_name"
)

fail=0
for c in "${CASES[@]}"; do
    # shellcheck disable=SC2086
    packaged_cli $c > /tmp/cli-agree.packaged.$$ 2>/dev/null; prc=$?
    # shellcheck disable=SC2086
    repo_cli $c > /tmp/cli-agree.repo.$$ 2>/dev/null; rrc=$?
    if [ "$prc" -ne 0 ] || [ "$rrc" -ne 0 ] || [ ! -s /tmp/cli-agree.packaged.$$ ]; then
        echo "FAIL: $c: packaged exit $prc, repo exit $rrc, or empty output (cannot compare)"
        fail=1
    elif cmp -s /tmp/cli-agree.packaged.$$ /tmp/cli-agree.repo.$$; then
        echo "OK:   $c ($(wc -l < /tmp/cli-agree.repo.$$) lines)"
    else
        echo "FAIL: $c: packaged $(wc -l < /tmp/cli-agree.packaged.$$) lines, repo $(wc -l < /tmp/cli-agree.repo.$$) lines"
        fail=1
    fi
done
rm -f /tmp/cli-agree.packaged.$$ /tmp/cli-agree.repo.$$
exit "$fail"
