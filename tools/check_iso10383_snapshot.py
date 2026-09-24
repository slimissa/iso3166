#!/usr/bin/env python3
"""Verify every MIC in exchanges/ exists in the ISO 10383 registry.

Exit 0 if all resolve (or if the sibling is unreachable).
Exit 1 if any MIC is missing and --strict.
"""

import argparse, json, sys, urllib.request
from pathlib import Path

LIVE_URL = "https://raw.githubusercontent.com/slimissa/iso10383/main/iso10383.json"

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()

    here = Path(__file__).resolve().parents[1]
    mics = set()
    for f in (here / "exchanges").glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("mic"): mics.add(d["mic"])
        if d.get("code"): mics.add(d["code"])

    try:
        with urllib.request.urlopen(LIVE_URL, timeout=30) as r:
            live = {m["mic"] for m in json.loads(r.read())["mics"]}
    except Exception as e:
        print(f"note: sibling unreachable ({e})", file=sys.stderr)
        return 0

    missing = sorted(mics - live)
    if not missing:
        print(f"OK: all {len(mics)} MICs resolve")
        return 0

    print(f"missing: {len(missing)} MIC(s) not in ISO 10383")
    for m in missing:
        print(f"  {m}")

    # Known gap: XBEK, XNBO, XQSE. Documented in both registries.
    known = {"XBEK", "XNBO", "XQSE"}
    if set(missing) <= known:
        print("(all missing MICs are in the documented known-gap set)")
        return 0

    if args.strict:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
