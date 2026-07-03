# tests/test_fixtures_present.py
from pathlib import Path

import pandas as pd

DICT_DIR = Path("nfl_bigquery/dictionaries")
FIX_DIR = Path("tests/fixtures")


def test_dictionaries_vendored():
    for name in ["pbp", "schedules", "players", "player_stats"]:
        df = pd.read_csv(DICT_DIR / f"{name}.csv")
        assert {"field", "description", "type"} <= set(df.columns)
        assert len(df) > 0


def test_pbp_dictionary_is_large():
    df = pd.read_csv(DICT_DIR / "pbp.csv")
    assert len(df) >= 300  # nflverse pbp dictionary is ~372 rows


def test_parquet_fixtures_present():
    for name in ["pbp", "schedules", "players", "player_stats"]:
        df = pd.read_parquet(FIX_DIR / f"{name}_2023_sample.parquet")
        assert len(df) > 0


def test_dictionary_types_are_valid_tokens():
    valid = ["numeric", "character", "integer", "logical", "date", "timestamp"]
    for name in ["pbp", "schedules", "players", "player_stats"]:
        df = pd.read_csv(DICT_DIR / f"{name}.csv")
        bad = df[~df["type"].isin(valid)]
        assert bad.empty, (
            f"{name}.csv has invalid type tokens:\n{bad.to_string()}"
        )
