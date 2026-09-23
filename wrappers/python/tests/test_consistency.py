"""
Cross-language consistency tests.

Reads tests/cross_language_consistency.json (three levels up from this
file) and asserts the Python wrapper satisfies every case. The same
fixture is read by the JavaScript, Go, and Rust suites.
"""
import json
from pathlib import Path

import pytest

from iso3166 import CountryRegistry


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[3] / "tests" / "cross_language_consistency.json"


@pytest.fixture(scope="module")
def fixture():
    return json.loads(_fixture_path().read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reg():
    return CountryRegistry()


def test_lookup_alpha2(fixture, reg):
    for case in fixture["lookup_alpha2"]:
        c = reg.active(case["input"])
        assert c is not None, f"active({case['input']!r}) returned None"
        for key in ("alpha_2", "alpha_3", "numeric", "name", "status",
                    "independent", "region"):
            assert getattr(c, key) == case[key], \
                f"{case['input']}: {key} is {getattr(c, key)!r}, expected {case[key]!r}"


def test_lookup_alpha2_missing(fixture, reg):
    for code in fixture["lookup_alpha2_missing"]:
        assert reg.active(code) is None, f"active({code!r}) should be None"


def test_lookup_alpha3(fixture, reg):
    for case in fixture["lookup_alpha3"]:
        c = reg.by_alpha3(case["input"])
        assert c is not None
        assert c.alpha_2 == case["alpha_2"]


def test_lookup_numeric(fixture, reg):
    for case in fixture["lookup_numeric"]:
        c = reg.by_numeric(case["input"])
        assert c is not None
        assert c.alpha_2 == case["alpha_2"]


def test_counts(fixture, reg):
    s = reg.summary()
    assert s["total"] == fixture["counts"]["total"]
    assert s["active"] == fixture["counts"]["active"]
    assert s["withdrawn"] == fixture["counts"]["withdrawn"]
    for status, expected in fixture["counts"]["by_status"].items():
        assert s["by_status"].get(status, 0) == expected, \
            f"status {status}: got {s['by_status'].get(status)}, expected {expected}"


def test_overlap_codes(fixture, reg):
    for code, expected_statuses in fixture["overlap_codes"].items():
        matches = reg.with_alpha2(code)
        got = sorted(m.status for m in matches)
        assert got == sorted(expected_statuses), \
            f"{code}: got {got}, expected {sorted(expected_statuses)}"


def test_region_query(fixture, reg):
    for case in fixture["region_query"]:
        results = reg.region(case["region"])
        assert len(results) >= case["min_count"], \
            f"region {case['region']}: got {len(results)}, expected ≥ {case['min_count']}"
        codes = {c.alpha_2 for c in results}
        for code in case["must_contain"]:
            assert code in codes, f"region {case['region']} missing {code}"


def test_currencies(fixture, reg):
    for code, expected in fixture["currencies"].items():
        assert reg.currencies(code) == expected


def test_countries_with(fixture, reg):
    for curr, expected in fixture["countries_with"].items():
        got = [c.alpha_2 for c in reg.countries_with(curr)]
        assert got == expected


def test_search(fixture, reg):
    for case in fixture["search"]:
        results = reg.search(case["query"])
        assert len(results) >= case["min_count"], \
            f"search {case['query']!r}: got {len(results)}, expected ≥ {case['min_count']}"
        codes = {c.alpha_2 for c in results}
        for code in case["must_contain"]:
            assert code in codes, f"search {case['query']!r} missing {code}"


def test_lookup_withdrawn(fixture, reg):
    for case in fixture.get("lookup_withdrawn", []):
        matches = reg.with_alpha2(case["input"])
        found = any(
            m.status == "withdrawn" and m.name == case["name"]
            for m in matches
        )
        assert found, f"{case['input']}: withdrawn entry not found"
