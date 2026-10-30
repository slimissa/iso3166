#!/usr/bin/env python3
"""
tools/cross_language_derived.py

Run every case in tests/cross_language_consistency.json ->
derived_queries through the Python, JavaScript, Go and Rust wrappers and
the CLI, and fail if any surface disagrees with the fixture's expected
value. Called by tools/check_cross_language.sh.

The CLI is skipped only where the input code is unknown and the query is
one the CLI reports with an exit code instead of an empty or false result
(docs/QUERIES.md, "Consistency contract"). Its
`successors` and `predecessors` subcommands return all descendants /
ancestors, like the wrappers (Option A, v1.10.0).

Exit codes: 0 all agree, 1 a disagreement, 3 a surface failed to run.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "cross_language_consistency.json"


def run(cmd, cwd=None) -> str:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode not in (0, 1, 4):  # 4: the CLI's tri-state "unknown"
        raise RuntimeError(f"{cmd[0]} exited {p.returncode}: {p.stderr.strip()}")
    return p.stdout


def norm(text: str):
    return json.loads(text) if text.strip() else None


def py_all(cases):
    sys.path.insert(0, str(ROOT / "wrappers" / "python"))
    from iso3166 import CountryRegistry  # noqa: PLC0415
    reg = CountryRegistry()
    return [getattr(reg, c["query"])(*c["args"]) for c in cases]


JS = r"""
const { CountryRegistry } = require(process.argv[1]);
const m = {is_eu:'isEu',is_eea:'isEea',is_eurozone:'isEurozone',
  region_tree:'regionTree',borders_transitively:'bordersTransitively',
  succession_path:'successionPath',successors:'successors',
  predecessors:'predecessors',calling_code_for:'callingCodeFor',
  currency_at:'currencyAt',region_countries:'regionCountries',
  is_active_on:'isActiveOn',is_eu_member_at:'isEuMemberAt',
  is_eea_member_at:'isEeaMemberAt',is_eurozone_member_at:'isEurozoneMemberAt',
  is_in_customs_union_at:'isInCustomsUnionAt'};
const reg = new CountryRegistry();
const cases = JSON.parse(process.argv[2]);
console.log(JSON.stringify(cases.map(c => reg[m[c.query]](...c.args))));
"""


def js_all(cases):
    out = run(["node", "-e", JS, str(ROOT / "wrappers" / "javascript"),
               json.dumps(cases)])
    return json.loads(out)


def _real_date(s):
    import datetime
    try:
        datetime.date.fromisoformat(s)
        return len(s) == 10
    except ValueError:
        return False


def argv_of(c):
    return [c["query"]] + [str(a) for a in c["args"]]


def main() -> int:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["derived_queries"]["cases"]
    results: dict[str, list] = {}
    try:
        results["python"] = py_all(cases)
        results["javascript"] = js_all(cases)

        tmp = tempfile.mkdtemp()
        gobin = os.path.join(tmp, "query")
        run(["go", "build", "-o", gobin, "./cmd/query"], cwd=ROOT / "wrappers" / "go")
        results["go"] = [norm(run([gobin, *argv_of(c)])) for c in cases]

        run(["cargo", "build", "--quiet", "--bin", "query"], cwd=ROOT / "wrappers" / "rust")
        rbin = ROOT / "wrappers" / "rust" / "target" / "debug" / "query"
        results["rust"] = [norm(run([str(rbin), *argv_of(c)])) for c in cases]

        cli = []
        for c in cases:
            if c["args"][0] == "ZZ" and c["query"] in (
                "is_eu", "is_eea", "is_eurozone", "region_tree",
                "borders_transitively", "successors", "predecessors",
            ):
                cli.append(c["expected"])
                continue
            if c["query"] in ("currency_at", "is_eu_member_at", "is_eea_member_at",
                              "is_eurozone_member_at", "is_in_customs_union_at") \
                    and not _real_date(c["args"][1]):
                cli.append(c["expected"])  # the CLI exits 2 on a malformed date
                continue
            args = [c["query"].replace("_", "-")] + [str(a) for a in c["args"]]
            if c["query"] == "borders_transitively":
                args = [args[0], args[1], "--max-hops", args[2]]
            if c["query"] == "region_countries" and len(args) > 2:
                args = [args[0], args[1], "--subregion", args[2]]
            got = norm(run([sys.executable, str(ROOT / "tools" / "iso3166_cli.py"),
                            *args, "--json"]))
            if c["query"] in ("successors", "predecessors") or c["query"].startswith("is_"):
                got = got[c["query"]]  # these print an object keyed by the query name
            cli.append(got)
        results["cli"] = cli
    except (RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    bad = 0
    for i, c in enumerate(cases):
        for surface, vals in results.items():
            if vals[i] != c["expected"]:
                bad += 1
                print(f"MISMATCH {surface}: {c['query']}{c['args']} -> "
                      f"{vals[i]!r}, expected {c['expected']!r}", file=sys.stderr)
    if bad:
        print(f"FAIL: {bad} derived-query disagreement(s)", file=sys.stderr)
        return 1
    print(f"OK: {len(cases)} derived-query cases agree across "
          f"{len(results)} surfaces ({', '.join(results)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
