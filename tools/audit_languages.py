#!/usr/bin/env python3
"""
tools/audit_languages.py

Classify each officially-assigned entry's languages list as empty,
single-language, or multi-language. Advisory; no writes.

Usage:
    python3 tools/audit_languages.py
    python3 tools/audit_languages.py --json
    python3 tools/audit_languages.py --registry PATH
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REGISTRY = Path("iso3166.json")


def classify(reg: dict) -> dict:
    empty, single, multi = [], [], []
    for e in reg["countries"]["active"]:
        if e["status"] != "officially-assigned":
            continue
        langs = e.get("languages")
        if langs is None or langs == []:
            empty.append({"alpha_2": e["alpha_2"], "name": e["name"]})
        elif len(langs) == 1:
            single.append({
                "alpha_2": e["alpha_2"],
                "name": e["name"],
                "language": langs[0],
            })
        else:
            multi.append({
                "alpha_2": e["alpha_2"],
                "name": e["name"],
                "languages": langs,
            })
    return {"empty": empty, "single": single, "multi": multi}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    reg = json.loads(args.registry.read_text(encoding="utf-8"))
    result = classify(reg)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"empty ({len(result['empty'])}):")
    for e in result["empty"]:
        print(f"  {e['alpha_2']}  {e['name']}")
    print()
    print(f"single ({len(result['single'])}):")
    for e in result["single"]:
        print(f"  {e['alpha_2']}  {e['name']}  {e['language']}")
    print()
    print(f"multi ({len(result['multi'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
