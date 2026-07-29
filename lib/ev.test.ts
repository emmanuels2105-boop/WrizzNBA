import assert from "node:assert/strict";
import { test } from "node:test";

import {
  americanOddsToImpliedProbability,
  americanOddsToPayoutMultiplier,
  evaluateLine,
  expectedValue,
  halfKellyFraction,
  standardNormalCdf,
} from "./ev.ts";

test("standard normal CDF matches known reference values", () => {
  assert.ok(Math.abs(standardNormalCdf(0) - 0.5) < 1e-6);
  assert.ok(Math.abs(standardNormalCdf(1) - 0.8413447) < 1e-6);
  assert.ok(Math.abs(standardNormalCdf(-1) - 0.1586553) < 1e-6);
});

test("american odds convert to payout and implied probability correctly", () => {
  assert.ok(Math.abs(americanOddsToPayoutMultiplier(-110) - 100 / 110) < 1e-9);
  assert.ok(Math.abs(americanOddsToPayoutMultiplier(150) - 1.5) < 1e-9);

  assert.ok(Math.abs(americanOddsToImpliedProbability(-110) - 110 / 210) < 1e-9);
  assert.ok(Math.abs(americanOddsToImpliedProbability(150) - 0.4) < 1e-9);
});

test("EV is ~0 at a price's own breakeven probability, positive above it, negative below it", () => {
  const odds = -110;
  const breakeven = americanOddsToImpliedProbability(odds);

  assert.ok(Math.abs(expectedValue(breakeven, odds)) < 1e-9);
  assert.ok(expectedValue(breakeven + 0.05, odds) > 0);
  assert.ok(expectedValue(breakeven - 0.05, odds) < 0);
});

test("half-Kelly is exactly half of full Kelly", () => {
  const probability = 0.6;
  const odds = -110;
  const b = americanOddsToPayoutMultiplier(odds);
  const fullKelly = (probability * b - (1 - probability)) / b;

  assert.ok(Math.abs(halfKellyFraction(probability, odds) - fullKelly / 2) < 1e-9);
});

test("Kelly fraction clamps to 0 when the edge is negative, instead of a negative stake", () => {
  const odds = -110;
  const breakeven = americanOddsToImpliedProbability(odds);

  assert.equal(halfKellyFraction(breakeven - 0.1, odds), 0);
});

test("a line equal to the mean splits ~50/50 regardless of stdev", () => {
  const { over, under } = evaluateLine({ mean: 15, stdev: 4, line: 15, overOdds: -110, underOdds: -110 });

  assert.ok(Math.abs(over.probability - 0.5) < 1e-9);
  assert.ok(Math.abs(under.probability - 0.5) < 1e-9);
});

test("a non-zero mean/line gap with a small stdev pushes the probability toward certainty", () => {
  const { over, under } = evaluateLine({ mean: 20, stdev: 1, line: 15, overOdds: -110, underOdds: -110 });

  assert.ok(over.probability > 0.99);
  assert.ok(under.probability < 0.01);
});

test("a non-positive stdev is treated as a degenerate distribution, not a division error", () => {
  const above = evaluateLine({ mean: 20, stdev: 0, line: 15, overOdds: -110, underOdds: -110 });
  assert.equal(above.over.probability, 1);
  assert.equal(above.under.probability, 0);

  const below = evaluateLine({ mean: 10, stdev: 0, line: 15, overOdds: -110, underOdds: -110 });
  assert.equal(below.over.probability, 0);
  assert.equal(below.under.probability, 1);
});

test("over and under probabilities always sum to 1", () => {
  const { over, under } = evaluateLine({ mean: 12.3, stdev: 3.7, line: 14, overOdds: 120, underOdds: -150 });

  assert.ok(Math.abs(over.probability + under.probability - 1) < 1e-9);
});
