from datetime import date

from pipeline.client.dto import RawGameLogRow, RawTeam
from pipeline.db import repository
from pipeline.prediction.generate import generate_predictions
from pipeline.props import PropType

POINTS = PropType(name="POINTS", stat_column="points")
TODAY = date(2026, 7, 30)
TOMORROW = "2026-07-31"
DAY_AFTER = "2026-08-01"


def _seed_team_with_players(conn, team_id, abbr, player_specs):
    """player_specs: list of (player_id, full_name, points_per_game) -- gives each
    player 10 finished games this season at a steady points total, so every
    player has enough history for a real (non-None) prediction."""
    repository.upsert_team(conn, RawTeam(team_id, abbr, abbr), "t")
    for player_id, full_name, points in player_specs:
        for i in range(10):
            game_id = f"hist-{player_id}-{i}"
            repository.upsert_game(conn, game_id, "2026", f"2026-06-{i+1:02d}", team_id, team_id, "FINAL", "t")
            row = RawGameLogRow(
                season="2026", game_id=game_id, game_date=f"2026-06-{i+1:02d}", matchup="",
                player_id=player_id, player_name=full_name, team_id=team_id,
                team_abbreviation=abbr, team_name=abbr, minutes=20.0, points=points,
                rebounds=None, assists=None, steals=None, blocks=None, turnovers=None,
                field_goals_made=None, field_goals_attempted=None, three_pointers_made=None,
                three_pointers_attempted=None, free_throws_made=None, free_throws_attempted=None,
                plus_minus=None,
            )
            repository.upsert_player(conn, player_id, full_name, team_id, "t")
            repository.upsert_player_game_stats(conn, row, "t")


def test_only_predicts_games_happening_tomorrow(conn):
    _seed_team_with_players(conn, 1, "AAA", [(100, "A Player", 10)])
    _seed_team_with_players(conn, 2, "BBB", [(200, "B Player", 10)])
    _seed_team_with_players(conn, 3, "CCC", [(300, "C Player", 10)])
    _seed_team_with_players(conn, 4, "DDD", [(400, "D Player", 10)])
    repository.upsert_game(conn, "g-tomorrow", "2026", TOMORROW, 1, 2, "SCHEDULED", "t")
    repository.upsert_game(conn, "g-later", "2026", DAY_AFTER, 3, 4, "SCHEDULED", "t")

    summary = generate_predictions(conn, POINTS, today=TODAY)

    rows = conn.execute("SELECT player_id, game_id FROM predictions").fetchall()
    assert {r["player_id"] for r in rows} == {100, 200}
    assert all(r["game_id"] == "g-tomorrow" for r in rows)
    assert summary.predictions_written == 2


def test_no_games_tomorrow_predicts_nothing(conn):
    _seed_team_with_players(conn, 1, "AAA", [(100, "A Player", 10)])
    _seed_team_with_players(conn, 2, "BBB", [(200, "B Player", 10)])
    repository.upsert_game(conn, "g-later", "2026", DAY_AFTER, 1, 2, "SCHEDULED", "t")

    summary = generate_predictions(conn, POINTS, today=TODAY)

    assert summary.predictions_written == 0
    assert conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0] == 0


def test_caps_at_top_n_players_by_predicted_value_across_both_rosters(conn):
    # 3 players per team, 6 total -- cap top_n=4 should keep the 4 highest scorers
    # from either team, not e.g. an even 2-per-team split.
    _seed_team_with_players(conn, 1, "AAA", [(101, "A1", 30), (102, "A2", 5), (103, "A3", 3)])
    _seed_team_with_players(conn, 2, "BBB", [(201, "B1", 25), (202, "B2", 20), (203, "B3", 1)])
    repository.upsert_game(conn, "g-tomorrow", "2026", TOMORROW, 1, 2, "SCHEDULED", "t")

    summary = generate_predictions(conn, POINTS, top_n=4, today=TODAY)

    assert summary.predictions_written == 4
    predicted_players = {
        r["player_id"] for r in conn.execute("SELECT player_id FROM predictions").fetchall()
    }
    assert predicted_players == {101, 201, 202, 102}  # top 4 by points-per-game: 30, 25, 20, 5
