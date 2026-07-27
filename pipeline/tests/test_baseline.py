from pipeline.prediction.baseline import rolling_average_from_history


def test_uses_last_n_current_season_games_when_enough_exist():
    history = [("2026", float(v)) for v in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 100]]
    # 11 games this season, n=10 -> should drop the oldest (5) and average the rest.
    pred = rolling_average_from_history(history, target_season="2026", n=10)
    expected_window = [10, 15, 20, 25, 30, 35, 40, 45, 50, 100]
    assert pred.value == sum(expected_window) / len(expected_window)


def test_falls_back_to_prior_season_average_when_current_season_below_n():
    history = [("2025", float(v)) for v in [8, 12, 16, 20]] + [("2026", 30.0), ("2026", 40.0)]
    pred = rolling_average_from_history(history, target_season="2026", n=10)
    assert pred.value == (8 + 12 + 16 + 20) / 4


def test_partial_cold_start_when_no_prior_season_exists():
    history = [("2026", 12.0), ("2026", 18.0)]
    pred = rolling_average_from_history(history, target_season="2026", n=10)
    assert pred.value == (12.0 + 18.0) / 2


def test_returns_none_when_no_history_anywhere():
    pred = rolling_average_from_history([], target_season="2026", n=10)
    assert pred is None


def test_prediction_has_no_range_for_single_game_window():
    history = [("2026", 22.0)]
    pred = rolling_average_from_history(history, target_season="2026", n=10)
    assert pred.value == 22.0
    assert pred.low is None
    assert pred.high is None


def test_prediction_range_is_mean_plus_minus_one_stdev():
    history = [("2025", float(v)) for v in [10, 20]]
    pred = rolling_average_from_history(history, target_season="2026", n=10)
    assert pred.low < pred.value < pred.high
