"""The worked-examples index in docs/QUERIES.md must equal the fixture.

docs/QUERIES.md ("Worked examples index") lists every derived-query example
as a table row. tests/cross_language_consistency.json holds the same cases
under `derived_queries.cases`, and every wrapper and the CLI are checked
against that fixture. Nothing tied the two together: the document could
drift from the cases the wrappers are actually tested on.

This test parses both and requires them to be equal: same length, same
order, and for every position the same query name, the same argument tuple
and the same expected value. On a mismatch it prints the first five
differences.

ISO3166_QUERIES_MD and ISO3166_FIXTURE override the two input paths. They
exist so tools outside the repo (test-gate-index-fixture.sh) can point the
test at mutated copies; the gate never sets them.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERIES_MD = Path(os.environ.get("ISO3166_QUERIES_MD", ROOT / "docs" / "QUERIES.md"))
FIXTURE = Path(os.environ.get("ISO3166_FIXTURE", ROOT / "tests" / "cross_language_consistency.json"))

INDEX_HEADING = "## Worked examples index"
# | E12 | `method` | `[args as JSON]` | `expected as JSON` | ...
ROW_RE = re.compile(r"^\| E(\d+) \| `([^`]+)` \| `(.*?)` \| `(.*?)` \|")


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _index_section(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index(INDEX_HEADING)
    except ValueError:
        raise AssertionError(f"{QUERIES_MD}: no {INDEX_HEADING!r} heading") from None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start + 1:end]


def parse_index() -> list[tuple[int, str, tuple, str]]:
    """Return (E-number, query, args tuple, canonical expected) per index row."""
    rows = []
    for line in _index_section(QUERIES_MD.read_text(encoding="utf-8")):
        if not line.startswith("| E"):
            continue
        m = ROW_RE.match(line)
        assert m, f"{QUERIES_MD}: unparseable index row: {line[:100]!r}"
        n, query, args, expected = m.groups()
        rows.append((int(n), query, tuple(json.loads(args)), _canon(json.loads(expected))))
    return rows


def parse_fixture() -> list[tuple[str, tuple, str]]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = data["derived_queries"]["cases"]
    return [(c["query"], tuple(c["args"]), _canon(c["expected"])) for c in cases]


def test_index_rows_are_numbered_without_gaps():
    numbers = [n for n, *_ in parse_index()]
    assert numbers, "the index has no rows"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"index row numbers are not E1..E{len(numbers)} in order: "
        f"first break at position {next(i for i, n in enumerate(numbers, 1) if n != i)}"
    )


def test_index_matches_fixture():
    index = [row[1:] for row in parse_index()]
    fixture = parse_fixture()

    diffs: list[str] = []
    if len(index) != len(fixture):
        diffs.append(f"length: index has {len(index)} rows, fixture has {len(fixture)} cases")
    for pos, (a, b) in enumerate(zip(index, fixture), 1):
        if a != b:
            diffs.append(f"position {pos}:\n      index   {a}\n      fixture {b}")
    for pos in range(min(len(index), len(fixture)) + 1, max(len(index), len(fixture)) + 1):
        side, row = ("index", index[pos - 1]) if len(index) >= pos else ("fixture", fixture[pos - 1])
        diffs.append(f"position {pos}: only in {side}: {row}")

    assert not diffs, (
        f"docs/QUERIES.md index and the fixture's derived_queries differ "
        f"({len(diffs)} difference(s); first {min(5, len(diffs))}):\n  "
        + "\n  ".join(diffs[:5])
    )
