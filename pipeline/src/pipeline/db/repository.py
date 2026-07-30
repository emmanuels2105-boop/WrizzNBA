import sqlite3
from typing import Optional

from pipeline.client.dto import RawGameLogRow, RawTeam

# player_game_stats columns a prop type's stat_column is allowed to reference.
# stat_column always originates from our own seeded prop_types rows, but this
# whitelist keeps it that way even if that ever changes.
ALLOWED_STAT_COLUMNS = {
    "points",
    "rebounds",
    "assists",
    "steals",
    "blocks",
    "turnovers",
}


def upsert_team(conn: sqlite3.Connection, team: RawTeam, synced_at: str) -> None:
    conn.execute(
        """
        INSERT INTO teams (team_id, abbreviation, name, city, source_last_synced_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(team_id) DO UPDATE SET
            abbreviation = excluded.abbreviation,
            name = excluded.name,
            city = COALESCE(excluded.city, teams.city),
            source_last_synced_at = excluded.source_last_synced_at
        """,
        (team.team_id, team.abbreviation, team.name, team.city, synced_at),
    )


def upsert_player(
    conn: sqlite3.Connection, player_id: int, full_name: str, team_id: int, synced_at: str
) -> None:
    conn.execute(
        """
        INSERT INTO players (player_id, full_name, team_id, is_active, source_last_synced_at)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(player_id) DO UPDATE SET
            full_name = excluded.full_name,
            team_id = excluded.team_id,
            source_last_synced_at = excluded.source_last_synced_at
        """,
        (player_id, full_name, team_id, synced_at),
    )


def upsert_game(
    conn: sqlite3.Connection,
    game_id: str,
    season: str,
    game_date: str,
    home_team_id: int,
    away_team_id: int,
    status: str,
    synced_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO games (game_id, season, game_date, home_team_id, away_team_id, status, source_last_synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(game_id) DO UPDATE SET
            season = excluded.season,
            game_date = excluded.game_date,
            home_team_id = excluded.home_team_id,
            away_team_id = excluded.away_team_id,
            status = excluded.status,
            source_last_synced_at = excluded.source_last_synced_at
        """,
        (game_id, season, game_date, home_team_id, away_team_id, status, synced_at),
    )


def upsert_player_game_stats(conn: sqlite3.Connection, row: RawGameLogRow, synced_at: str) -> None:
    conn.execute(
        """
        INSERT INTO player_game_stats (
            game_id, player_id, team_id, minutes, points, rebounds, assists, steals, blocks,
            turnovers, field_goals_made, field_goals_attempted, three_pointers_made,
            three_pointers_attempted, free_throws_made, free_throws_attempted, plus_minus,
            source_last_synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(game_id, player_id) DO UPDATE SET
            team_id = excluded.team_id,
            minutes = excluded.minutes,
            points = excluded.points,
            rebounds = excluded.rebounds,
            assists = excluded.assists,
            steals = excluded.steals,
            blocks = excluded.blocks,
            turnovers = excluded.turnovers,
            field_goals_made = excluded.field_goals_made,
            field_goals_attempted = excluded.field_goals_attempted,
            three_pointers_made = excluded.three_pointers_made,
            three_pointers_attempted = excluded.three_pointers_attempted,
            free_throws_made = excluded.free_throws_made,
            free_throws_attempted = excluded.free_throws_attempted,
            plus_minus = excluded.plus_minus,
            source_last_synced_at = excluded.source_last_synced_at
        """,
        (
            row.game_id,
            row.player_id,
            row.team_id,
            row.minutes,
            row.points,
            row.rebounds,
            row.assists,
            row.steals,
            row.blocks,
            row.turnovers,
            row.field_goals_made,
            row.field_goals_attempted,
            row.three_pointers_made,
            row.three_pointers_attempted,
            row.free_throws_made,
            row.free_throws_attempted,
            row.plus_minus,
            synced_at,
        ),
    )


def upsert_prediction(
    conn: sqlite3.Connection,
    player_id: int,
    game_id: str,
    prop_type: str,
    predicted_value: float,
    predicted_low: Optional[float],
    predicted_high: Optional[float],
    model_name: str,
    model_version: str,
    generated_at: str,
    is_lock: bool = False,
    scoring_cv: Optional[float] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO predictions (
            player_id, game_id, prop_type, predicted_value, predicted_low, predicted_high,
            is_lock, scoring_cv, model_name, model_version, generated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_id, game_id, prop_type, model_name, model_version) DO UPDATE SET
            predicted_value = excluded.predicted_value,
            predicted_low = excluded.predicted_low,
            predicted_high = excluded.predicted_high,
            is_lock = excluded.is_lock,
            scoring_cv = excluded.scoring_cv,
            generated_at = excluded.generated_at
        """,
        (
            player_id,
            game_id,
            prop_type,
            predicted_value,
            predicted_low,
            predicted_high,
            int(is_lock),
            scoring_cv,
            model_name,
            model_version,
            generated_at,
        ),
    )


def get_scheduled_games(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT game_id, season, game_date, home_team_id, away_team_id
        FROM games
        WHERE status = 'SCHEDULED'
        ORDER BY game_date
        """
    ).fetchall()


def get_players_for_team(conn: sqlite3.Connection, team_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT player_id, full_name FROM players WHERE team_id = ? AND is_active = 1",
        (team_id,),
    ).fetchall()


def get_player_history(
    conn: sqlite3.Connection, player_id: int, stat_column: str
) -> list[tuple[str, float]]:
    if stat_column not in ALLOWED_STAT_COLUMNS:
        raise ValueError(f"Unsupported stat column: {stat_column}")
    rows = conn.execute(
        f"""
        SELECT g.season AS season, pgs.{stat_column} AS value
        FROM player_game_stats pgs
        JOIN games g ON g.game_id = pgs.game_id
        WHERE pgs.player_id = ? AND g.status = 'FINAL'
        ORDER BY g.game_date ASC, g.game_id ASC
        """,
        (player_id,),
    ).fetchall()
    return [(row["season"], row["value"]) for row in rows if row["value"] is not None]


def fetch_all_stats_for_backtest(
    conn: sqlite3.Connection, stat_column: str, seasons: list[str]
) -> list[sqlite3.Row]:
    if stat_column not in ALLOWED_STAT_COLUMNS:
        raise ValueError(f"Unsupported stat column: {stat_column}")
    placeholders = ",".join("?" for _ in seasons)
    return conn.execute(
        f"""
        SELECT pgs.player_id AS player_id, g.season AS season, g.game_date AS game_date,
               g.game_id AS game_id, pgs.{stat_column} AS value
        FROM player_game_stats pgs
        JOIN games g ON g.game_id = pgs.game_id
        WHERE g.status = 'FINAL' AND g.season IN ({placeholders}) AND pgs.{stat_column} IS NOT NULL
        ORDER BY pgs.player_id ASC, g.game_date ASC, g.game_id ASC
        """,
        seasons,
    ).fetchall()


def get_player_minutes_history(
    conn: sqlite3.Connection, player_id: int, stat_column: str
) -> list[tuple[str, float, float]]:
    if stat_column not in ALLOWED_STAT_COLUMNS:
        raise ValueError(f"Unsupported stat column: {stat_column}")
    rows = conn.execute(
        f"""
        SELECT g.season AS season, pgs.minutes AS minutes, pgs.{stat_column} AS value
        FROM player_game_stats pgs
        JOIN games g ON g.game_id = pgs.game_id
        WHERE pgs.player_id = ? AND g.status = 'FINAL' AND pgs.minutes IS NOT NULL
        ORDER BY g.game_date ASC, g.game_id ASC
        """,
        (player_id,),
    ).fetchall()
    return [
        (row["season"], row["minutes"], row["value"]) for row in rows if row["value"] is not None
    ]


def fetch_all_minutes_stats_for_backtest(
    conn: sqlite3.Connection, stat_column: str, seasons: list[str]
) -> list[sqlite3.Row]:
    if stat_column not in ALLOWED_STAT_COLUMNS:
        raise ValueError(f"Unsupported stat column: {stat_column}")
    placeholders = ",".join("?" for _ in seasons)
    return conn.execute(
        f"""
        SELECT pgs.player_id AS player_id, g.season AS season, g.game_date AS game_date,
               g.game_id AS game_id, pgs.minutes AS minutes, pgs.{stat_column} AS value
        FROM player_game_stats pgs
        JOIN games g ON g.game_id = pgs.game_id
        WHERE g.status = 'FINAL' AND g.season IN ({placeholders})
              AND pgs.minutes IS NOT NULL AND pgs.{stat_column} IS NOT NULL
        ORDER BY pgs.player_id ASC, g.game_date ASC, g.game_id ASC
        """,
        seasons,
    ).fetchall()


def get_prop_type(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT name, stat_column, description FROM prop_types WHERE name = ?", (name,)
    ).fetchone()
