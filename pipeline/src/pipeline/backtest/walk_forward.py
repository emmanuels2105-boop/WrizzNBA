import sqlite3
from dataclasses import dataclass
from itertools import groupby

from pipeline.backtest.metrics import mae, mape
from pipeline.db import repository
from pipeline.prediction.baseline import rolling_average_from_history
from pipeline.props import PropType


@dataclass
class BacktestReport:
    n_evaluated: int
    n_skipped: int
    mae: float
    mape: float
    mape_excluded_zero_actuals: int


def run_backtest(
    conn: sqlite3.Connection, prop_type: PropType, seasons: list[str], n: int = 10
) -> BacktestReport:
    """Walk-forward backtest: for every historical game, predicts using only
    games strictly before it (same rule as live prediction, via the same pure
    rolling_average_from_history function), then compares to what happened.
    """
    rows = repository.fetch_all_stats_for_backtest(conn, prop_type.stat_column, seasons)

    pairs: list[tuple[float, float]] = []
    skipped = 0

    for _player_id, player_rows in groupby(rows, key=lambda row: row["player_id"]):
        history: list[tuple[str, float]] = []
        for row in player_rows:
            prediction = rolling_average_from_history(history, row["season"], n)
            if prediction is None:
                skipped += 1
            else:
                pairs.append((row["value"], prediction.value))
            history.append((row["season"], row["value"]))

    mape_value, excluded = mape(pairs)
    return BacktestReport(
        n_evaluated=len(pairs),
        n_skipped=skipped,
        mae=mae(pairs) if pairs else float("nan"),
        mape=mape_value,
        mape_excluded_zero_actuals=excluded,
    )
