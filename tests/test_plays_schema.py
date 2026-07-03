from nfl_bigquery.plays.schema import PLAYS_PARTITION, PLAYS_SCHEMA
from nfl_bigquery.schema import spec_names


def test_plays_schema_large_and_unique():
    names = spec_names(PLAYS_SCHEMA)
    assert len(names) >= 300
    assert len(names) == len(set(names)), "duplicate column names"


def test_core_identifiers_required():
    by = {s.name: s for s in PLAYS_SCHEMA}
    for col in ["game_id", "play_id", "season", "week", "game_date"]:
        assert by[col].mode == "REQUIRED", col
    assert by["game_date"].type == "DATE"
    assert by["ingested_at"].type == "TIMESTAMP"


def test_key_columns_enriched():
    by = {s.name: s for s in PLAYS_SCHEMA}
    assert by["epa"].valid_range is not None
    assert "metric" in by["epa"].semantic_tags
    assert by["play_type"].valid_values is not None


def test_partition_config():
    assert PLAYS_PARTITION.field == "game_date"
    assert PLAYS_PARTITION.clustering == ["season", "week", "posteam"]
