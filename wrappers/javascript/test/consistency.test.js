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

test("lookup_fields", () => {
  for (const c of fixture.lookup_fields || []) {
    const got = reg.active(c.input);
    assert.ok(got, `${c.input} missing`);
    assert.deepEqual(got.official_name, c.official_name);
    assert.deepEqual(got.currency_codes || [], c.currency_codes);
    assert.deepEqual(got.calling_codes || [], c.calling_codes);
    assert.deepEqual(got.tlds || [], c.tlds);
    assert.deepEqual(got.languages || [], c.languages || []);
    assert.deepEqual(got.borders || [], c.borders || []);
  }
});

test("lookup_withdrawn_fields", () => {
  for (const c of fixture.lookup_withdrawn_fields || []) {
    const matches = reg.withAlpha2(c.input);
    assert.ok(matches.length > 0, `${c.input} not found`);
    assert.equal(matches[0].subregion, c.subregion,
      `${c.input}: subregion mismatch`);
  }
});

test("optional_absent", () => {
  for (const cs of fixture.optional_absent || []) {
    const c = reg.active(cs.input);
    assert.ok(c, `${cs.input} missing`);

    if (cs.field === "official_name") {
      const actual = c.official_name ?? null;
      assert.equal(
        actual,
        null,
        `${cs.input}.official_name: expected null, got ${JSON.stringify(actual)}`,
      );
    } else if (cs.field === "borders") {
      const actual = c.borders ?? [];
      assert.deepEqual(
        actual,
        [],
        `${cs.input}.borders: expected [], got ${JSON.stringify(actual)}`,
      );
    } else {
      throw new Error(`unknown field: ${cs.field}`);
    }
  }
});

test(
  "independent",
  {
    skip: !fixture.independent.enforced &&
      "independent snapshot not populated yet (run tools/enrich_independent.py --write)",
  },
  () => {
    const c = fixture.independent;
    for (const code of c.true) {
      const got = reg.active(code);
      assert.ok(got, `${code} missing`);
      assert.equal(got.independent, true, `${code}.independent: expected true`);
    }
    for (const code of c.false) {
      const got = reg.active(code);
      assert.ok(got, `${code} missing`);
      assert.equal(got.independent, false, `${code}.independent: expected false`);
    }
    const n = reg.allActive().filter((x) => x.independent === true).length;
    assert.ok(
      n >= c.count_true_min && n <= c.count_true_max,
      `independent=true count ${n} outside [${c.count_true_min}, ${c.count_true_max}]`,
    );
  },
);

// ---------------------------------------------------------------------
// Input contract (v1.8.0). Each test is skipped while its fixture
// section has enforced=false, so a wrapper can land before the others.
// ---------------------------------------------------------------------

function skipUnless(key) {
  return {
    skip: !fixture[key].enforced && `${key} enforced=false until all wrappers updated`,
  };
}

function terminals(code, seen = new Set()) {
  if (seen.has(code)) return new Set();
  seen.add(code);
  if (reg.active(code)) return new Set([code]);
  const out = new Set();
  for (const entry of reg.withAlpha2(code)) {
    for (const next of entry.replaced_by ?? []) {
      for (const t of terminals(next, seen)) out.add(t);
    }
  }
  return out;
}

const METHODS = {
  active: (x) => reg.active(x),
  by_alpha3: (x) => reg.byAlpha3(x),
  by_numeric: (x) => reg.byNumeric(x),
  region: (x) => reg.region(x),
  subregion: (x) => reg.subregion(x),
  search: (x) => reg.search(x),
  countries_with: (x) => reg.countriesWith(x),
};

test("empty_inputs", skipUnless("empty_inputs"), () => {
  for (const c of fixture.empty_inputs.cases) {
    const got = METHODS[c.method](c.input);
    assert.deepEqual(got, c.expected,
      `${c.method}(${JSON.stringify(c.input)}) should be ${JSON.stringify(c.expected)}`);
  }
});

test("numeric_sentinel", skipUnless("lookup_numeric_absent"), () => {
  for (const v of fixture.lookup_numeric_absent.cases) {
    assert.equal(reg.byNumeric(v), null, `byNumeric(${JSON.stringify(v)}) should be null`);
  }
});

test("alpha2_ambiguous", skipUnless("lookup_alpha2_ambiguous"), () => {
  for (const [code, c] of Object.entries(fixture.lookup_alpha2_ambiguous.cases)) {
    const matches = reg.withAlpha2(code);
    assert.equal(matches.length, c.count, `${code}: entry count`);
    const first = matches[0].status === "withdrawn" ? "withdrawn" : "active";
    assert.equal(first, c.first, `${code}: first entry`);
  }
});

test("successors", skipUnless("successors"), () => {
  for (const c of fixture.successors.cases) {
    assert.deepEqual([...terminals(c.input)].sort(), c.terminal, c.input);
  }
});

test("predecessors", skipUnless("predecessors"), () => {
  for (const c of fixture.predecessors.cases) {
    const got = reg.allWithdrawn()
      .filter((e) => e.alpha_2 !== c.input &&
        (e.replaced_by ?? []).some((n) => terminals(n).has(c.input)))
      .map((e) => e.alpha_2)
      .sort();
    assert.deepEqual(got, c.predecessors, c.input);
  }
});
