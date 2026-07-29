from pipeline.prediction.minutes_based import minutes_based_prediction_from_history


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


def test_single_game_cold_start_has_no_range():
    history = [("2026", 20.0, 10.0)]
    pred = minutes_based_prediction_from_history(history, target_season="2026", n=10, minutes_n=5)
    assert pred.value == 10.0  # 20 minutes * (10/20 rate)
    assert pred.low is None
    assert pred.high is None


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
