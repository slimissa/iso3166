#!/usr/bin/env bash
# examples/run_all.sh: run every example under examples/.
#
#   bash examples/run_all.sh            run each example, print its output
#   bash examples/run_all.sh --check    diff each output against its
#                                       expected_output.txt; exit 1 on any
#                                       difference or missing file
#   bash examples/run_all.sh --write    regenerate every expected_output.txt
#
# An example is a directory under examples/ that holds an analyze.py.
# PYTHON overrides the interpreter (default python3).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
py="${PYTHON:-python3}"
mode="${1:-run}"
case "$mode" in
    run|--check|--write) ;;
    *) echo "usage: run_all.sh [--check|--write]" >&2; exit 2 ;;
esac

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

found=0
bad=0
for dir in "$here"/*/; do
    [ -f "$dir/analyze.py" ] || continue
    name="$(basename "$dir")"
    found=$((found + 1))
    out="$tmp/$name.out"
    if ! "$py" "$dir/analyze.py" > "$out"; then
        echo "FAIL $name: analyze.py exited non-zero" >&2
        bad=$((bad + 1))
        continue
    fi
    case "$mode" in
        run)
            echo "=== $name ==="
            cat "$out"
            ;;
        --write)
            cp "$out" "$dir/expected_output.txt"
            echo "wrote examples/$name/expected_output.txt"
            ;;
        --check)
            if [ ! -f "$dir/expected_output.txt" ]; then
                echo "FAIL $name: no expected_output.txt" >&2
                bad=$((bad + 1))
            elif diff -u "$dir/expected_output.txt" "$out" > "$tmp/$name.diff"; then
                echo "ok   $name"
            else
                echo "FAIL $name: output differs from expected_output.txt" >&2
                cat "$tmp/$name.diff" >&2
                bad=$((bad + 1))
            fi
            ;;
    esac
done

if [ "$found" -eq 0 ]; then
    echo "FAIL: no example found under $here" >&2
    exit 1
fi
[ "$bad" -eq 0 ]
