from nfl_bigquery.games.schema import GAMES_PARTITION, GAMES_SCHEMA
from nfl_bigquery.partition import SeasonRangePartition, TimePartition
from nfl_bigquery.players.schema import DIM_PLAYERS_KEY, DIM_PLAYERS_SCHEMA
from nfl_bigquery.schema import spec_names
from nfl_bigquery.stats.schema import WEEKLY_STATS_PARTITION, WEEKLY_STATS_SCHEMA


def test_games_schema():
    by = {s.name: s for s in GAMES_SCHEMA}
    assert by["game_id"].mode == "REQUIRED"
    assert by["season"].mode == "REQUIRED"
    assert by["game_date"].type == "DATE"
    assert isinstance(GAMES_PARTITION, TimePartition)
    assert GAMES_PARTITION.clustering == ["season", "week"]


def test_weekly_stats_schema():
    by = {s.name: s for s in WEEKLY_STATS_SCHEMA}
    assert by["season"].mode == "REQUIRED"
    assert isinstance(WEEKLY_STATS_PARTITION, SeasonRangePartition)
    assert WEEKLY_STATS_PARTITION.clustering == ["week", "player_id"]


def test_dim_players_schema():
    names = spec_names(DIM_PLAYERS_SCHEMA)
    assert DIM_PLAYERS_KEY == "gsis_id"
    assert "gsis_id" in names
    by = {s.name: s for s in DIM_PLAYERS_SCHEMA}
    assert by["gsis_id"].mode == "REQUIRED"
