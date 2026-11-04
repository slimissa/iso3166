"""validate.py rejects club ranges that overlap, touch, or are misordered.

The rules live in _check_membership (integrity layer). They had no test:
the audit's first reading was that overlap was not checked at all, and it
took reading the function to find that it is. These cases pin it down.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import validate  # noqa: E402


def errors(ranges):
    r = validate.LayerResult("integrity")
    validate._check_membership(r, "active[0] (AA)", "eu_membership", ranges)
    return r.errors


def rg(frm, to):
    return {"from": frm, "to": to}


def test_disjoint_ranges_pass():
    assert errors([rg("1958-01-01", "1973-12-31"), rg("1980-01-01", None)]) == []


def test_ranges_on_consecutive_days_pass():
    assert errors([rg("1958-01-01", "1973-12-31"), rg("1974-01-01", None)]) == []


def test_overlapping_ranges_fail_and_name_the_conflict():
    e = errors([rg("1958-01-01", "1980-12-31"), rg("1970-01-01", "1990-12-31")])
    assert len(e) == 1
    assert "overlaps" in e[0] and "1980-12-31" in e[0] and "1970-01-01" in e[0]


def test_ranges_sharing_a_day_fail():
    # Ranges are inclusive: ending on the day the next one starts overlaps.
    e = errors([rg("1958-01-01", "1973-12-31"), rg("1973-12-31", None)])
    assert any("overlaps" in x for x in e)


def test_out_of_order_ranges_fail():
    e = errors([rg("1990-01-01", "1999-12-31"), rg("1958-01-01", "1970-12-31")])
    assert any("out of order" in x for x in e)


def test_a_range_after_an_open_ended_one_fails():
    e = errors([rg("1958-01-01", None), rg("1990-01-01", None)])
    assert any("open-ended" in x for x in e)


def test_an_inverted_range_fails():
    e = errors([rg("2030-01-01", "1958-01-01")])
    assert any("ends before it starts" in x for x in e)


def test_validate_exits_nonzero_on_overlapping_ranges_in_the_registry(tmp_path):
    reg = json.loads((ROOT / "iso3166.json").read_text(encoding="utf-8"))
    de = next(e for e in reg["countries"]["active"] if e["alpha_2"] == "DE")
    de["eu_membership"] = [rg("1958-01-01", "1980-12-31"), rg("1970-01-01", None)]
    path = tmp_path / "iso3166.json"
    path.write_text(json.dumps(reg), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate.py"), str(path),
         "--only", "integrity"],
        capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "overlaps or is out of order" in r.stdout + r.stderr
