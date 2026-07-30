import path from "node:path";
import { DatabaseSync } from "node:sqlite";

import { scoreConfidence, type PointsPrediction, type RawPrediction } from "@/lib/confidence";

export type { ConfidenceLevel, PointsPrediction } from "@/lib/confidence";

// Shape returned directly by node:sqlite -- is_lock is a SQLite INTEGER (0/1).
type SqlRow = Omit<RawPrediction, "isLock"> & { isLock: number };

const DB_PATH = path.join(process.cwd(), "pipeline", "data", "wnba.db");
// Must match MODEL_NAME/MODEL_VERSION in pipeline/src/pipeline/prediction/generate.py
// -- the predictions table's unique constraint includes both, so a model *or*
// scoring-logic change (e.g. v1 -> v2's confidence-signal swap) leaves old rows in
// place rather than overwriting them; filter explicitly to avoid showing
// duplicate rows per player once more than one model/version has run.
const CURRENT_MODEL_NAME = "minutes_based";
const CURRENT_MODEL_VERSION = "v2";

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

export function getUpcomingPredictions(): PointsPrediction[] {
  const rows =
    withDb(
      (db) =>
        db
          .prepare(
            `SELECT p.full_name AS playerName, t.abbreviation AS team,
                    TRIM(COALESCE(t.city || ' ', '') || t.name) AS teamFullName,
                    opp.abbreviation AS opponent,
                    TRIM(COALESCE(opp.city || ' ', '') || opp.name) AS opponentFullName,
                    g.game_date AS gameDate,
                    pr.predicted_value AS predictedValue,
                    pr.predicted_low AS predictedLow, pr.predicted_high AS predictedHigh,
                    pr.is_lock AS isLock, pr.scoring_cv AS scoringCv
             FROM predictions pr
             JOIN players p ON p.player_id = pr.player_id
             JOIN teams t ON t.team_id = p.team_id
             JOIN games g ON g.game_id = pr.game_id
             JOIN teams opp
               ON opp.team_id = CASE WHEN g.home_team_id = p.team_id THEN g.away_team_id ELSE g.home_team_id END
             WHERE pr.prop_type = 'POINTS' AND pr.model_name = ? AND pr.model_version = ?
             ORDER BY g.game_date ASC, pr.predicted_value DESC`,
          )
          .all(CURRENT_MODEL_NAME, CURRENT_MODEL_VERSION) as unknown as SqlRow[],
    ) ?? [];

  const rawPredictions: RawPrediction[] = rows.map((row) => ({ ...row, isLock: row.isLock === 1 }));
  return scoreConfidence(rawPredictions);
}

export function getLastRefreshedAt(): string | null {
  return withDb((db) => {
    const row = db
      .prepare(
        "SELECT MAX(generated_at) AS lastRefreshedAt FROM predictions WHERE model_name = ? AND model_version = ?",
      )
      .get(CURRENT_MODEL_NAME, CURRENT_MODEL_VERSION) as { lastRefreshedAt: string | null } | undefined;
    return row?.lastRefreshedAt ?? null;
  });
}
