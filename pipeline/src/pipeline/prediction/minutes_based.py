import sqlite3
from statistics import mean, stdev
from typing import Optional

from pipeline.config import DEFAULT_MINUTES_WINDOW, LOCK_CV_THRESHOLD, LOCK_WINDOW
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


def is_lock_eligible(
    history: list[tuple[str, float, float]],
    target_season: str,
    n: int = LOCK_WINDOW,
    cv_threshold: float = LOCK_CV_THRESHOLD,
) -> bool:
    """Whether a player's own recent scoring consistency earns the rare "It's a
    lock" tier, on top of (not instead of) the normal Low/Medium/High/Very High
    range-based confidence.

    Empirical basis (see the walk-forward calibration run against 2024-2026 data
    before this was added): neither the predicted range's absolute nor relative
    width correlates with actual hit-rate/error the way "confidence" implies --
    counterintuitively, *tighter* ranges had *worse* hit rates, because a narrow
    absolute band around a high-usage star is easier to miss than a wide-looking
    relative band around a bench player who barely deviates from near-zero. The
    one signal that did show a real, monotonic relationship with lower relative
    error was a player's own historical scoring consistency -- the coefficient of
    variation (stdev/mean) of their last `n` games' points. Lower CV genuinely
    predicts better relative accuracy (MAPE ~32% in the tightest historical CV
    band vs. ~144% in the loosest) -- a real but modest edge, not a guarantee,
    which is exactly why this is reserved for a strict cutoff and requires a full
    window of *strictly current-season* games (no cold-start/prior-season
    blending) so the CV estimate itself isn't diluted by stale data.
    """
    current_season_points = [points for season, _minutes, points in history if season == target_season]
    if len(current_season_points) < n:
        return False

    window = current_season_points[-n:]
    mean_points = mean(window)
    if mean_points <= 0:
        return False

    return (stdev(window) / mean_points) < cv_threshold


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
