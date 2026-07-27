"""All knowledge of stats.wnba.com/cdn.wnba.com endpoints lives in this module.

stats.wnba.com silently drops connections from plain `requests`/`curl` clients
(Akamai-style TLS fingerprinting) -- confirmed by spiking the endpoint directly.
`curl_cffi` with `impersonate="chrome"` is required to get a response at all.
"""

import time

from curl_cffi import requests

from pipeline.client.dto import RawGameLogRow, RawScheduleGame, RawTeam
from pipeline.config import SCHEDULE_URL, STATS_BASE_URL, WNBA_LEAGUE_ID

_HEADERS = {
    "Referer": "https://www.wnba.com/",
    "Origin": "https://www.wnba.com",
    "Accept": "application/json",
}

_REQUEST_DELAY_SECONDS = 0.6


class WnbaClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()

    def get_league_game_log(self, season: str) -> list[RawGameLogRow]:
        response = self._session.get(
            f"{STATS_BASE_URL}/leaguegamelog",
            params={
                "Counter": 1000,
                "Direction": "DESC",
                "LeagueID": WNBA_LEAGUE_ID,
                "PlayerOrTeam": "P",
                "Season": season,
                "SeasonType": "Regular Season",
                "Sorter": "DATE",
            },
            headers=_HEADERS,
            impersonate="chrome",
            timeout=30,
        )
        response.raise_for_status()
        time.sleep(_REQUEST_DELAY_SECONDS)

        result_set = response.json()["resultSets"][0]
        headers = result_set["headers"]
        return [_row_to_game_log(season, dict(zip(headers, row))) for row in result_set["rowSet"]]

    def get_schedule(self) -> list[RawScheduleGame]:
        """Returns the current season's full schedule (past + upcoming games).

        The CDN feed only serves the current season -- there is no equivalent
        feed for past seasons, so historical games come from get_league_game_log
        instead.
        """
        response = self._session.get(SCHEDULE_URL, impersonate="chrome", timeout=30)
        response.raise_for_status()

        league_schedule = response.json()["leagueSchedule"]
        season = league_schedule["seasonYear"]
        games = []
        for game_date in league_schedule["gameDates"]:
            for game in game_date["games"]:
                games.append(
                    RawScheduleGame(
                        game_id=game["gameId"],
                        season=season,
                        game_date=game["gameDateTimeUTC"][:10],
                        status="FINAL" if game["gameStatus"] == 3 else "SCHEDULED",
                        home_team=_team_from_schedule(game["homeTeam"]),
                        away_team=_team_from_schedule(game["awayTeam"]),
                    )
                )
        return games


def _row_to_game_log(season: str, row: dict) -> RawGameLogRow:
    return RawGameLogRow(
        season=season,
        game_id=row["GAME_ID"],
        game_date=row["GAME_DATE"],
        matchup=row["MATCHUP"],
        player_id=row["PLAYER_ID"],
        player_name=row["PLAYER_NAME"],
        team_id=row["TEAM_ID"],
        team_abbreviation=row["TEAM_ABBREVIATION"],
        team_name=row["TEAM_NAME"],
        minutes=row["MIN"],
        points=row["PTS"],
        rebounds=row["REB"],
        assists=row["AST"],
        steals=row["STL"],
        blocks=row["BLK"],
        turnovers=row["TOV"],
        field_goals_made=row["FGM"],
        field_goals_attempted=row["FGA"],
        three_pointers_made=row["FG3M"],
        three_pointers_attempted=row["FG3A"],
        free_throws_made=row["FTM"],
        free_throws_attempted=row["FTA"],
        plus_minus=row["PLUS_MINUS"],
    )


def _team_from_schedule(team: dict) -> RawTeam:
    return RawTeam(
        team_id=team["teamId"],
        abbreviation=team["teamTricode"],
        name=team["teamName"],
        city=team["teamCity"],
    )
