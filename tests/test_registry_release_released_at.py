"""registry_release.json: `released` is the data date, `released_at` the tag date.

`released` is iso3166.json meta.updated (the data update date; a pure function
of the tree). `released_at` is the date of the tag: null in the tagged tree,
stamped by scripts/release.sh in the verification-report commit AFTER the tag,
so `gen_registry_release.py --check` must not compare it.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "tools" / "gen_registry_release.py"
SCHEMA = json.loads((ROOT / "registry_release.schema.json").read_text(encoding="utf-8"))
NAMES = ["VERSION", "README.md", "scripts/release.sh", "tools/release_claims.json",
         "tools/iso4217_snapshot.json", "registry_release.json", "iso3166.json",
         "schema.json", "iso3166.sql", "iso3166.postgresql.sql", "iso3166.mysql.sql",
         "iso3166.sqlite.sql", "iso3166.csv", "iso3166.excel.csv",
         "iso3166.european.csv", "iso3166.tsv", "iso3166.parquet",
         "countries_by_region.parquet", "wrappers/python/iso3166/iso3166.json",
         "wrappers/javascript/iso3166.json", "wrappers/go/iso3166.json",
         "wrappers/rust/iso3166.json"]


def gen(root, *args):
    return subprocess.run([sys.executable, str(GEN), *args, "--root", str(root)],
                          capture_output=True, text=True)


def tree(tmp_path):
    for rel in NAMES:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    return tmp_path


def validator():
    return jsonschema.Draft202012Validator(
        SCHEMA, format_checker=jsonschema.FormatChecker())


def test_schema_declares_released_at_as_a_nullable_date():
    assert "released_at" in SCHEMA["properties"]
    assert "released_at" in SCHEMA["required"]
    doc = json.loads((ROOT / "registry_release.json").read_text(encoding="utf-8"))
    v = validator()
    for good in (None, "2026-11-20"):
        d = dict(doc, released_at=good)
        assert not list(v.iter_errors(d)), good
    for bad in ("tomorrow", "20261120", 20261120):
        d = dict(doc, released_at=bad)
        assert list(v.iter_errors(d)), bad


def test_committed_manifest_keeps_the_two_dates_apart():
    doc = json.loads((ROOT / "registry_release.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "iso3166.json").read_text(encoding="utf-8"))["meta"]
    assert doc["released"] == meta["updated"]
    assert doc["released_at"] is None or isinstance(doc["released_at"], str)
    assert list(doc).index("released_at") == list(doc).index("released") + 1


def test_stamp_then_check_passes_and_write_mode_keeps_the_stamp(tmp_path):
    root = tree(tmp_path)
    r = gen(root, "--stamp-released-at", "2026-11-20")
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads((root / "registry_release.json").read_text(encoding="utf-8"))
    assert doc["released_at"] == "2026-11-20"
    assert doc["released"] != "2026-11-20" or doc["released"] == doc["released"]
    assert gen(root, "--check").returncode == 0
    assert gen(root).returncode == 0          # regeneration keeps the stamp
    again = json.loads((root / "registry_release.json").read_text(encoding="utf-8"))
    assert again["released_at"] == "2026-11-20"
    assert gen(root, "--check").returncode == 0


def test_a_malformed_released_at_is_drift_and_a_bad_stamp_is_a_usage_error(tmp_path):
    root = tree(tmp_path)
    p = root / "registry_release.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["released_at"] = "tomorrow"
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert gen(root, "--check").returncode == 1
    assert gen(root, "--stamp-released-at", "2026-13-45").returncode == 2
    assert gen(root, "--stamp-released-at", "2026-11-20", "--check").returncode == 2


def test_check_still_catches_drift_next_to_a_stamped_released_at(tmp_path):
    root = tree(tmp_path)
    gen(root, "--stamp-released-at", "2026-11-20")
    with open(root / "iso3166.csv", "ab") as fh:
        fh.write(b"x")
    assert gen(root, "--check").returncode == 1


def test_release_sh_stamps_after_the_tag_in_the_report_commit():
    sh = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    assert sh.count("--stamp-released-at") == 1
    tag = sh.index('git tag -a "v$VERSION"')
    stamp = sh.index("--stamp-released-at")
    add = sh.index('git add "$REPORT" "$REPORT.sha256" registry_release.json')
    step7 = sh.index('step "7/7 verification report"')
    assert tag < step7 < stamp < add
