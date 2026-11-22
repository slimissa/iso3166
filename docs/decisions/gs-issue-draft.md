# Draft: the currency of `GS` (FKP or GBP)

Status: **not filed.** A draft of an issue for `slimissa/iso3166`. No issue
number exists, and none is made up here. The decision record is the section
"Open request: the currency of `GS`" in
[`cross-registry-edges.md`](./cross-registry-edges.md); it holds the state,
the three options and the reason the value of `GS` was not changed in
v1.12.4.

When the issue is filed, record its number on the `Issue:` line of that
section, and set the status line above to the issue's number.

## Issue text

**Title:** `GS` currency: FKP or GBP?

**Body:**

> ISO 4217's country-currency allow-list
> (`docs/COUNTRY_CURRENCY_ALLOWLIST.md`, ADR 0010 row GS) lists the `GS`
> pair as `fix-in-3166`: this registry says `FKP`, ISO 4217's registry says
> `GBP`. Secondary mirrors show "No universal currency" for `GS`. Decide
> `GBP`, `FKP` or `null`, record the source, and tell ISO 4217 so it can
> update its allow-list on its next re-vendor.
