export type ConfidenceLevel = "low" | "medium" | "high" | "very_high" | "lock";

export type PointsPrediction = {
  playerName: string;
  team: string;
  teamFullName: string;
  opponent: string;
  opponentFullName: string;
  gameDate: string;
  predictedValue: number;
  predictedLow: number | null;
  predictedHigh: number | null;
  confidence: ConfidenceLevel;
};

export type RawPrediction = Omit<PointsPrediction, "confidence"> & { isLock: boolean };

// Relative half-width of the predicted range -- the basis for confidence
// bucketing below. Smaller = tighter range relative to the prediction = more
// confident. A zero-width range (e.g. a player projected for exactly 0 points
// with no variance) is treated as maximally confident regardless of the
// predicted value, which also sidesteps a divide-by-zero on predictedValue.
function relativeHalfWidth(prediction: RawPrediction): number {
  if (prediction.predictedLow === null || prediction.predictedHigh === null) {
    return Infinity; // no range at all (single-game cold start) -- least confident
  }
  const halfWidth = (prediction.predictedHigh - prediction.predictedLow) / 2;
  if (halfWidth === 0) return 0;
  if (prediction.predictedValue <= 0) return Infinity;
  return halfWidth / prediction.predictedValue;
}

// Buckets predictions into quartiles of relative-range-width *within this
// batch*, rather than fixed thresholds, so "Confidence" stays meaningful (and
// roughly evenly distributed) as the underlying data's typical spread changes,
// instead of drifting toward "everything is Low" or "everything is Very High".
//
// Rows flagged is_lock (isLock) by the pipeline -- based on the player's own
// historical scoring consistency, not range width, see is_lock_eligible() in
// prediction/minutes_based.py -- skip the quartile system entirely and get the
// rare "lock" tier instead. They're excluded from the population used to
// compute quartile boundaries for everyone else, since they're a separate tier.
export function scoreConfidence(predictions: RawPrediction[]): PointsPrediction[] {
  const nonLockedEntries = predictions
    .map((prediction, index) => ({ index, prediction }))
    .filter(({ prediction }) => !prediction.isLock);

  const ranked = nonLockedEntries
    .map(({ index, prediction }) => ({ index, width: relativeHalfWidth(prediction) }))
    .sort((a, b) => a.width - b.width);

  const confidenceByIndex = new Map<number, ConfidenceLevel>();
  ranked.forEach(({ index }, rank) => {
    const percentile = ranked.length > 1 ? rank / (ranked.length - 1) : 0;
    const confidence: ConfidenceLevel =
      percentile < 0.25
        ? "very_high"
        : percentile < 0.5
          ? "high"
          : percentile < 0.75
            ? "medium"
            : "low";
    confidenceByIndex.set(index, confidence);
  });

  return predictions.map(({ isLock, ...rest }, index) => ({
    ...rest,
    confidence: isLock ? "lock" : (confidenceByIndex.get(index) ?? "low"),
  }));
}
