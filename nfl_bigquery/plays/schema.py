"""nfl_plays schema: all nflverse pbp columns (dictionary-seeded) + enrichment,
plus the synthetic ingested_at column and partitioning config.
"""
from __future__ import annotations

from nfl_bigquery.dictionary import build_specs
from nfl_bigquery.partition import TimePartition
from nfl_bigquery.plays.enrichment import ENRICHMENT
from nfl_bigquery.schema import ColumnSpec

# Columns whose BQ type must override the dictionary's generic type.
PLAYS_TYPE_OVERRIDES = {"game_date": "DATE"}

_INGESTED_AT = ColumnSpec(
    name="ingested_at", type="TIMESTAMP", mode="REQUIRED",
    short_description="UTC timestamp this row was written to BigQuery.",
    business_definition="Ingestion timestamp set by nfl-bigquery at write time.",
    semantic_tags=["lineage"], valid_range=None, valid_values=None,
    example_value=None, gotchas=[], source_field="(synthetic)",
    dictionary_type=None, deprecated_in_year=None,
)

PLAYS_SCHEMA: list[ColumnSpec] = build_specs(
    "pbp", enrichment=ENRICHMENT, type_overrides=PLAYS_TYPE_OVERRIDES,
) + [_INGESTED_AT]

PLAYS_PARTITION = TimePartition(field="game_date", clustering=["season", "week", "posteam"])
