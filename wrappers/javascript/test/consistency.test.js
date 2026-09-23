"use strict";

/**
 * Cross-language consistency tests.
 *
 * Reads tests/cross_language_consistency.json (two levels up from this
 * file) and asserts the JavaScript wrapper satisfies every case. The
 * same fixture is read by the Python, Go, and Rust suites.
 */

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { CountryRegistry } = require("..");

const FIXTURE_PATH = path.join(
  __dirname, "..", "..", "..", "tests", "cross_language_consistency.json",
);
const fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf-8"));

const reg = new CountryRegistry();

test("lookup_alpha2", () => {
  for (const c of fixture.lookup_alpha2) {
    const got = reg.active(c.input);
    assert.ok(got, `active(${JSON.stringify(c.input)}) returned null`);
    for (const key of [
      "alpha_2", "alpha_3", "numeric", "name",
      "status", "independent", "region",
    ]) {
      assert.deepEqual(got[key], c[key],
        `${c.input}: ${key} is ${JSON.stringify(got[key])}, expected ${JSON.stringify(c[key])}`);
    }
  }
});

test("lookup_alpha2_missing", () => {
  for (const code of fixture.lookup_alpha2_missing) {
    assert.equal(reg.active(code), null,
      `active(${JSON.stringify(code)}) should be null`);
  }
});

test("lookup_alpha3", () => {
  for (const c of fixture.lookup_alpha3) {
    const got = reg.byAlpha3(c.input);
    assert.ok(got, `byAlpha3(${JSON.stringify(c.input)}) returned null`);
    assert.equal(got.alpha_2, c.alpha_2);
  }
});

test("lookup_numeric", () => {
  for (const c of fixture.lookup_numeric) {
    const got = reg.byNumeric(c.input);
    assert.ok(got, `byNumeric(${JSON.stringify(c.input)}) returned null`);
    assert.equal(got.alpha_2, c.alpha_2);
  }
});

test("counts", () => {
  const s = reg.summary();
  assert.equal(s.total, fixture.counts.total);
  assert.equal(s.active, fixture.counts.active);
  assert.equal(s.withdrawn, fixture.counts.withdrawn);
  for (const [status, expected] of Object.entries(fixture.counts.by_status)) {
    assert.equal(s.by_status[status] ?? 0, expected,
      `status ${status}: got ${s.by_status[status] ?? 0}, expected ${expected}`);
  }
});

test("overlap_codes", () => {
  for (const [code, expected] of Object.entries(fixture.overlap_codes)) {
    const got = reg.withAlpha2(code).map((m) => m.status).sort();
    assert.deepEqual(got, [...expected].sort(),
      `${code}: got ${JSON.stringify(got)}, expected ${JSON.stringify(expected)}`);
  }
});

test("region_query", () => {
  for (const c of fixture.region_query) {
    const results = reg.region(c.region);
    assert.ok(results.length >= c.min_count,
      `region ${c.region}: got ${results.length}, expected >= ${c.min_count}`);
    const codes = new Set(results.map((r) => r.alpha_2));
    for (const code of c.must_contain) {
      assert.ok(codes.has(code), `region ${c.region} missing ${code}`);
    }
  }
});

test("currencies", () => {
  for (const [code, expected] of Object.entries(fixture.currencies)) {
    assert.deepEqual(reg.currencies(code), expected);
  }
});

test("countries_with", () => {
  for (const [curr, expected] of Object.entries(fixture.countries_with)) {
    const got = reg.countriesWith(curr).map((c) => c.alpha_2);
    assert.deepEqual(got, expected);
  }
});

test("search", () => {
  for (const c of fixture.search) {
    const results = reg.search(c.query);
    assert.ok(results.length >= c.min_count,
      `search ${JSON.stringify(c.query)}: got ${results.length}, expected >= ${c.min_count}`);
    const codes = new Set(results.map((r) => r.alpha_2));
    for (const code of c.must_contain) {
      assert.ok(codes.has(code), `search ${JSON.stringify(c.query)} missing ${code}`);
    }
  }
});


test("lookup_withdrawn", () => {
  for (const c of fixture.lookup_withdrawn || []) {
    const matches = reg.withAlpha2(c.input);
    const found = matches.some(
      (m) => m.status === "withdrawn" && m.name === c.name,
    );
    assert.ok(found, `${c.input}: withdrawn entry not found`);
  }
});
