// v1.12.5: an extra or missing argument throws TypeError, as in Python and
// the CLI. Before, reg.isEuMemberAt("DE", "2010-01-01", "OFAC") returned true.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { CountryRegistry } = require("..");

const reg = new CountryRegistry();

// method -> a valid argument list; optional trailing args are listed in `opt`.
const CALLS = {
  isEu: [["DE"], 1, 1],
  isEea: [["NO"], 1, 1],
  isEurozone: [["DE"], 1, 1],
  regionTree: [["FR"], 1, 1],
  bordersTransitively: [["DE"], 1, 2],
  successionPath: [["YU", "RS"], 2, 2],
  successors: [["YU"], 1, 1],
  predecessors: [["RS"], 1, 1],
  callingCodeFor: [["+49"], 1, 1],
  currencyAt: [["DE", "2000-01-01"], 2, 2],
  isActiveOn: [["DE", "1990-01-01"], 2, 2],
  activeOn: [["1990-01-01"], 1, 1],
  regionCountries: [["Europe"], 1, 2],
  isEuMemberAt: [["DE", "2010-01-01"], 2, 2],
  isEeaMemberAt: [["NO", "2010-01-01"], 2, 2],
  isEurozoneMemberAt: [["DE", "2010-01-01"], 2, 2],
  isInCustomsUnionAt: [["DE", "2010-01-01"], 2, 2],
};

test("every derived method is covered", () => {
  assert.equal(Object.keys(CALLS).length, 17);
});

for (const [name, [args, min, max]] of Object.entries(CALLS)) {
  test(`${name}: valid call works, one extra argument throws`, () => {
    assert.doesNotThrow(() => reg[name](...args), name);
    assert.throws(
      () => reg[name](...args, ...Array(max - args.length + 1).fill("OFAC")),
      (e) => e instanceof TypeError && /^expected .* argument/.test(e.message),
      name,
    );
  });
  test(`${name}: too few arguments throws`, () => {
    if (min > 0) {
      assert.throws(() => reg[name](...args.slice(0, min - 1)), TypeError, name);
    }
  });
}

test("the message says how many were expected and given", () => {
  assert.throws(() => reg.isEuMemberAt("DE", "2010-01-01", "OFAC"),
    { name: "TypeError", message: "expected 2 arguments, got 3" });
  assert.throws(() => reg.isEu("DE", 1),
    { name: "TypeError", message: "expected 1 argument, got 2" });
  assert.throws(() => reg.bordersTransitively("DE", 1, 2),
    { name: "TypeError", message: "expected 1 to 2 arguments, got 3" });
});
