"""validate.py's seventh layer, snapshot-value.

Before v1.12.6 `validate.py` printed "Summary: 6 OK" without looking at
the snapshot-backed fields other than currency_codes (and borders, as an
alpha-2 resolvability check). enrich_field.py --only-value did, but
validate.py never called it. These tests write a registry with ONE wrong
value per field and require `validate.py --only snapshot-value` to exit 1,
naming the entry and the field.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "validate.py"
REGISTRY = ROOT / "iso3166.json"

# (field, a wrong value). None of these is in the field's snapshot, and
# none is an active alpha-2 code.
WRONG = {
    "currency_codes": ["ZZZ"],
    "calling_codes": ["+9999"],
    "tlds": [".not-a-tld"],
    "languages": ["not-a-language"],
    "borders": ["ZZ"],
    "subregion": "Atlantis",
    "intermediate_region": "Atlantis",
}
# Any active entry will do: the mutation sets a non-null value, which the
# layer compares even where the committed value is null.
CODE = "FR"


def _run(path: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), str(path), "--only", "snapshot-value",
         *extra],
        capture_output=True, text=True, cwd=ROOT,
    )


def test_layer_registered_and_fixture_covers_every_field():
    """The layer sits between cross-reference and ground-truth, and WRONG
    names exactly the seven fields enrich_field.FIELDS has."""
    sys.path.insert(0, str(ROOT / "tools"))
    import enrich_field
    import validate

    names = list(validate.LAYER_NAMES)
    assert names.index("snapshot-value") == names.index("cross-reference") + 1
    assert names.index("snapshot-value") + 1 == names.index("ground-truth")

    assert sorted(WRONG) == sorted(enrich_field.FIELDS)
    assert len(WRONG) == 7


@pytest.mark.parametrize("field", sorted(WRONG))
def test_one_wrong_value_fails(field, tmp_path):
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entry = next(e for e in reg["countries"]["active"]
                 if e["alpha_2"] == CODE)
    entry[field] = copy.deepcopy(WRONG[field])
    bad = tmp_path / "iso3166.json"
    bad.write_text(json.dumps(reg), encoding="utf-8")

    r = _run(bad)
    assert r.returncode == 1, (r.stdout, r.stderr)
    assert CODE in r.stdout and field in r.stdout, r.stdout


def test_committed_tree_passes():
    r = _run(REGISTRY)
    assert r.returncode == 0, (r.stdout, r.stderr)
