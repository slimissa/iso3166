"""
tools/patterns.py

Regular expressions shared by more than one tool. A pattern that two
tools both need lives here, so the tools cannot drift apart.

This is a plain module, not a package: the tools run as scripts, so
Python puts tools/ itself on sys.path, and a sibling imports it with

    from patterns import CALLING_CODE_RE

A tool that may be loaded by path (for example from a test) first adds
its own directory to sys.path, as enrich_field.py does.
"""
from __future__ import annotations

import re

# ITU-T E.164 country calling codes. The hyphen form (e.g. "1-340")
# is used for sub-prefixes under a shared root.
CALLING_CODE_RE = re.compile(r"^[0-9]+(-[0-9]+)?$")
