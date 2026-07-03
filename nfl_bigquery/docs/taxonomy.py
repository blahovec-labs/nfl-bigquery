"""Registry mapping table name → (ColumnSpec list, one-line description)."""
from __future__ import annotations

from dataclasses import dataclass

from nfl_bigquery.games.schema import GAMES_SCHEMA
from nfl_bigquery.players.schema import DIM_PLAYERS_SCHEMA
from nfl_bigquery.plays.schema import PLAYS_SCHEMA
from nfl_bigquery.schema import ColumnSpec
from nfl_bigquery.stats.schema import WEEKLY_STATS_SCHEMA


@dataclass(frozen=True)
class TableDoc:
    name: str
    description: str
    columns: list[ColumnSpec]


TABLES: dict[str, TableDoc] = {
    "nfl_plays": TableDoc(
        "nfl_plays",
        "nflverse play-by-play, one row per play (EPA/WPA/air-yards modeled).",
        PLAYS_SCHEMA,
    ),
    "games": TableDoc(
        "games",
        "nflverse schedule, one row per game (teams, scores, lines, roof, referee).",
        GAMES_SCHEMA,
    ),
    "weekly_player_stats": TableDoc(
        "weekly_player_stats",
        "nflverse weekly player box-score stats, one row per player-week.",
        WEEKLY_STATS_SCHEMA,
    ),
    "dim_players": TableDoc(
        "dim_players",
        "nflverse player dimension keyed on gsis_id.",
        DIM_PLAYERS_SCHEMA,
    ),
}
