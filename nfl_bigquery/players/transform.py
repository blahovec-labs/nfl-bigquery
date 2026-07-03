from __future__ import annotations

import pandas as pd

from nfl_bigquery._transform_util import align_to_schema
from nfl_bigquery.players.schema import DIM_PLAYERS_SCHEMA


def transform_players(df: pd.DataFrame) -> pd.DataFrame:
    return align_to_schema(df, DIM_PLAYERS_SCHEMA)
