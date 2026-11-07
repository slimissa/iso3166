// The unknown-code contract (README section 4b, v1.12.5), JavaScript column.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { CountryRegistry } = require("..");

const reg = new CountryRegistry();

test("unknown code: null, [], null, false, false", () => {
  assert.equal(reg.active("XX"), null);
  assert.deepEqual(reg.currencies("XX"), []);
  assert.equal(reg.currencyAt("XX", "2000-01-01"), null);
  assert.equal(reg.isActiveOn("XX", "2000-01-01"), false);
  assert.equal(reg.isEuMemberAt("XX", "2010-01-01"), false);
});

test("an unknown code and a country without a currency look the same", () => {
  assert.deepEqual(reg.currencies("XX"), reg.currencies("AQ"));
  assert.equal(reg.active("XX"), null);
  assert.notEqual(reg.active("AQ"), null);
});

test("lookups are case-insensitive and do not strip; derived queries strip", () => {
  assert.equal(reg.active("us"), reg.active("US"));
  assert.notEqual(reg.active("us"), null);
  assert.equal(reg.active(" us "), null);
  assert.equal(reg.isEuMemberAt(" de ", "2010-01-01"), true);
});

test("alpha-3 in an alpha-2 lookup is null", () => {
  assert.equal(reg.active("USA"), null);
});

test("non-string input to a lookup is null, not an error", () => {
  for (const bad of [840, null, undefined, "", {}, []]) assert.equal(reg.active(bad), null);
});
