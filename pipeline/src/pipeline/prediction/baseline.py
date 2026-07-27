import sqlite3
from dataclasses import dataclass
from statistics import mean, stdev
from typing import Optional

from pipeline.db import repository


@dataclass(frozen=True)
class Prediction:
    value: float
    low: Optional[float]
    high: Optional[float]


def previous_season(season: str) -> str:
    return str(int(season) - 1)


def rolling_average_from_history(
    history: list[tuple[str, float]],
    target_season: str,
    n: int = 10,
) -> Optional[Prediction]:
    """Pure rolling-average baseline (v1 model).

    Resets each season: uses the last `n` games of `target_season` once enough
    exist, otherwise falls back to the prior season's full average (cold start),
    then to a partial average of whatever current-season games exist, else None
    if there's no history anywhere.
    """
    current = [value for season, value in history if season == target_season]
    if len(current) >= n:
        return _prediction_from_window(current[-n:])

    prior = [value for season, value in history if season == previous_season(target_season)]
    if prior:
        return _prediction_from_window(prior)

    if current:
        return _prediction_from_window(current)

    return None


def _prediction_from_window(window: list[float]) -> Prediction:
    avg = mean(window)
    if len(window) > 1:
        sd = stdev(window)
        return Prediction(value=avg, low=avg - sd, high=avg + sd)
    return Prediction(value=avg, low=None, high=None)


def predict_for_player(
    conn: sqlite3.Connection,
    player_id: int,
    stat_column: str,
    target_season: str,
    n: int = 10,
) -> Optional[Prediction]:
    history = repository.get_player_history(conn, player_id, stat_column)
    return rolling_average_from_history(history, target_season, n)
