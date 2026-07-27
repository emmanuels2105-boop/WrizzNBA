import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pipeline.client.dto import RawGameLogRow, RawTeam
from pipeline.client.wnba_client import WnbaClient
from pipeline.db import repository


@dataclass
class IngestSummary:
    teams: set[int] = field(default_factory=set)
    players: set[int] = field(default_factory=set)
    games: set[str] = field(default_factory=set)
    player_game_stats: int = 0

    def __str__(self) -> str:
        return (
            f"teams={len(self.teams)} players={len(self.players)} "
            f"games={len(self.games)} player_game_stats={self.player_game_stats}"
        )


def _is_wnba_franchise_team_id(team_id: int) -> bool:
    """League game logs include exhibition data (national-team games, All-Star
    draft squads) whose "teams" get assigned non-franchise ids -- e.g. a 5-digit
    national-team id, or a 1611665xxx All-Star squad id, instead of the normal
    1611661xxx franchise id range. Filtering to that range drops every row from
    those exhibition games, since none of their players carry a real franchise id.
    """
    return 1_611_661_000 <= team_id <= 1_611_661_999


def _parse_matchup_home_away(
    row: RawGameLogRow, abbreviation_to_team_id: dict[str, int]
) -> tuple[int, int]:
    if " vs. " in row.matchup:
        opponent_abbr = row.matchup.split(" vs. ")[1].strip()
        return row.team_id, abbreviation_to_team_id[opponent_abbr]
    if " @ " in row.matchup:
        opponent_abbr = row.matchup.split(" @ ")[1].strip()
        return abbreviation_to_team_id[opponent_abbr], row.team_id
    raise ValueError(f"Unrecognized matchup format: {row.matchup!r}")


def _ingest_season_game_log(
    conn: sqlite3.Connection,
    client: WnbaClient,
    season: str,
    synced_at: str,
    summary: IngestSummary,
) -> None:
    rows = [r for r in client.get_league_game_log(season) if _is_wnba_franchise_team_id(r.team_id)]
    # Ascending order so upserting a player's team_id last reflects their most recent game.
    rows.sort(key=lambda r: (r.game_date, r.game_id))

    abbreviation_to_team_id = {r.team_abbreviation: r.team_id for r in rows}
    upserted_games: set[str] = set()

    # Teams must all exist before any game row is inserted -- a game's home/away
    # team may belong to a team whose own game-log rows haven't been seen yet.
    for team_id, team_abbr, team_name in {(r.team_id, r.team_abbreviation, r.team_name) for r in rows}:
        repository.upsert_team(conn, RawTeam(team_id, team_abbr, team_name), synced_at)
        summary.teams.add(team_id)

    for row in rows:
        if row.game_id not in upserted_games:
            home_team_id, away_team_id = _parse_matchup_home_away(row, abbreviation_to_team_id)
            repository.upsert_game(
                conn, row.game_id, row.season, row.game_date, home_team_id, away_team_id, "FINAL", synced_at
            )
            upserted_games.add(row.game_id)
            summary.games.add(row.game_id)

        repository.upsert_player(conn, row.player_id, row.player_name, row.team_id, synced_at)
        summary.players.add(row.player_id)

        repository.upsert_player_game_stats(conn, row, synced_at)
        summary.player_game_stats += 1

    conn.commit()


def _ingest_schedule(
    conn: sqlite3.Connection, client: WnbaClient, synced_at: str, summary: IngestSummary
) -> None:
    for game in client.get_schedule():
        if not (
            _is_wnba_franchise_team_id(game.home_team.team_id)
            and _is_wnba_franchise_team_id(game.away_team.team_id)
        ):
            continue

        for team in (game.home_team, game.away_team):
            repository.upsert_team(conn, team, synced_at)
            summary.teams.add(team.team_id)

        repository.upsert_game(
            conn,
            game.game_id,
            game.season,
            game.game_date,
            game.home_team.team_id,
            game.away_team.team_id,
            game.status,
            synced_at,
        )
        summary.games.add(game.game_id)

    conn.commit()


def run_ingest(conn: sqlite3.Connection, client: WnbaClient, seasons: list[str]) -> IngestSummary:
    summary = IngestSummary()
    synced_at = datetime.now(timezone.utc).isoformat()

    for season in sorted(seasons):
        _ingest_season_game_log(conn, client, season, synced_at, summary)

    _ingest_schedule(conn, client, synced_at, summary)

    return summary
