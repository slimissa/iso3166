"""release.sh gives every run its own temp files; the v1.12.3 report is known bad.

The v1.12.3 verification report lists 11 gate commands where 38 ran. The
cause: release.sh wrote its record to a fixed /tmp path, and
tests/test_release_force.sh, which runs a whole release.sh inside the gate,
truncated that file. The dynamic proof is tests/test_release_force.sh
(scenarios 10 and 11). These tests pin the pieces that do not need a
throwaway repository.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")


def temp_block() -> str:
    begin = RELEASE.index("# BEGIN run-temp")
    end = RELEASE.index("# END run-temp")
    return RELEASE[begin:end]


def run_block(env_extra=None):
    """Run the run-temp block alone; print the paths it chose."""
    script = (
        "set -euo pipefail\n"
        + temp_block()
        + '\nprintf "%s\\n%s\\n%s\\n" "$RELEASE_TMP" "$GATE_REC" "$TAG_MESSAGE_FILE"\n'
        + 'rm -rf "$RELEASE_TMP"\n'
    )
    env = {"PATH": "/usr/bin:/bin"}
    env.update(env_extra or {})
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       env=env)
    assert r.returncode == 0, r.stderr
    return r.stdout.split()


def test_release_sh_names_no_fixed_tmp_path():
    fixed = [ln for ln in RELEASE.splitlines()
             if re.search(r'(=|>)\s*"?/tmp/', ln) and not ln.lstrip().startswith("#")]
    assert fixed == []


def test_two_runs_choose_two_different_directories():
    first, second = run_block(), run_block()
    assert first[0] != second[0]
    assert first[1] != second[1]


def test_an_inherited_gate_rec_is_ignored():
    # A nested release.sh inherits the outer run's environment. It must not
    # adopt the outer run's record file.
    outer = "/tmp/outer-run.rec"
    inner = run_block({"GATE_REC": outer, "GATE_LOG": "/tmp/outer-run.log"})
    assert inner[1] != outer
    assert inner[1].startswith(inner[0])


def test_the_v1_12_3_report_is_known_to_list_fewer_commands_than_ran():
    report = (ROOT / "docs" / "v1.12.3-verification.md").read_text(encoding="utf-8")
    listed = report.split("Gate commands:", 1)[1].split("Exit codes:", 1)[0]
    n = len(re.findall(r"^\s*\d+\. ", listed, re.M))
    gate = RELEASE.split("set -e\n", 1)[1].split(') > "$GATE_LOG"', 1)[0]
    ran = 8 + sum(1 for ln in gate.splitlines() if ln.strip())
    assert n == 11          # what the report says
    assert ran > n          # what ran at v1.12.3 and still runs


def test_the_v1_12_3_report_still_matches_its_sha256():
    import hashlib
    report = ROOT / "docs" / "v1.12.3-verification.md"
    digest, name = (ROOT / "docs" / "v1.12.3-verification.md.sha256").read_text(
        encoding="utf-8").split()
    assert name == "docs/v1.12.3-verification.md"
    assert hashlib.sha256(report.read_bytes()).hexdigest() == digest


def test_the_correction_is_in_an_errata_file_beside_the_report():
    errata = (ROOT / "docs" / "v1.12.3-verification-errata.md").read_text(encoding="utf-8")
    assert "11 commands" in errata and "38" in errata
    assert "unchanged" in errata
