"use strict";

/**
 * iso3166-registry — a canonical, versioned, machine-readable registry
 * of ISO 3166 country codes.
 *
 * Usage:
 *
 *     const { CountryRegistry } = require("iso3166-registry");
 *     const reg = new CountryRegistry();
 *     const us = reg.active("US");
 *     if (us) console.log(us.alpha_3, us.name);
 *
 * The registry file is bundled inside the package
 * (./iso3166.json). An alternative path can be passed to the
 * constructor.
 *
 * API names mirror the Python wrapper's, after idiomatic casing.
 * Every lookup returns null (or an empty array) on a miss; nothing
 * throws except a missing or malformed registry file.
 */

const fs = require("node:fs");
const path = require("node:path");

const ACTIVE_STATUSES = new Set([
  "officially-assigned",
  "user-assigned",
  "exceptionally-reserved",
]);

class RegistryError extends Error {
  constructor(message) {
    super(message);
    this.name = "RegistryError";
  }
}

/**
 * Build a frozen Country from a raw registry entry. Extra keys are
 * ignored; missing keys become null so every Country has the same
 * shape.
 */
function makeCountry(raw) {
  return Object.freeze({
    alpha_2: raw.alpha_2,
    alpha_3: raw.alpha_3,
    numeric: raw.numeric,
    name: raw.name,
    status: raw.status,
    independent: raw.independent,
    official_name: raw.official_name ?? null,
    region: raw.region ?? null,
    subregion: raw.subregion ?? null,
    intermediate_region: raw.intermediate_region ?? null,
    currency_codes: raw.currency_codes ?? null,
    calling_codes: raw.calling_codes ?? null,
    tlds: raw.tlds ?? null,
    languages: raw.languages ?? null,
    borders: raw.borders ?? null,
    note: raw.note ?? null,
    last_verified: raw.last_verified ?? null,
    withdrawal_date: raw.withdrawal_date ?? null,
    replaced_by: raw.replaced_by ?? null,
  });
}

class CountryRegistry {
  /**
   * @param {string} [registryPath] Path to iso3166.json. Defaults to
   *   the copy bundled inside this package.
   */
  constructor(registryPath) {
    const p = registryPath
      ? path.resolve(registryPath)
      : path.join(__dirname, "iso3166.json");

    if (!fs.existsSync(p)) {
      throw new RegistryError(`registry not found: ${p}`);
    }

    let data;
    try {
      data = JSON.parse(fs.readFileSync(p, "utf-8"));
    } catch (err) {
      throw new RegistryError(`${p}: invalid JSON: ${err.message}`);
    }

    this._path = p;
    this._meta = data.meta ?? {};

    const countries = data.countries ?? {};
    this._active = (countries.active ?? []).map(makeCountry);
    this._withdrawn = (countries.withdrawn ?? []).map(makeCountry);
    this._all = [...this._active, ...this._withdrawn];

    // Preferred (active) entry per key. AI and SK each have two entries
    // overall; active wins for the simple lookups.
    this._byAlpha2 = new Map();
    for (const c of this._active) this._byAlpha2.set(c.alpha_2, c);
    this._byAlpha3 = new Map(this._active.map((c) => [c.alpha_3, c]));
    this._byNumeric = new Map(this._active.map((c) => [c.numeric, c]));
  }

  // ----------------------------------------------------------------
  // Metadata
  // ----------------------------------------------------------------

  get path() {
    return this._path;
  }

  get meta() {
    return { ...this._meta };
  }

  get version() {
    return String(this._meta.version ?? "");
  }

  get updated() {
    return String(this._meta.updated ?? "");
  }

  // ----------------------------------------------------------------
  // Collections
  // ----------------------------------------------------------------

  /** All entries, active first, then withdrawn, each sorted by alpha_2. */
  all() {
    return [...this._all];
  }

  allActive() {
    return [...this._active];
  }

  allWithdrawn() {
    return [...this._withdrawn];
  }

  // ----------------------------------------------------------------
  // Lookup
  // ----------------------------------------------------------------

  /**
   * Look up by alpha-2. Case-insensitive. Returns null if absent.
   * Only active entries; withdrawn codes are reachable via withAlpha2.
   */
  active(code) {
    if (typeof code !== "string") return null;
    return this._byAlpha2.get(code.toUpperCase()) ?? null;
  }

  /**
   * All entries (active and withdrawn) with this alpha-2 code.
   * A small number of codes appear twice because ISO reassigned them
   * (AI, SK). Callers who want a single entry should use active().
   */
  withAlpha2(code) {
    if (typeof code !== "string") return [];
    const upper = code.toUpperCase();
    return this._all.filter((c) => c.alpha_2 === upper);
  }

  /** Alias for active(). Kept for API symmetry. */
  byAlpha2(code) {
    return this.active(code);
  }

  byAlpha3(code) {
    if (typeof code !== "string") return null;
    return this._byAlpha3.get(code.toUpperCase()) ?? null;
  }

  byNumeric(numeric) {
    if (numeric === null || numeric === undefined) return null;
    const padded = String(numeric).padStart(3, "0");
    return this._byNumeric.get(padded) ?? null;
  }

  // ----------------------------------------------------------------
  // Queries
  // ----------------------------------------------------------------

  /** Currencies in circulation in a country. Returns [] if none. */
  currencies(code) {
    const c = this.active(code);
    if (!c || !c.currency_codes) return [];
    return [...c.currency_codes];
  }

  /** Countries where a currency circulates. Returns [] if none. */
  countriesWith(currencyCode) {
    if (typeof currencyCode !== "string") return [];
    const target = currencyCode.toUpperCase();
    return this._active.filter(
      (c) => c.currency_codes && c.currency_codes.includes(target),
    );
  }

  /** Countries in a macro-region. Case-insensitive. */
  region(regionName) {
    if (typeof regionName !== "string") return [];
    const target = regionName.toLowerCase();
    return this._active.filter(
      (c) => (c.region ?? "").toLowerCase() === target,
    );
  }

  /** Countries in a sub-region. Case-insensitive. */
  subregion(subregionName) {
    if (typeof subregionName !== "string") return [];
    const target = subregionName.toLowerCase();
    return this._active.filter(
      (c) => (c.subregion ?? "").toLowerCase() === target,
    );
  }

  /** Substring search on name, official_name, alpha_2, alpha_3. */
  search(query) {
    if (typeof query !== "string") return [];
    const q = query.toLowerCase();
    const out = [];
    for (const c of this._all) {
      const haystack = [c.name, c.official_name, c.alpha_2, c.alpha_3]
        .filter((x) => x !== null && x !== undefined)
        .join(" ")
        .toLowerCase();
      if (haystack.includes(q)) out.push(c);
    }
    return out;
  }

  // ----------------------------------------------------------------
  // Summary
  // ----------------------------------------------------------------

  summary() {
    const byStatus = {};
    for (const c of this._all) {
      byStatus[c.status] = (byStatus[c.status] ?? 0) + 1;
    }
    return {
      version: this.version,
      updated: this.updated,
      total: this._all.length,
      active: this._active.length,
      withdrawn: this._withdrawn.length,
      by_status: byStatus,
    };
  }

  // ----------------------------------------------------------------
  // Iteration
  // ----------------------------------------------------------------

  [Symbol.iterator]() {
    return this._all[Symbol.iterator]();
  }
}

module.exports = {
  CountryRegistry,
  RegistryError,
  ACTIVE_STATUSES,
};
