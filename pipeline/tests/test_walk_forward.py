from pipeline.backtest.walk_forward import run_backtest, run_backtest_minutes_based
from pipeline.client.dto import RawGameLogRow, RawTeam
from pipeline.db import repository
from pipeline.props import PROP_TYPES


def _stat_row(game_id, season, player_id, points, minutes=20.0):
    return RawGameLogRow(
        season=season,
        game_id=game_id,
        game_date="",
        matchup="",
        player_id=player_id,
        player_name="Test Player",
        team_id=1,
        team_abbreviation="NYL",
        team_name="Liberty",
        minutes=minutes,
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


def test_walk_forward_matches_hand_computed_mae_and_mape(conn):
    repository.upsert_team(conn, RawTeam(1, "NYL", "Liberty"), "t")
    repository.upsert_team(conn, RawTeam(2, "ATL", "Dream"), "t")
    repository.upsert_player(conn, 100, "Test Player", 1, "t")

    # season 2025: two games (10, 20); season 2026: three games (30, 40, 50).
    games = [
        ("g1", "2025", "2025-06-01", 10),
        ("g2", "2025", "2025-06-03", 20),
        ("g3", "2026", "2026-05-01", 30),
        ("g4", "2026", "2026-05-03", 40),
        ("g5", "2026", "2026-05-05", 50),
    ]
    for game_id, season, date, points in games:
        repository.upsert_game(conn, game_id, season, date, 1, 2, "FINAL", "t")
        repository.upsert_player_game_stats(conn, _stat_row(game_id, season, 100, points), "t")

    report = run_backtest(conn, PROP_TYPES["POINTS"], seasons=["2025", "2026"], n=2)

    # Hand-computed walk-forward with n=2 (see PR description / commit for the trace):
    # g1: no history anywhere -> skipped
    # g2: 1 current-season game (<2), no prior season -> predict 10 -> |20-10|=10
    # g3: 0 current-season games, prior season [10,20] -> predict 15 -> |30-15|=15
    # g4: 1 current-season game (<2), prior season still used -> predict 15 -> |40-15|=25
    # g5: 2 current-season games [30,40] -> predict 35 -> |50-35|=15
    assert report.n_skipped == 1
    assert report.n_evaluated == 4
    assert report.mae == (10 + 15 + 25 + 15) / 4
    assert report.mape_excluded_zero_actuals == 0
    expected_mape = ((10 / 20) + (15 / 30) + (25 / 40) + (15 / 50)) / 4
    assert abs(report.mape - expected_mape) < 1e-9


def test_minutes_based_walk_forward_matches_hand_computed_mae(conn):
    repository.upsert_team(conn, RawTeam(1, "NYL", "Liberty"), "t")
    repository.upsert_team(conn, RawTeam(2, "ATL", "Dream"), "t")
    repository.upsert_player(conn, 100, "Test Player", 1, "t")

    # season 2025: (10min,5pts), (20min,10pts) -- rate 0.5 both games.
    # season 2026: (30min,9pts), (30min,21pts), (10min,1pt).
    games = [
        ("g1", "2025", "2025-06-01", 5, 10),
        ("g2", "2025", "2025-06-03", 10, 20),
        ("g3", "2026", "2026-05-01", 9, 30),
        ("g4", "2026", "2026-05-03", 21, 30),
        ("g5", "2026", "2026-05-05", 1, 10),
    ]
    for game_id, season, date, points, minutes in games:
        repository.upsert_game(conn, game_id, season, date, 1, 2, "FINAL", "t")
        repository.upsert_player_game_stats(
            conn, _stat_row(game_id, season, 100, points, minutes), "t"
        )

    report = run_backtest_minutes_based(
        conn, PROP_TYPES["POINTS"], seasons=["2025", "2026"], n=2, minutes_n=2
    )

    # Hand-computed walk-forward with n=2, minutes_n=2:
    # g1: no history anywhere -> skipped
    # g2: rate window=[(10,5)] (only game so far) -> rate=0.5; minutes window=[10] -> predicted=10*0.5=5; actual=10 -> |10-5|=5
    # g3: current season empty -> both windows fall back to full 2025 -> rate=(5+10)/(10+20)=0.5,
    #     predicted_minutes=mean(10,20)=15 -> predicted=7.5; actual=9 -> |9-7.5|=1.5
    # g4: current season has 1 game (<2) -> still falls back to 2025 for both -> predicted=7.5; actual=21 -> |21-7.5|=13.5
    # g5: current season now has 2 games [(30,9),(30,21)] -> rate=(9+21)/(30+30)=0.5, predicted_minutes=30 -> predicted=15; actual=1 -> |1-15|=14
    assert report.n_skipped == 1
    assert report.n_evaluated == 4
    assert report.mae == (5 + 1.5 + 13.5 + 14) / 4
