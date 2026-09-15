from __future__ import annotations

import pandas as pd

from nfl_bigquery._transform_util import align_to_schema
from nfl_bigquery.stats.schema import WEEKLY_STATS_SCHEMA


def transform_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    # Null player_id = nflverse team/aggregate rows (2001+). Not attributable to a
    # player, structurally unjoinable to dim_players.gsis_id, and rejected by the
    # REQUIRED column at load time. Drop them; player_id stays REQUIRED. Guard on
    # column presence: align_to_schema (below) is what adds a missing player_id
    # column for callers that pass a frame without one (e.g. sync's empty/partial
    # season fixtures), and dropna(subset=...) on a genuinely absent column raises
    # KeyError instead of no-op.
    if "player_id" in df.columns:
        df = df.dropna(subset=["player_id"])
    return align_to_schema(df, WEEKLY_STATS_SCHEMA)
