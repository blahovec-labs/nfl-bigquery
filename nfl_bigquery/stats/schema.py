from __future__ import annotations

from nfl_bigquery.dictionary import build_specs
from nfl_bigquery.partition import SeasonRangePartition
from nfl_bigquery.schema import ColumnSpec

WEEKLY_STATS_ENRICHMENT = {
    "player_id": {"mode": "REQUIRED", "semantic_tags": ["identifier", "join_key"],
                  "gotchas": ["gsis_id; join dim_players.gsis_id."]},
    "season": {"mode": "REQUIRED", "type": "INT64", "semantic_tags": ["partition_filter"],
               "valid_range": (1999.0, 2100.0)},
    "week": {"mode": "REQUIRED", "type": "INT64", "semantic_tags": ["cluster_key"],
             "valid_range": (1.0, 22.0)},
    "passing_yards": {"semantic_tags": ["metric"]},
    "rushing_yards": {"semantic_tags": ["metric"]},
    "receiving_yards": {"semantic_tags": ["metric"]},
    "passing_tds": {"semantic_tags": ["metric"]},
    "rushing_tds": {"semantic_tags": ["metric"]},
    "receiving_tds": {"semantic_tags": ["metric"]},
}

WEEKLY_STATS_SCHEMA: list[ColumnSpec] = build_specs(
    "player_stats", enrichment=WEEKLY_STATS_ENRICHMENT,
)
WEEKLY_STATS_PARTITION = SeasonRangePartition(clustering=["week", "player_id"])
