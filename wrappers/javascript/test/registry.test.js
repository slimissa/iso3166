"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");
const os = require("node:os");

const { CountryRegistry, RegistryError } = require("..");

function makeReg() {
  return new CountryRegistry();
}

test("loads", () => {
  const reg = makeReg();
  assert.ok(reg.all().length > 0);
  assert.notStrictEqual(reg.version, "");
});

test("US entry has expected fields", () => {
  const us = makeReg().active("US");
  assert.ok(us, "active('US') returned null");
  assert.equal(us.alpha_2, "US");
  assert.equal(us.alpha_3, "USA");
  assert.equal(us.numeric, "840");
  assert.equal(us.name, "United States of America");
  assert.equal(us.status, "officially-assigned");
  assert.equal(us.independent, true);
  assert.equal(us.region, "Americas");
});

test("lookups are case-insensitive", () => {
  const reg = makeReg();
  assert.deepEqual(reg.active("us"), reg.active("US"));
  assert.deepEqual(reg.byAlpha3("usa"), reg.byAlpha3("USA"));
});

test("missing codes return null", () => {
  const reg = makeReg();
  assert.equal(reg.active("XX"), null);
  assert.equal(reg.byAlpha3("XXX"), null);
  assert.equal(reg.byNumeric("999"), null);
});

test("non-string input returns null", () => {
  const reg = makeReg();
  assert.equal(reg.active(null), null);
  assert.equal(reg.active(123), null);
  assert.equal(reg.byAlpha3(undefined), null);
});

test("byNumeric zero-pads", () => {
  const reg = makeReg();
  assert.deepEqual(reg.byNumeric("20"), reg.byNumeric("020"));
  assert.equal(reg.byNumeric(20).alpha_2, "AD");
});

test("withdrawn codes are not in active()", () => {
  const reg = makeReg();
  assert.equal(reg.active("AN"), null);
  const matches = reg.withAlpha2("AN");
  assert.equal(matches.length, 1);
  assert.equal(matches[0].status, "withdrawn");
});

test("reassigned codes have two entries", () => {
  const reg = makeReg();
  for (const code of ["AI", "SK"]) {
    const matches = reg.withAlpha2(code);
    const statuses = matches.map((m) => m.status).sort();
    assert.deepEqual(statuses, ["officially-assigned", "withdrawn"],
      `${code}: got ${JSON.stringify(statuses)}`);
  }
});

test("allActive is sorted by alpha_2", () => {
  const codes = makeReg().allActive().map((c) => c.alpha_2);
  const sorted = [...codes].sort();
  assert.deepEqual(codes, sorted);
});

test("summary counts are internally consistent", () => {
  const reg = makeReg();
  const s = reg.summary();
  assert.equal(s.total, reg.all().length);
  assert.equal(s.active, reg.allActive().length);
  assert.equal(s.withdrawn, reg.allWithdrawn().length);
});

test("Country objects are frozen", () => {
  const us = makeReg().active("US");
  assert.throws(() => { us.alpha_2 = "XX"; }, TypeError);
});

test("constructor throws on missing file", () => {
  assert.throws(() => new CountryRegistry("/nonexistent.json"), RegistryError);
});

test("constructor throws on malformed JSON", () => {
  const tmp = path.join(os.tmpdir(), `iso3166-test-${process.pid}.json`);
  fs.writeFileSync(tmp, "{not json");
  try {
    assert.throws(() => new CountryRegistry(tmp), RegistryError);
  } finally {
    fs.unlinkSync(tmp);
  }
});

test("registry is iterable", () => {
  const reg = makeReg();
  const viaIterator = [...reg];
  assert.equal(viaIterator.length, reg.all().length);
});
