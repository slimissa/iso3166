"""The malformed-date contract (v1.12.5), per surface: silent failures are errors.

Before v1.12.5 the dated queries (`is_active_on` and the four club `*_at`
queries) answered `false` for a malformed date. The CLI exited 2 on the same
input, so the library and the CLI disagreed.

The 8 malformed inputs x 5 queries live in the fixture
(`derived_queries.error_cases`, written by tools/gen_consistency_fixture.py)
and are checked on every surface by tools/cross_language_derived.py. This
file runs them per surface: Python, JavaScript, Go, Rust and the CLI. A
surface whose toolchain is not installed is skipped, never passed.

The Python-only behaviour (what is converted, what raises) is in
test_python_datetime_conversion.py and test_api_misuse.py. This file needs
neither pandas nor a Python-specific type: it runs without either.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "wrappers" / "python"))

import cross_language_derived as xl  # noqa: E402

ERROR_CASES = xl.load_error_cases()
TOOLS = {"javascript": "node", "go": "go", "rust": "cargo"}
QUERIES = (
    "is_active_on", "is_eu_member_at", "is_eea_member_at",
    "is_eurozone_member_at", "is_in_customs_union_at",
)


def test_fixture_has_8_inputs_for_each_of_5_queries():
    assert len(ERROR_CASES) == 40
    assert {c["query"] for c in ERROR_CASES} == set(QUERIES)
    assert len({c["args"][1] for c in ERROR_CASES}) == 8


@pytest.mark.parametrize("surface", list(xl.ERROR_SURFACES))
def test_malformed_date_fails_loudly(surface):
    tool = TOOLS.get(surface)
    if tool and not shutil.which(tool):
        pytest.skip(f"{tool} is not installed")
    failures = xl.ERROR_SURFACES[surface](ERROR_CASES)
    assert not failures, "\n".join(failures)
