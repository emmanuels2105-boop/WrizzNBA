from statistics import mean, stdev

from pipeline.prediction.minutes_based import (
    is_lock_eligible,
    minutes_based_prediction_from_history,
    residual_stdev,
    scoring_cv,
)


def test_decoupled_windows_differ_from_plain_points_average():
    # Role increased partway through the season: first 5 games low minutes/points,
    # last 5 games much higher. A same-window design would collapse to mean(points);
    # this asserts the decoupled-window design actually produces something different.
    minutes = [15, 16, 14, 15, 15, 25, 28, 30, 27, 29]
    points = [6, 7, 6, 6, 7, 12, 14, 16, 13, 15]
    history = [("2026", m, p) for m, p in zip(minutes, points)]

    pred = minutes_based_prediction_from_history(history, target_season="2026", n=10, minutes_n=5)

    plain_average = sum(points) / len(points)
    assert abs(pred.value - plain_average) > 1.0  # meaningfully different, not a no-op
    assert round(pred.value, 2) == 13.25  # (sum(minutes[-5:])/5) * (sum(points)/sum(minutes))


def test_pooled_rate_is_not_skewed_by_a_single_low_minute_outlier():
    # A 1-minute/4-point game is a 4.0 points-per-minute ratio -- a naive mean of
    # per-game ratios would be dominated by it. Pooled (sum/sum), it barely moves.
    history = [("2026", 30.0, 15.0), ("2026", 28.0, 14.0), ("2026", 1.0, 4.0)]
    pred = minutes_based_prediction_from_history(history, target_season="2026", n=3, minutes_n=3)

    naive_mean_of_ratios = (15 / 30 + 14 / 28 + 4 / 1) / 3  # ~1.67
    pooled_rate = (15 + 14 + 4) / (30 + 28 + 1)  # ~0.559
    predicted_minutes = (30 + 28 + 1) / 3
    assert pred.value == predicted_minutes * pooled_rate
    assert pred.value < predicted_minutes * naive_mean_of_ratios / 2  # far more moderate


def test_all_dnp_rate_window_returns_none():
    history = [("2026", 0.0, 0.0), ("2026", 0.0, 0.0)]
    pred = minutes_based_prediction_from_history(history, target_season="2026", n=10, minutes_n=5)
    assert pred is None


def test_single_game_cold_start_still_gets_a_residual_based_range():
    # The range no longer comes from minutes-window stdev (which needs >=2 games),
    # so a single-game cold start still gets a real, calibrated range.
    history = [("2026", 20.0, 10.0)]
    pred = minutes_based_prediction_from_history(history, target_season="2026", n=10, minutes_n=5)
    assert pred.value == 10.0  # 20 minutes * (10/20 rate)
    assert pred.low == 10.0 - residual_stdev(10.0)
    assert pred.high == 10.0 + residual_stdev(10.0)


def test_falls_back_to_prior_season_when_current_below_window():
    # Both the rate window (n=10) and minutes window (minutes_n=5) fall back to
    # the same prior season here, since neither has enough current-season games.
    prior = [("2025", 20.0, 8.0), ("2025", 25.0, 11.0), ("2025", 30.0, 16.0)]
    current = [("2026", 22.0, 9.0)]
    history = prior + current

    pred = minutes_based_prediction_from_history(history, target_season="2026", n=10, minutes_n=5)

    rate = (8 + 11 + 16) / (20 + 25 + 30)
    predicted_minutes = (20 + 25 + 30) / 3
    assert pred.value == predicted_minutes * rate
    assert pred.low is not None and pred.low < pred.value < pred.high


def test_returns_none_with_no_history_anywhere():
    pred = minutes_based_prediction_from_history([], target_season="2026", n=10, minutes_n=5)
    assert pred is None


def test_lock_eligible_with_full_window_and_low_consistency():
    history = [("2026", 30.0, 20.0)] * 10  # dead-consistent: CV = 0
    assert is_lock_eligible(history, target_season="2026", n=10, cv_threshold=0.20) is True


def test_lock_not_eligible_with_fewer_than_n_current_season_games():
    # Only 9 current-season games, however consistent -- no cold-start/fallback allowed for locks.
    history = [("2026", 30.0, 20.0)] * 9
    assert is_lock_eligible(history, target_season="2026", n=10, cv_threshold=0.20) is False


def test_lock_not_eligible_with_high_variance():
    history = [("2026", 30.0, p) for p in [5, 25, 5, 25, 5, 25, 5, 25, 5, 25]]  # CV far above 0.20
    assert is_lock_eligible(history, target_season="2026", n=10, cv_threshold=0.20) is False


def test_lock_ignores_prior_season_games_toward_the_window():
    # 8 current-season + 3 prior-season games -- current-season count (8) is what matters, still < n.
    prior = [("2025", 30.0, 20.0)] * 3
    current = [("2026", 30.0, 20.0)] * 8
    history = prior + current
    assert is_lock_eligible(history, target_season="2026", n=10, cv_threshold=0.20) is False


def test_scoring_cv_returns_none_with_fewer_than_n_current_season_games():
    history = [("2026", 30.0, 20.0)] * 9
    assert scoring_cv(history, target_season="2026", n=10) is None


def test_scoring_cv_returns_none_for_non_positive_mean():
    # Every game scoreless -- CV (stdev/mean) is undefined, not a divide-by-zero.
    history = [("2026", 20.0, 0.0)] * 10
    assert scoring_cv(history, target_season="2026", n=10) is None


def test_scoring_cv_matches_stdev_over_mean_of_the_window():
    points = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
    history = [("2026", 25.0, p) for p in points]
    cv = scoring_cv(history, target_season="2026", n=10)
    assert cv == stdev(points) / mean(points)


def test_residual_stdev_picks_the_correct_tercile_bucket():
    assert residual_stdev(3.0) == 3.939  # low tercile
    assert residual_stdev(7.0) == 5.261  # mid tercile
    assert residual_stdev(15.0) == 6.816  # high tercile
