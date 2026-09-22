# ISO 3166 Country Registry

**A canonical, versioned, machine-readable registry of ISO 3166 country codes.**

One JSON file. Zero runtime dependencies. Four language wrappers. Same
architecture as [`slimissa/iso4217`](https://github.com/slimissa/iso4217).

> **Status: v0.1.0 — foundation only.** The schema, registry data,
> exports, CLI, and wrappers land over the phases tracked in
> [`docs/decisions/v1.0.0-decisions.md`](./docs/decisions/v1.0.0-decisions.md).
> Nothing here is stable yet.

## What this will be

Every system that touches international finance, trade, shipping, or
identity maintains its own country list. They drift. Some use alpha-3,
some alpha-2, some numeric. Some include territories, some merge them.

This registry provides one versioned, schema-validated JSON file that
any tool can depend on. The JSON is the contract. The SQL, CSV,
Parquet, CLI, and wrappers are five ways to consume it without writing
a parser.

## Links

- [Locked decisions for v1.0.0](./docs/decisions/v1.0.0-decisions.md)
- [Sibling registry: ISO 4217 currencies](https://github.com/slimissa/iso4217)
- [Sibling registry: Exchange Calendar](https://github.com/slimissa/exchange-calendar)

## License

Apache 2.0. See [`LICENSE`](./LICENSE).
