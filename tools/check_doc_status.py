#!/usr/bin/env python3
"""
check_doc_status.py: fails when a document's status line is overdue.

A status line opens a paragraph with `Status as of vX.Y.Z` and says when the
page was last read against the tree. It must carry a recheck date:

    Status as of v1.12.14 (recheck 2027-05-25). ...

The date is when the page is to be read against the tree again. Without a
gate a page goes stale silently; this check turns each date into a red build
on the day after it. Modelled on tools/check_recheck_dates.py in
slimissa/exchange-calendar (ab01489).

What is scanned
---------------
README.md, CONTRIBUTING.md and every docs/**/*.md. A status line is a line
that starts with `Status as of v`. Each one must read
`Status as of vX.Y.Z (recheck YYYY-MM-DD)`, and X.Y.Z must not be later than
VERSION.

When a date has passed
----------------------
A recheck date D has passed when D is earlier than --today (default: today).
On D itself the check passes: the recheck is due that day, not overdue.

Exit codes
----------
    0  every status line carries a recheck date that has not passed
    1  a recheck date has passed, a status line has no recheck date, or a
       status line names a version later than VERSION
    2  usage or parse problem: no repository root, or a recheck date that is
       not a valid YYYY-MM-DD date

Usage
-----
    python3 tools/check_doc_status.py
    python3 tools/check_doc_status.py --today 2027-06-01
    python3 tools/check_doc_status.py --root path/to/repo
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
STATUS_RE = re.compile(r"^Status as of v(\d+)\.(\d+)\.(\d+)(.*)$")
RECHECK_RE = re.compile(r"^ \(recheck (\S+?)\)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class StatusError(ValueError):
    """A recheck date that cannot be read as a date."""


@dataclass(frozen=True)
class Status:
    path: str
    line: int
    version: tuple
    recheck: date | None

    def where(self) -> str:
        return f"{self.path}:{self.line}"


def _files(root: Path) -> list[Path]:
    files = [root / "README.md", root / "CONTRIBUTING.md"]
    files += sorted((root / "docs").rglob("*.md")) if (root / "docs").is_dir() else []
    return [f for f in files if f.is_file()]


def collect(root: Path = DEFAULT_ROOT) -> list[Status]:
    """Every status line under root, in file order."""
    if not (root / "VERSION").is_file():
        raise FileNotFoundError(f"no VERSION file under {root}")
    found = []
    for f in _files(root):
        rel = f.relative_to(root).as_posix()
        for n, text in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            m = STATUS_RE.match(text)
            if not m:
                continue
            version = tuple(int(x) for x in m.group(1, 2, 3))
            r = RECHECK_RE.match(m.group(4))
            recheck = None
            if r:
                value = r.group(1)
                if not DATE_RE.match(value):
                    raise StatusError(f"{rel}:{n}: recheck date is not YYYY-MM-DD: {value!r}")
                try:
                    recheck = date.fromisoformat(value)
                except ValueError as exc:
                    raise StatusError(f"{rel}:{n}: recheck date is not a valid date: {value!r}") from exc
            found.append(Status(rel, n, version, recheck))
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(),
                        help="reference date, YYYY-MM-DD (default: today)")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                        help="repository root")
    args = parser.parse_args(argv)
    try:
        statuses = collect(args.root)
        current = tuple(int(x) for x in (args.root / "VERSION").read_text().strip().split("."))
    except (OSError, StatusError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    bad = []
    for s in statuses:
        v = "v" + ".".join(map(str, s.version))
        if s.recheck is None:
            bad.append(f"NO RECHECK: {s.where()} {v}: write 'Status as of {v} (recheck YYYY-MM-DD)'")
        elif s.recheck < args.today:
            bad.append(f"PASSED: {s.where()} {v} recheck {s.recheck.isoformat()}")
        else:
            print(f"due: {s.where()} {v} recheck {s.recheck.isoformat()}")
        if s.version > current:
            bad.append(f"FUTURE: {s.where()} {v} is later than VERSION {'.'.join(map(str, current))}")
    for line in bad:
        print(line)
    if bad:
        print(f"FAIL: {len(bad)} status line problem(s) on {args.today.isoformat()}; "
              "read the page against the tree, fix what is stale, then set a new "
              "version and recheck date.")
        return 1
    print(f"OK: {len(statuses)} status line(s), no recheck date before {args.today.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
