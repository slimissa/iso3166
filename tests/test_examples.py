"""Every example runs, and its output is the pinned output.

examples/run_all.sh --check runs each example under examples/ and diffs its
output against expected_output.txt. A registry change that moves a number the
example prints, or a code change that breaks the example, fails here with the
diff in the message. To accept an intended change:

    bash examples/run_all.sh --write

and read the diff before committing it.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUN_ALL = ROOT / "examples" / "run_all.sh"
EXAMPLE = ROOT / "examples" / "historical-entity-resolution"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_run_all_check_exits_zero():
    p = subprocess.run(["bash", str(RUN_ALL), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 0, p.stdout + p.stderr


def test_the_example_readme_quotes_the_pinned_output():
    """The transcript in the README is the pinned output, not a stale copy."""
    expected = (EXAMPLE / "expected_output.txt").read_text(encoding="utf-8")
    readme = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    assert expected in readme, (
        "examples/historical-entity-resolution/README.md no longer contains "
        "expected_output.txt verbatim; paste the new output into its Output section"
    )
