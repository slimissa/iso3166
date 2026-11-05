"""check_snapshot_freshness.py --check-upstream compares versions, offline-testable.

The upstream is a local bare git repository, so no test touches the network.
"""
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_snapshot_freshness.py"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   cwd=cwd, check=True, capture_output=True)


def make_upstream(tmp_path, tags):
    repo = tmp_path / "upstream"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "f").write_text("x")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "c")
    for t in tags:
        git(repo, "tag", "-a", t, "-m", t)
    return repo


def make_root(tmp_path, source_repo, source_version):
    root = tmp_path / "root"
    (root / "tools").mkdir(parents=True)
    meta = {"review_by": "2099-01-01", "refresh_cadence": "rare"}
    if source_repo is not None:
        meta["source_repo"] = str(source_repo)
        meta["source_version"] = source_version
    (root / "tools" / "x_snapshot.json").write_text(
        json.dumps({"meta": meta, "active": []}), encoding="utf-8")
    return root


def run(root, *flags):
    return subprocess.run(
        [sys.executable, str(TOOL), "--root", str(root), *flags],
        capture_output=True, text=True)


TAGS = ["v1.0.0", "v1.1.0", "v1.2.0", "v1.3.0", "v1.4.0", "v1.5.0",
        "v1.6.0-rc1", "nightly"]


def test_more_than_three_stable_tags_behind_warns_and_names_the_gap(tmp_path):
    up = make_upstream(tmp_path, TAGS)
    root = make_root(tmp_path, up, "1.0.0")
    r = run(root, "--check-upstream")
    assert r.returncode == 0, r.stdout + r.stderr      # advisory: never fails
    assert "[WARN]" in r.stdout
    assert "5 stable tags behind" in r.stdout          # prerelease and odd tag ignored
    assert "latest 1.5.0" in r.stdout


def test_three_or_fewer_behind_is_ok(tmp_path):
    up = make_upstream(tmp_path, TAGS)
    root = make_root(tmp_path, up, "1.2.0")            # 1.3, 1.4, 1.5 = 3 behind
    r = run(root, "--check-upstream")
    assert "[OK  ]" in r.stdout and "3 stable tag(s) behind" in r.stdout


def test_an_unreachable_upstream_is_a_warning_not_a_pass(tmp_path):
    root = make_root(tmp_path, tmp_path / "does-not-exist", "1.0.0")
    r = run(root, "--check-upstream")
    assert r.returncode == 0
    assert "[WARN]" in r.stdout and "unreachable" in r.stdout


def test_without_the_flag_nothing_is_fetched_or_printed(tmp_path):
    root = make_root(tmp_path, tmp_path / "does-not-exist", "1.0.0")
    r = run(root)
    assert r.returncode == 0
    assert "Upstream" not in r.stdout and "unreachable" not in r.stdout


def test_a_snapshot_without_source_version_is_skipped(tmp_path):
    root = make_root(tmp_path, None, None)
    r = run(root, "--check-upstream")
    assert r.returncode == 0
    assert "no snapshot carries source_version" in r.stdout


def test_the_real_iso4217_snapshot_names_its_source():
    root = TOOL.parent.parent
    meta = json.loads((root / "tools" / "iso4217_snapshot.json").read_text(
        encoding="utf-8"))["meta"]
    assert meta["source_repo"] == "slimissa/iso4217"
    assert meta["source_version"] == meta["iso4217_version"]
