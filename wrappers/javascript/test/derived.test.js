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
  assert.equal(reg.currencyAt("DE", "1970-01-01"), null);
  assert.deepEqual([...reg.currencyAt("DD", "1990-01-01")], ["EUR"]);
  assert.equal(reg.currencyAt("DD", "1990-10-04"), null);
  assert.equal(reg.currencyAt("BJ", "2000-01-01"), null);
  assert.deepEqual(
    [...reg.regionCountries("Europe", "Western Europe")],
    ["AT", "BE", "CH", "DE", "FR", "LI", "LU", "MC", "NL"],
  );
});

test("results are frozen", () => {
  assert.ok(Object.isFrozen(reg.regionTree("FR")));
  assert.throws(() => reg.regionTree("FR").push("X"), TypeError);
});

test("activeOn returns a frozen object", () => {
  const out = reg.activeOn("1990-01-01");
  assert.ok(Object.isFrozen(out));
  assert.throws(() => {
    out.DE = false;
  }, TypeError);
  assert.equal(out.DE, true);
});

test("currencyAt on a malformed date returns null, not an error", () => {
  for (const bad of ["2010-13-45", "2010-02-30", "20100101", "", "2010-01-01\n", null, undefined, 20100101]) {
    assert.equal(reg.currencyAt("DE", bad), null, String(bad));
  }
});

test("bordersTransitively defaults to 2 hops", () => {
  const dflt = [...reg.bordersTransitively("US")];
  assert.deepEqual(dflt, [...reg.bordersTransitively("US", 2)]);
  assert.notDeepEqual(dflt, [...reg.bordersTransitively("US", 1)]);
  assert.ok(dflt.length > reg.bordersTransitively("US", 1).length);
});

// v1.14.0: a withdrawn entry whose ISO page gives no withdrawal date.
test("isActiveOn: a withdrawn entry without withdrawal_date is unknown", () => {
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "iso3166.json"), "utf8"));
  for (const e of data.countries.withdrawn) {
    if (e.alpha_2 === "NT") Object.assign(e, { withdrawal_date: null, alpha_4: "NTHH", introduced: null });
    if (e.alpha_2 === "MI") Object.assign(e, { withdrawal_date: null, alpha_4: "MIUM", introduced: "1975-01-01" });
  }
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "iso3166-"));
  const file = path.join(dir, "iso3166.json");
  fs.writeFileSync(file, JSON.stringify(data));
  const r = new CountryRegistry(file);
  assert.equal(r.isActiveOn("NT", "1980-01-01"), null);
  assert.equal(r.isActiveOn("NT", "2025-01-01"), null);
  assert.equal(r.isActiveOn("MI", "1974-06-01"), false);
  assert.equal(r.isActiveOn("MI", "1980-01-01"), null);
});

test("alpha_4 and reservation are carried by withdrawn entries only", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "iso3166.json"), "utf8"));
  const want = Object.fromEntries(data.countries.withdrawn.map((e) => [e.alpha_2, [e.alpha_4, e.reservation]]));
  const got = Object.fromEntries(reg.allWithdrawn().map((c) => [c.alpha_2, [c.alpha_4, c.reservation]]));
  assert.deepEqual(got, want);
  assert.ok(reg.allActive().every((c) => c.alpha_4 === null && c.reservation === null));
});
