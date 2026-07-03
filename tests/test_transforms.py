import pandas as pd

from nfl_bigquery.games.transform import transform_schedules
from nfl_bigquery.players.transform import transform_players
from nfl_bigquery.plays.schema import PLAYS_SCHEMA
from nfl_bigquery.plays.transform import transform_pbp
from nfl_bigquery.schema import spec_names
from nfl_bigquery.stats.transform import transform_player_stats

FIX = "tests/fixtures"


def test_transform_pbp_reindexes_and_stamps():
    raw = pd.read_parquet(f"{FIX}/pbp_2023_sample.parquet")
    out = transform_pbp(raw)
    assert list(out.columns) == spec_names(PLAYS_SCHEMA)
    assert bool(out["ingested_at"].notna().all())
    assert len(out) == len(raw)


def test_transform_schedules_renames_gameday():
    raw = pd.read_parquet(f"{FIX}/schedules_2023_sample.parquet")
    out = transform_schedules(raw)
    assert "game_date" in out.columns
    assert "gameday" not in out.columns
    assert bool(out["ingested_at"].notna().all())


def test_transform_player_stats_stamps():
    raw = pd.read_parquet(f"{FIX}/player_stats_2023_sample.parquet")
    out = transform_player_stats(raw)
    assert bool(out["ingested_at"].notna().all())
    assert "season" in out.columns


def test_transform_players_has_key():
    raw = pd.read_parquet(f"{FIX}/players_2023_sample.parquet")
    out = transform_players(raw)
    assert "gsis_id" in out.columns
    assert bool(out["ingested_at"].notna().all())
