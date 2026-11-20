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
