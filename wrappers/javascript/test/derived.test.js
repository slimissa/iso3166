"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { CountryRegistry } = require("..");

const reg = new CountryRegistry();

test("isEu / isEea / isEurozone", () => {
  assert.equal(reg.isEu("DE"), true);
  assert.equal(reg.isEu("GB"), false);
  assert.equal(reg.isEu("CH"), false);
  assert.equal(reg.isEu("XK"), false);
  assert.equal(reg.isEea("NO"), true);
  assert.equal(reg.isEurozone("AD"), false);
  assert.equal(reg.isEurozone("DE"), true);
});

test("regionTree, bordersTransitively", () => {
  assert.deepEqual([...reg.regionTree("FR")], ["Europe", "Western Europe"]);
  assert.deepEqual([...reg.regionTree("TW")], []);
  assert.deepEqual([...reg.bordersTransitively("US", 1)], ["CA", "MX"]);
  assert.deepEqual([...reg.bordersTransitively("AQ", 2)], []);
});

test("succession", () => {
  assert.deepEqual([...reg.successionPath("YU", "RS")], ["YU", "CS", "RS"]);
  assert.equal(reg.successionPath("US", "GB"), null);
  assert.deepEqual([...reg.successors("YU")], ["CS", "ME", "RS"]);
  assert.deepEqual([...reg.predecessors("RS")], ["CS", "YU"]);
});

test("callingCodeFor, currencyAt, regionCountries", () => {
  assert.deepEqual([...reg.callingCodeFor("+44 20 7946 0958")], ["GB", "GG", "IM", "JE"]);
  assert.deepEqual([...reg.callingCodeFor("+999 123")], []);
  assert.deepEqual([...reg.currencyAt("DE", "2000-01-01")], ["EUR"]);
  assert.equal(reg.currencyAt("DD", "1990-01-01"), null);
  assert.deepEqual(
    [...reg.regionCountries("Europe", "Western Europe")],
    ["AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"],
  );
});

test("results are frozen", () => {
  assert.ok(Object.isFrozen(reg.regionTree("FR")));
  assert.throws(() => reg.regionTree("FR").push("X"), TypeError);
});
