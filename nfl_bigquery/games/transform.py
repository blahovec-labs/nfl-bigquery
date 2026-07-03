from __future__ import annotations

import pandas as pd

from nfl_bigquery._transform_util import align_to_schema
from nfl_bigquery.games.schema import GAMES_SCHEMA


def transform_schedules(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "gameday" in df.columns and "game_date" not in df.columns:
        df = df.rename(columns={"gameday": "game_date"})
    return align_to_schema(df, GAMES_SCHEMA)
