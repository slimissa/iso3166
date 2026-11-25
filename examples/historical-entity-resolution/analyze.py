#!/usr/bin/env python3
"""Three ways to validate a country column that spans 1990-2024.

    python3 analyze.py

1. naive       is the code in today's list?                       (loses real trades)
2. temporal   was the code in use ON THE TRADE DATE?             (is_active_on)
3. silent-fail the same query read with `if`, which treats the
               "source is silent" answer (None) as False           (loses them again)

The input is generate_fake_trades.generate(): synthetic, seeded, with a
`truth` label written from raw dates. Standard library only; the registry
is read from the repository's iso3166.json. The output is pinned in
expected_output.txt and checked by run_all.sh --check.
"""
from __future__ import annotations

import collections
import datetime
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "wrappers" / "python"))
sys.path.insert(0, str(HERE))

from iso3166 import CountryRegistry  # noqa: E402
import generate_fake_trades as gen  # noqa: E402


def usd(n: int) -> str:
    return f"${n:,}"


def share(n: int, total: int) -> str:
    return f"{n:,} ({100 * n / total:.1f}%)"


def top(counter: collections.Counter, k: int = 8) -> str:
    return ", ".join(f"{c} {n:,}" for c, n in counter.most_common(k))


def main() -> int:
    reg = CountryRegistry(ROOT / "iso3166.json")
    trades = gen.generate(reg)
    total = len(trades)
    total_usd = sum(t["notional_usd"] for t in trades)
    truth = collections.Counter(t["truth"] for t in trades)
    today = {c.alpha_2 for c in reg.all_active()}

    print(f"Historical entity resolution: {total:,} synthetic trades, "
          f"{gen.START} to {gen.END}")
    print(f"seed {gen.SEED}; generator truth: {truth['valid']:,} valid, "
          f"{truth['stale_code']:,} stale_code; notional {usd(total_usd)}")

    # ---- 1. naive ------------------------------------------------------
    print("\n== Scenario 1: naive (is the code in today's list?) ==")
    rejected = [t for t in trades if t["country"] not in today]
    genuine = [t for t in rejected if t["truth"] == "valid"]
    stale = [t for t in rejected if t["truth"] == "stale_code"]
    print(f"accepted : {share(total - len(rejected), total)}")
    print(f"rejected : {share(len(rejected), total)}, "
          f"notional {usd(sum(t['notional_usd'] for t in rejected))}")
    print(f"  genuine trades rejected (truth=valid): {len(genuine):,}, "
          f"notional {usd(sum(t['notional_usd'] for t in genuine))}")
    print(f"  bugs rejected (truth=stale_code)     : {len(stale):,}")
    print("  rejected codes: "
          + top(collections.Counter(t["country"] for t in rejected)))
    print("verdict  : every genuine SU, DD, YU, ZR ... trade is rejected, and it is\n"
          "           rejected for the same reason as the bugs. Nothing tells them apart.")

    # ---- 2. temporal ---------------------------------------------------
    print("\n== Scenario 2: temporal (is_active_on at the trade date) ==")
    answer = {t["trade_id"]: reg.is_active_on(t["country"], t["trade_date"])
              for t in trades}
    states = collections.Counter(answer.values())
    print(f"true     : {share(states[True], total)}   the code existed that day")
    print(f"false    : {share(states[False], total)}   the code did not exist that day")
    print(f"null     : {share(states[None], total)}   the registry does not know")
    false_accepts = sum(1 for t in trades
                        if t["truth"] == "stale_code" and answer[t["trade_id"]] is True)
    false_rejects = sum(1 for t in trades
                        if t["truth"] == "valid" and answer[t["trade_id"]] is False)
    stale_caught = sum(1 for t in trades
                       if t["truth"] == "stale_code" and answer[t["trade_id"]] is False)
    print(f"check against truth: stale_code caught {stale_caught:,} of {truth['stale_code']:,}; "
          f"false accepts {false_accepts}; false rejects {false_rejects}")
    unknown = collections.Counter(t["country"] for t in trades if answer[t["trade_id"]] is None)
    print(f"  null: {len(unknown)} distinct codes, introduced date not recorded; top: "
          + top(unknown))

    print("\nWithdrawn codes in valid trades, rolled up to today's countries:")
    legacy = collections.defaultdict(lambda: [0, 0])
    for t in trades:
        if t["truth"] == "valid" and t["country"] in gen.LEGACY_WEIGHTS:
            legacy[t["country"]][0] += 1
            legacy[t["country"]][1] += t["notional_usd"]
    outcome = collections.Counter()
    for code in sorted(legacy):
        n, notional = legacy[code]
        heirs = [c for c in reg.successors(code) if c in today]
        kind = "resolved" if len(heirs) == 1 else ("ambiguous" if heirs else "unresolved")
        outcome[kind] += n
        print(f"  {code}  {n:>4,} trades  {usd(notional):>13}  -> "
              f"{kind:<10} {', '.join(heirs) if heirs else '-'}")
    print("  " + ", ".join(f"{k} {v:,}" for k, v in sorted(outcome.items())))
    print("verdict  : genuine legacy trades are kept and the bugs are caught. Where the\n"
          "           tree has one heir the trade rolls up; with several or none it does\n"
          "           not, and the output says so instead of guessing.")

    # ---- 3. silent fail ------------------------------------------------
    print("\n== Scenario 3: silent-fail (the answer read with `if`) ==")
    truthy = [t for t in trades if reg.is_active_on(t["country"], t["trade_date"])]
    lost = [t for t in trades if answer[t["trade_id"]] is None]
    print(f"`if is_active_on(...)` accepts {share(len(truthy), total)}")
    print(f"scenario 2 accepts true + null  {share(states[True] + states[None], total)}")
    print(f"silently dropped by `if`: {len(lost):,} trades, "
          f"notional {usd(sum(t['notional_usd'] for t in lost))}, "
          f"all truth=valid: {all(t['truth'] == 'valid' for t in lost)}")
    print("  dropped codes: " + top(collections.Counter(t["country"] for t in lost)))
    print("verdict  : None is falsy. The query says \"the source is silent\" and `if`\n"
          "           reads that as \"no\". Test `is True`, `is False`, `is None`.")

    print("\nA malformed date is not silent any more (v1.12.5):")
    try:
        reg.is_active_on("DE", "1990-13-45")
    except ValueError as exc:
        print(f"  is_active_on('DE', '1990-13-45') raises ValueError: {exc}")
    print("  is_active_on('DE', datetime.date(1990, 1, 1)) -> "
          f"{reg.is_active_on('DE', datetime.date(1990, 1, 1))}")
    print(f"  is_active_on('XX', '1990-01-01') -> {reg.is_active_on('XX', '1990-01-01')}"
          "   (unknown code: known not to exist)")
    print(f"  is_active_on('RU', '1990-01-01') -> {reg.is_active_on('RU', '1990-01-01')}"
          "   (introduced date not recorded)")

    print("\n== Honest limits, as the registry answers them ==")
    print(f"  successors('SU') = {reg.successors('SU')}   (no heir recorded in the tree)")
    print(f"  successors('YU') = {reg.successors('YU')}   (two active heirs)")
    print(f"  is_active_on('CS', '1991-06-01') = {reg.is_active_on('CS', '1991-06-01')}"
          "   (CS holds one entry, Serbia and Montenegro, assigned 2003-07-23; Czechoslovakia's older CS is not split out)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
