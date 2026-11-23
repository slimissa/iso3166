"""The number of collected tests is pinned in tests/test_counts.json.

A test that stops being collected (a rename that breaks discovery, a
syntax error swallowed by a skip, a parametrize list that came out empty)
fails nothing: pytest just reports fewer tests. This test compares what
`pytest --collect-only` finds, per file and in total, with the pin, so a
silent loss is a loud failure and a new test is a deliberate edit.

After adding or removing a test, regenerate the pin and commit it with the
change:

    python3 tests/test_counts.py --write
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN = Path(__file__).resolve().parent / "test_counts.json"


def collected() -> dict:
    """Run `pytest --collect-only` on tests/ and count node ids per file."""
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q",
         "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
    files: dict[str, int] = {}
    for line in p.stdout.splitlines():
        if "::" in line and not line.startswith(" "):
            name = line.split("::", 1)[0]
            files[name] = files.get(name, 0) + 1
    return {"total": sum(files.values()), "files": dict(sorted(files.items()))}


def test_collected_tests_match_the_pin():
    pin = json.loads(PIN.read_text(encoding="utf-8"))
    now = collected()
    assert now["files"] == pin["files"], (
        "collected tests per file differ from tests/test_counts.json; "
        "if the change is intended, run: python3 tests/test_counts.py --write"
    )
    assert now["total"] == pin["total"]
    assert pin["total"] == sum(pin["files"].values()), "the pin disagrees with itself"


if __name__ == "__main__":
    if sys.argv[1:] != ["--write"]:
        sys.exit("usage: python3 tests/test_counts.py --write")
    PIN.write_text(json.dumps(collected(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {PIN.relative_to(ROOT)}")
