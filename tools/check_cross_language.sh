#!/usr/bin/env bash
#
# tools/check_cross_language.sh
#
# Run the same country lookup through all four language wrappers and
# verify they produce byte-identical output. This is the executable form
# of the ecosystem's central claim: "the JSON is the contract, and every
# wrapper agrees on what it says."
#
# Usage:
#   bash tools/check_cross_language.sh [CODE ...]
#
# Default code: US
#
# Exit codes:
#   0  All wrappers agreed on every code.
#   1  At least one code produced different output across wrappers.
#   2  Usage error or missing prerequisite.
#   3  A wrapper failed to run (build error, missing toolchain, etc.).
#
# Environment:
#   SKIP_BUILD=1    Skip the Rust/Go build step. Use when the binaries
#                   are already built and you want a fast re-run.
#   PY=python3      Override the Python interpreter.
#
set -euo pipefail

# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

PY="${PY:-python3}"
SKIP_BUILD="${SKIP_BUILD:-}"

CODES=("$@")
if [ ${#CODES[@]} -eq 0 ]; then
    CODES=("US")
fi

# ---------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------

require_cmd() {
    local cmd="$1"
    local why="$2"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "error: '$cmd' not found; required for $why" >&2
        exit 2
    fi
}

require_cmd "$PY" "the Python wrapper"
require_cmd node "the JavaScript wrapper"
require_cmd go   "the Go wrapper"
require_cmd cargo "the Rust wrapper"

# ---------------------------------------------------------------------
# Wrapper spot-checks
#
# Each function prints exactly one line: "ALPHA2 ALPHA3 NUMERIC NAME".
# Any deviation (extra output, different order, different spacing) is a
# failure, because the whole point of this script is byte-identity.
# ---------------------------------------------------------------------

run_python() {
    local code="$1"
    # Prefer the installed console script; fall back to the module.
    if command -v iso3166 >/dev/null 2>&1 && [ "$(command -v iso3166)" != "$HERE/bin/iso3166" ]; then
        "$PY" -c "
import sys
from iso3166 import CountryRegistry
c = CountryRegistry().active(sys.argv[1])
if c is None:
    sys.exit(1)
print(c.alpha_2, c.alpha_3, c.numeric, c.name)
" "$code"
    else
        "$PY" -c "
import sys
sys.path.insert(0, '$HERE/wrappers/python')
from iso3166 import CountryRegistry
c = CountryRegistry().active(sys.argv[1])
if c is None:
    sys.exit(1)
print(c.alpha_2, c.alpha_3, c.numeric, c.name)
" "$code"
    fi
}

run_javascript() {
    local code="$1"
    node -e "
const { CountryRegistry } = require('$HERE/wrappers/javascript');
const c = new CountryRegistry().active(process.argv[1]);
if (!c) process.exit(1);
console.log(c.alpha_2, c.alpha_3, c.numeric, c.name);
" "$code"
}

run_go() {
    local code="$1"
    ( cd "$HERE/wrappers/go" && go run ./cmd/lookup "$code" )
}

run_rust() {
    local code="$1"
    ( cd "$HERE/wrappers/rust" && cargo run --quiet --bin lookup "$code" )
}

# ---------------------------------------------------------------------
# Build step
# ---------------------------------------------------------------------

if [ -z "$SKIP_BUILD" ]; then
    echo "Building Go wrapper..." >&2
    ( cd "$HERE/wrappers/go" && go build ./... ) || {
        echo "error: go build failed" >&2
        exit 3
    }

    echo "Building Rust wrapper..." >&2
    ( cd "$HERE/wrappers/rust" && cargo build --quiet ) || {
        echo "error: cargo build failed" >&2
        exit 3
    }
fi

# ---------------------------------------------------------------------
# Run the checks
# ---------------------------------------------------------------------

WRAPPERS=(python javascript go rust)
declare -A RUNNERS=(
    [python]=run_python
    [javascript]=run_javascript
    [go]=run_go
    [rust]=run_rust
)

failures=0

# Column widths for the diagnostic table.
W_LANG=10

for code in "${CODES[@]}"; do
    echo ""
    echo "== $code =="

    # Collect outputs into an associative array.
    declare -A outputs
    declare -A status

    for lang in "${WRAPPERS[@]}"; do
        runner="${RUNNERS[$lang]}"
        if out="$("$runner" "$code" 2>/dev/null)"; then
            outputs[$lang]="$out"
            status[$lang]="ok"
        else
            outputs[$lang]="(failed)"
            status[$lang]="FAILED"
        fi
    done

    # Print the table.
    for lang in "${WRAPPERS[@]}"; do
        printf "  %-${W_LANG}s %s\n" "$lang" "${outputs[$lang]}"
    done

    # Compare. Pick the first wrapper as the reference, then require the
    # rest to match it exactly.
    reference="${outputs[python]}"
    reference_ok="${status[python]}"

    mismatch=0
    if [ "$reference_ok" != "ok" ]; then
        mismatch=1
        echo "  >> Python failed; cannot establish a reference" >&2
    fi

    for lang in "${WRAPPERS[@]}"; do
        [ "$lang" = "python" ] && continue
        if [ "${status[$lang]}" != "ok" ]; then
            mismatch=1
            echo "  >> $lang failed to run" >&2
            continue
        fi
        if [ "${outputs[$lang]}" != "$reference" ]; then
            mismatch=1
            echo "  >> $lang disagrees with python" >&2
            echo "     python: $reference" >&2
            echo "     $lang:  ${outputs[$lang]}" >&2
        fi
    done

    if [ "$mismatch" = "0" ]; then
        echo "  -> all four agree"
    else
        failures=$((failures + 1))
    fi

    unset outputs status
done

echo ""
if [ "$failures" -gt 0 ]; then
    echo "FAIL: $failures code(s) disagreed across wrappers"
    exit 1
fi

echo "OK: all codes agree across Python, JavaScript, Go, and Rust"
exit 0
