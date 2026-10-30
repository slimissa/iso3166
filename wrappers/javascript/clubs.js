"use strict";

/**
 * Club membership queries (v1.12.0).
 *
 * Mirrors wrappers/python/iso3166/clubs.py after idiomatic casing. Each
 * of the four clubs is a list of inclusive {from, to} ranges on every
 * active entry of iso3166.json (`to` null = still a member; [] = never).
 *
 * Rules for every *At query (docs/QUERIES.md, "Query 10"):
 *   - malformed date, unknown code, a code in no range -> false
 *   - from <= date <= to for any range (to null = no upper bound) -> true
 *   - before the first range, or after the last `to` -> false
 * The *At queries return a plain boolean, never null: an empty array is a
 * statement, not a silence, so there is no "unknown" state.
 *
 * isEu, isEea and isEurozone remain as current-status aliases: true when
 * the code has a range whose `to` is null.
 */

const CLUB_FIELDS = Object.freeze([
  "eu_membership",
  "eea_membership",
  "eurozone_membership",
  "customs_union",
]);

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const norm = (code) => (typeof code === "string" ? code.trim().toUpperCase() : "");

function validDate(s) {
  if (typeof s !== "string" || !DATE_RE.test(s)) return false;
  const y = Number(s.slice(0, 4));
  const m = Number(s.slice(5, 7));
  const d = Number(s.slice(8, 10));
  if (y < 1 || m < 1 || m > 12 || d < 1) return false;
  const leap = (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
  const dim = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
  return d <= dim;
}

/** Index the four arrays as frozen [from, to] pairs on the registry. */
function initClubs(registry, activeEntries) {
  const clubs = new Map();
  for (const e of activeEntries) {
    const byField = {};
    for (const f of CLUB_FIELDS) {
      byField[f] = Object.freeze(
        (e[f] ?? []).map((r) => Object.freeze([r.from, r.to ?? null])),
      );
    }
    clubs.set(e.alpha_2, Object.freeze(byField));
  }
  Object.defineProperty(registry, "_clubs", {
    value: clubs,
    writable: false,
    enumerable: false,
    configurable: true,
  });
}

const ClubMemberships = {
  _clubAt(field, code, date) {
    if (!validDate(date)) return false;
    const ranges = this._clubs.get(norm(code))?.[field] ?? [];
    return ranges.some(([from, to]) => from <= date && (to === null || date <= to));
  },

  _clubNow(field, code) {
    const ranges = this._clubs.get(norm(code))?.[field] ?? [];
    return ranges.some(([, to]) => to === null);
  },

  /**
   * Was `code` an EU member state on `date`? Founders count from
   * 1958-01-01 (the EEC). Both ends of a range are inclusive.
   *   isEuMemberAt("GB", "2010-01-01") // true
   *   isEuMemberAt("GB", "2023-01-01") // false
   * See docs/QUERIES.md, "Query 10".
   */
  isEuMemberAt(code, date) {
    return this._clubAt("eu_membership", code, date);
  },

  /**
   * Was `code` a party to the EEA Agreement on `date`? Dates are the
   * formal entry into force, so provisionally applying states (BG, RO,
   * the 2004 ten, HR) are false until the formal date. See
   * docs/decisions/club-memberships.md. See docs/QUERIES.md, "Query 10".
   */
  isEeaMemberAt(code, date) {
    return this._clubAt("eea_membership", code, date);
  },

  /**
   * Was `code` in the eurozone on `date`? Members count from 1 January
   * of their adoption year.
   *   isEurozoneMemberAt("GR", "2000-01-01") // false
   *   isEurozoneMemberAt("GR", "2002-01-01") // true
   * See docs/QUERIES.md, "Query 10".
   */
  isEurozoneMemberAt(code, date) {
    return this._clubAt("eurozone_membership", code, date);
  },

  /**
   * Was `code` in the EU customs union on `date`? AD and TR cover
   * industrial goods only (scope is in the snapshot meta).
   *   isInCustomsUnionAt("GB", "2010-01-01") // true
   *   isInCustomsUnionAt("GB", "2023-01-01") // false
   * See docs/QUERIES.md, "Query 10".
   */
  isInCustomsUnionAt(code, date) {
    return this._clubAt("customs_union", code, date);
  },
};

/** Install the club queries on a class's prototype. */
function install(cls) {
  for (const [name, fn] of Object.entries(ClubMemberships)) {
    Object.defineProperty(cls.prototype, name, {
      value: fn,
      writable: true,
      configurable: true,
      enumerable: false,
    });
  }
  return cls;
}

module.exports = { ClubMemberships, CLUB_FIELDS, initClubs, install };
