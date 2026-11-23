#!/usr/bin/env python3
"""Generate 10,000 SYNTHETIC trades, 1990-2024, from a fixed seed.

These are not real trades. They are a deterministic test bed with one
property: the country column mixes today's codes with codes that were
withdrawn from ISO 3166-1 during the period (SU, DD, YU, ZR, ...), the way a
long-lived trade database does.

    python3 generate_fake_trades.py            # CSV on stdout
    python3 generate_fake_trades.py --out FILE

Columns: trade_id, trade_date, country, notional_usd, truth.

`truth` is the generator's own label, written from raw dates and never from
is_active_on, so analyze.py can check its answers against something that did
not come from the query under test:

    valid       the code existed on trade_date
    stale_code  a withdrawn code used AFTER its withdrawal date (a legacy
                system still emitting YU in 2010): a data-quality bug

About 2 percent of trades are stale_code. Country weights are integers, so the
draw does not depend on floating-point rounding; the stdlib `random` module
with a fixed seed gives the same file on every supported Python 3.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "wrappers" / "python"))

from iso3166 import CountryRegistry  # noqa: E402

SEED = 3166
N_TRADES = 10_000
START = dt.date(1990, 1, 1)
END = dt.date(2024, 12, 31)
STALE_PERCENT = 2

# Weights are integers (tenths of a percent of the pool, roughly). Every
# code named here must exist in the registry; the generator asserts it.
ACTIVE_WEIGHTS = {
    # large, always-active countries
    "US": 180, "CN": 120, "DE": 100, "GB": 90, "JP": 90, "FR": 60, "CA": 40,
    "IN": 40, "BR": 30, "AU": 30, "KR": 30, "CH": 30, "NL": 30, "IT": 30,
    "ES": 30, "SG": 30,
    # active codes whose `introduced` date is null in the registry
    "RU": 50, "UA": 20, "CZ": 20, "SK": 10, "KZ": 10, "LT": 10, "CD": 10,
    # successor states created inside the period
    "RS": 10, "ME": 5, "TL": 3, "SS": 5,
}
OTHER_ACTIVE_WEIGHT = 2          # every other active code
LEGACY_WEIGHTS = {               # withdrawn inside or at the start of the period
    "SU": 30, "DD": 10, "YD": 5, "YU": 15, "ZR": 10, "TP": 3, "AN": 8, "NT": 2,
}


def d2i(d: dt.date) -> int:
    return d.toordinal()


def i2d(i: int) -> str:
    return dt.date.fromordinal(i).isoformat()


def generate(reg: CountryRegistry, n: int = N_TRADES, seed: int = SEED) -> list[dict]:
    """Return n trade rows as dicts. Same arguments, same rows."""
    rng = random.Random(seed)
    active = {c.alpha_2: c for c in reg.all_active()}
    withdrawn = {c.alpha_2: c for c in reg.all_withdrawn()}
    for code in ACTIVE_WEIGHTS:
        assert code in active, f"{code} is not an active code in this registry"
    for code in LEGACY_WEIGHTS:
        assert code in withdrawn, f"{code} is not a withdrawn code in this registry"

    # The pool holds (code, kind) pairs: a code can be both active and
    # withdrawn (SK is Slovakia now and was Sikkim until 1975), so the kind
    # says which registry entry a draw refers to.
    legacy = sorted(LEGACY_WEIGHTS)
    pool = [(c, "active") for c in sorted(active)] + [(c, "legacy") for c in legacy]
    pool_weights = ([ACTIVE_WEIGHTS.get(c, OTHER_ACTIVE_WEIGHT) for c in sorted(active)]
                    + [LEGACY_WEIGHTS[c] for c in legacy])
    legacy_weights = [LEGACY_WEIGHTS[c] for c in legacy]

    lo_all, hi_all = d2i(START), d2i(END)
    rows = []
    for trade_id in range(1, n + 1):
        if rng.randrange(100) < STALE_PERCENT:
            # A withdrawn code used after its withdrawal date.
            code = rng.choices(legacy, legacy_weights)[0]
            gone = d2i(dt.date.fromisoformat(withdrawn[code].withdrawal_date))
            lo, hi, truth = max(gone + 1, lo_all), hi_all, "stale_code"
        else:
            code, kind = rng.choices(pool, pool_weights)[0]
            lo, hi, truth = lo_all, hi_all, "valid"
            if kind == "legacy":
                gone = d2i(dt.date.fromisoformat(withdrawn[code].withdrawal_date))
                hi = min(gone, hi_all)
            elif active[code].introduced:
                lo = max(lo_all, d2i(dt.date.fromisoformat(active[code].introduced)))
        assert lo <= hi, f"empty date window for {code}"
        rows.append({
            "trade_id": trade_id,
            "trade_date": i2d(rng.randrange(lo, hi + 1)),
            "country": code,
            "notional_usd": rng.randrange(1, 1000) * 1000,
            "truth": truth,
        })
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="write the CSV here instead of stdout")
    ap.add_argument("--registry", default=str(ROOT / "iso3166.json"))
    args = ap.parse_args(argv)
    rows = generate(CountryRegistry(args.registry))
    out = open(args.out, "w", newline="", encoding="utf-8") if args.out else sys.stdout
    try:
        w = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    finally:
        if args.out:
            out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
