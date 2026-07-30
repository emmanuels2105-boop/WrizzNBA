import sqlite3
from statistics import mean, stdev
from typing import Optional

from pipeline.config import (
    DEFAULT_MINUTES_WINDOW,
    LOCK_CV_THRESHOLD,
    LOCK_WINDOW,
    RESIDUAL_STDEV_BY_TERCILE,
    RESIDUAL_TERCILE_BOUNDARIES,
)
from pipeline.db import repository
from pipeline.prediction.baseline import Prediction, _select_window


def residual_stdev(predicted_value: float) -> float:
    """Empirical historical-error stdev for a prediction of this size (see
    RESIDUAL_STDEV_BY_TERCILE in config.py for how these were derived)."""
    low_bound, mid_bound = RESIDUAL_TERCILE_BOUNDARIES
    if predicted_value < low_bound:
        return RESIDUAL_STDEV_BY_TERCILE["low"]
    if predicted_value < mid_bound:
        return RESIDUAL_STDEV_BY_TERCILE["mid"]
    return RESIDUAL_STDEV_BY_TERCILE["high"]


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

    Range (low/high) comes from `residual_stdev()` -- the empirical historical
    error for a prediction of this size, from a walk-forward backtest -- rather
    than variance in the minutes projection. A backtest of the old
    minutes-variance range found it was actually *inversely* correlated with
    real accuracy (tightest-range predictions had the worst error) and only a
    25% hit-rate against a ~65-70% target; this range is calibrated directly off
    historical error instead, and applies uniformly including single-game
    cold starts (which the old range couldn't cover, having no stdev to draw on).
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

    predicted_value = mean(minutes_window) * rate
    stdev_r = residual_stdev(predicted_value)
    return Prediction(value=predicted_value, low=max(0.0, predicted_value - stdev_r), high=predicted_value + stdev_r)


def scoring_cv(
    history: list[tuple[str, float, float]],
    target_season: str,
    n: int = LOCK_WINDOW,
) -> Optional[float]:
    """Coefficient of variation (stdev/mean) of a player's last `n` games'
    points, or None if there's no reliable current-season estimate yet.

    Empirical basis (see the walk-forward calibration run against 2024-2026
    data): neither the predicted range's absolute nor relative width
    correlates with actual accuracy the way "confidence" implies --
    counterintuitively, *tighter* ranges had *worse* accuracy, because a narrow
    absolute band around a high-usage star is easier to miss than a wide-looking
    relative band around a bench player who barely deviates from near-zero. The
    one signal that did show a real, monotonic relationship with lower relative
    error was a player's own historical scoring consistency -- this CV. Requires
    a full window of *strictly current-season* games (no cold-start/prior-season
    blending) so the estimate itself isn't diluted by stale data; returns None
    rather than a blended/partial estimate when that's not available yet.

    Used two ways: thresholded (see is_lock_eligible) for the rare "It's a Lock"
    tier, and as the ranking signal for the ordinary Low/Medium/High/Very High
    tiers (see lib/confidence.ts) -- lower CV ranks as more confident.
    """
    current_season_points = [points for season, _minutes, points in history if season == target_season]
    if len(current_season_points) < n:
        return None

    window = current_season_points[-n:]
    mean_points = mean(window)
    if mean_points <= 0:
        return None

    return stdev(window) / mean_points


def is_lock_eligible(
    history: list[tuple[str, float, float]],
    target_season: str,
    n: int = LOCK_WINDOW,
    cv_threshold: float = LOCK_CV_THRESHOLD,
) -> bool:
    """Whether a player's own recent scoring consistency earns the rare "It's a
    lock" tier, on top of (not instead of) the normal Low/Medium/High/Very High
    tiers. A real but modest edge (MAPE ~32% in the tightest historical CV band
    vs. ~144% in the loosest), not a guarantee -- see scoring_cv() for the basis.
    """
    cv = scoring_cv(history, target_season, n)
    return cv is not None and cv < cv_threshold


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
