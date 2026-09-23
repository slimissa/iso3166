"""
iso3166-registry — a canonical, versioned, machine-readable registry
of ISO 3166 country codes.

Public API:

    from iso3166 import CountryRegistry, Country, RegistryError

    reg = CountryRegistry()
    us = reg.active("US")

The bundled registry file is iso3166.json, shipped inside this package.
"""
from .registry import Country, CountryRegistry, RegistryError

__all__ = ["Country", "CountryRegistry", "RegistryError"]
__version__ = "1.5.0"
