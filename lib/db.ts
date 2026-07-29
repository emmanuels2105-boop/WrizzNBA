import path from "node:path";
import { DatabaseSync } from "node:sqlite";

export type ConfidenceLevel = "low" | "medium" | "high" | "very_high";

export type PointsPrediction = {
  playerName: string;
  team: string;
  opponent: string;
  gameDate: string;
  predictedValue: number;
  predictedLow: number | null;
  predictedHigh: number | null;
  confidence: ConfidenceLevel;
};

type RawPrediction = Omit<PointsPrediction, "confidence">;

const DB_PATH = path.join(process.cwd(), "pipeline", "data", "wnba.db");
// Must match MODEL_NAME in pipeline/src/pipeline/prediction/generate.py -- the
// predictions table's unique constraint includes model_name, so switching models
// leaves old rows in place rather than overwriting them; filter explicitly to
// avoid showing duplicate rows per player once more than one model has run.
const CURRENT_MODEL_NAME = "minutes_based";

function withDb<T>(fn: (db: DatabaseSync) => T): T | null {
  let db: DatabaseSync;
  try {
    db = new DatabaseSync(DB_PATH, { readOnly: true });
  } catch {
    // Pipeline hasn't been run yet (no data/wnba.db) -- let callers show an empty state.
    return null;
  }

  try {
    return fn(db);
  } finally {
    db.close();
  }
}

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
function withConfidenceLevels(predictions: RawPrediction[]): PointsPrediction[] {
  const ranked = predictions
    .map((prediction, index) => ({ index, width: relativeHalfWidth(prediction) }))
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

  return predictions.map((prediction, index) => ({
    ...prediction,
    confidence: confidenceByIndex.get(index) ?? "low",
  }));
}

export function getUpcomingPredictions(): PointsPrediction[] {
  const rows =
    withDb(
      (db) =>
        db
          .prepare(
            `SELECT p.full_name AS playerName, t.abbreviation AS team,
                    opp.abbreviation AS opponent, g.game_date AS gameDate,
                    pr.predicted_value AS predictedValue,
                    pr.predicted_low AS predictedLow, pr.predicted_high AS predictedHigh
             FROM predictions pr
             JOIN players p ON p.player_id = pr.player_id
             JOIN teams t ON t.team_id = p.team_id
             JOIN games g ON g.game_id = pr.game_id
             JOIN teams opp
               ON opp.team_id = CASE WHEN g.home_team_id = p.team_id THEN g.away_team_id ELSE g.home_team_id END
             WHERE pr.prop_type = 'POINTS' AND pr.model_name = ?
             ORDER BY g.game_date ASC, pr.predicted_value DESC`,
          )
          .all(CURRENT_MODEL_NAME) as unknown as RawPrediction[],
    ) ?? [];

  return withConfidenceLevels(rows);
}

export function getLastRefreshedAt(): string | null {
  return withDb((db) => {
    const row = db
      .prepare("SELECT MAX(generated_at) AS lastRefreshedAt FROM predictions WHERE model_name = ?")
      .get(CURRENT_MODEL_NAME) as { lastRefreshedAt: string | null } | undefined;
    return row?.lastRefreshedAt ?? null;
  });
}
