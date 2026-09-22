# iso3166-registry (Python)

Python wrapper for the [ISO 3166 country registry](https://github.com/slimissa/iso3166).

## Install

From the repository:

```bash
pip install -e wrappers/python
```

This installs the `iso3166` command and the `iso3166` importable
package.

Publication to PyPI is tracked for v1.2.0.

## Library

```python
from iso3166 import CountryRegistry

reg = CountryRegistry()

us = reg.active("US")
print(us.alpha_3, us.name)              # USA United States of America
print(reg.by_numeric("840").alpha_2)    # US
print(reg.by_alpha3("GBR").name)        # United Kingdom of Great Britain and Northern Ireland
print(reg.region("Europe")[0].alpha_2)  # AD (sorted by alpha_2)
print(len(reg.search("united")))        # multiple
print(reg.summary())
```

`active()` returns `None` for an unknown code. Use `with_alpha2()` to
retrieve both the active and withdrawn entries for a reassigned code
such as `AI` or `SK`.

## CLI

```bash
iso3166 lookup US
iso3166 list --region Europe
iso3166 info
iso3166 validate US FR DE
```

See the [top-level README](https://github.com/slimissa/iso3166) for the
full CLI reference.

## Tests

```bash
python3 -m pytest wrappers/python/tests/
```

## License

Apache 2.0.