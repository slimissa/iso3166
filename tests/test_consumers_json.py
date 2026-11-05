"""tools/consumers.json is well formed and agrees with docs/JOINS.md and the README."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONSUMERS = json.loads((ROOT / "tools" / "consumers.json").read_text(encoding="utf-8"))["consumers"]
JOINS = (ROOT / "docs" / "JOINS.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
FIELDS = {"alpha_2", "name", "region", "subregion", "currency_codes", "independent"}


def test_three_consumers_with_the_required_keys():
    assert len(CONSUMERS) == 3
    for c in CONSUMERS:
        assert set(c) == {"name", "repo", "snapshot_path", "fields_read"}
        assert re.fullmatch(r"[\w.-]+/[\w.-]+", c["repo"])
        assert c["snapshot_path"].endswith("_snapshot.json")
        assert c["fields_read"] and set(c["fields_read"]) <= FIELDS


def test_names_and_repos_are_unique():
    assert len({c["name"] for c in CONSUMERS}) == 3
    assert len({c["repo"] for c in CONSUMERS}) == 3


def test_every_field_read_is_in_joins_md_in_that_consumers_row():
    rows = {m.group(1): m.group(0)
            for m in re.finditer(r"^\| `(\w+)` \|.*$", JOINS, re.M)}
    for c in CONSUMERS:
        for f in c["fields_read"]:
            assert c["name"] in rows[f], f"{c['name']} reads {f} but JOINS.md does not say so"


def test_every_consumer_is_linked_in_readme_section_22():
    section = README.split("## 22. Consumed by", 1)[1].split("## 23.", 1)[0]
    for c in CONSUMERS:
        assert f"https://github.com/{c['repo']}" in section
