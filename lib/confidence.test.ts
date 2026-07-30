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
    scoringCv: 0.2,
    ...overrides,
  };
}

test("buckets non-lock predictions into quartiles by scoring CV, most consistent first", () => {
  const predictions = [
    prediction({ playerName: "MostConsistent", scoringCv: 0.05 }),
    prediction({ playerName: "Consistent", scoringCv: 0.15 }),
    prediction({ playerName: "Inconsistent", scoringCv: 0.25 }),
    prediction({ playerName: "MostInconsistent", scoringCv: 0.35 }),
  ];

  const scored = scoreConfidence(predictions);

  assert.equal(scored.find((p) => p.playerName === "MostConsistent")?.confidence, "very_high");
  assert.equal(scored.find((p) => p.playerName === "Consistent")?.confidence, "high");
  assert.equal(scored.find((p) => p.playerName === "Inconsistent")?.confidence, "medium");
  assert.equal(scored.find((p) => p.playerName === "MostInconsistent")?.confidence, "low");
});

test("lock-flagged predictions get the lock tier and are excluded from everyone else's quartile boundaries", () => {
  const predictions = [
    // Without exclusion, this ultra-inconsistent locked row would drag the other three's percentiles down.
    prediction({ playerName: "Locked", isLock: true, scoringCv: 0.9 }),
    prediction({ playerName: "A", scoringCv: 0.05 }),
    prediction({ playerName: "B", scoringCv: 0.15 }),
    prediction({ playerName: "C", scoringCv: 0.25 }),
  ];

  const scored = scoreConfidence(predictions);

  assert.equal(scored.find((p) => p.playerName === "Locked")?.confidence, "lock");
  assert.equal(scored.find((p) => p.playerName === "A")?.confidence, "very_high");
  assert.equal(scored.find((p) => p.playerName === "C")?.confidence, "low");
});

test("a missing CV (no reliable current-season estimate yet) is treated as least confident", () => {
  const predictions = [
    prediction({ playerName: "NoCv", scoringCv: null }),
    prediction({ playerName: "HasCv", scoringCv: 0.1 }),
  ];

  const scored = scoreConfidence(predictions);

  assert.equal(scored.find((p) => p.playerName === "NoCv")?.confidence, "low");
  assert.equal(scored.find((p) => p.playerName === "HasCv")?.confidence, "very_high");
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
