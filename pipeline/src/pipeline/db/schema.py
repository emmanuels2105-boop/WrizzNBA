SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS teams (
        team_id INTEGER PRIMARY KEY,
        abbreviation TEXT NOT NULL,
        name TEXT NOT NULL,
        city TEXT,
        source_last_synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER PRIMARY KEY,
        full_name TEXT NOT NULL,
        team_id INTEGER REFERENCES teams(team_id),
        position TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        source_last_synced_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS games (
        game_id TEXT PRIMARY KEY,
        season TEXT NOT NULL,
        game_date TEXT NOT NULL,
        home_team_id INTEGER NOT NULL REFERENCES teams(team_id),
        away_team_id INTEGER NOT NULL REFERENCES teams(team_id),
        status TEXT NOT NULL CHECK (status IN ('SCHEDULED', 'FINAL')),
        source_last_synced_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date)",
    "CREATE INDEX IF NOT EXISTS idx_games_status_date ON games(status, game_date)",
    """
    CREATE TABLE IF NOT EXISTS player_game_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id TEXT NOT NULL REFERENCES games(game_id),
        player_id INTEGER NOT NULL REFERENCES players(player_id),
        team_id INTEGER NOT NULL REFERENCES teams(team_id),
        minutes REAL,
        points INTEGER NOT NULL,
        rebounds INTEGER,
        assists INTEGER,
        steals INTEGER,
        blocks INTEGER,
        turnovers INTEGER,
        field_goals_made INTEGER,
        field_goals_attempted INTEGER,
        three_pointers_made INTEGER,
        three_pointers_attempted INTEGER,
        free_throws_made INTEGER,
        free_throws_attempted INTEGER,
        plus_minus REAL,
        source_last_synced_at TEXT NOT NULL,
        UNIQUE(game_id, player_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pgs_player ON player_game_stats(player_id)",
    """
    CREATE TABLE IF NOT EXISTS prop_types (
        name TEXT PRIMARY KEY,
        stat_column TEXT NOT NULL,
        description TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL REFERENCES players(player_id),
        game_id TEXT NOT NULL REFERENCES games(game_id),
        prop_type TEXT NOT NULL REFERENCES prop_types(name),
        predicted_value REAL NOT NULL,
        predicted_low REAL,
        predicted_high REAL,
        model_name TEXT NOT NULL,
        model_version TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        UNIQUE(player_id, game_id, prop_type, model_name, model_version)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_predictions_game ON predictions(game_id)",
]

SEED_PROP_TYPES = [
    ("POINTS", "points", "Points scored in a game"),
]
