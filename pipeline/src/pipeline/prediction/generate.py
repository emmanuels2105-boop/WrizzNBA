import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pipeline.db import repository
from pipeline.prediction.baseline import predict_for_player
from pipeline.props import PropType

MODEL_NAME = "rolling_average"
MODEL_VERSION = "v1"


@dataclass
class GenerateSummary:
    predictions_written: int = 0
    skipped_players: list[tuple[int, str]] = field(default_factory=list)

    def __str__(self) -> str:
        return f"predictions={self.predictions_written} skipped={len(self.skipped_players)}"


def _next_scheduled_game_per_team(conn: sqlite3.Connection) -> dict[int, sqlite3.Row]:
    """Maps team_id -> that team's soonest SCHEDULED game (rows already come
    ordered by game_date ascending from get_scheduled_games)."""
    next_game_for_team: dict[int, sqlite3.Row] = {}
    for game in repository.get_scheduled_games(conn):
        for team_id in (game["home_team_id"], game["away_team_id"]):
            next_game_for_team.setdefault(team_id, game)
    return next_game_for_team


def generate_predictions(
    conn: sqlite3.Connection, prop_type: PropType, n: int = 10
) -> GenerateSummary:
    summary = GenerateSummary()
    generated_at = datetime.now(timezone.utc).isoformat()

    for team_id, game in _next_scheduled_game_per_team(conn).items():
        for player in repository.get_players_for_team(conn, team_id):
            prediction = predict_for_player(
                conn, player["player_id"], prop_type.stat_column, game["season"], n
            )
            if prediction is None:
                summary.skipped_players.append((player["player_id"], player["full_name"]))
                continue

            repository.upsert_prediction(
                conn,
                player_id=player["player_id"],
                game_id=game["game_id"],
                prop_type=prop_type.name,
                predicted_value=prediction.value,
                predicted_low=prediction.low,
                predicted_high=prediction.high,
                model_name=MODEL_NAME,
                model_version=MODEL_VERSION,
                generated_at=generated_at,
            )
            summary.predictions_written += 1

    conn.commit()
    return summary
