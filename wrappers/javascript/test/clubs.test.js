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

test("bad inputs are false, never null", () => {
  for (const fn of ["isEuMemberAt", "isEeaMemberAt", "isEurozoneMemberAt", "isInCustomsUnionAt"]) {
    assert.equal(reg[fn]("DE", "2000-13-01"), false);
    assert.equal(reg[fn]("DE", "2000-1-1"), false);
    assert.equal(reg[fn]("DE", ""), false);
    assert.equal(reg[fn]("DE", null), false);
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
