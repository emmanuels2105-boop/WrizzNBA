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

export type RawPrediction = Omit<PointsPrediction, "confidence"> & {
  isLock: boolean;
  scoringCv: number | null;
};

// Buckets predictions into quartiles of scoring_cv (coefficient of variation of
// the player's own recent points -- see scoring_cv() in
// prediction/minutes_based.py) *within this batch*, rather than fixed
// thresholds, so "Confidence" stays meaningful as the underlying data's typical
// spread changes. Lower CV = more consistent = ranked more confident.
//
// A walk-forward backtest across 13,729 historical predictions found this
// correlates with real accuracy (MAPE ~31% in the tightest CV band vs. ~60-70%
// elsewhere). The previously-used range-width signal was found *inversely*
// correlated with accuracy (tightest-range predictions had the worst error) and
// was removed -- see pipeline/README.md "Known risks".
//
// Rows flagged is_lock (isLock) by the pipeline -- a stricter cutoff on the same
// CV signal, see is_lock_eligible() in prediction/minutes_based.py -- skip the
// quartile system entirely and get the rare "lock" tier instead. They're
// excluded from the population used to compute quartile boundaries for everyone
// else, since they're a separate tier.
export function scoreConfidence(predictions: RawPrediction[]): PointsPrediction[] {
  const nonLockedEntries = predictions
    .map((prediction, index) => ({ index, prediction }))
    .filter(({ prediction }) => !prediction.isLock);

  const ranked = nonLockedEntries
    // No reliable current-season CV yet (early-season cold start) -- least confident.
    .map(({ index, prediction }) => ({ index, cv: prediction.scoringCv ?? Infinity }))
    .sort((a, b) => a.cv - b.cv);

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

  return predictions.map(({ isLock, scoringCv: _scoringCv, ...rest }, index) => ({
    ...rest,
    confidence: isLock ? "lock" : (confidenceByIndex.get(index) ?? "low"),
  }));
}
