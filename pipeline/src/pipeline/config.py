from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PIPELINE_ROOT / "data" / "wnba.db"

WNBA_LEAGUE_ID = "10"
STATS_BASE_URL = "https://stats.wnba.com/stats"
SCHEDULE_URL = "https://cdn.wnba.com/static/json/staticData/scheduleLeagueV2_1.json"

DEFAULT_SEASONS = ["2024", "2025", "2026"]
DEFAULT_ROLLING_WINDOW = 10
