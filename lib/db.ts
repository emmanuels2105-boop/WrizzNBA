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

export function getUpcomingPredictions(): PointsPrediction[] {
  let db: DatabaseSync;
  try {
    db = new DatabaseSync(DB_PATH, { readOnly: true });
  } catch {
    // Pipeline hasn't been run yet (no data/wnba.db) -- let the page show an empty state.
    return [];
  }

  try {
    return db
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
      .all() as unknown as PointsPrediction[];
  } finally {
    db.close();
  }
}
