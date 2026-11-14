"""pyarrow is installed under constraints.txt, everywhere CI installs it.

A pyarrow bump changes the Parquet bytes, so `export_parquet.py --check`
fails on a different day from the commit that caused it. requirements-dev.txt
pins pyarrow==26.0.0, but a workflow line such as `pip install pyarrow pandas`
bypasses that file. These tests walk every workflow in .github/workflows/
and fail, naming file, job and line, when an install line that mentions
pyarrow does not carry `-c constraints.txt`.

Written fresh for this repository (there is no ported ancestor): the
invariants are in docs and in the test names below.

The walker is proved able to fail by three support tests that feed it
synthetic workflows (a non-zero install-line count, an unpinned line in a
multiline block, an unpinned line behind a backslash continuation).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
PIN = "pyarrow==26.0.0"

INSTALL_RE = re.compile(r"\bpip3?\s+install\b")
CONSTRAINT_RE = re.compile(r"(?:^|\s)(?:-c|--constraint)(?:\s+|=)constraints\.txt(?=\s|$)")
PYARROW_TOKEN_RE = re.compile(r"(?<![\w-])pyarrow(?:[<>=!~][^\s\"']*)?", re.I)


def _strings(node):
    """Every string under `node`, depth first."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def install_lines(path: Path):
    """Yield (job, lineno, line) for every `pip install` line of a workflow.

    Walks each job's step `run:` blocks and every string of its `strategy`.
    Backslash continuations are joined first, so a flag on the next
    physical line belongs to the install it continues. `lineno` is the
    1-based line inside its block where the logical line starts.
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for job, body in (doc.get("jobs") or {}).items():
        blocks = [s.get("run") for s in (body.get("steps") or [])
                  if isinstance(s, dict) and isinstance(s.get("run"), str)]
        blocks += list(_strings(body.get("strategy")))
        for block in blocks:
            logical, start = "", 1
            for n, raw in enumerate(block.splitlines(), 1):
                if not logical:
                    start = n
                if raw.rstrip().endswith("\\"):
                    logical += raw.rstrip()[:-1] + " "
                    continue
                logical += raw
                if INSTALL_RE.search(logical):
                    yield job, start, " ".join(logical.split())
                logical = ""
            if logical and INSTALL_RE.search(logical):
                yield job, start, " ".join(logical.split())


def violations(path: Path) -> list[str]:
    bad = []
    for job, lineno, line in install_lines(path):
        tokens = PYARROW_TOKEN_RE.findall(line)
        if not tokens:
            continue
        where = f"{path.name}:{job}: line {lineno}: {line}"
        if not CONSTRAINT_RE.search(line):
            bad.append(f"{where}  -> mentions pyarrow without -c constraints.txt")
        for t in tokens:
            if t != "pyarrow" and t != PIN:
                bad.append(f"{where}  -> {t!r} is not {PIN}")
    return bad


# ---------------------------------------------------------------- the tree

def test_workflows_exist():
    assert WORKFLOWS, "no workflow files found"


def test_every_pyarrow_install_line_uses_constraints_txt_and_the_pin():
    bad = [b for w in WORKFLOWS for b in violations(w)]
    assert not bad, "\n" + "\n".join(bad)


def test_constraints_txt_pins_pyarrow():
    c = ROOT / "constraints.txt"
    assert c.is_file(), "constraints.txt is missing"
    lines = [ln.strip() for ln in c.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    assert PIN in lines, lines


def test_requirements_dev_and_constraints_pin_the_same_pyarrow():
    req = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    pins = re.findall(r"^pyarrow[^\s#]*", req, re.M)
    assert pins == [PIN], pins


# --------------------------------------------- the walker can fail (support)

def _wf(tmp_path: Path, run_block: str, strategy: str = "") -> Path:
    body = "\n".join("          " + ln for ln in run_block.splitlines())
    text = (
        "jobs:\n"
        "  demo:\n"
        f"{strategy}"
        "    runs-on: ubuntu-24.04\n"
        "    steps:\n"
        "      - name: install\n"
        "        run: |\n"
        f"{body}\n"
    )
    p = tmp_path / "demo.yml"
    p.write_text(text, encoding="utf-8")
    return p


def test_support_walker_finds_install_lines_in_the_real_workflow():
    n = sum(1 for w in WORKFLOWS for _ in install_lines(w))
    assert n > 0
    assert any(PYARROW_TOKEN_RE.search(line)
               for w in WORKFLOWS for _, _, line in install_lines(w)), \
        "no install line mentions pyarrow: the check would pass vacuously"


def test_support_unpinned_line_in_a_multiline_block_is_caught(tmp_path):
    p = _wf(tmp_path, "echo start\npip install pyarrow pandas\necho end")
    bad = violations(p)
    assert len(bad) == 1, bad
    assert "demo.yml:demo: line 2" in bad[0]
    # the same line, constrained, is clean
    ok = _wf(tmp_path, "pip install pyarrow pandas -c constraints.txt")
    assert violations(ok) == []


def test_support_unpinned_line_via_backslash_continuation_is_caught(tmp_path):
    p = _wf(tmp_path, "pip install \\\n    pandas \\\n    pyarrow")
    assert len(violations(p)) == 1
    ok = _wf(tmp_path, "pip install \\\n    pandas \\\n    pyarrow \\\n"
                       "    -c constraints.txt")
    assert violations(ok) == []
    wrong = _wf(tmp_path, "pip install pyarrow==25.0.0 -c constraints.txt")
    assert any("is not pyarrow==26.0.0" in b for b in violations(wrong))
