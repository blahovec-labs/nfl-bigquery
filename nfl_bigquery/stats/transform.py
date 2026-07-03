from __future__ import annotations

import pandas as pd

from nfl_bigquery._transform_util import align_to_schema
from nfl_bigquery.stats.schema import WEEKLY_STATS_SCHEMA


def transform_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    return align_to_schema(df, WEEKLY_STATS_SCHEMA)
