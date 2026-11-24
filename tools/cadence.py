"""The review_by cadence rule, in one place.

refresh_cadence is "monthly", "quarterly" or "yearly", and
review_by = vendored_at + 1 cadence period: 1, 3 or 12 calendar months,
same day of month, clamped to the target month's last day
(2026-11-30 + 3 months = 2027-02-28).

Ported from slimissa/iso10383: CADENCE_MONTHS and add_months are the
definitions in tests/test_snapshot_meta.py at tag v1.1.9 (857cc31); the
module shape and review_by() follow its tools/cadence.py, added on main
in d41329e after that tag. Used by tests/test_snapshot_meta.py.
"""

import calendar
from datetime import date

CADENCE_MONTHS = {"monthly": 1, "quarterly": 3, "yearly": 12}


def add_months(d: date, n: int) -> date:
    """d plus n calendar months, same day, clamped to the target month's last day."""
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def review_by(vendored_at: str, cadence: str) -> str:
    """review_by (YYYY-MM-DD) for a vendored_at date and a refresh_cadence."""
    if cadence not in CADENCE_MONTHS:
        raise ValueError(f"refresh_cadence {cadence!r} not in {sorted(CADENCE_MONTHS)}")
    return add_months(date.fromisoformat(vendored_at), CADENCE_MONTHS[cadence]).isoformat()
