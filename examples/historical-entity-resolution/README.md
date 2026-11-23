# Historical entity resolution

A trade database that spans 1990 to 2024 holds country codes that no longer
exist: `SU`, `DD`, `YU`, `ZR`, `AN`. A validator that checks each code against
today's list rejects every one of them, including the trades that were correct
the day they were booked. This example runs three validators over the same
10,000 trades and shows what each one gets wrong.

**Data.** The trades are synthetic: `generate_fake_trades.py` writes 10,000
rows from seed 3166, dated 1990-01-01 to 2024-12-31, with weighted country
codes. About 2 percent are deliberately wrong: a withdrawn code used after its
withdrawal date, as a legacy system might still emit it. The generator labels
each row `valid` or `stale_code` from raw dates, never from `is_active_on`, so
the answers can be checked against something the query did not produce. The
registry is the repository's real `iso3166.json`.

## The failures

1. **Naive: is the code in today's list?** It rejects 672 trades. 483 of them
   are genuine, correct trades in withdrawn codes, and 189 are bugs, and the
   validator gives the same answer for both. A report built on it silently
   loses the Soviet and Yugoslav years.
2. **Silent-fail: `if reg.is_active_on(code, date):`.** The query is
   tri-state. `true` and `false` are answers; `null` means the registry's
   source is silent about when the code began. `None` is falsy, so the `if`
   drops all 1,667 of those trades (76 distinct codes, among them `RU`, `CZ` and
   `UA`), every one of them valid. That is 16.7 percent of the data, gone with
   no error.

## The solutions

3. **Temporal: `is_active_on(code, trade_date)`, read with `is True`,
   `is False` and `is None`.** It accepts the genuine legacy trades, catches
   all 189 stale codes, and has no false accepts or false rejects against the
   generator's labels. The `null` rows are not rejected and not accepted: they
   are a third list, to be reviewed or resolved by another source.

For the legacy codes that are accepted, `successors(code)` rolls them up to
today's countries where the tree has exactly one active heir (`DD` to `DE`,
`ZR` to `CD`, `TP` to `TL`, `YD` to `YE`), reports the candidates where it has
several (`YU` to `ME` or `RS`, `AN` to `BQ`, `CW` or `SX`), and says
"unresolved" where it has none (`SU`, `NT`). A rollup that picked one of
several heirs would be a guess; this one does not.

## Output

```text
Historical entity resolution: 10,000 synthetic trades, 1990-01-01 to 2024-12-31
seed 3166; generator truth: 9,811 valid, 189 stale_code; notional $5,001,005,000

== Scenario 1: naive (is the code in today's list?) ==
accepted : 9,328 (93.3%)
rejected : 672 (6.7%), notional $338,940,000
  genuine trades rejected (truth=valid): 483, notional $243,124,000
  bugs rejected (truth=stale_code)     : 189
  rejected codes: SU 238, YU 114, DD 84, ZR 77, AN 72, YD 37, NT 27, TP 23
verdict  : every genuine SU, DD, YU, ZR ... trade is rejected, and it is
           rejected for the same reason as the bugs. Nothing tells them apart.

== Scenario 2: temporal (is_active_on at the trade date) ==
true     : 8,144 (81.4%)   the code existed that day
false    : 189 (1.9%)   the code did not exist that day
null     : 1,667 (16.7%)   the registry does not know
check against truth: stale_code caught 189 of 189; false accepts 0; false rejects 0
  null: 76 distinct codes, introduced date not recorded; top: RU 316, CZ 129, UA 115, CD 71, LT 67, SK 59, KZ 52, GP 23

Withdrawn codes in valid trades, rolled up to today's countries:
  AN    48 trades    $22,585,000  -> ambiguous  BQ, CW, SX
  DD    55 trades    $27,376,000  -> resolved   DE
  NT    20 trades     $9,693,000  -> unresolved -
  SU   172 trades    $88,892,000  -> unresolved -
  TP    16 trades     $6,887,000  -> resolved   TL
  YD    30 trades    $16,583,000  -> resolved   YE
  YU    85 trades    $43,808,000  -> ambiguous  ME, RS
  ZR    57 trades    $27,300,000  -> resolved   CD
  ambiguous 133, resolved 158, unresolved 192
verdict  : genuine legacy trades are kept and the bugs are caught. Where the
           tree has one heir the trade rolls up; with several or none it does
           not, and the output says so instead of guessing.

== Scenario 3: silent-fail (the answer read with `if`) ==
`if is_active_on(...)` accepts 8,144 (81.4%)
scenario 2 accepts true + null  9,811 (98.1%)
silently dropped by `if`: 1,667 trades, notional $830,233,000, all truth=valid: True
  dropped codes: RU 316, CZ 129, UA 115, CD 71, LT 67, SK 59, KZ 52, GP 23
verdict  : None is falsy. The query says "the source is silent" and `if`
           reads that as "no". Test `is True`, `is False`, `is None`.

A malformed date is not silent any more (v1.12.5):
  is_active_on('DE', '1990-13-45') raises ValueError: malformed date: '1990-13-45' (want YYYY-MM-DD)
  is_active_on('DE', datetime.date(1990, 1, 1)) -> True
  is_active_on('XX', '1990-01-01') -> False   (unknown code: known not to exist)
  is_active_on('RU', '1990-01-01') -> None   (introduced date not recorded)

== Honest limits, as the registry answers them ==
  successors('SU') = []   (no heir recorded in the tree)
  successors('YU') = ['CS', 'ME', 'RS']   (two active heirs)
  is_active_on('CS', '1991-06-01') = True   (CS holds one entry, Serbia and Montenegro; the older meaning is not split out)
```

## Honest limits

- **The trades are made up.** The 2 percent of bad rows, the weights and the
  dates are the generator's choices. The example shows the mechanism catches a
  known mistake; it says nothing about how often real systems make it.
- **The answer to "which rows are unknown" depends on the registry.** 76 active
  codes have no recorded `introduced` date, far more than the 27 that carry a
  documented quarantine reason. `null` is the registry saying it will not guess.
  If a later release fills in dates, the numbers and `expected_output.txt`
  change, and the diff shows exactly which rows moved.
- **`SU` has no heir.** The tree records none, so 172 genuine `SU` trades stay
  unresolved. Splitting them among the successor states needs a source
  the registry does not hold.
- **Reused codes are one entry.** `CS` was Czechoslovakia and later Serbia and
  Montenegro; the registry holds the later entry, and `is_active_on("CS",
  "1991-06-01")` answers `true` for it. The older meaning is not split out.
- **Dates only.** The query answers whether a code existed on a day, not
  whether a country's borders, name or currency were what the trade assumed.

## Run it

```bash
python3 examples/historical-entity-resolution/analyze.py
python3 examples/historical-entity-resolution/generate_fake_trades.py --out trades.csv
```

`analyze.py` does not need the CSV; it calls the generator directly.
