"""enrich_independent.py: logic that does not depend on live ISO markup (v1.7.3)."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("enrich_independent", ROOT / "tools" / "enrich_independent.py")
ei = importlib.util.module_from_spec(_spec)
sys.modules["enrich_independent"] = ei
_spec.loader.exec_module(ei)

NOW = "2026-01-01T00:00:00Z"


def _entry(code, status="officially-assigned", independent=False):
    return {"alpha_2": code, "status": status, "independent": independent}


def _reg(active, withdrawn=()):
    return {"countries": {"active": list(active), "withdrawn": [_entry(c) for c in withdrawn]}}


def _write(tmp_path, reg):
    p = tmp_path / "iso3166.json"
    p.write_text(json.dumps(reg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p, tmp_path / "snap.json"


def _pages(mapping):
    def fetch(code):
        if code not in mapping:
            raise LookupError("HTTP 404")
        return mapping[code]
    return fetch


YES, NO = "<td>Independent</td><td>Yes</td>", "<td>Independent</td><td>No</td>"


def test_withdrawn_table_covers_exactly_the_registry_codes():
    reg = json.loads((ROOT / "iso3166.json").read_text(encoding="utf-8"))
    codes = {e["alpha_2"] for e in reg["countries"]["withdrawn"]}
    assert codes == ei.WITHDRAWN_TRUE | ei.WITHDRAWN_FALSE
    assert (len(ei.WITHDRAWN_TRUE), len(ei.WITHDRAWN_FALSE)) == (11, 14)


def test_parse_independent_assumed_format():
    assert ei.parse_independent(YES) is True
    assert ei.parse_independent(NO) is False
    assert ei.parse_independent("<html>app shell, no data</html>") is None
    assert ei.parse_independent("Independent: Yes ... Independent: No") is None


def test_overrides_and_unresolved_need_no_fetch():
    reg = _reg([_entry("XK", "user-assigned"), _entry("TW", independent=True),
                _entry("EU", "exceptionally-reserved", True), _entry("UK", "exceptionally-reserved")])
    def boom(code):
        raise AssertionError(f"fetched {code}")
    plan = ei.resolve(reg, boom)
    assert {c: i["value"] for c, i in plan["active"].items()} == {"XK": True, "TW": False, "EU": False}
    assert plan["unresolved"] == ["UK"] and not plan["failures"]


def test_write_applies_values_and_snapshot(tmp_path):
    reg = _reg([_entry("AT"), _entry("AQ", independent=True), _entry("XK", "user-assigned")], ["SU", "AI"])
    rp, sp = _write(tmp_path, reg)
    out = []
    rc = ei.cmd_run(rp, sp, _pages({"AT": YES, "AQ": NO}), write=True, now=NOW, out=out.append)
    assert rc == 0
    got = json.loads(rp.read_text())["countries"]
    assert {e["alpha_2"]: e["independent"] for e in got["active"]} == {"AT": True, "AQ": False, "XK": True}
    assert {e["alpha_2"]: e["independent"] for e in got["withdrawn"]} == {"SU": True, "AI": False}
    snap = json.loads(sp.read_text())
    assert snap["meta"]["extracted_at"] == NOW
    assert snap["entries"]["AT"] == {"value": True, "source_url": ei.OBP_URL.format(code="AT"), "extracted_at": NOW}
    assert snap["entries"]["XK"]["source_url"] is None and "override" in snap["entries"]["XK"]
    assert ei.cmd_check(rp, sp, out=out.append) == 0


def test_any_failure_writes_nothing(tmp_path):
    reg = _reg([_entry("AT"), _entry("BE")])
    rp, sp = _write(tmp_path, reg)
    before = rp.read_bytes()
    rc = ei.cmd_run(rp, sp, _pages({"AT": YES, "BE": "<html>shell</html>"}), write=True, now=NOW, out=lambda m: None)
    assert rc == 1 and rp.read_bytes() == before and not sp.exists()


def test_unknown_withdrawn_code_aborts(tmp_path):
    rp, sp = _write(tmp_path, _reg([_entry("AT")], ["ZZ"]))
    assert ei.cmd_run(rp, sp, _pages({"AT": YES}), write=True, now=NOW, out=lambda m: None) == 1
    assert not sp.exists()


def test_network_failure_exits_2_and_writes_nothing(tmp_path):
    rp, sp = _write(tmp_path, _reg([_entry("AT")]))
    before = rp.read_bytes()
    def down(code):
        raise ei.NetworkError("dns")
    out = []
    assert ei.cmd_run(rp, sp, down, write=True, now=NOW, out=out.append) == 2
    assert rp.read_bytes() == before and not sp.exists() and "no changes made" in out[0]


def test_dry_run_prints_distribution_and_writes_nothing(tmp_path):
    rp, sp = _write(tmp_path, _reg([_entry("AT"), _entry("AQ", independent=True), _entry("BE", independent=True)]))
    before = rp.read_bytes()
    out = []
    assert ei.cmd_run(rp, sp, _pages({"AT": YES, "AQ": NO, "BE": YES}), write=False, now=NOW, out=out.append) == 0
    assert "1 would become true, 1 would become false, 1 unchanged" in out[0]
    assert rp.read_bytes() == before and not sp.exists()


def test_check_missing_and_empty_snapshot_warn_and_pass(tmp_path):
    rp, sp = _write(tmp_path, _reg([_entry("AT")]))
    warned = []
    assert ei.cmd_check(rp, sp, out=lambda m: None, warn=warned.append) == 0   # missing file
    sp.write_text(json.dumps({"meta": {}, "entries": {}}))
    assert ei.cmd_check(rp, sp, out=lambda m: None, warn=warned.append) == 0   # empty
    assert warned == [ei.EMPTY_WARNING] * 2


def test_check_populated_mismatch_fails(tmp_path):
    rp, sp = _write(tmp_path, _reg([_entry("AT"), _entry("BE")], ["SU"]))
    ei.cmd_run(rp, sp, _pages({"AT": YES, "BE": YES}), write=True, now=NOW, out=lambda m: None)
    reg = json.loads(rp.read_text())
    reg["countries"]["active"][0]["independent"] = False     # AT drifts from the snapshot
    reg["countries"]["withdrawn"][0]["independent"] = False   # SU drifts from the table
    rp.write_text(json.dumps(reg, indent=2, sort_keys=True) + "\n")
    out = []
    assert ei.cmd_check(rp, sp, out=out.append) == 1
    text = "\n".join(out)
    assert "AT:" in text and "withdrawn SU" in text
