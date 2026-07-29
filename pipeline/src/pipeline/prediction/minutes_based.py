import sqlite3
from statistics import mean, stdev
from typing import Optional

from pipeline.config import DEFAULT_MINUTES_WINDOW
from pipeline.db import repository
from pipeline.prediction.baseline import Prediction, _select_window


def minutes_based_prediction_from_history(
    history: list[tuple[str, float, float]],
    target_season: str,
    n: int = 10,
    minutes_n: int = DEFAULT_MINUTES_WINDOW,
) -> Optional[Prediction]:
    """Projects points as predicted_minutes * points-per-minute rate, using two
    *different-sized* windows -- this is what makes the model produce a genuinely
    different number from the plain rolling-average baseline.

    If both components used the same window, `mean(minutes) * (sum(points)/sum(minutes))`
    algebraically collapses to exactly `mean(points)` (the sums of minutes cancel out),
    which would make this model a no-op wrapper around the existing one. Instead:

    - `rate` uses the full `n`-game window (season-reset/cold-start, same as the
      baseline): a *pooled* rate -- sum(points)/sum(minutes) over the window, not
      a mean of each game's individual ratio, since a single low-minute game (e.g.
      1 minute/4 points = a 4.0 points-per-minute ratio) would otherwise be a wild
      outlier. Pooled, it barely moves either sum. This is the more data-hungry,
      stable "true scoring efficiency" estimate.
    - `predicted_minutes` uses a shorter `minutes_n`-game window: minutes are far
      more time-varying than scoring efficiency (a role change, injury return, or
      new starter shows up within a few games), so a shorter, more recent window
      is more responsive to exactly the kind of shift a flat rolling average misses.

    Range (low/high) comes from variance in the minutes projection only, since the
    rate is comparatively stable; `None` when the minutes window is a single game
    (no stdev), same convention as the plain rolling-average model.
    """
    paired = [(season, (minutes, value)) for season, minutes, value in history]
    rate_window = _select_window(paired, target_season, n)
    if rate_window is None:
        return None

    total_minutes_for_rate = sum(m for m, _ in rate_window)
    if total_minutes_for_rate == 0:
        # Every game in the rate window was a DNP -- no basis for a scoring rate.
        return None
    rate = sum(v for _, v in rate_window) / total_minutes_for_rate

    minutes_only = [(season, minutes) for season, minutes, _ in history]
    minutes_window = _select_window(minutes_only, target_season, minutes_n)
    if minutes_window is None:
        return None

    predicted_minutes = mean(minutes_window)
    if len(minutes_window) > 1:
        minutes_stdev = stdev(minutes_window)
        low = max(0.0, (predicted_minutes - minutes_stdev) * rate)
        high = (predicted_minutes + minutes_stdev) * rate
        return Prediction(value=predicted_minutes * rate, low=low, high=high)

    return Prediction(value=predicted_minutes * rate, low=None, high=None)


def predict_for_player_minutes_based(
    conn: sqlite3.Connection,
    player_id: int,
    stat_column: str,
    target_season: str,
    n: int = 10,
    minutes_n: int = DEFAULT_MINUTES_WINDOW,
) -> Optional[Prediction]:
    history = repository.get_player_minutes_history(conn, player_id, stat_column)
    return minutes_based_prediction_from_history(history, target_season, n, minutes_n)
