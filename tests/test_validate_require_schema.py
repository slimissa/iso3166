"""validate.py --require-schema refuses to pass without the schema layer.

Without the flag, a missing jsonschema package makes the schema layer SKIP
and validate.py can exit 0 on five of six layers. These tests block the
import in a subprocess and check both behaviours.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "validate.py"

# Run validate.py with `import jsonschema` failing, as on a bare machine.
BLOCKED = (
    "import sys, runpy\n"
    "sys.modules['jsonschema'] = None\n"
    "sys.argv = ['validate.py'] + sys.argv[1:]\n"
    f"runpy.run_path({str(TOOL)!r}, run_name='__main__')\n"
)


def run(*flags, blocked=True):
    cmd = [sys.executable, "-c", BLOCKED, str(ROOT / "iso3166.json"), *flags] \
        if blocked else [sys.executable, str(TOOL), str(ROOT / "iso3166.json"), *flags]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def test_without_flag_a_missing_jsonschema_still_exits_zero():
    r = run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SKIP" in r.stdout


def test_with_flag_a_missing_jsonschema_exits_two_and_names_the_fix():
    r = run("--require-schema")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "pip install jsonschema" in r.stderr


def test_flag_contradicting_skip_schema_exits_two():
    r = run("--require-schema", "--skip", "schema", blocked=False)
    assert r.returncode == 2
    assert "contradicts" in r.stderr


def test_with_flag_and_jsonschema_present_the_real_data_passes():
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        return  # the blocked-import tests above are the point on this machine
    r = run("--require-schema", blocked=False)
    assert r.returncode == 0, r.stdout + r.stderr
