"use strict";

/**
 * Argument and date contract shared by derived.js and clubs.js.
 *
 * v1.12.8: extracted from the two files, which carried identical copies.
 * Behavior and messages are unchanged and pinned by test/contract.test.js.
 */

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

// v1.12.5: Python and the CLI reject an extra argument; JavaScript used to
// ignore it, so reg.isEuMemberAt("DE", "2010-01-01", "OFAC") returned true.
function checkArgs(got, min, max) {
  if (got < min || got > max) {
    const want = min === max ? String(min) : min + " to " + max;
    throw new TypeError(
      "expected " + want + " argument" + (max === 1 ? "" : "s") + ", got " + got,
    );
  }
}

function assertDate(s) {
  if (!validDate(s)) {
    throw new TypeError("malformed date: " + s + " (want YYYY-MM-DD)");
  }
}

function validDate(s) {
  if (typeof s !== "string" || !DATE_RE.test(s)) return false;
  const y = Number(s.slice(0, 4));
  const m = Number(s.slice(5, 7));
  const d = Number(s.slice(8, 10));
  if (y < 1 || m < 1 || m > 12 || d < 1) return false;
  const leap = (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
  const dim = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
  return d <= dim;
}

module.exports = { checkArgs, assertDate, validDate };
