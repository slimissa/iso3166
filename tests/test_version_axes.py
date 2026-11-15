"""tools/version_axes.json is the one list of version sites.

Before v1.12.6 three lists drifted independently: the JSON file (10 sites,
"not yet read"), check_version_consistency.py (9 hardcoded result lines)
and release.sh (8 hardcoded bumps). The checker and the release bump step
now both read the JSON, and these tests fail if a site is added, renamed
or re-flagged in only one place.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AXES = ROOT / "tools" / "version_axes.json"
CHECK = ROOT / "tools" / "check_version_consistency.py"
SITES = json.loads(AXES.read_text(encoding="utf-8"))["sites"]
NUMBER_WORDS = {10: "ten", 11: "eleven"}


def run(*args):
    return subprocess.run([sys.executable, str(CHECK), *args],
                          capture_output=True, text=True)


def temp_root(tmp_path, axes=None):
    """A copy of just the files the sites name, plus an axes file."""
    for s in SITES:
        dst = tmp_path / s["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / s["path"], dst)
    (tmp_path / "tools").mkdir(exist_ok=True)
    f = tmp_path / "tools" / "version_axes.json"
    f.write_text(json.dumps(axes if axes is not None
                            else json.loads(AXES.read_text(encoding="utf-8")),
                            indent=2), encoding="utf-8")
    return f


def read_axes():
    return json.loads(AXES.read_text(encoding="utf-8"))


def test_checker_passes_on_the_tree():
    r = run()
    assert r.returncode == 0, r.stdout + r.stderr


def test_checker_prints_every_site_by_name():
    r = run()
    for s in SITES:
        assert f"[{s['name']}]" in r.stdout, s["name"]
    assert len(re.findall(r"^\s+OK\s+\[", r.stdout, re.M)) + \
        len(re.findall(r"^\s+SKIP\s+\[", r.stdout, re.M)) == len(SITES)
    j = json.loads(run("--json").stdout)
    assert [x["name"] for x in j["sites"]] == [s["name"] for s in SITES]


def test_site_names_are_unique_and_each_bumped_site_names_a_bumper():
    names = [s["name"] for s in SITES]
    assert len(names) == len(set(names))
    for s in SITES:
        assert isinstance(s["bumped"], bool), s["name"]
        assert ("bumper" in s) == s["bumped"], s["name"]


def test_mutating_a_sites_path_fails_the_checker(tmp_path):
    axes = read_axes()
    axes["sites"][4]["path"] = "wrappers/python/pyproject-moved.toml"
    f = temp_root(tmp_path, axes)
    r = run("--root", str(tmp_path), "--axes", str(f))
    assert r.returncode == 1, r.stdout + r.stderr
    assert axes["sites"][4]["name"] in r.stdout


def test_mutating_a_sites_value_fails_the_checker(tmp_path):
    f = temp_root(tmp_path)
    p = tmp_path / "wrappers" / "python" / "iso3166" / "__init__.py"
    p.write_text(re.sub(r'__version__ = "[0-9.]+"', '__version__ = "0.0.1"',
                        p.read_text(encoding="utf-8")), encoding="utf-8")
    r = run("--root", str(tmp_path), "--axes", str(f))
    assert r.returncode == 1
    assert "[python-init]" in r.stdout and "0.0.1" in r.stdout


def _current(root: Path, site):
    sys.path.insert(0, str(ROOT / "tools"))
    import check_version_consistency as c

    return c.read_site(root, site, {"version": "9.9.9", "notes": []})


def test_bumped_true_sites_are_bumped_and_bumped_false_sites_are_not(tmp_path):
    f = temp_root(tmp_path)
    before = {s["name"]: _current(tmp_path, s) for s in SITES}
    r = run("--root", str(tmp_path), "--axes", str(f), "--bump", "9.9.9")
    assert r.returncode == 0, r.stdout + r.stderr
    for s in SITES:
        after = _current(tmp_path, s)
        if s["bumped"]:
            assert after == ("value", "9.9.9"), s["name"]
        else:
            assert after == before[s["name"]], s["name"]


def test_flipping_the_flag_in_the_json_changes_what_is_bumped(tmp_path):
    axes = read_axes()
    flipped = next(s for s in axes["sites"] if s["name"] == "python-init")
    flipped["bumped"] = False
    del flipped["bumper"]
    f = temp_root(tmp_path, axes)
    before = _current(tmp_path, flipped)
    run("--root", str(tmp_path), "--axes", str(f), "--bump", "9.9.9")
    assert _current(tmp_path, flipped) == before
    assert _current(tmp_path, next(s for s in SITES if s["name"] == "python-pyproject")) \
        == ("value", "9.9.9")


def test_a_bumped_site_without_a_known_bumper_is_refused(tmp_path):
    axes = read_axes()
    next(s for s in axes["sites"] if s["name"] == "python-init")["bumper"] = "nope"
    f = temp_root(tmp_path, axes)
    r = run("--root", str(tmp_path), "--axes", str(f), "--bump", "9.9.9")
    assert r.returncode == 2


def test_expect_skips_generated_sites_and_fails_on_a_stale_one(tmp_path):
    f = temp_root(tmp_path)
    current = (tmp_path / "VERSION").read_text(encoding="utf-8").strip()
    r = run("--root", str(tmp_path), "--axes", str(f), "--expect", current)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"all {sum('generated_by' not in s for s in SITES)} version sites" in r.stdout
    r = run("--root", str(tmp_path), "--axes", str(f), "--expect", "9.9.9")
    assert r.returncode == 1


def test_release_sh_reads_version_axes_and_hardcodes_no_site_path():
    sh = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    assert "check_version_consistency.py --bump" in sh
    assert "check_version_consistency.py --expect" in sh
    assert "version_axes" in sh
    for s in SITES:
        if s["bumped"] and s["path"].startswith("wrappers/"):
            assert s["path"] not in sh, f"release.sh hardcodes {s['path']}"


def test_readme_version_table_matches_the_json():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sec = readme.split("## 16. Versioning", 1)[1].split("\n## ", 1)[0]
    assert f"held by {NUMBER_WORDS[len(SITES)]} files" in sec
    rows = re.findall(r"^\| (\d+) \| `([a-z0-9-]+)` \|", sec, re.M)
    assert [n for _, n in rows] == [s["name"] for s in SITES]
