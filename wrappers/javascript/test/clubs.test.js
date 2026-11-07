"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { CountryRegistry, KNOWN_EU_MEMBERS } = require("..");

const reg = new CountryRegistry();

test("UK leaves the EU between 2010 and 2023; ends are inclusive", () => {
  assert.equal(reg.isEuMemberAt("GB", "2010-01-01"), true);
  assert.equal(reg.isEuMemberAt("GB", "2023-01-01"), false);
  assert.equal(reg.isEuMemberAt("GB", "2020-01-31"), true);
  assert.equal(reg.isEuMemberAt("GB", "2020-02-01"), false);
  assert.equal(reg.isEuMemberAt("GB", "1972-12-31"), false);
});

test("Greece: EU from 1981, eurozone from 2001", () => {
  assert.equal(reg.isEuMemberAt("GR", "1980-01-01"), false);
  assert.equal(reg.isEuMemberAt("GR", "2000-01-01"), true);
  assert.equal(reg.isEurozoneMemberAt("GR", "2000-01-01"), false);
  assert.equal(reg.isEurozoneMemberAt("GR", "2000-12-31"), false);
  assert.equal(reg.isEurozoneMemberAt("GR", "2001-01-01"), true);
  assert.equal(reg.isEurozoneMemberAt("GR", "2002-01-01"), true);
});

test("before the first range, EEA and customs union", () => {
  assert.equal(reg.isEuMemberAt("DE", "1950-01-01"), false);
  assert.equal(reg.isInCustomsUnionAt("GB", "2010-01-01"), true);
  assert.equal(reg.isInCustomsUnionAt("GB", "2023-01-01"), false);
  assert.equal(reg.isEeaMemberAt("GB", "2020-12-31"), true);
  assert.equal(reg.isEeaMemberAt("GB", "2021-01-01"), false);
});

test("malformed dates throw TypeError (v1.12.5), bad codes are false", () => {
  for (const fn of ["isEuMemberAt", "isEeaMemberAt", "isEurozoneMemberAt", "isInCustomsUnionAt"]) {
    for (const bad of ["2000-13-01", "2000-1-1", "", null, undefined, 20000101, new Date(2000, 0, 1)]) {
      assert.throws(() => reg[fn]("DE", bad), TypeError, `${fn}(${String(bad)})`);
    }
    assert.equal(reg[fn]("ZZ", "2000-01-01"), false);
    assert.equal(reg[fn](null, "2000-01-01"), false);
    assert.equal(reg[fn]("CH", "2000-01-01"), false);
  }
  assert.equal(reg.isEuMemberAt(" gb ", "2010-01-01"), true);
});

test("current-status aliases match the v1.11.1 answers for every code", () => {
  const EEA_NON_EU = new Set(["IS", "LI", "NO"]);
  for (const c of [...reg.allActive().map((e) => e.alpha_2), "ZZ", ""]) {
    const e = reg.active(c || "ZZ");
    const eu = KNOWN_EU_MEMBERS.has(c);
    const ea = eu || EEA_NON_EU.has(c);
    const ez = eu && Boolean(e && e.currency_codes && e.currency_codes.length === 1 && e.currency_codes[0] === "EUR");
    assert.deepEqual([reg.isEu(c), reg.isEea(c), reg.isEurozone(c)], [eu, ea, ez], c);
  }
  assert.equal(reg.allActive().filter((e) => reg.isEu(e.alpha_2)).length, 27);
  assert.equal(reg.allActive().filter((e) => reg.isEea(e.alpha_2)).length, 30);
  assert.equal(reg.allActive().filter((e) => reg.isEurozone(e.alpha_2)).length, 21);
});

test("EEA provisional application counts (v1.12.1)", () => {
  assert.equal(reg.isEeaMemberAt("BG", "2010-01-01"), true);
  assert.equal(reg.isEeaMemberAt("BG", "2005-01-01"), false);
  assert.equal(reg.isEeaMemberAt("BG", "2007-07-31"), false);
  assert.equal(reg.isEeaMemberAt("BG", "2007-08-01"), true);
  assert.equal(reg.isEeaMemberAt("CY", "2005-01-01"), true);
  assert.equal(reg.isEeaMemberAt("CY", "2003-01-01"), false);
  assert.equal(reg.isEeaMemberAt("HR", "2020-01-01"), false);
});

// v1.12.5, Query 11: activeOn is isActiveOn for every code.
test("activeOn('1990-01-01'): 275 keys, 170 true, 29 false, 76 null", () => {
  const r = reg.activeOn("1990-01-01");
  const vals = Object.values(r);
  assert.equal(vals.length, 275);
  assert.deepEqual(Object.keys(r), [...Object.keys(r)].sort());
  const n = (v) => vals.filter((x) => x === v).length;
  assert.deepEqual([n(true), n(false), n(null)], [170, 29, 76]);
  for (const [code, v] of Object.entries(r)) {
    assert.equal(v, reg.isActiveOn(code, "1990-01-01"), code);
  }
  assert.equal(r.DE, true);
  assert.equal(r.DD, true);
  assert.equal(r.BU, false);
  assert.equal(r.BJ, null);
  assert.equal(vals.filter(Boolean).length, 170); // truthiness drops the 76
  assert.throws(() => reg.activeOn("1990-13-01"), TypeError);
});
