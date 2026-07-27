from pipeline.client.dto import RawTeam
from pipeline.db import repository


def test_upsert_team_is_idempotent_and_updates_fields(conn):
    team = RawTeam(team_id=1, abbreviation="NYL", name="Liberty", city="New York")
    repository.upsert_team(conn, team, synced_at="2026-01-01T00:00:00Z")
    repository.upsert_team(conn, team, synced_at="2026-01-02T00:00:00Z")

    rows = conn.execute("SELECT * FROM teams").fetchall()
    assert len(rows) == 1
    assert rows[0]["source_last_synced_at"] == "2026-01-02T00:00:00Z"


def test_upsert_team_preserves_city_when_new_value_is_none(conn):
    full = RawTeam(team_id=1, abbreviation="NYL", name="Liberty", city="New York")
    repository.upsert_team(conn, full, synced_at="2026-01-01T00:00:00Z")

    partial = RawTeam(team_id=1, abbreviation="NYL", name="Liberty", city=None)
    repository.upsert_team(conn, partial, synced_at="2026-01-02T00:00:00Z")

    row = conn.execute("SELECT city FROM teams WHERE team_id = 1").fetchone()
    assert row["city"] == "New York"


def test_upsert_player_updates_team_on_conflict(conn):
    repository.upsert_team(conn, RawTeam(1, "NYL", "Liberty"), "2026-01-01T00:00:00Z")
    repository.upsert_team(conn, RawTeam(2, "ATL", "Dream"), "2026-01-01T00:00:00Z")

    repository.upsert_player(conn, player_id=100, full_name="Test Player", team_id=1, synced_at="t1")
    repository.upsert_player(conn, player_id=100, full_name="Test Player", team_id=2, synced_at="t2")

    rows = conn.execute("SELECT * FROM players").fetchall()
    assert len(rows) == 1
    assert rows[0]["team_id"] == 2


def test_upsert_game_is_idempotent(conn):
    repository.upsert_team(conn, RawTeam(1, "NYL", "Liberty"), "t")
    repository.upsert_team(conn, RawTeam(2, "ATL", "Dream"), "t")

    repository.upsert_game(conn, "g1", "2026", "2026-05-01", 1, 2, "SCHEDULED", "t1")
    repository.upsert_game(conn, "g1", "2026", "2026-05-01", 1, 2, "FINAL", "t2")

    rows = conn.execute("SELECT * FROM games").fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "FINAL"


def test_get_player_history_orders_chronologically_and_skips_nulls(conn):
    repository.upsert_team(conn, RawTeam(1, "NYL", "Liberty"), "t")
    repository.upsert_team(conn, RawTeam(2, "ATL", "Dream"), "t")
    repository.upsert_player(conn, 100, "Test Player", 1, "t")

    repository.upsert_game(conn, "g1", "2025", "2025-06-01", 1, 2, "FINAL", "t")
    repository.upsert_game(conn, "g2", "2026", "2026-05-10", 1, 2, "FINAL", "t")
    repository.upsert_game(conn, "g3", "2026", "2026-05-01", 1, 2, "FINAL", "t")

    from pipeline.client.dto import RawGameLogRow

    def stat_row(game_id, season, points):
        return RawGameLogRow(
            season=season,
            game_id=game_id,
            game_date="",
            matchup="",
            player_id=100,
            player_name="Test Player",
            team_id=1,
            team_abbreviation="NYL",
            team_name="Liberty",
            minutes=20.0,
            points=points,
            rebounds=None,
            assists=None,
            steals=None,
            blocks=None,
            turnovers=None,
            field_goals_made=None,
            field_goals_attempted=None,
            three_pointers_made=None,
            three_pointers_attempted=None,
            free_throws_made=None,
            free_throws_attempted=None,
            plus_minus=None,
        )

    repository.upsert_player_game_stats(conn, stat_row("g1", "2025", 10), "t")
    repository.upsert_player_game_stats(conn, stat_row("g3", "2026", 12), "t")
    repository.upsert_player_game_stats(conn, stat_row("g2", "2026", 15), "t")

    history = repository.get_player_history(conn, 100, "points")

    assert history == [("2025", 10), ("2026", 12), ("2026", 15)]
