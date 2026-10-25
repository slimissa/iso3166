#!/usr/bin/env python3
"""
tools/check_state_doc.py

Verify the claims in docs/STATE.md against the tree. Fails on drift.

Checked:
  - the title version is VERSION, or the newest versioned CHANGELOG
    heading when that is newer (a staged release: CHANGELOG written,
    VERSION not yet bumped by release.sh);
  - the title carries an ISO date;
  - "Registry data": active, withdrawn, total and per-status counts,
    against iso3166.json and meta.count_active / meta.count_withdrawn;
  - "Populated fields": every N/D, and every "missing XX, YY" list;
  - "Cross-registry snapshots vendored": version or count, file
    existence and review-by date, against the snapshot files;
  - "CI": job count in validate.yml and gate size in release.sh.

Counting rules match tools/gen_state_doc.py: list fields count when
non-empty, other fields when not null, `independent` when true.

Usage:
    python3 tools/check_state_doc.py
    python3 tools/check_state_doc.py --strict      # also require all sections
    python3 tools/check_state_doc.py --state PATH  # check another copy

Exit codes: 0 all claims match; 1 any mismatch; 2 usage or input error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ("Registry data", "Populated fields",
            "Cross-registry snapshots vendored", "CI", "Known limitations")
LIST_FIELDS = {"currency_codes", "calling_codes", "tlds", "languages", "borders"}
TITLE_RE = re.compile(r"^# Current state — v(\d+\.\d+\.\d+) \((\d{4}-\d{2}-\d{2})\)\s*$",
                      re.M)


class Fatal(Exception):
    pass


def vt(v: str):
    return tuple(int(x) for x in v.split("."))


def sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## (.+?)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def rows(body: str) -> list[list[str]]:
    out = []
    for ln in body.splitlines():
        if ln.startswith("|") and not re.match(r"^\|[-| ]+\|$", ln):
            out.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return out[1:]  # drop header


def populated(e: dict, f: str) -> bool:
    v = e.get(f)
    if f == "independent":
        return v is True
    if f in LIST_FIELDS:
        return bool(v)
    return v is not None


def check(root: Path, state: Path, strict: bool) -> list[str]:
    bad: list[str] = []
    try:
        text = state.read_text(encoding="utf-8")
    except OSError as exc:
        raise Fatal(f"cannot read {state}: {exc}")
    try:
        d = json.loads((root / "iso3166.json").read_text(encoding="utf-8"))
        meta, active, wd = d["meta"], d["countries"]["active"], d["countries"]["withdrawn"]
    except (OSError, KeyError, ValueError) as exc:
        raise Fatal(f"cannot read iso3166.json: {exc}")

    # title
    m = TITLE_RE.search(text)
    if not m:
        bad.append("title: expected '# Current state — vX.Y.Z (YYYY-MM-DD)'")
    else:
        ver, _date = m.group(1), m.group(2)
        cur = (root / "VERSION").read_text(encoding="utf-8").strip()
        cl = re.search(r"^## \[(\d+\.\d+\.\d+)\]",
                       (root / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
        top = cl.group(1) if cl else None
        if ver != cur and not (top == ver and vt(ver) > vt(cur)):
            bad.append(f"title: version v{ver} matches neither VERSION ({cur}) nor a "
                       f"newer top CHANGELOG heading ({top})")

    secs = sections(text)
    if strict:
        for s in SECTIONS:
            if s not in secs:
                bad.append(f"missing required section: '## {s}'")

    # registry data
    if "Registry data" in secs:
        claim = {r[0]: r[1] for r in rows(secs["Registry data"]) if len(r) >= 2}
        by = {}
        for e in active:
            by[e["status"]] = by.get(e["status"], 0) + 1
        if len(active) != meta["count_active"]:
            bad.append(f"iso3166.json: len(active)={len(active)} != meta.count_active="
                       f"{meta['count_active']}")
        if len(wd) != meta["count_withdrawn"]:
            bad.append(f"iso3166.json: len(withdrawn)={len(wd)} != meta.count_withdrawn="
                       f"{meta['count_withdrawn']}")
        want = {"Active entries": meta["count_active"],
                "Officially-assigned": by.get("officially-assigned", 0),
                "Exceptionally-reserved": by.get("exceptionally-reserved", 0),
                "User-assigned": by.get("user-assigned", 0),
                "Withdrawn entries": meta["count_withdrawn"],
                "Total entries": meta["count_active"] + meta["count_withdrawn"]}
        for k, v in want.items():
            if k not in claim:
                bad.append(f"Registry data: no row '{k}'")
            elif claim[k] != str(v):
                bad.append(f"Registry data: '{k}' says {claim[k]}, tree has {v}")

    # populated fields
    if "Populated fields" in secs:
        assigned = sum(1 for e in active if e["status"] == "officially-assigned")
        for r in rows(secs["Populated fields"]):
            if len(r) < 2:
                continue
            label, pop = r[0], r[1]
            notes = r[2] if len(r) > 2 else ""
            fields = [f.strip() for f in label.split(",")]
            mm = re.fullmatch(r"(\d+)/(\d+)", pop)
            if not mm:
                bad.append(f"Populated fields: '{label}' value '{pop}' is not N/D")
                continue
            n = sum(1 for e in active if all(populated(e, f) for f in fields))
            dn = assigned if label == "official_name" else len(active)
            if (int(mm.group(1)), int(mm.group(2))) != (n, dn):
                bad.append(f"Populated fields: '{label}' says {pop}, tree has {n}/{dn}")
            ml = re.search(r"missing ((?:[A-Z]{2})(?:, [A-Z]{2})*)", notes)
            if ml and len(fields) == 1:
                claimed = set(ml.group(1).split(", "))
                actual = {e["alpha_2"] for e in active if not populated(e, fields[0])
                          and (label != "official_name"
                               or e["status"] == "officially-assigned")}
                if claimed != actual:
                    bad.append(f"Populated fields: '{label}' missing-list says "
                               f"{sorted(claimed)}, tree has {sorted(actual)}")

    # snapshots
    if "Cross-registry snapshots vendored" in secs:
        for r in rows(secs["Cross-registry snapshots vendored"]):
            if len(r) < 4:
                continue
            name, ver, f, rb = r[:4]
            p = root / f
            if not p.is_file():
                bad.append(f"Snapshots: '{name}' file {f} does not exist")
                continue
            j = json.loads(p.read_text(encoding="utf-8"))
            mt = j["meta"]
            if "iso4217_version" in mt:
                actual_ver = mt["iso4217_version"]
            else:
                key = next((k for k in ("languages", "codes", "tlds", "subregions",
                                        "intermediate_regions") if k in j), None)
                unit = {"languages": "codes", "codes": "codes", "tlds": "TLDs",
                        "subregions": "names", "intermediate_regions": "names"}[key]
                actual_ver = f"{len(j[key])} {unit}"
            if ver != actual_ver:
                bad.append(f"Snapshots: '{name}' says {ver}, file has {actual_ver}")
            if rb != str(mt.get("review_by")):
                bad.append(f"Snapshots: '{name}' review-by says {rb}, file has "
                           f"{mt.get('review_by')}")

    # CI
    if "CI" in secs:
        y = (root / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        jobs = len(re.findall(r"^  [A-Za-z0-9_-]+:\s*$", y.split("\njobs:\n", 1)[1], re.M))
        sh = (root / "scripts/release.sh").read_text(encoding="utf-8")
        gate = sh.split("set -e\n", 1)[1].split(') > "$GATE_LOG"', 1)[0]
        checks = len([ln for ln in gate.splitlines() if ln.strip()])
        mj = re.search(r"(\d+) jobs", secs["CI"])
        mc = re.search(r"gate has (\d+) checks", secs["CI"])
        if not mj or int(mj.group(1)) != jobs:
            bad.append(f"CI: job count says {mj.group(1) if mj else 'nothing'}, "
                       f"validate.yml has {jobs}")
        if not mc or int(mc.group(1)) != checks:
            bad.append(f"CI: gate size says {mc.group(1) if mc else 'nothing'}, "
                       f"release.sh has {checks}")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--state", type=Path)
    ap.add_argument("--root", type=Path, default=ROOT)
    a = ap.parse_args(argv)
    root = a.root.resolve()
    try:
        bad = check(root, a.state or root / "docs" / "STATE.md", a.strict)
    except Fatal as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if bad:
        for b in bad:
            print(f"FAIL: {b}", file=sys.stderr)
        print(f"{len(bad)} claim(s) in STATE.md do not match the tree; "
              "re-run tools/gen_state_doc.py", file=sys.stderr)
        return 1
    print("OK: every claim in STATE.md matches the tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
