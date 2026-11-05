"""check_consumers_current.py: the lag of each consumer, from served metadata.

The consumers' metadata is a directory of files read through file:// URLs,
laid out the way raw.githubusercontent.com serves it: <repo>/main/<path>.
"""
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_consumers_current.py"


def serve(tmp_path, metas):
    """metas: {repo: json}. Returns (consumers.json path, base url)."""
    consumers = []
    for repo, meta in metas.items():
        d = tmp_path / "served" / repo / "main" / "tools"
        d.mkdir(parents=True)
        if meta is not None:
            (d / "iso3166_snapshot.meta.json").write_text(json.dumps(meta))
        consumers.append({"name": repo.split("/")[1], "repo": repo,
                          "snapshot_path": "tools/iso3166_snapshot.json",
                          "fields_read": ["alpha_2"]})
    cfile = tmp_path / "consumers.json"
    cfile.write_text(json.dumps({"consumers": consumers}))
    return cfile, (tmp_path / "served").as_uri()


def run(cfile, base, *flags):
    return subprocess.run(
        [sys.executable, str(TOOL), "--consumers", str(cfile),
         "--base-url", base, "--version", "1.12.3", *flags],
        capture_output=True, text=True)


def test_consumers_within_the_limit_exit_zero(tmp_path):
    cfile, base = serve(tmp_path, {"o/a": {"source_version": "1.8.0"},
                                   "o/b": {"source_version": "1.12.0"}})
    r = run(cfile, base)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "4 minor(s) behind" in r.stdout


def test_a_consumer_five_minors_behind_exits_one_and_is_named(tmp_path):
    cfile, base = serve(tmp_path, {"o/a": {"source_version": "1.7.0"},
                                   "o/b": {"source_version": "1.12.0"}})
    r = run(cfile, base)
    assert r.returncode == 1
    assert "[BEHIND] a:" in r.stdout and "[OK    ] b:" in r.stdout


def test_exchange_calendar_style_nested_meta_is_read(tmp_path):
    cfile, base = serve(tmp_path, {"o/ec": {"meta": {"source_version": "1.5.2"}}})
    r = run(cfile, base)
    assert r.returncode == 1
    assert "vendors 1.5.2, 7 minor(s) behind" in r.stdout


def test_unreadable_metadata_is_exit_two_not_a_pass(tmp_path):
    cfile, base = serve(tmp_path, {"o/a": {"source_version": "1.12.0"},
                                   "o/gone": None})
    r = run(cfile, base)
    assert r.returncode == 2
    assert "[ERR ] gone" in r.stdout


def test_missing_consumers_file_is_exit_two(tmp_path):
    r = run(tmp_path / "nope.json", (tmp_path).as_uri())
    assert r.returncode == 2
    assert "cannot read" in r.stderr


def test_the_limit_is_adjustable(tmp_path):
    cfile, base = serve(tmp_path, {"o/a": {"source_version": "1.10.0"}})
    assert run(cfile, base, "--limit", "3").returncode == 0
    assert run(cfile, base, "--limit", "2").returncode == 1
