"""nfl_plays schema: all nflverse pbp columns (dictionary-seeded) + enrichment,
plus the synthetic ingested_at column and partitioning config.
"""
from __future__ import annotations

from nfl_bigquery.dictionary import build_specs
from nfl_bigquery.partition import TimePartition
from nfl_bigquery.plays.enrichment import ENRICHMENT
from nfl_bigquery.schema import INGESTED_AT_SPEC, ColumnSpec

# Columns whose BQ type must override the dictionary's generic type.
PLAYS_TYPE_OVERRIDES = {"game_date": "DATE"}

PLAYS_SCHEMA: list[ColumnSpec] = build_specs(
    "pbp", enrichment=ENRICHMENT, type_overrides=PLAYS_TYPE_OVERRIDES,
) + [INGESTED_AT_SPEC]

PLAYS_PARTITION = TimePartition(field="game_date", clustering=["season", "week", "posteam"])
