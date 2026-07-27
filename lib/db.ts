import path from "node:path";
import { DatabaseSync } from "node:sqlite";

export type PointsPrediction = {
  playerName: string;
  team: string;
  opponent: string;
  gameDate: string;
  predictedValue: number;
  predictedLow: number | null;
  predictedHigh: number | null;
};

const DB_PATH = path.join(process.cwd(), "pipeline", "data", "wnba.db");

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
  return (
    withDb((db) =>
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
           WHERE pr.prop_type = 'POINTS'
           ORDER BY g.game_date ASC, pr.predicted_value DESC`,
        )
        .all() as unknown as PointsPrediction[],
    ) ?? []
  );
}

export function getLastRefreshedAt(): string | null {
  return withDb((db) => {
    const row = db.prepare("SELECT MAX(generated_at) AS lastRefreshedAt FROM predictions").get() as
      | { lastRefreshedAt: string | null }
      | undefined;
    return row?.lastRefreshedAt ?? null;
  });
}
