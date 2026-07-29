import assert from "node:assert/strict";
import { test } from "node:test";

import { scoreConfidence, type RawPrediction } from "./confidence.ts";

function prediction(overrides: Partial<RawPrediction>): RawPrediction {
  return {
    playerName: "Player",
    team: "NYL",
    teamFullName: "New York Liberty",
    opponent: "ATL",
    opponentFullName: "Atlanta Dream",
    gameDate: "2026-07-29",
    predictedValue: 10,
    predictedLow: 8,
    predictedHigh: 12,
    isLock: false,
    ...overrides,
  };
}

test("buckets non-lock predictions into quartiles by relative range width, tightest first", () => {
  // relative half-width = (high-low)/2 / value: 0.05, 0.15, 0.25, 0.35 -- evenly spread quartiles.
  const predictions = [
    prediction({ playerName: "Tightest", predictedValue: 10, predictedLow: 9.5, predictedHigh: 10.5 }),
    prediction({ playerName: "Tight", predictedValue: 10, predictedLow: 8.5, predictedHigh: 11.5 }),
    prediction({ playerName: "Wide", predictedValue: 10, predictedLow: 7.5, predictedHigh: 12.5 }),
    prediction({ playerName: "Widest", predictedValue: 10, predictedLow: 6.5, predictedHigh: 13.5 }),
  ];

  const scored = scoreConfidence(predictions);

  assert.equal(scored.find((p) => p.playerName === "Tightest")?.confidence, "very_high");
  assert.equal(scored.find((p) => p.playerName === "Tight")?.confidence, "high");
  assert.equal(scored.find((p) => p.playerName === "Wide")?.confidence, "medium");
  assert.equal(scored.find((p) => p.playerName === "Widest")?.confidence, "low");
});

test("lock-flagged predictions get the lock tier and are excluded from everyone else's quartile boundaries", () => {
  const predictions = [
    // Without exclusion, this ultra-wide locked row would drag the other three's percentiles down.
    prediction({ playerName: "Locked", isLock: true, predictedValue: 10, predictedLow: 0, predictedHigh: 20 }),
    prediction({ playerName: "A", predictedValue: 10, predictedLow: 9.5, predictedHigh: 10.5 }),
    prediction({ playerName: "B", predictedValue: 10, predictedLow: 8.5, predictedHigh: 11.5 }),
    prediction({ playerName: "C", predictedValue: 10, predictedLow: 7.5, predictedHigh: 12.5 }),
  ];

  const scored = scoreConfidence(predictions);

  assert.equal(scored.find((p) => p.playerName === "Locked")?.confidence, "lock");
  assert.equal(scored.find((p) => p.playerName === "A")?.confidence, "very_high");
  assert.equal(scored.find((p) => p.playerName === "C")?.confidence, "low");
});

test("a zero-width range is treated as maximally confident", () => {
  const predictions = [
    prediction({ playerName: "Zero", predictedValue: 10, predictedLow: 10, predictedHigh: 10 }),
    prediction({ playerName: "Wide", predictedValue: 10, predictedLow: 5, predictedHigh: 15 }),
  ];

  const scored = scoreConfidence(predictions);

  assert.equal(scored.find((p) => p.playerName === "Zero")?.confidence, "very_high");
});

test("a missing range (null low/high) is treated as least confident", () => {
  const predictions = [
    prediction({ playerName: "NoRange", predictedValue: 10, predictedLow: null, predictedHigh: null }),
    prediction({ playerName: "HasRange", predictedValue: 10, predictedLow: 9, predictedHigh: 11 }),
  ];

  const scored = scoreConfidence(predictions);

  assert.equal(scored.find((p) => p.playerName === "NoRange")?.confidence, "low");
  assert.equal(scored.find((p) => p.playerName === "HasRange")?.confidence, "very_high");
});

test("a non-positive predicted value with a real range is treated as least confident, not a division error", () => {
  const predictions = [
    prediction({ playerName: "ZeroValue", predictedValue: 0, predictedLow: -1, predictedHigh: 1 }),
    prediction({ playerName: "HasRange", predictedValue: 10, predictedLow: 9, predictedHigh: 11 }),
  ];

  const scored = scoreConfidence(predictions);

  assert.equal(scored.find((p) => p.playerName === "ZeroValue")?.confidence, "low");
});

test("a single non-lock prediction is very_high (percentile-zero edge case)", () => {
  const scored = scoreConfidence([prediction({ playerName: "Only" })]);

  assert.equal(scored[0].confidence, "very_high");
});

test("empty input produces empty output", () => {
  assert.deepEqual(scoreConfidence([]), []);
});

test("when every prediction is locked, all get the lock tier and nothing crashes on an empty ranking population", () => {
  const predictions = [
    prediction({ playerName: "A", isLock: true }),
    prediction({ playerName: "B", isLock: true }),
  ];

  const scored = scoreConfidence(predictions);

  assert.deepEqual(
    scored.map((p) => p.confidence),
    ["lock", "lock"],
  );
});
