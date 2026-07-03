from __future__ import annotations

from nfl_bigquery.dictionary import build_specs
from nfl_bigquery.partition import TimePartition
from nfl_bigquery.schema import INGESTED_AT_SPEC, ColumnSpec

GAMES_TYPE_OVERRIDES = {"gameday": "DATE", "game_date": "DATE"}
GAMES_ENRICHMENT = {
    "game_id": {"mode": "REQUIRED", "semantic_tags": ["identifier", "join_key"],
                "example_value": "2023_01_DET_KC"},
    "season": {"mode": "REQUIRED", "type": "INT64", "semantic_tags": ["identifier"],
               "valid_range": (1999.0, 2100.0)},
    "week": {"mode": "REQUIRED", "type": "INT64", "valid_range": (1.0, 22.0)},
    # keyed on the pre-rename dictionary field name `gameday`; _build() renames the
    # resulting spec to `game_date`, carrying this mode/type/tags through.
    "gameday": {"mode": "REQUIRED", "type": "DATE", "semantic_tags": ["partition_key"]},
    "home_team": {"semantic_tags": ["dimension"]},
    "away_team": {"semantic_tags": ["dimension"]},
    "spread_line": {"semantic_tags": ["betting"], "valid_range": (-30.0, 30.0)},
    "total_line": {"semantic_tags": ["betting"], "valid_range": (20.0, 75.0)},
    "roof": {"semantic_tags": ["dimension"],
             "valid_values": ["dome", "outdoors", "closed", "open", "retractable"]},
    "surface": {"semantic_tags": ["dimension"]},
    "referee": {"semantic_tags": ["dimension"]},
}


def _build() -> list[ColumnSpec]:
    specs = build_specs("schedules", enrichment=GAMES_ENRICHMENT,
                        type_overrides=GAMES_TYPE_OVERRIDES)
    # nflverse schedules names the date column `gameday`; rename to game_date for
    # cross-table consistency (transform renames the DataFrame column to match).
    renamed = []
    for s in specs:
        if s.name == "gameday":
            renamed.append(ColumnSpec(**{**s.__dict__, "name": "game_date"}))
        else:
            renamed.append(s)
    return renamed


GAMES_SCHEMA: list[ColumnSpec] = _build() + [INGESTED_AT_SPEC]
GAMES_PARTITION = TimePartition(field="game_date", clustering=["season", "week"])
