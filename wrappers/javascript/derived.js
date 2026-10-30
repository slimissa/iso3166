"use strict";

/**
 * Derived queries for CountryRegistry.
 *
 * v1.10.0 — design in docs/QUERIES.md (rationale in
 * docs/QUERIES-DECISIONS.md). That document is the contract: each
 * method below names its section.
 *
 * Mirrors wrappers/python/iso3166/derived.py after idiomatic casing.
 * Every list result is a frozen array, so a caller cannot mutate the
 * registry's internal state through it. An unknown code is not an
 * error: bool queries return false, list queries return [], optional
 * queries return null.
 *
 * isActiveOn (v1.11.0) is tri-state: true, false or null (unknown).
 *
 * isEu, isEea and isEurozone are current-status aliases since v1.12.0:
 * they read the membership arrays (see clubs.js and isEuMemberAt for the
 * date-scoped queries). currencyAt (v1.11.1) is
 * bounded by the entry's lifetime (`introduced`, `withdrawal_date`) but
 * returns current currencies: the tree stores no currency history.
 *
 * AI and SK exist twice (active and withdrawn). Field lookups use the
 * active entry; the succession graph is built from withdrawn entries
 * only, so successors("SK") follows Sikkim's replaced_by (IN).
 */

// Deprecated since v1.12.0 and no longer consulted: isEu, isEea and
// isEurozone read the date-scoped membership arrays. KNOWN_EU_MEMBERS is
// the 27 EU member states at v1.9.3. Both are kept only so existing
// imports keep working; they are a frozen snapshot and are not updated.
const KNOWN_EU_MEMBERS = Object.freeze(new Set([
  "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
  "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
  "SI", "ES", "SE",
]));
const EEA_NON_EU = Object.freeze(new Set(["IS", "LI", "NO"]));

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const PHONE_JUNK = new Set([" ", "-", "(", ")", ".", "+"]);

const norm = (code) => (typeof code === "string" ? code.trim().toUpperCase() : "");
const frozen = (arr) => Object.freeze([...arr]);

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

const DerivedQueries = {
  // -- internal ---------------------------------------------------

  _entry(code) {
    const c = norm(code);
    if (!c) return null;
    return (
      this._byAlpha2.get(c) ??
      this._withdrawn.find((w) => w.alpha_2 === c) ??
      null
    );
  },

  _edges() {
    if (!this._dqEdges) {
      const edges = new Map();
      for (const w of this._withdrawn) {
        if (w.replaced_by && w.replaced_by.length) {
          edges.set(w.alpha_2, [...w.replaced_by]);
        }
      }
      this._dqEdges = edges;
    }
    return this._dqEdges;
  },

  _reverseEdges() {
    if (!this._dqRev) {
      const rev = new Map();
      for (const [src, dsts] of this._edges()) {
        for (const d of dsts) {
          if (!rev.has(d)) rev.set(d, []);
          rev.get(d).push(src);
        }
      }
      this._dqRev = rev;
    }
    return this._dqRev;
  },

  _closure(start, edges) {
    const seen = new Set();
    const stack = [start];
    while (stack.length) {
      const cur = stack.pop();
      for (const nxt of edges.get(cur) ?? []) {
        if (!seen.has(nxt) && nxt !== start) {
          seen.add(nxt);
          stack.push(nxt);
        }
      }
    }
    return frozen([...seen].sort());
  },

  // -- Query 1: current status ------------------------------------

  /**
   * True if `code` is an EU member state today (its eu_membership array
   * has an open-ended range). See isEuMemberAt for date-scoped
   * membership. See docs/QUERIES.md, "Query 1".
   */
  isEu(code) {
    return this._clubNow("eu_membership", code);
  },

  /** True if `code` is in the EEA today. See isEeaMemberAt. See docs/QUERIES.md, "Query 1". */
  isEea(code) {
    return this._clubNow("eea_membership", code);
  },

  /**
   * True if `code` is in the eurozone today. Euro users that are not
   * members (AD, MC, SM, VA, ME, XK) and overseas codes (GF, GP, MQ, RE,
   * YT, AX, ...) are false. See isEurozoneMemberAt.
   * See docs/QUERIES.md, "Query 1".
   */
  isEurozone(code) {
    return this._clubNow("eurozone_membership", code);
  },

  // -- Query 2 ----------------------------------------------------

  /** [region, subregion, intermediate_region] with nulls dropped. See docs/QUERIES.md, "Query 2". */
  regionTree(code) {
    const e = this._entry(code);
    if (!e) return frozen([]);
    return frozen(
      [e.region, e.subregion, e.intermediate_region].filter((v) => v),
    );
  },

  // -- Query 3 ----------------------------------------------------

  /** Sorted codes within maxHops of `code` through borders, excluding it. See docs/QUERIES.md, "Query 3". */
  bordersTransitively(code, maxHops = 2) {
    const start = norm(code);
    if (!start || !(maxHops >= 1) || !this._entry(start)) return frozen([]);
    const seen = new Set([start]);
    let frontier = [start];
    for (let i = 0; i < maxHops; i++) {
      const next = [];
      for (const cur of frontier) {
        const e = this._byAlpha2.get(cur);
        for (const b of (e && e.borders) || []) {
          if (!seen.has(b)) {
            seen.add(b);
            next.push(b);
          }
        }
      }
      if (!next.length) break;
      frontier = next;
    }
    seen.delete(start);
    return frozen([...seen].sort());
  },

  // -- Queries 4 and 5 -------------------------------------------

  /** Shortest replaced_by path, endpoints included, or null. See docs/QUERIES.md, "Query 4". */
  successionPath(fromCode, toCode) {
    const a = norm(fromCode);
    const b = norm(toCode);
    if (!this._entry(a) || !this._entry(b)) return null;
    if (a === b) return frozen([a]);
    const edges = this._edges();
    const prev = new Map([[a, null]]);
    const q = [a];
    for (let i = 0; i < q.length; i++) {
      const cur = q[i];
      for (const nxt of edges.get(cur) ?? []) {
        if (prev.has(nxt)) continue;
        prev.set(nxt, cur);
        if (nxt === b) {
          const path = [b];
          while (prev.get(path[path.length - 1]) !== null) {
            path.push(prev.get(path[path.length - 1]));
          }
          return frozen(path.reverse());
        }
        q.push(nxt);
      }
    }
    return null;
  },

  /**
   * Returns all descendants: the transitive closure of replaced_by,
   * intermediate codes included, excluding `code`, sorted. The CLI
   * returns the same set. See docs/QUERIES.md, "Query 5".
   */
  successors(code) {
    const c = norm(code);
    return c ? this._closure(c, this._edges()) : frozen([]);
  },

  /**
   * Returns all ancestors: every withdrawn code from which `code` is
   * reachable through replaced_by, sorted. See docs/QUERIES.md,
   * "Query 5".
   */
  predecessors(code) {
    const c = norm(code);
    return c ? this._closure(c, this._reverseEdges()) : frozen([]);
  },

  // -- Query 6 ----------------------------------------------------

  /**
   * Sorted codes whose calling_codes is a prefix of the number's
   * digits. Country level only: "+44" returns GB, GG, IM and JE, and
   * "+1" returns all NANP entries. See docs/QUERIES.md, "Query 6".
   */
  callingCodeFor(number) {
    if (typeof number !== "string") return frozen([]);
    const digits = [...number].filter((ch) => !PHONE_JUNK.has(ch)).join("");
    if (!/^[0-9]+$/.test(digits)) return frozen([]);
    const out = new Set();
    for (const e of this._active) {
      for (const cc of e.calling_codes ?? []) {
        if (digits.startsWith(cc)) out.add(e.alpha_2);
      }
    }
    return frozen([...out].sort());
  },

  // -- Query 7: lifetime-bounded ----------------------------------

  /**
   * Currency in force on `date` (YYYY-MM-DD), bounded by the entry's
   * lifetime. The tree stores no currency history, so the list is the
   * entry's current currency_codes.
   *
   * Active with `introduced`: null before it, else currency_codes (DE in
   * 1990 returns ["EUR"], not DEM). Active without `introduced` (source
   * silent): null. Withdrawn: null after `withdrawal_date` (or before a
   * known `introduced`), else the union of the terminal successors'
   * current currencies. For withdrawn entries, returns the successor's
   * current currency; the withdrawn entry's historical currency is not
   * in the tree. For null `introduced` (all 25) it may differ from the
   * withdrawn entry's historical currency. null means "cannot answer".
   *
   *   currencyAt("DE", "2000-01-01") // ["EUR"]
   *   currencyAt("DE", "1970-01-01") // null (before introduced)
   *   currencyAt("DD", "1990-01-01") // ["EUR"] (successor's currency)
   *   currencyAt("DD", "1990-10-04") // null (after withdrawal)
   *   currencyAt("BJ", "2000-01-01") // null (introduced is null)
   *
   * See docs/QUERIES.md, "Query 7".
   */
  currencyAt(code, date) {
    if (!validDate(date)) return null;
    const c = norm(code);
    const act = this._byAlpha2.get(c);
    if (act) {
      if (act.introduced == null || date < act.introduced) return null;
      return act.currency_codes == null ? null : frozen(act.currency_codes);
    }
    const wd = this._withdrawn.find((w) => w.alpha_2 === c);
    if (!wd || !wd.withdrawal_date || date > wd.withdrawal_date) return null;
    if (wd.introduced != null && date < wd.introduced) return null;
    const edges = this._edges();
    const out = new Set();
    const seen = new Set();
    const stack = [c];
    while (stack.length) {
      const cur = stack.pop();
      if (seen.has(cur)) continue;
      seen.add(cur);
      const e = this._byAlpha2.get(cur);
      if (e) {
        for (const cc of e.currency_codes ?? []) out.add(cc);
      } else if (edges.has(cur)) {
        stack.push(...edges.get(cur));
      }
    }
    return out.size ? frozen([...out].sort()) : null;
  },

  /**
   * isActiveOn(code, date) -> boolean | null   [tri-state]
   *
   * false: malformed date, unknown code, a date before `introduced`, or
   * after a withdrawn entry's `withdrawal_date`. true: in force on that
   * date. null: unknown (an active entry whose `introduced` is null).
   * Active entries are resolved first (AI and SK exist twice). A
   * withdrawn entry has no sourced start date: false after
   * `withdrawal_date`, null before 1974-01-01 (ISO 3166 did not exist),
   * and true from 1974-01-01 up to and including `withdrawal_date`.
   *
   *   isActiveOn("DE", "1990-01-01") // true
   *   isActiveOn("DE", "1970-01-01") // false
   *   isActiveOn("BJ", "2000-01-01") // null
   *   isActiveOn("DD", "1800-01-01") // null (before 1974)
   *
   * See docs/QUERIES.md, "Query 9".
   */
  isActiveOn(code, date) {
    if (!validDate(date)) return false;
    const c = norm(code);
    const act = this._byAlpha2.get(c);
    if (act) {
      if (act.introduced == null) return null;
      return date >= act.introduced;
    }
    const wd = this._withdrawn.find((w) => w.alpha_2 === c);
    if (!wd || !wd.withdrawal_date) return false;
    if (date > wd.withdrawal_date) return false;
    if (wd.introduced == null) {
      // Start unknown: ISO 3166 began in 1974, so nothing earlier is known.
      return date < "1974-01-01" ? null : true;
    }
    return wd.introduced <= date;
  },

  // -- Query 8 ----------------------------------------------------

  /** Sorted active codes in region (and subregion). Case-insensitive. See docs/QUERIES.md, "Query 8". */
  regionCountries(region, subregion = null) {
    if (!region) return frozen([]);
    const r = region.toLowerCase();
    const s = subregion ? subregion.toLowerCase() : null;
    return frozen(
      this._active
        .filter(
          (e) =>
            (e.region ?? "").toLowerCase() === r &&
            (s === null || (e.subregion ?? "").toLowerCase() === s),
        )
        .map((e) => e.alpha_2)
        .sort(),
    );
  },
};

/** Install the derived queries on a class's prototype. */
function install(cls) {
  for (const [name, fn] of Object.entries(DerivedQueries)) {
    Object.defineProperty(cls.prototype, name, {
      value: fn,
      writable: true,
      configurable: true,
      enumerable: false,
    });
  }
  return cls;
}

module.exports = { DerivedQueries, KNOWN_EU_MEMBERS, EEA_NON_EU, install };
