import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pipeline.config import DEFAULT_MINUTES_WINDOW, LOCK_WINDOW
from pipeline.db import repository
from pipeline.prediction.minutes_based import (
    is_lock_eligible,
    minutes_based_prediction_from_history,
    scoring_cv,
)
from pipeline.props import PropType

# minutes_based beat the plain rolling-average baseline in backtesting (MAE 4.196
# vs 4.221 on 2024-2026 data) -- see pipeline/README.md for the comparison.
MODEL_NAME = "minutes_based"
# v2: confidence ranking switched from range-width (found inversely correlated
# with accuracy) to scoring_cv, and predicted_low/high switched from a
# minutes-variance range to an empirical residual range -- see config.py
# RESIDUAL_STDEV_BY_TERCILE. Versioned rather than overwritten in place so the
# v1 predictions used as backtest evidence for this change stay intact.
MODEL_VERSION = "v2"


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
    conn: sqlite3.Connection,
    prop_type: PropType,
    n: int = 10,
    minutes_n: int = DEFAULT_MINUTES_WINDOW,
) -> GenerateSummary:
    summary = GenerateSummary()
    generated_at = datetime.now(timezone.utc).isoformat()

    for team_id, game in _next_scheduled_game_per_team(conn).items():
        for player in repository.get_players_for_team(conn, team_id):
            history = repository.get_player_minutes_history(
                conn, player["player_id"], prop_type.stat_column
            )
            prediction = minutes_based_prediction_from_history(
                history, game["season"], n, minutes_n
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
                is_lock=is_lock_eligible(history, game["season"]),
                scoring_cv=scoring_cv(history, game["season"], LOCK_WINDOW),
                model_name=MODEL_NAME,
                model_version=MODEL_VERSION,
                generated_at=generated_at,
            )
            summary.predictions_written += 1

    conn.commit()
    return summary
