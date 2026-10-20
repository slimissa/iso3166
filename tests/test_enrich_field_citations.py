"""record_source writes one `<field> source:` line per field (v1.7.2, issue 0.1)."""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "enrich_field", Path(__file__).resolve().parent.parent / "tools" / "enrich_field.py")
ef = importlib.util.module_from_spec(_spec)
sys.modules["enrich_field"] = ef   # dataclasses look the module up here
_spec.loader.exec_module(ef)

U1, U2, U3 = "https://a.example/1", "https://b.example/2", "https://c.example/3"


def test_empty_note_gets_one_line():
    assert ef.record_source(None, U1, "tlds") == f"tlds source: {U1}"


def test_different_fields_coexist():
    n = ef.record_source(None, U1, "currency_codes")
    n = ef.record_source(n, U2, "calling_codes")
    n = ef.record_source(n, U3, "tlds")
    assert n.splitlines() == [
        f"currency_codes source: {U1}",
        f"calling_codes source: {U2}",
        f"tlds source: {U3}",
    ]


def test_same_field_replaced_not_duplicated():
    n = ef.record_source(None, U1, "tlds")
    n = ef.record_source(n, U2, "tlds")
    assert n == f"tlds source: {U2}"


def test_idempotent():
    n = ef.record_source(None, U1, "tlds")
    assert ef.record_source(n, U1, "tlds") == n


def test_prose_and_other_prefixes_preserved():
    existing = f"official_name source: {U1}\nAntarctica. Prose.\nsource: {U2}"
    n = ef.record_source(existing, U3, "borders")
    lines = n.splitlines()
    assert f"official_name source: {U1}" in lines
    assert "Antarctica. Prose." in lines
    assert f"source: {U2}" in lines          # legacy bare line untouched
    assert lines[-1] == f"borders source: {U3}"
