"""tools/cross_language_derived.py::check_active_on also checks the key order.

Query 11 returns "277 keys, sorted" (docs/QUERIES.md). The cross-language check
compared the maps with `==`, which ignores order, so a surface that returned the
right answer in the wrong order passed. Only the Python surface is used here, so
this runs wherever the root suite runs (no node, go or cargo needed).
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "cross_language_consistency.json"


def _tool():
    spec = importlib.util.spec_from_file_location(
        "cross_language_derived", ROOT / "tools" / "cross_language_derived.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _python_active_on():
    sys.path.insert(0, str(ROOT / "wrappers" / "python"))
    from iso3166 import CountryRegistry

    date = json.loads(FIXTURE.read_text(encoding="utf-8"))["derived_queries"]["active_on"]["date"]
    return CountryRegistry().active_on(date)


def test_sorted_active_on_passes_the_check():
    d = _python_active_on()
    assert list(d) == sorted(d)
    assert _tool().check_active_on({"python": d}) == []


def test_unsorted_active_on_is_reported_even_when_the_map_is_equal():
    d = _python_active_on()
    shuffled = dict(reversed(list(d.items())))
    assert shuffled == d and list(shuffled) != list(d)  # equal as a map, different order
    bad = _tool().check_active_on({"python": shuffled})
    assert len(bad) == 1, bad
    assert "not sorted" in bad[0] and "python" in bad[0]
