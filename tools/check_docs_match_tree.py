#!/usr/bin/env python3
"""
tools/check_docs_match_tree.py

Verify that specific claims in the prose docs match the tree, so the
next release cannot drift them silently.

Checks:
  (a) README.md "N checks run in sequence" == release gate size
      (non-blank lines of the gate subshell in scripts/release.sh).
  (b) README.md "N CI jobs" (every occurrence) and CONTRIBUTING.md
      "runs N jobs" == jobs in .github/workflows/validate.yml.
  (c) docs/ENRICHMENT.md "<number> enriched fields" == 1 (official_name)
      + the fields in tools/enrich_field.py FIELDS; and the doc has a
      section for each of those fields.
  (d) docs/PROVENANCE.md "current as of vX.Y.Z" matches VERSION.
  (e) CONTRIBUTING.md "As of vX.Y.Z" matches VERSION.
  (f) docs/LAYERS.md mentions every top-level *.parquet file.
  (g) CONTRIBUTING.md names every CI job id.
  (i) README.md "N auxiliary checks" == rows of its auxiliary-check table,
      and every tools/check_*.py is a row of that table.
  (h) LAYERS.md names every generator that release.sh step 2 runs.
  (j) ENRICHMENT.md names every entry whose subregion is null.

"Matches VERSION" means: equal to VERSION, or equal to the newest
CHANGELOG heading when that is newer (staged release, as in
check_state_doc.py).

Usage:
    python3 tools/check_docs_match_tree.py [--root DIR]

Exit codes: 0 all checks pass; 1 any mismatch; 2 unreadable input.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


class Fatal(Exception):
    pass


def read(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except OSError as exc:
        raise Fatal(f"cannot read {rel}: {exc}")


def vt(v: str):
    return tuple(int(x) for x in v.split("."))


def gate_size(root: Path) -> int:
    s = read(root, "scripts/release.sh")
    try:
        gate = s.split("set -e\n", 1)[1].split(') > "$GATE_LOG"', 1)[0]
    except IndexError:
        raise Fatal("cannot locate the gate subshell in scripts/release.sh")
    return len([ln for ln in gate.splitlines() if ln.strip()])


def ci_jobs(root: Path) -> list[str]:
    y = read(root, ".github/workflows/validate.yml")
    try:
        body = y.split("\njobs:\n", 1)[1]
    except IndexError:
        raise Fatal("no jobs: section in validate.yml")
    return re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", body, re.M)


def enriched_fields(root: Path) -> list[str]:
    tree = ast.parse(read(root, "tools/enrich_field.py"))
    for node in ast.walk(tree):
        tgt = None
        if isinstance(node, ast.AnnAssign):
            tgt, val = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt, val = node.targets[0], node.value
        if isinstance(tgt, ast.Name) and tgt.id == "FIELDS" and isinstance(val, ast.Dict):
            keys = [k.value for k in val.keys if isinstance(k, ast.Constant)]
            return ["official_name"] + keys
    raise Fatal("no FIELDS dict in tools/enrich_field.py")


def current_versions(root: Path) -> set[str]:
    ver = read(root, "VERSION").strip()
    ok = {ver}
    m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", read(root, "CHANGELOG.md"), re.M)
    if m and vt(m.group(1)) > vt(ver):
        ok.add(m.group(1))
    return ok


def run(root: Path) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []

    def rec(ok: bool, desc: str, doc, tree):
        out.append((ok, desc if ok else f"{desc} (doc says {doc}, tree says {tree})"))

    readme = read(root, "README.md")
    contrib = read(root, "CONTRIBUTING.md")
    enr = read(root, "docs/ENRICHMENT.md")
    prov = read(root, "docs/PROVENANCE.md")
    layers = read(root, "docs/LAYERS.md")

    # (a)
    n = gate_size(root)
    m = re.findall(r"(\d+) checks run in sequence", readme)
    rec(bool(m) and all(int(x) == n for x in m),
        "README gate count matches scripts/release.sh", m or "no 'N checks run in sequence'", n)

    # (b)
    jobs = ci_jobs(root)
    m = re.findall(r"(\d+) CI jobs", readme)
    rec(bool(m) and all(int(x) == len(jobs) for x in m),
        "README CI job count matches validate.yml", m or "no 'N CI jobs'", len(jobs))
    m = re.findall(r"runs (\d+) jobs", contrib)
    rec(bool(m) and all(int(x) == len(jobs) for x in m),
        "CONTRIBUTING CI job count matches validate.yml", m or "no 'runs N jobs'", len(jobs))

    # (c)
    fields = enriched_fields(root)
    m = re.findall(r"\b(\w+) enriched fields", enr)
    nums = [WORDS.get(x.lower(), int(x) if x.isdigit() else -1) for x in m]
    rec(bool(nums) and all(x == len(fields) for x in nums),
        "ENRICHMENT.md enriched-field count matches tools", m or "no 'N enriched fields'",
        len(fields))
    missing = [f for f in fields if f"## `{f}`" not in enr]
    rec(not missing, "ENRICHMENT.md has a section for every enriched field",
        f"no section for {missing}", "sections expected for " + ", ".join(fields))

    # (d), (e)
    ok_versions = current_versions(root)
    for desc, text, pat in (("PROVENANCE.md 'current as of' version", prov,
                             r"[Cc]urrent as of v(\d+\.\d+\.\d+)"),
                            ("CONTRIBUTING.md 'As of' version", contrib,
                             r"\bAs of v(\d+\.\d+\.\d+)")):
        m = re.findall(pat, text)
        rec(bool(m) and all(x in ok_versions for x in m), f"{desc} matches VERSION",
            m or "nothing", "/".join(sorted(ok_versions)))

    # (f)
    pq = sorted(p.name for p in root.glob("*.parquet"))
    miss = [p for p in pq if p not in layers]
    rec(not miss, "LAYERS.md lists every top-level parquet artifact",
        f"missing {miss}", pq)

    # (g)
    miss = [j for j in jobs if f"`{j}`" not in contrib]
    rec(not miss, "CONTRIBUTING.md names every CI job", f"missing {miss}",
        f"{len(jobs)} jobs")
    # (i)
    m = re.search(r"carries (\w+) auxiliary checks", readme)
    sect = readme.split("### Additional checks", 1)[-1].split("\n---", 1)[0]
    rows = re.findall(r"^\| `tools/(check_[A-Za-z0-9_]+\.(?:py|sh))` \|", sect, re.M)
    claimed = None
    if m:
        w = m.group(1).lower()
        claimed = WORDS.get(w, int(w) if w.isdigit() else None)
    rec(claimed == len(rows), "README auxiliary-check count matches its table",
        m.group(1) if m else "no 'N auxiliary checks'", len(rows))
    names = sorted(p.name for p in (root / "tools").glob("check_*"))
    miss = [n for n in names if n not in rows and n not in readme]
    miss += [n for n in names if n.endswith(".py") and n not in rows and n not in miss]
    rec(not miss, "README table lists every tools/check_*.py and names every check tool",
        f"missing {sorted(set(miss))}", f"{len(names)} check tools")
    # (h)
    rs = read(root, "scripts/release.sh")
    seg = rs.split("    python3 tools/export_sql.py\n", 1)
    gens = ["tools/export_sql.py"] + (
        re.findall(r"^    python3 (tools/[A-Za-z0-9_]+\.py)\s*$",
                   seg[1].split("GATE_LOG=", 1)[0], re.M) if len(seg) == 2 else [])
    miss = [g for g in gens if g not in layers]
    rec(not miss, "LAYERS.md names every generator release.sh step 2 runs",
        f"missing {miss}", f"{len(gens)} generators")
    # (j)
    reg = json.loads(read(root, "iso3166.json"))["countries"]
    sec = enr.split("## `subregion`", 1)[-1].split("## `intermediate_region`", 1)[0]
    nulls = [e["alpha_2"] for k in ("active", "withdrawn") for e in reg[k]
             if e.get("subregion") is None]
    miss = [c for c in nulls if not re.search(rf"\b{c}\b", sec)]
    rec(not miss, "ENRICHMENT.md names every entry with a null subregion",
        f"missing {miss}", f"{len(nulls)} null entries")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=ROOT)
    a = ap.parse_args(argv)
    try:
        results = run(a.root.resolve())
    except Fatal as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for ok, msg in results:
        print(("OK: " if ok else "FAIL: ") + msg)
    bad = sum(1 for ok, _ in results if not ok)
    if bad:
        print(f"{bad} doc claim(s) do not match the tree", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
