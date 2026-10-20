#!/usr/bin/env python3
"""One-shot migration of active-entry notes to per-field source citations.

Before v1.7.2 every enrich_field.py run replaced the previous run's bare
`source: <url>` line, so a note kept only the LAST field's citation.
From v1.7.2 each enriched field has its own `<field> source: <url>` line.

The URL enrich_field.py records is a pure function of (field, alpha-2):
FIELDS[field].source_template.format(code=alpha_2). The overwritten
citations are therefore reconstructible exactly; nothing has to be
guessed. The one surviving bare `source:` line is used as a cross-check:
it must equal the template URL of at least one populated field, or the
entry is left untouched and reported as flagged.

Rules per active entry:
  * no bare `source:` line            -> unchanged
  * bare line matches no populated
    field's template                   -> unchanged, FLAGGED (manual review)
  * otherwise the bare line is replaced, in place, by one
    `<field> source: <template url>` line for every populated field
    (value is not None) that has no per-field line yet, in the canonical
    order of enrich_field.FIELDS. Every other line (official_name source,
    prose) is preserved. If more than one field line was emitted, one
    marker line records that the split was reconstructed.
  * official_name is never invented: a populated official_name with no
    `official_name source:` line is counted and reported, not cited.

Usage:
    python3 tools/migrate_notes_to_per_field.py --dry-run
    python3 tools/migrate_notes_to_per_field.py --write
    python3 tools/migrate_notes_to_per_field.py --write --date 2026-10-20

Idempotent: a second --write run reports 0 changes.
Exit codes: 0 success, 1 flagged entries present (still written for the
rest when --write), 2 usage / IO error.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enrich_field as ef  # noqa: E402  (single source of truth for templates)

BARE_PREFIX = "source: "
MARKER_PREFIX = "# per-field sources reconstructed from enrich_field.py templates on "
MARKER_SUFFIX = "; pre-v1.7.2 notes kept only the last source"


def migrate_note(entry: dict, today: str) -> tuple[str | None, str]:
    """Return (new_note_or_None, status).

    status is one of: "unchanged", "flagged", "single", "split".
    new_note is None unless status in ("single", "split").
    """
    note = entry.get("note")
    if not note:
        return None, "unchanged"
    lines = note.split("\n")
    bare_idx = [i for i, l in enumerate(lines) if l.startswith(BARE_PREFIX)]
    if not bare_idx:
        return None, "unchanged"

    code = entry["alpha_2"]
    populated = [f for f in ef.FIELDS if entry.get(f) is not None]
    urls = {f: ef.FIELDS[f].source_template.format(code=code) for f in populated}

    survivors = {lines[i][len(BARE_PREFIX):] for i in bare_idx}
    if not survivors & set(urls.values()):
        return None, "flagged"

    have = {f for f in ef.FIELDS
            if any(l.startswith(f"{f} source:") for l in lines)}
    emit = [f"{f} source: {urls[f]}" for f in populated if f not in have]

    out: list[str] = []
    placed = False
    for i, l in enumerate(lines):
        if i in bare_idx:
            if not placed:
                out.extend(emit)
                if len(emit) > 1:
                    out.append(f"{MARKER_PREFIX}{today}{MARKER_SUFFIX}")
                placed = True
            continue
        out.append(l)
    return "\n".join(out), ("split" if len(emit) > 1 else "single")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--write", action="store_true")
    ap.add_argument("--date", default=date.today().isoformat(),
                    help="date recorded in the marker line (default: today)")
    ap.add_argument("--registry", type=Path, default=ef.REGISTRY)
    args = ap.parse_args()

    try:
        reg = ef.load_registry(args.registry)
    except (OSError, SystemExit) as exc:
        print(f"error: cannot load {args.registry}: {exc}", file=sys.stderr)
        return 2

    active = reg["countries"]["active"]
    counts = {"single": 0, "split": 0, "unchanged": 0, "flagged": 0}
    flagged: list[str] = []
    no_on_source: list[str] = []
    changes = 0
    for e in active:
        if e.get("official_name") is not None and not any(
                l.startswith("official_name source:")
                for l in (e.get("note") or "").split("\n")):
            no_on_source.append(e["alpha_2"])
        new, status = migrate_note(e, args.date)
        counts[status] += 1
        if status == "flagged":
            flagged.append(e["alpha_2"])
        if new is not None:
            changes += 1
            if args.write:
                e["note"] = new

    total = sum(counts.values())
    assert total == len(active)
    print(f"{total} entries scanned; {counts['single']} had one per-field "
          f"citation reconstructed; {counts['split']} had a shared citation "
          f"split across several fields; {counts['unchanged']} unchanged; "
          f"{counts['flagged']} flagged")
    if flagged:
        print(f"  flagged (surviving URL matches no populated field; left "
              f"untouched, review by hand): {', '.join(flagged)}")
    if no_on_source:
        print(f"  official_name populated but never cited (not invented): "
              f"{', '.join(no_on_source)}")
    print(f"{changes} changes" + (" written" if args.write and changes else
                                  " (dry run)" if args.dry_run else ""))
    if args.write and changes:
        ef.write_registry(args.registry, reg)
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
