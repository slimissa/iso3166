"""registry_release.json: the manifest of a release, checked against the tree.

Before v1.12.6 a consumer who wanted to verify a release had to hash every
file by hand. The manifest lists 16 artifacts with their sizes and SHA-256
digests; tools/gen_registry_release.py --check regenerates it in memory and
compares byte for byte.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "tools" / "gen_registry_release.py"
RELEASE = ROOT / "registry_release.json"
SCHEMA = ROOT / "registry_release.schema.json"

EXPECTED_PATHS = [
    "iso3166.json", "schema.json",
    "iso3166.sql", "iso3166.postgresql.sql", "iso3166.mysql.sql",
    "iso3166.sqlite.sql",
    "iso3166.csv", "iso3166.excel.csv", "iso3166.european.csv", "iso3166.tsv",
    "iso3166.parquet", "countries_by_region.parquet",
    "wrappers/python/iso3166/iso3166.json",
    "wrappers/javascript/iso3166.json",
    "wrappers/go/iso3166.json",
    "wrappers/rust/iso3166.json",
]


def load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def gen(*args, root=None):
    cmd = [sys.executable, str(GEN), *args]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_registry_release_matches_tree():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    r = gen("--check", "--version", version)
    assert r.returncode == 0, r.stdout + r.stderr


def test_registry_release_schema():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()).validate(load())


def test_registry_release_files_complete():
    assert len(EXPECTED_PATHS) == 16
    assert [f["path"] for f in load()["files"]] == EXPECTED_PATHS


def test_registry_release_sha_matches_file():
    for f in load()["files"]:
        data = (ROOT / f["path"]).read_bytes()
        assert f["sha256"] == hashlib.sha256(data).hexdigest(), f["path"]
        assert f["bytes"] == len(data), f["path"]


def test_registry_release_format_version():
    assert load()["format_version"] == "1.0.0"


def test_registry_release_vendors():
    v = {x["name"]: x for x in load()["vendors"]}
    assert v["iso4217"]["version"] == "1.8.0"
    assert v["iso4217"]["review_by"] == "2027-10-25"


def _copy_tree(tmp_path: Path) -> Path:
    names = ["VERSION", "README.md", "scripts/release.sh",
             "tools/release_claims.json", "tools/iso4217_snapshot.json",
             "registry_release.json", *EXPECTED_PATHS]
    for rel in names:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    return tmp_path


def test_check_reports_drift_when_a_listed_file_changes(tmp_path):
    root = _copy_tree(tmp_path)
    assert gen("--check", root=root).returncode == 0
    with open(root / "iso3166.csv", "ab") as fh:
        fh.write(b"x")
    r = gen("--check", root=root)
    assert r.returncode == 1, r.stdout + r.stderr


def test_check_usage_and_missing_input_exit_two(tmp_path):
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert gen("--check", "--version", "0.0.1").returncode == 2
    root = _copy_tree(tmp_path)
    (root / "registry_release.json").unlink()
    assert gen("--check", root=root).returncode == 2
    (root / "iso3166.tsv").unlink()
    r = gen("--version", version, root=root)
    assert r.returncode == 2 and "iso3166.tsv" in r.stderr
