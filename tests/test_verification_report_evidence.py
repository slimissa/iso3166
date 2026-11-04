"""The verification report records the gate evidence.

The report must let a later audit see that the gate ran: every command, its
exit code, the SHA-256 of the gate log, and a sibling .sha256 of the report
itself. The record handed to the writer is built from the real gate in
scripts/release.sh, so the "at least 30" bounds follow the real gate.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "write_verification_report.py"


def gate_commands() -> list[str]:
    text = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    block = text.split("set -e\n", 1)[1].split(') > "$GATE_LOG"', 1)[0]
    return [re.sub(r"^gate\s+", "", ln.strip())
            for ln in block.splitlines() if ln.strip()]


def freshness_commands() -> list[str]:
    text = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    block = text.split("# BEGIN artifact-freshness", 1)[1].split(
        "# END artifact-freshness", 1)[0]
    return re.findall(r'"(python3 tools/[a-z_]+\.py --check)"', block)


def write_report(tmp_path: Path, rows):
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    rec = tmp_path / "gate.rec"
    rec.write_text("".join(f"{rc}\t{cmd}\n" for rc, cmd in rows),
                   encoding="utf-8")
    log = tmp_path / "gate.log"
    log.write_text("=== gate: x\n=== exit: 0\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(TOOL), "--version", "9.9.9",
         "--commit", "a" * 40, "--tag", "v9.9.9", "--date", "2026-01-01",
         "--workflows", "validate.yml", "--gate-rec", str(rec),
         "--gate-log", str(log), "--out", "docs/v9.9.9-verification.md"],
        cwd=repo, capture_output=True, text=True)
    return repo, log, r


def section(text: str, heading: str) -> list[str]:
    """Numbered lines under `heading`, up to the next blank-then-heading."""
    body = text.split(heading, 1)[1]
    lines = []
    for ln in body.splitlines()[1:]:
        if re.match(r"^\s*\d+\. ", ln):
            lines.append(ln)
        elif ln.strip() and lines:
            break
    return lines


def real_rows():
    return [(0, c) for c in freshness_commands() + gate_commands()]


def test_report_lists_every_command_and_exit_code(tmp_path):
    rows = real_rows()
    repo, log, r = write_report(tmp_path, rows)
    assert r.returncode == 0, r.stderr
    text = (repo / "docs" / "v9.9.9-verification.md").read_text(encoding="utf-8")

    assert "Gate commands:" in text
    commands = section(text, "Gate commands:")
    assert len(commands) >= 30
    assert len(commands) == len(rows)

    assert "Exit codes:" in text
    codes = section(text, "Exit codes:")
    assert len(codes) >= 30
    assert len(codes) == len(rows)

    assert "Result: PASS" in text
    assert hashlib.sha256(log.read_bytes()).hexdigest() in text


def test_sibling_sha256_exists_and_matches_the_report(tmp_path):
    repo, _, r = write_report(tmp_path, real_rows())
    assert r.returncode == 0, r.stderr
    report = repo / "docs" / "v9.9.9-verification.md"
    sidecar = repo / "docs" / "v9.9.9-verification.md.sha256"
    assert sidecar.is_file()
    digest, name = sidecar.read_text(encoding="utf-8").split()
    assert name == "docs/v9.9.9-verification.md"
    assert digest == hashlib.sha256(report.read_bytes()).hexdigest()
    # The hash is not in the report body: it would change the hash.
    assert digest not in report.read_text(encoding="utf-8")


def test_a_non_zero_exit_code_is_recorded_not_hidden(tmp_path):
    rows = real_rows()
    rows[3] = (1, rows[3][1])
    repo, _, r = write_report(tmp_path, rows)
    assert r.returncode == 0
    text = (repo / "docs" / "v9.9.9-verification.md").read_text(encoding="utf-8")
    assert "Result: FAIL: 1 of" in text


def test_no_evidence_means_no_report(tmp_path):
    repo, _, r = write_report(tmp_path, [])
    assert r.returncode == 2
    assert not (repo / "docs" / "v9.9.9-verification.md").exists()
