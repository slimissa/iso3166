"""Shared helper for the CLI test files (test_cli_*.py)."""
import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the console script in a clean environment."""
    return subprocess.run(
        [sys.executable, "-m", "iso3166.cli", *args],
        capture_output=True, text=True,
    )
