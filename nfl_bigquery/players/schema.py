from __future__ import annotations

from nfl_bigquery.dictionary import build_specs
from nfl_bigquery.schema import INGESTED_AT_SPEC, ColumnSpec

DIM_PLAYERS_KEY = "gsis_id"
DIM_PLAYERS_ENRICHMENT = {
    "gsis_id": {"mode": "REQUIRED", "semantic_tags": ["identifier", "primary_key"],
                "example_value": "00-0033873",
                "gotchas": ["Canonical nflverse player id; joins to *_player_id in plays."]},
    "display_name": {"semantic_tags": ["dimension"]},
    "position": {"semantic_tags": ["dimension"]},
    "position_group": {"semantic_tags": ["dimension"]},
    "status": {"semantic_tags": ["dimension"]},
}

DIM_PLAYERS_SCHEMA: list[ColumnSpec] = build_specs(
    "players", enrichment=DIM_PLAYERS_ENRICHMENT,
) + [INGESTED_AT_SPEC]
