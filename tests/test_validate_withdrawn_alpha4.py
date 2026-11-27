"""v1.14.0: alpha_4 and reservation on withdrawn entries, status unchanged,
and the schema version tie (docs/decisions/withdrawn-alpha4.md).

One negative test per rule: each mutates a copy of iso3166.json and checks
that the validator layer reports it. The mutations use rows that exist in
every v1.14.0 state of the tree (NT, MI, DE), so the tests hold before and
after the data commits.
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("validate", ROOT / "tools" / "validate.py")
validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate)
import parse_source  # noqa: E402

SCHEMA = ROOT / "schema.json"
REG = json.loads((ROOT / "iso3166.json").read_text(encoding="utf-8"))


def reg():
    return copy.deepcopy(REG)


def row(r, section, a2):
    return next(e for e in r["countries"][section] if e["alpha_2"] == a2)


def errors(layer, r, **kw):
    return "\n".join(layer(r, **kw).errors)


def test_the_tree_passes_every_new_rule():
    r = reg()
    assert errors(validate.layer_schema, r, schema_path=SCHEMA) == ""
    assert errors(validate.layer_integrity, r) == ""
    assert errors(validate.layer_business, r) == ""
    assert errors(validate.layer_ground_truth, r) == ""


def test_every_withdrawn_row_has_the_two_keys_and_no_active_row_does():
    for key in ("alpha_4", "reservation"):
        assert all(key in e for e in REG["countries"]["withdrawn"]), key
        assert not any(key in e for e in REG["countries"]["active"]), key


def test_every_withdrawn_row_keeps_status_withdrawn():
    assert {e["status"] for e in REG["countries"]["withdrawn"]} == {"withdrawn"}


# --- alpha_4 -------------------------------------------------------------

def test_alpha_4_on_an_active_entry_is_rejected():
    r = reg()
    row(r, "active", "DE")["alpha_4"] = "DEDE"
    assert "alpha_4 is only allowed on withdrawn entries" in errors(validate.layer_integrity, r)
    assert "alpha_4" in errors(validate.layer_schema, r, schema_path=SCHEMA)


def test_a_withdrawn_entry_without_the_alpha_4_key_is_rejected():
    r = reg()
    del row(r, "withdrawn", "NT")["alpha_4"]
    assert "missing alpha_4" in errors(validate.layer_integrity, r)
    assert "'alpha_4' is a required property" in errors(validate.layer_schema, r, schema_path=SCHEMA)


@pytest.mark.parametrize("bad", ["NTH", "nthh", "NTHH1", "NT-H"])
def test_a_malformed_alpha_4_is_rejected(bad):
    r = reg()
    row(r, "withdrawn", "NT")["alpha_4"] = bad
    assert f"alpha_4 {bad!r} does not match" in errors(validate.layer_integrity, r)
    assert "does not match" in errors(validate.layer_schema, r, schema_path=SCHEMA)


def test_an_alpha_4_that_does_not_start_with_the_alpha_2_is_rejected():
    r = reg()
    row(r, "withdrawn", "NT")["alpha_4"] = "MIUM"
    assert "does not start with alpha_2 'NT'" in errors(validate.layer_integrity, r)


def test_a_duplicate_alpha_4_in_the_withdrawn_list_is_rejected():
    r = reg()
    row(r, "withdrawn", "NT")["alpha_4"] = "NTHH"
    row(r, "withdrawn", "MI")["alpha_4"] = "NTHH"
    assert "withdrawn: duplicate alpha_4: ['NTHH']" in errors(validate.layer_business, r)


# --- status: no new value -------------------------------------------------

def test_an_active_status_on_a_withdrawn_entry_is_rejected():
    r = reg()
    row(r, "withdrawn", "NT")["status"] = "exceptionally-reserved"
    assert "status must be 'withdrawn'" in errors(validate.layer_business, r)
    assert errors(validate.layer_schema, r, schema_path=SCHEMA) != ""


def test_the_withdrawn_ground_truth_counts_every_withdrawn_entry_whatever_its_reservation():
    r = reg()
    r["countries"]["withdrawn"] = [e for e in r["countries"]["withdrawn"] if e["alpha_2"] != "NT"]
    assert "withdrawn: MISSING from registry ['NT']" in errors(validate.layer_ground_truth, r)


# --- reservation -----------------------------------------------------------

def test_reservation_on_an_active_entry_is_rejected():
    r = reg()
    row(r, "active", "DE")["reservation"] = "transitionally-reserved"
    assert "reservation is only allowed on withdrawn entries" in errors(validate.layer_integrity, r)
    assert "reservation" in errors(validate.layer_schema, r, schema_path=SCHEMA)


def test_a_withdrawn_entry_without_the_reservation_key_is_rejected():
    r = reg()
    del row(r, "withdrawn", "MI")["reservation"]
    assert "missing reservation" in errors(validate.layer_integrity, r)
    assert "'reservation' is a required property" in errors(validate.layer_schema, r, schema_path=SCHEMA)


def test_a_reservation_outside_the_vocabulary_is_rejected():
    r = reg()
    row(r, "withdrawn", "MI")["reservation"] = "reserved"
    assert "reservation 'reserved' is not one of" in errors(validate.layer_integrity, r)
    assert "is not one of" in errors(validate.layer_schema, r, schema_path=SCHEMA)


def test_a_reservation_iso_does_not_show_is_rejected():
    # MI is formerly used in every v1.14.0 state; ISO reserves nothing for it.
    assert "MI" not in parse_source.WITHDRAWN_EXCEPTIONAL_RESERVATION_CODES
    assert "MI" not in parse_source.WITHDRAWN_TRANSITIONAL_RESERVATION_CODES
    r = reg()
    row(r, "withdrawn", "MI")["reservation"] = "exceptionally-reserved"
    assert ("withdrawn reservation exceptionally-reserved: EXTRA in registry ['MI']"
            in errors(validate.layer_ground_truth, r))


# --- withdrawal_date ------------------------------------------------------

def test_a_null_withdrawal_date_without_alpha_4_is_rejected():
    r = reg()
    e = row(r, "withdrawn", "NT")
    e["withdrawal_date"] = None
    e["alpha_4"] = None
    assert "withdrawal_date is required (null only with an ISO 3166-3 alpha_4)" in errors(validate.layer_business, r)


def test_a_null_withdrawal_date_with_alpha_4_is_accepted():
    r = reg()
    e = row(r, "withdrawn", "NT")
    e["withdrawal_date"] = None
    e["alpha_4"] = "NTHH"
    assert "withdrawal_date is required" not in errors(validate.layer_business, r)


# --- schema version -------------------------------------------------------

def test_meta_schema_version_must_be_the_schema_id_version():
    r = reg()
    r["meta"]["schema_version"] = "1.0.0"
    assert "meta.schema_version '1.0.0' != schema.json $id version '1.1.0'" in errors(
        validate.layer_schema, r, schema_path=SCHEMA)
