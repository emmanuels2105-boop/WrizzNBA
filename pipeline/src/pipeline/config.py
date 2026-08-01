from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PIPELINE_ROOT / "data" / "wnba.db"

WNBA_LEAGUE_ID = "10"
STATS_BASE_URL = "https://stats.wnba.com/stats"
SCHEDULE_URL = "https://cdn.wnba.com/static/json/staticData/scheduleLeagueV2_1.json"

DEFAULT_SEASONS = ["2024", "2025", "2026"]
DEFAULT_ROLLING_WINDOW = 10
# A sportsbook only posts points props for a handful of notable players per
# game, not a full 24-player two-roster slate -- predicting everyone else was
# never checkable against a real line anyway.
TOP_PLAYERS_PER_GAME = 10
# Shorter window for the minutes-based model's minutes projection -- deliberately
# smaller than DEFAULT_ROLLING_WINDOW so it's responsive to recent role/rotation
# changes, while the points-per-minute rate still uses the full, more stable window.
DEFAULT_MINUTES_WINDOW = 5

# "Lock" tier eligibility -- see is_lock_eligible() in prediction/minutes_based.py
# for the empirical basis. Requires a full window of strictly current-season
# games (LOCK_WINDOW), with points coefficient-of-variation under LOCK_CV_THRESHOLD.
LOCK_WINDOW = 10
LOCK_CV_THRESHOLD = 0.20

# Empirical residual stdev for predicted_low/predicted_high, derived from a
# walk-forward backtest of minutes_based across 13,729 historical predictions
# (2024-2026 seasons) -- see pipeline/README.md "Known risks" for how this
# replaced the old minutes-variance-based range, which had a 25% hit-rate
# against a target of ~65-70%. Residual stdev (actual - predicted) scales with
# scoring volume, so it's bucketed by tercile of predicted_value rather than a
# single flat number: low tercile 3.939, mid 5.261, high 6.816.
RESIDUAL_TERCILE_BOUNDARIES = (5.14, 10.59)  # (low/mid boundary, mid/high boundary)
RESIDUAL_STDEV_BY_TERCILE = {
    "low": 3.939,
    "mid": 5.261,
    "high": 6.816,
}
