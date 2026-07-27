from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RawTeam:
    team_id: int
    abbreviation: str
    name: str
    city: Optional[str] = None


@dataclass(frozen=True)
class RawGameLogRow:
    season: str
    game_id: str
    game_date: str
    matchup: str  # e.g. "NYL vs. ATL" (home) or "NYL @ ATL" (away)
    player_id: int
    player_name: str
    team_id: int
    team_abbreviation: str
    team_name: str
    minutes: Optional[float]
    points: int
    rebounds: Optional[int]
    assists: Optional[int]
    steals: Optional[int]
    blocks: Optional[int]
    turnovers: Optional[int]
    field_goals_made: Optional[int]
    field_goals_attempted: Optional[int]
    three_pointers_made: Optional[int]
    three_pointers_attempted: Optional[int]
    free_throws_made: Optional[int]
    free_throws_attempted: Optional[int]
    plus_minus: Optional[float]


@dataclass(frozen=True)
class RawScheduleGame:
    game_id: str
    season: str
    game_date: str
    status: str  # 'SCHEDULED' or 'FINAL'
    home_team: RawTeam
    away_team: RawTeam
