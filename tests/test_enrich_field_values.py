"""enrich_field.py --only-value compares values with the snapshot.

The presence check (--check) cannot tell a wrong value from a right one.
These tests run the tool as a subprocess against a throwaway registry and a
throwaway snapshot, so they depend on no real data.
"""
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "enrich_field.py"


def run(tmp_path: Path, tree_value, snapshot_values):
    registry = tmp_path / "iso3166.json"
    registry.write_text(json.dumps({"countries": {"active": [
        {"alpha_2": "AA", "name": "Aland", "status": "officially-assigned",
         "tlds": tree_value},
    ]}}), encoding="utf-8")
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"tlds": snapshot_values}), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(TOOL), "--field", "tlds", "--only-value",
         "--registry", str(registry), "--snapshot", str(snapshot)],
        capture_output=True, text=True,
    )


def test_value_matches_snapshot(tmp_path):
    r = run(tmp_path, [".aa"], [".aa", ".bb"])
    assert r.returncode == 0, r.stderr


def test_list_order_does_not_matter(tmp_path):
    r = run(tmp_path, [".bb", ".aa"], [".aa", ".bb"])
    assert r.returncode == 0, r.stderr


def test_value_differs_in_content(tmp_path):
    r = run(tmp_path, [".aa", ".zz"], [".aa", ".bb"])
    assert r.returncode == 1
    # The diff names the code, the field, the tree value and the snapshot.
    assert "AA" in r.stderr
    assert "tlds" in r.stderr
    assert "'.zz'" in r.stderr
    assert "snapshot" in r.stderr
