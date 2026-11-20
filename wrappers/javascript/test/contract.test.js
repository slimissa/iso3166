"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { KNOWN_EU_MEMBERS } = require("..");
const { EEA_NON_EU } = require("../derived");

test("KNOWN_EU_MEMBERS.add() throws and the snapshot is unchanged", () => {
  assert.equal(KNOWN_EU_MEMBERS.size, 27);
  assert.throws(() => KNOWN_EU_MEMBERS.add("XX"), TypeError);
  assert.equal(KNOWN_EU_MEMBERS.has("XX"), false);
  assert.equal(KNOWN_EU_MEMBERS.size, 27);
});

test("KNOWN_EU_MEMBERS.delete() and clear() throw", () => {
  assert.throws(() => KNOWN_EU_MEMBERS.delete("DE"), TypeError);
  assert.throws(() => KNOWN_EU_MEMBERS.clear(), TypeError);
  assert.equal(KNOWN_EU_MEMBERS.has("DE"), true);
  assert.equal(KNOWN_EU_MEMBERS.size, 27);
});

test("the frozen sets still read like Sets", () => {
  assert.ok(KNOWN_EU_MEMBERS instanceof Set);
  assert.ok(Object.isFrozen(KNOWN_EU_MEMBERS));
  assert.equal([...KNOWN_EU_MEMBERS].length, 27);
  assert.deepEqual([...EEA_NON_EU], ["IS", "LI", "NO"]);
  assert.throws(() => EEA_NON_EU.add("CH"), TypeError);
  assert.equal(EEA_NON_EU.has("CH"), false);
});

// ---- contract.js: the argument and date contract ---------------------------

const { checkArgs, assertDate, validDate } = require("../contract");

test("checkArgs: exact messages", () => {
  assert.throws(() => checkArgs(1, 2, 2), { name: "TypeError", message: "expected 2 arguments, got 1" });
  assert.throws(() => checkArgs(2, 1, 1), { name: "TypeError", message: "expected 1 argument, got 2" });
  assert.throws(() => checkArgs(3, 1, 2), { name: "TypeError", message: "expected 1 to 2 arguments, got 3" });
  assert.throws(() => checkArgs(0, 1, 2), { name: "TypeError", message: "expected 1 to 2 arguments, got 0" });
});

test("checkArgs: the bounds are inclusive", () => {
  for (const [got, min, max] of [[1, 1, 1], [2, 2, 2], [1, 1, 2], [2, 1, 2]]) {
    assert.doesNotThrow(() => checkArgs(got, min, max));
  }
});

test("assertDate: exact message, named by the offending value", () => {
  assert.throws(() => assertDate("2010-13-45"), { name: "TypeError", message: "malformed date: 2010-13-45 (want YYYY-MM-DD)" });
  assert.throws(() => assertDate(20100101), { name: "TypeError", message: "malformed date: 20100101 (want YYYY-MM-DD)" });
  assert.doesNotThrow(() => assertDate("2010-01-01"));
});

test("validDate: leap years", () => {
  assert.equal(validDate("2024-02-29"), true);
  assert.equal(validDate("2000-02-29"), true); // divisible by 400
  assert.equal(validDate("1900-02-29"), false); // divisible by 100, not by 400
  assert.equal(validDate("2023-02-29"), false);
  assert.equal(validDate("2023-02-28"), true);
});

test("validDate: month lengths, zero parts and year 1", () => {
  assert.equal(validDate("2023-04-30"), true);
  assert.equal(validDate("2023-04-31"), false);
  assert.equal(validDate("2023-00-10"), false);
  assert.equal(validDate("2023-01-00"), false);
  assert.equal(validDate("0000-01-01"), false);
  assert.equal(validDate("0001-01-01"), true);
});

test("validDate: a trailing newline, whitespace and non-strings are not dates", () => {
  assert.equal(validDate("2020-01-01\n"), false);
  assert.equal(validDate(" 2020-01-01"), false);
  assert.equal(validDate("2020-1-1"), false);
  assert.equal(validDate(null), false);
  assert.equal(validDate(undefined), false);
  assert.equal(validDate(20200101), false);
});

test("contract.js is published with the package", () => {
  const pkg = require("../package.json");
  assert.ok(pkg.files.includes("contract.js"));
});
