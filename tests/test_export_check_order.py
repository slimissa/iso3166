"""The artifact freshness block fails at --check, before it regenerates.

A --check that runs after regeneration compares a file with itself. The
block in scripts/release.sh (between the artifact-freshness markers) runs
--check on the committed artifacts FIRST. These tests run that block, taken
verbatim from release.sh, in a throwaway copy of the repository.
"""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns(
    ".git", "target", "node_modules", "__pycache__", "*.egg-info",
    ".pytest_cache",
)


def freshness_block() -> str:
    text = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    begin = text.index("# BEGIN artifact-freshness")
    end = text.index("# END artifact-freshness")
    return text[begin:end]


def run_block(repo: Path, mode: str = "full"):
    script = (
        'set -euo pipefail\n'
        'die() { printf "ERROR: %s\\n" "$*" >&2; exit 1; }\n'
        'GATE_REC=$(mktemp)\n'
        + freshness_block()
        + f"\nartifact_freshness {mode}\n"
    )
    return subprocess.run(["bash", "-c", script], cwd=repo,
                          capture_output=True, text=True)


def throwaway_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo, ignore=IGNORE)
    for cmd in (["git", "init", "-q", "-b", "main"],
                ["git", "add", "-A"],
                ["git", "-c", "user.name=t", "-c", "user.email=t@t",
                 "commit", "-q", "-m", "base"]):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    return repo


def test_stale_csv_fails_at_check_not_at_regeneration(tmp_path):
    repo = throwaway_repo(tmp_path)
    csv = repo / "iso3166.csv"
    text = csv.read_text(encoding="utf-8")
    assert "Afghanistan" in text
    csv.write_text(text.replace("Afghanistan", "Afghanistan2", 1),
                   encoding="utf-8")

    r = run_block(repo)
    out = r.stdout + r.stderr

    assert r.returncode != 0
    assert "FRESHNESS FAIL: python3 tools/export_csv.py --check" in out
    # It stopped before stage 2, so nothing was regenerated.
    assert "regenerating" not in out
    assert csv.read_text(encoding="utf-8") == text.replace(
        "Afghanistan", "Afghanistan2", 1)


def test_clean_tree_passes_all_three_stages(tmp_path):
    repo = throwaway_repo(tmp_path)
    r = run_block(repo)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "[1/3]" in out and "[2/3]" in out and "[3/3]" in out
    # Regeneration may rewrite countries_by_region.parquet byte for byte
    # (its --check compares tables); nothing else may change.
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                            capture_output=True, text=True).stdout
    changed = {line[3:] for line in status.splitlines()}
    assert changed <= {"countries_by_region.parquet"}, status
