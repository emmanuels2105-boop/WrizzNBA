from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PIPELINE_ROOT / "data" / "wnba.db"

WNBA_LEAGUE_ID = "10"
STATS_BASE_URL = "https://stats.wnba.com/stats"
SCHEDULE_URL = "https://cdn.wnba.com/static/json/staticData/scheduleLeagueV2_1.json"

DEFAULT_SEASONS = ["2024", "2025", "2026"]
DEFAULT_ROLLING_WINDOW = 10
# Shorter window for the minutes-based model's minutes projection -- deliberately
# smaller than DEFAULT_ROLLING_WINDOW so it's responsive to recent role/rotation
# changes, while the points-per-minute rate still uses the full, more stable window.
DEFAULT_MINUTES_WINDOW = 5

# "Lock" tier eligibility -- see is_lock_eligible() in prediction/minutes_based.py
# for the empirical basis. Requires a full window of strictly current-season
# games (LOCK_WINDOW), with points coefficient-of-variation under LOCK_CV_THRESHOLD.
LOCK_WINDOW = 10
LOCK_CV_THRESHOLD = 0.20
