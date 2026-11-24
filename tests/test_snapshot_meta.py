"""Vendoring metadata of the ISO 4217 snapshot (qlf-sentinel client contract CC-2).

tools/iso4217_snapshot.meta.json carries, in its "meta" object, source,
source_version, vendored_at, review_by and refresh_cadence; review_by is
vendored_at plus one cadence period (tools/cadence.py); every key present
both at the top level and in "meta" has the same value in both; every key
shared by the sibling "meta" and the snapshot's embedded "meta" has the same
value in both; and the sibling's source_version is the embedded
iso4217_version.

Modelled on tests/test_snapshot_meta.py of slimissa/iso10383 at tag v1.1.9
(857cc31). Rules (e) and (f) differ from that model: this snapshot is an
extract with its own embedded meta, not a byte-for-byte copy, so the
sibling is compared with the embedded meta instead of a top-level
source_version.
"""
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
from cadence import CADENCE_MONTHS, add_months, review_by  # noqa: E402

META = "iso4217_snapshot.meta.json"
SNAPSHOT = "iso4217_snapshot.json"
FIVE = ("source", "source_version", "vendored_at", "review_by", "refresh_cadence")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _iso_date(v):
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def cadence_problems(meta: dict) -> list[str]:
    """Rules (b) and (c): the cadence word and the review_by date."""
    out = []
    cad = meta.get("refresh_cadence")
    if "refresh_cadence" in meta and cad not in CADENCE_MONTHS:
        out.append(f"meta.refresh_cadence {cad!r} not in {sorted(CADENCE_MONTHS)}")
    va, rb = _iso_date(meta.get("vendored_at")), _iso_date(meta.get("review_by"))
    if va and rb and cad in CADENCE_MONTHS:
        want = add_months(va, CADENCE_MONTHS[cad])
        if rb != want:
            out.append(f"meta.review_by {rb} != vendored_at + 1 {cad} period ({want})")
    return out


def problems(meta_path: Path, snapshot_path: Path) -> list[str]:
    """Every rule the sibling meta file breaks; empty when it is valid."""
    doc = json.loads(meta_path.read_text(encoding="utf-8"))
    meta = doc.get("meta")
    if not isinstance(meta, dict):
        return ["no meta object"]
    out = []
    # (a) the five keys and their types
    for k in FIVE:
        if k not in meta:
            out.append(f"meta lacks {k}")
    if "source" in meta and not isinstance(meta["source"], str):
        out.append("meta.source is not a string")
    if "source_version" in meta and not (isinstance(meta["source_version"], str)
                                         and SEMVER.match(meta["source_version"])):
        out.append("meta.source_version is not SemVer")
    for k in ("vendored_at", "review_by"):
        if k in meta and _iso_date(meta[k]) is None:
            out.append(f"meta.{k} is not a YYYY-MM-DD date")
    # (b) cadence vocabulary, (c) review_by = vendored_at + 1 period
    out += cadence_problems(meta)
    # (d) top-level and "meta" copies agree
    for k in sorted(set(meta) & (set(doc) - {"meta"})):
        if doc[k] != meta[k]:
            out.append(f"{k}: top level {doc[k]!r} != meta {meta[k]!r}")
    # (e) sibling "meta" and the snapshot's embedded "meta" agree
    embedded = json.loads(snapshot_path.read_text(encoding="utf-8")).get("meta")
    if not isinstance(embedded, dict):
        return out + ["snapshot has no embedded meta object"]
    for k in sorted(set(meta) & set(embedded)):
        if meta[k] != embedded[k]:
            out.append(f"{k}: sibling meta {meta[k]!r} != embedded meta {embedded[k]!r}")
    # (f) the sibling names the vendored version
    if meta.get("source_version") != embedded.get("iso4217_version"):
        out.append(f"meta.source_version {meta.get('source_version')!r} != "
                   f"embedded iso4217_version {embedded.get('iso4217_version')!r}")
    return out


def test_iso4217_sibling_meta_satisfies_cc2_and_the_cadence_rule():
    assert problems(TOOLS / META, TOOLS / SNAPSHOT) == []


def test_iso4217_sibling_meta_values():
    meta = json.loads((TOOLS / META).read_text(encoding="utf-8"))["meta"]
    assert (meta["refresh_cadence"], meta["vendored_at"], meta["review_by"]) == \
        ("quarterly", "2026-11-21", "2027-02-21")


@pytest.mark.parametrize("start, n, end", [
    ("2026-11-21", 3, "2027-02-21"),
    ("2026-11-23", 12, "2027-11-23"),
    ("2026-11-30", 3, "2027-02-28"),   # clamped
    ("2027-11-30", 3, "2028-02-29"),   # clamped, leap year
    ("2026-01-31", 1, "2026-02-28"),   # clamped
    ("2026-12-15", 1, "2027-01-15"),   # year rollover
])
def test_add_months(start, n, end):
    assert add_months(date.fromisoformat(start), n) == date.fromisoformat(end)


def test_review_by_refuses_a_word_outside_the_vocabulary():
    assert review_by("2026-11-21", "quarterly") == "2027-02-21"
    with pytest.raises(ValueError, match="not in"):
        review_by("2026-11-21", "annual")


# --- negative tests: each rule on a broken copy of the real files ------------

def _copy(tmp_path):
    m, s = tmp_path / META, tmp_path / SNAPSHOT
    shutil.copy2(TOOLS / META, m)
    shutil.copy2(TOOLS / SNAPSHOT, s)
    return m, s


def _edit(path, change):
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def test_unbroken_copy_passes(tmp_path):
    assert problems(*_copy(tmp_path)) == []


@pytest.mark.parametrize("target, change, expect", [
    ("meta", lambda d: d.pop("meta"), "no meta object"),
    ("meta", lambda d: d["meta"].pop("vendored_at"), "meta lacks vendored_at"),
    ("meta", lambda d: d["meta"].update(source=7), "meta.source is not a string"),
    ("meta", lambda d: d["meta"].update(source_version="1.9"), "meta.source_version is not SemVer"),
    ("meta", lambda d: d["meta"].update(review_by="2027-02-30"), "meta.review_by is not a YYYY-MM-DD date"),
    ("meta", lambda d: d["meta"].update(refresh_cadence="annual"), "not in ['monthly', 'quarterly', 'yearly']"),
    ("meta", lambda d: d["meta"].update(review_by="2027-10-25"), "!= vendored_at + 1 quarterly period (2027-02-21)"),
    ("meta", lambda d: d.update(vendored_at="2026-11-20"), "vendored_at: top level '2026-11-20' != meta '2026-11-21'"),
    ("snapshot", lambda d: d["meta"].update(review_by="2027-10-25"),
     "review_by: sibling meta '2027-02-21' != embedded meta '2027-10-25'"),
    ("snapshot", lambda d: d["meta"].update(iso4217_version="1.9.4"),
     "!= embedded iso4217_version '1.9.4'"),
], ids=["a-no-meta", "a-missing-key", "a-source-type", "a-semver", "a-date",
        "b-cadence", "c-review-by", "d-copies-differ", "e-embedded-drift", "f-version"])
def test_each_rule_is_enforced(tmp_path, target, change, expect):
    m, s = _copy(tmp_path)
    _edit(m if target == "meta" else s, change)
    found = problems(m, s)
    assert any(expect in p for p in found), found
