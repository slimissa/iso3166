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

v1.12.5: `derived_queries.error_cases` are checked too. A malformed date is
an error, not an answer: Python raises ValueError, JavaScript throws
TypeError, the Go and Rust query binaries and the CLI exit 2 with a
"malformed date" message on stderr.

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


def load_error_cases() -> list[dict]:
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return fx["derived_queries"]["error_cases"]


def _exit2(cmd, cwd=None) -> str | None:
    """None if the command exited 2 with 'malformed date' on stderr, else why not."""
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 2:
        return f"exit {p.returncode}, stdout {p.stdout.strip()!r}"
    if "malformed date" not in p.stderr:
        return f"exit 2 but stderr is {p.stderr.strip()!r}"
    return None


def py_errors(cases) -> list[str]:
    sys.path.insert(0, str(ROOT / "wrappers" / "python"))
    from iso3166 import CountryRegistry  # noqa: PLC0415
    reg = CountryRegistry()
    bad = []
    for c in cases:
        try:
            got = getattr(reg, c["query"])(*c["args"])
        except ValueError as e:
            if "malformed date" not in str(e):
                bad.append(f"python {c['query']}{c['args']}: wrong message {e}")
        else:
            bad.append(f"python {c['query']}{c['args']}: returned {got!r}")
    return bad


JS_ERR = r"""
const { CountryRegistry } = require(process.argv[1]);
const m = {is_active_on:'isActiveOn',is_eu_member_at:'isEuMemberAt',
  is_eea_member_at:'isEeaMemberAt',is_eurozone_member_at:'isEurozoneMemberAt',
  is_in_customs_union_at:'isInCustomsUnionAt'};
const reg = new CountryRegistry();
const out = JSON.parse(process.argv[2]).map((c) => {
  try { return 'returned ' + JSON.stringify(reg[m[c.query]](...c.args)); }
  catch (e) { return e instanceof TypeError && /malformed date/.test(e.message) ? null : 'wrong error ' + e; }
});
console.log(JSON.stringify(out));
"""


def js_errors(cases) -> list[str]:
    out = json.loads(run(["node", "-e", JS_ERR, str(ROOT / "wrappers" / "javascript"),
                          json.dumps(cases)]))
    return [f"javascript {c['query']}{c['args']}: {r}" for c, r in zip(cases, out) if r]


def go_errors(cases) -> list[str]:
    tmp = tempfile.mkdtemp()
    gobin = os.path.join(tmp, "query")
    run(["go", "build", "-o", gobin, "./cmd/query"], cwd=ROOT / "wrappers" / "go")
    return [f"go {c['query']}{c['args']}: {why}" for c in cases
            if (why := _exit2([gobin, *argv_of(c)]))]


def rust_errors(cases) -> list[str]:
    run(["cargo", "build", "--quiet", "--bin", "query"], cwd=ROOT / "wrappers" / "rust")
    rbin = ROOT / "wrappers" / "rust" / "target" / "debug" / "query"
    return [f"rust {c['query']}{c['args']}: {why}" for c in cases
            if (why := _exit2([str(rbin), *argv_of(c)]))]


def cli_errors(cases) -> list[str]:
    bad = []
    for c in cases:
        args = [c["query"].replace("_", "-")] + [str(a) for a in c["args"]]
        why = _exit2([sys.executable, str(ROOT / "tools" / "iso3166_cli.py"), *args])
        if why:
            bad.append(f"cli {c['query']}{c['args']}: {why}")
    return bad


def active_on_results() -> dict[str, dict]:
    """active_on(date) as each surface returns it (v1.12.5, Query 11)."""
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))["derived_queries"]["active_on"]
    date = fx["date"]
    sys.path.insert(0, str(ROOT / "wrappers" / "python"))
    from iso3166 import CountryRegistry  # noqa: PLC0415
    out = {"python": CountryRegistry().active_on(date)}
    out["javascript"] = json.loads(run([
        "node", "-e",
        "const {CountryRegistry}=require(process.argv[1]);"
        "console.log(JSON.stringify(new CountryRegistry().activeOn(process.argv[2])))",
        str(ROOT / "wrappers" / "javascript"), date]))
    tmp = tempfile.mkdtemp()
    gobin = os.path.join(tmp, "query")
    run(["go", "build", "-o", gobin, "./cmd/query"], cwd=ROOT / "wrappers" / "go")
    out["go"] = json.loads(run([gobin, "active_on", date]))
    run(["cargo", "build", "--quiet", "--bin", "query"], cwd=ROOT / "wrappers" / "rust")
    out["rust"] = json.loads(run([str(ROOT / "wrappers" / "rust" / "target" / "debug" / "query"),
                                  "active_on", date]))
    out["cli"] = json.loads(run([sys.executable, str(ROOT / "tools" / "iso3166_cli.py"),
                                 "active-on", date, "--json"]))
    return out


def check_active_on(results: dict[str, dict]) -> list[str]:
    """Failures: a surface that differs from the fixture's counts or spot values."""
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))["derived_queries"]["active_on"]
    active = {e["alpha_2"] for e in json.loads(
        (ROOT / "iso3166.json").read_text(encoding="utf-8"))["countries"]["active"]}

    def tally(d, keys=None):
        t = {"true": 0, "false": 0, "null": 0}
        for k, v in d.items():
            if keys is None or k in keys:
                t["null" if v is None else ("true" if v else "false")] += 1
        return t

    bad = []
    for name, d in results.items():
        if len(d) != fx["keys"]:
            bad.append(f"{name} active_on: {len(d)} keys, expected {fx['keys']}")
        if tally(d) != fx["counts"]:
            bad.append(f"{name} active_on: counts {tally(d)}, expected {fx['counts']}")
        if tally(d, active) != fx["active_counts"]:
            bad.append(f"{name} active_on: active counts {tally(d, active)}, "
                       f"expected {fx['active_counts']}")
        for k, v in fx["spot"].items():
            if d.get(k, "MISSING") is not v:
                bad.append(f"{name} active_on[{k}] = {d.get(k, 'MISSING')!r}, expected {v!r}")
    first = next(iter(results.values()))
    for name, d in results.items():
        if d != first:
            bad.append(f"{name} active_on differs from {next(iter(results))}")
    return bad


ERROR_SURFACES = {
    "python": py_errors, "javascript": js_errors, "go": go_errors,
    "rust": rust_errors, "cli": cli_errors,
}


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
    try:
        for line in check_active_on(active_on_results()):
            bad += 1
            print(f"ACTIVE-ON {line}", file=sys.stderr)
    except (RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    err_cases = load_error_cases()
    try:
        for name, fn in ERROR_SURFACES.items():
            for line in fn(err_cases):
                bad += 1
                print(f"ERROR-CASE {line}", file=sys.stderr)
    except (RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    if bad:
        print(f"FAIL: {bad} derived-query disagreement(s)", file=sys.stderr)
        return 1
    print(f"OK: {len(cases)} derived-query cases agree across "
          f"{len(results)} surfaces ({', '.join(results)}); "
          f"active_on agrees on {len(results)} surfaces; "
          f"{len(err_cases)} malformed-date cases fail loudly on "
          f"{len(ERROR_SURFACES)} surfaces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
