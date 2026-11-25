"""tools/check_introduced_evidence.py and the ledger tools/introduced_evidence.json.

The ledger has one row per key of tools/introduced_snapshot.json. Only an
iso_primary row may be adopted, and an adopted date must equal iso3166.json
(docs/decisions/introduced-evidence.md). Each rule has a negative test on a
copy of the real ledger.
"""
import copy
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_introduced_evidence as cie  # noqa: E402

TODAY = date(2026, 11, 25)
LEDGER = json.loads((ROOT / "tools/introduced_evidence.json").read_text(encoding="utf-8"))
SNAPSHOT = json.loads((ROOT / "tools/introduced_snapshot.json").read_text(encoding="utf-8"))
TREE = json.loads((ROOT / "iso3166.json").read_text(encoding="utf-8"))
LIST_REASON = "maintainer list; ISO 3166:1974 text not yet obtained"
SHA = "a" * 64


def _list_1974() -> set:
    src = (ROOT / "tools/build_introduced_snapshot.py").read_text(encoding="utf-8")
    i = src.index("LIST_1974 = [")
    return set(re.findall(r'"([A-Z]{2})"', src[i:src.index("]", i)]))


def _row(ledger, code):
    return next(r for r in ledger["rows"] if r["code"] == code)


def _problems(ledger=LEDGER, tree=TREE, today=TODAY):
    return cie.problems(ledger, SNAPSHOT, tree, today)


def test_the_ledger_passes():
    assert _problems() == []
    assert cie.main(["--root", str(ROOT), "--today", date.today().isoformat()]) == 0


def test_one_row_per_snapshot_code():
    assert [r["code"] for r in LEDGER["rows"]] == sorted(SNAPSHOT["data"])
    assert len(LEDGER["rows"]) == 275


def test_every_1974_list_date_is_an_inference_with_its_reason():
    """D5: none of the 161 LIST_1974 dates hides behind the 1974 date."""
    listed = [r for r in LEDGER["rows"] if r["current"] == "1974-09-15"]
    assert len(listed) == 161
    assert {r["code"] for r in listed} <= _list_1974()
    for r in listed:
        assert (r["class"], r["verdict"], r["reason"]) == ("inference", "unconfirmed", LIST_REASON), r["code"]


def test_only_iso_primary_rows_are_adopted():
    for r in LEDGER["rows"]:
        if r["verdict"] == "adopted":
            assert r["class"] == "iso_primary", r["code"]


def test_every_dated_value_has_a_row_that_says_where_it_came_from():
    for r in LEDGER["rows"]:
        if r["current"] is not None:
            assert r["candidate"] == r["current"], r["code"]
            assert r["class"] in ("iso_primary", "inference", "lead_only"), r["code"]


def test_ledger_counts():
    c = Counter((r["class"], r["verdict"]) for r in LEDGER["rows"])
    assert sum(c.values()) == 275
    assert c[("ma_member", "adopted")] == 0


def _broken(change):
    led = copy.deepcopy(LEDGER)
    change(led)
    return _problems(led)


def _primary(led, code="SS", date_="2011-08-09"):
    r = _row(led, code)
    r.update({"class": "iso_primary", "verdict": "adopted", "candidate": date_,
              "doc": {"title": "ISO OBP code page", "number": None, "date": date_,
                      "urls": ["https://www.iso.org/obp/ui/#iso:code:3166:" + code],
                      "locator": "Change history", "sha256": SHA, "retrieved": "test"}})
    return r


@pytest.mark.parametrize("change, expect", [
    (lambda led: led.pop("rows"), "ledger has no `rows` list"),
    (lambda led: led["rows"].pop(0), "missing ['AD']"),
    (lambda led: led["rows"].insert(1, copy.deepcopy(led["rows"][0])), "duplicated ['AD']"),
    (lambda led: led["rows"].reverse(), "not one per snapshot code in sorted order"),
    (lambda led: _row(led, "AD").pop("reason"), "AD: keys"),
    (lambda led: _row(led, "AD").update(extra=1), "AD: keys"),
    (lambda led: _row(led, "AD").update(candidate="1974-9-15"), "AD: candidate '1974-9-15' is not null or YYYY-MM-DD"),
    (lambda led: _row(led, "AD").update({"class": "primary"}), "AD: class 'primary' not in"),
    (lambda led: _row(led, "AD").update(verdict="ok"), "AD: verdict 'ok' not in"),
    (lambda led: _row(led, "AD").update(reason=" "), "AD: reason is empty"),
    (lambda led: _row(led, "BA").update(doc={"title": "x"}), "BA: doc keys are not"),
    (lambda led: _row(led, "AD").update(current="1974-09-16"), "AD: current '1974-09-16' != snapshot '1974-09-15'"),
    (lambda led: _row(led, "AD").update(verdict="adopted"), "AD: adopted with class inference"),
    (lambda led: _row(led, "SS").update(verdict="adopted", **{"class": "ma_member"}), "SS: adopted with class ma_member"),
    (lambda led: _row(led, "AX").update(verdict="adopted"), "AX: adopted with class lead_only"),
    (lambda led: _primary(led)["doc"].update(sha256=None), "SS: iso_primary needs doc"),
    (lambda led: _primary(led)["doc"].update(urls=[]), "SS: iso_primary needs doc"),
    (lambda led: _primary(led, "SS", "2011-07-09"), "SS: adopted 2011-07-09 != iso3166.json introduced '2011-08-09'"),
    (lambda led: _primary(led, "SU", "1974-09-15"), "SU: adopted, but SU is not an active entry"),
    (lambda led: _primary(led).update(candidate=None), "SS: adopted with no candidate"),
    (lambda led: _row(led, "AD").update(verdict="conflict"), "AD: conflict, but candidate equals current"),
    (lambda led: _row(led, "AD").update(recheck_date="2026-11-24"), "AD: recheck_date 2026-11-24 has passed"),
    (lambda led: _row(led, "AD").update(recheck_date="soon"), "AD: recheck_date 'soon' is not YYYY-MM-DD"),
], ids=["no-rows", "missing-row", "duplicate-row", "unsorted", "missing-key", "extra-key", "bad-date",
        "bad-class", "bad-verdict", "empty-reason", "bad-doc", "current-drift", "adopted-inference",
        "adopted-ma-member", "adopted-lead", "primary-no-sha", "primary-no-url", "adopted-differs-from-tree",
        "adopted-not-active", "adopted-no-candidate", "conflict-equal", "recheck-passed", "recheck-malformed"])
def test_each_rule_is_enforced(change, expect):
    found = _broken(change)
    assert any(expect in p for p in found), found


def test_a_well_formed_primary_adoption_that_matches_the_tree_passes():
    led = copy.deepcopy(LEDGER)
    _primary(led)
    assert _problems(led) == []


def test_main_exit_codes(tmp_path):
    for name in ("tools/introduced_snapshot.json", "iso3166.json"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())
    assert cie.main(["--root", str(tmp_path), "--today", "2026-11-25"]) == 2
    led = copy.deepcopy(LEDGER)
    _row(led, "AD").update(verdict="adopted")
    (tmp_path / "tools/introduced_evidence.json").write_text(json.dumps(led), encoding="utf-8")
    assert cie.main(["--root", str(tmp_path), "--today", "2026-11-25"]) == 1


def test_the_generator_takes_exactly_the_adopted_iso_primary_rows():
    """build_introduced_snapshot.py step 2 reads adopted iso_primary rows and nothing else."""
    adopted = {r["code"]: r["candidate"] for r in LEDGER["rows"]
               if r["class"] == "iso_primary" and r["verdict"] == "adopted"}
    meta = SNAPSHOT["meta"]
    assert meta["iso_primary_codes"] == sorted(adopted)
    assert meta["counts"]["active_from_iso_primary"] == len(adopted)
    for code, d in adopted.items():
        assert SNAPSHOT["data"][code] == d, code


def test_the_obp_adoptions_cite_the_harvest_page_and_an_assignment_entry():
    """D7: only an assignment entry dates a code; never the 2011-12-13 alignment entry."""
    for r in LEDGER["rows"]:
        if r["class"] != "iso_primary":
            continue
        assert r["quote_ref"].split(" ", 1)[1] in ("Assign code elements", "Add new entry"), r["code"]
        assert "align ISO 3166-1 and ISO 3166-2" not in r["doc"]["locator"], r["code"]
        assert r["doc"]["urls"] == [f"https://www.iso.org/obp/ui/#iso:code:3166:{r['code']}"]
