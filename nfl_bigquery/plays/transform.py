from __future__ import annotations

import pandas as pd

from nfl_bigquery._transform_util import align_to_schema
from nfl_bigquery.plays.schema import PLAYS_SCHEMA


def transform_pbp(df: pd.DataFrame) -> pd.DataFrame:
    return align_to_schema(df, PLAYS_SCHEMA)
