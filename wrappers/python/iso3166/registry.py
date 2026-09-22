"""
iso3166.registry — load and query the ISO 3166 country registry.

    from iso3166 import CountryRegistry

    reg = CountryRegistry()
    us = reg.active("US")
    if us is not None:
        print(us.alpha_3, us.name)

The registry file is bundled inside the package. An alternative path
can be passed to the constructor.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional


__all__ = ["Country", "CountryRegistry", "RegistryError"]


ACTIVE_STATUSES = frozenset({
    "officially-assigned",
    "user-assigned",
    "exceptionally-reserved",
})


class RegistryError(Exception):
    """Raised when the registry file cannot be loaded."""


@dataclass(frozen=True)
class Country:
    """One country entry from the registry."""

    alpha_2: str
    alpha_3: str
    numeric: str
    name: str
    status: str
    independent: bool
    official_name: Optional[str] = None
    region: Optional[str] = None
    subregion: Optional[str] = None
    intermediate_region: Optional[str] = None
    currency_codes: Optional[list[str]] = None
    calling_codes: Optional[list[str]] = None
    tlds: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    borders: Optional[list[str]] = None
    note: Optional[str] = None
    last_verified: Optional[str] = None
    withdrawal_date: Optional[str] = None
    replaced_by: Optional[list[str]] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Country":
        return cls(
            alpha_2=d["alpha_2"],
            alpha_3=d["alpha_3"],
            numeric=d["numeric"],
            name=d["name"],
            status=d["status"],
            independent=d["independent"],
            official_name=d.get("official_name"),
            region=d.get("region"),
            subregion=d.get("subregion"),
            intermediate_region=d.get("intermediate_region"),
            currency_codes=d.get("currency_codes"),
            calling_codes=d.get("calling_codes"),
            tlds=d.get("tlds"),
            languages=d.get("languages"),
            borders=d.get("borders"),
            note=d.get("note"),
            last_verified=d.get("last_verified"),
            withdrawal_date=d.get("withdrawal_date"),
            replaced_by=d.get("replaced_by"),
        )

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES


def _default_registry_path() -> Path:
    return Path(__file__).resolve().parent / "iso3166.json"


class CountryRegistry:
    """Load and query the ISO 3166 registry.

    The registry is loaded once at construction. All lookups return
    Country instances (immutable); no method mutates internal state.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        p = Path(path) if path is not None else _default_registry_path()
        if not p.exists():
            raise RegistryError(f"registry not found: {p}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RegistryError(f"{p}: invalid JSON: {exc}") from exc

        self._path = p
        self._meta: dict[str, Any] = data.get("meta", {})

        countries = data.get("countries", {})
        self._active: list[Country] = [
            Country.from_dict(e) for e in countries.get("active", [])
        ]
        self._withdrawn: list[Country] = [
            Country.from_dict(e) for e in countries.get("withdrawn", [])
        ]
        self._all: list[Country] = self._active + self._withdrawn

        # Indexes: preferred (active) entry per key.
        self._by_alpha2: dict[str, Country] = {}
        for c in self._active:
            self._by_alpha2[c.alpha_2] = c
        self._by_alpha3: dict[str, Country] = {c.alpha_3: c for c in self._active}
        self._by_numeric: dict[str, Country] = {c.numeric: c for c in self._active}

    # ------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------

    @property
    def path(self) -> Path:
        return self._path

    @property
    def meta(self) -> dict[str, Any]:
        return dict(self._meta)

    @property
    def version(self) -> str:
        return str(self._meta.get("version", ""))

    @property
    def updated(self) -> str:
        return str(self._meta.get("updated", ""))

    # ------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------

    def all(self) -> list[Country]:
        """All entries, active first, then withdrawn, each sorted by alpha_2."""
        return list(self._all)

    def all_active(self) -> list[Country]:
        return list(self._active)

    def all_withdrawn(self) -> list[Country]:
        return list(self._withdrawn)

    def __iter__(self) -> Iterator[Country]:
        return iter(self._all)

    def __len__(self) -> int:
        return len(self._all)

    # ------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------

    def active(self, alpha_2: str) -> Optional[Country]:
        """Look up by alpha-2. Case-insensitive. Returns None if absent.

        Only active entries are returned; withdrawn codes are reachable
        via with_alpha2.
        """
        return self._by_alpha2.get(alpha_2.upper())

    def with_alpha2(self, alpha_2: str) -> list[Country]:
        """All entries (active and withdrawn) with this alpha-2 code.

        A small number of codes appear twice because ISO reassigned them
        (AI, SK). Callers who want a single entry should use active().
        """
        code = alpha_2.upper()
        return [c for c in self._all if c.alpha_2 == code]

    def by_alpha2(self, alpha_2: str) -> Optional[Country]:
        """Alias for active(). Kept for API symmetry with by_alpha3/by_numeric."""
        return self.active(alpha_2)

    def by_alpha3(self, alpha_3: str) -> Optional[Country]:
        return self._by_alpha3.get(alpha_3.upper())

    def by_numeric(self, numeric: str) -> Optional[Country]:
        return self._by_numeric.get(str(numeric).zfill(3))

    # ------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------

    def currencies(self, alpha_2: str) -> list[str]:
        c = self.active(alpha_2)
        if c is None or not c.currency_codes:
            return []
        return list(c.currency_codes)

    def countries_with(self, currency_code: str) -> list[Country]:
        code = currency_code.upper()
        return [
            c for c in self._active
            if c.currency_codes and code in c.currency_codes
        ]

    def region(self, region_name: str) -> list[Country]:
        target = region_name.lower()
        return [
            c for c in self._active
            if (c.region or "").lower() == target
        ]

    def subregion(self, subregion_name: str) -> list[Country]:
        target = subregion_name.lower()
        return [
            c for c in self._active
            if (c.subregion or "").lower() == target
        ]

    def search(self, query: str) -> list[Country]:
        """Substring search on name, official_name, alpha_2, alpha_3."""
        q = query.lower()
        out: list[Country] = []
        for c in self._all:
            haystack = " ".join(filter(None, [
                c.name, c.official_name, c.alpha_2, c.alpha_3,
            ])).lower()
            if q in haystack:
                out.append(c)
        return out

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for c in self._all:
            by_status[c.status] = by_status.get(c.status, 0) + 1
        return {
            "version": self.version,
            "updated": self.updated,
            "total": len(self._all),
            "active": len(self._active),
            "withdrawn": len(self._withdrawn),
            "by_status": by_status,
        }
