# Input contract

## Status

Accepted — 2026-10-21. Implemented in v1.8.0.

## Context

The four language wrappers (Python, JavaScript, Rust, Go) were built from
the same JSON registry but evolved their own edge-case behavior. An audit
found 22 consumer-visible divergences on three themes: empty-string
arguments, sentinel numeric codes (`"000"`), and withdrawn-entry
behavior. Examples, measured on v1.7.4: several active entries share the
placeholder numeric `"000"`, so `by_numeric("000")` returned Kosovo (`XK`)
in all four wrappers; `by_numeric("")` also returned `XK` in Python,
JavaScript and Rust (they pad `""` to `"000"`) but nothing in Go;
`search("")` returned every entry in Python, JavaScript and Rust but
nothing in Go.

The JSON is the contract. A consumer who switches language must not
see different answers for the same call. These decisions were deferred
through v1.7.x and are fixed here.

## Decision

### Empty-string inputs

| Call | Behavior |
|------|----------|
| `active("")`, `by_alpha2("")`, `by_alpha3("")`, `by_numeric("")` | None / null / nil |
| `region("")`, `subregion("")`, `search("")`, `countries_with("")` | `[]` / empty slice |

`region("")` and `subregion("")` return an empty list. They do not mean
"all entries with a null region". This changes Python, JavaScript and
Rust; Go already behaved this way.

### Numeric inputs

| Call | Behavior |
|------|----------|
| `by_numeric("000")` | None (sentinel, never a valid key) |
| `by_numeric("0")` | None (single digit → "000" → sentinel) |
| `by_numeric("20")` | AD (left-pad to 3 digits) |
| `by_numeric("020")` | AD (exact) |
| `by_numeric(20)` | AD (coerce int to string, then pad). Python and JavaScript only; Rust and Go reject non-string arguments at compile time |
| `by_numeric(" 20")`, `by_numeric("020 ")` | None (whitespace is not trimmed) |

### Withdrawn entries

| Call | Behavior |
|------|----------|
| `active("AN")`, `by_alpha2("AN")` | None (active-only) |
| `by_alpha3("ANT")`, `by_numeric("530")` | None (active-only) |
| `with_alpha2("AN")` | `[withdrawn_AN]` |
| `with_alpha2("AI")` | `[active_Anguilla, withdrawn_African_Afars]` (active-first ordering, pinned) |
| `with_alpha3("ANT")` | `[withdrawn_AN]` (new, for symmetry) |
| `with_numeric("530")` | `[withdrawn_AN]` (new, for symmetry) |

### CLI

`iso3166 lookup AN` keeps returning the withdrawn record. A new
`--active-only` flag on `lookup` returns not-found (exit 1) for
withdrawn codes, matching the library's `active()`.
`iso3166 validate AN` keeps exiting 0, because AN exists in the registry.

### Immutability

- Python: list fields of `Country` become `tuple[str, ...]`.
- JavaScript: list fields are deep-frozen in `makeCountry`.
- Go: `Active`, `ByAlpha2`, `ByAlpha3`, `ByNumeric` return `Country` by
  value instead of `*Country`. The returned value owns private copies of
  its slice and pointer fields, so mutating it cannot reach the registry.
  `Country.Exists()` reports whether a lookup found anything.
- Rust: no change; lookups already return `&Country`.

## Consequences

Breaking changes, all shipped together in v1.8.0:

- **Python.** `currency_codes`, `calling_codes`, `tlds`, `languages`,
  `borders`, `replaced_by` are tuples. Code that tests
  `isinstance(x, list)` or calls `.append` on them breaks.
  `by_numeric("000")`, `by_numeric("0")` and `by_numeric("")` now return
  None. `region("")`, `subregion("")`, `search("")` and
  `countries_with("")` return `[]`.
- **JavaScript.** List fields are frozen; `push`, `sort` and other
  in-place mutation throw `TypeError`. `byNumeric("000")`, `"0"`, `""`
  return null. `search("")` returns `[]` (it previously returned every
  entry); `region("")` and `subregion("")` return `[]` (they previously
  returned the entries with no region or sub-region).
- **Rust.** No signature changes. `by_numeric` rejects `""` and the
  sentinel (it returned `XK` for both). `search("")` returns an empty
  `Vec` (it returned every entry). `region("")`, `subregion("")` and
  `countries_with("")` already returned an empty `Vec` and still do.
- **Go.** `Active`, `ByAlpha2`, `ByAlpha3`, `ByNumeric` return `Country`,
  not `*Country`. `== nil` no longer compiles. Collection queries
  (`All`, `Region`, `Search`, ...) still return `[]*Country`; treat those
  entries as read-only.

New API: `with_alpha3`, `with_numeric` (Python, Rust), `withAlpha3`,
`withNumeric` (JavaScript), `WithAlpha3`, `WithNumeric` (Go).

## Migration

**Python.** Consumers who do `isinstance(c.currency_codes, list)` must
switch to `isinstance(c.currency_codes, tuple)` or to
`isinstance(..., (list, tuple))`. Code that needs a mutable copy calls
`list(c.currency_codes)`. Indexing, iteration, `in` and `len` are
unchanged. Callers that relied on `by_numeric("000")` returning an
entry must use `active()` or `by_alpha3()` instead.

**JavaScript.** Consumers who mutate list fields, for example
`us.currency_codes.push("X")` or `.sort()`, must copy first with
`[...us.currency_codes]` or `.slice()`. Callers that used
`search("")` to list everything must use `all()`.

**Rust.** No code changes are needed for compilation. Callers that
passed `""` or `"000"` to `by_numeric` and expected an entry now get
`None`. Callers that used `search("")` to list everything must use
`all_active()` and `all_withdrawn()`.

**Go.** Replace `if c := reg.Active("US"); c != nil` with
`if c := reg.Active("US"); c.Exists()`. Replace `c == nil` with
`!c.Exists()`. Code that stored `*Country` from these four methods
must store `Country`. Values are safe to modify locally; changes do not
reach the registry.

## Alternatives considered

- **Wrappers define their own semantics.** Rejected. It contradicts
  "the JSON is the contract" and is the cause of the 22 divergences.
- **Coerce silently** (treat `""` as "no filter", or map `"000"` to the
  first entry that carries it). Rejected. Silent divergence is worse than
  a documented breaking change, and `"000"` is shared by several
  unrelated entries, so no single answer is correct.
- **Go: keep `*Country` and add `Copy()`.** Rejected. It relies on
  callers remembering not to mutate; value return makes the compiler
  enforce the break.
